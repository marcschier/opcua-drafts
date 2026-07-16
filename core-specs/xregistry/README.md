# OPC UA xRegistry (abstract base)

This folder contains the specification and generated NodeSet for the abstract **OPC UA — xRegistry** companion model: a reusable OPC UA type system that projects a [xRegistry](https://github.com/xregistry/spec) registry onto the OPC UA **FileTransfer** model.

A registry and its groups are `FileDirectoryType` directories; a resource/version document *is* a `FileType` file. The base defines three ObjectTypes — `RegistryType`, `GroupType`, `ResourceFileType` — plus the common xRegistry attributes as Properties, `AddProperty`/`RemoveProperty` methods, auto-bootstrap, the three xRegistry representations (files / API server / document), and federation via `ExpandedNodeId`. The model is **domain-neutral**: concrete registries subtype these base types. The [Schema Registry](../schema-registry/) is the first such extension; a WoT Thing-Description registry is designed for but not yet built.

Files:

- `OPC-UA-xRegistry.md` — the abstract base specification (minimal-first; three representations; federation annex).
- `OPC-UA-xRegistry-Binding.md` — the generic OPC UA protocol binding for the xRegistry API, mirroring the xRegistry HTTP binding (`core/http.md`) for submission to the xRegistry organization.
- `Opc.Ua.XRegistry.NodeSet2.xml` — generated base NodeSet.
- `Opc.Ua.XRegistry.NodeIds.csv` — generated NodeIds.
- `tools/model-reference.md` — generated Annex A (embedded in the spec).

Regenerate and validate:

```powershell
python core-specs\xregistry\tools\build_model.py
python core-specs\xregistry\tools\validate_local.py
```

Draft numeric NodeIds use the provisional `63000+` block in `http://opcfoundation.org/UA/xRegistry/`; final NodeIds are assigned by the OPC Foundation.
