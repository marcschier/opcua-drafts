#!/usr/bin/env python3
"""
Build the worked examples from the published IDTA submodel templates.

The examples are generated rather than written. A hand-written example says what
its author believes; a generated one says what the tools do, and the tools are
the same ones the conformance runs use. An independent validator processes the
final serialized bytes before each file is written:

* an authored JSON-LD document is written only if reading it back gives the graph
  it was made from (clause 1 and `AASLD-Authored`); and
* a Thing Description is written only if it passes JSON-LD processing, the
  pinned W3C TD 1.1 schema and the complete hierarchy/order projection check.

The sources are seven templates vendored from an immutable
`admin-shell-io/submodel-templates` commit with SHA-256 metadata. They are the
submodels the Digital Product Passport and the Digital Battery Passport are
actually made of, so a clean checkout regenerates the same shapes without a
network request or an ignored cache.

Usage:
    python build_examples.py [--list]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AAS_DIR = os.path.normpath(os.path.join(HERE, "..", ".."))
OUT_LD = os.path.join(AAS_DIR, "examples", "jsonld")
OUT_WOT = os.path.join(AAS_DIR, "examples", "wot", "submodels")
OUT_MIN = os.path.join(AAS_DIR, "examples", "wot", "minimal")
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

sys.path.insert(0, HERE)

import wot_bridge  # noqa: E402
import validate_examples  # noqa: E402
from authored import as_graph, author, load_context, term  # noqa: E402
from pyld import jsonld  # noqa: E402
from rdflib import Literal  # noqa: E402
from lift import Lifter, Ontology, Schema, serialize, subject_iri  # noqa: E402

ONTOLOGY = Ontology()
SCHEMA = Schema()

# The submodels a product passport is assembled from. One per subject area.
SELECTED = validate_examples.TEMPLATE_SOURCES


def graph_of(env):
    sink = Lifter(ONTOLOGY, "linked", schema=SCHEMA).lift(env)
    core = serialize(sink, with_graphs=False)
    order = "\n".join(f"{s} {p} {o} ." for s, p, o, _ in sink.quads)
    return core, order


def relative_context(path, target):
    return os.path.relpath(target, os.path.dirname(path)).replace("\\", "/")


def final_text(doc):
    return json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def bundle_td_context(doc, path):
    inline = {}
    for entry in doc.get("@context", []):
        if isinstance(entry, dict):
            inline.update(entry)
    inline.pop("aas", None)
    inline.pop("uav", None)
    inline.pop("ua", None)
    inline["id"] = "@id"
    doc["@context"] = [
        validate_examples.TD_CONTEXT_URL,
        relative_context(path, validate_examples.AAS_CONTEXT),
        relative_context(path, validate_examples.BINDING_CONTEXT),
        inline,
    ]
    return doc


def write_final(path, doc, *, td=False, source=None, projection=False):
    text = final_text(doc)
    validate_examples.validate_bytes(
        os.path.abspath(path), text, td=td, source=source, projection=projection)
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def projection_paths(root_path, tds):
    roots = [td for td in tds if not td.get("uav:componentOf")]
    if len(roots) != 1:
        raise SystemExit(
            f"{root_path}: expected one projected Submodel root, got {len(roots)}")
    object_dir = root_path.removesuffix(".td.jsonld") + ".objects"
    paths = {}
    for td in tds:
        if td is roots[0]:
            path = root_path
        else:
            self_links = [
                link for link in td.get("links", [])
                if link.get("rel") == "self"
            ]
            if len(self_links) != 1:
                raise SystemExit(
                    f"{td.get('uav:id')}: expected one self link")
            digest = hashlib.sha256(
                self_links[0]["href"].encode("utf-8")).hexdigest()
            path = os.path.join(object_dir, digest + ".td.jsonld")
        paths[id(td)] = path
    return paths, object_dir


def write_projection_bundle(root_path, tds, source):
    paths, object_dir = projection_paths(root_path, tds)
    serialized = []
    for td in tds:
        path = paths[id(td)]
        serialized.append(
            (os.path.abspath(path),
             final_text(bundle_td_context(td, path))))
    result = validate_examples.validate_projection_bundle(serialized, source)

    if os.path.isdir(object_dir):
        shutil.rmtree(object_dir)
    os.makedirs(object_dir, exist_ok=True)
    for path, text in serialized:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    return result


def write_authored(name, env, context_doc):
    """The pure JSON-LD form: the AAS and nothing else. No WoT, no OPC UA."""
    core, order = graph_of(env)
    doc_text = author(core, order, context_doc)
    doc = json.loads(doc_text)
    path = os.path.join(OUT_LD, f"{name}.aas.jsonld")
    doc["@context"] = relative_context(path, validate_examples.AAS_CONTEXT)
    write_final(path, doc, source=env)
    return path, len(as_graph(core))


def as_td_object(doc, env, name, path):
    """Promote the Submodel node to the TD root without changing its graph."""
    submodels = env.get("submodels") or []
    if len(submodels) != 1:
        raise SystemExit(f"{name}: a Thing Description example requires one submodel")
    identifier = submodels[0]["id"]
    graph = doc.get("@graph")
    if not isinstance(graph, list):
        raise SystemExit(f"{name}: authored JSON-LD did not produce an @graph")

    root = None
    included = []
    for node in graph:
        if isinstance(node, dict) and node.get("id") == identifier:
            if root is not None:
                raise SystemExit(f"{name}: more than one JSON-LD node carries the submodel id")
            root = node
        else:
            included.append(node)
    if root is None:
        raise SystemExit(f"{name}: no JSON-LD node carries the submodel id")

    for node in graph:
        if isinstance(node, dict) and "id" in node:
            node["aas:Identifiable/id"] = node.pop("id")
    root.pop("@id", None)
    root["id"] = subject_iri(identifier)
    if included:
        root["@included"] = included
    types = root.get("@type", [])
    if not isinstance(types, list):
        types = [types]
    root["@type"] = ["uav:object", "i4aas:AASSubmodelType", *types]
    root["@context"] = [
        validate_examples.TD_CONTEXT_URL,
        relative_context(path, validate_examples.AAS_CONTEXT),
        relative_context(path, validate_examples.BINDING_CONTEXT),
        {
            "id": "@id",
            "i4aas": wot_bridge.I4AAS,
        },
    ]
    root["title"] = submodels[0].get("idShort", name)
    root["securityDefinitions"] = {"nosec_sc": {"scheme": "nosec"}}
    root["security"] = "nosec_sc"
    return root


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
    path = os.path.join(OUT_MIN, f"{name}.td.jsonld")
    doc = as_td_object(json.loads(author(core, order, context_doc)), env, name, path)
    write_final(path, doc, td=True, source=env)
    return path


def aas_graph_of(tds, context_doc):
    """The AAS triples a Thing Description carries, as N-Triples.

    Everything outside the AAS vocabulary is discarded - the `uav` terms, the WoT
    terms, the Thing's own members - leaving what the document says as an Asset
    Administration Shell.

    The remote Thing Description context is replaced by a local stub rather than
    fetched, so the check runs offline. Blank nodes are scoped per TD document
    before the datasets are combined, as JSON-LD requires.
    """
    stub = {"properties": {"@id": "https://example.invalid/wot#properties",
                           "@container": "@index"},
            "links": {"@id": "https://example.invalid/wot#links"},
            "title": "https://example.invalid/wot#title",
            "security": "https://example.invalid/wot#security",
            "securityDefinitions": "https://example.invalid/wot#securityDefinitions"}
    lines = []
    for document_index, td in enumerate(tds):
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
                    scoped = []
                    for part in (
                            quad["subject"], quad["predicate"], quad["object"]):
                        part = dict(part)
                        if part.get("type") == "blank node":
                            part["value"] = (
                                f"_:d{document_index}-"
                                + part["value"].removeprefix("_:"))
                        scoped.append(part)
                    lines.append("%s %s %s ." % tuple(term(part) for part in scoped))
    return "\n".join(lines)


def write_thing_descriptions(name, env, context_doc):
    """The same submodel as binding-valid Object Thing Descriptions."""
    tds = wot_bridge.generate(env, "attype")
    want = wot_bridge.expected(env)
    got = wot_bridge.project(tds, honour_proposed_term=True, form="attype")
    missing, extra, differing = wot_bridge.compare(want, got)
    if missing or extra or differing:
        raise SystemExit(f"{name}: projection does not match clause 5.6 "
                         f"({len(missing)} missing, {len(extra)} unexpected, "
                         f"{len(differing)} differing)")
    # The document has to be an AAS as well as a projection, or the `aas` prefix
    # is declared and never used. Every AAS property *and every literal value*
    # the reference lifting produces from the source submodels must be
    # recoverable from the Thing Descriptions. The independent final-byte check
    # below also compares subjects and the complete graph; this early emitter
    # check keeps a short diagnostic for dropped properties or literals.
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
    result = write_projection_bundle(path, tds, env)
    return path, len(want), len(carried), len(tds), result


def write_fixture_thing_descriptions():
    written = 0
    fixtures = os.path.join(AAS_DIR, "tools", "fixtures")
    for filename in sorted(os.listdir(fixtures)):
        if not filename.endswith(".json"):
            continue
        name = filename[:-5]
        with open(os.path.join(fixtures, filename), encoding="utf-8") as stream:
            env = json.load(stream)
        tds = wot_bridge.generate(env, "attype")
        path = os.path.join(AAS_DIR, "examples", "wot", f"{name}.td.jsonld")
        write_projection_bundle(path, tds, env)
        written += len(tds)
    return written


def stated_properties(graph):
    return {str(p) for _, p, _ in graph}


def stated_values(graph):
    """Every literal the graph states, with the property that states it."""
    return {(str(p), str(o)) for _, p, o in graph if isinstance(o, Literal)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="list the vendored templates and stop")
    args = ap.parse_args()

    validate_examples.verify_vendor()
    if args.list:
        for name, path in SELECTED:
            print(f"    {name}: {path}")
        return 0

    os.makedirs(OUT_LD, exist_ok=True)
    os.makedirs(OUT_WOT, exist_ok=True)
    os.makedirs(OUT_MIN, exist_ok=True)
    context_doc = load_context()
    wot_bridge.load_type_nodeids()

    written = 0
    for name, path in SELECTED:
        if not path.is_file():
            print(f"    missing vendored template: {path}", file=sys.stderr)
            return 1
        with open(path, encoding="utf-8") as f:
            env = json.load(f)
        ld_path, triples = write_authored(name, env, context_doc)
        write_minimal_td(name, env, context_doc)
        td_path, nodes, aas_triples, td_count, _ = write_thing_descriptions(
            name, env, context_doc)
        print(f"  {name:26s} {triples:5d} triples -> examples/jsonld/{os.path.basename(ld_path)}"
              f"   {nodes:4d} nodes in {td_count:3d} TDs + {aas_triples:5d} AAS triples "
              f"-> examples/wot/submodels/{os.path.basename(td_path)}")
        written += 1

    fixture_count = write_fixture_thing_descriptions()

    print(f"\n{written} submodel bundle(s), plus {fixture_count} fixture TD(s): "
          f"the AAS as pure JSON-LD, the same "
          f"document made loadable as a Thing Description, and one projection-complete\n"
          f"Thing Description per OPC UA Object. Every authored document lowers back to its "
          f"source AAS and every projection bundle projects to the AddressSpace clause 5.6 defines.")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())
