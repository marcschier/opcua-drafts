#!/usr/bin/env python3
"""
Generate the AAS JSON-LD context, and measure what it achieves.

The context is a convenience layer, not the conformance mechanism. Saying so is
cheap; this tool proves it. It builds the context from the same pinned tables the
lifting uses, runs a real JSON-LD 1.1 processor over the corpus, and reports how
much of the normative graph the context reproduces on its own.

What the context can do, using JSON-LD 1.1:

  * alias `modelType` to `@type`, so a discriminated object gets its class;
  * resolve a JSON key to the right property IRI with **type-scoped** contexts,
    which is what makes `value` on `Property` a different IRI from `value` on
    `Range` without any procedural step;
  * reach nested objects that carry no discriminator - `Reference`, `Key`,
    `Qualifier`, `AssetInformation`, the language-string types - with
    **property-scoped** contexts, so the class comes from the property's range.

What it cannot do, and why the lifting exists:

  * emit an `Identifiable`'s `id` as both the subject IRI and a literal;
  * construct a subject term for an `id` that is not a legal IRI;
  * turn `"xs:int"` into `aas:DataTypeDefXsd/Int` (attempted here with an
    explicit term definition, and measured rather than assumed);
  * record the order of an array.

Usage:
    python make_context.py            # write the context
    python make_context.py --measure  # write it, then measure it
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from lift import AAS, Lifter, Ontology, Schema, serialize  # noqa: E402

OUT = os.path.join(ROOT, "aas.context.jsonld")
XSD = "http://www.w3.org/2001/XMLSchema#"


def literal_term(prop, onto):
    """A term definition for a datatype-valued member."""
    rng = (prop["range"] or "xs:string").split(":")[-1]
    return {"@id": prop["iri"], "@type": XSD + rng}


def build(onto: Ontology, schema: Schema):
    # Every class the JSON can present, and the members it can carry.
    classes = sorted(onto.superclasses)

    def members_of(cls):
        """Every JSON key valid on this class, with the property it denotes."""
        out = {}
        for c in reversed(onto.mro(cls)):
            for (owner, name), prop in onto.properties.items():
                if owner == c:
                    out[name] = prop
        return out

    def scoped_context(cls, depth=0):
        """The term definitions that apply inside an object of this class."""
        ctx = {}
        for name, prop in sorted(members_of(cls).items()):
            rng = prop["range"] or ""
            if prop["kind"] == "DatatypeProperty":
                term = literal_term(prop, onto)
            else:
                target = rng[4:] if rng.startswith("aas:") else None
                if target and target in onto.enums:
                    term = {"@id": prop["iri"], "@type": "@vocab"}
                else:
                    term = {"@id": prop["iri"], "@type": "@id"}
                    # A nested object with no discriminator carries no key a
                    # context could turn into `rdf:type`: injecting one would
                    # mean redefining the `@type` keyword, which JSON-LD
                    # forbids. The scoped context can still give the object's
                    # members their correct property IRIs, so it is emitted; the
                    # missing type triple is the gap the measurement records.
                    if target and target not in schema.model_type and depth < 3:
                        inner = scoped_context(target, depth + 1)
                        if inner:
                            term["@context"] = inner
            if schema.is_array(onto, cls, name):
                term["@container"] = "@set"
            ctx[name] = term
        return ctx

    context = {
        "@version": 1.1,
        "@vocab": AAS,
        "aas": AAS,
        "modelType": "@type",
        "id": {"@id": AAS + "Identifiable/id", "@type": XSD + "string"},
        "assetAdministrationShells": {"@id": AAS + "Environment/assetAdministrationShells",
                                      "@type": "@id", "@container": "@set"},
        "submodels": {"@id": AAS + "Environment/submodels",
                      "@type": "@id", "@container": "@set"},
        "conceptDescriptions": {"@id": AAS + "Environment/conceptDescriptions",
                                "@type": "@id", "@container": "@set"},
    }

    # Enumeration spellings. A term containing a colon is read as a compact IRI
    # and JSON-LD requires it to expand to its own definition, so `xs:int`
    # cannot be aliased to `aas:DataTypeDefXsd/Int`: a processor rejects the
    # context with "term in form of IRI must expand to definition". The
    # enumerations whose JSON spelling has no colon can be aliased; the
    # `DataTypeDefXsd` values cannot, and that is the sharpest of the context's
    # limits. The lifting resolves them from the ontology instead.
    unaliasable = []
    for enum, members in sorted(onto.enums.items()):
        spellings = schema.enum_json.get(enum, [])
        for member in members:
            bare = member.lower()
            spelling = next((s for s in spellings if s.split(":", 1)[-1].lower() == bare), member)
            if ":" in spelling:
                unaliasable.append((enum, spelling))
                continue
            context.setdefault(spelling, f"{AAS}{enum}/{member}")

    # Type-scoped contexts, one per discriminated class.
    for cls in classes:
        if cls in schema.model_type:
            context[cls] = {"@id": f"{AAS}{cls}", "@context": scoped_context(cls)}

    return {"@context": context}, unaliasable


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------
def classify(via_context, via_lift, onto, schema):
    """Why the two graphs differ, by cause rather than by triple.

    Listing raw triples says only that they differ. The specification needs to
    state which of its clauses a context cannot carry, so the differences are
    attributed to a cause.
    """
    from rdflib import URIRef
    from rdflib.term import BNode

    causes = {}

    def bump(name, n=1):
        causes[name] = causes.get(name, 0) + n

    rdf_type = URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

    # A root Identifiable: the lifting gives it an IRI subject, a context can
    # only leave it a blank node, because `id` cannot be both subject and literal.
    id_prop = URIRef(AAS + "Identifiable/id")
    lift_roots = {s for s, _, _ in via_lift.triples((None, id_prop, None))}
    ctx_roots = {s for s, _, _ in via_context.triples((None, id_prop, None))}
    bump("root subject is a blank node, not an IRI",
         sum(1 for s in ctx_roots if isinstance(s, BNode)))

    # A nested object with no `modelType` gets no rdf:type from a context.
    for s, _, o in via_lift.triples((None, rdf_type, None)):
        cls = str(o).rsplit("/", 1)[-1]
        if cls not in schema.model_type and (s, rdf_type, o) not in via_context:
            bump("nested object has no rdf:type")

    # DataTypeDefXsd values cannot be aliased, so they land as `xs:int` IRIs.
    for s, p, o in via_context:
        if isinstance(o, URIRef) and str(o).startswith("xs:"):
            bump("enumeration value left as a compact IRI")

    return causes


def measure(context_doc, limit=0):
    from pyld import jsonld
    from rdflib import Graph
    from rdflib.compare import isomorphic

    corpus = os.path.join(ROOT, ".corpus")
    manifest = os.path.join(corpus, "manifest.json")
    cases = []
    if os.path.exists(manifest):
        with open(manifest, encoding="utf-8") as f:
            for case in sorted(json.load(f)["cases"]):
                p = os.path.join(corpus, "json", *case.split("/")) + ".json"
                if os.path.exists(p):
                    cases.append((case, p))
    else:
        with open(os.path.join(ROOT, "fixtures", "index.json"), encoding="utf-8") as f:
            for entry in json.load(f)["cases"]:
                cases.append((entry["case"], os.path.join(ROOT, "fixtures", entry["file"] + ".json")))
    if limit:
        cases = cases[:limit]

    onto, schema = Ontology(), Schema()
    base = "https://example.org/aas/"
    same, differ, errored = 0, 0, 0
    causes = {}
    reproduced, total_lift = 0, 0
    for case, path in cases:
        try:
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
            framed = dict(doc)
            framed["@context"] = context_doc["@context"]
            nq = jsonld.to_rdf(framed, {"format": "application/n-quads", "base": base})
            via_context = Graph()
            via_context.parse(data=nq, format="nt")

            lifter = Lifter(onto, base, "core", schema=schema)
            via_lift = Graph()
            via_lift.parse(data=serialize(lifter.lift(doc), with_graphs=False), format="nt")
        except Exception:  # noqa: BLE001
            errored += 1
            continue
        # How much of the lifted graph the context reproduces. Compared on
        # predicate and object, and only where the object is an IRI or a
        # literal: a blank node object cannot match by label, so counting those
        # would penalise the context for something neither side controls.
        from rdflib.term import BNode as _BNode
        lift_pairs = [(str(p), str(o)) for _, p, o in via_lift if not isinstance(o, _BNode)]
        ctx_pairs = {(str(p), str(o)) for _, p, o in via_context if not isinstance(o, _BNode)}
        total_lift += len(lift_pairs)
        reproduced += sum(1 for pair in lift_pairs if pair in ctx_pairs)
        if isomorphic(via_context, via_lift):
            same += 1
        else:
            differ += 1
            for cause, n in classify(via_context, via_lift, onto, schema).items():
                if n:
                    causes[cause] = causes.get(cause, 0) + 1
    return cases, same, differ, errored, causes, reproduced, total_lift


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    onto, schema = Ontology(), Schema()
    doc, unaliasable = build(onto, schema)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=2, sort_keys=False, ensure_ascii=False)
        f.write("\n")
    terms = len(doc["@context"])
    scoped = sum(1 for v in doc["@context"].values()
                 if isinstance(v, dict) and "@context" in v)
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {terms} terms, {scoped} type-scoped")
    if unaliasable:
        enums = sorted({e for e, _ in unaliasable})
        print(f"  not aliasable (spelling contains a colon): "
              f"{len(unaliasable)} values across {enums}")

    if not args.measure:
        return 0

    cases, same, differ, errored, causes, reproduced, total_lift = measure(doc, args.limit)
    total = len(cases)
    print(f"\ncontext measured against the lifting over {total} cases")
    print(f"  graphs identical : {same}")
    print(f"  graphs differ    : {differ}")
    print(f"  errored          : {errored}")
    if total_lift:
        pct = 100.0 * reproduced / total_lift
        print(f"\n  predicate/object pairs of the lifted graph that the context reproduces:")
        print(f"    {reproduced} of {total_lift}  ({pct:.1f}%)")
    if causes:
        print("\n  why the rest differ, by cause (cases affected):")
        for cause, n in sorted(causes.items(), key=lambda kv: -kv[1]):
            print(f"    {n:6d}  {cause}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
