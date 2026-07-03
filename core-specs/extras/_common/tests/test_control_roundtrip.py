"""Foundation tests: the corpus round-trips through the JSON control codec, and
canonical_equal enforces the OPC UA null/empty/NaN distinctions.

Run: python -m pytest core-specs/_common/tests   (from repo root)
or:  python core-specs/_common/tests/test_control_roundtrip.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from opcua_enc import json_control as jc  # noqa: E402
from opcua_enc import types as t  # noqa: E402
from opcua_enc import values as v  # noqa: E402
from opcua_enc.corpus import CORPUS  # noqa: E402


def test_corpus_roundtrips_through_control():
    failures = []
    for case in CORPUS:
        data = jc.to_bytes(case.type, case.value)
        back = jc.from_bytes(case.type, data)
        if not v.canonical_equal(back, case.value):
            failures.append((case.name, case.value, back))
    assert not failures, "round-trip mismatches:\n" + "\n".join(
        f"  {n}: {orig!r} != {got!r}" for n, orig, got in failures
    )


def test_corpus_is_nonempty_and_named_uniquely():
    assert len(CORPUS) >= 60
    names = [c.name for c in CORPUS]
    assert len(names) == len(set(names)), "duplicate corpus case names"


def test_canonical_equal_distinctions():
    # null vs empty vs whitespace
    assert not v.canonical_equal(None, "")
    assert not v.canonical_equal(None, [])
    assert not v.canonical_equal("", " ")
    # NaN is equal to itself; +0.0 and -0.0 differ
    assert v.canonical_equal(float("nan"), float("nan"))
    assert not v.canonical_equal(0.0, -0.0)
    assert v.canonical_equal(-0.0, -0.0)
    # int vs bool must not conflate
    assert not v.canonical_equal(1, True)
    # Variant type identity matters
    assert not v.canonical_equal(v.Variant(t.INT32, 1), v.Variant(t.INT16, 1))


if __name__ == "__main__":
    test_corpus_roundtrips_through_control()
    test_corpus_is_nonempty_and_named_uniquely()
    test_canonical_equal_distinctions()
    print(f"OK: {len(CORPUS)} corpus cases round-tripped through the JSON control codec.")
