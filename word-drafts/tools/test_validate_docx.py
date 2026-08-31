#!/usr/bin/env python3
"""Mutation-test validate_docx.py.

    python word-drafts/tools/test_validate_docx.py word-drafts/tools/specs/openusd-binding.json

A checker that passes trivially is worthless, so each mutation below breaks the document
in exactly one of the ways a check claims to catch, and the test fails if the validator
still reports the document as clean. The original file is never modified: every mutation
is applied to a copy in a temporary directory.
"""

import argparse
import io
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import validate_docx

REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def mutate(src, dst, transform, part='word/document.xml'):
    with zipfile.ZipFile(src) as z:
        names = z.namelist()
        data = {n: z.read(n) for n in names}
    original = data[part].decode('utf-8')
    mutated = transform(original)
    if mutated == original:
        raise AssertionError('mutation had no effect; the test itself is broken')
    data[part] = mutated.encode('utf-8')
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, data[n])


def _drop_first(pattern):
    def apply(text):
        return re.sub(pattern, '', text, count=1)
    return apply


def _replace_first(pattern, replacement):
    def apply(text):
        return re.sub(pattern, replacement, text, count=1)
    return apply


def _replace_last(pattern, replacement):
    """Mutate the final match — the node tables precede the conformance-units clause,
    so the last occurrence of a unit name is the one in that clause."""
    def apply(text):
        matches = list(re.finditer(pattern, text))
        if not matches:
            return text
        m = matches[-1]
        return text[:m.start()] + m.expand(replacement) + text[m.end():]
    return apply


def _replace_all(pattern, replacement):
    def apply(text):
        return re.sub(pattern, replacement, text)
    return apply


# Mutations that hold for any document. The rest are derived from the document under
# test: hard-coding one specification's type and unit names made the suite silently
# inapplicable to every other specification, reporting "the test itself is broken"
# instead of testing anything.
STATIC_MUTATIONS = [
    ('a table caption loses its SEQ field',
     'table-captions',
     _drop_first(r'<w:instrText[^>]*> SEQ Table \\\* ARABIC </w:instrText>')),
    ('a heading is given a literal clause number',
     'heading-numbers',
     _replace_first(r'(<w:pStyle w:val="Heading1"/>.*?<w:t[^>]*>)Scope',
                    r'\g<1>1 Scope')),
    ('a forbidden online-reference link appears in the body',
     'forbidden-links',
     _replace_first(r'(<w:pStyle w:val="Heading1"/></w:pPr>)',
                    r'\g<1><w:r><w:t>see '
                    r'https://reference.opcfoundation.org/specs/OPC-10000-3/</w:t></w:r>')),
    ('a retained template clause is deleted',
     'template-slices',
     _drop_first(r'<w:t[^>]*>[^<]*royalty[^<]*</w:t>')),
    ('change tracking is turned off',
     'track-changes',
     _drop_first(r'<w:trackChanges/>'),
     'word/settings.xml'),
]


def _member_row_re(row_marker, data_type):
    """The table row that declares this member of a type.

    Matching on the BrowseName alone is not enough: `NamespaceUri` also appears in the
    template's own example tables and in the Namespaces clause, so the first match was a
    row the node-table check never looks at and the mutation proved nothing. Requiring the
    member's printed DataType in the same row pins it to a real node table.
    """
    return re.compile(r'<w:tr[^>]*>(?:(?!</w:tr>).)*?' + re.escape(row_marker)
                      + r'(?:(?!</w:tr>).)*?' + re.escape(data_type)
                      + r'(?:(?!</w:tr>).)*?</w:tr>', re.S)


def _find_member_row(text, owner, row_marker, data_type):
    """The member row inside the *owning type's* definition table.

    A member of an abstract interface is re-declared in the tables of the types that
    implement it and listed again in Annex A, so searching the whole document finds a row
    that `check_node_tables` does not inspect. It inspects the table captioned
    "<type> definition"; the search starts there.
    """
    anchor = text.find(owner + ' definition')
    return _member_row_re(row_marker, data_type).search(text, max(anchor, 0))


def _drop_member_row(owner, row_marker, data_type):
    def apply(text):
        m = _find_member_row(text, owner, row_marker, data_type)
        return text if not m else text[:m.start()] + text[m.end():]
    return apply


def _corrupt_cell(owner, row_marker, was, now):
    """Change one cell inside the table row that declares `row_marker`.

    Substituting the first occurrence in the whole document is not the same thing: a
    DataType name also appears in prose and in its own clause heading, and mutating one
    of those proves nothing about the node tables.
    """
    def apply(text):
        m = _find_member_row(text, owner, row_marker, was)
        if not m:
            return text
        return text[:m.start()] + m.group(0).replace(was, now, 1) + text[m.end():]
    return apply


def _find_items_row(text, type_name, field_name, marker):
    bounds = _find_items_table(text, type_name)
    if bounds is None:
        return None
    table_start, table_end = bounds
    pattern = re.compile(
        r'<w:tr[^>]*>(?:(?!</w:tr>).)*?' + re.escape(field_name)
        + r'(?:(?!</w:tr>).)*?' + re.escape(marker)
        + r'(?:(?!</w:tr>).)*?</w:tr>', re.S)
    return pattern.search(text, table_start, table_end)


def _find_items_table(text, type_name):
    needle = type_name + ' Items'
    start = 0
    while True:
        anchor = text.find(needle, start)
        if anchor < 0:
            return None
        para_start = text.rfind('<w:p', 0, anchor)
        para_end = text.find('</w:p>', anchor)
        if para_start >= 0 and para_end >= 0:
            caption = text[para_start:para_end]
            if 'w:pStyle w:val="TABLE-title"' in caption:
                table_start = text.find('<w:tbl', para_end)
                table_end = text.find('</w:tbl>', table_start)
                if table_start >= 0 and table_end >= 0:
                    return table_start, table_end + len('</w:tbl>')
                return None
        start = anchor + len(needle)


def _corrupt_items_cell(type_name, field_name, was, now):
    def apply(text):
        m = _find_items_row(text, type_name, field_name, was)
        if not m:
            return text
        return text[:m.start()] + m.group(0).replace(was, now, 1) + text[m.end():]
    return apply


def _swap_first_structure_rows(type_name):
    def apply(text):
        bounds = _find_items_table(text, type_name)
        if bounds is None:
            return text
        start, end = bounds
        table = text[start:end]
        rows = list(re.finditer(r'<w:tr[^>]*>.*?</w:tr>', table, re.S))
        if len(rows) < 3:
            return text
        first, second = rows[1], rows[2]
        swapped = (table[:first.start()] + second.group(0)
                   + table[first.end():second.start()] + first.group(0)
                   + table[second.end():])
        return text[:start] + swapped + text[end:]
    return apply


def _duplicate_first_structure_row(type_name):
    def apply(text):
        bounds = _find_items_table(text, type_name)
        if bounds is None:
            return text
        start, end = bounds
        table = text[start:end]
        rows = list(re.finditer(r'<w:tr[^>]*>.*?</w:tr>', table, re.S))
        if len(rows) < 2:
            return text
        at = rows[1].end()
        duplicated = table[:at] + rows[1].group(0) + table[at:]
        return text[:start] + duplicated + text[end:]
    return apply


def derived_mutations(
        document_xml, rels_xml, model, doc_ns_index, structure_fields=False):
    """Mutations built from the document under test, plus the reason for any it skips."""
    out, skipped = [], []

    ref = re.search(r'REF (_Clause_c[A-Za-z0-9_]+) ', document_xml)
    if ref:
        out.append(('a cross-reference points at a bookmark that does not exist', 'xrefs',
                    _replace_first(r'REF ' + re.escape(ref.group(1)) + r' ',
                                   'REF _Clause_cGONE ')))
    else:
        skipped.append('xrefs: the document contains no clause cross-reference')

    typed = _a_typed_member(document_xml, model, doc_ns_index)
    if typed:
        owner, member, data_type = typed
        out.append(('a node table loses a member row', 'node-tables',
                    _drop_member_row(owner, member, data_type)))
        other = 'Int32' if data_type.lstrip('0:') != 'Int32' else 'Boolean'
        out.append(('a member DataType disagrees with the NodeSet', 'node-tables',
                    _corrupt_cell(owner, member, data_type, other)))
    else:
        skipped.append('node-tables: the document defines no type members')

    structure_field = _a_structure_field(
        document_xml, model, doc_ns_index, structure_fields)
    if structure_field:
        type_name, field_name, data_type, cardinality = structure_field
        other = '0:Int32' if data_type != '0:Int32' else '0:Boolean'
        out.append(('a Structure field DataType disagrees with the NodeSet',
                    'data-type-items',
                    _corrupt_items_cell(type_name, field_name, data_type, other)))
        if cardinality == '0..1':
            out.append(('an optional Structure field is printed as mandatory',
                        'data-type-items',
                        _corrupt_items_cell(type_name, field_name, cardinality, '1')))
        out.append(('Structure fields are reordered',
                    'data-type-items', _swap_first_structure_rows(type_name)))
        out.append(('a Structure Items table contains a duplicate field',
                    'data-type-items', _duplicate_first_structure_row(type_name)))
    else:
        skipped.append('data-type-items: the document defines no Structure fields')

    unit = _a_conformance_unit(document_xml, model)
    if unit:
        out.append(('a conformance unit is dropped from the conformance-units clause',
                    'conformance-units', _replace_all(re.escape(unit), 'XX-Renamed')))
    else:
        skipped.append('conformance-units: the model declares none')

    if '.pptx' in rels_xml:        out.append(('an embedded PowerPoint is wired as a compound-file object',
                    'embedded-packages',
                    _replace_first(
                        r'(Type="http://schemas\.openxmlformats\.org/officeDocument/2006/'
                        r'relationships/)package("[^>]*\.pptx")', r'\g<1>oleObject\g<2>'),
                    'word/_rels/document.xml.rels'))
    else:
        skipped.append('embedded-packages: the document embeds no figure')
    return out, skipped


def _a_typed_member(document_xml, model, doc_ns_index):
    """An owning type, a member BrowseName of it, and that member's printed DataType."""
    from opcdocx import nodeset_tables
    for node in model.nodes.values():
        if node.tag != 'UAObjectType' or (node.name + ' definition') not in document_xml:
            continue
        for _, child in model.members_of(node):
            if not child.name.isalnum() or child.name not in document_xml:
                continue
            data_type = nodeset_tables.data_type_cell(model, child,
                                                      doc_ns_index=doc_ns_index)
            if data_type:
                return node.name, child.name, data_type
    return None


def _a_conformance_unit(document_xml, model):
    units = sorted({c for n in model.nodes.values() for c in n.categories})
    for unit in units:
        if document_xml.count(unit) >= 2:
            return unit
    return None


def _a_structure_field(
        document_xml, model, doc_ns_index, structure_fields=False):
    """A rendered Structure field, preferring one whose cardinality is optional."""
    if not structure_fields:
        return None
    from opcdocx import nodeset_tables
    candidates = []
    for node in model.nodes.values():
        if node.tag != 'UADataType' or not node.definition:
            continue
        if (node.name + ' Items') not in document_xml:
            continue
        spec = nodeset_tables.enum_table(
            model, node.name, doc_ns_index=doc_ns_index,
            structure_fields=structure_fields)
        if spec['kind'] != 'structure':
            continue
        for field in spec['fields']:
            if _find_items_row(
                    document_xml, node.name, field['name'], field['type']):
                candidates.append((node.name, field['name'], field['type'],
                                   field['cardinality']))
    return next((c for c in candidates if c[3] == '0..1'),
                candidates[0] if candidates else None)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('config')
    args = ap.parse_args(argv)

    with open(args.config, encoding='utf-8') as f:
        cfg = json.load(f)
    src = os.path.join(REPO, cfg['output']['docx'])
    if not os.path.exists(src):
        print('build the document first: %s is missing' % cfg['output']['docx'])
        return 1

    failures = 0
    tmpdir = tempfile.mkdtemp(prefix='opcdocx-mutation-', dir=os.path.join(REPO, 'word-drafts'))
    try:
        baseline = _run(args.config, src)
        if baseline != 0:
            print('FAIL  the unmutated document does not validate cleanly')
            return 1
        print('ok    baseline document validates cleanly')

        with zipfile.ZipFile(src) as z:
            document_xml = z.read('word/document.xml').decode('utf-8')
            rels_xml = z.read('word/_rels/document.xml.rels').decode('utf-8')
        model = _model_for(cfg)
        derived, skipped = derived_mutations(
            document_xml, rels_xml, model,
            cfg['identity']['namespaceIndexInDocument'],
            cfg.get('structureFieldTables', False))
        for reason in skipped:
            print('skip  %s' % reason)

        for mutation in STATIC_MUTATIONS + derived:
            description, check, transform = mutation[:3]
            part = mutation[3] if len(mutation) > 3 else 'word/document.xml'
            dst = os.path.join(tmpdir, 'mutated.docx')
            try:
                mutate(src, dst, transform, part)
            except AssertionError as exc:
                print('FAIL  %s: %s' % (description, exc))
                failures += 1
                continue
            code, output = _run_capture(args.config, dst)
            caught = code != 0 and ('[%s]' % check) in output
            print('%s  %s -> %s'
                  % ('ok  ' if caught else 'FAIL', description,
                     check if caught else 'NOT CAUGHT'))
            if not caught:
                failures += 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    print('%d mutation(s) escaped detection' % failures)
    return 1 if failures else 0


def _model_for(cfg):
    from opcdocx import nodeset_tables
    if cfg['source'].get('nodeset'):
        return nodeset_tables.Model(os.path.join(REPO, cfg['source']['nodeset']),
                                    cfg.get('requiredModelNodes'))
    return nodeset_tables.NullModel(
        model_uri=cfg['identity']['namespaceUri'],
        version=cfg['identity']['version'],
        publication_date=cfg['identity']['publicationDate'])


def _run(config, docx):
    code, _ = _run_capture(config, docx)
    return code


def _run_capture(config, docx):
    buf = io.StringIO()
    stdout = sys.stdout
    sys.stdout = buf
    try:
        code = validate_docx.main([config, '--docx', docx])
    finally:
        sys.stdout = stdout
    return code, buf.getvalue()


if __name__ == '__main__':
    raise SystemExit(main())
