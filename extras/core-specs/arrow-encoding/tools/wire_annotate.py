from __future__ import annotations

import os
import struct
import sys
from collections.abc import Iterable

import pyarrow as pa

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc import hexdump


def annotate(data: bytes) -> list[hexdump.Field]:
    """Annotate an Arrow IPC stream.

    The annotation is exact at the IPC encapsulated-message level. FlatBuffer
    internals inside the metadata message are intentionally out of scope. For
    RecordBatch bodies, this annotator derives the buffer sequence from PyArrow
    arrays and verifies that the aligned buffers tile the body; if that cannot
    be proven it labels the body as one exact region.
    """

    messages = list(pa.ipc.MessageReader.open_stream(pa.BufferReader(data)))
    batches = _read_batches(data)
    batch_index = 0
    fields: list[hexdump.Field] = []
    offset = 0
    for message_index, message in enumerate(messages):
        label = f"message {message_index} {message.type}"
        if offset + 4 > len(data):
            raise ValueError("truncated IPC stream")
        prefix = struct.unpack_from("<i", data, offset)[0]
        if prefix == -1:
            fields.append(hexdump.Field(offset, 4, f"{label}: continuation (0xFFFFFFFF)"))
            offset += 4
            metadata_size = struct.unpack_from("<i", data, offset)[0]
            fields.append(hexdump.Field(offset, 4, f"{label}: metadata size (int32)"))
            offset += 4
        else:
            metadata_size = prefix
            fields.append(hexdump.Field(offset, 4, f"{label}: metadata size (int32, legacy no continuation)"))
            offset += 4

        fields.append(hexdump.Field(offset, metadata_size, f"{label}: metadata flatbuffer ({message.type}; FlatBuffer internals out of scope)"))
        offset += metadata_size
        meta_padding = _align8(offset) - offset
        if meta_padding:
            fields.append(hexdump.Field(offset, meta_padding, f"{label}: metadata padding"))
            offset += meta_padding

        body_len = 0 if message.body is None else len(message.body)
        if message.type == "record batch" and body_len and batch_index < len(batches):
            body_fields = _record_batch_body_fields(offset, body_len, batches[batch_index], label)
            fields.extend(body_fields)
            batch_index += 1
        elif body_len:
            fields.append(hexdump.Field(offset, body_len, f"{label}: body"))
        offset += body_len

    if offset < len(data):
        if data[offset:offset + 8] == b"\xff\xff\xff\xff\x00\x00\x00\x00":
            fields.append(hexdump.Field(offset, 4, "end-of-stream: continuation (0xFFFFFFFF)"))
            fields.append(hexdump.Field(offset + 4, 4, "end-of-stream: metadata size 0"))
            offset += 8
        elif data[offset:offset + 4] == b"\x00\x00\x00\x00":
            fields.append(hexdump.Field(offset, 4, "end-of-stream: metadata size 0"))
            offset += 4
    if offset != len(data):
        fields.append(hexdump.Field(offset, len(data) - offset, "trailing bytes"))
    hexdump.assert_contiguous(fields, len(data))
    return fields


def _read_batches(data: bytes) -> list[pa.RecordBatch]:
    reader = pa.ipc.open_stream(pa.BufferReader(data))
    return [batch for batch in reader]


def _record_batch_body_fields(offset: int, body_len: int, batch: pa.RecordBatch, label: str) -> list[hexdump.Field]:
    buffers: list[tuple[str, int]] = []
    for column_index, name in enumerate(batch.schema.names):
        buffers.extend(_array_buffers(batch.column(column_index), f"{label}: body column {name}"))

    pos = offset
    rel = 0
    out: list[hexdump.Field] = []
    try:
        for buf_label, size in buffers:
            out.append(hexdump.Field(pos, size, buf_label))
            pos += size
            rel += size
            padding = _align8(rel) - rel
            if padding:
                out.append(hexdump.Field(pos, padding, f"{buf_label} padding"))
                pos += padding
                rel += padding
        hexdump.assert_contiguous([hexdump.Field(f.offset - offset, f.length, f.label) for f in out], body_len)
    except Exception:
        return [hexdump.Field(offset, body_len, f"{label}: body (exact body; per-buffer offsets unavailable)")]
    return out


def _array_buffers(arr: pa.Array | pa.ChunkedArray, prefix: str) -> list[tuple[str, int]]:
    if isinstance(arr, pa.ChunkedArray):
        arr = arr.combine_chunks()
    ty = arr.type
    if pa.types.is_struct(ty):
        out = [_own_buffer(arr, 0, f"{prefix} validity bitmap")]
        for i, field in enumerate(ty):
            out.extend(_array_buffers(arr.field(i), f"{prefix}.{field.name}"))
        return _non_null(out)
    if pa.types.is_list(ty) or pa.types.is_large_list(ty):
        out = [
            _own_buffer(arr, 0, f"{prefix} validity bitmap"),
            _own_buffer(arr, 1, f"{prefix} offsets"),
        ]
        out.extend(_array_buffers(arr.values, f"{prefix}.item"))
        return _non_null(out)
    if pa.types.is_union(ty):
        out = [
            _own_buffer(arr, 1, f"{prefix} dense-union type ids"),
            _own_buffer(arr, 2, f"{prefix} dense-union value offsets"),
        ]
        for i, field in enumerate(ty):
            out.extend(_array_buffers(arr.field(i), f"{prefix}.{field.name}"))
        return _non_null(out)
    if pa.types.is_string(ty) or pa.types.is_binary(ty):
        return _non_null([
            _own_buffer(arr, 0, f"{prefix} validity bitmap"),
            _own_buffer(arr, 1, f"{prefix} offsets"),
            _own_buffer(arr, 2, f"{prefix} data"),
        ])
    if pa.types.is_large_string(ty) or pa.types.is_large_binary(ty):
        return _non_null([
            _own_buffer(arr, 0, f"{prefix} validity bitmap"),
            _own_buffer(arr, 1, f"{prefix} large offsets"),
            _own_buffer(arr, 2, f"{prefix} data"),
        ])
    if pa.types.is_null(ty):
        return []
    return _non_null([
        _own_buffer(arr, 0, f"{prefix} validity bitmap"),
        _own_buffer(arr, 1, f"{prefix} data"),
    ])


def _own_buffer(arr: pa.Array, index: int, label: str) -> tuple[str, int] | None:
    buffers = arr.buffers()
    if index >= len(buffers) or buffers[index] is None:
        return None
    return (label, buffers[index].size)


def _non_null(items: Iterable[tuple[str, int] | None]) -> list[tuple[str, int]]:
    return [item for item in items if item is not None]


def _align8(n: int) -> int:
    return (n + 7) & ~7


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python tools\\wire_annotate.py <stream.arrow>")
    with open(sys.argv[1], "rb") as f:
        payload = f.read()
    print(hexdump.hex_table(payload, annotate(payload)))
