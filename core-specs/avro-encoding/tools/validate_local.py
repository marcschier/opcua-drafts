from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from io import BytesIO

from fastavro import parse_schema, schemaless_reader

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "examples"

sys.path.insert(0, str(ROOT.parents[0] / "_common"))
from opcua_enc.corpus import CORPUS
from opcua_enc import types as t
from opcua_enc.values import canonical_equal, is_single_float_type

sys.path.insert(0, str(TOOLS))
import avro_codec
import schema_support

EXAMPLE_NAMES = [
    "bool_true", "uint64_max", "double_nan", "string_unicode", "nodeid_guid", "array_string_with_nulls",
    "matrix_double_2x2_special", "struct_person_min", "union_point", "envelope", "variant_matrix_int",
    "variant_extobj", "datavalue_full", "diaginfo_nested",
]


def write_examples() -> None:
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    selected = {c.name: c for c in CORPUS if c.name in EXAMPLE_NAMES}
    lines = ["# Avro example payloads", "", "The `.hex.txt` files contain schemaless Avro payload bytes generated from the shared CORPUS.", ""]
    for name in EXAMPLE_NAMES:
        c = selected[name]
        data = avro_codec.encode(c.type, c.value)
        (EXAMPLES / f"{name}.hex.txt").write_text(data.hex() + "\n", encoding="utf-8")
        lines.append(f"- `{name}.hex.txt` — `{type(c.type).__name__}` descriptor, {len(data)} bytes")
    (EXAMPLES / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def snapshot_examples() -> dict[str, str]:
    if not EXAMPLES.exists():
        return {}
    return {str(p.relative_to(EXAMPLES)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(EXAMPLES.glob("**/*")) if p.is_file()}


def snapshot_schemas() -> dict[str, str]:
    if not SCHEMAS.exists():
        return {}
    return {str(p.relative_to(SCHEMAS)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SCHEMAS.glob("**/*")) if p.is_file()}


def _fresh_named_schemas() -> dict[str, object]:
    named: dict[str, object] = {}
    for schema in json.loads((SCHEMAS / "opcua.builtins.avsc").read_text(encoding="utf-8")):
        parse_schema(schema, named_schemas=named)
    return named


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


def fresh_published_schema(ty: t.Type) -> object:
    named = _fresh_named_schemas()
    if isinstance(ty, (t.Struct, t.Enumeration)):
        path = SCHEMAS / f"{schema_support.avro_name(ty.name)}.avsc"
        return parse_schema(json.loads(path.read_text(encoding="utf-8")), named_schemas=named)
    top = schema_support.schema_for_type(ty, top=True)
    if isinstance(top, str) and top in named:
        return parse_schema(named[top], named_schemas=named)
    return parse_schema(_expand_top_refs(top, named), named_schemas=named)


def validate_schemas() -> list[str]:
    failures: list[str] = []
    named: dict[str, object] = {}
    builtins = SCHEMAS / "opcua.builtins.avsc"
    if builtins.exists():
        try:
            for schema in json.loads(builtins.read_text(encoding="utf-8")):
                parse_schema(schema, named_schemas=named)
        except Exception as exc:
            failures.append(f"schema {builtins.name}: {exc}")
    pending = [p for p in sorted(SCHEMAS.glob("*.avsc")) if p.name != "opcua.builtins.avsc"]
    errors: dict[Path, Exception] = {}
    while pending:
        progressed = False
        for p in pending[:]:
            try:
                parse_schema(json.loads(p.read_text(encoding="utf-8")), named_schemas=named)
                pending.remove(p)
                errors.pop(p, None)
                progressed = True
            except Exception as exc:
                errors[p] = exc
        if not progressed:
            break
    for p in pending:
        failures.append(f"schema {p.name}: {errors[p]}")
    return failures


def validate_roundtrip() -> list[str]:
    failures: list[str] = []
    for c in CORPUS:
        try:
            out = avro_codec.decode(c.type, avro_codec.encode(c.type, c.value))
            if not canonical_equal(c.value, out, single_float=is_single_float_type(c.type)):
                failures.append(f"roundtrip {c.name}: mismatch")
        except Exception as exc:
            failures.append(f"roundtrip {c.name}: {exc}")
    return failures


def validate_published_schema_conformance() -> list[str]:
    failures: list[str] = []
    for c in CORPUS:
        try:
            data = avro_codec.encode(c.type, c.value)
            datum = schemaless_reader(BytesIO(data), fresh_published_schema(c.type))
            out = avro_codec.decode_value(c.type, datum)
            if not canonical_equal(c.value, out, single_float=is_single_float_type(c.type)):
                failures.append(f"published-schema corpus {c.name}: mismatch")
        except Exception as exc:
            failures.append(f"published-schema corpus {c.name}: {exc}")
    return failures


def validate_examples_with_published_schemas() -> list[str]:
    failures: list[str] = []
    by_name = {c.name: c for c in CORPUS}
    for p in sorted(EXAMPLES.glob("*.hex.txt")):
        name = p.name.removesuffix(".hex.txt")
        if name not in by_name:
            failures.append(f"example {p.name}: no matching corpus case")
            continue
        c = by_name[name]
        try:
            data = bytes.fromhex(p.read_text(encoding="utf-8").strip())
            datum = schemaless_reader(BytesIO(data), fresh_published_schema(c.type))
            out = avro_codec.decode_value(c.type, datum)
            if not canonical_equal(c.value, out, single_float=is_single_float_type(c.type)):
                failures.append(f"example {p.name}: mismatch")
        except Exception as exc:
            failures.append(f"example {p.name}: {exc}")
    for p in sorted(EXAMPLES.glob("*.avro")):
        failures.append(f"example {p.name}: .avro object-container examples are not expected by this validator")
    return failures


def main() -> int:
    subprocess.run([sys.executable, str(TOOLS / "build_schemas.py")], cwd=ROOT.parents[1], check=True)
    schemas_after_first = snapshot_schemas()
    subprocess.run([sys.executable, str(TOOLS / "build_schemas.py")], cwd=ROOT.parents[1], check=True)
    if schemas_after_first != snapshot_schemas():
        failures = ["schemas are not byte-stable across regeneration"]
    else:
        failures = []
    failures.extend(validate_schemas())
    failures.extend(validate_roundtrip())
    failures.extend(validate_published_schema_conformance())
    before = snapshot_examples()
    write_examples()
    after = snapshot_examples()
    write_examples()
    after2 = snapshot_examples()
    if after != after2:
        failures.append("examples are not byte-stable across regeneration")
    if before and before != after:
        failures.append("examples were regenerated with drift; rerun validate_local.py and review changes")
    failures.extend(validate_examples_with_published_schemas())
    for f in failures:
        print("FAIL", f)
    print(f"validate_local: schemas={len(list(SCHEMAS.glob('*.avsc')))} corpus={len(CORPUS)} examples={len(EXAMPLE_NAMES)}; {len(failures)} failures")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
