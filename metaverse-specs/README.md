# metaverse-specs — OPC UA for virtual worlds, perception and robot control

Draft specifications connecting **OPC UA** to the systems that visualize, perceive and command physical machines — the "metaverse" / digital-twin track. Two of them bind OPC UA to **OpenUSD** (Universal Scene Description); the other two supply information models OPC UA lacks entirely, for **machine vision** and for **commanding a robot**.

Nothing here is normative, official, or endorsed by the OPC Foundation, the Alliance for OpenUSD, VDMA or any manufacturer. Namespace URIs and NodeIds are **provisional** and for prototyping only.

> **Every OPC UA specification described in this group is under OPC Foundation review** and is maintained in [`OPCF-Members/spec-drafts`](https://github.com/OPCF-Members/spec-drafts) until review completes. OPC Foundation members can [request access](https://github.com/OPCF-Members/Help); see [*Specifications under OPC Foundation review*](../README.md#specifications-under-opc-foundation-review). The independent [OpenUSD Artifact Registry working draft](https://github.com/xregistry/spec/blob/main/workingdrafts/models/openusd/spec.md) is maintained by the xRegistry project.

## The OpenUSD pair: two parts, two directions

The two specifications approach the same problem from opposite ends and are deliberately independent:

| | <!-- release-spec-link:W2BvcGVudXNkLWJpbmRpbmcvYF0oLi4vc291cmNlL21ldGF2ZXJzZS1zcGVjcy9vcGVudXNkLWJpbmRpbmcvKQ== -->`openusd-binding/`<!-- /release-spec-link --> — **Part 1** | <!-- release-spec-link:W2BvcGVudXNkLXNjZW5lL2BdKG9wZW51c2Qtc2NlbmUvKQ== -->`openusd-scene/`<!-- /release-spec-link --> — **Part 2** |
|---|---|---|
| Question | *Which USD prim represents this OPC UA Object, and which Variables drive its attributes?* | *What if the USD scene graph simply **were** an OPC UA address space?* |
| The scene lives | outside OPC UA, in `.usd` files a connector renders | inside OPC UA, as first-class browsable nodes |
| You get | a thin binding layer over an existing USD asset | Stage/Prim/Attribute/Relationship/Composition as ObjectTypes |
| Namespace | `http://opcfoundation.org/UA/OpenUSD/` | `http://opcfoundation.org/UA/OpenUSD/Scene/` |
| Release | 0.5.0 | 0.4.0 |

**Part 2 does not require Part 1.** It is self-contained on base OPC UA. Where a Server implements both, Part 1's `Server/OpenUSD/Stages` discovery and its bindings can target Part 2 attributes — see Part 2 Annex C.

Pick Part 1 when you already have an artist-authored USD asset and want to drive it. Pick Part 2 when the scene itself should be the address space — browsable, subscribable, historizable.

## The three standalone models

| | <!-- release-spec-link:W2B2aXNpb24vYF0oLi4vc291cmNlL21ldGF2ZXJzZS1zcGVjcy92aXNpb24vKQ== -->`vision/`<!-- /release-spec-link --> | <!-- release-spec-link:W2Byb2JvdC1pbnRlbnQvYF0oLi4vc291cmNlL21ldGF2ZXJzZS1zcGVjcy9yb2JvdC1pbnRlbnQvKQ== -->`robot-intent/`<!-- /release-spec-link --> | <!-- release-spec-link:W2BhaS1tb2RlbC1tYW5hZ2VtZW50L2BdKC4uL3NvdXJjZS9tZXRhdmVyc2Utc3BlY3MvYWktbW9kZWwtbWFuYWdlbWVudC8p -->`ai-model-management/`<!-- /release-spec-link --> |
|---|---|---|---|
| Question | *What does this camera see, and what did it conclude?* | *How do I tell this robot what to do?* | *Which model produced this answer, and can I audit it?* |
| The gap | OPC 40100-1 leaves result content undefined; OPC 40010-1 has no vision types at all | OPC 40010-1 describes robot topology and defines **no motion verbs** | OPC UA has no way to say what an AI model *is*, where it runs, or what it was trained on |
| Namespace | `http://opcfoundation.org/UA/Vision/` | `http://opcfoundation.org/UA/RobotIntent/` | `http://opcfoundation.org/UA/AI/` |
| Release | 0.4.1 | 0.3.0 | 0.5.1 |

Vision and Robot Intent are self-contained on base OPC UA. AI Model Management additionally requires *OPC UA — xRegistry*, because its model catalogue is a domain extension of that abstract registry rather than a private invention — a model catalogue **is** a registry, and defining a second one would leave two incompatible ways to describe the same artefact.

**They compose without coupling.** Vision's `InferencePipelineType.Deployment` and `VisionResultType.ModelUsed` are plain `NodeId` Properties, so a Server can publish cameras and verdicts with no AI model at all. Where it implements both models, `Deployment → UsesModel` identifies the model serving now, while `result.ModelUsed → ModelType → Digest` identifies the model that produced a retained result. Vision and Robot Intent share a frame vocabulary with identical literals and numbering. In every case the join is a **facet precondition**, never a `RequiredModel` — which is what lets a domain adopt one model without inheriting the others.

For a short browse-oriented introduction to the two models and their ownership boundary, see <!-- release-spec-link:W1Zpc2lvbiBhbmQgQUkgTW9kZWwgTWFuYWdlbWVudCB3YWxrdGhyb3VnaF0oLi4vc291cmNlL21ldGF2ZXJzZS1zcGVjcy9SRUFETUUubWQp -->[Vision and AI Model Management walkthrough](https://github.com/OPCF-Members/spec-drafts/blob/main/source/metaverse-specs/README.md)<!-- /release-spec-link -->. For transport-neutral guidance on retaining Vision results outside an OPC UA Server, see [External Result Mapping for Vision and AI](../source/metaverse-specs/vision-ai-external-result-mapping.md).

## Layout

- <!-- release-spec-link:YG9wZW51c2QtYmluZGluZy9gIOKAlCBQYXJ0IDEgc3BlY2lmaWNhdGlvbiwgTm9kZVNldCwgQ1NWLCBpbXBsZW1lbnRlciBhZGRlbmRhIGZvciBgcHVtcHMvYCBhbmQgYHJvYm90aWNzL2AsIHdpdGggdGhlIGluZGVwZW5kZW50IFtPcGVuVVNEIEFydGlmYWN0IFJlZ2lzdHJ5IHdvcmtpbmcgZHJhZnRdKGh0dHBzOi8vZ2l0aHViLmNvbS94cmVnaXN0cnkvc3BlYy9ibG9iL21haW4vd29ya2luZ2RyYWZ0cy9tb2RlbHMvb3BlbnVzZC9zcGVjLm1kKSBtYWludGFpbmVkIGJ5IHRoZSB4UmVnaXN0cnkgcHJvamVjdC4= -->*Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).*<!-- /release-spec-link -->
- <!-- release-spec-link:YG9wZW51c2Qtc2NlbmUvYCDigJQgUGFydCAyIHNwZWNpZmljYXRpb24sIE5vZGVTZXQsIENTViwgYW5kIG1hdGVyaWFsaXplZCBleGFtcGxlIG92ZXJsYXlzLg== -->*Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).*<!-- /release-spec-link -->
- <!-- release-spec-link:W2Bzb3VyY2UvbWV0YXZlcnNlLXNwZWNzL3Zpc2lvbi9gXSguLi9zb3VyY2UvbWV0YXZlcnNlLXNwZWNzL3Zpc2lvbi8pIOKAlCAqKk9QQyBVQSDigJQgVmlzaW9uKio6IHNlbnNvcnMsIHRoZSBtZWRpYSB0aGV5IGVtaXQsIHRoZSBBSSB0aGF0IGludGVycHJldHMgdGhlbSwgdGhlIHJlc3VsdHMgdGhleSBwcm9kdWNlLCBhbmQgdGhlIGZlZWRiYWNrIHBhdGggYmFjayBpbi4gU3RhbmRhbG9uZSBvbiBiYXNlIE9QQyBVQSwgd2l0aCB3b3JrZWQgYWRkZW5kYSBmb3IgYHJvYm90aWNzL2AgYW5kIGBtYWNoaW5lLXZpc2lvbi9gLg== -->*Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).*<!-- /release-spec-link -->
- <!-- release-spec-link:W2Bzb3VyY2UvbWV0YXZlcnNlLXNwZWNzL3JvYm90LWludGVudC9gXSguLi9zb3VyY2UvbWV0YXZlcnNlLXNwZWNzL3JvYm90LWludGVudC8pIOKAlCAqKk9QQyBVQSDigJQgUm9ib3QgSW50ZW50Kio6IHRhc2stbGV2ZWwgdmVyYnMgZm9yIGNvbW1hbmRpbmcgYSByb2JvdCwgd2l0aCBhIFBhcnQgMTAgbGlmZWN5Y2xlLiBPUEMgNDAwMTAtMSBkZXNjcmliZXMgcm9ib3QgdG9wb2xvZ3kgYW5kIGRlZmluZXMgbm8gbW90aW9uIHZlcmJzOyB0aGlzIHN1cHBsaWVzIHRoZSB2ZXJicyBhbmQgbm90aGluZyBlbHNlLiBTdGFuZGFsb25lIG9uIGJhc2UgT1BDIFVBLg== -->*Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).*<!-- /release-spec-link -->
- <!-- release-spec-link:W2Bzb3VyY2UvbWV0YXZlcnNlLXNwZWNzL2FpLW1vZGVsLW1hbmFnZW1lbnQvYF0oLi4vc291cmNlL21ldGF2ZXJzZS1zcGVjcy9haS1tb2RlbC1tYW5hZ2VtZW50Lykg4oCUICoqT1BDIFVBIOKAlCBBSSBNb2RlbCBNYW5hZ2VtZW50IGFuZCBJbmZlcmVuY2UqKjogd2hhdCBhIG1vZGVsIGlzLCBob3cgdG8gY2FsbCBpdCwgaG93IHRvIGNhbGwgb25lIGhvc3RlZCBzb21ld2hlcmUgZWxzZSwgYW5kIGhvdyB0byBnZXQgb25lIGZyb20gYSBjYXRhbG9ndWUgb250byB0aGUgbWFjaGluZS4gRGVsaWJlcmF0ZWx5ICoqZG9tYWluLW5ldXRyYWwqKiDigJQgaXQgbmFtZXMgbm8gY2FtZXJhLCBubyByb2JvdCBhbmQgbm8gc2Vuc29yIOKAlCBzbyBhbnkgZG9tYWluIGNhbiBidWlsZCBvbiBpdC4gVGhlIGludm9jYXRpb24gc3VyZmFjZSBkb2VzIG5vdCBjaGFuZ2Ugd2l0aCB3aGVyZSBpbmZlcmVuY2UgcnVuczsgd2hhdCBjaGFuZ2VzIGlzIHRoZSB0cnVzdCBib3VuZGFyeSwgYW5kIGNsYXVzZXMgOCBhbmQgMTAgYXJlIGFib3V0IHNheWluZyBzbyBvdXQgbG91ZDogd2hhdCBoYXBwZW5zIHdoZW4gdGhlIGxpbmsgZHJvcHMsIGFuZCB3aGV0aGVyIGNhbGxpbmcgYSBtb2RlbCBzZW5kcyBwbGFudCBkYXRhIG9mZiBzaXRlLg== -->*Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).*<!-- /release-spec-link -->
- [`extras/metaverse-specs/`](../extras/metaverse-specs/) — everything secondary to standardization, grouped by specification:
  - `openusd-binding/tools/` — the model generator and validator; `examples/` — the pumps and robotics USD assets, binding descriptors, writers, renderers and end-to-end guides.
  - `openusd-scene/tools/` — the model generator, the `.usd` ↔ NodeSet converters, and the round-trip checker.
  - `openusd-artifacts/` — the emitted xRegistry **artifact registry** for the examples (see Part 1 §7.11).
  - <!-- release-spec-link:YHZpc2lvbi90b29scy9gIOKAlCB0aGUgbW9kZWwgZ2VuZXJhdG9yLCB0aGUgZXhhbXBsZSBidWlsZGVyIGFuZCB0aGUgdmFsaWRhdG9yLg== -->*Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).*<!-- /release-spec-link -->
  - <!-- release-spec-link:YHJvYm90LWludGVudC90b29scy9gIOKAlCB0aGUgbW9kZWwgZ2VuZXJhdG9yIGFuZCB0aGUgdmFsaWRhdG9yLg== -->*Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).*<!-- /release-spec-link -->
  - <!-- release-spec-link:YGFpLW1vZGVsLW1hbmFnZW1lbnQvdG9vbHMvYCDigJQgdGhlIG1vZGVsIGdlbmVyYXRvciBhbmQgdGhlIHZhbGlkYXRvciwgaW5jbHVkaW5nIHRoZSBkb21haW4tbmV1dHJhbGl0eSBjaGVjayB0aGF0IGZhaWxzIHRoZSBidWlsZCBpZiBhIHR5cGUgbmFtZSBhY3F1aXJlcyBhIGRvbWFpbiB0ZXJtLg== -->*Under OPC Foundation review — moved to [OPCF-Members/spec-drafts](https://github.com/OPCF-Members/spec-drafts); OPC Foundation members can [request access](https://github.com/OPCF-Members/Help).*<!-- /release-spec-link -->
- [`extras/metaverse-specs/validate_all.py`](../extras/metaverse-specs/validate_all.py) — validates every active metaverse extension.

## Validate

```powershell
python extras\metaverse-specs\validate_all.py --self-contained
```

Every validator is a **stdlib-only structural check against the committed NodeSets**, so it runs on a clean checkout with no dependencies. `--self-contained` restricts the run to validators needing no untracked reference data — which is what CI uses, and today is all of them, so both forms are equivalent. (The artifacts validator additionally verifies the codeless schema through `PlugRegistry` when the USD Python SDK `pxr` happens to be installed, and skips that check otherwise.)

Each generated model is rebuilt from a single in-code source of truth (`extras/*/tools/build_model.py`) and is **deterministic** — regenerating reproduces the committed NodeSet byte for byte. Edit the generator, never the generated NodeSet or CSV.

NodeId assignment is **append-only**: new members take the next free id, because inserting one mid-file silently renumbers everything after it. Verify with a diff of `*.NodeIds.csv` against `main` before committing.
