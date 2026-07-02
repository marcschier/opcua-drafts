from __future__ import annotations

import os
import json
from functools import lru_cache
from io import BytesIO
from typing import Any

from fastavro import parse_schema, schemaless_reader, schemaless_writer

from schema_support import NS, avro_name, fullname, is_nullable_builtin, load_common, schema_for_type

load_common()
from opcua_enc import corpus as _corpus
from opcua_enc import types as t
from opcua_enc import values as v

INT32_MOD = 2**32
INT64_MOD = 2**64
SCHEMAS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "schemas"))


class TypeRegistry:
    def __init__(self, structs: tuple[t.Struct, ...] = _corpus.STRUCT_TYPES):
        self.structs = tuple(structs)
        self.by_name = {s.name: s for s in self.structs}
        self.by_key: dict[tuple[int, int, Any], t.Struct] = {}
        for s in self.structs:
            if s.type_id:
                self.by_key[self._parse_nodeid(s.type_id)] = s

    @staticmethod
    def _parse_nodeid(node_id: str) -> tuple[int, int, Any]:
        if node_id.startswith("i="):
            return (0, int(v.IdType.NUMERIC), int(node_id[2:]))
        raise ValueError(f"unsupported NodeId literal {node_id}")

    def resolve(self, node_id: v.NodeId) -> t.Struct:
        return self.by_key[(node_id.namespace, int(node_id.id_type), node_id.identifier)]


DEFAULT_REGISTRY = TypeRegistry()


def _signed32(x: int) -> int:
    x = int(x)
    return x - INT32_MOD if x >= 2**31 else x


def _unsigned32(x: int) -> int:
    return int(x) + INT32_MOD if int(x) < 0 else int(x)


def _signed64(x: int) -> int:
    x = int(x)
    return x - INT64_MOD if x >= 2**63 else x


def _unsigned64(x: int) -> int:
    return int(x) + INT64_MOD if int(x) < 0 else int(x)


@lru_cache(maxsize=256)
def _load_builtin_named_schemas() -> dict[str, Any]:
    named: dict[str, Any] = {}
    with open(os.path.join(SCHEMAS, "opcua.builtins.avsc"), "r", encoding="utf-8") as f:
        for schema in json.load(f):
            parse_schema(schema, named_schemas=named)
    return named


def _make_schema(ty: t.Type, reg: TypeRegistry) -> Any:
    named = dict(_load_builtin_named_schemas())
    if isinstance(ty, (t.Struct, t.Enumeration)):
        path = os.path.join(SCHEMAS, f"{avro_name(ty.name)}.avsc")
        with open(path, "r", encoding="utf-8") as f:
            return parse_schema(json.load(f), named_schemas=named)
    top = schema_for_type(ty, optional=False, top=True)
    if isinstance(top, str) and top in named:
        return parse_schema(named[top], named_schemas=named)
    top = _expand_top_refs(top, named)
    return parse_schema(top, named_schemas=named)

def _expand_top_refs(schema: Any, named: dict[str, Any]) -> Any:
    if isinstance(schema, str):
        if schema in named:
            return parse_schema(named[schema], named_schemas=named)
        return schema
    if isinstance(schema, list):
        return [_expand_top_refs(s, named) for s in schema]
    if isinstance(schema, dict):
        return {k: _expand_top_refs(v, named) if k in ("type", "items") else v for k, v in schema.items()}
    return schema


def encode(ty: t.Type, value: Any, reg: TypeRegistry = DEFAULT_REGISTRY) -> bytes:
    schema = _make_schema(ty, reg)
    datum = encode_value(ty, value, reg)
    bio = BytesIO()
    schemaless_writer(bio, schema, datum)
    return bio.getvalue()


def decode(ty: t.Type, data: bytes, reg: TypeRegistry = DEFAULT_REGISTRY) -> Any:
    schema = _make_schema(ty, reg)
    bio = BytesIO(data)
    return decode_value(ty, schemaless_reader(bio, schema), reg)


def encode_value(ty: t.Type, val: Any, reg: TypeRegistry = DEFAULT_REGISTRY) -> Any:
    if isinstance(ty, t.Array):
        if val is None: return None
        return [None if e is None else encode_value(ty.element, e, reg) for e in val]
    if isinstance(ty, t.Matrix):
        if val is None: return None
        return {"dimensions": list(val.dimensions), "values": [None if e is None else encode_value(ty.element, e, reg) for e in val.values]}
    if isinstance(ty, t.Enumeration):
        return int(val)
    if isinstance(ty, t.Struct):
        return _encode_struct(ty, val, reg)
    return _encode_builtin(ty.id, val, reg)


def _encode_struct(ty: t.Struct, val: Any, reg: TypeRegistry) -> Any:
    if ty.kind == t.StructureKind.UNION:
        if val.field_name is None:
            return {"switch": None, "value": None}
        fld = next(f for f in ty.fields if f.name == val.field_name)
        branch = fullname(f"{ty.name}_{fld.name}_Branch")
        return {"switch": fld.name, "value": (branch, {fld.name: encode_value(fld.type, val.value, reg)})}
    out = {}
    for f in ty.fields:
        if f.name in val.fields:
            encoded = encode_value(f.type, val.fields[f.name], reg)
            out[f.name] = {"value": encoded} if f.is_optional else encoded
        elif f.is_optional:
            out[f.name] = None
        else:
            raise ValueError(f"missing mandatory field {ty.name}.{f.name}")
    return out


def _encode_builtin(bid: t.BuiltInType, val: Any, reg: TypeRegistry) -> Any:
    B = t.BuiltInType
    if val is None and is_nullable_builtin(bid):
        return None
    if bid == B.Boolean: return bool(val)
    if bid in (B.SByte, B.Byte, B.Int16, B.UInt16, B.Int32): return int(val)
    if bid == B.UInt32: return _signed32(val)
    if bid == B.Int64: return int(val)
    if bid == B.UInt64: return _signed64(val)
    if bid in (B.Float, B.Double): return float(val)
    if bid == B.String: return val
    if bid == B.DateTime: return int(val.ticks)
    if bid == B.Guid: return val.bytes
    if bid == B.ByteString: return bytes(val)
    if bid == B.XmlElement: return val.value
    if bid == B.NodeId: return _encode_nodeid(val)
    if bid == B.ExpandedNodeId: return {"nodeId": _encode_nodeid(val.node_id), "namespaceUri": val.namespace_uri, "serverIndex": val.server_index}
    if bid == B.StatusCode: return _signed32(val.value)
    if bid == B.QualifiedName: return {"namespace": val.namespace, "name": val.name}
    if bid == B.LocalizedText: return {"locale": val.locale, "text": val.text}
    if bid == B.ExtensionObject: return _encode_extobj(val, reg)
    if bid == B.Variant: return _encode_variant(val, reg)
    if bid == B.DataValue: return _encode_datavalue(val, reg)
    if bid == B.DiagnosticInfo: return _encode_diag(val)
    raise ValueError(bid)


def _encode_nodeid(n: v.NodeId) -> dict[str, Any]:
    return {
        "namespace": int(n.namespace), "idType": int(n.id_type),
        "numeric": int(n.identifier) if n.id_type == v.IdType.NUMERIC else None,
        "string": n.identifier if n.id_type == v.IdType.STRING else None,
        "guid": n.identifier.bytes if n.id_type == v.IdType.GUID else None,
        "opaque": bytes(n.identifier) if n.id_type == v.IdType.OPAQUE else None,
    }


def _encode_extobj(eo: v.ExtensionObject, reg: TypeRegistry) -> dict[str, Any]:
    if eo.body is None:
        return {"typeId": _encode_nodeid(eo.type_id), "body": None}
    st = reg.resolve(eo.type_id)
    return {"typeId": _encode_nodeid(eo.type_id), "body": (fullname(st.name), _encode_struct(st, eo.body, reg))}


def _encode_variant(var: v.Variant, reg: TypeRegistry) -> dict[str, Any]:
    if var.vtype is None:
        return {"builtInType": 0, "dimensions": None, "body": None}
    assert isinstance(var.vtype, t.Builtin), "Avro Variant body must use a built-in type descriptor"
    key = var.vtype.id.name
    if var.dimensions is not None:
        body_name = fullname(f"Variant{key}MatrixBody")
        mv = v.Matrix(var.dimensions, var.value)
        body = {"matrix": {"dimensions": list(mv.dimensions), "values": [None if e is None else _encode_builtin(var.vtype.id, e, reg) for e in mv.values]}}
    elif isinstance(var.value, list):
        body_name = fullname(f"Variant{key}Array")
        body = {"values": [None if e is None else _encode_builtin(var.vtype.id, e, reg) for e in var.value]}
    else:
        body_name = fullname(f"Variant{key}Scalar")
        body = {"value": _encode_builtin(var.vtype.id, var.value, reg)}
    return {"builtInType": int(var.vtype.id), "dimensions": list(var.dimensions) if var.dimensions is not None else None, "body": (body_name, body)}


def _encode_datavalue(dv: v.DataValue, reg: TypeRegistry) -> dict[str, Any]:
    return {
        "value": _encode_variant(dv.value, reg) if dv.value is not None else None,
        "status": _signed32(dv.status.value) if dv.status is not None else None,
        "sourceTimestamp": dv.source_timestamp.ticks if dv.source_timestamp is not None else None,
        "sourcePicoseconds": dv.source_picoseconds,
        "serverTimestamp": dv.server_timestamp.ticks if dv.server_timestamp is not None else None,
        "serverPicoseconds": dv.server_picoseconds,
    }


def _encode_diag(d: v.DiagnosticInfo) -> dict[str, Any]:
    return {"symbolicId": d.symbolic_id, "namespaceUri": d.namespace_uri, "locale": d.locale, "localizedText": d.localized_text,
            "additionalInfo": d.additional_info, "innerStatusCode": _signed32(d.inner_status_code.value) if d.inner_status_code is not None else None,
            "innerDiagnosticInfo": _encode_diag(d.inner_diagnostic_info) if d.inner_diagnostic_info is not None else None}


def decode_value(ty: t.Type, obj: Any, reg: TypeRegistry = DEFAULT_REGISTRY) -> Any:
    if isinstance(ty, t.Array):
        if obj is None: return None
        return [None if e is None else decode_value(ty.element, e, reg) for e in obj]
    if isinstance(ty, t.Matrix):
        if obj is None: return None
        return v.Matrix(tuple(obj["dimensions"]), [None if e is None else decode_value(ty.element, e, reg) for e in obj["values"]])
    if isinstance(ty, t.Enumeration): return int(obj)
    if isinstance(ty, t.Struct): return _decode_struct(ty, obj, reg)
    return _decode_builtin(ty.id, obj, reg)


def _decode_struct(ty: t.Struct, obj: dict[str, Any], reg: TypeRegistry) -> Any:
    if ty.kind == t.StructureKind.UNION:
        if obj["switch"] is None:
            return v.UnionValue(None, None)
        fld = next(f for f in ty.fields if f.name == obj["switch"])
        return v.UnionValue(fld.name, decode_value(fld.type, obj["value"][fld.name], reg))
    fields = {}
    for f in ty.fields:
        if f.name in obj and not (f.is_optional and obj[f.name] is None):
            raw = obj[f.name]["value"] if f.is_optional else obj[f.name]
            fields[f.name] = decode_value(f.type, raw, reg)
    return v.StructValue(fields, ty.name)


def _decode_builtin(bid: t.BuiltInType, obj: Any, reg: TypeRegistry) -> Any:
    B = t.BuiltInType
    if bid == B.Boolean: return bool(obj)
    if bid in (B.SByte, B.Byte, B.Int16, B.UInt16, B.Int32): return int(obj)
    if bid == B.UInt32: return _unsigned32(obj)
    if bid == B.Int64: return int(obj)
    if bid == B.UInt64: return _unsigned64(obj)
    if bid in (B.Float, B.Double): return float(obj)
    if bid == B.String: return obj
    if bid == B.DateTime: return v.DateTime(int(obj))
    if bid == B.Guid: return v.Guid(bytes(obj))
    if bid == B.ByteString: return None if obj is None else bytes(obj)
    if bid == B.XmlElement: return v.XmlElement(obj)
    if bid == B.NodeId: return _decode_nodeid(obj)
    if bid == B.ExpandedNodeId: return v.ExpandedNodeId(_decode_nodeid(obj["nodeId"]), obj["namespaceUri"], obj["serverIndex"])
    if bid == B.StatusCode: return v.StatusCode(_unsigned32(obj))
    if bid == B.QualifiedName: return v.QualifiedName(obj["namespace"], obj["name"])
    if bid == B.LocalizedText: return None if obj is None else v.LocalizedText(obj["locale"], obj["text"])
    if bid == B.ExtensionObject: return _decode_extobj(obj, reg)
    if bid == B.Variant: return _decode_variant(obj, reg)
    if bid == B.DataValue: return _decode_datavalue(obj, reg)
    if bid == B.DiagnosticInfo: return _decode_diag(obj)
    raise ValueError(bid)


def _decode_nodeid(obj: dict[str, Any]) -> v.NodeId:
    idt = v.IdType(obj["idType"])
    if idt == v.IdType.NUMERIC: ident = obj["numeric"]
    elif idt == v.IdType.STRING: ident = obj["string"]
    elif idt == v.IdType.GUID: ident = v.Guid(bytes(obj["guid"]))
    else: ident = bytes(obj["opaque"])
    return v.NodeId(obj["namespace"], idt, ident)


def _decode_extobj(obj: dict[str, Any], reg: TypeRegistry) -> v.ExtensionObject:
    nid = _decode_nodeid(obj["typeId"])
    if obj["body"] is None:
        return v.ExtensionObject(nid, None)
    if isinstance(obj["body"], (bytes, bytearray)):
        return v.ExtensionObject(nid, bytes(obj["body"]))
    st = reg.resolve(nid)
    return v.ExtensionObject(nid, _decode_struct(st, obj["body"], reg))


def _decode_variant(obj: dict[str, Any], reg: TypeRegistry) -> v.Variant:
    tid = obj["builtInType"]
    if tid == 0:
        return v.Variant(None, None)
    bt = t.Builtin(t.BuiltInType(tid))
    body = obj["body"]
    if obj["dimensions"] is not None:
        value = [None if e is None else _decode_builtin(bt.id, e, reg) for e in body["matrix"]["values"]]
        return v.Variant(bt, value, tuple(obj["dimensions"]))
    if "values" in body:
        return v.Variant(bt, [None if e is None else _decode_builtin(bt.id, e, reg) for e in body["values"]])
    return v.Variant(bt, _decode_builtin(bt.id, body["value"], reg))


def _decode_datavalue(obj: dict[str, Any], reg: TypeRegistry) -> v.DataValue:
    return v.DataValue(
        value=_decode_variant(obj["value"], reg) if obj["value"] is not None else None,
        status=v.StatusCode(_unsigned32(obj["status"])) if obj["status"] is not None else None,
        source_timestamp=v.DateTime(obj["sourceTimestamp"]) if obj["sourceTimestamp"] is not None else None,
        source_picoseconds=obj["sourcePicoseconds"],
        server_timestamp=v.DateTime(obj["serverTimestamp"]) if obj["serverTimestamp"] is not None else None,
        server_picoseconds=obj["serverPicoseconds"],
    )


def _decode_diag(obj: dict[str, Any]) -> v.DiagnosticInfo:
    return v.DiagnosticInfo(
        symbolic_id=obj["symbolicId"], namespace_uri=obj["namespaceUri"], locale=obj["locale"], localized_text=obj["localizedText"],
        additional_info=obj["additionalInfo"], inner_status_code=v.StatusCode(_unsigned32(obj["innerStatusCode"])) if obj["innerStatusCode"] is not None else None,
        inner_diagnostic_info=_decode_diag(obj["innerDiagnosticInfo"]) if obj["innerDiagnosticInfo"] is not None else None,
    )
