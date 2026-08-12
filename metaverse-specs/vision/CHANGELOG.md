# Changelog — OPC UA — Vision

All notable changes to this specification and its information model.

NodeId assignment is **append-only**: a new member takes the next free id, so every previously published NodeId is stable across the releases below.

## 0.3.0 — 2026-08-12

### Results say what is; events say what happened

A result is a record and an event is an occurrence, and until now this model had only the first. Every consumer had to poll a `Results` folder and re-derive, from a changed array, what had actually taken place — and two consumers polling the same Server could disagree about when. §7.5 adds `VisionEventType` (abstract), `ObjectDetectedEventType` and `InspectionCompletedEventType`, appended at `i=1031`–`i=1033` with members from `i=6201`; no existing NodeId moves.

An event names the result that substantiates it and does not copy it, so there is no second copy of a fact to disagree with the first. Two fields are deliberate exceptions, because they are what a consumer filters on and requiring a read to obtain them would defeat the purpose: the detection itself, and the inspection verdict.

`Time` is the acquisition timestamp of the frame, not the moment inference finished — a distinction the model previously had no way to express at all. `InferenceEndTime` carries the latter, so the difference is the inference latency of that one observation, which is the first per-result latency this model exposes.

One event is raised per detection rather than per result. That is what makes `ClassLabel` and `Confidence` reachable by an `EventFilter`, so a client asks for the classes it cares about above a confidence it chooses and the Server sends nothing else; a per-result event would move that filtering to the client and give up most of the reason to raise events.

The well-known `Vision` object now declares `EventNotifier` and is the target of a `HasNotifier` reference from the Server object, so events raised anywhere in the model reach a client that subscribes at either. Nothing in this repository set `EventNotifier` before, which meant an EventType could have been declared and still been unreachable.

`GroundTruth` is Mandatory on every event: a consumer never has to infer from a confidence value whether it was told a measurement or a prediction. `Vision Events` joins the conformance units, and **VIS-Events** the facets.

### A manufacturing event is composed, not invented

Annex I.7 states how a cell learns that a part was picked: from the commanding model's completion event, corroborated by this model's detection event. This specification deliberately defines no `PickEventType`, because a camera cannot know that a pick happened — it can only report what it saw. The intent vocabulary is therefore already the manufacturing-event vocabulary, and a second one naming the same acts could only disagree with it.

## 0.2.0 — 2026-08-11

Every change in this release comes from an in-progress implementation of Release 0.1.0 against the OPC UA .NET Standard stack, working through the bin-picking scenario of the Robotics-Vision Addendum. They are reported in issues #66 to #71.

One NodeId changed name and none moved: `MediaEndpointType.ProfileName` became `DefaultProfileName` and kept `i=6019`. Two members were appended at `i=6199` and `i=6200`, and two enumeration DataTypes at `i=3016` and `i=3017`.

### Every Method with arguments was uncallable

`InputArguments` and `OutputArguments` are standard Properties of namespace 0, and this model qualified all 13 of them into its own namespace. A stack resolves a Method's signature by looking for the child Property named `InputArguments` **in namespace 0**; not finding it, it treats the Method as taking no arguments and rejects every call with `Bad_TooManyArguments`. The same defect qualified the `EnumStrings` Property of every enumeration DataType, so a client reading an enumeration's permitted values generically saw an enumeration with no names.

Both are fixed at the generator, which now declares a standard BrowseName as standard rather than inheriting the model namespace by default — so a Method added later cannot reintroduce it. `.github/scripts/check_browsename_namespace.py` checks every NodeSet in the repository for the whole class of defect, not only the names that broke here.

The reporting implementation's unit tests passed throughout, because they call the handler delegates directly. Only an end-to-end session surfaced it.

### A depth sensor can state its depth image shape

`Depth3DSensorType` gained Optional `DepthWidth` and `DepthHeight` (`UInt32`), present or absent together. `PointsPerFrame` is a nominal count and cannot be used to reproject a depth pixel or size a decoder, and §5.6 models a device producing both depth and a registered 2-D image as two sensors — so a structured-light sensor with no paired `ImageSensorType`, which is the common case for the Zivid, Ensenso and Photoneo class of device, had nowhere to publish the shape of its native depth image. Implementations were carrying it in vendor-private Properties, which is the failure §5.5 says this model exists to prevent.

### An empty observation is expressible

§9.5 rejected an empty `Detections` array and required exactly one non-empty corrected array, which made two true statements impossible to send: *"I examined this frame and there is nothing in it"* and *"the detection you published was a false positive and nothing replaces it"*.

The first is the terminating condition of a bin-picking task — the agent picks the last part, looks again, and could not report the bin was empty. The second is the correction shape a supervised loop most needs, because a false positive is the error an operator is most able to label with confidence. Correcting three detections to one was always expressible; correcting one to zero was not, which is the sign the rule was guarding against an accidentally empty call rather than expressing a domain constraint.

`SubmitDetections` gained `SceneIsEmpty` and `SubmitCorrection` gained `RetractAll`, both `Boolean` and both last in their argument lists because argument order is part of the wire contract. An empty array is accepted only with the corresponding flag set, so an accidentally empty call is still refused. §9.4 states that a negative example **is** a valid dataset sample and is counted in `SamplesCollected`, and §12.7 states the poisoning surface this opens: a stream of well-formed "nothing here" labels degrades recall while every individual call looks legitimate.

### Members that existed only in the CSV are specified

Six members were declared in the model and absent from the prose, so an implementer had to guess the semantics or read the NodeSet.

- `CoordinateFrameType.Transform` is the pose of this frame in its `ParentFrame` — the same direction as `ExtrinsicCalibrationType.Transform`, so a client composing a chain never has to invert one — with `Transform.FrameId` required to equal the parent's `FrameId`, and stated to be a snapshot rather than a guarantee of constancy (§5.8, §5.12).
- `SegmentationResultType.LabelClasses` is a `String[]` whose array position **is** the pixel value it names, with index `0` reserved for background. §7.4 also states what follows: a mask is single-label, and instance segmentation is expressed by giving each instance its own value (§7.4).
- `IlluminationType.LampType` and `LightingMode` became enumerations. OPC 40100-2 types them as an open `String` and an unconstrained `UInt32` and gives its values only as prose examples, which is the hard-coded-vocabulary failure §5.7 exists to prevent. The enumerations carry exactly the values 40100-2 names, plus `Other`; Annex D requirement 4 gives the conversion in both directions.
- `InferencePipelineType.LearningJob` is listed in §8.3 with its optionality and a forward reference to §9.5.1, which required it without §8.3 mentioning it existed.
- §5.1 and §9.1 state that `VisionFeedbackType` is concrete and directly instantiated, along with every other non-abstract ObjectType absent from the subtype figure.

### The media plane says which resolution its intrinsics belong to

§6.3 states that `ImageSensorType.Intrinsics` are authoritative at the sensor's native resolution, and that a client consuming a stream served at a different one **shall** rescale `Fx`, `Fy`, `Cx` and `Cy` — subtracting `OffsetX`/`OffsetY` first where the sensor delivers a crop, because the offset is in native pixels. A 4K sensor commonly streams 1080p, so the two disagree routinely; a client that skips the rescale computes rays wrong by the resolution ratio, and the error is proportional, so it survives every check that looks at units or magnitude.

`ProfileName` became `DefaultProfileName` and is defined: a profile is a Server-local named configuration with no node of its own, and this is the one profile name a client can rely on without prior knowledge. §6.3 states that a client without such knowledge passes an empty `ProfileName`, and that guess-and-retry against `Bad_InvalidArgument` is not a discovery mechanism — which was the only strategy the previous text left available.

### Two facet claims now mean something

*VIS-Calibration* requires `Vision/Frames` and requires it to hold every frame reachable through `MountedOn`, `SourceFrame` or `TargetFrame`. `Frames` is Optional on `VisionRootType`, so a Server could satisfy the facet with frames reachable only by walking the sensors, and a client browsing the well-known folder would conclude the Server had none while every result named a frame it never found.

*VIS-Feedback* names a minimum accepted `Purpose` set — at least `Trigger` and `Overlay` — and places `GroundTruthLabel` behind *VIS-Learning*, matching the chain §9.4 already described. Without a minimum, a Server accepting only `Trigger` conformed, and the claim said almost nothing about what a client could send.

## 0.1.0 — 2026-08-02

Initial working-group draft: sensors, the media they emit, coordinate frames and calibration, inference pipelines, results, the feedback and learning loop, simulation parity, and the interop profiles for OpenUSD Scene, OPC 40100 and Robot Intent.
