# Word drafts

Submission-ready **Microsoft Word** renderings of the specification drafts, built into the
official OPC Foundation companion specification template
(`templates/OPC 20020 - UA Companion Specification Template v1.01.19.docx`).

Nothing here is normative or endorsed by the OPC Foundation. The document number, the Mantis
project identifier and every NodeId are the template's own placeholders; the OPC Foundation
assigns the real values.

## These files are generated — please do not edit them

Every `.docx` and every `.docmodel.json` in this folder is a **build output**. The next build
overwrites it, so an edit made here is lost and leaves no trace. Change the source instead:

| To change | Edit |
|---|---|
| the words of a specification | its markdown under `core-specs/`, `companion-specs/`, `metaverse-specs/` or `wot-specs/` |
| a type, a Property, a NodeId | that specification's `tools/build_model.py`, then regenerate its NodeSet |
| the clause order, titles, identity, figures | that document's config in `tools/specs/` |
| the shape of the rendering itself | `tools/opcdocx/` |

Then rebuild with `python word-drafts/tools/build_all.py`. This mirrors what the repository
README already asks for generated artifacts: *edit the source, not the generated NodeSet /
CSV, and regenerate.*

## Reviewing and collaborating

**The documents open with Word's change tracking already turned on.** Mark one up and your
edits are recorded as visible, attributable revisions rather than silent changes — which is
exactly what makes a marked-up `.docx` useful as review feedback, even though the file itself
is regenerated.

**Send the marked-up file back and it becomes a pull request.** Open an issue, attach the
document, add the `word-review` label, and stop there. Your tracked changes become the pull
request's diff, your comments become a review on it, and the issue gets a reply with the link.
You need no git and no markdown, and you never describe the same change twice. What makes that
possible is that every paragraph carries the address of the source line it was rendered from,
so a mark can be traced back rather than guessed at — see *Sending a review back* below.

**These documents are regenerated automatically.** Every push to `main` that changes a
specification rebuilds them and collects the result on one standing pull request, so a `.docx`
here cannot quietly fall behind the markdown it renders. That pull request opens as a draft,
because finishing a document needs Microsoft Word — see *Sending a review back*.

If you would rather work in the repository directly, follow the *Contributing* section of the
[repository README](../README.md) and [`CONTRIBUTING.md`](../CONTRIBUTING.md): fork, branch,
annotate or change, then open a pull request — or open an issue if you would rather just raise
a point than edit anything. You do not have to write specification text yourself; maintainers
turn the discussion into concrete changes to the source and regenerate everything here.

| Artifact | What it is |
|---|---|
| `OPC-UA-OpenUSD-Binding-Part1.docx` | OpenUSD Binding, Part 1. |
| `OPC-UA-OpenUSD-Scene-Part2.docx` | OpenUSD Scene Materialization, Part 2. |
| `OPC-UA-xRegistry.docx` | xRegistry, the abstract registry base model. |
| `OPC-UA-Schema-Registry.docx` | Schema Registry, a domain registry on that base. |
| `OPC-UA-Observability-Export.docx` | Observability Export. |
| `OPC-UA-WoT-Connectivity.docx` | WoT Connectivity. |
| `OPC-UA-WoT-Binding.docx` | WoT Binding — declares a template deviation; see below. |
| `OPC-UA-Generators.docx` | Generators (generator sets). |
| `OPC-UA-Data-Channels.docx` | Data Channels — extends the base namespace; see below. |
| `OPC-UA-Avro-Encoding.docx` | Apache Avro DataEncoding — declares a template deviation; see below. |
| `OPC-UA-Arrow-Encoding.docx` | Apache Arrow DataEncoding — declares a template deviation; see below. |
| `*.docmodel.json` | The intermediate representation each document was rendered from. Committed **because a `.docx` diff is unreadable** — review this instead. |
| `*.provenance.json` | What each paragraph of the document was rendered from. This is what lets a marked-up copy be turned back into a change to the source. |
| `figures/*.pptx` | The editable PowerPoint behind each figure, embedded in the document as an OLE object. |
| `figures/*.png` | The preview image Word displays for each embedded object. |
| `tools/` | The build, the validator, its mutation test, the batch runner and the ingest. |

## Commands

```powershell
# one-time
pip install -r word-drafts/tools/requirements.txt

# markdown + NodeSet -> .docx  (pure Python, cross-platform, byte-reproducible)
# the whole batch: build, validate and mutation-test every converted specification
python word-drafts/tools/build_all.py

# what is converted, what is ready to convert next, and what is not a fit
python word-drafts/tools/build_all.py --list

# one specification at a time
python word-drafts/tools/build_docx.py         word-drafts/tools/specs/generators.json
python word-drafts/tools/validate_docx.py      word-drafts/tools/specs/generators.json
python word-drafts/tools/test_validate_docx.py word-drafts/tools/specs/generators.json

# update the table of contents, the table of figures, the table of tables and every
# cross-reference, so the committed file opens fully paginated  (needs Word; local only)
pwsh word-drafts/tools/finalize_word.ps1 -Path word-drafts/OPC-UA-Generators.docx

# the same for every converted document, then re-validate that each really is finalised
pwsh word-drafts/tools/finalize_all.ps1

# check the committed documents without opening Word
pwsh word-drafts/tools/finalize_all.ps1 -VerifyOnly

# a reviewed document -> a report, a branch, a pull request and a review
python word-drafts/tools/ingest_docx.py reviewed.docx
python word-drafts/tools/ingest_docx.py reviewed.docx --pr --dry-run
python word-drafts/tools/ingest_docx.py reviewed.docx --pr

# make a marked-up document to test the ingest against  (needs Word; local only)
pwsh word-drafts/tools/make_review_fixture.ps1 -Path word-drafts/OPC-UA-Generators.docx `
     -Out $env:TEMP/reviewed.docx -Edits 'old wording=>new wording'

# rewrite the markdown source into the same clause skeleton  (one-shot per restructure)
python word-drafts/tools/restructure_markdown.py word-drafts/tools/specs/openusd-binding.json
```

**`build_all.py` un-finalises everything it rebuilds, so always follow it with
`finalize_all.ps1`.** The pure-Python build writes fields, not field *results*: without the Word
pass the table of contents is empty and every cross-reference is blank until a reader presses F9.
Nothing else notices — the package is well formed and every other check passes — so
`validate_docx.py --finalized` exists to say so, and `finalize_all.ps1 -VerifyOnly` runs it across
the set.

The committed `.docx` is therefore the **post-finalise** file. A plain rebuild produces the
pre-finalise one, so the working tree will look dirty until you finalise again — Word's own save is
not byte-deterministic. The *build* is: two consecutive `build_docx.py` runs produce identical
bytes, which is what makes a `docmodel.json` diff meaningful.

## How it works

The template is **cloned, not rebuilt**. `build_docx.py` opens the template package and replaces
only the body ranges it owns; styles, numbering, settings, headers, footers, theme, fonts and the
five embedded OPC UA introduction figures are copied through byte-for-byte. Formatting therefore
matches the template by construction rather than by inspection.

Roughly 40 % of a conforming document is template boilerplate, and the build keeps it verbatim:
the cover, the legal front matter, clause 3.4 *Conventions used in this document* with its
Tables 1–14, clause 4.2 *Introduction to OPC Unified Architecture* with its figures, the Annex A
skeleton and the back matter. Only the placeholder tokens inside those regions are substituted.

Everything else is generated:

- **Prose** comes from the markdown draft, parsed into a semantic document model.
- **Node tables** are derived from `Opc.Ua.OpenUsd.NodeSet2.xml`, never transcribed, so the
  document and the model cannot disagree — and so the tables parse in the OPC Foundation's own
  Word-versus-NodeSet validator.
- **Figures** are rebuilt from the Mermaid sources as editable PowerPoint files and embedded as OLE
  objects, because the template forbids inline Word drawing objects.
- **Numbering** is left to Word: headings carry no literal clause number, captions carry `SEQ`
  fields, and cross-references are `REF` fields over bookmarks.

`tools/specs/<spec>.json` holds the whole per-document contract — identity, normative references,
abbreviations, the clause map and the figure list. Adding another specification of the same shape is
a new config file; a genuinely new shape needs a generalisation in `opcdocx/` first.

| Document | Built from |
|---|---|
| `OPC-UA-OpenUSD-Binding-Part1.docx` | `metaverse-specs/openusd-binding/` + `Opc.Ua.OpenUsd.NodeSet2.xml` — plus two folded annexes; see below |
| `OPC-UA-OpenUSD-Scene-Part2.docx` | `metaverse-specs/openusd-scene/` + `Opc.Ua.OpenUsdScene.NodeSet2.xml` |
| `OPC-UA-xRegistry.docx` | `core-specs/xregistry/` + `Opc.Ua.XRegistry.NodeSet2.xml` |
| `OPC-UA-Observability-Export.docx` | `core-specs/observability-export/` + `Opc.Ua.ObservabilityExport.NodeSet2.xml` — plus five folded annexes; see below |
| `OPC-UA-WoT-Connectivity.docx` | `wot-specs/WoT-Connectivity/` + `Opc.Ua.WoTCon.NodeSet2.xml` |
| `OPC-UA-WoT-Binding.docx` | `wot-specs/WoT-Binding/` — **no NodeSet**; see below |
| `OPC-UA-Schema-Registry.docx` | `core-specs/schema-registry/` + `Opc.Ua.SchemaRegistry.NodeSet2.xml` |
| `OPC-UA-Generators.docx` | `companion-specs/Generators/` + `Opc.Ua.Generators.NodeSet2.xml` |
| `OPC-UA-Data-Channels.docx` | `core-specs/data-channels/` + `Opc.Ua.DataChannels.NodeSet2.xml` — **base namespace**; see below |
| `OPC-UA-Avro-Encoding.docx` | `core-specs/encodings/avro/` — **no NodeSet**; see below |
| `OPC-UA-Arrow-Encoding.docx` | `core-specs/encodings/arrow/` — **no NodeSet**; see below |

## The ones that are annexes, not submissions

Seven markdown files in this repository are worked examples: they show what an existing
specification looks like applied to DI, to Facets, to Pumps, to Robotics. Each carries a
provisional `Examples` namespace or an example URN, defines instances rather than types, and has
no conformance clause — so none of them is a submission in its own right, and rendering each as a
standalone companion specification would have said something untrue on its title page.

They are published as what they are: **informative annexes of the specification they illustrate**.
A config may name extra sources under `additionalMarkdown`, and a clause-map entry may then carry
`in` to say which source it is drawn from. Sections are keyed per source, so an annex's own
"1 Scope" does not collide with the base document's. Two land in OpenUSD Binding Part 1 (annexes G
and H) and five in Observability Export (annexes D to H). `tools/specs/batch.json` records each one
under `notAFit`, naming the document it folds into.

## The one that owns no namespace

Ten of the eleven documents own a namespace. **Data Channels does not**: it proposes additions to
OPC 10000-3, -4 and -6, and its NodeSet declares `ModelUri = http://opcfoundation.org/UA/`, so its
Nodes live in the base namespace. It is rendered without a declared deviation — the NamespaceUri in
Annex A genuinely *is* that — but only because three things were made true first:

- `IsNamespaceSubset` is `True`, since the file holds this document's additions and not the whole
  base namespace. It used to be hard-coded `False` with prose to match, which here would have been
  a plain untruth.
- `StaticNumericNodeIdRange` is derived from the model (`65000:66038`) instead of the constant
  `1001:9999`, which was wrong for six of the other documents too.
- A base BrowseName prints unprefixed, because a document whose own namespace *is* namespace 0
  would otherwise show the same namespace two ways in one table.

The three insertion-ready errata beside it (`OPC-UA-Part3/4/6-*.md`) are tracked-change text against
existing core Parts. They are listed as not a fit, and that is a statement about them, not about the
pipeline.

## What is converted, and what is next

`tools/specs/batch.json` is the inventory. It lists the specifications that are converted, the ones
whose shape the pipeline already handles — so onboarding them is a config file plus the editorial
work the entry names — and the ones that are not a fit, with the reason. `build_all.py --list`
prints it.

**Every specification in this repository is now converted**, so the middle list is empty. The next
markdown specification added to the repository gets an entry there, then a config, then a row in the
tables above.

A document is "not a fit" only for a reason about the document, not about the tooling: an amendment
to a core Part is not a companion specification, a worked example belongs in the specification it
illustrates rather than beside it, and a presentation or a measurement report is not a specification
at all.

## Declared deviations

Eight of the eleven documents comply with OPC 20020 without deviation. Three cannot, all for the
same reason: **WoT Binding** defines a JSON-LD vocabulary and a NodeSet-to-WoT mapping, and the two
**encoding** specifications define a wire format. None of them has a NodeSet, ObjectTypes or
Instances, so the template's NodeClass clauses and Annex A NodeSet block have nothing to present.

A deviation is therefore something the pipeline refuses to take quietly. It must be

1. declared in the spec config (`templateDeviations`, with an `id` the contract knows),
2. printed into the document by the build — each of the three states it in clause 1.2, and
3. found there by `validate_docx.py`, which only then skips the checks that deviation names.

An undeclared deviation still fails, and a declared one whose statement is missing from the document
fails too. The result is a document validated against a smaller contract that the document itself
states.

## Sending a review back

The pipeline runs both ways. A marked-up `.docx` becomes a pull request whose diff is the
reviewer's tracked changes and whose review carries their comments.

**Every paragraph knows where it came from.** The build stamps a deterministic
`w14:paraId` on each paragraph and writes `*.provenance.json` beside the document mapping
those ids to source addresses. Word preserves an id it finds and only invents one where none
exists — measured: all 1255 ids in one document survived an edit-and-save round trip intact —
so a mark can be traced to the markdown that produced it without matching text or guessing at
positions. A paragraph whose id is unknown is one the reviewer created.

**Not every mark belongs in the markdown.** The ingest routes each one to its real owner and
applies only the first row:

| Marked content | Owner | What happens |
|---|---|---|
| Prose rendered from markdown | that `.md` | applied |
| Node tables | the UANodeSet / `build_model.py` | reported as a model change request |
| Clause 4.1, use cases, Annex A identity | `tools/specs/<spec>.json` | reported |
| Clause and caption numbers, cross-references | Word fields | reported — numbering is not authored |
| Retained template regions | the OPC 20020 template | reported, and flagged as a deviation |

**A change that cannot be placed exactly is refused.** The text a reviewer sees is not the
markdown — inline markup is gone, cross-references have become numbers, BrowseNames have been
resolved — so an edit is applied only where the text it replaces occurs exactly once in that
paragraph's own source lines. Ambiguity is reported, not guessed at.

**And then it is checked.** The markdown is patched, the document is rebuilt, and every
applied edit must now read the way the reviewer wrote it. One that does not is reported as
unapplied and blocks the pull request. That is the same discipline as the rest of the
pipeline: check the printed form, because both sides can agree on the same wrong thing.

One GitHub constraint shapes the comments. **The REST API will not attach an inline comment
to a line that is not part of the diff** — the web interface allows it, the API answers 422.
So a comment on a paragraph the reviewer also changed becomes a real inline comment, and a
comment on a paragraph they left alone is collected into the review body with a permanent
link to the exact lines, which GitHub renders as a quoted snippet. Inventing an edit to host
a comment would make the diff claim a change nobody asked for, so the ingest does not.

### Where the agent takes over

The ingest is deliberately narrow: it applies a change only where it can place it exactly,
and refuses everything else. What is left is not a failure but a different kind of work — a
comment states a problem rather than supplying replacement text, a mark may belong in the
information model, an edit may be unplaceable because the prose around it was rewritten.

That remainder goes to the coding agent, on the branch the ingest already built. It is given
the **report, not the document**, so it cannot revert or re-apply the exact edits; and it is
told that changing nothing is a valid outcome, because the branch already carries the
reviewer's marks and a guessed interpretation is worse than none.

Mechanical where it is exact, agentic where it needs judgement, and never both on the same
text.

### Regenerating on `main`

`.github/workflows/word-drafts-refresh.yml` rebuilds every document on each push to `main`
and collects the result on one standing pull request, from the branch `word-drafts/refresh`.
The build is byte-reproducible, so a document whose sources did not change comes out
identical and simply does not appear in the diff — nothing has to work out which documents
to rebuild.

It opens as a **draft** and stays one until the documents are finalised. CI cannot finalise
them — that needs Word — but it can *check* it, so the pull request flips to ready for
review on the next run once `validate_docx.py --finalized` passes for every document.
Merging it deletes the branch, and the next specification change opens a fresh one.

## The clause map

One mapping drives two consumers. `build_docx.py` orders the Word clauses from it, and
`restructure_markdown.py` rewrites the markdown into the same structure and rewrites every section
reference through it — in this document and in every sibling that cites it. That is what keeps the
markdown and the Word rendering from drifting into different structures.

`.github/scripts/check_section_refs.py` is the gate: it fails on any `§` reference that does not
resolve to a clause of the document it names.

## Known deviations

- The document number (`OPC nnnnn-m`), the Mantis project id and the NodeIds are deliberately left
  as placeholders, with a visible provisional banner in clause 1. They are build-config keys, so a
  real number can be dropped in without touching code.
- The clauses *OPC UA EventTypes*, *OPC UA VariableTypes*, *OPC UA ReferenceTypes*, *Instances* and
  *Well-Known BrowseNames* are removed: the model defines none of those, and the template's own
  Annex A instruction ("if not needed, this Annex section shall be deleted") is the pattern.
- `Server/OpenUSD` is a well-known instance the specification mandates, but the generator
  deliberately keeps concrete instances out of a type-only base NodeSet, so it has no *Instances*
  clause. Adding one is a model decision, not a rendering decision.
