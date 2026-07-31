# OPC UA — OpenUSD Binding (Part 1)

**Release 0.6.0 — Draft** · namespace `http://opcfoundation.org/UA/OpenUSD/`

This folder contains the specification and generated NodeSet for **Part 1** of the *OPC UA — OpenUSD* work: a small, generic **representation and binding layer** between an OPC UA address space and an OpenUSD model.

It answers two questions a renderer needs and OPC UA cannot otherwise express: **which composed USD prim represents a given OPC UA Object**, and **which live Variable values drive which USD attributes** (and, where authorized, which USD-side intents command OPC UA back). It is deliberately domain-agnostic — it binds the Objects and Variables of *any* companion specification (Pumps, Robotics, Machinery, …) and **does not require modifying the USD asset**.

The USD scene stays outside OPC UA. A connector browses the well-known `Server/OpenUSD` facility, resolves the bindings, subscribes, and writes the values into the stage. If you want the scene graph itself to live in the address space, that is [Part 2](../openusd-scene/).

## Capability groups

- **Representation (identity).** A mandatory `Server/OpenUSD` discovery root plus an `OpenUsdRepresentation` AddIn tying an Object to a canonical composed prim path on a named stage. Identity only — it carries no values.
- **Live property binding (telemetry).** A read-only mapping from a source Variable `Value` — resolved by NodeId, RelativePath, or **semantic id** (ECLASS / IEC CDD) — to a target USD attribute, with conversion and quality/timestamp/persistence hints. Binds *existing* domain Variables; it does not duplicate process data.
- **Commands (opt-in, authorized).** A fail-closed, single-writer path from a USD-side intent to an OPC UA write or `Method` call.
- **Alarms and history.** The same binding type specialized for A&C condition aspects and for authoring USD time samples from `HistoryRead`.
- **Composition.** Composing component Objects into the parent prim tree — nested, referenced, payloaded or `instanceable` — including **dynamic** reconciliation on model-change events and **cross-server** resolution by federation.
- **Asset content delivery (§7.11).** A server can serve the artist-authored USD closure itself, so a connector needs no external asset repository.

### 0.4.0 — the artifact registry

Release 0.4.0 rebases asset delivery on [*OPC UA — xRegistry*](../../core-specs/xregistry/OPC-UA-xRegistry.md), which becomes a **`RequiredModel`**. Served artifacts now live in an `OpenUsdArtifactRegistryType` at `Server/OpenUSD/Artifacts`, and a stage's `Assets` folder becomes a **view** that `Organizes` the subset it needs — so an artifact shared by several stages exists once, and gains versions, change detection, labels and federation.

This is the one place the model is no longer self-contained on base OPC UA alone, and it moves this namespace to **index 2** (index 1 is xRegistry). The streaming contract is unchanged: `ResourceType` is itself a Part 5 `FileType`, so an artifact node still *is* the file.

## Files

- `OPC-UA-OpenUSD-Bindings.md` — the specification.
- `Opc.Ua.OpenUsd.NodeSet2.xml` — generated NodeSet.
- `Opc.Ua.OpenUsd.NodeIds.csv` — generated NodeId assignments.
- `xRegistry-OpenUsd.md` — *OpenUSD Artifact Registry Service*: the artifact registry of §7.11 defined as a standalone **xRegistry domain specification**, structured for submission to the [xRegistry](https://github.com/xregistry/spec) project. It is the wire-format peer of §7.11 — same collections, same attributes, same identifier rules — so the two projections federate. It does not depend on OPC UA.
- `xRegistry-OpenUsd.model.json` — the authoritative xRegistry model for that spec (becomes `model.json` on submission).
- `pumps/` — implementer addendum + instance-overlay NodeSet for the pumps example.
- `robotics/` — implementer addendum + instance-overlay NodeSet for the robotics example.

Supporting material lives under [`../extras/openusd-binding/`](../extras/openusd-binding/): `tools/` (the generator, the validator, and the generated Annex A) and `examples/` (the USD assets, binding descriptors, Python writers, fallback renderers and **end-to-end guides** for pumps and robotics). The emitted xRegistry artifact registry for those examples is in [`../extras/openusd-artifacts/`](../extras/openusd-artifacts/).

## Conformance

23 conformance units, each independently testable, grouped into five profiles:

| Profile | Adds |
|---|---|
| **OpenUSD Representation Server** | discovery, stage, representation, registry |
| **OpenUSD Live Rendering Server** | + bindings, conversion, quality |
| **OpenUSD Interactive Server** | + authorized commands (and typically alarms) |
| **OpenUSD Composite Server** | + composition, dynamic and cross-server |
| **OpenUSD Artifact Server** | + asset delivery and the artifact registry |

## Regenerate and validate

```powershell
python metaverse-specs\extras\openusd-binding\tools\build_model.py
python metaverse-specs\extras\openusd-binding\tools\validate_local.py
```

Edit `tools/build_model.py` — the single source of truth — never the generated NodeSet or CSV. Append new members at the **end**; a mid-file insert silently renumbers every NodeId after it.

Draft numeric NodeIds are provisional (ObjectTypes `1001+`, DataTypes `3001+`, instance declarations `6001+`); final NodeIds are assigned by the OPC Foundation.
