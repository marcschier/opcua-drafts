from __future__ import annotations

import json
import os
import sys
from typing import Any

import pyarrow as pa

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc import corpus, fingerprint, nodeset
from opcua_enc import types as t

import arrow_codec


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_DIR = os.path.join(ROOT, "schemas")
NODESET = os.path.abspath(os.path.join(ROOT, "..", "pubsub-binding", "Opc.Ua.PubSubBinding.NodeSet2.xml"))


def main() -> None:
    os.makedirs(SCHEMA_DIR, exist_ok=True)
    for name in os.listdir(SCHEMA_DIR):
        if name.endswith(".json"):
            os.remove(os.path.join(SCHEMA_DIR, name))

    loaded = nodeset.load_datatypes(NODESET) if os.path.exists(NODESET) else nodeset.LoadResult()
    base_types: list[t.Type] = [t.Builtin(b) for b in t.BuiltInType]
    base_types += [t.Array(t.INT32, False), t.Matrix(t.DOUBLE), *corpus.STRUCT_TYPES, *corpus.ENUM_TYPES]

    write_json("base.json", {
        "schema": "opcua-arrow-reference-schemas",
        "builtins": {b.name: describe_type(t.Builtin(b)) for b in t.BuiltInType},
        "arrays": {"Array<Int32>": describe_type(t.Array(t.INT32, False))},
        "matrix": {"Matrix<Double>": describe_type(t.Matrix(t.DOUBLE))},
        "corpusTypes": {case.name: describe_type(case.type) for case in corpus.CORPUS},
        "networkMessage": network_message_schema(),
        "datasetMessage": dataset_message_schema(),
        "pyarrow": pa.__version__,
    })

    for enum in sorted([*corpus.ENUM_TYPES, *loaded.enums], key=lambda e: e.name):
        write_json(f"enum-{safe(enum.name)}.json", {
            "name": enum.name,
            "kind": "OptionSet" if enum.is_option_set else "Enumeration",
            "arrow": describe_type(enum),
            "members": [{"name": m.name, "value": m.value} for m in enum.members],
        })

    seen_structs = {s.name: s for s in [*corpus.STRUCT_TYPES, *loaded.structs]}
    for struct in sorted(seen_structs.values(), key=lambda s: s.name):
        write_json(f"struct-{safe(struct.name)}.json", {
            "name": struct.name,
            "kind": struct.kind.name,
            "typeId": struct.type_id,
            "encodingId": struct.encoding_id,
            "arrow": describe_type(struct),
            "fields": [
                {
                    "name": f.name,
                    "optional": f.is_optional,
                    "allowSubtypes": f.allow_subtypes,
                    "type": type_name(f.type),
                    "arrow": describe_type(f.type),
                }
                for f in struct.fields
            ],
        })

    write_json("nodeset-load-report.json", {
        "source": os.path.relpath(NODESET, ROOT),
        "structCount": len(loaded.structs),
        "enumCount": len(loaded.enums),
        "unresolved": sorted(loaded.unresolved),
    })
    write_json("schemaids.json", schemaids(loaded))


def describe_type(ty: t.Type) -> dict[str, Any]:
    arrow = arrow_codec.canonical_type_to_arrow(ty)
    return {"opcua": type_name(ty), "arrow": str(arrow), "detail": arrow_detail(arrow)}


def schemaids(loaded: nodeset.LoadResult | None = None) -> dict[str, dict[str, str]]:
    if loaded is None:
        loaded = nodeset.load_datatypes(NODESET) if os.path.exists(NODESET) else nodeset.LoadResult()
    entries: dict[str, dict[str, str]] = {}
    all_types: list[t.Type] = [t.Builtin(b) for b in t.BuiltInType]
    all_types.extend([t.Array(t.INT32, False), t.Matrix(t.DOUBLE), *corpus.STRUCT_TYPES, *corpus.ENUM_TYPES])
    all_types.extend(case.type for case in corpus.CORPUS)
    all_types.extend([*loaded.enums, *loaded.structs])
    for ty in sorted(_unique_types(all_types), key=type_name):
        entries[type_name(ty)] = schemaid_for_arrow_schema(_value_schema(arrow_codec.canonical_type_to_arrow(ty)))
    entries["DataSetMessage"] = schemaid_for_arrow_schema(_value_schema(dataset_message_arrow()))
    entries["NetworkMessage"] = schemaid_for_arrow_schema(_network_message_arrow_schema())
    return {name: entries[name] for name in sorted(entries)}


def schemaid_for_arrow_schema(schema: pa.Schema) -> dict[str, str]:
    return {
        "algorithm": "SHA-256 over Arrow Schema",
        "schemaid": fingerprint.sha256_id_hex(schema.serialize().to_pybytes()),
    }


def _value_schema(data_type: pa.DataType) -> pa.Schema:
    return pa.schema([pa.field("value", data_type)], metadata={b"opcua-arrow": b"1"})


def _unique_types(types: list[t.Type]) -> list[t.Type]:
    seen: dict[str, t.Type] = {}
    for ty in types:
        seen.setdefault(type_name(ty), ty)
    return list(seen.values())


def arrow_detail(dt: pa.DataType) -> Any:
    if pa.types.is_struct(dt):
        return {"type": "struct", "fields": [{"name": f.name, "nullable": f.nullable, "type": arrow_detail(f.type)} for f in dt]}
    if pa.types.is_list(dt) or pa.types.is_large_list(dt):
        return {"type": "list", "valueNullable": dt.value_field.nullable, "value": arrow_detail(dt.value_type)}
    if pa.types.is_union(dt):
        return {"type": "dense_union", "typeCodes": list(dt.type_codes), "fields": [{"name": f.name, "type": arrow_detail(f.type)} for f in dt]}
    return str(dt)


def type_name(ty: t.Type) -> str:
    if isinstance(ty, t.Builtin):
        return ty.id.name
    if isinstance(ty, t.Array):
        return f"Array<{type_name(ty.element)}>"
    if isinstance(ty, t.Matrix):
        return f"Matrix<{type_name(ty.element)}>"
    if isinstance(ty, t.Enumeration):
        return ty.name
    if isinstance(ty, t.Struct):
        return ty.name
    return str(ty)


def network_message_schema() -> dict[str, Any]:
    schema = _network_message_arrow_schema()
    return {"arrow": schema.to_string(), "fields": [{"name": f.name, "type": str(f.type), "nullable": f.nullable} for f in schema]}


def _network_message_arrow_schema() -> pa.Schema:
    fields = [
        pa.field("publisher_id", pa.utf8()),
        pa.field("writer_group_id", pa.uint16()),
        pa.field("dataset_writer_id", pa.uint16()),
        pa.field("sequence_number", pa.uint32()),
        pa.field("timestamp", pa.int64()),
        pa.field("messages", pa.list_(dataset_message_arrow())),
    ]
    return pa.schema(fields, metadata={b"opcua.mapping": b"arrow-network-message"})


def dataset_message_schema() -> dict[str, Any]:
    dt = dataset_message_arrow()
    return {"arrow": str(dt), "detail": arrow_detail(dt)}


def dataset_message_arrow() -> pa.DataType:
    return pa.struct([
        pa.field("dataset_writer_id", pa.uint16()),
        pa.field("sequence_number", pa.uint32()),
        pa.field("status", pa.uint32()),
        pa.field("field_index", pa.list_(pa.uint16())),
        pa.field("values", pa.list_(arrow_codec.canonical_type_to_arrow(t.VARIANT))),
    ])


def write_json(name: str, obj: Any) -> None:
    with open(os.path.join(SCHEMA_DIR, name), "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")


def safe(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)


if __name__ == "__main__":
    main()
