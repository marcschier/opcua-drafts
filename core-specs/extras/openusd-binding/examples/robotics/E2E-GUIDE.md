# End-to-end guide: render live articulated robots from OPC UA in OpenUSD

This is a hands-on guide for the **RoboticsDeviceIntegrationServer** bound to an **OpenUSD** model. It shows a robot cell whose two 6-axis articulated robots are rendered from live OPC UA Axis `ActualPosition` values: every joint in USD is driven by a generic binding, with **no robot-specific code** in the connector or renderer.

It realizes the collaboration flow described in Annex B of the base specification (`../../../openusd-binding/OPC-UA-OpenUSD-Bindings.md`). This document lives **outside** the normative spec; it is a tutorial for implementers.

## What you will build

```
RoboticsDeviceIntegrationServer       (OPC UA server: MotionDeviceSystem + OpenUSD bindings)
        │  Server/OpenUSD/Representations  (discovery)
        ▼
OpenUsdConnector  ──► UsdFileSink ──►  live.usda        (runtime override opinions)
                                          │  subLayers
                                          ▼
                                       stage.usda  =  live.usda  +  Cell.usda
                                          │
                                          ▼
                                 usdview / NVIDIA Omniverse   (the rendered live robot cell)
```

- **Server** — exposes `RobotCell` as an OPC 40010 `MotionDeviceSystem` with one system representation, two robot representations, and twelve Axis representations.
- **Connector** — the same generic OpenUSD connector/bridge used for pumps. It discovers representations via `Server/OpenUSD/Representations`, subscribes to the bound Variables, converts values, and writes a USD override layer through `UsdFileSink`.
- **Base asset** — `Cell.usda` (cell environment and positioned empty `/Cell/Robots/R1` and `/Cell/Robots/R2` mount-point Xforms). The generic connector composes non-instanceable `robot.usda` references into `live.usda`; `stage.usda` composes that live override layer on top of the environment.
- **Viewer** — `usdview` (baseline) or NVIDIA Omniverse (RTX).

## Articulation bindings

Each Axis representation carries the same `UaToUsdTelemetry` binding shape: `ParameterSet/ActualPosition` in degrees maps 1:1 to a USD rotate op. USD rotate ops are degrees, so the connector applies `Scale = 1.0`, `Offset = 0.0`.

| Robot | Axis | Axis source | USD target prim | Target property | Home |
|---|---|---|---|---|---|
| R1/R2 | A1 | `ParameterSet/ActualPosition` | `.../Base/J1` | `xformOp:rotateZ` | 0° |
| R1/R2 | A2 | `ParameterSet/ActualPosition` | `.../Base/J1/J2` | `xformOp:rotateY` | -30° |
| R1/R2 | A3 | `ParameterSet/ActualPosition` | `.../Base/J1/J2/J3` | `xformOp:rotateY` | 45° |
| R1/R2 | A4 | `ParameterSet/ActualPosition` | `.../Base/J1/J2/J3/J4` | `xformOp:rotateX` | 0° |
| R1/R2 | A5 | `ParameterSet/ActualPosition` | `.../Base/J1/J2/J3/J4/J5` | `xformOp:rotateY` | 60° |
| R1/R2 | A6 | `ParameterSet/ActualPosition` | `.../Base/J1/J2/J3/J4/J5/J6` | `xformOp:rotateX` | 0° |

The nested link Xforms form a serial kinematic chain, so changing A2 also moves every downstream wrist and flange prim.

## Safety, command, and dynamic tool bindings

| Binding | Intent | Source / command | USD target | Effect |
|---|---|---|---|---|
| `EmergencyStopBeacon` | `UaAlarmToUsd` | `/SafetyStates/EmergencyStop` ActiveState | `/Cell/SafetyBeacon.visibility` | beacon visible while e-stop is active |
| `EmergencyStopWarning` | `UaAlarmToUsd` | same cell e-stop | `/Cell/Robots/R1/Warning.visibility` and `/Cell/Robots/R2/Warning.visibility` | warning halos become visible while stopped, hidden when clear |
| `SpeedOverrideCommand` | `UsdToUaCommand` | USD `inputs:speedOverride` → controller SpeedOverride Variable | `/Cell.inputs:speedOverride` | opt-in command intent, fail-closed unless the bridge enables commands |
| `GripperTool` | composition | `/Flange/MountedTool` model change | `/Cell/Robots/R1/.../Flange/Tool` reference to `tool.usda` | dynamically attaches the gripper to R1 |

## Composition

The system representation composes `/Cell`. Its `<Component>` binding `RobotsAggregation` maps `MotionDevices` to non-instanceable `Reference` prims under `/Cell/Robots`; these robot prims are authored by the connector into `live.usda`, not by the base `Cell.usda` asset. Reference is used deliberately instead of Instance because R1 and R2 must carry independent opinions for `xformOp:rotate*`; an instanceable prim would share a prototype and cannot independently articulate the same joint paths.

Each robot representation recursively composes its `Axes` by `Child` arcs. The Axis representation does not create new geometry; it targets the pre-authored link Xform inside `robot.usda` and drives the rotate op on that link. The R1 tool uses dynamic `Reference` composition and is authored when the server adds the mounted tool node and emits a model-change event.

## Optional asset delivery (zero-setup base layers)

When the server advertises `RobotCellStage.Assets` (`OU-AssetDelivery`), the bridge can download `Cell.usda`, `robot.usda`, and `tool.usda` from the server through Part 5 `FileType`, verify their SHA-256 digests, and write them into a local cache before composing `live.usda`. In that mode `usdview` or Omniverse opens a fully local, self-contained `stage.usda`; no external asset repository or manual base-layer copy is needed. If the server does not advertise `Assets`, provide the base `.usda` files out-of-band as in Step 1.

## Prerequisites

- **.NET SDK 10** — to build and run the server + connector.
- The **UA-.NETStandard** working copy containing `RoboticsDeviceIntegrationServer` and the generic OpenUSD connector/bridge. The C# e2e coverage is `RobotOpenUsdE2eTests`.
- A USD viewer, either `usdview` or NVIDIA Omniverse.
- *(Optional)* Python 3 with `usd-core` (`pip install usd-core`) to validate composition. The Python writer also works without `pxr` by emitting deterministic USDA text.

## Step 1 — Prepare a working folder with the base assets

```bash
mkdir ~/robot-live
cp opcua-drafts/core-specs/extras/openusd-binding/examples/robotics/Cell.usda ~/robot-live/
cp opcua-drafts/core-specs/extras/openusd-binding/examples/robotics/robot.usda ~/robot-live/
cp opcua-drafts/core-specs/extras/openusd-binding/examples/robotics/tool.usda ~/robot-live/
cp opcua-drafts/core-specs/extras/openusd-binding/examples/robotics/stage.usda ~/robot-live/
```

`stage.usda` sublayers `live.usda` (stronger) over `Cell.usda`. `Cell.usda` shows only the environment; the full articulated robots appear when the connector or `usd_writer.py --demo` authors the robot references and joint overrides into `live.usda`.

## Step 2 — Start the server

```bash
cd UA-.NETStandard
dotnet run --project Applications/RoboticsDeviceIntegrationServer -c Release -f net10.0 -- --host localhost --port 62820
```

Wait for the server to listen at an `opc.tcp://localhost:62820/RoboticsDeviceIntegrationServer` endpoint. The server simulates both robots with phase-shifted joint sweeps and toggles the emergency-stop state to exercise alarm and dynamic reconciliation paths.

## Step 3 — Run the generic connector

```bash
cd UA-.NETStandard
dotnet run --project Applications/OpenUsdConnector -c Release -f net10.0 --   --server opc.tcp://localhost:62820/RoboticsDeviceIntegrationServer --out ~/robot-live/live.usda --insecure
```

The bridge is generic: it consumes `Server/OpenUSD/Representations`, subscribes to all Axis `ActualPosition` sources, and writes the declared target properties. Enable command writes only deliberately, for example with a connector-specific `--enable-commands` option and authorized server credentials.

## Step 4 — Open the rendered live robot cell

```bash
usdview ~/robot-live/stage.usda
```

You will see two articulated robots inside a fenced cell. With the connector running, reload the stage in `usdview` to pull the newest `live.usda`: R1 and R2 hold different joint poses, R1 carries a gripper on its flange, and the beacon plus each robot warning halo follow the e-stop safety state. Omniverse can consume the same composed stage continuously.

## Alternative — the Python demo writer

```bash
cd opcua-drafts/core-specs/extras/openusd-binding/examples/robotics
python usd_writer.py --demo
python render_robot.py stage.usda robot_render.png
```

The writer reads `Robotics.OpenUsdBinding.json` and writes a deterministic `live.usda` using the same prim paths, rotate ops, binding ids, safety targets, command target, and R1 dynamic tool declared by the descriptor. If `pxr` is installed it uses OpenUSD APIs; otherwise it writes valid USDA text by hand.

## What you should see

A cell with two independent 6-axis arms in non-home poses. Opening `Cell.usda` alone shows the environment plus empty R1/R2 mount points; opening `stage.usda` composes `live.usda`, which contains the robot references. The phase shift proves that `Reference` (not `Instance`) was used for the aggregated robots, because each robot has independent joint override opinions. R1's flange contains a dynamically composed `Tool` reference to `tool.usda`, and `/Cell.inputs:speedOverride` demonstrates the opt-in command target.
