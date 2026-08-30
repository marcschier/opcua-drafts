---
name: opcua-companion-spec
description: >-
  Author, edit and build an OPC UA companion specification whose source of truth is markdown
  plus a UANodeSet, in a working-group repository laid out like this one. Covers which
  clauses are authored and which are generated, the cross-reference and node-table dialect,
  draw.io figures in the normative OPC UA notation, the conformance-unit direction of
  travel, and how the STS XML is
  produced. WHEN: edit a clause, add or rename an ObjectType, add a conformance unit, add or
  change a figure, fix a lint finding, rebuild the STS XML, migrate a Word-source
  specification into this shape, or set up a new working-group repository from this one.
---

<!-- Written by `Opc.Ua.SpecificationPublisher upgrade`, which refreshes it when a new version
     of the tool ships a new copy. Edit it and it becomes yours; delete it and run
     `upgrade --write` to take the current copy back. -->

# OPC UA companion specification — markdown source

A repository holds as many specifications as its working group publishes together: one is a
directory under `source/`, and a directory with no files in it only groups others. A published
document is built from three things: `source/<spec>/spec.md` (prose), `model/*.NodeSet2.xml`
(the models, shared by every specification in the repository) and `source/<spec>/manifest.json`
(identity, plus the clauses nobody should retype). The build emits STS XML into `artifacts/`, and everything downstream — the online
reference, the search index, the Word rendering — is made from that.

Read `AUTHORING.md` first. It is the authoring contract; this skill is how to work
inside it.

## The one rule that explains the others

**Anything that can be derived is derived.** Clause numbers come from document order, table
and figure numbers from position, node tables from the NodeSet, the normative references and
namespace clauses from `manifest.json`. If you find yourself typing something the model or the
manifest already knows, that is the mistake — you have just created a second copy that
nothing keeps in step.

The corollary is that a lot of the published document is not in the markdown at all. Do not
go looking for clause 3, the Profiles clause or Annex A to edit; they are generated.
Ask for an optional one with a ```{clause}``` directive naming its `kind`.

## Where things live

| To change | Edit |
|---|---|
| Prose in any authored clause | `source/<spec>/spec.md` |
| A type's members, DataTypes, references | the NodeSet **and** the table that documents it; the validator reports if they disagree |
| Which types exist | the NodeSet, then add a clause with a table bound by `defines=` |
| Conformance units and Profiles | `source/<spec>/profiles.json` |
| Normative references, abbreviations, namespace indices, identity | `manifest.json` |
| A figure | `source/<spec>/figures/*.drawio` — draw it by hand; the validator checks the notation |
| Anything in `artifacts/` or `docs/` | nothing — the next build discards it |

## The dialect, in brief

```markdown
## Use cases {#sec-use-cases}          <- no number; anchors are mandatory

... defined in [](#tbl-examplemachinetype-definition).  <- derived label: leave it empty
... see [OPC 10000-5](#ref-uapart5).               <- stable label: write it out
```

````markdown
```{figure}
id: fig-information-model-overview
caption: Information Model overview
source: figures/information-model-overview.drawio
```
````

Build and render before you claim to be done:

```
dotnet tool restore
dotnet Opc.Ua.SpecificationPublisher build             # fails on anything the STS cannot carry
dotnet Opc.Ua.SpecificationPublisher publish           # render it and read it before saying it is done
```

While you are still editing, `html` does both in one pass and writes only the page — same
rendering, same reported problems, none of the artifacts you are not reading yet:

```
dotnet Opc.Ua.SpecificationPublisher html
```

`build` is not the rule checker. It catches what cannot be carried into the STS, and reports the
dialect rules on the line that broke them, but it does not compare the document against the
model. That is a separate tool, run on what `build` produced:

```
Opc.Ua.SpecificationValidator validate artifacts/<doc>.xml model/<primary>.NodeSet2.xml --dependency-dir model/dependencies
```

Between them they leave two things unchecked: the drawing inside a figure, and whether the prose
means what it says. Both are in `AUTHORING.md` and are on you to hold to.

## Conformance units are data, not prose

A unit's name appears in four places: the Conformance Units table, the Facet that requires it,
the `Category` element on every Node that implements it, and the profile database. It is
defined once, in the specification's `profiles.json`, and every clause that prints it is
generated from there. So

- adding a unit means adding it to that `profiles.json`, then putting the `Category` on the Nodes
  that implement it;
- a `Category` the NodeSet carries that no unit defines is reported, and so is a Facet that
  requires a unit nothing defines;
- renaming a unit in one place and not the other is the failure this rule exists to catch.

## Adding a type

1. Add it to the NodeSet (or to the generator that writes the NodeSet).
2. Add a clause in its `spec.md` with prose and a `nodetable` directive.
3. Add its conformance units to its `profiles.json`, and the matching `Category`
   elements to the NodeSet.
4. Run the checker. `OPC010` tells you about a type in the model with no clause; `OPC009`
   about a clause naming a type the model does not have. Both mean the same thing — the two
   halves were changed by different hands.

## Traps

- **A number in a heading.** The renderer supplies it; writing it yourself prints it twice
  and it goes stale the moment a clause moves. This is `OPC001` and it is the single most
  common mistake coming from a Word-authored document.
- **A label on a derived cross-reference.** `[Table 15](#tbl-x)` freezes a number that the
  renderer owns. Write `[](#tbl-x)`.
- **Emphasis with the space on the wrong side.** `*Nodes *and` and `the* optional Nodes *up`
  both render a literal asterisk and drop the term out of the index. Neither is visible in a
  parity check — the asterisk count is even in both. `--fix` handles them.
- **A node table with no `defines=`.** Nothing then checks it against the model, which is the
  one thing that makes a hand-written table trustworthy.
- **Drawing a shape instead of dragging one.** The notation is a draw.io shape library,
  `source/figures/uashapes-library.drawio.xml`, and every NodeClass and reference type comes
  out of it. The shapes are compiled stencils, so a rectangle you drew yourself is not the
  Object shape however much it looks like one, and the checker compares against the palette
  entry. Import the library once — in the draw.io app it is *File ▸ Open Library from ▸
  Device*, and in VS Code you add it through the shapes panel of the Draw.io Integration
  extension.
- **Using the wrong shape or arrowhead.** They are normative: an Object is a rectangle, a
  Method an ellipse, a type carries a shadow, and a hollow arrowhead does not mean what a
  filled one means. Label a box with its BrowseName (or set `opcNodeId`
  via Edit Data) and set `opcReferenceType` on every edge, and the validator checks the
  rest. Layout, routing and colour are yours and are not compared.
- **Forgetting `freeform: true`.** A workflow or state diagram is not an address-space
  view and the notation does not govern it. Mark it exempt rather than contorting it.
- **A compressed .drawio.** draw.io deflates the body by default and the file becomes a
  base64 blob — no shape check, no review. Turn compression off in File > Properties.
- **Reaching for an image when the figure depicts the address space.** A `.png` or plain
  `.svg` is fine for a photo, a screenshot, or artwork from elsewhere, and the validator says
  so once and carries it. For an address-space diagram it is the wrong choice: nothing can
  check it and nobody without the original can correct it. A binary nobody opens is a binary
  nobody checks, and the type it is missing stays missing.
- **Editing `artifacts/` or `publish/`.** Both are build output, exactly like the NodeSet is
  build output for a working group that generates its model. `publish/` is the tempting one,
  because it is the readable rendering — and it is regenerated from the STS on every merge.

## Migrating a Word-source specification into this shape

The Word path is not deprecated — it is the other supported workflow, and a working group
picks one. If a group is moving, the order that works is:

1. Convert the `.docx` to STS with the existing converter; that artifact is the reference.
2. Emit markdown from the STS and restructure it into this dialect: drop the generated
   clauses, unnumber the headings, replace node tables with directives, and redraw the
   figures in the notation `AUTHORING.md` sets out.
3. Rebuild STS from the markdown and diff it against step 1. An empty diff means the
   markdown carries everything; a non-empty diff is the exact list of what it does not.

Do not skip step 3 and do not eyeball it. The whole claim being made is that nothing was
lost, and that claim is checkable.
