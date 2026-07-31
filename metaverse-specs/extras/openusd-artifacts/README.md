# `openusd-artifacts` — xRegistry artifact registry for the OpenUSD binding

> **Draft-tracking artifact.** The OpenUSD binding model (Part 1 §7.11,
> `Opc.Ua.OpenUsd.NodeSet2.xml` 0.4.0) is a **draft** and is being edited; this
> folder tracks it and is regenerated from source. Treat the emitted JSON as
> illustrative, not authoritative.

The OpenUSD counterpart of `core-specs/extras/xregistry-catalog/`. Where that
folder emits an xRegistry **schema** catalog from an OPC UA NodeSet, this one
emits an xRegistry **artifact registry** — the artist-authored USD content a
server serves through `Server/OpenUSD/Artifacts` — per §7.11 of
`metaverse-specs/openusd-binding/OPC-UA-OpenUSD-Bindings.md`.

## Chosen vocabulary

The collection names and the domain attributes are **normatively defined** by
[`xRegistry-OpenUsd.md`](../../openusd-binding/xRegistry-OpenUsd.md) and its
model, [`xRegistry-OpenUsd.model.json`](../../openusd-binding/xRegistry-OpenUsd.model.json)
— the submittable xRegistry domain specification. This folder emits a conformant
instance of it.

| xRegistry role | Collection | Group / resource id | OPC UA type (Part 1 §7.11) |
|---|---|---|---|
| Groups (asset containers) | `usdassetgroups` | `usdassetgroupid` | `OpenUsdAssetGroupType` |
| Groups (schema plugins) | `usdschemaplugingroups` | `usdschemaplugingroupid` | `OpenUsdSchemaPluginGroupType` |
| Resources (in both group kinds) | `usdassets` | `usdassetid` | `OpenUsdAssetType` |
| Inline document field | `usdasset` | — | the `FileType` bytes |

Both group kinds hold `OpenUsdAssetType` resources, so both use the same
`usdassets` collection.

The domain metadata are **typed xRegistry attributes** declared in the model —
`assetidentifier`, `assetkind`, `dependson`, `digest`, `digestalg` on a resource
and `rootlayer` on an asset-container group — *not* `openusd.*` labels. This
matters beyond tidiness: xRegistry `labels` is a `map<string,string>`, so under
the previous label encoding `dependson` had to be a JSON-encoded *string*, while
Part 1 declares `DependsOn` as `String[]`. Declaring a model makes it a real
array and restores symmetry between the two projections.

Two attributes deliberately do **not** exist:

- **`assetcontainerid` / `pluginname`** — the *group id is* the container
  identifier and the plugin name. Restating a key as an attribute creates a
  second source of truth that can disagree with the first.
- **`mediatype`** — the core `contenttype` attribute already carries it. Part 1
  keeps a redundant `MediaType` for historical reasons and declares `ContentType`
  authoritative; the xRegistry projection simply omits it.

`validate_local.py` reads the enums and the required-attribute set straight out
of the model file, so the emitted document, the validator and the spec cannot
drift apart.

## Asset identifier &harr; `xid` (inter-derivable, §7.11.3)

The authored USD asset identifier and the xRegistry `xid` are **inter-derivable,
not equal** — equating them would lose the authored `@...@` string a resolver
needs:

- `assetidentifier` = the **authored** asset identifier, normalized relative to
  its container (a leading `./` is stripped; sub-paths and package `[...]`
  selectors are kept). A `componentAssetReference` of `@pump.usda@</Pump>`
  yields the identifier `pump.usda`.
- `ResourceId` (the resource key, `usdassetid`) = the URL-safe **percent-encoding**
  of the identifier — `pump.usda` stays `pump.usda`, while `textures/albedo.png`
  would become `textures%2Falbedo.png`.
- `xid` = `/<collection>/<usdassetgroupid>/usdassets/<ResourceId>`; the identifier
  is recovered by percent-decoding the xid's last segment.

The build derives them **one-directionally** (identifier → ResourceId → xid), so
they cannot diverge, and `validate_local.py` checks the round-trip
(`unquote(ResourceId) == assetidentifier`) rather than equality. Emitting the
*authored* identifier — not the xid — is what lets a connector cache each artifact
at its authored relative path so USD `@...@` references resolve locally.

## What is emitted

| Group | Kind | Artifacts |
|---|---|---|
| `usdassetgroups/pumps` (`pumps/Plant`) | asset container | `Plant.usda` (RootLayer) → `pump.usda`, `remote-pump.usda`; `pump.usda`, `remote-pump.usda` (Reference) |
| `usdassetgroups/robotics` (`robotics/Cell`) | asset container | `Cell.usda` (RootLayer) → `robot.usda`, `tool.usda`; `robot.usda`, `tool.usda` (Reference) |
| `usdschemaplugingroups/opcUaOpenUsdGeoDemo` | schema plugin | `plugInfo.json` (SchemaPlugin) + `generatedSchema.usda` (GeneratedSchema) |

A container group is **descriptor-driven**, not scanned. Each container's served
set, the authoritative `AssetKind` (including which artifact is the `RootLayer`),
and each `mediaType` come from its `*.OpenUsdBinding.json` descriptor's
`servedAssets.assets` (§7.11.2) — `pumps/Pumps.OpenUsdBinding.json` and
`robotics/Robotics.OpenUsdBinding.json`. The build fails loudly if a container's
descriptor is missing and cross-checks the served `RootLayer` against the
descriptor's `stage.rootLayerIdentifier`.

`openusd.dependson` is the artifact's **authored asset identifiers** (a JSON-array
string, restricted to the served set) so a resolver can match it directly against
a layer's `@...@` paths. Its edges come from two sources:

- the descriptor's **`componentAssetReference`** entries, which a connector authors
  at runtime (`dynamic: true`, §7.10/§7.10.1) and which therefore **cannot be seen by
  static scanning** — these attach to the root (the composition anchor);
- static `@...@` scanning of each served layer, used only as a **supplement** for
  sublayer/reference edges authored inside a served layer.

Static scanning never decides the artifact set or the root. Anything **not** in
`servedAssets` is excluded — in particular the connector's own `live.usda` runtime
override layer (serving it with a digest would freeze runtime values into
"delivered content", §7.10.1/§7.11.2 step 5) and the local `stage.usda` the operator
copies for the E2E walkthrough. `openusd.assetcontainerid` is the **group key**
(`pumps`, `robotics`), so it substitutes cleanly into §7.11.3's
`Xid = /<groups>/<AssetContainerId>/<resources>/<ResourceId>`.

`openusd.digest` is a SHA-256 over the exact embedded `usdasset` bytes
(`digestalg = Sha256`). All source layers here are text, so every artifact is
embedded **inline**; a binary or oversized artifact would instead carry a
`usdasseturl` (federation, §7.11.3).

> The pumps closure shows why scanning alone is unsound: `pump.usda` and
> `remote-pump.usda` contain **no** `@...@` at all, yet the descriptor lists them
> as served component assets. Robotics only *looked* right under scanning because
> its (excluded) `live.usda` ships a snapshot authoring `@robot.usda@`/`@tool.usda@`.

### Codeless schema — genuine, but an illustrative demo

`schemas/opcUaOpenUsdGeoDemo/` is a **real, registrable** codeless schema (a
concrete typed prim `OpcUaGeoreferencePrim` and a single-apply
`OpcUaGlobeAnchorAPI`), verified by loading the pair through USD's `PlugRegistry`
/ `UsdSchemaRegistry` (if `pxr` is installed, `validate_local.py` re-runs that
check). It mirrors the **shape** of the Part 2 Annex C georeference vendor types
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

`validate_local.py` is **independent of the emitter**: it re-derives the served
set, `AssetKind`, and `RootLayer` from the descriptors, and it re-scans each
embedded document for `@...@` (rather than trusting `openusd.dependson`), so it
catches an emitter that models the wrong closure — e.g. serving `live.usda`, or an
authored reference missing from `dependson`. It also checks the identifier↔xid
round-trip, `contenttype` vs `openusd.mediatype`, every `*count` field, recomputes
each SHA-256 digest, and confirms `openusd.pluginname` equals the embedded
manifest's `Plugins[0].Name`.
