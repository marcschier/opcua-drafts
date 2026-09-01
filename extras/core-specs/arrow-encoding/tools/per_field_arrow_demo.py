"""Reference check: Arrow's structural typing makes each field's Variant union
independent (per-field by construction), matching Avro's per-field model.

Two Variant-like dense unions narrowed differently coexist in one schema; growing
one field's union leaves the other field's type byte-identical. Run standalone;
exits non-zero if any assertion fails.
"""
from __future__ import annotations

import sys

import pyarrow as pa


def _variant_union(branches: list[tuple[str, pa.DataType]]) -> pa.DataType:
    fields = [pa.field("null", pa.null())]
    fields += [pa.field(f"scalar_{name}", pa.struct([pa.field("value", ty)])) for name, ty in branches]
    return pa.union(fields, mode="dense")


def main() -> int:
    signal = _variant_union([("Int32", pa.int32()), ("Double", pa.float64())])
    detail = _variant_union([("Boolean", pa.bool_()), ("Float", pa.float32())])
    schema = pa.schema([pa.field("signal", signal), pa.field("event_detail", detail)])

    # Independence: two Variant fields carry distinct, disjointly-narrowed unions.
    assert signal != detail, "expected independent per-field unions"
    assert schema.serialize().size > 0

    # Growing `signal` (append a branch) leaves `event_detail` byte-identical —
    # there is no shared named type to couple them.
    signal_grown = _variant_union([("Int32", pa.int32()), ("Double", pa.float64()), ("String", pa.utf8())])
    grown = pa.schema([pa.field("signal", signal_grown), pa.field("event_detail", detail)])
    assert grown.field("event_detail").type == detail, "detail changed when signal grew"
    assert grown.field("signal").type != schema.field("signal").type

    print("per_field_arrow_demo: independence=ok grow-isolated=ok; ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
