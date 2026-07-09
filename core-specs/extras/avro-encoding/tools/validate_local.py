from __future__ import annotations

import hashlib
import copy
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from io import BytesIO

from fastavro import parse_schema, schemaless_reader, schemaless_writer
from fastavro.schema import to_parsing_canonical_form

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
STD = ROOT.parents[1] / "avro-encoding"
SCHEMAS = ROOT / "schemas"
STD_SCHEMAS = STD / "schemas"
BUILTINS_SCHEMA = STD_SCHEMAS / "opcua.builtins.avsc"
EXAMPLES = ROOT / "examples"

sys.path.insert(0, str(ROOT.parents[0] / "_common"))
from opcua_enc import corpus, fingerprint, types as t
from opcua_enc.corpus import CORPUS
from opcua_enc.values import canonical_equal, is_single_float_type

sys.path.insert(0, str(TOOLS))
import avro_codec
import schema_handshake_demo
import schema_support

EXAMPLE_NAMES = [
    "bool_true", "uint64_max", "double_nan", "string_unicode", "nodeid_guid", "array_string_with_nulls",
    "matrix_double_2x2_special", "struct_person_min", "union_point", "envelope", "variant_matrix_int",
    "variant_extobj", "datavalue_full", "diaginfo_nested",
]
MESSAGE_EXAMPLE_NAMES = {
    "avro_schema_announcement": "AvroSchemaAnnouncement",
    "avro_schema_request": "AvroSchemaRequest",
}

DOC_SCHEMA_DOCS = [
    STD / "OPC-UA-Part14-Avro-MessageMapping.md",
    STD / "OPC-UA-Part6-Avro-DataEncoding.md",
]
DOC_SCHEMA_INTRO_RE = re.compile(r"`((?:\.\.[/\\]extras[/\\]avro-encoding[/\\])?schemas[/\\]([^`]+\.avsc))`")


def write_examples() -> None:
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    selected = {c.name: c for c in CORPUS if c.name in EXAMPLE_NAMES}
    lines = ["# Avro example payloads", "", "The `.hex.txt` files contain schemaless Avro payload bytes generated from the shared CORPUS.", ""]
    for name in EXAMPLE_NAMES:
        c = selected[name]
        data = avro_codec.encode(c.type, c.value)
        (EXAMPLES / f"{name}.hex.txt").write_text(data.hex() + "\n", encoding="utf-8")
        lines.append(f"- `{name}.hex.txt` — `{type(c.type).__name__}` descriptor, {len(data)} bytes")
    lines.extend(["", "Schema-exchange message examples are schemaless Avro payload bytes generated from the published `.avsc` files.", ""])
    for name, schema_name in MESSAGE_EXAMPLE_NAMES.items():
        data = _message_example_bytes(schema_name)
        (EXAMPLES / f"{name}.hex.txt").write_text(data.hex() + "\n", encoding="utf-8")
        lines.append(f"- `{name}.hex.txt` — `{schema_name}` record, {len(data)} bytes")
    (EXAMPLES / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _message_example_value(schema_name: str) -> dict[str, object]:
    schemaids = json.loads((SCHEMAS / "schemaids.json").read_text(encoding="utf-8"))
    action_schema_id = bytes.fromhex(schemaids["AvroActionRequestNetworkMessage"]["schemaid"])
    if schema_name == "AvroSchemaAnnouncement":
        return {
            "SchemaId": action_schema_id,
            "SchemaJson": (SCHEMAS / "AvroActionRequestNetworkMessage.avsc").read_text(encoding="utf-8"),
            "SchemaEpoch": 1,
        }
    if schema_name == "AvroSchemaRequest":
        response_schema_id = bytes.fromhex(schemaids["AvroActionResponseNetworkMessage"]["schemaid"])
        return {
            "RequesterId": "late-joiner-1",
            "SchemaIds": [action_schema_id, response_schema_id],
        }
    raise KeyError(schema_name)


def _message_example_schema(schema_name: str) -> object:
    return parse_schema(json.loads((SCHEMAS / f"{schema_name}.avsc").read_text(encoding="utf-8")))


def _message_example_bytes(schema_name: str) -> bytes:
    bio = BytesIO()
    schemaless_writer(bio, _message_example_schema(schema_name), _message_example_value(schema_name))
    return bio.getvalue()


def snapshot_examples() -> dict[str, str]:
    if not EXAMPLES.exists():
        return {}
    return {str(p.relative_to(EXAMPLES)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(EXAMPLES.glob("**/*")) if p.is_file()}


def snapshot_schemas() -> dict[str, str]:
    out: dict[str, str] = {}
    if BUILTINS_SCHEMA.exists():
        out[f"standard/schemas/{BUILTINS_SCHEMA.name}"] = hashlib.sha256(BUILTINS_SCHEMA.read_bytes()).hexdigest()
    if SCHEMAS.exists():
        out.update({f"extras/schemas/{p.relative_to(SCHEMAS)}": hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SCHEMAS.glob("**/*")) if p.is_file()})
    return out


def snapshot_schemaids() -> str | None:
    path = SCHEMAS / "schemaids.json"
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _fresh_named_schemas() -> dict[str, object]:
    named: dict[str, object] = {}
    for schema in json.loads(BUILTINS_SCHEMA.read_text(encoding="utf-8")):
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


def _raw_schema_registry() -> dict[str, object]:
    schemas: list[object] = []
    schemas.extend(json.loads(BUILTINS_SCHEMA.read_text(encoding="utf-8")))
    for path in sorted(SCHEMAS.glob("*.avsc")):
        schemas.append(json.loads(path.read_text(encoding="utf-8")))
    return schema_support.build_named_schema_registry(schemas)


def _raw_schema_registry_excluding(excluded_fullname: str | None) -> dict[str, object]:
    schemas: list[object] = []
    schemas.extend(json.loads(BUILTINS_SCHEMA.read_text(encoding="utf-8")))
    for path in sorted(SCHEMAS.glob("*.avsc")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(schema, dict) and schema_support.schema_fullname(schema) == excluded_fullname:
            continue
        schemas.append(schema)
    return schema_support.build_named_schema_registry(schemas)


def _canonical_schema_form(schema: object, excluded_fullname: str | None) -> str:
    registry = _raw_schema_registry_excluding(excluded_fullname)
    return to_parsing_canonical_form(parse_schema(copy.deepcopy(schema), named_schemas=registry))


def _doc_schema_blocks(doc: Path) -> list[tuple[int, str, str, str]]:
    lines = doc.read_text(encoding="utf-8").splitlines()
    blocks: list[tuple[int, str, str, str]] = []
    for i, line in enumerate(lines):
        matches = DOC_SCHEMA_INTRO_RE.findall(line)
        if not matches:
            continue
        schema_ref, schema_name = matches[-1]
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j >= len(lines) or lines[j].strip() != "```json":
            continue
        k = j + 1
        while k < len(lines) and lines[k].strip() != "```":
            k += 1
        if k >= len(lines):
            blocks.append((i + 1, schema_ref, schema_name, ""))
            continue
        blocks.append((i + 1, schema_ref, schema_name, "\n".join(lines[j + 1:k])))
    return blocks


def _doc_schema_path(schema_ref: str, schema_name: str) -> Path:
    normalized = schema_ref.replace("\\", "/")
    if normalized == "schemas/opcua.builtins.avsc":
        return BUILTINS_SCHEMA
    if normalized.startswith("../extras/avro-encoding/schemas/"):
        return SCHEMAS / schema_name
    return Path("__invalid_doc_schema_ref__")


def validate_doc_schema_blocks() -> tuple[list[str], int]:
    failures: list[str] = []
    block_count = 0
    for doc in DOC_SCHEMA_DOCS:
        blocks = _doc_schema_blocks(doc)
        block_count += len(blocks)
        if not blocks:
            failures.append(f"doc-schema {doc.name}: no ../extras/avro-encoding/schemas/*.avsc JSON blocks found")
            continue
        for line_no, schema_ref, schema_name, doc_json in blocks:
            schema_path = _doc_schema_path(schema_ref, schema_name)
            label = f"doc-schema {doc.name}:{line_no} {schema_ref}"
            if not schema_path.exists():
                failures.append(f"{label}: file does not exist")
                continue
            try:
                doc_schema = json.loads(doc_json)
            except Exception as exc:
                failures.append(f"{label}: doc JSON does not parse: {exc}")
                continue
            try:
                published_schema = json.loads(schema_path.read_text(encoding="utf-8"))
                excluded_fullname = schema_support.schema_fullname(published_schema) if isinstance(published_schema, dict) else None
                doc_canonical = _canonical_schema_form(doc_schema, excluded_fullname)
                published_canonical = _canonical_schema_form(published_schema, excluded_fullname)
            except Exception as exc:
                failures.append(f"{label}: schema parse failed: {exc}")
                continue
            if doc_canonical != published_canonical:
                doc_id = fingerprint.avro_schema_id_hex(doc_canonical.encode("utf-8"))
                published_id = fingerprint.avro_schema_id_hex(published_canonical.encode("utf-8"))
                failures.append(f"{label}: doc schema differs from published .avsc ({doc_id} != {published_id})")
    return failures, block_count


def _self_contained_schemaid(schema: object, registry: dict[str, object]) -> str:
    standalone = schema_support.self_contained_schema(schema, registry)
    canonical = to_parsing_canonical_form(parse_schema(standalone)).encode("utf-8")
    return fingerprint.avro_schema_id_hex(canonical)


def validate_nested_schemaid_gate() -> list[str]:
    failures: list[str] = []
    registry = _raw_schema_registry()
    envelope = json.loads((SCHEMAS / "Envelope.avsc").read_text(encoding="utf-8"))
    before = _self_contained_schemaid(envelope, registry)

    mutated = copy.deepcopy(registry)
    point = mutated[schema_support.fullname("Point")]
    assert isinstance(point, dict)
    point["fields"].append({"name": "Z", "type": "double"})
    after = _self_contained_schemaid(envelope, mutated)
    if before == after:
        failures.append(f"nested SchemaId gate: Envelope id did not change after Point changed ({before})")

    try:
        info = schema_handshake_demo._schema_info(corpus.ENVELOPE)
        parse_schema(json.loads(info.canonical_json))
    except Exception as exc:
        failures.append(f"nested SchemaId gate: Envelope announcement is not standalone: {exc}")
    return failures


def validate_schemas() -> list[str]:
    failures: list[str] = []
    named: dict[str, object] = {}
    builtins = BUILTINS_SCHEMA
    if builtins.exists():
        try:
            for schema in json.loads(builtins.read_text(encoding="utf-8")):
                parse_schema(schema, named_schemas=named)
        except Exception as exc:
            failures.append(f"schema {builtins.name}: {exc}")
    pending = [p for p in sorted(SCHEMAS.glob("*.avsc"))]
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
        if name in MESSAGE_EXAMPLE_NAMES:
            schema_name = MESSAGE_EXAMPLE_NAMES[name]
            try:
                data = bytes.fromhex(p.read_text(encoding="utf-8").strip())
                datum = schemaless_reader(BytesIO(data), _message_example_schema(schema_name))
                if datum != _message_example_value(schema_name):
                    failures.append(f"example {p.name}: mismatch")
            except Exception as exc:
                failures.append(f"example {p.name}: {exc}")
            continue
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
    schemaids_before = snapshot_schemaids()
    subprocess.run([sys.executable, str(TOOLS / "build_schemas.py")], cwd=ROOT.parents[2], check=True)
    schemaids_after_first = snapshot_schemaids()
    schemas_after_first = snapshot_schemas()
    subprocess.run([sys.executable, str(TOOLS / "build_schemas.py")], cwd=ROOT.parents[2], check=True)
    if schemas_after_first != snapshot_schemas():
        failures = ["schemas are not byte-stable across regeneration"]
    else:
        failures = []
    if schemaids_before and schemaids_before != schemaids_after_first:
        failures.append("extras/avro-encoding/schemas/schemaids.json was regenerated with drift; rerun validate_local.py and review changes")
    try:
        subprocess.run([sys.executable, str(TOOLS / "gen_type_reference.py"), "--check"], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        failures.append(f"type reference gate failed: exit {exc.returncode}")
    try:
        subprocess.run([sys.executable, str(TOOLS / "gen_evolution_annex.py"), "--check"], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        failures.append(f"evolution annex gate failed: exit {exc.returncode}")
    try:
        subprocess.run([sys.executable, str(TOOLS / "schema_handshake_demo.py")], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        failures.append(f"schema handshake demo failed: exit {exc.returncode}")
    try:
        subprocess.run([sys.executable, str(TOOLS / "action_discovery_demo.py")], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        failures.append(f"action/discovery demo failed: exit {exc.returncode}")
    try:
        subprocess.run([sys.executable, str(TOOLS / "evolution_demo.py")], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        failures.append(f"evolution demo failed: exit {exc.returncode}")
    try:
        subprocess.run([sys.executable, str(TOOLS / "namespace_map_demo.py")], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        failures.append(f"namespace map demo failed: exit {exc.returncode}")
    try:
        subprocess.run([sys.executable, str(TOOLS / "nodeid_string_demo.py")], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        failures.append(f"nodeid string demo failed: exit {exc.returncode}")
    try:
        subprocess.run([sys.executable, str(TOOLS / "per_field_demo.py")], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        failures.append(f"per-field demo failed: exit {exc.returncode}")
    failures.extend(validate_schemas())
    doc_failures, doc_block_count = validate_doc_schema_blocks()
    failures.extend(doc_failures)
    failures.extend(validate_nested_schemaid_gate())
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
    schemaid_count = len(json.loads((SCHEMAS / "schemaids.json").read_text(encoding="utf-8"))) if (SCHEMAS / "schemaids.json").exists() else 0
    print(f"validate_local: schemas={len(list(SCHEMAS.glob('*.avsc')))} schemaids={schemaid_count} corpus={len(CORPUS)} examples={len(EXAMPLE_NAMES) + len(MESSAGE_EXAMPLE_NAMES)} type_reference=31 handshake=ok nested_schemaid=ok doc_schema_blocks={doc_block_count} action_discovery=ok evolution=ok evolution_annex=ok namespace_map=ok nodeid_string=ok per_field=ok; {len(failures)} failures")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
