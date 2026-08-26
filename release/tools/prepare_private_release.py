#!/usr/bin/env python3
"""Prepare a private checkout to receive a submitted specification."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
EXPAND_BUNDLE = REPO / "release" / "private-repo" / "expand_bundle.py"

sys.path.insert(0, str(HERE))
from manifest import load as load_manifest  # type: ignore  # noqa: E402


def copy_export(export: Path, root: Path) -> int:
    count = 0
    for source in sorted(export.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(export)
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        count += 1
    if count == 0:
        raise RuntimeError("release export is empty")
    return count


def update_word_batch(root: Path, spec_id: str) -> None:
    path = root / "word-drafts" / "tools" / "specs" / "batch.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    converted = data.get("converted")
    if not isinstance(converted, list) or not all(isinstance(item, str) for item in converted):
        raise RuntimeError(f"{path}: converted must be an array of strings")
    if spec_id not in converted:
        converted.append(spec_id)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_readme(root: Path, title: str, markdown: str) -> None:
    path = root / "README.md"
    text = path.read_text(encoding="utf-8")
    location = Path(markdown).parent.as_posix() + "/"
    row = f"| {title} | `{location}` |"
    if row in text:
        return

    table = re.compile(
        r"(?P<table>"
        r"^\| Specification \| Where \|\r?\n"
        r"^\|---\|---\|\r?\n"
        r"(?:^\|.*\|\r?\n)+"
        r")",
        re.MULTILINE,
    )
    match = table.search(text)
    if match is None:
        raise RuntimeError(f"{path}: specification inventory table not found")
    newline = "\r\n" if "\r\n" in match.group("table") else "\n"
    updated = match.group("table") + row + newline
    path.write_text(text[: match.start()] + updated + text[match.end() :], encoding="utf-8")


def prepare(spec_id: str, root: Path, export: Path) -> None:
    manifest = load_manifest(REPO / "release" / "manifest.json")
    spec = manifest.spec(spec_id)
    if spec.get("submitted") is not True:
        raise RuntimeError(f"{spec_id}: only submitted specifications can enter the private repository")

    word_specs = spec.get("wordSpecs", [])
    if len(word_specs) != 1:
        raise RuntimeError(f"{spec_id}: expected exactly one Word specification descriptor")

    preserved = {}
    for relative in ("README.md", "word-drafts/tools/specs/batch.json"):
        path = root / relative
        if path.exists():
            preserved[relative] = path.read_bytes()

    try:
        subprocess.run(
            [sys.executable, str(EXPAND_BUNDLE), "--target", str(root), "--force"],
            cwd=REPO,
            check=True,
        )
    finally:
        for relative, content in preserved.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

    copied = copy_export(export, root)
    descriptor_path = root / word_specs[0]
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    markdown = descriptor.get("source", {}).get("markdown")
    if not isinstance(markdown, str) or not markdown:
        raise RuntimeError(f"{descriptor_path}: source.markdown is required")

    update_word_batch(root, spec_id)
    update_readme(root, str(spec["title"]), markdown)
    print(f"prepared {spec_id}: {copied} exported file(s), shared tooling refreshed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec_id")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--export", required=True, type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    export = args.export.resolve()
    if not root.is_dir():
        parser.error(f"private checkout does not exist: {root}")
    if not export.is_dir():
        parser.error(f"release export does not exist: {export}")

    try:
        prepare(args.spec_id, root, export)
    except (KeyError, OSError, RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
