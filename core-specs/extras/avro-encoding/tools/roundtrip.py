from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc.corpus import CORPUS
from opcua_enc.values import canonical_equal, is_single_float_type

import avro_codec


def main() -> int:
    failures = 0
    for case in CORPUS:
        try:
            data = avro_codec.encode(case.type, case.value)
            out = avro_codec.decode(case.type, data)
            ok = canonical_equal(case.value, out, single_float=is_single_float_type(case.type))
        except Exception as exc:
            ok = False
            out = exc
        if not ok:
            failures += 1
            print(f"FAIL {case.name}: {out!r}")
    print(f"Avro roundtrip: {len(CORPUS) - failures}/{len(CORPUS)} passed, {failures} failures")
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(main())
