#!/usr/bin/env python3
"""Independent semantic validator for the xRegistry AAS specifications."""

from __future__ import annotations

import base64
import copy
import hashlib
import ipaddress
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


HERE = Path(__file__).resolve().parent
AAS_DIR = HERE.parent
MODEL_PATH = AAS_DIR / "xRegistry-AAS.model.json"
REGISTRY_SPEC_PATH = AAS_DIR / "xRegistry-AAS.md"
PACKAGE_SPEC_PATH = AAS_DIR / "xRegistry-AAS-Packages.md"

ID_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")
OCI_DIGEST_RE = re.compile(r"^[a-z0-9]+(?:[+._-][a-z0-9]+)*:[a-f0-9]+$")
OCI_TAG_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$")
URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*$")
URI_ABSOLUTE_PREFIX_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*):")
URI_USERINFO_RE = re.compile(
    r"^(?:[A-Za-z0-9._~!$&'()*+,;=:-]|%[0-9A-Fa-f]{2})*$"
)
URI_REG_NAME_RE = re.compile(
    r"^(?:[A-Za-z0-9._~!$&'()*+,;=-]|%[0-9A-Fa-f]{2})+$"
)
URI_IPVFUTURE_RE = re.compile(
    r"^v[0-9A-Fa-f]+\.(?:[A-Za-z0-9._~!$&'()*+,;=:-])+$",
    re.IGNORECASE,
)
BAD_PERCENT_ESCAPE_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")
URI_PCHAR_PATTERN = r"(?:[A-Za-z0-9._~!$&'()*+,;=:@-]|%[0-9A-Fa-f]{2})"
URI_PATH_RE = re.compile(rf"^(?:/{URI_PCHAR_PATTERN}*)*$")
URI_QUERY_FRAGMENT_RE = re.compile(rf"^(?:{URI_PCHAR_PATTERN}|[/?])*$")

IDENTIFIER_EXAMPLES = {
    "https://fabrikam.com/aas/pump/SN-001":
        "com.fabrikam.aas.pump.SN-001."
        "07e57fb738a86393146c877d2808f53a695b5c561676cf9e10a89a127e2124a3",
    "https://contoso.com/ids/sm/nameplate":
        "com.contoso.ids.sm.nameplate."
        "118270ac2b1c9a2ea6a8a1baa6f97baf78cc576226978fbbbf36afdab3f4ee0d",
    "0173-1#02-AAO677#002":
        "0173-1-02-AAO677-002."
        "4a508ebd70e19917cd187073e2ff250e75d464260868f755e40ccb04d95948ca",
    "urn:uuid:2c4c1b0e-0e2a-4e2f-9a7e-3b3a1b7c9d21":
        "urn.uuid.2c4c1b0e-0e2a-4e2f-9a7e-3b3a1b7c9d21."
        "4c1bae38c355378c18a8b6a293df1ffa4143c4c0e591150417973255a6d265e9",
}

COLLIDING_PREFIX_SOURCES = (
    "https://example.com/ids/a+b",
    "https://example.com/ids/a:b",
)

OCI_EXAMPLES = (
    {
        "manifestdigest":
            "sha256:843f1b84d5129f49ddb26231c1f21fbe"
            "9ba5c78d3362731c27f16d1e467c20d0",
        "packagebase64": "QUFTWC1wYWNrYWdlLXYxCg==",
        "digest":
            "bb9aa6f9880d42b5c4afa6e61baa9b4e"
            "4e510e65c332ab62e85a1231c8f7517c",
    },
    {
        "manifestdigest":
            "sha256:14acf7d897aac9be7dcbcbb3cf57debf"
            "b650646e238078b34b1ef301f925b4ad",
        "packagebase64": "QUFTWC1wYWNrYWdlLXYyCg==",
        "digest":
            "e0c5a0a7d7a81a59853efc1b731eb1f"
            "fb8b54016c72dbca93ac33d32bb49f656",
    },
)

OCI_TAG_EXAMPLES = (
    "Release_2026.08",
    "_stable",
    "Rxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
)

OCI_REFERRER_EXAMPLE = {
    "subjectmanifestdigest": OCI_EXAMPLES[0]["manifestdigest"],
    "manifestdigest":
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "artifacttype": "application/vnd.dev.cosign.simplesigning.v1+json",
    "signer": "did:example:manufacturer",
    "attestationbase64": "YXR0ZXN0YXRpb24tdjEK",
    "digestalg": "Sha256",
    "digest":
        "a5dec971ce22f8a8080036cbc2a162733"
        "68074ed1c0e7be8bcfe51970bccfe19",
}


def _uri_authority_labels(source: str, parsed: object) -> list[str] | None:
    """Return labels only when the source has a valid RFC 3986 authority."""
    scheme = getattr(parsed, "scheme", "")
    authority = getattr(parsed, "netloc", "")
    if not URI_SCHEME_RE.fullmatch(scheme) or not authority:
        return None
    source_scheme = URI_ABSOLUTE_PREFIX_RE.match(source)
    if (
        source_scheme is None
        or source_scheme.group(1).casefold() != scheme.casefold()
    ):
        return None
    if any(
        char.isspace() or ord(char) < 0x20 or ord(char) == 0x7F
        for char in source
    ):
        return None
    if (
        not URI_PATH_RE.fullmatch(getattr(parsed, "path", ""))
        or not URI_QUERY_FRAGMENT_RE.fullmatch(getattr(parsed, "query", ""))
        or not URI_QUERY_FRAGMENT_RE.fullmatch(getattr(parsed, "fragment", ""))
    ):
        return None
    if any(
        BAD_PERCENT_ESCAPE_RE.search(component)
        for component in (
            authority,
            getattr(parsed, "path", ""),
            getattr(parsed, "query", ""),
            getattr(parsed, "fragment", ""),
        )
    ):
        return None

    separator = authority.rfind("@")
    if separator >= 0:
        if not URI_USERINFO_RE.fullmatch(authority[:separator]):
            return None
        host_port = authority[separator + 1:]
    else:
        host_port = authority
    if not host_port:
        return None

    port: str | None = None
    if host_port.startswith("["):
        end = host_port.find("]")
        if (
            end <= 1
            or host_port.count("[") != 1
            or host_port.count("]") != 1
        ):
            return None
        literal = host_port[1:end]
        suffix = host_port[end + 1:]
        if suffix:
            if not suffix.startswith(":"):
                return None
            port = suffix[1:]
        try:
            ipaddress.IPv6Address(literal)
        except ValueError:
            if not URI_IPVFUTURE_RE.fullmatch(literal):
                return None
        host_labels = [literal]
    else:
        if "[" in host_port or "]" in host_port or host_port.count(":") > 1:
            return None
        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
        else:
            host = host_port
        if not URI_REG_NAME_RE.fullmatch(host):
            return None
        host_labels = host.split(".")

    if port is not None:
        numeric_port = port.lstrip("0") or "0"
        if (
            not re.fullmatch(r"[0-9]+", port)
            or len(numeric_port) > 5
            or (len(numeric_port) == 5 and numeric_port > "65535")
        ):
            return None

    labels = list(reversed(host_labels))
    if port is not None:
        labels.append(port)
    return labels


def _source_labels(source: str) -> list[str]:
    try:
        parsed = urlsplit(source)
    except ValueError:
        parsed = None

    if parsed is not None:
        labels = _uri_authority_labels(source, parsed)
        if labels is not None:
            labels.extend(
                unquote(segment)
                for segment in parsed.path.split("/")
                if segment
            )
            return labels

    if source.lower().startswith("urn:"):
        return [unquote(segment) for segment in source.split(":") if segment]
    return [unquote(segment) for segment in source.split("/") if segment]


def readable_prefix(source: str) -> str:
    """Return the normalized, at-most-63-character readable id prefix."""
    normalized: list[str] = []
    for label in _source_labels(source):
        label = re.sub(r"[^A-Za-z0-9_.-]+", "-", label)
        label = re.sub(r"-+", "-", label)
        label = re.sub(r"\.+", ".", label).strip("-.")
        if label:
            normalized.append(label)

    if not normalized:
        return "_"

    while len(normalized) > 1 and len(".".join(normalized)) > 63:
        normalized.pop()

    prefix = ".".join(normalized)
    if len(prefix) > 63:
        prefix = prefix[:63].rstrip("-.")
    return prefix or "_"


def symbolic_identifier(source: str) -> str:
    """Implement the normative always-hashed symbolic identifier algorithm."""
    suffix = hashlib.sha256(source.encode("utf-8")).hexdigest()
    identifier = f"{readable_prefix(source)}.{suffix}"
    if not ID_RE.fullmatch(identifier):
        raise ValueError(f"invalid symbolic identifier for {source!r}: {identifier!r}")
    return identifier


def resource_xid(
    group_collection: str,
    group_source_identity: str,
    resource_collection: str | None = None,
    resource_source_identity: str | None = None,
) -> str:
    """Construct the relative xid from the full source-identity tuple."""
    xid = f"/{group_collection}/{symbolic_identifier(group_source_identity)}"
    if resource_collection is None and resource_source_identity is None:
        return xid
    if resource_collection is None or resource_source_identity is None:
        raise ValueError("resource collection and source identity must be supplied together")
    return f"{xid}/{resource_collection}/{symbolic_identifier(resource_source_identity)}"


def digest_bytes(data: bytes, algorithm: str) -> str:
    algorithms = {
        "Sha256": hashlib.sha256,
        "Sha384": hashlib.sha384,
        "Sha512": hashlib.sha512,
    }
    try:
        digest = algorithms[algorithm]
    except KeyError as exc:
        raise ValueError(f"unsupported digest algorithm: {algorithm}") from exc
    return digest(data).hexdigest()


def apply_oci_tag(
    versions: dict[str, dict[str, str]],
    tags: list[dict[str, str]],
    tag: str,
    manifest_digest: str,
    package_blob: bytes,
    digest_algorithm: str,
    package_digest: str,
) -> str:
    """Apply an OCI tag observation without mutating an existing Version."""
    if not OCI_TAG_RE.fullmatch(tag):
        raise ValueError("invalid OCI tag")
    if not OCI_DIGEST_RE.fullmatch(manifest_digest):
        raise ValueError("invalid OCI manifest digest")
    if digest_bytes(package_blob, digest_algorithm) != package_digest:
        raise ValueError("package blob digest mismatch")

    version_id = symbolic_identifier(manifest_digest)
    candidate = {
        "manifestdigest": manifest_digest,
        "digestalg": digest_algorithm,
        "digest": package_digest,
    }
    existing = versions.get(version_id)
    if existing is not None and existing != candidate:
        raise ValueError("attempt to mutate an immutable OCI Version")
    versions.setdefault(version_id, candidate)

    alias = {"tag": tag, "manifestdigest": manifest_digest}
    for index, existing_alias in enumerate(tags):
        if existing_alias.get("tag") == tag:
            tags[index] = alias
            break
    else:
        tags.append(alias)
    return version_id


def add_oci_referrer_resource(
    package_versions: dict[str, dict[str, str]],
    referrer_resources: dict[str, dict[str, object]],
    subject_manifest_digest: str,
    referrer_manifest_digest: str,
    attestation_blob: bytes,
    digest_algorithm: str,
    attestation_digest: str,
    artifact_type: str,
    signer: str | None = None,
) -> str:
    """Create a separate immutable referrer Resource for an OCI attestation."""
    for digest in (subject_manifest_digest, referrer_manifest_digest):
        if not OCI_DIGEST_RE.fullmatch(digest):
            raise ValueError("invalid OCI manifest digest")

    subject_version_id = symbolic_identifier(subject_manifest_digest)
    if subject_version_id not in package_versions:
        raise ValueError("unknown subject manifest")
    if not artifact_type:
        raise ValueError("missing OCI referrer artifact type")
    if digest_bytes(attestation_blob, digest_algorithm) != attestation_digest:
        raise ValueError("attestation blob digest mismatch")

    resource_id = symbolic_identifier(referrer_manifest_digest)
    version = {
        "subjectmanifestdigest": subject_manifest_digest,
        "manifestdigest": referrer_manifest_digest,
        "format": "Opaque/1.0",
        "artifacttype": artifact_type,
        "digestalg": digest_algorithm,
        "digest": attestation_digest,
    }
    if signer is not None:
        version["signer"] = signer

    candidate: dict[str, object] = {
        "referrerid": resource_id,
        "defaultversionid": resource_id,
        "versions": {resource_id: version},
    }
    existing = referrer_resources.get(resource_id)
    if existing is not None and existing != candidate:
        raise ValueError("attempt to mutate an immutable OCI referrer Resource")
    referrer_resources.setdefault(resource_id, candidate)
    return resource_id


def convert_resource_to_xref(resource: dict, target_xid: str) -> None:
    """Apply Core xref conversion only before any local Version exists."""
    if resource.get("versions"):
        raise ValueError("cannot convert retained local history to xref")
    resource["xref"] = target_xid


def _at(model: dict, *path: str) -> dict:
    value: object = model
    for component in path:
        if not isinstance(value, dict):
            return {}
        value = value.get(component, {})
    return value if isinstance(value, dict) else {}


def _check_identity(
    errors: list[str],
    attributes: dict,
    identity_name: str,
    context: str,
    versioned: bool,
) -> None:
    identity = attributes.get(identity_name)
    if not isinstance(identity, dict):
        errors.append(f"{context}: missing source identity {identity_name}")
        return
    if identity.get("required") is not True:
        errors.append(f"{context}.{identity_name}: source identity is not required")
    if identity.get("matchcase") is not True:
        errors.append(f"{context}.{identity_name}: source identity is not case-exact")
    if versioned and identity.get("matchversions") is not True:
        errors.append(f"{context}.{identity_name}: source identity is not invariant across Versions")
    if "always-hashed symbolic identifier" not in identity.get("description", ""):
        errors.append(f"{context}.{identity_name}: description omits the deterministic id rule")

    authority_marker = "sole resource source identity" if versioned else "sole group source identity"
    authorities = [
        name for name, definition in attributes.items()
        if isinstance(definition, dict)
        and authority_marker in definition.get("description", "").lower()
    ]
    if authorities != [identity_name]:
        errors.append(
            f"{context}: expected exactly one source identity {identity_name}, found {authorities}"
        )


def _check_history(
    errors: list[str],
    resource: dict,
    context: str,
    max_versions: int = 0,
) -> None:
    expected = {
        "maxversions": max_versions,
        "versionmode": "modifiedat",
        "singleversionroot": True,
    }
    for name, value in expected.items():
        if resource.get(name) != value:
            errors.append(f"{context}: {name} must be {value!r}")

    if "historypolicy" in resource.get("resourceattributes", {}):
        errors.append(
            f"{context}.resourceattributes: historypolicy is a domain extension "
            "and must be defined in metaattributes"
        )

    policy = resource.get("metaattributes", {}).get("historypolicy")
    if not isinstance(policy, dict):
        errors.append(f"{context}: missing meta.historypolicy")
        return
    if policy.get("required") is not True:
        errors.append(f"{context}.historypolicy: must be required")
    if policy.get("readonly") is not True:
        errors.append(f"{context}.historypolicy: must be server-controlled")
    if policy.get("default") != "retain-all":
        errors.append(f"{context}.historypolicy: default must be retain-all")
    if policy.get("enum") != ["retain-all"]:
        errors.append(f"{context}.historypolicy: only retain-all is conforming")
    if policy.get("strict") is not True:
        errors.append(f"{context}.historypolicy: strict must be true")


def validate_model(model: dict) -> list[str]:
    """Validate requirements that the generic xRegistry schema cannot express."""
    errors: list[str] = []
    groups = model.get("groups", {})

    group_identities = {
        "shells": "aasidentifier",
        "submodeltemplates": "templatenamespace",
        "conceptdictionaries": "dictionaryidentifier",
        "aasxregistries": "storeidentifier",
    }
    for group_name, identity_name in group_identities.items():
        group = groups.get(group_name, {})
        _check_identity(
            errors,
            group.get("attributes", {}),
            identity_name,
            f"groups.{group_name}.attributes",
            versioned=False,
        )

    resources = {
        "groups.shells.resources.submodels":
            _at(groups, "shells", "resources", "submodels"),
        "groups.conceptdictionaries.resources.conceptdescriptions":
            _at(groups, "conceptdictionaries", "resources", "conceptdescriptions"),
        "groups.aasxregistries.resources.packages":
            _at(groups, "aasxregistries", "resources", "packages"),
        "groups.aasxregistries.resources.referrers":
            _at(groups, "aasxregistries", "resources", "referrers"),
    }
    resource_identities = {
        "groups.shells.resources.submodels": "submodelidentifier",
        "groups.conceptdictionaries.resources.conceptdescriptions": "conceptidentifier",
        "groups.aasxregistries.resources.packages": "packageidentifier",
        "groups.aasxregistries.resources.referrers": "manifestdigest",
    }
    for context, resource in resources.items():
        _check_identity(
            errors,
            resource.get("attributes", {}),
            resource_identities[context],
            f"{context}.attributes",
            versioned=True,
        )
        _check_history(
            errors,
            resource,
            context,
            max_versions=1 if context.endswith(".referrers") else 0,
        )

    submodel_digest_algorithm = (
        resources["groups.shells.resources.submodels"]
        .get("attributes", {})
        .get("digestalg", {})
    )
    if submodel_digest_algorithm.get("enum") != ["Sha256", "Sha384", "Sha512"]:
        errors.append(
            "submodels.digestalg: must support exactly Sha256, Sha384 and Sha512"
        )
    if submodel_digest_algorithm.get("matchcase") is not True:
        errors.append("submodels.digestalg: exact enum case must be preserved")

    packages = resources["groups.aasxregistries.resources.packages"]
    package_attributes = packages.get("attributes", {})
    package_format = package_attributes.get("format", {})
    if package_format.get("enum") != ["AASX/3.0", "AASX/3.1"]:
        errors.append("packages.format: referrer-only Opaque/1.0 must not be listed")
    for name in ("digest", "digestalg"):
        if package_attributes.get(name, {}).get("required") is not True:
            errors.append(f"packages.{name}: package blob verification field must be required")
    digest_algorithm = package_attributes.get("digestalg", {})
    if digest_algorithm.get("enum") != ["Sha256", "Sha384", "Sha512"]:
        errors.append(
            "packages.digestalg: must support exactly Sha256, Sha384 and Sha512"
        )
    if digest_algorithm.get("strict") is not True:
        errors.append("packages.digestalg: unsupported algorithms must be rejected")
    if digest_algorithm.get("matchcase") is not True:
        errors.append("packages.digestalg: exact enum case must be preserved")
    if "MUST NOT substitute" not in digest_algorithm.get("description", ""):
        errors.append("packages.digestalg: descriptor algorithm must be retained exactly")
    manifest_digest = package_attributes.get("manifestdigest", {})
    if "Version source identity" not in manifest_digest.get("description", ""):
        errors.append("packages.manifestdigest: must identify the immutable OCI Version")
    if "package blob" not in manifest_digest.get("description", ""):
        errors.append("packages.manifestdigest: must be distinguished from the package blob")

    reserved_resource_attributes = packages.get("resourceattributes", {})
    if "tags" in reserved_resource_attributes:
        errors.append(
            "packages.resourceattributes: tags is a domain extension "
            "and must be defined in metaattributes"
        )
    if "referrers" in reserved_resource_attributes:
        errors.append(
            "packages.resourceattributes: referrers must be separate Resources"
        )

    meta_attributes = packages.get("metaattributes", {})
    tags = meta_attributes.get("tags")
    if not isinstance(tags, dict):
        errors.append("packages: missing meta.tags OCI alias entries")
    else:
        tag_item = tags.get("item", {})
        tag_attributes = tag_item.get("attributes", {})
        if tags.get("type") != "array" or tag_item.get("type") != "object":
            errors.append("packages.tags: must be an array of lossless alias entries")
        for name in ("tag", "manifestdigest"):
            definition = tag_attributes.get(name)
            if not isinstance(definition, dict) or definition.get("required") is not True:
                errors.append(f"packages.tags.{name}: must be required")
        if tag_attributes.get("tag", {}).get("matchcase") is not True:
            errors.append("packages.tags.tag: raw tag must be case-exact")
        if tag_attributes.get("manifestdigest", {}).get("matchcase") is not True:
            errors.append("packages.tags.manifestdigest: digest must be case-exact")
        if "tags" in package_attributes:
            errors.append("packages.tags: tags must not be Version attributes")
        description = tags.get("description", "").lower()
        if (
            "mutable" not in description
            or "raw" not in description
            or "must not be used as versionids" not in description
        ):
            errors.append(
                "packages.tags: description must make raw tags mutable non-Version aliases"
            )

    if "referrers" in meta_attributes:
        errors.append("packages.meta.referrers: referrers must be separate Resources")
    for name in ("subject", "attestations", "referrers"):
        if name in package_attributes:
            errors.append(
                f"packages.{name}: attestations must not be package Version attributes"
            )

    referrers = resources["groups.aasxregistries.resources.referrers"]
    referrer_attributes = referrers.get("attributes", {})
    for name in (
        "format",
        "manifestdigest",
        "subjectmanifestdigest",
        "artifacttype",
        "digest",
        "digestalg",
    ):
        if referrer_attributes.get(name, {}).get("required") is not True:
            errors.append(f"referrers.{name}: must be required")
    for name in ("manifestdigest", "subjectmanifestdigest", "digestalg"):
        if referrer_attributes.get(name, {}).get("matchcase") is not True:
            errors.append(f"referrers.{name}: exact case must be preserved")
    referrer_format = referrer_attributes.get("format", {})
    if (
        referrer_format.get("enum") != ["Opaque/1.0"]
        or referrer_format.get("strict") is not True
        or referrer_format.get("default") != "Opaque/1.0"
    ):
        errors.append("referrers.format: only Opaque/1.0 is conforming")
    referrer_digest_algorithm = referrer_attributes.get("digestalg", {})
    if referrer_digest_algorithm.get("enum") != ["Sha256", "Sha384", "Sha512"]:
        errors.append(
            "referrers.digestalg: must support exactly Sha256, Sha384 and Sha512"
        )
    if referrer_digest_algorithm.get("strict") is not True:
        errors.append("referrers.digestalg: unsupported algorithms must be rejected")
    referrer_description = referrers.get("description", "").lower()
    if (
        "separate resource" not in referrer_description
        or "exactly one immutable version" not in referrer_description
        or "default version" not in referrer_description
    ):
        errors.append(
            "referrers: must isolate each immutable attestation from package defaults"
        )
    for name in ("tags", "referrers"):
        if name in referrers.get("metaattributes", {}):
            errors.append(f"referrers.meta.{name}: mutable indexes are not allowed")

    if "dictionary" in groups.get("conceptdictionaries", {}).get("attributes", {}):
        errors.append("conceptdictionaries: obsolete duplicate dictionary identity remains")

    return errors


def validate_algorithms() -> list[str]:
    errors: list[str] = []

    for source, expected in IDENTIFIER_EXAMPLES.items():
        actual = symbolic_identifier(source)
        if actual != expected:
            errors.append(f"identifier example mismatch for {source}: {actual}")

    malformed_source = "http://["
    malformed_identifier = symbolic_identifier(malformed_source)
    if not malformed_identifier.startswith("http."):
        errors.append("malformed URI-like source did not use the free-form fallback")
    if not malformed_identifier.endswith(
        hashlib.sha256(malformed_source.encode("utf-8")).hexdigest()
    ):
        errors.append("malformed URI-like source did not retain its exact hash identity")

    invalid_authorities = {
        "https://example.com:bad/path": "https.example.com-bad.path",
        "https://example.com:65536/path": "https.example.com-65536.path",
        "https://[2001:db8::zz]:443/path": "https.2001-db8-zz-443.path",
    }
    for source, expected_prefix in invalid_authorities.items():
        if readable_prefix(source) != expected_prefix:
            errors.append(
                f"invalid URI authority did not use free-form fallback: {source}"
            )

    valid_authorities = {
        "https://example.com/path": "com.example.path",
        "https://example.com:443/path": "com.example.443.path",
        "https://[2001:db8::1]:8443/path": "2001-db8-1.8443.path",
    }
    for source, expected_prefix in valid_authorities.items():
        if readable_prefix(source) != expected_prefix:
            errors.append(f"valid URI authority was not normalized correctly: {source}")

    whitespace_sources = (
        " https://example.com/path",
        "https://example.com/path ",
    )
    for source in whitespace_sources:
        if readable_prefix(source) != "https.example.com.path":
            errors.append(
                f"whitespace-altered URI did not use free-form fallback: {source!r}"
            )
        if not symbolic_identifier(source).endswith(
            hashlib.sha256(source.encode("utf-8")).hexdigest()
        ):
            errors.append(
                f"whitespace-altered source did not retain exact identity: {source!r}"
            )

    first, second = COLLIDING_PREFIX_SOURCES
    if readable_prefix(first) != readable_prefix(second):
        errors.append("collision regression sources no longer share a readable prefix")
    singleton = {first: symbolic_identifier(first)}
    forward = {source: symbolic_identifier(source) for source in (first, second)}
    reverse = {source: symbolic_identifier(source) for source in (second, first)}
    if singleton[first] != forward[first] or forward != reverse:
        errors.append("identifier depends on sibling set or insertion order")
    if forward[first].casefold() == forward[second].casefold():
        errors.append("normalized-prefix collision was not disambiguated")

    group_source = "https://fabrikam.com/aas/pump/SN-001"
    resource_source = "https://contoso.com/ids/sm/nameplate"
    expected_xid = (
        f"/shells/{symbolic_identifier(group_source)}"
        f"/submodels/{symbolic_identifier(resource_source)}"
    )
    if resource_xid("shells", group_source, "submodels", resource_source) != expected_xid:
        errors.append("full xid is not a pure function of the source-identity tuple")

    versions: dict[str, dict[str, str]] = {}
    tags: list[dict[str, str]] = []
    retained: dict[str, dict[str, str]] | None = None
    for index, example in enumerate(OCI_EXAMPLES):
        blob = base64.b64decode(example["packagebase64"])
        version_id = apply_oci_tag(
            versions,
            tags,
            OCI_TAG_EXAMPLES[0],
            example["manifestdigest"],
            blob,
            "Sha256",
            example["digest"],
        )
        if version_id != symbolic_identifier(example["manifestdigest"]):
            errors.append("OCI Version id is not derived from manifest identity")
        if index == 0:
            retained = copy.deepcopy(versions)

    if len(versions) != 2:
        errors.append("OCI tag movement did not create two immutable Versions")
    moved_alias = next(
        (entry for entry in tags if entry.get("tag") == OCI_TAG_EXAMPLES[0]),
        None,
    )
    if moved_alias is None or moved_alias.get("manifestdigest") != OCI_EXAMPLES[1]["manifestdigest"]:
        errors.append("OCI tag did not move to the second manifest")
    if retained:
        first_version_id = symbolic_identifier(OCI_EXAMPLES[0]["manifestdigest"])
        if versions.get(first_version_id) != retained.get(first_version_id):
            errors.append("OCI tag movement mutated the retained first Version")

    for tag in OCI_TAG_EXAMPLES[1:]:
        apply_oci_tag(
            versions,
            tags,
            tag,
            OCI_EXAMPLES[1]["manifestdigest"],
            base64.b64decode(OCI_EXAMPLES[1]["packagebase64"]),
            "Sha256",
            OCI_EXAMPLES[1]["digest"],
        )
    if [entry.get("tag") for entry in tags] != list(OCI_TAG_EXAMPLES):
        errors.append("OCI raw tags were not preserved losslessly in array entries")

    algorithm_blob = b"AASX package bytes for digest algorithm coverage"
    for index, algorithm in enumerate(("Sha256", "Sha384", "Sha512"), start=1):
        algorithm_versions: dict[str, dict[str, str]] = {}
        manifest_digest = f"sha256:{index:064x}"
        version_id = apply_oci_tag(
            algorithm_versions,
            [],
            algorithm,
            manifest_digest,
            algorithm_blob,
            algorithm,
            digest_bytes(algorithm_blob, algorithm),
        )
        if algorithm_versions[version_id].get("digestalg") != algorithm:
            errors.append(f"OCI package digest algorithm was not retained: {algorithm}")
    try:
        apply_oci_tag(
            {},
            [],
            "unsupported",
            OCI_EXAMPLES[0]["manifestdigest"],
            b"package",
            "Blake3",
            "not-used",
        )
    except ValueError:
        pass
    else:
        errors.append("unsupported OCI package digest algorithm was accepted")
    for algorithm in ("sha256", "SHA256", "sha384", "sha512"):
        try:
            digest_bytes(b"package", algorithm)
        except ValueError:
            continue
        errors.append(f"incorrectly cased digest algorithm was accepted: {algorithm}")

    package_default_before = next(reversed(versions))
    package_resource: dict[str, object] = {
        "defaultversionid": package_default_before,
        "versions": versions,
    }
    package_resource_before = copy.deepcopy(package_resource)
    referrer_resources: dict[str, dict[str, object]] = {}
    referrer_id = add_oci_referrer_resource(
        package_resource["versions"],
        referrer_resources,
        OCI_REFERRER_EXAMPLE["subjectmanifestdigest"],
        OCI_REFERRER_EXAMPLE["manifestdigest"],
        base64.b64decode(OCI_REFERRER_EXAMPLE["attestationbase64"]),
        OCI_REFERRER_EXAMPLE["digestalg"],
        OCI_REFERRER_EXAMPLE["digest"],
        OCI_REFERRER_EXAMPLE["artifacttype"],
        OCI_REFERRER_EXAMPLE["signer"],
    )
    if package_resource != package_resource_before:
        errors.append(
            "later OCI referrer arrival mutated the package Resource or its default"
        )
    referrer = referrer_resources.get(referrer_id, {})
    referrer_versions = referrer.get("versions", {})
    if (
        referrer.get("defaultversionid") != referrer_id
        or not isinstance(referrer_versions, dict)
        or list(referrer_versions) != [referrer_id]
    ):
        errors.append("OCI attestation was not isolated in a one-Version referrer Resource")

    local_resource: dict[str, object] = {
        "versions": copy.deepcopy(versions),
    }
    local_resource_before = copy.deepcopy(local_resource)
    try:
        convert_resource_to_xref(local_resource, "/shells/remote")
    except ValueError:
        pass
    else:
        errors.append("Resource with retained local history converted to xref")
    if local_resource != local_resource_before:
        errors.append("failed xref conversion mutated retained local history")
    descriptor: dict[str, object] = {"versions": {}}
    convert_resource_to_xref(descriptor, "/shells/remote")
    if descriptor.get("xref") != "/shells/remote":
        errors.append("xref descriptor could not be established before local history")

    return errors


def validate_documents(registry_spec: str, package_spec: str) -> list[str]:
    errors: list[str] = []
    registry_flat = re.sub(r"\s+", " ", registry_spec)
    package_flat = re.sub(r"\s+", " ", package_spec)

    required_registry_phrases = (
        "suffix is ALWAYS present",
        "collision lookup or insertion order",
        "MUST NOT reject a source identity solely because URI parsing fails",
        "validate the untouched source before using a URI library's parsed result",
        "including leading or trailing whitespace",
        "MUST be retained without expiration",
        "MUST NOT prune or delete a Version",
        "it MUST NOT convert",
        "conversion request MUST fail without changing the Resource",
        "`digestalg` is REQUIRED when `digest` is present and is case-sensitive",
        "required `meta.historypolicy` value `retain-all`",
        "reserved system-managed `resourceattributes` object",
        '"meta": { "historypolicy": "retain-all" }',
        "`templatenamespace` is REQUIRED",
        "`dictionaryidentifier` is REQUIRED",
    )
    for phrase in required_registry_phrases:
        if phrase not in registry_flat:
            errors.append(f"xRegistry-AAS.md: missing normative phrase {phrase!r}")

    forbidden_registry_phrases = (
        "first eight lower-case hexadecimal",
        "where the result would collide",
        "/shells/com.fabrikam.type.pump ",
        "registry MAY convert between the two",
    )
    for phrase in forbidden_registry_phrases:
        if phrase.lower() in registry_flat.lower():
            errors.append(f"xRegistry-AAS.md: obsolete conditional-id text remains: {phrase!r}")
    if re.search(
        r'```json\s*\{\s*"historypolicy"\s*:',
        registry_spec,
    ):
        errors.append(
            "xRegistry-AAS.md: Resource history policy example is outside meta"
        )

    for source, identifier in IDENTIFIER_EXAMPLES.items():
        if source not in registry_spec or identifier not in registry_spec:
            errors.append(f"xRegistry-AAS.md: missing identifier example for {source}")
    malformed_source = "http://["
    malformed_identifier = symbolic_identifier(malformed_source)
    if malformed_source not in registry_spec or malformed_identifier not in registry_spec:
        errors.append("xRegistry-AAS.md: missing malformed source fallback example")

    required_package_phrases = (
        "`storeidentifier` is REQUIRED",
        "used as a `versionid`",
        "`meta.tags` is an array of entries carrying a raw `tag`",
        "`metaattributes` and serialized in the Resource `meta` object",
        "reserved system-managed `resourceattributes` object",
        '"meta": { "tags": [',
        "MUST NOT use the raw tag as a map or object key",
        "The manifest MUST contain exactly one package layer",
        "MUST compute the package-blob digest with the algorithm named by the descriptor",
        "`digestalg` is case-sensitive",
        "exact case-sensitive `digestalg`",
        "represented by its own immutable `referrer` Resource",
        "MUST NOT be represented as a Version of the `package` Resource",
        "A `referrer` Resource MUST contain exactly one immutable Version",
        "Adding the referrer MUST NOT modify that package Resource's Version collection",
        "because referrer Versions belong to a different Resource collection",
        "verify the returned package bytes against `digest`",
    )
    for phrase in required_package_phrases:
        if phrase not in package_flat:
            errors.append(f"xRegistry-AAS-Packages.md: missing normative phrase {phrase!r}")

    forbidden_package_phrases = (
        "| Version | one tag |",
        "| `digest` | the manifest digest |",
        "A `versionid` is the tag",
        "Resource-level `tags` map",
        "Resource-level `tags` array",
        "Resource-level `referrers` array",
        "Resource-level `historypolicy`",
        "`tags[\"",
        "entries in the `attestations` array",
        "`meta.referrers`",
        "own immutable `package` Version",
    )
    for phrase in forbidden_package_phrases:
        if phrase.lower() in package_flat.lower():
            errors.append(f"xRegistry-AAS-Packages.md: obsolete OCI mapping remains: {phrase!r}")
    if re.search(
        r'```json\s*\{\s*"(?:tags|historypolicy)"\s*:',
        package_spec,
    ):
        errors.append(
            "xRegistry-AAS-Packages.md: Resource domain metadata example is outside meta"
        )

    for example in OCI_EXAMPLES:
        for name in ("manifestdigest", "packagebase64", "digest"):
            if example[name] not in package_spec:
                errors.append(
                    f"xRegistry-AAS-Packages.md: missing OCI example {name}={example[name]}"
                )
        version_id = symbolic_identifier(example["manifestdigest"])
        if version_id not in package_spec:
            errors.append(
                f"xRegistry-AAS-Packages.md: missing derived OCI versionid {version_id}"
            )

    for tag in OCI_TAG_EXAMPLES:
        if tag not in package_spec:
            errors.append(f"xRegistry-AAS-Packages.md: missing raw OCI tag example {tag}")

    for name, value in OCI_REFERRER_EXAMPLE.items():
        if value not in package_spec:
            errors.append(
                f"xRegistry-AAS-Packages.md: missing later-referrer example {name}={value}"
            )
    referrer_id = symbolic_identifier(OCI_REFERRER_EXAMPLE["manifestdigest"])
    if referrer_id not in package_spec:
        errors.append(
            f"xRegistry-AAS-Packages.md: missing derived referrer id {referrer_id}"
        )

    return errors


def validate_repository() -> list[str]:
    with MODEL_PATH.open(encoding="utf-8") as stream:
        model = json.load(stream)
    registry_spec = REGISTRY_SPEC_PATH.read_text(encoding="utf-8")
    package_spec = PACKAGE_SPEC_PATH.read_text(encoding="utf-8")

    errors = validate_model(model)
    errors.extend(validate_algorithms())
    errors.extend(validate_documents(registry_spec, package_spec))
    return errors


def main() -> int:
    errors = validate_repository()
    print(f"xRegistry AAS semantic errors: {len(errors)}")
    for error in errors:
        print(f"  ERR {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
