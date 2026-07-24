# OPC UA — WoT Connectivity

**Release 1.1.0 — Draft (additive revision of OPC 10100-1 v1.02)**
**Namespace:** `http://opcfoundation.org/UA/WoT-Con/`
**Publication date:** 2026-07-22

> Status: Working-group draft, intended for submission to the **OPC Foundation Web of Things (WoT) Working Group**. This document, together with the generated `Opc.Ua.WoTCon.NodeSet2.xml` and `Opc.Ua.WoTCon.NodeIds.csv`, defines an **additive revision 1.1** of the OPC UA companion specification for W3C Web of Things (WoT) connectivity. It is **registry-first**: it layers a W3C Thing Model / Thing Description **document registry** over the abstract [OPC UA — xRegistry](../../core-specs/xregistry/OPC-UA-xRegistry.md) base model and treats the stored documents and their versions as the single source of truth from which the OPC UA AddressSpace and any code-behind are **derived**. Revision 1.1 keeps the published `http://opcfoundation.org/UA/WoT-Con/` namespace and **incorporates the full OPC 10100-1 v1.02 model into one combined NodeSet**, preserving every published NodeId, type and method signature and marking the superseded 1.02 management surface `Deprecated`. It can be read on its own. Nothing here is official or endorsed by the OPC Foundation or the W3C; the numeric NodeIds of the additive `64000+` registry block are provisional and final identifiers are assigned by the OPC Foundation.

---

## 1 Scope

This specification defines **WoT Connectivity 1.1**: an OPC UA information model and normative behaviour for a server that stores, validates, versions and **projects** W3C Web of Things documents. It is an **additive revision** of OPC 10100-1 v1.02 published in the same namespace `http://opcfoundation.org/UA/WoT-Con/`.

- A **Thing Model** (WoT-TM/1.1) describes a reusable class of Things; this specification projects it to OPC UA **types**.
- A **Thing Description** (WoT-TD/1.1) describes a concrete Thing instance; this specification projects it to OPC UA **instances** whose interaction affordances are bound to protocol bindings.

The registry files and versions are canonical. The AddressSpace that a client browses — types from Thing Models, instances from Thing Descriptions, References from links, and monitored values driven by binder plans built from forms — is a **derived projection** that a server refreshes, atomically and idempotently, from the stored documents.

This specification **incorporates** the published OPC 10100-1 v1.02 WoT Connectivity model (namespace `http://opcfoundation.org/UA/WoT-Con/`, model version 1.02.0) into the **same combined NodeSet and namespace**. Every published NodeId (`1..172`), type, method signature and the well-known `WoTAssetConnectionManagement` object is preserved exactly (§13). Because the additive registry supersedes the flat asset-management surface, the 1.02 management and upload types are marked **deprecated** (`ReleaseStatus="Deprecated"`, following OPC 11030) — deprecated, not removed, so existing 1.02 clients keep working unchanged. This is a single combined model in one namespace, not a separate namespace and not a dual profile.

Out of scope: the WoT vocabulary itself (defined by the revised [OPC UA — WoT Binding](../WoT-Binding/OPC-UA-WoT-Binding.md) JSON-LD vocabulary, a normative dependency of this specification), the xRegistry document/API semantics (defined by [OPC UA — xRegistry](../../core-specs/xregistry/OPC-UA-xRegistry.md)), and the concrete wire protocols of individual W3C binding templates.

## 2 Normative and informative references

- [OPC 10000-3](https://reference.opcfoundation.org/specs/OPC-10000-3/) — Address Space Model (model change, NodeVersion, DataTypes, References).
- [OPC 10000-5](https://reference.opcfoundation.org/specs/OPC-10000-5/) — Information Model (BaseObjectType, FolderType, PropertyType, BaseEventType, GeneralModelChangeEventType, structures).
- [OPC 10000-20](https://reference.opcfoundation.org/specs/OPC-10000-20/) — File Transfer (FileType).
- [OPC 11030](https://reference.opcfoundation.org/) — Compatibility and versioning rules for OPC UA information models (applied in §7.10 and §13).
- [OPC 10100-1 v1.02](https://reference.opcfoundation.org/specs/OPC-10100-1/) — the published WoT Connectivity baseline incorporated and preserved in §13.
- [OPC UA — xRegistry](../../core-specs/xregistry/OPC-UA-xRegistry.md) — the abstract registry base model this specification extends (RequiredModel).
- [OPC UA — WoT Binding](../WoT-Binding/OPC-UA-WoT-Binding.md) — the `uav` JSON-LD vocabulary and NodeSet↔WoT mapping (normative vocabulary dependency; not a NodeSet RequiredModel).
- [W3C WoT Thing Description 1.1](https://www.w3.org/TR/wot-thing-description11/) and [WoT Binding Templates](https://www.w3.org/TR/wot-binding-templates/).
- [WoT Registry (xRegistry WoT extension) 1.0-rc](https://github.com/varunpuranik/xregistry_spec/blob/WoT1/wot/spec.md) — the WoT document-registry model reconciled here (`thingdescriptiongroups`/`thingdescriptions`, `thingmodelgroups`/`thingmodels`, formats `WoT-TD/1.1` / `WoT-TM/1.1`).
- [xRegistry 1.0-rc3](https://github.com/xregistry/spec) — the core registry document/API specification.

## 3 Terms, definitions, and conventions

### 3.1 Normative keywords

The key words **shall**, **shall not**, **should**, **should not**, **may** and **optional** are used as defined in the OPC UA specifications. **shall** and **shall not** are absolute requirements; **should**/**should not** are strong recommendations; **may**/**optional** denote freedom.

### 3.2 Abbreviations

- **TD** — WoT Thing Description; **TM** — WoT Thing Model.
- **Affordance** — a WoT interaction affordance: a property, action or event.
- **Form** — a WoT `forms` entry binding an affordance to a protocol endpoint.
- **Projection** — the derived AddressSpace (and code-behind) materialized from stored documents.
- **Generation** — a monotonically increasing counter identifying one committed projection state of the registry.
- **Closure** — a document together with the transitive set of documents it depends on (the dependency DAG reachable from it).
- **Binder** — the component that turns a form into an executable read/write/observe/invoke/subscribe plan for a specific protocol binding.

### 3.3 Terms

- **Canonical document** — a stored TD or TM version; the authoritative source of truth. Everything a client browses is derived from it.
- **Desired version** vs **active version** — the version an operator wants projected vs the version whose projection is currently serving.
- **Shadow generation** — a fully materialized but not-yet-visible projection built beside the active one and switched in atomically.
- **Incorporated 1.02 model** — the published OPC 10100-1 v1.02 nodes, preserved unchanged in this combined NodeSet at their published NodeIds and marked `Deprecated` (§13).

## 4 Overview and architecture

This version of the WoT Connectivity specification is organised around a single principle: **the registry is the source of truth; the AddressSpace is a cache of it.** A server ingests TDs and TMs as registry documents, validates and versions them with xRegistry semantics, resolves their dependency graph, and **projects** the valid closure into OPC UA nodes. Clients interact with those projected nodes exactly as they would with any OPC UA model; the registry additionally exposes the documents, their lifecycle state, and a `Refresh` control surface.

```mermaid
graph TD
  subgraph canonical["Sources of truth (canonical)"]
    R[WoTRegistry i=64100]
    TDG[ThingDescriptionGroup]
    TMG[ThingModelGroup]
    TDF[ThingDescriptionFile - TD bytes]
    TMF[ThingModelFile - TM bytes]
    R --> TDG --> TDF
    R --> TMG --> TMF
  end
  subgraph derived["Derived projection (code-behind)"]
    OT[ObjectType / VariableType]
    OBJ[Object instance]
    VARS[Variables / Methods / EventTypes]
    BIND[Binder plans from forms]
  end
  TMF -- TM to types --> OT
  TDF -- TD to instances --> OBJ
  OBJ --> VARS
  VARS -- forms --> BIND
  TDF -. links rel=type .-> TMF
  R -- HasWoTProjection --> OBJ
  R -- Refresh / generation --> VARS
```

**Layering.** This specification reuses the abstract xRegistry base (`RegistryType`/`GroupType`/`ResourceType`, namespace index 1) and adds, in the same own namespace (index 2) that carries the incorporated 1.02 model, the WoT-specific subtypes, DataTypes, events and the well-known `WoTRegistry` object. The WoT vocabulary that governs how a document maps to nodes is the `uav` JSON-LD vocabulary of the revised [OPC UA — WoT Binding](../WoT-Binding/OPC-UA-WoT-Binding.md); it is a **normative dependency but not a NodeSet RequiredModel**, because it is a JSON-LD vocabulary, not an OPC UA information model.

**Relationship to OPC 10100-1 v1.02.** The published v1.02 asset-management surface (`WoTAssetConnectionManagement`, the asset types and the `WoTFile`/`CloseAndUpdate` upload flow) is incorporated into the same NodeSet and namespace and remains callable, but is marked `Deprecated`: it is a special, flat case of the general registry, and §13 records how it is backed by the registry without any signature change. New deployments use the registry surface directly.

**Separation of concerns.** Routing/lifecycle metadata (load state, generation, desired/active version, validation outcomes, content digest, selected bindings) lives on the registry and document nodes; the *semantic* mapping of affordances to nodes is carried by the stored document and the `uav` vocabulary. This mirrors the xRegistry separation of registry metadata from resource content.

## 5 Namespace, model dependencies, and NodeId allocation

- **NamespaceUri:** `http://opcfoundation.org/UA/WoT-Con/` — the **same** namespace as the published OPC 10100-1 v1.02 baseline. Revision 1.1 is additive within this one namespace; there is no separate `V2/` namespace.
- **Namespace order in the NodeSet:** index 0 Core (`http://opcfoundation.org/UA/`), index 1 xRegistry (`http://opcfoundation.org/UA/xRegistry/`), index 2 this specification (which carries both the incorporated 1.02 nodes and the additive registry nodes).
- **RequiredModels:** Core (`1.05.04`) and xRegistry (`0.1.0`). The WoT Binding vocabulary is **not** a RequiredModel.
- **NodeId allocation:** the incorporated OPC 10100-1 v1.02 nodes keep their exact published numeric identifiers `1..172` (preserved from the pinned `legacy/WotConnection.csv`; reserved ids stay reserved). The additive registry nodes use a dedicated **64000+** block for types (ObjectTypes, event types, DataTypes and the reference type), with member declarations (properties, methods, arguments, enum strings, encodings and the well-known instance) allocated **append-only** from **64500**. The 64000 block was chosen to avoid the preserved 1.02 range (`1..172`) and the ranges already used by sibling drafts in this repository (Generators `1001-6xxx`, Schema Registry `62000`, xRegistry `63000`) and does not overlap any published OPC Foundation range. Because member allocation is append-only in source order, new declarations shall only be added at the end of their block; reordering or inserting declarations renumbers many nodes and is prohibited without an explicit NodeId-impact review.

The generated artifacts are the normative machine-readable form: `Opc.Ua.WoTCon.NodeSet2.xml`, `Opc.Ua.WoTCon.NodeIds.csv` and the Annex A reference (`tools/model-reference.md`), all emitted deterministically by `tools/build_model.py` from the in-code registry model and the pinned legacy sources under `legacy/`. They shall not be hand-edited.

## 6 Information model

This section defines each information-model concept the additive registry introduces: **what** it is, **where** it appears in the AddressSpace, **why** it exists, and **how** it is used. Every type links to its normative node reference in [Annex A](#annex-a). Annex A also documents the incorporated 1.02 legacy types (§13). All registry NodeIds are provisional.

### 6.1 Registry root — `WoTRegistryType`

**What.** [`WoTRegistryType`](#type-WoTRegistryType) (`i=64000`) is the registry root type, a subtype of the abstract xRegistry [`RegistryType`](../../core-specs/xregistry/OPC-UA-xRegistry.md#type-RegistryType) (itself a `FolderType`). **Where.** It is instantiated once as the well-known `WoTRegistry` object under the `Server` object (§6.7). **Why.** It is the single entry point from which a client discovers every stored Thing Model and Thing Description and controls their projection. **How.** It holds the two group placeholders `<ThingDescriptionGroup>` / `<ThingModelGroup>` and adds registry-wide lifecycle state (`RefreshGeneration`, `AutoRefresh`, `RefreshMode`, `RefreshInterval`, `LastRefreshTime`, `LastRefreshSummary`, `DefaultAtomicity`, `DeletePolicy`), validation policy (`ValidateFormat`, `ValidateCompatibility`, `StrictValidation`, `VocabularyVersion`), the binding surface (`SupportedBindings`, `SelectedBindings`) and the `Refresh` Method (§9). A client browses `Server → WoTRegistry`, reads `RefreshGeneration` to learn the current projection generation, and calls `Refresh` to re-project on demand.

### 6.2 Groups — `ThingDescriptionGroupType` and `ThingModelGroupType`

**What.** [`ThingDescriptionGroupType`](#type-ThingDescriptionGroupType) (`i=64001`) and [`ThingModelGroupType`](#type-ThingModelGroupType) (`i=64002`) are xRegistry [`GroupType`](../../core-specs/xregistry/OPC-UA-xRegistry.md#type-GroupType) subtypes. **Where.** Instances appear directly under the registry, one group per related set of documents (for example one group per site or per vendor catalog). **Why.** Groups are the unit of organisation, access control and policy: read access to a group is the authorisation boundary for discovering the Things it contains (§7.11). **How.** Each group carries the group-level validation policy (`ValidateFormat`, `ValidateCompatibility`, `ConsistentFormat`) and a constrained `<ThingDescription>` / `<ThingModel>` placeholder that limits its members to the matching document subtype. A Thing Description group holds only Thing Descriptions; a Thing Model group holds only Thing Models.

### 6.3 Documents — `WoTDocumentType`, `ThingDescriptionFileType`, `ThingModelFileType`

**What.** [`WoTDocumentType`](#type-WoTDocumentType) (`i=64003`, **abstract**) is the base of a stored WoT document, a subtype of the xRegistry [`ResourceType`](../../core-specs/xregistry/OPC-UA-xRegistry.md#type-ResourceType). [`ThingDescriptionFileType`](#type-ThingDescriptionFileType) (`i=64004`) and [`ThingModelFileType`](#type-ThingModelFileType) (`i=64005`) are the concrete subtypes. **Where.** Document instances are the members of the groups. **Why.** The document *is* the canonical source of truth; everything a client browses in the projection is derived from these bytes and their versions. **How.** Because `ResourceType` is a `FileType`, the JSON-LD document bytes are read and written with the inherited `Open`/`Read`/`Write`/`Close` Methods, so a client fetches the exact stored TD/TM. `WoTDocumentType` adds the derived-projection metadata (`DocumentKind`, `Enabled`, `LoadState`, `DesiredVersionId`, `ActiveVersionId`, `IsDefault`, `Ancestor`, `Compatibility`, `AutoRefresh`, `RefreshGeneration`, `LastRefreshTime`, `ContentDigest`, `ValidationOutcome`, `MaterializedNodeCount`, `RootNodeId`, `SelectedBindings`) and the `Validate` / `SetEnabled` / `SetDefaultVersion` Methods. `ThingDescriptionFileType` adds the TD instance identity (`ThingId`, `ThingTitle`, `BaseUri`, `ModelReference`); `ThingModelFileType` adds the TM type identity (`ModelTitle`, `ModelVersion`, `DerivedTypeNodeId`). For example, after a Thing Model is projected, a client reads `ThingModelFileType.DerivedTypeNodeId` to find the ObjectType it produced.

### 6.4 Bindings — `WoTBindingType`

**What.** [`WoTBindingType`](#type-WoTBindingType) (`i=64006`) is a browseable protocol-binding descriptor. **Where.** The registry's `SupportedBindings` folder holds one `WoTBindingType` object per protocol binding the server can realise (OPC UA, HTTP, Modbus, …). **Why.** It lets a client discover which W3C binding templates the server supports, at which pinned document version and maturity, before relying on a form. **How.** Its `BindingUri`, `Title`, `ProfileVersion`, `DraftMaturity`, `Enabled`, `ContentTypes` and a `Capabilities` snapshot are individual, browseable nodes. Immutable *snapshots* of the selected binding set are additionally exposed as arrays of [`WoTBindingCapabilityDataType`](#type-WoTBindingCapabilityDataType) (`SelectedBindings`, on the registry and on each document). Browseable policy/identity is always exposed as Objects/Properties; arrays are used **only** for immutable snapshots. No credentials or secrets are ever exposed on a binding node.

### 6.5 DataTypes

**What.** The model defines eight enumerations and seven structures. **Where.** They type the Properties, method arguments and event fields above. **Why.** The enumerations give lifecycle and outcome values a stable, machine-readable meaning; the structures package related, versioned facts as a single immutable snapshot. **How.** The enumerations are [`WoTDocumentKindEnum`](#type-WoTDocumentKindEnum), [`WoTLoadStateEnum`](#type-WoTLoadStateEnum), [`WoTRefreshModeEnum`](#type-WoTRefreshModeEnum), [`WoTAtomicityEnum`](#type-WoTAtomicityEnum), [`WoTDeletePolicyEnum`](#type-WoTDeletePolicyEnum), [`WoTOutcomeEnum`](#type-WoTOutcomeEnum), [`WoTPhaseEnum`](#type-WoTPhaseEnum) and [`WoTBindingCapabilityEnum`](#type-WoTBindingCapabilityEnum). The structures — [`WoTValidationOutcomeDataType`](#type-WoTValidationOutcomeDataType), [`WoTBindingCapabilityDataType`](#type-WoTBindingCapabilityDataType), [`WoTRefreshOptionsDataType`](#type-WoTRefreshOptionsDataType), [`WoTResourceSelectorDataType`](#type-WoTResourceSelectorDataType), [`WoTResourceLoadResultDataType`](#type-WoTResourceLoadResultDataType), [`WoTRefreshSummaryDataType`](#type-WoTRefreshSummaryDataType) and [`WoTDependencyDataType`](#type-WoTDependencyDataType) — are each an **immutable versioned snapshot**, read as a single Variant and never mutated in place; each carries `Default Binary` and `Default JSON` encodings. `examples/04-refresh-results.json` (§12) shows the two refresh structures populated.

### 6.6 Events and the notifier chain

**What.** [`WoTResourceEventType`](#type-WoTResourceEventType) (`i=64010`, **abstract**, subtype of `BaseEventType`) is the common WoT resource event, carrying the affected identity (`Xid`, `ResourceId`, `VersionId`), `DocumentKind`, `Generation`, `Phase` and `Outcome`. Its concrete failure subtypes are [`WoTValidationFailureEventType`](#type-WoTValidationFailureEventType) (`i=64011`), [`WoTLoadFailureEventType`](#type-WoTLoadFailureEventType) (`i=64012`) and [`WoTBindingFailureEventType`](#type-WoTBindingFailureEventType) (`i=64013`); [`WoTRefreshCompletedEventType`](#type-WoTRefreshCompletedEventType) (`i=64014`) carries the `Summary` and committed `Generation`. **Where.** The failing **resource** is the source of a failure event; the **registry** is the source of the refresh-completed event. **Why.** Events let an operator observe validation, projection and binding problems and refresh completion without polling. **How.** The notifier chain is **Server → WoTRegistry → groups → resources**: the well-known `WoTRegistry` object declares `EventNotifier = SubscribeToEvents` and is a `HasNotifier` target of the `Server` object (`i=2253`); groups are `HasNotifier` targets of the registry and resources of their group. A subscriber on `WoTRegistry` therefore receives every failure event raised by any contained resource and the refresh-completed event raised by the registry itself.

### 6.7 Reference type and projection correlation — `HasWoTProjection`

**What.** [`HasWoTProjection`](#type-HasWoTProjection) (`i=64060`, subtype of `NonHierarchicalReferences`, inverse `WoTProjectionOf`). **Where.** It links a stored document resource (source) to the root node of its derived projection (target). **Why.** It lets a client navigate in both directions — find the projected node behind a document and the document behind a projected node — and it anchors `NodeVersion` correlation (§7.9). **How.** After a Thing Description is projected to an Object, the resource carries `HasWoTProjection` to that Object; browsing the inverse `WoTProjectionOf` from any projected node reaches its canonical document.

### 6.8 Well-known registry instance — `WoTRegistry`

**What.** `WoTRegistry` (`i=64100`, type definition `WoTRegistryType`). **Where.** It is a `HasComponent` of the `Server` object (`i=2253`). **Why.** A fixed, well-known location makes the registry discoverable without configuration, exactly as the incorporated 1.02 `WoTAssetConnectionManagement` object is discoverable under `Objects`. **How.** The generated NodeSet materialises the instance with a functional `Refresh` Method and concrete Values for every Mandatory member (own and inherited), so loading the NodeSet alone yields a structurally complete, callable registry; a server binds the concrete handlers.

## 7 Registry semantics and lifecycle (normative)

### 7.1 Canonical files, derived projection

The stored TD/TM files and their versions are canonical. The projected AddressSpace and any generated code-behind are **derived**: a server shall be able to rebuild them entirely from the stored documents, the pinned `uav` vocabulary version and the registry's model, without any additional hidden state. A client shall not rely on projected nodes surviving a change to the underlying document except as governed by the generation and retirement rules below.

### 7.2 Projection mapping

A valid document is projected using the `uav` JSON-LD vocabulary defined by the revised [OPC UA — WoT Binding](../WoT-Binding/OPC-UA-WoT-Binding.md); that specification is the normative source for how each `uav` term maps to an OPC UA construct, and this section applies it:

- A **Thing Model** projects to a **type**: `uav:objectType` → an `ObjectType`, `uav:variableType` → a `VariableType`; its affordances become **member declarations** with the declared modelling rule (`uav:modellingRule`), unit (`uav:unitProperty` / QUDT), scaling (`uav:scaleFactor`, `uav:decimalPlaces`) and grouping (`uav:memberOf`, `uav:propertyGroups`/`eventGroups`/`actionGroups`). The materialized type NodeId is exposed as `ThingModelFileType.DerivedTypeNodeId`.
- A **Thing Description** projects to an **instance**: `uav:object` → an `Object` whose affordances become **Variables** (properties), **Methods** (actions) and **event sources** (events → subtypes of an event type, per the TD's `uav:eventType`/`uav:isEvent`/`data`).
- **Affordances** map to nodes as above; **links** map to OPC UA **References** (`uav:componentModel` → `HasComponent`, a ReferenceType compact model name used directly in `rel` → that typed Reference with `uav:refType` as fallback, `uav:reference`/`uav:capability` → non-hierarchical references, `uav:componentOf` → the parent `HasComponent` of §7.3) or, when no native reference fits, to an explicit link representation carried on the projected node.
- **Forms** do not become nodes; each form is compiled into a **binder plan** (§8) that the server executes to read/write/observe/invoke/subscribe the affordance over the form's protocol binding.

### 7.3 Placement and parent selection (no mandatory flat root)

This specification **shall not** impose a mandatory flat "Assets" root as a container for every projected instance; the authored hierarchy and references of the stored documents determine where each Thing appears.

A Thing Description author selects the parent under which its projected Object is exposed by adding a WoT `links` entry with the relation **`rel: uav:componentOf`** (defined by the WoT Binding vocabulary, [§6.2](../WoT-Binding/OPC-UA-WoT-Binding.md)). The relation is directional: `uav:componentOf` states that *this* Thing is a component of the **linked** resource, so the link target is the intended **parent** (container). The link `href` **shall** identify the parent in one of three ways, and the materializer **shall** resolve it in this order:

1. another document in the same registry (a relative/registry href, resolved to that document's projection root in the committed generation);
2. an existing AddressSpace node, given as an OPC UA `NodeId` or a `uav:browsePath`;
3. the projection root of the Thing Model the TD derives from (a self-reference to the type instance owner), when the href names it.

When the parent resolves, the materializer **shall** create a forward OPC UA `HasComponent` reference from the resolved parent node to the projected Object (equivalently an inverse `HasComponent` from the Object to its parent). When a `uav:componentOf` link is present but its target cannot be resolved within the committed generation, the document's projection **shall** fail (`LoadState = Failed`, `WoTLoadFailureEventType`, `Phase = Projection`) rather than silently falling back. When no `uav:componentOf` link is present, the projected Object **shall** be `Organizes`d directly under the `Objects` folder. A server **shall not** require, and clients **shall not** assume, any additional convenience container.

### 7.4 Dependency graph construction and closure atomicity

Documents form a **dependency DAG**. A refresh **shall** construct this graph before projecting: a Thing Description depends on the Thing Models it derives from (`links rel=type`) and on any parent it references (`links rel=uav:componentOf`, §7.3); a Thing Model depends on the Thing Models it extends or references (`tm:extends`, `tm:ref`). Each resolved and unresolved edge **shall** be recorded as a `WoTDependencyDataType` (`SourceXid`, `TargetXid`, `TargetUri`, `RefType`, `Resolved`) so the closure is inspectable. A document together with its transitive dependencies is a **closure**.

A refresh **shall** reject a graph that is not a DAG: if a cycle is detected (for example two Thing Models that `tm:extends` each other), the affected documents **shall** be reported `Failed` with `Phase = DependencyResolution` and a `WoTLoadFailureEventType`, and **shall not** be projected. When the applied atomicity is `PerClosure` or coarser, the whole closure **shall** be projected into a shadow generation and committed together or not at all: a closure with any unresolved or invalid dependency **shall not** be partially activated — no node of that closure becomes visible. When the applied atomicity is `PerResource`, an independent resource with no unresolved dependency **may** commit even if an unrelated resource in the same refresh fails.

*Example.* Refreshing `pump-01` (which `links rel=type` to `PumpType`) with `Atomicity = PerClosure` activates the pair `{pump-01, PumpType}` atomically; if `PumpType` is missing, neither is projected and `pump-01` is reported `Failed` with an unresolved `WoTDependencyDataType` edge.

### 7.5 Invalid documents and desired-versus-active divergence

Validation failure **shall not** destroy data. An invalid document (format or compatibility) **shall** remain stored; its `LoadState` **shall** become `Failed`, its `ValidationOutcome` **shall** record the failing phase and reason, and a `WoTValidationFailureEventType` **shall** be raised from the resource. The **previously active valid projection of that resource shall remain active and unchanged**: a refresh that would activate an invalid document **shall** instead keep the prior committed generation of that closure serving.

`DesiredVersionId` records the version an operator wants projected; `ActiveVersionId` records the version currently serving. They **may** differ transiently during a switch. When the desired version is invalid, they **shall** diverge persistently — the last valid active version keeps serving while `DesiredVersionId` points at the rejected version — and this divergence **shall** be observable so operator tooling can surface it. A server **shall not** silently activate a desired version that fails validation.

### 7.6 Shadow prepare, switch, drain and retire

Projection **shall** be generational and use a shadow-then-switch discipline so a client never observes a half-built model. A refresh **shall** proceed through the phases of `WoTPhaseEnum`: it **prepares** the new nodes as a **shadow generation** beside the active one (`LoadState = Loading`), validates and binds them, then **switches atomically** to make them visible (`LoadState = Active`) and increments `RefreshGeneration`. The superseded generation **shall not** be deleted immediately: it **shall** enter `Superseded`, then `Retiring`, and **shall** be retired (`Retired`) only **after its monitored items and subscriptions have drained** onto the new generation, so active subscriptions are not disrupted by the switch. Concretely, a server **shall** migrate or settle monitored items against the new nodes before removing the old nodes; this drain-then-retire approach follows the behaviour validated in [PR #4015](https://github.com/OPCFoundation/UA-.NETStandard/pull/4015). The number of generations retired **shall** be reported in the refresh summary (`WoTRefreshSummaryDataType.Retired`).

```mermaid
stateDiagram-v2
  [*] --> Unloaded
  Unloaded --> Loading: prepare shadow generation
  Loading --> Active: atomic switch (RefreshGeneration++)
  Loading --> Failed: validation/projection error
  Active --> Superseded: newer generation switched in
  Superseded --> Retiring: begin drain
  Retiring --> Retired: monitored items drained
  Failed --> Loading: corrected document refreshed
```

### 7.7 Automatic and explicit refresh; idempotence

The registry **shall** support both automatic and explicit refresh. When `AutoRefresh` is true, the registry **shall** re-project per `RefreshMode`: `Periodic` on each `RefreshInterval`, `EventDriven` on a stored-document change (a write or, for a legacy asset, `CloseAndUpdate`), or `Scheduled` on an implementation-defined schedule. The `Refresh` Method (§9) **shall** re-project a selection on demand regardless of `AutoRefresh`.

A refresh **shall** be idempotent: a document whose `ContentDigest` is unchanged since its last projection at the current `VocabularyVersion` **shall** be reported `Unchanged` and **shall not** be re-materialized, unless `Options.Force` is set. Re-running an unchanged refresh **shall** produce the same active generation and the same node set (no NodeId churn, no `RefreshGeneration` increment). A server **should** compute `ContentDigest` over the canonical document bytes so that semantically insignificant reformatting does not force re-projection.

### 7.8 Version switch, unload, delete and federation

- **Version switch.** Setting `DesiredVersionId` (or calling `SetDefaultVersion`) and refreshing **shall** shadow-switch the resource's projection to the selected version per §7.6; the prior generation **shall** retire only after drain. Live subscriptions on the switched nodes **shall not** lose notifications across the switch.
- **Unload.** `SetEnabled(false)` **shall** request unloading the projection while keeping the stored document. Dependents **shall** be treated per the effective `DeletePolicy`: `Reject` **shall** refuse the operation while any loaded document still depends on the resource; `Retire` **shall** retire the projection but keep the document resolvable for dependents; `Cascade` **shall** unload dependents that resolve only through this document; `Force` **shall** unload the projection even while dependents remain, marking those dependents `Failed`.
- **Delete.** The inherited xRegistry `Delete` **shall** remove the stored resource/version; its projection **shall** be retired first, subject to the same `DeletePolicy`.
- **Federation.** A document **may** be served by reference through the inherited xRegistry `ExternalReference` (`ExpandedNodeId`) / `ResourceUrl`. A server **shall** resolve and project a federated document the same way as a local one, and a federated Thing Model **may** satisfy a local Thing Description's dependency closure. A federated dependency that cannot be resolved **shall** be reported as an unresolved `WoTDependencyDataType` edge and handled as in §7.4.

*Example.* Unloading `PumpType` with `DeletePolicy = Reject` while `pump-01` still depends on it is rejected; retrying with `Cascade` unloads `pump-01`'s projection first, then `PumpType`'s.

### 7.9 Model change events and NodeVersion correlation

A committed generation switch changes the AddressSpace graph. The server shall emit OPC UA **model change events** (`GeneralModelChangeEventType`) for the committed node additions/removals/reference changes, and shall stamp affected nodes' `NodeVersion` so a client can correlate a node's version with the `RefreshGeneration` that produced it (the `HasWoTProjection` reference ties the node back to its document). Model change events are emitted for **committed** graph changes only — never for shadow-generation scratch work.

### 7.10 Semantic change events (optional)

When a refresh changes the *meaning* of a type or instance (for example a DataType, EngineeringUnit or semantic identifier changes in a way governed by the Part 3/Part 5 model-change rules and the OPC 11030 compatibility rules), the server MAY additionally emit an OPC UA **semantic change event** (`SemanticChangeEventType`) for the affected nodes. Concrete subtypes of the abstract model/semantic change event types are defined only where required for emission; this specification relies on the Core types unless a WoT-specific subtype is needed.

### 7.11 Security

Fetching a document's `@context`, external JSON schemas and federated referents shall use transport security and honour the registry's configured trust; credentials for those fetches and for protocol-binding endpoints are held out of band and **never** exposed on registry or binding nodes (binding nodes carry policy and identity only). Management Methods (`Refresh`, `Validate`, `SetEnabled`, `SetDefaultVersion`, and the inherited xRegistry create/delete Methods) are subject to OPC UA role-based access control; read access to a group MAY be restricted to authorise discovery of the Things it contains. Operators should be aware that a TD can expose device endpoints and security schemes and should scope group read access accordingly.

## 8 Protocol binder (normative)

The **binder** turns a form into an executable plan. It has a protocol-independent **core** and a set of **per-binding** modules.

- **Core:** parses a form, resolves its `href` against the TD `base`, selects the binding by the form's protocol vocabulary, maps the WoT `op` set to OPC UA service semantics (readproperty→Read, writeproperty→Write, observeproperty→MonitoredItem, invokeaction→Call, subscribeevent→event MonitoredItem), and produces a plan whose capabilities are recorded in the document's `SelectedBindings` snapshot.
- **Per-binding:** each W3C binding template (OPC UA, HTTP, Modbus, MQTT, CoAP, …) is a module advertised as a `WoTBindingType` with its `Capabilities` (`WoTBindingCapabilityEnum` set) and content types.
- **Version pinning and maturity:** each binding is pinned to a specific W3C binding-document version (`ProfileVersion`) and exposes that document's **draft maturity** (`DraftMaturity`: WD/CR/PR/REC). A server shall bind a form only with a binding whose pinned document it implements, and shall surface the maturity so consumers can judge stability. A form that names an unknown binding or an operation the binding does not support raises a `WoTBindingFailureEventType`.

## 9 Refresh Method and results (normative)

### 9.1 Purpose and use cases

`Refresh` is the control surface that (re-)derives the AddressSpace projection from the canonical documents. It exists because the projection is a *cache*: whenever the documents, their versions, or the pinned vocabulary change, the cache must be rebuilt deterministically and atomically. An implementer should treat `Refresh` as the single funnel through which every projection change flows, whether triggered explicitly or automatically (§7.7). Typical use cases are: **initial load** of a newly ingested Thing Model or Thing Description; **version switch** to a newly published version; **repair** after a previously failed document is corrected; **dry-run planning** to preview what a refresh would do before committing; and **forced re-projection** after a vocabulary-version change even though document bytes are unchanged.

### 9.2 Signature

`WoTRegistryType.Refresh(Selection, Options, ExpectedGeneration, RequestId) → (Summary, Results, NewGeneration)`:

- **Selection** — an array of `WoTResourceSelectorDataType`; an empty array selects the whole registry. Selectors filter by kind, group, resource, version or a single `Xid`.
- **Options** — `WoTRefreshOptionsDataType`: `Atomicity`, `Force`, `DryRun`, `IncludeDependents`, `DeletePolicy`, `MaxParallelism`, `Timeout`.
- **ExpectedGeneration** — optimistic concurrency: if non-zero and unequal to `RefreshGeneration`, the call **shall** fail `Bad_InvalidState` and change nothing.
- **RequestId** — echoed into `Summary.RequestId` and the completion event for correlation.
- **Summary** — a `WoTRefreshSummaryDataType`: overall outcome, applied atomicity, counts (total/succeeded/unchanged/failed/skipped/retired), timing and the committed generation.
- **Results** — an array of `WoTResourceLoadResultDataType`, one per considered resource: identity, kind, per-resource outcome and phase, resulting load state, generation, materialized-node count and root, content digest and a message.
- **NewGeneration** — the committed generation; unchanged on a dry run or a full failure.

### 9.3 Caller workflow

A typical caller: (1) reads `RefreshGeneration` to capture the current generation; (2) calls `Refresh` with a `Selection`, `Options.DryRun = true` and `ExpectedGeneration` set to the captured value to obtain a plan (`Summary`/`Results`) without changing anything; (3) inspects the predicted per-resource outcomes; (4) calls `Refresh` again with `DryRun = false` and the same `ExpectedGeneration` to commit. Steps 1 and 4 make the operation safe under concurrency: if another refresh committed in between, the generation no longer matches and the commit fails without effect, so the caller re-plans against the new generation.

### 9.4 Validation, planning and apply algorithm

On each invocation the server **shall**:

1. **Check concurrency.** If `ExpectedGeneration` is non-zero and ≠ `RefreshGeneration`, fail `Bad_InvalidState`, change nothing.
2. **Select.** Expand `Selection` to a resource set; an empty `Selection` selects the whole registry. If `Options.IncludeDependents`, add every document that transitively depends on a selected document.
3. **Fetch and parse.** For each selected document, fetch its bytes and referenced `@context`/schemas (`Phase = Fetch`/`Parse`).
4. **Validate.** Perform format and, when enabled, compatibility validation (`Phase = FormatValidation`/`CompatibilityValidation`), recording a `WoTValidationOutcomeDataType`. An invalid document is marked `Failed` and excluded from projection; its prior active projection is retained (§7.5).
5. **Resolve dependencies.** Build the dependency DAG (§7.4) and group the valid documents into closures; a cyclic or unresolved-dependency closure is failed at `Phase = DependencyResolution`.
6. **Plan.** For each document, compare `ContentDigest` and vocabulary version against the last projection; unchanged documents are marked `Unchanged` and skipped unless `Options.Force`.
7. **Project (shadow).** Materialize the changed closures into a shadow generation (`Phase = Projection`, `LoadState = Loading`), honouring `MaxParallelism`. If `Options.DryRun`, stop here and report the plan without committing.
8. **Activate.** Switch the shadow generation in atomically at the granularity of `Options.Atomicity` (`Phase = Activation`), increment `RefreshGeneration`, emit Core model change events (§7.9), and stamp `NodeVersion`.
9. **Retire.** Move superseded generations to `Superseded`/`Retiring` and retire them after monitored items drain (`Phase = Retirement`, §7.6).
10. **Summarize.** Populate `Summary`/`Results`, cache `Summary` as `LastRefreshSummary`, set `LastRefreshTime`, and raise `WoTRefreshCompletedEventType`.

### 9.5 Concurrency and generation behaviour

Concurrent `Refresh` calls **shall** be serialized with respect to committing a generation: at most one generation switch is in flight at a time. `RefreshGeneration` **shall** increment by exactly one per committed switch and **shall not** change on a dry run, a full failure, or an all-`Unchanged` refresh. Because a caller can pin `ExpectedGeneration`, a lost update is impossible: a stale plan cannot overwrite a newer generation.

### 9.6 Outcomes, errors and implementer responsibilities

`DryRun` **shall** validate and compute `Summary`/`Results` without committing any projection change. `Validate` (on a document) performs format/compatibility validation only and returns a `WoTValidationOutcomeDataType`. A per-resource `Outcome` is one of `Success`, `Unchanged`, `Warning`, `Skipped`, `Rejected` or `Failed`; a document that fails **shall** carry the failing `Phase` and a human-readable `Message`. A partial failure under `PerResource` atomicity **shall** leave successful resources committed and failed resources on their prior generation; a failure under `PerClosure`/`PerRegistry` atomicity **shall** leave the whole unit uncommitted. Implementers are responsible for: making the whole operation restartable (a crash mid-refresh must not leave a half-switched generation); ensuring idempotence via `ContentDigest`; and never destroying a stored document or a last-valid projection because of a refresh error. A representative populated result set is `examples/04-refresh-results.json` (§12.4).

### 9.7 Refresh sequence

```mermaid
sequenceDiagram
  actor Op as Operator/Client
  participant R as WoTRegistry (Refresh)
  participant V as Validator
  participant P as Projector (shadow)
  participant AS as AddressSpace
  Op->>R: Refresh(Selection, Options, ExpectedGeneration, RequestId)
  R->>R: check ExpectedGeneration == RefreshGeneration
  alt mismatch
    R-->>Op: Bad_InvalidState (no change)
  else match
    R->>V: fetch, parse, validate selected documents
    V-->>R: WoTValidationOutcome per document
    R->>R: resolve dependency DAG -> closures
    R->>P: materialize changed closures (shadow generation)
    alt DryRun
      P-->>R: predicted node counts / roots
      R-->>Op: Summary + Results (NewGeneration unchanged)
    else commit
      P->>AS: atomic switch (Atomicity), RefreshGeneration++
      AS-->>R: model change events, NodeVersion stamped
      R->>AS: drain monitored items, retire superseded generation
      R-->>Op: Summary + Results + NewGeneration
      R->>Op: WoTRefreshCompletedEventType
    end
  end
```

## 10 Events and change notifications (normative)

Events let an operator observe the registry without polling; an implementer should raise them at the exact points below so tooling can react deterministically. A conformant registry **shall** raise: `WoTValidationFailureEventType` on a format or compatibility failure; `WoTLoadFailureEventType` when a validated document fails to materialize or a shadow generation cannot be activated; `WoTBindingFailureEventType` when a form cannot be bound (unknown binding or unsupported operation); and `WoTRefreshCompletedEventType` on every completed refresh, including automatic ones. Each failure event **shall** name the failing **resource** as its source and carry the `Phase` at which the failure occurred; the refresh-completed event **shall** name the **registry** and carry the committed `Summary` and `Generation`. On a committed generation switch the server **shall** additionally raise Core `GeneralModelChangeEventType` model change events for the added/removed nodes and reference changes (§7.9), and — where required by §7.10 — `SemanticChangeEventType`. Model change events **shall** be raised only for committed graph changes, never for shadow-generation scratch work. A subscriber on the well-known `WoTRegistry` object receives all of the above through the Server → registry → group → resource notifier chain (§6.6).

## 11 Security (normative)

Security applies at two boundaries: what the server fetches, and who may operate the registry. A server **shall** fetch a document's `@context`, external JSON schemas and federated referents over transport security and **shall** honour the registry's configured trust; credentials for those fetches and for protocol-binding endpoints are held out of band and **shall never** be exposed on registry or binding nodes (binding nodes carry policy and identity only, §6.4). The management Methods — `Refresh`, `Validate`, `SetEnabled`, `SetDefaultVersion` and the inherited xRegistry create/delete Methods — **shall** be subject to OPC UA role-based access control. Read access to a group **should** be restrictable, because it is the authorisation boundary that decides who can discover the Things a group contains. Operators **should** be aware that a Thing Description can expose device endpoints and security schemes, and **should** scope group read access accordingly. A server **shall not** weaken these controls for the incorporated 1.02 asset-management surface: the deprecated methods are subject to the same role-based access control as the registry methods that back them (§13.2).

## 12 Worked examples (informative)

The four documents under `examples/` are refreshed together in the `examples/04-refresh-results.json` run. Representative fragments are shown and discussed below; the full files carry the complete context and forms.

### 12.1 Thing Model → ObjectType (`examples/01-thing-model-pump.tm.jsonld`)

The Thing Model is a class template; its `@type` `uav:objectType` makes a refresh project it to an OPC UA ObjectType, and each affordance becomes a member declaration with the modelling rule the TM declares.

```jsonc
"@type": ["tm:ThingModel", "uav:objectType"],
"title": "PumpType",
"uav:browseName": "1:PumpType",
"properties": {
  "pumpSpeed": {
    "@type": "uav:variableType", "uav:browseName": "1:PumpSpeed",
    "type": "number", "unit": "qudt-quantitykind:AngularVelocity",
    "uav:modellingRule": "Mandatory", "uav:scaleFactor": 0.1, "uav:decimalPlaces": 2
  }
},
"actions": { "reset": { "@type": "uav:method", "uav:modellingRule": "Optional" } }
```

Here `PumpType` projects to an ObjectType whose `PumpSpeed` is a Mandatory Variable (scaled `engineering = raw × 0.1`, two decimals) and whose `reset` is an Optional Method. The resulting type NodeId is published back on `ThingModelFileType.DerivedTypeNodeId`.

### 12.2 Thing Description → Object instance (`examples/02-thing-description-pump.td.jsonld`)

The Thing Description is a concrete instance (`@type` `uav:object`) that derives from the Thing Model through a `links rel=type` entry — the dependency edge of §7.4 — and binds each affordance to a protocol form.

```jsonc
"@type": ["Thing", "uav:object"],
"title": "Pump 01",
"links": [ { "rel": "type", "href": "../01-thing-model-pump.tm.jsonld" } ],
"base": "opc.tcp://opcuademo.com:4840",
"properties": { "pumpSpeed": { "@type": "uav:variable",
  "forms": [ { "href": "/?id=nsu=http://example.com/demo/pump;s=PumpSpeed",
              "op": ["readproperty", "observeproperty"] } ] } }
```

A refresh with `Atomicity = PerClosure` activates `{Pump 01, PumpType}` together; the `pumpSpeed` form compiles into a binder plan (`readproperty` → Read, `observeproperty` → MonitoredItem, §8), and the resource carries `HasWoTProjection` to the projected Object. A TD that also wanted to appear under a parent machine would add a `links` entry with `rel: uav:componentOf` (§7.3).

### 12.3 Invalid Thing Description stays stored (`examples/03-invalid-thing-description.td.jsonld`)

An intentionally invalid TD demonstrates §7.5: it stays stored, is marked `Failed`, and leaves any prior projection untouched.

```jsonc
// missing top-level "title"; undefined security scheme; invalid form op
"security": "missing_sc",
"properties": { "pumpSpeed": { "forms": [ { "op": ["frobnicate"] } ] } },
"links": [ { "rel": "type", "href": "../thingmodels/does-not-exist.tm.jsonld" } ]
```

Format validation fails at `Phase = FormatValidation`; the registry records a `WoTValidationOutcomeDataType` with `FormatOutcome = Failed`, raises a `WoTValidationFailureEventType` from the resource, and reports an unresolved `WoTDependencyDataType` edge for the missing Thing Model.

### 12.4 Refresh results (`examples/04-refresh-results.json`)

The `Refresh` output over the three documents pairs a `WoTRefreshSummaryDataType` with per-resource `WoTResourceLoadResultDataType` rows.

```jsonc
"summary": { "Generation": 7, "Outcome": "Success", "Atomicity": "PerClosure",
             "Total": 3, "Succeeded": 2, "Failed": 1, "Retired": 1 },
"results": [
  { "ResourceId": "pumptype",   "Outcome": "Success", "Phase": "Activation",
    "LoadState": "Active", "MaterializedNodeCount": 12 },
  { "ResourceId": "pump-01",    "Outcome": "Success", "Phase": "Activation", "LoadState": "Active" },
  { "ResourceId": "pump-broken","Outcome": "Failed",  "Phase": "FormatValidation", "LoadState": "Failed" }
]
```

The summary reports two successes and one failure in generation 7, with one superseded generation retired after drain (§7.6); the failed `pump-broken` is isolated because its closure never activated, exactly as §7.4 requires.

## 13 Incorporated OPC 10100-1 v1.02 model (normative)

Revision 1.1 **incorporates** the published OPC 10100-1 v1.02 WoT Connectivity model into this combined NodeSet, in the **same** namespace `http://opcfoundation.org/UA/WoT-Con/`. Every published node is preserved at its **exact** numeric NodeId (`1..172`) and NodeClass — sourced from the pinned `legacy/WotConnection.csv` and emitted by `tools/build_model.py`, not hand-copied — so existing 1.02 clients continue to work unchanged. Because the additive registry supersedes the flat asset-management surface, the incorporated types and the well-known asset-management object carry `ReleaseStatus="Deprecated"` (following OPC 11030): they are **deprecated, not removed**. This is one combined model in one namespace; there is no separate namespace and no dual profile.

### 13.1 Preserved 1.02 model (unchanged)

The entry point is the `WoTAssetConnectionManagement` object (an instance of `WoTAssetConnectionManagementType`) under the `Objects` folder, preserved at its published NodeId and callable. Because xRegistry occupies namespace index 1 in this combined document, the 1.02 nodes are the own-namespace nodes at index 2; their **numeric identifiers are unchanged** and all own-namespace references and BrowseNames are consistent. The types, methods and method signatures are:

| Element | Kind | Preserved definition |
|---|---|---|
| `WoTAssetConnectionManagementType` | ObjectType (BaseObjectType) | `<WoTAssetName>` Object placeholder (BaseObjectType, `HasInterface` IWoTAssetType); `SupportedWoTBindings` `UriString[]` Property; Methods below; `Configuration` (WoTAssetConfigurationType). |
| `CreateAsset` | Method (Mandatory) | `CreateAsset([in] String AssetName, [out] NodeId AssetId)`. |
| `DeleteAsset` | Method (Mandatory) | `DeleteAsset([in] NodeId AssetId)`. |
| `DiscoverAssets` | Method (Optional) | `DiscoverAssets([out] String[] AssetEndpoints)`. |
| `CreateAssetForEndpoint` | Method (Optional) | `CreateAssetForEndpoint([in] String AssetName, [in] String AssetEndpoint, [out] NodeId AssetId)`. |
| `ConnectionTest` | Method (Optional) | `ConnectionTest([in] String AssetEndpoint, [out] Boolean Success, [out] String Status)`. |
| `WoTAssetConfigurationType` | ObjectType | Vendor `<WoTConfigurationParameterName>` Properties; `License` String. |
| `IWoTAssetType` | Interface (abstract) | `<WoTPropertyName>` Variables via `HasWoTComponent`; `AssetEndpoint` String; `WoTFile` (WoTAssetFileType, Mandatory). |
| `WoTAssetFileType` | ObjectType (FileType) | `CloseAndUpdate([in] UInt32 FileHandle)` (Mandatory). |
| `HasWoTComponent` | ReferenceType | Subtype of `HasComponent`; InverseName `WoTComponentOf`. |

Every 1.02 scenario continues to work: create-from-existing-TD (`CreateAsset` + `WoTFile` upload + `CloseAndUpdate`), discovery (`DiscoverAssets` → `ConnectionTest` → `CreateAssetForEndpoint` with an auto-generated TD file), deletion (`DeleteAsset`), and the supported-bindings advertisement (`SupportedWoTBindings`). The incorporated `NamespaceMetadata` carries the new `1.1.0` version while its NodeIds stay stable, and the deprecation is machine-readable (`ReleaseStatus="Deprecated"`) so tools can steer new development to the registry surface.

### 13.2 Backing the deprecated surface with the registry (signatures unchanged)

A server **may** back the deprecated asset-management surface with the registry so that both views stay consistent, **without changing any 1.02 signature**:

- **`CreateAsset(AssetName) → AssetId`** — the server creates (or reuses) a default `ThingDescriptionGroup`, creates a `ThingDescriptionFileType` resource for the asset (xRegistry `CreateResource`), and returns the NodeId of the *projected* Object as `AssetId`. The `<WoTAssetName>` object is the projected Object.
- **`WoTFile` / `WoTAssetFileType`** — the legacy `WoTFile` maps onto the `ThingDescriptionFileType` resource's inherited FileType (`Open`/`Read`/`Write`/`Close`): uploading the TD writes the resource's document bytes.
- **`CloseAndUpdate(FileHandle)`** — maps onto write-close of the resource followed by an implicit single-resource `Refresh` (validate + project). The 1.02 result codes are preserved: `Bad_DecodingError`/`Bad_NotSupported`/`Bad_NotFound` correspond to the format-validation and projection failures of this specification; on success the projected Variables appear exactly as in 1.02.
- **`DeleteAsset(AssetId)`** — maps onto `SetEnabled(false)` (unload projection) and the inherited xRegistry `Delete` of the backing resource, subject to the delete policy.
- **`DiscoverAssets` / `ConnectionTest` / `CreateAssetForEndpoint`** — preserved unchanged; a discovered/auto-generated TD is stored as a `ThingDescriptionFileType` resource, so discovery-created assets become first-class registry documents.
- **`SupportedWoTBindings` (`UriString[]`)** — surfaces the same binding set the registry advertises through `SupportedBindings` / `SelectedBindings`.
- **`HasWoTComponent`** — the legacy per-property reference remains valid on legacy-projected assets; registry-projected instances additionally carry `HasWoTProjection` back to their document.

Because the incorporation keeps the 1.02 namespace, types, node numbering and method signatures intact, a legacy client cannot tell whether the registry backs the asset manager; a registry-aware client sees the same assets as registry documents.

## 14 Conformance units and profiles

Conformance is composed from independently implementable **conformance units (CUs)**, grouped into **profiles**.

| CU | Requires |
|---|---|
| `WoT-Con Registry Discovery` | Well-known `WoTRegistry` under Server; browse registry/groups; read xRegistry + WoT metadata. |
| `WoT-Con Document Read` | Read a stored TD/TM via the inherited FileType `Open`/`Read`/`Close`. |
| `WoT-Con Document Write` | Create/write TD/TM resources via xRegistry `CreateResource` + FileType write. |
| `WoT-Con TD Validation` | Format + compatibility validation of TDs; `ValidationOutcome`; validation-failure events. |
| `WoT-Con TM Validation` | Format + compatibility validation of TMs. |
| `WoT-Con Type Materialization` | Project a TM to a type (`DerivedTypeNodeId`). |
| `WoT-Con Instance Materialization` | Project a TD to an instance with Variables/Methods/EventTypes. |
| `WoT-Con Reference Materialization` | Project links to References / explicit link representation (including parent `uav:componentOf`). |
| `WoT-Con Refresh` | `Refresh` Method with selection/options/expected-generation and detailed results. |
| `WoT-Con Events` | Resource lifecycle + refresh-completed events with the Server→registry→group→resource notifier chain. |
| `WoT-Con Model Change` | Model change events + NodeVersion correlation for committed generations. |
| `WoT-Con Semantic Change` | Optional semantic change events per §7.10. |
| `WoT-Con Version Lifecycle` | Desired/active version, version switch, unload, delete. |
| `WoT-Con Federation` | Resolve/project federated documents via `ExternalReference`/`ResourceUrl`. |
| `WoT-Con Binder Core` | Compile forms to binder plans; op→service mapping. |
| `WoT-Con Binder <Protocol>` | A specific per-binding module (OPC UA, HTTP, Modbus, …) with capabilities + version pinning. |
| `WoT-Con Atomicity Modes` | Per-resource / per-group / per-closure / per-registry atomicity with shadow switch + drain-retire. |
| `WoT-Con Legacy 1.02 Compatibility` | The incorporated OPC 10100-1 v1.02 model and scenarios, callable and preserved (§13). |

**Profiles.** *WoT-Con Registry Server* = Registry Discovery + Document Read/Write + TD/TM Validation + Type/Instance/Reference Materialization + Refresh + Events + Version Lifecycle + Binder Core + at least one Binder module. *WoT-Con Full* adds Model/Semantic Change, Federation and Atomicity Modes. *WoT-Con Legacy 1.02 Compatibility* is the incorporated-and-deprecated 1.02 surface (§13), independently conformant so existing 1.02 clients are served without the registry profile.

## 15 Acceptance scenarios

Each scenario is an end-to-end acceptance test for the CUs it exercises.

1. **Discover and read** — Browse `Server → WoTRegistry`, enumerate groups and resources, and read a stored TD's bytes via `Open`/`Read`/`Close`. *(Discovery, Document Read)*
2. **Ingest and validate a TM** — Create a `thingmodel` resource, write the `PumpType` TM, `Validate`; expect `FormatOutcome=Success`; `Refresh`; expect a projected ObjectType and `DerivedTypeNodeId` set. *(Document Write, TM Validation, Type Materialization)*
3. **Ingest a derived TD** — Create a `thingdescription` resource, write `Pump 01`, `Refresh` with `Atomicity=PerClosure`; expect the TD's closure (TD + PumpType TM) to activate atomically, an Object with `PumpSpeed`/`SpeedSetpoint`/`Reset`, forms bound to the OPC UA binder, and `HasWoTProjection` from the resource to the Object. *(Instance/Reference Materialization, Binder Core, Atomicity)*
4. **Invalid TD stays stored** — Write `pump-broken`, `Refresh`; expect `LoadState=Failed`, a `WoTValidationFailureEventType`, the document still readable, and any prior valid projection of that resource unchanged. *(TD Validation, Events)*
5. **Idempotent refresh** — Re-run scenario 3's `Refresh` unchanged; expect every result `Unchanged`, no node churn, `RefreshGeneration` unchanged. *(Refresh idempotence)*
6. **Version switch with live subscriptions** — Subscribe to `PumpSpeed`; publish `pump-01` v1.1.0; set `DesiredVersionId=1.1.0`; `Refresh`; expect a shadow switch, model change events for the committed change, `NodeVersion` updated, the old generation retired only after the subscription drains, and no lost notifications. *(Version Lifecycle, Model Change, Atomicity)*
7. **Unload with dependents** — `SetEnabled(false)` on the `PumpType` TM with `DeletePolicy=Reject` while `Pump 01` depends on it; expect rejection; retry with `Cascade`; expect the dependent TD's projection to unload. *(Version Lifecycle)*
8. **Federated dependency** — Point `Pump 01`'s TM dependency at a federated TM via `ResourceUrl`; `Refresh`; expect the closure to resolve and activate across the federation link. *(Federation)*
9. **Legacy round-trip** — Via the deprecated `WoTAssetConnectionManagement`, `CreateAsset("Pump01")`, `Open`/`Write`/`CloseAndUpdate` the TD, browse the mapped Variables; when the registry backs the surface, expect the same asset to appear as a `thingdescription` registry document with an identical projection. *(Legacy 1.02 Compatibility)*

## 16 NodeSet validation

The NodeSet, CSV and Annex A are generated from `tools/build_model.py` (from the in-code registry model and the pinned `legacy/` sources); they shall not be hand-edited. `tools/validate_local.py` checks XML well-formedness, unique NodeIds (additive registry ids in the 64000+ block, incorporated 1.02 ids in the preserved 1..172 range), CSV↔NodeSet consistency, that every reference resolves against the own namespace, the loaded xRegistry base `NodeIds.csv` and (when the gitignored `tools/ref/UA.NodeIds.csv` aid is present) the base UA ids, that each type carries a `HasSubtype` inverse and each Structure its encodings, that the well-known `WoTRegistry` instance is a component and `HasNotifier` target of the `Server` object with `EventNotifier` set, and that the registry and document types generate the required events. It additionally **proves the 1.02 preservation**: the first 172 CSV rows match the pinned `legacy/WotConnection.csv` exactly (every NodeId and NodeClass), every concrete legacy id is present with its pinned NodeClass while reserved ids are not emitted, the required 1.02 symbols and the callable well-known `WoTAssetConnectionManagement` are present, the management/upload surface carries `ReleaseStatus="Deprecated"`, and the combined NodeSet declares the single `http://opcfoundation.org/UA/WoT-Con/` namespace at model version 1.1.0. Finally it confirms the generated Annex A is embedded verbatim in this document.

---

<a id="annex-a"></a>

## Annex A — Information model

This annex is the normative node reference. It is generated from `tools/build_model.py` and always matches `Opc.Ua.WoTCon.NodeSet2.xml`. It documents one combined model in the companion namespace `http://opcfoundation.org/UA/WoT-Con/` (namespace index `2` in this NodeSet, after the required `http://opcfoundation.org/UA/xRegistry/` base model at index `1`). The additive **WoT Connectivity 1.1** registry types **extend the abstract [OPC UA — xRegistry](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md) base types** (`RegistryType`/`GroupType`/`ResourceType`) and use provisional NodeIds in the `64000+` block (final IDs are assigned by the OPC Foundation). The incorporated **OPC 10100-1 v1.02** legacy model is preserved unchanged at its published NodeIds `1..172` and is documented, with its `Deprecated` release status, under *Legacy model* below. The **Declared in** column marks members inherited from a supertype.

### Type overview

| NodeId | BrowseName | NodeClass | Subtype of |
|---|---|---|---|
| ns=2;i=64000 | [WoTRegistryType](#type-WoTRegistryType) | ObjectType | [RegistryType](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md#type-RegistryType) |
| ns=2;i=64001 | [ThingDescriptionGroupType](#type-ThingDescriptionGroupType) | ObjectType | [GroupType](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md#type-GroupType) |
| ns=2;i=64002 | [ThingModelGroupType](#type-ThingModelGroupType) | ObjectType | [GroupType](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md#type-GroupType) |
| ns=2;i=64003 | [WoTDocumentType](#type-WoTDocumentType) | ObjectType | [ResourceType](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md#type-ResourceType) |
| ns=2;i=64004 | [ThingDescriptionFileType](#type-ThingDescriptionFileType) | ObjectType | [WoTDocumentType](#type-WoTDocumentType) |
| ns=2;i=64005 | [ThingModelFileType](#type-ThingModelFileType) | ObjectType | [WoTDocumentType](#type-WoTDocumentType) |
| ns=2;i=64006 | [WoTBindingType](#type-WoTBindingType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| ns=2;i=64010 | [WoTResourceEventType](#type-WoTResourceEventType) | ObjectType | [BaseEventType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.2) |
| ns=2;i=64011 | [WoTValidationFailureEventType](#type-WoTValidationFailureEventType) | ObjectType | [WoTResourceEventType](#type-WoTResourceEventType) |
| ns=2;i=64012 | [WoTLoadFailureEventType](#type-WoTLoadFailureEventType) | ObjectType | [WoTResourceEventType](#type-WoTResourceEventType) |
| ns=2;i=64013 | [WoTBindingFailureEventType](#type-WoTBindingFailureEventType) | ObjectType | [WoTResourceEventType](#type-WoTResourceEventType) |
| ns=2;i=64014 | [WoTRefreshCompletedEventType](#type-WoTRefreshCompletedEventType) | ObjectType | [BaseEventType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.2) |
| ns=2;i=64020 | [WoTDocumentKindEnum](#type-WoTDocumentKindEnum) | DataType | [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40) |
| ns=2;i=64021 | [WoTLoadStateEnum](#type-WoTLoadStateEnum) | DataType | [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40) |
| ns=2;i=64022 | [WoTRefreshModeEnum](#type-WoTRefreshModeEnum) | DataType | [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40) |
| ns=2;i=64023 | [WoTAtomicityEnum](#type-WoTAtomicityEnum) | DataType | [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40) |
| ns=2;i=64024 | [WoTDeletePolicyEnum](#type-WoTDeletePolicyEnum) | DataType | [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40) |
| ns=2;i=64025 | [WoTOutcomeEnum](#type-WoTOutcomeEnum) | DataType | [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40) |
| ns=2;i=64026 | [WoTPhaseEnum](#type-WoTPhaseEnum) | DataType | [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40) |
| ns=2;i=64027 | [WoTBindingCapabilityEnum](#type-WoTBindingCapabilityEnum) | DataType | [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40) |
| ns=2;i=64040 | [WoTValidationOutcomeDataType](#type-WoTValidationOutcomeDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=2;i=64041 | [WoTBindingCapabilityDataType](#type-WoTBindingCapabilityDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=2;i=64042 | [WoTRefreshOptionsDataType](#type-WoTRefreshOptionsDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=2;i=64043 | [WoTResourceSelectorDataType](#type-WoTResourceSelectorDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=2;i=64044 | [WoTResourceLoadResultDataType](#type-WoTResourceLoadResultDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=2;i=64045 | [WoTRefreshSummaryDataType](#type-WoTRefreshSummaryDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=2;i=64046 | [WoTDependencyDataType](#type-WoTDependencyDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |
| ns=2;i=64060 | [HasWoTProjection](#type-HasWoTProjection) | ReferenceType | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-5/11.3) |

### Object types

<a id="type-WoTRegistryType"></a>

#### WoTRegistryType  (ns=2;i=64000)

*Inherits from:* [RegistryType](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md#type-RegistryType)

The WoT Connectivity 1.1 registry root - an xRegistry RegistryType (a FolderType) that holds ThingDescriptionGroupType and ThingModelGroupType groups. The stored Thing Description / Thing Model files and their versions are canonical; the projected AddressSpace (types from Thing Models, instances from Thing Descriptions) is derived code-behind. Exposed as a well-known WoTRegistry object under the Server object (i=2253). Adds registry-wide refresh, generation and validation-policy state and the Refresh Method.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| AutoRefresh | Variable | Boolean | Optional | WoTRegistryType | True if the registry automatically re-projects stored documents (per RefreshMode); false if only explicit Refresh calls re-project. |
| RefreshMode | Variable | [WoTRefreshModeEnum](#type-WoTRefreshModeEnum) | Optional | WoTRegistryType | How automatic refresh is triggered when AutoRefresh is true. |
| RefreshInterval | Variable | Duration | Optional | WoTRegistryType | The interval used when RefreshMode is Periodic. |
| RefreshGeneration | Variable | UInt32 | Mandatory | WoTRegistryType | The current committed projection generation; incremented on every committed refresh. Materialized nodes carry the generation in their NodeVersion for correlation. |
| LastRefreshTime | Variable | DateTime | Optional | WoTRegistryType | UTC time of the last completed refresh. |
| LastRefreshSummary | Variable | [WoTRefreshSummaryDataType](#type-WoTRefreshSummaryDataType) | Optional | WoTRegistryType | An immutable snapshot summarizing the last completed refresh. |
| DefaultAtomicity | Variable | [WoTAtomicityEnum](#type-WoTAtomicityEnum) | Optional | WoTRegistryType | The commit granularity applied when a Refresh omits an explicit atomicity. |
| DeletePolicy | Variable | [WoTDeletePolicyEnum](#type-WoTDeletePolicyEnum) | Optional | WoTRegistryType | The default policy for treating dependents on unload/delete. |
| ValidateFormat | Variable | Boolean | Optional | WoTRegistryType | Registry-wide default: validate document format on ingest/refresh. |
| ValidateCompatibility | Variable | Boolean | Optional | WoTRegistryType | Registry-wide default: validate version compatibility on ingest/refresh. |
| StrictValidation | Variable | Boolean | Optional | WoTRegistryType | If true, a validation warning is treated as a failure. |
| VocabularyVersion | Variable | String | Optional | WoTRegistryType | The version-pinned WoT Binding JSON-LD vocabulary this registry validates and projects against. |
| SelectedBindings | Variable | [WoTBindingCapabilityDataType](#type-WoTBindingCapabilityDataType)\[\] | Optional | WoTRegistryType | An immutable snapshot array of the protocol bindings currently selected/active registry-wide. |
| SupportedBindings | Object |  | Optional | WoTRegistryType | A folder of browseable WoTBindingType binding descriptors the server can realize (the live, per-field form of the selected-bindings snapshot). |
| <ThingDescriptionGroup> | Object |  | OptionalPlaceholder | WoTRegistryType | A Thing Description Group held by this registry (constrained to the ThingDescriptionGroupType subtype). |
| <ThingModelGroup> | Object |  | OptionalPlaceholder | WoTRegistryType | A Thing Model Group held by this registry (constrained to the ThingModelGroupType subtype). |
| Refresh | Method |  | Optional | WoTRegistryType | Re-project selected stored documents into the AddressSpace. Idempotent: a document whose content digest is unchanged is reported Unchanged and not re-materialized unless Options.Force is set. Projects into a shadow generation and switches atomically per Options.Atomicity; superseded generations are retired after their monitored items drain. If ExpectedGeneration is non-zero and does not equal RefreshGeneration, the call fails with Bad_InvalidState and changes nothing (optimistic concurrency). An empty Selection selects the whole registry. |

*Generates events:* [WoTRefreshCompletedEventType](#type-WoTRefreshCompletedEventType)

<a id="type-ThingDescriptionGroupType"></a>

#### ThingDescriptionGroupType  (ns=2;i=64001)

*Inherits from:* [GroupType](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md#type-GroupType)

An xRegistry GroupType that collects related ThingDescriptionFileType resources (a Thing Description Group per the WoT xRegistry model). Adds the group-level format/compatibility validation policy. Its <ThingDescription> placeholder constrains members to the Thing Description subtype.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| ValidateFormat | Variable | Boolean | Optional | ThingDescriptionGroupType | Group-level policy: validate Thing Description format (WoT-TD/1.1) on ingest. |
| ValidateCompatibility | Variable | Boolean | Optional | ThingDescriptionGroupType | Group-level policy: validate version compatibility on ingest. |
| ConsistentFormat | Variable | Boolean | Optional | ThingDescriptionGroupType | Group-level policy: require all versions of a resource to share one format. |
| <ThingDescription> | Object |  | OptionalPlaceholder | ThingDescriptionGroupType | A Thing Description resource held by this group (constrained to the ThingDescriptionFileType subtype). |

<a id="type-ThingModelGroupType"></a>

#### ThingModelGroupType  (ns=2;i=64002)

*Inherits from:* [GroupType](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md#type-GroupType)

An xRegistry GroupType that collects related ThingModelFileType resources (a Thing Model Group per the WoT xRegistry model). Adds the group-level format/compatibility validation policy. Its <ThingModel> placeholder constrains members to the Thing Model subtype.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| ValidateFormat | Variable | Boolean | Optional | ThingModelGroupType | Group-level policy: validate Thing Model format (WoT-TM/1.1) on ingest. |
| ValidateCompatibility | Variable | Boolean | Optional | ThingModelGroupType | Group-level policy: validate version compatibility on ingest. |
| ConsistentFormat | Variable | Boolean | Optional | ThingModelGroupType | Group-level policy: require all versions of a resource to share one format. |
| <ThingModel> | Object |  | OptionalPlaceholder | ThingModelGroupType | A Thing Model resource held by this group (constrained to the ThingModelFileType subtype). |

<a id="type-WoTDocumentType"></a>

#### WoTDocumentType  (ns=2;i=64003) *(abstract)*

*Inherits from:* [ResourceType](https://github.com/marcschier/opcua-drafts/blob/main/core-specs/xregistry/OPC-UA-xRegistry.md#type-ResourceType)

The abstract base of a stored WoT document resource - an xRegistry ResourceType (a FileType) whose content bytes are the JSON-LD document, read/written with the inherited Open/Read/Write/Close Methods. Adds the derived-projection metadata (load state, desired/active version, validation and compatibility outcomes, content digest, materialized-node count and root, selected bindings) and the Validate, SetEnabled and SetDefaultVersion Methods. Concrete subtypes fix the document kind.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| DocumentKind | Variable | [WoTDocumentKindEnum](#type-WoTDocumentKindEnum) | Mandatory | WoTDocumentType | Whether this document is a Thing Description or a Thing Model. Fixed by the concrete subtype. |
| Enabled | Variable | Boolean | Mandatory | WoTDocumentType | The desired enabled state: true requests that the document be validated and projected; false requests unload. |
| LoadState | Variable | [WoTLoadStateEnum](#type-WoTLoadStateEnum) | Mandatory | WoTDocumentType | The actual lifecycle state of this document's derived projection. |
| DesiredVersionId | Variable | String | Optional | WoTDocumentType | The versionid the operator wants active for this resource (the desired/pinned version). |
| ActiveVersionId | Variable | String | Optional | WoTDocumentType | The versionid whose projection is currently active. |
| IsDefault | Variable | Boolean | Optional | WoTDocumentType | xRegistry isdefault: true when this version is the resource's default (sticky) version. |
| Ancestor | Variable | String | Optional | WoTDocumentType | xRegistry ancestor: the versionid this version derives from (version lineage). |
| Compatibility | Variable | String | Optional | WoTDocumentType | The compatibility policy all versions of this resource adhere to (for example NONE, BACKWARD, FULL). |
| AutoRefresh | Variable | Boolean | Optional | WoTDocumentType | Per-document override of the registry AutoRefresh setting. |
| RefreshGeneration | Variable | UInt32 | Optional | WoTDocumentType | The registry generation at which this document was last projected. |
| LastRefreshTime | Variable | DateTime | Optional | WoTDocumentType | UTC time this document was last projected. |
| ContentDigest | Variable | ByteString | Optional | WoTDocumentType | The content digest (hash) of the stored document bytes; used to make refresh idempotent. |
| ValidationOutcome | Variable | [WoTValidationOutcomeDataType](#type-WoTValidationOutcomeDataType) | Optional | WoTDocumentType | An immutable snapshot of this document's format and compatibility validation result. |
| MaterializedNodeCount | Variable | UInt32 | Optional | WoTDocumentType | The number of AddressSpace nodes materialized from this document's active projection. |
| RootNodeId | Variable | [NodeId](https://reference.opcfoundation.org/specs/OPC-10000-3/8.2.1) | Optional | WoTDocumentType | The root node of this document's active projection (the type or instance root). |
| SelectedBindings | Variable | [WoTBindingCapabilityDataType](#type-WoTBindingCapabilityDataType)\[\] | Optional | WoTDocumentType | An immutable snapshot array of the protocol bindings selected for this document's forms. |
| Validate | Method |  | Optional | WoTDocumentType | Validate the stored document (format and, when enabled, compatibility) without changing its projection. Returns the outcome snapshot; also refreshes the ValidationOutcome Property. |
| SetEnabled | Method |  | Optional | WoTDocumentType | Set the desired Enabled state of this document. Enabling requests validation and projection; disabling requests unload per the registry DeletePolicy. If ExpectedEpoch is non-zero and does not equal the resource's current Epoch the call fails with Bad_InvalidState and changes nothing. |
| SetDefaultVersion | Method |  | Optional | WoTDocumentType | Make a specific version of this resource its default (sticky) version, so that resolvers selecting the resource without a versionid resolve to it. If ExpectedEpoch is non-zero and does not equal the resource's current Epoch the call fails with Bad_InvalidState and changes nothing. |

*Generates events:* [WoTValidationFailureEventType](#type-WoTValidationFailureEventType), [WoTLoadFailureEventType](#type-WoTLoadFailureEventType), [WoTBindingFailureEventType](#type-WoTBindingFailureEventType)

<a id="type-ThingDescriptionFileType"></a>

#### ThingDescriptionFileType  (ns=2;i=64004)

*Inherits from:* [WoTDocumentType](#type-WoTDocumentType)

A concrete WoTDocumentType whose content is a W3C WoT Thing Description (WoT-TD/1.1, application/td+json). Projects to OPC UA instances: affordances become Variables, Methods and event sources; forms become binder plans. Adds the Thing instance identity (ThingId, base URI) and the link to the Thing Model it derives from.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| ThingId | Variable | String | Optional | ThingDescriptionFileType | The Thing Description id (a URI/URN identifying the concrete Thing instance). |
| ThingTitle | Variable | String | Optional | ThingDescriptionFileType | The Thing Description human-readable title. |
| BaseUri | Variable | String | Optional | ThingDescriptionFileType | The Thing Description base URI used to resolve relative form hrefs. |
| ModelReference | Variable | String | Optional | ThingDescriptionFileType | The xid or href of the Thing Model this Thing Description derives from (links rel=type), when present. |

<a id="type-ThingModelFileType"></a>

#### ThingModelFileType  (ns=2;i=64005)

*Inherits from:* [WoTDocumentType](#type-WoTDocumentType)

A concrete WoTDocumentType whose content is a W3C WoT Thing Model (WoT-TM/1.1, application/tm+json). Projects to OPC UA types: it materializes an ObjectType or VariableType and the affordance member declarations and modelling rules. Adds the derived type NodeId and model version.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| ModelTitle | Variable | String | Optional | ThingModelFileType | The Thing Model human-readable title. |
| ModelVersion | Variable | String | Optional | ThingModelFileType | The Thing Model version (WoT version.model), when present. |
| DerivedTypeNodeId | Variable | [NodeId](https://reference.opcfoundation.org/specs/OPC-10000-3/8.2.1) | Optional | ThingModelFileType | The ObjectType or VariableType materialized from this Thing Model. |

<a id="type-WoTBindingType"></a>

#### WoTBindingType  (ns=2;i=64006)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

A browseable protocol-binding descriptor: the live, per-field representation of one W3C WoT protocol binding the server can realize (its URI, title, version-pinned W3C document, draft maturity, enabled state, content types and a capability snapshot). Selected/active binding sets are additionally exposed as immutable WoTBindingCapabilityDataType array snapshots. Policy and identity are browseable; no credentials or secrets are ever exposed here.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| BindingUri | Variable | String | Mandatory | WoTBindingType | The WoT protocol-binding vocabulary URI this descriptor represents. |
| Title | Variable | String | Optional | WoTBindingType | Human-readable binding title. |
| ProfileVersion | Variable | String | Optional | WoTBindingType | The version-pinned W3C binding document version. |
| DraftMaturity | Variable | String | Optional | WoTBindingType | The W3C maturity of the pinned binding document (for example WD, CR, PR, REC). |
| Enabled | Variable | Boolean | Optional | WoTBindingType | True if the server currently realizes forms of this binding. |
| ContentTypes | Variable | String\[\] | Optional | WoTBindingType | The content types this binding produces/consumes. |
| Capabilities | Variable | [WoTBindingCapabilityDataType](#type-WoTBindingCapabilityDataType) | Optional | WoTBindingType | An immutable capability snapshot for this binding. |

### Event types

<a id="type-WoTResourceEventType"></a>

#### WoTResourceEventType  (ns=2;i=64010) *(abstract)*

*Subtype of:* [BaseEventType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.2)

The common base event for a WoT resource lifecycle notification. Carries the identity of the affected resource/version, the document kind, the refresh generation, the phase reached and the outcome. Abstract; servers emit one of its concrete subtypes.

| Field | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|
| Xid | String | Mandatory | WoTResourceEventType | The xRegistry xid of the affected resource/version. |
| ResourceId | String | Mandatory | WoTResourceEventType | The resourceid of the affected resource. |
| VersionId | String | Mandatory | WoTResourceEventType | The versionid of the affected version. |
| DocumentKind | [WoTDocumentKindEnum](#type-WoTDocumentKindEnum) | Mandatory | WoTResourceEventType | Whether the document is a Thing Description or a Thing Model. |
| Generation | UInt32 | Mandatory | WoTResourceEventType | The refresh generation the notification relates to. |
| Phase | [WoTPhaseEnum](#type-WoTPhaseEnum) | Mandatory | WoTResourceEventType | The phase reached (the failing phase on a failure event). |
| Outcome | [WoTOutcomeEnum](#type-WoTOutcomeEnum) | Mandatory | WoTResourceEventType | The outcome the notification reports. |

<a id="type-WoTValidationFailureEventType"></a>

#### WoTValidationFailureEventType  (ns=2;i=64011)

*Subtype of:* [WoTResourceEventType](#type-WoTResourceEventType)

Raised when a document fails format or compatibility validation. The failing resource is the event source; the stored document is retained and any previous valid projection stays active.

| Field | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|
| ValidationOutcome | [WoTValidationOutcomeDataType](#type-WoTValidationOutcomeDataType) | Mandatory | WoTValidationFailureEventType | The full validation outcome snapshot for the failure. |

<a id="type-WoTLoadFailureEventType"></a>

#### WoTLoadFailureEventType  (ns=2;i=64012)

*Subtype of:* [WoTResourceEventType](#type-WoTResourceEventType)

Raised when a validated document fails to project (materialize) into the AddressSpace, or when its shadow generation cannot be activated. The failing resource is the event source.

| Field | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|
| LoadState | [WoTLoadStateEnum](#type-WoTLoadStateEnum) | Mandatory | WoTLoadFailureEventType | The load state after the failed projection/activation. |
| FailedNodeId | [NodeId](https://reference.opcfoundation.org/specs/OPC-10000-3/8.2.1) | Mandatory | WoTLoadFailureEventType | The node whose materialization failed, if identifiable. |
| Reason | String | Mandatory | WoTLoadFailureEventType | Human-readable failure reason. |

<a id="type-WoTBindingFailureEventType"></a>

#### WoTBindingFailureEventType  (ns=2;i=64013)

*Subtype of:* [WoTResourceEventType](#type-WoTResourceEventType)

Raised when a form cannot be bound to its protocol binding (unknown binding, unsupported operation or a runtime binder error). The failing resource is the event source.

| Field | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|
| BindingUri | String | Mandatory | WoTBindingFailureEventType | The binding URI that could not be bound. |
| Reason | String | Mandatory | WoTBindingFailureEventType | Human-readable binding failure reason. |

<a id="type-WoTRefreshCompletedEventType"></a>

#### WoTRefreshCompletedEventType  (ns=2;i=64014)

*Subtype of:* [BaseEventType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.2)

Raised by the registry when a Refresh completes (including automatic refreshes). Carries the refresh summary and the committed generation. The registry object is the event source.

| Field | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|
| Summary | [WoTRefreshSummaryDataType](#type-WoTRefreshSummaryDataType) | Mandatory | WoTRefreshCompletedEventType | The refresh summary snapshot. |
| RequestId | String | Mandatory | WoTRefreshCompletedEventType | The caller-supplied request identifier echoed from the Refresh call. |
| Generation | UInt32 | Mandatory | WoTRefreshCompletedEventType | The committed generation. |

### DataTypes

<a id="type-WoTDocumentKindEnum"></a>

#### WoTDocumentKindEnum  (ns=2;i=64020)

*Subtype of:* [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40)

The kind of WoT document a resource carries: a Thing Description (a concrete instance) or a Thing Model (a reusable type template).

| Name | Value | Description |
|---|---|---|
| ThingDescription | 0 | A W3C WoT Thing Description (WoT-TD/1.1); projects to OPC UA instances. |
| ThingModel | 1 | A W3C WoT Thing Model (WoT-TM/1.1); projects to OPC UA types. |

<a id="type-WoTLoadStateEnum"></a>

#### WoTLoadStateEnum  (ns=2;i=64021)

*Subtype of:* [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40)

The lifecycle state of a WoT document's derived projection in the AddressSpace. The registry file always remains stored; this enum reflects only the state of the code-behind projection.

| Name | Value | Description |
|---|---|---|
| Unloaded | 0 | Stored but not projected into the AddressSpace. |
| Validating | 1 | Format and compatibility validation is in progress. |
| Loading | 2 | The projection is being materialized under a shadow generation. |
| Active | 3 | The projection is committed and serving as the active generation. |
| Failed | 4 | Validation or projection failed; the last valid projection (if any) stays active. |
| Superseded | 5 | A newer generation has replaced this one; retained until monitored items drain. |
| Retiring | 6 | Being retired; awaiting monitored-item drain before node removal. |
| Retired | 7 | The projection has been removed from the AddressSpace. |

<a id="type-WoTRefreshModeEnum"></a>

#### WoTRefreshModeEnum  (ns=2;i=64022)

*Subtype of:* [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40)

How a registry or document triggers refresh of its derived projection.

| Name | Value | Description |
|---|---|---|
| Manual | 0 | Only an explicit Refresh Method call re-projects. |
| Periodic | 1 | The registry re-projects on a fixed interval (RefreshInterval). |
| EventDriven | 2 | The registry re-projects when a stored document changes (write/CloseAndUpdate). |
| Scheduled | 3 | The registry re-projects on an implementation-defined schedule. |

<a id="type-WoTAtomicityEnum"></a>

#### WoTAtomicityEnum  (ns=2;i=64023)

*Subtype of:* [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40)

The commit granularity applied when a refresh projects one or more documents.

| Name | Value | Description |
|---|---|---|
| PerResource | 0 | Each resource commits independently; a failure isolates to that resource. |
| PerGroup | 1 | All resources of a group commit together or not at all. |
| PerClosure | 2 | A document and its full dependency closure (DAG) commit atomically. |
| PerRegistry | 3 | All selected documents commit as a single all-or-nothing transaction. |

<a id="type-WoTDeletePolicyEnum"></a>

#### WoTDeletePolicyEnum  (ns=2;i=64024)

*Subtype of:* [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40)

How the registry treats dependents when a document version is unloaded or deleted.

| Name | Value | Description |
|---|---|---|
| Reject | 0 | Reject the operation while any other loaded document still depends on it. |
| Retire | 1 | Retire the projection but keep the stored document for dependents to resolve. |
| Cascade | 2 | Unload dependents that resolve only through this document. |
| Force | 3 | Force-unload the projection even while dependents remain, marking them Failed. |

<a id="type-WoTOutcomeEnum"></a>

#### WoTOutcomeEnum  (ns=2;i=64025)

*Subtype of:* [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40)

The outcome of a validation, projection or refresh operation on a document or the registry.

| Name | Value | Description |
|---|---|---|
| Success | 0 | The operation completed and changed the projection. |
| Unchanged | 1 | The operation was idempotent; the content digest matched and nothing changed. |
| Warning | 2 | The operation completed with non-fatal warnings. |
| Skipped | 3 | The operation was not applicable and was skipped. |
| Rejected | 4 | The operation was rejected by policy (for example concurrency or delete policy). |
| Failed | 5 | The operation failed; the previous valid projection (if any) remains active. |

<a id="type-WoTPhaseEnum"></a>

#### WoTPhaseEnum  (ns=2;i=64026)

*Subtype of:* [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40)

The processing phase a document reached, used to locate where an outcome was produced.

| Name | Value | Description |
|---|---|---|
| Fetch | 0 | Fetching the document bytes and its @context/schema references. |
| Parse | 1 | Parsing the JSON-LD document. |
| FormatValidation | 2 | Validating the document against its WoT-TD/WoT-TM format. |
| CompatibilityValidation | 3 | Validating the version against the resource compatibility policy. |
| DependencyResolution | 4 | Resolving the dependency closure (tm:extends, tm:ref, links rel=type). |
| Projection | 5 | Materializing types/instances into a shadow generation. |
| Activation | 6 | Committing the shadow generation as active. |
| Retirement | 7 | Retiring a superseded generation after monitored items drain. |

<a id="type-WoTBindingCapabilityEnum"></a>

#### WoTBindingCapabilityEnum  (ns=2;i=64027)

*Subtype of:* [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.40)

A single interaction operation a protocol binding supports, aligned with the WoT form op vocabulary.

| Name | Value | Description |
|---|---|---|
| ReadProperty | 0 | Read a property affordance. |
| WriteProperty | 1 | Write a property affordance. |
| ObserveProperty | 2 | Observe (subscribe to) a property affordance. |
| InvokeAction | 3 | Invoke an action affordance. |
| SubscribeEvent | 4 | Subscribe to an event affordance. |
| UnsubscribeEvent | 5 | Unsubscribe from an event affordance. |

<a id="type-WoTValidationOutcomeDataType"></a>

#### WoTValidationOutcomeDataType  (ns=2;i=64040)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

An immutable snapshot of a document's format and compatibility validation result. Read as a single Variant value; a new snapshot is produced on each validation and never mutated in place.

| Field | DataType | Description |
|---|---|---|
| FormatValidated | Boolean | True if format validation was performed. |
| FormatOutcome | [WoTOutcomeEnum](#type-WoTOutcomeEnum) | Outcome of format validation (WoT-TD/WoT-TM conformance). |
| FormatReason | String | Human-readable reason for the format outcome (empty on success). |
| CompatibilityValidated | Boolean | True if compatibility validation was performed. |
| CompatibilityOutcome | [WoTOutcomeEnum](#type-WoTOutcomeEnum) | Outcome of compatibility validation against the resource policy. |
| CompatibilityReason | String | Human-readable reason for the compatibility outcome (empty on success). |
| CompatibilityPolicy | String | The compatibility policy in force (for example NONE, BACKWARD, FULL). |
| ValidatedAt | DateTime | UTC time the validation completed. |
| VocabularyVersion | String | The pinned WoT Binding JSON-LD vocabulary version used for validation. |

<a id="type-WoTBindingCapabilityDataType"></a>

#### WoTBindingCapabilityDataType  (ns=2;i=64041)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

An immutable snapshot of a protocol binding's identity, version-pinned W3C document, maturity and supported operations. Held as an array element only for immutable snapshots; browseable binding objects (WoTBindingType) carry the live, per-field form.

| Field | DataType | Description |
|---|---|---|
| BindingUri | String | The WoT protocol-binding vocabulary URI (for example the OPC UA, HTTP or Modbus binding). |
| Title | String | Human-readable binding title. |
| ProfileVersion | String | The version-pinned W3C binding document version this capability snapshot was built against. |
| DraftMaturity | String | The W3C maturity of the pinned binding document (for example WD, CR, PR, REC). |
| Capabilities | [WoTBindingCapabilityEnum](#type-WoTBindingCapabilityEnum)\[\] | The interaction operations this binding supports. |
| ContentTypes | String\[\] | The content types this binding produces/consumes. |

<a id="type-WoTRefreshOptionsDataType"></a>

#### WoTRefreshOptionsDataType  (ns=2;i=64042)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

Immutable options controlling a single Refresh invocation.

| Field | DataType | Description |
|---|---|---|
| Atomicity | [WoTAtomicityEnum](#type-WoTAtomicityEnum) | Commit granularity for this refresh. |
| Force | Boolean | Re-project even when the content digest is unchanged. |
| DryRun | Boolean | Validate and compute results without committing any projection change. |
| IncludeDependents | Boolean | Also refresh documents that depend on the selected documents. |
| DeletePolicy | [WoTDeletePolicyEnum](#type-WoTDeletePolicyEnum) | How to treat dependents when a selected document is unloaded/retired. |
| MaxParallelism | UInt32 | Maximum number of documents projected concurrently; 0 lets the server decide. |
| Timeout | Duration | Overall time budget for the refresh; 0 lets the server decide. |

<a id="type-WoTResourceSelectorDataType"></a>

#### WoTResourceSelectorDataType  (ns=2;i=64043)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

An immutable selector identifying which stored documents a Refresh applies to. An empty selector array selects the whole registry.

| Field | DataType | Description |
|---|---|---|
| Kind | [WoTDocumentKindEnum](#type-WoTDocumentKindEnum) | Restrict to Thing Descriptions or Thing Models; omit to select both. |
| GroupId | String | Restrict to a group by groupid; empty selects all groups. |
| ResourceId | String | Restrict to a resource by resourceid; empty selects all resources. |
| VersionId | String | Restrict to a version by versionid; empty selects the resource's default version. |
| Xid | String | Select a single entity by its xRegistry xid; overrides the other fields when set. |

<a id="type-WoTResourceLoadResultDataType"></a>

#### WoTResourceLoadResultDataType  (ns=2;i=64044)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

An immutable per-resource result row of a Refresh. Never mutated; the array is a point-in-time snapshot for one generation.

| Field | DataType | Description |
|---|---|---|
| Xid | String | The xRegistry xid of the affected resource/version. |
| GroupId | String | The groupid of the resource's group. |
| ResourceId | String | The resourceid of the affected resource. |
| VersionId | String | The versionid that was projected. |
| Kind | [WoTDocumentKindEnum](#type-WoTDocumentKindEnum) | Whether the document is a Thing Description or a Thing Model. |
| Outcome | [WoTOutcomeEnum](#type-WoTOutcomeEnum) | The per-resource outcome. |
| Phase | [WoTPhaseEnum](#type-WoTPhaseEnum) | The phase the resource reached (the failing phase on failure). |
| LoadState | [WoTLoadStateEnum](#type-WoTLoadStateEnum) | The resulting load state of the projection. |
| Generation | UInt32 | The refresh generation this result belongs to. |
| MaterializedNodeCount | UInt32 | Number of AddressSpace nodes materialized for this resource. |
| RootNodeId | [NodeId](https://reference.opcfoundation.org/specs/OPC-10000-3/8.2.1) | The root node of the materialized projection, if any. |
| ContentDigest | ByteString | The content digest (hash) of the projected document bytes. |
| Message | String | Human-readable detail for the outcome. |

<a id="type-WoTRefreshSummaryDataType"></a>

#### WoTRefreshSummaryDataType  (ns=2;i=64045)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

An immutable summary of one Refresh invocation, also carried by the WoTRefreshCompletedEventType and cached on the registry as LastRefreshSummary.

| Field | DataType | Description |
|---|---|---|
| RequestId | String | The caller-supplied request identifier echoed back for correlation. |
| Generation | UInt32 | The committed refresh generation (0 on a dry run or full failure). |
| Outcome | [WoTOutcomeEnum](#type-WoTOutcomeEnum) | The overall outcome of the refresh. |
| Atomicity | [WoTAtomicityEnum](#type-WoTAtomicityEnum) | The commit granularity that was applied. |
| StartTime | DateTime | UTC start time of the refresh. |
| EndTime | DateTime | UTC end time of the refresh. |
| Total | UInt32 | Total number of resources considered. |
| Succeeded | UInt32 | Number of resources that changed successfully. |
| Unchanged | UInt32 | Number of resources that were idempotently unchanged. |
| Failed | UInt32 | Number of resources that failed. |
| Skipped | UInt32 | Number of resources skipped by selection or policy. |
| Retired | UInt32 | Number of superseded generations retired. |

<a id="type-WoTDependencyDataType"></a>

#### WoTDependencyDataType  (ns=2;i=64046)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

An immutable edge of the document dependency DAG, used to describe closures in results and diagnostics.

| Field | DataType | Description |
|---|---|---|
| SourceXid | String | The xid of the dependent document. |
| TargetXid | String | The xid of the document depended upon (empty if unresolved). |
| TargetUri | String | The raw href/URI of the dependency as authored in the document. |
| RefType | String | The dependency kind (for example tm:extends, tm:ref, links.rel=type). |
| Resolved | Boolean | True if the dependency resolved to a stored document. |

### Reference types

<a id="type-HasWoTProjection"></a>

| NodeId | BrowseName | InverseName | Subtype of | Description |
|---|---|---|---|---|
| ns=2;i=64060 | HasWoTProjection | WoTProjectionOf | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-5/11.3) | Links a stored WoT document resource (source) to the root node of its derived AddressSpace projection (target). Used to correlate materialized nodes and their NodeVersion with the canonical document, and to find the document behind a projected node. |

### Methods

| Method | Owning type | Input arguments | Output arguments |
|---|---|---|---|
| Refresh | [WoTRegistryType](#type-WoTRegistryType) | Selection, Options, ExpectedGeneration, RequestId | Summary, Results, NewGeneration |
| Validate | [WoTDocumentType](#type-WoTDocumentType) | (none) | Outcome |
| SetEnabled | [WoTDocumentType](#type-WoTDocumentType) | Enabled, ExpectedEpoch | (none) |
| SetDefaultVersion | [WoTDocumentType](#type-WoTDocumentType) | VersionId, ExpectedEpoch | (none) |

### Well-known instances

| BrowseName | NodeId | TypeDefinition | Note |
|---|---|---|---|
| WoTRegistry | ns=2;i=64100 | [WoTRegistryType](#type-WoTRegistryType) | The server-wide WoT Connectivity 1.1 registry, a well-known component of the Server object. Its stored Thing Description / Thing Model files are canonical; the projected AddressSpace is derived. It is the notifier for the WoT resource lifecycle events raised by its groups and resources. |

### Legacy model (OPC 10100-1 v1.02 — preserved, deprecated)

The published OPC 10100-1 v1.02 WoT Connectivity model is incorporated into this combined NodeSet unchanged, at its exact published NodeIds (`1..172`) and NodeClasses (preserved from the pinned `legacy/WotConnection.csv`). Because the additive registry supersedes it, the whole management/upload surface carries `ReleaseStatus="Deprecated"` — it is deprecated, not removed, so existing 1.02 clients keep working. The `WoTAssetConnectionManagement` object remains at its published NodeId and callable. Method signatures are unchanged and are listed in §13.1.

<a id="type-WoTAssetConnectionManagementType"></a>
<a id="type-IWoTAssetType"></a>
<a id="type-WoTAssetConfigurationType"></a>
<a id="type-WoTAssetFileType"></a>
<a id="type-HasWoTComponent"></a>

| NodeId | BrowseName | NodeClass | Subtype of | Release status |
|---|---|---|---|---|
| ns=2;i=1 | WoTAssetConnectionManagementType | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) | Deprecated |
| ns=2;i=42 | IWoTAssetType | ObjectType | [BaseInterfaceType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) | Deprecated |
| ns=2;i=105 | WoTAssetConfigurationType | ObjectType | [BaseInterfaceType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) | Deprecated |
| ns=2;i=110 | WoTAssetFileType | ObjectType | [FileType](https://reference.opcfoundation.org/specs/OPC-10000-20/4.2) | Deprecated |
| ns=2;i=142 | HasWoTComponent | ReferenceType | [HasComponent](https://reference.opcfoundation.org/specs/OPC-10000-5/11.3) | Deprecated |

| Well-known instance | NodeId | TypeDefinition | Release status |
|---|---|---|---|
| WoTAssetConnectionManagement | ns=2;i=31 | [WoTAssetConnectionManagementType](#type-WoTAssetConnectionManagementType) | Deprecated |

## Annex B — Incorporated 1.02 to registry crosswalk (informative)

This annex maps each OPC 10100-1 v1.02 element to its registry equivalent in revision 1.1. The incorporated 1.02 signatures and node numbering are unchanged (Section 13); the mapping shows how a server backs the deprecated asset-management surface with the registry.

| 1.02 element | 1.02 signature / shape | Registry equivalent (revision 1.1) |
|---|---|---|
| WoTAssetConnectionManagement | Well-known Object under Objects (deprecated) | Coexists with the well-known WoTRegistry (ns=2;i=64100) under Server. |
| CreateAsset | (in String AssetName, out NodeId AssetId) | CreateResource of a ThingDescriptionFileType in a default group; AssetId is the projected Object NodeId. |
| WoTFile / WoTAssetFileType | FileType with CloseAndUpdate | The ThingDescriptionFileType resource's inherited FileType (Open/Read/Write/Close). |
| CloseAndUpdate | (in UInt32 FileHandle) | Write-close of the resource + implicit single-resource Refresh (validate + project). |
| DeleteAsset | (in NodeId AssetId) | SetEnabled(false) + inherited xRegistry Delete of the backing resource. |
| DiscoverAssets | (out String[] AssetEndpoints) | Preserved unchanged; discovered TDs become thingdescription resources. |
| CreateAssetForEndpoint | (in String AssetName, in String AssetEndpoint, out NodeId AssetId) | Preserved unchanged; the auto-generated TD is stored as a resource. |
| ConnectionTest | (in String AssetEndpoint, out Boolean Success, out String Status) | Preserved unchanged. |
| SupportedWoTBindings | UriString[] Property | Surfaces the registry SupportedBindings / SelectedBindings set. |
| IWoTAssetType.<WoTPropertyName> | HasWoTComponent Variables | Legacy references preserved; registry instances also carry HasWoTProjection to their document. |
| HasWoTComponent | Subtype of HasComponent, inverse WoTComponentOf | Preserved; the registry adds HasWoTProjection (ns=2;i=64060) for document correlation. |

## Annex C — Example ingest-to-subscribe flow (informative)

The worked examples in `examples/` (a Thing Model, a matching Thing Description, an invalid Thing Description and a representative refresh-results document) exercise the registry-first lifecycle. The sequence below shows the canonical ingest, validate, refresh (shadow switch) and subscribe flow.

```mermaid
sequenceDiagram
  actor Op as Operator/Client
  participant Reg as WoTRegistry
  participant Grp as Group (TD/TM)
  participant Doc as Document (FileType)
  participant Proj as Projection (shadow then active)
  Op->>Grp: CreateResource(TM) then Open/Write/Close (TM bytes)
  Op->>Grp: CreateResource(TD) then Open/Write/Close (TD bytes)
  Op->>Reg: Refresh(Selection=all, Atomicity=PerClosure)
  Reg->>Doc: Validate format + compatibility
  Doc-->>Reg: ValidationOutcome (TM ok, TD ok, broken=Failed)
  Reg->>Proj: Build shadow generation for valid closure
  Proj-->>Reg: Bind forms to binder plans
  Reg->>Proj: Atomic switch then retire prior gen after drain
  Reg-->>Op: Summary + Results, NewGeneration
  Reg->>Op: WoTRefreshCompletedEventType
  Reg->>Op: WoTValidationFailureEventType (broken)
  Op->>Proj: Subscribe to projected Variable (survives future switches)
```

The invalid Thing Description (`03-invalid-thing-description.td.jsonld`) stays stored, reports `LoadState=Failed`, and does not disturb the active projection of any other resource; the refresh results (`04-refresh-results.json`) record its failing phase and reason alongside the two successful projections.
