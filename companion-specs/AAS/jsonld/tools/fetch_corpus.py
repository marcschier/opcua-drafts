#!/usr/bin/env python3
"""
Fetch the pinned upstream AAS example corpus and report where its JSON and RDF
halves disagree.

The upstream repository publishes, for each metamodel class, a set of generated
examples in both serializations:

    schemas/json/examples/generated/<Class>/<case>.json
    schemas/rdf/examples/generated/<Class>/<case>.ttl

A matched pair is the closest thing to a conformance oracle for a JSON-to-RDF
lifting: the JSON is the input and the Turtle is the expected output. That only
holds if both halves describe the same instance, and they do not always. This
tool downloads the pair set at a pinned ref and reports the disagreements, so
that the specification can state which cases are usable as an oracle and which
are upstream defects.

The corpus is large (~2400 pairs) and is therefore not vendored. It is cached
under `.corpus/` beside this tool, which is ignored by git. The small subset in
`fixtures/` is vendored so the conformance runner works offline.

Usage:
    python companion-specs/AAS/jsonld/tools/fetch_corpus.py            # fetch + report
    python companion-specs/AAS/jsonld/tools/fetch_corpus.py --report   # report only
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, ".corpus")

# The pinned upstream release. Every artefact this specification is checked
# against comes from this ref; nothing is read from a moving branch.
REPO = "admin-shell-io/aas-specs-metamodel"
REF = "V3.0.7"
COMMIT = "21e68502e367b72fd82cfa29488a686cbd3892a5"
RAW = f"https://raw.githubusercontent.com/{REPO}/{REF}"
TREE = f"https://api.github.com/repos/{REPO}/git/trees/{COMMIT}?recursive=1"

JSON_ROOT = "schemas/json/examples/generated"
RDF_ROOT = "schemas/rdf/examples/generated"


def _get(url: str, attempts: int = 5) -> bytes:
    """Fetch with backoff.

    raw.githubusercontent.com resets the connection under a burst of several
    hundred small requests, so a corpus fetch that does not retry fails part way
    through and leaves a half-populated cache.
    """
    last = None
    for attempt in range(attempts):
        req = urllib.request.Request(url, headers={"User-Agent": "aas-jsonld-corpus"})
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token and "api.github.com" in url:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - any transport failure is retryable
            last = exc
            time.sleep(min(2 ** attempt, 16) * 0.5)
    raise RuntimeError(f"giving up on {url}: {last}")


def list_pairs():
    """Every case for which both a .json and a .ttl exist, keyed by Class/case."""
    tree = json.loads(_get(TREE))["tree"]
    jsons, ttls = {}, {}
    for entry in tree:
        if entry["type"] != "blob":
            continue
        p = entry["path"]
        if p.startswith(JSON_ROOT) and p.endswith(".json"):
            jsons[p[len(JSON_ROOT) + 1:-5]] = p
        elif p.startswith(RDF_ROOT) and p.endswith(".ttl"):
            ttls[p[len(RDF_ROOT) + 1:-4]] = p
    both = sorted(set(jsons) & set(ttls))
    return both, jsons, ttls


def fetch(cases, jsons, ttls):
    os.makedirs(CACHE, exist_ok=True)
    manifest = {"repo": REPO, "ref": REF, "commit": COMMIT, "cases": {}}
    for i, case in enumerate(cases, 1):
        for kind, table, ext in (("json", jsons, ".json"), ("ttl", ttls, ".ttl")):
            dest = os.path.join(CACHE, kind, case.replace("/", os.sep) + ext)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if not os.path.exists(dest):
                with open(dest, "wb") as f:
                    f.write(_get(f"{RAW}/{urllib.parse.quote(table[case])}"))
        manifest["cases"][case] = {"json": jsons[case], "ttl": ttls[case]}
        if i % 100 == 0:
            print(f"  {i}/{len(cases)}", file=sys.stderr)
    with open(os.path.join(CACHE, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    return manifest


# ---------------------------------------------------------------------------
# Pair agreement
# ---------------------------------------------------------------------------
# A full comparison needs the lifting itself. What this tool checks is weaker and
# deliberately so: every *leaf string value* present in the JSON should appear
# somewhere in the Turtle, and vice versa. That is enough to detect the case the
# specification cares about - the two halves describing different instances -
# without presupposing the mapping the specification is about to define.
_TTL_LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"')


def json_leaves(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "modelType":
                continue
            json_leaves(v, out)
    elif isinstance(node, list):
        for v in node:
            json_leaves(v, out)
    elif isinstance(node, str):
        out.add(node)
    elif isinstance(node, bool):
        out.add("true" if node else "false")
    elif node is not None:
        out.add(str(node))
    return out


def ttl_literals(text):
    return {m.group(1) for m in _TTL_LITERAL.finditer(text)}


def report(manifest):
    rows, unreadable = [], []
    for case in sorted(manifest["cases"]):
        jp = os.path.join(CACHE, "json", case.replace("/", os.sep) + ".json")
        tp = os.path.join(CACHE, "ttl", case.replace("/", os.sep) + ".ttl")
        if not (os.path.exists(jp) and os.path.exists(tp)):
            continue
        try:
            with open(jp, encoding="utf-8") as f:
                doc = json.load(f)
            with open(tp, encoding="utf-8") as f:
                ttl = f.read()
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            unreadable.append((case, str(exc)[:80]))
            continue
        jvals = json_leaves(doc, set())
        tvals = ttl_literals(ttl)
        # Enumeration values become named individuals rather than literals, and
        # are therefore expected to be missing from the literal set.
        missing = {v for v in jvals - tvals
                   if v and f"/{v}>" not in ttl and f"/{v[0].upper()}{v[1:]}>" not in ttl}
        extra = tvals - jvals
        if missing or extra:
            rows.append((case, sorted(missing), sorted(extra)))
    return rows, unreadable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="report only; do not download")
    ap.add_argument("--limit", type=int, default=0, help="fetch at most N pairs")
    args = ap.parse_args()

    mpath = os.path.join(CACHE, "manifest.json")
    if args.report:
        if not os.path.exists(mpath):
            print("no cached corpus; run without --report first", file=sys.stderr)
            return 1
        with open(mpath, encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        print(f"listing {REPO}@{REF} ...", file=sys.stderr)
        cases, jsons, ttls = list_pairs()
        if args.limit:
            cases = cases[: args.limit]
        print(f"{len(cases)} matched pairs; fetching into {CACHE}", file=sys.stderr)
        manifest = fetch(cases, jsons, ttls)

    rows, unreadable = report(manifest)
    total = len(manifest["cases"])
    print(f"\npinned: {REPO}@{REF} ({COMMIT[:12]})")
    print(f"matched pairs: {total}")
    print(f"unreadable cached files: {len(unreadable)}")
    for case, why in unreadable[:10]:
        print(f"    {case}: {why}")
    print(f"pairs whose halves disagree: {len(rows)}")
    by_class = {}
    for case, missing, extra in rows:
        by_class.setdefault(case.split("/")[0], 0)
        by_class[case.split("/")[0]] += 1
    print("\ndisagreements by class:")
    for cls, n in sorted(by_class.items(), key=lambda kv: -kv[1])[:20]:
        print(f"    {n:5d}  {cls}")
    for case, missing, extra in rows[:15]:
        print(f"\n  {case}")
        if missing:
            print(f"    in JSON, absent from RDF: {missing[:6]}")
        if extra:
            print(f"    in RDF, absent from JSON: {extra[:6]}")
    if len(rows) > 15:
        print(f"\n  ... and {len(rows) - 15} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
