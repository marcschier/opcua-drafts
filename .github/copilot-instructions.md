# Copilot instructions — opcua-drafts

Draft **OPC UA specification documents and information models**. Nothing here is normative or
endorsed by the OPC Foundation; namespace URIs and NodeIds are provisional.

Most specifications are **generated from a single source of truth**, so the prose, the NodeSet,
the NodeId CSV and the Annex tables cannot drift apart. The most common way to break this repo is
to hand-edit a generated file.

[`CONTRIBUTING.md`](../CONTRIBUTING.md) covers the *process* — fork, branch, regenerate, validate,
PR. This file covers the commands, the architecture, and the *style*: the editorial and modelling
conventions the drafts have converged on.

Most rules below exist because breaking them produced a real defect that a green validation run did
not catch. The reason is given with each one; when a rule and a reason disagree, follow the reason.

## Commands

```powershell
# one-time
pip install -r core-specs/extras/requirements.txt

# validate everything (two separate entrypoints — neither covers the other's tree)
python core-specs/extras/validate_all.py
python metaverse-specs/validate_all.py

# what CI runs — only the checks that need no untracked base data
python core-specs/extras/validate_all.py --self-contained
python metaverse-specs/validate_all.py --self-contained

# a single extension (the granular unit — there is no per-test runner)
python metaverse-specs/extras/openusd-binding/tools/validate_local.py
python core-specs/xregistry/tools/validate_local.py

# regenerate one model, then confirm the diff is only what you intended
python metaverse-specs/extras/openusd-binding/tools/build_model.py

# the same advisory checks CI runs
npx markdownlint-cli2 "**/*.md"
python .github/scripts/check_links.py
python .github/scripts/check_mermaid.py     # needs: npm install -g @mermaid-js/mermaid-cli
python .github/scripts/check_yaml_json.py   # needs: pip install pyyaml
python .github/scripts/check_determinism.py
python .github/scripts/check_section_refs.py

# the Word rendering (see word-drafts/README.md)
pip install -r word-drafts/tools/requirements.txt
python word-drafts/tools/build_docx.py word-drafts/tools/specs/openusd-binding.json
python word-drafts/tools/validate_docx.py word-drafts/tools/specs/openusd-binding.json
python word-drafts/tools/test_validate_docx.py word-drafts/tools/specs/openusd-binding.json
pwsh word-drafts/tools/finalize_word.ps1 -Path word-drafts/OPC-UA-OpenUSD-Binding-Part1.docx
```

`--self-contained` means **"needs no untracked base data"**, not "no dependencies". Full runs
additionally require the gitignored `**/tools/ref/` NodeId tables and a base NodeSet
(`core-specs/pubsub-binding/Opc.Ua.PubSubBinding.NodeSet2.xml`) that is not distributed with the
repository, so full validation and the determinism gate are **local-only**; they skip or run a
subset in CI.

**Every CI check is advisory** (`continue-on-error: true` in `.github/workflows/pr-validation.yml`)
and never blocks a merge — a red job is easy to miss, so read the checks tab anyway.

## Architecture

Four independent specification trees, plus `skills/` (agent instructions that operate on the drafts):

| Tree | Contains |
|---|---|
| `core-specs/` | Proposed extensions to the base OPC UA namespace (encodings, registries, data channels, observability) |
| `metaverse-specs/` | OPC UA ⇄ OpenUSD (two parts: binding, scene materialization) |
| `wot-specs/` | W3C Web of Things binding and connectivity |
| `companion-specs/` | Domain companion specifications |
| `word-drafts/` | Submission-ready Word renderings built into the official OPC Foundation template, plus the build that produces them |
| `templates/` | The official OPC Foundation companion specification template the Word build clones |

**Normative / tooling split.** A spec folder holds only the normative documents and generated
base artifacts; tooling, descriptors and examples live in a mirrored `extras/` tree — for example
`metaverse-specs/openusd-binding/` (spec + NodeSet + CSV) against
`metaverse-specs/extras/openusd-binding/tools/` (generator + validator) and `.../examples/`.

**The split is not applied uniformly**, so locate the generator before assuming where it lives.
Some sit under the spec folder (`core-specs/xregistry/tools/`, `core-specs/schema-registry/tools/`,
`core-specs/data-channels/tools/`, `wot-specs/WoT-Connectivity/tools/`,
`companion-specs/Generators/tools/`) and others under `extras/`
(`core-specs/extras/observability-export/tools/`, all of `metaverse-specs/extras/*/tools/`).

**Validation is per-extension.** Each extension owns a `validate_local.py`; the two `validate_all.py`
files just drive lists of them. `wot-specs/` and `companion-specs/` are in **neither** aggregate —
run their validators directly.

**Registry specs layer.** `core-specs/xregistry/` is an abstract base model (`RegistryType` /
`GroupType` / `ResourceType`); `schema-registry`, the WoT connectivity registry and the OpenUSD
artifact registry are domain subtypes of it. `ResourceType` is itself an OPC UA Part 5 `FileType`,
which is why a registry resource can be streamed with `Open`/`Read`/`Close`.

## Voice and tense

**Write a point-in-time statement of the model, not a changelog.** A specification says what
the model *is*. It never says what it previously was.

Avoid: *"From Release 0.4.0 this facility is an artifact registry"*, *"the streaming contract
is exactly as in 0.2.0"*, *"`Assets` remains, but from 0.4.0 it is a view"*, *"the 0.1 baseline
binding"*.

Write instead: *"The facility is an artifact registry"*, *"`Assets` **is** a view"*.

A reader implementing the spec today should not have to replay prior releases to work out the
current design, and every delta sentence is a maintenance liability that goes stale on its own.

**Release history belongs in `CHANGELOG.md`** beside the specification, where the decisions
survive without the spec narrating them — why a dependency was taken, why an enumeration was
appended rather than renumbered, why a version bumped.

**Version banners stay.** `**Release 0.4.0 — Draft**` and the NodeSet `Version` /
`PublicationDate` identify *this* document. They are identity, not history.

**When removing a delta sentence, rewrite it — do not delete it.** Most carry normative content
in their second half. *"`Assets` remains, but from 0.4.0 it is a **view**"* becomes
*"`Assets` **is** a view"*: the requirement survives, the history does not.

Some phrasing only looks like history and should stay: *"adding a viewer no longer means writing
another bridge"* contrasts with an alternative design, and *"without invalidating previously
deployed connectors"* is a forward-looking property. Judge by whether the sentence describes the
model or its past.

## Normative language

**Match the house style of the target standards body.**

- OPC UA specifications use bold **shall** / **should** / **may**.
- An xRegistry domain specification uses RFC 2119 UPPER CASE (`MUST`, `SHOULD`, `MAY`), because
  that is what the xRegistry specifications use and the document must be submittable as-is.

Do not mix the two in one document.

**Every normative statement must be executable against a legal implementation.** Before writing
a **shall**, check that a conformant server can actually be observed to satisfy or violate it.

A conformance unit once required verifying `Xid`, `Epoch` and `Digest`, all of which were
`Optional` on the inherited base type and never promoted — so the requirement could not be tested
against a legal server. If a conformance unit depends on an inherited member, **promote that
member** in the domain type.

**Do not place a normative recommendation in a specification whose own model cannot satisfy it.**
A `should` to publish a file, in a Part that defines no mechanism for serving files, is
unimplementable. Either scope it (*"Where Part 1 is also implemented…"*) or make it informative.

**Separate a hint from an authority.** Where two members can both signal a change, say which one
decides. `Epoch` is a change *hint* — the base model increments it on any mutation, including a
label edit — while `Digest` is the authority.

## Structure and cross-references

**A specification should stand alone.** A reader who has never seen the companion document must
be able to implement it. Confine cross-references to a "relationship to other specifications"
section and the specific clauses that genuinely interoperate.

**Reference documents, not versions.** Prefer *"Where Part 1 is also implemented"* over
*"Where Part 1 ≥ 0.4.0 is implemented"*. A version floor embedded in prose is a delta statement
that goes stale, and the current document always describes the current model.

**One source of truth per fact.** Never restate a key as an attribute: if a group's id *is* the
asset container identifier, do not also define an `assetContainerId` attribute — that is a second
source of truth that can disagree with the first. The same applies to a media type already
carried by an inherited `ContentType`.

**Keep section numbering in document order.** One draft ran §1.4 → §1.1 → §1.2 → §1.3 for
several releases without anyone noticing.

**Prose wraps at paragraph boundaries**, one line per paragraph, not at a fixed column
(`MD013` is disabled in `.markdownlint-cli2.yaml`).

**A `§` reference must resolve to a real clause.** Renumbering a specification moves every
reference to it, in the document *and* in every sibling that cites it — a stale `§5.15` is
invisible to a spell-checker, a link checker, and a reader who does not follow it.
`python .github/scripts/check_section_refs.py` is the gate.

## The Word rendering

`word-drafts/` holds submission-ready Word documents built into the official OPC Foundation
companion specification template. **The clause map in `word-drafts/tools/specs/<spec>.json` drives
both the Word build and the markdown restructure**, so the two cannot drift into different
structures; the node tables are generated from the UANodeSet, so the document cannot drift from the
model.

Never hand-edit a generated `.docx` — it is a generated artifact exactly like a NodeSet. The
committed `*.docmodel.json` beside it exists so a reviewer can diff the document semantically
instead of diffing a ZIP.

The build is pure Python and byte-reproducible. `finalize_word.ps1` (Word COM, Windows-only, like
the determinism gate) updates the table of contents and every field so the committed file opens
fully paginated. See `word-drafts/README.md` and `skills/opcua-spec-to-word/`.

## The information model

**Edit the generator, never the generated file.** `tools/build_model.py` is the single source of
truth for the NodeSet, the NodeId CSV and the Annex table. Never hand-edit `*.NodeSet2.xml`,
`*.NodeIds.csv`, or `tools/model-reference.md`. Most of the rules below are consequences of this.

**NodeId assignment is append-only.** New members take the next free id at the *end* of the
declaration order. A mid-file insert silently renumbers every id after it. Verify with a diff of
`*.NodeIds.csv` against `main` before every commit — the expected result for an additive change
is *0 changed, 0 removed, N added*.

**Pass ObjectType NodeIds literally to member helpers.** The generators reuse short module-level
aliases (`R`, `S`, `A`, …) across sections, so referring to one parents the member to whatever
type was last assigned. This silently attached an entire registry to the wrong ObjectType while
the generated CSV still showed the correct symbolic name.

**Emit own-namespace NodeIds through the namespace helper (`T()`), never a hardcoded `ns=N`.**
Adding a `RequiredModel` shifts the model's namespace index. A hardcoded index does not merely go
stale — it starts pointing into a different, now-existing model.

**Bump `Version` and `PublicationDate` whenever the model changes**, including a single appended
member. Two models published under one identity are indistinguishable to a client that caches by
`(Version, PublicationDate)`. This has happened: a member and a concreteness change shipped under
an unchanged version. Update every place the version is stated — the spec banner, the generator
constants, example instance overlays' `RequiredModel`, and the folder `README`.

**Keep example instance overlays' `RequiredModel` in step with the base model.** Overlays that
pin an old version drift silently — three of them once required three different versions of the
same base model, none of them current.

**When subtyping a base model, constrain what it left open.** A domain registry that subtypes a
generic one must narrow the inherited placeholders to its own types; otherwise the subtype adds
metadata without actually restricting what the model may hold, and a client cannot tell one kind
of container from another except by convention.

## Examples, descriptors and validators

**Derive examples from the declared source of truth, not by scanning artifacts.** A descriptor
that states what a server serves is authoritative. Static scanning cannot see edges authored at
runtime, and a scan-derived example that happens to look right is right by accident — one example
passed only because it shipped a pre-authored snapshot that the sibling example lacked.

**A validator must be independent of the thing it validates.** Checking a generated field against
the document that the same generator wrote validates the emitter against itself. Re-derive from
the original source instead: re-scan the embedded documents, re-read the descriptor, recompute the
digest.

**Mutation-test the validator.** A checker that passes trivially is worthless. Mutate the artifact
in each way the checker claims to catch — and include the case that is easy to miss, such as a
smuggled reference *with the digest recomputed* — and confirm each mutation fails. Restore
byte-exactly afterwards.

**Cross-check a specification against its model in both directions.** Every attribute and enum
value the model declares must appear in the prose, and every attribute the prose defines must
exist in the model. Neither direction alone catches drift.

**Generators are deterministic.** Building twice produces byte-identical output, so a clean diff
proves the change is exactly what was intended. On Windows, generated files may appear modified
after regeneration purely from `LF`→`CRLF` normalization; confirm with `git diff --stat` before
assuming drift.

## Before opening a pull request

- Regenerate, then diff `*.NodeIds.csv` against `main` and confirm the churn is what you expect.
- Run the extension's validators and `validate_all.py --self-contained`.
- Grep the diff for delta vocabulary — *from Release*, *as in 0.x*, *no longer*, *previously*,
  *supersedes*, *remains but*, *as before* — and justify every hit that survives.
- Check that any version you changed is reflected everywhere it is stated: the spec banner, the
  generator constants, example overlays, and the folder `README`.
- The repository's CI checks are **advisory** and never block a merge, so a red job is easy to
  miss. Read them anyway; they catch real regressions.
