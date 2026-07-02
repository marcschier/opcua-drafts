---
name: opcua-scenario-binding
description: >-
  Generate OPC UA PubSub Scenario Bindings for any companion specification. Given a
  companion-spec NodeSet2.xml, classify its Variables and Methods into integration
  Scenarios (Observability, PredictiveMaintenance, AnomalyDetection, …) and routing
  Kinds (Telemetry, Status, Event, Command, …), emit type-level bindings as
  RelativePaths, and produce (a) a machine-readable ScenarioBindingConfiguration
  descriptor, (b) a human-readable binding annex, and optionally (c) a UANodeSet
  binding fragment. Implements the "OPC UA — PubSub Scenario Binding" base-namespace
  specification (core-specs/pubsub-binding). WHEN: add PubSub bindings to a companion
  spec, expose a companion spec over PubSub, generate scenario bindings, PubSub
  scenario annex, bind variables to scenarios, make a model observable/analytics-ready.
---

# OPC UA PubSub Scenario Binding

This skill makes any OPC UA Information Model **consumable over PubSub for integration
scenarios** by producing the bindings defined in the *OPC UA — PubSub Scenario Binding*
specification (`core-specs/pubsub-binding/OPC-UA-PubSub-Scenario-Binding.md`). It does the
*authoring* (semantic classification, which a human/LLM is good at); a deterministic
generator does the *expansion* into artifacts (which a program is good at).

Read the specification first — this skill assumes its two-layer contract:

- **Per-companion-spec grouping**: a `ScenarioBindingGroupType` anchor per descriptor
  carries the stable `CompanionSpecificationUri` and all `ModelNamespaceUris`; the
  registry and per-instance containers hold groups, and groups hold bindings.
- **Routing** (for a generic bridge): a `ScenarioUri` per binding + a `Kind` per item.
- **Semantic cross-reference** (for the ultimate consumer): each item retains
  `TypeDefinition`, namespace-qualified `BrowseName`, `ModelNamespaceUri` and any
  dictionary entry, and this is propagated into Part 14 `DataSetMetaData`.
- **DataSet class and cardinality**: each `ScenarioBinding` is classified as `DataItems`
  (a Part 14 `PublishedDataItems` DataSet of grouped Variables) or `Events` (a
  `PublishedEvents` DataSet of selected event fields from a notifier), carries a
  deterministic `DataSetClassId`, and may set a `DataSetCardinalityPath` that tells
  a bridge which matched level produces one DataSet per instance. Those DataSets share
  the same DataSet class.

## When to use

Use this skill when a user wants to expose a companion specification (or any device /
vendor model) over OPC UA PubSub for analytics, observability, predictive maintenance,
anomaly detection, energy management, alarm distribution, or fleet/compliance — without
hand-writing PubSub configuration per project.

## Inputs

1. The companion spec **NodeSet2.xml** (required) — the source of types, members and BrowseNames.
2. The companion spec **document** (optional but recommended) — for its own scenario/PubSub
   section, EU/engineering-unit hints, and any existing analytics guidance.
3. The **target Scenario set** (optional) — defaults to the six baseline Scenarios below;
   the user may add vendor Scenarios (their own URI authority).

## Outputs

Per companion spec (see the worked examples under `core-specs/pubsub-binding/examples/`):

- `<Domain>.ScenarioBinding.json` — the machine-readable **ScenarioBindingConfiguration**
  descriptor (single source of truth; the authoring DSL below).
- `Opc.Ua.<Domain>.ScenarioBinding.NodeSet2.xml` — the **binding instances**: a compact
  *theoretical instance* of the bound type in an example namespace, with a `ScenarioBindings`
  container holding a per-companion-spec `ScenarioBindingGroup`, with the
  `ScenarioBinding`/`BoundItem` instances nested below it (see "Two-level authoring").
- `OPC-UA-<Domain>-PubSub-Scenario-Binding-Addendum.md` — the companion-spec **addendum**:
  scope, the per-scenario annex tables, and diagrams showing where the bindings live on the
  theoretical instance.

**Reference implementation (use it, don't reinvent):**
`core-specs/pubsub-binding/examples/tools/build_bindings.py` (+ `nodeset_util.py`) is a
deterministic generator that reads the descriptor, **resolves and validates every
`BrowsePath` against the published companion NodeSet**, synthesises the instance overlay, and
emits the addendum (annex tables + two mermaid diagrams). Author the descriptor, then run it:
`python tools/build_bindings.py <domain>/<Domain>.ScenarioBinding.json`. The base companion
NodeSets live (gitignored) under `examples/tools/ref/`. Worked examples: `examples/pumps/`
(from the official `Pumps/instanceexample.xml`) and `examples/robotics/` (synthesised
`MotionDeviceSystem`).

Do **not** invent a domain example inside this skill; always generate from the actual input
NodeSet, and never claim a `BrowsePath` you have not resolved against that NodeSet.

## Procedure

### 1. Parse the model

Walk the target `ObjectType`'s instance declarations to enumerate bindable Variables/Methods
with their type-level RelativePath, namespace-qualified `BrowseName`, `DataType`, `ValueRank`,
`ModellingRule` and `TypeDefinition`. **Two nesting styles must both be followed** (this is the
key correctness trap): the children of a component are the merge of (a) its `TypeDefinition`'s
instance declarations *and* (b) any **inline** references declared directly on the component
node. Pump-style models nest purely by TypeDefinition (`Operational` → `MeasurementsType` →
`Speed`); robot-style models nest by inline **placeholders** (`MotionDevices` folder →
`<MotionDeviceIdentifier> : MotionDeviceType` → `Axes` → `<AxisIdentifier> : AxisType` → …).
`nodeset_util.NodeSetDB.walk` already does this merge; reuse it. Placeholder segments
(`<…Identifier>`) stay in the type-level BrowsePath; on a real server a placeholder path
**can match multiple instances** (per the base spec's resolution rules), and a binding's
`dataSetCardinalityPath` selects which placeholder level produces one DataSet per matched
instance. The illustrative overlay materialises representative concrete paths for display;
runtime multi-match expansion is a bridge/Server realization rule.

### 2. Classify each item's Kind (routing role)

`Kind` is domain-agnostic. Apply, in order:

| Signal in the model | Kind |
|---|---|
| Method node | `Command` |
| Variable whose TypeDefinition derives from a condition/alarm/event type, or whose name ends `Event`/`Alarm`/`Fault`/`Trip` | `Event` |
| Variable named `*State`, `*Status`, `*Mode`, `Enabled`, `Ready`, `Health`, or DataType is an Enumeration/Boolean state | `Status` |
| Variable named `*SetPoint`, `*Setpoint`, `*Command`, `*Target`, writable and control-like | `Setpoint` |
| Static nameplate/identity property (`Manufacturer`, `Model`, `SerialNumber`, `*Rating`, asset id) | `Identification` |
| Configuration/parameter property that changes rarely (`*Configuration`, thresholds, limits) | `Configuration` |
| Numeric measured Variable (`AnalogItemType`/has `EngineeringUnits`, or continuous physical quantity) | `Telemetry` |
| Monotonic total/accumulator (`*Count`, `*Hours`, `*Energy`, `*Total`) | `Counter` |
| Aggregated KPI or computed value | `Metric` |
| Anything else exposed | `Other` |

`Kind` values are exactly the members of `BoundItemKindEnum` in the spec:
`Telemetry`, `Status`, `Configuration`, `Metric`, `Counter`, `Event`, `Command`,
`Setpoint`, `Identification`, `Other`. When unsure between `Telemetry` and a total,
prefer `Telemetry` for instantaneous values and `Counter` for monotonic accumulators.

### 3. Assign items to Scenarios

An item may belong to **several** Scenarios. Use these heuristics; a binding is created per
(Scenario, Direction) with the items assigned to it.

| Scenario URI (`…/UA/PubSub/Scenarios/<Name>`) | Include items that are… |
|---|---|
| `Observability` | operational Telemetry + Status + primary Events; the "what's happening now" set an HMI would show. |
| `PredictiveMaintenance` | usage/wear Counters and Metrics (`*Hours`, `*Count`, temperatures, pressures, vibration), plus maintenance-relevant Status/Events. |
| `AnomalyDetection` | high-resolution correlated Telemetry (electrical, thermal, mechanical signals) suitable for baseline/deviation models. |
| `EnergyAndLoadManagement` | power/load/energy/demand Telemetry & Metrics and related Setpoints/Commands. |
| `AlarmAndEventDistribution` | all Event/Alarm items and their acknowledge/reset Methods. |
| `FleetAndCompliance` | identity/nameplate `Identification` + compliance-relevant Metrics/Events for multi-site reporting. |

Set each binding's **Direction** (a `ScenarioBindingDirectionEnum` value — the role the
*server* offers): `Publisher` for read/telemetry scenarios (a client sets up a subscriber);
`Subscriber` when a client feeds data into the server; `ActionInvoker` for delivering
Commands to bound Methods; `ActionResponder` when clients invoke bound Actions;
`Bidirectional` when both apply.

Give each item a stable `FieldName` (default: the BrowseName; disambiguate placeholders by
appending the matched BrowseName as the spec requires). Set the descriptor-level
`companionSpecificationUri` to the stable URI for the companion specification itself (not a
namespace URI), and `modelNamespaceUris` to every namespace URI that specification defines or
covers; these become the per-spec group identity.

### 4. Classify each scenario's content as Data or Event

Each `ScenarioBinding` defines one DataSet class; `dataSetCardinalityPath` may cause a bridge
to realize several DataSet instances of that same class. Set its `ContentKind`
(`ScenarioContentKindEnum`) before emitting the descriptor:

- `DataItems` (default): a data DataSet (`PublishedDataItems`) made from grouped
  Variables. This is the common case for observability, maintenance, anomaly,
  energy/load and fleet data.
- `Events`: an event DataSet (`PublishedEvents`) made from an event notifier and selected
  event fields. Alarm/event/safety scenarios (for example `AlarmAndEventDistribution`)
  are typically Event DataSets.

For an Event DataSet identify:

1. the **event notifier** (`eventSourcePath`): the Object that raises events, often the
   bound root or a component with the `EventNotifier` attribute;
2. the **event type** being selected (record it as the event fields'
   `SourceTypeDefinition` when generated);
3. the **selected fields** as `BoundEventFieldType`/`BoundItemDataType` entries with
   `kind: "Event"` and `browsePath` segments relative to the event TypeDefinition
   (for example `EventId`, `EventType`, `Time`, `Severity`, `Message`, `SourceName`,
   `ConditionName`, plus domain-specific condition fields);
4. an optional `filter` (OPC UA `ContentFilter` where-clause), such as a severity
   threshold or event-type restriction.

### 5. Choose the DataSet cardinality anchor

For each binding, decide whether the binding describes one DataSet for the bound root or one
DataSet per matched placeholder/component level. Author `dataSetCardinalityPath` as a
RelativePath to that level; omit it only when the bound root (`"/"`) is the cardinality level.
When the path matches many instances, the bridge produces **one DataSet per matched instance**
of that level. Placeholder segments **below** the cardinality level expand into fields inside
that DataSet. The `DataSetClassId` remains shared by all those DataSets: one DataSetClass,
many DataSetWriters.

For robotics, prefer per-device cardinality for device-scoped scenarios:
`/MotionDevices/<MotionDeviceIdentifier>` means one DataSet per motion device; item paths such
as `/MotionDevices/<MotionDeviceIdentifier>/Axes/<AxisIdentifier>/ParameterSet/ActualPosition`
then put axis-level placeholders below the device cardinality and make them fields. A binding's
item paths should sit under its cardinality path; if they do not, split the binding or choose a
higher cardinality anchor.

### 6. Reuse & extend base facet bindings

Before duplicating a scenario for a derived type, check whether the same integration facet is
already bound on a base ObjectType, an Interface, or an AddInType. If so, author the deriving
binding as a **delta**: set `baseDataSetClassIds` to the base facet binding classes it extends
or composes, and list only added or overridden fields. The deriving binding still has its own
deterministic `DataSetClassId`; `baseDataSetClassIds` advertises the class lineage.

Choosing a composition axis:

- **Subtype** (`HasSubtype`) is an is-a refinement: the derived ObjectType inherits the base
  binding and adds or refines fields.
- **Interface facet** (`HasInterface`) is a contract capability many unrelated types implement;
  it adds no new structure, but its fields compose with the host DataSet when present.
- **AddIn** (`HasAddIn`, a subtype of `HasComponent`) is a reusable structural block, such as a
  GPS/Location object, that brings its own sub-objects and whose fields compose into the host
  DataSet.

Field removal is not supported: a derived DataSet is always a **superset** of each base it
extends. To refine an inherited field (for example `samplingIntervalHint` or `browsePath`), add
a bound item with the same `fieldName`; composition uses override-by-`fieldName`. At realization
time, the bridge composes the effective DataSet by union over the instance's supertypes,
`HasInterface` targets and `HasAddIn` children, advertises contributing base classes in
`baseDataSetClassIds`, and tags inherited fields with `sourceScenarioBindingClassId`. A
`HasBaseBinding` reference may be emitted for browsing convenience, but the portable lineage
carrier is `baseDataSetClassIds`.

### 7. Fill the semantic cross-reference (mechanical)

For every item, populate from the NodeSet (do not guess):
`SourceTypeDefinition`, `SourceBrowseName` (with namespace), `ModelNamespaceUri`,
`AttributeId` (13/Value unless otherwise), and `SemanticReferenceUri` — set the last from
the identifier of any `HasDictionaryEntry` target (OPC 10000-19) or a known IRDI/CDD, if the
model has one. For data items set `BrowsePath` to the RelativePath from the type root
(recommended locator); leave absolute NodeIds unset for type-level bindings. For event
fields, `BrowsePath` is relative to the selected event TypeDefinition and the generated
`EventFieldOperand` is the corresponding Part 14 `SimpleAttributeOperand`.

### 8. Compute the DataSet class identity (mechanical)

Every binding gets a deterministic `DataSetClassId` (Part 14 `Guid`) with grain
**(scenario × bound type)**. The generator computes it; do **not** author it in the
descriptor:

```text
uuid5(fc164bdb-8705-58e9-ab11-7b1ed155b4e8,
      "<ScenarioUri>|<AppliesToType as namespaceUri;BrowseName>|<MajorVersion>")
```

`MajorVersion` is `configurationVersion.majorVersion` (absent ⇒ `1`). The same scenario, type
and major version therefore produce the same DataSet class across servers, making it the
cross-server recognition key. The reference generator emits `DataSetClassId` (and `ContentKind`)
on each browsable `ScenarioBinding` instance. Propagation to `DataSetMetaData.dataSetClassId`
and the realizing `PublishedDataSet.DataSetClassId` is a **realization** step the base spec
requires *where PubSub is configured* (§5.5) — it is not produced by the example generator.

### 9. Emit the descriptor

Write `ScenarioBindingConfiguration` (see format below). Include the top-level
`companionSpecificationUri` and `modelNamespaceUris` so the generator can emit one
`ScenarioBindingGroupType` per descriptor, with all bindings nested under that group. This is
the single source; the annex and the NodeSet fragment are **derived** from it, never authored
separately.

### 10. Generate the addendum + instance overlay

Run the reference generator (`build_bindings.py`) on the descriptor. It renders one annex
table per Scenario (linking each referenced base type to `https://reference.opcfoundation.org/`
and own concepts to the base spec), emits the instance-overlay NodeSet with a
`ScenarioBindingGroupType` carrying `CompanionSpecificationUri` and `ModelNamespaceUris`, nests
the `ScenarioBinding` objects under that group, emits per-binding `DataSetClassId`,
`ContentKind` and `DataSetCardinalityPath` (when authored), and emits `BoundEventFieldType`
items for event DataSets, then assembles the addendum. Leave transport/security/addressing as
deployment parameters — never
bake them in. Exposing the full Part 14 `DataSetMetaData` (fields + `dataSetClassId` +
`configurationVersion`) so a consumer can obtain the class schema offline is a capability the
base spec defines (§5.8); a Server SHOULD populate it, but the example generator does not emit
the full metadata value.

### 11. Validate

- **Every `BrowsePath` resolves against the input NodeSet** — the generator fails hard if not;
  never ship a path you have not resolved. For Event DataSets, data-source paths resolve
  from the bound type while event field paths are validated against the selected event type.
- Every item has a `Kind`, a `FieldName` and a complete semantic cross-reference.
- Every descriptor has `companionSpecificationUri` and `modelNamespaceUris`, and the overlay
  nests bindings under that per-companion-spec group.
- Every binding has the correct `contentKind`; Event bindings have an `eventSourcePath` or
  intentionally default to the bound root.
- Every binding has a deliberate `dataSetCardinalityPath` (or intentionally defaults to the
  bound root), and its item paths sit under that cardinality path unless the binding is split.
- `DataSetClassId` is generated, stable for `(ScenarioUri, AppliesToType, MajorVersion)`,
  shared by all DataSets produced for a cardinality match, and appears consistently in the
  binding and PubSub metadata.
- Derived bindings list only delta fields, reference base classes via `baseDataSetClassIds`,
  and never remove inherited fields (a derived DataSet is a superset).
- When present, `DataSetMetaData` includes the fields, `dataSetClassId` and
  `configurationVersion`.
- Scenario URIs are well-formed; vendor Scenarios use the vendor's own URI authority and
  **not** the reserved `…/opcfoundation.org/UA/PubSub/Scenarios/` root.
- Field names are unique within a binding.
- The overlay NodeSet is well-formed, NodeIds unique, and every reference target resolves
  against the base spec + companion + DI/IA/Machinery NodeSets.
- Every mermaid diagram renders (`mmdc`).

## Two-level authoring: type-level definition + instance overlay

A companion specification is owned by *its* namespace, so **you cannot add `HasInterface` or a
`ScenarioBindings` component to the base companion type** (e.g. `PumpType`,
`MotionDeviceSystemType`) from an addendum. Author the bindings at two levels instead:

1. **Type-level definition (reusable, portable).** The `ScenarioBindingConfiguration`
   descriptor + the annex express each binding as a `BrowsePath` (RelativePath) from the type
   root. This does not touch the base type and applies to *every* conforming instance. It is
   the normative-recommendation artifact a future revision of the companion spec (or a server)
   would adopt. The descriptor also names the per-companion-spec group identity with
   `companionSpecificationUri` and `modelNamespaceUris`, preventing BrowseName collisions when
   multiple companion specs publish bindings into one registry.
2. **Instance overlay (concrete, illustrative).** In your **own example namespace**
   (`http://opcfoundation.org/UA/PubSub/Examples/<Domain>/`), synthesise a compact
   *theoretical instance* of the bound type — you own it, so you may apply `IPubSubScenarioBoundType`
   and hang a `ScenarioBindings` container off it (`HasComponent`). Emit the
   `ScenarioBindingGroup` instance under `ScenarioBindings`, then the `ScenarioBinding`/`BoundItem`
   instances below that group.

**Two locators, one per level.** On the type level a `BoundItem` uses **`BrowsePath`**; on the
instance overlay it uses **`BindsToNode`** pointing at the concrete signal node (both are
defined by the base spec). The overlay materialises only the parent-chain objects and the
bound leaf for each path — it is illustrative, not a conformant full instance; say so.

**Theoretical instance.** Prefer the companion's official instance example if one exists (e.g.
Pumps `instanceexample.xml`); otherwise synthesise a minimal one. **Placeholder path segments**
(`<AxisIdentifier>`) become concrete instance names (`Axis_1`) in the overlay while the
type-level BrowsePath keeps the placeholder.

**Diagram conventions (two per addendum).** (a) a *bindings overview*
(instance → ScenarioBindings → per-spec ScenarioBindingGroup → per-scenario ScenarioBinding → BoundItems); (b) an *instance
placement* diagram (instance → `HasInterface`/`HasComponent` → ScenarioBindings → group → binding →
BoundItem → `BindsToNode` → the signal node), so a reader sees exactly where bindings live.

## Domain heuristics learned from the worked examples

- **Measurement-rich models (e.g. Pumps).** Most signals live under one operational group
  (`Operational/Measurements/*`): flow/head/pressure/power/temperatures → Telemetry,
  efficiencies → Metric, start counters → Counter, nameplate under `Identification/*` →
  Identification. Scenarios map cleanly and densely.
- **Structure/state-machine models (e.g. Robotics).** Fewer flat analog measurements; signals
  are nested under placeholders (`MotionDevices/<…>/Axes/<…>/ParameterSet/ActualPosition`,
  `PowerTrains/<…>/<Motor…>/ParameterSet/MotorTemperature`, `Controllers/<…>/ParameterSet/*`).
  Lean on axis/motor Telemetry, controller thermals, **Status/Event** from `SafetyStates`
  (EmergencyStop/ProtectiveStop/OperationalMode), and nameplate for FleetAndCompliance. Expect
  more `Status`/`Event` and fewer `Telemetry` than a measurement-rich model. Choose a
  placeholder cardinality anchor deliberately: for device-scoped robotics scenarios use
  `/MotionDevices/<MotionDeviceIdentifier>` so each motion device gets its own DataSet, while
  axis/motor placeholders below that level become fields.
- **Event/safety scenarios.** Do not model alarm streams as ordinary grouped Variables when
  the domain exposes OPC UA Events/Conditions. Use `contentKind: "Events"`, choose the
  notifier (`eventSourcePath`), select standard event fields plus domain-specific condition
  fields, and add a `filter` when the scenario is scoped to severity or event type.


## Descriptor DSL

A single JSON object — the **authoring DSL** consumed by `build_bindings.py`. You write the
intent (which type, which scenarios, Data vs Event content, which items by `BrowsePath`, which
`Kind`, and which companion-spec group owns them); the generator resolves each data
`BrowsePath` against the companion NodeSet, resolves event field paths against the selected
event type, and fills in the namespaces, source `BrowseName`, `TypeDefinition`, `DataType`,
`DataSetFieldId`, `EventFieldOperand` and `DataSetClassId` mechanically, then emits the grouped
overlay NodeSet + addendum. `DataSetMetaData`/`PublishedDataSet` propagation remains the
spec-defined realization step, not generated by this descriptor tool.
`browsePath` uses **plain BrowseNames** (no namespace prefix) — the generator recovers the
namespace per segment from the walk. Keep placeholder segments (`<AxisIdentifier>`) verbatim.

```json
{
  "domain": "Pumps",
  "appliesToType": "PumpType",
  "baseModelNamespaceUri": "http://opcfoundation.org/UA/Pumps/",
  "companionSpecificationUri": "https://reference.opcfoundation.org/Pumps/",
  "modelNamespaceUris": ["http://opcfoundation.org/UA/Pumps/"],
  "exampleNamespaceUri": "http://opcfoundation.org/UA/PubSub/Examples/Pumps/",
  "instanceName": "ExamplePump",
  "summary": "one-line description used in the addendum scope",
  "companionSpec": { "name": "OPC UA for Pumps and Vacuum Pumps", "ref": "https://reference.opcfoundation.org/Pumps/…" },
  "instanceModel": { "note": "…theoretical instance note…", "ref": "https://github.com/OPCFoundation/UA-Nodeset/blob/latest/Pumps/instanceexample.xml", "refName": "Pumps/instanceexample.xml" },
  "configurationVersion": { "majorVersion": 1, "minorVersion": 0 },
  "baseNodeSets": ["Opc.Ua.Pumps.NodeSet2.xml", "Opc.Ua.Di.NodeSet2.xml", "Opc.Ua.Machinery.NodeSet2.xml"],
  "requiredModels": [
    { "uri": "http://opcfoundation.org/UA/Pumps/" },
    { "uri": "http://opcfoundation.org/UA/DI/" },
    { "uri": "http://opcfoundation.org/UA/Machinery/" }
  ],
  "scenarioBindings": [
    {
      "name": "Observability",
      "scenarioUri": "http://opcfoundation.org/UA/PubSub/Scenarios/Observability",
      "direction": "Publisher",
      "contentKind": "DataItems",
      "dataSetCardinalityPath": "/",
      "boundItems": [
        { "fieldName": "Speed", "kind": "Telemetry", "browsePath": "/Operational/Measurements/Speed", "samplingIntervalHint": 1000 }
      ]
    },
    {
      "name": "AlarmAndEventDistribution",
      "scenarioUri": "http://opcfoundation.org/UA/PubSub/Scenarios/AlarmAndEventDistribution",
      "direction": "Publisher",
      "contentKind": "Events",
      "eventSourcePath": "/",
      "eventType": "AlarmConditionType",
      "filter": { "whereClause": "Severity >= 500" },
      "boundItems": [
        { "fieldName": "EventId", "kind": "Event", "browsePath": "/EventId" },
        { "fieldName": "EventType", "kind": "Event", "browsePath": "/EventType" },
        { "fieldName": "Time", "kind": "Event", "browsePath": "/Time" },
        { "fieldName": "Severity", "kind": "Event", "browsePath": "/Severity" },
        { "fieldName": "Message", "kind": "Event", "browsePath": "/Message" },
        { "fieldName": "SourceName", "kind": "Event", "browsePath": "/SourceName" },
        { "fieldName": "ConditionName", "kind": "Event", "browsePath": "/ConditionName" }
      ]
    }
  ]
}
```

Field notes:
- `companionSpecificationUri` is the stable **spec-level** identifier for the companion
  specification group anchor. It is distinct from any namespace URI because one companion
  specification can define several model namespaces.
- `modelNamespaceUris` lists the namespace URIs the companion specification defines/covers;
  the generator emits them on the `ScenarioBindingGroupType` instance together with
  `CompanionSpecificationUri`, then nests this descriptor's bindings below that group.
- `appliesToType` is the plain BrowseName of the binding target: an `ObjectType`, Interface, or
  AddInType. The generator locates it in `baseNodeSets`.
- `baseNodeSets` are filenames under `examples/tools/ref/` (gitignored); `requiredModels` are
  the namespace URIs emitted as `<RequiredModel>` (order sets the ns indices).
- `fieldName` defaults to the last `browsePath` segment; make it unique within a binding.
- `direction` ∈ `Publisher` | `Subscriber` | `ActionInvoker` | `ActionResponder` |
  `Bidirectional`.
- `contentKind` ∈ `DataItems` | `Events`; omit it only for the default `DataItems`.
- `dataSetCardinalityPath` is a RelativePath to the level that determines DataSet
  multiplicity; omit it to default to the bound root. `"/"` (or an empty string) is accepted
  as an explicit alias for omitted and is normalized away — it is never emitted as an empty
  path segment. When it matches multiple
  instances, a bridge/Server produces one DataSet per matched instance. Placeholders below that
  path become fields in each DataSet, and all such DataSets share the binding's
  `DataSetClassId` (one DataSetClass, many DataSetWriters). For robotics,
  `"/MotionDevices/<MotionDeviceIdentifier>"` means one DataSet per motion device; item paths
  should sit under that path.
- `dataSetClassId` is **not** authored. The generator derives it deterministically as
  `uuid5(fc164bdb-8705-58e9-ab11-7b1ed155b4e8, "<ScenarioUri>|<namespaceUri;BrowseName>|<MajorVersion>")`.
- `baseDataSetClassIds` (per binding) is an array of Guid strings naming the base facet
  DataSet classes this binding extends or composes. Omit it for a root/base binding. When
  present, author only delta fields: added fields and overrides by identical `fieldName`; never
  restate inherited fields just to carry them forward.
- `kind` ∈ `Telemetry` | `Status` | `Configuration` | `Metric` | `Counter` | `Event` |
  `Command` | `Setpoint` | `Identification` | `Other`.
- `sourceScenarioBindingClassId` (per `boundItems` entry) is the provenance Guid for the
  scenario binding class that contributed the field. It is normally set by composition/the
  generator, not hand-authored, and lets subscribers extract exact per-facet field subsets from a
  merged DataSet.
- For a Method use `kind: "Command"` and a `browsePath` to the Method.
- For `contentKind: "Events"`, set `eventSourcePath` to the notifier RelativePath (`"/"` means
  the bound root). Event `boundItems` are selected event fields: their `browsePath` is relative
  to the event TypeDefinition, their `kind` is `Event`, and the generator emits
  `BoundEventFieldType`/`EventFieldOperand`.
- `eventType` (Events only) is the event type whose fields are selected — one of
  `BaseEventType` | `ConditionType` | `AlarmConditionType` | `SystemEventType` (default
  `BaseEventType`); the generator uses it as each event field's `SourceTypeDefinition`.
- `filter` is optional and represents the event `ContentFilter` where-clause; use it only when
  the scenario requires a severity, event-type or domain-specific restriction.

## Annex template (per Scenario)

```markdown
### Scenario: <Name>

*URI:* `http://opcfoundation.org/UA/PubSub/Scenarios/<Name>` · *Direction:* <Direction>

| Field | Kind | BrowsePath | Source type | DataType | Semantic ref |
|---|---|---|---|---|---|
| ActivePower | Telemetry | `/ElectricalMeasurements/ActivePower` | [AnalogUnitType](https://reference.opcfoundation.org/…) | Double | — |
```

Prefix the annex with a note that all NodeIds/paths are relative to the companion model and
that the bindings realize the *PubSub Scenario Binding* base specification.

## Quality bar

- Author intent (which items, which scenarios, which Kind) is the human/LLM contribution;
  everything mechanical (semantic fields, paths, tables) is generated from the NodeSet so it
  cannot drift.
- Never require a bridge to understand the domain — Kind + ScenarioUri must be enough to route.
- Keep the descriptor the single source of truth; regenerate the annex and fragment from it.
