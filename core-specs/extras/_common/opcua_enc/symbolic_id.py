"""Symbolic xRegistry entity identifiers — the executable form of *OPC UA — xRegistry* §6.9.

An xRegistry group or resource identifier is derived from the entity's **source
identity** — the domain-defined string that names *what* the entity is: an OPC UA
namespace URI, an authored USD asset identifier, a W3C Thing identifier, a DataType
BrowseName. It is **never** derived from a resource document or a digest of one, so it
is invariant across the entity's versions.

:func:`symbolic_id` turns a source identity into a dot-separated, reverse-DNS-flavoured
token such as ``org.contoso.assets.pump``. The output alphabet is ``A-Z a-z 0-9 _ . -``,
a strict subset of what xRegistry core permits in a ``<SINGULAR>id`` (RFC 3986
*unreserved* plus ``:`` and ``@``), chosen so one identifier is simultaneously safe in a
URL, on a command line, and as a file name in the static-file-server representation.

The construction is **one-way**: distinct source identities can normalize to the same
token, which is what the disambiguator resolves. A consumer holding a source identity
computes the identifier in closed form and confirms it against the entity's
source-identity attribute; a consumer holding only an identifier resolves the entity by
matching that attribute. Nothing inverts the transform.

Run this module directly to execute its self-test.
"""
from __future__ import annotations

import hashlib
import re
import urllib.parse

# xRegistry core v1.0-rc3 `<SINGULAR>id`: RFC 3986 unreserved plus ':' and '@', starting
# with ALPHA / DIGIT / '_', 1..128 characters. Every symbolic identifier satisfies it.
XREGISTRY_ID_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9\-._~:@]{0,127}$")

#: The alphabet a symbolic identifier is normalized into (a subset of the above).
_ALLOWED = re.compile(r"[^A-Za-z0-9_.-]+")

MAX_LEN = 128
DISAMBIGUATOR_LEN = 8
#: Longest prefix that still leaves room for ``"." + 8 hex characters``.
_TRIMMED_LEN = MAX_LEN - DISAMBIGUATOR_LEN - 1


def is_valid_xregistry_id(value: str) -> bool:
    """True when ``value`` is a legal xRegistry ``<SINGULAR>id``."""
    return bool(value) and bool(XREGISTRY_ID_RE.match(value))


def disambiguator(source_identity: str) -> str:
    """The first 8 hex characters of SHA-256 over the *exact* source identity.

    A function of the identity, not of any document, so it does not change when a new
    version is written.
    """
    return hashlib.sha256(source_identity.encode("utf-8")).hexdigest()[:DISAMBIGUATOR_LEN]


def split_identity(source_identity: str) -> tuple[list[str], list[str]]:
    """Step 1-3: split a source identity into reversed-authority and path labels."""
    text = source_identity.strip()
    if text.lower().startswith("urn:"):
        # A URN has no authority; the path is the URN split on ':', so the leading
        # 'urn' survives as the first label and a URN never aliases a bare path.
        return [], [p for p in text.split(":") if p]

    parts = urllib.parse.urlsplit(text)
    if parts.scheme and parts.netloc:
        netloc = parts.netloc.rsplit("@", 1)[-1]          # discard userinfo
        host, port = netloc, ""
        if not netloc.endswith("]") and ":" in netloc:     # not an IPv6 literal
            head, _, tail = netloc.rpartition(":")
            if tail.isdigit():
                host, port = head, tail
        authority = [lbl for lbl in reversed(host.split(".")) if lbl]
        if port:
            authority.append(port)
        path = parts.path
    else:
        authority, path = [], text

    segments = [urllib.parse.unquote(seg) for seg in path.split("/")]
    return authority, [seg for seg in segments if seg]


def normalize_label(label: str) -> str:
    """Step 4: fold one label into the output alphabet, preserving letter case."""
    out = _ALLOWED.sub("-", label)
    out = re.sub(r"-{2,}", "-", out)
    out = re.sub(r"\.{2,}", ".", out)
    return out.strip("-.")


def symbolic_id(source_identity: str, existing: object = None) -> str:
    """Construct the symbolic identifier of ``source_identity``.

    ``existing`` is an optional iterable of sibling identifiers already present in the
    same collection; a case-insensitive collision with one of them appends the
    disambiguator, as xRegistry requires ids to be unique case-insensitively within
    their parent.
    """
    authority, path = split_identity(source_identity)
    labels = [n for n in (normalize_label(lbl) for lbl in authority + path) if n]
    candidate = ".".join(labels)

    truncated = False
    if len(candidate) > MAX_LEN:
        truncated = True
        while labels and len(".".join(labels)) > _TRIMMED_LEN:
            labels.pop()
        candidate = ".".join(labels)
        if len(candidate) > _TRIMMED_LEN:
            candidate = candidate[:_TRIMMED_LEN].rstrip("-.")

    if not candidate:
        candidate = "_"
    # Step 4 strips leading '-' and '.' from every label, so a surviving candidate
    # always starts with a letter, a digit or '_' - the xRegistry start-character rule.

    taken = {str(e).lower() for e in (existing or ())}
    if truncated or candidate.lower() in taken:
        head = candidate if len(candidate) <= _TRIMMED_LEN else candidate[:_TRIMMED_LEN]
        candidate = f"{head.rstrip('-.')}.{disambiguator(source_identity)}"

    return candidate


_SELF_TEST = [
    # (source identity, expected symbolic identifier)
    ("http://contoso.org/UA/Pumps/", "org.contoso.UA.Pumps"),
    ("http://opcfoundation.org/UA/", "org.opcfoundation.UA"),
    ("https://contoso.org:8443/UA/Pumps", "org.contoso.8443.UA.Pumps"),
    ("https://user:pw@contoso.org/things/pump-01", "org.contoso.things.pump-01"),
    ("urn:dev:ops:32473-pump-01", "urn.dev.ops.32473-pump-01"),
    ("pump.usda", "pump.usda"),
    ("./pump.usda", "pump.usda"),
    ("textures/albedo.png", "textures.albedo.png"),
    ("pkg.usdz[tex/a.png]", "pkg.usdz-tex.a.png"),
    ("fabrikam.plant-01", "fabrikam.plant-01"),
    ("BoundItemDataType", "BoundItemDataType"),
    ("http://opcfoundation.org/UA/Pumps/#Section", "org.opcfoundation.UA.Pumps"),
    ("textures/%C3%A4lbedo.png", "textures.lbedo.png"),
    ("", "_"),
    ("///", "_"),
    ("-leading.", "leading"),
    ("...", "_"),
]


def _self_test() -> None:
    for source, expected in _SELF_TEST:
        got = symbolic_id(source)
        assert got == expected, f"{source!r}: expected {expected!r}, got {got!r}"
        assert is_valid_xregistry_id(got), f"{source!r}: {got!r} is not a legal xRegistry id"

    # A collision appends the identity digest, and only to the loser.
    first = symbolic_id("a/b")
    second = symbolic_id("a.b", existing=[first])
    assert first == "a.b" and second == f"a.b.{disambiguator('a.b')}", (first, second)

    # Case-insensitive collision, because xRegistry ids are unique case-insensitively.
    assert symbolic_id("A.B", existing=["a.b"]) == f"A.B.{disambiguator('A.B')}"

    # The disambiguator is a function of the identity, not of any document.
    assert disambiguator("a.b") == disambiguator("a.b")

    # Over-long identities are truncated to a legal id and disambiguated.
    long_id = "http://contoso.org/" + "/".join(f"segment{i:03d}" for i in range(40))
    got = symbolic_id(long_id)
    assert is_valid_xregistry_id(got) and len(got) <= MAX_LEN, (len(got), got)
    assert got.endswith("." + disambiguator(long_id)), got

    # A truncated identity is disambiguated even with no sibling to collide with,
    # because truncation itself destroys uniqueness.
    assert symbolic_id(long_id) == symbolic_id(long_id)

    print(f"symbolic_id OK - {len(_SELF_TEST)} vectors + collision, case, length checks")


if __name__ == "__main__":
    _self_test()
