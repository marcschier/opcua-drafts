#!/usr/bin/env python3
"""
Round-trip check for the OPC UA for Asset Administration Shell mapping (clause 8).

Losslessness is only a claim until it is executed. This runs both directions defined by
clause 8 over the fixture corpus:

  materialize -> serialize   an AAS environment becomes an AddressSpace subtree and comes
                             back equal to what it started as
  serialize -> materialize   a subtree becomes an environment and becomes the same subtree

The materializer here implements clause 5.6 exactly - it is a reference implementation of
the algorithm, not a general-purpose AAS server - so that a failure means the mapping is
lossy rather than that a tool is clever. Anything the mapping cannot carry shows up as a
difference, which is the point.

Usage (from the repository root):
    python companion-specs/AAS/tools/roundtrip_check.py
"""
from __future__ import annotations
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")

NS = 2  # the server namespace instances live in

# ---------------------------------------------------------------------------
# The metamodel classes this mapping covers, and the ObjectType each becomes.
# A class absent here has no representation, which clause 5.1 makes a defect.
# ---------------------------------------------------------------------------
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

# Child-bearing fields, per element class: the metamodel field, and whether it is ordered.
CHILD_FIELDS = {
    "SubmodelElementCollection": ("value", False),
    "SubmodelElementList": ("value", True),
    "AnnotatedRelationshipElement": ("annotations", False),
    "Entity": ("statements", False),
}

# Fields carrying a value that clause 5.2 requires to be kept lexically.
LEXICAL_VALUE = {"Property": "value", "Range": None}


def _fail(msg):
    raise AssertionError(msg)


# ---------------------------------------------------------------------------
# Materialization - clause 5.6
# ---------------------------------------------------------------------------
def id_short_path(parent_path, elem, index):
    """Clause 5.3: short names joined by '.', with [n] for a member of a list."""
    if index is not None:
        return f"{parent_path}[{index}]"
    seg = elem.get("idShort")
    if seg is None:
        _fail(f"element without idShort outside a list at {parent_path!r}")
    return f"{parent_path}.{seg}" if parent_path else seg


def node_id(owner_id, path=None):
    return f"ns={NS};s={owner_id}" if path is None else f"ns={NS};s={owner_id}#{path}"


def browse_name(elem, index):
    """Clause 5.3: the short name, or the index for a list member which has none."""
    return str(index) if index is not None else elem["idShort"]


def materialize_element(elem, owner_id, parent_path, index, out):
    model_type = elem.get("modelType")
    if model_type not in ELEMENT_TYPES:
        _fail(f"element class {model_type!r} has no ObjectType in the mapping")
    path = id_short_path(parent_path, elem, index)
    node = {
        "NodeId": node_id(owner_id, path),
        "BrowseName": browse_name(elem, index),
        "TypeDefinition": ELEMENT_TYPES[model_type],
        "Members": {},
        "Children": [],
    }
    m = node["Members"]

    # clause 5.5: a field present in the source gets a member; an absent one gets none.
    for f in ("idShort", "category", "displayName", "description", "extensions",
              "semanticId", "supplementalSemanticIds", "qualifiers",
              "embeddedDataSpecifications"):
        if f in elem:
            m[f] = elem[f]
    m["ModelType"] = model_type
    if index is not None:
        m["Index"] = index  # clause 5.4

    child_field = CHILD_FIELDS.get(model_type)
    for f, v in elem.items():
        if f in ("modelType", "idShort", "category", "displayName", "description",
                 "extensions", "semanticId", "supplementalSemanticIds", "qualifiers",
                 "embeddedDataSpecifications"):
            continue
        if child_field and f == child_field[0]:
            continue
        if model_type == "Property" and f == "value":
            # clause 5.2: the value is carried twice, and RawValue is normative.
            m["RawValue"] = v
            m["Value"] = v
            continue
        m[f] = v

    if child_field:
        field, ordered = child_field
        if field in elem:
            for i, child in enumerate(elem[field]):
                node["Children"].append(
                    materialize_element(child, owner_id, path, i if ordered else None, out))
            if not elem[field]:
                m["_emptyChildren"] = True  # clause 5.5: present but empty
    out.append(node)
    return node


def materialize(env):
    """Clause 5.6, steps 1-6."""
    space = {"Type": "AASEnvironmentType", "Shells": [], "Submodels": [], "Concepts": []}
    for shell in env.get("assetAdministrationShells", []):
        space["Shells"].append({
            "NodeId": node_id(shell["id"]),
            "BrowseName": shell.get("idShort", shell["id"]),
            "TypeDefinition": "AASType",
            "Members": {k: v for k, v in shell.items() if k != "modelType"},
            "ModelType": shell.get("modelType", "AssetAdministrationShell"),
        })
    for sm in env.get("submodels", []):
        nodes = []
        for i, e in enumerate(sm.get("submodelElements", [])):
            materialize_element(e, sm["id"], "", None, nodes)
        space["Submodels"].append({
            "NodeId": node_id(sm["id"]),
            "BrowseName": sm.get("idShort", sm["id"]),
            "TypeDefinition": "AASSubmodelType",
            "Members": {k: v for k, v in sm.items()
                        if k not in ("modelType", "submodelElements")},
            "ModelType": sm.get("modelType", "Submodel"),
            "Elements": [materialize_element(e, sm["id"], "", None, [])
                         for e in sm.get("submodelElements", [])],
            "HasElements": "submodelElements" in sm,
        })
    for cd in env.get("conceptDescriptions", []):
        space["Concepts"].append({
            "NodeId": node_id(cd["id"]),
            "BrowseName": cd.get("idShort", cd["id"]),
            "TypeDefinition": "AASConceptDescriptionType",
            "Members": {k: v for k, v in cd.items() if k != "modelType"},
            "ModelType": cd.get("modelType", "ConceptDescription"),
        })
    return space


# ---------------------------------------------------------------------------
# Serialization - the reverse direction
# ---------------------------------------------------------------------------
def serialize_element(node):
    model_type = node["Members"]["ModelType"]
    elem = {"modelType": model_type}
    child_field = CHILD_FIELDS.get(model_type)
    for k, v in node["Members"].items():
        if k in ("ModelType", "Index", "Value", "_emptyChildren"):
            continue
        if k == "RawValue":
            elem["value"] = v          # clause 5.2: RawValue is the normative carrier
            continue
        elem[k] = v
    if child_field:
        field, ordered = child_field
        kids = node["Children"]
        if kids:
            if ordered:
                kids = sorted(kids, key=lambda n: n["Members"]["Index"])  # clause 5.4
            elem[field] = [serialize_element(k) for k in kids]
        elif node["Members"].get("_emptyChildren"):
            elem[field] = []
    return elem


def serialize(space):
    env = {}
    if space["Shells"]:
        env["assetAdministrationShells"] = [
            dict({"modelType": s["ModelType"]}, **s["Members"]) for s in space["Shells"]]
    if space["Submodels"]:
        out = []
        for s in space["Submodels"]:
            sm = dict({"modelType": s["ModelType"]}, **s["Members"])
            if s["HasElements"]:
                sm["submodelElements"] = [serialize_element(e) for e in s["Elements"]]
            out.append(sm)
        env["submodels"] = out
    if space["Concepts"]:
        env["conceptDescriptions"] = [
            dict({"modelType": c["ModelType"]}, **c["Members"]) for c in space["Concepts"]]
    return env


# ---------------------------------------------------------------------------
# Comparison - clause 8: canonical member order, arrays compared in order
# ---------------------------------------------------------------------------
def canon(x):
    if isinstance(x, dict):
        return {k: canon(x[k]) for k in sorted(x)}
    if isinstance(x, list):
        return [canon(i) for i in x]
    return x


def diff(a, b, path="$"):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                return f"{path}.{k}: missing after round trip"
            if k not in b:
                return f"{path}.{k}: appeared during round trip"
            d = diff(a[k], b[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return f"{path}: length {len(a)} became {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = diff(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    if a != b:
        return f"{path}: {a!r} became {b!r}"
    return None


def run(path):
    with open(path, encoding="utf-8") as f:
        env = json.load(f)
    space = materialize(env)
    back = serialize(space)
    d = diff(canon(env), canon(back))
    if d:
        return f"materialize/serialize: {d}"
    space2 = materialize(back)
    d = diff(canon(space), canon(space2))
    if d:
        return f"serialize/materialize: {d}"
    return None


# ---------------------------------------------------------------------------
# Negative control
# ---------------------------------------------------------------------------
# A round-trip check that cannot fail proves nothing. Each control below breaks exactly
# one of the normative rules and asserts the harness notices - so a green run above means
# the rules are load-bearing, not that the comparison is blind.
def _self_test():
    original = globals()["serialize_element"]

    def plain(node, reverse=False, drop_empty=False, float_values=False):
        mt = node["Members"]["ModelType"]
        elem = {"modelType": mt}
        for k, v in node["Members"].items():
            if k in ("ModelType", "Index", "Value", "_emptyChildren"):
                continue
            if k == "RawValue":
                if float_values:
                    try:
                        v = str(float(v))
                    except ValueError:
                        pass
                elem["value"] = v
                continue
            elem[k] = v
        cf = CHILD_FIELDS.get(mt)
        if cf:
            field, _ = cf
            kids = node["Children"]
            if kids:
                kids = list(reversed(kids)) if reverse else kids
                elem[field] = [plain(k, reverse, drop_empty, float_values) for k in kids]
            elif node["Members"].get("_emptyChildren") and not drop_empty:
                elem[field] = []
        return elem

    controls = [
        ("clause 5.2 - lexical form reconstructed from the typed value",
         "lexical-forms-that-do-not-survive-typing.json",
         lambda n: plain(n, float_values=True)),
        ("clause 5.4 - list order not restored from Index",
         "ordering-and-nesting.json",
         lambda n: plain(n, reverse=True)),
        ("clause 5.5 - absent conflated with empty",
         "absent-versus-empty.json",
         lambda n: plain(n, drop_empty=True)),
    ]

    detected = 0
    for name, fixture, broken in controls:
        globals()["serialize_element"] = broken
        try:
            err = run(os.path.join(FIXTURES, fixture))
        finally:
            globals()["serialize_element"] = original
        if err:
            detected += 1
            print(f"detected  {name}")
        else:
            print(f"MISSED    {name}")
    print(f"\n{detected}/{len(controls)} induced defects detected")
    return 0 if detected == len(controls) else 1


def main():
    if not os.path.isdir(FIXTURES):
        print(f"no fixture corpus at {FIXTURES}", file=sys.stderr)
        return 1
    names = sorted(n for n in os.listdir(FIXTURES) if n.endswith(".json"))
    if not names:
        print("fixture corpus is empty", file=sys.stderr)
        return 1
    failed = 0
    for n in names:
        err = run(os.path.join(FIXTURES, n))
        if err:
            print(f"FAIL {n}: {err}")
            failed += 1
        else:
            print(f"ok   {n}")
    print(f"\n{len(names) - failed}/{len(names)} fixtures round-trip losslessly")
    if failed:
        return 1
    print()
    return _self_test()


if __name__ == "__main__":
    sys.exit(main())
