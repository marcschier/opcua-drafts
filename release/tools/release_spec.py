#!/usr/bin/env python3
"""Move draft specifications between the public and private review repositories.

The manifest is the source of truth for which files belong to a specification.
This tool only repairs repository structure around that move: aggregate
validators, Markdown links, Word conversion batches, and agent allow-lists.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import posixpath
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

sys.path.insert(0, str(HERE))
try:
    from manifest import load as load_manifest  # type: ignore
except ImportError as exc:  # pragma: no cover - exercised when the parallel task has not landed.
    raise SystemExit(
        "release/tools/manifest.py is required. "
        "It is owned by the manifest task and was not found."
    ) from exc


VALIDATOR_MARKER = "release-spec-validator"
MD_MARKER = "release-spec-link"
AGGREGATE_VALIDATORS = (
    "extras/core-specs/validate_all.py",
    "extras/cloud-specs/validate_all.py",
    "extras/metaverse-specs/validate_all.py",
    "extras/companion-specs/validate_all.py",
    "extras/wot-specs/validate_all.py",
)
WORD_BATCH = "word-drafts/tools/specs/batch.json"
AGENT_TASK = ".github/workflows/agent-task.yml"
CANONICAL_ALLOWED_PATHS = [
    "source",
    "model",
    "extras",
    "core-specs",
    "cloud-specs",
    "metaverse-specs",
    "wot-specs",
    "companion-specs",
    "word-drafts/tools",
]
CANONICAL_WORD_ORDER = [
    "openusd-binding",
    "openusd-scene",
    "xregistry",
    "observability-export",
    "wot-connectivity",
    "wot-binding",
    "schema-registry",
    "generators",
    "data-channels",
    "avro-encoding",
    "arrow-encoding",
    "async-services",
    "vision",
    "ai-model-management",
    "robot-intent",
    "aas",
]
IGNORED_GENERATED_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
IGNORED_GENERATED_SUFFIXES = {".pyc", ".pyo"}


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO).as_posix()


def repo_path(repo_rel: str) -> Path:
    return REPO / Path(*repo_rel.split("/"))


def norm(repo_rel: str) -> str:
    return repo_rel.replace("\\", "/").strip("/")


def b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def unb64(text: str) -> str:
    return base64.b64decode(text.encode("ascii")).decode("utf-8")


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def split_line_ending(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    if line.endswith("\r"):
        return line[:-1], "\r"
    return line, ""


def match_eol(text: str, template: str) -> str:
    if "\r\n" in template:
        return text.replace("\n", "\r\n")
    return text


def is_probably_text(path: Path) -> bool:
    return path.suffix.lower() in {
        ".md",
        ".py",
        ".json",
        ".yml",
        ".yaml",
        ".txt",
        ".ps1",
        ".toml",
        ".csv",
        ".xml",
        ".jsonld",
        ".ttl",
        ".avsc",
        ".usda",
        ".svg",
    }


def iter_repo_files() -> Iterable[Path]:
    ignored_dirs = {".git", ".release-spec-work"}
    for root, dirs, files in os.walk(REPO):
        # A directory carrying its own .git is a submodule or nested clone. The private review
        # repository is available to members as one, and rewriting references inside it would
        # edit another repository's working tree while releasing a specification from this one.
        dirs[:] = [
            d for d in dirs
            if d not in ignored_dirs and not (Path(root) / d / ".git").exists()
        ]
        for name in files:
            yield Path(root) / name


@dataclass
class TextChange:
    path: str
    old: str
    new: str
    summary: str


@dataclass
class Plan:
    action: str
    spec_id: str
    closure: list[str]
    files: list[str]
    export_files: list[str]
    vendor_files: list[str]
    text_changes: list[TextChange]
    manual_steps: list[str]
    export_dir: Path | None = None
    import_dir: Path | None = None


def moving_specs(manifest, spec_id: str) -> list[str]:
    ids = [norm(s) for s in manifest.closure(spec_id)]
    if spec_id not in ids:
        ids.insert(0, spec_id)
    return ids


def _own_file_set_from_dir(base: Path, spec: dict) -> set[str]:
    keep_public = [norm(path) for path in spec.get("keepPublic", [])]
    files: set[str] = set()
    for move in spec.get("move", []):
        move = norm(move)
        root = base / Path(*move.split("/"))
        if root.is_file():
            candidates = [move]
        elif root.exists():
            candidates = [
                norm((Path(move) / path.relative_to(root)).as_posix())
                for path in root.rglob("*")
                if path.is_file()
                and not any(part in IGNORED_GENERATED_DIRS for part in path.relative_to(root).parts)
                and path.suffix.lower() not in IGNORED_GENERATED_SUFFIXES
            ]
        else:
            candidates = []
        for candidate in candidates:
            if not any(belongs_to(candidate, {keep}, []) for keep in keep_public):
                files.add(candidate)
    return files


def spec_file_set(manifest, spec_id: str, import_dir: Path | None = None) -> list[str]:
    files = sorted(norm(p) for p in manifest.file_set(spec_id))
    if files or import_dir is None:
        return files
    restored: set[str] = set()
    for sid in moving_specs(manifest, spec_id):
        restored.update(_own_file_set_from_dir(import_dir, manifest.spec(sid)))
    return sorted(restored)


def spec_export_set(manifest, spec_id: str) -> list[str]:
    export_set = getattr(manifest, "export_set", None)
    if export_set is None:
        raise RuntimeError("release/tools/manifest.py must expose export_set(spec_id)")
    return sorted(norm(p) for p in export_set(spec_id))


def submitted(manifest, spec_id: str) -> bool:
    return bool(manifest.spec(spec_id).get("submitted", True))


def public_state(manifest, spec_id: str) -> bool:
    return manifest.spec(spec_id).get("state", "public") == "public"


def vendor_specs(manifest, spec_id: str) -> list[str]:
    vendors: list[str] = []
    seen: set[str] = set()

    def visit_vendor(vendor_id: str) -> None:
        vendor_id = norm(vendor_id)
        if vendor_id in seen:
            return
        seen.add(vendor_id)
        vendors.append(vendor_id)
        for child in manifest.spec(vendor_id).get("vendor", []):
            visit_vendor(child)

    for moving_id in moving_specs(manifest, spec_id):
        for vendor_id in manifest.spec(moving_id).get("vendor", []):
            visit_vendor(vendor_id)
    return vendors


def dependent_specs(manifest, spec_id: str) -> list[str]:
    dependents = getattr(manifest, "dependents", None)
    if dependents is None:
        raise RuntimeError("release/tools/manifest.py must expose dependents(spec_id)")
    return sorted(norm(sid) for sid in dependents(spec_id) if norm(sid) != spec_id)


def public_dependency_blockers(manifest, spec_id: str) -> list[str]:
    moving = set(moving_specs(manifest, spec_id))
    return [
        sid
        for sid in dependent_specs(manifest, spec_id)
        if sid not in moving and submitted(manifest, sid) and public_state(manifest, sid)
    ]


def moved_roots(manifest, closure: Iterable[str]) -> list[str]:
    """The move entries that can be matched by prefix.

    A move entry with a ``keepPublic`` path under it is **not** wholly moved, and using it
    as a prefix would claim the kept file too — telling a reader to request member access
    for a document still sitting in this repository. Such an entry is dropped here and its
    concrete files are matched through the file set instead, which already excludes what
    stays. Nothing is lost: a link to a path that does not exist would already have failed
    the link check, so prefix matching only ever has to cover files that are really there.
    """
    roots: list[str] = []
    for sid in closure:
        spec = manifest.spec(sid)
        kept = [norm(k) for k in spec.get("keepPublic", [])]
        for value in spec.get("move", []):
            value = norm(value)
            if any(k == value or k.startswith(value.rstrip("/") + "/") for k in kept):
                continue
            roots.append(value)
    return sorted(set(roots), key=lambda p: (p.count("/"), p))


def belongs_to(path: str, files: set[str], roots: Iterable[str]) -> bool:
    path = norm(path)
    if path in files:
        return True
    for root in roots:
        root = norm(root)
        if path == root or path.startswith(root + "/"):
            return True
    return False


def resolve_link(markdown_file: str, target: str) -> str | None:
    target = target.strip()
    if not target or target.startswith("#"):
        return None
    lower = target.lower()
    if re.match(r"^[a-z][a-z0-9+.-]*:", lower):
        return None
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split()[0].strip("'\"")
    target = target.split("#", 1)[0]
    if not target:
        return None
    base = Path(markdown_file).parent
    joined = (base / Path(*target.replace("\\", "/").split("/"))).as_posix()
    # pathlib does not collapse "..", so a cross-tree link such as
    # ../../wot-specs/WoT-Connectivity/ would otherwise never match a moved path.
    collapsed = posixpath.normpath(joined)
    if collapsed == ".." or collapsed.startswith("../"):
        return None
    return norm(collapsed)


def inline_link_destination(body: str) -> str:
    stripped = body.strip()
    if stripped.startswith("<") and ">" in stripped:
        return stripped[1 : stripped.index(">")]
    return stripped.split()[0].strip("'\"") if stripped else ""


def repair_markdown_release(text: str, path: str, files: set[str], roots: list[str]) -> tuple[str, int]:
    count = 0

    def replace_ref(match: re.Match[str]) -> str:
        nonlocal count
        original = match.group(0)
        target = match.group("target")
        resolved = resolve_link(path, target)
        if resolved and belongs_to(resolved, files, roots):
            count += 1
            return f"<!-- {MD_MARKER}:{b64(original)} --><!-- /{MD_MARKER} -->"
        return original

    ref_re = re.compile(
        r"^(?P<indent>[ \t]{0,3})\[(?P<label>[^\]\n]+)\]:[ \t]*(?P<target>\S.*)$",
        re.MULTILINE,
    )

    inline_re = re.compile(r"(?P<bang>!?)\[(?P<label>[^\]\n]+)\]\((?P<body>[^)\n]+)\)")

    def replace_inline(match: re.Match[str]) -> str:
        nonlocal count
        original = match.group(0)
        target = inline_link_destination(match.group("body"))
        resolved = resolve_link(path, target)
        if resolved and belongs_to(resolved, files, roots):
            count += 1
            visible = "" if match.group("bang") else match.group("label")
            return f"<!-- {MD_MARKER}:{b64(original)} -->{visible}<!-- /{MD_MARKER} -->"
        return original

    def repair(segment: str) -> str:
        return inline_re.sub(replace_inline, ref_re.sub(replace_ref, segment))

    # Releases accumulate: a file repaired by an earlier release still has to be repairable by
    # the next one. Rewrite only the text outside existing capsules, so their encoded originals
    # are never re-encoded and a second release can still fix its own references.
    capsule_re = re.compile(
        rf"<!-- {re.escape(MD_MARKER)}:[A-Za-z0-9+/=]+ -->.*?<!-- /{re.escape(MD_MARKER)} -->",
        re.DOTALL,
    )
    out: list[str] = []
    index = 0
    for capsule in capsule_re.finditer(text):
        out.append(repair(text[index : capsule.start()]))
        out.append(capsule.group(0))
        index = capsule.end()
    out.append(repair(text[index:]))
    return "".join(out), count


def repair_markdown_return(text: str, path: str, files: set[str], roots: list[str]) -> tuple[str, int]:
    pattern = re.compile(
        rf"<!-- {re.escape(MD_MARKER)}:([A-Za-z0-9+/=]+) -->.*?<!-- /{re.escape(MD_MARKER)} -->",
        re.DOTALL,
    )
    count = 0

    def restore(match: re.Match[str]) -> str:
        nonlocal count
        original = unb64(match.group(1))
        if not capsule_belongs_to(original, path, files, roots):
            return match.group(0)
        count += 1
        return original

    return pattern.sub(restore, text), count


def review_note(manifest) -> str:
    """The visible text left where a released specification used to be described.

    A reader of the public repository should be able to find the document rather than
    conclude it was withdrawn, so the note names the private repository and how a member
    obtains access. It sits outside the capsule's encoded original, so changing it does not
    affect what a return restores.
    """
    private = getattr(manifest, "privateRepo", None) or "OPCF-Members/spec-drafts"
    access = getattr(manifest, "accessInfo", None) or "https://github.com/OPCF-Members/Help"
    return (
        f"*Under OPC Foundation review — moved to "
        f"[{private}](https://github.com/{private}); "
        f"OPC Foundation members can [request access]({access}).*"
    )


def repair_markdown_reverse_lines_release(
    text: str, moved_dirs: set[str], path: str, files: set[str], roots: list[str], note: str
) -> tuple[str, int]:
    if not moved_dirs:
        return text, 0
    count = 0
    out: list[str] = []
    moved_dir_tokens = {token.strip("/").lower() + "/" for token in moved_dirs if token}
    for line in text.splitlines(keepends=True):
        if f"<!-- {MD_MARKER}:" in line:
            out.append(line)
            continue
        raw, newline = split_line_ending(line)
        stripped = raw.lstrip()
        haystack = raw.lower()
        item = re.match(r"^(?P<prefix>[ \t]*[-*][ \t]+)(?P<content>.*)$", raw)
        is_list_item = stripped.startswith(("- ", "* "))
        names_moved_dir = any(token in haystack for token in moved_dir_tokens)
        if is_list_item and item and names_moved_dir:
            count += 1
            # Keep the bullet and its indentation outside the capsule, so the list structure
            # survives. Replacing the whole line leaves the surrounding items looking
            # unindented and unseparated, which markdownlint rejects.
            prefix = item.group("prefix")
            content = item.group("content")
            out.append(f"{prefix}<!-- {MD_MARKER}:{b64(content)} -->{note}<!-- /{MD_MARKER} -->{newline}")
        else:
            out.append(line)
    return "".join(out), count


def private_url(manifest, repo_rel: str) -> str:
    """A GitHub URL for a file that has moved to the private review repository.

    A relative link would be worse than useless once the file is gone: the submodule is
    empty for everyone who is not a member, so `check_links.py` would fail for them and
    the reader would still have nothing to open.
    """
    private = getattr(manifest, "privateRepo", None) or "OPCF-Members/spec-drafts"
    return f"https://github.com/{private}/blob/main/{norm(repo_rel)}"


TABLE_CONTRACT = ("status", "documents")


def private_document_label(path: str) -> str:
    lowered = path.lower()
    if lowered.endswith(".docx"):
        return "Word"
    if "/examples/" in lowered and lowered.endswith(("/index.md", "/readme.md")):
        return "Guides"
    if lowered.endswith("/spec.md"):
        return "Specification"
    if lowered.endswith(("/readme.md", ".md")):
        return "Document"
    return "Artifact"


def rewrite_private_row_links(
    cell: str,
    path: str,
    files: set[str],
    roots: list[str],
    manifest,
) -> str:
    """Point links retained in a public inventory row at the private review copy."""
    def replace(match: re.Match[str]) -> str:
        target = inline_link_destination(match.group("body"))
        resolved = resolve_link(path, target)
        if not resolved or not belongs_to(resolved, files, roots):
            return match.group(0)
        return f"]({private_url(manifest, resolved)})"

    return re.sub(r"\]\((?P<body>[^)\n]+)\)", replace, cell)


def repair_markdown_table_rows_release(
    text: str,
    moved_dirs: set[str],
    path: str,
    files: set[str],
    roots: list[str],
    note: str,
    manifest,
) -> tuple[str, int]:
    """Capsule an inventory table row whose specification is moving.

    The README lists every specification in tables rather than bullets, so the bullet
    repair below never sees them. A row left alone would keep advertising a document that
    is no longer here, with links the link repair had already emptied.

    This runs BEFORE the link repair. If it ran after, every row would already hold a
    capsule around its own links and would be skipped, exactly as the bullet pass skips
    such lines.

    Only tables whose last two columns are Status and Documents are touched, because those
    are the two cells whose content the move invalidates; a table of some other shape is
    left alone rather than rewritten into something this function guessed at. The whole row
    is encoded so a return restores it unchanged, and the replacement keeps the original
    cell count -- collapsing four cells into two fails MD056.
    """
    count = 0
    out: list[str] = []
    contract = False
    moved_dir_tokens = {token.strip("/").lower() + "/" for token in moved_dirs if token}

    for line in text.splitlines(keepends=True):
        raw, newline = split_line_ending(line)
        stripped = raw.strip()

        if not stripped.startswith("|"):
            contract = False
            out.append(line)
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells) and cells:
            out.append(line)
            continue
        lowered = [c.lower() for c in cells]
        if len(lowered) >= 3 and tuple(lowered[-2:]) == TABLE_CONTRACT:
            contract = True
            out.append(line)
            continue

        if not contract or f"<!-- {MD_MARKER}:" in raw:
            out.append(line)
            continue

        targets: list[str] = []
        for match in re.finditer(r"\]\((?P<body>[^)\n]+)\)", raw):
            target = inline_link_destination(match.group("body"))
            resolved = resolve_link(path, target)
            if resolved and belongs_to(resolved, files, roots):
                targets.append(resolved)
        names_moved_dir = any(
            f"`{token}`" in raw.lower() or f"`{token.rstrip('/')}`" in raw.lower()
            for token in moved_dir_tokens
        )
        if not targets and not names_moved_dir:
            out.append(line)
            continue

        original = stripped[1:-1] if stripped.endswith("|") else stripped[1:]
        docs = " · ".join(
            f"[{private_document_label(t)}]({private_url(manifest, t)})"
            for t in targets
        ) or "—"
        retained = [
            rewrite_private_row_links(cell, path, files, roots, manifest)
            for cell in cells[:-2]
        ]
        replacement = " " + " | ".join(retained + [note, docs]) + " "
        count += 1
        indent = raw[: len(raw) - len(raw.lstrip())]
        # Both markers sit INSIDE the outer pipes. markdownlint counts cells without
        # stripping HTML comments, so a closing marker after the final pipe makes the row
        # end in content and fails MD055 and MD056 together.
        out.append(
            f"{indent}|<!-- {MD_MARKER}:{b64(original)} -->{replacement}<!-- /{MD_MARKER} -->|{newline}"
        )

    return "".join(out), count


def validator_base(path: str) -> Path:
    # All repository aggregate validators build their child paths from HERE,
    # where HERE is the directory containing validate_all.py.
    return repo_path(path).parent


def resolved_validator_path(aggregate: str, validator_rel: str) -> str:
    if validator_rel.startswith(("source/", "extras/", "model/")):
        return norm(validator_rel)
    return norm(posixpath.normpath(posixpath.join(posixpath.dirname(aggregate), validator_rel)))


def repair_validator_release(text: str, aggregate: str, files: set[str], roots: list[str]) -> tuple[str, int]:
    count = 0
    out: list[str] = []
    line_re = re.compile(r"^(\s*)([\"'])([^\"']*validate_[^\"']*\.py)\2(,.*)$")
    for line in text.splitlines(keepends=True):
        raw, newline = split_line_ending(line)
        match = line_re.match(raw)
        if match:
            target = resolved_validator_path(aggregate, match.group(3))
            if belongs_to(target, files, roots):
                out.append(f"{match.group(1)}# {VALIDATOR_MARKER}:{b64(raw)}{newline}")
                count += 1
                continue
        out.append(line)
    return "".join(out), count


def capsule_belongs_to(original: str, source: str, files: set[str], roots: list[str]) -> bool:
    """Whether an encoded original refers to the file set currently being returned.

    Releases accumulate, so one file can hold capsules written by several releases. A return
    must undo only its own, or restoring one specification would silently re-enable another
    that is still private — re-enabling a validator whose files are absent, for instance.
    """
    for match in re.finditer(r"\]\((?P<body>[^)\n]+)\)", original):
        resolved = resolve_link(source, inline_link_destination(match.group("body")))
        if resolved and belongs_to(resolved, files, roots):
            return True
    match = re.match(r"^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*(?P<target>\S.*)$", original)
    if match:
        resolved = resolve_link(source, match.group("target"))
        if resolved and belongs_to(resolved, files, roots):
            return True
    # Whole-line capsules carry a prose bullet that names a moved directory in backticks and
    # holds no link, so there is nothing to resolve; match them the same way the release did.
    haystack = original.lower()
    for root in roots:
        token = norm(root).strip("/").lower()
        if not token:
            continue
        if f"`{token}/`" in haystack or f"`{token}`" in haystack:
            return True
        leaf = token.rsplit("/", 1)[-1]
        if f"`{leaf}/`" in haystack or f"`{leaf}`" in haystack:
            return True
    return False


def repair_validator_return(text: str, aggregate: str, files: set[str], roots: list[str]) -> tuple[str, int]:
    count = 0
    out: list[str] = []
    marker_re = re.compile(rf"^(\s*)# {re.escape(VALIDATOR_MARKER)}:([A-Za-z0-9+/=]+)$")
    for line in text.splitlines(keepends=True):
        raw, newline = split_line_ending(line)
        match = marker_re.match(raw)
        if not match:
            out.append(line)
            continue
        original = unb64(match.group(2))
        entry = re.search(r"[\"'](?P<target>[^\"']+)[\"']", original)
        target = resolved_validator_path(aggregate, entry.group("target")) if entry else None
        if target is None or belongs_to(target, files, roots):
            out.append(original + newline)
            count += 1
        else:
            out.append(line)
    return "".join(out), count


def word_spec_ids(manifest, spec_ids: Iterable[str]) -> list[str]:
    ids: list[str] = []
    for sid in spec_ids:
        for path in manifest.spec(sid).get("wordSpecs", []):
            ids.append(Path(path).stem)
    return ids


def publisher_spec_entries(manifest, spec_ids: Iterable[str]) -> list[dict]:
    entries: list[dict] = []
    for sid in spec_ids:
        for entry in manifest.spec(sid).get("publisherSpecs", []):
            if isinstance(entry, dict):
                entries.append(dict(entry))
    return entries


def publisher_spec_ids(manifest, spec_ids: Iterable[str]) -> list[str]:
    return [
        str(entry["spec"])
        for entry in publisher_spec_entries(manifest, spec_ids)
        if isinstance(entry.get("spec"), str)
    ]


def reverse_reference_tokens(manifest, spec_ids: Iterable[str], roots: Iterable[str]) -> set[str]:
    tokens = {norm(sid) for sid in spec_ids}
    tokens.update(Path(root).name for root in roots)
    for sid in spec_ids:
        spec = manifest.spec(sid)
        title = spec.get("title")
        if isinstance(title, str):
            tokens.add(title)
            if "—" in title:
                tokens.add(title.split("—", 1)[1].strip())
        for word_spec in spec.get("wordSpecs", []):
            path = repo_path(norm(word_spec))
            if not path.exists():
                continue
            try:
                data = json.loads(read_text(path))
            except (OSError, json.JSONDecodeError):
                continue
            identity = data.get("identity", {})
            if isinstance(identity, dict):
                for key in ("partNumber", "partName", "subTitle"):
                    value = identity.get(key)
                    if isinstance(value, str) and value:
                        tokens.add(value)
            for value in data.get("citedAs", []):
                if isinstance(value, str) and value:
                    tokens.add(value)
        for entry in spec.get("publisherSpecs", []):
            if not isinstance(entry, dict):
                continue
            for key in ("spec", "markdown", "docNumber"):
                value = entry.get(key)
                if isinstance(value, str) and value:
                    tokens.add(value)
    return tokens


def private_batch_path() -> Path | None:
    """Resolve the bundled private ``batch.json`` through the bundle manifest.

    The bundle stores payload files under neutral paths with an inert suffix so
    this repository cannot mistake them for its own configuration, so the stored
    location is not derivable from the destination. ``release/private-repo/manifest.json``
    is the only source of truth for that mapping; resolving through it means a
    future restructure of the bundle cannot silently strip the ordering hint.
    """
    bundle_manifest = REPO / "release" / "private-repo" / "manifest.json"
    if not bundle_manifest.exists():
        return None
    try:
        entries = json.loads(read_text(bundle_manifest)).get("files", [])
    except (OSError, json.JSONDecodeError) as exc:
        print(f"warning: cannot read the private bundle manifest: {exc}", file=sys.stderr)
        return None
    for entry in entries:
        if entry.get("destination") == "word-drafts/tools/specs/batch.json":
            stored = REPO / "release" / "private-repo" / "files" / Path(entry["stored"])
            if stored.exists():
                return stored
            print(
                f"warning: the private bundle manifest points at {entry['stored']}, which is missing",
                file=sys.stderr,
            )
            return None
    print(
        "warning: the private bundle no longer carries word-drafts/tools/specs/batch.json; "
        "Word batch ordering falls back to the canonical order",
        file=sys.stderr,
    )
    return None


def all_manifest_word_order(manifest) -> list[str]:
    order: list[str] = []

    def extend_unique(values: Iterable[str]) -> None:
        for value in values:
            if value not in order:
                order.append(value)

    private_batch = private_batch_path()
    if private_batch is not None:
        try:
            batch = json.loads(read_text(private_batch))
            converted = batch.get("converted", [])
            if isinstance(converted, list):
                extend_unique(str(item) for item in converted)
            migrated = batch.get("migrated", [])
            if isinstance(migrated, list):
                extend_unique(
                    str(item["spec"])
                    for item in migrated
                    if isinstance(item, dict) and isinstance(item.get("spec"), str)
                )
        except (OSError, json.JSONDecodeError) as exc:
            print(f"warning: cannot parse the bundled private batch.json: {exc}", file=sys.stderr)
    extend_unique(CANONICAL_WORD_ORDER)
    for sid in manifest.spec_ids():
        extend_unique(word_spec_ids(manifest, [sid]))
        extend_unique(publisher_spec_ids(manifest, [sid]))
    return order


def dump_json_like_repo(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def repair_word_batch_release(text: str, manifest, departing_spec_ids: list[str]) -> tuple[str, int]:
    data = json.loads(text)
    departing_word_ids = set(word_spec_ids(manifest, departing_spec_ids))
    departing_publisher_ids = set(publisher_spec_ids(manifest, departing_spec_ids))
    converted = list(data.get("converted", []))
    new_converted = [item for item in converted if item not in departing_word_ids]
    migrated = list(data.get("migrated", []))
    new_migrated = [
        item
        for item in migrated
        if not (
            isinstance(item, dict)
            and isinstance(item.get("spec"), str)
            and item["spec"] in departing_publisher_ids
        )
    ]
    if new_converted == converted and new_migrated == migrated:
        return text, 0
    data["converted"] = new_converted
    if "migrated" in data or new_migrated:
        data["migrated"] = new_migrated
    removed = (len(converted) - len(new_converted)) + (len(migrated) - len(new_migrated))
    return match_eol(dump_json_like_repo(data), text), removed


def repair_word_batch_return(text: str, manifest, returning_spec_ids: list[str]) -> tuple[str, int]:
    data = json.loads(text)
    converted = list(data.get("converted", []))
    converted_additions = [
        item for item in word_spec_ids(manifest, returning_spec_ids) if item not in converted
    ]
    present = set(converted) | set(converted_additions)
    desired = all_manifest_word_order(manifest)
    ordered = [item for item in desired if item in present]
    ordered.extend(item for item in converted if item in present and item not in ordered)
    ordered.extend(item for item in converted_additions if item not in ordered)

    expected_entries = {
        entry["spec"]: entry
        for entry in publisher_spec_entries(manifest, returning_spec_ids)
        if isinstance(entry.get("spec"), str)
    }
    migrated = list(data.get("migrated", []))
    migrated_by_id: dict[str, dict] = {}
    migrated_other: list[object] = []
    changed_entries = 0
    for item in migrated:
        if not isinstance(item, dict) or not isinstance(item.get("spec"), str):
            migrated_other.append(item)
            continue
        spec_id = item["spec"]
        replacement = expected_entries.get(spec_id, item)
        if replacement != item:
            changed_entries += 1
        migrated_by_id[spec_id] = replacement
    for spec_id, entry in expected_entries.items():
        if spec_id not in migrated_by_id:
            migrated_by_id[spec_id] = entry
            changed_entries += 1
    migrated_order = [item for item in desired if item in migrated_by_id]
    migrated_order.extend(item for item in migrated_by_id if item not in migrated_order)
    new_migrated = [migrated_by_id[item] for item in migrated_order] + migrated_other

    if ordered == converted and new_migrated == migrated:
        return text, 0
    data["converted"] = ordered
    if "migrated" in data or new_migrated:
        data["migrated"] = new_migrated
    return (
        match_eol(dump_json_like_repo(data), text),
        len(converted_additions) + changed_entries,
    )


def parse_allowed_paths(text: str) -> list[str]:
    match = re.search(r"(?m)^  ALLOWED_PATHS: >-\n(?P<body>(?:    .+\n)+)", text)
    if not match:
        return []
    return [line.strip() for line in match.group("body").splitlines() if line.strip()]


def replace_allowed_paths(text: str, values: list[str]) -> str:
    body = "".join(f"    {value}\n" for value in values)
    replaced = re.sub(r"(?m)^  ALLOWED_PATHS: >-\n(?:    .+\n)+", f"  ALLOWED_PATHS: >-\n{body}", text)
    return match_eol(replaced, text)


def tree_has_files(tree: str, moving: set[str], extra_present: set[str] | None = None) -> bool:
    prefix = norm(tree) + "/"
    extra_present = extra_present or set()
    for path in extra_present:
        if path == tree or path.startswith(prefix):
            return True
    root = repo_path(tree)
    if not root.exists():
        return False
    for file in root.rglob("*"):
        if file.is_file():
            r = rel(file)
            if r not in moving:
                return True
    return False


def repair_agent_task_release(text: str, moving: set[str]) -> tuple[str, int]:
    current = parse_allowed_paths(text)
    if not current:
        return text, 0
    kept = [item for item in current if tree_has_files(item, moving)]
    if kept == current:
        return text, 0
    return replace_allowed_paths(text, kept), len(current) - len(kept)


def repair_agent_task_return(text: str, import_files: set[str]) -> tuple[str, int]:
    current = parse_allowed_paths(text)
    if not current:
        return text, 0
    present = set(current)
    for item in CANONICAL_ALLOWED_PATHS:
        if item not in present and tree_has_files(item, set(), import_files):
            present.add(item)
    ordered = [item for item in CANONICAL_ALLOWED_PATHS if item in present]
    ordered.extend(item for item in current if item not in ordered)
    if ordered == current:
        return text, 0
    return replace_allowed_paths(text, ordered), len(ordered) - len(current)


def add_change(changes: list[TextChange], path: str, old: str, new: str, summary: str) -> None:
    if old != new:
        changes.append(TextChange(path, old, new, summary))


def planned_text(path: str, changes: list[TextChange]) -> str:
    for change in reversed(changes):
        if change.path == path:
            return change.new
    return read_text(repo_path(path))


def text_repairs_release(manifest, closure: list[str], files: list[str], roots: list[str]) -> list[TextChange]:
    moving = set(files)
    changes: list[TextChange] = []
    markdown_reverse_refs = {
        norm(path)
        for sid in closure
        for path in manifest.spec(sid).get("reverseRefs", [])
        if norm(path).endswith(".md")
    }
    moving_spec_ids = {sid.lower() for sid in closure}
    # Derived from the manifest's move entries rather than from `roots`, because `roots`
    # deliberately omits an entry that keeps something public — and a directory being
    # partly kept does not stop prose from naming it in backticks.
    moved_dirs = {
        Path(entry).name
        for sid in closure
        for entry in (norm(v) for v in manifest.spec(sid).get("move", []))
        if Path(entry).name.lower() in moving_spec_ids
        and any(path == entry or path.startswith(entry.rstrip("/") + "/") for path in moving)
    }

    for aggregate in AGGREGATE_VALIDATORS:
        path = repo_path(aggregate)
        if not path.exists() or aggregate in moving:
            continue
        old = read_text(path)
        new, count = repair_validator_release(old, aggregate, moving, roots)
        add_change(changes, aggregate, old, new, f"comment out {count} departed validator(s)")

    batch = repo_path(WORD_BATCH)
    if batch.exists() and WORD_BATCH not in moving:
        old = read_text(batch)
        new, count = repair_word_batch_release(old, manifest, closure)
        add_change(changes, WORD_BATCH, old, new, f"remove {count} Word conversion batch entrie(s)")

    for path in iter_repo_files():
        r = rel(path)
        if r in moving or path.suffix.lower() != ".md":
            continue
        old = planned_text(r, changes) if any(c.path == r for c in changes) else read_text(path)
        row_count = 0
        if r in markdown_reverse_refs:
            old, row_count = repair_markdown_table_rows_release(
                old, moved_dirs, r, moving, roots, review_note(manifest), manifest
            )
            old, line_count = repair_markdown_reverse_lines_release(
                old, moved_dirs, r, moving, roots, review_note(manifest)
            )
        else:
            line_count = 0
        new, count = repair_markdown_release(old, r, moving, roots)
        add_change(
            changes,
            r,
            planned_text(r, changes) if any(c.path == r for c in changes) else read_text(path),
            new,
            f"neutralize {count} Markdown link(s), {row_count} table row(s) and {line_count} reverse-reference line(s) into private specs",
        )

    workflow = repo_path(AGENT_TASK)
    if workflow.exists() and AGENT_TASK not in moving:
        old = planned_text(AGENT_TASK, changes) if any(c.path == AGENT_TASK for c in changes) else read_text(workflow)
        new, count = repair_agent_task_release(old, moving)
        add_change(changes, AGENT_TASK, old, new, f"remove {count} empty ALLOWED_PATHS entrie(s)")

    return changes


def text_repairs_return(manifest, closure: list[str], files: list[str], import_dir: Path | None, roots: list[str]) -> list[TextChange]:
    changes: list[TextChange] = []
    import_files = set(files)

    for aggregate in AGGREGATE_VALIDATORS:
        path = repo_path(aggregate)
        if not path.exists():
            continue
        old = read_text(path)
        new, count = repair_validator_return(old, aggregate, import_files, roots)
        add_change(changes, aggregate, old, new, f"restore {count} validator entrie(s)")

    batch = repo_path(WORD_BATCH)
    if batch.exists():
        old = read_text(batch)
        new, count = repair_word_batch_return(old, manifest, closure)
        add_change(changes, WORD_BATCH, old, new, f"restore {count} Word conversion batch entrie(s)")

    for path in iter_repo_files():
        if path.suffix.lower() != ".md":
            continue
        r = rel(path)
        old = planned_text(r, changes) if any(c.path == r for c in changes) else read_text(path)
        new, count = repair_markdown_return(old, r, import_files, roots)
        add_change(changes, r, old, new, f"restore {count} Markdown link(s)")

    workflow = repo_path(AGENT_TASK)
    if workflow.exists():
        old = planned_text(AGENT_TASK, changes) if any(c.path == AGENT_TASK for c in changes) else read_text(workflow)
        new, count = repair_agent_task_return(old, import_files)
        add_change(changes, AGENT_TASK, old, new, f"restore {count} ALLOWED_PATHS entrie(s)")

    return changes


def manual_steps_release(manifest, closure: list[str], changes: list[TextChange], moving: set[str]) -> list[str]:
    changed = {change.path for change in changes}
    manual: list[str] = []
    automatically_handled = set(AGGREGATE_VALIDATORS) | {WORD_BATCH, AGENT_TASK}
    for sid in closure:
        for path in manifest.spec(sid).get("reverseRefs", []):
            path = norm(path)
            if path.endswith(".md"):
                continue
            if path in moving or path in changed or path in automatically_handled:
                continue
            p = repo_path(path)
            if p.exists():
                manual.append(
                    f"{path}: reverse reference to {sid} is outside the automated Markdown, "
                    "validator, Word batch, and ALLOWED_PATHS repairs"
                )
    return sorted(set(manual))


def manual_steps_return_vendors(vendor_files: list[str], import_dir: Path | None, changes: list[TextChange]) -> list[str]:
    if import_dir is None:
        return []
    planned = {change.path: change.new.encode("utf-8") for change in changes}
    manual: list[str] = []
    for path in vendor_files:
        public = repo_path(path)
        private = import_dir / Path(*path.split("/"))
        if not private.exists():
            manual.append(f"{path}: vendored file is missing from the private import; cannot compare it")
            continue
        if path in planned:
            public_bytes = planned[path]
        elif public.exists():
            public_bytes = public.read_bytes()
        else:
            manual.append(f"{path}: vendored file is missing from the public tree; cannot compare it")
            continue
        private_bytes = private.read_bytes()
        if is_probably_text(public):
            public_bytes = public_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            private_bytes = private_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if public_bytes != private_bytes:
            manual.append(
                f"{path}: vendored dependency differs between private import and public tree; "
                "review manually rather than overwriting the public copy"
            )
    return manual


def relevant_manifest_problems(action: str, problems: list[str], files: list[str], roots: list[str]) -> list[str]:
    if action != "return":
        return problems
    expected_missing = set(files)
    filtered: list[str] = []
    for problem in problems:
        match = re.search(r"path does not exist: (.+)$", problem)
        if match and belongs_to(match.group(1), expected_missing, roots):
            continue
        filtered.append(problem)
    return filtered


def build_plan(manifest, action: str, spec_id: str, export_dir: str | None, import_dir: str | None) -> Plan:
    closure = moving_specs(manifest, spec_id)
    import_path = Path(import_dir).resolve() if import_dir else None
    files = spec_file_set(manifest, spec_id, import_path if action == "return" else None)
    export_files = spec_export_set(manifest, spec_id)
    vendor_files = sorted(set(export_files) - set(files))
    roots = moved_roots(manifest, closure)
    if action == "release":
        changes = text_repairs_release(manifest, closure, files, roots)
        manual = manual_steps_release(manifest, closure, changes, set(files))
        if not submitted(manifest, spec_id):
            manual.insert(
                0,
                f"{spec_id}: submitted is false; this is a shared dependency that is vendored rather than released",
            )
        return Plan(
            action,
            spec_id,
            closure,
            files,
            export_files,
            vendor_files,
            changes,
            manual,
            Path(export_dir).resolve() if export_dir else None,
        )
    changes = text_repairs_return(manifest, closure, files, import_path, roots)
    manual = manual_steps_return_vendors(vendor_files, import_path, changes)
    return Plan(action, spec_id, closure, files, export_files, vendor_files, changes, manual, None, import_path)


def print_status(manifest) -> int:
    problems = manifest.validate()
    for spec_id in manifest.spec_ids():
        spec = manifest.spec(spec_id)
        try:
            move_count = len(spec_file_set(manifest, spec_id))
            vendor_count = len(set(spec_export_set(manifest, spec_id)) - set(spec_file_set(manifest, spec_id)))
            dependents = ", ".join(dependent_specs(manifest, spec_id)) or "-"
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        vendors = ", ".join(vendor_specs(manifest, spec_id)) or "-"
        print(
            f"{spec_id}\t{spec.get('state', '(unknown)')}\t"
            f"submitted={submitted(manifest, spec_id)}\t"
            f"moves={move_count}\tvendors={vendor_count} ({vendors})\t"
            f"dependents={dependents}"
        )
    if problems:
        print("Manifest is invalid:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 2
    return 0


def print_plan(plan: Plan, dry_run: bool) -> None:
    prefix = "Would" if dry_run else "Will"
    print(f"{prefix} {plan.action} {plan.spec_id}")
    if plan.closure != [plan.spec_id]:
        print("Closure:")
        for sid in plan.closure:
            print(f"  {sid}")
    if plan.action == "release":
        if plan.export_dir:
            print(f"{prefix} export {len(plan.export_files)} file(s) to {plan.export_dir}")
        else:
            print("No export directory supplied")
        if plan.vendor_files:
            print(f"{prefix} vendor {len(plan.vendor_files)} file(s) into the private export:")
            for path in plan.vendor_files:
                print(f"  {path}")
        print(f"{prefix} remove {len(plan.files)} file(s) from the public tree:")
    else:
        if plan.import_dir:
            print(f"{prefix} import {len(plan.files)} file(s) from {plan.import_dir}")
        else:
            print("No import directory supplied")
        print(f"{prefix} restore {len(plan.files)} file(s) to the public tree:")
    for path in plan.files:
        print(f"  {path}")
    if plan.text_changes:
        print(f"{prefix} modify {len(plan.text_changes)} support file(s):")
        for change in plan.text_changes:
            print(f"  {change.path}: {change.summary}")
    if plan.manual_steps:
        print("Required manual steps:")
        for step in plan.manual_steps:
            print(f"  - {step}")


def copy_to_export(files: list[str], export_dir: Path) -> None:
    for path in files:
        src = repo_path(path)
        if not src.exists():
            raise FileNotFoundError(f"cannot export missing file: {path}")
    for path in files:
        src = repo_path(path)
        dest = export_dir / Path(*path.split("/"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def copy_from_import(files: list[str], import_dir: Path) -> None:
    missing = [path for path in files if not (import_dir / Path(*path.split("/"))).exists()]
    if missing:
        raise FileNotFoundError("import directory is missing: " + ", ".join(missing))
    for path in files:
        src = import_dir / Path(*path.split("/"))
        dest = repo_path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def prune_empty_dirs(start: Path) -> None:
    current = start
    while current != REPO and current.exists():
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def delete_public_files(files: list[str]) -> None:
    for path in sorted(files, key=lambda p: p.count("/"), reverse=True):
        p = repo_path(path)
        if p.exists():
            p.unlink()
            prune_empty_dirs(p.parent)


def apply_text_changes(changes: list[TextChange]) -> dict[str, str]:
    backups: dict[str, str] = {}
    for change in changes:
        backups[change.path] = change.old
        write_text(repo_path(change.path), change.new)
    return backups


def restore_text_backups(backups: dict[str, str]) -> None:
    for path, content in backups.items():
        write_text(repo_path(path), content)


def set_spec_states(spec_ids: Iterable[str], state: str) -> None:
    """Record in the manifest which specifications currently live in the private repository.

    Without this the manifest keeps claiming a released specification is ``public``, so its
    absent paths fail validation and the first release blocks every later one.
    """
    path = REPO / "release" / "manifest.json"
    text = read_text(path)
    data = json.loads(text)
    changed = False
    for spec_id in spec_ids:
        spec = data["specs"].get(spec_id)
        if spec is not None and spec.get("state") != state:
            spec["state"] = state
            changed = True
    if changed:
        write_text(path, match_eol(dump_json_like_repo(data), text))


def apply_plan(plan: Plan) -> int:
    if plan.manual_steps:
        print_plan(plan, dry_run=False)
        print("Aborting because manual steps are required.", file=sys.stderr)
        return 3
    if plan.action == "release" and not plan.export_dir:
        print("Refusing a real release without --export; otherwise deleted files would not be staged.", file=sys.stderr)
        return 2
    if plan.action == "return" and not plan.import_dir:
        print("Refusing a real return without --import; missing files cannot be restored safely.", file=sys.stderr)
        return 2

    backups: dict[str, str] = {}
    try:
        if plan.action == "release":
            assert plan.export_dir is not None
            copy_to_export(plan.export_files, plan.export_dir)
            backups = apply_text_changes(plan.text_changes)
            delete_public_files(plan.files)
            set_spec_states(plan.closure, "released")
        else:
            assert plan.import_dir is not None
            copy_from_import(plan.files, plan.import_dir)
            backups = apply_text_changes(plan.text_changes)
            set_spec_states(plan.closure, "public")
    except Exception as exc:  # noqa: BLE001 - rollback must catch filesystem failures.
        restore_text_backups(backups)
        print(f"Failed; restored edited support files: {exc}", file=sys.stderr)
        return 1
    return 0


def print_dependency_blockers(manifest, spec_id: str, blockers: list[str]) -> None:
    for blocker in blockers:
        print(
            f"Refusing to release {spec_id}: submitted public spec {blocker} closes over it. "
            f"Run 'python release/tools/release_spec.py release {blocker}' to move both.",
            file=sys.stderr,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    for name in ("release", "return"):
        p = sub.add_parser(name)
        p.add_argument("spec_id")
        p.add_argument("--dry-run", action="store_true")
        if name == "release":
            p.add_argument("--export")
        else:
            p.add_argument("--import", dest="import_dir")
    args = parser.parse_args(argv)

    manifest = load_manifest()
    if args.command == "status":
        return print_status(manifest)

    problems = manifest.validate()

    try:
        if args.command == "release":
            blockers = public_dependency_blockers(manifest, args.spec_id)
            if blockers:
                print_dependency_blockers(manifest, args.spec_id, blockers)
                return 4
        if args.command == "release":
            plan = build_plan(manifest, "release", args.spec_id, args.export, None)
        else:
            plan = build_plan(manifest, "return", args.spec_id, None, args.import_dir)
    except KeyError as exc:
        print(f"unknown spec id: {args.spec_id}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    roots = moved_roots(manifest, plan.closure)
    problems = relevant_manifest_problems(args.command, problems, plan.files, roots)
    plan.manual_steps[:0] = [f"manifest validation: {problem}" for problem in problems]

    if args.dry_run:
        print_plan(plan, dry_run=True)
        return 3 if plan.manual_steps else 0
    return apply_plan(plan)


if __name__ == "__main__":
    raise SystemExit(main())
