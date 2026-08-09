#!/usr/bin/env python3
"""
The authored linked-data form: write an AAS as JSON-LD, get an AAS back.

Clause 1 says an Asset Administration Shell in JSON-LD is any JSON-LD 1.1
document whose RDF interpretation contains the graph the RDF mapping of
IDTA-01001 Part 1 defines. Nothing is required of its surface - not the member
names, not the nesting, not whether a term is compact or absolute.

This tool is what makes that checkable rather than asserted. For each document of
the corpus it:

1. lifts the AAS JSON document to the graph (clause 2), which is the content an
   author would be writing;
2. serializes that graph as idiomatic JSON-LD, compacted against the published
   context - prefixed IRIs, `@id`, `@type`, `@list` where order is carried. This
   is an *authored* document: it has the shape linked data has, not the shape the
   JSON mapping has;
3. reads that document back with a JSON-LD processor and takes its RDF;
4. checks the recovered graph against the graph of step 1; and
5. lowers the recovered graph (clause 4) and checks the AAS JSON document comes
   back.

Steps 3 to 5 are the claim `AASLD-Authored` makes. Step 2 is not normative - it
is one way of writing the document, chosen here because a generated example can
be checked, where a hand-written one can only be admired.

The superset allowance of clause 1 is exercised separately: `--superset` adds
triples in a foreign vocabulary to the authored document before step 3, and the
run must still produce the same AAS.

Usage:
    python authored.py [--corpus] [--limit N] [--superset] [--dump-one out.jsonld]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys

from pyld import jsonld
from rdflib import XSD, Dataset, Graph, Literal, Namespace
from rdflib.compare import isomorphic

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from conformance import (BASE, canonical, cases_from_corpus,  # noqa: E402
                         cases_from_fixtures)
from lift import Lifter, Ontology, Schema, iri, literal, serialize  # noqa: E402
from lower import Lowerer, parse_nt, unescape  # noqa: E402

ONTOLOGY = Ontology()
SCHEMA = Schema()

CONTEXT = os.path.normpath(os.path.join(HERE, "..", "..", "aas.context.jsonld"))
ORDER_GRAPH = "https://w3id.org/aas-jsonld/graph/order"
RDF_LANG_STRING = "http://www.w3.org/1999/02/22-rdf-syntax-ns#langString"
FOREIGN = Namespace("https://example.org/vocab/")


def load_actual(json_path):
    """The graph of clause 2, as N-Triples text.

    Text, not two parsed graphs. The ordering graph names blank nodes of the core
    graph, so the two must share one set of labels; parsing them separately lets
    a parser rename the nodes of one and not the other, and the ordering graph
    then points at nothing. Keeping the text is what keeps them in step.
    """
    with open(json_path, encoding="utf-8") as f:
        doc = json.load(f)
    sink = Lifter(ONTOLOGY, BASE, "linked", schema=SCHEMA).lift(doc)
    core = serialize(sink, with_graphs=False)
    order = "\n".join(f"{s} {p} {o} ." for s, p, o, _ in sink.quads)
    return core, order


def as_graph(nt_text) -> Graph:
    g = Graph()
    if nt_text.strip():
        g.parse(data=nt_text, format="nt")
    return g


def load_context():
    with open(CONTEXT, encoding="utf-8") as f:
        return json.load(f)


TERM_RE = re.compile(
    r'^(?:<(?P<iri>[^>]*)>'
    r'|(?P<bnode>_:\S+)'
    r'|"(?P<lex>(?:[^"\\]|\\.)*)"(?:\^\^<(?P<dt>[^>]*)>|@(?P<lang>[A-Za-z0-9-]+))?)$')


def to_term(text):
    """One N-Triples term as the processor's term dictionary."""
    m = TERM_RE.match(text.strip())
    if m is None:
        raise ValueError(f"unparsable term: {text[:80]!r}")
    if m.group("iri") is not None:
        return {"type": "IRI", "value": m.group("iri")}
    if m.group("bnode") is not None:
        return {"type": "blank node", "value": m.group("bnode")}
    node = {"type": "literal", "value": unescape(m.group("lex"))}
    if m.group("lang"):
        node["language"] = m.group("lang")
        node["datatype"] = RDF_LANG_STRING
    else:
        node["datatype"] = m.group("dt") or str(XSD.string)
    return node


def to_dataset(core_nt, order_nt):
    """The lifted graph as the processor's dataset, without going through text.

    The processor is never handed N-Quads text in either direction. Its N-Quads
    reader decodes `\\\\n` - an escaped backslash followed by the letter n - as an
    escaped backslash followed by a newline, and its writer emits a raw newline
    for the same input. Both corrupt a literal the published submodel templates
    contain. The structured form has no escaping in it, so neither can happen.
    """
    dataset = {}
    for name, text in (("@default", core_nt), (ORDER_GRAPH, order_nt)):
        quads = []
        for s, p, o in parse_nt(text):
            quads.append({"subject": to_term(s), "predicate": to_term(p),
                          "object": to_term(o)})
        if quads:
            dataset[name] = quads
    return dataset


def author(core_nt, order_nt, context_doc) -> str:
    """Write the graph the way an author writes it: as linked data.

    A real JSON-LD 1.1 processor does the work - it takes the dataset from RDF
    and compacts it against the published context. What comes out has prefixed
    IRIs, `@id` and `@type`, and nesting that follows the graph rather than the
    JSON mapping.

    The ordering graph is a named graph, so it is carried as a `@graph` entry of
    its own inside the document, which is how JSON-LD writes a dataset.
    """
    expanded = jsonld.from_rdf(to_dataset(core_nt, order_nt))
    compacted = jsonld.compact(expanded, context_doc["@context"])
    return json.dumps(compacted, ensure_ascii=False, sort_keys=True)


def add_foreign(doc_text):
    """Exercise the superset allowance of clause 1.

    A document may carry triples the AAS vocabulary does not define. They must
    survive the round trip to RDF untouched and must not reach the AAS JSON
    document, because the lowering reads the AAS vocabulary and nothing else.
    """
    doc = json.loads(doc_text)
    nodes = doc.get("@graph") if isinstance(doc, dict) else None
    target = None
    for node in (nodes if isinstance(nodes, list) else [doc]):
        if isinstance(node, dict) and "@graph" not in node:
            target = node
            break
    if target is not None:
        target["https://example.org/vocab/reviewedBy"] = {"@id": "https://example.org/people/1"}
        target["https://example.org/vocab/reviewNote"] = "carried through, not converted"
    return json.dumps(doc, ensure_ascii=False)


def read_back(doc_text):
    """Take the RDF of an authored document, the way any consumer would.

    The processor returns the dataset as terms, and the N-Triples text is written
    here with the same escaping the lifting uses. Going through the processor's
    own N-Quads writer instead loses data: given a literal containing a backslash
    followed by `n` - which the published submodel templates contain - it emits an
    escaped backslash followed by a raw newline, which is not a legal N-Quads
    literal and breaks any line-based reader.
    """
    dataset = jsonld.to_rdf(json.loads(doc_text))
    core, order = [], []
    for graph_name, quads in dataset.items():
        target = order if graph_name == ORDER_GRAPH else core
        for quad in quads:
            target.append("%s %s %s ." % (term(quad["subject"]),
                                          term(quad["predicate"]),
                                          term(quad["object"])))
    return "\n".join(core), "\n".join(order)


def term(node):
    """One RDF term of the processor's dataset, as N-Triples."""
    if node["type"] == "IRI":
        return iri(node["value"])
    if node["type"] == "blank node":
        return node["value"]
    return literal(node["value"], node.get("datatype"), node.get("language"))


def drop_foreign(nt_text):
    """Remove the triples clause 1's superset allowance let in."""
    return "\n".join(line for line in nt_text.splitlines()
                     if f"<{FOREIGN}" not in line)


def strip_foreign(g: Graph) -> Graph:
    out = Graph()
    for s, p, o in g:
        if not str(p).startswith(str(FOREIGN)):
            out.add((s, p, normalize_literal(o)))
    return out


def normalize_literal(term):
    """RDF 1.1 says a plain literal *is* `xsd:string`; rdflib keeps them apart.

    The lifting writes the datatype explicitly and a JSON-LD processor writes a
    plain literal, so the two graphs compare unequal on a difference RDF does not
    recognise. Dropping the explicit datatype puts both in the same form.
    """
    if isinstance(term, Literal) and term.datatype == XSD.string:
        return Literal(str(term))
    return term


def normalized(g: Graph) -> Graph:
    out = Graph()
    for s, p, o in g:
        out.add((s, p, normalize_literal(o)))
    return out


def lower_graph(core_nt, order_nt, seed):
    """Lower the recovered graph, shuffled, exactly as conformance.py does."""
    triples = parse_nt(core_nt)
    quads = parse_nt(order_nt) if order_nt.strip() else ()
    rng = random.Random(seed)
    rng.shuffle(triples)
    if quads:
        rng.shuffle(quads)
    lowerer = Lowerer(ONTOLOGY, SCHEMA)
    lowerer.load(triples, quads)
    return lowerer.lower()


def serialize_graph(g: Graph):
    if not len(g):
        return []
    return [line for line in g.serialize(format="nt").splitlines() if line.strip()]


def check(name, jpath, tpath, context_doc, superset, dump=None):
    with open(jpath, encoding="utf-8") as f:
        source = json.load(f)
    core_nt, order_nt = load_actual(jpath)

    doc_text = author(core_nt, order_nt, context_doc)
    if superset:
        doc_text = add_foreign(doc_text)
    if dump:
        with open(dump, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(json.loads(doc_text), indent=2, ensure_ascii=False, sort_keys=True))
            f.write("\n")

    back_core, back_order = read_back(doc_text)
    back_core = drop_foreign(back_core)
    graph_ok = (isomorphic(normalized(as_graph(back_core)), normalized(as_graph(core_nt)))
                and isomorphic(normalized(as_graph(back_order)),
                               normalized(as_graph(order_nt))))

    try:
        recovered = lower_graph(back_core, back_order, seed=20260809)
        for collection in ("assetAdministrationShells", "submodels", "conceptDescriptions"):
            if collection in source:
                source[collection] = sorted(source[collection], key=lambda n: n.get("id", ""))
        json_ok = canonical(recovered) == canonical(source)
        why = "" if json_ok else "documents differ"
    except Exception as exc:  # a lowering that raises is a failure, not a crash
        json_ok = False
        why = f"{type(exc).__name__}: {exc}"
    return graph_ok, json_ok, why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", action="store_true", help="run the pinned corpus, not the fixtures")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--superset", action="store_true",
                    help="add foreign-vocabulary triples to each authored document")
    ap.add_argument("--dump-one", help="write the first authored document here")
    args = ap.parse_args()

    context_doc = load_context()
    cases = list(cases_from_corpus() if args.corpus else cases_from_fixtures())
    if not cases:
        print("no cases: fetch the corpus first", file=sys.stderr)
        return 1
    if args.limit:
        cases = cases[:args.limit]

    graph_pass = json_pass = 0
    skipped = 0
    failures = []
    for i, (name, jpath, tpath) in enumerate(cases):
        dump = args.dump_one if (i == 0 and args.dump_one) else None
        try:
            g_ok, j_ok, why = check(name, jpath, tpath, context_doc, args.superset, dump)
        except (json.JSONDecodeError, UnicodeDecodeError):
            # An unreadable upstream file is not a result either way; the corpus
            # fetcher records these and `conformance.py` reports the same count.
            skipped += 1
            continue
        graph_pass += g_ok
        json_pass += j_ok
        if not (g_ok and j_ok) and len(failures) < 8:
            failures.append(f"    {name}: graph={g_ok} json={j_ok} {why}")

    total = len(cases) - skipped
    scope = "corpus" if args.corpus else "fixtures"
    extra = " with foreign triples added" if args.superset else ""
    print(f"AASLD-Authored over {total} {scope} document(s){extra}")
    print(f"  authored document carries the graph : {graph_pass}/{total}")
    print(f"  authored document lowers to the AAS : {json_pass}/{total}")
    if skipped:
        print(f"  unreadable upstream files skipped   : {skipped}")
    for line in failures:
        print(line)
    return 0 if graph_pass == total and json_pass == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
