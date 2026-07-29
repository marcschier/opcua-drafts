"""Low-level WordprocessingML construction.

Everything the writer emits goes through here, so the markup stays consistent with the
template. Element shapes were taken from the template itself (see
skills/opcua-spec-to-word/reference/template-contract.md); the normative table geometry is
the one used by Table 16 of OPC 20020.
"""

from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
V = 'urn:schemas-microsoft-com:vml'
O = 'urn:schemas-microsoft-com:office:office'
WP = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
PIC = 'http://schemas.openxmlformats.org/drawingml/2006/picture'
XML = 'http://www.w3.org/XML/1998/namespace'

NSMAP = {'w': W, 'r': R, 'v': V, 'o': O, 'wp': WP, 'a': A, 'pic': PIC, 'xml': XML}


def q(tag):
    """'w:p' -> '{namespace}p'."""
    prefix, _, local = tag.partition(':')
    return '{%s}%s' % (NSMAP[prefix], local)


def wel(tag, attrs=None, children=()):
    """Build an element. `attrs` keys are qualified names such as 'w:val'."""
    e = etree.Element(q(tag))
    for k, v in (attrs or {}).items():
        e.set(q(k), str(v))
    for c in children:
        if c is not None:
            e.append(c)
    return e


# --------------------------------------------------------------------------- runs


def run(text, *, bold=False, italic=False, style=None, color=None, no_proof=False,
        sub=False, sup=False):
    r = wel('w:r')
    rpr = wel('w:rPr')
    if style:
        rpr.append(wel('w:rStyle', {'w:val': style}))
    if bold:
        rpr.append(wel('w:b'))
    if italic:
        rpr.append(wel('w:i'))
    if color:
        rpr.append(wel('w:color', {'w:val': color}))
    if no_proof:
        rpr.append(wel('w:noProof'))
    if sub:
        rpr.append(wel('w:vertAlign', {'w:val': 'subscript'}))
    if sup:
        rpr.append(wel('w:vertAlign', {'w:val': 'superscript'}))
    if len(rpr):
        r.append(rpr)
    if text is not None:
        t = wel('w:t')
        t.set(q('xml:space'), 'preserve')
        t.text = text
        r.append(t)
    return r


def break_run():
    r = wel('w:r')
    r.append(wel('w:br'))
    return r


def tab_run():
    r = wel('w:r')
    r.append(wel('w:tab'))
    return r


# --------------------------------------------------------------------------- fields


def field_runs(instruction, cached='1', *, bold=False, italic=False):
    """A complex field: begin / instrText / separate / cached result / end."""
    out = []
    r = wel('w:r')
    r.append(wel('w:fldChar', {'w:fldCharType': 'begin'}))
    out.append(r)
    r = wel('w:r')
    it = wel('w:instrText')
    it.set(q('xml:space'), 'preserve')
    it.text = ' %s ' % instruction.strip()
    r.append(it)
    out.append(r)
    r = wel('w:r')
    r.append(wel('w:fldChar', {'w:fldCharType': 'separate'}))
    out.append(r)
    out.append(run(cached, bold=bold, italic=italic, no_proof=True))
    r = wel('w:r')
    r.append(wel('w:fldChar', {'w:fldCharType': 'end'}))
    out.append(r)
    return out


def seq_field(kind, cached='1'):
    return field_runs('SEQ %s \\* ARABIC' % kind, cached)


def ref_field(bookmark, cached='0', *, number_only=False):
    """REF field. `number_only` yields the clause number (\\r), as the template does."""
    flags = '\\r \\h' if number_only else '\\h'
    return field_runs('REF %s %s' % (bookmark, flags), cached)


def pageref_field(bookmark, cached='1'):
    return field_runs('PAGEREF %s \\h' % bookmark, cached)


def toc_field(instruction):
    """A TOC field with no cached result — Word fills it in on update."""
    out = []
    r = wel('w:r')
    r.append(wel('w:fldChar', {'w:fldCharType': 'begin', 'w:dirty': 'true'}))
    out.append(r)
    r = wel('w:r')
    it = wel('w:instrText')
    it.set(q('xml:space'), 'preserve')
    it.text = ' %s ' % instruction.strip()
    r.append(it)
    out.append(r)
    r = wel('w:r')
    r.append(wel('w:fldChar', {'w:fldCharType': 'separate'}))
    out.append(r)
    out.append(run('Right-click and choose Update Field.', no_proof=True))
    r = wel('w:r')
    r.append(wel('w:fldChar', {'w:fldCharType': 'end'}))
    out.append(r)
    return out


# --------------------------------------------------------------------------- bookmarks


class BookmarkAllocator:
    """Hands out bookmark ids above everything the template already uses."""

    def __init__(self, start_id):
        self._next = start_id
        self._names = {}

    def allocate(self, name):
        if name in self._names:
            return self._names[name]
        bid = self._next
        self._next += 1
        self._names[name] = bid
        return bid

    @property
    def names(self):
        return dict(self._names)


def bookmark_start(bid, name):
    return wel('w:bookmarkStart', {'w:id': str(bid), 'w:name': name})


def bookmark_end(bid):
    return wel('w:bookmarkEnd', {'w:id': str(bid)})


# --------------------------------------------------------------------------- paragraphs


def paragraph(style=None, runs=(), *, keep_next=False, num=None, outline_level=None,
              page_break_before=False):
    p = wel('w:p')
    ppr = wel('w:pPr')
    if style:
        ppr.append(wel('w:pStyle', {'w:val': style}))
    if page_break_before:
        ppr.append(wel('w:pageBreakBefore'))
    if keep_next:
        ppr.append(wel('w:keepNext'))
    if num is not None:
        numpr = wel('w:numPr')
        numpr.append(wel('w:ilvl', {'w:val': str(num[1])}))
        numpr.append(wel('w:numId', {'w:val': str(num[0])}))
        ppr.append(numpr)
    if outline_level is not None:
        ppr.append(wel('w:outlineLvl', {'w:val': str(outline_level)}))
    if len(ppr):
        p.append(ppr)
    for r in runs:
        if r is not None:
            p.append(r)
    return p


def text_paragraph(style, text, **kw):
    return paragraph(style, [run(text)] if text else [], **kw)


# --------------------------------------------------------------------------- tables

GRAY = '808080'


def _tbl_borders():
    b = wel('w:tblBorders')
    for side, sz in (('top', 12), ('left', 12), ('bottom', 12), ('right', 12),
                     ('insideH', 6), ('insideV', 6)):
        b.append(wel('w:' + side, {'w:val': 'single', 'w:sz': str(sz),
                                   'w:space': '0', 'w:color': GRAY}))
    return b


def table(grid_widths, *, align='center'):
    """A table with the OPC 20020 normative geometry."""
    tbl = wel('w:tbl')
    tblpr = wel('w:tblPr')
    tblpr.append(wel('w:tblW', {'w:w': str(sum(grid_widths)), 'w:type': 'dxa'}))
    if align:
        tblpr.append(wel('w:jc', {'w:val': align}))
    tblpr.append(_tbl_borders())
    tblpr.append(wel('w:tblLayout', {'w:type': 'fixed'}))
    tblpr.append(wel('w:tblLook', {'w:val': '0000', 'w:firstRow': '0', 'w:lastRow': '0',
                                   'w:firstColumn': '0', 'w:lastColumn': '0',
                                   'w:noHBand': '0', 'w:noVBand': '0'}))
    tbl.append(tblpr)
    grid = wel('w:tblGrid')
    for gw in grid_widths:
        grid.append(wel('w:gridCol', {'w:w': str(gw)}))
    tbl.append(grid)
    return tbl


def _tc_borders(top='single', bottom='single'):
    tb = wel('w:tcBorders')
    tb.append(wel('w:top', {'w:val': top, 'w:sz': '4', 'w:space': '0', 'w:color': 'auto'}))
    tb.append(wel('w:left', {'w:val': 'single', 'w:sz': '4', 'w:space': '0', 'w:color': 'auto'}))
    tb.append(wel('w:bottom', {'w:val': bottom, 'w:sz': '4', 'w:space': '0', 'w:color': 'auto'}))
    tb.append(wel('w:right', {'w:val': 'single', 'w:sz': '4', 'w:space': '0', 'w:color': 'auto'}))
    return tb


def cell(width, blocks, *, span=None, top='single', bottom='single'):
    tc = wel('w:tc')
    tcpr = wel('w:tcPr')
    tcpr.append(wel('w:tcW', {'w:w': str(width), 'w:type': 'dxa'}))
    if span and span > 1:
        tcpr.append(wel('w:gridSpan', {'w:val': str(span)}))
    tcpr.append(_tc_borders(top, bottom))
    tc.append(tcpr)
    blocks = list(blocks) or [paragraph('TableText')]
    for b in blocks:
        tc.append(b)
    return tc


def row(cells, *, header=False, align='center'):
    tr = wel('w:tr')
    trpr = wel('w:trPr')
    if header:
        trpr.append(wel('w:tblHeader'))
    if align:
        trpr.append(wel('w:jc', {'w:val': align}))
    if len(trpr):
        tr.append(trpr)
    for c in cells:
        tr.append(c)
    return tr


def cell_paragraph(text=None, *, style='TableText', bold=False, italic=False, runs=None):
    rs = runs if runs is not None else ([run(text, bold=bold, italic=italic)] if text else [])
    return paragraph(style, rs)


# --------------------------------------------------------------------------- reading


def parse(data):
    return etree.fromstring(data)


def xml_bytes(tree):
    return etree.tostring(tree, xml_declaration=True, encoding='UTF-8', standalone=True)


def iter_text(node):
    out = []
    for n in node.iter():
        if n.tag == q('w:t'):
            out.append(n.text or '')
        elif n.tag == q('w:tab'):
            out.append('\t')
    return ''.join(out)


def para_style(p):
    ppr = p.find(q('w:pPr'))
    if ppr is None:
        return 'Normal'
    s = ppr.find(q('w:pStyle'))
    return s.get(q('w:val')) if s is not None else 'Normal'
