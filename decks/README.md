# `decks/` — the drafts overview deck

One deck covers **every** effort in this repository: the drafts in `core-specs/`, `cloud-specs/`,
`metaverse-specs/`, `wot-specs/` and `companion-specs/`, together with the ten demos that show them
running on the [OPC UA .NET Standard stack](https://github.com/OPCFoundation/UA-.NETStandard).

| | |
|---|---|
| Deck | [`OPC-UA-Drafts-Overview.pptx`](OPC-UA-Drafts-Overview.pptx) |
| Slide source | [`content/`](content/) — one YAML file per effort, one per demo |
| Generator | [`build_deck.py`](build_deck.py) (structure) and [`theme.py`](theme.py) (look) |
| Checks | [`check_layout.py`](check_layout.py) (geometry) and [`export_slides.ps1`](export_slides.ps1) (look at it) |
| Demo material | [`demos/`](demos/) — a presenter walkthrough and a runnable script per demo |

## The deck is generated — never edit the `.pptx`

Exactly like the Word renderings under [`word-drafts/`](../word-drafts/): the PowerPoint file is a
build artifact of the YAML beside it. Edit the YAML and rebuild; a hand edit is lost on the next
build.

```powershell
# regenerate the deck
python decks/build_deck.py

# validate the content without writing a file
python decks/build_deck.py --check

# fail on any content problem (what CI would run)
python decks/build_deck.py --check --strict
```

Requires `python-pptx` and `PyYAML`.

The build is **deterministic** — like the generators elsewhere in this repository, rebuilding
without a content change produces a byte-identical `.pptx`, so a clean `git status` after a rebuild
confirms the deck matches its source.

## Content model

Every file under `content/` is one YAML document describing a run of slides:

```yaml
id: core-05-data-channels          # stable identifier, matches the file name
section: core                      # core | cloud | metaverse | wot | companion | front | close
order: 150                         # global sort key; files are emitted in ascending order
footer: OPC UA — Data Channels     # per-file footer, overridable per slide
slides:
  - layout: bullets
    title: Why it exists
    kicker: OPC UA has no streaming primitive
    bullets:
      - text: Video, audio and continuous content run **beside** the Server today
        children:
          - An RTSP or WebRTC endpoint with its own port, handshake and trust anchor
      - text: A second security surface is a second thing to get wrong
    takeaway: One SecureChannel, many streams — no second trust anchor.
    notes: |
      Speaker notes. Every content slide needs them.
```

### Ordering

`order` is a global sort key across all files, so a demo slide is placed by giving it an `order`
between the effort's slides. The convention is:

| Range | Holds |
|---|---|
| 0–99 | front matter |
| 100–199 | `core` |
| 200–299 | `companion` |
| 300–399 | `wot` |
| 400–499 | `cloud` |
| 500–599 | `metaverse` |
| 700–799 | the reference implementation and the demos that show the stack itself |
| 900+ | closing |

Within a range, each effort gets a block of ten (`110`, `120`, …) and its slides step by one.
A demo slide uses the order immediately after the effort's last slide.

### Inline formatting

`**bold**` and `` `code` `` work inside any text field.

> **YAML gotcha.** A backtick is a reserved indicator in YAML and cannot *begin* a plain scalar.
> Quote any value that starts with one — ``text: "`FolderType` is the projection"`` — or put a word
> in front of it. The same applies to a leading `@`.

### Layouts

| `layout` | Fields | Use for |
|---|---|---|
| `title` | `title`, `subtitle`, `byline` (list), `disclaimer` | the opening slide |
| `section` | `title`, `subtitle`, `contents` (list) | a tree divider |
| `bullets` | `title`, `kicker`, `bullets`, `takeaway` | the workhorse |
| `two-column` | `title`, `kicker`, `left`/`right` each `{heading, bullets}` | contrasts, before/after |
| `table` | `title`, `kicker`, `table: {columns, rows, widths, font_size}` | type tables, matrices |
| `code` | `title`, `kicker`, `intro`, `code`, `outro`, `font_size` | NodeSet, JSON, C#, shell |
| `diagram` | `title`, `kicker`, `cols`, `rows`, `nodes`, `arrows`, `captions` | architecture, flow |
| `statement` | `statement`, `attribution` | the one claim a section turns on |
| `demo` | `title`, `kicker`, `state`, `see`, `parts`, `run`, `proves` | the demo slides |

#### `bullets`

Either a plain string or a mapping. Nesting is expressed with `children` (preferred) or an explicit
`level` (0–2). `style: muted` renders an aside.

#### `diagram`

`nodes` are placed on a grid — `cols` wide (default 12) by `rows` tall (default 6):

```yaml
- layout: diagram
  title: How it all fits
  cols: 12
  rows: 6
  nodes:
    - {id: reg, x: 4.5, y: 0, w: 3, h: 1, text: xRegistry, style: primary}
    - {id: sr,  x: 0.5, y: 2, w: 3, h: 1.2, text: Schema Registry, lines: ["subtypes the base model"]}
  arrows:
    - {from: reg, to: sr, label: subtypes}  captions:
    - {x: 0, y: 5.4, w: 12, text: Everything below is a domain extension, center: true}
```

`style` is one of `primary`, `accent`, `pale`, `muted`, `deep`, `green`, `purple`.

**Arrows route themselves.** Connection sites are derived from where the two shapes sit, so a
child below its parent is joined bottom-to-top and a peer beside it left-to-right, and the
connector becomes an elbow unless the shapes share a centre line. That keeps every line running
top-to-bottom or left-to-right instead of cutting diagonally across the boxes between them.
Override only when you have a reason: `from_site` and `to_site` take `0` top, `1` left, `2`
bottom, `3` right, and `kind` takes `straight` or `elbow`. `check_layout.py` rejects an override
that points an edge away from the shape it connects to, or that leaves a diagonal line.

#### `demo`

```yaml
- layout: demo
  title: "Demo — robot intent viewer, driven from an MCP client"
  state: master           # master | branch | walkthrough
  see: [...]              # what happens on screen
  parts: [...]            # the projects involved
  run: ["pwsh decks/demos/05-robot-intent-viewer-mcp/run-demo.ps1"]
  proves: One sentence tying it back to the draft.
```

`state` drives the badge: green for a demo that runs on the stack's `master`, amber for one that
needs a feature branch, grey for a walkthrough with no script yet.

`run:` lines are rendered in a monospaced panel already — give the plain command, with no wrapping
backticks. Any that slip in are stripped.

## Rules the build enforces

`--check --strict` fails when:

- a slide uses an unknown `layout`;
- a content file has no `section`;
- a content slide (anything other than `title`, `section` or `statement`) has no `notes`;
- a `table` slide is missing its columns or rows;
- a `diagram` arrow names a node that does not exist.

`check_layout.py` is separate and advisory: it estimates text overflow and reports shape overlap,
footer intrusion, title collision, degenerate shapes, and arrows that are diagonal or leave an
edge facing away from what they connect to.

## Looking at it

Geometry checks cannot tell you whether a slide *reads* well, and they cannot see a connector
routed across a box. Where PowerPoint is installed, export real renderings and look:

```powershell
.\decks\export_slides.ps1                          # every slide
.\decks\export_slides.ps1 -Slides 4,31,74          # just these
.\decks\export_slides.ps1 -Deck review.pptx -OutputDirectory $env:TEMP\review
```

PNG files land in `%TEMP%\deck-render` by default. Build to a scratch `--out` file when you are
iterating, so the committed deck only changes when you mean it to.

## Conventions

- **Every effort gets the same four beats** — *why it exists*, *what it adds*, *how it works*,
  *status and where it lives* — so the deck reads as one argument rather than eighteen.
- **Problem first.** The first slide of an effort states the gap in OPC UA, not the solution.
- **Speaker notes carry the detail.** Slides stay readable; the depth lives in the notes.
- **Say what is a draft.** Version and target body belong on the status slide of every effort.
- **A demo slide sits next to the effort it demonstrates**, not in a demo appendix.
