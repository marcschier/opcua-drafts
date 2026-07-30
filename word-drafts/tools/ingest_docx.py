"""Turn a reviewer's marked-up document back into a change to the markdown.

A reviewed `.docx` carries two kinds of intent — tracked changes and comments — and this
module routes both back to the source that owns them.

Three ideas carry the whole thing.

**Every paragraph says where it came from.** The build stamps a deterministic
`w14:paraId` on each paragraph and writes a sidecar mapping ids to source addresses.
Word preserves an id it finds, so a mark in the reviewer's copy is traceable to the
markdown that produced it without matching text or guessing at positions. A paragraph
whose id is unknown is one the reviewer created.

**Not everything is the markdown's to change.** Node tables come from the UANodeSet,
some prose is authored in the spec config, clause numbers are Word fields, and about
forty per cent of the document is the template itself. An edit to any of those is
reported, naming the artifact that really owns it. Applying it to the markdown would put
the change in a file that does not control the text, and it would be silently undone by
the next build.

**A patch that cannot be placed exactly is refused.** The rendered text a reviewer sees
is not the markdown: inline markup is gone, cross-references have become numbers,
BrowseNames have been resolved. So an edit is applied only where the text it replaces
occurs exactly once in the block's own source lines. Anything else is reported as
needing a human, which is the honest answer.
"""

import argparse
import difflib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opcdocx import contract, md_parse, review  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPECS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'specs')


class IngestError(Exception):
    """A condition that makes the whole ingest untrustworthy, not just one mark."""


# --------------------------------------------------------------------------- sources


def git_show(commit, path):
    """A file as it was at a commit, or None when it was not there."""
    try:
        out = subprocess.run(['git', '-C', REPO, 'show', '%s:%s' % (commit, path)],
                             capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.decode('utf-8')


class Sources:
    """The markdown as the reviewer read it, and as it is now.

    A reviewer works from a document that was built at some commit. If the markdown has
    moved on since, patching the current text with offsets taken from the old text would
    corrupt it, so the two are kept apart: edits are computed against the revision the
    reviewer saw, and applied to a branch based on it.

    Line endings are remembered per file and restored on write. This repository checks
    markdown out with CRLF, and a tool that quietly rewrites a whole file to LF while
    changing two words is a tool nobody will run twice.
    """

    def __init__(self, commit, paths):
        self.commit = commit
        self.at_review = {}
        self.current = {}
        self.newline = {}
        for path in paths:
            if not path.endswith('.md'):
                continue
            full = os.path.join(REPO, path)
            if os.path.exists(full):
                with open(full, 'rb') as f:
                    raw = f.read()
                self.newline[path] = '\r\n' if b'\r\n' in raw else '\n'
                self.current[path] = raw.decode('utf-8').replace('\r\n', '\n')
            old = git_show(commit, path) if commit and commit != 'unknown' else None
            self.at_review[path] = (old.replace('\r\n', '\n') if old is not None
                                    else self.current.get(path))

    def stale(self):
        return [p for p, text in self.at_review.items()
                if text is not None and self.current.get(p) != text]

    def write(self, path, text):
        """Write a file back with the line endings it had."""
        data = text.replace('\n', self.newline.get(path, '\n')).encode('utf-8')
        with open(os.path.join(REPO, path), 'wb') as f:
            f.write(data)


# --------------------------------------------------------------------------- addressing


class Address:
    """Where a paragraph of the document came from."""

    def __init__(self, para_id, raw):
        self.para_id = para_id
        self.owner = (raw or {}).get('owner', 'unknown')
        self.file = (raw or {}).get('file')
        self.section = (raw or {}).get('section')
        self.block = (raw or {}).get('block')
        self.region = (raw or {}).get('region')
        self.kind = (raw or {}).get('kind')

    def describe(self):
        if self.owner == 'markdown':
            return '%s, section %r, block %d' % (self.file, self.section, self.block)
        if self.owner == 'generated':
            return 'generated %s in region %r' % (self.kind, self.region)
        if self.owner == 'template':
            return 'a retained region of the OPC 20020 template'
        return 'an unrecognised paragraph'

    def real_owner(self, config):
        """The artifact a reviewer's edit here actually belongs in."""
        if self.owner == 'markdown':
            return self.file
        if self.owner == 'template':
            return 'templates/OPC 20020 - UA Companion Specification Template v1.01.19.docx'
        if self.kind in ('nodetable', 'enumtable', 'methodtable'):
            nodeset = (config.get('source') or {}).get('nodeset')
            return nodeset or 'the information model'
        return 'word-drafts/tools/specs/%s.json' % config['_specId']


# --------------------------------------------------------------------------- patching


class Edit:
    """One text substitution inside one source file, already located."""

    def __init__(self, path, line, before, after, *, para_id=None, author=None):
        self.path = path
        self.line = line
        self.before = before
        self.after = after
        self.para_id = para_id
        self.author = author


class Refusal:
    def __init__(self, para_id, reason, detail='', *, owner=None, author=None):
        self.para_id = para_id
        self.reason = reason
        self.detail = detail
        self.owner = owner
        self.author = author


def block_spans(text, path):
    """`(section key, block ordinal) -> (first line, last line)`, 1-based inclusive."""
    sections, order = md_parse.split_sections(text, source=path)
    parser = md_parse.BlockParser()
    spans = {}
    for key in order:
        section = sections[key]
        parser.parse(section.lines, context=section.key, source=section.source,
                     line_offset=section.start_line)
        for ordinal, span in enumerate(parser.last_spans):
            spans[(key, ordinal)] = span
    return spans


def locate(lines, span, needle):
    """Find `needle` in a block's source lines; return `(line index, column)`.

    Ambiguity is a refusal, not a coin toss: if the text a reviewer replaced occurs more
    than once inside the block there is no way to know which one they meant, and picking
    the first would corrupt the other.
    """
    hits = []
    for i in range(span[0] - 1, min(span[1], len(lines))):
        start = 0
        while True:
            at = lines[i].find(needle, start)
            if at < 0:
                break
            hits.append((i, at))
            start = at + 1
    return hits


# Two changes closer together than this are treated as one. Character-level diffing
# turns "stand-alone server" -> "standalone Server" into a deleted hyphen and a changed
# letter, and neither is findable on its own; merged and grown to whole words they are a
# single substitution that occurs exactly once.
MERGE_GAP = 16


def diff_spans(before, after):
    """The substitutions that turn one string into the other, at word granularity."""
    opcodes = [op for op in
               difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes()
               if op[0] != 'equal']
    if not opcodes:
        return []

    merged = [list(opcodes[0][1:])]
    for _tag, i1, i2, j1, j2 in opcodes[1:]:
        if i1 - merged[-1][1] <= MERGE_GAP:
            merged[-1][1], merged[-1][3] = i2, j2
        else:
            merged.append([i1, i2, j1, j2])

    out = []
    for i1, i2, j1, j2 in merged:
        left = _word_start(before, i1, after, j1)
        right = _word_end(before, i2, after, j2)
        out.append((before[i1 - left:i2 + right], after[j1 - left:j2 + right], i1 - left))
    return out


def _word_start(before, i, after, j):
    """How far left both strings can grow together without splitting a word."""
    k = 0
    while i - k > 0 and j - k > 0 and not before[i - k - 1].isspace():
        if before[i - k - 1] != after[j - k - 1]:
            break
        k += 1
    return k


def _word_end(before, i, after, j):
    k = 0
    while i + k < len(before) and j + k < len(after) and not before[i + k].isspace():
        if before[i + k] != after[j + k]:
            break
        k += 1
    return k


def plan_paragraph_edit(para, address, sources, spans_cache, report_author):
    """Work out how to make a marked-up paragraph true in the markdown.

    Returns a list of `Edit` and a list of `Refusal`.
    """
    path = address.file
    text = sources.at_review.get(path)
    if text is None:
        return [], [Refusal(para.para_id, 'source-missing',
                            'the file %s is not available at the reviewed revision' % path,
                            author=report_author)]
    lines = text.split('\n')
    spans = spans_cache.setdefault(path, block_spans(text, path))
    span = spans.get((address.section, address.block))
    if span is None:
        return [], [Refusal(para.para_id, 'block-missing',
                            'section %r block %d is not in %s at the reviewed revision'
                            % (address.section, address.block, path),
                            author=report_author)]

    edits, refusals = [], []
    for before, after, start in diff_spans(para.rejected, para.accepted):
        needle, replacement = _widen(para.rejected, para.accepted, before, after, start)
        if not needle:
            refusals.append(Refusal(
                para.para_id, 'no-anchor',
                'the change adds text with nothing before it to anchor to',
                author=report_author))
            continue
        hits = locate(lines, span, needle)
        if len(hits) != 1:
            refusals.append(Refusal(
                para.para_id,
                'not-found' if not hits else 'ambiguous',
                'the text %r %s in the markdown for this paragraph, so the change '
                'cannot be placed exactly' % (
                    _clip(needle),
                    'does not appear' if not hits else 'appears %d times' % len(hits)),
                author=report_author))
            continue
        line, _col = hits[0]
        edits.append(Edit(path, line, needle, replacement,
                          para_id=para.para_id, author=report_author))
    return edits, refusals


def _widen(rejected, accepted, before, after, start):
    """Give a pure insertion something to anchor to.

    An insertion has nothing to replace, so it is turned into a substitution of the text
    immediately before it. Twenty-odd characters is enough to be unique inside one
    paragraph and short enough to survive markup, which is the balance that matters.
    """
    if before:
        return before, after
    lead = rejected[max(0, start - 24):start]
    lead = lead.lstrip()
    if not lead:
        return '', ''
    return lead, lead + after


def _clip(s, n=48):
    s = ' '.join(s.split())
    return s if len(s) <= n else s[:n - 1] + '…'


def apply_edits(text, edits):
    """Apply located edits to one file's text, later lines first.

    Applying from the bottom up keeps every not-yet-applied line number valid, the same
    reason the forward build edits the template body bottom-up.
    """
    lines = text.split('\n')
    for edit in sorted(edits, key=lambda e: e.line, reverse=True):
        line = lines[edit.line]
        if line.count(edit.before) != 1:
            raise IngestError('edit no longer applies at %s:%d' % (edit.path, edit.line + 1))
        lines[edit.line] = line.replace(edit.before, edit.after, 1)
    return '\n'.join(lines)


# --------------------------------------------------------------------------- comments


class Note:
    """A comment, resolved to a place in the source."""

    def __init__(self, comment, address, path=None, line=None, owner=None):
        self.comment = comment
        self.address = address
        self.path = path
        self.line = line
        self.owner = owner


def place_comment(comment, address, sources, spans_cache):
    """The source line a comment is about, as precisely as the anchor allows."""
    path = address.file
    text = sources.at_review.get(path)
    if text is None:
        return None, None
    lines = text.split('\n')
    spans = spans_cache.setdefault(path, block_spans(text, path))
    span = spans.get((address.section, address.block))
    if span is None:
        return path, None
    anchor = ' '.join((comment.anchor or '').split())
    if anchor:
        hits = locate(lines, span, anchor)
        if len(hits) == 1:
            return path, hits[0][0] + 1
    return path, span[0]


# --------------------------------------------------------------------------- ingest


class Ingest:
    def __init__(self, docx_path, *, spec_id=None):
        self.doc = review.ReviewedDocument(docx_path)
        self.docx_path = docx_path
        props = self.doc.properties
        self.spec_id = spec_id or props.get('SpecId')
        if not self.spec_id:
            raise IngestError(
                'the document records no SpecId, so there is no way to tell which '
                'specification it is. It was probably built before the pipeline started '
                'stamping documents; rebuild and re-review.')
        if props.get('PipelineVersion') not in (None, contract.PIPELINE_VERSION):
            raise IngestError(
                'the document was built by pipeline version %s, this is version %s. '
                'Paragraph identity may mean something different; rebuild and re-review.'
                % (props.get('PipelineVersion'), contract.PIPELINE_VERSION))

        config_path = os.path.join(SPECS, self.spec_id + '.json')
        if not os.path.exists(config_path):
            raise IngestError('no build config for %r' % self.spec_id)
        with open(config_path, encoding='utf-8') as f:
            self.config = json.load(f)
        self.config['_specId'] = self.spec_id

        self.commit = props.get('SourceCommit') or 'unknown'
        self.provenance = self._load_provenance()
        self.sources = Sources(self.commit, self.provenance.get('sources') or [])
        self.addresses = {pid: Address(pid, raw)
                          for pid, raw in (self.provenance.get('paragraphs') or {}).items()}

        self.edits = []
        self.refusals = []
        self.notes = []
        self.unverified = []
        self._spans = {}

    def _load_provenance(self):
        rel = os.path.splitext(self.config['output']['docmodel'])[0]
        rel = rel.replace('.docmodel', '') + '.provenance.json'
        raw = git_show(self.commit, rel) if self.commit != 'unknown' else None
        if raw is None:
            full = os.path.join(REPO, rel)
            if not os.path.exists(full):
                raise IngestError(
                    'no provenance sidecar for this document, at %s or at commit %s. '
                    'Without it a mark cannot be traced to its source.'
                    % (rel, self.commit[:12]))
            with open(full, encoding='utf-8') as f:
                raw = f.read()
        return json.loads(raw)

    # ------------------------------------------------------------------ the work

    def run(self):
        for para in self.doc.paragraphs:
            if not para.changed:
                continue
            author = para.revisions[0].author if para.revisions else None
            address = self.addresses.get(para.para_id)
            if address is None:
                self.refusals.append(Refusal(
                    para.para_id, 'new-paragraph',
                    'a paragraph the reviewer created; there is no source line to change, '
                    'so where it belongs is an editorial decision',
                    owner=None, author=author))
                continue
            if address.owner != 'markdown':
                self.refusals.append(Refusal(
                    para.para_id, 'not-markdown',
                    'the text is %s' % address.describe(),
                    owner=address.real_owner(self.config), author=author))
                continue
            edits, refusals = plan_paragraph_edit(para, address, self.sources,
                                                  self._spans, author)
            self.edits.extend(edits)
            self.refusals.extend(refusals)

        for comment in self.doc.comments:
            address = self.addresses.get(comment.para_id)
            if address is None:
                self.notes.append(Note(comment, None, owner='unknown'))
                continue
            if address.owner != 'markdown':
                self.notes.append(Note(comment, address,
                                       owner=address.real_owner(self.config)))
                continue
            path, line = place_comment(comment, address, self.sources, self._spans)
            self.notes.append(Note(comment, address, path=path, line=line,
                                   owner='markdown'))
        return self

    def patched(self):
        """`path -> new text` for every file this ingest changes."""
        by_path = {}
        for edit in self.edits:
            by_path.setdefault(edit.path, []).append(edit)
        return {path: apply_edits(self.sources.at_review[path], edits)
                for path, edits in by_path.items()}

    def verify(self, template=None):
        """Rebuild from the patched markdown and check the reviewer's intent survived.

        Every earlier step is an argument that the change is right. This is the only one
        that checks: with the edits applied, the paragraphs the reviewer changed must now
        read the way they wanted them to. A paragraph that does not is an edit that was
        applied to the wrong place, or applied and then undone by the rendering — and it
        is reported rather than shipped, because the whole point of the pipeline is that
        the document and the source cannot disagree.

        Returns the list of paragraphs whose accepted text the rebuild did not reproduce.
        """
        if not self.edits:
            return []
        rebuilt = self._rebuild_with_patch(template)
        applied = {e.para_id for e in self.edits}
        missed = []
        for para in self.doc.paragraphs:
            if para.para_id not in applied:
                continue
            now = rebuilt.get(para.para_id)
            if now is None or _norm(now) != _norm(para.accepted):
                missed.append((para, now))
        return missed

    def _rebuild_with_patch(self, template=None):
        """Rebuild with the edits in place, then put the working tree back as it was."""
        patched = self.patched()
        stash = {}
        try:
            for path, text in patched.items():
                full = os.path.join(REPO, path)
                with open(full, 'rb') as f:
                    stash[full] = f.read()
                self.sources.write(path, text)
            return self._rebuild(template)
        finally:
            for full, raw in stash.items():
                with open(full, 'wb') as f:
                    f.write(raw)

    def _rebuild(self, template=None):
        """`paraId -> text` from a fresh build of the current working tree."""
        import build_docx
        import render_docx

        build = build_docx.Build(os.path.join(SPECS, self.spec_id + '.json'))
        doc = build.build_docmodel()
        out = os.path.join(REPO, 'word-drafts', '.ingest-verify.docx')
        try:
            render_docx.render(build, doc, template or build_docx.TEMPLATE, out)
            verify = review.ReviewedDocument(out)
        finally:
            if os.path.exists(out):
                os.remove(out)
        return {p.para_id: p.accepted for p in verify.paragraphs if p.para_id}

    # ------------------------------------------------------------------ reporting

    def report(self):
        lines = []
        add = lines.append
        authors = self.doc.authors()
        add('Ingested from `%s`.' % os.path.basename(self.docx_path))
        add('')
        add('| | |')
        add('|---|---|')
        add('| Specification | `%s` |' % self.spec_id)
        add('| Built from | `%s` |' % self.commit[:12])
        add('| Reviewers | %s |' % (', '.join(authors) or '—'))
        add('| Tracked changes | %d, in %d paragraph(s) |'
            % (len(self.doc.revisions),
               sum(1 for p in self.doc.paragraphs if p.changed)))
        add('| Comments | %d |' % len(self.doc.comments))
        add('| Applied | %d edit(s) across %d file(s) |'
            % (len(self.edits), len({e.path for e in self.edits})))
        add('| Not applied | %d |' % len(self.refusals))
        add('| Round trip | %s |' % (
            'not run' if self.unverified is None else
            'every applied edit reads as the reviewer wrote it' if not self.unverified
            else '**%d applied edit(s) did not survive a rebuild**' % len(self.unverified)))
        add('')

        stale = self.sources.stale()
        if stale:
            add('> [!NOTE]')
            add('> The markdown has moved on since this document was built. The changes '
                'below are computed against `%s`, the revision the reviewer read, so '
                'they may need rebasing: %s.'
                % (self.commit[:12], ', '.join('`%s`' % s for s in stale)))
            add('')

        if self.edits:
            add('## Applied')
            add('')
            for edit in self.edits:
                add('- `%s:%d` — %s' % (edit.path, edit.line + 1,
                                        _change_phrase(edit)))
            add('')

        routed = [r for r in self.refusals if r.owner]
        unplaced = [r for r in self.refusals if not r.owner]
        if routed:
            add('## Not applied — the markdown does not own this text')
            add('')
            add('These marks are real, and they are in the wrong file to act on. Each one '
                'names the artifact that does own the text.')
            add('')
            add('| Paragraph | Belongs in | What was marked |')
            add('|---|---|---|')
            for r in routed:
                add('| `%s` | `%s` | %s |' % (r.para_id, r.owner, r.detail))
            add('')
        if unplaced:
            add('## Not applied — needs a human')
            add('')
            for r in unplaced:
                add('- `%s` (%s) — %s' % (r.para_id, r.reason, r.detail))
            add('')

        if self.unverified:
            add('## Applied, but the rebuild does not agree')
            add('')
            add('The edit went in and the regenerated document still does not read the '
                'way the reviewer wrote it. Treat these as unapplied.')
            add('')
            for para, now in self.unverified:
                add('- `%s`' % para.para_id)
                add('  - wanted: %s' % _code(para.accepted, 200))
                add('  - got: %s' % (_code(now, 200) if now else '_paragraph is gone_'))
            add('')

        if self.notes:
            placed = [n for n in self.notes if n.owner == 'markdown']
            elsewhere = [n for n in self.notes if n.owner != 'markdown']
            if placed:
                add('## Comments')
                add('')
                for note in placed:
                    where = ('`%s:%s`' % (note.path, note.line)
                             if note.path and note.line else '_unplaced_')
                    add('- %s — **%s**: %s'
                        % (where, note.comment.author, _clip(note.comment.body, 120)))
                add('')
            if elsewhere:
                add('## Comments on text the markdown does not own')
                add('')
                add('Worth reading, but the change they ask for would not be made here.')
                add('')
                add('| Belongs in | Anchored to | Comment |')
                add('|---|---|---|')
                for note in elsewhere:
                    add('| `%s` | %s | **%s**: %s |'
                        % (note.owner or 'unknown',
                           _code(note.comment.anchor or '(whole paragraph)'),
                           note.comment.author, _clip(note.comment.body, 100)))
                add('')
        return '\n'.join(lines).rstrip() + '\n'


def _norm(s):
    """Compare what a reader sees: whitespace runs are not meaningful differences."""
    return ' '.join((s or '').split())


def _change_phrase(edit):
    if edit.after.startswith(edit.before):
        return 'inserted %s' % _code(edit.after[len(edit.before):])
    if not edit.after:
        return 'deleted %s' % _code(edit.before)
    return '%s → %s' % (_code(edit.before), _code(edit.after))


def _code(s, n=48):
    return '`%s`' % _clip(s, n).replace('`', "'")


# --------------------------------------------------------------------------- cli


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('docx', help='the reviewed document')
    ap.add_argument('--spec', default=None,
                    help='override the SpecId recorded in the document')
    ap.add_argument('--write', action='store_true',
                    help='write the patched markdown into the working tree')
    ap.add_argument('--no-verify', action='store_true',
                    help='skip the rebuild that checks the edits really took effect')
    ap.add_argument('--report', default=None, help='write the report to this file')
    ap.add_argument('--pr', action='store_true',
                    help='open a pull request and post the comments as a review')
    ap.add_argument('--base', default='main', help='the branch the pull request targets')
    ap.add_argument('--draft', action='store_true', help='open the pull request as a draft')
    ap.add_argument('--dry-run', action='store_true',
                    help='with --pr, print what would be published and change nothing')
    args = ap.parse_args(argv)

    try:
        ingest = Ingest(args.docx, spec_id=args.spec).run()
        if args.no_verify:
            ingest.unverified = None
        else:
            ingest.unverified = ingest.verify()
    except IngestError as exc:
        print('cannot ingest: %s' % exc)
        return 2

    report = ingest.report()
    print(report)
    if args.report:
        with open(args.report, 'w', encoding='utf-8', newline='\n') as f:
            f.write(report)

    if ingest.unverified and args.pr:
        print('refusing to open a pull request: %d applied edit(s) did not survive a '
              'rebuild. Fix those first, or re-run with --no-verify to publish anyway.'
              % len(ingest.unverified))
        return 3

    if args.write:
        for path, text in ingest.patched().items():
            ingest.sources.write(path, text)
            print('wrote %s' % path)

    if args.pr:
        from opcdocx import github_review
        try:
            plan = github_review.publish(ingest, repo_root=REPO, base=args.base,
                                         draft=args.draft, dry_run=args.dry_run)
        except github_review.GitHubError as exc:
            print('cannot publish: %s' % exc)
            return 4
        print(json.dumps(plan, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
