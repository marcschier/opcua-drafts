"""The document intermediate representation.

A *docmodel* is an ordered list of blocks with inline runs. It is deliberately plain
JSON-shaped data: it is committed next to the .docx so that a reviewer can diff the
document semantically instead of diffing a ZIP, and it is where template conformance is
decided before any XML exists.

Block kinds
-----------
clause      a numbered heading; Word supplies the number
annex       an annex title; Word supplies the letter
para        a paragraph in a named template style
list        a bulleted or numbered list
table       a generic table with a caption
nodetable   a placeholder resolved from the NodeSet into official Table 2 markup
code        a fenced code block, rendered in the CODE style
figure      an embedded PowerPoint object with a caption
note        a NOTE paragraph
term        an entry in clause 3.2
pagebreak   an explicit page break

Inline run kinds
----------------
t     literal text, optionally bold or italic
code  an identifier, rendered in the VARIABLE character style
xref  a cross-reference resolved to a REF field over a bookmark
link  an external hyperlink
tab   a tab
br    a line break
"""

import json


# --------------------------------------------------------------------------- inline


def t(text, *, b=False, i=False):
    r = {'r': 't', 'text': text}
    if b:
        r['b'] = True
    if i:
        r['i'] = True
    return r


def code(text):
    return {'r': 'code', 'text': text}


def xref(target, *, kind='clause', prefix=None):
    """A cross-reference. `kind` selects how the REF field is rendered."""
    r = {'r': 'xref', 'target': target, 'kind': kind}
    if prefix:
        r['prefix'] = prefix
    return r


def link(text, href):
    return {'r': 'link', 'text': text, 'href': href}


def tab():
    return {'r': 'tab'}


def br():
    return {'r': 'br'}


# --------------------------------------------------------------------------- blocks


def clause(cid, title, level=1):
    return {'t': 'clause', 'id': cid, 'title': title, 'level': level}


def annex(aid, title, *, normative=False):
    return {'t': 'annex', 'id': aid, 'title': title, 'normative': normative}


def annex_clause(cid, title, level=1):
    return {'t': 'annex-clause', 'id': cid, 'title': title, 'level': level}


def para(runs, style='PARAGRAPH', *, bookmark=None):
    b = {'t': 'para', 'style': style, 'runs': list(runs)}
    if bookmark:
        b['bookmark'] = bookmark
    return b


def text_para(s, style='PARAGRAPH', *, bookmark=None):
    return para([t(s)], style, bookmark=bookmark)


def blist(items, *, ordered=False, level=0):
    return {'t': 'list', 'ordered': ordered, 'level': level,
            'items': [list(i) for i in items]}


def table(tid, caption, headers, rows, *, kind='generic', widths=None, note=None):
    return {'t': 'table', 'id': tid, 'caption': caption, 'kind': kind,
            'headers': [list(h) for h in headers],
            'rows': [[list(c) for c in r] for r in rows],
            'widths': widths, 'note': note}


def nodetable(tid, caption, browse_name, *, kind='type'):
    return {'t': 'nodetable', 'id': tid, 'caption': caption,
            'browseName': browse_name, 'kind': kind}


def codeblock(lines, *, lang=None):
    return {'t': 'code', 'lang': lang, 'lines': list(lines)}


def figure(fid, caption, *, source, mermaid=None):
    return {'t': 'figure', 'id': fid, 'caption': caption, 'source': source,
            'mermaid': mermaid}


def note(runs):
    return {'t': 'note', 'runs': list(runs)}


def term(name, definition, *, notes=(), examples=(), source=None):
    return {'t': 'term', 'term': name, 'definition': definition,
            'notes': list(notes), 'examples': list(examples), 'source': source}


def pagebreak():
    return {'t': 'pagebreak'}


# --------------------------------------------------------------------------- document


class DocModel:
    """An ordered list of blocks per template region."""

    def __init__(self):
        self.regions = {}
        self.order = []

    def region(self, name):
        if name not in self.regions:
            self.regions[name] = []
            self.order.append(name)
        return self.regions[name]

    def add(self, name, *blocks):
        r = self.region(name)
        for b in blocks:
            if isinstance(b, list):
                r.extend(b)
            elif b is not None:
                r.append(b)
        return self

    def to_json(self):
        return json.dumps({'regions': {k: self.regions[k] for k in self.order},
                           'order': self.order},
                          indent=2, ensure_ascii=False) + '\n'

    @classmethod
    def from_json(cls, s):
        raw = json.loads(s)
        d = cls()
        for name in raw['order']:
            d.regions[name] = raw['regions'][name]
            d.order.append(name)
        return d

    def iter_blocks(self):
        for name in self.order:
            for b in self.regions[name]:
                yield name, b


def plain_text(runs):
    """Flatten inline runs to plain text, for validation and heading checks."""
    out = []
    for r in runs:
        kind = r.get('r')
        if kind in ('t', 'code', 'link'):
            out.append(r.get('text', ''))
        elif kind == 'xref':
            out.append(r.get('prefix', '') or '')
        elif kind == 'tab':
            out.append('\t')
        elif kind == 'br':
            out.append(' ')
    return ''.join(out)
