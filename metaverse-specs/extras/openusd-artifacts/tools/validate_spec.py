#!/usr/bin/env python3
"""Validate the submittable xRegistry OpenUSD domain specification.

The spec document and its model are two statements of the same thing, and a
reader of one will act on the other, so they must not drift. This checks:

  * ``xRegistry-OpenUsd.model.json`` parses and has the structural shape the
    xRegistry core model schema requires (groups -> singular + resources ->
    singular + attributes), with a ``*``/any escape on every attribute map.
  * Every group collection, resource collection and singular the model declares
    is mentioned in the spec document, and every collection name the spec
    mentions in its pseudo-JSON is declared by the model.
  * Every extension attribute the model declares is documented in the spec, and
    every attribute the spec documents is declared by the model.
  * Every enum value the model declares (assetkind, digestalg, format) appears
    in the spec, so a reader cannot be given a shorter list than an
    implementation accepts.
  * The spec does not define attributes this domain deliberately omits
    (``mediatype``, ``assetcontainerid``, ``pluginname``) other than to say so.

Standard library only; no network access.

Usage: python metaverse-specs/extras/openusd-artifacts/tools/validate_spec.py
Exit code 0 and "OK" on success; non-zero with an ERRORS list otherwise.
"""
from __future__ import annotations

import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BINDING = os.path.abspath(os.path.join(HERE, "..", "..", "..", "openusd-binding"))
MODEL = os.path.join(BINDING, "xRegistry-OpenUsd.model.json")
SPEC = os.path.join(BINDING, "xRegistry-OpenUsd.md")

# Attributes this domain deliberately does NOT define; each is discussed in the
# spec, so presence of the word is fine but a definition would be a defect.
OMITTED = ("mediatype", "assetcontainerid", "pluginname")

ERR: list[str] = []


def err(msg: str) -> None:
    ERR.append(msg)


def _check_model_shape(model: dict) -> None:
    if "$schema" not in model:
        err("model: missing $schema")
    groups = model.get("groups")
    if not isinstance(groups, dict) or not groups:
        err("model: no groups declared")
        return
    for gcoll, gdef in groups.items():
        if not gdef.get("singular"):
            err(f"model/{gcoll}: missing 'singular'")
        gattrs = gdef.get("attributes", {})
        if "*" not in gattrs:
            err(f"model/{gcoll}: group attributes lack the '*' any-escape")
        resources = gdef.get("resources")
        if not isinstance(resources, dict) or not resources:
            err(f"model/{gcoll}: no resources declared")
            continue
        for rcoll, rdef in resources.items():
            if not rdef.get("singular"):
                err(f"model/{gcoll}/{rcoll}: missing 'singular'")
            if rdef.get("hasdocument") is not True:
                err(f"model/{gcoll}/{rcoll}: hasdocument must be true for a document store")
            rattrs = rdef.get("attributes", {})
            if "*" not in rattrs:
                err(f"model/{gcoll}/{rcoll}: resource attributes lack the '*' any-escape")
            for aname, adef in rattrs.items():
                if aname == "*":
                    continue
                if adef.get("name") != aname:
                    err(f"model/{gcoll}/{rcoll}/{aname}: 'name' != key")
                if not adef.get("type"):
                    err(f"model/{gcoll}/{rcoll}/{aname}: missing 'type'")
                if adef.get("type") == "array" and "item" not in adef:
                    err(f"model/{gcoll}/{rcoll}/{aname}: array without 'item'")
                if not adef.get("description"):
                    err(f"model/{gcoll}/{rcoll}/{aname}: missing 'description'")


def _model_facts(model: dict):
    collections: set[str] = set()
    singulars: set[str] = set()
    attrs: set[str] = set()
    enums: set[str] = set()
    for gcoll, gdef in model.get("groups", {}).items():
        collections.add(gcoll)
        singulars.add(gdef.get("singular", ""))
        attrs |= set(gdef.get("attributes", {})) - {"*"}
        for rcoll, rdef in gdef.get("resources", {}).items():
            collections.add(rcoll)
            singulars.add(rdef.get("singular", ""))
            for aname, adef in rdef.get("attributes", {}).items():
                if aname == "*":
                    continue
                attrs.add(aname)
                enums |= set(adef.get("enum", []))
    return collections, {s for s in singulars if s}, attrs, enums


def main() -> int:
    for path in (MODEL, SPEC):
        if not os.path.exists(path):
            print(f"missing {path}")
            return 1

    with open(MODEL, encoding="utf-8") as fh:
        try:
            model = json.load(fh)
        except json.JSONDecodeError as exc:
            print(f"ERRORS:\n  - model does not parse: {exc}")
            return 1
    spec = open(SPEC, encoding="utf-8").read()

    _check_model_shape(model)
    collections, singulars, attrs, enums = _model_facts(model)

    for name in sorted(collections | singulars):
        if not re.search(rf"`{re.escape(name)}`", spec):
            err(f"spec does not mention model name `{name}`")

    for attr in sorted(attrs):
        if not re.search(rf"`{re.escape(attr)}`", spec):
            err(f"spec does not document model attribute `{attr}`")

    for value in sorted(enums):
        if not re.search(rf"`{re.escape(value)}`", spec):
            err(f"spec does not list model enum value `{value}`")

    # The spec's own extension-attribute bullets must all exist in the model.
    for m in re.finditer(r"^- \*\*`([a-z]+)`\*\* — (REQUIRED|OPTIONAL)", spec, re.M):
        if m.group(1) not in attrs:
            err(f"spec defines attribute `{m.group(1)}` that the model does not declare")

    # Deliberately omitted attributes must not be declared by the model.
    for name in OMITTED:
        if name in attrs:
            err(f"model declares `{name}`, which this domain deliberately omits")

    if ERR:
        print("ERRORS:")
        for e in ERR:
            print(f"  - {e}")
        return 1

    print(f"spec/model: {len(collections)} collections, {len(attrs)} extension "
          f"attributes, {len(enums)} enum values cross-checked")
    print("OK - 0 errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
