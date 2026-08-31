#!/usr/bin/env python3
"""Check each manifest's identity against the model it names.

`identity.namespaceUri` must match the `ModelUri` of the NodeSet under `model`, and
`identity.version` and `identity.publicationDate` must match that model's. The publisher
prints the manifest's values on the cover and states the model's in Annex A, so when the two
disagree one document says two different things about the same namespace.

The two are authored separately -- one by hand, one by a generator -- so nothing else notices
when they drift, and drift is what this catches: an Observability Export manifest naming
`.../Observability/` for a model that declares `.../ObservabilityExport/`, at a version and a
publication date the model had never had.

A specification that adds Nodes to the base OPC UA namespace rather than owning one is exempt
from the version and publication-date comparison: its model states the base namespace's
version, which is not the document's, and `identity.namespaceUri` is the base namespace by
design. It is still checked for the URI.

Usage (from repo root):  python .github/scripts/check_manifest_model.py
Exit code is non-zero if any manifest disagrees with its model.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_NAMESPACE = "http://opcfoundation.org/UA/"
MODEL_RE = re.compile(
    r'<Model ModelUri="([^"]+)"[^>]*?Version="([^"]+)" PublicationDate="([^"]+)"')


def manifests():
    source = os.path.join(ROOT, "source")
    for dirpath, _dirnames, filenames in os.walk(source):
        if "manifest.json" in filenames:
            yield os.path.join(dirpath, "manifest.json")


def main():
    problems = []
    checked = 0
    for path in sorted(manifests()):
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
        model = cfg.get("model")
        if not model:
            continue
        identity = cfg.get("identity", {})
        nodeset = os.path.join(ROOT, *model["nodeset"].split("/"))
        if not os.path.exists(nodeset):
            problems.append("%s: names a NodeSet that is not there: %s" % (rel, model["nodeset"]))
            continue
        with open(nodeset, encoding="utf-8") as f:
            head = f.read(8000)
        m = MODEL_RE.search(head)
        if not m:
            problems.append("%s: %s declares no <Model>" % (rel, model["nodeset"]))
            continue
        checked += 1
        uri, version, published = m.group(1), m.group(2), m.group(3)[:10]

        if identity.get("namespaceUri") != uri:
            problems.append("%s: identity.namespaceUri is %r but the model declares %r"
                            % (rel, identity.get("namespaceUri"), uri))
        # A subset of the base namespace states the base namespace's version, not its own.
        if uri == BASE_NAMESPACE:
            continue
        if identity.get("version") != version:
            problems.append("%s: identity.version is %r but the model declares %r"
                            % (rel, identity.get("version"), version))
        if identity.get("publicationDate") != published:
            problems.append("%s: identity.publicationDate is %r but the model declares %r"
                            % (rel, identity.get("publicationDate"), published))

    if problems:
        print("check_manifest_model: %d disagreement(s) across %d model(s)"
              % (len(problems), checked))
        for p in problems:
            print("  %s" % p)
        return 1
    print("check_manifest_model: OK (%d model(s) agree with their manifest)" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
