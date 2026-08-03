# The pipeline

```text
markdown draft ─┐
UANodeSet ──────┼─► build_docx.py ─► docmodel.json ─► render_docx.py ─► .docx
build config ───┘                                          │
OPC 20020 template ────────────────────────────────────────┘
   (cloned: styles, numbering, headers, footers, theme, retained clauses, OLE figures)
                                                           │
   Mermaid ─► mermaid_pptx.py ─► .pptx + .png ─► ole_embed.py
                                                           │
                                        validate_docx.py ──┤ 0 errors
                                     test_validate_docx.py ─┤ 0 escaped mutations
                                       finalize_word.ps1 ───┘ Word updates every field
```

## Why two intermediate representations

**`docmodel.json`** is a semantic document model: ordered blocks with inline runs. It is committed
next to the `.docx` because a ZIP diff is unreadable — a reviewer diffs the IR. It is also where
template conformance is decided, before any XML exists.

**The package itself is cloned, not rebuilt.** Opening the template and replacing only the body
ranges we own means `styles.xml`, `numbering.xml`, `settings.xml`, the headers, the footers, the
theme, the font table and the embedded OPC UA introduction figures are copied through byte-for-byte.
Formatting matches the template by construction.

### Alternatives that were rejected

| Approach | Why not |
|---|---|
| `pandoc --reference-doc` | Maps to a fixed style vocabulary (`Heading N`, `Compact`), not the template's ~90 custom styles. Emits no `SEQ`, `REF`, `TOC` fields and no bookmarks, so nothing renumbers. Cannot produce the machine-parseable node tables. |
| `python-docx` alone | Fine for styles and tables, but fields, bookmarks and OLE embeddings need raw `oxml` anyway — at which point `lxml` + `zipfile` is simpler and gives byte control. |
| Driving Word COM for the whole build | Slow, Windows-only, and not reproducible. Word is used only for the finalisation pass. |
| Rendering Mermaid to PNG and inserting a picture | Violates Guideline 1: figures must be embedded document objects. |

## Module map

| Module | Responsibility |
|---|---|
| `opcdocx/contract.py` | The template contract as data: style allow-list, numbering ids, table grids, prohibitions, document-property keys. |
| `opcdocx/oxml.py` | WordprocessingML construction: runs, fields, bookmarks, paragraphs, tables with the template's geometry. |
| `opcdocx/docmodel.py` | The IR: block and inline constructors, JSON round-trip. |
| `opcdocx/md_parse.py` | Markdown → IR. Section references become `xref` runs. |
| `opcdocx/nodeset_tables.py` | UANodeSet → the Table 2 / enumeration / Annex A structures. |
| `opcdocx/writer.py` | IR → body elements, allocating bookmarks and caption sequences. |
| `opcdocx/package.py` | The `.docx` package: clone, edit the body, substitute tokens, write with fixed timestamps. |
| `opcdocx/mermaid_pptx.py` | Mermaid flowchart and sequence diagrams → editable `.pptx` + preview PNG. |
| `opcdocx/ole_embed.py` | The `w:object` / `v:shape` / `o:OLEObject` markup and its parts. |
| `build_docx.py` | Orchestration: config, clause map, generated clauses. |
| `render_docx.py` | The template surgery plan, applied bottom-up. |
| `validate_docx.py` | The contract, checked against the produced file. |
| `test_validate_docx.py` | Mutation test of the validator. |
| `restructure_markdown.py` | The same clause map applied to the markdown source and its siblings. |
| `finalize_word.ps1` | Word COM: update fields, both tables of figures/tables and the TOC, repaginate, save, optional PDF. |

## Template surgery

`render_docx.py` locates the template's regions by marker paragraph (text + style), then edits
**bottom-up** so indices found before the first edit stay valid. Anything not listed in its plan is
untouched.

Two consequences worth remembering:

- **Keep the rendered heading, or alias its bookmark.** Where the template's own heading paragraph
  is retained and only the body replaced, the generated heading — and its bookmark — is discarded.
  `ALIAS_BOOKMARKS` re-attaches the bookmark names to the retained paragraph.
- **Retained text points at bookmarks in replaced clauses.** `UAPart3`, `_Ref85018491`,
  `_Ref16577438`, `_Ref127248897`, `_Ref55114991` all live in clauses the build regenerates.
  Re-attach them, or Word prints `Error! Reference source not found` inside template text.

## Determinism

The build must be byte-reproducible so a clean `git diff` proves the change was the intended one:

- ZIP entries are written with a fixed timestamp and fixed external attributes.
- Bookmark ids and relationship ids are allocated in document order from a fixed base.
- Generated `.pptx` files are normalised: fixed `dcterms:created` / `dcterms:modified`, empty
  `lastModifiedBy`, `revision` 1, fixed ZIP entry timestamps. Without this the embedded figure
  differs on every run.

Verify with two builds and a hash comparison.

## Onboarding another specification

1. Copy `word-drafts/tools/specs/openusd-binding.json`.
2. Point `source.markdown` and `source.nodeset` at the new draft.
3. Fill `identity`, `abbreviations` and `normativeReferences`.
4. Write the `clauseMap`: for each clause, its number, its template-capitalised title, the markdown
   heading it comes from, and — for a type clause — the `nodetable` BrowseName. A model with many
   types does not need one entry each: an entry with `"generated": "types"` and a `nodeClass` emits
   a subclause per Node of that class from the model, continuing the numbering from `numberFrom`
   and skipping anything the map already named. Set `"emitHeading": false` on such an entry when it
   continues a clause the map has already opened.
5. Write the `xrefMap` from the draft's current clause numbers to the new ones, and the `annexMap`
   for annex letters.
6. List `citedAs` — how sibling documents name this one — and `unanchoredSiblings` for any README
   beside it whose bare `§` references mean it.
7. List the `figures`.
8. Build, validate, mutation-test, finalise.

**How much of this is really config.** Each new *shape* cost a generalisation before its config
worked:

| Specification | New shape it forced |
|---|---|
| OpenUSD Part 1 | the pipeline itself |
| OpenUSD Part 2 | VariableTypes and ReferenceTypes clauses; no Security clause; annex regions and bookmark aliases had been hardcoded to Part 1's clause numbers; per-NodeClass type-clause generation |
| xRegistry | **Methods** — signature block, Table 20 arguments, Table 21 AddressSpace definition, and Method lookup disambiguated by owning type |
| Observability Export | Mermaid **classDiagram**; a lower-case-initial proper noun (`xRegistry`) in a heading |
| WoT Connectivity | **EventTypes** and **Instances** clauses; NodeClass *selection* (`select`) because an EventType is a `UAObjectType` and a deprecated legacy block has to follow the current types inside the same clause; a per-subclause deprecation NOTE; the `stateDiagram-v2` dialect; an instance table's `TypeDefinition` row |
| WoT Binding | **declared partial compliance** — no NodeSet at all: a null model, an Annex A that states the artifacts a document publishes when it publishes no NodeSet, and prose references spelled `Section 9.2` rather than `§9.2` |
| Schema Registry | a conformance clause with **no units at all** — the units had to be derived from the capabilities the clause describes in prose, not tokenised from an existing list |
| Generators | **RequiredModel BrowseNames**: a type borrowed from DI or Machinery is a bare NodeId in the NodeSet and there is nothing to resolve it against, so the names come from config; markdown that **links into the online reference** in body prose, which Guideline 5 forbids |
| Data Channels | **a document that owns no namespace** — its Nodes are additions to the base namespace, so `namespaceIndexInDocument` is 0, `IsNamespaceSubset` is True, and base names must print unprefixed; a Terms clause read from a *sibling* document (`termsFrom`); a Use cases clause **written in config** because the document has no material shaped like one |
| Avro and Arrow Encoding | **scale, and nothing else** — 121 and 106 clause-map entries, five heading levels deep. Both are the WoT Binding shape (`no-information-model`), and the only new mechanism either needed was a clause **authored in config**, because neither has a Use cases or a conformance clause of its own |
| The seven folded annexes | **more than one markdown source per document** — `additionalMarkdown` plus `"in"` on a clause-map entry, with sections keyed per source so a folded "1 Scope" does not collide with the base document's; and the class-diagram relations `..\|>` and `<\|..`, which only a worked example drew |

**How much of this is really config.** Eleven specifications have now been onboarded, and each new
*shape* cost a generalisation before its config worked.

Everything above is now driven by the docmodel and the config, and a twelfth specification of any of
those shapes is genuinely a config file. **Config carries what varies between documents of the same
shape; a new shape is code.**

## Not every draft is a companion specification

OPC 20020 is the *UA Companion Specification Template*. Before writing a config, read what the
document says it is. Three signals decide it, and the NodeSet settles the argument:

- **`ModelUri`.** A companion specification owns a namespace. Data Channels declares
  `http://opcfoundation.org/UA/` — the *base* namespace — because it proposes additions to
  OPC 10000-3, -4 and -6. That is core errata wearing a specification's clothes.
- **What the header claims.** "Proposed addition to OPC 10000-6" is not a companion
  specification, however complete the document is.
- **Whether an insertion clause exists.** A document ending in "Insertion into OPC 10000-4
  v1.05.07" is tracked-change text for an existing Part; it has no template shape at all and
  should not be converted.

A base-namespace document can still be rendered faithfully — Data Channels is — but only once the
generated Namespaces clause stops claiming to describe a namespace the document does not own.

## An annex is not a submission

The other way a draft fails the "is this a companion specification?" test is by being a **worked
example**: it shows an existing specification applied to DI, to Facets, to Pumps, to Robotics. The
signals are consistent — a provisional `Examples` namespace or an example URN, instances rather than
types, no conformance clause, and prose that only makes sense beside the document it illustrates.

Do not render it standalone. Its title page would claim it is a companion specification, and that
would be false. Do not drop it either — the content is real. **Fold it into the specification it
illustrates as an informative annex**, which is what it always was:

```jsonc
"additionalMarkdown": { "pumps": "metaverse-specs/.../OPC-UA-Pumps-...-Addendum.md" },
// then, on each clause-map entry drawn from it:
{ "id": "annex-g", "title": "Pumps", "in": "pumps", ... }
```

Sections are keyed per source, so the annex's own "1 Scope" does not collide with the base
document's. Two consequences catch people out:

- A reference from the annex **to its base specification is now internal** and must resolve through
  the clause map. References to anything else stay foreign. Both are checked, so getting it wrong
  fails the build rather than shipping a dead cross-reference.
- Figures come with it. `_detect_restructured` ignores entries carrying `in`, but the figure list
  does not: every diagram in the folded source needs an entry in `figures`, or the build writes
  `figure6.png` … `figureN.png` into the figures folder with the containing clause title as the
  caption. Count the diagrams in the source before rebuilding.

Record the fold in `batch.json` under `notAFit`, naming the document it folds into — "not a fit"
then reads as *published as what it is*, not *dropped*.

## The batch

`tools/specs/batch.json` records which specifications are converted, which the pipeline could take
next and what editorial work each of those still needs, and which are not a fit and why.
`tools/build_all.py` runs build, validate and mutation-test across the batch;
`build_all.py --list` prints the inventory. Finalising in Word stays separate, because it needs
Word and is not byte-deterministic.

## Declared partial compliance

The template admits no deviation, and for eight of the eleven documents none was needed. Three need
one, all for the same reason: WoT Binding defines a JSON-LD vocabulary and a NodeSet↔WoT mapping,
and the Avro and Arrow specifications define a wire format. None has a NodeSet, ObjectTypes or
Instances, so the NodeClass clauses and Annex A's NodeSet block have nothing to present.

The answer is not to relax the checker. It is to make a deviation **impossible to take quietly**:

1. the config declares it (`templateDeviations`, `id` drawn from `contract.KNOWN_DEVIATIONS`),
2. the build prints the declared statement into the document (clause 1.2),
3. the validator refuses a deviation it does not know, refuses one whose statement it cannot find in
   the produced document, and only then skips the checks that deviation names.

So the document is validated against a smaller contract that is *stated in the document itself*, and
anything undeclared still fails. Two consequences are easy to miss and both were real defects:

- Annex A's retained boilerplate says where to download the NodeSet. For a document that has none
  that text is false, so the whole annex body is replaced rather than retained.
- Clause 3.4's retained text promises that "Annex A defines the actual NodeIds". The two halves of
  that sentence are substituted separately, because the cross-reference field to Annex A sits
  between them and has to survive.
