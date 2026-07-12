# OPC UA Pumps — OpenUSD Bindings Addendum

**Implementer Annex to *OPC UA — OpenUSD Bindings* (Release 0.1.0 — Draft).**

> This addendum is the **implementer (Pump) annex** for the generic *OPC UA — OpenUSD Bindings* companion model. All Pump-specific and end-to-end detail lives here; the base specification (`../OPC-UA-OpenUSD-Bindings.md`) remains domain-agnostic. It shows how a `PumpType` instance (OPC 40223 Pumps) is bound to an OpenUSD prim and how three live measurements drive the render. The machine-readable source of truth is `../../extras/openusd-binding/examples/pumps/Pumps.OpenUsdBinding.json`; a runnable USD writer is `../../extras/openusd-binding/examples/pumps/usd_writer.py`; the C# end-to-end validation lives in the `marcschier/UA-.NETStandard` `PumpDeviceIntegrationServer` sample.

---

## 1 Scope

This addendum binds one `PumpType` instance to a USD prim and defines three read-only live bindings (Part 2, `UaToUsdTelemetry`): impeller rotation, body colour from temperature, and visibility from running state. It is illustrative; a concrete server supplies the exact source BrowsePaths and stage identifiers.

## 2 Normative references

- *OPC UA — OpenUSD Bindings*, Release 0.1.0 (the base specification).
- [OPC 40223](https://reference.opcfoundation.org/specs/OPC-40223/) — OPC UA for Pumps and Vacuum Pumps (`PumpType`, namespace `http://opcfoundation.org/UA/Pumps/`).
- [OPC 10000-100](https://reference.opcfoundation.org/specs/OPC-10000-100/) — Devices (DI), the base of `PumpType`.

## 3 How the bindings are applied

A `PumpType` instance (for example `Pump101`) gains an OpenUSD representation by composing an `OpenUsdRepresentation` AddIn (`HasAddIn`) that targets a stage and a prim path, and by carrying the live bindings as children of that AddIn:

```text
Pump101 : PumpType
  └─ HasAddIn OpenUsdRepresentation : OpenUsdRepresentationType
       Stage    = NodeId(Server/OpenUSD/Stages/PlantStage)
       PrimPath = "/Plant/Pumps/P101"
       ├─ Speed              : OpenUsdLiveBindingType
       ├─ BearingTemperature : OpenUsdLiveBindingType
       └─ Running            : OpenUsdLiveBindingType
```

The AddIn is also `Organizes`-listed from `Server/OpenUSD/Representations`, so a generic connector discovers it without knowing anything about pumps. Each binding's source resolves **relative to `Pump101`** via `SourceBrowsePath`, so the same declaration applies to every pump instance; the effective runtime key is `(Pump101, BindingDefinitionId)`.

## 4 OpenUSD bindings for `PumpType`

| Binding | Source (relative to the Pump) | Target property | USD type | RenderTargetKind | Conversion |
|---|---|---|---|---|---|
| **Speed** | `/Operational/Measurements/RotationalSpeed` | `xformOp:rotateZ` | `double` | Rotation | rpm → per-tick degrees (Scale 0.06) |
| **BearingTemperature** | `/Operational/Measurements/BearingTemperature` | `primvars:displayColor` (on `…/Body`) | `color3f` | DisplayColor | °C → blue→red gradient (connector mapping) |
| **Running** | `/Operational/IsRunning` | `visibility` | `token` | Visibility | bool → `inherited`/`invisible` |

Notes:

- **Speed** targets the represented prim itself (empty `TargetPrimPath`); the connector integrates rpm into an angle each frame. `xformOp:rotateZ` must appear in the prim's `xformOpOrder`.
- **BearingTemperature** targets a child prim (`…/Body`) and drives a colour; the numeric-to-`color3f` mapping is a connector responsibility declared by `RenderTargetKind = DisplayColor` and `ValueSemanticUri`.
- **Running** toggles visibility; a non-Good source value uses the binding's `BadQualityAction` (default `Skip`).

## 4.1 Reference implementation (validated end-to-end)

The `PumpDeviceIntegrationServer` sample in `marcschier/UA-.NETStandard` realizes this design and validates it with an automated end-to-end test (`PumpOpenUsdE2eTests`, three passing cases: the companion model is served, the representation and its bindings are discoverable through the registry, and live values flow through a generic connector into a mock USD sink). Because the sample's `PumpType` instance (`Pump #1`) exposes the OPC 40223 measurement surface, the reference bindings use the measurements actually present rather than the illustrative `Speed`/`Running` above:

| Reference binding | Source (Pump measurement) | Target property | USD type | RenderTargetKind |
|---|---|---|---|---|
| **MassFlowSpin** | `MassFlow` | `xformOp:rotateZ` (on the represented prim) | `double` | Rotation |
| **BearingTempColor** | `BearingTemperature` | `primvars:displayColor` (on `…/Body`) | `color3f` | DisplayColor |
| **DiffPressureEmissive** | `DifferentialPressure` | `inputs:emissiveColor` | `color3f` | EmissiveColor |

Implementer findings from the source-generated OPC UA .NET model (generic, not Pump-specific — applies to any server built from this companion NodeSet):

- **Attach with a hierarchical ReferenceType.** The generated `CreateInstanceOf…` factories leave `ReferenceTypeId = Null`, which is not a browsable reference. Attach the `OpenUsdRepresentation` AddIn to the represented Object and each `OpenUsdLiveBinding` to the representation with an explicit `HasComponent` (or `HasAddIn`) so the nodes are browsable.
- **Instantiate bindings via the placeholder.** Create each binding from the representation's `<Binding>` placeholder (the generated `AddxBinding_` helper), which yields a concrete instance with a valid BrowseName and reference type.
- **Optional members are not auto-created.** Only mandatory members exist after instantiation; the optional members a connector reads (`SourceNodeId`, `RenderTargetKind`, `Scale`, `BadQualityAction`) must be explicitly created so they carry a BrowseName and are browsable/readable.
- **Discovery uses the registry, not the represented object.** A connector enumerates representations from `Server/OpenUSD/Representations` (Organizes) — it does not need to know or reach the represented Object, confirming the Part 1 discovery facility is sufficient on its own.

## 5 Where the bindings live

- **Machine-readable descriptor:** `../../extras/openusd-binding/examples/pumps/Pumps.OpenUsdBinding.json`.
- **Illustrative instance overlay (NodeSet):** `Opc.Ua.Pumps.OpenUsdBinding.NodeSet2.xml` (this folder) — a concrete `Pump101` with the AddIn and the three bindings, for browsing/inspection.
- **Runnable USD writer:** `../../extras/openusd-binding/examples/pumps/usd_writer.py` (+ generated `live.usda`).
- **C# end-to-end:** the `PumpDeviceIntegrationServer` sample in `marcschier/UA-.NETStandard` exposes the representation + bindings, and `PumpOpenUsdE2eTests` starts the server via the generic host, connects a client session, discovers the representation and bindings through `Server/OpenUSD/Representations`, subscribes to the bound source Variables, and drives a generic connector into a mock USD sink (asserted in CI). A Python `pxr` writer authors a real `live.usda` locally (Omniverse rendering is out of CI scope).

## 6 Deliverables

| Artifact | Path |
|---|---|
| This addendum | `core-specs/openusd-binding/pumps/OPC-UA-Pumps-OpenUSD-Bindings-Addendum.md` |
| Instance overlay | `core-specs/openusd-binding/pumps/Opc.Ua.Pumps.OpenUsdBinding.NodeSet2.xml` |
| Descriptor | `core-specs/extras/openusd-binding/examples/pumps/Pumps.OpenUsdBinding.json` |
| USD writer + example stage | `core-specs/extras/openusd-binding/examples/pumps/usd_writer.py`, `live.usda` |
