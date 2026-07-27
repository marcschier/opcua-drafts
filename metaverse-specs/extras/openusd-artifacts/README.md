# `openusd-artifacts` — xRegistry artifact registry for the OpenUSD binding

> **Draft-tracking artifact.** The OpenUSD binding model (Part 1 §5.15,
> `Opc.Ua.OpenUsd.NodeSet2.xml` 0.4.0) is a **draft** and is being edited; this
> folder tracks it and is regenerated from source. Treat the emitted JSON as
> illustrative, not authoritative.

The OpenUSD counterpart of `core-specs/extras/xregistry-catalog/`. Where that
folder emits an xRegistry **schema** catalog from an OPC UA NodeSet, this one
emits an xRegistry **artifact registry** — the artist-authored USD content a
server serves through `Server/OpenUSD/Artifacts` — per §5.15 of
`metaverse-specs/openusd-binding/OPC-UA-OpenUSD-Bindings.md`.

## Chosen vocabulary

The base xRegistry model names each collection for its domain. This document uses:

| xRegistry role | Collection | Group / resource id | Model type |
|---|---|---|---|
| Groups (asset containers) | `usdassetgroups` | `usdassetgroupid` | `OpenUsdAssetGroupType` |
| Groups (schema plugins) | `usdschemaplugingroups` | `usdschemaplugingroupid` | `OpenUsdSchemaPluginGroupType` |
| Resources (in both group kinds) | `usdassets` | `usdassetid` | `OpenUsdAssetType` |
| Inline document field | `usdasset` | — | the `FileType` bytes |

Both group kinds hold `OpenUsdAssetType` resources, so both use the same
`usdassets` collection. The domain attributes travel as `openusd.*` labels
(`assetidentifier`, `assetkind`, `mediatype`, `digest`, `digestalg`, `dependson`).

## `xid` **is** the asset identifier (normative, §5.15.3)

Every artifact's `xid` equals its `openusd.assetidentifier` — that is what makes
the registry an addressable USD `ArResolver` backend. The build derives one xid
`/<collection>/<group>/usdassets/<filename>` and copies it into the label, so the
two strings **cannot** diverge; `validate_local.py` re-checks the equality.

## What is emitted

| Group | Kind | Artifacts |
|---|---|---|
| `usdassetgroups/pumps` (`pumps/Plant`) | asset container | `stage.usda` (RootLayer) → `live.usda`, `Plant.usda` (SubLayer) |
| `usdassetgroups/robotics` (`robotics/Cell`) | asset container | `stage.usda` (RootLayer) → `live.usda`, `Cell.usda` (SubLayer); `live.usda` → `robot.usda`, `tool.usda` (Reference) |
| `usdschemaplugingroups/opcUaOpenUsdGeoDemo` | schema plugin | `plugInfo.json` (SchemaPlugin) + `generatedSchema.usda` (GeneratedSchema) |

A container group is the **transitive closure** reachable from its stage root
layer. `AssetKind` is derived from the composition graph (a layer's incoming arc:
`subLayers` → SubLayer, `references` → Reference, `payload` → Payload; the root
has no incoming arc). `openusd.dependson` is derived by scanning each `.usda` for
`@...@` references (authored order, de-duplicated, resolved to the sibling's xid);
it is a JSON-array string. `openusd.digest` is a SHA-256 over the exact embedded
`usdasset` bytes (`digestalg = Sha256`). All source layers here are text, so every
artifact is embedded **inline**; a binary or oversized artifact would instead
carry a `usdasseturl` (federation, §5.15.3).

### Codeless schema — genuine, but an illustrative demo

`schemas/opcUaOpenUsdGeoDemo/` is a **real, registrable** codeless schema (a
concrete typed prim `OpcUaGeoreferencePrim` and a single-apply
`OpcUaGlobeAnchorAPI`), verified by loading the pair through USD's `PlugRegistry`
/ `UsdSchemaRegistry` (if `pxr` is installed, `validate_local.py` re-runs that
check). It mirrors the **shape** of the Part 2 Annex B georeference vendor types
under prototype-owned names — it is **not** the official Cesium for Omniverse
schema. `schema.usda` is the `usdGenSchema` input kept for provenance.

## Build & validate

```powershell
python metaverse-specs/extras/openusd-artifacts/tools/build_catalog.py
python metaverse-specs/extras/openusd-artifacts/tools/validate_local.py
```

`build_catalog.py` and `validate_local.py` are stdlib-only (`validate_local.py`
optionally uses `pxr` for the schema-registration check). Output is deterministic
(`sort_keys=True`, fixed indent) — running the build twice is byte-identical.
