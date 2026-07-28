#!/usr/bin/env python3
"""Build an xRegistry artifact-registry document for the OpenUSD binding domain.

Emits the OpenUSD counterpart of ``core-specs/extras/xregistry-catalog`` per
§5.15 of ``metaverse-specs/openusd-binding/OPC-UA-OpenUSD-Bindings.md``:

  * ``usdassetgroups``        -> one ``OpenUsdAssetGroupType`` per asset container.
  * ``usdschemaplugingroups`` -> one ``OpenUsdSchemaPluginGroupType`` per codeless
                                 USD schema plugin (a ``plugInfo.json`` +
                                 ``generatedSchema.usda`` pair).

The served-asset set, each artifact's ``AssetKind``, and the ``RootLayer`` come
from the container's ``*.OpenUsdBinding.json`` descriptor (§5.15.2), NOT from
scanning: ``servedAssets.assets`` is authoritative, and ``componentAssetReference``
edges are authored by a connector at runtime (§5.12/§5.13), so static ``@...@``
scanning cannot see them. Static scanning is used only as a *supplement* to
``openusd.dependson`` for sublayer/reference edges authored inside a served layer;
it never decides the artifact set or the root. Anything not in ``servedAssets``
(e.g. the connector's own ``live.usda`` override layer, or the local ``stage.usda``)
is excluded. A container whose descriptor is missing is a hard error.

Both group kinds hold ``OpenUsdAssetType`` resources under a ``usdassets``
collection. Per §5.15.3 the authored asset identifier and the xRegistry ``Xid``
are *inter-derivable*, not equal: ``openusd.assetidentifier`` is the authored USD
asset identifier normalized relative to its container (leading ``./`` removed);
``ResourceId`` is its URL-safe percent-encoding; and ``Xid`` is
``/<groups>/<AssetContainerId>/<resources>/<ResourceId>``. The build derives them
one-directionally (identifier -> ResourceId -> Xid), so they cannot diverge, and
the identifier is recoverable by percent-decoding the Xid's last segment.
``openusd.dependson`` lists the **authored asset identifiers** an artifact
references (descriptor component-asset edges on the root, plus any in-layer
``@...@`` edges), so a resolver can match them straight against ``@...@``, and
``openusd.digest`` is a SHA-256 over the exact bytes embedded for each artifact.

The source layers and descriptors are the artist-authored examples under
``metaverse-specs/extras/openusd-binding/examples``; the codeless schema pair is
the illustrative demo under ``../schemas/opcUaOpenUsdGeoDemo``.

Output is deterministic: ``sort_keys=True`` with a fixed indent, so running the
tool twice produces byte-identical output.

Usage (from repo root):
  python metaverse-specs/extras/openusd-artifacts/tools/build_catalog.py [EXAMPLES_DIR]
Writes: metaverse-specs/extras/openusd-artifacts/examples/openusd-artifacts.xregistry.json
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ART_ROOT = os.path.abspath(os.path.join(HERE, ".."))
DEFAULT_EXAMPLES = os.path.abspath(os.path.join(HERE, "..", "..", "openusd-binding", "examples"))
SCHEMA_DIR = os.path.join(ART_ROOT, "schemas", "opcUaOpenUsdGeoDemo")
OUT = os.path.join(ART_ROOT, "examples", "openusd-artifacts.xregistry.json")

SPEC_VERSION = "1.0-rc3"
REGISTRY_ID = "openusd-artifact-registry"
SELF = "https://registry.example.com/"

# Group collection names (this document's chosen vocabulary, stated in README).
ASSET_GROUPS = "usdassetgroups"
PLUGIN_GROUPS = "usdschemaplugingroups"
RESOURCES = "usdassets"

# format / contenttype by artifact media. Format identifiers are the enum of
# xRegistry-OpenUsd.md §4.5; they describe the DOCUMENT, while AssetKind
# describes the artifact's ROLE in the closure. The two are orthogonal.
USDA = ("OpenUSD/1.0", "model/vnd.usda")
PLUGINFO = ("USD-PlugInfo/1.0", "application/json")
GENSCHEMA = ("USD-GeneratedSchema/1.0", "model/vnd.usda")

# Extension by format identifier for served layers and other artifact classes.
_FORMAT_BY_EXT = {
    ".usda": "OpenUSD/1.0",
    ".usdc": "OpenUSD/1.0",
    ".usd": "OpenUSD/1.0",
    ".usdz": "USDZ/1.0",
    ".mtlx": "MaterialX/1.39",
}

# Asset containers to emit: (container id / group key, human name, source subdir).
# The served-asset set and kinds come from each subdir's *.OpenUsdBinding.json.
CONTAINERS = [
    ("pumps", "pumps/Plant", "pumps"),
    ("robotics", "robotics/Cell", "robotics"),
]

# The two files of a codeless schema map to fixed AssetKinds (spec §5.15.1/§5.15.4).
# A generatedSchema.usda is syntactically a USD layer but is registered rather
# than composed, so it carries its own format identifier (xRegistry spec §4.5.5).
SCHEMA_FILE_KIND = {
    "plugInfo.json": ("SchemaPlugin", PLUGINFO),
    "generatedSchema.usda": ("GeneratedSchema", GENSCHEMA),
}

# Matches the asset path inside a USD ``@...@`` reference (excludes any trailing
# ``</PrimPath>`` selector, which sits outside the surrounding @-quotes).
_REF = re.compile(r"@([^@]+)@")

# Descriptor filename suffix that seeds a container (servedAssets + kinds + root).
DESCRIPTOR_SUFFIX = ".OpenUsdBinding.json"


def _read_text(path: str) -> str:
    """Read a text file with universal-newline translation so the embedded bytes
    (and therefore the SHA-256 digest) are LF-normalised and checkout-stable."""
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_asset_id(ref: str) -> str:
    """Normalize an authored ``@...@`` reference to a container-relative asset
    identifier (§5.15.3): trim, use forward slashes, drop a single leading
    ``./``. Sub-paths and package ``[...]`` selectors are preserved verbatim so
    the identifier still resolves the way the layer authored it."""
    ref = ref.strip().replace("\\", "/")
    if ref.startswith("./"):
        ref = ref[2:]
    return ref


def _resource_id(asset_id: str) -> str:
    """URL-safe percent-encoding of an asset identifier (§5.15.3 ResourceId).

    Nothing that is URL-safe is escaped, so a plain ``live.usda`` is unchanged
    while ``textures/albedo.png`` becomes ``textures%2Falbedo.png``. The inverse
    is ``urllib.parse.unquote``; the validator asserts the round-trip."""
    return urllib.parse.quote(asset_id, safe="")


def _scan_dependencies(text: str) -> list[str]:
    """Ordered, de-duplicated authored asset identifiers from every ``@...@``
    reference, in the order they are authored in the layer (DependsOn order)."""
    ordered: list[str] = []
    for ref in _REF.findall(text):
        aid = _normalize_asset_id(ref)
        if aid and aid not in ordered:
            ordered.append(aid)
    return ordered


def _iter_named_strings(node, key):
    """Yield every string value stored under ``key`` anywhere in a nested JSON
    structure, in document (insertion) order."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key and isinstance(v, str):
                yield v
            else:
                yield from _iter_named_strings(v, key)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_named_strings(item, key)


def _component_asset_ids(descriptor: dict) -> list[str]:
    """Ordered, de-duplicated asset identifiers referenced by every
    ``componentAssetReference`` in the descriptor. A connector authors component
    references at runtime (§5.12/§5.13), so static ``@...@`` scanning cannot see
    them; the descriptor is their only source of truth."""
    ordered: list[str] = []
    for ref in _iter_named_strings(descriptor, "componentAssetReference"):
        for aid in _scan_dependencies(ref):
            if aid not in ordered:
                ordered.append(aid)
    return ordered


def _asset_stem(identifier: str) -> str:
    """Basename without directory, package selector, or extension - used to match
    a served RootLayer asset to the stage's ``rootLayerIdentifier`` (which may use
    a different ``.usd``/``.usda`` variant or an ``asset-repo/`` prefix)."""
    base = identifier.replace("\\", "/").split("/")[-1].split("[", 1)[0]
    return os.path.splitext(base)[0]


def _fmt_for(asset_id: str, media_type: str) -> tuple[str, str]:
    """(format, contenttype) for a served asset. contenttype is kept equal to the
    descriptor's mediaType; format is derived from the extension and is one of the
    identifiers enumerated in xRegistry-OpenUsd.md §4.5. Anything whose internal
    structure the spec does not describe (textures, volumes) is Opaque/1.0."""
    base = asset_id.replace("\\", "/").split("/")[-1].split("[", 1)[0]
    ext = os.path.splitext(base)[1].lower()
    return (_FORMAT_BY_EXT.get(ext, "Opaque/1.0"), media_type)


def _resource(collection, group_id, asset_id, text, kind, fmt_tuple, depends_ids):
    fmt, contenttype = fmt_tuple
    # asset_id is the single source of truth; ResourceId and Xid derive from it.
    resource_id = _resource_id(asset_id)
    xid = f"/{collection}/{group_id}/{RESOURCES}/{resource_id}"
    # Domain metadata are TYPED xRegistry attributes declared in
    # xRegistry-OpenUsd.model.json - not labels. labels is a map<string,string>,
    # which would force dependson to be a JSON-encoded string and break symmetry
    # with the OPC UA projection, where DependsOn is a String[].
    resource = {
        "usdassetid": resource_id,
        "xid": xid,
        "epoch": 1,
        "versionid": "1",
        "isdefault": True,
        "name": asset_id,
        "format": fmt,
        "contenttype": contenttype,
        "usdasset": text,
        # The authored, container-relative asset identifier (§5.1). The ResourceId
        # in the xid is quote(assetidentifier); the identifier is recoverable by
        # unquoting the xid's last segment.
        "assetidentifier": asset_id,
        "assetkind": kind,
        # authored asset identifiers, so a resolver matches them vs @...@.
        "dependson": list(depends_ids),
        "digest": _sha256_hex(text),
        "digestalg": "Sha256",
    }
    return resource


def _find_descriptor(src_dir: str) -> str:
    cands = sorted(f for f in os.listdir(src_dir) if f.endswith(DESCRIPTOR_SUFFIX))
    if len(cands) != 1:
        raise SystemExit(f"{src_dir}: expected exactly one *{DESCRIPTOR_SUFFIX}, found {cands}")
    return os.path.join(src_dir, cands[0])


def _build_container_group(collection, group_id, name, src_dir):
    descriptor = json.loads(_read_text(_find_descriptor(src_dir)))
    served = descriptor.get("servedAssets", {}).get("assets", [])
    if not served:
        raise SystemExit(f"{src_dir}: descriptor has no servedAssets.assets")

    # servedAssets is the authoritative artifact set, AssetKind, and media type.
    served_ids: list[str] = []
    kind_of: dict[str, str] = {}
    media_of: dict[str, str] = {}
    for a in served:
        aid = _normalize_asset_id(a["assetIdentifier"])
        if aid in kind_of:
            raise SystemExit(f"{src_dir}: duplicate servedAsset {aid!r}")
        served_ids.append(aid)
        kind_of[aid] = a["assetKind"]
        media_of[aid] = a.get("mediaType", USDA[1])

    roots = [aid for aid in served_ids if kind_of[aid] == "RootLayer"]
    if len(roots) != 1:
        raise SystemExit(f"{src_dir}: expected exactly one RootLayer in servedAssets, found {roots}")
    root = roots[0]

    # Cross-check the served root against the stage's rootLayerIdentifier (§5.15.2:
    # the root is the artifact whose AssetIdentifier matches the stage root).
    stage_root = descriptor.get("stage", {}).get("rootLayerIdentifier", "")
    if stage_root and _asset_stem(stage_root) != _asset_stem(root):
        raise SystemExit(
            f"{src_dir}: RootLayer {root!r} does not match stage.rootLayerIdentifier {stage_root!r}")

    served_set = set(served_ids)
    # Component-asset edges attach to the root: it is the composition anchor into
    # which a connector authors the component references at runtime (§5.12/§5.13).
    component_edges = [aid for aid in _component_asset_ids(descriptor) if aid in served_set]

    resources: dict[str, dict] = {}
    for aid in served_ids:
        src_path = os.path.join(src_dir, aid)
        if not os.path.isfile(src_path):
            raise SystemExit(f"{src_dir}: served asset {aid!r} is not present on disk")
        text = _read_text(src_path)
        # DependsOn = static @...@ edges authored INSIDE this served layer (the
        # supplement), plus (for the root) the descriptor's component-asset edges.
        # Both are authored asset identifiers, restricted to the served set.
        deps = [d for d in _scan_dependencies(text) if d in served_set and d != aid]
        if aid == root:
            for d in component_edges:
                if d not in deps and d != aid:
                    deps.append(d)
        res = _resource(collection, group_id, aid, text, kind_of[aid], _fmt_for(aid, media_of[aid]), deps)
        resources[res["usdassetid"]] = res  # keyed by ResourceId

    group = {
        "usdassetgroupid": group_id,
        "name": name,
        # The group id IS the asset container identifier (xRegistry spec §4.1), so
        # no separate attribute restates it. rootlayer is a real typed attribute.
        "rootlayer": root,
        f"{RESOURCES}count": len(resources),
        RESOURCES: resources,
    }
    return group


def _build_schema_plugin_group(collection):
    manifest_text = _read_text(os.path.join(SCHEMA_DIR, "plugInfo.json"))
    # The plugin name is authoritative from the manifest, not the directory name.
    plugin_name = json.loads(manifest_text)["Plugins"][0]["Name"]

    resources: dict[str, dict] = {}
    for filename, (kind, fmt_tuple) in SCHEMA_FILE_KIND.items():
        text = _read_text(os.path.join(SCHEMA_DIR, filename))
        res = _resource(collection, plugin_name, filename, text, kind, fmt_tuple, [])
        resources[res["usdassetid"]] = res  # keyed by ResourceId

    group = {
        "usdschemaplugingroupid": plugin_name,
        "name": plugin_name,
        # The group id IS the plugin name (xRegistry spec §4.3); no label restates it.
        f"{RESOURCES}count": len(resources),
        RESOURCES: resources,
    }
    return group


def build(examples_dir: str) -> dict:
    asset_groups: dict[str, dict] = {}
    for group_id, name, sub in CONTAINERS:
        src_dir = os.path.join(examples_dir, sub)
        if not os.path.isdir(src_dir):
            raise SystemExit(f"missing container source directory: {src_dir}")
        asset_groups[group_id] = _build_container_group(ASSET_GROUPS, group_id, name, src_dir)

    plugin_group = _build_schema_plugin_group(PLUGIN_GROUPS)
    plugin_groups = {plugin_group["usdschemaplugingroupid"]: plugin_group}

    return {
        "specversion": SPEC_VERSION,
        "registryid": REGISTRY_ID,
        "self": SELF,
        "description": (
            "OpenUSD artifact registry (draft): artist-authored USD layers and a "
            "codeless schema plugin for the OPC UA <-> OpenUSD bindings, addressable "
            "as a USD ArResolver backend (AssetIdentifier <-> ResourceId <-> Xid, "
            "inter-derivable per §5.15.3)."
        ),
        f"{ASSET_GROUPS}count": len(asset_groups),
        ASSET_GROUPS: asset_groups,
        f"{PLUGIN_GROUPS}count": len(plugin_groups),
        PLUGIN_GROUPS: plugin_groups,
    }


def main() -> int:
    examples_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EXAMPLES
    doc = build(examples_dir)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")

    n_assets = sum(g[f"{RESOURCES}count"] for g in doc[ASSET_GROUPS].values())
    n_plugins = sum(g[f"{RESOURCES}count"] for g in doc[PLUGIN_GROUPS].values())
    print(f"wrote {OUT}")
    print(f"  {ASSET_GROUPS}={len(doc[ASSET_GROUPS])} artifacts={n_assets}; "
          f"{PLUGIN_GROUPS}={len(doc[PLUGIN_GROUPS])} artifacts={n_plugins}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
