# OPC UA — Robot Intent

**Release 0.4.0 — Draft.** An OPC UA information model for commanding a robot at the level of task intent, with a lifecycle that survives the minutes such work actually takes.

Nothing here is normative, official, or endorsed by the OPC Foundation, VDMA or any robot manufacturer. Namespace URIs and NodeIds are **provisional** and for prototyping only.

## What it is for

OPC 40010-1 *Robotics* describes robot **topology** in detail and defines **no motion verbs at all** — its whole actuation surface is `Start`, `Stop` and loading a named program. A conformant client can discover everything about a robot's construction and cannot ask it to move anywhere.

This model supplies the verbs, and nothing else, so the two compose rather than compete. It sits **above** the vendor motion language and **beside and beneath nothing** in the safety system:

- task-level intents — joint, linear and circular moves, trajectories, Cartesian paths, force-controlled moves, grasp, release, pick, place, tool change, output, program call, wait, and six application processes;
- a lifecycle built on the Part 10 program model, because an OPC UA `Call` cannot stay open for the length of a real motion;
- PLCopen buffer modes for queueing and blending, and VDA 5050 blocking modes for concurrency;
- missions with an immutable committed base, a revisable horizon, and an IEC 61131-3 step graph with per-step error policies;
- **safety awareness** — what the safety system is enforcing, and a duty to refuse work that would exceed it;
- **real-time channel brokerage** — describe and lease RTDE, EGM, FRI, RSI, MotoROS2 or OPC UA FX, without carrying a single sample;
- the robot's kinematic chain, reach and payload, which OPC 40010-1 does not define;
- a machine-readable capability declaration, so a client reads what a robot accepts instead of probing for it.

## Layout

| File | What it is |
|---|---|
| [`spec.md`](spec.md) | The specification |
| [`OPC-UA-Robot-Intent-Research.md`](OPC-UA-Robot-Intent-Research.md) | The prior art, the gaps, and the decisions those gaps forced |
| `Opc.Ua.RobotIntent.NodeSet2.xml` | The information model — **generated** |
| `Opc.Ua.RobotIntent.NodeIds.csv` | The NodeId assignments — **generated** |

Tooling lives in [`metaverse-specs/extras/robot-intent/tools/`](../../../metaverse-specs/extras/robot-intent/tools/): `build_model.py` is the single source of truth for all three generated artifacts, `validate_local.py` is the gate, and `model-reference.md` is the generated Annex A.

## Build and validate

```powershell
python metaverse-specs\extras\robot-intent\tools\build_model.py
python metaverse-specs\extras\robot-intent\tools\validate_local.py
```

The generator is **deterministic**: rebuilding reproduces the committed NodeSet byte for byte. Edit the generator, never the generated NodeSet, CSV or Annex A.

NodeId assignment is **append-only** — new members take the next free id, because inserting one mid-file silently renumbers everything after it.

The validator re-derives everything from the committed artifacts rather than asking the generator what it emitted, and cross-checks the specification against the model **in both directions**: every type and every enumeration literal the model declares must be named in the prose, and every `ns=1;i=<n>` the prose cites must exist in the model.

## Namespace

`http://opcfoundation.org/UA/RobotIntent/`

The NodeSet declares exactly one `RequiredModel` — the base OPC UA namespace. Binding to an OPC 40010-1 `MotionDeviceSystem` is an optional profile carried by a ReferenceType (Annex B), not a NodeSet dependency, so a Server can adopt this model without pulling in any companion specification.
