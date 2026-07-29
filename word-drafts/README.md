# Word drafts

Submission-ready **Microsoft Word** renderings of the specification drafts, built into the
official OPC Foundation companion specification template
(`templates/OPC 20020 - UA Companion Specification Template v1.01.19.docx`).

Nothing here is normative or endorsed by the OPC Foundation. The document number, the Mantis
project identifier and every NodeId are the template's own placeholders; the OPC Foundation
assigns the real values.

| Artifact | What it is |
|---|---|
| `OPC-UA-OpenUSD-Binding-Part1.docx` | The generated document. Committed, so a reviewer needs no toolchain. |
| `OPC-UA-OpenUSD-Binding-Part1.docmodel.json` | The intermediate representation the document was rendered from. Committed **because a `.docx` diff is unreadable** — review this instead. |
| `figures/*.pptx` | The editable PowerPoint behind each figure, embedded in the document as an OLE object. |
| `figures/*.png` | The preview image Word displays for each embedded object. |
| `tools/` | The build, the validator and its mutation test. |

## Commands

```powershell
# one-time
pip install -r word-drafts/tools/requirements.txt

# markdown + NodeSet -> .docx  (pure Python, cross-platform, byte-reproducible)
python word-drafts/tools/build_docx.py word-drafts/tools/specs/openusd-binding.json

# check the result against the template contract
python word-drafts/tools/validate_docx.py word-drafts/tools/specs/openusd-binding.json

# prove the validator actually catches what it claims to
python word-drafts/tools/test_validate_docx.py word-drafts/tools/specs/openusd-binding.json

# update the table of contents, the table of figures, the table of tables and every
# cross-reference, so the committed file opens fully paginated  (needs Word; local only)
pwsh word-drafts/tools/finalize_word.ps1 -Path word-drafts/OPC-UA-OpenUSD-Binding-Part1.docx

# rewrite the markdown source into the same clause skeleton
python word-drafts/tools/restructure_markdown.py word-drafts/tools/specs/openusd-binding.json
```

Run `finalize_word.ps1` before committing. The pure-Python build cannot paginate, so without it
the table of contents and every page number carry no correct value until a reader updates the
fields by hand.

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
abbreviations, the clause map and the figure list. Adding another specification is a new config
file, not new code.

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
