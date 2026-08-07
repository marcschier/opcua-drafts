#!/usr/bin/env python3
"""
Local structural validator for the OPC UA Data Channels NodeSet, CSV and Annex A.

Runs with no untracked base data, so it is part of the CI self-contained set. The
cross-check of base UA NodeIds is skipped when the gitignored `tools/ref/UA.NodeIds.csv`
aid is absent, exactly as the WoT-Connectivity validator does.

Usage (from repo root):  python core-specs/data-channels/tools/validate_local.py
"""
from __future__ import annotations

import csv
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.dirname(HERE)
REF = os.path.join(HERE, "ref")
NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"

XML = os.path.join(GEN, "Opc.Ua.DataChannels.NodeSet2.xml")
CSVF = os.path.join(GEN, "Opc.Ua.DataChannels.NodeIds.csv")
ANNEX = os.path.join(HERE, "model-reference.md")
DOCS = ("OPC-UA-Part3-Data-Channel-Model.md", "OPC-UA-Data-Channels.md")
BEGIN_MARK = "<!-- BEGIN GENERATED: model-reference -->"
END_MARK = "<!-- END GENERATED: model-reference -->"

sys.path.insert(0, HERE)
import build_model  # noqa: E402

# The reserved provisional ranges, mirroring build_model.py. Anything outside them is
# either a base UA NodeId or a mistake.
OWN_RANGES = ((65000, 65199), (65900, 65999), (66000, 69999))

ServerCapabilities = "i=2268"
DataTypeEncodingType = "i=76"
Structure = "i=22"
Enumeration = "i=29"

errors: list[str] = []
warnings: list[str] = []


def is_own(num: int) -> bool:
    return any(lo <= num <= hi for lo, hi in OWN_RANGES)


def load_ids(path):
    out = set()
    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[1].strip().isdigit():
                out.add(int(row[1]))
    return out


_ua_csv = os.path.join(REF, "UA.NodeIds.csv")
UA = load_ids(_ua_csv) if os.path.exists(_ua_csv) else None
# Base ids this overlay references that a trimmed base table may not list.
UA_EXTRA = {2268, 2253, 2041, 2069, 14533, 17602, 17603, 76, 297}

NID_RE = re.compile(r"^(?:ns=(\d+);)?i=(\d+)$")
ALIAS: dict[str, str] = {}


def parse_nid(text):
    text = ALIAS.get(text, text)
    m = NID_RE.match(text or "")
    if not m:
        return None
    return int(m.group(1) or 0), int(m.group(2))


# --- Parse -----------------------------------------------------------------
tree = ET.parse(XML)
root = tree.getroot()
defined: dict[int, tuple[str, str]] = {}
elems: list[tuple[str, ET.Element]] = []

for el in root:
    tag = el.tag.replace(NS, "")
    if tag == "Aliases":
        for a in el:
            ALIAS[a.get("Alias")] = a.text
    if tag == "Models":
        for model in el:
            if model.get("ModelUri") != build_model.NAMESPACE:
                errors.append(f"model declares an unexpected ModelUri {model.get('ModelUri')}")
            for req in model:
                if req.tag.replace(NS, "") != "RequiredModel":
                    continue
                if req.get("ModelUri") == model.get("ModelUri"):
                    errors.append("a Model shall not require itself: a self-referential "
                                  "RequiredModel is a cycle in the dependency graph")
    if tag == "NamespaceUris" and list(el):
        errors.append("an errata overlay on the base namespace shall declare no NamespaceUri")
    if not tag.startswith("UA"):
        continue
    parsed = parse_nid(el.get("NodeId"))
    if parsed is None:
        errors.append(f"unparsable NodeId {el.get('NodeId')}")
    else:
        ns, num = parsed
        if ns != 0:
            errors.append(f"i={num}: overlay nodes shall be in namespace 0, found ns={ns}")
        if num in defined:
            errors.append(f"duplicate NodeId i={num}")
        defined[num] = (tag, el.get("BrowseName"))
    elems.append((tag, el))


def check_target(text, ctx):
    parsed = parse_nid(text)
    if parsed is None:
        return
    ns, num = parsed
    if ns != 0:
        errors.append(f"{ctx}: reference into namespace {ns}")
        return
    if num in defined:
        return
    if is_own(num):
        errors.append(f"{ctx}: i={num} is in a reserved own range but is not defined here")
        return
    if UA is None or num in UA or num in UA_EXTRA:
        return
    errors.append(f"{ctx}: i={num} is neither defined here nor a known base UA NodeId")


# --- Node-level checks ------------------------------------------------------
for tag, el in elems:
    nid = el.get("NodeId")
    bn = el.get("BrowseName") or ""
    ctx = f"{tag} {bn} ({nid})"
    parsed = parse_nid(nid)
    num = parsed[1] if parsed else -1

    if parsed and not is_own(num):
        errors.append(f"{ctx}: NodeId outside the reserved provisional ranges {OWN_RANGES}")
    if ":" in bn:
        errors.append(f"{ctx}: BrowseName shall be unqualified in a base-namespace overlay")

    if el.get("ParentNodeId"):
        check_target(el.get("ParentNodeId"), ctx + " parent")
    if el.get("DataType"):
        check_target(el.get("DataType"), ctx + " datatype")

    refs = el.find(NS + "References")
    rl = []
    if refs is not None:
        for r in refs:
            rt, tgt = r.get("ReferenceType"), r.text
            fwd = r.get("IsForward", "true") != "false"
            rl.append((rt, tgt, fwd))
            check_target(rt, ctx + " reftype")
            check_target(tgt, ctx + " ref")

    reftypes = [rt for rt, _, _ in rl]
    typedefs = [t for rt, t, _f in rl if rt == "HasTypeDefinition"]
    is_encoding = any(parse_nid(t) == (0, 76) for t in typedefs)
    category = el.find(NS + "Category")
    is_instance = category is not None and (category.text or "").strip() == build_model.CAT_INST

    if tag in ("UAObjectType", "UADataType", "UAVariableType", "UAReferenceType"):
        if not any(rt == "HasSubtype" and not fwd for rt, _, fwd in rl):
            errors.append(f"{ctx}: type without an inverse HasSubtype")

    if tag == "UAReferenceType" and el.get("Symmetric") != "true":
        if el.find(NS + "InverseName") is None:
            errors.append(f"{ctx}: asymmetric ReferenceType without an InverseName")

    if tag in ("UAVariable", "UAObject", "UAMethod"):
        if not typedefs and tag != "UAMethod":
            errors.append(f"{ctx}: missing HasTypeDefinition")
        # EnumStrings hangs off a DataType, not off a type declaration, so it carries no
        # ModellingRule - the base UA NodeSet models it the same way.
        is_enum_strings = bn == "EnumStrings"
        if ("HasModellingRule" not in reftypes and not is_encoding and not is_instance
                and not is_enum_strings):
            warnings.append(f"{ctx}: type member without a HasModellingRule")

    if tag == "UAVariable" and el.get("ValueRank") == "1" and "ArrayDimensions" not in el.attrib:
        warnings.append(f"{ctx}: array Variable without ArrayDimensions")

# --- DataType checks --------------------------------------------------------
for tag, el in elems:
    if tag != "UADataType":
        continue
    nid = el.get("NodeId")
    bn = el.get("BrowseName")
    ctx = f"UADataType {bn} ({nid})"
    refs = el.find(NS + "References")
    rl = [(r.get("ReferenceType"), r.text, r.get("IsForward", "true") != "false")
          for r in (refs if refs is not None else [])]
    supertype = next((t for rt, t, fwd in rl if rt == "HasSubtype" and not fwd), None)
    definition = el.find(NS + "Definition")
    if definition is None:
        errors.append(f"{ctx}: DataType without a Definition")
        continue
    fields = list(definition)

    if supertype == Structure:
        encodings = [t for rt, t, fwd in rl if rt == "HasEncoding" and fwd]
        if len(encodings) != len(build_model.ENCODINGS):
            errors.append(f"{ctx}: {len(encodings)} DataTypeEncoding objects, "
                          f"expected {len(build_model.ENCODINGS)}")
        for enc in encodings:
            p = parse_nid(enc)
            if p is None or p[1] not in defined:
                errors.append(f"{ctx}: encoding {enc} not defined here")
        for fld in fields:
            if not fld.get("DataType"):
                errors.append(f"{ctx}: structure field {fld.get('Name')} without a DataType")
            else:
                check_target(fld.get("DataType"), f"{ctx} field {fld.get('Name')}")
            if fld.find(NS + "Description") is None:
                warnings.append(f"{ctx}: structure field {fld.get('Name')} without a Description")
    elif supertype == Enumeration:
        values = [int(f.get("Value")) for f in fields]
        if values != sorted(values) or len(set(values)) != len(values):
            errors.append(f"{ctx}: enumeration values are not unique and ascending: {values}")
        es = next((t for rt, t, fwd in rl if rt == "HasProperty" and fwd), None)
        p = parse_nid(es) if es else None
        if p is None or p[1] not in defined:
            errors.append(f"{ctx}: enumeration without an EnumStrings Property")
        else:
            es_el = next(e for t, e in elems if e.get("NodeId") == es)
            if es_el.get("ArrayDimensions") != str(len(fields)):
                errors.append(f"{ctx}: EnumStrings length {es_el.get('ArrayDimensions')} "
                              f"does not match {len(fields)} enumeration fields")

# --- CSV consistency --------------------------------------------------------
with open(CSVF, encoding="utf-8") as f:
    rows = [r for r in csv.reader(f) if r]
csv_ids: dict[int, tuple[str, str]] = {}
for r in rows:
    if len(r) != 3:
        errors.append(f"csv: malformed row {r}")
        continue
    if not r[1].isdigit():
        errors.append(f"csv: non-numeric id in {r}")
        continue
    num = int(r[1])
    if num in csv_ids:
        errors.append(f"csv: duplicate id {num}")
    csv_ids[num] = (r[2], r[0])
for num, (tag, bn) in defined.items():
    if num not in csv_ids:
        errors.append(f"i={num} {bn} present in the NodeSet but missing from the CSV")
    elif csv_ids[num][0] != tag[2:]:
        errors.append(f"i={num}: NodeClass {tag[2:]} in the NodeSet, "
                      f"{csv_ids[num][0]} in the CSV")
for num in csv_ids:
    if num not in defined:
        errors.append(f"csv id {num} is not in the NodeSet")

# --- Well-known instance ----------------------------------------------------
inst = next((el for _t, el in elems if el.get("NodeId") == "i=65100"), None)
if inst is None:
    errors.append("the well-known DataChannelCapabilities instance i=65100 is missing")
elif inst.get("ParentNodeId") != ServerCapabilities:
    errors.append("DataChannelCapabilities is not parented by ServerCapabilities (i=2268)")

# --- Determinism ------------------------------------------------------------
for path, produced in ((XML, build_model.emit()), (CSVF, build_model.emit_csv()),
                       (ANNEX, build_model.emit_md())):
    with open(path, encoding="utf-8") as f:
        if f.read() != produced:
            errors.append(f"{os.path.basename(path)} differs from the generator output; "
                          "run tools/build_model.py")

# --- Annex embedding --------------------------------------------------------
with open(ANNEX, encoding="utf-8") as f:
    annex = f.read()
for name in DOCS:
    path = os.path.join(GEN, name)
    if not os.path.exists(path):
        errors.append(f"{name} is missing")
        continue
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if BEGIN_MARK not in text or END_MARK not in text:
        errors.append(f"{name}: model-reference markers are missing")
        continue
    embedded = text[text.index(BEGIN_MARK) + len(BEGIN_MARK):text.index(END_MARK)]
    if embedded.strip() != annex.strip():
        errors.append(f"{name}: the embedded Annex A differs from tools/model-reference.md")

# --- Report -----------------------------------------------------------------
base_note = f"{len(UA)} ids" if UA is not None else "skipped (no local base table)"
print(f"NodeSet nodes: {len(defined)}   CSV rows: {len(rows)}   base UA cross-check: {base_note}")
# --- AddressSpace figures agree with the model they draw ------------------------
# A node table is generated from the NodeSet and so cannot drift. A figure is authored,
# and a wrong arrow looks exactly like a right one, so it is re-derived from the model.
_fig_spec = os.path.join(GEN, 'OPC-UA-Data-Channels.md')
_fig_tools = os.path.abspath(os.path.join(HERE, "..", "..", "..", "word-drafts", "tools"))
if os.path.isdir(_fig_tools) and os.path.exists(_fig_spec):
    if _fig_tools not in sys.path:
        sys.path.insert(0, _fig_tools)
    try:
        from opcdocx import nodeset_diagram as _nd
    except ImportError as _exc:
        warnings.append(f"model-figure check skipped: {_exc}")
    else:
        try:
            errors.extend(_nd.check_markdown(_fig_spec, XML))
        except ValueError as _exc:
            errors.append(f"model figure: {_exc}")

print(f"ERRORS: {len(errors)}")
for e in errors[:50]:
    print("  ERR", e)
print(f"WARNINGS: {len(warnings)}")
for w in warnings[:40]:
    print("  WARN", w)
sys.exit(1 if errors else 0)
