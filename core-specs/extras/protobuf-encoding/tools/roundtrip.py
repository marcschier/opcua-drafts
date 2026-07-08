from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, os.path.abspath(HERE / ".." / ".." / "_common"))
from opcua_enc.corpus import CORPUS  # noqa: E402
from opcua_enc.values import canonical_equal, is_single_float_type  # noqa: E402
from protobuf_codec import decode, encode  # noqa: E402


def main() -> int:
    failures = 0
    for case in CORPUS:
        data = encode(case.type, case.value)
        got = decode(case.type, data)
        if not canonical_equal(case.value, got, single_float=is_single_float_type(case.type)):
            failures += 1
            print(f"FAIL {case.name}: {case.value!r} != {got!r}")
    print(f"roundtrip: {len(CORPUS) - failures}/{len(CORPUS)} passed, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
