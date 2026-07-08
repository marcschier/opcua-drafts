"""Deterministic OPC UA NamespaceUri -> Avro namespace mapping.

Reference implementation of *OPC UA — Apache Avro DataEncoding* §6.5. A
NamespaceUri is converted to an Avro namespace by reverse-DNS of the authority,
appended lower-cased path segments, per-part escaping to ``[a-z0-9_]`` and a
reserved final ``avro`` part. Distinct URIs that collide after conversion are
disambiguated with the deterministic counter rule (``_2``, ``_3`` … in ordinal
URI order).

The base OPC UA namespace ``http://opcfoundation.org/UA/`` keeps its fixed Avro
namespace ``org.opcfoundation.ua.avro`` (which the general function also yields).
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from urllib.parse import urlsplit

BASE_URI = "http://opcfoundation.org/UA/"
BASE_NS = "org.opcfoundation.ua.avro"
RESERVED_SUFFIX = "avro"


def _legal_part(part: str) -> str:
    """Escape one URI segment into a single legal Avro name part."""
    s = re.sub(r"[^a-z0-9_]", "_", part.lower())
    if not s or s[0].isdigit():
        s = "_" + s
    return s


def avro_namespace_from_uri(uri: str) -> str:
    """Map a single NamespaceUri to an Avro namespace (§6.5 steps 1–5)."""
    if uri.rstrip("/") == BASE_URI.rstrip("/"):
        return BASE_NS
    parts: list[str] = []
    split = urlsplit(uri)
    if split.scheme and split.netloc:
        host = split.netloc
        if "@" in host:  # drop userinfo
            host = host.split("@", 1)[1]
        if ":" in host:  # drop port
            host = host.split(":", 1)[0]
        host = host.rstrip(".")
        labels = [label for label in host.split(".") if label]
        parts.extend(reversed(labels))
        parts.extend(seg for seg in split.path.split("/") if seg)
    else:
        rest = uri.split(":", 1)[1] if ":" in uri else uri
        for chunk in rest.split(":"):
            parts.extend(seg for seg in chunk.split("/") if seg)
    legal = [_legal_part(p) for p in parts if p]
    legal.append(RESERVED_SUFFIX)
    return ".".join(legal)


def _suffix_last_part(ns: str, ordinal: int) -> str:
    """Append an ordinal to the last name part, before the reserved suffix."""
    parts = ns.split(".")
    if len(parts) >= 2 and parts[-1] == RESERVED_SUFFIX:
        parts[-2] = f"{parts[-2]}_{ordinal}"
    else:  # degenerate URI that produced only the reserved part
        parts.insert(0, f"_{ordinal}")
    return ".".join(parts)


def assign_avro_namespaces(uris: Iterable[str]) -> dict[str, str]:
    """Map a scope of NamespaceUris to distinct Avro namespaces (§6.5).

    Every natural namespace is reserved first, so a disambiguating suffix can
    never coincide with another URI's natural namespace. Colliding URIs are
    ordered by ordinal code-point order; the first keeps the natural namespace,
    later ones advance ``_2``, ``_3`` … past any already-reserved name. The
    result is deterministic for a given input set.
    """
    uris = list(uris)
    natural = {uri: avro_namespace_from_uri(uri) for uri in uris}
    groups: dict[str, list[str]] = {}
    for uri in uris:
        groups.setdefault(natural[uri], []).append(uri)
    occupied = set(groups)  # every natural namespace is taken by its first member
    result: dict[str, str] = {}
    for ns in sorted(groups):
        group = sorted(groups[ns])
        result[group[0]] = ns
        for uri in group[1:]:
            ordinal = 2
            candidate = _suffix_last_part(ns, ordinal)
            while candidate in occupied:
                ordinal += 1
                candidate = _suffix_last_part(ns, ordinal)
            occupied.add(candidate)
            result[uri] = candidate
    return result
