#!/usr/bin/env python3
"""Run every metaverse-specs (OPC UA <-> OpenUSD) extension's local validation from one place.

Usage (from repo root):
    python metaverse-specs/validate_all.py                  # all metaverse-specs extensions
    python metaverse-specs/validate_all.py --self-contained # only checks that need no untracked ref data (CI)

The OpenUSD validators are stdlib-only structural checks against the committed NodeSets, so they run on
a clean checkout. Exit code is non-zero if any run extension fails.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Structural validators that run on a clean checkout (stdlib only, validate committed NodeSets).
SELF_CONTAINED = [
    "extras/openusd-binding/tools/validate_local.py",
    "extras/openusd-scene/tools/validate_local.py",
    # openusd-scene added in the Scene Materialization (Part 2) work.
]

# Validators that additionally need untracked base data (none yet).
NEEDS_BASE_DATA: list[str] = []


def run(targets):
    failed = []
    for rel in targets:
        path = os.path.join(HERE, *rel.split("/"))
        print(f"=== metaverse-specs/{rel} ===")
        rc = subprocess.run([sys.executable, path], cwd=HERE).returncode
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
    suffix = " (self-contained)" if self_contained_only else ""
    print("ALL METAVERSE EXTENSIONS VALIDATED OK" + suffix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
