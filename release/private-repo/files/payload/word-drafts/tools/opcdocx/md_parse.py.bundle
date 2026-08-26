"""Markdown -> docmodel.

Only the constructs the specification drafts actually use are supported; anything else
raises, because silently dropping content from a specification is worse than failing the
build. Section references (`§7.4.2`) become `xref` runs so the Word writer can emit a REF
field over a bookmark and let Word supply the live clause number.
"""

import re

from . import contract
from . import docmodel as dm

HEADING_RE = re.compile(r'^(#{1,6})\s+(.*?)\s*$')
FENCE_RE = re.compile(r'^```\s*([A-Za-z0-9_+-]*)\s*$')
BULLET_RE = re.compile(r'^(\s*)[-*]\s+(.*)$')
ORDERED_RE = re.compile(r'^(\s*)(\d+)\.\s+(.*)$')
TABLE_SEP_RE = re.compile(r'^\|[\s:\-|]+\|$')
HRULE_RE = re.compile(r'^-{3,}\s*$')
BLOCKQUOTE_RE = re.compile(r'^>\s?(.*)$')

# `§5.15.3`, `§5.15`, `§7` and the "Part 1 §5.15" form used across the sibling drafts.
SECTION_REF_RE = re.compile(r'§\s*([0-9]+(?:\.[0-9]+)*)')

# Some drafts spell a cross-reference out as "Section 9.2", "clause 9.2" or
# "Sections 9.2 and 10.1" instead of using §. Those are references too, and a
# build that did not recognise them
# shipped a document whose every cross-reference still pointed at the source document's
# pre-restructure numbering.
WORD_REF_RE = re.compile(
    r'(?P<word>\b(?:Sections?|clauses?)\s+)'
    r'(?P<num>[0-9]+(?:\.[0-9]+)*)(?!\.?[0-9])(?![A-Za-z])',
    re.IGNORECASE)

# A list form: "Sections 9.2 and 10.1", "Sections 5, 6, and 10". Every number in the list
# is a reference; rewriting only the first would leave the rest pointing at the source
# document's own numbering.
_NUM = r'[0-9]+(?:\.[0-9]+)*'
WORD_REF_LIST_RE = re.compile(
    r'\b(?:Sections?|clauses?)\s+' + _NUM
    + r'(?:(?:,\s+and\s+|,\s+|\s+(?:and|to)\s+|\s*[\u2013\u2014-]\s*)'
    + _NUM + r')*(?!\.?[0-9])(?![A-Za-z])',
    re.IGNORECASE)

_MARKUP_IN_LABEL_RE = re.compile(r'[`*]')

_INLINE_RE = re.compile(
    r'(?P<code>`[^`]+`)'
    r'|(?P<bold>\*\*(?:[^*]|\*(?!\*))+\*\*)'
    r'|(?P<italic>(?<!\*)\*(?!\*)(?:[^*]+)\*(?!\*))'
    r'|(?P<link>\[[^\]]+\]\([^)]+\))'
    r'|(?P<ref>§\s*[0-9]+(?:\.[0-9]+)*)'
    r'|(?P<wordref>' + WORD_REF_LIST_RE.pattern + r')'
)


_NUM = r'[0-9]+(?:\.[0-9]+)*'

# A reference qualified by another document belongs to that document, and resolving it
# through this document's clause map corrupts it: "OPC 10000-6 Section 5.1.1" is a clause
# of Part 6, not of the document being built. The window is bounded so that a qualifier
# earlier in the same sentence does not mask a genuine self-reference.
# The gap between a qualifier and the reference it governs: the rest of the same sentence.
# It may contain *other* references to the same document — "the Part 6 errata §5.13 … and
# §5.14" is one sentence citing one document twice — so a gap that forbade the section sign
# recognised only the first of a list. A sentence end is a period followed by whitespace,
# which is not the period inside §5.13.
_QUALIFIER_GAP = (r'(?:(?!\.\s)[^\u00a7\n]|\u00a7\s*[0-9][0-9.]*\s*(?:,|and|to|;)?\s*)'
                  r'{0,300}')

FOREIGN_QUALIFIER_RE = re.compile(
    r'(?:OPC\s*\d{4,5}|IEC\s*\d+|RFC\s*\d+|W3C|AOUSD|xRegistry'
    r'|WoT\s+Binding|WoT-Binding|Thing\s+Description\s+1\.1'
    r'|Part\s*\d+|\bthe base\b|\bbase(?: (?:spec|specification|model))?\b'
    r'|\*[^*]*OPC UA[^*]*\*)'
    + _QUALIFIER_GAP + r'$', re.IGNORECASE)


_LINK_TARGET_RE = re.compile(r'\]\([^)]*\)')


def _is_foreign(text, start, extra=None, end=None):
    window = text[max(0, start - 260):start]
    # A markdown link's URL is invisible to the reader but counts against the distance
    # between the qualifier and the reference, and a single reference.opcfoundation.org
    # URL is long enough on its own to hide "OPC 10000-3" from the window.
    window = _LINK_TARGET_RE.sub('', window).replace('[', '')
    if extra is not None and extra.search(window):
        return True
    if end is not None and extra is not None:
        after = text[end:end + 140]
        sentence_tail = re.split(r'\.\s', after, maxsplit=1)[0].rstrip('.')
        if (re.match(r'^\s+(?:of|in)\s+(?:the\s+)?',
                     sentence_tail, re.IGNORECASE)
                and extra.search(sentence_tail)):
            return True
    return bool(FOREIGN_QUALIFIER_RE.search(window))


def foreign_anchor_re(anchors):
    """A qualifier pattern for the names this document uses for other documents.

    The built-in list only knows standards bodies and part numbers. A draft cites its
    siblings by nickname — "the Bindings spec", "the primer" — and a reference anchored
    on one of those belongs to that document, not this one.
    """
    if not anchors:
        return None
    alt = '|'.join(re.escape(a) for a in anchors)
    return re.compile(r'(?:' + alt + r')' + _QUALIFIER_GAP + r'$', re.IGNORECASE)


class Section:
    """One markdown heading and the blocks under it, excluding nested subsections.

    `source` and `start_line` are the section's address in the repository. They are not
    written into the docmodel — a line number churns whenever anything above it moves,
    which would swamp the semantic diff the docmodel exists to provide — but they let a
    caller resolve a block back to the lines it came from, which is what turns a
    reviewer's edit in Word into an edit in the markdown.
    """

    def __init__(self, level, title, key, *, source=None, start_line=1):
        self.level = level
        self.title = title
        self.key = key
        self.source = source
        self.start_line = start_line
        self.lines = []

    def __repr__(self):
        return 'Section(%d, %r, %d lines)' % (self.level, self.key, len(self.lines))


def split_sections(text, source=None):
    """Split a markdown document into an ordered mapping of `key -> Section`.

    The key is the heading text with markdown emphasis intact, matching the `from`
    values in the build config so a human can read the mapping against the source.
    """
    sections = {}
    order = []
    preamble = Section(0, '', '__preamble__', source=source, start_line=1)
    sections['__preamble__'] = preamble
    order.append('__preamble__')
    current = preamble
    for lineno, line in enumerate(text.splitlines(), start=1):
        m = HEADING_RE.match(line)
        if m and not _in_fence(current.lines):
            level = len(m.group(1))
            title = m.group(2)
            key = title
            if key in sections:
                raise ValueError('duplicate heading: %r' % key)
            current = Section(level, title, key, source=source, start_line=lineno + 1)
            sections[key] = current
            order.append(key)
            continue
        current.lines.append(line)
    return sections, order


def _in_fence(lines):
    """True when the accumulated lines end inside an open code fence."""
    open_fence = False
    for ln in lines:
        if FENCE_RE.match(ln):
            open_fence = not open_fence
    return open_fence


# --------------------------------------------------------------------------- inline


def parse_inline(text, *, xref_resolver=None, foreign_anchors=None):
    """Inline markdown -> docmodel runs."""
    runs = []
    pos = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > pos:
            runs.append(dm.t(_unescape(text[pos:m.start()])))
        if m.group('code'):
            runs.append(dm.code(m.group('code')[1:-1]))
        elif m.group('bold'):
            runs.extend(_styled(m.group('bold')[2:-2], xref_resolver, foreign_anchors,
                                b=True))
        elif m.group('italic'):
            runs.extend(_styled(m.group('italic')[1:-1], xref_resolver, foreign_anchors,
                                i=True))
        elif m.group('link'):
            label, _, href = m.group('link')[1:-1].partition('](')
            if href.startswith(contract.FORBIDDEN_LINK_HOSTS) or any(
                    host in href for host in contract.FORBIDDEN_LINK_HOSTS):
                # Guideline 5 forbids a link into the online reference anywhere but
                # Annex A. The citation is what matters, so the link is dropped and its
                # label kept — including any code formatting inside it.
                runs.extend(parse_inline(label, xref_resolver=xref_resolver,
                                         foreign_anchors=foreign_anchors))
            elif _MARKUP_IN_LABEL_RE.search(label):
                # A label such as [`WoTRegistryType`](#type-WoTRegistryType) carries its
                # own inline markup. Emitting it as one plain run put the backticks into
                # the document; the writer drops the href for every link anyway, so the
                # label is parsed and its formatting kept.
                runs.extend(parse_inline(label, xref_resolver=xref_resolver,
                                         foreign_anchors=foreign_anchors))
            else:
                runs.append(dm.link(_unescape(label), href))
        elif m.group('ref'):
            number = SECTION_REF_RE.match(m.group('ref')).group(1)
            resolved = (xref_resolver(number)
                        if xref_resolver and not _is_foreign(
                            text, m.start(), foreign_anchors, m.end())
                        else None)
            if resolved:
                target, label = resolved
                runs.append(dm.xref(target, kind='clause', prefix=label))
            else:
                runs.append(dm.t(m.group('ref')))
        elif m.group('wordref'):
            resolver = (None if _is_foreign(
                            text, m.start(), foreign_anchors, m.end())
                        else xref_resolver)
            runs.extend(_word_reference_runs(m.group('wordref'), resolver))
        pos = m.end()
    if pos < len(text):
        runs.append(dm.t(_unescape(text[pos:])))
    return [r for r in runs if r.get('text') != '' or r.get('r') != 't']


def _unescape(s):
    return s.replace('\\|', '|').replace('\\*', '*').replace('\\_', '_')


def _styled(text, xref_resolver, foreign_anchors, *, b=False, i=False):
    """Emphasised text, with the inline markup inside it still parsed.

    Bold and italic used to be emitted as a single plain run, so a code span, a link or a
    section reference written inside them reached the document as literal markdown. It is
    not a rare construct — `**the `EngineType` component**` is ordinary prose in these
    drafts — and it left stray backticks in every document built before this.
    """
    out = []
    for run in parse_inline(text, xref_resolver=xref_resolver,
                            foreign_anchors=foreign_anchors):
        if run.get('r') == 't':
            run = dict(run)
            if b:
                run['b'] = True
            if i:
                run['i'] = True
        out.append(run)
    return out


def _word_reference_runs(text, xref_resolver):
    """`Sections 9.2 and 10.1` -> a cross-reference per number, separators preserved.

    The leading word is kept ("Clause"/"Clauses" in template style is left to the source
    document); only the numbers become fields, so a reader still reads a sentence and
    Word still renumbers the targets.
    """
    runs = []
    pos = 0
    for m in re.finditer(_NUM + r'(?!\.?[0-9])', text):
        if m.start() > pos:
            runs.append(dm.t(text[pos:m.start()]))
        resolved = xref_resolver(m.group(0)) if xref_resolver else None
        if resolved:
            target, label = resolved
            runs.append(dm.xref(target, kind='clause', prefix=label))
        else:
            runs.append(dm.t(m.group(0)))
        pos = m.end()
    if pos < len(text):
        runs.append(dm.t(text[pos:]))
    return runs


def _split_row(raw):
    """Split a markdown table row, honouring escaped pipes."""
    inner = raw.strip()
    if inner.startswith('|'):
        inner = inner[1:]
    if inner.endswith('|'):
        inner = inner[:-1]
    cells = []
    buf = []
    i = 0
    while i < len(inner):
        ch = inner[i]
        if ch == '\\' and i + 1 < len(inner):
            buf.append(inner[i:i + 2])
            i += 2
            continue
        if ch == '|':
            cells.append(''.join(buf).strip())
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    cells.append(''.join(buf).strip())
    return cells


# --------------------------------------------------------------------------- blocks


class BlockParser:
    def __init__(self, *, xref_resolver=None, table_captions=None,
                 foreign_anchors=None):
        self.xref_resolver = xref_resolver
        self.foreign_anchors = foreign_anchors
        self.table_captions = table_captions or {}
        self.last_spans = []

    def inline(self, text):
        return parse_inline(text, xref_resolver=self.xref_resolver,
                            foreign_anchors=self.foreign_anchors)

    def parse(self, lines, *, context='', source=None, line_offset=1):
        """Parse markdown lines into docmodel blocks.

        When `source` is given every block is stamped with the address it came from —
        the file, the section key and the block's ordinal inside that section. That
        address is what lets a mark made in Word be routed back to the markdown that
        produced it. The ordinal is used rather than a line number because it is stable:
        editing one paragraph does not renumber the ones below it.

        `last_spans` records the 1-based `(first, last)` line of each block for a caller
        that has to *edit* the source rather than just name it. It is deliberately not
        part of the docmodel, for the same reason: it churns.
        """
        blocks = []
        spans = []
        i = 0
        n = len(lines)
        state = {'start': 0, 'ordinal': 0}

        def add(block, end):
            if source is not None:
                block['src'] = {'f': source, 's': context or '__preamble__',
                                'b': state['ordinal']}
            state['ordinal'] += 1
            blocks.append(block)
            spans.append((state['start'] + line_offset, end - 1 + line_offset))

        while i < n:
            state['start'] = i
            line = lines[i]
            stripped = line.strip()
            if not stripped:
                i += 1
                continue
            if HRULE_RE.match(stripped):
                i += 1
                continue

            fence = FENCE_RE.match(stripped)
            if fence:
                lang = fence.group(1) or None
                body = []
                i += 1
                while i < n and not FENCE_RE.match(lines[i].strip()):
                    body.append(lines[i])
                    i += 1
                i += 1
                if lang == 'mermaid':
                    add(dm.figure(None, None, source='mermaid',
                                  mermaid='\n'.join(body)), i)
                else:
                    add(dm.codeblock(body, lang=lang), i)
                continue

            if stripped.startswith('|'):
                rows, i = self._read_table(lines, i)
                add(self._table_block(rows, context), i)
                continue

            bq = BLOCKQUOTE_RE.match(stripped)
            if bq:
                body = []
                while i < n and BLOCKQUOTE_RE.match(lines[i].strip()):
                    body.append(BLOCKQUOTE_RE.match(lines[i].strip()).group(1))
                    i += 1
                add(dm.note(self.inline(' '.join(x for x in body if x))), i)
                continue

            if BULLET_RE.match(line) or ORDERED_RE.match(line):
                items, ordered, i = self._read_list(lines, i)
                add(dm.blist([self.inline(x) for x in items], ordered=ordered), i)
                continue

            i += 1
            add(dm.para(self.inline(stripped)), i)
        self.last_spans = spans
        return blocks

    def _read_table(self, lines, i):
        rows = []
        n = len(lines)
        while i < n and lines[i].strip().startswith('|'):
            raw = lines[i].strip()
            if not TABLE_SEP_RE.match(raw):
                rows.append(_split_row(raw))
            i += 1
        return rows, i

    def _table_block(self, rows, context):
        if not rows:
            return dm.para([])
        headers = [self.inline(c) for c in rows[0]]
        body = [[self.inline(c) for c in r] for r in rows[1:]]
        caption = self.table_captions.get(context)
        return dm.table(None, caption, headers, body)

    def _read_list(self, lines, i):
        items = []
        ordered = bool(ORDERED_RE.match(lines[i]))
        n = len(lines)
        while i < n:
            line = lines[i]
            mb = BULLET_RE.match(line)
            mo = ORDERED_RE.match(line)
            if mb:
                items.append(mb.group(2))
            elif mo:
                items.append(mo.group(3))
            elif line.strip() and line.startswith(('  ', '\t')) and items:
                items[-1] += ' ' + line.strip()
            else:
                break
            i += 1
        return items, ordered, i
