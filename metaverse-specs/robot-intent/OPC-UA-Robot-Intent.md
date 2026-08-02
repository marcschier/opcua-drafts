# OPC UA — Robot Intent

> Status: Working-group draft (Release 0.1.0). This document, together with `Opc.Ua.RobotIntent.NodeSet2.xml` and `Opc.Ua.RobotIntent.NodeIds.csv`, defines an OPC UA information model for **commanding a robot at the level of task intent** — move there, grasp that, pick from here, place at that — with a lifecycle that survives the minutes such work actually takes.
>
> Nothing here is normative, official, or endorsed by the OPC Foundation, VDMA or any robot manufacturer; namespace URIs and NodeIds are **provisional** and for prototyping only. The prior art, the gaps this model fills, and the decisions those gaps forced are recorded in the companion research report, [`OPC-UA-Robot-Intent-Research.md`](OPC-UA-Robot-Intent-Research.md).

---

## 1 Scope

This specification defines an OPC UA information model that lets a Server describe:

- **what a robot can be asked to do** — as a declared, machine-readable set of intents rather than a convention a client must know in advance;
- **how to ask it** — one submission per intent, or an ordered mission of them;
- **what happens next** — a lifecycle a client can observe from admission through queueing, execution and cancellation to a terminal result;
- **what the request refers to** — the frames, tools, locations, axes, signals and programs that give a pose or a place its meaning;
- **when the robot will refuse** — the operational modes, the command authority, and the boundary between this interface and the safety system that is never crossed.

### 1.1 Motivation

OPC 40010-1 describes robot **topology** in detail — the motion device system, its axes, its power trains, its controller, its safety states. It defines **no motion verbs at all**. Its entire actuation surface is `Start`, `Stop` and the loading of a named program over two state machines. A conformant client can discover everything about a robot's construction and cannot ask it to move anywhere.

The consequence is that every robot integration above the level of "run program 7" is bespoke. Two Servers can be fully conformant to OPC 40010-1 and still share no way to express *move the tool to this pose*. The verbs exist — every vendor has joint, linear and circular moves, a speed, an acceleration, a blend, a tool frame and a work frame — but they exist only in vendor languages that do not interoperate.

This specification supplies the verbs, and nothing else, so that the two compose rather than compete.

There is a second gap, and it is the harder one. A motion takes seconds; a pick takes a minute. An OPC UA `Call` cannot stay open that long — Session timeouts, SecureChannel re-keying and transport timeouts all bound it, and OPC 10000-4 is explicit that if the Session ends the result is discarded *"independent of the task actually performed at the Server"*. A synchronous method that commands a robot is therefore not merely inelegant; it loses the outcome of work that has already physically happened. Clause 6 addresses this, and it is the reason the model is shaped the way it is.

### 1.2 Motivating use cases

- **Task-level cell control.** A cell controller sequences a robot, a fixture and a conveyor without embedding vendor motion code, because the robot's capability is declared and its verbs are portable.
- **Planner and agent integration.** A planner — symbolic, learned, or a language model — emits intents against a declared vocabulary, and receives structured failures it can re-plan against rather than a vendor error string.
- **Mixed-fleet work cells.** Two robots from different manufacturers execute the same mission definition, because the mission is expressed in intents and each Server translates into its own controller's language.
- **Long-running supervised operation.** A supervisory system submits a mission, watches it progress, revises the part that has not yet been committed, and cancels it cleanly when the upstream process changes.
- **Auditable commanding.** Every intent records which Session commanded it, when, with what arguments and to what outcome, because the Part 10 program model already carries that.

### 1.3 What this specification does not do

Three of these are permanent boundaries, and two are deferrals this working group may revisit.

**Out of scope by design:**

- It is **not** a real-time motion interface. It does not stream trajectories, close force loops, track conveyors or replace `servoj`, EGM, FRI or RSI. Those run at 250 Hz to 1 kHz on dedicated channels; this interface runs at OPC UA rates and is measured in whole motions, not in cycles. §4.3 states this as a normative limit rather than a caution.
- It is **not** a safety function, and it is **not** safety-rated. Clause 10 says exactly what that means and what it does not permit a client to assume.
- It does **not** define the robot's construction. Axes appear here only in the detail an intent needs — order, kind, limits — because a joint target is meaningless without them. OPC 40010-1 describes the machine, and Annex B binds the two.

**Not addressed yet:**

- It does **not yet** define a portable inspection, welding or dispensing process model. Such work is reachable through `CallProgramIntentDataType` and is a candidate for a later part.
- It does **not yet** define conditional or branching missions. A mission is an ordered sequence; branching, loops and error-handling policies are deferred, because a sequence with a revisable horizon covers the supervised cases without committing the model to an execution language.

Neither list is a statement that the omitted capability is unimportant — only that Release 0.1.0 does not define it, and that a Server is conformant without it.

### 1.4 Capabilities and versioning

Release 0.1.0 covers the intent vocabulary, the execution lifecycle, queueing and blending, cancellation, missions with a committed base and a revisable horizon, command authority, and capability declaration. The NodeSet declares exactly one `RequiredModel` — the base OPC UA namespace — so a Server can adopt it without pulling in any companion model.

---

## 2 Normative references

- **OPC 10000-3, -4, -5** — Address Space Model, Services, Information Model. The base UA namespace is the only required model. OPC 10000-4 §5.12.2 bounds what a Method call can do, and OPC 10000-4 §5.7.5 defines the `Cancel` Service that §6.5 distinguishes this specification's cancellation from.
- **OPC 10000-10** — Programs. `ProgramStateMachineType` is the base type of `IntentOperationType` and `MissionType`, and supplies the transition events, the terminal result object and the invocation diagnostics this specification relies on rather than re-inventing.
- **OPC 10000-6** — Mappings. Structure subtyping and `ExtensionObject` encoding of the intent hierarchy (§5.3).
- **ISO 8373** — *Robots and robotic devices — Vocabulary*. Source of the terms in clause 3; where this document uses *pose*, *path*, *trajectory*, *tool centre point*, *end effector* or *workspace*, it uses them as ISO 8373 defines them.
- **ISO 9787:2013** — *Robots and robotic devices — Coordinate systems and motion nomenclatures*. Source of the frame roles in `FrameRoleEnum`, and of the roll-pitch-yaw convention used by the conversion in Annex C.
- **ISO 10218-1** and **ISO 10218-2** — *Robotics — Safety requirements*. Source of the operational modes in `OperationalModeEnum` and of the single-point-of-control requirement discussed in clause 10.
- **IEC 60204-1** — *Safety of machinery — Electrical equipment of machines*. Source of the stop categories that clause 10 states this interface does **not** select.

Informative alignments — PLCopen Motion Control, VDA 5050, ROS 2 actions, MoveIt, the vendor motion languages, and the Capability–Skill–Service model — are listed in Annex D. They are **not** normative references and impose no dependency, notwithstanding that `BufferModeEnum` and `BlockingModeEnum` adopt their vocabularies deliberately and unchanged.

---

## 3 Terms, definitions and abbreviations

| Term | Definition |
|---|---|
| **Intent** | A single task-level request — one motion, one grasp, one pick. Modelled as a subtype of `IntentDataType`. It is what a client submits and what a mission step holds. |
| **Intent operation** | One submitted intent, tracked to completion. Modelled as `IntentOperationType`, a Part 10 program instance created per submission. |
| **Mission** | An ordered sequence of intents submitted and tracked as a unit. Modelled as `MissionType`. |
| **Base** (of a mission) | The prefix of released steps. Committed, possibly already executing, and immutable (§7.2). |
| **Horizon** (of a mission) | The suffix of unreleased steps. Provisional, and revisable by `UpdateMission` (§7.2). |
| **Pose** | A rigid-body placement — three of position and three of orientation — expressed relative to a named frame. Carried by `Pose3DDataType`, whose orientation is a unit quaternion ordered (x, y, z, w) per §5.2. |
| **Frame** | A named right-handed Cartesian coordinate system a pose is expressed relative to. Frames form a tree through `HasFrameParent`. Modelled as `CoordinateFrameType`. |
| **Tool centre point (TCP)** | The origin of a tool frame; the point a motion intent drives to its target. OPC 40010-1 defines no such concept, so `ToolType.TcpFrame` supplies one. |
| **Blending** | Rounding the corner between two motions rather than stopping on the first one's target. Requested by `BlendDataType`, and by the blending values of `BufferModeEnum`. |
| **Buffer mode** | How a newly submitted intent relates to the one already executing — abort it, queue behind it, or blend into it. `BufferModeEnum`. |
| **Blocking mode** | Whether an intent tolerates motion and other intents alongside it. `BlockingModeEnum`. |
| **Command authority** | The exclusive right, held by at most one Session, to submit intents to one controller (clause 8). It is an arbitration mechanism between clients and **not** the single point of control that ISO 10218-2 requires. |
| **Terminal state** | An `ExecutionStateEnum` value from which execution does not resume: `Succeeded`, `Failed`, `Cancelled`, or `Retriable`. |

---

## 4 Overview and concepts

### 4.1 The layered contract

This specification occupies one band and touches neither the band above nor the two below.

```mermaid
flowchart TB
    A["Planner, cell controller, agent, fleet manager"]
    B["Robot Intent - this specification<br/>task-level verbs, whole motions"]
    C["Vendor motion language<br/>URScript, RAPID, KRL, TP, INFORM"]
    D["Real-time channel<br/>RTDE, EGM, FRI, RSI"]
    E["Safety-rated controller<br/>independent of this interface"]
    F["OPC 40010-1 topology<br/>optional binding, Annex B"]
    A --> B
    B --> C
    C --> D
    F -.-> B
    E -.-> C
```

A Server implementing this specification **shall** translate intents into whatever its controller actually executes. It **shall not** require a client to know which controller that is: the point of the model is that the same intent, submitted to two Servers driving robots from two manufacturers, produces the same physical outcome within the tolerance each robot is capable of.

The safety layer is beside and beneath this interface and is never mediated by it. That relationship is normative and is stated in clause 10.

### 4.2 Intent, not trajectory

An intent says **what** is to be achieved and constrains **how far** the Server may go in achieving it. It does not say how. The Server owns path planning, inverse kinematics, singularity avoidance, collision checking and the choice of configuration.

This is what makes the model portable. Every vendor already solves those problems, differently and well; a specification that dictated the solution would be implementable by nobody. `MotionConstraintsDataType` is therefore a set of **bounds**, not a plan, and a Server **shall** clamp a request to what the robot is configured to permit rather than refuse it — except where clause 10 requires refusal.

The same reasoning applies to blending. `BlendDataType.Radius` is a request in metres because that is the only unit two vendors share; controllers that expose a unitless blend scale map it as best they can, and a Server that cannot honour the exact radius **shall** still succeed. A client that needs the exact path uses `Exact` termination, which every vendor implements identically.

### 4.3 What this interface is not for

A Server **shall not** present this interface as a real-time control channel, and a client **shall not** use it as one.

OPC UA method invocation is not deterministic and, in the deployments this model is written for, completes in tens of milliseconds. Vendor real-time channels run two to four orders of magnitude faster on dedicated transports. The following are therefore outside what the model can express, and a Server **shall not** claim conformance for them:

- servo-level or joint-cyclic control;
- closed force or impedance loops that require a bounded control period;
- conveyor tracking, seam tracking or any other motion slaved to an external signal at rate;
- trajectory streaming, whether as a dense waypoint list or as a time-parameterised path.

`IntentOperationType.CurrentPose` exists so a client can *watch* a motion. It is a status report delivered at whatever rate the client's Subscription asks for, and using it to close a control loop is outside this specification.

### 4.4 Architecture

```mermaid
flowchart LR
    S["Server"] --> R["RobotIntent<br/>well-known entry point"]
    R --> CTL["IntentController<br/>one per robot"]
    CTL --> CAP["Capabilities"]
    CTL --> REF["Frames, Tools, Locations,<br/>Axes, Outputs, Programs"]
    CTL --> OPS["Intents<br/>IntentOperation per submission"]
    CTL --> MIS["Missions<br/>Mission per submission"]
    MIS --> OPS
```

A client browses `Server/RobotIntent/Controllers` to find every robot it may command, reads that controller's `Capabilities` to learn what it accepts, resolves the frames and locations its intents will refer to, and then submits.

---

## 5 Information model

### 5.1 Type hierarchy

| Type | NodeId | Subtype of |
|---|---|---|
| `RobotIntentRootType` | `ns=1;i=1001` | `BaseObjectType` |
| `IntentControllerType` | `ns=1;i=1002` | `BaseObjectType` |
| `IntentOperationType` | `ns=1;i=1003` | `ProgramStateMachineType` (`i=2391`) |
| `MissionType` | `ns=1;i=1004` | `ProgramStateMachineType` (`i=2391`) |
| `IntentCapabilitiesType` | `ns=1;i=1005` | `BaseObjectType` |
| `CoordinateFrameType` | `ns=1;i=1006` | `BaseObjectType` |
| `ToolType` | `ns=1;i=1007` | `BaseObjectType` |
| `LocationType` | `ns=1;i=1008` | `BaseObjectType` |
| `AxisType` | `ns=1;i=1009` | `BaseObjectType` |
| `OutputSignalType` | `ns=1;i=1010` | `BaseObjectType` |
| `ProgramType` | `ns=1;i=1011` | `BaseObjectType` |

Annex A is the authoritative node reference and carries every member with its DataType, ValueRank and ModellingRule.

### 5.2 Poses, frames and units (normative)

`Pose3DDataType` (`ns=1;i=3050`) carries `FrameId`, a `Position` of three `Double` in **metres**, and an `Orientation` of four `Double` forming a **unit quaternion ordered (x, y, z, w)**.

Four rules make this unambiguous, and a Server **shall** satisfy all of them.

1. Every frame in this model is **right-handed**.
2. Position is in **metres**; joint targets are in **radians** for a `Revolute` axis and **metres** for a `Prismatic` one; force is in **newtons**; time is in **milliseconds** where carried as `Duration`. These units are fixed by this specification and are **not** negotiable per-instance. `Pose3DDataType` appears as a Method argument, where no `EUInformation` property can reach it, so a per-instance unit would be undeliverable.
3. `Orientation` **shall** be normalised. A Server receiving a quaternion whose norm differs from 1 by more than 1e-6 **shall** reject the intent with `ParameterInvalid`.
4. `FrameId` names a `CoordinateFrameType` instance under the controller's `Frames` folder. An empty `FrameId` means the Server's default work frame.

Quaternions are used because OPC UA defines no quaternion DataType anywhere, and because the `A`, `B`, `C` fields of the core `ThreeDOrientation` carry no convention of their own — the only normative assignment of meaning to them is external to the base specification. A quaternion has no such ambiguity, no gimbal degeneracy, and is what robot controllers and scene descriptions already hold internally. Annex C gives the normative bidirectional conversion to `ThreeDFrame`, so a Server that also speaks OPC 40010-1 or a spatial-location model can move between the two without inventing a convention.

### 5.3 The intent hierarchy

Intents are a **DataType hierarchy**, not one Method per verb.

```mermaid
flowchart TB
    I["IntentDataType (abstract)"]
    M["MotionIntentDataType (abstract)"]
    I --> M
    M --> JM["JointMoveIntentDataType"]
    M --> LM["LinearMoveIntentDataType"]
    M --> CM["CircularMoveIntentDataType"]
    I --> G["GraspIntentDataType"]
    I --> R["ReleaseIntentDataType"]
    I --> P["PickIntentDataType"]
    I --> PL["PlaceIntentDataType"]
    I --> T["ToolChangeIntentDataType"]
    I --> O["SetOutputIntentDataType"]
    I --> C["CallProgramIntentDataType"]
    I --> W["WaitIntentDataType"]
```

Three consequences follow, and each is the reason for the choice:

- **A single intent and a mission step are the same shape.** `MissionStepDataType.Intent` is an `IntentDataType`, so nothing has to be expressed twice.
- **Extension is subtyping.** A vendor or a later part adds an intent by deriving from `IntentDataType`. It is then carried, queued, cancelled and reported by the existing machinery without a new Method.
- **Discovery is a read, not a probe.** `IntentCapabilitiesType.SupportedIntents` names each accepted DataType. A client learns what a robot accepts by reading one Variable, rather than by browsing for BrowseNames and inferring support from their presence.

`IntentDataType` carries what every intent needs: `IntentId`, `Label`, `BufferMode` and `BlockingMode`. `MotionIntentDataType` adds `ToolFrame`, `Constraints` and `Blend` — the members that are meaningless for `SetOutput` and essential for a move.

Fields whose DataType is one of the two abstract structures are emitted with `AllowSubTypes="true"`, so a client decoding a mission does not have to infer polymorphism from the abstractness of a DataType.

### 5.4 Motion intents

`JointMoveIntentDataType` (`ns=1;i=3055`) interpolates in joint space. The tool centre point's path is not controlled and **shall not** be relied on. It carries either explicit `JointTargets` or a `TargetPose`, and `HasJointTargets` decides which — a Boolean discriminator rather than a sentinel, so that neither field has to encode "unset".

Giving a pose rather than joint values is the *"move there, you choose how"* case: the Server solves the kinematics and selects a configuration. A Server **shall** reject a `JointMoveIntentDataType` whose `HasJointTargets` is true and whose `JointTargets` length differs from `IntentCapabilitiesType.AxisCount`, with `ParameterInvalid`.

`LinearMoveIntentDataType` (`ns=1;i=3056`) drives the tool centre point along a straight line. `CircularMoveIntentDataType` (`ns=1;i=3057`) drives it along the arc through `ViaPoint` to `Target`; only the **position** of `ViaPoint` defines the arc, and a Server **shall** ignore its orientation.

The three correspond to the instructions every vendor already has, which is why they are three and not one:

| This specification | UR | ABB | KUKA | FANUC | Yaskawa |
|---|---|---|---|---|---|
| `JointMoveIntentDataType` | `movej` | `MoveJ` / `MoveAbsJ` | `PTP` | `J` | `MOVJ` |
| `LinearMoveIntentDataType` | `movel` | `MoveL` | `LIN` | `L` | `MOVL` |
| `CircularMoveIntentDataType` | `movec` | `MoveC` | `CIRC` | `C` | `MOVC` |

### 5.5 Manipulation intents

`GraspIntentDataType` and `ReleaseIntentDataType` actuate an end effector. `Force` and `Width` are requests: an end effector that cannot regulate force **shall** ignore `Force` and still succeed, because refusing would make the intent unusable on the majority of grippers that are open or closed and nothing else.

`PickIntentDataType` and `PlaceIntentDataType` reference a `LocationType` **node** through `Source` and `Destination`. They do not name a station in a string. A location therefore has exactly one definition — its pose, its occupancy, what it holds and how much of it — which a client can read, subscribe to and reason about. A free-text station identifier would be a second definition of the same fact, able to disagree with the first.

`ToolChangeIntentDataType` references the `ToolType` to fit; a null `Tool` releases the fitted tool and fits nothing.

### 5.6 Auxiliary intents

`SetOutputIntentDataType` writes an `OutputSignalType` node, so the signal's range, unit and meaning are described once in the address space instead of being implied by a line name. `Value` is `BaseDataType` and **shall** match the signal's own DataType.

`CallProgramIntentDataType` runs a `ProgramType` held on the controller. It is the escape hatch for capability this model does not describe, and the bridge to the programs an OPC 40010-1 task control already exposes (Annex B).

`WaitIntentDataType` waits for a duration, for a signal, or for both. A mission needs it to express a rendezvous with something the robot does not control; without it a client has to hold the queue open from outside, which defeats the point of submitting a mission at all.

### 5.7 Reference objects

`CoordinateFrameType` instances form a tree through `HasFrameParent`, so a pose given in one frame can be re-expressed in another by composing the transforms along the path between them. `Role` follows ISO 9787, which standardises *which* frames exist; the transform between them is carried explicitly because no standard says how to calibrate it.

`ToolType.TcpFrame` **shall** reference a `CoordinateFrameType` whose `Role` is `Tool`. At most one `ToolType` instance under a controller **shall** have `Fitted` true at any time.

`AxisType.Index` fixes the position of that axis in `JointMoveIntentDataType.JointTargets`, and `Kind` fixes the unit of that entry. The indices of the axes under one controller **shall** be the contiguous range `0` to `AxisCount − 1`.

### 5.8 Enumerations

The values below are normative. Where a value is cited as interoperable with another specification, renumbering it breaks that claim.

**`ExecutionStateEnum`** (`ns=1;i=3001`) — tabulated with its Part 10 pairing in §6.3: `Accepted` 0, `Queued` 1, `Executing` 2, `Suspended` 3, `Cancelling` 4, `Succeeded` 5, `Failed` 6, `Cancelled` 7, `Retriable` 8.

**`BufferModeEnum`** (`ns=1;i=3002`) — the values of PLCopen `MC_BufferMode`, adopted unchanged.

| Value | | Meaning |
|---|---|---|
| `Aborting` | 0 | Abort what is executing and start immediately. The default, and always accepted. |
| `Buffered` | 1 | Queue; start when the predecessor succeeds. |
| `BlendingLow` | 2 | Blend at the lower of the two boundary speeds. |
| `BlendingPrevious` | 3 | Blend at the predecessor's boundary speed. |
| `BlendingNext` | 4 | Blend at the successor's boundary speed. |
| `BlendingHigh` | 5 | Blend at the higher of the two boundary speeds. |

**`BlockingModeEnum`** (`ns=1;i=3003`) — the VDA 5050 `blockingType` matrix.

| Value | | Motion may continue | Other intents may run |
|---|---|---|---|
| `None` | 0 | yes | yes |
| `Soft` | 1 | no | yes |
| `Single` | 2 | yes | no |
| `Hard` | 3 | no | no |

**`TerminationModeEnum`** (`ns=1;i=3004`) — `Exact` 0 (come to rest on the target), `Blend` 1 (round the corner into the next motion).

**`ReleaseModeEnum`** (`ns=1;i=3005`) — `Drop` 0 (open where it is), `Place` 1 (set down under control at the target), `Handover` 2 (retain until a receiving party has taken it).

**`ApproachModeEnum`** (`ns=1;i=3006`) — `Default` 0 (the Server chooses), `ToolZ` 1 (along the tool's own Z axis), `Top` 2 (from above, in the target's frame), `Side` 3 (laterally, in the target's frame).

**`FrameRoleEnum`** (`ns=1;i=3007`) — the coordinate systems ISO 9787 standardises: `World` 0, `Base` 1, `MechanicalInterface` 2 (the flange), `Tool` 3, `Object` 4 (a workpiece frame), `Other` 5.

**`OperationalModeEnum`** (`ns=1;i=3008`) — the ISO 10218-1 modes, numbered as OPC 40010-1 numbers them: `Other` 0, `ManualReducedSpeed` 1, `ManualHighSpeed` 2, `Automatic` 3, `AutomaticExternal` 4. Clause 10 permits submission only in the last two.

**`StopModeEnum`** (`ns=1;i=3010`) — the values of `PossibleStopModes` in OPC 40010-1: `OnPath` 1, `EndOfCycle` 2, `ProcessStop` 3, `QuickStop` 4, `EndOfInstruction` 5. §10.3 states what these do **not** mean.

**`AxisKindEnum`** (`ns=1;i=3011`) — `Revolute` 0 (its joint target is in radians), `Prismatic` 1 (in metres).

**`MissionUpdateResultEnum`** (`ns=1;i=3012`) — `Accepted` 0, `Outdated` 1 (the update identifier was not greater), `BaseConflict` 2 (it would have altered a released step), `UnknownMission` 3, `Rejected` 4 (refused for a reason the Server states in `Message`).

**`IntentFailureEnum`** (`ns=1;i=3009`) — the reason an intent did not succeed. The set is small and diagnosable on purpose: a client decides whether to retry, re-plan or escalate from this value alone.

| Value | | Meaning |
|---|---|---|
| `None` | 0 | No failure; reported on success. |
| `Unreachable` | 1 | The target lies outside the reachable workspace. |
| `Kinematics` | 2 | No kinematic solution, or a singularity on the path. |
| `Collision` | 3 | A collision was predicted or detected. |
| `JointLimit` | 4 | A joint limit would be or was exceeded. |
| `SpeedLimit` | 5 | The requested speed is not permitted in the active mode. |
| `ToolMissing` | 6 | The required tool is not fitted or not identified. |
| `ObjectNotFound` | 7 | The object to act on was not present. |
| `GraspFailed` | 8 | The object was not acquired, or was lost in transit. |
| `Timeout` | 9 | Did not complete within its permitted time. |
| `NotPermittedInMode` | 10 | Refused; the operational mode does not permit it (§10.2). |
| `ControlNotOwned` | 11 | Refused; the caller does not hold command authority (clause 8). |
| `CapabilityNotSupported` | 12 | Not implemented, or not in this combination (clause 9). |
| `ParameterInvalid` | 13 | A parameter was missing, malformed or out of range. |
| `QueueFull` | 14 | The queue is at `MaxQueueDepth`. |
| `Superseded` | 15 | An `Aborting` submission or a mission update replaced it. |
| `HardwareFault` | 16 | A fault in the robot, the end effector or the controller. |
| `SafetyStop` | 17 | A safety function acted. The safety system decided this, not this interface. |
| `Other` | 18 | A reason none of the above describes; see `Message`. |

---

## 6 Intent lifecycle (normative)

### 6.1 Why an intent is a program instance

A `Call` cannot outlive the Session that made it, and OPC 10000-4 §5.12.2 states that when a Session ends the method result is discarded *"independent of the task actually performed at the Server"*. A robot commanded by a synchronous method therefore keeps moving after the answer has been thrown away — and OPC 10000-10 §4.1 gives the OPC Foundation's own resolution: a Method performs a calculation, a **Program** runs a batch process or a machine tool part program.

`SubmitIntent` accordingly returns as soon as the intent is **admitted**, not when the robot has finished. What it returns is a NodeId: an `IntentOperationType` instance created for that submission, which the client subscribes to for progress and reads for the result.

Building on `ProgramStateMachineType` rather than defining a fresh state machine buys four things this specification then does not have to invent: transition events, a terminal result object that survives the operation, invocation diagnostics recording which Session commanded what, and a lifetime model for the instance itself.

### 6.2 Submission

On `SubmitIntent` a Server **shall**, in this order:

1. Refuse with `ControlNotOwned` if the calling Session does not hold command authority (clause 8).
2. Refuse with `NotPermittedInMode` if `OperationalMode` is not `Automatic` or `AutomaticExternal` (clause 10).
3. Refuse with `CapabilityNotSupported` if the intent's DataType is not among `SupportedIntents`, or if its `BufferMode` or `BlockingMode` is not among those the capability entry permits.
4. Refuse with `ParameterInvalid` if a parameter is missing, malformed or out of range.
5. Refuse with `QueueFull` if admitting it would exceed `MaxQueueDepth`.
6. Otherwise create an `IntentOperationType` instance, assign an `IntentId` if the request left it empty, and return both.

A refusal at any of these steps **shall not** create an operation instance and **shall not** move the robot.

An `IntentId` returned by the Server **shall** be unique among the intents that Server currently holds. A client-supplied `IntentId` that collides with an outstanding one **shall** be refused with `ParameterInvalid`.

### 6.3 States

The Part 10 state machine carries the coarse lifecycle. `ExecutionState` refines it, because `Queued`, `Cancelling` and the distinction between the three terminal outcomes cannot be told apart from `CurrentState` alone.

**The state machine is authoritative** for the coarse state and is what generates events. `ExecutionState` **shall** at all times be consistent with it according to the following table, which is exhaustive: a pairing not listed here is not legal.

| `ExecutionState` | Part 10 state | Meaning |
|---|---|---|
| `Accepted` | `Ready` | Admitted and validated; not yet queued or executing. |
| `Queued` | `Ready` | Waiting behind another intent. `QueuePosition` is non-zero. |
| `Executing` | `Running` | Commanding the robot now. |
| `Suspended` | `Suspended` | Paused; position retained. |
| `Cancelling` | `Running` | A cancel was accepted; motion is being brought to a controlled end. |
| `Succeeded` | `Halted` | Terminal. Completed as requested. |
| `Failed` | `Halted` | Terminal. `Result.Failure` carries the reason. |
| `Cancelled` | `Halted` | Terminal. Ended early because a cancel was accepted. |
| `Retriable` | `Halted` | Terminal for now; `Retry` may re-attempt it. |

```mermaid
stateDiagram-v2
    [*] --> Accepted
    Accepted --> Queued
    Accepted --> Executing
    Queued --> Executing
    Queued --> Cancelled
    Executing --> Suspended
    Suspended --> Executing
    Executing --> Cancelling
    Cancelling --> Cancelled
    Executing --> Succeeded
    Executing --> Failed
    Executing --> Retriable
    Retriable --> Queued
    Succeeded --> [*]
    Failed --> [*]
    Cancelled --> [*]
```

The distinction between `Accepted` and `Queued` is the one PLCopen draws between an axis command that is busy and one that is actively commanding. A client that cannot see it cannot tell "the robot has not started your work yet" from "the robot is working on it".

### 6.4 Queueing and blending

`BufferMode` on the submitted intent decides how it relates to what is already executing.

`Aborting` is the default and **shall** be accepted by every Server. It terminates the executing intent as `Cancelled` — with `Result.Failure` set to `Superseded` — and begins the new one.

`Buffered` queues the intent; it begins when its predecessor reaches `Succeeded`.

The four blending modes queue the intent and additionally ask that the robot not decelerate to a stop at the boundary. Where blending occurs, the predecessor reaches `Succeeded` **when blending begins**, not when its target is exactly attained, and its `Result.AchievedPose` **shall** record where the tool centre point was at that moment. This is the behaviour PLCopen defines, and reporting it any other way would tell a client the robot stopped somewhere it never was.

A Server that accepts a blending mode but executes it as `Buffered` **shall** report `BlendingSupported` false. A client can then tell a robot that blends from one that merely tolerates being asked to.

`MaxQueueDepth` bounds the queue. A Server with `MaxQueueDepth` zero accepts only `Aborting` submissions.

`BlockingMode` is orthogonal to `BufferMode` and constrains concurrency rather than ordering: whether motion may continue during the intent, and whether other intents may run alongside it. A Server **shall not** begin an intent whose `BlockingMode` is `Single` or `Hard` while any other intent is executing.

### 6.5 Cancellation — and what the `Cancel` Service is not

> The OPC UA `Cancel` Service defined in OPC 10000-4 §5.7.5 cancels an **outstanding service request**. It does not stop the robot. Invoking it against a submission returns `Bad_RequestCancelledByClient` for that request and leaves the motion running.

Stopping a robot is `CancelIntent`, `CancelMission` or `CancelAll` — Methods on the information model, with real-world effect. This distinction is normative because a specification that leaves it implicit produces implementations that believe they have a stop button and do not.

A Server **may refuse** a cancel, and reports that in the `Accepted` output. Some motions cannot be abandoned part-way without leaving the cell in a worse state than completing them — a tool change mid-exchange, a placement mid-release. A capability entry whose `CancelSupported` is false declares this in advance for a whole intent type; `Accepted` false reports it for one occasion.

Where a cancel is accepted, the operation enters `Cancelling` and then `Cancelled`. `Cancelling` is not terminal: a client that treats the acceptance of a cancel as the end of motion will act too early.

`StopMode` says how urgently to stop. It carries the values of `PossibleStopModes` in OPC 40010-1 so that a Server implementing both reports one vocabulary. It selects **no** IEC 60204-1 stop category; clause 10 explains why it cannot.

### 6.6 Pause, resume and retry

`Pause` suspends execution retaining position, and `Resume` continues it. Both are optional, and a capability entry declares per intent type whether they are honoured.

`Retriable` is a terminal state a Server uses where it judges an intent worth another attempt — a grasp that closed on nothing, a location that was momentarily blocked. `Retry` creates a **new** `IntentOperationType` instance for the new attempt; the original remains, terminal, with its own result. A Server that does not offer `Retry` never enters `Retriable` and reports `Failed` instead.

### 6.7 Results

When an operation reaches a terminal state its `Result` **shall** be complete and **shall not** change thereafter. The same `IntentResultDataType` value **shall** also be reachable under the inherited `FinalResultData` object, so that a client written against Part 10 finds the result where Part 10 says it will be.

`Result.AchievedPose` records where the driven tool centre point came to rest, or was when blending began. It is what lets a client audit a placement and distinguish a blended corner from an exact stop.

`Result.Failure` is a small, diagnosable set precisely so that a client can decide from it alone whether to retry, re-plan or escalate. `Message` is for a human and **shall not** be parsed.

A Server **shall** retain a terminated operation for long enough that a client which was disconnected at the moment of completion can still read its result on reconnection. It **may** then delete it; `AutoDelete` and `RecycleCount`, inherited from Part 10, describe what it does.

---

## 7 Missions (normative)

### 7.1 Purpose

A mission is an ordered sequence of intents submitted and tracked as a unit. It exists so that a supervisor can commit work in advance — the robot keeps moving through a sequence without a round trip per step — while retaining the ability to change what has not yet been committed.

`MissionDataType` (`ns=1;i=3068`) carries the mission: a client-assigned `MissionId`, a monotonically increasing `MissionUpdateId`, a `Label`, and the ordered `Steps`. `MissionType` (`ns=1;i=1004`) is the instance that tracks one, and like `IntentOperationType` it is a Part 10 program instance for the reasons §6.1 gives.

Missions are optional. `IntentCapabilitiesType.MissionsSupported` declares whether a Server implements them.

### 7.2 Base and horizon

Every step carries `Released`. The released steps form a prefix called the **base**; the rest form the **horizon**.

```mermaid
flowchart LR
    S0["Step 0<br/>released"] --> S1["Step 1<br/>released"]
    S1 --> S2["Step 2<br/>released"]
    S2 --> S3["Step 3<br/>horizon"]
    S3 --> S4["Step 4<br/>horizon"]
```

The base is **committed and immutable**. A Server **shall** assume every released step is executing or already executed, and **shall** refuse any update that would alter, remove or reorder one.

The horizon is provisional. `UpdateMission` replaces it wholly and **may** release some or all of its steps in doing so, extending the base.

`ReleasedStepCount` on the mission instance states how many steps are in the base, so a client does not have to scan the array to find the boundary.

A Server **shall** enforce all of the following, and **shall** apply an update atomically — an update either takes effect entirely or not at all:

1. `MissionUpdateId` **shall** be strictly greater than the mission's current value. An update that is not is refused with `Outdated`. This is what makes two updates that crossed in flight safe: the later one wins and the earlier one is rejected rather than applied out of order.
2. An update that would alter a released step is refused with `BaseConflict`.
3. `SequenceId` **shall** ascend across the steps of a mission, and `StepId` **shall** be unique within it.

### 7.3 Execution

A mission executes its steps in ascending `SequenceId`. Each step, when it begins, gets an `IntentOperationType` instance, and `MissionStepDataType.Operation` references it.

`MissionStepDataType.Status` is a **hint**. Where `Operation` is not null, that operation's state machine **decides**, and `Status` **shall** reflect it. Two members can report the state of one step; this sentence says which one is right.

A step that terminates `Failed` **shall** cause the mission to terminate `Failed` without beginning any later step. Release 0.1.0 defines no error-handling policy beyond this; a client that wants one submits the recovery itself.

`CancelMission` cancels the mission and every intent belonging to it, subject to the same right of refusal as `CancelIntent`.

---

## 8 Command authority (normative)

At most one Session at a time holds command authority over a controller, and only that Session **may** submit intents or missions. `ControlOwner` reports which.

`RequestControl` grants authority when no other Session holds it, or when the holder's Session has closed. A Server **shall** release authority automatically when the holding Session closes, so that a crashed client does not lock a robot permanently. `ReleaseControl` gives it up explicitly; outstanding intents are unaffected, and a client that wants them stopped calls `CancelAll` first.

Reading, browsing and subscribing require no authority. Observation is always permitted.

> Command authority arbitrates between OPC UA clients. It is **not** the single point of control required by ISO 10218-2, which concerns the mutual exclusion of remote command and local manual control and is enforced by safety-rated means outside this interface. A Server **shall not** present command authority as satisfying that requirement.

---

## 9 Capabilities and discovery (normative)

`IntentCapabilitiesType` is what makes an intent surface self-describing. A conformant Server **shall** populate it to reflect what it will actually accept — it is a contract, not documentation.

`SupportedIntents` carries one `IntentCapabilityDataType` per accepted intent type, naming the DataType and declaring whether cancel, pause and retry are honoured for it, which buffer and blocking modes it accepts, and which named `Attributes` this Server recognises.

Three rules keep the declaration honest, and each is checkable against a running Server:

1. A Server **shall** refuse an intent whose DataType is not listed, with `CapabilityNotSupported`.
2. Every entry's `SupportedBufferModes` **shall** include `Aborting`.
3. `BlendingSupported` **shall** be false unless the blending buffer modes actually blend.

`AxisCount` states how many entries `JointMoveIntentDataType.JointTargets` must carry, and **shall** equal the number of `AxisType` instances under the controller.

---

## 10 Safety (normative)

### 10.1 This interface is not safety-rated

**This specification defines a non-safety-rated application interface.** The Methods defined here are processed by the robot controller as application-level requests. They do not constitute, and **shall not** be used as, safety functions as defined in IEC 61508, nor safety communication as defined in IEC 61784-3 or IEC 62541-15.

The safety functions of the robot system — emergency stop, protective stop, speed and separation monitoring, force limiting, and enabling device control — are implemented in safety-rated hardware and firmware independent of this interface, and **shall** remain effective regardless of its state, including when the Server is unreachable, the Session has closed, or a client is submitting intents as fast as the Server will accept them.

A Server **shall not** claim, and a client **shall not** assume, any safety integrity level or performance level for any part of this model.

### 10.2 Operational mode gates submission

A Server **shall** refuse `SubmitIntent` and `SubmitMission` with `NotPermittedInMode` unless `OperationalMode` is `Automatic` or `AutomaticExternal`.

`OperationalMode` is read-only. This specification defines **no** way to command a mode change, because mode selection is a safety function performed by safety-rated means — a key switch, an interlock — and an interface that could change it from the network would defeat the arrangement it is reporting.

Where a person may be within the safeguarded space, the applicable safety standard, not this interface, decides what motion is permitted. A Server **shall not** rely on a client to observe such limits.

### 10.3 A stop request is not a stop category

`StopMode` expresses urgency. It **shall not** be interpreted as selecting, implying or guaranteeing any IEC 60204-1 stop category. Category 0, 1 and 2 stops are determined solely by the robot controller's safety system in response to the active operational mode and the risk assessment for the installation.

A client that requires a category-rated stop **shall** obtain it from the safety system. It cannot be obtained here.

### 10.4 Refusal is a normal outcome

Every rule above produces a refusal rather than a degraded execution, and each is observable against a running Server: a conformant Server can be seen to refuse a submission outside Automatic mode, and to refuse one from a Session that does not hold authority. A client **shall** treat refusal as an expected outcome and not as an error condition to be retried blindly.

---

## 11 Security

### 11.1 Commanding is a privileged operation

Every Method in this model moves a machine that can injure people and destroy property. A Server **shall** require an authenticated Session and **should** restrict the Methods of `IntentControllerType` by Role, distinctly from read access to the same address space. Observing a robot and commanding one are different privileges and **shall not** be conflated.

A Server **should** apply `UserExecutable` to the Methods it exposes so that a client discovers what it is permitted to invoke before invoking it.

### 11.2 Command authority is not authorisation

Command authority (clause 8) prevents two authorised clients from interleaving motion. It grants nothing. A Server **shall** apply its access control independently: a Session that holds authority but lacks the necessary Role **shall** still be refused.

### 11.3 NodeIds in intents are untrusted input

`PickIntentDataType.Source`, `SetOutputIntentDataType.Output`, `CallProgramIntentDataType.Program` and the other NodeId-valued members carry references chosen by the client. A Server **shall** validate that each resolves to a node of the expected type **under the controller being commanded**, and **shall** refuse with `ParameterInvalid` otherwise. A NodeId that resolves to a node belonging to a different controller, or to no node at all, **shall not** be acted on.

`CallProgramIntentDataType` deserves particular care: it runs code the Server holds. A Server **shall** restrict it to programs it has published as `ProgramType` instances, and **shall not** accept a program identifier that names anything else.

### 11.4 Cybersecurity is in scope of the safety case

ISO 10218-1 addresses cybersecurity where a vulnerability could compromise robot safety. A networked command interface is exactly such a surface. The measures above are therefore not merely good practice; where this interface is deployed on a robot subject to that standard, they form part of the case that the installation is safe.

---

## 12 Profiles and conformance units

### 12.1 Declaring conformance

A Server declares conformance by exposing `RobotIntentRootType` under the Server object with `SpecificationVersion` set to the release it implements, and by populating `IntentCapabilitiesType` truthfully.

### 12.2 Facets

| Facet | Requires |
|---|---|
| **RI-Base** (mandatory) | `RobotIntentRootType`; at least one `IntentControllerType` with `Capabilities`, `Frames`, `Tools`, `Locations`, `Axes` and `Intents`; `SubmitIntent`, `CancelIntent`, `CancelAll`, `RequestControl`, `ReleaseControl`; `IntentOperationType` instances with the state model of §6.3; the refusal rules of §6.2 and clause 10. |
| **RI-Motion-Joint** | `JointMoveIntentDataType`, with `AxisType` instances covering `0` to `AxisCount − 1`. |
| **RI-Motion-Linear** | `LinearMoveIntentDataType`. |
| **RI-Motion-Circular** | `CircularMoveIntentDataType`. |
| **RI-Grasp** | `GraspIntentDataType` and `ReleaseIntentDataType`, and at least one `ToolType` with a `TcpFrame`. |
| **RI-PickPlace** | `PickIntentDataType`, `PlaceIntentDataType`, and at least one `LocationType`. |
| **RI-ToolChange** | `ToolChangeIntentDataType`, and more than one `ToolType`. |
| **RI-Output** | `SetOutputIntentDataType` and the `Outputs` folder. |
| **RI-Program** | `CallProgramIntentDataType` and the `Programs` folder. |
| **RI-Wait** | `WaitIntentDataType`. |
| **RI-Queue** | `MaxQueueDepth` greater than zero; `Buffered` accepted; `QueuePosition` maintained. |
| **RI-Blending** | `BlendingSupported` true; the four blending buffer modes accepted and honoured; `Result.AchievedPose` reported at the blend point per §6.4. |
| **RI-Pause** | `Pause` and `Resume`. |
| **RI-Retry** | `Retry`, and `Retriable` reachable. |
| **RI-Mission** | `MissionsSupported` true; `SubmitMission`, `CancelMission`; `MissionType` instances. |
| **RI-Mission-Horizon** | **RI-Mission**, plus `MissionHorizonSupported` true, `UpdateMission`, and the base immutability rules of §7.2. |
| **RI-Interop-40010** | Annex B. |

A facet other than **RI-Base** is claimed only where every intent type it names appears in `SupportedIntents`.

---

## 13 Deliverables and reproducibility

| Artifact | Path |
|---|---|
| This specification | `metaverse-specs/robot-intent/OPC-UA-Robot-Intent.md` |
| Research report | `metaverse-specs/robot-intent/OPC-UA-Robot-Intent-Research.md` |
| Information model | `metaverse-specs/robot-intent/Opc.Ua.RobotIntent.NodeSet2.xml` |
| NodeId assignments | `metaverse-specs/robot-intent/Opc.Ua.RobotIntent.NodeIds.csv` |
| Generator | `metaverse-specs/extras/robot-intent/tools/build_model.py` |
| Validator | `metaverse-specs/extras/robot-intent/tools/validate_local.py` |
| Annex A (generated) | `metaverse-specs/extras/robot-intent/tools/model-reference.md` |

The NodeSet, the CSV and Annex A are generated from a single in-code source of truth and are **deterministic**: regenerating reproduces them byte for byte. The generator is edited; the generated files are not.

```powershell
python metaverse-specs\extras\robot-intent\tools\build_model.py
python metaverse-specs\extras\robot-intent\tools\validate_local.py
```

---

## Annex A — Information model (generated)

Annex A is generated from the NodeSet and is authoritative for identifiers, DataTypes, ValueRanks, ModellingRules, structure fields, enumeration values and Method signatures. See [`../extras/robot-intent/tools/model-reference.md`](../extras/robot-intent/tools/model-reference.md).

---

## Annex B — OPC 40010 interop profile (normative for RI-Interop-40010)

OPC 40010-1 describes the robot; this specification commands it. The two are joined by one reference and are otherwise independent — this model takes no dependency on the Robotics NodeSet, and a Server implementing only this specification is fully conformant.

A Server claiming **RI-Interop-40010** **shall**:

1. Expose a `HasIntentController` reference from the `MotionDeviceSystemType` instance describing the robot to the `IntentControllerType` instance that commands it. The inverse, `IntentControllerOf`, leads from the intent surface back to the machine.
2. Report `IntentControllerType.OperationalMode` with the same value as the corresponding OPC 40010-1 operational mode of that motion device system. The two **shall not** disagree; where they would, the OPC 40010-1 value is the robot's own report and decides.
3. Publish, as `ProgramType` instances under the controller's `Programs` folder, exactly those programs the OPC 40010-1 task control can load, so that `CallProgramIntentDataType` and the OPC 40010-1 task control name the same things.
4. Express the poses it publishes in frames whose transforms are consistent with the mounting and geometry the OPC 40010-1 model describes.

A Server **shall not** duplicate OPC 40010-1's topology in this model. `AxisType` exists here only to fix the order, kind and limits that a joint target needs; where OPC 40010-1 is also implemented, its axis description is the fuller one and this model's `AxisType` instances **shall** agree with it.

Note that OPC 40010-1 defines no tool centre point. `ToolType.TcpFrame` supplies the concept, and there is nothing in OPC 40010-1 for it to contradict.

---

## Annex C — Pose conversion (normative)

A Server that exchanges poses with a model using the core `ThreeDFrame` — OPC 40010-1, or a spatial-location model — **shall** convert as follows.

**Position.** `ThreeDCartesianCoordinates` `X`, `Y`, `Z` are metres, as is `Pose3DDataType.Position`. The mapping is the identity.

**Orientation.** The `A`, `B`, `C` fields of `ThreeDOrientation` are, per ISO 9787, rotations about the **X**, **Y** and **Z** axes of the reference frame — roll, pitch and yaw — applied as an **intrinsic** rotation in the order Z, then Y, then X. Angles are in radians.

Given `A` (roll), `B` (pitch), `C` (yaw), let

```text
cr = cos(A/2)   sr = sin(A/2)
cp = cos(B/2)   sp = sin(B/2)
cy = cos(C/2)   sy = sin(C/2)
```

then the unit quaternion ordered (x, y, z, w) is

```text
x = sr*cp*cy - cr*sp*sy
y = cr*sp*cy + sr*cp*sy
z = cr*cp*sy - sr*sp*cy
w = cr*cp*cy + sr*sp*sy
```

and the inverse is

```text
A = atan2( 2*(w*x + y*z), 1 - 2*(x*x + y*y) )
B = asin ( clamp( 2*(w*y - z*x), -1, +1 ) )
C = atan2( 2*(w*z + x*y), 1 - 2*(y*y + z*z) )
```

Three properties of this conversion are normative:

- The clamp in the expression for `B` is required. Floating-point error can carry the argument of `asin` outside `[−1, +1]`, and without the clamp a conversion that should yield a pole orientation yields a domain error instead.
- `q` and `−q` denote the same orientation. A Server **should** emit the representative whose `w` is non-negative, so that two Servers describing one orientation produce the same four numbers.
- The conversion is lossy in one direction only at the poles, where `B` is ±π/2 and roll and yaw are not separately recoverable. A Server converting a pose that originated as a quaternion **shall not** round-trip it through `ThreeDOrientation` when it can avoid doing so.

---

## Annex D — Informative alignments

These are **not** normative references and impose no dependency. They are recorded because this model borrowed from them deliberately, and an implementer who knows them will recognise what was borrowed.

- **PLCopen Motion Control** — `BufferModeEnum` adopts `MC_BufferMode` unchanged, including the rule that the predecessor completes when blending begins. The `Accepted` / `Queued` distinction is PLCopen's `Busy` without `Active`.
- **VDA 5050** — `BlockingModeEnum` is the `blockingType` matrix. The base/horizon mission model, the monotonic update identifier and the rejection of an outdated update are that specification's order model. `IntentCapabilitiesType` plays the role of its factsheet.
- **ROS 2 actions** — the goal handle returned on submission, the server's right to refuse a cancel, and the explicit `Cancelling` state before `Cancelled`.
- **MoveIt** — `MotionSequenceItem.blend_radius` is the same abstraction as `BlendDataType.Radius`.
- **OPC 10031-4 job control** — the separation of cancelling work that has not started from aborting work that has.
- **Capability–Skill–Service** (Plattform Industrie 4.0) — in that vocabulary this model is the **service** layer over a robot's **skills**, discovered by **capability**. `IntentCapabilitiesType` is the capability declaration.
- **Vendor motion languages** — URScript, RAPID, KRL, TP, INFORM and AS. The three motion intents are their common denominator, and `BlendDataType` is the portable form of `r`, `zonedata`, `$APO`, `CNT` and `PL`.
- **The OPC UA robot skill model** developed in the VDMA SOArc working group (`http://opcfoundation.org/UA/Skills/`) is prior art in this area. This specification uses a different namespace and does not extend it.
