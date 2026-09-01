"""Point a model generator at `model/<group>/<spec>/`, and stop Annex A injection.

Two consequences of the conversion, both in the `__main__` block.

The NodeSet and its NodeIds CSV go to the owning specification's mirrored model directory
rather than beside the prose. `inject()` -- which wrote the generated Annex A into the
markdown -- has nothing left to do: the annex is now a `{clause} kind: annex-a` directive
that the publisher fills from the same NodeSet.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

OUTDIR = re.compile(r'^(\s*)outdir = (?:os\.path\.dirname\(here\)'
                    r'|os\.path\.abspath\(os\.path\.join\(here, "\.\."\)\))[^\n]*$', re.M)
# `if inject(os.path.join(outdir, "...")` and its indented body, to the end of the block.
INJECT_LOOP_HEAD = re.compile(
    r'^([ \t]*)for [^\n]+:\n(?=\1[ \t]+if inject\()', re.M)
INJECT = re.compile(r'^([ \t]*)if inject\(.*?\n(?:\1[ \t]+.*\n|[ \t]*\n)*', re.M)


def patch(path: pathlib.Path, root: pathlib.Path, write: bool) -> tuple[bool, str | None]:
    text = path.read_text(encoding='utf-8')
    if 'outdir' not in text:
        return False, 'no outdir to repoint'
    spec_dir = path.parent.parent.relative_to(root / 'source')
    model_parts = ', '.join('"%s"' % part for part in ('model', *spec_dir.parts))

    def replacement(match):
        indent = match.group(1)
        return (
            f'{indent}# The NodeSet and its CSV belong to the owning specification\n'
            f'{indent}# under model/<group>/<spec>/.\n'
            f'{indent}outdir = os.path.abspath(os.path.join(\n'
            f'{indent}    here, os.pardir, os.pardir, os.pardir, os.pardir, '
            f'{model_parts}))\n'
            f'{indent}os.makedirs(outdir, exist_ok=True)')

    updated, n = OUTDIR.subn(replacement, text, count=1)
    if n == 0:
        return False, 'outdir is not one of the two known shapes; check by hand'
    updated, loop = INJECT_LOOP_HEAD.subn('', updated)
    updated, injected = INJECT.subn('', updated)
    if write:
        path.write_text(updated, encoding='utf-8', newline='\n')
    removed = injected + loop
    return True, ('inject() call removed' if removed else 'no inject() call to remove')


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('root', type=pathlib.Path)
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args(argv)

    for py in sorted((args.root / 'source').rglob('tools/build_model.py')):
        ok, note = patch(py, args.root, args.write)
        rel = py.relative_to(args.root).as_posix()
        print('%s %s (%s)' % ('ok  ' if ok else 'SKIP', rel, note))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
