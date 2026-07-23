#!/usr/bin/env python3
"""Deterministic, standard-library validator for the OPC UA WoT Binding draft.

Run from anywhere:  python wot-specs/WoT-Binding/tools/validate_local.py

The validator uses only the Python standard library and performs a fixed,
order-independent set of checks so that a clean checkout always produces the
same result. It verifies, for the wot-specs/WoT-Binding/ folder:

  1. Every JSON and JSON-LD artifact parses.
  2. The JSON-LD context declares the official uav namespace/prefix and contains
     every documented uav term (preserved OPC 10101 terms, the model/platform
     vocabulary, and the preservation-envelope member terms).
  3. Every example declares an @context that binds the uav namespace.
  4. The default native example uses uav:NodeModel profile 1.0 without an
     envelope, and every exceptional uav:nodeSet envelope is internally consistent: encoding
     is base64, the SHA-256 field matches the digest of the decoded bytes, and
     the decoded bytes are a well-formed XML document rooted at UANodeSet.
  5. Every internal relative reference resolves to a file on disk, and the
     required artifacts are all present.
  6. No forbidden vendor prefixes, namespaces, or legacy modelling-language
     names appear in any committed file.
  7. Every `uav:unitProperty` is a canonical RFC 6901 JSON Pointer that resolves,
     within the same document, to a non-empty string value.
  8. Every `uav:containedIn` names an actual composite (matched by `title`) that
     declares `uav:isComposite`; when a local `uav:componentModel` link connects
     the two examples, the composite's `uav:contains` must reciprocally list the
     link's `uav:refName` (containment consistency, Section 7 of the spec).
  9. Every NodeId-valued term (`uav:id`, `uav:hasComponent`, `uav:componentOf`,
     `uav:mapToNodeId`, `uav:mapToType`, a NodeId-valued `uav:refType`, and each
     `?id=` / NodeId link `href`) in an example is a portable OPC 10000-6
     ExpandedNodeId and never the session-local `ns=<index>` form (Section 5.1.1).
 10. Event annotations are consistent: an affordance annotated `@type uav:eventType`
     never sets `uav:isEvent: false` (Section 5.2).
 11. The native projection example has the required root/model/node structure.

Exit code is 0 and the last line is "OK" on success; non-zero with an ERRORS
list otherwise.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CONTEXT = os.path.join(ROOT, "opc-ua-wot-binding.context.jsonld")
SCHEMA = os.path.join(ROOT, "opc-ua-wot-binding.schema.json")
SPEC = os.path.join(ROOT, "OPC-UA-WoT-Binding.md")
README = os.path.join(ROOT, "README.md")
EXAMPLES = os.path.join(ROOT, "examples")

UAV_NS = "http://opcfoundation.org/UA/WoT-Binding/"
UANODESET_LOCALNAME = "UANodeSet"

# Every uav term the specification documents. Each MUST be discoverable in the
# JSON-LD context as a "uav:<term>" key or value.
DOCUMENTED_TERMS = [
    # Preserved OPC 10101 vocabulary.
    "id", "browsePath", "browseName",
    "object", "objectType", "variable", "variableType", "method", "eventType",
    "hasComponent", "componentOf",
    "mapToNodeId", "mapToType", "mapByFieldPath",
    # Preserved OPC 10101 security vocabulary.
    "channelsec", "authentication", "securityMode", "securityPolicy",
    "userIdentityToken", "issueToken",
    # Model and platform vocabulary.
    "isComposite", "isEvent",
    "capability", "componentModel", "reference", "typedReference",
    "refName", "refType",
    "contains", "containedIn",
    "congruentType", "nameNamespace",
    "scaleFactor", "decimalPlaces",
    "propertyGroups", "eventGroups", "actionGroups", "memberOf",
    "unitProperty",
    "metadata", "semanticId",
    "actionConfiguration", "propertyConfiguration", "eventConfiguration",
    "includeInherited",
    "additionalProperties", "externalSchema", "modellingRule",
    # Preservation envelope.
    "nodes", "NodeModel",
    "nodeSet", "contentType", "encoding", "sha256", "data", "profileVersion",
]

REQUIRED_EXAMPLES = [
    "01-opcua-td-pump.jsonld",
    "02-thing-model-pump.jsonld",
    "03-nodeset-preservation-envelope.jsonld",
    "04-type-reference-modelling-rule.jsonld",
    "05-native-node-model.jsonld",
]

# Forbidden tokens are assembled from fragments so that this file never contains
# the literal itself; this keeps the file scannable by its own check.
FORBIDDEN = [
    "d" + "ov:",     # vendor prefix
    "d" + "tv:",     # vendor prefix
    "a" + "ov:",     # vendor prefix
    "d" + "tmi:",    # vendor node-identifier namespace scheme
    "d" + "tdl",     # legacy source modelling-language name
]

TEXT_EXTS = {".md", ".json", ".jsonld", ".py", ".txt"}
REL_RE = re.compile(r"^\.{1,2}/")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

# Portable identity (Section 5.1.1): NodeId-valued terms shall be OPC 10000-6
# ExpandedNodeId strings (nsu=<NamespaceUri>;<idtype>=<id>, or a namespace-0
# canonical i=<id>) and shall not use the session-local ns=<index> form.
PORTABLE_ID_STRING_KEYS = ("uav:id", "uav:mapToNodeId", "uav:mapToType")
PORTABLE_ID_ARRAY_KEYS = ("uav:hasComponent", "uav:componentOf")
SESSION_NS_RE = re.compile(r"ns=[0-9]")
EXPANDED_NODEID_RE = re.compile(r"^(svr=[0-9]+;)?(nsu=[^;]+;)?[isgb]=.+$")
NODEID_HREF_PREFIX_RE = re.compile(r"^(svr=|nsu=|ns=|[isgb]=)")

ERR: list[str] = []


def err(msg: str) -> None:
    ERR.append(msg)


def rel(path: str) -> str:
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def iter_strings(obj):
    """Yield every dict key and string value in a parsed JSON document."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from iter_strings(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_strings(item)
    elif isinstance(obj, str):
        yield obj


def iter_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from iter_dicts(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from iter_dicts(item)


def all_text_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in sorted(filenames):
            if os.path.splitext(name)[1].lower() in TEXT_EXTS:
                yield os.path.join(dirpath, name)


def json_files():
    for path in all_text_files():
        if os.path.splitext(path)[1].lower() in (".json", ".jsonld"):
            yield path


def check_required_files():
    for path in [CONTEXT, SCHEMA, SPEC, README]:
        if not os.path.isfile(path):
            err(f"missing required artifact {rel(path)}")
    if not os.path.isdir(EXAMPLES):
        err("missing required examples/ directory")
        return
    for name in REQUIRED_EXAMPLES:
        if not os.path.isfile(os.path.join(EXAMPLES, name)):
            err(f"missing required example examples/{name}")


def check_json_parses():
    parsed = {}
    for path in sorted(json_files()):
        try:
            parsed[path] = load_json(path)
        except (json.JSONDecodeError, OSError) as exc:
            err(f"{rel(path)}: JSON does not parse ({exc})")
    return parsed


def context_term_strings(ctx_doc):
    return set(iter_strings(ctx_doc))


def check_context(ctx_doc):
    strings = context_term_strings(ctx_doc)
    if UAV_NS not in strings:
        err(f"context does not declare the uav namespace {UAV_NS}")
    if "uav" not in strings:
        err("context does not declare the 'uav' prefix key")
    for term in DOCUMENTED_TERMS:
        if f"uav:{term}" not in strings:
            err(f"context is missing documented term uav:{term}")


def check_examples(parsed):
    example_paths = [
        p for p in sorted(parsed)
        if os.path.dirname(p) == EXAMPLES and p.lower().endswith(".jsonld")
    ]
    if len(example_paths) < 5:
        err(f"expected at least 5 .jsonld examples, found {len(example_paths)}")
    for path in example_paths:
        doc = parsed[path]
        if not isinstance(doc, dict) or "@context" not in doc:
            err(f"{rel(path)}: example does not declare a top-level @context")
            continue
        if UAV_NS not in set(iter_strings(doc.get("@context"))):
            err(f"{rel(path)}: @context does not bind the uav namespace {UAV_NS}")


def find_envelopes(parsed):
    envelopes = []
    for path, doc in parsed.items():
        for node in iter_dicts(doc):
            if node.get("@type") == "uav:nodeSet":
                envelopes.append((path, node))
    return envelopes


def check_envelope(path, env):
    where = rel(path)
    for field in ("contentType", "encoding", "sha256", "data"):
        if field not in env:
            err(f"{where}: preservation envelope missing '{field}'")
    if env.get("encoding") not in (None, "base64"):
        err(f"{where}: preservation envelope encoding must be 'base64'")
    digest = env.get("sha256", "")
    if not isinstance(digest, str) or not HEX64_RE.match(digest):
        err(f"{where}: preservation envelope sha256 is not a 64-char lower-hex digest")
    data = env.get("data")
    if not isinstance(data, str):
        err(f"{where}: preservation envelope data is not a string")
        return
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        err(f"{where}: preservation envelope data is not valid base64")
        return
    actual = hashlib.sha256(raw).hexdigest()
    if isinstance(digest, str) and HEX64_RE.match(digest) and actual != digest:
        err(f"{where}: preservation envelope sha256 mismatch "
            f"(declared {digest}, computed {actual})")
    try:
        rootel = ET.fromstring(raw)
    except ET.ParseError as exc:
        err(f"{where}: preservation envelope data does not decode to well-formed XML ({exc})")
        return
    localname = rootel.tag.split("}")[-1]
    if localname != UANODESET_LOCALNAME:
        err(f"{where}: preservation envelope XML root is <{localname}>, expected <{UANODESET_LOCALNAME}>")


def check_envelopes(parsed):
    envelopes = find_envelopes(parsed)
    if not envelopes:
        err("no uav:nodeSet preservation envelope found in any example")
    for path, env in envelopes:
        check_envelope(path, env)


def check_native_projection(parsed):
    path = os.path.join(EXAMPLES, "05-native-node-model.jsonld")
    doc = parsed.get(path)
    if not isinstance(doc, dict):
        return
    if "uav:nodeSet" in doc:
        err(f"{rel(path)}: native completeness example shall not contain uav:nodeSet")
    projection = doc.get("uav:nodes")
    if not isinstance(projection, dict):
        err(f"{rel(path)}: missing uav:nodes object")
        return
    if projection.get("@type") != "uav:NodeModel":
        err(f"{rel(path)}: uav:nodes @type shall be uav:NodeModel")
    if projection.get("profileVersion") != "1.0":
        err(f"{rel(path)}: uav:nodes profileVersion shall be 1.0")
    nodes = projection.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        err(f"{rel(path)}: uav:nodes nodes shall be a non-empty array")
        return
    node_classes = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            err(f"{rel(path)}: uav:nodes nodes[{index}] is not an object")
            continue
        for field in ("nodeClass", "nodeId", "browseName"):
            if not isinstance(node.get(field), str) or not node[field]:
                err(f"{rel(path)}: uav:nodes nodes[{index}] missing '{field}'")
        if isinstance(node.get("nodeClass"), str):
            node_classes.add(node["nodeClass"])
    if "ObjectType" not in node_classes or "Variable" not in node_classes:
        err(f"{rel(path)}: native example shall include ObjectType and Variable records")


def check_relative_refs(parsed):
    for path, doc in parsed.items():
        base = os.path.dirname(path)
        for value in iter_strings(doc):
            if REL_RE.match(value):
                target = os.path.normpath(os.path.join(base, value))
                if not os.path.exists(target):
                    err(f"{rel(path)}: internal relative reference '{value}' does not resolve")


def resolve_json_pointer(doc, pointer):
    """Resolve an RFC 6901 JSON Pointer against a parsed document. Returns (value, found)."""
    if pointer == "":
        return doc, True
    if not pointer.startswith("/"):
        return None, False
    node = doc
    for raw_part in pointer.split("/")[1:]:
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            if part not in node:
                return None, False
            node = node[part]
        elif isinstance(node, list):
            if not part.isdigit() or int(part) >= len(node):
                return None, False
            node = node[int(part)]
        else:
            return None, False
    return node, True


def check_unit_properties(parsed):
    """uav:unitProperty shall be a canonical JSON Pointer resolving, in-document, to a
    non-empty string (Section 6.5 / 7 'Unit pointer' rule). Checked on examples only: the
    context and schema files declare the term itself, not a usage of it."""
    for path, doc in parsed.items():
        if os.path.dirname(path) != EXAMPLES or not isinstance(doc, dict):
            continue
        for node in iter_dicts(doc):
            if not isinstance(node, dict) or "uav:unitProperty" not in node:
                continue
            pointer = node["uav:unitProperty"]
            if not isinstance(pointer, str) or not pointer.startswith("/"):
                err(f"{rel(path)}: uav:unitProperty '{pointer}' is not a canonical "
                    f"RFC 6901 JSON Pointer")
                continue
            value, found = resolve_json_pointer(doc, pointer)
            if not found:
                err(f"{rel(path)}: uav:unitProperty '{pointer}' does not resolve within the document")
            elif not isinstance(value, str) or not value:
                err(f"{rel(path)}: uav:unitProperty '{pointer}' resolves to a non-string or "
                    f"empty value")


def check_containment(parsed):
    """uav:containedIn shall name an actual composite (Section 7 'Containment consistency'):
    the value must match the title of a document declaring uav:isComposite, and where a
    local uav:componentModel link connects the two examples, the composite's uav:contains
    must reciprocally list that link's uav:refName. Checked on examples only: the context
    and schema files declare the term itself, not a usage of it."""
    titles = {}
    for path, doc in parsed.items():
        if os.path.dirname(path) == EXAMPLES and isinstance(doc, dict) and isinstance(doc.get("title"), str):
            titles.setdefault(doc["title"], []).append((path, doc))

    for path, doc in parsed.items():
        if os.path.dirname(path) != EXAMPLES or not isinstance(doc, dict):
            continue
        for node in iter_dicts(doc):
            if not isinstance(node, dict) or "uav:containedIn" not in node:
                continue
            contained_in = node["uav:containedIn"]
            if not isinstance(contained_in, str) or not contained_in:
                err(f"{rel(path)}: uav:containedIn is not a non-empty string")
                continue
            candidates = [(cpath, cdoc) for cpath, cdoc in titles.get(contained_in, [])
                          if cdoc.get("uav:isComposite")]
            if not candidates:
                err(f"{rel(path)}: uav:containedIn '{contained_in}' does not match the "
                    f"title of any known composite (uav:isComposite: true)")
                continue
            reciprocal_ok = False
            for cpath, cdoc in candidates:
                contains = cdoc.get("uav:contains") or []
                base = os.path.dirname(cpath)
                for link in cdoc.get("links", []) or []:
                    if not isinstance(link, dict) or link.get("rel") != "uav:componentModel":
                        continue
                    href = link.get("href")
                    if not isinstance(href, str) or not REL_RE.match(href):
                        continue
                    target = os.path.normpath(os.path.join(base, href))
                    if os.path.normpath(target) != os.path.normpath(path):
                        continue
                    if link.get("uav:refName") in contains:
                        reciprocal_ok = True
            if not reciprocal_ok:
                err(f"{rel(path)}: uav:containedIn '{contained_in}' has no reciprocal "
                    f"uav:componentModel link + matching uav:contains entry in a composite "
                    f"named '{contained_in}'")


def _expanded_nodeid(path, where, value):
    """Assert that value is a portable OPC 10000-6 ExpandedNodeId (Section 5.1.1):
    no session-local ns=<index> form, and a recognizable idtype (i/s/g/b)."""
    if not isinstance(value, str) or not value:
        err(f"{rel(path)}: {where} is not a non-empty string")
        return
    if SESSION_NS_RE.search(value):
        err(f"{rel(path)}: {where} uses the session-local ns=<index> form ('{value}'); "
            f"a persisted document shall use an ExpandedNodeId (nsu=<NamespaceUri>;... "
            f"or namespace-0 i=...)")
        return
    if not EXPANDED_NODEID_RE.match(value):
        err(f"{rel(path)}: {where} '{value}' is not a valid ExpandedNodeId string")


def check_portable_identity(parsed):
    """Portable identity (Section 5.1.1 / Section 7 'Portable identity'): every
    NodeId-valued term shall be an ExpandedNodeId and shall not use ns=<index>.
    Checked on examples only: the context and schema files declare the terms, not
    usages of them. The canonical NodeSet2 XML inside a uav:nodeSet envelope is
    carried base64-encoded under the 'data' key. NodeSet-local nodeId/reference
    fields inside uav:nodes are paired with that projection's namespaceUris table
    and are not readable identity terms, so neither representation is affected by
    this rule."""
    for path, doc in parsed.items():
        if os.path.dirname(path) != EXAMPLES or not isinstance(doc, dict):
            continue
        for node in iter_dicts(doc):
            if not isinstance(node, dict):
                continue
            for key in PORTABLE_ID_STRING_KEYS:
                if key in node:
                    _expanded_nodeid(path, key, node[key])
            for key in PORTABLE_ID_ARRAY_KEYS:
                if key in node:
                    values = node[key]
                    if not isinstance(values, list):
                        err(f"{rel(path)}: {key} is not an array")
                        continue
                    for value in values:
                        _expanded_nodeid(path, f"{key} entry", value)
            ref_type = node.get("uav:refType")
            if isinstance(ref_type, str) and "=" in ref_type:
                # A NodeId-valued uav:refType (a browse name such as HasComponent
                # carries no '='); it shall be a portable ExpandedNodeId.
                _expanded_nodeid(path, "uav:refType", ref_type)
            href = node.get("href")
            if isinstance(href, str):
                if "?id=" in href:
                    _expanded_nodeid(path, "form href ?id=", href.split("?id=", 1)[1])
                elif NODEID_HREF_PREFIX_RE.match(href):
                    _expanded_nodeid(path, "link href NodeId", href)


def check_event_annotations(parsed):
    """Event annotation consistency (Section 5.2 / Section 7 'Event annotation
    consistency'): uav:eventType is the @type counterpart of the uav:isEvent flag,
    so an affordance annotated @type uav:eventType shall not set uav:isEvent: false.
    Checked on examples only."""
    for path, doc in parsed.items():
        if os.path.dirname(path) != EXAMPLES or not isinstance(doc, dict):
            continue
        for node in iter_dicts(doc):
            if not isinstance(node, dict):
                continue
            types = node.get("@type")
            type_list = (types if isinstance(types, list)
                         else [types] if isinstance(types, str) else [])
            if "uav:eventType" in type_list and node.get("uav:isEvent") is False:
                err(f"{rel(path)}: an affordance annotated @type uav:eventType shall not "
                    f"set uav:isEvent: false (Section 5.2)")


MODELLING_RULE_IDS = {
    "Mandatory": "i=78",
    "Optional": "i=80",
    "MandatoryPlaceholder": "i=11510",
    "OptionalPlaceholder": "i=11508",
}

MODELLING_RULE_TABLE_RE = re.compile(
    r"Modelling rule \(`Mandatory` `(i=\d+)`, `Optional` `(i=\d+)`, "
    r"`MandatoryPlaceholder` `(i=\d+)`, `OptionalPlaceholder` `(i=\d+)`\)"
)


def check_modelling_rule_ids():
    """The normative modelling-rule NodeIds documented in the spec (Section 9
    NodeSet2 and WoT conversion table) shall match the OPC 10000-3 standard
    values: Mandatory i=78, Optional i=80, MandatoryPlaceholder i=11510,
    OptionalPlaceholder i=11508. This guards against the two placeholder
    NodeIds being swapped or mistyped."""
    try:
        text = open(SPEC, encoding="utf-8").read()
    except OSError as exc:
        err(f"{rel(SPEC)}: cannot read ({exc})")
        return
    match = MODELLING_RULE_TABLE_RE.search(text)
    if not match:
        err(f"{rel(SPEC)}: modelling rule NodeId table not found or not in expected format")
        return
    found = {
        "Mandatory": match.group(1),
        "Optional": match.group(2),
        "MandatoryPlaceholder": match.group(3),
        "OptionalPlaceholder": match.group(4),
    }
    for rule, expected in MODELLING_RULE_IDS.items():
        if found[rule] != expected:
            err(f"{rel(SPEC)}: modelling rule '{rule}' documented as '{found[rule]}', "
                f"expected '{expected}'")


def check_forbidden_tokens():
    for path in all_text_files():
        try:
            text = open(path, encoding="utf-8").read().lower()
        except OSError as exc:
            err(f"{rel(path)}: cannot read ({exc})")
            continue
        for token in FORBIDDEN:
            if token in text:
                err(f"{rel(path)}: contains forbidden token '{token}'")


def main() -> int:
    check_required_files()
    parsed = check_json_parses()

    ctx_doc = parsed.get(CONTEXT)
    if ctx_doc is None and os.path.isfile(CONTEXT):
        # parse failure already reported
        pass
    elif ctx_doc is not None:
        check_context(ctx_doc)

    check_examples(parsed)
    check_native_projection(parsed)
    check_envelopes(parsed)
    check_relative_refs(parsed)
    check_unit_properties(parsed)
    check_containment(parsed)
    check_portable_identity(parsed)
    check_event_annotations(parsed)
    check_modelling_rule_ids()
    check_forbidden_tokens()

    print(f"context: {rel(CONTEXT)}")
    print(f"json artifacts checked: {len(parsed)}")
    print(f"documented uav terms: {len(DOCUMENTED_TERMS)}")
    if ERR:
        print(f"ERRORS: {len(ERR)}")
        for message in ERR:
            print(f"  - {message}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
