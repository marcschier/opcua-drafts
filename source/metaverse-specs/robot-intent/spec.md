## Scope {#sec-scope}

This specification defines an OPC UA information model that lets a Server describe:

- **what a robot can be asked to do** — as a declared, machine-readable set of intents rather than a convention a client must know in advance;
- **how to ask it** — one submission per intent, or an ordered mission of them;
- **what happens next** — a lifecycle a client can observe from admission through queueing, execution and cancellation to a terminal result;
- **what the request refers to** — the frames, tools, locations, axes, signals and programs that give a pose or a place its meaning;
- **when the robot will refuse** — the operational modes, the command authority, and the boundary between this interface and the safety system that is never crossed.

### Motivation {#sec-motivation}

OPC 40010-1 describes robot **topology** in detail — the motion device system, its axes, its power trains, its controller, its safety states. It defines **no motion verbs at all**. Its entire actuation surface is `Start`, `Stop` and the loading of a named program over two state machines. A conformant client can discover everything about a robot's construction and cannot ask it to move anywhere.

The consequence is that every robot integration above the level of "run program 7" is bespoke. Two Servers can be fully conformant to OPC 40010-1 and still share no way to express *move the tool to this pose*. The verbs exist — every vendor has joint, linear and circular moves, a speed, an acceleration, a blend, a tool frame and a work frame — but they exist only in vendor languages that do not interoperate.

This specification supplies the verbs, and nothing else, so that the two compose rather than compete.

There is a second gap, and it is the harder one. A motion takes seconds; a pick takes a minute. An OPC UA `Call` cannot stay open that long — Session timeouts, SecureChannel re-keying and transport timeouts all bound it, and OPC 10000-4 is explicit that if the Session ends the result is discarded *"independent of the task actually performed at the Server"*. A synchronous method that commands a robot is therefore not merely inelegant; it loses the outcome of work that has already physically happened. Clause 6 addresses this, and it is the reason the model is shaped the way it is.

### Motivating use cases {#sec-motivating-use-cases}

- **Task-level cell control.** A cell controller sequences a robot, a fixture and a conveyor without embedding vendor motion code, because the robot's capability is declared and its verbs are portable.
- **Planner and agent integration.** A planner — symbolic, learned, or a language model — emits intents against a declared vocabulary, and receives structured failures it can re-plan against rather than a vendor error string.
- **Mixed-fleet work cells.** Two robots from different manufacturers execute the same mission definition, because the mission is expressed in intents and each Server translates into its own controller's language.
- **Long-running supervised operation.** A supervisory system submits a mission, watches it progress, revises the part that has not yet been committed, and cancels it cleanly when the upstream process changes.
- **Auditable commanding.** Every intent records which Session commanded it, when, with what arguments and to what outcome. Part 10 carries that in `ProgramDiagnostic`, which it leaves Optional; §6.1 promotes it to Mandatory here, because a capability a specification advertises cannot rest on a member a conformant Server may omit.

### What this specification does not do {#sec-what-this-specification-does-not-do}

Two of these are permanent boundaries. Neither is a deferral.

- It is **not** a real-time control channel. Trajectory *execution* is in scope — a client hands over a whole time-parameterised path and the robot's own motion kernel runs it (§6.8) — and where a high-rate channel is genuinely needed, this specification **brokers** it (§6.9). What it does not do is carry the samples: it defines no transport, closes no control loop, and runs at OPC UA rates. §4.3 draws that line as a normative limit rather than a caution.
- It is **not** a safety function, and it is **not** safety-rated. This is not a scoping preference; it is what the technology permits. OPC 10000-15 carries cyclic safety data from a provider to a consumer, and a client calling a Method has no way to supply safety-rated arguments — so no Method in this or any other companion specification can be a safety function. What **is** in scope is *awareness*: the model reports what the safety system is enforcing, and a Server **shall** refuse work that would exceed it. Clause 10 states both halves precisely.

Neither statement is about the importance of the omitted capability. The first is a division of labour with the layer beneath; the second is the boundary of what an OPC UA Method can be.

### Capabilities and versioning {#sec-capabilities-and-versioning}

This specification covers the intent vocabulary — joint, linear and circular moves, trajectories, Cartesian paths, force-controlled moves, grasping, picking and placing, tool change, output, program call, waiting, and six application processes — together with the execution lifecycle, queueing and blending, cancellation, missions with a committed base, a revisable horizon and a step graph, command authority, safety awareness, the robot's kinematic description, real-time channel brokerage, and capability declaration.

The NodeSet declares exactly one `RequiredModel` — the base OPC UA namespace — so a Server can adopt it without pulling in any companion model. A Server implements the facets it can honour and declares the rest false; only **RI-Base** is mandatory (§12.2).

---

## Overview and concepts {#sec-overview-and-concepts}

### The layered contract {#sec-the-layered-contract}

This specification occupies one band and touches neither the band above nor the two below.

```{figure}
id: fig-ri-layers
caption: The layered contract
source: figures/RobotIntent-Fig1-Layers.png
```

A Server implementing this specification **shall** translate intents into whatever its controller actually executes. It **shall not** require a client to know which controller that is: the point of the model is that the same intent, submitted to two Servers driving robots from two manufacturers, produces the same physical outcome within the tolerance each robot is capable of.

The safety layer is beside and beneath this interface and is never mediated by it. That relationship is normative and is stated in clause 10.

### Intent, not trajectory {#sec-intent-not-trajectory}

An intent says **what** is to be achieved and constrains **how far** the Server may go in achieving it. It does not say how. The Server owns path planning, inverse kinematics, singularity avoidance, collision checking and the choice of configuration.

This is what makes the model portable. Every vendor already solves those problems, differently and well; a specification that dictated the solution would be implementable by nobody. `MotionConstraintsDataType` is therefore a set of **bounds**, not a plan, and a Server **shall** clamp a request to what the robot is configured to permit rather than refuse it — except where clause 10 requires refusal.

The same reasoning applies to blending. `BlendDataType.Radius` is a request in metres because that is the only unit two vendors share; controllers that expose a unitless blend scale map it as best they can, and a Server that cannot honour the exact radius **shall** still succeed. A client that needs the exact path uses `Exact` termination, which every vendor implements identically.

### What this interface carries, and what it brokers {#sec-what-this-interface-carries-and-what-it-brokers}

OPC UA method invocation is not deterministic and, in the deployments this model is written for, completes in tens of milliseconds. Vendor real-time channels run two to four orders of magnitude faster on dedicated transports. That difference is not something a specification can argue away, so this model divides the work rather than pretending the gap is not there.

**Carried here — one submission, executed by the robot.** A trajectory, a Cartesian path or a force-controlled move is handed over *whole* and run by the robot's own motion kernel (§6.8). The round trip happens once, at submission, so the transport's latency bounds how quickly work can be *started* and never how accurately it is *executed*. This is the same shape as `FollowJointTrajectory` in ROS and the buffered path function blocks of PLCopen, and it is why trajectory execution belongs here while trajectory streaming does not.

**Brokered — described, leased, and left alone.** Where a client genuinely needs a high-rate channel — visual servoing, force tracking, conveyor following — the Server describes one and leases it (§6.9). The samples travel on that channel and never through this interface.

A Server **shall not** present this interface as a real-time control channel, and a client **shall not** use it as one. In particular:

- servo-level or joint-cyclic control **shall not** be attempted through repeated submission;
- a closed force or impedance loop requiring a bounded control period **shall** use a brokered channel, not `ForceIntentDataType`, which commands a *move until contact* and not a continuous loop;
- conveyor tracking, seam tracking and any other motion slaved to an external signal at rate **shall** use a brokered channel or the robot's own facility.

`IntentOperationType.CurrentPose` exists so a client can *watch* a motion. It is a status report delivered at whatever rate the client's Subscription asks for, and using it to close a control loop is outside this specification.

### Architecture {#sec-architecture}

```{figure}
id: fig-ri-architecture
caption: Architecture of an intent controller in the AddressSpace
source: figures/RobotIntent-Fig2-Architecture.png
```

A client browses `Server/RobotIntent/Controllers` to find every robot it may command, reads that controller's `Capabilities` to learn what it accepts, resolves the frames and locations its intents will refer to, and then submits.

---

## Information model {#sec-information-model}

The AddressSpace figures in this document use the OPC UA graphical notation of OPC 10000-3. A Node of an instance NodeClass — Object, Variable or View — is a plain rectangle, a Method is a rounded rectangle, and a type — ObjectType, VariableType, ReferenceType or DataType — is a rectangle standing on a shadow. An abstract type is set in *italics*, and a Node whose BrowseName is a placeholder is written in angle brackets. A `HasTypeDefinition` reference carries a solid arrowhead; a `HasComponent` reference is the plain unlabelled arrow; every other ReferenceType is drawn with its BrowseName on the arrow. A figure shows the part of the model its clause describes, never the whole of it.

```{figure}
id: fig-ri-notation
caption: Graphical notation used by the AddressSpace figures
source: figures/RobotIntent-FigNotation.png
```

### Type hierarchy {#sec-type-hierarchy}

The entry point is a root Object holding the controllers a Server exposes:

<!-- model-figure: root=ns=1;i=1001 require=mandatory external=BaseObjectType  graph=figures/fig-ri-hierarchy.mmd -->

```{figure}
id: fig-ri-hierarchy
caption: The type hierarchy
source: figures/RobotIntent-FigHierarchy.png
```

A controller carries the containers a client browses, the intent queue, and the control-ownership and submission Methods. The figure shows those; Annex A carries the full member list:

<!-- model-figure: root=ns=1;i=1002 external=BaseObjectType  graph=figures/fig-ri-controller.mmd -->

```{figure}
id: fig-ri-controller
caption: Instance structure of an intent controller
source: figures/RobotIntent-Fig3-Controller.png
```

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
| `SafetyStateType` | `ns=1;i=1012` | `BaseObjectType` |
| `RealTimeChannelType` | `ns=1;i=1013` | `BaseObjectType` |
| `RobotDescriptionType` | `ns=1;i=1014` | `BaseObjectType` |

Annex A is the authoritative node reference and carries every member with its DataType, ValueRank and ModellingRule.

### Poses, frames and units (normative) {#sec-poses-frames-and-units-normative}

`Pose3DDataType` (`ns=1;i=3050`) carries `FrameId`, a `Position` of three `Double` in **metres**, and an `Orientation` of four `Double` forming a **unit quaternion ordered (x, y, z, w)**.

Four rules make this unambiguous, and a Server **shall** satisfy all of them.

1. Every frame in this model is **right-handed**.
2. Position is in **metres**; joint targets are in **radians** for a `Revolute` axis and **metres** for a `Prismatic` one; force is in **newtons**; time is in **milliseconds** where carried as `Duration`. These units are fixed by this specification and are **not** negotiable per-instance. `Pose3DDataType` appears as a Method argument, where no `EUInformation` property can reach it, so a per-instance unit would be undeliverable.
3. `Orientation` **shall** be normalised. A Server receiving a quaternion whose norm differs from 1 by more than 1e-6 **shall** reject the intent with `ParameterInvalid`.
4. `FrameId` names a `CoordinateFrameType` instance under the controller's `Frames` folder. An empty `FrameId` means the Server's default work frame.

Quaternions are used because OPC UA defines no quaternion DataType anywhere, and because the `A`, `B`, `C` fields of the core `ThreeDOrientation` carry no convention of their own — the only normative assignment of meaning to them is external to the base specification. A quaternion has no such ambiguity, no gimbal degeneracy, and is what robot controllers and scene descriptions already hold internally. Annex C gives the normative bidirectional conversion to `ThreeDFrame`, so a Server that also speaks OPC 40010-1 or a spatial-location model can move between the two without inventing a convention.

### The intent hierarchy {#sec-the-intent-hierarchy}

Intents are a **DataType hierarchy**, not one Method per verb.

```{figure}
id: fig-ri-intenttree
caption: The intent DataType hierarchy
source: figures/RobotIntent-Fig4-IntentTree.png
```

Three consequences follow, and each is the reason for the choice:

- **A single intent and a mission step are the same shape.** `MissionStepDataType.Intent` is an `IntentDataType`, so nothing has to be expressed twice.
- **Extension is subtyping.** A vendor or a later part adds an intent by deriving from `IntentDataType`. It is then carried, queued, cancelled and reported by the existing machinery without a new Method.
- **Discovery is a read, not a probe.** `IntentCapabilitiesType.SupportedIntents` names each accepted DataType. A client learns what a robot accepts by reading one Variable, rather than by browsing for BrowseNames and inferring support from their presence.

`IntentDataType` carries what every intent needs: `IntentId`, `Label`, `BufferMode` and `BlockingMode`. `MotionIntentDataType` adds `ToolFrame`, `Constraints` and `Blend` — the members that are meaningless for `SetOutput` and essential for a move.

Fields whose DataType is one of the two abstract structures are emitted with `AllowSubTypes="true"`, so a client decoding a mission does not have to infer polymorphism from the abstractness of a DataType.

### Motion intents {#sec-motion-intents}

`JointMoveIntentDataType` (`ns=1;i=3055`) interpolates in joint space. The tool centre point's path is not controlled and **shall not** be relied on. It carries either explicit `JointTargets` or a `TargetPose`, and `HasJointTargets` decides which — a Boolean discriminator rather than a sentinel, so that neither field has to encode "unset".

Giving a pose rather than joint values is the *"move there, you choose how"* case: the Server solves the kinematics and selects a configuration. A Server **shall** reject a `JointMoveIntentDataType` whose `HasJointTargets` is true and whose `JointTargets` length differs from `IntentCapabilitiesType.AxisCount`, with `ParameterInvalid`.

`LinearMoveIntentDataType` (`ns=1;i=3056`) drives the tool centre point along a straight line. `CircularMoveIntentDataType` (`ns=1;i=3057`) drives it along the arc through `ViaPoint` to `Target`; only the **position** of `ViaPoint` defines the arc, and a Server **shall** ignore its orientation.

The three correspond to the instructions every vendor already has, which is why they are three and not one:

| This specification | UR | ABB | KUKA | FANUC | Yaskawa |
|---|---|---|---|---|---|
| `JointMoveIntentDataType` | `movej` | `MoveJ` / `MoveAbsJ` | `PTP` | `J` | `MOVJ` |
| `LinearMoveIntentDataType` | `movel` | `MoveL` | `LIN` | `L` | `MOVL` |
| `CircularMoveIntentDataType` | `movec` | `MoveC` | `CIRC` | `C` | `MOVC` |

### Paths, trajectories and contact {#sec-paths-trajectories-and-contact}

Three further motion intents cover the work that a single target pose cannot express.

`CartesianPathIntentDataType` (`ns=1;i=3074`) carries a list of `PathWaypointDataType` (`ns=1;i=3073`), each a pose with the blend that applies at it. It carries **no timing**: the Server paces it from `Constraints`. This is the portable form of a taught path, and per-waypoint blending is exactly what distinguishes it from a sequence of separate linear moves — the robot need not stop between waypoints.

`TrajectoryIntentDataType` (`ns=1;i=3072`) carries `TrajectoryPointDataType` (`ns=1;i=3070`) points, each with `TimeFromStart` and per-axis positions, optionally velocities and accelerations. Timing is what makes it a trajectory rather than a path. It also carries a `PathTolerance` and a `GoalTolerance`, both `MotionToleranceDataType` (`ns=1;i=3071`), and a `GoalTimeTolerance`, which is a `Duration` — lateness is one number, not a pose deviation. Between them, "did it work?" has an answer the client set rather than one the Server chose.

A Server **shall** reject a trajectory whose points are not in ascending `TimeFromStart` order, or whose `Positions` length differs from `AxisCount`, with `ParameterInvalid`. Where `MaxTrajectoryPoints` is non-zero, it **shall** reject a longer trajectory with `ParameterInvalid`.

The whole trajectory is submitted in one call and executed by the robot's own motion kernel. That is the point: the transport is on the critical path once, at submission, and never during execution (§4.3).

`ForceIntentDataType` (`ns=1;i=3075`) travels along `Direction` until `ContactForce` is reached or `MaxDistance` is exhausted. Exhausting the distance without contact **shall** be reported as `Failed` with `ObjectNotFound` — the intent was to touch something, and not touching it is not success. `HoldForce` keeps the robot pressing after contact instead of stopping.

A Server **shall** report `ForceControlSupported` false unless the robot genuinely regulates force. Accepting a force intent and ignoring the force would tell a client its part was pressed when it was only approached.

### Process intents {#sec-process-intents}

`ProcessIntentDataType` (`ns=1;i=3076`) is the abstract base of the intents that run an application process along a path. Beyond each process's own parameters it carries two things every process needs: `ProcessProgram`, referencing the procedure the equipment already holds, and `Attributes` for what this specification has not standardised.

| Intent | NodeId | Covers |
|---|---|---|
| `ArcWeldIntentDataType` | `ns=1;i=3077` | voltage, wire feed and travel speed, gas pre- and post-flow, arc start delay, crater fill, weave, seam tracking |
| `SpotWeldIntentDataType` | `ns=1;i=3078` | weld schedule, gun force, approach and retract distance, stack thickness, tip dress |
| `DispenseIntentDataType` | `ns=1;i=3079` | flow rate, trigger-on and trigger-off distance, bead width, material temperature, purge |
| `FastenIntentDataType` | `ns=1;i=3080` | joint reference, program number, torque, angle, snug torque |
| `PalletiseIntentDataType` | `ns=1;i=3081` | pattern, layer, row, column, item orientation |
| `SurfaceFinishIntentDataType` | `ns=1;i=3082` | contact force, feed rate, tool speed, step-over |

Each parameter set is the subset the vendor languages agree on — ABB `seamdata`/`welddata`/`weavedata`, FANUC weld schedules and KUKA ArcTech for arc welding, and their equivalents elsewhere. Where an installation works to a welding procedure specification, `WeldProcedureRef` names it and this specification does not restate its content.

Three of these deserve their reasoning stated.

**Seam tracking is a switch, not a channel.** `ArcWeldIntentDataType.SeamTrackingEnabled` asks the equipment to run *its own* seam-tracking facility for the duration of this weld. It does not make this interface a real-time one: §4.3 permits seam tracking through a brokered channel **or the robot's own facility**, and this is the second of those. The sensing, the correction and the control period stay inside the controller, where the arc voltage or laser seam finder already is; nothing is sampled, carried or closed over OPC UA. A Server whose equipment provides no such facility **shall** refuse an intent carrying `SeamTrackingEnabled` true with `CapabilityNotSupported`, rather than accepting it and welding an uncorrected path.

**Fastening is deliberately thin.** OPC 40450 and OPC 40451 already define industrial joining and tightening in full, including step-wise results and traces. Where a controller exposes such a model, `FastenIntentDataType.Joint` references the joint in that model and the result belongs there. Where no such model is exposed under the controller, `Joint` is null, the remaining fastening parameters stand alone, and a Server **shall** refuse a non-null `Joint` with `CapabilityNotSupported`. Restating torque strategies here would create a second definition of a fact that specification already owns — the same reason `PickIntentDataType.Source` references a `Location` node instead of naming a station in a string.

**Palletising references a pattern, not a computed pose.** `Pattern` is a `LocationType`, so the geometry has one definition a client can read and subscribe to, rather than being recomputed from indices independently on both sides and disagreeing.

`WeaveShapeEnum` (`ns=1;i=3018`) gives the oscillation across an arc weld seam: `None`, `Sine`, `Zigzag`, `Trapezoid`.

### Manipulation intents {#sec-manipulation-intents}

`GraspIntentDataType` and `ReleaseIntentDataType` actuate an end effector. `Force` and `Width` are requests: an end effector that cannot regulate force **shall** ignore `Force` and still succeed, because refusing would make the intent unusable on the majority of grippers that are open or closed and nothing else.

`PickIntentDataType` and `PlaceIntentDataType` reference a `LocationType` **node** through `Source` and `Destination`. They do not name a station in a string. A location therefore has exactly one definition — its pose, its occupancy, what it holds and how much of it — which a client can read, subscribe to and reason about. A free-text station identifier would be a second definition of the same fact, able to disagree with the first.

`ToolChangeIntentDataType` references the `ToolType` to fit; a null `Tool` releases the fitted tool and fits nothing.

### Auxiliary intents {#sec-auxiliary-intents}

`SetOutputIntentDataType` writes an `OutputSignalType` node, so the signal's range, unit and meaning are described once in the address space instead of being implied by a line name. `Value` is `BaseDataType` and **shall** match the signal's own DataType.

`CallProgramIntentDataType` runs a `ProgramType` held on the controller. It is the escape hatch for capability this model does not describe, and the bridge to the programs an OPC 40010-1 task control already exposes (Annex B).

`WaitIntentDataType` waits for a duration, for a signal, or for both. A mission needs it to express a rendezvous with something the robot does not control; without it a client has to hold the queue open from outside, which defeats the point of submitting a mission at all.

`Signal` is bounded so that §11.3 has something to check: it **shall** resolve either to an `OutputSignalType` instance under the controller being commanded, or to a Variable of DataType `Boolean` under it, and a Server **shall** refuse anything else with `ParameterInvalid`. A NodeId-valued member that no rule constrains cannot be validated, and an unvalidated NodeId is the surface §11.3 exists to close.

### Reference objects {#sec-reference-objects}

`CoordinateFrameType` instances form a tree through `HasFrameParent`, so a pose given in one frame can be re-expressed in another by composing the transforms along the path between them. `Role` follows ISO 9787, which standardises *which* frames exist; the transform between them is carried explicitly because no standard says how to calibrate it.

`ToolType.TcpFrame` **shall** reference a `CoordinateFrameType` whose `Role` is `Tool`. At most one `ToolType` instance under a controller **shall** have `Fitted` true at any time.

`AxisType.Index` fixes the position of that axis in `JointMoveIntentDataType.JointTargets`, and `Kind` fixes the unit of that entry. The indices of the axes under one controller **shall** be the contiguous range `0` to `AxisCount − 1`.

### What the controller itself reports {#sec-what-the-controller-itself-reports}

Four reports of `IntentControllerType` say what the robot is doing right now, and each is read-only and normative.
`ActiveMission` is required only where `MissionsSupported` is true, because a Server that does not implement
missions has no mission instance to reference.

- `OperationalMode` is the robot's own report of the mode in force. §10.2 gates submission on it and forbids commanding it.
- `Ready` is true exactly when the Server would admit a well-formed intent from the Session that holds command authority. A Server **shall** report it false whenever §6.2 or §10.4 would refuse for a reason that does not depend on the intent — outside `Automatic` or `AutomaticExternal`, under an emergency or protective stop, or with `SafetyControllerOk` false. It exists so a client can see that submitting is pointless without submitting to find out; it is a **hint about the Server**, and a Server **shall not** treat a client's having read it as licence to skip any check of §6.2.
- `ActiveIntent` references the `IntentOperationType` instance whose `ExecutionState` is `Executing` or `Cancelling`, and is null when none is. On a Server that supports missions, where the executing intent belongs to a mission, `ActiveMission` references that mission's `MissionType` instance; otherwise `ActiveMission` is null.
- `ControlOwner` reports the Session holding command authority, or null. Clause 8 governs it.

None of these is a substitute for the per-operation state of §6.3. Two members may not report the state of one intent: the operation's own state machine decides, and these summarise it.

### `RobotDescriptionType` {#sec-robotdescriptiontype}

`RobotDescriptionType` (`ns=1;i=1014`) carries enough of the robot's construction for a client to plan against it without a second specification: a `KinematicChain` of `KinematicJointDataType` (`ns=1;i=3084`) from the base outwards, a `MountingPose`, a `ReachRadius`, a `PayloadLimit`, and ceilings on tool centre point speed and acceleration.

Each `KinematicJointDataType` names the `AxisType` it corresponds to, its `Kind`, the `OriginTransform` of its frame within its predecessor's at zero position, and the unit `AxisVector` it rotates about or translates along.

This is **additive, not duplicative**. OPC 40010-1 describes a robot's topology and its axes in detail and defines no kinematic chain an inverse-kinematics solver could use, and no tool centre point at all. Where OPC 40010-1 is also implemented, its axis description is the fuller one and Annex B fixes which side decides.

*Table - RobotDescriptionType Definition* {#tbl-robotdescriptiontype-definition defines=RobotDescriptionType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:RobotDescriptionType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:Manufacturer | 0:LocalizedText | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Model | 0:String | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:KinematicChain | 1:KinematicJointDataType[] | 0:BaseDataVariableType | M |
| 0:HasComponent | Variable | 1:MountingPose | 1:Pose3DDataType | 0:BaseDataVariableType | O |
| 0:HasProperty | Variable | 1:ReachRadius | 0:Double | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:PayloadLimit | 0:Double | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:MaxCartesianSpeed | 0:Double | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:MaxCartesianAcceleration | 0:Double | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent |  |  |  |  |  |

### `SafetyStateType` {#sec-safetystatetype}

`SafetyStateType` (`ns=1;i=1012`) reports what the robot's safety system is doing: `ActiveFunction`, `EmergencyStopActive`, `ProtectiveStopActive`, `SafeSpeedLimitActive`, `SafeSpeedLimit`, `SafetyControllerOk` and a human-readable `LastStopReason`.

`SafeMotionFunctionEnum` (`ns=1;i=3013`) names the function being enforced, using the vocabulary of IEC 61800-5-2: `None`, `Sto`, `Ss1`, `Ss2`, `Sos`, `Sls`, `Slp`, `Sdi`, `Sbc`.

Every member is **read-only and a report**. The safety system enforces these independently of this interface and remains effective when the Server is unreachable. Clause 10 states what a Server must do with them and what a client may not conclude from them.

*Table - SafetyStateType Definition* {#tbl-safetystatetype-definition defines=SafetyStateType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:SafetyStateType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:ActiveFunction | 1:SafeMotionFunctionEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:EmergencyStopActive | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:ProtectiveStopActive | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:SafeSpeedLimitActive | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:SafeSpeedLimit | 0:Double | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:SafetyControllerOk | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:LastStopReason | 0:LocalizedText | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent |  |  |  |  |  |

### `RealTimeChannelType` {#sec-realtimechanneltype}

`RealTimeChannelType` (`ns=1;i=1013`) describes a high-rate channel the Server can offer, so a client can find and open one: `Transport`, `EndpointUrl`, `Initiator`, `NominalRate`, `PayloadDescriptor`, `RequiredMode`, `Available`, and the current `LeaseHolder` and `LeaseExpiry`.

`RealTimeTransportEnum` (`ns=1;i=3014`) names the transport: `Rtde`, `Egm`, `Fri`, `Rsi`, `MotoRos2`, `OpcUaFx`, `Other`. Of these only `OpcUaFx` — OPC UA FX, OPC 10000-80 to -84 — is an OPC Foundation specification; the rest are vendor channels this model describes without defining.

`ChannelInitiatorEnum` (`ns=1;i=3015`) says which end opens the connection: `Server` or `Client`. It is stated rather than left to the reader because getting it wrong is the usual reason a first connection attempt fails.

§6.9 defines the lease.

*Table - RealTimeChannelType Definition* {#tbl-realtimechanneltype-definition defines=RealTimeChannelType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:RealTimeChannelType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:ChannelId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Transport | 1:RealTimeTransportEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:EndpointUrl | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Initiator | 1:ChannelInitiatorEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:NominalRate | 0:Double | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:PayloadDescriptor | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:RequiredMode | 1:OperationalModeEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Available | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:LeaseHolder | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:LeaseExpiry | 0:UtcTime | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent |  |  |  |  |  |

### Enumerations {#sec-enumerations}

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
| `SafetyLimitExceeded` | 19 | Refused; the request would exceed a limit the safety system is enforcing (§10.3). |
| `NoTransition` | 20 | A mission branch point had no true outgoing transition, or the selected transition target did not resolve (§7.4). |

**`ErrorPolicyEnum`** (`ns=1;i=3016`) — what a mission does when a step does not succeed (§7.4): `Abort` 0 (the default), `Retry` 1, `Skip` 2, `Fallback` 3, `Compensate` 4.

**`DivergenceKindEnum`** (`ns=1;i=3017`) — how the transitions leaving one step relate, following the divergence of an IEC 61131-3 sequential function chart: `Alternative` 0 (exactly one is taken — an OR divergence), `Parallel` 1 (all are taken and the branches run concurrently — an AND divergence).

---

## Intent lifecycle (normative) {#sec-intent-lifecycle-normative}

### Why an intent is a program instance {#sec-why-an-intent-is-a-program-instance}

A `Call` cannot outlive the Session that made it, and OPC 10000-4 §5.12.2 states that when a Session ends the method result is discarded *"independent of the task actually performed at the Server"*. A robot commanded by a synchronous method therefore keeps moving after the answer has been thrown away — and OPC 10000-10 §4.1 gives the OPC Foundation's own resolution: a Method performs a calculation, a **Program** runs a batch process or a machine tool part program.

`SubmitIntent` accordingly returns as soon as the intent is **admitted**, not when the robot has finished. What it returns is a NodeId: an `IntentOperationType` instance created for that submission, which the client subscribes to for progress and reads for the result.

Building on `ProgramStateMachineType` rather than defining a fresh state machine buys four things this specification then does not have to invent: transition events, a terminal result object that survives the operation, invocation diagnostics recording which Session commanded what, and a lifetime model for the instance itself.

**Two of those are Optional in Part 10, and this specification promotes both.** `IntentOperationType` declares `FinalResultData` and `ProgramDiagnostic` **Mandatory**.

Inheriting them would not have been enough. §6.7 requires the result to be reachable under `FinalResultData`, and §1.2 advertises auditable commanding, which *is* `ProgramDiagnostic` and nothing else. Both would have rested on members a fully conformant Server could omit — so a Server could pass every conformance test while providing neither, and the two claims would be false against a legal implementation. Promoting them is what makes the claims testable rather than aspirational.

A promotion changes the ModellingRule and **nothing else**. Both members are therefore declared exactly as OPC 10000-10 declares them — `FinalResultData` an Object of `BaseObjectType` reached by `HasComponent`, and `ProgramDiagnostic` a Variable of `ProgramDiagnostic2Type` of DataType `ProgramDiagnostic2DataType`, also reached by `HasComponent`. Altering the reference type or the TypeDefinition would declare a *second* member beside the inherited one rather than promote it, and a client written against Part 10 would then find two.

### Submission {#sec-submission}

On `SubmitIntent` a Server **shall**, in this order:

1. Refuse with `ControlNotOwned` if the calling Session does not hold command authority (clause 8).
2. Refuse with `NotPermittedInMode` if `OperationalMode` is not `Automatic` or `AutomaticExternal` (clause 10).
3. Refuse with `CapabilityNotSupported` if the intent's DataType is not among `SupportedIntents`, or if its `BufferMode` or `BlockingMode` is not among those the capability entry permits.
4. Refuse with `ParameterInvalid` if a parameter is missing, malformed or out of range.
5. Refuse with `QueueFull` if admitting it would exceed `MaxQueueDepth`.
6. Otherwise create an `IntentOperationType` instance, assign an `IntentId` if the request left it empty, and return both.

A refusal at any of these steps **shall not** create an operation instance and **shall not** move the robot.

**A refusal is an output, not a `StatusCode`.** §10.5 makes refusal an ordinary outcome, so a Server **shall** return `Good` from `SubmitIntent` and report the refusal in its output arguments: `Accepted` false, `Failure` set to the `IntentFailureEnum` value named above, `Message` carrying detail for a human, `IntentId` empty and `Operation` null. On admission it returns `Accepted` true, `Failure` `None`, and the assigned `IntentId` and `Operation`. `SubmitMission` and `Retry` report a refusal the same way.

This is what makes the ordered rules above observable. A Server that signalled a refusal with a Bad `StatusCode` would tell a client only that something went wrong, and the whole point of a small, diagnosable failure set (§5.8) is that a client decides whether to retry, re-plan or escalate from that value alone. A Server **shall not** substitute a Bad `StatusCode` for one of these refusals. `Bad_` codes remain what they always were — the transport, the Session and the Service layer failing — and a client **shall** distinguish the two.

An `IntentId` returned by the Server **shall** be unique among the intents that Server currently holds. A client-supplied `IntentId` that collides with an outstanding one **shall** be refused with `ParameterInvalid`.

### States {#sec-states}

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

```{figure}
id: fig-ri-lifecycle
caption: The intent execution state model
source: figures/RobotIntent-Fig5-Lifecycle.png
```

The distinction between `Accepted` and `Queued` is the one PLCopen draws between an axis command that is busy and one that is actively commanding. A client that cannot see it cannot tell "the robot has not started your work yet" from "the robot is working on it".

### Queueing and blending {#sec-queueing-and-blending}

`BufferMode` on the submitted intent decides how it relates to what is already executing.

`Aborting` is the default and **shall** be accepted by every Server. It terminates the executing intent as `Cancelled` — with `Result.Failure` set to `Superseded` — and begins the new one.

A supersede carries no client-chosen `StopMode`, because the submission that caused it names none. The Server chooses, and **should** choose the most urgent stop the cell tolerates, since the successor is about to command motion of its own and the two must not overlap. A Server **should** document which mode a superseded intent is stopped with, so the behaviour is predictable rather than discovered.

`Buffered` queues the intent; it begins when its predecessor reaches `Succeeded`.

The four blending modes queue the intent and additionally ask that the robot not decelerate to a stop at the boundary. Where blending occurs, the predecessor reaches `Succeeded` **when blending begins**, not when its target is exactly attained, and its `Result.AchievedPose` **shall** record where the tool centre point was at that moment. This is the behaviour PLCopen defines, and reporting it any other way would tell a client the robot stopped somewhere it never was.

A Server that accepts a blending mode but executes it as `Buffered` **shall** report `BlendingSupported` false. A client can then tell a robot that blends from one that merely tolerates being asked to.

`MaxQueueDepth` bounds the queue. A Server with `MaxQueueDepth` zero accepts only `Aborting` submissions.

`BlockingMode` is orthogonal to `BufferMode` and constrains concurrency rather than ordering: whether motion may continue during the intent, and whether other intents may run alongside it. A Server **shall not** begin an intent whose `BlockingMode` is `Single` or `Hard` while any other intent is executing.

### Cancellation — and what the `Cancel` Service is not {#sec-cancellation-and-what-the-cancel-service-is-not}

> The OPC UA `Cancel` Service defined in OPC 10000-4 §5.7.5 cancels an **outstanding service request**. It does not stop the robot. Invoking it against a submission returns `Bad_RequestCancelledByClient` for that request and leaves the motion running.

Stopping a robot is `CancelIntent`, `CancelMission` or `CancelAll` — Methods on the information model, with real-world effect. This distinction is normative because a specification that leaves it implicit produces implementations that believe they have a stop button and do not.

A Server **may refuse** a cancel, and reports that in the `Accepted` output. Some motions cannot be abandoned part-way without leaving the cell in a worse state than completing them — a tool change mid-exchange, a placement mid-release. A capability entry whose `CancelSupported` is false declares this in advance for a whole intent type; `Accepted` false reports it for one occasion.

Where a cancel is accepted, the operation enters `Cancelling` and then `Cancelled`. `Cancelling` is not terminal: a client that treats the acceptance of a cancel as the end of motion will act too early.

`StopMode` says how urgently to stop. It carries the values of `PossibleStopModes` in OPC 40010-1 so that a Server implementing both reports one vocabulary. It selects **no** IEC 60204-1 stop category; clause 10 explains why it cannot.

A Server **shall** either honour the requested `StopMode` or treat every value as its single stop behaviour; it **shall not** vary silently between the two. Where it cannot differentiate, it **should** say so — the capability declaration is the natural place — because a client that asks for `OnPath` and silently receives a `QuickStop` has been told something untrue about how the cell came to rest. A Server that does differentiate **should** make the difference observable in `Result.AchievedPose`, which records where the tool centre point actually stopped.

### Pause, resume and retry {#sec-pause-resume-and-retry}

`Pause` suspends execution retaining position, and `Resume` continues it. Both are optional, and a capability entry declares per intent type whether they are honoured.

Suspending execution means the robot stops. A Server **shall not** report `Suspended` for an operation whose motion is still in progress: Part 10 defines that state as position retained, and a client or operator that reads it will act on the robot having come to rest. Since this specification defines no channel through which a Server can instruct an actuator to pause mid-motion, whether a Server can honour `Pause` for a running intent depends entirely on the underlying controller.

A Server that cannot suspend a running intent **shall** declare `PauseSupported` false for that intent type. It **may** still stop its queue on `Pause` - refusing to start further work is useful on its own - but the executing operation remains `Executing` until it finishes, and `Ready` **shall** reflect that no new work will be admitted. This is the same rule clause 9 applies to `BlendingSupported`: declare false rather than accept work that will not be performed.

`Retriable` is a terminal state a Server uses where it judges an intent worth another attempt — a grasp that closed on nothing, a location that was momentarily blocked. `Retry` creates a **new** `IntentOperationType` instance for the new attempt; the original remains, terminal, with its own result. A Server that does not offer `Retry` never enters `Retriable` and reports `Failed` instead.

`Retry` refuses like a submission does, and reports it the same way (§6.2): `Accepted` false with a `Failure` and a `Message`. A named intent that is not in `Retriable` is refused with `ParameterInvalid`, and one whose capability entry declares `RetrySupported` false with `CapabilityNotSupported`.

### Results {#sec-results}

When an operation reaches a terminal state its `Result` **shall** be complete and **shall not** change thereafter. The same `IntentResultDataType` value **shall** also be reachable under the `FinalResultData` object, which this specification promotes to **Mandatory** on `IntentOperationType` for exactly this reason — Part 10 leaves it Optional, and a **shall** that rests on a member a conformant Server may omit is not a requirement, so that a client written against Part 10 finds the result where Part 10 says it will be.

`Result.AchievedPose` records where the driven tool centre point came to rest, or was when blending began. It is what lets a client audit a placement and distinguish a blended corner from an exact stop.

`Result.Failure` is a small, diagnosable set precisely so that a client can decide from it alone whether to retry, re-plan or escalate. `Message` is for a human and **shall not** be parsed.

A Server **shall** retain a terminated operation for long enough that a client which was disconnected at the moment of completion can still read its result on reconnection. It **may** then delete it; `AutoDelete` and `RecycleCount`, inherited from Part 10, describe what it does.

**What decided this intent.** `IntentOperationType.DecidedBy` is an Optional `NodeId` naming the artefact that produced the intent's parameters — typically a result published by a perception model, or the model itself — and is null where a human taught the pose or a program held it.

It exists because a pick pose is increasingly computed rather than taught, and an investigation into why a cell did something starts at the motion. Without this member the trail ends exactly there: a Server can say *what* it was asked to do and *what happened*, and nothing about *what decided it*. A specification that publishes a model's digest, the deployment that served it and the result it produced, and then loses the thread at the point the robot actually moved, has documented everything except the step that mattered.

A Server **shall not** populate it with an identifier it cannot resolve at the moment of submission, and a client **shall not** assume the target is still resolvable later — the deciding artefact may be retained under a different lifetime than the operation, and §11.3 governs what a NodeId-valued member may point at. This model defines no type for the target and takes **no dependency** on any model that might: the base OPC UA namespace remains its only `RequiredModel` (§2), which is why this is a NodeId Property rather than a reference. Where the *OPC UA — Vision* model is also implemented, the natural value is the `ResultId`-bearing `VisionResultType` instance the pose came from, and Annex E.7 says what a consumer can then reconstruct.

### Trajectory execution (normative) {#sec-trajectory-execution-normative}

A trajectory is submitted like any other intent and tracked by the same lifecycle. Two things are particular to it.

**It is handed over whole.** A Server **shall** accept the entire trajectory at submission and execute it without further exchange. It **shall not** require a client to feed points during execution, because a transport that cannot guarantee the next point arrives in time cannot be part of the control loop (§4.3).

**Tolerance decides success.** While executing, a Server **shall** report `Failed` with `Kinematics` if deviation exceeds `PathTolerance`. At the end it **shall** report `Failed` with `Kinematics` if the final deviation exceeds `GoalTolerance`, and `Failed` with `Timeout` if completion is later than the final point's `TimeFromStart` by more than `GoalTimeTolerance`. A tolerance of zero or less means the Server applies its own, and a Server that applies its own **should** publish it in `Result.Outputs` so the client can learn what was actually enforced.

`Progress` is meaningful for a trajectory in a way it is not for a single move: a Server **should** report the fraction of `TimeFromStart` elapsed.

### Brokering a real-time channel (normative) {#sec-brokering-a-real-time-channel-normative}

Where a client needs a rate this interface cannot carry, the Server describes a channel and leases it. The samples travel on that channel; this specification defines no transport and inspects no payload.

`OpenRealTimeChannel` takes a lease. A Server **shall** refuse it — returning `Granted` false, with `Message` saying which of these it was — when the channel is not `Available`, when another Session holds the lease, when `OperationalMode` is not the channel's `RequiredMode`, or when the caller does not hold command authority. On success it returns the `EndpointUrl`, the `PayloadDescriptor` and a `LeaseExpiry`.

A Server **shall** bound `RequestedLease` to what it is willing to grant and report the bounded value in `LeaseExpiry`; a `RequestedLease` of zero or less asks for the Server's own default.

A lease **shall** lapse at `LeaseExpiry` unless renewed by a further `OpenRealTimeChannel` from the holding Session, and **shall** be released when that Session closes. This is the same reasoning as command authority in clause 8: a client that dies must not hold a resource for good.

`CloseRealTimeChannel` releases the lease explicitly.

Two rules keep the division of labour honest:

- While a channel lease is held, a Server **shall** refuse motion intents with `CapabilityNotSupported` unless it can genuinely arbitrate between the two sources. Two things commanding one robot with no arbitration is the failure this rule exists to prevent.
- A Server **shall not** represent a brokered channel as being under this interface's control. Its behaviour, its guarantees and its failure modes are the transport's.

Of the transports named, only `OpcUaFx` — OPC UA FX, OPC 10000-80 to -84 — is an OPC Foundation specification. It is the open path, and a Server that offers it gives a client something it can implement from published documents rather than from a vendor SDK.

### Events (normative) {#sec-events-normative}

An `IntentOperationType` is a `ProgramStateMachineType`, so OPC 10000-10 already raises a transition event whenever its state changes. What that event cannot carry is **which** intent changed and to **what outcome**: it names the state machine and the transition, and a consumer supervising a cell of robots must read the operation back to learn anything useful — by which time the Server may have recycled it, since §6.7 requires the result to outlive only a reconnect.

`IntentEventType` is the abstract base; `IntentCompletedEventType` and `MissionCompletedEventType` are what a Server raises. They do not replace the Part 10 transition events and a Server **shall** continue to raise those: a Part 10 client that knows nothing of this model still works.

| Type | Member | Type | Rule | Meaning |
|---|---|---|---|---|
| `IntentEventType` *(abstract)* | `IntentId` | String | M | The intent this event concerns |
| | `Operation` | NodeId | M | The `IntentOperationType` tracking it |
| | `IntentTypeId` | NodeId | M | The `IntentDataType` subtype that was submitted |
| | `MissionId` | String | O | Mission it belongs to, or empty |
| `IntentCompletedEventType` | `State` | `ExecutionStateEnum` | M | Terminal state |
| | `Failure` | `IntentFailureEnum` | M | Why it did not succeed, or `None` |
| | `Result` | `IntentResultDataType` | M | The full result |
| | `DecidedBy` | NodeId | O | What produced the intent's parameters (§6.7) |
| `MissionCompletedEventType` | `State` | `ExecutionStateEnum` | M | Terminal state of the mission |
| | `CompletedSteps` | UInt32 | M | How many steps reached a terminal state |
| | `FailedStepId` | String | O | The step that ended the mission, or empty |

**Raised once, and only on a terminal transition.** A Server **shall** raise `IntentCompletedEventType` exactly once per intent, on the transition into `Succeeded`, `Failed`, `Cancelled` or `Retriable`, and **shall not** raise it for an intermediate state. `Cancelling` is not terminal (§6.5), and an event raised there would tell a consumer the work had stopped while the robot was still moving. Where `Retry` creates a new operation (§6.6), that operation raises its own event on its own terminal transition; the original's event stands and is not retracted.

**`IntentTypeId` is what makes the event filterable.** It names the `IntentDataType` subtype submitted, so a client subscribes to picks — or to arc welds, or to everything that failed — with an `EventFilter` and the Server sends nothing else. Without it a consumer receives every completion in the cell and discards most of them, which is the cost events exist to avoid.

**`Result` is repeated deliberately.** It is the one piece of state these events duplicate, because the `Operation` node it would otherwise be read from need not still exist by the time a consumer reacts. Everything else is a reference to be followed.

**Where events are raised.** The well-known `RobotIntent` object declares `EventNotifier` with the `SubscribeToEvents` bit set and is the target of a `HasNotifier` reference from the Server object, so a client subscribes at either and receives every intent event in the Server. A Server **shall** additionally set `EventNotifier` on each `IntentControllerType` instance and **shall** add a `HasNotifier` reference from the `RobotIntent` object to it, so a client that supervises one robot subscribes to that robot alone. `SourceNode` **shall** be the `IntentControllerType` instance that executed the work.

**Severity.** A Server **shall** raise a completion whose `State` is `Succeeded` at a severity of 1 to 199, and one whose `State` is `Failed` at 500 or above. `Cancelled` and `Retriable` are the operator's or the client's own doing rather than a fault, and **should** be raised below 500.

**The time base is stated, not assumed.** Annex E.7 has a consumer correlating a completion raised here with a perception event raised by another Server, so whether the two clocks agree matters. `RobotIntentRootType.ClockSynchronised` is `true` only where this Server's clock is disciplined to an external reference shared with those systems, and `TimeSyncSource` names it. A Server **shall not** report it true on the strength of having set its clock once — the member asserts an ongoing discipline — and where it is `false` or absent a consumer **shall not** attribute a completion to an observation on timing alone.

Neither member is Mandatory and no synchronisation is required: most cells do not have a disciplined time base, and clause 4.3 already places anything needing tighter timing than this interface offers on a brokered channel. What is required is that a Server unable to support the correlation says so.

**These are events, not conditions.** A completion occurs and is over. A robot that is unable to accept work — `Ready` false, a protective stop active — is a *state* that persists, and OPC 10000-9 `ConditionType` is what models that; this specification defines no alarm types, because a Server that needs to alarm on a stop already has `SafetyStateType` to alarm from and nothing about such an alarm is specific to intent.

**Safety is unaffected.** These events report. Clause 10 governs what may be commanded and by what, and nothing in this clause changes it: a consumer **shall not** treat an event as authorisation for anything, and a Server **shall not** make any safety function contingent on one being delivered.

---

## Missions (normative) {#sec-missions-normative}

### Purpose {#sec-purpose}

A mission is an ordered sequence of intents submitted and tracked as a unit. It exists so that a supervisor can commit work in advance — the robot keeps moving through a sequence without a round trip per step — while retaining the ability to change what has not yet been committed.

`MissionDataType` (`ns=1;i=3068`) carries the mission: a client-assigned `MissionId`, a monotonically increasing `MissionUpdateId`, a `Label`, and the ordered `Steps`. `MissionType` (`ns=1;i=1004`) is the instance that tracks one, and like `IntentOperationType` it is a Part 10 program instance for the reasons §6.1 gives.

Missions are optional. `IntentCapabilitiesType.MissionsSupported` declares whether a Server implements them.

### Base and horizon {#sec-base-and-horizon}

Every step carries `Released`. The released steps form a prefix called the **base**; the rest form the **horizon**.

```{figure}
id: fig-ri-mission
caption: A mission base and horizon
source: figures/RobotIntent-Fig6-Mission.png
```

The base is **committed and immutable**. A Server **shall** assume every released step is executing or already executed, and **shall** refuse any update that would alter, remove or reorder one.

The horizon is provisional. `UpdateMission` replaces it wholly and **may** release some or all of its steps in doing so, extending the base.

`ReleasedStepCount` on the mission instance states how many steps are in the base, so a client does not have to scan the array to find the boundary.

A Server **shall** enforce all of the following, and **shall** apply an update atomically — an update either takes effect entirely or not at all:

1. `MissionUpdateId` **shall** be strictly greater than the mission's current value. An update that is not is refused with `Outdated`. This is what makes two updates that crossed in flight safe: the later one wins and the earlier one is rejected rather than applied out of order.
2. An update that would alter a released step is refused with `BaseConflict`.
3. `SequenceId` **shall** ascend across the steps of a mission, and `StepId` **shall** be unique within it.

### Execution {#sec-execution}

A mission executes its steps in ascending `SequenceId`. Each step, when it begins, gets an `IntentOperationType` instance, and `MissionStepDataType.Operation` references it.

`MissionStepDataType.Status` is a **hint**. Where `Operation` is not null, that operation's state machine **decides**, and `Status` **shall** reflect it. Two members can report the state of one step; this sentence says which one is right.

A step that terminates `Failed` **shall** cause the mission to terminate `Failed` without beginning any later step, **unless** the step declares an error policy that says otherwise (§7.4).

`CancelMission` cancels the mission and every intent belonging to it, subject to the same right of refusal as `CancelIntent`.

### The step graph (normative) {#sec-the-step-graph-normative}

A mission may carry `Transitions`, an array of `MissionTransitionDataType` (`ns=1;i=3083`). Where it is **empty**, the mission is the ordered sequence §7.3 describes and nothing else applies — which is what makes the graph an addition rather than a replacement.

The model is the step-and-transition form of an IEC 61131-3 sequential function chart, chosen over a behaviour tree because it is the notation the audience implementing this already knows, it has an IEC serialization, and it needs no tick loop.

Each transition carries `FromStepId`, `ToStepId`, a `Condition` and a `DivergenceKind`.

`Condition` is an OPC UA `ContentFilter` — the base specification's own filter grammar, reused rather than invented. A specification that defined its own expression language would oblige every implementer to write a parser for it, and would then have to say what happens when two parsers disagree. An empty filter is always true.

`DivergenceKind` says how the transitions leaving one step relate:

- `Alternative` — exactly one is taken, the first whose `Condition` holds, in `Transitions` order. A Server **shall** evaluate them in that order so that two clients reading the same mission predict the same branch.
- `Parallel` — all are taken, and the branches execute concurrently. A Server **shall** report `MissionBranchingSupported` false if it cannot run branches concurrently, rather than silently serialising them.

Where a step has outgoing transitions and none of their conditions holds, the mission **shall** terminate `Failed`
with `NoTransition`. A Server **shall** report the same outcome if the transition selected for execution no longer
resolves to a step of the mission. It **shall not** report `Succeeded`, because `Succeeded` means the mission ran as
requested and would falsely state that unexecuted work was complete.

A Server **shall** refuse a mission whose transitions name a `FromStepId` or `ToStepId` that is not a step of that mission, and one that mixes `Alternative` and `Parallel` on transitions leaving the same step.

**Error policies.** `MissionStepDataType.ErrorPolicy` says what happens when the step does not succeed:

| Policy | Behaviour |
|---|---|
| `Abort` | End the mission. The default, and what a mission without policies does. |
| `Retry` | Re-attempt the step. The Server bounds the attempts and reports `Failed` when they are exhausted. |
| `Skip` | Record the failure and continue with the next step. |
| `Fallback` | Continue at `FallbackStepId`. |
| `Compensate` | Run `FallbackStepId` to undo what has been done, then end the mission. |

A Server **shall** refuse a mission where `ErrorPolicy` is `Fallback` or `Compensate` and `FallbackStepId` does not name a step of that mission. `Compensate` differs from `Fallback` in what happens afterwards, and only in that: both run the fallback step, but `Compensate` then ends the mission rather than continuing.

Where a step's policy is honoured, the *mission* does not terminate `Failed` even though the *step* did — which is the whole reason the policies exist, and why §7.3's rule is stated as a default rather than an invariant.

---

## Command authority (normative) {#sec-command-authority-normative}

At most one Session at a time holds command authority over a controller, and only that Session **may** submit intents or missions. `ControlOwner` reports which.

`RequestControl` grants authority when no other Session holds it, or when the holder's Session has closed. A Server **shall** release authority automatically when the holding Session closes, so that a crashed client does not lock a robot permanently. `ReleaseControl` gives it up explicitly; outstanding intents are unaffected, and a client that wants them stopped calls `CancelAll` first.

Reading, browsing and subscribing require no authority. Observation is always permitted.

> Command authority arbitrates between OPC UA clients. It is **not** the single point of control required by ISO 10218-2, which concerns the mutual exclusion of remote command and local manual control and is enforced by safety-rated means outside this interface. A Server **shall not** present command authority as satisfying that requirement.

---

## Capabilities and discovery (normative) {#sec-capabilities-and-discovery-normative}

`IntentCapabilitiesType` is what makes an intent surface self-describing. A conformant Server **shall** populate it to reflect what it will actually accept — it is a contract, not documentation.

`SupportedIntents` carries one `IntentCapabilityDataType` per accepted intent type, naming the DataType and declaring whether cancel, pause and retry are honoured for it, which buffer and blocking modes it accepts, and which named `Attributes` this Server recognises. It is intentionally at intent-type granularity; it does not define per-member capabilities. The member-level scope of `FastenIntentDataType.Joint` is therefore structural: a client tells whether non-null `Joint` values are meaningful by browsing for the OPC 40450 / OPC 40451 joining or tightening model under the controller.

Four rules keep the declaration honest, and each is checkable against a running Server:

1. A Server **shall** refuse an intent whose DataType is not listed, with `CapabilityNotSupported`.
2. Every entry's `SupportedBufferModes` **shall** include `Aborting`.
3. `BlendingSupported` **shall** be false unless the blending buffer modes actually blend.
4. `PauseSupported` **shall** be false unless `Pause` actually suspends a *running* intent, per §6.6. Stopping only the queue is not suspending execution, and `Suspended` **shall not** be reported while the robot is still moving.

A fifth rule applies the same honesty to the **Method surface**, because a declaration a client cannot act on is worse than no declaration. Where a Server declares a capability, the Methods that make it usable **shall** be present on the controller and callable:

| Declaration | Methods or members that **shall** be present |
|---|---|
| `MissionsSupported` true | `SubmitMission`, `CancelMission` |
| `MissionsSupported` true | `ActiveMission` |
| `MissionHorizonSupported` true | `UpdateMission` |
| `RealTimeChannelsSupported` true | `OpenRealTimeChannel`, `CloseRealTimeChannel` |
| a capability entry with `PauseSupported` true | `Pause`, `Resume` |
| a capability entry with `RetrySupported` true | `Retry` |

These Methods are Optional on `IntentControllerType`, which is what makes the rule necessary: a Server can otherwise advertise missions while omitting `SubmitMission` entirely, and a client discovers the contradiction only by calling something that is not there. Like the others, this is observable against a running Server — browse the controller and compare what it offers with what it claims.

`AxisCount` states how many entries `JointMoveIntentDataType.JointTargets` must carry, and **shall** equal the number of `AxisType` instances under the controller.

Five further declarations cover the capability added beyond single moves. `TrajectorySupported` and `ForceControlSupported` say whether trajectories and force-controlled moves are accepted; `RealTimeChannelsSupported` whether channels are brokered; `MissionBranchingSupported` whether `Transitions` are evaluated at all; and `MaxTrajectoryPoints` bounds a trajectory, zero meaning the Server states no limit.

Each follows the same rule as `BlendingSupported`: a Server declares false rather than accepting work it will not actually perform. A Server that reports `MissionBranchingSupported` false executes the steps in order and ignores any transitions supplied, and a client reading that declaration knows not to express a branch it needs.

`SupportedFacets` is the same contract at the level of whole facets, and it is bound by every rule above. A facet is not a summary of the declaration a client has already read: some of what Table 12.2 requires — that blending modes are honoured, that the refusal rules of §6.2 are followed, that a mission base is immutable — cannot be established by reading the address space at all. Listing such a facet is therefore an attestation, and a Server that lists **RI-Blending** while treating the buffer modes as `Buffered` has made a false statement of exactly the kind rule 3 forbids, whatever `BlendingSupported` says. Clause 12.2 sets out which requirements are structural and which are attested.

---

## Safety (normative) {#sec-safety-normative}

### This interface is not safety-rated {#sec-this-interface-is-not-safety-rated}

**This specification defines a non-safety-rated application interface.** The Methods defined here are processed by the robot controller as application-level requests. They do not constitute, and **shall not** be used as, safety functions as defined in IEC 61508, nor safety communication as defined in IEC 61784-3 or IEC 62541-15.

The safety functions of the robot system — emergency stop, protective stop, speed and separation monitoring, force limiting, and enabling device control — are implemented in safety-rated hardware and firmware independent of this interface, and **shall** remain effective regardless of its state, including when the Server is unreachable, the Session has closed, or a client is submitting intents as fast as the Server will accept them.

A Server **shall not** claim, and a client **shall not** assume, any safety integrity level or performance level for any part of this model.

This is a property of the technology, not a choice this working group made. OPC 10000-15 carries cyclic safety data from a SafetyProvider to a SafetyConsumer; the consumer's request carries an identifier, a monitoring number and one octet of explicitly **non-safety** flags, so a caller has no channel through which to supply safety-rated arguments. Every safety fieldbus — PROFIsafe, CIP Safety, FSoE, openSAFETY — expresses a safety command as a **continuously asserted cyclic signal**, because the integrity argument rests on the fail-safe state that follows when assertion stops. A Method call has no defined behaviour when it stops being called, and therefore cannot be a safety function however it is labelled.

A specification that ignored this would not be merely wrong; it would encourage an integrator to rely on something that fails silently. §10.4 says what can honestly be done instead.

### Operational mode gates submission {#sec-operational-mode-gates-submission}

A Server **shall** refuse `SubmitIntent` and `SubmitMission` with `NotPermittedInMode` unless `OperationalMode` is `Automatic` or `AutomaticExternal`.

`OperationalMode` is read-only. This specification defines **no** way to command a mode change, because mode selection is a safety function performed by safety-rated means — a key switch, an interlock — and an interface that could change it from the network would defeat the arrangement it is reporting.

Where a person may be within the safeguarded space, the applicable safety standard, not this interface, decides what motion is permitted. A Server **shall not** rely on a client to observe such limits.

### A stop request is not a stop category {#sec-a-stop-request-is-not-a-stop-category}

`StopMode` expresses urgency. It **shall not** be interpreted as selecting, implying or guaranteeing any IEC 60204-1 stop category. Category 0, 1 and 2 stops are determined solely by the robot controller's safety system in response to the active operational mode and the risk assessment for the installation.

A client that requires a category-rated stop **shall** obtain it from the safety system. It cannot be obtained here.

### Safety awareness, and its limits {#sec-safety-awareness-and-its-limits}

What this specification *can* do is see what the safety system is enforcing and refuse work that would contradict it. `SafetyStateType` (§5.7.2) reports it, and the following are normative.

A Server **shall** refuse `SubmitIntent` and `SubmitMission`:

- with `SafetyLimitExceeded`, when `SafeSpeedLimitActive` is true and the intent's `Constraints.CartesianSpeed` exceeds `SafeSpeedLimit`;
- with `NotPermittedInMode`, when `EmergencyStopActive` or `ProtectiveStopActive` is true;
- with `NotPermittedInMode`, when `SafetyControllerOk` is false.

A Server **shall** publish `ActiveFunction`, `EmergencyStopActive`, `ProtectiveStopActive`, `SafeSpeedLimitActive`, `SafeSpeedLimit` and `SafetyControllerOk` as the safety system reports them, and **shall not** publish a value the safety system has not asserted.

Each of these is observable against a running Server: assert a protective stop and a conformant Server refuses; lower `SafeSpeedLimit` below a submitted speed and it refuses.

**What none of this makes true.** These refusals are an application-layer courtesy performed by non-safety-rated software. They reduce the number of requests the safety system has to reject; they are not a protective measure and nothing may be assumed from their presence. In particular:

- a client **shall not** treat a Server's acceptance of an intent as evidence that the motion is safe;
- a client **shall not** treat `SafeSpeedLimit` as a limit *this interface* enforces — the safety system enforces it, and would enforce it identically if this model did not exist;
- a Server **shall not** offer any Method that commands a safe motion function, changes an operational mode, or clears a stop. Those are safety functions, and clause 10.1 says why no Method here can be one.

The asymmetry is deliberate: this model may **observe** the safety system and **refuse** on what it sees, and may never **instruct** it.

### Refusal is a normal outcome {#sec-refusal-is-a-normal-outcome}

Every rule above produces a refusal rather than a degraded execution, and each is observable against a running Server: a conformant Server can be seen to refuse a submission outside Automatic mode, and to refuse one from a Session that does not hold authority. A client **shall** treat refusal as an expected outcome and not as an error condition to be retried blindly.

---

## Security {#sec-security}

### Commanding is a privileged operation {#sec-commanding-is-a-privileged-operation}

Every Method in this model moves a machine that can injure people and destroy property. A Server **shall** require an authenticated Session and **should** restrict the Methods of `IntentControllerType` by Role, distinctly from read access to the same address space. Observing a robot and commanding one are different privileges and **shall not** be conflated.

A Server **should** apply `UserExecutable` to the Methods it exposes so that a client discovers what it is permitted to invoke before invoking it.

### Command authority is not authorisation {#sec-command-authority-is-not-authorisation}

Command authority (clause 8) prevents two authorised clients from interleaving motion. It grants nothing. A Server **shall** apply its access control independently: a Session that holds authority but lacks the necessary Role **shall** still be refused.

### NodeIds in intents are untrusted input {#sec-nodeids-in-intents-are-untrusted-input}

`PickIntentDataType.Source`, `SetOutputIntentDataType.Output`, `CallProgramIntentDataType.Program` and the other NodeId-valued members carry references chosen by the client. A Server **shall** validate that each resolves to a node of the expected type **under the controller being commanded**, and **shall** refuse with `ParameterInvalid` otherwise. A NodeId that resolves to a node belonging to a different controller, or to no node at all, **shall not** be acted on.

The expected type is fixed for every such member, so that "the expected type" is a checkable statement rather than an instruction to guess:

| Member | Resolves to |
|---|---|
| `PickIntentDataType.Source`, `PlaceIntentDataType.Destination`, `PalletiseIntentDataType.Pattern` | a `LocationType` instance under the controller |
| `MotionIntentDataType.ToolFrame`, `ForceIntentDataType.FrameId` | a `CoordinateFrameType` instance under the controller; `ToolFrame` additionally of `Role` `Tool` |
| `ToolChangeIntentDataType.Tool` | a `ToolType` instance under the controller, or null to release the fitted tool |
| `SetOutputIntentDataType.Output` | an `OutputSignalType` instance under the controller; `Value` **shall** match that signal's own DataType |
| `CallProgramIntentDataType.Program`, `ProcessIntentDataType.ProcessProgram` | a `ProgramType` instance under the controller |
| `WaitIntentDataType.Signal` | an `OutputSignalType` instance under the controller, or a Variable of DataType `Boolean` under it |
| `FastenIntentDataType.Joint` | a joint in an OPC 40450 / OPC 40451 model under the controller where one is implemented; otherwise the intent's own parameters stand alone and the member is null |
| `IntentOperationType.DecidedBy` | any Node the Server can resolve at submission, or null. **The exception to the rule above**: it is written by the Server rather than supplied by a client, so it is not untrusted input, and it deliberately names an artefact this specification does not define — see §6.7 |

`CallProgramIntentDataType` deserves particular care: it runs code the Server holds. A Server **shall** restrict it to programs it has published as `ProgramType` instances, and **shall not** accept a program identifier that names anything else.

For `FastenIntentDataType.Joint`, absence of an OPC 40450 / OPC 40451 joining or tightening model under the controller is itself the discoverable structural statement that non-null `Joint` values are not supported. A Server in that case **shall** refuse a non-null `Joint` with `CapabilityNotSupported`. Where such a model is exposed, a `Joint` that does not resolve to a joint in that model is malformed input and **shall** be refused with `ParameterInvalid`.

### Cybersecurity is in scope of the safety case {#sec-cybersecurity-is-in-scope-of-the-safety-case}

ISO 10218-1 addresses cybersecurity where a vulnerability could compromise robot safety. A networked command interface is exactly such a surface. The measures above are therefore not merely good practice; where this interface is deployed on a robot subject to that standard, they form part of the case that the installation is safe.

---

## Profiles and conformance units {#sec-profiles-and-conformance-units}

```{clause}
kind: profiles
```

### Declaring conformance {#sec-declaring-conformance}

A Server declares conformance by exposing `RobotIntentRootType` under the Server object with `SpecificationVersion` set to the release it implements, by populating `IntentCapabilitiesType` truthfully, and by listing in `SupportedFacets` the facets of Table 12.2 that each controller satisfies.

`SupportedFacets` carries the facet names of Table 12.2 verbatim. It exists because conformance is otherwise not machine-readable: a client would have to re-derive the whole table from the address space, and since several rows are behavioural, two clients deriving independently could reach different conclusions about the same Server. This mirrors `ServerCapabilitiesType.ServerProfileArray` in OPC 10000-5, where a Server states its profiles rather than leaving them to be inferred.

A Server shall not list a facet whose structural requirements are unmet. The behavioural requirements are the Server's own attestation and are subject to the honesty rules of clause 9 — a Server that lists **RI-Blending** while treating the blending buffer modes as `Buffered` is making a false statement in exactly the sense clause 9 forbids, and is no more conformant than one that reports `BlendingSupported` true under the same conditions.

The NodeSet assigns every Node to one of four conformance units: `RobotIntent` for the ObjectTypes and their members, `RobotIntent DataTypes` for the intent hierarchy and the enumerations, `RobotIntent ReferenceTypes` for the references, and `RobotIntent Events` for the EventTypes of §6.10. The facets below are expressed over those Nodes, so a Server claiming a facet implements the units the facet's members belong to.

### Facets {#sec-facets}

Requirements are of two kinds. **Structural** requirements are settled by reading the address space and the capability declaration: a client can check them, and so can a compliance tool, without commanding the robot. **Behavioural** requirements — written below as accepting, honouring, maintaining or observing a rule — cannot be settled by reading, only by exercising the Server, and are the Server's attestation under clause 9.

| Facet | Requires |
|---|---|
| **RI-Base** (mandatory) | `RobotIntentRootType`; at least one `IntentControllerType` with `Capabilities`, `Frames`, `Tools`, `Locations`, `Axes` and `Intents`; `SubmitIntent`, `CancelIntent`, `CancelAll`, `RequestControl`, `ReleaseControl`; `IntentOperationType` instances with the state model of §6.3; the refusal rules of §6.2 and clause 10. |
| **RI-Motion-Joint** | `JointMoveIntentDataType`, with `AxisType` instances covering `0` to `AxisCount − 1`. |
| **RI-Motion-Linear** | `LinearMoveIntentDataType`. |
| **RI-Motion-Circular** | `CircularMoveIntentDataType`. |
| **RI-Trajectory** | `TrajectoryIntentDataType`, `TrajectorySupported` true, and the tolerance rules of §6.8. |
| **RI-Path** | `CartesianPathIntentDataType` and `TrajectorySupported` true. |
| **RI-Force** | `ForceIntentDataType` and `ForceControlSupported` true — the robot genuinely regulates force. |
| **RI-RealTimeChannel** | `RealTimeChannelsSupported` true; the `RealTimeChannels` folder with at least one `RealTimeChannelType`; `OpenRealTimeChannel` and `CloseRealTimeChannel` with the lease rules of §6.9. |
| **RI-Safety** | `SafetyState` populated from the safety system, and the refusals of §10.4. |
| **RI-Events** | The EventTypes of §6.10 and every rule in that clause. A Server claiming it **shall** raise `IntentCompletedEventType` for **every** intent that reaches a terminal state, including those it refused after admission and those cancelled by another client — a facet under which a Server may report some completions and not others is worth nothing, because silence would then be ambiguous between "still running" and "finished, unreported". `MissionCompletedEventType` is additionally required where **RI-Mission** is claimed. Raising these does not relieve a Server of the Part 10 transition events. |
| **RI-Description** | `Description` with a `KinematicChain` covering every axis, `ReachRadius`, `PayloadLimit` and `MaxCartesianSpeed`. |
| **RI-Process-ArcWeld** | `ArcWeldIntentDataType`. |
| **RI-Process-SpotWeld** | `SpotWeldIntentDataType`. |
| **RI-Process-Dispense** | `DispenseIntentDataType`. |
| **RI-Process-Fasten** | `FastenIntentDataType`. Support for non-null `Joint` is structural: where an OPC UA joining or tightening model is implemented, `Joint` resolves into it; where no such model is exposed under the controller, `Joint` is null and a non-null `Joint` is refused with `CapabilityNotSupported`. |
| **RI-Process-Palletise** | `PalletiseIntentDataType` and at least one `LocationType` describing a pattern. |
| **RI-Process-SurfaceFinish** | `SurfaceFinishIntentDataType` and **RI-Force**. |
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
| **RI-Mission-Branching** | **RI-Mission**, plus `MissionBranchingSupported` true, `Transitions` evaluated per §7.4, and the error policies honoured. |
| **RI-Interop-40010** | Annex B. |
| **RI-Interop-Vision** | Annex E. |

A facet other than **RI-Base** is claimed only where every intent type it names appears in `SupportedIntents`.

**RI-Base** additionally requires `SupportedFacets`, since a conformance claim that cannot be read is not a claim.

Conformance is therefore declared at two levels, and they answer different questions. `SupportedFacets` is a member of `IntentCapabilitiesType`, so it is stated **per controller**: a Server hosting two robots of different capability has two answers, and a client asking whether *this* controller blends must read *this* controller's list. `ServerProfileArray` is a member of the Server object, so it is stated **once for the Server**, which is the right granularity for a profile (§12.3) — a named shape an integrator specifies and a supplier builds to.

A Server **shall** publish the URI of every profile it claims in `Server/ServerCapabilities/ServerProfileArray`, and
**shall** also publish the facet URIs for every facet required by those profiles and every facet listed by any
controller in `SupportedFacets`. The two discovery paths **shall** agree: a profile URI shall be backed by at least one
controller whose `SupportedFacets` includes every facet in that profile, and a facet URI shall be backed by at least
one controller that lists the corresponding facet. A facet URI on the Server that no controller lists in
`SupportedFacets` is a claim nothing in the address space backs, and a client that read only one of them would be told
something untrue by the other.

### Profiles {#sec-profiles}

A facet is a building block. A **profile** is a complete claim: a named set of facets describing one plausible robot Server, which is what an integrator specifies and what two manufacturers implementing the same shape agree they have built. §1.2's use cases are written about profiles even though they do not use the word — a mixed-fleet cell works only because two robots claim the same one.

Four are defined. Each includes the **Robot Motion Server** set, and a Server **may** claim more than one: a robot that both follows paths and executes missions claims two.

Claiming a profile is claiming every facet in it, on the terms §12.2 sets out — structural requirements a client can check by reading, behavioural ones the Server attests to under clause 9. A profile is a shorter way to say the same thing, not a weaker one.

| Profile | Facets | The Server it describes |
|---|---|---|
| **Robot Motion Server** | RI-Base, RI-Motion-Joint, RI-Motion-Linear, RI-Description, RI-Safety | The baseline. A robot that can be commanded to a joint configuration or a Cartesian pose, that describes its own kinematics and limits, and that reports what its safety system is enforcing. |
| **Robot Handling Server** | Motion, plus RI-Motion-Circular, RI-Grasp, RI-PickPlace, RI-ToolChange, RI-Output, RI-Queue | Material handling. Picking, placing, changing tools and driving the discrete outputs a gripper needs, with a queue so a cell controller can stay ahead of the robot. |
| **Robot Path Server** | Motion, plus RI-Trajectory, RI-Path, RI-Blending | Continuous-path work. A whole path is handed over once and the robot's own motion kernel runs it, blending between segments rather than stopping at each. |
| **Robot Mission Server** | Motion, plus RI-Mission, RI-Program, RI-Wait, RI-Pause, RI-Retry | Long-running supervised operation. A mission is submitted, watched, paused, retried and cancelled, which is §1.2's fourth use case stated as a claim. |

**RI-Safety is in the baseline rather than optional to it.** Clause 10 is explicit that this specification is not safety-rated and that no Method here is a safety function. What it does require is a duty: the Server *reports* what the safety system enforces and *refuses* work that would exceed it. Every profiled Server owes that duty, because an integrator specifying a profile is entitled to assume a robot will decline an intent its safety configuration forbids rather than attempt it. A robot that cannot read its safety system claims facets individually and not a profile.

The process facets — **RI-Process-ArcWeld** and its siblings — are deliberately in no profile. A welding robot is a **Robot Path Server** that additionally claims **RI-Process-ArcWeld**, and bundling the process into a profile would have produced one profile per process and no way to say that the underlying motion is the same. The same reasoning keeps **RI-Force**, **RI-RealTimeChannel** and the two interop facets outside all four.

### Profile and facet URIs {#sec-profile-and-facet-uris}

A profile name is for a human. `ServerProfileArray` holds URIs, and unless this specification states them two Servers implementing the same profile publish different strings and no client can match either.

Profiles are published under `http://opcfoundation.org/UA-Profile/RobotIntent/Server/`:

| Profile | URI suffix |
|---|---|
| Robot Motion Server | `Motion` |
| Robot Handling Server | `Handling` |
| Robot Path Server | `Path` |
| Robot Mission Server | `Mission` |

Facets are published under `http://opcfoundation.org/UA-Profile/RobotIntent/Facet/`, with the suffix being the facet name after the `RI-` prefix: **RI-Base** is `Base`, **RI-Motion-Joint** is `Motion-Joint`, **RI-Process-ArcWeld** is `Process-ArcWeld`, and so on for every row of §12.2. A Server claiming a profile publishes the profile URI and the facet URIs that make the profile true; a Server claiming additional per-controller facets publishes those facet URIs as well. These URIs exist so a generic OPC UA tool that reads `ServerProfileArray` and knows nothing about robots can still recognise both the profile and the facets behind it; the authority on which facets a given controller satisfies is that controller's `SupportedFacets`, because only it is stated per controller.

These URIs are **provisional**, on the same terms as the namespace URI and the NodeIds: this is a working-group draft, and the OPC Foundation assigns the final values.

---

## Deliverables and reproducibility {#sec-deliverables-and-reproducibility}

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

## Information model reference {#anx-a annex=normative}

```{clause}
kind: annex-a
```

## OPC 40010 interop profile (normative for RI-Interop-40010) {#anx-b annex=normative}

OPC 40010-1 describes the robot; this specification commands it. The two are joined by one reference and are otherwise independent — this model takes no dependency on the Robotics NodeSet, and a Server implementing only this specification is fully conformant.

A Server claiming **RI-Interop-40010** **shall**:

1. Expose a `HasIntentController` reference from the `MotionDeviceSystemType` instance describing the robot to the `IntentControllerType` instance that commands it. The inverse, `IntentControllerOf`, leads from the intent surface back to the machine.
2. Report `IntentControllerType.OperationalMode` with the same value as the corresponding OPC 40010-1 operational mode of that motion device system. The two **shall not** disagree; where they would, the OPC 40010-1 value is the robot's own report and decides.
3. Publish, as `ProgramType` instances under the controller's `Programs` folder, exactly those programs the OPC 40010-1 task control can load, so that `CallProgramIntentDataType` and the OPC 40010-1 task control name the same things.
4. Express the poses it publishes in frames whose transforms are consistent with the mounting and geometry the OPC 40010-1 model describes.

A Server **shall not** duplicate OPC 40010-1's topology in this model. `AxisType` exists here only to fix the order, kind and limits that a joint target needs; where OPC 40010-1 is also implemented, its axis description is the fuller one and this model's `AxisType` instances **shall** agree with it. The same rule governs `RobotDescriptionType`: its `KinematicChain` is additive — OPC 40010-1 defines no kinematic chain — but where the two describe the same axis, **OPC 40010-1 decides** and this model reflects it.

Note that OPC 40010-1 defines no tool centre point. `ToolType.TcpFrame` supplies the concept, and there is nothing in OPC 40010-1 for it to contradict.

A Server claiming **RI-Interop-40010** together with **RI-Safety** **shall** report `SafetyStateType` consistently with the OPC 40010-1 safety state of the same motion device system. Where they would disagree, the OPC 40010-1 value is the robot's own report and decides — and neither is safety-rated, as both specifications say of themselves.

---

## Pose conversion (normative) {#anx-c annex=normative}

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

## Informative alignments {#anx-d annex=normative}

These are **not** normative references and impose no dependency. They are recorded because this model borrowed from them deliberately, and an implementer who knows them will recognise what was borrowed.

- **PLCopen Motion Control** — `BufferModeEnum` adopts `MC_BufferMode` unchanged, including the rule that the predecessor completes when blending begins. The `Accepted` / `Queued` distinction is PLCopen's `Busy` without `Active`.
- **VDA 5050** — `BlockingModeEnum` is the `blockingType` matrix. The base/horizon mission model, the monotonic update identifier and the rejection of an outdated update are that specification's order model. `IntentCapabilitiesType` plays the role of its factsheet.
- **ROS 2 actions** — the goal handle returned on submission, the server's right to refuse a cancel, and the explicit `Cancelling` state before `Cancelled`.
- **MoveIt** — `MotionSequenceItem.blend_radius` is the same abstraction as `BlendDataType.Radius`.
- **OPC 10031-4 job control** — the separation of cancelling work that has not started from aborting work that has.
- **Capability–Skill–Service** (Plattform Industrie 4.0) — in that vocabulary this model is the **service** layer over a robot's **skills**, discovered by **capability**. `IntentCapabilitiesType` is the capability declaration.
- **Vendor motion languages** — URScript, RAPID, KRL, TP, INFORM and AS. The three motion intents are their common denominator, and `BlendDataType` is the portable form of `r`, `zonedata`, `$APO`, `CNT` and `PL`. The process intents are drawn the same way: `ArcWeldIntentDataType` from ABB `seamdata`/`welddata`/`weavedata`, FANUC weld schedules and KUKA ArcTech; `SpotWeldIntentDataType` from ABB `SpotL` and FANUC SpotTool; `DispenseIntentDataType` from ABB `DispL`.
- **ROS `control_msgs/FollowJointTrajectory`** — the shape of `TrajectoryIntentDataType`, including the separation of path, goal and goal-time tolerance. Every ROS robot driver already accepts it, which is the point.
- **OPC UA FX** (OPC 10000-80 to -84) — the open transport a brokered channel may name, and the only one in `RealTimeTransportEnum` that is an OPC Foundation specification.
- **OPC 40450 / OPC 40451** (Industrial Joining Technologies) — where fastening results and joint definitions belong. `FastenIntentDataType` references them rather than restating them.
- **IEC 61131-3 sequential function charts** — the step, transition and divergence model of §7.4. Behaviour trees were considered and not adopted: their tick semantics need a runtime that controller vendors do not provide, and their serialization is a library's rather than a standard's.
- **ISO 15609** — welding procedure specifications, named by `ArcWeldIntentDataType.WeldProcedureRef` and not restated here.
- **The OPC UA robot skill model** developed in the VDMA SOArc working group (`http://opcfoundation.org/UA/Skills/`) is prior art in this area. This specification uses a different namespace and does not extend it.

---

## Vision interop profile (normative for RI-Interop-Vision) {#anx-e annex=normative}

A vision model that publishes a grasp pose and this model that executes it are deployed on the same cell, and each defines its own `CoordinateFrameType`. Without a rule the flange is described twice, with two `FrameId` strings and two transforms that can disagree.

This annex imposes **no** NodeSet dependency in either direction. Both models keep the base OPC UA namespace as their only `RequiredModel`, and a Server implementing only this one is unaffected.

**E.1 This model's frame tree decides.** Where a Server implements both for the same robot, the frames here are authoritative. This model owns `ToolType.TcpFrame` and is what the robot actually moves to; a pose that disagrees with it is wrong however carefully it was measured.

**E.2 `FrameId` corresponds by value.** A frame present in both models **shall** carry the same `FrameId` string in each. That string, not the NodeId, is what `Pose3DDataType` names.

**E.3 Roles correspond by name, never by number.** The two vocabularies agree on `World`, `Base`, `MechanicalInterface`, `Tool`, `Object` and `Other`. A vision model may additionally define a camera role, which this model does not; such a frame **shall** appear here as `Other`. A gateway **shall** map by literal name and **shall not** cast the integer between the two enumerations, because each is decoded against the DataType of the Variable carrying it.

**E.4 Poses transcode explicitly.** A vision pose may carry a covariance field this model's `Pose3DDataType` does not. A boundary **shall** drop it inbound and **shall not** fabricate one outbound. Both sides use metres and a unit quaternion ordered (x, y, z, w) in a right-handed frame, so no numeric conversion is required — but §5.2 rule 3 still applies, and an inbound pose whose quaternion is not normalised **shall** be rejected with `ParameterInvalid` rather than renormalised.

**E.5 An empty `FrameId` is not passed outward.** §5.2 rule 4 reads an empty `FrameId` as this Server's default work frame. A vision model may forbid an empty value entirely, so a boundary publishing a pose outward **shall** substitute the named frame explicitly.

**E.6 A grasp pose is resolved to the tool centre point.** A pose received for execution **shall** be resolved, through the frame tree, to the `Tool` frame named by the intent's `ToolFrame`. A hand-eye calibration resolves to the mechanical interface, and the offset from there to the tool centre point is exactly what it does not measure — so a Server **shall not** execute a pose that resolves only to `MechanicalInterface`, and **shall** refuse it with `ParameterInvalid`.

**E.7 This model is the authority on what the robot did.** A cell that wants to know a part was picked takes that from `IntentCompletedEventType` (§6.10), where `IntentTypeId` names `PickIntentDataType` and `State` is `Succeeded`. A vision model can report what a camera saw and cannot report what a robot did; this model can, and a consumer joining the two **shall** treat the completion as authoritative for the action and the observation as corroborating it.

This is why §6.10 carries `IntentTypeId`. It makes the kind of work the event is about selectable by an `EventFilter`, so a line controller subscribes to the completions it cares about — the picks, or everything that failed — without receiving and discarding the rest. The intent vocabulary is therefore also the manufacturing-event vocabulary: `pick`, `place` and the others are already named as intent types, and a completion event is what turns each of them into an occurrence something downstream can react to. A separate event vocabulary naming the same acts would be a second definition able to disagree with the first about what happened.

**E.8 The chain reaches the decision.** Where both models are implemented, `IntentOperationType.DecidedBy` (§6.7) **should** name the `VisionResultType` instance the intent's parameters came from. A consumer holding an `IntentCompletedEventType` can then follow `DecidedBy` to the result, the result to its pipeline and deployment, and the deployment to the model and its digest — so the question *which model caused this motion* is answerable from one notification and a walk, rather than by correlating two event streams on timing and hoping.

This is the one place the two models compose into something neither provides alone. The vision model can say which model produced a pose and cannot say whether a robot acted on it; this model can say what the robot did and, without `DecidedBy`, cannot say why. Populating it costs a Server that implements both nothing it does not already know at submission.

## Types the prose does not introduce {#sec-types-not-introduced}

The types below are declared by the model. Each clause was generated because no clause of this document named its type; fold them into the prose where they belong.

### RobotIntentRootType {#sec-robotintentroottype}

Server-level entry point. A client that has just connected browses here to find every robot it can command, without knowing the Server's layout.

*Table - RobotIntentRootType Definition* {#tbl-robotintentroottype-definition defines=RobotIntentRootType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:RobotIntentRootType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasComponent | Object | 1:Controllers |  | 0:FolderType | M |
| 0:HasProperty | Variable | 1:SpecificationVersion | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:ClockSynchronised | 0:Boolean | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:TimeSyncSource | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent |  |  |  |  |  |

### IntentControllerType {#sec-intentcontrollertype}

The intent surface for one robot: what it can be asked to do, the frames and objects those requests refer to, and the intents and missions currently outstanding. Everything a client needs in order to command the robot hangs from here.

*Table - IntentControllerType Definition* {#tbl-intentcontrollertype-definition defines=IntentControllerType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:IntentControllerType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:OperationalMode | 1:OperationalModeEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Ready | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:ControlOwner | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:MaxQueueDepth | 0:UInt32 | 0:PropertyType | M |
| 0:HasComponent | Variable | 1:ActiveIntent | 0:NodeId | 0:BaseDataVariableType | M |
| 0:HasComponent | Variable | 1:ActiveMission | 0:NodeId | 0:BaseDataVariableType | O |
| 0:HasComponent | Object | 1:Capabilities |  | 1:IntentCapabilitiesType | M |
| 0:HasComponent | Object | 1:Frames |  | 0:FolderType | M |
| 0:HasComponent | Object | 1:Tools |  | 0:FolderType | M |
| 0:HasComponent | Object | 1:Locations |  | 0:FolderType | M |
| 0:HasComponent | Object | 1:Axes |  | 0:FolderType | M |
| 0:HasComponent | Object | 1:Outputs |  | 0:FolderType | O |
| 0:HasComponent | Object | 1:Programs |  | 0:FolderType | O |
| 0:HasComponent | Object | 1:Intents |  | 0:FolderType | M |
| 0:HasComponent | Object | 1:Missions |  | 0:FolderType | O |
| 0:HasComponent | Method | 1:RequestControl |  |  | M |
| 0:HasComponent | Method | 1:ReleaseControl |  |  | M |
| 0:HasComponent | Method | 1:SubmitIntent |  |  | M |
| 0:HasComponent | Method | 1:CancelIntent |  |  | M |
| 0:HasComponent | Method | 1:CancelAll |  |  | M |
| 0:HasComponent | Method | 1:Pause |  |  | O |
| 0:HasComponent | Method | 1:Resume |  |  | O |
| 0:HasComponent | Method | 1:Retry |  |  | O |
| 0:HasComponent | Method | 1:SubmitMission |  |  | O |
| 0:HasComponent | Method | 1:UpdateMission |  |  | O |
| 0:HasComponent | Method | 1:CancelMission |  |  | O |
| 0:HasComponent | Object | 1:SafetyState |  | 1:SafetyStateType | M |
| 0:HasComponent | Object | 1:Description |  | 1:RobotDescriptionType | O |
| 0:HasComponent | Object | 1:RealTimeChannels |  | 0:FolderType | O |
| 0:HasComponent | Method | 1:OpenRealTimeChannel |  |  | O |
| 0:HasComponent | Method | 1:CloseRealTimeChannel |  |  | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent |  |  |  |  |  |

#### RequestControl {#sec-intentcontrollertype-requestcontrol type=IntentControllerType method=RequestControl}

Take command authority. A Server grants it only when no other Session holds it, or when the holder's Session has closed. Holding authority is a precondition for submitting, and exists so that two clients cannot interleave motion; it is NOT the single point of control that ISO 10218-2 requires, which is enforced by safety-rated means outside this interface.

**Signature**

```text
RequestControl (
  [out] 0:Boolean Granted,
  [out] 0:NodeId  CurrentOwner);
```

*Table - RequestControl Method Arguments* {#tbl-requestcontrol-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Granted | True when the caller now holds authority. |
| CurrentOwner | SessionId of the holder after the call. |

#### ReleaseControl {#sec-intentcontrollertype-releasecontrol type=IntentControllerType method=ReleaseControl}

Give up command authority. Outstanding intents are unaffected; use CancelAll to stop them.

**Signature**

```text
ReleaseControl ();
```

*Table - ReleaseControl Method Arguments* {#tbl-releasecontrol-method-arguments}

| **Argument** | **Description** |
| --- | --- |

#### SubmitIntent {#sec-intentcontrollertype-submitintent type=IntentControllerType method=SubmitIntent}

Submit one intent. Returns as soon as the intent is admitted - NOT when the robot has finished, which may be minutes later. The returned Operation is a node the client subscribes to for progress and reads for the result. This is the whole reason the model is built on the Part 10 program lifecycle: an OPC UA Call cannot stay open for the duration of a motion.

**Signature**

```text
SubmitIntent (
  [in]  1:IntentDataType    Intent,
  [out] 0:Boolean           Accepted,
  [out] 0:String            IntentId,
  [out] 0:NodeId            Operation,
  [out] 1:IntentFailureEnum Failure,
  [out] 0:LocalizedText     Message);
```

*Table - SubmitIntent Method Arguments* {#tbl-submitintent-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Intent | The intent to execute. |
| Accepted | True when the intent was admitted. False is a refusal, which clause 10.5 makes an ordinary outcome rather than an error. |
| IntentId | Identifier of the intent, assigned by the Server when the request left it empty. Empty on a refusal. |
| Operation | The IntentOperation that tracks it. Null on a refusal, because a refusal creates no operation instance. |
| Failure | Why the intent was refused, or None when it was admitted. |
| Message | Human-readable detail on a refusal. For a human; never parsed. |

#### CancelIntent {#sec-intentcontrollertype-cancelintent type=IntentControllerType method=CancelIntent}

Ask the Server to end an intent early. The Server MAY refuse, and says so in Accepted, because some motions cannot be abandoned safely part-way. This is not the OPC UA Cancel Service, which discards a pending response and leaves the robot moving; see clause 6.5.

**Signature**

```text
CancelIntent (
  [in]  0:String       IntentId,
  [in]  1:StopModeEnum StopMode,
  [out] 0:Boolean      Accepted);
```

*Table - CancelIntent Method Arguments* {#tbl-cancelintent-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| IntentId | The intent to cancel. |
| StopMode | How urgently to stop. |
| Accepted | True when the Server will act on it. |

#### CancelAll {#sec-intentcontrollertype-cancelall type=IntentControllerType method=CancelAll}

Ask the Server to end every outstanding intent and mission.

**Signature**

```text
CancelAll (
  [in]  1:StopModeEnum StopMode,
  [out] 0:UInt32       Cancelled);
```

*Table - CancelAll Method Arguments* {#tbl-cancelall-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| StopMode | How urgently to stop. |
| Cancelled | How many were acted on. |

#### Pause {#sec-intentcontrollertype-pause type=IntentControllerType method=Pause}

Suspend execution, retaining position so it can be resumed.

**Signature**

```text
Pause (
  [out] 0:Boolean Accepted);
```

*Table - Pause Method Arguments* {#tbl-pause-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Accepted | True when execution is suspending. |

#### Resume {#sec-intentcontrollertype-resume type=IntentControllerType method=Resume}

Continue execution suspended by Pause.

**Signature**

```text
Resume (
  [out] 0:Boolean Accepted);
```

*Table - Resume Method Arguments* {#tbl-resume-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Accepted | True when execution is resuming. |

#### Retry {#sec-intentcontrollertype-retry type=IntentControllerType method=Retry}

Re-attempt an intent that terminated Retriable.

**Signature**

```text
Retry (
  [in]  0:String            IntentId,
  [out] 0:Boolean           Accepted,
  [out] 0:NodeId            Operation,
  [out] 1:IntentFailureEnum Failure,
  [out] 0:LocalizedText     Message);
```

*Table - Retry Method Arguments* {#tbl-retry-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| IntentId | The intent to re-attempt. |
| Accepted | True when a new attempt was admitted. |
| Operation | The IntentOperation that tracks the new attempt. Null on a refusal. |
| Failure | Why the re-attempt was refused, or None when it was admitted. |
| Message | Human-readable detail on a refusal. |

#### SubmitMission {#sec-intentcontrollertype-submitmission type=IntentControllerType method=SubmitMission}

Submit an ordered sequence of intents as one unit. Steps marked Released form the base and are committed; the rest form the horizon and may still be revised by UpdateMission.

**Signature**

```text
SubmitMission (
  [in]  1:MissionDataType   Mission,
  [out] 0:Boolean           Accepted,
  [out] 0:String            MissionId,
  [out] 0:NodeId            Operation,
  [out] 1:IntentFailureEnum Failure,
  [out] 0:LocalizedText     Message);
```

*Table - SubmitMission Method Arguments* {#tbl-submitmission-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Mission | The mission to execute. |
| Accepted | True when the mission was admitted. |
| MissionId | Identifier of the mission, assigned by the Server when the request left it empty. Empty on a refusal. |
| Operation | The Mission that tracks it. Null on a refusal. |
| Failure | Why the mission was refused, or None when it was admitted. |
| Message | Human-readable detail on a refusal. |

#### UpdateMission {#sec-intentcontrollertype-updatemission type=IntentControllerType method=UpdateMission}

Replace the horizon of a mission already submitted. The base is untouchable: it has been committed and may already have executed, so an update that would alter a released step is refused rather than partly applied.

**Signature**

```text
UpdateMission (
  [in]  0:String                  MissionId,
  [in]  0:UInt32                  MissionUpdateId,
  [in]  1:MissionStepDataType[]   Steps,
  [out] 1:MissionUpdateResultEnum Result,
  [out] 0:LocalizedText           Message);
```

*Table - UpdateMission Method Arguments* {#tbl-updatemission-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| MissionId | The mission to update. |
| MissionUpdateId | Revision of the update. Must be greater than the mission's current value. |
| Steps | The steps that replace the horizon. |
| Result | Outcome of the update. |
| Message | Human-readable detail on a refusal. |

#### CancelMission {#sec-intentcontrollertype-cancelmission type=IntentControllerType method=CancelMission}

Ask the Server to end a mission and every intent belonging to it.

**Signature**

```text
CancelMission (
  [in]  0:String       MissionId,
  [in]  1:StopModeEnum StopMode,
  [out] 0:Boolean      Accepted);
```

*Table - CancelMission Method Arguments* {#tbl-cancelmission-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| MissionId | The mission to cancel. |
| StopMode | How urgently to stop. |
| Accepted | True when the Server will act on it. |

#### OpenRealTimeChannel {#sec-intentcontrollertype-openrealtimechannel type=IntentControllerType method=OpenRealTimeChannel}

Take a lease on a brokered real-time channel. The Server prepares the transport and returns what the client needs in order to connect; it does not carry the samples. A lease that is not renewed lapses, which is what stops a dead client from holding the channel.

**Signature**

```text
OpenRealTimeChannel (
  [in]  0:String        ChannelId,
  [in]  0:Duration      RequestedLease,
  [out] 0:Boolean       Granted,
  [out] 0:String        EndpointUrl,
  [out] 0:String        PayloadDescriptor,
  [out] 0:UtcTime       LeaseExpiry,
  [out] 0:LocalizedText Message);
```

*Table - OpenRealTimeChannel Method Arguments* {#tbl-openrealtimechannel-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| ChannelId | The channel to open. |
| RequestedLease | How long the lease is wanted for, in milliseconds. |
| Granted | True when the lease was taken. |
| EndpointUrl | Where to connect. |
| PayloadDescriptor | The transport's own configuration. |
| LeaseExpiry | When the lease lapses. |
| Message | Human-readable detail on a refusal. For a human; never parsed. |

#### CloseRealTimeChannel {#sec-intentcontrollertype-closerealtimechannel type=IntentControllerType method=CloseRealTimeChannel}

Give up a lease on a brokered channel.

**Signature**

```text
CloseRealTimeChannel (
  [in]  0:String  ChannelId,
  [out] 0:Boolean Released);
```

*Table - CloseRealTimeChannel Method Arguments* {#tbl-closerealtimechannel-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| ChannelId | The channel to release. |
| Released | True when the lease was held and is now released. |

### IntentOperationType {#sec-intentoperationtype}

One submitted intent, tracked to completion. It is a Part 10 program instance, so its lifecycle is the one OPC UA already defines for work that outlives a service call: transitions raise ProgramTransitionEvents, the terminal result survives in FinalResultData, and ProgramDiagnostic2DataType records which Session commanded it without this specification having to model provenance itself.

*Table - IntentOperationType Definition* {#tbl-intentoperationtype-definition defines=IntentOperationType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:IntentOperationType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:ProgramStateMachineType defined in [](#ref-uapart5) |  |  |  |  |  |
| 0:HasProperty | Variable | 1:IntentId | 0:String | 0:PropertyType | M |
| 0:HasComponent | Variable | 1:Intent | 1:IntentDataType | 0:BaseDataVariableType | M |
| 0:HasProperty | Variable | 1:ExecutionState | 1:ExecutionStateEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Progress | 0:Double | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:CurrentPose | 1:Pose3DDataType | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:Result | 1:IntentResultDataType | 0:BaseDataVariableType | M |
| 0:HasProperty | Variable | 1:MissionId | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:QueuePosition | 0:UInt32 | 0:PropertyType | O |
| 0:HasComponent | Object | 0:FinalResultData |  | 0:BaseObjectType | M |
| 0:HasComponent | Variable | 0:ProgramDiagnostic | 0:ProgramDiagnostic2DataType | 0:ProgramDiagnostic2Type | M |
| 0:HasProperty | Variable | 1:DecidedBy | 0:NodeId | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent |  |  |  |  |  |

### MissionType {#sec-missiontype}

One submitted mission, tracked to completion. It is a Part 10 program instance for the same reasons an IntentOperation is, and it owns the IntentOperations of its steps.

*Table - MissionType Definition* {#tbl-missiontype-definition defines=MissionType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:MissionType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:ProgramStateMachineType defined in [](#ref-uapart5) |  |  |  |  |  |
| 0:HasProperty | Variable | 1:MissionId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:MissionUpdateId | 0:UInt32 | 0:PropertyType | M |
| 0:HasComponent | Variable | 1:Mission | 1:MissionDataType | 0:BaseDataVariableType | M |
| 0:HasProperty | Variable | 1:ExecutionState | 1:ExecutionStateEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:CurrentStepId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:ReleasedStepCount | 0:UInt32 | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent |  |  |  |  |  |

### IntentCapabilitiesType {#sec-intentcapabilitiestype}

What one robot will accept. A client reads this once, before it submits anything, and knows what the robot can do and under what constraints.

*Table - IntentCapabilitiesType Definition* {#tbl-intentcapabilitiestype-definition defines=IntentCapabilitiesType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:IntentCapabilitiesType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasComponent | Variable | 1:SupportedIntents | 1:IntentCapabilityDataType[] | 0:BaseDataVariableType | M |
| 0:HasProperty | Variable | 1:MissionsSupported | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:MissionHorizonSupported | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:BlendingSupported | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:MaxBlendRadius | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:AxisCount | 0:UInt32 | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:TrajectorySupported | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:ForceControlSupported | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:RealTimeChannelsSupported | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:MissionBranchingSupported | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:MaxTrajectoryPoints | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:SupportedFacets | 0:String[] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent |  |  |  |  |  |

### CoordinateFrameType {#sec-coordinateframetype}

A named right-handed Cartesian frame. Frames form a tree through HasFrameParent, so a client can compose a chain from a tool frame to a world frame. Roles follow ISO 9787, which standardises which frames exist; the transform between them is carried explicitly because no standard says how to calibrate it.

*Table - CoordinateFrameType Definition* {#tbl-coordinateframetype-definition defines=CoordinateFrameType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:CoordinateFrameType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:FrameId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Role | 1:FrameRoleEnum | 0:PropertyType | M |
| 0:HasComponent | Variable | 1:Transform | 1:Pose3DDataType | 0:BaseDataVariableType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent |  |  |  |  |  |

### ToolType {#sec-tooltype}

An end effector. Its tool centre point is a CoordinateFrame of role Tool, which is what a motion intent drives to a target - OPC 40010-1 models robot topology in detail but has no tool centre point at all, so this specification supplies one.

*Table - ToolType Definition* {#tbl-tooltype-definition defines=ToolType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ToolType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:ToolId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Name | 0:LocalizedText | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Fitted | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:TcpFrame | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Mass | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:MaxGraspForce | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:MaxOpening | 0:Double | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent |  |  |  |  |  |

### LocationType {#sec-locationtype}

A named place an intent can refer to. Pick and Place reference these nodes rather than naming a station in a string, so a location has one definition that a client can read, subscribe to and reason about.

*Table - LocationType Definition* {#tbl-locationtype-definition defines=LocationType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:LocationType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:LocationId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Name | 0:LocalizedText | 0:PropertyType | M |
| 0:HasComponent | Variable | 1:Pose | 1:Pose3DDataType | 0:BaseDataVariableType | M |
| 0:HasProperty | Variable | 1:Occupied | 0:Boolean | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:ObjectClass | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Capacity | 0:UInt32 | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent |  |  |  |  |  |

### AxisType {#sec-axistype}

One axis of the robot. The order of these nodes under the controller's Axes folder fixes the order of JointMoveIntentDataType.JointTargets, and Kind fixes each entry's unit.

*Table - AxisType Definition* {#tbl-axistype-definition defines=AxisType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:AxisType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:AxisId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Index | 0:UInt32 | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Kind | 1:AxisKindEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:MinPosition | 0:Double | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:MaxPosition | 0:Double | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:MaxSpeed | 0:Double | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:Position | 0:Double | 0:BaseDataVariableType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent |  |  |  |  |  |

### OutputSignalType {#sec-outputsignaltype}

A signal SetOutput can write. Modelling it as a node means the range, the unit and the meaning are described once, instead of every client having to know what a line name implies.

*Table - OutputSignalType Definition* {#tbl-outputsignaltype-definition defines=OutputSignalType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:OutputSignalType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:SignalId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Name | 0:LocalizedText | 0:PropertyType | M |
| 0:HasComponent | Variable | 1:Value | 0:BaseDataType | 0:BaseDataVariableType | M |
| 0:HasProperty | Variable | 1:Writable | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:EngineeringUnits | 0:EUInformation | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent |  |  |  |  |  |

### ProgramType {#sec-programtype}

A program held on the controller that CallProgram can run. This is the bridge to capability this specification does not model, and to the programs an OPC 40010-1 task control already exposes.

*Table - ProgramType Definition* {#tbl-programtype-definition defines=ProgramType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ProgramType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:ProgramId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Name | 0:LocalizedText | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Description | 0:LocalizedText | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:Parameters | 0:KeyValuePair[] | 0:BaseDataVariableType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent |  |  |  |  |  |

### IntentEventType {#sec-intenteventtype}

Abstract base of every event this model raises. It identifies the work the event is about, and its subtypes say what became of it. Time is inherited from BaseEventType and is when the reported transition occurred.

*Table - IntentEventType Definition* {#tbl-intenteventtype-definition defines=IntentEventType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:IntentEventType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseEventType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:IntentId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Operation | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:IntentTypeId | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:MissionId | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent Events |  |  |  |  |  |

### IntentCompletedEventType {#sec-intentcompletedeventtype}

An intent reached a terminal state. Raised exactly once per intent, on the transition into Succeeded, Failed, Cancelled or Retriable, and never for an intermediate state - Cancelling is not terminal (clause 6.5) and an event raised there would tell a consumer the work had stopped while the robot was still moving.

*Table - IntentCompletedEventType Definition* {#tbl-intentcompletedeventtype-definition defines=IntentCompletedEventType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:IntentCompletedEventType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:IntentEventType defined in [](#sec-intenteventtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 1:State | 1:ExecutionStateEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Failure | 1:IntentFailureEnum | 0:PropertyType | M |
| 0:HasComponent | Variable | 1:Result | 1:IntentResultDataType | 0:BaseDataVariableType | M |
| 0:HasProperty | Variable | 1:DecidedBy | 0:NodeId | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent Events |  |  |  |  |  |

### MissionCompletedEventType {#sec-missioncompletedeventtype}

A mission reached a terminal state. IntentId carries the last intent the mission ran, so a consumer that missed the per-intent events still learns where the mission stopped.

*Table - MissionCompletedEventType Definition* {#tbl-missioncompletedeventtype-definition defines=MissionCompletedEventType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:MissionCompletedEventType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:IntentEventType defined in [](#sec-intenteventtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 1:State | 1:ExecutionStateEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:CompletedSteps | 0:UInt32 | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:FailedStepId | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent Events |  |  |  |  |  |

### ExecutionStateEnum {#sec-executionstateenum}

Fine-grained execution state of an intent or a mission. This REFINES the Part 10 program state machine rather than restating it: Queued, Cancelling and the three terminal outcomes cannot be told apart from CurrentState alone. Clause 6.3 fixes which ExecutionState may accompany which Part 10 state, and a Server shall satisfy that table.

*Table - ExecutionStateEnum Definition* {#tbl-executionstateenum-definition defines=ExecutionStateEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ExecutionStateEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[9] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### BufferModeEnum {#sec-buffermodeenum}

How a newly submitted intent relates to the one already executing. The values and their meanings are those of PLCopen Motion Control MC_BufferMode, adopted unchanged because every motion runtime already implements them. In all blending modes the robot does not decelerate to a stop at the boundary, and the predecessor reaches Succeeded when blending begins rather than when its target is exactly attained.

*Table - BufferModeEnum Definition* {#tbl-buffermodeenum-definition defines=BufferModeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:BufferModeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[6] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### BlockingModeEnum {#sec-blockingmodeenum}

Whether an intent tolerates motion and other intents running alongside it. The four values are the two-by-two matrix of VDA 5050 blockingType, adopted because it is the only widely deployed concurrency annotation for robot actions.

*Table - BlockingModeEnum Definition* {#tbl-blockingmodeenum-definition defines=BlockingModeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:BlockingModeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[4] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### TerminationModeEnum {#sec-terminationmodeenum}

Whether a motion ends exactly on its target or is blended into the next one. This is the only distinction every vendor expresses identically; the blend magnitude in BlendDataType.Radius is a request, not a guarantee.

*Table - TerminationModeEnum Definition* {#tbl-terminationmodeenum-definition defines=TerminationModeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:TerminationModeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[2] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### ReleaseModeEnum {#sec-releasemodeenum}

How a held object is given up.

*Table - ReleaseModeEnum Definition* {#tbl-releasemodeenum-definition defines=ReleaseModeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ReleaseModeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[3] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### ApproachModeEnum {#sec-approachmodeenum}

Direction from which an end effector approaches an object or a placement.

*Table - ApproachModeEnum Definition* {#tbl-approachmodeenum-definition defines=ApproachModeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ApproachModeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[4] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### FrameRoleEnum {#sec-frameroleenum}

Role of a coordinate frame, following the coordinate systems ISO 9787 standardises. The roles say WHICH frames exist; no standard says how to calibrate between them, which is why CoordinateFrameType carries the transform explicitly.

*Table - FrameRoleEnum Definition* {#tbl-frameroleenum-definition defines=FrameRoleEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:FrameRoleEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[6] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### OperationalModeEnum {#sec-operationalmodeenum}

Operational mode of the robot system, as defined by ISO 10218-1 and reported identically by OPC 40010-1. It is READ-ONLY here: mode selection is a safety function performed by safety-rated means, and this specification defines no way to command it. Clause 10 restricts intent submission to Automatic and AutomaticExternal.

*Table - OperationalModeEnum Definition* {#tbl-operationalmodeenum-definition defines=OperationalModeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:OperationalModeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[5] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### IntentFailureEnum {#sec-intentfailureenum}

Why an intent did not succeed. The set is deliberately small and diagnosable: a client decides whether to retry, re-plan or escalate from this value alone, and reads Message only to show a human.

*Table - IntentFailureEnum Definition* {#tbl-intentfailureenum-definition defines=IntentFailureEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:IntentFailureEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[21] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### StopModeEnum {#sec-stopmodeenum}

How urgently a cancellation should bring motion to an end. The values are those of PossibleStopModes in OPC 40010-1, so a Server implementing both reports one vocabulary. This is an APPLICATION-LEVEL request: it does not select, imply or guarantee any IEC 60204-1 stop category, which only the robot's safety system determines. See clause 10.

*Table - StopModeEnum Definition* {#tbl-stopmodeenum-definition defines=StopModeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:StopModeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[5] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### AxisKindEnum {#sec-axiskindenum}

Whether an axis rotates or translates. This fixes the unit of the corresponding entry of JointMoveIntentDataType.JointTargets.

*Table - AxisKindEnum Definition* {#tbl-axiskindenum-definition defines=AxisKindEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:AxisKindEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[2] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### MissionUpdateResultEnum {#sec-missionupdateresultenum}

Outcome of a mission update, reported so a client can tell a stale update from a rejected one without parsing a StatusCode.

*Table - MissionUpdateResultEnum Definition* {#tbl-missionupdateresultenum-definition defines=MissionUpdateResultEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:MissionUpdateResultEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[5] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### Pose3DDataType {#sec-pose3ddatatype}

A rigid-body pose. Position is metres; Orientation is a UNIT QUATERNION ordered (x, y, z, w). Quaternions are used because OPC UA defines no quaternion type and the Euler triple in ThreeDOrientation is ambiguous without an external convention; Annex C gives the normative conversion to and from ThreeDFrame. All frames are right-handed. FrameId names the CoordinateFrame the pose is expressed in; an empty FrameId means the Server's default work frame.

*Table - Pose3DDataType Definition* {#tbl-pose3ddatatype-definition defines=Pose3DDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:Pose3DDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### MotionConstraintsDataType {#sec-motionconstraintsdatatype}

Limits a motion is to respect. Every field is a REQUEST bounded by what the robot is configured to permit: a Server clamps rather than refuses, except where clause 10 requires refusal. A value of zero or less means the field is unspecified and the Server chooses.

*Table - MotionConstraintsDataType Definition* {#tbl-motionconstraintsdatatype-definition defines=MotionConstraintsDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:MotionConstraintsDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### BlendDataType {#sec-blenddatatype}

How a motion ends. Radius is interpreted only when Termination is Blend, and is a request: controllers that expose a unitless blend scale rather than a distance map it as best they can, and a Server that cannot honour the exact radius still succeeds.

*Table - BlendDataType Definition* {#tbl-blenddatatype-definition defines=BlendDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:BlendDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### IntentDataType {#sec-intentdatatype}

Abstract base of every intent. An intent is a single task-level request; it is what a client submits and what a mission step holds, so the two are the same shape. Extension is by SUBTYPING this structure, which keeps new intents discoverable through IntentCapabilitiesType rather than by probing for BrowseNames.

*Table - IntentDataType Definition* {#tbl-intentdatatype-definition defines=IntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:IntentDataType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### MotionIntentDataType {#sec-motionintentdatatype}

Abstract base of the intents that move the robot. ToolFrame names the frame whose origin is driven to the target - without it a pose target is meaningless, and OPC 40010-1 defines no tool centre point at all.

*Table - MotionIntentDataType Definition* {#tbl-motionintentdatatype-definition defines=MotionIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:MotionIntentDataType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:IntentDataType defined in [](#sec-intentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### JointMoveIntentDataType {#sec-jointmoveintentdatatype}

Move by interpolating in joint space. This is the fastest way between two configurations and the path the tool centre point takes is not controlled. It is the portable equivalent of PTP, MoveJ, J and MOVJ. Giving a pose rather than joint values asks the Server to solve the kinematics itself, which is the 'move to this pose, you choose how' case.

*Table - JointMoveIntentDataType Definition* {#tbl-jointmoveintentdatatype-definition defines=JointMoveIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:JointMoveIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:MotionIntentDataType defined in [](#sec-motionintentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### LinearMoveIntentDataType {#sec-linearmoveintentdatatype}

Move the tool centre point along a straight line to the target. The portable equivalent of LIN, MoveL, L and MOVL.

*Table - LinearMoveIntentDataType Definition* {#tbl-linearmoveintentdatatype-definition defines=LinearMoveIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:LinearMoveIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:MotionIntentDataType defined in [](#sec-motionintentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### CircularMoveIntentDataType {#sec-circularmoveintentdatatype}

Move the tool centre point along the circular arc that passes through ViaPoint and ends at Target. The portable equivalent of CIRC, MoveC, C and MOVC. Only the position of ViaPoint defines the arc; its orientation is ignored.

*Table - CircularMoveIntentDataType Definition* {#tbl-circularmoveintentdatatype-definition defines=CircularMoveIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:CircularMoveIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:MotionIntentDataType defined in [](#sec-motionintentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### GraspIntentDataType {#sec-graspintentdatatype}

Close the end effector on an object. Force and Width are requests; an end effector that cannot regulate force ignores Force and still succeeds.

*Table - GraspIntentDataType Definition* {#tbl-graspintentdatatype-definition defines=GraspIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:GraspIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:IntentDataType defined in [](#sec-intentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### ReleaseIntentDataType {#sec-releaseintentdatatype}

Give up a held object.

*Table - ReleaseIntentDataType Definition* {#tbl-releaseintentdatatype-definition defines=ReleaseIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ReleaseIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:IntentDataType defined in [](#sec-intentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### PickIntentDataType {#sec-pickintentdatatype}

Take an object from a location. Source is a REFERENCE TO A LOCATION NODE, not a name: the location's pose and its properties are then read from the address space, so the station identity has exactly one definition.

*Table - PickIntentDataType Definition* {#tbl-pickintentdatatype-definition defines=PickIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:PickIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:IntentDataType defined in [](#sec-intentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### PlaceIntentDataType {#sec-placeintentdatatype}

Put a held object at a location. Destination is a reference to a Location node, for the same reason as PickIntentDataType.Source.

*Table - PlaceIntentDataType Definition* {#tbl-placeintentdatatype-definition defines=PlaceIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:PlaceIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:IntentDataType defined in [](#sec-intentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### ToolChangeIntentDataType {#sec-toolchangeintentdatatype}

Exchange the fitted end effector.

*Table - ToolChangeIntentDataType Definition* {#tbl-toolchangeintentdatatype-definition defines=ToolChangeIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ToolChangeIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:IntentDataType defined in [](#sec-intentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### SetOutputIntentDataType {#sec-setoutputintentdatatype}

Set a discrete or analogue output. Output references an OutputSignal node, so the signal's meaning, range and unit are described once in the address space instead of being implied by a string.

*Table - SetOutputIntentDataType Definition* {#tbl-setoutputintentdatatype-definition defines=SetOutputIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:SetOutputIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:IntentDataType defined in [](#sec-intentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### CallProgramIntentDataType {#sec-callprogramintentdatatype}

Run a program that already exists on the controller. This is the escape hatch for capability this specification does not model, and the bridge to the OPC 40010-1 task control surface.

*Table - CallProgramIntentDataType Definition* {#tbl-callprogramintentdatatype-definition defines=CallProgramIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:CallProgramIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:IntentDataType defined in [](#sec-intentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### WaitIntentDataType {#sec-waitintentdatatype}

Do nothing for a while, or until released. A mission needs this to express a rendezvous with something the robot does not control; without it a client has to hold the queue open from outside.

*Table - WaitIntentDataType Definition* {#tbl-waitintentdatatype-definition defines=WaitIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:WaitIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:IntentDataType defined in [](#sec-intentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### IntentResultDataType {#sec-intentresultdatatype}

The outcome of one intent, preserved after it terminates. AchievedPose records where the tool centre point actually ended, which is what lets a client tell a blended corner from an exact stop and audit a placement.

*Table - IntentResultDataType Definition* {#tbl-intentresultdatatype-definition defines=IntentResultDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:IntentResultDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### MissionStepDataType {#sec-missionstepdatatype}

One step of a mission. Released is what splits a mission into its immutable base and its revisable horizon: a released step has been committed and may already be executing, so an update may not touch it. Status is a HINT - where Operation is not null, that IntentOperation's state machine decides.

*Table - MissionStepDataType Definition* {#tbl-missionstepdatatype-definition defines=MissionStepDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:MissionStepDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### MissionDataType {#sec-missiondatatype}

An ordered sequence of intents submitted and tracked as a unit. MissionUpdateId increases with every update, so a Server can reject an update that crossed with another in flight instead of applying it out of order.

*Table - MissionDataType Definition* {#tbl-missiondatatype-definition defines=MissionDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:MissionDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### IntentCapabilityDataType {#sec-intentcapabilitydatatype}

What the Server will accept for one intent type. This is the machine-readable declaration that makes an intent surface discoverable: a client reads it once and knows what it may submit, instead of submitting to find out. It is the analogue of the VDA 5050 factsheet.

*Table - IntentCapabilityDataType Definition* {#tbl-intentcapabilitydatatype-definition defines=IntentCapabilityDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:IntentCapabilityDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### SafeMotionFunctionEnum {#sec-safemotionfunctionenum}

The safe motion function a safety system is enforcing, as defined by IEC 61800-5-2. This is a REPORT. The safety system enforces these independently of this interface, and a client reading them has not thereby obtained any safety function - see clause 10.

*Table - SafeMotionFunctionEnum Definition* {#tbl-safemotionfunctionenum-definition defines=SafeMotionFunctionEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:SafeMotionFunctionEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[9] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### RealTimeTransportEnum {#sec-realtimetransportenum}

The transport of a brokered real-time channel. This specification defines none of these: it describes them so a client can find and open one, and the samples never traverse this interface.

*Table - RealTimeTransportEnum Definition* {#tbl-realtimetransportenum-definition defines=RealTimeTransportEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:RealTimeTransportEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[7] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### ChannelInitiatorEnum {#sec-channelinitiatorenum}

Which end opens the transport connection of a brokered channel. Getting this wrong is the usual reason a first connection attempt fails, so it is stated rather than left to the reader.

*Table - ChannelInitiatorEnum Definition* {#tbl-channelinitiatorenum-definition defines=ChannelInitiatorEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ChannelInitiatorEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[2] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### ErrorPolicyEnum {#sec-errorpolicyenum}

What a mission does when one of its steps does not succeed. Without this a mission can only abort, which forces every recovery out into the client.

*Table - ErrorPolicyEnum Definition* {#tbl-errorpolicyenum-definition defines=ErrorPolicyEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ErrorPolicyEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[5] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### DivergenceKindEnum {#sec-divergencekindenum}

How the transitions leaving one step relate to each other, following the divergence of an IEC 61131-3 sequential function chart.

*Table - DivergenceKindEnum Definition* {#tbl-divergencekindenum-definition defines=DivergenceKindEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:DivergenceKindEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[2] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### WeaveShapeEnum {#sec-weaveshapeenum}

The oscillation applied across an arc weld seam.

*Table - WeaveShapeEnum Definition* {#tbl-weaveshapeenum-definition defines=WeaveShapeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:WeaveShapeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[4] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### TrajectoryPointDataType {#sec-trajectorypointdatatype}

One point of a time-parameterised path. Positions are per axis in the order the axes are declared, in radians or metres by AxisKind. TimeFromStart is measured from the start of the trajectory, which is what makes the path a trajectory rather than a list of waypoints. Velocities and Accelerations are optional and may be empty.

*Table - TrajectoryPointDataType Definition* {#tbl-trajectorypointdatatype-definition defines=TrajectoryPointDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:TrajectoryPointDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### MotionToleranceDataType {#sec-motiontolerancedatatype}

How far execution may deviate before it is a failure. A tolerance of zero or less means the Server applies its own.

*Table - MotionToleranceDataType Definition* {#tbl-motiontolerancedatatype-definition defines=MotionToleranceDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:MotionToleranceDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### TrajectoryIntentDataType {#sec-trajectoryintentdatatype}

Execute a time-parameterised path. The Server's own motion kernel runs it; this interface hands the whole trajectory over in one submission and does not stream it. That is what makes trajectory execution expressible here when real-time control is not - see clause 4.3.

*Table - TrajectoryIntentDataType Definition* {#tbl-trajectoryintentdatatype-definition defines=TrajectoryIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:TrajectoryIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:MotionIntentDataType defined in [](#sec-motionintentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### PathWaypointDataType {#sec-pathwaypointdatatype}

One waypoint of a Cartesian path, with the blend that applies at it. Per-waypoint blending is what distinguishes a path from a sequence of separate linear moves: the robot need not stop between them.

*Table - PathWaypointDataType Definition* {#tbl-pathwaypointdatatype-definition defines=PathWaypointDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:PathWaypointDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### CartesianPathIntentDataType {#sec-cartesianpathintentdatatype}

Follow a list of Cartesian waypoints. This is the portable form of a taught path, and unlike a trajectory it carries no timing: the Server paces it from the motion constraints.

*Table - CartesianPathIntentDataType Definition* {#tbl-cartesianpathintentdatatype-definition defines=CartesianPathIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:CartesianPathIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:MotionIntentDataType defined in [](#sec-motionintentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### ForceIntentDataType {#sec-forceintentdatatype}

Move until contact. The portable subset of the force-controlled moves every vendor offers: travel along a direction until a contact force is reached or a distance is exhausted, whichever comes first. Reaching the distance without contact is a failure, because the intent was to touch something.

*Table - ForceIntentDataType Definition* {#tbl-forceintentdatatype-definition defines=ForceIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ForceIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:MotionIntentDataType defined in [](#sec-motionintentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### ProcessIntentDataType {#sec-processintentdatatype}

Abstract base of the intents that run an application process along a path. Every process needs the same two things beyond its own parameters: a reference to the process program or procedure the equipment holds, and room for the parameters this specification has not standardised.

*Table - ProcessIntentDataType Definition* {#tbl-processintentdatatype-definition defines=ProcessIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ProcessIntentDataType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:MotionIntentDataType defined in [](#sec-motionintentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### ArcWeldIntentDataType {#sec-arcweldintentdatatype}

Lay an arc weld along the path. The parameters are the subset ABB seamdata/welddata/weavedata, FANUC weld schedules and KUKA ArcTech all carry. WeldProcedureRef points at a welding procedure specification (ISO 15609) where the installation works to one; this specification does not restate its content.

*Table - ArcWeldIntentDataType Definition* {#tbl-arcweldintentdatatype-definition defines=ArcWeldIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ArcWeldIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:ProcessIntentDataType defined in [](#sec-processintentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### SpotWeldIntentDataType {#sec-spotweldintentdatatype}

Make a resistance spot weld at the target. WeldSchedule selects the weld controller's own program: current and time are the weld controller's business, and are carried here only where the installation drives them from the robot.

*Table - SpotWeldIntentDataType Definition* {#tbl-spotweldintentdatatype-definition defines=SpotWeldIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:SpotWeldIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:ProcessIntentDataType defined in [](#sec-processintentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### DispenseIntentDataType {#sec-dispenseintentdatatype}

Lay a bead of adhesive, sealant or paint along the path. The trigger distances exist because material does not start and stop instantly: a Server begins dispensing before the path and stops before its end.

*Table - DispenseIntentDataType Definition* {#tbl-dispenseintentdatatype-definition defines=DispenseIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:DispenseIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:ProcessIntentDataType defined in [](#sec-processintentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### FastenIntentDataType {#sec-fastenintentdatatype}

Drive a fastener at the target. This intent is deliberately THIN: OPC 40450 and OPC 40451 already define joining and tightening in full, so where such a model is exposed, Joint references the joint in that model and the result belongs there; otherwise Joint is null and the remaining fastening parameters stand alone. Restating those parameters here would create a second definition of the same fact.

*Table - FastenIntentDataType Definition* {#tbl-fastenintentdatatype-definition defines=FastenIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:FastenIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:ProcessIntentDataType defined in [](#sec-processintentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### PalletiseIntentDataType {#sec-palletiseintentdatatype}

Place an item into a pattern. The pattern itself is a Location, so its geometry has one definition that a client can read rather than being recomputed from indices on both sides.

*Table - PalletiseIntentDataType Definition* {#tbl-palletiseintentdatatype-definition defines=PalletiseIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:PalletiseIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:ProcessIntentDataType defined in [](#sec-processintentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### SurfaceFinishIntentDataType {#sec-surfacefinishintentdatatype}

Follow the path pressing into the surface - grinding, polishing, deburring or sanding. ContactForce is what distinguishes it from a plain path: the robot yields normal to the surface to hold that force.

*Table - SurfaceFinishIntentDataType Definition* {#tbl-surfacefinishintentdatatype-definition defines=SurfaceFinishIntentDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:SurfaceFinishIntentDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:ProcessIntentDataType defined in [](#sec-processintentdatatype) |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### MissionTransitionDataType {#sec-missiontransitiondatatype}

One edge of a mission's step graph, following the step-and-transition form of an IEC 61131-3 sequential function chart. Condition is an OPC UA ContentFilter - the base specification's own filter grammar, reused so that this specification does not invent an expression language for implementers to write a parser for.

*Table - MissionTransitionDataType Definition* {#tbl-missiontransitiondatatype-definition defines=MissionTransitionDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:MissionTransitionDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### KinematicJointDataType {#sec-kinematicjointdatatype}

One joint of the kinematic chain: where it sits relative to its predecessor and which way it acts. OPC 40010-1 describes a robot's topology and its axes but defines no kinematic chain, so this is additive rather than a second account of the same thing.

*Table - KinematicJointDataType Definition* {#tbl-kinematicjointdatatype-definition defines=KinematicJointDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:KinematicJointDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent DataTypes |  |  |  |  |  |

### HasIntentController {#sec-hasintentcontroller}

Binds an intent surface to the thing it commands. This is how the model attaches to a robot described by another specification - an OPC 40010-1 MotionDeviceSystem, say - without depending on it. Annex B defines that binding.

*Table - HasIntentController Definition* {#tbl-hasintentcontroller-definition defines=HasIntentController}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:HasIntentController |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:NonHierarchicalReferences defined in OPC 10000-5 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent ReferenceTypes |  |  |  |  |  |

### HasFrameParent {#sec-hasframeparent}

From a CoordinateFrame to the frame its Transform is expressed in. Frames form a tree, so a pose given in one frame can be re-expressed in another by composing the transforms along the path between them.

*Table - HasFrameParent Definition* {#tbl-hasframeparent-definition defines=HasFrameParent}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:HasFrameParent |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:NonHierarchicalReferences defined in OPC 10000-5 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| RobotIntent ReferenceTypes |  |  |  |  |  |
