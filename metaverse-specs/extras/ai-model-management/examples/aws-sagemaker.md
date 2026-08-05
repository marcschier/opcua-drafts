# Amazon SageMaker real-time endpoints

Informative. Every member named here is defined in
[the specification](../../../ai-model-management/OPC-UA-AI-Model-Management.md); this guide
introduces none. Vendor facts verified 2026-08-05 against the documentation linked at the
end.

Amazon SageMaker real-time endpoints run the container you deploy and route invocation
bytes to it. That makes SageMaker different from hosted-model systems: the host defines the
endpoint management plane, but the request and response contract at inference time is often
your container's contract.

That is the useful thing to model honestly. A container can be wholly proprietary, or it
can serve an OpenAI-compatible surface through TGI, vLLM or a similar runtime. `ApiDialect`
describes the contract the endpoint speaks, not who hosts it.

## The `ModelSourceType`

| Member | Amazon SageMaker endpoint |
|---|---|
| `SourceId` | your name for it, stable across restarts |
| `EndpointUri` | the SageMaker Runtime endpoint for `EndpointName` |
| `ApiDialect` | `Proprietary`, or `RestChatCompletions` for an OpenAI-compatible container |
| `EndpointDescriptionUri` | the container contract documentation |
| `AuthenticationKind` | `WorkloadIdentity`, or `ApiKey` for static access keys |
| `CredentialReference` | names the IAM role binding or key record — never the value |
| `TokenAudience` | empty |
| `Reachability` | maintained from `TestConnection` and from call outcomes |

`ApiDialect` is `Proprietary` for the default SageMaker case, and for a different reason
from Bedrock. Bedrock's proprietary surface is vendor-defined; SageMaker's request and
response bodies are container-defined. You built the container, so you define the contract.
`EndpointDescriptionUri` matters even more here than it does for Bedrock because it is the
only thing that can tell a client what the endpoint expects.

A common SageMaker deployment is a container serving an OpenAI-compatible surface, such as
TGI or vLLM. Where that is what you deployed, `RestChatCompletions` is the honest dialect
rather than `Proprietary`. The dialect describes the contract this Server speaks to the
endpoint and not who is hosting it.

SageMaker uses AWS Signature Version 4. Apply §9.2 the same way as in the
[Bedrock guide](aws-bedrock.md): SigV4 signing through an attached IAM role is
`WorkloadIdentity`, SigV4 signing through stored access keys is `ApiKey`, and
`EndpointDescriptionUri` records the actual signing arrangement when a client needs that
handshake detail.

## Identity

The inference plane has no standard model-listing endpoint. The control plane can list and
describe endpoints and models, including the model artefact S3 URI and container image, but
that is not the same thing as a `/v1/models` response.

| Member | From | Note |
|---|---|---|
| `Publisher` | operator assertion, or the container/model owner from control-plane metadata | not returned by invocation |
| `Name` | endpoint name, model name or container-declared model id | choose the value the endpoint expects clients to use |
| `Version` | model package version, image tag or container-declared version where one exists | no standard inference-plane field |
| `ModelId` | endpoint name plus target model or variant where used | keep the routing identity needed to call it |
| `Framework`, `Format` | control-plane or operator metadata | not returned by invocation |
| `ArtifactUri` | S3 model artefact URI such as `s3://bucket/model.tar.gz` | available from the model configuration |
| `Digest`, `DigestAlgorithm` | **not exposed by the inference plane** | see the S3 ETag warning below |
| `DigestProvenance` | `NotAvailable` from the inference plane | `Stage` hashing can reach `ComputedByServer`; an S3 ETag is not an independent digest |

SageMaker often gives the operator the artefact URI and control of the object behind it.
`ArtifactUri` can therefore be filled from the S3 model artefact location.

That still does not fill `Digest`. An S3 ETag is a de facto hash in common cases, but it is
not surfaced in any inference-plane response and it is not an artefact digest under
§12.1.1. Publish `ArtifactUri` when you have it; use `ComputedByServer` only if the Server
hashes the artefact during import, and `VerifiedOnStage` only if an independent declared
digest matched under §10.4.

## `Invoke`

`InvokeEndpoint` sends raw bytes to the container. `Content-Type` and `Accept` declare the
media types, and SageMaker passes headers such as custom attributes, target model, target
variant, inference component and session id to the container.

| Deployment member | From |
|---|---|
| `ApiDialect` | `Proprietary`, or `RestChatCompletions` for an OpenAI-compatible container |
| `EndpointDescriptionUri` | the container contract documentation |

The deployment's `ApiDialect` is usually the same as the source's because the Server passes
the payload through to the container. §6.4.2 makes that value the contract an OPC UA client
must satisfy when it fills `Payload`. `EndpointDescriptionUri` is the place to publish the
container contract when the dialect is `Proprietary`.

| Output | From |
|---|---|
| `ResponsePayload` | the container response body, verbatim |
| `ResponseContentType` | the response media type the container returns |
| `ModelUsed` | the `ModelType` NodeId this deployment resolved to — not merely the endpoint name |
| `Usage.UnitKind` | container-defined; empty when the container response is not metered, per §8.2.3 |
| `Usage.InputUnits` | container-defined; `0` when `UnitKind` is empty |
| `Usage.OutputUnits` | container-defined; `0` when `UnitKind` is empty |
| `Usage.TotalUnits` | container-defined; `0` when `UnitKind` is empty |
| `FinishReason` | container-defined |
| `SafetyAssessment` | container-defined |
| `RetryAfter` | the `Retry-After` header, where the response carries one |

For a plain container-defined endpoint, the Server cannot infer token counts or finish
reasons from the SageMaker envelope. CloudWatch can record latency and throughput, but that
is operational telemetry outside the response body. When the container response does not
meter the call, `Usage` is returned with empty `UnitKind` and zero counts; §8.2.3 defines
that as "not metered" rather than as a measurement. If the container emits
OpenAI-compatible chat-completions JSON, use the `RestChatCompletions` mapping from the
OpenAI-compatible guides: `usage.prompt_tokens`, `usage.completion_tokens`,
`usage.total_tokens` and `choices[0].finish_reason` carry the values.

`ModelUsed` still matters when SageMaker routes by target model, target variant or inference
component. A caller needs the `ModelType` NodeId that actually answered, especially where a
multi-model endpoint or variant route makes the endpoint name insufficient.

## Asynchronous inference

SageMaker has native Asynchronous Inference endpoints. `InvokeEndpointAsync` submits work to
`/endpoints/{EndpointName}/async-invocations`; the input can be in the request body or named
by `X-Amzn-SageMaker-InputLocation` as an S3 URI. The service returns 202 with an
`OutputLocation` S3 URI and an `InferenceId`; completion can be observed from S3 or through
SNS notification.

That is a genuine `InvokeAsync` mapping. `InferenceId` goes in `JobId`, `OutputLocation`
becomes `ResponseUri`, and the OPC UA job follows the Part 10 program lifecycle required
by §8.6 while the Server observes the asynchronous invocation and exposes the container
response through the `InferenceJobType` instance.

| Member | From |
|---|---|
| `JobId` | `InferenceId` |
| `RequestUri` | `X-Amzn-SageMaker-InputLocation`, where the request names S3 input |
| `ResponseUri` | `OutputLocation` |

Batch Transform is also a SageMaker batch mechanism, but it is a separate job API for
offline inference over S3 datasets. Map it only if the Server intentionally exposes that
control-plane job as `InvokeAsync`; it is not the real-time endpoint's asynchronous path.

## Large payloads

For asynchronous endpoints, `X-Amzn-SageMaker-InputLocation` can point at an S3 object
containing the payload. That is a native way to avoid the inline request limit for the async
path.

That is a by-reference payload, not an OPC UA chunked transfer.

| Member | From |
|---|---|
| `PayloadUri` | the S3 URI in `X-Amzn-SageMaker-InputLocation` |
| `RequestUri` | the S3 input location actually submitted |
| `ResponseUri` | the `OutputLocation` returned by `InvokeEndpointAsync` |

`BeginTransfer` and `InferenceTransferType` are the Server's own Part 5 `FileType` path as
§8.2 defines, for a payload too large to carry through the OPC UA call. §8.6.1 separates
that case from data that already lives in S3. A `PayloadUri`, `RequestUri` or `ResponseUri`
is untrusted input under §12.2, and it is also an egress decision under §9.5: a deployment
whose `EgressPermitted` is false **shall not** accept a `PayloadUri` naming somewhere
outside the operator's boundary. The Server may still write an assembled transfer to S3 and
call `InvokeEndpointAsync` where that egress is permitted, or issue one ordinary real-time
`InvokeEndpoint` request when the payload fits.

## The catalogue

SageMaker has useful control-plane inventory: endpoints, models, model artefact S3 URIs and
container images. It has no standard inference-plane catalogue and no `/v1/models` shape.
`ListModels` on the `ModelSourceType` can therefore be implemented only from the Server's
own configuration or from SageMaker control-plane calls that the Server is authorized to
make.

SageMaker is the one system in this set where `Stage` import under §10.3 is often genuinely
achievable. The operator commonly controls the S3 artefact, can fetch `s3://bucket/model.tar.gz`,
compute a digest, compare it with a catalogue entry and then publish the resulting
`ModelType`. That is different from hosted-model systems such as Bedrock, where the model
bytes are not available to the Server.

The distinction is important. `Federate` is enough when the Server only calls a SageMaker
endpoint. `Stage` is appropriate when the Server obtains the artefact and can perform the
§10.4 digest check before deployment.

## Residency, egress and retention

The SageMaker endpoint region is visible from the AWS endpoint and control plane. Whether
payloads leave the site, whether inputs are retained by the container and what jurisdiction
applies are still operator assertions.

| Member | Amazon SageMaker endpoint |
|---|---|
| `InferenceLocation` | `Cloud`, or `OnServer` for SageMaker Local Mode |
| `EgressPermitted` | `true` for AWS-hosted endpoints; `false` for local-only deployments |
| `DataJurisdiction` | the AWS region, or the local site |
| `RetainsInput` | asserted from the container and surrounding logging configuration |
| `EgressPolicyUri` | your policy document |

SageMaker Local Mode runs containers locally through the SageMaker Python SDK and Docker,
with the same style of `/invocations` call against localhost. In that deployment the data
boundary is the local machine or site rather than the AWS region, and the residency members
should say that.

## What this system does not tell you

- **The request schema, unless your container does.** SageMaker passes bytes. If the
  container contract is not documented through `EndpointDescriptionUri`, a client cannot
  know what to send.
- **Usage and finish reason in a standard envelope.** Token counts and `FinishReason` are
  available only if the container chooses to return them. Otherwise `UsageDataType` uses
  the §8.2.3 not-metered sentinel.
- **A digest from the inference plane.** `ArtifactUri` can be filled from the S3 model
  artefact URI, but `Digest` cannot be filled from `InvokeEndpoint` or
  `InvokeEndpointAsync`. `DigestProvenance` is `NotAvailable` for that surface under
  §12.1.1.
- **That an S3 ETag is a model digest.** It may be a useful storage hint, but §12.1.1
  treats storage entity tags as non-content identifiers. It is not the independent source
  declaration needed for `VerifiedOnStage`.
- **Where your data went, or whether it was kept.** Region, egress and retention depend on
  the endpoint deployment, container logging and operator policy.

## Conformance units

This arrangement is an **AI Inference Gateway Server**: it reaches the
**AI-Base**, **AI-Invoke**, **AI-OffServer**, **AI-Federation** and
**AI-Residency** facets that §13.3 bundles for a hosted inference Server.

Reachable against Amazon SageMaker endpoints: **AI-Base**, **AI-Invoke**,
**AI-InvokeAsync**, **AI-Transfer**, **AI-OffServer**, **AI-Federation**,
**AI-Residency**.

For a container that does not meter, **AI-Invoke** is satisfied by returning `Usage`
with empty `UnitKind` and zero counts; §13.2 accommodates that.

Out of reach without something else: **AI-Catalogue** needs a registry projection with real
resources, and **AI-Import** requires **AI-Catalogue** (§13) — an import job with nothing to
import from is not implementable, so a Server staging artefacts from S3 URIs alone claims
neither. Pair SageMaker with a content-addressed registry that declares a digest and both
become reachable together; [the Hugging Face guide](hugging-face.md) is the worked case.
**AI-Signatures** needs tensor shapes or schema metadata from the container;
**AI-Learning** needs training, which is not what invocation is.

## Sources

- [Amazon SageMaker InvokeEndpoint API](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_runtime_InvokeEndpoint.html)
- [Amazon SageMaker InvokeEndpointAsync API](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_runtime_InvokeEndpointAsync.html)
