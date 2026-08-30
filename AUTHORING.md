<!-- Written by `Opc.Ua.SpecificationPublisher upgrade`, which refreshes it when a new version
     of the tool ships a new copy. It describes the tool's authoring dialect, so it is the
     tool's to keep current rather than each working group's to maintain by hand.

     Edit it if you want to - it then becomes yours, and the tool will not touch it again.
     Delete it and run `upgrade --write` to take the current copy back. -->

# Authoring this specification

The source of truth for this document is **markdown plus the NodeSet**, not a Word file.
A repository holds as many specifications as its working group publishes together: one
specification is a directory under `source/`, and
`source/<spec>/spec.md` carries its prose, `source/<spec>/manifest.json` its identity and the
clauses nobody should have to retype, and `model/*.NodeSet2.xml` — shared by all of them — the
models. The build produces STS XML, and everything downstream — the online reference, the
search index, the Word rendering — is made from that.

This page is the authoring contract. Some of it is enforced and some of it is not, and it is
worth knowing which as you read. `build` refuses anything the STS cannot carry and reports the
dialect rules on the source line; `Opc.Ua.SpecificationValidator validate` compares the built
document against the NodeSets; `.markdownlint-cli2.yaml` covers hygiene as you type. What none
of them check is the drawing inside a figure, and no rule anywhere checks whether the prose
means what it says. Read those parts as what a reviewer will hold you to.

```
dotnet tool restore                    # once, per clone

dotnet Opc.Ua.SpecificationPublisher build                # markdown + NodeSet -> STS XML
dotnet Opc.Ua.SpecificationPublisher publish              # render it and read it

dotnet Opc.Ua.SpecificationPublisher html                 # just the page, while you write
```

While you are writing, `html` is the one to run. It goes from the markdown to the same page
`publish` produces and writes nothing else — no STS, no `NodeIds.csv`, no Word edition — so
it is quick enough to run on every save and leave a browser tab open on. It reports the same
problems: the page is still rendered from the STS, built in memory, so anything that cannot
be carried is missing from what you are looking at rather than hidden until CI.

`build` is not a rule checker, but it is not silent either: anything it cannot carry into
the STS is reported and fails the run, and that covers most of what goes wrong in practice —
a cross-reference with no target, a nodetable naming a type the model does not have. CI runs
these same commands at the same pinned version, so a check that fails there fails here too.
Nothing needs Node, Python, a browser or Office.

## What you write, and what is written for you

Only some of the published document lives in your `spec.md`. The rest is generated,
because it is either identical in every companion specification or derivable from the
model — and a clause a working group cannot edit is a clause it cannot get wrong.

| Clause | Comes from |
|---|---|
| 1 Scope | **you**, in `spec.md` |
| Use cases, Information model overview, per-type prose | **you**, in `spec.md` |
| 2 Normative references | `manifest.json` → `normativeReferences` |
| 3.1 Overview | the OPC 20020 template + `identity` |
| 3.2 Terms and definitions | `manifest.json` → `terms` |
| 3.3 Abbreviations | `manifest.json` → `abbreviations` |
| Profiles and Conformance Units | `profiles.json`, beside it |
| Namespaces, Annex A | `manifest.json` identity + the NodeSet |
| Every node table | the NodeSet |

Clauses 1, 2 and 3 are mandatory: you write Scope, and the tool writes 2 and 3 whether or not
you ask. A document that is not a companion specification says so in its manifest and gets
neither — see below. Everything else generated is optional and appears only where you ask for it, with a
`clause` directive — the same idea as binding a table to a type with `defines=`:

````markdown
```{clause}
kind: profiles
```
````

`kind` is one of `terms`, `profiles`, `namespaces`, `annex-a`. `terms` is a subclause of clause 3
and goes in its fixed place there, so the directive only switches it on; the rest appear where you
write them. `annex-a` takes `capability-identifiers: true` to add A.2 Capability Identifiers.

There is no `conventions` kind. The Conventions clause was the same words in every companion
specification, and those words are now in OPC 10000-3 — which your normative references already
cite. A `kind: conventions` directive left over from an earlier document is reported, saying
exactly that.

### A document that is not a companion specification

Not everything published through this pipeline has the clause structure OPC 20020 mandates. The
OPC UA Introduction whitepaper, the Conventions document and the template itself carry the same
identity, build from the same markdown and render through the same STS — and none of them opens
with Scope, Normative references and Terms, definitions and abbreviations in that order.

The manifest says so, once, and the three clauses stop being assumed:

```json
  "structure": {
    "scope": true,
    "normativeReferences": false,
    "termsDefinitionsAndAbbreviations": false,
    "frontMatter": false
  }
```

Every key defaults to `true`, so **a companion specification writes nothing here** and gets what
it always got. Turning one off removes the generated clause and the check that goes with it; it
does not stop the document authoring a clause of its own in that position, which is exactly what
OPC 20019 does with Conventions.

`frontMatter` is the Agreement of Use. Deleting `source/agreement-of-use.md` is not the same
statement — the file is shared by every specification in the repository, so a whitepaper that
should not carry a legal notice cannot say so by removing what its siblings need.

Don't edit `source/agreement-of-use.md` or `source/logo-left.*`/`logo-right.*` directly — `upgrade
--write` downloads them from the OPC Foundation and overwrites whatever is there. Name a
co-publisher in `legal.md` at the repository root; see that file for what it does and does not
affect.

`scope` is a check rather than a generator — it is the one mandatory clause no tool can write —
so turning it off only stops the build insisting that clause 1 is Scope. And because `terms` is a
subclause of clause 3, asking for it with a `{clause}` directive while clause 3 is off is reported
rather than silently dropped.

Two consequences worth stating plainly:

- **Do not paste a node table into the markdown.** Write a `nodetable` directive and let it
  be generated. This is the whole reason the document cannot drift from the model.
- **Conformance units are data, not prose.** They live in `profiles.json` beside the prose, because the
  same names also go into the NodeSet as `Category` elements, into the profile database, and
  into the definition table of every type that carries one. A unit the NodeSet carries and
  `profiles.json` does not define is reported; so is a Facet that requires a unit
  nothing defines.

A Facet may of course require something another specification defines, and that is written the
way a BrowseName from another namespace is — with the namespace index in front:

```json
{ "name": "0:Base Info Custom Type System", "group": "Base Information", "optional": false },
{ "name": "3:Machinery Machine Identification Server Facet", "group": "Profile", "optional": false }
```

The prefix is what says the unit is defined elsewhere, so it is not reported as undefined; an
index the namespace table does not declare still is. `group` is required on these and only on
these: a unit this document defines states its group once, on its own definition, and the table
takes it from there, but no such definition exists here to read for one that belongs to another
document. Write `Profile` when the entry is a Facet or a Profile, otherwise the Conformance
Group that document lists it under.

## Headings carry no numbers

Numbering comes from document order. Write the title only.

```markdown
## Use cases {#sec-use-cases}
### Quality assurance/traceability {#sec-quality-assurance-traceability}
```

Not `## 5 Use cases`. A number in a heading is printed twice by the renderer, and it goes
stale the moment somebody inserts a clause above it. Insert, delete and reorder clauses
freely — that is the point.

Every heading needs an anchor (`{#sec-...}`), because that is what cross-references bind
to. Anchors are stable across renumbering; numbers are not.

**An annex says so on its heading**, and is then lettered rather than numbered:

```markdown
## <Title> Namespace and mappings {#anx-namespace annex=normative}
```

`annex=normative` or `annex=informative` — the value is what the STS records as the annex's
`content-type`, and there is no default because "is this normative?" is not a question a tool
should answer on an author's behalf. Only a top-level heading (`##`) can be one; the clauses
under it are numbered A.1, A.2 from it. Do not write "Annex A" in the title: the letter comes
from position among the annexes, exactly as a clause number comes from position among the
clauses, so inserting one re-letters the rest.

Most companion specifications do not need this — their Annex A is generated, with
`` ```{clause} kind: annex-a ``. It is for an annex the working group writes.

## Prose can live in its own file

The ObjectTypes clause is most of the document, and in a specification with sixty types it
is the only clause anyone is editing. Give it a file, and read it in where it belongs:

````markdown
```{include objecttypes}
```
````

`objecttypes` is a key of the manifest's `markdown` block, and the manifest names the file:

```json
  "markdown": {
    "main": "spec.md",
    "objecttypes": "object-types.md",
    "figures": "figures"
  },
```

**The part carries its own headings.** Everything in `object-types.md` — heading and all —
takes the place of the directive, at the heading levels it was written with. So a part is not
limited to one clause: several small related clauses can share a file, which is usually what
you want when no one of them justifies a file of its own.

Breaking prose out is a move and nothing else: same text, same place in the document, same
numbering. An include can sit anywhere a heading could, a part can include a part of its own,
and a part that includes itself is reported rather than read forever.

Where you put the include decides the depth its prose lands at, because the part no longer sits
under a heading that states it. A file opening at `##` read in at the top of the document is a
run of clauses; one opening at `###` read in under a `##` heading is that clause's subclauses.
Skipping a level — `####` where `###` was meant — is reported, because nothing downstream could
tell it from a deliberate nesting.

It is still one document. An anchor declared in one file is cited from another, `update`
reads and rewrites every file together, and a citation that resolves is never reported as
dangling because of which file it happens to be in.

### How big is too big

**Aim for under about 1000 lines per file, and treat 2000 as the outer edge.** Nothing enforces
it. It is the point past which a diff stops being reviewable, a search returns forty hits per
type, and anyone — person or agent — has to hold the whole document to change one clause.

When a file is over, take the **largest top-level clause or annex** in it, give that a file of
its own, and look again. Repeat until everything is under, or until what is left is a single
clause that cannot be divided without cutting into the middle of somebody's argument — which is
where you stop, because a file that begins partway through a clause is worse than a long one.

Annexes are usually the easiest wins after the ObjectTypes clause: they are self-contained by
construction. And because a broken-out file can break out its own clauses in turn, an
ObjectTypes clause that is still enormous on its own gets one file per group of types. A file
that names itself, directly or through another, is reported rather than read until the stack
runs out.

## Cross-references

Two forms, and which one you use depends on whether the *label* is derived.

**A number is derived — so write no label:**

```markdown
... is formally defined in [](#tbl-examplemachinetype-definition).
... as shown in [](#fig-information-model-overview).
```

The renderer fills in "Table 19" or "Figure 6". Writing the number yourself creates a second
copy that nothing keeps in step (`OPC005`).

**A citation of another standard has a stable label — so write it out:**

```markdown
... see [OPC 10000-5](#ref-uapart5).
```

The label must match the entry in `manifest.json` (`OPC006`), and the id must exist there
(`OPC004`).

Anchor prefixes: `sec-` clauses, `tbl-` tables, `fig-` figures, `ref-` normative references.

## Node tables

You write them. Generating a node table from the NodeSet does not work consistently -- these
tables make editorial choices the model cannot express -- so the table is authored and merely
**bound** to the type it documents. The validator then reports where the table and the model
disagree, instead of the tool overwriting your work.

Bind it with `defines=` on the caption:

```markdown
*Table - ExampleMachineType Definition* {#tbl-examplemachinetype-definition defines=ExampleMachineType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | ExampleMachineType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:MachineryItemType defined in OPC 40001-1 |  |  |  |  |  |
| 0:HasAddIn | Object | 2:Components |  | 2:MachineComponentsType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| Example ExampleMachineType Basic |  |  |  |  |  |
```

Three things to know about that shape:

**Column spans are trailing empty cells.** Markdown has none, so a cell spanning the rest of
its row is written as one cell followed by empties, and the converter turns the run back into
a span. It reads acceptably on GitHub and needs no syntax other tools do not understand.

**A cell can hold a list.** A markdown row is one line, so there is nowhere to put the line
breaks a list needs — but a cell already separates things with `<br>`, and a run of `<br>`-
separated items each opening `- ` or `1. ` is read as the list it is meant to be:

```markdown
| Reported when | - the unit is not defined<br>- the Facet requires nothing<br>- the name collides |
| In order      | 1. resolve the NodeId<br>2. read the BrowseName<br>3. compare the two |
```

Bullets need the space after the dash, exactly as they do in prose, so `a value - not a bullet`
stays a sentence. The numbers you write are not read — a list renumbers itself, so `1. 1. 1.`
and `1. 2. 3.` are the same list. Text before or after the run stays an ordinary paragraph, so
an intro line and then the items works. A cell with no markers is a paragraph as it always was.

**Consecutive tables under one caption stay together.** The attribute block, the References
grid and the Conformance Units block are three tables sharing one caption and one number,
which is exactly the `table-wrap` the STS carries. Separate them with a blank line; do not
give them separate captions.

**`---` ends the run.** A blank line does not — it is not a block, and the run only ends when
something that is not a table comes along. So an uncaptioned table that is a table of its own
rather than another block of the one above it says so with a thematic break:

```markdown
| **Attribute** | **Value** |
| --- | --- |
| BrowseName | SomeType |

---

| **Editor Note** |
| --- |
| Something about the type, not part of its definition. |
```

The break prints nothing. It is not a horizontal rule, and it is not an empty paragraph — an
empty paragraph is what an author reaches for otherwise, and it doubles the space between the
two tables. Written anywhere else it is simply ignored, so it costs nothing to use it as a
reading aid in a long file.

**Every table that documents a type gets `defines=`**, not just the definition table -- the
additional references, additional subcomponents and attribute-values tables too. The kind is
read from the caption, so keep the wording (`... Definition`, `... Additional References`,
`... Additional Subcomponents`, `... Attribute values for child Nodes`).

`OPC009` reports a `defines=` naming a type the model does not declare; `OPC010` reports a
type in the model that nothing defines.

## DataType field tables

A Structure, Union, Enumeration or OptionSet is documented by two tables: the definition table
above, bound with `defines=`, and a field table beside it. The field table *is* derivable — it
is the `DataTypeDefinition` the NodeSet carries — so it is generated rather than merely checked.
Bind it with `datatype=`:

```markdown
*Table - ExampleSetpoints Structure* {#tbl-examplesetpoints-structure datatype=ExampleSetpoints}

| **Name** | **Type** | **Description** | **AllowSubtypes** |
| --- | --- | --- | --- |
| ExampleSetpoints | 0:Structure | Subtype of the 0:Structure defined in [](#ref-uapart5) |  |
|   SP1 | 0:Double | Setpoint 1 |  |
|   SomeVector | 0:Vector |  | Yes |
```

The shape follows the DataType's form and you do not choose it: Structure and Union get
Name / Type / Description, an Enumeration gets Name / **Value** / Description, an OptionSet gets
Name / **Bit** / Description. `AllowSubtypes` appears when the table already has it or a field
needs it, so a Union that never allows one keeps three columns. Write the caption alone and
`update` fills the table in; after that it keeps it in step.

Two things differ from `defines=`. Fields are written in the order the `DataTypeDefinition`
declares them, not the order you had — for a Structure that order is the wire format, so the
document disagreeing with the model is a finding rather than noise. And a field's **Description
is yours when the model has none**: every other column is a fact the model owns, but a NodeSet
with no `<Description>` should not silently erase the sentence an editor wrote.

Unlike `defines=`, the caption wording is not read, so `... Structure` and `... Values` are
conventions rather than requirements.

## Attribute values

The Value column of an "Attribute values for child nodes" table holds a Node's Value attribute,
and a markdown cell is one line — so a structured value is written with `<br>` between its parts:

```markdown
| 1:SomeMeasurement<br>0:EURange | High: 1000<br>Low: 0 | The range. |
| 1:SomeNumericArray             | 0<br>1<br>2          |            |
```

`Name: value` lines are an object and plain lines are an array, and both are published one line
per part, which is how the OPC tables set a small value. A value with a container inside it — an
EnumValues array of objects — is written as JSON instead, where the punctuation earns its place.
Write it either way: JSON in, lines out, if it is small enough for lines.

Only the first colon divides, so `NamespaceUri: urn:x:2026-08:y` is one field. Unquoted text is a
string unless it is plainly a number or a boolean, so `UnitId: 1234` compares as a number.

**Quotes mark a string.** A line is a field only when an *unquoted* name precedes the colon, so an
array element that contains one has to be quoted or it reads as a field: `"a:b"`. Quote a string
that would otherwise read as a number, too — `Code: "1000"`. The tool re-quotes on the way out
wherever it has to, so what it publishes reads back as the value it started from.

Mixing the two is an error rather than a guess, because a malformed object and an array of
unquoted strings want opposite corrections:

```
line 127: the value names fields on 1 of its 2 lines, but "0" names none.
Every line of an object has to start with "<Name>: "; quote a line that is meant to be a string.
```

## Method clauses

A Method's signature and its argument list are both in the model, on the Method's
`InputArguments` and `OutputArguments`. The binding goes on the **clause heading** rather than on
a caption, because the signature comes before any table there is to hang an attribute on:

```markdown
### ExampleReset {#sec-ExampleReset type=ExampleMachineType method=ExampleReset}
```

Both halves are required and neither means anything alone: a Method's BrowseName identifies it
within the Type that declares it, and two Types may each declare an `ExampleReset`.

That one binding governs two things in the clause. The fenced block after a `**Signature**` line:

````markdown
**Signature**
```
ExampleReset (
  [in]  0:String       Reason,
  [out] 0:Int32        Status);
```
````

and the table whose caption ends `Method Arguments`:

```markdown
*Table - ExampleReset Method Arguments* {#tbl-examplereset-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Reason | Why the reset was requested. |
| Status | The outcome. |
```

Only those two are touched. The result-codes table below them is not derivable and is left
exactly as you wrote it. Arguments appear in the order they are passed, which is the model's
order and not a presentation choice, and a description falls back to the one already in the
table when the NodeSet carries none — the same rule as a DataType's fields.

Write the `**Signature**` fence empty and the caption bare, and `update` fills both in.

## Figures

Not every figure is the same kind of thing, so not every figure is checked the same way.

| What it is | Save it as | Checked against the model? |
|---|---|---|
| An address-space diagram | `.drawio.svg` | **yes** — shapes, arrowheads, completeness |
| Any other diagram you draw | `.drawio.svg` + `freeform: true` | no |
| A drawing carried over from a Word master | its original `.vsdx` or `.pptx`, plus the `.svg` a generator renders from it | no — the rendered SVG is opaque |
| A photo, screenshot or artwork from elsewhere | `.png`, `.jpg`, `.svg` | no — it is opaque |
| A sequence or state diagram | `.mmd` | no |

The third row is a **supported steady state**, not a stage of a migration. A working group that
came from Word keeps its Visio and PowerPoint drawings as the source of truth, maps their
extension to a generator, and edits them in the application that drew them; `update --write`
re-renders the SVG and both are committed together. Publishing that way is complete and correct.
What it costs is the checking in column three — an exported SVG carries no diagram to read, so
nothing compares its shapes against the model. Moving to a checkable figure later is one line in
`figureGenerators`, and `.drawio.svg` is one destination for it rather than the only one.

````markdown
```{figure}
id: fig-information-model-overview
caption: Information Model overview
source: figures/information-model-overview.drawio.svg
```
````

A **`.drawio.svg`** is an SVG that carries its own diagram, so the picture and the source are
one file: it renders on GitHub and reopens in the editor, and nothing in the pipeline ever
has to render a diagram. In VS Code the Draw.io Integration extension edits one in place —
open, edit, save. There is no export step.

Compression is fine; draw.io deflates the embedded diagram by default and the validator
inflates it. `OPC012` fires only when there is no readable diagram at all, or when a file
named `.svg` is really plain draw.io XML and so renders nowhere.

**Images are accepted and not argued with.** A `.png` or a plain `.svg` is right for a
photograph, a screenshot, or artwork produced somewhere else. You get one note (`OPC033`)
recording that its shapes cannot be checked and that nobody without the original can correct
it — that is a statement of fact, not a complaint. It is only the wrong choice for an
address-space diagram, where being checkable is the point.

**A figure may be generated from a text source instead.** The requirement is only that the
figure is an SVG; draw.io is one way to get one and a renderer you run is another. Map the
source's extension to a script in the specification's `manifest.json`, and `update --write` runs it:

```json
"figureGenerators": { ".puml": "tools/puml-to-svg.ps1" }
```

The script is called as `<script> <source> <svg>` from the repository root and must write the
SVG; `.ps1` and `.sh` are both run, so the choice of language is yours. Only `update` runs
them — a build reads the committed `.svg` and executes nothing, so it does not matter what is
installed on the machine that builds. Commit the source and the `.svg` together.

Where the renderer is not the same program on every platform — a Visio drawing is rendered by
Visio on Windows and by LibreOffice elsewhere — name one per platform instead:

```json
".vsdx": { "win": "tools/office-to-svg.ps1", "default": "tools/office-to-svg.sh" }
```

The keys are `win`, `linux`, `mac` and `default`. This is written down rather than worked out
from the machine, so that it is the same for every author and there is nothing to change after
a clone. Renderers do differ, so a figure someone regenerates on the other platform can come
back as a whole-file diff — worth knowing, and the reason a group that is entirely on one
platform should just name one script.

**A diagram that names nothing in the model is left alone.** The notation only governs
figures that depict the address space, and the validator works out which those are: a shape
carrying a NodeId, or simply labelled with a BrowseName the model declares, opts the figure
in. One that names nothing gets a note (`OPC034`) suggesting `freeform: true`; adding it
makes the note go away and states the intent for the next reader.

### Draw it yourself; the validator checks it

You compose the figure in draw.io. Nothing is generated over the top of it and the layout is
entirely yours — a person makes a better diagram than a layout algorithm does.

What the validator enforces is the part that is not a matter of taste. OPC UA gives every
NodeClass a shape and every reference type an arrowhead, and **they are normative**. A wrong
shape or arrowhead makes the document state something about the model that is not true.

| NodeClass | Shape | | NodeClass | Shape |
|---|---|---|---|---|
| Object | rectangle | | ObjectType | rectangle **+ shadow** |
| Variable | rounded rectangle | | VariableType | rounded rectangle **+ shadow** |
| Method | ellipse | | DataType | hexagon **+ shadow** |
| View | trapezoid | | ReferenceType | chevron **+ shadow** |

| Reference | Arrowhead | | Reference | Arrowhead |
|---|---|---|---|---|
| HasSubtype | hollow double block | | HasEventSource | hollow block |
| HasTypeDefinition | filled double block | | HasInterface | hollow block, dashed |
| HasComponent | single crossbar | | Hierarchical | open arrowhead |
| HasProperty | double crossbar | | Asymmetric | filled block |
| HasAddIn | open arrowhead | | Symmetric | filled block at both ends |
| | | | OneWay | filled block, dashed |

`HasAddIn` and a plain hierarchical reference are drawn identically, so the picture cannot
distinguish them and neither can the checker. `opcReferenceType` is what says which one you
meant, and both are accepted against that arrowhead.

### The palette is the only way in

`source/figures/uashapes-library.drawio.xml` is a draw.io **shape library**. Import it once and
the eight NodeClasses and eleven reference types appear as a palette in the shapes panel; you
drag out the one you want and type the BrowseName into it.

It is not a diagram you copy cells from, and there is nothing to type by hand. Each shape is a
compiled stencil taken from the OPC Foundation's Visio master — the geometry is a base64 blob
inside the style, so a shape is either the notation's shape or it is not one, and there is no
near-miss to argue about. The validator compares the same way: byte-for-byte against the
palette entry, not against a description of it.

**In the draw.io desktop app or the web editor**, *File ▸ Open Library from ▸ Device*, and
choose the file. It appears at the top of the shapes panel, above Scratchpad, and stays open
until you close it.

**In VS Code**, add it through the shapes panel of the Draw.io Integration extension the same
way. The extension also has a `hediet.vscode-drawio.customLibraries` setting that would load
the palette automatically, and this repository deliberately does not ship one:

```json
"hediet.vscode-drawio.customLibraries": [
  { "entryId": "opcua", "libName": "OPC UA",
    "file": "${workspaceFolder}/source/figures/uashapes-library.drawio.xml" }
]
```

`${workspaceFolder}` is the *first* folder VS Code has open, which is the repository only when
you opened the repository. Open a parent directory, or add it to a multi-root workspace, and
the path resolves to nothing — and the extension does not guard the read, so the editor comes
up **blank** with no error to explain it. Set it in your own user or workspace settings if you
want it; it is not something a repository should do to everyone who clones it.

The library is written by the tool, like `AUTHORING.md` and the workflow are: `upgrade` puts
the current one in place, so a correction to the notation arrives with a tool release rather
than as a file somebody has to re-import in every repository. Edit it and it becomes yours,
`upgrade` stops refreshing it, and `OPC019` reports once that the notation this repository
draws with is no longer the notation the tool ships.

A **drop shadow marks a type** — all four type NodeClasses carry one, no instance does. It is
no longer what identifies them, though: each palette entry carries its own identity, so an
ObjectType is recognised as an ObjectType whatever the page is doing to shadows. **Format ▸
Diagram ▸ Shadow applied to the whole page** is now a cosmetic defect rather than a
correctness one — every shape renders shadowed and a reader can no longer see which are types.
`OPC018` still reports it.

Only the notation-bearing properties are compared. Routing, waypoints, exit and entry
points, spacing, colour — all yours, all ignored by the checker.

**Naming a box.** Give it the BrowseName as its label and the validator resolves it:

```
ExampleMachineType    a type this document declares
2:MachineryItemType   a type from another specification, with its namespace prefix
```

For a box whose label you expect to reword, attach the NodeId instead — draw.io's *Edit
Data* (right-click ▸ Edit Data), key `opcNodeId`. The NodeId then identifies the box no
matter what it says. If you set both, they must agree (`OPC017`).

**Naming an edge.** Set `opcReferenceType` on it via Edit Data — `HasSubtype`,
`HasComponent`, and so on. An edge with no reference type is a line whose meaning nobody
stated, and in this notation the arrowhead *is* the meaning, so it is reported (`OPC014`).

**Optional scaffolding.** Seeding a `.drawio` from the model — shapes and arrowheads already
correct, for you to rearrange — is planned as a `seed-figure` verb on the tool. Until it
lands there is no scaffolding: start from an empty canvas and drag the shapes out of the
palette. It was always a convenience rather than the workflow.

### What is checked

| | |
|---|---|
| `OPC013` | a shape against the palette entry for the NodeClass of the node it names |
| `OPC014` | an edge's arrowheads against its reference type, and edges with no reference type |
| `OPC016` | no box names something the model has never heard of |
| `OPC017` | a box's label agrees with the node its NodeId identifies |
| `OPC018` | page-level shadow, which makes every shape look like a type |
| `OPC019` | this repository's copy of the shape library is not the one the tool ships |

Compression is fine — draw.io deflates the embedded diagram by default and the validator
inflates it. `OPC012` fires only when there is no readable diagram at all, or when a file
named `.svg` is really plain draw.io XML and so renders nowhere.

### Free-form figures

Not every diagram depicts an address space. A workflow, a deployment sketch, a state
machine, a conceptual overview — the OPC UA notation does not govern any of them, and
forcing it on them would be nonsense. Mark those exempt:

````markdown
```{figure}
id: fig-ordering-workflow
caption: Ordering workflow
source: figures/ordering-workflow.drawio
freeform: true
```
````

A free-form figure is skipped by every rule above. It must still be a `.drawio` or `.mmd`
in this repository — an editable source is not the same requirement as the notation, and
that one does not lapse.

## Prose conventions

- **One paragraph per line.** Do not hard-wrap. A reworded sentence should be a one-line
  diff, not a reflowed block.
- ***Italics are semantic.*** `*Term*` marks a defined term or an OPC UA term and feeds the
  term index. Do not use italics for emphasis.
- **Mind the space.** `*Nodes *and` and `the* optional Nodes *under` both render a literal
  asterisk and lose the term (`OPC020`). `--fix` corrects them.
- **No raw HTML** (`OPC007`), with one exception: `<br>` is a hard line break, and `<br/>` and
  `<br />` are the same thing. It is the only one, because a paragraph is one line here — the
  two-trailing-spaces convention has nowhere to live — and a cell holding four sentences that
  belong on four lines has no other way to say so. It becomes a real break in the STS, the page
  and the Word edition, not the literal text `<br>`. Anything else markdown cannot express is a
  conversation about the dialect, not a place for a `<table>`.
- **Angle brackets are otherwise literal.** `<SUBJECT>` reads as a placeholder prompt and `a < b`
  as a comparison, in the source and in the published document alike.
- **Do not link `reference.opcfoundation.org`** (`OPC030`). Cite `OPC 10000-N`; the
  generated clauses carry the addresses.

## The rules

`--list-rules` prints the current set. They grow over time; the identifiers are stable, so
a rule is never renumbered and a finding can always be cited.

| Range | Concern |
|---|---|
| `OPC001`–`OPC011` | structure and dialect — the converter cannot proceed |
| `OPC012`–`OPC019` | figures — notation conformance and agreement with the model |
| `OPC020`–`OPC024` | markdown hygiene — mostly `--fix`able |
| `OPC030`–`OPC032` | content policy and model agreement |

Severity is `error` when the converter would fail or produce something quietly wrong,
`warning` when it is legitimate but probably not intended, `note` for cosmetics. Only errors
fail the build.

## What runs when

| Event | What happens |
|---|---|
| Pull request | markdownlint + the rule checker. Findings appear inline on the changed lines, via code scanning. Errors fail the check. |
| Push to `main` | the STS XML is built and committed to `artifacts/`. |

A finding on a line you did not touch still appears in the checks tab and in the job
summary — code scanning only annotates lines within the diff, which is a GitHub constraint,
not a judgement about which findings matter.

## Getting from the rendering back to the source

Every clause, table and figure in the published page carries a 📝 beside its
heading. It opens what was written to produce it:

- **reading the page from your checkout** — the markdown file itself, in your editor, at the
  line. VS Code needs nothing installed; the first click asks the browser for permission to
  open it, and there is a box to stop asking. `--editor` selects a different one —
  `vscode-insiders`, `vscodium`, `cursor`. Visual Studio has no URL scheme of its own and is
  not among them.
- **reading it on the published site** — the source on GitHub, at the same line, pinned to
  the commit that build read rather than to a branch that has moved since.

Nothing is baked into the page: where the link goes is worked out when you open it, from
where you opened it. So the same file works from a clone and from the site, and cloning the
repository and opening `docs/index.html` gives you links into *your* copy.

**A generated clause has one too**, pointing at whatever decides what it says rather than at
prose it does not have — and the tooltip names the file, so landing in JSON is never a
surprise:

| Clause | Opens |
|---|---|
| 2 Normative references | `manifest.json`, at `normativeReferences` |
| 3.1 Overview | `manifest.json`, at `identity` |
| 3.2 Terms and definitions | `manifest.json`, at `terms` |
| 3.3 Abbreviations | `manifest.json`, at `abbreviations` |
| Conformance Units, and its table | `profiles.json`, at `conformanceUnits` |
| Profiles, and the URI table | `profiles.json`, at `profiles` |
| One Facet's subclause | `profiles.json`, at **that Facet's own entry** |
| Namespaces | `manifest.json`, at `namespaces` |
| Annex A | the `{clause}` directive that asked for it |

So every heading in the document carries a 📝. That is deliberate: a clause with no link is
indistinguishable from a feature that has stopped working.

Links come from a map `build` writes beside the STS, and `html` writes beside the page. It is
not committed, so a document rendered from the artifacts alone simply has no links; nothing
else changes.
