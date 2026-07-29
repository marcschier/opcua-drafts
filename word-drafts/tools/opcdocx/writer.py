"""docmodel -> WordprocessingML, using only styles the template defines.

Numbering is Word's job: headings carry no literal clause number, table and figure
captions carry a SEQ field, and every cross-reference is a REF field over a bookmark.
That is what makes the produced document renumber itself correctly when a clause moves.
"""

from . import contract
from . import oxml
from .oxml import (bookmark_end, bookmark_start, cell, cell_paragraph, paragraph, ref_field,
                   row, run, seq_field, table, wel)

HEADING_STYLES = {1: 'Heading1', 2: 'Heading2', 3: 'Heading3', 4: 'Heading4', 5: 'Heading5'}
ANNEX_HEADING_STYLES = {1: 'ANNEX-heading1', 2: 'ANNEX-heading2', 3: 'ANNEX-heading3'}


class Writer:
    """Turns docmodel blocks into body elements and keeps the bookmark bookkeeping."""

    def __init__(self, bookmarks, *, model=None, doc_ns_index=2):
        self.bm = bookmarks
        self.model = model
        self.doc_ns_index = doc_ns_index
        self.table_seq = 0
        self.figure_seq = 0
        self.targets = {}          # docmodel id -> bookmark name
        self.pending_figures = []  # (bookmark, docmodel figure block)

    # ------------------------------------------------------------------ helpers

    def bookmark_name(self, kind, ident):
        safe = ''.join(ch if (ch.isalnum() or ch == '_') else '_' for ch in str(ident))
        return '_%s_%s' % (kind, safe)

    def prepare(self, doc):
        """Register every bookmark name up front so forward references resolve.

        A cross-reference may point at a clause that has not been rendered yet, and a
        REF field to an unknown bookmark renders as "Error! Reference source not found",
        which is exactly the kind of defect that survives a casual read-through.
        """
        kinds = {'clause': 'Clause', 'annex': 'Annex', 'annex-clause': 'Clause',
                 'table': 'Tab', 'nodetable': 'Tab', 'enumtable': 'Tab', 'figure': 'Fig'}
        for _region, b in doc.iter_blocks():
            kind = kinds.get(b['t'])
            if kind and b.get('id'):
                self.targets[b['id']] = self.bookmark_name(kind, b['id'])

    def _wrap_bookmark(self, para, name):
        bid = self.bm.allocate(name)
        para.insert(_after_ppr(para), bookmark_start(bid, name))
        para.append(bookmark_end(bid))
        return para

    def runs(self, inline):
        out = []
        for r in inline:
            kind = r.get('r')
            if kind == 't':
                out.append(run(r['text'], bold=r.get('b', False), italic=r.get('i', False)))
            elif kind == 'code':
                out.append(run(r['text'], style='VARIABLE'))
            elif kind == 'link':
                out.append(run(r['text']))
            elif kind == 'xref':
                name = self.targets.get(r['target'], r['target'])
                cached = r.get('prefix') or '0'
                out.extend(ref_field(name, cached, number_only=(r['kind'] == 'clause')))
            elif kind == 'tab':
                out.append(oxml.tab_run())
            elif kind == 'br':
                out.append(oxml.break_run())
        return out

    # ------------------------------------------------------------------ blocks

    def block(self, b, *, annex=False):
        kind = b['t']
        handler = getattr(self, '_b_' + kind.replace('-', '_'), None)
        if handler is None:
            raise ValueError('unknown docmodel block: %r' % kind)
        return handler(b, annex=annex)

    def blocks(self, seq, *, annex=False):
        out = []
        for b in seq:
            out.extend(self.block(b, annex=annex))
        return out

    def _b_clause(self, b, *, annex=False):
        style = HEADING_STYLES[b['level']]
        name = self.bookmark_name('Clause', b['id'])
        self.targets[b['id']] = name
        p = paragraph(style, [run(b['title'])])
        return [self._wrap_bookmark(p, name)]

    def _b_annex(self, b, *, annex=False):
        name = self.bookmark_name('Annex', b['id'])
        self.targets[b['id']] = name
        kind = 'normative' if b.get('normative') else 'informative'
        p = paragraph('ANNEXtitle', [
            run('(%s)' % kind), oxml.break_run(), oxml.break_run(), run(b['title'])],
            page_break_before=True)
        return [self._wrap_bookmark(p, name)]

    def _b_annex_clause(self, b, *, annex=False):
        style = ANNEX_HEADING_STYLES[b['level']]
        name = self.bookmark_name('Clause', b['id'])
        self.targets[b['id']] = name
        p = paragraph(style, [run(b['title'])])
        return [self._wrap_bookmark(p, name)]

    def _b_para(self, b, *, annex=False):
        p = paragraph(b.get('style') or 'PARAGRAPH', self.runs(b['runs']))
        if b.get('bookmark'):
            self._wrap_bookmark(p, b['bookmark'])
        return [p]

    def _b_note(self, b, *, annex=False):
        return [paragraph('NOTE', [run('NOTE   ')] + self.runs(b['runs']))]

    def _b_list(self, b, *, annex=False):
        num = (contract.NUMID_BULLETS, b.get('level', 0))
        style = 'ListNumber' if b['ordered'] else 'ListBullet'
        return [paragraph(style, self.runs(item), num=num) for item in b['items']]

    def _b_code(self, b, *, annex=False):
        out = []
        for line in b['lines']:
            out.append(paragraph('CODE', [run(line)] if line else []))
        return out

    def _b_pagebreak(self, b, *, annex=False):
        return [paragraph('PARAGRAPH', [_page_break_run()])]

    def _b_term(self, b, *, annex=False):
        out = [paragraph('TERM-number3', []),
               paragraph('TERM', [run(b['term'])]),
               paragraph('TERM-definition', self.runs(b['definition']))]
        for note in b.get('notes') or []:
            out.append(paragraph('TERM-note', [run('Note 1 to entry: ')] + self.runs(note)))
        for i, ex in enumerate(b.get('examples') or [], 1):
            out.append(paragraph('TERM-example', [run('EXAMPLE %d ' % i)] + self.runs(ex)))
        if b.get('source'):
            out.append(paragraph('TERM-source', [run('[SOURCE: %s]' % b['source'])]))
        return out

    def _b_figure(self, b, *, annex=False):
        """A figure is an embedded object; the OLE part is attached in a later pass."""
        name = self.bookmark_name('Fig', b['id'])
        self.targets[b['id']] = name
        self.figure_seq += 1
        holder = paragraph('FIGURE', [])
        caption = paragraph('FIGURE-title',
                            [run('Figure ')] + seq_field('Figure', str(self.figure_seq))
                            + [run(' \u2013 %s' % b['caption'])])
        self._wrap_bookmark(caption, name)
        self.pending_figures.append((holder, b))
        return [holder, caption]

    # ------------------------------------------------------------------ tables

    def caption(self, ident, text):
        name = self.bookmark_name('Tab', ident)
        self.targets[ident] = name
        self.table_seq += 1
        p = paragraph('TABLE-title',
                      [run('Table ')] + seq_field('Table', str(self.table_seq))
                      + [run(' \u2013 %s' % text)], keep_next=True)
        return self._wrap_bookmark(p, name)

    def _b_table(self, b, *, annex=False):
        ncols = max(len(b['headers']), max((len(r) for r in b['rows']), default=0))
        widths = b.get('widths') or _even_widths(ncols)
        out = []
        if b.get('caption'):
            out.append(self.caption(b['id'], b['caption']))
        tbl = table(widths)
        if b['headers']:
            tbl.append(row([cell(widths[i], [cell_paragraph(runs=self.runs(h), bold=True)],
                                 bottom='double')
                            for i, h in enumerate(b['headers'])], header=True))
        for r in b['rows']:
            cells = []
            for i in range(ncols):
                inline = r[i] if i < len(r) else []
                cells.append(cell(widths[i], [cell_paragraph(runs=self.runs(inline))]))
            tbl.append(row(cells))
        out.append(tbl)
        out.append(paragraph('spacer', []))
        if b.get('note'):
            out.append(paragraph('TableNotes', [run(b['note'])]))
        return out

    # ------------------------------------------------------------------ node tables

    def _b_nodetable(self, b, *, annex=False):
        from . import nodeset_tables as nt
        spec = nt.type_table(self.model, b['browseName'], doc_ns_index=self.doc_ns_index)
        return self.type_definition_table(b['id'], b['caption'], spec)

    def _b_enumtable(self, b, *, annex=False):
        from . import nodeset_tables as nt
        spec = nt.enum_table(self.model, b['browseName'])
        return self.enum_tables(b['id'], spec)

    def type_definition_table(self, ident, caption, spec):
        """The Table 2 shape: Attribute/Value rows, a References block, ConformanceUnits."""
        g = contract.TYPE_TABLE_GRID
        total = sum(g)
        rest = total - g[0]
        out = [self.caption(ident, caption)]
        tbl = table(g)

        tbl.append(row([
            cell(g[0], [cell_paragraph('Attribute', bold=True)], bottom='double'),
            cell(rest, [cell_paragraph('Value', bold=True)], span=5, bottom='double'),
        ], header=True))
        first = True
        for name, value in spec['attributes']:
            tbl.append(row([
                cell(g[0], [cell_paragraph(name)], top='double' if first else 'single'),
                cell(rest, [cell_paragraph(value)], span=5,
                     top='double' if first else 'single'),
            ]))
            first = False

        headers = contract.TYPE_TABLE_REFERENCE_HEADERS
        tbl.append(row([cell(g[i], [cell_paragraph(h, bold=True)],
                             top='double', bottom='double')
                        for i, h in enumerate(headers)]))
        if spec['subtypeOf']:
            tbl.append(row([cell(total, [cell_paragraph(
                'Subtype of the %s defined in OPC 10000-5, i.e. inheriting the '
                'InstanceDeclarations of that Node.' % spec['subtypeOf'])],
                span=6, top='double')]))
        for m in spec['members']:
            tbl.append(row([
                cell(g[0], [cell_paragraph(m['referenceType'])]),
                cell(g[1], [cell_paragraph(m['nodeClass'])]),
                cell(g[2], [cell_paragraph(m['browseName'], style='TableTextWithTabs')]),
                cell(g[3], [cell_paragraph(m['dataType'])]),
                cell(g[4], [cell_paragraph(m['typeDefinition'])]),
                cell(g[5], [cell_paragraph(m['other'])]),
            ]))

        tbl.append(row([cell(total, [cell_paragraph('Conformance Units', bold=True)],
                             span=6, bottom='double')]))
        units = spec['conformanceUnits'] or ['OpenUSD ' + spec['browseName']]
        for i, cu in enumerate(units):
            tbl.append(row([cell(total, [cell_paragraph(cu)], span=6,
                                 top='double' if i == 0 else 'single')]))
        out.append(tbl)
        out.append(paragraph('spacer', []))
        return out

    def enum_tables(self, ident, spec):
        """The two tables an enumeration DataType needs: its Items and its definition."""
        g = contract.ENUM_GRID
        out = [self.caption(ident + '-items', '%s Items' % spec['browseName'])]
        tbl = table(g)
        tbl.append(row([cell(g[i], [cell_paragraph(h, bold=True)], bottom='double')
                        for i, h in enumerate(contract.ENUM_HEADERS)], header=True))
        for f in spec['fields']:
            tbl.append(row([
                cell(g[0], [cell_paragraph(f['name'])]),
                cell(g[1], [cell_paragraph(f['value'])]),
                cell(g[2], [cell_paragraph(f['description'])]),
            ]))
        out.append(tbl)
        out.append(paragraph('spacer', []))
        return out


# --------------------------------------------------------------------------- helpers


def _after_ppr(p):
    return 1 if len(p) and p[0].tag == oxml.q('w:pPr') else 0


def _page_break_run():
    r = wel('w:r')
    r.append(wel('w:br', {'w:type': 'page'}))
    return r


def _even_widths(n):
    total = contract.GENERIC_TABLE_TOTAL
    if n <= 0:
        return [total]
    base = total // n
    widths = [base] * n
    widths[-1] += total - base * n
    return widths
