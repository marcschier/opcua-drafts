# Azure AI Foundry

Informative. Every member named here is defined in
[the specification](../../../ai-model-management/OPC-UA-AI-Model-Management.md); this guide
introduces none. Vendor facts verified 2026-08-05 against the documentation linked at the
end.

Azure AI Foundry serves models over an HTTP contract that is OpenAI-compatible in schema
and Azure-hosted in everything else — authentication, regions, and the model catalogue
behind it. **Foundry Local** runs the same contract on the machine, reached either over
loopback or through an in-process SDK.

Both are covered here because the interesting thing about them is that they are the same
thing in two places, which is exactly the claim §8.1 makes: where inference runs does not
change how it is called. What it changes is `InferenceLocation`, `EgressPermitted` and
`DataJurisdiction` — the members that exist precisely to record that difference.

## The `ModelSourceType`

| Member | Cloud | Foundry Local |
|---|---|---|
| `SourceId` | your name for it, stable across restarts | as cloud |
| `EndpointUri` | `https://{resource}.openai.azure.com/openai/v1/` | `http://localhost:{port}/v1/` |
| `ApiDialect` | `RestChatCompletions` | `RestChatCompletions`, or `EmbeddedRuntime` through the SDK |
| `EndpointDescriptionUri` | not required; the dialect names the contract | as cloud |
| `AuthenticationKind` | `WorkloadIdentity`, or `ApiKey` | `Anonymous` |
| `CredentialReference` | names the key or the token scope — never the value | empty |
| `TokenAudience` | `https://ai.azure.com/.default` | empty |
| `Reachability` | maintained from `TestConnection` and from call outcomes | as cloud |

`AuthenticationKind` is `WorkloadIdentity` when the Server holds a Microsoft Entra managed
identity and obtains tokens through it. That applies §9.2's storage rule: no secret is
stored anywhere, so there is nothing to leak, rotate or archive. `ApiKey` is the fallback
where a managed identity is not available.

Foundry Local is `Anonymous` because it listens on loopback and there is nothing to
authenticate to. That is a statement about the deployment, not a relaxation: an endpoint
reachable only from the machine it runs on has the machine's own access control in front of
it.

The two SDK-hosted variants are worth distinguishing. Reached over its loopback HTTP
server, Foundry Local is `RestChatCompletions` and looks like any other endpoint. Reached
through the in-process SDK — `Microsoft.AI.Foundry.Local` and its siblings, which are
library APIs rather than HTTP — it is `EmbeddedRuntime`, and `EndpointUri` is empty because
there is no endpoint. Say which one you built, because the failure modes differ: one can be
unreachable, the other can only be absent.

## Identity

The listing endpoint returns `id`, `object`, `created` and `owned_by`. A per-model
`GET /model-info` adds a name, a type and capabilities. Neither carries a digest or
structured provenance, and neither decomposes into the triple `ModelType` asks for.

| Member | From | Note |
|---|---|---|
| `Publisher` | empty unless independent provenance identifies the producer | `owned_by` reports the serving host or account, not the model producer |
| `Name` | `id`, with the trailing date removed | on a deployed model this is the *deployment* name, which is yours |
| `Version` | the date suffix of `id`, where there is one | `gpt-4o-2024-08-06` yields `2024-08-06` |
| `ModelId` | the whole `id` | keep it verbatim under §6.2; it is what you must send back |
| `PublishedAt` | `created` | Unix timestamp from the source, not the Server's acquisition time |
| `Framework`, `Format` | not exposed | leave empty |
| `Digest`, `DigestAlgorithm` | **not exposed** | see below |
| `DigestProvenance` | `NotAvailable` | no artefact digest is exposed; the model name is not one |

Two traps here.

The `owned_by` field reports the serving host or account. §6.2 says `Publisher` names the
organisation that produced the model and is left empty where only the serving organisation
is known. The full `id` still goes verbatim in `ModelId`, so two Servers can compare the
source system's own identifier even when the `Publisher`, `Name`, `Version` triple is
incomplete.

The `id` on a cloud deployment is a **deployment name you chose**, not the model's identity.
Two Servers in the same plant can call the same underlying model different things, and
nothing in the API will tell you they are the same. If the provenance question matters to
you — and §11 exists because it usually does — record the underlying model in `ModelId` and
your deployment name in the deployment's `DeploymentId`, where it belongs.

The date suffix is a **convention, not a field**. Splitting `gpt-4o-2024-08-06` on the last
hyphen group works today and is not something the API promises. A model named without one
leaves `Version` empty, which is honest, rather than being given a fabricated `1.0.0`.

The `created` timestamp is the value for `PublishedAt`. §6.2.3 requires the source's
publication time rather than the time this Server first saw the model, because the source
time is what lets opaque identifiers be ordered.

## `Invoke`

The request body goes through as the caller supplied it. §8.2 makes the payload opaque to
the Server, and the reason shows here: the `extra-parameters: pass-through` header exists so
that model-specific fields can reach the model without the API version moving, and a Server
that parsed and re-serialised the body would defeat it.

| Deployment member | Cloud | Foundry Local |
|---|---|---|
| `ApiDialect` | `RestChatCompletions` | `RestChatCompletions`, or `EmbeddedRuntime` through the SDK |

The deployment's `ApiDialect` is usually the same as the source's because the payload
passes through unchanged. §6.4.2 says that is the honest answer given twice: the source
value tells this Server what it speaks outward, and the deployment value tells a client
what to put in `Payload`.

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
`content_filter` to `Filtered`. There is no `Cancelled` on this contract — a cancelled call
is cancelled by the Server, not by the endpoint — and `Error` covers a response that arrived
but could not be understood.

`ModelUsed` is a NodeId in this Server's address space, not the `model` string the endpoint
echoed back. A caller can already see the string in the payload. What it cannot otherwise
find out is *which of the models this Server publishes* answered, and that is the question
`ModelUsed` exists to settle — see §8.2.1, and the fallback case in §9.4 where the two differ.

## Asynchronous inference

Azure OpenAI has a batch API — `POST /batches`, a job identifier, a 24-hour completion
window — and it is reached on a different plane from the v1 inference surface. Treat it as
unavailable from the inference endpoint unless you have checked for your resource.

So `InvokeAsync` is generally the Server's own job: it accepts the call, returns an
`InferenceJobType` NodeId, and runs the synchronous request itself. §8.6 permits exactly
this, and the value is real even when nothing native backs it — the result survives the
client that asked for it disconnecting, which a synchronous call cannot offer.

Where you do wire it to the batch API, the mapping is direct: the batch identifier goes in
`JobId` and the job's lifecycle follows the Part 10 program state machine as §8.6 requires.

## Large payloads

`POST /files` yields a `file_id` referenced from a later request, on the Azure OpenAI plane.
It is a by-reference payload, not a chunked transfer.

| Member | From |
|---|---|
| `PayloadUri` | the `file_id` named by the later request |
| `RequestUri` | the file id actually submitted by the Server |

A later Azure OpenAI request that names the uploaded file supplies that id through
`PayloadUri`, and the job records what was submitted in `InferenceJobType.RequestUri`
where asynchronous processing is used.

`BeginTransfer` and `InferenceTransferType` are the Server's own, over Part 5 `FileType` as
§8.2 defines, for a payload too large to carry through the OPC UA call. §8.6.1 separates
that case from data that already lives elsewhere. A `PayloadUri` or `RequestUri` is
untrusted input under §12.2, and it is also an egress decision under §9.5: a cloud
deployment may accept an Azure file reference only where the operator has permitted that
egress, and a deployment whose `EgressPermitted` is false **shall not** accept a
`PayloadUri` naming somewhere outside the operator's boundary.

## The catalogue

The inference-plane `GET /v1/models` lists **what is deployed on this resource**, which is
the right source for `ListModels` on the `ModelSourceType` — it answers what this source can
actually serve.

It is not a catalogue in the §10 sense. The Foundry model catalogue lives on the management
plane, needs an Azure subscription, and has no notion of a content-addressed version. A
`ModelRegistryType` over it would be a projection of a browsing experience, and one that
could not populate `Digest` on any `ModelResourceType` in it.

If you want §10 with real digests, the source has to be a registry that is content-addressed
— see [the Hugging Face guide](hugging-face.md), which is the one in this set that is.

## Residency, egress and retention

Nothing in the API states any of these. All three are operator assertions.

| Member | Cloud | Foundry Local |
|---|---|---|
| `InferenceLocation` | `Cloud` | `OnServer` |
| `EgressPermitted` | `true` | `false` |
| `DataJurisdiction` | the region the resource is in | the site |
| `RetainsInput` | `false` under the standard contract | `false` |
| `EgressPolicyUri` | your policy document | — |

`DataJurisdiction` comes from the region you created the resource in, and someone has to
write it down: the API will not tell you, and a resource created in the wrong region answers
exactly as convincingly as one created in the right one.

`EgressPermitted` is `true` for the cloud service and no encryption changes that. §9.5 makes
the point and it is worth repeating because it is the mistake people make: TLS answers who
can read the payload in flight, not whether it left the site. A client refusing to send
process data off-premises needs the second answer, and needs it before it calls.

`RetainsInput` asks whether the far end **keeps** the input after serving it, which is a
wider question than whether it trains on it. Azure's contract states that customer data is
not used to train foundation models; that is a contractual statement rather than a field in
a response, and it does not by itself answer logging, abuse monitoring or evaluation.

So publish `false` only where the operator has established that none of those retain input
for this resource, and `true` where any of them does. It is the operator asserting it
either way — there is no response field to read — and the member is worth nothing if it is
filled in from the first sentence of a marketing page rather than from the configuration.

## What this system does not tell you

- **Which weights answered.** No digest, anywhere, on any call. `Digest` and
  `DigestAlgorithm` stay empty, and `DigestProvenance` is `NotAvailable` under
  §12.1.1. Do not hash the model name to fill them.
- **What the model was trained on.** Nothing maps to `TrainedOn` or `DatasetType`. If
  lineage matters, it comes from the model card or the supplier, by hand.
- **Whether the model behind a name changed.** A `Pinned` deployment here is pinned to a
  string. The provider's versioning policy is what holds it still; the Server cannot verify
  it and should not imply otherwise.
- **Where your data went, or whether it was kept.** Both are contract terms, recorded as
  operator assertions in `DataJurisdiction`, `EgressPermitted` and `RetainsInput`.
- **Its own health, before you call it.** There is no dedicated health endpoint on the
  inference plane; `TestConnection` is a listing call whose success is the signal. That is
  enough to distinguish a wrong credential from a wrong URL, which is what commissioning
  needs it for.

## Conformance units

The cloud arrangement is an **AI Inference Gateway Server**: it reaches the
**AI-Base**, **AI-Invoke**, **AI-OffServer**, **AI-Federation** and
**AI-Residency** facets that §13.3 bundles for a hosted inference Server.
Foundry Local is the same call shape on the same host, so that arrangement is an
**AI Inference Device Server** instead.

Reachable against Azure AI Foundry: **AI-Base**, **AI-Invoke**, **AI-InvokeAsync**,
**AI-Transfer**, **AI-OffServer**, **AI-Federation**, **AI-Residency**.

Out of reach without something else: **AI-Catalogue** and **AI-Import** need a
content-addressed registry; **AI-Signatures** needs tensor shapes this contract does not
carry; **AI-Learning** needs training, which is not what this is.

## Sources

- [Azure AI Foundry Model Inference REST API](https://learn.microsoft.com/en-us/rest/api/microsoft-foundry/modelinference/)
- [API version lifecycle](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle)
- [Foundry Local — get started](https://learn.microsoft.com/en-us/azure/foundry-local/get-started)
- [Azure OpenAI batch](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/batch)
