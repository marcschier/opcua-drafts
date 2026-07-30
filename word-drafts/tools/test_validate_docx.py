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


def _drop_member_row(row_marker, data_type):
    row_re = _member_row_re(row_marker, data_type)

    def apply(text):
        m = row_re.search(text)
        return text if not m else text[:m.start()] + text[m.end():]
    return apply


def _corrupt_cell(row_marker, was, now):
    """Change one cell inside the table row that declares `row_marker`.

    Substituting the first occurrence in the whole document is not the same thing: a
    DataType name also appears in prose and in its own clause heading, and mutating one
    of those proves nothing about the node tables.
    """
    row_re = _member_row_re(row_marker, was)

    def apply(text):
        m = row_re.search(text)
        if not m:
            return text
        return text[:m.start()] + m.group(0).replace(was, now, 1) + text[m.end():]
    return apply


def derived_mutations(document_xml, rels_xml, model, doc_ns_index):
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
        member, data_type = typed
        out.append(('a node table loses a member row', 'node-tables',
                    _drop_member_row(member, data_type)))
        other = '0:Int32' if data_type != '0:Int32' else '0:Boolean'
        out.append(('a member DataType disagrees with the NodeSet', 'node-tables',
                    _corrupt_cell(member, data_type, other)))
    else:
        skipped.append('node-tables: the document defines no type members')

    unit = _a_conformance_unit(document_xml, model)
    if unit:
        out.append(('a conformance unit is dropped from the conformance-units clause',
                    'conformance-units', _replace_all(re.escape(unit), 'XX-Renamed')))
    else:
        skipped.append('conformance-units: the model declares none')

    if '.pptx' in rels_xml:
        out.append(('an embedded PowerPoint is wired as a compound-file object',
                    'embedded-packages',
                    _replace_first(
                        r'(Type="http://schemas\.openxmlformats\.org/officeDocument/2006/'
                        r'relationships/)package("[^>]*\.pptx")', r'\g<1>oleObject\g<2>'),
                    'word/_rels/document.xml.rels'))
    else:
        skipped.append('embedded-packages: the document embeds no figure')
    return out, skipped


def _a_typed_member(document_xml, model, doc_ns_index):
    """A member BrowseName that appears in a node table, with its printed DataType."""
    from opcdocx import nodeset_tables
    for node in model.nodes.values():
        if node.tag != 'UAObjectType':
            continue
        for _, child in model.members_of(node):
            if not child.name.isalnum() or child.name not in document_xml:
                continue
            data_type = nodeset_tables.data_type_cell(model, child,
                                                      doc_ns_index=doc_ns_index)
            if data_type:
                return child.name, data_type
    return None


def _a_conformance_unit(document_xml, model):
    units = sorted({c for n in model.nodes.values() for c in n.categories})
    for unit in units:
        if document_xml.count(unit) >= 2:
            return unit
    return None


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
            document_xml, rels_xml, model, cfg['identity']['namespaceIndexInDocument'])
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
