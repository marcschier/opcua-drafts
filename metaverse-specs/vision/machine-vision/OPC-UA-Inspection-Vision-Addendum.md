# OPC UA Inspection — Vision Addendum

**Implementer annex to *OPC UA — Vision* (Release 0.1.0 — Draft).**

> A worked example of machine-vision inspection: a fixed camera measures a sealing surface, on-server inference produces a verdict with QIF-shaped characteristics including measurement uncertainty, and each result carries a subscribable JPEG thumbnail through the optional size-gated inline delivery facet. The machine-readable source of truth is [`Inspection.Vision.json`](../../extras/vision/examples/machine-vision/Inspection.Vision.json); this document and `Opc.Ua.Inspection.Vision.NodeSet2.xml` are both generated from it by `build_examples.py`, so prose and model cannot drift.

---

## 1 Scope

This addendum shows the case OPC 40100-1 orchestrates but does not describe: the *content* of an inspection result. A fixed area-scan camera inspects a sealing surface; the result is an `InspectionResultType` carrying an `Evaluation` and a set of `VisionCharacteristicDataType` entries with nominal, actual, deviation, tolerances and uncertainty. It also demonstrates the optional **Media Inline Delivery** facet: a small JPEG thumbnail is published as `LatestClip` and can be subscribed to with a MonitoredItem, while the full-resolution image stays behind a URI.

## 2 Normative references

- *OPC UA — Vision*, Release 0.1.0 (the base specification), `../OPC-UA-Vision.md`.
- [OPC 40100-1](https://reference.opcfoundation.org/specs/OPC-40100-1/) — OPC UA for Machine Vision Part 1, whose `ResultContent` this example populates. Not a dependency of this model.
- ISO 23952:2020 (QIF) — the shape `VisionCharacteristicDataType` mirrors.
- ISO 14253 — the uncertainty semantics used by `Uncertainty` and `NotDecidable`.

## 3 The sensor

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

## 4 Media endpoints

Both mandatory defaults of base specification §6.2 are present — an RTSP stream and a JPEG clip endpoint:

| Endpoint | Type | Key members |
|---|---|---|
| `LiveRtsp` | `StreamEndpointType` | `StreamProtocol = Rtsp`, `EndpointUri = rtsp://192.0.2.77:554/setup` |
| `PartFrames` | `ClipEndpointType` | `ClipFormat = Jpeg`, `EndpointUri = https://192.0.2.77/clips/{resultId}.jpg` |

This clip endpoint additionally enables the optional **Media Inline Delivery** facet, with `MaxInlineClipSize = 262144` bytes. A client may subscribe to `LatestClip` and receive the encoded JPEG directly; if an image exceeds that bound the Server sets `Bad_EncodingLimitsExceeded` and the client falls back to `LatestClipMetadata.Uri` (base specification §6.4).

## 5 Inference

| Member | Value |
|---|---|
| Model | `SealDefectNet` v`1.4.1` (ONNX) |
| `TaskKind` | `Segmentation` |
| `InferenceLocation` | **`OnServer`** |
| `AcceleratorKind` | `Npu` |

Inference runs **on-server**: `InferenceLocation = OnServer`, on an NPU in the station industrial PC. A client consuming the results cannot distinguish this from the off-server robotics example except by reading that one property — which is the intent of base specification §8.2. Because the pipeline is not continuous, `RunInference` is called per part by the station PLC and returns the `ResultId` it produced.

## 6 Results

Each part produces an `InspectionResultType`. `Evaluation` uses the OPC 40001-101 value semantics, and the `Characteristics` array carries one `VisionCharacteristicDataType` per measured feature — for example a flatness with `Nominal = 0.0`, `Actual = 0.018`, `UpperTolerance = 0.020`, `Unit = mm` and `Uncertainty = 0.004`. That last field is the point: because the expanded uncertainty spans the tolerance limit, the Server reports `NotDecidable` rather than asserting `Ok` from the point estimate alone. A verdict recorded this way is reproducible by a third party, and a QIF document can be generated from it without inventing information.

## 7 Feedback

When a quality engineer overrides a verdict at the review station, the HMI calls `SubmitCorrection` with `Purpose = GroundTruthLabel`, passing the corrected characteristics and a reason. Because this endpoint enables inline delivery, the corrected thumbnail may accompany the call as an inline `ByteString` provided it fits `MaxInlineFeedbackImageSize`; anything larger is rejected with `Bad_EncodingLimitsExceeded` and resubmitted through `SubmitImageReference`. Downstream leak-test results arrive through `SubmitInspectionResult`, which reconciles a downstream `Evaluation` and its characteristics against what the vision system originally reported — and the disagreements are precisely the samples the next `LearningJobType` collects.

## 8 Deliverables

| File | Content |
|---|---|
| [`Inspection.Vision.json`](../../extras/vision/examples/machine-vision/Inspection.Vision.json) | Machine-readable descriptor (single source). |
| [`Opc.Ua.Inspection.Vision.NodeSet2.xml`](Opc.Ua.Inspection.Vision.NodeSet2.xml) | The generated instance overlay. |

Regenerate from the repository root with `python metaverse-specs/extras/vision/tools/build_examples.py`.
