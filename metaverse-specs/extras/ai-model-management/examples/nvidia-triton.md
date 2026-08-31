# NVIDIA Triton Inference Server

Informative. Every member named here is defined in
[the specification](../../../../source/metaverse-specs/ai-model-management/spec.md); this guide
introduces none. Vendor facts verified 2026-08-05 against the documentation linked at the
end.

NVIDIA Triton Inference Server is a self-hosted inference runtime for configured models.
It serves the KServe v2 Open Inference Protocol over HTTP
and gRPC, with readiness and metadata endpoints beside inference.

Triton is the guide in this set where tensor signatures matter. Its metadata endpoint
returns input and output names, datatypes and shapes, which map directly onto `Inputs` and
`Outputs` on `ModelType` and make **AI-Signatures** reachable without guessing.

## The `ModelSourceType`

| Member | REST endpoint | gRPC endpoint |
|---|---|---|
| `SourceId` | your name for the Triton server | as REST |
| `EndpointUri` | `http://{host}:8000/v2/` by default | `{host}:8001` by default |
| `ApiDialect` | `OpenInferenceProtocol` | `OpenInferenceProtocol` |
| `EndpointDescriptionUri` | the KServe v2 protocol documentation, if published | the Triton gRPC service definition, if published |
| `AuthenticationKind` | `Anonymous`, unless the operator adds a wrapper | as REST |
| `CredentialReference` | empty, or the name of the wrapper credential — never the value | as REST |
| `TokenAudience` | empty unless the wrapper requires one | as REST |
| `Reachability` | maintained from readiness endpoints and call outcomes | as REST |

Triton is the one system here where the same contract naturally appears over two
transports. Use `OpenInferenceProtocol` when this Server reaches Triton's OIP binding,
whether that is HTTP `POST /v2/models/{name}/infer` or the gRPC `ModelInfer` RPC.
`TensorRemoteProcedure` is reserved for a tensor-oriented RPC contract that is not OIP,
such as a dedicated inference server speaking its own predict RPC. The literal names the
contract this Server calls, not the transport.

The same distinction applies on the deployment side. A deployment that expects an OPC UA
caller to send an OIP body publishes `DeploymentType.ApiDialect` as
`OpenInferenceProtocol`, whether this Server forwards that body over HTTP or over gRPC.
The dialect tells the caller what payload contract it must satisfy; the transport is a
separate integration choice.

Triton does not include authentication in its core protocol. If an operator adds nginx,
Envoy or another gateway, §9.2 says `AuthenticationKind` describes the credential this
Server stores for that gateway.

## Identity

`GET /v2/models/{name}` returns model metadata: `name`, optional `versions`, `platform`,
`inputs` and `outputs`. `GET /v2` returns server metadata rather than model identity.

| Member | From | Note |
|---|---|---|
| `Publisher` | operator-chosen namespace | Triton does not expose a publisher field |
| `Name` | `name` | the repository model name |
| `Version` | the selected entry from `versions`, where used | Triton has a real version path segment |
| `ModelId` | `name` plus version when pinned | keep enough to reconstruct the endpoint path |
| `Framework` | `platform` | examples include backend platform strings |
| `Format` | operator assertion | not a separate OIP field |
| `PublishedAt`, `LastModifiedAt` | empty | OIP metadata exposes no model vintage timestamp |
| `Digest`, `DigestAlgorithm` | **not exposed by OIP v2** | see catalogue and import below |
| `DigestProvenance` | `NotAvailable` | OIP v2 returns no artefact digest |

Triton model versions are explicit: inference can target
`/v2/models/{name}/versions/{version}/infer`. That is a real version dimension, unlike
systems that carry a date or revision in a name string. A deployment that calls a specific
version is `Pinned`; a deployment that calls only `{name}` and accepts whichever version
the repository policy serves is a candidate for `FollowsRef`.

The trap is that an explicit version is still not a digest. It tells the Server which
repository version it addressed; it does not prove which bytes the repository mounted for
that version.

The research establishes Triton metadata fields for name, versions, platform and tensor
signatures. It does not establish a protocol field for the source publication time or for
the time the repository loaded the model, so `PublishedAt` and `LastModifiedAt` stay empty
unless a separate catalogue supplies them. §6.2.3 forbids using the Server's own discovery
or acquisition time as `PublishedAt`.

## `Invoke`

For REST, `Invoke` maps to `POST /v2/models/{name}/infer` or
`POST /v2/models/{name}/versions/{version}/infer`. For gRPC, it maps to `ModelInfer`.

| Output | From |
|---|---|
| `ResponsePayload` | the OIP response body or encoded gRPC response |
| `ResponseContentType` | `application/json` for REST, an implementation media type for gRPC |
| `ModelUsed` | the `ModelType` NodeId this deployment resolved to |
| `Usage.UnitKind` | empty when the model exposes no accounting output; otherwise the declared unit, per §8.2.3 |
| `Usage.InputUnits` | `0` when `UnitKind` is empty; otherwise the measured input count |
| `Usage.OutputUnits` | `0` when `UnitKind` is empty; otherwise the measured output count |
| `Usage.TotalUnits` | `0` when `UnitKind` is empty; otherwise the measured total count |
| `FinishReason` | `Stop` for a complete successful tensor response, or `Error` |
| `SafetyAssessment` | not provided by the protocol |
| `RetryAfter` | empty unless a wrapper supplies it |

OIP v2 returns named output tensors. It does not define token counts, a usage envelope or a
standard finish reason. If a model backend exposes counts or stop reasons as output
tensors, a Server may map them, but that is a model contract rather than a Triton protocol
feature.

Where it does not expose counts, §8.2.3 supplies the representation: `Usage` is returned
with an empty `UnitKind` and zero counts, and those zeros are not measurements.

The payload is still opaque to the OPC UA caller under §8.2. A Server may validate it
against `Inputs` before forwarding, which is exactly why the signatures are valuable, but
the domain meaning of the tensors belongs to the consuming specification.

## Asynchronous inference

OIP v2 has no handle-and-poll job API. Triton supports server-side dynamic batching, but
the client still sends a synchronous inference request and receives a synchronous response.

`InvokeAsync` is therefore an OPC UA-side job as §8.6 describes. The Server accepts the
request, returns an `InferenceJobType`, runs the Triton call and records the same
`ResponsePayload`, `ModelUsed`, `Usage` and `FinishReason` that `Invoke` would have
returned.

## Large payloads

The REST protocol carries tensor data in the request body, including base64-encoded bytes
for `BYTES` tensors. The research found no OIP v2 file upload or chunked transfer API.

gRPC streaming can be used for very large inputs, but that is still the Triton transport
chosen by this Server. It does not replace `BeginTransfer` for OPC UA clients. Under
§8.2.4, `BeginTransfer` lets the OPC UA client write the request through Part 5 `FileType`;
the Server then calls Triton by its chosen REST or gRPC route.

## The catalogue

Triton serves configured models, but OIP metadata is not a §10 catalogue entry and does
not carry a digest. Repository configuration is outside what OIP exposes; read Triton's
own documentation for how a deployment configures and manages the model repository.

The valuable metadata is the shape contract. `GET /v2/models/{name}` returns `inputs` and
`outputs` with tensor names, datatypes and shapes. Those map directly to `Inputs` and
`Outputs` on `ModelType`, whose semantics in §6.2 are name, element type, shape with `-1`
for a dynamic axis, and an optional layout hint.

That makes **AI-Signatures** reachable here. A client can check at configuration time that
the tensors it intends to send match what the model declares, instead of discovering a
shape mismatch as a failed production call. Most hosted chat-style systems in this set do
not expose enough information to do that.

`Stage` import under §10.3 needs a separate catalogue projection alongside Triton. That
projection supplies the `ModelRegistryType`, `ModelPublisherType`, `ModelResourceType` and
declared digest that §10.4 verifies; Triton alone does not expose them.

## Residency, egress and retention

Triton is self-hosted, so these answers come from the deployment topology and repository
policy rather than from the protocol.

| Member | Typical Triton deployment |
|---|---|
| `InferenceLocation` | `OnServer` or `EdgeOffServer` |
| `EgressPermitted` | `false` when Triton is inside the operator boundary |
| `DataJurisdiction` | the site, zone or storage jurisdiction of the serving deployment |
| `RetainsInput` | `false` unless logging or tracing stores request tensors |
| `EgressPolicyUri` | your plant or platform policy |

The readiness endpoints are a better operational source than the listing-call
approximation many hosted systems need. `GET /v2/health/ready` tests server readiness, and
`GET /v2/models/{name}/ready` or the versioned form tests model readiness. These are
natural inputs to `TestConnection`, `Reachability`, `LastSuccessAt` and
`ConsecutiveFailures`.

The cited research establishes Triton's metrics surface, but not a specific protocol field
that maps a per-deployment latency value into this model. A Server that needs
`ObservedLatency` therefore measures the call itself, which §6.4.3 permits; if it reports
`Degraded` on latency grounds, it publishes that measured value so the state can be
checked.

## What this system does not tell you

- **A content digest.** The cited OIP metadata exposes name, versions, platform and tensor
  signatures, not a hash of repository contents. `DigestProvenance` is `NotAvailable` for
  that projection; any digest comes from a separate catalogue.
- **A publisher.** The model repository names models; it does not state who published them.
  `Publisher` is an operator namespace unless a separate catalogue supplies one.
- **Usage accounting.** Token counts and finish reasons are not protocol fields. Treat them
  as model outputs only where the model explicitly declares them; otherwise `UsageDataType`
  uses the §8.2.3 not-metered sentinel.
- **Training lineage.** Nothing in the Triton protocol maps to `TrainedOn` or `DatasetType`.
- **Residency or retention.** Self-hosting gives the operator control of the answer; the
  answer still has to be recorded explicitly.

## Conformance units

A Triton reached across the plant network is an **AI Inference Gateway Server**
where the secure off-server endpoint and residency assertions below are present.
Triton on the same host as the OPC UA Server is an **AI Inference Device Server**
instead, because its `InferenceLocation` is `OnServer`.

Reachable against Triton: **AI-Base**, **AI-Invoke**, **AI-InvokeAsync**, **AI-Transfer**,
**AI-Federation**, **AI-Residency** and **AI-Signatures**. **AI-OffServer** is reachable
for a deployment whose `InferenceLocation` is not `OnServer`, which is what §13.2 asks for.
What that deployment must additionally satisfy is §12.2, and it is not optional: where
`InferenceLocation` is not `OnServer`, `EndpointUri` **shall** name an authenticated,
confidential scheme. Triton's default `http://{host}:8000/v2/` listener does not, so a
Triton reached across the plant network is fronted with TLS and authentication before this
facet is claimed. Triton on the same host is `OnServer`, where the question does not arise.

The unmetered case satisfies **AI-Invoke**: the Server returns `Usage` with empty
`UnitKind` and zero counts, and §13.2 accommodates that.

Out of reach from Triton alone: **AI-Catalogue** and **AI-Import**, because they need a
separate conforming registry projection with catalogue resources and declared digests, and
**AI-Learning**, because training and promotion lifecycle support are outside OIP v2.

## Sources

- [Triton Inference Server protocol documentation](https://github.com/triton-inference-server/server/blob/main/docs/protocol/README.md)
- [KServe v2 required inference API](https://github.com/kserve/kserve/blob/master/docs/predict-api/v2/required_api.md)
- [Triton gRPC service definition](https://github.com/triton-inference-server/common/blob/main/protobuf/grpc_service.proto)
