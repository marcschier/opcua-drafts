#!/usr/bin/env python3
from __future__ import annotations
import os, sys, xml.etree.ElementTree as ET

NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SCENE = os.path.join(ROOT, "openusd-scene", "Opc.Ua.OpenUsdScene.NodeSet2.xml")
CASES = [
    os.path.join(ROOT, "openusd-scene", "pumps", "Opc.Ua.Pumps.OpenUsdScene.NodeSet2.xml"),
    os.path.join(ROOT, "openusd-scene", "robotics", "Opc.Ua.Robotics.OpenUsdScene.NodeSet2.xml"),
]
BASE = {"i=1","i=2","i=6","i=7","i=8","i=10","i=11","i=12","i=15","i=17","i=20","i=21","i=22","i=24","i=29","i=32","i=35","i=37","i=40","i=44","i=45","i=46","i=47","i=58","i=61","i=62","i=63","i=68","i=78","i=80","i=85","i=290","i=11508","i=17602","i=17603","i=17604"}

def node_ids(path):
    r = ET.parse(path).getroot()
    return {e.get("NodeId") for e in r if e.tag.startswith(NS) and e.tag[len(NS):].startswith("UA")}

def validate(path, scene_ids):
    err = []
    root = ET.parse(path).getroot()
    models = root.findall(f"{NS}Models/{NS}Model")
    if len(models) != 1:
        err.append("expected exactly one Model")
    else:
        req = {r.get("ModelUri") for r in models[0].findall(f"{NS}RequiredModel")}
        if "http://opcfoundation.org/UA/" not in req or "http://opcfoundation.org/UA/OpenUSD/Scene/" not in req:
            err.append("missing base UA or Scene RequiredModel")
    nodes = [e for e in root if e.tag.startswith(NS) and e.tag[len(NS):].startswith("UA")]
    own = {}
    for n in nodes:
        if n.get("NodeId") in own:
            err.append(f"duplicate NodeId {n.get('NodeId')}")
        own[n.get("NodeId")] = n
    def resolves(x): return x in own or x in BASE or x in scene_ids
    for n in nodes:
        nid = n.get("NodeId"); cls = n.tag[len(NS):]; refs = n.findall(f"{NS}References/{NS}Reference")
        for r in refs:
            tgt = (r.text or "").strip()
            if not resolves(tgt):
                err.append(f"{nid} unresolved reference target {tgt}")
        ad = n.get("ArrayDimensions"); vr = n.get("ValueRank")
        if ad is not None and vr is not None:
            try: rank = int(vr)
            except ValueError: rank = None
            if rank is not None and rank >= 0 and len(ad.split(",")) != rank:
                err.append(f"{nid} ValueRank={rank} but ArrayDimensions '{ad}' has {len(ad.split(','))} entries")
        if n.get("ParentNodeId") and cls in ("UAObject","UAVariable"):
            if not any(r.get("ReferenceType") in ("HasTypeDefinition", "i=40") for r in refs):
                err.append(f"{nid} has ParentNodeId but no HasTypeDefinition")
            p = n.get("ParentNodeId")
            if not any(r.get("IsForward","true") == "false" and (r.text or "").strip() == p and r.get("ReferenceType") in ("HasComponent","HasProperty","Organizes","HasAddIn","i=47","i=46","i=35","i=17604") for r in refs):
                err.append(f"{nid} ParentNodeId {p} not backed by inverse hierarchical reference")
    return len(nodes), err

def main() -> int:
    scene_ids = node_ids(SCENE)
    total = 0; errors = []
    for c in CASES:
        count, err = validate(c, scene_ids)
        total += count
        print(f"{os.path.basename(os.path.dirname(c))}: nodes: {count}")
        errors += [f"{c}: {e}" for e in err]
    if errors:
        print(f"ERRORS: {len(errors)}")
        for e in errors: print("  -", e)
        return 1
    print(f"OK - 0 errors ({total} example nodes)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
