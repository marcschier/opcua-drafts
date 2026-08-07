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

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# tools -> Generators -> companion-specs -> repository root
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
GEN = os.path.dirname(HERE)
SPEC = os.path.join(GEN, "OPC-UA-Companion-Specification-for-Generators.md")
XML = os.path.join(GEN, "Opc.Ua.Generators.NodeSet2.xml")
TOOLS = os.path.join(ROOT, "word-drafts", "tools")

errors: list[str] = []
warnings: list[str] = []

for path in (SPEC, XML):
    if not os.path.exists(path):
        errors.append(f"missing {os.path.relpath(path, ROOT)}")

if not errors:
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
