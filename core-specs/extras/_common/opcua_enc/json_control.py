"""A type-directed JSON *control* codec.

This is **not** the OPC UA JSON DataEncoding; it is a compact, deliberately
lossless reference codec used to (a) prove that the shared corpus and
``canonical_equal`` are internally consistent, and (b) demonstrate the
encode/decode dispatch pattern that the Avro / Protobuf / Arrow extensions
follow. Values are mapped to plain JSON-serialisable Python structures, then
through ``json.dumps(..., allow_nan=True)`` / ``json.loads`` for a real
bytes round-trip.

Structured bodies inside an ExtensionObject are resolved through a small type
registry keyed by NodeId, mirroring how a real decoder resolves an inline type
identifier to its schema.
"""
from __future__ import annotations

import base64
import json
from typing import Any

from . import corpus as _corpus
from . import types as t
from . import values as v


class TypeRegistry:
    """Resolves the concrete Struct for an ExtensionObject/abstract field."""

    def __init__(self, structs: tuple[t.Struct, ...]):
        self._by_key: dict[tuple[int, int, Any], t.Struct] = {}
        for s in structs:
            if s.type_id:
                self._by_key[self._parse(s.type_id)] = s

    @staticmethod
    def _parse(node_id: str) -> tuple[int, int, Any]:
        # Supports the "i=<n>" numeric form used by the corpus.
        assert node_id.startswith("i="), node_id
        return (0, int(v.IdType.NUMERIC), int(node_id[2:]))

    def resolve(self, node_id: v.NodeId) -> t.Struct:
        key = (node_id.namespace, int(node_id.id_type), node_id.identifier)
        return self._by_key[key]


DEFAULT_REGISTRY = TypeRegistry(_corpus.STRUCT_TYPES)


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


# --------------------------------------------------------------------------
# encode
# --------------------------------------------------------------------------

def encode_value(ty: t.Type, val: Any, reg: TypeRegistry = DEFAULT_REGISTRY) -> Any:
    if isinstance(ty, t.Array):
        if val is None:
            return None
        return [None if e is None else encode_value(ty.element, e, reg) for e in val]
    if isinstance(ty, t.Matrix):
        if val is None:
            return None
        return {"dims": list(val.dimensions), "values": [None if e is None else encode_value(ty.element, e, reg) for e in val.values]}
    if isinstance(ty, t.Enumeration):
        return int(val)
    if isinstance(ty, t.Struct):
        return _encode_struct(ty, val, reg)
    assert isinstance(ty, t.Builtin), ty
    return _encode_builtin(ty.id, val, reg)


def _encode_struct(ty: t.Struct, val: v.StructValue | v.UnionValue, reg: TypeRegistry) -> Any:
    if ty.kind == t.StructureKind.UNION:
        assert isinstance(val, v.UnionValue)
        if val.field_name is None:
            return {"switch": None}
        fld = next(f for f in ty.fields if f.name == val.field_name)
        return {"switch": val.field_name, "value": encode_value(fld.type, val.value, reg)}
    assert isinstance(val, v.StructValue)
    out: dict[str, Any] = {}
    for f in ty.fields:
        if f.name in val.fields:
            out[f.name] = encode_value(f.type, val.fields[f.name], reg)
        elif not f.is_optional:
            raise ValueError(f"missing mandatory field {ty.name}.{f.name}")
    return out


def _encode_builtin(bid: t.BuiltInType, val: Any, reg: TypeRegistry) -> Any:
    B = t.BuiltInType
    if val is None and bid in (B.String, B.ByteString, B.XmlElement):
        return None
    if bid in (B.Boolean,) or bid in t.INTEGER_RANGES or bid in (B.Float, B.Double):
        return val
    if bid == B.String:
        return val
    if bid == B.DateTime:
        return val.ticks
    if bid == B.Guid:
        return _b64(val.bytes)
    if bid == B.ByteString:
        return _b64(val)
    if bid == B.XmlElement:
        return val.value
    if bid == B.StatusCode:
        return val.value
    if bid == B.NodeId:
        return _encode_nodeid(val)
    if bid == B.ExpandedNodeId:
        return {"node": _encode_nodeid(val.node_id), "nsUri": val.namespace_uri, "srv": val.server_index}
    if bid == B.QualifiedName:
        return {"ns": val.namespace, "name": val.name}
    if bid == B.LocalizedText:
        if val is None:
            return None
        return {"locale": val.locale, "text": val.text}
    if bid == B.ExtensionObject:
        return _encode_extobj(val, reg)
    if bid == B.Variant:
        return _encode_variant(val, reg)
    if bid == B.DataValue:
        return _encode_datavalue(val, reg)
    if bid == B.DiagnosticInfo:
        return _encode_diag(val)
    raise ValueError(f"unhandled builtin {bid}")


def _encode_nodeid(n: v.NodeId) -> Any:
    if n.id_type in (v.IdType.GUID,):
        ident: Any = _b64(n.identifier.bytes)
    elif n.id_type == v.IdType.OPAQUE:
        ident = _b64(n.identifier)
    else:
        ident = n.identifier
    return {"ns": n.namespace, "t": int(n.id_type), "id": ident}


def _encode_extobj(eo: v.ExtensionObject, reg: TypeRegistry) -> Any:
    if eo.body is None:
        return {"typeId": _encode_nodeid(eo.type_id), "body": None}
    struct = reg.resolve(eo.type_id)
    return {"typeId": _encode_nodeid(eo.type_id), "body": _encode_struct(struct, eo.body, reg)}


def _encode_variant(var: v.Variant, reg: TypeRegistry) -> Any:
    if var.vtype is None:
        return {"t": 0}
    assert isinstance(var.vtype, t.Builtin), "control Variant bodies are built-in typed"
    is_array = isinstance(var.value, list)
    out: dict[str, Any] = {"t": int(var.vtype.id), "a": 1 if is_array else 0}
    if var.dimensions is not None:
        out["d"] = list(var.dimensions)
    if is_array:
        out["v"] = [None if e is None else _encode_builtin(var.vtype.id, e, reg) for e in var.value]
    else:
        out["v"] = _encode_builtin(var.vtype.id, var.value, reg)
    return out


def _encode_datavalue(dv: v.DataValue, reg: TypeRegistry) -> Any:
    out: dict[str, Any] = {}
    if dv.value is not None:
        out["value"] = _encode_variant(dv.value, reg)
    if dv.status is not None:
        out["status"] = dv.status.value
    if dv.source_timestamp is not None:
        out["srcTs"] = dv.source_timestamp.ticks
    if dv.source_picoseconds is not None:
        out["srcPs"] = dv.source_picoseconds
    if dv.server_timestamp is not None:
        out["srvTs"] = dv.server_timestamp.ticks
    if dv.server_picoseconds is not None:
        out["srvPs"] = dv.server_picoseconds
    return out


def _encode_diag(d: v.DiagnosticInfo) -> Any:
    out: dict[str, Any] = {}
    if d.symbolic_id is not None:
        out["sym"] = d.symbolic_id
    if d.namespace_uri is not None:
        out["ns"] = d.namespace_uri
    if d.locale is not None:
        out["loc"] = d.locale
    if d.localized_text is not None:
        out["lt"] = d.localized_text
    if d.additional_info is not None:
        out["info"] = d.additional_info
    if d.inner_status_code is not None:
        out["ist"] = d.inner_status_code.value
    if d.inner_diagnostic_info is not None:
        out["inner"] = _encode_diag(d.inner_diagnostic_info)
    return out


# --------------------------------------------------------------------------
# decode
# --------------------------------------------------------------------------

def decode_value(ty: t.Type, obj: Any, reg: TypeRegistry = DEFAULT_REGISTRY) -> Any:
    if isinstance(ty, t.Array):
        if obj is None:
            return None
        return [None if e is None else decode_value(ty.element, e, reg) for e in obj]
    if isinstance(ty, t.Matrix):
        if obj is None:
            return None
        return v.Matrix(tuple(obj["dims"]), [None if e is None else decode_value(ty.element, e, reg) for e in obj["values"]])
    if isinstance(ty, t.Enumeration):
        return int(obj)
    if isinstance(ty, t.Struct):
        return _decode_struct(ty, obj, reg)
    assert isinstance(ty, t.Builtin), ty
    return _decode_builtin(ty.id, obj, reg)


def _decode_struct(ty: t.Struct, obj: Any, reg: TypeRegistry) -> Any:
    if ty.kind == t.StructureKind.UNION:
        if obj.get("switch") is None:
            return v.UnionValue(None, None)
        fld = next(f for f in ty.fields if f.name == obj["switch"])
        return v.UnionValue(fld.name, decode_value(fld.type, obj["value"], reg))
    fields: dict[str, Any] = {}
    for f in ty.fields:
        if f.name in obj:
            fields[f.name] = decode_value(f.type, obj[f.name], reg)
    return v.StructValue(fields, ty.name)


def _decode_builtin(bid: t.BuiltInType, obj: Any, reg: TypeRegistry) -> Any:
    B = t.BuiltInType
    if bid == B.Boolean:
        return bool(obj)
    if bid in t.INTEGER_RANGES:
        return None if obj is None else int(obj)
    if bid in (B.Float, B.Double):
        return obj
    if bid == B.String:
        return obj
    if bid == B.DateTime:
        return v.DateTime(int(obj))
    if bid == B.Guid:
        return v.Guid(_unb64(obj))
    if bid == B.ByteString:
        return None if obj is None else _unb64(obj)
    if bid == B.XmlElement:
        return v.XmlElement(obj)
    if bid == B.StatusCode:
        return v.StatusCode(int(obj))
    if bid == B.NodeId:
        return _decode_nodeid(obj)
    if bid == B.ExpandedNodeId:
        return v.ExpandedNodeId(_decode_nodeid(obj["node"]), obj["nsUri"], obj["srv"])
    if bid == B.QualifiedName:
        return v.QualifiedName(obj["ns"], obj["name"])
    if bid == B.LocalizedText:
        if obj is None:
            return None
        return v.LocalizedText(obj["locale"], obj["text"])
    if bid == B.ExtensionObject:
        return _decode_extobj(obj, reg)
    if bid == B.Variant:
        return _decode_variant(obj, reg)
    if bid == B.DataValue:
        return _decode_datavalue(obj, reg)
    if bid == B.DiagnosticInfo:
        return _decode_diag(obj)
    raise ValueError(f"unhandled builtin {bid}")


def _decode_nodeid(obj: Any) -> v.NodeId:
    idt = v.IdType(obj["t"])
    ident = obj["id"]
    if idt == v.IdType.GUID:
        ident = v.Guid(_unb64(ident))
    elif idt == v.IdType.OPAQUE:
        ident = _unb64(ident)
    return v.NodeId(obj["ns"], idt, ident)


def _decode_extobj(obj: Any, reg: TypeRegistry) -> v.ExtensionObject:
    type_id = _decode_nodeid(obj["typeId"])
    if obj["body"] is None:
        return v.ExtensionObject(type_id, None)
    struct = reg.resolve(type_id)
    return v.ExtensionObject(type_id, _decode_struct(struct, obj["body"], reg))


def _decode_variant(obj: Any, reg: TypeRegistry) -> v.Variant:
    tid = obj["t"]
    if tid == 0:
        return v.Variant(None, None)
    bt = t.Builtin(t.BuiltInType(tid))
    dims = tuple(obj["d"]) if "d" in obj else None
    if obj.get("a"):
        value = [None if e is None else _decode_builtin(bt.id, e, reg) for e in obj["v"]]
    else:
        value = _decode_builtin(bt.id, obj["v"], reg)
    return v.Variant(bt, value, dims)


def _decode_datavalue(obj: Any, reg: TypeRegistry) -> v.DataValue:
    return v.DataValue(
        value=_decode_variant(obj["value"], reg) if "value" in obj else None,
        status=v.StatusCode(obj["status"]) if "status" in obj else None,
        source_timestamp=v.DateTime(obj["srcTs"]) if "srcTs" in obj else None,
        source_picoseconds=obj.get("srcPs"),
        server_timestamp=v.DateTime(obj["srvTs"]) if "srvTs" in obj else None,
        server_picoseconds=obj.get("srvPs"),
    )


def _decode_diag(obj: Any) -> v.DiagnosticInfo:
    return v.DiagnosticInfo(
        symbolic_id=obj.get("sym"),
        namespace_uri=obj.get("ns"),
        locale=obj.get("loc"),
        localized_text=obj.get("lt"),
        additional_info=obj.get("info"),
        inner_status_code=v.StatusCode(obj["ist"]) if "ist" in obj else None,
        inner_diagnostic_info=_decode_diag(obj["inner"]) if "inner" in obj else None,
    )


# --------------------------------------------------------------------------
# bytes round-trip
# --------------------------------------------------------------------------

def to_bytes(ty: t.Type, val: Any, reg: TypeRegistry = DEFAULT_REGISTRY) -> bytes:
    return json.dumps(encode_value(ty, val, reg), allow_nan=True).encode("utf-8")


def from_bytes(ty: t.Type, data: bytes, reg: TypeRegistry = DEFAULT_REGISTRY) -> Any:
    return decode_value(ty, json.loads(data.decode("utf-8")), reg)
