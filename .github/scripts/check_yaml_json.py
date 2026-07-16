#!/usr/bin/env python3
"""Check that every tracked JSON and YAML file parses.

Covers descriptors, schemas, GitHub issue forms, and workflows. JSON uses the stdlib; YAML uses
PyYAML when available (install with `pip install pyyaml`) and is otherwise skipped with a notice.
The GitHub issue forms under .github/ISSUE_TEMPLATE are additionally checked for the required
`name` / `description` / `body` keys.

Usage (from repo root):  python .github/scripts/check_yaml_json.py
Exit code is non-zero if any file fails to parse.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP_DIRS = {".git", "node_modules", "__pycache__"}

try:
    import yaml  # type: ignore
    HAVE_YAML = True
except Exception:
    HAVE_YAML = False


def walk(exts):
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if os.path.splitext(name)[1].lower() in exts:
                yield os.path.join(dirpath, name)


def main():
    rel = lambda p: os.path.relpath(p, ROOT).replace(os.sep, "/")
    errors = []
    n_json = n_yaml = 0

    for path in walk({".json"}):
        n_json += 1
        try:
            json.load(open(path, encoding="utf-8"))
        except Exception as e:
            errors.append((rel(path), str(e)))

    if HAVE_YAML:
        for path in walk({".yml", ".yaml"}):
            n_yaml += 1
            try:
                doc = yaml.safe_load(open(path, encoding="utf-8"))
            except Exception as e:
                errors.append((rel(path), str(e)))
                continue
            if os.sep + "ISSUE_TEMPLATE" + os.sep in path and isinstance(doc, dict):
                missing = [k for k in ("name", "description", "body") if k not in doc]
                if missing:
                    errors.append((rel(path), f"issue form missing keys: {', '.join(missing)}"))
    else:
        print("check_yaml_json: note - PyYAML not installed, YAML files not checked")

    if errors:
        print(f"check_yaml_json: {len(errors)} file(s) failed")
        for path, why in errors:
            print(f"  {path}: {why}")
        return 1
    print(f"check_yaml_json: OK ({n_json} JSON, {n_yaml} YAML parsed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
