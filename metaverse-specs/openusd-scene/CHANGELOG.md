# Changelog — OPC UA — OpenUSD Scene Materialization (Part 2)

Release history for `OPC-UA-OpenUSD-Scene-Materialization.md` and
`Opc.Ua.OpenUsdScene.NodeSet2.xml`. The specification itself describes only the
current model; this file records how it got there.

NodeId assignment is **append-only**: new members take the next free id, so every
previously published NodeId is stable across all releases below.

## 0.3.0 — 2026-07-29

**Model corrections found while implementing Part 2.**

- **`UsdApiSchemaType` is concrete.** §8.4 requires an importer to degrade an
  unknown applied API schema *to* a `UsdApiSchemaType` AddIn, which is a positive
  requirement to instantiate the type — but the model declared it
  `IsAbstract="true"`, and an Object cannot take an abstract ObjectType as its
  `HasTypeDefinition` (OPC 10000-3). A conforming importer could not satisfy
  §8.4 at all, and the nodes it produced were rejected by strict clients and
  NodeSet validators. `NodeId 1020` is unchanged and no member NodeId shifted.
- **`UsdAttributeType.ConnectionPaths` added** (NodeId 6078). Relationships could
  already carry their authored targets, but attribute *connections* had nowhere
  to go, so a round-trip lost them.
- **Annex B.3 corrected.** Its `.usda` snippet authored `CesiumGeoreferencePrim`
  through `apiSchemas`, while §5.8, Annex B.1 and B.3's own rendered address
  space describe it as a typed prim. An implementation following the snippet
  produced no portable georeference for the normative shape, silently failing
  the Georeferencing conformance unit. The snippet now matches the normative
  text, with a note that a materializer should recognise either spelling.
- **Two §8.4 clarifications.** The prim fallback is `UsdPrimType` specifically
  (the text said "`UsdPrimType`/`UsdTypedType`", but `UsdTypedType` is abstract
  and cannot be an instance's type definition); and an opaque value shall retain
  the *authored text*, not a host-language rendering of it, or "so an exporter
  reproduces it faithfully" is unachievable.

The `Version`/`PublicationDate` bump exists so a Client can detect these model
changes — `ConnectionPaths` and the concrete `UsdApiSchemaType` were originally
published under the unchanged 0.2.0 identity, which made the two models
indistinguishable.

## 0.2.0 — 2026-07-25

**Geospatial.**

- The portable `UsdGeoreferenceApiType` / `UsdGlobeAnchorApiType` applied API
  schemas (§5.8), since core OpenUSD has no geodetic schema.
- Annex B — the concrete Cesium for Omniverse georeference mapping
  (informative).
- The `Georeferencing` conformance unit.

## 0.1.0 — 2026-07-21

**Introduction.** A native OPC UA materialization of the OpenUSD data model.

- Stage, Prim, Attribute, Relationship, Metadata, composition arcs and
  VariantSets as ObjectTypes, VariableTypes and DataTypes.
- USD IsA schemas mapped to OPC UA ObjectType subtyping; applied API schemas
  mapped to AddIns / Interfaces (§8).
- Bidirectional `.usd` ↔ address-space conversion with the §7.4 round-trip
  contract.
- Two live-data modes (§9): attribute Values updated in place, or retained
  history as time samples.
- Self-contained on base OPC UA — it does not require Part 1.
