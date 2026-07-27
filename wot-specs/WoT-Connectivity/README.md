# OPC UA — WoT Connectivity

A **registry-first** revision **1.1** of the OPC UA companion specification for Web of Things (WoT) connectivity. Instead of a flat asset-connection manager, WoT Connectivity 1.1 layers a W3C **Thing Model / Thing Description document registry** over the abstract [OPC UA — xRegistry](../../core-specs/xregistry/) base model and treats the stored documents and their versions as the single source of truth from which the OPC UA AddressSpace and any code-behind are **derived**. It is an **additive** revision in the same published namespace: the full OPC 10100-1 v1.02 model is incorporated into one combined NodeSet and the superseded 1.02 surface is marked deprecated.

> Experimental and non-normative, intended for submission to the OPC Foundation WoT Working Group. Nothing here is official or endorsed by the OPC Foundation or the W3C; the additive registry NodeIds (the `64000+` block) are provisional and used for prototyping only.

## What it is

- `WoTRegistryType` (subtype of xRegistry `RegistryType`) is a well-known `WoTRegistry` Object under the **Server** object (`i=2253`). It holds `ThingDescriptionGroupType` / `ThingModelGroupType` groups whose files are `ThingDescriptionFileType` / `ThingModelFileType` resources — concrete subtypes of the abstract `WoTDocumentType` (an xRegistry `ResourceType`, i.e. a `FileType`).
- **Thing Models project to OPC UA types; Thing Descriptions project to OPC UA instances**; affordances become Variables/Methods/EventTypes, links become References (including a parent `uav:componentOf`), and forms become protocol **binder plans**. The projection is a **shadow-switched, generational, idempotent** derivation of the canonical documents.
- Validation outcomes, load state, desired/active version, content digest, materialized nodes and selected bindings are exposed on the registry and document nodes; a `Refresh` Method drives explicit re-projection with detailed summary/results; resource lifecycle and refresh-completed **events** flow along a Server → registry → group → resource notifier chain.
- The revised [OPC UA — WoT Binding](../WoT-Binding/) `uav` JSON-LD vocabulary is a **normative dependency** governing the document→node mapping, but **not** a NodeSet `RequiredModel` (it is a vocabulary, not an information model).

## Incorporated OPC 10100-1 v1.02 model

The published **OPC 10100-1 v1.02** WoT Connectivity model (namespace `http://opcfoundation.org/UA/WoT-Con/`, v1.02.0) is **incorporated into the same combined NodeSet and namespace**, preserving every published NodeId (`1..172`), type and method signature (`CreateAsset`, `DeleteAsset`, `DiscoverAssets`, `CreateAssetForEndpoint`, `ConnectionTest`, `WoTFile`/`CloseAndUpdate`, `SupportedWoTBindings`, `HasWoTComponent`) and the well-known `WoTAssetConnectionManagement` object. Because the registry supersedes the flat asset surface, those types are marked `ReleaseStatus="Deprecated"` (per OPC 11030) — deprecated, not removed, so existing 1.02 clients keep working. The 1.02 sources are pinned under [`legacy/`](legacy/) and incorporated deterministically by the generator; §13 / Annex B of the specification record how the deprecated surface is backed by the registry without changing any signature.

## Files

- `OPC-UA-WoT-Connectivity.md` — the full standalone 1.1 specification (Annex A is the embedded generated node reference; Annexes B/C are informative).
- `Opc.Ua.WoTCon.NodeSet2.xml` — generated combined NodeSet (requires the Core and xRegistry base NodeSets as `<RequiredModel>`).
- `Opc.Ua.WoTCon.NodeIds.csv` — generated NodeIds (the preserved 1.02 rows `1..172` plus the additive registry rows).
- `legacy/WotConnection.xml` / `legacy/WotConnection.csv` — the pinned OPC 10100-1 v1.02 authoring sources (source input, not hand-copied output).
- `tools/build_model.py` — the canonical generator (single source of truth; parses the pinned legacy sources).
- `tools/model-reference.md` — generated Annex A (embedded verbatim in the spec).
- `tools/validate_local.py` — the deterministic, standard-library structural validator.
- `examples/` — a Thing Model, a matching Thing Description, an intentionally invalid Thing Description, and a representative refresh-results document.

## Namespace and NodeIds

One NamespaceUri `http://opcfoundation.org/UA/WoT-Con/` at model version `1.1.0` (namespace index 2 in the NodeSet, after Core at 0 and the xRegistry base at 1). The incorporated 1.02 nodes keep their published NodeIds `1..172`; the additive registry nodes use a provisional **64000+** block (types) with members allocated append-only from **64500**. Final registry NodeIds are assigned by the OPC Foundation.

## Regenerate and validate

The xRegistry base must be generated first, because this NodeSet references it:

```powershell
python core-specs\xregistry\tools\build_model.py
python core-specs\xregistry\tools\validate_local.py
python wot-specs\WoT-Connectivity\tools\build_model.py
python wot-specs\WoT-Connectivity\tools\validate_local.py
```

The validator checks XML/CSV consistency, that references resolve against the own namespace and the loaded xRegistry base `NodeIds.csv`, the Server→WoTRegistry notifier topology, that each type has a `HasSubtype` inverse and each Structure its encodings, and that the generated Annex A is embedded verbatim in the specification. It additionally **proves the 1.02 preservation**: the first 172 CSV rows match `legacy/WotConnection.csv` exactly, every concrete legacy id is present with its pinned NodeClass, the deprecated management surface carries `ReleaseStatus="Deprecated"`, the callable well-known `WoTAssetConnectionManagement` is present, and the combined NodeSet declares one namespace at model version 1.1.0. For full base-namespace NodeId resolution, place `UA.NodeIds.csv` in `tools/ref/` (this local validation aid is gitignored).
