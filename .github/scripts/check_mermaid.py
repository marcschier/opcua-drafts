#!/usr/bin/env python3
"""Render/parse every fenced ```mermaid block in the repository's Markdown files.

Each block is extracted (dedented to handle diagrams nested under list items) and compiled with
the Mermaid CLI (`mmdc`). A block that fails to compile is a syntax error (for example an unquoted
`;` in a note, or a bad edge).

Requires the Mermaid CLI on PATH, or set MMDC to its path, or have `npx` available (the script will
fall back to `npx -y @mermaid-js/mermaid-cli mmdc`). Rendering needs a headless Chromium.

Usage (from repo root):  python .github/scripts/check_mermaid.py
Exit code is non-zero if any diagram fails to compile.
"""
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SKIP_DIRS = {".git", "node_modules", "__pycache__"}
OPEN_RE = re.compile(r"^(\s*)```mermaid\s*$")
CLOSE_RE = re.compile(r"^\s*```\s*$")


def md_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.lower().endswith(".md"):
                yield os.path.join(dirpath, name)


def blocks(path):
    """Yield (start_line, dedented_source) for each mermaid block in a file."""
    lines = open(path, encoding="utf-8").read().splitlines()
    i = 0
    while i < len(lines):
        m = OPEN_RE.match(lines[i])
        if not m:
            i += 1
            continue
        indent = len(m.group(1))
        start = i + 1
        buf = []
        i += 1
        while i < len(lines) and not CLOSE_RE.match(lines[i]):
            buf.append(lines[i][indent:] if lines[i][:indent].strip() == "" else lines[i])
            i += 1
        i += 1  # consume closing fence
        yield start, "\n".join(buf)


def mmdc_cmd():
    env = os.environ.get("MMDC")
    if env:
        cmd = shlex.split(env, posix=(os.name != "nt"))
    elif shutil.which("mmdc"):
        cmd = [shutil.which("mmdc")]
    else:
        npx = shutil.which("npx")
        if not npx:
            return None
        cmd = [npx, "-y", "@mermaid-js/mermaid-cli", "mmdc"]
    # On CI (headless Linux) Chromium needs --no-sandbox; supply it via a puppeteer config if present.
    pcfg = os.path.join(ROOT, ".github", "puppeteer-config.json")
    if os.path.exists(pcfg):
        cmd += ["-p", pcfg]
    return cmd


def run_mmdc(cmd):
    # On Windows, npm installs `mmdc` as a .cmd shim that CreateProcess cannot launch directly;
    # route it through the shell. On POSIX (incl. CI) mmdc is a normal executable.
    if os.name == "nt" and cmd and cmd[0].lower().endswith((".cmd", ".bat")):
        cmd = ["cmd", "/c"] + cmd
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    cmd = mmdc_cmd()
    if cmd is None:
        print("check_mermaid: ERROR - no mmdc / npx available", file=sys.stderr)
        return 2
    total, failed = 0, 0
    rel = lambda p: os.path.relpath(p, ROOT).replace(os.sep, "/")
    with tempfile.TemporaryDirectory() as tmp:
        for md in md_files():
            for n, (line, src) in enumerate(blocks(md), start=1):
                total += 1
                mmd = os.path.join(tmp, f"d{total}.mmd")
                out = os.path.join(tmp, f"d{total}.svg")
                open(mmd, "w", encoding="utf-8").write(src)
                proc = run_mmdc(cmd + ["-i", mmd, "-o", out])
                if proc.returncode != 0 or not os.path.exists(out):
                    failed += 1
                    err = (proc.stderr or proc.stdout or "").strip().splitlines()
                    detail = err[0] if err else "unknown error"
                    print(f"  FAIL {rel(md)} block #{n} (line {line}): {detail}")
    if failed:
        print(f"check_mermaid: {failed} of {total} diagrams failed to compile")
        return 1
    print(f"check_mermaid: OK ({total} diagrams compiled)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
