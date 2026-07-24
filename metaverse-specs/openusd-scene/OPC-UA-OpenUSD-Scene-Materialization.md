# OPC UA — OpenUSD Scene Materialization (Part 2)

**Release 0.1.0 — Draft**
**Namespace:** `http://opcfoundation.org/UA/OpenUSD/Scene/`
**Publication date:** 2026-07-21

> Status: Working-group draft. This document, together with `Opc.Ua.OpenUsdScene.NodeSet2.xml` and `Opc.Ua.OpenUsdScene.NodeIds.csv`, defines an OPC UA information model that **natively materializes the OpenUSD (Universal Scene Description) data model** — Stage, Prim, Attribute, Relationship, Metadata, Composition arcs, VariantSets, and typed/API schemas — as OPC UA ObjectTypes, VariableTypes, and DataTypes, so that a composed USD scene *is* an OPC UA address space: browsable, subscribable, historizable, and vendor-extensible with native OPC UA semantics. It is **Part 2** of the *OPC UA — OpenUSD* work and **extends** the Part 1 *OPC UA — OpenUSD Bindings* model without changing it. Nothing here is normative, official, or endorsed by the OPC Foundation or the Alliance for OpenUSD; namespace URIs and NodeIds are **provisional** and for prototyping only.

---

## 1 Scope

Part 1 (*OPC UA — OpenUSD Bindings*) declares **which external USD prim represents an OPC UA Object** and **which live Variable values drive which USD attributes**; the USD scene lives outside OPC UA and a connector renders it. Part 2 is complementary and orthogonal: it **brings the USD scene graph into the OPC UA address space** as first-class nodes, so the composed stage can be read, browsed, subscribed, historized, authored, and extended directly over OPC UA, and converted losslessly (for the composed scene) to and from `.usd` files.

The model is **domain-agnostic** and **self-contained**: it depends only on the base OPC UA model (it does **not** require Part 1). It covers:

- **Structure.** A composed **Stage**, its **Prim** namespace hierarchy, each prim's **Attributes** (typed, valued Variables) and **Relationships** (ordered targets, as both references and target-list Variables), prim/stage **Metadata**, applied **API schemas**, **composition arcs**, and **VariantSets**.
- **Typed schemas as OPC UA types.** USD IsA (typed) schemas map to OPC UA **ObjectType subtyping** (`UsdGeomMeshType : UsdGeomGprimType : UsdGeomXformableType : …`); USD applied **API schemas** map to OPC UA **AddIns / Interfaces**. This is the vendor-extension mechanism (§8).
- **Conversion.** A normative, bidirectional mapping between a composed USD stage and this address space (§7), with a **composed-scene round-trip contract**.
- **Live data.** A materialized **Attribute** is an ordinary OPC UA Variable, so time-varying USD attributes (e.g. an `xformOp:rotateZ` driven by process data) are exposed as **live** Variable values and, where retained, as **HistoricalAccess** time samples — and may be driven by, or serve as the target of, Part 1 live bindings (§9).

**Fidelity (normative boundary).** This model materializes the **composed** (resolved) stage as the primary address space, plus **composition-arc and provenance metadata** sufficient to reconstruct the arc structure. It does **not** materialize the per-layer opinion stack (the authoring layer stack, per-layer overrides, and value-clip machinery); those are summarised as provenance metadata. Round-trip is therefore **composed-scene lossless**, not authoring-layer lossless (§7.4).

**Out of scope (reserved):** value clips, per-layer opinion editing, the full UsdShade/UsdLux/UsdSkel/UsdPhysics schema surface (vendor/extension packages), USD `Sdf` layer-file muting/permissions, and the render/materialization semantics of specific renderers.

---

## 2 Normative references

- [OPC 10000-3](https://reference.opcfoundation.org/specs/OPC-10000-3/) — Address Space Model (Object/Variable/DataType/ReferenceType, subtyping, AddIns §4.10.3, Interfaces).
- [OPC 10000-4](https://reference.opcfoundation.org/specs/OPC-10000-4/), [10000-5](https://reference.opcfoundation.org/specs/OPC-10000-5/) — Services and the base information model.
- [OPC 10000-11](https://reference.opcfoundation.org/specs/OPC-10000-11/) — Historical Access (time-sampled attribute values, §9).
- [OPC 10000-7](https://reference.opcfoundation.org/specs/OPC-10000-7/) — Profiles and Conformance Units.
- [AOUSD OpenUSD Core Specification 1.0.1](https://github.com/aousd/specifications-public/blob/2f9e746c4fbd7f48d6d2c9ac568133fe398bbfc0/core/1.0.1/core_spec.md) — normative for USD paths, prims, properties, metadata, composition, variants, and value resolution. **Note:** the Core Specification excludes the domain schemas (UsdGeom, UsdShade, …); the UsdGeom subset materialized here (§5.4) pins a versioned OpenUSD schema release for those type names.
- *OPC UA — OpenUSD Bindings* (Part 1) — the representation/live-binding companion model this document extends (interop in §9, §10).

---

## 3 Terms, definitions and abbreviations

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

---

## 4 Overview and concepts

### 4.1 The materialization

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

The **prim hierarchy is the OPC UA node hierarchy** (`HasComponent`), so browsing the address space is browsing the scene. Attribute Variables carry the resolved value; the exact `SdfValueTypeName` is preserved in a `UsdTypeName` property so nothing is lost even when several USD types share one OPC UA DataType (§6.2).

### 4.2 Two complementary models

| | Part 1 — Bindings | Part 2 — Scene Materialization (this) |
|---|---|---|
| USD scene lives | **outside** OPC UA (external stage) | **inside** OPC UA (materialized) |
| OPC UA carries | *which prim/attr* a value maps to | the *prims/attributes themselves* |
| Consumer | a connector that writes an external stage | a client that reads/browses/subscribes the scene, or exports `.usd` |
| Depends on | base UA | base UA (self-contained) |

The two interoperate (§9, §10): a Part 1 live binding may **target a Part 2 attribute Variable** (so the same process value drives the in-server materialized scene), and a materialized stage may be **listed under Part 1's `Server/OpenUSD/Stages`** for unified discovery — but neither model requires the other.

### 4.3 Discovery

A materialized stage is a `UsdStageType` Object. A Server SHOULD expose its materialized stages as components of a well-known folder — either Part 1's `Server/OpenUSD/Stages` (when Part 1 is also implemented) or, standalone, a `Server/OpenUSDScene/Stages` folder — so a client starts at one entry point and browses `HasComponent` into the prim tree.

---

## 5 Information model

> The complete, generated node reference (every type, member, NodeId, ModellingRule) is **Annex A**, produced from the single source of truth `Opc.Ua.OpenUsdScene.NodeSet2.xml`. This section is the normative narrative; Annex A is authoritative for identifiers.

### 5.1 `UsdStageType : BaseObjectType`

A composed stage. Optional Property members carry stage metadata: `DefaultPrim`, `UpAxis`, `MetersPerUnit`, `KilogramsPerUnit`, `TimeCodesPerSecond`, `StartTimeCode`, `EndTimeCode`, `RootLayerIdentifier`, `Documentation`. Its composed root prims are `HasComponent` children of type `UsdPrimType` (an `<UsdPrim>` `OptionalPlaceholder`).

### 5.2 `UsdPrimType : BaseObjectType`

A prim (an untyped prim or an `over`). Optional Property members: `Specifier` (`UsdSpecifierEnum` — `Def`/`Over`/`Class`), `TypeName` (the schema type token, empty when untyped), `Kind` (`UsdPrimKindEnum`), `Active`, `Instanceable`, `Documentation`. Extensible members (all `OptionalPlaceholder`): child prims `<UsdPrim>` (`UsdPrimType`), attributes `<UsdAttribute>` (`UsdAttributeType`), relationships `<UsdRelationship>` (`UsdRelationshipType`). Optional Folders: `AppliedSchemas`, `Composition`, `VariantSets`, `Metadata`.

### 5.3 Typed prim hierarchy (IsA schemas)

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

A prim of a **known** typed schema is materialized as the matching subtype (its `HasTypeDefinition`), and its `TypeName` property still carries the exact USD `typeName`. A prim of an **unknown** typed schema degrades to `UsdPrimType`/`UsdTypedType` carrying the `TypeName` token — never dropped (§8.4). Vendors add new typed prims by **subtyping** `UsdTypedType` (§8.1).

### 5.4 `UsdAttributeType : BaseDataVariableType` (VariableType)

The materialized attribute. Its `Value` is the resolved attribute value; its DataType/ValueRank are chosen per the value-type map (§6.2) — for a role-carrying USD value type the DataType is the corresponding **semantic subtype of the built-in** (§5.7) so the role is discoverable from the type system. Optional Property members: `UsdTypeName` (the exact `SdfValueTypeName`, e.g. `float3`, `token`, `asset`, `color3f[]`, retained as a fidelity annotation of the precise spelling), `Variability` (`UsdVariabilityEnum`), `Custom`, `Namespace` (property namespace, e.g. `primvars`, `xformOp`), `Interpolation`. Attribute **connections** are expressed as `UsdConnection` references to the connected attribute(s).

### 5.5 `UsdRelationshipType : BaseObjectType`

A relationship. Mandatory `Targets` (ordered `NodeId[]` — the materialized target nodes) and `TargetPaths` (ordered `String[]` — the SdfPath strings, for fidelity when a target is outside the materialized subtree); Optional `Custom`. Each resolved target is **also** linked with a `UsdRelationshipTarget` reference so the relationship is browsable as a graph edge.

### 5.6 Composition, variants, applied schemas

- `UsdCompositionArcType` (under a prim's `Composition/`): `ArcKind` (`UsdArcKindEnum` — `Reference`/`Payload`/`Inherit`/`Specialize`/`VariantSet`/`Sublayer`/`Instance`), `AssetPath`, `PrimPath`, `ListPosition` (`UsdListOpTypeEnum`), `VariantSet`, `VariantSelection`. This records **how** the composed prim came to be, so the arc structure round-trips (§7.4).
- `UsdVariantSetType` (under a prim's `VariantSets/`): `SetName`, `Selection` (the selected variant), and `<Variant>` `OptionalPlaceholder` branches.
- `UsdApiSchemaType : BaseObjectType` (abstract) is the base for **applied API schemas**, applied to a prim via **HasAddIn** under `AppliedSchemas/`. `UsdCollectionAPIType` is a worked example. Vendors add new API schemas by **subtyping** `UsdApiSchemaType` (or as Interfaces, §8.2).

### 5.7 DataTypes and ReferenceTypes

- Enumerations: `UsdSpecifierEnum`, `UsdVariabilityEnum`, `UsdPrimKindEnum`, `UsdListOpTypeEnum`, `UsdArcKindEnum`.
- Semantic subtypes of built-ins — the OPC UA idiom for conveying meaning by **extending a primitive type**, exactly as the standard defines `Duration : Double`, `UtcTime : DateTime`, or `LocaleId : String`. Scalars: `UsdToken : String`, `UsdAssetPath : String`, `UsdTimeCode : Double`. Role-carrying value types: `UsdColor3f`, `UsdNormal3f`, `UsdPoint3f`, `UsdVector3f`, `UsdTexCoord2f`, `UsdQuatf` (all `: Float`) and `UsdQuatd`, `UsdMatrix4d` (both `: Double`). USD's `color3f`, `normal3f`, `point3f` and `vector3f` all decompose to a `Float[3]` and differ **only by role**; giving each its own DataType makes that role discoverable and the mapping reversible from the type system rather than only from the `UsdTypeName` annotation. Each is the **element** DataType of a fixed-length array Variable (§6.2), so the built-in value encoding of the supertype (`Float`/`Double`) is unchanged and remains renderer-friendly. A generic client browses such a Variable as its nearest built-in supertype. Vendors add their own role types the same way (§8.3).
- Structured: `UsdLayerOffset`, `UsdReferenceSpec`, `UsdVariantSelection`.
- ReferenceTypes: `UsdRelationshipTarget` and `UsdConnection` (both `: NonHierarchicalReferences`) — the browsable relationship and connection edges.

---

## 6 Mapping tables (normative)

### 6.1 USD concept → OPC UA node

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
| Composition arc | `UsdCompositionArcType` under `Composition/` |
| VariantSet / selection | `UsdVariantSetType` under `VariantSets/` |
| Specifier / Kind / Variability | `UsdSpecifierEnum` / `UsdPrimKindEnum` / `UsdVariabilityEnum` |

### 6.2 `SdfValueTypeName` → OPC UA DataType + ValueRank

Scalars map to built-ins or, where USD attaches a **role/semantic**, to a DataType that **subtypes the built-in** (the `Duration : Double` idiom, §5.7); fixed-size math types map to fixed-length OPC UA **arrays** (via `ValueRank`/`ArrayDimensions`); arrays add one rank. A role-carrying vector uses its semantic DataType as the array's element type. The exact USD type name is always also preserved in the attribute's `UsdTypeName` property, so the mapping is reversible even where the built-in encoding is many-to-one.

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

### 6.3 Metadata

Well-known prim metadata (`typeName`→`TypeName`, `specifier`→`Specifier`, `kind`→`Kind`, `active`→`Active`, `instanceable`→`Instanceable`, `documentation`→`Documentation`) map to the typed members of §5.2; well-known stage metadata to §5.1. All other metadata (`customData`, `assetInfo`, `comment`, `displayName`, schema-specific keys, …) map to Property Variables under the prim's/stage's `Metadata/` folder, named by the metadata key, with the value carried per §6.2. Nested dictionaries map to nested `Metadata/` folders.

---

## 7 Conversion (`.usd` ↔ address space) (normative)

### 7.1 `.usd` → address space (import / materialize)

1. Open and **compose** the stage. Create a `UsdStageType` and populate its metadata (§5.1).
2. Traverse the composed prim tree depth-first. For each prim, create a `UsdPrimType`(-subtype by `typeName`, §5.3) `HasComponent` under its parent; set `Specifier`/`TypeName`/`Kind`/`Active`/`Instanceable`.
3. For each **attribute**, create a `UsdAttributeType` with DataType/ValueRank/Value/`UsdTypeName`/`Variability`/`Namespace` (§5.4, §6.2); if it has authored connections, add `UsdConnection` references. If it has time samples, materialize the default as `Value` and expose the samples via HistoricalAccess (§9).
4. For each **relationship**, create a `UsdRelationshipType` with ordered `Targets`/`TargetPaths` and `UsdRelationshipTarget` references (§5.5).
5. Record applied API schemas (`AppliedSchemas/`), composition arcs (`Composition/`), variant sets + selection (`VariantSets/`), and remaining metadata (`Metadata/`).

### 7.2 Address space → `.usd` (export)

The inverse: BrowseName → prim/property name; `TypeName` → `def <Type>` (or `over`/`class` per `Specifier`); each `UsdAttributeType` → an attribute (its `UsdTypeName` gives the exact `SdfValueTypeName`; `Value` → default; HistoricalAccess → time samples per a recording profile); `UsdRelationshipType` → a relationship (`TargetPaths`); `Composition/` arcs → `references`/`payloads`/`inherits`/`specializes`/`variantSets`; `VariantSets/` → variant sets and selection; `Metadata/` → metadata. The exported layer is a single **flattened** composed layer unless a provenance-aware exporter reconstructs arcs from `Composition/`.

### 7.3 Reference converter

A reference `usd_to_nodeset` / `nodeset_to_usd` implementation is provided under `metaverse-specs/extras/openusd-scene/tools` (using `usd-core` where available, else a scoped `.usda` reader/writer for the example subset). It regenerates the example nodesets (§11) from the example `.usda` and re-emits `.usda`, with a round-trip check.

### 7.4 Round-trip contract

Import→export is **composed-scene lossless**: the exported composed stage is prim-for-prim, attribute-for-attribute (name, `SdfValueTypeName`, resolved value/array shape), relationship-for-relationship (ordered targets), metadata-for-metadata (well-known + custom), variant-selection-, `kind`- and `specifier`-equivalent to the input's **composed** result, and the recorded composition **arc list** is preserved. It is **not** authoring-layer lossless: the input's per-layer opinion stack, sublayer structure, and value clips are summarised as provenance metadata (`Composition/`, `RootLayerIdentifier`) rather than reproduced layer-by-layer.

---

## 8 Vendor extension (normative)

USD's two schema kinds map to OPC UA's two extension mechanisms:

### 8.1 Typed (IsA) schemas → ObjectType subtyping

A vendor materializes a new typed prim by defining an ObjectType that **subtypes** the closest materialized ancestor (e.g. a robot-joint prim type `: UsdGeomXformableType`, a custom gprim `: UsdGeomGprimType`). Instances use it as their `HasTypeDefinition` and still carry the USD `TypeName` token. A generic client that does not know the subtype browses it as its nearest known supertype — subtyping is transparent to browse.

### 8.2 Applied (API) schemas → AddIns / Interfaces

A vendor materializes a new applied API schema either as an **AddIn** ObjectType (`: UsdApiSchemaType`, applied with `HasAddIn` under `AppliedSchemas/`) or as an **Interface** (`: BaseInterfaceType`, applied with `HasInterface`) when the schema's members should appear inline on the prim. Multiple API schemas compose on one prim exactly as multiple AddIns/Interfaces do.

### 8.3 New value types → DataType subtyping

A vendor adds a USD value type by **subtyping the built-in primitive it decomposes to**, conveying the role in the type system exactly as this model defines `UsdColor3f : Float` or the standard defines `Duration : Double` (§5.7): e.g. a `UsdColor3d : Double` for `color3d`, a `UsdHalf : Float` for a `half`-precision channel, or a `UsdFrustum`-style structured DataType for a compound value. Instances use the new DataType (as the element type of the fixed-length array, for vector roles); a client that does not recognise it reads the built-in supertype. Alternatively a vendor registers a `UsdTypeName` token that maps (per §6.2) to an existing OPC UA DataType. Either way the `UsdTypeName` annotation still records the exact `SdfValueTypeName` for lossless export.

### 8.4 Unknown-type fallback (normative)

An importer that encounters an unknown typed schema, API schema, or value type **shall not drop it**: it degrades the prim to `UsdPrimType`/`UsdTypedType` (carrying `TypeName`), the API schema to a `UsdApiSchemaType` AddIn (carrying `SchemaName`), and the value to an opaque value carrying the `UsdTypeName` — so an exporter reproduces it faithfully and a vendor-aware client can still interpret it.

---

## 9 Live-data mapping (normative, two modes)

A materialized `UsdAttributeType` is an ordinary OPC UA Variable, so USD's static/time-sampled attribute duality maps onto OPC UA's Value/subscription/history surface in **two modes** a Server may mix per attribute:

- **Mode A — live.** The attribute's `Value` is **server-maintained and time-varying**: a Subscription/MonitoredItem delivers changes, and (where the Server retains it) `HistoryRead` (Part 11) exposes the value timeline — the OPC UA counterpart of USD time samples. Time-varying `xformOp`s (an impeller `xformOp:rotateZ`, robot joint angles) and any process-driven attribute use this mode. The Value is driven either by the Server's own logic or by a **Part 1** `OpenUsdValueChangeBinding`/`OpenUsdHistoryBinding` whose **target is this attribute Variable** (§10) — so the same process value that a Part 1 connector would push to an external stage instead (or also) drives the in-server materialized scene.
- **Mode B — static.** The attribute's `Value` is the authored default; it does not change at runtime.

Timecode ↔ wall-clock: USD time codes are stage-timeline ordinates and OPC UA timestamps are wall-clock; they relate only through an explicit epoch and `TimeCodesPerSecond` declared by a recording profile. Absent that, HistoricalAccess samples are on a Server-defined timeline and are informative.

---

## 10 Relationship to Part 1 (informative)

Part 2 is additive and self-contained, but designed to interoperate with Part 1:

- **Binding target.** A Part 1 live binding may resolve its **target** to a Part 2 attribute Variable (by NodeId) instead of an external-stage attribute — the materialized scene becomes the binding sink, and Part 1's discovery/conversion/quality machinery applies unchanged.
- **Binding source.** A Part 2 attribute may be the **source** a Part 1 binding reads (e.g. to mirror the materialized scene onto an external stage).
- **Discovery.** A materialized `UsdStageType` may be organized under Part 1's `Server/OpenUSD/Stages`, so one connector discovers both the external-stage bindings and the in-server materialized stages.
- **Identity.** A Part 1 `OpenUsdRepresentation.PrimPath` and a Part 2 prim node identify the same prim on the same stage, so a client can pivot from an OPC UA domain Object (Pump, Robot axis) to its materialized prim and back.

Neither model requires the other; a Server may implement either alone.

---

## 11 Examples (informative)

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

## 12 Profiles and conformance units

| CU | Requirement |
|---|---|
| **Scene Structure** (base) | Expose materialized stages as `UsdStageType`; materialize the prim tree, attributes (with `UsdTypeName`), and relationships per §5–§6. |
| **Composition Provenance** | Populate `Composition/` arcs and `VariantSets/` per §5.6, §7.4. |
| **Typed Schemas** | Materialize known typed prims as the UsdGeom subtypes of §5.3; unknown → fallback §8.4. |
| **Applied Schemas** | Materialize applied API schemas as AddIns/Interfaces per §5.6, §8.2. |
| **Live Attributes** | Mode-A live attribute Values and, where retained, HistoricalAccess time samples per §9. |
| **Conversion** | Bidirectional `.usd`↔address-space per §7 with the §7.4 round-trip contract. |
| **Part 1 Interop** | Discovery under `Server/OpenUSD/Stages` and Part 1 bindings targeting Part 2 attributes per §10. |

Each CU is independent and additive; a Server implements only what it needs (Scene Structure is the baseline).

---

## Annex A — Information model (generated)

The complete node reference (every ObjectType, VariableType, DataType, ReferenceType, member, ModellingRule and NodeId) is generated from `Opc.Ua.OpenUsdScene.NodeSet2.xml` into `../extras/openusd-scene/tools/model-reference.md` and is authoritative for identifiers.
