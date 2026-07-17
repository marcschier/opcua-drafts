<a id="annex-a"></a>

## Annex A — Information model

This annex is the normative node reference. It is generated from `tools/build_model.py` and always matches `Opc.Ua.XRegistry.NodeSet2.xml`. All nodes are defined in the companion namespace `http://opcfoundation.org/UA/xRegistry/` (which requires the base OPC UA namespace); the numeric NodeIds shown are **draft** identifiers within that namespace. The **Declared in** column marks members inherited from a supertype.

### Type overview

| NodeId | BrowseName | NodeClass | Subtype of |
|---|---|---|---|
| ns=1;i=63000 | [RegistryType](#type-RegistryType) | ObjectType | [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6) |
| ns=1;i=63001 | [GroupType](#type-GroupType) | ObjectType | [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6) |
| ns=1;i=63002 | [ResourceType](#type-ResourceType) | ObjectType | [FileType](https://reference.opcfoundation.org/specs/OPC-10000-20/4.2) |
| ns=1;i=63003 | [AttributesType](#type-AttributesType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| ns=1;i=63004 | [RegistryCapabilitiesDataType](#type-RegistryCapabilitiesDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24) |

### Object types

<a id="type-RegistryType"></a>

#### RegistryType  (ns=1;i=63000)

*Inherits from:* [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6)

The abstract xRegistry root, expressed as a FolderType that organizes its Group objects. It creates groups through the CreateGroup Method; a group is removed with its own Delete Method. The physical backing may be a file-system directory, but the type is a plain organizing folder. Domain registries subtype this.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| RegistryId | Variable | String | Mandatory | RegistryType | xRegistry registryid: the stable identifier of this registry. |
| SpecVersion | Variable | String | Optional | RegistryType | The xRegistry specification version this registry conforms to. |
| Capabilities | Object |  | Optional | RegistryType | The registry capabilities document (xRegistry /capabilities): a FileType whose content is the capabilities JSON, read with the inherited Open/Read/Close Methods (so an arbitrarily large document is not bounded by MaxStringLength). |
| Model | Object |  | Optional | RegistryType | The registry model document (xRegistry /model): a FileType whose content is the model JSON, read with the inherited Open/Read/Close Methods. No structured DataType is defined for the model because the OPC UA AddressSpace type system (the ObjectTypes and their members) is the structural equivalent of the model. |
| CapabilitiesInfo | Variable | [RegistryCapabilitiesDataType](#type-RegistryCapabilitiesDataType) | Optional | RegistryType | The typed form of the registry capabilities (RegistryCapabilitiesDataType), read as a single Variant value, in addition to the raw JSON of the Capabilities FileType. |
| Xid | Variable | String | Optional | RegistryType | xRegistry relative identifier (xid): the entity's stable path within the registry, independent of the hosting endpoint. |
| Epoch | Variable | UInt32 | Optional | RegistryType | xRegistry epoch: a counter that increments on every change to the entity. |
| Name | Variable | String | Optional | RegistryType | Human-readable name of the entity. |
| Description | Variable | String | Optional | RegistryType | Human-readable description of the entity. |
| Documentation | Variable | String | Optional | RegistryType | URL to human-readable documentation for the entity. |
| Labels | Object |  | Optional | RegistryType | The entity's extensible xRegistry labels/attributes, exposed as an AttributesType container: each label is a browsable PropertyType Variable, added and removed with the container's AddAttribute/RemoveAttribute Methods. Deleted together with the entity. |
| CreatedAt | Variable | DateTime | Optional | RegistryType | UTC timestamp when the entity was created. |
| ModifiedAt | Variable | DateTime | Optional | RegistryType | UTC timestamp when the entity was last modified. |
| <Group> | Object |  | OptionalPlaceholder | RegistryType | A group held by this registry. |
| CreateGroup | Method |  | Optional | RegistryType | Create a group under this registry and assign its GroupId. The server creates the GroupType Object and bootstraps its xRegistry attributes (Xid, Epoch, CreatedAt, ModifiedAt). Fails if a group with the same GroupId already exists; use GetOrCreateGroup for idempotent create-or-get. |
| GetOrCreateGroup | Method |  | Optional | RegistryType | Idempotently return the group with this GroupId, creating it if absent. One-shot form that avoids a separate existence check: returns the existing GroupType Object (Created = false) or a newly created and bootstrapped one (Created = true). |

<a id="type-GroupType"></a>

#### GroupType  (ns=1;i=63001)

*Inherits from:* [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6)

An abstract xRegistry group, expressed as a FolderType that organizes its resource files. It creates resources and versions through the CreateResource Method and is removed with its own Delete Method. Domain group types subtype this and add the group key (e.g. a namespace URI).

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| GroupId | Variable | String | Mandatory | GroupType | xRegistry groupid: the stable identifier of this group. Group identifiers are globally unique for federation. |
| Xid | Variable | String | Optional | GroupType | xRegistry relative identifier (xid): the entity's stable path within the registry, independent of the hosting endpoint. |
| Epoch | Variable | UInt32 | Optional | GroupType | xRegistry epoch: a counter that increments on every change to the entity. |
| Name | Variable | String | Optional | GroupType | Human-readable name of the entity. |
| Description | Variable | String | Optional | GroupType | Human-readable description of the entity. |
| Documentation | Variable | String | Optional | GroupType | URL to human-readable documentation for the entity. |
| Labels | Object |  | Optional | GroupType | The entity's extensible xRegistry labels/attributes, exposed as an AttributesType container: each label is a browsable PropertyType Variable, added and removed with the container's AddAttribute/RemoveAttribute Methods. Deleted together with the entity. |
| CreatedAt | Variable | DateTime | Optional | GroupType | UTC timestamp when the entity was created. |
| ModifiedAt | Variable | DateTime | Optional | GroupType | UTC timestamp when the entity was last modified. |
| <Resource> | Object |  | OptionalPlaceholder | GroupType | A resource file held by this group. |
| CreateResource | Method |  | Optional | GroupType | Create a resource, or a new version of an existing resource, as a ResourceType file in this group, optionally opened for writing. A resource version is identified by (ResourceId, VersionId): when the ResourceId is new the resource is created with this first version; when the ResourceId already exists a new sibling version is created. When VersionId is empty the server assigns the next versionid per the registry model. The server bootstraps the resource's xRegistry attributes when the file is closed. Fails with Bad_NodeIdExists if that exact (ResourceId, VersionId) already exists; use GetOrCreateResource for idempotent create-or-get. |
| GetOrCreateResource | Method |  | Optional | GroupType | Idempotently return the (ResourceId, VersionId) version, creating it if absent, optionally opened for writing. When VersionId is empty the resource's default (latest) version is returned, or - if the resource does not yet exist - created as its first version. One-shot form that avoids a separate existence check: returns the existing ResourceType file (Created = false) or a newly created one (Created = true); a write FileHandle is returned when RequestFileOpen is true. |
| Delete | Method |  | Optional | GroupType | Delete this group and everything it contains (its resources and their versions and labels). The xRegistry-semantic deletion Method, symmetric with CreateResource. If ExpectedEpoch is non-zero and does not equal the group's current Epoch, the call fails with Bad_InvalidState and deletes nothing; 0 disables the check. Success or failure is conveyed by the Method Call StatusCode. |

<a id="type-ResourceType"></a>

#### ResourceType  (ns=1;i=63002)

*Inherits from:* [FileType](https://reference.opcfoundation.org/specs/OPC-10000-20/4.2)

An abstract xRegistry resource/version whose document IS the file: the content is read and written through the inherited FileType methods (Open/Read/Write/Close). Carries the xRegistry attributes and an optional ExternalReference for federation. Domain resource types subtype this.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| ResourceId | Variable | String | Mandatory | ResourceType | xRegistry resourceid: the stable identifier of the resource within its group. |
| VersionId | Variable | String | Optional | ResourceType | xRegistry versionid: the identifier of the version this file represents. |
| Format | Variable | String | Optional | ResourceType | xRegistry format string identifying the document's schema language/shape. |
| ContentType | Variable | String | Optional | ResourceType | Media type (content-type) of the document bytes. |
| ExternalReference | Variable | [ExpandedNodeId](https://reference.opcfoundation.org/specs/OPC-10000-3/8.2.3) | Optional | ResourceType | Federation link: an ExpandedNodeId identifying this resource in another (possibly remote) registry - the ServerUri identifies the hosting registry endpoint, the NamespaceUri and Identifier identify the group and resource. Present when the document is served by reference (xRegistry <RESOURCE>url). |
| ResourceUrl | Variable | String | Optional | ResourceType | Federation link (string form): the URL from which the document can be obtained (xRegistry <RESOURCE>url), for example an opc.tcp endpoint plus browse path, or an HTTP URL. |
| Xid | Variable | String | Optional | ResourceType | xRegistry relative identifier (xid): the entity's stable path within the registry, independent of the hosting endpoint. |
| Epoch | Variable | UInt32 | Optional | ResourceType | xRegistry epoch: a counter that increments on every change to the entity. |
| Name | Variable | String | Optional | ResourceType | Human-readable name of the entity. |
| Description | Variable | String | Optional | ResourceType | Human-readable description of the entity. |
| Documentation | Variable | String | Optional | ResourceType | URL to human-readable documentation for the entity. |
| Labels | Object |  | Optional | ResourceType | The entity's extensible xRegistry labels/attributes, exposed as an AttributesType container: each label is a browsable PropertyType Variable, added and removed with the container's AddAttribute/RemoveAttribute Methods. Deleted together with the entity. |
| CreatedAt | Variable | DateTime | Optional | ResourceType | UTC timestamp when the entity was created. |
| ModifiedAt | Variable | DateTime | Optional | ResourceType | UTC timestamp when the entity was last modified. |
| Delete | Method |  | Optional | ResourceType | Delete this resource file and everything it contains (its versions and labels). The xRegistry-semantic deletion Method, symmetric with the group's Delete and consistent with the resource being a FileType. If ExpectedEpoch is non-zero and does not equal the resource's current Epoch, the call fails with Bad_InvalidState and deletes nothing; 0 disables the check. Success or failure is conveyed by the Method Call StatusCode. |

<a id="type-AttributesType"></a>

#### AttributesType  (ns=1;i=63003)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

A container for an entity's extensible xRegistry attributes/labels. Each attribute materializes as a browsable HasProperty PropertyType Variable whose BrowseName is the attribute key, so attributes can be browsed, read and enumerated, and are deleted with the owning entity. The AddAttribute/RemoveAttribute Methods add and remove attributes. This follows the OPC UA extensible-container pattern (an OptionalPlaceholder Property plus Add/Remove Methods); the placeholder isolates dynamic attributes so they never conflict with an entity's fixed attribute BrowseNames.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| <Attribute> | Variable | String | OptionalPlaceholder | AttributesType | An xRegistry attribute or label materialized as a PropertyType Variable: the BrowseName is the attribute key and the Value is its string value. OptionalPlaceholder so a server exposes one Variable per present attribute. |
| AddAttribute | Method |  | Optional | AttributesType | Add or update an xRegistry attribute/label in this container. The server materializes it as a browsable PropertyType Variable whose BrowseName is the Key, and increments the owning entity's Epoch. If ExpectedEpoch is non-zero and does not equal the owning entity's current Epoch, the call fails with Bad_InvalidState and makes no change (optimistic concurrency). Success or failure is conveyed by the Method Call StatusCode. |
| RemoveAttribute | Method |  | Optional | AttributesType | Remove an xRegistry attribute/label (the Variable whose BrowseName is the Key) from this container. If ExpectedEpoch is non-zero and does not equal the owning entity's current Epoch, the call fails with Bad_InvalidState and makes no change. Success or failure is conveyed by the Method Call StatusCode. |

### DataTypes

<a id="type-RegistryCapabilitiesDataType"></a>

#### RegistryCapabilitiesDataType  (ns=1;i=63004)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-5/8.24)

The typed form of the xRegistry capabilities document (xRegistry /capabilities), whose fields have a fixed schema in the xRegistry core specification. Read as a single Variant value from RegistryType.CapabilitiesInfo, in addition to the raw JSON exposed by the Capabilities FileType. Additional/vendor capability keys that are not among these fixed fields remain available through the Capabilities FileType JSON.

| Field | DataType | Description |
|---|---|---|
| Flags | String\[\] | The request flags the registry supports (e.g. doc, epoch, filter, inline, sort). |
| Mutable | String\[\] | Which parts of the registry are mutable (e.g. capabilities, model, entities). |
| Pagination | Boolean | Whether the registry supports pagination of collections. |
| ShortSelf | Boolean | Whether the registry offers a shortself alias for entity self URLs. |
| SpecVersions | String\[\] | The xRegistry specification versions the registry supports. |
| StickyVersions | Boolean | Whether the registry keeps the default version sticky across updates. |
| EnforceCompatibility | Boolean | Whether the registry enforces version compatibility on updates. |
| Apis | String\[\] | The additional API endpoints the registry offers (e.g. /export). |
| Schemas | String\[\] | The schema formats the registry can validate against (schema-domain registries). |

### Methods

| Method | Owning type | Input arguments | Output arguments |
|---|---|---|---|
| AddAttribute | [AttributesType](#type-AttributesType) | Key, Value, ExpectedEpoch | (none) |
| RemoveAttribute | [AttributesType](#type-AttributesType) | Key, ExpectedEpoch | (none) |
| CreateGroup | [RegistryType](#type-RegistryType) | GroupId | GroupNodeId |
| GetOrCreateGroup | [RegistryType](#type-RegistryType) | GroupId | GroupNodeId, Created |
| CreateResource | [GroupType](#type-GroupType) | ResourceId, VersionId, RequestFileOpen | ResourceNodeId, VersionId, FileHandle |
| GetOrCreateResource | [GroupType](#type-GroupType) | ResourceId, VersionId, RequestFileOpen | ResourceNodeId, VersionId, FileHandle, Created |
| Delete | [GroupType](#type-GroupType) | ExpectedEpoch | (none) |
| Delete | [ResourceType](#type-ResourceType) | ExpectedEpoch | (none) |

