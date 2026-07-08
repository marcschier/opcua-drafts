"""Reference checks for the NamespaceUri -> Avro namespace mapping (§6.5).

Run standalone; the process exits non-zero if any assertion fails.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from namespace_map import (  # noqa: E402
    RESERVED_SUFFIX,
    assign_avro_namespaces,
    avro_namespace_from_uri,
)


def main() -> int:
    # Steps 1–5: representative single-URI conversions.
    cases = {
        "http://opcfoundation.org/UA/": "org.opcfoundation.ua.avro",
        "http://opcfoundation.org/UA/DI/": "org.opcfoundation.ua.di.avro",
        "http://example.org/UA/Line3": "org.example.ua.line3.avro",
        # a path segment starting with a digit is prefixed with "_".
        "http://www.example.com/factory/2/cell": "com.example.www.factory._2.cell.avro",
        # non-authority URN: scheme-specific part split on ":" and "/".
        "urn:example:opcua:Line3": "example.opcua.line3.avro",
    }
    for uri, expected in cases.items():
        got = avro_namespace_from_uri(uri)
        assert got == expected, f"{uri}: expected {expected!r}, got {got!r}"
        assert got.split(".")[-1] == RESERVED_SUFFIX, got

    # Conflict rule: two distinct URIs that escape to the same Avro namespace
    # are disambiguated deterministically by the counter rule in ordinal order.
    a, b = "http://example.org/UA/Line-3", "http://example.org/UA/Line.3"
    assert avro_namespace_from_uri(a) == avro_namespace_from_uri(b)
    assigned = assign_avro_namespaces([b, a])  # order-independent input
    assert assigned[a] == "org.example.ua.line_3.avro", assigned
    assert assigned[b] == "org.example.ua.line_3_2.avro", assigned
    assert assigned[a] != assigned[b]
    assert all(ns.endswith("." + RESERVED_SUFFIX) for ns in assigned.values())

    # Cascade: a suffixed candidate that would itself collide with a third URI's
    # natural namespace advances the counter until it is free.
    c = "http://example.org/UA/Line_3_2"  # natural namespace == b's suffix
    cascade = assign_avro_namespaces([c, b, a])
    assert cascade[a] == "org.example.ua.line_3.avro", cascade
    assert cascade[c] == "org.example.ua.line_3_2.avro", cascade
    assert cascade[b] == "org.example.ua.line_3_3.avro", cascade
    assert len(set(cascade.values())) == 3, cascade

    # Non-colliding scope leaves every namespace unsuffixed.
    scope = assign_avro_namespaces(cases.keys())
    assert set(scope.values()) == set(cases.values())

    print(
        f"namespace_map_demo: single={len(cases)} conflict=ok "
        f"({assigned[a]} / {assigned[b]}); ok"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
