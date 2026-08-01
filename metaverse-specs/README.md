# metaverse-specs — OPC UA ⇄ OpenUSD

Draft specifications connecting **OPC UA** to **OpenUSD** (Universal Scene Description) — the "metaverse" / digital-twin visualization track. The goal across both parts is the same: let a generic connector or renderer show **live industrial data** in a USD scene without anyone hard-coding the mapping.

Nothing here is normative, official, or endorsed by the OPC Foundation or the Alliance for OpenUSD. Namespace URIs and NodeIds are **provisional** and for prototyping only.

## Two parts, two directions

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

## Layout

- <!-- release-spec-link:YG9wZW51c2QtYmluZGluZy9gIOKAlCBQYXJ0IDEgc3BlY2lmaWNhdGlvbiwgTm9kZVNldCwgQ1NWLCBpbXBsZW1lbnRlciBhZGRlbmRhIGZvciBgcHVtcHMvYCBhbmQgYHJvYm90aWNzL2AsIGFuZCB0aGUgc3RhbmRhbG9uZSAqKnhSZWdpc3RyeSBkb21haW4gc3BlY2lmaWNhdGlvbioqIGZvciB0aGUgYXJ0aWZhY3QgcmVnaXN0cnkgKGB4UmVnaXN0cnktT3BlblVzZC5tZGApLCB3aGljaCBkZWZpbmVzIHRoZSBzYW1lIHJlZ2lzdHJ5IGluZGVwZW5kZW50bHkgb2YgT1BDIFVBIHNvIHRoZSB0d28gcHJvamVjdGlvbnMgZmVkZXJhdGUu -->*Under OPC Foundation review; temporarily maintained outside this repository.*<!-- /release-spec-link -->
- <!-- release-spec-link:YG9wZW51c2Qtc2NlbmUvYCDigJQgUGFydCAyIHNwZWNpZmljYXRpb24sIE5vZGVTZXQsIENTViwgYW5kIG1hdGVyaWFsaXplZCBleGFtcGxlIG92ZXJsYXlzLg== -->*Under OPC Foundation review; temporarily maintained outside this repository.*<!-- /release-spec-link -->
- `extras/` — everything secondary to standardization, mirroring the two folders above:
  - `openusd-binding/tools/` — the model generator and validator; `examples/` — the pumps and robotics USD assets, binding descriptors, writers, renderers and end-to-end guides.
  - `openusd-scene/tools/` — the model generator, the `.usd` ↔ NodeSet converters, and the round-trip checker.
  - `openusd-artifacts/` — the emitted xRegistry **artifact registry** for the examples (see Part 1 §7.11).
- `validate_all.py` — validates every OpenUSD extension.

## Validate

```powershell
python metaverse-specs\validate_all.py --self-contained
```

Every validator is a **stdlib-only structural check against the committed NodeSets**, so it runs on a clean checkout with no dependencies. `--self-contained` restricts the run to validators needing no untracked reference data — which is what CI uses, and today is all of them, so both forms are equivalent. (The artifacts validator additionally verifies the codeless schema through `PlugRegistry` when the USD Python SDK `pxr` happens to be installed, and skips that check otherwise.)

Each generated model is rebuilt from a single in-code source of truth (`extras/*/tools/build_model.py`) and is **deterministic** — regenerating reproduces the committed NodeSet byte for byte. Edit the generator, never the generated NodeSet or CSV.

NodeId assignment is **append-only**: new members take the next free id, because inserting one mid-file silently renumbers everything after it. Verify with a diff of `*.NodeIds.csv` against `main` before committing.
