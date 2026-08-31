#!/usr/bin/env python3
"""Check internal Markdown links across the repository.

For every tracked `*.md` file, resolve each relative link target on disk and every in-page
`#anchor` against the target file's headings (GitHub-slugged), explicit `id="..."` anchors,
the `{#anchor}` attribute blocks the OPC UA specification template writes on headings and
table captions, and the `id:` a `{figure}` directive declares. External links (http/https/
mailto) and non-file schemes are skipped, and so are the files `upgrade` owns.

Usage (from repo root):  python .github/scripts/check_links.py
Exit code is non-zero if any internal link is broken.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SKIP_DIRS = {".git", "node_modules", "__pycache__",
             # Local, gitignored cache of the pinned upstream AAS example corpus.
             # Fetched by companion-specs/AAS/jsonld/tools/fetch_corpus.py.
             ".corpus",
             # Local cache of the published IDTA submodel templates.
             ".templates"}


def is_nested_repo(path):
    """A directory carrying its own .git is a submodule or nested clone, not part of this tree.

    The private review repository is available to OPC Foundation members as a submodule, and
    its contents belong to its own checks. Scanning it here would make a member's local run
    disagree with CI, which never checks a submodule out.
    """
    return os.path.exists(os.path.join(path, ".git"))


def tool_owned():
    """Paths written by `Opc.Ua.SpecificationPublisher upgrade`, which are not ours to fix.

    The scaffold records what it last wrote, and its documentation cites anchors that stand for
    a real one -- `[](#tbl-x)` in an example of how to cite a table. Reporting those as broken
    would train a reader to ignore this check. A file listed under `yours` has been edited here
    and the tool will never refresh it again, so it *is* ours and stays in scope.
    """
    try:
        with open(os.path.join(ROOT, ".config", "spec-scaffold.json"), encoding="utf-8") as f:
            scaffold = json.load(f)
    except (OSError, ValueError):
        return set()
    mine = set(scaffold.get("yours") or ())
    return {os.path.join(ROOT, *p.split("/"))
            for p in (scaffold.get("files") or {}) if p not in mine}


LINK_RE = re.compile(r"(?<!\\)\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
EXPLICIT_ID_RE = re.compile(r'<[a-zA-Z][^>]*?\b(?:id|name)\s*=\s*"([^"]+)"')
FENCE_RE = re.compile(r"^\s*(```|~~~)")

# The OPC UA specification template writes an anchor as a trailing attribute block rather than
# as an HTML element, on a heading and on a table caption alike: `## Scope {#sec-scope}` and
# `*Table - X Definition* {#tbl-x-definition defines=X}`. Both declare the anchor everything
# else in the document cites.
ATTR_ID_RE = re.compile(r"\{#([A-Za-z0-9][A-Za-z0-9_.:-]*)")
ATTR_BLOCK_RE = re.compile(r"\s*\{#[^}]*\}\s*$")

# A figure declares its anchor inside a directive fence, so it is the one anchor that lives
# where a fence scan would otherwise skip it:
#
#     ```{figure}
#     id: fig-information-model-overview
#     ```
DIRECTIVE_FENCE_RE = re.compile(r"^\s*(?:```|~~~)\{(\w+)\}\s*$")
DIRECTIVE_ID_RE = re.compile(r"^\s*id:\s*(\S+)\s*$")


def md_files():
    owned = tool_owned()
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [
            d for d in dirnames
            if d not in SKIP_DIRS and not is_nested_repo(os.path.join(dirpath, d))
        ]
        for name in filenames:
            if name.lower().endswith(".md"):
                path = os.path.join(dirpath, name)
                if path not in owned:
                    yield path


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
    in_directive = False
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return ids
    for line in lines:
        if FENCE_RE.match(line):
            if not in_fence:
                in_directive = bool(DIRECTIVE_FENCE_RE.match(line))
            else:
                in_directive = False
            in_fence = not in_fence
            continue
        if in_fence:
            if in_directive:
                mid = DIRECTIVE_ID_RE.match(line)
                if mid:
                    ids.add(mid.group(1))
            continue
        m = HEADING_RE.match(line)
        if m:
            s = slug(ATTR_BLOCK_RE.sub("", m.group(2)))
            if s in counts:
                counts[s] += 1
                ids.add(f"{s}-{counts[s]}")
            else:
                counts[s] = 0
                ids.add(s)
        for mid in EXPLICIT_ID_RE.finditer(line):
            ids.add(mid.group(1))
        for mid in ATTR_ID_RE.finditer(line):
            ids.add(mid.group(1))
    return ids


def normative_reference_ids(path):
    """The `ref-<id>` anchors a specification's manifest defines.

    A citation of another standard resolves against `manifest.json` -> `normativeReferences`,
    not against a heading: clause 2 is generated from that list, so the anchor exists in the
    published document and nowhere in the markdown. Every part of one specification shares the
    one manifest, so the lookup walks up to the directory holding it.
    """
    directory = os.path.dirname(os.path.abspath(path))
    while True:
        candidate = os.path.join(directory, "manifest.json")
        if os.path.exists(candidate):
            try:
                with open(candidate, encoding="utf-8") as f:
                    manifest = json.load(f)
            except (OSError, ValueError):
                return set()
            return {"ref-%s" % r["id"] for r in manifest.get("normativeReferences", [])
                    if isinstance(r, dict) and r.get("id")}
        parent = os.path.dirname(directory)
        if parent == directory or len(directory) <= len(ROOT):
            return set()
        directory = parent


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
                    anchor_cache[dest] = anchors_of(dest) | normative_reference_ids(dest)
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
