# OPC UA Robotics — OpenUSD Bindings Addendum

**Implementer Annex to *OPC UA — OpenUSD Bindings* (Release 0.2.0 — Draft).**

> This addendum is the **implementer (Robotics) annex** for the generic *OPC UA — OpenUSD Bindings* companion model. All Robotics-specific and end-to-end detail lives here; the base specification (`../OPC-UA-OpenUSD-Bindings.md`) remains domain-agnostic. It shows how an OPC 40010 `MotionDeviceSystem` instance representing a robot cell is bound to an OpenUSD prim, how two 6-axis `MotionDevice` robots are recursively composed, and how each Axis' `ActualPosition` drives one USD joint rotate op. The machine-readable source of truth is `../../extras/openusd-binding/examples/robotics/Robotics.OpenUsdBinding.json`; a runnable USD writer is `../../extras/openusd-binding/examples/robotics/usd_writer.py`; the C# end-to-end validation lives in the `RoboticsDeviceIntegrationServer` sample and `RobotOpenUsdE2eTests`.

---

## 1 Scope

This addendum binds one OPC 40010 `MotionDeviceSystem` (`RobotCell`) to `/Cell` in an OpenUSD stage. It defines recursive composition from the system to two articulated `MotionDevice` robots (`/Cell/Robots/R1`, `/Cell/Robots/R2`) and from each robot to six Axis link Xforms. Each Axis carries a read-only telemetry binding (`OpenUsdValueChangeBindingType`) from `ParameterSet/ActualPosition` in degrees to a USD rotate op (`xformOp:rotateZ`, `xformOp:rotateY`, or `xformOp:rotateX`). It also shows an emergency-stop alarm binding driving beacon visibility and a per-robot warning-halo visibility, an opt-in speed-override command binding, and a dynamic gripper tool reference mounted on R1's flange.

## 2 Normative references

- *OPC UA — OpenUSD Bindings*, Release 0.2.0 (the base specification).
- [OPC 40010](https://reference.opcfoundation.org/specs/40010/) — OPC UA for Robotics, namespace `http://opcfoundation.org/UA/Robotics/`.
- [OPC 10000-100](https://reference.opcfoundation.org/specs/OPC-10000-100/) — Devices (DI), the base for component and device integration modelling.

## 3 How the bindings are applied

A `MotionDeviceSystemType` instance gains an OpenUSD representation by composing an `OpenUsdRepresentation` AddIn (`HasAddIn`) that targets a stage and `/Cell`, and by carrying `<Component>` and `<Binding>` children. Component bindings then recursively compose the represented children:

```text
RobotCell : MotionDeviceSystemType
  └─ HasAddIn OpenUsdRepresentation : OpenUsdRepresentationType
       Stage    = NodeId(Server/OpenUSD/Stages/RobotCellStage)
       PrimPath = "/Cell"
       ├─ <Component> RobotsAggregation : OpenUsdComponentBindingType
       │    MotionDevices (Organizes, Many) -> /Cell/Robots/<BrowseName>, Reference @robot.usda@</Robot>
       ├─ EmergencyStopBeacon : OpenUsdAlarmBindingType (-> /Cell/SafetyBeacon.visibility)
       └─ SpeedOverrideCommand : OpenUsdCommandBindingType (-> /Cell.inputs:speedOverride)

MotionDevices/R1 : MotionDeviceType
  └─ HasAddIn OpenUsdRepresentation
       PrimPath = "/Cell/Robots/R1"
       ├─ <Component> AxesAggregation : Axes (HasComponent, Many) -> child link Xforms
       ├─ <Component> GripperTool : Flange/MountedTool -> /Cell/Robots/R1/Base/J1/J2/J3/J4/J5/J6/Flange/Tool, Reference @tool.usda@</Gripper>, Dynamic=true
       └─ EmergencyStopWarning : OpenUsdAlarmBindingType (-> /Cell/Robots/R1/Warning.visibility)

MotionDevices/R1/Axes/A1 : AxisType
  └─ HasAddIn OpenUsdRepresentation
       PrimPath = "/Cell/Robots/R1/Base/J1"
       └─ AxisActualPosition : OpenUsdValueChangeBindingType
            SourceBrowsePath = "/ParameterSet/ActualPosition"
            TargetPropertyName = "xformOp:rotateZ"
            RenderTargetKind = Rotation
```

The AddIns are also `Organizes`-listed from `Server/OpenUSD/Representations`, so a generic connector discovers them without knowing anything about robotics. Each Axis binding resolves its source relative to the represented Axis Object; the effective runtime key is `(Axis Object, BindingDefinitionId)`.

## 4 OpenUSD bindings for `MotionDeviceSystem` / `MotionDevice` / `Axis`

| Binding | Source / component relationship | Target property | USD type | RenderTargetKind / arc | Conversion |
|---|---|---|---|---|---|
| **RobotsAggregation** | `RobotCell/MotionDevices` (`Organizes`, Many) | `/Cell/Robots/<BrowseName>` | prim reference | Reference | compose `@robot.usda@</Robot>`; non-instanceable |
| **AxisActualPosition A1** | Axis `A1/ParameterSet/ActualPosition` | `xformOp:rotateZ` on `.../Base/J1` | `double` | Rotation | degrees -> degrees |
| **AxisActualPosition A2** | Axis `A2/ParameterSet/ActualPosition` | `xformOp:rotateY` on `.../Base/J1/J2` | `double` | Rotation | degrees -> degrees |
| **AxisActualPosition A3** | Axis `A3/ParameterSet/ActualPosition` | `xformOp:rotateY` on `.../Base/J1/J2/J3` | `double` | Rotation | degrees -> degrees |
| **AxisActualPosition A4** | Axis `A4/ParameterSet/ActualPosition` | `xformOp:rotateX` on `.../Base/J1/J2/J3/J4` | `double` | Rotation | degrees -> degrees |
| **AxisActualPosition A5** | Axis `A5/ParameterSet/ActualPosition` | `xformOp:rotateY` on `.../Base/J1/J2/J3/J4/J5` | `double` | Rotation | degrees -> degrees |
| **AxisActualPosition A6** | Axis `A6/ParameterSet/ActualPosition` | `xformOp:rotateX` on `.../Base/J1/J2/J3/J4/J5/J6` | `double` | Rotation | degrees -> degrees |
| **EmergencyStopBeacon** | `/SafetyStates/EmergencyStop` ActiveState | `/Cell/SafetyBeacon.visibility` | `token` | Visibility | active -> `inherited`, clear -> `invisible` |
| **EmergencyStopWarning** | shared cell e-stop ActiveState | robot `Warning.visibility` | `token` | Visibility | active -> `inherited`, clear -> `invisible` |
| **SpeedOverrideCommand** | USD command intent -> `/Controllers/Controller_C1/ParameterSet/SpeedOverride` | `/Cell.inputs:speedOverride` | `double` | command | opt-in, authorized write |
| **GripperTool** | `R1/Flange/MountedTool` | `/Cell/Robots/R1/.../Flange/Tool` | prim reference | Reference, Dynamic | compose `@tool.usda@</Gripper>` while mounted |

Notes:

- Every joint target prim must contain the named `xformOp:rotate*` in `xformOpOrder`.
- The Axis values are already in degrees; no radians conversion is applied.
- The robot safety binding targets `Warning.visibility` on each robot root. Visibility is used because the shared emergency-stop source is Boolean and the generic connector maps Boolean values reliably to the `Visibility` render target (`inherited` / `invisible`).

## 4.1 Composition / aggregation

The robotics example exercises recursive composition (base spec §5.12–5.14). The system aggregates MotionDevices using `CompositionArc = Reference`; the base `Cell.usda` layer contains positioned empty `/Cell/Robots/R1` and `/Cell/Robots/R2` mount-point Xforms, and the connector authors reference arcs on those prims in the stronger `live.usda` layer. Each robot then composes its Axes using `CompositionArc = Child`, because the link prims are pre-authored inside `robot.usda`. The nesting mirrors the OPC 40010 structure while preserving an artist-authored USD kinematic chain.

Reference, not Instance, is intentional for `/Cell/Robots/R1` and `/Cell/Robots/R2`: both robots use the same reusable `robot.usda` asset, but each needs independent live opinions on the same relative joint paths. Instanceable prims share prototype composition and are not suitable when every robot must articulate independently. The R1 gripper uses dynamic Reference composition so a model-change event can add or remove `/Cell/Robots/R1/Base/J1/J2/J3/J4/J5/J6/Flange/Tool` without mutating `Cell.usda`.

## 4.2 Asset content delivery

The reference server also demonstrates the optional `OU-AssetDelivery` capability from the base spec §5.15. `RobotCellStage` exposes an `Assets` folder whose `OpenUsdAssetType` children serve the `.usda` layers through read-only Part 5 `FileType` streams: `Cell.usda` (`RootLayer`), `robot.usda` (`Reference`), and `tool.usda` (`Reference`). Each served layer carries a SHA-256 digest.

A generic connector can therefore browse `<Stage>.Assets`, download and verify the layers, cache them with the same relative `AssetIdentifier` paths, and compose the live layer over the local `Cell.usda`. The rendered robot-cell twin is self-contained: no external asset repository or manual USD asset setup is required when the server advertises this capability.

## 4.3 Reference implementation

The `RoboticsDeviceIntegrationServer` sample realizes this design and validates it with `RobotOpenUsdE2eTests`: the companion Robotics model is served; the `RobotCell` representation and child robot/Axis representations are discoverable through `Server/OpenUSD/Representations`; live Axis telemetry drives a generic connector into a USD sink; the e-stop alarm updates cell beacon and robot warning visibility; the speed override command is declared but fail-closed unless the connector enables commands and the server authorizes the write; and the dynamic gripper is reconciled from model-change events.

The connector/bridge is the same generic implementation used for the pump example. It does not branch on `MotionDeviceSystemType`; it processes every `OpenUsdRepresentation` and its `<Binding>` / `<Component>` children.

## 5 Where the bindings live

- **Machine-readable descriptor:** `../../extras/openusd-binding/examples/robotics/Robotics.OpenUsdBinding.json`.
- **Illustrative instance overlay (NodeSet):** `Opc.Ua.Robotics.OpenUsd.NodeSet2.xml` (this folder) — a concrete `RobotCell` with an `OpenUsdRepresentation` AddIn, a `RobotsAggregation` component binding, and representative robot/Axis bindings for browsing/inspection.
- **Runnable USD writer:** `../../extras/openusd-binding/examples/robotics/usd_writer.py` (+ generated `live.usda`).
- **USD assets and tutorial:** `../../extras/openusd-binding/examples/robotics/Cell.usda`, `robot.usda`, `tool.usda`, `stage.usda`, `render_robot.py`, and `E2E-GUIDE.md`.
- **C# end-to-end:** the `RoboticsDeviceIntegrationServer` sample exposes the representation + bindings, and `RobotOpenUsdE2eTests` discovers them through the registry and drives the same generic connector infrastructure used by pumps.

## 6 Deliverables

| Artifact | Path |
|---|---|
| This addendum | `core-specs/openusd-binding/robotics/OPC-UA-Robotics-OpenUSD-Bindings-Addendum.md` |
| Instance overlay | `core-specs/openusd-binding/robotics/Opc.Ua.Robotics.OpenUsd.NodeSet2.xml` |
| Descriptor | `core-specs/extras/openusd-binding/examples/robotics/Robotics.OpenUsdBinding.json` |
| USD writer + example stage | `core-specs/extras/openusd-binding/examples/robotics/usd_writer.py`, `live.usda`, `stage.usda` |
| USD assets | `core-specs/extras/openusd-binding/examples/robotics/Cell.usda`, `robot.usda`, `tool.usda` |
| Tutorial + fallback renderer | `core-specs/extras/openusd-binding/examples/robotics/E2E-GUIDE.md`, `render_robot.py` |
