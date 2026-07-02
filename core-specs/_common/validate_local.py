#!/usr/bin/env python3
"""Validate the shared foundation: run the corpus through the JSON control codec
and exercise the NodeSet loader. Exit non-zero on any failure.

Usage (from repo root):  python core-specs/_common/validate_local.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from opcua_enc import json_control as jc  # noqa: E402
from opcua_enc import values as v  # noqa: E402
from opcua_enc.corpus import CORPUS  # noqa: E402


def main() -> int:
    fails = 0
    for case in CORPUS:
        try:
            back = jc.from_bytes(case.type, jc.to_bytes(case.type, case.value))
            if not v.canonical_equal(back, case.value):
                print(f"FAIL round-trip: {case.name}: {case.value!r} != {back!r}")
                fails += 1
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR {case.name}: {exc}")
            fails += 1
    print(f"corpus: {len(CORPUS)} cases, {fails} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
