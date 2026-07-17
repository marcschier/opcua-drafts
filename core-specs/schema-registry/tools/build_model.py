#!/usr/bin/env python3
"""
Generator for the OPC UA Schema Registry companion NodeSet (WG draft).

Emits, from a single in-code source of truth:
  * Opc.Ua.SchemaRegistry.NodeSet2.xml
  * Opc.Ua.SchemaRegistry.NodeIds.csv
  * tools/model-reference.md

The model is a companion namespace (http://opcfoundation.org/UA/SchemaRegistry/).
Draft numeric identifiers are provisional and drawn from 62000+; final NodeIds are
assigned by the OPC Foundation. Runtime schema document nodes may additionally use
Opaque NodeIds whose identifier bytes are the raw SchemaId fingerprint.
"""
from __future__ import annotations
import os
import re
import xml.sax.saxutils as sx

# Base NodeIds
HasComponent = "i=47"
HasProperty = "i=46"
HasSubtype = "i=45"
Organizes = "i=35"
HasTypeDefinition = "i=40"
HasModellingRule = "i=37"

MR_Mandatory = "i=78"
MR_Optional = "i=80"
MR_OptionalPlaceholder = "i=11508"

BaseObjectType = "i=58"
FolderType = "i=61"
BaseDataVariableType = "i=63"
PropertyType = "i=68"
DataTypeEncodingType = "i=76"

Boolean = "i=1"
UInt32 = "i=7"
String = "i=12"
DateTime = "i=13"
ByteString = "i=15"
Duration = "i=290"
Argument = "i=296"
ConfigurationVersionDataType = "i=14593"
PublishSubscribe = "i=14443"
Server = "i=2253"

XR_NS = 1          # required model: the abstract xRegistry base (http://opcfoundation.org/UA/xRegistry/)
OWN_NS = 2         # this specification's own namespace (SchemaRegistry)
OWN_MIN = 62000
_next_member = [62500]

class Node:
    __slots__ = ("nid", "cls", "bname", "symbolic", "display", "desc", "parent", "attrs", "refs", "category", "definition", "value", "abstract")
    def __init__(self, nid, cls, bname, symbolic, display=None, desc=None, parent=None, attrs=None, category=None, abstract=False):
        self.nid = nid
        self.cls = cls
        self.bname = bname
        self.symbolic = symbolic
        self.display = display or bname
        self.desc = desc
        self.parent = parent
        self.attrs = attrs or {}
        self.refs = []
        self.category = category
        self.definition = None
        self.value = None
        self.abstract = abstract

NODES = {}
ORDER = []

def T(nid):
    return f"ns={OWN_NS};i={nid}"

def X(nid):
    """Reference to an abstract xRegistry base type (required model)."""
    return f"ns={XR_NS};i={nid}"

# abstract xRegistry base types this spec extends
XRegistry_RegistryType = X(63000)
XRegistry_GroupType = X(63001)
XRegistry_ResourceType = X(63002)

def _mid():
    v = _next_member[0]
    _next_member[0] += 1
    return v

def add(nid, cls, bname, symbolic, display=None, desc=None, parent=None, attrs=None, category=None, abstract=False):
    n = Node(nid, cls, bname, symbolic, display, desc, parent, attrs, category, abstract)
    NODES[nid] = n
    ORDER.append(nid)
    return n

def ref(nid, reftype, target, forward=True):
    NODES[nid].refs.append((reftype, target, forward))

# Builders
def object_type(nid, name, base, desc, category, abstract=False):
    add(nid, "UAObjectType", name, name, desc=desc, category=category, abstract=abstract)
    ref(nid, HasSubtype, base, forward=False)
    return nid

def _member_var(owner, owner_sym, name, datatype, typedef, rule, reftype, desc, valuerank="-1"):
    nid = _mid()
    add(nid, "UAVariable", name, f"{owner_sym}_{name.strip('<>')}", desc=desc, parent=T(owner), attrs={"DataType": datatype, "ValueRank": valuerank})
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid

def prop_var(owner, owner_sym, name, datatype, desc, rule=MR_Optional, valuerank="-1"):
    return _member_var(owner, owner_sym, name, datatype, PropertyType, rule, HasProperty, desc, valuerank)

def obj_member(owner, owner_sym, name, typedef, desc, rule=MR_Optional, reftype=HasComponent):
    nid = _mid()
    add(nid, "UAObject", name, f"{owner_sym}_{name.strip('<>')}", desc=desc, parent=T(owner))
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid

def placeholder_obj(owner, owner_sym, name, typedef, desc, rule=MR_OptionalPlaceholder, reftype=HasComponent):
    return obj_member(owner, owner_sym, name, typedef, desc, rule, reftype)

def method(owner, owner_sym, name, desc, rule=MR_Optional, inargs=None, outargs=None):
    nid = _mid()
    add(nid, "UAMethod", name, f"{owner_sym}_{name}", desc=desc, parent=T(owner))
    ref(nid, HasModellingRule, rule)
    ref(nid, HasComponent, T(owner), forward=False)
    ref(owner, HasComponent, T(nid))
    if inargs:
        _args(nid, f"{owner_sym}_{name}", "InputArguments", inargs)
    if outargs:
        _args(nid, f"{owner_sym}_{name}", "OutputArguments", outargs)
    return nid

def _args(method_nid, method_sym, bname, args):
    nid = _mid()
    add(nid, "UAVariable", bname, f"{method_sym}_{bname}", parent=T(method_nid), attrs={"DataType": Argument, "ValueRank": "1", "ArrayDimensions": str(len(args))})
    ref(nid, HasModellingRule, MR_Mandatory)
    ref(nid, HasTypeDefinition, PropertyType)
    ref(nid, HasProperty, T(method_nid), forward=False)
    ref(method_nid, HasProperty, T(nid))
    parts = ['<Value>', '<ListOfExtensionObject xmlns="http://opcfoundation.org/UA/2008/02/Types.xsd">']
    for arg in args:
        aname, adtype, adesc = arg[0], arg[1], arg[2]
        arank = arg[3] if len(arg) > 3 else -1
        parts.append("<ExtensionObject><TypeId><Identifier>i=297</Identifier></TypeId><Body><Argument>")
        parts.append(f"<Name>{sx.escape(aname)}</Name><DataType><Identifier>{adtype}</Identifier></DataType>")
        if arank is not None and arank >= 0:
            parts.append(f"<ValueRank>{arank}</ValueRank><ArrayDimensions><UInt32>0</UInt32></ArrayDimensions>")
        else:
            parts.append("<ValueRank>-1</ValueRank><ArrayDimensions/>")
        if adesc:
            parts.append(f"<Description><Text>{sx.escape(adesc)}</Text></Description>")
        parts.append("</Argument></Body></ExtensionObject>")
    parts.append("</ListOfExtensionObject></Value>")
    NODES[nid].value = "".join(parts)

# Model
CAT = "Schema Registry"
CAT_INST = "Schema Registry Instances"

object_type(62000, "SchemaRegistryType", XRegistry_RegistryType,
            "The in-server Schema Registry root - an xRegistry RegistryType (a FolderType) whose group "
            "folders hold schema files. Adds SchemaId-based resolution (GetSchema and the Opaque SchemaId "
            "NodeId fast path). Exposed as a well-known object under the Server object; a server does not "
            "have to support PubSub to be a schema registry.", CAT)
object_type(62001, "SchemaGroupType", XRegistry_GroupType,
            "An xRegistry GroupType keyed by an OPC UA namespace URI; a folder of schema files for the "
            "DataTypes and PublishedDataSets of that namespace.", CAT)
object_type(62002, "SchemaFileType", XRegistry_ResourceType,
            "An xRegistry ResourceType whose file content is one concrete schema document (Avro, Apache "
            "Arrow or JSON Schema). Adds the OPC UA schema-decoding metadata (SchemaId and per-encoding fields) "
            "used by a consumer that must resolve a schema from an on-wire fingerprint.", CAT)

SR = "SchemaRegistryType"
placeholder_obj(62000, SR, "<SchemaGroup>", T(62001), "A schema group folder (per OPC UA namespace) held by the registry.")
method(62000, SR, "GetSchema",
       "Return the schema document and metadata for a raw on-wire SchemaId fingerprint (the method form of the Opaque SchemaId NodeId fast path). An unresolved SchemaId returns the Method Call StatusCode Bad_NotFound rather than an empty result.",
       inargs=[("SchemaId", ByteString, "Raw on-wire SchemaId fingerprint bytes.")],
       outargs=[("Document", ByteString, "Schema document bytes."), ("Format", String, "xRegistry format string."), ("ContentType", String, "Schema document media type.")])

SG = "SchemaGroupType"
prop_var(62001, SG, "NamespaceUri", String, "The OPC UA namespace URI represented by this schema group (the xRegistry group key).", rule=MR_Mandatory)
placeholder_obj(62001, SG, "<Schema>", T(62002), "A schema file (one DataType/DataSet in one format) held by this group.")

SF = "SchemaFileType"
prop_var(62002, SF, "SchemaId", ByteString, "Raw on-wire SchemaId fingerprint bytes. The schema file is additionally addressable by an Opaque NodeId whose identifier bytes are exactly this value.", rule=MR_Mandatory)
prop_var(62002, SF, "SchemaIdAlg", String, "SchemaId algorithm name, such as CRC-64-AVRO or SHA-256.", rule=MR_Mandatory)
prop_var(62002, SF, "DataTypeEncoding", String, "The OPC UA DataTypeEncoding name, for example Default Avro or Default Arrow.")
prop_var(62002, SF, "Compatibility", String, "xRegistry compatibility mode governing this schema's versions, such as NONE, BACKWARD, FORWARD or FULL. All versions of one schema adhere to this mode; a breaking change starts a new schema.")
prop_var(62002, SF, "IsDefault", Boolean, "xRegistry isdefault: true when this file is the schema's default (latest) version in the flat projection.")
prop_var(62002, SF, "Ancestor", String, "xRegistry ancestor: the versionid of the version this one derives from, establishing the version lineage.")
prop_var(62002, SF, "ModelVersion", String, "OPC UA NodeSet model version label (opcua.modelversion).")
prop_var(62002, SF, "ConfigurationVersion", ConfigurationVersionDataType, "PubSub DataSet schema profile only: the Part 14 ConfigurationVersion (opcua.configurationversion) when the schema describes a DataSet. Omitted for a non-PubSub schema registry.")
prop_var(62002, SF, "ExpiryTime", DateTime, "Optional UTC expiry time for mirror/cache mode.")
prop_var(62002, SF, "Ttl", Duration, "Optional time-to-live for mirror/cache mode.")

# Well-known instance hooked onto the Server object (PubSub-independent).
add(62100, "UAObject", "SchemaRegistry", "SchemaRegistry", desc="Server-wide in-server Schema Registry, a well-known component of the Server object. A server that supports PubSub may additionally reference this object from PublishSubscribe.", parent=Server, category=CAT_INST)
ref(62100, HasTypeDefinition, T(62000))
ref(62100, HasComponent, Server, forward=False)

# Emission
NAMESPACE = "http://opcfoundation.org/UA/SchemaRegistry/"
VERSION = "0.1.0"
PUBDATE = "2026-07-16T00:00:00Z"
ALIASES = [
    ("Boolean", Boolean), ("UInt32", UInt32), ("String", String), ("DateTime", DateTime),
    ("ByteString", ByteString), ("Duration", Duration), ("Argument", Argument),
    ("Organizes", Organizes), ("HasModellingRule", HasModellingRule),
    ("HasTypeDefinition", HasTypeDefinition), ("HasSubtype", HasSubtype),
    ("HasProperty", HasProperty), ("HasComponent", HasComponent),
]
REFTYPE_ALIAS = {v: k for k, v in ALIASES}
DATATYPE_ALIAS = {v: k for k, v in ALIASES}
_PRIO = {HasModellingRule: 0, HasSubtype: 1}

def _sorted_refs(refs):
    return sorted(range(len(refs)), key=lambda i: (_PRIO.get(refs[i][0], 2), i))

def _fmt_reftype(t):
    return REFTYPE_ALIAS.get(t, t)

def _fmt_datatype(t):
    return DATATYPE_ALIAS.get(t, t)

def _fmt_browse_name(n):
    return f"{OWN_NS}:{sx.escape(n.bname)}"

def _emit_node(n):
    a = [f'{n.cls} NodeId="{T(n.nid)}"', f'BrowseName="{_fmt_browse_name(n)}"']
    if n.parent is not None:
        a.append(f'ParentNodeId="{n.parent}"')
    for k in ("DataType", "ValueRank", "ArrayDimensions"):
        if k in n.attrs:
            v = _fmt_datatype(n.attrs[k]) if k == "DataType" else n.attrs[k]
            a.append(f'{k}="{v}"')
    if n.cls == "UAObjectType" and n.abstract:
        a.append('IsAbstract="true"')
    lines = ["  <" + " ".join(a) + ">"]
    lines.append(f"    <DisplayName>{sx.escape(n.display)}</DisplayName>")
    if n.desc:
        lines.append(f"    <Description>{sx.escape(n.desc)}</Description>")
    if n.category:
        lines.append(f"    <Category>{sx.escape(n.category)}</Category>")
    lines.append("    <References>")
    for i in _sorted_refs(n.refs):
        rt, tgt, fwd = n.refs[i]
        lines.append(f'      <Reference ReferenceType="{_fmt_reftype(rt)}"{("" if fwd else " IsForward=\"false\"")}>{tgt}</Reference>')
    lines.append("    </References>")
    if n.definition:
        lines.append("    " + n.definition)
    if n.value:
        lines.append("    " + n.value)
    lines.append(f"  </{n.cls}>")
    return "\n".join(lines)

def emit():
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<!-- OPC UA Schema Registry companion namespace. PROVISIONAL NodeIds (final IDs assigned by the OPC Foundation). -->',
           '<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
           '  <NamespaceUris>', '    <Uri>http://opcfoundation.org/UA/xRegistry/</Uri>', f'    <Uri>{NAMESPACE}</Uri>', '  </NamespaceUris>',
           '  <Models>', f'    <Model ModelUri="{NAMESPACE}" Version="{VERSION}" PublicationDate="{PUBDATE}">',
           '      <RequiredModel ModelUri="http://opcfoundation.org/UA/" Version="1.05.04" PublicationDate="2024-05-01T00:00:00Z" />',
           '      <RequiredModel ModelUri="http://opcfoundation.org/UA/xRegistry/" Version="0.1.0" PublicationDate="2026-07-16T00:00:00Z" />',
           '    </Model>', '  </Models>', '  <Aliases>']
    for name, val in ALIASES:
        out.append(f'    <Alias Alias="{name}">{val}</Alias>')
    out.append('  </Aliases>')
    for nid in ORDER:
        out.append(_emit_node(NODES[nid]))
    out.append('</UANodeSet>')
    return "\n".join(out) + "\n"

def emit_csv():
    return "\n".join(f"{NODES[nid].symbolic},{nid},{NODES[nid].cls[2:]}" for nid in ORDER) + "\n"

LINK_MAP = {
    "BaseObjectType": "https://reference.opcfoundation.org/specs/OPC-10000-5/6.2",
    "FolderType": "https://reference.opcfoundation.org/specs/OPC-10000-5/6.6",
    "PropertyType": "https://reference.opcfoundation.org/specs/OPC-10000-5/7.3",
    "BaseDataVariableType": "https://reference.opcfoundation.org/specs/OPC-10000-5/7.4",
    "ConfigurationVersionDataType": "https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.2.6",
    "RegistryType": "OPC-UA-xRegistry.md#type-RegistryType",
    "GroupType": "OPC-UA-xRegistry.md#type-GroupType",
    "ResourceType": "OPC-UA-xRegistry.md#type-ResourceType",
}
_BASE_NAMES = {"i=58": "BaseObjectType", "i=61": "FolderType", "i=63": "BaseDataVariableType", "i=68": "PropertyType"}
# abstract xRegistry base types this spec extends (required model, ns=1)
_XR_NAMES = {XRegistry_RegistryType: "RegistryType", XRegistry_GroupType: "GroupType", XRegistry_ResourceType: "ResourceType"}
_OWN = None

def _friendly(tgt):
    if tgt in _BASE_NAMES:
        return _BASE_NAMES[tgt]
    if tgt in _XR_NAMES:
        return _XR_NAMES[tgt]
    if tgt in DATATYPE_ALIAS:
        return DATATYPE_ALIAS[tgt]
    if tgt.startswith(f"ns={OWN_NS};i="):
        num = int(tgt.split("i=")[1])
        if num in NODES:
            return NODES[num].bname
    if tgt == ConfigurationVersionDataType:
        return "ConfigurationVersionDataType"
    return tgt

def _anchor(name):
    return "type-" + name

def _link(display):
    if not display:
        return display
    arr = ""
    core = display
    if core.endswith("[]"):
        arr = r"\[\]"; core = core[:-2]
    if core in _OWN:
        return f"[{core}](#{_anchor(core)})" + arr
    if core in LINK_MAP:
        return f"[{core}]({LINK_MAP[core]})" + arr
    return core + arr

def _member_rule(n):
    for rt, tgt, fwd in n.refs:
        if rt == HasModellingRule:
            return {MR_Mandatory: "Mandatory", MR_Optional: "Optional", MR_OptionalPlaceholder: "OptionalPlaceholder"}.get(tgt, "")
    return ""

def _supertype(n):
    for rt, tgt, fwd in n.refs:
        if rt == HasSubtype and not fwd:
            return tgt
    return ""

def _members_of(nid):
    out = []
    for rt, tgt, fwd in NODES[nid].refs:
        if rt in (HasComponent, HasProperty, Organizes) and fwd and tgt.startswith(f"ns={OWN_NS};i="):
            num = int(tgt.split("i=")[1])
            if num in NODES:
                out.append(num)
    return out

def emit_md():
    global _OWN
    _OWN = {NODES[nid].bname for nid in ORDER if NODES[nid].cls in ("UAObjectType", "UADataType", "UAReferenceType")}
    obj_types = [nid for nid in ORDER if NODES[nid].cls == "UAObjectType"]
    method_args = {}
    method_out = {}
    for nid in ORDER:
        n = NODES[nid]
        if n.cls == "UAVariable" and n.bname in ("InputArguments", "OutputArguments") and n.value:
            names = re.findall(r"<Name>([^<]+)</Name>", n.value)
            pid = int(n.parent.split("i=")[1]) if n.parent else None
            if n.bname == "InputArguments": method_args[pid] = names
            else: method_out[pid] = names
    md = ['<a id="annex-a"></a>', '', '## Annex A — Information model\n',
          'This annex is the normative node reference. It is generated from `tools/build_model.py` and always matches `Opc.Ua.SchemaRegistry.NodeSet2.xml`. All nodes are proposed additions in the companion namespace `http://opcfoundation.org/UA/SchemaRegistry/` (namespace index `2` in this NodeSet, after the required `http://opcfoundation.org/UA/xRegistry/` base model at index `1`). The Schema Registry types **extend the abstract [OPC UA — xRegistry](OPC-UA-xRegistry.md) base types** (`RegistryType`/`GroupType`/`ResourceType`). The numeric NodeIds shown are **provisional** (final IDs are assigned by the OPC Foundation). The **Declared in** column marks members inherited from a supertype.\n']
    md.append('### Type overview\n')
    md.append('| NodeId | BrowseName | NodeClass | Subtype of |')
    md.append('|---|---|---|---|')
    for nid in obj_types:
        n = NODES[nid]
        md.append(f"| ns={OWN_NS};i={nid} | {_link(n.bname)} | {n.cls[2:]} | {_link(_friendly(_supertype(n)))} |")
    md.append('')
    md.append('### Object types\n')
    for nid in obj_types:
        n = NODES[nid]
        md.append(f'<a id="{_anchor(n.bname)}"></a>')
        md.append('')
        md.append(f"#### {n.bname}  (ns={OWN_NS};i={nid})\n")
        md.append(f"*Inherits from:* {_link(_friendly(_supertype(n)))}\n")
        if n.desc: md.append(n.desc + "\n")
        rows = []
        for m in _members_of(nid):
            mn = NODES[m]
            dt = _friendly(mn.attrs.get("DataType", "")) if mn.attrs.get("DataType") else ""
            if mn.attrs.get("ValueRank") == "1" and dt: dt += "[]"
            rows.append((mn.bname, mn.cls[2:], _link(dt), _member_rule(mn), n.bname, (mn.desc or "").replace("|", "/")))
        if rows:
            md.append('| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |')
            md.append('|---|---|---|---|---|---|')
            for r in rows:
                md.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")
            md.append('')
    md.append('### Methods\n')
    md.append('| Method | Owning type | Input arguments | Output arguments |')
    md.append('|---|---|---|---|')
    for nid in ORDER:
        n = NODES[nid]
        if n.cls != "UAMethod": continue
        owner = NODES[int(n.parent.split("i=")[1])].bname if n.parent else ""
        md.append(f"| {n.bname} | {_link(owner)} | {', '.join(method_args.get(nid, [])) or '(none)'} | {', '.join(method_out.get(nid, [])) or '(none)'} |")
    md.append('')
    md.append('### Well-known instances\n')
    md.append('| BrowseName | NodeId | TypeDefinition | Note |')
    md.append('|---|---|---|---|')
    for nid in ORDER:
        n = NODES[nid]
        if n.category != CAT_INST or n.cls != "UAObject": continue
        td = ""
        for rt, tgt, fwd in n.refs:
            if rt == HasTypeDefinition: td = _link(_friendly(tgt))
        md.append(f"| {n.bname} | ns={OWN_NS};i={nid} | {td} | {(n.desc or '').replace('|','/')} |")
    md.append('')
    return "\n".join(md) + "\n"

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.dirname(here)
    with open(os.path.join(outdir, "Opc.Ua.SchemaRegistry.NodeSet2.xml"), "w", encoding="utf-8") as f:
        f.write(emit())
    with open(os.path.join(outdir, "Opc.Ua.SchemaRegistry.NodeIds.csv"), "w", encoding="utf-8") as f:
        f.write(emit_csv())
    with open(os.path.join(here, "model-reference.md"), "w", encoding="utf-8") as f:
        f.write(emit_md())
    nt = sum(1 for k in NODES if NODES[k].cls in ("UAObjectType", "UADataType", "UAReferenceType"))
    print(f"Nodes: {len(NODES)}  (types: {nt})")
    print(f"Member id range: 62500..{_next_member[0] - 1}")
