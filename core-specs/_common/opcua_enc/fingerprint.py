"""Schema fingerprints / SchemaIds shared by the encoding extensions.

A **SchemaId** is a compact, deterministic fingerprint of a *canonical* schema
document. It is what a message carries (instead of the whole schema) so an
encoder can announce a schema once and reference it thereafter, and a decoder
can cache it by id (see each extension's Part 14 SchemaId handshake).

Two fingerprints are provided:

* :func:`rabin_crc64_avro` — the 64-bit CRC-64-AVRO Rabin fingerprint defined by
  the Apache Avro specification, used for Avro single-object encoding
  (``0xC3 0x01`` + 8-byte little-endian fingerprint). The caller passes the
  Avro *Parsing Canonical Form* bytes.
* :func:`sha256_id` — a generic truncated SHA-256 id for Protobuf / Arrow, whose
  canonical form is the serialized descriptor / schema.
"""
from __future__ import annotations

import hashlib

_EMPTY64 = 0xC15D213AA4D7A795
_MASK64 = 0xFFFFFFFFFFFFFFFF


def _build_table() -> list[int]:
    table: list[int] = []
    for i in range(256):
        fp = i
        for _ in range(8):
            fp = (fp >> 1) ^ (_EMPTY64 & -(fp & 1))
        table.append(fp & _MASK64)
    return table


_FP_TABLE = _build_table()


def rabin_crc64_avro(canonical: bytes) -> int:
    """The 64-bit CRC-64-AVRO Rabin fingerprint of ``canonical`` (PCF bytes)."""
    fp = _EMPTY64
    for b in canonical:
        fp = ((fp >> 8) ^ _FP_TABLE[(fp ^ b) & 0xFF]) & _MASK64
    return fp


def avro_single_object_prefix(fp: int) -> bytes:
    """The Avro single-object encoding prefix: ``0xC3 0x01`` + fp (8 bytes LE)."""
    return b"\xc3\x01" + (fp & _MASK64).to_bytes(8, "little")


def avro_schema_id_hex(canonical: bytes) -> str:
    """Hex of the Avro Rabin fingerprint in little-endian byte order.

    This matches Avro single-object encoding (the 8 bytes after ``0xC3 0x01``)
    and fastavro's ``fingerprint(pcf, "CRC-64-AVRO")``.
    """
    return rabin_crc64_avro(canonical).to_bytes(8, "little").hex()


def sha256_id(canonical: bytes, nbytes: int = 8) -> bytes:
    """The first ``nbytes`` of SHA-256(``canonical``) as a SchemaId."""
    if not 1 <= nbytes <= 32:
        raise ValueError("nbytes must be 1..32")
    return hashlib.sha256(canonical).digest()[:nbytes]


def sha256_id_hex(canonical: bytes, nbytes: int = 8) -> str:
    return sha256_id(canonical, nbytes).hex()
