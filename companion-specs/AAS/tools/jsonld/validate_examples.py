#!/usr/bin/env python3
"""Validate the committed JSON-LD and Thing Description examples.

Validation is deliberately separate from the emitters.  It processes the exact
bytes that will be written, resolves only the bundled AAS context and the pinned
W3C TD and OPC UA WoT Binding contexts, validates TD syntax against both pinned
schemas, lowers the AAS graph, and independently compares the complete projected
containment graph across sibling TDs.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from jsonschema import Draft7Validator, Draft202012Validator
from pyld import jsonld

HERE = Path(__file__).resolve().parent
AAS_DIR = HERE.parent.parent
TOOLS_DIR = HERE.parent
VENDOR = HERE / "vendor"
TD_CONTEXT = VENDOR / "td-context-1.1.jsonld"
TD_SCHEMA = VENDOR / "td-json-schema-validation.json"
BINDING_CONTEXT = VENDOR / "opc-ua-wot-binding.context.jsonld"
BINDING_SCHEMA = VENDOR / "opc-ua-wot-binding.schema.json"
VENDOR_SOURCES = VENDOR / "sources.json"
TEMPLATE_MANIFEST = VENDOR / "template-sources.json"
AAS_CONTEXT = AAS_DIR / "aas.context.jsonld"
NODEIDS = AAS_DIR / "Opc.Ua.I4AAS.NodeIds.csv"
NODESET = AAS_DIR / "Opc.Ua.I4AAS.NodeSet2.xml"
FIXTURES = TOOLS_DIR / "fixtures"

TD_CONTEXT_URL = "https://www.w3.org/2022/wot/td/v1.1"
AAS_CONTEXT_URL = "https://w3id.org/aas-jsonld/context"
ORDER_GRAPH = "https://w3id.org/aas-jsonld/graph/order"
AAS = "https://admin-shell.io/aas/3/0/"
LD = "https://w3id.org/aas-jsonld/"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
UA = "http://opcfoundation.org/UA/"
UAV = "http://opcfoundation.org/UA/WoT-Binding/"
I4AAS_FAMILY = "http://opcfoundation.org/UA/I4AAS/"
EXPECTED_I4AAS = "http://opcfoundation.org/UA/I4AAS/v3/"
TD = "https://www.w3.org/2019/wot/td#"
HCTL = "https://www.w3.org/2019/wot/hypermedia#"
XSD = "http://www.w3.org/2001/XMLSchema#"
NODESET_XMLNS = "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"


def load_model_uri() -> str:
    model = ET.parse(NODESET).find(
        f"{{{NODESET_XMLNS}}}Models/{{{NODESET_XMLNS}}}Model")
    if model is None or not model.get("ModelUri"):
        raise AssertionError(f"{NODESET}: no model URI")
    return model.get("ModelUri")


I4AAS = load_model_uri()
if I4AAS != EXPECTED_I4AAS:
    raise AssertionError(
        f"{NODESET}: ModelUri is {I4AAS!r}, expected {EXPECTED_I4AAS!r}")

sys.path.insert(0, str(HERE))

from conformance import canonical  # noqa: E402
from lift import Lifter, Ontology, Schema, iri, literal, serialize  # noqa: E402
from lower import Lowerer, parse_nt  # noqa: E402

ONTOLOGY = Ontology()
SCHEMA = Schema()

TEMPLATE_METADATA = json.loads(TEMPLATE_MANIFEST.read_text(encoding="utf-8"))
TEMPLATE_SOURCES = tuple(
    (name, VENDOR / meta["file"])
    for name, meta in sorted(TEMPLATE_METADATA["templates"].items())
)

NODE_CLASS_TERMS = {
    "uav:object", "uav:variable", "uav:method", "uav:objectType",
    "uav:variableType", "uav:referenceType", "uav:dataType", "uav:view",
}

ELEMENT_TYPES = {
    "Property": "AASPropertyType",
    "MultiLanguageProperty": "AASMultiLanguagePropertyType",
    "Range": "AASRangeType",
    "Blob": "AASBlobType",
    "File": "AASFileType",
    "ReferenceElement": "AASReferenceElementType",
    "RelationshipElement": "AASRelationshipElementType",
    "AnnotatedRelationshipElement": "AASAnnotatedRelationshipElementType",
    "SubmodelElementCollection": "AASSubmodelElementCollectionType",
    "SubmodelElementList": "AASSubmodelElementListType",
    "Entity": "AASEntityType",
    "BasicEventElement": "AASBasicEventElementType",
    "Operation": "AASOperationType",
    "Capability": "AASCapabilityType",
}

CHILD_FIELDS = {
    "SubmodelElementCollection": ("value", False),
    "SubmodelElementList": ("value", True),
    "AnnotatedRelationshipElement": ("annotations", False),
    "Entity": ("statements", False),
}

OPERATION_ROLES = (
    ("inputVariables", "InputVariables"),
    ("outputVariables", "OutputVariables"),
    ("inoutputVariables", "InoutputVariables"),
)

IDENTIFIABLE_GROUPS = (
    ("assetAdministrationShells", "AssetAdministrationShell"),
    ("submodels", "Submodel"),
    ("conceptDescriptions", "ConceptDescription"),
)


def verify_vendor() -> None:
    with VENDOR_SOURCES.open(encoding="utf-8") as stream:
        sources = json.load(stream)
    for name, meta in sources.items():
        actual = hashlib.sha256((VENDOR / name).read_bytes()).hexdigest()
        if actual != meta["sha256"]:
            raise AssertionError(f"{name}: pinned SHA-256 is {meta['sha256']}, got {actual}")
    commit = TEMPLATE_METADATA.get("commit", "")
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise AssertionError("template source commit is not an immutable Git SHA")
    for name, meta in TEMPLATE_METADATA["templates"].items():
        path = VENDOR / meta["file"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != meta["sha256"]:
            raise AssertionError(
                f"{name}: pinned SHA-256 is {meta['sha256']}, got {actual}")


def _loader_document(url: str, path: Path) -> dict:
    return {
        "contextUrl": None,
        "documentUrl": url,
        "document": json.loads(path.read_text(encoding="utf-8")),
        "contentType": "application/ld+json",
    }


def document_loader(url: str, options=None) -> dict:
    if url == TD_CONTEXT_URL:
        return _loader_document(url, TD_CONTEXT)
    if url == AAS_CONTEXT_URL:
        raise ValueError(
            f"{AAS_CONTEXT_URL} is not the context strategy of the committed examples")
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == "file":
        path = Path(urllib.request.url2pathname(parsed.path)).resolve()
        try:
            path.relative_to(AAS_DIR)
        except ValueError as exc:
            raise ValueError(f"context is outside the AAS tree: {path}") from exc
        if not path.is_file():
            raise ValueError(f"context does not exist: {path}")
        return _loader_document(url, path)
    raise ValueError(f"unbundled JSON-LD context: {url}")


def process_jsonld(doc: object, path: Path) -> dict:
    return jsonld.to_rdf(
        doc,
        {
            "base": path.resolve().as_uri(),
            "documentLoader": document_loader,
        },
    )


def merge_document_datasets(datasets: list[tuple[Path, dict]]) -> dict:
    merged = defaultdict(list)
    for document_index, (path, dataset) in enumerate(datasets):
        scope = hashlib.sha256(
            (str(path.resolve()) + f"#{document_index}").encode("utf-8")
        ).hexdigest()[:16]
        for graph_name, quads in dataset.items():
            scoped_graph = (
                f"_:d{scope}-{graph_name.removeprefix('_:')}"
                if graph_name.startswith("_:") else graph_name)
            for quad in quads:
                scoped_quad = {}
                for name in ("subject", "predicate", "object"):
                    part = dict(quad[name])
                    if part.get("type") == "blank node":
                        part["value"] = (
                            f"_:d{scope}-"
                            + part["value"].removeprefix("_:"))
                    scoped_quad[name] = part
                merged[scoped_graph].append(scoped_quad)
    return dict(merged)


def validate_td(doc: object) -> None:
    if not isinstance(doc, dict):
        raise AssertionError("a Thing Description file must contain one JSON object")
    if "id" not in doc:
        raise AssertionError("a published Thing Description must carry the id alias")
    if "id" in doc and "@id" in doc:
        raise AssertionError("a Thing Description must use either id or @id, not both")
    validate_absolute_uri(doc["id"], "Thing Description id")
    errors = sorted(
        Draft7Validator(json.loads(TD_SCHEMA.read_text(encoding="utf-8"))).iter_errors(doc),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        where = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise AssertionError(f"TD schema at {where}: {first.message}")
    errors = sorted(
        Draft202012Validator(
            json.loads(BINDING_SCHEMA.read_text(encoding="utf-8"))
        ).iter_errors(doc),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        where = "/".join(str(part) for part in first.absolute_path) or "<root>"
        raise AssertionError(f"OPC UA WoT Binding schema at {where}: {first.message}")


def resolved_local_context(value: str, path: Path) -> Path | None:
    url = urllib.parse.urljoin(path.resolve().as_uri(), value)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "file":
        return None
    return Path(urllib.request.url2pathname(parsed.path)).resolve()


def validate_context_strategy(doc: object, path: Path, td: bool) -> None:
    if not isinstance(doc, dict):
        return
    context = doc.get("@context")
    if td:
        if not isinstance(context, list):
            raise AssertionError("a published TD must carry a context array")
        strings = [entry for entry in context if isinstance(entry, str)]
        if strings.count(TD_CONTEXT_URL) != 1:
            raise AssertionError("a published TD must carry the W3C TD 1.1 context once")
        local_aas = [
            value for value in strings
            if resolved_local_context(value, path) == AAS_CONTEXT.resolve()
        ]
        local_binding = [
            value for value in strings
            if resolved_local_context(value, path) == BINDING_CONTEXT.resolve()
        ]
        if len(local_aas) != 1 or len(local_binding) != 1 or len(strings) != 3:
            raise AssertionError(
                "a published TD must carry exactly the W3C, bundled AAS, "
                "and bundled OPC UA WoT Binding contexts")
        if not all(isinstance(entry, (str, dict)) for entry in context):
            raise AssertionError("a published TD context may contain only IRIs and inline terms")
        inline = {}
        for entry in context:
            if isinstance(entry, dict):
                inline.update(entry)
        if inline.get("id") != "@id":
            raise AssertionError("the final inline context must keep TD id as the @id alias")
        return
    if not isinstance(context, str) or resolved_local_context(context, path) != AAS_CONTEXT.resolve():
        raise AssertionError("a published AAS JSON-LD example must use the bundled AAS context")


def term(node: dict) -> str:
    if node["type"] == "IRI":
        return iri(node["value"])
    if node["type"] == "blank node":
        return node["value"]
    return literal(node["value"], node.get("datatype"), node.get("language"))


def dataset_text(dataset: dict) -> tuple[str, str]:
    core, order = [], []
    for graph_name, quads in dataset.items():
        target = order if graph_name == ORDER_GRAPH else core
        for quad in quads:
            target.append(
                f"{term(quad['subject'])} {term(quad['predicate'])} {term(quad['object'])} .")
    return "\n".join(core), "\n".join(order)


def validate_td_identifier(doc: dict, dataset: dict) -> None:
    root = f"<{doc['id']}>"
    aas_types = [
        obj
        for subject, predicate, obj in parse_nt(dataset_text(dataset)[0])
        if (
            subject == root
            and predicate == iri(RDF_TYPE)
            and obj.startswith(f"<{AAS}"))
    ]
    if len(aas_types) != 1:
        raise AssertionError(
            "the TD id alias does not identify exactly one typed AAS node "
            "in the final RDF graph")


def core_rdf_index(dataset: dict):
    index = defaultdict(lambda: defaultdict(list))
    for graph_name, quads in dataset.items():
        if graph_name == ORDER_GRAPH:
            continue
        for quad in quads:
            subject = quad["subject"]["value"]
            predicate = quad["predicate"]["value"]
            index[subject][predicate].append(quad["object"])
    return index


def one_rdf(index, subject: str, predicate: str, *, required=True):
    values = index.get(subject, {}).get(predicate, [])
    if not values and not required:
        return None
    if len(values) != 1:
        raise AssertionError(
            f"{subject}: {predicate} has {len(values)} values, expected one")
    return values[0]


def rdf_literal(node: dict, label: str) -> str:
    if node.get("type") != "literal":
        raise AssertionError(f"{label} is not an RDF literal")
    return node["value"]


def validate_absolute_uri(value: str, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AssertionError(f"{label} is empty or not a string")
    if (
            any(ord(char) <= 0x20 or 0x7F <= ord(char) <= 0x9F
                for char in value)
            or any(char in '<>"{}|\\^`' for char in value)):
        raise AssertionError(f"{label} contains whitespace or a control character")
    for offset, char in enumerate(value):
        if char == "%" and (
                offset + 2 >= len(value)
                or any(digit not in "0123456789abcdefABCDEF"
                       for digit in value[offset + 1:offset + 3])):
            raise AssertionError(f"{label} contains an invalid percent escape")
    parsed = urllib.parse.urlsplit(value)
    if not parsed.scheme:
        raise AssertionError(f"{label} is not an absolute URI: {value!r}")
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        raise AssertionError(f"{label} has no authority: {value!r}")
    try:
        parsed.port
    except ValueError as exc:
        raise AssertionError(f"{label} has an invalid authority: {value!r}") from exc
    return value


def type_terms(value) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {entry for entry in value if isinstance(entry, str)}
    return set()


def validate_node_class_domains(doc: dict) -> None:
    root_types = type_terms(doc.get("@type"))
    if "uav:object" not in root_types:
        raise AssertionError("a projected OPC UA Object TD root must carry uav:object")
    if root_types & {"uav:variable", "uav:method"}:
        raise AssertionError("uav:variable and uav:method are not Thing-level types")

    def walk(value, *, root=False, domain=None, label="<root>"):
        if isinstance(value, list):
            for index, entry in enumerate(value):
                walk(entry, domain=domain, label=f"{label}/{index}")
            return
        if not isinstance(value, dict):
            return
        types = type_terms(value.get("@type"))
        if not root and "uav:object" in types:
            raise AssertionError(
                f"{label}: uav:object is permitted only at Thing level")
        if "uav:variable" in types and domain != "property":
            raise AssertionError(
                f"{label}: uav:variable is permitted only on property affordances")
        if "uav:method" in types and domain != "action":
            raise AssertionError(
                f"{label}: uav:method is permitted only on action affordances")
        for member, expected_type, member_domain in (
                ("properties", "uav:variable", "property"),
                ("actions", "uav:method", "action")):
            affordances = value.get(member, {})
            if affordances is None:
                continue
            if not isinstance(affordances, dict):
                raise AssertionError(f"{label}/{member}: affordance map is not an object")
            for name, affordance in affordances.items():
                if not isinstance(affordance, dict):
                    raise AssertionError(
                        f"{label}/{member}/{name}: affordance is not an object")
                if expected_type not in type_terms(affordance.get("@type")):
                    raise AssertionError(
                        f"{label}/{member}/{name}: missing {expected_type}")
                walk(
                    affordance, domain=member_domain,
                    label=f"{label}/{member}/{name}")
        for key, child in value.items():
            if key in {"properties", "actions"}:
                continue
            walk(child, label=f"{label}/{key}")

    walk(doc, root=True)


def validate_expanded_node_class_domains(dataset: dict, doc: dict) -> None:
    index = core_rdf_index(dataset)
    root = doc.get("id")
    if not isinstance(root, str):
        raise AssertionError("Thing Description has no root identifier")

    def targets(predicate):
        return {
            obj["value"]
            for obj in index.get(root, {}).get(predicate, [])
            if obj.get("type") in {"IRI", "blank node"}
        }

    property_affordances = targets(TD + "hasPropertyAffordance")
    action_affordances = targets(TD + "hasActionAffordance")
    typed = defaultdict(set)
    for subject, predicates in index.items():
        for obj in predicates.get(RDF_TYPE, []):
            if obj.get("type") == "IRI":
                typed[obj["value"]].add(subject)
    if typed[UAV + "object"] != {root}:
        raise AssertionError(
            "expanded uav:object types are not confined to the TD root")
    if typed[UAV + "variable"] != property_affordances:
        raise AssertionError(
            "expanded uav:variable types do not equal the property affordances")
    if typed[UAV + "method"] != action_affordances:
        raise AssertionError(
            "expanded uav:method types do not equal the action affordances")


def parse_opc_form_href(value: str, expected_node_id: str, label: str) -> str:
    validate_absolute_uri(value, label)
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "opc.tcp":
        raise AssertionError(f"{label} does not use opc.tcp")
    if not parsed.hostname or parsed.port is None or parsed.username or parsed.password:
        raise AssertionError(f"{label} must carry an OPC UA host and explicit port")
    if parsed.fragment:
        raise AssertionError(f"{label} must not carry a fragment")
    if not parsed.path.startswith("/"):
        raise AssertionError(f"{label} has no absolute OPC UA resource path")
    if not parsed.query.startswith("id=") or "&" in parsed.query:
        raise AssertionError(f"{label} must carry exactly one id query parameter")
    raw_node_id = parsed.query[3:]
    if not raw_node_id:
        raise AssertionError(f"{label} has an empty id query parameter")
    try:
        node_id = urllib.parse.unquote_to_bytes(raw_node_id).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError(f"{label} does not encode a UTF-8 ExpandedNodeId") from exc
    canonical = urllib.parse.quote(
        node_id, safe=":/;=,!$'()*+-._~@")
    if canonical != raw_node_id:
        raise AssertionError(f"{label} is not canonically percent encoded")
    parse_expanded_node_id(node_id, f"{label} id")
    if node_id != expected_node_id:
        raise AssertionError(
            f"{label} addresses {node_id!r}, expected {expected_node_id!r}")
    return node_id


def validate_object_form(doc: dict) -> None:
    node_id = doc.get("uav:id")
    if not isinstance(node_id, str):
        raise AssertionError("projected Object TD has no compact uav:id")
    forms = doc.get("forms")
    if not isinstance(forms, list) or len(forms) != 1:
        raise AssertionError("projected Object TD must carry exactly one Thing-level form")
    form = forms[0]
    if not isinstance(form, dict) or not isinstance(form.get("href"), str):
        raise AssertionError("projected Object TD form has no href")
    if form.get("op") != "readallproperties":
        raise AssertionError(
            "an OPC UA Object address form must use the Thing-level "
            "readallproperties operation")
    parse_opc_form_href(form["href"], node_id, "projected Object TD form href")


def is_ascii_digits(value: str) -> bool:
    return bool(value) and all(character in "0123456789" for character in value)


def _take_length(text: str) -> tuple[int, str]:
    token, separator, tail = text.partition(":")
    if (
            not separator
            or not is_ascii_digits(token)
            or (len(token) > 1 and token.startswith("0"))):
        raise AssertionError("invalid I4AAS length prefix")
    return int(token), tail


def encode_nodeid_component(value: str) -> str:
    encoded = []
    for character in value:
        codepoint = ord(character)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise AssertionError("a NodeId component contains a Unicode surrogate")
        if character == "%" or codepoint <= 0x1F or 0x7F <= codepoint <= 0x9F:
            encoded.extend(f"%{byte:02X}" for byte in character.encode("utf-8"))
        else:
            encoded.append(character)
    return "".join(encoded)


def decode_nodeid_component(value: str) -> str:
    if any(ord(character) <= 0x1F or 0x7F <= ord(character) <= 0x9F
           for character in value):
        raise AssertionError("an encoded NodeId component contains a raw control character")
    try:
        decoded = urllib.parse.unquote_to_bytes(value).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AssertionError("an encoded NodeId component is not UTF-8") from exc
    if encode_nodeid_component(decoded) != value:
        raise AssertionError("a NodeId component is not canonically escaped")
    return decoded


def decode_i4aas_identifier(identifier: str) -> tuple[str, str, str | None]:
    if len(identifier) > 4096 or not identifier.startswith("i4aas3:"):
        raise AssertionError("invalid I4AAS V3 String NodeId")
    kind, separator, rest = identifier[len("i4aas3:"):].partition(":")
    if not separator or kind not in {"A", "S", "C", "E"}:
        raise AssertionError("invalid I4AAS node-kind discriminator")
    owner_length, rest = _take_length(rest)
    if kind == "E":
        path_length, payload = _take_length(rest)
        if len(payload) != owner_length + path_length:
            raise AssertionError("I4AAS element payload does not match its lengths")
        return (
            kind,
            decode_nodeid_component(payload[:owner_length]),
            decode_nodeid_component(payload[owner_length:]),
        )
    if len(rest) != owner_length:
        raise AssertionError("I4AAS identifiable payload does not match its length")
    return kind, decode_nodeid_component(rest), None


def parse_expanded_node_id(value: str, label: str) -> tuple[str, str, str, str | None]:
    if not isinstance(value, str) or not value.startswith("nsu="):
        raise AssertionError(f"{label} is not an nsu= ExpandedNodeId: {value!r}")
    namespace, separator, identifier = value[4:].partition(";")
    if not separator:
        raise AssertionError(f"{label} has no ExpandedNodeId identifier")
    validate_absolute_uri(namespace, f"{label} namespace")
    if not identifier.startswith("s="):
        raise AssertionError(f"{label} is not the required String ExpandedNodeId")
    kind, owner, path = decode_i4aas_identifier(identifier[2:])
    return namespace, kind, owner, path


def parse_qualified_name(value: str, label: str) -> tuple[str, str]:
    if not isinstance(value, str) or not value.startswith("nsu="):
        raise AssertionError(f"{label} is not an nsu= QualifiedName: {value!r}")
    namespace, separator, name = value[4:].partition(";")
    if not separator or not name or name.startswith(("s=", "i=", "g=", "b=")):
        raise AssertionError(f"{label} is malformed: {value!r}")
    validate_absolute_uri(namespace, f"{label} namespace")
    if any(ord(character) <= 0x1F or 0x7F <= ord(character) <= 0x9F
           for character in name):
        raise AssertionError(f"{label} contains a control character")
    return namespace, name


def parse_numeric_node_id(value: str, label: str) -> int:
    if not isinstance(value, str) or not value.startswith("i="):
        raise AssertionError(f"{label} is not a numeric NodeId: {value!r}")
    number = value[2:]
    if not is_ascii_digits(number) or (
            len(number) > 1 and number.startswith("0")):
        raise AssertionError(f"{label} is malformed: {value!r}")
    return int(number)


def validate_expanded_namespaces(dataset: dict, doc: dict | None, td: bool) -> None:
    index = core_rdf_index(dataset)
    known_properties = {prop["iri"] for prop in ONTOLOGY.properties.values()}
    known_classes = set(ONTOLOGY.superclasses)
    known_classes.update(ONTOLOGY.enums)
    known_aas_objects = {AAS + name for name in known_classes}
    for enum_name, members in ONTOLOGY.enums.items():
        known_aas_objects.update(AAS + enum_name + "/" + member for member in members)
    allowed_uav = {
        UAV + name for name in (
            "object", "id", "browseName", "hasComponent", "componentOf", "index",
            "modellingRule", "refId", "refName",
        )
    }
    for predicates in index.values():
        for predicate, objects in predicates.items():
            if predicate.startswith(AAS) and predicate not in known_properties:
                raise AssertionError(f"unknown AAS property IRI {predicate}")
            if predicate.startswith(UAV) and predicate not in allowed_uav:
                raise AssertionError(f"unknown UAV IRI {predicate}")
            for obj in objects:
                if obj.get("type") != "IRI":
                    continue
                value = obj["value"]
                if value.startswith(I4AAS_FAMILY) and not value.startswith(I4AAS):
                    raise AssertionError(f"I4AAS IRI is outside the v3 namespace: {value}")
                if predicate == RDF_TYPE and value.startswith(AAS):
                    if value not in known_aas_objects:
                        raise AssertionError(f"unknown AAS class IRI {value}")
                if predicate == RDF_TYPE and value.startswith(I4AAS):
                    name = value[len(I4AAS):]
                    if name not in TYPE_NODEIDS:
                        raise AssertionError(f"unknown I4AAS v3 type IRI {value}")
    for subject, predicates in index.items():
        for predicate in (UAV + "id", UAV + "componentOf"):
            for obj in predicates.get(predicate, []):
                parse_expanded_node_id(
                    rdf_literal(obj, f"{subject} {predicate}"),
                    f"{subject} {predicate}",
                )
        for obj in predicates.get(UAV + "browseName", []):
            parse_qualified_name(
                rdf_literal(obj, f"{subject} uav:browseName"),
                f"{subject} uav:browseName",
            )
        for obj in predicates.get(UAV + "refId", []):
            parse_numeric_node_id(
                rdf_literal(obj, f"{subject} uav:refId"),
                f"{subject} uav:refId",
            )
        for predicate in (HCTL + "hasTarget", HCTL + "hasAnchor"):
            for obj in predicates.get(predicate, []):
                if obj.get("type") not in {"IRI", "literal"}:
                    raise AssertionError(
                        f"{subject} {predicate} is not a URI-valued RDF term")
                validate_absolute_uri(
                    obj["value"], f"{subject} {predicate}")
    if td:
        root = doc.get("id") if isinstance(doc, dict) else None
        if not root:
            raise AssertionError("Thing Description has no root identifier")
        types = {
            obj["value"]
            for obj in index.get(root, {}).get(RDF_TYPE, [])
            if obj.get("type") == "IRI"
        }
        if UAV + "object" not in types:
            raise AssertionError("expanded RDF does not use the exact UAV object IRI")
        model_types = [value for value in types if value.startswith(I4AAS)]
        if len(model_types) != 1:
            raise AssertionError(
                "expanded RDF does not use exactly one I4AAS v3 type IRI")


def sorted_roots(doc: dict) -> dict:
    out = json.loads(json.dumps(doc))
    for collection in ("assetAdministrationShells", "submodels", "conceptDescriptions"):
        if collection in out:
            out[collection] = sorted(out[collection], key=lambda node: node.get("id", ""))
    return out


def aas_signature_context(text: str):
    """Build structural signatures for AAS subjects in one core graph."""
    triples = parse_nt(text)
    aas_triples = [
        triple for triple in triples
        if (triple[1][1:-1].startswith(AAS)
            or (triple[1] == iri(RDF_TYPE) and triple[2].startswith(f"<{AAS}")))
    ]
    outgoing = {}
    for subject, predicate, obj in aas_triples:
        outgoing.setdefault(subject, []).append((predicate, obj))
    root_types = {
        iri(AAS + "AssetAdministrationShell"),
        iri(AAS + "Submodel"),
        iri(AAS + "ConceptDescription"),
    }
    typed_roots = {
        subject for subject, predicate, obj in aas_triples
        if predicate == iri(RDF_TYPE) and obj in root_types
    }
    identified = {
        subject for subject, predicate, _ in aas_triples
        if predicate == iri(AAS + "Identifiable/id")
    }
    roots = typed_roots & identified
    memo = {}
    visiting = set()

    def render(subject: str):
        if subject in memo:
            return memo[subject]
        if subject in visiting:
            raise AssertionError("the AAS content contains a subject cycle")
        visiting.add(subject)
        value = tuple(sorted(
            (predicate, render(obj) if obj in outgoing and obj not in roots else obj)
            for predicate, obj in outgoing.get(subject, [])
        ))
        visiting.remove(subject)
        memo[subject] = value
        return value

    def signature(value: str):
        if value in roots:
            return ("root", value)
        if value in outgoing:
            return ("node", render(value))
        return ("term", value)

    return roots, render, signature


def canonical_aas_content(text: str) -> tuple:
    """Compare AAS graph structure while allowing named projected child nodes.

    Clause 2 emits blank nodes below each root. A projection-complete TD names
    those nodes so links can address them. Replacing a blank node with an IRI is
    an RDF skolemization, so the comparison recursively renders every AAS child
    subject but retains the encoded root IRI and every literal or vocabulary
    IRI.
    """
    roots, render, _ = aas_signature_context(text)
    return tuple(sorted((root, render(root)) for root in roots))


def ordering_occurrences(core_text: str, order_text: str) -> Counter:
    """Return every ordering occurrence as a blank-node-independent tuple."""
    _, _, signature = aas_signature_context(core_text)
    grouped = defaultdict(lambda: defaultdict(list))
    for subject, predicate, obj in parse_nt(order_text):
        grouped[subject][predicate].append(obj)
    required = {
        iri(RDF_TYPE): iri(LD + "Occurrence"),
        iri(LD + "subject"): None,
        iri(LD + "property"): None,
        iri(LD + "member"): None,
        iri(LD + "index"): None,
    }
    occurrences = Counter()
    for occurrence, fields in grouped.items():
        if set(fields) != set(required):
            raise AssertionError(
                f"{occurrence}: ordering occurrence fields are incomplete or unexpected")
        values = {}
        for predicate, fixed in required.items():
            objects = fields[predicate]
            if len(objects) != 1:
                raise AssertionError(
                    f"{occurrence}: {predicate} has {len(objects)} values")
            values[predicate] = objects[0]
            if fixed is not None and objects[0] != fixed:
                raise AssertionError(
                    f"{occurrence}: {predicate} is {objects[0]}, expected {fixed}")
        property_term = values[iri(LD + "property")]
        if not (property_term.startswith("<") and property_term.endswith(">")):
            raise AssertionError(f"{occurrence}: ordering property is not an IRI")
        index_term = values[iri(LD + "index")]
        if not index_term.endswith(f"^^<{XSD}nonNegativeInteger>"):
            raise AssertionError(
                f"{occurrence}: ordering index has the wrong datatype")
        lexical = index_term.split('"', 2)[1] if index_term.startswith('"') else ""
        if not is_ascii_digits(lexical):
            raise AssertionError(f"{occurrence}: ordering index is not non-negative")
        occurrences[(
            signature(values[iri(LD + "subject")]),
            property_term,
            signature(values[iri(LD + "member")]),
            int(lexical),
        )] += 1
    return occurrences


def validate_ordering_occurrences(core_text: str, order_text: str,
                                  expected_core: str, expected_order: str) -> int:
    actual = ordering_occurrences(core_text, order_text)
    expected = ordering_occurrences(expected_core, expected_order)
    if actual != expected:
        missing = list((expected - actual).elements())
        extra = list((actual - expected).elements())
        raise AssertionError(
            "ordering occurrences differ"
            + (f"; missing {missing[:1]}" if missing else "")
            + (f"; unexpected {extra[:1]}" if extra else ""))
    return sum(expected.values())


def validate_aas_content(dataset: dict, source: dict) -> tuple[int, str, str]:
    core_text, order_text = dataset_text(dataset)
    sink = Lifter(ONTOLOGY, "linked", schema=SCHEMA).lift(source)
    expected_core = serialize(sink, with_graphs=False)
    if canonical_aas_content(core_text) != canonical_aas_content(expected_core):
        raise AssertionError("final JSON-LD bytes do not carry the complete AAS graph")
    return len(parse_nt(expected_core)), core_text, order_text


def without_empty_arrays(value):
    if isinstance(value, list):
        return [without_empty_arrays(item) for item in value]
    if isinstance(value, dict):
        return {
            key: without_empty_arrays(member)
            for key, member in value.items()
            if member != []
        }
    return value


def validate_aas_roundtrip(dataset: dict, source: dict, *,
                           ignore_empty_arrays=False) -> tuple[int, int]:
    triple_count, core_text, order_text = validate_aas_content(dataset, source)
    lowerer = Lowerer(ONTOLOGY, SCHEMA)
    lowerer.load(parse_nt(core_text), parse_nt(order_text) if order_text.strip() else ())
    recovered = lowerer.lower()
    actual = sorted_roots(recovered)
    expected = sorted_roots(source)
    if ignore_empty_arrays:
        # JSON-LD assigns no RDF term to an empty array. Projection TDs retain
        # it in their JSON surface; this RDF round trip proves every represented
        # member and its order without conflating an empty member with content.
        actual = without_empty_arrays(actual)
        expected = without_empty_arrays(expected)
    if canonical(actual) != canonical(expected):
        raise AssertionError("final JSON-LD bytes do not lower to the source AAS")

    sink = Lifter(ONTOLOGY, "linked", schema=SCHEMA).lift(source)
    expected_order = "\n".join(f"{s} {p} {o} ." for s, p, o, _ in sink.quads)
    occurrence_count = validate_ordering_occurrences(
        core_text, order_text, serialize(sink, with_graphs=False), expected_order)
    return triple_count, occurrence_count


def load_type_nodeids() -> dict[str, str]:
    out = {}
    for line in NODEIDS.read_text(encoding="utf-8").splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) >= 3 and parts[2] == "ObjectType":
            out[parts[0]] = f"nsu={I4AAS};i={parts[1]}"
    return out


TYPE_NODEIDS = load_type_nodeids()


def resolve_type(entry: dict) -> str:
    for value in entry.get("@type", []):
        if value in NODE_CLASS_TERMS:
            continue
        if isinstance(value, str) and value.startswith("i4aas:"):
            resolved = TYPE_NODEIDS.get(value.split(":", 1)[1])
            if resolved:
                return resolved
    return f"nsu={UA};i=58"


def expected_node_id(owner: str, path: str | None, namespace: str) -> str:
    encoded_owner = encode_nodeid_component(owner)
    if path is None:
        identifier = f"i4aas3:S:{len(encoded_owner)}:{encoded_owner}"
    else:
        encoded_path = encode_nodeid_component(path)
        identifier = (
            f"i4aas3:E:{len(encoded_owner)}:{len(encoded_path)}:"
            f"{encoded_owner}{encoded_path}"
        )
    decode_i4aas_identifier(identifier)
    return f"nsu={namespace};s={identifier}"


def expected_subject(owner: str, path: str | None) -> str:
    encoded_owner = base64.urlsafe_b64encode(owner.encode("utf-8")).decode("ascii").rstrip("=")
    root = "https://w3id.org/aas-jsonld/subject/v1/" + encoded_owner
    if path is None:
        return root
    encoded_path = base64.urlsafe_b64encode(path.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{root}/node/{encoded_path}"


def child_path(parent: str, element: dict, index: int | None) -> str:
    if index is not None:
        return f"{parent}[{index}]"
    segment = element.get("idShort")
    if segment is None:
        raise AssertionError(f"element outside a list has no idShort below {parent!r}")
    return f"{parent}.{segment}" if parent else segment


def expected_identifiable_browse_names(
        env: dict, digest_function=None) -> dict[tuple[str, int], str]:
    digest_function = digest_function or (
        lambda identifier: hashlib.sha256(
            identifier.encode("utf-8")).hexdigest())
    names = {}
    occupied = set()
    derived = []
    for collection_name, kind_name in IDENTIFIABLE_GROUPS:
        values = env.get(collection_name, []) or []
        identifiers = set()
        for index, value in enumerate(values):
            identifier = value.get("id")
            if not isinstance(identifier, str) or not identifier:
                raise AssertionError(
                    f"{collection_name}[{index}].id is not a non-empty string")
            if identifier in identifiers:
                raise AssertionError(
                    f"{collection_name} contains duplicate identifier {identifier!r}")
            identifiers.add(identifier)
            if "idShort" in value:
                id_short = value["idShort"]
                if not isinstance(id_short, str) or not id_short:
                    raise AssertionError(
                        f"{collection_name}[{index}].idShort is invalid")
                names[(collection_name, index)] = id_short
                occupied.add(id_short)
                continue
            digest = digest_function(identifier)
            derived.append((
                f"{kind_name}_{digest}",
                identifier.encode("utf-8"),
                collection_name,
                index,
            ))
    for base, _, collection_name, index in sorted(
            derived, key=lambda entry: (entry[0], entry[1])):
        name = base
        suffix = 0
        while name in occupied:
            name = f"{base}_{suffix}"
            suffix += 1
        names[(collection_name, index)] = name
        occupied.add(name)
    return names


def expected_projection(env: dict, namespace: str) -> dict[str, dict]:
    out = {}
    browse_names = expected_identifiable_browse_names(env)
    for submodel_index, submodel in enumerate(env.get("submodels", []) or []):
        owner = submodel["id"]
        root = expected_node_id(owner, None, namespace)
        out[root] = {
            "Subject": expected_subject(owner, None),
            "BrowseName": browse_names[("submodels", submodel_index)],
            "TypeDefinition": TYPE_NODEIDS["AASSubmodelType"],
            "Parent": None,
            "Source": None,
            "Reference": None,
            "Index": None,
            "LinkCount": 0,
            "OperationRole": None,
            "OperationIndex": None,
            "ValueNodeId": None,
            "OperationVariables": None,
        }

        def collect(element: dict, parent_path: str, parent: str,
                    index: int | None, reference: str, *,
                    path_override: str | None = None,
                    browse_override: str | None = None,
                    operation_role: str | None = None) -> None:
            model_type = element.get("modelType")
            type_name = ELEMENT_TYPES.get(model_type)
            if type_name is None:
                raise AssertionError(f"no ObjectType expectation for {model_type!r}")
            path = path_override or child_path(parent_path, element, index)
            key = expected_node_id(owner, path, namespace)
            out[key] = {
                "Subject": expected_subject(owner, path),
                "BrowseName": (
                    browse_override if browse_override is not None
                    else str(index) if index is not None else element["idShort"]
                ),
                "TypeDefinition": TYPE_NODEIDS[type_name],
                "Parent": parent,
                "Source": parent,
                "Reference": reference,
                "Index": index,
                "LinkCount": 1,
                "OperationRole": operation_role,
                "OperationIndex": index if operation_role else None,
                "ValueNodeId": key if operation_role else None,
                "OperationVariables": None,
            }
            child_field = CHILD_FIELDS.get(model_type)
            if child_field:
                field, is_list = child_field
                children = element.get(field) or []
                ordered = is_list and element.get("orderRelevant", True)
                child_reference = "HasOrderedComponent" if ordered else "HasComponent"
                for child_index, child in enumerate(children):
                    collect(
                        child, path, key, child_index if is_list else None,
                        child_reference)
            if model_type == "Operation":
                contract = {}
                for role, browse_name in OPERATION_ROLES:
                    if role not in element:
                        continue
                    values = []
                    for role_index, wrapper in enumerate(element.get(role) or []):
                        child = wrapper.get("value") if isinstance(wrapper, dict) else None
                        if not isinstance(child, dict):
                            raise AssertionError(
                                f"{path}.{role}[{role_index}] has no value")
                        if (
                                not isinstance(child.get("idShort"), str)
                                or not child["idShort"]):
                            raise AssertionError(
                                f"{path}.{role}[{role_index}].value has no idShort")
                        operation_path = f"{path}.{role}[{role_index}]"
                        collect(
                            child, path, key, role_index, "HasComponent",
                            path_override=operation_path,
                            browse_override=child["idShort"],
                            operation_role=role)
                        values.append({
                            "ValueNodeId": expected_node_id(
                                owner, operation_path, namespace),
                        })
                    contract[browse_name] = tuple(values)
                out[key]["OperationVariables"] = contract

        for element in submodel.get("submodelElements", []) or []:
            collect(element, "", root, None, "HasComponent")
    return out


def actual_projection(
        dataset: dict, documents: list[tuple[Path, dict]]
) -> tuple[dict[str, dict], list[str]]:
    """Read a multi-TD projection from expanded RDF and public TD links."""
    index = core_rdf_index(dataset)
    errors = []
    out = {}
    by_subject = {}
    node_kinds = {}
    node_subjects = sorted(
        subject for subject, predicates in index.items()
        if UAV + "id" in predicates
    )
    if not node_subjects:
        errors.append("expanded RDF contains no exact uav:id predicates")
    for subject in node_subjects:
        try:
            validate_absolute_uri(subject, "projected node subject")
            id_node = one_rdf(index, subject, UAV + "id")
            node_id = rdf_literal(id_node, f"{subject} uav:id")
            namespace, kind, _, _ = parse_expanded_node_id(
                node_id, f"{subject} uav:id")
            browse_node = one_rdf(index, subject, UAV + "browseName")
            browse_value = rdf_literal(
                browse_node, f"{subject} uav:browseName")
            browse_namespace, browse = parse_qualified_name(
                browse_value, f"{subject} uav:browseName")
            if browse_namespace != namespace:
                raise AssertionError(
                    f"{subject}: BrowseName and NodeId namespaces differ")
            types = {
                obj["value"]
                for obj in index[subject].get(RDF_TYPE, [])
                if obj.get("type") == "IRI"
            }
            if UAV + "object" not in types:
                raise AssertionError(f"{subject}: missing exact uav:object type")
            model_types = sorted(value for value in types if value.startswith(I4AAS))
            if len(model_types) != 1:
                raise AssertionError(
                    f"{subject}: expected one exact I4AAS v3 type, got {model_types}")
            type_name = model_types[0][len(I4AAS):]
            type_definition = TYPE_NODEIDS.get(type_name)
            if type_definition is None:
                raise AssertionError(f"{subject}: unknown I4AAS type {type_name}")
            parent_node = one_rdf(
                index, subject, UAV + "componentOf", required=False)
            parent = None
            if parent_node is not None:
                parent = rdf_literal(parent_node, f"{subject} uav:componentOf")
                parent_namespace, _, _, _ = parse_expanded_node_id(
                    parent, f"{subject} uav:componentOf")
                if parent_namespace != namespace:
                    raise AssertionError(
                        f"{subject}: parent and child namespaces differ")
            index_node = one_rdf(index, subject, UAV + "index", required=False)
            position = None
            if index_node is not None:
                lexical = rdf_literal(index_node, f"{subject} uav:index")
                if index_node.get("datatype") != XSD + "integer":
                    raise AssertionError(
                        f"{subject}: uav:index is not an xsd:integer")
                if not is_ascii_digits(lexical) or (
                        len(lexical) > 1 and lexical.startswith("0")):
                    raise AssertionError(
                        f"{subject}: uav:index is not a canonical "
                        "non-negative integer")
                position = int(lexical)
            modelling = one_rdf(
                index, subject, UAV + "modellingRule", required=False)
            if modelling is not None:
                rule = rdf_literal(modelling, f"{subject} uav:modellingRule")
                if rule not in {
                    "Mandatory", "Optional",
                    "MandatoryPlaceholder", "OptionalPlaceholder",
                }:
                    raise AssertionError(
                        f"{subject}: invalid modelling rule {rule!r}")
        except AssertionError as exc:
            errors.append(str(exc))
            continue
        if node_id in out:
            errors.append(f"duplicate projected ExpandedNodeId {node_id}")
            continue
        by_subject[subject] = node_id
        node_kinds[subject] = kind
        out[node_id] = {
            "Subject": subject,
            "BrowseName": browse,
            "TypeDefinition": type_definition,
            "Parent": parent,
            "Source": None,
            "Reference": None,
            "Index": position,
            "LinkCount": 0,
            "OperationRole": None,
            "OperationIndex": None,
            "ValueNodeId": None,
            "OperationVariables": None,
        }

    roots = [subject for subject, kind in node_kinds.items() if kind == "S"]
    if len(roots) != 1:
        errors.append(f"expected one projected Submodel root, got {len(roots)}")
        return out, errors
    root_id = by_subject[roots[0]]
    if out[root_id]["Parent"] is not None:
        errors.append("projected Submodel root has uav:componentOf")

    by_document_iri = {}
    document_node_ids = {}
    for path, doc in documents:
        subject = doc.get("id")
        node_id = by_subject.get(subject)
        if node_id is None:
            errors.append(f"{path}: TD id is not a projected node subject")
            continue
        self_links = [
            link for link in doc.get("links", [])
            if isinstance(link, dict) and link.get("rel") == "self"
        ]
        if len(self_links) != 1:
            errors.append(f"{node_id}: expected one sibling-TD self link")
            continue
        self_link = self_links[0]
        try:
            target = validate_absolute_uri(
                self_link.get("href"), f"{node_id} self link")
            if target == subject:
                raise AssertionError(
                    f"{node_id}: self link must identify the TD document, "
                    "not reuse the AAS RDF subject")
            if self_link.get("type") != "application/td+json":
                raise AssertionError(
                    f"{node_id}: self link is not application/td+json")
        except AssertionError as exc:
            errors.append(str(exc))
            continue
        if target in by_document_iri:
            errors.append(f"duplicate sibling TD document IRI {target}")
            continue
        by_document_iri[target] = (path, doc, node_id)
        document_node_ids[id(doc)] = node_id

    expected_children = defaultdict(set)
    for node_id, node in out.items():
        if node["Parent"] is not None:
            expected_children[node["Parent"]].add(node_id)

    for path, doc in documents:
        node_id = document_node_ids.get(id(doc))
        if node_id is None:
            continue
        parent = out[node_id]["Parent"]
        component_links = [
            link for link in doc.get("links", [])
            if isinstance(link, dict) and link.get("rel") == "uav:componentOf"
        ]
        if parent is None:
            if component_links:
                errors.append(
                    f"{node_id}: projected root has a componentOf link")
        elif len(component_links) != 1:
            errors.append(
                f"{node_id}: expected one componentOf sibling-TD link, "
                f"got {len(component_links)}")
        else:
            link = component_links[0]
            target = by_document_iri.get(link.get("href"))
            if target is None:
                errors.append(
                    f"{node_id}: componentOf target is not a sibling TD IRI")
            elif target[2] != parent:
                errors.append(
                    f"{node_id}: componentOf link targets {target[2]!r}, "
                    f"expected parent {parent!r}")
            if link.get("type") != "application/td+json":
                errors.append(
                    f"{node_id}: componentOf link is not application/td+json")
            if any(member in link for member in ("anchor", "uav:refId", "uav:refName")):
                errors.append(
                    f"{node_id}: componentOf link carries reference metadata")

        has_components = doc.get("uav:hasComponent", [])
        if not isinstance(has_components, list):
            errors.append(f"{node_id}: uav:hasComponent is not an array")
            has_components = []
        for target_id in has_components:
            try:
                parse_expanded_node_id(
                    target_id, f"{node_id} uav:hasComponent")
            except AssertionError as exc:
                errors.append(str(exc))
        if len(has_components) != len(set(has_components)):
            errors.append(f"{node_id}: uav:hasComponent contains duplicates")
        if set(has_components) != expected_children[node_id]:
            errors.append(
                f"{node_id}: uav:hasComponent does not equal its projected children")

        used_ref_names = set()
        for link in doc.get("links", []):
            if not isinstance(link, dict) or link.get("rel") not in {
                    "ua:HasComponent", "ua:HasOrderedComponent"}:
                continue
            relation = link["rel"]
            target_document = by_document_iri.get(link.get("href"))
            if target_document is None:
                errors.append(
                    f"{node_id}: containment href is not a sibling TD IRI")
                continue
            target_id = target_document[2]
            if link.get("type") != "application/td+json":
                errors.append(
                    f"{node_id}: containment target is not application/td+json")
            if "anchor" in link:
                errors.append(
                    f"{node_id}: containment source must be the containing TD")
            ref_name = link.get("uav:refName")
            if ref_name is not None:
                if ref_name != out[target_id]["BrowseName"]:
                    errors.append(
                        f"{node_id}: containment uav:refName {ref_name!r} "
                        f"does not equal target BrowseName "
                        f"{out[target_id]['BrowseName']!r}")
                elif ref_name in used_ref_names:
                    errors.append(
                        f"{node_id}: containment uav:refName {ref_name!r} "
                        "is not unique")
                used_ref_names.add(ref_name)
            try:
                ref_id = link.get("uav:refId")
                numeric_ref = parse_numeric_node_id(
                    ref_id, f"{node_id} containment uav:refId")
                expected_ref = (
                    49 if relation == "ua:HasOrderedComponent" else 47)
                if numeric_ref != expected_ref:
                    raise AssertionError(
                        f"{node_id}: {relation} requires i={expected_ref}, "
                        f"got {ref_id}")
            except AssertionError as exc:
                errors.append(str(exc))
            node = out[target_id]
            node["LinkCount"] += 1
            if node["LinkCount"] != 1:
                errors.append(f"{target_id}: more than one containment link")
                continue
            node["Source"] = node_id
            node["Reference"] = relation.split(":", 1)[1]

    for node_id, node in out.items():
        expected_count = 0 if node["Parent"] is None else 1
        if node["LinkCount"] != expected_count:
            errors.append(
                f"{node_id}: expected {expected_count} typed containment "
                f"link(s), got {node['LinkCount']}")

    used_operation_children = set()
    for subject, node_id in by_subject.items():
        types = {
            obj["value"]
            for obj in index[subject].get(RDF_TYPE, [])
            if obj.get("type") == "IRI"
        }
        if AAS + "Operation" not in types:
            continue
        contract = {}
        for role, browse_name in OPERATION_ROLES:
            wrappers = index[subject].get(AAS + "Operation/" + role)
            if wrappers is None:
                continue
            indexed_values = []
            for wrapper_node in wrappers:
                wrapper = wrapper_node["value"]
                wrapper_types = {
                    obj["value"]
                    for obj in index[wrapper].get(RDF_TYPE, [])
                    if obj.get("type") == "IRI"
                }
                if AAS + "OperationVariable" not in wrapper_types:
                    errors.append(
                        f"{wrapper}: missing exact aas:OperationVariable type")
                    continue
                values = index[wrapper].get(AAS + "OperationVariable/value", [])
                if len(values) != 1:
                    errors.append(
                        f"{wrapper}: expected one OperationVariable value, "
                        f"got {len(values)}")
                    continue
                target_subject = values[0]["value"]
                target_id = by_subject.get(target_subject)
                if target_id is None:
                    errors.append(
                        f"{wrapper}: ValueNodeId target is not a materialized child")
                    continue
                target = out[target_id]
                if target["Index"] is None:
                    errors.append(
                        f"{target_id}: operation variable child has no uav:index")
                    continue
                if target_id in used_operation_children:
                    errors.append(
                        f"{target_id}: operation variable child is referenced "
                        "more than once")
                    continue
                used_operation_children.add(target_id)
                target["OperationRole"] = role
                target["OperationIndex"] = target["Index"]
                target["ValueNodeId"] = target_id
                indexed_values.append((target["Index"], target_id))
            indexed_values.sort()
            if [position for position, _ in indexed_values] != list(
                    range(len(indexed_values))):
                errors.append(
                    f"{node_id}: {role} indices are not contiguous from zero")
            contract[browse_name] = tuple(
                {"ValueNodeId": value} for _, value in indexed_values)
        out[node_id]["OperationVariables"] = contract
    return out, errors


def compare_projection(
        env: dict, dataset: dict, documents: list[tuple[Path, dict]]
) -> tuple[list[str], int, int]:
    actual, errors = actual_projection(dataset, documents)
    root_ids = []
    for node_id in actual:
        try:
            namespace, kind, _, _ = parse_expanded_node_id(
                node_id, "projected root candidate")
        except AssertionError:
            continue
        if kind == "S":
            root_ids.append((node_id, namespace))
    if len(root_ids) != 1:
        return errors + [
            f"expected one independently parsed Submodel root, got {len(root_ids)}"
        ], 0, 0
    expected = expected_projection(env, root_ids[0][1])
    for key in sorted(set(expected) - set(actual)):
        errors.append(f"missing projected node {key}")
    for key in sorted(set(actual) - set(expected)):
        errors.append(f"unexpected projected node {key}")
    fields = ("Subject", "BrowseName", "TypeDefinition", "Parent", "Source",
              "Reference", "Index", "LinkCount", "OperationRole",
              "OperationIndex", "ValueNodeId", "OperationVariables")
    for key in sorted(set(expected) & set(actual)):
        for field in fields:
            if expected[key].get(field) != actual[key].get(field):
                errors.append(
                    f"{key}: {field} expected {expected[key].get(field)!r}, "
                    f"got {actual[key].get(field)!r}")
    edges = sum(node["Parent"] is not None for node in expected.values())
    indices = sum(node["Index"] is not None for node in expected.values())
    return errors, edges, indices


def validate_projection(
        env: dict, dataset: dict, documents: list[tuple[Path, dict]]
) -> tuple[int, int]:
    errors, edges, indices = compare_projection(env, dataset, documents)
    if errors:
        raise AssertionError(errors[0])
    return edges, indices


def validate_projection_bundle(
        serialized: list[tuple[str | Path, str]], source: dict) -> dict:
    if not serialized:
        raise AssertionError("a projection bundle must contain at least one TD")
    documents = []
    datasets = []
    seen_paths = set()
    for raw_path, text in serialized:
        path = Path(raw_path).resolve()
        if path in seen_paths:
            raise AssertionError(f"projection bundle repeats {path}")
        seen_paths.add(path)
        doc = json.loads(text)
        validate_td(doc)
        validate_context_strategy(doc, path, True)
        validate_node_class_domains(doc)
        validate_object_form(doc)
        dataset = process_jsonld(doc, path)
        if not any(dataset.values()):
            raise AssertionError(f"{path}: JSON-LD processing produced an empty dataset")
        validate_expanded_node_class_domains(dataset, doc)
        validate_expanded_namespaces(dataset, doc, True)
        validate_td_identifier(doc, dataset)
        documents.append((path, doc))
        datasets.append((path, dataset))

    merged = merge_document_datasets(datasets)
    edges, indices = validate_projection(source, merged, documents)
    projected_source = {"submodels": source.get("submodels", []) or []}
    triples, occurrences = validate_aas_roundtrip(
        merged, projected_source, ignore_empty_arrays=True)
    return {
        "files": len(documents),
        "tds": len(documents),
        "triples": triples,
        "edges": edges,
        "indices": indices,
        "occurrences": occurrences,
    }


def projection_bundle_paths(root_path: Path) -> list[Path]:
    object_dir = Path(str(root_path).removesuffix(".td.jsonld") + ".objects")
    return [root_path, *sorted(object_dir.glob("*.td.jsonld"))]


def load_projection_bundle(root_path: Path) -> list[tuple[Path, object]]:
    paths = projection_bundle_paths(root_path)
    if not paths[0].is_file():
        raise AssertionError(f"projection root is missing: {paths[0]}")
    return [
        (path, json.loads(path.read_text(encoding="utf-8")))
        for path in paths
    ]


def clone_bundle(
        documents: list[tuple[Path, object]]
) -> list[tuple[Path, object]]:
    return [
        (path, json.loads(json.dumps(doc)))
        for path, doc in documents
    ]


def serialized_bundle(
        documents: list[tuple[Path, object]]
) -> list[tuple[Path, str]]:
    return [(path, json.dumps(doc)) for path, doc in documents]


def expect_bundle_mutation(
        name: str, documents: list[tuple[Path, object]], source: dict
) -> int:
    try:
        validate_projection_bundle(serialized_bundle(documents), source)
    except Exception as exc:
        print(f"  caught: {name} ({type(exc).__name__}: {exc})")
        return 1
    raise AssertionError(f"{name}: mutation escaped projection validation")


def self_href(doc: dict) -> str:
    matches = [
        link["href"] for link in doc.get("links", [])
        if isinstance(link, dict) and link.get("rel") == "self"
    ]
    if len(matches) != 1:
        raise AssertionError("expected exactly one self link")
    return matches[0]


def projection_mutation_test() -> int:
    source_path = FIXTURES / "ordering-and-nesting.json"
    root_path = AAS_DIR / "examples" / "wot" / "ordering-and-nesting.td.jsonld"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    original = load_projection_bundle(root_path)
    caught = 0

    parent = clone_bundle(original)
    child = next(doc for _, doc in parent if doc.get("uav:componentOf"))
    original_parent = child["uav:componentOf"][0]
    wrong_parent = next(
        doc["uav:id"] for _, doc in parent
        if doc["uav:id"] not in {child["uav:id"], original_parent})
    child["uav:componentOf"] = [wrong_parent]
    caught += expect_bundle_mutation(
        "replace containment parent", parent, source)

    source_link = clone_bundle(original)
    parent_doc = next(
        doc for _, doc in source_link
        if any(
            isinstance(link, dict)
            and link.get("rel") in {"ua:HasComponent", "ua:HasOrderedComponent"}
            for link in doc.get("links", [])))
    typed_link = next(
        link for link in parent_doc["links"]
        if link.get("rel") in {"ua:HasComponent", "ua:HasOrderedComponent"})
    typed_link["href"] = next(
        self_href(doc) for _, doc in source_link
        if self_href(doc) not in {typed_link["href"], self_href(parent_doc)})
    caught += expect_bundle_mutation(
        "replace containment source target", source_link, source)

    subject = clone_bundle(original)
    child = next(doc for _, doc in subject if doc.get("uav:componentOf"))
    child["id"] += "-wrong-subject"
    caught += expect_bundle_mutation(
        "replace projected element subject", subject, source)

    index = clone_bundle(original)
    indexed = next(doc for _, doc in index if "uav:index" in doc)
    indexed["uav:index"] += 1
    caught += expect_bundle_mutation("replace uav:index", index, source)

    containment_target = clone_bundle(original)
    parent_doc = next(
        doc for _, doc in containment_target
        if any(
            link.get("rel") in {"ua:HasComponent", "ua:HasOrderedComponent"}
            for link in doc.get("links", []) if isinstance(link, dict)))
    typed_link = next(
        link for link in parent_doc["links"]
        if link.get("rel") in {"ua:HasComponent", "ua:HasOrderedComponent"})
    target_doc = next(
        doc for _, doc in containment_target
        if self_href(doc) == typed_link["href"])
    typed_link["href"] = target_doc["id"]
    caught += expect_bundle_mutation(
        "replace sibling TD containment target with RDF subject",
        containment_target, source)

    missing_sibling = clone_bundle(original)
    removed = next(
        doc for _, doc in missing_sibling if doc.get("uav:componentOf"))
    missing_sibling = [
        (path, doc) for path, doc in missing_sibling if doc is not removed
    ]
    caught += expect_bundle_mutation(
        "remove referenced sibling TD", missing_sibling, source)
    return caught


def final_bytes_mutation_test() -> int:
    source_path = FIXTURES / "ordering-and-nesting.json"
    root_path = AAS_DIR / "examples" / "wot" / "ordering-and-nesting.td.jsonld"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    original = load_projection_bundle(root_path)
    mutations = []

    missing_context = clone_bundle(original)
    root = missing_context[0][1]
    replaced = False
    for index, entry in enumerate(root["@context"]):
        if isinstance(entry, str) and entry != TD_CONTEXT_URL:
            root["@context"][index] = "https://example.invalid/missing-context"
            replaced = True
            break
    if not replaced:
        raise AssertionError("context mutation found no bundled context")
    mutations.append(("replace bundled context with a 404 URL", missing_context))

    array_container = clone_bundle(original)
    array_container[0] = (array_container[0][0], [array_container[0][1]])
    mutations.append(("wrap the TD object in an array", array_container))

    dual_identifier = clone_bundle(original)
    dual_identifier[0][1]["@id"] = dual_identifier[0][1]["id"]
    mutations.append(("carry both id and @id", dual_identifier))

    overridden_id_alias = clone_bundle(original)
    for entry in overridden_id_alias[0][1]["@context"]:
        if isinstance(entry, dict):
            entry.pop("id", None)
    mutations.append(
        ("let a bundled context override the TD id alias", overridden_id_alias))

    schema_invalid = clone_bundle(original)
    schema_invalid[0][1].pop("security", None)
    mutations.append(("remove TD security", schema_invalid))

    return sum(
        expect_bundle_mutation(name, documents, source)
        for name, documents in mutations
    )


def aas_content_mutation_test() -> int:
    source_path = FIXTURES / "every-element-type.json"
    root_path = AAS_DIR / "examples" / "wot" / "every-element-type.td.jsonld"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    documents = clone_bundle(load_projection_bundle(root_path))
    blobs = [
        doc for _, doc in documents
        if "aas:Blob" in type_terms(doc.get("@type"))
    ]
    if len(blobs) != 1:
        raise AssertionError(f"datatype mutation expected one Blob, got {len(blobs)}")
    value = blobs[0]["aas:Blob/value"]
    if not isinstance(value, dict) or "@value" not in value:
        raise AssertionError("datatype mutation requires an expanded JSON-LD value")
    value["@type"] = XSD + "string"
    return expect_bundle_mutation(
        "replace AAS literal datatype", documents, source)


def expanded_namespace_mutation_test() -> int:
    source_path = FIXTURES / "ordering-and-nesting.json"
    root_path = AAS_DIR / "examples" / "wot" / "ordering-and-nesting.td.jsonld"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    original = load_projection_bundle(root_path)
    mutations = []

    for prefix in ("uav", "i4aas"):
        rebound = clone_bundle(original)
        inline = next(
            entry for entry in rebound[0][1]["@context"]
            if isinstance(entry, dict))
        if prefix == "uav":
            inline["uav:id"] = {
                "@id": "https://example.org/wrong-uav/id",
            }
        else:
            inline[prefix] = f"https://example.org/wrong-{prefix}/"
        mutations.append((f"rebind {prefix}", rebound))

    malformed_nodeid = clone_bundle(original)
    malformed_nodeid[0][1]["uav:id"] = "nsu=not a uri"
    mutations.append(("malform nsu= ExpandedNodeId", malformed_nodeid))

    subject_href = clone_bundle(original)
    subject_href[0][1]["forms"][0]["href"] = subject_href[0][1]["id"]
    mutations.append(("replace OPC UA form href with RDF subject", subject_href))

    wrong_node = clone_bundle(original)
    wrong_node[0][1]["forms"][0]["href"] = wrong_node[1][1]["forms"][0]["href"]
    mutations.append(("address the wrong OPC UA NodeId", wrong_node))

    return sum(
        expect_bundle_mutation(name, documents, source)
        for name, documents in mutations
    )


def form_encoding_mutation_test() -> int:
    source_path = FIXTURES / "identifiable-without-idshort.json"
    root_path = (
        AAS_DIR / "examples" / "wot"
        / "identifiable-without-idshort.td.jsonld")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    documents = clone_bundle(load_projection_bundle(root_path))
    href = documents[0][1]["forms"][0]["href"]
    if "%250A" not in href:
        raise AssertionError("form encoding mutation found no URI-layer control escape")
    documents[0][1]["forms"][0]["href"] = href.replace("%250A", "%0A", 1)
    return expect_bundle_mutation(
        "remove the URI layer from an ExpandedNodeId percent escape",
        documents, source)


def node_class_domain_mutation_test() -> int:
    root_path = AAS_DIR / "examples" / "wot" / "ordering-and-nesting.td.jsonld"
    valid = load_projection_bundle(root_path)[0][1]
    valid = json.loads(json.dumps(valid))
    form_href = valid["forms"][0]["href"]
    valid["properties"] = {
        "value": {
            "@type": "uav:variable",
            "type": "string",
            "forms": [{"href": form_href, "op": "readproperty"}],
        },
    }
    valid["actions"] = {
        "invoke": {
            "@type": "uav:method",
            "forms": [{"href": form_href, "op": "invokeaction"}],
        },
    }
    validate_td(valid)
    validate_node_class_domains(valid)
    validate_expanded_node_class_domains(
        process_jsonld(valid, root_path), valid)

    mutations = []
    nested_object = json.loads(json.dumps(valid))
    nested_object["properties"]["value"]["@type"] = "uav:object"
    mutations.append(("place uav:object in TD properties", nested_object))
    absolute_nested_object = json.loads(json.dumps(valid))
    absolute_nested_object["properties"]["value"]["@type"] = [
        "uav:variable", UAV + "object",
    ]
    mutations.append(
        ("smuggle the absolute uav:object IRI into a property",
         absolute_nested_object))
    property_without_variable = json.loads(json.dumps(valid))
    property_without_variable["properties"]["value"]["@type"] = "aas:Property"
    mutations.append(("remove uav:variable from a property", property_without_variable))
    action_as_variable = json.loads(json.dumps(valid))
    action_as_variable["actions"]["invoke"]["@type"] = "uav:variable"
    mutations.append(("replace uav:method action with uav:variable", action_as_variable))
    root_as_variable = json.loads(json.dumps(valid))
    root_as_variable["@type"] = [
        value if value != "uav:object" else "uav:variable"
        for value in root_as_variable["@type"]
    ]
    mutations.append(("replace Thing-level uav:object", root_as_variable))

    caught = 0
    for name, mutated in mutations:
        try:
            validate_td(mutated)
            validate_node_class_domains(mutated)
            validate_expanded_node_class_domains(
                process_jsonld(mutated, root_path), mutated)
        except Exception as exc:
            print(f"  caught: {name} ({type(exc).__name__}: {exc})")
            caught += 1
        else:
            raise AssertionError(f"{name}: mutation escaped node-class validation")
    return caught


def operation_variable_mutation_test() -> int:
    source_path = FIXTURES / "every-element-type.json"
    root_path = AAS_DIR / "examples" / "wot" / "every-element-type.td.jsonld"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    original = load_projection_bundle(root_path)
    caught = 0

    def operation(documents):
        matches = [
            doc for _, doc in documents
            if "aas:Operation/inputVariables" in doc
        ]
        if len(matches) != 1:
            raise AssertionError(f"expected one Operation TD, got {len(matches)}")
        return matches[0]

    wrong_role = clone_bundle(original)
    role_operation = operation(wrong_role)
    moved = role_operation["aas:Operation/inputVariables"].pop(1)
    role_operation["aas:Operation/outputVariables"].append(moved)
    caught += expect_bundle_mutation(
        "move an Operation variable to another role", wrong_role, source)

    wrong_order = clone_bundle(original)
    order_operation = operation(wrong_order)
    second_subject = order_operation["aas:Operation/inputVariables"][1][
        "aas:OperationVariable/value"]["@id"]
    second_entry = next(doc for _, doc in wrong_order if doc.get("id") == second_subject)
    second_entry["uav:index"] = 0
    caught += expect_bundle_mutation(
        "duplicate an Operation variable index", wrong_order, source)

    wrong_value_node = clone_bundle(original)
    value_operation = operation(wrong_value_node)
    output_subject = value_operation["aas:Operation/outputVariables"][0][
        "aas:OperationVariable/value"]["@id"]
    value_operation["aas:Operation/inputVariables"][0][
        "aas:OperationVariable/value"]["@id"] = output_subject
    caught += expect_bundle_mutation(
        "replace an Operation ValueNodeId target", wrong_value_node, source)

    role_ref_name = clone_bundle(original)
    role_operation = operation(role_ref_name)
    child_subject = role_operation["aas:Operation/inputVariables"][0][
        "aas:OperationVariable/value"]["@id"]
    child_doc = next(doc for _, doc in role_ref_name if doc.get("id") == child_subject)
    target_href = self_href(child_doc)
    relation = next(
        link for link in role_operation["links"]
        if link.get("href") == target_href
        and link.get("rel") in {"ua:HasComponent", "ua:HasOrderedComponent"})
    relation["uav:refName"] = "0"
    caught += expect_bundle_mutation(
        "use an Operation role index as uav:refName", role_ref_name, source)
    return caught


def ordering_occurrence_mutation_test() -> int:
    templates = load_template_sources()
    source = templates["digital-nameplate"]
    path = AAS_DIR / "examples" / "jsonld" / "digital-nameplate.aas.jsonld"
    doc = json.loads(path.read_text(encoding="utf-8"))

    def mutate(node) -> bool:
        if isinstance(node, dict):
            value = node.get("aasld:property")
            if isinstance(value, dict) and "@id" in value:
                value["@id"] = "https://example.org/foreign/orderingProperty"
                return True
            return any(mutate(value) for value in node.values())
        if isinstance(node, list):
            return any(mutate(value) for value in node)
        return False

    if not mutate(doc):
        raise AssertionError("ordering mutation found no occurrence property")
    dataset = process_jsonld(doc, path)
    core_text, order_text = dataset_text(dataset)
    sink = Lifter(ONTOLOGY, "linked", schema=SCHEMA).lift(source)
    expected_core = serialize(sink, with_graphs=False)
    expected_order = "\n".join(f"{s} {p} {o} ." for s, p, o, _ in sink.quads)
    try:
        validate_ordering_occurrences(
            core_text, order_text, expected_core, expected_order)
    except AssertionError as exc:
        if "ordering occurrences differ" not in str(exc):
            raise
        print("  caught: replace ordering occurrence property (AssertionError)")
        return 1
    raise AssertionError(
        "replace ordering occurrence property: mutation escaped occurrence validation")


def nested_reference_order_mutation_test() -> int:
    source_path = FIXTURES / "ordering-and-nesting.json"
    path = AAS_DIR / "examples" / "wot" / "ordering-and-nesting.td.jsonld"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    documents = clone_bundle(load_projection_bundle(path))

    def mutate(node) -> bool:
        if isinstance(node, dict):
            prop = node.get(LD + "property")
            if (
                    isinstance(prop, dict)
                    and prop.get("@id") == AAS + "Reference/keys"):
                index = node.get(LD + "index")
                if not isinstance(index, dict) or "@value" not in index:
                    raise AssertionError(
                        "Reference.keys occurrence has no explicit index")
                index["@value"] = "1"
                return True
            return any(mutate(value) for value in node.values())
        if isinstance(node, list):
            return any(mutate(value) for value in node)
        return False

    if not any(mutate(doc) for _, doc in documents):
        raise AssertionError("nested ordering mutation found no Reference.keys occurrence")
    return expect_bundle_mutation(
        "replace nested Reference.keys occurrence index", documents, source)


def mutation_test() -> int:
    return (
        projection_mutation_test()
        + final_bytes_mutation_test()
        + aas_content_mutation_test()
        + expanded_namespace_mutation_test()
        + form_encoding_mutation_test()
        + node_class_domain_mutation_test()
        + operation_variable_mutation_test()
        + ordering_occurrence_mutation_test()
        + nested_reference_order_mutation_test()
    )


def validate_bytes(path: Path, text: str, *, td: bool = False,
                   source: dict | None = None, projection: bool = False) -> dict:
    path = Path(path)
    if projection:
        if not td or source is None:
            raise AssertionError(
                "projection validation requires a TD and its source environment")
        serialized = [(path, text)]
        for child_path in projection_bundle_paths(path)[1:]:
            serialized.append(
                (child_path, child_path.read_text(encoding="utf-8")))
        return validate_projection_bundle(serialized, source)
    doc = json.loads(text)
    if td:
        validate_td(doc)
        validate_node_class_domains(doc)
    validate_context_strategy(doc, path, td)
    dataset = process_jsonld(doc, path)
    if not any(dataset.values()):
        raise AssertionError("JSON-LD processing produced an empty dataset")
    if td:
        validate_expanded_node_class_domains(dataset, doc)
    validate_expanded_namespaces(dataset, doc if isinstance(doc, dict) else None, td)
    result = {"graphs": len(dataset)}
    if td:
        validate_td_identifier(doc, dataset)
    if source is not None:
        triples, occurrences = validate_aas_roundtrip(dataset, source)
        result.update(triples=triples, occurrences=occurrences)
    return result


def load_template_sources() -> dict[str, dict]:
    out = {}
    for name, path in TEMPLATE_SOURCES:
        if path.is_file():
            out[name] = json.loads(path.read_text(encoding="utf-8"))
    return out


def validate_committed() -> tuple[int, int, int, int, int, int]:
    verify_vendor()
    templates = load_template_sources()
    missing_templates = [
        name for name, _ in TEMPLATE_SOURCES
        if name not in templates
    ]
    if missing_templates:
        raise AssertionError(
            "authoritative template source is missing for: " + ", ".join(missing_templates))
    checked = tds = projected = edges = indices = occurrences = 0
    seen_td_paths = set()
    examples = AAS_DIR / "examples"
    for path in sorted((examples / "jsonld").glob("*.aas.jsonld")):
        source = templates.get(path.name.removesuffix(".aas.jsonld"))
        result = validate_bytes(
            path, path.read_text(encoding="utf-8"), source=source)
        checked += 1
        occurrences += result.get("occurrences", 0)
    for path in sorted((examples / "wot" / "minimal").glob("*.td.jsonld")):
        source = templates.get(path.name.removesuffix(".td.jsonld"))
        result = validate_bytes(
            path, path.read_text(encoding="utf-8"), td=True, source=source)
        checked += 1
        tds += 1
        seen_td_paths.add(path.resolve())
        occurrences += result.get("occurrences", 0)
    for path in sorted((examples / "wot" / "submodels").glob("*.td.jsonld")):
        source = templates.get(path.name.removesuffix(".td.jsonld"))
        if source is None:
            raise AssertionError(f"{path}: no authoritative template source")
        bundle_paths = projection_bundle_paths(path)
        serialized = [
            (bundle_path, bundle_path.read_text(encoding="utf-8"))
            for bundle_path in bundle_paths
        ]
        result = validate_projection_bundle(serialized, source)
        checked += result["files"]
        tds += result["tds"]
        projected += 1
        edges += result["edges"]
        indices += result["indices"]
        occurrences += result["occurrences"]
        seen_td_paths.update(bundle_path.resolve() for bundle_path in bundle_paths)
    for path in sorted((examples / "wot").glob("*.td.jsonld")):
        source_path = FIXTURES / f"{path.name.removesuffix('.td.jsonld')}.json"
        source = json.loads(source_path.read_text(encoding="utf-8"))
        bundle_paths = projection_bundle_paths(path)
        serialized = [
            (bundle_path, bundle_path.read_text(encoding="utf-8"))
            for bundle_path in bundle_paths
        ]
        result = validate_projection_bundle(serialized, source)
        checked += result["files"]
        tds += result["tds"]
        projected += 1
        edges += result["edges"]
        indices += result["indices"]
        occurrences += result["occurrences"]
        seen_td_paths.update(bundle_path.resolve() for bundle_path in bundle_paths)
    all_td_paths = {
        path.resolve()
        for path in (examples / "wot").rglob("*.td.jsonld")
    }
    orphans = sorted(all_td_paths - seen_td_paths)
    if orphans:
        raise AssertionError(
            f"unvalidated or orphaned Thing Description: {orphans[0]}")
    return checked, tds, projected, edges, indices, occurrences


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mutations", action="store_true",
                        help="also prove projection and final-byte mutations are rejected")
    args = parser.parse_args()
    checked, tds, projected, edges, indices, occurrences = validate_committed()
    print(f"validated final bytes: {checked} file(s)")
    print(f"  W3C TD 1.1 schema: {tds}")
    print(f"  complete hierarchy/order projections: {projected}")
    print(f"  containment edges compared: {edges}")
    print(f"  array/list indices compared: {indices}")
    print(f"  ordering occurrences compared: {occurrences}")
    if args.mutations:
        print(f"mutations caught: {mutation_test()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
