"""Content-only routing between public layouts and working-group review repositories."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import json
import posixpath
import re
import subprocess
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

IGNORED_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
PROTECTED_ROOTS = {
    ".github", ".config", ".git", ".gitignore", ".gitattributes", ".gitmodules",
    ".markdownlint-cli2.yaml", "AUTHORING.md", "legal.md", "skills", "templates",
    "tools", "install-tools.ps1", "install-tools.sh", "docs", "artifacts",
}
PROTECTED_SOURCE = {"agreement-of-use.md", "logo-left.jpg", "logo-right.jpg", "figures"}


def relative_path(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("a non-empty repository-relative path is required")
    value = value.replace("\\", "/")
    parts = value.split("/")
    if (value.startswith("/") or re.match(r"^[A-Za-z]:", value)
            or any(part in {"", ".", ".."} for part in parts)):
        raise ValueError(f"unsafe repository-relative path: {value!r}")
    return value


def under(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(prefix + "/")


def checked_path(root: Path, relative: str) -> Path:
    relative = relative_path(relative)
    result = root.joinpath(*relative.split("/")).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError(f"path escapes repository through a link: {relative}")
    return result


def require_review_repository(root: Path, repository: str) -> None:
    result = subprocess.run(["git", "-C", str(root), "config", "--get", "remote.origin.url"],
                            capture_output=True, text=True)
    if result.returncode:
        raise ValueError("review root must be a Git checkout with an origin remote")
    url = result.stdout.strip()
    if url.startswith("git@github.com:"):
        actual = url[len("git@github.com:"):]
    else:
        parsed = urlsplit(url)
        actual = parsed.path.lstrip("/") if parsed.hostname == "github.com" and parsed.scheme in {"https", "ssh"} else ""
    actual = actual.rstrip("/").removesuffix(".git")
    if actual.lower() != repository.lower():
        raise ValueError(f"review checkout does not belong to {repository}; refusing to modify it")


@dataclass(frozen=True)
class Mapping:
    public: str
    review: str
    directory: bool = True

    def translate(self, path: str, reverse: bool = False) -> str | None:
        source, target = (self.review, self.public) if reverse else (self.public, self.review)
        if path == source:
            return target
        if self.directory and path.startswith(source + "/"):
            return target + path[len(source):]
        return None


@dataclass(frozen=True)
class Route:
    repository: str
    submodule: str
    group: str
    mappings: tuple[Mapping, ...]
    excluded: tuple[str, ...] = ()
    legacy_layout: bool = False

    @property
    def identity_layout(self) -> bool:
        return self.legacy_layout and not self.mappings

    def translate(self, path: str, reverse: bool = False) -> str:
        path = relative_path(path)
        if self.identity_layout:
            return path
        order = sorted(self.mappings, key=lambda item: len(item.review if reverse else item.public), reverse=True)
        for mapping in order:
            result = mapping.translate(path, reverse)
            if result is not None:
                return relative_path(result)
        raise ValueError(f"no {self.group} {'return' if reverse else 'release'} mapping for {path}")

    def excludes(self, public_path: str) -> bool:
        return any(under(public_path, prefix) for prefix in self.excluded)

    def require_content(self, review_path: str) -> None:
        parts = PurePosixPath(relative_path(review_path)).parts
        if parts[0] in PROTECTED_ROOTS:
            raise ValueError(f"review infrastructure is protected: {review_path}")
        if parts[0] == "source" and len(parts) > 1 and parts[1] in PROTECTED_SOURCE:
            raise ValueError(f"shared publication infrastructure is protected: {review_path}")
        if not self.legacy_layout and (parts[0] == "word-drafts" or parts[0] not in {"source", "model", "extras"}):
            raise ValueError(f"not WG specification content: {review_path}")


def route_for(manifest, spec_id: str) -> Route:
    spec = manifest.spec(spec_id)
    key = spec.get("reviewRepository", "core")
    repositories = manifest._data.get("reviewRepositories", {})
    config = repositories.get(key)
    if config is None:
        if key != "core":
            raise ValueError(f"{spec_id}: unknown review repository {key!r}")
        config = {"repository": manifest.privateRepo, "submodule": "spec-drafts", "group": "Core"}
    repository = config.get("repository")
    if not isinstance(repository, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError(f"{spec_id}: invalid review repository")
    mappings = []
    for item in spec.get("reviewPaths", []):
        if not isinstance(item, dict) or set(item) != {"public", "review", "directory"} or type(item["directory"]) is not bool:
            raise ValueError(f"{spec_id}: invalid review path mapping")
        mappings.append(Mapping(relative_path(item["public"]), relative_path(item["review"]), item["directory"]))
    legacy = key == "core" and repository.lower() == "opcf-members/spec-drafts"
    if not legacy and not mappings:
        raise ValueError(f"{spec_id}: WG routing requires explicit path mappings")
    route = Route(repository, relative_path(config["submodule"]), config["group"],
                  tuple(mappings), tuple(relative_path(p) for p in spec.get("reviewExclude", [])), legacy)
    for mapping in mappings:
        route.require_content(mapping.review)
    for field in ("public", "review"):
        keys = [getattr(item, field) for item in mappings]
        if len(keys) != len(set(keys)):
            raise ValueError(f"{spec_id}: duplicate {field} mapping")
    return route


def closure_routes(manifest, spec_id: str) -> dict[str, Route]:
    routes = {key: route_for(manifest, key) for key in manifest.closure(spec_id)}
    if len({route.repository for route in routes.values()}) != 1:
        raise ValueError(f"{spec_id}: a release closure cannot cross working-group repositories; use a dependency snapshot")
    return routes


def owner_for_public(manifest, path: str) -> tuple[str, Route]:
    path = relative_path(path)
    candidates = []
    for spec_id in manifest.spec_ids():
        route = route_for(manifest, spec_id)
        prefixes = [mapping.public for mapping in route.mappings] + manifest.spec(spec_id)["move"]
        for prefix in prefixes:
            if under(path, prefix):
                candidates.append((len(prefix), spec_id, route))
    if not candidates:
        raise ValueError(f"no specification owns {path}")
    _, spec_id, route = max(candidates, key=lambda item: item[0])
    return spec_id, route


def public_file_map(manifest, spec_id: str, files: list[str]) -> dict[str, str]:
    """Map moving public files; dependencies/infrastructure are never silently exported."""
    routes = closure_routes(manifest, spec_id)
    result = {}
    targets = {}
    for path in files:
        owner, route = owner_for_public(manifest, path)
        if owner not in routes:
            raise ValueError(f"{path}: outside the selected release closure")
        if route.excludes(path):
            continue
        target = route.translate(path)
        route.require_content(target)
        if target in targets:
            raise ValueError(f"release paths collide at {target}: {targets[target]} and {path}")
        targets[target] = path
        result[path] = target
    return result


def review_file_map(manifest, spec_id: str, root: Path) -> dict[str, str]:
    """Read the actual review checkout, including destination-only additions."""
    routes = closure_routes(manifest, spec_id)
    result = {}
    for key, route in routes.items():
        mappings = route.mappings
        if route.identity_layout:
            mappings = tuple(Mapping(p, p, "." not in PurePosixPath(p).name)
                             for p in manifest.spec(key)["move"])
        candidates = set()
        for mapping in mappings:
            path = checked_path(root, mapping.review)
            if path.is_file():
                candidates.add(mapping.review)
            elif path.is_dir():
                candidates.update(file.relative_to(root).as_posix() for file in path.rglob("*")
                                  if file.is_file() and not IGNORED_DIRS.intersection(file.relative_to(root).parts)
                                  and file.suffix not in IGNORED_SUFFIXES)
        for relative in sorted(candidates):
            checked_path(root, relative)
            route.require_content(relative)
            public = route.translate(relative, reverse=True)
            if (any(under(public, prefix) for prefix in manifest.sharedTooling)
                    or (route.legacy_layout and not any(
                        under(public, prefix) for prefix in manifest.spec(key)["move"]))):
                # Explicitly mapped shared helpers are export inputs, not returned ownership.
                continue
            if route.excludes(public) or any(under(public, p) for p in manifest.spec(key).get("keepPublic", [])):
                continue
            if public in result and result[public] != relative:
                raise ValueError(f"return paths collide at {public}")
            result[public] = relative
    return result


def cleanup_file_map(manifest, spec_id: str, root: Path) -> dict[str, str]:
    """Refuse removal of a model still required by content left in the repository."""
    files = review_file_map(manifest, spec_id, root)
    removing = set(files.values())
    namespace = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"
    removed_models = {}
    remaining = []
    for path in (root / "model").rglob("*.xml"):
        relative = path.relative_to(root).as_posix()
        checked_path(root, relative)
        try:
            tree = ET.parse(path)
        except ET.ParseError as error:
            raise ValueError(f"cannot verify cleanup dependencies: malformed {relative}") from error
        models = tree.findall(namespace + "Models/" + namespace + "Model")
        normalized = path.read_bytes().replace(b"\r\n", b"\n")
        if relative in removing:
            for model in models:
                removed_models[model.get("ModelUri")] = (relative, normalized)
        else:
            remaining.extend((relative, model, normalized) for model in models)
    for relative, model, _payload in remaining:
        for requirement in model.findall(namespace + "RequiredModel"):
            uri = requirement.get("ModelUri")
            if uri not in removed_models:
                continue
            original, payload = removed_models[uri]
            retained = any(candidate.get("ModelUri") == uri and content == payload
                           for _path, candidate, content in remaining)
            if not retained:
                raise ValueError(
                    f"cleanup would remove {original} still required by {relative}; "
                    "retain a byte-identical pinned dependency before removing its owning specification")
    return files


def translated_content(manifest, spec_id: str, source: str, destination: str,
                       payload: bytes, *, reverse: bool = False) -> bytes:
    """Translate publication paths, never model identities or arbitrary source code."""
    route = route_for(manifest, spec_id)
    if route.identity_layout:
        return payload
    suffix = PurePosixPath(source).suffix.lower()
    if suffix not in {".md", ".json"}:
        return payload
    text = payload.decode("utf-8")
    routes = {key: route_for(manifest, key) for key in manifest.spec_ids()}
    moving = set(manifest.closure(spec_id))

    def locate(path):
        matches = []
        for key, other in routes.items():
            if reverse and other.repository != route.repository:
                continue
            for mapping in other.mappings:
                prefix = mapping.review if reverse else mapping.public
                mapped = mapping.translate(path, reverse)
                if mapped is not None:
                    matches.append((len(prefix), key, other, mapped))
        return max(matches, key=lambda item: item[0]) if matches else None

    if suffix == ".json":
        if PurePosixPath(source).name != "manifest.json":
            return payload
        document = json.loads(text)
        if not isinstance(document, dict):
            raise ValueError(f"{source}: manifest must be an object")
        model = document.get("model")
        if isinstance(model, dict):
            for key in ("nodeset", "generator"):
                if key in model:
                    found = locate(relative_path(model[key]))
                    if found is None:
                        raise ValueError(f"{source}: no route for model.{key}: {model[key]}")
                    model[key] = found[3]
        file_owner = locate(source)
        if file_owner is None:
            raise ValueError(f"no publication owns {source}")
        publications = manifest.spec(file_owner[1]).get("publisherSpecs", [])
        if len(publications) != 1:
            raise ValueError(f"{spec_id}: one publication identity is required for routing")
        number = publications[0]["docNumber"]
        if not re.fullmatch(r"OPC [0-9]+(?:-[0-9]+)?", number):
            raise ValueError(f"{spec_id}: invalid document number")
        if not isinstance(document.get("identity"), dict):
            raise ValueError(f"{source}: publication identity is missing")
        document["identity"]["docNumber"] = number
        output = document.get("output")
        if isinstance(output, dict):
            output["sts"] = f"artifacts/{number.replace(' ', '-')}.xml"
            output["documentationCsv"] = f"artifacts/{number.replace(' ', '-')}-documentation.csv"
        return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")

    def link(match):
        target = match.group(1)
        if target.startswith(("#", "/", "<")) or re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", target):
            return match.group(0)
        path, marker, fragment = target.partition("#")
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source), path))
        found = locate(resolved)
        if found is None:
            return match.group(0)
        _, owner, other, mapped = found
        if not reverse and other.repository != route.repository:
            mapped = f"https://github.com/{other.repository}/blob/main/{mapped}"
        elif reverse and owner not in moving:
            mapped = f"https://github.com/{route.repository}/blob/main/{resolved}"
        else:
            mapped = posixpath.relpath(mapped, posixpath.dirname(destination))
        return "](" + mapped + (marker + fragment if marker else "") + ")"

    lines = []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            lines.append(line)
            continue
        if fence is None:
            # A literal example of Markdown link syntax is not a navigational link.
            spans = re.split(r"(`[^`\n]*`)", line)
            for index in range(0, len(spans), 2):
                spans[index] = re.sub(r"\]\(([^)\s]+)\)", link, spans[index])
            line = "".join(spans)
        lines.append(line)
    return "".join(lines).encode("utf-8")
