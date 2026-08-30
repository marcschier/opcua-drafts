---
name: opcua-word-to-markdown
description: >-
  Migrate an existing Word-authored OPC UA companion specification into this repository, whose
  source of truth is markdown plus a UANodeSet. Covers producing the reference STS from the
  .docx, filling in manifest.json and profiles.json, rewriting clauses into the markdown
  dialect, splitting a large document across several markdown files, carrying figures across as
  Office sources wired to a generator, and proving by diff that nothing was lost. WHEN: the user
  has a
  .docx (or an STS XML converted from one) and a mostly empty repository created from the
  specification template, and asks to migrate, port, convert or bring it in.
---

<!-- Written by `Opc.Ua.SpecificationPublisher upgrade`, which refreshes it when a new version
     of the tool ships a new copy. Edit it and it becomes yours; delete it and run
     `upgrade --write` to take the current copy back. -->

# Migrating a Word specification into this repository

Read `AUTHORING.md` first — it is the dialect this migration targets, and this skill assumes it.

**Most of this migration is judgement, not transformation.** There is no `.docx → markdown`
converter and no `STS → markdown` emitter; do not go looking for one and do not tell the user
you will write one. What tooling exists produces the **reference artifact** and **checks your
work**. The restructuring in between is yours.

That division is the whole method:

```
  .docx ──[ tool ]──► STS XML  ← the reference. Ground truth. Never edited.
                        │
                        │  ← you read this and write markdown. This is the work.
                        ▼
  source/<spec>/*.md + manifest.json + profiles.json + model/
                        │
                        └──[ tool ]──► STS XML  ──[ diff ]──► what you have not carried yet
```

The claim being made is that nothing was lost. That claim is checkable, so check it — do not
eyeball the two documents.

## What is deterministic, and what is not

| | |
|---|---|
| **Tool** | `.docx` → reference STS; markdown → STS; STS → HTML and `.docx` renderings; anchor renaming and namespace-index assignment (`update --write`); clauses 2 and 3, Profiles, Namespaces, Annex A and every `NodeIds.csv` — **generated, never migrated** |
| **You** | deciding what is authored vs generated; unnumbering headings and inventing anchors; node tables into the table shape with `defines=`; cross-references into their two forms; conformance units out of prose into `profiles.json`; identity and normative references into `manifest.json`; exporting each figure's Office source and wiring its generator; repairing broken emphasis |

Figures sit across the line: exporting the drawing and wiring `figureGenerators` is yours, and
producing the `.svg` from it is then deterministic — `update --write` runs the generator. See
step 6.

If a step feels mechanical enough to script, it is still cheaper to do it a clause at a time and
let `build` tell you when it is wrong.

## Step 1 — the reference STS

`Opc.Ua.SpecificationValidator` converts the Word document. It is **Windows-only** and drives
Word, Visio, PowerPoint and Excel through COM, so it is a separate package from the publisher and
the user must run it on a Windows machine with Office installed. If they are on Linux or macOS,
say so plainly and ask them for the STS XML instead — the migration works fine from that alone,
and everything after this step is cross-platform.

```
dotnet tool install --global OPCFoundation.Opc.Ua.SpecificationValidator

Opc.Ua.SpecificationValidator convert-validate <input.docx> _work/reference/ \
    --nodeset model/Opc.Ua.<Subject>.NodeSet2.xml \
    --images
```

`convert-validate` runs `preprocess` (Word → `clean.docx` in a work directory) and then `convert`,
and validates the result against the NodeSet. Run the two separately if you need to inspect the
intermediate:

```
Opc.Ua.SpecificationValidator preprocess <input.docx> _work/prep/
Opc.Ua.SpecificationValidator convert     _work/prep/ _work/reference/ --nodeset <primary.xml>
```

Put it under `_work/`, which is gitignored. **The reference STS is not committed and is never
edited.** It is evidence, not source. A migration that edits it to make the diff pass has proved
nothing.

The validation findings alongside it are worth reading before you write a line of markdown: they
tell you where the Word document and the model already disagreed. You are migrating a document,
not fixing it — carry those disagreements across as they are and report them to the user
separately. Silently correcting the specification during a format migration is how a diff stops
meaning anything.

## Step 2 — the model

Copy the NodeSet into `model/` and name it from `manifest.json`, relative to the repository. Then:

```
Opc.Ua.SpecificationPublisher fetch-dependencies
```

Commit what it downloads. Do this before writing prose: nearly every node table you write is
checked against the model, and without it every check is vacuous.

## Step 3 — identity: manifest.json, the cover, and the Agreement of Use

Fill it from the Word document's front matter and the reference STS, not from memory.

| Field | Where it comes from |
|---|---|
| `identity.*` | the document's cover and title page |
| `normativeReferences` | clause 2 of the Word document — **then delete clause 2 from the prose** |
| `abbreviations` | clause 3.3 — then delete it from the prose |
| `terms` | clause 3.2 — then delete it from the prose |
| `namespaces.table` | the document's namespace table, **not** the NodeSet's ordering |

The namespace indices are the *document's*. The NodeSet's own ordering is different, and using it
silently mislabels every BrowseName in every generated node table. Add each URI with
`"index": null` and let `update --write` number them, then read the diff.

### Check the repository is named correctly, and say so if it is not

Once you know the document number, check the name of the directory you are working in. A
specification repository is `<number>-<short name>` — `OPC40001-Machinery`,
`OPC40750-BatteryProduction`, `OPC30080-FDI` — no space after `OPC`, no dots, short name in
PascalCase. Where the repository holds several parts, both halves name the **series**: a
repository publishing OPC 40700, 40701 and 40702 is `OPC40700-SurfaceTechnology`, taking the
lowest number and the series title, not the name of whichever part is being migrated first.

You cannot rename it yourself and should not try. Tell the user, once, early — renaming after
anyone has linked to the repository or its published site means fixing every one of those links.

### The partner organisation

A published OPC specification is often a joint work, and the template cannot know with whom. Do
not extract the partner's name or logo from the Word master by hand — that used to be the
procedure and is not any more. `upgrade --write` downloads `source/agreement-of-use.md` and the
cover logos from the OPC Foundation's shared repository of partner agreements, keyed by the
`Partner organization:` line in `legal.md` at the repository root, and overwrites whatever is on
disk every time it runs. Set that line to the partner's name — matching a folder in that shared
repository, such as `VDMA` or `VDW` — and run `upgrade --write`; leave it blank for the Foundation
publishing alone. Read `legal.md` itself before touching any of this, it explains what gets
fetched and why editing the fetched files directly accomplishes nothing.

If the Word master names a partner this migration should carry forward, tell the working group to
set `legal.md` and run `upgrade --write` — do not hand-copy the name or the logo out of the
document yourself.

### The issue-tracking URL

`identity.mantisUrl` in the manifest still names this specification's issue tracker:

```json
  "identity": { "mantisUrl": "https://mantis.opcfoundation.org/set_project.php?project_id=NNN" }
```

but the Agreement of Use fetched by `upgrade --write` has nowhere left in it to carry that link -
the shared repository's copy carries no `<mantisUrl>` placeholder to substitute into, unlike the
Word master this migration is reading from. Set `mantisUrl` in the manifest regardless; where the
per-specification link surfaces instead is not decided yet.

### Errata links

Older Agreements of Use carry a link to an errata page. **Drop it.** It is not part of the
current text, it is not something the working group is choosing to omit, and it should not appear
in the list of what you could not carry — it is simply gone from the document the Foundation
publishes now.

## Step 4 — delete the generated clauses

This is the step that is skipped and should not be. In the Word document these clauses are prose;
here they are generated, and a migrated copy of one is a second copy that nothing keeps in step.

Delete from the prose entirely:

- clause 2, Normative references → `manifest.json`
- clause 3.2 Terms, 3.3 Abbreviations → `manifest.json`
- clause 3.1 Overview → the OPC 20020 template, built in
- clause 3.4 Conventions used in this document → **OPC 10000-3**. Not migrated and not
  generated: the text moved there, so delete it and leave the normative reference to do the work
- Profiles and Conformance Units → `profiles.json`
- Namespaces, Annex A → generated from the manifest and the model
- **"Introduction to OPC Unified Architecture"** → boilerplate repeated in every companion
  specification. It is not migrated. It also carries figures that have no source, which is the
  usual reason a migration stalls here.

What is left is clause 1 Scope, the domain prose, the use cases, the information-model overview
and the per-type clauses. That is the whole of what you write.

Ask for the generated ones back where they belong, with a directive:

````markdown
```{clause}
kind: profiles
```
````

## Step 5 — the prose, one clause at a time

Do **not** convert the whole document and then try to build. Get clause 1 and a single ObjectType
through `build` cleanly first; the errors you hit on the first type are the errors you would have
hit sixty times.

### Plan the file layout before you convert

A companion specification is routinely a few hundred pages, and pouring all of it into one
`spec.md` produces a file nobody can work in — a reviewer's diff is unreadable, an editor's search
returns forty hits per type, and an agent asked to change one clause has to hold the whole
document to do it.

**Aim for under ~1000 lines per markdown file, and treat ~2000 as the outer edge.** It is a
guideline, not a limit the tool enforces: do not split a clause that belongs together to get
under a number, and do not leave a 4000-line file alone because splitting it is awkward.

Decide the split **before** converting prose. Doing it afterwards means moving the same text
twice.

The mechanism is an `{include}` directive naming a key in the manifest's `markdown` block:

````markdown
```{include objecttypes}
```
````

```json
  "markdown": {
    "main": "spec.md",
    "objecttypes": "object-types.md",
    "statemachines": "state-machines.md",
    "annex-b": "annex-b-profiles.md",
    "figures": "figures"
  }
```

Everything in the named file — **headings and all** — takes the place of the directive, at the
heading levels it was written with. Breaking prose out is a move and nothing else: same text,
same place in the document, same numbering. It is still one document. Anchors declared in one
file are cited from another, `update` reads and rewrites them together, and a citation is never
reported as dangling because of which file it happens to be in.

Because the part carries its own headings, a file can hold **several clauses**, which is the
answer for a run of small related clauses none of which justifies a file alone. Where you put
the include decides the depth: a file opening at `##` read in at the top of the document is a run
of clauses; one opening at `###` read in under a `##` heading is that clause's subclauses.
Skipping a level is reported.

**The procedure is: measure, break out the largest, repeat.**

1. Count the lines in each file.
2. Take the **largest top-level clause or annex** in the file that is over target and give it a
   file of its own.
3. Re-measure and repeat until everything is under target, or until what is left is one clause
   that cannot be divided further without cutting into the middle of it.

Break on a **top-level clause or an annex**, not mid-clause. A file that starts partway through
somebody's argument is worse than a long one.

Almost always the first break is the ObjectTypes clause, which is most of the document and the
only clause anyone will edit again. Annexes are the next candidates — they are self-contained by
construction, which is what makes them cheap to move.

**A broken-out file can break out its own prose in turn.** That is the answer for an ObjectTypes
clause that is still 5000 lines after the first split: give each group of types its own file and
put an `{include}` for each inside `object-types.md`. Nesting is read recursively, and a file that
includes itself — directly or through another — is reported rather than read until the stack runs
out.

Name the key after the clause and the file after the key, so the manifest reads as a table of
contents. Two failures are reported plainly if you get it wrong: an include the manifest names no
file for, and one naming a file that does not exist.

Working from the reference STS rather than the `.docx` is easier — it is structured XML, the
tables are already `table-wrap` elements, and the cross-references are already `xref`s.

- **Headings lose their numbers.** `## 5 Use cases` becomes `## Use cases {#sec-use-cases}`.
  Numbering comes from document order. Every heading needs an anchor, because that is what
  cross-references bind to.
- **Node tables are authored, and bound.** Keep the table; add `defines=<TypeName>` to its
  caption. Column spans become one cell followed by empty ones. The attribute block, the
  References grid and the Conformance Units block stay under one caption, separated by blank
  lines. Do not give them separate captions.
- **Cross-references take one of two forms.** `[](#tbl-...)` where the label is a derived number,
  `[OPC 10000-5](#ref-uapart5)` where it is a standard's stable designation. A migrated
  "see Table 15" must become the first form — the frozen number is the defect being removed.
- **Conformance units move to `profiles.json`.** They are data in four places at once, and the
  Word document's Profiles clause is one rendering of them.
- **Repair broken emphasis.** `*Nodes *and` and `the* optional Nodes *under` render a literal
  asterisk and drop the term from the index. They are endemic in Word-converted text, invisible
  in a parity check because the asterisk count is even either way, and there are usually dozens.
- **One paragraph per line.** Do not hard-wrap. Word exports often arrive wrapped; unwrap them.

As each clause lands, check it against the layout you planned above — a clause that turns out
much larger converted than it looked in Word is the signal to break it out now rather than at
the end.

## Step 6 — figures

**Do not redraw the figures during the migration.** Carry them across as the Office files they
already are, wire them up, and let the working group redraw them afterwards as a separate piece
of work. Redrawing sixty diagrams is not a format migration, and bundling the two means the diff
in step 7 can no longer tell you whether the *document* survived.

The only requirement on a figure is that it is an **SVG**. Where that SVG comes from is the
working group's business, and for a migration it comes from the original drawing.

### Export each figure as the file it really is

A Word master embeds its figures as OLE objects. Save each one out as its true format — a Visio
drawing as `.vsdx`, a PowerPoint slide as `.pptx` — into that specification's figures directory,
named for the anchor its directive will use:

```
source/<spec>/figures/fig-information-model-overview.vsdx
```

That file stays the figure's source of truth until somebody redraws it. It is **committed**, not
scratch. A raster the converter exported is not a substitute: it is the picture with the drawing
thrown away, and nobody can correct it afterwards.

### Wire the generator

In that specification's `manifest.json`:

```json
  "figureGenerators": {
    ".drawio.svg": "",
    ".vsdx": { "win": "tools/office-to-svg.ps1", "default": "tools/office-to-svg.sh" },
    ".pptx": { "win": "tools/office-to-svg.ps1", "default": "tools/office-to-svg.sh" }
  }
```

Both scripts come from the tool — `upgrade` writes `tools/office-to-svg.ps1` and
`tools/office-to-svg.sh` and keeps them current, so there is nothing to fetch. Where every
author is on Windows, name the `.ps1` on its own as a plain string
(`".vsdx": "tools/office-to-svg.ps1"`) and leave the `.sh` out — the object form is for a group
whose authors are not all on one platform, and it exists because Visio renders a figure on
Windows and LibreOffice renders it everywhere else. Ask which case this working group is in
rather than assuming; it is not something to infer from the machine you are running on.

Keep the `.drawio.svg` line with its empty script even when nothing uses it yet — an empty
generator means "this source already is the figure", and the block is what says which kinds of
figure source this repository has.

### Render, and commit both

```
Opc.Ua.SpecificationPublisher update           # lists what it would run
Opc.Ua.SpecificationPublisher update --write   # runs each generator
```

`update` calls the script as `<script> <source> <svg>` from the repository root and writes the
`.svg` beside the source. It compares the bytes, so a figure that regenerates identically says so
rather than showing up as a change. Commit the source and the `.svg` **together**.

A `build` never runs a generator — it reads the committed `.svg` and executes nothing. That is
deliberate: rendering a Visio drawing needs Visio, and a build that shelled out to it would
succeed on the author's machine and fail in CI, or quietly produce something different.

The figure directive names the **`.svg`**, not the source:

````markdown
```{figure}
id: fig-information-model-overview
caption: Information Model overview
source: figures/fig-information-model-overview.svg
```
````

### What the shipped generator does and does not do

`tools/office-to-svg.ps1` drives Visio and PowerPoint through COM, so it needs **Windows with
those applications installed** — the same constraint as step 1, and the same application that
drew the diagram writes the SVG, which is the highest-fidelity path available.

- Visio: exports the **first page only**, and warns when there are more.
- PowerPoint: exports the **shape range of the first slide**, not the slide — a slide exports as
  the diagram adrift in a 16:9 field of whitespace, and the figure is the drawing.
- It refuses any other extension rather than guessing.

It is not the only possible generator and the tool knows nothing about it. On Linux or macOS,
write one that shells out to LibreOffice — `soffice --headless --convert-to svg` handles both
formats — and name that in the manifest instead. The contract is only `<script> <source> <svg>`.

### This is the workflow afterwards, not a waypoint

Once wired, the Office file **is** the figure's source of truth and stays that way. The authoring
loop is:

```
edit fig-....vsdx in Visio  ->  update --write  ->  commit the .vsdx and the .svg together
```

Nothing about that is provisional. A working group can publish from Office sources indefinitely,
and the specification is complete and correct while it does. Do not describe it to the user as
technical debt, and do not schedule its removal.

What the group gives up is **checking**. An Office-exported SVG is a picture: it renders, it goes
in the document, and it is opaque, exactly like a `.png`. Nothing can compare its shapes and
arrowheads against the model, because there is no diagram inside it to read. That is the defect
that hides here: the diagram showed the types the model had on the day it was drawn, and nothing
can tell when the model moves on.

Moving to a checkable figure is a **later, optional decision the author makes**, and
`.drawio.svg` is one way to take it — the picture and its editable diagram in one file, with the
shapes dragged out of the OPC UA palette, `source/figures/uashapes-library.drawio.xml`, which is
a draw.io shape library the tool ships and `upgrade` keeps current. It is not the only way. The generator
contract is `<script> <source> <svg>` and nothing in the tool knows what is on the other end, so
a group can move to PlantUML, Graphviz, a Python renderer, or anything else that emits SVG.
Changing is one line in `figureGenerators` and the new source committed beside it.

State the trade-off once, when you hand over: which figures depict the address space and are
therefore unchecked while they stay Office-sourced. Then leave it. It is the working group's
call, and it is not part of this migration.

Two kinds of figure never need to move at all:

- **photographs, screenshots and artwork from elsewhere** — a `.png` or plain `.svg` is the right
  answer and is accepted without argument;
- **diagrams that depict no address space** — workflows, state machines, conceptual overviews.
  Mark them `freeform: true`, which states the intent for the next reader and exempts them.

## Step 7 — prove it

```
Opc.Ua.SpecificationPublisher update --write     # anchors, namespace indices; read the diff
Opc.Ua.SpecificationPublisher build              # markdown + NodeSet -> STS
Opc.Ua.SpecificationPublisher publish            # render it and actually read it
```

Then diff the STS you built against the reference from step 1. **A non-empty diff is the exact
list of what the markdown does not yet carry** — that is what it is for, so work it down rather
than explaining it away.

Expect and accept these differences, and say which ones you are relying on:

- clause numbering, where a generated clause now sits in a different place;
- the generated clauses themselves, which are now built from the manifest rather than copied;
- the omitted "Introduction to OPC Unified Architecture";
- figure references, where a regenerated figure has a new file name;
- the Agreement of Use, where a hard-coded tracker address became `<mantisUrl>` and is
  substituted back, and where an errata link was dropped.

Anything else is something you dropped.

Do not report the migration as done on a green `build`. `build` fails on what cannot be carried
into the STS; it does not know what the Word document said. The diff is the check, and reading
the rendered `publish` output is what catches prose that survived structurally but reads as
nonsense.

## Working with the user

- **Migrate one specification at a time**, even when the repository will hold several.
- **Never edit the reference STS**, and never regenerate it to make a diff smaller.
- **Do not fix the specification while migrating it.** Errors, disagreements with the model,
  missing types — carry them across unchanged and hand the user a list. A migration and a
  correction in one commit cannot be reviewed.
- **Report what you could not carry**, rather than quietly leaving it out. A clause you skipped
  because its figures had no source is the user's decision to make, not yours.
- If the `.docx` cannot be converted because the user is not on Windows or has no Office, say so
  in one sentence and ask for the STS XML. Do not attempt to read the `.docx` directly and
  reconstruct the document from it — that produces something plausible and unverifiable, which is
  the one outcome this whole procedure exists to prevent.
