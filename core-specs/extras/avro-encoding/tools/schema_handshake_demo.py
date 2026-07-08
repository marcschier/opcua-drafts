from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any

from fastavro import parse_schema, schemaless_reader, schemaless_writer
from fastavro.schema import to_parsing_canonical_form

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
STD = ROOT.parents[1] / "avro-encoding"
SCHEMAS = ROOT / "schemas"
STD_SCHEMAS = STD / "schemas"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc import corpus, fingerprint, types as t, values as v
from opcua_enc.values import canonical_equal, is_single_float_type

sys.path.insert(0, str(TOOLS))
import avro_codec
import schema_support


@dataclass(frozen=True)
class SchemaInfo:
    type: t.Type
    schema: object
    parsed_schema: object
    canonical_json: str
    schema_id: str
    fp: int


@dataclass(frozen=True)
class Frame:
    kind: str
    schema_id: str
    body: bytes | None = None
    schema_json: str | None = None


def _schema_info(ty: t.Type) -> SchemaInfo:
    schema = schema_support.self_contained_schema(_raw_schema(ty), _schema_registry())
    parsed = parse_schema(schema)
    canonical = to_parsing_canonical_form(parsed)
    canonical_bytes = canonical.encode("utf-8")
    fp = fingerprint.rabin_crc64_avro(canonical_bytes)
    schema_id = fingerprint.avro_schema_id_hex(canonical_bytes)
    return SchemaInfo(ty, schema, parsed, canonical, schema_id, fp)


@lru_cache(maxsize=1)
def _schema_registry() -> dict[str, object]:
    schemas: list[object] = []
    schemas.extend(json.loads((STD_SCHEMAS / "opcua.builtins.avsc").read_text(encoding="utf-8")))
    for path in sorted(SCHEMAS.glob("*.avsc")):
        schemas.append(json.loads(path.read_text(encoding="utf-8")))
    return schema_support.build_named_schema_registry(schemas)


def _raw_schema(ty: t.Type) -> object:
    if isinstance(ty, (t.Struct, t.Enumeration)):
        return json.loads((SCHEMAS / f"{schema_support.avro_name(ty.name)}.avsc").read_text(encoding="utf-8"))
    return schema_support.schema_for_type(ty, top=True)


class Encoder:
    def __init__(self) -> None:
        self.announced: dict[str, set[str]] = {}
        self.announce_count: dict[str, int] = {}

    def encode(self, destination: str, ty: t.Type, value: Any) -> list[Frame]:
        info = _schema_info(ty)
        out: list[Frame] = []
        seen = self.announced.setdefault(destination, set())
        if info.schema_id not in seen:
            seen.add(info.schema_id)
            self.announce_count[info.schema_id] = self.announce_count.get(info.schema_id, 0) + 1
            out.append(Frame("schema-announcement", info.schema_id, schema_json=info.canonical_json))
        datum = avro_codec.encode_value(ty, value)
        bio = BytesIO()
        schemaless_writer(bio, info.parsed_schema, datum)
        body = fingerprint.avro_single_object_prefix(info.fp) + bio.getvalue()
        out.append(Frame("value", info.schema_id, body=body))
        return out

    def announce(self, destination: str, ty: t.Type) -> Frame:
        info = _schema_info(ty)
        self.announced.setdefault(destination, set()).add(info.schema_id)
        self.announce_count[info.schema_id] = self.announce_count.get(info.schema_id, 0) + 1
        return Frame("schema-announcement", info.schema_id, schema_json=info.canonical_json)


@dataclass
class Decoder:
    type_by_id: dict[str, t.Type]
    cache: dict[str, object] = field(default_factory=dict)

    def accept(self, frame: Frame) -> Any | None:
        if frame.kind == "schema-announcement":
            assert frame.schema_json is not None
            canonical = frame.schema_json.encode("utf-8")
            assert fingerprint.avro_schema_id_hex(canonical) == frame.schema_id
            self.cache[frame.schema_id] = parse_schema(json.loads(frame.schema_json))
            return None
        if frame.kind != "value":
            raise ValueError(frame.kind)
        if frame.schema_id not in self.cache:
            raise UnknownSchema(frame.schema_id)
        assert frame.body is not None
        expected_prefix = fingerprint.avro_single_object_prefix(int.from_bytes(bytes.fromhex(frame.schema_id), "little"))
        assert frame.body.startswith(expected_prefix)
        datum = schemaless_reader(BytesIO(frame.body[len(expected_prefix):]), self.cache[frame.schema_id])
        return avro_codec.decode_value(self.type_by_id[frame.schema_id], datum)


class UnknownSchema(Exception):
    pass


def main() -> int:
    point_value = v.StructValue({"X": 1.0, "Y": 2.0}, "Point")
    point_value2 = v.StructValue({"X": 3.0, "Y": 4.0}, "Point")
    envelope_value = next(c.value for c in corpus.CORPUS if c.name == "envelope")

    point_info = _schema_info(corpus.POINT)
    envelope_info = _schema_info(corpus.ENVELOPE)
    assert point_info.schema_id != envelope_info.schema_id

    encoder = Encoder()
    decoder = Decoder({point_info.schema_id: corpus.POINT, envelope_info.schema_id: corpus.ENVELOPE})
    decoded: list[Any] = []

    for ty, value in [(corpus.POINT, point_value), (corpus.POINT, point_value2), (corpus.ENVELOPE, envelope_value)]:
        for frame in encoder.encode("primary", ty, value):
            got = decoder.accept(frame)
            if got is not None:
                decoded.append(got)

    assert encoder.announce_count[point_info.schema_id] == 1
    assert encoder.announce_count[envelope_info.schema_id] == 1
    assert canonical_equal(point_value, decoded[0], single_float=is_single_float_type(corpus.POINT))
    assert canonical_equal(point_value2, decoded[1], single_float=is_single_float_type(corpus.POINT))
    assert canonical_equal(envelope_value, decoded[2], single_float=is_single_float_type(corpus.ENVELOPE))

    late = Decoder({point_info.schema_id: corpus.POINT, envelope_info.schema_id: corpus.ENVELOPE})
    late_value_frame = encoder.encode("primary", corpus.ENVELOPE, envelope_value)[0]
    assert late_value_frame.kind == "value"
    try:
        late.accept(late_value_frame)
        raise AssertionError("late decoder unexpectedly decoded without schema")
    except UnknownSchema as exc:
        assert exc.args[0] == envelope_info.schema_id
    late.accept(encoder.announce("late", corpus.ENVELOPE))
    recovered = late.accept(late_value_frame)
    assert canonical_equal(envelope_value, recovered, single_float=is_single_float_type(corpus.ENVELOPE))

    print("schema_handshake_demo: announcements=2 schema-change=ok late-join=ok composite=ok decoded=4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
