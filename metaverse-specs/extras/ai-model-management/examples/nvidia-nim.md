# NVIDIA NIM

Informative. Every member named here is defined in
[the specification](../../../../source/metaverse-specs/ai-model-management/spec.md); this guide
introduces none. Vendor facts verified 2026-08-05 against the documentation linked at the
end.

NVIDIA NIM Microservices serve models through the OpenAI-compatible `/v1/` contract, backed
by vLLM for LLMs. The same contract can be reached on NVIDIA's hosted endpoint or from a
self-hosted container on NVIDIA GPU infrastructure.

That makes NIM the cleanest example of §8.1 in this set: where inference runs does not
change how it is called. The difference is recorded in `InferenceLocation`,
`EgressPermitted` and `DataJurisdiction`, not in the `Invoke` signature.

## The `ModelSourceType`

| Member | Self-hosted NIM | Hosted NIM |
|---|---|---|
| `SourceId` | your name for the NIM instance | your name for the NVIDIA endpoint |
| `EndpointUri` | `http://{host}:8000/v1/` by default | `https://integrate.api.nvidia.com/v1/` |
| `ApiDialect` | `RestChatCompletions` | `RestChatCompletions` |
| `EndpointDescriptionUri` | not required; the dialect names the contract | as self-hosted |
| `AuthenticationKind` | `Anonymous`, unless the operator adds one | `ApiKey` |
| `CredentialReference` | empty, or the name of the proxy credential — never the value | names the stored key — never the value |
| `TokenAudience` | empty | empty |
| `Reachability` | maintained from `TestConnection` and call outcomes | as self-hosted |

Self-hosted NIM does not enforce authentication by default. If the plant puts an
authentication wrapper in front of it, §9.2 says `AuthenticationKind` describes the
credential this Server stores for that wrapper. It is not a claim about what NIM itself
implements.

A NIM running on the same host as the OPC UA Server has `InferenceLocation` `OnServer`. A
NIM running on a GPU appliance elsewhere on the plant network has `InferenceLocation`
`EdgeOffServer`. Both are ordinary and honest arrangements; this member is what tells them
apart.

## Identity

`GET /v1/models` returns the OpenAI-shaped listing: `id`, `object`, `created` and
`owned_by`. NIM model ids are unusually helpful because an id such as
`meta/llama-3.1-8b-instruct` carries the publisher namespace directly.

| Member | From | Note |
|---|---|---|
| `Publisher` | the part before `/` in `id`, where present; otherwise empty unless independent provenance identifies the producer | `meta/llama-3.1-8b-instruct` yields `meta` |
| `Name` | the part after `/`, or the whole `id` if there is no `/` | keep the model name as served |
| `Version` | not exposed as a field | do not invent one from the name |
| `ModelId` | the whole `id` | this is what the endpoint expects |
| `PublishedAt` | `created` | Unix timestamp from the source, not the Server's acquisition time |
| `Framework`, `Format` | not exposed by the listing | leave empty unless configured out of band |
| `Digest`, `DigestAlgorithm` | **not exposed** | the manifest is not a weight hash |
| `DigestProvenance` | `NotAvailable` | no artefact digest is exposed; manifest profile metadata is not one |

The publisher split is worth noticing. An id such as `meta/llama-3.1-8b-instruct` carries
the originator in the id itself, so `Publisher` can be `meta` — the organisation that
trained the model — rather than the organisation hosting it, which is what a bare
`owned_by` usually gives you. That is §6.2's rule: `Publisher` answers "who made this",
not "who is serving it".

The OpenAI-shaped `created` field belongs in `PublishedAt`. §6.2.3 requires the source's
publication time rather than the time this Server first saw the model.

NIM also exposes `GET /v1/manifest`, which returns model profile metadata. Precision maps
to `Quantization`. GPU compatibility belongs on the deployment through `AcceleratorKind`
and `AcceleratorName`, because it says what this instance can run on. `GET /v1/metadata`
returns the active model profile identity, and that profile id belongs in
`RuntimeIdentity`: the profile itself has a home instead of being reduced to its precision
and accelerator fields. The manifest does not provide an artefact digest under §12.1.1, so
it cannot populate `Digest`.

## `Invoke`

The request body goes through as the caller supplied it. §8.2 makes the payload opaque, and
NIM gives the Server no reason to reinterpret it: the remote contract is the ordinary
OpenAI-compatible chat, completions or embeddings request.

| Deployment member | From |
|---|---|
| `ApiDialect` | `RestChatCompletions` |
| `RuntimeIdentity` | the active model profile id from `GET /v1/metadata` |

The deployment's `ApiDialect` is the same as the source's because the Server passes the
OpenAI-compatible payload through. §6.4.2 says that value tells an OPC UA client what to
put in `Payload`, while the source value tells this Server what to speak to NIM. §9.3.1
uses `RuntimeIdentity` for the serving configuration identity, so an active profile change
is observable on the deployment even when the model id stays the same.

| Output | From |
|---|---|
| `ResponsePayload` | the response body, verbatim |
| `ResponseContentType` | `application/json` |
| `ModelUsed` | the `ModelType` NodeId this deployment resolved to |
| `Usage.UnitKind` | `tokens` |
| `Usage.InputUnits` | `usage.prompt_tokens` |
| `Usage.OutputUnits` | `usage.completion_tokens` |
| `Usage.TotalUnits` | `usage.total_tokens` |
| `FinishReason` | `choices[0].finish_reason`, mapped below |
| `SafetyAssessment` | populated when filtering is reported |
| `RetryAfter` | the `Retry-After` header, where the response carries one |

`FinishReason` maps: `stop` to `Stop`, `length` to `Length`, `tool_calls` to `ToolCall`,
`content_filter` to `Filtered`. `Cancelled` is produced by this Server when it cancels the
call, and `Error` covers a response that arrived but could not be understood.

`ModelUsed` is still a NodeId in this Server's address space, not the endpoint's `model`
string. The endpoint string is useful, but it cannot answer the §8.2.1 question when a
fallback deployment answered instead.

## Asynchronous inference

The standard NIM microservice API has no job-based batch or asynchronous inference surface.
It is a real-time request/response service.

`InvokeAsync` is therefore the Server's own job, as §8.6 permits. The Server accepts the
request, returns an `InferenceJobType`, runs the NIM request itself and stores the same
`ResponsePayload`, `ModelUsed`, `Usage` and `FinishReason` that a synchronous `Invoke`
would have returned.

## Large payloads

NIM accepts the request body directly. The research found no `/v1/files` endpoint and no
dedicated chunked upload API on the NIM surface; images are carried in the request body
where the selected model accepts them.

So `BeginTransfer` is an OPC UA-side facility, not a NIM feature. The Server uses the
transfer path of §8.2 to collect a request that is too large for a `ByteString`, then
issues one ordinary NIM request.

## The catalogue

`GET /v1/models` is a useful `ListModels` implementation for a `ModelSourceType`: it tells
the Server which loaded models this NIM endpoint can serve.

It is not a §10 catalogue. It does not expose immutable content-addressed versions,
`ModelResourceType` entries, dataset resources or digests. `GET /v1/manifest` adds profile
metadata, including precision and GPU compatibility, but it still does not identify model
bytes by hash.

If the operator controls the container image and model repository, a separate plant
catalogue can describe those artefacts and make `Stage` imports meaningful. That catalogue
is outside the NIM inference API.

## Residency, egress and retention

The NIM API does not state residency, egress or retention. The operator asserts them on the
deployment.

| Member | Self-hosted NIM in the plant | Hosted NIM |
|---|---|---|
| `InferenceLocation` | `OnServer` or `EdgeOffServer` | `Cloud` |
| `EgressPermitted` | `false` | `true` |
| `DataJurisdiction` | the site or plant network zone | the service region or contract jurisdiction |
| `RetainsInput` | `false` if the operator controls logging accordingly | operator assertion |
| `EgressPolicyUri` | your plant policy | your provider policy |

`EgressPermitted` is `false` for a NIM in the plant, and that is one of the main reasons to
run one. The model may sit on another GPU appliance, but the payload stays inside the
operator boundary.

The difference between `OnServer` and `EdgeOffServer` is not cosmetic. It says whether a
host failure takes both the OPC UA Server and the model down together, or whether the
network path to the appliance can fail independently.

## What this system does not tell you

- **A weight digest.** The manifest describes profiles and compatibility, not a
  cryptographic hash. `Digest` and `DigestAlgorithm` stay empty, and `DigestProvenance` is
  `NotAvailable` under §12.1.1 unless an external catalogue supplies a digest.
- **Training lineage.** Nothing in the NIM API maps to `TrainedOn` or `DatasetType`.
- **A structured version.** The served `id` is the operational identifier. If it contains a
  version-like substring, that is still part of the name unless another source defines it.
- **Residency or retention.** Self-hosting makes the answers controllable, not automatic.
  Record the operator's policy in `DataJurisdiction`, `EgressPermitted`, `RetainsInput` and
  `EgressPolicyUri`.
- **A built-in health contract beyond ordinary calls.** `TestConnection` can use
  `GET /v1/models` or a lightweight inference request, but NIM's OpenAI-compatible surface
  does not add a dedicated health endpoint in the cited API surface.

## Conformance units

A NIM on a GPU appliance elsewhere is an **AI Inference Gateway Server** where
the secure off-server endpoint and residency assertions below are present. NIM on
the same host as the OPC UA Server is an **AI Inference Device Server** instead,
because its `InferenceLocation` is `OnServer`.

Reachable against self-hosted NIM: **AI-Base**, **AI-Invoke**, **AI-InvokeAsync**,
**AI-Transfer**, **AI-Federation** and **AI-Residency**. **AI-OffServer** is reachable for
a deployment whose `InferenceLocation` is not `OnServer`, which is what §13.2 asks for.
What that deployment must additionally satisfy is §12.2, and it is not optional: where
`InferenceLocation` is not `OnServer`, `EndpointUri` **shall** name an authenticated,
confidential scheme. NIM's default `http://{host}:8000/v1/` listener does not, so a NIM on
a GPU appliance elsewhere on the plant network is fronted with TLS and authentication
before this facet is claimed. NIM on the same host is `OnServer`, where the question does
not arise.

Out of reach from NIM alone: **AI-Catalogue** and **AI-Import** need a separate catalogue
with digests; **AI-Signatures** needs tensor signatures the OpenAI-compatible contract does
not carry; **AI-Learning** needs training and promotion lifecycle support.

## Sources

- [NVIDIA NIM for LLMs API reference](https://docs.nvidia.com/nim/large-language-models/2.0.0/reference/api-reference.html)
