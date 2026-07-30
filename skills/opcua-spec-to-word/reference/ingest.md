# Ingesting a reviewed document

The pipeline runs both ways. A reviewer marks up the generated `.docx` in Word — tracked
changes and comments — and `ingest_docx.py` turns that into a pull request whose diff is
their changes and whose review carries their comments.

The value is not the automation. It is that a reviewer who has Word and no git can
contribute without anyone re-typing their edits, and without their comment landing three
paragraphs from where they meant it.

## The one idea everything rests on

**Every paragraph carries the address of the source that produced it.**

The forward build derives a `w14:paraId` from `(spec, source file, section key, block
ordinal)` instead of letting Word invent one, and writes a `*.provenance.json` sidecar
mapping ids to addresses. Two properties make this work:

- **Word preserves an id it finds.** It only assigns one where none exists. Measured on a
  real round trip: all 1255 build-assigned ids survived an edit-and-save intact, and the
  200 ids Word added were on paragraphs the *template* had left unstamped.
- **An unknown id is therefore a new paragraph** — one the reviewer created. That is a
  fact, not an inference.

The address is an ordinal, not a line number, deliberately. A line number churns whenever
anything above it moves, which would make the committed sidecar unreadable as a diff and
would break the moment a reviewer's copy was one commit stale.

### Things that look equivalent and are not

- **Do not match on text.** It fails exactly where it matters: on the paragraphs the
  reviewer changed.
- **Do not rely on document order.** It fails as soon as the reviewer inserts a paragraph.
- **Do not stamp `HEAD` as the source commit.** Every document's bytes would change on
  every unrelated commit, so a rebuild would never be a no-op and real changes could not
  be told from noise. Stamp *the last commit that touched this document's inputs*, which
  is stable and is also the revision the reviewer was actually reading.
- **Seed the id generator with the template's own ids.** The template is a real Word
  document; its retained paragraphs already carry `w14:paraId`. A generated id that
  collides with one makes two paragraphs indistinguishable.
- **Build the sidecar by walking the saved package, not the writer's intent.** Blocks get
  rendered for regions that are then not inserted. The sidecar has to describe the
  document the reviewer will open.

## Ownership routing

Only the first row can be acted on. The rest are reported, naming the artifact that really
owns the text — because applying a change to a file that does not control the words is
worse than not applying it, and it would be silently undone by the next build.

| Marked content | Owner | Action |
|---|---|---|
| Prose rendered from markdown | that `.md` | apply |
| Prose from a folded annex | its `additionalMarkdown` source | apply, to the right file |
| Clause 4.1, use cases, Annex A identity | `tools/specs/<spec>.json` | report |
| Node tables, conformance-unit tables | the UANodeSet / `build_model.py` | report as a model change request |
| Clause and caption numbers, cross-references | Word fields | reject — numbering is not authored |
| Retained template regions | the OPC 20020 template | reject, and flag as a deviation |

The routing falls out of the provenance rather than being guessed at: a block with a `src`
came from markdown, a `nodetable` block came from the model, an id the writer never issued
came from the template.

## Placing a change in the source

The text a reviewer sees is not the markdown. Inline markup is gone, cross-references have
become numbers, BrowseNames have been resolved. So the rule is:

> Apply an edit only where the text it replaces occurs **exactly once** in that
> paragraph's own source lines.

Zero occurrences or more than one is a refusal with a reason, not a coin toss. Two details
make this work in practice rather than in principle:

- **Diff at word granularity, not character granularity.** Character diffing turns
  `stand-alone server` → `standalone Server` into a deleted hyphen and a changed letter,
  and neither is findable on its own. Merge changes closer together than ~16 characters
  and grow each span to whole-word boundaries in both strings; the result is one
  substitution that occurs exactly once.
- **A pure insertion has nothing to replace**, so give it the ~24 characters before it as
  an anchor and rewrite it as a substitution.

Apply edits bottom-up within a file, for the same reason the forward build edits the
template body bottom-up: every not-yet-applied position stays valid.

Preserve line endings. This repository checks markdown out with CRLF, and a tool that
rewrites a whole file to LF while changing two words is a tool nobody runs twice.

## The gate

Patch the markdown, rebuild the document, and require that **every applied edit now reads
the way the reviewer wrote it**. One that does not is reported as unapplied and blocks the
pull request.

This is the only step that checks rather than argues, and it is the same discipline as the
rest of the pipeline: check the printed form, because both sides can agree on the same
wrong thing. Give it a test that fails when it stops working — plant an edit that changes
a different paragraph and confirm the gate notices.

## Publishing, and the constraint that shapes it

**The GitHub REST API will not attach an inline review comment to a line that is not part
of the diff.** The web interface allows it; the API answers `422 line must be part of the
diff`. There is no workaround, so the comments are tiered:

| Anchor | Vehicle |
|---|---|
| A line the same review changed | a real inline comment, with Word's threads posted as `in_reply_to` replies |
| An unchanged line | collected into the review body with a `blob/<sha>/file.md#L12-L14` permalink, which GitHub renders as a quoted snippet |
| Generated or template content | a separate section — the change it asks for would not be made here |

Do not fabricate an edit to host a comment. The diff would claim a change nobody asked
for, which is a worse lie than "this comment is on an unchanged line".

One commit per reviewer, with `Co-authored-by`, so `git log` and `git blame` attribute the
words to whoever wrote them. Apply each reviewer's edits cumulatively — two people may have
marked up the same file, and the second commit must build on the first rather than revert
it. A conflict then surfaces as *"edit no longer applies"*, which is the correct outcome.

**Work everything out before switching revisions.** Publishing checks out the commit the
reviewed document was built from, and that commit may predate the ingest tool itself. A
lazy `import` after the checkout looks for a file that does not exist yet, and anything
else computed afterwards is computed against the wrong repository. Compute the patches
first, hand them over, and let the publishing step know only about `git` and `gh`.

## Testing without Word

The reader is tested against **synthetic WordprocessingML** so it runs in CI, and the
shapes were taken from a document Word actually produced rather than invented.
`make_review_fixture.ps1` drives Word to produce the real thing locally, taking
`find=>replace` and `find=>comment` instructions so the marks land on text you chose.

Two traps in that script, both found the hard way:

- **Do not match paragraphs by style name.** `Style.NameLocal` is not the styleId, so
  `-eq 'PARAGRAPH'` silently matches nothing and the fixture comes out empty. Locate text
  with `Find` instead.
- **Invoking `pwsh script.ps1 -Edits $array` re-parses the arguments** and the array
  arrives as loose positional tokens. Call the script with `&` in the current session.

The template ships **one comment of its own** — Randy Armstrong, 2019, "This figure is an
embedded Visio object." Exclude it by identity, or every ingest reports it as new feedback.

## Where the mechanical part ends

The ingest is narrow on purpose, and that leaves a remainder: comments state a problem
rather than supplying replacement text, some marks belong in the information model, and an
edit is sometimes unplaceable because the prose around it was rewritten. That remainder is
work of a different kind, not a failure, and it goes to a coding agent.

Two rules keep the two halves from fighting:

- **The agent gets the report, not the document.** It cannot then revert or re-apply the
  exact edits the ingest already made, because it never sees them as marks.
- **Changing nothing is a stated, valid outcome.** The branch already carries the reviewer's
  marks; a guessed interpretation on top of them is worse than none.

Mechanical where it is exact, agentic where it needs judgement, and never both on the same
text.

In GitHub Actions the agent runs as Copilot CLI — `npm install -g @github/copilot`, then
`copilot --yolo -p "…"` — authenticated by the **built-in token** with
`permissions: copilot-requests: write`. No stored secret. GitHub documents that path for
organization-owned repositories, so on a user-owned one it may be refused; the workflow
therefore uses a `COPILOT_GITHUB_TOKEN` secret when one exists and says which it used, so
switching over is a secret rather than an edit. Note that `copilot-requests` is newer than
actionlint's built-in scope list, so the linter reports it as unknown — that is a false
positive, and CI ignores exactly that message and nothing else.

Two things are worth enforcing in the workflow rather than asking for in the prompt: revert
any edit to a generated artifact before committing, since the next build would discard it
silently anyway; and refuse to run on any branch outside a known agent prefix. A prompt is
a wish; a workflow step is a rule.

## What CI cannot do

`build_all.py` is pure Python and runs anywhere, so a hosted runner can regenerate every
document — but it **cannot finish one**. Resolving the table of contents and the
cross-references needs Microsoft Word.

That asymmetry has a clean resolution, because verifying finalisation needs no Word at all:
a finalised document carries one cached `PAGEREF` per contents entry and a fresh build
carries none. So the regeneration pull request opens as a **draft**, and CI flips it to
ready for review once `validate_docx.py --finalized` passes. The draft state *is* the
message, and it cannot be forgotten the way a note in a pull request body can.
