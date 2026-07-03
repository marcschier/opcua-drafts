from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc import hexdump


PRIMITIVES = {"null", "boolean", "int", "long", "float", "double", "bytes", "string"}


def _fullname(schema: Mapping[str, Any]) -> str | None:
    name = schema.get("name")
    if not isinstance(name, str):
        return None
    if "." in name:
        return name
    ns = schema.get("namespace")
    return f"{ns}.{name}" if isinstance(ns, str) and ns else name


def _named_schemas(schema: Any) -> dict[str, Any]:
    named: dict[str, Any] = {}

    def visit(s: Any) -> None:
        if isinstance(s, Mapping):
            embedded = s.get("__named_schemas")
            if isinstance(embedded, Mapping):
                for k, v in embedded.items():
                    if not k.startswith("__"):
                        named[k] = v
            fn = _fullname(s)
            if fn:
                named[fn] = s
            typ = s.get("type")
            if typ is not s:
                visit(typ)
            for f in s.get("fields", []) or []:
                visit(f.get("type"))
            visit(s.get("items"))
            visit(s.get("values"))
        elif isinstance(s, list):
            for x in s:
                visit(x)

    visit(schema)
    return named


def _resolve(schema: Any, named: dict[str, Any]) -> Any:
    while isinstance(schema, str) and schema not in PRIMITIVES and schema in named:
        schema = named[schema]
    return schema


def _read_varint(data: bytes, offset: int) -> tuple[int, int, int]:
    raw = 0
    shift = 0
    pos = offset
    while True:
        if pos >= len(data):
            raise ValueError("truncated Avro varint")
        b = data[pos]
        pos += 1
        raw |= (b & 0x7F) << shift
        if not b & 0x80:
            break
        shift += 7
        if shift > 70:
            raise ValueError("Avro varint is too long")
    value = (raw >> 1) ^ -(raw & 1)
    return value, offset, pos - offset


def _append_varint(fields: list[hexdump.Field], data: bytes, offset: int, label: str) -> tuple[int, int]:
    value, start, length = _read_varint(data, offset)
    fields.append(hexdump.Field(start, length, f"{label} = {value}"))
    return value, start + length


def annotate(schema: Any, data: bytes) -> list[hexdump.Field]:
    """Return contiguous byte-layout fields for schemaless Avro ``data``.

    ``schema`` may be a raw or fastavro-parsed schema. Named references are
    resolved from the parsed ``__named_schemas`` table when available.
    """
    named = _named_schemas(schema)
    fields: list[hexdump.Field] = []
    end = _walk(schema, data, 0, "$", fields, named)
    if end != len(data):
        raise ValueError(f"annotation consumed {end} bytes but payload has {len(data)}")
    hexdump.assert_contiguous(fields, len(data))
    return fields


def _walk(schema: Any, data: bytes, offset: int, label: str, fields: list[hexdump.Field], named: dict[str, Any]) -> int:
    schema = _resolve(schema, named)
    if isinstance(schema, list):
        index, pos = _append_varint(fields, data, offset, f"{label}: union branch index")
        if index < 0 or index >= len(schema):
            raise ValueError(f"union branch index {index} outside 0..{len(schema) - 1}")
        branch = schema[index]
        branch_name = _schema_label(branch, named)
        return _walk(branch, data, pos, f"{label}: branch {index} ({branch_name})", fields, named)
    if isinstance(schema, str):
        return _walk_primitive(schema, data, offset, label, fields)
    if not isinstance(schema, Mapping):
        raise TypeError(f"unsupported Avro schema node {schema!r}")

    typ = _resolve(schema.get("type"), named)
    if isinstance(typ, (list, Mapping)):
        return _walk(typ, data, offset, label, fields, named)
    if typ == "record":
        pos = offset
        for f in schema.get("fields", []):
            pos = _walk(f["type"], data, pos, f"{label}.{f['name']}", fields, named)
        return pos
    if typ == "array":
        pos = offset
        block = 0
        while True:
            count, pos = _append_varint(fields, data, pos, f"{label}: array block {block} count")
            if count == 0:
                return pos
            if count < 0:
                count = -count
                _size, pos = _append_varint(fields, data, pos, f"{label}: array block {block} byte size")
            for i in range(count):
                pos = _walk(schema["items"], data, pos, f"{label}[{i}]", fields, named)
            block += 1
    if typ == "map":
        pos = offset
        block = 0
        while True:
            count, pos = _append_varint(fields, data, pos, f"{label}: map block {block} count")
            if count == 0:
                return pos
            if count < 0:
                count = -count
                _size, pos = _append_varint(fields, data, pos, f"{label}: map block {block} byte size")
            for i in range(count):
                pos = _walk_primitive("string", data, pos, f"{label}{{key {i}}}", fields)
                pos = _walk(schema["values"], data, pos, f"{label}{{value {i}}}", fields, named)
            block += 1
    if typ == "fixed":
        size = int(schema["size"])
        fields.append(hexdump.Field(offset, size, f"{label}: fixed {schema.get('name', '')} ({size} bytes)"))
        return offset + size
    if typ == "enum":
        _index, pos = _append_varint(fields, data, offset, f"{label}: enum index")
        return pos
    return _walk_primitive(str(typ), data, offset, label, fields)


def _walk_primitive(typ: str, data: bytes, offset: int, label: str, fields: list[hexdump.Field]) -> int:
    if typ == "null":
        fields.append(hexdump.Field(offset, 0, f"{label}: null"))
        return offset
    if typ == "boolean":
        fields.append(hexdump.Field(offset, 1, f"{label}: boolean"))
        return offset + 1
    if typ in ("int", "long"):
        _value, pos = _append_varint(fields, data, offset, f"{label}: {typ}")
        return pos
    if typ == "float":
        fields.append(hexdump.Field(offset, 4, f"{label}: float32 little-endian"))
        return offset + 4
    if typ == "double":
        fields.append(hexdump.Field(offset, 8, f"{label}: float64 little-endian"))
        return offset + 8
    if typ in ("bytes", "string"):
        length, pos = _append_varint(fields, data, offset, f"{label}: {typ} length")
        if length < 0:
            raise ValueError(f"negative {typ} length {length}")
        fields.append(hexdump.Field(pos, length, f"{label}: {typ} data"))
        return pos + length
    raise ValueError(f"unsupported Avro primitive {typ!r}")


def _schema_label(schema: Any, named: dict[str, Any]) -> str:
    schema = _resolve(schema, named)
    if isinstance(schema, str):
        return schema
    if isinstance(schema, Mapping):
        return str(_fullname(schema) or schema.get("type"))
    return str(schema)


if __name__ == "__main__":
    raise SystemExit("wire_annotate.py is a library; import annotate(schema, data)")
