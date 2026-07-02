from __future__ import annotations

import os
import importlib
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GEN = HERE / "_generated"
sys.path.insert(0, os.path.abspath(HERE / ".." / ".." / "_common"))
from opcua_enc import corpus as _corpus, types as t, values as v  # noqa: E402


class TypeRegistry:
    def __init__(self, structs: tuple[t.Struct, ...] | list[t.Struct]):
        self._by_key: dict[tuple[int, int, Any], t.Struct] = {}
        self._by_name: dict[str, t.Struct] = {}
        for s in structs:
            self._by_name[s.name] = s
            if s.type_id:
                self._by_key[self._parse(s.type_id)] = s

    @staticmethod
    def _parse(node_id: str) -> tuple[int, int, Any]:
        if node_id.startswith("i="):
            return (0, int(v.IdType.NUMERIC), int(node_id[2:]))
        if node_id.startswith("ns=") and ";i=" in node_id:
            ns, ident = node_id.split(";i=", 1)
            return (int(ns[3:]), int(v.IdType.NUMERIC), int(ident))
        raise ValueError(f"unsupported NodeId literal {node_id!r}")

    def resolve(self, node_id: v.NodeId) -> t.Struct:
        return self._by_key[(node_id.namespace, int(node_id.id_type), node_id.identifier)]


DEFAULT_REGISTRY = TypeRegistry(_corpus.STRUCT_TYPES)


def _compile_if_needed() -> None:
    target = GEN / "opcua_builtins_pb2.py"
    protos = list((ROOT / "schemas").glob("*.proto"))
    if target.exists() and protos and target.stat().st_mtime >= max(p.stat().st_mtime for p in protos):
        return
    from build_schemas import main as build_main
    build_main()
    GEN.mkdir(parents=True, exist_ok=True)
    proto_files = [str(p) for p in sorted((ROOT / "schemas").glob("*.proto"))]
    try:
        import grpc_tools.protoc  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("grpcio-tools is required: pip install grpcio-tools") from exc
    cmd = [sys.executable, "-m", "grpc_tools.protoc", f"-I{ROOT / 'schemas'}", f"--python_out={GEN}", *proto_files]
    rc = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    if rc.returncode:
        raise RuntimeError(rc.stdout + rc.stderr)


_compile_if_needed()
sys.path.insert(0, str(GEN))
import opcua_builtins_pb2 as pb  # noqa: E402


def reload_generated() -> None:
    global pb
    importlib.invalidate_caches()
    pb = importlib.reload(pb)
    for path in sorted(GEN.glob("*_pb2.py")):
        name = path.stem
        if name != "opcua_builtins_pb2" and name in sys.modules:
            importlib.reload(sys.modules[name])


def _safe_name(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not s or s[0].isdigit():
        s = "_" + s
    return s


def _field_name(name: str) -> str:
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s).lower()
    return _safe_name(s)


def _message_class(ty: t.Struct) -> Any:
    module = importlib.import_module(f"{_safe_name(ty.name).lower()}_pb2")
    return getattr(module, _safe_name(ty.name))


_VALUE_FIELD = {
    t.BuiltInType.Boolean: "boolean_value",
    t.BuiltInType.SByte: "sbyte_value",
    t.BuiltInType.Byte: "byte_value",
    t.BuiltInType.Int16: "int16_value",
    t.BuiltInType.UInt16: "uint16_value",
    t.BuiltInType.Int32: "int32_value",
    t.BuiltInType.UInt32: "uint32_value",
    t.BuiltInType.Int64: "int64_value",
    t.BuiltInType.UInt64: "uint64_value",
    t.BuiltInType.Float: "float_value",
    t.BuiltInType.Double: "double_value",
    t.BuiltInType.DateTime: "datetime_value",
    t.BuiltInType.Guid: "guid_value",
    t.BuiltInType.XmlElement: "xml_element_value",
    t.BuiltInType.NodeId: "node_id_value",
    t.BuiltInType.ExpandedNodeId: "expanded_node_id_value",
    t.BuiltInType.StatusCode: "status_code_value",
    t.BuiltInType.QualifiedName: "qualified_name_value",
    t.BuiltInType.LocalizedText: "localized_text_value",
    t.BuiltInType.ExtensionObject: "extension_object_value",
    t.BuiltInType.Variant: "variant_value",
    t.BuiltInType.DataValue: "data_value",
    t.BuiltInType.DiagnosticInfo: "diagnostic_info_value",
}


def encode(ty: t.Type, value: Any, reg: TypeRegistry = DEFAULT_REGISTRY) -> bytes:
    msg = _encode_struct_message(ty, value, reg) if isinstance(ty, t.Struct) else _encode_value(ty, value, reg)
    return msg.SerializeToString(deterministic=True)


def decode(ty: t.Type, data: bytes, reg: TypeRegistry = DEFAULT_REGISTRY) -> Any:
    if isinstance(ty, t.Struct):
        msg = _message_class(ty)()
        msg.ParseFromString(data)
        return _decode_struct_message(ty, msg, reg)
    msg = pb.Value()
    msg.ParseFromString(data)
    return _decode_value(ty, msg, reg)


def _encode_value(ty: t.Type, val: Any, reg: TypeRegistry) -> pb.Value:
    out = pb.Value()
    if isinstance(ty, t.Array):
        if val is None:
            return out
        arr = pb.ArrayValue()
        for item in val:
            arr.values.append(pb.Value() if item is None else _encode_value(ty.element, item, reg))
        out.array_value.CopyFrom(arr)
        return out
    if isinstance(ty, t.Matrix):
        if val is None:
            return out
        mat = pb.MatrixValue(dimensions=list(val.dimensions))
        for item in val.values:
            mat.values.append(pb.Value() if item is None else _encode_value(ty.element, item, reg))
        out.matrix_value.CopyFrom(mat)
        return out
    if isinstance(ty, t.Enumeration):
        out.enum_value = int(val)
        return out
    if isinstance(ty, t.Struct):
        msg = _encode_struct_message(ty, val, reg)
        out.message_value.Pack(msg)
        return out
    assert isinstance(ty, t.Builtin), ty
    return _encode_builtin(ty.id, val, reg)


def _encode_builtin(bid: t.BuiltInType, val: Any, reg: TypeRegistry) -> pb.Value:
    out = pb.Value()
    B = t.BuiltInType
    if val is None and bid in (B.String, B.ByteString):
        return out
    if bid == B.Boolean:
        out.boolean_value = bool(val)
    elif bid == B.SByte:
        out.sbyte_value = int(val)
    elif bid == B.Byte:
        out.byte_value = int(val)
    elif bid == B.Int16:
        out.int16_value = int(val)
    elif bid == B.UInt16:
        out.uint16_value = int(val)
    elif bid == B.Int32:
        out.int32_value = int(val)
    elif bid == B.UInt32:
        out.uint32_value = int(val)
    elif bid == B.Int64:
        out.int64_value = int(val)
    elif bid == B.UInt64:
        out.uint64_value = int(val)
    elif bid == B.Float:
        out.float_value = float(val)
    elif bid == B.Double:
        out.double_value = float(val)
    elif bid == B.String:
        out.string_value = val
    elif bid == B.DateTime:
        out.datetime_value = val.ticks
    elif bid == B.Guid:
        out.guid_value = val.bytes
    elif bid == B.ByteString:
        out.bytestring_value = val
    elif bid == B.XmlElement:
        x = pb.XmlElementValue()
        if val.value is not None:
            x.value = val.value
        out.xml_element_value.CopyFrom(x)
    elif bid == B.NodeId:
        out.node_id_value.CopyFrom(_encode_nodeid(val))
    elif bid == B.ExpandedNodeId:
        ex = pb.ExpandedNodeId(node_id=_encode_nodeid(val.node_id), server_index=val.server_index)
        if val.namespace_uri is not None:
            ex.namespace_uri = val.namespace_uri
        out.expanded_node_id_value.CopyFrom(ex)
    elif bid == B.StatusCode:
        out.status_code_value = val.value
    elif bid == B.QualifiedName:
        q = pb.QualifiedName(namespace=val.namespace)
        if val.name is not None:
            q.name = val.name
        out.qualified_name_value.CopyFrom(q)
    elif bid == B.LocalizedText:
        lt = pb.LocalizedText()
        if val.locale is not None:
            lt.locale = val.locale
        if val.text is not None:
            lt.text = val.text
        out.localized_text_value.CopyFrom(lt)
    elif bid == B.ExtensionObject:
        out.extension_object_value.CopyFrom(_encode_extobj(val, reg))
    elif bid == B.Variant:
        out.variant_value.CopyFrom(_encode_variant(val, reg))
    elif bid == B.DataValue:
        out.data_value.CopyFrom(_encode_datavalue(val, reg))
    elif bid == B.DiagnosticInfo:
        out.diagnostic_info_value.CopyFrom(_encode_diag(val))
    else:
        raise ValueError(f"unhandled builtin {bid}")
    return out


def _encode_nodeid(n: v.NodeId) -> pb.NodeId:
    out = pb.NodeId(namespace=n.namespace, id_type=int(n.id_type))
    if n.id_type == v.IdType.NUMERIC:
        out.numeric = int(n.identifier)
    elif n.id_type == v.IdType.STRING:
        out.string = n.identifier
    elif n.id_type == v.IdType.GUID:
        out.guid = n.identifier.bytes
    elif n.id_type == v.IdType.OPAQUE:
        out.opaque = n.identifier
    return out


def _encode_struct_message(ty: t.Struct, val: Any, reg: TypeRegistry) -> Any:
    if ty.kind == t.StructureKind.UNION:
        return _encode_union_message(ty, val, reg)
    if not isinstance(val, v.StructValue):
        raise TypeError(f"expected StructValue for {ty.name}")
    out = _message_class(ty)()
    for fld in ty.fields:
        if fld.name in val.fields:
            _assign_field(out, _field_name(fld.name), fld.type, val.fields[fld.name], reg)
        elif not fld.is_optional:
            raise ValueError(f"missing mandatory field {ty.name}.{fld.name}")
    return out


def _encode_union_message(ty: t.Struct, val: v.UnionValue, reg: TypeRegistry) -> Any:
    out = _message_class(ty)()
    if val.field_name is None:
        return out
    fld = next(f for f in ty.fields if f.name == val.field_name)
    _assign_field(out, _field_name(fld.name), fld.type, val.value, reg)
    return out


def _assign_field(msg: Any, name: str, ty: t.Type, val: Any, reg: TypeRegistry) -> None:
    encoded = _encode_field_value(ty, val, reg)
    if encoded is None:
        return
    if hasattr(encoded, "DESCRIPTOR"):
        getattr(msg, name).CopyFrom(encoded)
    else:
        setattr(msg, name, encoded)


def _encode_field_value(ty: t.Type, val: Any, reg: TypeRegistry) -> Any:
    if isinstance(ty, t.Array):
        if val is None:
            return None
        arr = pb.ArrayValue()
        for item in val:
            arr.values.append(pb.Value() if item is None else _encode_value(ty.element, item, reg))
        return arr
    if isinstance(ty, t.Matrix):
        if val is None:
            return None
        mat = pb.MatrixValue(dimensions=list(val.dimensions))
        for item in val.values:
            mat.values.append(pb.Value() if item is None else _encode_value(ty.element, item, reg))
        return mat
    if isinstance(ty, t.Struct):
        return _encode_struct_message(ty, val, reg)
    if isinstance(ty, t.Enumeration):
        return int(val)
    assert isinstance(ty, t.Builtin), ty
    if ty.id == t.BuiltInType.String:
        out = pb.StringValue()
        if val is not None:
            out.value = val
        return out
    if ty.id == t.BuiltInType.ByteString:
        out = pb.ByteStringValue()
        if val is not None:
            out.value = val
        return out
    return _encode_builtin_field(ty.id, val, reg)


def _encode_builtin_field(bid: t.BuiltInType, val: Any, reg: TypeRegistry) -> Any:
    return getattr(_encode_builtin(bid, val, reg), _VALUE_FIELD[bid])


def _encode_extobj(eo: v.ExtensionObject, reg: TypeRegistry) -> pb.ExtensionObject:
    out = pb.ExtensionObject(type_id=_encode_nodeid(eo.type_id))
    if eo.body is not None:
        out.message_body.Pack(_encode_struct_message(reg.resolve(eo.type_id), eo.body, reg))
    return out


def _encode_variant(var: v.Variant, reg: TypeRegistry) -> pb.Variant:
    out = pb.Variant()
    if var.vtype is None:
        return out
    if not isinstance(var.vtype, t.Builtin):
        raise ValueError("this reference codec supports built-in Variant body types")
    out.built_in_type = int(var.vtype.id)
    if isinstance(var.value, list):
        if var.dimensions is None:
            arr = pb.ArrayValue()
            for item in var.value:
                arr.values.append(pb.Value() if item is None else _encode_builtin(var.vtype.id, item, reg))
            out.array.CopyFrom(arr)
        else:
            mat = pb.MatrixValue(dimensions=list(var.dimensions))
            for item in var.value:
                mat.values.append(pb.Value() if item is None else _encode_builtin(var.vtype.id, item, reg))
            out.matrix.CopyFrom(mat)
    else:
        out.scalar.CopyFrom(_encode_builtin(var.vtype.id, var.value, reg))
    return out


def _encode_datavalue(dv: v.DataValue, reg: TypeRegistry) -> pb.DataValue:
    out = pb.DataValue()
    if dv.value is not None:
        out.value.CopyFrom(_encode_variant(dv.value, reg))
    if dv.status is not None:
        out.status = dv.status.value
    if dv.source_timestamp is not None:
        out.source_timestamp = dv.source_timestamp.ticks
    if dv.source_picoseconds is not None:
        out.source_picoseconds = dv.source_picoseconds
    if dv.server_timestamp is not None:
        out.server_timestamp = dv.server_timestamp.ticks
    if dv.server_picoseconds is not None:
        out.server_picoseconds = dv.server_picoseconds
    return out


def _encode_diag(d: v.DiagnosticInfo) -> pb.DiagnosticInfo:
    out = pb.DiagnosticInfo()
    if d.symbolic_id is not None:
        out.symbolic_id = d.symbolic_id
    if d.namespace_uri is not None:
        out.namespace_uri = d.namespace_uri
    if d.locale is not None:
        out.locale = d.locale
    if d.localized_text is not None:
        out.localized_text = d.localized_text
    if d.additional_info is not None:
        out.additional_info = d.additional_info
    if d.inner_status_code is not None:
        out.inner_status_code = d.inner_status_code.value
    if d.inner_diagnostic_info is not None:
        out.inner_diagnostic_info.CopyFrom(_encode_diag(d.inner_diagnostic_info))
    return out


def _decode_value(ty: t.Type, msg: pb.Value, reg: TypeRegistry) -> Any:
    if isinstance(ty, t.Array):
        if msg.WhichOneof("kind") is None:
            return None
        return [None if e.WhichOneof("kind") is None else _decode_value(ty.element, e, reg) for e in msg.array_value.values]
    if isinstance(ty, t.Matrix):
        if msg.WhichOneof("kind") is None:
            return None
        return v.Matrix(tuple(msg.matrix_value.dimensions), [None if e.WhichOneof("kind") is None else _decode_value(ty.element, e, reg) for e in msg.matrix_value.values])
    if isinstance(ty, t.Enumeration):
        return int(msg.enum_value)
    if isinstance(ty, t.Struct):
        concrete = _message_class(ty)()
        if msg.WhichOneof("kind") != "message_value" or not msg.message_value.Unpack(concrete):
            raise ValueError(f"expected {ty.name} message_value")
        return _decode_struct_message(ty, concrete, reg)
    assert isinstance(ty, t.Builtin), ty
    return _decode_builtin(ty.id, msg, reg)


def _decode_builtin(bid: t.BuiltInType, msg: pb.Value, reg: TypeRegistry) -> Any:
    B = t.BuiltInType
    kind = msg.WhichOneof("kind")
    if kind is None and bid in (B.String, B.ByteString):
        return None
    if bid == B.Boolean:
        return bool(msg.boolean_value)
    if bid == B.SByte:
        return int(msg.sbyte_value)
    if bid == B.Byte:
        return int(msg.byte_value)
    if bid == B.Int16:
        return int(msg.int16_value)
    if bid == B.UInt16:
        return int(msg.uint16_value)
    if bid == B.Int32:
        return int(msg.int32_value)
    if bid == B.UInt32:
        return int(msg.uint32_value)
    if bid == B.Int64:
        return int(msg.int64_value)
    if bid == B.UInt64:
        return int(msg.uint64_value)
    if bid == B.Float:
        return float(msg.float_value)
    if bid == B.Double:
        return float(msg.double_value)
    if bid == B.String:
        return msg.string_value
    if bid == B.DateTime:
        return v.DateTime(int(msg.datetime_value))
    if bid == B.Guid:
        return v.Guid(bytes(msg.guid_value))
    if bid == B.ByteString:
        return bytes(msg.bytestring_value)
    if bid == B.XmlElement:
        x = msg.xml_element_value
        return v.XmlElement(x.value if x.HasField("value") else None)
    if bid == B.NodeId:
        return _decode_nodeid(msg.node_id_value)
    if bid == B.ExpandedNodeId:
        ex = msg.expanded_node_id_value
        return v.ExpandedNodeId(_decode_nodeid(ex.node_id), ex.namespace_uri if ex.HasField("namespace_uri") else None, ex.server_index)
    if bid == B.StatusCode:
        return v.StatusCode(int(msg.status_code_value))
    if bid == B.QualifiedName:
        q = msg.qualified_name_value
        return v.QualifiedName(q.namespace, q.name if q.HasField("name") else None)
    if bid == B.LocalizedText:
        lt = msg.localized_text_value
        return v.LocalizedText(lt.locale if lt.HasField("locale") else None, lt.text if lt.HasField("text") else None)
    if bid == B.ExtensionObject:
        return _decode_extobj(msg.extension_object_value, reg)
    if bid == B.Variant:
        return _decode_variant(msg.variant_value, reg)
    if bid == B.DataValue:
        return _decode_datavalue(msg.data_value, reg)
    if bid == B.DiagnosticInfo:
        return _decode_diag(msg.diagnostic_info_value)
    raise ValueError(f"unhandled builtin {bid}")


def _decode_nodeid(n: pb.NodeId) -> v.NodeId:
    idt = v.IdType(int(n.id_type))
    field = n.WhichOneof("identifier")
    if idt == v.IdType.NUMERIC:
        ident: Any = int(n.numeric)
    elif idt == v.IdType.STRING:
        ident = n.string
    elif idt == v.IdType.GUID:
        ident = v.Guid(bytes(n.guid))
    elif idt == v.IdType.OPAQUE:
        ident = bytes(n.opaque)
    else:
        ident = None
    if field is None and idt == v.IdType.NUMERIC:
        ident = 0
    return v.NodeId(n.namespace, idt, ident)


def _decode_struct_message(ty: t.Struct, msg: Any, reg: TypeRegistry) -> Any:
    if ty.kind == t.StructureKind.UNION:
        return _decode_union_message(ty, msg, reg)
    out: dict[str, Any] = {}
    for fld in ty.fields:
        name = _field_name(fld.name)
        if _field_absent(msg, name, fld.type):
            continue
        out[fld.name] = _decode_field_value(fld.type, msg, name, reg)
    return v.StructValue(out, ty.name)


def _decode_union_message(ty: t.Struct, msg: Any, reg: TypeRegistry) -> v.UnionValue:
    selected = msg.WhichOneof("value")
    if selected is None:
        return v.UnionValue(None, None)
    fld = next(f for f in ty.fields if _field_name(f.name) == selected)
    return v.UnionValue(fld.name, _decode_field_value(fld.type, msg, selected, reg))


def _field_absent(msg: Any, name: str, ty: t.Type) -> bool:
    try:
        return not msg.HasField(name)
    except ValueError:
        return False


def _decode_field_value(ty: t.Type, msg: Any, name: str, reg: TypeRegistry) -> Any:
    val = getattr(msg, name)
    if isinstance(ty, t.Array):
        return [None if e.WhichOneof("kind") is None else _decode_value(ty.element, e, reg) for e in val.values]
    if isinstance(ty, t.Matrix):
        return v.Matrix(tuple(val.dimensions), [None if e.WhichOneof("kind") is None else _decode_value(ty.element, e, reg) for e in val.values])
    if isinstance(ty, t.Struct):
        return _decode_struct_message(ty, val, reg)
    if isinstance(ty, t.Enumeration):
        return int(val)
    assert isinstance(ty, t.Builtin), ty
    if ty.id == t.BuiltInType.String:
        return val.value if val.HasField("value") else None
    if ty.id == t.BuiltInType.ByteString:
        return bytes(val.value) if val.HasField("value") else None
    return _decode_builtin_field(ty.id, val, reg)


def _decode_builtin_field(bid: t.BuiltInType, val: Any, reg: TypeRegistry) -> Any:
    msg = pb.Value()
    field = _VALUE_FIELD[bid]
    if hasattr(val, "DESCRIPTOR"):
        getattr(msg, field).CopyFrom(val)
    else:
        setattr(msg, field, val)
    return _decode_builtin(bid, msg, reg)


def _decode_extobj(msg: pb.ExtensionObject, reg: TypeRegistry) -> v.ExtensionObject:
    type_id = _decode_nodeid(msg.type_id)
    if msg.WhichOneof("body") != "message_body":
        return v.ExtensionObject(type_id, None)
    struct = reg.resolve(type_id)
    concrete = _message_class(struct)()
    if not msg.message_body.Unpack(concrete):
        raise ValueError(f"ExtensionObject body is not {struct.name}")
    return v.ExtensionObject(type_id, _decode_struct_message(struct, concrete, reg))


def _decode_variant(msg: pb.Variant, reg: TypeRegistry) -> v.Variant:
    if not msg.HasField("built_in_type"):
        return v.Variant(None, None)
    bt = t.Builtin(t.BuiltInType(msg.built_in_type))
    payload = msg.WhichOneof("payload")
    if payload == "array":
        val = [None if e.WhichOneof("kind") is None else _decode_builtin(bt.id, e, reg) for e in msg.array.values]
        return v.Variant(bt, val)
    if payload == "matrix":
        val = [None if e.WhichOneof("kind") is None else _decode_builtin(bt.id, e, reg) for e in msg.matrix.values]
        return v.Variant(bt, val, tuple(msg.matrix.dimensions))
    return v.Variant(bt, _decode_builtin(bt.id, msg.scalar, reg))


def _decode_datavalue(msg: pb.DataValue, reg: TypeRegistry) -> v.DataValue:
    return v.DataValue(
        value=_decode_variant(msg.value, reg) if msg.HasField("value") else None,
        status=v.StatusCode(msg.status) if msg.HasField("status") else None,
        source_timestamp=v.DateTime(msg.source_timestamp) if msg.HasField("source_timestamp") else None,
        source_picoseconds=msg.source_picoseconds if msg.HasField("source_picoseconds") else None,
        server_timestamp=v.DateTime(msg.server_timestamp) if msg.HasField("server_timestamp") else None,
        server_picoseconds=msg.server_picoseconds if msg.HasField("server_picoseconds") else None,
    )


def _decode_diag(msg: pb.DiagnosticInfo) -> v.DiagnosticInfo:
    return v.DiagnosticInfo(
        symbolic_id=msg.symbolic_id if msg.HasField("symbolic_id") else None,
        namespace_uri=msg.namespace_uri if msg.HasField("namespace_uri") else None,
        locale=msg.locale if msg.HasField("locale") else None,
        localized_text=msg.localized_text if msg.HasField("localized_text") else None,
        additional_info=msg.additional_info if msg.HasField("additional_info") else None,
        inner_status_code=v.StatusCode(msg.inner_status_code) if msg.HasField("inner_status_code") else None,
        inner_diagnostic_info=_decode_diag(msg.inner_diagnostic_info) if msg.HasField("inner_diagnostic_info") else None,
    )
