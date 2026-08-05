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

**An artefact digest.** Not Azure AI Foundry, not OpenAI, not Bedrock, not SageMaker, not
NIM, not Triton, not Vertex AI. Model identity on every hosted inference platform in this
set is a name string, sometimes carrying a date — `gpt-4o-2024-08-06`,
`meta/llama-3.1-8b-instruct`. None of them returns a cryptographic hash of the weights that
answered.

Hugging Face is the exception, and it is not an inference platform: as a catalogue it is
content-addressed, with an immutable commit SHA per version and a `sha256` per LFS-stored
file.

Three consequences worth taking seriously:

- `Digest` and `DigestAlgorithm` are left empty against a hosted endpoint. §11 permits this,
  and a Server **shall not** invent a value — hashing the model's name produces something
  that looks like an artefact digest, is not one, and will eventually be compared against a
  real one.
- A `Pinned` deployment against a hosted endpoint is pinned to a **name**. The binding says
  the artefact behind it cannot change without an observable change to the deployment, and
  what actually enforces that is the provider's policy rather than anything the Server can
  verify. That is a materially weaker guarantee than the same word carries against a staged
  artefact, and an audit process designed around it should know which one it has.
- The `Stage` import mode of §10.3 is the only path in this set that ends with a digest the
  Server computed itself, because it is the only one where the Server holds the bytes.

**Training lineage, data residency, and whether your input is retained.** No inference API
in this set states any of them in a response. `TrainedOn`, `DataJurisdiction`,
`EgressPermitted` and `RetainsInput` are therefore operator assertions: someone reads the
contract and the region configuration and writes down what is true. The model gives them a
place to write it down and a client a way to read it, which is the whole of what a protocol
can do here.

That these are assertions rather than measurements is not a weakness of the model. It is
the situation, stated.

## Reading the mappings

`AuthenticationKind` classifies **what is stored**, not which handshake is performed. That
is what makes it answerable across systems whose handshakes have nothing in common, and it
is why §9.2 prefers `WorkloadIdentity`: it is the one value under which no secret exists
anywhere for an attacker to read.

AWS is the case that tests it. SigV4 is not one of the five literals, and the two AWS
guides map it by what it stores: an IAM role attached to the pod or instance is
`WorkloadIdentity`, because nothing is stored; static access keys are `ApiKey`. The
reasoning is spelled out in [the Bedrock guide](aws-bedrock.md).

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
| `RateLimit.RetryAfter` | the `Retry-After` response header |
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
