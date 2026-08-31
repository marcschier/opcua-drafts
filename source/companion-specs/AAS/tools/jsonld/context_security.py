#!/usr/bin/env python3
"""Bounded, default-deny JSON-LD context resolution.

The repository's processors are intentionally offline.  A caller may opt in to
network resolution, but only for explicitly allowlisted HTTPS origins and with
content pins, address checks and bounded redirects.
"""
from __future__ import annotations

import hashlib
import http.client
import ipaddress
import json
import socket
import ssl
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping


class ContextSecurityError(ValueError):
    """A JSON-LD context violates the configured resolution policy."""


@dataclass(frozen=True)
class BundledContext:
    path: Path
    sha256: str | None = None


@dataclass(frozen=True)
class NetworkResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes
    content_type: str = "application/ld+json"


Resolver = Callable[[str, int], tuple[str, ...]]
Transport = Callable[[str, tuple[str, ...], float, int], NetworkResponse]
EgressPolicy = Callable[[str, tuple[str, ...]], bool]


def _default_resolver(host: str, port: int) -> tuple[str, ...]:
    addresses = {
        result[4][0]
        for result in socket.getaddrinfo(
            host, port, type=socket.SOCK_STREAM)
    }
    return tuple(sorted(addresses))


def _default_transport(
        url: str, addresses: tuple[str, ...],
        timeout: float, max_bytes: int) -> NetworkResponse:
    """Fetch over TLS through an already validated IP, preserving host SNI."""
    parsed = urllib.parse.urlsplit(url)
    port = parsed.port or 443
    target = parsed.path or "/"
    if parsed.query:
        target += "?" + parsed.query
    last_error = None
    for address in addresses:
        connection = None
        raw_socket = None
        try:
            raw_socket = socket.create_connection(
                (address, port), timeout=timeout)
            tls_socket = ssl.create_default_context().wrap_socket(
                raw_socket, server_hostname=parsed.hostname)
            raw_socket = None
            connection = http.client.HTTPConnection(
                parsed.hostname, port, timeout=timeout)
            connection.sock = tls_socket
            connection.request(
                "GET",
                target,
                headers={
                    "Accept": "application/ld+json, application/json",
                    "Host": parsed.netloc,
                },
            )
            response = connection.getresponse()
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise ContextSecurityError(
                    f"context response exceeds {max_bytes} bytes")
            return NetworkResponse(
                status=response.status,
                headers=dict(response.getheaders()),
                body=body,
                content_type=response.headers.get_content_type(),
            )
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            last_error = exc
        finally:
            if raw_socket is not None:
                raw_socket.close()
            if connection is not None:
                connection.close()
    raise ContextSecurityError(
        f"context connection failed for validated addresses: {url}"
    ) from last_error


def _canonical_origin(url: str) -> str:
    if any(ord(character) <= 0x20 or ord(character) == 0x7F for character in url):
        raise ContextSecurityError(
            "context URLs must not contain whitespace or control characters")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ContextSecurityError(
            f"network contexts require an absolute HTTPS URL: {url}")
    if parsed.username is not None or parsed.password is not None:
        raise ContextSecurityError(
            "context URLs must not contain ambient credentials")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ContextSecurityError(
            f"context URL has an invalid authority: {url}") from exc
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    return f"https://{host}" + (f":{port}" if port not in (None, 443) else "")


SHARED_IPV4 = ipaddress.ip_network("100.64.0.0/10")
SITE_LOCAL_IPV6 = ipaddress.ip_network("fec0::/10")
IPV4_COMPATIBLE = ipaddress.ip_network("::/96")
NAT64_WELL_KNOWN = ipaddress.ip_network("64:ff9b::/96")
NAT64_LOCAL_USE = ipaddress.ip_network("64:ff9b:1::/48")


def _parse_address(address: str):
    try:
        return ipaddress.ip_address(address)
    except ValueError as exc:
        raise ContextSecurityError(
            f"DNS returned an invalid IP address: {address}") from exc


def _in_network(value, network) -> bool:
    return value.version == network.version and value in network


def _trusted_address(value, trusted_networks) -> bool:
    return any(_in_network(value, network) for network in trusted_networks)


def _embedded_ipv4_addresses(value) -> tuple[ipaddress.IPv4Address, ...]:
    if not isinstance(value, ipaddress.IPv6Address):
        return ()
    embedded = []

    if value.ipv4_mapped is not None:
        embedded.append(value.ipv4_mapped)
    elif _in_network(value, IPV4_COMPATIBLE) and int(value) > 1:
        embedded.append(ipaddress.IPv4Address(value.packed[-4:]))

    if _in_network(value, NAT64_WELL_KNOWN):
        embedded.append(ipaddress.IPv4Address(value.packed[-4:]))
    if value.sixtofour is not None:
        embedded.append(value.sixtofour)
    if value.teredo is not None:
        embedded.extend(value.teredo)

    # ISATAP interface identifiers embed IPv4 after 0000:5efe or 0200:5efe.
    if value.packed[8:12] in (b"\x00\x00\x5e\xfe", b"\x02\x00\x5e\xfe"):
        embedded.append(ipaddress.IPv4Address(value.packed[-4:]))

    return tuple(dict.fromkeys(embedded))


def _non_global_or_prohibited(value) -> bool:
    return any((
        not value.is_global,
        value.is_loopback,
        value.is_link_local,
        value.is_private,
        value.is_multicast,
        value.is_reserved,
        value.is_unspecified,
        getattr(value, "is_site_local", False),
        _in_network(value, SHARED_IPV4),
        _in_network(value, SITE_LOCAL_IPV6),
        _in_network(value, NAT64_LOCAL_USE),
    ))


def _blocked_address(value, trusted_networks) -> bool:
    if _trusted_address(value, trusted_networks):
        return False
    forms = (
        (value.ipv4_mapped,)
        if isinstance(value, ipaddress.IPv6Address)
        and value.ipv4_mapped is not None
        else (value, *_embedded_ipv4_addresses(value))
    )
    return any(
        _non_global_or_prohibited(form)
        and not _trusted_address(form, trusted_networks)
        for form in forms
    )


def _connection_address(value):
    if isinstance(value, ipaddress.IPv6Address) and value.ipv4_mapped is not None:
        return value.ipv4_mapped
    return value


def _validate_sha256(value: str, label: str) -> None:
    if (
            len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)):
        raise ValueError(f"{label} must be a lowercase SHA-256 hexadecimal digest")


@dataclass(frozen=True)
class ContextPolicy:
    bundled: Mapping[str, BundledContext] = field(default_factory=dict)
    network_enabled: bool = False
    allowlisted_origins: frozenset[str] = frozenset()
    network_sha256: Mapping[str, str] = field(default_factory=dict)
    require_network_pins: bool = True
    trusted_networks: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = ()
    max_contexts: int = 32
    max_context_bytes: int = 1_048_576
    max_context_depth: int = 8
    max_redirects: int = 3
    max_response_bytes: int = 524_288
    timeout_seconds: float = 10.0
    resolver: Resolver = _default_resolver
    transport: Transport = _default_transport
    egress_policy: EgressPolicy | None = None

    def __post_init__(self):
        canonical = frozenset(
            _canonical_origin(origin) for origin in self.allowlisted_origins)
        object.__setattr__(self, "allowlisted_origins", canonical)
        trusted = tuple(
            ipaddress.ip_network(network, strict=False)
            if isinstance(network, str) else network
            for network in self.trusted_networks
        )
        object.__setattr__(self, "trusted_networks", trusted)
        for name, value in (
                ("max_contexts", self.max_contexts),
                ("max_context_bytes", self.max_context_bytes),
                ("max_context_depth", self.max_context_depth),
                ("max_response_bytes", self.max_response_bytes)):
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.max_redirects < 0:
            raise ValueError("max_redirects must not be negative")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        for url, digest in self.network_sha256.items():
            _validate_sha256(digest, f"network context pin for {url}")
        for url, bundled in self.bundled.items():
            if bundled.sha256 is not None:
                _validate_sha256(
                    bundled.sha256, f"bundled context pin for {url}")

    def loader(self, document=None, *, base: str | None = None):
        loader = SecureContextLoader(self)
        if document is not None:
            loader.prepare(document, base=base)
        return loader


class SecureContextLoader:
    """A per-processing-operation PyLD document loader."""

    def __init__(self, policy: ContextPolicy):
        self.policy = policy
        self.context_count = 0
        self.context_bytes = 0
        self._documents: set[str] = set()
        self._edges: dict[str, set[str]] = {}
        self._cache: dict[str, dict] = {}

    def prepare(self, document, *, base: str | None = None) -> None:
        self._inspect_document(document, base or "urn:jsonld:input", "<input>", 0)

    def __call__(self, url: str, options=None) -> dict:
        if url in self._cache:
            return self._cache[url]
        bundled = self.policy.bundled.get(url)
        if bundled is not None:
            raw = bundled.path.read_bytes()
            if len(raw) > self.policy.max_response_bytes:
                raise ContextSecurityError(
                    f"bundled context exceeds {self.policy.max_response_bytes} bytes: "
                    f"{bundled.path}")
            if bundled.sha256 is not None:
                actual = hashlib.sha256(raw).hexdigest()
                if actual != bundled.sha256:
                    raise ContextSecurityError(
                        f"bundled context hash mismatch for {bundled.path}: "
                        f"expected {bundled.sha256}, got {actual}")
            document = self._parse_json(raw, str(bundled.path))
            result = self._loader_result(
                url, document, "application/ld+json")
        else:
            result = self._load_network(url)
            document = result["document"]
        self._inspect_document(document, url, url, 0)
        self._cache[url] = result
        return result

    @staticmethod
    def _loader_result(url: str, document, content_type: str) -> dict:
        return {
            "contextUrl": None,
            "documentUrl": url,
            "document": document,
            "contentType": content_type,
        }

    @staticmethod
    def _parse_json(raw: bytes, label: str):
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ContextSecurityError(
                f"context is not UTF-8 JSON: {label}") from exc

    def _load_network(self, url: str) -> dict:
        if not self.policy.network_enabled:
            raise ContextSecurityError(
                f"network JSON-LD context loading is disabled: {url}")
        origin = _canonical_origin(url)
        if origin not in self.policy.allowlisted_origins:
            raise ContextSecurityError(
                f"JSON-LD context origin is not allowlisted: {origin}")
        expected_hash = self.policy.network_sha256.get(url)
        if self.policy.require_network_pins and expected_hash is None:
            raise ContextSecurityError(
                f"network JSON-LD context is not content-hash pinned: {url}")

        current = url
        for redirects in range(self.policy.max_redirects + 1):
            addresses = self._validate_network_target(current)
            response = self.policy.transport(
                current, addresses, self.policy.timeout_seconds,
                self.policy.max_response_bytes)
            if response.status in {301, 302, 303, 307, 308}:
                location = next(
                    (value for key, value in response.headers.items()
                     if key.lower() == "location"),
                    None,
                )
                if not location:
                    raise ContextSecurityError(
                        f"context redirect has no Location header: {current}")
                if redirects == self.policy.max_redirects:
                    raise ContextSecurityError(
                        f"context redirect limit exceeded: {url}")
                current = urllib.parse.urljoin(current, location)
                continue
            if response.status < 200 or response.status >= 300:
                raise ContextSecurityError(
                    f"context request returned HTTP {response.status}: {current}")
            if len(response.body) > self.policy.max_response_bytes:
                raise ContextSecurityError(
                    f"context response exceeds "
                    f"{self.policy.max_response_bytes} bytes")
            if expected_hash is not None:
                actual = hashlib.sha256(response.body).hexdigest()
                if actual != expected_hash:
                    raise ContextSecurityError(
                        f"context hash mismatch for {url}: "
                        f"expected {expected_hash}, got {actual}")
            document = self._parse_json(response.body, current)
            return self._loader_result(
                current, document, response.content_type)
        raise AssertionError("unreachable redirect state")

    def _validate_network_target(self, url: str) -> tuple[str, ...]:
        origin = _canonical_origin(url)
        if origin not in self.policy.allowlisted_origins:
            raise ContextSecurityError(
                f"redirected context origin is not allowlisted: {origin}")
        parsed = urllib.parse.urlsplit(url)
        port = parsed.port or 443
        resolved = self.policy.resolver(parsed.hostname, port)
        if not resolved:
            raise ContextSecurityError(
                f"context host resolved to no addresses: {parsed.hostname}")
        parsed_addresses = tuple(
            dict.fromkeys(_parse_address(address) for address in resolved))
        blocked = [
            address for address in parsed_addresses
            if _blocked_address(address, self.policy.trusted_networks)
        ]
        if blocked:
            raise ContextSecurityError(
                "context host resolves to a non-global or prohibited address, "
                f"including a mapped or embedded target: {blocked[0]}")
        addresses = tuple(dict.fromkeys(
            str(_connection_address(address))
            for address in parsed_addresses
        ))
        if (
                self.policy.egress_policy is not None
                and not self.policy.egress_policy(url, addresses)):
            raise ContextSecurityError(
                f"context request was denied by egress policy: {url}")
        return addresses

    def _inspect_document(
            self, document, base: str, document_key: str, active_depth: int) -> None:
        if document_key in self._documents:
            return
        self._documents.add(document_key)

        def walk(node, depth):
            if isinstance(node, list):
                for value in node:
                    walk(value, depth)
                return
            if not isinstance(node, dict):
                return
            child_depth = depth
            if "@context" in node:
                child_depth = depth + 1
                self._inspect_context(
                    node["@context"], base, document_key, child_depth)
            for key, value in node.items():
                if key != "@context":
                    walk(value, child_depth)

        walk(document, active_depth)

    def _inspect_context(
            self, context, base: str, document_key: str, depth: int) -> None:
        if depth > self.policy.max_context_depth:
            raise ContextSecurityError(
                f"JSON-LD context nesting exceeds "
                f"{self.policy.max_context_depth}")
        entries = context if isinstance(context, list) else [context]
        for entry in entries:
            self.context_count += 1
            if self.context_count > self.policy.max_contexts:
                raise ContextSecurityError(
                    f"JSON-LD context count exceeds "
                    f"{self.policy.max_contexts}")
            encoded = json.dumps(
                entry, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            self.context_bytes += len(encoded)
            if self.context_bytes > self.policy.max_context_bytes:
                raise ContextSecurityError(
                    f"JSON-LD context bytes exceed "
                    f"{self.policy.max_context_bytes}")
            if isinstance(entry, str):
                self._add_edge(
                    document_key, urllib.parse.urljoin(base, entry))
            elif isinstance(entry, dict):
                imported = entry.get("@import")
                if imported is not None:
                    if not isinstance(imported, str):
                        raise ContextSecurityError(
                            "JSON-LD @import must be an IRI string")
                    self._add_edge(
                        document_key, urllib.parse.urljoin(base, imported))
                self._inspect_scoped_contexts(
                    entry, base, document_key, depth)
            elif entry is not None:
                raise ContextSecurityError(
                    "JSON-LD @context entries must be objects, IRIs or null")

    def _inspect_scoped_contexts(
            self, node, base: str, document_key: str, depth: int) -> None:
        if isinstance(node, list):
            for value in node:
                self._inspect_scoped_contexts(
                    value, base, document_key, depth)
            return
        if not isinstance(node, dict):
            return
        if "@context" in node:
            self._inspect_context(
                node["@context"], base, document_key, depth + 1)
        for key, value in node.items():
            if key != "@context":
                self._inspect_scoped_contexts(
                    value, base, document_key, depth)

    def _add_edge(self, source: str, target: str) -> None:
        self._edges.setdefault(source, set()).add(target)
        self._check_reference_depth()

    def _check_reference_depth(self) -> None:
        def visit(node: str, stack: tuple[str, ...]) -> int:
            if node in stack:
                raise ContextSecurityError(
                    f"JSON-LD context reference cycle: {node}")
            children = self._edges.get(node, ())
            if not children:
                return 0
            return 1 + max(
                visit(child, stack + (node,)) for child in children)

        for root in self._edges:
            if visit(root, ()) > self.policy.max_context_depth:
                raise ContextSecurityError(
                    f"JSON-LD context reference depth exceeds "
                    f"{self.policy.max_context_depth}")


DEFAULT_POLICY = ContextPolicy()


def default_deny_loader(document=None, *, base: str | None = None):
    """Return a fresh offline loader prepared for one JSON-LD operation."""
    return DEFAULT_POLICY.loader(document, base=base)
