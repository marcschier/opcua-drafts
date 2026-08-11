#!/usr/bin/env python3
"""Run the self-contained validators owned by companion-specs."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PYTHON = sys.executable

COMMANDS = (
    ("Generators", (PYTHON, "companion-specs/Generators/tools/validate_local.py")),
    (
        "AAS model",
        (PYTHON, "companion-specs/AAS/tools/validate_local.py", "--self-contained"),
    ),
    ("AAS round trip", (PYTHON, "companion-specs/AAS/tools/roundtrip_check.py")),
    ("AAS xRegistry semantics", (PYTHON, "companion-specs/AAS/tools/validate_xregistry_aas.py")),
    (
        "AAS xRegistry regressions",
        (PYTHON, "-m", "unittest", "companion-specs.AAS.tools.test_validate_xregistry_aas"),
    ),
    ("AAS JSON-LD regressions", (PYTHON, "companion-specs/AAS/tools/jsonld/regression_tests.py")),
    ("AAS final examples", (PYTHON, "companion-specs/AAS/tools/jsonld/validate_examples.py")),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_deterministic(name: str, command: tuple[str, ...], paths: list[Path]) -> int:
    """Regenerate once and prove that the committed outputs were already current."""
    before = {path: digest(path) for path in paths}
    print(f"=== {name} ===", flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode:
        print(f"FAILED: {name}", file=sys.stderr)
        return result.returncode
    changed = [str(path.relative_to(ROOT)) for path in paths if digest(path) != before[path]]
    if changed:
        print(
            f"FAILED: {name} changed generated output: {', '.join(changed)}",
            file=sys.stderr,
        )
        return 1
    return 0


def run_deterministic_tree(
    name: str,
    command: tuple[str, ...],
    root: Path,
    pattern: str,
) -> int:
    """Regenerate a variable output set and check both bytes and membership."""
    before_paths = sorted(root.rglob(pattern))
    before = {path: digest(path) for path in before_paths}
    print(f"=== {name} ===", flush=True)
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode:
        print(f"FAILED: {name}", file=sys.stderr)
        return result.returncode

    after_paths = sorted(root.rglob(pattern))
    before_rel = {path.relative_to(ROOT) for path in before_paths}
    after_rel = {path.relative_to(ROOT) for path in after_paths}
    if before_rel != after_rel:
        added = sorted(str(path) for path in after_rel - before_rel)
        removed = sorted(str(path) for path in before_rel - after_rel)
        print(
            f"FAILED: {name} changed generated file set; "
            f"added={added or '-'} removed={removed or '-'}",
            file=sys.stderr,
        )
        return 1

    changed = [str(path.relative_to(ROOT)) for path in after_paths if digest(path) != before[path]]
    if changed:
        print(
            f"FAILED: {name} changed generated output: {', '.join(changed)}",
            file=sys.stderr,
        )
        return 1

    untracked = []
    for path in after_paths:
        result = subprocess.run(
            ("git", "ls-files", "--error-unmatch", str(path.relative_to(ROOT))),
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode:
            untracked.append(str(path.relative_to(ROOT)))
    if untracked:
        print(
            f"FAILED: {name} generated untracked output: {', '.join(untracked)}",
            file=sys.stderr,
        )
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-contained",
        action="store_true",
        help="accepted for parity with the other tree aggregates; every companion gate is self-contained",
    )
    parser.parse_args(argv)

    model_outputs = [
        ROOT / "companion-specs/AAS/Opc.Ua.I4AAS.NodeSet2.xml",
        ROOT / "companion-specs/AAS/Opc.Ua.I4AAS.NodeIds.csv",
        ROOT / "companion-specs/AAS/tools/model-reference.md",
        ROOT / "companion-specs/AAS/OPC-UA-AAS.md",
    ]
    if run_deterministic(
        "AAS regeneration",
        (PYTHON, "companion-specs/AAS/tools/build_model.py"),
        model_outputs,
    ):
        return 1

    if run_deterministic_tree(
        "AAS example regeneration",
        (PYTHON, "companion-specs/AAS/tools/jsonld/build_examples.py"),
        ROOT / "companion-specs/AAS/examples",
        "*.jsonld",
    ):
        return 1

    for name, command in COMMANDS:
        print(f"=== {name} ===", flush=True)
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            print(f"FAILED: {name}", file=sys.stderr)
            return result.returncode
    print("\nALL COMPANION EXTENSIONS VALIDATED OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
