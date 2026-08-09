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
import random
import sys

from rdflib import Graph
from rdflib.compare import isomorphic, to_isomorphic, graph_diff

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIXTURES = os.path.join(ROOT, "fixtures")
CORPUS = os.path.join(ROOT, ".corpus")

sys.path.insert(0, HERE)
from lift import AAS, Lifter, Ontology, Schema, serialize  # noqa: E402
from lower import Lowerer, parse_nt  # noqa: E402

IDSHORT = AAS + "Referable/idShort"

# The upstream Turtle carries no base (D3), so a parser resolves its relative
# subject terms against whatever it is given. Giving it the same base the
# lifting uses removes that difference from the comparison, leaving only
# differences the lifting is responsible for.
BASE = "https://example.org/aas/"

# Permutations tried for the core-graph round trip. One shuffle measures one
# permutation, and the published figure moved by six percentage points across
# seeds, so a single seed reports an accident rather than a property.
SEEDS = (20260809, 1, 2, 3, 5, 8, 13, 21, 12345, 99991)


def load_expected(path):
    g = Graph()
    g.parse(path, format="turtle", publicID=BASE)
    return g


def load_actual(json_path, profile="core", emit_root_idshort=True):
    with open(json_path, encoding="utf-8") as f:
        doc = json.load(f)
    lifter = Lifter(ONTOLOGY, BASE, profile, emit_root_idshort=emit_root_idshort, schema=SCHEMA)
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


def canonical(doc):
    """AAS JSON compared as data, not as bytes.

    Root collections are order-free - the metamodel gives no meaning to the
    order of `submodels` within an Environment - so they are sorted by `id`
    before comparison. Every other array keeps its order, because the round trip
    is exactly the claim that order survives.
    """
    if isinstance(doc, dict):
        return {k: canonical(v) for k, v in sorted(doc.items())}
    if isinstance(doc, list):
        return [canonical(v) for v in doc]
    return doc


def round_trip(jpath, with_order, seed=20260809):
    """Lift then lower, and report whether the source document came back.

    The triples are shuffled before lowering. RDF is a set, so a consumer gets no
    order guarantee, and a lowering that recovered an array's order from the
    order the triples happened to arrive in would be measuring the serializer
    rather than the graph. One shuffle measures one permutation, so the caller
    varies the seed; see `order_sensitive` for the structural figure, which does
    not depend on sampling at all.
    """
    with open(jpath, encoding="utf-8") as f:
        source = json.load(f)
    lifter = Lifter(ONTOLOGY, BASE, "linked" if with_order else "core", schema=SCHEMA)
    sink = lifter.lift(source)
    core = parse_nt(serialize(sink, with_graphs=False))
    random.Random(seed).shuffle(core)
    order = parse_nt("\n".join(f"{s} {p} {o} ." for s, p, o, _ in sink.quads)) if with_order else ()
    low = Lowerer(ONTOLOGY, SCHEMA)
    low.load(core, order)
    result = low.lower()
    for collection in ("assetAdministrationShells", "submodels", "conceptDescriptions"):
        if collection in source:
            source[collection] = sorted(source[collection], key=lambda n: n.get("id", ""))
    return canonical(source) == canonical(result), source, result


def order_sensitive(jpath):
    """Whether the core graph can guarantee this document's arrays at all.

    A document carries an array of two or more members, or it does not. Where it
    does, the core graph does not represent that array's order and no lowering can
    guarantee it: a particular permutation may happen to come back right, which is
    why a shuffle-based figure varies with the seed and understates the
    population. This is the structural answer and does not sample.
    """
    with open(jpath, encoding="utf-8") as f:
        source = json.load(f)

    def walk(node):
        if isinstance(node, dict):
            return any(walk(v) for v in node.values())
        if isinstance(node, list):
            return len(node) > 1 or any(walk(v) for v in node)
        return False

    return walk(source)


def main():
    global ONTOLOGY, SCHEMA
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", action="store_true", help="require the full upstream corpus")
    ap.add_argument("--show", type=int, default=6, help="how many failures to describe")
    args = ap.parse_args()

    ONTOLOGY = Ontology()
    SCHEMA = Schema()

    cases = list(cases_from_corpus()) if (args.corpus or os.path.exists(os.path.join(CORPUS, "manifest.json"))) else []
    source = "upstream corpus"
    if not cases:
        if args.corpus:
            print("no cached corpus; run tools/fetch_corpus.py first", file=sys.stderr)
            return 1
        cases = list(cases_from_fixtures())
        source = "vendored fixtures"

    passed, d1, failed, errored, ordered = 0, 0, [], [], 0
    rt_with, rt_without, rt_err, rt_structural = 0, 0, 0, 0
    order_only = []
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
        else:
            # D1 of the register: for most cases the upstream JSON example carries a
            # root idShort that the upstream Turtle example does not. Retry without
            # it; if that agrees, the only difference is the known corpus deviation.
            try:
                without, _ = load_actual(jpath, profile="linked", emit_root_idshort=False)
            except Exception:  # noqa: BLE001
                without = None
            if without is not None and isomorphic(expected, without):
                d1 += 1
            else:
                failed.append((case, expected, actual))

        # The round trip. With the ordering graph it must always succeed. Without
        # it, whether a document survives depends on which permutation the
        # consumer happens to see, so several are tried and the structural figure
        # is reported beside them.
        try:
            ok_with, _, _ = round_trip(jpath, with_order=True)
            core_ok = all(round_trip(jpath, with_order=False, seed=s)[0] for s in SEEDS)
            structural = order_sensitive(jpath)
        except Exception:  # noqa: BLE001
            rt_err += 1
            continue
        rt_with += ok_with
        rt_without += core_ok
        if structural:
            rt_structural += 1
        if ok_with and not core_ok:
            order_only.append(case)

    total = len(cases)
    print(f"source: {source}")
    print(f"cases: {total}")
    print("\nAASLD-RdfCompatible (base supplied per D3)")
    print(f"  isomorphic to the core graph of clause 2 : {passed}")
    print(f"  isomorphic once the root idShort is set  : {d1}   <- corpus deviation D1")
    print(f"  differing                                : {len(failed)}")
    print(f"  errored                                  : {len(errored)}")
    print("\nAASLD-JsonRoundTrip")
    print(f"  restored with the ordering graph         : {rt_with}")
    print(f"  restored from the core graph alone,")
    print(f"    under every one of {len(SEEDS)} permutations       : {rt_without}")
    print(f"  failed under at least one permutation    : {len(order_only)}")
    print(f"  structurally order-bearing               : {rt_structural}"
          f"   <- what the core graph cannot guarantee")
    print(f"  errored                                  : {rt_err}")
    print("\nAASLD-Linked")
    print(f"  cases carrying an ordering graph: {ordered}")
    for case in order_only[: args.show]:
        print(f"    order-dependent: {case}")

    for case, why in errored[: args.show]:
        print(f"\n  ERROR {case}\n      {why[:200]}")
    for case, expected, actual in failed[: args.show]:
        print(f"\n  DIFFERS {case}")
        print(describe(expected, actual))

    return 0 if not failed and not errored else 1


if __name__ == "__main__":
    sys.exit(main())
