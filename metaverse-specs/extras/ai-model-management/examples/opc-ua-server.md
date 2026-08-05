# Another OPC UA Server

Informative. Every member named here is defined in
[the specification](../../../ai-model-management/OPC-UA-AI-Model-Management.md); this guide
introduces none. No vendor facts to date: the contract is this specification.

A `ModelSourceType` whose `ApiDialect` is `OpcUaInference` names **another Server
implementing this specification**. A cell Server delegating to a line Server, a line Server
delegating to a site Server, one plant borrowing capacity from another.

This is the only entry in the set where nothing is lost in translation, because there is no
translation. Every other guide is an exercise in deciding what to do about members the
remote system has no answer for; here the remote system has the same members, defined the
same way, because it is running the same model. Reading this guide against any of the
others is the clearest available statement of what the specification is *for*.

## The `ModelSourceType`

| Member | Value |
|---|---|
| `SourceId` | your name for the upstream Server |
| `EndpointUri` | its OPC UA endpoint — `opc.tcp://…` |
| `ApiDialect` | `OpcUaInference` |
| `EndpointDescriptionUri` | not required; the dialect names the contract exactly |
| `AuthenticationKind` | `MutualTls` under the usual certificate arrangement |
| `CredentialReference` | names the client certificate — never its private key |
| `TokenAudience` | empty; there is no token |
| `Reachability` | from `TestConnection`, which opens a Session |

`MutualTls` is the honest value for the ordinary OPC UA arrangement, where both ends hold
application instance certificates and each validates the other's. It is the one place in
this whole set where the authentication is symmetric — the upstream Server authenticates
the downstream one as surely as the reverse — and no other entry in
`AuthenticationKindEnum` says that.

`Anonymous` is what a Session with `SecurityMode` `None` deserves to be called. If that is
what you built, say so rather than claiming `MutualTls` because certificates exist
somewhere in the deployment.

## Identity

Nothing has to be reconstructed. The upstream Server publishes `ModelType` instances with
`Publisher`, `Name`, `Version`, `Digest` and `DigestAlgorithm` already populated, and the
downstream Server browses them.

| Member | From |
|---|---|
| `Publisher`, `Name`, `Version` | the upstream `ModelType`, read directly |
| `ModelId` | the upstream `ModelId` |
| `Digest`, `DigestAlgorithm` | **whatever the upstream Server has** |
| `Framework`, `Format`, `TaskKind` | the upstream members of the same names |
| `Inputs`, `Outputs` | the upstream signature, so **AI-Signatures** carries through |

The important word is *whatever*. A digest does not appear because the link is OPC UA; it
appears if the upstream Server had one. An upstream Server that is itself federating to a
hosted endpoint has an empty `Digest`, and the downstream Server's `Digest` is empty for
the same reason. Nothing along the chain may fill it in — §11 forbids inventing a value,
and a Server that manufactured one at the second hop would be laundering the absence of
provenance into the appearance of it.

What does travel is the `ImportedFrom` reference. Follow it upstream and the chain
terminates wherever the artefact actually came from, however many Servers back that is.
That is the whole point of §11 being a walk rather than a field.

## `Invoke`

The downstream Server calls the upstream `Invoke` and returns what comes back. Every output
maps to itself: `ResponsePayload`, `ResponseContentType`, `Usage`, `FinishReason`,
`SafetyAssessment`, `RetryAfter`.

`ModelUsed` needs care, and it is the one genuinely interesting mapping in this guide.

The upstream Server returns a NodeId **in its own address space**. It means nothing
downstream — the downstream client cannot resolve it, and passing it through would hand a
caller an identifier that looks resolvable and is not. The downstream Server therefore
returns the NodeId of *its own* `ModelType` representing the model that answered.

Which means the downstream Server has to be able to tell which one that was. If it
publishes one local model per upstream model, the mapping is a lookup. If the upstream
Server fell back — its `FallbackPolicy` being `FallBackTo`, and it substituted — then the
NodeId it returned is not the model the downstream Server asked for, and the downstream
Server must resolve *that* one or admit it cannot.

A downstream Server that cannot resolve the returned NodeId to a local `ModelType` has one
correct move and one tempting wrong one. **AI-Invoke** requires `ModelUsed` populated on
every response (§13), so a null is not an available answer for a call that succeeded: the
downstream Server publishes a `ModelType` for the substitute and returns that, or it fails
the call.

Returning the model that was *requested* is the tempting wrong one. It converts a visible
substitution into an invisible one, at exactly the point where a reader is furthest from
the evidence. A Server that cannot keep up with what its upstream is doing should say so by
failing, not by answering plausibly.

Which means the practical arrangement is to mirror the upstream's models — including its
fallbacks — rather than only the ones this Server expects to use. A fallback that has never
been exercised is precisely the one whose `ModelType` will be missing on the day it is.

## Asynchronous inference

`InvokeAsync` maps to the upstream `InvokeAsync`, and this is the one guide in the set
where that sentence is complete. Both ends have `AiJobType` on the Part 10 program state
machine, so the downstream Server can mirror the upstream job's state rather than inventing
a lifecycle over a polled REST call.

Mirror it rather than proxy it. The downstream job is a job in the downstream address
space, with its own `JobId`, and it reaches Halted when the upstream one does. A client
that subscribes to the downstream job should not need a Session on the upstream Server to
learn what happened.

## Large payloads

`BeginTransfer` maps to the upstream `BeginTransfer`, both over Part 5 `FileType`.

Read `MaxInlinePayloadSize` from the upstream deployment and publish a value **no larger**
downstream. Publishing a larger one produces a call that the downstream Server accepts and
the upstream Server refuses, which turns a bound that §8.2.4 exists to make visible in
advance into one discovered from a rejection — the exact failure the member was added to
prevent.

The same applies to a chain: the effective limit is the smallest along it, and each hop
publishes the smallest it knows about.

## The catalogue

An upstream `ModelRegistryType` is browsable directly, so §10 needs nothing built. A
downstream Server can present the upstream registry, or federate against it with a
`Mode` of `Federate` — the mode that moves no bytes and leaves the artefact where it
is (§10.3).

`Stage` also works and means what it says: the downstream Server fetches the artefact and
holds it. That is the arrangement worth choosing when the link is the thing you do not
trust, because after it the downstream Server can serve with the link down — and it can
verify the digest itself, having the bytes to verify it against.

## Residency, egress and retention

| Member | Value |
|---|---|
| `InferenceLocation` | `EdgeOffServer` for another Server on the plant network; `Cloud` if it is genuinely off-site |
| `EgressPermitted` | whether the payload leaves *this* site — not whether it leaves this machine |
| `DataJurisdiction` | the upstream Server's, which you have to read from it and record |
| `RetainsInput` | whatever the upstream Server declares, propagated |

These do not compose automatically and that is the trap in this guide.

The downstream Server's `EgressPermitted` must account for what the upstream Server does
with the payload, not merely for the hop between them. A cell Server calling a site Server
over the plant network looks like `EgressPermitted` `false` — one local hop, no internet.
If that site Server is itself federating to a hosted endpoint, the payload leaves the site,
and the cell Server publishing `false` is publishing something untrue about the only thing
a caller wanted to know.

So: read the upstream deployment's `EgressPermitted`, `DataJurisdiction` and `RetainsInput`,
and let them raise your own. Nothing enforces this. It is an operator assertion like all
the others, with the difference that here the information you need is machine-readable one
hop away, and there is no excuse for guessing it.

## What this system does not tell you

Very little, and the exceptions are worth naming precisely because they are so few:

- **Whether the upstream Server is telling the truth.** Every residency and provenance
  member is an assertion at every hop. Federation propagates assertions; it does not
  verify them. The one thing that can be verified is a digest, and only when a `Stage`
  import gave you the bytes to check it against.
- **How deep the chain goes.** There is no hop count. Following `ImportedFrom` and
  `Source` walks it, and a cycle is possible if two Servers are configured to federate to
  each other — worth checking for at commissioning, because nothing in the model prevents
  it.
- **What the upstream Server is federating to.** Browsable if it publishes a
  `ModelSourceType`, which it should, and absent if it does not.

Against every other guide in this set the closing section is a list of what the platform
withholds. Here it is a list of what federation cannot manufacture, which is a different
thing: the model is not losing information at this hop. It is carrying forward exactly as
much as was there to begin with.

## Conformance units

A conformance unit describes what **this** Server exposes, not what it can reach. A link to
a capable upstream Server does not make that Server's facets local, and this is the trap
worth stating plainly: federating to a Server with a catalogue does not give this Server
**AI-Catalogue**. Mirroring the upstream registry into this address space does.

Reachable from the link itself: **AI-Federation** and **AI-OffServer**, the second where
the Session is secured — §13 requires `EndpointUri` to name an authenticated, confidential
scheme, which an ordinary `opc.tcp` Session with `SignAndEncrypt` and mutual certificate
validation satisfies and an unsecured one does not.

Reachable where this Server proxies the upstream Method and publishes the required outputs
locally: **AI-Base**, **AI-Invoke**, **AI-InvokeAsync**, **AI-Transfer**.

Reachable only where this Server mirrors the upstream nodes rather than pointing at them:
**AI-Catalogue**, **AI-Import**, **AI-Dataset**, **AI-Signatures**, **AI-Stream**,
**AI-Learning**, **AI-Residency**. Each needs nodes in this address space that a client can
browse, read and subscribe to without a Session on the upstream Server — which is what
mirroring means and why it is work rather than configuration.

This is the only guide in the set whose limits come from what this Server chose to build
rather than from what the far end withholds.

## Sources

None. The contract is
[the specification](../../../ai-model-management/OPC-UA-AI-Model-Management.md) — §8 for
the inference Methods, §9 for federation, §10 for the catalogue, §11 for provenance.
