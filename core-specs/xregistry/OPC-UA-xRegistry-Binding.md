# OPC UA — xRegistry Binding

**Working draft for submission to the OPC Foundation Working Group and the xRegistry organization**
**Proposed Part: OPC 10000-2xx (number to be assigned)**
**Companion namespace:** `http://opcfoundation.org/UA/xRegistry/`
**Version:** 0.1.0 · **Date:** 2026-07-16

> **Status — working draft.** This document defines the OPC UA protocol binding for xRegistry, using the OPC UA FileTransfer-based information model defined by [*OPC UA — xRegistry*](OPC-UA-xRegistry.md). It mirrors the structure and intent of the xRegistry HTTP binding (`core/http.md`) so that an xRegistry registry can be served over OPC UA with the same registry, group, resource, version, document, metadata, request-flag and error semantics.

---

## 1 Scope

This specification defines the generic OPC UA protocol binding for [xRegistry](https://github.com/xregistry/spec), analogous to the xRegistry HTTP binding, but expressed in terms of OPC UA AddressSpace nodes, Services and FileTransfer Methods.

The abstract OPC UA information model is defined by [*OPC UA — xRegistry*](OPC-UA-xRegistry.md): a registry is a `RegistryType` directory, each group is a `GroupType` directory, and each resource or resource version document is a `ResourceFileType` file. This binding specifies how each xRegistry API operation is realized against those nodes using Browse, Read, Write, Call, Query and FileTransfer operations.

This binding is protocol-specific and does not redefine the xRegistry core processing model. Entity identity (`xid`, `self`, group identifiers, resource identifiers and version identifiers), update semantics (`PUT`, `PATCH`, `POST`, `DELETE`), request flags, collection processing, metadata/document separation and error conditions retain their xRegistry meaning, while their transport representation is OPC UA rather than HTTP.

This binding is independent of any domain registry. A concrete companion specification subtypes `RegistryType`, `GroupType` and `ResourceFileType` and constrains the group and resource names; the OPC UA operation mapping in this document remains the same.

## 2 Normative references

- [xRegistry Core specification, v1.0-rc3](https://github.com/xregistry/spec/blob/v1.0-rc3/core/spec.md) — the registry, group, resource, version, metadata, request-flag and error model.
- [xRegistry HTTP binding, v1.0-rc3](https://github.com/xregistry/spec/blob/v1.0-rc3/core/http.md) — the reference binding whose entity and operation structure this document mirrors.
- [xRegistry primer, v1.0-rc3](https://github.com/xregistry/spec/blob/v1.0-rc3/core/primer.md) — the three xRegistry representations and federation concepts.
- [OPC UA — xRegistry](OPC-UA-xRegistry.md) — the companion information model bound by this document.
- [OPC 10000-3](https://reference.opcfoundation.org/specs/OPC-10000-3/) — Address Space Model, including `ExpandedNodeId`.
- [OPC 10000-4](https://reference.opcfoundation.org/specs/OPC-10000-4/) — Services, including Browse, Read, Write, Call, Query, TranslateBrowsePathsToNodeIds and StatusCodes.
- [OPC 10000-5](https://reference.opcfoundation.org/specs/OPC-10000-5/) — Base Information Model, including `PropertyType` and `KeyValuePair`.
- [OPC 10000-20](https://reference.opcfoundation.org/specs/OPC-10000-20/) — File Transfer, including `FileType` and `FileDirectoryType`.

## 3 Notations and terminology

Key words **shall**, **should**, **may**, **shall not** and **should not** are interpreted as described in the ISO/IEC directives and RFC 2119.

The terms registry, group, resource, version, document, metadata, collection, request flag, `xid`, `self`, `epoch`, `labels`, `model`, `capabilities`, federation and representation have the meanings defined by the xRegistry core specification and [*OPC UA — xRegistry*](OPC-UA-xRegistry.md).

OPC UA type and member names are written exactly as defined by [*OPC UA — xRegistry*](OPC-UA-xRegistry.md) Annex A and the corresponding NodeSet: `RegistryType`, `GroupType`, `ResourceFileType`, `RegistryId`, `SpecVersion`, `Capabilities`, `Model`, `GroupId`, `ResourceId`, `VersionId`, `Format`, `ContentType`, `ExternalReference`, `ResourceUrl`, `Xid`, `Epoch`, `Name`, `Description`, `Documentation`, `Labels`, `CreatedAt`, `ModifiedAt`, `AddProperty` and `RemoveProperty`.

The OPC UA Services used by this binding are Browse for collection enumeration, Read for Properties and node metadata, Write for writable Properties, Call for FileTransfer and xRegistry property Methods, Query for server-side filtering where supported, TranslateBrowsePathsToNodeIds for path resolution, and the FileTransfer Methods inherited from `FileType` and `FileDirectoryType`.

In pseudo-signatures, the FileTransfer Methods are shown by their BrowseNames rather than by numeric NodeIds because a concrete server may expose them on domain subtypes of `RegistryType`, `GroupType` or `ResourceFileType`.

## 4 OPC UA Binding Overview

### 4.1 OPC UA API patterns

This specification defines the following base OPC UA access patterns, corresponding to the base HTTP API paths:

```yaml
/                                                # RegistryType root
/capabilities                                    # RegistryType.Capabilities Property
/capabilitiesoffered                             # Offered capabilities, if exposed by domain model or Capabilities payload
/model                                           # RegistryType.Model Property
/modelsource                                     # Writable source model, if exposed by domain model or Model payload
/export                                          # Serialized export of RegistryType subtree
/<GROUPS>                                        # Browse RegistryType children of a group collection/type
/<GROUPS>/<GID>                                  # GroupType directory
/<GROUPS>/<GID>/<RESOURCES>                      # Browse GroupType children of a resource collection/type
/<GROUPS>/<GID>/<RESOURCES>/<RID>                # ResourceFileType default resource/version file
/<GROUPS>/<GID>/<RESOURCES>/<RID>/meta           # Metadata Properties of ResourceFileType
/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions       # Version files associated with ResourceFileType
/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID> # ResourceFileType file for a specific VersionId
```

The OPC UA binding has no URL authority. The equivalent of the HTTP API prefix is the selected `RegistryType` root node; every path in this document is resolved relative to that root by Browse or TranslateBrowsePathsToNodeIds.

A server may expose more than one registry. Each registry is a distinct `RegistryType` or domain subtype instance, and the client selects the registry by NodeId, BrowsePath, discovery metadata or domain convention before applying this binding.

If an optional xRegistry API path is not supported, the server shall fail the corresponding Browse, Read, Write or Call operation with an appropriate StatusCode, normally `Bad_NodeIdUnknown`, `Bad_BrowseNameInvalid`, `Bad_NotSupported` or `Bad_MethodInvalid` depending on how the operation was attempted.

If an operation is not supported for an otherwise supported node, the server shall return `Bad_NotSupported`, `Bad_UserAccessDenied`, `Bad_NotWritable`, `Bad_MethodInvalid` or `Bad_InvalidArgument` as appropriate.

### 4.2 Path to AddressSpace mapping

The following table defines the normative mapping from xRegistry paths to OPC UA targets.

| xRegistry path | OPC UA target | Primary operation |
|---|---|---|
| `/` | selected `RegistryType` root node | Read Properties and Browse group children |
| `/capabilities` | `RegistryType.Capabilities` | Read or Write the JSON string Property |
| `/capabilitiesoffered` | offered-capabilities structure exposed by the server, if any | Read a domain Property or the offered section of `Capabilities` |
| `/model` | `RegistryType.Model` | Read the JSON string Property |
| `/modelsource` | server-specific model source, if writable; otherwise `RegistryType.Model` is read-only | Read or Write a domain Property or reject as unsupported |
| `/export` | `RegistryType` subtree serialized as an xRegistry document | Browse and Read subtree; optionally server-side export Property or Method in a domain model |
| `/<GROUPS>` | collection of `GroupType` children under `RegistryType` whose collection name is `<GROUPS>` | Browse, Query, and optionally Call `CreateDirectory` on the registry |
| `/<GROUPS>/<GID>` | `GroupType` child whose `GroupId` is `<GID>` | Read/Write Properties, Browse resources, Delete via parent |
| `/<GROUPS>/<GID>/<RESOURCES>` | collection of `ResourceFileType` children under the group whose collection name is `<RESOURCES>` | Browse, Query, and optionally Call `CreateFile` on the group |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>` | default `ResourceFileType` for `ResourceId = <RID>` | Open/Read document or Read Properties for metadata |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>$details` | same `ResourceFileType`, metadata view | Read/Write Properties and optionally Call `AddProperty`/`RemoveProperty` |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/meta` | metadata Properties of the resource and default-version selection state | Read/Write Properties; domain extensions may add meta Properties |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions` | set of `ResourceFileType` files with matching `ResourceId` and distinct `VersionId` | Browse/Query associated version files |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>` | `ResourceFileType` whose `ResourceId = <RID>` and `VersionId = <VID>` | Open/Read document or Read Properties for metadata |
| `/<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>$details` | same version file, metadata view | Read/Write Properties and optionally Call `AddProperty`/`RemoveProperty` |

The collection names `<GROUPS>` and `<RESOURCES>` are xRegistry model names, not new base nodes in this abstract namespace. A domain registry may express them through subtype BrowseNames, domain Properties, folders or model metadata, but each concrete group instance shall be a `GroupType` subtype and each concrete resource/version instance shall be a `ResourceFileType` subtype.

### 4.3 Path resolution

A client resolves an xRegistry path by starting at the selected `RegistryType` root and applying Browse or TranslateBrowsePathsToNodeIds to locate children with the requested BrowseName or with the requested identifier Property.

When a path segment is an xRegistry collection name (`<GROUPS>` or `<RESOURCES>`), the client may resolve it through the registry `Model` JSON, through the BrowseName of domain subtype children, or through domain-specific collection folders if the companion specification defines them. The abstract base model requires the resulting instances to be `GroupType` or `ResourceFileType`, not a particular collection-folder shape.

When a path segment is an entity identifier (`<GID>`, `<RID>` or `<VID>`), the definitive match is the corresponding `GroupId`, `ResourceId` or `VersionId` Property. BrowseName equality is a useful optimization but is not the normative identity test unless the domain specification constrains BrowseNames to equal identifiers.

The xRegistry `self` value is not a mandatory OPC UA Property in the base model. In this binding it is derived from the selected registry root and the entity's `Xid`; an OPC UA client can reconstruct a canonical `self` reference as a registry root NodeId plus the relative `Xid`, or as an implementation-defined URL/URN for display.

### 4.4 Entity processing rules

The HTTP binding distinguishes `GET`, `PUT`, `PATCH`, `POST` and `DELETE`; this binding maps those verbs to OPC UA operations while retaining the same xRegistry entity-processing semantics.

A `GET` of a collection is Browse or Query over the corresponding directory. A `GET` of an entity metadata view is Read of the entity Properties. A `GET` of a resource or version document is `Open`/`Read`/`Close` on the `ResourceFileType` file.

A `PUT` of an entity is a full replacement of its mutable metadata and, for resources or versions with documents, optionally a full replacement of the file bytes. It is realized by creating the node if needed (`CreateDirectory` or `CreateFile`), writing file content if present, and writing or removing mutable Properties so omitted mutable attributes are reset or removed according to the xRegistry core rules.

A `PATCH` of an entity changes only explicitly named mutable attributes. It is realized by Write of writable Properties, by `AddProperty(Key, Value) → Success` and `RemoveProperty(Key) → Success` on `ResourceFileType` where extension attributes or labels are involved, and by domain-defined writable Properties for registry or group extension attributes. A `PATCH` shall not be used to patch arbitrary bytes inside a resource document; replacing document bytes uses the `PUT` document mapping.

A `POST` to a collection creates or updates one or more child entities. It is realized as a sequence of `CreateDirectory` or `CreateFile` calls followed by Property Writes and, for document-bearing resources or versions, file Writes. A server shall apply the xRegistry atomicity rule: if one entity in the request cannot be processed, the server should reject the whole operation and avoid partial effects; if the server cannot guarantee multi-node atomicity, it shall advertise that limitation in `Capabilities`.

A `DELETE` of an entity is the inherited `Delete` Method on the parent `FileDirectoryType`, targeting the child directory or file to remove. A `DELETE` of a collection is a batch of `Delete` calls over selected children.

### 4.5 Method signatures and argument mapping

The FileTransfer Method signatures used by this binding are the standard OPC 10000-20 signatures of the inherited Methods on `FileDirectoryType` and `FileType`; their exact argument definitions are normative in OPC 10000-20.

| xRegistry action | OPC UA Method or Service | Argument mapping |
|---|---|---|
| Create group | `RegistryType.CreateDirectory(directoryName)` | `directoryName` is the desired BrowseName or server-derived name for a `GroupType` subtype; `GroupId` is written or derived after creation |
| Create resource or version | `GroupType.CreateFile(fileName, requestFileOpen)` | `fileName` is the desired BrowseName or filename for a `ResourceFileType` subtype; `requestFileOpen = true` returns a write handle when document bytes follow |
| Delete group/resource/version | parent `FileDirectoryType.Delete(objectToDelete)` | `objectToDelete` is the child `NodeId` resolved from the xRegistry path |
| Move or copy entity | parent `FileDirectoryType.MoveOrCopy(objectToMoveOrCopy, targetDirectory, createCopy, newName)` | xRegistry identity Properties shall be updated or validated according to whether the operation is a move or copy |
| Read document | `ResourceFileType.Open(mode)` → `Read(fileHandle, length)` → `Close(fileHandle)` | `mode` is read-only; `length` and repeated Reads are bounded by `Size` |
| Replace document | `ResourceFileType.Open(mode)` → `SetPosition(fileHandle, 0)` → `Write(fileHandle, data)` → `Close(fileHandle)` | `mode` allows write; the complete replacement byte stream is written; server updates `ModifiedAt` and `Epoch` |
| Read metadata | Read Service on Properties | Property BrowseNames map to xRegistry attribute names by the tables in this document and the domain model |
| Replace scalar metadata | Write Service on Properties | Value DataTypes are those in Annex A of the base model |
| Add/update resource extension attribute or label | `ResourceFileType.AddProperty(Key: String, Value: String) → (Success: Boolean)` | `Key` is the xRegistry attribute or label key; `Value` is the canonical string representation |
| Remove resource extension attribute or label | `ResourceFileType.RemoveProperty(Key: String) → (Success: Boolean)` | `Key` is the xRegistry attribute or label key; `Success = true` indicates the effective absence of the property |

The base NodeSet defines `AddProperty` and `RemoveProperty` on `ResourceFileType`. Registry-level or group-level mutable extension attributes shall be represented as writable Properties on the relevant domain subtype or by domain-defined Methods; this base binding does not invent additional Methods on `RegistryType` or `GroupType`.

### 4.6 Attribute mapping

The base model Properties map to xRegistry attributes as follows.

| xRegistry attribute | OPC UA Property | Applies to |
|---|---|---|
| `registryid` | `RegistryId` | `RegistryType` |
| `specversion` | `SpecVersion` | `RegistryType` |
| `capabilities` | `Capabilities` | `RegistryType` |
| `model` | `Model` | `RegistryType` |
| `<GROUP>id` | `GroupId` | `GroupType` |
| `<RESOURCE>id` | `ResourceId` | `ResourceFileType` |
| `versionid` | `VersionId` | `ResourceFileType` |
| `format` | `Format` | `ResourceFileType` |
| `contenttype` | `ContentType` | `ResourceFileType` |
| `<RESOURCE>url` | `ResourceUrl` | `ResourceFileType` |
| federation target | `ExternalReference` | `ResourceFileType` |
| `xid` | `Xid` | all base entity types |
| `epoch` | `Epoch` | all base entity types |
| `name` | `Name` | all base entity types |
| `description` | `Description` | all base entity types |
| `documentation` | `Documentation` | all base entity types |
| `labels` | `Labels` | all base entity types |
| `createdat` | `CreatedAt` | all base entity types |
| `modifiedat` | `ModifiedAt` | all base entity types |

The xRegistry attributes `self`, collection `url` attributes, collection `count` attributes, `metaurl`, `versionsurl`, `versionscount`, `defaultversionurl`, `isdefault`, `ancestor`, `<RESOURCE>` and `<RESOURCE>base64` are serialization artifacts or domain/model attributes rather than mandatory base Properties. A server may expose them as domain Properties, but a client shall be able to derive them from `Xid`, `ResourceId`, `VersionId`, Browse results and the document bytes where possible.

## 5 Registry OPC UA APIs

This section mirrors the entity order of the xRegistry HTTP binding and defines the successful OPC UA interaction patterns. Error mapping is specified in §10.

### 5.1 Entity Processing Rules

### 5.1.1 Creating or Updating Entities

Creating or updating entities may be done with the OPC UA equivalents of HTTP `PUT`, `PATCH` and `POST`.

The OPC UA `PUT` equivalent for a single entity shall target the entity's node or the parent directory from which the entity can be created. If the entity does not exist, the server creates a `GroupType` directory or `ResourceFileType` file; if it exists, the server updates it. Mutable Properties omitted from the replacement representation shall be deleted, reset to default, or left unchanged only where the xRegistry core rules or server-managed semantics require that behavior.

The OPC UA `PATCH` equivalent for a single entity shall write only explicitly named mutable Properties and shall remove explicitly null attributes. For a resource metadata patch, a client may call `AddProperty` for present string extension attributes or labels and `RemoveProperty` for null extension attributes or labels; for base Properties the client should use Write where the Property is writable.

The OPC UA `POST` equivalent for a collection shall process a map of child entities as repeated create-or-update operations under the collection's parent directory. A client creates groups with `CreateDirectory` on `RegistryType` and resources or versions with `CreateFile` on `GroupType`; after creation it writes mandatory and mutable Properties and writes document bytes where supplied.

The OPC UA `POST` equivalent for a single entity that owns nested collections shall process only nested collection entries and shall not modify the owning entity's own Properties, matching the HTTP `POST <PATH-TO-ENTITY>` rule.

Unless otherwise stated, a request to update a read-only Property shall be ignored only if xRegistry says that read-only attribute updates are ignored; otherwise the server shall reject the Write with `Bad_NotWritable` or `Bad_UserAccessDenied`. A request that supplies an identifier Property (`RegistryId`, `GroupId`, `ResourceId` or `VersionId`) whose value conflicts with the target entity shall fail with `Bad_InvalidArgument` or `Bad_IdentityChangeNotSupported`.

Any successful create or update shall update `ModifiedAt` and increment `Epoch` on the modified entity. Creation shall initialize `CreatedAt`, `ModifiedAt`, `Epoch`, `Xid` and the appropriate identifier Properties according to [*OPC UA — xRegistry*](OPC-UA-xRegistry.md) §6.5.

### 5.1.2 OPC UA-specific attribute processing rules

OPC UA carries metadata as typed Property Values rather than HTTP headers. The HTTP-specific header encoding rules do not apply; strings are OPC UA `String`, timestamps are `DateTime`, `Labels` is `KeyValuePair[]`, `ExternalReference` is `ExpandedNodeId`, and `Epoch` is `UInt32`.

When a resource document is read as bytes, accompanying metadata is obtained by separate Read operations on the same `ResourceFileType` Properties. A server may optimize this by returning metadata in the same Service response when using Query or by exposing a domain Method, but the interoperable baseline is separate `Open`/`Read`/`Close` plus Read Properties.

The HTTP `$details` suffix is represented by choosing Property Reads/Writes instead of file content Reads/Writes. The target NodeId is the same `ResourceFileType`; only the operation mode differs.

The xRegistry `contenttype` attribute maps to `ContentType`, not to `MimeType`. `MimeType` is inherited from `FileType` and may mirror `ContentType` for generic FileTransfer clients; when both are present, `ContentType` is the xRegistry attribute and `MimeType` is the FileTransfer media hint.

### 5.1.3 Pagination

OPC UA Browse already paginates large child sets through continuation points and `BrowseNext`. A server shall use Browse continuation points as the baseline representation of xRegistry pagination for collections.

A client that wants a page of collection entries calls Browse with a requested maximum reference count and then calls `BrowseNext` until the desired page is complete or no continuation point remains. The equivalent of an HTTP `Link` next relation is the continuation point held by the client session.

For file bytes, a client paginates through `Read(fileHandle, length)` and may use `GetPosition` and `SetPosition` to implement random access. For arrays such as `Labels`, a client may use the Read Service `IndexRange` parameter where supported.

### 5.1.4 Supported operations discovery

The HTTP `OPTIONS` method is represented by OPC UA metadata. A client discovers supported operations by browsing the target node for Methods, by reading `Writable`, `UserWritable`, AccessLevel and UserAccessLevel attributes of Variables, by reading `Capabilities`, and by inspecting executable/user-executable bits of Method nodes.

A server shall not require a side-effecting operation for discovery. If a FileTransfer Method or `AddProperty`/`RemoveProperty` is absent, non-executable or rejected with `Bad_UserAccessDenied`, the corresponding xRegistry write operation is not available to that client.

### 5.2 Registry Entity

### 5.2.1 `GET /`

The OPC UA equivalent of `GET /` is Read of the selected `RegistryType` Properties plus Browse of its group children.

A client shall read `RegistryId`, `SpecVersion`, `Capabilities`, `Model`, `Xid`, `Epoch`, `Name`, `Description`, `Documentation`, `Labels`, `CreatedAt` and `ModifiedAt` where present. It shall Browse the registry root to discover `GroupType` or domain subtype children and shall include collection URL/count equivalents in a serialized response by deriving them from the registry model and Browse results.

### 5.2.2 `PATCH` and `PUT /`

The OPC UA equivalent of `PATCH /` or `PUT /` is Write of mutable `RegistryType` Properties and, if the request includes nested group collections, create-or-update of the corresponding `GroupType` children.

For `PUT /`, the client writes the full replacement set of mutable registry attributes; omitted mutable attributes are removed or reset according to xRegistry rules. `Capabilities` and `Model` are special: absence shall not require a change, while presence shall be treated as a complete replacement unless the request is a patch-level update supported by the server.

For `PATCH /`, the client writes only included Properties. A null attribute is represented by writing a server-defined null/default value if the DataType permits it, by deleting a domain extension Property if supported, or by failing with `Bad_NotSupported` if the attribute is mandatory or cannot be removed.

The base `RegistryType` does not define `AddProperty` or `RemoveProperty`; registry extension attributes shall therefore be modeled as writable Properties on a domain subtype or managed by a domain-defined Method.

### 5.2.3 `POST /`

The OPC UA equivalent of `POST /` is batch creation or update of group entities under the selected `RegistryType` without modifying registry-level Properties.

For each group entry in the request, the client resolves an existing group by `GroupId`; if absent, it calls `CreateDirectory(directoryName)` on the registry root. The server creates a `GroupType` or domain subtype instance, initializes `GroupId`, `Xid`, `Epoch`, `CreatedAt` and `ModifiedAt`, and then applies the supplied group Properties and nested resource collections.

If the request contains registry-level attributes rather than only group collections, the server shall reject it with `Bad_InvalidArgument`, corresponding to xRegistry `groups_only`.

### 5.2.4 `GET /export`

The OPC UA equivalent of `GET /export` is serialization of the selected `RegistryType` subtree into the xRegistry JSON document shape. It is an alias for reading the registry with document mode and inlining the full subtree, equivalent to HTTP `GET /?doc&inline=*,capabilities,modelsource`.

The interoperable baseline export algorithm is Browse the registry subtree, Read all mapped Properties, Open/Read/Close each inlined `ResourceFileType` document, and serialize the result according to §8. A server may expose an optimized domain Method or Property for export, but such an optimization shall produce the same document shape.

Update operations on `/export` are not defined by this binding. Import is an implementation capability expressed as normal create/update operations or by a domain-defined import Method.

### 5.3 Registry Capabilities

### 5.3.1 `GET /capabilities`

The OPC UA equivalent of `GET /capabilities` is Read of `RegistryType.Capabilities`. The Property value is a JSON string containing the xRegistry capabilities map.

A server should include in `Capabilities` the OPC UA binding features it supports, such as create, update, delete, query, filter, inline, export, versioning, federation, writable model and multi-operation atomicity.

### 5.3.2 `GET /capabilitiesoffered`

The base information model does not define a separate `CapabilitiesOffered` Property. If a server supports mutable capabilities, it shall expose the offered-capabilities information either inside the `Capabilities` JSON, as a domain subtype Property, or through domain documentation referenced by `Model`.

If no offered-capabilities target is exposed, the operation shall fail with `Bad_NodeIdUnknown` or `Bad_NotSupported` rather than inventing an unmapped base node.

### 5.3.3 `PATCH` and `PUT /capabilities`

The OPC UA equivalent of `PATCH /capabilities` or `PUT /capabilities` is Write of `RegistryType.Capabilities` if the Property is writable for the current user. A `PUT` writes the complete capabilities JSON. A `PATCH` writes only top-level capabilities if the server supports patch-level semantics; otherwise the client shall perform read-modify-write and the server may reject partial writes with `Bad_NotSupported`.

Unsupported capability changes shall fail with `Bad_InvalidArgument` or `Bad_NotSupported`, and no capability change shall take effect before the current Service operation completes.

### 5.4 Registry Model

### 5.4.1 `GET /model`

The OPC UA equivalent of `GET /model` is Read of `RegistryType.Model`. The Property value is a JSON string containing the full xRegistry model definition.

A client may also use `Model` to resolve domain collection names to `GroupType` and `ResourceFileType` subtype BrowseNames before browsing entities.

### 5.4.2 `GET /modelsource`

The base information model does not define a distinct `ModelSource` Property. If a server distinguishes the effective model from the client-provided model source, it shall expose the model source as a domain subtype Property or inside the `Model` JSON using a documented shape.

If the model source has never been set and a model-source target exists, the server shall return an empty JSON object (`{}`) as a string value, matching xRegistry semantics.

### 5.4.3 `PUT /modelsource`

The OPC UA equivalent of `PUT /modelsource` is Write of the domain-defined model-source Property or other domain-defined operation. The abstract base binding does not define a writable `ModelSource` node.

If a server supports model-source updates via `RegistryType.Model`, it shall document that `Model` is serving as model source and shall apply the xRegistry full-replacement rules. If the server exposes only effective `Model`, attempts to write model source shall fail with `Bad_NotWritable` or `Bad_NotSupported`.

### 5.5 Group Entity

### 5.5.1 `GET /<GROUPS>`

The OPC UA equivalent of `GET /<GROUPS>` is Browse or Query over the selected `RegistryType` root to return `GroupType` children that belong to the requested group collection.

The client filters Browse results by TypeDefinition (`GroupType` or subtype), by collection metadata in `Model`, by domain subtype, and finally by `GroupId` when an identifier is needed. The serialized collection keys are the `GroupId` values, not necessarily BrowseNames.

### 5.5.2 `PATCH` and `POST /<GROUPS>`

The OPC UA equivalent of `PATCH /<GROUPS>` or `POST /<GROUPS>` is batch create-or-update of `GroupType` children under the registry root.

For each group key, the client resolves an existing group by `GroupId`. If absent and creation is allowed, it calls `CreateDirectory(directoryName)` on the `RegistryType` root. It then writes group Properties according to `PATCH` or `POST` semantics: `PATCH` writes only named attributes; `POST` supplies a full representation of each group being processed.

The response representation is obtained by reading back only the groups processed, not the entire group collection.

### 5.5.3 `DELETE /<GROUPS>`

The OPC UA equivalent of `DELETE /<GROUPS>` is a batch of `Delete(objectToDelete)` calls on the `RegistryType` root, one for each selected group child.

If an entity-specific `epoch` precondition is supplied, the client or server shall Read `Epoch` before deletion and fail the operation with `Bad_InvalidState` if the value does not match. If a server cannot perform the check and delete atomically, it shall either reject the preconditioned delete or advertise the limitation in `Capabilities`.

### 5.5.4 `GET /<GROUPS>/<GID>`

The OPC UA equivalent of `GET /<GROUPS>/<GID>` is resolution of the `GroupType` child whose `GroupId` equals `<GID>`, followed by Read of its Properties and Browse of its resource children as needed.

The standard base Properties are `GroupId`, `Xid`, `Epoch`, `Name`, `Description`, `Documentation`, `Labels`, `CreatedAt` and `ModifiedAt`. Domain group subtypes may add mandatory group-key Properties and extension metadata.

### 5.5.5 `PATCH` and `PUT /<GROUPS>/<GID>`

The OPC UA equivalent of `PATCH /<GROUPS>/<GID>` or `PUT /<GROUPS>/<GID>` is create-or-update of one `GroupType` directory and Write of its mutable Properties.

If the group does not exist and the operation permits creation, the server creates it with `CreateDirectory` on the registry root. The supplied `<GID>` shall match `GroupId`; a mismatch fails with `Bad_InvalidArgument`.

For `PUT`, omitted mutable group Properties are reset or removed according to xRegistry rules. For `PATCH`, omitted Properties are unchanged.

### 5.5.6 `POST /<GROUPS>/<GID>`

The OPC UA equivalent of `POST /<GROUPS>/<GID>` is batch create-or-update of resource collections under the specified group without modifying the group's own Properties.

The request body equivalent is a map from `<RESOURCES>` collection names to resource maps. For each resource entry, the client calls `CreateFile` if needed, writes the document if supplied, and writes resource Properties according to the nested operation semantics.

If the operation attempts to update group-level attributes rather than nested resource collections, the server shall reject it with `Bad_InvalidArgument`, corresponding to xRegistry `resources_only`.

### 5.5.7 `DELETE /<GROUPS>/<GID>`

The OPC UA equivalent of `DELETE /<GROUPS>/<GID>` is `Delete(objectToDelete)` on the parent `RegistryType`, where `objectToDelete` is the resolved group NodeId.

If an `epoch` precondition is supplied, `Epoch` shall be checked before deletion as described in §5.5.3.

### 5.6 Resource Entity

### 5.6.1 Resource Metadata vs Resource Document

In HTTP, `$details` distinguishes resource metadata from the resource document. In OPC UA, the same distinction is made by the operation selected on the same `ResourceFileType` node.

To access the document, a client uses the inherited `FileType` Methods on `ResourceFileType`: `Open`, `Read`, optionally `GetPosition` and `SetPosition`, `Write` when replacing the document, and `Close`.

To access metadata, a client uses Read or Write on `ResourceFileType` Properties: `ResourceId`, `VersionId`, `Format`, `ContentType`, `ExternalReference`, `ResourceUrl`, `Xid`, `Epoch`, `Name`, `Description`, `Documentation`, `Labels`, `CreatedAt` and `ModifiedAt`, plus domain Properties.

If a resource type's xRegistry model has `hasdocument = false`, document access shall be rejected with `Bad_NotReadable`, `Bad_InvalidState` or `Bad_NotSupported`, and metadata access remains the normal entity representation.

### 5.6.2 Serializing Resource Domain-Specific Documents

When a resource or version is serialized as its domain-specific document, the bytes returned by `Read(fileHandle, length)` are the exact document bytes. If the document is empty, `Read` returns zero bytes at end-of-file.

The HTTP `xRegistry-` headers have no OPC UA equivalent. Clients obtain the same metadata by reading the Properties of the file before or after reading bytes. Servers should keep `ContentType` and the inherited `MimeType` consistent so generic FileTransfer clients can identify the media type.

If `ResourceUrl` is present and the document is external, `Open` may fail with `Bad_NotReadable` or may return a local cached representation. In either case the client can read `ResourceUrl` and `ExternalReference` to resolve the external content as described in §9.

### 5.6.3 `GET /<GROUPS>/<GID>/<RESOURCES>`

The OPC UA equivalent of `GET /<GROUPS>/<GID>/<RESOURCES>` is Browse or Query over the `GroupType` directory to return `ResourceFileType` children in the requested resource collection.

The serialized collection keys are `ResourceId` values. The default version of each resource is represented by the `ResourceFileType` selected by the server as the default for that `ResourceId`; in a flat implementation with one file per resource, that file's `VersionId` is the default version.

A client derives `versionscount` by querying or browsing all files associated with the same `ResourceId`, and derives `metaurl` and `versionsurl` from `Xid`.

### 5.6.4 `PATCH` and `POST /<GROUPS>/<GID>/<RESOURCES>`

The OPC UA equivalent of `PATCH /<GROUPS>/<GID>/<RESOURCES>` or `POST /<GROUPS>/<GID>/<RESOURCES>` is batch create-or-update of `ResourceFileType` children under the group.

For each resource key, the client resolves an existing default resource by `ResourceId`; if absent and creation is allowed, it calls `CreateFile(fileName, requestFileOpen)` on the `GroupType`. If `requestFileOpen = true`, the returned file handle may be used immediately to write the document bytes.

For metadata-only updates, the client writes Properties and optionally calls `AddProperty`/`RemoveProperty` for resource extension attributes or labels. For document creation or replacement, the client writes the complete document byte stream and sets `ContentType`, `Format`, `ResourceUrl` and `ExternalReference` as applicable.

### 5.6.5 `DELETE /<GROUPS>/<GID>/<RESOURCES>`

The OPC UA equivalent of `DELETE /<GROUPS>/<GID>/<RESOURCES>` is a batch of `Delete(objectToDelete)` calls on the parent `GroupType`, one for each selected `ResourceFileType` or resource-version set.

If the implementation represents multiple versions as sibling files, deleting a resource collection entry shall delete all version files for the selected `ResourceId` unless the request specifically targets `/versions/<VID>`.

### 5.6.6 `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>`

The OPC UA equivalent of `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>` without `$details` is document retrieval from the default `ResourceFileType`: `Open` for read, repeated `Read`, and `Close`. The client may read `Size`, `Writable`, `MimeType`, `LastModifiedTime`, `ContentType`, `ResourceId`, `VersionId`, `Xid` and `Epoch` to reproduce the full xRegistry response metadata.

The OPC UA equivalent with `$details` is Read of the same file's Properties without reading the file bytes.

If `ResourceUrl` or `ExternalReference` indicates external content, the server may either redirect by metadata (that is, return readable `ResourceUrl`/`ExternalReference` while `Open` fails with a suitable StatusCode) or serve cached bytes from the local file. The choice shall be documented in `Capabilities`.

### 5.6.7 `PATCH` and `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>`

The OPC UA equivalent of metadata `PATCH` or `PUT` is Write of the default `ResourceFileType` Properties, optionally combined with `AddProperty` and `RemoveProperty` for resource extension attributes and labels.

The OPC UA equivalent of document `PUT` is create-if-needed plus complete file replacement. If the resource file does not exist, the client calls `CreateFile` on the parent group. It then opens the file for writing, sets position to zero where needed, writes the complete new byte stream, closes the file, and writes or validates metadata Properties.

`PATCH` of document bytes is not defined. A client that wants to change document content shall use the `PUT` mapping and provide a complete replacement document.

If the supplied `ResourceId` conflicts with `<RID>`, the operation shall fail with `Bad_InvalidArgument`. If supplied `VersionId` creates a new version rather than replacing the default version, the operation shall follow §5.8.

### 5.6.8 `POST /<GROUPS>/<GID>/<RESOURCES>/<RID>`

The OPC UA equivalent of `POST /<GROUPS>/<GID>/<RESOURCES>/<RID>` is creation or update of a single version for the resource. In the flat base projection, this is a `ResourceFileType` with the same `ResourceId` and a distinct `VersionId`.

If a new version is created, the client calls `CreateFile` on the group with a filename or BrowseName derived from `<RID>` and the new `VersionId`, writes the version document if supplied, and writes `ResourceId = <RID>` and the new `VersionId`. The server updates default-version state according to xRegistry rules and domain model capabilities.

The response representation is obtained by reading back the created or updated version file's Properties and, for document mode, by reading back its file bytes if needed.

### 5.6.9 `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>`

The OPC UA equivalent of `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>` is deletion of the default resource entity or all version files associated with `ResourceId = <RID>`, depending on the server's version representation and xRegistry model configuration.

A server shall not leave dangling version files that remain discoverable as the same resource unless the domain model explicitly supports detached historic versions. If deletion of a default resource is disallowed while versions exist, the server shall return `Bad_InvalidState` or `Bad_NotSupported`.

### 5.7 Meta Entity

### 5.7.1 `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta`

The OPC UA equivalent of `GET .../meta` is Read of the resource-level metadata Properties on the `ResourceFileType` that represents the resource's default version, plus any domain Properties that represent xRegistry meta attributes such as compatibility, default-version selection, default-version stickiness or counts.

The base model does not define a separate `Meta` Object. The meta entity is therefore a serialization view over Properties of the resource and, where present, domain-defined Properties.

### 5.7.2 `PATCH` and `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta`

The OPC UA equivalent of meta update is Write of the Properties that implement the requested meta attributes. Base Properties such as `Epoch`, `CreatedAt` and `ModifiedAt` are normally server-managed and shall not be directly writable unless the server explicitly allows administrative writes.

Changing default-version state is domain-defined because the base model only defines `VersionId` on `ResourceFileType`; a server that supports the xRegistry `defaultversionid` meta attribute shall expose a writable domain Property or Method for that state.

### 5.7.3 `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/meta`

Deleting the meta entity is not supported. The server shall reject attempts to delete the meta view with `Bad_NotSupported` or `Bad_InvalidArgument`. Individual mutable meta attributes may be reset through the `PATCH` or `PUT` mapping if the domain model supports them.

### 5.8 Version Entity

### 5.8.1 `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions`

The OPC UA equivalent of `GET .../versions` is Browse or Query for all `ResourceFileType` files associated with `ResourceId = <RID>` and a non-empty `VersionId` under the owning `GroupType`.

An implementation may represent the default version as the same file reached by the resource path and additional versions as sibling files, or it may expose only one version if it does not support version history. The serialized version collection keys are `VersionId` values.

### 5.8.2 `PATCH` and `POST /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions`

The OPC UA equivalent of collection-level version update is batch create-or-update of version files. For each version key, the client resolves a `ResourceFileType` with `ResourceId = <RID>` and `VersionId = <VID>`; if absent and creation is allowed, it calls `CreateFile` on the group.

For `PATCH`, only named version attributes are written. For `POST`, each version entry is a full representation and omitted mutable attributes are reset or removed according to xRegistry rules.

If an empty version map is supplied for a non-existent resource, the server shall reject it with `Bad_InvalidArgument`, corresponding to xRegistry `missing_versions`.

### 5.8.3 `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions`

The OPC UA equivalent of deleting a versions collection subset is a batch of `Delete` calls on the parent `GroupType`, targeting the version files selected by `VersionId`.

A server shall reject deletion of the last required version of a resource if the xRegistry model requires every resource to have at least one version. A server shall also reject deletion of a default version unless it can atomically select a new default or the request explicitly sets one through a supported flag or meta update.

### 5.8.4 `GET /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>`

The OPC UA equivalent of `GET .../versions/<VID>` without `$details` is `Open`/`Read`/`Close` on the `ResourceFileType` whose `ResourceId` is `<RID>` and `VersionId` is `<VID>`.

The OPC UA equivalent with `$details` is Read of that version file's Properties. The `Xid` Property should identify the version path when the server materializes versions as separate entities.

### 5.8.5 `PATCH` and `PUT /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>`

The OPC UA equivalent of metadata update is Write of Properties on the version file, with `ResourceId` and `VersionId` validated against `<RID>` and `<VID>`. Extension attributes and labels on `ResourceFileType` may be managed through `AddProperty` and `RemoveProperty` where supported.

The OPC UA equivalent of document `PUT` is create-if-needed plus complete replacement of the version file bytes using `CreateFile`, `Open`, `SetPosition`, `Write` and `Close`.

`PATCH` of version document bytes is not defined.

### 5.8.6 `DELETE /<GROUPS>/<GID>/<RESOURCES>/<RID>/versions/<VID>`

The OPC UA equivalent of `DELETE .../versions/<VID>` is `Delete(objectToDelete)` on the parent `GroupType`, targeting the resolved version file.

If the version is the default version, the server shall either reject the delete with `Bad_InvalidState` or update default-version state according to xRegistry and domain rules.

## 6 Request Flags / Query Parameters

The xRegistry core request flags are protocol-independent. In OPC UA they are represented by operation choice, service parameters, Query clauses, continuation points, Read `IndexRange`, Write options, or server capabilities rather than URI query parameters.

Unknown or unsupported flags should be ignored when xRegistry defines them as response-shaping hints, and shall be rejected with `Bad_NotSupported` or `Bad_InvalidArgument` when they are required for safe write semantics.

| xRegistry flag | OPC UA realization |
|---|---|
| `?inline` | Browse and Read the named child collections or Properties in the same client operation sequence; a server-side Query or domain export may inline server-side |
| `?filter` | OPC UA Query Service where supported; otherwise client-side filtering after Browse and Read |
| `?sort` | Query ordering where supported; otherwise client-side ordering of Browse/Read results |
| pagination flags | Browse continuation points, `BrowseNext`, file `Read` length, and Read `IndexRange` |
| `?doc` | Serialize using document shape, omitting redundant URL/count metadata as defined by xRegistry |
| `?meta` | Read metadata Properties rather than document bytes; equivalent to `$details` operation mode for resources and versions |
| `?export` | Serialize the selected subtree as an xRegistry document; `/export` is the registry-root shorthand |
| `?epoch` | Read-and-compare `Epoch` before Write/Delete; server should perform atomically when advertised |
| `?ignore` | Server-side write processing option advertised in `Capabilities`; unsupported ignore values fail with `Bad_InvalidArgument` |
| `?setdefaultversionid` | Domain-defined default-version update, normally a meta Property or Method |
| `?specversion` | Compare requested version against `SpecVersion` and `Capabilities`; reject incompatible processing with `Bad_InvalidArgument` |
| `?binary` | Prefer raw `Open`/`Read` bytes for documents; metadata remains OPC UA typed Properties |
| `?collections` | Include or omit collection members by Browse depth and serialization rules |

### 6.1 `?filter` Flag

A server may support `?filter` through the OPC UA Query Service. The queried node set is the collection directory, the type filter is `GroupType` or `ResourceFileType` or a domain subtype, and filter operands reference Properties such as `GroupId`, `ResourceId`, `VersionId`, `Name`, `Labels`, `CreatedAt`, `ModifiedAt` or domain Properties.

If Query is not supported, a client may implement the same semantics by Browse of the collection, Read of Properties for candidate entities, and local evaluation of the xRegistry filter expressions. Such client-side filtering is interoperable but may be less efficient.

### 6.2 `?ignore` Flag

The `?ignore` flag affects write processing. In OPC UA, ignore behavior is advertised in `Capabilities` and applied by the server while processing Write, Call and FileTransfer operations.

Because OPC UA Write and Call do not carry arbitrary query parameters, a generic client that needs `ignore` semantics shall either use a server-defined operation that accepts write options, or shall pre-process the representation and omit ignored attributes before issuing standard Writes and Calls. Unsupported ignore requirements shall fail with `Bad_NotSupported` or `Bad_InvalidArgument`.

### 6.3 `?inline` Flag

The `?inline` flag maps to Browse depth and Property/document retrieval. `inline=*` means the client recursively browses the selected subtree, reads each entity's Properties, and reads document bytes where the document shape requires them.

Inlining `capabilities` and `model` means reading `Capabilities` and `Model` on the registry root. Inlining nested collections means browsing `GroupType` and `ResourceFileType` children and serializing them into the parent entity representation.

### 6.4 `?sort` Flag

A server may implement sorting with Query. If it does not, clients sort the collection entries after reading the Properties used as sort keys.

Browse order alone shall not be assumed to be xRegistry sort order unless the server explicitly documents that behavior in `Capabilities`.

### 6.5 `?doc`, `?meta` and `$details`

`?doc` selects xRegistry document serialization and normally causes derived URL/count attributes to be omitted where the xRegistry document shape omits them. In OPC UA this is a serialization mode, not a different node.

`?meta` and `$details` select Property access for resources and versions. A client shall not attempt byte-level `PATCH` of a document by using `?meta`; metadata and document bytes are separate operation modes on the same `ResourceFileType`.

### 6.6 Pagination and ranges

Collection pagination maps to Browse continuation points. Document range retrieval maps to the `length` argument of `Read`, to repeated reads from the current file position, and to `SetPosition` for random access. Array slicing maps to the Read Service `IndexRange` parameter for array-valued Properties such as `Labels`.

Continuation points are session-scoped OPC UA state and are not serializable as stable xRegistry URLs. A bridge that exposes both HTTP and OPC UA may translate between HTTP pagination links and OPC UA continuation points internally.

## 7 OPC UA value encoding

OPC UA uses typed Values and StatusCodes rather than HTTP headers and JSON bodies for every operation. JSON appears in this binding only where xRegistry defines a JSON document attribute, namely `Capabilities`, `Model`, possible model-source or export payloads, and resource documents whose domain media type is JSON.

Strings shall be encoded as OPC UA `String`, timestamps as `DateTime`, integer epochs as `UInt32`, labels as `KeyValuePair[]`, federation targets as `ExpandedNodeId`, and document bytes as `ByteString` chunks returned by `Read` on `FileType`.

When a complete xRegistry entity is serialized for export or for an OPC UA-to-HTTP bridge, the base Property BrowseNames are converted to their xRegistry lower-case attribute names. Domain Properties are serialized according to the domain registry model.

A server shall preserve unknown extension attributes that it accepts, using domain extension Properties, `Labels`, or `AddProperty`/`RemoveProperty` on `ResourceFileType` as applicable. If the server cannot preserve an accepted extension attribute, it shall reject the update rather than silently losing information.

## 8 Serialization

The document representation defined by xRegistry is produced from the OPC UA AddressSpace by walking the selected subtree and converting nodes and Properties to the xRegistry JSON entity shape.

For a `RegistryType`, serialization reads registry Properties, emits `registryid`, `specversion`, common attributes and any requested `capabilities` and `model` payloads, then serializes group collections by browsing `GroupType` children and grouping them by the xRegistry model's collection names.

For a `GroupType`, serialization reads `GroupId` and common Properties, emits the domain group identifier attribute, and serializes resource collections by browsing `ResourceFileType` children and grouping them by domain resource collection names.

For a `ResourceFileType`, metadata serialization reads `ResourceId`, `VersionId`, `Format`, `ContentType`, `ExternalReference`, `ResourceUrl` and common Properties. Document serialization reads the file bytes with FileTransfer and places them in the xRegistry `<RESOURCE>` or `<RESOURCE>base64` attribute according to the xRegistry document rules and the selected encoding.

The inverse import process creates or updates the same subtree: create group directories, create resource/version files, write document bytes, write mapped Properties, and let the server auto-bootstrap `Xid`, `Epoch`, `CreatedAt` and `ModifiedAt` where they are not explicitly supplied or are server-managed.

Serialization shall preserve the three-representation symmetry described in [*OPC UA — xRegistry*](OPC-UA-xRegistry.md) §4.2 and §7: an entity has the same `Xid` and identity whether reached as a file, through OPC UA services, or in an exported xRegistry document.

## 9 Federation

Federation is realized by `ExternalReference` and `ResourceUrl` on `ResourceFileType`, as defined by [*OPC UA — xRegistry*](OPC-UA-xRegistry.md) §8 and Annex B.

`ExternalReference` is an `ExpandedNodeId`. Its `ServerUri` identifies the remote OPC UA server that hosts the referenced registry, and its `NamespaceUri` plus identifier identify the remote resource node independently of the server's local namespace indexes.

`ResourceUrl` is the xRegistry `<RESOURCE>url` string. It may contain an OPC UA endpoint/browse-path convention for another OPC UA registry, or an HTTP URL for a non-OPC-UA xRegistry server.

To resolve a federated OPC UA resource, a client reads `ExternalReference`; if `ServerUri` is local or empty it resolves the target in the local AddressSpace, otherwise it discovers or connects to the remote endpoint, maps the `NamespaceUri` to the remote namespace index, resolves the target NodeId or BrowsePath, and reads the remote `ResourceFileType` using the same FileTransfer operations as for a local file.

A server may expose a local proxy `ResourceFileType` for a federated resource. Such a proxy shall retain the remote resource identity in `Xid`, `ResourceId` and `VersionId`, and shall not treat the local endpoint identity as part of the resource identity.

## 10 Error Handling

OPC UA errors are returned as StatusCodes on Service results, Operation results, Method Call results, or individual input/output argument diagnostics. When an xRegistry error includes structured details, a server should include additional diagnostic information in the OPC UA DiagnosticInfo or in a domain-specific error payload where available.

The following mapping is normative unless a more specific OPC UA StatusCode applies.

| xRegistry / HTTP condition | OPC UA StatusCode |
|---|---|
| API path not supported (`api_not_found`) | `Bad_NodeIdUnknown`, `Bad_BrowseNameInvalid` or `Bad_NotSupported` |
| action not supported for an existing node | `Bad_NotSupported` or `Bad_MethodInvalid` |
| entity not found | `Bad_NodeIdUnknown` or `Bad_NotFound` where available |
| method target not found | `Bad_MethodInvalid` |
| invalid path segment or malformed identifier | `Bad_BrowseNameInvalid` or `Bad_InvalidArgument` |
| required attribute missing | `Bad_InvalidArgument` |
| invalid attribute value | `Bad_InvalidArgument`, `Bad_TypeMismatch` or `Bad_OutOfRange` |
| mismatched `RegistryId`, `GroupId`, `ResourceId` or `VersionId` | `Bad_InvalidArgument` or `Bad_IdentityChangeNotSupported` |
| already exists | `Bad_BrowseNameDuplicated` or `Bad_NodeIdExists` |
| not writable or read-only attribute | `Bad_NotWritable` or `Bad_UserAccessDenied` |
| resource document not readable | `Bad_NotReadable` or `Bad_InvalidState` |
| missing body or missing document bytes | `Bad_InvalidArgument` |
| unsupported `$details` / metadata mode | `Bad_NotSupported` or `Bad_InvalidArgument` |
| `PATCH` attempted on document bytes | `Bad_NotSupported` |
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

A server conforms to the read-only OPC UA xRegistry binding if it exposes a `RegistryType` root or domain subtype, exposes groups as `GroupType` or subtypes, exposes resource/version documents as `ResourceFileType` or subtypes, and supports Browse, Read and `Open`/`Read`/`Close` sufficient to retrieve registry metadata, collections and resource documents.

A server conforms to the writable OPC UA xRegistry binding if, in addition to read-only conformance, it supports the applicable FileTransfer creation and mutation Methods (`CreateDirectory`, `CreateFile`, `Delete`, optionally `MoveOrCopy`), writable Properties, and `AddProperty`/`RemoveProperty` on `ResourceFileType` where resource extension attributes or labels are mutable.

A server conforms to the query/export OPC UA xRegistry binding if it implements the request-flag mappings it advertises in `Capabilities`, including Browse continuation point pagination, Query or equivalent filtering where advertised, and export serialization that follows the xRegistry document shape.

A client conforms if it can select a `RegistryType` root, resolve xRegistry paths to AddressSpace nodes, use Browse/Read/FileTransfer operations for `GET`, use Write/Call operations for advertised write capabilities, interpret StatusCodes according to §10, and serialize or consume xRegistry document representations according to §8.

A conforming implementation shall not require any node or Method name that is not defined by [*OPC UA — xRegistry*](OPC-UA-xRegistry.md), OPC 10000-20, or its own domain companion specification.
