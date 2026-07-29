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


MUTATIONS = [
    ('a node table loses a member row',
     'node-tables',
     _drop_first(r'<w:tr[^>]*>(?:(?!</w:tr>).)*?RootLayerIdentifier.*?</w:tr>')),
    ('a member DataType disagrees with the NodeSet',
     'node-tables',
     _replace_first(r'(<w:t[^>]*>)0:Guid(</w:t>)', r'\g<1>0:Int32\g<2>')),
    ('a table caption loses its SEQ field',
     'table-captions',
     _drop_first(r'<w:instrText[^>]*> SEQ Table \\\* ARABIC </w:instrText>')),
    ('a heading is given a literal clause number',
     'heading-numbers',
     _replace_first(r'(<w:pStyle w:val="Heading1"/>.*?<w:t[^>]*>)Scope',
                    r'\g<1>1 Scope')),
    ('a cross-reference points at a bookmark that does not exist',
     'xrefs',
     _replace_first(r'REF _Clause_c7_11 ', 'REF _Clause_cGONE ')),
    ('a forbidden online-reference link appears in the body',
     'forbidden-links',
     _replace_first(r'(<w:pStyle w:val="Heading1"/></w:pPr>)',
                    r'\g<1><w:r><w:t>see '
                    r'https://reference.opcfoundation.org/specs/OPC-10000-3/</w:t></w:r>')),
    ('a retained template clause is deleted',
     'template-slices',
     _drop_first(r'<w:t[^>]*>[^<]*royalty[^<]*</w:t>')),
    ('an embedded PowerPoint is wired as a compound-file object',
     'embedded-packages',
     _replace_first(r'(Type="http://schemas\.openxmlformats\.org/officeDocument/2006/'
                    r'relationships/)package("[^>]*\.pptx")', r'\g<1>oleObject\g<2>'),
     'word/_rels/document.xml.rels'),
]


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

        for mutation in MUTATIONS:
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
