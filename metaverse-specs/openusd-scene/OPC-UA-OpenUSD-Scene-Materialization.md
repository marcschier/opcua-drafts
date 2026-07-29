# OPC UA for OpenUSD — Part 2: OpenUSD Scene Materialization

**Release 0.4.0 — Draft**
**Namespace:** `http://opcfoundation.org/UA/OpenUSD/Scene/`
**Publication date:** 2026-07-29

> Status: Working-group draft. This document, together with `Opc.Ua.OpenUsdScene.NodeSet2.xml` and `Opc.Ua.OpenUsdScene.NodeIds.csv`, defines an OPC UA information model that **natively materializes the OpenUSD (Universal Scene Description) data model** — Stage, Prim, Attribute, Relationship, Metadata, Composition arcs, VariantSets, and typed/API schemas — as OPC UA ObjectTypes, VariableTypes, and DataTypes, so that a composed USD scene *is* an OPC UA address space: browsable, subscribable, historizable, and vendor-extensible with native OPC UA semantics. It is **Part 2** of the *OPC UA — OpenUSD* work and **extends** the Part 1 *OPC UA — OpenUSD Bindings* model without changing it. Nothing here is normative, official, or endorsed by the OPC Foundation or the Alliance for OpenUSD; namespace URIs and NodeIds are **provisional** and for prototyping only.

---

## 1 Scope

Part 1 (*OPC UA — OpenUSD Bindings*) declares **which external USD prim represents an OPC UA Object** and **which live Variable values drive which USD attributes**; the USD scene lives outside OPC UA and a connector renders it. Part 2 is complementary and orthogonal: it **brings the USD scene graph into the OPC UA address space** as first-class nodes, so the composed stage can be read, browsed, subscribed, historized, authored, and extended directly over OPC UA, and converted losslessly (for the composed scene) to and from `.usd` files.

The model is **domain-agnostic** and **self-contained**: it depends only on the base OPC UA model (it does **not** require Part 1). It covers:

- **Structure.** A composed **Stage**, its **Prim** namespace hierarchy, each prim's **Attributes** (typed, valued Variables) and **Relationships** (ordered targets, as both references and target-list Variables), prim/stage **Metadata**, applied **API schemas**, **composition arcs**, and **VariantSets**.
- **Typed schemas as OPC UA types.** USD IsA (typed) schemas map to OPC UA **ObjectType subtyping** (`UsdGeomMeshType : UsdGeomGprimType : UsdGeomXformableType : …`); USD applied **API schemas** map to OPC UA **AddIns / Interfaces**. This is the vendor-extension mechanism (§6.7).
- **Conversion.** A normative, bidirectional mapping between a composed USD stage and this address space (§6.6), with a **composed-scene round-trip contract**.
- **Live data.** A materialized **Attribute** is an ordinary OPC UA Variable, so time-varying USD attributes (e.g. an `xformOp:rotateZ` driven by process data) are exposed as **live** Variable values and, where retained, as **HistoricalAccess** time samples — and may be driven by, or serve as the target of, Part 1 live bindings (§11).

**Fidelity (normative boundary).** This model materializes the **composed** (resolved) stage as the primary address space, plus **composition-arc and provenance metadata** sufficient to reconstruct the arc structure. It does **not** materialize the per-layer opinion stack (the authoring layer stack, per-layer overrides, and value-clip machinery); those are summarised as provenance metadata. Round-trip is therefore **composed-scene lossless**, not authoring-layer lossless (§6.6.4).

**Out of scope (reserved):** value clips, per-layer opinion editing, the full UsdShade/UsdLux/UsdSkel/UsdPhysics schema surface (vendor/extension packages), USD `Sdf` layer-file muting/permissions, and the render/materialization semantics of specific renderers.

The release history of this specification is recorded in [`CHANGELOG.md`](CHANGELOG.md).

---

## 2 Normative references

- [OPC 10000-3](https://reference.opcfoundation.org/specs/OPC-10000-3/) — Address Space Model (Object/Variable/DataType/ReferenceType, subtyping, AddIns §4.10.3, Interfaces).
- [OPC 10000-4](https://reference.opcfoundation.org/specs/OPC-10000-4/), [10000-5](https://reference.opcfoundation.org/specs/OPC-10000-5/) — Services and the base information model.
- [OPC 10000-11](https://reference.opcfoundation.org/specs/OPC-10000-11/) — Historical Access (time-sampled attribute values, §6.8).
- [OPC 10000-7](https://reference.opcfoundation.org/specs/OPC-10000-7/) — Profiles and Conformance Units.
- [OPC 10000-210 (RSL)](https://reference.opcfoundation.org/specs/OPC-10000-210) and [OPC 10000-211 (GPOS)](https://reference.opcfoundation.org/specs/OPC-10000-211) — Relative Spatial Location and Global Positioning; the OPC UA relative-pose and global-position source models that the geospatial materialization (§7.6, Annex C) maps to.
- [AOUSD OpenUSD Core Specification 1.0.1](https://github.com/aousd/specifications-public/blob/2f9e746c4fbd7f48d6d2c9ac568133fe398bbfc0/core/1.0.1/core_spec.md) — normative for USD paths, prims, properties, metadata, composition, variants, and value resolution. **Note:** the Core Specification excludes the domain schemas (UsdGeom, UsdShade, …); the UsdGeom subset materialized here (§8.1) pins a versioned OpenUSD schema release for those type names.
- *OPC UA — OpenUSD Bindings* (Part 1) — the representation/live-binding companion model this document extends (interop in §6.8, Annex C).

---

## 3 Terms, abbreviated terms and conventions

### 3.1 Overview

It is assumed that basic concepts of OPC UA information modelling and of OpenUSD are understood in this document. For the purposes of this document, the terms and definitions given in OPC 10000-1, OPC 10000-3, OPC 10000-4, OPC 10000-5 and OPC 10000-7, as well as the following, apply.

OPC UA terms and terms defined in this document are italicized in the document.

### 3.2 OpenUSD scene terms

| Term | Meaning |
|---|---|
| Stage | The fully composed, resolved view of a set of USD layers (materialized here as a `UsdStageType`). |
| Prim | The primary container object in the USD namespace hierarchy (materialized as a `UsdPrimType` or a typed subtype). |
| Property | A prim member: an **Attribute** (typed, valued) or a **Relationship** (ordered targets). |
| Attribute | A typed, valued USD property (materialized as a `UsdAttributeType` Variable). |
| Relationship | A USD property whose value is an ordered list of target paths (materialized as a `UsdRelationshipType`). |
| Typed (IsA) schema | A USD prim type that defines the prim's `typeName` (e.g. `Mesh`); maps to an OPC UA ObjectType subtype. |
| Applied (API) schema | A reusable, applied bundle of properties/metadata (e.g. a Collection); maps to an OPC UA AddIn/Interface. |
| Composition arc | A `reference`/`payload`/`inherits`/`specializes`/`variantSet`/`sublayer`/`instance` edge that composed the stage. |
| SdfPath / prim path | The canonical path of a prim/property, e.g. `/Plant/Pumps/P101.radius`. |
| Composed-scene round-trip | Import→materialize→export producing an equivalent **composed** stage (§7.4). |

### 3.3 Abbreviated terms

| Abbreviation | Term |
|---|---|
| AECO | Architecture, Engineering, Construction and Operations |
| AOUSD | Alliance for OpenUSD |
| API | Application Programming Interface |
| CRS | Coordinate Reference System |
| ECEF | Earth-Centred, Earth-Fixed |
| ENU | East-North-Up |
| EPSG | European Petroleum Survey Group |
| GPOS | Global Positioning |
| IRDI | International Registration Data Identifier |
| RSL | Relative Spatial Location |
| Sdf | Scene Description Foundation |
| URI | Uniform Resource Identifier |
| USD | Universal Scene Description |
| WGS84 | World Geodetic System 1984 |

### 3.4 Conventions used in this document

Node definitions in this document follow the table conventions of the OPC Foundation companion specification template: an Attribute/Value block, a References block giving the ReferenceType, NodeClass, BrowseName, DataType and TypeDefinition of each child Node, and the ConformanceUnits that require the Node in the AddressSpace. The Word rendering of this document carries that clause verbatim from the template.

A BrowseName defined outside this document is prefixed with its namespace index; a BrowseName without a prefix belongs to this document’s namespace. Placeholder InstanceDeclarations are enclosed in angle brackets.

---

## 4 General information to OpenUSD and OPC UA

### 4.1 Introduction to OpenUSD

OpenUSD (Universal Scene Description) is an open, extensible framework for describing, composing, simulating and collaborating on three-dimensional scenes. Its scene graph is assembled from layers that compose into a single stage, so several authors and tools contribute to one scene without rewriting it. A stage is a hierarchy of prims, each carrying typed attributes and relationships, addressed by a canonical prim path.

OpenUSD is governed by the Alliance for OpenUSD (AOUSD), which publishes the OpenUSD Core Specification. The Core Specification covers paths, composition, layers and identity; the domain schemas that describe geometry, materials, lighting, skeletons and physics are versioned separately with the OpenUSD software releases.

### 4.2 Introduction to OPC Unified Architecture

The Word rendering of this document carries the standard OPC UA introduction from the OPC Foundation companion specification template, including its five figures. See OPC 10000-1 for the overview and OPC 10000-3 and OPC 10000-5 for the address space and information model.

---

## 5 Use cases

Two worked examples materialize the Part 1 demo assets as Part 2 address spaces (the generated nodesets are `pumps/Opc.Ua.Pumps.OpenUsdScene.NodeSet2.xml` and `robotics/Opc.Ua.Robotics.OpenUsdScene.NodeSet2.xml`, each `RequiredModel`-ing this Scene model + base UA):

- **Pump / Plant.** The composed **Plant** stage (`Plant.usda`, which references and instances `pump.usda`) materialized as a `UsdStageType` + prim tree (`/Plant`, `/Plant/Pumps/P101`, `Pump`/`Body`/`Impeller`), with a **live** `Impeller` `xformOp:rotateZ` attribute (Mode A, historizing) driven from pump flow, and `UsdCompositionArcType` entries recording the `Reference`/`Instance` aggregation of the pumps.
- **Robot / Cell.** The composed **Cell** stage (`Cell.usda` → `robot.usda` + `tool.usda`) materialized with nested `Xform` joints (`Base`/`J1`…`J6`/`Flange`/`Tool`), **live** joint-rotate attributes (Mode A), and a vendor-extension demo — an applied `UsdCollectionAPIType` (a materialized API schema) attached via `HasAddIn`.

**Reproduce.** The example nodesets are generated from the `.usda` assets by the reference converter and are byte-deterministic:

```text
python metaverse-specs/extras/openusd-scene/tools/regen_examples.py     # (re)generate both example nodesets
python metaverse-specs/extras/openusd-scene/tools/roundtrip_check.py     # export back to .usda and diff (composed-scene equivalent)
python metaverse-specs/validate_all.py --self-contained                 # structural validation (model + examples)
```

---

## 6 OpenUSD scene information model overview

### 6.1 The materialization

A composed USD stage is a tree of prims; each prim has typed attributes, relationships, metadata, applied schemas, composition arcs, and variant sets. Part 2 maps this tree **structurally** onto the OPC UA address space:

```text
UsdStageType  (Server/OpenUSD/Stages/<stage>)
  ├─ (metadata Variables: DefaultPrim, UpAxis, MetersPerUnit, TimeCodesPerSecond, …)
  └─ HasComponent <Prim>  : UsdPrimType / UsdGeom…Type          ← the prim namespace tree
        ├─ (Property Variables: Specifier, TypeName, Kind, Active, …)
        ├─ HasComponent <ChildPrim> : UsdPrimType …             ← nested prims
        ├─ HasComponent <Attribute> : UsdAttributeType          ← typed, valued attributes
        ├─ HasComponent <Relationship> : UsdRelationshipType    ← ordered targets (+ UsdRelationshipTarget refs)
        ├─ AppliedSchemas/  → HasAddIn <ApiSchema> : UsdApiSchemaType
        ├─ Composition/     → <Arc> : UsdCompositionArcType
        ├─ VariantSets/     → <Set> : UsdVariantSetType
        └─ Metadata/        → (metadata Property Variables)
```

The **prim hierarchy is the OPC UA node hierarchy** (`HasComponent`), so browsing the address space is browsing the scene. Attribute Variables carry the resolved value; the exact `SdfValueTypeName` is preserved in a `UsdTypeName` property so nothing is lost even when several USD types share one OPC UA DataType (§6.5.2).

### 6.2 Two complementary models

| | Part 1 — Bindings | Part 2 — Scene Materialization (this) |
|---|---|---|
| USD scene lives | **outside** OPC UA (external stage) | **inside** OPC UA (materialized) |
| OPC UA carries | *which prim/attr* a value maps to | the *prims/attributes themselves* |
| Consumer | a connector that writes an external stage | a client that reads/browses/subscribes the scene, or exports `.usd` |
| Depends on | base UA | base UA (self-contained) |

The two interoperate (§6.8, Annex C): a Part 1 live binding may **target a Part 2 attribute Variable** (so the same process value drives the in-server materialized scene), and a materialized stage may be **listed under Part 1's `Server/OpenUSD/Stages`** for unified discovery — but neither model requires the other.

### 6.3 Discovery

A materialized stage is a `UsdStageType` Object. A Server SHOULD expose its materialized stages as components of a well-known folder — either Part 1's `Server/OpenUSD/Stages` (when Part 1 is also implemented) or, standalone, a `Server/OpenUSDScene/Stages` folder — so a client starts at one entry point and browses `HasComponent` into the prim tree.

### 6.4 Organisation of the model

> The complete, generated node reference (every type, member, NodeId, ModellingRule) is **Annex A**, produced from the single source of truth `Opc.Ua.OpenUsdScene.NodeSet2.xml`. This section is the normative narrative; Annex A is authoritative for identifiers.

### 6.5 Mapping tables

#### 6.5.1 USD concept to OPC UA Node

| USD | OPC UA |
|---|---|
| Stage | `UsdStageType` Object |
| Prim (untyped / `over`) | `UsdPrimType` Object |
| Prim (typed) | subtype of `UsdTypedType` (by `typeName`); unknown → `UsdTypedType`/`UsdPrimType` + `TypeName` |
| Child prim | `HasComponent` to a `UsdPrimType`(-subtype) |
| Attribute | `UsdAttributeType` Variable (`HasComponent`) |
| Relationship | `UsdRelationshipType` Object + `UsdRelationshipTarget` refs |
| Attribute connection | `UsdConnection` reference |
| Prim/stage metadata | Property Variables (well-known ones as typed members; the rest under `Metadata/`) |
| Applied API schema | `UsdApiSchemaType` AddIn (`HasAddIn`) or Interface (`HasInterface`) |
| Georeference / globe anchor (geodetic) | portable `UsdGeoreferenceApiType` / `UsdGlobeAnchorApiType` AddIn (§7.6); a vendor georeference prim → a `UsdTypedType` subtype, a vendor anchor schema → its own `UsdApiSchemaType` subtype |
| Composition arc | `UsdCompositionArcType` under `Composition/` |
| VariantSet / selection | `UsdVariantSetType` under `VariantSets/` |
| Specifier / Kind / Variability | `UsdSpecifierEnum` / `UsdPrimKindEnum` / `UsdVariabilityEnum` |

#### 6.5.2 SdfValueTypeName to OPC UA DataType and ValueRank

Scalars map to built-ins or, where USD attaches a **role/semantic**, to a DataType that **subtypes the built-in** (the `Duration : Double` idiom, §9); fixed-size math types map to fixed-length OPC UA **arrays** (via `ValueRank`/`ArrayDimensions`); arrays add one rank. A role-carrying vector uses its semantic DataType as the array's element type. The exact USD type name is always also preserved in the attribute's `UsdTypeName` property, so the mapping is reversible even where the built-in encoding is many-to-one.

| SdfValueTypeName | DataType | ValueRank / ArrayDimensions |
|---|---|---|
| `bool` | Boolean | Scalar |
| `int`, `uchar`(→SByte), `int64` | Int32 / SByte / Int64 | Scalar |
| `uint`, `uint64` | UInt32 / UInt64 | Scalar |
| `half`,`float` / `double` | Float / Double | Scalar |
| `string` | String | Scalar |
| `token` | `UsdToken` (: String) | Scalar |
| `asset` | `UsdAssetPath` (: String) | Scalar |
| `timecode` | `UsdTimeCode` (: Double) | Scalar |
| `float2/3/4`, `double2/3/4`, `int2/3/4` | Float/Double/Int32 | 1‑D array, `ArrayDimensions=2/3/4` |
| `color3f` / `normal3f` / `point3f` / `vector3f` | `UsdColor3f` / `UsdNormal3f` / `UsdPoint3f` / `UsdVector3f` (: Float) | 1‑D array, `ArrayDimensions=3` |
| `texCoord2f` | `UsdTexCoord2f` (: Float) | 1‑D array, `=2` |
| `quatf` / `quatd` | `UsdQuatf` (: Float) / `UsdQuatd` (: Double) | 1‑D array, `=4` |
| `matrix4d` | `UsdMatrix4d` (: Double) | 1‑D array, `=16` |
| `<T>[]` (any array) | as above, +1 rank | ValueRank +1 |
| anything else | BaseDataType (opaque) + `UsdTypeName` | — |

A **generic** numeric tuple (`float3`, `int2`, …) carries no role beyond its shape, which `ArrayDimensions` already conveys, so it stays a plain built-in array; a `Float[3]` therefore unambiguously means `float3`, while the role variants are distinguished by their semantic DataType. Because these role types subtype a built-in, the value bytes are identical to the plain array form — a client that does not recognise the subtype reads it as `Float[3]`/`Double[16]`, while a role-aware client (a renderer, a material editor) can tell a colour from a point without parsing a string.

#### 6.5.3 Metadata

Well-known prim metadata (`typeName`→`TypeName`, `specifier`→`Specifier`, `kind`→`Kind`, `active`→`Active`, `instanceable`→`Instanceable`, `documentation`→`Documentation`) map to the typed members of §7.2; well-known stage metadata to §7.1. All other metadata (`customData`, `assetInfo`, `comment`, `displayName`, schema-specific keys, …) map to Property Variables under the prim's/stage's `Metadata/` folder, named by the metadata key, with the value carried per §6.5.2. Nested dictionaries map to nested `Metadata/` folders.

### 6.6 Conversion between .usd and the address space

#### 6.6.1 Importing a .usd into the address space

1. Open and **compose** the stage. Create a `UsdStageType` and populate its metadata (§7.1).
2. Traverse the composed prim tree depth-first. For each prim, create a `UsdPrimType`(-subtype by `typeName`, §7.3) `HasComponent` under its parent; set `Specifier`/`TypeName`/`Kind`/`Active`/`Instanceable`.
3. For each **attribute**, create a `UsdAttributeType` with DataType/ValueRank/Value/`UsdTypeName`/`Variability`/`Namespace` (§8.1, §6.5.2); if it has authored connections, add `UsdConnection` references. If it has time samples, materialize the default as `Value` and expose the samples via HistoricalAccess (§6.8).
4. For each **relationship**, create a `UsdRelationshipType` with ordered `Targets`/`TargetPaths` and `UsdRelationshipTarget` references (§7.4).
5. Record applied API schemas (`AppliedSchemas/`), composition arcs (`Composition/`), variant sets + selection (`VariantSets/`), and remaining metadata (`Metadata/`).

#### 6.6.2 Exporting the address space to .usd

The inverse: BrowseName → prim/property name; `TypeName` → `def <Type>` (or `over`/`class` per `Specifier`); each `UsdAttributeType` → an attribute (its `UsdTypeName` gives the exact `SdfValueTypeName`; `Value` → default; HistoricalAccess → time samples per a recording profile); `UsdRelationshipType` → a relationship (`TargetPaths`); `Composition/` arcs → `references`/`payloads`/`inherits`/`specializes`/`variantSets`; `VariantSets/` → variant sets and selection; `Metadata/` → metadata. The exported layer is a single **flattened** composed layer unless a provenance-aware exporter reconstructs arcs from `Composition/`.

#### 6.6.3 Reference converter

A reference `usd_to_nodeset` / `nodeset_to_usd` implementation is provided under `metaverse-specs/extras/openusd-scene/tools` (using `usd-core` where available, else a scoped `.usda` reader/writer for the example subset). It regenerates the example nodesets (§5) from the example `.usda` and re-emits `.usda`, with a round-trip check.

#### 6.6.4 Round-trip contract

Import→export is **composed-scene lossless**: the exported composed stage is prim-for-prim, attribute-for-attribute (name, `SdfValueTypeName`, resolved value/array shape), relationship-for-relationship (ordered targets), metadata-for-metadata (well-known + custom), variant-selection-, `kind`- and `specifier`-equivalent to the input's **composed** result, and the recorded composition **arc list** is preserved. It is **not** authoring-layer lossless: the input's per-layer opinion stack, sublayer structure, and value clips are summarised as provenance metadata (`Composition/`, `RootLayerIdentifier`) rather than reproduced layer-by-layer.

### 6.7 Vendor extension

USD's two schema kinds map to OPC UA's two extension mechanisms:

#### 6.7.1 Typed schemas as ObjectType subtyping

A vendor materializes a new typed prim by defining an ObjectType that **subtypes** the closest materialized ancestor (e.g. a robot-joint prim type `: UsdGeomXformableType`, a custom gprim `: UsdGeomGprimType`). Instances use it as their `HasTypeDefinition` and still carry the USD `TypeName` token. A generic client that does not know the subtype browses it as its nearest known supertype — subtyping is transparent to browse.

A USD-side client, however, cannot interpret such a prim without the corresponding **USD** schema: a `plugInfo.json` manifest plus a `generatedSchema.usda`, the two files OpenUSD's `PlugRegistry`/`UsdSchemaRegistry` need and the only two a codeless schema requires. This Part defines no mechanism for serving files, so it places no requirement on how they are delivered. Where Part 1 is also implemented, a Server **should** publish them through its artifact registry, which defines a schema-plugin group for exactly this purpose (Part 1 §7.13); a client then fetches the plugin from the same registry it fetches layers from, registers it, and reads the materialized scene with the vendor's prim types fully understood instead of degraded to the §6.7.4 fallback. A Server implementing this Part alone may publish them by any out-of-band means, or not at all — in which case a USD-side client falls back to §6.7.4.

#### 6.7.2 Applied schemas as AddIns and Interfaces

A vendor materializes a new applied API schema either as an **AddIn** ObjectType (`: UsdApiSchemaType`, applied with `HasAddIn` under `AppliedSchemas/`) or as an **Interface** (`: BaseInterfaceType`, applied with `HasInterface`) when the schema's members should appear inline on the prim. Multiple API schemas compose on one prim exactly as multiple AddIns/Interfaces do.

#### 6.7.3 New value types as DataType subtyping

A vendor adds a USD value type by **subtyping the built-in primitive it decomposes to**, conveying the role in the type system exactly as this model defines `UsdColor3f : Float` or the standard defines `Duration : Double` (§9): e.g. a `UsdColor3d : Double` for `color3d`, a `UsdHalf : Float` for a `half`-precision channel, or a `UsdFrustum`-style structured DataType for a compound value. Instances use the new DataType (as the element type of the fixed-length array, for vector roles); a client that does not recognise it reads the built-in supertype. Alternatively a vendor registers a `UsdTypeName` token that maps (per §6.5.2) to an existing OPC UA DataType. Either way the `UsdTypeName` annotation still records the exact `SdfValueTypeName` for lossless export.

#### 6.7.4 Unknown-type fallback

An importer that encounters an unknown typed schema, API schema, or value type **shall not drop it**: it degrades the prim to `UsdPrimType` (the concrete base — `UsdTypedType` is abstract and so cannot be an instance's `HasTypeDefinition`) carrying `TypeName`, the API schema to a `UsdApiSchemaType` AddIn (carrying `SchemaName`; this is why that type is concrete, §7.5), and the value to an opaque value carrying the `UsdTypeName` — so an exporter reproduces it faithfully and a vendor-aware client can still interpret it. An opaque value **shall** retain the authored text of the value, not a host-language rendering of it, so that export is byte-faithful.

### 6.8 Live-data mapping

A materialized `UsdAttributeType` is an ordinary OPC UA Variable, so USD's static/time-sampled attribute duality maps onto OPC UA's Value/subscription/history surface in **two modes** a Server may mix per attribute:

- **Mode A — live.** The attribute's `Value` is **server-maintained and time-varying**: a Subscription/MonitoredItem delivers changes, and (where the Server retains it) `HistoryRead` (Part 11) exposes the value timeline — the OPC UA counterpart of USD time samples. Time-varying `xformOp`s (an impeller `xformOp:rotateZ`, robot joint angles) and any process-driven attribute use this mode. The Value is maintained by the **Server** — either by its own logic, or by applying a **Part 1** `OpenUsdValueChangeBinding`/`OpenUsdHistoryBinding` whose **target is this attribute Variable** (Annex C, via `TargetNodeId` or the resolved target path) — so the same process value that a Part 1 connector would push to an external stage instead (or also) drives the in-server materialized scene. Note that an *external* Part 1 connector authors into a USD sink and cannot write this Variable; Mode A is therefore a Server-side responsibility.
- **Mode B — static.** The attribute's `Value` is the authored default; it does not change at runtime.

Timecode ↔ wall-clock: USD time codes are stage-timeline ordinates and OPC UA timestamps are wall-clock; they relate only through an explicit epoch and `TimeCodesPerSecond` declared by a recording profile. Absent that, HistoricalAccess samples are on a Server-defined timeline and are informative.

---

## 7 OPC UA ObjectTypes

### 7.1 UsdStageType

A composed stage. Optional Property members carry stage metadata: `DefaultPrim`, `UpAxis`, `MetersPerUnit`, `KilogramsPerUnit`, `TimeCodesPerSecond`, `StartTimeCode`, `EndTimeCode`, `RootLayerIdentifier`, `Documentation`. Its composed root prims are `HasComponent` children of type `UsdPrimType` (an `<UsdPrim>` `OptionalPlaceholder`).

### 7.2 UsdPrimType

A prim (an untyped prim or an `over`). Optional Property members: `Specifier` (`UsdSpecifierEnum` — `Def`/`Over`/`Class`), `TypeName` (the schema type token, empty when untyped), `Kind` (`UsdPrimKindEnum`), `Active`, `Instanceable`, `Documentation`. Extensible members (all `OptionalPlaceholder`): child prims `<UsdPrim>` (`UsdPrimType`), attributes `<UsdAttribute>` (`UsdAttributeType`), relationships `<UsdRelationship>` (`UsdRelationshipType`). Optional Folders: `AppliedSchemas`, `Composition`, `VariantSets`, `Metadata`.

### 7.3 UsdTypedType

`UsdTypedType : UsdPrimType` (abstract) is the base of all typed prims. The materialized **UsdGeom** subset (a versioned schema release, §2):

```text
UsdTypedType
 ├─ UsdGeomImageableType         (Visibility, Purpose)
 │   ├─ UsdGeomScopeType
 │   └─ UsdGeomXformableType     (XformOpOrder)
 │        ├─ UsdGeomXformType
 │        └─ UsdGeomGprimType    (DisplayColor, DisplayOpacity, DoubleSided)
 │             ├─ UsdGeomMeshType     (Points, FaceVertexCounts, FaceVertexIndices)
 │             ├─ UsdGeomCylinderType (Height, Radius, Axis)
 │             ├─ UsdGeomSphereType   (Radius)
 │             ├─ UsdGeomCubeType     (Size)
 │             ├─ UsdGeomConeType     (Height, Radius, Axis)
 │             └─ UsdGeomCapsuleType  (Height, Radius, Axis)
 ├─ UsdShadeMaterialType
 └─ UsdShadeShaderType           (Info_Id)
```

A prim of a **known** typed schema is materialized as the matching subtype (its `HasTypeDefinition`), and its `TypeName` property still carries the exact USD `typeName`. A prim of an **unknown** typed schema degrades to `UsdPrimType`/`UsdTypedType` carrying the `TypeName` token — never dropped (§6.7.4). Vendors add new typed prims by **subtyping** `UsdTypedType` (§6.7.1).

### 7.4 UsdRelationshipType

A relationship. Mandatory `Targets` (ordered `NodeId[]` — the materialized target nodes) and `TargetPaths` (ordered `String[]` — the SdfPath strings, for fidelity when a target is outside the materialized subtree); Optional `Custom`. Each resolved target is **also** linked with a `UsdRelationshipTarget` reference so the relationship is browsable as a graph edge.

### 7.5 UsdCompositionArcType

- `UsdCompositionArcType` (under a prim's `Composition/`): `ArcKind` (`UsdArcKindEnum` — `Reference`/`Payload`/`Inherit`/`Specialize`/`VariantSet`/`Sublayer`/`Instance`), `AssetPath`, `PrimPath`, `ListPosition` (`UsdListOpTypeEnum`), `VariantSet`, `VariantSelection`. This records **how** the composed prim came to be, so the arc structure round-trips (§6.6.4).
- `UsdVariantSetType` (under a prim's `VariantSets/`): `SetName`, `Selection` (the selected variant), and `<Variant>` `OptionalPlaceholder` branches.
- `UsdApiSchemaType : BaseObjectType` is the base for **applied API schemas**, applied to a prim via **HasAddIn** under `AppliedSchemas/`. `UsdCollectionAPIType` is a worked example. It is deliberately **concrete**, because §6.7.4 requires an unknown applied schema to degrade to a `UsdApiSchemaType` AddIn carrying its `SchemaName` — an Object cannot take an abstract ObjectType as its `HasTypeDefinition`. Vendors add new API schemas by **subtyping** `UsdApiSchemaType` (or as Interfaces, §6.7.2).

### 7.6 UsdGeoreferenceApiType

USD places prims in a **local** Cartesian stage frame and defines no geodetic (latitude/longitude) schema in its Core Specification. A georeferenced stage — one anchored to real-world global coordinates — is therefore expressed today through **applied API schemas** provided by extensions (NVIDIA `omni.usd.schema.geospatial`, Cesium for Omniverse). This model materializes those schemas through the ordinary vendor-extension mechanism (§6.7): a georeference/anchor API schema materializes as a `UsdApiSchemaType` AddIn under a prim's `AppliedSchemas/` (§6.7.2), and a georeference *prim* type (e.g. Cesium's `CesiumGeoreferencePrim`) materializes as a `UsdTypedType` subtype (§6.7.1). The concrete Cesium mapping is given in **Annex C**.

To give a client a **vendor-neutral** anchor it can read without knowing which extension authored the stage, this model additionally defines two portable applied API schemas:

- **`UsdGeoreferenceApiType : UsdApiSchemaType`** — a stage-level georeference origin: `Latitude`, `Longitude` (decimal degrees), `Height` (metres above the ellipsoid), `EpsgCode` (EPSG CRS; 0 = local, 4326 = WGS84/GPS), `TangentPlane` (e.g. `ENU`). Applied via `HasAddIn` to the stage's root/anchor prim.
- **`UsdGlobeAnchorApiType : UsdApiSchemaType`** — a per-prim geodetic position (`Latitude`, `Longitude`, `Height`) resolved against the stage `UsdGeoreferenceApiType`. Applied to any placed prim.

A materializer that recognises a vendor georeference schema **should** additionally populate the portable schema (dual-authoring the same values), so a generic client obtains the anchor from one well-known type while a vendor-aware client still reads the native schema.

**Bridge to the OPC UA spatial companion specs.** The portable georeference corresponds directly to the OPC UA global- and relative-positioning models:

| Portable georeference | OPC UA source (OPC 10000-210 / 211) |
|---|---|
| `UsdGeoreferenceApiType` origin (`Latitude`/`Longitude`/`Height`/`EpsgCode`) | GPOS `GlobalPositionType` at a reference point / `ZoneType` |
| `UsdGlobeAnchorApiType` per-prim position | a per-asset GPOS `GlobalPosition` |
| origin ↔ local frame (the tangent-plane transform) | GPOS `GroundControlPointDataType` (local XYZ ↔ global lat/lon) |
| a placed prim's `UsdGeomXformable` transform ops | RSL `CartesianFrameAngleOrientationType` (`3DFrame`); see the Bindings spec §7.4.2 and Bindings spec Annex F |

Latitude/longitude are decimal degrees, height/elevation metres; a non-WGS84 `EpsgCode` is reprojected before authoring. USD's stage `upAxis` and `metersPerUnit` do **not** auto-reconcile with a geodetic frame; the materializer records them on the `UsdStageType` (§7.1) and the tangent-plane convention on the georeference so a consumer can compose the correct local↔global transform.

### 7.7 `UsdGeomImageableType`

Abstract USD imageable prim base.

### 7.8 `UsdGeomXformableType`

Abstract USD xformable prim base.

### 7.9 `UsdGeomXformType`

USD Xform prim.

### 7.10 `UsdGeomScopeType`

USD Scope prim.

### 7.11 `UsdGeomGprimType`

Abstract USD geometric prim base.

### 7.12 `UsdGeomMeshType`

USD Mesh prim.

### 7.13 `UsdGeomCylinderType`

USD Cylinder prim.

### 7.14 `UsdGeomSphereType`

USD Sphere prim.

### 7.15 `UsdGeomCubeType`

USD Cube prim.

### 7.16 `UsdGeomConeType`

USD Cone prim.

### 7.17 `UsdGeomCapsuleType`

USD Capsule prim.

### 7.18 `UsdShadeMaterialType`

USD Shade material prim hook.

### 7.19 `UsdShadeShaderType`

USD Shade shader prim hook.

### 7.20 `UsdVariantSetType`

USD variant set materialization.

### 7.21 `UsdApiSchemaType`

Base for applied USD API schema AddIns. Concrete, because §6.7.4 requires an unknown applied schema to degrade to a UsdApiSchemaType AddIn carrying its SchemaName rather than being dropped; vendors still subtype it (§6.7.2).

### 7.22 `UsdCollectionAPIType`

USD CollectionAPI applied API schema.

### 7.23 `UsdGlobeAnchorApiType`

Portable per-prim globe anchor applied API schema: the geodetic position of an individual prim, resolved against the stage UsdGeoreferenceApiType. Vendor-neutral materialization of Cesium CesiumGlobeAnchorAPI / NVIDIA WGS84LocalPositionAPI; maps to a per-asset OPC UA GPOS GlobalPosition.

---

## 8 OPC UA VariableTypes

The materialized attribute. Its `Value` is the resolved attribute value; its DataType/ValueRank are chosen per the value-type map (§6.5.2) — for a role-carrying USD value type the DataType is the corresponding **semantic subtype of the built-in** (§9) so the role is discoverable from the type system. Optional Property members: `UsdTypeName` (the exact `SdfValueTypeName`, e.g. `float3`, `token`, `asset`, `color3f[]`, retained as a fidelity annotation of the precise spelling), `Variability` (`UsdVariabilityEnum`), `Custom`, `Namespace` (property namespace, e.g. `primvars`, `xformOp`), `Interpolation`, and `ConnectionPaths` (ordered `String[]`). Attribute **connections** are expressed as `UsdConnection` references to the connected attribute(s), and — exactly as `UsdRelationshipType` pairs `Targets` with `TargetPaths` (§7.4) — the ordered `ConnectionPaths` carry the authored SdfPath strings. Both are needed: a connection whose target lies outside the materialized subtree has no node to point at, so without `ConnectionPaths` it could not be exported, and the reference set alone does not preserve authored order.

An attribute may carry a **default value and a connection at once**; a materializer shall retain both.

### 8.1 `UsdAttributeType`

USD attribute value variable. The runtime DataType and ValueRank reflect the composed Sdf value type.

---

## 9 OPC UA DataTypes

- Enumerations: `UsdSpecifierEnum`, `UsdVariabilityEnum`, `UsdPrimKindEnum`, `UsdListOpTypeEnum`, `UsdArcKindEnum`.
- Semantic subtypes of built-ins — the OPC UA idiom for conveying meaning by **extending a primitive type**, exactly as the standard defines `Duration : Double`, `UtcTime : DateTime`, or `LocaleId : String`. Scalars: `UsdToken : String`, `UsdAssetPath : String`, `UsdTimeCode : Double`. Role-carrying value types: `UsdColor3f`, `UsdNormal3f`, `UsdPoint3f`, `UsdVector3f`, `UsdTexCoord2f`, `UsdQuatf` (all `: Float`) and `UsdQuatd`, `UsdMatrix4d` (both `: Double`). USD's `color3f`, `normal3f`, `point3f` and `vector3f` all decompose to a `Float[3]` and differ **only by role**; giving each its own DataType makes that role discoverable and the mapping reversible from the type system rather than only from the `UsdTypeName` annotation. Each is the **element** DataType of a fixed-length array Variable (§6.5.2), so the built-in value encoding of the supertype (`Float`/`Double`) is unchanged and remains renderer-friendly. A generic client browses such a Variable as its nearest built-in supertype. Vendors add their own role types the same way (§6.7.3).
- Structured: `UsdLayerOffset`, `UsdReferenceSpec`, `UsdVariantSelection`.
- ReferenceTypes: `UsdRelationshipTarget` and `UsdConnection` (both `: NonHierarchicalReferences`) — the browsable relationship and connection edges.

---

## 10 OPC UA ReferenceTypes

### 10.1 `UsdRelationshipTarget`

Browsable relationship edge from a prim or relationship to its target prim.

### 10.2 `UsdConnection`

Browsable USD attribute-connection edge.

---

## 11 Profiles and conformance units

| CU | Requirement |
|---|---|
| **OUS-SceneStructure** (base) | Expose materialized stages as `UsdStageType`; materialize the prim tree, attributes (with `UsdTypeName`), and relationships per §6.4–§6.5. |
| **OUS-CompositionProvenance** | Populate `Composition/` arcs and `VariantSets/` per §7.5, §6.6.4. |
| **OUS-TypedSchemas** | Materialize known typed prims as the UsdGeom subtypes of §7.3; unknown → fallback §6.7.4. |
| **OUS-AppliedSchemas** | Materialize applied API schemas as AddIns/Interfaces per §7.5, §6.7.2. |
| **OUS-Georeferencing** | Materialize georeference/globe-anchor API schemas per §7.6 — the portable `UsdGeoreferenceApiType`/`UsdGlobeAnchorApiType`, and vendor schemas (Cesium/NVIDIA) as AddIns/typed prims per §6.7 (Annex C). |
| **OUS-LiveAttributes** | Mode-A live attribute Values and, where retained, HistoricalAccess time samples per §6.8. |
| **OUS-Conversion** | Bidirectional `.usd`↔address-space per §6.6 with the §6.6.4 round-trip contract. |
| **OUS-Part1Interop** | Discovery under `Server/OpenUSD/Stages` and Part 1 bindings targeting Part 2 attributes per Annex C. |

Each CU is independent and additive; a Server implements only what it needs (`OUS-SceneStructure` is the baseline). The `OUS` prefix is the short name of this specification, so a conformance unit identifier is unique across companion specifications.

---

## 12 Namespaces

### 12.1 Namespace metadata

The namespace metadata provide standardized information about the elements of this namespace, which an aggregating Server relies on. All Nodes defined by this document are static.

| Property | DataType | Value |
|---|---|---|
| NamespaceUri | String | `http://opcfoundation.org/UA/OpenUSD/Scene/` |
| NamespaceVersion | String | 0.4.0 |
| NamespacePublicationDate | DateTime | 2026-07-29 |
| IsNamespaceSubset | Boolean | False |
| StaticNodeIdTypes | IdType[] | 0 (Numeric) |
| StaticNumericNodeIdRange | NumericRange[] | 1001:9999 |
| StaticStringNodeIdPattern | String | -- |

### 12.2 Handling of OPC UA namespaces

Namespaces are used by OPC UA to create unique identifiers across different naming authorities. The following namespaces are used for BrowseNames in this document; the default namespace is not listed, because every BrowseName without a prefix uses it.

| NamespaceURI | Namespace index | Example |
|---|---|---|
| `http://opcfoundation.org/UA/` | 0 | `0:EngineeringUnits` |
| `http://opcfoundation.org/UA/xRegistry/` | 1 | `1:ResourceType` |

---

## Annex A (normative) — OpenUSD scene namespace and mappings

The complete node reference (every ObjectType, VariableType, DataType, ReferenceType, member, ModellingRule and NodeId) is generated from `Opc.Ua.OpenUsdScene.NodeSet2.xml` into `../extras/openusd-scene/tools/model-reference.md` and is authoritative for identifiers.

---

## Annex B (informative) — Relationship to Part 1

Part 2 is additive and self-contained, but designed to interoperate with Part 1:

- **Binding target.** A Part 1 live binding may resolve its **target** to a Part 2 attribute Variable instead of an external-stage attribute — the materialized scene becomes the binding sink, and Part 1's discovery/conversion/quality machinery applies unchanged. Part 1 carries this two ways: the optional `TargetNodeId` names the materialized `UsdAttributeType` Variable directly, and the mandatory `TargetStage`/`TargetPrimPath`/`TargetPropertyName` triple resolves to the same Variable by BrowseName path (with `TargetStage` naming this model's `UsdStageType`). A Server **should** author both so path-resolving and NodeId-resolving connectors agree.
- **Binding source.** A Part 2 attribute may be the **source** a Part 1 binding reads (e.g. to mirror the materialized scene onto an external stage).
- **Discovery.** A materialized `UsdStageType` may be organized under Part 1's `Server/OpenUSD/Stages`, so one connector discovers both the external-stage bindings and the in-server materialized stages.
- **Identity.** A Part 1 `OpenUsdRepresentation.PrimPath` and a Part 2 prim node identify the same prim on the same stage, so a client can pivot from an OPC UA domain Object (Pump, Robot axis) to its materialized prim and back.
- **Artifacts.** Part 1 serves USD content from an **xRegistry artifact registry** at `Server/OpenUSD/Artifacts` (Part 1 §7.11). Part 2 does **not** take that dependency: it is base-UA-only and reaches the registry only *indirectly*, when a Server implements both. Where it does, a materialized stage's `RootLayerIdentifier` (§7.1) is the asset identifier of the registry artifact whose `AssetKind` is `RootLayer` — and because Part 1 makes an artifact's registry `ResourceId` the URL-safe encoding of that identifier (Part 1 §7.11.3), the stage's authored bytes are located by computation rather than by search. A Part 2 Server with no Part 1 registry treats `RootLayerIdentifier` as an opaque provenance string.
- **Who drives Mode A.** A Part 1 *connector* authors into a USD sink and cannot write an in-server Variable; driving a materialized attribute's `Value` (§6.8 Mode A) is therefore a **Server-side** responsibility — a Part 1 binding declares the mapping, the Server (or a server-hosted connector) applies it.

Neither model requires the other; a Server may implement either alone.

---

## Annex C (informative) — Concrete Cesium for Omniverse georeference mapping

Core OpenUSD has no geodetic schema, and the Alliance for OpenUSD's native geolocation schema (an [AECO Interest Group proposal to the Geometry Working Group](https://aousd.org/news/alliance-for-openusd-announces-new-members-interest-groups-and-working-group-progress/), tracked in the [OpenUSD-proposals](https://github.com/PixarAnimationStudios/OpenUSD-proposals) repository) is, as of this draft, still in progress and unratified. Georeferencing today is therefore done with extension schemas. This annex shows exactly how a **Cesium for Omniverse** georeferenced stage materializes and how it relates to the portable georeference schemas of §7.6. Cesium georeferences a stage with a `CesiumGeoreferencePrim` (a typed prim) and anchors individual prims with the `CesiumGlobeAnchorAPI` (an applied API schema).

### C.1 CesiumGeoreferencePrim as a UsdTypedType subtype

A vendor typed prim materializes as an ObjectType subtyping `UsdTypedType` (§6.7.1); its attributes materialize as `UsdAttributeType` Variables (§8.1):

| Cesium USD attribute | SdfValueTypeName | Materialized as |
|---|---|---|
| `cesium:anchor:latitude` | `double` | `UsdAttributeType` (Double), `UsdTypeName = "double"` |
| `cesium:anchor:longitude` | `double` | `UsdAttributeType` (Double) |
| `cesium:anchor:height` | `double` | `UsdAttributeType` (Double) |
| `ecefToUsdTransform` (read-only) | `matrix4d` | `UsdAttributeType` (`UsdMatrix4d`, `Double[16]`) |

### C.2 CesiumGlobeAnchorAPI as a UsdApiSchemaType AddIn

An applied API schema materializes as a `UsdApiSchemaType` AddIn under the prim's `AppliedSchemas/` (§6.7.2, §7.5):

| Cesium USD attribute | SdfValueTypeName | Materialized as |
|---|---|---|
| `cesium:anchor:latitude` | `double` | `UsdAttributeType` (Double) on the AddIn |
| `cesium:anchor:longitude` | `double` | `UsdAttributeType` (Double) |
| `cesium:anchor:height` | `double` | `UsdAttributeType` (Double) |

The materializer **should** also apply the portable `UsdGlobeAnchorApiType` carrying the same `Latitude`/`Longitude`/`Height`, so a generic client reads the anchor without Cesium-specific knowledge (§7.6).

### C.3 Worked example

```usda
#usda 1.0
( upAxis = "Z"  metersPerUnit = 1.0 )

def CesiumGeoreferencePrim "World" {
    double cesium:anchor:latitude  = 47.6062
    double cesium:anchor:longitude = -122.3321
    double cesium:anchor:height    = 56.0

    def Xform "AGV_07" ( prepend apiSchemas = ["CesiumGlobeAnchorAPI"] ) {
        double cesium:anchor:latitude  = 47.6061
        double cesium:anchor:longitude = -122.3319
        double cesium:anchor:height    = 56.0
    }
}
```

`CesiumGeoreferencePrim` is a **typed prim** (§6.7.1) and `CesiumGlobeAnchorAPI` an **applied API schema** (§6.7.2), so they are authored differently — the first as the prim's `typeName`, the second in `apiSchemas`. A materializer **should** nevertheless recognise a georeference declared either way, since stages in the wild author `CesiumGeoreferencePrim` through `apiSchemas` as well; the portable dual-authoring of §7.6 applies in both cases.

materializes as (abbreviated address space):

```text
World : UsdCesiumGeoreferencePrimType (: UsdTypedType)          # vendor typed prim (§6.7.1)
  ├─ cesium:anchor:latitude   : UsdAttributeType = 47.6062
  ├─ cesium:anchor:longitude  : UsdAttributeType = -122.3321
  ├─ cesium:anchor:height     : UsdAttributeType = 56.0
  ├─ AppliedSchemas/ → HasAddIn UsdGeoreferenceApiType          # portable dual-author (§7.6)
  │     Latitude=47.6062  Longitude=-122.3321  Height=56.0  EpsgCode=4326  TangentPlane="ENU"
  └─ HasComponent AGV_07 : UsdGeomXformType
        └─ AppliedSchemas/
              ├─ HasAddIn UsdCesiumGlobeAnchorAPIType (: UsdApiSchemaType)   # vendor (§6.7.2)
              │     cesium:anchor:latitude=47.6061 …
              └─ HasAddIn UsdGlobeAnchorApiType                              # portable (§7.6)
                    Latitude=47.6061  Longitude=-122.3319  Height=56.0
```

### C.4 Round-trip

Export reproduces the vendor schema names (`CesiumGeoreferencePrim`, `CesiumGlobeAnchorAPI`) and attribute values from the materialized nodes; the portable `UsdGeoreferenceApiType` / `UsdGlobeAnchorApiType` AddIns are additive provenance that need not be re-emitted to `.usd` (they carry no opinion the vendor schema does not). The georeference round-trip is therefore composed-scene lossless per §6.6.4, with the local↔global transform recovered from the vendor schema (or recomputed from the portable origin plus the stage `metersPerUnit`/`upAxis`).
