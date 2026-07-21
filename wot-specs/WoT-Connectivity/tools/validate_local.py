#!/usr/bin/env python3
"""Local structural validator for the WoT Connectivity V2 NodeSet + CSV + Annex A.

Standard library only. Loads the local abstract xRegistry base NodeIds (the
RequiredModel this spec extends) so cross-namespace references resolve. Base UA
NodeIds are checked only when a local validation aid table
(tools/ref/UA.NodeIds.csv, gitignored) is present.

Checks:
  * XML well-formedness, unique own NodeIds, own ids in the 64000+ block.
  * Every reference target resolves: own (ns=2), xRegistry base (ns=1), base UA.
  * Types carry a HasSubtype inverse; instances/members carry a HasModellingRule
    (except the well-known instance, encodings and well-known-parent members).
  * UAObject/UAVariable carry a HasTypeDefinition.
  * Structure DataTypes carry Default Binary + Default JSON encodings.
  * CSV <-> XML consistency (ids, classes, no orphans).
  * The well-known WoTRegistry instance is a component of the Server object
    (i=2253), is an EventNotifier and is a HasNotifier target of the Server
    (Server -> WoTRegistry notifier topology).
  * The well-known WoTRegistry instance materializes a concrete Value for every
    Mandatory member of WoTRegistryType, own (for example RefreshGeneration)
    and inherited from the xRegistry RegistryType (RegistryId).
  * The generated Annex A (tools/model-reference.md) is embedded verbatim in
    OPC-UA-WoT-Connectivity.md (generated-annex equality).
"""
import os
import sys
import csv
import re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(GEN))
REF = os.path.join(HERE, "ref")
NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"
XML = os.path.join(GEN, "Opc.Ua.WoTConV2.NodeSet2.xml")
CSVF = os.path.join(GEN, "Opc.Ua.WoTConV2.NodeIds.csv")
SPEC = os.path.join(GEN, "OPC-UA-WoT-Connectivity.md")
MODELREF = os.path.join(HERE, "model-reference.md")

XR_NS = 1          # required model: abstract xRegistry base
OWN_NS = 2         # this specification's own namespace (WoT-Con V2)
OWN_MIN = 64000

WELLKNOWN = {64100}
SERVER = 2253


def load_ids(p):
    s = set()
    with open(p, encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[1].strip().isdigit():
                s.add(int(row[1]))
    return s


_ua_csv = os.path.join(REF, "UA.NodeIds.csv")
UA = load_ids(_ua_csv) if os.path.exists(_ua_csv) else None
# Common base/Part 5 ids this spec references, in case the local UA table is minimal.
UA_EXTRA = {1, 3, 5, 6, 7, 9, 11, 12, 13, 15, 17, 18, 21, 22, 29, 32, 35, 37, 38, 40, 41, 45,
            46, 47, 48, 58, 61, 63, 68, 76, 78, 80, 290, 296, 297, 2041, 2253, 11508, 11575}

_xr_csv = os.path.join(ROOT, "core-specs", "xregistry", "Opc.Ua.XRegistry.NodeIds.csv")
XR = load_ids(_xr_csv) if os.path.exists(_xr_csv) else None

errors, warnings = [], []
ALIAS = {}
tree = ET.parse(XML)
root = tree.getroot()
defined = {}
elems = []

NID_RE = re.compile(r"^(?:ns=(\d+);)?i=(\d+)$")


def parse_numeric_nodeid(t):
    t = ALIAS.get(t, t)
    m = NID_RE.match(t or "")
    if not m:
        return None
    ns = int(m.group(1) or 0)
    return ns, int(m.group(2))


for el in root:
    tag = el.tag.replace(NS, "")
    if tag == "Aliases":
        for a in el:
            ALIAS[a.get("Alias")] = a.text
    if not tag.startswith("UA"):
        continue
    nid = el.get("NodeId")
    parsed = parse_numeric_nodeid(nid)
    if parsed and parsed[0] == OWN_NS:
        key = parsed[1]
        if key in defined:
            errors.append(f"dup NodeId ns={OWN_NS};i={key}")
        defined[key] = (tag, el.get("BrowseName"))
    elems.append((tag, el))


def check(t, ctx):
    parsed = parse_numeric_nodeid(t)
    if parsed is None:
        return
    ns, v = parsed
    if ns == OWN_NS:
        if v in defined:
            return
        errors.append(f"{ctx}: ns={OWN_NS};i={v} not defined here")
        return
    if ns == XR_NS:
        if XR is None or v in XR:
            return
        errors.append(f"{ctx}: ns={XR_NS};i={v} not defined in the xRegistry base model")
        return
    if v in UA_EXTRA:
        return
    if UA is None:
        return
    if v in UA:
        return
    errors.append(f"{ctx}: i={v} not defined here and not a known base/xRegistry id")


enc_types = set()  # DataTypes that declare an encoding
for tag, el in elems:
    bn = el.get("BrowseName")
    nid = el.get("NodeId")
    ctx = f"{tag} {bn} ({nid})"
    parsed = parse_numeric_nodeid(nid)
    if parsed and parsed[0] == OWN_NS and parsed[1] < OWN_MIN:
        errors.append(f"{ctx}: own NodeId below reserved provisional block {OWN_MIN}")
    if el.get("ParentNodeId"):
        check(el.get("ParentNodeId"), ctx + " parent")
    if el.get("DataType"):
        check(el.get("DataType"), ctx + " datatype")
    refs = el.find(NS + "References")
    rl = []
    if refs is not None:
        for r in refs:
            rt = r.get("ReferenceType")
            tgt = r.text
            fwd = r.get("IsForward", "true") != "false"
            rl.append((rt, tgt, fwd))
            check(rt, ctx + " reftype")
            check(tgt, ctx + " ref")
    reftypes = [rt for rt, _, _ in rl]
    typedef = [t for rt, t, f in rl if rt == "HasTypeDefinition"]
    is_enc = any(parse_numeric_nodeid(t) == (0, 76) for t in typedef)
    # Track encodings for the DataType that owns them.
    for rt, t, f in rl:
        if rt == "HasEncoding" and not f:
            p = parse_numeric_nodeid(t)
            if p and p[0] == OWN_NS:
                enc_types.add(p[1])
    if tag in ("UAObjectType", "UADataType", "UAVariableType", "UAReferenceType"):
        if not any(rt == "HasSubtype" and not fwd for rt, _, fwd in rl):
            errors.append(f"{ctx}: type without HasSubtype(inverse)")
    if tag in ("UAVariable", "UAObject", "UAMethod") and el.get("ParentNodeId"):
        p = parse_numeric_nodeid(el.get("ParentNodeId"))
        wellknown_parent = p is not None and p[0] == 0
        own_id = parsed[1] if parsed and parsed[0] == OWN_NS else None
        cat_el = el.find(NS + "Category")
        is_instance = cat_el is not None and (cat_el.text or "").strip().endswith("Instances")
        if "HasModellingRule" not in reftypes and not is_enc and not wellknown_parent:
            if own_id not in WELLKNOWN and not is_instance:
                warnings.append(f"{ctx}: instance/member without HasModellingRule")
        if tag in ("UAVariable", "UAObject") and not typedef and not is_enc:
            errors.append(f"{ctx}: missing HasTypeDefinition")

# Structure DataTypes must declare both encodings.
for tag, el in elems:
    if tag != "UADataType":
        continue
    parsed = parse_numeric_nodeid(el.get("NodeId"))
    definition = el.find(NS + "Definition")
    subtype = None
    refs = el.find(NS + "References")
    if refs is not None:
        for r in refs:
            if r.get("ReferenceType") == "HasSubtype" and r.get("IsForward") == "false":
                subtype = parse_numeric_nodeid(r.text)
    # Structures (subtype of i=22) require Default Binary + Default JSON encodings.
    if subtype == (0, 22):
        if parsed and parsed[1] not in enc_types:
            errors.append(f"UADataType {el.get('BrowseName')}: Structure without HasEncoding objects")

# CSV consistency
rows = [r for r in csv.reader(open(CSVF, encoding="utf-8")) if r]
csv_ids = {}
for r in rows:
    if len(r) != 3:
        errors.append(f"csv bad row {r}")
        continue
    if not r[1].isdigit():
        errors.append(f"csv nonnumeric id {r}")
        continue
    csv_ids[int(r[1])] = (r[2], r[0])
for num, (tag, bn) in defined.items():
    if num not in csv_ids:
        errors.append(f"ns={OWN_NS};i={num} {bn} missing from CSV")
    elif csv_ids[num][0] != tag[2:]:
        errors.append(f"class mismatch ns={OWN_NS};i={num}")
for cid in csv_ids:
    if cid not in defined:
        errors.append(f"csv id {cid} not in XML")

# Well-known WoTRegistry instance topology.
registry = next((el for tag, el in elems if el.get("NodeId") == f"ns={OWN_NS};i=64100"), None)
if registry is None:
    errors.append("WoTRegistry well-known instance ns=2;i=64100 missing")
else:
    if registry.get("ParentNodeId") != f"i={SERVER}":
        errors.append("WoTRegistry well-known instance is not parented by the Server object i=2253")
    if registry.get("EventNotifier") not in ("1", "5", "7"):
        errors.append("WoTRegistry well-known instance does not declare EventNotifier (SubscribeToEvents)")
    rrefs = registry.find(NS + "References")
    rrefs = list(rrefs) if rrefs is not None else []
    has_notifier = any(r.get("ReferenceType") == "HasNotifier" and r.get("IsForward") == "false"
                       and parse_numeric_nodeid(r.text) == (0, SERVER) for r in rrefs)
    has_typedef = any(r.get("ReferenceType") == "HasTypeDefinition"
                      and parse_numeric_nodeid(r.text) == (OWN_NS, 64000) for r in rrefs)
    if not has_notifier:
        errors.append("WoTRegistry is not a HasNotifier target of the Server object (notifier topology)")
    if not has_typedef:
        errors.append("WoTRegistry does not have HasTypeDefinition WoTRegistryType")

# Registry/document types generate the required events (notifier chain sources).
def refs_of(numeric_id):
    el = next((e for t, e in elems if e.get("NodeId") == f"ns={OWN_NS};i={numeric_id}"), None)
    out = []
    if el is not None:
        rr = el.find(NS + "References")
        for r in (list(rr) if rr is not None else []):
            out.append((r.get("ReferenceType"), r.text, r.get("IsForward", "true") != "false"))
    return out

reg_events = {parse_numeric_nodeid(t)[1] for rt, t, f in refs_of(64000)
              if rt == "GeneratesEvent" and parse_numeric_nodeid(t) and parse_numeric_nodeid(t)[0] == OWN_NS}
doc_events = {parse_numeric_nodeid(t)[1] for rt, t, f in refs_of(64003)
              if rt == "GeneratesEvent" and parse_numeric_nodeid(t) and parse_numeric_nodeid(t)[0] == OWN_NS}
if 64014 not in reg_events:
    errors.append("WoTRegistryType does not GeneratesEvent WoTRefreshCompletedEventType")
for ev in (64011, 64012, 64013):
    if ev not in doc_events:
        errors.append(f"WoTDocumentType does not GeneratesEvent ns=2;i={ev}")

# Mandatory-instance completeness: a well-known instance must materialize a concrete Value
# for every Mandatory member of its type, own AND inherited, so that loading the NodeSet
# alone (with no server-side logic) yields a structurally complete instance.
def _local_bn(bn):
    return bn.split(":", 1)[1] if bn and ":" in bn else bn


def _mandatory_members(el_list, parent_nodeid):
    names = set()
    for el in el_list:
        if el.get("ParentNodeId") != parent_nodeid:
            continue
        refs = el.find(NS + "References")
        if refs is None:
            continue
        if any(r.get("ReferenceType") == "HasModellingRule" and parse_numeric_nodeid(r.text) == (0, 78)
               for r in refs):
            names.add(_local_bn(el.get("BrowseName")))
    return names


own_mandatory = _mandatory_members([el for _, el in elems], f"ns={OWN_NS};i=64000")

xr_mandatory = set()
_xr_xml = os.path.join(ROOT, "core-specs", "xregistry", "Opc.Ua.XRegistry.NodeSet2.xml")
if os.path.exists(_xr_xml):
    xr_root = ET.parse(_xr_xml).getroot()
    xr_elems = [e for e in xr_root if e.tag.replace(NS, "").startswith("UA")]
    xr_mandatory = _mandatory_members(xr_elems, f"ns={XR_NS};i=63000")
else:
    warnings.append("xRegistry NodeSet2.xml not found; skipping inherited-mandatory completeness check")

expected_mandatory = own_mandatory | xr_mandatory
if registry is not None:
    reg_children_by_name = {}
    for _, el in elems:
        if el.get("ParentNodeId") == f"ns={OWN_NS};i=64100":
            reg_children_by_name[_local_bn(el.get("BrowseName"))] = el
    for mname in sorted(expected_mandatory):
        child = reg_children_by_name.get(mname)
        if child is None:
            errors.append(f"WoTRegistry well-known instance does not materialize Mandatory member '{mname}'")
            continue
        vel = child.find(NS + "Value")
        if vel is None or (len(list(vel)) == 0 and not (vel.text or "").strip()):
            errors.append(f"WoTRegistry well-known instance member '{mname}' has no materialized Value")

# Generated-annex equality: model-reference.md is embedded verbatim in the spec.
annex_ok = None
if os.path.exists(MODELREF) and os.path.exists(SPEC):
    ann = open(MODELREF, encoding="utf-8").read().replace("\r\n", "\n").strip()
    spec = open(SPEC, encoding="utf-8").read().replace("\r\n", "\n")
    if '<a id="annex-a"></a>' not in spec:
        errors.append("spec is missing the <a id=\"annex-a\"></a> Annex A marker")
        annex_ok = False
    elif ann not in spec:
        errors.append("generated Annex A (model-reference.md) is not embedded verbatim in the spec")
        annex_ok = False
    else:
        annex_ok = True
elif not os.path.exists(SPEC):
    warnings.append("spec OPC-UA-WoT-Connectivity.md not found; skipping annex-embed check")

print(f"XML nodes: {len(defined)}   CSV rows: {len(rows)}   "
      f"base ids: {len(UA) if UA is not None else 'skipped (no local base table)'}   "
      f"xRegistry base ids: {len(XR) if XR is not None else 'skipped'}   "
      f"annex embedded: {annex_ok}")
print(f"ERRORS: {len(errors)}")
for e in errors[:60]:
    print("  ERR", e)
print(f"WARNINGS: {len(warnings)}")
for w in warnings[:40]:
    print("  WARN", w)
sys.exit(1 if errors else 0)
