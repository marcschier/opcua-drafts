# OPC UA Pumps — OpenUSD Bindings Addendum

**Implementer Annex to *OPC UA — OpenUSD Bindings* (Release 0.2.0 — Draft).**

> This addendum is the **implementer (Pump) annex** for the generic *OPC UA — OpenUSD Bindings* companion model. All Pump-specific and end-to-end detail lives here; the base specification (`../OPC-UA-OpenUSD-Bindings.md`) remains domain-agnostic. It shows how a `PumpType` instance (OPC 40223 Pumps) is bound to an OpenUSD prim and how three live measurements drive the render. The machine-readable source of truth is `../../extras/openusd-binding/examples/pumps/Pumps.OpenUsdBinding.json`; a runnable USD writer is `../../extras/openusd-binding/examples/pumps/usd_writer.py`; the C# end-to-end validation lives in the `marcschier/UA-.NETStandard` `PumpDeviceIntegrationServer` sample.

---

## 1 Scope

This addendum binds one `PumpType` instance to a USD prim and defines three read-only telemetry bindings (Part 2, `OpenUsdValueChangeBindingType`): impeller rotation from mass flow, body colour from bearing temperature, and status-light glow from differential pressure. It also shows the 0.2 capability bindings on the same pump — an alarm binding (`OpenUsdAlarmBindingType`) driving status-light visibility and an opt-in command binding (`OpenUsdCommandBindingType`) writing a speed setpoint — plus a stage content-integrity digest. It is illustrative; a concrete server supplies the exact source BrowsePaths and stage identifiers.

## 2 Normative references

- *OPC UA — OpenUSD Bindings*, Release 0.2.0 (the base specification).
- [OPC 40223](https://reference.opcfoundation.org/specs/OPC-40223/) — OPC UA for Pumps and Vacuum Pumps (`PumpType`, namespace `http://opcfoundation.org/UA/Pumps/`).
- [OPC 10000-100](https://reference.opcfoundation.org/specs/OPC-10000-100/) — Devices (DI), the base of `PumpType`.

## 3 How the bindings are applied

A `PumpType` instance (for example `Pump101`) gains an OpenUSD representation by composing an `OpenUsdRepresentation` AddIn (`HasAddIn`) that targets a stage and a prim path, and by carrying the live bindings as children of that AddIn:

```text
Pump101 : PumpType
  └─ HasAddIn OpenUsdRepresentation : OpenUsdRepresentationType
       Stage    = NodeId(Server/OpenUSD/Stages/PlantStage)
       PrimPath = "/Plant/Pumps/P101"
       ├─ MassFlowSpin           : OpenUsdValueChangeBindingType   (+SourceSemanticId)
       ├─ BearingTempColor       : OpenUsdValueChangeBindingType
       ├─ DiffPressureEmissive   : OpenUsdValueChangeBindingType
       ├─ AlarmActiveVisibility  : OpenUsdAlarmBindingType
       └─ SpeedSetpointCommand   : OpenUsdCommandBindingType   (opt-in)
```

The AddIn is also `Organizes`-listed from `Server/OpenUSD/Representations`, so a generic connector discovers it without knowing anything about pumps. Each binding's source resolves **relative to `Pump101`** via `SourceBrowsePath` (or, from 0.2, a portable `SourceSemanticId`), so the same declaration applies to every pump instance; the effective runtime key is `(Pump101, BindingDefinitionId)`. The alarm and command bindings target two extra pump Variables — `AlarmActive` (Boolean) and a writable `SpeedSetpoint` (Double) — and the `PlantStage` carries a `RootLayerDigest` (SHA-256) a connector verifies before composing.

## 4 OpenUSD bindings for `PumpType`

| Binding | Source (relative to the Pump) | Target property | USD type | RenderTargetKind | Conversion |
|---|---|---|---|---|---|
| **MassFlowSpin** | `/Operational/Measurements/MassFlow` | `xformOp:rotateZ` (on `…/Impeller`) | `double` | Rotation | flow → rotateZ angle (Scale) |
| **BearingTempColor** | `/Operational/Measurements/BearingTemperature` | `primvars:displayColor` (on `…/Body`) | `color3f` | DisplayColor | °C → blue→red gradient (connector mapping) |
| **DiffPressureEmissive** | `/Operational/Measurements/DifferentialPressure` | `inputs:emissiveColor` (on the status-light material) | `color3f` | EmissiveColor | bar → emissive glow (connector mapping) |

Notes:

- **MassFlowSpin** targets the impeller prim; `xformOp:rotateZ` must appear in that prim's `xformOpOrder`.
- **BearingTempColor** targets a child prim (`…/Body`) and drives a colour; the numeric-to-`color3f` mapping is a connector responsibility declared by `RenderTargetKind = DisplayColor` and `ValueSemanticUri`.
- **DiffPressureEmissive** drives a `UsdPreviewSurface` emissive input; a non-Good source value uses the binding's `BadQualityAction` (default `Skip`).

## 4.1 Reference implementation (validated end-to-end)

The `PumpDeviceIntegrationServer` sample in `marcschier/UA-.NETStandard` realizes this design and validates it with an automated end-to-end test suite (`PumpOpenUsdE2eTests`, ten passing cases): the companion model is served; the facility is browsable from the Server Object; the representation and its five bindings are discoverable through the registry; live telemetry flows through a generic connector into a mock USD sink; the semantic id + signal role are surfaced; the stage `RootLayerDigest` verifies; the alarm binding drives status-light visibility; the command binding is fail-closed by default and writes the server setpoint when enabled; and history replay degrades gracefully on a non-historizing source. Because the sample's `PumpType` instance (`Pump #1`) exposes the OPC 40223 measurement surface, the reference bindings use the measurements actually present rather than the illustrative `Speed`/`Running` above:

| Reference binding | Source (Pump measurement) | Target property | USD type | RenderTargetKind |
|---|---|---|---|---|
| **MassFlowSpin** | `MassFlow` (+ `SourceSemanticId` IRDI) | `xformOp:rotateZ` (on the represented prim) | `double` | Rotation |
| **BearingTempColor** | `BearingTemperature` | `primvars:displayColor` (on `…/Body`) | `color3f` | DisplayColor |
| **DiffPressureEmissive** | `DifferentialPressure` | `inputs:emissiveColor` | `color3f` | EmissiveColor |
| **AlarmActiveVisibility** | `AlarmActive` (supervision alarm ActiveState) | `visibility` (on `…/StatusLight`) | `token` | Visibility |
| **SpeedSetpointCommand** | *(command)* → `SpeedSetpoint` | `inputs:speedSetpoint` (on `…/Impeller`) | `double` | — |

The alarm binding (`OpenUsdAlarmBindingType`, `AlarmAspect = ActiveState`) shows the status light when a supervision alarm is active; the command binding (`OpenUsdCommandBindingType`, `SignalRole = Controllable`) is opt-in — the bridge writes the setpoint only with `--enable-commands` (single-writer, fail-closed). The `PlantStage` publishes a `RootLayerDigest` (`Sha256`) the connector verifies before composing.

Implementer findings from the source-generated OPC UA .NET model (generic, not Pump-specific — applies to any server built from this companion NodeSet):

- **Attach with a hierarchical ReferenceType.** The generated `CreateInstanceOf…` factories leave `ReferenceTypeId = Null`, which is not a browsable reference. Attach the `OpenUsdRepresentation` AddIn to the represented Object and each `OpenUsdLiveBinding` to the representation with an explicit `HasComponent` (or `HasAddIn`) so the nodes are browsable.
- **Instantiate bindings via the placeholder.** Create each binding from the representation's `<Binding>` placeholder (the generated `AddxBinding_` helper), which yields a concrete instance with a valid BrowseName and reference type.
- **Optional members are not auto-created.** Only mandatory members exist after instantiation; the optional members a connector reads (`SourceNodeId`, `RenderTargetKind`, `Scale`, `BadQualityAction`, and the 0.2 members `SignalRole`, `SourceSemanticId`, `AlarmAspect`, `CommandTargetNodeId`, `CommandTriggerPropertyName`) must be explicitly created so they carry a BrowseName and are browsable/readable.
- **Discovery uses the registry, not the represented object.** A connector enumerates representations from `Server/OpenUSD/Representations` (Organizes) — it does not need to know or reach the represented Object, confirming the Part 1 discovery facility is sufficient on its own.

## 4.2 Composition / aggregation (validated)

The sample also exercises the composition model (base spec §5.12–5.14):

- **1:1 (Child).** The pump is composed of an `Impeller` and a `Bearing` component Object, each with its own representation, declared as `One` `<Component>` bindings (`CompositionArc = Child`) that compose the `…/Impeller` and `…/Bearing` child prims.
- **1..n (Instance) + dynamic.** A `ProductionLine` Object aggregates 1..n pumps via a `Many` `<Component>` binding (`CompositionArc = Instance`, `Dynamic = true`), authoring an instanceable reference prim per pump under `/Plant/Line1/Pumps`. A pump is added and removed at runtime; with `ModelChangeEmissionEnabled` the server emits `GeneralModelChangeEvent`s and the connector reconciles the prims (new prim authored; removed prim set `active = false`).
- **Cross-server (Reference).** A `<Component>` binding carries `ComponentServerUri`/`ComponentEndpointUrl` for an OEM pump on another server; the connector composes its reference prim and (given a remote session factory) federates to drive its bindings.

Composition-specific implementer findings (generic):

- **Reach the represented Object via the aggregating reference.** Resolve a representation's owner by browsing the inverse of `HasComponent`/`HasAddIn` (`Aggregates`), not any hierarchical reference — otherwise the `Organizes` link from the registry is mistaken for the parent.
- **Process every representation.** Composition spans the aggregating representation and each component's own representation, so a connector iterates all registry entries, not just the first.
- **One `OfType` filter covers both model-change events.** `GeneralModelChangeEventType` and `SemanticChangeEventType` both derive from `BaseModelChangeEventType`, so a single `OfType(BaseModelChangeEventType)` event filter suffices.

`PumpOpenUsdE2eTests` now has **sixteen** passing cases; the five composition cases are `PumpComponentsComposeChildPrims`, `ProductionLineAggregatesPumps`, `DynamicPumpIsComposedThenDeactivated`, `CrossServerComponentIsComposed`, and `ComponentBindingsAreDiscoverable`.

## 4.3 Asset content delivery

The reference server also demonstrates the optional `OU-AssetDelivery` capability from the base spec §5.15. `PlantStage` exposes an `Assets` folder whose `OpenUsdAssetType` children serve the `.usda` layers through read-only Part 5 `FileType` streams: `Plant.usda` (`RootLayer`), `pump.usda` (`Reference`), and `remote-pump.usda` (`Reference`). Each served layer carries a SHA-256 digest.

A generic connector can therefore browse `<Stage>.Assets`, download and verify the layers, cache them with the same relative `AssetIdentifier` paths, and compose the live layer over the local `Plant.usda`. The rendered pump twin is self-contained: no external asset repository or manual USD asset setup is required when the server advertises this capability.

## 5 Where the bindings live

- **Machine-readable descriptor:** `../../extras/openusd-binding/examples/pumps/Pumps.OpenUsdBinding.json`.
- **Illustrative instance overlay (NodeSet):** `Opc.Ua.Pumps.OpenUsd.NodeSet2.xml` (this folder) — a concrete `Pump101` with the AddIn and the three telemetry bindings, for browsing/inspection. The alarm, command, and integrity capabilities are shown in the descriptor JSON and the C# sample.
- **Runnable USD writer:** `../../extras/openusd-binding/examples/pumps/usd_writer.py` (+ generated `live.usda`).
- **C# end-to-end:** the `PumpDeviceIntegrationServer` sample in `marcschier/UA-.NETStandard` exposes the representation + bindings, and `PumpOpenUsdE2eTests` starts the server via the generic host, connects a client session, discovers the representation and bindings through `Server/OpenUSD/Representations`, subscribes to the bound source Variables, and drives a generic connector into a mock USD sink (asserted in CI). A Python `pxr` writer authors a real `live.usda` locally (Omniverse rendering is out of CI scope).

## 6 Deliverables

| Artifact | Path |
|---|---|
| This addendum | `core-specs/openusd-binding/pumps/OPC-UA-Pumps-OpenUSD-Bindings-Addendum.md` |
| Instance overlay | `core-specs/openusd-binding/pumps/Opc.Ua.Pumps.OpenUsd.NodeSet2.xml` |
| Descriptor | `core-specs/extras/openusd-binding/examples/pumps/Pumps.OpenUsdBinding.json` |
| USD writer + example stage | `core-specs/extras/openusd-binding/examples/pumps/usd_writer.py`, `live.usda` |
