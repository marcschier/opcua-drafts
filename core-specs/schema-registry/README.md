# OPC UA Schema Registry

This folder contains the specification and generated NodeSet companion extension for an in-server OPC UA Schema Registry.

The Schema Registry is a **domain extension of the abstract [OPC UA — xRegistry](../xregistry/) companion model**: `SchemaRegistryType`, `SchemaGroupType` and `SchemaFileType` subtype the base `RegistryType`, `GroupType` and `ResourceType`, so the registry and its schema groups are OPC UA `FolderType` folders and its schema documents are `FileType` files. Because the base OPC UA API is a first-class xRegistry binding, an OPC UA Schema Registry is discovered, downloaded, registered, browsed and federated the **same way as an HTTP xRegistry Schema Registry** (peer bindings; the HTTP correspondence is informative, in the spec's Annex D). It is a **stand-alone server capability**, exposed as a well-known `SchemaRegistry` Object under the **Server** object (`i=2253`) — a server does **not** have to support PubSub to be a schema registry; a PubSub-capable server may additionally reference it from `PublishSubscribe`, and the PubSub DataSet schema behaviour is isolated in the spec's optional Annex C profile. Each schema document is also addressable at runtime by an Opaque NodeId in the Schema Registry namespace whose Identifier bytes are the raw on-wire `SchemaId` fingerprint.

Files:

- `OPC-UA-Schema-Registry.md` — the specification (extends the xRegistry base; minimal-first; SchemaId fast path; evolution/versioning; resolution flow; federation).
- `Opc.Ua.SchemaRegistry.NodeSet2.xml` — generated NodeSet (requires the xRegistry base NodeSet as a `<RequiredModel>`).
- `Opc.Ua.SchemaRegistry.NodeIds.csv` — generated NodeIds.
- `tools/model-reference.md` — generated Annex A (embedded in the spec).

Regenerate and validate (the xRegistry base must be generated first, as this NodeSet references it):

```powershell
python core-specs\xregistry\tools\build_model.py
python core-specs\xregistry\tools\validate_local.py
python core-specs\schema-registry\tools\build_model.py
python core-specs\schema-registry\tools\validate_local.py
```

Draft numeric NodeIds use the provisional `62000+` block in `http://opcfoundation.org/UA/SchemaRegistry/` (namespace index 2 in the NodeSet, after the xRegistry base at index 1); final NodeIds are assigned by the OPC Foundation.
