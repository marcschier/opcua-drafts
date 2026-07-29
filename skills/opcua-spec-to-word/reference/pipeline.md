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

**How much of this is really config.** Part 2 was onboarded to test the claim. Its config was
written from scratch, but four generalisations to `opcdocx/` were needed first, because Part 1 had
never exercised them:

- the renderer hardcoded *ObjectTypes + DataTypes*; Part 2 has VariableTypes and ReferenceTypes;
- `Security` was assumed to exist as a clause after Namespaces; Part 2 has none;
- the annex regions were hardcoded `annex-b` … `annex-f`;
- the retained-heading bookmark aliases hardcoded Part 1's clause numbers (its Profiles clause is
  9, Part 2's is 11).

All four are now driven by the docmodel and the config. Expect the *first* specification with a
genuinely new shape — Methods, EventTypes, Structures with optional fields — to need a similar
round. The config carries what varies between documents of the same shape; a new shape is code.
