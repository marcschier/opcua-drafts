#!/usr/bin/env python3
"""Load and validate the specification release manifest."""

from __future__ import annotations

import ast
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = REPO_ROOT / "release" / "manifest.json"
NODESET_NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"
BASE_MODEL_URI = "http://opcfoundation.org/UA/"
TREE_NAMES = {"core-specs", "cloud-specs", "metaverse-specs", "wot-specs", "companion-specs"}


def _rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _norm(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def _abs(path: str) -> Path:
    return REPO_ROOT / Path(*_norm(path).split("/"))


def _is_under(path: str, parent: str) -> bool:
    path = _norm(path)
    parent = _norm(parent)
    return path == parent or path.startswith(parent.rstrip("/") + "/")


def _path_exists(path: str) -> bool:
    return _abs(path).exists()


# Build artefacts that live inside specification trees but are never tracked. The walk is a
# filesystem walk, not a git walk, so without this an export depends on whether the author
# happened to run Python locally: .pyc files would be copied into the private repository and
# counted in the file set the public side is asked to delete.
_IGNORE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
_IGNORE_SUFFIXES = {".pyc", ".pyo"}


def _walk_files(path: str) -> list[str]:
    root = _abs(path)
    if root.is_file():
        return [] if root.suffix in _IGNORE_SUFFIXES else [_norm(path)]
    if not root.exists():
        return []
    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]
        for name in filenames:
            if Path(name).suffix in _IGNORE_SUFFIXES:
                continue
            files.append(_rel(Path(dirpath) / name))
    return files


def _json_paths(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            found.extend(_json_paths(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_json_paths(item))
    elif isinstance(value, str):
        candidate = _norm(value)
        if candidate and _path_exists(candidate):
            found.append(candidate)
    return found


class Manifest:
    def __init__(self, data: dict[str, Any], path: Path) -> None:
        self._data = data
        self._path = path
        self.publicRepo = data.get("publicRepo", "")
        self.privateRepo = data.get("privateRepo", "")
        self.sharedTooling = [_norm(p) for p in data.get("sharedTooling", [])]
        self._specs: dict[str, dict[str, Any]] = data.get("specs", {})

    def spec(self, spec_id: str) -> dict:
        try:
            return self._specs[spec_id]
        except KeyError as exc:
            known = ", ".join(self.spec_ids()) or "(none)"
            raise KeyError(f"unknown spec id {spec_id!r}; known specs: {known}") from exc

    def spec_ids(self) -> list[str]:
        return sorted(self._specs)

    def closure(self, spec_id: str) -> list[str]:
        return self._relation_closure(spec_id, "closure", include_self=True)

    def vendor(self, spec_id: str) -> list[str]:
        vendors: list[str] = []
        seen: set[str] = set()
        for moving in self.closure(spec_id):
            for vendored in self._relation_closure(moving, "vendor", include_self=False):
                if vendored not in seen:
                    seen.add(vendored)
                    vendors.append(vendored)
        return vendors

    def _relation_closure(self, spec_id: str, relation: str, include_self: bool) -> list[str]:
        self.spec(spec_id)
        result: list[str] = []
        seen: set[str] = set()

        def visit(current: str) -> None:
            if current in seen:
                return
            seen.add(current)
            if include_self or current != spec_id:
                result.append(current)
            for dep in sorted(self.spec(current).get(relation, [])):
                visit(dep)

        if include_self:
            visit(spec_id)
        else:
            for dep in sorted(self.spec(spec_id).get(relation, [])):
                visit(dep)
        return result

    def file_set(self, spec_id: str) -> list[str]:
        files: set[str] = set()
        for current in self.closure(spec_id):
            files.update(self._own_file_set(current))
        return sorted(files)

    def export_set(self, spec_id: str) -> list[str]:
        files: set[str] = set()
        for current in self.closure(spec_id):
            files.update(self._own_export_set(current))
        for current in self.vendor(spec_id):
            files.update(self._own_export_set(current))
        # Shared tooling is duplicated into the private repository rather than moved: the
        # public side still needs it for specifications that are not under review, and the
        # private side needs it because released tooling imports it. Without this the export
        # carries generators whose `sys.path` insert resolves to nothing.
        for shared in self.sharedTooling:
            files.update(_walk_files(shared))
        return sorted(files)

    def dependents(self, spec_id: str) -> list[str]:
        self.spec(spec_id)
        return [
            current
            for current in self.spec_ids()
            if current != spec_id
            and self.spec(current).get("submitted") is True
            and spec_id in self.closure(current)
        ]

    def validate(self) -> list[str]:
        problems: list[str] = []
        problems.extend(self._validate_shape())
        if problems:
            return problems

        problems.extend(self._validate_paths())
        problems.extend(self._validate_relations())
        problems.extend(self._validate_overlaps())
        problems.extend(self._validate_shared_tooling())
        problems.extend(self._validate_closure_complete())
        problems.extend(self._validate_moving_python_paths())
        problems.extend(self._validate_nonmoving_python_paths())
        return sorted(dict.fromkeys(problems))

    def _own_file_set(self, spec_id: str) -> set[str]:
        spec = self.spec(spec_id)
        keep_public = [_norm(p) for p in spec.get("keepPublic", [])]
        files: set[str] = set()
        for move in spec.get("move", []):
            for file_path in _walk_files(move):
                if not any(_is_under(file_path, keep) for keep in keep_public):
                    files.add(file_path)
        return files

    def _own_export_set(self, spec_id: str) -> set[str]:
        files: set[str] = set()
        for move in self.spec(spec_id).get("move", []):
            files.update(_walk_files(move))
        return files

    def _validate_shape(self) -> list[str]:
        problems: list[str] = []
        if not isinstance(self._data, dict):
            return ["manifest root must be an object"]
        if not isinstance(self.publicRepo, str) or not self.publicRepo:
            problems.append("publicRepo must be a non-empty string")
        if not isinstance(self.privateRepo, str) or not self.privateRepo:
            problems.append("privateRepo must be a non-empty string")
        if not isinstance(self.sharedTooling, list):
            problems.append("sharedTooling must be a list")
        if not isinstance(self._specs, dict) or not self._specs:
            problems.append("specs must be a non-empty object")
        required = {
            "title",
            "submitted",
            "state",
            "move",
            "keepPublic",
            "closure",
            "vendor",
            "wordSpecs",
            "validateAll",
            "reverseRefs",
        }
        for spec_id, spec in self._specs.items():
            if not isinstance(spec, dict):
                problems.append(f"{spec_id}: spec entry must be an object")
                continue
            missing = sorted(required - set(spec))
            if missing:
                problems.append(f"{spec_id}: missing fields: {', '.join(missing)}")
            if spec.get("state") not in {"public", "released"}:
                problems.append(f"{spec_id}: state must be 'public' or 'released'")
            if not isinstance(spec.get("submitted"), bool):
                problems.append(f"{spec_id}: submitted must be true or false")
            if spec.get("submitted") is False and spec.get("state") == "released":
                problems.append(f"{spec_id}: submitted false spec cannot have state 'released'")
            for key in ("move", "keepPublic", "closure", "vendor", "wordSpecs", "reverseRefs"):
                if key in spec and not isinstance(spec[key], list):
                    problems.append(f"{spec_id}: {key} must be a list")
            validate_all = spec.get("validateAll")
            if validate_all is not None and not isinstance(validate_all, str):
                problems.append(f"{spec_id}: validateAll must be a string or null")
        return problems

    def _validate_paths(self) -> list[str]:
        problems: list[str] = []
        for path in self.sharedTooling:
            if not _path_exists(path):
                problems.append(f"sharedTooling path does not exist: {path}")

        # Entries declared by a released specification, which lives in the private repository.
        # A public specification may legitimately reverse-reference one of them.
        released_roots = [
            move
            for spec_id in self.spec_ids()
            if self.spec(spec_id).get("state") != "public"
            for move in self.spec(spec_id).get("move", [])
        ]

        for spec_id in self.spec_ids():
            spec = self.spec(spec_id)
            # A released specification lives in the private repository, so its paths are
            # absent here by design. Requiring them would make the first release block every
            # later one, and would make the manifest permanently invalid while review runs.
            if spec.get("state") != "public":
                continue
            for key in ("move", "keepPublic", "wordSpecs", "reverseRefs"):
                for path in spec.get(key, []):
                    if _path_exists(path):
                        continue
                    if key == "reverseRefs" and any(_is_under(path, root) for root in released_roots):
                        continue
                    problems.append(f"{spec_id}: {key} path does not exist: {_norm(path)}")
            validate_all = spec.get("validateAll")
            if validate_all is not None and not _path_exists(validate_all):
                problems.append(f"{spec_id}: validateAll path does not exist: {_norm(validate_all)}")
            for keep in spec.get("keepPublic", []):
                if not any(_is_under(keep, move) for move in spec.get("move", [])):
                    problems.append(f"{spec_id}: keepPublic path is not inside a move entry: {_norm(keep)}")
        return problems

    def _validate_relations(self) -> list[str]:
        problems: list[str] = []
        known = set(self.spec_ids())
        for spec_id in self.spec_ids():
            closure = set(self.spec(spec_id).get("closure", []))
            vendor = set(self.spec(spec_id).get("vendor", []))
            for relation, deps in (("closure", closure), ("vendor", vendor)):
                for dep in deps:
                    if dep not in known:
                        problems.append(f"{spec_id}: {relation} contains unknown spec id: {dep}")
            both = sorted(closure & vendor)
            if both:
                problems.append(f"{spec_id}: closure and vendor overlap: {', '.join(both)}")

        for spec_id in self.spec_ids():
            closure = set(self.closure(spec_id))
            vendors = set(self.vendor(spec_id))
            both = sorted(closure & vendors)
            if both:
                problems.append(f"{spec_id}: transitive closure and vendor overlap: {', '.join(both)}")
            for dep in sorted(closure - {spec_id}):
                if self.spec(dep).get("submitted") is False:
                    problems.append(f"{spec_id}: submitted false spec {dep} must be vendored, not in closure")

        visiting: set[str] = set()
        visited: set[str] = set()
        stack: list[str] = []

        def visit(current: str) -> None:
            if current in visiting:
                cycle = stack[stack.index(current):] + [current]
                problems.append("closure/vendor cycle: " + " -> ".join(cycle))
                return
            if current in visited:
                return
            visiting.add(current)
            stack.append(current)
            for dep in sorted(set(self.spec(current).get("closure", [])) | set(self.spec(current).get("vendor", []))):
                if dep in known:
                    visit(dep)
            stack.pop()
            visiting.remove(current)
            visited.add(current)

        for spec_id in self.spec_ids():
            visit(spec_id)
        return problems

    def _validate_overlaps(self) -> list[str]:
        problems: list[str] = []
        owners: dict[str, str] = {}
        for spec_id in self.spec_ids():
            for file_path in self._own_file_set(spec_id):
                prior = owners.get(file_path)
                if prior is None:
                    owners[file_path] = spec_id
                    continue
                prior_closure = set(self.closure(prior))
                current_closure = set(self.closure(spec_id))
                if spec_id not in prior_closure and prior not in current_closure:
                    problems.append(f"{file_path}: moved by both {prior} and {spec_id}")
        return problems

    def _validate_shared_tooling(self) -> list[str]:
        problems: list[str] = []
        for shared in self.sharedTooling:
            for spec_id in self.spec_ids():
                for move in self.spec(spec_id).get("move", []):
                    if _is_under(shared, move):
                        problems.append(f"{spec_id}: sharedTooling path is inside move set: {shared}")
        return problems

    def _validate_closure_complete(self) -> list[str]:
        problems: list[str] = []
        owners = self._path_owners()
        uri_owners = self._model_uri_owners(owners)

        for spec_id in self.spec_ids():
            needed: set[str] = set()
            files = self._own_file_set(spec_id)
            for file_path in files:
                path = _abs(file_path)
                if file_path.endswith(".NodeSet2.xml"):
                    needed.update(self._required_model_deps(file_path, uri_owners))
                if file_path.endswith(".md"):
                    needed.update(self._markdown_link_deps(path, spec_id, owners))
                if file_path.endswith(".py"):
                    needed.update(self._python_path_deps(path, spec_id))

            for word_spec in self.spec(spec_id).get("wordSpecs", []):
                try:
                    with _abs(word_spec).open("r", encoding="utf-8") as handle:
                        word_data = json.load(handle)
                except (OSError, json.JSONDecodeError):
                    continue
                for referenced in _json_paths(word_data):
                    owner = owners.get(referenced)
                    if owner and owner != spec_id:
                        needed.add(owner)

            available = set(self.closure(spec_id)) | set(self.vendor(spec_id))
            for dep in sorted(needed):
                if dep != spec_id and dep not in available:
                    problems.append(f"{spec_id}: derived dependency {dep} is missing from closure or vendor")
        return problems

    def _validate_nonmoving_python_paths(self) -> list[str]:
        problems: list[str] = []
        spec_files = {spec_id: sorted(self._own_file_set(spec_id)) for spec_id in self.spec_ids()}
        tool_paths = sorted(
            list((REPO_ROOT / "core-specs" / "extras").glob("**/tools/*.py"))
            + list((REPO_ROOT / "metaverse-specs" / "extras").glob("**/tools/*.py"))
            + list((REPO_ROOT / "wot-specs").glob("**/tools/*.py"))
        )
        for spec_id in self.spec_ids():
            if self.spec(spec_id).get("submitted") is False:
                continue
            moving = spec_files[spec_id]
            if not moving:
                continue
            covered_by_dependent_release: set[str] = set()
            for other_id in self.spec_ids():
                if spec_id in self.closure(other_id):
                    covered_by_dependent_release.update(spec_files[other_id])
            for tool_path in tool_paths:
                rel_tool = _rel(tool_path)
                if rel_tool in covered_by_dependent_release:
                    continue
                for candidate in self._python_component_paths(tool_path):
                    if _is_under(rel_tool, candidate):
                        continue
                    if self._touches_file_set(candidate, moving):
                        problems.append(
                            f"{rel_tool}: component-built path {candidate} points into {spec_id}'s moving file set"
                        )
        return problems

    def _validate_moving_python_paths(self) -> list[str]:
        problems: list[str] = []
        for spec_id in self.spec_ids():
            if self.spec(spec_id).get("submitted") is False:
                continue
            public_files = set(self.file_set(spec_id))
            export_files = self.export_set(spec_id)
            for file_path in sorted(public_files):
                if not file_path.endswith(".py") or "/tools/" not in file_path:
                    continue
                for candidate in self._python_component_paths(_abs(file_path)):
                    candidate_path = _abs(candidate)
                    if not candidate_path.exists():
                        continue
                    if self._touches_file_set(candidate, export_files):
                        continue
                    if any(_is_under(candidate, shared) for shared in self.sharedTooling):
                        continue
                    problems.append(
                        f"{file_path}: component-built path {candidate} is not included in {spec_id}'s export set"
                    )
        return problems

    def _touches_file_set(self, candidate: str, file_set: list[str]) -> bool:
        candidate = _norm(candidate)
        return any(path == candidate or path.startswith(candidate.rstrip("/") + "/") for path in file_set)

    def _python_component_paths(self, path: Path) -> set[str]:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            return set()

        env: dict[str, str] = {"__file__": str(path)}
        candidates: set[str] = set()

        def func_name(node: ast.AST) -> str | None:
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Attribute):
                base = func_name(node.value)
                return f"{base}.{node.attr}" if base else node.attr
            if isinstance(node, ast.Call):
                base = func_name(node.func)
                return f"{base}()" if base else None
            if isinstance(node, ast.Subscript):
                base = func_name(node.value)
                return f"{base}[]" if base else None
            return None

        def eval_node(node: ast.AST) -> str | None:
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                return node.value
            if isinstance(node, ast.Name):
                return env.get(node.id)
            if isinstance(node, ast.Call):
                name = func_name(node.func)
                if name in {"os.path.join", "posixpath.join", "ntpath.join"}:
                    parts = [eval_node(arg) for arg in node.args]
                    if all(part is not None for part in parts):
                        return os.path.join(*(part for part in parts if part is not None))
                if name == "repo_path":
                    parts = [eval_node(arg) for arg in node.args]
                    if all(part is not None for part in parts):
                        return str((REPO_ROOT / Path(*(part for part in parts if part is not None))).resolve())
                if name in {"os.path.abspath", "os.path.normpath"} and node.args:
                    value = eval_node(node.args[0])
                    if value is not None:
                        return os.path.abspath(value) if name.endswith("abspath") else os.path.normpath(value)
                if name == "os.path.dirname" and node.args:
                    value = eval_node(node.args[0])
                    if value is not None:
                        return os.path.dirname(value)
                if name == "Path" and node.args:
                    return eval_node(node.args[0])
                if name and name.endswith(".resolve") and isinstance(node.func, ast.Attribute):
                    value = eval_node(node.func.value)
                    return os.path.abspath(value) if value is not None else None
            if isinstance(node, ast.Attribute) and node.attr == "parent":
                value = eval_node(node.value)
                return os.path.dirname(value) if value is not None else None
            if isinstance(node, ast.Subscript):
                base_name = func_name(node.value)
                if base_name and base_name.endswith(".parents"):
                    value_node = node.value
                    assert isinstance(value_node, ast.Attribute)
                    base = eval_node(value_node.value)
                    idx = None
                    if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, int):
                        idx = node.slice.value
                    if base is not None and idx is not None:
                        parent = Path(base).resolve().parents[idx]
                        return str(parent)
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                left = eval_node(node.left)
                right = eval_node(node.right)
                if left is not None and right is not None:
                    return os.path.join(left, right)
            return None

        for stmt in tree.body:
            if isinstance(stmt, ast.Assign):
                value = eval_node(stmt.value)
                if value is not None:
                    for target in stmt.targets:
                        if isinstance(target, ast.Name):
                            env[target.id] = value
                    if isinstance(stmt.value, ast.Call):
                        self._add_repo_candidate(candidates, value)
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.value is not None:
                value = eval_node(stmt.value)
                if value is not None:
                    env[stmt.target.id] = value
                    if isinstance(stmt.value, ast.Call):
                        self._add_repo_candidate(candidates, value)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and ("join" in (func_name(node.func) or "") or func_name(node.func) == "repo_path"):
                value = eval_node(node)
                if value is not None:
                    self._add_repo_candidate(candidates, value)
        return candidates

    def _add_repo_candidate(self, candidates: set[str], value: str) -> None:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = (REPO_ROOT / candidate).resolve()
        else:
            candidate = candidate.resolve()
        try:
            rel = _rel(candidate)
        except ValueError:
            return
        parts = rel.split("/")
        if len(parts) < 4 and (not candidate.exists() or not candidate.is_file()):
            return
        if candidate.exists() and candidate.is_dir() and parts[-1] not in {"examples", "schemas", "tools", "legacy"}:
            return
        candidates.add(rel)

    def _path_owners(self) -> dict[str, str]:
        owners: dict[str, str] = {}
        for spec_id in self.spec_ids():
            for file_path in self._own_file_set(spec_id):
                owners[file_path] = spec_id
        return owners

    def _model_uri_owners(self, owners: dict[str, str]) -> dict[str, str]:
        uri_owners: dict[str, str] = {}
        for file_path, spec_id in owners.items():
            if not file_path.endswith(".NodeSet2.xml"):
                continue
            try:
                root = ET.parse(_abs(file_path)).getroot()
            except ET.ParseError:
                continue
            for model in root.findall(f".//{NODESET_NS}Models/{NODESET_NS}Model"):
                uri = model.get("ModelUri")
                if uri and uri != BASE_MODEL_URI:
                    uri_owners.setdefault(uri, spec_id)
        return uri_owners

    def _required_model_deps(self, file_path: str, uri_owners: dict[str, str]) -> set[str]:
        deps: set[str] = set()
        try:
            root = ET.parse(_abs(file_path)).getroot()
        except ET.ParseError:
            return deps
        for required in root.findall(f".//{NODESET_NS}RequiredModel"):
            uri = required.get("ModelUri")
            owner = uri_owners.get(uri or "")
            if owner:
                deps.add(owner)
        return deps

    def _markdown_link_deps(self, path: Path, spec_id: str, owners: dict[str, str]) -> set[str]:
        deps: set[str] = set()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return deps
        for target in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", text):
            target = target.strip()
            if "://" in target or not target:
                continue
            resolved = (path.parent / Path(*_norm(target).split("/"))).resolve()
            try:
                rel = _rel(resolved)
            except ValueError:
                continue
            if resolved.is_dir():
                prefix = rel.rstrip("/") + "/"
                target_owners = {owner for file_path, owner in owners.items() if file_path.startswith(prefix)}
                for owner in target_owners:
                    if owner in self.closure(spec_id) or not self._is_reverse_ref(_rel(path), owner):
                        deps.add(owner)
            else:
                owner = owners.get(rel)
                if owner and (owner in self.closure(spec_id) or not self._is_reverse_ref(_rel(path), owner)):
                    deps.add(owner)
        return deps

    def _is_reverse_ref(self, file_path: str, target_spec_id: str) -> bool:
        return _norm(file_path) in {_norm(path) for path in self.spec(target_spec_id).get("reverseRefs", [])}

    def _python_path_deps(self, path: Path, spec_id: str) -> set[str]:
        deps: set[str] = set()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            return deps
        literals = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        for other_id in self.spec_ids():
            if other_id == spec_id:
                continue
            for move in self.spec(other_id).get("move", []):
                parts = [part for part in _norm(move).split("/") if part and part not in TREE_NAMES and part != "extras"]
                if parts and all(part in literals for part in parts):
                    deps.add(other_id)
                normalized = _norm(move)
                if any(normalized in literal.replace("\\", "/") for literal in literals):
                    deps.add(other_id)
        return deps


def load(path: str | None = None) -> Manifest:
    manifest_path = Path(path) if path is not None else DEFAULT_MANIFEST
    if not manifest_path.is_absolute():
        manifest_path = REPO_ROOT / manifest_path
    with manifest_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return Manifest(data, manifest_path)


def main() -> int:
    manifest = load(sys.argv[1] if len(sys.argv) > 1 else None)
    problems = manifest.validate()
    if problems:
        print("Manifest validation failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print(f"Manifest valid: {len(manifest.spec_ids())} specs")
    for spec_id in manifest.spec_ids():
        print(
            f"- {spec_id}: submitted={manifest.spec(spec_id).get('submitted')} "
            f"closure={manifest.closure(spec_id)} vendor={manifest.vendor(spec_id)} "
            f"files={len(manifest.file_set(spec_id))} export={len(manifest.export_set(spec_id))}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
