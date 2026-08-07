# opcua-drafts

A scratch pad for **OPC UA specification drafts**.

This repository is a working area for authoring and iterating on draft OPC UA information models and companion specifications. It is intentionally informal: contents are experimental drafts used to explore modelling approaches, try out tooling, and prototype NodeSets before anything is proposed or released. Nothing here is normative, official, or final, and everything is subject to change or removal without notice.

## The specifications

Sixteen documents, grouped by the tree they live in. Every one is a **working draft**: nothing here is normative, official, or endorsed by the OPC Foundation, and namespace URIs and NodeIds are provisional.

Each is generated from a single source of truth — a `tools/build_model.py` emits the NodeSet, the NodeId CSV and the annex tables — so the prose, the model and the tables cannot drift apart. The Word renderings are built into the official OPC Foundation template and are the format a submission is reviewed in.

### core — additions to the base OPC UA namespace

Proposed extensions to `http://opcfoundation.org/UA/` itself, rather than companion models beside it. These are the drafts aimed at an OPC Foundation Working Group as errata or new Parts.

| Specification | What it is, and why it exists | Status | Documents |
|---|---|---|---|
| **OPC UA — Data Channels** | A named, authorized, flow-controlled stream of opaque bytes multiplexed onto a SecureChannel that is **already open** — no second port, no second handshake, no second trust anchor. It exists because OPC UA has no streaming primitive, so video, audio and other continuous content today runs over an RTSP or WebRTC endpoint *beside* the Server, with its own security to configure and get wrong. Errata against Parts 3, 4 and 6, plus an `opc.quic` transport. | Draft 0.1.1 | [Specification](core-specs/data-channels/OPC-UA-Data-Channels.md) · [Word](word-drafts/OPC-UA-Data-Channels.docx) |
| **OPC UA — Apache Arrow Encoding** | A columnar DataEncoding: a Part 6 value mapping, a Part 14 PubSub **batch** message mapping, and an ADBC-style historian surface where Part 11 `HistoryRead` returns Arrow record batches. It exists because analytics and historian consumers read columns, and re-encoding row-at-a-time OPC UA data into columns at the edge of every pipeline is work nobody needs to do twice. | Draft 0.1.0 | [Specification](core-specs/arrow-encoding/OPC-UA-Arrow-Encoding.md) · [Word](word-drafts/OPC-UA-Arrow-Encoding.docx) |
| <!-- release-spec-link:KipPUEMgVUEg4oCUIEFwYWNoZSBBdnJvIERhdGFFbmNvZGluZyoqIHwgQSBQYXJ0IDYgbWFwcGluZyBvZiB0aGUgZnVsbCBPUEMgVUEgdHlwZSBtb2RlbCBhbmQgYSBQYXJ0IDE0IFB1YlN1YiBtZXNzYWdlIG1hcHBpbmcsIGluY2x1ZGluZyBBY3Rpb24gaW52b2tlL3Jlc3BvbnNlIGFuZCBEaXNjb3ZlcnkgbWVzc2FnZXMuIFJldmVyc2libGUg4oCUIGBkZWNvZGUoZW5jb2RlKHgpKSA9PSB4YCDigJQgd2l0aCBhIE5vZGVTZXQtZHJpdmVuIHNjaGVtYSBnZW5lcmF0b3IgYW5kIGEgU2NoZW1hSWQgaGFuZHNoYWtlLCBzbyBhIGRpc2Nvbm5lY3RlZCBjb25zdW1lciBjYW4gZGVjb2RlIGEgcGF5bG9hZCBpdCBkaWQgbm90IG5lZ290aWF0ZS4gfCBEcmFmdCB8IFtTcGVjaWZpY2F0aW9uXShjb3JlLXNwZWNzL2F2cm8tZW5jb2RpbmcvT1BDLVVBLUF2cm8tRW5jb2RpbmcubWQpIMK3IFtXb3JkXSh3b3JkLWRyYWZ0cy9PUEMtVUEtQXZyby1FbmNvZGluZy5kb2N4KSB8 -->**OPC UA — Apache Avro DataEncoding** | A Part 6 mapping of the full OPC UA type model and a Part 14 PubSub message mapping, including Action invoke/response and Discovery messages. Reversible — `decode(encode(x)) == x` — with a NodeSet-driven schema generator and a SchemaId handshake, so a disconnected consumer can decode a payload it did not negotiate. | *Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).* | [Specification](https://github.com/OPCF-Members/spec-drafts/blob/main/core-specs/avro-encoding/OPC-UA-Avro-Encoding.md) · [Word](https://github.com/OPCF-Members/spec-drafts/blob/main/word-drafts/OPC-UA-Avro-Encoding.docx) |<!-- /release-spec-link -->
| **OPC UA — xRegistry** | An **abstract** base model projecting any [xRegistry](https://github.com/xregistry/spec) registry onto the AddressSpace: a registry or group is a `FolderType`, a resource version is a Part 5 `FileType`, so a resource can be streamed with `Open`/`Read`/`Close`. It exists so that every domain registry in this repository is the same shape rather than a private invention — Schema Registry, the WoT connectivity registry and the OpenUSD artifact registry all subtype it. | Draft 0.3.0 | [Specification](core-specs/xregistry/OPC-UA-xRegistry.md) · [Word](word-drafts/OPC-UA-xRegistry.docx) |
| **xRegistry — OPC UA API** | The OPC UA binding of xRegistry written as a peer of its HTTP binding, targeted at the xRegistry project as `core/opcua.md` rather than at the OPC Foundation. It exists so the projection is defined once, on both sides of the boundary. | Draft 0.1.0 | [Specification](core-specs/xregistry/xRegistry-OPC-UA-Api.md) · — |

### cloud — a Server's cloud-facing surface

How a model reaches the systems that consume it, rather than the operators who browse it. Both are domain extensions of `xregistry/` or feed the encodings beside it.

| Specification | What it is, and why it exists | Status | Documents |
|---|---|---|---|
| **OPC UA — Schema Registry** | A concrete xRegistry whose resources are schema documents, exposed as a well-known object under the Server object. It exists because a schema-based encoding is not self-describing: a decoder that receives an Avro or Arrow payload needs the exact schema that produced it, and Binary, XML and JSON never had that problem. Deliberately decoupled from PubSub — a Server need not implement Part 14 to be a schema registry. | Draft 0.5.0 | [Specification](cloud-specs/schema-registry/OPC-UA-Schema-Registry.md) · [Word](word-drafts/OPC-UA-Schema-Registry.docx) |
| **OPC UA — Observability Export** | A transport-neutral layer letting a Server, or a companion specification, declare how its data lands in an observability system as OpenTelemetry metrics, logs and traces. It exists so one generic read-only bridge can forward any conforming Server without understanding the domain, instead of a bespoke exporter per companion specification. Ships addenda for DI, Pumps, Robotics and the Machinery facets. | Draft 0.1.0 | [Specification](cloud-specs/observability-export/OPC-UA-Observability-Export.md) · [Word](word-drafts/OPC-UA-Observability-Export.docx) |

### metaverse — virtual worlds, perception and robot control

Connecting OPC UA to the systems that visualize, perceive and command physical machines. See [`metaverse-specs/README.md`](metaverse-specs/README.md) for how the pieces relate.

| Specification | What it is, and why it exists | Status | Documents |
|---|---|---|---|
| <!-- release-spec-link:KipPUEMgVUEgZm9yIE9wZW5VU0Qg4oCUIFBhcnQgMTogQmluZGluZyoqIHwgQSByZXByZXNlbnRhdGlvbiwgbGl2ZS1iaW5kaW5nLCBjb21tYW5kLCBhbGFybSBhbmQgY29tcG9zaXRpb24gbGF5ZXIgbGV0dGluZyBhbnkgT1BDIFVBIGNvbXBhbmlvbiBtb2RlbCBkcml2ZSBPcGVuVVNEIHByaW1zIHRocm91Z2ggYSBkaXNjb3ZlcmFibGUgYFNlcnZlci9PcGVuVVNEYCBjb250cmFjdC4gSXQgZXhpc3RzIHNvIHRoYXQgYWRkaW5nIGEgdmlld2VyIGRvZXMgbm90IG1lYW4gd3JpdGluZyBhbm90aGVyIGJyaWRnZS4gfCBEcmFmdCAwLjUuMCB8IFtTcGVjaWZpY2F0aW9uXShtZXRhdmVyc2Utc3BlY3Mvb3BlbnVzZC1iaW5kaW5nL09QQy1VQS1PcGVuVVNELUJpbmRpbmdzLm1kKSDCtyBbV29yZF0od29yZC1kcmFmdHMvT1BDLVVBLU9wZW5VU0QtQmluZGluZy1QYXJ0MS5kb2N4KSB8 -->**OPC UA for OpenUSD — Part 1: Binding** | A representation, live-binding, command, alarm and composition layer letting any OPC UA companion model drive OpenUSD prims through a discoverable `Server/OpenUSD` contract. It exists so that adding a viewer does not mean writing another bridge. | *Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).* | [Specification](https://github.com/OPCF-Members/spec-drafts/blob/main/metaverse-specs/openusd-binding/OPC-UA-OpenUSD-Bindings.md) · [Word](https://github.com/OPCF-Members/spec-drafts/blob/main/word-drafts/OPC-UA-OpenUSD-Binding-Part1.docx) |<!-- /release-spec-link -->
| <!-- release-spec-link:KipPUEMgVUEgZm9yIE9wZW5VU0Qg4oCUIFBhcnQgMjogU2NlbmUgTWF0ZXJpYWxpemF0aW9uKiogfCBUaGUgZnVsbCBPcGVuVVNEIGRhdGEgbW9kZWwg4oCUIFN0YWdlLCBQcmltLCBBdHRyaWJ1dGUsIFJlbGF0aW9uc2hpcCwgQ29tcG9zaXRpb24sIFZhcmlhbnQg4oCUIGFzIG5hdGl2ZSBPUEMgVUEgdHlwZXMsIHdpdGggYmlkaXJlY3Rpb25hbCBgLnVzZGAg4oaUIEFkZHJlc3NTcGFjZSBjb252ZXJzaW9uLiBJdCBhcHByb2FjaGVzIHRoZSBzYW1lIHByb2JsZW0gZnJvbSB0aGUgb3Bwb3NpdGUgZW5kIHRvIFBhcnQgMSBhbmQgaXMgc2VsZi1jb250YWluZWQ6IGl0cyBOb2RlU2V0IHJlcXVpcmVzIG9ubHkgYmFzZSBPUEMgVUEuIHwgRHJhZnQgMC40LjAgfCBbU3BlY2lmaWNhdGlvbl0obWV0YXZlcnNlLXNwZWNzL29wZW51c2Qtc2NlbmUvT1BDLVVBLU9wZW5VU0QtU2NlbmUtTWF0ZXJpYWxpemF0aW9uLm1kKSDCtyBbV29yZF0od29yZC1kcmFmdHMvT1BDLVVBLU9wZW5VU0QtU2NlbmUtUGFydDIuZG9jeCkgfA== -->**OPC UA for OpenUSD — Part 2: Scene Materialization** | The full OpenUSD data model — Stage, Prim, Attribute, Relationship, Composition, Variant — as native OPC UA types, with bidirectional `.usd` ↔ AddressSpace conversion. It approaches the same problem from the opposite end to Part 1 and is self-contained: its NodeSet requires only base OPC UA. | *Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).* | [Specification](https://github.com/OPCF-Members/spec-drafts/blob/main/metaverse-specs/openusd-scene/OPC-UA-OpenUSD-Scene-Materialization.md) · [Word](https://github.com/OPCF-Members/spec-drafts/blob/main/word-drafts/OPC-UA-OpenUSD-Scene-Part2.docx) |<!-- /release-spec-link -->
| **OPC UA — Vision** | An information model for machine vision and robotics vision: the sensors, the media they emit, the AI that interprets them and the results they publish. It exists because OPC 40100-1 leaves result content undefined and OPC 40010-1 has no vision types at all, so what a camera actually *concluded* has no standard shape. Media is brokered, not carried. | Draft 0.1.0 | [Specification](metaverse-specs/vision/OPC-UA-Vision.md) · — |
| **OPC UA — Robot Intent** | Commanding a robot at the level of task intent — move there, grasp that, pick from here — with a Part 10 lifecycle rather than a blocking Method. It exists because OPC 40010-1 describes robot topology and defines **no motion verbs**, so every integrator writes vendor motion code for work that is identical across vendors. Explicitly not safety-rated; it reports what the safety system enforces and refuses what would exceed it. | Draft 0.1.0 | [Specification](metaverse-specs/robot-intent/OPC-UA-Robot-Intent.md) · — |
| **OPC UA — AI Model Management and Inference** | What an AI model *is*, what it was trained on, where it executes, how it is invoked and how a better one replaces it. It exists because OPC UA has no way to say any of that, so a plant cannot answer *which model produced this answer, and can I audit it* — the question that arrives six months after the parts shipped. Domain-neutral by construction. Eleven [implementation guides](metaverse-specs/extras/ai-model-management/examples/index.md) map it onto real systems. | Draft 0.4.0 | [Specification](metaverse-specs/ai-model-management/OPC-UA-AI-Model-Management.md) · — |
| **OpenUSD Artifact Registry Service** | An xRegistry domain specification for OpenUSD artifacts, proposed to [xregistry.org](https://github.com/xregistry/spec) rather than to the OPC Foundation, which is why it stays here while the OpenUSD parts are under review. | Draft | [Specification](metaverse-specs/openusd-binding/xRegistry-OpenUsd.md) · — |

### wot — Web of Things

Both specifications are under OPC Foundation review, so the `wot-specs/` tree is not in this repository at present.

| Specification | What it is, and why it exists | Status | Documents |
|---|---|---|---|
| <!-- release-spec-link:KipPUEMgVUEg4oCUIFdlYiBvZiBUaGluZ3MgQmluZGluZyoqIHwgQSBzdGFuZGFsb25lIHJldmlzaW9uIG9mIE9QQyAxMDEwMSBkZXNjcmliaW5nIGFuIE9QQyBVQSBpbnRlcmZhY2UgYXMgYSBXM0MgVGhpbmcgRGVzY3JpcHRpb24gb3IgVGhpbmcgTW9kZWwsIHByZXNlcnZpbmcgdGhlIG9mZmljaWFsIGB1YXZgIHZvY2FidWxhcnkgYW5kIHRoZSBSZWFkL1dyaXRlL09ic2VydmUvQ2FsbCBhbmQgc2VjdXJpdHkgbWFwcGluZ3MsIGFuZCBhZGRpbmcgYSBjb2xsaXNpb24tc2FmZSBtb2RlbCB2b2NhYnVsYXJ5IHBsdXMgYmlkaXJlY3Rpb25hbCBOb2RlU2V0MiBjb252ZXJzaW9uLiBJdCBleGlzdHMgc28gYSBUaGluZyBEZXNjcmlwdGlvbiByb3VuZC10cmlwcyB3aXRob3V0IGxvc2luZyB0aGUgZmFjdHMgT1BDIFVBIGtub3dzIGFuZCB0aGUgdm9jYWJ1bGFyeSBjYW5ub3QgeWV0IGV4cHJlc3MuIHwgRHJhZnQgfCBbU3BlY2lmaWNhdGlvbl0od290LXNwZWNzL1dvVC1CaW5kaW5nL09QQy1VQS1Xb1QtQmluZGluZy5tZCkgwrcgW1dvcmRdKHdvcmQtZHJhZnRzL09QQy1VQS1Xb1QtQmluZGluZy5kb2N4KSB8 -->**OPC UA — Web of Things Binding** | A standalone revision of OPC 10101 describing an OPC UA interface as a W3C Thing Description or Thing Model, preserving the official `uav` vocabulary and the Read/Write/Observe/Call and security mappings, and adding a collision-safe model vocabulary plus bidirectional NodeSet2 conversion. It exists so a Thing Description round-trips without losing the facts OPC UA knows and the vocabulary cannot yet express. | *Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).* | [Specification](https://github.com/OPCF-Members/spec-drafts/blob/main/wot-specs/WoT-Binding/OPC-UA-WoT-Binding.md) · [Word](https://github.com/OPCF-Members/spec-drafts/blob/main/word-drafts/OPC-UA-WoT-Binding.docx) |<!-- /release-spec-link -->
| <!-- release-spec-link:KipPUEMgVUEg4oCUIFdvVCBDb25uZWN0aXZpdHkqKiB8IEEgcmVnaXN0cnktZmlyc3QgcmV2aXNpb24gb2YgT1BDIDEwMTAwLTEgbGF5ZXJpbmcgYSBUaGluZyBNb2RlbCAvIFRoaW5nIERlc2NyaXB0aW9uIGRvY3VtZW50IHJlZ2lzdHJ5IG92ZXIgdGhlIGB4cmVnaXN0cnkvYCBiYXNlIG1vZGVsLCB3aXRoIHRoZSBBZGRyZXNzU3BhY2UgYXMgYSBkZXJpdmVkLCBzaGFkb3ctc3dpdGNoZWQgcHJvamVjdGlvbiBvZiB0aGUgc3RvcmVkIGRvY3VtZW50cy4gSXQgZXhpc3RzIGJlY2F1c2UgdGhlIGRvY3VtZW50cyBhcmUgY2Fub25pY2FsIGFuZCB0aGUgcHJvamVjdGlvbiBpcyBub3QsIGFuZCB0aGUgcHVibGlzaGVkIDEuMDIgbW9kZWwgaGFkIGl0IHRoZSBvdGhlciB3YXkgcm91bmQuIEluY29ycG9yYXRlcyBldmVyeSBwdWJsaXNoZWQgTm9kZUlkLiB8IERyYWZ0IDEuMSB8IFtTcGVjaWZpY2F0aW9uXSh3b3Qtc3BlY3MvV29ULUNvbm5lY3Rpdml0eS9PUEMtVUEtV29ULUNvbm5lY3Rpdml0eS5tZCkgwrcgW1dvcmRdKHdvcmQtZHJhZnRzL09QQy1VQS1Xb1QtQ29ubmVjdGl2aXR5LmRvY3gpIHw= -->**OPC UA — WoT Connectivity** | A registry-first revision of OPC 10100-1 layering a Thing Model / Thing Description document registry over the `xregistry/` base model, with the AddressSpace as a derived, shadow-switched projection of the stored documents. It exists because the documents are canonical and the projection is not, and the published 1.02 model had it the other way round. Incorporates every published NodeId. | *Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).* | [Specification](https://github.com/OPCF-Members/spec-drafts/blob/main/wot-specs/WoT-Connectivity/OPC-UA-WoT-Connectivity.md) · [Word](https://github.com/OPCF-Members/spec-drafts/blob/main/word-drafts/OPC-UA-WoT-Connectivity.docx) |<!-- /release-spec-link -->

### companion — domain companion specifications

| Specification | What it is, and why it exists | Status | Documents |
|---|---|---|---|
| **OPC UA for Generators (GenSets)** | A generator set as both an automation asset and a machine built around a prime-mover engine exposing SAE J1939 over CAN: nameplate, ratings, operating state and mode, health and control. It exists because the engine's own bus already carries most of this and nothing standardises how it reaches an OPC UA client. | Draft 1.0.0 | [Specification](companion-specs/Generators/OPC-UA-Companion-Specification-for-Generators.md) · [Word](word-drafts/OPC-UA-Generators.docx) |

Vision, Robot Intent and AI Model Management have no Word rendering yet — they have no clause map under [`word-drafts/tools/specs/`](word-drafts/tools/specs/), which is what drives the build.

## Specifications under OPC Foundation review

Five drafts have been submitted to the OPC Foundation and are being reviewed under member confidentiality. They are **not in this repository while that review runs** — they live in [`OPCF-Members/spec-drafts`](https://github.com/OPCF-Members/spec-drafts), a private repository of the OPC Foundation members organization.

They appear in the tables above with their status, and link to the private repository.

**If you reviewed one of these here, that is where the discussion continues.** The private repository carries the same contribution and review model as this one — the same Word round trip, the same label-driven agents, the same validation — so nothing about how you give feedback changes.

Access is for OPC Foundation members. Request it through the [member portal](https://memberportal.opcfoundation.org/api/access-request); see [`OPCF-Members/Help`](https://github.com/OPCF-Members/Help) for what the members organization holds and who to contact (`github@opcfoundation.org`). If you are not a member, the OPC Foundation's own review and comment process is the route in.

### Getting it all in one checkout

Members can have both repositories side by side: `spec-drafts/` is registered as a submodule pointing at the private repository.

```powershell
# clone everything at once
git clone --recurse-submodules https://github.com/marcschier/opcua-drafts.git

# or populate it in a checkout you already have
git submodule update --init spec-drafts

# move it forward to the current private main
git submodule update --remote spec-drafts
```

**If you are not a member, nothing changes for you.** A plain `git clone` leaves `spec-drafts/` empty and everything else works exactly as before; only the submodule fetch fails, and only if you ask for it. Continuous integration never checks it out, and the repository's own checks skip any directory that carries its own `.git`, so a member running them locally gets the same result as CI rather than also validating the private tree.

The submodule is a pinned commit like any other, so `git status` showing it behind is normal — it moves when someone commits a new pointer.

Two documents that were part of the OpenUSD work stay here, because they are proposed to [xregistry.org](https://github.com/xregistry/spec) rather than to the OPC Foundation: [`xRegistry-OpenUsd.md`](metaverse-specs/openusd-binding/xRegistry-OpenUsd.md) and its model. The [`xregistry/`](core-specs/xregistry/) base model they build on also stays, because the specifications that subtype it are still public.

Each specification returns here once its review completes.

## Contributing

Feedback on these drafts is welcome — and you don't have to write the specification yourself. Fork the repo, create a branch, and either make changes or just **annotate** the drafts (inline comments, notes, or open questions); then open a pull request and discuss. Maintainers use **AI agents** to turn the feedback and discussion into concrete specification text, information-model (NodeSet / CSV) updates, and regenerated artifacts.

1. Fork `marcschier/opcua-drafts` and check out a topic branch.
2. Make your changes or annotations — for generated specs, edit the source (a descriptor or `tools/build_model.py`), not the generated NodeSet / CSV, and regenerate.
3. Open a pull request against `main` and discuss.
4. Maintainers apply the agreed changes with AI, regenerate, and validate (`python core-specs/extras/validate_all.py`, and the equivalent for the tree the change lands in).

### You don't have to touch git at all

Two labels start an agent that does the work and opens the pull request for you. **Only a maintainer can apply a label**, so a label is a deliberate decision to act on something — open the issue first and say what you want.

| Label | What happens |
|---|---|
| `word-review` | Attach a marked-up `.docx` from [`word-drafts/`](word-drafts/) to the issue. Your tracked changes become the pull request's diff and your comments become a review on it; anything that needs judgement rather than a substitution is handed to the agent. See [*Sending a review back*](word-drafts/README.md#sending-a-review-back). |
| `needs pr` | The agent reads the issue and every comment on it and opens a pull request implementing what it asks for. If the issue asks no concrete question of the text, it says so and opens nothing. |

Everything an agent writes is a **draft of an answer, not an answer** — it goes through the same review as anyone else's pull request.

The label decides *that* the agent runs. It cannot decide *what it is told*, because anyone can write an issue and anyone can comment on one, so the agent is built on the assumption that its input is hostile: it runs with no write credential, is handed the issue text as a file marked untrusted rather than as instructions, and can only propose changes under the specification trees. Whatever it produces is a patch that a person reads before it lands.

The Word renderings under `word-drafts/` are regenerated automatically whenever a specification changes on `main`, and collected on one standing pull request. Do not edit them by hand.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full workflow, validation, and conventions, and [`.github/copilot-instructions.md`](.github/copilot-instructions.md) for the specification authoring style — voice and tense, normative language, and the model, example and validator conventions the drafts follow — together with the build and validation commands and a map of the repository.

## Repository layout

Each tree holds only the **normative** documents and the generated base artifacts — the specification, its `NodeSet2.xml` and its `NodeIds.csv`. Everything secondary sits in a mirrored `extras/` tree: generators, validators, examples, descriptors and generated non-base schemas. The split is not applied uniformly, so look for the generator before assuming where it lives.

| Path | Holds |
|---|---|
| [`core-specs/`](core-specs/) | Proposed additions to the base OPC UA namespace, plus [`core-specs/extras/`](core-specs/extras/) and the shared `_common/` encoding package. Validate with `python core-specs/extras/validate_all.py`. |
| [`cloud-specs/`](cloud-specs/) | The cloud-facing surface. Validate with `python cloud-specs/validate_all.py`. |
| [`metaverse-specs/`](metaverse-specs/) | Virtual worlds, perception and robot control. Validate with `python metaverse-specs/validate_all.py`. |
| [`companion-specs/`](companion-specs/) | Domain companion specifications, one folder per domain. |
| [`word-drafts/`](word-drafts/) | Submission-ready Word renderings built into the official OPC Foundation template, and the build that produces them. Never edit a `.docx` by hand — see [`word-drafts/README.md`](word-drafts/README.md). |
| [`templates/`](templates/) | The official OPC Foundation companion specification template the Word build clones. |
| [`skills/`](skills/) | Reusable authoring skills — agent instructions that operate on the drafts. |
| [`release/`](release/) | The tooling that moves a specification to the private review repository and brings it back, and the manifest recording what has been submitted. |
| [`spec-drafts/`](https://github.com/OPCF-Members/spec-drafts) | The private review repository, registered as a submodule. Empty unless you are an OPC Foundation member who asked for it. |

Validation is **per specification**: each extension owns a `tools/validate_local.py`, and the three `validate_all.py` files drive lists of them. A tree drives only its own, so a specification that changes trees takes its entry with it.

