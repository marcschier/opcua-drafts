# Changelog — OPC UA — OpenUSD Binding

Release history for `OPC-UA-OpenUSD-Bindings.md` and `Opc.Ua.OpenUsd.NodeSet2.xml`.
The specification itself describes only the current model; this file records how it
got there.

NodeId assignment is **append-only**: new members take the next free id, so every
previously published NodeId is stable across all releases below, and a namespace
index change does not affect per-namespace NodeId numbers.

## 0.5.0 — 2026-07-29

**Conformance units in the model, and a Word rendering.**

- Every Type Node now carries the ConformanceUnits that require it in the AddressSpace,
  as `Category` elements in the UANodeSet. OPC 20020 3.4.1.1 requires this, and the
  node tables of the Word rendering are generated from it. The previous `Category`
  values were coarse grouping labels (`OpenUSD Binding`, `OpenUSD Binding DataTypes`)
  that no conformance test could use. No NodeId changed.
- The specification is restructured into the clause skeleton the OPC Foundation
  companion specification template mandates: Scope, Normative references, Terms and
  conventions, General information, Use cases, Information model overview, ObjectTypes,
  DataTypes, Profiles and conformance units, Namespaces, Security, then Annexes A–F.
  Every clause number therefore moved; the mapping is recorded in
  `word-drafts/tools/specs/openusd-binding.json` and was applied mechanically to this
  document and to every sibling that cites it.
- The behavioural clauses now sit with the type they constrain: source and target
  resolution, conversion, and quality/timestamp/persistence are subclauses of
  `OpenUsdLiveBindingType`; the command rules belong to `OpenUsdCommandBindingType`;
  dynamic and cross-server composition belong to `OpenUsdComponentBindingType`; asset
  content delivery belongs to `OpenUsdArtifactRegistryType`.
- Informative material moved to annexes: using the model (Annex B), interoperability
  with OpenUSD and Omniverse (Annex C), the end-to-end collaboration flow (Annex D),
  bridging to the asset administration shell (Annex E) and geospatial rendering
  (Annex F). "Deliverables and reproducibility" is repository documentation and now
  lives in `README.md` alone.
- A submission-ready Word rendering is generated into `word-drafts/`. It is built from
  this document and the UANodeSet, so the node tables cannot drift from the model.

## 0.4.0 — 2026-07-27

**The artifact registry.**

- Asset content delivery (§5.15) is rebased on
  [*OPC UA — xRegistry*](../../core-specs/xregistry/OPC-UA-xRegistry.md), which
  becomes a **`RequiredModel`** of this specification — the only place the model
  is not self-contained on base OPC UA. A per-stage folder of files cannot
  express versions, change detection, labels or federation, and duplicates
  artifacts across stages that share them.
- `OpenUsdAssetType` subtypes the xRegistry `ResourceType`. Because
  `ResourceType` is itself a Part 5 `FileType`, the change is **structurally
  additive for a consumer**: an artifact node still *is* the file and its bytes
  are still read with `Open`/`Read`/`Close`. A connector that only downloads a
  root layer needs no change. What the retype adds is the xRegistry entity
  surface (`Xid`, `Epoch`, versions, `Labels`, federation) and a **server-wide**
  registry at `Server/OpenUSD/Artifacts` that stages reference rather than
  duplicate.
- `OpenUsdStageType.Assets` becomes a **view** that `Organizes` registry
  artifacts instead of owning them.
- The NodeSet gains a second RequiredModel, so xRegistry occupies namespace
  index 1 and this model moves to **index 2**.
- Five `OpenUsdAssetKindEnum` members **appended** — `MaterialX`, `Volume`,
  `SchemaPlugin`, `GeneratedSchema`, `Manifest` — so the registry can carry the
  artifact kinds a real USD asset needs beyond layers and textures, including
  the two files that constitute a codeless USD schema (§5.15.4). Existing
  members keep their numbers.
- New conformance units `OU-ArtifactRegistry`, `OU-ArtifactFederation` and
  `OU-SchemaPluginDelivery`, and a new *OpenUSD Artifact Server* profile.
- Adds the standalone xRegistry domain specification
  [`xRegistry-OpenUsd.md`](xRegistry-OpenUsd.md) — the same registry defined
  independently of OPC UA, so the two projections federate.

## 0.3.0 — 2026-07-25

**Geospatial.**

- The `Georeference` render target, the geospatial conversion profile (§5.8),
  and the `OU-Conversion-Geo` conformance unit (§7), mapped to the USD
  georeference schemas in Annex D.
- Because this adds a member to `OpenUsdRenderTargetKindEnum`, the NodeSet's
  `Version`/`PublicationDate` are bumped so a Client can detect the model
  change. A Server implementing no geospatial binding is otherwise unaffected.
- `UsdAttributeType.TargetNodeId` added so a binding can name a materialized
  Part 2 attribute Variable directly, alongside the BrowseName-path triple.

## 0.2.0 — 2026-07-13

**Capabilities beyond telemetry.** All additive and each gated by its own
conformance unit.

- Semantic-id source resolution (`SourceSemanticId`, ECLASS / IEC CDD).
- Command binding (opt-in, authorized, single-writer, fail-closed).
- Alarm and history bindings.
- Content integrity (`RootLayerDigest`).
- Composition / aggregation, including dynamic reconciliation from model-change
  events and cross-server components.
- Asset content delivery as a per-stage `Assets` folder of Part 5 `FileType`
  nodes with per-artifact digests.
- **Live-binding refactor.** A binding becomes an abstract
  `OpenUsdLiveBindingType` with one concrete subtype per intent
  (`OpenUsdValueChangeBindingType`, `OpenUsdAlarmBindingType`,
  `OpenUsdHistoryBindingType`, `OpenUsdCommandBindingType`; §5.4), replacing a
  single type discriminated by an `IntentProfile` enumeration. The 0.1 telemetry
  binding is expressed as `OpenUsdValueChangeBindingType`.

## 0.1.0 — 2026-07-12

**Baseline.**

- The mandatory `Server/OpenUSD` discovery facility, `OpenUsdStageType`, and the
  `OpenUsdRepresentation` AddIn tying an OPC UA Object to a composed USD prim
  path — identity only.
- A read-only telemetry binding from a source Variable `Value` to a target USD
  attribute, with conversion and quality/timestamp/persistence hints.
- The informative Omniverse realization profile.
