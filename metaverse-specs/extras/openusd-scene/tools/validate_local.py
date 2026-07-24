#!/usr/bin/env python3
"""
Local structural + modelling-rule validator for the OpenUSD Scene Materialization NodeSet.

Reproducible in-repo gate. Checks, against Opc.Ua.OpenUsdScene.NodeSet2.xml:
  * XML well-formedness and single <Model> with only a base-UA <RequiredModel>.
  * Unique NodeIds; every reference target resolves (own ns=1 node or known base-UA id).
  * Every UAObjectType/UAVariableType/UADataType/UAReferenceType has an inverse HasSubtype to a base.
  * Every instance-declaration member (has ParentNodeId) has a HasTypeDefinition and,
    unless it is a documented type-level constant, a HasModellingRule.
  * ParentNodeId is backed by an inverse hierarchical reference.
  * Forward/inverse hierarchical reference pairs are consistent.
  * Enum EnumStrings ArrayDimensions equals the number of enum fields.
Exit code 0 and "OK" on success; non-zero with an ERRORS list otherwise.
"""
from __future__ import annotations
import os
import sys
import xml.etree.ElementTree as ET

NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"

# Base-UA NodeIds that this model legitimately references (namespace 0).
KNOWN_BASE = {
    "i=1", "i=2", "i=6", "i=7", "i=8", "i=10", "i=11", "i=12", "i=15",
    "i=17", "i=20", "i=21", "i=22", "i=24", "i=29", "i=32", "i=35",
    "i=37", "i=40", "i=44", "i=45", "i=46", "i=47", "i=58", "i=61",
    "i=62", "i=63", "i=68", "i=78", "i=80", "i=290", "i=11508",
    "i=17602", "i=17603", "i=17604",
}
HIER = {"i=47", "i=46", "i=35", "i=17603", "i=17604"}
NO_RULE_OK = {"DefaultInstanceBrowseName"}

ERR = []


def err(m):
    ERR.append(m)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.normpath(os.path.join(here, "..", "..", "..", "openusd-scene",
                                          "Opc.Ua.OpenUsdScene.NodeSet2.xml"))
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        print(f"ERRORS: 1\n  XML parse error: {e}")
        sys.exit(1)
    root = tree.getroot()

    models = root.findall(f"{NS}Models/{NS}Model")
    if len(models) != 1:
        err(f"expected exactly one <Model>, found {len(models)}")
    else:
        reqs = models[0].findall(f"{NS}RequiredModel")
        if len(reqs) != 1 or reqs[0].get("ModelUri") != "http://opcfoundation.org/UA/":
            err("expected exactly one <RequiredModel> for the base UA namespace")

    nodes = [e for e in root if e.tag.startswith(NS) and e.tag[len(NS):].startswith("UA")]
    by_id = {}
    for n in nodes:
        nid = n.get("NodeId")
        if nid in by_id:
            err(f"duplicate NodeId {nid}")
        by_id[nid] = n

    def resolves(tid):
        return tid in by_id or tid in KNOWN_BASE

    def is_concrete_instance(node):
        cur = node
        seen = set()
        while True:
            p = cur.get("ParentNodeId")
            if not p or cur.get("NodeId") in seen:
                return False
            seen.add(cur.get("NodeId"))
            if p not in by_id:
                return True
            cur = by_id[p]
            if cur.tag[len(NS):] in ("UAObjectType", "UAVariableType", "UADataType",
                                     "UAReferenceType"):
                return False

    for n in nodes:
        cls = n.tag[len(NS):]
        nid = n.get("NodeId")
        bname = n.get("BrowseName", "")
        refs = n.findall(f"{NS}References/{NS}Reference")
        for r in refs:
            tgt = (r.text or "").strip()
            if not resolves(tgt):
                err(f"{nid} ({bname}) references unresolved target {tgt}")
        reftypes = [(r.get("ReferenceType"), (r.text or "").strip(),
                     r.get("IsForward", "true") != "false") for r in refs]

        if cls in ("UAObjectType", "UAVariableType", "UADataType", "UAReferenceType"):
            if not any(rt == "HasSubtype" and not fwd for rt, _, fwd in reftypes):
                err(f"{cls} {nid} ({bname}) missing inverse HasSubtype to a base type")

        if n.get("ParentNodeId"):
            parent = n.get("ParentNodeId")
            if cls in ("UAVariable", "UAObject"):
                if not any(rt == "HasTypeDefinition" for rt, _, _ in reftypes):
                    err(f"{cls} {nid} ({bname}) has ParentNodeId but no HasTypeDefinition")
            simple = bname.split(":")[-1]
            if simple not in NO_RULE_OK and not is_concrete_instance(n):
                if not any(rt == "HasModellingRule" for rt, _, _ in reftypes):
                    err(f"{cls} {nid} ({bname}) has ParentNodeId but no HasModellingRule")
            if not any((rt in ("HasComponent", "HasProperty", "Organizes", "HasInterface", "HasAddIn")
                        and not fwd and tgt == parent) for rt, tgt, fwd in reftypes):
                err(f"{cls} {nid} ({bname}) ParentNodeId {parent} not backed by an inverse "
                    "hierarchical reference")

    for n in nodes:
        nid = n.get("NodeId")
        for r in n.findall(f"{NS}References/{NS}Reference"):
            rt = r.get("ReferenceType")
            tgt = (r.text or "").strip()
            fwd = r.get("IsForward", "true") != "false"
            if rt in ("HasComponent", "HasProperty", "Organizes", "HasAddIn") and fwd and tgt in by_id:
                back = by_id[tgt].findall(f"{NS}References/{NS}Reference")
                if not any(b.get("ReferenceType") == rt
                           and (b.text or "").strip() == nid
                           and b.get("IsForward", "true") == "false" for b in back):
                    err(f"{nid} -> {tgt} ({rt}) has no matching inverse reference on target")

    for n in nodes:
        if n.tag[len(NS):] == "UADataType":
            defn = n.find(f"{NS}Definition")
            if defn is None:
                continue
            fields = defn.findall(f"{NS}Field")
            es_id = None
            for r in n.findall(f"{NS}References/{NS}Reference"):
                if r.get("ReferenceType") == "HasProperty" and r.get("IsForward", "true") != "false":
                    cand = by_id.get((r.text or "").strip())
                    if cand is not None and cand.get("BrowseName", "").endswith("EnumStrings"):
                        es_id = (r.text or "").strip()
            if es_id and fields:
                es = by_id[es_id]
                ad = es.get("ArrayDimensions")
                if ad != str(len(fields)):
                    err(f"{n.get('NodeId')} EnumStrings ArrayDimensions={ad} != field count {len(fields)}")

    print(f"nodes: {len(nodes)}")
    if ERR:
        print(f"ERRORS: {len(ERR)}")
        for e in ERR:
            print(f"  - {e}")
        sys.exit(1)
    print("OK - 0 errors")


if __name__ == "__main__":
    main()
