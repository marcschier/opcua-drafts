# Presentations

Reviewer- and stakeholder-facing decks that introduce the working-draft specifications in this repository. The decks **summarize and link** to the normative drafts — they are not themselves normative.

## Contents

- `OPC-UA-Encoding-and-Registry-Overview.md` — ~12-slide [Marp](https://marp.app/) deck introducing the **Avro binding** (why / how / measured performance), the **xRegistry** base, and the **Schema Registry**. Includes per-slide presenter notes and Mermaid diagrams.
- `OPC-UA-Observability-Export-Overview.md` — ~12-slide [Marp](https://marp.app/) deck introducing the **Observability Export** companion specification: the why, the two-layer contract, the information model, the OpenTelemetry (OTEL) mapping and bridge, applied examples, and conformance. Includes presenter notes and Mermaid diagrams.

## Format

Each deck is a single [Marp](https://marp.app/) Markdown file:

- YAML front matter selects the theme, size and pagination.
- Slides are separated by `---` (thematic breaks).
- **Presenter notes** are HTML comments (`<!-- Speaker notes: … -->`) — they are shown in Marp presenter view and exports with notes, and hidden on the rendered slides.
- **Diagrams** are fenced ```mermaid blocks, following the repository convention (the same blocks are syntax-checked in CI by `.github/scripts/check_mermaid.py`).

## Render

Marp CLI renders a deck to HTML, PDF or PPTX. The commands below use `OPC-UA-Encoding-and-Registry-Overview.md`; swap in `OPC-UA-Observability-Export-Overview.md` to render the other deck. From the repository root:

```powershell
# HTML (self-contained)
npx --yes @marp-team/marp-cli core-specs/presentations/OPC-UA-Encoding-and-Registry-Overview.md --html -o overview.html

# PDF (with presenter notes)
npx --yes @marp-team/marp-cli core-specs/presentations/OPC-UA-Encoding-and-Registry-Overview.md --pdf --pdf-notes -o overview.pdf

# PowerPoint
npx --yes @marp-team/marp-cli core-specs/presentations/OPC-UA-Encoding-and-Registry-Overview.md --pptx -o overview.pptx
```

### PPTX with rendered diagrams (build script)

`marp --pptx` does **not** render Mermaid. To export every deck in this folder to PPTX with the Mermaid diagrams pre-rendered and embedded, run the build script:

```powershell
pwsh core-specs/presentations/build-pptx.ps1
```

For each Marp deck (`marp: true` in front matter) it renders the ```mermaid blocks to PNG via the Mermaid CLI, substitutes them into a temporary build copy (with a small build-only stylesheet so the diagrams and text fit), and runs marp-cli — writing `<deck>.pptx` next to each deck. The source Markdown is never modified. Requires Node.js on PATH.

### Mermaid diagrams

Standard Marp does not render Mermaid natively. Two supported paths:

- **VS Code** — the *Marp for VS Code* extension with Mermaid enabled renders the diagrams inline in the preview and its exports. This is the simplest path for authoring.
- **Marp CLI** — enable a Mermaid-capable engine, or pre-render the diagrams to SVG (for example with `npx --yes @mermaid-js/mermaid-cli`) and reference the images. GitHub and the VS Code Markdown preview render the ```mermaid blocks as-is, so the source stays diffable and review-friendly either way.

## Sources

Each deck summarizes and should stay consistent with its normative sources.

**`OPC-UA-Encoding-and-Registry-Overview.md`**

- [Avro Part 6 — DataEncoding](../avro-encoding/OPC-UA-Part6-Avro-DataEncoding.md) and [Avro Part 14 — PubSub mapping](../avro-encoding/OPC-UA-Part14-Avro-MessageMapping.md)
- [xRegistry base](../xregistry/OPC-UA-xRegistry.md) and its [OPC UA API binding](../xregistry/xRegistry-OPC-UA-Api.md)
- [Schema Registry](../schema-registry/OPC-UA-Schema-Registry.md)
- [Encoding performance comparison](../extras/performance/OPC-UA-Encoding-Performance-Comparison.md) (all performance numbers on the Avro slide are cited from this report)

**`OPC-UA-Observability-Export-Overview.md`**

- [Observability Export](../observability-export/OPC-UA-Observability-Export.md)
