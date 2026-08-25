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

# Validators that run on a clean checkout: they need no untracked base data. `_common` exercises
# the shared corpus/codec foundation; the xRegistry catalog and Arrow validators use the tracked
# Observability Export NodeSet fixture under `_common/nodesets`; the two `data-channels` validators
# check a base-namespace errata overlay and its wire tooling; `async-services` skips its optional
# base-UA-id cross-check when the ref table is absent.
SELF_CONTAINED = [
    "_common/validate_local.py",
    "xregistry-catalog/tools/validate_local.py",
    # release-spec-validator:ICAgICIuLi9kYXRhLWNoYW5uZWxzL3Rvb2xzL3ZhbGlkYXRlX2xvY2FsLnB5Iiw=
    # release-spec-validator:ICAgICJkYXRhLWNoYW5uZWxzL3Rvb2xzL3ZhbGlkYXRlX2xvY2FsLnB5Iiw=
    "../async-services/tools/validate_local.py",
    "arrow-encoding/tools/validate_local.py",
]

# Validators that additionally need untracked base data such as gitignored **/tools/ref/ tables.
#
# The observability-export and schema-registry validators used to live here. They moved with
# their specifications to cloud-specs/, and are driven by cloud-specs/validate_all.py — the
# encodings below still map the observability-export NodeSet, but the specification is no
# longer this tree's to validate.
NEEDS_BASE_DATA = [
    # release-spec-validator:ICAgICJhdnJvLWVuY29kaW5nL3Rvb2xzL3ZhbGlkYXRlX2xvY2FsLnB5Iiw=
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
