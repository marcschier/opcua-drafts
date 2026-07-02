from __future__ import annotations

import os
import sys
from typing import Any, Iterable

import pyarrow as pa

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc import corpus as _corpus
from opcua_enc import json_control
from opcua_enc import types as t
from opcua_enc import values as v


TypeRegistry = json_control.TypeRegistry
DEFAULT_REGISTRY = json_control.DEFAULT_REGISTRY

_DIAG_FRAME = pa.struct([
    pa.field("symbolic_id", pa.int32()),
    pa.field("namespace_uri", pa.int32()),
    pa.field("locale", pa.int32()),
    pa.field("localized_text", pa.int32()),
    pa.field("additional_info", pa.utf8()),
    pa.field("inner_status_code", pa.uint32()),
])


def type_to_arrow(ty: t.Type) -> pa.DataType:
    return canonical_type_to_arrow(ty)


def canonical_type_to_arrow(
    ty: t.Type,
    structs: tuple[t.Struct, ...] = _corpus.STRUCT_TYPES,
    _seen: frozenset[str] = frozenset(),
) -> pa.DataType:
    if isinstance(ty, t.Array):
        return pa.list_(pa.field("item", canonical_type_to_arrow(ty.element, structs, _seen), nullable=ty.allow_null_elements))
    if isinstance(ty, t.Matrix):
        return _matrix_type(canonical_type_to_arrow(ty.element, structs, _seen), ty.allow_null_elements)
    if isinstance(ty, t.Enumeration):
        return pa.uint32() if ty.is_option_set else pa.int32()
    if isinstance(ty, t.Struct):
        if ty.kind == t.StructureKind.UNION:
            seen = _seen | frozenset([ty.name])
            return pa.union(
                [pa.field("null", pa.null()), *[pa.field(f.name, pa.struct([pa.field("value", canonical_type_to_arrow(f.type, structs, seen))])) for f in ty.fields]],
                mode="dense",
            )
        if ty.name in _seen:
            return pa.struct([])
        seen = _seen | frozenset([ty.name])
        return pa.struct([
            pa.field(f.name, _optional_type(f.type, structs, seen) if f.is_optional else canonical_type_to_arrow(f.type, structs, seen), nullable=_nullable_type(f.type) and not f.is_optional)
            for f in ty.fields
        ])
    assert isinstance(ty, t.Builtin), ty
    if ty.id == t.BuiltInType.Variant:
        return _canonical_variant_type(structs, _seen)
    if ty.id == t.BuiltInType.ExtensionObject:
        return _canonical_extobj_type(structs, _seen)
    if ty.id == t.BuiltInType.DataValue:
        return _datavalue_type(structs, _seen)
    if ty.id == t.BuiltInType.DiagnosticInfo:
        return _diagnostic_type()
    return _builtin_arrow(ty.id)


def _optional_type(ty: t.Type, structs: tuple[t.Struct, ...], seen: frozenset[str]) -> pa.DataType:
    return pa.struct([
        pa.field("present", pa.bool_(), nullable=False),
        pa.field("value", canonical_type_to_arrow(ty, structs, seen), nullable=True),
    ])


def _matrix_type(value_type: pa.DataType, allow_null_elements: bool) -> pa.DataType:
    return pa.struct([
        pa.field("dimensions", pa.list_(pa.int32()), nullable=False),
        pa.field("values", pa.list_(pa.field("item", value_type, nullable=allow_null_elements)), nullable=False),
    ])


def _canonical_extobj_type(structs: tuple[t.Struct, ...], seen: frozenset[str]) -> pa.DataType:
    body_fields = [pa.field("null", pa.null())]
    body_fields.extend(pa.field(s.name, canonical_type_to_arrow(s, structs, seen)) for s in structs)
    body_fields.append(pa.field("binary", pa.binary()))
    return pa.struct([
        pa.field("type_id", _nodeid_type(), nullable=False),
        pa.field("body", pa.union(body_fields, mode="dense"), nullable=False),
    ])


def _canonical_variant_type(structs: tuple[t.Struct, ...], seen: frozenset[str]) -> pa.DataType:
    fields: list[pa.Field] = [pa.field("null", pa.null())]
    for bt in t.VARIANT_BODY_TYPES:
        scalar = _canonical_extobj_type(structs, seen) if bt.id == t.BuiltInType.ExtensionObject else _builtin_arrow(bt.id)
        name = bt.id.name
        fields.append(pa.field(f"scalar_{name}", scalar))
        fields.append(pa.field(f"array_{name}", pa.list_(pa.field("item", scalar))))
        fields.append(pa.field(f"matrix_{name}", _matrix_type(scalar, True)))
    return pa.union(fields, mode="dense")


def _datavalue_type(structs: tuple[t.Struct, ...], seen: frozenset[str]) -> pa.DataType:
    return pa.struct([
        pa.field("value", _canonical_variant_type(structs, seen)),
        pa.field("status", pa.uint32()),
        pa.field("source_timestamp", pa.int64()),
        pa.field("source_picoseconds", pa.uint16()),
        pa.field("server_timestamp", pa.int64()),
        pa.field("server_picoseconds", pa.uint16()),
    ])


def _diagnostic_type() -> pa.DataType:
    return pa.struct([
        pa.field("symbolic_id", pa.int32()),
        pa.field("namespace_uri", pa.int32()),
        pa.field("locale", pa.int32()),
        pa.field("localized_text", pa.int32()),
        pa.field("additional_info", pa.utf8()),
        pa.field("inner_status_code", pa.uint32()),
        pa.field("inner_diagnostic_info", pa.list_(pa.field("item", _DIAG_FRAME, nullable=False))),
    ])


def _builtin_arrow(bid: t.BuiltInType) -> pa.DataType:
    B = t.BuiltInType
    return {
        B.Boolean: pa.bool_(),
        B.SByte: pa.int8(),
        B.Byte: pa.uint8(),
        B.Int16: pa.int16(),
        B.UInt16: pa.uint16(),
        B.Int32: pa.int32(),
        B.UInt32: pa.uint32(),
        B.Int64: pa.int64(),
        B.UInt64: pa.uint64(),
        B.Float: pa.float32(),
        B.Double: pa.float64(),
        B.String: pa.utf8(),
        B.DateTime: pa.int64(),
        B.Guid: pa.binary(16),
        B.ByteString: pa.binary(),
        B.XmlElement: pa.utf8(),
        B.NodeId: _nodeid_type(),
        B.ExpandedNodeId: pa.struct([
            pa.field("node_id", _nodeid_type(), nullable=False),
            pa.field("namespace_uri", pa.utf8()),
            pa.field("server_index", pa.uint32(), nullable=False),
        ]),
        B.StatusCode: pa.uint32(),
        B.QualifiedName: pa.struct([
            pa.field("namespace", pa.uint16(), nullable=False),
            pa.field("name", pa.utf8()),
        ]),
        B.LocalizedText: pa.struct([
            pa.field("locale", pa.utf8()),
            pa.field("text", pa.utf8()),
        ]),
    }[bid]


def _nodeid_type() -> pa.DataType:
    return pa.struct([
        pa.field("namespace", pa.uint16(), nullable=False),
        pa.field("id_type", pa.uint8(), nullable=False),
        pa.field("numeric", pa.uint32()),
        pa.field("string", pa.utf8()),
        pa.field("guid", pa.binary(16)),
        pa.field("opaque", pa.binary()),
    ])


def encode(ty: t.Type, value: Any, reg: TypeRegistry = DEFAULT_REGISTRY) -> bytes:
    arr = _build_array(ty, [value], reg, canonical_type_to_arrow(ty))
    schema = pa.schema([pa.field("value", arr.type)], metadata={b"opcua-arrow": b"1"})
    batch = pa.record_batch([arr], schema=schema)
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, schema) as writer:
        writer.write_batch(batch)
    return sink.getvalue().to_pybytes()


def decode(ty: t.Type, data: bytes, reg: TypeRegistry = DEFAULT_REGISTRY) -> Any:
    reader = pa.ipc.open_stream(pa.BufferReader(data))
    batch = reader.read_next_batch()
    return decode_array_value(ty, batch.column(0), 0, reg)


def decode_array_value(ty: t.Type, arr: pa.Array | pa.ChunkedArray, index: int = 0, reg: TypeRegistry = DEFAULT_REGISTRY) -> Any:
    if isinstance(arr, pa.ChunkedArray):
        arr = arr.combine_chunks()
    return _from_scalar(ty, arr[index], reg)


def _build_array(ty: t.Type, vals: list[Any], reg: TypeRegistry, pa_type: pa.DataType | None = None) -> pa.Array:
    pa_type = canonical_type_to_arrow(ty) if pa_type is None else pa_type
    if not vals:
        return _empty_array(pa_type)
    if isinstance(ty, t.Array):
        return _build_list_array(ty.element, vals, ty.allow_null_elements, reg, pa_type)
    if isinstance(ty, t.Matrix):
        return _build_struct_array(
            ["dimensions", "values"],
            [t.Array(t.INT32, False), t.Array(ty.element, ty.allow_null_elements)],
            [[None if x is None else list(x.dimensions) for x in vals], [None if x is None else x.values for x in vals]],
            reg,
            pa_type,
            mask=[x is None for x in vals],
        )
    if isinstance(ty, t.Enumeration):
        return pa.array([None if x is None else int(x) for x in vals], type=pa_type)
    if isinstance(ty, t.Struct):
        if ty.kind == t.StructureKind.UNION:
            return _build_union_array(ty, vals, reg, pa_type)
        return _build_opc_struct_array(ty, vals, reg, pa_type)
    assert isinstance(ty, t.Builtin), ty
    return _build_builtin_array(ty.id, vals, reg, pa_type)



def _empty_array(pa_type: pa.DataType) -> pa.Array:
    if pa.types.is_null(pa_type):
        return pa.nulls(0)
    if pa.types.is_union(pa_type):
        children = [_empty_array(field.type) for field in pa_type]
        return pa.UnionArray.from_dense(pa.array([], type=pa.int8()), pa.array([], type=pa.int32()), children, field_names=[f.name for f in pa_type], type_codes=pa_type.type_codes)
    if pa.types.is_struct(pa_type):
        return pa.StructArray.from_arrays([_empty_array(field.type) for field in pa_type], fields=list(pa_type), mask=pa.array([], type=pa.bool_()))
    if pa.types.is_list(pa_type):
        return pa.ListArray.from_arrays(pa.array([0], type=pa.int32()), _empty_array(pa_type.value_type), type=pa_type, mask=pa.array([], type=pa.bool_()))
    return pa.array([], type=pa_type)


def _build_builtin_array(bid: t.BuiltInType, vals: list[Any], reg: TypeRegistry, pa_type: pa.DataType) -> pa.Array:
    B = t.BuiltInType
    if bid in (B.Boolean,) or bid in t.INTEGER_RANGES or bid in (B.Float, B.Double, B.String):
        return pa.array(vals, type=pa_type)
    if bid == B.DateTime:
        return pa.array([None if x is None else x.ticks for x in vals], type=pa_type)
    if bid == B.Guid:
        return pa.array([None if x is None else x.bytes for x in vals], type=pa_type)
    if bid == B.ByteString:
        return pa.array(vals, type=pa_type)
    if bid == B.XmlElement:
        return pa.array([None if x is None else x.value for x in vals], type=pa_type)
    if bid == B.StatusCode:
        return pa.array([None if x is None else x.value for x in vals], type=pa_type)
    if bid == B.NodeId:
        return _build_nodeid_array(vals, pa_type)
    if bid == B.ExpandedNodeId:
        return _build_struct_array(
            ["node_id", "namespace_uri", "server_index"],
            [t.NODEID, t.STRING, t.UINT32],
            [[None if x is None else x.node_id for x in vals], [None if x is None else x.namespace_uri for x in vals], [None if x is None else x.server_index for x in vals]],
            reg,
            pa_type,
            mask=[x is None for x in vals],
        )
    if bid == B.QualifiedName:
        return _build_struct_array(
            ["namespace", "name"], [t.UINT16, t.STRING],
            [[None if x is None else x.namespace for x in vals], [None if x is None else x.name for x in vals]], reg, pa_type,
            mask=[x is None for x in vals],
        )
    if bid == B.LocalizedText:
        return _build_struct_array(
            ["locale", "text"], [t.STRING, t.STRING],
            [[None if x is None else x.locale for x in vals], [None if x is None else x.text for x in vals]], reg, pa_type,
            mask=[x is None for x in vals],
        )
    if bid == B.ExtensionObject:
        return _build_extobj_array(vals, reg, pa_type)
    if bid == B.Variant:
        return _build_variant_array(vals, reg, pa_type)
    if bid == B.DataValue:
        return _build_datavalue_array(vals, reg, pa_type)
    if bid == B.DiagnosticInfo:
        return _build_diag_array(vals, pa_type)
    raise ValueError(f"unhandled builtin {bid}")


def _build_nodeid_array(vals: list[v.NodeId | None], pa_type: pa.DataType) -> pa.Array:
    ns, idt, num, string, guid, opaque = [], [], [], [], [], []
    mask = []
    for n in vals:
        mask.append(n is None)
        ns.append(0 if n is None else n.namespace)
        idt.append(0 if n is None else int(n.id_type))
        num.append(n.identifier if n is not None and n.id_type == v.IdType.NUMERIC else None)
        string.append(n.identifier if n is not None and n.id_type == v.IdType.STRING else None)
        guid.append(n.identifier.bytes if n is not None and n.id_type == v.IdType.GUID else None)
        opaque.append(n.identifier if n is not None and n.id_type == v.IdType.OPAQUE else None)
    return pa.StructArray.from_arrays(
        [pa.array(ns, type=pa.uint16()), pa.array(idt, type=pa.uint8()), pa.array(num, type=pa.uint32()), pa.array(string, type=pa.utf8()), pa.array(guid, type=pa.binary(16)), pa.array(opaque, type=pa.binary())],
        fields=list(pa_type),
        mask=pa.array(mask, type=pa.bool_()),
    )


def _build_list_array(elem_ty: t.Type, vals: list[Any], allow_null_elements: bool, reg: TypeRegistry, pa_type: pa.DataType) -> pa.Array:
    offsets = [0]
    flat: list[Any] = []
    mask: list[bool] = []
    for val in vals:
        if val is None:
            mask.append(True)
        else:
            mask.append(False)
            flat.extend(val)
        offsets.append(len(flat))
    child = _build_array(elem_ty, flat, reg, pa_type.value_type) if flat else pa.array([], type=pa_type.value_type)
    return pa.ListArray.from_arrays(pa.array(offsets, type=pa.int32()), child, type=pa_type, mask=pa.array(mask, type=pa.bool_()))


def _build_opc_struct_array(ty: t.Struct, vals: list[v.StructValue | None], reg: TypeRegistry, pa_type: pa.DataType) -> pa.Array:
    arrays: list[pa.Array] = []
    for i, f in enumerate(ty.fields):
        child_type = pa_type[i].type
        if f.is_optional:
            present = [x is not None and f.name in x.fields for x in vals]
            raw = [x.fields[f.name] if x is not None and f.name in x.fields else None for x in vals]
            arrays.append(_build_struct_array(["present", "value"], [t.BOOLEAN, f.type], [present, raw], reg, child_type))
        else:
            raw = []
            for x in vals:
                if x is None:
                    raw.append(None)
                elif f.name in x.fields:
                    raw.append(x.fields[f.name])
                else:
                    raise ValueError(f"missing mandatory field {ty.name}.{f.name}")
            arrays.append(_build_array(f.type, raw, reg, child_type))
    return pa.StructArray.from_arrays(arrays, fields=list(pa_type), mask=pa.array([x is None for x in vals], type=pa.bool_()))


def _build_struct_array(names: list[str], child_types: list[t.Type], child_vals: list[list[Any]], reg: TypeRegistry, pa_type: pa.DataType, mask: list[bool] | None = None) -> pa.Array:
    arrays = [_build_array(child_ty, vals, reg, pa_type[i].type) for i, (child_ty, vals) in enumerate(zip(child_types, child_vals))]
    return pa.StructArray.from_arrays(arrays, fields=list(pa_type), mask=pa.array(mask, type=pa.bool_()) if mask is not None else None)


def _build_union_array(ty: t.Struct, vals: list[v.UnionValue | None], reg: TypeRegistry, pa_type: pa.UnionType) -> pa.Array:
    branch_values: list[list[Any]] = [[] for _ in range(pa_type.num_fields)]
    type_ids: list[int] = []
    offsets: list[int] = []
    fields_by_name = {f.name: f for f in ty.fields}
    for val in vals:
        if val is None or val.field_name is None:
            branch = 0
            body = None
        else:
            branch = _type_field_index(pa_type, val.field_name)
            body = val.value
        if branch < 0:
            raise ValueError(f"unknown union field {val.field_name}")
        type_ids.append(pa_type.type_codes[branch])
        offsets.append(len(branch_values[branch]))
        branch_values[branch].append(body)
    children: list[pa.Array] = []
    for i, field in enumerate(pa_type):
        if field.name == "null":
            children.append(pa.nulls(len(branch_values[i])))
        else:
            children.append(_build_struct_array(["value"], [fields_by_name[field.name].type], [branch_values[i]], reg, field.type))
    return pa.UnionArray.from_dense(pa.array(type_ids, type=pa.int8()), pa.array(offsets, type=pa.int32()), children, field_names=[f.name for f in pa_type], type_codes=pa_type.type_codes)


def _build_variant_array(vals: list[v.Variant | None], reg: TypeRegistry, pa_type: pa.UnionType) -> pa.Array:
    branch_values: list[list[Any]] = [[] for _ in range(pa_type.num_fields)]
    type_ids: list[int] = []
    offsets: list[int] = []
    branch_types = _variant_branch_types()
    for var in vals:
        if var is None or var.vtype is None:
            name, body = "null", None
        else:
            assert isinstance(var.vtype, t.Builtin), "Variant bodies must be built-in typed"
            kind = "matrix" if var.dimensions is not None else "array" if isinstance(var.value, list) else "scalar"
            name = f"{kind}_{var.vtype.id.name}"
            body = v.Matrix(var.dimensions, var.value) if kind == "matrix" else var.value
        branch = _type_field_index(pa_type, name)
        type_ids.append(pa_type.type_codes[branch])
        offsets.append(len(branch_values[branch]))
        branch_values[branch].append(body)
    children = []
    for i, field in enumerate(pa_type):
        if field.name == "null":
            children.append(pa.nulls(len(branch_values[i])))
        else:
            children.append(_build_array(branch_types[field.name], branch_values[i], reg, field.type))
    return pa.UnionArray.from_dense(pa.array(type_ids, type=pa.int8()), pa.array(offsets, type=pa.int32()), children, field_names=[f.name for f in pa_type], type_codes=pa_type.type_codes)


def _variant_branch_types() -> dict[str, t.Type]:
    out: dict[str, t.Type] = {}
    for bt in t.VARIANT_BODY_TYPES:
        out[f"scalar_{bt.id.name}"] = bt
        out[f"array_{bt.id.name}"] = t.Array(bt, True)
        out[f"matrix_{bt.id.name}"] = t.Matrix(bt, True)
    return out


def _build_extobj_array(vals: list[v.ExtensionObject | None], reg: TypeRegistry, pa_type: pa.DataType) -> pa.Array:
    type_ids = [None if x is None else x.type_id for x in vals]
    body_type = pa_type.field("body").type
    branch_values: list[list[Any]] = [[] for _ in range(body_type.num_fields)]
    type_id_codes: list[int] = []
    offsets: list[int] = []
    structs = {s.name: s for s in ALL_CORPUS_STRUCTS}
    for eo in vals:
        if eo is None or eo.body is None:
            name, body = "null", None
        else:
            struct = reg.resolve(eo.type_id)
            name, body = struct.name, eo.body
            if _type_field_index(body_type, name) < 0:
                name, body = "binary", None
        branch = _type_field_index(body_type, name)
        type_id_codes.append(body_type.type_codes[branch])
        offsets.append(len(branch_values[branch]))
        branch_values[branch].append(body)
    children = []
    for i, field in enumerate(body_type):
        if field.name == "null":
            children.append(pa.nulls(len(branch_values[i])))
        elif field.name == "binary":
            children.append(pa.array(branch_values[i], type=field.type))
        else:
            children.append(_build_array(structs[field.name], branch_values[i], reg, field.type))
    body_arr = pa.UnionArray.from_dense(pa.array(type_id_codes, type=pa.int8()), pa.array(offsets, type=pa.int32()), children, field_names=[f.name for f in body_type], type_codes=body_type.type_codes)
    return pa.StructArray.from_arrays([_build_nodeid_array(type_ids, pa_type.field("type_id").type), body_arr], fields=list(pa_type), mask=pa.array([x is None for x in vals], type=pa.bool_()))


def _build_datavalue_array(vals: list[v.DataValue | None], reg: TypeRegistry, pa_type: pa.DataType) -> pa.Array:
    return _build_struct_array(
        ["value", "status", "source_timestamp", "source_picoseconds", "server_timestamp", "server_picoseconds"],
        [t.VARIANT, t.UINT32, t.INT64, t.UINT16, t.INT64, t.UINT16],
        [
            [None if x is None else x.value for x in vals],
            [None if x is None or x.status is None else x.status.value for x in vals],
            [None if x is None or x.source_timestamp is None else x.source_timestamp.ticks for x in vals],
            [None if x is None else x.source_picoseconds for x in vals],
            [None if x is None or x.server_timestamp is None else x.server_timestamp.ticks for x in vals],
            [None if x is None else x.server_picoseconds for x in vals],
        ],
        reg,
        pa_type,
        mask=[x is None for x in vals],
    )


def _diag_to_frames(d: v.DiagnosticInfo | None) -> list[v.DiagnosticInfo]:
    frames = []
    cur = None if d is None else d.inner_diagnostic_info
    while cur is not None:
        frames.append(cur)
        cur = cur.inner_diagnostic_info
    return frames


def _build_diag_array(vals: list[v.DiagnosticInfo | None], pa_type: pa.DataType) -> pa.Array:
    frame_struct = t.Struct("DiagnosticInfoFrame", (
        t.Field("symbolic_id", t.INT32), t.Field("namespace_uri", t.INT32), t.Field("locale", t.INT32),
        t.Field("localized_text", t.INT32), t.Field("additional_info", t.STRING), t.Field("inner_status_code", t.UINT32),
    ))
    frame_vals = []
    for d in vals:
        frame_vals.append([
            v.StructValue({
                "symbolic_id": f.symbolic_id,
                "namespace_uri": f.namespace_uri,
                "locale": f.locale,
                "localized_text": f.localized_text,
                "additional_info": f.additional_info,
                "inner_status_code": None if f.inner_status_code is None else f.inner_status_code.value,
            }) for f in _diag_to_frames(d)
        ])
    return _build_struct_array(
        ["symbolic_id", "namespace_uri", "locale", "localized_text", "additional_info", "inner_status_code", "inner_diagnostic_info"],
        [t.INT32, t.INT32, t.INT32, t.INT32, t.STRING, t.UINT32, t.Array(frame_struct, False)],
        [
            [None if x is None else x.symbolic_id for x in vals],
            [None if x is None else x.namespace_uri for x in vals],
            [None if x is None else x.locale for x in vals],
            [None if x is None else x.localized_text for x in vals],
            [None if x is None else x.additional_info for x in vals],
            [None if x is None or x.inner_status_code is None else x.inner_status_code.value for x in vals],
            frame_vals,
        ],
        DEFAULT_REGISTRY,
        pa_type,
        mask=[x is None for x in vals],
    )


def _from_scalar(ty: t.Type, scalar: pa.Scalar, reg: TypeRegistry) -> Any:
    if isinstance(ty, t.Struct) and ty.kind == t.StructureKind.UNION:
        return _union_from_scalar(ty, scalar, reg)
    if isinstance(ty, t.Builtin) and ty.id == t.BuiltInType.Variant:
        return _variant_from_scalar(scalar, reg)
    if not scalar.is_valid:
        if isinstance(ty, t.Builtin) and ty.id == t.BuiltInType.XmlElement:
            return v.XmlElement(None)
        return None
    if isinstance(ty, t.Array):
        return [_from_scalar(ty.element, scalar.values[i], reg) for i in range(len(scalar.values))]
    if isinstance(ty, t.Matrix):
        dims = [int(x.as_py()) for x in scalar["dimensions"].values]
        vals = [_from_scalar(ty.element, scalar["values"].values[i], reg) for i in range(len(scalar["values"].values))]
        return v.Matrix(tuple(dims), vals)
    if isinstance(ty, t.Enumeration):
        return int(scalar.as_py())
    if isinstance(ty, t.Struct):
        fields = {}
        for f in ty.fields:
            child = scalar[f.name]
            if f.is_optional:
                if bool(child["present"].as_py()):
                    fields[f.name] = _from_scalar(f.type, child["value"], reg)
            elif child.is_valid or not f.is_optional:
                fields[f.name] = _from_scalar(f.type, child, reg)
        return v.StructValue(fields, ty.name)
    assert isinstance(ty, t.Builtin), ty
    return _builtin_from_scalar(ty.id, scalar, reg)


def _builtin_from_scalar(bid: t.BuiltInType, scalar: pa.Scalar, reg: TypeRegistry) -> Any:
    B = t.BuiltInType
    if bid in (B.Boolean,) or bid in t.INTEGER_RANGES or bid in (B.Float, B.Double, B.String):
        return scalar.as_py()
    if bid == B.DateTime:
        return v.DateTime(int(scalar.as_py()))
    if bid == B.Guid:
        return v.Guid(scalar.as_py())
    if bid == B.ByteString:
        return scalar.as_py()
    if bid == B.XmlElement:
        return v.XmlElement(scalar.as_py())
    if bid == B.StatusCode:
        return v.StatusCode(int(scalar.as_py()))
    if bid == B.NodeId:
        return _nodeid_from_scalar(scalar)
    if bid == B.ExpandedNodeId:
        return v.ExpandedNodeId(_nodeid_from_scalar(scalar["node_id"]), scalar["namespace_uri"].as_py(), int(scalar["server_index"].as_py()))
    if bid == B.QualifiedName:
        return v.QualifiedName(int(scalar["namespace"].as_py()), scalar["name"].as_py())
    if bid == B.LocalizedText:
        return v.LocalizedText(scalar["locale"].as_py(), scalar["text"].as_py())
    if bid == B.ExtensionObject:
        return _extobj_from_scalar(scalar, reg)
    if bid == B.Variant:
        return _variant_from_scalar(scalar, reg)
    if bid == B.DataValue:
        return v.DataValue(
            value=None if not scalar["value"].is_valid else _variant_from_scalar(scalar["value"], reg),
            status=None if not scalar["status"].is_valid else v.StatusCode(int(scalar["status"].as_py())),
            source_timestamp=None if not scalar["source_timestamp"].is_valid else v.DateTime(int(scalar["source_timestamp"].as_py())),
            source_picoseconds=None if not scalar["source_picoseconds"].is_valid else int(scalar["source_picoseconds"].as_py()),
            server_timestamp=None if not scalar["server_timestamp"].is_valid else v.DateTime(int(scalar["server_timestamp"].as_py())),
            server_picoseconds=None if not scalar["server_picoseconds"].is_valid else int(scalar["server_picoseconds"].as_py()),
        )
    if bid == B.DiagnosticInfo:
        return _diag_from_scalar(scalar)
    raise ValueError(f"unhandled builtin {bid}")


def _nodeid_from_scalar(scalar: pa.Scalar) -> v.NodeId:
    id_type = v.IdType(int(scalar["id_type"].as_py()))
    if id_type == v.IdType.NUMERIC:
        ident: Any = int(scalar["numeric"].as_py())
    elif id_type == v.IdType.STRING:
        ident = scalar["string"].as_py()
    elif id_type == v.IdType.GUID:
        ident = v.Guid(scalar["guid"].as_py())
    else:
        ident = scalar["opaque"].as_py()
    return v.NodeId(int(scalar["namespace"].as_py()), id_type, ident)


def _type_field_index(data_type: pa.DataType, name: str) -> int:
    for i, field in enumerate(data_type):
        if field.name == name:
            return i
    return -1


def _union_field_name(union_type: pa.UnionType, type_code: int) -> str:
    return union_type[union_type.type_codes.index(type_code)].name


def _union_from_scalar(ty: t.Struct, scalar: pa.Scalar, reg: TypeRegistry) -> v.UnionValue:
    name = _union_field_name(scalar.type, scalar.type_code)
    if name == "null":
        return v.UnionValue(None, None)
    fld = next(f for f in ty.fields if f.name == name)
    return v.UnionValue(name, _from_scalar(fld.type, scalar.value["value"], reg))


def _variant_from_scalar(scalar: pa.Scalar, reg: TypeRegistry) -> v.Variant:
    name = _union_field_name(scalar.type, scalar.type_code)
    if name == "null":
        return v.Variant(None, None)
    kind, bt_name = name.split("_", 1)
    bt = t.Builtin(t.BuiltInType[bt_name])
    if kind == "scalar":
        return v.Variant(bt, _from_scalar(bt, scalar.value, reg))
    if kind == "array":
        return v.Variant(bt, [_from_scalar(bt, scalar.value.values[i], reg) for i in range(len(scalar.value.values))])
    mat = _from_scalar(t.Matrix(bt), scalar.value, reg)
    return v.Variant(bt, mat.values, mat.dimensions)


def _extobj_from_scalar(scalar: pa.Scalar, reg: TypeRegistry) -> v.ExtensionObject:
    type_id = _nodeid_from_scalar(scalar["type_id"])
    body = scalar["body"]
    name = _union_field_name(body.type, body.type_code)
    if name == "null":
        return v.ExtensionObject(type_id, None)
    if name == "binary":
        return v.ExtensionObject(type_id, None)
    struct = reg.resolve(type_id)
    return v.ExtensionObject(type_id, _from_scalar(struct, body.value, reg))


def _diag_from_scalar(scalar: pa.Scalar) -> v.DiagnosticInfo:
    def frame_to_diag(frame: pa.Scalar, inner: v.DiagnosticInfo | None) -> v.DiagnosticInfo:
        return v.DiagnosticInfo(
            symbolic_id=None if not frame["symbolic_id"].is_valid else int(frame["symbolic_id"].as_py()),
            namespace_uri=None if not frame["namespace_uri"].is_valid else int(frame["namespace_uri"].as_py()),
            locale=None if not frame["locale"].is_valid else int(frame["locale"].as_py()),
            localized_text=None if not frame["localized_text"].is_valid else int(frame["localized_text"].as_py()),
            additional_info=None if not frame["additional_info"].is_valid else frame["additional_info"].as_py(),
            inner_status_code=None if not frame["inner_status_code"].is_valid else v.StatusCode(int(frame["inner_status_code"].as_py())),
            inner_diagnostic_info=inner,
        )
    inner = None
    frames = scalar["inner_diagnostic_info"].values
    for i in range(len(frames) - 1, -1, -1):
        inner = frame_to_diag(frames[i], inner)
    return v.DiagnosticInfo(
        symbolic_id=None if not scalar["symbolic_id"].is_valid else int(scalar["symbolic_id"].as_py()),
        namespace_uri=None if not scalar["namespace_uri"].is_valid else int(scalar["namespace_uri"].as_py()),
        locale=None if not scalar["locale"].is_valid else int(scalar["locale"].as_py()),
        localized_text=None if not scalar["localized_text"].is_valid else int(scalar["localized_text"].as_py()),
        additional_info=None if not scalar["additional_info"].is_valid else scalar["additional_info"].as_py(),
        inner_status_code=None if not scalar["inner_status_code"].is_valid else v.StatusCode(int(scalar["inner_status_code"].as_py())),
        inner_diagnostic_info=inner,
    )


def _nullable_type(ty: t.Type) -> bool:
    if isinstance(ty, t.Builtin):
        return ty.id in (
            t.BuiltInType.String,
            t.BuiltInType.ByteString,
            t.BuiltInType.XmlElement,
            t.BuiltInType.NodeId,
            t.BuiltInType.ExpandedNodeId,
            t.BuiltInType.QualifiedName,
            t.BuiltInType.LocalizedText,
            t.BuiltInType.ExtensionObject,
            t.BuiltInType.DataValue,
            t.BuiltInType.Variant,
            t.BuiltInType.DiagnosticInfo,
        )
    return isinstance(ty, (t.Array, t.Matrix, t.Struct))


ALL_CORPUS_STRUCTS = _corpus.STRUCT_TYPES