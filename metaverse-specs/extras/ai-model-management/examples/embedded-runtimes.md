# Embedded runtimes

Informative. Every member named here is defined in
[the specification](../../../ai-model-management/OPC-UA-AI-Model-Management.md); this guide
introduces none. Vendor facts verified 2026-08-05 against the documentation linked at the
end.

ONNX Runtime and llama.cpp are local execution stacks. The model artefact is a file on the
machine, and inference is normally a library call in the Server's own process. llama.cpp also
ships `llama-server`, an HTTP server with an OpenAI-compatible surface; that case is covered
separately because the dialect follows the contract the Server speaks, not the software behind
it.

This is the happy path for §10.4. The operator holds the `.onnx` or `.gguf` file, so the
Server can hash the bytes it is about to run. Hosted endpoints in this guide set cannot offer
that: they name a model, but they do not expose a digest of the weights that answered.

## The `ModelSourceType`

| Member | ONNX Runtime / libllama | `llama-server` on loopback |
|---|---|---|
| `SourceId` | your name for the local runtime | your name for the loopback server |
| `EndpointUri` | empty; there is no endpoint | `http://127.0.0.1:{port}/v1/` |
| `ApiDialect` | `EmbeddedRuntime` | `RestChatCompletions` |
| `EndpointDescriptionUri` | your documentation for the library binding, if useful | not required; the dialect names the contract |
| `AuthenticationKind` | `Anonymous` | `Anonymous` |
| `CredentialReference` | empty | empty |
| `TokenAudience` | empty | empty |
| `Reachability` | maintained from artefact-load and local-run outcomes | maintained from HTTP probes and call outcomes |
| `ConsecutiveFailures` | consecutive load, missing-file or local execution failures | consecutive HTTP or execution failures |
| `Capabilities` | what the wrapper exposes | chat, completions, embeddings and other enabled routes |

`EmbeddedRuntime` means the Server reaches the runtime through a library rather than a
socket. `EndpointUri` is therefore empty, and a source of this kind is not unreachable in
the network sense. It is present or absent: the file exists and can be loaded, or it cannot.
`TestConnection` is still useful, but it probes the configured artefact path and runtime
initialisation rather than a port. `Reachability` and `ConsecutiveFailures` therefore record
local readiness, not routing or firewall health.

`llama-server` is different. The same llama.cpp weights reached through its HTTP process are
`RestChatCompletions`, with `EndpointUri` on loopback and `AuthenticationKind` `Anonymous`.
The dialect describes the contract this Server speaks to the execution site. It does not
describe the product, the file format or the vendor. A Server that calls libllama directly
and a Server that calls `llama-server` can execute the same `.gguf` file and still publish
different `ApiDialect` values, because they speak different contracts.

## Identity

The local file is the identity anchor, not a provider-side deployment name.

| Member | ONNX Runtime | llama.cpp |
|---|---|---|
| `Publisher` | operator, model producer metadata, or configured catalogue owner | operator, model family owner, or configured catalogue owner |
| `Name` | configured name or metadata-derived model name | configured name or filename-derived model name |
| `Version` | model version metadata where present | configured revision or file/catalogue revision |
| `ModelId` | stable local identifier, often the file path plus digest | stable local identifier, often the file path plus digest |
| `Framework` | ONNX / ONNX Runtime, where the file metadata supports it | llama.cpp |
| `Format` | ONNX | GGUF |
| `Digest`, `DigestAlgorithm` | hash of the `.onnx` artefact | hash of the `.gguf` artefact |
| `ArtifactUri` | local file URI | local file URI |
| `ParameterCount`, `Quantization` | fill where the artefact metadata provides them | fill from GGUF metadata where available |

The digest is the standout difference from hosted systems. `Digest` and `DigestAlgorithm`
can be a genuine artefact hash, and `ArtifactUri` can point at the file the Server actually
opens. A `Pinned` deployment is then pinned to bytes, not to a string that a provider
promises to keep stable. That is what the word pinned ought to mean, and this arrangement is
where the model can say it without pretending.

ONNX model files can carry metadata such as producer, domain, model version and custom
metadata, and the loaded session exposes the input and output tensor names, element types and
shapes. Map those to `Framework`, `Format`, `Version`, `Inputs` and `Outputs` where the file
actually carries them. That makes **AI-Signatures** reachable for tensor models: a client can
read the shape contract from `ModelType` instead of discovering it from a failed run, which is
the distinction §6.2 exists to preserve.

GGUF metadata can carry architecture, quantization and parameter-count information. Where the
Server reads it from the header, `Quantization` and `ParameterCount` are not operator notes;
they are properties of the artefact. Hosted inference surfaces in the set do not give the
Server that view of the weights.

## `Invoke`

For ONNX Runtime and libllama the mapping is a wrapper decision. The Server receives the
opaque §8.2 payload, converts it to the runtime's input objects, runs the local call, and
returns the runtime output as the response payload. There is no remote envelope to preserve.

For `llama-server`, the request body goes through the OpenAI-compatible route the deployment
uses, usually `/v1/chat/completions`, `/v1/completions` or `/v1/embeddings`.

| Output | ONNX Runtime / libllama | `llama-server` |
|---|---|---|
| response payload | wrapper-defined bytes or JSON | HTTP response body, verbatim |
| response content type | wrapper-defined | `application/json` |
| model used | the `ModelType` NodeId for the local file | the `ModelType` NodeId for the served file |
| `Usage.UnitKind` | empty unless the wrapper meters it | `tokens` |
| `Usage.InputUnits` | empty unless the wrapper meters it | prompt token count |
| `Usage.OutputUnits` | empty unless the wrapper meters it | completion token count |
| `Usage.TotalUnits` | empty unless the wrapper meters it | total token count |

Usage accounting is precise by case. `llama-server` uses an OpenAI-compatible response and
returns token counts, so `UsageDataType` can be populated with `tokens`. ONNX Runtime
in-process has no usage telemetry field in the research, so the Server should leave usage
empty unless its own wrapper has a metering rule it is prepared to document.

Finish reasons are also case-specific. The OpenAI-compatible llama.cpp surface includes a
finish-reason field; ordinary values map the same way as the other chat-completions guides:
`stop` to `Stop`, `length` to `Length`, tool calls to `ToolCall`, and filtering to
`Filtered` where the wrapper can detect it. The research did not verify llama.cpp's exact
values for unusual cases, so a Server should map unknown values to `Error` rather than
inventing a literal.

## Asynchronous inference

Neither ONNX Runtime nor llama.cpp gives the Server a native batch job API to map onto.
`InvokeAsync` is therefore the Server's own job, as §8.6 permits: it accepts the request,
creates the job node, runs the local inference, and stores the result there.

That is still worth implementing. A local run can be long even when it makes no network
call, especially for large models, slow CPUs or large inputs. The job outlives the client
Session that asked for it, which is the property synchronous `Invoke` cannot provide.

## Large payloads

Neither runtime provides a native file-upload or chunked-request facility that maps onto
`BeginTransfer`. For embedded runtimes that is not a limitation of the execution site: the
Server already owns the bytes once the OPC UA transfer completes.

`BeginTransfer` is therefore the Server's own Part 5 file exchange described in §8.2. The
client writes the request in chunks, the Server reassembles it, runs the local runtime, and
exposes the response through the same transfer object if it is too large for the inline
result. No ONNX Runtime or llama.cpp feature has to be arranged for that to work.

## The catalogue

There is no native ONNX Runtime catalogue API, and the research reports no llama.cpp
catalogue with version and digest. `llama-server` has `GET /v1/models`, and router mode can
list loaded or loadable models, but that is an execution listing rather than a §10 catalogue.

The Server can nevertheless satisfy §10 with local artefacts because it holds the files. A
configured directory, an internal registry or a staging area can be projected as catalogue
entries whose `ArtifactUri`, `Digest` and `DigestAlgorithm` are computed from the local file.
This is the one guide where §10.4 digest verification is a real gate rather than a missing
provider feature: staging computes the digest over the bytes received and refuses to deploy a
mismatch.

That buys something concrete. A hosted deployment can tell a client which name answered; a
local staged deployment can tell it which bytes answered. The cost is equally concrete:
someone must place, update, remove and audit model files on every machine that may run them.

## Residency, egress and retention

| Member | ONNX Runtime / libllama | `llama-server` on loopback |
|---|---|---|
| `InferenceLocation` | `OnServer` | `OnServer` |
| `EgressPermitted` | `false` | `false` |
| `DataJurisdiction` | the site | the site |
| `RetainsInput` | `false`, unless the wrapper logs it | `false`, unless the server or wrapper logs it |
| `EgressPolicyUri` | optional local policy | optional local policy |

Here `EgressPermitted` is not a contractual assertion about a provider. It is a property of
the architecture: the Server runs the model in-process, or calls a loopback HTTP process on
the same machine. There is no provider network call for input to take. If the wrapper writes
prompts, tensors or outputs to logs, that is retention, not egress, and it belongs in
`RetainsInput` and the operator's policy.

`DataJurisdiction` is still worth filling. Local does not mean ungoverned; it means the
processing location is the site that owns the machine, which is exactly the question §9.5
asks a deployment to answer.

## What this system does not tell you

- **Who approved the file.** A digest says which bytes are present, not that they are safe to
  run. `ProvenanceUri`, `Card` and the governance material of §11 still have to come from the
  operator's process or catalogue.
- **What the model was trained on.** Neither ONNX Runtime nor llama.cpp exposes training
  lineage. If lineage matters, it comes from a model card, a registry or manual governance.
- **A remote health signal for embedded runtimes.** There is no endpoint to ask. The only
  useful probe is loading the file and, where appropriate, running a small local check.
- **Provider-managed scale.** Running on the Server gives excellent provenance and residency,
  but someone owns the disk layout, accelerator drivers, model updates and rollback plan on
  every machine.
- **Native jobs or native transfers.** `InvokeAsync` and `BeginTransfer` are Server features
  here. That is acceptable, but it means their lifecycle, expiry and cleanup are your design.

## Conformance units

Reachable against embedded runtimes: **AI-Base**, **AI-Invoke**, **AI-InvokeAsync**,
**AI-Transfer**, **AI-Residency**, **AI-Catalogue** and **AI-Import**. **AI-Signatures** is
reachable for ONNX models where the Server publishes the tensor signatures it reads from the
loaded model.

Out of reach without something else: **AI-Learning** needs a training loop; **AI-OffServer**
does not describe an `OnServer` deployment; **AI-Stream** needs a subscription or data-channel
stream the Server chooses to implement.

## Sources

- [ONNX Runtime GenAI C++ API](https://onnxruntime.ai/docs/genai/api/cpp.html)
- [ONNX Runtime GenAI Python API](https://onnxruntime.ai/docs/genai/api/python.html)
- [llama.cpp server tools](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)
