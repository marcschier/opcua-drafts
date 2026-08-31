#!/usr/bin/env python3
"""Run every cloud-specs extension's local validation from one place.

Usage (from repo root):
    python cloud-specs/validate_all.py                  # all cloud-specs extensions
    python cloud-specs/validate_all.py --self-contained # only checks that need no untracked ref data (CI)

`cloud-specs/` holds the specifications that describe an OPC UA Server's cloud-facing
surface: the schema registry a decoder resolves a fingerprint against, and the
observability export that projects a model into a telemetry pipeline. They were part of
`core-specs/` until they outgrew it; the aggregate moved with them, because a tree whose
validators are driven from another tree stops being validated the moment someone tidies
that other tree's list.

Exit code is non-zero if any run extension fails.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Validators that run on a clean checkout. Each one skips its optional cross-check against
# the gitignored **/tools/ref/ base tables when those are absent, and validates the
# committed NodeSet and CSV either way — the same arrangement the data-channels validators
# use in core-specs/extras/validate_all.py.
SELF_CONTAINED = [
    "../source/cloud-specs/schema-registry/tools/validate_local.py",
]

# Validators that additionally need untracked base data (none yet).
NEEDS_BASE_DATA: list[str] = []


def run(targets):
    failed = []
    for rel in targets:
        path = os.path.join(HERE, *rel.split("/"))
        print(f"=== cloud-specs/{rel} ===")
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
    print("ALL CLOUD EXTENSIONS VALIDATED OK" + suffix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
