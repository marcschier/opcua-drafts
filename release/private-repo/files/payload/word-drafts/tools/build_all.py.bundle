#!/usr/bin/env python3
"""Build, validate and mutation-test every converted specification.

    python word-drafts/tools/build_all.py            # the whole batch
    python word-drafts/tools/build_all.py --list     # what is converted and what is ready
    python word-drafts/tools/build_all.py xregistry generators

The batch is `specs/batch.json`, which also records the specifications the pipeline could
take next and the editorial work each one still needs. Finalising in Word stays a separate,
local step (`finalize_word.ps1`), because it needs Word and is not byte-deterministic.
"""

import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BATCH = os.path.join(HERE, 'specs', 'batch.json')

STEPS = ('build_docx.py', 'validate_docx.py', 'test_validate_docx.py')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('specs', nargs='*', help='spec ids; defaults to the whole batch')
    ap.add_argument('--list', action='store_true', help='show the inventory and exit')
    ap.add_argument('--skip-mutations', action='store_true',
                    help='build and validate only')
    args = ap.parse_args(argv)

    with open(BATCH, encoding='utf-8') as f:
        batch = json.load(f)

    if args.list:
        print('converted (%d):' % len(batch['converted']))
        for spec in batch['converted']:
            print('    %s' % spec)
        print('\nready, needs a config file plus the work named (%d):'
              % len(batch['ready']))
        for entry in batch['ready']:
            print('    %-24s %s' % (entry['id'], entry['needs']))
        print('\nnot a fit (%d):' % len(batch['notAFit']))
        for entry in batch['notAFit']:
            print('    %s' % entry['markdown'])
            print('        %s' % entry['why'])
        return 0

    specs = args.specs or batch['converted']
    unknown = [s for s in specs if not os.path.exists(_config(s))]
    if unknown:
        print('no config for: %s' % ', '.join(unknown))
        return 2

    steps = STEPS[:-1] if args.skip_mutations else STEPS
    failed = []
    for spec in specs:
        for step in steps:
            code = subprocess.call([sys.executable, os.path.join(HERE, step),
                                    _config(spec)])
            if code != 0:
                failed.append('%s: %s' % (spec, step))
                break
        else:
            print('ok    %s' % spec)

    print('\n%d of %d specification(s) built, validated and mutation-tested'
          % (len(specs) - len(failed), len(specs)))
    for f in failed:
        print('FAIL  %s' % f)
    return 1 if failed else 0


def _config(spec):
    return os.path.join(HERE, 'specs', '%s.json' % spec)


if __name__ == '__main__':
    raise SystemExit(main())
