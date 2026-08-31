#!/usr/bin/env python3
"""Checks for the Generators companion specification.

`source/companion-specs/Generators/tools/` held only `build_model.py`: the model was generated
but nothing checked the document against it. That was tolerable while the document carried
only tables, because the tables are generated from the NodeSet and cannot drift.

The AddressSpace figures changed that. A figure is authored, and a wrong arrow looks
exactly like a right one, so `opcdocx.nodeset_diagram` re-derives every Node and every
Reference a figure claims, straight from the UANodeSet.

Run from anywhere:  python source/companion-specs/Generators/tools/validate_local.py
Exit code is non-zero and the errors are listed if a figure disagrees with the model.
"""
from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
# tools -> Generators -> companion-specs -> source -> repository root
ROOT = os.path.abspath(os.path.join(
    HERE, os.pardir, os.pardir, os.pardir, os.pardir))
GEN = os.path.dirname(HERE)
# The NodeSets live in the owning specification's mirrored model directory.
MODEL = os.path.abspath(os.path.join(
    HERE, os.pardir, os.pardir, os.pardir, os.pardir, "model", "companion-specs", "Generators"))
SPEC = os.path.join(GEN, "spec.md")
XML = os.path.join(MODEL, "Opc.Ua.Generators.NodeSet2.xml")
ANNEX = os.path.join(HERE, "model-reference.md")
MANIFEST = os.path.join(GEN, "manifest.json")
TOOLS = os.path.join(ROOT, "word-drafts", "tools")
NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"

errors: list[str] = []
warnings: list[str] = []

for path in (SPEC, XML, ANNEX, MANIFEST):
    if not os.path.exists(path):
        errors.append(f"missing {os.path.relpath(path, ROOT)}")

if not errors:
    with open(SPEC, encoding="utf-8") as f:
        specification = f.read()
    with open(MANIFEST, encoding="utf-8") as f:
        manifest = json.load(f)

    model = ET.parse(XML).getroot().find(f"{NS}Models/{NS}Model")
    if model is None:
        errors.append("NodeSet has no Model declaration")
    else:
        identity = manifest.get("identity", {})
        if identity.get("version") != model.get("Version"):
            errors.append(
                f"manifest version {identity.get('version')} != NodeSet Version "
                f"{model.get('Version')}")
        if identity.get("publicationDate") != (model.get("PublicationDate") or "")[:10]:
            errors.append(
                f"manifest publicationDate {identity.get('publicationDate')} != NodeSet "
                f"PublicationDate {model.get('PublicationDate')}")

    if "kind: annex-a" not in specification:
        errors.append("specification has no generated Annex A directive")

    if os.path.isdir(TOOLS):
        if TOOLS not in sys.path:
            sys.path.insert(0, TOOLS)
        try:
            from opcdocx import nodeset_diagram
        except ImportError as exc:
            warnings.append(f"model-figure check skipped: {exc}")
        else:
            try:
                errors.extend(nodeset_diagram.check_markdown(SPEC, XML))
            except ValueError as exc:
                errors.append(f"model figure: {exc}")
    else:
        warnings.append("model-figure check skipped: word-drafts/tools not found")

print(f"spec: {os.path.relpath(SPEC, ROOT)}")
print(f"ERRORS: {len(errors)}")
for e in errors[:60]:
    print("  ERR", e)
print(f"WARNINGS: {len(warnings)}")
for w in warnings[:40]:
    print("  WARN", w)
sys.exit(1 if errors else 0)
