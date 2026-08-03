#!/usr/bin/env python3
"""Materialize the inert private-repo bundle into a target checkout.

The bundle stores files under neutral ``.bundle`` names so this public repository does not
interpret them as live ``.github`` configuration. ``manifest.json`` is the only mapping
from stored path to destination path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
FILES = BASE / 'files'
MANIFEST = BASE / 'manifest.json'


def load_manifest() -> list[dict[str, str]]:
    doc = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if doc.get('version') != 1 or not isinstance(doc.get('files'), list):
        raise SystemExit('manifest.json has an unsupported shape')
    return doc['files']


def verify_entry(entry: dict[str, str]) -> bytes:
    stored = Path(entry['stored'])
    if stored.is_absolute() or '..' in stored.parts:
        raise SystemExit(f'refusing unsafe stored path: {stored}')
    source = FILES / stored
    data = source.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != entry.get('sha256'):
        raise SystemExit(f'hash mismatch for {stored}: {digest} != {entry.get("sha256")}')
    dest = Path(entry['destination'])
    if dest.is_absolute() or '..' in dest.parts:
        raise SystemExit(f'refusing unsafe destination path: {dest}')
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True, help='private repository checkout to populate')
    parser.add_argument('--force', action='store_true', help='overwrite existing files that differ')
    parser.add_argument('--dry-run', action='store_true', help='show actions without writing')
    args = parser.parse_args(argv)

    target = Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    entries = load_manifest()
    wrote = skipped = 0
    for entry in entries:
        data = verify_entry(entry)
        dest_rel = Path(entry['destination'])
        dest = target / dest_rel
        if dest.exists() and dest.read_bytes() == data:
            print(f'OK      {dest_rel.as_posix()}')
            skipped += 1
            continue
        if dest.exists() and not args.force:
            raise SystemExit(f'{dest_rel.as_posix()} exists and differs; rerun with --force')
        print(f'WRITE   {entry["stored"]} -> {dest_rel.as_posix()}')
        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        wrote += 1
    print(f'{wrote} file(s) materialized, {skipped} already current')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
