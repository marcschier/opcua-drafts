# Changelog — OPC UA — AI Model Management and Inference

All notable changes to this specification and its information model.

## Unreleased

### Conformance units named in the specification

§13.1 names the three conformance units the NodeSet assigns its Nodes to — `AiModelManagement`, `AiModelManagement DataTypes` and `AiModelManagement ReferenceTypes` — and says the facets are expressed over those Nodes. The units were always in the NodeSet; the document never named them, so a reader could not tell which unit a facet's members belonged to. No Node changes and the release version does not move.

### Profiles

Clause 13 has been titled *Profiles and conformance units* since 0.1.0 and defined only facets. §13.3 defines four profiles and §13.4 gives their URIs. The information model does not change, so the release version does not move: profiles are published through the base-UA `Server/ServerCapabilities/ServerProfileArray` and need no member.

A facet is a building block; a profile is a complete claim. The distinction matters commercially rather than technically — a plant writes a profile name into a purchase order, and enumerating nine facets correctly is not something a procurement document does reliably.

| Profile | Facets |
|---|---|
| AI Inference Device Server | AI-Base, AI-Invoke |
| AI Inference Gateway Server | AI-Base, AI-Invoke, AI-OffServer, AI-Federation, AI-Residency |
| AI Model Catalogue Server | AI-Base, AI-Catalogue, AI-Import |
| AI Model Lifecycle Server | AI-Base, AI-Dataset, AI-Learning, AI-Catalogue, AI-Import |

The first three were already in §13.1 as prose examples — "a device that runs one fixed model", "a gateway that calls a hosted model", "a plant MLOps node". Naming them cost nothing but a name. §13.1 now points at §13.3 rather than restating them, so the shapes have one definition.

`AI-Residency` is **inside** the gateway profile rather than optional to it. Once inference leaves the Server, *where does my data go* has an answer, and a gateway that cannot state it is the arrangement §9.5 exists to prevent. A Server that federates and cannot answer claims the facets individually.

The **Lifecycle** profile is witnessed by none of the eleven mapped systems, and is defined anyway. All eleven are inference or catalogue systems; none is a plant that trains, which is what clause 7 was written for. Its absence was also why `AI-Learning`, `AI-Dataset` and `AI-Stream` looked orphaned — they belonged to a Server shape the document described nowhere.

`AI-Stream` remains in no profile, deliberately. §13.2 already says a Server answering only through `Invoke` is conformant without it, and a facet that is genuinely optional to every shape should not be bundled into one.

§3 gains definitions for *conformance unit*, *facet* and *profile*. The document used "facet" throughout and defined it nowhere, and "profile" collides with the *typed profile* of a consuming specification (§6.4.1), which is a payload vocabulary and has nothing to do with conformance.

`validate_examples.py` checks every `**… Server**` token in the guides against the profile table, so a guide claiming a shape the specification does not define fails the same way a misspelled facet does.

## 0.4.0 — 2026-08-06

The eleven mappings published under `extras/ai-model-management/examples/` were re-read with a different question: not *which rules are wrong* — that was 0.3.0 — but *what do these systems do that this model cannot represent at all*. The answer had a consistent signature. A guide would **name** a vendor field and then never map it, because there was no member to map it to, and the omission was invisible because nothing was missing from the guide's own tables. Five gaps were found that way, and three further defects were found by checking the specification against itself.

### Breaking changes

Three Methods gain arguments. A client that calls positionally will break; one that builds its call from `InputArguments` will not.

| Method | Change |
|---|---|
| `DeploymentType.Invoke` | `PayloadUri` input, after `Payload` |
| `DeploymentType.InvokeAsync` | `PayloadUri` input, after `Payload` |
| `ModelSourceType.ListModels` | `ContinuationPoint` input and output |

NodeIds are unaffected: an argument list is the *Value* of an existing `InputArguments` Variable, not its identity. Churn for the release is **0 changed, 0 removed, 12 added**.

### A model had no time on it

Six of the eleven return a model's creation or modification time in the very call a Server populates `ModelType` from — OpenAI, Azure and NIM `created`, Vertex `createTime` and `updateTime`, Hugging Face `lastModified`, Bedrock `startOfLifeTime`. Every guide listed the field and mapped it nowhere.

The asymmetry made the omission plain rather than arguable. `DatasetType.CreatedAt` already exists with §6.3 defending it, and a catalogue resource inherits `CreatedAt`/`ModifiedAt` from xRegistry — so a model known through a catalogue had a vintage and the same model federated from an endpoint did not.

`PublishedAt` and `LastModifiedAt` close it. `LastModifiedAt` is the one that carries weight: §9.3's `FollowsRef` lets the artefact change with nothing else changing, and §12.3.1 requires repointing to be an authorization-bearing act, pointing at `AiJobType.RequestedBy` for the record — but a reference that moves *at the source* produces no job, so the audit trail that clause demands could not be constructed on the one path it exists to cover. A Server following a mutable reference **shall** populate it.

### A model had no end to it

Bedrock alone publishes `modelLifecycle`, with `legacyTime` and `endOfLifeTime`. One vendor of eleven, and it is in this release anyway, because vendor count is the wrong measure for an industrial model: the other ten were built for an audience that does not have to keep a line running.

`ModelCardType.DeprecatedFrom` and `SupportedUntil` are on the card rather than the nameplate for the reason the split exists — *how long will this keep working* is a question about whether the model may run here.

What made it worth a member is what happens on the date. The deployment does not degrade; it stops. `Reachability` goes `Unreachable`, `FallbackPolicy` fires, and where that is `FallBackTo` the line keeps producing while something outside the qualified configuration answers. §12.3.2 constrains that fallback and `ModelUsed` records it faithfully, so nothing is hidden — it is simply not noticed, because nobody was watching for a date. Every other availability facility in the model is a way of coping *after* the fact; this is the only one whose value is a date in the future.

### The asynchronous path could not carry a large payload

`InferenceJobType` had no `TransferRequired` and no `Transfer`, so `InvokeAsync` was a `ByteString` in and out, bounded by exactly the three limits §8.2.4 says this model does not get to choose — while §8.6 motivated it with "a batch scored overnight and an analysis over months of recorded data", which are the requests most likely to exceed them. §13.2 asserted parity with `Invoke`; on size there was none. AI-Transfer is a separate facet, so a Server could implement either alone and a client with a large payload and a long-running job had no path giving it both.

§8.6.1 separates two problems that had been collapsed into one. **A result too large to carry** is what `TransferRequired`/`Transfer` solve, and the job now carries the same pair on the same terms. **Data that never needed to move** is different: five hosted platforms take a storage URI in and out, and chunking a batch that already sits in the plant's object store copies it twice for no benefit. `PayloadUri` on `Invoke` and `InvokeAsync`, with `RequestUri` and `ResponseUri` on the job, is the answer — governed by the exactly-one rule §10.2 already applies to `Source` and `Registry`.

Five guides had discarded the vendor mechanism on the same narrow ground, that it is not a chunked transfer. They were right that it is not, and there was nothing else to compare it to.

Two obligations are inherited rather than invented: such a URI is untrusted input under §12.2, and it is an egress question under §9.5 — a deployment whose `EgressPermitted` is false **shall not** accept a `PayloadUri` naming somewhere outside the operator's boundary. A URI is a quieter way to move data than a payload, which is why it needs saying.

### A deployment did not say what to send it

Ten of the eleven publish a request contract. The model captured it for the tensor half only: §6.2 called `Inputs`/`Outputs` the only machine-readable description of what a deployment accepts, and they are empty for every system whose contract is a JSON body — which is why `AI-Signatures` was unclaimable by every hosted platform in the set.

The vocabulary existed and was out of reach. `ApiDialect` sat on `ModelSourceType`, and §9.2 scoped it away in terms that were an explicit assertion rather than an oversight: *"They never affect how an OPC UA client calls this Server, which is always §8."* For an `OnServer` deployment `Source` is null, so there was not even an indirect path.

§6.4.2 puts `ApiDialect` and `EndpointDescriptionUri` on `DeploymentType`, and §9.2's sentence is rewritten rather than quietly dropped. The replacement keeps what was true — how a client calls this Server is always §8, one Method and one opaque payload — and adds what was missing: naming *which* contract the opaque bytes must satisfy is not typing them, and §8.2's argument for opacity is about contents. The two dialects are read by different parties: the source's is what this Server speaks outward, the deployment's is what a caller must speak inward. A Server that passes the payload through publishes the same value twice.

### A pinned deployment could move without anything changing

OpenAI publishes `system_fingerprint` and NIM an active profile ID — an identity for the *serving configuration* as distinct from the artefact. §12.1.1 correctly forbade putting either in `Digest` and offered `ArtifactUri` or `ProvenanceUri` instead, which are scalar Strings on `ModelType` and cannot hold a per-deployment value. The datum was thrown away.

`DeploymentType.RuntimeIdentity` holds it: opaque, compared only for equality, never parsed — the same contract `Digest` has. §9.3.1 states what makes it matter: a change to it **is** an observable change to the deployment, which is what makes §9.3's promise about a `Pinned` artefact true rather than aspirational. Under a `Pinned` binding it is often the only observable change available, because the model did not move and nothing else in the address space did either.

§9.3.1 also states, at no model cost, what `Pinned` is actually worth. Where `DigestProvenance` is `NotAvailable` the deployment is pinned to a **name** the source promises to hold stable, and `Pinned` records that promise rather than this Server's verification. The two are already distinguishable by reading one member.

### Three defects found by reading the specification against itself

- **§6.4.3 defined a state transition with no modelled input.** `Degraded` was normative for a deployment "answering but missing its `LatencyBudget`", and no measured latency existed anywhere, so the rule could not be observed to be satisfied or violated by any legal Server. `ObservedLatency` supplies it. `LatencyBudget`'s own description claimed a client could detect regression from it, which was never true of a budget alone.
- **§13.2's AI-InvokeAsync row** claimed parity with `Invoke` that was false on payload size. It is true once §8.6.1 lands, and the row now says which rules it rests on.
- **§9.4's `ListModels` answered catalogue size with a cap and no cursor.** `MaxResults` bounds the response and puts everything past it permanently out of reach, which against a public catalogue is most of it. `ContinuationPoint` makes the enumeration completable, and an empty returned value is how a client knows to stop.

### Nothing here is Mandatory

Every added member is Optional, governed by a **conditional shall** stated in the clause that defines it — populate `LastModifiedAt` where the binding follows a mutable reference, `ObservedLatency` where the Server reports `Degraded` on latency grounds, `ApiDialect` where `Inputs`/`Outputs` do not describe the payload contract. A blanket Mandatory would have obliged nine of eleven Servers to publish `RuntimeIdentity` they cannot obtain, and a requirement no conformant implementation can satisfy is not a requirement. A conditional one binds exactly where it can be discharged, and stays testable.

### Known gaps

Unchanged from 0.3.0: `AI-Learning`, `AI-Stream` and `AI-Dataset` are witnessed by none of the eleven systems; `AI-Catalogue` and `AI-Import` are co-extensive across all of them; and clause 13 is titled "Profiles and conformance units" while defining no profiles.

## 0.3.0 — 2026-08-05

Eleven informative mappings of this model onto real systems — Microsoft Foundry, OpenAI, Amazon Bedrock, Amazon SageMaker, Google Vertex AI, NVIDIA NIM, NVIDIA Triton, KServe Open Inference Protocol, Hugging Face, embedded runtimes and a peer OPC UA Server — were written against release 0.2.0 and are published beside it under `extras/ai-model-management/examples/`. Writing them was a natural experiment: a rule that no real system can satisfy, or that two of them satisfy differently, shows up as a mapping that cannot be written honestly. This release is what the experiment found.

### Model changes

**`DigestProvenanceEnum` (`ns=2;i=3015`)**, with `DigestProvenance` **Mandatory** on `ModelType` and Optional on `ModelResourceType`.

`Digest` is Mandatory so that its absence is uniform and browsable, and that remains right — seven of the eleven systems cannot fill it, and making it Optional would have made "no digest" indistinguishable from "does not implement digests". But an empty `Digest` then carried two meanings and a populated one carried three, and a client deciding whether to run a model on a line needs *nobody checked* separated from *two parties agree*.

The absence of a positive answer was doing visible harm in the guides: five of them each prohibited a **different** wrong value — a response fingerprint, a resource name, a storage entity tag, a NIM manifest hash, a repository commit identifier — and none could say what to publish instead. §12.1.1 now states the prohibition once and supplies `NotAvailable` as the answer.

Mandatory rather than Optional for the reason `Digest` itself is Mandatory, which §6.2 already gives: clause 12 depends on it, and a rule that depends on an Optional member is a rule a conformant Server can silently not satisfy. It is always answerable, because `NotAvailable` is always available.

A StatusCode channel was considered and rejected: `DeclaredBySource` and `VerifiedOnStage` are both *Good*, so the distinction the member exists to make cannot be carried by a status.

**`ModelImportJobType.Registry` (Optional `NodeId`)**, with §10.2 requiring exactly one of `Source` and `Registry` to be non-null.

`Source` was Mandatory and typed `ModelSourceType`, so there was no path from an import job to a `ModelRegistryType` — contradicting the §4.4 and §5.1 diagrams, which draw exactly that edge. A Server importing from a catalogue had to invent a `ModelSourceType` wrapper around its own registry.

`Source` keeps its Mandatory modelling rule and takes null on the registry path, which is the idiom `TargetDeployment` already uses. Nothing renumbers and no existing member changes its rule.

**`ModelType.Name` is constrained rather than retyped.** Its `Text` **shall** be the source system's name for the model, carried across unchanged; a Server **may** add a translation for display and **shall not** translate, reformat or prettify the `Text`. Retyping from `LocalizedText` to `String` would have been the cleaner model and is breaking, and the identity property that was wanted — two Servers fetching one model from two mirrors produce the same string — is obtainable by constraining the field.

NodeId churn for the release is **0 changed, 0 removed, 5 added**.

### Normative changes carrying no model cost

- **§8.2.3 — an empty `UnitKind` means the call was not metered.** `AI-Invoke` required `Usage` "populated on every response" while no clause imposed the obligation, and "empty" was unencodable: the three counts are `UInt64` and this model declares no optional fields, so leaving them empty encodes as `0`, indistinguishable from a metered zero. The facet was therefore unsatisfiable for every tensor and in-process runtime, and five guides claimed it while documenting empty `Usage`. The unit carries the sentinel because the counts cannot.

- **§9.5 — residency composes end-to-end rather than next-hop.** A payload leaves a deployment along exactly two modelled edges, `FallsBackTo` and `Source`, and only the first was guarded. `EgressPermitted`'s only **shall** binds on `InferenceLocation` `Cloud`, so a cell-to-site `EdgeOffServer` hop escaped it entirely — one local hop with no internet in sight, while the site Server federates onward to a hosted endpoint. A Server federating to a peer now reads that peer's declarations and publishes nothing more permissive, defaulting fail-safe where it cannot read them.

- **§12.1.1 — digest provenance does not strengthen by being forwarded**, on the ordering `NotAvailable` < `DeclaredBySource` < `ComputedByServer` < `VerifiedOnStage`. The same composition argument as §9.5, applied to the other thing a federated deployment forwards.

- **§13.2 — `AI-Base` deployment requirements are conditional on the Server exposing a deployment.** §13.1 describes a plant MLOps node that "may never call `Invoke` at all" and the facet required at least one `DeploymentType`, so the specification promised a Server shape its own conformance table forbade. A catalogue Server is that shape.

- **§13.2 — `AI-OffServer` cites §12.2's scheme requirement instead of restating it**, so the two cannot drift apart.

- **§6.2, §9.2 — three members that were answering two questions each.** `ModelId` carries the source's identifier verbatim. `Publisher` names the organisation that **produced** the model, not the one serving it — two guides read it from an `owned_by` field and published the host, so two Servers serving one model disagreed about who made it. `AuthenticationKind` classifies what is **stored**, not the handshake performed, which is what makes a request-signing scheme answerable without a new literal. `ApiDialect` classifies the contract this Server speaks to that endpoint, and a catalogue-only source is `Proprietary` with an `EndpointDescriptionUri` — correct, rather than a shortcoming.

### What the experiment vindicated

Recorded because a design that survives contact with eleven systems is worth not relitigating: `Digest` Mandatory despite most sources being unable to fill it; dialects naming contracts rather than vendors; `UnitKind` in place of hardcoded token fields; `Throttled` separated from `Unreachable`; and an open-string `TaskKind`.

### Known gaps

`AI-Learning`, `AI-Stream` and `AI-Dataset` are witnessed by none of the eleven systems. `AI-Catalogue` and `AI-Import` are co-extensive across all of them. Clause 13 is titled "Profiles and conformance units" and defines no profiles.

## 0.2.0 — 2026-08-03

Federation, catalogue and chunked transfer. `ModelSourceType`, the xRegistry-derived registry types, `ModelImportJobType`, `InferenceJobType`, `InferenceTransferType`, `EvaluationRunType` and `ModelCardType`, with the residency and egress members on `DeploymentType`.

## 0.1.0

Initial working-group draft: `AiRootType`, `ModelType`, `DatasetType`, `DeploymentType` and `LearningJobType`.
