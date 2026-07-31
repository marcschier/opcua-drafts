# OPC UA — OpenUSD Scene Materialization (Part 2)

**Release 0.4.1 — Draft** · namespace `http://opcfoundation.org/UA/OpenUSD/Scene/`

This folder contains the specification and generated NodeSet for **Part 2** of the *OPC UA — OpenUSD* work: a native OPC UA materialization of the **full OpenUSD data model**.

Stage, Prim, Attribute, Relationship, Metadata, composition arcs, VariantSets and typed/API schemas become OPC UA ObjectTypes, VariableTypes and DataTypes — so a composed USD scene **is** an OPC UA address space: browsable, subscribable, historizable, authorable, and vendor-extensible with native OPC UA semantics.

Where [Part 1](../openusd-binding/) leaves the scene outside OPC UA and binds into it, Part 2 brings the scene graph in. The two are complementary and orthogonal.

**Part 2 is self-contained.** It depends only on the base OPC UA model and does **not** require Part 1 — its NodeSet declares exactly one `RequiredModel`. Where a Server implements both, discovery under `Server/OpenUSD/Stages` and Part 1 bindings targeting Part 2 attributes are described in Annex C.

## What it covers

- **Structure.** A composed Stage, its Prim namespace hierarchy, each prim's Attributes (typed, valued Variables) and Relationships (ordered targets, as both References and target-list Variables), prim/stage Metadata, applied API schemas, composition arcs and VariantSets.
- **Typed schemas as OPC UA types.** USD IsA schemas map to ObjectType **subtyping** (`UsdGeomMeshType : UsdGeomGprimType : UsdGeomXformableType : …`); applied **API schemas** map to **AddIns / Interfaces**. This is the vendor-extension mechanism (§6.7) — a generic client browses an unknown subtype as its nearest known supertype, so subtyping is transparent to browse.
- **Conversion (§6.6).** Bidirectional `.usd` ↔ address space, with a normative round-trip contract for the composed scene.
- **Live data (§6.8).** Two modes: attribute Values updated in place, or retained history as time samples.
- **Georeferencing (§7.6).** A portable `UsdGeoreferenceApiType` / `UsdGlobeAnchorApiType`, since core OpenUSD has no geodetic schema. Annex C maps the concrete Cesium for Omniverse spelling, informatively.
- **Fallbacks (§6.7.4).** An importer **shall not drop** what it does not recognize — an unknown typed prim degrades to `UsdPrimType`, an unknown applied schema to a `UsdApiSchemaType` AddIn carrying its `SchemaName`, and an opaque value retains the **authored text** so an exporter reproduces it faithfully.

## Files

- `OPC-UA-OpenUSD-Scene-Materialization.md` — the specification.
- `Opc.Ua.OpenUsdScene.NodeSet2.xml` — generated NodeSet.
- `Opc.Ua.OpenUsdScene.NodeIds.csv` — generated NodeId assignments.
- `pumps/`, `robotics/` — materialized instance-overlay NodeSets for the two worked examples.

Tooling lives under [`../extras/openusd-scene/tools/`](../extras/openusd-scene/tools/): the model generator, the `usd_to_nodeset.py` / `nodeset_to_usd.py` converters, `regen_examples.py`, and `roundtrip_check.py` — which proves the §6.6.4 contract by converting each example both ways and diffing.

## Conformance

Eight independent, additive conformance units — **Scene Structure** is the baseline; a Server implements only what it needs:

Scene Structure · Composition Provenance · Typed Schemas · Applied Schemas · Georeferencing · Live Attributes · Conversion · Part 1 Interop

## Regenerate and validate

```powershell
python metaverse-specs\extras\openusd-scene\tools\build_model.py
python metaverse-specs\extras\openusd-scene\tools\validate_local.py
python metaverse-specs\extras\openusd-scene\tools\roundtrip_check.py
```

Edit `tools/build_model.py` — the single source of truth — never the generated NodeSet or CSV. Append new members at the **end**; a mid-file insert silently renumbers every NodeId after it.

Draft numeric NodeIds are provisional; final NodeIds are assigned by the OPC Foundation.
