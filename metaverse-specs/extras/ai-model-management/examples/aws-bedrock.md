# Amazon Bedrock

Informative. Every member named here is defined in
[the specification](../../../ai-model-management/OPC-UA-AI-Model-Management.md); this guide
introduces none. Vendor facts verified 2026-08-05 against the documentation linked at the
end.

Amazon Bedrock is a managed AWS service for hosted foundation models from several
publishers. The two inference surfaces that matter here are the Bedrock Runtime Converse
API, which gives one request and response shape across model families, and InvokeModel,
which sends a raw body whose schema depends on the selected model family.

That distinction is the practical one for this specification. Converse is the surface to
prefer for a Server implementing §8.2 because one payload shape across families lets `Invoke`
stay opaque under §8.2 without the Server learning whether the target is Anthropic, Amazon,
Meta or another family.

## The `ModelSourceType`

| Member | Amazon Bedrock |
|---|---|
| `SourceId` | your name for it, stable across restarts |
| `EndpointUri` | the regional Bedrock Runtime endpoint, for example `https://bedrock-runtime.{region}.amazonaws.com/` |
| `ApiDialect` | `Proprietary` |
| `EndpointDescriptionUri` | the documentation for the exact Bedrock operation and payload shape you use |
| `AuthenticationKind` | `WorkloadIdentity`, or `ApiKey` for static access keys |
| `CredentialReference` | names the IAM role binding or key record — never the value |
| `TokenAudience` | empty |
| `Reachability` | maintained from `TestConnection` and from call outcomes |

`ApiDialect` is `Proprietary`. Bedrock Converse is not OpenAI-shaped, not KServe-shaped and
not the OPC UA inference Method. InvokeModel is even more vendor-specific: the body is raw
JSON whose schema depends on the model family. §9.2 says a Server using `Proprietary`
should populate `EndpointDescriptionUri`, and Bedrock is the concrete reason. Without that
URI, nothing in the address space tells a client whether the Server expects the Converse
shape or a family-specific InvokeModel body.

AWS authenticates Bedrock calls with Signature Version 4. SigV4 is not one of the
five `AuthenticationKindEnum` literals because §9.2 classifies the credential the Server
stores, not the handshake it performs. SigV4 driven by an IAM role attached to the pod,
task or instance is `WorkloadIdentity`, because no secret is stored anywhere. SigV4 driven
by static access keys is `ApiKey`, because a secret is stored and must be rotated. If a
reader needs the handshake recorded exactly, set `EndpointDescriptionUri` to documentation
for the actual AWS SigV4 arrangement in use.

## Identity

`ListFoundationModels` returns `modelId`, `modelArn`, `modelName`, `providerName` and
`modelLifecycle`, among other capability fields. `providerName` is the model producer that
§6.2 says belongs in `Publisher` — Anthropic, Meta, Amazon and similar names — rather than
merely the host written into an `owned_by` field.

| Member | From | Note |
|---|---|---|
| `Publisher` | `providerName` | the model publisher, not merely AWS as host |
| `Name` | `modelName` | display name from the Bedrock catalogue |
| `Version` | parsed from `modelId` or `modelArn`, where the provider encodes one | a version identifier, not a digest |
| `ModelId` | `modelId` | keep it verbatim; it is what you send back |
| `PublishedAt` | `modelLifecycle.startOfLifeTime` | source publication time under §6.2.3 |
| `DeprecatedFrom` | `modelLifecycle.legacyTime` | the date the source stops treating the model as current |
| `SupportedUntil` | `modelLifecycle.endOfLifeTime` | the date the source stops serving the model |
| `Framework`, `Format` | not exposed | leave empty |
| `Digest`, `DigestAlgorithm` | **not exposed** | `modelArn` is not a weight hash |
| `DigestProvenance` | `NotAvailable` | no artefact digest is exposed; `modelArn` is not one |

`modelArn` is useful because it carries the AWS resource identity and includes a versioned
model identifier. It still does not identify the bytes by content under §12.1.1, so it
cannot populate `Digest`.

The lifecycle dates are the strongest Bedrock-specific identity mapping. `startOfLifeTime`
is the source's publication time for `PublishedAt`; `legacyTime` and `endOfLifeTime` belong
on the model card as `DeprecatedFrom` and `SupportedUntil`. §11.1 is the reason to carry
the retirement date: at `SupportedUntil` the deployment stops being served, and fallback
can route production to a model outside the qualified configuration.

## `Invoke`

For Converse, the request body goes through as the caller supplied it. The Server is not
required to understand the model family, which is exactly why Converse is preferable here:
one body shape lets §8.2 remain true across families.

| Deployment member | From |
|---|---|
| `ApiDialect` | `Proprietary` |
| `EndpointDescriptionUri` | the documentation for Converse, or the family-specific InvokeModel contract |
| `ObservedLatency` | `metrics.latencyMs` from Converse |

The deployment's `ApiDialect` is the same as the source's when the Server passes the
Bedrock payload through. §6.4.2 says to publish that value twice because the source value
describes this Server's outward call and the deployment value tells an OPC UA client what
shape its `Payload` must have. `EndpointDescriptionUri` is especially important for
InvokeModel, where `Proprietary` covers a family-specific body. `metrics.latencyMs` is the
measurement for `ObservedLatency`; under §6.4.3 a Server reporting `Degraded` on latency
grounds must publish the measurement that makes the state checkable.

| Output | From |
|---|---|
| `ResponsePayload` | the Converse response body, verbatim |
| `ResponseContentType` | `application/json` |
| `ModelUsed` | the `ModelType` NodeId this deployment resolved to — not the Bedrock `modelId` string |
| `Usage.UnitKind` | `tokens` |
| `Usage.InputUnits` | `usage.inputTokens` |
| `Usage.OutputUnits` | `usage.outputTokens` |
| `Usage.TotalUnits` | `usage.totalTokens` |
| `FinishReason` | `stopReason`, mapped below |
| `SafetyAssessment` | populated when guardrails or filtering intervened |
| `RetryAfter` | the `Retry-After` header, where the response carries one |

`FinishReason` maps directly where Converse reports one: `end_turn` and `stop_sequence` to
`Stop`, `max_tokens` to `Length`, `tool_use` to `ToolCall`, and `guardrail_intervened` or
`content_filtered` to `Filtered`. The research directly verified `end_turn`, `max_tokens`
and `stop_sequence` from the response schema and found the other values in AWS guidance;
that uncertainty belongs in an implementation note if the Server treats unrecognised values
as anything other than `Error`.

InvokeModel is the escape hatch for model-specific bodies. It still maps to `Invoke`
because §8.2 makes the payload opaque, but the Server cannot give a general mapping for
usage or finish reason unless the selected family's response schema carries them. If you
use InvokeModel, make `EndpointDescriptionUri` point to the family-specific contract. Where
the response does not define usage counts, return `Usage` with empty `UnitKind` and zero
counts; §8.2.3 defines that as "not metered" rather than as a measurement. A Server that
does report a non-empty `UnitKind` must have obtained the corresponding counts from the
execution site.

## Asynchronous inference

Bedrock has native batch inference through `CreateModelInvocationJob`. The job takes S3
input, a `modelId`, an execution `roleArn` and S3 output configuration, returns a `jobArn`,
and can use either InvokeModel or Converse invocation types. The documented timeout range
is 24 to 168 hours.

That is a genuine `InvokeAsync` mapping.

| Member | From |
|---|---|
| `JobId` | the Bedrock `jobArn` |
| `RequestUri` | the S3 input location |
| `ResponseUri` | the S3 output location |

The OPC UA job follows the Part 10 program lifecycle required by §8.6 while the Server
observes the Bedrock job and exposes the result or failure through the `InferenceJobType`
instance.

## Large payloads

The real-time Bedrock runtime takes the request body inline; the research notes an inline
limit of about 4 MB. Bedrock batch inference uses S3 input and output locations, but that
is a by-reference payload contract, not a chunked upload path for one synchronous call.

| Member | From |
|---|---|
| `PayloadUri` | the S3 input location supplied for the batch request |
| `RequestUri` | the S3 input location actually submitted |
| `ResponseUri` | the S3 output location returned or configured for the job |

`BeginTransfer` is the Server's own Part 5 `FileType` transfer path as §8.2 defines, for
a payload too large to carry through the OPC UA call. §8.6.1 separates that case from data
that already lives in S3. A `PayloadUri`, `RequestUri` or `ResponseUri` is untrusted input
under §12.2, and it is also an egress decision under §9.5: a deployment whose
`EgressPermitted` is false **shall not** accept a `PayloadUri` naming somewhere outside the
operator's boundary.

## The catalogue

`ListFoundationModels` is the right source for `ListModels` on the `ModelSourceType`: it
answers which foundation models Bedrock exposes in the region and provides `modelId`,
`modelArn`, `modelName`, `providerName` and `modelLifecycle`.

Within `modelLifecycle`, `status` is not a substitute for observing deployment state, and
the research does not establish how `publicExtendedAccessTime` changes the card dates. The
dates mapped above are the ones carried by the information model.

It is not a catalogue in the §10.1 sense. The API lists hosted models, not content-addressed
artefacts that a Server can fetch, hash and stage. `providerName` gives a useful publisher,
and `modelArn` gives a stable AWS resource identity, but neither supplies `Digest` on a
`ModelResourceType`.

A Server can federate Bedrock-hosted models under §9.1. It cannot satisfy
`AI-Catalogue` or `AI-Import` from `ListFoundationModels` alone, because there is no model
artefact to stage and verify under §10.3 and §10.4.

## Residency, egress and retention

The region is visible in the Bedrock endpoint and the control-plane region used for
listing. The retention and training-use position is a contractual AWS statement, not a
field in an inference response. Treat the table as operator assertions.

| Member | Amazon Bedrock |
|---|---|
| `InferenceLocation` | `Cloud` |
| `EgressPermitted` | `true` |
| `DataJurisdiction` | the AWS region used by the endpoint |
| `RetainsInput` | asserted from the Bedrock data-use contract |
| `EgressPolicyUri` | your policy document |

`EgressPermitted` is `true` because the request leaves the Server for a cloud service. §9.5
makes the point: SigV4 and TLS answer who may call and who can read the traffic in flight,
not whether the payload left the site.

## What this system does not tell you

- **The exact handshake.** SigV4 is not in `AuthenticationKindEnum` because §9.2
  classifies what is stored. Use `WorkloadIdentity` for role-based signing and `ApiKey`
  for static access keys, and point `EndpointDescriptionUri` at the SigV4 handshake you
  actually use.
- **Which weights answered.** No digest is returned by Converse, InvokeModel or
  `ListFoundationModels`. `DigestProvenance` is `NotAvailable` under §12.1.1.
  `modelArn` carries a version identifier, not a weight hash.
- **A universal request body.** Converse gives one Bedrock body shape; InvokeModel gives a
  raw body whose schema depends on the provider family.
- **What the model was trained on.** Nothing maps to `TrainedOn` or `DatasetType`. If
  lineage matters, it comes from supplier documentation or a model card outside the
  inference response.
- **Where your data went, or whether it was kept.** Region and retention are recorded as
  operator assertions in `DataJurisdiction`, `EgressPermitted` and `RetainsInput`.

## Conformance units

This arrangement is an **AI Inference Gateway Server**: it reaches the
**AI-Base**, **AI-Invoke**, **AI-OffServer**, **AI-Federation** and
**AI-Residency** facets that §13.3 bundles for a hosted inference Server.

Reachable against Amazon Bedrock: **AI-Base**, **AI-Invoke**, **AI-InvokeAsync**,
**AI-Transfer**, **AI-OffServer**, **AI-Federation**, **AI-Residency**.

Converse is metered through `usage.inputTokens`, `usage.outputTokens` and
`usage.totalTokens`. InvokeModel responses that do not carry counts satisfy
**AI-Invoke** by returning `Usage` with empty `UnitKind` and zero counts; §13.2
accommodates that.

Out of reach without something else: **AI-Catalogue** and **AI-Import** need a
content-addressed registry; **AI-Signatures** needs tensor shapes this contract does not
carry; **AI-Learning** needs training, which is not what this is.

## Sources

- [Amazon Bedrock Converse API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html)
- [Amazon Bedrock InvokeModel API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_InvokeModel.html)
- [Amazon Bedrock ListFoundationModels API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_ListFoundationModels.html)
- [Amazon Bedrock CreateModelInvocationJob API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_CreateModelInvocationJob.html)
- [Amazon SageMaker InvokeEndpoint API](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_runtime_InvokeEndpoint.html)
