# Hugging Face

Informative. Every member named here is defined in
[the specification](../../../ai-model-management/OPC-UA-AI-Model-Management.md); this guide
introduces none. Vendor facts verified 2026-08-05 against the documentation linked at the
end.

Hugging Face Hub is a catalogue, not a serving surface. It can be projected as a model
registry, and it can tell a Server something the hosted inference systems in this guide set
cannot: which immutable revision and which LFS-stored file digest describe the artefact.

That distinction is the spine of this mapping. A Hugging Face commit SHA identifies a
repository revision; a per-file LFS `sha256` identifies an artefact file. §10.4 verifies a
fetched artefact against a declared digest, so the file digest is the value that can make
that gate real.

## The `ModelSourceType`

Hugging Face Hub is not an inference endpoint. Most of the serving-oriented members are
therefore either empty or operator-maintained, and the useful operation is catalogue
listing rather than `Invoke`.

| Member | Hugging Face Hub |
|---|---|
| `SourceId` | your name for this Hub catalogue source |
| `EndpointUri` | `https://huggingface.co/api/` |
| `ApiDialect` | empty; this is not an inference wire contract |
| `EndpointDescriptionUri` | `https://huggingface.co/.well-known/openapi.json` |
| `AuthenticationKind` | `Anonymous` for public repositories, `BearerToken` where private or gated repositories are accessed |
| `CredentialReference` | names the Hugging Face token — never the value |
| `TokenAudience` | empty |
| `Reachability` | maintained from Hub API calls such as listing or repository detail |
| `Capabilities` | catalogue capabilities, not inference capabilities |
| `TestConnection` | a Hub API probe |
| `ListModels` | backed by `GET /api/models` and filtered by the Server |

`AuthenticationKind` is `BearerToken` only when the Server stores a Hugging Face token in
its credential store. A public anonymous projection is `Anonymous`, and the public xrproxy
adapter takes that stricter route: it reads the Hub without an auth token and rejects
incoming authorization headers.

Gated and private repositories matter at the catalogue boundary. A gated model may be
visible as metadata while its artefacts require an entitlement; a private repository needs
a token even to read. In both cases `CredentialReference` names the credential used by the
Server, and §9.2's rule applies unchanged: the address space never carries the token.

## Identity

The Hub gives a better identity than a hosted inference endpoint because a repository has
an owner, a name and immutable commits.

| Member | From | Note |
|---|---|---|
| `Publisher` | `author` or the owner segment of `id` | maps to `ModelPublisherType` |
| `Name` | the repository basename | maps to `ModelResourceType` |
| `Version` | commit `sha` | immutable version identity |
| `ModelId` | full repo id, such as `google-bert/bert-base-uncased` | keep it verbatim |
| `TaskKind` | `pipeline_tag` | where the field is present |
| `Framework` | `library_name` | where the field is present |
| `Card` | `cardData` and the model card | structured metadata plus the human card |
| `Digest`, `DigestAlgorithm` | per-file LFS `sha256` from the tree API | artefact-level digest, not the commit SHA |
| `ArtifactUri` | the selected file URL or Hub resource URL | choose the artefact being imported |
| `ProvenanceUri` | the Hub repository or xRegistry resource URL | points back to the catalogue entry |

The commit SHA is a Git object identity for the repository revision. It answers "which
revision of this repository did I mean?" and is the right `Version` for the catalogue
resource.

It is not the hash of a weights file. `GET /api/models/{owner}/{repo}/tree/{rev}` returns
file entries, and LFS-stored files include an `lfs` field with `sha256`. That is the value
to publish as `Digest` with `DigestAlgorithm` set to the corresponding SHA-256 algorithm
name when the model artefact is one of those LFS files.

Branches and tags are mutable pointers to commits. A deployment pinned to a commit is
`Pinned`; a deployment tracking `main` or another branch is `FollowsRef` with `BoundRef`
set to that ref. §9.3 is exactly about this case, and §12.3 makes the consequence plain:
repointing the followed ref changes what the equipment runs and must be treated as an
authorization-bearing act, not as harmless configuration.

## `Invoke`

The Hub does not define `Invoke`. A Server importing from or federating to the Hub needs a
separate runtime: Hugging Face Inference Endpoints, TGI, vLLM, transformers, llama.cpp or
some other serving arrangement.

Where the runtime is a TGI-backed Hugging Face Inference Endpoint in chat mode, the call can
look like `RestChatCompletions` and follows the chat-completions mapping used by the other
guides: response JSON is returned as `ResponsePayload`, token counts populate
`UsageDataType`, and finish reasons map to `FinishReasonEnum` as that dialect defines.

Where the runtime is the older task-specific endpoint shape, the request is task-specific
JSON and the response usually has no token accounting. The Server can still return the
payload under §8.2, but `UsageDataType` may be empty and `FinishReason` will usually be
`Stop` for success or `Error` for a failed or uninterpretable response.

Do not infer serving semantics from the catalogue entry. `pipeline_tag` is useful for
`TaskKind`; it is not a complete request or response contract.

## Asynchronous inference

The Hub has no batch inference API. Hugging Face Inference Endpoints may offer asynchronous
arrangements in some configurations, but the research did not verify a standard job-based
API that all endpoints expose.

So `InvokeAsync` is normally the Server's own job under §8.6. It accepts the request,
returns an `InferenceJobType`, runs the chosen runtime, and records the same `ModelUsed`,
`Usage`, `FinishReason` and result payload that `Invoke` would have returned.

## Large payloads

The Hub stores repository files through Git and Git LFS. That is catalogue storage, not an
inference transfer protocol.

`BeginTransfer` is therefore the Server's own OPC UA transfer path under §8.2.4. For a
staged import, the Server fetches the selected artefact from the Hub, verifies the LFS file
digest under §10.4 and then exposes the staged artefact or deployment locally. For an
inference request whose payload is too large, the Server reassembles the request and sends
one ordinary call to whatever runtime it uses.

## The catalogue

This is where Hugging Face fits the specification.

The public xrproxy Hugging Face adapter already uses the xRegistry shape that Annex B cites:

| Hugging Face concept | xRegistry concept | AI model-management type |
|---|---|---|
| owner or namespace | group | `ModelPublisherType` |
| repository basename | resource | `ModelResourceType` |
| commit SHA | version identity | `ModelReferenceDataType.Version` / `ModelType.Version` |
| branches and tags | mutable refs | `MutableRefs`, `FollowsRef`, `BoundRef` |

For `google-bert/bert-base-uncased`, the proxy path is
`/huggingfaceregistries/google-bert/models/bert-base-uncased`, and a version path appends
`/versions/{sha}`. The owner is the group; the repository is the resource; the commit SHA is
the immutable version.

That is the shape §10.1 requires. It is also the one case in this guide set where §10.4 can
be an actual protection. Hosted inference platforms identify models by strings and return
no weight hash. Hugging Face can give a Server both the immutable revision and, for
LFS-stored artefacts, the per-file SHA-256 that the Server can recompute after staging.

The import rule is precise:

- use the commit SHA as the version identity;
- use the selected LFS file's `sha256` as `Digest`;
- set `DigestAlgorithm` to SHA-256;
- fail the staging import if the fetched bytes do not match, as §10.4 requires.

`cardData` and the model card relate to `Card` on `ModelType` and to §11.1. They are not a
substitute for a digest, and the card's training-data information is not guaranteed to be a
structured `DatasetType` lineage.

## Residency, egress and retention

The Hub API does not tell a Server the plant-level residency answer. The operator states
it on the deployment that uses the model.

| Member | Hugging Face catalogue import | Hugging Face-hosted inference |
|---|---|---|
| `InferenceLocation` | depends where the staged model runs | usually `Cloud` for managed endpoints |
| `EgressPermitted` | `false` after a local staged import; `true` while fetching from the Hub if the fetch crosses the boundary | `true` |
| `DataJurisdiction` | the operator's site or zone after staging | the contracted endpoint region or jurisdiction |
| `RetainsInput` | `false` for local inference if no remote runtime receives input | operator assertion for managed inference |
| `EgressPolicyUri` | your policy document | your policy document |

A staged local deployment is the interesting outcome: model bytes came from the Hub, but
inference data does not have to. §9.5 asks where input goes during invocation, not where the
artefact was obtained.

## What this system does not tell you

- **Which file is the model artefact.** A repository can contain several large files. The
  catalogue gives file digests; the Server or import policy must choose which file is the
  deployable artefact.
- **A single repository-wide artefact digest.** The commit SHA identifies a revision. The
  LFS `sha256` identifies one file. Do not publish the commit SHA as the artefact `Digest`.
- **Structured training lineage.** Model cards and `cardData` can describe training data,
  but the research did not verify a structured API field that populates `TrainedOn` or a
  `DatasetType` without human or policy interpretation.
- **Inference-plane provenance.** Inference responses do not return the Hub commit or file
  digest that answered. If that matters, bind the deployment to the imported `ModelType` and
  return that node as `ModelUsed`.
- **Residency and retention.** Hub and endpoint responses do not populate
  `DataJurisdiction`, `EgressPermitted` or `RetainsInput`; the operator asserts them.

## Conformance units

Reachable against a Hugging Face catalogue projection: **AI-Base**, **AI-Catalogue** and
**AI-Import**. **AI-Residency** is reachable for deployments the Server creates from the
imported model, because the operator can state the invocation boundary.

Reachable only with a separate runtime: **AI-Invoke**, **AI-InvokeAsync**, **AI-Transfer**,
**AI-OffServer**, **AI-Federation** and **AI-Signatures** depend on how the model is served
after catalogue import. **AI-Learning** needs training workflow support, which the Hub
catalogue does not provide.

## Sources

- [Hugging Face Hub API documentation](https://huggingface.co/docs/hub/api)
- [Hugging Face Hub OpenAPI document](https://huggingface.co/.well-known/openapi.json)
- [Hugging Face Inference Endpoints documentation](https://huggingface.co/docs/inference-endpoints/en/index)
- xregistry/xrproxy Hugging Face adapter README, verified at SHA `ac3fa09ec72c851c62435da2104269f20b439640`
- xregistry/xrproxy `huggingface/src/hf-client.ts`, verified at SHA `6e37565e75bfbfd023e9db8042d865484d132a77`
