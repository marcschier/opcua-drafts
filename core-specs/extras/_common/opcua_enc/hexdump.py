"""Render annotated byte layouts as Markdown, for the per-type "byte-level
layout" tables in the encoding specs.

A layout is a list of :class:`Field` ``(offset, length, label)`` rows over a
``bytes`` payload. :func:`hex_table` renders them; :func:`assert_contiguous`
checks the rows tile the payload with no gaps or overlaps (a correctness guard
for the wire annotators).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    offset: int
    length: int
    label: str


def assert_contiguous(fields: list[Field], total: int) -> None:
    pos = 0
    for f in fields:
        if f.offset != pos:
            raise ValueError(f"gap/overlap at offset {f.offset}, expected {pos} ({f.label})")
        if f.length < 0:
            raise ValueError(f"negative length for {f.label}")
        pos += f.length
    if pos != total:
        raise ValueError(f"fields cover {pos} bytes but payload is {total}")


def _fmt(chunk: bytes, limit: int = 16) -> str:
    if len(chunk) <= limit:
        return chunk.hex(" ") or "—"
    head = chunk[:limit].hex(" ")
    return f"{head} … (+{len(chunk) - limit} B)"


def hex_table(data: bytes, fields: list[Field], *, check: bool = True) -> str:
    """Render ``fields`` over ``data`` as a Markdown offset/bytes/len/field table."""
    if check:
        assert_contiguous(fields, len(data))
    rows = ["| Offset | Len | Bytes | Field |", "|---:|---:|---|---|"]
    for f in fields:
        chunk = data[f.offset:f.offset + f.length]
        label = f.label.replace("[", r"\[").replace("]", r"\]")
        rows.append(f"| {f.offset} | {f.length} | `{_fmt(chunk)}` | {label} |")
    return "\n".join(rows)


def raw_hex(data: bytes, width: int = 16) -> str:
    """A plain fenced hex dump of ``data`` (offset: hex  ascii)."""
    lines = []
    for off in range(0, len(data), width):
        chunk = data[off:off + width]
        hexs = chunk.hex(" ")
        asci = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{off:08x}  {hexs:<{width * 3}}  {asci}")
    return "\n".join(lines)
