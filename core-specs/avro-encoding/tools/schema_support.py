from __future__ import annotations

import os
import re
from typing import Any

NS = "org.opcfoundation.ua.avro"


def common_path(*parts: str) -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common", *parts))


def repo_path(*parts: str) -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", *parts))


def load_common() -> None:
    import sys
    p = common_path()
    if p not in sys.path:
        sys.path.insert(0, p)


def avro_name(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", name or "Type")
    if not re.match(r"[A-Za-z_]", s):
        s = "T_" + s
    return s


def fullname(name: str) -> str:
    return f"{NS}.{avro_name(name)}"


def stable_json(data: Any) -> str:
    import json
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def nullable(schema: Any) -> list[Any]:
    return ["null", schema]


def is_nullable_builtin(bid: Any) -> bool:
    from opcua_enc import types as t

    return bid in (
        t.BuiltInType.String,
        t.BuiltInType.ByteString,
        t.BuiltInType.XmlElement,
        t.BuiltInType.LocalizedText,
        t.BuiltInType.NodeId,
        t.BuiltInType.ExpandedNodeId,
        t.BuiltInType.QualifiedName,
        t.BuiltInType.ExtensionObject,
    )


def node_id_schema() -> dict[str, Any]:
    return {"type": "record", "name": "NodeId", "namespace": NS, "fields": [
        {"name": "namespace", "type": "int"},
        {"name": "idType", "type": "int"},
        {"name": "numeric", "type": nullable("long"), "default": None},
        {"name": "string", "type": nullable("string"), "default": None},
        {"name": "guid", "type": nullable({"type": "fixed", "name": "Guid", "namespace": NS, "size": 16, "logicalType": "opcua-guid"}), "default": None},
        {"name": "opaque", "type": nullable("bytes"), "default": None},
    ]}


def type_key(ty: Any) -> str:
    from opcua_enc import types as t

    if isinstance(ty, t.Builtin): return ty.id.name
    if isinstance(ty, t.Array): return "ArrayOf" + type_key(ty.element)
    if isinstance(ty, t.Matrix): return "MatrixOf" + type_key(ty.element)
    if isinstance(ty, (t.Struct, t.Enumeration)): return ty.name
    return "Type"


def schema_for_type(ty: Any, optional: bool = False, *, top: bool = False) -> Any:
    from opcua_enc import types as t

    if isinstance(ty, t.Array):
        out = {"type": "array", "items": schema_for_type(ty.element, ty.allow_null_elements)}
        return nullable(out) if optional or top else out
    if isinstance(ty, t.Matrix):
        name = avro_name(("TopMatrixOf" if top else "MatrixOf") + type_key(ty.element))
        out = {"type": "record", "name": name, "namespace": NS, "fields": [
            {"name": "dimensions", "type": {"type": "array", "items": "int"}},
            {"name": "values", "type": {"type": "array", "items": schema_for_type(ty.element, ty.allow_null_elements)}}]}
        return nullable(out) if optional or top else out
    if isinstance(ty, t.Enumeration):
        return nullable("int") if optional else "int"
    if isinstance(ty, t.Struct):
        ref = fullname(ty.name)
        return nullable(ref) if optional else ref

    B = t.BuiltInType
    bid = ty.id
    s: Any
    if bid == B.Boolean: s = "boolean"
    elif bid in (B.SByte, B.Byte, B.Int16, B.UInt16, B.Int32, B.UInt32): s = "int"
    elif bid in (B.Int64, B.UInt64, B.DateTime): s = "long"
    elif bid == B.Float: s = "float"
    elif bid == B.Double: s = "double"
    elif bid in (B.String, B.XmlElement): s = "string"
    elif bid == B.Guid: s = fullname("Guid")
    elif bid == B.ByteString: s = "bytes"
    elif bid == B.NodeId: s = fullname("NodeId")
    elif bid == B.ExpandedNodeId: s = fullname("ExpandedNodeId")
    elif bid == B.StatusCode: s = "int"
    elif bid == B.QualifiedName: s = fullname("QualifiedName")
    elif bid == B.LocalizedText: s = fullname("LocalizedText")
    elif bid == B.ExtensionObject: s = fullname("ExtensionObject")
    elif bid == B.Variant: s = fullname("Variant")
    elif bid == B.DataValue: s = fullname("DataValue")
    elif bid == B.DiagnosticInfo: s = fullname("DiagnosticInfo")
    else: raise ValueError(bid)
    return nullable(s) if optional or is_nullable_builtin(bid) or (top and bid in (B.String, B.ByteString, B.XmlElement, B.LocalizedText)) else s


def optional_field_schema(struct_name: str, field_name: str, value_type: Any) -> list[Any]:
    wrapper = {
        "type": "record",
        "name": avro_name(f"{struct_name}_{field_name}_Optional"),
        "namespace": NS,
        "fields": [{"name": "value", "type": value_type}],
    }
    return nullable(wrapper)


def datatype_schema(ty: Any) -> Any:
    from opcua_enc import types as t

    if isinstance(ty, t.Enumeration):
        return "int"
    assert isinstance(ty, t.Struct)
    if ty.kind == t.StructureKind.UNION:
        branches: list[Any] = ["null"]
        for f in ty.fields:
            branches.append({"type": "record", "name": avro_name(f"{ty.name}_{f.name}_Branch"), "namespace": NS, "fields": [{"name": f.name, "type": schema_for_type(f.type)}]})
        return {"type": "record", "name": avro_name(ty.name), "namespace": NS, "fields": [
            {"name": "switch", "type": nullable("string"), "default": None},
            {"name": "value", "type": branches, "default": None}]}
    fields = []
    for f in ty.fields:
        value_schema = schema_for_type(f.type)
        if f.is_optional:
            fields.append({"name": avro_name(f.name), "type": optional_field_schema(ty.name, f.name, value_schema), "default": None})
        else:
            fields.append({"name": avro_name(f.name), "type": value_schema})
    return {"type": "record", "name": avro_name(ty.name), "namespace": NS, "fields": fields}


def variant_branch_defs() -> list[dict[str, Any]]:
    from opcua_enc import types as t

    defs: list[dict[str, Any]] = []
    for bt in t.VARIANT_BODY_TYPES:
        key = bt.id.name
        scalar = schema_for_type(bt)
        array = {"type": "array", "items": schema_for_type(bt, optional=is_nullable_builtin(bt.id))}
        matrix = {"type": "record", "name": avro_name(f"Variant{key}Matrix"), "namespace": NS, "fields": [
            {"name": "dimensions", "type": {"type": "array", "items": "int"}},
            {"name": "values", "type": {"type": "array", "items": schema_for_type(bt, optional=is_nullable_builtin(bt.id))}}]}
        defs.append({"type": "record", "name": avro_name(f"Variant{key}Scalar"), "namespace": NS, "fields": [{"name": "value", "type": scalar}]})
        defs.append({"type": "record", "name": avro_name(f"Variant{key}Array"), "namespace": NS, "fields": [{"name": "values", "type": array}]})
        defs.append(matrix)
        defs.append({"type": "record", "name": avro_name(f"Variant{key}MatrixBody"), "namespace": NS, "fields": [{"name": "matrix", "type": fullname(f"Variant{key}Matrix")}]})
    return defs


def variant_body_union() -> list[Any]:
    from opcua_enc import types as t

    u: list[Any] = ["null"]
    for bt in t.VARIANT_BODY_TYPES:
        key = bt.id.name
        u.extend([fullname(f"Variant{key}Scalar"), fullname(f"Variant{key}Array"), fullname(f"Variant{key}MatrixBody")])
    return u


def builtin_defs(known_structs: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    struct_union: list[Any] = ["null"]
    struct_union.extend(datatype_schema(s) for s in known_structs)
    struct_union.append("bytes")
    return [
        node_id_schema(),
        {"type": "record", "name": "ExpandedNodeId", "namespace": NS, "fields": [
            {"name": "nodeId", "type": fullname("NodeId")},
            {"name": "namespaceUri", "type": nullable("string"), "default": None},
            {"name": "serverIndex", "type": "long", "default": 0}]},
        {"type": "record", "name": "QualifiedName", "namespace": NS, "fields": [
            {"name": "namespace", "type": "int"}, {"name": "name", "type": nullable("string"), "default": None}]},
        {"type": "record", "name": "LocalizedText", "namespace": NS, "fields": [
            {"name": "locale", "type": nullable("string"), "default": None}, {"name": "text", "type": nullable("string"), "default": None}]},
        {"type": "record", "name": "ExtensionObject", "namespace": NS, "fields": [
            {"name": "typeId", "type": fullname("NodeId")},
            {"name": "body", "type": struct_union, "default": None, "doc": "Known ExtensionObject bodies use typed record branches; bytes is reserved for genuinely unknown type ids."}]},
        *variant_branch_defs(),
        {"type": "record", "name": "Variant", "namespace": NS, "fields": [
            {"name": "builtInType", "type": "int"},
            {"name": "dimensions", "type": nullable({"type": "array", "items": "int"}), "default": None},
            {"name": "body", "type": variant_body_union(), "default": None}]},
        {"type": "record", "name": "DataValue", "namespace": NS, "fields": [
            {"name": "value", "type": nullable(fullname("Variant")), "default": None},
            {"name": "status", "type": nullable("int"), "default": None},
            {"name": "sourceTimestamp", "type": nullable("long"), "default": None},
            {"name": "sourcePicoseconds", "type": nullable("int"), "default": None},
            {"name": "serverTimestamp", "type": nullable("long"), "default": None},
            {"name": "serverPicoseconds", "type": nullable("int"), "default": None}]},
        {"type": "record", "name": "DiagnosticInfo", "namespace": NS, "fields": [
            {"name": "symbolicId", "type": nullable("int"), "default": None},
            {"name": "namespaceUri", "type": nullable("int"), "default": None},
            {"name": "locale", "type": nullable("int"), "default": None},
            {"name": "localizedText", "type": nullable("int"), "default": None},
            {"name": "additionalInfo", "type": nullable("string"), "default": None},
            {"name": "innerStatusCode", "type": nullable("int"), "default": None},
            {"name": "innerDiagnosticInfo", "type": nullable("DiagnosticInfo"), "default": None}]},
        {"type": "record", "name": "DataSetMessage", "namespace": NS, "fields": [
            {"name": "messageType", "type": {"type": "enum", "name": "DataSetMessageType", "namespace": NS, "symbols": ["KeyFrame", "DeltaFrame"]}},
            {"name": "writerId", "type": "int"},
            {"name": "sequenceNumber", "type": nullable("long"), "default": None},
            {"name": "status", "type": nullable("int"), "default": None},
            {"name": "timestamp", "type": nullable("long"), "default": None},
            {"name": "fields", "type": {"type": "array", "items": fullname("Variant")}}]},
        {"type": "record", "name": "NetworkMessage", "namespace": NS, "fields": [
            {"name": "publisherId", "type": nullable("string"), "default": None},
            {"name": "groupHeader", "type": nullable("bytes"), "default": None},
            {"name": "payload", "type": {"type": "array", "items": fullname("DataSetMessage")}}]},
    ]
