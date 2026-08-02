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

### Not in this release

Conditional and branching missions; a portable process model for inspection, welding or dispensing; any real-time or servo-level facility, which §4.3 excludes as a normative limit rather than a deferral.
