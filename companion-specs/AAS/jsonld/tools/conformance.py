#!/usr/bin/env python3
"""
Conformance runner for the AAS JSON-LD lifting.

Three claims are checked independently, because collapsing them would let
fidelity to a lossy target stand in for fidelity to the source:

  AASLD-RdfCompatible  the lifted graph equals the normative RDF for the pinned
                       upstream release, modulo the declared deviations D1 and
                       D3 of UPSTREAM-DEFECTS.md
  AASLD-JsonRoundTrip  not yet exercised here; it needs lower.py
  AASLD-Linked         the enrichment graph carries the ordering that the
                       normative serialization discards (D2)

Comparison is on RDF graph isomorphism, so blank node labelling does not matter,
which is the only sound way to compare two serializations of the same graph.

The upstream corpus is used when it has been fetched; otherwise the vendored
fixtures are used, so the runner works offline.

Usage:
    python conformance.py             # fixtures, or the full corpus if cached
    python conformance.py --corpus    # require the full corpus
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from rdflib import Graph
from rdflib.compare import isomorphic, to_isomorphic, graph_diff

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURES = os.path.join(ROOT, "fixtures")
CORPUS = os.path.join(ROOT, ".corpus")

sys.path.insert(0, HERE)
from lift import AAS, Lifter, Ontology, serialize  # noqa: E402

IDSHORT = AAS + "Referable/idShort"

# The upstream Turtle carries no base (D3), so a parser resolves its relative
# subject terms against whatever it is given. Giving it the same base the
# lifting uses removes that difference from the comparison, leaving only
# differences the lifting is responsible for.
BASE = "https://example.org/aas/"


def load_expected(path):
    g = Graph()
    g.parse(path, format="turtle", publicID=BASE)
    return g


def load_actual(json_path, profile="core", emit_root_idshort=True):
    with open(json_path, encoding="utf-8") as f:
        doc = json.load(f)
    lifter = Lifter(ONTOLOGY, BASE, profile, emit_root_idshort=emit_root_idshort)
    sink = lifter.lift(doc)
    g = Graph()
    g.parse(data=serialize(sink, with_graphs=False), format="nt")
    order = Graph()
    if sink.quads:
        order.parse(data="\n".join(f"{s} {p} {o} ." for s, p, o, _ in sink.quads), format="nt")
    return g, order


def cases_from_fixtures():
    index = os.path.join(FIXTURES, "index.json")
    with open(index, encoding="utf-8") as f:
        meta = json.load(f)
    for entry in meta["cases"]:
        base = os.path.join(FIXTURES, entry["file"])
        yield entry["case"], base + ".json", base + ".ttl"


def cases_from_corpus():
    manifest = os.path.join(CORPUS, "manifest.json")
    if not os.path.exists(manifest):
        return
    with open(manifest, encoding="utf-8") as f:
        meta = json.load(f)
    for case in sorted(meta["cases"]):
        j = os.path.join(CORPUS, "json", *case.split("/")) + ".json"
        t = os.path.join(CORPUS, "ttl", *case.split("/")) + ".ttl"
        if os.path.exists(j) and os.path.exists(t):
            yield case, j, t


def describe(expected, actual, limit=4):
    _, in_expected, in_actual = graph_diff(to_isomorphic(expected), to_isomorphic(actual))
    out = []
    for label, g in (("expected only", in_expected), ("lifted only", in_actual)):
        rows = sorted(f"{s} {p} {o}" for s, p, o in g)[:limit]
        if rows:
            out.append(f"      {label}:")
            out += [f"        {r[:150]}" for r in rows]
    return "\n".join(out)


def main():
    global ONTOLOGY
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", action="store_true", help="require the full upstream corpus")
    ap.add_argument("--show", type=int, default=6, help="how many failures to describe")
    args = ap.parse_args()

    ONTOLOGY = Ontology()

    cases = list(cases_from_corpus()) if (args.corpus or os.path.exists(os.path.join(CORPUS, "manifest.json"))) else []
    source = "upstream corpus"
    if not cases:
        if args.corpus:
            print("no cached corpus; run tools/fetch_corpus.py first", file=sys.stderr)
            return 1
        cases = list(cases_from_fixtures())
        source = "vendored fixtures"

    passed, d1, failed, errored, ordered = 0, 0, [], [], 0
    for case, jpath, tpath in cases:
        try:
            expected = load_expected(tpath)
            actual, order = load_actual(jpath, profile="linked")
        except Exception as exc:  # noqa: BLE001 - report, do not abort the run
            errored.append((case, f"{type(exc).__name__}: {exc}"))
            continue
        if order:
            ordered += 1
        if isomorphic(expected, actual):
            passed += 1
            continue
        # D1 of the register: for most cases the upstream JSON example carries a
        # root idShort that the upstream Turtle example does not. Retry without
        # it; if that agrees, the only difference is the known corpus deviation.
        try:
            without, _ = load_actual(jpath, profile="linked", emit_root_idshort=False)
        except Exception:  # noqa: BLE001
            without = None
        if without is not None and isomorphic(expected, without):
            d1 += 1
            continue
        failed.append((case, expected, actual))

    total = len(cases)
    print(f"source: {source}")
    print(f"cases: {total}")
    print("\nAASLD-RdfCompatible (base supplied per D3)")
    print(f"  isomorphic outright                     : {passed}")
    print(f"  isomorphic once the root idShort is set  : {d1}   <- corpus deviation D1")
    print(f"  differing                                : {len(failed)}")
    print(f"  errored                                  : {len(errored)}")
    print("\nAASLD-Linked")
    print(f"  cases carrying an ordering graph: {ordered}")

    for case, why in errored[: args.show]:
        print(f"\n  ERROR {case}\n      {why[:200]}")
    for case, expected, actual in failed[: args.show]:
        print(f"\n  DIFFERS {case}")
        print(describe(expected, actual))

    return 0 if not failed and not errored else 1


if __name__ == "__main__":
    sys.exit(main())
