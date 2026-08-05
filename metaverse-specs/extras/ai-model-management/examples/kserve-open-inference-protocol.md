# KServe / Open Inference Protocol v2

Informative. Every member named here is defined in
[the specification](../../../ai-model-management/OPC-UA-AI-Model-Management.md); this guide
introduces none. Vendor facts verified 2026-08-05 against the documentation linked at the
end.

Open Inference Protocol v2 is the vendor-neutral tensor inference contract associated with
KServe. It is not a hosted product, and that is why the specification has an
`OpenInferenceProtocol` literal: an installation that standardises on this contract can
change serving implementations without changing any client of this Server.

KServe and NVIDIA Triton both implement this shape. Triton has its own guide because it
also exposes NVIDIA-specific surfaces; use this guide for the open protocol baseline and
see [the NVIDIA Triton guide](nvidia-triton.md) when the implementation is Triton.

## The `ModelSourceType`

| Member | KServe / OIP v2 endpoint |
|---|---|
| `SourceId` | your name for the serving endpoint |
| `EndpointUri` | the base URL that exposes `/v2` |
| `ApiDialect` | `OpenInferenceProtocol` |
| `EndpointDescriptionUri` | the OIP v2 specification or local endpoint documentation |
| `AuthenticationKind` | implementation-defined: often `Anonymous`, `BearerToken`, `MutualTls` or `WorkloadIdentity` |
| `CredentialReference` | names the configured credential — never the value |
| `TokenAudience` | only where the chosen authentication scheme needs it |
| `Reachability` | maintained from liveness, readiness and model-readiness probes |
| `Capabilities` | tensor inference and any implementation extensions the Server chooses to publish |
| `TestConnection` | maps to the OIP health and model-readiness probes |
| `ListModels` | not defined by base OIP; implementation-specific if present |

The protocol does not define authentication. Apply §9.2 to the credential the Server
stores: no credential is `Anonymous`, a stored bearer credential is `BearerToken`, platform
identity with no stored secret is `WorkloadIdentity`, and mutual TLS credentials are
`MutualTls`.

`ApiDialect` is the important member here. It names the wire contract rather than KServe as
a product, so a Server can move from one OIP implementation to another without changing the
OPC UA-facing deployment description.

A deployment that accepts the OIP request body from an OPC UA caller publishes
`DeploymentType.ApiDialect` as `OpenInferenceProtocol`. This is the clean case for
§6.4.2: the payload contract genuinely is the OIP body, so the source dialect and the
deployment dialect are the same when the Server passes that body through.

The health endpoints make `TestConnection` real rather than a disguised inference call:
server liveness, server readiness and model readiness distinguish a dead process, a server
that is not ready to serve, and one model that is not ready. Those results are the natural
source for `Reachability`, with call failures and throttling updating it afterwards as
§9.4 describes.

## Identity

OIP names models by strings in the URL and optionally by version strings in the same path.
It does not carry a content digest.

| Member | From | Note |
|---|---|---|
| `Publisher` | operator assertion | not present in the protocol |
| `Name` | `{MODEL_NAME}` | from `/v2/models/{MODEL_NAME}` |
| `Version` | `{MODEL_VERSION}` or one entry from `versions` | optional |
| `ModelId` | the model name, or name plus version | keep the value the endpoint expects |
| `Framework` | `platform` | examples include serving platforms such as TensorRT plan |
| `Inputs` | metadata `inputs` | names, datatypes and shapes |
| `Outputs` | metadata `outputs` | names, datatypes and shapes |
| `PublishedAt`, `LastModifiedAt` | not exposed | leave empty unless another catalogue supplies them |
| `Digest`, `DigestAlgorithm` | not exposed | leave empty unless another catalogue supplies them |
| `DigestProvenance` | `NotAvailable` | base OIP returns no artefact digest |

`GET /v2/models/{name}[/versions/{version}]` returns model metadata: `name`, optional
`versions`, `platform`, and `inputs` and `outputs` with tensor names, datatypes and shapes.
Those `inputs` and `outputs` map directly onto `Inputs` and `Outputs` on `ModelType`.

Base OIP exposes no source publication or modification timestamp. `PublishedAt` and
`LastModifiedAt` therefore stay empty on the same terms as `Digest`: an implementation may
populate them from another catalogue, but the OIP metadata response does not establish
them.

That makes **AI-Signatures** reachable. §6.2 says these tensor signatures are the
machine-readable description of what a deployment accepts, and OIP is one of the few
serving protocols in this guide set that actually exposes them.

An explicit version in the URL is a `Pinned` binding. A deployment that follows a serving
alias or other mutable name is `FollowsRef` with `BoundRef` naming that ref, and §9.3's
warning applies: changing the ref changes what answers.

## `Invoke`

The standard inference call is:

```http
POST /v2/models/{MODEL_NAME}[/versions/{MODEL_VERSION}]/infer
```

The request carries an optional id, optional parameters, input tensors and requested output
tensors. A tensor has a `name`, `shape`, `datatype` and data. The response mirrors the
shape with output tensors.

| Output | From |
|---|---|
| `ResponsePayload` | the OIP response body, verbatim |
| `ResponseContentType` | `application/json` for the HTTP/REST binding |
| `ModelUsed` | the `ModelType` NodeId for the resolved model and version |
| `Usage.UnitKind` | empty for an unmetered OIP response; otherwise the implementation extension's unit, per §8.2.3 |
| `Usage.InputUnits` | `0` when `UnitKind` is empty; otherwise the measured input count |
| `Usage.OutputUnits` | `0` when `UnitKind` is empty; otherwise the measured output count |
| `Usage.TotalUnits` | `0` when `UnitKind` is empty; otherwise the measured total count |
| `FinishReason` | normally `Stop` for success, `Error` for failed or invalid responses |
| `SafetyAssessment` | not defined by OIP |
| `RetryAfter` | only from implementation-specific throttling headers |

This is a tensor protocol, not a chat protocol. It has no standard token accounting, no
choice list and no text-generation finish reason. That is not a defect; it is exactly what
a reader mapping a vision model, a vibration model or a classical tensor model will meet.
§8.2.3 gives that absence an encoding: `Usage` is returned, with an empty `UnitKind` and
zero counts, and clients treat those zeros as "not metered" rather than as measurements.

The OIP datatypes verified in the research include `BOOL`, unsigned and signed integer
widths, `FP16`, `FP32`, `FP64`, `BYTES` and `STRING`. The Server maps those into the tensor
signature element types it publishes with `Inputs` and `Outputs`.

## Asynchronous inference

Base OIP v2 does not define a job or handle pattern. Server-side dynamic batching is an
implementation detail, not an `InvokeAsync` contract.

So `InvokeAsync` is normally implemented by the OPC UA Server under §8.6: it creates an
`InferenceJobType`, submits or schedules the ordinary OIP inference request, and publishes
the job lifecycle and result through OPC UA. If an implementation adds its own async API,
that remains behind the same `InferenceJobType` surface.

## Large payloads

Base OIP v2 does not define chunked upload or a file-transfer API for inference. The HTTP
body contains the tensors.

`BeginTransfer` is therefore the Server's OPC UA transfer path under §8.2.4. The client
writes the request through `InferenceTransferType`, the Server sends one OIP request when
ready, and the response is read back through the same OPC UA exchange if it is too large to
return inline.

## The catalogue

OIP model metadata is not a catalogue in the §10 sense. It tells a caller what one serving
endpoint can execute and what tensor shapes it expects; it does not define publishers,
resources, immutable content-addressed versions, model cards or artefact digests.

That means `ListModels`, if an implementation provides it, is a serving inventory rather
than a `ModelRegistryType`. It can create useful `ModelType` instances for deployments, and
it can populate `Inputs` and `Outputs`, but it cannot by itself satisfy **AI-Catalogue** or
**AI-Import**.

Pair OIP with a real catalogue when import provenance matters. The catalogue supplies
`Publisher`, `Name`, `Version`, `Digest` and `DigestAlgorithm`; OIP supplies the serving
contract and the tensor signatures.

## Residency, egress and retention

OIP says nothing about geography or retention. Those are deployment facts supplied by the
operator and by the platform that hosts the endpoint.

| Member | KServe / OIP v2 endpoint |
|---|---|
| `InferenceLocation` | usually `EdgeOffServer`, `Cloud` or `OnServer`, depending where the endpoint runs |
| `EgressPermitted` | `true` if input leaves the operator boundary, otherwise `false` |
| `DataJurisdiction` | the site, cluster, region or jurisdiction the operator uses |
| `RetainsInput` | operator assertion; report `true` if it cannot be established |
| `EgressPolicyUri` | your policy document |

The common on-premises KServe case is exactly why §9.5 separates location from egress. A
remote endpoint on the plant network is off the Server, but it may still keep data inside
the operator boundary.

## What this system does not tell you

- **Who published the model.** OIP has `name` and optional `version`, not a publisher
  namespace. `Publisher` is supplied by the operator or by an external catalogue.
- **Which bytes are running.** No content digest is returned. `Digest` and
  `DigestAlgorithm` need another source, `DigestProvenance` is `NotAvailable`, and §10.4
  cannot verify an import from OIP alone.
- **Usage accounting.** There are no standard token, image, sample or byte counts in the
  OIP response envelope. Without an implementation extension, `UsageDataType` uses the
  §8.2.3 not-metered sentinel: empty `UnitKind` and zero counts.
- **Chat finish semantics.** There is no standard equivalent of `length`, `tool_calls` or
  `content_filter`. `FinishReasonEnum` has little to say beyond `Stop` and `Error`.
- **Asynchronous jobs or large-object transfer.** Base OIP defines synchronous tensor
  inference. `InvokeAsync` and `BeginTransfer` are OPC UA Server features unless the chosen
  implementation adds something native.
- **Residency and retention.** The protocol does not state where input is processed or
  whether it is retained.

## Conformance units

Where the OIP endpoint is off-server and the operator states the residency boundary,
this arrangement is an **AI Inference Gateway Server**: it reaches the
**AI-Base**, **AI-Invoke**, **AI-OffServer**, **AI-Federation** and
**AI-Residency** facets that §13.3 bundles for a gateway.

Reachable against a conforming OIP endpoint: **AI-Base**, **AI-Invoke**,
**AI-Federation** and **AI-Signatures**. **AI-OffServer** is reachable for a deployment
whose `InferenceLocation` is not `OnServer`, which is what §13.2 asks for. What that
deployment must additionally satisfy is §12.2, and it is not optional: where
`InferenceLocation` is not `OnServer`, `EndpointUri` **shall** name an authenticated,
confidential scheme. A bare `/v2` base URL over plain HTTP does not, so an OIP endpoint
reached across a network is fronted with TLS and authentication before this facet is
claimed. **AI-Residency** is reachable where the operator can state the deployment
boundary required by §9.5.

The absence of OIP usage counts does not weaken **AI-Invoke**: the Server returns `Usage`
with empty `UnitKind` and zero counts for an unmetered call, and §13.2 accommodates that.

Reachable through the OPC UA Server rather than the OIP protocol itself: **AI-InvokeAsync**
and **AI-Transfer**. Out of reach without another system: **AI-Catalogue** and **AI-Import**
need a catalogue with immutable versions and digests; **AI-Learning** needs a training
workflow.

## Sources

- [KServe Predict Protocol v2 required API](https://github.com/kserve/kserve/blob/master/docs/predict-api/v2/required_api.md)
- [KServe Predict Protocol v2 documentation](https://github.com/kserve/kserve/blob/master/docs/predict-api/v2/)
