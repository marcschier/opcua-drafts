# External Result Mapping for Vision and AI

> Informative, transport-neutral guidance for mapping externally stored results
> to OPC UA Vision 0.5.0 and AI Model Management and Inference 0.6.0. This is
> not a conformance profile and introduces no requirements on either
> specification.

This document describes a semantic boundary, not a wire envelope. An
implementation can use a database row, an object-store manifest, an HTTP
representation, or another application contract. It should preserve the
distinctions below while using the normative definitions in
<!-- release-spec-link:W1Zpc2lvbl0odmlzaW9uL3NwZWMubWQp -->[Vision](https://github.com/OPCF-Members/spec-drafts/blob/main/source/metaverse-specs/vision/spec.md)<!-- /release-spec-link --> and
<!-- release-spec-link:W0FJIE1vZGVsIE1hbmFnZW1lbnRdKGFpLW1vZGVsLW1hbmFnZW1lbnQvc3BlYy5tZCk= -->[AI Model Management](https://github.com/OPCF-Members/spec-drafts/blob/main/source/metaverse-specs/ai-model-management/spec.md)<!-- /release-spec-link -->.
Where this guide and a normative clause differ, the normative clause governs.

## 1. Identity and a live locator

The durable external identity of a Vision result is the pair:

| Semantic field | Source | Meaning |
|---|---|---|
| `ApplicationUri` | The OPC UA Server application's `ApplicationUri` | Globally identifies the application that assigned the result identifier |
| `ResultId` | `VisionResultType.ResultId` | Identifies the result within that Server application |

`ResultId` alone is not globally unique. An endpoint URL is routing
information and is not application identity: certificates, DNS names, ports,
and discovery URLs can change while the application remains the same.

An external record may also retain a live locator:

| Locator component | Guidance |
|---|---|
| Endpoint URL | Optional current route used to establish an OPC UA connection |
| Application identity | The expected `ApplicationUri`; verify it when connecting |
| Result NodeId | Store the namespace URI plus identifier type and identifier value |

Do not persist a namespace index such as `ns=4`; indexes are assigned per
Server namespace table and may change after restart or redeployment. Persist a
namespace-stable representation equivalent to an `ExpandedNodeId` whose
namespace is a URI. The endpoint, expected `ApplicationUri`, and
namespace-stable NodeId together locate a live result without confusing route,
application, and node identity.

Vision defines bounded retention of result Objects in §7.1.1. After deterministic
eviction, the live NodeId no longer resolves and the result is no longer
browsable under the pipeline's bounded `Results` collection. The external
`(ApplicationUri, ResultId)` identity remains valid for the external record;
it does not promise that the OPC UA Object still exists. An external system
that needs a durable snapshot must copy the fields it needs while the result is
retained. It must not treat a broken live locator as proof that the external
record never existed.

Result retention is distinct from media retention. Evicting a result Object
does not assert that its acquisition image or segmentation mask URI remains
fetchable, and expiry of media does not by itself evict the result. Vision
§§6.1–6.6 define media endpoints and image references; Vision §7.1.1 defines
result retention.

## 2. Optional OPC UA links

External stores commonly retain links as nullable semantic slots. When a live
OPC UA target is stored, use the locator rules above rather than a namespace
index.

| External link | OPC UA source | Interpretation |
|---|---|---|
| Vision result | The concrete `VisionResultType` Object | Live source record |
| Sensor | `VisionResultType.Sensor` | Sensor that supplied the observation |
| Pipeline | `VisionResultType.Pipeline` | Vision processing pipeline |
| Deployment | `InferencePipelineType.Deployment` | Deployment currently bound to the pipeline |
| Actual model | `VisionResultType.ModelUsed` | Model that actually produced this historical result |
| Asynchronous inference job | The `InferenceJobType` returned by `InvokeAsync` | AI job that retained the asynchronous response and `ModelUsed` |

These links are optional in an external contract. A missing link means
unavailable or not represented; it is not permission to infer a target from a
name. In particular, never replace historical `ModelUsed` with
`pipeline.Deployment → UsesModel`. AI §§6.5, 8.2.1, and 12.1 define
`UsesModel` as current serving state and `ModelUsed` as invocation-time
identity. Vision §7.1 applies that historical meaning to a retained result.

## 3. Common result fields

Map the common `VisionResultType` members before mapping a concrete result:

| External concept | Vision member | Mapping note |
|---|---|---|
| Result identifier | `ResultId` | Combine with `ApplicationUri` externally |
| Result creation time | `CreationTime` | Do not substitute frame acquisition time |
| Acquisition image | `Frame` | Map as described in §4.5 |
| Producing sensor and pipeline | `Sensor`, `Pipeline` | Optional links, not copied names |
| Actual model and version | `ModelUsed`, `ModelVersionUsed` | Preserve both when present; Vision §7.1 defines their consistency |
| Result confidence | `Confidence` | Result-level confidence only |
| Explanation | `ExplanationUri` | A reference to explanatory material, not an image or model artifact |

The concrete result determines which typed payload follows. Do not flatten all
result kinds into an untyped bag: inspection characteristics, detections, and
segmentation masks make different claims.

## 4. Typed mappings

### 4.1 Inspection

Map `InspectionResultType` according to Vision §7.2:

| External concept | Vision source |
|---|---|
| Overall verdict | `Evaluation` |
| Part and recipe identifiers | `PartId`, `RecipeId` |
| Measurements | `Characteristics[]` |
| Per-measurement values | `CharacteristicId`, `Name`, `Nominal`, `Actual`, `Deviation`, tolerances, `Unit`, `Uncertainty`, and `Status` |

Keep `Undefined`, `Ok`, `NotOk`, and `NotDecidable` distinct. Do not collapse
`NotDecidable` into failure or success. Preserve uncertainty and its sentinel;
Vision §§5.12 and 7.2 define the coverage factor and the reproducible verdict
rules. This inspection `Evaluation` is a production verdict. It is not an AI
`EvaluationRunType`, which records model qualification metrics (AI §11.2).

### 4.2 Detection

Map each `VisionDetectionDataType` in `DetectionResultType.Detections` according
to Vision §7.3:

| External concept | Vision source |
|---|---|
| Detection identity and class | `DetectionId`, `ClassLabel`, `ClassId` |
| Detection confidence | `Confidence` |
| Tracking identity | `TrackId` |
| 2-D geometry | `HasBoundingBox2D`, `BoundingBox2D` |
| 3-D geometry | `HasBoundingBox3D`, `BoundingBox3D` |
| Pose | `HasPose`, `Pose` |

Honor each `Has…` field. Default-encoded geometry is not present geometry.
Vision §5.12 defines pixels, origin, rotation, metres, array order, and
structure optionality; an external mapping must not silently change those
conventions.

### 4.3 Pose and covariance

Map `VisionPose3DDataType` as one coherent value:

- retain `FrameId`;
- retain `Position` in metres ordered `(x, y, z)`;
- retain the normalized quaternion ordered `(x, y, z, w)`;
- retain `Covariance` as the row-major 6×6 matrix over
  `(x, y, z, rx, ry, rz)`, with rotational terms in radians.

An empty covariance array means *not reported*, not zero uncertainty. Do not
create a covariance matrix when none was published. Vision §§5.8 and 5.12
define frame resolution, transform direction, handedness, and pose validity.

### 4.4 Segmentation

Map `SegmentationResultType` according to Vision §7.4:

| External concept | Vision source |
|---|---|
| Encoded mask | `Mask` (`VisionImageReferenceDataType`) |
| Pixel-value vocabulary | `LabelClasses[]` |

Array index is the pixel value and index 0 is background. Preserve the order;
sorting labels changes the result. The mask reference does not imply that the
referenced bytes are retained as long as the result Object.

### 4.5 Acquisition images

Map `VisionImageReferenceDataType` without turning it into a generic URI:

| External concept | Vision field |
|---|---|
| Media location | `Uri` |
| Acquisition timestamp | `Timestamp` |
| Content digest | `Digest`, `DigestAlgorithm` |
| Encoding and pixel description | `Format`, `PixelFormat` |
| Shape and encoded size | `Width`, `Height`, `SizeBytes` |

The image timestamp is acquisition time; it is not result creation time or
inference completion time. Vision §§5.11–5.12 and 6.4 define image-reference
semantics and correlation. Preserve the image digest separately from any model
artifact digest.

## 5. Confidence

Vision confidence values are fractions from 0.0 through 1.0 (Vision §5.12).
Preserve their scope:

- `VisionResultType.Confidence` applies to the overall result;
- `VisionDetectionDataType.Confidence` applies to one detection.

Do not convert between fractions and percentages without an explicit external
unit, aggregate detection confidences into a result confidence, copy a
result-level confidence onto every detection, or manufacture confidence when
the optional source member is absent. Confidence is not probability unless the
producer's model contract says so, and it is not an inspection verdict,
uncertainty, or safety assessment.

## 6. Names that must remain distinct

Similar words at the boundary often describe different identities:

| External term | OPC UA concept | Keep distinct from |
|---|---|---|
| Provider | Operator or service providing an endpoint | `ModelType.Publisher`, which identifies who published the model |
| Publisher | `ModelType.Publisher` | OPC UA event publisher, Server application, or transport producer |
| Binding | External route/configuration binding | `DeploymentType.VersionBinding` and `BoundRef`, which define pinned versus followed model references (AI §9.3) |
| Version | `ModelType.Version` / `ModelVersionUsed` | Version-binding mode, endpoint API version, or external schema version |
| Manufacturing job | OPC 40100 job or site production order | `InferenceJobType`, an asynchronous AI invocation (AI §8.6) |
| Evaluation | `InspectionResultType.Evaluation` | `EvaluationRunType`, a model qualification run with metrics (AI §11.2) |
| Image digest | `VisionImageReferenceDataType.Digest` | `ModelType.Digest`, which identifies model artifact bytes |
| Model digest | `ModelType.Digest` plus algorithm and provenance | A response fingerprint, URI, resource name, or result identifier (AI §§10.4 and 12.1) |

The external schema should use qualified names where its native vocabulary
would otherwise collapse these distinctions.

## 7. URI roles

A URI's field determines what it means. Do not put every URI into a generic
`resourceUri`:

| URI role | OPC UA member or output |
|---|---|
| Image or mask bytes | `VisionImageReferenceDataType.Uri` |
| Human- or machine-readable explanation | `VisionResultType.ExplanationUri` |
| Model artifact bytes | `ModelType.ArtifactUri` |
| Model provenance record | `ModelType.ProvenanceUri` |
| Remote inference endpoint | `ModelSourceType.EndpointUri` |
| Endpoint contract description | `DeploymentType.EndpointDescriptionUri` |
| Inference request/response stored externally | `PayloadUri`, `RequestUri`, `ResponseUri` |
| Evaluation report | `EvaluationRunType.ReportUri` |
| Model safety policy | `ModelType.SafetyPolicyUri` |
| Deployment egress policy | `DeploymentType.EgressPolicyUri` |

Vision §§6.1 and 12.3 and AI §§8.6.1 and 12.2 define dereferencing and trust
boundaries. A URI is a locator, not content identity, application identity, or
evidence that bytes remain available.

## 8. Optional AI execution metadata

When the external producer has the AI invocation envelope, it may retain:

- `FinishReason`, preserving incomplete, filtered, cancelled, and error
  outcomes rather than treating every successful service call as complete
  (AI §8.2.2);
- `Usage`, including `UnitKind` and the distinction between unmetered and zero
  use (AI §8.2.3);
- `SafetyAssessment[]`, preserving category, severity, filtered state, and
  detail (AI §11.4).

These fields describe execution. They do not alter the typed Vision result.
A safety assessment says what an AI policy flagged or withheld; it is not a
functional-safety claim, SIL/PL assessment, permission to actuate, or evidence
that a machine action is safe.

## 9. Deliberate exclusions

This guide does not define:

- MQTT envelopes, topics, broker conventions, or QoS;
- replay identifiers, idempotency keys, or duplicate handling;
- recording or evidence-retention status;
- cross-source correlation policy;
- `Recommendation` semantics, withholding policy, setpoints, actuation, or
  command authority;
- functional-safety behavior or claims.

Those belong to a transport contract, evidence system, application policy, or
control/safety specification layered outside these information models. Adding
them here would turn an informative semantic mapping into a new protocol or
conformance profile.
