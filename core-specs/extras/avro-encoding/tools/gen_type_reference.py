from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import sys
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any

from fastavro import parse_schema

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
STD = ROOT.parents[1] / "avro-encoding"
SCHEMAS = ROOT / "schemas"
STD_SCHEMAS = STD / "schemas"
BUILTINS_SCHEMA = STD_SCHEMAS / "opcua.builtins.avsc"
SCHEMAIDS = SCHEMAS / "schemaids.json"
PART6 = STD / "OPC-UA-Part6-Avro-DataEncoding.md"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc import corpus, hexdump, types as t, values as v

sys.path.insert(0, str(TOOLS))
import avro_codec
import schema_support
import wire_annotate

BEGIN = "<!-- BEGIN GENERATED: type-reference -->"
END = "<!-- END GENERATED: type-reference -->"


BUILTIN_CASES = {
    t.BuiltInType.Boolean: "bool_true",
    t.BuiltInType.SByte: "sbyte_min",
    t.BuiltInType.Byte: "byte_max",
    t.BuiltInType.Int16: "int16_min",
    t.BuiltInType.UInt16: "uint16_max",
    t.BuiltInType.Int32: "int32_min",
    t.BuiltInType.UInt32: "uint32_max",
    t.BuiltInType.Int64: "int64_min",
    t.BuiltInType.UInt64: "uint64_max",
    t.BuiltInType.Float: "float_normal",
    t.BuiltInType.Double: "double_nan",
    t.BuiltInType.String: "string_unicode",
    t.BuiltInType.DateTime: "datetime_now",
    t.BuiltInType.Guid: "guid",
    t.BuiltInType.ByteString: "bytestring",
    t.BuiltInType.XmlElement: "xml",
    t.BuiltInType.NodeId: "nodeid_numeric",
    t.BuiltInType.ExpandedNodeId: "expnodeid_full",
    t.BuiltInType.StatusCode: "status_bad",
    t.BuiltInType.QualifiedName: "qname",
    t.BuiltInType.LocalizedText: "ltext_full",
    t.BuiltInType.ExtensionObject: "extobj_point",
    t.BuiltInType.DataValue: "datavalue_full",
    t.BuiltInType.Variant: "variant_matrix_int",
    t.BuiltInType.DiagnosticInfo: "diaginfo_nested",
}

COMPOSITE_CASES = [
    ("One-dimensional array", "array_string_with_nulls", "Array: nullable String elements, preserves null array elements."),
    ("Matrix", "matrix_double_2x2_special", "Matrix record: dimensions plus row-major values."),
    ("Structure", "struct_point", "Plain structure: record fields in DataTypeDefinition order."),
    ("Structure with optional fields", "struct_person_present_null", "Optional wrapper distinguishes absent from present-null."),
    ("Union", "union_point", "Union record: switch field plus record-wrapped selected value."),
    ("Worked structured DataType: Envelope", "envelope", "Nested structure with array and subtyped ExtensionObject payload."),
]


def _fresh_named_schemas() -> dict[str, object]:
    named: dict[str, object] = {}
    for schema in json.loads(BUILTINS_SCHEMA.read_text(encoding="utf-8")):
        parse_schema(schema, named_schemas=named)
    return named


def _expand_top_refs(schema: object, named: dict[str, object]) -> object:
    if isinstance(schema, str):
        if schema in named:
            return parse_schema(named[schema], named_schemas=named)
        return schema
    if isinstance(schema, list):
        return [_expand_top_refs(s, named) for s in schema]
    if isinstance(schema, dict):
        return {k: _expand_top_refs(v, named) if k in ("type", "items") else v for k, v in schema.items()}
    return schema


def published_schema(ty: t.Type) -> object:
    named = _fresh_named_schemas()
    if isinstance(ty, (t.Struct, t.Enumeration)):
        path = SCHEMAS / f"{schema_support.avro_name(ty.name)}.avsc"
        return parse_schema(json.loads(path.read_text(encoding="utf-8")), named_schemas=named)
    top = schema_support.schema_for_type(ty, top=True)
    if isinstance(top, str) and top in named:
        return parse_schema(named[top], named_schemas=named)
    return parse_schema(_expand_top_refs(top, named), named_schemas=named)


def raw_fragment(ty: t.Type) -> object:
    if isinstance(ty, (t.Struct, t.Enumeration)):
        return json.loads((SCHEMAS / f"{schema_support.avro_name(ty.name)}.avsc").read_text(encoding="utf-8"))
    top = schema_support.schema_for_type(ty, top=True)
    if isinstance(ty, t.Builtin):
        name = {
            t.BuiltInType.Guid: "Guid",
            t.BuiltInType.NodeId: "NodeId",
            t.BuiltInType.ExpandedNodeId: "ExpandedNodeId",
            t.BuiltInType.QualifiedName: "QualifiedName",
            t.BuiltInType.LocalizedText: "LocalizedText",
            t.BuiltInType.ExtensionObject: "ExtensionObject",
            t.BuiltInType.Variant: "Variant",
            t.BuiltInType.DataValue: "DataValue",
            t.BuiltInType.DiagnosticInfo: "DiagnosticInfo",
        }.get(ty.id)
        if name:
            full = schema_support.fullname(name)
            for s in json.loads(BUILTINS_SCHEMA.read_text(encoding="utf-8")):
                ns = s.get("namespace")
                fn = f"{ns}.{s['name']}" if ns else s["name"]
                if fn == full:
                    return s
    return top


def _jsonable(x: Any) -> Any:
    if dataclasses.is_dataclass(x):
        return {k: _jsonable(vv) for k, vv in dataclasses.asdict(x).items()}
    if isinstance(x, bytes):
        return "0x" + x.hex()
    if isinstance(x, float):
        if math.isnan(x):
            return "NaN"
        if math.isinf(x):
            return "Infinity" if x > 0 else "-Infinity"
        return x
    if isinstance(x, dict):
        return {str(k): _jsonable(vv) for k, vv in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(vv) for vv in x]
    if x is None or isinstance(x, (str, bool, int)):
        return x
    return str(x)


def value_text(value: Any) -> str:
    return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True)


def schema_text(schema: object) -> str:
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True)


def schema_inline(schema: object) -> str:
    return "`" + json.dumps(schema, ensure_ascii=False, sort_keys=True) + "`"


def type_name(ty: t.Type) -> str:
    if isinstance(ty, t.Builtin):
        return ty.id.name
    if isinstance(ty, t.Array):
        return f"ArrayOf{type_name(ty.element)}"
    if isinstance(ty, t.Matrix):
        return f"MatrixOf{type_name(ty.element)}"
    if isinstance(ty, (t.Struct, t.Enumeration)):
        return ty.name
    return type(ty).__name__


@lru_cache(maxsize=1)
def schemaids() -> dict[str, dict[str, str]]:
    return json.loads(SCHEMAIDS.read_text(encoding="utf-8"))


def schemaid_for(ty: t.Type) -> str:
    return schemaids()[type_name(ty)]["schemaid"]


def layout_rows(ty: t.Type, fragment: object, note: str) -> list[tuple[str, str, str, str]]:
    if isinstance(ty, t.Array):
        return [
            ("array", schema_inline(fragment), "array nullable at top level", note),
            ("items", schema_inline(schema_support.schema_for_type(ty.element, ty.allow_null_elements)), "per element as configured", "Avro array blocks are count-prefixed and zero-terminated."),
        ]
    if isinstance(ty, t.Matrix):
        assert isinstance(fragment, list)
        rec = fragment[1]
        return [(f["name"], schema_inline(f["type"]), "record field", "Matrix dimensions then row-major values.") for f in rec["fields"]]
    if isinstance(ty, t.Struct):
        assert isinstance(fragment, dict)
        return [(f["name"], schema_inline(f["type"]), "optional wrapper" if f.get("default") is None and isinstance(f.get("type"), list) else "present", note) for f in fragment["fields"]]
    return [("value", schema_inline(fragment), "nullable where schema is a null union", note)]


def render_item(title: str, case: corpus.Case, note: str) -> str:
    fragment = raw_fragment(case.type)
    data = avro_codec.encode(case.type, case.value)
    fields = wire_annotate.annotate(published_schema(case.type), data)
    hexdump.assert_contiguous(fields, len(data))
    rows = ["| Field | Avro type | Presence / nullability | Notes |", "|---|---|---|---|"]
    for field, avro_type, presence, row_note in layout_rows(case.type, fragment, note):
        rows.append(f"| `{field}` | {avro_type} | {presence} | {row_note} |")
    return "\n".join([
        f"### {title}",
        "",
        f"**SchemaId** `{schemaid_for(case.type)}`",
        "",
        "\n".join(rows),
        "",
        "**Avro schema fragment**",
        "",
        "```json",
        schema_text(fragment),
        "```",
        "",
        f"**Example value** (`{case.name}`)",
        "",
        "```json",
        value_text(case.value),
        "```",
        "",
        f"**Encoded bytes** ({len(data)} bytes)",
        "",
        "```text",
        data.hex(),
        "```",
        "",
        "**Annotated byte-level breakdown**",
        "",
        hexdump.hex_table(data, fields),
        "",
    ])


def _growing_layout_rows(fragment: object) -> list[tuple[str, str, str, str]]:
    assert isinstance(fragment, dict)
    rows: list[tuple[str, str, str, str]] = []
    for f in fragment["fields"]:
        if f["name"] == "body":
            rows.append((
                "body",
                "append-only growing union — see §6.4",
                "nullable",
                "Not expanded here; the full published aggregation is `../extras/avro-encoding/schemas/opcua.builtins.avsc`.",
            ))
            continue
        avro_type = f["type"]
        nullable = isinstance(avro_type, list) and avro_type and avro_type[0] == "null"
        rows.append((
            f["name"],
            schema_inline(avro_type),
            "nullable" if nullable else "present",
            "Fixed member of the record shape.",
        ))
    return rows


def render_growing_item(title: str, case: corpus.Case, note: str) -> str:
    """Render Variant / ExtensionObject without dumping the universal union.

    The body member is the append-only growing union of §6.4; only the fixed
    record shape, a single example and a pointer are shown. SchemaId, bytes and
    the annotated breakdown are still produced from the published aggregation
    schema so they remain exact and reversible.
    """
    fragment = raw_fragment(case.type)
    assert isinstance(fragment, dict)
    body_field = next(f for f in fragment["fields"] if f["name"] == "body")
    has_bytes_fallback = isinstance(body_field["type"], list) and "bytes" in body_field["type"]
    data = avro_codec.encode(case.type, case.value)
    fields = wire_annotate.annotate(published_schema(case.type), data)
    hexdump.assert_contiguous(fields, len(data))
    rows = ["| Field | Avro type | Presence / nullability | Notes |", "|---|---|---|---|"]
    for field, avro_type, presence, row_note in _growing_layout_rows(fragment):
        rows.append(f"| `{field}` | {avro_type} | {presence} | {row_note} |")
    body_note = (
        "The `body` member is the append-only **growing union** governed by §6.4 (see also *OPC UA — Schema Registry* §5.6). "
        "Its members are not reproduced here because the union grows as new "
        + ("built-in body types" if case.type.id == t.BuiltInType.Variant else "concrete DataTypes")
        + " are observed; the complete aggregation used by the conformance corpus is the published `opcua.builtins.avsc`."
    )
    if has_bytes_fallback:
        body_note += " An opaque body that has no known record branch is carried in an opaque fallback branch (`bytes` for a Binary body, `string` for an XML or textual body), appended append-only like any other branch."
    return "\n".join([
        f"### {title}",
        "",
        f"**SchemaId** `{schemaid_for(case.type)}`",
        "",
        "\n".join(rows),
        "",
        body_note,
        "",
        f"**Example value** (`{case.name}`)",
        "",
        "```json",
        value_text(case.value),
        "```",
        "",
        f"**Encoded bytes** ({len(data)} bytes)",
        "",
        "```text",
        data.hex(),
        "```",
        "",
        "**Annotated byte-level breakdown** (the body union index below is into the published aggregation schema)",
        "",
        hexdump.hex_table(data, fields),
        "",
    ])


def reference_cases() -> list[tuple[str, corpus.Case, str]]:
    by_name = {c.name: c for c in corpus.CORPUS}
    items: list[tuple[str, corpus.Case, str]] = []
    for bid in t.BuiltInType:
        name = BUILTIN_CASES[bid]
        items.append((f"Built-in {bid.name}", by_name[name], f"OPC UA BuiltInType {bid.value}."))
    for title, case_name, note in COMPOSITE_CASES:
        items.append((title, by_name[case_name], note))
    return items


def generated_content() -> str:
    lines = [
        "The following reference material is generated from the published `.avsc` schemas and the shared conformance corpus. Do not edit it by hand; run `python ..\\extras\\avro-encoding\\tools\\gen_type_reference.py`.",
        "",
    ]
    for title, case, note in reference_cases():
        if isinstance(case.type, t.Builtin) and case.type.id in (
            t.BuiltInType.Variant,
            t.BuiltInType.ExtensionObject,
        ):
            lines.append(render_growing_item(title, case, note))
        else:
            lines.append(render_item(title, case, note))
    return "\n".join(lines).rstrip() + "\n"


def inject(doc: str, content: str) -> str:
    if BEGIN not in doc or END not in doc:
        block = f"\n\n## Annex A Generated type reference\n\n{BEGIN}\n{content}{END}\n"
        return doc.rstrip() + block
    before, rest = doc.split(BEGIN, 1)
    _old, after = rest.split(END, 1)
    return before + BEGIN + "\n" + content + END + after


def validate_annotations() -> None:
    for _title, case, _note in reference_cases():
        data = avro_codec.encode(case.type, case.value)
        fields = wire_annotate.annotate(published_schema(case.type), data)
        hexdump.assert_contiguous(fields, len(data))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if the committed Part 6 generated block is stale")
    args = ap.parse_args()
    content = generated_content()
    old = PART6.read_text(encoding="utf-8")
    new = inject(old, content)
    if args.check:
        if old != new:
            print("type reference drift: run python ..\\extras\\avro-encoding\\tools\\gen_type_reference.py")
            return 1
        validate_annotations()
        print(f"type reference: {len(reference_cases())} sections checked")
        return 0
    PART6.write_text(new, encoding="utf-8", newline="\n")
    print(f"wrote {len(reference_cases())} generated type-reference sections to {PART6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
