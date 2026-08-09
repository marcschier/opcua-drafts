#!/usr/bin/env python3
"""
Lift an AAS JSON document into RDF, per the AAS JSON-LD specification.

The lifting is table-driven: the tables are read from the pinned upstream OWL
ontology rather than restated here, so the mapping cannot drift from the
ontology it claims to target. What this module adds is the part the ontology
does not state and a JSON-LD context cannot perform:

  * resolving a JSON key to a property IRI by walking the class hierarchy, since
    a key declared on `Referable` appears on a JSON object whose `modelType` is
    `Property`;
  * inferring the class of a nested object that carries no `modelType`, from the
    range of the property that reaches it;
  * turning an enumeration value into a named individual;
  * constructing the subject term of an `Identifiable`, including the case the
    upstream specification leaves undefined - an `id` that is not a legal IRI
    (defect D4);
  * emitting the ordering that the upstream serialization discards (defect D2),
    into a separate enrichment graph.

Output is N-Triples (or N-Quads when an enrichment graph is produced), because
comparing graphs is the whole point and N-Triples is the form a comparison can
be done on without a parser.

Usage:
    python lift.py <input.json> --base https://example.org/aas/ [--profile linked]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ONTOLOGY = os.path.join(os.path.dirname(HERE), "upstream", "rdf-ontology.ttl")
SCHEMA = os.path.join(os.path.dirname(HERE), "upstream", "aas.schema.json")

AAS = "https://admin-shell.io/aas/3/0/"
XS = "http://www.w3.org/2001/XMLSchema#"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
# Minted for what the upstream serialization cannot express. See the register.
LD = "https://w3id.org/aas-jsonld/"
ORDER_GRAPH = LD + "graph/order"

# The three collections of an Environment, and the class each holds.
ROOT_COLLECTIONS = {
    "assetAdministrationShells": "AssetAdministrationShell",
    "submodels": "Submodel",
    "conceptDescriptions": "ConceptDescription",
}

# Ordering. The upstream serialization discards the order of every multi-valued
# property (defect D2), so an array that came in as `[a, b]` may come back as
# `[b, a]`. That is harmless for a set, and wrong for `Reference/keys`, where the
# key sequence is the reference path, and for a `SubmodelElementList` whose
# `orderRelevant` is true, and for a multi-language value, whose array order the
# metamodel's own serialization preserves.
#
# Rather than enumerate the ordered cases and be wrong about one, the enrichment
# profile records the position of every member of every array-valued property.
# Which properties those are is read from the pinned JSON Schema, not listed here.


# ---------------------------------------------------------------------------
# Ontology tables
# ---------------------------------------------------------------------------
class Ontology:
    def __init__(self, path=ONTOLOGY):
        text = open(path, encoding="utf-8").read()

        # Class blocks, parsed once. A block runs to the next top-level subject,
        # which is either an `aas:Name rdf:type` line or a `<...>` line at the
        # start of a line. Scanning for `owl:oneOf` across the whole file instead
        # would attribute one class's enumeration members to an earlier class.
        blocks = re.findall(
            r"^aas:(\w+)\s+rdf:type\s+owl:Class\s*;(.*?)(?=^aas:\w+\s+rdf:type|^<|\Z)",
            text, re.S | re.M)
        self.superclasses = {}
        self.enums = {}
        for name, body in blocks:
            self.superclasses.setdefault(name, [])
            self.superclasses[name] += re.findall(r"rdfs:subClassOf\s+aas:(\w+)", body)
            one_of = re.search(r"owl:oneOf\s*\((.*?)\)", body, re.S)
            if one_of:
                members = re.findall(
                    r"<" + re.escape(AAS) + re.escape(name) + r"/(\w+)>", one_of.group(1))
                if members:
                    self.enums[name] = members

        self.properties = {}   # (owner, name) -> {"iri", "kind", "range"}
        for owner, name, kind, body in re.findall(
            r"<" + re.escape(AAS) + r"(\w+)/(\w+)>\s+rdf:type\s+owl:(DatatypeProperty|ObjectProperty)\s*;(.*?)(?=\n<|\Z)",
            text, re.S):
            rng = re.findall(r"rdfs:range\s+(\S+)", body)
            self.properties[(owner, name)] = {
                "iri": f"{AAS}{owner}/{name}",
                "kind": kind,
                "range": rng[0] if rng else None,
            }

    def mro(self, cls):
        """The class and its ancestors, breadth first, without duplicates."""
        seen, order, queue = set(), [], [cls]
        while queue:
            c = queue.pop(0)
            if c in seen:
                continue
            seen.add(c)
            order.append(c)
            queue += self.superclasses.get(c, [])
        return order

    def resolve(self, cls, key):
        """The property a JSON key denotes on an object of this class."""
        for c in self.mro(cls):
            hit = self.properties.get((c, key))
            if hit:
                return hit
        return None


class Schema:
    """The facts the ontology does not carry: discriminators, arrays, enum spelling."""

    def __init__(self, path=SCHEMA):
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        self.defs = doc.get("$defs") or doc.get("definitions") or {}

        # A class carries `modelType` when its definition pins it to a constant.
        self.model_type = set()
        for name, node in self.defs.items():
            for const in re.findall(r'"modelType":\s*\{"const":\s*"(\w+)"', json.dumps(node)):
                self.model_type.add(const)

        # Arrays, and the JSON type of each scalar member, keyed by (class, member).
        self.arrays = set()
        self.scalar_type = {}
        for name, node in self.defs.items():
            for props in self._property_blocks(node):
                for member, spec in props.items():
                    if not isinstance(spec, dict):
                        continue
                    if spec.get("type") == "array":
                        self.arrays.add((name, member))
                    elif "type" in spec:
                        self.scalar_type[(name, member)] = spec["type"]

        # Enumeration spelling: the ontology individual is `Int`, the JSON is `xs:int`.
        self.enum_json = {}
        for name, node in self.defs.items():
            values = node.get("enum")
            if values:
                self.enum_json[name] = list(values)

    @staticmethod
    def _property_blocks(node):
        if not isinstance(node, dict):
            return
        if "properties" in node:
            yield node["properties"]
        for branch in node.get("allOf", []) or []:
            if isinstance(branch, dict) and "properties" in branch:
                yield branch["properties"]

    def is_array(self, onto, cls, member):
        for c in onto.mro(cls):
            if (c, member) in self.arrays:
                return True
        return False

    def json_type(self, onto, cls, member):
        for c in onto.mro(cls):
            hit = self.scalar_type.get((c, member))
            if hit:
                return hit
        return "string"


# ---------------------------------------------------------------------------
# Terms
# ---------------------------------------------------------------------------
_IRI_OK = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:[^\s<>\"{}|\\^`]*$")


def is_absolute_iri(value: str) -> bool:
    """An absolute IRI with at most one '#'.

    RFC 3986 forbids '#' inside a fragment, so an IRDI such as
    `0173-1#02-AAO677#002` is not one, however inviting it looks.
    """
    return bool(_IRI_OK.match(value)) and value.count("#") <= 1


def skolem(identifier: str) -> str:
    """A deterministic IRI for an `id` that is not a legal IRI (defect D4).

    The construction is one way and collision resistant: the full identifier is
    hashed, so two different identifiers cannot share a subject, and the same
    identifier always yields the same subject. The identifier itself is never
    recovered from the IRI - it is recovered by reading `aas:Identifiable/id`,
    which this lifting always emits.
    """
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
    return f"{LD}id/{digest}"


class Sink:
    """Collects triples, and quads for the enrichment graph."""

    def __init__(self):
        self.triples = []
        self.quads = []
        self._bnode = 0

    def fresh(self):
        self._bnode += 1
        return f"_:b{self._bnode}"

    def add(self, s, p, o, graph=None):
        (self.quads if graph else self.triples).append((s, p, o, graph))


def iri(value):
    return f"<{value}>"


def literal(value, datatype=None, language=None):
    esc = (value.replace("\\", "\\\\").replace('"', '\\"')
                .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"))
    if language:
        return f'"{esc}"@{language}'
    return f'"{esc}"^^<{datatype or XS + "string"}>'


# ---------------------------------------------------------------------------
# Lifting
# ---------------------------------------------------------------------------
class Lifter:
    def __init__(self, onto: Ontology, base: str, profile: str = "core",
                 emit_root_idshort: bool = True, schema: "Schema | None" = None):
        self.onto = onto
        self.schema = schema or Schema()
        self.base = base
        self.profile = profile
        # Upstream drops this (defect D1). The lifting emits it; the conformance
        # runner can suppress it to compare against the upstream corpus.
        self.emit_root_idshort = emit_root_idshort
        self.sink = Sink()

    # -- subject terms ------------------------------------------------------
    def subject_for(self, identifier: str) -> str:
        if is_absolute_iri(identifier):
            return iri(identifier)
        if _IRI_OK.match(identifier) or "#" in identifier or " " in identifier:
            return iri(skolem(identifier))
        # A relative reference: resolve against the required base (defect D3).
        return iri(urllib.parse.urljoin(self.base, urllib.parse.quote(identifier, safe="/:@")))

    # -- values -------------------------------------------------------------
    def enum_member(self, enum_name: str, value: str) -> str:
        members = self.onto.enums.get(enum_name, [])
        if value in members:
            return iri(f"{AAS}{enum_name}/{value}")
        # DataTypeDefXsd is written `xs:int` in JSON and `Int` in RDF.
        bare = value.split(":", 1)[-1]
        for candidate in (bare, bare[:1].upper() + bare[1:]):
            if candidate in members:
                return iri(f"{AAS}{enum_name}/{candidate}")
        lowered = {m.lower(): m for m in members}
        if bare.lower() in lowered:
            return iri(f"{AAS}{enum_name}/{lowered[bare.lower()]}")
        raise ValueError(f"{value!r} is not a member of {enum_name}")

    def datatype_literal(self, value, range_name):
        if isinstance(value, bool):
            return literal("true" if value else "false", XS + "boolean")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return literal(str(value), XS + range_name.split(":")[-1])
        suffix = range_name.split(":")[-1] if range_name else "string"
        return literal(str(value), XS + suffix)

    # -- objects ------------------------------------------------------------
    def class_of(self, node, range_ref):
        if isinstance(node, dict) and "modelType" in node:
            return node["modelType"]
        if range_ref and range_ref.startswith("aas:"):
            return range_ref[4:]
        return None

    def lift_object(self, node, cls, subject=None, is_root=False):
        subject = subject or self.sink.fresh()
        self.sink.add(subject, iri(RDF_TYPE), iri(f"{AAS}{cls}"))
        for key, value in node.items():
            if key == "modelType":
                continue
            prop = self.onto.resolve(cls, key)
            if prop is None:
                raise ValueError(f"no property {key!r} on {cls} or its supertypes")
            if is_root and prop["iri"] == AAS + "Referable/idShort" and not self.emit_root_idshort:
                continue
            self.lift_value(subject, prop, value, cls, key)
        return subject

    def lift_value(self, subject, prop, value, cls, key):
        if isinstance(value, list):
            for index, item in enumerate(value):
                obj = self.lift_single(subject, prop, item)
                if self.profile == "linked":
                    # Order is carried by an index on a reified occurrence, not
                    # by rdf:List, so the published SHACL and ordinary SPARQL
                    # both keep working on the core graph.
                    occ = self.sink.fresh()
                    self.sink.add(occ, iri(RDF_TYPE), iri(LD + "Occurrence"), ORDER_GRAPH)
                    self.sink.add(occ, iri(LD + "subject"), subject, ORDER_GRAPH)
                    self.sink.add(occ, iri(LD + "property"), iri(prop["iri"]), ORDER_GRAPH)
                    self.sink.add(occ, iri(LD + "member"), obj, ORDER_GRAPH)
                    self.sink.add(occ, iri(LD + "index"),
                                  literal(str(index), XS + "nonNegativeInteger"), ORDER_GRAPH)
            return
        self.lift_single(subject, prop, value)

    def lift_single(self, subject, prop, value):
        rng = prop["range"] or ""
        if prop["kind"] == "DatatypeProperty":
            obj = self.datatype_literal(value, rng)
            self.sink.add(subject, iri(prop["iri"]), obj)
            return obj
        name = rng[4:] if rng.startswith("aas:") else None
        if name and name in self.onto.enums:
            obj = self.enum_member(name, value)
            self.sink.add(subject, iri(prop["iri"]), obj)
            return obj
        cls = self.class_of(value, rng)
        if cls is None:
            raise ValueError(f"cannot type the object of {prop['iri']}")
        child = self.lift_object(value, cls)
        self.sink.add(subject, iri(prop["iri"]), child)
        return child

    # -- entry point --------------------------------------------------------
    def lift(self, doc):
        for collection, default_cls in ROOT_COLLECTIONS.items():
            for node in doc.get(collection, []) or []:
                cls = node.get("modelType", default_cls)
                identifier = node.get("id")
                if identifier is None:
                    raise ValueError(f"{cls} at the root has no id")
                self.lift_object(node, cls, self.subject_for(identifier), is_root=True)
        return self.sink


def serialize(sink, with_graphs=True):
    lines = [f"{s} {p} {o} ." for s, p, o, _ in sink.triples]
    if with_graphs:
        lines += [f"{s} {p} {o} <{g}> ." for s, p, o, g in sink.quads]
    return "\n".join(sorted(lines)) + ("\n" if lines else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--base", default="https://example.org/aas/")
    ap.add_argument("--profile", choices=("core", "linked"), default="core")
    ap.add_argument("--no-root-idshort", action="store_true",
                    help="suppress the root idShort, to compare against the upstream corpus (D1)")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        doc = json.load(f)
    lifter = Lifter(Ontology(), args.base, args.profile,
                    emit_root_idshort=not args.no_root_idshort)
    sys.stdout.write(serialize(lifter.lift(doc)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
