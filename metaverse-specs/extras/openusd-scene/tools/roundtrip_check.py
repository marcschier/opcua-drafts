#!/usr/bin/env python3
from __future__ import annotations
import os, sys
from scene_common import parse_usda, read_nodeset, write_usda, scene_signature

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
CASES = [
    ("pumps", os.path.join(ROOT, "extras", "openusd-binding", "examples", "pumps", "Plant.usda"),
     os.path.join(ROOT, "openusd-scene", "pumps", "Opc.Ua.Pumps.OpenUsdScene.NodeSet2.xml")),
    ("robotics", os.path.join(ROOT, "extras", "openusd-binding", "examples", "robotics", "Cell.usda"),
     os.path.join(ROOT, "openusd-scene", "robotics", "Opc.Ua.Robotics.OpenUsdScene.NodeSet2.xml")),
]

def main() -> int:
    failed = []
    for name, usd, nodeset in CASES:
        expected = parse_usda(usd, name.capitalize())
        actual = read_nodeset(nodeset)
        scratch = os.path.join(HERE, f".roundtrip_{name}.usda")
        try:
            write_usda(actual, scratch)
            reparsed = parse_usda(scratch, actual.stage_name, apply_example_overlays=False)
            if scene_signature(expected) != scene_signature(reparsed):
                failed.append(name)
                print(f"{name}: DIFF")
            else:
                live = [p.path + "." + a.name for p in actual.all_prims() for a in p.attributes if a.live]
                print(f"{name}: OK ({len(actual.all_prims())} prims, {len(live)} live attributes)")
        finally:
            if os.path.exists(scratch):
                os.remove(scratch)
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    print("ROUNDTRIP OK - 0 diffs")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
