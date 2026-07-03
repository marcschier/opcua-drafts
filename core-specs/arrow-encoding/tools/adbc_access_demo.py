from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Literal

import pyarrow as pa

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc import corpus
from opcua_enc import types as t
from opcua_enc import values as v
from opcua_enc.values import canonical_equal, is_single_float_type

import arrow_codec


@dataclass(frozen=True)
class HistorySample:
    source_timestamp: v.DateTime
    server_timestamp: v.DateTime | None
    value: Any
    status: v.StatusCode = v.StatusCode(0)


@dataclass(frozen=True)
class AggregateSample(HistorySample):
    aggregate_id: v.NodeId = v.NodeId(0, v.IdType.NUMERIC, 2342)
    processing_interval: int = 0
    interval_start: v.DateTime = v.DateTime(0)
    interval_end: v.DateTime = v.DateTime(0)


@dataclass(frozen=True)
class DecodedSample:
    node_id: v.NodeId
    source_timestamp: v.DateTime
    server_timestamp: v.DateTime | None
    value: Any
    status: v.StatusCode


@dataclass(frozen=True)
class DecodedAggregateSample(DecodedSample):
    aggregate_id: v.NodeId
    processing_interval: int
    interval_start: v.DateTime
    interval_end: v.DateTime


class Connection:
    def create_statement(self) -> "Statement":
        return Statement()


class Statement:
    def __init__(self) -> None:
        self._kind: Literal["raw", "processed"] | None = None
        self._node_id: v.NodeId | None = None
        self._data_type: t.Type | None = None
        self._samples: list[HistorySample] = []
        self._max_rows_per_batch = 1024

    def bind_raw(
        self,
        *,
        node_id: v.NodeId,
        data_type: t.Type,
        samples: list[HistorySample],
        max_rows_per_batch: int = 1024,
    ) -> "Statement":
        self._kind = "raw"
        self._node_id = node_id
        self._data_type = data_type
        self._samples = list(samples)
        self._max_rows_per_batch = max_rows_per_batch
        return self

    def bind_processed(
        self,
        *,
        node_id: v.NodeId,
        data_type: t.Type,
        samples: list[AggregateSample],
        max_rows_per_batch: int = 1024,
    ) -> "Statement":
        self._kind = "processed"
        self._node_id = node_id
        self._data_type = data_type
        self._samples = list(samples)
        self._max_rows_per_batch = max_rows_per_batch
        return self

    def execute_query(self) -> bytes:
        if self._kind is None or self._node_id is None or self._data_type is None:
            raise ValueError("statement is not bound")
        schema = history_schema(self._data_type, aggregate=self._kind == "processed")
        sink = pa.BufferOutputStream()
        with pa.ipc.new_stream(sink, schema) as writer:
            for offset in range(0, len(self._samples), self._max_rows_per_batch):
                chunk = self._samples[offset:offset + self._max_rows_per_batch]
                writer.write_batch(_batch(schema, self._node_id, self._data_type, chunk, self._kind == "processed"))
        return sink.getvalue().to_pybytes()


def history_schema(data_type: t.Type, *, aggregate: bool) -> pa.Schema:
    fields = [
        pa.field("NodeId", arrow_codec.canonical_type_to_arrow(t.NODEID), nullable=False),
        pa.field("SourceTimestamp", pa.int64(), nullable=False),
        pa.field("ServerTimestamp", pa.int64()),
        pa.field("Value", arrow_codec.canonical_type_to_arrow(data_type)),
        pa.field("StatusCode", pa.uint32(), nullable=False),
    ]
    if aggregate:
        fields.extend([
            pa.field("AggregateId", arrow_codec.canonical_type_to_arrow(t.NODEID), nullable=False),
            pa.field("ProcessingInterval", pa.int64(), nullable=False),
            pa.field("IntervalStart", pa.int64(), nullable=False),
            pa.field("IntervalEnd", pa.int64(), nullable=False),
        ])
    return pa.schema(fields, metadata={b"opcua-arrow": b"1", b"opcua-history": b"HistoryRead"})


def _batch(schema: pa.Schema, node_id: v.NodeId, data_type: t.Type, samples: list[HistorySample], aggregate: bool) -> pa.RecordBatch:
    columns = [
        arrow_codec._build_array(t.NODEID, [node_id] * len(samples), arrow_codec.DEFAULT_REGISTRY, schema.field("NodeId").type),
        pa.array([s.source_timestamp.ticks for s in samples], type=pa.int64()),
        pa.array([None if s.server_timestamp is None else s.server_timestamp.ticks for s in samples], type=pa.int64()),
        arrow_codec._build_array(data_type, [s.value for s in samples], arrow_codec.DEFAULT_REGISTRY, schema.field("Value").type),
        pa.array([s.status.value for s in samples], type=pa.uint32()),
    ]
    if aggregate:
        aggregate_samples = [s for s in samples if isinstance(s, AggregateSample)]
        if len(aggregate_samples) != len(samples):
            raise TypeError("processed statements require AggregateSample rows")
        columns.extend([
            arrow_codec._build_array(t.NODEID, [s.aggregate_id for s in aggregate_samples], arrow_codec.DEFAULT_REGISTRY, schema.field("AggregateId").type),
            pa.array([s.processing_interval for s in aggregate_samples], type=pa.int64()),
            pa.array([s.interval_start.ticks for s in aggregate_samples], type=pa.int64()),
            pa.array([s.interval_end.ticks for s in aggregate_samples], type=pa.int64()),
        ])
    return pa.record_batch(columns, schema=schema)


def read_history_stream(payload: bytes, data_type: t.Type, *, aggregate: bool) -> list[DecodedSample]:
    reader = pa.ipc.open_stream(pa.BufferReader(payload))
    expected_schema = history_schema(data_type, aggregate=aggregate)
    if not reader.schema.equals(expected_schema, check_metadata=True):
        raise AssertionError(f"schema mismatch:\n{reader.schema}\n!=\n{expected_schema}")
    rows: list[DecodedSample] = []
    for batch in reader:
        for row in range(batch.num_rows):
            common = dict(
                node_id=arrow_codec.decode_array_value(t.NODEID, batch.column(batch.schema.get_field_index("NodeId")), row),
                source_timestamp=v.DateTime(int(batch.column(batch.schema.get_field_index("SourceTimestamp"))[row].as_py())),
                server_timestamp=_nullable_datetime(batch.column(batch.schema.get_field_index("ServerTimestamp"))[row]),
                value=arrow_codec.decode_array_value(data_type, batch.column(batch.schema.get_field_index("Value")), row),
                status=v.StatusCode(int(batch.column(batch.schema.get_field_index("StatusCode"))[row].as_py())),
            )
            if aggregate:
                rows.append(DecodedAggregateSample(
                    **common,
                    aggregate_id=arrow_codec.decode_array_value(t.NODEID, batch.column(batch.schema.get_field_index("AggregateId")), row),
                    processing_interval=int(batch.column(batch.schema.get_field_index("ProcessingInterval"))[row].as_py()),
                    interval_start=v.DateTime(int(batch.column(batch.schema.get_field_index("IntervalStart"))[row].as_py())),
                    interval_end=v.DateTime(int(batch.column(batch.schema.get_field_index("IntervalEnd"))[row].as_py())),
                ))
            else:
                rows.append(DecodedSample(**common))
    return rows


def _nullable_datetime(scalar: pa.Scalar) -> v.DateTime | None:
    return None if not scalar.is_valid else v.DateTime(int(scalar.as_py()))


def _assert_raw_roundtrip() -> None:
    node_id = v.NodeId(2, v.IdType.STRING, "Machine/Line1/Point")
    samples = [
        HistorySample(v.DateTime(132537600000000000), v.DateTime(132537600000000100), v.StructValue({"X": 1.0, "Y": 2.0}, "Point")),
        HistorySample(v.DateTime(132537600010000000), v.DateTime(132537600010000100), v.StructValue({"X": 3.5, "Y": -0.0}, "Point")),
        HistorySample(v.DateTime(132537600020000000), v.DateTime(132537600020000100), v.StructValue({"X": 5.0, "Y": 8.0}, "Point"), v.StatusCode(0x40000000)),
    ]
    stream = Connection().create_statement().bind_raw(
        node_id=node_id,
        data_type=corpus.POINT,
        samples=samples,
        max_rows_per_batch=2,
    ).execute_query()
    assert _record_batch_count(stream) == 2, "max rows per batch must chunk the stream"
    decoded = read_history_stream(stream, corpus.POINT, aggregate=False)
    _assert_common(decoded, node_id, samples, corpus.POINT)


def _assert_aggregate_roundtrip() -> None:
    node_id = v.NodeId(2, v.IdType.STRING, "Machine/Line1/Temperature")
    aggregate_id = v.NodeId(0, v.IdType.NUMERIC, 2342)
    samples = [
        AggregateSample(v.DateTime(132537600300000000), v.DateTime(132537600300000050), 12.5, v.StatusCode(0), aggregate_id, 600_000_000, v.DateTime(132537600000000000), v.DateTime(132537600600000000)),
        AggregateSample(v.DateTime(132537600900000000), v.DateTime(132537600900000050), 13.25, v.StatusCode(0), aggregate_id, 600_000_000, v.DateTime(132537600600000000), v.DateTime(132537601200000000)),
    ]
    stream = Connection().create_statement().bind_processed(
        node_id=node_id,
        data_type=t.DOUBLE,
        samples=samples,
        max_rows_per_batch=1,
    ).execute_query()
    assert _record_batch_count(stream) == 2, "aggregate continuation batches must be preserved"
    decoded = read_history_stream(stream, t.DOUBLE, aggregate=True)
    _assert_common(decoded, node_id, samples, t.DOUBLE)
    for got, want in zip(decoded, samples):
        assert isinstance(got, DecodedAggregateSample)
        assert canonical_equal(got.aggregate_id, want.aggregate_id)
        assert got.processing_interval == want.processing_interval
        assert canonical_equal(got.interval_start, want.interval_start)
        assert canonical_equal(got.interval_end, want.interval_end)


def _assert_common(decoded: list[DecodedSample], node_id: v.NodeId, samples: list[HistorySample], data_type: t.Type) -> None:
    if len(decoded) != len(samples):
        raise AssertionError(f"decoded {len(decoded)} rows, expected {len(samples)}")
    for got, want in zip(decoded, samples):
        assert canonical_equal(got.node_id, node_id)
        assert canonical_equal(got.source_timestamp, want.source_timestamp)
        assert canonical_equal(got.server_timestamp, want.server_timestamp)
        assert canonical_equal(got.status, want.status)
        assert canonical_equal(got.value, want.value, single_float=is_single_float_type(data_type))


def _record_batch_count(payload: bytes) -> int:
    return sum(1 for message in pa.ipc.MessageReader.open_stream(pa.BufferReader(payload)) if message.type == "record batch")


def main() -> int:
    _assert_raw_roundtrip()
    _assert_aggregate_roundtrip()
    print("adbc_access_demo: raw HistoryRead and processed aggregate ArrowArrayStream roundtrips ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
