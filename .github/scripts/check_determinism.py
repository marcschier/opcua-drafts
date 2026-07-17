#!/usr/bin/env python3
"""Determinism / "generated files are up to date" check.

Regenerates the deterministic encoding artifacts and fails if that produces any change under
version control — i.e. a generated file was hand-edited or a source change was not regenerated.

The encoding generators map a base NodeSet (`core-specs/pubsub-binding/Opc.Ua.PubSubBinding.NodeSet2.xml`)
that is not distributed with the repository. When that base data is absent (for example on a clean
CI checkout) this check **skips** cleanly rather than fail; run it locally where the base NodeSet is
present for a full determinism gate.

Usage (from repo root):  python .github/scripts/check_determinism.py
Exit code: 0 = clean or skipped, 1 = generated files drifted, 2 = a generator errored.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_NODESET = os.path.join(ROOT, "core-specs", "pubsub-binding", "Opc.Ua.PubSubBinding.NodeSet2.xml")

GENERATORS = [
    "core-specs/extras/avro-encoding/tools/build_schemas.py",
    "core-specs/extras/arrow-encoding/tools/build_schemas.py",
    "core-specs/extras/xregistry-catalog/tools/build_catalog.py",
]


def main():
    if not os.path.exists(BASE_NODESET):
        print("check_determinism: SKIP - base NodeSet not present "
              "(core-specs/pubsub-binding/Opc.Ua.PubSubBinding.NodeSet2.xml); "
              "run locally with the base data for a full determinism gate")
        return 0
    for rel in GENERATORS:
        print(f"=== regenerate {rel} ===")
        proc = subprocess.run([sys.executable, os.path.join(ROOT, *rel.split("/"))], cwd=ROOT)
        if proc.returncode != 0:
            print(f"check_determinism: ERROR - generator failed: {rel}")
            return 2
    diff = subprocess.run(["git", "diff", "--stat", "--exit-code"], cwd=ROOT)
    if diff.returncode != 0:
        print("check_determinism: generated files drifted - regenerate and commit "
              "(do not hand-edit generated artifacts)")
        return 1
    print("check_determinism: OK (regeneration produced no changes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
