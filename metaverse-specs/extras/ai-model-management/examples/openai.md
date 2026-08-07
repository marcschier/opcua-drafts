# OpenAI platform API

Informative. Every member named here is defined in
[the specification](../../../ai-model-management/OPC-UA-AI-Model-Management.md); this guide
introduces none. Vendor facts verified 2026-08-05 against the documentation linked at the
end.

The OpenAI platform API serves models over the HTTP `/v1` API, with
`POST /v1/chat/completions` as the chat-completions surface mapped here. The same platform
also has the newer `/v1/responses` surface and other endpoints, but this guide is about the
chat-completions shape because that is what `RestChatCompletions` names.

That naming matters. The specification names the dialect for the wire contract, not for
OpenAI as a vendor, because the same request and response shape is served by Azure AI
Foundry, NVIDIA NIM, llama.cpp-compatible servers and other systems. A Server can therefore
say `RestChatCompletions` without claiming that the endpoint is OpenAI-operated.

## The `ModelSourceType`

| Member | OpenAI platform API |
|---|---|
| `SourceId` | your name for it, stable across restarts |
| `EndpointUri` | `https://api.openai.com/v1/` |
| `ApiDialect` | `RestChatCompletions` |
| `EndpointDescriptionUri` | not required; the dialect names the contract |
| `AuthenticationKind` | `BearerToken` |
| `CredentialReference` | names the bearer credential — never the value |
| `TokenAudience` | empty |
| `Reachability` | maintained from `TestConnection` and from call outcomes |

`AuthenticationKind` is `BearerToken` for the ordinary OpenAI platform arrangement because
the Server presents a bearer credential in the standard authorization header.
`CredentialReference` is the name by which the Server finds that credential in its own
store. It is not a place to copy the token, and §9.2 is explicit that credentials are not
exposed through the address space.

The OpenAI documentation also describes workload identity federation for obtaining
short-lived tokens. Apply §9.2: if a Server implements that arrangement without storing a
secret, the deployment is `WorkloadIdentity`; if it stores a bearer credential, it is
`BearerToken`.

## Identity

`GET /v1/models` returns `id`, `object`, `created` and `owned_by`. That is the same thin
identity exposed by the other OpenAI-compatible systems in this set, and it does not carry
the full `ModelType` identity.

| Member | From | Note |
|---|---|---|
| `Publisher` | empty unless independent provenance identifies the producer | `owned_by` reports the serving host or account, not the model producer |
| `Name` | `id`, with the trailing date removed | only where the name follows that convention |
| `Version` | the date suffix of `id`, where there is one | `gpt-4o-2024-08-06` yields `2024-08-06` |
| `ModelId` | the whole `id` | keep it verbatim under §6.2; it is what you send back |
| `PublishedAt` | `created` | Unix timestamp from the source, not the Server's acquisition time |
| `Framework`, `Format` | not exposed | leave empty |
| `Digest`, `DigestAlgorithm` | **not exposed** | see the `system_fingerprint` warning below |
| `DigestProvenance` | `NotAvailable` | no artefact digest is exposed; `system_fingerprint` is not one |

The `owned_by` field reports the serving host or account. §6.2 says `Publisher` names the
organisation that produced the model and is left empty where only the serving organisation
is known. The full `id` still goes verbatim in `ModelId`, so two Servers can compare the
source system's own identifier even when the `Publisher`, `Name`, `Version` triple is
incomplete.

The `created` timestamp belongs in `PublishedAt`. §6.2.3 uses the source's publication
time to order opaque model identifiers and forbids substituting the Server's acquisition
time.

Pinned model ids such as `gpt-4o-2024-08-06` are immutable by OpenAI policy, not by content
addressing. A `Pinned` deployment is pinned to a name whose behaviour the provider promises
to hold stable. It is not pinned to a digest the Server can verify.

The `system_fingerprint` field in chat-completions responses is the trap in this mapping.
It is a real backend configuration fingerprint and is useful for repeatability
investigations, but it is not an artefact digest under §12.1.1. It therefore populates
`RuntimeIdentity`, not `Digest`: §9.3.1 treats a change to `RuntimeIdentity` as an
observable change to the deployment, which is the assurance a `Pinned` deployment can give
when no digest is available.

## `Invoke`

The request body goes through as the caller supplied it. §8.2 makes the payload opaque to
the Server, and the OpenAI chat-completions request is exactly the kind of vendor-shaped
JSON that rule exists to preserve.

| Deployment member | From |
|---|---|
| `ApiDialect` | `RestChatCompletions` |
| `RuntimeIdentity` | `system_fingerprint`, where the response carries one |

The deployment's `ApiDialect` is the same as the source's in the ordinary pass-through
arrangement. §6.4.2 makes that duplication intentional: the source value tells this Server
what to send outward, and the deployment value tells an OPC UA client what to put in
`Payload`.

| Output | From |
|---|---|
| `ResponsePayload` | the response body, verbatim |
| `ResponseContentType` | `application/json` |
| `ModelUsed` | the `ModelType` NodeId this deployment resolved to — not the response's `model` string |
| `Usage.UnitKind` | `tokens` |
| `Usage.InputUnits` | `usage.prompt_tokens` |
| `Usage.OutputUnits` | `usage.completion_tokens` |
| `Usage.TotalUnits` | `usage.total_tokens` |
| `FinishReason` | `choices[0].finish_reason`, mapped below |
| `SafetyAssessment` | populated when the content filter fired |
| `RetryAfter` | the `Retry-After` header, where the response carries one |

`FinishReason` maps: `stop` to `Stop`, `length` to `Length`, `tool_calls` to `ToolCall`,
`content_filter` to `Filtered`. The deprecated `function_call` value is an older form of a
tool call and should be reported as `ToolCall` if the Server chooses to accept it. There is
no `Cancelled` value on this contract — a cancelled call is cancelled by the Server, not by
the endpoint — and `Error` covers a response that arrived but could not be understood.

`ModelUsed` is a NodeId in this Server's address space, not the `model` string the endpoint
echoed back. A caller can already see the string in the payload. What it cannot otherwise
find out is *which of the models this Server publishes* answered, and that is the question
`ModelUsed` exists to settle — see §8.2.1, and the fallback case in §9.4 where the two differ.

## Asynchronous inference

OpenAI has a native batch API: `POST /v1/batches` creates a batch job from a pre-uploaded
JSONL file, returns a batch `id`, runs against endpoints including `/v1/chat/completions`,
and uses a fixed `24h` completion window. Results are retrieved through the Files API by
the returned output file id.

That gives `InvokeAsync` something native to map onto.

| Member | From |
|---|---|
| `JobId` | the OpenAI batch `id` |
| `RequestUri` | the batch `input_file_id` |
| `ResponseUri` | the output file id whose content the Files API returns |

The OPC UA job follows the Part 10 program lifecycle required by §8.6 while the Server
polls or observes the OpenAI batch status. OpenAI statuses such as `validating`,
`in_progress`, `finalizing`, `completed`, `failed`, `expired`, `cancelling` and
`cancelled` are endpoint details behind that lifecycle, not new OPC UA states.

The Server still owns the OPC UA job object. It is the place where the client reads the
state, result reference and failure reason, even though the work is being performed by the
OpenAI batch service.

## Large payloads

OpenAI has a Files API: `POST /v1/files` uploads a file and returns a `file_id`. The batch
API uses such a file as its input, and other OpenAI features can refer to files by id.

That is a by-reference payload, not a chunked transfer. A client that wants the Server to
submit an already uploaded file names the `file_id` through `PayloadUri`; the corresponding
`InferenceJobType.RequestUri` records the batch `input_file_id`, and `ResponseUri` records
the returned output file id.

| Member | From |
|---|---|
| `PayloadUri` | the `file_id` named by the request |
| `RequestUri` | the batch `input_file_id` actually submitted |
| `ResponseUri` | the returned output file id whose content the Files API serves |

`BeginTransfer` and `InferenceTransferType` are the Server's own, over Part 5 `FileType` as
§8.2 defines, for a payload too large to carry through the OPC UA call. §8.6.1 separates
that case from data that already lives elsewhere. A `PayloadUri`, `RequestUri` or
`ResponseUri` is untrusted input under §12.2, and it is also an egress decision under §9.5:
a deployment whose `EgressPermitted` is false **shall not** accept a `PayloadUri` naming
somewhere outside the operator's boundary.

## The catalogue

`GET /v1/models` is a useful source for `ListModels` on the `ModelSourceType`: it answers
which model ids the endpoint exposes, and it returns the `id`, `object`, `created` and
`owned_by` fields that the identity mapping above draws on.

It is not a catalogue in the §10 sense. It has no content-addressed artefact, no digest, no
resource that can be staged and verified, and no model card or provenance document that the
API exposes as a structured registry resource.

If you want §10 with real digests, the source has to be a registry that is
content-addressed. An OpenAI model id can be federated as an externally hosted deployment
under clause 9, but it cannot by itself satisfy `AI-Catalogue` or `AI-Import`.

## Residency, egress and retention

Nothing in the API response states residency, egress or retention. All three are operator
assertions.

| Member | OpenAI platform API |
|---|---|
| `InferenceLocation` | `Cloud` |
| `EgressPermitted` | `true` |
| `DataJurisdiction` | the jurisdiction the operator has contracted for |
| `RetainsInput` | asserted from the operator's retention arrangement |
| `EgressPolicyUri` | your policy document |

`EgressPermitted` is `true` because the request leaves the Server for a cloud service. §9.5
makes the point and it is worth repeating because it is the mistake people make: TLS
answers who can read the payload in flight, not whether it left the site.

Retention is likewise not a response field. The OpenAI request has a `store` field that
controls whether a completion is stored for distillation or evals, and separate policy
arrangements such as Zero Data Retention can apply, but the response does not confirm the
plant-level retention answer. The Server has to publish the operator's assertion in
`RetainsInput`.

## What this system does not tell you

- **Which weights answered.** No digest, anywhere, on any call. `Digest` and
  `DigestAlgorithm` stay empty, and `DigestProvenance` is `NotAvailable` under
  §12.1.1. Do not hash the model name, and do not use `system_fingerprint` as a digest.
- **What `system_fingerprint` means for provenance.** It is a backend configuration
  fingerprint. It belongs in `RuntimeIdentity`, where §9.3.1 makes changes observable on
  the deployment, but it is not a model artefact identity.
- **What the model was trained on.** Nothing maps to `TrainedOn` or `DatasetType`. If
  lineage matters, it comes from documentation or the supplier, by hand.
- **Whether the model behind an unpinned name changed.** A `Pinned` deployment can bind to a
  dated model id, but the pin is a name backed by provider policy, not a digest-backed
  artefact.
- **Where your data went, or whether it was kept.** Both are contract terms, recorded as
  operator assertions in `DataJurisdiction`, `EgressPermitted` and `RetainsInput`.

## Conformance units

This arrangement is an **AI Inference Gateway Server**: it reaches the
**AI-Base**, **AI-Invoke**, **AI-OffServer**, **AI-Federation** and
**AI-Residency** facets that §13.3 bundles for a hosted inference Server.

Reachable against the OpenAI platform API: **AI-Base**, **AI-Invoke**,
**AI-InvokeAsync**, **AI-Transfer**, **AI-OffServer**, **AI-Federation**,
**AI-Residency**.

Out of reach without something else: **AI-Catalogue** and **AI-Import** need a
content-addressed registry; **AI-Signatures** needs tensor shapes this contract does not
carry; **AI-Learning** needs training, which is not what this is.

## Sources

- [OpenAI chat completions API](https://developers.openai.com/api/reference/resources/chat)
- [OpenAI models list API](https://developers.openai.com/api/reference/resources/models/methods/list)
- [OpenAI API overview](https://developers.openai.com/api/reference/overview)
- [OpenAI batches API](https://developers.openai.com/api/reference/resources/batches)
- [OpenAI workload identity federation guide](https://developers.openai.com/api/docs/guides/workload-identity-federation)
