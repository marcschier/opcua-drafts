from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STD = (HERE / ".." / ".." / ".." / "protobuf-encoding").resolve()
TOOLS = ROOT / "tools"
SCHEMAS = ROOT / "schemas"
STD_SCHEMAS = STD / "schemas"
PART6 = STD / "OPC-UA-Part6-Protobuf-DataEncoding.md"
SCHEMAIDS = SCHEMAS / "schemaids.json"
ALGORITHM = "SHA-256 over transitive FileDescriptorSet"
sys.path.insert(0, os.path.abspath(ROOT / ".." / "_common"))
from opcua_enc import corpus, fingerprint, hexdump, types as t  # noqa: E402
import build_schemas  # noqa: E402
import protobuf_codec  # noqa: E402
import wire_annotate  # noqa: E402

BEGIN = "<!-- BEGIN GENERATED: type-reference -->"
END = "<!-- END GENERATED: type-reference -->"


def _safe_name(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not s or s[0].isdigit():
        s = "_" + s
    return s


def _type_name(ty: t.Type) -> str:
    if isinstance(ty, t.Builtin):
        return ty.id.name
    if isinstance(ty, t.Array):
        return f"Array<{_type_name(ty.element)}>"
    if isinstance(ty, t.Matrix):
        return f"Matrix<{_type_name(ty.element)}>"
    if isinstance(ty, t.Struct):
        return ty.name
    if isinstance(ty, t.Enumeration):
        return ty.name
    return str(ty)


def _case(name: str) -> corpus.Case:
    return next(c for c in corpus.CORPUS if c.name == name)


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
    t.BuiltInType.Double: "double_tiny",
    t.BuiltInType.String: "string_unicode",
    t.BuiltInType.DateTime: "datetime_now",
    t.BuiltInType.Guid: "guid",
    t.BuiltInType.ByteString: "bytestring",
    t.BuiltInType.XmlElement: "xml",
    t.BuiltInType.NodeId: "nodeid_guid",
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
    ("Array with nullable elements", "array_string_with_nulls"),
    ("Matrix", "matrix_double_2x2_special"),
    ("Structure", "struct_point"),
    ("Structure with optional fields", "struct_person_one_opt"),
    ("Optional scalar presence", "optscalars_zero_present"),
    ("Optional Float presence", "floatholder_full"),
    ("Union oneof", "union_point"),
    ("Worked structured DataType: Envelope", "envelope"),
]


def _message_descriptor(ty: t.Type) -> Any:
    if isinstance(ty, t.Struct):
        mod = importlib.import_module(f"{_safe_name(ty.name).lower()}_pb2")
        return getattr(mod, _safe_name(ty.name)).DESCRIPTOR
    import opcua_builtins_pb2 as pb
    return pb.Value.DESCRIPTOR


def _file_proto(file_desc: Any) -> Any:
    from google.protobuf import descriptor_pb2

    fdp = descriptor_pb2.FileDescriptorProto()
    fdp.ParseFromString(file_desc.serialized_pb)
    fdp.ClearField("source_code_info")
    return fdp


def _collect_files(file_desc: Any) -> Any:
    from google.protobuf import descriptor_pb2

    seen: set[str] = set()
    ordered: list[Any] = []

    def visit(fd: Any) -> None:
        if fd.name in seen:
            return
        for dep in sorted(fd.dependencies, key=lambda d: d.name):
            visit(dep)
        seen.add(fd.name)
        ordered.append(_file_proto(fd))

    visit(file_desc)
    fds = descriptor_pb2.FileDescriptorSet()
    fds.file.extend(ordered)
    return fds


def _schema_id(desc: Any) -> str:
    from google.protobuf import descriptor_pb2

    if isinstance(desc, descriptor_pb2.FileDescriptorSet):
        fds = desc
    elif isinstance(desc, descriptor_pb2.FileDescriptorProto):
        fds = descriptor_pb2.FileDescriptorSet()
        fds.file.append(desc)
    else:
        file_desc = desc.file if hasattr(desc, "file") else desc
        fds = _collect_files(file_desc)
    return fingerprint.sha256_id_hex(fds.SerializeToString(deterministic=True))


def _field_proto_type(fd: Any) -> str:
    from google.protobuf.descriptor import FieldDescriptor

    if fd.message_type:
        return fd.message_type.full_name
    if fd.enum_type:
        return fd.enum_type.full_name
    return {
        FieldDescriptor.TYPE_DOUBLE: "double",
        FieldDescriptor.TYPE_FLOAT: "float",
        FieldDescriptor.TYPE_INT64: "int64",
        FieldDescriptor.TYPE_UINT64: "uint64",
        FieldDescriptor.TYPE_INT32: "int32",
        FieldDescriptor.TYPE_FIXED64: "fixed64",
        FieldDescriptor.TYPE_FIXED32: "fixed32",
        FieldDescriptor.TYPE_BOOL: "bool",
        FieldDescriptor.TYPE_STRING: "string",
        FieldDescriptor.TYPE_BYTES: "bytes",
        FieldDescriptor.TYPE_UINT32: "uint32",
        FieldDescriptor.TYPE_SFIXED32: "sfixed32",
        FieldDescriptor.TYPE_SFIXED64: "sfixed64",
        FieldDescriptor.TYPE_SINT32: "sint32",
        FieldDescriptor.TYPE_SINT64: "sint64",
    }[fd.type]


def _builtin_field(ty: t.Builtin) -> tuple[str, str]:
    field = protobuf_codec._VALUE_FIELD.get(ty.id)
    if field is None:
        if ty.id == t.BuiltInType.String:
            field = "string_value"
        elif ty.id == t.BuiltInType.ByteString:
            field = "bytestring_value"
        else:
            raise KeyError(ty.id)
    desc = _message_descriptor(ty)
    fd = desc.fields_by_name[field]
    return field, _field_proto_type(fd)


def _table_for(ty: t.Type) -> str:
    rows = ["| Field | proto3 type/label | Presence | Notes |", "|---|---|---|---|"]
    if isinstance(ty, t.Builtin):
        field, ptype = _builtin_field(ty)
        rows.append(f"| `{field}` | `{ptype}` in `Value.kind` | selected `oneof` arm | BuiltInType `{ty.id.value}`. |")
    elif isinstance(ty, t.Array):
        rows.append("| `array_value.values` | `repeated Value` | containing `Value.kind`; each element wrapper present | Empty element wrapper is a null element. |")
    elif isinstance(ty, t.Matrix):
        rows.append("| `matrix_value.dimensions` | `repeated int32` | present matrix | Row-major dimensions. |")
        rows.append("| `matrix_value.values` | `repeated Value` | present matrix | Count shall equal product of dimensions. |")
    elif isinstance(ty, t.Struct):
        if ty.kind == t.StructureKind.UNION:
            rows.append("| `value` | `oneof` | zero or one selected arm | Field numbers follow DataTypeDefinition order. |")
        for i, fld in enumerate(ty.fields, 1):
            presence = "optional" if fld.is_optional else ("oneof arm" if ty.kind == t.StructureKind.UNION else "present for mandatory fields")
            rows.append(f"| `{protobuf_codec._field_name(fld.name)}` | `{_type_name(fld.type)}` = {i} | {presence} | DataTypeDefinition field `{fld.name}`. |")
    return "\n".join(rows)


def _proto_snippet(ty: t.Type) -> str:
    if isinstance(ty, t.Struct):
        return (SCHEMAS / f"{_safe_name(ty.name).lower()}.proto").read_text(encoding="utf-8").strip()
    if isinstance(ty, t.Array):
        return "message ArrayValue {\n  repeated Value values = 1;\n}"
    if isinstance(ty, t.Matrix):
        return "message MatrixValue {\n  repeated int32 dimensions = 1;\n  repeated Value values = 2;\n}"
    assert isinstance(ty, t.Builtin)
    field, _ = _builtin_field(ty)
    fd = _message_descriptor(ty).fields_by_name[field]
    type_name = _field_proto_type(fd)
    return f"message Value {{\n  oneof kind {{\n    {type_name} {field} = {fd.number};\n  }}\n}}"


def _schema_reference(ty: t.Type) -> str:
    if isinstance(ty, t.Struct):
        filename = f"{_safe_name(ty.name).lower()}.proto"
        return f"Schema file: [`{filename}`](../extras/protobuf-encoding/schemas/{filename})"
    return "Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)"


def _section(title: str, case: corpus.Case) -> str:
    data = protobuf_codec.encode(case.type, case.value)
    desc = _message_descriptor(case.type)
    fields = wire_annotate.annotate(data, desc)
    hexdump.assert_contiguous(fields, len(data))
    return "\n".join(
        [
            f"### {title}",
            "",
            _table_for(case.type),
            "",
            f"SchemaId: `{_schema_id(desc)}`",
            "",
            _schema_reference(case.type),
            "",
            "```proto",
            _proto_snippet(case.type),
            "```",
            "",
            f"Example corpus case: `{case.name}`",
            "",
            "```text",
            repr(case.value),
            "```",
            "",
            f"Encoded bytes: `{data.hex() or '∅'}`",
            "",
            hexdump.hex_table(data, fields),
            "",
        ]
    )


def generate() -> str:
    build_schemas.main()
    protobuf_codec.reload_generated()
    lines = [
        "## Annex A — Generated Protobuf type reference",
        "",
        BEGIN,
        "",
        "This annex is generated by `../extras/protobuf-encoding/tools/gen_type_reference.py`; edit the generator, not this block.",
        "",
    ]
    for bid in t.BuiltInType:
        case = _case(BUILTIN_CASES[bid])
        lines.append(_section(f"Built-in {bid.name}", case))
    for title, case_name in COMPOSITE_CASES:
        lines.append(_section(title, _case(case_name)))
    lines += [END, ""]
    return "\n".join(lines)


def _schema_entry(desc: Any) -> dict[str, str]:
    return {"schemaid": _schema_id(desc), "algorithm": ALGORITHM}


def generate_schemaids() -> dict[str, dict[str, str]]:
    build_schemas.main()
    protobuf_codec.reload_generated()
    import opcua_builtins_pb2 as pb

    out: dict[str, dict[str, str]] = {}
    value_entry = _schema_entry(pb.Value.DESCRIPTOR)
    for bid in t.BuiltInType:
        out[bid.name] = dict(value_entry)

    out["Array"] = _schema_entry(pb.ArrayValue.DESCRIPTOR)
    out["ArrayNullableElement"] = _schema_entry(pb.Value.DESCRIPTOR)
    out["Matrix"] = _schema_entry(pb.MatrixValue.DESCRIPTOR)
    out["Variant"] = _schema_entry(pb.Variant.DESCRIPTOR)
    out["AbstractSubtype"] = _schema_entry(pb.ExtensionObject.DESCRIPTOR)

    representative = {
        "Structure": corpus.POINT,
        "StructureWithOptionalFields": corpus.PERSON,
        "UnionOneof": corpus.MEASUREMENT,
        "WorkedStructuredDataType": corpus.ENVELOPE,
    }
    for name, st in representative.items():
        out[name] = _schema_entry(_message_descriptor(st))

    structs, enums = build_schemas.collect_types()
    for st in sorted(structs, key=lambda s: s.name):
        out[st.name] = _schema_entry(_message_descriptor(st))
    for enum in sorted(enums, key=lambda e: e.name):
        mod = importlib.import_module(f"{_safe_name(enum.name).lower()}_pb2")
        out[enum.name] = _schema_entry(mod.DESCRIPTOR)

    return {k: out[k] for k in sorted(out)}


def schemaids_text() -> str:
    return json.dumps(generate_schemaids(), indent=2, sort_keys=True) + "\n"


def inject(doc: str, generated: str) -> str:
    pattern = re.compile(r"## Annex A — Generated Protobuf type reference\n\n<!-- BEGIN GENERATED: type-reference -->.*?<!-- END GENERATED: type-reference -->\n?", re.S)
    if pattern.search(doc):
        return pattern.sub(lambda _m: generated.rstrip() + "\n", doc)
    return doc.rstrip() + "\n\n" + generated.rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if the generated annex differs from the document")
    args = parser.parse_args()
    generated = generate()
    schemaids = schemaids_text()
    current = PART6.read_text(encoding="utf-8")
    updated = inject(current, generated)
    if args.check:
        failures = 0
        if current != updated:
            print("FAIL Part 6 type-reference annex is out of date")
            failures += 1
        if not SCHEMAIDS.exists() or SCHEMAIDS.read_text(encoding="utf-8") != schemaids:
            print("FAIL schemas\\schemaids.json is out of date")
            failures += 1
        if failures:
            return 1
        print("type-reference and schemaids: up to date")
        return 0
    PART6.write_text(updated, encoding="utf-8", newline="\n")
    SCHEMAIDS.write_text(schemaids, encoding="utf-8", newline="\n")
    print(f"updated {PART6}")
    print(f"updated {SCHEMAIDS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
