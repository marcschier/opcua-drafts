"""Generate Annex C of the Avro Part 6 spec: a worked incremental-schema example.

The example grows a single lineage of self-contained Avro schemas append-only, as
governed by *OPC UA — Schema Registry* §5.6 and Avro §6.4, for a DataSet whose
fields are a Variant (`signal`) and an ExtensionObject (`event`) whose concrete
struct `SensorEvent` itself contains a nested Variant (`detail`). It demonstrates:

* the data-driven narrow start (only the concrete types of the first values);
* growth at three positions — the shared Variant body union (for the top-level
  `signal`), that *same* shared union again (for the nested `detail`), and the
  ExtensionObject body union (for a second concrete struct);
* distinct per-minor SchemaIds (CRC-64-AVRO of the Parsing Canonical Form); and
* a message written under 1.0 decoding unchanged under 1.3 (append-only).

The generator computes everything from real fastavro schemas and asserts the
round-trip and compatibility properties, then injects the rendered Annex between
its markers (drift-gated via ``--check`` from ``validate_local.py``).
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from io import BytesIO
from pathlib import Path

from fastavro import parse_schema, schemaless_reader, schemaless_writer
from fastavro.schema import to_parsing_canonical_form

ROOT = Path(__file__).resolve().parents[1]
STD = ROOT.parents[1] / "avro-encoding"
PART6 = STD / "OPC-UA-Part6-Avro-DataEncoding.md"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
import schema_support  # noqa: E402
from opcua_enc import fingerprint  # noqa: E402

NS = "org.opcfoundation.ua.avro"
BEGIN = "<!-- BEGIN GENERATED: evolution-annex -->"
END = "<!-- END GENERATED: evolution-annex -->"

# OPC UA BuiltInType ids for the body types the example uses.
BUILTIN_ID = {"Boolean": 1, "Int32": 6, "Float": 10, "Double": 11}
SCALAR_AVRO = {"Boolean": "boolean", "Int32": "int", "Float": "float", "Double": "double"}


# --------------------------------------------------------------------------
# Schema builders (a single shared Variant record and a single shared
# ExtensionObject record per self-contained schema, per schema_support.py).
# --------------------------------------------------------------------------
def _scalar_branch(key: str) -> dict:
    return {"type": "record", "name": f"Variant{key}Scalar", "namespace": NS,
            "fields": [{"name": "value", "type": SCALAR_AVRO[key]}]}


def _variant_record(body_keys: list[str]) -> dict:
    body = ["null"] + [f"{NS}.Variant{k}Scalar" for k in body_keys]
    return {"type": "record", "name": "Variant", "namespace": NS, "fields": [
        {"name": "builtInType", "type": "int"},
        {"name": "dimensions", "type": ["null", {"type": "array", "items": "int"}], "default": None},
        {"name": "body", "type": body, "default": None}]}


def _sensor_event() -> dict:
    # A concrete Structure whose `detail` field is itself a Variant (a struct with
    # a variant): it references the one shared Variant record by name.
    return {"type": "record", "name": "SensorEvent", "namespace": NS, "fields": [
        {"name": "deviceId", "type": "string"},
        {"name": "detail", "type": f"{NS}.Variant"}]}


def _alarm_event() -> dict:
    return {"type": "record", "name": "AlarmEvent", "namespace": NS, "fields": [
        {"name": "code", "type": "int"},
        {"name": "message", "type": ["null", "string"], "default": None}]}


def _ext_record(struct_names: list[str]) -> dict:
    # No opaque body occurs in this scenario, so the union carries no `bytes`
    # fallback; new concrete structs are appended at the end (append-only).
    body = ["null"] + [f"{NS}.{n}" for n in struct_names]
    return {"type": "record", "name": "ExtensionObject", "namespace": NS, "fields": [
        {"name": "typeId", "type": "string"},
        {"name": "body", "type": body, "default": None}]}


def _sample() -> dict:
    return {"type": "record", "name": "Sample", "namespace": NS, "fields": [
        {"name": "signal", "type": f"{NS}.Variant"},
        {"name": "event", "type": f"{NS}.ExtensionObject"}]}


def _named_defs(struct_names: list[str]) -> list[dict]:
    defs: list[dict] = [_sensor_event()]
    if "AlarmEvent" in struct_names:
        defs.append(_alarm_event())
    return defs


def _self_contained(variant_keys: list[str], struct_names: list[str]) -> dict:
    """Build the self-contained schema by inlining each named type at first use."""
    defs: list[dict] = [_scalar_branch(k) for k in variant_keys]
    defs.append(_variant_record(variant_keys))
    defs.extend(_named_defs(struct_names))
    defs.append(_ext_record(struct_names))
    sample = _sample()
    defs.append(sample)
    registry = schema_support.build_named_schema_registry(defs)
    return schema_support.self_contained_schema(sample, registry)


def _schema_id(schema: dict) -> str:
    canonical = to_parsing_canonical_form(parse_schema(copy.deepcopy(schema))).encode("utf-8")
    return fingerprint.avro_schema_id_hex(canonical)


def _body_union(schema: dict, record_name: str) -> list[str]:
    """Short-name body union of a named record inside the self-contained schema."""
    def find(node):
        if isinstance(node, dict):
            if node.get("name") == record_name and node.get("type") == "record":
                return node
            for v in node.values():
                r = find(v)
                if r:
                    return r
        if isinstance(node, list):
            for v in node:
                r = find(v)
                if r:
                    return r
        return None

    rec = find(schema)
    body = next(f for f in rec["fields"] if f["name"] == "body")["type"]
    names = []
    for branch in body:
        if isinstance(branch, str):
            names.append(branch.split(".")[-1] if branch.startswith(NS) else branch)
        elif isinstance(branch, dict):
            names.append(branch.get("name", "<inline>"))
    return names


# --------------------------------------------------------------------------
# Values
# --------------------------------------------------------------------------
def _variant_value(key: str, value) -> dict:
    return {"builtInType": BUILTIN_ID[key], "dimensions": None,
            "body": (f"{NS}.Variant{key}Scalar", {"value": value})}


def _sensor_sample(signal_key, signal_value, detail_key, detail_value) -> dict:
    return {
        "signal": _variant_value(signal_key, signal_value),
        "event": {"typeId": "i=1001", "body": (f"{NS}.SensorEvent", {
            "deviceId": "dev-1", "detail": _variant_value(detail_key, detail_value)})},
    }


def _write(schema: dict, datum: dict) -> bytes:
    bio = BytesIO()
    schemaless_writer(bio, parse_schema(copy.deepcopy(schema)), datum)
    return bio.getvalue()


def _read(schema: dict, data: bytes) -> dict:
    return schemaless_reader(BytesIO(data), parse_schema(copy.deepcopy(schema)), return_record_name=True)


# --------------------------------------------------------------------------
# Build + assert
# --------------------------------------------------------------------------
MINORS = [
    ("1.0", ["Int32", "Boolean"], ["SensorEvent"],
     "First message: `signal` = Int32(42), `event` = SensorEvent{ detail = Boolean(true) }. The initial (`MAJOR.0`) schema is narrowed data-driven to exactly the concrete types the two fields first carry."),
    ("1.1", ["Int32", "Boolean", "Double"], ["SensorEvent"],
     "`signal` now carries a Double, so `VariantDoubleScalar` is appended to the shared Variant body union. The ExtensionObject union is unchanged."),
    ("1.2", ["Int32", "Boolean", "Double", "Float"], ["SensorEvent"],
     "The nested `event.detail` Variant now carries a Float, so `VariantFloatScalar` is appended to the **same shared** Variant body union — growth triggered from inside the ExtensionObject struct. Because the Variant record is shared, the Float body type is thereby also available to `signal`."),
    ("1.3", ["Int32", "Boolean", "Double", "Float"], ["SensorEvent", "AlarmEvent"],
     "`event` now carries a second concrete struct, `AlarmEvent`, so it is appended to the ExtensionObject body union. The shared Variant union is unchanged."),
]


def _build():
    rows = []
    for label, vkeys, snames, desc in MINORS:
        schema = _self_contained(vkeys, snames)
        rows.append({
            "label": label, "desc": desc, "schema": schema,
            "schema_id": _schema_id(schema),
            "variant_union": _body_union(schema, "Variant"),
            "ext_union": _body_union(schema, "ExtensionObject"),
        })

    # Distinct SchemaId per minor.
    ids = [r["schema_id"] for r in rows]
    assert len(set(ids)) == len(ids), f"SchemaIds not distinct: {ids}"

    # Append-only: each minor's Variant and ExtensionObject unions are a prefix
    # extension of the previous minor's (no reorder/removal of existing members).
    for prev, cur in zip(rows, rows[1:]):
        assert cur["variant_union"][:len(prev["variant_union"])] == prev["variant_union"], "variant union not append-only"
        assert cur["ext_union"][:len(prev["ext_union"])] == prev["ext_union"], "ext union not append-only"

    # Round-trip a representative value under each minor.
    v10 = _sensor_sample("Int32", 42, "Boolean", True)
    v11 = _sensor_sample("Double", 2.5, "Boolean", True)
    v12 = _sensor_sample("Int32", 7, "Float", 1.5)
    v13 = {"signal": _variant_value("Int32", 7),
           "event": {"typeId": "i=1002", "body": (f"{NS}.AlarmEvent", {"code": 9, "message": "over-temp"})}}
    for schema, datum in ((rows[0]["schema"], v10), (rows[1]["schema"], v11),
                          (rows[2]["schema"], v12), (rows[3]["schema"], v13)):
        got = _read(schema, _write(schema, datum))
        assert got["signal"]["body"][1] is not None

    # Backward compatibility: a message written under 1.0 decodes unchanged under 1.3.
    bytes_v10 = _write(rows[0]["schema"], v10)
    under_v13 = _read(rows[3]["schema"], bytes_v10)
    assert under_v13["signal"]["body"][0] == f"{NS}.VariantInt32Scalar"
    assert under_v13["signal"]["body"][1]["value"] == 42
    assert under_v13["event"]["body"][0] == f"{NS}.SensorEvent"
    assert under_v13["event"]["body"][1]["detail"]["body"][0] == f"{NS}.VariantBooleanScalar"
    assert under_v13["event"]["body"][1]["detail"]["body"][1]["value"] is True

    return rows, bytes_v10.hex()


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------
def _union_code(names: list[str]) -> str:
    return "`[" + ", ".join(f'"{n}"' for n in names) + "]`"


def generated_content() -> str:
    rows, hex_v10 = _build()
    out: list[str] = [
        "This annex is generated from real Avro schemas by `../extras/avro-encoding/tools/gen_evolution_annex.py`; do not edit it by hand.",
        "",
        "It shows one lineage of self-contained schemas built and adapted incrementally as values are observed, per the growing-union model of §6.4 and *OPC UA — Schema Registry* §5.6. All record names below are in the `org.opcfoundation.ua.avro` namespace.",
        "",
        "**Scenario.** A DataSet sample has two fields: `signal`, a Variant, and `event`, an ExtensionObject whose concrete struct `SensorEvent` itself contains a Variant field `detail` (a struct with a variant). A self-contained schema carries a single shared `Variant` record, so both `signal` and the nested `detail` reference the *same* growing Variant body union; the `event` ExtensionObject has its own growing struct-type union. The initial schema is built data-driven from the first values, then grown append-only at whichever position changes.",
        "",
    ]
    for r in rows:
        out.append(f"### MinorVersion {r['label']}")
        out.append("")
        out.append(r["desc"])
        out.append("")
        out.append(f"- Shared Variant body union: {_union_code(r['variant_union'])}")
        out.append(f"- ExtensionObject body union: {_union_code(r['ext_union'])}")
        out.append(f"- **SchemaId** `{r['schema_id']}`")
        out.append("")
        if r["label"] == "1.0":
            out.append("Self-contained `MAJOR.0` schema:")
            out.append("")
            out.append("```json")
            out.append(json.dumps(r["schema"], ensure_ascii=False, indent=2, sort_keys=True))
            out.append("```")
            out.append("")

    out.append("### Backward compatibility")
    out.append("")
    out.append(
        f"A `Sample` written under 1.0 — `signal` = Int32(42), `event` = SensorEvent{{ detail = Boolean(true) }} — encodes to `{hex_v10}` and decodes unchanged under the 1.3 schema. `VariantInt32Scalar` (branch 1) and `VariantBooleanScalar` (branch 2) keep their indices in the shared Variant union, and `SensorEvent` (branch 1) keeps its index in the ExtensionObject union, because every member was appended, never reordered. Each minor is a distinct SchemaId in one lineage; a decoder holding the 1.3 schema decodes every earlier minor of that lineage, while the appended members stay unused for older values (§6.4)."
    )
    out.append("")
    return "\n".join(out).rstrip() + "\n"


def inject(doc: str, content: str) -> str:
    if BEGIN not in doc or END not in doc:
        block = f"\n\n## Annex C Worked schema-evolution example (incremental growth)\n\n{BEGIN}\n{content}{END}\n"
        return doc.rstrip() + block
    before, rest = doc.split(BEGIN, 1)
    _old, after = rest.split(END, 1)
    return before + BEGIN + "\n" + content + END + after


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if the committed Annex C is stale")
    args = ap.parse_args()
    content = generated_content()
    old = PART6.read_text(encoding="utf-8")
    new = inject(old, content)
    if args.check:
        if old != new:
            print("evolution annex drift: run python ..\\extras\\avro-encoding\\tools\\gen_evolution_annex.py")
            return 1
        print(f"evolution annex: {len(MINORS)} minors checked")
        return 0
    PART6.write_text(new, encoding="utf-8", newline="\n")
    print(f"wrote evolution annex ({len(MINORS)} minors) to {PART6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
