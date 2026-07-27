#!/usr/bin/env python3
"""Build an xRegistry artifact-registry document for the OpenUSD binding domain.

Emits the OpenUSD counterpart of ``core-specs/extras/xregistry-catalog`` per
§5.15 of ``metaverse-specs/openusd-binding/OPC-UA-OpenUSD-Bindings.md``:

  * ``usdassetgroups``        -> one ``OpenUsdAssetGroupType`` per asset container
                                 (a stage root layer plus the transitive closure
                                 of sublayers / references / payloads it needs).
  * ``usdschemaplugingroups`` -> one ``OpenUsdSchemaPluginGroupType`` per codeless
                                 USD schema plugin (a ``plugInfo.json`` +
                                 ``generatedSchema.usda`` pair).

Both group kinds hold ``OpenUsdAssetType`` resources under a ``usdassets``
collection. Every artifact's ``xid`` is, by construction, identical to its
``openusd.assetidentifier`` label (§5.15.3): the label is copied from the
resource's own ``xid`` field, so the two strings can never diverge. ``AssetKind``
is derived from the composition graph (not hard-coded), ``openusd.dependson`` is
derived by scanning each layer for ``@...@`` asset references, and
``openusd.digest`` is a SHA-256 over the exact bytes embedded for each artifact.

The source layers are the artist-authored examples under
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

# format / contenttype / mediatype by artifact media.
USDA = ("OpenUSD/1.0", "model/vnd.usda", "model/vnd.usda")
PLUGINFO = ("OpenUSD-PlugInfo/1.0", "application/json", "application/json")

# Asset containers to emit: (container id, human name, source subdirectory).
CONTAINERS = [
    ("pumps", "pumps/Plant", "pumps"),
    ("robotics", "robotics/Cell", "robotics"),
]

# The two files of a codeless schema map to fixed AssetKinds (spec §5.15.1/§5.15.4).
SCHEMA_FILE_KIND = {
    "plugInfo.json": ("SchemaPlugin", PLUGINFO),
    "generatedSchema.usda": ("GeneratedSchema", USDA),
}

_REF = re.compile(r"@([^@]+)@")
_SUBLAYERS = re.compile(r"subLayers\s*=\s*\[(.*?)\]", re.S)
_LISTOP = r"(?:(?:prepend|append|add|delete|reorder)\s+)?"
_REFERENCES = re.compile(_LISTOP + r"references\s*=\s*(\[[^\]]*\]|@[^@]+@[^\n]*)")
_PAYLOADS = re.compile(_LISTOP + r"payloads?\s*=\s*(\[[^\]]*\]|@[^@]+@[^\n]*)")


def _read_text(path: str) -> str:
    """Read a text file with universal-newline translation so the embedded bytes
    (and therefore the SHA-256 digest) are LF-normalised and checkout-stable."""
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _ref_basename(ref: str) -> str:
    ref = ref.strip().split("[", 1)[0]  # drop any package selector
    if ref.startswith("./"):
        ref = ref[2:]
    return ref.replace("\\", "/").split("/")[-1]


def _scan_dependencies(text: str) -> list[str]:
    """Ordered, de-duplicated basenames from every ``@...@`` reference, in the
    order they are authored in the layer (this is the DependsOn order)."""
    ordered: list[str] = []
    for ref in _REF.findall(text):
        base = _ref_basename(ref)
        if base and base not in ordered:
            ordered.append(base)
    return ordered


def _scan_kinded_refs(text: str) -> list[tuple[str, str]]:
    """(AssetKind, basename) for each reference, classified by composition arc."""
    out: list[tuple[str, str]] = []
    for block in _SUBLAYERS.findall(text):
        for ref in _REF.findall(block):
            out.append(("SubLayer", _ref_basename(ref)))
    for m in _REFERENCES.finditer(text):
        for ref in _REF.findall(m.group(1)):
            out.append(("Reference", _ref_basename(ref)))
    for m in _PAYLOADS.finditer(text):
        for ref in _REF.findall(m.group(1)):
            out.append(("Payload", _ref_basename(ref)))
    return out


def _artifact_xid(collection: str, group_id: str, filename: str) -> str:
    """The single source of truth for both ``xid`` and ``assetidentifier``."""
    return f"/{collection}/{group_id}/{RESOURCES}/{filename}"


def _resource(collection, group_id, filename, text, kind, fmt_tuple, depends_xids):
    fmt, contenttype, mediatype = fmt_tuple
    xid = _artifact_xid(collection, group_id, filename)
    resource = {
        "usdassetid": filename,
        "xid": xid,
        "epoch": 1,
        "versionid": "1",
        "isdefault": True,
        "name": filename,
        "format": fmt,
        "contenttype": contenttype,
        "usdasset": text,
        "labels": {
            # assetidentifier is copied from the resource's OWN xid so the
            # normative "AssetIdentifier == Xid" rule cannot be violated.
            "openusd.assetidentifier": xid,
            "openusd.assetkind": kind,
            "openusd.mediatype": mediatype,
            "openusd.digest": _sha256_hex(text),
            "openusd.digestalg": "Sha256",
            "openusd.dependson": json.dumps(depends_xids, separators=(",", ":")),
        },
    }
    return resource


def _classify_container(files_refs: dict[str, list[tuple[str, str]]]) -> tuple[str, dict[str, str]]:
    """Return (root filename, {filename: AssetKind}) for one container.

    The root is the layer with no incoming arc that itself sublayers others; the
    container is the transitive closure reachable from that root. Kinds come from
    the incoming arc (SubLayer / Reference / Payload); exactly one RootLayer.
    """
    incoming: dict[str, list[str]] = {f: [] for f in files_refs}
    adjacency: dict[str, list[str]] = {f: [] for f in files_refs}
    for src, refs in files_refs.items():
        for kind, base in refs:
            if base in files_refs:
                incoming[base].append(kind)
                if base not in adjacency[src]:
                    adjacency[src].append(base)

    roots = [
        f for f, inc in incoming.items()
        if not inc and any(k == "SubLayer" for k, _ in files_refs[f])
    ]
    if len(roots) != 1:
        raise SystemExit(f"expected exactly one root layer, found {sorted(roots)}")
    root = roots[0]

    # Transitive closure from the root (all arc kinds).
    closure = {root}
    stack = [root]
    while stack:
        cur = stack.pop()
        for nxt in adjacency[cur]:
            if nxt not in closure:
                closure.add(nxt)
                stack.append(nxt)

    kinds = {root: "RootLayer"}
    for f in closure:
        if f == root:
            continue
        inc = incoming[f]
        if "SubLayer" in inc:
            kinds[f] = "SubLayer"
        elif "Reference" in inc:
            kinds[f] = "Reference"
        elif "Payload" in inc:
            kinds[f] = "Payload"
        else:  # reachable only via an arc kind we do not special-case
            kinds[f] = "Reference"
    return root, kinds


def _build_container_group(collection, group_id, name, src_dir):
    usda_files = sorted(f for f in os.listdir(src_dir) if f.endswith(".usda"))
    texts = {f: _read_text(os.path.join(src_dir, f)) for f in usda_files}
    files_refs = {f: _scan_kinded_refs(t) for f, t in texts.items()}
    root, kinds = _classify_container(files_refs)

    filenames = [f for f in usda_files if f in kinds]  # closure only
    resources: dict[str, dict] = {}
    for f in filenames:
        depends = [
            _artifact_xid(collection, group_id, base)
            for base in _scan_dependencies(texts[f])
            if base in kinds  # every dependency is inside the container closure
        ]
        resources[f] = _resource(collection, group_id, f, texts[f], kinds[f], USDA, depends)

    group = {
        "usdassetgroupid": group_id,
        "name": name,
        "labels": {
            "openusd.assetcontainerid": f"/{collection}/{group_id}/{RESOURCES}/",
            "openusd.rootlayer": _artifact_xid(collection, group_id, root),
        },
        f"{RESOURCES}count": len(resources),
        RESOURCES: resources,
    }
    return group


def _build_schema_plugin_group(collection):
    plugin_name = os.path.basename(SCHEMA_DIR)
    manifest = json.loads(_read_text(os.path.join(SCHEMA_DIR, "plugInfo.json")))
    declared = manifest["Plugins"][0]["Name"]
    if declared != plugin_name:
        raise SystemExit(f"plugin dir '{plugin_name}' != manifest Name '{declared}'")

    resources: dict[str, dict] = {}
    for filename, (kind, fmt_tuple) in SCHEMA_FILE_KIND.items():
        text = _read_text(os.path.join(SCHEMA_DIR, filename))
        resources[filename] = _resource(collection, plugin_name, filename, text, kind, fmt_tuple, [])

    group = {
        "usdschemaplugingroupid": plugin_name,
        "name": plugin_name,
        "labels": {"openusd.pluginname": plugin_name},
        f"{RESOURCES}count": len(resources),
        RESOURCES: resources,
    }
    return group


def build(examples_dir: str) -> dict:
    asset_groups: dict[str, dict] = {}
    for group_id, name, sub in CONTAINERS:
        src_dir = os.path.join(examples_dir, sub)
        asset_groups[group_id] = _build_container_group(ASSET_GROUPS, group_id, name, src_dir)

    plugin_groups = {
        os.path.basename(SCHEMA_DIR): _build_schema_plugin_group(PLUGIN_GROUPS),
    }

    return {
        "specversion": SPEC_VERSION,
        "registryid": REGISTRY_ID,
        "self": SELF,
        "description": (
            "OpenUSD artifact registry (draft): artist-authored USD layers and a "
            "codeless schema plugin for the OPC UA <-> OpenUSD bindings, addressable "
            "as a USD ArResolver backend (AssetIdentifier == Xid)."
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
