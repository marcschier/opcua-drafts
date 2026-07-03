from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc.corpus import CORPUS
from opcua_enc.values import canonical_equal, is_single_float_type

import arrow_codec


def run() -> tuple[int, int]:
    failures = 0
    for case in CORPUS:
        decoded = arrow_codec.decode(case.type, arrow_codec.encode(case.type, case.value))
        if not canonical_equal(case.value, decoded, single_float=is_single_float_type(case.type)):
            failures += 1
            print(f"FAIL {case.name}: {case.value!r} != {decoded!r}")
    total = len(CORPUS)
    print(f"Arrow roundtrip: {total - failures}/{total} passed, {failures} failures")
    return total, failures


if __name__ == "__main__":
    _, failed = run()
    raise SystemExit(1 if failed else 0)
