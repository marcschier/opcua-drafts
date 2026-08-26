#!/usr/bin/env python3
"""
Generator for the OPC UA for Vision Systems worked examples.

Reads a JSON descriptor and emits, deterministically:
  * ../../../vision/<folder>/Opc.Ua.<Domain>.Vision.NodeSet2.xml  - an instance overlay
  * ../../../vision/<folder>/OPC-UA-<Domain>-Vision-Addendum.md    - the addendum

Usage (from the repo root):
    python metaverse-specs/extras/vision/tools/build_examples.py            # all descriptors
    python metaverse-specs/extras/vision/tools/build_examples.py <file.json>

Why a generator at all: the sibling openusd-binding addenda have hand-authored overlay
NodeSets with no committed generator, so their prose and their XML can drift apart. Here
the descriptor is the single source of truth for both, and the overlay is regenerated
rather than edited.

Type NodeIds are resolved by importing build_model.py, so an example can never reference
a type id that the base model does not define.
"""
from __future__ import annotations
import json
import os
import re
import sys
import xml.sax.saxutils as sx

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_model as vm  # noqa: E402  (path set above)

# The AI Model Management model is a separate specification in a sibling extras tree. It is
# loaded by path rather than imported as a package so that neither generator depends on
# the other's location, and so a reader can see exactly which file is being read.
import importlib.util as _ilu  # noqa: E402
_AI_GEN = os.path.normpath(
    os.path.join(HERE, "..", "..", "ai-model-management", "tools", "build_model.py"))
_spec = _ilu.spec_from_file_location("ai_build_model", _AI_GEN)
am = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(am)

VISION_NS = vm.NAMESPACE
AI_NS = am.NAMESPACE

# Base-UA NodeIds used by the overlays. Emitted through an <Aliases> block, as the
# base NodeSets in this repository do, so the XML stays readable.
ALIASES = [
    ("Boolean", "i=1"), ("Int32", "i=6"), ("UInt32", "i=7"), ("UInt64", "i=9"),
    ("Double", "i=11"), ("String", "i=12"), ("LocalizedText", "i=21"),
    ("HasComponent", "i=47"), ("HasProperty", "i=46"),
    ("HasTypeDefinition", "i=40"), ("HasInterface", "i=17603"),
    ("Organizes", "i=35"), ("NodeId", "i=17"), ("UtcTime", "i=294"),
    ("ByteString", "i=15"),
]

HasComponent = "HasComponent"
HasProperty = "HasProperty"
HasTypeDefinition = "HasTypeDefinition"
HasInterface = "HasInterface"
Organizes = "Organizes"
FolderType = "i=61"
PropertyType = "i=68"
BaseDataVariableType = "i=63"
BaseObjectType = "i=58"
SERVER_OBJECT = "i=2253"


def method_decl(type_name, method_name):
    """NodeId of a Method's declaration on a Vision type, for MethodDeclarationId."""
    tid = TYPE_ID.get(type_name)
    for n in vm.NODES.values():
        if (n.cls == "UAMethod" and n.bname == method_name
                and n.parent == f"ns=1;i={tid}"):
            return f"ns=2;i={n.nid}"
    raise SystemExit(f"no Method '{method_name}' on '{type_name}'")


def mandatory_members(type_name):
    """Mandatory member BrowseNames declared on a Vision type, including inherited."""
    out = {}
    tid = TYPE_ID.get(type_name)
    guard = 0
    while tid is not None and guard < 20:
        guard += 1
        for n in vm.NODES.values():
            if n.parent != f"ns=1;i={tid}":
                continue
            for rt, tgt, fwd in n.refs:
                if rt == vm.HasModellingRule and tgt == vm.MR_Mandatory:
                    out.setdefault(n.bname, n)
        nxt = None
        for rt, tgt, fwd in vm.NODES[tid].refs:
            if rt == vm.HasSubtype and not fwd and tgt.startswith("ns=1;i="):
                nxt = int(tgt.split("i=")[1])
        tid = nxt
    return out

# Type BrowseName -> NodeId in the Vision namespace, taken from the base model.
TYPE_ID = {n.bname: n.nid for n in vm.NODES.values()
           if n.cls in ("UAObjectType", "UADataType", "UAReferenceType")}

# The Vision ReferenceTypes the overlays use, aliased so the XML stays readable.
for _rt in ("HasCalibration", "MountedOn"):
    ALIASES.append((_rt, f"ns=2;i={TYPE_ID[_rt]}"))
HasCalibration = "HasCalibration"
MountedOn = "MountedOn"
UsesModel = "UsesModel"

# Type BrowseName -> NodeId in the AI Model Management namespace, taken from that model.
AI_TYPE_ID = {n.bname: n.nid for n in am.NODES.values()
              if n.cls in ("UAObjectType", "UADataType", "UAReferenceType")}
ALIASES.append((UsesModel, f"ns=3;i={AI_TYPE_ID[UsesModel]}"))


def aitype(name):
    """Type NodeId in the AI Model Management namespace (index 3)."""
    if name not in AI_TYPE_ID:
        raise SystemExit(f"unknown AI type '{name}' - check ai build_model.py")
    return f"ns=3;i={AI_TYPE_ID[name]}"


def put_enum_ai(ov, parent, name, enum_name, literal, desc=None):
    """An enum Property whose DataType is declared by the AI Model Management model."""
    val = am_enum_value(enum_name, literal)
    return ov.prop(name, aitype(enum_name), v_int32(val), parent, desc)


def am_enum_value(enum_name, literal):
    for n in am.NODES.values():
        if n.bname == enum_name and n.definition:
            m = re.search(rf'<Field Name="{literal}" Value="(\d+)"', n.definition)
            if m:
                return int(m.group(1))
    raise SystemExit(f"unknown AI enum literal {enum_name}.{literal}")


def vtype(name):
    if name not in TYPE_ID:
        raise SystemExit(f"unknown Vision type '{name}' - check build_model.py")
    return f"ns=2;i={TYPE_ID[name]}"


def enum_value(enum_name, field_name):
    """Resolve an enumeration field to its integer value from the base model."""
    nid = TYPE_ID.get(enum_name)
    if nid is None:
        raise SystemExit(f"unknown enumeration '{enum_name}'")
    defn = vm.NODES[nid].definition or ""
    marker = f'Name="{field_name}" Value="'
    i = defn.find(marker)
    if i < 0:
        raise SystemExit(f"'{field_name}' is not a field of {enum_name}")
    j = i + len(marker)
    return int(defn[j:defn.find('"', j)])


class Overlay:
    """Accumulates instance nodes for one example overlay."""

    def __init__(self, example_uri):
        self.example_uri = example_uri
        self.nodes = []
        self.next_id = 5001

    def _nid(self):
        v = self.next_id
        self.next_id += 1
        return v

    def obj(self, browse, typedef, parent=None, reftype=HasComponent, desc=None,
            external_parent=None, browse_ns=1):
        nid = self._nid()
        refs = [(HasTypeDefinition, typedef, True)]
        parent_attr = None
        if external_parent is not None:
            # A node rooted at a base-UA node (the Server Object). The inverse
            # reference is all the overlay can emit; the forward reference is added by
            # the Server when it merges this NodeSet into the address space.
            refs.append((reftype, external_parent, False))
            parent_attr = external_parent
        elif parent is not None:
            refs.append((reftype, f"ns=1;i={parent}", False))
            self._add_forward(parent, reftype, nid)
            parent_attr = f"ns=1;i={parent}"
        self.nodes.append(dict(cls="UAObject", nid=nid, browse=browse, desc=desc,
                               parent=parent_attr, browse_ns=browse_ns,
                               refs=refs, attrs={}, value=None))
        return nid

    def ref(self, source, reftype, target):
        """A non-hierarchical reference between two overlay nodes, emitted on both."""
        self._add_forward(source, reftype, None, explicit=target)
        if target.startswith("ns=1;i="):
            tgt_nid = int(target.split("i=")[1])
            for n in self.nodes:
                if n["nid"] == tgt_nid:
                    n["refs"].append((reftype, f"ns=1;i={source}", False))
                    return
            raise SystemExit(f"reference target {target} not found")

    def meth(self, browse, decl_id, parent, desc=None):
        """A Method instance. Methods carry MethodDeclarationId, not HasTypeDefinition."""
        nid = self._nid()
        refs = [(HasComponent, f"ns=1;i={parent}", False)]
        self._add_forward(parent, HasComponent, nid)
        self.nodes.append(dict(cls="UAMethod", nid=nid, browse=browse, desc=desc,
                               parent=f"ns=1;i={parent}", refs=refs,
                               attrs={"MethodDeclarationId": decl_id}, value=None))
        return nid

    def struct_var(self, browse, datatype, parent, desc=None):
        """A structure-valued member, declared with the right DataType. The concrete
        value is carried in the addendum rather than encoded here."""
        return self.data_var(browse, datatype, parent, desc=desc)

    def data_var(self, browse, datatype, parent, desc=None):
        """A DataVariable component with an explicit DataType and no encoded value."""
        nid = self._nid()
        refs = [(HasTypeDefinition, BaseDataVariableType, True),
                (HasComponent, f"ns=1;i={parent}", False)]
        self._add_forward(parent, HasComponent, nid)
        self.nodes.append(dict(cls="UAVariable", nid=nid, browse=browse, desc=desc,
                               parent=f"ns=1;i={parent}",
                               refs=refs, attrs={"DataType": datatype}, value=None))
        return nid

    def folder(self, browse, parent, desc=None, browse_ns=1):
        return self.obj(browse, FolderType, parent, desc=desc, browse_ns=browse_ns)

    def prop(self, browse, datatype, value, parent, desc=None,
             typedef=PropertyType, reftype=HasProperty, browse_ns=1):
        nid = self._nid()
        refs = [(HasTypeDefinition, typedef, True),
                (reftype, f"ns=1;i={parent}", False)]
        self._add_forward(parent, reftype, nid)
        self.nodes.append(dict(cls="UAVariable", nid=nid, browse=browse, desc=desc,
                               parent=f"ns=1;i={parent}", browse_ns=browse_ns,
                               refs=refs, attrs={"DataType": datatype},
                               value=value))
        return nid

    def iface(self, node_nid, typedef):
        self._add_forward(node_nid, HasInterface, None, explicit=typedef)

    def _add_forward(self, parent, reftype, child_nid, explicit=None):
        for n in self.nodes:
            if n["nid"] == parent:
                tgt = explicit if explicit is not None else f"ns=1;i={child_nid}"
                n["refs"].append((reftype, tgt, True))
                return
        raise SystemExit(f"parent ns=1;i={parent} not found")

    def emit(self, domain):
        out = ['<?xml version="1.0" encoding="utf-8"?>',
               f'<!-- OPC UA - Vision worked example: {domain}. Generated by '
               'build_examples.py - do not edit by hand. PROVISIONAL NodeIds. -->',
               '<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
               'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
               'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" '
               'xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
               '  <NamespaceUris>',
               f'    <Uri>{sx.escape(self.example_uri)}</Uri>',
               f'    <Uri>{sx.escape(VISION_NS)}</Uri>',
               f'    <Uri>{sx.escape(AI_NS)}</Uri>',
               '  </NamespaceUris>',
               '  <Models>',
               f'    <Model ModelUri={sx.quoteattr(self.example_uri)} '
               f'Version="0.1.0" '
               f'PublicationDate="{vm.PUBDATE}">',
               '      <RequiredModel ModelUri="http://opcfoundation.org/UA/" '
               f'Version="{vm.BASE_UA_VERSION}" '
               f'PublicationDate="{vm.BASE_UA_PUBDATE}" />',
               f'      <RequiredModel ModelUri={sx.quoteattr(VISION_NS)} '
               f'Version="{vm.VERSION}" '
               f'PublicationDate="{vm.PUBDATE}" />',
               f'      <RequiredModel ModelUri={sx.quoteattr(AI_NS)} '
               f'Version="{am.VERSION}" '
               f'PublicationDate="{am.PUBDATE}" />',
               '    </Model>',
               '  </Models>',
               '  <Aliases>']
        for name, val in ALIASES:
            out.append(f'    <Alias Alias="{name}">{val}</Alias>')
        out.append('  </Aliases>')
        for n in self.nodes:
            out.append(self._emit_node(n))
        out.append('</UANodeSet>')
        return "\n".join(out) + "\n"

    @staticmethod
    def _emit_node(n):
        a = [f'{n["cls"]} NodeId="ns=1;i={n["nid"]}"',
             f'BrowseName={sx.quoteattr(str(n.get("browse_ns", 1)) + ":" + n["browse"])}']
        if n["parent"]:
            a.append(f'ParentNodeId="{n["parent"]}"')
        if "DataType" in n["attrs"]:
            a.append(f'DataType="{n["attrs"]["DataType"]}"')
        if "MethodDeclarationId" in n["attrs"]:
            a.append(f'MethodDeclarationId="{n["attrs"]["MethodDeclarationId"]}"')
        lines = ["  <" + " ".join(a) + ">"]
        lines.append(f'    <DisplayName>{sx.escape(n["browse"])}</DisplayName>')
        if n["desc"]:
            lines.append(f'    <Description>{sx.escape(n["desc"])}</Description>')
        lines.append("    <References>")
        for rt, tgt, fwd in n["refs"]:
            fs = "" if fwd else ' IsForward="false"'
            lines.append(f'      <Reference ReferenceType="{rt}"{fs}>{tgt}</Reference>')
        lines.append("    </References>")
        if n["value"] is not None:
            lines.append("    " + n["value"])
        lines.append(f'  </{n["cls"]}>')
        return "\n".join(lines)


UAX = 'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd"'


def v_string(s):
    return f'<Value><uax:String {UAX}>{sx.escape(str(s))}</uax:String></Value>'


def v_uint32(i):
    return f'<Value><uax:UInt32 {UAX}>{int(i)}</uax:UInt32></Value>'


def v_uint64(i):
    return f'<Value><uax:UInt64 {UAX}>{int(i)}</uax:UInt64></Value>'


def v_double(d):
    return f'<Value><uax:Double {UAX}>{float(d)}</uax:Double></Value>'


def v_bool(b):
    return (f'<Value><uax:Boolean {UAX}>'
            f'{"true" if b else "false"}</uax:Boolean></Value>')


def v_int32(i):
    return f'<Value><uax:Int32 {UAX}>{int(i)}</uax:Int32></Value>'


def v_nodeid(s):
    return (f'<Value><uax:NodeId {UAX}><uax:Identifier>{sx.escape(str(s))}'
            f'</uax:Identifier></uax:NodeId></Value>')


def v_datetime(s):
    return f'<Value><uax:DateTime {UAX}>{sx.escape(str(s))}</uax:DateTime></Value>'


def v_ltext(s):
    return (f'<Value><uax:LocalizedText {UAX}>'
            f'<uax:Text>{sx.escape(str(s))}</uax:Text></uax:LocalizedText></Value>')


def v_bytestring(s):
    return f'<Value><uax:ByteString {UAX}>{sx.escape(str(s))}</uax:ByteString></Value>'


# Property name -> (DataType alias, value emitter). Anything not listed is a String.
DT = {
    "UInt32": ("UInt32", v_uint32),
    "UInt64": ("UInt64", v_uint64),
    "Double": ("Double", v_double),
    "Duration": ("Duration", v_double),
    "Boolean": ("Boolean", v_bool),
    "Int32": ("Int32", v_int32),
    "String": ("String", v_string),
    "LocalizedText": ("LocalizedText", v_ltext),
    "NodeId": ("NodeId", v_nodeid),
    "UtcTime": ("UtcTime", v_datetime),
    "ByteString": ("ByteString", v_bytestring),
}


def put(ov, parent, name, kind, value, desc=None):
    dt, fn = DT[kind]
    return ov.prop(name, dt, fn(value), parent, desc=desc)


def put_enum(ov, parent, name, enum_name, field, desc=None):
    val = enum_value(enum_name, field)
    return ov.prop(name, f"ns=2;i={TYPE_ID[enum_name]}", v_int32(val), parent,
                   desc=desc or f"{enum_name}.{field}")


# ---------------------------------------------------------------------------
# Overlay construction
# ---------------------------------------------------------------------------
SECURE_SCHEMES = ("rtsps://", "https://", "srts://", "grpcs://", "wss://")


def secure_transport(uri):
    """§12.2: SecureTransport states whether the media transport itself is
    confidential. Derived from the endpoint scheme so the example cannot claim
    protection its own URI contradicts."""
    return str(uri).lower().startswith(SECURE_SCHEMES)


def add_data_channel(ov, endpoint, dc):
    """Wire the optional §6.7 data-channel path onto a media endpoint.

    The source Object is created by the Server, not by this specification, so the
    overlay emits a plain BaseObjectType standing in for it. On a Server that
    implements the OPC UA - Data Channels draft this Object would also implement
    IDataChannelSourceType and be reachable by HasDataChannel - neither of which this
    overlay emits, because those are provisional identifiers in the base namespace and
    a NodeSet referencing them would not load on a Server without that draft.
    """
    src = ov.obj(dc["sourceName"], BaseObjectType, endpoint,
                 desc="Stands in for the Server-created data channel source. On a "
                      "Server implementing the OPC UA - Data Channels draft this "
                      "Object implements IDataChannelSourceType; this overlay does not "
                      "reference that draft's provisional NodeIds, so it loads "
                      "unchanged on a Server without it.")
    put(ov, endpoint, "DataChannelSource", "NodeId", f"ns=1;i={src}",
        desc="The Object on which a client opens the data channel (§6.7).")
    put(ov, endpoint, "DataChannelContentType", "String", dc["contentType"],
        desc="IANA media type carried on the data channel (§6.7).")
    return src


def build_media(ov, sensor, st, cl):
    """Media management object with one stream and one clip endpoint."""
    media = ov.obj("Media", vtype("VisionMediaManagementType"), sensor,
                   desc="Media endpoints and their control surface.")
    streams = ov.folder("StreamEndpoints", media)
    clips = ov.folder("ClipEndpoints", media)

    stream = ov.obj(st["name"], vtype("StreamEndpointType"), streams,
                    desc=st.get("description"))
    put(ov, stream, "EndpointId", "String", st["endpointId"])
    put(ov, stream, "EndpointUri", "String", st["endpointUri"])
    put_enum(ov, stream, "StreamProtocol", "VisionStreamProtocolEnum", st["protocol"])
    put(ov, stream, "ProtocolVersion", "String", st.get("protocolVersion", "1.0"))
    put_enum(ov, stream, "State", "VisionEndpointStateEnum", st.get("state", "Ready"))
    put_enum(ov, stream, "Authentication", "VisionEndpointAuthenticationEnum",
             st.get("authentication", "Digest"))
    put(ov, stream, "SecureTransport", "Boolean", secure_transport(st["endpointUri"]),
        desc="Derived from the endpoint scheme; see base specification §12.2.")
    if "dataChannel" in st:
        add_data_channel(ov, stream, st["dataChannel"])
    if "codec" in st:
        put_enum(ov, stream, "Codec", "VisionVideoCodecEnum", st["codec"])
    for name, kind in (("Width", "UInt32"), ("Height", "UInt32"),
                       ("FrameRate", "Double")):
        key = name[0].lower() + name[1:]
        if key in st:
            put(ov, stream, name, kind, st[key])

    clip = ov.obj(cl["name"], vtype("ClipEndpointType"), clips,
                  desc=cl.get("description"))
    put(ov, clip, "EndpointId", "String", cl["endpointId"])
    put(ov, clip, "EndpointUri", "String", cl["endpointUri"])
    put_enum(ov, clip, "ClipFormat", "VisionClipFormatEnum", cl["format"])
    put_enum(ov, clip, "State", "VisionEndpointStateEnum", cl.get("state", "Ready"))
    put_enum(ov, clip, "Authentication", "VisionEndpointAuthenticationEnum",
             cl.get("authentication", "Token"))
    put(ov, clip, "SecureTransport", "Boolean", secure_transport(cl["endpointUri"]),
        desc="Derived from the endpoint scheme; see base specification §12.2.")
    if "dataChannel" in cl:
        add_data_channel(ov, clip, cl["dataChannel"])
    # Instantiating any of the four VIS-Media-Inline members claims the facet, so
    # clause 11 requires all four. InlineDeliveryEnabled = false is the "supported but
    # currently off" state of §6.4 rule 5, not the absence of the facet - an endpoint
    # that does not offer inline delivery at all simply omits the key.
    if "inlineDeliveryEnabled" in cl:
        put(ov, clip, "InlineDeliveryEnabled", "Boolean", cl["inlineDeliveryEnabled"])
        put(ov, clip, "MaxInlineClipSize", "UInt32", cl.get("maxInlineClipSize", 0))
        ov.data_var("LatestClip", "ByteString", clip,
                    desc="Most recent clip, published inline within MaxInlineClipSize. "
                         "Subscribable; see §6.4 rules 3 to 5 for the overflow, "
                         "correlation and initial-state behaviour.")
        ov.struct_var("LatestClipMetadata",
                      f"ns=2;i={TYPE_ID['VisionImageReferenceDataType']}", clip,
                      desc="Descriptor for LatestClip, carrying the Uri that remains "
                           "valid when the inline payload does not fit, and the "
                           "Timestamp and Digest that correlate the two (§6.4 rule 4).")

    # Mandatory Methods of VisionMediaManagementType.
    for mname in ("GetStreamEndpoint", "ReleaseStreamEndpoint", "GetClip"):
        ov.meth(mname, method_decl("VisionMediaManagementType", mname), media,
                desc=f"{mname} as declared by VisionMediaManagementType.")
    return media


def build_sensor(ov, name, s, sim=None, parent=None):
    """One sensor instance, physical or simulated. Both take the identical shape -
    that is the sim/real symmetry the base specification requires."""
    sensor = ov.obj(name, vtype(s["type"]), parent, reftype=Organizes,
                    desc=s.get("description"))
    if s.get("realityKind") in ("Simulated", "Hybrid"):
        ov.iface(sensor, vtype("IVisionSimulatedType"))

    put(ov, sensor, "SensorId", "String", s["sensorId"])
    put_enum(ov, sensor, "RealityKind", "VisionRealityKindEnum", s["realityKind"])
    put_enum(ov, sensor, "Modality", "VisionSensorModalityEnum", s["modality"])
    for pname, kind in (("Manufacturer", "LocalizedText"), ("Model", "LocalizedText"),
                        ("SerialNumber", "String"), ("DeviceUri", "String"),
                        ("FrameId", "String")):
        key = pname[0].lower() + pname[1:]
        if key in s:
            put(ov, sensor, pname, kind, s[key])
    if s["type"] == "ImageSensorType":
        for pname, kind in (("Width", "UInt32"), ("Height", "UInt32"),
                            ("PixelFormat", "String"), ("ExposureTime", "Double"),
                            ("Gain", "Double"), ("AcquisitionFrameRate", "Double"),
                            ("TriggerMode", "String"), ("TriggerSource", "String")):
            key = pname[0].lower() + pname[1:]
            if key in s:
                put(ov, sensor, pname, kind, s[key])

    if sim:
        put(ov, sensor, "SimulatorUri", "String", sim["simulatorUri"])
        put(ov, sensor, "StageIdentifier", "String", sim["stageIdentifier"])
        put(ov, sensor, "PrimPath", "String", sim["primPath"])
        if "groundTruthAvailable" in sim:
            put(ov, sensor, "GroundTruthAvailable", "Boolean",
                sim["groundTruthAvailable"])
        if "randomizationSeed" in sim:
            put(ov, sensor, "RandomizationSeed", "UInt64", sim["randomizationSeed"])
    return sensor


def build_overlay(d):
    ov = Overlay(d["exampleNamespaceUri"])
    s = d["sensor"]

    # The well-known entry point required by §4.2: a component of the Server Object,
    # BrowseName qualified with the Vision namespace (index 2 in this overlay).
    root = ov.obj("Vision", vtype("VisionRootType"), external_parent=SERVER_OBJECT,
                  browse_ns=2,
                  desc="Well-known Vision entry point for this example (§4.2).")
    f_sensors = ov.folder("Sensors", root)
    f_pipelines = ov.folder("Pipelines", root)
    f_frames = ov.folder("Frames", root)

    # Models, datasets, deployments and learning jobs belong to OPC UA - AI Model Management
    # and Learning, whose own well-known object sits BESIDE the Vision one under the
    # Server Object. Hanging them under the Vision root would put them in folders
    # VisionRootType does not declare, and would leave the example unable to satisfy
    # the AI-Base facet that the VIS-Inference-* and VIS-Learning facets require.
    airoot = ov.obj("AiModelManagement", aitype("AiRootType"), external_parent=SERVER_OBJECT,
                    browse_ns=3,
                    desc="Well-known AI Model Management entry point for this example.")
    ov.prop("SpecificationVersion", "String", v_string(am.VERSION), airoot,
            "Release of the AI Model Management specification this example is built against.",
            browse_ns=3)
    f_models = ov.folder("Models", airoot, browse_ns=3)
    f_datasets = ov.folder("Datasets", airoot, browse_ns=3)
    f_deployments = ov.folder("Deployments", airoot, browse_ns=3)
    f_jobs = ov.folder("LearningJobs", airoot, browse_ns=3)
    ov.roots = dict(sensors=f_sensors, pipelines=f_pipelines, models=f_models,
                    datasets=f_datasets, deployments=f_deployments,
                    frames=f_frames, jobs=f_jobs)

    sim = d.get("simulation") if s.get("realityKind") in ("Simulated", "Hybrid") else None
    sensor = build_sensor(ov, d["instanceName"], s, sim, parent=f_sensors)
    build_media(ov, sensor, d["stream"], d["clip"])

    # --- optics -------------------------------------------------------------
    if "optics" in d:
        o = d["optics"]
        optics = ov.obj("Optics", vtype("OpticsType"), sensor)
        for name in ("FocalLength", "Aperture", "WorkingDistance", "Magnification"):
            key = name[0].lower() + name[1:]
            if key in o:
                put(ov, optics, name, "Double", o[key])
        for name in ("OpticalFormat", "MountType", "LensType"):
            key = name[0].lower() + name[1:]
            if key in o:
                put(ov, optics, name, "String", o[key])

    # --- coordinate frames (built first so calibrations can reference them) ----
    frame_ids = {}
    frame_nodes = {}
    for f in d.get("frames", []):
        fr = ov.obj(f["name"], vtype("CoordinateFrameType"), ov.roots["frames"],
                    reftype=Organizes, desc=f.get("description"))
        put(ov, fr, "FrameId", "String", f["frameId"])
        put_enum(ov, fr, "Role", "VisionFrameRoleEnum", f["role"])
        frame_ids[f["frameId"]] = f"ns=1;i={fr}"
        frame_nodes[f["frameId"]] = fr
    # ParentFrame is what makes the tree composable; §7.3 and the addendum both depend
    # on a client being able to walk camera -> flange -> base.
    for f in d.get("frames", []):
        fr = frame_nodes[f["frameId"]]
        put(ov, fr, "ParentFrame", "NodeId",
            frame_ids.get(f.get("parentFrame"), "i=0"))

    # A sensor mounted on a frame says so with MountedOn (§5.11).
    if s.get("mountedOn") in frame_ids:
        ov.ref(sensor, MountedOn, frame_ids[s["mountedOn"]])

    # --- calibration --------------------------------------------------------
    if d.get("calibrations"):
        cals = ov.folder("Calibrations", sensor)
        for c in d["calibrations"]:
            cal = ov.obj(c["name"], vtype(c["type"]), cals, desc=c.get("description"))
            put(ov, cal, "CalibrationId", "String", c["calibrationId"])
            put(ov, cal, "PerformedAt", "UtcTime",
                c.get("performedAt", "2026-07-01T00:00:00Z"))
            put(ov, cal, "Valid", "Boolean", c.get("valid", True))
            if "residualError" in c:
                put(ov, cal, "ResidualError", "Double", c["residualError"])
            if "method" in c:
                put(ov, cal, "Method", "String", c["method"])
            # §5.11: the sensor a calibration belongs to is reachable by HasCalibration.
            ov.ref(sensor, HasCalibration, f"ns=1;i={cal}")
            if c["type"] == "ExtrinsicCalibrationType":
                put_enum(ov, cal, "Mount", "VisionCalibrationMountEnum", c["mount"])
                put(ov, cal, "SourceFrame", "NodeId",
                    frame_ids.get(c["sourceFrame"], "i=0"))
                put(ov, cal, "TargetFrame", "NodeId",
                    frame_ids.get(c["targetFrame"], "i=0"))
                ov.struct_var("Transform", f"ns=2;i={TYPE_ID['VisionPose3DDataType']}",
                              cal, desc="Pose of SourceFrame expressed in TargetFrame. "
                                        "The field values are tabulated in the "
                                        "addendum's calibration clause.")
            else:
                ov.struct_var("Intrinsics",
                              f"ns=2;i={TYPE_ID['VisionIntrinsicsDataType']}", cal,
                              desc="Intrinsic parameters. The field values are "
                                   "tabulated in the addendum's calibration clause.")

    # --- AI -----------------------------------------------------------------
    ai = d["ai"]
    model = ov.obj(ai["model"]["name"], aitype("ModelType"), ov.roots["models"],
                   reftype=Organizes, desc=ai["model"].get("description"))
    m = ai["model"]
    put(ov, model, "ModelId", "String", m["modelId"])
    put(ov, model, "Name", "LocalizedText", m["name"])
    put(ov, model, "Version", "String", m["version"])
    for name in ("Framework", "Format", "TaskKind", "ArtifactUri"):
        key = name[0].lower() + name[1:]
        if key in m:
            put(ov, model, name, "String", m[key])
    # §12.6 requires both for any model reachable through ArtifactUri.
    put(ov, model, "Digest", "ByteString", m["digest"],
        desc="SHA-256 of the model artefact at ArtifactUri.")
    put(ov, model, "DigestAlgorithm", "String", m.get("digestAlgorithm", "SHA-256"))

    dep = ai["deployment"]
    deployment = ov.obj(dep["name"], aitype("DeploymentType"), ov.roots["models"],
                        reftype=Organizes, desc=dep.get("description"))
    put(ov, deployment, "DeploymentId", "String", dep["deploymentId"])
    put_enum_ai(ov, deployment, "InferenceLocation", "InferenceLocationEnum",
             dep["inferenceLocation"])
    if "acceleratorKind" in dep:
        put_enum_ai(ov, deployment, "AcceleratorKind", "AcceleratorKindEnum",
                 dep["acceleratorKind"])
    if "acceleratorName" in dep:
        put(ov, deployment, "AcceleratorName", "String", dep["acceleratorName"])
    if "endpointUri" in dep:
        put(ov, deployment, "EndpointUri", "String", dep["endpointUri"])
    # UsesModel identifies the model serving now. A retained result's ModelUsed identifies
    # the model that actually produced that result.
    ov.ref(deployment, UsesModel, f"ns=1;i={model}")

    pl = ai["pipeline"]
    pipeline = ov.obj(pl["name"], vtype("InferencePipelineType"), ov.roots["pipelines"],
                      reftype=Organizes, desc=pl.get("description"))
    put(ov, pipeline, "PipelineId", "String", pl["pipelineId"])
    put(ov, pipeline, "Sensor", "NodeId", f"ns=1;i={sensor}")
    put(ov, pipeline, "Deployment", "NodeId", f"ns=1;i={deployment}")
    put_enum(ov, pipeline, "State", "VisionEndpointStateEnum",
             pl.get("state", "Active"))
    put(ov, pipeline, "Continuous", "Boolean", pl.get("continuous", True))
    ov.folder("Results", pipeline)
    ov.obj("Feedback", vtype("VisionFeedbackType"), pipeline,
           desc="Feedback surface for corrections and overlays.")

    # --- simulated twin ------------------------------------------------------
    # Emitted with exactly the same shape as the physical sensor above. That is the
    # point: a client cannot distinguish them except by reading RealityKind.
    if "twin" in d:
        tw = d["twin"]
        twin = build_sensor(ov, tw["instanceName"], tw["sensor"], tw["simulation"],
                            parent=ov.roots["sensors"])
        build_media(ov, twin, tw["stream"], tw["clip"])
        if "learningJob" in tw:
            lj = tw["learningJob"]
            dataset = ov.obj(lj["datasetName"], aitype("DatasetType"),
                             ov.roots["models"], reftype=Organizes,
                             desc="Synthetic dataset produced from the twin.")
            put(ov, dataset, "DatasetId", "String", lj["datasetId"])
            put_enum_ai(ov, dataset, "SourceKind", "DatasetSourceEnum",
                     lj.get("sourceKind", "Synthetic"))
            job = ov.obj(lj["name"], aitype("LearningJobType"), ov.roots["jobs"],
                         reftype=Organizes, desc=lj.get("description"))
            put(ov, job, "JobId", "String", lj["jobId"])
            put_enum_ai(ov, job, "State", "LearningJobStateEnum",
                     lj.get("state", "Collecting"))

    # Append new instance members only after the complete pre-existing overlay. Adding
    # them beside Results would renumber Feedback and every node generated afterwards.
    # The base type still owns these Properties; generation order exists solely to
    # preserve the examples' published NodeIds.
    put(ov, pipeline, "MaxResultAge", "Duration", pl["maxResultAge"])
    put(ov, pipeline, "MaxRetainedResults", "UInt32", pl["maxRetainedResults"])

    return ov


# ---------------------------------------------------------------------------
# Addendum
# ---------------------------------------------------------------------------
def emit_addendum(d, annex=None):
    """Render the worked example.

    With annex=None the result is the standalone addendum published next to its
    overlay. With annex set to a letter it is the same content rendered for
    embedding as an annex of OPC-UA-Vision.md: headings demoted one level and
    numbered within the annex, and relative links rebased from vision/<folder>/ to
    vision/. One renderer, so the two cannot drift.
    """
    s = d["sensor"]
    st = d["stream"]
    cl = d["clip"]
    ai = d["ai"]
    dep = ai["deployment"]
    pl = ai["pipeline"]
    up = ".." if annex else "../.."
    rel = f"{up}/extras/vision/examples/{d['folder']}/{d['descriptorFile']}"
    nodeset = f"Opc.Ua.{d['domain']}.Vision.NodeSet2.xml"
    nodeset_link = f"{d['outputFolder']}/{nodeset}" if annex else nodeset
    L = []
    A = L.append
    sec = [0]

    def head(title):
        sec[0] += 1
        A(f"### {annex}.{sec[0]} {title}" if annex else f"## {sec[0]} {title}")

    if annex:
        A(f"## Annex {annex} — Worked example: {d['annexTitle']} (informative)")
        A("")
        A(f"> {d['summary']} This annex and the overlay "
          f"[`{nodeset}`]({nodeset_link}) are both generated from "
          f"[`{d['descriptorFile']}`]({rel}) by `build_examples.py`, so prose and "
          "model cannot drift. The same content is published beside the overlay as "
          f"[`OPC-UA-{d['domain']}-Vision-Addendum.md`]"
          f"({d['outputFolder']}/OPC-UA-{d['domain']}-Vision-Addendum.md).")
        A("")
    else:
        A(f"# OPC UA {d['domain']} — Vision Addendum")
        A("")
        A(f"**Implementer annex to *OPC UA for Vision Systems* (Release {vm.VERSION} — "
          "Draft).**")
        A("")
        A(f"> {d['summary']} The machine-readable source of truth is "
          f"[`{d['descriptorFile']}`]({rel}); this document and "
          f"`{nodeset}` are both generated from it by "
          "`build_examples.py`, so prose and model cannot drift. It is also published "
          f"as Annex {d['annexLetter']} of "
          "[`OPC-UA-Vision.md`](../OPC-UA-Vision.md).")
        A("")
        A("---")
        A("")
    head("Scope")
    A("")
    A(d["scope"])
    A("")
    head("Normative references")
    A("")
    if not annex:
        A("- *OPC UA for Vision Systems*, Release " + vm.VERSION + " (the base specification), "
          "`../OPC-UA-Vision.md`.")
    for r in d.get("references", []):
        A(f"- {r}")
    if annex and not d.get("references"):
        A("None beyond the normative references of clause 2.")
    A("")
    head("The sensor")
    A("")
    A("| Member | Value |")
    A("|---|---|")
    A(f"| Type | `{s['type']}` |")
    A(f"| `SensorId` | `{s['sensorId']}` |")
    A(f"| `RealityKind` | `{s['realityKind']}` |")
    A(f"| `Modality` | `{s['modality']}` |")
    for key, label in (("width", "`Width`"), ("height", "`Height`"),
                       ("pixelFormat", "`PixelFormat`"),
                       ("exposureTime", "`ExposureTime` (µs)"),
                       ("gain", "`Gain`"),
                       ("acquisitionFrameRate", "`AcquisitionFrameRate`"),
                       ("triggerMode", "`TriggerMode`"),
                       ("deviceUri", "`DeviceUri`"),
                       ("frameId", "`FrameId`")):
        if key in s:
            A(f"| {label} | `{s[key]}` |")
    A("")
    if "simulation" in d and s["realityKind"] in ("Simulated", "Hybrid"):
        sim = d["simulation"]
        A("The sensor implements `IVisionSimulatedType`, so it is addressable in the "
          "same terms as the scene it renders:")
        A("")
        A("| Member | Value |")
        A("|---|---|")
        A(f"| `SimulatorUri` | `{sim['simulatorUri']}` |")
        A(f"| `StageIdentifier` | `{sim['stageIdentifier']}` |")
        A(f"| `PrimPath` | `{sim['primPath']}` |")
        A("")
        A("`PrimPath` resolves to a `UsdGeomCameraType` instance where the Server also "
          "implements *OPC UA — OpenUSD Scene Materialization* (base specification "
          "Annex C).")
        A("")
    head("Media endpoints")
    A("")
    A("Both mandatory defaults of base specification §6.2 are present — an RTSP stream "
      "and a JPEG clip endpoint:")
    A("")
    A("| Endpoint | Type | Key members |")
    A("|---|---|---|")
    A(f"| `{st['name']}` | `StreamEndpointType` | `StreamProtocol = {st['protocol']}`, "
      f"`EndpointUri = {st['endpointUri']}` |")
    A(f"| `{cl['name']}` | `ClipEndpointType` | `ClipFormat = {cl['format']}`, "
      f"`EndpointUri = {cl['endpointUri']}` |")
    A("")
    if cl.get("inlineDeliveryEnabled"):
        A(f"This clip endpoint additionally enables the optional **VIS-Media-Inline** "
          f"facet, with `MaxInlineClipSize = {cl['maxInlineClipSize']}` bytes. Clause 11 "
          "requires all four members of that facet together, so the endpoint "
          "instantiates `InlineDeliveryEnabled`, `MaxInlineClipSize`, `LatestClip` and "
          "`LatestClipMetadata`. A client may subscribe to `LatestClip` and receive the "
          "encoded JPEG directly; if an image exceeds that bound the Server sets "
          "`Bad_EncodingLimitsExceeded` and the client falls back to "
          "`LatestClipMetadata.Uri` (base specification §6.4).")
    else:
        A("This clip endpoint implements the optional **VIS-Media-Inline** facet but "
          "leaves it switched off: `InlineDeliveryEnabled = false`, so per base "
          "specification §6.4 rule 5 the Server reports `LatestClip` with "
          "`Bad_NotSupported` while `LatestClipMetadata` stays readable. Clips are "
          "obtained through `GetClip` and fetched from the returned `Uri`, which is the "
          "default path. Clause 11 requires the facet's four members to be present "
          "together even in this state, which is why the overlay declares all four.")
    A("")
    dc_eps = [(st, "stream"), (cl, "clip")]
    if any("dataChannel" in e for e, _k in dc_eps):
        A("Both endpoints additionally offer the optional **VIS-Media-DataChannel** "
          "facet of base specification §6.7, so this example shows the case where a "
          "data channel is an *additional* path to the same content rather than the "
          "only one:")
        A("")
        A("| Endpoint | `StreamProtocol` / `ClipFormat` | `EndpointUri` | "
          "`DataChannelSource` | `DataChannelContentType` |")
        A("|---|---|---|---|---|")
        for e, kind in dc_eps:
            if "dataChannel" not in e:
                continue
            what = e["protocol"] if kind == "stream" else e["format"]
            A(f"| `{e['name']}` | `{what}` | `{e['endpointUri']}` | "
              f"`{e['dataChannel']['sourceName']}` | "
              f"`{e['dataChannel']['contentType']}` |")
        A("")
        A("`StreamProtocol` stays `Rtsp` and `EndpointUri` keeps its out-of-band value, "
          "because per §6.7 a Server sets `StreamProtocol = DataChannel` only where the "
          "data channel is the endpoint's *only* path. A non-null `DataChannelSource` "
          "is what signals the additional path. Per §6.3 the Server will not return "
          "these on the data-channel path unless a client asks for "
          "`PreferredProtocol = DataChannel` explicitly, so a client that cannot open "
          "a data channel is unaffected.")
        A("")
        A("The source Objects in this overlay are plain `BaseObjectType` instances "
          "standing in for Server-created nodes. On a Server implementing the "
          "*OPC UA — Data Channels* draft each would also implement "
          "`IDataChannelSourceType` and be reachable by `HasDataChannel`. This overlay "
          "emits neither, because those are provisional identifiers in the **base** "
          "namespace: a NodeSet referencing them would fail to load on the majority of "
          "Servers, which have not adopted that draft. That draft is a **working "
          "draft**, and both this example and the base specification are fully "
          "conformant without it.")
        A("")
    if d.get("frames") or d.get("calibrations"):
        head("Coordinate frames and calibration")
        A("")
    if d.get("frames"):
        A("The frame tree. `ParentFrame` is what makes it composable: a client walks "
          "from the frame a pose is expressed in up to the frame it needs, composing "
          "the transforms it finds on the way.")
        A("")
        A("| Instance | `FrameId` | `Role` | `ParentFrame` |")
        A("|---|---|---|---|")
        for f in d["frames"]:
            parent = f.get("parentFrame")
            A(f"| `{f['name']}` | `{f['frameId']}` | `{f['role']}` | "
              f"{('`' + parent + '`') if parent else 'none (tree root)'} |")
        A("")
    for c in d.get("calibrations", []):
        A(f"**`{c['name']}`** (`{c['type']}`) — {c['description']}")
        A("")
        A("| Member | Value |")
        A("|---|---|")
        A(f"| `CalibrationId` | `{c['calibrationId']}` |")
        A(f"| `PerformedAt` | `{c.get('performedAt', 'n/a')}` |")
        A(f"| `Valid` | `{str(c.get('valid', True)).lower()}` |")
        if "method" in c:
            A(f"| `Method` | `{c['method']}` |")
        if "residualError" in c:
            A(f"| `ResidualError` | `{c['residualError']}` |")
        if "mount" in c:
            A(f"| `Mount` | `{c['mount']}` |")
        if "sourceFrame" in c:
            A(f"| `SourceFrame` | `{c['sourceFrame']}` |")
        if "targetFrame" in c:
            A(f"| `TargetFrame` | `{c['targetFrame']}` |")
        A("")
        if c.get("fields"):
            field_var = ("Transform" if c["type"] == "ExtrinsicCalibrationType"
                         else "Intrinsics")
            A(f"`{field_var}` field values, in the units fixed by base specification "
              "§5.12:")
            A("")
            A("| Field | Value | Unit / convention |")
            A("|---|---|---|")
            for fname, fval, funit in c["fields"]:
                A(f"| `{fname}` | `{fval}` | {funit} |")
            A("")
    if d.get("calibrations"):
        A("Each calibration is reachable from the sensor by a `HasCalibration` "
          "reference, as base specification §5.11 requires.")
        A("")
    if "twin" in d:
        tw = d["twin"]
        ts = tw["sensor"]
        sim = tw["simulation"]
        head("The simulated twin")
        A("")
        A(tw["note"])
        A("")
        A("| Member | Physical sensor | Simulated twin |")
        A("|---|---|---|")
        A(f"| Instance | `{d['instanceName']}` | `{tw['instanceName']}` |")
        A(f"| `RealityKind` | `{s['realityKind']}` | `{ts['realityKind']}` |")
        A(f"| Type | `{s['type']}` | `{ts['type']}` |")
        A(f"| `Width` x `Height` | `{s.get('width')}` x `{s.get('height')}` | "
          f"`{ts.get('width')}` x `{ts.get('height')}` |")
        A(f"| `PixelFormat` | `{s.get('pixelFormat')}` | `{ts.get('pixelFormat')}` |")
        A("| Media endpoints | RTSP + JPEG | RTSP + JPEG |")
        A("")
        A("The twin additionally implements `IVisionSimulatedType`:")
        A("")
        A("| Member | Value |")
        A("|---|---|")
        A(f"| `SimulatorUri` | `{sim['simulatorUri']}` |")
        A(f"| `StageIdentifier` | `{sim['stageIdentifier']}` |")
        A(f"| `PrimPath` | `{sim['primPath']}` |")
        if "groundTruthAvailable" in sim:
            A(f"| `GroundTruthAvailable` | `{str(sim['groundTruthAvailable']).lower()}` |")
        A("")
        A("`PrimPath` resolves to a `UsdGeomCameraType` instance where the Server also "
          "implements *OPC UA — OpenUSD Scene Materialization* and claims the base "
          "specification's *VIS-Interop-Scene* facet (Annex C), so the camera's "
          "aperture and focal-length attributes are both the scene description and the "
          "imaging intrinsics.")
        A("")
    head("Inference")
    A("")
    A("| Member | Value |")
    A("|---|---|")
    A(f"| Model | `{ai['model']['name']}` v`{ai['model']['version']}` "
      f"({ai['model'].get('format', 'n/a')}) |")
    A(f"| `TaskKind` | `{ai['model'].get('taskKind', 'n/a')}` |")
    A(f"| `InferenceLocation` | **`{dep['inferenceLocation']}`** |")
    if "acceleratorKind" in dep:
        A(f"| `AcceleratorKind` | `{dep['acceleratorKind']}` |")
    if "endpointUri" in dep:
        A(f"| `EndpointUri` | `{dep['endpointUri']}` |")
    A(f"| `MaxResultAge` | `{pl['maxResultAge']}` ms |")
    A(f"| `MaxRetainedResults` | `{pl['maxRetainedResults']}` |")
    A("")
    A(d["inferenceNote"])
    A("")
    A("The deployment carries exactly one `UsesModel` reference to the model above, as "
      "*OPC UA — AI Model Management and Inference* requires. That reference says which "
      "model is serving now. Each retained result records the model that actually answered "
      "in `ModelUsed`, so an audit follows `result.ModelUsed` to the model and its `Digest` "
      "even after a promotion, fallback or followed-reference change.")
    A("")
    head("Results")
    A("")
    A(d["resultsNote"])
    A("")
    head("Feedback")
    A("")
    A(d["feedbackNote"])
    A("")
    head("Deliverables")
    A("")
    A("| File | Content |")
    A("|---|---|")
    A(f"| [`{d['descriptorFile']}`]({rel}) | Machine-readable descriptor (single "
      "source). |")
    A(f"| [`{nodeset}`]({nodeset_link}) | The generated instance overlay. |")
    if annex:
        A(f"| [`OPC-UA-{d['domain']}-Vision-Addendum.md`]"
          f"({d['outputFolder']}/OPC-UA-{d['domain']}-Vision-Addendum.md) | This annex, "
          "published standalone beside the overlay. |")
    A("")
    A("Regenerate from the repository root with "
      "`python metaverse-specs/extras/vision/tools/build_examples.py`.")
    return "\n".join(L).rstrip() + "\n"


SPEC_PATH = os.path.normpath(os.path.join(HERE, "..", "..", "..", "vision",
                                          "OPC-UA-Vision.md"))


def splice(marker, body):
    """Replace the region between the generated-annex markers in the base spec.

    Same mechanism the core-specs generators use, so the annex text in the spec is
    generated output guarded by the repository's determinism check rather than
    hand-maintained prose that could drift from the overlay.
    """
    begin = f"<!-- BEGIN GENERATED: {marker} -->"
    end = f"<!-- END GENERATED: {marker} -->"
    with open(SPEC_PATH, encoding="utf-8") as f:
        text = f.read()
    if begin not in text or end not in text:
        raise SystemExit(f"markers for '{marker}' not found in {SPEC_PATH}")
    start = text.index(begin) + len(begin)
    finish = text.index(end)
    new_text = text[:start] + "\n\n" + body.rstrip() + "\n\n" + text[finish:]
    if new_text != text:
        with open(SPEC_PATH, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)


SAFE_NAME = re.compile(r"[A-Za-z0-9._-]+")


def safe_component(value, field):
    """A descriptor value used to build a filesystem path or a filename.

    Descriptors are contributor-supplied and a maintainer runs this generator over a
    PR branch, so a value like '../../..' or an absolute path would silently write
    outside the tree - os.path.join discards everything before an absolute component,
    and normpath does not undo traversal.
    """
    if not isinstance(value, str) or not SAFE_NAME.fullmatch(value):
        raise SystemExit(f"descriptor field '{field}' must match "
                         f"[A-Za-z0-9._-]+; got {value!r}")
    if value in (".", ".."):
        raise SystemExit(f"descriptor field '{field}' must not be {value!r}")
    return value


def process(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    d["descriptorFile"] = os.path.basename(path)
    d["folder"] = os.path.basename(os.path.dirname(os.path.abspath(path)))
    for field in ("outputFolder", "domain", "annexLetter", "annexMarker"):
        safe_component(d[field], field)
    vision_root = os.path.normpath(os.path.join(HERE, "..", "..", "..", "vision"))
    outdir = os.path.normpath(os.path.join(vision_root, d["outputFolder"]))
    if os.path.commonpath([os.path.abspath(outdir),
                           os.path.abspath(vision_root)]) != os.path.abspath(
                               vision_root):
        raise SystemExit(f"outputFolder escapes the vision tree: {outdir}")
    os.makedirs(outdir, exist_ok=True)
    ov = build_overlay(d)
    xml_path = os.path.join(outdir, f"Opc.Ua.{d['domain']}.Vision.NodeSet2.xml")
    md_path = os.path.join(outdir, f"OPC-UA-{d['domain']}-Vision-Addendum.md")
    with open(xml_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(ov.emit(d["domain"]))
    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(emit_addendum(d))
    splice(d["annexMarker"], emit_addendum(d, annex=d["annexLetter"]))
    print(f"{d['domain']}: {len(ov.nodes)} instance nodes -> {d['outputFolder']}/ "
          f"(+ Annex {d['annexLetter']})")


def main():
    args = sys.argv[1:]
    if args:
        for a in args:
            process(a)
        return 0
    root = os.path.join(HERE, "..", "examples")
    found = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in sorted(filenames):
            if fn.endswith(".json"):
                found.append(os.path.join(dirpath, fn))
    for p in sorted(found):
        process(p)
    if not found:
        print("no descriptors found")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
