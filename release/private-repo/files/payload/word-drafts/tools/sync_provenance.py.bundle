#!/usr/bin/env python3
"""Bring a document's provenance sidecar back in line after Word has touched it.

    python word-drafts/tools/sync_provenance.py word-drafts/OPC-UA-xRegistry.docx

The build stamps a `w14:paraId` on every paragraph it writes and records what each one
addresses. Word then adds ids of its own — to the template's retained paragraphs, which
the template shipped without them — so a finalised document contains ids the sidecar has
never heard of.

Left alone, that is not cosmetic. The ingest reads an unknown id as *a paragraph the
reviewer created*, so a mark on the cover page would be reported as new text rather than
as an edit to the template. Recording Word's ids as template-owned keeps the sidecar a
true description of the document that actually ships.

`finalize_word.ps1` runs this automatically; it is idempotent.
"""

import argparse
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lxml import etree  # noqa: E402

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
W14 = '{http://schemas.microsoft.com/office/word/2010/wordml}'


def sidecar_for(docx_path):
    base = os.path.splitext(docx_path)[0]
    return base + '.provenance.json'


def sync(docx_path):
    """Returns the number of paragraphs added, or None when there is no sidecar."""
    path = sidecar_for(docx_path)
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        prov = json.load(f)

    with zipfile.ZipFile(docx_path) as z:
        document = etree.fromstring(z.read('word/document.xml'))

    paragraphs = prov.setdefault('paragraphs', {})
    present = set()
    added = 0
    for p in document.iter(W + 'p'):
        pid = p.get(W14 + 'paraId')
        if not pid:
            continue
        present.add(pid)
        if pid not in paragraphs:
            paragraphs[pid] = {'owner': 'template'}
            added += 1

    # A paragraph the build wrote and Word then removed would leave a dangling entry, and
    # an address that points at nothing is worse than no address at all.
    for pid in [k for k in paragraphs if k not in present]:
        del paragraphs[pid]

    prov['paragraphs'] = {k: paragraphs[k] for k in sorted(paragraphs)}
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(prov, f, indent=2, ensure_ascii=False)
        f.write('\n')
    return added


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('docx', nargs='+')
    args = ap.parse_args(argv)

    for path in args.docx:
        added = sync(path)
        if added is None:
            print('no provenance sidecar for %s' % os.path.basename(path))
        else:
            print('synced provenance for %s (%d paragraph(s) Word added)'
                  % (os.path.basename(path), added))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
