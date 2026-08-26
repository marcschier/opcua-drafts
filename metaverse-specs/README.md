# metaverse-specs — OPC UA for virtual worlds, perception and robot control

Draft specifications connecting **OPC UA** to the systems that visualize, perceive and command physical machines — the "metaverse" / digital-twin track. Two of them bind OPC UA to **OpenUSD** (Universal Scene Description); the other two supply information models OPC UA lacks entirely, for **machine vision** and for **commanding a robot**.

Nothing here is normative, official, or endorsed by the OPC Foundation, the Alliance for OpenUSD, VDMA or any manufacturer. Namespace URIs and NodeIds are **provisional** and for prototyping only.

> **Both OpenUSD parts are under OPC Foundation review** and are maintained in [`OPCF-Members/spec-drafts`](https://github.com/OPCF-Members/spec-drafts) until it completes. OPC Foundation members can [request access](https://github.com/OPCF-Members/Help); see [*Specifications under OPC Foundation review*](../README.md#specifications-under-opc-foundation-review). What remains here is the tooling, the examples, and the [xRegistry OpenUSD domain specification](openusd-binding/xRegistry-OpenUsd.md), which is proposed to xregistry.org rather than to the OPC Foundation.

## The OpenUSD pair: two parts, two directions

The two specifications approach the same problem from opposite ends and are deliberately independent:

| | <!-- release-spec-link:W2BvcGVudXNkLWJpbmRpbmcvYF0ob3BlbnVzZC1iaW5kaW5nLyk= -->`openusd-binding/`<!-- /release-spec-link --> — **Part 1** | <!-- release-spec-link:W2BvcGVudXNkLXNjZW5lL2BdKG9wZW51c2Qtc2NlbmUvKQ== -->`openusd-scene/`<!-- /release-spec-link --> — **Part 2** |
|---|---|---|
| Question | *Which USD prim represents this OPC UA Object, and which Variables drive its attributes?* | *What if the USD scene graph simply **were** an OPC UA address space?* |
| The scene lives | outside OPC UA, in `.usd` files a connector renders | inside OPC UA, as first-class browsable nodes |
| You get | a thin binding layer over an existing USD asset | Stage/Prim/Attribute/Relationship/Composition as ObjectTypes |
| Namespace | `http://opcfoundation.org/UA/OpenUSD/` | `http://opcfoundation.org/UA/OpenUSD/Scene/` |
| Release | 0.5.0 | 0.4.0 |

**Part 2 does not require Part 1.** It is self-contained on base OPC UA. Where a Server implements both, Part 1's `Server/OpenUSD/Stages` discovery and its bindings can target Part 2 attributes — see Part 2 Annex C.

Pick Part 1 when you already have an artist-authored USD asset and want to drive it. Pick Part 2 when the scene itself should be the address space — browsable, subscribable, historizable.

## The three standalone models

| | [`vision/`](vision/) | [`robot-intent/`](robot-intent/) | [`ai-model-management/`](ai-model-management/) |
|---|---|---|---|
| Question | *What does this camera see, and what did it conclude?* | *How do I tell this robot what to do?* | *Which model produced this answer, and can I audit it?* |
| The gap | OPC 40100-1 leaves result content undefined; OPC 40010-1 has no vision types at all | OPC 40010-1 describes robot topology and defines **no motion verbs** | OPC UA has no way to say what an AI model *is*, where it runs, or what it was trained on |
| Namespace | `http://opcfoundation.org/UA/Vision/` | `http://opcfoundation.org/UA/RobotIntent/` | `http://opcfoundation.org/UA/AI/` |
| Release | 0.4.1 | 0.3.0 | 0.5.1 |

Vision and Robot Intent are self-contained on base OPC UA. AI Model Management additionally requires *OPC UA — xRegistry*, because its model catalogue is a domain extension of that abstract registry rather than a private invention — a model catalogue **is** a registry, and defining a second one would leave two incompatible ways to describe the same artefact.

**They compose without coupling.** Vision's `InferencePipelineType.Deployment` and `VisionResultType.ModelUsed` are plain `NodeId` Properties, so a Server can publish cameras and verdicts with no AI model at all. Where it implements both models, `Deployment → UsesModel` identifies the model serving now, while `result.ModelUsed → ModelType → Digest` identifies the model that produced a retained result. Vision and Robot Intent share a frame vocabulary with identical literals and numbering. In every case the join is a **facet precondition**, never a `RequiredModel` — which is what lets a domain adopt one model without inheriting the others.

For a short browse-oriented introduction to the two models and their ownership boundary, see [Vision and AI Model Management walkthrough](vision-ai-walkthrough.md). For transport-neutral guidance on retaining Vision results outside an OPC UA Server, see [External Result Mapping for Vision and AI](vision-ai-external-result-mapping.md).

## Layout

- <!-- release-spec-link:YG9wZW51c2QtYmluZGluZy9gIOKAlCBQYXJ0IDEgc3BlY2lmaWNhdGlvbiwgTm9kZVNldCwgQ1NWLCBpbXBsZW1lbnRlciBhZGRlbmRhIGZvciBgcHVtcHMvYCBhbmQgYHJvYm90aWNzL2AsIGFuZCB0aGUgc3RhbmRhbG9uZSAqKnhSZWdpc3RyeSBkb21haW4gc3BlY2lmaWNhdGlvbioqIGZvciB0aGUgYXJ0aWZhY3QgcmVnaXN0cnkgKGB4UmVnaXN0cnktT3BlblVzZC5tZGApLCB3aGljaCBkZWZpbmVzIHRoZSBzYW1lIHJlZ2lzdHJ5IGluZGVwZW5kZW50bHkgb2YgT1BDIFVBIHNvIHRoZSB0d28gcHJvamVjdGlvbnMgZmVkZXJhdGUu -->*Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).*<!-- /release-spec-link -->
- <!-- release-spec-link:YG9wZW51c2Qtc2NlbmUvYCDigJQgUGFydCAyIHNwZWNpZmljYXRpb24sIE5vZGVTZXQsIENTViwgYW5kIG1hdGVyaWFsaXplZCBleGFtcGxlIG92ZXJsYXlzLg== -->*Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).*<!-- /release-spec-link -->
- `vision/` — **OPC UA — Vision**: sensors, the media they emit, the AI that interprets them, the results they produce, and the feedback path back in. Standalone on base OPC UA, with worked addenda for `robotics/` and `machine-vision/`.
- `robot-intent/` — **OPC UA — Robot Intent**: task-level verbs for commanding a robot, with a Part 10 lifecycle. OPC 40010-1 describes robot topology and defines no motion verbs; this supplies the verbs and nothing else. Standalone on base OPC UA.
- `ai-model-management/` — **OPC UA — AI Model Management and Inference**: what a model is, how to call it, how to call one hosted somewhere else, and how to get one from a catalogue onto the machine. Deliberately **domain-neutral** — it names no camera, no robot and no sensor — so any domain can build on it. The invocation surface does not change with where inference runs; what changes is the trust boundary, and clauses 8 and 10 are about saying so out loud: what happens when the link drops, and whether calling a model sends plant data off site.
- `extras/` — everything secondary to standardization, mirroring the folders above:
  - `openusd-binding/tools/` — the model generator and validator; `examples/` — the pumps and robotics USD assets, binding descriptors, writers, renderers and end-to-end guides.
  - `openusd-scene/tools/` — the model generator, the `.usd` ↔ NodeSet converters, and the round-trip checker.
  - `openusd-artifacts/` — the emitted xRegistry **artifact registry** for the examples (see Part 1 §7.11).
  - `vision/tools/` — the model generator, the example builder and the validator.
  - `robot-intent/tools/` — the model generator and the validator.
  - `ai-model-management/tools/` — the model generator and the validator, including the domain-neutrality check that fails the build if a type name acquires a domain term.
- `validate_all.py` — validates every extension in this tree.

## Validate

```powershell
python metaverse-specs\validate_all.py --self-contained
```

Every validator is a **stdlib-only structural check against the committed NodeSets**, so it runs on a clean checkout with no dependencies. `--self-contained` restricts the run to validators needing no untracked reference data — which is what CI uses, and today is all of them, so both forms are equivalent. (The artifacts validator additionally verifies the codeless schema through `PlugRegistry` when the USD Python SDK `pxr` happens to be installed, and skips that check otherwise.)

Each generated model is rebuilt from a single in-code source of truth (`extras/*/tools/build_model.py`) and is **deterministic** — regenerating reproduces the committed NodeSet byte for byte. Edit the generator, never the generated NodeSet or CSV.

NodeId assignment is **append-only**: new members take the next free id, because inserting one mid-file silently renumbers everything after it. Verify with a diff of `*.NodeIds.csv` against `main` before committing.
