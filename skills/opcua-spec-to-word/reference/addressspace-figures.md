# AddressSpace figures

An AddressSpace figure draws part of an information model in the OPC UA graphical notation
of OPC 10000-3. It is authored as Mermaid in the specification markdown, rebuilt as a real
PowerPoint object for the Word rendering, and checked against the UANodeSet it claims to
draw.

Three separate things have to line up, and each exists for a reason.

## Why not a PNG

Template contract Guideline 1: *figures shall be embedded PowerPoint/Excel/Visio objects*,
and `pipeline.md` names "rendering Mermaid to PNG and inserting a picture" as the way to
violate it. The `.png` beside every `.pptx` is Word's preview bitmap for the OLE object,
never the figure itself. So there is no PNG fallback for a diagram the renderer cannot
draw — the answer is to teach the renderer, or to split the figure.

## The notation

The notation is **opt-in**. A diagram enters it by giving any node a `:::` class; without
one, the renderer draws exactly what it drew before. Architecture and sequence figures are
therefore untouched by any of this, and their bytes do not move.

| Concept | Mermaid | PowerPoint |
| --- | --- | --- |
| Object, Variable, View | `N[Name]:::object` / `:::variable` / `:::view` | plain rectangle |
| Method | `N(Name):::method` | rounded rectangle |
| ObjectType, VariableType, ReferenceType, DataType | `N[[Name]]:::objecttype` and so on | rectangle with a grey drop shadow |
| Abstract type | add `abstract` to the class list: `N[[Name]]:::objecttype,abstract` | shadowed rectangle, italic label |
| Placeholder | write the BrowseName as `&lt;Name&gt;` | rectangle, brackets shown |

| Reference | Mermaid | PowerPoint |
| --- | --- | --- |
| HasComponent | `A --> B` | open arrowhead, no label |
| HasTypeDefinition | `A ==> B` | large solid arrowhead |
| HasInterface | `A -.->\|HasInterface\| B` | dashed, labelled |
| Any other ReferenceType | `A -->\|BrowseName\| B` | labelled arrow |

PowerPoint has no double-arrowhead line end, so `HasTypeDefinition` is distinguished by a
large solid head rather than the two triangles a hand-drawn figure uses. The legend figure
in the specification states this, so a reader is never guessing.

`classDef` lines are carried in the markdown so GitHub renders the same distinction, and
are ignored by the PowerPoint renderer, which is driven by the `:::` classes themselves.

**One `:::` per node.** Several classes go in one comma-separated list —
`:::objecttype,abstract`. Chaining them as `:::objecttype:::abstract` is a parse error in
Mermaid itself, so GitHub shows a red *"Unable to render rich display"* box where the
figure should be. `python .github/scripts/check_mermaid.py` compiles every block with the
Mermaid CLI and is the gate that catches it; run it whenever a diagram changes, because
nothing else in the build does — the PowerPoint renderer parses its own subset and will
happily accept syntax Mermaid rejects.

## The gate

A figure opts into checking with a directive immediately above its fence:

```text
<!-- model-figure: root=ns=2;i=1 require=mandatory external=Objects,BaseObjectType -->
```

- `root` — the Node the figure is scoped to, as a NodeId or an unambiguous BrowseName.
- `require=mandatory` — every Mandatory member of the root must appear in the figure.
- `external` — Nodes from a required model, which this NodeSet cannot verify. They must be
  named explicitly; otherwise a typo in a BrowseName would be waved through as "probably
  from the base namespace".

`opcdocx/nodeset_diagram.py` then re-derives every claim from the NodeSet: that each Node
exists, that its NodeClass matches the declared class, that `IsAbstract` matches
`:::abstract`, that a bracketed BrowseName matches a placeholder ModellingRule, and that
every edge is a real Reference of that type in that direction.

**An edge to an `external=` Node is checked from the end that is in the model.** Every
figure anchors its types on a base-namespace supertype, so skipping those edges — which is
what "one end is not in this NodeSet" first suggests — left the majority of edges
unverified, and a `HasSubtype` drawn as an `Organizes` passed. A NodeSet does carry its own
half: the inverse `HasSubtype` sits on the subtype and the inverse `HasComponent` on the
child, each naming a NodeId outside the model. That verifies the ReferenceType and its
direction, and where the far NodeId is a well-known base Node its BrowseName is verified
too. Where it is not known, the edge is accepted on type and direction rather than guessed
at.

**Resolution walks the graph, not the name index.** This model has 46 BrowseNames borne by
more than one Node — `CreateAsset` exists on the type *and* on the well-known instance, and
so does most of the 1.02 surface. Resolving by name would check an edge against the wrong
Node and report success. A child is therefore resolved as the Node its already-resolved
parent actually references. Where the reference is stored only on the far side — a NodeSet
writes `HasTypeDefinition` on the instance and leaves the type with no inverse — the
relation is searched from the other end.

The gate runs from the specification's own `tools/validate_local.py`, because validation in
this repository is per-extension.

## Adding a figure

1. Author the Mermaid with `:::` classes and the directive.
2. Add a `figures[]` entry to the Word config **in document order**. The build pairs
   diagrams with entries positionally, so an entry in the wrong place captions the wrong
   picture.
3. Run `python .github/scripts/check_mermaid.py`. The PowerPoint renderer parses a subset
   of Mermaid and accepts things Mermaid does not, so a diagram can build into a perfect
   Word figure and still fail to render on GitHub.
4. Run the specification's validator; it will name every disagreement with the model.
5. Rebuild the document and run `finalize_word.ps1`.

If a figure is too wide the layout wraps it and the edges start to cross. That is the
signal to split it — a figure is meant to show the part of the model its clause describes,
not the whole model.
