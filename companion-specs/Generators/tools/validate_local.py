#!/usr/bin/env python3
"""Checks for the Generators companion specification.

`companion-specs/Generators/tools/` held only `build_model.py`: the model was generated
but nothing checked the document against it. That was tolerable while the document carried
only tables, because the tables are generated from the NodeSet and cannot drift.

The AddressSpace figures changed that. A figure is authored, and a wrong arrow looks
exactly like a right one, so `opcdocx.nodeset_diagram` re-derives every Node and every
Reference a figure claims, straight from the UANodeSet.

Run from anywhere:  python companion-specs/Generators/tools/validate_local.py
Exit code is non-zero and the errors are listed if a figure disagrees with the model.
"""
from __future__ import annotations

import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
# tools -> Generators -> companion-specs -> repository root
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
GEN = os.path.dirname(HERE)
SPEC = os.path.join(GEN, "OPC-UA-Companion-Specification-for-Generators.md")
XML = os.path.join(GEN, "Opc.Ua.Generators.NodeSet2.xml")
ANNEX = os.path.join(HERE, "model-reference.md")
WORD_CONFIG = os.path.join(ROOT, "word-drafts", "tools", "specs", "generators.json")
TOOLS = os.path.join(ROOT, "word-drafts", "tools")
NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"
ANNEX_MARKER = '<a id="annex-a"></a>'

errors: list[str] = []
warnings: list[str] = []

for path in (SPEC, XML, ANNEX, WORD_CONFIG):
    if not os.path.exists(path):
        errors.append(f"missing {os.path.relpath(path, ROOT)}")

if not errors:
    with open(SPEC, encoding="utf-8") as f:
        specification = f.read()
    with open(ANNEX, encoding="utf-8") as f:
        generated_reference = f.read()
    with open(WORD_CONFIG, encoding="utf-8") as f:
        word_config = json.load(f)

    model = ET.parse(XML).getroot().find(f"{NS}Models/{NS}Model")
    if model is None:
        errors.append("NodeSet has no Model declaration")
    else:
        release_match = re.search(r"\*\*Release ([^ ]+) — Draft\*\*", specification)
        date_match = re.search(r"\*\*Publication date:\*\* (\d{4}-\d{2}-\d{2})", specification)
        if release_match is None:
            errors.append("specification has no Release banner")
        elif release_match.group(1) != model.get("Version"):
            errors.append(
                f"specification Release {release_match.group(1)} != NodeSet Version "
                f"{model.get('Version')}")
        if date_match is None:
            errors.append("specification has no Publication date")
        elif date_match.group(1) != (model.get("PublicationDate") or "")[:10]:
            errors.append(
                f"specification Publication date {date_match.group(1)} != NodeSet "
                f"PublicationDate {model.get('PublicationDate')}")
        identity = word_config.get("identity", {})
        if identity.get("version") != model.get("Version"):
            errors.append(
                f"Word config version {identity.get('version')} != NodeSet Version "
                f"{model.get('Version')}")
        if identity.get("publicationDate") != (model.get("PublicationDate") or "")[:10]:
            errors.append(
                f"Word config publicationDate {identity.get('publicationDate')} != NodeSet "
                f"PublicationDate {model.get('PublicationDate')}")

    if ANNEX_MARKER not in specification or ANNEX_MARKER not in generated_reference:
        errors.append("Annex A marker missing from specification or generated reference")
    elif (specification[specification.index(ANNEX_MARKER):] !=
          generated_reference[generated_reference.index(ANNEX_MARKER):]):
        errors.append("specification Annex A differs from generated model-reference.md")

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
