<a id="annex-a"></a>
## Annex A — Information model

This annex is the normative node reference. It is generated from `extras/scenario-binding/tools/build_model.py` and always matches `Opc.Ua.ScenarioBinding.NodeSet2.xml`. All nodes are proposed additions to the base OPC UA namespace `http://opcfoundation.org/UA/`; the NodeIds shown are **provisional** (final IDs are assigned by the OPC Foundation). The **Declared in** column marks members inherited from a supertype.

### Type overview

| NodeId | BrowseName | NodeClass | Subtype of |
|---|---|---|---|
| i=60001 | [BindsToNode](#type-BindsToNode) | ReferenceType | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) |
| i=60002 | [ScenarioRealizedBy](#type-ScenarioRealizedBy) | ReferenceType | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) |
| i=60003 | [HasBaseBinding](#type-HasBaseBinding) | ReferenceType | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) |
| i=60004 | [RealizedBy](#type-RealizedBy) | ReferenceType | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) |
| i=60012 | [BoundItemType](#type-BoundItemType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| i=60013 | [BoundVariableType](#type-BoundVariableType) | ObjectType | [BoundItemType](#type-BoundItemType) |
| i=60014 | [BoundMethodType](#type-BoundMethodType) | ObjectType | [BoundItemType](#type-BoundItemType) |
| i=60017 | [BoundEventFieldType](#type-BoundEventFieldType) | ObjectType | [BoundItemType](#type-BoundItemType) |
| i=60011 | [ScenarioBindingType](#type-ScenarioBindingType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| i=60018 | [ScenarioBindingGroupType](#type-ScenarioBindingGroupType) | ObjectType | [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6) |
| i=60010 | [ScenarioFolderType](#type-ScenarioFolderType) | ObjectType | [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6) |
| i=60015 | [ScenarioProfileType](#type-ScenarioProfileType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| i=60016 | [IScenarioBoundType](#type-IScenarioBoundType) | ObjectType | [BaseInterfaceType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.9) |
| i=60050 | [ScenarioBindingDirectionEnum](#type-ScenarioBindingDirectionEnum) | DataType | Enumeration |
| i=60051 | [BoundItemKindEnum](#type-BoundItemKindEnum) | DataType | Enumeration |
| i=60053 | [MetricInstrumentTypeEnum](#type-MetricInstrumentTypeEnum) | DataType | Enumeration |
| i=60054 | [MetricTemporalityEnum](#type-MetricTemporalityEnum) | DataType | Enumeration |
| i=60052 | [ScenarioContentKindEnum](#type-ScenarioContentKindEnum) | DataType | Enumeration |
| i=60060 | [BoundItemDataType](#type-BoundItemDataType) | DataType | Structure |

### Reference types

<a id="type-BindsToNode"></a>
#### BindsToNode  (i=60001)

*Subtype of:* [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) · *InverseName:* `IsBoundBy`

Links a BoundItem to the companion-specification Variable or Method in the AddressSpace that it exposes for a scenario. The target is the authoritative semantic node; the BoundItem does not copy its meaning.

<a id="type-ScenarioRealizedBy"></a>
#### ScenarioRealizedBy  (i=60002)

*Subtype of:* [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) · *InverseName:* `RealizesScenario`

Links a ScenarioBinding to the optional OPC UA Part 14 PubSub node(s) that realize it (a PublishedDataSet, DataSetWriter, DataSetReader or an ActionTarget). Forward 'ScenarioRealizedBy' reads binding -> realization; the inverse 'RealizesScenario' reads realization -> binding. Absent (and never required) when the binding is not realized over PubSub - a Server may instead serve the binding over the classic client/server (RPC) interface.

<a id="type-HasBaseBinding"></a>
#### HasBaseBinding  (i=60003)

*Subtype of:* [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) · *InverseName:* `IsBaseBindingOf`

Links a derived or composing ScenarioBinding to a base ScenarioBinding whose fields it extends or composes (e.g. a Machine binding to the Device-facet binding it builds on). Optional browse convenience used where the base binding node is present in the same AddressSpace; the portable, cross-specification lineage carrier is ScenarioBinding.BaseDataSetClassIds.

<a id="type-RealizedBy"></a>
#### RealizedBy  (i=60004)

*Subtype of:* [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-3/7.4) · *InverseName:* `Realizes`

Links a ScenarioProfile to the ScenarioBindingGroups that serve its scenario. Forward 'RealizedBy' reads profile -> group (the registry's scenario-first path to every group serving the scenario, across instances and specifications); the inverse 'Realizes' reads group -> profile, so given a group a client resolves its scenario - and thus the ScenarioUri - from the profile under the Scenarios registry. Non-hierarchical: a group's single hierarchical parent is the IScenarioBoundType object that contains it, so this cross-link never forms a hierarchy loop. Distinct from ScenarioRealizedBy/RealizesScenario, which links a binding to its optional Part 14 PubSub realization.

### Object types

<a id="type-BoundItemType"></a>
#### BoundItemType  (i=60012)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

A single item bound into a scenario: it references the companion-spec node it exposes (BindsToNode and/or a BrowsePath) and carries the routing role (Kind) and the semantic cross-reference retained for export.

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
| SourceScenarioBindingClassId | Variable | Guid | Optional | BoundItemType | Provenance: DataSetClassId of the base scenario binding this field originates from (its facet). Lets a subscriber partition a composed DataSet into exact per-base-class field subsets. Absent for fields defined by this binding itself. |
| SemanticReferenceUri | Variable | String | Optional | BoundItemType | Optional external semantic identifier (e.g. IRDI/CDD). |
| DimensionConstantValue | Variable | String | Optional | BoundItemType | For a Kind=Dimension item whose attribute value is a constant (not read from a node): the attribute value; the attribute key is FieldName. Absent for a node-sourced dimension (which uses its BrowsePath). |

<a id="type-BoundVariableType"></a>
#### BoundVariableType  (i=60013)

*Inherits from:* [BoundItemType](#type-BoundItemType)

A bound Variable exposed as a PubSub DataSet field.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| MetricInstrumentType | Variable | [MetricInstrumentTypeEnum](#type-MetricInstrumentTypeEnum) | Optional | BoundVariableType | OTEL metric instrument this value maps to (Counter, UpDownCounter, Histogram, Gauge and the observable variants). Primarily used by the Observability scenario; when absent a bridge applies the default for the item's Kind. |
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
| SourceScenarioBindingClassId | Variable | Guid | Optional | [BoundItemType](#type-BoundItemType) | Provenance: DataSetClassId of the base scenario binding this field originates from (its facet). Lets a subscriber partition a composed DataSet into exact per-base-class field subsets. Absent for fields defined by this binding itself. |
| SemanticReferenceUri | Variable | String | Optional | [BoundItemType](#type-BoundItemType) | Optional external semantic identifier (e.g. IRDI/CDD). |
| DimensionConstantValue | Variable | String | Optional | [BoundItemType](#type-BoundItemType) | For a Kind=Dimension item whose attribute value is a constant (not read from a node): the attribute value; the attribute key is FieldName. Absent for a node-sourced dimension (which uses its BrowsePath). |

<a id="type-BoundMethodType"></a>
#### BoundMethodType  (i=60014)

*Inherits from:* [BoundItemType](#type-BoundItemType)

A bound Method exposed as an invokable action; may be realized as a Part 14 Action/ActionTarget.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| OwningObjectPath | Variable | [RelativePath](https://reference.opcfoundation.org/specs/OPC-10000-4/7.30) | Optional | BoundMethodType | RelativePath to the Object the Method is called on (default: the bound root). |
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
| SourceScenarioBindingClassId | Variable | Guid | Optional | [BoundItemType](#type-BoundItemType) | Provenance: DataSetClassId of the base scenario binding this field originates from (its facet). Lets a subscriber partition a composed DataSet into exact per-base-class field subsets. Absent for fields defined by this binding itself. |
| SemanticReferenceUri | Variable | String | Optional | [BoundItemType](#type-BoundItemType) | Optional external semantic identifier (e.g. IRDI/CDD). |
| DimensionConstantValue | Variable | String | Optional | [BoundItemType](#type-BoundItemType) | For a Kind=Dimension item whose attribute value is a constant (not read from a node): the attribute value; the attribute key is FieldName. Absent for a node-sourced dimension (which uses its BrowsePath). |

<a id="type-BoundEventFieldType"></a>
#### BoundEventFieldType  (i=60017)

*Inherits from:* [BoundItemType](#type-BoundItemType)

A bound event field of an event DataSet, selected by a Part 14 SimpleAttributeOperand. Its BrowsePath is resolved relative to the event TypeDefinition (SourceTypeDefinition), not the AddressSpace instance; the EventSourcePath on the ScenarioBinding names the notifier it is selected from.

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
| SourceScenarioBindingClassId | Variable | Guid | Optional | [BoundItemType](#type-BoundItemType) | Provenance: DataSetClassId of the base scenario binding this field originates from (its facet). Lets a subscriber partition a composed DataSet into exact per-base-class field subsets. Absent for fields defined by this binding itself. |
| SemanticReferenceUri | Variable | String | Optional | [BoundItemType](#type-BoundItemType) | Optional external semantic identifier (e.g. IRDI/CDD). |
| DimensionConstantValue | Variable | String | Optional | [BoundItemType](#type-BoundItemType) | For a Kind=Dimension item whose attribute value is a constant (not read from a node): the attribute value; the attribute key is FieldName. Absent for a node-sourced dimension (which uses its BrowsePath). |

<a id="type-ScenarioBindingType"></a>
#### ScenarioBindingType  (i=60011)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

One scenario binding on a bound object or type. It declares the direction, lists the bound items (browsable and/or as a compact array), and may reference the Part 14 nodes that realize it. Its scenario is not stored here: the binding lives in a ScenarioBindingGroup whose profile (reached via the group's Realizes reference) carries the ScenarioUri, and the DataSetClassId already encodes the scenario.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Direction | Variable | [ScenarioBindingDirectionEnum](#type-ScenarioBindingDirectionEnum) | Mandatory | ScenarioBindingType | Role the server offers for this binding. |
| ConfigurationVersion | Variable | i=14593 | Optional | ScenarioBindingType | Version of the binding, aligned with the realizing DataSetMetaData. |
| DataSetClassId | Variable | Guid | Mandatory | ScenarioBindingType | Stable DataSetClassId (Part 14) identifying the class of the DataSet this binding defines, so subscribers recognize the same DataSet class across servers. It is a semantic class identity, not a guarantee of a fixed field layout (see the DataSetClassId clause). Deterministic. |
| BaseDataSetClassIds | Variable | Guid\[\] | Optional | ScenarioBindingType | DataSetClassIds of the base facet bindings this binding extends or composes (its class lineage). This binding's own DataSetClassId identifies the composed/derived class; a subscriber that knows a base class-id consumes the matching field subset (see BoundItemType.SourceScenarioBindingClassId). |
| ContentKind | Variable | [ScenarioContentKindEnum](#type-ScenarioContentKindEnum) | Mandatory | ScenarioBindingType | Whether the binding realizes as a data DataSet (PublishedDataItems) or an event DataSet (PublishedEvents). |
| DataSetCardinalityPath | Variable | [RelativePath](https://reference.opcfoundation.org/specs/OPC-10000-4/7.30) | Optional | ScenarioBindingType | RelativePath to the cardinality level: the Server/bridge produces one DataSet per matched instance of it (default: the bound root); placeholders below it become fields. The DataSetClassId is shared across those DataSets (one class, many writers). |
| DataSetMetaData | Variable | [DataSetMetaDataType](https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.2.3) | Optional | ScenarioBindingType | Part 14 DataSetMetaData for this DataSet (fields, dataSetClassId, configurationVersion), exposed so a consumer gets the class schema offline. |
| EventSourcePath | Variable | [RelativePath](https://reference.opcfoundation.org/specs/OPC-10000-4/7.30) | Optional | ScenarioBindingType | For an event DataSet: RelativePath to the event notifier to subscribe to (default: the cardinality anchor, i.e. the bound root when DataSetCardinalityPath is omitted). |
| Filter | Variable | [ContentFilter](https://reference.opcfoundation.org/specs/OPC-10000-4/7.4.1) | Optional | ScenarioBindingType | For an event DataSet: optional ContentFilter (event where-clause). |
| LogTemplate | Variable | String | Optional | ScenarioBindingType | For an event/log DataSet: a structured-log message template with {FieldName} holes that reference the binding's bound event fields, so a bridge can render an OTEL LogRecord Body while still carrying the fields as attributes. |
| LogSeverityFieldName | Variable | String | Optional | ScenarioBindingType | For an event/log DataSet: FieldName of the bound field carrying severity, mapped to the OTEL LogRecord SeverityNumber/SeverityText. |
| LogBodyFieldName | Variable | String | Optional | ScenarioBindingType | For an event/log DataSet: FieldName of the bound field carrying the rendered body, an alternative to LogTemplate when the Server already produces the message text. |
| LogTimestampFieldName | Variable | String | Optional | ScenarioBindingType | For an event/log DataSet: FieldName of the bound field carrying the record timestamp, mapped to the OTEL LogRecord Timestamp. |
| BoundItems | Variable | [BoundItemDataType](#type-BoundItemDataType)\[\] | Optional | ScenarioBindingType | Compact machine-readable list of bound items (the DataSet fields). |
| <BoundItem> | Object |  | OptionalPlaceholder | ScenarioBindingType | A browsable bound item (rich form of a BoundItems entry). |

<a id="type-ScenarioBindingGroupType"></a>
#### ScenarioBindingGroupType  (i=60018)

*Inherits from:* [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6)

A per-companion-specification group of that spec's ScenarioBinding objects. It is contained (HasComponent) in the IScenarioBoundType object that owns the bindings, and is linked to the ScenarioProfile it serves by a Realizes reference (the inverse of the profile's RealizedBy). Identified by CompanionSpecificationUri (a stable spec-level identifier, distinct from a namespace URI, because a companion specification may define several namespace URIs), so groups from different specifications on one object never collide by BrowseName.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| CompanionSpecificationUri | Variable | String | Mandatory | ScenarioBindingGroupType | Stable spec-level identifier of the companion specification this group anchors. Sibling groups on one IScenarioBoundType object are unique by (Scenario x CompanionSpecificationUri), and each group's BrowseName is derived from this identity so sibling BrowseNames do not collide. |
| ModelNamespaceUris | Variable | String\[\] | Mandatory | ScenarioBindingGroupType | All namespace URIs the companion specification defines/covers. |
| <ScenarioBinding> | Object |  | OptionalPlaceholder | ScenarioBindingGroupType | A scenario binding of this companion specification. |

<a id="type-ScenarioFolderType"></a>
#### ScenarioFolderType  (i=60010)

*Inherits from:* [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6)

The type of the Scenarios registry: a discoverable folder of ScenarioProfile objects, exposed as a component of the Server Object. It is the scenario-first discovery entry point. Extensible - companion and scenario specifications add their own ScenarioProfile objects.

<a id="type-ScenarioProfileType"></a>
#### ScenarioProfileType  (i=60015)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

A registered integration scenario: its URI plus human-readable metadata, and RealizedBy references to the ScenarioBindingGroups (which live on the bound instances) that serve this scenario. Groups are not contained here - the profile is not duplicated per instance; a group reaches its profile via the inverse Realizes reference. The registry is extensible; vendors and other specifications add profiles with their own URIs.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| ScenarioUri | Variable | String | Mandatory | ScenarioProfileType | The scenario URI. Authoritative here; a binding's scenario is this ScenarioUri, reached from the binding's group via Realizes. |
| Title | Variable | LocalizedText | Optional | ScenarioProfileType | Short human-readable title. |
| Summary | Variable | LocalizedText | Optional | ScenarioProfileType | Human-readable description of the scenario and its intended consumers. |
| Keywords | Variable | String\[\] | Optional | ScenarioProfileType | Keywords describing the scenario. |

<a id="type-IScenarioBoundType"></a>
#### IScenarioBoundType  (i=60016)

*Inherits from:* [BaseInterfaceType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.9)

Interface implemented by a companion-specification ObjectType (or instance) to advertise that it participates in scenario bindings, by containing its ScenarioBindingGroup objects directly (one per (Scenario x companion specification) it serves; typically one per scenario for a single-specification instance). Each contained group Realizes the ScenarioProfile under the Scenarios registry that defines its scenario.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| <ScenarioBindingGroup> | Object |  | OptionalPlaceholder | IScenarioBoundType | A group of this object's bindings for one (Scenario x companion specification), contained here (HasComponent) and linked to its ScenarioProfile by a Realizes reference. Sibling groups have unique BrowseNames - by scenario for a single-specification instance, and additionally by specification when several specifications serve one scenario on the instance. |

### Data types

<a id="type-ScenarioBindingDirectionEnum"></a>
#### ScenarioBindingDirectionEnum  (i=60050)

*Subtype of:* Enumeration

The role the server offers for a ScenarioBinding, and hence what a client sets up on the other side.

| Name | Value | Description |
|---|---|---|
| Publisher | 0 | The server publishes the bound data; a client sets up a subscriber. |
| Subscriber | 1 | The server subscribes to the bound data; a client sets up a publisher. |
| ActionInvoker | 2 | The server invokes bound Methods/Actions on receipt; a client sends the trigger. |
| ActionResponder | 3 | The server responds to bound Actions; a client invokes them. |
| Bidirectional | 4 | Both data and action directions apply. |

<a id="type-BoundItemKindEnum"></a>
#### BoundItemKindEnum  (i=60051)

*Subtype of:* Enumeration

Generic role of a bound item for routing/bridging. It is intentionally domain-agnostic: a bridge maps each Kind to its target system without understanding the companion-specification semantics.

| Name | Value | Description |
|---|---|---|
| Telemetry | 0 | A measured/process value that changes continuously (maps to a time series). |
| Status | 1 | A discrete state/health/mode value. |
| Configuration | 2 | A configuration/parameter value that changes rarely. |
| Metric | 3 | An aggregated KPI or computed value. |
| Counter | 4 | A monotonically increasing counter/total. |
| Event | 5 | An event or condition (maps to a log/alarm stream). |
| Command | 6 | A bound Method/Action invocation (maps to an action). |
| Setpoint | 7 | A writable setpoint/target value. |
| Identification | 8 | Static nameplate/identity information. |
| Other | 9 | Any other role. |
| Dimension | 10 | An attribute/label that qualifies the metrics and logs of its binding (an OTEL/metric dimension), not a measured value. Applied to every data point the binding produces. |

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

<a id="type-ScenarioContentKindEnum"></a>
#### ScenarioContentKindEnum  (i=60052)

*Subtype of:* Enumeration

Whether a scenario binding realizes as a Part 14 data DataSet (PublishedDataItems) or an event DataSet (PublishedEvents). A binding is exactly one DataSet.

| Name | Value | Description |
|---|---|---|
| DataItems | 0 | A data DataSet: grouped Variable values (PublishedDataItemsType). |
| Events | 1 | An event DataSet: selected event fields from a notifier (PublishedEventsType). |

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
| OwningObjectPath | [RelativePath](https://reference.opcfoundation.org/specs/OPC-10000-4/7.30) | For a bound Method: RelativePath to the Object it is called on (default: the bound root). |
| SourceTypeDefinition | NodeId | TypeDefinition of the source node (semantic identity). |
| SourceBrowseName | QualifiedName | Namespace-qualified BrowseName of the source node. |
| ModelNamespaceUri | String | Namespace URI of the companion model that defines the source. |
| DataSetFieldId | Guid | GUID correlating this item to Part 14 FieldMetaData.dataSetFieldId. |
| SourceScenarioBindingClassId | Guid | Provenance: DataSetClassId of the base scenario binding this field originates from (its facet). Lets a subscriber partition a composed DataSet into exact per-base-class field subsets. Absent for fields defined by this binding itself. |
| SemanticReferenceUri | String | Optional external semantic identifier (e.g. IRDI/CDD) for the item. |
| EventFieldOperand | [SimpleAttributeOperand](https://reference.opcfoundation.org/specs/OPC-10000-4/7.4.4) | For an event-DataSet field: the Part 14 SimpleAttributeOperand that selects it (alternative/complement to BrowsePath, whose segments are then relative to the event TypeDefinition). |
| MetricInstrumentType | [MetricInstrumentTypeEnum](#type-MetricInstrumentTypeEnum) | OTEL metric instrument this value maps to (Counter, Histogram, Gauge, …); primarily for the Observability scenario. |
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
| Scenarios | i=60101 | [ScenarioFolderType](#type-ScenarioFolderType) | Server-wide registry of integration scenarios, discoverable as a component of the Server object. It is the scenario-first entry point; its presence does not require any PubSub configuration. |
| Observability | i=60110 | [ScenarioProfileType](#type-ScenarioProfileType) | Real-time operational monitoring: SCADA/HMI, dashboards and observability platforms (e.g. OpenTelemetry). Low latency, cyclic telemetry and status. |
| PredictiveMaintenance | i=60111 | [ScenarioProfileType](#type-ScenarioProfileType) | Condition- and usage-based trending fed to maintenance analytics to forecast wear and schedule service. |
| AnomalyDetection | i=60112 | [ScenarioProfileType](#type-ScenarioProfileType) | High-resolution, correlated signals for baseline modelling and deviation/outlier detection. |
| EnergyAndLoadManagement | i=60113 | [ScenarioProfileType](#type-ScenarioProfileType) | Power, load, demand and energy signals for load management, peak shaving and grid-services coordination. |
| AlarmAndEventDistribution | i=60114 | [ScenarioProfileType](#type-ScenarioProfileType) | Condition and event streams for operators, CMMS/EAM and safety functions. |
| FleetAndCompliance | i=60115 | [ScenarioProfileType](#type-ScenarioProfileType) | Multi-site supervision, contractual reporting and regulatory compliance. |

