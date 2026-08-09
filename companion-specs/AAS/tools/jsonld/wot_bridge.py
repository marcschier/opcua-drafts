#!/usr/bin/env python3
"""
Generate Thing Descriptions from an AAS environment, project them, and compare
the result against the AddressSpace the AAS companion specification defines.

Annex F of `OPC-UA-AAS.md` claims that a Thing Description carrying the AAS
vocabulary, loaded through the WoT Connectivity registry, materializes the same
nodes as clause 5.6. This tool is what makes that claim checkable rather than
asserted: it emits the Thing Descriptions, applies the projection rules the annex
states, and diffs the resulting node set against the one `roundtrip_check.py`
materializes from the same environment.

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
                         [--dump-td out.jsonld]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AAS_TOOLS = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, AAS_TOOLS)

import roundtrip_check as rt  # noqa: E402
from jsonld.lift import Ontology  # noqa: E402

I4AAS = "http://opcfoundation.org/UA/I4AAS/"
UA = "http://opcfoundation.org/UA/"
AAS_NS = "https://admin-shell.io/aas/3/0/"

# The vocabulary, read from the pinned ontology rather than restated here.
ONTOLOGY = Ontology()

# The ObjectType each metamodel class materializes as, from clause 6. Read from
# the round-trip reference implementation so the two cannot disagree.
ELEMENT_TYPES = dict(rt.ELEMENT_TYPES)

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


def expanded_node_id(owner_id, path=None, namespace=None):
    """Clause 5.3: the String NodeId, qualified by the instance NamespaceUri."""
    ident = owner_id if path is None else f"{owner_id}#{path}"
    return f"nsu={namespace or INSTANCE_NS};s={ident}"


def browse_name(name, namespace=None):
    return f"nsu={namespace or INSTANCE_NS};{name}"


def node_iri(owner_id, path=None):
    """The subject term of a node, so the AAS triples have something to hang on.

    An identifier that is already an absolute IRI without a fragment takes the
    `idShortPath` as its fragment, which is readable and is the same construction
    clause 5.3 uses for the NodeId. Anything else - a URN, an IRDI, or an IRI that
    already carries a fragment - is hashed, because appending a second fragment
    would not be a legal IRI. Clause 2.2 rule 3 of the JSON-LD mapping does the
    same thing for the same reason.
    """
    if path is None:
        base = owner_id
    elif is_absolute_iri(owner_id) and "#" not in owner_id:
        return f"{owner_id}#{path}"
    else:
        base = f"{owner_id}#{path}"
    if is_absolute_iri(base) and "#" not in base:
        return base
    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()
    return f"https://w3id.org/aas-jsonld/id/{digest}"


def is_absolute_iri(value):
    return bool(re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value or "")) and " " not in value


def aas_members(node, skip_field=None, cls=None):
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
    out = {}
    if cls:
        out["@type"] = compact(f"{AAS_NS}{cls}")
    for key, value in node.items():
        if key in ("modelType", skip_field):
            continue
        prop = ONTOLOGY.resolve(cls, key) if cls else None
        if prop is None:
            continue
        rendered = render_value(value, prop)
        if rendered is not None:
            out[compact(prop["iri"])] = rendered
    return out


def render_value(value, prop):
    rng = (prop.get("range") or "").split(":")[-1]
    if isinstance(value, list):
        rendered = [render_value(v, prop) for v in value]
        return [r for r in rendered if r is not None] or None
    if isinstance(value, dict):
        return aas_members(value, cls=value.get("modelType") or rng) or None
    if rng in ONTOLOGY.enums:
        member = enum_individual(rng, value)
        return {"@id": compact(member)} if member else None
    if isinstance(value, bool):
        return value
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


def merge_aas(entry, node, skip_field=None):
    """Add the node's AAS content to an affordance, keeping the `@type` list.

    `@type` already carries the NodeClass term and the ObjectType; the AAS class
    joins them rather than replacing them, so the same member says what the node
    projects to and what it is in the metamodel.
    """
    members = aas_members(node, skip_field)
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


def td_for_submodel(sm, form, namespace=None):
    """A Thing Description that is the submodel, and projects to its node tree."""
    owner = sm["id"]
    child_field = rt.CHILD_FIELDS.get("Submodel")
    td = {
        "@context": [
            "https://www.w3.org/2022/wot/td/v1.1",
            {"uav": "http://opcfoundation.org/UA/WoT-Binding/",
             "aas": AAS_NS,
             "i4aas": I4AAS,
             "ua": UA},
        ],
        "@type": ["uav:object"],
        "@id": node_iri(owner),
        "title": sm.get("idShort", owner),
        "id": owner,
        "uav:id": expanded_node_id(owner, None, namespace),
        "uav:browseName": browse_name(sm.get("idShort", owner), namespace),
        "properties": {},
        "links": [],
    }
    merge_aas(td, sm, child_field[0] if child_field else None)
    bind_type(td, "AASSubmodelType", form)

    contained = []
    for index, element in enumerate(sm.get("submodelElements", []) or []):
        emit_element(td, element, owner, "", None, form, namespace)
        contained.append({"@id": node_iri(owner, rt.id_short_path("", element, None))})
    if contained:
        td["aas:Submodel/submodelElements"] = contained
    return td


def emit_element(td, element, owner, parent_path, index, form, namespace=None):
    """Each submodel element becomes a contained Object, named by clause 5.3."""
    model_type = element.get("modelType")
    type_name = ELEMENT_TYPES.get(model_type)
    if type_name is None:
        raise ValueError(f"no ObjectType for {model_type!r}")
    path = rt.id_short_path(parent_path, element, index)
    browse = str(index) if index is not None else element["idShort"]
    child_field = rt.CHILD_FIELDS.get(model_type)

    entry = {
        "@type": ["uav:object"],
        "@id": node_iri(owner, path),
        "uav:id": expanded_node_id(owner, path, namespace),
        "uav:browseName": browse_name(browse, namespace),
        "uav:modellingRule": "Optional",
    }
    # `uav:componentOf` is only written where it says something. Every affordance
    # of a Thing Description is already a member of that Thing, so naming the
    # Thing as the parent repeats what the document structure states; a nested
    # element's parent is another affordance and cannot be read off the document.
    if parent_path:
        entry["uav:componentOf"] = [expanded_node_id(owner, parent_path, namespace)]
    merge_aas(entry, element, child_field[0] if child_field else None)
    bind_type(entry, type_name, form)
    if index is not None:
        entry["uav:index"] = index
    td["properties"][path] = entry

    if child_field:
        field, is_list = child_field
        children = element.get(field) or []
        ordered = is_list and element.get("orderRelevant", True)
        contained = []
        for i, child in enumerate(children):
            emit_element(td, child, owner, path, i if is_list else None, form, namespace)
            child_path = rt.id_short_path(path, child, i if is_list else None)
            contained.append({"@id": node_iri(owner, child_path)})
            td["links"].append({
                "rel": "ua:HasOrderedComponent" if ordered else "ua:HasComponent",
                "href": expanded_node_id(owner, child_path, namespace),
                "uav:refId": "i=49" if ordered else "i=47",
                "uav:refName": str(i) if is_list else child.get("idShort", ""),
            })
        if contained:
            prop = ONTOLOGY.resolve(model_type, field)
            if prop is not None:
                entry[compact(prop["iri"])] = contained


def generate(env, form="term"):
    load_type_nodeids()
    return [td_for_submodel(sm, form) for sm in env.get("submodels", []) or []]



# ---------------------------------------------------------------------------
# Projection: the rules Annex F states, applied to the generated documents
# ---------------------------------------------------------------------------
def project(tds, honour_proposed_term, form="term"):
    """Return the node set a WoT Connectivity registry would materialize."""
    nodes = {}
    for td in tds:
        root = td["uav:id"]
        nodes[root] = {
            "BrowseName": td["uav:browseName"].split(";")[-1],
            "TypeDefinition": type_of(td, honour_proposed_term, form),
        }
        for path, entry in td["properties"].items():
            nodes[entry["uav:id"]] = {
                "BrowseName": entry["uav:browseName"].split(";")[-1],
                "TypeDefinition": type_of(entry, honour_proposed_term, form),
            }
        for link in td["links"]:
            node = nodes.get(link["href"])
            if node is not None:
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
    nodes = {}
    for sm in space["Submodels"]:
        owner = sm["Members"]["id"]
        nodes[expanded_node_id(owner)] = {
            "BrowseName": sm["BrowseName"],
            "TypeDefinition": TYPE_NODEIDS.get("AASSubmodelType"),
        }
        for element in sm["Elements"]:
            collect(element, owner, nodes)
    return nodes


def collect(node, owner, out):
    key = expanded_node_id(owner, path_of(node, owner))
    out[key] = {
        "BrowseName": node["BrowseName"],
        "TypeDefinition": TYPE_NODEIDS.get(node["TypeDefinition"]),
    }
    ref = node["Members"].get("_childReference")
    for child in node["Children"]:
        collect(child, owner, out)
        out[expanded_node_id(owner, path_of(child, owner))]["Reference"] = ref or "HasComponent"
    return out


def path_of(node, owner):
    """The `idShortPath` part of a node's String NodeId.

    Clause 5.3 builds the identifier as `<owner id>#<idShortPath>`, and an AAS
    identifier may itself contain a `#` - every SAMM URN in the battery passport
    templates does. Splitting on the first one therefore takes the owner's own
    fragment for part of the path. The owner is known, so the prefix is removed
    rather than searched for.
    """
    ident = node["NodeId"].split(";s=", 1)[-1]
    prefix = owner + "#"
    if ident.startswith(prefix):
        return ident[len(prefix):]
    return ident.split("#", 1)[1] if "#" in ident else None


def compare(want, got):
    missing = sorted(set(want) - set(got))
    extra = sorted(set(got) - set(want))
    differing = []
    for key in sorted(set(want) & set(got)):
        for field in ("BrowseName", "TypeDefinition", "Reference"):
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
    args = ap.parse_args()

    with open(args.environment, encoding="utf-8") as f:
        env = json.load(f)

    tds = generate(env, args.form)
    if args.dump_td:
        with open(args.dump_td, "w", encoding="utf-8", newline="\n") as f:
            json.dump(tds, f, indent=2, ensure_ascii=False)
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
    compared_refs = sum(1 for k in set(want) & set(got)
                        if want[k].get("Reference") or got[k].get("Reference"))
    print(f"  of which a containment ReferenceType was compared on: {compared_refs}")
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
