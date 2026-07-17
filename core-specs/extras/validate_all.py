#!/usr/bin/env python3
"""Run every extension's local validation from one place.

Usage (from repo root):
    python core-specs/extras/validate_all.py                  # all extensions (needs local ref data)
    python core-specs/extras/validate_all.py --self-contained # only checks that need no gitignored
                                                              # ref data (used by CI)

Exit code is non-zero if any run extension fails.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Validators that run on a clean checkout: they need no untracked base data — neither the gitignored
# **/tools/ref/ tables nor a base NodeSet. `_common` exercises the shared corpus/codec foundation;
# `xregistry-catalog` validates its committed catalog artifacts without rebuilding.
SELF_CONTAINED = [
    "_common/validate_local.py",
    "xregistry-catalog/tools/validate_local.py",
]

# Validators that additionally need untracked base data — a base NodeSet (e.g.
# core-specs/pubsub-binding/Opc.Ua.PubSubBinding.NodeSet2.xml, which the encoding generators map) or
# the gitignored **/tools/ref/ tables — so they only run where that data is present (locally, not on
# a clean CI checkout).
NEEDS_BASE_DATA = [
    "avro-encoding/tools/validate_local.py",
    "arrow-encoding/tools/validate_local.py",
    "../schema-registry/tools/validate_local.py",
    "observability-export/tools/validate_local.py",
    "observability-export/examples/tools/validate_examples.py",
    "openusd-binding/tools/validate_local.py",
]


def run(targets):
    failed = []
    for rel in targets:
        path = os.path.join(HERE, *rel.split("/"))
        print(f"=== {rel} ===")
        rc = subprocess.run([sys.executable, path], cwd=os.path.dirname(HERE)).returncode
        if rc != 0:
            failed.append(rel)
            print(f"  !! FAILED (exit {rc})")
    return failed


def main() -> int:
    self_contained_only = "--self-contained" in sys.argv[1:]
    targets = SELF_CONTAINED if self_contained_only else SELF_CONTAINED + NEEDS_BASE_DATA
    failed = run(targets)
    print()
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    if self_contained_only:
        print("ALL SELF-CONTAINED EXTENSIONS VALIDATED OK")
    else:
        print("ALL EXTENSIONS VALIDATED OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
