#!/usr/bin/env python3
"""
Generator for the abstract OPC UA xRegistry companion NodeSet (WG draft).

Emits, from a single in-code source of truth:
  * Opc.Ua.XRegistry.NodeSet2.xml
  * Opc.Ua.XRegistry.NodeIds.csv
  * tools/model-reference.md

This is the REUSABLE base type system for the xRegistry model
(registry -> groups -> resources/versions) expressed over the OPC UA
FileTransfer model: a registry and its groups are FileDirectoryType
directories; a resource/version document is a FileType file. Domain
specifications (Schema Registry now, WoT-file registry later) subtype these
base types. Namespace http://opcfoundation.org/UA/xRegistry/; draft numeric
identifiers are provisional and drawn from 63000+.
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
# FileTransfer base types (OPC 10000-5 / OPC 10000-20)
FileType = "i=11575"
FileDirectoryType = "i=13353"

Boolean = "i=1"
UInt32 = "i=7"
String = "i=12"
DateTime = "i=13"
ByteString = "i=15"
ExpandedNodeId = "i=18"
Duration = "i=290"
Argument = "i=296"
KeyValuePair = "i=14533"
NodeId = "i=17"
Structure = "i=22"
HasEncoding = "i=38"
DataTypeEncodingType = "i=76"

OWN_NS = 1
OWN_MIN = 63000
_next_member = [63500]

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

def placeholder_obj(owner, owner_sym, name, typedef, desc, rule=MR_OptionalPlaceholder, reftype=Organizes):
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

DATATYPE_FIELDS = {}

def data_type(nid, name, fields, desc, category, base=Structure, encodings=("Binary", "JSON")):
    """Emit a Structure DataType with a StructureDefinition and DataTypeEncoding objects.

    fields: list of (FieldName, DataType, Description, valuerank) - valuerank optional (default -1 scalar).
    """
    add(nid, "UADataType", name, name, desc=desc, category=category)
    ref(nid, HasSubtype, base, forward=False)
    DATATYPE_FIELDS[nid] = fields
    parts = [f'<Definition Name="{sx.escape(name)}">']
    for f in fields:
        fname, fdt, fdesc = f[0], f[1], f[2]
        frank = f[3] if len(f) > 3 else -1
        attrs = f'Name="{sx.escape(fname)}" DataType="{fdt}"'
        if frank is not None and frank >= 0:
            attrs += f' ValueRank="{frank}"'
        parts.append(f"<Field {attrs}>")
        if fdesc:
            parts.append(f"<Description>{sx.escape(fdesc)}</Description>")
        parts.append("</Field>")
    parts.append("</Definition>")
    NODES[nid].definition = "".join(parts)
    for enc in encodings:
        enc_nid = _mid()
        bn = f"Default {enc}"
        add(enc_nid, "UAObject", bn, f"{name}_Default{enc}", parent=T(nid), attrs={"_ns0bn": True})
        ref(enc_nid, HasTypeDefinition, DataTypeEncodingType)
        ref(enc_nid, HasEncoding, T(nid), forward=False)
        ref(nid, HasEncoding, T(enc_nid))
    return nid

def common_attrs(nid, sym):
    """The xRegistry attributes common to a registry, group and resource entity."""
    prop_var(nid, sym, "Xid", String, "xRegistry relative identifier (xid): the entity's stable path within the registry, independent of the hosting endpoint.")
    prop_var(nid, sym, "Epoch", UInt32, "xRegistry epoch: a counter that increments on every change to the entity.")
    prop_var(nid, sym, "Name", String, "Human-readable name of the entity.")
    prop_var(nid, sym, "Description", String, "Human-readable description of the entity.")
    prop_var(nid, sym, "Documentation", String, "URL to human-readable documentation for the entity.")
    obj_member(nid, sym, "Labels", T(63003),
               "The entity's extensible xRegistry labels/attributes, exposed as an AttributesType container: each label "
               "is a browsable PropertyType Variable, added and removed with the container's AddAttribute/RemoveAttribute "
               "Methods. Deleted together with the entity.", rule=MR_Optional)
    prop_var(nid, sym, "CreatedAt", DateTime, "UTC timestamp when the entity was created.")
    prop_var(nid, sym, "ModifiedAt", DateTime, "UTC timestamp when the entity was last modified.")

# Model
CAT = "xRegistry"

object_type(63000, "RegistryType", FolderType,
            "The abstract xRegistry root, expressed as a FolderType that organizes its Group objects. It creates groups "
            "through the CreateGroup Method; a group is removed with its own Delete Method. The physical "
            "backing may be a file-system directory, but the type is a plain organizing folder. Domain registries "
            "subtype this.", CAT)
object_type(63001, "GroupType", FolderType,
            "An abstract xRegistry group, expressed as a FolderType that organizes its resource files. It creates "
            "resources and versions through the CreateResource Method and is removed with its own Delete Method. "
            "Domain group types subtype this and add the group key (e.g. a namespace URI).", CAT)
object_type(63002, "ResourceType", FileType,
            "An abstract xRegistry resource/version whose document IS the file: the content is read and written "
            "through the inherited FileType methods (Open/Read/Write/Close). Carries the xRegistry attributes and "
            "an optional ExternalReference for federation. Domain resource types subtype this.", CAT)
object_type(63003, "AttributesType", BaseObjectType,
            "A container for an entity's extensible xRegistry attributes/labels. Each attribute materializes as a "
            "browsable HasProperty PropertyType Variable whose BrowseName is the attribute key, so attributes can be "
            "browsed, read and enumerated, and are deleted with the owning entity. The AddAttribute/RemoveAttribute "
            "Methods add and remove attributes. This follows the OPC UA extensible-container pattern (an "
            "OptionalPlaceholder Property plus Add/Remove Methods); the placeholder isolates dynamic attributes so "
            "they never conflict with an entity's fixed attribute BrowseNames.", CAT)

AT = "AttributesType"
prop_var(63003, AT, "<Attribute>", String,
         "An xRegistry attribute or label materialized as a PropertyType Variable: the BrowseName is the attribute key "
         "and the Value is its string value. OptionalPlaceholder so a server exposes one Variable per present attribute.",
         rule=MR_OptionalPlaceholder)
method(63003, AT, "AddAttribute",
       "Add or update an xRegistry attribute/label in this container. The server materializes it as a browsable "
       "PropertyType Variable whose BrowseName is the Key, and increments the owning entity's Epoch. If ExpectedEpoch "
       "is non-zero and does not equal the owning entity's current Epoch, the call fails with Bad_InvalidState and "
       "makes no change (optimistic concurrency). Success or failure is conveyed by the Method Call StatusCode.",
       inargs=[("Key", String, "Attribute (or label) name."), ("Value", String, "Attribute value."),
               ("ExpectedEpoch", UInt32, "Expected current Epoch of the owning entity for optimistic concurrency; 0 disables the check.")])
method(63003, AT, "RemoveAttribute",
       "Remove an xRegistry attribute/label (the Variable whose BrowseName is the Key) from this container. If "
       "ExpectedEpoch is non-zero and does not equal the owning entity's current Epoch, the call fails with "
       "Bad_InvalidState and makes no change. Success or failure is conveyed by the Method Call StatusCode.",
       inargs=[("Key", String, "Attribute (or label) name."),
               ("ExpectedEpoch", UInt32, "Expected current Epoch of the owning entity for optimistic concurrency; 0 disables the check.")])

data_type(63004, "RegistryCapabilitiesDataType",
          [("Flags", String, "The request flags the registry supports (e.g. doc, epoch, filter, inline, sort).", 1),
           ("Mutable", String, "Which parts of the registry are mutable (e.g. capabilities, model, entities).", 1),
           ("Pagination", Boolean, "Whether the registry supports pagination of collections."),
           ("ShortSelf", Boolean, "Whether the registry offers a shortself alias for entity self URLs."),
           ("SpecVersions", String, "The xRegistry specification versions the registry supports.", 1),
           ("StickyVersions", Boolean, "Whether the registry keeps the default version sticky across updates."),
           ("EnforceCompatibility", Boolean, "Whether the registry enforces version compatibility on updates."),
           ("Apis", String, "The additional API endpoints the registry offers (e.g. /export).", 1),
           ("Schemas", String, "The schema formats the registry can validate against (schema-domain registries).", 1)],
          "The typed form of the xRegistry capabilities document (xRegistry /capabilities), whose fields have a fixed "
          "schema in the xRegistry core specification. Read as a single Variant value from RegistryType.CapabilitiesInfo, "
          "in addition to the raw JSON exposed by the Capabilities FileType. Additional/vendor capability keys that are "
          "not among these fixed fields remain available through the Capabilities FileType JSON.", CAT)


RG = "RegistryType"
prop_var(63000, RG, "RegistryId", String, "xRegistry registryid: the stable identifier of this registry.", rule=MR_Mandatory)
prop_var(63000, RG, "SpecVersion", String, "The xRegistry specification version this registry conforms to.")
obj_member(63000, RG, "Capabilities", FileType,
           "The registry capabilities document (xRegistry /capabilities): a FileType whose content is the capabilities "
           "JSON, read with the inherited Open/Read/Close Methods (so an arbitrarily large document is not bounded by "
           "MaxStringLength).")
obj_member(63000, RG, "Model", FileType,
           "The registry model document (xRegistry /model): a FileType whose content is the model JSON, read with the "
           "inherited Open/Read/Close Methods. No structured DataType is defined for the model because the OPC UA "
           "AddressSpace type system (the ObjectTypes and their members) is the structural equivalent of the model.")
prop_var(63000, RG, "CapabilitiesInfo", T(63004),
         "The typed form of the registry capabilities (RegistryCapabilitiesDataType), read as a single Variant value, "
         "in addition to the raw JSON of the Capabilities FileType.")
common_attrs(63000, RG)
placeholder_obj(63000, RG, "<Group>", T(63001), "A group held by this registry.")
method(63000, RG, "CreateGroup",
       "Create a group under this registry and assign its GroupId. The server creates the GroupType Object and "
       "bootstraps its xRegistry attributes (Xid, Epoch, CreatedAt, ModifiedAt). Fails if a group with the same "
       "GroupId already exists; use GetOrCreateGroup for idempotent create-or-get.",
       inargs=[("GroupId", String, "The groupid of the group to create.")],
       outargs=[("GroupNodeId", NodeId, "NodeId of the created group Object.")])
method(63000, RG, "GetOrCreateGroup",
       "Idempotently return the group with this GroupId, creating it if absent. One-shot form that avoids a separate "
       "existence check: returns the existing GroupType Object (Created = false) or a newly created and bootstrapped "
       "one (Created = true).",
       inargs=[("GroupId", String, "The groupid to get or create.")],
       outargs=[("GroupNodeId", NodeId, "NodeId of the existing or newly created group Object."),
                ("Created", Boolean, "True if the group was created, false if it already existed.")])

GP = "GroupType"
prop_var(63001, GP, "GroupId", String, "xRegistry groupid: the stable identifier of this group. Group identifiers are globally unique for federation.", rule=MR_Mandatory)
common_attrs(63001, GP)
placeholder_obj(63001, GP, "<Resource>", T(63002), "A resource file held by this group.")
method(63001, GP, "CreateResource",
       "Create a resource - or a new version of a resource - as a ResourceType file in this group, optionally opened "
       "for writing. The server bootstraps the resource's xRegistry attributes when the file is closed. Fails if a "
       "resource with the same ResourceId already exists; use GetOrCreateResource for idempotent create-or-get.",
       inargs=[("ResourceId", String, "The resourceid of the resource; a versionid is assigned or supplied per the registry model."),
               ("RequestFileOpen", Boolean, "If true, the new resource file is opened for writing and a FileHandle is returned.")],
       outargs=[("ResourceNodeId", NodeId, "NodeId of the created resource Object."),
                ("FileHandle", UInt32, "Write handle when RequestFileOpen is true; otherwise 0.")])
method(63001, GP, "GetOrCreateResource",
       "Idempotently return the resource with this ResourceId, creating it if absent, optionally opened for writing. "
       "One-shot form that avoids a separate existence check: returns the existing ResourceType file (Created = false) "
       "or a newly created one (Created = true); a write FileHandle is returned when RequestFileOpen is true.",
       inargs=[("ResourceId", String, "The resourceid to get or create."),
               ("RequestFileOpen", Boolean, "If true, the resource file is opened for writing and a FileHandle is returned.")],
       outargs=[("ResourceNodeId", NodeId, "NodeId of the existing or newly created resource Object."),
                ("FileHandle", UInt32, "Write handle when RequestFileOpen is true; otherwise 0."),
                ("Created", Boolean, "True if the resource was created, false if it already existed.")])
method(63001, GP, "Delete",
       "Delete this group and everything it contains (its resources and their versions and labels). The xRegistry-"
       "semantic deletion Method, symmetric with CreateResource. If ExpectedEpoch is non-zero and does not equal the "
       "group's current Epoch, the call fails with Bad_InvalidState and deletes nothing; 0 disables the check. Success "
       "or failure is conveyed by the Method Call StatusCode.",
       inargs=[("ExpectedEpoch", UInt32, "Expected current Epoch of the group for optimistic concurrency; 0 disables the check.")])

RS = "ResourceType"
prop_var(63002, RS, "ResourceId", String, "xRegistry resourceid: the stable identifier of the resource within its group.", rule=MR_Mandatory)
prop_var(63002, RS, "VersionId", String, "xRegistry versionid: the identifier of the version this file represents.")
prop_var(63002, RS, "Format", String, "xRegistry format string identifying the document's schema language/shape.")
prop_var(63002, RS, "ContentType", String, "Media type (content-type) of the document bytes.")
prop_var(63002, RS, "ExternalReference", ExpandedNodeId,
         "Federation link: an ExpandedNodeId identifying this resource in another (possibly remote) registry - "
         "the ServerUri identifies the hosting registry endpoint, the NamespaceUri and Identifier identify the "
         "group and resource. Present when the document is served by reference (xRegistry <RESOURCE>url).")
prop_var(63002, RS, "ResourceUrl", String,
         "Federation link (string form): the URL from which the document can be obtained (xRegistry <RESOURCE>url), "
         "for example an opc.tcp endpoint plus browse path, or an HTTP URL.")
common_attrs(63002, RS)
method(63002, RS, "Delete",
       "Delete this resource file and everything it contains (its versions and labels). The xRegistry-semantic "
       "deletion Method, symmetric with the group's Delete and consistent with the resource being a FileType. If "
       "ExpectedEpoch is non-zero and does not equal the resource's current Epoch, the call fails with Bad_InvalidState "
       "and deletes nothing; 0 disables the check. Success or failure is conveyed by the Method Call StatusCode.",
       inargs=[("ExpectedEpoch", UInt32, "Expected current Epoch of the resource for optimistic concurrency; 0 disables the check.")])

# Emission
NAMESPACE = "http://opcfoundation.org/UA/xRegistry/"
VERSION = "0.1.0"
PUBDATE = "2026-07-16T00:00:00Z"
UA_REQUIRED_VERSION = "1.05.04"
UA_REQUIRED_PUBDATE = "2024-05-01T00:00:00Z"
ALIASES = [
    ("Boolean", Boolean), ("UInt32", UInt32), ("String", String), ("DateTime", DateTime),
    ("ByteString", ByteString), ("ExpandedNodeId", ExpandedNodeId), ("Duration", Duration),
    ("Argument", Argument), ("KeyValuePair", KeyValuePair), ("NodeId", NodeId),
    ("Organizes", Organizes), ("HasModellingRule", HasModellingRule),
    ("HasTypeDefinition", HasTypeDefinition), ("HasSubtype", HasSubtype),
    ("HasProperty", HasProperty), ("HasComponent", HasComponent), ("HasEncoding", HasEncoding),
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
    if n.attrs.get("_ns0bn"):
        return sx.escape(n.bname)
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
           '<!-- OPC UA xRegistry abstract companion namespace. Draft NodeIds (final IDs assigned by the OPC Foundation). -->',
           '<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
           '  <NamespaceUris>', f'    <Uri>{NAMESPACE}</Uri>', '  </NamespaceUris>',
           '  <Models>', f'    <Model ModelUri="{NAMESPACE}" Version="{VERSION}" PublicationDate="{PUBDATE}">',
           f'      <RequiredModel ModelUri="http://opcfoundation.org/UA/" Version="{UA_REQUIRED_VERSION}" PublicationDate="{UA_REQUIRED_PUBDATE}" />',
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
    "FileType": "https://reference.opcfoundation.org/specs/OPC-10000-20/4.2",
    "FileDirectoryType": "https://reference.opcfoundation.org/specs/OPC-10000-20/4.3.1",
    "KeyValuePair": "https://reference.opcfoundation.org/specs/OPC-10000-5/12.23",
    "ExpandedNodeId": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.2.3",
    "Structure": "https://reference.opcfoundation.org/specs/OPC-10000-5/8.24",
}
_BASE_NAMES = {"i=58": "BaseObjectType", "i=61": "FolderType", "i=63": "BaseDataVariableType",
               "i=68": "PropertyType", FileType: "FileType", FileDirectoryType: "FileDirectoryType",
               Structure: "Structure"}
_OWN = None

def _friendly(tgt):
    if tgt in _BASE_NAMES:
        return _BASE_NAMES[tgt]
    if tgt in DATATYPE_ALIAS:
        return DATATYPE_ALIAS[tgt]
    if tgt.startswith(f"ns={OWN_NS};i="):
        num = int(tgt.split("i=")[1])
        if num in NODES:
            return NODES[num].bname
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
    dt_types = [nid for nid in ORDER if NODES[nid].cls == "UADataType"]
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
          'This annex is the normative node reference. It is generated from `tools/build_model.py` and always matches `Opc.Ua.XRegistry.NodeSet2.xml`. All nodes are defined in the companion namespace `http://opcfoundation.org/UA/xRegistry/` (which requires the base OPC UA namespace); the numeric NodeIds shown are **draft** identifiers within that namespace. The **Declared in** column marks members inherited from a supertype.\n']
    md.append('### Type overview\n')
    md.append('| NodeId | BrowseName | NodeClass | Subtype of |')
    md.append('|---|---|---|---|')
    for nid in obj_types + dt_types:
        n = NODES[nid]
        md.append(f"| ns=1;i={nid} | {_link(n.bname)} | {n.cls[2:]} | {_link(_friendly(_supertype(n)))} |")
    md.append('')
    md.append('### Object types\n')
    for nid in obj_types:
        n = NODES[nid]
        md.append(f'<a id="{_anchor(n.bname)}"></a>')
        md.append('')
        md.append(f"#### {n.bname}  (ns=1;i={nid})\n")
        md.append(f"*Inherits from:* {_link(_friendly(_supertype(n)))}\n")
        if n.desc: md.append(n.desc + "\n")
        rows = []
        for m in _members_of(nid):
            mn = NODES[m]
            dt = _link(_friendly(mn.attrs.get("DataType", ""))) if mn.attrs.get("DataType") else ""
            if mn.attrs.get("ValueRank", "") == "1" and dt:
                dt += r"\[\]"
            rows.append((mn.bname, mn.cls[2:], dt, _member_rule(mn), n.bname, (mn.desc or "").replace("|", "/")))
        if rows:
            md.append("| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |")
            md.append("|---|---|---|---|---|---|")
            for r in rows:
                md.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")
            md.append('')
    if dt_types:
        md.append('### DataTypes\n')
        for nid in dt_types:
            n = NODES[nid]
            md.append(f'<a id="{_anchor(n.bname)}"></a>')
            md.append('')
            md.append(f"#### {n.bname}  (ns=1;i={nid})\n")
            md.append(f"*Subtype of:* {_link(_friendly(_supertype(n)))}\n")
            if n.desc: md.append(n.desc + "\n")
            flds = DATATYPE_FIELDS.get(nid, [])
            if flds:
                md.append("| Field | DataType | Description |")
                md.append("|---|---|---|")
                for f in flds:
                    fname, fdt, fdesc = f[0], f[1], f[2]
                    frank = f[3] if len(f) > 3 else -1
                    dt = _link(_friendly(fdt))
                    if frank is not None and frank >= 0:
                        dt += r"\[\]"
                    md.append(f"| {fname} | {dt} | {(fdesc or '').replace('|', '/')} |")
                md.append('')
    md.append('### Methods\n')
    md.append('| Method | Owning type | Input arguments | Output arguments |')
    md.append('|---|---|---|---|')
    for nid in ORDER:
        n = NODES[nid]
        if n.cls != "UAMethod":
            continue
        owner = NODES[int(n.parent.split("i=")[1])].bname if n.parent else ""
        ins = ", ".join(method_args.get(nid, [])) or "(none)"
        outs = ", ".join(method_out.get(nid, [])) or "(none)"
        md.append(f"| {n.bname} | {_link(owner)} | {ins} | {outs} |")
    md.append('')
    return "\n".join(md) + "\n"

if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.abspath(os.path.join(here, ".."))
    with open(os.path.join(outdir, "Opc.Ua.XRegistry.NodeSet2.xml"), "w", encoding="utf-8") as f:
        f.write(emit())
    with open(os.path.join(outdir, "Opc.Ua.XRegistry.NodeIds.csv"), "w", encoding="utf-8") as f:
        f.write(emit_csv())
    with open(os.path.join(here, "model-reference.md"), "w", encoding="utf-8") as f:
        f.write(emit_md())
    nt = sum(1 for k in NODES if NODES[k].cls in ("UAObjectType", "UADataType", "UAReferenceType"))
    print(f"Nodes: {len(NODES)}  (types: {nt})  member range: 63500..{_next_member[0]-1}")
