# Changelog — OPC UA — Robot Intent

All notable changes to this specification and its information model.

## 0.1.0 — 2026-08-02

Initial working-group draft.

### Why this specification exists

OPC 40010-1 defines robot topology and no motion verbs. The gap was filled unilaterally in the .NET OPC UA stack by ten verbs in an application-owned namespace, resolved by BrowseName and explicitly self-described as a non-normative convention. That contribution established a vocabulary; it established no lifecycle. This release standardises the layer and supplies the lifecycle.

### Decisions, and what forced them

- **The lifecycle is Part 10, not a bespoke state machine.** OPC 10000-4 §5.12.2 discards a method result when the Session ends *"independent of the task actually performed at the Server"* — a synchronous motion method therefore loses the outcome of work that has already physically happened. OPC 10000-10 §4.1 gives the OPC Foundation's own resolution, and building on `ProgramStateMachineType` supplies transition events, a surviving result object and invocation diagnostics that would otherwise have to be invented.

- **`ExecutionState` refines the Part 10 state rather than restating it.** `Queued`, `Cancelling` and the three terminal outcomes cannot be distinguished from `CurrentState` alone. The state machine remains authoritative and §6.3 tabulates every legal pairing, so the refinement is checkable rather than merely asserted.

- **Verbs are a DataType hierarchy, not one Method each.** This makes a single submission and a mission step the same shape, makes extension a subtyping act, and makes discovery a read of `SupportedIntents` rather than a probe for BrowseNames.

- **Orientation is a unit quaternion, not the core `ThreeDOrientation`.** OPC UA defines no quaternion type, and the `A`, `B`, `C` fields carry no convention of their own — the only normative assignment of meaning to them is external to the base specification. Annex C carries the bidirectional conversion, including the clamp that keeps a pole orientation from becoming a domain error, so the divergence costs no interoperability.

- **`Pick` and `Place` reference Location nodes, not station strings.** A free-text station identifier would be a second definition of a fact the address space already holds, able to disagree with the first.

- **Queueing is PLCopen `MC_BufferMode` and concurrency is VDA 5050 `blockingType`, both adopted unchanged.** No OPC UA specification defines motion-level queueing or blending; both of these are already implemented across the industry, and re-designing either would have produced something less implementable and no more correct.

- **The specification declares itself non-safety-rated.** OPC 40010-1 §7.7.1 disclaims functional safety for its own safety states, and an OPC UA method call carries no safety rating. Clause 10 states the boundary, restricts submission to Automatic and Automatic External modes, and records that a stop request selects no IEC 60204-1 stop category.

- **Command authority is arbitration, not the single point of control.** ISO 10218-2 requires mutual exclusion between remote command and local manual control by safety-rated means. Clause 8 says plainly that this model does not provide it, because a specification that implied otherwise would be dangerous.

- **The NodeSet is standalone.** The only `RequiredModel` is the base UA namespace; OPC 40010-1 interop is an optional profile carried by `HasIntentController`. This follows the precedent set by *OPC UA — Vision* in this repository.

- **Real-time is a division of labour, not an exclusion.** Trajectory *execution* is expressible over request/response — the whole path is handed over once and the robot's own motion kernel runs it, which is what `FollowJointTrajectory` and the PLCopen buffered path blocks do. Streaming *control* is not, so the model **brokers** a channel instead: it describes and leases RTDE, EGM, FRI, RSI, MotoROS2 or OPC UA FX, and the samples never traverse OPC UA. This is the same shape as the Vision model brokering a media endpoint rather than carrying pixels.

- **Safety is awareness plus a refusal duty, and explicitly not a rating.** OPC 10000-15 carries cyclic safety data from a provider to a consumer, and the consumer's request holds an identifier, a monitoring number and one octet of explicitly non-safety flags — so a caller cannot supply safety-rated arguments, and no Method in any companion specification can be a safety function. Every safety fieldbus expresses a safety command as a continuously asserted cyclic signal, because the integrity argument rests on the fail-safe state that follows when assertion stops; a Method call has no behaviour when it stops being called. The model therefore *reports* what the safety system enforces and *refuses* work that would exceed it, and says plainly that neither makes anything safe.

- **The kinematic chain is additive, not a second account.** OPC 40010-1 describes a robot's topology and axes in detail and defines no kinematic chain an IK solver could use, and no tool centre point. Annex B fixes which side decides where both are present.

- **Fastening is thin on purpose.** OPC 40450 and OPC 40451 already define joining and tightening in full, so `FastenIntentDataType.Joint` references a joint there rather than restating torque strategies — the same rule that made `Pick` take a `Location` node instead of a station string.

- **Mission branching follows IEC 61131-3, not a behaviour tree.** Steps and transitions with alternative and parallel divergence are the notation the controller audience already knows and has an IEC serialization; a behaviour tree needs a tick runtime controller vendors do not provide, and its serialization belongs to a library rather than a standard. Transition conditions reuse the base UA `ContentFilter` so that no implementer has to write a parser for an invented expression language. An empty transition array leaves the mission the flat sequence it was.

### Not in this release

Any real-time or servo-level facility carried *through* this interface, which §4.3 excludes as a normative limit; and any claim of functional safety, which clause 10.1 explains cannot be made.
