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

HERE = os.path.dirname(os.path.abspath(__file__))
AAS_DIR = os.path.normpath(os.path.join(HERE, "..", ".."))
TEMPLATES = os.path.join(AAS_DIR, "jsonld", ".templates")
OUT_LD = os.path.join(AAS_DIR, "examples", "jsonld")
OUT_WOT = os.path.join(AAS_DIR, "examples", "wot", "submodels")
OUT_MIN = os.path.join(AAS_DIR, "examples", "wot", "minimal")
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

sys.path.insert(0, HERE)

import wot_bridge  # noqa: E402
from authored import (as_graph, author, load_context, lower_graph,  # noqa: E402
                      read_back, term)
from pyld import jsonld  # noqa: E402
from rdflib import Literal  # noqa: E402
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
    doc["@context"] = "https://w3id.org/aas-jsonld/context"

    back_core, back_order = read_back(doc_text)
    recovered = lower_graph(back_core, back_order, seed=20260809)
    source = json.loads(json.dumps(env))
    for collection in ("assetAdministrationShells", "submodels", "conceptDescriptions"):
        if collection in source:
            source[collection] = sorted(source[collection], key=lambda n: n.get("id", ""))
    if canonical(recovered) != canonical(source):
        raise SystemExit(f"{name}: the authored document does not lower to the source AAS")
    if len(as_graph(back_core)) != len(as_graph(core)):
        raise SystemExit(f"{name}: the authored document does not carry the whole graph")

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
    doc = json.loads(author(core, order, context_doc))
    submodels = env.get("submodels") or []
    title = submodels[0].get("idShort", name) if submodels else name

    doc["@context"] = ["https://www.w3.org/2022/wot/td/v1.1",
                       "https://w3id.org/aas-jsonld/context",
                       {"uav": "http://opcfoundation.org/UA/WoT-Binding/",
                        "i4aas": wot_bridge.I4AAS}]
    doc["@type"] = ["uav:object", "i4aas:AASSubmodelType"]
    doc["title"] = title
    doc["securityDefinitions"] = {"nosec_sc": {"scheme": "nosec"}}
    doc["security"] = "nosec_sc"

    for member in ("@context", "@type", "title", "securityDefinitions", "security"):
        if member not in doc:
            raise SystemExit(f"{name}: minimal Thing Description is missing {member}")

    path = os.path.join(OUT_MIN, f"{name}.td.jsonld")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    return path


def aas_graph_of(tds, context_doc):
    """The AAS triples a Thing Description carries, as N-Triples.

    Everything outside the AAS vocabulary is discarded - the `uav` terms, the WoT
    terms, the Thing's own members - leaving what the document says as an Asset
    Administration Shell.

    The remote Thing Description context is replaced by a local stub rather than
    fetched, so the check runs offline. The stub defines only what is needed to
    reach the nested nodes - `properties` as an index container - because a term
    the context does not define is dropped, and dropping `properties` would drop
    every element with it. Nothing the stub defines survives the filter.
    """
    stub = {"properties": {"@id": "https://example.invalid/wot#properties",
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
    # is declared and never used. Every AAS property *and every literal value*
    # the reference lifting produces from the source submodels must be
    # recoverable from the Thing Descriptions. Subjects are not compared: the
    # Thing Description names its nodes by clause 5.3 and the lifting skolemizes
    # them, so the two agree on what is said and not on what it is said about.
    carried = as_graph(aas_graph_of(tds, context_doc))
    expected_aas = as_graph(graph_of({"submodels": env.get("submodels") or []})[0])
    lost_props = stated_properties(expected_aas) - stated_properties(carried)
    if lost_props:
        raise SystemExit(f"{name}: the Thing Description drops AAS properties: "
                         f"{sorted(lost_props)[:5]}")
    lost_values = stated_values(expected_aas) - stated_values(carried)
    if lost_values:
        raise SystemExit(f"{name}: the Thing Description drops {len(lost_values)} "
                         f"AAS values, for example {sorted(lost_values)[:3]}")

    path = os.path.join(OUT_WOT, f"{name}.td.jsonld")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(tds, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path, len(want), len(carried)


def stated_properties(graph):
    return {str(p) for _, p, _ in graph}


def stated_values(graph):
    """Every literal the graph states, with the property that states it."""
    return {(str(p), str(o)) for _, p, o in graph if isinstance(o, Literal)}


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
          f"Thing Description. Every authored document lowers back to its source AAS and "
          f"every projection-complete document projects to the AddressSpace clause 5.6 defines.")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
