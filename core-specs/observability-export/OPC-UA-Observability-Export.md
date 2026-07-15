# OPC UA — Observability Export

**Working draft for submission to the OPC Foundation Working Group**
**Proposed Part: OPC 10000‑2xx (number to be assigned)**
**Namespace:** `http://opcfoundation.org/UA/` (base OPC UA namespace)
**Version:** 0.1.0 · **Date:** 2026-07-15

> **Status — working draft.** This document proposes an addition to the *base* OPC UA namespace and is intended for discussion by the Working Group. Together with `Opc.Ua.ObservabilityExport.NodeSet2.xml` and `Opc.Ua.ObservabilityExport.NodeIds.csv` it defines a small, transport-neutral **observability export** layer that a Server serves over the classic OPC UA client/server (RPC) interface and, optionally, realizes over PubSub ([OPC 10000-14](https://reference.opcfoundation.org/specs/OPC-10000-14/)). **All NodeIds are provisional** and drawn from a currently-unused block; final NodeIds are assigned by the OPC Foundation. Nothing here re-specifies classic Services or PubSub mechanics — it references them.

---

## 1 Scope

This specification defines an information model that lets an OPC UA Server, or a companion specification, **declare how the data of any Information Model lands in an observability system** — as metrics, logs and traces — and lets a generic **bridge** discover those declarations and forward the data to that observability system without understanding the domain semantics.

It specifies:

- a discoverable, server-wide **Observability** registry, reachable from the standard **Server Object**, that lists every observability-exporting object;
- an **ObservabilityBinding** that associates a bound Object or type with exactly one **OTEL signal** — a **metric** set, a **log** stream, or a **trace** stream — whose **bound items** are Variables or event fields;
- a normative mapping from those bindings to **OpenTelemetry (OTEL)** — metric instruments, LogRecords and Spans, plus Resource and attribute (dimension) handling — sufficient for a bridge to emit OTEL to an **OTEL Collector** (or directly to any observability backend);
- a **semantic cross‑reference** carried by each bound item back to the model that defines it, retained so it can be **exported to a disconnected consumer** (for example a subscriber that only sees a PubSub message);
- normative rules for locating bound items by **BrowsePath** (RelativePath) so that bindings can be authored once at the type level and resolved per instance;
- normative rules for realizing a binding through classic OPC UA Subscriptions and Reads as the baseline, and through OPC UA PubSub as an optional Part 14 realization where the Server provides it;
- the **Profiles and Conformance Units** for Servers and Clients.

OTEL is the normative reference target because it is the de-facto vendor-neutral wire and data model for metrics, logs and traces; the model is nonetheless **generic** — the same bindings drive any observability backend (§8), since the mapping metadata is expressed in OTEL-shaped but backend-agnostic terms.

It is explicitly **out of scope** to define new PubSub transports, message mappings, security, or the lifecycle of PubSub configuration; these are defined by [OPC 10000-14](https://reference.opcfoundation.org/specs/OPC-10000-14/) and referenced here for the optional PubSub realization. Invoking or writing to the Server (commands, setpoints, actuation) is out of scope: observability export is **read-only**.

### 1.1 Motivation

Companion specifications describe *what a thing is*. Getting that thing's live data into an **observability** system — metrics dashboards, log search, distributed tracing — is a separate, repetitive integration problem: someone must decide which Variables are metrics and of what instrument and unit, which event fields become structured log records, which Program or audit events become spans, and how each is labelled. Today this is solved ad-hoc, once per model and once per project, usually by hand-wiring an OPC UA client to a metrics/log agent.

This specification makes the decision **part of the model and discoverable at runtime**. A Server advertises, per bound object, exactly which nodes to observe and how they map to OTEL; a generic **bridge** — a read-only Client whose only job is to forward OPC UA data into an observability system — discovers the binding, uses classic Subscriptions/Reads as the baseline (or PubSub where the Server has realized the same binding as Part 14 configuration), and emits OTEL metrics, logs and spans. The bridge needs to understand *OTEL* and the *routing role*, not the pump, the robot or the generator.

### 1.2 Motivating use cases

The practical value is that a **single generic bridge** can light up observability for many machines with *no domain-specific code*: the Server has already decided which signals matter and what they mean. A consumer recognizes and routes the data by its OTEL signal and its stable `DataSetClassId`, not by knowing the pump, the robot or the generator. The use cases below are illustrative; product names are examples only and imply no endorsement.

```mermaid
flowchart LR
  subgraph Servers[OPC UA Servers with Observability Export]
    S1[Pumps]
    S2[Robotics]
    S3[Generators]
  end
  B["Generic bridge<br/>discovers Server/Observability<br/>Subscriptions/Reads or PubSub"]
  OT[OTEL Collector]
  M["Metrics backend<br/>Prometheus · Grafana · Fabric RTI"]
  L["Logs backend<br/>Loki · Splunk · Elastic"]
  TR["Traces backend<br/>Jaeger · Tempo · Zipkin"]
  S1 --> B
  S2 --> B
  S3 --> B
  B -->|OTLP metrics| OT --> M
  B -->|OTLP logs| OT --> L
  B -->|OTLP traces| OT --> TR
```

**Factory-floor metrics to OpenTelemetry and Grafana.** The Metrics binding declares which Variables are metrics — with their OTEL instrument type, unit and histogram buckets — and which items are dimensions. A bridge subscribes to the metric set and emits OTEL metrics to an OTEL Collector, which drives Grafana (or any metrics backend) for live factory-operations dashboards. Because the OTEL semantics are carried in the model, the same bridge lights up dashboards for a new machine or a new vendor with no per-model wiring.

**Structured logs from OPC UA events.** A Logs binding maps selected event fields of a notifier to OTEL LogRecords, with a message template, severity and timestamp. A bridge subscribes to the events and emits structured OTEL logs to any log backend (Loki, Splunk, Elastic), each record carrying the companion-model field names and the binding's dimensions as attributes.

**Traces from Program and audit events.** A Traces binding maps a Program state machine's executions — or correlated audit events — to OTEL spans, with trace/span identity, timing and status. A bridge emits spans to a tracing backend (Jaeger, Tempo, Zipkin), so an operation on the floor (a recipe run, a maintenance job) becomes a first-class trace correlated with the metrics and logs around it.

**Egress to any observability stack.** Because the mapping metadata is OTEL-shaped but backend-agnostic, the same bindings drive other stacks — Prometheus remote-write, Splunk HEC, Microsoft Fabric Real-Time Intelligence, or an Apache Arrow lakehouse — by a thin adapter in the bridge (§8). Where the Server realizes the binding over PubSub (Part 14), the same egress is a fan-out of `DataSetMessage`s.

## 2 Normative references

- [OPC 10000‑3](https://reference.opcfoundation.org/specs/OPC-10000-3/) — Address Space Model.
- [OPC 10000‑4](https://reference.opcfoundation.org/specs/OPC-10000-4/) — Services (TranslateBrowsePathsToNodeIds, RelativePath, Subscriptions).
- [OPC 10000‑5](https://reference.opcfoundation.org/specs/OPC-10000-5/) — Information Model (base types, Interfaces).
- [OPC 10000‑6](https://reference.opcfoundation.org/specs/OPC-10000-6/) — Mappings (DataType encodings: Binary, XML, JSON).
- [OPC 10000‑7](https://reference.opcfoundation.org/specs/OPC-10000-7/) — Profiles.
- [OPC 10000‑10](https://reference.opcfoundation.org/specs/OPC-10000-10/) — Programs (`ProgramStateMachineType`), for the trace mapping.
- [OPC 10000‑14](https://reference.opcfoundation.org/specs/OPC-10000-14/) — PubSub (PublishedDataSet, PublishedDataItems, PublishedEvents, DataSetWriter/Reader, DataSetMetaData, DataSetClassId).
- [OPC 10000‑19](https://reference.opcfoundation.org/specs/OPC-10000-19/) — Dictionary Reference (`HasDictionaryEntry`, IRDI/CDD).
- [OpenTelemetry specification](https://opentelemetry.io/docs/specs/otel/) — data model for metrics, logs and traces (informative external reference).
- [OTLP](https://opentelemetry.io/docs/specs/otlp/) — OpenTelemetry Protocol (informative external reference).

## 3 Terms, definitions and abbreviations

| Term | Definition |
|---|---|
| Observability system | Any system that ingests metrics, logs and/or traces for monitoring, alerting, search or analysis (e.g. an OTEL Collector and its backends). |
| Observability export | The act of forwarding OPC UA data into an observability system as OTEL metrics, logs or traces. |
| Observability binding | A transport-neutral association of a bound Object or type with exactly one OTEL signal — a metric set, a log stream, or a trace stream — and the mapping needed to emit it. Its bound items are homogeneous per binding: Variables for metrics, event fields for logs and traces. |
| Bound item | A metric value, dimension, or event field that an observability binding exposes, with routing and semantic metadata. |
| <a id="term-bound-root"></a>Bound root | The Object (an instance, or a type when authoring type‑level bindings) that a bound item's BrowsePath is resolved from. |
| <a id="term-binding-target"></a>Binding target | The TypeDefinitionNode a binding is declared on — an ObjectType, an Interface (facet), or an AddInType (an Interface and an AddInType are themselves ObjectTypes). Its type‑level BrowsePaths resolve against any instance that is‑a the ObjectType, implements the Interface (`HasInterface`), or composes the AddInType (`HasAddIn`). |
| Signal kind | The OTEL signal a binding exposes: `Metrics`, `Logs` or `Traces`. |
| Routing role (`Kind`) | The small, domain‑agnostic classification a bridge uses to forward an item (Telemetry, Metric, Counter, Event, Dimension, …). |
| Dimension | A bound item that is an OTEL attribute/label applied to every data point of its binding, rather than a measured value. |
| Semantic cross‑reference | The retained link from a bound item back to the model node that defines it (TypeDefinition, BrowseName, namespace, dictionary entry). |
| Bridge | A read-only Client whose sole purpose is to forward observable data from an OPC UA Server into an observability system, without understanding the domain semantics. |
| Realization | The concrete mechanism that carries a binding: classic OPC UA Subscriptions and Reads as the baseline, or optional Part 14 PubSub nodes (PublishedDataSet, DataSetWriter/Reader) where configured. |
| DataSetClassId | The Guid carried by Part 14 DataSetMetaData that identifies a binding/observability class independently of any Server instance. |
| OTEL | OpenTelemetry. PDS: PublishedDataSet. |

Key words **shall**, **should**, **may**, **shall not** are to be interpreted as in ISO/IEC directives; normative and informative content is marked as such.

## 4 Overview and concepts

### 4.1 The two‑layer contract

An observability binding carries two distinct kinds of metadata, and keeping them separate is the central design idea:

1. **Routing / OTEL metadata — for the bridge.** The binding's `SignalKind` says *which OTEL signal this serves* (metrics, logs, traces); the per‑item `Kind` says *how to forward this value* (a metric time series, a dimension, a log/trace field). For metrics the routing metadata also includes the OTEL instrument (`MetricInstrumentType`), unit, histogram buckets and temporality; for logs the `LogTemplate`/severity/timestamp field names; for traces the span name, identity, timing and status field names. A bridge configures itself from routing metadata alone, for any domain.
2. **Semantic metadata — for the consumer.** Each bound item also retains a **cross‑reference back to the model** that defines it: the source `TypeDefinition`, the namespace‑qualified `BrowseName`, the `ModelNamespaceUri`, and — where available — a dictionary entry ([OPC 10000‑19](https://reference.opcfoundation.org/specs/OPC-10000-19/), IRDI/CDD). This is what lets a *disconnected* consumer, holding only a PubSub message or an OTEL data point, recover what the value *means*.

The bridge never needs the semantic layer to do its job; it forwards it verbatim (as OTEL attributes / Part 14 FieldMetaData) so the ultimate consumer can use it.

### 4.2 Discovery

A Server exposes a server-wide `Observability` Object of [`ObservabilityFolderType`](#type-ObservabilityFolderType) as a component of the standard **Server Object** (`i=2253`); it is the discovery entry point. The registry references, through non-hierarchical [`RealizedBy`](#type-RealizedBy) references, every [`ObservabilityBindingGroupType`](#type-ObservabilityBindingGroupType) Object in the Server. A Client browses `Server/Observability`, follows `RealizedBy` to the groups, and browses each group's [`ObservabilityBindingType`](#type-ObservabilityBindingType) children.

Each [`ObservabilityBindingGroupType`](#type-ObservabilityBindingGroupType) is a `HasComponent` child of the [`IObservableType`](#type-IObservableType) Object instance it describes, and that Object is the group's single hierarchical parent. `RealizedBy` is non-hierarchical so the group can remain hierarchically contained by the bound instance while still being reachable from the registry; this avoids a second hierarchical parent and prevents a registry→group→instance hierarchy loop. Given a group, a Client browses the inverse `Realizes` reference back to the registry. The group carries `CompanionSpecificationUri` and `ModelNamespaceUris` for namespace matching, and it remains the BrowseName collision boundary for the bindings on that instance.

There is a single kind of registry entry; there is no notion of selectable "scenarios" or "profiles". A Server that exports observability data exposes the `Observability` registry and one group per (companion specification × observable instance).

### 4.3 Realization (hybrid)

A binding **declares** intent; whether and how it is realized over the wire is separate.

**A conforming Server is not required to implement OPC UA PubSub.** The default and most common case is a Server with **no PubSub configuration surface at all**: this specification references Part 14 *types* to describe an optional realization, but never requires *instances* of them — no `PublishSubscribe` object, `PublishedDataSet`, `DataSetWriter` or `WriterGroup` need exist. On such a Server a bridge reads a binding through **classic Subscriptions and Reads** (§6); this is the baseline realization.

Where a Server does implement PubSub, a binding **may** additionally be realized as Part 14 configuration (a `PublishedDataSet` and `DataSetWriter`), linked from the binding by [`ObservabilityRealizedBy`](#type-ObservabilityRealizedBy); the realizing node points back with inverse `RealizesObservability`. The bridge then consumes the DataSet as a subscriber. Either way, the bridge emits the same OTEL.

### 4.4 Architecture

```mermaid
flowchart TB
  subgraph Server[OPC UA Server]
    SO[Server Object i=2253]
    OB["Observability<br/>(ObservabilityFolderType)"]
    subgraph Inst["Bound instance (IObservableType)"]
      G["ObservabilityBindingGroup<br/>CompanionSpecificationUri<br/>ModelNamespaceUris"]
      M["ObservabilityBinding · Metrics<br/>DataSetClassId, BoundItems"]
      L["ObservabilityBinding · Logs"]
      T["ObservabilityBinding · Traces"]
    end
    PDS["(optional) PublishedDataSet<br/>DataSetWriter"]
  end
  Bridge["Bridge (read-only Client)"]
  Coll[OTEL Collector]
  SO -->|HasComponent| OB
  OB -.->|RealizedBy| G
  G -->|HasComponent| M
  G --> L
  G --> T
  M -.->|ObservabilityRealizedBy opt.| PDS
  Bridge -->|Browse Server/Observability| OB
  Bridge -->|Subscriptions/Reads or DataSetReader| Server
  Bridge -->|OTLP metrics/logs/traces| Coll
```

## 5 Information model

The full node reference — every type, member, DataType and well-known instance — is generated in **[Annex A](#annex-a)**. This clause states the intent and the normative rules. All types are defined in the base namespace; NodeIds are provisional.

The model uses non-hierarchical ReferenceTypes for cross-links that must not affect containment: `BindsToNode` links a bound item to the source Variable, event source or Program it exposes; `ObservabilityRealizedBy`/`RealizesObservability` links a binding to its optional Part 14 PubSub realization; `HasBaseBinding` links a derived or composed binding to a locally present base binding; and `RealizedBy`/`Realizes` links the `Observability` registry to the instance-contained `ObservabilityBindingGroup` Objects.

### 5.1 ObservabilityFolderType

The server-wide `Observability` registry is an [`ObservabilityFolderType`](#type-ObservabilityFolderType) Object exposed as a component of the **Server Object**. It references, through [`RealizedBy`](#type-RealizedBy), every [`ObservabilityBindingGroupType`](#type-ObservabilityBindingGroupType) in the Server. A Client follows those references to the groups and browses each group's `<ObservabilityBinding>` children. No query Method is defined — Browse and Read already provide enumeration and selection, and requiring a Method would burden the classic Servers that are the common case.

#### 5.1.1 ObservabilityBindingGroupType

An [`ObservabilityBindingGroupType`](#type-ObservabilityBindingGroupType) is the per-companion-specification anchor contained by the [`IObservableType`](#type-IObservableType) Object instance it describes. Its `CompanionSpecificationUri` (Mandatory) is a stable **specification-level** identifier, not a namespace URI: a companion specification may define several namespace URIs across modules, versions or profiles, and those URIs are therefore not a unique group key. `ModelNamespaceUris` (Mandatory) lists all namespace URIs the companion specification defines or covers so a Client can match the group to the namespaces it knows. Each group `Realizes` the server-wide `Observability` registry; the registry references the groups through `RealizedBy`.

Because sibling groups are contained by the same instance, an instance **shall not** expose two sibling groups with the same `CompanionSpecificationUri`; and because sibling Objects must also have distinct BrowseNames, each group's BrowseName **shall** be stable and unique among that instance's groups. Bindings are named only within their group, so two companion specifications may use the same binding BrowseName without colliding.

### 5.2 ObservabilityBindingType

An [`ObservabilityBindingType`](#type-ObservabilityBindingType) represents exactly one observability binding — one OTEL signal (a metric set, a log stream, or a trace stream) for one bound target. `SignalKind` (Mandatory, an [`ObservabilitySignalKindEnum`](#type-ObservabilitySignalKindEnum)) selects the signal — `Metrics`, `Logs` or `Traces` (§5.6). `ConfigurationVersion` aligns the binding with the `ConfigurationVersion` of its schema so a consumer can detect change. `DataSetClassId` (Mandatory) is the stable Part 14 class identity for the binding and already encodes the signal kind (§5.7). `DataSetCardinalityPath` (Optional) selects the cardinality level for instances of that class; when omitted, the cardinality level is the bound root.

The bound items are exposed **both** as browsable `<BoundItem>` objects **and** as a compact `BoundItems` array of [`BoundItemDataType`](#type-BoundItemDataType); when both are present they **shall** carry equivalent bound-item information (the same members and values). The bound items are homogeneous per binding: Variables for a metric set, event fields for a log or trace stream.

`DataSetMetaData` (Optional) exposes the Part 14 [`DataSetMetaDataType`](https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.2.4) schema offline (§5.8). For log and trace bindings, `EventSourcePath` (Optional) identifies the event notifier; when omitted, the notifier is the cardinality anchor (the bound root when `DataSetCardinalityPath` is omitted). `Filter` (Optional, a [`ContentFilter`](https://reference.opcfoundation.org/specs/OPC-10000-4/7.4.1)) is the event where-clause. The OTEL mapping members (`Log*`, `Span*`, and the per-item metric members) are described in §5.13. Where PubSub is configured, this binding references the realizing Part 14 node with [`ObservabilityRealizedBy`](#type-ObservabilityRealizedBy).

#### 5.2.1 DataSet cardinality (normative)

`DataSetCardinalityPath` names the cardinality anchor. A Server **shall** produce one DataSet instance for each matched instance of the `DataSetCardinalityPath`. If it is omitted, the cardinality anchor is the bound root and the binding produces one DataSet for that bound root. If the path resolves to multiple nodes, each resolved node is a separate cardinality anchor and therefore produces a separate DataSet.

The binding's `DataSetClassId` is unchanged by cardinality expansion and **shall** be shared by all produced DataSets. In PubSub realizations this means one DataSet class and, typically, one `DataSetWriter` per produced DataSet instance; in classic realizations the bridge creates the equivalent set of Subscriptions/MonitoredItems per cardinality anchor while retaining the same class identity. Because placeholder segments below the anchor expand per instance, the produced DataSets share the `DataSetClassId` but their concrete `DataSetMetaData` (field set and `ConfigurationVersion`) is per instance and may differ in field count (§5.7).

Illustrative cases:

| Binding shape | Result |
|---|---|
| `DataSetCardinalityPath` omitted on a single pump bound root | One metric DataSet for that pump. |
| `DataSetCardinalityPath = /MotionDevices/<MotionDevice>` on a three-robot cell | Three DataSets, one per MotionDevice, all with the same `DataSetClassId`; `<Axis>/ActualPosition` expands to per-axis fields **within** each device DataSet. |
| `DataSetCardinalityPath = /MotionDevices/<MotionDevice>` with a bound item two placeholder levels below the anchor on a robot with 6 power trains × 1 motor | One DataSet per MotionDevice; the two sub-anchor placeholders expand to 6 `MotorTemperature` fields per device, all sharing the one `DataSetClassId`. Placeholder levels compose multiplicatively. |

BrowsePaths at or above the cardinality anchor select which content instances are produced. Placeholders strictly below the cardinality anchor do **not** create additional DataSets; they expand to disambiguated fields within that DataSet according to the BrowsePath resolution rules (§5.10).

The **shape** of a produced DataSet is the resolved field set for one cardinality anchor. For the metric binding of a `MotionDevice` `Robot_1` (6 axes, 6 motors), the bridge produces one DataSet of this shape (see the Robotics addendum for the full worked resolution):

```text
DataSet "Robot_1 · Metrics"   (one DataSetClassId, shared by every MotionDevice DataSet)
  AxisActualPosition_Axis_1 … AxisActualPosition_Axis_6            Gauge · deg
  MotorTemperature_PowerTrain_1_Motor_1 … _PowerTrain_6_Motor_1    Gauge · Cel
  SpeedOverride                                                    Gauge · %
```

A different topology (for example a 4-axis SCARA) yields the same `DataSetClassId` but a DataSet with fewer fields; a subscriber recognizes the class regardless of the per-instance field count.

### 5.3 BoundItemType and its subtypes

A [`BoundItemType`](#type-BoundItemType) describes one metric, dimension, or event field. It **shall** carry a `FieldName` and a `Kind` (a [`BoundItemKindEnum`](#type-BoundItemKindEnum)). It locates its source in one of two ways (§5.10) and carries the semantic cross-reference (§5.4). [`BoundVariableType`](#type-BoundVariableType) binds a Variable exposed as a metric field and adds the OTEL metric members (`MetricInstrumentType`, `Unit`, `ExplicitBucketBoundaries`, `MetricTemporality`, `Monotonic`); a bound item may instead be a metric dimension (`Kind = Dimension`, optionally with a `DimensionConstantValue`). [`BoundEventFieldType`](#type-BoundEventFieldType) binds an event field of a log or trace stream, selected by a [`SimpleAttributeOperand`](https://reference.opcfoundation.org/specs/OPC-10000-4/7.4.4); its `BrowsePath` is relative to the event `SourceTypeDefinition`, not to the AddressSpace instance.

```mermaid
classDiagram
  direction LR
  class BoundItemType {
    +FieldName
    +Kind
    +BrowsePath
    +DimensionConstantValue
    +SourceTypeDefinition
    +SourceBrowseName
    +ModelNamespaceUri
    +SemanticReferenceUri
  }
  class BoundVariableType {
    +MetricInstrumentType
    +Unit
    +ExplicitBucketBoundaries
    +MetricTemporality
    +Monotonic
  }
  class BoundEventFieldType {
    +EventFieldOperand
  }
  class BoundItemKindEnum {
    <<enumeration>>
    Telemetry = 0
    Status = 1
    Metric = 2
    Counter = 3
    Event = 4
    Dimension = 5
    Identification = 6
    Other = 7
  }
  BoundVariableType --|> BoundItemType
  BoundEventFieldType --|> BoundItemType
  BoundItemType --> BoundItemKindEnum : Kind
```

### 5.4 Semantic cross-reference (normative)

Each bound item **shall** retain enough information to identify the model node it exposes independently of the live AddressSpace — as applicable to its NodeClass:

- `SourceTypeDefinition` — the TypeDefinition NodeId of the source node, or for [`BoundEventFieldType`](#type-BoundEventFieldType), the event TypeDefinition against which the field operand is evaluated;
- `SourceBrowseName` — its namespace-qualified BrowseName;
- `ModelNamespaceUri` — the namespace URI of the model that defines it;
- optionally, `SemanticReferenceUri` — a portable external semantic identifier for the item (an IRDI/CDD, e.g. the identifier of a [OPC 10000-19](https://reference.opcfoundation.org/specs/OPC-10000-19/) dictionary entry). A Server that models the dictionary linkage natively **may** additionally place a `HasDictionaryEntry` reference on the browsable `BoundItem`; `SemanticReferenceUri` is the carrier used in the compact form and for propagation, so the linkage survives export.

These values are **derivable from the AddressSpace** and a generating tool **should** populate them mechanically to avoid drift.

The semantic Properties carry the **Optional** ModellingRule on [`BoundItemType`](#type-BoundItemType) at the type definition so one base type can serve bound Variables and bound event fields even though different subsets apply to different NodeClasses. This does not make the applicable values optional for a conforming instance: the *Semantic Cross-Reference* conformance unit (§7) requires a Server that exposes a binding to populate the applicable subset per NodeClass — `SourceTypeDefinition`, `SourceBrowseName` and `ModelNamespaceUri` for a bound **Variable**; and `SourceTypeDefinition` (the event type), `SourceBrowseName` and `ModelNamespaceUri` for a bound **event field**.

#### 5.4.1 Propagation to Part 14 FieldMetaData (Part 14 realization)

When a binding is realized as a Part 14 `PublishedDataSet`, for every bound item the Server **shall**:

1. set the corresponding `FieldMetaData.dataSetFieldId` to the item's `DataSetFieldId`;
2. add to `FieldMetaData.properties` the KeyValuePairs `ModelNamespaceUri`, `SourceBrowseName`, `SourceTypeDefinition`, `BrowsePath` and, where present, `SemanticReferenceUri`, `SourceBindingClassId` (so a disconnected subscriber can recognize fields inherited from a base facet class) and `EventFieldOperand`; and
3. ensure the `DataSetMetaData` namespace and DataType tables describe any non-standard DataTypes used.

The property keys **shall** match the corresponding [`BoundItemType`](#type-BoundItemType) or [`BoundItemDataType`](#type-BoundItemDataType) member names above, so a consumer can map each `FieldMetaData` property back to the binding model without a separate lookup. As a result the PubSub stream is **self-describing**. This requirement is a Conformance Unit (§7).

### 5.5 Propagation to Part 14 configuration (normative)

Where PubSub is configured, the Server **shall** propagate the binding into Part 14 configuration as follows:

1. create or identify one `PublishedDataSet` for each DataSet instance produced by `DataSetCardinalityPath`;
2. set each `DataSetMetaData.dataSetClassId` and `PublishedDataSet.DataSetClassId` to the binding's shared `DataSetClassId`;
3. for any exposed `DataSetMetaData`, set `ConfigurationVersion` to the binding's `ConfigurationVersion`;
4. for any exposed `DataSetMetaData`, populate `FieldMetaData` from the `BoundItems` as specified in §5.4;
5. for `SignalKind = Metrics`, realize the DataSet as [`PublishedDataItemsType`](https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.4) and map each [`BoundVariableType`](#type-BoundVariableType) or data [`BoundItemDataType`](#type-BoundItemDataType) entry to a published data Variable;
6. for `SignalKind = Logs` or `Traces`, realize the DataSet as [`PublishedEventsType`](https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.5), map [`BoundEventFieldType`](#type-BoundEventFieldType) / `EventFieldOperand` entries to `SelectedFields`, map `EventSourcePath` to the `EventNotifier` (default: the cardinality anchor), and map `Filter` to the PublishedEvents `Filter`.

Applicable only where the Server implements PubSub.

### 5.6 Signal kind and granularity (normative)

An [`ObservabilityBindingType`](#type-ObservabilityBindingType) **shall** expose exactly one `SignalKind`. The `BoundItems` of the binding **shall** be homogeneous for that signal; a single binding **shall not** mix metric Variables and event fields as peer content. An [`ObservabilityBindingGroupType`](#type-ObservabilityBindingGroupType) may contain multiple bindings when an instance exports several signals (e.g. a Metrics binding **and** a Logs binding). This class is the granularity at which class identity, configuration versioning and subscriber recognition are defined: per signal kind, per bound ObjectType, per major version.

For `SignalKind = Metrics`, the DataSet is a data DataSet: grouped Variable values modeled by Part 14 [`PublishedDataItemsType`](https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.4). The fields are [`BoundVariableType`](#type-BoundVariableType) objects, or [`BoundItemDataType`](#type-BoundItemDataType) entries whose source locators identify Variables.

For `SignalKind = Logs` or `Traces`, the DataSet is an event DataSet modeled by Part 14 [`PublishedEventsType`](https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.5). `EventSourcePath` names the event notifier to subscribe to; if absent, the notifier is the cardinality anchor. The fields are [`BoundEventFieldType`](#type-BoundEventFieldType) objects, or [`BoundItemDataType`](#type-BoundItemDataType) entries with `EventFieldOperand`, and they map to PublishedEvents `SelectedFields`. `Filter` carries the optional Part 14 event where-clause. Logs and Traces differ only in the OTEL mapping applied by the bridge (§5.13.2, §5.13.3).

### 5.7 DataSetClassId (normative)

`DataSetClassId` **shall** be a Version-5 UUID as defined by RFC 4122, computed over the canonical UTF-8 string:

```text
ObservabilityExport|<AppliesToType>|<SignalKind>|<MajorVersion>
```

The namespace UUID **shall** be the fixed UUID `8d3280be-2bf7-5ab1-9898-15a237192577`, defined by this specification as `uuid5(URL, "http://opcfoundation.org/UA/ObservabilityExport/DataSetClass")`.

`AppliesToType` is the namespace-qualified BrowseName of the concrete [binding target](#term-binding-target) (a TypeDefinitionNode) encoded as `<namespaceUri>;<Name>`. `SignalKind` is the binding's signal kind expressed as the exact [`ObservabilitySignalKindEnum`](#type-ObservabilitySignalKindEnum) name — `Metrics`, `Logs` or `Traces` (§5.6). `MajorVersion` is the binding's `ConfigurationVersion.MajorVersion` expressed as a base-10 integer without leading zeroes. If the binding does not expose `ConfigurationVersion`, `MajorVersion` **shall** be taken as `1` (equivalently, an absent `ConfigurationVersion` is treated as `{MajorVersion = 1, MinorVersion = 0}`). Because a browsing subscriber recomputes `DataSetClassId` from the binding's exposed attributes, a binding whose `MajorVersion` is **not** `1` **shall** expose `ConfigurationVersion`.

Because the calculation is deterministic, every Server publishing the same signal kind, binding target and major version **shall** compute the same `DataSetClassId`. A semantics-agnostic subscriber can therefore recognize the *class* from `DataSetClassId` alone, without browsing the Server. The identity grain is per `(AppliesToType × SignalKind × MajorVersion)`: because `SignalKind` is part of the identity, a metric set, a log stream and a trace stream for the same bound target and major version are **distinct** classes with distinct `DataSetClassId`s.

`DataSetClassId` identifies the *semantic* class — the signal kind applied to a binding target at a major version — and is a routing and recognition key, **not** a guarantee of a fixed field layout. When `DataSetCardinalityPath` leaves placeholder segments below the cardinality anchor (§5.2.1), the concrete `DataSetMetaData` may differ in field count between instances of the same class. A consumer that requires the exact field layout **shall** read each DataSet's `DataSetMetaData` (§5.8) rather than infer it from `DataSetClassId`.

A derived or composed binding keeps its own deterministic `DataSetClassId` and additionally advertises the base classes it extends or composes with `BaseDataSetClassIds` (§5.12).

### 5.8 DataSetMetaData exposure

A binding **may** expose `DataSetMetaData` carrying the DataSet fields plus `dataSetClassId` and `configurationVersion`. When present, it **shall** be consistent with the binding's `BoundItems`, `DataSetClassId`, `SignalKind` and `ConfigurationVersion`. This lets a subscriber or offline tool obtain the class schema without browsing the bound model or reading the runtime PubSub configuration.

### 5.9 IObservableType

An Interface a model may apply (via `HasInterface`) to advertise that it exports observability data. It contains the Object's per-`CompanionSpecificationUri` [`ObservabilityBindingGroupType`](#type-ObservabilityBindingGroupType) components directly — typically one for a single-specification instance — rather than a separate container; sibling group BrowseNames are unique (§5.1.1). Each contained group `Realizes` the server-wide `Observability` registry. Applying the Interface at the **type** level, with type-level BrowsePath bindings, is the recommended way for a companion specification to adopt this specification without changing its own types' semantics.

### 5.10 Locating bound items — BrowsePath resolution (normative)

A bound item locates its source node in one of two ways:

- **BrowsePath (recommended).** `BrowsePath` is a [`RelativePath`](https://reference.opcfoundation.org/specs/OPC-10000-4/7.30) resolved from `StartingNode` (default: the [bound root](#term-bound-root)). Because it is relative, a single binding authored on a **type** applies to **every instance**: the Server resolves it per instance with [TranslateBrowsePathsToNodeIds](https://reference.opcfoundation.org/specs/OPC-10000-4/). This is the recommended mechanism and the form emitted by the authoring tool. For [`BoundEventFieldType`](#type-BoundEventFieldType), the `BrowsePath` segments select an event field relative to `SourceTypeDefinition`, the event TypeDefinition, and may be represented directly as `EventFieldOperand`.
- **Absolute NodeId.** `SourceNodeId` (and the `BindsToNode` reference on the browsable form) identifies the node directly, for server-specific or instance-specific bindings. It is not used to select event fields inside a PublishedEvents DataSet.

[Binding targets](#term-binding-target) are TypeDefinitionNodes — ObjectTypes, Interface facets, or AddInTypes; because `HasInterface` is applied to the instance and `HasAddIn` is hierarchical (a subtype of `HasComponent`), type-level BrowsePaths still resolve against the instance using the same `HierarchicalReferences` (`i=33`) traversal.

Resolution rules a Server **shall** apply:

1. If a BrowsePath does not resolve on a given instance (an absent Optional component), the item is **omitted** for that instance; this is **not** an error.
2. `DataSetCardinalityPath` is resolved first from the bound root (or defaults to the bound root). If it matches multiple nodes, each matched node is a separate cardinality anchor and produces a separate DataSet instance.
3. A bound-item BrowsePath that matches multiple nodes at or above the cardinality anchor participates in selecting the produced content instances; it shall not be collapsed into multiple fields of one DataSet.
4. A bound-item BrowsePath that matches multiple nodes strictly below a cardinality anchor (a placeholder such as `<Rating>`, or an array of components) expands to one bound field per match within that DataSet; `FieldName` is made unique by appending the matched BrowseName or another deterministic path-derived suffix.
5. For an event field, the path targets a field of the event TypeDefinition; the notifier is identified by `EventSourcePath`, not by the field `BrowsePath`.
6. Type-level BrowsePaths and `DataSetCardinalityPath` resolve against the **live** AddressSpace. When the instance structure changes — a cardinality anchor or a placeholder instance is added or removed — the Server/bridge **shall** re-resolve the affected paths and add or remove the corresponding DataSets and fields. A bridge **should** drive this re-evaluation from the Server's **model-change signalling** — subscribing to `GeneralModelChangeEventType` notifications (or observing a changed node version or a bumped DataSet `ConfigurationVersion`) — rather than polling.

### 5.11 Registry and adoption

The `Observability` registry is an [`ObservabilityFolderType`](#type-ObservabilityFolderType) Object under the Server Object and is the discovery entry point. A companion specification adopts this specification by applying [`IObservableType`](#type-IObservableType) to a type (or instance) and authoring type-level bindings; the Server then contains one `ObservabilityBindingGroup` per (companion specification × observable instance), each `Realizes`-linked to the registry. A Client that supports observability export does not need to know which specification contributed a binding: it browses the registry, follows `RealizedBy` to the serving groups distinguished by `CompanionSpecificationUri`, browses each group's [`ObservabilityBindingType`](#type-ObservabilityBindingType) children, then resolves each binding through the classic baseline or optional PubSub realization.

### 5.12 Binding inheritance and facet composition (normative)

A binding may be declared on a [binding target](#term-binding-target) — a **TypeDefinitionNode**; in practice an ObjectType, an Interface (facet) or an AddInType. The target's type-level BrowsePaths resolve against any instance that is-a that type, implements that Interface using `HasInterface`, or composes that AddInType using `HasAddIn`. `HasAddIn` is the core OPC UA ReferenceType `i=17604`, a subtype of `HasComponent`, so AddIn children are reachable by the §5.10 BrowsePath resolution over `HierarchicalReferences` (`i=33`).

Inheritance is uniform across the three OPC UA composition axes: a subtype inherits the bindings of its supertype, a type (or one of its component objects) implementing a facet Interface inherits the facet's bindings, and a host composing an AddIn inherits the AddIn's bindings. A facet implemented by a component object is composed at that component's path.

A derived binding **shall** list only its additional delta fields and **shall** reference the base class lineage with `BaseDataSetClassIds`; it **may** additionally use `HasBaseBinding` when the base binding node is present locally. A derived field with the same `FieldName` as an inherited field **shall** override the inherited field. A binding **shall not** remove an inherited field; every derived binding is a superset of each base binding it extends, which makes base-class field-subset recognition safe.

For a given instance and signal kind, a Server or bridge **shall** compose the effective binding as follows:

1. Collect candidate bindings of the same `SignalKind` from the instance's TypeDefinition and its supertype chain, from each `HasInterface` target type, from each `HasAddIn` child's type, and from each hierarchical **child object** whose TypeDefinition — or an Interface that child implements — declares a binding for that signal kind (this is how a facet implemented by a sub-object, such as a DI `IVendorNameplateType` nameplate on a Machinery `Identification` component, is reached).
2. Each collected binding has a **mount path** — the RelativePath from the composing instance's root to the node that **carries the facet**. For a binding on the bound type itself (**subtype**) or on an **Interface the bound type implements directly** (`HasInterface`), the mount path is **empty**. For a binding carried by a **hierarchical child** — an **AddIn** child (`HasAddIn`) or a **component/child object** whose type or implemented Interface declares it — the mount path is that **child's BrowsePath**. Before unioning, the Server/bridge **shall** re-anchor every path of a collected binding by prefixing the mount path: each bound item's `BrowsePath` (and `StartingNode`), the binding's `DataSetCardinalityPath`, and its `EventSourcePath` are resolved relative to `mountPath + path`.
3. Union the candidates' re-anchored `BoundItems`, applying override-by-`FieldName` so the most-derived contribution wins.
4. Set `SourceBindingClassId` on each composed field **only** for fields inherited from — or overriding a field of — a base facet binding; its value is the **base facet binding's `DataSetClassId`**. Fields the composing binding **defines itself** **omit** `SourceBindingClassId`.
5. Set the composed binding's `BaseDataSetClassIds` to the set of contributing base `DataSetClassId` values.
6. Compute the composed binding's own `DataSetClassId` per §5.7 for the concrete `AppliesToType`.

A base facet binding **may** merge into the composing binding only when its (re-anchored) `DataSetCardinalityPath` resolves to the **same cardinality anchor** as the composing binding. A base binding whose `DataSetCardinalityPath` resolves to a **different or multi-valued** cardinality anchor **shall not** be merged; instead the Server/bridge **shall** expose it as its own DataSet(s) per §5.2.1, still recognizable through the composing binding's `BaseDataSetClassIds`.

A subscriber that understands a base facet selects exactly the composed fields whose `SourceBindingClassId` equals that facet's `DataSetClassId`; a subscriber that understands the full composed class consumes every field.

Guidance: use a subtype binding for is-a refinement, use an Interface facet binding for a contract capability implemented by many types, and use an AddIn binding for a reusable structural block that brings its own sub-objects.

### 5.13 OTEL mapping (normative)

This clause defines how a bridge maps an [`ObservabilityBindingType`](#type-ObservabilityBindingType) to OpenTelemetry signals. The mapping is expressed in OTEL terms; §8 notes how the same metadata drives other backends.

#### 5.13.1 Metrics

For `SignalKind = Metrics`, a bound Variable maps to exactly one OTEL metric instrument. If `MetricInstrumentType` is present it selects the instrument directly and overrides the default; if it is absent, the bridge derives the instrument from the item's `Kind`:

| Bound item `Kind` | Default OTEL metric instrument |
|---|---|
| `Telemetry` | Gauge |
| `Metric` | Gauge |
| `Counter` | Counter (monotonic) |
| `Status` | Gauge (numeric state) — informative |
| other kinds | Not a metric; a bridge may skip the item or treat it as a Gauge. |

`Monotonic` is implied by the selected instrument unless set explicitly: Counter and ObservableCounter instruments are monotonic, while UpDownCounter and Gauge instruments are not. An explicit `Monotonic` **shall not** contradict the selected instrument.

**Metric unit.** The metric unit is `Unit` (a UCUM annotation) when present; otherwise a bridge SHOULD derive it from the source Variable's `EngineeringUnits` (`EUInformation`) where present; otherwise the metric is unitless. `Unit` is also the carrier that survives export to a disconnected consumer.

**Histogram buckets and temporality.** For a Histogram, `ExplicitBucketBoundaries` (Double[]) gives the bucket boundaries. `MetricTemporality` (`Cumulative` or `Delta`) is the aggregation temporality a bridge uses when exporting a Sum (Counter/UpDownCounter) or Histogram data stream. For Gauge instruments temporality does not apply. When `MetricTemporality` is absent, `Cumulative` is assumed for Sum/Histogram instruments, and Gauges report last-value.

#### 5.13.2 Logs

For `SignalKind = Logs`, the bound event fields are the structured attributes of an OTEL LogRecord. `LogTemplate` is a message template whose `{FieldName}` placeholders reference bound event `FieldName`s; a bridge renders it to the LogRecord Body while still carrying the fields as attributes. Alternatively, `LogBodyFieldName` names a field already carrying the rendered body. A Server should set only one; if both are present, `LogTemplate` takes precedence for the Body and `LogBodyFieldName` is then an ordinary attribute. `LogSeverityFieldName` names the field mapped to the LogRecord SeverityNumber/SeverityText, and `LogTimestampFieldName` names the field mapped to the LogRecord Timestamp. The binding's `Kind = Dimension` items also apply to each log record as attributes.

When the bound severity field already carries an OTEL SeverityNumber (1..24), a bridge uses it directly; otherwise it applies the following recommended mapping from the OPC UA `Severity` UInt16 value:

| OPC UA `Severity` | OTEL SeverityNumber (SeverityText) |
|---|---|
| 1–199 | 5 (DEBUG) |
| 200–399 | 9 (INFO) |
| 400–599 | 13 (WARN) |
| 600–799 | 17 (ERROR) |
| 800–1000 | 21 (FATAL) |

#### 5.13.3 Traces

For `SignalKind = Traces`, the bound event fields map to an OTEL Span. A trace binding is event-sourced like a log binding — it selects fields from a notifier (`EventSourcePath`, `Filter`) — but a bridge produces a Span rather than a LogRecord. Trace sources are, typically, a [`ProgramStateMachineType`](https://reference.opcfoundation.org/specs/OPC-10000-10/) execution (a Program run is a span), an `AuditEventType` (a request/response is a span), or a pair of correlated events.

A bridge builds each Span from the binding's members:

- **Name** — `SpanNameFieldName` (a bound field) or `SpanNameTemplate` (a `{FieldName}` template). If neither is set, the bridge uses the event type BrowseName.
- **Identity** — `TraceIdFieldName`, `SpanIdFieldName`, `ParentSpanIdFieldName` name the fields carrying the trace/span/parent ids. When a trace or span id field is absent, the bridge generates one; `ParentSpanIdFieldName` lets a span nest under its caller.
- **Timing** — `SpanStartTimeFieldName` (default: the event Time/SourceTimestamp) and `SpanEndTimeFieldName`. When no end time and no correlation is configured, the event is a **zero-duration** span (a point-in-time span).
- **Correlation** — `SpanCorrelationFieldName` names the field whose value pairs a **start** event with its matching **end** event into one span (for example a Program run id or an audit correlation id). When absent, each event is an independent span.
- **Status** — `SpanStatusFieldName` maps to the Span Status (`Ok`/`Error`/`Unset`); when absent, a bridge derives it from the event `Severity`/`Quality` (e.g. bad quality or Severity ≥ 600 → `Error`).
- **Kind** — `SpanKind` is a constant per binding (`Internal`, `Server`, `Client`, `Producer`, `Consumer`; default `Internal`).

The binding's `Kind = Dimension` items apply to each Span as attributes. Cross-system trace-context propagation (W3C traceparent) between the OPC UA Server and other systems is **out of scope**; the mapping covers producing spans from OPC UA Program/audit/correlated events.

#### 5.13.4 Resource and attributes (dimensions)

Within a binding, every bound item with `Kind = Dimension` is an OTEL **attribute** applied to every metric data point, log record and span the binding produces; dimensions are binding-level in this revision. A dimension's attribute key is its `FieldName`; its value is read from the dimension item's source node through its `BrowsePath` unless `DimensionConstantValue` is set, in which case the dimension is a constant attribute — for example `service.name`. A dimension whose `Kind` is `Identification` (or whose key is a well-known OTEL Resource attribute such as `service.name`, `service.namespace`, `host.name`) **should** be emitted as an OTEL **Resource** attribute rather than a per-data-point attribute; all other dimensions are per-data-point attributes. Non-dimension items are the measured values / event fields.

These OTEL members are Optional and are ignored by signal kinds to which they do not apply; they do not change the `DataSetClassId` derivation.

## 6 Using the model (informative)

This clause shows how a **bridge** consumes the model. It is informative; conformance is defined in §7.

### 6.1 Walkthrough

1. **Discover.** Browse `Server/Observability`, follow its `RealizedBy` references to the instance-contained `ObservabilityBindingGroup` Objects, then browse each group's `ObservabilityBinding` children. If starting from an `IObservableType` instance, browse its per-spec groups directly.
2. **Recognize.** If the bridge has prior knowledge of a class, it can recognize an incoming PubSub DataSet realization by `DataSetClassId` alone (signal kind is part of the identity); no browse of the publishing Server is required. If it is browsing, read `DataSetClassId`, `SignalKind`, `DataSetCardinalityPath` and optionally `DataSetMetaData` to learn the schema.
3. **Compose.** Before resolving items, compose the effective class by the §5.12 union algorithm: gather bindings inherited via subtype, `HasInterface` facets and `HasAddIn` children of the same `SignalKind`, then apply override-by-`FieldName` and field provenance tagging.
4. **Realize — classic path (the default).** Resolve `DataSetCardinalityPath` (default: the bound root) to the set of DataSet instances to create. For `SignalKind = Metrics`, resolve each bound Variable `BrowsePath` (or read `SourceNodeId`) with `TranslateBrowsePathsToNodeIds`, then create a Subscription with a MonitoredItem on that node and `AttributeId`, honouring `SamplingIntervalHint`; a bridge may also Read the values directly. For `SignalKind = Logs` or `Traces`, resolve `EventSourcePath` to the notifier (default: the cardinality anchor), subscribe to Events, use the `BoundEventFieldType` / `EventFieldOperand` entries as selected fields, and apply `Filter` where supported. This path needs no PubSub configuration and works on any Server.
5. **Realize — PubSub path (only where PubSub is configured).** If the binding is [`ObservabilityRealizedBy`](#type-ObservabilityRealizedBy) a Part 14 node, read the `DataSetMetaData` and the transport from the owning `WriterGroup`/`PubSubConnection`, then create a `DataSetReader`/subscriber.
6. **Emit OTEL.** For each field, emit the OTEL signal per §5.13 (metric instrument, LogRecord, or Span), attach the binding's dimensions as attributes/Resource, and carry the semantic cross-reference so the downstream consumer can interpret it. **No domain knowledge is required.**

### 6.2 Sequence — classic server (the default)

```mermaid
sequenceDiagram
  participant S as Server (no PubSub surface)
  participant B as Bridge (Client)
  participant C as OTEL Collector
  B->>S: Browse Server/Observability
  S-->>B: ObservabilityBindingGroup { CompanionSpecificationUri, ModelNamespaceUris }
  B->>S: Browse selected group children
  S-->>B: ObservabilityBinding { SignalKind, DataSetClassId, DataSetCardinalityPath, BoundItems... }
  B->>B: Compose effective class via §5.12 union
  B->>S: Resolve DataSetCardinalityPath (default bound root)
  alt Metrics
    loop per BoundVariable
      B->>S: TranslateBrowsePathsToNodeIds (BrowsePath)
      B->>S: CreateSubscription + CreateMonitoredItems (AttributeId, SamplingIntervalHint)
    end
  else Logs or Traces
    B->>S: Resolve EventSourcePath (default: cardinality anchor)
    B->>S: Subscribe to Events (SelectedFields + Filter)
  end
  loop runtime
    S-->>B: DataChange or Event notification
    B->>C: OTLP metric / LogRecord / Span (+ dimensions + semantic cross-ref)
  end
```

### 6.3 Sequence — PubSub-capable server (less common)

```mermaid
sequenceDiagram
  participant S as Server (PubSub configured)
  participant B as Bridge (Client)
  participant C as OTEL Collector
  B->>S: Browse Server/Observability
  S-->>B: ObservabilityBindingGroup { CompanionSpecificationUri, ModelNamespaceUris }
  B->>S: Browse selected group children
  S-->>B: ObservabilityBinding + realization (PublishedDataSet RealizesObservability binding)
  B->>S: Read DataSetMetaData + WriterGroup/PubSubConnection
  B->>B: Match or cache DataSetClassId
  B->>B: Create DataSetReader (subscriber)
  loop runtime
    S-->>B: PubSub DataSetMessage
    B->>C: OTLP metric / LogRecord / Span (+ dimensions + semantic cross-ref)
  end
```

## 7 Profiles and Conformance Units

The following Conformance Units (CUs) are defined; Facets group them for Servers and Clients.

| Conformance Unit | Requirement |
|---|---|
| Observability Discovery | Expose a server-wide `Observability` registry of type [`ObservabilityFolderType`](#type-ObservabilityFolderType) as a component of the Server Object, referencing every `ObservabilityBindingGroup` through `RealizedBy`. |
| Binding Grouping | On each `IObservableType` instance, group bindings under one `ObservabilityBindingGroup` per `CompanionSpecificationUri`; make sibling groups unique by that identifier and BrowseName, have each group `Realizes` the registry, and expose `ModelNamespaceUris`. |
| BrowsePath Resolution | Author bound items as type-level BrowsePaths and resolve them per instance under the rules of §5.10. |
| DataSet Cardinality | Resolve `DataSetCardinalityPath` and create one DataSet instance per matched cardinality anchor while sharing the binding's `DataSetClassId`. |
| DataSet Class Identity | Compute the deterministic `DataSetClassId` per §5.7 and propagate it to `DataSetMetaData.dataSetClassId` and `PublishedDataSet.DataSetClassId` wherever PubSub realization is configured. |
| Binding Inheritance & Facet Composition | Compose the effective class by unioning bindings inherited via subtype, `HasInterface` and `HasAddIn` (override by `FieldName`), advertise base classes via `BaseDataSetClassIds`, and tag field provenance with `SourceBindingClassId` (§5.12). |
| Metrics OTEL Mapping | For a Metrics binding, map bound Variables to OTEL metric instruments per `MetricInstrumentType` (or the Kind default), unit and temporality, and attach `Kind = Dimension` items as attributes/Resource (§5.13.1, §5.13.4). |
| Logs OTEL Mapping | For a Logs binding, render event bindings to OTEL LogRecords via `LogTemplate`/`LogSeverityFieldName`/`LogBodyFieldName`/`LogTimestampFieldName`, carrying dimensions as attributes (§5.13.2). |
| Traces OTEL Mapping | For a Traces binding, produce OTEL Spans from Program/audit/correlated events via the `Span*` members (name, identity, timing, correlation, status, kind), carrying dimensions as attributes (§5.13.3). |
| Metric Realization *(optional)* | Realize a Metrics binding as one Part 14 `PublishedDataSet`/`DataSetWriter` per DataSet instance, with `PublishedDataItemsType`. Applicable only where the Server implements PubSub. |
| Event DataSet Binding *(optional)* | Realize a Logs or Traces binding as one Part 14 `PublishedDataSet`/`DataSetWriter` per DataSet instance, with `PublishedEventsType`, mapping `BoundEventFieldType`/`EventFieldOperand` to `SelectedFields`, `EventSourcePath` to the notifier and `Filter` to the event filter. Applicable only where the Server implements PubSub. |
| Semantic Cross-Reference | Populate the semantic fields on every exposed bound item (`SourceTypeDefinition`/`SourceBrowseName`/`ModelNamespaceUri`, per §5.4). Independent of PubSub. |
| PubSub MetaData Propagation *(optional)* | Where a binding is realized over PubSub, propagate the semantic fields into `DataSetMetaData.FieldMetaData` per §5.4.1 and the DataSet-level fields per §5.5. |

**Facets (informative grouping):**

- **Server Observability Facet** — Observability Discovery + Binding Grouping + BrowsePath Resolution + DataSet Cardinality + Semantic Cross-Reference + DataSet Class Identity + Binding Inheritance & Facet Composition (mandatory); Metric Realization + Event DataSet Binding + PubSub MetaData Propagation (as offered, only where PubSub is implemented).
- **Publisher Facet** — Metric Realization and/or Event DataSet Binding, plus PubSub MetaData Propagation where DataSet metadata is exposed.
- **Bridge (Client) Facet** — browse the `Observability` registry, follow `RealizedBy` to groups and bindings, recognize by `DataSetClassId`, compose the effective class by the §5.12 union algorithm, resolve `DataSetCardinalityPath`, realize via the classic path (default) or PubSub where configured, and emit OTEL per the Metrics/Logs/Traces mapping CUs.

## 8 Other observability backends (informative)

OTEL is the normative mapping target, but the binding metadata is deliberately backend-agnostic — it describes *what the value is* (instrument, unit, temporality, dimension) and *what it means* (semantic cross-reference), not an OTEL-specific wire format. A bridge therefore drives other observability stacks with a thin adapter that consumes the same bindings:

- **Prometheus / Grafana.** Map the metric instrument and unit to a Prometheus metric type; emit `Kind = Dimension` items as labels; a Counter with `Cumulative` temporality maps directly to a Prometheus counter, a Gauge to a gauge, a Histogram to a Prometheus histogram using `ExplicitBucketBoundaries`.
- **Splunk / Elastic (logs).** Emit each Logs LogRecord as an event/document; the rendered `LogTemplate` body, severity and timestamp map to the platform's message/severity/time fields, and every bound field and dimension becomes an indexed field.
- **Jaeger / Tempo / Zipkin (traces).** The §5.13.3 span model maps directly to these tracing backends' span schema (trace/span id, parent, name, timing, status, kind, attributes).
- **Microsoft Fabric Real-Time Intelligence / eventstream.** Stream each DataSet as a self-describing record whose columns are the bound `FieldName`s carrying the semantic cross-reference, so a KQL/eventhouse schema is populated without hand-mapping.
- **Apache Arrow lakehouse.** Shape a metric or event DataSet into a columnar Arrow RecordBatch (one column per bound field, engineering units and semantic references carried as field metadata) for a data lake.

Because the semantic cross-reference travels with every field, any of these destinations recovers the companion-model meaning of each value without connecting to the Server.

## 9 Deliverables and reproducibility

This specification is delivered with:

- `Opc.Ua.ObservabilityExport.NodeSet2.xml` — the information model (base namespace, provisional NodeIds);
- `Opc.Ua.ObservabilityExport.NodeIds.csv` — the NodeId assignments;
- **[Annex A](#annex-a)** — the generated node reference (always matches the NodeSet);
- per-companion-specification **addenda** (`pumps/`, `robotics/`, `facets/`, `di/`) that apply the bindings to concrete models, each with an instance-overlay NodeSet;
- machine-readable example binding descriptors and generator tooling under `core-specs/extras/observability-export/`.

The NodeSet, CSV and Annex A are generated from a single source of truth (`core-specs/extras/observability-export/tools/build_model.py`); the example overlays and descriptors are generated by `core-specs/extras/observability-export/examples/tools/build_bindings.py`. Regeneration is byte-deterministic.

<a id="annex-a"></a>
## Annex A — Information model

This annex is the normative node reference. It is generated from [`core-specs/extras/observability-export/tools/build_model.py`](../extras/observability-export/tools/build_model.py) and always matches `Opc.Ua.ObservabilityExport.NodeSet2.xml`. All nodes are proposed additions to the base OPC UA namespace `http://opcfoundation.org/UA/`; the NodeIds shown are **provisional** (final IDs are assigned by the OPC Foundation). The **Declared in** column marks members inherited from a supertype.

### Type overview

| NodeId | BrowseName | NodeClass | Subtype of |
|---|---|---|---|
| i=60001 | [BindsToNode](#type-BindsToNode) | ReferenceType | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) |
| i=60002 | [ObservabilityRealizedBy](#type-ObservabilityRealizedBy) | ReferenceType | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) |
| i=60003 | [HasBaseBinding](#type-HasBaseBinding) | ReferenceType | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) |
| i=60004 | [RealizedBy](#type-RealizedBy) | ReferenceType | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) |
| i=60012 | [BoundItemType](#type-BoundItemType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| i=60013 | [BoundVariableType](#type-BoundVariableType) | ObjectType | [BoundItemType](#type-BoundItemType) |
| i=60017 | [BoundEventFieldType](#type-BoundEventFieldType) | ObjectType | [BoundItemType](#type-BoundItemType) |
| i=60011 | [ObservabilityBindingType](#type-ObservabilityBindingType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| i=60018 | [ObservabilityBindingGroupType](#type-ObservabilityBindingGroupType) | ObjectType | [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6) |
| i=60010 | [ObservabilityFolderType](#type-ObservabilityFolderType) | ObjectType | [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6) |
| i=60016 | [IObservableType](#type-IObservableType) | ObjectType | [BaseInterfaceType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.9) |
| i=60051 | [BoundItemKindEnum](#type-BoundItemKindEnum) | DataType | Enumeration |
| i=60053 | [MetricInstrumentTypeEnum](#type-MetricInstrumentTypeEnum) | DataType | Enumeration |
| i=60054 | [MetricTemporalityEnum](#type-MetricTemporalityEnum) | DataType | Enumeration |
| i=60052 | [ObservabilitySignalKindEnum](#type-ObservabilitySignalKindEnum) | DataType | Enumeration |
| i=60060 | [BoundItemDataType](#type-BoundItemDataType) | DataType | Structure |

### Reference types

<a id="type-BindsToNode"></a>
#### BindsToNode  (i=60001)

*Subtype of:* [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) · *InverseName:* `IsBoundBy`

Links a BoundItem to the companion-specification Variable, event source or Program in the AddressSpace that it exposes for observability export. The target is the authoritative semantic node; the BoundItem does not copy its meaning.

<a id="type-ObservabilityRealizedBy"></a>
#### ObservabilityRealizedBy  (i=60002)

*Subtype of:* [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) · *InverseName:* `RealizesObservability`

Links an ObservabilityBinding to the optional OPC UA Part 14 PubSub node(s) that realize it (a PublishedDataSet, DataSetWriter or DataSetReader). Forward 'ObservabilityRealizedBy' reads binding -> realization; the inverse 'RealizesObservability' reads realization -> binding. Absent (and never required) when the binding is not realized over PubSub - a Server may instead serve the binding over the classic client/server (RPC) interface.

<a id="type-HasBaseBinding"></a>
#### HasBaseBinding  (i=60003)

*Subtype of:* [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) · *InverseName:* `IsBaseBindingOf`

Links a derived or composing ObservabilityBinding to a base ObservabilityBinding whose fields it extends or composes (e.g. a Machine binding to the Device-facet binding it builds on). Optional browse convenience used where the base binding node is present in the same AddressSpace; the portable, cross-specification lineage carrier is ObservabilityBinding.BaseDataSetClassIds.

<a id="type-RealizedBy"></a>
#### RealizedBy  (i=60004)

*Subtype of:* [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) · *InverseName:* `Realizes`

Links the server-wide Observability registry to the ObservabilityBindingGroups it lists. Forward 'RealizedBy' reads registry -> group (the discovery path to every group that exports observability data, across instances and specifications); the inverse 'Realizes' reads group -> registry. Non-hierarchical: a group's single hierarchical parent is the IObservableType object that contains it, so this cross-link never forms a hierarchy loop. Distinct from ObservabilityRealizedBy/RealizesObservability, which links a binding to its optional Part 14 PubSub realization.

### Object types

<a id="type-BoundItemType"></a>
#### BoundItemType  (i=60012)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

A single item bound for observability export: it references the companion-spec node it exposes (BindsToNode and/or a BrowsePath) and carries the routing role (Kind) and the semantic cross-reference retained for export.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| FieldName | Variable | String | Mandatory | BoundItemType | Stable logical field name of the item. |
| Kind | Variable | [BoundItemKindEnum](#type-BoundItemKindEnum) | Mandatory | BoundItemType | Generic routing role of the item. |
| AttributeId | Variable | UInt32 | Optional | BoundItemType | Attribute of the source node to expose (default 13 = Value). |
| BrowsePath | Variable | [RelativePath](https://reference.opcfoundation.org/specs/OPC-10000-4/7.30) | Optional | BoundItemType | RECOMMENDED locator: RelativePath from the bound root; resolved per instance. |
| StartingNode | Variable | NodeId | Optional | BoundItemType | Node the BrowsePath is resolved from (default: the bound root). |
| SourceNodeId | Variable | NodeId | Optional | BoundItemType | Alternative absolute locator (instance/server-specific). |
| SamplingIntervalHint | Variable | Duration | Optional | BoundItemType | Recommended sampling/publishing interval (ms). |
| IndexRange | Variable | NumericRange | Optional | BoundItemType | Optional sub-range for array values. |
| SourceTypeDefinition | Variable | NodeId | Optional | BoundItemType | TypeDefinition of the source node (semantic identity). |
| SourceBrowseName | Variable | QualifiedName | Optional | BoundItemType | Namespace-qualified BrowseName of the source node. |
| ModelNamespaceUri | Variable | String | Optional | BoundItemType | Namespace URI of the companion model defining the source. |
| DataSetFieldId | Variable | Guid | Optional | BoundItemType | GUID correlating the item to Part 14 FieldMetaData. |
| SourceBindingClassId | Variable | Guid | Optional | BoundItemType | Provenance: DataSetClassId of the base observability binding this field originates from (its facet). Lets a subscriber partition a composed DataSet into exact per-base-class field subsets. Absent for fields defined by this binding itself. |
| SemanticReferenceUri | Variable | String | Optional | BoundItemType | Optional external semantic identifier (e.g. IRDI/CDD). |
| DimensionConstantValue | Variable | String | Optional | BoundItemType | For a Kind=Dimension item whose attribute value is a constant (not read from a node): the attribute value; the attribute key is FieldName. Absent for a node-sourced dimension (which uses its BrowsePath). |

<a id="type-BoundVariableType"></a>
#### BoundVariableType  (i=60013)

*Inherits from:* [BoundItemType](#type-BoundItemType)

A bound Variable exposed as a PubSub DataSet field.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| MetricInstrumentType | Variable | [MetricInstrumentTypeEnum](#type-MetricInstrumentTypeEnum) | Optional | BoundVariableType | OTEL metric instrument this value maps to (Counter, UpDownCounter, Histogram, Gauge and the observable variants). When absent a bridge applies the default for the item's Kind. |
| Unit | Variable | String | Optional | BoundVariableType | UCUM unit annotation for the metric. When absent a bridge derives the unit from the source node's EngineeringUnits (EUInformation) where present. |
| ExplicitBucketBoundaries | Variable | Double\[\] | Optional | BoundVariableType | For a Histogram instrument: the explicit bucket boundaries a bridge configures. |
| MetricTemporality | Variable | [MetricTemporalityEnum](#type-MetricTemporalityEnum) | Optional | BoundVariableType | Aggregation temporality (Cumulative/Delta) of the metric value, so a bridge accumulates or reports it correctly. |
| Monotonic | Variable | Boolean | Optional | BoundVariableType | Whether the metric is monotonically increasing. When absent, monotonicity is implied by MetricInstrumentType (e.g. Counter is monotonic, UpDownCounter is not). |
| FieldName | Variable | String | Mandatory | [BoundItemType](#type-BoundItemType) | Stable logical field name of the item. |
| Kind | Variable | [BoundItemKindEnum](#type-BoundItemKindEnum) | Mandatory | [BoundItemType](#type-BoundItemType) | Generic routing role of the item. |
| AttributeId | Variable | UInt32 | Optional | [BoundItemType](#type-BoundItemType) | Attribute of the source node to expose (default 13 = Value). |
| BrowsePath | Variable | [RelativePath](https://reference.opcfoundation.org/specs/OPC-10000-4/7.30) | Optional | [BoundItemType](#type-BoundItemType) | RECOMMENDED locator: RelativePath from the bound root; resolved per instance. |
| StartingNode | Variable | NodeId | Optional | [BoundItemType](#type-BoundItemType) | Node the BrowsePath is resolved from (default: the bound root). |
| SourceNodeId | Variable | NodeId | Optional | [BoundItemType](#type-BoundItemType) | Alternative absolute locator (instance/server-specific). |
| SamplingIntervalHint | Variable | Duration | Optional | [BoundItemType](#type-BoundItemType) | Recommended sampling/publishing interval (ms). |
| IndexRange | Variable | NumericRange | Optional | [BoundItemType](#type-BoundItemType) | Optional sub-range for array values. |
| SourceTypeDefinition | Variable | NodeId | Optional | [BoundItemType](#type-BoundItemType) | TypeDefinition of the source node (semantic identity). |
| SourceBrowseName | Variable | QualifiedName | Optional | [BoundItemType](#type-BoundItemType) | Namespace-qualified BrowseName of the source node. |
| ModelNamespaceUri | Variable | String | Optional | [BoundItemType](#type-BoundItemType) | Namespace URI of the companion model defining the source. |
| DataSetFieldId | Variable | Guid | Optional | [BoundItemType](#type-BoundItemType) | GUID correlating the item to Part 14 FieldMetaData. |
| SourceBindingClassId | Variable | Guid | Optional | [BoundItemType](#type-BoundItemType) | Provenance: DataSetClassId of the base observability binding this field originates from (its facet). Lets a subscriber partition a composed DataSet into exact per-base-class field subsets. Absent for fields defined by this binding itself. |
| SemanticReferenceUri | Variable | String | Optional | [BoundItemType](#type-BoundItemType) | Optional external semantic identifier (e.g. IRDI/CDD). |
| DimensionConstantValue | Variable | String | Optional | [BoundItemType](#type-BoundItemType) | For a Kind=Dimension item whose attribute value is a constant (not read from a node): the attribute value; the attribute key is FieldName. Absent for a node-sourced dimension (which uses its BrowsePath). |

<a id="type-BoundEventFieldType"></a>
#### BoundEventFieldType  (i=60017)

*Inherits from:* [BoundItemType](#type-BoundItemType)

A bound event field of a log or trace (event-sourced) binding, selected by a Part 14 SimpleAttributeOperand. Its BrowsePath is resolved relative to the event TypeDefinition (SourceTypeDefinition), not the AddressSpace instance; the EventSourcePath on the ObservabilityBinding names the notifier it is selected from.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| EventFieldOperand | Variable | [SimpleAttributeOperand](https://reference.opcfoundation.org/specs/OPC-10000-4/7.4.4) | Optional | BoundEventFieldType | The Part 14 SimpleAttributeOperand that selects this field (TypeDefinitionId, BrowsePath, AttributeId); maps directly to a PublishedEvents SelectedFields entry. |
| FieldName | Variable | String | Mandatory | [BoundItemType](#type-BoundItemType) | Stable logical field name of the item. |
| Kind | Variable | [BoundItemKindEnum](#type-BoundItemKindEnum) | Mandatory | [BoundItemType](#type-BoundItemType) | Generic routing role of the item. |
| AttributeId | Variable | UInt32 | Optional | [BoundItemType](#type-BoundItemType) | Attribute of the source node to expose (default 13 = Value). |
| BrowsePath | Variable | [RelativePath](https://reference.opcfoundation.org/specs/OPC-10000-4/7.30) | Optional | [BoundItemType](#type-BoundItemType) | RECOMMENDED locator: RelativePath from the bound root; resolved per instance. |
| StartingNode | Variable | NodeId | Optional | [BoundItemType](#type-BoundItemType) | Node the BrowsePath is resolved from (default: the bound root). |
| SourceNodeId | Variable | NodeId | Optional | [BoundItemType](#type-BoundItemType) | Alternative absolute locator (instance/server-specific). |
| SamplingIntervalHint | Variable | Duration | Optional | [BoundItemType](#type-BoundItemType) | Recommended sampling/publishing interval (ms). |
| IndexRange | Variable | NumericRange | Optional | [BoundItemType](#type-BoundItemType) | Optional sub-range for array values. |
| SourceTypeDefinition | Variable | NodeId | Optional | [BoundItemType](#type-BoundItemType) | TypeDefinition of the source node (semantic identity). |
| SourceBrowseName | Variable | QualifiedName | Optional | [BoundItemType](#type-BoundItemType) | Namespace-qualified BrowseName of the source node. |
| ModelNamespaceUri | Variable | String | Optional | [BoundItemType](#type-BoundItemType) | Namespace URI of the companion model defining the source. |
| DataSetFieldId | Variable | Guid | Optional | [BoundItemType](#type-BoundItemType) | GUID correlating the item to Part 14 FieldMetaData. |
| SourceBindingClassId | Variable | Guid | Optional | [BoundItemType](#type-BoundItemType) | Provenance: DataSetClassId of the base observability binding this field originates from (its facet). Lets a subscriber partition a composed DataSet into exact per-base-class field subsets. Absent for fields defined by this binding itself. |
| SemanticReferenceUri | Variable | String | Optional | [BoundItemType](#type-BoundItemType) | Optional external semantic identifier (e.g. IRDI/CDD). |
| DimensionConstantValue | Variable | String | Optional | [BoundItemType](#type-BoundItemType) | For a Kind=Dimension item whose attribute value is a constant (not read from a node): the attribute value; the attribute key is FieldName. Absent for a node-sourced dimension (which uses its BrowsePath). |

<a id="type-ObservabilityBindingType"></a>
#### ObservabilityBindingType  (i=60011)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

One observability binding on a bound object or type. It declares the OTEL signal kind it exposes (metrics, logs or traces), lists the bound items (browsable and/or as a compact array), carries the OTEL mapping metadata, and may reference the Part 14 nodes that realize it. It lives in an ObservabilityBindingGroup contained by the bound instance; its stable DataSetClassId already encodes the bound type, the signal kind and the major version.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| SignalKind | Variable | [ObservabilitySignalKindEnum](#type-ObservabilitySignalKindEnum) | Mandatory | ObservabilityBindingType | The OTEL signal this binding exposes: Metrics (a data DataSet), Logs (an event DataSet) or Traces (spans from Program executions, audit or correlated events). |
| ConfigurationVersion | Variable | i=14593 | Optional | ObservabilityBindingType | Version of the binding, aligned with the realizing DataSetMetaData. |
| DataSetClassId | Variable | Guid | Mandatory | ObservabilityBindingType | Stable DataSetClassId (Part 14) identifying the observability class this binding defines - a metric set, a log stream, or a trace stream - so subscribers recognize the same class across servers. It is a semantic class identity, not a guarantee of a fixed field layout (see the DataSetClassId clause). Deterministic. |
| BaseDataSetClassIds | Variable | Guid\[\] | Optional | ObservabilityBindingType | DataSetClassIds of the base facet bindings this binding extends or composes (its class lineage). This binding's own DataSetClassId identifies the composed/derived class; a subscriber that knows a base class-id consumes the matching field subset (see BoundItemType.SourceBindingClassId). |
| DataSetCardinalityPath | Variable | [RelativePath](https://reference.opcfoundation.org/specs/OPC-10000-4/7.30) | Optional | ObservabilityBindingType | RelativePath to the cardinality level: the Server/bridge produces one DataSet per matched instance of it (default: the bound root); placeholders below it become fields within that produced DataSet. The DataSetClassId is shared across those DataSets (one class, many writers). |
| DataSetMetaData | Variable | [DataSetMetaDataType](https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.2.3) | Optional | ObservabilityBindingType | Part 14 DataSetMetaData for this DataSet (fields, dataSetClassId, configurationVersion), exposed so a consumer gets the class schema offline. |
| EventSourcePath | Variable | [RelativePath](https://reference.opcfoundation.org/specs/OPC-10000-4/7.30) | Optional | ObservabilityBindingType | For a Logs or Traces binding: RelativePath to the event notifier to subscribe to (default: the cardinality anchor, i.e. the bound root when DataSetCardinalityPath is omitted). |
| Filter | Variable | [ContentFilter](https://reference.opcfoundation.org/specs/OPC-10000-4/7.4.1) | Optional | ObservabilityBindingType | For a Logs or Traces binding: optional ContentFilter (event where-clause). |
| LogTemplate | Variable | String | Optional | ObservabilityBindingType | For a Logs binding: a structured-log message template with {FieldName} holes that reference the binding's bound event fields, so a bridge can render an OTEL LogRecord Body while still carrying the fields as attributes. |
| LogSeverityFieldName | Variable | String | Optional | ObservabilityBindingType | For a Logs binding: FieldName of the bound field carrying severity, mapped to the OTEL LogRecord SeverityNumber/SeverityText. |
| LogBodyFieldName | Variable | String | Optional | ObservabilityBindingType | For a Logs binding: FieldName of the bound field carrying the rendered body, an alternative to LogTemplate when the Server already produces the message text. |
| LogTimestampFieldName | Variable | String | Optional | ObservabilityBindingType | For a Logs binding: FieldName of the bound field carrying the record timestamp, mapped to the OTEL LogRecord Timestamp. |
| SpanNameTemplate | Variable | String | Optional | ObservabilityBindingType | For a Traces binding: a span-name template with {FieldName} holes referencing bound event fields, rendered by a bridge to the OTEL span name. |
| SpanNameFieldName | Variable | String | Optional | ObservabilityBindingType | For a Traces binding: FieldName of the bound field carrying the span name (alternative to SpanNameTemplate). |
| TraceIdFieldName | Variable | String | Optional | ObservabilityBindingType | For a Traces binding: FieldName of the bound field carrying the trace id (16-byte hex or opaque). When absent a bridge derives or generates a trace id. |
| SpanIdFieldName | Variable | String | Optional | ObservabilityBindingType | For a Traces binding: FieldName of the bound field carrying the span id (8-byte hex or opaque). When absent a bridge generates a span id. |
| ParentSpanIdFieldName | Variable | String | Optional | ObservabilityBindingType | For a Traces binding: FieldName of the bound field carrying the parent span id, so a bridge can nest the span under its caller. |
| SpanStartTimeFieldName | Variable | String | Optional | ObservabilityBindingType | For a Traces binding: FieldName of the bound field carrying the span start time (default: the event Time/SourceTimestamp). |
| SpanEndTimeFieldName | Variable | String | Optional | ObservabilityBindingType | For a Traces binding: FieldName of the bound field carrying the span end time. When absent (and no correlation is configured) the event is a zero-duration span. |
| SpanStatusFieldName | Variable | String | Optional | ObservabilityBindingType | For a Traces binding: FieldName of the bound field carrying the span status (Ok/Error/Unset); when absent a bridge derives it from the event Severity/Quality. |
| SpanKind | Variable | String | Optional | ObservabilityBindingType | For a Traces binding: the OTEL SpanKind for spans produced by this binding (Internal, Server, Client, Producer, Consumer). Constant per binding; default Internal. |
| SpanCorrelationFieldName | Variable | String | Optional | ObservabilityBindingType | For a Traces binding: FieldName of the bound field whose value pairs a start event with its matching end event into one span (e.g. a Program run id). When absent, each event is an independent span. |
| BoundItems | Variable | [BoundItemDataType](#type-BoundItemDataType)\[\] | Optional | ObservabilityBindingType | Compact machine-readable list of bound items (the DataSet fields). |
| <BoundItem> | Object |  | OptionalPlaceholder | ObservabilityBindingType | A browsable bound item (rich form of a BoundItems entry). |

<a id="type-ObservabilityBindingGroupType"></a>
#### ObservabilityBindingGroupType  (i=60018)

*Inherits from:* [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6)

A per-companion-specification group of that spec's ObservabilityBinding objects. It is contained (HasComponent) in the IObservableType object that owns the bindings, and is linked to the server-wide Observability registry by a Realizes reference (the inverse of the registry's RealizedBy). Identified by CompanionSpecificationUri (a stable spec-level identifier, distinct from a namespace URI, because a companion specification may define several namespace URIs), so groups from different specifications on one object never collide by BrowseName.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| CompanionSpecificationUri | Variable | String | Mandatory | ObservabilityBindingGroupType | Stable spec-level identifier of the companion specification this group anchors. Sibling groups on one IObservableType object are unique by CompanionSpecificationUri, and each group's BrowseName is derived from this identity so sibling BrowseNames do not collide. |
| ModelNamespaceUris | Variable | String\[\] | Mandatory | ObservabilityBindingGroupType | All namespace URIs the companion specification defines/covers. |
| <ObservabilityBinding> | Object |  | OptionalPlaceholder | ObservabilityBindingGroupType | An observability binding of this companion specification. |

<a id="type-ObservabilityFolderType"></a>
#### ObservabilityFolderType  (i=60010)

*Inherits from:* [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6)

The type of the server-wide Observability registry, exposed as a component of the Server Object. It is the discovery entry point: it references every ObservabilityBindingGroup that exports observability data through non-hierarchical RealizedBy references (the groups themselves stay contained by their bound instances). Extensible - companion specifications contribute their instances' groups.

<a id="type-IObservableType"></a>
#### IObservableType  (i=60016)

*Inherits from:* [BaseInterfaceType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.9)

Interface implemented by a companion-specification ObjectType (or instance) to advertise that it exports observability data, by containing its ObservabilityBindingGroup objects directly (one per companion specification it covers; typically one for a single-specification instance). Each contained group Realizes the server-wide Observability registry.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| <ObservabilityBindingGroup> | Object |  | OptionalPlaceholder | IObservableType | A group of this object's observability bindings for one companion specification, contained here (HasComponent) and linked to the Observability registry by a Realizes reference. Sibling groups have unique BrowseNames, distinguished by specification when several specifications are observable on the instance. |

### Data types

<a id="type-BoundItemKindEnum"></a>
#### BoundItemKindEnum  (i=60051)

*Subtype of:* Enumeration

Generic role of a bound item for routing/bridging to an observability backend. It is intentionally domain-agnostic: a bridge maps each Kind to its target signal without understanding the companion-specification semantics.

| Name | Value | Description |
|---|---|---|
| Telemetry | 0 | A measured/process value that changes continuously (maps to a metric time series). |
| Status | 1 | A discrete state/health/mode value (maps to a numeric-state gauge). |
| Metric | 2 | An aggregated KPI or computed value. |
| Counter | 3 | A monotonically increasing counter/total. |
| Event | 4 | An event or condition field (maps to a log record or a span). |
| Dimension | 5 | An attribute/label that qualifies the metrics, logs and traces of its binding (an OTEL attribute or Resource dimension), not a measured value. Applied to every data point the binding produces. |
| Identification | 6 | Static nameplate/identity information, typically emitted as an OTEL Resource attribute. |
| Other | 7 | Any other role. |

<a id="type-MetricInstrumentTypeEnum"></a>
#### MetricInstrumentTypeEnum  (i=60053)

*Subtype of:* Enumeration

The OpenTelemetry-style metric instrument a bound value maps to. Lets a bridge emit the correct instrument without domain knowledge; complements the coarser BoundItemKindEnum.

| Name | Value | Description |
|---|---|---|
| Counter | 0 | Monotonically increasing synchronous sum (OTEL Counter). |
| UpDownCounter | 1 | Non-monotonic synchronous sum (OTEL UpDownCounter). |
| Histogram | 2 | Synchronous distribution of values (OTEL Histogram). |
| Gauge | 3 | Synchronous last-value sample (OTEL Gauge). |
| ObservableCounter | 4 | Asynchronous monotonic sum, observed on collect (OTEL ObservableCounter). |
| ObservableUpDownCounter | 5 | Asynchronous non-monotonic sum (OTEL ObservableUpDownCounter). |
| ObservableGauge | 6 | Asynchronous last-value sample (OTEL ObservableGauge). |

<a id="type-MetricTemporalityEnum"></a>
#### MetricTemporalityEnum  (i=60054)

*Subtype of:* Enumeration

Aggregation temporality of a metric value, so a bridge accumulates or reports it correctly.

| Name | Value | Description |
|---|---|---|
| Cumulative | 0 | The value is a running total since a fixed start (OTEL cumulative). |
| Delta | 1 | The value is the change since the previous report (OTEL delta). |

<a id="type-ObservabilitySignalKindEnum"></a>
#### ObservabilitySignalKindEnum  (i=60052)

*Subtype of:* Enumeration

The OTEL signal an observability binding exposes: metrics (a Part 14 data DataSet, PublishedDataItems), logs (an event DataSet, PublishedEvents), or traces (spans produced from Program executions, audit events or correlated events). A binding is exactly one signal kind.

| Name | Value | Description |
|---|---|---|
| Metrics | 0 | A metric set: grouped Variable values mapped to OTEL metric instruments (PublishedDataItemsType). |
| Logs | 1 | A log stream: selected event fields from a notifier mapped to OTEL LogRecords (PublishedEventsType). |
| Traces | 2 | A trace/span stream: Program executions, audit events or correlated events mapped to OTEL spans (PublishedEventsType). |

<a id="type-BoundItemDataType"></a>
#### BoundItemDataType  (i=60060)

*Subtype of:* Structure

Machine-readable descriptor of a single bound item: how to LOCATE it (BrowsePath relative to StartingNode, or an absolute SourceNodeId), its routing role (Kind) and the SEMANTIC cross-reference back to the companion model (TypeDefinition, BrowseName, ModelNamespaceUri, SemanticReferenceUri), which is retained so it can be exported to a disconnected consumer.

| Field | DataType | Description |
|---|---|---|
| FieldName | String | Stable logical field name; matches the PubSub DataSet field name. |
| Kind | [BoundItemKindEnum](#type-BoundItemKindEnum) | Generic routing role of the item. |
| AttributeId | UInt32 | Attribute of the source node to expose (default 13 = Value). |
| SamplingIntervalHint | Duration | Recommended sampling/publishing interval, in ms. |
| IndexRange | NumericRange | Optional sub-range for array values. |
| StartingNode | NodeId | Node the BrowsePath is resolved from (default: the bound root). |
| BrowsePath | [RelativePath](https://reference.opcfoundation.org/specs/OPC-10000-4/7.30) | RECOMMENDED locator: RelativePath from StartingNode (type-level, portable). |
| SourceNodeId | NodeId | Alternative absolute locator (instance/server-specific). |
| SourceTypeDefinition | NodeId | TypeDefinition of the source node (semantic identity). |
| SourceBrowseName | QualifiedName | Namespace-qualified BrowseName of the source node. |
| ModelNamespaceUri | String | Namespace URI of the companion model that defines the source. |
| DataSetFieldId | Guid | GUID correlating this item to Part 14 FieldMetaData.dataSetFieldId. |
| SourceBindingClassId | Guid | Provenance: DataSetClassId of the base observability binding this field originates from (its facet). Lets a subscriber partition a composed DataSet into exact per-base-class field subsets. Absent for fields defined by this binding itself. |
| SemanticReferenceUri | String | Optional external semantic identifier (e.g. IRDI/CDD) for the item. |
| EventFieldOperand | [SimpleAttributeOperand](https://reference.opcfoundation.org/specs/OPC-10000-4/7.4.4) | For a log/trace (event-DataSet) field: the Part 14 SimpleAttributeOperand that selects it (alternative/complement to BrowsePath, whose segments are then relative to the event TypeDefinition). |
| MetricInstrumentType | [MetricInstrumentTypeEnum](#type-MetricInstrumentTypeEnum) | OTEL metric instrument this value maps to (Counter, Histogram, Gauge, …), for a Metrics binding. |
| Unit | String | UCUM unit annotation for the metric; if absent a bridge derives it from the source node's EngineeringUnits. |
| ExplicitBucketBoundaries | Double\[\] | For a Histogram instrument: the explicit bucket boundaries. |
| MetricTemporality | [MetricTemporalityEnum](#type-MetricTemporalityEnum) | Aggregation temporality (Cumulative/Delta) of the metric value. |
| Monotonic | Boolean | Whether the metric is monotonic; if absent it is implied by MetricInstrumentType. |
| DimensionConstantValue | String | For a Kind=Dimension item with a constant value: the attribute value (key is FieldName). Absent when the dimension value is read from the source node. |

### Methods

| Method | Owning type | Input arguments | Output arguments |
|---|---|---|---|

### Well-known instances

| BrowseName | NodeId | TypeDefinition | Note |
|---|---|---|---|
| Observability | i=60101 | [ObservabilityFolderType](#type-ObservabilityFolderType) | Server-wide registry of observability bindings, discoverable as a component of the Server object. It references (RealizedBy) every ObservabilityBindingGroup exposed by the Server's instances; its presence does not require any PubSub configuration. |

