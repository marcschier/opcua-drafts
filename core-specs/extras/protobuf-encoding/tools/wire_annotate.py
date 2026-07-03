from __future__ import annotations

import os
import sys
from typing import Any

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "_common")))
from opcua_enc import hexdump  # noqa: E402

try:
    from google.protobuf.descriptor import FieldDescriptor
except ImportError:  # pragma: no cover
    FieldDescriptor = Any  # type: ignore


def _varint(data: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    start = pos
    while pos < len(data):
        b = data[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if not b & 0x80:
            return value, pos - start
        shift += 7
        if shift >= 70:
            break
    raise ValueError(f"unterminated varint at offset {start}")


def _field_by_number(desc: Any, number: int) -> Any | None:
    try:
        return desc.fields_by_number.get(number)
    except AttributeError:
        return None


def _name(field: Any | None, number: int) -> str:
    return field.name if field is not None else f"field_{number}"


def _annotate(data: bytes, message_descriptor: Any, *, prefix: str, base: int) -> list[hexdump.Field]:
    fields: list[hexdump.Field] = []
    pos = 0
    total = len(data)
    while pos < total:
        tag_offset = pos
        tag, tag_len = _varint(data, pos)
        pos += tag_len
        number = tag >> 3
        wire_type = tag & 0x07
        fd = _field_by_number(message_descriptor, number)
        label = f"{prefix}{_name(fd, number)}"
        fields.append(hexdump.Field(base + tag_offset, tag_len, f"{label}: tag field={number} wire={wire_type}"))

        if wire_type == 0:
            _, val_len = _varint(data, pos)
            fields.append(hexdump.Field(base + pos, val_len, f"{label}: varint value"))
            pos += val_len
        elif wire_type == 1:
            fields.append(hexdump.Field(base + pos, 8, f"{label}: 64-bit value"))
            pos += 8
        elif wire_type == 2:
            length, len_len = _varint(data, pos)
            fields.append(hexdump.Field(base + pos, len_len, f"{label}: length={length}"))
            pos += len_len
            payload_offset = pos
            payload = data[pos:pos + length]
            if len(payload) != length:
                raise ValueError(f"truncated length-delimited field {label}")
            if fd is not None and getattr(fd, "type", None) == FieldDescriptor.TYPE_MESSAGE and length:
                fields.extend(_annotate(payload, fd.message_type, prefix=f"{label}.", base=base + payload_offset))
            else:
                fields.append(hexdump.Field(base + payload_offset, length, f"{label}: payload"))
            pos += length
        elif wire_type == 5:
            fields.append(hexdump.Field(base + pos, 4, f"{label}: 32-bit value"))
            pos += 4
        else:
            raise ValueError(f"unsupported protobuf wire type {wire_type} at offset {tag_offset}")
    return fields


def annotate(data: bytes, message_descriptor: Any, *, prefix: str = "") -> list[hexdump.Field]:
    """Return contiguous byte annotations for ``data`` parsed as ``message_descriptor``."""
    fields = _annotate(data, message_descriptor, prefix=prefix, base=0)
    hexdump.assert_contiguous(fields, len(data))
    return fields


def main() -> int:
    import argparse
    import importlib

    parser = argparse.ArgumentParser(description="Annotate protobuf wire bytes.")
    parser.add_argument("module", help="generated *_pb2 module")
    parser.add_argument("message", help="message name")
    parser.add_argument("hex", help="protobuf bytes as hex")
    args = parser.parse_args()
    mod = importlib.import_module(args.module)
    desc = getattr(mod, args.message).DESCRIPTOR
    payload = bytes.fromhex(args.hex)
    print(hexdump.hex_table(payload, annotate(payload, desc)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
