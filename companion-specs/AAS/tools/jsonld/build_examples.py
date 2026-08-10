#!/usr/bin/env python3
"""
Build the worked examples from the published IDTA submodel templates.

The examples are generated rather than written. A hand-written example says what
its author believes; a generated one says what the tools do, and the tools are
the same ones the conformance runs use. Every file this writes has been through
a check before it is written:

* an authored JSON-LD document is written only if reading it back gives the graph
  it was made from (clause 1 and `AASLD-Authored`); and
* a Thing Description is written only if projecting it gives the AddressSpace
  clause 5.6 of the AAS companion specification materializes (Annex F).

The sources are the templates `dpp_inventory.py` cached from
`admin-shell-io/submodel-templates`. They are the submodels the Digital Product
Passport and the Digital Battery Passport are actually made of, so the examples
are the shapes an implementer meets rather than shapes invented for a document.

Usage:
    python build_examples.py [--list]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
AAS_DIR = os.path.normpath(os.path.join(HERE, "..", ".."))
TEMPLATES = os.path.join(AAS_DIR, "jsonld", ".templates")
OUT_LD = os.path.join(AAS_DIR, "examples", "jsonld")
OUT_WOT = os.path.join(AAS_DIR, "examples", "wot", "submodels")
OUT_MIN = os.path.join(AAS_DIR, "examples", "wot", "minimal")
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
CONTEXT_IRI = "https://w3id.org/aas-jsonld/context"

sys.path.insert(0, HERE)

import wot_bridge  # noqa: E402
from authored import (as_graph, author, load_context, lower_graph,  # noqa: E402
                      read_back, term)
from pyld import jsonld  # noqa: E402
from rdflib import BNode, Graph  # noqa: E402
from conformance import BASE, canonical  # noqa: E402
from lift import Lifter, Ontology, Schema, serialize  # noqa: E402

ONTOLOGY = Ontology()
SCHEMA = Schema()

# The submodels a product passport is assembled from. One per subject area, and
# the newest revision of each where the cache holds more than one.
SELECTED = [
    ("digital-nameplate",
     "published__Digital Battery Passport__1_Digital Nameplate__1__0__"
     "IDTA 02035-1_DBP-Part-1_Digital Nameplate.json"),
    ("handover-documentation",
     "published__Digital Battery Passport__2_Handover Documentation__1__0__"
     "IDTA 02035-2_DBP-Part-2_HandoverDocumentation.json"),
    ("product-carbon-footprint",
     "published__Digital Battery Passport__3_Product Carbon Footprint__1__0__"
     "IDTA 02035-3_DBP-Part-3_ProductCarbonFootprint.json"),
    ("technical-data",
     "published__Digital Battery Passport__4_Technical Data__1__0__1__"
     "IDTA 02035-4_DBP-Part-4_TechnicalData.json"),
    ("material-composition",
     "published__Digital Battery Passport__6_Material Composition__1__0__1__"
     "IDTA 02035-6_DBP-Part-6_MaterialComposition.json"),
    ("circularity",
     "published__Digital Battery Passport__7_Circularity__1__0__1__"
     "IDTA 02035-7_DBP-Part-7_Circularity.json"),
    ("digital-product-passport",
     "published__Digital Product Passport__Digital Product Passport Part-1__1__0__1__"
     "IDTA 02099-1_Template Digital Product Passport - Part 1.json"),
]


def graph_of(env):
    sink = Lifter(ONTOLOGY, BASE, "linked", schema=SCHEMA).lift(env)
    core = serialize(sink, with_graphs=False)
    order = "\n".join(f"{s} {p} {o} ." for s, p, o, _ in sink.quads)
    return core, order


def write_authored(name, env, context_doc):
    """The pure JSON-LD form: the AAS and nothing else. No WoT, no OPC UA."""
    core, order = graph_of(env)
    doc_text = author(core, order, context_doc)
    doc = json.loads(doc_text)
    doc["@context"] = CONTEXT_IRI

    # The document is checked in the form it ships, context IRI and all.
    back_core, back_order = read_back(as_written(doc, context_doc))
    recovered = lower_graph(back_core, back_order, seed=20260809)
    source = json.loads(json.dumps(env))
    for collection in ("assetAdministrationShells", "submodels", "conceptDescriptions"):
        if collection in source:
            source[collection] = sorted(source[collection], key=lambda n: n.get("id", ""))
    if canonical(recovered) != canonical(source):
        raise SystemExit(f"{name}: the authored document does not lower to the source AAS")
    if fingerprints(as_graph(back_core)) != fingerprints(as_graph(core)):
        raise SystemExit(f"{name}: the authored document does not carry its own graph")

    path = os.path.join(OUT_LD, f"{name}.aas.jsonld")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    return path, len(as_graph(core))


def write_minimal_td(name, env, context_doc):
    """The authored AAS plus the least that makes it a Thing Description.

    Not the projection-complete document `write_thing_descriptions` writes. This
    one answers a narrower question: what has to be added to a pure JSON-LD AAS
    before a WoT runtime will load it at all. The answer is four members, three
    of which are the Thing Description's own requirements and one of which is
    this Binding's:

      `@context`            the TD context, alongside the AAS one
      `title`               required of every Thing Description
      `securityDefinitions` required, even when the scheme is `nosec`
      `security`            required
      `@type`               `uav:object`, plus the ObjectType, per Annex F

    What it does not carry is the per-node `uav:id`, `uav:browseName`,
    `uav:componentOf` and ordering links. Without those a converter still
    projects the document, but the nodes it makes are named by browse path
    rather than by clause 5.3, so they are not the nodes clause 5.6 defines.
    That is the whole difference between this file and its neighbour, and it is
    why both are published.
    """
    core, order = graph_of(env)
    doc_text = author(core, order, context_doc)
    doc = json.loads(doc_text)
    submodels = env.get("submodels") or []
    title = submodels[0].get("idShort", name) if submodels else name

    doc["@context"] = ["https://www.w3.org/2022/wot/td/v1.1",
                       CONTEXT_IRI,
                       {"uav": "http://opcfoundation.org/UA/WoT-Binding/",
                        "i4aas": wot_bridge.I4AAS}]
    # Append, do not replace. The authored document's `@type` is the AAS class,
    # and overwriting it deletes `rdf:type aas:Submodel` - the one triple that
    # says what the document is.
    existing = doc.get("@type") or []
    existing = existing if isinstance(existing, list) else [existing]
    doc["@type"] = ["uav:object", "i4aas:AASSubmodelType"] + [
        t for t in existing if t not in ("uav:object", "i4aas:AASSubmodelType")]
    doc["title"] = title
    doc["securityDefinitions"] = {"nosec_sc": {"scheme": "nosec"}}
    doc["security"] = "nosec_sc"

    # The AAS content has to still be there. Checking for the five members
    # assigned immediately above would check that Python performs assignment;
    # this reads the document back, discards everything the WoT vocabulary added,
    # and requires the graph it was made from - the bar `write_authored` is held
    # to, allowing for the superset clause 1 permits.
    back_core, back_order = read_back(as_written(doc, context_doc))
    if not (fingerprints(aas_only(back_core)) == fingerprints(as_graph(core))
            and fingerprints(as_graph(back_order)) == fingerprints(as_graph(order))):
        raise SystemExit(f"{name}: the minimal Thing Description does not carry "
                         f"the AAS it was made from")

    path = os.path.join(OUT_MIN, f"{name}.td.jsonld")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    return path


def as_written(doc, context_doc):
    """The document exactly as it ships, with its context IRIs resolved locally.

    `write_authored` and `write_minimal_td` both replace the inline context with
    the IRI the context is published under, so the file that ships is not the
    string that was checked. Resolving that IRI against the local file, and the
    Thing Description context against a stub, checks the artefact rather than its
    predecessor - which matters while the `w3id.org` redirect is unregistered and
    the IRI does not resolve at all.
    """
    local = json.loads(json.dumps(doc))
    resolved = []
    for entry in (local["@context"] if isinstance(local["@context"], list)
                  else [local["@context"]]):
        if entry == CONTEXT_IRI:
            resolved.append(context_doc["@context"])
        elif isinstance(entry, str) and entry.startswith("https://www.w3.org/"):
            resolved.append({"id": "@id"})
        else:
            resolved.append(entry)
    local["@context"] = resolved
    return json.dumps(local, ensure_ascii=False)


def aas_only(nt_text):
    """The AAS triples of a graph: the vocabulary's predicates, and its classes."""
    out = Graph()
    for s, p, o in as_graph(nt_text):
        if str(p).startswith(wot_bridge.AAS_NS) or (
                str(p) == RDF_TYPE and str(o).startswith(wot_bridge.AAS_NS)):
            out.add((s, p, o))
    return out


def aas_graph_of(tds):
    """The AAS triples a Thing Description carries, as N-Triples.

    Everything outside the AAS vocabulary is discarded - the `uav` terms, the WoT
    terms, the Thing's own members - leaving what the document says as an Asset
    Administration Shell.

    The remote Thing Description context is replaced by a local stub rather than
    fetched, so the check runs offline. The stub has to reproduce the **keyword
    aliases** the real context defines, not only the terms this check needs to
    traverse. A stub that merely omits `id` makes a document carrying both `@id`
    and `id` look well formed here while a conforming processor rejects it with
    `colliding keywords`, which is exactly the defect this check exists to catch.
    """
    stub = {"id": "@id",
            "properties": {"@id": "https://example.invalid/wot#properties",
                           "@container": "@index"},
            "actions": {"@id": "https://example.invalid/wot#actions",
                        "@container": "@index"},
            "events": {"@id": "https://example.invalid/wot#events",
                       "@container": "@index"},
            "links": {"@id": "https://example.invalid/wot#links"},
            "title": "https://example.invalid/wot#title",
            "security": "https://example.invalid/wot#security",
            "securityDefinitions": "https://example.invalid/wot#securityDefinitions"}
    lines = []
    for td in tds:
        local = json.loads(json.dumps(td))
        inline = [c for c in local["@context"] if isinstance(c, dict)]
        merged = dict(stub)
        for c in inline:
            merged.update(c)
        local["@context"] = merged
        dataset = jsonld.to_rdf(local)
        for quads in dataset.values():
            for quad in quads:
                predicate = quad["predicate"]["value"]
                is_aas = predicate.startswith(wot_bridge.AAS_NS) or (
                    predicate == RDF_TYPE
                    and quad["object"]["value"].startswith(wot_bridge.AAS_NS))
                if is_aas:
                    lines.append("%s %s %s ." % (term(quad["subject"]),
                                                 term(quad["predicate"]),
                                                 term(quad["object"])))
    return "\n".join(lines)


def write_thing_descriptions(name, env, context_doc):
    """The same submodel as a Thing Description, with the WoT vocabulary added."""
    tds = wot_bridge.generate(env, "attype")
    want = wot_bridge.expected(env)
    if not want:
        raise SystemExit(f"{name}: no nodes expected, so the comparison would pass "
                         f"without testing anything")
    got = wot_bridge.project(tds, honour_proposed_term=True, form="attype")
    missing, extra, differing = wot_bridge.compare(want, got)
    if missing or extra or differing:
        raise SystemExit(f"{name}: projection does not match clause 5.6 "
                         f"({len(missing)} missing, {len(extra)} unexpected, "
                         f"{len(differing)} differing)")
    for td in tds:
        td["securityDefinitions"] = {"nosec_sc": {"scheme": "nosec"}}
        td["security"] = "nosec_sc"

    # The document has to be an AAS as well as a projection, or the `aas` prefix
    # is declared and never used. What the Thing Descriptions say as an AAS is
    # compared against what the reference lifting says from the same submodels.
    carried = as_graph(aas_graph_of(tds))
    expected_aas = as_graph(graph_of({"submodels": env.get("submodels") or []})[0])
    missing = fingerprints(expected_aas) - fingerprints(carried)
    if missing:
        raise SystemExit(f"{name}: the Thing Description does not carry {len(missing)} "
                         f"of the source AAS's nodes, for example {sorted(missing)[:2]}")

    path = os.path.join(OUT_WOT, f"{name}.td.jsonld")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(tds, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path, len(want), len(carried)


def fingerprints(graph):
    """Each node of the graph as what it says about itself, counted.

    Subjects are not compared directly: the Thing Description names its nodes by
    clause 5.3 and the reference lifting leaves them blank, so no label is
    shared. A node is identified instead by the multiset of statements it makes,
    with any object that is *another node of the same graph* standing in as `[]`
    because its label is arbitrary on both sides. An IRI that is not described in
    the graph - an enumeration individual, an external reference - is kept
    verbatim, because there it is the value rather than a name for one.

    Counting those, rather than collecting predicates and values into sets, is
    what makes the check load-bearing: a set is unchanged by deleting every
    repeated occurrence of a value, and by moving every value onto one node, and
    neither of those is a document that still carries the AAS.
    """
    described = {s for s in graph.subjects()}
    per_subject = defaultdict(list)
    for s, p, o in graph:
        anonymous = isinstance(o, BNode) or o in described
        per_subject[s].append(f"{p.n3()} {'[]' if anonymous else o.n3()}")
    return Counter(tuple(sorted(statements)) for statements in per_subject.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="list the cached templates and stop")
    args = ap.parse_args()

    if args.list:
        for entry in sorted(os.listdir(TEMPLATES)):
            print("   ", entry)
        return 0

    if not os.path.isdir(TEMPLATES):
        print("no template cache: run dpp_inventory.py first", file=sys.stderr)
        return 1

    os.makedirs(OUT_LD, exist_ok=True)
    os.makedirs(OUT_WOT, exist_ok=True)
    os.makedirs(OUT_MIN, exist_ok=True)
    context_doc = load_context()
    wot_bridge.load_type_nodeids()

    written = 0
    for name, filename in SELECTED:
        path = os.path.join(TEMPLATES, filename)
        if not os.path.exists(path):
            print(f"    missing from the cache, skipped: {filename}", file=sys.stderr)
            continue
        with open(path, encoding="utf-8") as f:
            env = json.load(f)
        ld_path, triples = write_authored(name, env, context_doc)
        write_minimal_td(name, env, context_doc)
        td_path, nodes, aas_triples = write_thing_descriptions(name, env, context_doc)
        print(f"  {name:26s} {triples:5d} triples -> examples/jsonld/{os.path.basename(ld_path)}"
              f"   {nodes:4d} nodes + {aas_triples:5d} AAS triples -> examples/wot/submodels/{os.path.basename(td_path)}")
        written += 1

    print(f"\n{written} submodel(s), three files each: the AAS as pure JSON-LD, the same "
          f"document made loadable as a Thing Description, and the projection-complete\n"
          f"Thing Description. Every authored document lowers back to its source AAS, every\n"
          f"minimal document still carries that AAS once the WoT vocabulary is discarded, and\n"
          f"every projection-complete document carries it and projects without difference\n"
          f"against the reference materializer - which is a comparison of this document's own\n"
          f"rules against its own implementation, as Annex F.6 states.")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
