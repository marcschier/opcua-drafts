#!/usr/bin/env python3
"""Validate the generated OpenUSD artifact-registry document.

The checks are deliberately INDEPENDENT of the emitter. The artifact set, the
per-artifact ``AssetKind``, and the ``RootLayer`` come from each container's
``*.OpenUsdBinding.json`` descriptor (§5.15.2) - the same source the build reads -
and authored dependencies are re-scanned from each artifact's embedded document
rather than trusted from ``openusd.dependson``. So the validator can catch an
emitter that models the wrong closure (e.g. serving the connector's own
``live.usda`` override layer, or dropping a descriptor component-asset edge).

Structural + §5.15.3 checks against ``examples/openusd-artifacts.xregistry.json``:

  * required top-level / group / resource attributes and id<->key agreement;
  * identifier<->id<->xid round-trip: every ``ResourceId`` percent-decodes to its
    ``openusd.assetidentifier`` and is recoverable from the ``xid``'s last segment;
  * xids are globally unique and structurally ``/<coll>/<group>/usdassets/<id>``;
  * ``contenttype`` agrees with ``openusd.mediatype``; every ``*count`` field
    equals the actual collection size;
  * every ``openusd.digest`` matches a recomputed SHA-256 over the exact embedded
    document bytes, with ``openusd.digestalg == Sha256``.

Asset-container groups (cross-checked against the descriptor):

  * the group's artifact set equals ``servedAssets`` exactly - nothing outside it
    (no ``live.usda`` / ``stage.usda``) and nothing missing;
  * each artifact's ``AssetKind`` matches the descriptor's ``assetKind``;
  * exactly one ``RootLayer``, matching both the descriptor's ``rootLayerIdentifier``
    and the group's ``openusd.rootlayer`` label; ``openusd.assetcontainerid`` is the
    group key;
  * every ``@...@`` reference re-scanned from an artifact's own document appears in
    its ``openusd.dependson`` and resolves within the container, and every declared
    ``dependson`` entry resolves within the container too.

Schema-plugin groups:

  * exactly one ``SchemaPlugin`` and one ``GeneratedSchema``; ``plugInfo.json``
    parses as JSON; ``openusd.pluginname`` equals the embedded manifest's
    ``Plugins[0].Name`` (re-read from the document, not a directory name).

If the USD Python bindings (``pxr``) are installed, each embedded codeless schema
pair is additionally registered through ``PlugRegistry`` / ``UsdSchemaRegistry``
to confirm the two schema types resolve with the expected schema kinds.

Usage: python metaverse-specs/extras/openusd-artifacts/tools/validate_local.py
Exit code 0 and "OK" on success; non-zero with an ERRORS list otherwise.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ART_ROOT = os.path.abspath(os.path.join(HERE, ".."))
EXAMPLE = os.path.join(ART_ROOT, "examples", "openusd-artifacts.xregistry.json")
EXAMPLES_DIR = os.path.abspath(os.path.join(ART_ROOT, "..", "openusd-binding", "examples"))

ASSET_GROUPS = "usdassetgroups"
PLUGIN_GROUPS = "usdschemaplugingroups"
RESOURCES = "usdassets"
DESCRIPTOR_SUFFIX = ".OpenUsdBinding.json"

ALLOWED_FORMATS = {"OpenUSD/1.0", "OpenUSD-PlugInfo/1.0"}
ALLOWED_KINDS = {
    "RootLayer", "SubLayer", "Reference", "Payload", "Texture", "Package",
    "MaterialX", "Volume", "SchemaPlugin", "GeneratedSchema", "Manifest",
}

_REF = re.compile(r"@([^@]+)@")

ERR: list[str] = []


def err(msg: str) -> None:
    ERR.append(msg)


def _normalize_asset_id(ref: str) -> str:
    ref = ref.strip().replace("\\", "/")
    if ref.startswith("./"):
        ref = ref[2:]
    return ref


def _asset_stem(identifier: str) -> str:
    base = identifier.replace("\\", "/").split("/")[-1].split("[", 1)[0]
    return os.path.splitext(base)[0]


def _authored_refs(text: str) -> list[str]:
    """Independently re-scan an embedded document for its ``@...@`` references."""
    out: list[str] = []
    for r in _REF.findall(text or ""):
        aid = _normalize_asset_id(r)
        if aid and aid not in out:
            out.append(aid)
    return out


def _deps(res) -> list[str]:
    return json.loads(res.get("labels", {}).get("openusd.dependson", "[]"))


def _load_descriptors() -> dict[str, dict]:
    """Parse every container's ``*.OpenUsdBinding.json``, keyed by both its source
    subdirectory name and its lower-cased ``domain`` so a group id resolves either
    way. This is the independent source of truth for the served-asset closure."""
    out: dict[str, dict] = {}
    if not os.path.isdir(EXAMPLES_DIR):
        return out
    for sub in sorted(os.listdir(EXAMPLES_DIR)):
        d = os.path.join(EXAMPLES_DIR, sub)
        if not os.path.isdir(d):
            continue
        cands = sorted(f for f in os.listdir(d) if f.endswith(DESCRIPTOR_SUFFIX))
        if len(cands) != 1:
            continue
        with open(os.path.join(d, cands[0]), encoding="utf-8") as fh:
            desc = json.load(fh)
        for key in {sub, str(desc.get("domain", "")).lower()}:
            if key:
                out[key] = desc
    return out


def _check_resource(collection, gid, rid, res, all_xids):
    if res.get("usdassetid") != rid:
        err(f"{collection}/{gid}/{RESOURCES}/{rid}: usdassetid mismatch ({res.get('usdassetid')!r})")
    labels = res.get("labels", {})
    xid = res.get("xid")
    aid = labels.get("openusd.assetidentifier")

    # §5.15.3 round-trip: ResourceId percent-decodes to the authored identifier,
    # and the identifier is recoverable from the xid's last segment.
    if aid is None:
        err(f"{rid}: missing openusd.assetidentifier")
    else:
        if urllib.parse.unquote(rid) != aid:
            err(f"{rid}: ResourceId does not percent-decode to assetidentifier {aid!r}")
        last = xid.rsplit("/", 1)[-1] if isinstance(xid, str) else ""
        if urllib.parse.unquote(last) != aid:
            err(f"{rid}: xid last segment {last!r} does not percent-decode to assetidentifier {aid!r}")

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

    # contenttype must agree with the declared media type.
    ct, media = res.get("contenttype"), labels.get("openusd.mediatype")
    if ct != media:
        err(f"{rid}: contenttype {ct!r} != openusd.mediatype {media!r}")

    doc_text = res.get("usdasset")
    if doc_text is None and res.get("usdasseturl") is None:
        err(f"{rid}: has neither 'usdasset' nor 'usdasseturl'")

    # digest matches a recomputed SHA-256 over the embedded bytes.
    if doc_text is not None:
        if labels.get("openusd.digestalg") != "Sha256":
            err(f"{rid}: openusd.digestalg != 'Sha256'")
        recomputed = hashlib.sha256(doc_text.encode("utf-8")).hexdigest()
        if labels.get("openusd.digest") != recomputed:
            err(f"{rid}: openusd.digest does not match recomputed SHA-256")
        if fmt == "OpenUSD-PlugInfo/1.0":
            try:
                json.loads(doc_text)
            except json.JSONDecodeError:
                err(f"{rid}: embedded plugInfo JSON does not parse")
    return xid, aid, kind


def _check_dependencies(collection, gid, aid, text, declared, ids_in_group, unit):
    """Independent closure check for one artifact: every @...@ authored in its own
    document must appear in dependson AND resolve within the container; and every
    declared dependson entry must resolve within the container."""
    for ref in _authored_refs(text):
        if ref not in declared:
            err(f"{collection}/{gid}/{aid}: authored reference @{ref}@ missing from dependson")
        if ref not in ids_in_group:
            err(f"{collection}/{gid}/{aid}: authored reference @{ref}@ resolves to no artifact in {unit} {gid!r}")
    for dep in declared:
        if dep not in ids_in_group:
            err(f"{collection}/{gid}/{aid}: dependson {dep!r} resolves to no artifact in {unit} {gid!r}")


def _check_asset_container(collection, gid, group, descriptors, all_xids) -> int:
    if group.get("usdassetgroupid") != gid:
        err(f"{collection}/{gid}: usdassetgroupid mismatch")

    desc = descriptors.get(gid)
    served_ids: list[str] = []
    served_kind: dict[str, str] = {}
    root_stem = ""
    if desc is None:
        err(f"{collection}/{gid}: no *{DESCRIPTOR_SUFFIX} descriptor found to validate against")
    else:
        for a in desc.get("servedAssets", {}).get("assets", []):
            said = _normalize_asset_id(a["assetIdentifier"])
            served_ids.append(said)
            served_kind[said] = a["assetKind"]
        root_stem = _asset_stem(desc.get("stage", {}).get("rootLayerIdentifier", ""))

    resources = group.get(RESOURCES, {})
    ids_in_group: set[str] = set()
    kind_by_aid: dict[str, str] = {}
    text_by_aid: dict[str, str] = {}
    deps_by_aid: dict[str, list[str]] = {}
    roots: list[str] = []
    for rid, res in resources.items():
        xid, aid, kind = _check_resource(collection, gid, rid, res, all_xids)
        all_xids.add(xid)
        if aid is None:
            continue
        ids_in_group.add(aid)
        kind_by_aid[aid] = kind
        text_by_aid[aid] = res.get("usdasset") or ""
        deps_by_aid[aid] = _deps(res)
        if kind == "RootLayer":
            roots.append(aid)

    if group.get(f"{RESOURCES}count") != len(resources):
        err(f"{collection}/{gid}: {RESOURCES}count {group.get(f'{RESOURCES}count')!r} != {len(resources)}")

    # The group's artifact set equals servedAssets exactly (the core §5.15.2 rule).
    if desc is not None:
        extra = ids_in_group - set(served_ids)
        missing = set(served_ids) - ids_in_group
        if extra:
            err(f"{collection}/{gid}: artifacts not in servedAssets: {sorted(extra)}")
        if missing:
            err(f"{collection}/{gid}: servedAssets missing from group: {sorted(missing)}")
        for aid, kind in kind_by_aid.items():
            if aid in served_kind and kind != served_kind[aid]:
                err(f"{collection}/{gid}/{aid}: assetkind {kind!r} != descriptor {served_kind[aid]!r}")

    # Exactly one RootLayer, agreeing with the descriptor and the group label.
    if len(roots) != 1:
        err(f"{collection}/{gid}: expected exactly one RootLayer, found {sorted(roots)}")
    else:
        root = roots[0]
        if root_stem and _asset_stem(root) != root_stem:
            err(f"{collection}/{gid}: RootLayer {root!r} != descriptor rootLayerIdentifier stem {root_stem!r}")
        label_root = group.get("labels", {}).get("openusd.rootlayer")
        if label_root not in (None, root):
            err(f"{collection}/{gid}: openusd.rootlayer {label_root!r} != RootLayer {root!r}")

    acid = group.get("labels", {}).get("openusd.assetcontainerid")
    if acid not in (None, gid):
        err(f"{collection}/{gid}: openusd.assetcontainerid {acid!r} != group key {gid!r}")

    for aid, text in text_by_aid.items():
        _check_dependencies(collection, gid, aid, text, deps_by_aid[aid], ids_in_group, "container")
    return len(resources)


def _check_plugin_group(collection, gid, group, all_xids) -> int:
    if group.get("usdschemaplugingroupid") != gid:
        err(f"{collection}/{gid}: usdschemaplugingroupid mismatch")
    resources = group.get(RESOURCES, {})
    if group.get(f"{RESOURCES}count") != len(resources):
        err(f"{collection}/{gid}: {RESOURCES}count {group.get(f'{RESOURCES}count')!r} != {len(resources)}")

    kinds: list[str] = []
    ids_in_group: set[str] = set()
    text_by_aid: dict[str, str] = {}
    deps_by_aid: dict[str, list[str]] = {}
    manifest_name = None
    for rid, res in resources.items():
        xid, aid, kind = _check_resource(collection, gid, rid, res, all_xids)
        all_xids.add(xid)
        kinds.append(kind)
        if aid is not None:
            ids_in_group.add(aid)
            text_by_aid[aid] = res.get("usdasset") or ""
            deps_by_aid[aid] = _deps(res)
        if res.get("format") == "OpenUSD-PlugInfo/1.0" and res.get("usdasset"):
            try:
                manifest_name = json.loads(res["usdasset"])["Plugins"][0]["Name"]
            except (json.JSONDecodeError, KeyError, IndexError):
                manifest_name = None

    if kinds.count("SchemaPlugin") != 1 or kinds.count("GeneratedSchema") != 1:
        err(f"{collection}/{gid}: need exactly one SchemaPlugin and one GeneratedSchema, got {sorted(kinds)}")

    # openusd.pluginname is the embedded manifest's Plugins[0].Name (re-read here).
    label_name = group.get("labels", {}).get("openusd.pluginname")
    if manifest_name is None:
        err(f"{collection}/{gid}: no parseable plugInfo manifest Name in the document")
    else:
        if label_name != manifest_name:
            err(f"{collection}/{gid}: openusd.pluginname {label_name!r} != manifest Name {manifest_name!r}")
        if gid != manifest_name:
            err(f"{collection}/{gid}: group key != manifest Name {manifest_name!r}")

    for aid, text in text_by_aid.items():
        _check_dependencies(collection, gid, aid, text, deps_by_aid[aid], ids_in_group, "group")
    return len(resources)


def _verify_schema_plugin_with_usd(doc):
    """Optional: register each embedded codeless pair and confirm it resolves."""
    try:
        from pxr import Plug, Usd  # type: ignore
    except Exception:
        print("  (install USD 'pxr' to also register-check the codeless schema pair)")
        return

    base = os.path.join(ART_ROOT, "examples", ".schema-verify")
    try:
        for gid, group in doc.get(PLUGIN_GROUPS, {}).items():
            # A unique directory per plugin: PlugRegistry is a process-global
            # singleton, so a second plugin group sharing one path would fail to
            # register (and raise a false error).
            verify_dir = os.path.join(base, gid)
            shutil.rmtree(verify_dir, ignore_errors=True)
            os.makedirs(verify_dir, exist_ok=True)
            for rid, res in group.get(RESOURCES, {}).items():
                with open(os.path.join(verify_dir, rid), "w", encoding="utf-8", newline="") as fh:
                    fh.write(res.get("usdasset", ""))
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
        shutil.rmtree(base, ignore_errors=True)


def main() -> int:
    if not os.path.exists(EXAMPLE):
        print(f"missing {EXAMPLE}; run build_catalog.py first")
        return 1
    with open(EXAMPLE, encoding="utf-8") as fh:
        doc = json.load(fh)

    for attr in ("specversion", "registryid", ASSET_GROUPS, PLUGIN_GROUPS):
        if attr not in doc:
            err(f"top-level missing '{attr}'")
    if doc.get(f"{ASSET_GROUPS}count") != len(doc.get(ASSET_GROUPS, {})):
        err(f"{ASSET_GROUPS}count != number of {ASSET_GROUPS}")
    if doc.get(f"{PLUGIN_GROUPS}count") != len(doc.get(PLUGIN_GROUPS, {})):
        err(f"{PLUGIN_GROUPS}count != number of {PLUGIN_GROUPS}")

    descriptors = _load_descriptors()
    all_xids: set[str] = set()
    n_assets = 0
    for gid, group in doc.get(ASSET_GROUPS, {}).items():
        n_assets += _check_asset_container(ASSET_GROUPS, gid, group, descriptors, all_xids)
    for gid, group in doc.get(PLUGIN_GROUPS, {}).items():
        n_assets += _check_plugin_group(PLUGIN_GROUPS, gid, group, all_xids)

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
