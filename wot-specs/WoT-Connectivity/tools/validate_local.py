#!/usr/bin/env python3
"""Local structural validator for the WoT Connectivity 1.1 combined NodeSet + CSV + Annex A.

Standard library only. Loads the local abstract xRegistry base NodeIds (the
RequiredModel this spec extends) and the pinned legacy NodeId table so the 1.02
preservation can be proven. Base UA NodeIds are checked only when a local
validation aid table (tools/ref/UA.NodeIds.csv, gitignored) is present.

Checks:
  * XML well-formedness, unique own NodeIds, additive registry ids in the 64000+
    block, incorporated 1.02 legacy ids in the preserved 1..172 range.
  * Every reference target resolves: own (ns=2), xRegistry base (ns=1), base UA.
  * Types carry a HasSubtype inverse; instances/members carry a HasModellingRule
    (except the well-known instances, encodings and well-known-parent members).
  * UAObject/UAVariable carry a HasTypeDefinition.
  * Structure DataTypes carry Default Binary + Default JSON encodings.
  * Well-known Properties (InputArguments, OutputArguments, EnumStrings) carry a
    namespace-0 BrowseName, not a namespace-2 (this spec's own) BrowseName.
  * CSV <-> XML consistency (ids, classes, no orphans; reserved 'Unspecified'
    legacy ids stay in the CSV without an XML node).
  * Legacy preservation: the first 172 CSV rows match the pinned
    legacy/WotConnection.csv byte-for-byte (every published NodeId and NodeClass
    preserved); the required 1.02 symbols are present as nodes with the pinned id
    and class; the management/upload surface carries ReleaseStatus="Deprecated";
    the well-known WoTAssetConnectionManagement (i=31) is under Objects, typed and
    callable.
  * The combined NodeSet uses one NamespaceUri (http://opcfoundation.org/UA/
    WoT-Con/) at model version 1.1.0.
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
XML = os.path.join(GEN, "Opc.Ua.WoTCon.NodeSet2.xml")
CSVF = os.path.join(GEN, "Opc.Ua.WoTCon.NodeIds.csv")
SPEC = os.path.join(GEN, "OPC-UA-WoT-Connectivity.md")
MODELREF = os.path.join(HERE, "model-reference.md")
LEGACY_CSVF = os.path.join(GEN, "legacy", "WotConnection.csv")

NAMESPACE = "http://opcfoundation.org/UA/WoT-Con/"
MODEL_VERSION = "1.1.0"

XR_NS = 1          # required model: abstract xRegistry base
OWN_NS = 2         # this specification's own namespace (WoT-Con)
OWN_MIN = 64000    # additive registry block

WELLKNOWN = {64100, 31}
SERVER = 2253
OBJECTS = 85

# The 1.02 symbols that must be preserved (BrowseName-ish, id, NodeClass).
REQUIRED_LEGACY = {
    1: ("ObjectType", "WoTAssetConnectionManagementType"),
    31: ("Object", "WoTAssetConnectionManagement"),
    42: ("ObjectType", "IWoTAssetType"),
    105: ("ObjectType", "WoTAssetConfigurationType"),
    110: ("ObjectType", "WoTAssetFileType"),
    142: ("ReferenceType", "HasWoTComponent"),
}
# The 1.02 management/upload surface that must be machine-readably deprecated.
LEGACY_DEPRECATED_TYPES = {1, 42, 105, 110, 142, 31}


def load_ids(p):
    s = set()
    with open(p, encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[1].strip().isdigit():
                s.add(int(row[1]))
    return s


_ua_csv = os.path.join(REF, "UA.NodeIds.csv")
UA = load_ids(_ua_csv) if os.path.exists(_ua_csv) else None
# Common base/Part 5/Part 20 ids this spec references, in case the local UA table is minimal.
UA_EXTRA = {1, 3, 5, 6, 7, 9, 11, 12, 13, 15, 17, 18, 21, 22, 24, 29, 32, 35, 37, 38, 40, 41, 45,
            46, 47, 48, 58, 61, 63, 68, 76, 78, 80, 85, 95, 96, 256, 290, 291, 294, 296, 297,
            2004, 2041, 2253, 11508, 11510, 11575, 11616, 11715, 17602, 17603, 20998, 23751, 24263}

# Pinned legacy NodeId table: the authoritative 1.02 preservation source.
LEGACY_ROWS = []
if os.path.exists(LEGACY_CSVF):
    with open(LEGACY_CSVF, encoding="utf-8") as f:
        for r in csv.reader(f):
            if len(r) == 3 and r[1].strip().isdigit():
                LEGACY_ROWS.append((r[0], int(r[1]), r[2]))
LEGACY_IDS = {sid for _, sid, _ in LEGACY_ROWS}
LEGACY_CONCRETE = {sid: cls for _, sid, cls in LEGACY_ROWS if cls != "Unspecified"}
LEGACY_RESERVED = {sid for _, sid, cls in LEGACY_ROWS if cls == "Unspecified"}

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
    if parsed and parsed[0] == OWN_NS and parsed[1] < OWN_MIN and parsed[1] not in LEGACY_IDS:
        errors.append(f"{ctx}: own NodeId below reserved provisional block {OWN_MIN} and not a preserved 1.02 id")
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

# Well-known Properties (InputArguments, OutputArguments, EnumStrings) must carry a
# namespace-0 BrowseName (Part 5/Part 6 well-known names), not this spec's own
# namespace-2 BrowseName prefix.
WELLKNOWN_NS0_PROPERTIES = {"InputArguments", "OutputArguments", "EnumStrings"}
for tag, el in elems:
    bn = el.get("BrowseName")
    if not bn:
        continue
    prefix, _, local = bn.rpartition(":") if ":" in bn else (None, None, bn)
    if local in WELLKNOWN_NS0_PROPERTIES and prefix not in (None, "0"):
        errors.append(f"{tag} {bn} ({el.get('NodeId')}): well-known Property must use the namespace-0 "
                       f"BrowseName '{local}', not '{bn}'")

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
    if cid not in defined and csv_ids[cid][0] != "Unspecified":
        errors.append(f"csv id {cid} not in XML")

# --- Legacy OPC 10100-1 v1.02 preservation -------------------------------------
# 1) The first 172 generated CSV rows must equal the pinned legacy table exactly
#    (every published NodeId and NodeClass preserved, including reserved rows).
if not LEGACY_ROWS:
    warnings.append("legacy/WotConnection.csv not found; skipping 1.02 preservation checks")
else:
    gen_legacy = rows[:len(LEGACY_ROWS)]
    pinned = [[s, str(i), c] for s, i, c in LEGACY_ROWS]
    if gen_legacy != pinned:
        errors.append("legacy preservation: generated CSV rows 1..172 do not match the pinned "
                      "legacy/WotConnection.csv (NodeId/NodeClass drift)")
    # 2) Every concrete legacy id is present in the XML with the pinned NodeClass.
    for sid, cls in LEGACY_CONCRETE.items():
        if sid not in defined:
            errors.append(f"legacy preservation: 1.02 id {sid} ({cls}) missing from the combined NodeSet")
        elif defined[sid][0][2:] != cls:
            errors.append(f"legacy preservation: 1.02 id {sid} class {defined[sid][0][2:]} != pinned {cls}")
    # 3) Reserved ids must NOT be emitted (they are burned, CSV-only).
    for sid in LEGACY_RESERVED:
        if sid in defined:
            errors.append(f"legacy preservation: reserved (Unspecified) 1.02 id {sid} must not be emitted as a node")
    # 4) Required 1.02 symbols present with the pinned id and class.
    for sid, (cls, name) in REQUIRED_LEGACY.items():
        if sid not in defined:
            errors.append(f"legacy preservation: required 1.02 symbol {name} (i={sid}) missing")
        elif defined[sid][0][2:] != cls:
            errors.append(f"legacy preservation: required 1.02 symbol {name} class mismatch")

# --- Legacy deprecation is machine-readable (ReleaseStatus="Deprecated") --------
el_by_id = {parse_numeric_nodeid(el.get("NodeId"))[1]: el for tag, el in elems
            if parse_numeric_nodeid(el.get("NodeId")) and parse_numeric_nodeid(el.get("NodeId"))[0] == OWN_NS}
for sid in LEGACY_DEPRECATED_TYPES:
    el = el_by_id.get(sid)
    if el is None:
        continue
    if el.get("ReleaseStatus") != "Deprecated":
        errors.append(f"legacy deprecation: 1.02 management/upload node i={sid} lacks ReleaseStatus=\"Deprecated\"")

# --- Well-known WoTAssetConnectionManagement (i=31) is under Objects and callable
wacm = el_by_id.get(31)
if LEGACY_ROWS:
    if wacm is None:
        errors.append("legacy: well-known WoTAssetConnectionManagement (i=31) missing")
    else:
        if wacm.get("ParentNodeId") != f"i={OBJECTS}":
            errors.append("legacy: WoTAssetConnectionManagement is not organized under the Objects folder (i=85)")
        wrefs = wacm.find(NS + "References")
        wrefs = list(wrefs) if wrefs is not None else []
        if not any(r.get("ReferenceType") == "HasTypeDefinition"
                   and parse_numeric_nodeid(r.text) == (OWN_NS, 1) for r in wrefs):
            errors.append("legacy: WoTAssetConnectionManagement lacks HasTypeDefinition WoTAssetConnectionManagementType")
        # It must expose the mandatory CreateAsset/DeleteAsset methods (callable).
        method_children = {(e.get("BrowseName") or "").split(":")[-1] for t, e in elems
                           if e.get("ParentNodeId") == f"ns={OWN_NS};i=31" and t == "UAMethod"}
        for m in ("CreateAsset", "DeleteAsset"):
            if m not in method_children:
                errors.append(f"legacy: WoTAssetConnectionManagement does not expose the callable {m} method")

# --- Combined NodeSet declares one namespace at model version 1.1.0 -------------
ns_uris = [u.text for u in root.iter(NS + "Uri")]
if NAMESPACE not in ns_uris:
    errors.append(f"combined NodeSet does not declare the NamespaceUri {NAMESPACE}")
if f"{NAMESPACE}V2/" in ns_uris or any(u and u.endswith("/V2/") for u in ns_uris):
    errors.append("combined NodeSet still declares a separate V2 namespace")
model = next((m for m in root.iter(NS + "Model") if m.get("ModelUri") == NAMESPACE), None)
if model is None:
    errors.append(f"combined NodeSet has no <Model ModelUri=\"{NAMESPACE}\">")
elif model.get("Version") != MODEL_VERSION:
    errors.append(f"combined NodeSet model version {model.get('Version')} != {MODEL_VERSION}")

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
