# Changelog — OPC UA — Robot Intent

All notable changes to this specification and its information model.

## 0.2.0 — 2026-08-12

### Standard BrowseNames are written in namespace 0

`InputArguments` and `OutputArguments` are standard Properties of OPC 10000-3 and OPC 10000-5 and live in namespace 0. All 21 of this model's argument Properties were qualified into the model's own namespace, and a stack resolves a Method's signature by looking for the child Property named `InputArguments` **in namespace 0** — not finding it, it treats the Method as taking no arguments and rejects every call with `Bad_TooManyArguments`. **Every Method in this model was uncallable.** The same defect qualified the `EnumStrings` Property of every enumeration DataType, so a client reading an enumeration's permitted values generically saw an enumeration with no names.

Both are fixed at the generator, which now declares a standard BrowseName as standard rather than inheriting the model namespace by default, so a Method added later cannot reintroduce it. `.github/scripts/check_browsename_namespace.py` guards the whole class across every NodeSet in the repository.

No NodeId moved: the change is the BrowseName attribute alone. The model identity moves with it because a client that cached this model under the previous `(Version, PublicationDate)` holds BrowseNames that no longer describe it, and two models published under one identity are indistinguishable to such a client.

### Seam tracking is a switch, not a channel

§5.4.2 now states what `ArcWeldIntentDataType.SeamTrackingEnabled` asks for: the equipment's own seam-tracking facility, which is the second branch §4.3 already permits. Nothing is sampled or carried over OPC UA. The two clauses were consistent and separated far enough that they read as contradicting.

### Conformance is machine-readable

`IntentCapabilitiesType.SupportedFacets` (`String[]`, Mandatory, appended at `i=6139`; no existing NodeId moves) carries the facet names of Table 12.2 that a controller claims. Clause 12 defined conformance in terms of facets and gave a Server nowhere to state which it had, so a client had to re-derive the whole table from the address space — which is what the reference implementation did. Several rows are behavioural and cannot be settled by browsing at all, so two clients deriving independently could reach opposite conclusions about one Server and both be reading the specification correctly. §12.2 now separates structural requirements, which a client checks by reading, from behavioural ones, which are the Server's attestation under clause 9. **RI-Base** requires the member.

### Implementation defects

Defects found by implementing the specification in the OPC UA .NET Standard stack. Every change here
makes an existing claim true; none adds capability, and no previously assigned NodeId moves.

- **A refusal is now observable.** `SubmitIntent`, `SubmitMission` and `Retry` gained `Accepted`,
  `Failure` (`IntentFailureEnum`) and `Message` output arguments, and §6.2 now states that a Server
  returns `Good` and reports the refusal in those outputs rather than substituting a Bad `StatusCode`.
  Before this, §6.2 ordered six distinct refusals and §5.8 called the failure set "small and
  diagnosable on purpose" — and a client could observe neither, because the only outputs were
  `IntentId` and `Operation`. A specification cannot require an ordering of refusals a conformant
  client has no way to see. `OpenRealTimeChannel` gained a `Message` for the same reason: §6.9 lists
  four grounds for refusal behind a single `Granted` boolean.

- **The Part 10 promotions are now legal promotions.** `IntentOperationType.ProgramDiagnostic` was
  declared as a Property of `PropertyType` reached by `HasProperty`. OPC 10000-10 declares that member
  as a Variable of `ProgramDiagnostic2Type` reached by `HasComponent`, so the declaration added a
  second member beside the inherited one instead of promoting it — which is what stopped a Part 10
  client, and the first stack that tried to generate the model, from finding it. A promotion changes
  the ModellingRule and nothing else, and §6.1 now says so.

- **`WaitIntentDataType.Signal` is bounded.** It read "an OutputSignal **or other node**", which §11.3
  cannot check: an unvalidated NodeId is precisely the surface §11.3 exists to close. It now resolves
  to an `OutputSignalType` under the controller or to a Variable of DataType `Boolean` under it.

- **§11.3 names the expected type of every NodeId-valued member.** "A node of the expected type" was
  an instruction to guess. A table now fixes it for `Source`, `Destination`, `Pattern`, `ToolFrame`,
  `FrameId`, `Tool`, `Output`, `Program`, `ProcessProgram`, `Signal` and `Joint`.

- **§5.7.0 gives `Ready`, `ActiveIntent`, `ActiveMission` and `ControlOwner` normative meaning.** They
  were in the model and in no clause, so what a Server had to publish in them was unstated.

- **§6.9 bounds `RequestedLease`.** The lease rules never said what limits a request, so a client could
  ask for a lease of any length and the Server's answer was unspecified.

- **§9 applies its honesty rule to the Method surface.** Three rules already kept the capability
  declaration honest, but nothing said that a declared capability must come with the Methods that make it
  usable — and `SubmitMission`, `UpdateMission`, `CancelMission` and the two channel Methods are all
  *Optional* on `IntentControllerType`. A Server could therefore advertise `MissionsSupported` true and
  omit `SubmitMission` entirely, which is precisely what the first implementation did, and a client
  discovered the contradiction only by calling something that was not there. A fourth rule and a table now
  fix which Methods each declaration implies.

- **§6.5 says what a Server that cannot differentiate `StopMode` must do.** The text gave `StopMode` the
  `PossibleStopModes` vocabulary of OPC 40010-1 and then said nothing about a Server that treats every
  value alike — so accepting the argument and discarding it looked conformant. A Server must now either
  honour it or treat every value as its single stop behaviour, and should say which; a client that asks for
  `OnPath` and silently gets a `QuickStop` has been told something untrue about how the cell stopped.

- **§6.4 says which stop a superseded intent gets.** An `Aborting` submission carries no `StopMode`, so the
  mode a superseded intent is stopped with was undefined. The Server chooses, should choose the most urgent
  stop the cell tolerates since the successor is about to command motion, and should document it.

### Profiles

Clause 12 has been titled *Profiles and conformance units* since 0.1.0 and defined only facets. §12.3 defines four profiles and §12.4 gives their URIs. The information model does not change for this, so the release version does not move on its account: profiles are published through the base-UA `Server/ServerCapabilities/ServerProfileArray` and need no member.

| Profile | Facets |
|---|---|
| Robot Motion Server | RI-Base, RI-Motion-Joint, RI-Motion-Linear, RI-Description, RI-Safety |
| Robot Handling Server | Motion, plus RI-Motion-Circular, RI-Grasp, RI-PickPlace, RI-ToolChange, RI-Output, RI-Queue |
| Robot Path Server | Motion, plus RI-Trajectory, RI-Path, RI-Blending |
| Robot Mission Server | Motion, plus RI-Mission, RI-Program, RI-Wait, RI-Pause, RI-Retry |

§1.2's use cases were already written about profiles without using the word. A mixed-fleet work cell — two robots from different manufacturers executing one mission definition — works only if both claim the same shape, and there was no name for the shape to claim.

`RI-Safety` is in the baseline rather than optional to it, and that is the decision in this change most worth arguing about. Clause 10 is explicit that this specification is not safety-rated and that no Method here is a safety function. What it does impose is a duty: report what the safety system enforces, and refuse work that would exceed it. An integrator specifying a profile is entitled to assume a robot declines an intent its safety configuration forbids rather than attempting it, and a robot that cannot read its safety system claims facets individually instead.

The process facets are deliberately in **no** profile. A welding robot is a **Robot Path Server** that additionally claims `RI-Process-ArcWeld`; bundling the process in would have produced one profile per process and no way to say the underlying motion is the same. `RI-Force`, `RI-RealTimeChannel` and the two interop facets stay outside all four for the same reason.

§3 gains definitions for *conformance unit*, *facet* and *profile*, none of which the document defined while using the first two throughout.

Facets and profiles are declared at different levels and §12.2 says how they relate: `SupportedFacets` is on `IntentCapabilitiesType` and is therefore per controller, `ServerProfileArray` is on the Server object and is therefore per Server. Where a Server publishes facet URIs as well as profile URIs, the two must agree.

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
