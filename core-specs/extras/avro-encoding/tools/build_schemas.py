from __future__ import annotations

import argparse
import json
import os
import shutil

from fastavro import parse_schema
from fastavro.schema import to_parsing_canonical_form

from schema_support import (
    avro_name,
    build_named_schema_registry,
    builtin_defs,
    datatype_schema,
    load_common,
    repo_path,
    schema_for_type,
    self_contained_schema,
    stable_json,
    type_key,
)
from message_types import HAND_AUTHORED_MESSAGE_SCHEMAS, MESSAGE_STRUCTS

load_common()
from opcua_enc import corpus, fingerprint, nodeset, types as t

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "schemas"))
STD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "avro-encoding"))
STD_SCHEMAS = os.path.join(STD_DIR, "schemas")
BUILTINS_SCHEMA = os.path.join(STD_SCHEMAS, "opcua.builtins.avsc")
DEFAULT_NODESET = repo_path("core-specs", "pubsub-binding", "Opc.Ua.PubSubBinding.NodeSet2.xml")


def _struct_dependencies(ty: t.Type) -> set[str]:
    deps: set[str] = set()
    if isinstance(ty, t.Struct):
        deps.add(ty.name)
    elif isinstance(ty, (t.Array, t.Matrix)):
        deps.update(_struct_dependencies(ty.element))
    return deps


def order_structs(structs: tuple[t.Struct, ...]) -> tuple[t.Struct, ...]:
    by_name = {s.name: s for s in structs}
    out: list[t.Struct] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(s: t.Struct) -> None:
        if s.name in visited:
            return
        if s.name in visiting:
            return
        visiting.add(s.name)
        deps = set()
        for f in s.fields:
            deps.update(_struct_dependencies(f.type))
        for dep in sorted(deps - {s.name}):
            if dep in by_name:
                visit(by_name[dep])
        visiting.remove(s.name)
        visited.add(s.name)
        out.append(s)

    for s in structs:
        visit(s)
    return tuple(out)


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


def _schemaid(schema: object, registry: dict[str, object]) -> dict[str, str]:
    parsed_schema = parse_schema(self_contained_schema(schema, registry))
    canonical = to_parsing_canonical_form(parsed_schema).encode("utf-8")
    return {
        "schemaid": fingerprint.avro_schema_id_hex(canonical),
        "algorithm": "CRC-64-AVRO Rabin",
    }


def _parse_with_refs(schema: object, named: dict[str, object]) -> object:
    if isinstance(schema, str) and schema in named:
        return parse_schema(named[schema], named_schemas=named)
    return parse_schema(_expand_top_refs(schema, named), named_schemas=named)


def write_schemaids(enums: tuple[t.Enumeration, ...], structs: tuple[t.Struct, ...]) -> None:
    named: dict[str, object] = {}
    entries: dict[str, dict[str, str]] = {}

    builtin_schemas = json.loads(open(BUILTINS_SCHEMA, "r", encoding="utf-8").read())
    for schema in builtin_schemas:
        parse_schema(schema, named_schemas=named)
    raw_datatypes: dict[str, object] = {}
    for ty in sorted([*enums, *structs], key=lambda x: avro_name(x.name)):
        with open(os.path.join(OUT_DIR, f"{avro_name(ty.name)}.avsc"), "r", encoding="utf-8") as f:
            raw_datatypes[avro_name(ty.name)] = json.load(f)
    for name in sorted(HAND_AUTHORED_MESSAGE_SCHEMAS):
        with open(os.path.join(OUT_DIR, f"{name}.avsc"), "r", encoding="utf-8") as f:
            raw_datatypes[name] = json.load(f)
    registry = build_named_schema_registry([*builtin_schemas, *raw_datatypes.values()])

    for bid in t.BuiltInType:
        entries[bid.name] = _schemaid(schema_for_type(t.Builtin(bid), top=True), registry)

    composite_types = sorted(
        {
            c.type
            for c in corpus.CORPUS
            if isinstance(c.type, (t.Array, t.Matrix))
        },
        key=type_key,
    )
    for ty in composite_types:
        entries[type_key(ty)] = _schemaid(schema_for_type(ty, top=True), registry)

    for ty in sorted([*enums, *structs], key=lambda x: avro_name(x.name)):
        entries[avro_name(ty.name)] = _schemaid(raw_datatypes[avro_name(ty.name)], registry)
    for name in sorted(HAND_AUTHORED_MESSAGE_SCHEMAS):
        entries[name] = _schemaid(raw_datatypes[name], registry)

    with open(os.path.join(OUT_DIR, "schemaids.json"), "w", encoding="utf-8") as f:
        f.write(stable_json(entries))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("nodeset", nargs="?", default=DEFAULT_NODESET)
    args = ap.parse_args()
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(STD_SCHEMAS, exist_ok=True)
    result = nodeset.load_datatypes(args.nodeset)
    enums = tuple(sorted([*corpus.ENUM_TYPES, *result.enums], key=lambda x: x.name))
    nodeset_structs = tuple(sorted(result.structs, key=lambda x: x.name))
    structs = order_structs((*corpus.STRUCT_TYPES, *nodeset_structs, *MESSAGE_STRUCTS))
    with open(BUILTINS_SCHEMA, "w", encoding="utf-8") as f:
        f.write(stable_json(builtin_defs(order_structs((*corpus.STRUCT_TYPES, *nodeset_structs)))))
    for ty in sorted([*enums, *structs], key=lambda x: x.name):
        with open(os.path.join(OUT_DIR, f"{avro_name(ty.name)}.avsc"), "w", encoding="utf-8") as f:
            f.write(stable_json(datatype_schema(ty)))
    for name, schema in sorted(HAND_AUTHORED_MESSAGE_SCHEMAS.items()):
        with open(os.path.join(OUT_DIR, f"{name}.avsc"), "w", encoding="utf-8") as f:
            f.write(stable_json(schema))
    write_schemaids(enums, structs)
    print(f"Generated {1 + len(enums) + len(structs) + len(HAND_AUTHORED_MESSAGE_SCHEMAS)} schema files in {OUT_DIR} and {STD_SCHEMAS}")
    if result.unresolved:
        print(f"Unresolved fields mapped to ExtensionObject: {len(result.unresolved)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
