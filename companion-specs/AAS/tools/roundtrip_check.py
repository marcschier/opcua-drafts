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

# ---------------------------------------------------------------------------
# Clause 5.2 / clause 8: a value is compared in the xsd value space, and a serializer
# emits the XSD canonical lexical representation. canonical_value() below is that
# representation - it is deliberately total: a form this mapping does not normalize is
# returned unchanged, which makes it compare equal to itself and nothing else.
# ---------------------------------------------------------------------------
import decimal
import re

_INTEGER_TYPES = {
    "xs:byte", "xs:unsignedByte", "xs:short", "xs:unsignedShort", "xs:int",
    "xs:unsignedInt", "xs:long", "xs:unsignedLong", "xs:integer",
    "xs:nonNegativeInteger", "xs:positiveInteger", "xs:nonPositiveInteger",
    "xs:negativeInteger",
}


def _canon_decimal(s):
    """The XSD canonical form of an xs:decimal, computed textually.

    Deliberately not via the decimal module: its default context rounds to 28
    significant digits, which silently truncated a 62-digit fixture value. xs:decimal is
    arbitrary precision, so anything that imposes a working precision is wrong here.
    """
    s = s.strip()
    neg = s.startswith("-")
    if s[:1] in ("+", "-"):
        s = s[1:]
    ip, _, fp = s.partition(".")
    ip = ip.lstrip("0") or "0"
    fp = fp.rstrip("0") or "0"
    out = f"{ip}.{fp}"
    return "-" + out if neg and (ip != "0" or fp != "0") else out


def canonical_value(value, value_type):
    """The XSD canonical lexical representation of `value` read as `value_type`."""
    if value is None or value_type is None:
        return value
    try:
        if value_type == "xs:boolean":
            if value in ("true", "1"):
                return "true"
            if value in ("false", "0"):
                return "false"
            return value
        if value_type in _INTEGER_TYPES:
            return str(int(value))     # Python ints are arbitrary precision
        if value_type == "xs:decimal":
            return _canon_decimal(value)
        if value_type in ("xs:double", "xs:float"):
            f = float(value)
            if f != f:
                return "NaN"
            if f in (float("inf"), float("-inf")):
                return "INF" if f > 0 else "-INF"
            m, _, e = repr(f).partition("e")
            exp = int(e) if e else 0
            d = decimal.Decimal(m).scaleb(exp).normalize()
            sign, digits, dexp = d.as_tuple()
            mant = "".join(str(x) for x in digits)
            exp10 = dexp + len(digits) - 1
            mant = mant[0] + "." + (mant[1:] or "0")
            return f"{'-' if sign else ''}{mant}E{exp10}"
        if value_type == "xs:dateTime":
            m = re.match(r"^(-?\d{4,}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)"
                         r"(Z|[+-]\d{2}:\d{2})?$", value)
            if not m:
                return value
            import datetime
            body, tz = m.group(1), m.group(2)
            if tz in (None, "Z"):
                base = body
            else:
                dt = datetime.datetime.fromisoformat(body)
                sign = 1 if tz[0] == "+" else -1
                off = datetime.timedelta(hours=int(tz[1:3]), minutes=int(tz[4:6]))
                base = (dt - sign * off).isoformat()
            if "." in base:
                head, frac = base.split(".")
                frac = frac.rstrip("0")
                base = f"{head}.{frac}" if frac else head
            return base + "Z"
    except (ValueError, ArithmeticError):
        return value
    return value


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
            # clause 5.2: one Value node, typed by the DataType clause 7.1 assigns.
            m["Value"] = v
            continue
        if model_type == "Range" and f in ("min", "max"):
            m[f] = v
            continue
        m[f] = v

    if child_field:
        field, is_list = child_field
        if field in elem:
            ordered = is_list and elem.get("orderRelevant", True)
            for i, child in enumerate(elem[field]):
                node["Children"].append(
                    materialize_element(child, owner_id, path,
                                        i if is_list else None, out))
            if not elem[field]:
                m["_emptyChildren"] = True  # clause 5.5: present but empty
            if is_list:
                # clause 5.4: the ReferenceType, not a Property, states whether the
                # order carries meaning. Index is materialized either way here, because
                # this implementation claims AAS-LosslessRoundTrip.
                m["_childReference"] = "HasOrderedComponent" if ordered else "HasComponent"
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
    members = node["Members"]
    value_type = members.get("valueType")
    for k, v in members.items():
        if k in ("ModelType", "Index", "_emptyChildren", "_childReference"):
            continue
        if k == "Value":
            # clause 8: emit the XSD canonical lexical representation of the value.
            elem["value"] = canonical_value(v, value_type)
            continue
        if model_type == "Range" and k in ("min", "max"):
            elem[k] = canonical_value(v, value_type)
            continue
        elem[k] = v
    if child_field:
        field, is_list = child_field
        kids = node["Children"]
        if kids:
            if is_list:
                kids = sorted(kids, key=lambda n: n["Members"]["Index"])  # clause 5.4
            elem[field] = [serialize_element(k) for k in kids]
        elif members.get("_emptyChildren"):
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
# Comparison - clause 8: equivalence, not byte equality
# ---------------------------------------------------------------------------
def canon(x):
    if isinstance(x, dict):
        return {k: canon(x[k]) for k in sorted(x)}
    if isinstance(x, list):
        return [canon(i) for i in x]
    return x


def _bag_key(x):
    return json.dumps(canon(x), sort_keys=True, ensure_ascii=False)


def equivalize(x):
    """Clause 8: reduce to the form equivalence is judged on.

    Values become their XSD canonical lexical representation, so that two lexical forms
    of one value compare equal. A SubmodelElementList whose orderRelevant is false is a
    bag, so its members are sorted into a deterministic order; an ordered list is left
    alone, because its order is part of what is being compared.
    """
    if isinstance(x, list):
        return [equivalize(i) for i in x]
    if not isinstance(x, dict):
        return x
    out = {k: equivalize(v) for k, v in x.items()}
    vt = out.get("valueType")
    if vt is not None:
        for field in ("value", "min", "max", "Value"):
            v = out.get(field)
            if isinstance(v, str):
                out[field] = canonical_value(v, vt)
    if out.get("modelType") == "SubmodelElementList" and out.get("orderRelevant") is False:
        members = out.get("value")
        if isinstance(members, list):
            out["value"] = sorted(members, key=_bag_key)
    if out.get("_childReference") == "HasComponent" and isinstance(out.get("Children"), list):
        out["Children"] = sorted(out["Children"], key=_bag_key)
    return out


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
    d = diff(canon(equivalize(env)), canon(equivalize(back)))
    if d:
        return f"materialize/serialize: {d}"
    space2 = materialize(back)
    d = diff(canon(equivalize(space)), canon(equivalize(space2)))
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

    def plain(node, reverse=False, drop_empty=False, corrupt_values=False,
              canonicalize=True, round_precision=0):
        mt = node["Members"]["ModelType"]
        elem = {"modelType": mt}
        members = node["Members"]
        vt = members.get("valueType")

        def out_value(v):
            if corrupt_values:
                try:
                    return str(float(v) + 1)   # a different value, not a re-writing
                except (TypeError, ValueError):
                    return (v or "") + "!"
            if round_precision and vt == "xs:decimal":
                with decimal.localcontext() as ctx:
                    ctx.prec = round_precision
                    return str(+decimal.Decimal(v))
            return canonical_value(v, vt) if canonicalize else v

        for k, v in members.items():
            if k in ("ModelType", "Index", "_emptyChildren", "_childReference"):
                continue
            if k == "Value":
                elem["value"] = out_value(v)
                continue
            if mt == "Range" and k in ("min", "max"):
                elem[k] = out_value(v)
                continue
            elem[k] = v
        cf = CHILD_FIELDS.get(mt)
        if cf:
            field, is_list = cf
            kids = node["Children"]
            if kids:
                if reverse:
                    kids = list(reversed(kids))
                elif is_list:
                    kids = sorted(kids, key=lambda n: n["Members"]["Index"])
                elem[field] = [plain(k, reverse, drop_empty, corrupt_values, canonicalize,
                                     round_precision)
                               for k in kids]
            elif members.get("_emptyChildren") and not drop_empty:
                elem[field] = []
        return elem

    controls = [
        ("clause 5.2 - a value altered rather than re-written",
         "non-canonical-lexical-forms.json",
         lambda n: plain(n, corrupt_values=True), True),
        # xs:decimal is arbitrary precision. Canonicalizing it through a fixed working
        # precision loses digits while still producing a plausible-looking decimal, and
        # loses them on both sides of the comparison, so nothing else here would notice.
        ("clause 7.1 - xs:decimal truncated to a working precision",
         "non-canonical-lexical-forms.json",
         lambda n: plain(n, round_precision=28), True),
        ("clause 5.4 - ordered list not restored from Index",
         "ordering-and-nesting.json",
         lambda n: plain(n, reverse=True), True),
        ("clause 5.5 - absent conflated with empty",
         "absent-versus-empty.json",
         lambda n: plain(n, drop_empty=True), True),
        # The converse control. Equivalence is value-based, so a serializer that re-writes
        # a value into its canonical lexical form must NOT be reported: a check that fires
        # on every difference is as useless as one that fires on none.
        ("clause 8 - canonical re-writing accepted as equivalent",
         "non-canonical-lexical-forms.json",
         lambda n: plain(n, canonicalize=True), False),
    ]

    ok = 0
    for name, fixture, broken, expect_error in controls:
        globals()["serialize_element"] = broken
        try:
            err = run(os.path.join(FIXTURES, fixture))
        finally:
            globals()["serialize_element"] = original
        if bool(err) == expect_error:
            ok += 1
            print(f"{'detected ' if expect_error else 'accepted '} {name}")
        else:
            print(f"MISSED     {name}" + (f" ({err})" if err else ""))
    print(f"\n{ok}/{len(controls)} controls behaved as specified")
    return 0 if ok == len(controls) else 1


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
