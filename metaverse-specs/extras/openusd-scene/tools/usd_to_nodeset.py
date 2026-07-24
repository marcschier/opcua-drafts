#!/usr/bin/env python3
from __future__ import annotations
import argparse, os, sys
from scene_common import parse_usda, emit_nodeset

def main() -> int:
    ap = argparse.ArgumentParser(description="Materialize a composed USDA scene as an OPC UA OpenUSD Scene NodeSet.")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--namespace", required=True)
    ap.add_argument("--stage-name", required=True)
    args = ap.parse_args()
    stage = parse_usda(args.input, args.stage_name)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8", newline="\n") as f:
        f.write(emit_nodeset(stage, args.namespace))
    live = [p.path + "." + a.name for p in stage.all_prims() for a in p.attributes if a.live]
    print(f"Wrote {args.output} ({len(stage.all_prims())} prims, {len(live)} live attributes)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
