# OPC UA xRegistry (abstract base)

This folder redirects to the two bodies that maintain the xRegistry work. The abstract **OPC UA — xRegistry** companion model is under OPC Foundation review, and the OPC UA protocol binding for the xRegistry API is maintained by the xRegistry project.

A registry and its groups are `FolderType` folders; a resource/version document *is* a `FileType` file. The base defines four ObjectTypes — `RegistryType`, `GroupType`, `ResourceType`, `AttributesType` — plus the common xRegistry attributes as Properties, a `Labels` (`AttributesType`) container whose `AddAttribute`/`RemoveAttribute` Methods add/remove individual browsable label Properties, auto-bootstrap, symbolic entity identifiers derived from a domain source identity beside a Mandatory human-readable `Name`, the three xRegistry representations (files / API server / document), and federation via `ExpandedNodeId`. The model is **domain-neutral**: concrete registries subtype these base types. The [Schema Registry](../../source/cloud-specs/schema-registry), the OpenUSD artifact registry and the WoT Thing-Description registry are domain extensions built on it.

The model version is **0.4.0** (`2026-08-31`); a domain NodeSet that subtypes these types declares it as a `<RequiredModel>` at that version.

## Where the base specification lives

The base specification and everything generated from it — `OPC-UA-xRegistry.md`, `Opc.Ua.XRegistry.NodeSet2.xml`, `Opc.Ua.XRegistry.NodeIds.csv`, the generated Annex A under `tools/`, and the Word rendering — are **under OPC Foundation review** and live in [`OPCF-Members/spec-drafts`](https://github.com/OPCF-Members/spec-drafts) under `core-specs/xregistry/`. **Target:** OPC Foundation standardization — the reusable base for domain-specific registries (schema, Asset, Semantic, WoT, …). Regeneration and validation run there.

OPC Foundation members can [request access](https://github.com/OPCF-Members/Help), and can populate the private tree beside this one with `git submodule update --init spec-drafts`.

## OPC UA protocol binding

The [xRegistry OPC UA API](https://github.com/xregistry/spec/blob/main/workingdrafts/bindings/opcua.md) is the canonical OPC UA protocol binding. It was merged through [xregistry/spec#511](https://github.com/xregistry/spec/pull/511); this repository does not carry a second copy.

Draft numeric NodeIds use the provisional `63000+` block in `http://opcfoundation.org/UA/xRegistry/`; final NodeIds are assigned by the OPC Foundation.
