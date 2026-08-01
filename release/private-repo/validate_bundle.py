#!/usr/bin/env python3
"""Validate the inert private-repo bootstrap bundle.

Checks that every manifest entry exists, hashes match, destinations are safe, stored paths
are inert, and stored YAML/JSON parses according to its destination extension.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
FILES = BASE / 'files'
MANIFEST = BASE / 'manifest.json'
TEXT_EXTS = {'.md', '.txt', '.py', '.ps1', '.yml', '.yaml', '.json'}

try:
    import yaml  # type: ignore
except Exception:  # noqa: BLE001 - validation must say exactly what is missing
    yaml = None


def main() -> int:
    problems: list[str] = []
    try:
        manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    except Exception as exc:  # noqa: BLE001
        print(f'validate_bundle: manifest is not valid JSON: {exc}')
        return 1
    entries = manifest.get('files') if manifest.get('version') == 1 else None
    if not isinstance(entries, list):
        print('validate_bundle: manifest must have version=1 and a files array')
        return 1

    seen_stored: set[str] = set()
    seen_dest: set[str] = set()
    expected_stored = set()
    for i, entry in enumerate(entries, 1):
        stored_s = entry.get('stored')
        dest_s = entry.get('destination')
        digest = entry.get('sha256')
        if not all(isinstance(x, str) for x in (stored_s, dest_s, digest)):
            problems.append(f'entry {i}: stored, destination and sha256 must be strings')
            continue
        stored = Path(stored_s)
        dest = Path(dest_s)
        expected_stored.add(stored_s)
        if stored.is_absolute() or '..' in stored.parts:
            problems.append(f'{stored_s}: unsafe stored path')
            continue
        if dest.is_absolute() or '..' in dest.parts:
            problems.append(f'{dest_s}: unsafe destination path')
            continue
        if any(part == '.github' for part in stored.parts) or stored.suffix != '.bundle':
            problems.append(f'{stored_s}: stored path is not inert')
        if stored_s in seen_stored:
            problems.append(f'{stored_s}: duplicate stored path')
        if dest_s in seen_dest:
            problems.append(f'{dest_s}: duplicate destination path')
        seen_stored.add(stored_s)
        seen_dest.add(dest_s)
        path = FILES / stored
        if not path.exists():
            problems.append(f'{stored_s}: missing stored file')
            continue
        data = path.read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != digest:
            problems.append(f'{stored_s}: sha256 mismatch')
        dest_suffix = dest.suffix.lower()
        if dest_suffix == '.json':
            try:
                json.loads(data.decode('utf-8-sig'))
            except Exception as exc:  # noqa: BLE001
                problems.append(f'{dest_s}: JSON parse failed: {exc}')
        elif dest_suffix in {'.yml', '.yaml'}:
            if yaml is None:
                problems.append(f'{dest_s}: YAML validation requires PyYAML (pip install pyyaml)')
            else:
                try:
                    yaml.safe_load(data.decode('utf-8-sig'))
                except Exception as exc:  # noqa: BLE001
                    problems.append(f'{dest_s}: YAML parse failed: {exc}')

    actual_stored = {p.relative_to(FILES).as_posix() for p in FILES.rglob('*') if p.is_file()}
    for extra in sorted(actual_stored - expected_stored):
        problems.append(f'{extra}: stored file is not listed in manifest')

    if problems:
        print(f'validate_bundle: {len(problems)} problem(s)')
        for problem in problems:
            print(f'  {problem}')
        return 1
    print(f'validate_bundle: OK ({len(entries)} manifest file(s))')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
