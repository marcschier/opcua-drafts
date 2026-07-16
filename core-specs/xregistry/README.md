# OPC UA xRegistry (abstract base)

This folder contains the specification and generated NodeSet for the abstract **OPC UA — xRegistry** companion model: a reusable OPC UA type system that projects a [xRegistry](https://github.com/xregistry/spec) registry onto the OPC UA **FileTransfer** model.

A registry and its groups are `FileDirectoryType` directories; a resource/version document *is* a `FileType` file. The base defines three ObjectTypes — `RegistryType`, `GroupType`, `ResourceType` — plus the common xRegistry attributes as Properties, `AddAttribute`/`RemoveAttribute` methods, auto-bootstrap, the three xRegistry representations (files / API server / document), and federation via `ExpandedNodeId`. The model is **domain-neutral**: concrete registries subtype these base types. The [Schema Registry](../schema-registry/) is the first such extension; Asset, Semantic and WoT Thing-Description registries are designed for but not yet built.

Files:

- `OPC-UA-xRegistry.md` — the abstract base specification (minimal-first; three representations; federation annex). **Target:** OPC Foundation standardization — the reusable base for domain-specific registries (schema, Asset, Semantic, WoT, …).
- `xRegistry-OPC-UA-Api.md` — the OPC UA API binding for xRegistry (a self-contained peer of the xRegistry HTTP binding, defined in xRegistry core/primer terms). **Target:** an xRegistry submission as `core/opcua.md`, or an xRegistry extension proposal.
- `Opc.Ua.XRegistry.NodeSet2.xml` — generated base NodeSet.
- `Opc.Ua.XRegistry.NodeIds.csv` — generated NodeIds.
- `tools/model-reference.md` — generated Annex A (embedded in the spec).

Regenerate and validate:

```powershell
python core-specs\xregistry\tools\build_model.py
python core-specs\xregistry\tools\validate_local.py
```

Draft numeric NodeIds use the provisional `63000+` block in `http://opcfoundation.org/UA/xRegistry/`; final NodeIds are assigned by the OPC Foundation.
