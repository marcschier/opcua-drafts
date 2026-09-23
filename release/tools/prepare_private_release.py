#!/usr/bin/env python3
"""Stage explicitly routed specification content without replacing review infrastructure."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from manifest import load as load_manifest
from review_routes import checked_path, closure_routes, public_file_map, require_review_repository, translated_content, under


def prepare(spec_id: str, root: Path, export: Path, manifest=None) -> list[str]:
    manifest = manifest or load_manifest()
    spec = manifest.spec(spec_id)
    if spec.get("submitted") is not True:
        raise RuntimeError(f"{spec_id}: only submitted specifications can enter review")
    routes = closure_routes(manifest, spec_id)
    route = routes[spec_id]
    files = sorted(path.relative_to(export).as_posix() for path in export.rglob("*") if path.is_file())
    if not files:
        raise RuntimeError("release export is empty")
    if route.legacy_layout:
        allowed = [path for key in routes for path in manifest.spec(key)["move"]]
        allowed += manifest.sharedTooling
        unexpected = [path for path in files if not any(under(path, prefix) for prefix in allowed)]
        if unexpected:
            raise RuntimeError("unapproved export content: " + ", ".join(unexpected))
        mapping = ({path: path for path in files} if route.identity_layout
                   else public_file_map(manifest, spec_id, files))
    else:
        mapping = public_file_map(manifest, spec_id, files)
    if not mapping:
        raise RuntimeError("export contains no transferable specification content")

    # Preflight the entire batch. A conflict must not leave a partly overwritten checkout.
    contents = {}
    for public, review in mapping.items():
        route.require_content(review)
        source = checked_path(export, public)
        target = checked_path(root, review)
        if not source.is_file():
            raise RuntimeError(f"missing export file: {public}")
        contents[review] = translated_content(manifest, spec_id, public, review, source.read_bytes())
        if target.exists() and (not target.is_file() or target.read_bytes() != contents[review]):
            raise RuntimeError(
                f"destination has different content at {review}; reconcile the source and destination "
                "edits on the review branch before retrying (no files were overwritten)")
    for public, review in mapping.items():
        source = checked_path(export, public)
        target = checked_path(root, review)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(contents[review])
    print(f"prepared {spec_id} for {route.repository}: {len(mapping)} content file(s); infrastructure retained")
    return sorted(mapping.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec_id")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--export", required=True, type=Path)
    args = parser.parse_args()
    root, export = args.root.resolve(), args.export.resolve()
    if not root.is_dir() or not export.is_dir():
        parser.error("review checkout and export directory must both exist")
    try:
        manifest = load_manifest()
        require_review_repository(root, manifest.review_route(args.spec_id).repository)
        prepare(args.spec_id, root, export, manifest)
    except (KeyError, OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
