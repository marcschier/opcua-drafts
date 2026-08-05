# Implementing this specification against real systems

Informative. Nothing here is normative, and nothing here introduces a member: every one is
defined in [the specification](../../../ai-model-management/OPC-UA-AI-Model-Management.md).

The specification is vendor-neutral on purpose. §9.2 names the `ApiDialectEnum` literals
for what a contract *does* rather than for whoever published it first, because a literal in
a standard should not be an advertisement. That is right for the normative document, and it
leaves an implementer holding a question it does not answer: they are not integrating "a
REST chat-completions contract", they are integrating Azure AI Foundry, or Amazon Bedrock,
or the Triton server already running in the plant.

These guides answer it. One per system, each saying which member takes which field, and —
more usefully — which members the system gives you nothing to fill.

## The guides

| Guide | What it is | `ApiDialect` |
|---|---|---|
| [Azure AI Foundry](azure-ai-foundry.md) | hosted inference, and Foundry Local on the machine | `RestChatCompletions` |
| [OpenAI](openai.md) | hosted inference | `RestChatCompletions` |
| [Amazon Bedrock](aws-bedrock.md) | hosted inference | `Proprietary` |
| [Amazon SageMaker](aws-sagemaker.md) | hosted endpoints serving your own container | `Proprietary` |
| [NVIDIA NIM](nvidia-nim.md) | self-hosted microservices | `RestChatCompletions` |
| [NVIDIA Triton](nvidia-triton.md) | self-hosted inference server | `OpenInferenceProtocol`, `TensorRemoteProcedure` |
| [Google Vertex AI](google-vertex-ai.md) | hosted inference | `Proprietary` |
| [Hugging Face](hugging-face.md) | a catalogue, not a serving surface | — |
| [KServe / Open Inference Protocol](kserve-open-inference-protocol.md) | the vendor-neutral baseline | `OpenInferenceProtocol` |
| [Embedded runtimes](embedded-runtimes.md) | ONNX Runtime and llama.cpp, in process | `EmbeddedRuntime`, `RestChatCompletions` |
| [Another OPC UA Server](opc-ua-server.md) | federating to a Server implementing this specification | `OpcUaInference` |

Every `ApiDialectEnum` literal is exercised by at least one guide, and
`tools/validate_examples.py` checks that it stays that way. A dialect nobody could show an
example of would be a literal worth removing.

Read [Another OPC UA Server](opc-ua-server.md) against any of the others when you want the
shortest statement of what this specification is for. It is the only guide in the set where
nothing is lost, because the remote system has the same members — every other guide is an
exercise in deciding what to do about the ones it does not have.

## The shape every guide follows

The same nine sections in the same order, so that the tables mean something and so that a
reader who has read one guide can skim the next:

1. What the system is.
2. **The `ModelSourceType`** — the filled member table.
3. **Identity** — how the endpoint's model naming becomes `Publisher`, `Name` and `Version`.
4. **`Invoke`** — the request and response mapping, including `UsageDataType` and
   `FinishReasonEnum`.
5. **Asynchronous inference** — whether `InvokeAsync` has anything native to map onto.
6. **Large payloads** — whether `BeginTransfer` has anything native to map onto.
7. **The catalogue** — how §10 is satisfied, or why it cannot be.
8. **Residency, egress and retention** — what the operator asserts because the API does not.
9. **What this system does not tell you.**

Section 9 is the one to read first. A mapping document that lists only what maps is
marketing; what an implementer needs before committing is the list of things they will have
to source from somewhere else, or decide to live without.

## What none of them gives you

Across the set, eight of the eleven arrangements reach the **AI Inference Gateway Server**
profile, two reach **AI Inference Device Server**, one reaches **AI Model Catalogue
Server**, and none reaches **AI Model Lifecycle Server**. That last is not a shortcoming of
the profile: these eleven are inference and catalogue systems, and none of them is a plant
that trains, which is the shape clause 7 was written for.

**An artefact digest.** Not Azure AI Foundry, not OpenAI, not Bedrock, not SageMaker, not
NIM, not Triton, not Vertex AI. Model identity on every hosted inference platform in this
set is a name string, sometimes carrying a date — `gpt-4o-2024-08-06`,
`meta/llama-3.1-8b-instruct`. None of them returns a cryptographic hash of the weights that
answered.

Two entries are exceptions, and neither is a hosted platform. Hugging Face is
content-addressed as a catalogue, with an immutable commit SHA per revision and a `sha256`
per LFS-stored file. An [embedded runtime](embedded-runtimes.md) holds the artefact on the
machine, so the Server can hash the file itself — which is the only arrangement in the set
where a digest is something this Server computed rather than something it was told.

Three consequences worth taking seriously:

- `Digest` and `DigestAlgorithm` are Mandatory members (§6.2) and stay empty against a
  hosted endpoint. §12.1 requires a Server to populate `Digest` for every model **whose
  artefact is obtainable through `ArtifactUri`**, and a hosted model's is not, so the
  obligation does not bite. What the Server states instead is `DigestProvenance`
  `NotAvailable`, which is Mandatory and always answerable: the absence is recorded rather
  than merely left, and a client can tell a source that publishes no digest from a Server
  that declined to carry one.
- Filling `Digest` with something derived from the model's name is what would defeat §12.1
  entirely. Every guide in this set met a different tempting value — a response
  fingerprint, a resource name, a storage entity tag, a repository commit identifier — and
  §12.1.1 prohibits all of them in one rule, because each looks like an artefact digest,
  is not one, and will eventually be compared against a real one.
- A `Pinned` deployment against a hosted endpoint is pinned to a **name**. The binding says
  the artefact behind it cannot change without an observable change to the deployment, and
  what actually enforces that is the provider's policy rather than anything the Server can
  verify. That is a materially weaker guarantee than the same word carries against an
  artefact the Server holds, and an audit process designed around it should know which one
  it has.
- The `Stage` import mode of §10.3 is the only path in this set that ends with a digest the
  Server computed from bytes it fetched, and §10.4's verification — refusing to deploy on a
  mismatch — is a real gate only there and on an embedded runtime. Those are also the only
  two arrangements that reach `DigestProvenance` `VerifiedOnStage`.

`DigestProvenance` is worth reading as the axis this whole set varies along, because it
grades the evidence rather than merely recording its presence:

| Value | Where it is reachable in this set |
|---|---|
| `NotAvailable` | Every hosted inference API: Foundry, OpenAI, Bedrock, SageMaker's inference plane, Vertex AI, NIM, Triton, base OIP |
| `DeclaredBySource` | Hugging Face, whose tree API declares a per-file `sha256` the Server can forward without hashing anything; and a federated peer Server, whose digest is an assertion received |
| `ComputedByServer` | An [embedded runtime](embedded-runtimes.md), where the artefact is a local file and hashing it costs nothing |
| `VerifiedOnStage` | A `Stage` import from a catalogue that declared a digest — in practice Hugging Face, or a peer registry |

Read down that column and the pattern is that **evidence tracks custody**. A Server can say
something strong about an artefact exactly to the degree it has held the bytes, and no
amount of vendor cooperation short of publishing a content hash changes that. It is also
why the embedded case is not the poor relation it looks like: it is the only arrangement
here where a Server can produce evidence entirely on its own.

**Training lineage, data residency, and whether your input is retained.** No inference API
in this set states any of them in a response. `TrainedOn`, `DataJurisdiction`,
`EgressPermitted` and `RetainsInput` are therefore operator assertions: someone reads the
contract and the region configuration and writes down what is true. The model gives them a
place to write it down and a client a way to read it, which is the whole of what a protocol
can do here.

That these are assertions rather than measurements is not a weakness of the model. It is
the situation, stated.

There is one exception, and it is the case where an assertion can be checked against
another: where a deployment federates to another Server implementing this specification,
§9.5 obliges it to read that Server's declarations and forbids publishing anything more
permissive. [The federation guide](opc-ua-server.md) works it through. It propagates
honesty rather than establishing it — but it closes the case where every Server in a chain
is truthful and the answer still comes out wrong because nobody was obliged to look up.

**A model's age, and how long it has left.** These split the set in a way none of the other
questions do, and the split runs the opposite way to the digest one.

Six of the eleven publish a vintage — `created` on OpenAI, Azure and NIM, `createTime` and
`updateTime` on Vertex AI, `lastModified` on Hugging Face, `startOfLifeTime` on Bedrock —
so `PublishedAt` and `LastModifiedAt` (§6.2.3) are answerable more often than `Digest` is.
`LastModifiedAt` matters more than it looks: a deployment with `VersionBinding` `FollowsRef`
can have the artefact change beneath it with nothing else changing, and §12.3.1's audit
trail points at a job record that a source-side move never produces. This is the member
that makes the move visible at all.

Exactly one system says when a model **stops**. Bedrock's `modelLifecycle` carries
`legacyTime` and `endOfLifeTime`, and nothing else in the set has an equivalent. One vendor
out of eleven is a thin basis for a member and it is in the model anyway, because on that
date the deployment does not degrade — it stops, `FallbackPolicy` fires, and where that is
`FallBackTo` the line keeps producing while something outside the qualified configuration
answers. §11.1 sets out the reasoning. Every other availability facility here is a way of
coping after the fact; `SupportedUntil` is the only one whose value is a date in the future.

**Where the large data actually lives.** Every hosted platform in the set takes a storage
URI in and out — OpenAI and Azure `file_id`, Bedrock's S3 input and output configuration,
SageMaker's `InputLocation` header, Vertex's `fileUri` — and none of the self-hosted four
does. That is not a coincidence: a hosted platform is on the far side of a network from
your data, and a self-hosted runtime is not.

The distinction §8.6.1 draws is worth carrying into every mapping. *A payload too large to
carry* is a transport problem and `BeginTransfer` solves it. *Data that never needed to
move* is not a transport problem at all, and chunking a batch that already sits in the
plant's object store copies it twice for no benefit. `PayloadUri` is for the second, and it
comes with an obligation these guides state repeatedly: a URI the execution site reads is a
path the input data takes, so §9.5's `EgressPermitted` governs it exactly as it governs the
endpoint.

## Reading the mappings

`AuthenticationKind` classifies **what is stored**, not which handshake is performed —
§9.2 states the rule, and it is what makes the member answerable across systems whose
handshakes have nothing in common. It is also why §9.2 prefers `WorkloadIdentity`: it is
the one value under which no secret exists anywhere for an attacker to read.

AWS is the case that shows the rule working. SigV4 is not one of the five literals and does
not need to be: signed by an assigned IAM role it is `WorkloadIdentity`, because nothing is
stored; signed by static access keys it is `ApiKey`, because something is. One scheme, two
values, decided by what an attacker could steal. [The Bedrock guide](aws-bedrock.md) works
it through, and points `EndpointDescriptionUri` at the handshake for a reader who needs it
recorded exactly.

`ApiDialect` is read the same way — it names the contract *this Server speaks to that
endpoint*, not everything the endpoint could offer. The same runtime is `EmbeddedRuntime`
in process and `RestChatCompletions` over its own loopback server; the same host is
`Proprietary` through its native API and `RestChatCompletions` through its
OpenAI-compatible one.

## Throttling, on every one of them

`Reachability` separates `Throttled` from `Unreachable` on purpose, and §9.4 gives the
reason: the two look alike from outside and call for opposite responses. An unreachable
endpoint should be failed over. A throttled one will serve again shortly, and failing it
over merely moves the load onto a weaker model for nothing.

Every hosted platform in this set throttles, and the mapping is the same for all of them
because it is HTTP rather than anyone's API:

| Model | From |
|---|---|
| `Reachability` = `Throttled` | HTTP 429, or a documented capacity refusal |
| `RateLimit.RetryAfter` | a Duration, parsed from the `Retry-After` header — which carries either seconds or an HTTP date, so it is converted rather than copied |
| `RateLimit.Limit`, `RateLimit.Remaining`, `RateLimit.Interval` | rate-limit response headers, where the platform returns them |
| `RateLimit.UnitKind` | `requests` or `tokens`, depending on which quota bound |

Do not count a 429 as a failure. `ConsecutiveFailures` answers *is this endpoint broken*,
and a quota refusal is an endpoint working exactly as contracted. Folding the two together
produces a deployment that reports itself as failing whenever it is busy, which is both
wrong and the moment a supervisory client most needs the report to be right.

Which headers a given platform returns, and under what names, is documented per platform
and is not reproduced here — the shape above is what the model asks for, and the header
names are the one part of this that changes without notice.

## Currency

Each guide records the date its vendor facts were verified and links to primary
documentation. Vendor APIs move and nothing here can keep up with them automatically —
`tools/validate_examples.py` checks these guides against the information model, which is
the part that can be checked. Dating the rest is more honest than implying it is fresh.
