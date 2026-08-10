# `decks/` — the drafts overview deck

One deck covers **every** effort in this repository: the drafts in `core-specs/`, `cloud-specs/`,
`metaverse-specs/`, `wot-specs/` and `companion-specs/`, together with the ten demos that show them
running on the [OPC UA .NET Standard stack](https://github.com/OPCFoundation/UA-.NETStandard).

| | |
|---|---|
| Deck | [`OPC-UA-Drafts-Overview.pptx`](OPC-UA-Drafts-Overview.pptx) |
| Slide source | [`content/`](content/) — one YAML file per effort, one per demo |
| Generator | [`build_deck.py`](build_deck.py) (structure) and [`theme.py`](theme.py) (look) |
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

## Content model

Every file under `content/` is one YAML document describing a run of slides:

```yaml
id: core-01-data-channels          # stable identifier, matches the file name
section: core                      # core | cloud | metaverse | wot | companion | front | close
order: 110                         # global sort key; files are emitted in ascending order
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
| 200–299 | `cloud` |
| 300–399 | `metaverse` |
| 400–499 | `wot` |
| 500–599 | `companion` |
| 900+ | closing |

Within a range, each effort gets a block of ten (`110`, `120`, …) and its slides step by one.
A demo slide uses the order immediately after the effort's last slide.

### Inline formatting

`**bold**` and `` `code` `` work inside any text field.

> **YAML gotcha.** A backtick is a reserved indicator in YAML and cannot *begin* a plain scalar.
> Quote any value that starts with one — `text: "`FolderType` is the projection"` — or put a word
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
    - {from: reg, to: sr, label: subtypes}
  captions:
    - {x: 0, y: 5.4, w: 12, text: Everything below is a domain extension, center: true}
```

`style` is one of `primary`, `accent`, `pale`, `muted`, `deep`, `green`, `purple`.
Arrow endpoints attach to connection sites `0` top, `1` left, `2` bottom, `3` right — set with
`from_site` and `to_site`.

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

## Conventions

- **Every effort gets the same four beats** — *why it exists*, *what it adds*, *how it works*,
  *status and where it lives* — so the deck reads as one argument rather than eighteen.
- **Problem first.** The first slide of an effort states the gap in OPC UA, not the solution.
- **Speaker notes carry the detail.** Slides stay readable; the depth lives in the notes.
- **Say what is a draft.** Version and target body belong on the status slide of every effort.
- **A demo slide sits next to the effort it demonstrates**, not in a demo appendix.
