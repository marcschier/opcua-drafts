"""Generate Annex C of the Avro Part 6 spec: a worked incremental-schema example
using the **per-field** Variant/ExtensionObject model.

Each Variant field carries its own record named by field path (`VariantSignal`,
`VariantEventDetail`), so the fields grow **independently**: growing the nested
`detail` Variant does not touch `signal`. The lineage grows one self-contained
schema append-only for a DataSet whose fields are a Variant (`signal`) and an
ExtensionObject (`event`) whose concrete struct `SensorEvent` contains a nested
Variant (`detail`). It demonstrates:

* the data-driven narrow start (only the concrete types of the first values);
* independent growth of `VariantSignal` (Int32 -> +Double) and `VariantEventDetail`
  (Boolean -> +Float), plus the `ExtensionObjectEvent` struct union (+AlarmEvent);
* distinct per-minor SchemaIds (CRC-64-AVRO of the Parsing Canonical Form); and
* a message written under 1.0 decoding unchanged under 1.3 (append-only).

The generator computes everything from real fastavro schemas and asserts the
round-trip, independence and compatibility properties, then injects the rendered
Annex between its markers (drift-gated via ``--check`` from ``validate_local.py``).
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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc import fingerprint  # noqa: E402

NS = "org.opcfoundation.ua.avro"
BEGIN = "<!-- BEGIN GENERATED: evolution-annex -->"
END = "<!-- END GENERATED: evolution-annex -->"

BUILTIN_ID = {"Boolean": 1, "Int32": 6, "Float": 10, "Double": 11}
SCALAR_AVRO = {"Boolean": "boolean", "Int32": "int", "Float": "float", "Double": "double"}


# --------------------------------------------------------------------------
# Per-field schema builders: each Variant/ExtObj occurrence is a distinct record
# named by field path, inlined once, so fields evolve independently.
# --------------------------------------------------------------------------
def _variant(name: str, keys: list[str]) -> dict:
    body: list = ["null"]
    for k in keys:
        body.append({"type": "record", "name": f"{name}_{k}Scalar", "namespace": NS,
                     "fields": [{"name": "value", "type": SCALAR_AVRO[k]}]})
    return {"type": "record", "name": name, "namespace": NS, "fields": [
        {"name": "builtInType", "type": "int"},
        {"name": "dimensions", "type": ["null", {"type": "array", "items": "int"}], "default": None},
        {"name": "body", "type": body, "default": None}]}


def _alarm_event() -> dict:
    return {"type": "record", "name": "AlarmEvent", "namespace": NS, "fields": [
        {"name": "code", "type": "int"},
        {"name": "message", "type": ["null", "string"], "default": None}]}


def _sensor_event(detail_keys: list[str]) -> dict:
    return {"type": "record", "name": "SensorEvent", "namespace": NS, "fields": [
        {"name": "deviceId", "type": "string"},
        {"name": "detail", "type": _variant("VariantEventDetail", detail_keys)}]}


def _ext_event(detail_keys: list[str], struct_names: list[str]) -> dict:
    structs: list = [_sensor_event(detail_keys)]
    if "AlarmEvent" in struct_names:
        structs.append(_alarm_event())
    return {"type": "record", "name": "ExtensionObjectEvent", "namespace": NS, "fields": [
        {"name": "typeId", "type": "string"},
        {"name": "body", "type": ["null", *structs], "default": None}]}


def _sample(signal_keys: list[str], detail_keys: list[str], struct_names: list[str]) -> dict:
    return {"type": "record", "name": "Sample", "namespace": NS, "fields": [
        {"name": "signal", "type": _variant("VariantSignal", signal_keys)},
        {"name": "event", "type": _ext_event(detail_keys, struct_names)}]}


def _schema_id(schema: dict) -> str:
    canonical = to_parsing_canonical_form(parse_schema(copy.deepcopy(schema))).encode("utf-8")
    return fingerprint.avro_schema_id_hex(canonical)


def _find(node, name: str):
    if isinstance(node, dict):
        if node.get("name") == name and node.get("type") == "record":
            return node
        for v in node.values():
            r = _find(v, name)
            if r:
                return r
    if isinstance(node, list):
        for v in node:
            r = _find(v, name)
            if r:
                return r
    return None


def _body_union(schema: dict, record_name: str) -> list[str]:
    rec = _find(schema, record_name)
    body = next(f for f in rec["fields"] if f["name"] == "body")["type"]
    return [b if isinstance(b, str) else b["name"] for b in body]


# --------------------------------------------------------------------------
# Values
# --------------------------------------------------------------------------
def _variant_value(name: str, key: str, value) -> dict:
    return {"builtInType": BUILTIN_ID[key], "dimensions": None,
            "body": (f"{NS}.{name}_{key}Scalar", {"value": value})}


def _sensor_sample(signal_key, signal_value, detail_key, detail_value) -> dict:
    detail = _variant_value("VariantEventDetail", detail_key, detail_value)
    return {
        "signal": _variant_value("VariantSignal", signal_key, signal_value),
        "event": {"typeId": "i=1001",
                  "body": (f"{NS}.SensorEvent", {"deviceId": "dev-1", "detail": detail})},
    }


def _write(schema: dict, datum: dict) -> bytes:
    bio = BytesIO()
    schemaless_writer(bio, parse_schema(copy.deepcopy(schema)), datum)
    return bio.getvalue()


def _read(schema: dict, data: bytes) -> dict:
    return schemaless_reader(BytesIO(data), parse_schema(copy.deepcopy(schema)), return_record_name=True)


# --------------------------------------------------------------------------
# Build + assert.  Each minor: (label, signal_keys, detail_keys, struct_names, desc)
# --------------------------------------------------------------------------
MINORS = [
    ("1.0", ["Int32"], ["Boolean"], ["SensorEvent"],
     "First message: `signal` = Int32(42), `event` = SensorEvent{ detail = Boolean(true) }. The initial (`MAJOR.0`) schema is narrowed data-driven to exactly the concrete types each field first carries, and each Variant field has its own record (`VariantSignal`, `VariantEventDetail`)."),
    ("1.1", ["Int32", "Double"], ["Boolean"], ["SensorEvent"],
     "`signal` now carries a Double, so `VariantSignal_DoubleScalar` is appended to **`VariantSignal`** only. `VariantEventDetail` and the ExtensionObject union are untouched."),
    ("1.2", ["Int32", "Double"], ["Boolean", "Float"], ["SensorEvent"],
     "The nested `event.detail` Variant now carries a Float, so `VariantEventDetail_FloatScalar` is appended to **`VariantEventDetail`** only — because it has its own record, `VariantSignal` is unchanged (independent evolution). This is the key difference from a single shared `Variant` record."),
    ("1.3", ["Int32", "Double"], ["Boolean", "Float"], ["SensorEvent", "AlarmEvent"],
     "`event` now carries a second concrete struct, `AlarmEvent`, appended to the `ExtensionObjectEvent` body union. Both Variant records are unchanged."),
]


def _build():
    rows = []
    for label, sk, dk, sn, desc in MINORS:
        schema = _sample(sk, dk, sn)
        rows.append({
            "label": label, "desc": desc, "schema": schema, "schema_id": _schema_id(schema),
            "signal_union": _body_union(schema, "VariantSignal"),
            "detail_union": _body_union(schema, "VariantEventDetail"),
            "ext_union": _body_union(schema, "ExtensionObjectEvent"),
        })

    ids = [r["schema_id"] for r in rows]
    assert len(set(ids)) == len(ids), f"SchemaIds not distinct: {ids}"

    # Append-only: each field's union is a prefix extension of the previous minor's.
    for prev, cur in zip(rows, rows[1:]):
        for key in ("signal_union", "detail_union", "ext_union"):
            assert cur[key][:len(prev[key])] == prev[key], f"{key} not append-only"

    # Independence: growing one field never changes another field's union.
    assert rows[2]["signal_union"] == rows[1]["signal_union"], "signal changed when detail grew"
    assert rows[1]["detail_union"] == rows[0]["detail_union"], "detail changed when signal grew"

    # Round-trip a representative value under each minor.
    v10 = _sensor_sample("Int32", 42, "Boolean", True)
    v11 = _sensor_sample("Double", 2.5, "Boolean", True)
    v12 = _sensor_sample("Int32", 7, "Float", 1.5)
    v13 = {"signal": _variant_value("VariantSignal", "Int32", 7),
           "event": {"typeId": "i=1002", "body": (f"{NS}.AlarmEvent", {"code": 9, "message": "over-temp"})}}
    for schema, datum in ((rows[0]["schema"], v10), (rows[1]["schema"], v11),
                          (rows[2]["schema"], v12), (rows[3]["schema"], v13)):
        got = _read(schema, _write(schema, datum))
        assert got["signal"]["body"][1] is not None

    # Backward compatibility: a message written under 1.0 decodes unchanged under 1.3.
    bytes_v10 = _write(rows[0]["schema"], v10)
    under_v13 = _read(rows[3]["schema"], bytes_v10)
    assert under_v13["signal"]["body"][0] == f"{NS}.VariantSignal_Int32Scalar"
    assert under_v13["signal"]["body"][1]["value"] == 42
    assert under_v13["event"]["body"][0] == f"{NS}.SensorEvent"
    assert under_v13["event"]["body"][1]["detail"]["body"][0] == f"{NS}.VariantEventDetail_BooleanScalar"
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
        "It shows one lineage of self-contained schemas built and adapted incrementally as values are observed, per the per-field growing-union model of §6.4 and *OPC UA — Schema Registry* §5.6. All record names below are in the `org.opcfoundation.ua.avro` namespace.",
        "",
        "**Scenario.** A DataSet sample has two fields: `signal`, a Variant, and `event`, an ExtensionObject whose concrete struct `SensorEvent` itself contains a Variant field `detail` (a struct with a variant). Under the per-field model each Variant field has its **own** record named by field path — `VariantSignal` and `VariantEventDetail` — each with its own body union, so `signal` and the nested `detail` grow independently. The `event` ExtensionObject likewise has its own struct-type union. The initial schema is built data-driven from the first values, then grown append-only at whichever field changes.",
        "",
    ]
    for r in rows:
        out.append(f"### MinorVersion {r['label']}")
        out.append("")
        out.append(r["desc"])
        out.append("")
        out.append(f"- `VariantSignal` body union: {_union_code(r['signal_union'])}")
        out.append(f"- `VariantEventDetail` body union: {_union_code(r['detail_union'])}")
        out.append(f"- `ExtensionObjectEvent` body union: {_union_code(r['ext_union'])}")
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
        f"A `Sample` written under 1.0 — `signal` = Int32(42), `event` = SensorEvent{{ detail = Boolean(true) }} — encodes to `{hex_v10}` and decodes unchanged under the 1.3 schema. Each per-field record keeps its members' branch indices under growth (`VariantSignal_Int32Scalar`, `VariantEventDetail_BooleanScalar` and `SensorEvent` all stay at branch 1), because members are only ever appended, never reordered. Each minor is a distinct SchemaId in one lineage; a decoder holding the 1.3 schema decodes every earlier minor of that lineage, while the appended members stay unused for older values (§6.4). Note that between 1.1 and 1.2 the `VariantSignal` schema is byte-identical: growing `detail` cannot affect `signal` because they are separate records."
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
