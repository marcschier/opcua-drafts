#!/usr/bin/env python3
"""Validate the generated OpenUSD artifact-registry document.

Structural + normative checks against ``examples/openusd-artifacts.xregistry.json``:

  * required top-level / group / resource attributes and id<->key agreement;
  * every artifact ``xid`` equals its ``openusd.assetidentifier`` label (§5.15.3);
  * xids are globally unique and structurally ``/<coll>/<group>/usdassets/<id>``;
  * every ``openusd.dependson`` entry resolves to an artifact in the document;
  * exactly one ``RootLayer`` artifact per asset-container group, agreeing with
    the group's ``openusd.rootlayer`` label;
  * every ``openusd.digest`` matches a recomputed SHA-256 over the exact embedded
    document bytes, with ``openusd.digestalg == Sha256``;
  * each schema-plugin group holds exactly one ``SchemaPlugin`` and one
    ``GeneratedSchema`` artifact, and its ``plugInfo.json`` parses as JSON.

If the USD Python bindings (``pxr``) are installed, the embedded codeless schema
pair is additionally registered through ``PlugRegistry`` / ``UsdSchemaRegistry``
to confirm the two schema types resolve with the expected schema kinds.

Usage: python metaverse-specs/extras/openusd-artifacts/tools/validate_local.py
Exit code 0 and "OK" on success; non-zero with an ERRORS list otherwise.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ART_ROOT = os.path.abspath(os.path.join(HERE, ".."))
EXAMPLE = os.path.join(ART_ROOT, "examples", "openusd-artifacts.xregistry.json")

ASSET_GROUPS = "usdassetgroups"
PLUGIN_GROUPS = "usdschemaplugingroups"
RESOURCES = "usdassets"

ALLOWED_FORMATS = {"OpenUSD/1.0", "OpenUSD-PlugInfo/1.0"}
ALLOWED_KINDS = {
    "RootLayer", "SubLayer", "Reference", "Payload", "Texture", "Package",
    "MaterialX", "Volume", "SchemaPlugin", "GeneratedSchema", "Manifest",
}

ERR: list[str] = []


def err(msg: str) -> None:
    ERR.append(msg)


def _iter_groups(doc, collection, id_attr):
    for gid, group in doc.get(collection, {}).items():
        yield collection, gid, group, id_attr


def _check_resource(collection, gid, rid, res, all_xids):
    if res.get("usdassetid") != rid:
        err(f"{collection}/{gid}/{RESOURCES}/{rid}: usdassetid mismatch ({res.get('usdassetid')!r})")
    labels = res.get("labels", {})
    xid = res.get("xid")

    # (1) xid == assetidentifier label (normative §5.15.3).
    aid = labels.get("openusd.assetidentifier")
    if xid != aid:
        err(f"{rid}: xid {xid!r} != openusd.assetidentifier {aid!r}")

    # xid is unique and structurally derived from collection/group/id.
    expected = f"/{collection}/{gid}/{RESOURCES}/{rid}"
    if xid != expected:
        err(f"{rid}: xid {xid!r} != expected {expected!r}")
    if xid in all_xids:
        err(f"{rid}: duplicate xid {xid!r}")

    fmt = res.get("format")
    if fmt not in ALLOWED_FORMATS:
        err(f"{rid}: bad format {fmt!r}")
    kind = labels.get("openusd.assetkind")
    if kind not in ALLOWED_KINDS:
        err(f"{rid}: bad openusd.assetkind {kind!r}")

    doc_text = res.get("usdasset")
    if doc_text is None and res.get("usdasseturl") is None:
        err(f"{rid}: has neither 'usdasset' nor 'usdasseturl'")

    # (4) digest matches a recomputed SHA-256 over the embedded bytes.
    if doc_text is not None:
        if labels.get("openusd.digestalg") != "Sha256":
            err(f"{rid}: openusd.digestalg != 'Sha256'")
        recomputed = hashlib.sha256(doc_text.encode("utf-8")).hexdigest()
        if labels.get("openusd.digest") != recomputed:
            err(f"{rid}: openusd.digest does not match recomputed SHA-256")
        # plugInfo.json artifacts must parse as JSON.
        if fmt == "OpenUSD-PlugInfo/1.0":
            try:
                json.loads(doc_text)
            except json.JSONDecodeError:
                err(f"{rid}: embedded plugInfo JSON does not parse")
    return xid, kind


def _verify_schema_plugin_with_usd(doc):
    """Optional: register the embedded codeless pair and confirm it resolves."""
    try:
        from pxr import Plug, Usd  # type: ignore
    except Exception:
        print("  (install USD 'pxr' to also register-check the codeless schema pair)")
        return

    verify_dir = os.path.join(ART_ROOT, "examples", ".schema-verify")
    for gid, group in doc.get(PLUGIN_GROUPS, {}).items():
        shutil.rmtree(verify_dir, ignore_errors=True)
        os.makedirs(verify_dir, exist_ok=True)
        try:
            for rid, res in group.get(RESOURCES, {}).items():
                with open(os.path.join(verify_dir, rid), "w", encoding="utf-8", newline="") as fh:
                    fh.write(res["usdasset"])
            plugs = Plug.Registry().RegisterPlugins(verify_dir)
            if gid not in [p.name for p in plugs]:
                err(f"schema plugin '{gid}' did not register through PlugRegistry")
                continue
            reg = Usd.SchemaRegistry()
            manifest = json.loads(group[RESOURCES]["plugInfo.json"]["usdasset"])
            for tname, tinfo in manifest["Plugins"][0]["Info"]["Types"].items():
                got = str(reg.GetSchemaKind(tname))
                want = tinfo["schemaKind"]
                if want.lower() not in got.lower():
                    err(f"schema type '{tname}': schemaKind {got!r} != declared {want!r}")
        finally:
            shutil.rmtree(verify_dir, ignore_errors=True)


def main() -> int:
    if not os.path.exists(EXAMPLE):
        print(f"missing {EXAMPLE}; run build_catalog.py first")
        return 1
    with open(EXAMPLE, encoding="utf-8") as fh:
        doc = json.load(fh)

    for attr in ("specversion", "registryid", ASSET_GROUPS, PLUGIN_GROUPS):
        if attr not in doc:
            err(f"top-level missing '{attr}'")

    all_xids: set[str] = set()
    depends: list[tuple[str, str]] = []  # (owning rid, dependency xid)
    n_assets = 0

    # Asset-container groups: exactly one RootLayer each.
    for collection, gid, group, id_attr in _iter_groups(doc, ASSET_GROUPS, "usdassetgroupid"):
        if group.get(id_attr) != gid:
            err(f"{collection}/{gid}: {id_attr} mismatch")
        roots = []
        for rid, res in group.get(RESOURCES, {}).items():
            n_assets += 1
            xid, kind = _check_resource(collection, gid, rid, res, all_xids)
            all_xids.add(xid)
            if kind == "RootLayer":
                roots.append(xid)
            for dep in json.loads(res.get("labels", {}).get("openusd.dependson", "[]")):
                depends.append((rid, dep))
        if len(roots) != 1:
            err(f"{collection}/{gid}: expected exactly one RootLayer, found {len(roots)}")
        elif group.get("labels", {}).get("openusd.rootlayer") not in (None, roots[0]):
            err(f"{collection}/{gid}: openusd.rootlayer label != the RootLayer xid")

    # Schema-plugin groups: exactly one SchemaPlugin + one GeneratedSchema each.
    for collection, gid, group, id_attr in _iter_groups(doc, PLUGIN_GROUPS, "usdschemaplugingroupid"):
        if group.get(id_attr) != gid:
            err(f"{collection}/{gid}: {id_attr} mismatch")
        kinds: list[str] = []
        for rid, res in group.get(RESOURCES, {}).items():
            n_assets += 1
            xid, kind = _check_resource(collection, gid, rid, res, all_xids)
            all_xids.add(xid)
            kinds.append(kind)
            for dep in json.loads(res.get("labels", {}).get("openusd.dependson", "[]")):
                depends.append((rid, dep))
        if kinds.count("SchemaPlugin") != 1 or kinds.count("GeneratedSchema") != 1:
            err(f"{collection}/{gid}: need exactly one SchemaPlugin and one GeneratedSchema, got {sorted(kinds)}")

    # (2) every dependson entry resolves to an artifact that exists.
    for rid, dep in depends:
        if dep not in all_xids:
            err(f"{rid}: openusd.dependson entry {dep!r} resolves to no artifact")

    _verify_schema_plugin_with_usd(doc)

    print(f"artifacts: {n_assets} across "
          f"{len(doc.get(ASSET_GROUPS, {}))} asset container(s) + "
          f"{len(doc.get(PLUGIN_GROUPS, {}))} schema plugin(s)")
    if ERR:
        print(f"ERRORS: {len(ERR)}")
        for e in ERR:
            print(f"  - {e}")
        return 1
    print("OK - 0 errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
