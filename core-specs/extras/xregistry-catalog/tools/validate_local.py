#!/usr/bin/env python3
"""Validate the generated xRegistry catalog is structurally conformant.

Checks: required top-level + group + schema attributes; unique schema ids;
formats from the allowed set; embedded documents parse (Avro/Arrow/JSON Schema
as JSON); and — if the ``jsonschema`` package is
installed — every generated JSON Schema is a valid Draft 2020-12 schema.

Identity is re-derived from the **source NodeSet** rather than read back out of the
catalog, so this checker is independent of the emitter: the expected group id comes from
the NodeSet's ModelUri and the expected schema ids from its DataType names crossed with
the three formats, both through the same normative construction the specification defines
(`opcua_enc.symbolic_id`). It also asserts the xRegistry ``<SINGULAR>id`` grammar, that
every entity carries a non-empty ``name``, and that no content fingerprint is used as a
resource key.

Usage: python core-specs/extras/xregistry-catalog/tools/validate_local.py
"""
from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "_common")))

from opcua_enc import nodeset  # noqa: E402
from opcua_enc.symbolic_id import is_valid_xregistry_id, symbolic_id  # noqa: E402

EXAMPLE = os.path.abspath(os.path.join(HERE, "..", "examples", "opcua-catalog.xregistry.json"))
# The source model is under review; validate against the byte-identical public
# fixture used by build_catalog.py.
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SOURCE_NODESET = os.path.join(
    REPO, "core-specs", "extras", "_common", "nodesets",
    "Opc.Ua.ObservabilityExport.NodeSet2.xml")
ALLOWED_FORMATS = {"Avro/1.11", "ApacheArrow/1.0", "JsonSchema/2020-12"}
FORMAT_KEYS = ("avro", "arrow", "jsonschema")
_UA_NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"


def _fail(msg: str, errs: list) -> None:
    errs.append(msg)


def _expected_identity() -> tuple[str, str, set[str]] | None:
    """Re-derive (group id, group name, schema ids) from the source NodeSet."""
    if not os.path.exists(SOURCE_NODESET):
        return None
    root = ET.parse(SOURCE_NODESET).getroot()
    model = root.find(f"{_UA_NS}Models/{_UA_NS}Model")
    if model is None or not model.get("ModelUri"):
        return None
    ns_uri = model.get("ModelUri")
    loaded = nodeset.load_datatypes(SOURCE_NODESET)
    names = [s.name for s in loaded.structs] + [e.name for e in loaded.enums]
    ids = {symbolic_id(f"{n}/{fk}") for n in names for fk in FORMAT_KEYS}
    return symbolic_id(ns_uri), ns_uri, ids


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

    expected = _expected_identity()

    seen: set[str] = set()
    n_schemas = 0
    for gid, group in cat.get("schemagroups", {}).items():
        if group.get("schemagroupid") != gid:
            _fail(f"group '{gid}' schemagroupid mismatch", errs)
        if not is_valid_xregistry_id(gid):
            _fail(f"group id '{gid}' is not a legal xRegistry <SINGULAR>id", errs)
        if not group.get("name"):
            _fail(f"group '{gid}' has no name", errs)
        if expected and gid == expected[0] and group.get("name") != expected[1]:
            _fail(f"group '{gid}' name is not its source identity '{expected[1]}'", errs)
        for sid, sch in group.get("schemas", {}).items():
            n_schemas += 1
            if sch.get("schemaid") != sid:
                _fail(f"schema '{sid}' schemaid mismatch", errs)
            if not is_valid_xregistry_id(sid):
                _fail(f"schema id '{sid}' is not a legal xRegistry <SINGULAR>id", errs)
            if sid in seen:
                _fail(f"duplicate schemaid '{sid}'", errs)
            seen.add(sid)
            if not sch.get("name"):
                _fail(f"schema '{sid}' has no name", errs)
            labels = sch.get("labels", {})
            if "opcua.schemaid" in labels:
                _fail(f"schema '{sid}' still projects the fingerprint as 'opcua.schemaid'", errs)
            if "opcua.schemafingerprint" not in labels:
                _fail(f"schema '{sid}' has no 'opcua.schemafingerprint' label", errs)
            fingerprint = labels.get("opcua.schemafingerprint")
            if fingerprint and fingerprint == sid:
                _fail(f"schema '{sid}' uses its content fingerprint as the resource key", errs)
            if "schema" in sch and not fingerprint:
                _fail(f"schema '{sid}' embeds a document but has no fingerprint", errs)
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

    if expected is None:
        print("  (source NodeSet not available; identity re-derivation skipped)")
    else:
        exp_gid, _, exp_ids = expected
        if exp_gid not in cat.get("schemagroups", {}):
            _fail(f"expected group id '{exp_gid}' re-derived from the NodeSet is not in the catalog", errs)
        for missing in sorted(exp_ids - seen):
            _fail(f"schema id '{missing}' re-derived from the NodeSet is missing from the catalog", errs)
        for extra in sorted(seen - exp_ids):
            _fail(f"schema id '{extra}' is not derivable from the NodeSet's DataTypes", errs)

    print(f"catalog: {len(cat.get('schemagroups', {}))} group(s), {n_schemas} schema(s), {len(errs)} error(s)")
    if Draft202012Validator is None:
        print("  (install 'jsonschema' to also validate JSON Schema documents)")
    for e in errs:
        print("  ERROR:", e)
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
