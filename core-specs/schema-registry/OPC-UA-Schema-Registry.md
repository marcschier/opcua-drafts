# OPC UA — In-server Schema Registry

**Working draft for submission to the OPC Foundation Working Group**
**Proposed Part: OPC 10000-2xx (number to be assigned)**
**Companion namespace:** `http://opcfoundation.org/UA/SchemaRegistry/`
**Version:** 0.1.0 · **Date:** 2026-07-04

> **Status — working draft.** This document defines an in-server Schema Registry information model for OPC UA. The model is intentionally isomorphic to the xRegistry Schema Registry model (`registry` → `schemagroups` → `schemas` → `versions`) so the same subtree can be projected by OPC UA REST as an xRegistry-compatible JSON document. It also defines a fast SchemaId NodeId resolution path for schema-based PubSub and service encodings. Nothing here is normative or endorsed by the OPC Foundation.

---

## 1 Scope

Schema-based encodings such as Avro, Protobuf and Apache Arrow require a decoder to obtain the concrete schema document that matches the received payload. The sibling xRegistry Schema Catalog draft defines an out-of-band registry and catalog format for disconnected consumers. This specification defines the in-server AddressSpace projection of the same model so an OPC UA Client can resolve schemas directly from the Server that publishes or owns them.

The model has three goals:

- expose an xRegistry-isomorphic tree under the Part 14 `PublishSubscribe` object so OPC UA Browse, Read and REST can represent the same registry, schemagroups, schemas and versions;
- allow a decoder that has only the on-wire `SchemaId` bytes to perform a single Read by an Opaque NodeId and obtain the schema document without browsing, searching labels or recomputing a fingerprint;
- keep this service parallel to the Security Key Service and other PubSub services rather than folding schema resolution into `GetSecurityKeys`.

This companion namespace does not define a new transport. OPC UA Client/Server services and OPC UA REST expose the same AddressSpace; the JSON mapping clause in §7 specifies the representation of this AddressSpace as an xRegistry-compatible document.

## 2 Normative references

- OPC 10000-3 — Address Space Model, NodeIds, References and TypeDefinitions.
- OPC 10000-5 — Base Information Model, FolderType, PropertyType and method Argument metadata.
- OPC 10000-14 — PubSub, including the well-known `PublishSubscribe` object (`i=14443`), `ConfigurationVersionDataType` and Security Key Service relationship.
- OPC UA Avro Message Mapping draft §9 — SchemaId handshake and decoder cache-miss behavior.
- OPC UA Arrow Message Mapping draft §5.2 — SchemaId handshake and cache-miss behavior.
- OPC UA xRegistry Schema Catalog draft — out-of-band Schema Registry mapping, `opcua.*` labels and §6 resolution flow.
- xRegistry Schema Registry Service — `registry`, `schemagroups`, `schemas`, `versions`, `format`, `schemaurl` and inline schema carriers.

## 3 Terms, definitions and abbreviations

| Term | Definition |
|---|---|
| Schema Registry | The in-server registry root, equivalent to an xRegistry `registry` document. |
| Schema Group | A group for one OPC UA namespace URI, equivalent to an xRegistry `schemagroup`. |
| Schema | One DataType or PublishedDataSet in one schema format, equivalent to an xRegistry `schema` Resource. |
| Schema Version | One concrete schema document, equivalent to an xRegistry schema `version`. |
| SchemaId | Raw on-wire schema fingerprint bytes defined by the encoding mapping, for example the 8-byte CRC-64-AVRO fingerprint or the 8-byte truncated SHA-256 fingerprint (a profile may specify a longer length). |
| SchemaId NodeId | An Opaque NodeId in the Schema Registry namespace whose Identifier bytes are exactly the raw SchemaId bytes. |

Key words **shall**, **should** and **may** are interpreted as in ISO/IEC directives / RFC 2119.

## 4 Information model

The companion namespace is `http://opcfoundation.org/UA/SchemaRegistry/`. Draft numeric NodeIds use the provisional `62000+` block in this namespace; final NodeIds are assigned by the OPC Foundation.

A Server exposes one well-known `SchemaRegistry` Object as a `HasComponent` of the Part 14 `PublishSubscribe` Object (`i=14443`). This mirrors the discoverability pattern used by PubSub services: a Client that can discover PubSub configuration can discover schema resolution in the same place. The well-known instance is parallel to Security Key Service and scenario binding services.

### 4.1 SchemaRegistryType

`SchemaRegistryType` is the registry root and corresponds to the xRegistry `registry` document. It has a Mandatory `Namespaces` container of `SchemaNamespacesType` for groups and an OptionalPlaceholder `<SchemaGroup>` for Servers that expose groups directly below the registry. It has the `GetSchema` Method and may have the `RegisterSchema` Method.

### 4.1.1 SchemaNamespacesType

`SchemaNamespacesType` is the `Namespaces` / `schemagroups` container. Its `<SchemaGroup>` OptionalPlaceholder declares that children of the container are `SchemaGroupType` instances.

### 4.2 SchemaGroupType

`SchemaGroupType` corresponds to an xRegistry `schemagroup`. Each instance is keyed by the namespace URI. Its Mandatory `NamespaceUri` Property stores the exact OPC UA namespace URI; the BrowseName of the instance may be a server-chosen URL-safe key. The `<Schema>` OptionalPlaceholder contains `SchemaType` instances.

### 4.3 SchemaType

`SchemaType` corresponds to an xRegistry `schema` Resource. It represents one `(DataType or PublishedDataSet) × format` pair. The `BrowseName` Property stores the OPC UA BrowseName or PublishedDataSet name, `Format` stores the xRegistry format string, and `DataTypeEncoding` stores the related OPC UA DataTypeEncoding name such as `Default Avro`, `Default Arrow` or `Default Protobuf` when applicable. The `<Version>` OptionalPlaceholder contains `SchemaVersionType` instances.

### 4.4 SchemaVersionType

`SchemaVersionType` corresponds to one xRegistry schema `version`. `Document` is a Mandatory ByteString Property containing the schema document bytes. `Format`, `ContentType`, `SchemaId` and `SchemaIdAlg` are Mandatory Properties. `ModelVersion`, `ConfigurationVersion`, `ExpiryTime` and `Ttl` are Optional Properties.

For a PubSub DataSet schema, `ConfigurationVersion` is the Part 14 `ConfigurationVersionDataType`. For schemas not tied to a DataSet, `ConfigurationVersion` is omitted. `ModelVersion` records the originating NodeSet model version when known.

## 5 SchemaId-NodeId fast access

Each schema Version document shall be additionally addressable by an Opaque NodeId in the Schema Registry namespace. The deterministic construction is:

```
NamespaceIndex = namespace index assigned to http://opcfoundation.org/UA/SchemaRegistry/
IdentifierType = Opaque
Identifier = the exact raw on-wire SchemaId bytes
```

The node addressed by this Opaque NodeId is the Version's `Document` Variable, or an equivalent ByteString Variable that has the same Value and is linked to the Version. A Client that receives a schema-based message and finds a cache miss constructs this NodeId from the received SchemaId bytes and performs one `Read` of the Value Attribute. If the node exists, the returned ByteString is the schema document. No Browse, label search, fingerprint recomputation or schema regeneration is required.

The Identifier is not a stringified hex label. It is the raw byte sequence used on the wire: 8 bytes for Avro CRC-64-AVRO fingerprints, 8 bytes for Arrow's truncated SHA-256 fingerprint (or the length a profile specifies), and any other length defined by an encoding mapping. Opaque NodeIds allow arbitrary byte lengths.

The SchemaId NodeId is content-derived and stable. A TTL refresh, mirror refetch or metadata update that does not change the schema document keeps the same SchemaId NodeId. A changed schema document produces a new SchemaId and therefore a new Opaque NodeId.

## 6 Methods

### 6.1 GetSchema

`GetSchema(SchemaId: ByteString) → (Document: ByteString, Format: String, ContentType: String, Found: Boolean)` resolves the raw on-wire SchemaId bytes and returns the schema document and enough metadata to parse it. It is the method form of the cache-miss path used by decoders that cannot or do not want to construct an Opaque NodeId. `Found=false` indicates that no Version with this SchemaId is registered.

### 6.2 RegisterSchema

`RegisterSchema(...)` is optional. It is intended for server configuration, writers or administrative tools that authoritatively populate the registry. Read-only consumers do not need it. Servers may instead populate the registry from configuration files, PubSub DataSet metadata, generated NodeSets or a mirrored external xRegistry.

## 7 xRegistry REST/JSON mapping

The AddressSpace subtree rooted at `SchemaRegistry` maps directly to the xRegistry Schema Registry JSON shape. This is a mapping clause for OPC UA REST and JSON export of the AddressSpace; it is not a new transport.

| OPC UA node | xRegistry JSON member |
|---|---|
| `SchemaRegistry` | registry document root |
| `Namespaces` / `SchemaGroupType` children | `schemagroups` map |
| `SchemaGroupType.NamespaceUri` | group `labels["opcua.namespaceuri"]` |
| `SchemaType` children | group `schemas` map |
| `SchemaType.BrowseName` | schema `name` and `labels["opcua.browsename"]` |
| `SchemaType.Format` | schema `format` |
| `SchemaType.DataTypeEncoding` | schema `labels["opcua.datatypeencoding"]` |
| `SchemaVersionType` children | schema `versions` map |
| `SchemaVersionType.Document` | inline `schema` bytes or `schemabase64`, depending on REST representation and content type |
| `SchemaVersionType.ContentType` | version `contenttype` |
| `SchemaVersionType.SchemaId` | version `labels["opcua.schemaid"]` as lower-case hex |
| `SchemaVersionType.SchemaIdAlg` | version `labels["opcua.schemaid.alg"]` |
| `SchemaVersionType.ModelVersion` | version `labels["opcua.modelversion"]` |
| `SchemaVersionType.ConfigurationVersion` | version `labels["opcua.configurationversion"]` as `major.minor` |

An OPC UA REST GET of the `SchemaRegistry` subtree should therefore be serializable as an xRegistry-compatible document. Conversely, an imported xRegistry Schema Registry document can be projected into these ObjectTypes without loss of the OPC UA labels needed by the Part 14 resolution flow.

## 8 TTL and mirror semantics

A Server is authoritative by default. In authoritative mode, schema Versions do not expire and `ExpiryTime` and `Ttl` are omitted.

A Server may operate as a TTL-cached mirror in front of an external xRegistry. In mirror mode, `Ttl` records the configured time-to-live and `ExpiryTime` records the current expiry timestamp. On cache miss or expired lookup the Server may refetch from the external registry, update metadata and refresh `Document`. The SchemaId NodeId remains stable across a refresh as long as the fetched document has the same SchemaId. If the external document changes, the SchemaId changes and a different Opaque NodeId is used for the new Version.

## 9 Relationship to SKS and Part 14 PubSub

The Schema Registry is a well-known PubSub-adjacent service under `PublishSubscribe`, parallel to the Security Key Service described by Part 14 §8. It may be co-located, co-configured and co-secured with the Security Key Service because both are used by subscribers during PubSub setup or recovery. It shall not be folded into `GetSecurityKeys`: keys and schema documents have different lifetimes, access control policies, payload shapes and cache semantics.

A PubSub decoder follows the Avro §9 or Arrow §5.2 cache-miss flow. If the message carries a SchemaId and the decoder cache does not contain it, the decoder first attempts the Opaque NodeId Read or calls `GetSchema`. If neither succeeds, it may fall back to an announcement frame, an external xRegistry lookup, or AddressSpace schema regeneration as defined by the encoding mapping.

## 10 Relationship to the out-of-band xRegistry catalog

The xRegistry Schema Catalog companion draft defines the disconnected and out-of-band view: registry → schemagroups → schemas → versions plus `opcua.*` labels. This specification defines the in-server AddressSpace projection/cache of that same information model and the §6 in-server resolution path. The two models are intentionally isomorphic so tooling can export from a Server to xRegistry, import from xRegistry to a Server, or use OPC UA REST to obtain the same JSON structure.

## 11 NodeSet validation

The NodeSet, CSV and Annex A are generated from `tools/build_model.py`. The local validator checks XML well-formedness, unique NodeIds, CSV ↔ NodeSet consistency, that the well-known `SchemaRegistry` instance is attached to `PublishSubscribe` (`i=14443`), and that base/Part 14 NodeId references are resolvable when local reference tables are available.

---

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
| DataTypeEncoding | Variable | String | Optional | SchemaType | The OPC UA DataTypeEncoding name, for example Default Avro, Default Arrow or Default Protobuf. |
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

