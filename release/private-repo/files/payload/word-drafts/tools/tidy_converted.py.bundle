"""Apply the conversion's whitespace tidy to markdown already converted.

`convert_to_template.tidy` normalises what the conversion disturbs -- the blank lines left
where a clause or a banner was deleted, the missing ones where a table was inserted, the
trailing spaces. It was added after the first conversion had already run, so this applies it
to the files that missed it rather than converting them again from sources that have moved.

Idempotent: running it on an already-tidy file changes nothing.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import convert_to_template as ctt  # noqa: E402


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('root', type=pathlib.Path)
    ap.add_argument('--write', action='store_true')
    args = ap.parse_args(argv)

    # `upgrade --write` downloads these from the OPC Foundation and overwrites whatever is
    # there. Editing one makes it ours and it is never refreshed again, so a whitespace tidy
    # is exactly the wrong reason to take ownership of it.
    owned = {'agreement-of-use.md'}

    changed = 0
    for md in sorted((args.root / 'source').rglob('*.md')):
        if md.name in owned:
            continue
        before = md.read_text(encoding='utf-8')
        after = '\n'.join(ctt.tidy(before.splitlines())) + '\n'
        if after != before:
            changed += 1
            if args.write:
                md.write_text(after, encoding='utf-8', newline='\n')
            print('%s' % md.relative_to(args.root).as_posix())
    print('%d file(s) %s' % (changed, 'tidied' if args.write else 'would be tidied'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
