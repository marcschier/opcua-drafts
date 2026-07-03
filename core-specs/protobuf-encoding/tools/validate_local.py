from __future__ import annotations

import filecmp
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCHEMAS = ROOT / "schemas"
GEN = HERE / "_generated"
EXAMPLES = ROOT / "examples"
sys.path.insert(0, os.path.abspath(HERE / ".." / ".." / "_common"))
from opcua_enc import hexdump, types as t, values as v  # noqa: E402
from opcua_enc.corpus import CORPUS  # noqa: E402
from opcua_enc.values import canonical_equal, is_single_float_type  # noqa: E402
from opcua_enc import fingerprint  # noqa: E402
import build_schemas  # noqa: E402
import gen_type_reference  # noqa: E402
import protobuf_codec  # noqa: E402
import wire_annotate  # noqa: E402

EXAMPLE_CASES = [
    "bool_true", "uint64_max", "string_null", "string_unicode", "nodeid_guid",
    "array_string_with_nulls", "matrix_double_2x2_special", "struct_person_one_opt",
    "union_point", "envelope", "variant_matrix_int", "datavalue_full", "diaginfo_nested",
]


def _safe_name(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not s or s[0].isdigit():
        s = "_" + s
    return s


def _field_name(name: str) -> str:
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s).lower()
    return _safe_name(s)


def _msg_cls(st: t.Struct):
    mod = importlib.import_module(f"{_safe_name(st.name).lower()}_pb2")
    return getattr(mod, _safe_name(st.name))


def _msg_desc(ty: t.Type):
    if isinstance(ty, t.Struct):
        return _msg_cls(ty).DESCRIPTOR
    import opcua_builtins_pb2 as gate_pb
    return gate_pb.Value.DESCRIPTOR


def _published_decode(ty: t.Type, data: bytes):
    import opcua_builtins_pb2 as gate_pb
    if isinstance(ty, t.Struct):
        msg = _msg_cls(ty)()
        msg.ParseFromString(data)
        return _pub_struct(ty, msg)
    msg = gate_pb.Value()
    msg.ParseFromString(data)
    return _pub_value(ty, msg)


def _pub_value(ty: t.Type, msg):
    import opcua_builtins_pb2 as gate_pb
    if isinstance(ty, t.Array):
        if msg.WhichOneof("kind") is None:
            return None
        return [None if e.WhichOneof("kind") is None else _pub_value(ty.element, e) for e in msg.array_value.values]
    if isinstance(ty, t.Matrix):
        if msg.WhichOneof("kind") is None:
            return None
        return v.Matrix(tuple(msg.matrix_value.dimensions), [None if e.WhichOneof("kind") is None else _pub_value(ty.element, e) for e in msg.matrix_value.values])
    if isinstance(ty, t.Enumeration):
        return int(msg.enum_value)
    if isinstance(ty, t.Struct):
        concrete = _msg_cls(ty)()
        if msg.WhichOneof("kind") != "message_value" or not msg.message_value.Unpack(concrete):
            raise ValueError(f"published schema cannot decode {ty.name}")
        return _pub_struct(ty, concrete)
    B = t.BuiltInType
    bid = ty.id
    kind = msg.WhichOneof("kind")
    if kind is None and bid in (B.String, B.ByteString):
        return None
    if bid == B.Boolean: return bool(msg.boolean_value)
    if bid == B.SByte: return int(msg.sbyte_value)
    if bid == B.Byte: return int(msg.byte_value)
    if bid == B.Int16: return int(msg.int16_value)
    if bid == B.UInt16: return int(msg.uint16_value)
    if bid == B.Int32: return int(msg.int32_value)
    if bid == B.UInt32: return int(msg.uint32_value)
    if bid == B.Int64: return int(msg.int64_value)
    if bid == B.UInt64: return int(msg.uint64_value)
    if bid == B.Float: return float(msg.float_value)
    if bid == B.Double: return float(msg.double_value)
    if bid == B.String: return msg.string_value
    if bid == B.DateTime: return v.DateTime(int(msg.datetime_value))
    if bid == B.Guid: return v.Guid(bytes(msg.guid_value))
    if bid == B.ByteString: return bytes(msg.bytestring_value)
    if bid == B.XmlElement:
        x = msg.xml_element_value
        return v.XmlElement(x.value if x.HasField("value") else None)
    if bid == B.NodeId: return _pub_nodeid(msg.node_id_value)
    if bid == B.ExpandedNodeId:
        ex = msg.expanded_node_id_value
        return v.ExpandedNodeId(_pub_nodeid(ex.node_id), ex.namespace_uri if ex.HasField("namespace_uri") else None, ex.server_index)
    if bid == B.StatusCode: return v.StatusCode(int(msg.status_code_value))
    if bid == B.QualifiedName:
        q = msg.qualified_name_value
        return v.QualifiedName(q.namespace, q.name if q.HasField("name") else None)
    if bid == B.LocalizedText:
        lt = msg.localized_text_value
        return v.LocalizedText(lt.locale if lt.HasField("locale") else None, lt.text if lt.HasField("text") else None)
    if bid == B.ExtensionObject: return _pub_extobj(msg.extension_object_value)
    if bid == B.Variant: return _pub_variant(msg.variant_value)
    if bid == B.DataValue: return _pub_datavalue(msg.data_value)
    if bid == B.DiagnosticInfo: return _pub_diag(msg.diagnostic_info_value)
    raise ValueError(f"unhandled builtin {bid}")


def _pub_nodeid(n):
    idt = v.IdType(int(n.id_type))
    if idt == v.IdType.NUMERIC:
        ident = int(n.numeric)
    elif idt == v.IdType.STRING:
        ident = n.string
    elif idt == v.IdType.GUID:
        ident = v.Guid(bytes(n.guid))
    else:
        ident = bytes(n.opaque)
    return v.NodeId(n.namespace, idt, ident)


def _pub_struct(ty: t.Struct, msg):
    if ty.kind == t.StructureKind.UNION:
        selected = msg.WhichOneof("value")
        if selected is None:
            return v.UnionValue(None, None)
        fld = next(f for f in ty.fields if _field_name(f.name) == selected)
        return v.UnionValue(fld.name, _pub_field(fld.type, getattr(msg, selected)))
    out = {}
    for fld in ty.fields:
        name = _field_name(fld.name)
        try:
            absent = not msg.HasField(name)
        except ValueError:
            absent = False
        if absent:
            continue
        out[fld.name] = _pub_field(fld.type, getattr(msg, name))
    return v.StructValue(out, ty.name)


def _pub_field(ty: t.Type, val):
    if isinstance(ty, t.Array):
        return [None if e.WhichOneof("kind") is None else _pub_value(ty.element, e) for e in val.values]
    if isinstance(ty, t.Matrix):
        return v.Matrix(tuple(val.dimensions), [None if e.WhichOneof("kind") is None else _pub_value(ty.element, e) for e in val.values])
    if isinstance(ty, t.Struct):
        return _pub_struct(ty, val)
    if isinstance(ty, t.Enumeration):
        return int(val)
    if ty.id == t.BuiltInType.String:
        return val.value if val.HasField("value") else None
    if ty.id == t.BuiltInType.ByteString:
        return bytes(val.value) if val.HasField("value") else None
    msg = importlib.import_module("opcua_builtins_pb2").Value()
    field = protobuf_codec._VALUE_FIELD[ty.id]
    if hasattr(val, "DESCRIPTOR"):
        getattr(msg, field).CopyFrom(val)
    else:
        setattr(msg, field, val)
    return _pub_value(ty, msg)


def _pub_extobj(msg):
    type_id = _pub_nodeid(msg.type_id)
    if msg.WhichOneof("body") is None:
        return v.ExtensionObject(type_id, None)
    if msg.WhichOneof("body") != "message_body":
        raise ValueError("ExtensionObject did not use the published per-type message body")
    st = protobuf_codec.DEFAULT_REGISTRY.resolve(type_id)
    concrete = _msg_cls(st)()
    if not msg.message_body.Unpack(concrete):
        raise ValueError(f"ExtensionObject Any does not contain {st.name}")
    return v.ExtensionObject(type_id, _pub_struct(st, concrete))


def _pub_variant(msg):
    if not msg.HasField("built_in_type"):
        return v.Variant(None, None)
    bt = t.Builtin(t.BuiltInType(msg.built_in_type))
    payload = msg.WhichOneof("payload")
    if payload == "array":
        return v.Variant(bt, [None if e.WhichOneof("kind") is None else _pub_value(bt, e) for e in msg.array.values])
    if payload == "matrix":
        return v.Variant(bt, [None if e.WhichOneof("kind") is None else _pub_value(bt, e) for e in msg.matrix.values], tuple(msg.matrix.dimensions))
    return v.Variant(bt, _pub_value(bt, msg.scalar))


def _pub_datavalue(msg):
    return v.DataValue(
        value=_pub_variant(msg.value) if msg.HasField("value") else None,
        status=v.StatusCode(msg.status) if msg.HasField("status") else None,
        source_timestamp=v.DateTime(msg.source_timestamp) if msg.HasField("source_timestamp") else None,
        source_picoseconds=msg.source_picoseconds if msg.HasField("source_picoseconds") else None,
        server_timestamp=v.DateTime(msg.server_timestamp) if msg.HasField("server_timestamp") else None,
        server_picoseconds=msg.server_picoseconds if msg.HasField("server_picoseconds") else None,
    )


def _pub_diag(msg):
    return v.DiagnosticInfo(
        symbolic_id=msg.symbolic_id if msg.HasField("symbolic_id") else None,
        namespace_uri=msg.namespace_uri if msg.HasField("namespace_uri") else None,
        locale=msg.locale if msg.HasField("locale") else None,
        localized_text=msg.localized_text if msg.HasField("localized_text") else None,
        additional_info=msg.additional_info if msg.HasField("additional_info") else None,
        inner_status_code=v.StatusCode(msg.inner_status_code) if msg.HasField("inner_status_code") else None,
        inner_diagnostic_info=_pub_diag(msg.inner_diagnostic_info) if msg.HasField("inner_diagnostic_info") else None,
    )


def _compile() -> tuple[int, str]:
    GEN.mkdir(parents=True, exist_ok=True)
    for old in GEN.glob("*_pb2.py"):
        old.unlink()
    proto_files = [str(p) for p in sorted(SCHEMAS.glob("*.proto"))]
    cmd = [sys.executable, "-m", "grpc_tools.protoc", f"-I{SCHEMAS}", f"--python_out={GEN}", *proto_files]
    p = subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True)
    return p.returncode, p.stdout + p.stderr


def _snapshot() -> dict[str, bytes]:
    return {str(p.relative_to(ROOT)): p.read_bytes() for p in sorted(SCHEMAS.glob("*.proto"))}


def _write_examples() -> None:
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    wanted = set(EXAMPLE_CASES)
    index = []
    for p in EXAMPLES.glob("*.bin"):
        p.unlink()
    for case in CORPUS:
        if case.name not in wanted:
            continue
        data = protobuf_codec.encode(case.type, case.value)
        filename = f"{case.name}.bin"
        (EXAMPLES / filename).write_bytes(data)
        index.append({"name": case.name, "file": filename, "type": str(case.type), "size": len(data), "hex": data.hex()})
    (EXAMPLES / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def _file_proto(file_desc):
    from google.protobuf import descriptor_pb2

    out = descriptor_pb2.FileDescriptorProto()
    out.ParseFromString(file_desc.serialized_pb)
    out.ClearField("source_code_info")
    return out


def _collect_files(file_desc, override=None):
    from google.protobuf import descriptor_pb2

    seen: set[str] = set()
    ordered = []

    def visit(fd) -> None:
        if fd.name in seen:
            return
        for dep in sorted(fd.dependencies, key=lambda d: d.name):
            visit(dep)
        seen.add(fd.name)
        ordered.append(override if override is not None and override.name == fd.name else _file_proto(fd))

    visit(file_desc)
    fds = descriptor_pb2.FileDescriptorSet()
    fds.file.extend(ordered)
    return fds


def _schema_id(file_desc_or_set) -> bytes:
    return fingerprint.sha256_id(file_desc_or_set.SerializeToString(deterministic=True))


def _nested_import_schemaid_change() -> tuple[str, str]:
    from google.protobuf import descriptor_pb2

    cases_by_name = {case.name: case for case in CORPUS}
    envelope_desc = _msg_desc(cases_by_name["envelope"].type)
    point_desc = _msg_desc(cases_by_name["struct_point"].type)
    changed_point = _file_proto(point_desc.file)
    point = next(m for m in changed_point.message_type if m.name == "Point")
    field = point.field.add()
    field.name = "schema_gate"
    field.number = 100
    field.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE

    old_id = _schema_id(_collect_files(envelope_desc.file))
    new_id = _schema_id(_collect_files(envelope_desc.file, changed_point))
    return old_id.hex(), new_id.hex()


def main() -> int:
    failures = 0
    build_schemas.main()
    first = _snapshot()
    build_schemas.main()
    second = _snapshot()
    if first != second:
        failures += 1
        print("FAIL schemas are not deterministic")

    rc, out = _compile()
    if rc:
        failures += 1
        print("FAIL proto compilation")
        print(out)
    else:
        protobuf_codec.reload_generated()

    rt_failures = 0
    for case in CORPUS:
        got = protobuf_codec.decode(case.type, protobuf_codec.encode(case.type, case.value))
        if not canonical_equal(case.value, got, single_float=is_single_float_type(case.type)):
            rt_failures += 1
            print(f"FAIL roundtrip {case.name}: {case.value!r} != {got!r}")
    failures += rt_failures

    gate_failures = 0
    for case in CORPUS:
        try:
            got = _published_decode(case.type, protobuf_codec.encode(case.type, case.value))
        except Exception as exc:
            gate_failures += 1
            print(f"FAIL conformance {case.name}: {exc}")
            continue
        if not canonical_equal(case.value, got, single_float=is_single_float_type(case.type)):
            gate_failures += 1
            print(f"FAIL conformance {case.name}: {case.value!r} != {got!r}")
    failures += gate_failures

    before = {p.name: p.read_bytes() for p in EXAMPLES.glob("*") if p.is_file()}
    _write_examples()
    after = {p.name: p.read_bytes() for p in EXAMPLES.glob("*") if p.is_file()}
    if before and before != after:
        failures += 1
        print("FAIL examples were not byte-stable; regenerated files differ")

    cases_by_name = {case.name: case for case in CORPUS}
    example_gate_failures = 0
    index_by_file = {entry["file"]: entry["name"] for entry in json.loads((EXAMPLES / "index.json").read_text(encoding="utf-8"))}
    bin_files = sorted(EXAMPLES.glob("*.bin"))
    for bin_file in bin_files:
        if bin_file.name not in index_by_file:
            example_gate_failures += 1
            print(f"FAIL example conformance {bin_file.name}: missing from index.json")
            continue
        case = cases_by_name[index_by_file[bin_file.name]]
        try:
            got = _published_decode(case.type, bin_file.read_bytes())
        except Exception as exc:
            example_gate_failures += 1
            print(f"FAIL example conformance {bin_file.name}: {exc}")
            continue
        if not canonical_equal(case.value, got, single_float=is_single_float_type(case.type)):
            example_gate_failures += 1
            print(f"FAIL example conformance {bin_file.name}: {case.value!r} != {got!r}")
    failures += example_gate_failures

    annotation_failures = 0
    for case in CORPUS:
        data = protobuf_codec.encode(case.type, case.value)
        try:
            fields = wire_annotate.annotate(data, _msg_desc(case.type))
            hexdump.assert_contiguous(fields, len(data))
        except Exception as exc:
            annotation_failures += 1
            print(f"FAIL wire annotation {case.name}: {exc}")
    failures += annotation_failures

    drift_failures = 0
    generated_doc = gen_type_reference.inject(
        (ROOT / "OPC-UA-Part6-Protobuf-DataEncoding.md").read_text(encoding="utf-8"),
        gen_type_reference.generate(),
    )
    if generated_doc != (ROOT / "OPC-UA-Part6-Protobuf-DataEncoding.md").read_text(encoding="utf-8"):
        drift_failures += 1
        print("FAIL Part 6 type-reference annex is out of date; run tools\\gen_type_reference.py")
    schemaids_path = SCHEMAS / "schemaids.json"
    schemaids = gen_type_reference.schemaids_text()
    if not schemaids_path.exists() or schemaids_path.read_text(encoding="utf-8") != schemaids:
        drift_failures += 1
        print("FAIL schemas\\schemaids.json is out of date; run tools\\gen_type_reference.py")
    failures += drift_failures

    nested_schemaid_failures = 0
    try:
        nested_old_id, nested_new_id = _nested_import_schemaid_change()
        if nested_old_id == nested_new_id:
            nested_schemaid_failures += 1
            print(f"FAIL nested SchemaId gate: Envelope id did not change after Point changed ({nested_old_id})")
    except Exception as exc:
        nested_old_id, nested_new_id = "error", "error"
        nested_schemaid_failures += 1
        print(f"FAIL nested SchemaId gate: {exc}")
    failures += nested_schemaid_failures

    conformance_ok = len(CORPUS) - gate_failures
    examples_ok = len(bin_files) - example_gate_failures
    nested_status = "ok" if not nested_schemaid_failures else "fail"
    print(f"validate_local: proto_files={len(list(SCHEMAS.glob('*.proto')))} corpus={len(CORPUS) - rt_failures}/{len(CORPUS)} conformance={conformance_ok}/{len(CORPUS)} examples={examples_ok}/{len(bin_files)} annotations={len(CORPUS) - annotation_failures}/{len(CORPUS)} drift={'ok' if not drift_failures else 'fail'} nested_schemaid={nested_status}({nested_old_id}->{nested_new_id}); {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
