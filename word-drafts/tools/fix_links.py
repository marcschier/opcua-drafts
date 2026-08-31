"""Repoint every relative link the conversion invalidated.

Moving a specification into `source/<group>/<name>/` and its NodeSets into `model/` breaks
every relative link that crossed either boundary, in both directions: the documents that moved
now sit at a different depth, and the documents that did not now point at a path that is gone.

The map comes from git, which already knows what moved: `--find-renames` pairs the old path
with the new one. What git cannot know is that a document was *replaced* rather than moved --
`OPC-UA-xRegistry.md` became `spec.md` -- so those pairs are given.

Every rewrite is a path recomputed from the linking file's own directory, so a link that was
already relative stays relative and one that was already correct is left alone.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
LINK = re.compile(r'(?<!\\)\[([^\]]*)\]\(([^)]+)\)')


def renames_from_git() -> dict[str, str]:
    out = subprocess.run(['git', 'diff', '--cached', '--name-status', '--find-renames'],
                         cwd=REPO, capture_output=True, text=True).stdout
    moved = {}
    for line in out.splitlines():
        parts = line.split('\t')
        if parts[0].startswith('R') and len(parts) == 3:
            moved[parts[1]] = parts[2]
    return moved


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--replaced', type=pathlib.Path,
                    help='JSON of old repo-relative path -> new one, for documents that were '
                         'rewritten rather than moved')
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args(argv)

    moved = renames_from_git()
    if args.replaced:
        moved.update(json.loads(args.replaced.read_text(encoding='utf-8')))
    # Where each file used to be, so a relative link is resolved from the directory it was
    # written in. Resolving it from the new location is what makes `../X` look unexplained:
    # the document moved a level, so the same text now means something else.
    came_from = {new: old for old, new in moved.items()}

    changed = 0
    unresolved = []
    for md in REPO.rglob('*.md'):
        rel = md.relative_to(REPO).as_posix()
        if rel.startswith(('node_modules/', 'spec-drafts/', 'docs/', '_work/')):
            continue
        text = md.read_text(encoding='utf-8')
        origin = REPO / came_from.get(rel, rel)

        def repoint(m):
            nonlocal changed
            target = m.group(2)
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.\-]*:', target) or target.startswith(('#', '//')):
                return m.group(0)
            path, _, frag = target.partition('#')
            if not path:
                return m.group(0)
            here = (origin.parent / path).resolve()
            try:
                old = here.relative_to(REPO).as_posix()
            except ValueError:
                return m.group(0)
            new_target = moved.get(old, old if (REPO / old).exists() else None)
            if new_target is None:
                unresolved.append('%s -> %s' % (rel, target))
                return m.group(0)
            new = os.path.relpath(REPO / new_target, md.parent).replace(os.sep, '/')
            if new == path:
                return m.group(0)
            changed += 1
            return '[%s](%s%s)' % (m.group(1), new, ('#' + frag) if frag else '')

        rewritten = LINK.sub(repoint, text)
        if rewritten != text and args.write:
            md.write_text(rewritten, encoding='utf-8', newline='\n')

    print('%d link(s) repointed across %d rename(s)' % (changed, len(moved)))
    if unresolved:
        print('\n%d link(s) still resolve to nothing and no rename explains them:'
              % len(unresolved), file=sys.stderr)
        for u in sorted(set(unresolved)):
            print('  %s' % u, file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
