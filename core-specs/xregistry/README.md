# OPC UA xRegistry (abstract base)

This folder contains the specification and generated NodeSet for the abstract **OPC UA — xRegistry** companion model: a reusable OPC UA type system that projects a [xRegistry](https://github.com/xregistry/spec) registry onto the OPC UA AddressSpace as folders and files.

A registry and its groups are `FolderType` folders; a resource/version document *is* a `FileType` file. The base defines four ObjectTypes — `RegistryType`, `GroupType`, `ResourceType`, `AttributesType` — plus the common xRegistry attributes as Properties, a `Labels` (`AttributesType`) container whose `AddAttribute`/`RemoveAttribute` Methods add/remove individual browsable label Properties, auto-bootstrap, symbolic entity identifiers derived from a domain source identity beside a Mandatory human-readable `Name`, the three xRegistry representations (files / API server / document), and federation via `ExpandedNodeId`. The model is **domain-neutral**: concrete registries subtype these base types. The [Schema Registry](../../cloud-specs/schema-registry/), the [OpenUSD artifact registry](../../metaverse-specs/openusd-binding/) and the [WoT Thing-Description registry](../../wot-specs/WoT-Connectivity/) are the domain extensions built on it.

The model version is **0.3.0** (`2026-07-31`); a domain NodeSet that subtypes these types declares it as a `<RequiredModel>` at that version.

Files:

- `OPC-UA-xRegistry.md` — the abstract base specification (minimal-first; three representations; federation annex). **Target:** OPC Foundation standardization — the reusable base for domain-specific registries (schema, Asset, Semantic, WoT, …).
- `xRegistry-OPC-UA-Api.md` — the OPC UA API binding for xRegistry (a self-contained peer of the xRegistry HTTP binding, defined in xRegistry core/primer terms). **Target:** an xRegistry submission as `core/opcua.md`, or an xRegistry extension proposal. **Submitted** as [xregistry/spec#511](https://github.com/xregistry/spec/pull/511).
- `Opc.Ua.XRegistry.NodeSet2.xml` — generated base NodeSet.
- `Opc.Ua.XRegistry.NodeIds.csv` — generated NodeIds.
- `tools/model-reference.md` — generated Annex A (embedded in the spec).

Regenerate and validate:

```powershell
python core-specs\xregistry\tools\build_model.py
python core-specs\xregistry\tools\validate_local.py
```

Draft numeric NodeIds use the provisional `63000+` block in `http://opcfoundation.org/UA/xRegistry/`; final NodeIds are assigned by the OPC Foundation.
