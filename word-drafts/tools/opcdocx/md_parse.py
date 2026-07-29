"""Markdown -> docmodel.

Only the constructs the specification drafts actually use are supported; anything else
raises, because silently dropping content from a specification is worse than failing the
build. Section references (`§7.4.2`) become `xref` runs so the Word writer can emit a REF
field over a bookmark and let Word supply the live clause number.
"""

import re

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

_INLINE_RE = re.compile(
    r'(?P<code>`[^`]+`)'
    r'|(?P<bold>\*\*(?:[^*]|\*(?!\*))+\*\*)'
    r'|(?P<italic>(?<!\*)\*(?!\*)(?:[^*]+)\*(?!\*))'
    r'|(?P<link>\[[^\]]+\]\([^)]+\))'
    r'|(?P<ref>§\s*[0-9]+(?:\.[0-9]+)*)'
)


class Section:
    """One markdown heading and the blocks under it, excluding nested subsections."""

    def __init__(self, level, title, key):
        self.level = level
        self.title = title
        self.key = key
        self.lines = []

    def __repr__(self):
        return 'Section(%d, %r, %d lines)' % (self.level, self.key, len(self.lines))


def split_sections(text):
    """Split a markdown document into an ordered mapping of `key -> Section`.

    The key is the heading text with markdown emphasis intact, matching the `from`
    values in the build config so a human can read the mapping against the source.
    """
    sections = {}
    order = []
    preamble = Section(0, '', '__preamble__')
    sections['__preamble__'] = preamble
    order.append('__preamble__')
    current = preamble
    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if m and not _in_fence(current.lines):
            level = len(m.group(1))
            title = m.group(2)
            key = title
            if key in sections:
                raise ValueError('duplicate heading: %r' % key)
            current = Section(level, title, key)
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


def parse_inline(text, *, xref_resolver=None):
    """Inline markdown -> docmodel runs."""
    runs = []
    pos = 0
    for m in _INLINE_RE.finditer(text):
        if m.start() > pos:
            runs.append(dm.t(_unescape(text[pos:m.start()])))
        if m.group('code'):
            runs.append(dm.code(m.group('code')[1:-1]))
        elif m.group('bold'):
            runs.append(dm.t(_unescape(m.group('bold')[2:-2]), b=True))
        elif m.group('italic'):
            runs.append(dm.t(_unescape(m.group('italic')[1:-1]), i=True))
        elif m.group('link'):
            label, _, href = m.group('link')[1:-1].partition('](')
            runs.append(dm.link(_unescape(label), href))
        elif m.group('ref'):
            number = SECTION_REF_RE.match(m.group('ref')).group(1)
            resolved = xref_resolver(number) if xref_resolver else None
            if resolved:
                target, label = resolved
                runs.append(dm.xref(target, kind='clause', prefix=label))
            else:
                runs.append(dm.t(m.group('ref')))
        pos = m.end()
    if pos < len(text):
        runs.append(dm.t(_unescape(text[pos:])))
    return [r for r in runs if r.get('text') != '' or r.get('r') != 't']


def _unescape(s):
    return s.replace('\\|', '|').replace('\\*', '*').replace('\\_', '_')


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
    def __init__(self, *, xref_resolver=None, table_captions=None):
        self.xref_resolver = xref_resolver
        self.table_captions = table_captions or {}

    def inline(self, text):
        return parse_inline(text, xref_resolver=self.xref_resolver)

    def parse(self, lines, *, context=''):
        blocks = []
        i = 0
        n = len(lines)
        while i < n:
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
                    blocks.append(dm.figure(None, None, source='mermaid',
                                            mermaid='\n'.join(body)))
                else:
                    blocks.append(dm.codeblock(body, lang=lang))
                continue

            if stripped.startswith('|'):
                rows, i = self._read_table(lines, i)
                blocks.append(self._table_block(rows, context))
                continue

            bq = BLOCKQUOTE_RE.match(stripped)
            if bq:
                body = []
                while i < n and BLOCKQUOTE_RE.match(lines[i].strip()):
                    body.append(BLOCKQUOTE_RE.match(lines[i].strip()).group(1))
                    i += 1
                blocks.append(dm.note(self.inline(' '.join(x for x in body if x))))
                continue

            if BULLET_RE.match(line) or ORDERED_RE.match(line):
                items, ordered, i = self._read_list(lines, i)
                blocks.append(dm.blist([self.inline(x) for x in items], ordered=ordered))
                continue

            blocks.append(dm.para(self.inline(stripped)))
            i += 1
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
