# OPC UA Robotics — Vision Addendum

**Implementer annex to *OPC UA — Vision* (Release 0.2.0 — Draft).**

> A worked example of vision-guided robotics: an eye-in-hand 3D camera on a robot flange detects parts in a bin and publishes 6-DoF pick poses, with inference running off-server on an edge GPU and a simulated twin sensor rendering the same cell in NVIDIA Isaac Sim. The machine-readable source of truth is [`Robotics.Vision.json`](../../../../metaverse-specs/extras/vision/examples/robotics/Robotics.Vision.json); this document and `Opc.Ua.Robotics.Vision.NodeSet2.xml` are both generated from it by `build_examples.py`, so prose and model cannot drift. It is also published as Annex F of [`OPC-UA-Vision.md`](../spec.md).

---

## 1 Scope

This worked example binds one eye-in-hand camera to a robot flange frame and shows the full perception path: a hand-eye `ExtrinsicCalibrationType` that makes poses actionable, a `DetectionResultType` carrying 6-DoF grasp poses in a named frame, an off-server GPU deployment, and an RTSP stream with detection overlay feedback. It is the case OPC UA has no coverage for today: OPC 40010-1 Robotics contains no vision, camera, perception or calibration types at all, and neither it nor OPC 40100 references the other.

## 2 Normative references

- *OPC UA — Vision*, Release 0.2.0 (the base specification), `../spec.md`.
- [OPC 40010-1](https://reference.opcfoundation.org/specs/OPC-40010-1/) — OPC UA for Robotics, whose `MotionDeviceSystemType` describes the robot this camera is mounted on. Not a dependency of this model.
- ISO 9787:2013 — coordinate systems, the source of the frame roles used here.
- ROS 2 `vision_msgs` — the convention `VisionDetectionDataType` field naming follows.

## 3 The sensor

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

## 4 Media endpoints

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

## 5 Coordinate frames and calibration

The frame tree. `ParentFrame` is what makes it composable: a client walks from the frame a pose is expressed in up to the frame it needs, composing the transforms it finds on the way.

| Instance | `FrameId` | `Role` | `ParentFrame` |
|---|---|---|---|
| `WorldFrame` | `world` | `World` | none (tree root) |
| `RobotBaseFrame` | `robot_base` | `Base` | `world` |
| `FlangeFrame` | `flange` | `Tool` | `robot_base` |
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
| `Cx` | `1223.1` | px, corner-datum per 5.10 |
| `Cy` | `1021.7` | px, corner-datum per 5.10 |
| `Skew` | `0.0` | px |
| `DistortionModel` | `BrownConrady` | 5.10 ordering: k1, k2, p1, p2, k3 |
| `DistortionCoefficients` | `[-0.1721, 0.0934, 0.0002, -0.0001, -0.0188]` | dimensionless |
| `Width` | `2448` | px |
| `Height` | `2048` | px |

**`HandEye`** (`ExtrinsicCalibrationType`) — Transform from the camera frame to the robot flange frame. Eye-in-hand: the camera moves with the tool.

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
| `FrameId` | `flange` | equals the TargetFrame's FrameId, per the 5.10 frame-precedence rule |
| `Position` | `(0.062, -0.031, 0.115)` | metres, ordered (x, y, z) |
| `Orientation` | `(0.0, 0.0, 0.7071, 0.7071)` | unit quaternion ordered (x, y, z, w) |
| `Covariance` | `empty array` | not reported, per the 5.10 sentinel |

Each calibration is reachable from the sensor by a `HasCalibration` reference, as base specification §5.11 requires.

## 6 The simulated twin

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

## 7 Inference

| Member | Value |
|---|---|
| Model | `GraspPoseNet` v`3.2.0` (TensorRT) |
| `TaskKind` | `PoseEstimation` |
| `InferenceLocation` | **`EdgeOffServer`** |
| `AcceleratorKind` | `Gpu` |
| `EndpointUri` | `grpcs://192.0.2.60:8001/graspposenet` |

Inference runs **off-server** on a cell-side GPU appliance. The Server publishes results it did not compute. Nothing else in the model changes: a client reads `DetectionResultType` exactly as it would if `InferenceLocation` were `OnServer`, and consults that property only if it cares about the latency or trust boundary. Because the deployment is remote, base specification §12.6 applies: the channel to the inference service is authenticated and integrity-protected, and `AiModelType.Digest` lets a consumer confirm which artefact produced a result.

The deployment carries exactly one `UsesModel` reference to the model above, as base specification §5.11 requires. That reference is the only defined path from a result to the model artefact and its `Digest`, so it is what makes the §12.6 provenance check possible.

## 8 Results

Each cycle produces a `DetectionResultType` whose `Detections` carry `ClassLabel`, `Confidence`, a `BoundingBox2D`, a `BoundingBox3D` and — the member that makes the result actionable — a 6-DoF `Pose`. Every pose names its `FrameId` (`camera_eih`), which is only meaningful because the `HandEye` calibration above relates that frame to the flange. A consumer composes camera → flange → base through the `CoordinateFrameType` tree to obtain a pose the robot controller can execute. `ResidualError` on the calibration is what tells the consumer how much to trust it.

## 9 Feedback

Two feedback paths are exercised. During commissioning, the HMI calls `SubmitDetections` with `Purpose = Overlay` so the operator sees candidate grasps drawn on the RTSP stream. In production, a failed pick calls `SubmitCorrection` with `Purpose = GroundTruthLabel`, and the corrected pose is retained by the `LearningJobType` as a labelled sample — so the cases the model gets wrong are exactly the cases the next dataset contains. Feedback images are passed by reference through `SubmitImageReference`; this example does not enable inline feedback images.

## 10 Deliverables

| File | Content |
|---|---|
| [`Robotics.Vision.json`](../../../../metaverse-specs/extras/vision/examples/robotics/Robotics.Vision.json) | Machine-readable descriptor (single source). |
| [`Opc.Ua.Robotics.Vision.NodeSet2.xml`](../../../../model/metaverse-specs/vision/Opc.Ua.Robotics.Vision.NodeSet2.xml) | The generated instance overlay. |

Regenerate from the repository root with `python metaverse-specs/extras/vision/tools/build_examples.py`.
