#!/usr/bin/env python3
"""Local structural validator for the AAS NodeSet + CSV."""
import os, sys, csv, re
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.dirname(HERE)
REF = os.path.join(HERE, "ref")
NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"
XML = os.path.join(GEN, "Opc.Ua.I4AAS.NodeSet2.xml")
CSVF = os.path.join(GEN, "Opc.Ua.I4AAS.NodeIds.csv")
XR_NS = 1          # required model: abstract xRegistry base (http://opcfoundation.org/UA/xRegistry/)
OWN_NS = 2         # this specification's own namespace (I4AAS V3)
OWN_MIN = 1001
UA_NAMESPACE = "http://opcfoundation.org/UA/"
XR_NAMESPACE = "http://opcfoundation.org/UA/xRegistry/"
OWN_NAMESPACE = "http://opcfoundation.org/UA/I4AAS/v3/"

errors, warnings = [], []

def load_ids(p):
    s = set()
    with open(p, encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[1].strip().isdigit():
                s.add(int(row[1]))
    return s

def resolve_required_csv(model_uri, candidates):
    for candidate in candidates:
        path = os.path.abspath(candidate)
        if os.path.isfile(path):
            return path
    rendered = ", ".join(os.path.abspath(path) for path in candidates)
    raise FileNotFoundError(
        f"RequiredModel {model_uri} cannot be resolved; looked for {rendered}")

_ua_csv = os.path.join(REF, "UA.NodeIds.csv")
UA = load_ids(_ua_csv) if os.path.exists(_ua_csv) else None
UA_EXTRA = {297, 2253}
# The xRegistry base model is under OPC Foundation review and is therefore not
# guaranteed to be in this public tree. Resolve it through the explicit override,
# a local ref table, the pre-release public location, or the registered sibling
# spec-drafts checkout. If none is available, say that the cross-model references
# were NOT checked; never print a success-shaped "skipped" result.
_repo = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
_xr_override = os.environ.get("I4AAS_XREGISTRY_CSV")
_xr_candidates = [
    _xr_override,
    os.path.join(REF, "Opc.Ua.XRegistry.NodeIds.csv"),
    os.path.join(_repo, "core-specs", "xregistry",
                 "Opc.Ua.XRegistry.NodeIds.csv"),
    os.path.join(_repo, "spec-drafts", "core-specs", "xregistry",
                 "Opc.Ua.XRegistry.NodeIds.csv"),
]
_xr_csv = next((
    os.path.abspath(path) for path in _xr_candidates
    if path and os.path.isfile(path)
), None)
XR = load_ids(_xr_csv) if _xr_csv else None
if XR is None:
    warnings.append(
        "RequiredModel http://opcfoundation.org/UA/xRegistry/ was NOT CHECKED "
        "(no NodeId table found; cross-model references accepted unverified)")

if UA is None:
    warnings.append(
        "base OPC UA NodeId table is not installed under tools/ref; "
        "base-node existence checks use the repository's sanctioned "
        "self-contained mode")

ALIAS = {}
tree = ET.parse(XML)
root = tree.getroot()
defined = {}
elems = []

NID_RE = re.compile(r"^(?:ns=(\d+);)?i=(\d+)$")

def parse_numeric_nodeid(t):
    t = ALIAS.get(t, t)
    m = NID_RE.match(t or "")
    if not m:
        return None
    ns = int(m.group(1) or 0)
    return ns, int(m.group(2))

for el in root:
    tag = el.tag.replace(NS, "")
    if tag == "Aliases":
        for a in el:
            ALIAS[a.get("Alias")] = a.text
    if not tag.startswith("UA"):
        continue
    nid = el.get("NodeId")
    parsed = parse_numeric_nodeid(nid)
    if parsed and parsed[0] == OWN_NS:
        key = parsed[1]
        if key in defined:
            errors.append(f"dup NodeId ns={OWN_NS};i={key}")
        defined[key] = (tag, el.get("BrowseName"))
    elems.append((tag, el))

namespace_uris = [
    uri.text for uri in root.findall(f"{NS}NamespaceUris/{NS}Uri")
]
if namespace_uris != [XR_NAMESPACE, OWN_NAMESPACE]:
    errors.append(
        f"NamespaceUris are {namespace_uris!r}, expected "
        f"[{XR_NAMESPACE!r}, {OWN_NAMESPACE!r}]")
model = root.find(f"{NS}Models/{NS}Model")
if model is None:
    errors.append("NodeSet has no Model declaration")
    required_models = []
else:
    if model.get("ModelUri") != OWN_NAMESPACE:
        errors.append(
            f"ModelUri {model.get('ModelUri')!r} is not {OWN_NAMESPACE!r}")
    required_models = [
        required.get("ModelUri")
        for required in model.findall(NS + "RequiredModel")
    ]
    for required_uri in required_models:
        if required_uri == UA_NAMESPACE:
            continue
        if required_uri == XR_NAMESPACE:
            if XR is None:
                errors.append(
                    f"declared RequiredModel {XR_NAMESPACE} is unresolved")
            continue
        errors.append(f"declared RequiredModel {required_uri!r} is unresolved")
    if XR_NAMESPACE not in required_models:
        errors.append(f"NodeSet does not declare RequiredModel {XR_NAMESPACE}")

def check(t, ctx):
    parsed = parse_numeric_nodeid(t)
    if parsed is None:
        return
    ns, v = parsed
    if ns == OWN_NS:
        if v in defined:
            return
        errors.append(f"{ctx}: ns={OWN_NS};i={v} not defined here")
        return
    if ns == XR_NS:
        if XR is None:
            return
        if v in XR:
            return
        errors.append(f"{ctx}: ns={XR_NS};i={v} not defined in the xRegistry base model")
        return
    if UA is None:
        return
    if v in UA or v in UA_EXTRA:
        return
    errors.append(f"{ctx}: i={v} not defined here and not a known base/Part 14 id")

for tag, el in elems:
    bn = el.get("BrowseName"); nid = el.get("NodeId")
    ctx = f"{tag} {bn} ({nid})"
    parsed = parse_numeric_nodeid(nid)
    if parsed and parsed[0] == OWN_NS and parsed[1] < OWN_MIN:
        errors.append(f"{ctx}: own NodeId below reserved provisional block {OWN_MIN}")
    if el.get("ParentNodeId"):
        check(el.get("ParentNodeId"), ctx + " parent")
    if el.get("DataType"):
        check(el.get("DataType"), ctx + " datatype")
    refs = el.find(NS + "References"); rl = []
    if refs is not None:
        for r in refs:
            rt = r.get("ReferenceType"); tgt = r.text; fwd = r.get("IsForward", "true") != "false"
            rl.append((rt, tgt, fwd)); check(rt, ctx + " reftype"); check(tgt, ctx + " ref")
    reftypes = [rt for rt, _, _ in rl]
    typedef = [t for rt, t, f in rl if rt == "HasTypeDefinition"]
    is_enc = any(parse_numeric_nodeid(t) == (0, 76) for t in typedef)
    if tag in ("UAObjectType", "UADataType", "UAVariableType", "UAReferenceType"):
        if not any(rt == "HasSubtype" and not fwd for rt, _, fwd in rl):
            errors.append(f"{ctx}: type without HasSubtype(inverse)")
    if tag in ("UAVariable", "UAObject", "UAMethod") and el.get("ParentNodeId"):
        p = parse_numeric_nodeid(el.get("ParentNodeId"))
        wellknown_parent = p is not None and p[0] == 0
        cat_el = el.find(NS + "Category")
        is_instance = cat_el is not None and (cat_el.text or "").strip() == "AAS Instances"
        if "HasModellingRule" not in reftypes and not is_enc and not wellknown_parent:
            # Runtime instances under the well-known registry (and the materialized members of
            # the well-known SchemaRegistry object) are concrete, not type declarations.
            if not (parsed and parsed[1] in (1150,)) and not is_instance:
                warnings.append(f"{ctx}: instance/member without HasModellingRule")
        if tag in ("UAVariable", "UAObject") and not typedef and not is_enc:
            errors.append(f"{ctx}: missing HasTypeDefinition")

rows = [r for r in csv.reader(open(CSVF, encoding="utf-8")) if r]
csv_ids = {}
for r in rows:
    if len(r) != 3:
        errors.append(f"csv bad row {r}"); continue
    if not r[1].isdigit():
        errors.append(f"csv nonnumeric id {r}"); continue
    csv_ids[int(r[1])] = (r[2], r[0])
for num, (tag, bn) in defined.items():
    if num not in csv_ids:
        errors.append(f"ns={OWN_NS};i={num} {bn} missing from CSV")
    elif csv_ids[num][0] != tag[2:]:
        errors.append(f"class mismatch ns={OWN_NS};i={num}")
for cid in csv_ids:
    if cid not in defined:
        errors.append(f"csv id {cid} not in XML")

# The AASRegistry well-known instance is a component of the Server object (PubSub-independent).
registry = next((el for tag, el in elems if el.get("NodeId") == "ns=2;i=1150"), None)
if registry is None:
    errors.append("AASRegistry well-known instance ns=2;i=1150 missing")
elif registry.get("ParentNodeId") != "i=2253":
    errors.append("AASRegistry well-known instance is not parented by the Server object i=2253")

# The generated Annex A is embedded verbatim in the specification, so a regeneration that
# is not carried into the document is caught here rather than by a reader.
_annex = os.path.join(HERE, "model-reference.md")
_spec = os.path.join(GEN, "OPC-UA-AAS.md")
if os.path.exists(_annex) and os.path.exists(_spec):
    with open(_annex, encoding="utf-8") as f:
        rendered = f.read()
    with open(_spec, encoding="utf-8") as f:
        spec_text = f.read()
    if '<a id="annex-a"></a>' not in spec_text:
        errors.append('spec is missing the <a id="annex-a"></a> Annex A marker')
    elif rendered.strip() not in spec_text.replace("\r\n", "\n"):
        errors.append("generated Annex A (tools/model-reference.md) is not embedded verbatim in the spec")

print(
    f"XML nodes: {len(defined)}   CSV rows: {len(rows)}   "
    f"base ids: {len(UA) if UA is not None else 'skipped (no local base table)'}   "
    "xRegistry base ids: "
    f"{str(len(XR)) + ' from ' + os.path.relpath(_xr_csv, GEN) if XR is not None else 'NOT CHECKED (no table found; cross-model references accepted unverified)'}")

# Negative control: a declared tracked dependency must never degrade into
# "accept every reference" when its file disappears.
try:
    resolve_required_csv("urn:missing:test-model", [
        os.path.join(HERE, "fixtures", "__missing_required_model__.csv"),
    ])
except FileNotFoundError:
    print("detected missing RequiredModel dependency")
else:
    errors.append("missing RequiredModel dependency was silently accepted")

# --- AddressSpace figures agree with the model they draw ------------------------
# A node table is generated from the NodeSet and so cannot drift. A figure is authored,
# and a wrong arrow looks exactly like a right one, so it is re-derived from the model.
_fig_spec = os.path.join(GEN, 'OPC-UA-AAS.md')
_fig_tools = os.path.abspath(os.path.join(HERE, "..", "..", "..", "word-drafts", "tools"))
if os.path.isdir(_fig_tools) and os.path.exists(_fig_spec):
    if _fig_tools not in sys.path:
        sys.path.insert(0, _fig_tools)
    try:
        from opcdocx import nodeset_diagram as _nd
    except ImportError as _exc:
        warnings.append(f"model-figure check skipped: {_exc}")
    else:
        try:
            errors.extend(_nd.check_markdown(_fig_spec, XML))
        except ValueError as _exc:
            errors.append(f"model figure: {_exc}")

print(f"ERRORS: {len(errors)}")
for e in errors[:50]: print("  ERR", e)
print(f"WARNINGS: {len(warnings)}")
for w in warnings[:40]: print("  WARN", w)
sys.exit(1 if errors else 0)
