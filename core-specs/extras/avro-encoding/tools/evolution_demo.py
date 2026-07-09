"""Reference demonstration of append-only "growing union" schema evolution.

This is the executable companion to *OPC UA — Schema Registry* §5.6. Using
fastavro it shows, with assertions, that:

* a Variant body-type union and an ExtensionObject body union can start narrow
  and grow append-only across MinorVersions;
* the latest-minor (superset) schema decodes messages written under an earlier
  minor of the same lineage, because an existing union member keeps its Avro
  branch index (append-only), so older bytes select the same member and the
  appended members are simply unused;
* each minor is a distinct schema with a distinct Avro SchemaId (the CRC-64-AVRO
  Rabin fingerprint of the Parsing Canonical Form);
* an opaque-fallback branch (`bytes` for a Binary body, `string` for an XML or
  textual body) is appended append-only like any other branch — it may sit at
  any position, not a reserved index — and its branch index is fixed once
  appended, so an older opaque ExtensionObject body still decodes under a grown
  schema; and
* an old (narrow) reader cannot decode a value of a newly-appended type, which is
  why a consumer must hold the latest minor of the lineage.

Run standalone; the process exits non-zero if any assertion fails.
"""
from __future__ import annotations

import os
import sys
from io import BytesIO

from fastavro import parse_schema, schemaless_reader, schemaless_writer
from fastavro.schema import to_parsing_canonical_form

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc import fingerprint

NS = "org.opcfoundation.ua.avro"


def _schema_id(schema: dict) -> str:
    canonical = to_parsing_canonical_form(parse_schema(schema)).encode("utf-8")
    return fingerprint.avro_schema_id_hex(canonical)


def _scalar_branch(key: str, avro_type: str) -> dict:
    return {"type": "record", "name": f"Variant{key}Scalar", "namespace": NS,
            "fields": [{"name": "value", "type": avro_type}]}


def _variant_schema(branches: list[dict]) -> dict:
    """A Variant record whose body union carries only the given branches, in order."""
    return {"type": "record", "name": "Variant", "namespace": NS, "fields": [
        {"name": "builtInType", "type": "int"},
        {"name": "dimensions", "type": ["null", {"type": "array", "items": "int"}], "default": None},
        {"name": "body", "type": ["null", *branches], "default": None}]}


def _ext_schema(branches: list) -> dict:
    """An ExtensionObject record whose body union carries the given branches in order.

    Branches are appended append-only in discovery order; an opaque fallback
    (``"bytes"`` for a Binary body, ``"string"`` for an XML or textual body) is
    just another appended branch and may sit at any position, not a reserved one.
    """
    return {"type": "record", "name": "ExtObj", "namespace": NS, "fields": [
        {"name": "typeId", "type": "string"},
        {"name": "body", "type": ["null", *branches], "default": None}]}


def _write(schema: dict, datum: dict) -> bytes:
    bio = BytesIO()
    schemaless_writer(bio, parse_schema(schema), datum)
    return bio.getvalue()


def _read(schema: dict, data: bytes) -> dict:
    return schemaless_reader(BytesIO(data), parse_schema(schema), return_record_name=True)


def _check(failures: list[str], name: str, condition: bool) -> None:
    if not condition:
        failures.append(name)


def run() -> int:
    failures: list[str] = []

    # ---- Variant body-type union: minor 0 {Int32} -> minor 1 {Int32, Double} ----
    int32 = _scalar_branch("Int32", "int")
    double = _scalar_branch("Double", "double")
    narrow = _variant_schema([int32])            # body: ["null", VariantInt32Scalar]
    grown = _variant_schema([int32, double])     # body: ["null", VariantInt32Scalar, VariantDoubleScalar]

    id_narrow, id_grown = _schema_id(narrow), _schema_id(grown)
    _check(failures, "variant-minor-distinct-schemaid", id_narrow != id_grown)

    # Append-only: the narrow body union is a prefix of the grown body union.
    nb = narrow["fields"][2]["type"]
    gb = grown["fields"][2]["type"]
    _check(failures, "variant-append-only-prefix", gb[:len(nb)] == nb)

    int32_variant = {"builtInType": 6, "dimensions": None,
                     "body": (f"{NS}.VariantInt32Scalar", {"value": 42})}
    double_variant = {"builtInType": 11, "dimensions": None,
                      "body": (f"{NS}.VariantDoubleScalar", {"value": 2.5})}

    # Written under minor 0.
    bytes_v0 = _write(narrow, int32_variant)
    # Baseline: minor 0 reader decodes its own bytes.
    got_v0_v0 = _read(narrow, bytes_v0)
    _check(failures, "variant-v0-selfdecode", got_v0_v0["body"][1]["value"] == 42)
    # Compatibility contract: the latest minor (grown) decodes the older (narrow) bytes.
    got_v0_v1 = _read(grown, bytes_v0)
    _check(failures, "variant-latest-decodes-older",
           got_v0_v1["body"][0] == f"{NS}.VariantInt32Scalar" and got_v0_v1["body"][1]["value"] == 42)
    # A value of the appended type round-trips under the grown schema.
    bytes_v1 = _write(grown, double_variant)
    got_v1_v1 = _read(grown, bytes_v1)
    _check(failures, "variant-appended-type-roundtrip",
           got_v1_v1["body"][0] == f"{NS}.VariantDoubleScalar" and got_v1_v1["body"][1]["value"] == 2.5)
    # Forward-incompatibility: the old (narrow) reader cannot decode the appended type.
    old_reader_failed = False
    try:
        r = _read(narrow, bytes_v1)
        old_reader_failed = r["body"][1].get("value") != 2.5
    except Exception:
        old_reader_failed = True
    _check(failures, "variant-old-reader-cannot-read-new", old_reader_failed)

    # ---- ExtensionObject union: opaque fallback appended append-only at any position ----
    # The fallback is NOT reserved ahead of the struct branches; each fallback
    # (`bytes` for a Binary body, `string` for an XML/textual body) is appended
    # when a value first needs it, exactly like a struct branch, so it may sit at
    # any position and keeps its index once appended.
    point = {"type": "record", "name": "Point", "namespace": NS,
             "fields": [{"name": "x", "type": "double"}, {"name": "y", "type": "double"}]}
    point2 = {"type": "record", "name": "Point2", "namespace": NS,
              "fields": [{"name": "x", "type": "double"}, {"name": "y", "type": "double"},
                         {"name": "z", "type": "double"}]}
    ext0 = _ext_schema([point])                              # ["null", Point]
    ext1 = _ext_schema([point, "bytes"])                     # ["null", Point, "bytes"]
    ext2 = _ext_schema([point, "bytes", "string"])           # ["null", Point, "bytes", "string"]
    ext3 = _ext_schema([point, "bytes", "string", point2])   # + Point' appended after the fallbacks

    ids = [_schema_id(ext0), _schema_id(ext1), _schema_id(ext2), _schema_id(ext3)]
    _check(failures, "ext-minors-distinct-schemaid", len(set(ids)) == 4)

    # Append-only: each body union is a prefix of the next.
    b0, b1, b2, b3 = (e["fields"][1]["type"] for e in (ext0, ext1, ext2, ext3))
    _check(failures, "ext-append-only-prefix",
           b1[:len(b0)] == b0 and b2[:len(b1)] == b1 and b3[:len(b2)] == b2)
    # The fallbacks sit at appended (non-reserved) positions: bytes at index 2, string at index 3.
    _check(failures, "ext-fallback-any-position", b3[2] == "bytes" and b3[3] == "string")

    # A struct written under minor 0 (Point at index 1) still decodes under minor 3.
    pt_v0 = {"typeId": "i=3001", "body": (f"{NS}.Point", {"x": 1.0, "y": 2.0})}
    got_pt = _read(ext3, _write(ext0, pt_v0))
    _check(failures, "ext-struct-decodes-under-grown",
           got_pt["body"][0] == f"{NS}.Point" and got_pt["body"][1] == {"x": 1.0, "y": 2.0})
    # An opaque Binary body written under minor 1 (bytes at index 2) still decodes under minor 3.
    opaque_bytes = {"typeId": "i=999", "body": ("bytes", b"\x01\x02\x03")}
    got_bytes = _read(ext3, _write(ext1, opaque_bytes))
    _check(failures, "ext-bytes-decodes-under-grown", got_bytes["body"] == b"\x01\x02\x03")
    # An opaque XML/textual body written under minor 2 (string at index 3) still decodes under minor 3.
    opaque_xml = {"typeId": "i=888", "body": ("string", "<Value>1</Value>")}
    got_xml = _read(ext3, _write(ext2, opaque_xml))
    _check(failures, "ext-string-decodes-under-grown", got_xml["body"] == "<Value>1</Value>")
    # The struct appended after the fallbacks round-trips typed under minor 3.
    p2 = {"typeId": "i=3002", "body": (f"{NS}.Point2", {"x": 1.0, "y": 2.0, "z": 3.0})}
    got_p2 = _read(ext3, _write(ext3, p2))
    _check(failures, "ext-appended-struct-roundtrip",
           got_p2["body"][0] == f"{NS}.Point2" and got_p2["body"][1] == {"x": 1.0, "y": 2.0, "z": 3.0})

    total = 13
    if failures:
        for f in failures:
            print(f"FAIL {f}")
    print(f"evolution_demo: {total - len(failures)}/{total} checks passed, {len(failures)} failures")
    return len(failures)


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
