# OPC UA — WoT Connectivity V2

A complete, standalone draft **registry-first** revision of the OPC UA companion specification for Web of Things (WoT) connectivity. Instead of a flat asset-connection manager, WoT Connectivity V2 layers a W3C **Thing Model / Thing Description document registry** over the abstract [OPC UA — xRegistry](../../core-specs/xregistry/) base model and treats the stored documents and their versions as the single source of truth from which the OPC UA AddressSpace and any code-behind are **derived**.

> Experimental and non-normative. Nothing here is official or endorsed by the OPC Foundation or the W3C; the provisional namespace `http://opcfoundation.org/UA/WoT-Con/V2/` and all numeric NodeIds are used for prototyping only.

## What it is

- `WoTRegistryType` (subtype of xRegistry `RegistryType`) is a well-known `WoTRegistry` Object under the **Server** object (`i=2253`). It holds `ThingDescriptionGroupType` / `ThingModelGroupType` groups whose files are `ThingDescriptionFileType` / `ThingModelFileType` resources — concrete subtypes of the abstract `WoTDocumentType` (an xRegistry `ResourceType`, i.e. a `FileType`).
- **Thing Models project to OPC UA types; Thing Descriptions project to OPC UA instances**; affordances become Variables/Methods/EventTypes, links become References, and forms become protocol **binder plans**. The projection is a **shadow-switched, generational, idempotent** derivation of the canonical documents.
- Validation outcomes, load state, desired/active version, content digest, materialized nodes and selected bindings are exposed on the registry and document nodes; a `Refresh` Method drives explicit re-projection with detailed summary/results; resource lifecycle and refresh-completed **events** flow along a Server → registry → group → resource notifier chain.
- The revised [OPC UA — WoT Binding](../WoT-Binding/) `uav` JSON-LD vocabulary is a **normative dependency** governing the document→node mapping, but **not** a NodeSet `RequiredModel` (it is a vocabulary, not an information model).

## Legacy profile

Every feature and scenario of the published **OPC 10100-1 v1.02** WoT Connectivity model (namespace `http://opcfoundation.org/UA/WoT-Con/`, v1.02.0) is preserved as a separately implementable **legacy profile** with its exact published namespace, types and method signatures (`CreateAsset`, `DeleteAsset`, `DiscoverAssets`, `CreateAssetForEndpoint`, `ConnectionTest`, `WoTFile`/`CloseAndUpdate`, `SupportedWoTBindings`, `HasWoTComponent`). The V2 NodeSet does **not** redefine or renumber any 1.02 node; the specification (Section 13, Annex B) records how the legacy surface adapts onto the registry without changing any signature.

## Files

- `OPC-UA-WoT-Connectivity.md` — the full standalone V2 specification (Annex A is the embedded generated node reference; Annexes B/C are informative).
- `Opc.Ua.WoTConV2.NodeSet2.xml` — generated NodeSet (requires the Core and xRegistry base NodeSets as `<RequiredModel>`).
- `Opc.Ua.WoTConV2.NodeIds.csv` — generated NodeIds.
- `tools/build_model.py` — the canonical generator (single source of truth).
- `tools/model-reference.md` — generated Annex A (embedded verbatim in the spec).
- `tools/validate_local.py` — the deterministic, standard-library structural validator.
- `examples/` — a Thing Model, a matching Thing Description, an intentionally invalid Thing Description, and a representative refresh-results document.

## Namespace and NodeIds

Provisional NamespaceUri `http://opcfoundation.org/UA/WoT-Con/V2/` (namespace index 2 in the NodeSet, after Core at 0 and the xRegistry base at 1). Draft numeric NodeIds use a dedicated provisional **64000+** block (types) with members allocated append-only from **64500**; final NodeIds are assigned by the OPC Foundation.

## Regenerate and validate

The xRegistry base must be generated first, because this NodeSet references it:

```powershell
python core-specs\xregistry\tools\build_model.py
python core-specs\xregistry\tools\validate_local.py
python wot-specs\WoT-Connectivity\tools\build_model.py
python wot-specs\WoT-Connectivity\tools\validate_local.py
```

The validator checks XML/CSV consistency, that references resolve against the own namespace and the loaded xRegistry base `NodeIds.csv`, the Server→WoTRegistry notifier topology, that each type has a `HasSubtype` inverse and each Structure its encodings, and that the generated Annex A is embedded verbatim in the specification. For full base-namespace NodeId resolution, place `UA.NodeIds.csv` in `tools/ref/` (this local validation aid is gitignored).
