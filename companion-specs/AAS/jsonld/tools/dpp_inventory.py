#!/usr/bin/env python3
"""
Inventory the semantic identifiers actually used by the IDTA DPP and battery
passport submodel templates.

Artefact C started from the premise that those templates are predominantly
ECLASS-based, so binding an ECLASS IRDI to its published IRI would carry most of
the work. The design review disputed that. This settles it by reading the
published templates rather than a summary of them: the templates ship as AAS
JSON, so every `semanticId` and `supplementalSemanticId` can be counted.

What it reports, per template and overall:

  * how many semantic identifiers there are, and how many are distinct;
  * which scheme each belongs to - ECLASS IRDI, IEC CDD IRDI, a SAMM URN, an
    admin-shell.io IRI, or something else;
  * what each identifier denotes, since an identifier on a `ConceptDescription`
    is not a property and asserting `owl:equivalentProperty` for it would be a
    category error;
  * how many can be given a dereferenceable IRI today.

Usage:
    python dpp_inventory.py            # fetch and report
    python dpp_inventory.py --report   # report from the cache
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, ".templates")

REPO = "admin-shell-io/submodel-templates"
REF = "main"
RAW = f"https://raw.githubusercontent.com/{REPO}/{REF}"
TREE = f"https://api.github.com/repos/{REPO}/git/trees/{REF}?recursive=1"

# The template families this inventory covers.
FAMILIES = ("Digital Battery Passport", "Digital Product Passport")

# Identifier schemes, tested in order. The ECLASS and IEC CDD patterns are the
# IRDI forms of ISO/IEC 11179-6; the issuing organisation is the leading code.
SCHEMES = [
    ("ECLASS IRDI", re.compile(r"^0173-1#")),
    ("IEC CDD IRDI", re.compile(r"^0112/")),
    ("other IRDI", re.compile(r"^\d{4}[-/]")),
    ("SAMM URN", re.compile(r"^urn:samm:")),
    ("other URN", re.compile(r"^urn:")),
    ("admin-shell.io IRI", re.compile(r"^https?://admin-shell\.io/")),
    ("other IRI", re.compile(r"^https?://")),
]

# ECLASS publishes a canonical IRI for an IRDI; IEC CDD does not.
ECLASS_IRI = "https://rdf.eclass.eu/resource/"


def _get(url, attempts=5):
    last = None
    for attempt in range(attempts):
        req = urllib.request.Request(url, headers={"User-Agent": "aas-dpp-inventory"})
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token and "api.github.com" in url:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(min(2 ** attempt, 16) * 0.5)
    raise RuntimeError(f"giving up on {url}: {last}")


def template_paths():
    tree = json.loads(_get(TREE))["tree"]
    out = []
    for entry in tree:
        if entry["type"] != "blob":
            continue
        p = entry["path"]
        if not p.endswith(".json"):
            continue
        if not any(f in p for f in FAMILIES):
            continue
        # Prefer the variant without example values: it is the template itself.
        out.append(p)
    return sorted(out)


def fetch(paths):
    os.makedirs(CACHE, exist_ok=True)
    saved = []
    for p in paths:
        dest = os.path.join(CACHE, p.replace("/", "__"))
        if not os.path.exists(dest):
            with open(dest, "wb") as f:
                f.write(_get(f"{RAW}/{urllib.parse.quote(p)}"))
        saved.append((p, dest))
    return saved


def scheme_of(value):
    for name, pattern in SCHEMES:
        if pattern.match(value):
            return name
    return "unrecognised"


_IRI_OK = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:[^\s<>\"{}|\\^`]*$")


def is_legal_iri(value):
    """Whether the identifier can be used as an RDF IRI without construction.

    A URN is a legal IRI whether or not it dereferences, so `urn:samm:...` needs
    no mapping at all. An IRDI is not: `0173-1#02-AAO677#002` carries a second
    `#`, which RFC 3986 does not permit in a fragment.
    """
    return bool(_IRI_OK.match(value)) and value.count("#") <= 1


def walk(node, out, denotes=None):
    """Collect every Reference that acts as a semantic identifier."""
    if isinstance(node, dict):
        model_type = node.get("modelType")
        for key in ("semanticId", "supplementalSemanticIds", "valueId", "unitId"):
            value = node.get(key)
            if value is None:
                continue
            for ref in (value if isinstance(value, list) else [value]):
                if not isinstance(ref, dict):
                    continue
                for k in ref.get("keys", []) or []:
                    raw = k.get("value", "")
                    out.append({
                        # Some published templates carry an identifier with
                        # surrounding whitespace. It is reported separately and
                        # trimmed here, because an untrimmed value classifies as
                        # unrecognised and would be given a hash IRI when it has
                        # a perfectly good ECLASS one.
                        "value": raw.strip(),
                        "raw": raw,
                        "untrimmed": raw != raw.strip(),
                        "keyType": k.get("type", ""),
                        "refType": ref.get("type", ""),
                        "member": key,
                        "denotedBy": model_type or denotes or "",
                    })
        for k, v in node.items():
            walk(v, out, model_type or denotes)
    elif isinstance(node, list):
        for v in node:
            walk(v, out, denotes)
    return out


def report(saved):
    per_template = {}
    everything = []
    for path, dest in saved:
        try:
            with open(dest, encoding="utf-8") as f:
                doc = json.load(f)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        found = walk(doc, [])
        if not found:
            continue
        family = next((f for f in FAMILIES if f in path), "?")
        name = os.path.basename(path)
        per_template[(family, name)] = found
        everything += found
    return per_template, everything


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    index = os.path.join(CACHE, "index.json")
    if args.report and os.path.exists(index):
        with open(index, encoding="utf-8") as f:
            saved = [(p, os.path.join(CACHE, p.replace("/", "__"))) for p in json.load(f)]
    else:
        paths = template_paths()
        print(f"{len(paths)} template documents in {len(FAMILIES)} families", file=sys.stderr)
        saved = fetch(paths)
        os.makedirs(CACHE, exist_ok=True)
        with open(index, "w", encoding="utf-8") as f:
            json.dump([p for p, _ in saved], f, indent=2)

    per_template, everything = report(saved)

    print(f"repository: {REPO}@{REF}")
    print(f"documents with semantic identifiers: {len(per_template)}")
    print(f"semantic identifier occurrences: {len(everything)}")
    distinct = {e["value"] for e in everything}
    print(f"distinct identifiers: {len(distinct)}")

    print("\nby scheme (distinct identifiers):")
    schemes = Counter(scheme_of(v) for v in distinct)
    for name, n in schemes.most_common():
        share = 100.0 * n / max(len(distinct), 1)
        print(f"  {n:6d}  {share:5.1f}%  {name}")

    print("\nby what the identifier is attached to (occurrences):")
    for member, n in Counter(e["member"] for e in everything).most_common():
        print(f"  {n:6d}  {member}")

    print("\nby the class carrying it (occurrences):")
    for cls, n in Counter(e["denotedBy"] for e in everything).most_common(8):
        print(f"  {n:6d}  {cls or '(root)'}")

    resolvable = sum(1 for v in distinct if scheme_of(v) in
                     ("ECLASS IRDI", "admin-shell.io IRI", "other IRI"))
    print(f"\ndistinct identifiers with a dereferenceable IRI today: {resolvable} of {len(distinct)}"
          f"  ({100.0 * resolvable / max(len(distinct), 1):.1f}%)")
    print("  ECLASS IRDIs resolve through " + ECLASS_IRI)
    print("  IEC CDD IRDIs and SAMM URNs have no published dereferenceable form")

    # The figure that decides the design. A URN is a legal IRI whether or not it
    # dereferences, so it needs no construction and no minted term: it is already
    # usable as an RDF resource. Only an IRDI needs one.
    legal = sum(1 for v in distinct if is_legal_iri(v))
    needs_construction = sorted(v for v in distinct if not is_legal_iri(v))
    by_scheme = Counter(scheme_of(v) for v in needs_construction)
    print(f"\ndistinct identifiers already usable as an RDF IRI: {legal} of {len(distinct)}"
          f"  ({100.0 * legal / max(len(distinct), 1):.1f}%)")
    print(f"needing a construction: {len(needs_construction)}")
    for name, n in by_scheme.most_common():
        print(f"  {n:6d}  {name}")

    print("\nwhat the identifier denotes, by the member carrying it:")
    denotes = defaultdict(Counter)
    for e in everything:
        denotes[e["member"]][e["keyType"]] += 1
    for member in ("semanticId", "supplementalSemanticIds", "valueId", "unitId"):
        top = ", ".join(f"{k or '(none)'}={n}" for k, n in denotes[member].most_common(3))
        print(f"  {member:24s} {top}")

    untrimmed = {e["raw"] for e in everything if e.get("untrimmed")}
    if untrimmed:
        print(f"\nidentifiers carrying surrounding whitespace in the published template: "
              f"{len(untrimmed)}")
        for raw in sorted(untrimmed)[:5]:
            print(f"  {raw!r}")

    print("\nper template:")
    for (family, name), found in sorted(per_template.items()):
        vals = {e["value"] for e in found}
        top = Counter(scheme_of(v) for v in vals).most_common(2)
        summary = ", ".join(f"{n} {s}" for s, n in top)
        print(f"  {family[:26]:28s} {name[:52]:54s} {len(vals):4d} distinct  ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
