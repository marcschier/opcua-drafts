"""Point a model generator at `model/`, and stop it writing Annex A into the prose.

Two consequences of the conversion, both in the `__main__` block.

The NodeSet and its NodeIds CSV go to the repository's `model/` rather than beside the
specification, because that is where the publisher looks and where a sibling can borrow from
them. And `inject()` -- which wrote the generated Annex A into the markdown -- has nothing left
to do: the annex is now a `{clause} kind: annex-a` directive that the publisher fills from the
same NodeSet, so writing it into the prose as well would publish it twice and leave the copy
that can drift.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

OUTDIR = re.compile(r'^(\s*)outdir = (?:os\.path\.dirname\(here\)'
                    r'|os\.path\.abspath\(os\.path\.join\(here, "\.\."\)\))[^\n]*$', re.M)
REPLACEMENT = ('{indent}# The NodeSet and its CSV belong to the repository, not to this\n'
               '{indent}# specification: the publisher reads them from model/, and a sibling\n'
               '{indent}# published alongside borrows types from them by ModelUri.\n'
               '{indent}outdir = os.path.abspath(os.path.join(\n'
               '{indent}    here, os.pardir, os.pardir, os.pardir, os.pardir, "model"))\n'
               '{indent}os.makedirs(outdir, exist_ok=True)')

# `if inject(os.path.join(outdir, "...")` and its indented body, to the end of the block.
INJECT = re.compile(r'^([ \t]*)if inject\(.*?\n(?:\1[ \t]+.*\n|[ \t]*\n)*', re.M)


def patch(path: pathlib.Path, write: bool) -> tuple[bool, str | None]:
    text = path.read_text(encoding='utf-8')
    if 'outdir' not in text:
        return False, 'no outdir to repoint'
    updated, n = OUTDIR.subn(lambda m: REPLACEMENT.format(indent=m.group(1)), text, count=1)
    if n == 0:
        return False, 'outdir is not one of the two known shapes; check by hand'
    updated, injected = INJECT.subn('', updated)
    if write:
        path.write_text(updated, encoding='utf-8', newline='\n')
    return True, ('inject() call removed' if injected else 'no inject() call to remove')


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('root', type=pathlib.Path)
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args(argv)

    for py in sorted((args.root / 'source').rglob('tools/build_model.py')):
        ok, note = patch(py, args.write)
        rel = py.relative_to(args.root).as_posix()
        print('%s %s (%s)' % ('ok  ' if ok else 'SKIP', rel, note))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
