<a id="annex-a"></a>
## Annex A — Information model

This annex is the normative node reference. It is generated from `tools/build_model.py` and always matches `Opc.Ua.XRegistry.NodeSet2.xml`. All nodes are defined in the companion namespace `http://opcfoundation.org/UA/xRegistry/` (which requires the base OPC UA namespace); the numeric NodeIds shown are **draft** identifiers within that namespace. The **Declared in** column marks members inherited from a supertype.

### Type overview

| NodeId | BrowseName | NodeClass | Subtype of |
|---|---|---|---|
| ns=1;i=63000 | [RegistryType](#type-RegistryType) | ObjectType | [FileDirectoryType](https://reference.opcfoundation.org/specs/OPC-10000-20/4.3.1) |
| ns=1;i=63001 | [GroupType](#type-GroupType) | ObjectType | [FileDirectoryType](https://reference.opcfoundation.org/specs/OPC-10000-20/4.3.1) |
| ns=1;i=63002 | [ResourceType](#type-ResourceType) | ObjectType | [FileType](https://reference.opcfoundation.org/specs/OPC-10000-20/4.2) |

### Object types

<a id="type-RegistryType"></a>
#### RegistryType  (ns=1;i=63000)

*Inherits from:* [FileDirectoryType](https://reference.opcfoundation.org/specs/OPC-10000-20/4.3.1)

The abstract xRegistry root, expressed as a FileDirectory. It contains Group directories and supports creating and managing them through the CreateGroup Method (and the inherited FileDirectoryType Delete/MoveOrCopy Methods). Domain registries subtype this.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| RegistryId | Variable | String | Mandatory | RegistryType | xRegistry registryid: the stable identifier of this registry. |
| SpecVersion | Variable | String | Optional | RegistryType | The xRegistry specification version this registry conforms to. |
| Capabilities | Variable | String | Optional | RegistryType | The registry capabilities document (xRegistry /capabilities), as a JSON string. |
| Model | Variable | String | Optional | RegistryType | The registry model document (xRegistry /model), as a JSON string. |
| Xid | Variable | String | Optional | RegistryType | xRegistry relative identifier (xid): the entity's stable path within the registry, independent of the hosting endpoint. |
| Epoch | Variable | UInt32 | Optional | RegistryType | xRegistry epoch: a counter that increments on every change to the entity. |
| Name | Variable | String | Optional | RegistryType | Human-readable name of the entity. |
| Description | Variable | String | Optional | RegistryType | Human-readable description of the entity. |
| Documentation | Variable | String | Optional | RegistryType | URL to human-readable documentation for the entity. |
| Labels | Variable | [KeyValuePair](https://reference.opcfoundation.org/specs/OPC-10000-5/12.23)\[\] | Optional | RegistryType | xRegistry labels: an extensible map of name/value pairs, managed by AddAttribute/RemoveAttribute on resources. |
| CreatedAt | Variable | DateTime | Optional | RegistryType | UTC timestamp when the entity was created. |
| ModifiedAt | Variable | DateTime | Optional | RegistryType | UTC timestamp when the entity was last modified. |
| <Group> | Object |  | OptionalPlaceholder | RegistryType | A group directory held by this registry. |
| CreateGroup | Method |  | Optional | RegistryType | Create a group directory under this registry and assign its GroupId. This is the xRegistry-semantic form of the inherited FileDirectoryType CreateDirectory Method; the server bootstraps the new group's xRegistry attributes (Xid, Epoch, CreatedAt, ModifiedAt). |

<a id="type-GroupType"></a>
#### GroupType  (ns=1;i=63001)

*Inherits from:* [FileDirectoryType](https://reference.opcfoundation.org/specs/OPC-10000-20/4.3.1)

An abstract xRegistry group, expressed as a FileDirectory that contains resources. It creates resources and versions through the CreateResourceOrVersion Method. Domain group types subtype this and add the group key (e.g. a namespace URI).

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| GroupId | Variable | String | Mandatory | GroupType | xRegistry groupid: the stable identifier of this group. Group identifiers are globally unique for federation. |
| Xid | Variable | String | Optional | GroupType | xRegistry relative identifier (xid): the entity's stable path within the registry, independent of the hosting endpoint. |
| Epoch | Variable | UInt32 | Optional | GroupType | xRegistry epoch: a counter that increments on every change to the entity. |
| Name | Variable | String | Optional | GroupType | Human-readable name of the entity. |
| Description | Variable | String | Optional | GroupType | Human-readable description of the entity. |
| Documentation | Variable | String | Optional | GroupType | URL to human-readable documentation for the entity. |
| Labels | Variable | [KeyValuePair](https://reference.opcfoundation.org/specs/OPC-10000-5/12.23)\[\] | Optional | GroupType | xRegistry labels: an extensible map of name/value pairs, managed by AddAttribute/RemoveAttribute on resources. |
| CreatedAt | Variable | DateTime | Optional | GroupType | UTC timestamp when the entity was created. |
| ModifiedAt | Variable | DateTime | Optional | GroupType | UTC timestamp when the entity was last modified. |
| <Resource> | Object |  | OptionalPlaceholder | GroupType | A resource file held by this group. |
| CreateResourceOrVersion | Method |  | Optional | GroupType | Create a resource - or a new version of a resource - as a file in this group, optionally opened for writing. This is the xRegistry-semantic form of the inherited FileDirectoryType CreateFile Method; the server bootstraps the resource's xRegistry attributes when the file is closed. |

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
| Labels | Variable | [KeyValuePair](https://reference.opcfoundation.org/specs/OPC-10000-5/12.23)\[\] | Optional | ResourceType | xRegistry labels: an extensible map of name/value pairs, managed by AddAttribute/RemoveAttribute on resources. |
| CreatedAt | Variable | DateTime | Optional | ResourceType | UTC timestamp when the entity was created. |
| ModifiedAt | Variable | DateTime | Optional | ResourceType | UTC timestamp when the entity was last modified. |
| AddAttribute | Method |  | Optional | ResourceType | Add or update an xRegistry attribute (or label) on this resource, further configuring the registry structure. The server materializes the attribute in the AddressSpace. |
| RemoveAttribute | Method |  | Optional | ResourceType | Remove an xRegistry attribute (or label) from this resource. |

### Methods

| Method | Owning type | Input arguments | Output arguments |
|---|---|---|---|
| CreateGroup | [RegistryType](#type-RegistryType) | GroupId | GroupNodeId |
| CreateResourceOrVersion | [GroupType](#type-GroupType) | ResourceId, RequestFileOpen | ResourceNodeId, FileHandle |
| AddAttribute | [ResourceType](#type-ResourceType) | Key, Value | Success |
| RemoveAttribute | [ResourceType](#type-ResourceType) | Key | Success |

