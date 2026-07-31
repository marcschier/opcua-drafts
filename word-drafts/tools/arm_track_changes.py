#!/usr/bin/env python3
"""Re-arm Word's change tracking in a finalised document.

    python word-drafts/tools/arm_track_changes.py word-drafts/OPC-UA-xRegistry.docx

The build writes `w:trackChanges` into `word/settings.xml`, but Word rewrites that part from
its own state whenever it actually changes the document — and its own state says tracking is
off — so the finalise pass drops it. Setting the COM property instead does not work: setting
it False removes the element and setting it back True does not restore it. The reliable
place is the package, once Word has closed the file, which is what this does.

`finalize_word.ps1` runs it automatically; it is idempotent, so running it again is safe.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opcdocx.package import arm_track_changes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('docx', nargs='+')
    args = ap.parse_args(argv)

    for path in args.docx:
        changed = arm_track_changes(path)
        print('%s change tracking in %s'
              % ('armed' if changed else 'already armed:', os.path.basename(path)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
