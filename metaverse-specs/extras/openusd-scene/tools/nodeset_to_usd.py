#!/usr/bin/env python3
from __future__ import annotations
import argparse, os
from scene_common import read_nodeset, write_usda

def main() -> int:
    ap = argparse.ArgumentParser(description="Export an OpenUSD Scene example NodeSet as a flattened USDA layer.")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    stage = read_nodeset(args.input)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    write_usda(stage, args.output)
    print(f"Wrote {args.output} ({len(stage.all_prims())} prims)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
