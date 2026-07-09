#!/usr/bin/env python3
"""Local structural validator for the ns0 PubSub Binding nodeset + CSV."""
import os, sys, csv, re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
# The generated NodeSet/CSV live in core-specs/scenario-binding; this validator lives under core-specs/extras.
GEN = os.path.abspath(os.path.join(HERE, "..", "..", "..", "scenario-binding"))
REF = os.path.join(HERE, "ref")
NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"
XML = os.path.join(GEN, "Opc.Ua.ScenarioBinding.NodeSet2.xml")
CSVF = os.path.join(GEN, "Opc.Ua.ScenarioBinding.NodeIds.csv")

def load_ids(p):
    s = set()
    with open(p, encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[1].strip().isdigit():
                s.add(int(row[1]))
    return s

_ua_csv = os.path.join(REF, "UA.NodeIds.csv")
# Base UA NodeId table is a local validation aid (not distributed). When absent,
# base-id resolution is skipped: any id below the provisional block is assumed to
# be a valid base id, and only ids in the provisional block must be defined here.
UA = load_ids(_ua_csv) if os.path.exists(_ua_csv) else None
UA_EXTRA = {297}  # Argument encoding used in method args
errors, warnings = [], []
ALIAS = {}
tree = ET.parse(XML)
root = tree.getroot()
defined = {}
elems = []
for el in root:
    tag = el.tag.replace(NS, "")
    if tag == "Aliases":
        for a in el:
            ALIAS[a.get("Alias")] = a.text
    if not tag.startswith("UA"):
        continue
    nid = el.get("NodeId")
    if nid and nid.startswith("i="):
        num = int(nid.split("=")[1])
        if num in defined:
            errors.append(f"dup NodeId i={num}")
        defined[num] = (tag, el.get("BrowseName"))
    elems.append((tag, el))

def resolve(t):
    t = ALIAS.get(t, t)
    if t.startswith("i="):
        return int(t.split("=")[1])
    return None

OWN_MIN = 60000

def check(t, ctx):
    v = resolve(t)
    if v is None:
        return
    if v in defined:
        return
    if UA is None:
        if v < OWN_MIN:
            return  # assume valid base id (base table not available locally)
    elif v in UA or v in UA_EXTRA:
        return
    errors.append(f"{ctx}: i={v} not defined here and not a known base id")

OWN_MIN = 60000
for tag, el in elems:
    bn = el.get("BrowseName"); nid = el.get("NodeId")
    ctx = f"{tag} {bn} ({nid})"
    num = int(nid.split("=")[1]) if nid and nid.startswith("i=") else None
    if num is not None and num >= OWN_MIN and UA is not None and num in UA:
        errors.append(f"{ctx}: provisional id collides with a base UA id")
    if el.get("ParentNodeId"): check(el.get("ParentNodeId"), ctx+" parent")
    if el.get("DataType"): check(el.get("DataType"), ctx+" datatype")
    refs = el.find(NS+"References"); rl=[]
    if refs is not None:
        for r in refs:
            rt=r.get("ReferenceType"); tgt=r.text; fwd=r.get("IsForward","true")!="false"
            rl.append((rt,tgt,fwd)); check(rt,ctx+" reftype"); check(tgt,ctx+" ref")
    reftypes=[rt for rt,_,_ in rl]
    typedef=[t for rt,t,f in rl if rt=="HasTypeDefinition"]
    is_enc = any(resolve(t)==76 for t in typedef)
    if tag in ("UAObjectType","UADataType","UAVariableType","UAReferenceType"):
        if not any(rt=="HasSubtype" and not fwd for rt,_,fwd in rl):
            errors.append(f"{ctx}: type without HasSubtype(inverse)")
    if tag in ("UAVariable","UAObject","UAMethod") and el.get("ParentNodeId"):
        num_p = resolve(el.get("ParentNodeId"))
        wellknown = num_p is not None and (num_p in UA if UA is not None else num_p < OWN_MIN)
        if "HasModellingRule" not in reftypes and not is_enc and not wellknown \
           and bn not in ("EnumStrings",) and num not in (60101,) and num < 60110:
            warnings.append(f"{ctx}: instance without HasModellingRule")
        if tag in ("UAVariable","UAObject") and not typedef and not is_enc:
            errors.append(f"{ctx}: missing HasTypeDefinition")

# CSV consistency
rows=[r for r in csv.reader(open(CSVF,encoding="utf-8")) if r]
csv_ids={}
for r in rows:
    if len(r)!=3: errors.append(f"csv bad row {r}"); continue
    csv_ids[int(r[1])]=(r[2],r[0])
for num,(tag,bn) in defined.items():
    if num not in csv_ids: errors.append(f"i={num} {bn} missing from CSV")
    elif csv_ids[num][0]!=tag[2:]: errors.append(f"class mismatch i={num}")
for cid in csv_ids:
    if cid not in defined: errors.append(f"csv id {cid} not in XML")

print(f"XML nodes: {len(defined)}   CSV rows: {len(rows)}   base ids: {len(UA) if UA is not None else 'skipped (no local base table)'}")
print(f"ERRORS: {len(errors)}")
for e in errors[:50]: print("  ERR", e)
print(f"WARNINGS: {len(warnings)}")
for w in warnings[:40]: print("  WARN", w)
sys.exit(1 if errors else 0)
