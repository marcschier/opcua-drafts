"""Move a converted specification's remaining files into the template layout.

`convert_spec.py` writes the manifest, the prose and the profiles into
`source/<group>/<name>/`. What is left in the old directory is everything the conversion did
not read: the generator, the README, the sibling documents, the example NodeSets. This moves
them, with `git mv` so the history follows, and it puts every NodeSet and NodeIds CSV in
`model/` -- which is where the tool's own documentation puts them, because a part borrows types
from the siblings it is published with and resolution is by ModelUri rather than by directory.

The documents the conversion already read are deleted rather than moved: the main markdown
became `spec.md`, and each addendum became the part named for it.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent


def git(*args) -> int:
    return subprocess.run(['git', *args], cwd=REPO).returncode


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('spec', help='name of a word-drafts/tools/specs/<spec>.json, or --config')
    ap.add_argument('--from', dest='src', required=True, help='the old directory')
    ap.add_argument('--config', type=pathlib.Path,
                    help='a build config elsewhere, for a specification with no Word rendering')
    ap.add_argument('--group', required=True)
    ap.add_argument('--name', required=True)
    args = ap.parse_args(argv)

    cfg_path = args.config or (HERE / 'specs' / ('%s.json' % args.spec))
    cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
    src = REPO / args.src
    dest = REPO / 'source' / args.group / args.name
    model = REPO / 'model'
    model.mkdir(parents=True, exist_ok=True)

    consumed = {REPO / cfg['source']['markdown']}
    consumed |= {REPO / p for p in (cfg.get('additionalMarkdown') or {}).values()}

    for path in sorted(src.rglob('*')):
        if path.is_dir():
            continue
        if path in consumed:
            git('rm', '-q', str(path.relative_to(REPO)).replace('\\', '/'))
            continue
        if path.suffix == '.xml' and path.name.endswith('.NodeSet2.xml'):
            target = model / path.name
        elif path.name.endswith('.NodeIds.csv'):
            target = model / path.name
        else:
            target = dest / path.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        git('mv', str(path.relative_to(REPO)).replace('\\', '/'),
            str(target.relative_to(REPO)).replace('\\', '/'))

    print('moved %s -> %s (NodeSets to model/)' % (args.src, dest.relative_to(REPO)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
