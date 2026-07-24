<a id="annex-a"></a>

## Annex A — Information model

This annex is the normative node reference. It is generated from `core-specs/extras/observability-export/tools/build_model.py` and always matches `Opc.Ua.ObservabilityExport.NodeSet2.xml`. All nodes are defined in this specification's own namespace `http://opcfoundation.org/UA/ObservabilityExport/` (namespace index 1 in the NodeSet, which requires the base OPC UA namespace); the NodeIds shown are the draft numeric identifiers within that namespace. The **Declared in** column marks members inherited from a supertype.

### Type overview

| NodeId | BrowseName | NodeClass | Subtype of |
|---|---|---|---|
| i=60001 | [BindsToNode](#type-BindsToNode) | ReferenceType | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) |
| i=60002 | [ExportedBy](#type-ExportedBy) | ReferenceType | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) |
| i=60003 | [HasBaseBinding](#type-HasBaseBinding) | ReferenceType | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) |
| i=60004 | [Collects](#type-Collects) | ReferenceType | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) |
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

<a id="type-ExportedBy"></a>

#### ExportedBy  (i=60002)

*Subtype of:* [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) · *InverseName:* `Exports`

Links an ObservabilityBinding to the optional OPC UA Part 14 PubSub node(s) that export it (a PublishedDataSet, DataSetWriter or DataSetReader) - the concrete OTEL exporter for the binding's signal. Forward 'ExportedBy' reads binding -> exporter; the inverse 'Exports' reads exporter -> binding. Absent (and never required) when the binding is not exported over PubSub - a Server may instead serve the binding over the classic client/server (RPC) interface.

<a id="type-HasBaseBinding"></a>

#### HasBaseBinding  (i=60003)

*Subtype of:* [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) · *InverseName:* `IsBaseBindingOf`

Links a derived or composing ObservabilityBinding to a base ObservabilityBinding whose fields it extends or composes (e.g. a Machine binding to the Device-facet binding it builds on). Optional browse convenience used where the base binding node is present in the same AddressSpace; the portable, cross-specification lineage carrier is ObservabilityBinding.BaseDataSetClassIds.

<a id="type-Collects"></a>

#### Collects  (i=60004)

*Subtype of:* [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) · *InverseName:* `CollectedBy`

Links the server-wide Observability registry to the ObservabilityBindingGroups it collects. Forward 'Collects' reads registry -> group (the discovery path to every group that exports observability data, across instances and specifications); the inverse 'CollectedBy' reads group -> registry. Non-hierarchical: a group's single hierarchical parent is the IObservableType object that contains it, so this cross-link never forms a hierarchy loop. Distinct from ExportedBy/Exports, which links a binding to its optional Part 14 PubSub exporter.

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

A per-companion-specification group of that spec's ObservabilityBinding objects. It is contained (HasComponent) in the IObservableType object that owns the bindings, and is collected by the server-wide Observability registry (the registry Collects it; the group carries the inverse CollectedBy reference). Identified by CompanionSpecificationUri (a stable spec-level identifier, distinct from a namespace URI, because a companion specification may define several namespace URIs), so groups from different specifications on one object never collide by BrowseName.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| CompanionSpecificationUri | Variable | String | Mandatory | ObservabilityBindingGroupType | Stable spec-level identifier of the companion specification this group anchors. Sibling groups on one IObservableType object are unique by CompanionSpecificationUri, and each group's BrowseName is derived from this identity so sibling BrowseNames do not collide. |
| ModelNamespaceUris | Variable | String\[\] | Mandatory | ObservabilityBindingGroupType | All namespace URIs the companion specification defines/covers. |
| <ObservabilityBinding> | Object |  | OptionalPlaceholder | ObservabilityBindingGroupType | An observability binding of this companion specification. |

<a id="type-ObservabilityFolderType"></a>

#### ObservabilityFolderType  (i=60010)

*Inherits from:* [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6)

The type of the server-wide Observability registry, exposed as a component of the Server Object. It is the discovery entry point: it Collects every ObservabilityBindingGroup that exports observability data through non-hierarchical Collects references (the groups themselves stay contained by their bound instances). Extensible - companion specifications contribute their instances' groups.

<a id="type-IObservableType"></a>

#### IObservableType  (i=60016)

*Inherits from:* [BaseInterfaceType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.9)

Interface implemented by a companion-specification ObjectType (or instance) to advertise that it exports observability data, by containing its ObservabilityBindingGroup objects directly (one per companion specification it covers; typically one for a single-specification instance). Each contained group is collected by the server-wide Observability registry (CollectedBy).

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| <ObservabilityBindingGroup> | Object |  | OptionalPlaceholder | IObservableType | A group of this object's observability bindings for one companion specification, contained here (HasComponent) and collected by the Observability registry (the inverse CollectedBy reference). Sibling groups have unique BrowseNames, distinguished by specification when several specifications are observable on the instance. |

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
| Observability | i=60101 | [ObservabilityFolderType](#type-ObservabilityFolderType) | Server-wide registry of observability bindings, discoverable as a component of the Server object. It Collects every ObservabilityBindingGroup exposed by the Server's instances; its presence does not require any PubSub configuration. |
