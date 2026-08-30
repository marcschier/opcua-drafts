"""Point a specification's own scripts at `model/`, where its NodeSet now lives.

Every generator and validator under `source/<group>/<name>/tools/` built its NodeSet path from
the specification directory, because that is where the file used to sit. It is now in the
repository's `model/`, shared with the siblings the specification is published with, so the
path has to be built from the repository root instead.

The scripts share one shape -- `HERE` is the tools directory, `GEN` its parent -- so this adds
a `MODEL` beside them and moves the NodeSet and NodeIds joins onto it. `GEN` itself is left
alone, because it is also how a script finds things that did not move.

A file that does not have that shape is reported rather than guessed at.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

GEN_ANCHOR = re.compile(r'^(\s*)GEN = os\.path\.dirname\(HERE\)\s*$', re.M)
MODEL_LINE = ('{indent}# The NodeSets live in the repository\'s model/, shared by every '
              'specification\n'
              '{indent}# published together, because resolution is by ModelUri rather than by '
              'directory.\n'
              '{indent}MODEL = os.path.abspath(os.path.join(\n'
              '{indent}    HERE, os.pardir, os.pardir, os.pardir, os.pardir, "model"))\n')

# `os.path.join(GEN, "Opc.Ua.X.NodeSet2.xml")` and the CSV beside it.
OWN = re.compile(r'os\.path\.join\(GEN,\s*("Opc\.Ua\.[^"]*\.(?:NodeSet2\.xml|NodeIds\.csv)")\)')
# `os.path.join(GEN, "..", "<sibling>", "Opc.Ua.X.NodeIds.csv")` -- a borrowed model, which is
# in the same model/ directory now, so the sibling name drops out.
SIBLING = re.compile(r'os\.path\.join\(GEN,\s*"\.\.",\s*"[^"]+",\s*'
                     r'("Opc\.Ua\.[^"]*\.(?:NodeSet2\.xml|NodeIds\.csv)")\)')


def patch(path: pathlib.Path, write: bool) -> tuple[int, str | None]:
    text = path.read_text(encoding='utf-8')
    if 'NodeSet2.xml' not in text and 'NodeIds.csv' not in text:
        return 0, None
    if not GEN_ANCHOR.search(text):
        return 0, 'no `GEN = os.path.dirname(HERE)` to hang MODEL on'

    updated = text
    if 'MODEL = ' not in updated:
        updated = GEN_ANCHOR.sub(
            lambda m: m.group(0) + '\n' + MODEL_LINE.format(indent=m.group(1)).rstrip('\n'),
            updated, count=1)
    updated, n1 = SIBLING.subn(r'os.path.join(MODEL, \1)', updated)
    updated, n2 = OWN.subn(r'os.path.join(MODEL, \1)', updated)
    if n1 + n2 == 0:
        return 0, 'nothing matched the join patterns; check by hand'
    if write:
        path.write_text(updated, encoding='utf-8', newline='\n')
    return n1 + n2, None


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('root', type=pathlib.Path, help='the repository')
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args(argv)

    total = 0
    findings = []
    for py in sorted((args.root / 'source').rglob('tools/*.py')):
        n, why = patch(py, args.write)
        total += n
        if why:
            findings.append('%s: %s' % (py.relative_to(args.root).as_posix(), why))
        elif n:
            print('%s: %d path(s)' % (py.relative_to(args.root).as_posix(), n))

    print('%d path(s) repointed at model/' % total)
    for f in findings:
        print('  %s' % f, file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
