#!/usr/bin/env python3
"""Remove a returned specification's private copy using the release manifest API."""

from __future__ import annotations

import argparse
from pathlib import Path

from manifest import load as load_manifest


def remove_empty_parents(path: Path, root: Path) -> None:
    parent = path.parent
    while parent != root and parent.is_relative_to(root):
        try:
            parent.rmdir()
        except OSError:
            return
        parent = parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec_id")
    parser.add_argument("--root", required=True, help="private repository checkout root")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest = load_manifest()
    root = Path(args.root).resolve()
    removed: list[str] = []
    missing: list[str] = []

    for rel in manifest.file_set(args.spec_id):
        target = (root / Path(*rel.split("/"))).resolve()
        if not target.is_relative_to(root):
            raise SystemExit(f"manifest path escapes private checkout: {rel}")
        if target.exists():
            removed.append(rel)
            if not args.dry_run:
                if target.is_dir():
                    raise SystemExit(f"manifest file set unexpectedly contains a directory: {rel}")
                target.unlink()
                remove_empty_parents(target, root)
        else:
            missing.append(rel)

    for rel in removed:
        print(f"remove {rel}")
    for rel in missing:
        print(f"missing {rel}")

    if not removed:
        raise SystemExit("no private files matched the manifest file set")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
