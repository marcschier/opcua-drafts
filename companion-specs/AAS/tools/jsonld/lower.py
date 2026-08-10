#!/usr/bin/env python3
"""
Lower an RDF graph produced by `lift.py` back into AAS JSON.

This exists to make the second conformance claim testable. `AASLD-RdfCompatible`
says the lifted graph agrees with the normative RDF; it says nothing about
whether the source document survives. `AASLD-JsonRoundTrip` is the stronger
claim, and lowering is what tests it.

The two claims come apart, and that is the point. The normative RDF discards the
order of `Reference/keys` and of an ordered `SubmodelElementList` (defect D2), so
a lowering that reads only the core graph cannot restore a multi-key reference
path. Given the ordering graph the enrichment profile emits, it can. Running the
round trip with and without that graph is therefore a measurement of what the
upstream serialization loses, rather than an assertion about it.

Like `lift.py`, the tables are read from pinned artefacts: the ontology supplies
the class hierarchy and property ranges, the JSON Schema supplies which classes
carry a `modelType` discriminator, which members are arrays, and the JSON
spelling of each enumeration value.

Usage:
    python lower.py <graph.nt> [--order <order.nt>]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lift import AAS, LD, Ontology, Schema, ROOT_COLLECTIONS  # noqa: E402

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


# ---------------------------------------------------------------------------
# N-Triples
# ---------------------------------------------------------------------------
_TRIPLE = re.compile(
    r'^\s*(?P<s><[^>]*>|_:\S+)\s+(?P<p><[^>]*>)\s+(?P<o>'
    r'<[^>]*>|_:\S+|"(?:[^"\\]|\\.)*"(?:\^\^<[^>]*>|@[\w-]+)?)\s*\.\s*$')


def parse_nt(text):
    out = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = _TRIPLE.match(line)
        if not m:
            raise ValueError(f"cannot parse: {line[:120]}")
        out.append((m.group("s"), m.group("p"), m.group("o")))
    return out


def unquote_iri(term):
    return term[1:-1] if term.startswith("<") else term


def literal_value(term):
    m = re.match(r'^"((?:[^"\\]|\\.)*)"', term)
    return unescape(m.group(1))


ESCAPES = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f",
           '"': '"', "'": "'", "\\": "\\"}


def unescape(raw):
    """Decode an N-Triples literal in one left-to-right pass.

    Sequential `str.replace` calls cannot do this. `\\\\n` in the serialization is
    an escaped backslash followed by the letter n, and replacing `\\n` first
    consumes the second half of the backslash escape, turning a backslash and an
    n into a newline. No example in the corpus contains one; the published
    submodel templates do.

    Malformed input is passed through rather than raised on. A truncated or
    non-hexadecimal `\\u` escape is a defect in whatever produced the text, and a
    lowering that stops with a `ValueError` from `int()` reports it as a crash in
    the reader; keeping the characters lets the caller see what it was given.
    """
    out = []
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch != "\\" or i + 1 >= len(raw):
            out.append(ch)
            i += 1
            continue
        nxt = raw[i + 1]
        if nxt in ESCAPES:
            out.append(ESCAPES[nxt])
            i += 2
        elif nxt in ("u", "U"):
            width = 4 if nxt == "u" else 8
            digits = raw[i + 2:i + 2 + width]
            try:
                if len(digits) != width:
                    raise ValueError("truncated")
                out.append(chr(int(digits, 16)))
            except (ValueError, OverflowError):
                out.append(ch)
                i += 1
                continue
            i += 2 + width
        else:
            out.append(nxt)
            i += 2
    return "".join(out)


def is_literal(term):
    return term.startswith('"')


# ---------------------------------------------------------------------------
# Lowering
# ---------------------------------------------------------------------------
class Lowerer:
    def __init__(self, onto: Ontology, schema: Schema):
        self.onto = onto
        self.schema = schema
        self.enum_from_individual = {}
        for enum, members in onto.enums.items():
            spellings = schema.enum_json.get(enum, [])
            table = {}
            for spelling in spellings:
                bare = spelling.split(":", 1)[-1]
                joined = "".join(part.capitalize() for part in bare.split("_"))
                for member in members:
                    if member.lower() in (bare.lower(), joined.lower()):
                        table[member] = spelling
            for member in members:
                table.setdefault(member, member)
            self.enum_from_individual[enum] = table

    def load(self, triples, order_triples=()):
        self.by_subject = defaultdict(lambda: defaultdict(list))
        for s, p, o in triples:
            self.by_subject[s][unquote_iri(p)].append(o)
        # index -> position, keyed by (subject, property, member)
        self.order = {}
        occurrences = defaultdict(dict)
        for s, p, o in order_triples:
            occurrences[s][unquote_iri(p)] = o
        for occ in occurrences.values():
            try:
                key = (occ[LD + "subject"], unquote_iri(occ[LD + "property"]), occ[LD + "member"])
                self.order[key] = int(literal_value(occ[LD + "index"]))
            except KeyError:
                continue

    def class_of(self, subject):
        types = self.by_subject[subject].get(RDF_TYPE, [])
        for t in types:
            name = unquote_iri(t)
            if name.startswith(AAS):
                return name[len(AAS):]
        return None

    def member_name(self, prop_iri):
        return prop_iri.rsplit("/", 1)[-1]

    def scalar(self, cls, member, term):
        raw = literal_value(term)
        kind = self.schema.json_type(self.onto, cls, member)
        if kind == "boolean":
            return raw == "true"
        if kind in ("integer", "number"):
            try:
                return int(raw) if kind == "integer" else float(raw)
            except ValueError:
                return raw
        return raw

    def build(self, subject, cls=None):
        cls = cls or self.class_of(subject)
        if cls is None:
            raise ValueError(f"no rdf:type for {subject}")
        node = {}
        for prop_iri, objects in self.by_subject[subject].items():
            if prop_iri == RDF_TYPE:
                continue
            member = self.member_name(prop_iri)
            prop = self.onto.resolve(cls, member)
            if prop is None:
                raise ValueError(f"no property {member!r} on {cls}")
            values = self.values_for(cls, member, prop, subject, prop_iri, objects)
            node[member] = values
        if cls in self.schema.model_type:
            node["modelType"] = cls
        return node

    def values_for(self, cls, member, prop, subject, prop_iri, objects):
        ordered = sorted(
            objects,
            key=lambda o: self.order.get((subject, prop_iri, o), 1 << 30))
        out = [self.one(cls, member, prop, o) for o in ordered]
        if self.schema.is_array(self.onto, cls, member):
            return out
        return out[0]

    def one(self, cls, member, prop, term):
        if is_literal(term):
            return self.scalar(cls, member, term)
        rng = prop["range"] or ""
        name = rng[4:] if rng.startswith("aas:") else None
        if name and name in self.onto.enums:
            individual = unquote_iri(term).rsplit("/", 1)[-1]
            return self.enum_from_individual.get(name, {}).get(individual, individual)
        return self.build(term)

    def lower(self):
        doc = {}
        for subject in list(self.by_subject):
            cls = self.class_of(subject)
            collection = next((c for c, k in ROOT_COLLECTIONS.items() if k == cls), None)
            if collection is None:
                continue
            if AAS + "Identifiable/id" not in self.by_subject[subject]:
                continue
            doc.setdefault(collection, []).append(self.build(subject, cls))
        for collection in doc:
            doc[collection].sort(key=lambda n: n.get("id", ""))
        return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("graph", help="the core graph, as N-Triples")
    ap.add_argument("--order", help="the ordering graph, as N-Triples")
    args = ap.parse_args()

    with open(args.graph, encoding="utf-8") as f:
        triples = parse_nt(f.read())
    order = ()
    if args.order:
        with open(args.order, encoding="utf-8") as f:
            order = parse_nt(f.read())

    low = Lowerer(Ontology(), Schema())
    low.load(triples, order)
    json.dump(low.lower(), sys.stdout, indent=2, sort_keys=True, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
