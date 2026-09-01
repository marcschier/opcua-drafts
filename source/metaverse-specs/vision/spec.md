## Scope {#sec-scope}

This specification defines an OPC UA information model that lets a Server describe:

- **what sensors it has** — physical or simulated — and their imaging parameters;
- **where their media can be obtained** — a live stream, a still clip — without carrying pixels over OPC UA;
- **how they are calibrated** and in which coordinate frames their output is expressed;
- **what AI runs on them**, whether that inference happens on the Server or somewhere else entirely;
- **what results they produce**, with content that is actually defined rather than left to the application;
- **how a consumer feeds information back**, including corrections that become training data.

This specification complements OPC 40100-1 and OPC 40100-2. It does not define machine-vision job orchestration, recipe or configuration management, or asset lifecycle management. OPC 40100-1 remains authoritative for jobs, system state, recipes, configurations and result transfer, and OPC 40100-2 remains authoritative for asset identity, component inventory, condition monitoring and maintenance. This specification extends those models with sensor acquisition semantics, media endpoints, calibration and coordinate frames, AI inference and provenance, defined result content, and feedback. Annex D defines the integration contract for a Server that exposes the same equipment through this specification and OPC 40100.

### Motivation {#sec-motivation}

Two OPC UA machine vision companion specifications already exist, as well as a robotics one (OPC 40010-1). None of them describes the four things above. OPC 40100-1 orchestrates jobs but states that result content is *"application-specific and not defined at this time"*. OPC 40100-2 models lenses and lamps in detail but adds no members to its image sensor type. OPC 40010-1 contains no vision, camera, perception or calibration types whatsoever. And no OPC UA specification describes an AI model. The evidence for each of these statements, with quotations and section numbers, is in the companion [research report](research.md).

The consequence is that every vision integration is bespoke: two Servers can be fully conformant to the existing specifications and still be mutually unintelligible.

### Motivating use cases {#sec-motivating-use-cases}

- **Inspection.** A fixed camera measures a part. The verdict, the characteristics behind it, and the frame it was computed from are all published, so a downstream system can act on the verdict *and* audit it.
- **Vision-guided robotics.** A camera on a robot flange detects parts in a bin and publishes 6-DoF pick poses in a named frame, with the hand-eye calibration that makes those poses meaningful.
- **Off-server AI.** Inference runs on an edge GPU or in a cloud service. The Server publishes results it did not compute, and clients consume them through exactly the same contract. The model being executed is **not** firmware baked into the camera: it is an artefact the operator or system integrator supplies, versions and approves, and the Server describes which one is currently deployed (§8.1).
- **Synthetic data and learning.** A simulated sensor renders a scene, ground truth is captured as a dataset, a model is trained and promoted, and operator corrections from the production line flow back into the next dataset.
- **Live viewing.** An operator opens the camera's RTSP stream, optionally with detections drawn on it.

### What this specification does not (yet) do {#sec-what-this-specification-does-not-yet-do}

Two of these are permanent boundaries, and two are deferrals this working group may revisit.

**Out of scope by design:**

- It does **not** carry pixels on its default path. Media is brokered by reference (§6). Two optional facets exist beside that default — a size-gated inline `ByteString` for single stills (§6.4), and, where a Server implements the *OPC UA — Data Channels* draft, a data channel multiplexed onto the SecureChannel (§6.7). Neither changes the default, and a Server is conformant with neither.
- It does **not** replace GenICam, GigE Vision, USB3 Vision or CoaXPress. Those move and configure image data at the device layer; this model sits above them and borrows their vocabulary without depending on them (Annex E).

**Not addressed yet:**

- It does **not yet** define an inspection *program* or *recipe* format. A `RecipeId` identifies one; its content is out of scope here, as it is in OPC 40100-1. Should a portable recipe format emerge, binding to it is additive.
- It does **not yet** take a dependency on OPC 40100, OPC 40010, DI, Machinery or the OpenUSD models. Interop with each is an optional profile (Annexes C and D). These are candidates for normative dependencies once the interop profiles have been exercised against real implementations.

Neither list is a statement that the omitted capability is unimportant — only that this specification does not define it, and that a Server is conformant without it.

### Capabilities and versioning {#sec-capabilities-and-versioning}

This specification covers sensors, the media they emit, coordinate frames and calibration, inference pipelines, results, and the feedback path back in. The AI models those pipelines run are described by *OPC UA — AI Model Management and Inference* (§8.1). The NodeSet declares exactly one `RequiredModel` — the base OPC UA namespace — so a Server can adopt it without pulling in any companion model.

---

## Overview and concepts {#sec-overview-and-concepts}

### The layered contract {#sec-the-layered-contract}

This model occupies one layer of a stack it does not attempt to own:

```text
   Enterprise / lifecycle        Asset Administration Shell, MES, MLOps
        ^
   THIS SPECIFICATION            sensors - media endpoints - AI - results - feedback
        ^                        (semantics and control plane)
   Device control API            GenICam: GenApi, SFNC, PFNC, GenTL, GenDC
        ^
   Pixel transport               GigE Vision, USB3 Vision, CoaXPress, MIPI CSI-2
```

A Server implementing this model almost always uses GenICam internally to talk to its cameras. That is invisible here by design, and is why `VisionSensorType.DeviceUri` exists: it lets a client correlate the semantic sensor with the transport-level device without this model reaching down into it. Annex H gives the member-by-member binding for a Server that does.

### Discovery (normative) {#sec-discovery-normative}

A conforming Server **shall** expose exactly one well-known Object `Vision` of type `VisionRootType` as a component of the Server Object (`i=2253`), with BrowseName `Vision` qualified by the namespace `http://opcfoundation.org/UA/Vision/`. A client **shall** resolve that namespace's index from `Server.NamespaceArray` rather than assuming a fixed index. It contains:

- `Sensors` (Mandatory) — every `VisionSensorType` instance;
- `Pipelines` and `Frames` (Optional).

Models, deployments and learning jobs are **not** here. They are reached through `AiRootType` in *OPC UA — AI Model Management and Inference*, whose own well-known object sits beside this one under the Server object. A client looking for what AI a Server runs browses there, not here.

A client therefore starts at `Server/Vision/Sensors` and follows references outward. This mirrors the discovery pattern of *OPC UA — OpenUSD Bindings*.

### Sim/real symmetry (normative) {#sec-sim-real-symmetry-normative}

**Sim/real symmetry** is the property that a physical sensor and a simulated one are described by the *same* members, carrying the *same* units and the *same* meaning, so that a client cannot tell them apart except by reading `RealityKind` — and does not need to. "Sim" is a simulated or rendered sensor, typically one that exists only inside a scene simulator such as NVIDIA Isaac Sim; "real" is a physical device on the plant floor. The symmetry is what lets one client, one recipe and one trained model move between a simulation used to generate training data and the production cell it was built to represent.

Every `VisionSensorType` instance **shall** declare `RealityKind`. A Server **shall not** vary the meaning, units or semantics of any other member based on its value. A sensor whose `RealityKind` is `Simulated` or `Hybrid` **shall** additionally implement `IVisionSimulatedType`, which names the simulator and the scene prim being rendered; clause 11 accordingly makes *VIS-Simulation* required of any Server that reports either value, rather than optional.

The intent is that a client written against `VisionSensorType` works unchanged against a physical camera, against its digital twin, and against a purely synthetic sensor used to generate training data.

### Architecture {#sec-architecture}

```{figure}
id: fig-vis-architecture
caption: Architecture of a vision system
source: figures/Vision-Fig1-Architecture.png
```

---

## Information model {#sec-information-model}

The model has **21 ObjectTypes**, and they exist in five groups, each answering one question a vision integration has to answer:

| Group | Question it answers | Types | Clause |
|---|---|---|---|
| **Sensing** | What is the device, and what did it see it with? | `VisionSensorType`, `ImageSensorType`, `Depth3DSensorType`, `OpticsType`, `IlluminationType` | §5.4–5.5 |
| **Media** | How do I get the imagery, without putting it in OPC UA? | `VisionMediaManagementType`, `MediaEndpointType`, `StreamEndpointType`, `ClipEndpointType` | §6 |
| **Spatial** | Where is the sensor, and what is a pose *relative to*? | `CoordinateFrameType`, `VisionCalibrationType`, `IntrinsicCalibrationType`, `ExtrinsicCalibrationType` | §5.8 |
| **AI** | What computed the answer, and can I audit it? | `InferencePipelineType` here; `ModelType`, `DatasetType`, `DeploymentType` and `LearningJobType` in *OPC UA — AI Model Management and Inference* | §8, §9 |
| **Outcome** | What is the answer, and how do I correct it? | `VisionResultType`, `InspectionResultType`, `DetectionResultType`, `SegmentationResultType`, `VisionFeedbackType` | §7, §9 |

Plus two structural types: `VisionRootType`, the entry point (§4.2), and `IVisionSimulatedType`, the interface that makes a synthetic sensor addressable (§5.9).

A Server does not need to implement all of it. `VisionSensorType` with `Media` is the mandatory core; everything else is claimed through the facets of clause 11. The subclauses below describe, for each type, why it exists, when a Server instantiates it and what a client does with it. Field-level declarations are in Annex A; units and orderings are fixed in §5.12.

### Type hierarchy {#sec-type-hierarchy}

The AddressSpace figures in this document use the OPC UA graphical notation of OPC 10000-3. A Node of an instance NodeClass — Object, Variable or View — is a plain rectangle, a Method is a rounded rectangle, and a type — ObjectType, VariableType, ReferenceType or DataType — is a rectangle standing on a shadow. An abstract type is set in *italics* rather than annotated in its label, and a Node whose BrowseName is a placeholder is written in angle brackets. A `HasTypeDefinition` reference carries a solid arrowhead; a `HasComponent` reference is the plain unlabelled arrow; every other ReferenceType is drawn with its BrowseName on the arrow.

```{figure}
id: fig-vis-notation
caption: Graphical notation used by the AddressSpace figures
source: figures/Vision-FigNotation.png
```

<!-- model-figure: root=ns=1;i=1002 external=BaseObjectType,BaseInterfaceType  graph=figures/fig-vis-hierarchy.mmd -->

```{figure}
id: fig-vis-hierarchy
caption: The type hierarchy
source: figures/Vision-FigHierarchy.png
```

Four abstract bases, each with concrete subtypes, and one interface. The pattern is deliberate: a client written against the abstract base — `VisionSensorType`, `MediaEndpointType`, `VisionCalibrationType`, `VisionResultType` — works against every subtype, including ones added in a later release.

Every other ObjectType in this specification is **concrete and directly instantiated**, and has no subtypes here: `VisionRootType`, `OpticsType`, `IlluminationType`, `CoordinateFrameType`, `InferencePipelineType` and `VisionFeedbackType`. They are absent from the figure above because it shows the subtype lattice and they take no part in one, not because their concreteness is undecided. `VisionFeedbackType` in particular is instantiated directly as the `Feedback` object of an `InferencePipelineType` (§9.1); a Server does not subtype it to obtain a feedback surface.

### Instance structure and references {#sec-instance-structure-and-references}

This is the shape of a populated address space. Solid arrows are hierarchical (`HasComponent`, `Organizes`, `HasProperty`); dashed arrows are the ReferenceTypes of §5.11; dotted arrows are NodeId-valued Properties.

```{figure}
id: fig-vis-instances
caption: Instance structure and references
source: figures/Vision-Fig2-Instances.png
```

Reading the diagram as a client would: find `Vision` under the Server Object, browse `Sensors`, pick a sensor, and everything needed to *use* its output hangs off it — the media to see it, the optics and calibration to interpret it, and, through `Pipelines`, the model that produced it and the feedback surface to correct it.

The three chains worth tracing are:

- **Imagery** — sensor → `Media` → endpoint → `GetStreamEndpoint`/`GetClip` → a URI (§6).
- **Meaning of a pose** — result → `FrameId` → `CoordinateFrameType` → `ParentFrame` → … → world, composed through the `ExtrinsicCalibrationType` transforms (§5.8, §7.3).
- **Provenance of an answer** — a historical result follows `ModelUsed` → model → `Digest`; the pipeline follows `Deployment` → `UsesModel` → model to discover what is serving now (§8.1, §12.6). `UsesModel` has cardinality exactly 1 so the deployment's current state is unambiguous; `ModelUsed` preserves the identity that answered after that state changes.

### `VisionRootType : BaseObjectType` {#sec-visionroottype-baseobjecttype}

The single entry point (§4.2). Holds the three folders and nothing else.

This type exists because discovery has to be deterministic. Without a well-known root a client would have to search the address space for anything that looks like a camera, and two Servers would place them differently. A Server instantiates exactly one, as a component of the Server Object.

`Sensors` is Mandatory; `Pipelines` and `Frames` are Optional, and their absence is meaningful — a Server with no `Models` folder is not doing AI, and a client can determine that in one Browse rather than by inference. A Server claiming *VIS-Calibration* is the exception: clause 11 makes `Frames` mandatory under that facet and requires it to hold every frame reachable through `MountedOn`, `SourceFrame` or `TargetFrame`, so that a client publishing or consuming poses has one deterministic entry point rather than having to walk the sensors to find frames.

*Table - VisionRootType Definition* {#tbl-visionroottype-definition defines=VisionRootType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionRootType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasComponent | Object | 1:Sensors |  | 0:FolderType | M |
| 0:HasComponent | Object | 1:Pipelines |  | 0:FolderType | O |
| 0:HasComponent | Object | 1:Frames |  | 0:FolderType | O |
| 0:HasProperty | Variable | 1:ClockSynchronised | 0:Boolean | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:TimeSyncSource | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### `VisionSensorType : BaseObjectType` (abstract) {#sec-visionsensortype-baseobjecttype-abstract}

The base of everything that senses.

| Member | Type | Rule | Meaning |
|---|---|---|---|
| `SensorId` | String | M | Unique within the Server |
| `RealityKind` | `VisionRealityKindEnum` | M | Physical, Simulated or Hybrid |
| `Modality` | `VisionSensorModalityEnum` | M | Area2D, Line2D, Depth3D, Thermal, … |
| `Manufacturer`, `Model`, `SerialNumber` | — | O | Nameplate |
| `DeviceUri` | String | O | Transport-level device identity, e.g. a GigE Vision device id |
| `FrameId` | String | O | This sensor's own camera frame |
| `Media` | `VisionMediaManagementType` | **M** | Media endpoints and their control surface |
| `Optics` | `OpticsType` | O | The lens |
| `Illumination` | `IlluminationType` | O | The light source |
| `Calibrations` | Folder | O | `VisionCalibrationType` instances |

This type is abstract because everything a client needs in order to *address* a sensor — identify it, learn what kind of sensing it does, and obtain imagery — is the same whether the device is a 2-D camera, a depth sensor, or a thermal imager. Putting that on an abstract base means a generic viewer, an asset inventory, or a monitoring system can be written once against `VisionSensorType` and work against every sensor kind, including kinds added later. Only the *acquisition parameters* differ, and those live on the concrete subtypes.

A Server never instantiates it directly. It instantiates `ImageSensorType`, `Depth3DSensorType`, or a vendor subtype, under `Vision/Sensors`.

`Media` is mandatory because a sensor a client cannot obtain imagery from is not usefully described. `RealityKind` is mandatory because a client that cannot tell a rendered frame from a real one cannot safely act on it (§4.3).

`SensorId` is the domain identifier for a sensor within this model; the Object's NodeId is its OPC UA address. Pipeline and result references resolve to that `VisionSensorType` Object and do not restate its nameplate as another identifier. `Manufacturer`, `Model` and `SerialNumber` are optional portable nameplate projections, not a second asset identity. They remain on the common base so a simulated sensor and a physical sensor expose the same readable shape without making DI or OPC 40100 a RequiredModel.

For a simulated sensor, or for a physical sensor described only by this specification, the populated projection is authoritative. Where DI or OPC 40100 also exposes an authoritative device/nameplate Object for the same physical sensor, that standard Object decides and each populated projection field **shall** equal its corresponding standard value. `DeviceUri` is not a nameplate field: it identifies the transport-level device endpoint and **shall not** be substituted for a DI `ProductInstanceUri` or another asset identifier.

*Table - VisionSensorType Definition* {#tbl-visionsensortype-definition defines=VisionSensorType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionSensorType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:SensorId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:RealityKind | 1:VisionRealityKindEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Modality | 1:VisionSensorModalityEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Manufacturer | 0:LocalizedText | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Model | 0:LocalizedText | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:SerialNumber | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:DeviceUri | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:FrameId | 0:String | 0:PropertyType | O |
| 0:HasComponent | Object | 1:Media |  | 1:VisionMediaManagementType | M |
| 0:HasComponent | Object | 1:Optics |  | 1:OpticsType | O |
| 0:HasComponent | Object | 1:Illumination |  | 1:IlluminationType | O |
| 0:HasComponent | Object | 1:Calibrations |  | 0:FolderType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### `ImageSensorType : VisionSensorType` {#sec-imagesensortype-visionsensortype}

The 2-D imaging sensor, and the layer OPC 40100-2 leaves empty. Acquisition parameters use GenICam SFNC 2.8 names and semantics, and `PixelFormat` uses PFNC naming; Annex H gives the member-by-member binding.

Mandatory: `Width`, `Height`, `PixelFormat`. Optional: `ExposureTime` (microseconds), `Gain`, `AcquisitionFrameRate`, `TriggerMode`, `TriggerSource`, `OffsetX`, `OffsetY`, `BinningHorizontal`, `BinningVertical`, `ReverseX`, `ReverseY`, and `Intrinsics`.

This type exists to close the gap that makes vision integration bespoke today: OPC 40100-2 models the lens and the lamp in detail but its `VisionImageSensorType` adds no members, and no OPC UA specification references GenICam. The parameters that determine what an image actually *is* — resolution, pixel format, exposure, gain — therefore have no standard place to live, and every integration invents one.

A Server instantiates it for any 2-D camera: area-scan, line-scan or thermal. `Modality` distinguishes them, so the member set does not have to.

A client uses it for three things. It sizes buffers and picks a decoder from `Width`, `Height` and `PixelFormat`. It reasons about motion blur and throughput from `ExposureTime` and `AcquisitionFrameRate` — a result that arrives late is often an exposure problem, not a network one. And it uses `Width` and `Height` together with `Intrinsics` to convert pixel coordinates into rays, which is what makes a 2-D detection usable in 3-D.

*Table - ImageSensorType Definition* {#tbl-imagesensortype-definition defines=ImageSensorType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ImageSensorType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:VisionSensorType defined in [](#sec-visionsensortype-baseobjecttype-abstract) |  |  |  |  |  |
| 0:HasProperty | Variable | 1:Width | 0:UInt32 | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Height | 0:UInt32 | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:PixelFormat | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:ExposureTime | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Gain | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:AcquisitionFrameRate | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:TriggerMode | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:TriggerSource | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:OffsetX | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:OffsetY | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:BinningHorizontal | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:BinningVertical | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:ReverseX | 0:Boolean | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:ReverseY | 0:Boolean | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:Intrinsics | 1:VisionIntrinsicsDataType | 0:BaseDataVariableType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### `Depth3DSensorType : VisionSensorType` {#sec-depth3dsensortype-visionsensortype}

Depth and point-cloud sensing: `MinDepth`, `MaxDepth`, `DepthScale`, `Baseline`, `PointsPerFrame`, and — where the device has one — the shape of its native depth image in `DepthWidth` and `DepthHeight`.

A **point cloud** (§3) is an unordered set of 3-D points, each carrying at least an (x, y, z) coordinate in a named frame. This type exists because a depth sensor's usable output is bounded in a way a 2-D camera's is not: `MinDepth` and `MaxDepth` state where measurements are valid at all, and `Baseline` determines how depth precision degrades with distance for a stereo device. A bin-picking client that ignores these will confidently return poses computed from noise at the edge of the working volume.

`DepthWidth` and `DepthHeight` are Optional and are present or absent together. A structured-light, time-of-flight or stereo device produces an ordered depth image with a native shape, and a client needs that shape for two things a count cannot give it: reprojecting a depth pixel back to a ray, and sizing a decoder for a depth stream that is not delivered as an unordered cloud. `PointsPerFrame` is a nominal count and is not a substitute. A sensor whose output genuinely has no image shape — a profile or line-triangulation device, or one that emits only an unordered cloud — omits both.

A device that produces both a depth map and a registered 2-D image is modelled as two sensors sharing a `FrameId`, not as one sensor carrying both member sets. `DepthWidth` and `DepthHeight` therefore do not duplicate `ImageSensorType.Width` and `Height`: they describe the depth image of a device that need not have a 2-D sensor at all, which is the common case for the structured-light sensors this type is instantiated for.

A Server instantiates it for stereo, time-of-flight, structured-light or laser-triangulation devices.

A client uses it to reject detections outside `[MinDepth, MaxDepth]`, to convert raw depth samples with `DepthScale`, and to size its expectations from `PointsPerFrame`.

Point clouds are obtained through a media endpoint and are never read as an OPC UA array: a single frame is routinely megabytes and would exceed practical message limits, and §12.4 explains why an OPC UA Subscription is the wrong transport for one.

*Table - Depth3DSensorType Definition* {#tbl-depth3dsensortype-definition defines=Depth3DSensorType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:Depth3DSensorType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:VisionSensorType defined in [](#sec-visionsensortype-baseobjecttype-abstract) |  |  |  |  |  |
| 0:HasProperty | Variable | 1:MinDepth | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:MaxDepth | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:DepthScale | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Baseline | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:PointsPerFrame | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:DepthWidth | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:DepthHeight | 0:UInt32 | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### `OpticsType` and `IlluminationType` {#sec-opticstype-and-illuminationtype}

Lens and light-source description. Member names are aligned with the `ILensType`, `ILampType` and `ILightingControllerType` of OPC 40100-2, so a Server implementing both models reports one set of values under two vocabularies rather than maintaining two.

These types exist because in machine vision the lens and the lighting determine whether a measurement is possible at all, and both are routinely changed in the field without the camera changing. Modelling them separately from the sensor means a maintenance system can record that a lens was swapped, and a diagnostic client can correlate a drift in results with a lamp whose `RelativeIntensity` has been falling.

A Server instantiates them whenever the values are known — typically on an inspection station, where they were chosen deliberately. A robot cell camera with a fixed lens and ambient light will often omit both.

A client uses `OpticsType.FocalLength` and `WorkingDistance` to sanity-check that the calibration it holds still corresponds to the physical setup, and `IlluminationType.Wavelength` to confirm that the illuminant matches what a colour-sensitive recipe assumed.

`OpticsType` carries `FocalLength`, `Aperture`, `WorkingDistance` and `MinimumWorkingDistance`, all Optional and all in the units §5.12 fixes, together with four further Optional members describing the lens as a part rather than as a setting: `Magnification`, the image size divided by the object size; `OpticalFormat`, the largest sensor diagonal the lens covers, conventionally written as a fraction of an inch such as `2/3"`; `MountType`, the mechanical mount — `C`, `CS`, `F`, `M12`; and `LensType`, the optical class — `Entocentric`, `Telecentric`, `Fisheye`. The last three are free-form `String`s: unlike the illumination vocabulary they describe mechanical and optical conventions that predate this model and are not standardised anywhere it could point to, and `OpticalFormat` in particular is a notation rather than a value space. A client matching a lens to a sensor uses `OpticalFormat` and `MountType`; one deciding whether a measurement is geometrically possible uses `Magnification` and `LensType`, since a telecentric lens and an entocentric one of the same focal length do not measure the same way.

`IlluminationType.LampType` and `LightingMode` are Optional and enumerated. `LampType` is a `VisionLampTypeEnum` — `Led`, `Fluorescent`, `Laser`, `Xenon`, `Halogen`, `Other` — and states the emitter technology. `LightingMode` is a `VisionLightingModeEnum` — `Continuous`, `Strobe`, `Modulated`, `Other` — and states how the emitter is currently being driven, which is what tells a client whether a short exposure on a moving part is viable.

Both are enumerated rather than free text. OPC 40100-2 types the corresponding members as an open `String` and an unconstrained `UInt32` and gives its permitted values only as prose examples, which leaves every integration to hard-code its own vocabulary — the failure this clause exists to prevent. The enumerations are seeded with exactly the values 40100-2 names, so the alignment holds at the level of values and not merely of member names, and `Other` keeps the value space open for an emitter neither standard anticipated. Annex D gives the conversion in both directions for a Server that implements both models.

### Frames and calibration {#sec-frames-and-calibration}

`CoordinateFrameType` names a frame, gives it a `Role` from the ISO 9787 vocabulary, links it to its `ParentFrame`, and carries its `Transform`. Frames form a tree, so a client can compose a chain from a camera frame to a world frame.

`Transform` is Optional and is the pose of **this** frame expressed in its `ParentFrame` — parent-to-child, the same direction as `ExtrinsicCalibrationType.Transform` in its `TargetFrame`, so a client composing a chain applies every transform it meets the same way and never has to invert one. `Transform.FrameId` **shall** equal the `FrameId` of the frame named by `ParentFrame`; a Server that cannot satisfy that has not established what its own numbers are relative to. A root frame has no `ParentFrame` and therefore no `Transform`.

`Transform` is a snapshot, not a guarantee of constancy. A static frame — a camera bolted to a gantry — holds a value that does not change, and a moving one, such as a tool frame on a robot, holds the pose at the moment it was read. A client that needs a pose synchronised with a specific image **shall not** read it from here; it takes the frame data accompanying the result, because a separately read `Transform` and a separately delivered image have no common timestamp.

`VisionCalibrationType` (abstract) carries the provenance a client needs to decide whether to trust a calibration: `CalibrationId`, `PerformedAt`, `Valid`, `ResidualError`, `Method`.

- `IntrinsicCalibrationType` adds `Intrinsics`.
- `ExtrinsicCalibrationType` adds `Mount` (`EyeInHand`, `EyeToHand`, `Fixed`), `SourceFrame`, `TargetFrame` and `Transform`.

These types exist because a 6-DoF pose is meaningless without the frame it is expressed in, and a frame is useless without a path to the frame the consumer cares about. This is the single most common failure in robot-vision integration: the pose is correct and the robot moves to the wrong place, because the two ends disagreed about what the numbers were relative to. `CoordinateFrameType` makes the frame a first-class node with a stable identity instead of a string convention, and `ExtrinsicCalibrationType` supplies the transforms that connect them.

A Server instantiates `CoordinateFrameType` whenever it publishes poses — clause 11 ties this to *VIS-Result-Detection* through §7.3 — `IntrinsicCalibrationType` whenever pixel coordinates need to become rays, and `ExtrinsicCalibrationType` whenever the sensor's output must be expressed in someone else's frame, which for a robot cell is always.

A client walks `ParentFrame` from the pose's own frame toward the frame it needs, composing each `Transform` on the way, exactly as Annex F.5 tabulates. Before doing so it **should** check `Valid` and `PerformedAt` — a stale calibration is worse than none, because it is wrong silently — and it uses `ResidualError` to decide how much positional tolerance to allow.

ISO 9787 standardises *which* frames exist, but no ISO, IEC, VDI or ANSI standard defines the hand-eye calibration *procedure*. Only the outcome is portable, so this model carries the outcome — the transform, the arrangement it applies to, and its residual — and says nothing about how it was obtained.

### `IVisionSimulatedType : BaseInterfaceType` {#sec-ivisionsimulatedtype-baseinterfacetype}

Applied to a simulated or hybrid sensor. Mandatory `SimulatorUri`, `StageIdentifier` and `PrimPath`; optional `GroundTruthAvailable` and `RandomizationSeed`. `StageIdentifier` and `PrimPath` reuse the identity contract of the OpenUSD specifications verbatim, so a synthetic sensor is addressable in exactly the terms a scene already uses (Annex C).

It is an interface rather than a subtype because being simulated is orthogonal to what a sensor senses. A subtype would force a simulated variant of every sensor type — `SimulatedImageSensorType`, `SimulatedDepth3DSensorType` — and a client would have to handle both. As an interface it applies to any sensor type, present and future, and leaves the sensor's own member set unchanged. That is what makes the sim/real symmetry of §4.3 hold: a client reads identical members either way and consults `RealityKind` only when it needs to care.

A Server applies it to every sensor whose `RealityKind` is `Simulated` or `Hybrid`; clause 11 makes *VIS-Simulation* required in that case rather than optional.

A training-data pipeline uses `RandomizationSeed` to reproduce a run exactly. A validation client uses `GroundTruthAvailable` to know that results from this sensor are simulator truth rather than predictions, and so **shall not** use them to measure model accuracy. An operator tool uses `PrimPath` to open the corresponding camera in the scene.

*Table - IVisionSimulatedType Definition* {#tbl-ivisionsimulatedtype-definition defines=IVisionSimulatedType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:IVisionSimulatedType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseInterfaceType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:SimulatorUri | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:StageIdentifier | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:PrimPath | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:GroundTruthAvailable | 0:Boolean | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:RandomizationSeed | 0:UInt64 | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### DataTypes {#sec-datatypes}

The enumerations are closed: each is contiguous from 0, and the repository validator enforces that. `Rtsp` and `Jpeg` are pinned at value 0 so that §6.2's mandatory-default guarantee is structural rather than editorial — an implementer reading only the NodeSet still gets it right.

| Enumeration | What it states |
|---|---|
| `VisionRealityKindEnum` | Whether a sensor is `Physical`, `Simulated` or `Hybrid` (§4.3). |
| `VisionSensorModalityEnum` | What the sensor senses — `Area2D`, `Line2D`, `Depth3D`, `Thermal`, `Multispectral`, `Event`, `Other`. |
| `VisionStreamProtocolEnum` | Wire protocol of a continuous stream. `Rtsp` is value 0 and the mandatory default (§6.2); `DataChannel` is the optional in-band path of §6.7. |
| `VisionClipFormatEnum` | Encoding of a single still. `Jpeg` is value 0 and the mandatory default. |
| `VisionVideoCodecEnum` | Codec carried by a stream endpoint — `H264`, `H265`, `Mjpeg`, `Av1`, `Raw`, `Other`. |
| `VisionEndpointStateEnum` | Lifecycle state shared by media endpoints, deployments and pipelines (§6.6). |
| `VisionEndpointAuthenticationEnum` | How the media plane authenticates, independently of the OPC UA session — `None`, `Basic`, `Digest`, `Token`, `MutualTls` (§12.1). |
| `VisionResultEvaluationEnum` | Overall inspection verdict — `Undefined`, `Ok`, `NotOk`, `NotDecidable`. Value semantics reused from OPC 40001-101. |
| `VisionToleranceStatusEnum` | Per-characteristic outcome — `InTolerance`, `OutOfTolerance`, `Indeterminate`, the last when uncertainty crosses a tolerance limit (§7.2). |
| `VisionFeedbackPurposeEnum` | Why a client is submitting feedback — `Overlay`, `Reconciliation`, `GroundTruthLabel` or `Trigger` (§9.2). |
| `VisionCalibrationMountEnum` | The camera-to-robot arrangement a hand-eye calibration applies to — `EyeInHand`, `EyeToHand`, `Fixed`, or `Unknown` where the Server cannot tell. |
| `VisionFrameRoleEnum` | The role a coordinate frame plays, from the ISO 9787 vocabulary — world, base, mechanical interface, tool, object — plus `Camera`, which ISO 9787 does not define. The mechanical interface and the tool are separate roles: an eye-in-hand calibration resolves to the flange, while a grasp is executed at the tool centre point. |
| `VisionDistortionModelEnum` | Which lens-distortion model the coefficients follow; §5.12 fixes their ordering per model. |

The structures are structures, not folders of Variables, because each is read as a unit or not at all. Splitting `VisionPose3DDataType` into seven Variables would let a client read a position from one acquisition and an orientation from the next, and would multiply the MonitoredItem count on a busy line by an order of magnitude. It also makes the array cases — `Detections`, `Characteristics` — a single value change rather than a variable-length subtree that has to be re-browsed whenever the part changes.

| Structure | What it carries |
|---|---|
| `VisionPose3DDataType` | A 6-DoF pose (§3): position in metres, orientation as a unit quaternion, the `FrameId` it is relative to, and an optional covariance. |
| `VisionBoundingBox2DDataType` | An axis-aligned or rotated box in pixel coordinates, for a detection in the image plane: `CenterX`, `CenterY`, `Width`, `Height`, `Rotation`. |
| `VisionBoundingBox3DDataType` | An oriented box in metres, for a detection localised in space: `Center` and `Size`. |
| `VisionImageReferenceDataType` | A descriptor for an image the client fetches elsewhere: `Uri`, `Timestamp`, `Digest` and format. The correlation key of §6.4 rule 4. |
| `VisionIntrinsicsDataType` | Camera intrinsics — focal lengths, principal point, skew, distortion model and coefficients, and the resolution they were computed at. |
| `VisionDetectionDataType` | One detected instance: `DetectionId`, `ClassLabel`, `ClassId`, `Confidence`, optional 2-D and 3-D geometry, optional pose, optional `TrackId`. Shaped on ROS 2 `vision_msgs`. |
| `VisionCharacteristicDataType` | One measured property of a part: `CharacteristicId`, `Name`, nominal, actual, deviation, tolerances, unit, **uncertainty** and status. Shaped on QIF (ISO 23952) Results. |
| `VisionStreamSessionDataType` | A granted media lease: the `Uri`, its expiry, and the `Protocol` actually served. Returned by `GetStreamEndpoint`, never published as a Variable (§12.2). |

Full field-level detail — DataType, ValueRank, ModellingRule, structure fields, enumeration values and Method signatures — is in the generated Annex A. Units and orderings for every quantity are fixed normatively in §5.12.

### ReferenceTypes {#sec-referencetypes}

Each ReferenceType subtypes `NonHierarchicalReferences`. They exist alongside the hierarchy because the hierarchy answers *what is part of this sensor*, whereas these answer *what does this node depend on*, and the two are not the same shape. A calibration is listed under its sensor, but a frame is not part of any one sensor — it is shared and lives in its own folder. A NodeId Property could express such a link, but a reference is browsable in **both** directions, which is what lets a client ask the reverse question — *which sensors does this calibration affect?* — the question that is asked the moment a calibration is found to be wrong.

The following constraints are **normative**; a Server **shall not** use these ReferenceTypes with other SourceNode or TargetNode types.

| ReferenceType | InverseName | SourceNode | TargetNode | Cardinality |
|---|---|---|---|---|
| `HasCalibration` | `IsCalibrationOf` | `VisionSensorType` | `VisionCalibrationType` | 0..n, at most one *valid* per calibration kind |
| `MountedOn` | `HasMounted` | `VisionSensorType` | `CoordinateFrameType` | 0..1 |
| `HasScenePrim` | `IsScenePrimOf` | `VisionSensorType` | a materialized camera prim (Annex C) | 0..1 |
| `ProducedBy` | `Produces` | `VisionResultType` | `InferencePipelineType` | 0..1 |

- **`HasCalibration`** links a sensor to a calibration that applies to it. Following it forward answers *how do I interpret this sensor's output*; following `IsCalibrationOf` back answers *which sensors does this calibration affect*, which is what a maintenance client asks after re-calibrating. The cardinality allows a history of superseded calibrations to remain browsable, so long as only one per kind is `Valid`.
- **`MountedOn`** links a sensor to the coordinate frame it is physically attached to — a frame of role `MechanicalInterface` for an eye-in-hand camera, a station frame for a fixed one. It is the structural statement of what the extrinsic calibration measures numerically, and it lets a client find the mounting frame without parsing a calibration.
- **`HasScenePrim`** links a sensor to the camera prim it corresponds to in a materialized OpenUSD stage. It exists so a client can navigate from sensor to scene without resolving `PrimPath` as a string. Required only where the Server claims *VIS-Interop-Scene* (Annex C).
- **`ProducedBy`** links a result to the pipeline that computed it. It duplicates the `Pipeline` Property deliberately: the Property is convenient to read with the result, the reference is browsable in reverse so a client can enumerate everything one pipeline produced.

The deployment-to-model link is **not** here. `UsesModel` is defined by *OPC UA — AI Model Management and Inference*, which also states its exactly-one cardinality; it identifies the model serving now. Historical provenance instead follows `VisionResultType.ModelUsed` to the model that actually answered and its `Digest`, and the **VIS-Inference-\*** facets require that specification so both paths have defined targets (§7.1, §11.2 and §12.6).

The following are **normative**:

- A `VisionResultType` instance **shall** identify its producer either by the `Pipeline` Property or by a `ProducedBy` reference. Where both are present they **shall** designate the same `InferencePipelineType` instance; a client **shall** treat the `ProducedBy` reference as authoritative.
- Where a sensor is calibrated, it **shall** carry a `HasCalibration` reference to each applicable calibration in addition to listing it under `Calibrations`.

### Units, encodings and conventions (normative) {#sec-units-encodings-and-conventions-normative}

Every physical quantity in this model is fixed here. A Server **shall** use these units and orderings, and **shall not** substitute others.

| Member or field | Unit / encoding |
|---|---|
| `ImageSensorType.ExposureTime` | microseconds |
| `ImageSensorType.Width`, `Height`, `OffsetX`, `OffsetY` | pixels |
| `VisionPose3DDataType.Position` | metres, ordered (x, y, z) |
| `VisionPose3DDataType.Orientation` | **unit quaternion ordered (x, y, z, w)** |
| `VisionPose3DDataType.Covariance` | row-major 6×6 over (x, y, z, rx, ry, rz), rotations in radians; an **empty array** means not reported |
| `VisionBoundingBox2DDataType` | pixels; origin is the **top-left** pixel; `Rotation` is **degrees clockwise** about the box centre |
| `VisionBoundingBox3DDataType.Size` | metres, ordered (x, y, z) |
| `VisionIntrinsicsDataType.Fx`, `Fy`, `Cx`, `Cy` | pixels, in the top-left-origin image frame |
| `OpticsType.FocalLength` | millimetres |
| `OpticsType.WorkingDistance`, `MinimumWorkingDistance` | metres |
| `IlluminationType.Wavelength` | nanometres |
| `IlluminationType.RelativeIntensity`, `Quality` | percent (0–100) |
| `Depth3DSensorType.MinDepth`, `MaxDepth`, `Baseline` | metres |
| `Depth3DSensorType.DepthWidth`, `DepthHeight` | pixels |
| `StreamEndpointType.Bitrate` | bits per second |
| `StreamEndpointType.FrameRate`, `ImageSensorType.AcquisitionFrameRate` | frames per second |
| `Confidence`, `VisionDetectionDataType.Confidence` | 0.0 to 1.0 inclusive |
| `ClipEndpointType.Quality` | 0 to 100, format-defined |
| `MaxInlineClipSize`, `MaxInlineFeedbackImageSize`, `SizeBytes` | bytes |
| `PixelFormat` | a GenICam **PFNC** name, e.g. `Mono8`, `BayerRG12`, `RGB8` |
| `DigestAlgorithm` | an IANA hash-function name with **at least 256-bit output and no known collision weakness**; the default is `SHA-256`. `MD5`, `SHA-1` and truncated variants **shall not** be used — see §12.6 |

**Measurement uncertainty.** `VisionCharacteristicDataType.Uncertainty` is the **expanded** uncertainty at **coverage factor k = 2** (approximately 95 %), per ISO 14253-1, expressed in the same unit as `Actual`. A value of `0` means uncertainty is not reported, and a Server that does not evaluate uncertainty **shall** report `0` rather than a guess. Without a fixed coverage factor the §7.2 `NotDecidable` rule would not be reproducible between Servers, so a Server **shall not** report uncertainty at another coverage factor.

**Frame and pose conventions.** Three further rules make a pose unambiguous, and a Server **shall** satisfy all of them.

1. Every frame in this model is **right-handed**. The table above fixes the units of a pose; handedness is what fixes its meaning, and neither the base OPC UA specification nor ISO 9787 states it for you.
2. `VisionPose3DDataType.Orientation` **shall** be normalised. A Server publishing a quaternion whose norm differs from 1 by more than 1e-6 is not describing a rotation, and a client **shall** treat such a pose as invalid rather than renormalising it silently — the error is more likely to be a wrong field order than a rounding artefact.
3. `FrameId` **shall** be non-empty wherever a pose is published (§7.3). This model defines **no** default frame: a pose whose frame is not named is not actionable, and §5.8 explains what happens when the two ends disagree about what the numbers were relative to.

> Rule 3 differs deliberately from specifications that treat an empty `FrameId` as a default working frame. Where poses are exchanged with such a model, the boundary **shall** substitute the named frame explicitly rather than passing the empty value through, because the same empty field means opposite things on either side.

**Distortion coefficient ordering.** `VisionIntrinsicsDataType.DistortionCoefficients` **shall** be ordered per `DistortionModel`:

| `DistortionModel` | Ordering |
|---|---|
| `None` | empty array |
| `BrownConrady` | k1, k2, p1, p2, k3 (further radial terms k4, k5, k6 may follow) |
| `KannalaBrandt` | k1, k2, k3, k4 |
| `RationalPolynomial` | k1, k2, p1, p2, k3, k4, k5, k6 |
| `Other` | undefined; a client **shall not** attempt to undistort |

**Structure field optionality.** The structures of this specification are plain structures: every field is always encoded. Optionality is expressed by explicit `Has…` Boolean fields. Where a `Has…` field is `false`, the corresponding field **shall** be encoded with default values and a client **shall** ignore its content. Where a field has no `Has…` companion, the sentinel for "not reported" is: empty array (`Covariance`, `DistortionCoefficients`), `0` (`Uncertainty`), empty `ByteString` (`Digest`), or empty `String` (`TrackId`, `Uri`).

**NodeId-valued Properties.** A Property whose DataType is `NodeId` (`Sensor`, `Pipeline`, `Deployment`, `ModelUsed`, `ParentFrame`, `SourceFrame`, `TargetFrame`, `PreferredStreamEndpoint`, `PreferredClipEndpoint`, `Dataset`, `BaseModel`, `CandidateModel`) **shall** contain either a NodeId resolvable in the same Server or a null NodeId. A null NodeId means "not set"; a Server **shall not** use a non-null NodeId that does not resolve.

**Pixel datum.** The origin corner is the top-left of the image, and the datum is the **corner** of the top-left pixel: the image occupies the continuous range `[0, W] × [0, H]`, so the centre of the top-left pixel is `(0.5, 0.5)` and a perfectly centred principal point is `Cx = W/2`. This is the convention the Annex B.2 derivation produces. It differs by exactly 0.5 px from the OpenCV convention used by `sensor_msgs/CameraInfo`, in which pixel *centres* fall on integer coordinates and a centred principal point is `(W−1)/2`; a client bridging to OpenCV or ROS **shall** subtract 0.5 from `Cx` and `Cy`, and Annex E.4 restates this.

**Frame precedence.** Where a pose is reachable both through a NodeId-valued frame Property and through the `FrameId` String inside `VisionPose3DDataType`, the structure field is authoritative for the pose's own frame and the Property is authoritative for the model's topology. Specifically, `ExtrinsicCalibrationType.Transform.FrameId` **shall** equal the `FrameId` of the `CoordinateFrameType` instance referenced by `TargetFrame`, and `CoordinateFrameType.Transform.FrameId` **shall** equal the `FrameId` of the instance referenced by `ParentFrame`; a Server **shall not** publish either pair in disagreement. A client that finds them inconsistent **shall** treat the calibration as unusable rather than choosing one.

**"Not specified" Method arguments.** Clause 6.5, 8.4 and 9.4 rely on a caller being able to leave an argument unspecified. Because most OPC UA built-in types have no distinguished null, the encoding is fixed here and **shall** be used:

| Argument DataType | "not specified" is encoded as | Notes |
|---|---|---|
| `NodeId` | a null NodeId | as for Properties, above |
| `String`, `ByteString` | an empty (zero-length) value | a null value **shall** be treated identically |
| `UtcTime`, `DateTime` | `0`, that is `1601-01-01T00:00:00Z` | the null DateTime of OPC 10000-6; a Server **shall not** interpret it as a literal instant |
| `UInt32`, `Double` (configuration arguments) | `0` | means "leave the current value unchanged"; a Server **shall not** return `Bad_OutOfRange` for `0` |
| Enumerations | *no unspecified value exists* | see below |

No enumeration argument of this specification has an "unspecified" literal, and none **shall** be added: `VisionStreamProtocolEnum.Rtsp` and `VisionClipFormatEnum.Jpeg` are fixed at value `0` by §6.2, so value `0` is an explicit request for the mandatory default. A caller with no preference therefore passes `0` and receives the default, which is the same outcome an "unspecified" literal would produce.

---

## Media endpoints (normative) {#sec-media-endpoints-normative}

### The default path {#sec-the-default-path}

**Media is obtained out-of-band.** OPC UA describes and controls the endpoint; the bytes travel over RTSP or HTTP. This preserves the layering of §4.1, keeps OPC UA payloads small, and keeps subscription semantics meaningful.

This is the default and the only path a Server is required to offer. Two optional facets deliver bytes through OPC UA itself, each for a narrow reason: §6.4 for a single still small enough to fit a `ByteString`, and §6.7 for a continuous stream where the Server implements the *OPC UA — Data Channels* draft. Neither displaces this clause.

### Mandatory defaults {#sec-mandatory-defaults}

A Server claiming the *VIS-Media-Rtsp* facet **shall** expose, for every sensor, at least one `StreamEndpointType` instance whose `StreamProtocol` is **`Rtsp`**. A Server claiming the *VIS-Media-Jpeg* facet **shall** expose, for every sensor, at least one `ClipEndpointType` instance whose `ClipFormat` is **`Jpeg`**. Both facets are required by *VIS-Base* (§11), so for any conformant Server both hold.

Every other protocol (`Rtsps`, `WebRtc`, `Srt`, `Hls`, `Mjpeg`, `GenDc`, `DataChannel`) and every other format (`Png`, `Tiff`, `Bmp`, `WebP`, `GenDc`) is **optional**. A client may therefore assume, without negotiation, that RTSP and JPEG are available.

`Rtsp` is value 0 of `VisionStreamProtocolEnum` and `Jpeg` is value 0 of `VisionClipFormatEnum`; the repository validator enforces both, so the guarantee cannot drift. The `StreamEndpoints` and `ClipEndpoints` folders each declare a `MandatoryPlaceholder` member, so the requirement is discoverable from the type and not only from this clause.

RTSP means **RTSP/1.0 (RFC 2326)** unless `ProtocolVersion` says otherwise. RTSP 2.0 is not backward compatible, so a Server offering only 2.0 **shall not** claim *VIS-Media-Rtsp*.

### Selecting and configuring endpoints {#sec-selecting-and-configuring-endpoints}

`VisionMediaManagementType` holds `StreamEndpoints` and `ClipEndpoints` folders, the `PreferredStreamEndpoint` and `PreferredClipEndpoint` pointers, and the Methods defined in §6.5.

**Endpoint selection (normative).** `GetStreamEndpoint` and `GetClip` each take an `Endpoint` argument. When it is null the Server **shall** use `PreferredStreamEndpoint` / `PreferredClipEndpoint`; when that pointer is also null the Server **shall** select the first endpoint in the corresponding folder, in BrowseName order, that satisfies the request. Both Methods return the `Endpoint` actually used, so the choice is never ambiguous to the caller.

Where `GetClip.Format` and the selected endpoint's `ClipFormat` differ, the **argument wins**: the Server either transcodes or returns `Bad_NotSupported` (§6.5). `Jpeg` is always supported by at least one endpoint (§6.2).

`PreferredProtocol` on `GetStreamEndpoint` is advisory: the Server returns what it can serve, which is at minimum RTSP.

**Profiles (normative).** A *profile* is a Server-local named configuration of an endpoint — an encoder preset, an ONVIF Media 2 profile, a vendor recipe — and has no node of its own. `MediaEndpointType.DefaultProfileName` names the one the endpoint uses when `GetStreamEndpoint` is called with an empty `ProfileName`, and is empty where the endpoint has a single configuration and takes no profile name at all.

This specification defines no way to enumerate the others, deliberately: their number, names and meaning are Server-local, and a folder of them would be a second source of truth for a configuration this model does not otherwise describe. The consequence is stated plainly rather than left to be discovered — a client with no out-of-band knowledge of a Server **shall** pass an empty `ProfileName`, and a Server **shall** honour that by selecting `DefaultProfileName`. Guess-and-retry against `Bad_InvalidArgument` is not a discovery mechanism and a client **should not** use it. A client that does know a Server's profile names, because it was configured with them, passes one.

**Intrinsics are the sensor's, and are rescaled by the consumer (normative).** `ImageSensorType.Intrinsics` are expressed at the sensor's native `Width` and `Height` and are authoritative for the sensor's native frame. A `StreamEndpointType` routinely serves a smaller frame — a 4K sensor commonly streams 1080p to keep the bitrate manageable, and `ConfigureStreamEndpoint` lets a client change it — so the two will disagree.

A client interpreting a frame served on such an endpoint **shall** rescale `Fx`, `Fy`, `Cx` and `Cy` from `(sensor.Width, sensor.Height)` to `(endpoint.Width, endpoint.Height)` before applying them, scaling `Fx` and `Cx` by `endpoint.Width / sensor.Width` and `Fy` and `Cy` by `endpoint.Height / sensor.Height`. Where `ImageSensorType.OffsetX` or `OffsetY` is non-zero the sensor is delivering a crop, and the principal point is not at the centre of the delivered image: the client **shall** subtract the offset from `Cx` and `Cy` *before* scaling, because the offset is in native sensor pixels. A Server **shall not** republish rescaled intrinsics as the sensor's `Intrinsics`, which would misreport the calibration it actually holds.

A client that skips this converts pixel coordinates to rays that are wrong by the ratio of encoder to sensor resolution. The error is proportional, so it survives every sanity check that looks at units or magnitude, and it is one of the most common integration faults in this domain.

**Data-channel endpoints are never selected implicitly (normative).** A `StreamEndpointType` whose `StreamProtocol` is `DataChannel`, and any endpoint whose `DataChannelSource` is non-null, **shall not** be returned by the selection rule above unless the caller passed `PreferredProtocol = DataChannel` explicitly. A Server **shall not** make such an endpoint the target of `PreferredStreamEndpoint` or `PreferredClipEndpoint`. The reason is that §5.12 fixes value `0` (`Rtsp`) as what an unspecified preference means, and a data channel additionally requires a client capability the Server cannot assume: a client that cannot open one would receive an endpoint it cannot use. A caller that *does* pass `DataChannel` and finds none available receives `Bad_NotSupported` (§6.5) and falls back to the out-of-band path.

### Optional inline clip delivery {#sec-optional-inline-clip-delivery}

A `ClipEndpointType` **may** additionally publish the encoded image inline, so that clients can `Read` it or, more usefully, **subscribe to it with a MonitoredItem**. The value changes once per acquisition, which suits one-image-per-inspected-part operation.

This facet is governed by five rules:

1. **The out-of-band path remains the default.** Inline delivery is optional, is declared by the *VIS-Media-Inline* facet, and a Server is fully conformant without it. `InlineDeliveryEnabled` states whether it is active.
2. **Size is bounded, and the bound is a Server capability.** A Server implementing this facet **shall** publish `Server.ServerCapabilities.MaxByteStringLength`, and `MaxInlineClipSize` **shall not** exceed it. A Server **shall not** publish an inline clip larger than `MaxInlineClipSize`. Where a Session's `MaxResponseMessageSize`, or the channel's negotiated `MaxMessageSize`, is smaller than `MaxInlineClipSize`, the Server **shall** treat that Session as though `MaxInlineClipSize` were the smaller value and apply rule 3 accordingly. `MaxByteStringLength` is a Server-wide capability rather than a per-Session negotiated value; this rule is what makes one published bound safe for Sessions with differing message limits.
3. **Overflow is explicit.** When the encoded image exceeds the effective limit of rule 2, the Server **shall** set the `LatestClip` StatusCode to **`Bad_EncodingLimitsExceeded`** and **shall not** truncate. The client **shall** fall back to `LatestClipMetadata.Uri`, which remains valid.
4. **Correlation is defined.** A Server **shall** update `LatestClip` and `LatestClipMetadata` so that both reflect the same acquisition. A client **shall** use `LatestClipMetadata.Timestamp` together with `Digest` as the correlation key, and **shall not** assume that two independently received values belong to the same frame. A Server **should** report both in the same NotificationMessage where the Subscription's revised `maxNotificationsPerPublish` permits it, but correlation **shall not** depend on that: `maxNotificationsPerPublish` is chosen by the client, so a Server cannot guarantee co-delivery.
5. **Initial and disabled states are defined.** Before the first acquisition a Server **shall** report both `LatestClip` and `LatestClipMetadata` with StatusCode `Bad_NoDataAvailable`. Where `InlineDeliveryEnabled` is `false` the Server **shall** report `LatestClip` with StatusCode `Bad_NotSupported`; `LatestClipMetadata` remains readable.

A Server **should** offer a reduced-resolution or reduced-quality thumbnail profile that fits the limit, rather than persistently returning `Bad_EncodingLimitsExceeded`.

**Where a data channel is also available.** A still that exceeds the effective limit of rule 2 is exactly the case §6.7 handles better: a data channel is not bounded by `MaxByteStringLength` and does not force the client onto a second protocol. Where a Server implements both facets on the same `ClipEndpointType`, it **should** offer the oversized image on the data channel rather than only returning `Bad_EncodingLimitsExceeded`. This is a *should*, not a *shall*, because the data channel depends on a draft and on a client capability. The inline facet is **not** deprecated by §6.7 and remains fully conformant on its own: it is the only in-band still path available to a Server that does not implement that draft.

`GetClip` follows the same discipline: it always returns a descriptor carrying a `Uri`, and returns bytes in `InlineImage` only when `RequestInline` is true **and** the encoded image fits.

**Inline delivery is not a video path.** It exists for single stills. A client that wants continuous imagery uses a `StreamEndpointType`.

### Media Method definitions (normative) {#sec-media-method-definitions-normative}

Argument order is as declared in Annex A. An argument that is "not specified" is encoded as defined in §5.12, which fixes the encoding for each DataType used below. A Server **shall** return the listed StatusCode when the stated condition holds, and **shall not** return `Good` in that case.

**`GetStreamEndpoint(Endpoint, ProfileName, PreferredProtocol) → (Session, Endpoint)`** — leases a stream. `Endpoint` null selects per §6.3; `ProfileName` empty selects the endpoint's `DefaultProfileName` per §6.3, and is what a client without prior knowledge of the Server passes. `PreferredProtocol` is advisory — the Server selects per §6.3 and reports what it actually granted in `Session`, so a caller that requires a specific protocol **shall** inspect the result rather than assume. The returned `Session.Uri` **may** embed a single-use or time-limited credential, which is why it is a Method result and not a browsable Variable. A Server **shall** set `Session.ExpiresAt` and **shall** expire the lease then, even if `ReleaseStreamEndpoint` is never called.

| StatusCode | Condition |
|---|---|
| `Bad_NotFound` | `Endpoint` is non-null but is not a `StreamEndpointType` of this sensor |
| `Bad_InvalidArgument` | `ProfileName` is non-empty and unknown to the selected endpoint |
| `Bad_ResourceUnavailable` | `ActiveSessions` has reached `MaxSessions` |
| `Bad_NotSupported` | `Endpoint` is non-null and cannot serve `PreferredProtocol` — the caller named both an endpoint and a protocol that endpoint does not offer, so §6.3 fallback does not apply; **or** `PreferredProtocol` is `DataChannel` and no data-channel endpoint is available on this sensor (§6.7) |
| `Bad_UserAccessDenied` | the caller is not authorized for media access (§12.1) |

Where the selected endpoint is a data-channel endpoint (§6.7), `Session.Uri` **shall** be empty: the bytes arrive on a data channel the client opens against the endpoint's `DataChannelSource`, not at a location the Server can name in a URI. `Session.ExpiresAt` still applies and still bounds the lease. A client **shall** read `DataChannelSource` from the returned `Endpoint` rather than expecting it in `Session`, because the source Node is a property of the endpoint and outlives any one lease.

**`ReleaseStreamEndpoint(SessionToken)`** — ends a lease. A Server **shall** return `Good` for any token it is not currently holding, whether that token has expired, has already been released, was garbage-collected, or was never issued. This makes a client's cleanup path idempotent and survivable across Server restart; distinguishing "never issued" would require unbounded token retention, so no StatusCode is defined for it.

| StatusCode | Condition |
|---|---|
| `Bad_UserAccessDenied` | the caller is not authorized for media access (§12.1) |

**`ConfigureStreamEndpoint(Endpoint, Codec, Width, Height, FrameRate, Bitrate)`** — changes encoding parameters. Per §5.12, a numeric argument of `0` means "leave unchanged", so a caller may change the codec alone. A Server **shall** either apply the request exactly, or clamp each unsupported value to the nearest supported one and return `Good_Clamped`, or reject with `Bad_OutOfRange`. It **shall not** silently apply a different value and return `Good`. The effective values are readable on the endpoint afterwards.

| StatusCode | Condition |
|---|---|
| `Good_Clamped` | one or more values were clamped to a supported value |
| `Bad_NotFound` | `Endpoint` is not a `StreamEndpointType` of this sensor |
| `Bad_OutOfRange` | a non-zero value is unsupported and the Server does not clamp |
| `Bad_NotSupported` | `Codec` is not supported by the endpoint |
| `Bad_InvalidState` | the endpoint has active sessions and cannot be reconfigured |

**`SelectEndpoint(StreamEndpoint, ClipEndpoint)`** — sets the preferred pointers. A null argument leaves that pointer unchanged.

| StatusCode | Condition |
|---|---|
| `Bad_NotFound` | an argument is non-null and does not resolve |
| `Bad_TypeMismatch` | an argument resolves to a node of the wrong endpoint kind |

**`GetClip(Endpoint, ResultId, Timestamp, Format, RequestInline) → (Image, Endpoint, InlineImage)`** — returns the still associated with `ResultId`, or the frame nearest `Timestamp` when `ResultId` is empty. Exactly one selector **shall** be supplied; per §5.12 an unspecified `ResultId` is the empty String and an unspecified `Timestamp` is `1601-01-01T00:00:00Z`. `Image` is always populated with a resolvable `Uri`; `InlineImage` is populated only when `RequestInline` is true and the encoded image fits the effective limit of §6.4 rule 2, and is otherwise empty with `Image.Uri` still valid.

| StatusCode | Condition |
|---|---|
| `Bad_InvalidArgument` | both selectors unspecified, or both specified |
| `Bad_NotFound` | `ResultId` does not designate a currently retained result produced from **this sensor**, including an identifier whose result node was evicted; or no frame near `Timestamp` within the frame/clip retention policy |
| `Bad_NotSupported` | `Format` cannot be produced by any clip endpoint of this sensor |
| `Bad_UserAccessDenied` | the caller is not authorized for media access (§12.1) |

`ResultId` is immutable and unique Server-wide (§7.1), but this Method is scoped to one sensor. A Server **shall** return `Bad_NotFound` when `ResultId` designates a result produced from a different sensor or a result node that has been evicted, and **shall not** disclose whether the identifier exists or previously existed elsewhere in the Server — otherwise the per-sensor authorization of §12.1 could be bypassed simply by presenting another sensor's identifier here. Where results are subject to per-sensor authorization, `ResultId` **shall not** be derived from a predictable sequence.

### Endpoint state model (normative) {#sec-endpoint-state-model-normative}

`VisionEndpointStateEnum` is used by `MediaEndpointType` and `InferencePipelineType`. *OPC UA — AI Model Management and Inference* defines its own `DeploymentStateEnum` with the same five literals and the same transitions, so a client can apply one rule to both without this specification imposing a dependency. All transitions are **Server-driven**; no Method sets `State` directly.

```{figure}
id: fig-vis-endpointstate
caption: The media endpoint state model
source: figures/Vision-Fig3-EndpointState.png
```

| State | Media endpoint | Deployment | Pipeline |
|---|---|---|---|
| `Inactive` | declared, not serving | model not loaded | not bound, or disabled |
| `Ready` | able to serve, no session | model loaded, idle | bound, awaiting a trigger |
| `Active` | at least one session leased | executing inference | producing results |
| `Degraded` | serving below configured quality | exceeding `LatencyBudget` | producing results at reduced quality or rate |
| `Faulted` | unable to serve | model failed to load or execute | unable to produce results |

A Server **shall** report `Degraded` rather than `Active` when it knows the configured quality, latency budget or rate is not being met, and `Faulted` rather than `Inactive` when the cause is a failure rather than configuration.

### Media on an OPC UA data channel (optional) {#sec-media-on-an-opc-ua-data-channel-optional}

> **Draft dependency.** This clause is defined against *OPC UA — Data Channels*, a **working draft in this repository** (§2), not a released OPC UA specification. Its NodeIds, MessageType and StatusCodes are provisional and may change or be withdrawn. This facet is **entirely optional**: *VIS-Base* does not require it, §6.2's RTSP and JPEG guarantee is unaffected by it, and a Server that does not implement it — which will be most Servers — is fully conformant. Nothing in this specification's NodeSet references that draft's identifiers, so adopting or ignoring it changes nothing about loading this model.

Every other path in this clause requires a second protocol beside OPC UA: a client that has an authenticated OPC UA session must still reach the camera over RTSP or HTTPS, through whatever firewall, NAT and credential arrangement that implies. A data channel carries the bytes over the SecureChannel the client **already has**. There is no second connection to authorize, no media credential to issue or leak (§12.2), and no second port to open.

A Server offering this facet publishes it on an existing `StreamEndpointType` or `ClipEndpointType`, and a client recognises it by:

- `DataChannelSource` (`NodeId`) is **non-null** and designates the Object on which the client opens the data channel. This is the discriminator.
- `EndpointUri` is **empty** where the data channel is the endpoint's only path, because there is no location a URI could name. Where the endpoint also serves out-of-band, `EndpointUri` keeps its usual meaning and the data channel is an additional path to the same content.
- `DataChannelContentType` names the IANA media type the channel carries — `video/H264`, `image/jpeg`. It duplicates the source's own `ContentType` deliberately, so a client can learn the payload type from **this** model without the Data Channels model being present.
- For a stream endpoint, `StreamProtocol` **may** be `DataChannel`. A Server **shall** set it to `DataChannel` only where the data channel is the endpoint's only path; where the endpoint also serves RTSP, `StreamProtocol` keeps naming the out-of-band protocol and `DataChannelSource` alone signals the additional path.

This specification defines no wire format and no Service. Framing, flow control, delivery modes, the Services that open and close a channel, and the transport bindings are all defined by the Data Channels draft. This clause states only *where* the data channel for a media endpoint is, and *what* the bytes on it are.

**Discovery and graceful absence (normative).** A client **shall** determine support before relying on it, and **shall** be able to proceed without it:

1. A client **shall** treat the absence of `Server.ServerCapabilities.DataChannelCapabilities` as meaning the Server does not support data channels, and **shall not** attempt to open one.
2. A client **shall** treat `Bad_ServiceUnsupported` from `OpenDataChannel` as definitive for that SecureChannel, and **shall not** retry.
3. A client **shall not** probe by sending frames. On a Server that does not implement the draft this is indistinguishable from an attack and costs the connection.
4. Where a data channel is unavailable for any reason, a client **shall** fall back to the endpoint's out-of-band path, which §6.2 guarantees exists.
5. A Server **shall not** require a client to use a data channel. Every sensor still carries the mandatory RTSP and JPEG endpoints of §6.2.

**Correlation for clips.** Where a clip endpoint delivers stills on a data channel, the correlation problem is the one §6.4 rule 4 already solves, and the same rule applies: a client **shall** correlate bytes received on the channel with `LatestClipMetadata` — or with the `Image` descriptor returned by `GetClip` — using `Timestamp` together with `Digest`. No second correlation mechanism is defined, and a Server **shall not** invent one.

**Relationship to the other facets.** *VIS-Media-DataChannel* is additive to *VIS-Media-Rtsp*, *VIS-Media-Jpeg* and *VIS-Media-Inline*; it replaces none of them. Its most useful role is the case §6.4 rule 3 handles least well — a still too large for `MaxByteStringLength` — where it removes the size ceiling entirely rather than forcing the client onto a URI fetch.

---

## Result semantics (normative) {#sec-result-semantics-normative}

This clause is the reason the specification exists. OPC 40100-1, OPC 40001-101 and OPC 40210 all type their result payload as `BaseDataType[]` and decline to define it. This model defines it.

### `VisionResultType` (abstract) {#sec-visionresulttype-abstract}

Mandatory `ResultId` and `CreationTime`. Optional `Sensor`, `Pipeline`, `Frame` (a `VisionImageReferenceDataType`), and the trust members `ModelUsed`, `ModelVersionUsed`, `Confidence` and `ExplanationUri`.

The trust members are not decoration. Where a deployment falls under a high-risk regime, the question *"which model version produced this decision, and on what basis"* must be answerable from the address space rather than reconstructed from logs (§12.5).

`ModelUsed` is the `NodeId` of the model that actually produced the result. Where the Server also implements *OPC UA — AI Model Management and Inference*, a non-null value **shall** resolve to the `ModelType` returned as `ModelUsed` by the synchronous invocation or retained on the asynchronous inference job. It may differ from the model reached through the pipeline's current `Deployment → UsesModel` path after a fallback, promotion or `FollowsRef` repointing. Where `ModelUsed` is non-null and `ModelVersionUsed` is populated, `ModelVersionUsed` **shall** equal the referenced `ModelType.Version`.

A Server **shall** retain a `ModelType` instance referenced by `ModelUsed` for at least as long as it retains any `VisionResultType` instance that names it. Otherwise the Server would publish a non-null NodeId that no longer resolves and the historical decision chain would end before its digest.

`ResultId` is immutable and unique Server-wide. A Server **shall never** reuse a `ResultId` for a different result, including after the original result is evicted or after the Server restarts. Persistence of this non-reuse guarantee is part of the identifier contract; eviction frees a result node, not its identity.

*Table - VisionResultType Definition* {#tbl-visionresulttype-definition defines=VisionResultType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionResultType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:ResultId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:CreationTime | 0:UtcTime | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Sensor | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Pipeline | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:ModelVersionUsed | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Confidence | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:ExplanationUri | 0:String | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:Frame | 1:VisionImageReferenceDataType | 0:BaseDataVariableType | O |
| 0:HasProperty | Variable | 1:ModelUsed | 0:NodeId | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

#### Result-node retention {#sec-result-node-retention}

Where an `InferencePipelineType` instantiates `Results`, the applicable inference facet requires both `MaxResultAge` (`Duration`) and `MaxRetainedResults` (`UInt32`) to be instantiated. At least one value **shall** be non-zero. Zero means **no limit in that dimension**; it does not authorize arbitrary eviction. `MaxResultAge` is measured from `CreationTime` in the milliseconds used by `Duration`.

A result **shall** remain browsable and readable under `Results` until either its age exceeds the non-zero `MaxResultAge`, or retaining it would exceed the non-zero `MaxRetainedResults`. Under count pressure the Server **shall** evict the result with the oldest `CreationTime` first; equal `CreationTime` values are ordered by `ResultId` using ascending Unicode code-point order. Lowering either limit **shall** immediately evict results in that order until the retained set is compliant. Raising a limit does not restore evicted nodes.

After eviction, Services addressing the old result node **shall** return the applicable `Bad_NodeIdUnknown`. Methods that select by `ResultId`, including `GetClip` and the feedback Methods, **shall** return `Bad_NotFound` when the result is no longer retained in their scope. The permanent non-reuse rule above prevents either response from later resolving to a different result.

These limits govern only **result nodes** under `Results`. They do not govern the frame or clip named by `Frame`, an out-of-band explanation or model artefact named by a URI, or evidence retained by an external application. Each has an independent owner and retention policy. Evicting a result therefore neither requires nor implies deleting media, external artefacts or application evidence, whose retention may outlive the Vision node. Conversely, retaining a result does not promise that an external URI remains resolvable unless another applicable policy requires it.

### `InspectionResultType` {#sec-inspectionresulttype}

The machine-vision outcome. Mandatory `Evaluation` and `Characteristics`; optional `PartId` and `RecipeId`.

`VisionResultEvaluationEnum` reuses the value semantics of the OPC 40001-101 `ResultEvaluationEnum` — `Undefined`, `Ok`, `NotOk`, `NotDecidable` — so a client already consuming Machinery results needs no new interpretation rules.

`VisionCharacteristicDataType` mirrors the QIF (ISO 23952) Results field set: `Nominal`, `Actual`, `Deviation`, `LowerTolerance`, `UpperTolerance`, `Unit`, **`Uncertainty`** and `Status`. Units, the sentinel for "not reported", and the coverage factor are fixed in §5.12.

Uncertainty is what makes a verdict reproducible by a third party, and it is the reason `NotDecidable` exists. The rule is normative: where the interval `Actual ± Uncertainty` crosses a tolerance limit, a Server **shall** report `Status = Indeterminate` for that characteristic, and **shall not** assert `Ok` or `NotOk` for the result on the strength of the point estimate alone. Where any characteristic is `Indeterminate`, the result `Evaluation` **shall** be `NotDecidable` unless another characteristic is independently `OutOfTolerance`, in which case it **shall** be `NotOk`.

Because §5.12 fixes the coverage factor at k = 2, two Servers that both evaluate uncertainty and are presented with the same measurement reach the same verdict. The converse is equally normative and is the limit of the guarantee: `Uncertainty = 0` means uncertainty was **not evaluated**, not that it is negligible, so the interval test above degenerates to the point estimate and the resulting `Evaluation` is **not comparable** with that of a Server which does evaluate it. A Server claiming *VIS-Result-Inspection* **shall** therefore either report a genuine expanded uncertainty for every characteristic it publishes, or report `0` for every characteristic — it **shall not** mix the two within one result, since that would make the result's own `Evaluation` incoherent. A client **shall not** compare verdicts across Servers, or across results, whose uncertainty reporting differs in this respect.

*Table - InspectionResultType Definition* {#tbl-inspectionresulttype-definition defines=InspectionResultType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:InspectionResultType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:VisionResultType defined in [](#sec-visionresulttype-abstract) |  |  |  |  |  |
| 0:HasProperty | Variable | 1:Evaluation | 1:VisionResultEvaluationEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:PartId | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:RecipeId | 0:String | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:Characteristics | 1:VisionCharacteristicDataType[] | 0:BaseDataVariableType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### `DetectionResultType` {#sec-detectionresulttype}

The robotics-vision outcome. Mandatory `Detections`; optional `FrameId` naming the frame that detection poses are expressed in.

`VisionDetectionDataType` follows ROS 2 `vision_msgs` conventions: a class label and id, a confidence, an optional 2-D box, an optional 3-D box, an optional 6-DoF `Pose`, and an optional `TrackId`. The `HasBoundingBox2D`, `HasBoundingBox3D` and `HasPose` flags state which geometry is meaningful, and the rule governing them is in §5.12: where a flag is `false` a client **shall** ignore the corresponding field's content.

A pose is only actionable if its frame is known, which is why `VisionPose3DDataType` carries `FrameId` and why §5.8 exists. `FrameId` **shall** be non-empty whenever `HasPose` is `true`. Where the Server also implements *VIS-Calibration*, `FrameId` **shall** be the `FrameId` of a `CoordinateFrameType` instance that exists in the same Server, so that the pose can be composed through the frame tree. Where the Server does not implement *VIS-Calibration* it has no frame tree to resolve against; `FrameId` **shall** then be an identifier that is stable for the lifetime of the Server and agreed out of band, and a client **shall not** assume it is resolvable in the address space. A Server that publishes poses **should** implement *VIS-Calibration* for exactly this reason.

*Table - DetectionResultType Definition* {#tbl-detectionresulttype-definition defines=DetectionResultType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:DetectionResultType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:VisionResultType defined in [](#sec-visionresulttype-abstract) |  |  |  |  |  |
| 0:HasComponent | Variable | 1:Detections | 1:VisionDetectionDataType[] | 0:BaseDataVariableType | M |
| 0:HasProperty | Variable | 1:FrameId | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### `SegmentationResultType` {#sec-segmentationresulttype}

Mandatory `Mask`, a `VisionImageReferenceDataType`. Masks are images and follow the media rules of §6; they are referenced, not inlined into the result.

Optional `LabelClasses`, a `String` array naming what the mask's pixel values mean. Array position **is** the mapping: the name at index *i* names the class encoded by pixel value *i*. Index `0` is reserved for background — the pixels the segmentation assigns to no class — so a mask distinguishing two classes carries three entries. A Server that publishes a mask **should** publish `LabelClasses` with it; without it the mask is an image of numbers whose meaning is agreed out of band, which is the situation this clause exists to end.

The mapping is by pixel value, so a mask is single-label: one pixel belongs to one class. This is *semantic* segmentation. An *instance* segmentation, where two pixels may carry the same class but belong to different objects, is expressed by giving each instance its own value and naming them accordingly — `["background", "bolt_1", "bolt_2"]` — because a client that must tell two bolts apart needs them to differ in the mask itself, not in a channel convention it has to be told about. Multi-label masks, where one pixel carries several classes at once, are not expressible here.

`LabelClasses` on a result names the classes of *that* mask. `ModelType.LabelClasses` (Annex B.3) names the classes the model was trained to produce. They are usually equal and are not required to be: a pipeline may publish a mask covering only the classes present in the frame.

*Table - SegmentationResultType Definition* {#tbl-segmentationresulttype-definition defines=SegmentationResultType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:SegmentationResultType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:VisionResultType defined in [](#sec-visionresulttype-abstract) |  |  |  |  |  |
| 0:HasProperty | Variable | 1:LabelClasses | 0:String[] | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:Mask | 1:VisionImageReferenceDataType | 0:BaseDataVariableType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### Events (normative) {#sec-events-normative}

A result is a **retained record**; an event is an **occurrence**. The types above are records: within the explicit limits of §7.1.1 they persist and are re-readable, so a late consumer can find them. That is why they are Objects rather than notifications. An event-only pipeline may omit `Results` entirely; it raises occurrences but makes no result-node retention promise. This distinction avoids adding meaningless retention members to such a pipeline.

This clause adds the occurrence. `VisionEventType` is the abstract base; `ObjectDetectedEventType` and `InspectionCompletedEventType` are what a Server raises. They are ordinary OPC UA EventTypes, so a client subscribes with an `EventFilter` and the existing machinery of OPC 10000-4 applies unchanged.

| Type | Member | Type | Rule | Meaning |
|---|---|---|---|---|
| `VisionEventType` *(abstract)* | `ResultId` | String | M | The result that substantiates this event |
| | `Sensor` | NodeId | M | The sensor the observation was made with |
| | `GroundTruth` | Boolean | M | True where this is simulator ground truth, not a prediction |
| | `Pipeline` | NodeId | O | The pipeline that produced the result, where one did |
| | `ModelVersionUsed` | String | O | Version of the model that decided; repeated as a filterable value while the result carries the model NodeId |
| | `Confidence` | Double | O | 0.0 to 1.0; absent is not zero |
| | `InferenceEndTime` | UtcTime | O | When inference finished; `Time` is when the frame was acquired |
| `ObjectDetectedEventType` | `Detection` | `VisionDetectionDataType` | M | The detection this event reports |
| `InspectionCompletedEventType` | `Evaluation` | `VisionResultEvaluationEnum` | M | The verdict |
| | `PartId` | String | O | The inspected part, where the result names one |
| | `RecipeId` | String | O | The recipe that ran, where the result names one |
| | `FailedCharacteristics` | `VisionCharacteristicDataType[]` | O | Only the characteristics whose `Status` is not `InTolerance` |

**An event names its result and does not repeat it.** Every event carries `ResultId`, and a consumer that needs detail may read the retained `VisionResultType` it names. That read can return `Bad_NodeIdUnknown` after retention expires; an event is not an extension of the result node's lifetime. Copying result content into the event would create a second copy of a fact that can disagree with the first. Two fields are deliberate exceptions, because they are what a consumer filters on and requiring a read to obtain them would defeat the purpose: the `Detection` on `ObjectDetectedEventType`, and `Evaluation` on `InspectionCompletedEventType`.

`FailedCharacteristics` carries the failing characteristics and only those; a passing inspection carries an empty array. Repeating every characteristic would duplicate the result for the common case where none failed, while repeating the failing ones lets a consumer act on *why* a part was rejected without a read. A Server **shall not** include a characteristic whose `Status` is `InTolerance`, and a consumer **shall not** treat the array as the complete characteristic set — that is in the result.

**`Time` is when the frame was acquired.** `BaseEventType.Time` is the time of the occurrence, and for an inferred observation the occurrence is the *frame*, not the inference. A Server **shall** set `Time` to the acquisition timestamp of the frame the result was derived from — the `Timestamp` of the result's `Frame`, where it carries one — and **shall not** set it to the moment inference completed. `InferenceEndTime` carries that moment separately, so the difference between the two is the inference latency of this observation. A Server that cannot establish an acquisition timestamp **shall** omit `InferenceEndTime` rather than set both to the same value, because equal values assert a latency of zero.

**One event per detection.** A `DetectionResultType` carrying *n* detections raises *n* `ObjectDetectedEventType`s, all naming the same `ResultId`. This is what makes `ClassLabel` and `Confidence` available to an `EventFilter`, so a client asks for the classes it cares about above a confidence it chooses and the Server sends nothing else. A single event per result would move that filtering to the client and give up most of the reason to raise events at all. A Server **may** omit events for detections a configured threshold excludes, and **shall not** vary the `ResultId` between events derived from one result.

**Inferred is not measured.** `GroundTruth` is Mandatory on every event. It is `true` only where the value is simulator ground truth rather than a prediction, mirroring `IVisionSimulatedType.GroundTruthAvailable` on the sensor, and §10 already requires the two to be distinguishable. A consumer **shall not** have to infer from `Confidence`, or from the sensor's `RealityKind`, whether it is being told a measurement or a guess.

**The time base is stated, not assumed.** Every timestamp in this model is `UtcTime` (§5.12), which fixes the *representation* and says nothing about whether two Servers agree. Annex I.7 has a consumer correlating an event raised here with one raised by a commanding model, so the agreement matters and is made discoverable rather than assumed: `VisionRootType.ClockSynchronised` is `true` only where this Server's clock is disciplined to an external reference shared with the systems its events are correlated against, and `TimeSyncSource` names what that reference is.

A Server **shall not** report `ClockSynchronised` true on the strength of having set its clock once; the member asserts an ongoing discipline. Where it is `false` or absent a consumer **shall** treat cross-Server ordering as unreliable below the accuracy its own observation supports, and **shall not** attribute a detection to a motion on timing alone.

Neither member is Mandatory and no synchronisation is required. Most cells do not have a disciplined time base, and a **shall** that most conformant Servers would fail is not a requirement — it is a statement that the specification is not implementable. What this model requires instead is that a Server which cannot support the correlation Annex I.7 describes says so, so a consumer learns it by reading rather than by misattributing a frame. Where sub-frame correlation is genuinely needed, IEEE 1588 is the usual answer and `TimeSyncSource` is where a Server says it uses it.

**Where events are raised.** The well-known `Vision` object declares `EventNotifier` with the `SubscribeToEvents` bit set and is the target of a `HasNotifier` reference from the Server object, so a client subscribes at either and receives every Vision event in the Server. A Server **shall** additionally set `EventNotifier` on each `InferencePipelineType` instance that raises events and **shall** add a `HasNotifier` reference from the `Vision` object to it, so a client that wants one pipeline can subscribe to that pipeline alone. `SourceNode` **shall** be the pipeline that produced the result, or the sensor where no pipeline did.

**Severity.** `BaseEventType.Severity` is 1 to 1000. A Server **shall** raise `ObjectDetectedEventType` and a passing `InspectionCompletedEventType` at a severity of 1 to 199, because neither demands attention, and **shall** raise an `InspectionCompletedEventType` whose `Evaluation` is `NotOk` at 500 or above. Anything else would make a routine detection indistinguishable, in a generic alarm client, from a rejected part.

**These are events, not conditions.** A detection and a verdict are transient: they occur, they are reported, and nothing about them persists in a state a client would acknowledge. OPC 10000-9 `ConditionType` models the opposite — something that stays true until it stops being true — and neither of these is that. A Server that needs to raise an *alarm* about its vision system, such as a sensor that has stopped responding, uses the base OPC UA alarm types; this model defines none, because nothing about such an alarm is specific to vision.

**Semantic identifiers.** A Server **may** add a `HasDictionaryEntry` reference (OPC 10000-19) from any EventType defined here to a dictionary entry naming the same concept in ECLASS, IEC CDD or another vocabulary. This specification prescribes no dictionary and defines no identifiers of its own: no agreed identifier exists for these concepts, and minting one here would create a vocabulary with a single member and no authority behind it.

---

## AI integration (normative) {#sec-ai-integration-normative}

### The model this pipeline runs {#sec-the-model-this-pipeline-runs}

The model itself, the data it was trained on and the deployment that executes it are **not** defined here. They are defined by *OPC UA — AI Model Management and Inference*, which is domain-neutral: nothing about a model nameplate, a dataset's provenance or an inference endpoint is specific to a camera, and a specification that defined them here would oblige every other domain either to depend on a vision model or to define them again.

`InferencePipelineType.Deployment` is a **`NodeId` Property** naming that deployment. It is a NodeId and not a reference precisely so that this NodeSet takes no dependency: a Server implementing this specification alone is fully conformant, and a Server that describes its deployment some other way names that node instead.

Where the Server implements both, the deployment is a `DeploymentType` instance. Two related paths are then available: `pipeline.Deployment → DeploymentType → UsesModel → ModelType` identifies the model serving now, while `result.ModelUsed → ModelType → Digest` identifies and verifies the model that produced a retained result. The second path is authoritative for historical provenance because fallback, promotion and `FollowsRef` repointing can make the deployment's current model differ from the one that answered. Where the Server does not implement both specifications, the `ModelUsed` target's semantics are out of scope and §12.6's provenance guarantee is unavailable, which is why the **VIS-Inference-\*** facets require the AI model (§11.2).

#### A model is a business artefact, not device firmware {#sec-a-model-is-a-business-artefact-not-device-firmware}

This assumption is why the model is separated from the sensor that uses it, and it is what makes the separation of specifications the right shape rather than merely a tidy one.

An AI model is **supplied and governed by the end-user**, not baked into the device by its manufacturer. The same physical camera runs different models over its life; the same model runs on many cameras and on off-server hardware the camera vendor never sees.

Two consequences are normative here, and the rest belong to the specification that owns the model:

1. **Lifecycles are independent.** A Server **shall not** require a device firmware change to change the deployed model, and **shall not** tie a model's version to any device or firmware version. Replacing a model **shall** be observable as a change to the deployment, not as a change to the sensor.
2. **Authority to change a model is separate from authority to operate the device.** A client authorized to browse a sensor, view its stream or trigger inference is **not** thereby authorized to promote or replace a model — see §12.5.

### On-server and off-server inference {#sec-on-server-and-off-server-inference}

The deployment's inference location is mandatory in the model that defines it and takes one of `OnServer`, `EdgeOffServer`, `Cloud`, `InSimulator`. It is restated here because it is what a vision client reasons about when it decides whether to trust a latency budget.

**This property changes where computation happens and therefore the trust boundary. It changes nothing else.** A Server **shall** publish results through the same types, with the same members and the same meaning, regardless of its value. When inference is off-server the Server publishes results it did not compute; a client that does not care where inference ran does not have to look.

For off-server deployments, `EndpointUri` names the inference service and `LatencyBudget` states the latency it is expected to meet, so a client can detect regression rather than merely observing it.

#### Usage model {#sec-usage-model}

The four values differ in who runs the model, what the Server must reach, and what fails when the link fails. In every case the **client sees the same exchange** — that is the point of the property.

| Value | Where the model runs | What the Server must reach | Typical reason to choose it |
|---|---|---|---|
| `OnServer` | In the Server's own process or device | nothing | Lowest latency, no external dependency; bounded by the device's own compute |
| `EdgeOffServer` | A separate box on the same network, e.g. an edge GPU | `EndpointUri` on the local network | Model too large for the camera; keeps data on-premises |
| `Cloud` | A hosted service | `EndpointUri` across the internet | Elastic capacity, centrally managed models; adds a WAN dependency |
| `InSimulator` | Inside the scene simulator | the simulator | Synthetic data generation and validation before deployment (§10) |

**The client's exchange is identical in all four cases.** It calls the pipeline, reads the result, and optionally follows the provenance chain — none of which mentions where inference ran:

```{figure}
id: fig-vis-exchange
caption: The client exchange, identical at every inference location
source: figures/Vision-Fig4-Exchange.png
```

**`OnServer`** — the Server computes the result itself, so the only failure mode is its own:

```{figure}
id: fig-vis-onserver
caption: Inference on the Server
source: figures/Vision-Fig5-OnServer.png
```

**`EdgeOffServer` and `Cloud`** — the Server is a broker. It publishes a result it did not compute, and the extra failure modes are reachability and latency:

```{figure}
id: fig-vis-offserver
caption: Inference off the Server, and its failure modes
source: figures/Vision-Fig6-OffServer.png
```

**`InSimulator`** — the sensor is simulated, so results may be simulator **ground truth** rather than predictions. A client **shall** consult `GroundTruthAvailable` before treating them as model output (§10):

```{figure}
id: fig-vis-simulator
caption: Inference in the simulator
source: figures/Vision-Fig7-Simulator.png
```

A Server **shall not** vary the result types, member meanings or StatusCodes by `InferenceLocation`; the only observable differences are the failure modes above and the presence of `EndpointUri` and `LatencyBudget`.

### `InferencePipelineType` {#sec-inferencepipelinetype}

Binds a `Sensor` to a `Deployment`, exposes `State` and `Continuous`, optionally holds a `Results` folder and `Feedback` object, carries an optional `LearningJob`, and offers `RunInference`, `StartContinuous` and `Stop`. `PipelineId` is Mandatory and identifies the pipeline uniquely within the Server, in the same way `SensorId` identifies a sensor; it is what a `VisionResultType` names in its `Pipeline` Property (§5.11).

`MaxResultAge` and `MaxRetainedResults` are Optional in the type model because a pipeline that only raises events has no `Results` instance and no result nodes to retain. Where `Results` is instantiated under an inference facet, both limits are required and §7.1.1 governs them.

`LearningJob` is an Optional `NodeId` naming the job that consumes the `GroundTruthLabel` corrections submitted through this pipeline's `Feedback` object, or null where the Server retains none. It is a `NodeId` and not a reference for the same reason `Deployment` is: this specification takes no dependency on the model that defines the job. §9.5.1 requires it to be non-null wherever such a correction is retained — it is how a client establishes that its label reached a learning loop at all, rather than being accepted and discarded.

A Server whose inference is entirely off-server and continuously running may implement none of the three Methods; the pipeline still describes the binding and publishes the results.

*Table - InferencePipelineType Definition* {#tbl-inferencepipelinetype-definition defines=InferencePipelineType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:InferencePipelineType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:PipelineId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Sensor | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Deployment | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:State | 1:VisionEndpointStateEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Continuous | 0:Boolean | 0:PropertyType | O |
| 0:HasComponent | Object | 1:Results |  | 0:FolderType | O |
| 0:HasComponent | Object | 1:Feedback |  | 1:VisionFeedbackType | O |
| 0:HasComponent | Method | 1:RunInference |  |  | O |
| 0:HasComponent | Method | 1:StartContinuous |  |  | O |
| 0:HasComponent | Method | 1:Stop |  |  | O |
| 0:HasProperty | Variable | 1:LearningJob | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:MaxResultAge | 0:Duration | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:MaxRetainedResults | 0:UInt32 | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

#### RunInference {#sec-inferencepipelinetype-runinference type=InferencePipelineType method=RunInference}

Run inference once, on the current or a specified frame, and return the identifier of the result that was produced.

**Signature**

```text
RunInference (
  [in]  0:UtcTime Timestamp,
  [out] 0:String  ResultId);
```

*Table - RunInference Method Arguments* {#tbl-runinference-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Timestamp | Frame nearest this time, or null for the newest. |
| ResultId | Identifier of the produced result. |

#### StartContinuous {#sec-inferencepipelinetype-startcontinuous type=InferencePipelineType method=StartContinuous}

Begin running inference on every acquired frame.

**Signature**

```text
StartContinuous ();
```

*Table - StartContinuous Method Arguments* {#tbl-startcontinuous-method-arguments}

| **Argument** | **Description** |
| --- | --- |

#### Stop {#sec-inferencepipelinetype-stop type=InferencePipelineType method=Stop}

Stop continuous inference.

**Signature**

```text
Stop ();
```

*Table - Stop Method Arguments* {#tbl-stop-method-arguments}

| **Argument** | **Description** |
| --- | --- |

### Inference Method definitions (normative) {#sec-inference-method-definitions-normative}

**`RunInference(Timestamp) → (ResultId)`** — runs inference once on the frame nearest `Timestamp`, or on the newest frame when `Timestamp` is unspecified per §5.12, and returns the identifier of the result produced. A Server that implements `RunInference` **shall** instantiate `Results`, `MaxResultAge` and `MaxRetainedResults`; the result **shall** exist and be retrievable under `Results` before the Method returns `Good`. Its subsequent lifetime follows §7.1.1. Clause 11 makes this a condition of the inference facets.

| StatusCode | Condition |
|---|---|
| `Bad_InvalidState` | `State` is `Inactive` or `Faulted` |
| `Bad_NotFound` | no frame exists near `Timestamp` within retention |
| `Bad_ResourceUnavailable` | an off-server deployment is unreachable |
| `Bad_Timeout` | inference exceeded the deployment's `LatencyBudget` and was abandoned |
| `Bad_UserAccessDenied` | the caller is not authorized to trigger inference |

**`StartContinuous()`** and **`Stop()`** — start and stop per-frame inference. Both are **idempotent**: calling `StartContinuous` while `Continuous` is already true, or `Stop` while it is already false, **shall** return `Good` and change nothing.

| StatusCode | Condition |
|---|---|
| `Bad_InvalidState` | `State` is `Inactive` or `Faulted` (`StartContinuous` only) |
| `Bad_ResourceUnavailable` | an off-server deployment is unreachable (`StartContinuous` only) |
| `Bad_UserAccessDenied` | the caller is not authorized |

On success `StartContinuous` **shall** set `Continuous` to true and drive `State` toward `Active`; `Stop` **shall** set `Continuous` to false and drive `State` toward `Ready` (§6.6).

---

## Feedback and the learning loop (normative) {#sec-feedback-and-the-learning-loop-normative}

### Why this clause exists {#sec-why-this-clause-exists}

Clauses 6 to 8 describe one direction only: the vision system observes, and a consumer reads what it concluded. That is sufficient for a system that is always right, and no vision system is. Three things routinely need to travel the *other* way, from the consumer back into the vision system, and none of them has a home in any existing OPC UA specification:

- An operator watching a live stream needs to **see what the system saw** — the boxes it drew, on the image it drew them on — in order to judge whether to trust it.
- A downstream station that measured the part independently, or a quality engineer who overrode a verdict, holds information the vision system does not: **what actually turned out to be true**.
- A model that is wrong about a new part variant can only be fixed by **being told what the right answer was**, in a form that can become training data.

Without a defined path for these, each is rebuilt per site: an HMI writes overlay boxes into a vendor-specific tag, corrections end up in a spreadsheet, and the labels needed to retrain the model are re-created by hand from images someone exported. This clause gives all three one surface, and §12.7 states what a Server may then believe.

**"Return path"** means exactly this reverse direction: `VisionFeedbackType` is the object through which a *client* writes information back into the vision system, in contrast with the rest of the model, through which the *Server* publishes information outward. It is a return path in the control-loop sense — an output of the process is fed back to influence its future behaviour — not a network path or a message route.

`VisionFeedbackType` is a **concrete** ObjectType. A Server instantiates it directly as the `Feedback` object of an `InferencePipelineType`; it is not abstract and is not subtyped to obtain a feedback surface.

```{figure}
id: fig-vis-returnpath
caption: The return path
source: figures/Vision-Fig8-ReturnPath.png
```

### The four purposes {#sec-the-four-purposes}

`VisionFeedbackType` serves four purposes with one surface. `VisionFeedbackPurposeEnum` states which applies:

- **`Overlay`** — submitted geometry is drawn onto the outgoing stream, governed by `OverlayEnabled`, `OverlayStyle` and `OverlayTtl`. Used during commissioning and for operator confidence; it changes what a human sees and nothing else.
- **`Reconciliation`** — a downstream verdict is recorded against a result, so what the line concluded can be compared with what the vision system reported. It changes the record, not the model.
- **`GroundTruthLabel`** — a correction is retained as labelled training data. It is the only one of the four that can change what the system decides in future, which is why §12.7 gates it.
- **`Trigger`** — the submitted payload is an acquisition or processing request rather than a report: a client that already knows where to look tells the sensor to look there. It changes neither the record nor the model, and a Server that does not accept externally triggered acquisition returns `Bad_NotSupported`.

The Methods are `SubmitDetections`, `SubmitInspectionResult`, `SubmitCorrection` and `SubmitImageReference`.

### Feedback images {#sec-feedback-images}

Feedback images follow exactly the discipline of §6.4. `SubmitImageReference` — passing a `VisionImageReferenceDataType` — is the **default** path. `SubmitDetections` and `SubmitCorrection` each additionally accept an optional inline `ByteString`, which a Server **shall** accept only within `MaxInlineFeedbackImageSize`, itself bounded as in §6.4 rule 2. An oversized payload **shall** be rejected with **`Bad_EncodingLimitsExceeded`**, and the client **shall** retry by reference.

Any `Uri` in a submitted `VisionImageReferenceDataType` is a location the Server will dereference, so §12.3 states the validation it **shall** apply first.

### Closing the loop {#sec-closing-the-loop}

`LearningJobType` is where corrections accumulate and become a new model version. Its state model, its Methods and its StatusCodes are defined by *OPC UA — AI Model Management and Inference* and are not restated here (§9.5.1).

```{figure}
id: fig-vis-loop
caption: Closing the learning loop
source: figures/Vision-Fig9-Loop.png
```

A Server **may** implement only the capture stages and leave training to an external MLOps system; the state machine is the same either way, and `TriggerTraining` simply reports whether the request was queued.

A **negative example** — a frame labelled as containing no instances of any class, submitted as `SubmitDetections` with `SceneIsEmpty` true or `SubmitCorrection` with `RetractAll` true and `Purpose = GroundTruthLabel` — **is** a valid dataset sample. A Server **shall** account for it in `SamplesCollected` exactly as it accounts for a sample carrying geometry, and **shall not** discard it as an empty submission. Negative examples are what teach a detector that a frame may legitimately contain nothing, and a dataset that admits only positive ones is biased by construction.

`PromoteModel` changes what the system decides. A Server **shall** require an authorization for it that is distinct from, and not implied by, the authorization for any `VisionFeedbackType` Method or for `StartCollection`, `StopCollection` and `TriggerTraining` (§12.5). Clause 11 makes this a condition of *VIS-Learning*.

### Feedback and learning Method definitions (normative) {#sec-feedback-and-learning-method-definitions-normative}

Every Method in this clause is a **write** and **shall** be authorized independently (§12.5). None of them changes a published result: a correction is recorded alongside the original, never in place of it, so the audit trail is preserved.

**`SubmitDetections(Purpose, Detections, FrameReference, InlineImage, SceneIsEmpty)`** and **`SubmitCorrection(ResultId, Purpose, CorrectedDetections, CorrectedCharacteristics, Reason, InlineImage, RetractAll)`** — `InlineImage` is optional and **shall** be accepted only within `MaxInlineFeedbackImageSize`, itself bounded as in §6.4 rule 2.

`SceneIsEmpty` and `RetractAll` exist because an empty observation is a real one. "I examined this frame and there is nothing in it" is the terminating condition of a bin-picking task and a legitimate — indeed necessary — training label, since a detector trained only on frames that contain objects learns that every frame contains objects. A false positive, likewise, is corrected by asserting that nothing replaces it, and it is the error class an operator is most able to label with confidence. Neither statement can be made by submitting an array, because both *are* the empty array.

The rules are therefore:

- `SubmitDetections` **shall** accept an empty `Detections` when `SceneIsEmpty` is true, and **shall** reject an empty `Detections` when it is false. A Server **shall** treat the pair as the assertion that the frame was examined and found to contain nothing, and **shall not** treat it as a failed acquisition. Where `SceneIsEmpty` is true and `Detections` is non-empty the call is inconsistent and **shall** be rejected.
- For `SubmitCorrection`, **at most one** of `CorrectedDetections` and `CorrectedCharacteristics` **shall** be non-empty, and it **shall** match the kind of the referenced result. Both may be empty only when `RetractAll` is true, which asserts that the referenced result should contain nothing at all. Where `RetractAll` is true and either array is non-empty the call is inconsistent and **shall** be rejected.

An accidentally empty call is still refused, because the flag is what distinguishes a deliberate empty observation from a lost payload. A correction from three detections to one has always been expressible by submitting the one; these rules make the correction from one to zero expressible too, which it was not.

**`SubmitInspectionResult(ResultId, Evaluation, Characteristics)`** — records a downstream verdict against an existing result for reconciliation.

**`SubmitImageReference(Purpose, Image, ResultId)`** — the default feedback-image path. `ResultId` may be empty when the image is not tied to a result.

| StatusCode | Condition | Applies to |
|---|---|---|
| `Bad_NotFound` | `ResultId` is non-empty and does not designate a currently retained result of **this pipeline**, including an identifier whose node was evicted | all four |
| `Bad_InvalidArgument` | `Detections` empty and `SceneIsEmpty` false; or `Detections` non-empty and `SceneIsEmpty` true; or `SubmitCorrection` supplies both corrected arrays; or supplies neither with `RetractAll` false; or supplies either with `RetractAll` true | `SubmitDetections`, `SubmitCorrection` |
| `Bad_TypeMismatch` | the corrected array kind does not match the referenced result | `SubmitCorrection` |
| `Bad_EncodingLimitsExceeded` | `InlineImage` exceeds `MaxInlineFeedbackImageSize` | `SubmitDetections`, `SubmitCorrection` |
| `Bad_NotSupported` | `Purpose` is `Overlay` but `OverlayEnabled` is false | `SubmitDetections`, `SubmitImageReference` |
| `Bad_UserAccessDenied` | the caller is not authorized to write feedback | all four |

As in §6.5, the selector is scoped to the object carrying the Method: a Server **shall** return `Bad_NotFound` when `ResultId` designates a result of a different `InferencePipelineType`, and **shall not** disclose that it exists elsewhere. Without this, a client authorized on one pipeline's feedback surface could attach corrections and ground-truth labels to another pipeline's results.

Any `Uri` inside a submitted `VisionImageReferenceDataType` is a client-supplied location the Server will dereference; §12.3 states the validation a Server **shall** apply before doing so.

A Server that accepts a correction with `Purpose = GroundTruthLabel` **shall** either retain it for the associated `LearningJobType` or return `Bad_NotSupported`; it **shall not** return `Good` and discard it, because a client has no other way to learn that its label was dropped. Retention is not acceptance as truth — §12.7 states what a Server **shall** record alongside the sample and what **shall** gate its admission to a training run.

#### The learning Methods are not defined here {#sec-the-learning-methods-are-not-defined-here}

`StartCollection`, `StopCollection`, `TriggerTraining` and `PromoteModel` belong to `LearningJobType`, which *OPC UA — AI Model Management and Inference* defines together with its state model, its StatusCodes and the requirement that `PromoteModel` carry an authorization distinct from every other Method on the job. This specification does not restate them: two documents stating the same transition table is two places for it to be wrong, and the one that is wrong is discovered by an implementer, not by a validator.

What *is* stated here is the part that is specific to vision — the join between a correction submitted through `VisionFeedbackType` and the job that consumes it:

1. A Server that retains a `GroundTruthLabel` correction **shall** populate `InferencePipelineType.LearningJob` with the job that will consume it, so a client can determine whether its label reached a learning loop at all. A Server that retains nothing leaves it null, which is the honest answer and a different one from an unpopulated Optional member on a Server that does retain.
2. A Server **shall not** report a job as `Collecting` on the strength of corrections it discarded. Where a correction was accepted with `Good` and retained, `SamplesCollected` **shall** account for it; the two statements are the same fact and a client that trusts one is entitled to the other.
3. Promotion changes what every downstream verdict means. §12.5 requires its authorization to be distinct from the authorization for any `VisionFeedbackType` Method, and that requirement is stated in both documents deliberately — it is the one rule where a reader of either specification alone would otherwise reach the wrong conclusion.

---

## Simulation parity (normative) {#sec-simulation-parity-normative}

A simulated sensor **shall** expose the same members, with the same units and meanings, as a physical one (§4.3). Beyond that:

- `IVisionSimulatedType.PrimPath` **shall** be an absolute, composed-stage prim path, using the same identity contract as the OpenUSD specifications.
- Where the Server claims *VIS-Interop-Scene*, `PrimPath` **shall** resolve to a `UsdGeomCameraType` instance and the sensor **shall** carry a `HasScenePrim` reference to it. Annex C states the full requirement set for that facet and is the single normative source for it; a Server that implements both specifications without claiming the facet uses `PrimPath` as an opaque descriptor.
- Where `GroundTruthAvailable` is true, results produced from that sensor are simulator ground truth rather than inference output. A Server **shall** make this distinguishable — by pipeline, by `ModelUsed` and `ModelVersionUsed` being absent, or by an explicit convention — so that ground truth is never mistaken for a prediction.
- `RandomizationSeed` **should** be published whenever domain randomization is active, so a dataset can be reproduced.

---

## Profiles and conformance units {#sec-profiles-and-conformance-units}

```{clause}
kind: profiles
```

### Declaring conformance {#sec-declaring-conformance}

*VIS-Base* is **mandatory**: a Server **shall not** claim conformance to this specification unless it satisfies *VIS-Base*. Every other facet is optional and additive. This is what makes the §6.2 guarantee unconditional — *VIS-Base* requires *VIS-Media-Rtsp* and *VIS-Media-Jpeg*, so a client may assume RTSP and JPEG on any conformant Server without negotiation.

A claim **shall** be discoverable. A Server **shall** add the URI of each facet it implements to `Server.ServerCapabilities.ServerProfileArray`, and **shall not** add the URI of a facet whose members and rules it does not satisfy. Facet URIs are formed by appending the facet identifier to `http://opcfoundation.org/UA/Vision/Facet/` — for example `http://opcfoundation.org/UA/Vision/Facet/VIS-Media-Inline`. A client determines what a Server supports by reading `ServerProfileArray`; it **should** additionally verify the members it depends on, because the address space, not the claim, is authoritative.

Where a facet's row names members, a Server claiming it **shall** instantiate every named member on every instance of the stated type — an Optional ModellingRule in the model becomes mandatory under the facet that names it. Where a row names a clause, every **shall** in that clause applies.

The NodeSet assigns every Node to one of four conformance units: `Vision` for the ObjectTypes and their members, `Vision DataTypes` for the structures and enumerations, `Vision ReferenceTypes` for the references, and `Vision Events` for the EventTypes of §7.5. The facets below are expressed over those Nodes, so a Server claiming a facet implements the units the facet's members belong to.

### Facets {#sec-facets}

| Facet | Requires |
|---|---|
| **VIS-Base** *(mandatory)* | The well-known `Vision` object per §4.2, `Sensors`, and at least one sensor with `SensorId`, `RealityKind`, `Modality` and `Media`. Requires *VIS-Media-Rtsp* and *VIS-Media-Jpeg*. |
| **VIS-Sensor-Params** | `ImageSensorType` with `Width`, `Height`, `PixelFormat` |
| **VIS-Optics** | `OpticsType` and/or `IlluminationType` |
| **VIS-Media-Rtsp** | At least one `StreamEndpointType` with `StreamProtocol = Rtsp`, `ProtocolVersion` and `SecureTransport`; `GetStreamEndpoint`, `ReleaseStreamEndpoint` (§6.5), and the §12.2 credential conditions |
| **VIS-Media-Jpeg** | At least one `ClipEndpointType` with `ClipFormat = Jpeg` and `SecureTransport`; `GetClip` (§6.5) |
| **VIS-Media-Inline** | On the same `ClipEndpointType` instance: all four of `LatestClip`, `LatestClipMetadata`, `MaxInlineClipSize`, `InlineDeliveryEnabled`, and all five §6.4 rules. A Server **shall not** instantiate a proper subset of the four. |
| **VIS-Media-DataChannel** *(depends on a draft)* | On at least one `MediaEndpointType` instance: `DataChannelSource` non-null and `DataChannelContentType` non-empty, plus all of §6.7 and the §6.3 no-implicit-selection rule. Requires the *Data Channel Media Server Facet* of *OPC UA — Data Channels*, which is a **working draft** (§2) — this facet is therefore provisional, is **not** required by *VIS-Base*, and a Server claiming it **shall** still satisfy *VIS-Media-Rtsp* and *VIS-Media-Jpeg*. |
| **VIS-Endpoint-Config** | `ConfigureStreamEndpoint`, `SelectEndpoint` (§6.5) |
| **VIS-Calibration** | `CoordinateFrameType` plus `IntrinsicCalibrationType` and/or `ExtrinsicCalibrationType`, with the §5.11 reference constraints and the §5.12 frame-precedence rule. A Server claiming this facet **shall** instantiate `Vision/Frames`, and it **shall** contain every `CoordinateFrameType` instance reachable through `MountedOn`, `SourceFrame` or `TargetFrame`. Frames **may** additionally appear elsewhere; `Frames` is the one place a client is entitled to find all of them. |
| **VIS-Result-Inspection** | `InspectionResultType` with `Evaluation` and `Characteristics`, and the §7.2 uncertainty rule including its uniform-reporting requirement |
| **VIS-Result-Detection** | `DetectionResultType` with `Detections`, the §5.12 pose conventions, and the §7.3 `FrameId` rule |
| **VIS-Events** | The EventTypes of §7.5 and every rule in that clause. A Server claiming it **shall** raise `ObjectDetectedEventType` for every detection it publishes and `InspectionCompletedEventType` for every inspection it concludes — a facet that permits a Server to raise events for some results and not others tells a client nothing, because silence would then be ambiguous between "nothing happened" and "this one was not reported". Requires *VIS-Result-Detection* for the first and *VIS-Result-Inspection* for the second, whichever the Server publishes; a Server that publishes only one kind of result claims this facet on the strength of that kind alone. |
| **VIS-Feedback** | `VisionFeedbackType` with at least `SubmitImageReference`, the §9.3 and §9.5 rules, the §12.3 inbound-URI validation, and the §12.7 feedback-integrity rules. A Server claiming this facet **shall** accept at least `Trigger` and `Overlay` on `SubmitImageReference`, and on `SubmitDetections` where that Method is instantiated. Accepting `Reconciliation` needs no further facet. Accepting `GroundTruthLabel` on `SubmitCorrection` requires *VIS-Learning* in addition. |
| **VIS-Inference-OnServer** | `InferencePipelineType` with a deployment whose `InferenceLocation` is `OnServer`, and the `UsesModel` constraint. Every result produced through that deployment populates `ModelUsed` with the `ModelType` that actually answered (§7.1). Where `Results` is instantiated, both `MaxResultAge` and `MaxRetainedResults`, at least one non-zero, and every rule of §7.1.1; `RunInference` requires `Results` (§8.4). `ModelType.Digest` and `DigestAlgorithm` per §12.6 |
| **VIS-Inference-OffServer** | As above with any other `InferenceLocation`, including the same conditional retention requirements and `ModelUsed` on every result, plus `EndpointUri` naming an authenticated, confidential scheme (§12.6) |
| **VIS-Simulation** | `IVisionSimulatedType` on every sensor whose `RealityKind` is `Simulated` or `Hybrid` (§4.3, §10). **Required** of any Server that reports either value. |
| **VIS-Learning** | `VisionFeedbackType.SubmitCorrection` accepting `GroundTruthLabel`, the §9.5.1 join rules, and the **AI-Learning** facet of *OPC UA — AI Model Management and Inference*, which carries `LearningJobType`, its state model and the **distinct `PromoteModel` authorization** this specification also requires in §12.5 |
| **VIS-Interop-Scene** | The numbered requirements of Annex C, which are normative for a Server claiming this facet |
| **VIS-Interop-40100** | The numbered requirements of Annex D, which are normative for a Server claiming this facet |
| **VIS-Interop-RobotIntent** | The numbered requirements of Annex I, which are normative for a Server claiming this facet |

Facets are independent and additive except where a row states a dependency. Three dependencies exist: *VIS-Base* requires *VIS-Media-Rtsp* and *VIS-Media-Jpeg*; *VIS-Simulation* is required — not merely permitted — of any Server that reports `RealityKind` as `Simulated` or `Hybrid`; and a Server accepting `GroundTruthLabel` under *VIS-Feedback* requires *VIS-Learning*, which is where §9.4 says such a correction goes. A facet is claimed only when every member and rule it lists is satisfied.

Two rows constrain what a facet claim is worth rather than which members exist. *VIS-Calibration* names `Vision/Frames` because a client needs one deterministic entry point: `Frames` carries an Optional ModellingRule on `VisionRootType`, so without this row a Server could satisfy the facet with frames reachable only by walking `MountedOn` from every sensor, and a client browsing `Frames` would conclude the Server had none while every result named a frame it never found. *VIS-Feedback* names a minimum accepted `Purpose` set for the same reason: without one, a Server accepting only `Trigger` would conform, and the claim would say almost nothing about what a client can send.

**Three facets require a second specification.** *VIS-Inference-OnServer*, *VIS-Inference-OffServer* and *VIS-Learning* each name a type defined by *OPC UA — AI Model Management and Inference* — `DeploymentType`, `ModelType`, `LearningJobType` — so a Server claiming any of them **shall** also implement that specification's **AI-Base** facet, and **AI-Learning** for *VIS-Learning*. **AI-Events** is independent: the Vision inference facets do not require promotion events, and a Server claims that AI facet separately when it exposes them. This is the only place either specification depends on the other, and it is stated as a facet precondition rather than a `RequiredModel` deliberately: a Server that publishes cameras, calibration and results and never mentions a model is fully conformant to **VIS-Base** with this NodeSet alone.

*VIS-Media-DataChannel* is the only facet defined against a document that is not a released specification. It is marked as such in its row and in §6.7, and it is deliberately structured so that its withdrawal would cost nothing: the two members it uses become permanently null, the enumeration literal goes unused, and every other facet is unaffected.

---

## Security {#sec-security}

### Media credentials are not OPC UA credentials {#sec-media-credentials-are-not-opc-ua-credentials}

A media endpoint has its own authentication, stated by `MediaEndpointType.Authentication`. Authorization to browse a sensor does **not** imply authorization to view its stream. A Server **shall** authorize `GetStreamEndpoint` and `GetClip` independently of read access to the sensor's descriptive members.

`Authentication = None` is appropriate only on an isolated network and **should not** be used otherwise.

### Leases expire, and credentials need a protected channel {#sec-leases-expire-and-credentials-need-a-protected-channel}

A `Uri` returned by `GetStreamEndpoint` or `GetClip` **may** embed a credential. It is therefore returned by a Method — auditable and addressed to one caller — and never published as a browsable Variable. A Server **shall** enforce `ExpiresAt` and **shall** bound the number of concurrent leases per session.

Delivering a credential to one caller is not sufficient if the channel carrying it is readable. A Server **shall not** return a `Session.Uri` or `Image.Uri` that embeds a credential unless **both** of the following hold, and **shall** return `Bad_SecurityModeInsufficient` otherwise:

1. the OPC UA SecureChannel carrying the Method response has `MessageSecurityMode` of `SignAndEncrypt`; and
2. the selected endpoint's `MediaEndpointType.SecureTransport` is `true`.

`SecureTransport` is Mandatory on every `MediaEndpointType` for this reason: it is the member on which rule 2 is evaluated, and a client **shall** treat `false` as meaning the media transport itself offers no confidentiality, whatever the endpoint's `Authentication` states. A Server that publishes only `Rtsp` endpoints therefore cannot issue embedded credentials, since RTSP/1.0 has no transport security; such a Server **shall** rely on the endpoint's own out-of-band authentication instead, and **should** additionally offer an `Rtsps` or `Srt` endpoint so that credentialed access is available at all.

A credential-bearing URI **shall not** be written to any log, trace or audit record. The §12.5 audit record **shall** reference the `EndpointId` and the lease identifier instead. This is a distinct requirement because URLs carrying credentials are routinely captured by media-server access logs, proxies and process listings, where they outlive the lease.

**A data channel needs no media credential at all.** This is the security argument for §6.7 and is worth stating plainly: a data channel is carried on the SecureChannel the client has already authenticated, so it inherits that channel's authentication, signing and encryption. There is no second credential to mint, embed in a URI, transmit or leak, and the whole of the preceding requirement is simply inapplicable. Where a Server offers both, the data-channel path is therefore the *more* secure one, and §12.3's client-side allowlist obligation does not arise either, because there is no URI to resolve.

Two conditions apply to it:

1. A Server **shall** set `SecureTransport` to `true` on a data-channel endpoint only where the SecureChannel carrying the channel has `MessageSecurityMode` of `SignAndEncrypt`. On a `Sign`-only or `None` channel the media is not confidential, whatever the transport is.
2. A Server **shall not** carry media on a data channel opened over a SecureChannel whose SecurityMode is `None`, and **shall not** rely on `DataChannelCapabilities.AllowInsecureDataChannels` for media. That flag exists in the Data Channels draft for cases where payload confidentiality is not required; imagery is not such a case, and on such a channel a frame carries neither signature nor encryption, so both the payload and its sequence numbers are forgeable.

### URIs are untrusted input — in both directions {#sec-uris-are-untrusted-input-in-both-directions}

Two directions have to be considered separately, and only the first was historically obvious.

**Server-published URIs, consumed by a client.** `EndpointUri`, `ArtifactUri`, `ProvenanceUri` and `ExplanationUri` are published by the Server and could direct a client at an arbitrary location — an SSRF-class risk for the client. A client **shall** apply a scheme and host allowlist and **shall** impose resource limits when resolving them. Where a `Digest` is present, a client **shall** verify the fetched bytes against it per §12.6 and **shall** refuse a mismatch. This mirrors the resolver-safety treatment in *OPC UA — OpenUSD Bindings* §9.

**Client-supplied URIs, consumed by the Server.** `VisionImageReferenceDataType.Uri` is *also* a client input: it arrives through `SubmitImageReference` — the default feedback-image path of §9.3, required by *VIS-Feedback* — and through the `FrameReference` argument of `SubmitDetections`. Because §9.4 requires submitted imagery to become retained training data, the Server or its backend dereferences a location chosen by the caller. That makes the Server the SSRF target.

A Server **shall** treat every `Uri` received from a client as untrusted, and **shall**:

1. restrict accepted schemes to an explicit allowlist — `https`, and the Server's own clip endpoints — and reject all others, including `file`, `ftp`, `gopher` and `data`;
2. reject destinations that resolve to loopback, link-local (`169.254.0.0/16`, `fe80::/10`), unique-local (`fc00::/7`) or otherwise non-routable addresses, unless an operator has explicitly configured that destination;
3. re-validate the destination **after** DNS resolution and **after every redirect**, so that a name resolving to an internal address, or a redirect to one, is rejected rather than followed;
4. bound the response size, the connection and total time, and the number of redirects; and
5. where the submitted `Digest` is present, verify it per §12.6 **before** the bytes are admitted to any dataset.

A Server **shall not** disclose connection failure detail that would let a caller distinguish a filtered destination from an unreachable one, since that turns the feedback surface into an internal port scanner.

### Inline payloads are a denial-of-service surface {#sec-inline-payloads-are-a-denial-of-service-surface}

Inline delivery amplifies payload size by orders of magnitude relative to ordinary Variables. A Server **shall** enforce `MaxInlineClipSize` and `MaxInlineFeedbackImageSize` as bounded in §6.4 rule 2, **shall** revise the requested `SamplingInterval` of a MonitoredItem on an image-bearing Variable upward to a rate it can sustain, and **shall** bound that item's `QueueSize` — an image-bearing queue of any depth multiplies memory by the image size, so a Server **should** revise the queue size to 1 unless a larger value is explicitly configured. Both are per-MonitoredItem revised values, which is the lever a Server actually controls; the Subscription's publishing interval is client-set and **shall not** be relied on for this bound. These are normative bounds, not tuning advice.

### Feedback and promotion are writes {#sec-feedback-and-promotion-are-writes}

Every `VisionFeedbackType` Method mutates state: overlays change what operators see, reconciliation changes the record, and corrections change what the next model learns. A Server **shall** require explicit authorization for each.

`LearningJobType.PromoteModel` changes what the system *decides*, on every deployment fed by the job. A Server **shall** require an authorization for `PromoteModel` that is **distinct from, and not implied by**, the authorization required for any `VisionFeedbackType` Method or for `StartCollection`, `StopCollection` or `TriggerTraining`. A principal able to submit corrections **shall not** thereby be able to promote a model. This is the requirement §8.1.1 consequence 2 refers to, and clause 11 makes it a condition of *VIS-Learning* so that it is testable.

A Server **shall** retain an audit record of every correction and promotion, including the authenticated caller identity and the timestamp, and **shall not** include a credential-bearing URI in it (§12.2). Where the deployment falls under a high-risk regulatory regime, this record and the §7.1 trust members are what make the decision chain reconstructible.

Result-node eviction under §7.1.1 **shall not** be treated as authorization to delete this audit record or evidence retained by an external application. Those records have independent retention obligations defined by their application policies. Conversely, an audit or evidence record that preserves a `ResultId` does not keep the Vision result node alive and **shall not** cause that identifier to be reused or rebound.

### Off-server inference crosses a trust boundary {#sec-off-server-inference-crosses-a-trust-boundary}

When `InferenceLocation` is not `OnServer`, results were computed by a system the OPC UA client cannot inspect. A Server **shall** establish an authenticated, integrity-protected channel to that service. `DeploymentType.EndpointUri` **shall** name a scheme that provides authentication and confidentiality — for example `https` or `grpcs`, not their plaintext counterparts — and a Server **shall not** publish a plaintext scheme for a deployment it claims conformance for.

**Artefact integrity.** A model artefact fetched out of band is bytes this Server did not serve, so the only thing that ties it to the answer is the digest. *OPC UA — AI Model Management and Inference* makes the model's `Digest` and `DigestAlgorithm` Mandatory, bars weak and truncated hash functions, and requires a client to refuse an algorithm it does not recognise rather than skip verification and report success. This specification does not restate those rules — it makes them a **condition of the inference facets** (clause 11): a Server claiming **VIS-Inference-OffServer** without a verifiable digest has published an unauditable verdict, which is the whole failure this clause exists to prevent.

Digest verification is the terminus of the provenance chain. `VisionResultType.ModelUsed` keeps the historical chain intact while the result is retained by recording which `ModelType` answered at inference time. A client auditing a retained result **shall** walk `result.ModelUsed → ModelType → Digest`, not the deployment's current `UsesModel` reference, which describes what is serving now. If evidence must outlive `MaxResultAge` or `MaxRetainedResults`, the application **shall** preserve it under its applicable evidence-retention policy before the Vision result is evicted; this specification does not silently extend either lifetime or prescribe that external policy.

### Feedback is untrusted training data {#sec-feedback-is-untrusted-training-data}

§12.5 governs *permission to call* a feedback Method. This clause governs what may then be *believed*, which is a separate question: §9.4 routes a submitted `GroundTruthLabel` into `DatasetType`, then into a training run, a `CandidateModel` and — after promotion — into every verdict the line produces. A single misused credential on the feedback surface is therefore a path to influencing safety-relevant decisions, and authorization alone does not bound it.

A Server **shall**:

1. record the authenticated caller identity with every retained sample whose `Purpose` is `GroundTruthLabel`, and make it available to the `LearningJobType` that consumes the dataset — an unattributable label set cannot be reviewed or retracted;
2. distinguish, within `DatasetType`, samples originating from client feedback from samples originating from capture, so that a reviewer can weigh them differently; and
3. require a distinct authorization or an explicit approval step before client-submitted labels are admitted to a training run, mirroring the `PromoteModel` gate of §12.5.

A Server **should** bound the proportion of any dataset contributed by a single principal, and **should** support retracting all samples attributed to one identity.

**An empty label is a label.** `SceneIsEmpty` and `RetractAll` (§9.5) let a client assert that a frame contains nothing and that a published detection was a false positive, and both are retained as training data. Neither is a lower-risk submission than one carrying geometry: a stream of "nothing here" labels against frames that do contain parts teaches a detector to miss them, and a stream of retractions teaches it to suppress true positives — a class of attack that degrades recall while every individual call looks well-formed and stays within any rate limit on payload size. The rules above apply to these samples unchanged, and a Server **should** treat an anomalous rate of empty or retracting submissions from one principal as it treats any other dataset-poisoning signal.

**Overlays are also untrusted.** Geometry submitted through `SubmitDetections` with `Purpose = Overlay` is drawn on the stream a human operator watches (§9.2), and `ClassLabel` is free-form text. A Server **shall** render client-submitted overlay geometry so that it is visually distinguishable from Server-generated annotation, and **shall** bound `OverlayTtl` to a Server-configured maximum, so that an authorized-but-untrusted client cannot present a persistent misleading view to a human decision-maker.

---

## Deliverables and reproducibility {#sec-deliverables-and-reproducibility}

| Artifact | Path |
|---|---|
| This specification | `metaverse-specs/vision/OPC-UA-Vision.md` |
| Research and design rationale | `metaverse-specs/vision/OPC-UA-Vision-Research.md` |
| Base NodeSet | `metaverse-specs/vision/Opc.Ua.Vision.NodeSet2.xml` |
| NodeIds | `metaverse-specs/vision/Opc.Ua.Vision.NodeIds.csv` |
| Annex A (generated node table) | `extras/metaverse-specs/vision/tools/model-reference.md` |
| Generator | `extras/metaverse-specs/vision/tools/build_model.py` |
| Validator | `extras/metaverse-specs/vision/tools/validate_local.py` |
| Annex F — robotics worked example | `metaverse-specs/vision/robotics/` |
| Annex G — machine-vision worked example | `metaverse-specs/vision/machine-vision/` |
| Example generator | `extras/metaverse-specs/vision/tools/build_examples.py` |

Annexes F and G are **generated** into this document from the descriptors under `extras/metaverse-specs/vision/examples/`, between `<!-- BEGIN GENERATED -->` markers, by the same run that writes their overlays. They are also published standalone beside those overlays. Do not edit them here; edit the descriptor and regenerate.

Regenerate and validate from the repository root:

```powershell
python extras/metaverse-specs/vision/tools/build_model.py
python extras/metaverse-specs/vision/tools/build_examples.py
python extras/metaverse-specs/vision/tools/validate_local.py
python extras/metaverse-specs/validate_all.py --self-contained
```

The NodeSet and NodeIds are generated and byte-deterministic; do not hand-edit them. The validator additionally enforces two specification invariants that would otherwise be able to drift: that `Rtsp` is value 0 of `VisionStreamProtocolEnum`, and that `Jpeg` is value 0 of `VisionClipFormatEnum`.

---

## Information model reference {#anx-a annex=normative}

```{clause}
kind: annex-a
```

## Isaac Sim and Omniverse Replicator mapping (informative) {#anx-b annex=informative}

This annex is the vision-side half of the sim/real contract. The scene-side half is Annex D of *OPC UA — OpenUSD Scene Materialization*, and the binding-side view is Annex G of *OPC UA — OpenUSD Binding (Part 1)*.

### B.1 Why the mapping is anchored on UsdGeom {#sec-b-1-why-the-mapping-is-anchored-on-usdgeom}

NVIDIA Isaac Sim is an OpenUSD application. A camera in Isaac Sim is a `UsdGeomCamera` prim, and Part 2 materializes the UsdGeom typed-prim hierarchy into the address space. **`UsdGeomCameraType` is therefore the intersection between OpenUSD and this specification**: the same node is a scene object to Part 2 and a sensor to this model.

That is not incidental. A camera prim's aperture and focal-length attributes *are* the imaging intrinsics, so anchoring the mapping there means the simulator's configuration and the sensor's description are one artefact rather than two that must be kept in step.

### B.2 Sensor and intrinsics {#sec-b-2-sensor-and-intrinsics}

| This specification | Isaac Sim | OpenUSD (Part 2) |
|---|---|---|
| `ImageSensorType` | Camera sensor plus render product | `UsdGeomCameraType` |
| `IVisionSimulatedType.PrimPath` | Camera prim path in the stage | `SdfPath` |
| `VisionIntrinsicsDataType` | derived, see below | `FocalLength`, `HorizontalAperture`, `VerticalAperture`, apertures offsets |
| `ImageSensorType.Width` / `Height` | render product resolution | not on the prim |
| `Depth3DSensorType.MinDepth` / `MaxDepth` | near/far clip | `ClippingRange` |
| `OpticsType.Aperture` | depth-of-field f-stop | `FStop` |
| `OpticsType.WorkingDistance` | focus plane | `FocusDistance` |

Intrinsics are derived rather than stored twice. For a render product of width `W` and height `H`, with pixel coordinates in the **top-left-origin** frame of §5.12:

```text
Fx = FocalLength * W / HorizontalAperture
Fy = FocalLength * H / VerticalAperture
Cx = W / 2 - HorizontalApertureOffset * W / HorizontalAperture
Cy = H / 2 + VerticalApertureOffset   * H / VerticalAperture
```

`Fx` and `Fy` are ratios and are therefore independent of the stage's `metersPerUnit`. `Cx` carries a **minus**: USD's aperture window spans `[-HorizontalAperture/2 + offset, +HorizontalAperture/2 + offset]` in camera space, so a positive offset slides the film in `+x` and moves the principal point **left** in the image. `Cy` carries the opposite sign because the image row axis is inverted relative to USD's `+Y` up.

Resolution belongs to the render product, not the camera prim, which is why `Width` and `Height` live on `ImageSensorType` and not in USD. USD cameras look down −Z with +Y up; a client converting to a computer-vision convention applies the standard 180° rotation about X.

### B.3 Ground truth — Replicator annotators to result types {#sec-b-3-ground-truth-replicator-annotators-to-result-types}

Replicator attaches annotators to a render product. These are simulation outputs, not scene content, so they map to **results**, not to prims:

| Replicator annotator | This specification |
|---|---|
| `rgb` | a clip or stream payload, referenced by `VisionImageReferenceDataType` |
| `bounding_box_2d_tight`, `bounding_box_2d_loose` | `VisionDetectionDataType.BoundingBox2D` |
| `bounding_box_3d` | `VisionDetectionDataType.BoundingBox3D` and `Pose` |
| `semantic_segmentation`, `instance_segmentation` | `SegmentationResultType.Mask` |
| `distance_to_camera`, `distance_to_image_plane` | `Depth3DSensorType` output |
| `pointcloud` | `Depth3DSensorType` output, via a media endpoint |
| `normals`, `motion_vectors` | auxiliary channels, out of scope |

Class labels come from the `Semantics` applied API schema on prims, which Part 2 materializes as a `UsdApiSchemaType` AddIn. A client can therefore read a stage's label set over OPC UA and know which classes a generated dataset will contain **before** running the simulation — and those labels are the same strings that appear in `ModelType.LabelClasses` and `VisionDetectionDataType.ClassLabel`.

Because these are ground truth rather than prediction, §10 requires a Server to make them distinguishable from inference output.

### B.4 Datasets and the training loop {#sec-b-4-datasets-and-the-training-loop}

| This specification | Isaac Sim |
|---|---|
| `DatasetType` with `SourceKind = Synthetic` | Replicator writer output (BasicWriter, COCO, KITTI) |
| `DatasetType.SampleCount` | frames written |
| `IVisionSimulatedType.RandomizationSeed` | domain randomization seed |
| `LearningJobType` states `Collecting` → `Training` | a randomization run, then Isaac Lab or an external trainer |
| `DeploymentType` with `InferenceLocation = InSimulator` | inference inside the simulator, for closed-loop evaluation |

### B.5 Streaming from a simulator {#sec-b-5-streaming-from-a-simulator}

A simulated sensor still needs a `StreamEndpointType` with `StreamProtocol = Rtsp` and a `ClipEndpointType` with `ClipFormat = Jpeg` (§6.2). A Server backed by Isaac Sim satisfies this by serving the render product through an RTSP encoder, or by bridging the ROS 2 image topic that Isaac Sim's ROS bridge publishes. From the client's side nothing differs from a physical camera — which is the entire point.

### B.6 The sim-to-real loop, end to end {#sec-b-6-the-sim-to-real-loop-end-to-end}

1. Part 2 materializes the cell — geometry, semantic labels, and one or more `UsdGeomCameraType` prims.
2. Part 1 bindings drive live plant state into the stage, so the simulated cell tracks the real one.
3. A `VisionSensorType` with `RealityKind = Simulated` points at the camera prim through `PrimPath` and `HasScenePrim`.
4. Replicator renders and emits annotators; the Server publishes them as results and accumulates a `DatasetType` with `SourceKind = Synthetic`.
5. `LearningJobType` trains a `CandidateModel` and promotes it.
6. The promoted model is deployed against the **physical** sensor — same types, same members, `RealityKind = Physical`.
7. Operator corrections from the line arrive through `SubmitCorrection` and seed the next dataset, now `Mixed`.

Step 2 is what makes step 4 worth doing: a randomization run seeded from real plant state produces training data about the cell as it actually is, not as it was authored.

---

## OpenUSD Scene interop profile (normative for *VIS-Interop-Scene*) {#anx-c annex=normative}

This annex is informative for a Server that does not claim *VIS-Interop-Scene*, and normative for one that does. A Server claiming the facet implements both this specification and *OPC UA — OpenUSD Scene Materialization*, and **shall** satisfy all four requirements below. This profile takes no NodeSet dependency in either direction; it constrains only a Server that publishes both models.

1. `IVisionSimulatedType.PrimPath` **shall** resolve, within the stage named by `StageIdentifier`, to an instance of `UsdGeomCameraType`.
2. The sensor **shall** carry a `HasScenePrim` reference to that instance, so a client can navigate from sensor to prim without string resolution.
3. Where both describe the same quantity the values are **converted, not equal** — USD lengths are in world units scaled by the stage's `metersPerUnit`, whereas this model fixes SI units in §5.12:

   ```text
   OpticsType.FocalLength[mm]                 = prim.FocalLength   * metersPerUnit * 100
   OpticsType.WorkingDistance[m]              = prim.FocusDistance * metersPerUnit
   OpticsType.Aperture[f-number]              = prim.FStop
   Depth3DSensorType.MinDepth/MaxDepth[m]     = prim.ClippingRange * metersPerUnit
   ```

   Under no single stage scale would all of these be numerically identical, so a Server **shall** apply the conversion rather than copying the value.
4. `VisionIntrinsicsDataType` **shall** be consistent with the prim's aperture and focal-length attributes at the sensor's `Width` and `Height`, per the derivation in B.2 and the pixel datum of §5.12.

A Server that implements only this specification uses `PrimPath` as an opaque, portable descriptor and is fully conformant without this facet.

---

## OPC 40100 Machine Vision interop profile (normative for *VIS-Interop-40100*) {#anx-d annex=normative}

OPC 40100-1 orchestrates a vision system through its state machine, jobs, recipes, configurations and result transfer. OPC 40100-2 describes the system's assets, components, condition and maintenance information. This specification extends that family at the sensing and perception layer: it defines acquisition parameters, media endpoints, calibration and coordinate frames, AI inference and provenance, the content carried by a result, and the feedback path. It does not replace either OPC 40100 part.

This annex is informative for a Server that does not claim *VIS-Interop-40100*, and normative for one that does. A Server claiming the facet exposes both this model and OPC 40100 for the same equipment, and **shall** satisfy all five requirements below.

1. The Server **shall not** duplicate OPC 40100-1 job orchestration or its state machine in this model; the OPC 40100-1 instance remains the single source for job state.
2. For every inspection the Server reports through both models, the OPC 40100-1 `ResultDataType.ResultContent` **shall** be populated from the corresponding `InspectionResultType.Characteristics`, and `ResultDataType.ResultId` **shall** be equal to `VisionResultType.ResultId`. This equality is what lets a client join the two views; without it the mapping is unverifiable.
3. Where the Server exposes an OPC 40100-2 `ILensType` and an `OpticsType` for the same lens, the two **shall** describe it consistently, converted into the units fixed by §5.12.
4. Where the Server exposes an OPC 40100-2 `ILampType` or `ILightingControllerType` and an `IlluminationType` for the same emitter, the same consistency requirement applies. OPC 40100-2 types `LampType` as an open `String` and `LightingMode` as an unconstrained `UInt32`; this model enumerates both (§5.7). A Server exposing both **shall** convert as follows: `VisionLampTypeEnum` maps to and from the OPC 40100-2 String by the enumeration symbol name, compared case-insensitively, with `Other` used for any String no symbol matches; `VisionLightingModeEnum` maps to and from the OPC 40100-2 UInt32 by its numeric value, with any value the enumeration does not define read as `Other`. A Server **shall not** report an emitter as `Other` in this model while OPC 40100-2 reports a value one of the named symbols covers.
5. Where the Server exposes an OPC 40100-2 `VisionImageSensorType`, or a DI device/nameplate Object, for the same physical sensor as an `ImageSensorType`, the standard asset/device Object is authoritative for `Manufacturer`, `Model` and `SerialNumber`. Each corresponding `VisionSensorType` field that is populated **shall** equal the standard value. OPC 40100-2 `VisionImageSensorType` adds no members of its own, so this model supplies the imaging parameters; the two **shall not** identify different devices. References within this model target the `VisionSensorType` Object's NodeId. `SensorId` is its Vision-domain identifier and need not equal the standard Object's NodeId or asset identifier.

The alignment table below records the correspondence the requirements above rest on:

| Existing OPC 40100 authority or extension point | Extension defined by this specification |
|---|---|
| OPC 40100-1 `VisionSystemType` job orchestration and state machine | Not duplicated; Vision results and pipelines are associated with the job controlled by OPC 40100-1 |
| OPC 40100-1 `ResultDataType.ResultContent` (application-specific) | `InspectionResultType.Characteristics` defines interoperable inspection-result content |
| OPC 40100-1 `ResultDataType.ResultId` | `VisionResultType.ResultId` provides the join key between orchestration and perception views |
| OPC 40100-1 recipe identity and management | `InspectionResultType.RecipeId` identifies the recipe used without redefining its content or lifecycle |
| OPC 40100-2 `ILensType` | `OpticsType` provides the operational optics projection, with aligned member names and consistent values |
| OPC 40100-2 `ILampType`, `ILightingControllerType` | `IlluminationType` provides the operational illumination projection; enumerated values are converted per requirement 4 |
| OPC 40100-2 `VisionImageSensorType` and its DI/nameplate context | `ImageSensorType` adds acquisition and imaging semantics; the OPC 40100-2 or DI Object remains authoritative for asset identity |
| OPC 40100-2 `SoftwareComponents` | `ModelType` identifies the AI model specifically and adds model provenance |

The intended division is that OPC 40100-1 answers *"what job is the system running"*, OPC 40100-2 answers *"what equipment is installed and what condition is it in"*, and this specification answers *"what did the system see, how was it observed, and what produced the interpretation"*. Neither model requires the other, and a Server is fully conformant to this specification without this facet.

---

## Mapping to adjacent standards (informative) {#anx-e annex=informative}

None of the following is a normative reference. Names and field sets were borrowed deliberately so that bridges are mechanical, but no dependency is taken.

### E.1 GenICam — SFNC and PFNC {#sec-e-1-genicam-sfnc-and-pfnc}

**Annex H is the full binding.** The summary below is retained here so this annex lists every adjacent standard in one place.

| This specification | GenICam |
|---|---|
| `ImageSensorType.Width`, `Height`, `OffsetX`, `OffsetY` | SFNC `Width`, `Height`, `OffsetX`, `OffsetY` |
| `ExposureTime`, `Gain`, `AcquisitionFrameRate` | SFNC identically named features |
| `TriggerMode`, `TriggerSource` | SFNC identically named features |
| `BinningHorizontal`, `BinningVertical`, `ReverseX`, `ReverseY` | SFNC identically named features |
| `PixelFormat` string values | PFNC names, e.g. `Mono8`, `BayerRG12`, `RGB8` |
| `VisionSensorType.DeviceUri` | the GenTL device identifier |
| `VisionStreamProtocolEnum.GenDc` | a GenDC container stream |

GenICam configures and streams from the device; this model publishes semantics and brokers endpoints. There is no published GenICam-to-OPC-UA mapping specification, and neither this annex nor Annex H is one.

### E.2 ONVIF — Profiles S, T and M {#sec-e-2-onvif-profiles-s-t-and-m}

ONVIF is the dominant standard in network video and physical security, and an increasing number of industrial cameras expose it. It reached the same layering conclusion as §6.1 independently: Profiles S and T broker an RTSP endpoint and leave the pixels on RTP.

| This specification | ONVIF |
|---|---|
| `StreamEndpointType` with `StreamProtocol = Rtsp` | Profile S / T media service, RTSP + RTP |
| `StreamEndpointType` with `Rtsps`, `SecureTransport` | Profile T secure transport |
| `StreamEndpointType.Codec` | Profile T H.264 / H.265 encoder configuration |
| `VisionSensorType.DeviceUri` | the ONVIF device service address |
| `DetectionResultType.Detections` | Profile M analytics metadata — *partial*, see below |

Profile M is the closest external analogue to clause 7 and the strongest evidence that result content *can* be standardised — but its vocabulary is surveillance (faces, licence plates, line crossing), and it carries no measured characteristic, no tolerance, no ISO 14253 uncertainty, no 6-DoF pose in a named frame and no description of the model that produced the output. It is therefore adjacent on the **media** axis and not usable on the **semantics** axis. A Server fronting an ONVIF camera publishes its stream through `StreamEndpointType` exactly as it would a GenICam device; this model is indifferent to which. The research report §3.1a sets out the comparison in full.

### E.3 QIF — ISO 23952 {#sec-e-3-qif-iso-23952}

`VisionCharacteristicDataType` mirrors QIF Results: `Nominal`, `Actual`, `Deviation`, `LowerTolerance`, `UpperTolerance`, `Unit`, `Uncertainty` (per ISO 14253) and `Status`. A QIF document can be produced from an `InspectionResultType` without inventing information. The reverse — a full QIF-to-OPC-UA semantic mapping — does not exist as a standard; OPC 40210 §5.3.3 names QIF as a result format and explicitly defines "only the transport".

### E.4 ROS 2 `vision_msgs` {#sec-e-4-ros-2-visionmsgs}

| This specification | ROS 2 |
|---|---|
| `VisionDetectionDataType` | `vision_msgs/Detection2D`, `Detection3D` |
| `ClassLabel`, `ClassId`, `Confidence` | `ObjectHypothesis` |
| `Pose` with `FrameId` | `ObjectHypothesisWithPose` plus the `header.frame_id` |
| `VisionBoundingBox2DDataType` | `vision_msgs/BoundingBox2D` |
| `VisionBoundingBox3DDataType` | `vision_msgs/BoundingBox3D` |
| `VisionIntrinsicsDataType` | `sensor_msgs/CameraInfo` K, D, and size |
| `SegmentationResultType` | `vision_msgs` segmentation messages |
| `CoordinateFrameType` tree | the TF frame tree |

The `CameraInfo` mapping is **not** a copy. Two adjustments are required, both fixed normatively in §5.12: the principal point uses a different sub-pixel datum, so a bridge **shall** compute `K[2] = Cx − 0.5` and `K[5] = Cy − 0.5` when producing `CameraInfo`, and add 0.5 when consuming it; and `D` is ordered by `DistortionModel` per the §5.12 table, which for `BrownConrady` already matches the OpenCV `plumb_bob` order. Quaternions in `geometry_msgs` are ordered (x, y, z, w), which matches §5.12 and needs no reordering.

### E.5 IDTA Asset Administration Shell submodels {#sec-e-5-idta-asset-administration-shell-submodels}

| This specification | IDTA template |
|---|---|
| `ModelType` | **IDTA 02060** AI Model Nameplate |
| `DatasetType` | **IDTA 02058** AI Dataset |
| `DeploymentType` | **IDTA 02059** AI Model Management |

There is no IDTA submodel template for machine vision, so `VisionSensorType` and the result types have no counterpart. The OPC UA bridge to the AAS, OPC 30270, currently maps AAS V2.0.1 and is slated for replacement; this model therefore aligns by field name rather than depending on that bridge.

### E.6 ISO robotics and metrology {#sec-e-6-iso-robotics-and-metrology}

| This specification | Standard |
|---|---|
| `VisionFrameRoleEnum` | ISO 9787:2013 coordinate systems, distinguishing the mechanical interface from the tool centre point |
| `VisionCharacteristicDataType.Uncertainty` | ISO 14253 |
| `ExtrinsicCalibrationType` | no standard defines the hand-eye procedure; only the result is portable |
| Terminology | ISO 8373:2021 robotics vocabulary |

---

<!-- BEGIN GENERATED: annex-robotics -->

## Worked example: robotics vision, eye-in-hand picking (informative) {#anx-f annex=normative}

> A worked example of vision-guided robotics: an eye-in-hand 3D camera on a robot flange detects parts in a bin and publishes 6-DoF pick poses, with inference running off-server on an edge GPU and a simulated twin sensor rendering the same cell in NVIDIA Isaac Sim. This annex and the overlay [`Opc.Ua.Robotics.Vision.NodeSet2.xml`](../../../model/metaverse-specs/vision/Opc.Ua.Robotics.Vision.NodeSet2.xml) are both generated from [`Robotics.Vision.json`](../../../extras/metaverse-specs/vision/examples/robotics/Robotics.Vision.json) by `build_examples.py`, so prose and model cannot drift. The same content is published beside the overlay as [`OPC-UA-Robotics-Vision-Addendum.md`](robotics/OPC-UA-Robotics-Vision-Addendum.md).

### F.1 Scope {#sec-f-1-scope}

This worked example binds one eye-in-hand camera to a robot flange frame and shows the full perception path: a hand-eye `ExtrinsicCalibrationType` that makes poses actionable, a `DetectionResultType` carrying 6-DoF grasp poses in a named frame, an off-server GPU deployment, and an RTSP stream with detection overlay feedback. It is the case OPC UA has no coverage for today: OPC 40010-1 Robotics contains no vision, camera, perception or calibration types at all, and neither it nor OPC 40100 references the other.

### F.2 Normative references {#sec-f-2-normative-references}

- OPC 40010-1 — OPC UA for Robotics, whose `MotionDeviceSystemType` describes the robot this camera is mounted on. Not a dependency of this model.
- ISO 9787:2013 — coordinate systems, the source of the frame roles used here.
- ROS 2 `vision_msgs` — the convention `VisionDetectionDataType` field naming follows.

### F.3 The sensor {#sec-f-3-the-sensor}

| Member | Value |
|---|---|
| Type | `ImageSensorType` |
| `SensorId` | `cam-eih-01` |
| `RealityKind` | `Physical` |
| `Modality` | `Area2D` |
| `Width` | `2448` |
| `Height` | `2048` |
| `PixelFormat` | `BayerRG8` |
| `ExposureTime` (µs) | `4000.0` |
| `Gain` | `2.5` |
| `AcquisitionFrameRate` | `15.0` |
| `TriggerMode` | `On` |
| `DeviceUri` | `gev://192.0.2.41/0` |
| `FrameId` | `camera_eih` |

### F.4 Media endpoints {#sec-f-4-media-endpoints}

Both mandatory defaults of base specification §6.2 are present — an RTSP stream and a JPEG clip endpoint:

| Endpoint | Type | Key members |
|---|---|---|
| `LiveRtsp` | `StreamEndpointType` | `StreamProtocol = Rtsp`, `EndpointUri = rtsp://192.0.2.41:554/main` |
| `PickFrames` | `ClipEndpointType` | `ClipFormat = Jpeg`, `EndpointUri = https://192.0.2.41/clips/{resultId}.jpg` |

This clip endpoint implements the optional **VIS-Media-Inline** facet but leaves it switched off: `InlineDeliveryEnabled = false`, so per base specification §6.4 rule 5 the Server reports `LatestClip` with `Bad_NotSupported` while `LatestClipMetadata` stays readable. Clips are obtained through `GetClip` and fetched from the returned `Uri`, which is the default path. Clause 11 requires the facet's four members to be present together even in this state, which is why the overlay declares all four.

Both endpoints additionally offer the optional **VIS-Media-DataChannel** facet of base specification §6.7, so this example shows the case where a data channel is an *additional* path to the same content rather than the only one:

| Endpoint | `StreamProtocol` / `ClipFormat` | `EndpointUri` | `DataChannelSource` | `DataChannelContentType` |
|---|---|---|---|---|
| `LiveRtsp` | `Rtsp` | `rtsp://192.0.2.41:554/main` | `H264DataChannelSource` | `video/H264` |
| `PickFrames` | `Jpeg` | `https://192.0.2.41/clips/{resultId}.jpg` | `JpegDataChannelSource` | `image/jpeg` |

`StreamProtocol` stays `Rtsp` and `EndpointUri` keeps its out-of-band value, because per §6.7 a Server sets `StreamProtocol = DataChannel` only where the data channel is the endpoint's *only* path. A non-null `DataChannelSource` is what signals the additional path. Per §6.3 the Server will not return these on the data-channel path unless a client asks for `PreferredProtocol = DataChannel` explicitly, so a client that cannot open a data channel is unaffected.

The source Objects in this overlay are plain `BaseObjectType` instances standing in for Server-created nodes. On a Server implementing the *OPC UA — Data Channels* draft each would also implement `IDataChannelSourceType` and be reachable by `HasDataChannel`. This overlay emits neither, because those are provisional identifiers in the **base** namespace: a NodeSet referencing them would fail to load on the majority of Servers, which have not adopted that draft. That draft is a **working draft**, and both this example and the base specification are fully conformant without it.

### F.5 Coordinate frames and calibration {#sec-f-5-coordinate-frames-and-calibration}

The frame tree. `ParentFrame` is what makes it composable: a client walks from the frame a pose is expressed in up to the frame it needs, composing the transforms it finds on the way.

| Instance | `FrameId` | `Role` | `ParentFrame` |
|---|---|---|---|
| `WorldFrame` | `world` | `World` | none (tree root) |
| `RobotBaseFrame` | `robot_base` | `Base` | `world` |
| `FlangeFrame` | `flange` | `MechanicalInterface` | `robot_base` |
| `GripperTcpFrame` | `gripper_tcp` | `Tool` | `flange` |
| `CameraFrame` | `camera_eih` | `Camera` | `flange` |

**`Intrinsics2448x2048`** (`IntrinsicCalibrationType`) — Pinhole intrinsics with Brown-Conrady distortion at full resolution.

| Member | Value |
|---|---|
| `CalibrationId` | `intr-cam-eih-01-2448` |
| `PerformedAt` | `2026-06-14T09:12:00Z` |
| `Valid` | `true` |
| `Method` | `Zhang` |
| `ResidualError` | `0.21` |

`Intrinsics` field values, in the units fixed by base specification §5.12:

| Field | Value | Unit / convention |
|---|---|---|
| `Fx` | `2140.5` | px |
| `Fy` | `2139.8` | px |
| `Cx` | `1223.1` | px, corner-datum per §5.12 |
| `Cy` | `1021.7` | px, corner-datum per §5.12 |
| `Skew` | `0.0` | px |
| `DistortionModel` | `BrownConrady` | §5.12 ordering: k1, k2, p1, p2, k3 |
| `DistortionCoefficients` | `[-0.1721, 0.0934, 0.0002, -0.0001, -0.0188]` | dimensionless |
| `Width` | `2448` | px |
| `Height` | `2048` | px |

**`HandEye`** (`ExtrinsicCalibrationType`) — Transform from the camera frame to the robot mechanical interface. Eye-in-hand: the camera moves with the flange, so a pick pose is obtained by composing camera → flange → tool centre point.

| Member | Value |
|---|---|
| `CalibrationId` | `hand-eye-cam-eih-01` |
| `PerformedAt` | `2026-06-14T10:40:00Z` |
| `Valid` | `true` |
| `Method` | `Daniilidis` |
| `ResidualError` | `0.0008` |
| `Mount` | `EyeInHand` |
| `SourceFrame` | `camera_eih` |
| `TargetFrame` | `flange` |

`Transform` field values, in the units fixed by base specification §5.12:

| Field | Value | Unit / convention |
|---|---|---|
| `FrameId` | `flange` | equals the TargetFrame's FrameId, per the §5.12 frame-precedence rule |
| `Position` | `(0.062, -0.031, 0.115)` | metres, ordered (x, y, z) |
| `Orientation` | `(0.0, 0.0, 0.7071, 0.7071)` | unit quaternion ordered (x, y, z, w) |
| `Covariance` | `empty array` | not reported, per the §5.12 sentinel |

Each calibration is reachable from the sensor by a `HasCalibration` reference, as base specification §5.11 requires.

### F.6 The simulated twin {#sec-f-6-the-simulated-twin}

The same cell is rendered in NVIDIA Isaac Sim, and the synthetic sensor is modelled here alongside the physical one. Note what is *not* different: same type, same members, same units, same mandatory RTSP and JPEG endpoints. A client written against `VisionSensorType` consumes either without modification, and can tell them apart only by reading `RealityKind`. That is the sim/real symmetry of base specification §4.3, and it is what lets a model be trained on synthetic data and then deployed against the physical camera unchanged.

| Member | Physical sensor | Simulated twin |
|---|---|---|
| Instance | `BinPickingCamera` | `BinPickingCameraTwin` |
| `RealityKind` | `Physical` | `Simulated` |
| Type | `ImageSensorType` | `ImageSensorType` |
| `Width` x `Height` | `2448` x `2048` | `2448` x `2048` |
| `PixelFormat` | `BayerRG8` | `BayerRG8` |
| Media endpoints | RTSP + JPEG | RTSP + JPEG |

The twin additionally implements `IVisionSimulatedType`:

| Member | Value |
|---|---|
| `SimulatorUri` | `isaacsim://cell-sim-01` |
| `StageIdentifier` | `omniverse://plant/Cell_A/stage.usda` |
| `PrimPath` | `/Cell/Robots/R1/Flange/Camera` |
| `GroundTruthAvailable` | `true` |

`PrimPath` resolves to a `UsdGeomCameraType` instance where the Server also implements *OPC UA — OpenUSD Scene Materialization* and claims the base specification's *VIS-Interop-Scene* facet (Annex C), so the camera's aperture and focal-length attributes are both the scene description and the imaging intrinsics.

### F.7 Inference {#sec-f-7-inference}

| Member | Value |
|---|---|
| Model | `GraspPoseNet` v`3.2.0` (TensorRT) |
| `TaskKind` | `PoseEstimation` |
| `InferenceLocation` | **`EdgeOffServer`** |
| `AcceleratorKind` | `Gpu` |
| `EndpointUri` | `grpcs://192.0.2.60:8001/graspposenet` |
| `MaxResultAge` | `3600000` ms |
| `MaxRetainedResults` | `2000` |

Inference runs **off-server** on a cell-side GPU appliance. The Server publishes results it did not compute. Nothing else in the model changes: a client reads `DetectionResultType` exactly as it would if `InferenceLocation` were `OnServer`, and consults that property only if it cares about the latency or trust boundary. Because the deployment is remote, base specification §12.6 applies: the channel to the inference service is authenticated and integrity-protected, and `ModelType.Digest` lets a consumer confirm which artefact produced a result.

The deployment carries exactly one `UsesModel` reference to the model above, as *OPC UA — AI Model Management and Inference* requires. That reference says which model is serving now. Each retained result records the model that actually answered in `ModelUsed`, so an audit follows `result.ModelUsed` to the model and its `Digest` even after a promotion, fallback or followed-reference change.

### F.8 Results {#sec-f-8-results}

Each cycle produces a `DetectionResultType`; the pipeline retains result nodes for at most one hour and 2,000 results, evicting oldest `CreationTime` first when count pressure applies. Its `ModelUsed` names `GraspPoseNet`, the model that actually answered, even if the deployment later promotes another model or routes one call through a fallback. Its `Detections` carry `ClassLabel`, `Confidence`, a `BoundingBox2D`, a `BoundingBox3D` and — the member that makes the result actionable — a 6-DoF `Pose`. Every pose names its `FrameId` (`camera_eih`), which is only meaningful because the `HandEye` calibration above relates that frame to the flange. A consumer composes camera → flange → base through the `CoordinateFrameType` tree to obtain the pose in robot coordinates, and camera → flange → `gripper_tcp` to obtain what the gripper must actually reach. The two are distinct: the calibration resolves to the mechanical interface, while a grasp is executed at the tool centre point, and the frame tree carries the offset between them rather than leaving it to be assumed. `ResidualError` on the calibration is what tells the consumer how much to trust it. Result-node eviction is independent of frame/clip, external artefact, and application evidence retention.

### F.9 Feedback {#sec-f-9-feedback}

Two feedback paths are exercised. During commissioning, the HMI calls `SubmitDetections` with `Purpose = Overlay` so the operator sees candidate grasps drawn on the RTSP stream. In production, a failed pick calls `SubmitCorrection` with `Purpose = GroundTruthLabel`, and the corrected pose is retained by the `LearningJobType` as a labelled sample — so the cases the model gets wrong are exactly the cases the next dataset contains. Feedback images are passed by reference through `SubmitImageReference`; this example does not enable inline feedback images.

### F.10 Deliverables {#sec-f-10-deliverables}

| File | Content |
|---|---|
| [`Robotics.Vision.json`](../../../extras/metaverse-specs/vision/examples/robotics/Robotics.Vision.json) | Machine-readable descriptor (single source). |
| [`Opc.Ua.Robotics.Vision.NodeSet2.xml`](../../../model/metaverse-specs/vision/Opc.Ua.Robotics.Vision.NodeSet2.xml) | The generated instance overlay. |
| [`OPC-UA-Robotics-Vision-Addendum.md`](robotics/OPC-UA-Robotics-Vision-Addendum.md) | This annex, published standalone beside the overlay. |

Regenerate from the repository root with `python extras/metaverse-specs/vision/tools/build_examples.py`.

<!-- END GENERATED: annex-robotics -->

---

<!-- BEGIN GENERATED: annex-machine-vision -->

## Worked example: machine vision, dimensional inspection (informative) {#anx-g annex=normative}

> A worked example of machine-vision inspection: a fixed camera measures a sealing surface, on-server inference produces a verdict with QIF-shaped characteristics including measurement uncertainty, and each result carries a subscribable JPEG thumbnail through the optional size-gated inline delivery facet. This annex and the overlay [`Opc.Ua.Inspection.Vision.NodeSet2.xml`](../../../model/metaverse-specs/vision/Opc.Ua.Inspection.Vision.NodeSet2.xml) are both generated from [`Inspection.Vision.json`](../../../extras/metaverse-specs/vision/examples/machine-vision/Inspection.Vision.json) by `build_examples.py`, so prose and model cannot drift. The same content is published beside the overlay as [`OPC-UA-Inspection-Vision-Addendum.md`](machine-vision/OPC-UA-Inspection-Vision-Addendum.md).

### G.1 Scope {#sec-g-1-scope}

This worked example shows the case OPC 40100-1 orchestrates but does not describe: the *content* of an inspection result. A fixed area-scan camera inspects a sealing surface; the result is an `InspectionResultType` carrying an `Evaluation` and a set of `VisionCharacteristicDataType` entries with nominal, actual, deviation, tolerances and uncertainty. It also demonstrates the optional **VIS-Media-Inline** facet: a small JPEG thumbnail is published as `LatestClip` and can be subscribed to with a MonitoredItem, while the full-resolution image stays behind a URI.

### G.2 Normative references {#sec-g-2-normative-references}

- OPC 40100-1 — OPC UA for Machine Vision Part 1, whose `ResultContent` this example populates. Not a dependency of this model.
- ISO 23952:2020 (QIF) — the shape `VisionCharacteristicDataType` mirrors.
- ISO 14253 — the uncertainty semantics used by `Uncertainty` and `NotDecidable`.

### G.3 The sensor {#sec-g-3-the-sensor}

| Member | Value |
|---|---|
| Type | `ImageSensorType` |
| `SensorId` | `cam-insp-07` |
| `RealityKind` | `Physical` |
| `Modality` | `Area2D` |
| `Width` | `2592` |
| `Height` | `1944` |
| `PixelFormat` | `Mono8` |
| `ExposureTime` (µs) | `1200.0` |
| `Gain` | `1.0` |
| `AcquisitionFrameRate` | `8.0` |
| `TriggerMode` | `On` |
| `DeviceUri` | `u3v://0x2A0B/0x0410/SN-9083-1174` |
| `FrameId` | `camera_insp_07` |

### G.4 Media endpoints {#sec-g-4-media-endpoints}

Both mandatory defaults of base specification §6.2 are present — an RTSP stream and a JPEG clip endpoint:

| Endpoint | Type | Key members |
|---|---|---|
| `LiveRtsp` | `StreamEndpointType` | `StreamProtocol = Rtsp`, `EndpointUri = rtsp://192.0.2.77:554/setup` |
| `PartFrames` | `ClipEndpointType` | `ClipFormat = Jpeg`, `EndpointUri = https://192.0.2.77/clips/{resultId}.jpg` |

This clip endpoint additionally enables the optional **VIS-Media-Inline** facet, with `MaxInlineClipSize = 262144` bytes. Clause 11 requires all four members of that facet together, so the endpoint instantiates `InlineDeliveryEnabled`, `MaxInlineClipSize`, `LatestClip` and `LatestClipMetadata`. A client may subscribe to `LatestClip` and receive the encoded JPEG directly; if an image exceeds that bound the Server sets `Bad_EncodingLimitsExceeded` and the client falls back to `LatestClipMetadata.Uri` (base specification §6.4).

### G.5 Coordinate frames and calibration {#sec-g-5-coordinate-frames-and-calibration}

The frame tree. `ParentFrame` is what makes it composable: a client walks from the frame a pose is expressed in up to the frame it needs, composing the transforms it finds on the way.

| Instance | `FrameId` | `Role` | `ParentFrame` |
|---|---|---|---|
| `StationFrame` | `station` | `World` | none (tree root) |
| `CameraFrame` | `camera_insp_07` | `Camera` | `station` |

**`Intrinsics2592x1944`** (`IntrinsicCalibrationType`) — Pinhole intrinsics at full resolution; a telecentric lens leaves very little residual distortion.

| Member | Value |
|---|---|
| `CalibrationId` | `intr-cam-insp-07` |
| `PerformedAt` | `2026-05-02T07:55:00Z` |
| `Valid` | `true` |
| `Method` | `Zhang` |
| `ResidualError` | `0.08` |

`Intrinsics` field values, in the units fixed by base specification §5.12:

| Field | Value | Unit / convention |
|---|---|---|
| `Fx` | `8310.2` | px |
| `Fy` | `8309.6` | px |
| `Cx` | `1295.4` | px, corner-datum per §5.12 |
| `Cy` | `971.2` | px, corner-datum per §5.12 |
| `Skew` | `0.0` | px |
| `DistortionModel` | `BrownConrady` | §5.12 ordering: k1, k2, p1, p2, k3 |
| `DistortionCoefficients` | `[-0.0021, 0.0004, 0.0, 0.0, 0.0]` | dimensionless; a telecentric lens is close to distortion-free |
| `Width` | `2592` | px |
| `Height` | `1944` | px |

**`StationMounting`** (`ExtrinsicCalibrationType`) — Transform from the camera frame to the station world frame. The camera is fixed, so there is no kinematic chain.

| Member | Value |
|---|---|
| `CalibrationId` | `extr-cam-insp-07` |
| `PerformedAt` | `2026-05-02T08:20:00Z` |
| `Valid` | `true` |
| `Method` | `TargetPlate` |
| `ResidualError` | `0.00015` |
| `Mount` | `Fixed` |
| `SourceFrame` | `camera_insp_07` |
| `TargetFrame` | `station` |

`Transform` field values, in the units fixed by base specification §5.12:

| Field | Value | Unit / convention |
|---|---|---|
| `FrameId` | `station` | equals the TargetFrame's FrameId, per the §5.12 frame-precedence rule |
| `Position` | `(0.0, 0.0, 0.320)` | metres, ordered (x, y, z) |
| `Orientation` | `(1.0, 0.0, 0.0, 0.0)` | unit quaternion ordered (x, y, z, w); a 180 degree rotation about x, so the camera looks down at the station |
| `Covariance` | `empty array` | not reported, per the §5.12 sentinel |

Each calibration is reachable from the sensor by a `HasCalibration` reference, as base specification §5.11 requires.

### G.6 Inference {#sec-g-6-inference}

| Member | Value |
|---|---|
| Model | `SealDefectNet` v`1.4.1` (ONNX) |
| `TaskKind` | `Segmentation` |
| `InferenceLocation` | **`OnServer`** |
| `AcceleratorKind` | `Npu` |
| `MaxResultAge` | `86400000` ms |
| `MaxRetainedResults` | `10000` |

Inference runs **on-server**: `InferenceLocation = OnServer`, on an NPU in the station industrial PC. A client consuming the results cannot distinguish this from the off-server robotics example except by reading that one property — which is the intent of base specification §8.2. Because the pipeline is not continuous, `RunInference` is called per part by the station PLC and returns the `ResultId` it produced.

The deployment carries exactly one `UsesModel` reference to the model above, as *OPC UA — AI Model Management and Inference* requires. That reference says which model is serving now. Each retained result records the model that actually answered in `ModelUsed`, so an audit follows `result.ModelUsed` to the model and its `Digest` even after a promotion, fallback or followed-reference change.

### G.7 Results {#sec-g-7-results}

Each part produces an `InspectionResultType`. The pipeline retains result nodes for at most 24 hours and 10,000 results; whichever bound first requires eviction applies. Its `ModelUsed` names `SealDefectNet`, the model that actually answered, while the deployment's `UsesModel` reference says which model is serving now. `Evaluation` uses the OPC 40001-101 value semantics, and the `Characteristics` array carries one `VisionCharacteristicDataType` per measured feature — for example a flatness with `Nominal = 0.0`, `Actual = 0.018`, `UpperTolerance = 0.020`, `Unit = mm` and `Uncertainty = 0.004`. That last field is the point: because the expanded uncertainty spans the tolerance limit, the Server reports `NotDecidable` rather than asserting `Ok` from the point estimate alone. A verdict recorded this way is reproducible by a third party, and a QIF document can be generated from it without inventing information. Evicting the result node does not define the lifetime of its JPEG, external explanation artefact, or application evidence record.

### G.8 Feedback {#sec-g-8-feedback}

When a quality engineer overrides a verdict at the review station, the HMI calls `SubmitCorrection` with `Purpose = GroundTruthLabel`, passing the corrected characteristics and a reason. Because this endpoint enables inline delivery, the corrected thumbnail may accompany the call as an inline `ByteString` provided it fits `MaxInlineFeedbackImageSize`; anything larger is rejected with `Bad_EncodingLimitsExceeded` and resubmitted through `SubmitImageReference`. Downstream leak-test results arrive through `SubmitInspectionResult`, which reconciles a downstream `Evaluation` and its characteristics against what the vision system originally reported — and the disagreements are precisely the samples the next `LearningJobType` collects.

### G.9 Deliverables {#sec-g-9-deliverables}

| File | Content |
|---|---|
| [`Inspection.Vision.json`](../../../extras/metaverse-specs/vision/examples/machine-vision/Inspection.Vision.json) | Machine-readable descriptor (single source). |
| [`Opc.Ua.Inspection.Vision.NodeSet2.xml`](../../../model/metaverse-specs/vision/Opc.Ua.Inspection.Vision.NodeSet2.xml) | The generated instance overlay. |
| [`OPC-UA-Inspection-Vision-Addendum.md`](machine-vision/OPC-UA-Inspection-Vision-Addendum.md) | This annex, published standalone beside the overlay. |

Regenerate from the repository root with `python extras/metaverse-specs/vision/tools/build_examples.py`.

<!-- END GENERATED: annex-machine-vision -->

---

## GenICam binding (informative) {#anx-h annex=informative}

This annex is the binding that clause 5.5 refers to. It exists because a Server implementing this model almost always talks to its cameras through GenICam, and the question *"which SFNC feature does this member come from"* would otherwise be answered differently by every implementer. It is **informative**: nothing here requires a GenICam device, and a Server whose cameras are not GenICam devices populates the same members from whatever its driver provides.

### H.1 Why the names were borrowed {#sec-h-1-why-the-names-were-borrowed}

`ImageSensorType` uses GenICam **SFNC 2.8** feature names and semantics, and `PixelFormat` uses **PFNC** naming. The alternative — inventing OPC UA names for parameters that already have universally understood ones — would have forced every Server to maintain a translation table and every client to learn a second vocabulary for the same physical quantities. Borrowing the names makes the bridge mechanical in both directions.

Borrowing names is not taking a dependency. This specification declares no GenICam reference, requires no GenTL producer, and works unchanged over a camera exposed by any other means.

### H.2 Acquisition parameters {#sec-h-2-acquisition-parameters}

Read as: the Server reads the SFNC feature and publishes it as the member, applying the stated conversion.

| `ImageSensorType` member | SFNC 2.8 feature | Type in SFNC | Conversion |
|---|---|---|---|
| `Width` | `Width` | IInteger | none |
| `Height` | `Height` | IInteger | none |
| `OffsetX` | `OffsetX` | IInteger | none |
| `OffsetY` | `OffsetY` | IInteger | none |
| `PixelFormat` | `PixelFormat` | IEnumeration | the PFNC **name** of the selected entry, as a String — not the numeric PFNC value |
| `ExposureTime` | `ExposureTime` | IFloat, microseconds | none; §5.12 fixes microseconds for exactly this reason |
| `Gain` | `Gain` | IFloat | none. SFNC `Gain` is in dB where `GainAuto` is off and the device declares it so; this model does not fix a unit for `Gain` and a Server **should** publish the device's own |
| `AcquisitionFrameRate` | `AcquisitionFrameRate` | IFloat, Hz | none |
| `TriggerMode` | `TriggerMode` | IEnumeration (`Off`, `On`) | the entry name as a String |
| `TriggerSource` | `TriggerSource` | IEnumeration | the entry name as a String |
| `BinningHorizontal` | `BinningHorizontal` | IInteger | none |
| `BinningVertical` | `BinningVertical` | IInteger | none |
| `ReverseX` | `ReverseX` | IBoolean | none |
| `ReverseY` | `ReverseY` | IBoolean | none |

Two SFNC conventions matter when reading this table:

1. **Selectors.** Several SFNC features are qualified by a selector — `GainSelector`, `TriggerSelector`, `ExposureTimeSelector`. This model publishes the value for the device's **currently selected** entry and does not model the selector. A Server that must expose more than one selector value models it as more than one sensor, or as a vendor extension.
2. **`…Auto` features.** `ExposureAuto`, `GainAuto` and `BalanceWhiteAuto` have no member here. Where they are active the corresponding value is being changed by the device, so a Server **should** publish the current effective value and a client **should not** assume it is stable between acquisitions.

### H.3 Pixel formats {#sec-h-3-pixel-formats}

`PixelFormat` carries a PFNC *name*, not a numeric value, because the name is stable across PFNC revisions and is what appears in every camera datasheet and SDK.

| Family | Examples | Note |
|---|---|---|
| Monochrome | `Mono8`, `Mono10`, `Mono12`, `Mono16` | bit depth is part of the name |
| Bayer | `BayerRG8`, `BayerGB12`, `BayerBG16` | the two letters give the CFA phase; the client needs them to demosaic correctly |
| Colour | `RGB8`, `BGR8`, `RGBa8`, `YCbCr422_8` | |
| 3-D | `Coord3D_ABC32f`, `Coord3D_C16` | produced by `Depth3DSensorType`, not by `ImageSensorType` |

A client that does not recognise a `PixelFormat` **shall not** guess: it obtains the image through a media endpoint in a format it does understand — JPEG is always available (§6.2) — rather than misinterpreting the bytes.

### H.4 Device identity and transport {#sec-h-4-device-identity-and-transport}

| This specification | GenICam / transport layer |
|---|---|
| `VisionSensorType.DeviceUri` | the GenTL device identifier, or a transport-specific URI such as `gev://<ip>/<n>` for GigE Vision or `u3v://<vid>/<pid>/<serial>` for USB3 Vision |
| `VisionSensorType.Manufacturer`, `Model`, `SerialNumber` | the corresponding GenTL device information |
| `VisionStreamProtocolEnum.GenDc` | a GenDC container stream, where the Server brokers the device stream directly |

`DeviceUri` is the join key: it is what lets a maintenance tool holding a GenTL device list match a camera to its OPC UA node.

### H.5 What deliberately has no binding {#sec-h-5-what-deliberately-has-no-binding}

- **Streaming itself.** GigE Vision, USB3 Vision and CoaXPress move pixels; this model brokers endpoints (§6.1). A Server does not re-publish a GenICam stream through OPC UA.
- **The full SFNC feature set.** SFNC has hundreds of features. This model publishes the ones that determine what an image *is* and how to interpret a result. A Server needing more exposes them as vendor members.
- **Writing features.** Nothing in this model configures a camera through GenICam. `ConfigureStreamEndpoint` (§6.5) configures the *encoder* of a media endpoint, not the sensor.

There is no published GenICam-to-OPC-UA mapping specification. This annex is a binding for this model only, and does not claim to be one.

---

## Robot Intent interop profile (normative for *VIS-Interop-RobotIntent*) {#anx-i annex=normative}

A camera that guides a robot and an interface that commands one are deployed on the same cell, and each defines its own `CoordinateFrameType`. Without a rule the flange is described twice, in two namespaces, with two `FrameId` strings and two `Transform` values that can disagree — the failure §5.8 warns about, arrived at by integration rather than by miscalibration.

This annex fixes the correspondence. It imposes **no** NodeSet dependency in either direction: both models keep the base OPC UA namespace as their only `RequiredModel`, and a Server implementing one of them is unaffected by the other.

**I.1 One frame tree is authoritative.** Where a Server implements both models for the same physical robot, the commanding model's frame tree **shall** decide. It owns the tool centre point, and a pose that disagrees with the frame the robot actually moves to is wrong however carefully it was measured. This model's frames **shall** then describe the same physical frames with the same transforms.

**I.2 `FrameId` corresponds by value.** A frame present in both models **shall** carry the **same** `FrameId` string in each. That string, not the NodeId, is what a pose names, so it is the only correspondence a pose can carry.

**I.3 Roles correspond by name.** The two role vocabularies agree on `World`, `Base`, `MechanicalInterface`, `Tool`, `Object` and `Other`; a frame present in both **shall** carry the same role. `Camera` exists only here, and a camera frame published to the commanding model **shall** be given the role `Other` there, because that model defines no camera role and misusing `Tool` would put a grasp at the lens.

> The numeric values of the two enumerations are **not** interchangeable across models: each is decoded against the DataType of the Variable that carries it. A gateway **shall** map by literal name and **shall not** cast the integer.

**I.4 Poses transcode explicitly.** The two pose structures are not wire-compatible — this model's carries a fourth field, `Covariance`. A boundary **shall** transcode rather than pass through:

| From | To | Rule |
|---|---|---|
| `VisionPose3DDataType` | commanding pose | drop `Covariance`; `FrameId`, `Position` and `Orientation` transfer unchanged |
| commanding pose | `VisionPose3DDataType` | set `Covariance` to an **empty array**, which §5.12 defines as *not reported* — a Server **shall not** fabricate one |

Both use metres and a unit quaternion ordered (x, y, z, w) in a right-handed frame, so the numbers themselves need no conversion.

**I.5 An empty `FrameId` is never passed through.** §5.12 rule 3 requires a named frame here, while a commanding model may read an empty `FrameId` as its default working frame. A boundary **shall** substitute the named frame explicitly in that direction, and **shall** reject a pose it cannot name rather than guessing.

**I.6 A grasp pose reaches the tool centre point.** A pose published for a robot to act on **shall** be resolvable, through the frame tree, to a frame of role `Tool`. Resolving only to `MechanicalInterface` is not sufficient: the offset between the flange and the tool centre point is exactly what a hand-eye calibration does not measure, and Annex F carries it as a distinct frame for this reason.

**I.7 A manufacturing event is composed, not invented.** A cell wants to know that a part was picked, placed, aligned or rejected. This model deliberately defines no `PickEventType`, and a Server **shall not** publish one under this specification, because **a camera cannot know that a pick happened**. It can report what it saw; the robot is what knows what it did.

So the two halves come from the two models, and a consumer joins them:

| Half | Source | Carries |
|---|---|---|
| The **action** — authoritative | `IntentCompletedEventType` on the commanding model, where the submitted intent was a pick and the terminal state is success | that the robot picked, and what its own result says about the outcome |
| The **observation** — corroborating | `ObjectDetectedEventType` (§7.5) on this model | that an object of a class was seen, where, and with what confidence |

The action alone is sufficient: a robot that reports a successful pick has picked, whatever a camera thinks. The observation adds what the robot cannot supply — which object, at what pose, identified by which model version — and is what makes the event traceable back to a decision under §12.6.

A consumer correlating the two **shall** use the event `Time` of each, which §7.5 fixes as the frame acquisition time on this side, and **shall not** assume the two arrive in that order or in the same notification: they are raised by different objects and, in a Server that implements only one of the two models, one of them does not exist at all. Where the intent named a `Location` and the detection carries a pose, the two **shall** be related through the frame tree of I.1 rather than by comparing coordinates in different frames.

**Correlation on time is only as good as the clocks.** Both models publish `ClockSynchronised` and `TimeSyncSource` on their roots (§7.5). A consumer **shall** read both before correlating on timing, and where either Server reports `false` or omits the member **shall not** attribute a detection to a motion on timing alone — it uses `DecidedBy` instead, which states the link rather than inferring it.

**The link can be stated rather than inferred.** Where the commanding model populates `IntentOperationType.DecidedBy` with the `VisionResultType` instance a pose came from, the correlation stops being a timing argument: a consumer follows the reference from the completion to the result, and from `result.ModelUsed` to the model and digest. `ProducedBy` still identifies the pipeline, whose `Deployment → UsesModel` path shows what is serving now. Together those paths give the historical decision and current configuration without conflating them, and that is what the commanding model's Annex E.8 asks a Server implementing both to do.

The consequence is that the intent vocabulary *is* the manufacturing-event vocabulary. `pick`, `place` and the rest are already named — as intent types the commanding model defines — and a completion event carrying the intent type is what turns each of them into an occurrence a line controller can subscribe to. Nothing further needs to be invented here, and inventing it would produce a second vocabulary that could disagree with the first about what happened.

## Types the prose does not introduce {#sec-types-not-introduced}

The types below are declared by the model. Each clause was generated because no clause of this document named its type; fold them into the prose where they belong.

### OpticsType {#sec-opticstype}

The lens in front of a sensor. Member names are deliberately aligned with the ILensType of OPC 40100-2 so that a Server implementing both models reports one set of values under two vocabularies.

*Table - OpticsType Definition* {#tbl-opticstype-definition defines=OpticsType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:OpticsType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:FocalLength | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Aperture | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:WorkingDistance | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:MinimumWorkingDistance | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Magnification | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:OpticalFormat | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:MountType | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:LensType | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### IlluminationType {#sec-illuminationtype}

A controlled light source associated with a sensor. Member names align with the ILampType and ILightingControllerType of OPC 40100-2.

*Table - IlluminationType Definition* {#tbl-illuminationtype-definition defines=IlluminationType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:IlluminationType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:LampType | 1:VisionLampTypeEnum | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Wavelength | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:RelativeIntensity | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:LightingMode | 1:VisionLightingModeEnum | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Quality | 0:Double | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### MediaEndpointType {#sec-mediaendpointtype}

Abstract base for a media access point. The endpoint DESCRIBES where media can be obtained; on the default path the media itself never traverses OPC UA. Subtypes add the protocol- or format-specific members.

*Table - MediaEndpointType Definition* {#tbl-mediaendpointtype-definition defines=MediaEndpointType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:MediaEndpointType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:EndpointId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:EndpointUri | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:State | 1:VisionEndpointStateEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Authentication | 1:VisionEndpointAuthenticationEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:SecureTransport | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:DefaultProfileName | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:DataChannelSource | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:DataChannelContentType | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### StreamEndpointType {#sec-streamendpointtype}

A continuous media stream. A conformant Server SHALL expose at least one instance whose StreamProtocol is Rtsp; every other protocol is optional. This is the default way to obtain live imagery.

*Table - StreamEndpointType Definition* {#tbl-streamendpointtype-definition defines=StreamEndpointType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:StreamEndpointType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:MediaEndpointType defined in [](#sec-mediaendpointtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 1:StreamProtocol | 1:VisionStreamProtocolEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:ProtocolVersion | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Codec | 1:VisionVideoCodecEnum | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Width | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Height | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:FrameRate | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Bitrate | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:MaxSessions | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:ActiveSessions | 0:UInt32 | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### ClipEndpointType {#sec-clipendpointtype}

A still-image access point. A conformant Server SHALL expose at least one instance whose ClipFormat is Jpeg; every other format is optional. In addition to the default URI path, this type MAY publish the encoded image inline as a ByteString so that clients can Read or Subscribe to it - but only within MaxInlineClipSize, which SHALL NOT exceed the Server's ServerCapabilities.MaxByteStringLength. Inline delivery serves single stills; it is not a substitute for a StreamEndpoint.

*Table - ClipEndpointType Definition* {#tbl-clipendpointtype-definition defines=ClipEndpointType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ClipEndpointType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:MediaEndpointType defined in [](#sec-mediaendpointtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 1:ClipFormat | 1:VisionClipFormatEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Quality | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Width | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Height | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Retention | 0:Duration | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:InlineDeliveryEnabled | 0:Boolean | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:MaxInlineClipSize | 0:UInt32 | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:LatestClip | 0:ByteString | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:LatestClipMetadata | 1:VisionImageReferenceDataType | 0:BaseDataVariableType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### VisionMediaManagementType {#sec-visionmediamanagementtype}

Container and control surface for a sensor's media endpoints. Holds the endpoint folders and the Methods that select, configure and lease them.

*Table - VisionMediaManagementType Definition* {#tbl-visionmediamanagementtype-definition defines=VisionMediaManagementType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionMediaManagementType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasComponent | Object | 1:StreamEndpoints |  | 0:FolderType | M |
| 0:HasComponent | Object | 1:ClipEndpoints |  | 0:FolderType | M |
| 0:HasProperty | Variable | 1:PreferredStreamEndpoint | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:PreferredClipEndpoint | 0:NodeId | 0:PropertyType | O |
| 0:HasComponent | Method | 1:GetStreamEndpoint |  |  | M |
| 0:HasComponent | Method | 1:ReleaseStreamEndpoint |  |  | M |
| 0:HasComponent | Method | 1:ConfigureStreamEndpoint |  |  | O |
| 0:HasComponent | Method | 1:SelectEndpoint |  |  | O |
| 0:HasComponent | Method | 1:GetClip |  |  | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

#### GetStreamEndpoint {#sec-visionmediamanagementtype-getstreamendpoint type=VisionMediaManagementType method=GetStreamEndpoint}

Lease a stream. Returns a session descriptor whose Uri may embed a time-limited credential; the client opens that Uri with the media protocol. The preferred protocol is advisory - the Server returns what it can serve, which is at minimum RTSP.

**Signature**

```text
GetStreamEndpoint (
  [in]  0:NodeId                      Endpoint,
  [in]  0:String                      ProfileName,
  [in]  1:VisionStreamProtocolEnum    PreferredProtocol,
  [out] 1:VisionStreamSessionDataType Session,
  [out] 0:NodeId                      Endpoint);
```

*Table - GetStreamEndpoint Method Arguments* {#tbl-getstreamendpoint-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Endpoint | StreamEndpoint to lease. Null selects PreferredStreamEndpoint, or, when that is also null, the first endpoint in StreamEndpoints in BrowseName order that satisfies the request. |
| ProfileName | Requested profile, or empty for the default. |
| PreferredProtocol | Advisory protocol preference. |
| Session | The leased session. |
| Endpoint | The StreamEndpoint that was leased. |

#### ReleaseStreamEndpoint {#sec-visionmediamanagementtype-releasestreamendpoint type=VisionMediaManagementType method=ReleaseStreamEndpoint}

Release a previously leased stream session. A Server SHALL also expire leases automatically at ExpiresAt.

**Signature**

```text
ReleaseStreamEndpoint (
  [in]  0:ByteString SessionToken);
```

*Table - ReleaseStreamEndpoint Method Arguments* {#tbl-releasestreamendpoint-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| SessionToken | Token from GetStreamEndpoint. |

#### ConfigureStreamEndpoint {#sec-visionmediamanagementtype-configurestreamendpoint type=VisionMediaManagementType method=ConfigureStreamEndpoint}

Change the encoding parameters of a stream endpoint. A Server MAY reject or clamp values it cannot serve; the resulting effective values are readable on the endpoint.

**Signature**

```text
ConfigureStreamEndpoint (
  [in]  0:NodeId               Endpoint,
  [in]  1:VisionVideoCodecEnum Codec,
  [in]  0:UInt32               Width,
  [in]  0:UInt32               Height,
  [in]  0:Double               FrameRate,
  [in]  0:UInt32               Bitrate);
```

*Table - ConfigureStreamEndpoint Method Arguments* {#tbl-configurestreamendpoint-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Endpoint | StreamEndpoint to configure. |
| Codec | Requested codec. |
| Width | Requested width in pixels. |
| Height | Requested height in pixels. |
| FrameRate | Requested frames per second. |
| Bitrate | Requested bitrate in bits per second. |

#### SelectEndpoint {#sec-visionmediamanagementtype-selectendpoint type=VisionMediaManagementType method=SelectEndpoint}

Designate the preferred stream and clip endpoints, updating PreferredStreamEndpoint and PreferredClipEndpoint.

**Signature**

```text
SelectEndpoint (
  [in]  0:NodeId StreamEndpoint,
  [in]  0:NodeId ClipEndpoint);
```

*Table - SelectEndpoint Method Arguments* {#tbl-selectendpoint-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| StreamEndpoint | Preferred stream endpoint, or null to leave unchanged. |
| ClipEndpoint | Preferred clip endpoint, or null to leave unchanged. |

#### GetClip {#sec-visionmediamanagementtype-getclip type=VisionMediaManagementType method=GetClip}

Obtain a still image: either the frame associated with a given ResultId, or the frame nearest a timestamp. The returned descriptor always carries a Uri. The bytes are returned inline only when RequestInline is true AND the encoded image fits MaxInlineClipSize; otherwise InlineImage is empty and the client uses the Uri.

**Signature**

```text
GetClip (
  [in]  0:NodeId                       Endpoint,
  [in]  0:String                       ResultId,
  [in]  0:UtcTime                      Timestamp,
  [in]  1:VisionClipFormatEnum         Format,
  [in]  0:Boolean                      RequestInline,
  [out] 1:VisionImageReferenceDataType Image,
  [out] 0:NodeId                       Endpoint,
  [out] 0:ByteString                   InlineImage);
```

*Table - GetClip Method Arguments* {#tbl-getclip-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Endpoint | ClipEndpoint to use. Null selects PreferredClipEndpoint, or, when that is also null, the first endpoint in ClipEndpoints in BrowseName order that supports Format. |
| ResultId | Result whose frame is wanted, or empty. |
| Timestamp | Frame nearest this time, used when ResultId is empty. |
| Format | Requested encoding; Jpeg is always supported. |
| RequestInline | Ask for the bytes inline in addition to the Uri. |
| Image | Descriptor of the clip. |
| Endpoint | The ClipEndpoint that served the clip. |
| InlineImage | Encoded bytes, or empty when not requested or too large. |

### CoordinateFrameType {#sec-coordinateframetype}

A named coordinate frame. Frames form a tree through ParentFrame, so a client can compose a chain from a camera frame to a world frame. Roles follow ISO 9787, which standardises WHICH frames exist - note that no standard defines how to CALIBRATE between them, which is why ExtrinsicCalibrationType carries the result explicitly.

*Table - CoordinateFrameType Definition* {#tbl-coordinateframetype-definition defines=CoordinateFrameType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:CoordinateFrameType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:FrameId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Role | 1:VisionFrameRoleEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:ParentFrame | 0:NodeId | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:Transform | 1:VisionPose3DDataType | 0:BaseDataVariableType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### VisionCalibrationType {#sec-visioncalibrationtype}

Abstract base for a calibration result, carrying the provenance a client needs in order to decide whether to trust it.

*Table - VisionCalibrationType Definition* {#tbl-visioncalibrationtype-definition defines=VisionCalibrationType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionCalibrationType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:CalibrationId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:PerformedAt | 0:UtcTime | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Valid | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:ResidualError | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Method | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### IntrinsicCalibrationType {#sec-intrinsiccalibrationtype}

Camera intrinsics and lens distortion for a specific image size.

*Table - IntrinsicCalibrationType Definition* {#tbl-intrinsiccalibrationtype-definition defines=IntrinsicCalibrationType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:IntrinsicCalibrationType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:VisionCalibrationType defined in [](#sec-visioncalibrationtype) |  |  |  |  |  |
| 0:HasComponent | Variable | 1:Intrinsics | 1:VisionIntrinsicsDataType | 0:BaseDataVariableType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### ExtrinsicCalibrationType {#sec-extrinsiccalibrationtype}

The rigid transform between two frames. For a robot cell this is the hand-eye calibration. No ISO, IEC or VDI standard defines the calibration PROCEDURE, so this type carries the resulting transform, the mounting arrangement it applies to, and its residual, which is what a consumer actually needs.

*Table - ExtrinsicCalibrationType Definition* {#tbl-extrinsiccalibrationtype-definition defines=ExtrinsicCalibrationType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ExtrinsicCalibrationType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:VisionCalibrationType defined in [](#sec-visioncalibrationtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 1:Mount | 1:VisionCalibrationMountEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:SourceFrame | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:TargetFrame | 0:NodeId | 0:PropertyType | M |
| 0:HasComponent | Variable | 1:Transform | 1:VisionPose3DDataType | 0:BaseDataVariableType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

### VisionFeedbackType {#sec-visionfeedbacktype}

The return path into the vision system. It serves three purposes at once: drawing geometry onto the outgoing stream, recording a downstream verdict against a result, and - most importantly - accepting corrected labels that become training data. That last purpose is what turns a deployed inspection system into a learning one. Every Method here is a WRITE and requires explicit authorization.

*Table - VisionFeedbackType Definition* {#tbl-visionfeedbacktype-definition defines=VisionFeedbackType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionFeedbackType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:OverlayEnabled | 0:Boolean | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:OverlayStyle | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:OverlayTtl | 0:Duration | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:MaxInlineFeedbackImageSize | 0:UInt32 | 0:PropertyType | O |
| 0:HasComponent | Method | 1:SubmitDetections |  |  | O |
| 0:HasComponent | Method | 1:SubmitInspectionResult |  |  | O |
| 0:HasComponent | Method | 1:SubmitCorrection |  |  | O |
| 0:HasComponent | Method | 1:SubmitImageReference |  |  | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision |  |  |  |  |  |

#### SubmitDetections {#sec-visionfeedbacktype-submitdetections type=VisionFeedbackType method=SubmitDetections}

Push detected geometry back into the vision system. With Purpose set to Overlay the boxes are drawn on the stream; with Purpose set to GroundTruthLabel they are retained as corrected labels for the associated learning job.

**Signature**

```text
SubmitDetections (
  [in]  1:VisionFeedbackPurposeEnum    Purpose,
  [in]  1:VisionDetectionDataType[]    Detections,
  [in]  1:VisionImageReferenceDataType FrameReference,
  [in]  0:ByteString                   InlineImage,
  [in]  0:Boolean                      SceneIsEmpty);
```

*Table - SubmitDetections Method Arguments* {#tbl-submitdetections-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Purpose | Why the geometry is being sent. |
| Detections | The detections. |
| FrameReference | Frame the detections belong to. |
| InlineImage | Optional annotated image, accepted only within MaxInlineFeedbackImageSize; otherwise use SubmitImageReference. |
| SceneIsEmpty | True asserts that the frame was examined and contains nothing to report, which is a deliberate observation and not a failed one. It is the only way Detections may be empty: an empty array with this false is rejected, so a call that lost its payload is still caught. False with a non-empty Detections is the ordinary case. Last in the list because argument order is part of the wire contract. See clause 9.5. |

#### SubmitInspectionResult {#sec-visionfeedbacktype-submitinspectionresult type=VisionFeedbackType method=SubmitInspectionResult}

Record a downstream inspection verdict against a result, for reconciliation with what the vision system originally reported.

**Signature**

```text
SubmitInspectionResult (
  [in]  0:String                         ResultId,
  [in]  1:VisionResultEvaluationEnum     Evaluation,
  [in]  1:VisionCharacteristicDataType[] Characteristics);
```

*Table - SubmitInspectionResult Method Arguments* {#tbl-submitinspectionresult-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| ResultId | Result being reconciled. |
| Evaluation | Downstream verdict. |
| Characteristics | Downstream measurements, where available. |

#### SubmitCorrection {#sec-visionfeedbacktype-submitcorrection type=VisionFeedbackType method=SubmitCorrection}

Submit a human-in-the-loop or downstream correction of a previous result. This is the primary source of labelled data for retraining.

**Signature**

```text
SubmitCorrection (
  [in]  0:String                         ResultId,
  [in]  1:VisionFeedbackPurposeEnum      Purpose,
  [in]  1:VisionDetectionDataType[]      CorrectedDetections,
  [in]  1:VisionCharacteristicDataType[] CorrectedCharacteristics,
  [in]  0:LocalizedText                  Reason,
  [in]  0:ByteString                     InlineImage,
  [in]  0:Boolean                        RetractAll);
```

*Table - SubmitCorrection Method Arguments* {#tbl-submitcorrection-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| ResultId | Result being corrected. |
| Purpose | Normally GroundTruthLabel. |
| CorrectedDetections | Corrected detections, where the result was a detection. |
| CorrectedCharacteristics | Corrected characteristics, where the result was an inspection. |
| Reason | Why the correction was made. |
| InlineImage | Optional corrected or annotated image, accepted only within MaxInlineFeedbackImageSize; otherwise use SubmitImageReference. |
| RetractAll | True asserts that the corrected result should contain nothing at all - every detection or characteristic it reported was a false positive and nothing replaces it. It is the only way both corrected arrays may be empty. This is the most valuable correction shape for a learning loop, because a false positive is the error an operator is most able to label with confidence. Last in the list because argument order is part of the wire contract. See clause 9.5. |

#### SubmitImageReference {#sec-visionfeedbacktype-submitimagereference type=VisionFeedbackType method=SubmitImageReference}

The default way to hand an image back: by reference. Used whenever the image exceeds MaxInlineFeedbackImageSize, and preferred in all cases.

**Signature**

```text
SubmitImageReference (
  [in]  1:VisionFeedbackPurposeEnum    Purpose,
  [in]  1:VisionImageReferenceDataType Image,
  [in]  0:String                       ResultId);
```

*Table - SubmitImageReference Method Arguments* {#tbl-submitimagereference-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Purpose | Why the image is being sent. |
| Image | Descriptor of the image. |
| ResultId | Associated result, or empty. |

### VisionEventType {#sec-visioneventtype}

Abstract base of every event this model raises. It adds to BaseEventType the provenance a vision event needs to be actionable: which result substantiates it, which sensor and pipeline produced it, which model version decided, and how far the answer can be trusted. Time is inherited from BaseEventType and clause 7.5 fixes what it means here.

*Table - VisionEventType Definition* {#tbl-visioneventtype-definition defines=VisionEventType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionEventType |  |  |  |  |
| IsAbstract | True |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseEventType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:ResultId | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Sensor | 0:NodeId | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:GroundTruth | 0:Boolean | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:Pipeline | 0:NodeId | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:ModelVersionUsed | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Confidence | 0:Double | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:InferenceEndTime | 0:UtcTime | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision Events |  |  |  |  |  |

### ObjectDetectedEventType {#sec-objectdetectedeventtype}

One detected instance, raised once per entry in a DetectionResultType's Detections. One event per detection rather than one per result is what makes the class and the confidence available to an EventFilter, so a client asks for the two classes it cares about above a confidence it chooses and the Server sends nothing else. A per-result event would move that filtering to the client and give up most of the reason to use events at all.

*Table - ObjectDetectedEventType Definition* {#tbl-objectdetectedeventtype-definition defines=ObjectDetectedEventType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ObjectDetectedEventType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:VisionEventType defined in [](#sec-visioneventtype) |  |  |  |  |  |
| 0:HasComponent | Variable | 1:Detection | 1:VisionDetectionDataType | 0:BaseDataVariableType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision Events |  |  |  |  |  |

### InspectionCompletedEventType {#sec-inspectioncompletedeventtype}

An inspection reached a verdict. Raised once per InspectionResultType, because an inspection concludes once - unlike detection, where a single frame yields many independent findings.

*Table - InspectionCompletedEventType Definition* {#tbl-inspectioncompletedeventtype-definition defines=InspectionCompletedEventType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:InspectionCompletedEventType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 1:VisionEventType defined in [](#sec-visioneventtype) |  |  |  |  |  |
| 0:HasProperty | Variable | 1:Evaluation | 1:VisionResultEvaluationEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:PartId | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:RecipeId | 0:String | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:FailedCharacteristics | 1:VisionCharacteristicDataType[] | 0:BaseDataVariableType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision Events |  |  |  |  |  |

### VisionRealityKindEnum {#sec-visionrealitykindenum}

Whether the sensor observes the physical world, a simulation, or both. This is the sim/real switch: every other member of the model means the same thing regardless of its value.

*Table - VisionRealityKindEnum Definition* {#tbl-visionrealitykindenum-definition defines=VisionRealityKindEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionRealityKindEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[3] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionStreamProtocolEnum {#sec-visionstreamprotocolenum}

Wire protocol of a continuous media stream. Rtsp is the mandatory default: a conformant Server exposes at least one StreamEndpoint using it.

*Table - VisionStreamProtocolEnum Definition* {#tbl-visionstreamprotocolenum-definition defines=VisionStreamProtocolEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionStreamProtocolEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[9] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionClipFormatEnum {#sec-visionclipformatenum}

Encoding of a still clip. Jpeg is the mandatory default: a conformant Server exposes at least one ClipEndpoint using it.

*Table - VisionClipFormatEnum Definition* {#tbl-visionclipformatenum-definition defines=VisionClipFormatEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionClipFormatEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[7] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionVideoCodecEnum {#sec-visionvideocodecenum}

Codec carried by a stream endpoint.

*Table - VisionVideoCodecEnum Definition* {#tbl-visionvideocodecenum-definition defines=VisionVideoCodecEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionVideoCodecEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[6] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionEndpointStateEnum {#sec-visionendpointstateenum}

Runtime lifecycle state of a media endpoint or deployment.

*Table - VisionEndpointStateEnum Definition* {#tbl-visionendpointstateenum-definition defines=VisionEndpointStateEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionEndpointStateEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[5] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionEndpointAuthenticationEnum {#sec-visionendpointauthenticationenum}

Authentication a client must present to the media endpoint. This is the media-plane credential, independent of the OPC UA session.

*Table - VisionEndpointAuthenticationEnum Definition* {#tbl-visionendpointauthenticationenum-definition defines=VisionEndpointAuthenticationEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionEndpointAuthenticationEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[5] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionResultEvaluationEnum {#sec-visionresultevaluationenum}

Overall verdict of a result. Value semantics are aligned with the ResultEvaluationEnum of OPC 40001-101 so that a client already consuming Machinery results needs no new interpretation rules.

*Table - VisionResultEvaluationEnum Definition* {#tbl-visionresultevaluationenum-definition defines=VisionResultEvaluationEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionResultEvaluationEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[4] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionToleranceStatusEnum {#sec-visiontolerancestatusenum}

Per-characteristic tolerance outcome.

*Table - VisionToleranceStatusEnum Definition* {#tbl-visiontolerancestatusenum-definition defines=VisionToleranceStatusEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionToleranceStatusEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[3] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionFeedbackPurposeEnum {#sec-visionfeedbackpurposeenum}

Why a client is pushing information back into the vision system.

*Table - VisionFeedbackPurposeEnum Definition* {#tbl-visionfeedbackpurposeenum-definition defines=VisionFeedbackPurposeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionFeedbackPurposeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[4] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionCalibrationMountEnum {#sec-visioncalibrationmountenum}

Physical relationship between a camera and the kinematic chain it is calibrated against.

*Table - VisionCalibrationMountEnum Definition* {#tbl-visioncalibrationmountenum-definition defines=VisionCalibrationMountEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionCalibrationMountEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[4] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionFrameRoleEnum {#sec-visionframeroleenum}

Role of a coordinate frame, following the ISO 9787 frame vocabulary. The mechanical interface and the tool are DISTINCT roles: a camera on a robot flange is calibrated to the mechanical interface, while a pick pose has to reach the tool centre point, and a model that cannot tell them apart cannot express the offset between them.

*Table - VisionFrameRoleEnum Definition* {#tbl-visionframeroleenum-definition defines=VisionFrameRoleEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionFrameRoleEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[7] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionDistortionModelEnum {#sec-visiondistortionmodelenum}

Lens distortion model the coefficients belong to.

*Table - VisionDistortionModelEnum Definition* {#tbl-visiondistortionmodelenum-definition defines=VisionDistortionModelEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionDistortionModelEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[5] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionSensorModalityEnum {#sec-visionsensormodalityenum}

What the sensor measures.

*Table - VisionSensorModalityEnum Definition* {#tbl-visionsensormodalityenum-definition defines=VisionSensorModalityEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionSensorModalityEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[7] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionLampTypeEnum {#sec-visionlamptypeenum}

Emitter technology of a light source. The named values are those OPC 40100-2 gives as examples for ILampType.LampType, which is a free String there.

*Table - VisionLampTypeEnum Definition* {#tbl-visionlamptypeenum-definition defines=VisionLampTypeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionLampTypeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[6] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionLightingModeEnum {#sec-visionlightingmodeenum}

How a light source is being driven. The named values are those OPC 40100-2 gives as examples for ILightingControllerType.LightingMode, which is an unconstrained UInt32 there.

*Table - VisionLightingModeEnum Definition* {#tbl-visionlightingmodeenum-definition defines=VisionLightingModeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionLightingModeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[4] | 0:PropertyType | M |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionPose3DDataType {#sec-visionpose3ddatatype}

A rigid-body pose expressed in a named coordinate frame. Position is metres; Orientation is a unit quaternion ordered (x, y, z, w). Covariance is an optional row-major 6x6 matrix over (x, y, z, rx, ry, rz); an empty array means the uncertainty is not reported.

*Table - VisionPose3DDataType Definition* {#tbl-visionpose3ddatatype-definition defines=VisionPose3DDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionPose3DDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionBoundingBox2DDataType {#sec-visionboundingbox2ddatatype}

A box in image space. The origin is the top-left pixel; Rotation is degrees clockwise about the box centre, so 0 denotes an axis-aligned box.

*Table - VisionBoundingBox2DDataType Definition* {#tbl-visionboundingbox2ddatatype-definition defines=VisionBoundingBox2DDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionBoundingBox2DDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionBoundingBox3DDataType {#sec-visionboundingbox3ddatatype}

An oriented box in three-dimensional space, given by a centre pose and an extent.

*Table - VisionBoundingBox3DDataType Definition* {#tbl-visionboundingbox3ddatatype-definition defines=VisionBoundingBox3DDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionBoundingBox3DDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionImageReferenceDataType {#sec-visionimagereferencedatatype}

A reference to image bytes that are NOT carried in the OPC UA payload. This is the default way results point at imagery: the Uri is resolved out-of-band, typically through a ClipEndpoint, and verified against Digest.

*Table - VisionImageReferenceDataType Definition* {#tbl-visionimagereferencedatatype-definition defines=VisionImageReferenceDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionImageReferenceDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionIntrinsicsDataType {#sec-visionintrinsicsdatatype}

Pinhole intrinsics plus a distortion model, in pixel units, valid for the stated image size. For a simulated sensor these are derived from the USD camera aperture and focal-length attributes.

*Table - VisionIntrinsicsDataType Definition* {#tbl-visionintrinsicsdatatype-definition defines=VisionIntrinsicsDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionIntrinsicsDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionDetectionDataType {#sec-visiondetectiondatatype}

One detected instance. This is the robotics-vision payload: a class, a score, and enough geometry to act on - a 2-D box for image-space work, a 3-D box and a 6-DoF pose for picking and visual servoing. Field naming follows the ROS 2 vision_msgs conventions so that a bridge is mechanical.

*Table - VisionDetectionDataType Definition* {#tbl-visiondetectiondatatype-definition defines=VisionDetectionDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionDetectionDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionCharacteristicDataType {#sec-visioncharacteristicdatatype}

One measured characteristic of an inspected part. This is the machine-vision payload, and the field set deliberately mirrors QIF (ISO 23952) Results, including measurement uncertainty, so that a QIF document can be produced from it without inventing information.

*Table - VisionCharacteristicDataType Definition* {#tbl-visioncharacteristicdatatype-definition defines=VisionCharacteristicDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionCharacteristicDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### VisionStreamSessionDataType {#sec-visionstreamsessiondatatype}

A leased media session. The Uri may embed a single-use or time-limited credential, which is why it is returned by a Method rather than published as a browsable Variable.

*Table - VisionStreamSessionDataType Definition* {#tbl-visionstreamsessiondatatype-definition defines=VisionStreamSessionDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:VisionStreamSessionDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision DataTypes |  |  |  |  |  |

### HasCalibration {#sec-hascalibration}

Links a sensor to a calibration currently valid for it.

*Table - HasCalibration Definition* {#tbl-hascalibration-definition defines=HasCalibration}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:HasCalibration |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:NonHierarchicalReferences defined in OPC 10000-5 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision ReferenceTypes |  |  |  |  |  |

### MountedOn {#sec-mountedon}

Links a sensor to the CoordinateFrame it is rigidly mounted on, for example a robot flange frame for an eye-in-hand camera.

*Table - MountedOn Definition* {#tbl-mountedon-definition defines=MountedOn}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:MountedOn |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:NonHierarchicalReferences defined in OPC 10000-5 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision ReferenceTypes |  |  |  |  |  |

### HasScenePrim {#sec-hassceneprim}

Links a sensor to the materialized USD prim representing it, when the Server also implements OPC UA - OpenUSD Scene Materialization. The target is expected to be a UsdGeomCameraType instance. Optional: PrimPath remains the portable descriptor.

*Table - HasScenePrim Definition* {#tbl-hassceneprim-definition defines=HasScenePrim}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:HasScenePrim |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:NonHierarchicalReferences defined in OPC 10000-5 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision ReferenceTypes |  |  |  |  |  |

### ProducedBy {#sec-producedby}

Links a result to the inference pipeline that produced it.

*Table - ProducedBy Definition* {#tbl-producedby-definition defines=ProducedBy}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ProducedBy |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:NonHierarchicalReferences defined in OPC 10000-5 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Vision ReferenceTypes |  |  |  |  |  |
