#!/usr/bin/env python3
"""Validate the generated xRegistry catalog is structurally conformant.

Checks: required top-level + group + schema attributes; unique schema ids;
formats from the allowed set; embedded documents parse (Avro/Arrow/JSON Schema
as JSON); and — if the ``jsonschema`` package is
installed — every generated JSON Schema is a valid Draft 2020-12 schema.

Usage: python core-specs/extras/xregistry-catalog/tools/validate_local.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLE = os.path.abspath(os.path.join(HERE, "..", "examples", "opcua-catalog.xregistry.json"))
ALLOWED_FORMATS = {"Avro/1.11", "ApacheArrow/1.0", "JsonSchema/2020-12"}


def _fail(msg: str, errs: list) -> None:
    errs.append(msg)


def main() -> int:
    errs: list[str] = []
    if not os.path.exists(EXAMPLE):
        print(f"missing {EXAMPLE}; run build_catalog.py first")
        return 1
    with open(EXAMPLE, encoding="utf-8") as fh:
        cat = json.load(fh)

    for attr in ("specversion", "registryid", "schemagroups"):
        if attr not in cat:
            _fail(f"top-level missing '{attr}'", errs)

    try:
        from jsonschema import Draft202012Validator  # type: ignore
    except Exception:
        Draft202012Validator = None

    seen: set[str] = set()
    n_schemas = 0
    for gid, group in cat.get("schemagroups", {}).items():
        if group.get("schemagroupid") != gid:
            _fail(f"group '{gid}' schemagroupid mismatch", errs)
        for sid, sch in group.get("schemas", {}).items():
            n_schemas += 1
            if sch.get("schemaid") != sid:
                _fail(f"schema '{sid}' schemaid mismatch", errs)
            if sid in seen:
                _fail(f"duplicate schemaid '{sid}'", errs)
            seen.add(sid)
            fmt = sch.get("format")
            if fmt not in ALLOWED_FORMATS:
                _fail(f"schema '{sid}' bad format '{fmt}'", errs)
            if "schema" not in sch and "schemaurl" not in sch:
                _fail(f"schema '{sid}' has neither 'schema' nor 'schemaurl'", errs)
            doc = sch.get("schema")
            if doc is not None:
                if isinstance(doc, str):
                    try:
                        json.loads(doc)
                    except json.JSONDecodeError:
                        _fail(f"schema '{sid}' embedded JSON does not parse", errs)
                if fmt == "JsonSchema/2020-12" and Draft202012Validator is not None:
                    try:
                        Draft202012Validator.check_schema(doc)
                    except Exception as exc:  # noqa: BLE001
                        _fail(f"schema '{sid}' invalid JSON Schema: {exc}", errs)

    print(f"catalog: {len(cat.get('schemagroups', {}))} group(s), {n_schemas} schema(s), {len(errs)} error(s)")
    if Draft202012Validator is None:
        print("  (install 'jsonschema' to also validate JSON Schema documents)")
    for e in errs:
        print("  ERROR:", e)
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
