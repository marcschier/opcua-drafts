#!/usr/bin/env python3
"""Check internal Markdown links across the repository.

For every tracked `*.md` file, resolve each relative link target on disk and every in-page
`#anchor` against the target file's headings (GitHub-slugged) and explicit `id="..."` anchors.
External links (http/https/mailto) and non-file schemes are skipped.

Usage (from repo root):  python .github/scripts/check_links.py
Exit code is non-zero if any internal link is broken.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SKIP_DIRS = {".git", "node_modules", "__pycache__"}
LINK_RE = re.compile(r"(?<!\\)\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
EXPLICIT_ID_RE = re.compile(r'<[a-zA-Z][^>]*?\b(?:id|name)\s*=\s*"([^"]+)"')
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def md_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.lower().endswith(".md"):
                yield os.path.join(dirpath, name)


def slug(text):
    """Approximate GitHub's heading-to-anchor slug."""
    text = re.sub(r"<[^>]+>", "", text)          # strip HTML tags
    text = re.sub(r"[`*_~]", "", text)           # strip basic inline markdown
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links -> link text
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]+", "", text, flags=re.UNICODE)  # drop punctuation
    text = text.replace(" ", "-")
    return text


def anchors_of(path):
    """Return the set of valid in-page anchors for a Markdown file."""
    ids = set()
    counts = {}
    in_fence = False
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return ids
    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            s = slug(m.group(2))
            if s in counts:
                counts[s] += 1
                ids.add(f"{s}-{counts[s]}")
            else:
                counts[s] = 0
                ids.add(s)
        for mid in EXPLICIT_ID_RE.finditer(line):
            ids.add(mid.group(1))
    return ids


def is_external(target):
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", target)) or target.startswith("//")


def main():
    anchor_cache = {}
    broken = []
    checked = 0
    for md in md_files():
        base = os.path.dirname(md)
        text = open(md, encoding="utf-8").read()
        # ignore fenced code when scanning for links
        stripped, in_fence = [], False
        for line in text.splitlines():
            if FENCE_RE.match(line):
                in_fence = not in_fence
                stripped.append("")
                continue
            stripped.append("" if in_fence else line)
        for m in LINK_RE.finditer("\n".join(stripped)):
            target = m.group(1).strip()
            if not target or is_external(target) or target.startswith("<"):
                continue
            target = target.split(" ")[0]            # drop optional "title"
            path_part, _, frag = target.partition("#")
            checked += 1
            if path_part:
                dest = os.path.normpath(os.path.join(base, path_part))
                if not os.path.exists(dest):
                    broken.append((md, target, "missing file"))
                    continue
            else:
                dest = md
            if frag and dest.lower().endswith(".md"):
                if dest not in anchor_cache:
                    anchor_cache[dest] = anchors_of(dest)
                if slug(frag) not in anchor_cache[dest] and frag not in anchor_cache[dest]:
                    broken.append((md, target, "missing anchor"))
    rel = lambda p: os.path.relpath(p, ROOT).replace(os.sep, "/")
    if broken:
        print(f"check_links: {len(broken)} broken of {checked} internal links")
        for md, target, why in broken:
            print(f"  {rel(md)} -> {target}  ({why})")
        return 1
    print(f"check_links: OK ({checked} internal links across markdown files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
