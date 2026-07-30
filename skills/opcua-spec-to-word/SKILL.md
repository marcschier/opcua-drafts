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
   abbreviations, the clause map, the figure list. Adding a specification of the same *shape* is a
   config file; a genuinely new shape (Methods, EventTypes, Structures) needs a generalisation in
   `opcdocx/` first. See `reference/pipeline.md` for what onboarding Part 2 actually cost.

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
   (`finalize_word.ps1`, or `finalize_all.ps1` after a batch build — a rebuild always leaves the
   document unfinalised).
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
- **Migrate every call site, not just the builders.** Changing `Category` from one grouping label to
  per-node conformance units leaves coarse labels behind wherever a call passes the old constant
  explicitly, and generators also *branch* on the category string (`if n.category != "… Instances"`).
  `check_conformance_units` catches the leftovers, which is what it is for.
- **A conformance unit needs an identifier, not a prose name.** Specifications often name their
  units in prose ("Binding Grouping", "Scene Structure"). A `Category` element and a Word table row
  need a token: prefix the specification's short name (`OBS-BindingGrouping`, `OUS-SceneStructure`,
  `XREG-Registry`). Give the specification's conformance clause the same identifiers, or
  `check_conformance_units` will fail — correctly.
- **A proper noun may start lower-case.** `xRegistry`, `xformOp`, `usdview`. Guideline 2 exempts
  proper nouns and type names from the initial capital, so a naive "headings start with a capital"
  check produces false errors.
- **The same Method name appears on several types.** `Delete` on both `GroupType` and
  `ResourceType`, `AddAttribute` on every container. Look a Method up by name *and owning type*, or
  the document silently documents whichever was declared first.
- **Running the full validation suite regenerates other specifications' artifacts.** The Avro
  encoding validators derive schemas from other specs' NodeSets, so changing one model leaves
  unrelated files modified in the working tree. Check `git status` for changes outside your scope
  and revert them; they belong in their own change.
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
- **A generator named after the first specification will be reused by the next one.** A generator
  called `intro-openusd` produced clause 4.1 for every document, so the xRegistry and Observability
  Export drafts each shipped three paragraphs introducing *OpenUSD* under a heading that promised
  their own subject. Nothing failed: styles, fields and numbering were all correct. Put per-document
  prose in the config, and check that clause 4.1 actually names the document's subject.
- **A reference to another document must not be renumbered.** `OPC 10000-6 Section 5.1.1` and
  `the Bindings spec §7.4.2` belong to those documents; resolving them through this document's
  clause map produces a confident, wrong cross-reference. Match a qualifier in a *bounded window*
  before the reference — and strip markdown link targets first, because one
  `reference.opcfoundation.org` URL is long enough on its own to push `OPC 10000-3` out of the
  window. Nicknames (`the primer`, `the Bindings spec`) are per-document, so keep them in config.
- **A reference that resolves to nothing is worse than one that fails loudly.** It is printed as
  plain text carrying the source document's own numbering, which after restructuring is simply a
  wrong number, and no style or field check notices. Fail the build on an unresolved internal
  section reference.
- **Not every draft writes `§`.** `Section 9.2`, `Sections 9.2 and 10.1`, `Sections 5, 6, and 10`
  are references too. Every number in the list is one; rewriting only the first leaves the rest
  pointing at the old numbering.
- **An old clause number may collide with a new one.** In an unrestructured document, resolving a
  reference directly before consulting the clause map sends `Section 5` to whatever clause 5 has
  *become* instead of to what clause 5 *was*. Decide which numbering the markdown carries, then
  resolve in that order.
- **An unparsed diagram construct became a node.** `A -- label --> B` and `-.->|label|` were not in
  the edge splitter, so the edge text was taken for a node id and drawn as a box. Make an
  unrecognised endpoint an error; a diagram that renders nonsense is worse than one that fails.
- **Mermaid subgraphs nest, and clusters must stay contiguous.** Layer the clusters first and the
  nodes inside each cluster second, or two subgraphs interleave, their frames overlap, and whatever
  pushes them apart makes the canvas metres wide. A node inside a *nested* subgraph is inside its
  parent's frame too.
- **A cyclic diagram diverges under longest-path layering.** A state machine legitimately loops;
  drop cycle-closing back edges from the layering (still drawing them) or the canvas grows by one
  layer per iteration until the guard trips.
- **An edge label is occluded by whatever is drawn after it.** Place labels clear of the node boxes
  *and* of each other, and include them in the canvas extents — otherwise the figure needs the
  manual repair the pipeline exists to avoid. The editable PowerPoint needs the labels too; drawing
  them only in the preview bitmap hands an editor a diagram whose edges say nothing.
- **A mutation test that hard-codes one document's names is not a test.** Reusing OpenUSD type and
  unit names made the suite report "the test itself is broken" for every other specification.
  Derive each mutation from the document under test, and *skip* with a reason where a mutation
  cannot apply. Anchor a node-table mutation on the member's BrowseName **and** its printed
  DataType: the BrowseName alone also matches the template's own example tables, so the mutation
  lands somewhere the check never looks and proves nothing.
- **Inline markup nested inside bold, italic or a link label leaks.** A bolded span containing a
  code span, and a link whose label is a code span, are ordinary prose in these drafts:

  ```text
  **the `EngineType` component**        [`WoTRegistryType`](#type-WoTRegistryType)
  ```

  Emitting the span as one plain run put literal backticks and link brackets into *every* document
  built before this was found — well formed, correctly styled, and wrong. Parse the content
  recursively and carry the emphasis down onto the text runs.
- **A BrowseName the model cannot resolve is printed as a NodeId.** A type borrowed from a
  RequiredModel (`ns=2;i=15063`) or a base Node missing from the table of standard Nodes falls
  through to its numeric form, and the document still agrees with the NodeSet because both sides
  carry the same unreadable string. Only a check on the *printed* form catches it; twenty of them
  had reached print. The names cannot be guessed — take them from the generator that wrote the
  NodeSet, which names every one of them as a constant.
- **A conformance clause may name no units at all.** Two specifications described their
  capabilities only in prose. Units then have to be *derived* from what the clause distinguishes,
  written into the clause as a table, and assigned per node — inventing them from the model's
  grouping labels alone produces units that no reader can claim.
- **A draft may hyperlink the online reference in body prose.** Guideline 5 forbids that outside
  Annex A. The citation is what matters, so the link is dropped and its label kept; that is a
  transformation the pipeline can make on its own rather than an edit to the source.
- **Generated boilerplate makes claims, and a claim can be false.** The Namespaces clause stated
  `IsNamespaceSubset = False` and "the UANodeSet XML file contains the complete namespace", and
  `StaticNumericNodeIdRange = 1001:9999`. Both were true of the first specification converted and
  neither is a property of the template — the range was wrong for six of eight documents, and the
  subset flag is *false* for any document that adds Nodes to a namespace it does not own. Derive
  what can be derived from the model; put the rest in config.
- **A qualifier governs the rest of its sentence, not the next few characters.** "The Part 6
  errata §5.13 gives the full transition table … and §5.14 names the four timeouts" cites one
  document twice; a window that stopped at the first section sign, or at a character count,
  called the second reference an internal one. Bound the window by the sentence — a period
  followed by whitespace, which is not the period inside §5.13.
- **An EventType may leave the model before reaching BaseEventType.** `AuditOpenDataChannelEventType`
  derives from `AuditSessionEventType`, which is a base-namespace type the NodeSet does not
  describe, so walking the supertype chain gives up and the type is filed under ObjectTypes.
  The base event types have to be named explicitly; nothing in the file says they are events.
- **A clause title is plain text, so strip the markup out of it.** A heading written
  ``### 6.3 Bare RecordBatch framing (`batch`)`` yields a title with backticks in it, and an
  annex heading written `### D.1 Boolean` yields one with a literal clause number — which the
  numbering check rejects, correctly, because Word supplies the number.
- **Change tracking has to be armed in the package, after Word.** The template ships without
  `w:trackChanges`, so the build writes it into `word/settings.xml` — but Word rewrites that
  part from its own state whenever it actually changes the document, and drops the element.
  Going through the COM property is worse, not better: setting `Document.TrackRevisions` to
  false *removes* the element, setting it back to true does not restore it, and in this
  environment Word does not write the element even for a document it created itself with
  tracking on. So: the build writes it, the finalise pass leaves `TrackRevisions` alone, and
  `arm_track_changes.py` re-inserts it once Word has closed the file. The guarantee is the
  file content, which the validator checks — not a Word round-trip.
- **Arming tracking and then editing records your own edits.** If the finalise pass ran with
  tracking active, five hundred field updates would ship as five hundred revisions, in a
  document that still validates and still looks right. The check that no `w:ins`, `w:del`,
  `w:moveFrom` or `w:moveTo` exists is what makes that impossible to miss; write it before
  trusting the arming.
- **A worked example is an annex of the specification it illustrates, not a submission of its
  own.** Seven drafts here each apply an existing specification to one domain — provisional
  `Examples` namespace, instances not types, no conformance clause. Rendering one standalone
  puts a false claim on its title page; dropping it loses real content. Fold it in with
  `additionalMarkdown` plus `"in"` on the clause-map entries. Then remember the two things that
  come with it: a reference back to the base specification becomes *internal* and must resolve
  through the clause map, and **every diagram in the folded source needs a `figures` entry** —
  otherwise the build silently writes `figure6.png` … `figureN.png` with the containing clause
  title as the caption. Count the diagrams first.
- **A build un-finalises the document, and a batch build un-finalises all of them.** The build
  writes fields, not field *results*, so a freshly built document opens with an **empty table of
  contents and blank cross-references**. Nothing catches it: the package is well formed, the
  styles are right, every other check passes, and the file is simply not finished. Seven of
  eleven documents were committed in that state here, because they had been rebuilt for an
  unrelated change and only the documents whose *content* changed were re-finalised. The rule is
  that `build_all.py` is always followed by `finalize_all.ps1`, and the check that makes it
  visible is a populated `TOC` — one cached `PAGEREF` per entry, absent in a fresh build.

## Verification checklist

- [ ] `validate_docx.py` reports 0 errors.
- [ ] Change tracking is armed and the document carries no revisions of its own.
- [ ] `test_validate_docx.py` reports 0 escaped mutations, and every skip has a real reason.
- [ ] `build_docx.py` reports no unresolved internal section references.
- [ ] `check_section_refs.py` is clean for the documents you touched.
- [ ] Two consecutive builds are byte-identical.
- [ ] `finalize_word.ps1` reports *all fields resolved*.
- [ ] **Every** document is finalised, not just the ones you changed:
      `finalize_all.ps1 -VerifyOnly` is clean.
- [ ] The `.docx` opens, the table of contents is populated, figures render, and no field shows an
      error.
- [ ] Any `templateDeviations` are declared, printed in the document, and are the *only* checks
      relaxed.
