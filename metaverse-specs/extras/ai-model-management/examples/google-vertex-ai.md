# Google Vertex AI

Informative. Every member named here is defined in
[the specification](../../../ai-model-management/OPC-UA-AI-Model-Management.md); this guide
introduces none. Vendor facts verified 2026-08-05 against the documentation linked at the
end.

Google Vertex AI serves hosted Gemini models, publisher models and custom models through
regional Google Cloud endpoints. The native Gemini surface uses `:generateContent` and
`:streamGenerateContent` on a fully qualified model resource, while custom and AutoML
prediction use `:predict` on an endpoint resource.

The important distinction for this specification is not what Vertex AI can offer in total.
It is the contract this Server actually speaks to the endpoint. A Server using the native
Vertex AI request body is different from one reaching Vertex AI through the beta
OpenAI-compatible surface, even if both ultimately call a model hosted by Google.

## The `ModelSourceType`

| Member | Native Vertex AI | OpenAI-compatible Vertex AI |
|---|---|---|
| `SourceId` | your name for it, stable across restarts | as native |
| `EndpointUri` | the regional Vertex AI endpoint and resource path, for example `https://aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/{publisher}/models/{model}:generateContent` | `https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/endpoints/openapi/` |
| `ApiDialect` | `Proprietary` | `RestChatCompletions` |
| `EndpointDescriptionUri` | the documentation for `:generateContent`, `:streamGenerateContent` or `:predict` | not required; the dialect names the contract |
| `AuthenticationKind` | `WorkloadIdentity`, or `BearerToken` where the Server stores a token | as native |
| `CredentialReference` | names the service account, workload binding or token record — never the value | as native |
| `TokenAudience` | the Google OAuth scope used to obtain the access token | as native |
| `Reachability` | maintained from `TestConnection` and from call outcomes | as native |

`ApiDialect` is `Proprietary` for the native Vertex AI surfaces because the request body is
neither chat-completions JSON nor KServe Open Inference Protocol. The Gemini body has
`contents`, `systemInstruction`, `generationConfig` and `safetySettings`; the custom
prediction body has `instances`. §9.2 says a Server using `Proprietary` should populate
`EndpointDescriptionUri`, and Vertex AI is a clear case for doing so because even two
native Vertex AI operations have different payload shapes.

Vertex AI also has an OpenAI-compatible endpoint for some models, reached through an
`openai` SDK base URL under `endpoints/openapi/`. The research flags its exact GA status as
uncertain and describes it as beta. A Server that uses that surface is
`RestChatCompletions`, not `Proprietary`, because the dialect records the wire contract
this Server actually speaks, not every contract the provider could have served.

The arrangement to reach for is `WorkloadIdentity`: Google service accounts, Workload
Identity Federation, GKE workload identity and Cloud Run managed identity all let the
Server obtain short-lived access tokens without storing a secret. Under §9.2, a directly
stored bearer token is `BearerToken`. The research verifies OAuth and Application Default
Credentials but does not state the literal OAuth scope; put the configured Google OAuth
scope in `TokenAudience`, following the same pattern the Foundry guide uses for Azure.

## Identity

Vertex AI publisher model resource names are structured. For publisher models the name is a
path such as
`projects/{project}/locations/{location}/publishers/{publisher}/models/{model}`. That is
much richer than a bare model id: the `publishers/{publisher}` segment gives `Publisher`
directly, and the `locations/{location}` segment gives the deployment's
`DataJurisdiction` from the resource identity itself.

| Member | From | Note |
|---|---|---|
| `Publisher` | the `publishers/{publisher}` segment, or the `publisher` field returned by the publisher-model listing | available for publisher models |
| `Name` | `displayName`, or the final `models/{model}` segment where no display name is used | keep the resource path separately in `ModelId` |
| `Version` | the `version` field for publisher models, `versionId` for custom models, or `modelVersion` in a Gemini response | do not invent one where none is present |
| `ModelId` | the full Vertex AI resource `name` | keep it verbatim; it is what identifies the hosted model |
| `Framework`, `Format` | not exposed for hosted Gemini publisher models | leave empty |
| `Digest`, `DigestAlgorithm` | **not exposed** | `artifactUri` is not a digest |
| `DigestProvenance` | `NotAvailable` | no artefact digest is exposed; `artifactUri` is not one |

This resource name carries provenance and residency fields the Server already has to use. A
deployment pointed at
`projects/p/locations/europe-west4/publishers/google/models/gemini-...` carries its
publisher and region in the identifier the Server already has to call. A Server still
needs to publish the OPC UA `DataJurisdiction` on the deployment, but it is not forced to
recover that value from an out-of-band convention.

Custom models are less uniform. The Model Registry lists
`projects/{project}/locations/{location}/models/{model}` resources with `displayName`,
`versionId`, `artifactUri` and `metadataSchemaUri`. The location remains structured, but
there is no `publishers/{publisher}` segment in that resource path.

## `Invoke`

For native Gemini `:generateContent`, the request body goes through as the caller supplied
it. §8.2 makes the payload opaque to the Server, and this is the kind of vendor-shaped JSON
that rule exists to preserve.

| Output | From |
|---|---|
| `ResponsePayload` | the `GenerateContentResponse` body, verbatim |
| `ResponseContentType` | `application/json` |
| `ModelUsed` | the `ModelType` NodeId this deployment resolved to — not the response's `modelVersion` string |
| `Usage.UnitKind` | `tokens` |
| `Usage.InputUnits` | `usageMetadata.promptTokenCount` |
| `Usage.OutputUnits` | `usageMetadata.candidatesTokenCount` |
| `Usage.TotalUnits` | `usageMetadata.totalTokenCount` |
| `FinishReason` | `candidates[0].finishReason`, mapped below |
| `SafetyAssessment` | populated from `safetyRatings` when filtering or safety policy intervened |
| `RetryAfter` | the `Retry-After` header, where the response carries one |

The usage field names are not the OpenAI names. A Server that reads
`usage.prompt_tokens` from a native Vertex AI response will publish empty usage even when
the endpoint reported it. The verified native fields are `promptTokenCount`,
`candidatesTokenCount` and `totalTokenCount` under `usageMetadata`.

`FinishReason` maps: `FINISH_REASON_STOP` to `Stop`,
`FINISH_REASON_MAX_TOKENS` to `Length`, and the safety-related values
`FINISH_REASON_SAFETY`, `FINISH_REASON_RECITATION`, `FINISH_REASON_BLOCKLIST`,
`FINISH_REASON_PROHIBITED_CONTENT`, `FINISH_REASON_IMAGE_PROHIBITED_CONTENT`,
`FINISH_REASON_NO_IMAGE` and `FINISH_REASON_SPII` to `Filtered`.
`FINISH_REASON_MALFORMED_FUNCTION_CALL`, `FINISH_REASON_OTHER` and
`FINISH_REASON_UNSPECIFIED` are best reported as `Error` unless the Server has a more
specific policy. The research did not verify a successful tool-call terminal value on the
native Vertex AI response.

For custom model `:predict`, the response shape depends on the model. It still maps to
`Invoke` because §8.2 makes the payload opaque, but there is no general usage or finish
reason mapping unless the selected model's response schema carries those fields.

## Asynchronous inference

Vertex AI has native Batch Prediction jobs. The research verifies
`POST /v1/projects/{project}/locations/{location}/batchPredictionJobs`, with input from
Google Cloud Storage or BigQuery, a returned job resource and status, and JSONL on GCS for
Gemini batch input.

That gives `InvokeAsync` a real remote job to map onto. The Vertex AI batch prediction job
name goes in `JobId`, and the OPC UA job follows the Part 10 program lifecycle required by
§8.6 while the Server observes the Vertex AI job and exposes the result or failure through
the `InferenceJobType` instance.

## Large payloads

For large media, the Vertex AI pattern is to put the object in Google Cloud Storage and
refer to it from the request as `fileUri` in a `fileData` part. That is useful for native
Gemini requests, but it is not a chunked upload path for one OPC UA call.

So `BeginTransfer` is the Server's own Part 5 `FileType` transfer path as §8.2.4 defines.
The Server reassembles the payload and then issues one ordinary Vertex AI request, or
writes one ordinary batch input object, depending on which operation the client started.

## The catalogue

The publisher-model listing,
`GET https://aiplatform.googleapis.com/v1beta1/publishers/*/models`, is a useful source
for `ListModels` on the `ModelSourceType`. It returns `name`, `publisher`, `displayName`,
`description`, `version`, `supportedGenerationMethods`, `createTime` and `updateTime`,
which is enough to expose the hosted models this source can call.

The custom Model Registry is also useful for federation. It lists project and location
models with `name`, `displayName`, `versionId`, `createTime`, `updateTime`, `artifactUri`
and `metadataSchemaUri`.

Neither surface is a complete §10.1 catalogue by itself. The publisher-model list exposes
hosted models, not content-addressed artefacts a Server can stage and verify. The custom
registry exposes an `artifactUri`, but the research found no cryptographic digest. A Server
can federate Vertex AI-hosted models under §9.1; it cannot satisfy `AI-Catalogue` or
`AI-Import` from these APIs alone because §10.4 needs a digest to verify what was imported.

## Residency, egress and retention

The region is visible in the Vertex AI endpoint and in the model resource name. Retention
and training use are contractual statements, not fields in the inference response. Treat
the table as operator assertions, except for the region value carried by the resource path.

| Member | Google Vertex AI |
|---|---|
| `InferenceLocation` | `Cloud` |
| `EgressPermitted` | `true` |
| `DataJurisdiction` | the `locations/{location}` segment used by the endpoint and model resource |
| `RetainsInput` | asserted from the operator's Google Cloud data-use arrangement |
| `EgressPolicyUri` | your policy document |

`EgressPermitted` is `true` because the request leaves the Server for a cloud service.
§9.5 makes the point: OAuth, service accounts and TLS answer who may call and who can read
the traffic in flight, not whether the payload left the site.

The region-in-identity point is genuinely useful. A Server configured with a Vertex AI
publisher model can derive the jurisdiction it publishes from the same resource name it
uses to invoke the model, and a commissioning review can compare that value against the
endpoint URL. The API still does not state retention in the response; `RetainsInput` is the
operator's assertion.

## What this system does not tell you

- **Which weights answered.** No digest is returned for hosted Gemini models, publisher
  model listings or custom model registry entries. `DigestProvenance` is `NotAvailable`
  under §12.1.1. `artifactUri` is a storage location, not a content hash.
- **What the model was trained on.** Nothing maps to a dataset lineage in the information
  model. If lineage matters, it comes from a model card or supplier documentation outside
  the inference response.
- **The exact OAuth scope in the research file.** The research verifies OAuth, ADC,
  service accounts and workload identity, but the literal scope text is redacted or absent.
  Publish the configured Google OAuth scope in `TokenAudience`; do not move it into
  `CredentialReference`.
- **The maturity of the OpenAI-compatible surface.** The research says the
  OpenAI-compatible Vertex AI endpoint is beta and flags its exact GA status as uncertain.
  A Server using it should document that endpoint choice explicitly.
- **Retention in an inference response.** The response reports usage and safety fields, but
  not whether input is retained or used for training. That remains an operator assertion in
  `RetainsInput`.

## Conformance units

Reachable against Google Vertex AI: **AI-Base**, **AI-Invoke**, **AI-InvokeAsync**,
**AI-Transfer**, **AI-OffServer**, **AI-Federation**, **AI-Residency**.

Out of reach without something else: **AI-Catalogue** and **AI-Import** need a
content-addressed registry; **AI-Signatures** needs tensor shapes this contract does not
carry for Gemini; **AI-Learning** needs training lineage and promotion semantics beyond
the inference response.

## Sources

- [Vertex AI Gemini model reference](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini)
- [Vertex AI OpenAI migration guide](https://cloud.google.com/vertex-ai/generative-ai/docs/migrate/migrate-from-openai)
- [Vertex AI publisher models REST reference](https://cloud.google.com/vertex-ai/docs/reference/rest/v1beta1/publishers.models)
