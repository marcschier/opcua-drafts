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
