# xRegistry — OPC UA API

**Working draft for submission to the OPC Foundation Working Group and the xRegistry organization**
**Proposed Part: OPC 10000-2xx (number to be assigned)**
**Companion namespace:** `http://opcfoundation.org/UA/xRegistry/`
**Version:** 0.1.0 · **Date:** 2026-07-16
**Target:** xRegistry submission as `core/opcua.md`, or an xRegistry extension proposal.

> **Status — working draft.** This document defines the self-contained OPC UA API binding of the xRegistry core model, using the OPC UA FileTransfer-based information model defined by [*OPC UA — xRegistry*](OPC-UA-xRegistry.md). It is a first-class peer of the xRegistry HTTP binding, not a derivation from it, so xRegistry registries can be discovered, read, created, updated, deleted, exported and federated natively through OPC UA AddressSpace nodes, Services and FileTransfer Methods.

---

## 1 Scope

This specification defines the OPC UA API binding for [xRegistry](https://github.com/xregistry/spec): how a registry, its groups, resources, versions, documents and attributes are discovered, read, created, updated and deleted natively over OPC UA Services while realizing the xRegistry core model on the OPC UA AddressSpace and FileTransfer model of [*OPC UA — xRegistry*](OPC-UA-xRegistry.md).

The abstract information model is defined by [*OPC UA — xRegistry*](OPC-UA-xRegistry.md): a registry is a `RegistryType` directory, each group is a `GroupType` directory, and each resource or resource version document is a `ResourceType` file. This API specifies how clients interact with those nodes using Browse, BrowseNext, Read, Write, Call, Query, TranslateBrowsePathsToNodeIds and the inherited FileTransfer Methods.

This binding stands on its own and does not depend on any particular transport binding. The xRegistry HTTP binding and this OPC UA binding are peer protocol bindings of the same xRegistry core model; Annex A provides an informative correspondence for readers familiar with the HTTP binding, while §9 describes federation, including references to registries hosted behind an HTTP API.

This binding is independent of any domain registry. A concrete companion specification subtypes `RegistryType`, `GroupType` and `ResourceType`, constrains group and resource names, and may add domain Properties or Methods; the OPC UA API patterns in this document remain the same.

## 2 Normative references

- [xRegistry Core specification, v1.0-rc3](https://github.com/xregistry/spec/blob/v1.0-rc3/core/spec.md) — the registry, group, resource, version, document, attribute, request-flag, operation-processing and error model.
- [xRegistry primer, v1.0-rc3](https://github.com/xregistry/spec/blob/v1.0-rc3/core/primer.md) — the xRegistry concepts, representations, request-shaping concepts and federation model.
- [OPC UA — xRegistry](OPC-UA-xRegistry.md) — the OPC UA companion information model used by this API.
- [OPC 10000-3](https://reference.opcfoundation.org/specs/OPC-10000-3/) — Address Space Model, including NodeIds, References, TypeDefinitions and `ExpandedNodeId`.
- [OPC 10000-4](https://reference.opcfoundation.org/specs/OPC-10000-4/) — Services, including Browse, BrowseNext, Read, Write, Call, Query, TranslateBrowsePathsToNodeIds and StatusCodes.
- [OPC 10000-5](https://reference.opcfoundation.org/specs/OPC-10000-5/) — Base Information Model, including `PropertyType` and `KeyValuePair`.
- [OPC 10000-20](https://reference.opcfoundation.org/specs/OPC-10000-20/) — File Transfer, including `FileType`, `FileDirectoryType` and their Methods.

Informative reference:

- [xRegistry HTTP binding, v1.0-rc3](https://github.com/xregistry/spec/blob/v1.0-rc3/core/http.md) — sibling protocol binding used only for the correspondence table in Annex A.

## 3 Terms and conventions

Key words **shall**, **should**, **may**, **shall not** and **should not** are interpreted as described in the ISO/IEC directives and RFC 2119.

The xRegistry terms registry, group, resource, version, document, attributes, collection, `xid`, `self`, `epoch`, `labels`, model, capabilities, request flags, representation and federation have the meanings defined by the xRegistry core specification and primer. In this document, an `xid` is the xRegistry relative identifier of an entity within a registry, for example `/schemagroups/g1/schemas/s1`; it is not a protocol URL and is resolved against the selected `RegistryType` root.

OPC UA type and member names are written exactly as defined by [*OPC UA — xRegistry*](OPC-UA-xRegistry.md) Annex A and the corresponding NodeSet: `RegistryType`, `GroupType`, `ResourceType`, `RegistryId`, `SpecVersion`, `Capabilities`, `Model`, `GroupId`, `ResourceId`, `VersionId`, `Format`, `ContentType`, `ExternalReference`, `ResourceUrl`, `Xid`, `Epoch`, `Name`, `Description`, `Documentation`, `Labels`, `CreatedAt`, `ModifiedAt`, `AddAttribute` and `RemoveAttribute`.

The OPC UA Services used by this API are Browse for collection enumeration, BrowseNext for continuation points, Read for Properties and node metadata, Write for writable Properties, Call for FileTransfer and xRegistry property Methods, Query for server-side filtering where supported, TranslateBrowsePathsToNodeIds for path resolution, and the FileTransfer Methods inherited from `FileType` and `FileDirectoryType`.

In pseudo-signatures, FileTransfer Methods are shown by their BrowseNames rather than by numeric NodeIds because a concrete server may expose them on domain subtypes of `RegistryType`, `GroupType` or `ResourceType`.

## 4 The OPC UA API access model

### 4.1 AddressSpace root and service model

An OPC UA xRegistry API is an AddressSpace subtree rooted at a selected `RegistryType` or domain subtype instance. Each registry root represents one xRegistry registry; each `GroupType` child represents a group; each `ResourceType` child represents a resource or resource version whose document bytes are obtained through `FileType` Methods; and xRegistry attributes are OPC UA Properties on those Objects.

A server may expose more than one registry. A client selects the registry root by NodeId, BrowsePath, discovery metadata or domain convention before applying this API.

The selected registry root is the API authority for the operation sequence. No URL authority is involved in the native OPC UA API; entity identity is carried by xRegistry identifier Properties and `Xid`, while the OPC UA session, endpoint and NodeIds identify where those entities are currently served.

The baseline operation model is: Browse a directory to enumerate a collection, Read Properties to obtain attributes, Write writable Properties to change mutable attributes, Call `Open`/`Read`/`Write`/`Close` to read or replace document bytes, Call `CreateGroup`/`CreateResourceOrVersion` (and the inherited `Delete`/`MoveOrCopy`) to manage lifecycle, Call `AddAttribute`/`RemoveAttribute` for supported resource extension attributes or labels, and use Query where the server advertises server-side filtering or ordering.

If an optional xRegistry function is not supported for an otherwise supported node, the server shall return `Bad_NotSupported`, `Bad_UserAccessDenied`, `Bad_NotWritable`, `Bad_MethodInvalid` or `Bad_InvalidArgument` as appropriate. If the requested node or Property cannot be resolved, the server shall return an appropriate StatusCode such as `Bad_NodeIdUnknown`, `Bad_BrowseNameInvalid` or `Bad_NotFound` where available.

### 4.2 Resolving xRegistry `xid`s to OPC UA nodes

The following table defines the native addressing model from xRegistry `xid` or relative identifier forms to OPC UA targets. The left column is xRegistry identity notation from the core model, not a protocol path; clients resolve it by Browse, TranslateBrowsePathsToNodeIds, identifier-Property matching and model metadata starting at the selected `RegistryType` root.

| xRegistry `xid` / relative identifier | OPC UA target | Primary OPC UA operation |
|---|---|---|
| `/` | selected `RegistryType` root node | Read registry Properties and Browse group children |
| `/capabilities` | `RegistryType.Capabilities` Property | Read or Write the JSON string Property when supported |
| `/capabilitiesoffered` | offered-capabilities structure exposed by the server, if any | Read a domain Property or an offered section inside `Capabilities` |
| `/model` | `RegistryType.Model` Property | Read the JSON string Property |
| `/modelsource` | server-specific model-source Property or operation, if exposed | Read or Write the domain-defined model-source target, or reject as unsupported |
| `/export` | selected `RegistryType` subtree serialized as an xRegistry document | Browse and Read the subtree, or use a domain export Method or Property if advertised |
| `/<GROUPS>` | collection of `GroupType` children under the registry whose collection name is `<GROUPS>` | Browse, Query and optionally `CreateGroup` on the registry |
| `/<GROUPS>/<GID>` | `GroupType` child whose `GroupId` is `<GID>` | Read/Write Properties, Browse resources, delete through the parent directory |
| `/<GROUPS>/<GID>/<RESOURCES>` | collection of `ResourceType` children under the group whose collection name is `<RESOURCES>` | Browse, Query and optionally `CreateResourceOrVersion` on the group |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>` | default `ResourceType` for `ResourceId = <RID>` | `Open`/`Read` document bytes or Read metadata Properties |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>$details` | same `ResourceType`, metadata view | Read/Write Properties and optionally `AddAttribute`/`RemoveAttribute` |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/meta` | metadata Properties of the resource and default-version selection state | Read/Write Properties; domain extensions may add meta Properties |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions` | set of `ResourceType` files with matching `ResourceId` and distinct `VersionId` | Browse or Query associated version files |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>` | `ResourceType` whose `ResourceId = <RID>` and `VersionId = <VID>` | `Open`/`Read` document bytes or Read metadata Properties |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>$details` | same version file, metadata view | Read/Write Properties and optionally `AddAttribute`/`RemoveAttribute` |

The collection names `<GROUPS>` and `<RESOURCES>` are xRegistry model names, not mandatory OPC UA base nodes. A domain registry may express collection names through subtype BrowseNames, domain Properties, folders or model metadata, but each concrete group instance shall be a `GroupType` or subtype and each concrete resource or version instance shall be a `ResourceType` or subtype.

When a relative identifier segment is an entity identifier such as `<GID>`, `<RID>` or `<VID>`, the definitive match is the corresponding `GroupId`, `ResourceId` or `VersionId` Property. BrowseName equality is a useful optimization but is not the normative identity test unless the domain specification constrains BrowseNames to equal identifiers.

The xRegistry `self` value is not a mandatory OPC UA Property in the base model. In this API it is derived from the selected registry root and the entity's `Xid`; an OPC UA client can reconstruct a canonical self reference as a registry root NodeId plus the relative `Xid`, or as an implementation-defined URL or URN for display.

### 4.3 Entity processing rules

Reading a collection is Browse or Query over the corresponding directory. Reading an entity metadata view is Read of the entity Properties. Reading a resource or version document is `Open`/`Read`/`Close` on the `ResourceType` file.

Full replacement of an entity targets the entity node or the parent directory from which the entity can be created. If the entity does not exist, the server creates a `GroupType` directory or `ResourceType` file; if it exists, the server updates it. Mutable Properties omitted from the replacement representation shall be deleted, reset to default or left unchanged only where the xRegistry core rules or server-managed semantics require that behavior.

Partial update of an entity changes only explicitly named mutable attributes and removes explicitly null attributes where removal is supported. It is realized by Write of writable Properties, by `AddAttribute(Key, Value) -> Success` and `RemoveAttribute(Key) -> Success` on `ResourceType` where extension attributes or labels are involved, and by domain-defined writable Properties or Methods for registry or group extension attributes. Partial update shall not patch arbitrary bytes inside a resource document; document content changes use complete replacement of the document byte stream.

Collection processing creates or updates one or more child entities under the collection's parent directory. A client creates groups with `CreateGroup` on `RegistryType` and resources or versions with `CreateResourceOrVersion` on `GroupType`; after creation it writes mandatory and mutable Properties and writes document bytes where supplied. A server shall apply the xRegistry atomicity rule: if one entity in a collection operation cannot be processed, the server should reject the whole operation and avoid partial effects; if the server cannot guarantee multi-node atomicity, it shall advertise that limitation in `Capabilities`.

Nested collection processing on an entity shall process only nested collection entries and shall not modify the owning entity's own Properties. For example, processing resources under a selected group creates or updates `ResourceType` children without changing the group's own Properties.

Deleting an entity is the inherited `Delete(objectToDelete)` Method on the parent `FileDirectoryType`, targeting the child directory or file to remove. Deleting a collection subset is a batch of `Delete` calls over selected children.

Unless otherwise stated, a request to update a read-only Property shall be ignored only if xRegistry says that read-only attribute updates are ignored; otherwise the server shall reject the Write with `Bad_NotWritable` or `Bad_UserAccessDenied`. A request that supplies an identifier Property (`RegistryId`, `GroupId`, `ResourceId` or `VersionId`) whose value conflicts with the target entity shall fail with `Bad_InvalidArgument` or `Bad_IdentityChangeNotSupported`.

Any successful create or update shall update `ModifiedAt` and increment `Epoch` on the modified entity. Creation shall initialize `CreatedAt`, `ModifiedAt`, `Epoch`, `Xid` and the appropriate identifier Properties according to [*OPC UA — xRegistry*](OPC-UA-xRegistry.md) §6.5 and the xRegistry core rules.

### 4.4 OPC UA-specific attribute processing

OPC UA carries metadata as typed Property Values. Strings are OPC UA `String`, timestamps are `DateTime`, `Labels` is `KeyValuePair[]`, `ExternalReference` is `ExpandedNodeId`, and `Epoch` is `UInt32`.

When a resource document is read as bytes, accompanying metadata is obtained by separate Read operations on the same `ResourceType` Properties. A server may optimize this by returning metadata in the same Service response when using Query or by exposing a domain Method, but the interoperable baseline is separate `Open`/`Read`/`Close` plus Read Properties.

The metadata view of a resource or version is represented by choosing Property Reads or Writes instead of file content Reads or Writes. The target NodeId is the same `ResourceType`; only the operation mode differs.

The xRegistry `contenttype` attribute maps to `ContentType`, not to `MimeType`. `MimeType` is inherited from `FileType` and may mirror `ContentType` for generic FileTransfer clients; when both are present, `ContentType` is the xRegistry attribute and `MimeType` is the FileTransfer media hint.

### 4.5 Method signatures and argument mapping

The creation and mutation Method signatures used by this API are the domain-named `CreateGroup`, `CreateResourceOrVersion`, `AddAttribute` and `RemoveAttribute` Methods defined by the xRegistry base model, together with the inherited `Open` / `Read` / `Write` / `Close` / `Delete` / `MoveOrCopy` Methods whose exact argument definitions are normative in OPC 10000-20.

| xRegistry action | OPC UA Method or Service | Argument mapping |
|---|---|---|
| Create group | `RegistryType.CreateGroup(GroupId) -> (GroupNodeId)` | `GroupId` is the groupid of the `GroupType` (or subtype) to create; the server creates the group directory and bootstraps its xRegistry attributes |
| Create resource or version | `GroupType.CreateResourceOrVersion(ResourceId, RequestFileOpen) -> (ResourceNodeId, FileHandle)` | `ResourceId` identifies the `ResourceType` (or subtype); `RequestFileOpen = true` returns a write `FileHandle` when document bytes follow |
| Delete group/resource/version | parent `FileDirectoryType.Delete(objectToDelete)` | `objectToDelete` is the child `NodeId` resolved from the xRegistry `xid` or identifier Properties |
| Move or copy entity | parent `FileDirectoryType.MoveOrCopy(objectToMoveOrCopy, targetDirectory, createCopy, newName)` | xRegistry identity Properties shall be updated or validated according to whether the operation is a move or copy |
| Read document | `ResourceType.Open(mode)` -> `Read(fileHandle, length)` -> `Close(fileHandle)` | `mode` is read-only; `length` and repeated Reads are bounded by `Size` |
| Replace document | `ResourceType.Open(mode)` -> `SetPosition(fileHandle, 0)` -> `Write(fileHandle, data)` -> `Close(fileHandle)` | `mode` allows write; the complete replacement byte stream is written; server updates `ModifiedAt` and `Epoch` |
| Read metadata | Read Service on Properties | Property BrowseNames map to xRegistry attribute names by the tables in this document and the domain model |
| Replace scalar metadata | Write Service on Properties | Value DataTypes are those in Annex A of the base model |
| Add/update resource extension attribute or label | `ResourceType.AddAttribute(Key: String, Value: String) -> (Success: Boolean)` | `Key` is the xRegistry attribute or label key; `Value` is the canonical string representation |
| Remove resource extension attribute or label | `ResourceType.RemoveAttribute(Key: String) -> (Success: Boolean)` | `Key` is the xRegistry attribute or label key; `Success = true` indicates the effective absence of the attribute |

The base NodeSet defines `CreateGroup` on `RegistryType`, `CreateResourceOrVersion` on `GroupType`, and `AddAttribute` / `RemoveAttribute` on `ResourceType`. These are the xRegistry-semantic forms of the inherited FileDirectory `CreateDirectory` / `CreateFile` and of an attribute `PATCH`; a generic FileTransfer client may still use the inherited `CreateDirectory` / `CreateFile` directly. Registry-level or group-level mutable extension attributes are represented as writable Properties on the relevant domain subtype or by domain-defined Methods.

### 4.5.1 Concurrency and locking (optional)

FileTransfer itself provides the baseline concurrency control: `ResourceType.Open` opens a resource document for exclusive write (a second write-`Open` returns `Bad_NotWritable`, and a read-`Open` returns `Bad_NotReadable` while the file is open for writing), so document replacement is already serialized per file. Optimistic concurrency across metadata is provided by the xRegistry `Epoch`: a client Reads `Epoch`, and a server that supports the `epoch` precondition rejects a stale Write or Delete with `Bad_InvalidState` (§6, §10).

Beyond this, a server **may** optionally expose coarser-grained exclusive access using the standard OPC UA locking mechanism — a `LockingServicesType` component (`InitLock` / `RenewLock` / `ExitLock` / `BreakLock`, OPC 10000-5) — on the registry root, a group or a resource, so that a client can hold an explicit exclusive lock across a multi-step create/update sequence. This API does not require locking; when it is absent, clients rely on FileTransfer `Open` exclusivity and `Epoch` preconditions.

### 4.6 Attribute-to-Property mapping

The base model Properties map to xRegistry attributes as follows.

| xRegistry attribute | OPC UA Property | Applies to |
|---|---|---|
| `registryid` | `RegistryId` | `RegistryType` |
| `specversion` | `SpecVersion` | `RegistryType` |
| `capabilities` | `Capabilities` | `RegistryType` |
| `model` | `Model` | `RegistryType` |
| `<GROUP>id` | `GroupId` | `GroupType` |
| `<RESOURCE>id` | `ResourceId` | `ResourceType` |
| `versionid` | `VersionId` | `ResourceType` |
| `format` | `Format` | `ResourceType` |
| `contenttype` | `ContentType` | `ResourceType` |
| `<RESOURCE>url` | `ResourceUrl` | `ResourceType` |
| federation target | `ExternalReference` | `ResourceType` |
| `xid` | `Xid` | all base entity types |
| `epoch` | `Epoch` | all base entity types |
| `name` | `Name` | all base entity types |
| `description` | `Description` | all base entity types |
| `documentation` | `Documentation` | all base entity types |
| `labels` | `Labels` | all base entity types |
| `createdat` | `CreatedAt` | all base entity types |
| `modifiedat` | `ModifiedAt` | all base entity types |

The xRegistry attributes `self`, collection `url` attributes, collection `count` attributes, `metaurl`, `versionsurl`, `versionscount`, `defaultversionurl`, `isdefault`, `ancestor`, `<RESOURCE>` and `<RESOURCE>base64` are serialization artifacts or domain/model attributes rather than mandatory base Properties. A server may expose them as domain Properties, but a client shall be able to derive them from `Xid`, `ResourceId`, `VersionId`, Browse results and the document bytes where possible.

### 4.7 Supported operations discovery and pagination

A client discovers supported operations by browsing the target node for Methods, by reading `Writable`, `UserWritable`, AccessLevel and UserAccessLevel attributes of Variables, by reading `Capabilities`, and by inspecting executable and user-executable bits of Method nodes.

A server shall not require a side-effecting operation for discovery. If a FileTransfer Method or `AddAttribute`/`RemoveAttribute` is absent, non-executable or rejected with `Bad_UserAccessDenied`, the corresponding xRegistry write capability is not available to that client.

OPC UA Browse paginates large child sets through continuation points and `BrowseNext`. A client that wants a page of collection entries calls Browse with a requested maximum reference count and then calls `BrowseNext` until the desired page is complete or no continuation point remains.

For file bytes, a client paginates through `Read(fileHandle, length)` and may use `GetPosition` and `SetPosition` to implement random access. For arrays such as `Labels`, a client may use the Read Service `IndexRange` parameter where supported.

## 5 Registry operations

This section defines successful native OPC UA interaction patterns for xRegistry entities. Error mapping is specified in §10.

### 5.1 Reading the registry

A client reads the selected `RegistryType` root by Reading its Properties and Browsing its group children. The standard base Properties are `RegistryId`, `SpecVersion`, `Capabilities`, `Model`, `Xid`, `Epoch`, `Name`, `Description`, `Documentation`, `Labels`, `CreatedAt` and `ModifiedAt` where present.

A serialized registry representation derives collection URL and count attributes from the registry model and Browse results rather than from mandatory OPC UA nodes. Domain group subtypes and the `Model` Property determine how browsed groups are grouped into xRegistry collections.

### 5.2 Creating and updating the registry

A registry-level full replacement writes the full replacement set of mutable `RegistryType` Properties; omitted mutable attributes are removed or reset according to xRegistry rules. `Capabilities` and `Model` are special: absence shall not require a change, while presence shall be treated as a complete replacement unless the server supports finer-grained update semantics.

A registry-level partial update writes only included Properties. A null attribute is represented by writing a server-defined null/default value if the DataType permits it, by deleting a domain extension Property if supported, or by failing with `Bad_NotSupported` if the attribute is mandatory or cannot be removed.

The base `RegistryType` does not define `AddAttribute` or `RemoveAttribute`; registry extension attributes shall therefore be modeled as writable Properties on a domain subtype or managed by a domain-defined Method.

When a registry-level operation includes nested group collections, each group entry is resolved by `GroupId`; if absent, the server creates a `GroupType` or domain subtype instance using `CreateGroup(GroupId)` on the registry root, initializes `GroupId`, `Xid`, `Epoch`, `CreatedAt` and `ModifiedAt`, and applies the supplied group Properties and nested resource collections.

When the requested operation is explicitly limited to group collection processing, registry-level attributes shall be rejected with `Bad_InvalidArgument`, corresponding to xRegistry `groups_only`.

### 5.3 Exporting the registry

Export is serialization of the selected `RegistryType` subtree into the xRegistry JSON document shape. The interoperable baseline export algorithm is Browse the registry subtree, Read all mapped Properties, Open/Read/Close each inlined `ResourceType` document, and serialize the result according to §8.

A server may expose an optimized domain Method or Property for export, but such an optimization shall produce the same document shape as the baseline algorithm. Import is an implementation capability expressed as normal create/update operations or by a domain-defined import Method.

### 5.4 Reading capabilities and model documents

A client reads registry capabilities by Reading `RegistryType.Capabilities`. The Property value is a JSON string containing the xRegistry capabilities map, including any OPC UA binding features the server supports, such as create, update, delete, query, filter, inline, export, versioning, federation, writable model and multi-operation atomicity.

The base information model does not define a separate `CapabilitiesOffered` Property. If a server supports mutable capabilities, it shall expose the offered-capabilities information either inside the `Capabilities` JSON, as a domain subtype Property, or through domain documentation referenced by `Model`. If no offered-capabilities target is exposed, the operation shall fail with `Bad_NodeIdUnknown` or `Bad_NotSupported` rather than inventing an unmapped base node.

A client reads the registry model by Reading `RegistryType.Model`. The Property value is a JSON string containing the full xRegistry model definition, and clients may use it to resolve domain collection names to `GroupType` and `ResourceType` subtype BrowseNames before browsing entities.

The base information model does not define a distinct `ModelSource` Property. If a server distinguishes the effective model from the client-provided model source, it shall expose the model source as a domain subtype Property or inside the `Model` JSON using a documented shape. If the model source has never been set and a model-source target exists, the server shall return an empty JSON object (`{}`) as a string value, matching xRegistry semantics.

### 5.5 Updating capabilities and model-source information

Capabilities updates are Write operations on `RegistryType.Capabilities` if the Property is writable for the current user. A full replacement writes the complete capabilities JSON; a partial capabilities update writes only top-level capabilities if the server supports patch-level semantics, otherwise the client shall perform read-modify-write and the server may reject partial Writes with `Bad_NotSupported`.

Unsupported capability changes shall fail with `Bad_InvalidArgument` or `Bad_NotSupported`, and no capability change shall take effect before the current Service operation completes.

Model-source updates are Write operations on the domain-defined model-source Property or another domain-defined operation. The abstract base API does not define a writable `ModelSource` node. If a server supports model-source updates via `RegistryType.Model`, it shall document that `Model` is serving as model source and shall apply the xRegistry full-replacement rules; if the server exposes only effective `Model`, attempts to write model source shall fail with `Bad_NotWritable` or `Bad_NotSupported`.

### 5.6 Listing group collections

A client lists a group collection by Browse or Query over the selected `RegistryType` root to return `GroupType` children that belong to the requested group collection.

The client filters Browse results by TypeDefinition (`GroupType` or subtype), by collection metadata in `Model`, by domain subtype, and finally by `GroupId` when an identifier is needed. The serialized collection keys are the `GroupId` values, not necessarily BrowseNames.

### 5.7 Creating and updating groups

A client creates or updates groups as `GroupType` children under the registry root. For each group key, the client resolves an existing group by `GroupId`; if absent and creation is allowed, it calls `CreateGroup(GroupId)` on the `RegistryType` root. It then writes group Properties according to the requested processing mode: partial updates write only named attributes, while full representations reset or remove omitted mutable attributes according to xRegistry rules.

The response representation is obtained by reading back only the groups processed, not the entire group collection.

If a group does not exist and the operation permits creation, the server creates it with `CreateGroup` on the registry root. The supplied group identifier shall match `GroupId`; a mismatch fails with `Bad_InvalidArgument`.

Processing nested resource collections under a group creates or updates resource collections under the specified group without modifying the group's own Properties. The request representation is a map from resource collection names to resource maps; for each resource entry, the client calls `CreateResourceOrVersion` if needed, writes the document if supplied, and writes resource Properties according to the nested operation semantics.

If an operation attempts to update group-level attributes while it is explicitly limited to nested resource collection processing, the server shall reject it with `Bad_InvalidArgument`, corresponding to xRegistry `resources_only`.

### 5.8 Reading a group

A client reads a group by resolving the `GroupType` child whose `GroupId` equals the requested group identifier, then Reading its Properties and Browsing its resource children as needed.

The standard base Properties are `GroupId`, `Xid`, `Epoch`, `Name`, `Description`, `Documentation`, `Labels`, `CreatedAt` and `ModifiedAt`. Domain group subtypes may add mandatory group-key Properties and extension metadata.

### 5.9 Deleting groups

Deleting a selected group is `Delete(objectToDelete)` on the parent `RegistryType`, where `objectToDelete` is the resolved group NodeId. Deleting a collection subset is a batch of `Delete(objectToDelete)` calls on the registry root, one for each selected group child.

If an entity-specific `epoch` precondition is supplied, the client or server shall Read `Epoch` before deletion and fail the operation with `Bad_InvalidState` if the value does not match. If a server cannot perform the check and delete atomically, it shall either reject the preconditioned delete or advertise the limitation in `Capabilities`.

### 5.10 Resource metadata and resource documents

The xRegistry distinction between resource metadata and resource document is made by the operation selected on the same `ResourceType` node. To access the document, a client uses the inherited `FileType` Methods on `ResourceType`: `Open`, `Read`, optionally `GetPosition` and `SetPosition`, `Write` when replacing the document, and `Close`.

To access metadata, a client uses Read or Write on `ResourceType` Properties: `ResourceId`, `VersionId`, `Format`, `ContentType`, `ExternalReference`, `ResourceUrl`, `Xid`, `Epoch`, `Name`, `Description`, `Documentation`, `Labels`, `CreatedAt` and `ModifiedAt`, plus domain Properties.

If a resource type's xRegistry model has `hasdocument = false`, document access shall be rejected with `Bad_NotReadable`, `Bad_InvalidState` or `Bad_NotSupported`, and metadata access remains the normal entity representation.

When a resource or version is serialized as its domain-specific document, the bytes returned by `Read(fileHandle, length)` are the exact document bytes. If the document is empty, `Read` returns zero bytes at end-of-file.

OPC UA has no need for transport headers to carry resource metadata. Clients obtain the metadata by reading the Properties of the file before or after reading bytes. Servers should keep `ContentType` and the inherited `MimeType` consistent so generic FileTransfer clients can identify the media type.

If `ResourceUrl` is present and the document is external, `Open` may fail with `Bad_NotReadable` or may return a local cached representation. In either case the client can read `ResourceUrl` and `ExternalReference` to resolve the external content as described in §9.

### 5.11 Listing resource collections

A client lists a resource collection by Browse or Query over the `GroupType` directory to return `ResourceType` children in the requested resource collection.

The serialized collection keys are `ResourceId` values. The default version of each resource is represented by the `ResourceType` selected by the server as the default for that `ResourceId`; in a flat implementation with one file per resource, that file's `VersionId` is the default version.

A client derives `versionscount` by querying or browsing all files associated with the same `ResourceId`, and derives `metaurl` and `versionsurl` from `Xid`.

### 5.12 Creating and updating resources

A client creates or updates resources as `ResourceType` children under the group. For each resource key, the client resolves an existing default resource by `ResourceId`; if absent and creation is allowed, it calls `CreateResourceOrVersion(ResourceId, RequestFileOpen)` on the `GroupType`. If `RequestFileOpen = true`, the returned file handle may be used immediately to write the document bytes.

For metadata-only updates, the client writes Properties and optionally calls `AddAttribute`/`RemoveAttribute` for resource extension attributes or labels. For document creation or replacement, the client writes the complete document byte stream and sets `ContentType`, `Format`, `ResourceUrl` and `ExternalReference` as applicable.

If the supplied `ResourceId` conflicts with the selected resource identifier, the operation shall fail with `Bad_InvalidArgument`. If supplied `VersionId` creates a new version rather than replacing the default version, the operation shall follow §5.17.

### 5.13 Reading a resource document

A client reads the default resource document by resolving the default `ResourceType` for the selected `ResourceId`, calling `Open` for read, repeatedly calling `Read`, and calling `Close`. The client may read `Size`, `Writable`, `MimeType`, `LastModifiedTime`, `ContentType`, `ResourceId`, `VersionId`, `Xid` and `Epoch` to reproduce the full xRegistry response metadata.

If `ResourceUrl` or `ExternalReference` indicates external content, the server may either redirect by metadata by returning readable `ResourceUrl`/`ExternalReference` while `Open` fails with a suitable StatusCode, or serve cached bytes from the local file. The choice shall be documented in `Capabilities`.

### 5.14 Reading and updating resource metadata

A client reads resource metadata by Reading the default resource file's Properties without reading file bytes. A client updates metadata by Writing the default `ResourceType` Properties, optionally combined with `AddAttribute` and `RemoveAttribute` for resource extension attributes and labels.

The resource-level meta view is a serialization view over Properties of the resource and, where present, domain-defined Properties. The base model does not define a separate `Meta` Object.

Base Properties such as `Epoch`, `CreatedAt` and `ModifiedAt` are normally server-managed and shall not be directly writable unless the server explicitly allows administrative writes.

Changing default-version state is domain-defined because the base model only defines `VersionId` on `ResourceType`; a server that supports the xRegistry `defaultversionid` meta attribute shall expose a writable domain Property or Method for that state.

Deleting the meta view is not supported. The server shall reject attempts to delete the meta view with `Bad_NotSupported` or `Bad_InvalidArgument`. Individual mutable meta attributes may be reset through update processing if the domain model supports them.

### 5.15 Replacing a resource document

Replacing a resource document is create-if-needed plus complete file replacement. If the resource file does not exist, the client calls `CreateResourceOrVersion` on the parent group. It then opens the file for writing, sets position to zero where needed, writes the complete new byte stream, closes the file, and writes or validates metadata Properties.

Partial patching of document bytes is not defined. A client that wants to change document content shall provide a complete replacement document.

### 5.16 Deleting resources

Deleting a selected resource is deletion of the default resource entity or all version files associated with the selected `ResourceId`, depending on the server's version representation and xRegistry model configuration. Deleting a resource collection subset is a batch of `Delete(objectToDelete)` calls on the parent `GroupType`, one for each selected `ResourceType` or resource-version set.

If the implementation represents multiple versions as sibling files, deleting a resource collection entry shall delete all version files for the selected `ResourceId` unless the request specifically targets a version entity.

A server shall not leave dangling version files that remain discoverable as the same resource unless the domain model explicitly supports detached historic versions. If deletion of a default resource is disallowed while versions exist, the server shall return `Bad_InvalidState` or `Bad_NotSupported`.

### 5.17 Listing versions

A client lists versions by Browse or Query for all `ResourceType` files associated with the selected `ResourceId` and a non-empty `VersionId` under the owning `GroupType`.

An implementation may represent the default version as the same file reached by the resource identity and additional versions as sibling files, or it may expose only one version if it does not support version history. The serialized version collection keys are `VersionId` values.

### 5.18 Creating and updating versions

A client creates or updates a version by resolving a `ResourceType` with the selected `ResourceId` and `VersionId`; if absent and creation is allowed, it calls `CreateResourceOrVersion` on the group with a filename or BrowseName derived from the resource identifier and the new `VersionId`.

For partial metadata updates, only named version attributes are written. For full version representations, omitted mutable attributes are reset or removed according to xRegistry rules. Extension attributes and labels on `ResourceType` may be managed through `AddAttribute` and `RemoveAttribute` where supported.

For document-bearing versions, the client writes the version document if supplied and writes `ResourceId` and the new `VersionId`. The server updates default-version state according to xRegistry rules and domain model capabilities.

If an empty version map is supplied for a non-existent resource, the server shall reject it with `Bad_InvalidArgument`, corresponding to xRegistry `missing_versions`.

The response representation is obtained by reading back the created or updated version file's Properties and, for document mode, by reading back its file bytes if needed.

### 5.19 Reading a version

A client reads a version document with `Open`/`Read`/`Close` on the `ResourceType` whose `ResourceId` is the selected resource identifier and whose `VersionId` is the selected version identifier.

A client reads version metadata by Reading that version file's Properties. The `Xid` Property should identify the version path when the server materializes versions as separate entities.

### 5.20 Replacing a version document

Replacing a version document is create-if-needed plus complete replacement of the version file bytes using `CreateResourceOrVersion`, `Open`, `SetPosition`, `Write` and `Close`.

Partial patching of version document bytes is not defined.

### 5.21 Deleting versions

Deleting a selected version is `Delete(objectToDelete)` on the parent `GroupType`, targeting the resolved version file. Deleting a versions collection subset is a batch of `Delete` calls on the parent `GroupType`, targeting the version files selected by `VersionId`.

A server shall reject deletion of the last required version of a resource if the xRegistry model requires every resource to have at least one version. A server shall also reject deletion of a default version unless it can atomically select a new default or the request explicitly sets one through a supported flag or meta update.

If the version is the default version, the server shall either reject the delete with `Bad_InvalidState` or update default-version state according to xRegistry and domain rules.

## 6 Request flags

The xRegistry core request flags defined by the xRegistry core specification and primer are protocol-independent processing and representation controls. In OPC UA they are represented by operation choice, service parameters, Query clauses, continuation points, Read `IndexRange`, Write options or server capabilities rather than by transport-specific query parameters.

Unknown or unsupported flags should be ignored when xRegistry defines them as response-shaping hints, and shall be rejected with `Bad_NotSupported` or `Bad_InvalidArgument` when they are required for safe write semantics.

| xRegistry flag | OPC UA realization |
|---|---|
| `inline` | Browse and Read the named child collections or Properties in the same client operation sequence; a server-side Query or domain export may inline server-side |
| `filter` | OPC UA Query Service where supported; otherwise client-side filtering after Browse and Read |
| `sort` | Query ordering where supported; otherwise client-side ordering of Browse/Read results |
| pagination | Browse continuation points, `BrowseNext`, file `Read` length, and Read `IndexRange` |
| `doc` | Serialize using document shape, omitting redundant URL/count metadata as defined by xRegistry |
| `meta` | Read metadata Properties rather than document bytes; equivalent to metadata operation mode for resources and versions |
| `export` | Serialize the selected subtree as an xRegistry document |
| `epoch` | Read-and-compare `Epoch` before Write/Delete; server should perform atomically when advertised |
| `ignore` | Server-side write processing option advertised in `Capabilities`; unsupported ignore values fail with `Bad_InvalidArgument` |
| `setdefaultversionid` | Domain-defined default-version update, normally a meta Property or Method |
| `specversion` | Compare requested version against `SpecVersion` and `Capabilities`; reject incompatible processing with `Bad_InvalidArgument` |
| `binary` | Prefer raw `Open`/`Read` bytes for documents; metadata remains OPC UA typed Properties |
| `collections` | Include or omit collection members by Browse depth and serialization rules |

### 6.1 Filtering

A server may support the `filter` flag through the OPC UA Query Service. The queried node set is the collection directory, the type filter is `GroupType` or `ResourceType` or a domain subtype, and filter operands reference Properties such as `GroupId`, `ResourceId`, `VersionId`, `Name`, `Labels`, `CreatedAt`, `ModifiedAt` or domain Properties.

If Query is not supported, a client may implement the same semantics by Browse of the collection, Read of Properties for candidate entities, and local evaluation of the xRegistry filter expressions. Such client-side filtering is interoperable but may be less efficient.

### 6.2 Ignore processing

The `ignore` flag affects write processing. In OPC UA, ignore behavior is advertised in `Capabilities` and applied by the server while processing Write, Call and FileTransfer operations.

Because standard OPC UA Write and Call requests do not carry arbitrary xRegistry option maps, a generic client that needs `ignore` semantics shall either use a server-defined operation that accepts write options, or shall pre-process the representation and omit ignored attributes before issuing standard Writes and Calls. Unsupported ignore requirements shall fail with `Bad_NotSupported` or `Bad_InvalidArgument`.

### 6.3 Inlining

The `inline` flag maps to Browse depth and Property/document retrieval. `inline=*` means the client recursively browses the selected subtree, reads each entity's Properties, and reads document bytes where the document shape requires them.

Inlining `capabilities` and `model` means reading `Capabilities` and `Model` on the registry root. Inlining nested collections means browsing `GroupType` and `ResourceType` children and serializing them into the parent entity representation.

### 6.4 Sorting

A server may implement sorting with Query. If it does not, clients sort the collection entries after reading the Properties used as sort keys.

Browse order alone shall not be assumed to be xRegistry sort order unless the server explicitly documents that behavior in `Capabilities`.

### 6.5 Document and metadata modes

The `doc` flag selects xRegistry document serialization and normally causes derived URL/count attributes to be omitted where the xRegistry document shape omits them. In OPC UA this is a serialization mode, not a different node.

The `meta` flag selects Property access for resources and versions. A client shall not attempt byte-level partial update of a document by selecting metadata mode; metadata and document bytes are separate operation modes on the same `ResourceType`.

### 6.6 Pagination and ranges

Collection pagination maps to Browse continuation points. Document range retrieval maps to the `length` argument of `Read`, to repeated reads from the current file position, and to `SetPosition` for random access. Array slicing maps to the Read Service `IndexRange` parameter for array-valued Properties such as `Labels`.

Continuation points are session-scoped OPC UA state and are not serializable as stable xRegistry identifiers. A protocol bridge may translate between another binding's pagination tokens and OPC UA continuation points internally.

## 7 Value encoding

OPC UA uses typed Values and StatusCodes rather than transport headers and JSON envelopes for every operation. JSON appears in this binding only where xRegistry defines a JSON document attribute, namely `Capabilities`, `Model`, possible model-source or export payloads, and resource documents whose domain media type is JSON.

Strings shall be encoded as OPC UA `String`, timestamps as `DateTime`, integer epochs as `UInt32`, labels as `KeyValuePair[]`, federation targets as `ExpandedNodeId`, and document bytes as `ByteString` chunks returned by `Read` on `FileType`.

When a complete xRegistry entity is serialized for export or for a protocol bridge, the base Property BrowseNames are converted to their xRegistry lower-case attribute names. Domain Properties are serialized according to the domain registry model.

A server shall preserve unknown extension attributes that it accepts, using domain extension Properties, `Labels`, or `AddAttribute`/`RemoveAttribute` on `ResourceType` as applicable. If the server cannot preserve an accepted extension attribute, it shall reject the update rather than silently losing information.

## 8 Serialization / export-import

The document representation defined by xRegistry is produced from the OPC UA AddressSpace by walking the selected subtree and converting nodes and Properties to the xRegistry JSON entity shape.

For a `RegistryType`, serialization reads registry Properties, emits `registryid`, `specversion`, common attributes and any requested `capabilities` and `model` payloads, then serializes group collections by browsing `GroupType` children and grouping them by the xRegistry model's collection names.

For a `GroupType`, serialization reads `GroupId` and common Properties, emits the domain group identifier attribute, and serializes resource collections by browsing `ResourceType` children and grouping them by domain resource collection names.

For a `ResourceType`, metadata serialization reads `ResourceId`, `VersionId`, `Format`, `ContentType`, `ExternalReference`, `ResourceUrl` and common Properties. Document serialization reads the file bytes with FileTransfer and places them in the xRegistry `<RESOURCE>` or `<RESOURCE>base64` attribute according to the xRegistry document rules and the selected encoding.

The inverse import process creates or updates the same subtree: create group directories, create resource/version files, write document bytes, write mapped Properties, and let the server auto-bootstrap `Xid`, `Epoch`, `CreatedAt` and `ModifiedAt` where they are not explicitly supplied or are server-managed.

Serialization shall preserve the three-representation symmetry described by the xRegistry primer and by [*OPC UA — xRegistry*](OPC-UA-xRegistry.md) §4.2 and §7: an entity has the same `Xid` and identity whether reached as a file, through OPC UA services, or in an exported xRegistry document.

## 9 Federation

Federation is realized by `ExternalReference` and `ResourceUrl` on `ResourceType`, as defined by the xRegistry primer, xRegistry core specification, and [*OPC UA — xRegistry*](OPC-UA-xRegistry.md) §8 and Annex B.

`ExternalReference` is an `ExpandedNodeId`. Its `ServerUri` identifies the remote OPC UA server that hosts the referenced registry, and its `NamespaceUri` plus identifier identify the remote resource node independently of the server's local namespace indexes.

`ResourceUrl` is the xRegistry `<RESOURCE>url` string. It may contain an OPC UA endpoint/browse-path convention for another OPC UA registry, or an HTTP URL for a registry hosted behind the xRegistry HTTP API or another non-OPC-UA registry API.

To resolve a federated OPC UA resource, a client reads `ExternalReference`; if `ServerUri` is local or empty it resolves the target in the local AddressSpace, otherwise it discovers or connects to the remote endpoint, maps the `NamespaceUri` to the remote namespace index, resolves the target NodeId or BrowsePath, and reads the remote `ResourceType` using the same FileTransfer operations as for a local file.

To resolve a resource federated to an HTTP-API-hosted registry, a client or gateway uses `ResourceUrl` as the external locator and treats the remote bytes and metadata as the representation of the same xRegistry resource identity carried by `Xid`, `ResourceId` and `VersionId`. The HTTP authority identifies the serving endpoint, not the resource identity.

A server may expose a local proxy `ResourceType` for a federated resource. Such a proxy shall retain the remote resource identity in `Xid`, `ResourceId` and `VersionId`, and shall not treat the local endpoint identity as part of the resource identity.

## 10 Error handling

OPC UA errors are returned as StatusCodes on Service results, Operation results, Method Call results, or individual input/output argument diagnostics. When an xRegistry error includes structured details, a server should include additional diagnostic information in the OPC UA DiagnosticInfo or in a domain-specific error payload where available.

The following mapping is normative unless a more specific OPC UA StatusCode applies.

| xRegistry error condition | OPC UA StatusCode |
|---|---|
| API function or entity target not supported (`api_not_found`) | `Bad_NodeIdUnknown`, `Bad_BrowseNameInvalid` or `Bad_NotSupported` |
| action not supported for an existing node | `Bad_NotSupported` or `Bad_MethodInvalid` |
| entity not found | `Bad_NodeIdUnknown` or `Bad_NotFound` where available |
| method target not found | `Bad_MethodInvalid` |
| invalid relative identifier segment or malformed identifier | `Bad_BrowseNameInvalid` or `Bad_InvalidArgument` |
| required attribute missing | `Bad_InvalidArgument` |
| invalid attribute value | `Bad_InvalidArgument`, `Bad_TypeMismatch` or `Bad_OutOfRange` |
| mismatched `RegistryId`, `GroupId`, `ResourceId` or `VersionId` | `Bad_InvalidArgument` or `Bad_IdentityChangeNotSupported` |
| already exists | `Bad_BrowseNameDuplicated` or `Bad_NodeIdExists` |
| not writable or read-only attribute | `Bad_NotWritable` or `Bad_UserAccessDenied` |
| resource document not readable | `Bad_NotReadable` or `Bad_InvalidState` |
| missing body or missing document bytes | `Bad_InvalidArgument` |
| unsupported metadata mode | `Bad_NotSupported` or `Bad_InvalidArgument` |
| partial update attempted on document bytes | `Bad_NotSupported` |
| unsupported flag or ignore value | `Bad_NotSupported` or `Bad_InvalidArgument` |
| `epoch` precondition failed | `Bad_InvalidState` |
| delete would violate version/default-version constraints | `Bad_InvalidState` |
| query/filter not supported | `Bad_QueryTooComplex`, `Bad_FilterNotAllowed` or `Bad_NotSupported` |
| continuation point invalid or expired | `Bad_ContinuationPointInvalid` |
| file handle invalid | `Bad_InvalidArgument` or the FileTransfer-defined invalid-handle StatusCode |
| file is locked or concurrently modified | `Bad_InvalidState` or `Bad_ResourceUnavailable` |
| external federation target cannot be resolved | `Bad_NotFound`, `Bad_CommunicationError` or `Bad_ServerUriInvalid` |
| server cannot preserve accepted extension attribute | `Bad_NotSupported` |
| operation exceeds server limits | `Bad_TooManyOperations`, `Bad_EncodingLimitsExceeded` or `Bad_OutOfMemory` |

A batch operation shall report failure in a way that lets the client identify the failing entity. If the operation is represented as multiple OPC UA Service calls, the failing call's StatusCode and diagnostics identify the entity. If a server exposes a domain batch Method, each entity result should carry its own StatusCode and the Method result shall indicate whether any partial effects occurred.

Authorization failures shall use `Bad_UserAccessDenied` or `Bad_SecurityChecksFailed`. Authentication and secure-channel failures are governed by OPC 10000-4 and are not redefined by this binding.

## 11 Conformance

A server conforms to the read-only OPC UA xRegistry API if it exposes a `RegistryType` root or domain subtype, exposes groups as `GroupType` or subtypes, exposes resource/version documents as `ResourceType` or subtypes, and supports Browse, Read and `Open`/`Read`/`Close` sufficient to retrieve registry metadata, collections and resource documents.

A server conforms to the writable OPC UA xRegistry API if, in addition to read-only conformance, it supports the applicable FileTransfer creation and mutation Methods (`CreateGroup`, `CreateResourceOrVersion`, `Delete`, optionally `MoveOrCopy`), writable Properties, and `AddAttribute`/`RemoveAttribute` on `ResourceType` where resource extension attributes or labels are mutable.

A server conforms to the query/export OPC UA xRegistry API if it implements the request-flag mappings it advertises in `Capabilities`, including Browse continuation point pagination, Query or equivalent filtering where advertised, and export serialization that follows the xRegistry document shape.

A client conforms if it can select a `RegistryType` root, resolve xRegistry `xid`s or relative identifiers to AddressSpace nodes, use Browse/Read/FileTransfer operations for reading, use Write/Call operations for advertised write capabilities, interpret StatusCodes according to §10, and serialize or consume xRegistry document representations according to §8.

A conforming implementation shall not require any node or Method name that is not defined by [*OPC UA — xRegistry*](OPC-UA-xRegistry.md), OPC 10000-20, or its own domain companion specification.

## Annex A — Correspondence to the xRegistry HTTP binding (informative)

This annex is informative and provides a cross-walk for readers coming from the sibling xRegistry HTTP binding. The OPC UA API defined by this document is not derived from these HTTP methods or paths; the table only identifies the corresponding operation concepts in the two peer bindings.

| xRegistry operation | OPC UA operation in this document | HTTP binding method and path |
|---|---|---|
| Read registry | Read `RegistryType` Properties and Browse group children (§5.1) | `GET /` |
| Replace or partially update registry attributes | Write mutable `RegistryType` Properties and process nested groups when supplied (§5.2) | `PUT /`, `PATCH /` |
| Process group collections at the registry root | Resolve or create `GroupType` children with `CreateGroup` and Write Properties (§5.2) | `POST /` |
| Export registry document | Browse/Read the `RegistryType` subtree and serialize it (§5.3, §8) | `GET /export` or `GET /?export` |
| Read capabilities | Read `RegistryType.Capabilities` (§5.4) | `GET /capabilities` |
| Read offered capabilities | Read a domain offered-capabilities Property or offered section in `Capabilities` (§5.4) | `GET /capabilitiesoffered` |
| Replace or partially update capabilities | Write `RegistryType.Capabilities` if writable (§5.5) | `PUT /capabilities`, `PATCH /capabilities` |
| Read model | Read `RegistryType.Model` (§5.4) | `GET /model` |
| Read model source | Read a domain model-source target or documented section in `Model` (§5.4) | `GET /modelsource` |
| Replace model source | Write the domain model-source target if supported (§5.5) | `PUT /modelsource` |
| List a group collection | Browse or Query `GroupType` children under the registry (§5.6) | `GET /<GROUPS>` |
| Create or update a group collection subset | Resolve/create `GroupType` children and Write group Properties (§5.7) | `PATCH /<GROUPS>`, `POST /<GROUPS>` |
| Delete a group collection subset | Batch `Delete(objectToDelete)` on the `RegistryType` root (§5.9) | `DELETE /<GROUPS>` |
| Read a group | Resolve the `GroupType` by `GroupId`, then Read Properties and Browse resources (§5.8) | `GET /<GROUPS>/<GID>` |
| Replace or partially update a group | Create if needed with `CreateGroup`, then Write mutable group Properties (§5.7) | `PUT /<GROUPS>/<GID>`, `PATCH /<GROUPS>/<GID>` |
| Process resource collections under a group | Resolve/create `ResourceType` children and Write documents or Properties (§5.7) | `POST /<GROUPS>/<GID>` |
| Delete a group | `Delete(objectToDelete)` on the parent `RegistryType` (§5.9) | `DELETE /<GROUPS>/<GID>` |
| List a resource collection | Browse or Query `ResourceType` children under the group (§5.11) | `GET /<GROUPS>/<GID>/<RESOURCES>` |
| Create or update a resource collection subset | Resolve/create `ResourceType` children with `CreateResourceOrVersion`, then Write documents or Properties (§5.12) | `PATCH /<GROUPS>/<GID>/<RESOURCES>`, `POST /<GROUPS>/<GID>/<RESOURCES>` |
| Delete a resource collection subset | Batch `Delete(objectToDelete)` on the parent `GroupType` (§5.16) | `DELETE /<GROUPS>/<GID>/<RESOURCES>` |
| Read a resource document | `Open`/`Read`/`Close` on the default `ResourceType` (§5.13) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>` |
| Read resource metadata | Read Properties of the default `ResourceType` (§5.14) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>$details` |
| Replace or partially update resource metadata | Write resource Properties and optionally call `AddAttribute`/`RemoveAttribute` (§5.14) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>$details`, `PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>$details` |
| Replace a resource document | Create if needed with `CreateResourceOrVersion`, then `Open`/`SetPosition`/`Write`/`Close` (§5.15) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>` |
| Create or update a resource version | Create/update a `ResourceType` with matching `ResourceId` and `VersionId` (§5.18) | `POST /<GROUPS>/<GID>/<RESOURCES>/<RID>` |
| Delete a resource | Delete the default resource or all associated version files according to model rules (§5.16) | `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>` |
| Read resource meta entity | Read resource-level Properties and domain meta Properties (§5.14) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta` |
| Replace or partially update resource meta entity | Write supported meta Properties or domain default-version state (§5.14) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta`, `PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta` |
| Delete resource meta entity | Reject as unsupported or reset individual mutable meta attributes when domain-defined (§5.14) | `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta` |
| List versions | Browse or Query version `ResourceType` files (§5.17) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions` |
| Create or update version collection subset | Resolve/create version files and Write version documents or Properties (§5.18) | `PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions`, `POST /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions` |
| Delete version collection subset | Batch `Delete(objectToDelete)` of selected version files (§5.21) | `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions` |
| Read a version document | `Open`/`Read`/`Close` on the selected version file (§5.19) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>` |
| Read version metadata | Read Properties of the selected version file (§5.19) | `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>$details` |
| Replace or partially update version metadata | Write version Properties and optionally call `AddAttribute`/`RemoveAttribute` (§5.18) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>$details`, `PATCH /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>$details` |
| Replace a version document | Create if needed, then `Open`/`SetPosition`/`Write`/`Close` on the version file (§5.20) | `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>` |
| Delete a version | `Delete(objectToDelete)` on the parent `GroupType` (§5.21) | `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>` |
