#!/usr/bin/env python3
"""Check each manifest's identity and dependency closure against its model.

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

Every `RequiredModel` is checked against the NodeSet for that model when it is present under
`model/` or `model/dependencies/`. Its own prerequisites shall also be declared by the top-level
model, and shall occur earlier in the list: the NodeSet loader processes the declarations in
order. This is what distinguishes a complete closure

    UA, DI, IA, Machinery

from `UA, DI, Machinery`, which loads Machinery before the IA types it borrows are available.

Usage (from repo root):  python .github/scripts/check_manifest_model.py
Exit code is non-zero if any manifest disagrees with its model.
"""

import json
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_NAMESPACE = "http://opcfoundation.org/UA/"
UANS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"


def manifests():
    source = os.path.join(ROOT, "source")
    for dirpath, _dirnames, filenames in os.walk(source):
        if "manifest.json" in filenames:
            yield os.path.join(dirpath, "manifest.json")


def model_definitions(path):
    """Return every Model in one NodeSet and its ordered RequiredModel declarations."""
    root = ET.parse(path).getroot()
    definitions = []
    for model in root.findall("%sModels/%sModel" % (UANS, UANS)):
        required = [
            {
                "uri": item.get("ModelUri"),
                "version": item.get("Version"),
                "publicationDate": (item.get("PublicationDate") or "")[:10],
            }
            for item in model.findall("%sRequiredModel" % UANS)
        ]
        definitions.append({
            "uri": model.get("ModelUri"),
            "version": model.get("Version"),
            "publicationDate": (model.get("PublicationDate") or "")[:10],
            "required": required,
        })
    return definitions


def available_models():
    """Map ModelUri to the local NodeSet that defines it."""
    available = {}
    model_dir = os.path.join(ROOT, "model")
    for directory in (model_dir, os.path.join(model_dir, "dependencies")):
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if not name.lower().endswith(".xml"):
                continue
            path = os.path.join(directory, name)
            try:
                definitions = model_definitions(path)
            except (OSError, ET.ParseError):
                continue
            for definition in definitions:
                uri = definition.get("uri")
                if uri:
                    available[uri] = (path, definition)
    return available


def check_dependency_closure(rel, nodeset, top, available, problems):
    """Require each dependency's own prerequisites before it in the top model's list."""
    required = top["required"]
    position = {item["uri"]: index for index, item in enumerate(required)}
    for index, item in enumerate(required):
        dependency = available.get(item["uri"])
        if not dependency:
            continue
        dependency_path, definition = dependency
        for prerequisite in definition["required"]:
            uri = prerequisite["uri"]
            if not uri or uri == top["uri"]:
                continue
            prerequisite_index = position.get(uri)
            if prerequisite_index is None:
                problems.append(
                    "%s: %s requires %s, but %s does not declare that transitive dependency"
                    % (
                        rel,
                        os.path.basename(dependency_path),
                        uri,
                        os.path.basename(nodeset),
                    )
                )
            elif prerequisite_index >= index:
                problems.append(
                    "%s: %s requires %s, which must occur before it in %s (positions %d and %d)"
                    % (
                        rel,
                        os.path.basename(dependency_path),
                        uri,
                        os.path.basename(nodeset),
                        prerequisite_index + 1,
                        index + 1,
                    )
                )


def main():
    problems = []
    checked = 0
    available = available_models()
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
        definitions = model_definitions(nodeset)
        if not definitions:
            problems.append("%s: %s declares no <Model>" % (rel, model["nodeset"]))
            continue
        top = definitions[0]
        checked += 1
        uri = top["uri"]
        version = top["version"]
        published = top["publicationDate"]

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
        check_dependency_closure(rel, nodeset, top, available, problems)

    if problems:
        print("check_manifest_model: %d problem(s) across %d model(s)"
              % (len(problems), checked))
        for p in problems:
            print("  %s" % p)
        return 1
    print("check_manifest_model: OK (%d model(s) agree with their manifest)" % checked)
    return 0


if __name__ == "__main__":
    sys.exit(main())
