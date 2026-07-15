---
name: opcua-observability-export
description: >-
  Generate OPC UA Observability Export bindings for any companion specification.
  Given a companion-spec NodeSet2.xml, classify its Variables and events into
  OpenTelemetry (OTEL) signals — metrics, logs and traces — and routing Kinds
  (Telemetry, Metric, Counter, Event, Dimension, …), emit type-level bindings as
  RelativePaths, and produce (a) a machine-readable binding descriptor (JSON), (b) a
  human-readable observability addendum, and (c) an instance-overlay UANodeSet.
  Implements the "OPC UA — Observability Export" base-namespace specification
  (core-specs/observability-export). WHEN: make a companion spec observable, export a
  model to OpenTelemetry / an observability system, generate metric/log/trace bindings,
  bridge OPC UA data to Prometheus/Grafana/Loki/Jaeger, expose a model as OTEL.
---

# OPC UA Observability Export

This skill makes any OPC UA Information Model **observable** by producing the bindings
defined in the *OPC UA — Observability Export* specification
(`core-specs/observability-export/OPC-UA-Observability-Export.md`). A binding declares how the
model's data lands in an observability system as **OTEL metrics, logs and traces**; it is served
over the classic client/server (RPC) interface by default, and PubSub is an optional realization.
The skill does the *authoring* (semantic classification, which a human/LLM is good at); a
deterministic generator does the *expansion* into artifacts (which a program is good at).

Read the specification first — this skill assumes its two-layer contract:

- **Discovery**: the Server Object has an `Observability` (`ObservabilityFolderType`) registry. A
  read-only **bridge** starts there, follows `RealizedBy` to per-companion-spec
  `ObservabilityBindingGroupType` nodes contained by `IObservableType`, then browses the bindings.
  There is a single kind of registry entry — no "scenarios", no "profiles".
- **Routing / OTEL** (for the bridge): each binding's `SignalKind` (`Metrics`/`Logs`/`Traces`) plus
  a per-item `Kind`, and the OTEL mapping metadata (metric instrument/unit/temporality, log
  template/severity, span name/identity/timing).
- **Semantic cross-reference** (for the ultimate consumer): each item retains `TypeDefinition`,
  namespace-qualified `BrowseName`, `ModelNamespaceUri` and any dictionary entry, propagated into
  Part 14 `DataSetMetaData` where PubSub is realized.
- **Class and cardinality**: each `ObservabilityBinding` is one `SignalKind` — `Metrics` (a Part 14
  `PublishedDataItems` DataSet of grouped Variables), `Logs` or `Traces` (a `PublishedEvents` DataSet
  of selected event fields, mapped to LogRecords or Spans) — carries a deterministic `DataSetClassId`,
  and may set a `DataSetCardinalityPath` telling a bridge which matched level produces one DataSet per
  instance. Those DataSets share the same class.

## When to use

Use this skill when a user wants to make a companion specification (or any device / vendor model)
**observable** — to export its live data to OpenTelemetry, Prometheus/Grafana, Loki/Splunk,
Jaeger/Tempo, Microsoft Fabric RTI, or an Arrow lakehouse — without hand-writing per-project
integration. It is **read-only**: it never invokes Methods, writes setpoints, or actuates.

## Inputs

1. The companion spec **NodeSet2.xml** (required) — the source of types, members and BrowseNames.
2. The companion spec **document** (optional but recommended) — for EU/engineering-unit hints, event
   models, and any existing observability guidance.
3. The **signals to export** (optional) — defaults to Metrics + Logs; add Traces when the model has a
   Program state machine or audit/correlated events worth exposing as spans.

## Outputs

Per companion spec — descriptor sources and tooling live under
`core-specs/extras/observability-export/examples/<spec>/`; the standardized addendum + overlay outputs
land under `core-specs/observability-export/<spec>/`:

- `<Domain>.ObservabilityExport.json` — the machine-readable **binding descriptor (JSON)**
  (single source of truth; the authoring DSL below).
- `Opc.Ua.<Domain>.ObservabilityExport.NodeSet2.xml` — the **binding instances**: a compact
  *theoretical instance* of the bound type in an example namespace, applying `IObservableType` and
  exposing one `ObservabilityBindingGroup` per companion specification directly on the instance, with
  the `ObservabilityBinding`/`BoundItem` instances nested below the group and the group carrying
  `Realizes` to the well-known `Observability` registry (see "Two-level authoring").
- `OPC-UA-<Domain>-Observability-Export-Addendum.md` — the companion-spec **addendum**: scope, the
  per-signal annex tables, and diagrams showing where the bindings live on the theoretical instance.

**Reference implementation (use it, don't reinvent):**
`core-specs/extras/observability-export/examples/tools/build_bindings.py` (+ `nodeset_util.py`) is a
deterministic generator that reads the descriptor, **resolves and validates every `BrowsePath`
against the published companion NodeSet**, synthesises the instance overlay, and emits the addendum
(annex tables + two mermaid diagrams) into `core-specs/observability-export/<spec>/`. Author the
descriptor, then run it (from `core-specs/extras/observability-export/examples/`):
`python tools/build_bindings.py <domain>/<Domain>.ObservabilityExport.json tools/ref`. The base
companion NodeSets live (gitignored) under
`core-specs/extras/observability-export/examples/tools/ref/`. Worked example descriptors:
`.../examples/pumps/` (from the official `Pumps/instanceexample.xml`) and `.../examples/robotics/`
(synthesised `MotionDeviceSystem`).

Do **not** invent a domain example inside this skill; always generate from the actual input NodeSet,
and never claim a `BrowsePath` you have not resolved against that NodeSet.

## Procedure

### 1. Parse the model

Walk the target `ObjectType`'s instance declarations to enumerate bindable Variables and event
sources with their type-level RelativePath, namespace-qualified `BrowseName`, `DataType`, `ValueRank`,
`ModellingRule` and `TypeDefinition`. **Two nesting styles must both be followed** (the key
correctness trap): the children of a component are the merge of (a) its `TypeDefinition`'s instance
declarations *and* (b) any **inline** references declared directly on the component node. Pump-style
models nest purely by TypeDefinition (`Operational` → `MeasurementsType` → `Speed`); robot-style
models nest by inline **placeholders** (`MotionDevices` folder → `<MotionDeviceIdentifier> :
MotionDeviceType` → `Axes` → `<AxisIdentifier> : AxisType` → …). `nodeset_util.NodeSetDB.walk`
already does this merge; reuse it. Placeholder segments (`<…Identifier>`) stay in the type-level
BrowsePath; on a real server a placeholder path **can match multiple instances**, and a binding's
`dataSetCardinalityPath` selects which placeholder level produces one DataSet per matched instance.

### 2. Classify each item's Kind (routing role)

`Kind` is domain-agnostic. Apply, in order:

| Signal in the model | Kind |
|---|---|
| Variable whose TypeDefinition derives from a condition/alarm/event type, or a selected event field | `Event` |
| Variable named `*State`, `*Status`, `*Mode`, `Enabled`, `Ready`, `Health`, or DataType is an Enumeration/Boolean state | `Status` |
| Static nameplate/identity property (`Manufacturer`, `Model`, `SerialNumber`, asset id, location) | `Identification` |
| Monotonic total/accumulator (`*Count`, `*Hours`, `*Energy`, `*Total`) | `Counter` |
| Aggregated KPI or computed value | `Metric` |
| Numeric measured Variable (`AnalogItemType`/has `EngineeringUnits`, or a continuous physical quantity) | `Telemetry` |
| A label/attribute that qualifies a binding's data points (not a measured value) | `Dimension` |
| Anything else exposed | `Other` |

`Kind` values are exactly the members of `BoundItemKindEnum` in the spec: `Telemetry`, `Status`,
`Metric`, `Counter`, `Event`, `Dimension`, `Identification`, `Other`. When unsure between `Telemetry`
and a total, prefer `Telemetry` for instantaneous values and `Counter` for monotonic accumulators.
An `Identification` item is usually best emitted as a `Dimension` (an OTEL Resource attribute).

### 3. Group items into signals (Metrics / Logs / Traces)

Each `ObservabilityBinding` exposes exactly one `SignalKind`; a group may hold several bindings. Sort
the bindable items into signals:

| SignalKind | Include items that are… | Part 14 form |
|---|---|---|
| `Metrics` | measured/aggregated/counter/status Variables + their dimensions — the numeric time series a metrics backend charts. | data DataSet (`PublishedDataItems`) |
| `Logs` | selected event fields of a notifier (event/alarm/condition streams) rendered as OTEL LogRecords. | event DataSet (`PublishedEvents`) |
| `Traces` | Program executions, audit events, or correlated event pairs rendered as OTEL spans. | event DataSet (`PublishedEvents`) |

A binding is homogeneous: a Metrics binding holds only Variables; a Logs/Traces binding holds only
event fields. Put metrics and events in **sibling** bindings in the same group, never mixed. Give
each item a stable `FieldName` (default: the BrowseName; disambiguate placeholders by appending the
matched BrowseName). Set the descriptor-level `companionSpecificationUri` to the stable URI for the
companion specification itself (not a namespace URI), and `modelNamespaceUris` to every namespace URI
that specification defines or covers.

### 4. Author the Logs / Traces detail

For a **Logs** binding identify:

1. the **event notifier** (`eventSourcePath`): the Object that raises events, often the bound root or
   a component with the `EventNotifier` attribute;
2. the **event type** being selected (`eventType`; recorded as the event fields' `SourceTypeDefinition`);
3. the **selected fields** as `boundItems` with `kind: "Event"` and `browsePath` segments relative to
   the event TypeDefinition (e.g. `EventId`, `EventType`, `Time`, `Severity`, `Message`, `SourceName`,
   plus domain-specific condition fields);
4. the OTEL LogRecord mapping: `logTemplate` (a `{FieldName}` message template) or `logBodyFieldName`,
   plus `logSeverityFieldName` and `logTimestampFieldName`;
5. an optional `filter` (OPC UA `ContentFilter` where-clause), e.g. a severity threshold.

For a **Traces** binding identify the same event source, then the span mapping members: `spanNameTemplate`
or `spanNameFieldName`; `traceIdFieldName`, `spanIdFieldName`, `parentSpanIdFieldName`;
`spanStartTimeFieldName` and `spanEndTimeFieldName`; `spanCorrelationFieldName` (pairs a start event
with its end event into one span — e.g. a Program run id); `spanStatusFieldName`; and `spanKind`
(constant, default `Internal`). Program state-machine transitions and audit events are the natural
span sources; when no end time or correlation is available, each event is a zero-duration span.

### 5. Enrich Metrics for OTEL

For a Metrics binding, carry enough OpenTelemetry detail for a generic bridge to emit metrics
faithfully. Pick the instrument per metric with `metricInstrumentType` (or rely on the Kind default),
set `unit` (UCUM), `metricTemporality` and histogram `explicitBucketBoundaries` where relevant, and
declare binding-level dimensions with `kind: "Dimension"`: node-sourced dimensions use `browsePath`;
constant dimensions use `dimensionConstantValue` (e.g. `service.name`). Kind→instrument default:
`Telemetry`/`Metric` → `Gauge`; `Counter` → `Counter` (monotonic); `Status` → `Gauge`. An explicit
`metricInstrumentType` overrides the default. Dimensions that are well-known OTEL Resource attributes
(`service.name`, `service.namespace`, `host.name`) become Resource attributes; other dimensions are
per-data-point attributes.

### 6. Choose the DataSet cardinality anchor

For each binding, decide whether it describes one DataSet for the bound root or one DataSet per
matched placeholder/component level. Author `dataSetCardinalityPath` as a RelativePath to that level;
omit it only when the bound root (`"/"`) is the cardinality level. When the path matches many
instances, the bridge produces **one DataSet per matched instance**; placeholder segments **below**
the cardinality level expand into fields inside that DataSet. The `DataSetClassId` is shared by all
those DataSets: one class, many writers. For robotics, prefer per-device cardinality
(`/MotionDevices/<MotionDeviceIdentifier>`) so item paths like
`/MotionDevices/<MotionDeviceIdentifier>/Axes/<AxisIdentifier>/ParameterSet/ActualPosition` put axis
placeholders below the device cardinality and make them fields.

### 7. Reuse & extend base facet bindings

Before duplicating a binding for a derived type, check whether the same observability facet is already
bound on a base ObjectType, an Interface, or an AddInType. If so, author the deriving binding as a
**delta**: set `baseDataSetClassIds` to the base facet binding classes it extends or composes, and
list only added or overridden fields. The deriving binding keeps its own deterministic
`DataSetClassId`; `baseDataSetClassIds` advertises the lineage.

Choosing a composition axis:

- **Subtype** (`HasSubtype`) is an is-a refinement: the derived ObjectType inherits the base binding
  and adds or refines fields.
- **Interface facet** (`HasInterface`) is a contract capability many unrelated types implement; its
  fields compose with the host DataSet when present.
- **AddIn** (`HasAddIn`, a subtype of `HasComponent`) is a reusable structural block (e.g. a Location
  object) that brings its own sub-objects and whose fields compose into the host DataSet.

Field removal is not supported: a derived DataSet is a **superset** of each base it extends. To refine
an inherited field (e.g. `samplingIntervalHint` or `browsePath`), add a bound item with the same
`fieldName`; composition uses override-by-`fieldName`. At realization the bridge composes the effective
DataSet by union over supertypes, `HasInterface` targets and `HasAddIn` children, advertises
contributing base classes in `baseDataSetClassIds`, and tags inherited fields with
`SourceBindingClassId`. A `HasBaseBinding` reference may be emitted for browsing convenience, but the
portable lineage carrier is `baseDataSetClassIds`.

### 8. Fill the semantic cross-reference (mechanical)

For every item, populate from the NodeSet (do not guess): `SourceTypeDefinition`, `SourceBrowseName`
(with namespace), `ModelNamespaceUri`, `AttributeId` (13/Value unless otherwise), and
`SemanticReferenceUri` — set the last from the identifier of any `HasDictionaryEntry` target (OPC
10000-19) or a known IRDI/CDD, if present. For metric items set `BrowsePath` to the RelativePath from
the type root (recommended locator); leave absolute NodeIds unset for type-level bindings. For event
fields, `BrowsePath` is relative to the selected event TypeDefinition and the generated
`EventFieldOperand` is the corresponding Part 14 `SimpleAttributeOperand`.

### 9. Compute the DataSet class identity (mechanical)

Every binding gets a deterministic `DataSetClassId` (Part 14 `Guid`) with grain **(bound type ×
SignalKind × major version)**. The generator computes it; do **not** author it in the descriptor:

```text
uuid5(8d3280be-2bf7-5ab1-9898-15a237192577,
      "ObservabilityExport|<AppliesToType as namespaceUri;BrowseName>|<SignalKind>|<MajorVersion>")
```

`SignalKind` is the enum name (`Metrics`, `Logs` or `Traces`); `MajorVersion` is
`configurationVersion.majorVersion` (absent ⇒ `1`). The same bound type, signal kind and major version
therefore produce the same class across servers — the cross-server recognition key. The reference
generator emits `DataSetClassId` (and `SignalKind`) on each browsable `ObservabilityBinding`.
Propagation to `DataSetMetaData.dataSetClassId` and the realizing `PublishedDataSet.DataSetClassId` is
a **realization** step the base spec requires *where PubSub is configured* (§5.5) — not produced by the
example generator.

### 10. Emit the descriptor

Write the binding descriptor (JSON; see format below). Include the top-level
`companionSpecificationUri` and `modelNamespaceUris` so the generated structure can emit one
`ObservabilityBindingGroupType` per companion specification, with that spec's bindings nested under the
group. This is the single source; the annex and the NodeSet overlay are **derived** from it, never
authored separately.

### 11. Generate the addendum + instance overlay

Run the reference generator (`build_bindings.py`) on the descriptor. It renders one annex table per
binding (linking each referenced base type to `https://reference.opcfoundation.org/` and own concepts
to the base spec), emits the instance-overlay NodeSet with an `ObservabilityBindingGroupType` carrying
`CompanionSpecificationUri` and `ModelNamespaceUris` plus `Realizes` to the well-known `Observability`
registry, nests the `ObservabilityBinding` objects under the group, emits per-binding `DataSetClassId`
and `SignalKind`, `DataSetCardinalityPath` (when authored), the metric members for Metrics bindings and
`BoundEventFieldType` items for Logs/Traces bindings, then assembles the addendum. Leave
transport/security/addressing as deployment parameters — never bake them in.

### 12. Validate

- **Every `BrowsePath` resolves against the input NodeSet** — the generator fails hard if not; never
  ship a path you have not resolved. For Logs/Traces, event-field paths are validated against the
  selected event type.
- Every item has a `Kind`, a `FieldName` and a complete semantic cross-reference.
- Run `python tools/validate_examples.py` (overlay well-formedness, unique NodeIds, no dangling refs,
  full cross-NodeSet resolution) → must report `ERRORS: 0`.

## Two-level authoring: type-level definition + instance overlay

A companion specification is owned by *its* namespace, so **you cannot add `HasInterface` or binding
components to the base companion type** (e.g. `PumpType`, `MotionDeviceSystemType`) from an addendum.
Author the bindings at two levels instead:

1. **Type-level definition (reusable, portable).** The binding descriptor (JSON) + the annex express
   each binding as a `BrowsePath` (RelativePath) from the type root. This does not touch the base type
   and applies to *every* conforming instance. It is the artifact a future revision of the companion
   spec (or a server) would adopt. The descriptor names the companion-spec facet of each group with
   `companionSpecificationUri` and `modelNamespaceUris`.
2. **Instance overlay (concrete, illustrative).** In your **own example namespace**
   (`http://opcfoundation.org/UA/PubSub/Examples/<Domain>/`), synthesise a compact *theoretical
   instance* of the bound type — you own it, so you may apply `IObservableType` and expose one
   `ObservabilityBindingGroup` per companion specification directly on the instance (`HasComponent`),
   with `Realizes` to the well-known `Observability` registry. Emit the matching
   `ObservabilityBinding`/`BoundItem` instances below the group.

**Server-wide discovery.** A server exposes `Server` → `Observability` (`ObservabilityFolderType`),
which references per-spec `ObservabilityBindingGroupType` nodes via `RealizedBy`. Those groups are
contained by an `IObservableType` object and carry inverse `Realizes` back to the registry. A bridge
starts at the `Observability` registry, follows `RealizedBy` to groups, then browses the bindings and
bound items.

**Two locators, one per level.** On the type level a `BoundItem` uses **`BrowsePath`**; on the instance
overlay it uses **`BindsToNode`** pointing at the concrete signal node (both defined by the base spec).
The overlay materialises only the parent-chain objects and the bound leaf for each path — it is
illustrative, not a conformant full instance; say so.

**Diagram conventions (two per addendum).** (a) a *bindings overview* (`Server` → `Observability`
--`RealizedBy`--> per-spec `ObservabilityBindingGroup` → `ObservabilityBinding` → BoundItems); (b) an
*instance placement* diagram (instance → `IObservableType` → group --`Realizes`--> `Observability`,
plus group → binding → BoundItem → `BindsToNode` → the signal node).

## Domain heuristics learned from the worked examples

- **Measurement-rich models (e.g. Pumps).** Most signals live under one operational group
  (`Operational/Measurements/*`): flow/head/pressure/power/temperatures → Telemetry, efficiencies →
  Metric, start counters → Counter, nameplate under `Identification/*` → Identification/Dimension. A
  dense **Metrics** binding plus a **Logs** binding over the event notifier is the typical result.
- **Structure/state-machine models (e.g. Robotics).** Signals nest under placeholders
  (`MotionDevices/<…>/Axes/<…>/ParameterSet/ActualPosition`, `PowerTrains/<…>/<Motor…>/…`). Lean on
  axis/motor Telemetry and controller thermals for Metrics, `SafetyStates` for Logs, and a Program
  state machine (e.g. a motion job) for a **Traces** binding. Choose a placeholder cardinality anchor
  deliberately (`/MotionDevices/<MotionDeviceIdentifier>`).
- **Event/safety streams.** Do not model alarm streams as ordinary grouped Variables when the domain
  exposes OPC UA Events/Conditions. Use a `Logs` binding, choose the notifier (`eventSourcePath`),
  select standard event fields plus domain-specific condition fields, and add a `filter` when scoped
  to severity or event type.

## Descriptor DSL

A single JSON object — the **authoring DSL** consumed by `build_bindings.py`. You write the intent
(which type, which signals, which items by `BrowsePath`, which `Kind`, and which companion
specification owns them); the generator resolves each metric `BrowsePath` against the companion
NodeSet, resolves event field paths against the selected event type, and fills in the namespaces,
source `BrowseName`, `TypeDefinition`, `DataType`, `DataSetFieldId`, `EventFieldOperand` and
`DataSetClassId` mechanically, then emits the grouped overlay NodeSet + addendum. `browsePath` uses
**plain BrowseNames** (no namespace prefix) — the generator recovers the namespace per segment from
the walk. Keep placeholder segments (`<AxisIdentifier>`) verbatim.

```json
{
  "domain": "Pumps",
  "appliesToType": "PumpType",
  "baseModelNamespaceUri": "http://opcfoundation.org/UA/Pumps/",
  "companionSpecificationUri": "http://opcfoundation.org/UA/Pumps/",
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
  "observabilityBindings": [
    {
      "name": "Metrics",
      "signalKind": "Metrics",
      "dataSetCardinalityPath": "/",
      "boundItems": [
        { "fieldName": "Speed", "kind": "Telemetry", "metricInstrumentType": "Gauge", "unit": "1/min", "browsePath": "/Operational/Measurements/Speed", "samplingIntervalHint": 1000 },
        { "fieldName": "BearingTemperature", "kind": "Telemetry", "metricInstrumentType": "Histogram", "unit": "Cel", "explicitBucketBoundaries": [40, 60, 80, 100, 120], "browsePath": "/Operational/Measurements/BearingTemperature" },
        { "fieldName": "NumberOfStarts", "kind": "Counter", "metricInstrumentType": "Counter", "metricTemporality": "Cumulative", "monotonic": true, "browsePath": "/Operational/Measurements/NumberOfStarts" },
        { "fieldName": "SerialNumber", "kind": "Dimension", "browsePath": "/Identification/SerialNumber" },
        { "fieldName": "service.name", "kind": "Dimension", "dimensionConstantValue": "pump-observability" }
      ]
    },
    {
      "name": "Logs",
      "signalKind": "Logs",
      "eventSourcePath": "/",
      "eventType": "BaseEventType",
      "logTemplate": "{SourceName}: {Message} (severity {Severity})",
      "logSeverityFieldName": "Severity",
      "logBodyFieldName": "Message",
      "logTimestampFieldName": "Time",
      "boundItems": [
        { "fieldName": "EventId", "kind": "Event", "browsePath": "/EventId" },
        { "fieldName": "SourceName", "kind": "Event", "browsePath": "/SourceName" },
        { "fieldName": "Time", "kind": "Event", "browsePath": "/Time" },
        { "fieldName": "Severity", "kind": "Event", "browsePath": "/Severity" },
        { "fieldName": "Message", "kind": "Event", "browsePath": "/Message" },
        { "fieldName": "service.name", "kind": "Dimension", "dimensionConstantValue": "pump-observability" }
      ]
    }
  ]
}
```

Traces binding fragment (a Program run → one span):

```json
{
  "observabilityBindings": [
    {
      "name": "Traces",
      "signalKind": "Traces",
      "eventSourcePath": "/",
      "eventType": "AuditUpdateStateEventType",
      "spanNameTemplate": "{SourceName}:{ProgramName}",
      "spanCorrelationFieldName": "RunId",
      "spanStartTimeFieldName": "Time",
      "spanStatusFieldName": "Status",
      "spanKind": "Internal",
      "boundItems": [
        { "fieldName": "RunId", "kind": "Event", "browsePath": "/RunId" },
        { "fieldName": "ProgramName", "kind": "Event", "browsePath": "/ProgramName" },
        { "fieldName": "Time", "kind": "Event", "browsePath": "/Time" },
        { "fieldName": "Status", "kind": "Event", "browsePath": "/Status" },
        { "fieldName": "SourceName", "kind": "Event", "browsePath": "/SourceName" }
      ]
    }
  ]
}
```

Field notes:
- `companionSpecificationUri` is the stable **spec-level** identifier for the companion specification
  facet of each group. It is distinct from any namespace URI because one companion specification can
  define several model namespaces.
- `modelNamespaceUris` lists the namespace URIs the companion specification defines/covers; the
  generator emits them on each `ObservabilityBindingGroupType` instance together with
  `CompanionSpecificationUri`, adds `Realizes` to the well-known `Observability` registry, then nests
  the bindings below that group.
- `signalKind` ∈ `Metrics` | `Logs` | `Traces`. The generated `ObservabilityBinding` carries it as a
  property; it also drives the deterministic `DataSetClassId`. There is no `scenarioUri`/`direction`/
  `contentKind` — those concepts are removed.
- `appliesToType` is the plain BrowseName of the binding target: an `ObjectType`, Interface, or
  AddInType. The generator locates it in `baseNodeSets`.
- `baseNodeSets` are filenames under `core-specs/extras/observability-export/examples/tools/ref/`
  (gitignored); `requiredModels` are the namespace URIs emitted as `<RequiredModel>` (order sets the
  ns indices).
- `fieldName` defaults to the last `browsePath` segment; make it unique within a binding.
- `baseDataSetClassIds` (optional, array) lists base facet binding classes a derived/composed binding
  extends; the generator tags inherited fields with `SourceBindingClassId`.

## Annex template (per signal)

### Binding: <Name> (<SignalKind>)

- one-sentence purpose (what a bridge does with this signal);
- a table of bound items: `FieldName`, `Kind`, `BrowsePath`, resolved `BrowseName`, `DataType`,
  and — for Metrics — `MetricInstrumentType`/`Unit`; for Logs/Traces — the OTEL mapping members;
- the deterministic `DataSetClassId` and, when composed, its `BaseDataSetClassIds`.

## Quality bar

- Every `BrowsePath` resolves against the input NodeSet; event field paths resolve against the
  selected event type. Never ship an unresolved path.
- Every item has a `Kind`, a unique `FieldName`, and a complete semantic cross-reference.
- Every descriptor has `companionSpecificationUri` and `modelNamespaceUris`; the overlay nests
  bindings under the correct companion-spec group, each `Realizes`-linked to the `Observability`
  registry.
- Every binding has the correct `signalKind`; Logs/Traces bindings have an `eventSourcePath` (or
  intentionally default to the bound root) and their OTEL mapping members.
- Metrics carry an instrument type (or rely on the Kind default); dimensions are marked
  `kind: "Dimension"`.
- Every binding has a deliberate `dataSetCardinalityPath` (or intentionally defaults to the bound
  root), and its item paths sit under that cardinality path unless the binding is split.
- `DataSetClassId` is generated, stable for `(AppliesToType, SignalKind, MajorVersion)`, and shared by
  all DataSets produced for a cardinality match.
- Derived bindings list only delta fields, reference base classes via `baseDataSetClassIds`, and never
  remove inherited fields (a derived DataSet is a superset).
- The overlay NodeSet is well-formed, NodeIds unique, and every reference target resolves against the
  base spec + companion + DI/IA/Machinery NodeSets (`validate_examples.py` reports `ERRORS: 0`).
- Every mermaid diagram renders (`mmdc`).
