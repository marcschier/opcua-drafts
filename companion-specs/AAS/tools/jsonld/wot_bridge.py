#!/usr/bin/env python3
"""
Generate Thing Descriptions from an AAS environment, project them, and compare
the result against the AddressSpace the AAS companion specification defines.

Annex F of `OPC-UA-AAS.md` claims that a Thing Description carrying the AAS
vocabulary, loaded through the WoT Connectivity registry, materializes the same
hierarchy and order as clause 5.6. This tool emits the Thing Descriptions,
applies the projection rules the annex states, and diffs every projected node,
containment source and parent, ReferenceType and list index against the
AddressSpace `roundtrip_check.py` independently materializes.

Two things the design review insisted on are built in.

**The claim is scoped to a subgraph.** A registry adds nodes of its own - the
document resource, its versions, the `HasWoTProjection` reference. Comparing the
whole AddressSpace would fail for reasons that have nothing to do with the
mapping, so the comparison covers the identified projection subgraph only.

**The type binding is not assumed.** With the vocabulary as published,
`uav:congruentType` is reconciliation metadata and does not set a
`HasTypeDefinition`. The generator therefore names the ObjectType in `@type`, and
the projector honours it only when `--proposed` is passed. Without that flag the
run reports what the published vocabulary actually achieves, which is less.

`--form term` writes the same binding as a dedicated `uav:typeref` member
instead. That form was proposed first and withdrawn; the option is kept because
the two produce identical node sets, and that is the measurement that decided
between them.

Usage:
    python wot_bridge.py <environment.json> [--proposed] [--form attype|term]
                         [--dump-dir output-directory]
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.parse
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
AAS_TOOLS = os.path.normpath(os.path.join(HERE, ".."))
NODESET = os.path.normpath(
    os.path.join(AAS_TOOLS, "..", "Opc.Ua.I4AAS.NodeSet2.xml"))
sys.path.insert(0, AAS_TOOLS)

import roundtrip_check as rt  # noqa: E402
from jsonld.lift import Ontology, subject_iri  # noqa: E402

UA = "http://opcfoundation.org/UA/"
AAS_NS = "https://admin-shell.io/aas/3/0/"
LD = "https://w3id.org/aas-jsonld/"
ORDER_GRAPH = LD + "graph/order"
XSD = "http://www.w3.org/2001/XMLSchema#"
NODESET_XMLNS = "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"


def load_model_uri():
    model = ET.parse(NODESET).find(f"{{{NODESET_XMLNS}}}Models/"
                                   f"{{{NODESET_XMLNS}}}Model")
    if model is None or not model.get("ModelUri"):
        raise ValueError(f"{NODESET}: no model URI")
    return model.get("ModelUri")


I4AAS = load_model_uri()

# The vocabulary, read from the pinned ontology rather than restated here.
ONTOLOGY = Ontology()

# The ObjectType each metamodel class materializes as, from clause 6. Read from
# the round-trip reference implementation so the two cannot disagree.
ELEMENT_TYPES = dict(rt.ELEMENT_TYPES)

OPERATION_ROLES = (
    ("inputVariables", "InputVariables"),
    ("outputVariables", "OutputVariables"),
    ("inoutputVariables", "InoutputVariables"),
)

# Draft NodeIds of the I4AAS ObjectTypes, from Opc.Ua.I4AAS.NodeIds.csv.
TYPE_NODEIDS = {}


def load_type_nodeids():
    path = os.path.normpath(os.path.join(HERE, "..", "..", "Opc.Ua.I4AAS.NodeIds.csv"))
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3 and parts[2] == "ObjectType":
                TYPE_NODEIDS[parts[0]] = f"nsu={I4AAS};i={parts[1]}"
    return TYPE_NODEIDS


def typeref(type_name):
    """The single form a document carries: the prefix-qualified BrowseName.

    One form, not two. A document that carried both a compact name and an
    ExpandedNodeId would have to keep them consistent, and the pair adds nothing:
    the prefix binds to the NamespaceUri in the `@context`, so the compact name
    already identifies the type unambiguously wherever the model is loaded.
    """
    return f"i4aas:{type_name}"


def resolve_typeref(value):
    """Resolve a `uav:typeref` the way a Server does: by name, in what it has.

    The candidate space is the loaded AddressSpace. This resolves the compact
    name through the NodeId table the specification publishes, which is the same
    lookup a Server performs against its own namespace table - it does not read
    back a NodeId the generator wrote.
    """
    if not value or ":" not in value:
        return None
    prefix, name = value.split(":", 1)
    if prefix != "i4aas":
        return None
    return TYPE_NODEIDS.get(name)


# The node-class terms of the Binding. A member of `@type` that is one of these
# says which NodeClass the entry projects to; it is never a TypeDefinition.
NODE_CLASS_TERMS = {"uav:object", "uav:variable", "uav:method", "uav:objectType",
                    "uav:variableType", "uav:referenceType", "uav:dataType", "uav:view"}


def resolve_attype(types):
    """Resolve a TypeDefinition carried in `@type`, the way a Server would.

    `@type` already carries the NodeClass term, so the TypeDefinition is the
    member that is not one. Resolution is against what the Server has: a member
    naming a type it holds is the TypeDefinition, and one it does not hold is an
    ordinary semantic annotation, which is what `@type` means everywhere else.
    """
    for value in types or []:
        if value in NODE_CLASS_TERMS:
            continue
        resolved = resolve_typeref(value)
        if resolved:
            return resolved
    return None


# ---------------------------------------------------------------------------
# Generation: an AAS environment becomes one Thing Description per Submodel
# ---------------------------------------------------------------------------
# The NamespaceUri a Server materializes instances into. A document carries a
# real NamespaceUri, because `uav:id` is an ExpandedNodeId in the string form of
# OPC 10000-6 and nothing in the WoT drafts defines a placeholder syntax for one.
# A document that cannot know the target namespace omits `uav:id` instead; see
# Annex F.5.
INSTANCE_NS = "https://example.com/aas/instances/"
OPC_ENDPOINT = "opc.tcp://example.com:4840"
TD_DOCUMENT_NS = "https://w3id.org/aas-jsonld/td/v1/"


def expanded_node_id(owner_id, path=None, namespace=None):
    """Clause 5.3: the String NodeId, qualified by the instance NamespaceUri."""
    ident = rt.node_identifier("E" if path is not None else "S", owner_id, path)
    return f"nsu={namespace or INSTANCE_NS};s={ident}"


def browse_name(name, namespace=None):
    return f"nsu={namespace or INSTANCE_NS};{name}"


def node_iri(owner_id, path=None):
    """The JSON-LD subject of a projected root or contained node.

    Root subjects use clause 2.2 exactly.  Contained nodes occupy a child
    namespace below that subject; base64url keeps every idShortPath in one path
    segment and makes the child namespace disjoint from all root subjects.
    """
    root = subject_iri(owner_id)
    if path is None:
        return root
    encoded = base64.urlsafe_b64encode(path.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{root}/node/{encoded}"


def td_document_iri(owner_id, path=None):
    encoded_owner = base64.urlsafe_b64encode(
        owner_id.encode("utf-8")).decode("ascii").rstrip("=")
    root = TD_DOCUMENT_NS + encoded_owner
    if path is None:
        return root
    encoded_path = base64.urlsafe_b64encode(
        path.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{root}/node/{encoded_path}"


def opc_form_href(node_id, endpoint=OPC_ENDPOINT):
    encoded = urllib.parse.quote(
        node_id, safe=":/;=,!$'()*+-._~@")
    return endpoint.rstrip("/") + "/?id=" + encoded


class AASRenderState:
    """Assign nested blank nodes and emit the complete AAS ordering graph."""

    def __init__(self):
        self.counter = 0
        self.occurrences = []

    def blank(self, label):
        self.counter += 1
        return f"_:aas-{label}-{self.counter}"

    def add_occurrence(self, subject, prop, member, index):
        if not subject:
            raise ValueError(f"{prop['iri']}: ordered value has no RDF subject")
        if isinstance(member, dict) and "@id" in member:
            member_term = {"@id": member["@id"]}
        elif isinstance(member, dict) and "@value" in member:
            member_term = dict(member)
        elif prop.get("kind") == "ObjectProperty":
            member_term = {"@id": member}
        else:
            member_term = member
        self.occurrences.append({
            "@id": self.blank("occurrence"),
            "@type": LD + "Occurrence",
            LD + "subject": {"@id": subject},
            LD + "property": {"@id": prop["iri"]},
            LD + "member": member_term,
            LD + "index": {
                "@value": str(index),
                "@type": XSD + "nonNegativeInteger",
            },
        })

    def attach(self, document):
        if self.occurrences:
            document.setdefault("@included", []).append({
                "@id": ORDER_GRAPH,
                "@graph": self.occurrences,
            })


def aas_members(node, skip_field=None, cls=None, *, subject=None, state=None):
    """The node's own AAS content, as compact JSON-LD in the AAS vocabulary.

    Without this a Thing Description carries a node skeleton and no Asset
    Administration Shell: the `aas` prefix would be declared and never used, and
    the document would not be an AAS by clause 1 of the JSON-LD mapping. The
    child collection is skipped, because each child is a node of its own and is
    referenced rather than nested.

    A nested object that carries no `modelType` - a `Reference`, a `Key`, a
    `Qualifier`, a language string - takes its class from the declared range of
    the property that reached it, which is clause 2.3 of the JSON-LD mapping.
    """
    cls = cls or node.get("modelType")
    skipped = ({skip_field} if isinstance(skip_field, str)
               else set(skip_field or ()))
    out = {}
    if cls:
        out["@type"] = compact(f"{AAS_NS}{cls}")
    for key, value in node.items():
        if key == "modelType" or key in skipped:
            continue
        prop = ONTOLOGY.resolve(cls, key) if cls else None
        if prop is None:
            continue
        rendered = render_value(value, prop, subject=subject, state=state)
        if rendered is not None:
            out[compact(prop["iri"])] = rendered
    return out


def render_value(value, prop, *, subject=None, state=None):
    rng = (prop.get("range") or "").split(":")[-1]
    if isinstance(value, list):
        rendered = []
        for index, item in enumerate(value):
            member = render_value(item, prop, state=state)
            if member is None:
                continue
            rendered.append(member)
            if state is not None:
                state.add_occurrence(subject, prop, member, index)
        return rendered or None
    if isinstance(value, dict):
        nested_subject = state.blank("node") if state is not None else None
        members = aas_members(
            value,
            cls=value.get("modelType") or rng,
            subject=nested_subject,
            state=state,
        )
        if nested_subject is not None:
            members = {"@id": nested_subject, **members}
        return members or None
    if prop.get("kind") == "DatatypeProperty":
        if isinstance(value, bool):
            lexical = "true" if value else "false"
        else:
            lexical = str(value)
        return {
            "@value": lexical,
            "@type": XSD + (rng or "string"),
        }
    if rng in ONTOLOGY.enums:
        member = enum_individual(rng, value)
        return {"@id": compact(member)} if member else None
    return value


def enum_individual(enum_name, value):
    members = ONTOLOGY.enums.get(enum_name, [])
    bare = str(value).split(":", 1)[-1]
    joined = "".join(part.capitalize() for part in bare.split("_"))
    lowered = {m.lower(): m for m in members}
    for candidate in (str(value), bare, bare[:1].upper() + bare[1:], joined):
        if candidate in members:
            return f"{AAS_NS}{enum_name}/{candidate}"
    for candidate in (bare.lower(), joined.lower()):
        if candidate in lowered:
            return f"{AAS_NS}{enum_name}/{lowered[candidate]}"
    return None


def compact(iri):
    return "aas:" + iri[len(AAS_NS):] if iri.startswith(AAS_NS) else iri


def merge_aas(entry, node, skip_field=None, state=None):
    """Add the node's AAS content to an affordance, keeping the `@type` list.

    `@type` already carries the NodeClass term and the ObjectType; the AAS class
    joins them rather than replacing them, so the same member says what the node
    projects to and what it is in the metamodel.
    """
    subject = entry.get("@id") or entry.get("id")
    members = aas_members(
        node, skip_field, subject=subject, state=state)
    aas_type = members.pop("@type", None)
    if aas_type:
        entry["@type"] = entry["@type"] + [aas_type]
    entry.update(members)
    return entry


def bind_type(entry, type_name, form):
    """Write the type reference in whichever form is under test."""
    if form == "attype":
        entry["@type"] = entry["@type"] + [typeref(type_name)]
    else:
        entry["uav:typeref"] = typeref(type_name)
    return entry


def td_for_submodel(sm, form, namespace=None, root_browse_name=None):
    """Return one binding-valid Thing Description for every projected Object."""
    owner = sm["id"]
    if root_browse_name is None:
        if not isinstance(sm.get("idShort"), str) or not sm["idShort"]:
            raise ValueError("a Submodel without idShort requires a derived BrowseName")
        root_browse_name = sm["idShort"]
    documents = []

    def add_child(parent, child_path, reference, ref_name):
        child_id = expanded_node_id(owner, child_path, namespace)
        parent.setdefault("uav:hasComponent", []).append(child_id)
        parent["links"].append({
            "rel": reference,
            "href": td_document_iri(owner, child_path),
            "type": "application/td+json",
            "uav:refId": (
                "i=49" if reference == "ua:HasOrderedComponent" else "i=47"),
            "uav:refName": ref_name,
        })

    def emit_object(node, path, parent_path, browse, type_name, *,
                    index=None, reference=None):
        state = AASRenderState()
        node_id = expanded_node_id(owner, path, namespace)
        document = {
            "@context": [
                "https://www.w3.org/2022/wot/td/v1.1",
                {"uav": "http://opcfoundation.org/UA/WoT-Binding/",
                 "aas": AAS_NS,
                 "i4aas": I4AAS,
                 "ua": UA},
            ],
            "@type": ["uav:object"],
            "id": node_iri(owner, path),
            "title": browse,
            "uav:id": node_id,
            "uav:browseName": browse_name(browse, namespace),
            "forms": [{
                "href": opc_form_href(node_id),
                "contentType": "application/octet-stream",
                "op": "readallproperties",
            }],
            "links": [{
                "rel": "self",
                "href": td_document_iri(owner, path),
                "type": "application/td+json",
            }],
            "securityDefinitions": {"nosec_sc": {"scheme": "nosec"}},
            "security": "nosec_sc",
        }
        if path is not None:
            document["uav:modellingRule"] = "Optional"
            document["uav:componentOf"] = [
                expanded_node_id(owner, parent_path, namespace)
            ]
            document["links"].append({
                "rel": "uav:componentOf",
                "href": td_document_iri(owner, parent_path),
                "type": "application/td+json",
            })
        if index is not None:
            document["uav:index"] = index

        model_type = node.get("modelType")
        child_field = rt.CHILD_FIELDS.get(model_type)
        skipped = ({child_field[0]} if child_field else set())
        if model_type == "Submodel":
            skipped.add("submodelElements")
        if model_type == "Operation":
            skipped.update(role for role, _ in OPERATION_ROLES)
        merge_aas(document, node, skipped, state)
        bind_type(document, type_name, form)
        documents.append(document)

        if model_type == "Submodel":
            field = "submodelElements"
            children = node.get(field) or []
            contained = []
            for child in children:
                child_path = rt.id_short_path("", child, None)
                child_type = ELEMENT_TYPES.get(child.get("modelType"))
                if child_type is None:
                    raise ValueError(
                        f"no ObjectType for {child.get('modelType')!r}")
                emit_object(
                    child, child_path, None, child["idShort"], child_type,
                    reference="ua:HasComponent")
                add_child(
                    document, child_path, "ua:HasComponent", child["idShort"])
                contained.append({"@id": node_iri(owner, child_path)})
            if contained:
                prop = ONTOLOGY.resolve("Submodel", field)
                if prop is None:
                    raise ValueError(
                        "Submodel.submodelElements is absent from the pinned ontology")
                document[compact(prop["iri"])] = contained
                for child_index, member in enumerate(contained):
                    state.add_occurrence(
                        document["id"], prop, member, child_index)

        elif child_field:
            field, is_list = child_field
            children = node.get(field) or []
            ordered = is_list and node.get("orderRelevant", True)
            child_reference = (
                "ua:HasOrderedComponent" if ordered else "ua:HasComponent")
            contained = []
            for child_index, child in enumerate(children):
                source_index = child_index if is_list else None
                child_path = rt.id_short_path(path, child, source_index)
                child_type = ELEMENT_TYPES.get(child.get("modelType"))
                if child_type is None:
                    raise ValueError(
                        f"no ObjectType for {child.get('modelType')!r}")
                child_browse = (
                    str(child_index) if is_list else child["idShort"])
                emit_object(
                    child, child_path, path, child_browse, child_type,
                    index=source_index, reference=child_reference)
                add_child(
                    document, child_path, child_reference, child_browse)
                contained.append({"@id": node_iri(owner, child_path)})
            if contained:
                prop = ONTOLOGY.resolve(model_type, field)
                if prop is None:
                    raise ValueError(
                        f"{model_type}.{field} is absent from the pinned ontology")
                document[compact(prop["iri"])] = contained
                for child_index, member in enumerate(contained):
                    state.add_occurrence(
                        document["id"], prop, member, child_index)

        if model_type == "Operation":
            for role, _ in OPERATION_ROLES:
                if role not in node:
                    continue
                wrappers = node.get(role) or []
                references = []
                for role_index, wrapper in enumerate(wrappers):
                    child = (
                        wrapper.get("value") if isinstance(wrapper, dict)
                        else None)
                    if not isinstance(child, dict):
                        raise ValueError(
                            f"{path}.{role}[{role_index}] has no "
                            "operation variable value")
                    if (
                            not isinstance(child.get("idShort"), str)
                            or not child["idShort"]):
                        raise ValueError(
                            f"{path}.{role}[{role_index}].value has no idShort")
                    child_path = f"{path}.{role}[{role_index}]"
                    child_type = ELEMENT_TYPES.get(child.get("modelType"))
                    if child_type is None:
                        raise ValueError(
                            f"no ObjectType for {child.get('modelType')!r}")
                    emit_object(
                        child, child_path, path, child["idShort"], child_type,
                        index=role_index, reference="ua:HasComponent")
                    add_child(
                        document, child_path, "ua:HasComponent",
                        child["idShort"])
                    wrapper_node = {
                        "@id": state.blank("node"),
                        "@type": "aas:OperationVariable",
                        "aas:OperationVariable/value": {
                            "@id": node_iri(owner, child_path),
                        },
                    }
                    references.append(wrapper_node)
                prop = ONTOLOGY.resolve("Operation", role)
                if prop is None:
                    raise ValueError(
                        f"Operation.{role} is absent from the pinned ontology")
                document[compact(prop["iri"])] = references
                for role_index, wrapper_node in enumerate(references):
                    state.add_occurrence(
                        document["id"], prop, wrapper_node, role_index)

        state.attach(document)
        return document

    emit_object(
        sm, None, None, root_browse_name, "AASSubmodelType")
    return documents


def generate(env, form="term", *, digest_function=None):
    load_type_nodeids()
    root_browse_names = rt.identifiable_browse_names(
        env, digest_function=digest_function)
    documents = []
    for index, sm in enumerate(env.get("submodels", []) or []):
        documents.extend(td_for_submodel(
            sm, form,
            root_browse_name=root_browse_names[("submodels", index)]))
    return documents



# ---------------------------------------------------------------------------
# Projection: the rules Annex F states, applied to the generated documents
# ---------------------------------------------------------------------------
def project(tds, honour_proposed_term, form="term"):
    """Return the node set a WoT Connectivity registry would materialize."""
    nodes = {}
    by_subject = {}
    by_document = {}
    for td in tds:
        root = td["uav:id"]
        root_subject = td.get("id") or td.get("@id")
        parents = td.get("uav:componentOf", [])
        if not isinstance(parents, list):
            parents = [parents]
        nodes[root] = {
            "Subject": root_subject,
            "BrowseName": td["uav:browseName"].split(";")[-1],
            "TypeDefinition": type_of(td, honour_proposed_term, form),
            "Parent": (
                None if not parents
                else parents[0] if len(parents) == 1
                else tuple(parents)),
            "Source": None,
            "Reference": None,
            "Index": td.get("uav:index"),
            "LinkCount": 0,
            "OperationRole": None,
            "OperationIndex": None,
            "OperationVariables": None,
        }
        by_subject[root_subject] = root
        self_links = [
            link for link in td.get("links", [])
            if link.get("rel") == "self"
        ]
        if len(self_links) == 1:
            by_document[self_links[0].get("href")] = td

    for td in tds:
        types = td.get("@type", [])
        if "aas:Operation" not in types:
            continue
        operation = nodes[td["uav:id"]]
        contract = {}
        for role, browse_name in OPERATION_ROLES:
            wrappers = td.get(f"aas:Operation/{role}")
            if wrappers is None:
                continue
            wrappers = wrappers if isinstance(wrappers, list) else [wrappers]
            values = []
            for role_index, wrapper in enumerate(wrappers):
                value = (
                    wrapper.get("aas:OperationVariable/value")
                    if isinstance(wrapper, dict) else None)
                subject = value.get("@id") if isinstance(value, dict) else None
                target = by_subject.get(subject)
                values.append({"ValueNodeId": target})
                if target in nodes:
                    nodes[target]["OperationRole"] = role
                    nodes[target]["OperationIndex"] = role_index
            contract[browse_name] = tuple(values)
        operation["OperationVariables"] = contract

    for td in tds:
        source = td["uav:id"]
        for link in td.get("links", []):
            if link.get("rel") not in (
                    "ua:HasComponent", "ua:HasOrderedComponent"):
                continue
            target_td = by_document.get(link.get("href"))
            target = target_td.get("uav:id") if target_td is not None else None
            node = nodes.get(target)
            if node is not None:
                node["LinkCount"] += 1
                if node["LinkCount"] > 1:
                    node["Source"] = "<multiple>"
                    node["Reference"] = "<multiple>"
                    continue
                node["Source"] = source
                node["Reference"] = link["rel"].split(":")[-1]
    return nodes


def type_of(entry, honour_proposed_term, form="term"):
    """Which ObjectType the projection gives a node.

    With the published vocabulary a Thing Description projects to an Object typed
    `BaseObjectType` unless it instantiates a Thing Model, and `uav:congruentType`
    does not change that: it is reconciliation metadata and is retained as
    residue. The proposed binding names an ObjectType that is already loaded and
    resolves it by name against what the Server has, not by reading back a NodeId
    the document carries - in either of the two forms under test.
    """
    if honour_proposed_term:
        resolved = (resolve_attype(entry.get("@type")) if form == "attype"
                    else resolve_typeref(entry.get("uav:typeref")))
        if resolved:
            return resolved
    return f"nsu={UA};i=58"  # BaseObjectType



# ---------------------------------------------------------------------------
# Expectation: what clause 5.6 materializes from the same environment
# ---------------------------------------------------------------------------
def expected(env):
    load_type_nodeids()
    space = rt.materialize(env)
    source_submodels = {
        submodel["id"]: submodel
        for submodel in env.get("submodels", []) or []
    }
    nodes = {}
    for sm in space["Submodels"]:
        owner = sm["Members"]["id"]
        nodes[expanded_node_id(owner)] = {
            "Subject": node_iri(owner),
            "BrowseName": sm["BrowseName"],
            "TypeDefinition": TYPE_NODEIDS.get("AASSubmodelType"),
            "Parent": None,
            "Source": None,
            "Reference": None,
            "Index": None,
            "LinkCount": 0,
            "OperationRole": None,
            "OperationIndex": None,
            "OperationVariables": None,
        }
        for element in sm["Elements"]:
            collect(element, owner, nodes, expanded_node_id(owner), "HasComponent")
        source = source_submodels.get(owner)
        if source is None:
            raise ValueError(f"materialized Submodel {owner!r} has no source")
        for element in source.get("submodelElements", []) or []:
            collect_operation_contracts(
                element, owner, nodes, rt.id_short_path("", element, None))
    return nodes


def collect(node, owner, out, parent, reference):
    path = path_of(node, owner)
    key = expanded_node_id(owner, path)
    out[key] = {
        "Subject": node_iri(owner, path),
        "BrowseName": node["BrowseName"],
        "TypeDefinition": TYPE_NODEIDS.get(node["TypeDefinition"]),
        "Parent": parent,
        "Source": parent,
        "Reference": reference,
        "Index": node["Members"].get("Index"),
        "LinkCount": 1,
        "OperationRole": None,
        "OperationIndex": None,
        "OperationVariables": None,
    }
    ref = node["Members"].get("_childReference") or "HasComponent"
    for child in node["Children"]:
        collect(child, owner, out, key, ref)
    if node["Members"].get("ModelType") == "Operation":
        contract = {}
        for role, browse_name in OPERATION_ROLES:
            entries = node["Members"].get(browse_name)
            if entries is None:
                continue
            values = []
            for role_index, entry in enumerate(entries):
                if not isinstance(entry, dict) or set(entry) != {"ValueNodeId"}:
                    raise ValueError(
                        f"{path}.{browse_name}[{role_index}] is not an "
                        "AASOperationVariableDataType")
                target = expanded_materialized_node_id(
                    entry["ValueNodeId"], owner)
                if target not in out:
                    raise ValueError(
                        f"{path}.{browse_name}[{role_index}].ValueNodeId "
                        f"does not name a materialized child")
                out[target]["OperationRole"] = role
                out[target]["OperationIndex"] = role_index
                values.append({"ValueNodeId": target})
            contract[browse_name] = tuple(values)
        out[key]["OperationVariables"] = contract
    return out


def expanded_materialized_node_id(value, owner):
    """Normalize a local materializer NodeId to the TD instance namespace."""
    if not isinstance(value, str) or ";s=" not in value:
        raise ValueError(f"Operation ValueNodeId is not a String NodeId: {value!r}")
    identifier = value.split(";s=", 1)[1]
    kind, decoded_owner, path = rt.decode_node_identifier(identifier)
    if kind != "E" or decoded_owner != owner or path is None:
        raise ValueError(f"unexpected Operation ValueNodeId {value!r}")
    return f"nsu={INSTANCE_NS};s={identifier}"


def collect_operation_contracts(element, owner, out, path):
    """Cross-check source roles against the round-trip materializer contract."""
    model_type = element.get("modelType")
    child_field = rt.CHILD_FIELDS.get(model_type)
    if child_field:
        field, is_list = child_field
        for index, child in enumerate(element.get(field) or []):
            child_path = rt.id_short_path(path, child, index if is_list else None)
            collect_operation_contracts(child, owner, out, child_path)

    if model_type != "Operation":
        return
    operation_id = expanded_node_id(owner, path)
    if operation_id not in out:
        raise ValueError(f"Operation {path!r} was not materialized")
    contract = {}
    for role, browse_name in OPERATION_ROLES:
        if role not in element:
            continue
        values = []
        for role_index, wrapper in enumerate(element.get(role) or []):
            child = wrapper.get("value") if isinstance(wrapper, dict) else None
            if not isinstance(child, dict):
                raise ValueError(
                    f"{path}.{role}[{role_index}] has no operation variable value")
            if not isinstance(child.get("idShort"), str) or not child["idShort"]:
                raise ValueError(
                    f"{path}.{role}[{role_index}].value has no idShort")
            child_path = f"{path}.{role}[{role_index}]"
            child_id = expanded_node_id(owner, child_path)
            materialized = out.get(child_id)
            if materialized is None:
                raise ValueError(
                    f"{path}.{browse_name}[{role_index}].ValueNodeId "
                    "does not name a materialized child")
            if (
                    materialized["Parent"] != operation_id
                    or materialized["Reference"] != "HasComponent"
                    or materialized["Index"] != role_index
                    or materialized["OperationRole"] != role
                    or materialized["OperationIndex"] != role_index):
                raise ValueError(
                    f"{child_id}: round-trip Operation role/containment differs "
                    "from the source")
            values.append({"ValueNodeId": child_id})
            collect_operation_contracts(child, owner, out, child_path)
        contract[browse_name] = tuple(values)
    if out[operation_id]["OperationVariables"] != contract:
        raise ValueError(
            f"{operation_id}: round-trip Operation ValueNodeId contract differs "
            "from the source")


def path_of(node, owner):
    """The `idShortPath` decoded from the clause 5.3 String NodeId."""
    ident = node["NodeId"].split(";s=", 1)[-1]
    kind, decoded_owner, path = rt.decode_node_identifier(ident)
    if kind != "E" or decoded_owner != owner:
        raise ValueError(f"unexpected element NodeId {ident!r}")
    return path


def compare(want, got):
    missing = sorted(set(want) - set(got))
    extra = sorted(set(got) - set(want))
    differing = []
    for key in sorted(set(want) & set(got)):
        for field in ("Subject", "BrowseName", "TypeDefinition", "Parent", "Source",
                      "Reference", "Index", "LinkCount", "OperationRole",
                      "OperationIndex", "OperationVariables"):
            if want[key].get(field) != got[key].get(field):
                differing.append((key, field, want[key].get(field), got[key].get(field)))
    return missing, extra, differing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("environment")
    ap.add_argument("--proposed", action="store_true",
                    help="honour the proposed type binding of spec-drafts#19")
    ap.add_argument("--form", choices=("attype", "term"), default="attype",
                    help="how the type reference is written: a member of @type "
                         "(the proposed form), or a dedicated uav:typeref member "
                         "(the withdrawn alternative, kept so the two can be compared)")
    ap.add_argument("--dump-td", help="write the generated Thing Descriptions here")
    ap.add_argument(
        "--dump-dir",
        help="write one numbered Thing Description file per projected Object")
    args = ap.parse_args()

    with open(args.environment, encoding="utf-8") as f:
        env = json.load(f)

    tds = generate(env, args.form)
    if args.dump_dir:
        os.makedirs(args.dump_dir, exist_ok=True)
        for index, td in enumerate(tds):
            path = os.path.join(args.dump_dir, f"{index:04d}.td.jsonld")
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                json.dump(td, f, indent=2, ensure_ascii=False)
                f.write("\n")
    if args.dump_td:
        if len(tds) != 1:
            print("--dump-td requires an environment projecting exactly one Object; "
                  "use --dump-dir for a projection bundle",
                  file=sys.stderr)
            return 1
        with open(args.dump_td, "w", encoding="utf-8", newline="\n") as f:
            json.dump(tds[0], f, indent=2, ensure_ascii=False)
            f.write("\n")

    want = expected(env)
    got = project(tds, honour_proposed_term=args.proposed, form=args.form)
    missing, extra, differing = compare(want, got)

    if not want:
        print("no nodes expected: the environment contains no submodels, so this run "
              "would pass without testing anything", file=sys.stderr)
        return 1

    binding = ("uav:typeref" if args.form == "term" else "a member of @type")
    print(f"vocabulary: {'published + ' + binding if args.proposed else 'published only'}")
    print(f"nodes expected by clause 5.6 : {len(want)}")
    print(f"nodes produced by projection : {len(got)}")
    print(f"  missing   : {len(missing)}")
    print(f"  unexpected: {len(extra)}")
    print(f"  differing : {len(differing)}")
    compared_edges = sum(1 for k in set(want) & set(got)
                         if want[k].get("Parent") or got[k].get("Parent"))
    compared_indices = sum(1 for k in set(want) & set(got)
                           if want[k].get("Index") is not None
                           or got[k].get("Index") is not None)
    print(f"  containment edges compared              : {compared_edges}")
    print(f"  array/list indices compared             : {compared_indices}")
    for key, field, w, g in differing[:6]:
        print(f"    {key}\n      {field}: expected {w}, got {g}")
    for key in missing[:4]:
        print(f"    missing: {key}")
    print("\nScope: submodels and their elements. Shells and concept descriptions are not compared.\n"
          "This compares the documented projection rules against the reference materializer.\n"
          "Both sides are implemented here, so it demonstrates that the rules of Annex F are\n"
          "self-consistent and complete for these fixtures. It is not a test of any WoT\n"
          "Connectivity implementation, and Annex F is informative for that reason.")
    return 0 if not (missing or extra or differing) else 1


if __name__ == "__main__":
    sys.exit(main())
