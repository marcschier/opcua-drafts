from __future__ import annotations

import argparse
import os
import shutil

from schema_support import avro_name, builtin_defs, datatype_schema, load_common, repo_path, stable_json

load_common()
from opcua_enc import corpus, nodeset, types as t

OUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "schemas"))
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("nodeset", nargs="?", default=DEFAULT_NODESET)
    args = ap.parse_args()
    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)
    result = nodeset.load_datatypes(args.nodeset)
    enums = tuple(sorted([*corpus.ENUM_TYPES, *result.enums], key=lambda x: x.name))
    structs = order_structs((*corpus.STRUCT_TYPES, *tuple(sorted(result.structs, key=lambda x: x.name))))
    with open(os.path.join(OUT_DIR, "opcua.builtins.avsc"), "w", encoding="utf-8") as f:
        f.write(stable_json(builtin_defs(structs)))
    for ty in sorted([*enums, *structs], key=lambda x: x.name):
        with open(os.path.join(OUT_DIR, f"{avro_name(ty.name)}.avsc"), "w", encoding="utf-8") as f:
            f.write(stable_json(datatype_schema(ty)))
    print(f"Generated {1 + len(enums) + len(structs)} schema files in {OUT_DIR}")
    if result.unresolved:
        print(f"Unresolved fields mapped to ExtensionObject: {len(result.unresolved)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
