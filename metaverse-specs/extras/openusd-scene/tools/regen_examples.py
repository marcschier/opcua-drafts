#!/usr/bin/env python3
"""Regenerate the OpenUSD Scene example NodeSets from the openusd-binding example USDA assets.

Single reproducible entry point (mirrors the repo's "generated from a single source of truth"
convention): re-running produces byte-identical output. Run from anywhere:

    python metaverse-specs/extras/openusd-scene/tools/regen_examples.py
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MV = os.path.normpath(os.path.join(HERE, "..", "..", ".."))  # metaverse-specs/
EX = os.path.join(MV, "extras", "openusd-binding", "examples")
OUT = os.path.join(MV, "openusd-scene")

CASES = [
    ("pumps",
     os.path.join(EX, "pumps", "Plant.usda"),
     os.path.join(OUT, "pumps", "Opc.Ua.Pumps.OpenUsdScene.NodeSet2.xml"),
     "http://example.com/UA/OpenUSD/Scene/Pumps/", "Plant"),
    ("robotics",
     os.path.join(EX, "robotics", "Cell.usda"),
     os.path.join(OUT, "robotics", "Opc.Ua.Robotics.OpenUsdScene.NodeSet2.xml"),
     "http://example.com/UA/OpenUSD/Scene/Robotics/", "Cell"),
]


def main() -> int:
    gen = os.path.join(HERE, "usd_to_nodeset.py")
    for name, inp, out, ns, stage in CASES:
        rc = subprocess.run(
            [sys.executable, gen, "--input", inp, "--output", out,
             "--namespace", ns, "--stage-name", stage]).returncode
        if rc != 0:
            print(f"  !! {name} FAILED (exit {rc})")
            return rc
        print(f"regenerated {name}: {os.path.relpath(out, MV)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
