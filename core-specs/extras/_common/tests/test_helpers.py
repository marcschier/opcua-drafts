"""Tests for the shared fingerprint + hexdump helpers.

Run: python core-specs/_common/tests/test_helpers.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from opcua_enc import fingerprint as fp  # noqa: E402
from opcua_enc import hexdump as hd  # noqa: E402


def test_rabin_matches_fastavro():
    import fastavro.schema as s

    for sch in [
        {"type": "string"},
        {"type": "long"},
        {"type": "record", "name": "R", "fields": [{"name": "a", "type": "int"}, {"name": "b", "type": ["null", "string"]}]},
    ]:
        pcf = s.to_parsing_canonical_form(s.parse_schema(sch))
        assert fp.avro_schema_id_hex(pcf.encode("utf-8")) == s.fingerprint(pcf, "CRC-64-AVRO")


def test_single_object_prefix_tail_equals_id():
    pcf = b'{"type":"long"}'
    prefix = fp.avro_single_object_prefix(fp.rabin_crc64_avro(pcf))
    assert prefix[:2] == b"\xc3\x01"
    assert prefix[2:].hex() == fp.avro_schema_id_hex(pcf)


def test_sha256_id_stable_and_sized():
    a = fp.sha256_id(b"schema", 8)
    assert len(a) == 8 and a == fp.sha256_id(b"schema", 8)
    assert fp.sha256_id(b"schema", 8) != fp.sha256_id(b"schema2", 8)


def test_hexdump_contiguity():
    data = bytes(range(10))
    fields = [hd.Field(0, 2, "magic"), hd.Field(2, 8, "fingerprint")]
    table = hd.hex_table(data, fields)
    assert "magic" in table and "fingerprint" in table
    try:
        hd.assert_contiguous([hd.Field(0, 2, "a"), hd.Field(3, 2, "b")], 5)
        raise AssertionError("expected gap to be detected")
    except ValueError:
        pass


if __name__ == "__main__":
    test_rabin_matches_fastavro()
    test_single_object_prefix_tail_equals_id()
    test_sha256_id_stable_and_sized()
    test_hexdump_contiguity()
    print("OK: fingerprint + hexdump helpers verified")
