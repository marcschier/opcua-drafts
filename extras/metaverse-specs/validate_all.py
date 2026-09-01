#!/usr/bin/env python3
"""Run every metaverse-specs (OPC UA <-> OpenUSD) extension's local validation from one place.

Usage (from repo root):
    python extras/metaverse-specs/validate_all.py                  # all metaverse-specs extensions
    python extras/metaverse-specs/validate_all.py --self-contained # only checks that need no untracked ref data (CI)

The OpenUSD validators are stdlib-only structural checks against the committed NodeSets, so they run on
a clean checkout. Exit code is non-zero if any run extension fails.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

# Structural validators that run on a clean checkout (stdlib only, validate committed NodeSets).
SELF_CONTAINED = [
    # release-spec-validator:ICAgICJvcGVudXNkLWJpbmRpbmcvdG9vbHMvdmFsaWRhdGVfbG9jYWwucHkiLA==
    # release-spec-validator:ICAgICJvcGVudXNkLXNjZW5lL3Rvb2xzL3ZhbGlkYXRlX2xvY2FsLnB5Iiw=
    # release-spec-validator:ICAgICJvcGVudXNkLXNjZW5lL3Rvb2xzL3ZhbGlkYXRlX2V4YW1wbGVzLnB5Iiw=
    # release-spec-validator:ICAgICJvcGVudXNkLWFydGlmYWN0cy90b29scy92YWxpZGF0ZV9sb2NhbC5weSIs
    "vision/tools/validate_local.py",
    "robot-intent/tools/validate_local.py",
    "ai-model-management/tools/validate_local.py",
    "ai-model-management/examples/tools/validate_examples.py",
    # openusd-scene added in the Scene Materialization (Part 2) work.
    # openusd-artifacts moves with the private OpenUSD review material.
    # vision added in the OPC UA - Vision work.
    # robot-intent added in the OPC UA - Robot Intent work; it also cross-checks the
    # specification against the model in both directions.
    # ai-model-management is a separate specification, so vision's validator also reads
    # that NodeSet to resolve the overlay references that cross between them.
    # validate_examples keeps the vendor implementation guides beside that specification
    # from citing members the model no longer declares.
]

# Validators that additionally need untracked base data (none yet).
NEEDS_BASE_DATA: list[str] = []


def run(targets):
    failed = []
    for rel in targets:
        path = os.path.join(HERE, *rel.split("/"))
        print(f"=== extras/metaverse-specs/{rel} ===")
        rc = subprocess.run([sys.executable, path], cwd=REPO).returncode
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
