---
name: opcua-spec-to-word
description: >-
  Convert a markdown OPC UA specification draft into a submission-ready Microsoft Word
  document that adheres to the official OPC Foundation companion specification template
  (OPC 20020), with no manual editing afterwards. Clones the template package so styles,
  numbering, headers and embedded figures survive byte-for-byte; generates the normative
  node tables from the UANodeSet so the document cannot drift from the model; rebuilds
  Mermaid diagrams as embedded PowerPoint objects because the template forbids inline
  drawings; leaves all numbering to Word fields; and validates the result against a
  machine-readable template contract. WHEN: turn a spec into Word, produce a .docx for
  OPC Foundation submission, apply the OPC UA companion spec template, restructure a
  draft into the mandated clause skeleton, generate OPC UA type-definition tables.
---

# OPC UA specification → OPC Foundation Word template

The OPC Foundation accepts companion specifications as Word documents built on
**OPC 20020 — UA Companion Specification Template**. The template is not a style sheet: it
mandates a clause skeleton, a machine-parseable table grammar that the Foundation's own
Word-versus-NodeSet validator reads, and a set of editing guidelines with hard prohibitions.

This skill converts a markdown draft into that document **deterministically**, so the result
needs no manual editing and can be rebuilt from source at any time.

## When to use

Use it when a markdown specification in this repository has to become a `.docx` for review or
submission, when an existing Word draft has to be regenerated after a model change, or when a
draft has to be restructured into the template's clause skeleton.

Do **not** use it to hand-edit a `.docx`. Editing the generated file breaks the single source of
truth exactly the way hand-editing a generated NodeSet does.

## The five things that make this hard

1. **Word owns the numbering.** `Heading1`–`Heading5` and `ANNEXtitle`/`ANNEX-heading*` carry an
   automatic clause number from `word/numbering.xml`. Writing `## 5.15 Asset delivery` into a
   heading produces *"7.11 5.15 Asset delivery"*. Emit the title only; cross-reference with a
   `REF` field over a bookmark and let Word print the number.
2. **The node tables are parsed by a tool, not just read.** Generate them from the UANodeSet.
3. **Figures must be embedded document objects.** Guideline 1 forbids inline Word drawing objects
   — a rendered PNG is not conforming. Rebuild the diagram as a real PowerPoint file and embed it
   as an OLE object with a preview image.
4. **Most of the document is the template's own text.** Clone the template and replace only what
   you own. Regenerating boilerplate is how a document stops matching the template.
5. **Restructuring renumbers everything.** Every `§` reference in the document *and in every
   sibling document that cites it* has to move with it, behind a gate that fails on a stale one.

## Read first

- `reference/template-contract.md` — the machine-readable contract: style allow-list, numbering
  wiring, the six table grammars, the retained regions, the prohibitions, the document properties.
- `reference/pipeline.md` — the tool layout, the extension points, and how to onboard a new
  specification.

## Inputs

1. The **markdown draft** — the prose.
2. The **UANodeSet** — the authority for every type table and every conformance unit.
3. A **build config** (`word-drafts/tools/specs/<spec>.json`) — identity, normative references,
   abbreviations, the clause map, the figure list. Adding a specification is a config file, not code.

## Outputs

1. The **`.docx`**, committed.
2. The **`.docmodel.json`** intermediate representation, committed — a `.docx` diff is unreadable,
   so review the IR instead.
3. The **`figures/*.pptx`** sources of the embedded objects.
4. A **restructured markdown source** in the same clause order, so the two cannot drift.

## Procedure

1. **Read the template contract.** Never assume; unpack the template and check. A `.docx` is a ZIP
   of XML: `word/document.xml`, `word/styles.xml`, `word/numbering.xml`, `docProps/custom.xml`.
2. **Write the clause map** in the build config: for each clause, its number, its title in template
   capitalisation, and the markdown heading it comes from. Include an `xrefMap` from old clause
   numbers to new ones. This single map drives both the Word build and the markdown restructure.
3. **Make the model carry its conformance units.** OPC 20020 3.4.1.1 requires every Type Node and
   well-known Instance Node to name the ConformanceUnits that require it, as `Category` elements in
   the UANodeSet. If the generator does not emit them, the node tables cannot be produced. Edit the
   generator, never the generated file, and bump `Version`/`PublicationDate` everywhere they are
   stated.
4. **Restructure the markdown** (`restructure_markdown.py`), then rewrite `§` references in every
   sibling document, then run `check_section_refs.py` until it is clean.
5. **Build** (`build_docx.py`), **validate** (`validate_docx.py`), **finalise** with Word COM
   (`finalize_word.ps1`).
6. **Prove the build is deterministic** — build twice and compare hashes.
7. **Mutation-test the validator** (`test_validate_docx.py`). A checker that passes trivially is
   worthless.

## Traps found the hard way

- **An embedded OPC package needs the `package` relationship type, not `oleObject`.** A `.pptx`,
  `.xlsx`, `.vsdx` or `.sldx` wired as `.../relationships/oleObject` looks correct, opens fine, and
  is **silently discarded by Word on the next save**, leaving only the preview picture — the exact
  thing Guideline 1 forbids. Only compound-file embeddings (`.bin`, `.vsd`) use `oleObject`. The
  symptom is that `Document.InlineShapes` reports the figure as a picture (type 3) instead of an
  embedded object (type 1). Check it that way; the XML alone will not tell you.
- **`Category` elements are not conformance units by default.** A model may carry coarse grouping
  labels there. The template expects the ConformanceUnit names; grep the NodeSet before assuming.
- **Bookmarks die with the clause you replace.** Retained template text points at bookmarks such as
  `UAPart3`, `_Ref85018491` and `_Ref16577438` that live in clauses the build regenerates. Re-attach
  those names to the new equivalents, or Word prints *"Error! Reference source not found"* inside
  template text you never touched.
- **Word splits a token across runs** whenever it carries mixed formatting. Substitute per run
  first, and only collapse a paragraph into its first run when a token genuinely spans runs —
  collapsing unconditionally destroys line breaks in the annex titles.
- **A `.pptx` carries timestamps** in `docProps/core.xml` and in every ZIP entry header. Normalise
  them or the build is not reproducible and a clean diff proves nothing.
- **A sentence-final period defeats a naive reference rewrite.** `§5.15.` must still match `5.15`;
  use a lookahead that blocks a longer *number*, not any dot.
- **Guideline 5 has an exception.** Links into `reference.opcfoundation.org` are forbidden — except
  in Annex A, where the template itself mandates the NodeSet download URLs.
- **Delete the EDITING Guidelines clause.** The template says to, and Word renumbers automatically.
- **Drop clauses the model has no content for** rather than shipping them empty.
- **Repo-internal prose does not belong in a submission.** Paths, build commands and links to a
  `CHANGELOG.md` are for contributors, not for the standards body.

## Verification checklist

- [ ] `validate_docx.py` reports 0 errors.
- [ ] `test_validate_docx.py` reports 0 escaped mutations.
- [ ] `check_section_refs.py` is clean for the documents you touched.
- [ ] Two consecutive builds are byte-identical.
- [ ] `finalize_word.ps1` reports *all fields resolved*.
- [ ] The `.docx` opens, the table of contents is populated, figures render, and no field shows an
      error.
