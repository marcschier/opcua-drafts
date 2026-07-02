#!/usr/bin/env python3
"""Run every extension's local validation from one place.

Usage (from repo root):  python core-specs/validate_all.py
Exit code is non-zero if any extension fails.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS = [
    "_common/validate_local.py",
    "avro-encoding/tools/validate_local.py",
    "protobuf-encoding/tools/validate_local.py",
    "arrow-encoding/tools/validate_local.py",
    "xregistry-catalog/tools/validate_local.py",
]


def main() -> int:
    failed = []
    for rel in TARGETS:
        path = os.path.join(HERE, *rel.split("/"))
        print(f"=== {rel} ===")
        rc = subprocess.run([sys.executable, path], cwd=os.path.dirname(HERE)).returncode
        if rc != 0:
            failed.append(rel)
            print(f"  !! FAILED (exit {rc})")
    print()
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    print("ALL EXTENSIONS VALIDATED OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
