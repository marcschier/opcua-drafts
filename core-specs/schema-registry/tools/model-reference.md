<a id="annex-a"></a>
## Annex A — Information model

This annex is the normative node reference. It is generated from `tools/build_model.py` and always matches `Opc.Ua.SchemaRegistry.NodeSet2.xml`. All nodes are proposed additions in the companion namespace `http://opcfoundation.org/UA/SchemaRegistry/`; the numeric NodeIds shown are **provisional** (final IDs are assigned by the OPC Foundation). The **Declared in** column marks members inherited from a supertype.

### Type overview

| NodeId | BrowseName | NodeClass | Subtype of |
|---|---|---|---|
| ns=1;i=62000 | [SchemaRegistryType](#type-SchemaRegistryType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| ns=1;i=62001 | [SchemaGroupType](#type-SchemaGroupType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| ns=1;i=62002 | [SchemaType](#type-SchemaType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| ns=1;i=62003 | [SchemaVersionType](#type-SchemaVersionType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| ns=1;i=62004 | [SchemaNamespacesType](#type-SchemaNamespacesType) | ObjectType | [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6) |

### Object types

<a id="type-SchemaRegistryType"></a>
#### SchemaRegistryType  (ns=1;i=62000)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

The in-server registry root, isomorphic to an xRegistry Schema Registry document. It exposes schema groups and methods for SchemaId-based resolution.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Namespaces | Object |  | Mandatory | SchemaRegistryType | Container for SchemaGroup objects, equivalent to xRegistry schemagroups. |
| <SchemaGroup> | Object |  | OptionalPlaceholder | SchemaRegistryType | A SchemaGroup directly below the registry when a server chooses not to use the Namespaces folder. |
| GetSchema | Method |  | Optional | SchemaRegistryType | Return the schema document and metadata for a raw on-wire SchemaId fingerprint. |
| RegisterSchema | Method |  | Optional | SchemaRegistryType | Optional authoritative population method used by server configuration or writers, not by read-only consumers. |

<a id="type-SchemaGroupType"></a>
#### SchemaGroupType  (ns=1;i=62001)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

An xRegistry schemagroup, keyed by an OPC UA namespace URI and containing schemas for DataTypes or PublishedDataSets in that namespace.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| NamespaceUri | Variable | String | Mandatory | SchemaGroupType | The OPC UA namespace URI represented by this schemagroup. |
| <Schema> | Object |  | OptionalPlaceholder | SchemaGroupType | A schema Resource for one DataType or PublishedDataSet and one format. |

<a id="type-SchemaType"></a>
#### SchemaType  (ns=1;i=62002)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

An xRegistry schema Resource for one DataType or PublishedDataSet in one schema format.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| BrowseName | Variable | String | Mandatory | SchemaType | The OPC UA BrowseName or PublishedDataSet name represented by this schema Resource. |
| Format | Variable | String | Mandatory | SchemaType | The xRegistry schema format, for example Avro/1.11 or ApacheArrow/1.0. |
| DataTypeEncoding | Variable | String | Optional | SchemaType | The OPC UA DataTypeEncoding name, for example Default Avro or Default Arrow. |
| <Version> | Object |  | OptionalPlaceholder | SchemaType | One concrete schema document Version. |

<a id="type-SchemaVersionType"></a>
#### SchemaVersionType  (ns=1;i=62003)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

An xRegistry schema Version: one concrete schema document plus labels used for OPC UA schema-based decoding.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Document | Variable | ByteString | Mandatory | SchemaVersionType | The schema document bytes. In instances this Variable should be assigned the Opaque SchemaId NodeId for direct Read access. |
| Format | Variable | String | Mandatory | SchemaVersionType | The xRegistry format string copied onto the Version. |
| ContentType | Variable | String | Mandatory | SchemaVersionType | The media type of the schema document. |
| SchemaId | Variable | ByteString | Mandatory | SchemaVersionType | Raw on-wire SchemaId fingerprint bytes. |
| SchemaIdAlg | Variable | String | Mandatory | SchemaVersionType | SchemaId algorithm name, such as CRC-64-AVRO or SHA-256. |
| ModelVersion | Variable | String | Optional | SchemaVersionType | OPC UA NodeSet model version label opcua.modelversion. |
| ConfigurationVersion | Variable | [ConfigurationVersionDataType](https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.2.6) | Optional | SchemaVersionType | PubSub ConfigurationVersion label opcua.configurationversion when the schema describes a DataSet. |
| ExpiryTime | Variable | DateTime | Optional | SchemaVersionType | Optional UTC expiry time for mirror/cache mode. |
| Ttl | Variable | Duration | Optional | SchemaVersionType | Optional time-to-live in milliseconds for mirror/cache mode. |

<a id="type-SchemaNamespacesType"></a>
#### SchemaNamespacesType  (ns=1;i=62004)

*Inherits from:* [FolderType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.6)

The registry's schemagroups container. Its children are SchemaGroupType instances keyed by OPC UA namespace URI.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| <SchemaGroup> | Object |  | OptionalPlaceholder | SchemaNamespacesType | A SchemaGroup held by the Namespaces container. |

### Methods

| Method | Owning type | Input arguments | Output arguments |
|---|---|---|---|
| GetSchema | [SchemaRegistryType](#type-SchemaRegistryType) | SchemaId | Document, Format, ContentType, Found |
| RegisterSchema | [SchemaRegistryType](#type-SchemaRegistryType) | NamespaceUri, BrowseName, Format, ContentType, Document, SchemaId, SchemaIdAlg, ModelVersion, ConfigurationVersion | VersionNodeId, DocumentNodeId, Registered |

### Well-known instances

| BrowseName | NodeId | TypeDefinition | Note |
|---|---|---|---|
| SchemaRegistry | ns=1;i=62100 | [SchemaRegistryType](#type-SchemaRegistryType) | Server-wide in-server Schema Registry, discoverable from the PublishSubscribe object. |
| Namespaces | ns=1;i=62101 | [SchemaNamespacesType](#type-SchemaNamespacesType) | Container for namespace schema groups. |

