#!/usr/bin/env python3
"""Local structural validator for the abstract xRegistry NodeSet + CSV."""
import os, sys, csv, re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.dirname(HERE)
REF = os.path.join(HERE, "ref")
NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"
XML = os.path.join(GEN, "Opc.Ua.XRegistry.NodeSet2.xml")
CSVF = os.path.join(GEN, "Opc.Ua.XRegistry.NodeIds.csv")
OWN_NS = 1
OWN_MIN = 63000

def load_ids(p):
    s = set()
    with open(p, encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[1].strip().isdigit():
                s.add(int(row[1]))
    return s

_ua_csv = os.path.join(REF, "UA.NodeIds.csv")
UA = load_ids(_ua_csv) if os.path.exists(_ua_csv) else None
UA_EXTRA = {297}
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
    if UA is None:
        return
    if v in UA or v in UA_EXTRA:
        return
    errors.append(f"{ctx}: i={v} not defined here and not a known base UA id")

for tag, el in elems:
    bn = el.get("BrowseName"); nid = el.get("NodeId")
    ctx = f"{tag} {bn} ({nid})"
    parsed = parse_numeric_nodeid(nid)
    if parsed and parsed[0] == OWN_NS and parsed[1] < OWN_MIN:
        errors.append(f"{ctx}: own NodeId below reserved draft block {OWN_MIN}")
    if el.get("ParentNodeId"):
        check(el.get("ParentNodeId"), ctx + " parent")
    if el.get("DataType"):
        check(el.get("DataType"), ctx + " datatype")
    refs = el.find(NS + "References"); rl = []
    if refs is not None:
        for r in refs:
            rt = r.get("ReferenceType"); tgt = r.text; fwd = r.get("IsForward", "true") != "false"
            rl.append((rt, tgt, fwd)); check(rt, ctx + " reftype"); check(tgt, ctx + " ref")
    reftypes = [rt for rt, _, _ in rl]
    typedef = [t for rt, t, f in rl if rt == "HasTypeDefinition"]
    is_enc = any(parse_numeric_nodeid(t) == (0, 76) for t in typedef)
    if tag in ("UAObjectType", "UADataType", "UAVariableType", "UAReferenceType"):
        if not any(rt == "HasSubtype" and not fwd for rt, _, fwd in rl):
            errors.append(f"{ctx}: type without HasSubtype(inverse)")
    if tag in ("UAVariable", "UAObject", "UAMethod") and el.get("ParentNodeId"):
        p = parse_numeric_nodeid(el.get("ParentNodeId"))
        wellknown_parent = p is not None and p[0] == 0
        if "HasModellingRule" not in reftypes and not is_enc and not wellknown_parent:
            warnings.append(f"{ctx}: instance/member without HasModellingRule")
        if tag in ("UAVariable", "UAObject") and not typedef and not is_enc:
            errors.append(f"{ctx}: missing HasTypeDefinition")

rows = [r for r in csv.reader(open(CSVF, encoding="utf-8")) if r]
csv_ids = {}
for r in rows:
    if len(r) != 3:
        errors.append(f"csv bad row {r}"); continue
    if not r[1].isdigit():
        errors.append(f"csv nonnumeric id {r}"); continue
    csv_ids[int(r[1])] = (r[2], r[0])
for num, (tag, bn) in defined.items():
    if num not in csv_ids:
        errors.append(f"ns={OWN_NS};i={num} {bn} missing from CSV")
    elif csv_ids[num][0] != tag[2:]:
        errors.append(f"class mismatch ns={OWN_NS};i={num}")
for cid in csv_ids:
    if cid not in defined:
        errors.append(f"csv id {cid} not in XML")

print(f"XML nodes: {len(defined)}   CSV rows: {len(rows)}   base ids: {len(UA) if UA is not None else 'skipped (no local base table)'}")
print(f"ERRORS: {len(errors)}")
for e in errors[:50]: print("  ERR", e)
print(f"WARNINGS: {len(warnings)}")
for w in warnings[:40]: print("  WARN", w)
sys.exit(1 if errors else 0)
