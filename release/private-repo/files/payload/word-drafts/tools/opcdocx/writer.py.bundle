"""docmodel -> WordprocessingML, using only styles the template defines.

Numbering is Word's job: headings carry no literal clause number, table and figure
captions carry a SEQ field, and every cross-reference is a REF field over a bookmark.
That is what makes the produced document renumber itself correctly when a clause moves.

Every paragraph is stamped with a `w14:paraId` derived from the block's source address
rather than left for Word to invent. Word preserves an id it finds and only assigns one
where it is missing, so after a reviewer's round trip a paragraph with a known id is
traceable to the markdown that produced it, and a paragraph with an unknown id is one the
reviewer created. That is what makes a marked-up document ingestible.
"""

import hashlib

from . import contract
from . import docmodel as dm
from . import oxml
from .oxml import (bookmark_end, bookmark_start, cell, cell_paragraph, paragraph, ref_field,
                   row, run, seq_field, table, wel)

HEADING_STYLES = {1: 'Heading1', 2: 'Heading2', 3: 'Heading3', 4: 'Heading4', 5: 'Heading5'}
ANNEX_HEADING_STYLES = {1: 'ANNEX-heading1', 2: 'ANNEX-heading2', 3: 'ANNEX-heading3'}


def para_id(key):
    """An 8-hex-digit `w14:paraId` derived deterministically from a source address.

    Word treats `00000000` as absent and reserves ids with the high bit set, so the
    digest is masked into `00000001`..`7FFFFFFF`.
    """
    digest = hashlib.blake2b(key.encode('utf-8'), digest_size=8).digest()
    value = int.from_bytes(digest, 'big') & 0x7FFFFFFF
    return '%08X' % (value or 1)


class Writer:
    """Turns docmodel blocks into body elements and keeps the bookmark bookkeeping."""

    def __init__(self, bookmarks, *, model=None, doc_ns_index=2, reserved_ids=()):
        self.bm = bookmarks
        self.model = model
        self.doc_ns_index = doc_ns_index
        self.table_seq = 0
        self.figure_seq = 0
        self.targets = {}          # docmodel id -> bookmark name
        self.pending_figures = []  # (bookmark, docmodel figure block)
        self.para_ids = {}         # paraId -> source address, for the provenance sidecar
        # The template is a real Word document, so its retained paragraphs already carry
        # paraIds. Generating one that collides would make two paragraphs — one of them
        # the reviewer's, one of them the template's — indistinguishable on the way back.
        self.reserved_ids = set(reserved_ids)
        self._region = ''
        self._block_index = 0

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
                 'table': 'Tab', 'nodetable': 'Tab', 'enumtable': 'Tab',
                 'methodtable': 'Tab', 'figure': 'Fig'}
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
        out = handler(b, annex=annex)
        self._stamp(out, b)
        return out

    def blocks(self, seq, *, annex=False, region=''):
        out = []
        previous, self._region = self._region, region or self._region
        for index, b in enumerate(seq):
            self._block_index = index
            out.extend(self.block(b, annex=annex))
        self._region = previous
        return out

    def _stamp(self, elements, block):
        """Give every paragraph a paraId derived from where the block came from.

        A block can emit many paragraphs — a list one per item, a table one per cell —
        so the ordinal within the block is part of the address. Collisions are resolved
        by rehashing rather than ignored: two paragraphs sharing an id would silently
        merge two source locations into one on the way back.
        """
        self.stamp(elements, dm.source_key(block, self._region, self._block_index))

    def stamp(self, elements, base):
        """Stamp a run of elements against an explicit source key.

        Some markup is built outside the block dispatcher — Annex A's node reference
        table, the draft banner, the tables of contents. Left unstamped, Word assigns its
        own ids on the first save and the ingest reads them as the template's, so a mark
        on a generated node table would be reported as a template deviation instead of a
        change to the information model.
        """
        for ordinal, p in enumerate(_iter_paragraphs(elements)):
            key = '%s\x1f%d' % (base, ordinal)
            pid = para_id(key)
            attempt = 0
            while pid in self.reserved_ids or (pid in self.para_ids
                                               and self.para_ids[pid] != key):
                attempt += 1
                pid = para_id('%s\x1f#%d' % (key, attempt))
            self.para_ids[pid] = key
            p.set(oxml.q('w14:paraId'), pid)
        return elements

    def stamp_generated(self, elements, region, kind, index=0):
        """Stamp markup that has no docmodel block, naming what generated it."""
        return self.stamp(elements, 'gen\x1f%s\x1f%d\x1f%s' % (region, index, kind))

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
        spec = nt.enum_table(
            self.model, b['browseName'], doc_ns_index=self.doc_ns_index,
            structure_fields=b.get('structureFields', False))
        return self.enum_tables(b['id'], spec)

    def _b_methodtable(self, b, *, annex=False):
        """OPC 20020 8.1.3: signature, Method Arguments, AddressSpace definition."""
        from . import nodeset_tables as nt
        spec = nt.method_table(self.model, b['browseName'],
                               doc_ns_index=self.doc_ns_index, owner=b.get('owner'))
        out = []
        if spec['description']:
            out.append(paragraph('PARAGRAPH', [run(spec['description'])]))
        out.append(paragraph('PARAGRAPH', [run('Signature')]))
        for line in spec['signature']:
            out.append(paragraph('MethodSignature', [run(line)]))

        if spec['arguments']:
            g = [2200, 6726]
            out.append(self.caption(b['id'] + '-args',
                                    '%s Method Arguments' % spec['browseName']))
            tbl = table(g)
            tbl.append(row([
                cell(g[0], [cell_paragraph('Argument', bold=True)], bottom='double'),
                cell(g[1], [cell_paragraph('Description', bold=True)], bottom='double'),
            ], header=True))
            for a in spec['arguments']:
                tbl.append(row([
                    cell(g[0], [cell_paragraph(a['name'])]),
                    cell(g[1], [cell_paragraph(a['description'])]),
                ]))
            out.append(tbl)
            out.append(paragraph('spacer', []))

        # The template omits the AddressSpace table when a Method has no Properties
        # beyond InputArguments and OutputArguments.
        if spec['hasExtraProperties'] or spec['arguments']:
            out.extend(self.method_addressspace_table(b['id'] + '-as', spec))
        return out

    def method_addressspace_table(self, ident, spec):
        g = contract.TYPE_TABLE_GRID
        total = sum(g)
        rest = total - g[0]
        out = [self.caption(ident, '%s Method AddressSpace definition'
                            % spec['browseName'])]
        tbl = table(g)
        tbl.append(row([
            cell(g[0], [cell_paragraph('Attribute', bold=True)], bottom='double'),
            cell(rest, [cell_paragraph('Value', bold=True)], span=5, bottom='double'),
        ], header=True))
        tbl.append(row([
            cell(g[0], [cell_paragraph('BrowseName')], top='double'),
            cell(rest, [cell_paragraph(spec['browseName'])], span=5, top='double'),
        ]))
        headers = ['References', 'NodeClass', 'BrowseName', 'DataType',
                   'TypeDefinition', 'ModellingRule']
        tbl.append(row([cell(g[i], [cell_paragraph(h, bold=True)],
                             top='double', bottom='double')
                        for i, h in enumerate(headers)]))
        for present, name in ((spec['inputs'], 'InputArguments'),
                              (spec['outputs'], 'OutputArguments')):
            if not present:
                continue
            tbl.append(row([
                cell(g[0], [cell_paragraph('0:HasProperty')]),
                cell(g[1], [cell_paragraph('Variable')]),
                cell(g[2], [cell_paragraph('0:' + name, style='TableTextWithTabs')]),
                cell(g[3], [cell_paragraph('0:Argument[]')]),
                cell(g[4], [cell_paragraph('0:PropertyType')]),
                cell(g[5], [cell_paragraph('0:Mandatory')]),
            ]))
        if spec['conformanceUnits']:
            tbl.append(row([cell(total, [cell_paragraph('Conformance Units', bold=True)],
                                 span=6, bottom='double')]))
            for i, cu in enumerate(spec['conformanceUnits']):
                tbl.append(row([cell(total, [cell_paragraph(cu)], span=6,
                                     top='double' if i == 0 else 'single')]))
        out.append(tbl)
        out.append(paragraph('spacer', []))
        return out

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
        """The Items table for an Enumeration or Structure DataType."""
        structure = spec['kind'] == 'structure'
        g = contract.STRUCTURE_GRID if structure else contract.ENUM_GRID
        headers = contract.STRUCTURE_HEADERS if structure else contract.ENUM_HEADERS
        out = [self.caption(ident + '-items', '%s Items' % spec['browseName'])]
        tbl = table(g)
        tbl.append(row([cell(g[i], [cell_paragraph(h, bold=True)], bottom='double')
                        for i, h in enumerate(headers)], header=True))
        for f in spec['fields']:
            if structure:
                tbl.append(row([
                    cell(g[0], [cell_paragraph(f['name'])]),
                    cell(g[1], [cell_paragraph(f['type'])]),
                    cell(g[2], [cell_paragraph(f['cardinality'])]),
                    cell(g[3], [cell_paragraph(f['description'])]),
                ]))
            else:
                tbl.append(row([
                    cell(g[0], [cell_paragraph(f['name'])]),
                    cell(g[1], [cell_paragraph(f['value'])]),
                    cell(g[2], [cell_paragraph(f['description'])]),
                ]))
        out.append(tbl)
        out.append(paragraph('spacer', []))
        return out


# --------------------------------------------------------------------------- helpers


def _iter_paragraphs(elements):
    """Every `w:p` an element list contains, including the ones inside table cells.

    `iter()` already yields the element itself when it matches, so a top-level paragraph
    must not be yielded separately or it would be stamped twice and keep the second id.
    """
    tag = oxml.q('w:p')
    for el in elements:
        for p in el.iter(tag):
            yield p


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
