# Changelog — OPC UA — AI Model Management and Inference

All notable changes to this specification and its information model.

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
