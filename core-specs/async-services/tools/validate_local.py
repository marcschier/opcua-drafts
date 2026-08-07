#!/usr/bin/env python3
"""
Local structural validator for the OPC UA Asynchronous Service Execution NodeSet, CSV
and Annex A, and for the agreement between the specification documents and the model.

Runs with no untracked base data, so it is part of the CI self-contained set. The
cross-check of base UA NodeIds is skipped when the gitignored `tools/ref/UA.NodeIds.csv`
aid is absent, exactly as the Data Channels validator does.

Usage (from repo root):  python core-specs/async-services/tools/validate_local.py
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

XML = os.path.join(GEN, "Opc.Ua.AsyncServices.NodeSet2.xml")
CSVF = os.path.join(GEN, "Opc.Ua.AsyncServices.NodeIds.csv")
ANNEX = os.path.join(HERE, "model-reference.md")

PART4 = "OPC-UA-Part4-Async-Service-Execution.md"
PART5 = "OPC-UA-Part5-Async-Service-Model.md"
COMBINED = "OPC-UA-Async-Services.md"
ALL_DOCS = (PART4, PART5, COMBINED)
# The Part 5 errata defines the model, and the combined spec is a self-contained merge of
# both errata; the Part 4 errata defines Services and carries no node table.
DOCS_WITH_ANNEX = (PART5, COMBINED)

BEGIN_MARK = "<!-- BEGIN GENERATED: model-reference -->"
END_MARK = "<!-- END GENERATED: model-reference -->"

sys.path.insert(0, HERE)
import build_model  # noqa: E402

# The reserved provisional ranges, mirroring build_model.py. Anything outside them is
# either a base UA NodeId or a mistake.
OWN_RANGES = ((70000, 70199), (70900, 70999), (71000, 74999))
INSTANCE_MIN, INSTANCE_MAX = build_model.INSTANCE_MIN, build_model.INSTANCE_MAX

ServerCapabilities = "i=2268"
ServerDiagnostics = "i=2274"
Structure = "i=22"
Enumeration = "i=29"

# The StatusCodes this draft introduces, and the ones it reuses. A code that appears in a
# document but in neither list is either a typo or a code someone added without recording
# it, and clause 9 of the Part 4 errata is where the reader looks for both.
NEW_STATUS_CODES = (
    "Bad_DeferralNotSupported",
    "Bad_DeferredRequestExpired",
    "Bad_DeferredRequestUnknown",
    "Bad_RequestHandleInUse",
    "Bad_TooManyDeferredRequests",
)
REUSED_STATUS_CODES = (
    "Bad_CertificateInvalid",
    "Bad_ConfigurationError",
    "Bad_DeviceFailure",
    "Bad_InvalidState",
    "Bad_NoCommunication",
    "Bad_NotConnected",
    "Bad_NothingToDo",
    "Bad_RequestCancelledByClient",
    "Bad_RequestCancelledByRequest",
    "Bad_RequestNotComplete",
    "Bad_SecurityModeInsufficient",
    "Bad_ServerTooBusy",
    "Bad_ServiceUnsupported",
    "Bad_SessionClosed",
    "Bad_SessionIdInvalid",
    "Bad_SessionNotActivated",
    "Bad_Shutdown",
    "Bad_Timeout",
    "Bad_TooManyOperations",
    "Bad_TransactionPending",
    "Bad_UserAccessDenied",
    "Good_CompletesAsynchronously",
)

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
UA_EXTRA = {2268, 2274, 2253, 2041, 2052, 2069, 76, 25, 288, 289, 290, 294, 389, 392}

NID_RE = re.compile(r"^(?:ns=(\d+);)?i=(\d+)$")
ALIAS: dict[str, str] = {}


def parse_nid(text):
    text = ALIAS.get(text, text)
    m = NID_RE.match(text or "")
    if not m:
        return None
    return int(m.group(1) or 0), int(m.group(2))


def read_doc(name):
    path = os.path.join(GEN, name)
    if not os.path.exists(path):
        errors.append(f"{name} is missing")
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


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
    # A well-known instance is identified by its reserved id range rather than by its
    # <Category>, which carries conformance units and not the generator's grouping.
    is_instance = INSTANCE_MIN <= num <= INSTANCE_MAX

    if tag in ("UAObjectType", "UADataType", "UAVariableType", "UAReferenceType"):
        if not any(rt == "HasSubtype" and not fwd for rt, _, fwd in rl):
            errors.append(f"{ctx}: type without an inverse HasSubtype")

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

# --- Every declared member is Mandatory -------------------------------------
# A conformance unit has to be executable against a legal Server, and every member of this
# model is named by one. An Optional member would make the unit that tests it unverifiable:
# a Server could omit the member and still conform. Where a capability is genuinely absent
# the model expresses it as a value - 0, FALSE, an empty array - which a Client can read.
for tag, el in elems:
    if tag != "UAVariable" or (el.get("BrowseName") or "") == "EnumStrings":
        continue
    refs = el.find(NS + "References")
    rl = [(r.get("ReferenceType"), r.text) for r in (refs if refs is not None else [])]
    rule = next((t for rt, t in rl if rt == "HasModellingRule"), None)
    if rule is not None and parse_nid(rule) != (0, 78):
        errors.append(f"UAVariable {el.get('BrowseName')} ({el.get('NodeId')}): "
                      "member is not Mandatory, so a conformance unit naming it cannot be "
                      "tested against a legal Server")

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

# --- Well-known instances ---------------------------------------------------
for nid, parent, parent_name in (("i=70100", ServerCapabilities, "ServerCapabilities"),
                                 ("i=70101", ServerDiagnostics, "ServerDiagnostics")):
    inst = next((el for _t, el in elems if el.get("NodeId") == nid), None)
    if inst is None:
        errors.append(f"the well-known instance {nid} is missing")
    elif inst.get("ParentNodeId") != parent:
        errors.append(f"{inst.get('BrowseName')} is not parented by "
                      f"{parent_name} ({parent})")

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
for name in DOCS_WITH_ANNEX:
    text = read_doc(name)
    if text is None:
        continue
    if BEGIN_MARK not in text or END_MARK not in text:
        errors.append(f"{name}: model-reference markers are missing")
        continue
    embedded = text[text.index(BEGIN_MARK) + len(BEGIN_MARK):text.index(END_MARK)]
    if embedded.strip() != annex.strip():
        errors.append(f"{name}: the embedded Annex A differs from tools/model-reference.md")

# --- Specification and model agree, in both directions ----------------------
docs = {name: read_doc(name) for name in ALL_DOCS}
prose = "\n".join(t for t in docs.values() if t)

# The generator emits a conformance unit as a <Category>; the documents have to define it.
emitted_units = {(c.text or "").strip() for _t, el in elems
                 for c in el.findall(NS + "Category")}
for unit in sorted(emitted_units):
    if unit not in build_model.ALL_CONFORMANCE_UNITS:
        errors.append(f"conformance unit {unit} is emitted but is not in "
                      "build_model.ALL_CONFORMANCE_UNITS")
for unit in build_model.ALL_CONFORMANCE_UNITS:
    if prose and unit not in prose:
        errors.append(f"conformance unit {unit} is declared by the generator but named in "
                      "no specification document")
for unit in sorted(set(re.findall(r"\bASE-[A-Za-z]+\b", prose))):
    if unit not in build_model.ALL_CONFORMANCE_UNITS:
        errors.append(f"conformance unit {unit} is named in a document but is not declared "
                      "by the generator")

# Every type the model declares has to be described somewhere, and every type name the
# prose uses has to exist. Checking one direction only lets the other drift. Both
# directions are checked against the text with Annex A removed: the annex lists every
# type by construction, so leaving it in would make the first direction vacuous.
annex_free = {name: re.sub(re.escape(BEGIN_MARK) + r".*?" + re.escape(END_MARK), "",
                           text or "", flags=re.S)
              for name, text in docs.items()}
hand_written = "\n".join(annex_free.values())
own_types = sorted(bn for _num, (tag, bn) in defined.items()
                   if tag in ("UAObjectType", "UADataType"))
for name in own_types:
    if hand_written and name not in hand_written:
        errors.append(f"{name} is declared by the model but is described in no specification "
                      "document outside the generated annex")
declared = set(own_types) | {bn for _num, (_tag, bn) in defined.items()}
for name, text in annex_free.items():
    for used in set(re.findall(r"\b([A-Z][A-Za-z]*(?:EventType|DataType|Type))\b", text)):
        if used.startswith(("AsyncService", "Deferral", "DeferredRequest")) \
                and used not in declared:
            errors.append(f"{name}: names {used}, which the model does not declare")

# --- StatusCodes ------------------------------------------------------------
def _slice(text, start, end):
    if not text:
        return ""
    i = text.find(start)
    j = text.find(end)
    return text[i:j] if 0 <= i < j else ""


part4 = docs.get(PART4) or ""
# Scoped to the StatusCodes clause, not to the whole document: every code is also used in
# the clause that returns it, so a whole-document search could never notice a code that
# was dropped from the table a reader consults to look it up.
status_clause = _slice(part4, "\n## 9 StatusCodes", "\n## 10 Conformance units")
if part4 and not status_clause:
    errors.append(f"{PART4}: the StatusCodes clause could not be located")
for code in NEW_STATUS_CODES:
    if status_clause and code not in status_clause:
        errors.append(f"StatusCode {code} is not listed in the StatusCodes clause of {PART4}")
known_codes = set(NEW_STATUS_CODES) | set(REUSED_STATUS_CODES)
for name, text in docs.items():
    if not text:
        continue
    for code in sorted(set(re.findall(r"\b(?:Bad|Good|Uncertain)_[A-Za-z]+\b", text))):
        if code not in known_codes:
            errors.append(f"{name}: uses StatusCode {code}, which is in neither the new nor "
                          "the reused list of this validator")

# --- The combined spec does not drift from the errata it merges -------------
# The combined document restates the Part 4 Service clauses, and those clauses number
# identically in both (5 The Continue Service .. 8 Interaction with other Services), so a
# normative paragraph of one has to be a normative paragraph of the other, character for
# character. Checking only that both exist would let a `shall` be tightened in one and not
# the other, which is the failure mode a merged read invites.
p4_services = _slice(annex_free.get(PART4, ""), "\n## 5 The Complete Service",
                     "\n## 9 StatusCodes")
combined_services = _slice(annex_free.get(COMBINED, ""), "\n## 5 The Complete Service",
                           "\n## 9 The information model")
if p4_services and combined_services:
    for para in p4_services.split("\n"):
        para = para.rstrip()
        if "**shall" not in para:
            continue
        # A paragraph that cites a sibling document by name is the one thing that must
        # differ: the combined read carries the same rule pointing at its own clauses.
        if "Part 5 errata" in para or "Part 4 errata" in para:
            continue
        if para not in combined_services:
            errors.append(f"{COMBINED}: a normative paragraph of {PART4} clauses 5-8 is "
                          f"missing or altered: {para[:110]!r}")
else:
    errors.append("could not locate clauses 5-8 in both the Part 4 errata and the combined "
                  "specification; the drift check did not run")

# --- The security control the prose defines is in the model too --------------
# Part 5 clause 6 requires the encryption restriction on DeferredRequests to be expressed
# through the AccessRestrictions Attribute, "so a Client can discover it by reading rather
# than by failing". A code generator consuming the NodeSet is the normal path for an OPC UA
# stack, so a NodeSet without the Attribute produces a Server the prose forbids.
ENCRYPTION_REQUIRED = 2
_dr = next((el for _t, el in elems if (el.get("BrowseName") or "") == "DeferredRequests"),
           None)
if _dr is None:
    errors.append("the DeferredRequests Variable is missing from the model")
else:
    _ar = _dr.get("AccessRestrictions")
    if _ar is None or not _ar.isdigit() or not int(_ar) & ENCRYPTION_REQUIRED:
        errors.append("DeferredRequests carries AccessRestrictions "
                      f"{_ar!r}, which does not set the EncryptionRequired bit "
                      f"({ENCRYPTION_REQUIRED}); the Part 5 errata clause 6 requires the "
                      "model to state the restriction its prose defines")

# --- AddressSpace figures ---------------------------------------------------
# Each `<!-- model-figure -->` diagram is re-derived from the NodeSet, so a figure that
# draws a Node, a member or a Reference the model does not have fails here.
_fig_spec = os.path.join(GEN, 'OPC-UA-Async-Services.md')
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

# --- Report -----------------------------------------------------------------
base_note = f"{len(UA)} ids" if UA is not None else "skipped (no local base table)"
print(f"NodeSet nodes: {len(defined)}   CSV rows: {len(rows)}   "
      f"conformance units: {len(build_model.ALL_CONFORMANCE_UNITS)}   "
      f"base UA cross-check: {base_note}")
print(f"ERRORS: {len(errors)}")
for e in errors[:50]:
    print("  ERR", e)
print(f"WARNINGS: {len(warnings)}")
for w in warnings[:40]:
    print("  WARN", w)
sys.exit(1 if errors else 0)
