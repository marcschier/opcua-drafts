#!/usr/bin/env python3
"""
Build the DPP and battery passport identifier mapping dataset.

The inventory settled what the templates actually contain, and it is not what
the plan assumed: SAMM URNs are the largest scheme at 52.6% of distinct
identifiers, ECLASS is a quarter, IEC CDD is under 3%. It also showed that
64.9% of identifiers are already legal IRIs and need no mapping at all - a URN
is an IRI whether or not it dereferences.

So the dataset is small on purpose. It records one row per identifier that
cannot be used as an RDF IRI as written, and for each row it carries what a
mapping record needs to be trustworthy: the scheme, the construction applied,
whether the result dereferences, what the identifier denotes, and where it was
found. Nothing is asserted about equivalence to a term in another vocabulary,
because an AAS semanticId key is a `GlobalReference` in 1504 of 1588 cases and
denotes a concept rather than an RDF property; `owl:equivalentProperty` would be
a category error.

Output is SSSOM-shaped TSV, which is a published convention for mapping sets and
carries provenance columns as a matter of course.

Usage:
    python dpp_map.py            # write mappings.sssom.tsv
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "jsonld"))
sys.path.insert(0, HERE)

from dpp_inventory import (CACHE, FAMILIES, REF, REPO, is_legal_iri,  # noqa: E402
                           scheme_of, walk)

OUT = os.path.normpath(os.path.join(HERE, "..", "..", "dpp", "mappings.sssom.tsv"))
LD = "https://w3id.org/aas-dpp/"

# ECLASS publishes this construction in "ECLASS Serialization as RDF, Part 1"
# v1.0.0 (April 2024). It is the only IRDI scheme in these templates with a
# published canonical IRI form.
ECLASS_BASE = "https://rdf.eclass.eu/resource/"


def construct(value):
    """The IRI for an identifier, and how it was arrived at."""
    if is_legal_iri(value):
        return value, "identity", "yes" if value.startswith("http") else "no"
    scheme = scheme_of(value)
    if scheme == "ECLASS IRDI":
        return ECLASS_BASE + value.replace("#", "_"), "eclass-rdf-part1", "yes"
    # No published canonical form. A stable, collision-resistant IRI is minted so
    # the identifier can be a subject at all; it is explicitly not dereferenceable
    # and the original is always retained alongside.
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"{LD}id/{digest}", "aas-dpp-hash", "no"


def collect():
    index = os.path.join(CACHE, "index.json")
    if not os.path.exists(index):
        raise SystemExit("no template cache; run dpp_inventory.py first")
    with open(index, encoding="utf-8") as f:
        paths = json.load(f)
    rows = {}
    for path in paths:
        dest = os.path.join(CACHE, path.replace("/", "__"))
        if not os.path.exists(dest):
            continue
        try:
            with open(dest, encoding="utf-8") as f:
                doc = json.load(f)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        family = next((fam for fam in FAMILIES if fam in path), "?")
        for entry in walk(doc, []):
            value = entry["value"]
            if not value:
                continue
            row = rows.setdefault(value, {
                "value": value,
                "scheme": scheme_of(value),
                "members": set(),
                "keyTypes": set(),
                "carriedBy": set(),
                "families": set(),
            })
            row["members"].add(entry["member"])
            row["keyTypes"].add(entry["keyType"])
            row["carriedBy"].add(entry["denotedBy"])
            row["families"].add(family)
    return rows


COLUMNS = [
    "subject_id", "subject_label", "predicate_id", "object_id",
    "mapping_justification", "subject_source", "subject_source_version",
    "object_source", "mapping_tool", "confidence",
    "subject_type", "comment",
]


def predicate_for(row):
    """The mapping predicate, chosen by what the identifier denotes.

    An AAS semanticId key is a GlobalReference in almost every case: it names a
    concept in an external dictionary, not an RDF property. SKOS is the vocabulary
    for relating concepts, and the relation asserted is the weakest one that is
    defensible - the two identifiers are two names for one concept, which is what
    the construction guarantees, and nothing about the concept's definition.
    """
    if row["keyTypes"] <= {"GlobalReference"}:
        return "skos:exactMatch"
    return "skos:closeMatch"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="include identifiers that need no construction")
    args = ap.parse_args()

    rows = collect()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)

    written, skipped = 0, 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# mapping_set_id: {LD}mappings\n")
        f.write(f"# license: https://creativecommons.org/licenses/by/4.0/\n")
        f.write(f"# subject_source: {REPO}@{REF}\n")
        f.write("# comment: identifiers that cannot be used as an RDF IRI as written,\n")
        f.write("#   and the construction that gives each one. Identifiers that are\n")
        f.write("#   already legal IRIs are used unchanged and are not listed.\n")
        f.write("\t".join(COLUMNS) + "\n")
        for value in sorted(rows):
            row = rows[value]
            if is_legal_iri(value) and not args.all:
                skipped += 1
                continue
            iri, justification, dereferences = construct(value)
            f.write("\t".join([
                value,
                "|".join(sorted(row["carriedBy"])) or "",
                predicate_for(row),
                iri,
                justification,
                REPO,
                REF,
                row["scheme"],
                "dpp_map.py",
                "1.0" if justification in ("identity", "eclass-rdf-part1") else "0.5",
                "|".join(sorted(row["keyTypes"])),
                f"members={'|'.join(sorted(row['members']))}; dereferences={dereferences}",
            ]) + "\n")
            written += 1

    print(f"wrote {os.path.relpath(OUT, ROOT)}")
    print(f"  identifiers needing a construction : {written}")
    print(f"  identifiers usable as written      : {skipped}")
    by_just = Counter()
    by_deref = Counter()
    for value in rows:
        if is_legal_iri(value):
            continue
        _, j, d = construct(value)
        by_just[j] += 1
        by_deref[d] += 1
    print("\n  by construction:")
    for name, n in by_just.most_common():
        print(f"    {n:5d}  {name}")
    print("\n  dereferenceable after construction:")
    for name, n in by_deref.most_common():
        print(f"    {n:5d}  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
