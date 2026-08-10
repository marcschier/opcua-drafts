# OPC UA xRegistry (abstract base)

This folder holds the OPC UA API binding for [xRegistry](https://github.com/xregistry/spec). The abstract **OPC UA — xRegistry** companion model it builds on — a reusable OPC UA type system that projects an xRegistry registry onto the OPC UA AddressSpace as folders and files — is under OPC Foundation review, and is described below because everything here depends on it.

A registry and its groups are `FolderType` folders; a resource/version document *is* a `FileType` file. The base defines four ObjectTypes — `RegistryType`, `GroupType`, `ResourceType`, `AttributesType` — plus the common xRegistry attributes as Properties, a `Labels` (`AttributesType`) container whose `AddAttribute`/`RemoveAttribute` Methods add/remove individual browsable label Properties, auto-bootstrap, symbolic entity identifiers derived from a domain source identity beside a Mandatory human-readable `Name`, the three xRegistry representations (files / API server / document), and federation via `ExpandedNodeId`. The model is **domain-neutral**: concrete registries subtype these base types. The [Schema Registry](../../cloud-specs/schema-registry/), the <!-- release-spec-link:W09wZW5VU0QgYXJ0aWZhY3QgcmVnaXN0cnldKC4uLy4uL21ldGF2ZXJzZS1zcGVjcy9vcGVudXNkLWJpbmRpbmcvKQ== -->OpenUSD artifact registry<!-- /release-spec-link --> and the <!-- release-spec-link:W1dvVCBUaGluZy1EZXNjcmlwdGlvbiByZWdpc3RyeV0oLi4vLi4vd290LXNwZWNzL1dvVC1Db25uZWN0aXZpdHkvKQ== -->WoT Thing-Description registry<!-- /release-spec-link --> are the domain extensions built on it.

The model version is **0.3.0** (`2026-07-31`); a domain NodeSet that subtypes these types declares it as a `<RequiredModel>` at that version.

## Where the base specification lives

The base specification and everything generated from it — `OPC-UA-xRegistry.md`, `Opc.Ua.XRegistry.NodeSet2.xml`, `Opc.Ua.XRegistry.NodeIds.csv`, the generated Annex A under `tools/`, and the Word rendering — are **under OPC Foundation review** and live in [`OPCF-Members/spec-drafts`](https://github.com/OPCF-Members/spec-drafts) under `core-specs/xregistry/`. **Target:** OPC Foundation standardization — the reusable base for domain-specific registries (schema, Asset, Semantic, WoT, …). Regeneration and validation run there.

OPC Foundation members can [request access](https://github.com/OPCF-Members/Help), and can populate the private tree beside this one with `git submodule update --init spec-drafts`.

## What stays here

- `xRegistry-OPC-UA-Api.md` — the OPC UA API binding for xRegistry (a self-contained peer of the xRegistry HTTP binding, defined in xRegistry core/primer terms). **Target:** an xRegistry submission as `core/opcua.md`, or an xRegistry extension proposal. **Submitted** as [xregistry/spec#511](https://github.com/xregistry/spec/pull/511).

It stays because it is proposed to xregistry.org rather than to the OPC Foundation, so it is not part of the OPC Foundation review.

Draft numeric NodeIds use the provisional `63000+` block in `http://opcfoundation.org/UA/xRegistry/`; final NodeIds are assigned by the OPC Foundation.
