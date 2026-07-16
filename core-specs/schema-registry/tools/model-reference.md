<a id="annex-a"></a>
## Annex A — Information model

This annex is the normative node reference. It is generated from `tools/build_model.py` and always matches `Opc.Ua.SchemaRegistry.NodeSet2.xml`. All nodes are proposed additions in the companion namespace `http://opcfoundation.org/UA/SchemaRegistry/` (namespace index `2` in this NodeSet, after the required `http://opcfoundation.org/UA/xRegistry/` base model at index `1`). The Schema Registry types **extend the abstract [OPC UA — xRegistry](OPC-UA-xRegistry.md) base types** (`RegistryType`/`GroupType`/`ResourceType`). The numeric NodeIds shown are **provisional** (final IDs are assigned by the OPC Foundation). The **Declared in** column marks members inherited from a supertype.

### Type overview

| NodeId | BrowseName | NodeClass | Subtype of |
|---|---|---|---|
| ns=2;i=62000 | [SchemaRegistryType](#type-SchemaRegistryType) | ObjectType | [RegistryType](OPC-UA-xRegistry.md#type-RegistryType) |
| ns=2;i=62001 | [SchemaGroupType](#type-SchemaGroupType) | ObjectType | [GroupType](OPC-UA-xRegistry.md#type-GroupType) |
| ns=2;i=62002 | [SchemaFileType](#type-SchemaFileType) | ObjectType | [ResourceType](OPC-UA-xRegistry.md#type-ResourceType) |

### Object types

<a id="type-SchemaRegistryType"></a>
#### SchemaRegistryType  (ns=2;i=62000)

*Inherits from:* [RegistryType](OPC-UA-xRegistry.md#type-RegistryType)

The in-server Schema Registry root - an xRegistry RegistryType (a FolderType) whose group folders hold schema files. Adds SchemaId-based resolution (GetSchema and the Opaque SchemaId NodeId fast path). Exposed as a well-known object under the Part 14 PublishSubscribe object.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| <SchemaGroup> | Object |  | OptionalPlaceholder | SchemaRegistryType | A schema group folder (per OPC UA namespace) held by the registry. |
| GetSchema | Method |  | Optional | SchemaRegistryType | Return the schema document and metadata for a raw on-wire SchemaId fingerprint (the method form of the Opaque SchemaId NodeId fast path). |

<a id="type-SchemaGroupType"></a>
#### SchemaGroupType  (ns=2;i=62001)

*Inherits from:* [GroupType](OPC-UA-xRegistry.md#type-GroupType)

An xRegistry GroupType keyed by an OPC UA namespace URI; a folder of schema files for the DataTypes and PublishedDataSets of that namespace.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| NamespaceUri | Variable | String | Mandatory | SchemaGroupType | The OPC UA namespace URI represented by this schema group (the xRegistry group key). |
| <Schema> | Object |  | OptionalPlaceholder | SchemaGroupType | A schema file (one DataType/DataSet in one format) held by this group. |

<a id="type-SchemaFileType"></a>
#### SchemaFileType  (ns=2;i=62002)

*Inherits from:* [ResourceType](OPC-UA-xRegistry.md#type-ResourceType)

An xRegistry ResourceType whose file content is one concrete schema document (Avro, Apache Arrow or JSON Schema). Adds the OPC UA schema-decoding metadata (SchemaId and per-encoding fields) used by a consumer that must resolve a schema from an on-wire fingerprint.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| SchemaId | Variable | ByteString | Mandatory | SchemaFileType | Raw on-wire SchemaId fingerprint bytes. The schema file is additionally addressable by an Opaque NodeId whose identifier bytes are exactly this value. |
| SchemaIdAlg | Variable | String | Mandatory | SchemaFileType | SchemaId algorithm name, such as CRC-64-AVRO or SHA-256. |
| DataTypeEncoding | Variable | String | Optional | SchemaFileType | The OPC UA DataTypeEncoding name, for example Default Avro or Default Arrow. |
| ModelVersion | Variable | String | Optional | SchemaFileType | OPC UA NodeSet model version label (opcua.modelversion). |
| ConfigurationVersion | Variable | [ConfigurationVersionDataType](https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.2.6) | Optional | SchemaFileType | PubSub ConfigurationVersion (opcua.configurationversion) when the schema describes a DataSet. |
| ExpiryTime | Variable | DateTime | Optional | SchemaFileType | Optional UTC expiry time for mirror/cache mode. |
| Ttl | Variable | Duration | Optional | SchemaFileType | Optional time-to-live for mirror/cache mode. |

### Methods

| Method | Owning type | Input arguments | Output arguments |
|---|---|---|---|
| GetSchema | [SchemaRegistryType](#type-SchemaRegistryType) | SchemaId | Document, Format, ContentType, Found |

### Well-known instances

| BrowseName | NodeId | TypeDefinition | Note |
|---|---|---|---|
| SchemaRegistry | ns=2;i=62100 | [SchemaRegistryType](#type-SchemaRegistryType) | Server-wide in-server Schema Registry, discoverable from the PublishSubscribe object. |

