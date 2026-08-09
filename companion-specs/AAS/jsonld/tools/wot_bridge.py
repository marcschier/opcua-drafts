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
`HasTypeDefinition`. The generator therefore emits the proposed `uav:typeDefinition`
term, and the projector honours it only when `--proposed` is passed. Without that
flag the run reports what the published vocabulary actually achieves, which is
less.

Usage:
    python wot_bridge.py <environment.json> [--proposed] [--dump-td out.jsonld]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
AAS_TOOLS = os.path.normpath(os.path.join(HERE, "..", "..", "tools"))
sys.path.insert(0, AAS_TOOLS)

import roundtrip_check as rt  # noqa: E402

I4AAS = "http://opcfoundation.org/UA/I4AAS/"
UA = "http://opcfoundation.org/UA/"

# The ObjectType each metamodel class materializes as, from clause 6. Read from
# the round-trip reference implementation so the two cannot disagree.
ELEMENT_TYPES = dict(rt.ELEMENT_TYPES)
ROOT_TYPES = {
    "Submodel": "AASSubmodelType",
    "AssetAdministrationShell": "AASType",
    "ConceptDescription": "AASConceptDescriptionType",
}

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


# ---------------------------------------------------------------------------
# Generation: an AAS environment becomes one Thing Description per Submodel
# ---------------------------------------------------------------------------
def expanded_node_id(owner_id, path=None):
    """Clause 5.3, written portably: an ExpandedNodeId naming its namespace."""
    ident = owner_id if path is None else f"{owner_id}#{path}"
    return f"nsu={{server}};s={ident}"


def td_for_submodel(sm):
    """A Thing Description whose projection is the submodel's node tree."""
    owner = sm["id"]
    td = {
        "@context": [
            "https://www.w3.org/2022/wot/td/v1.1",
            {"uav": "http://opcfoundation.org/UA/WoT-Binding/",
             "aas": "https://admin-shell.io/aas/3/0/",
             "i4aas": I4AAS,
             "ua": UA},
        ],
        "@type": ["uav:object"],
        "title": sm.get("idShort", owner),
        "id": owner,
        "uav:id": expanded_node_id(owner),
        "uav:browseName": f"nsu={{server}};{sm.get('idShort', owner)}",
        "uav:typeDefinition": TYPE_NODEIDS.get("AASSubmodelType"),
        "uav:congruentTypeName": "i4aas:AASSubmodelType",
        "uav:congruentType": TYPE_NODEIDS.get("AASSubmodelType"),
        "properties": {},
        "links": [],
    }
    for index, element in enumerate(sm.get("submodelElements", []) or []):
        emit_element(td, element, owner, "", None)
    return td


def emit_element(td, element, owner, parent_path, index):
    """Each submodel element becomes a contained Object, named by clause 5.3."""
    model_type = element.get("modelType")
    type_name = ELEMENT_TYPES.get(model_type)
    if type_name is None:
        raise ValueError(f"no ObjectType for {model_type!r}")
    path = rt.id_short_path(parent_path, element, index)
    node_id = expanded_node_id(owner, path)
    browse = str(index) if index is not None else element["idShort"]

    entry = {
        "@type": ["uav:object"],
        "uav:id": node_id,
        "uav:browseName": f"nsu={{server}};{browse}",
        "uav:typeDefinition": TYPE_NODEIDS.get(type_name),
        "uav:congruentTypeName": f"i4aas:{type_name}",
        "uav:congruentType": TYPE_NODEIDS.get(type_name),
        "uav:componentOf": [expanded_node_id(owner, parent_path) if parent_path
                            else expanded_node_id(owner)],
        "uav:modellingRule": "Optional",
    }
    if index is not None:
        entry["uav:index"] = index
    td["properties"][path] = entry

    child_field = rt.CHILD_FIELDS.get(model_type)
    if child_field:
        field, is_list = child_field
        children = element.get(field) or []
        ordered = is_list and element.get("orderRelevant", True)
        for i, child in enumerate(children):
            emit_element(td, child, owner, path, i if is_list else None)
            child_path = rt.id_short_path(path, child, i if is_list else None)
            td["links"].append({
                "rel": "ua:HasOrderedComponent" if ordered else "ua:HasComponent",
                "href": expanded_node_id(owner, child_path),
                "uav:refId": "i=49" if ordered else "i=47",
                "uav:refName": str(i) if is_list else child.get("idShort", ""),
            })


def generate(env):
    load_type_nodeids()
    return [td_for_submodel(sm) for sm in env.get("submodels", []) or []]


# ---------------------------------------------------------------------------
# Projection: the rules Annex F states, applied to the generated documents
# ---------------------------------------------------------------------------
def project(tds, honour_proposed_term):
    """Return the node set a WoT Connectivity registry would materialize."""
    nodes = {}
    for td in tds:
        root = td["uav:id"]
        nodes[root] = {
            "BrowseName": td["uav:browseName"].split(";")[-1],
            "TypeDefinition": type_of(td, honour_proposed_term, "AASSubmodelType"),
        }
        for path, entry in td["properties"].items():
            nodes[entry["uav:id"]] = {
                "BrowseName": entry["uav:browseName"].split(";")[-1],
                "TypeDefinition": type_of(entry, honour_proposed_term, None),
            }
        for link in td["links"]:
            node = nodes.get(link["href"])
            if node is not None:
                node["Reference"] = link["rel"].split(":")[-1]
    return nodes


def type_of(entry, honour_proposed_term, _default):
    """Which ObjectType the projection gives a node.

    With the published vocabulary a Thing Description projects to an Object typed
    `BaseObjectType` unless it instantiates a Thing Model, and `uav:congruentType`
    does not change that. The proposed `uav:typeDefinition` binds the projected
    Object to an ObjectType that is already loaded.
    """
    if honour_proposed_term and entry.get("uav:typeDefinition"):
        return entry["uav:typeDefinition"]
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
    ident = node["NodeId"].split(";s=", 1)[-1]
    path = ident.split("#", 1)[1] if "#" in ident else None
    key = expanded_node_id(owner, path)
    out[key] = {
        "BrowseName": node["BrowseName"],
        "TypeDefinition": TYPE_NODEIDS.get(node["TypeDefinition"]),
    }
    ref = node["Members"].get("_childReference")
    for child in node["Children"]:
        collect(child, owner, out)
        child_ident = child["NodeId"].split(";s=", 1)[-1]
        child_path = child_ident.split("#", 1)[1] if "#" in child_ident else None
        out[expanded_node_id(owner, child_path)]["Reference"] = ref or "HasComponent"
    return out


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
                    help="honour the proposed uav:typeDefinition term")
    ap.add_argument("--dump-td", help="write the generated Thing Descriptions here")
    args = ap.parse_args()

    with open(args.environment, encoding="utf-8") as f:
        env = json.load(f)

    tds = generate(env)
    if args.dump_td:
        with open(args.dump_td, "w", encoding="utf-8", newline="\n") as f:
            json.dump(tds, f, indent=2, ensure_ascii=False)
            f.write("\n")

    want = expected(env)
    got = project(tds, honour_proposed_term=args.proposed)
    missing, extra, differing = compare(want, got)

    if not want:
        print("no nodes expected: the environment contains no submodels, so this run "
              "would pass without testing anything", file=sys.stderr)
        return 1

    print(f"vocabulary: {'published + proposed uav:typeDefinition' if args.proposed else 'published only'}")
    print(f"nodes expected by clause 5.6 : {len(want)}")
    print(f"nodes produced by projection : {len(got)}")
    print(f"  missing   : {len(missing)}")
    print(f"  unexpected: {len(extra)}")
    print(f"  differing : {len(differing)}")
    for key, field, w, g in differing[:6]:
        print(f"    {key}\n      {field}: expected {w}, got {g}")
    for key in missing[:4]:
        print(f"    missing: {key}")
    print("\nThis compares the documented projection rules against the reference materializer.\n"
          "Both sides are implemented here, so it demonstrates that the rules of Annex F are\n"
          "self-consistent and complete for these fixtures. It is not a test of any WoT\n"
          "Connectivity implementation, and Annex F is informative for that reason.")
    return 0 if not (missing or extra or differing) else 1


if __name__ == "__main__":
    sys.exit(main())
