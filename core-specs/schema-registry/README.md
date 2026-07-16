# OPC UA Schema Registry

This folder contains the specification and generated NodeSet companion extension for an in-server OPC UA Schema Registry.

The Schema Registry is a **domain extension of the abstract [OPC UA — xRegistry](../xregistry/) companion model**: `SchemaRegistryType`, `SchemaGroupType` and `SchemaFileType` subtype the base `RegistryType`, `GroupType` and `ResourceType`, so the registry and its schema groups are OPC UA `FolderType` folders and its schema documents are `FileType` files. It is exposed as a well-known `SchemaRegistry` Object under Part 14 `PublishSubscribe` (`i=14443`). Each schema document is also addressable at runtime by an Opaque NodeId in the Schema Registry namespace whose Identifier bytes are the raw on-wire `SchemaId` fingerprint.

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
