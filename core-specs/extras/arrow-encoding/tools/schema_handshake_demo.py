from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any

import pyarrow as pa

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc import fingerprint
from opcua_enc import types as t
from opcua_enc.values import canonical_equal, is_single_float_type

import arrow_codec
import build_schemas


@dataclass
class DestinationState:
    announced: set[str] = field(default_factory=set)


@dataclass
class Decoder:
    cache: dict[str, pa.Schema] = field(default_factory=dict)

    def receive_stream(self, schema_id: str, payload: bytes, ty: t.Type, expected: list[Any]) -> None:
        reader = pa.ipc.open_stream(pa.BufferReader(payload))
        if schema_id not in self.cache:
            self.cache[schema_id] = reader.schema
        if not reader.schema.equals(self.cache[schema_id], check_metadata=True):
            raise AssertionError("received stream schema does not match cached SchemaId schema")
        seen: list[Any] = []
        for batch in reader:
            if not batch.schema.equals(self.cache[schema_id], check_metadata=True):
                raise AssertionError("record batch schema drifted within stream")
            for row in range(batch.num_rows):
                seen.append(arrow_codec.decode_array_value(ty, batch.column(0), row))
        if len(seen) != len(expected):
            raise AssertionError(f"decoded {len(seen)} values, expected {len(expected)}")
        single = is_single_float_type(ty)
        for got, want in zip(seen, expected):
            if not canonical_equal(got, want, single_float=single):
                raise AssertionError(f"{got!r} != {want!r}")


def main() -> int:
    state = DestinationState()
    decoder = Decoder()
    registry: dict[str, bytes] = {}

    sid_a, stream_a, announced_a = encode_stream(t.INT32, [[1, 2], [3]], state, registry)
    assert announced_a, "first schema must be announced"
    assert _message_counts(stream_a)["schema"] == 1, "IPC Schema message must appear once in a stream"
    assert _message_counts(stream_a)["record batch"] == 2, "expected two RecordBatches"
    decoder.receive_stream(sid_a, stream_a, t.INT32, [1, 2, 3])

    sid_a2, stream_a2, announced_a2 = encode_stream(t.INT32, [[4]], state, registry)
    assert sid_a2 == sid_a, "same DataSet schema must keep the same SchemaId"
    assert not announced_a2, "known SchemaId must not be globally re-announced"
    assert _message_counts(stream_a2)["schema"] == 1, "each IPC stream still carries exactly one Schema message"
    decoder.receive_stream(sid_a2, stream_a2, t.INT32, [4])

    sid_b, stream_b, announced_b = encode_stream(t.STRING, [["changed", None]], state, registry)
    assert sid_b != sid_a, "schema change must yield a new SchemaId"
    assert announced_b, "new SchemaId must be announced"
    assert _message_counts(stream_b)["schema"] == 1, "changed schema opens a new stream with one Schema message"
    decoder.receive_stream(sid_b, stream_b, t.STRING, ["changed", None])

    late = Decoder()
    assert sid_a in registry, "published schema registry must contain the first SchemaId"
    late.cache[sid_a] = pa.ipc.read_schema(pa.BufferReader(registry[sid_a]))
    late.receive_stream(sid_a, stream_a, t.INT32, [1, 2, 3])
    assert sid_b not in late.cache
    late.cache[sid_b] = pa.ipc.read_schema(pa.BufferReader(registry[sid_b]))
    late.receive_stream(sid_b, stream_b, t.STRING, ["changed", None])

    print("schema_handshake_demo: announcements once per SchemaId, schema change re-announced, decoder cache and late-joiner recovery ok")
    return 0


def encode_stream(ty: t.Type, batches: list[list[Any]], state: DestinationState, registry: dict[str, bytes]) -> tuple[str, bytes, bool]:
    data_type = arrow_codec.canonical_type_to_arrow(ty)
    schema = pa.schema([pa.field("value", data_type)], metadata={b"opcua-arrow": b"1"})
    canonical = schema.serialize().to_pybytes()
    schema_id = fingerprint.sha256_id_hex(canonical, build_schemas.ARROW_SCHEMAID_BYTES)
    announced = schema_id not in state.announced
    if announced:
        state.announced.add(schema_id)
        registry[schema_id] = canonical
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, schema) as writer:
        for values in batches:
            arr = arrow_codec._build_array(ty, values, arrow_codec.DEFAULT_REGISTRY, data_type)
            writer.write_batch(pa.record_batch([arr], schema=schema))
    return schema_id, sink.getvalue().to_pybytes(), announced


def _message_counts(payload: bytes) -> dict[str, int]:
    counts: dict[str, int] = {}
    for message in pa.ipc.MessageReader.open_stream(pa.BufferReader(payload)):
        counts[message.type] = counts.get(message.type, 0) + 1
    return counts


if __name__ == "__main__":
    raise SystemExit(main())
