from __future__ import annotations

import hashlib
import json
import os
import sys
from typing import Any

import pyarrow as pa

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc.corpus import CORPUS
from opcua_enc.values import canonical_equal, is_single_float_type

import arrow_codec
import adbc_access_demo
import build_schemas
import gen_type_reference
import roundtrip
import schema_handshake_demo
import wire_annotate


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STD = os.path.abspath(os.path.join(ROOT, "..", "..", "arrow-encoding"))
EXAMPLES = os.path.join(ROOT, "examples")
SUBSET = [
    "bool_true",
    "int32_max",
    "double_neg_zero",
    "double_nan",
    "string_unicode",
    "nodeid_guid",
    "array_string_with_nulls",
    "matrix_double_2x2_special",
    "struct_person_min",
    "union_point",
    "variant_extobj",
    "datavalue_full",
    "diaginfo_nested",
    "struct_person_present_null",
    "union_text_null",
]


def main() -> int:
    failures = 0
    failures += schemaids_drift_gate()
    build_schemas.main()
    first = schema_snapshots()
    build_schemas.main()
    second = schema_snapshots()
    if first != second:
        failures += 1
        print("FAIL schemas are not deterministic")

    _, rt_failures = roundtrip.run()
    failures += rt_failures

    before = generate_examples()
    after = generate_examples()
    if before != after:
        failures += 1
        print("FAIL examples are not stable")

    conformance_failures = conformance_gate()
    failures += conformance_failures
    failures += type_reference_drift_gate()
    failures += annotation_gate()
    failures += schema_handshake_demo.main()
    failures += adbc_access_demo.main()

    print(f"validate_local: schemas ok, schemaids ok, examples ok, type-reference ok, byte-annotations ok, handshake ok, adbc-access ok, conformance gate {len(CORPUS) - conformance_failures}/{len(CORPUS)} corpus passed, {len(CORPUS) - rt_failures}/{len(CORPUS)} corpus passed, {failures} failures")
    return 1 if failures else 0


def snapshot(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        if os.path.isfile(full):
            with open(full, "rb") as f:
                out[name] = hashlib.sha256(f.read()).hexdigest()
    return out


def schema_snapshots() -> dict[str, dict[str, str]]:
    return {
        "base": snapshot(os.path.join(STD, "schemas")),
        "extras": snapshot(os.path.join(ROOT, "schemas")),
    }


def generate_examples() -> dict[str, str]:
    os.makedirs(EXAMPLES, exist_ok=True)
    selected = {case.name: case for case in CORPUS if case.name in SUBSET}
    index = []
    hashes: dict[str, str] = {}
    for name in SUBSET:
        case = selected[name]
        data = arrow_codec.encode(case.type, case.value)
        file_name = f"{name}.arrow"
        full = os.path.join(EXAMPLES, file_name)
        with open(full, "wb") as f:
            f.write(data)
        digest = hashlib.sha256(data).hexdigest()
        hashes[file_name] = digest
        index.append({"name": name, "file": file_name, "type": build_schemas.type_name(case.type), "sha256": digest, "bytes": len(data)})
    with open(os.path.join(EXAMPLES, "index.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump({"contentType": "application/vnd.apache.arrow.stream", "examples": index}, f, indent=2, sort_keys=True)
        f.write("\n")
    hashes["index.json"] = hashlib.sha256(json.dumps(index, sort_keys=True).encode("utf-8")).hexdigest()
    return hashes


def conformance_gate() -> int:
    published = load_published_corpus_types()
    failures = 0
    for case in CORPUS:
        expected_type = published[case.name]
        data = arrow_codec.encode(case.type, case.value)
        try:
            decoded = decode_with_published_schema(case.type, data, expected_type)
        except Exception as exc:
            failures += 1
            print(f"FAIL conformance {case.name}: {exc}")
            continue
        if not canonical_equal(case.value, decoded, single_float=is_single_float_type(case.type)):
            failures += 1
            print(f"FAIL conformance {case.name}: {case.value!r} != {decoded!r}")
    failures += conformance_examples(published)
    print(f"Arrow conformance gate: {len(CORPUS) - failures}/{len(CORPUS)} corpus passed, {failures} failures")
    return failures


def type_reference_drift_gate() -> int:
    with open(os.path.join(STD, "OPC-UA-Part6-Arrow-DataEncoding.md"), encoding="utf-8") as f:
        text = f.read()
    begin = gen_type_reference.BEGIN
    end = gen_type_reference.END
    if begin not in text or end not in text:
        print("FAIL type-reference markers missing")
        return 1
    current = text[text.index(begin) + len(begin):text.index(end)].strip()
    expected = gen_type_reference.generate().strip()
    if current != expected:
        print("FAIL generated type-reference annex drift; run tools\\gen_type_reference.py")
        return 1
    print("Type-reference drift gate: ok")
    return 0


def schemaids_drift_gate() -> int:
    path = os.path.join(ROOT, "schemas", "schemaids.json")
    with open(path, encoding="utf-8") as f:
        current = json.load(f)
    expected = build_schemas.schemaids()
    if current != expected:
        print("FAIL schemas\\schemaids.json drift; run tools\\build_schemas.py")
        return 1
    print(f"SchemaId drift gate: {len(current)} entries ok")
    return 0


def annotation_gate() -> int:
    failures = 0
    for case in CORPUS:
        try:
            data = arrow_codec.encode(case.type, case.value)
            fields = wire_annotate.annotate(data)
            from opcua_enc import hexdump
            hexdump.assert_contiguous(fields, len(data))
        except Exception as exc:
            failures += 1
            print(f"FAIL byte annotation {case.name}: {exc}")
    print(f"Byte annotation gate: {len(CORPUS) - failures}/{len(CORPUS)} corpus layouts contiguous, {failures} failures")
    return failures


def conformance_examples(published: dict[str, pa.DataType]) -> int:
    failures = 0
    with open(os.path.join(EXAMPLES, "index.json"), encoding="utf-8") as f:
        examples = json.load(f)["examples"]
    by_name = {case.name: case for case in CORPUS}
    for item in examples:
        case = by_name[item["name"]]
        with open(os.path.join(EXAMPLES, item["file"]), "rb") as f:
            data = f.read()
        try:
            decoded = decode_with_published_schema(case.type, data, published[case.name])
        except Exception as exc:
            failures += 1
            print(f"FAIL conformance example {item['file']}: {exc}")
            continue
        if not canonical_equal(case.value, decoded, single_float=is_single_float_type(case.type)):
            failures += 1
            print(f"FAIL conformance example {item['file']}: {case.value!r} != {decoded!r}")
    return failures


def decode_with_published_schema(ty: Any, data: bytes, expected_type: pa.DataType) -> Any:
    reader = pa.ipc.open_stream(pa.BufferReader(data))
    schema = reader.schema
    expected_schema = pa.schema([pa.field("value", expected_type)], metadata={b"opcua-arrow": b"1"})
    if not schema.equals(expected_schema, check_metadata=True):
        raise AssertionError(f"IPC schema {schema} does not match published schema {expected_schema}")
    batch = reader.read_next_batch()
    return arrow_codec.decode_array_value(ty, batch.column(0), 0)


def load_published_corpus_types() -> dict[str, pa.DataType]:
    with open(os.path.join(STD, "schemas", "base.json"), encoding="utf-8") as f:
        base = json.load(f)
    return {name: arrow_from_detail(desc["detail"]) for name, desc in base["corpusTypes"].items()}


def arrow_from_detail(detail: Any) -> pa.DataType:
    if isinstance(detail, dict):
        kind = detail["type"]
        if kind == "struct":
            return pa.struct([pa.field(f["name"], arrow_from_detail(f["type"]), nullable=f.get("nullable", True)) for f in detail["fields"]])
        if kind == "list":
            return pa.list_(pa.field("item", arrow_from_detail(detail["value"]), nullable=detail.get("valueNullable", True)))
        if kind == "dense_union":
            return pa.union([pa.field(f["name"], arrow_from_detail(f["type"])) for f in detail["fields"]], mode="dense", type_codes=detail.get("typeCodes"))
        raise ValueError(f"unknown Arrow detail kind {kind}")
    return primitive_arrow(str(detail))


def primitive_arrow(name: str) -> pa.DataType:
    primitives = {
        "null": pa.null(), "bool": pa.bool_(), "int8": pa.int8(), "uint8": pa.uint8(),
        "int16": pa.int16(), "uint16": pa.uint16(), "int32": pa.int32(), "uint32": pa.uint32(),
        "int64": pa.int64(), "uint64": pa.uint64(), "float": pa.float32(), "double": pa.float64(),
        "string": pa.utf8(), "binary": pa.binary(), "fixed_size_binary[16]": pa.binary(16),
    }
    if name not in primitives:
        raise ValueError(f"unknown primitive Arrow type {name}")
    return primitives[name]


if __name__ == "__main__":
    raise SystemExit(main())
