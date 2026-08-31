#!/usr/bin/env python3
"""
Generator for the OPC UA — Vision companion specification (WG draft).

Emits, from a single in-code source of truth:
  * ../../../vision/Opc.Ua.Vision.NodeSet2.xml  - the information model (UANodeSet)
  * ../../../vision/Opc.Ua.Vision.NodeIds.csv   - the NodeId assignments (SymbolicName,Id,NodeClass)
  * model-reference.md                          - the generated Annex A (node reference)

The model is a COMPANION specification in its OWN namespace
(http://opcfoundation.org/UA/Vision/, namespace index 1). Nodes therefore use
`ns=1;i=<n>` NodeIds; references to base UA types use plain `i=<n>`.

It is deliberately STANDALONE: the only <RequiredModel> is the base UA namespace, so a
server can adopt it without pulling in DI, Machinery, Robotics or OpenUSD. Interop with
OPC 40100 (Machine Vision) and with OPC UA - OpenUSD Scene Materialization is expressed
as optional profiles in the spec annexes and carried by String/NodeId properties, not by
NodeSet dependencies.

NodeIds are PROVISIONAL (final IDs assigned by the OPC Foundation) and follow the repo
convention: ObjectTypes/Interfaces 1001+, Enumerations 3001+ (EnumStrings = enum + 900),
Structures 3050+, ReferenceTypes 4001+, DataType encodings 5001+, well-known instances
7001+, and all remaining instance declarations sequentially from 6001. New members must
be APPENDED so that previously published member NodeIds stay stable.

Design notes (see ../../../vision/OPC-UA-Vision-Research.md for the evidence base):
  * Pixels never traverse OPC UA on the DEFAULT path. The model brokers media ENDPOINTS
    (RTSP for streams, JPEG for clips) and leaves the bytes out-of-band. Two OPTIONAL
    facets exist beside that default: a size-gated inline ByteString for single stills,
    and - where a Server implements the OPC UA - Data Channels errata proposal - a data
    channel multiplexed onto the SecureChannel. Neither is required, and the RTSP/JPEG
    guarantee is unchanged by either.
  * Result CONTENT is defined here - deliberately doing what OPC 40100-1 declined to do.
  * Inference location (on-server vs off-server) is an explicit property, so the same
    result contract serves both deployments.
"""
from __future__ import annotations
import os
import re
import xml.sax.saxutils as sx

NAMESPACE = "http://opcfoundation.org/UA/Vision/"
VERSION = "0.2.0"
PUBDATE = "2026-08-31T00:00:00Z"

BASE_UA_VERSION = "1.05.04"
BASE_UA_PUBDATE = "2023-12-15T00:00:00Z"

# --- base UA NodeIds (namespace 0) -----------------------------------------
HasComponent = "i=47"
HasProperty = "i=46"
HasSubtype = "i=45"
Organizes = "i=35"
HasTypeDefinition = "i=40"
HasModellingRule = "i=37"
HasInterface = "i=17603"
HasEncoding = "i=38"

MR_Mandatory = "i=78"
MR_Optional = "i=80"
MR_OptionalPlaceholder = "i=11508"
MR_MandatoryPlaceholder = "i=11510"

BaseObjectType = "i=58"
FolderType = "i=61"
PropertyType = "i=68"
BaseDataVariableType = "i=63"
BaseInterfaceType = "i=17602"
DataTypeEncodingType = "i=76"
Enumeration = "i=29"
Structure = "i=22"
NonHierarchicalReferences = "i=32"

BaseDataType = "i=24"
Boolean = "i=1"
Int32 = "i=6"
UInt32 = "i=7"
UInt64 = "i=9"
Double = "i=11"
String = "i=12"
Guid = "i=14"
ByteString = "i=15"
NodeId_ = "i=17"
QualifiedName = "i=20"
LocalizedText = "i=21"
UtcTime = "i=294"
Duration = "i=290"
Argument = "i=296"
EUInformation = "i=887"

Server = "i=2253"

ALIASES = [
    ("Boolean", Boolean), ("Int32", Int32), ("UInt32", UInt32), ("UInt64", UInt64),
    ("Double", Double), ("String", String), ("Guid", Guid), ("ByteString", ByteString),
    ("NodeId", NodeId_), ("QualifiedName", QualifiedName), ("LocalizedText", LocalizedText),
    ("UtcTime", UtcTime), ("Duration", Duration), ("Argument", Argument),
    ("EUInformation", EUInformation), ("BaseDataType", BaseDataType),
    ("HasComponent", HasComponent), ("HasProperty", HasProperty),
    ("HasSubtype", HasSubtype), ("Organizes", Organizes),
    ("HasTypeDefinition", HasTypeDefinition), ("HasModellingRule", HasModellingRule),
    ("HasInterface", HasInterface), ("HasEncoding", HasEncoding),
    ("Mandatory", MR_Mandatory), ("Optional", MR_Optional),
    ("OptionalPlaceholder", MR_OptionalPlaceholder),
    ("MandatoryPlaceholder", MR_MandatoryPlaceholder),
]

REFTYPE_ALIAS = {v: k for k, v in ALIASES}
DATATYPE_ALIAS = {v: k for k, v in ALIASES}


# --- node registry ---------------------------------------------------------
class Node:
    __slots__ = ("nid", "cls", "bname", "symbolic", "display", "desc", "parent",
                 "attrs", "refs", "category", "definition", "value", "abstract",
                 "inverse")

    def __init__(self, nid, cls, bname, symbolic, display, desc, parent, attrs,
                 category, abstract):
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
        self.inverse = None


NODES = {}
ORDER = []
_next_member = [6001]
_next_encoding = [5001]


def _mid():
    v = _next_member[0]
    _next_member[0] += 1
    return v


def T(nid):
    """Own-namespace NodeId (ns=1)."""
    return f"ns=1;i={nid}"


def add(nid, cls, bname, symbolic, display=None, desc=None, parent=None,
        attrs=None, category=None, abstract=False):
    n = Node(nid, cls, bname, symbolic, display, desc, parent, attrs, category, abstract)
    NODES[nid] = n
    ORDER.append(nid)
    return n


def ref(nid, reftype, target, forward=True):
    NODES[nid].refs.append((reftype, target, forward))


# --- builders --------------------------------------------------------------
def object_type(nid, name, base, desc, abstract=False):
    add(nid, "UAObjectType", name, name, desc=desc, category=CAT, abstract=abstract)
    ref(nid, HasSubtype, base, forward=False)
    return nid


def interface_type(nid, name, base, desc):
    add(nid, "UAObjectType", name, name, desc=desc, category=CAT, abstract=True)
    ref(nid, HasSubtype, base, forward=False)
    return nid


def reference_type(nid, name, inverse, desc, base=NonHierarchicalReferences):
    n = add(nid, "UAReferenceType", name, name, desc=desc, category=CAT_RT)
    n.inverse = inverse
    ref(nid, HasSubtype, base, forward=False)
    return nid


def _member_var(owner, owner_sym, name, datatype, typedef, rule, reftype, desc,
                valuerank="-1"):
    nid = _mid()
    attrs = {"DataType": datatype, "ValueRank": valuerank}
    add(nid, "UAVariable", name, f"{owner_sym}_{name.strip('<>')}", desc=desc,
        parent=T(owner), attrs=attrs)
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid


def prop_var(owner, owner_sym, name, datatype, desc, rule=MR_Optional, valuerank="-1"):
    return _member_var(owner, owner_sym, name, datatype, PropertyType, rule,
                       HasProperty, desc, valuerank)


def data_var(owner, owner_sym, name, datatype, desc, rule=MR_Optional, valuerank="-1"):
    return _member_var(owner, owner_sym, name, datatype, BaseDataVariableType, rule,
                       HasComponent, desc, valuerank)


def folder_member(owner, owner_sym, name, desc, rule=MR_Mandatory):
    nid = _mid()
    add(nid, "UAObject", name, f"{owner_sym}_{name}", desc=desc, parent=T(owner))
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, FolderType)
    ref(nid, HasComponent, T(owner), forward=False)
    ref(owner, HasComponent, T(nid))
    return nid


def obj_member(owner, owner_sym, name, typedef, desc, rule=MR_Optional,
               reftype=HasComponent):
    nid = _mid()
    add(nid, "UAObject", name, f"{owner_sym}_{name.strip('<>')}", desc=desc,
        parent=T(owner))
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid


def _args(method_nid, method_sym, bname, args):
    """Emit an InputArguments / OutputArguments Property for a Method."""
    nid = _mid()
    add(nid, "UAVariable", bname, f"{method_sym}_{bname}", parent=T(method_nid),
        attrs={"DataType": Argument, "ValueRank": "1",
               "ArrayDimensions": str(len(args))})
    ref(nid, HasModellingRule, MR_Mandatory)
    ref(nid, HasTypeDefinition, PropertyType)
    ref(nid, HasProperty, T(method_nid), forward=False)
    ref(method_nid, HasProperty, T(nid))
    parts = ['<Value>',
             '<uax:ListOfExtensionObject xmlns:uax='
             '"http://opcfoundation.org/UA/2008/02/Types.xsd">']
    for arg in args:
        aname, adtype, adesc = arg[0], arg[1], arg[2]
        arank = arg[3] if len(arg) > 3 else -1
        parts.append("<uax:ExtensionObject><uax:TypeId><uax:Identifier>i=297"
                     "</uax:Identifier></uax:TypeId>")
        parts.append("<uax:Body><uax:Argument>")
        parts.append(f"<uax:Name>{sx.escape(aname)}</uax:Name>")
        parts.append(f"<uax:DataType><uax:Identifier>{adtype}</uax:Identifier>"
                     "</uax:DataType>")
        if arank is not None and arank >= 0:
            parts.append(f"<uax:ValueRank>{arank}</uax:ValueRank>"
                         "<uax:ArrayDimensions><uax:UInt32>0</uax:UInt32>"
                         "</uax:ArrayDimensions>")
        else:
            parts.append("<uax:ValueRank>-1</uax:ValueRank>"
                         "<uax:ArrayDimensions/>")
        if adesc:
            parts.append("<uax:Description><uax:Text>"
                         f"{sx.escape(adesc)}</uax:Text></uax:Description>")
        parts.append("</uax:Argument></uax:Body></uax:ExtensionObject>")
    parts.append("</uax:ListOfExtensionObject></Value>")
    NODES[nid].value = "".join(parts)
    return nid


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


def enum_type(nid, name, desc, fields):
    add(nid, "UADataType", name, name, desc=desc, category=CAT_DT)
    ref(nid, HasSubtype, Enumeration, forward=False)
    dparts = [f'<Definition Name="{name}">']
    for (fname, val, fdesc) in fields:
        if fdesc:
            dparts.append(f'<Field Name="{sx.escape(fname)}" Value="{val}">')
            dparts.append(f'<Description>{sx.escape(fdesc)}</Description></Field>')
        else:
            dparts.append(f'<Field Name="{sx.escape(fname)}" Value="{val}"/>')
    dparts.append("</Definition>")
    NODES[nid].definition = "".join(dparts)
    es = nid + 900
    ref(nid, HasProperty, T(es))
    add(es, "UAVariable", "EnumStrings", f"{name}_EnumStrings", parent=T(nid),
        attrs={"DataType": LocalizedText, "ValueRank": "1",
               "ArrayDimensions": str(len(fields))})
    ref(es, HasModellingRule, MR_Mandatory)
    ref(es, HasTypeDefinition, PropertyType)
    ref(es, HasProperty, T(nid), forward=False)
    vp = ['<Value>',
          '<uax:ListOfLocalizedText xmlns:uax='
          '"http://opcfoundation.org/UA/2008/02/Types.xsd">']
    for (fname, _val, _fdesc) in fields:
        vp.append("<uax:LocalizedText><uax:Text>"
                  f"{sx.escape(fname)}</uax:Text></uax:LocalizedText>")
    vp.append("</uax:ListOfLocalizedText></Value>")
    NODES[es].value = "".join(vp)
    return nid


def struct_type(nid, name, desc, fields):
    """A Structure DataType plus its Default Binary encoding object.

    fields: list of (FieldName, DataType, Description[, ValueRank[, ArrayDimensions]])
    """
    add(nid, "UADataType", name, name, desc=desc, category=CAT_DT)
    ref(nid, HasSubtype, Structure, forward=False)
    dparts = [f'<Definition Name="{name}">']
    for f in fields:
        fname, fdtype, fdesc = f[0], f[1], f[2]
        frank = f[3] if len(f) > 3 else None
        fdims = f[4] if len(f) > 4 else None
        a = [f'Name="{sx.escape(fname)}"', f'DataType="{fdtype}"']
        if frank is not None:
            a.append(f'ValueRank="{frank}"')
        if fdims is not None:
            a.append(f'ArrayDimensions="{fdims}"')
        attr = " ".join(a)
        if fdesc:
            dparts.append(f'<Field {attr}>')
            dparts.append(f'<Description>{sx.escape(fdesc)}</Description></Field>')
        else:
            dparts.append(f'<Field {attr}/>')
    dparts.append("</Definition>")
    NODES[nid].definition = "".join(dparts)
    enc = _next_encoding[0]
    _next_encoding[0] += 1
    ref(nid, HasEncoding, T(enc))
    add(enc, "UAObject", "Default Binary", f"{name}_Encoding_DefaultBinary",
        desc="Default Binary encoding of the structure.")
    ref(enc, HasTypeDefinition, DataTypeEncodingType)
    ref(enc, HasEncoding, T(nid), forward=False)
    return nid


def well_known(nid, name, typedef, parent_nodeid, desc, reftype=HasComponent):
    add(nid, "UAObject", name, name, desc=desc, parent=parent_nodeid)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, parent_nodeid, forward=False)
    return nid


# ===========================================================================
# ==============================  MODEL DEFINITION  =========================
# ===========================================================================
CAT = "Vision"
CAT_DT = "Vision DataTypes"
CAT_RT = "Vision ReferenceTypes"

# ---------------------------------------------------------------------------
# Enumerations (3001+)
# ---------------------------------------------------------------------------
enum_type(3001, "VisionRealityKindEnum",
          "Whether the sensor observes the physical world, a simulation, or both. This is "
          "the sim/real switch: every other member of the model means the same thing "
          "regardless of its value.",
          [("Physical", 0, "A physical device observing the real world."),
           ("Simulated", 1, "A synthetic sensor rendered by a simulator (e.g. NVIDIA "
                            "Isaac Sim); ground truth may be available."),
           ("Hybrid", 2, "A physical device whose output is augmented or replayed "
                         "through a simulation.")])

enum_type(3002, "VisionStreamProtocolEnum",
          "Wire protocol of a continuous media stream. Rtsp is the mandatory default: a "
          "conformant Server exposes at least one StreamEndpoint using it.",
          [("Rtsp", 0, "RTSP (RFC 7826/2326). MANDATORY default streaming protocol."),
           ("Rtsps", 1, "RTSP over TLS."),
           ("WebRtc", 2, "WebRTC."),
           ("Srt", 3, "Secure Reliable Transport."),
           ("Hls", 4, "HTTP Live Streaming."),
           ("Mjpeg", 5, "Motion JPEG over HTTP."),
           ("GenDc", 6, "GenICam GenDC container stream."),
           ("Other", 7, "A protocol identified by the endpoint URI scheme."),
           ("DataChannel", 8,
            "The stream is carried on an OPC UA data channel multiplexed onto the "
            "SecureChannel the client already has, per the OPC UA - Data Channels "
            "errata proposal. OPTIONAL and never a default: see clause 6.7. That "
            "proposal is a DRAFT in this repository, not a released OPC UA "
            "specification, so a Server is fully conformant without it.")])

enum_type(3003, "VisionClipFormatEnum",
          "Encoding of a still clip. Jpeg is the mandatory default: a conformant Server "
          "exposes at least one ClipEndpoint using it.",
          [("Jpeg", 0, "JPEG (ISO/IEC 10918). MANDATORY default clip format."),
           ("Png", 1, "PNG."),
           ("Tiff", 2, "TIFF."),
           ("Bmp", 3, "BMP."),
           ("WebP", 4, "WebP."),
           ("GenDc", 5, "GenICam GenDC container."),
           ("Other", 6, "A format identified by the accompanying media type.")])

enum_type(3004, "VisionVideoCodecEnum",
          "Codec carried by a stream endpoint.",
          [("H264", 0, None), ("H265", 1, None), ("Mjpeg", 2, None),
           ("Av1", 3, None), ("Raw", 4, "Uncompressed frames."),
           ("Other", 5, None)])

enum_type(3005, "VisionEndpointStateEnum",
          "Runtime lifecycle state of a media endpoint or deployment.",
          [("Inactive", 0, "Declared but not serving."),
           ("Ready", 1, "Able to serve; no active session."),
           ("Active", 2, "Serving at least one session."),
           ("Degraded", 3, "Serving below configured quality."),
           ("Faulted", 4, "Unable to serve.")])

enum_type(3006, "VisionEndpointAuthenticationEnum",
          "Authentication a client must present to the media endpoint. This is the "
          "media-plane credential, independent of the OPC UA session.",
          [("None", 0, "No authentication. Appropriate only on an isolated network."),
           ("Basic", 1, "HTTP/RTSP Basic."),
           ("Digest", 2, "HTTP/RTSP Digest."),
           ("Token", 3, "Bearer token, typically the time-limited token returned by "
                        "GetStreamEndpoint or GetClip."),
           ("MutualTls", 4, "Client certificate.")])

enum_type(3007, "VisionInferenceLocationEnum",
          "Where inference executes. The result contract is identical in every case; this "
          "property exists so a client can reason about latency, availability and trust "
          "boundary without changing how it reads results.",
          [("OnServer", 0, "In the OPC UA Server process or on its host."),
           ("EdgeOffServer", 1, "On a separate edge node reached over the network."),
           ("Cloud", 2, "In a remote or cloud service."),
           ("InSimulator", 3, "Inside the simulator that also renders the sensor.")])

enum_type(3008, "VisionAcceleratorKindEnum",
          "Compute device executing the model.",
          [("Cpu", 0, None), ("Gpu", 1, None), ("Npu", 2, None), ("Fpga", 3, None),
           ("Tpu", 4, None), ("Other", 5, None)])

enum_type(3009, "VisionResultEvaluationEnum",
          "Overall verdict of a result. Value semantics are aligned with the "
          "ResultEvaluationEnum of OPC 40001-101 so that a client already consuming "
          "Machinery results needs no new interpretation rules.",
          [("Undefined", 0, "No verdict available."),
           ("Ok", 1, "Within tolerance / accepted."),
           ("NotOk", 2, "Out of tolerance / rejected."),
           ("NotDecidable", 3, "A verdict was not possible, typically because the "
                               "measurement uncertainty spans a tolerance limit.")])

enum_type(3010, "VisionToleranceStatusEnum",
          "Per-characteristic tolerance outcome.",
          [("InTolerance", 0, None), ("OutOfTolerance", 1, None),
           ("Indeterminate", 2, "Uncertainty spans a tolerance limit.")])

enum_type(3011, "VisionFeedbackPurposeEnum",
          "Why a client is pushing information back into the vision system.",
          [("Overlay", 0, "Render the geometry onto the outgoing stream."),
           ("Reconciliation", 1, "Record a downstream verdict against the result."),
           ("GroundTruthLabel", 2, "Treat the payload as a corrected label for training."),
           ("Trigger", 3, "Use the payload as an acquisition or processing trigger.")])

enum_type(3012, "VisionCalibrationMountEnum",
          "Physical relationship between a camera and the kinematic chain it is "
          "calibrated against.",
          [("EyeInHand", 0, "Camera mounted on the moving flange or tool."),
           ("EyeToHand", 1, "Camera fixed in the workspace observing the tool."),
           ("Fixed", 2, "Camera fixed with no associated kinematic chain."),
           ("Unknown", 3, None)])

enum_type(3013, "VisionFrameRoleEnum",
          "Role of a coordinate frame, following the ISO 9787 frame vocabulary.",
          [("World", 0, None), ("Base", 1, None),
           ("Tool", 2, "Tool / tool centre point (TCP) frame."),
           ("Camera", 3, None), ("Object", 4, None), ("Other", 5, None)])

enum_type(3014, "VisionDistortionModelEnum",
          "Lens distortion model the coefficients belong to.",
          [("None", 0, None),
           ("BrownConrady", 1, "Radial and tangential (k1, k2, p1, p2, k3...)."),
           ("KannalaBrandt", 2, "Fisheye / equidistant."),
           ("RationalPolynomial", 3, None), ("Other", 4, None)])

enum_type(3015, "VisionSensorModalityEnum",
          "What the sensor measures.",
          [("Area2D", 0, "Two-dimensional area-scan imaging."),
           ("Line2D", 1, "Line-scan imaging."),
           ("Depth3D", 2, "Depth or point-cloud sensing."),
           ("Thermal", 3, None), ("Multispectral", 4, None),
           ("Event", 5, "Event / neuromorphic camera."), ("Other", 6, None)])

enum_type(3016, "VisionLearningJobStateEnum",
          "State of a dataset-capture, retraining and promotion cycle.",
          [("Idle", 0, None), ("Collecting", 1, None), ("Labelling", 2, None),
           ("Training", 3, None), ("Validating", 4, None),
           ("Ready", 5, "A candidate model is available for promotion."),
           ("Promoted", 6, None), ("Failed", 7, None)])

enum_type(3017, "VisionDatasetSourceEnum",
          "Provenance of the samples in a dataset.",
          [("Real", 0, "Captured from physical sensors."),
           ("Synthetic", 1, "Rendered by a simulator."),
           ("Mixed", 2, "Both, e.g. synthetic pre-training with real fine-tuning.")])

VisionRealityKindEnum = T(3001)
VisionStreamProtocolEnum = T(3002)
VisionClipFormatEnum = T(3003)
VisionVideoCodecEnum = T(3004)
VisionEndpointStateEnum = T(3005)
VisionEndpointAuthenticationEnum = T(3006)
VisionInferenceLocationEnum = T(3007)
VisionAcceleratorKindEnum = T(3008)
VisionResultEvaluationEnum = T(3009)
VisionToleranceStatusEnum = T(3010)
VisionFeedbackPurposeEnum = T(3011)
VisionCalibrationMountEnum = T(3012)
VisionFrameRoleEnum = T(3013)
VisionDistortionModelEnum = T(3014)
VisionSensorModalityEnum = T(3015)
VisionLearningJobStateEnum = T(3016)
VisionDatasetSourceEnum = T(3017)

# ---------------------------------------------------------------------------
# Structured DataTypes (3050+)
# ---------------------------------------------------------------------------
struct_type(3050, "VisionPose3DDataType",
            "A rigid-body pose expressed in a named coordinate frame. Position is metres; "
            "Orientation is a unit quaternion ordered (x, y, z, w). Covariance is an "
            "optional row-major 6x6 matrix over (x, y, z, rx, ry, rz); an empty array "
            "means the uncertainty is not reported.",
            [("FrameId", String, "FrameId of the CoordinateFrame this pose is expressed in."),
             ("Position", Double, "Translation (x, y, z) in metres.", 1, 3),
             ("Orientation", Double, "Unit quaternion (x, y, z, w).", 1, 4),
             ("Covariance", Double, "Row-major 6x6 covariance, or empty.", 1, 36)])
VisionPose3DDataType = T(3050)

struct_type(3051, "VisionBoundingBox2DDataType",
            "A box in image space. The origin is the top-left pixel; Rotation is degrees "
            "clockwise about the box centre, so 0 denotes an axis-aligned box.",
            [("CenterX", Double, "Box centre x, in pixels."),
             ("CenterY", Double, "Box centre y, in pixels."),
             ("Width", Double, "Box width, in pixels."),
             ("Height", Double, "Box height, in pixels."),
             ("Rotation", Double, "Rotation about the centre, in degrees.")])
VisionBoundingBox2DDataType = T(3051)

struct_type(3052, "VisionBoundingBox3DDataType",
            "An oriented box in three-dimensional space, given by a centre pose and an "
            "extent.",
            [("Center", VisionPose3DDataType, "Centre pose of the box."),
             ("Size", Double, "Extent (x, y, z) in metres.", 1, 3)])
VisionBoundingBox3DDataType = T(3052)

struct_type(3053, "VisionImageReferenceDataType",
            "A reference to image bytes that are NOT carried in the OPC UA payload. This "
            "is the default way results point at imagery: the Uri is resolved out-of-band, "
            "typically through a ClipEndpoint, and verified against Digest.",
            [("Uri", String, "Location of the encoded image."),
             ("Digest", ByteString, "Cryptographic digest of the referenced bytes."),
             ("DigestAlgorithm", String, "Digest algorithm; default SHA-256."),
             ("Format", VisionClipFormatEnum, "Container or encoding of the image."),
             ("PixelFormat", String, "Pixel format using GenICam PFNC naming, for example "
                                     "Mono8, BayerRG12 or RGB8."),
             ("Width", UInt32, "Image width in pixels."),
             ("Height", UInt32, "Image height in pixels."),
             ("SizeBytes", UInt32, "Encoded size, so a client can decide whether to fetch."),
             ("Timestamp", UtcTime, "Acquisition time of the frame.")])
VisionImageReferenceDataType = T(3053)

struct_type(3054, "VisionIntrinsicsDataType",
            "Pinhole intrinsics plus a distortion model, in pixel units, valid for the "
            "stated image size. For a simulated sensor these are derived from the USD "
            "camera aperture and focal-length attributes.",
            [("Fx", Double, "Focal length in pixels, x."),
             ("Fy", Double, "Focal length in pixels, y."),
             ("Cx", Double, "Principal point x, in pixels."),
             ("Cy", Double, "Principal point y, in pixels."),
             ("Skew", Double, "Axis skew; 0 for square pixels."),
             ("DistortionModel", VisionDistortionModelEnum,
              "Model the coefficients belong to."),
             ("DistortionCoefficients", Double, "Coefficients, model-ordered.", 1),
             ("Width", UInt32, "Image width these intrinsics are valid for."),
             ("Height", UInt32, "Image height these intrinsics are valid for.")])
VisionIntrinsicsDataType = T(3054)

struct_type(3055, "VisionDetectionDataType",
            "One detected instance. This is the robotics-vision payload: a class, a score, "
            "and enough geometry to act on - a 2-D box for image-space work, a 3-D box "
            "and a 6-DoF pose for picking and visual servoing. Field naming follows the "
            "ROS 2 vision_msgs conventions so that a bridge is mechanical.",
            [("DetectionId", String, "Identifier unique within the result."),
             ("ClassLabel", String, "Human-readable class name."),
             ("ClassId", UInt32, "Numeric class identifier within the model label set."),
             ("Confidence", Double, "Score in the range 0.0 to 1.0."),
             ("HasBoundingBox2D", Boolean, "True when BoundingBox2D is meaningful."),
             ("BoundingBox2D", VisionBoundingBox2DDataType, "Image-space box."),
             ("HasBoundingBox3D", Boolean, "True when BoundingBox3D is meaningful."),
             ("BoundingBox3D", VisionBoundingBox3DDataType, "Object-space box."),
             ("HasPose", Boolean, "True when Pose is meaningful."),
             ("Pose", VisionPose3DDataType, "6-DoF pose, for example a grasp pose."),
             ("TrackId", String, "Stable identity across frames, when tracking is done.")])
VisionDetectionDataType = T(3055)

struct_type(3056, "VisionCharacteristicDataType",
            "One measured characteristic of an inspected part. This is the machine-vision "
            "payload, and the field set deliberately mirrors QIF (ISO 23952) Results, "
            "including measurement uncertainty, so that a QIF document can be produced "
            "from it without inventing information.",
            [("CharacteristicId", String, "Identifier of the characteristic measured."),
             ("Name", String, "Human-readable characteristic name."),
             ("Nominal", Double, "Design or target value."),
             ("Actual", Double, "Measured value."),
             ("Deviation", Double, "Actual minus Nominal."),
             ("LowerTolerance", Double, "Lower tolerance limit, relative to Nominal."),
             ("UpperTolerance", Double, "Upper tolerance limit, relative to Nominal."),
             ("Uncertainty", Double, "Expanded measurement uncertainty (ISO 14253), in the "
                                     "same unit as Actual. 0 means not reported."),
             ("Unit", EUInformation, "Engineering unit of Nominal, Actual and Deviation."),
             ("Status", VisionToleranceStatusEnum, "Per-characteristic outcome.")])
VisionCharacteristicDataType = T(3056)

struct_type(3057, "VisionStreamSessionDataType",
            "A leased media session. The Uri may embed a single-use or time-limited "
            "credential, which is why it is returned by a Method rather than published as "
            "a browsable Variable.",
            [("SessionToken", ByteString, "Opaque token identifying the lease."),
             ("Uri", String, "Media URI to open."),
             ("Protocol", VisionStreamProtocolEnum, "Protocol of the returned URI."),
             ("ExpiresAt", UtcTime, "Expiry after which the Uri is no longer valid.")])
VisionStreamSessionDataType = T(3057)

struct_type(3058, "VisionTensorSignatureDataType",
            "Shape and element type of one model input or output tensor.",
            [("Name", String, "Tensor name as declared by the model."),
             ("ElementType", String, "Element type, for example float32, uint8 or int64."),
             ("Shape", Int32, "Dimensions; -1 marks a dynamic axis.", 1),
             ("Layout", String, "Optional axis layout hint, for example NCHW or NHWC.")])
VisionTensorSignatureDataType = T(3058)

# ---------------------------------------------------------------------------
# ReferenceTypes (4001+)
# ---------------------------------------------------------------------------
reference_type(4001, "HasCalibration", "IsCalibrationOf",
               "Links a sensor to a calibration currently valid for it.")
reference_type(4002, "MountedOn", "HasMounted",
               "Links a sensor to the CoordinateFrame it is rigidly mounted on, for "
               "example a robot flange frame for an eye-in-hand camera.")
reference_type(4003, "HasScenePrim", "IsScenePrimOf",
               "Links a sensor to the materialized USD prim representing it, when the "
               "Server also implements OPC UA - OpenUSD Scene Materialization. The target "
               "is expected to be a UsdGeomCameraType instance. Optional: PrimPath remains "
               "the portable descriptor.")
reference_type(4004, "UsesModel", "IsUsedByDeployment",
               "Links an AiDeploymentType instance to the AiModelType instance it "
               "executes. Clause 5.11 requires exactly one such reference per deployment; "
               "it is the only defined path from a result to the model artefact and its "
               "Digest, on which clause 12.6 depends.")
reference_type(4005, "ProducedBy", "Produces",
               "Links a result to the inference pipeline that produced it.")

# ---------------------------------------------------------------------------
# ObjectTypes (1001+)
# ---------------------------------------------------------------------------

# ---- Optics and illumination ----------------------------------------------
object_type(1005, "OpticsType", BaseObjectType,
            "The lens in front of a sensor. Member names are deliberately aligned with "
            "the ILensType of OPC 40100-2 so that a Server implementing both models "
            "reports one set of values under two vocabularies.")
OP = 1005
prop_var(OP, "OpticsType", "FocalLength", Double, "Focal length in millimetres.")
prop_var(OP, "OpticsType", "Aperture", Double, "Current aperture as an f-number.")
prop_var(OP, "OpticsType", "WorkingDistance", Double,
         "Current object-to-lens distance in metres.")
prop_var(OP, "OpticsType", "MinimumWorkingDistance", Double,
         "Smallest usable object-to-lens distance in metres.")
prop_var(OP, "OpticsType", "Magnification", Double, "Image size divided by object size.")
prop_var(OP, "OpticsType", "OpticalFormat", String,
         "Largest sensor diagonal the lens covers, for example 2/3 inch.")
prop_var(OP, "OpticsType", "MountType", String,
         "Lens mount, for example C, CS, F or M12.")
prop_var(OP, "OpticsType", "LensType", String,
         "Lens class, for example Entocentric, Telecentric or Fisheye.")

object_type(1006, "IlluminationType", BaseObjectType,
            "A controlled light source associated with a sensor. Member names align with "
            "the ILampType and ILightingControllerType of OPC 40100-2.")
IL = 1006
prop_var(IL, "IlluminationType", "LampType", String,
         "Emitter technology, for example LED, Laser, Xenon or Fluorescent.")
prop_var(IL, "IlluminationType", "Wavelength", Double,
         "Dominant emission wavelength in nanometres.")
prop_var(IL, "IlluminationType", "RelativeIntensity", Double,
         "Current output as a percentage of full capability.")
prop_var(IL, "IlluminationType", "LightingMode", String,
         "Operating mode, for example Continuous, Strobe or Modulated.")
prop_var(IL, "IlluminationType", "Quality", Double,
         "Remaining emitter quality as a percentage; 100 is new.")

# ---- Media endpoints -------------------------------------------------------
object_type(1007, "MediaEndpointType", BaseObjectType,
            "Abstract base for a media access point. The endpoint DESCRIBES where media "
            "can be obtained; on the default path the media itself never traverses OPC "
            "UA. Subtypes add the protocol- or format-specific members.",
            abstract=True)
ME = 1007
prop_var(ME, "MediaEndpointType", "EndpointId", String,
         "Identifier of this endpoint, unique within the sensor.", MR_Mandatory)
prop_var(ME, "MediaEndpointType", "EndpointUri", String,
         "Base URI at which the media is served. May be a template that "
         "GetStreamEndpoint or GetClip resolves into a session-specific URI.",
         MR_Mandatory)
prop_var(ME, "MediaEndpointType", "State", VisionEndpointStateEnum,
         "Runtime state of this endpoint.", MR_Mandatory)
prop_var(ME, "MediaEndpointType", "Authentication", VisionEndpointAuthenticationEnum,
         "Credential the media plane requires. Independent of the OPC UA session.",
         MR_Mandatory)
prop_var(ME, "MediaEndpointType", "SecureTransport", Boolean,
         "True when the media transport itself provides confidentiality, for example "
         "RTSPS, SRT with encryption, or HTTPS. Mandatory because clause 12.2 "
         "evaluates credential issuance on it: a Server SHALL NOT return a URI "
         "embedding a credential unless this is true and the OPC UA SecureChannel is "
         "SignAndEncrypt. A client SHALL treat false as meaning the media transport "
         "offers no confidentiality, whatever Authentication states.",
         MR_Mandatory)
prop_var(ME, "MediaEndpointType", "ProfileName", String,
         "Vendor profile label, for example main or sub.")

object_type(1008, "StreamEndpointType", T(ME),
            "A continuous media stream. A conformant Server SHALL expose at least one "
            "instance whose StreamProtocol is Rtsp; every other protocol is optional. "
            "This is the default way to obtain live imagery.")
SE = 1008
prop_var(SE, "StreamEndpointType", "StreamProtocol", VisionStreamProtocolEnum,
         "Protocol of this stream. Rtsp is the mandatory default.", MR_Mandatory)
prop_var(SE, "StreamEndpointType", "ProtocolVersion", String,
         "Version of StreamProtocol served, e.g. '1.0' for RTSP/1.0 (RFC 2326) or '2.0' "
         "for RTSP/2.0 (RFC 7826). RTSP 2.0 is not backward compatible with 1.0, so a "
         "client that must interoperate without probing reads this.", MR_Mandatory)
prop_var(SE, "StreamEndpointType", "Codec", VisionVideoCodecEnum,
         "Codec carried by the stream.")
prop_var(SE, "StreamEndpointType", "Width", UInt32, "Streamed frame width in pixels.")
prop_var(SE, "StreamEndpointType", "Height", UInt32, "Streamed frame height in pixels.")
prop_var(SE, "StreamEndpointType", "FrameRate", Double, "Streamed frames per second.")
prop_var(SE, "StreamEndpointType", "Bitrate", UInt32,
         "Target bitrate in bits per second.")
prop_var(SE, "StreamEndpointType", "MaxSessions", UInt32,
         "Maximum concurrent sessions this endpoint will serve.")
prop_var(SE, "StreamEndpointType", "ActiveSessions", UInt32,
         "Sessions currently leased.")

object_type(1009, "ClipEndpointType", T(ME),
            "A still-image access point. A conformant Server SHALL expose at least one "
            "instance whose ClipFormat is Jpeg; every other format is optional. In "
            "addition to the default URI path, this type MAY publish the encoded image "
            "inline as a ByteString so that clients can Read or Subscribe to it - but "
            "only within MaxInlineClipSize, which SHALL NOT exceed the Server's "
            "ServerCapabilities.MaxByteStringLength. Inline delivery serves single "
            "stills; it is not a substitute for a StreamEndpoint.")
CE = 1009
prop_var(CE, "ClipEndpointType", "ClipFormat", VisionClipFormatEnum,
         "Encoding of clips from this endpoint. Jpeg is the mandatory default.",
         MR_Mandatory)
prop_var(CE, "ClipEndpointType", "Quality", UInt32,
         "Encoder quality 0 to 100 where the format defines one, for example JPEG.")
prop_var(CE, "ClipEndpointType", "Width", UInt32, "Clip width in pixels.")
prop_var(CE, "ClipEndpointType", "Height", UInt32, "Clip height in pixels.")
prop_var(CE, "ClipEndpointType", "Retention", Duration,
         "How long a generated clip remains retrievable at its Uri.")
prop_var(CE, "ClipEndpointType", "InlineDeliveryEnabled", Boolean,
         "True when LatestClip is published. False, the default, means clients use the "
         "URI path exclusively.")
prop_var(CE, "ClipEndpointType", "MaxInlineClipSize", UInt32,
         "Largest inline payload this endpoint will publish, in bytes. SHALL NOT exceed "
         "Server.ServerCapabilities.MaxByteStringLength, and a Read or Publish response "
         "carrying the value is additionally bounded by the Session's "
         "MaxResponseMessageSize. See clause 6.4.")
data_var(CE, "ClipEndpointType", "LatestClip", ByteString,
         "The most recently produced clip, encoded per ClipFormat. Subscribable: the "
         "value changes once per acquisition, which suits one-image-per-part inspection. "
         "When the encoded image exceeds MaxInlineClipSize the Server SHALL set the "
         "StatusCode to Bad_EncodingLimitsExceeded, and the client SHALL fall back to "
         "LatestClipMetadata.Uri, which remains valid.")
data_var(CE, "ClipEndpointType", "LatestClipMetadata", VisionImageReferenceDataType,
         "Descriptor of LatestClip, including the out-of-band Uri and Digest. Populated "
         "whenever a clip exists, whether or not the bytes are published inline.")

object_type(1010, "VisionMediaManagementType", BaseObjectType,
            "Container and control surface for a sensor's media endpoints. Holds the "
            "endpoint folders and the Methods that select, configure and lease them.")
MM = 1010
placeholder_obj = obj_member  # MandatoryPlaceholder members are ordinary obj_members

sef = folder_member(MM, "VisionMediaManagementType", "StreamEndpoints",
                    "StreamEndpointType instances offered by this sensor. At least one "
                    "uses Rtsp.", MR_Mandatory)
placeholder_obj(sef, "VisionMediaManagementType_StreamEndpoints", "<StreamEndpoint>",
                T(SE), "A stream endpoint offered by this sensor.",
                rule=MR_MandatoryPlaceholder)
cef = folder_member(MM, "VisionMediaManagementType", "ClipEndpoints",
                    "ClipEndpointType instances offered by this sensor. At least one "
                    "uses Jpeg.", MR_Mandatory)
placeholder_obj(cef, "VisionMediaManagementType_ClipEndpoints", "<ClipEndpoint>",
                T(CE), "A clip endpoint offered by this sensor.",
                rule=MR_MandatoryPlaceholder)
prop_var(MM, "VisionMediaManagementType", "PreferredStreamEndpoint", NodeId_,
         "The StreamEndpoint a client should use unless it has a reason not to.")
prop_var(MM, "VisionMediaManagementType", "PreferredClipEndpoint", NodeId_,
         "The ClipEndpoint a client should use unless it has a reason not to.")
method(MM, "VisionMediaManagementType", "GetStreamEndpoint",
       "Lease a stream. Returns a session descriptor whose Uri may embed a time-limited "
       "credential; the client opens that Uri with the media protocol. The preferred "
       "protocol is advisory - the Server returns what it can serve, which is at "
       "minimum RTSP.",
       MR_Mandatory,
       inargs=[("Endpoint", NodeId_,
                "StreamEndpoint to lease. Null selects PreferredStreamEndpoint, or, "
                "when that is also null, the first endpoint in StreamEndpoints in "
                "BrowseName order that satisfies the request."),
               ("ProfileName", String, "Requested profile, or empty for the default."),
               ("PreferredProtocol", VisionStreamProtocolEnum,
                "Advisory protocol preference.")],
       outargs=[("Session", VisionStreamSessionDataType, "The leased session."),
                ("Endpoint", NodeId_, "The StreamEndpoint that was leased.")])
method(MM, "VisionMediaManagementType", "ReleaseStreamEndpoint",
       "Release a previously leased stream session. A Server SHALL also expire leases "
       "automatically at ExpiresAt.",
       MR_Mandatory,
       inargs=[("SessionToken", ByteString, "Token from GetStreamEndpoint.")])
method(MM, "VisionMediaManagementType", "ConfigureStreamEndpoint",
       "Change the encoding parameters of a stream endpoint. A Server MAY reject or "
       "clamp values it cannot serve; the resulting effective values are readable on "
       "the endpoint.",
       MR_Optional,
       inargs=[("Endpoint", NodeId_, "StreamEndpoint to configure."),
               ("Codec", VisionVideoCodecEnum, "Requested codec."),
               ("Width", UInt32, "Requested width in pixels."),
               ("Height", UInt32, "Requested height in pixels."),
               ("FrameRate", Double, "Requested frames per second."),
               ("Bitrate", UInt32, "Requested bitrate in bits per second.")])
method(MM, "VisionMediaManagementType", "SelectEndpoint",
       "Designate the preferred stream and clip endpoints, updating "
       "PreferredStreamEndpoint and PreferredClipEndpoint.",
       MR_Optional,
       inargs=[("StreamEndpoint", NodeId_,
                "Preferred stream endpoint, or null to leave unchanged."),
               ("ClipEndpoint", NodeId_,
                "Preferred clip endpoint, or null to leave unchanged.")])
method(MM, "VisionMediaManagementType", "GetClip",
       "Obtain a still image: either the frame associated with a given ResultId, or the "
       "frame nearest a timestamp. The returned descriptor always carries a Uri. The "
       "bytes are returned inline only when RequestInline is true AND the encoded image "
       "fits MaxInlineClipSize; otherwise InlineImage is empty and the client uses the "
       "Uri.",
       MR_Mandatory,
       inargs=[("Endpoint", NodeId_,
                "ClipEndpoint to use. Null selects PreferredClipEndpoint, or, when that "
                "is also null, the first endpoint in ClipEndpoints in BrowseName order "
                "that supports Format."),
               ("ResultId", String, "Result whose frame is wanted, or empty."),
               ("Timestamp", UtcTime,
                "Frame nearest this time, used when ResultId is empty."),
               ("Format", VisionClipFormatEnum,
                "Requested encoding; Jpeg is always supported."),
               ("RequestInline", Boolean,
                "Ask for the bytes inline in addition to the Uri.")],
       outargs=[("Image", VisionImageReferenceDataType, "Descriptor of the clip."),
                ("Endpoint", NodeId_, "The ClipEndpoint that served the clip."),
                ("InlineImage", ByteString,
                 "Encoded bytes, or empty when not requested or too large.")])

# ---- Coordinate frames and calibration ------------------------------------
object_type(1011, "CoordinateFrameType", BaseObjectType,
            "A named coordinate frame. Frames form a tree through ParentFrame, so a "
            "client can compose a chain from a camera frame to a world frame. Roles "
            "follow ISO 9787, which standardises WHICH frames exist - note that no "
            "standard defines how to CALIBRATE between them, which is why "
            "ExtrinsicCalibrationType carries the result explicitly.")
CF = 1011
prop_var(CF, "CoordinateFrameType", "FrameId", String,
         "Identifier referenced by VisionPose3DDataType.FrameId.", MR_Mandatory)
prop_var(CF, "CoordinateFrameType", "Role", VisionFrameRoleEnum,
         "Role of this frame.", MR_Mandatory)
prop_var(CF, "CoordinateFrameType", "ParentFrame", NodeId_,
         "The frame this one is expressed in; null for a root frame.")
data_var(CF, "CoordinateFrameType", "Transform", VisionPose3DDataType,
         "Pose of this frame within ParentFrame.")

object_type(1012, "VisionCalibrationType", BaseObjectType,
            "Abstract base for a calibration result, carrying the provenance a client "
            "needs in order to decide whether to trust it.", abstract=True)
CAL = 1012
prop_var(CAL, "VisionCalibrationType", "CalibrationId", String,
         "Identifier of this calibration.", MR_Mandatory)
prop_var(CAL, "VisionCalibrationType", "PerformedAt", UtcTime,
         "When the calibration was computed.", MR_Mandatory)
prop_var(CAL, "VisionCalibrationType", "Valid", Boolean,
         "False when the Server knows the calibration is stale, for example after a "
         "mount change.", MR_Mandatory)
prop_var(CAL, "VisionCalibrationType", "ResidualError", Double,
         "Reprojection or fit residual, in the natural unit of the method.")
prop_var(CAL, "VisionCalibrationType", "Method", String,
         "Free-text method identifier, for example Zhang, Tsai-Lenz or Daniilidis.")

object_type(1013, "IntrinsicCalibrationType", T(CAL),
            "Camera intrinsics and lens distortion for a specific image size.")
data_var(1013, "IntrinsicCalibrationType", "Intrinsics", VisionIntrinsicsDataType,
         "The intrinsic parameters.", MR_Mandatory)

object_type(1014, "ExtrinsicCalibrationType", T(CAL),
            "The rigid transform between two frames. For a robot cell this is the "
            "hand-eye calibration. No ISO, IEC or VDI standard defines the calibration "
            "PROCEDURE, so this type carries the resulting transform, the mounting "
            "arrangement it applies to, and its residual, which is what a consumer "
            "actually needs.")
EX = 1014
prop_var(EX, "ExtrinsicCalibrationType", "Mount", VisionCalibrationMountEnum,
         "Mounting arrangement the transform applies to.", MR_Mandatory)
prop_var(EX, "ExtrinsicCalibrationType", "SourceFrame", NodeId_,
         "Frame the transform maps from.", MR_Mandatory)
prop_var(EX, "ExtrinsicCalibrationType", "TargetFrame", NodeId_,
         "Frame the transform maps to.", MR_Mandatory)
data_var(EX, "ExtrinsicCalibrationType", "Transform", VisionPose3DDataType,
         "Pose of SourceFrame expressed in TargetFrame.", MR_Mandatory)

# ---- Sensors ---------------------------------------------------------------
object_type(1002, "VisionSensorType", BaseObjectType,
            "Abstract base for anything that produces imagery or range data. The "
            "RealityKind property is what makes the model sim/real symmetric: a physical "
            "camera and a simulated one expose the same members, so a client written "
            "against this type works against either.",
            abstract=True)
VS = 1002
prop_var(VS, "VisionSensorType", "SensorId", String,
         "Identifier of the sensor, unique within the Server.", MR_Mandatory)
prop_var(VS, "VisionSensorType", "RealityKind", VisionRealityKindEnum,
         "Whether this sensor is physical, simulated or hybrid.", MR_Mandatory)
prop_var(VS, "VisionSensorType", "Modality", VisionSensorModalityEnum,
         "What the sensor measures.", MR_Mandatory)
prop_var(VS, "VisionSensorType", "Manufacturer", LocalizedText, "Device manufacturer.")
prop_var(VS, "VisionSensorType", "Model", LocalizedText, "Device model designation.")
prop_var(VS, "VisionSensorType", "SerialNumber", String, "Device serial number.")
prop_var(VS, "VisionSensorType", "DeviceUri", String,
         "Transport-level device identifier, for example a GigE Vision or USB3 Vision "
         "device id. Lets a client correlate this sensor with the GenICam layer that "
         "actually moves the pixels.")
prop_var(VS, "VisionSensorType", "FrameId", String,
         "FrameId of this sensor's own camera frame.")
obj_member(VS, "VisionSensorType", "Media", T(MM),
           "Media endpoints and their control surface.", MR_Mandatory)
obj_member(VS, "VisionSensorType", "Optics", T(OP), "Lens in front of this sensor.")
obj_member(VS, "VisionSensorType", "Illumination", T(IL),
           "Light source associated with this sensor.")
folder_member(VS, "VisionSensorType", "Calibrations",
              "VisionCalibrationType instances for this sensor.", MR_Optional)

object_type(1003, "ImageSensorType", T(VS),
            "A two-dimensional imaging sensor. The acquisition parameters use GenICam "
            "SFNC 2.8 names and semantics so that a Server bridging a GenICam device can "
            "map them one to one, and a client that knows SFNC needs no translation "
            "table. This is the layer OPC 40100-2 leaves empty: its VisionImageSensorType "
            "adds no members at all.")
IS = 1003
prop_var(IS, "ImageSensorType", "Width", UInt32,
         "Image width in pixels (SFNC Width).", MR_Mandatory)
prop_var(IS, "ImageSensorType", "Height", UInt32,
         "Image height in pixels (SFNC Height).", MR_Mandatory)
prop_var(IS, "ImageSensorType", "PixelFormat", String,
         "Pixel format using GenICam PFNC naming, for example Mono8, BayerRG12 or RGB8 "
         "(SFNC PixelFormat).", MR_Mandatory)
prop_var(IS, "ImageSensorType", "ExposureTime", Double,
         "Exposure time in microseconds (SFNC ExposureTime).")
prop_var(IS, "ImageSensorType", "Gain", Double, "Analog gain (SFNC Gain).")
prop_var(IS, "ImageSensorType", "AcquisitionFrameRate", Double,
         "Frames per second (SFNC AcquisitionFrameRate).")
prop_var(IS, "ImageSensorType", "TriggerMode", String,
         "Trigger mode, On or Off (SFNC TriggerMode).")
prop_var(IS, "ImageSensorType", "TriggerSource", String,
         "Active trigger source (SFNC TriggerSource).")
prop_var(IS, "ImageSensorType", "OffsetX", UInt32,
         "Region-of-interest x offset (SFNC OffsetX).")
prop_var(IS, "ImageSensorType", "OffsetY", UInt32,
         "Region-of-interest y offset (SFNC OffsetY).")
prop_var(IS, "ImageSensorType", "BinningHorizontal", UInt32,
         "Horizontal binning factor (SFNC BinningHorizontal).")
prop_var(IS, "ImageSensorType", "BinningVertical", UInt32,
         "Vertical binning factor (SFNC BinningVertical).")
prop_var(IS, "ImageSensorType", "ReverseX", Boolean, "Horizontal flip (SFNC ReverseX).")
prop_var(IS, "ImageSensorType", "ReverseY", Boolean, "Vertical flip (SFNC ReverseY).")
data_var(IS, "ImageSensorType", "Intrinsics", VisionIntrinsicsDataType,
         "Currently applicable intrinsics, mirroring the active IntrinsicCalibration.")

object_type(1004, "Depth3DSensorType", T(VS),
            "A sensor producing depth or point-cloud data. Point clouds are large and are "
            "obtained through a media endpoint, not read as an OPC UA array.")
D3 = 1004
prop_var(D3, "Depth3DSensorType", "MinDepth", Double,
         "Smallest reportable range in metres.")
prop_var(D3, "Depth3DSensorType", "MaxDepth", Double,
         "Largest reportable range in metres.")
prop_var(D3, "Depth3DSensorType", "DepthScale", Double,
         "Metres represented by one unit of the raw depth map.")
prop_var(D3, "Depth3DSensorType", "Baseline", Double,
         "Stereo baseline in metres, where applicable.")
prop_var(D3, "Depth3DSensorType", "PointsPerFrame", UInt32,
         "Nominal point count per frame.")

# ---- Simulation interface --------------------------------------------------
interface_type(1030, "IVisionSimulatedType", BaseInterfaceType,
               "Applied to a sensor whose RealityKind is Simulated or Hybrid. It names "
               "the simulator and the scene prim being rendered, which is what makes a "
               "synthetic sensor addressable in the same terms as a physical one. When "
               "the Server also implements OPC UA - OpenUSD Scene Materialization, "
               "PrimPath resolves to a UsdGeomCameraType instance and HasScenePrim points "
               "at it directly.")
SIM = 1030
prop_var(SIM, "IVisionSimulatedType", "SimulatorUri", String,
         "Identifier of the simulator or renderer, for example an Isaac Sim instance.",
         MR_Mandatory)
prop_var(SIM, "IVisionSimulatedType", "StageIdentifier", String,
         "Root layer identifier of the stage being rendered. Uses the same identity "
         "contract as OPC UA - OpenUSD Bindings and Scene Materialization.",
         MR_Mandatory)
prop_var(SIM, "IVisionSimulatedType", "PrimPath", String,
         "Absolute SdfPath of the camera prim this sensor renders from.", MR_Mandatory)
prop_var(SIM, "IVisionSimulatedType", "GroundTruthAvailable", Boolean,
         "True when the simulator can emit annotator ground truth alongside imagery.")
prop_var(SIM, "IVisionSimulatedType", "RandomizationSeed", UInt64,
         "Seed of the active domain-randomization run, so a dataset can be reproduced.")

# ---- AI: model, dataset, deployment ----------------------------------------
object_type(1015, "AiModelType", BaseObjectType,
            "Nameplate of a trained model. The member set is deliberately aligned with "
            "the IDTA 02060 AI Model Nameplate submodel template, which is currently the "
            "only standardised description of an industrial AI model, so an Asset "
            "Administration Shell can be populated from this node without loss.")
AM = 1015
prop_var(AM, "AiModelType", "ModelId", String, "Identifier of the model.", MR_Mandatory)
prop_var(AM, "AiModelType", "Name", LocalizedText, "Human-readable model name.",
         MR_Mandatory)
prop_var(AM, "AiModelType", "Version", String, "Model version.", MR_Mandatory)
prop_var(AM, "AiModelType", "Framework", String,
         "Producing framework, for example PyTorch, TensorFlow or scikit-learn.")
prop_var(AM, "AiModelType", "Format", String,
         "Serialization format, for example ONNX, TensorRT or OpenVINO IR.")
prop_var(AM, "AiModelType", "TaskKind", String,
         "What the model does, for example Detection2D, Detection3D, Classification, "
         "Segmentation, PoseEstimation or AnomalyDetection.")
prop_var(AM, "AiModelType", "Digest", ByteString,
         "Cryptographic digest of the model artefact, for provenance and integrity. "
         "Mandatory: clause 12.6 requires it for every model whose artefact is "
         "obtainable through ArtifactUri, and it is the terminus of the provenance "
         "chain that UsesModel keeps intact.",
         MR_Mandatory)
prop_var(AM, "AiModelType", "DigestAlgorithm", String,
         "Hash function used for Digest. SHALL name a function with at least 256-bit "
         "output and no known collision weakness; SHA-256 is the default and is always "
         "acceptable. SHALL NOT be MD5, SHA-1 or a truncated variant - chosen-prefix "
         "collisions against those are practical, so a substituted artefact would pass "
         "verification. SHALL be non-empty where Digest is non-empty. See clause 12.6.",
         MR_Mandatory)
prop_var(AM, "AiModelType", "ArtifactUri", String,
         "Where the model artefact can be obtained. Treated as untrusted input.")
prop_var(AM, "AiModelType", "ProvenanceUri", String,
         "Training provenance or model card location.")
prop_var(AM, "AiModelType", "LabelClasses", String,
         "Ordered class label set; the index corresponds to "
         "VisionDetectionDataType.ClassId.", MR_Optional, valuerank="1")
data_var(AM, "AiModelType", "Inputs", VisionTensorSignatureDataType,
         "Input tensor signatures.", MR_Optional, valuerank="1")
data_var(AM, "AiModelType", "Outputs", VisionTensorSignatureDataType,
         "Output tensor signatures.", MR_Optional, valuerank="1")

object_type(1016, "AiDatasetType", BaseObjectType,
            "A dataset used to train or validate a model. Aligned with the IDTA 02058 AI "
            "Dataset submodel template. SourceKind distinguishes real capture from "
            "simulator output, which is the provenance a reviewer needs when synthetic "
            "data is involved.")
AD = 1016
prop_var(AD, "AiDatasetType", "DatasetId", String, "Identifier of the dataset.",
         MR_Mandatory)
prop_var(AD, "AiDatasetType", "Name", LocalizedText, "Human-readable dataset name.")
prop_var(AD, "AiDatasetType", "Version", String, "Dataset version.")
prop_var(AD, "AiDatasetType", "SourceKind", VisionDatasetSourceEnum,
         "Whether samples are real, synthetic or mixed.", MR_Mandatory)
prop_var(AD, "AiDatasetType", "SampleCount", UInt64, "Number of samples.")
prop_var(AD, "AiDatasetType", "LabelClasses", String, "Class labels present.",
         MR_Optional, valuerank="1")
prop_var(AD, "AiDatasetType", "CreatedAt", UtcTime, "Creation time.")
prop_var(AD, "AiDatasetType", "ArtifactUri", String,
         "Where the dataset can be obtained.")
prop_var(AD, "AiDatasetType", "Digest", ByteString, "Digest of the dataset artefact.")

object_type(1017, "AiDeploymentType", BaseObjectType,
            "A model made executable somewhere. Aligned with the IDTA 02059 AI Deployment "
            "submodel template. InferenceLocation is the on-server versus off-server "
            "switch: it changes where the computation happens and therefore the trust "
            "boundary, but it does NOT change the result contract.")
AY = 1017
prop_var(AY, "AiDeploymentType", "DeploymentId", String,
         "Identifier of the deployment.", MR_Mandatory)
prop_var(AY, "AiDeploymentType", "InferenceLocation", VisionInferenceLocationEnum,
         "Where inference executes.", MR_Mandatory)
prop_var(AY, "AiDeploymentType", "AcceleratorKind", VisionAcceleratorKindEnum,
         "Compute device executing the model.")
prop_var(AY, "AiDeploymentType", "AcceleratorName", String,
         "Free-text accelerator identification, for example an NPU or GPU part name.")
prop_var(AY, "AiDeploymentType", "EndpointUri", String,
         "Inference endpoint when InferenceLocation is not OnServer. Treated as "
         "untrusted input and subject to the resolver policy of the security clause.")
prop_var(AY, "AiDeploymentType", "LatencyBudget", Duration,
         "Latency the deployment is expected to meet, so a client can detect regression.")
prop_var(AY, "AiDeploymentType", "BatchSize", UInt32,
         "Configured inference batch size.")
prop_var(AY, "AiDeploymentType", "State", VisionEndpointStateEnum,
         "Runtime state of the deployment.")

# ---- Results ---------------------------------------------------------------
object_type(1020, "VisionResultType", BaseObjectType,
            "Abstract base for a vision result. Unlike OPC 40100-1, whose ResultContent "
            "is BaseDataType[] and explicitly not defined, the subtypes of this type "
            "define their content. The trust members exist so that a high-risk "
            "deployment can log which model version produced a decision and where its "
            "explanation lives.",
            abstract=True)
VR = 1020
prop_var(VR, "VisionResultType", "ResultId", String,
         "Identifier of the result, unique within the Server.", MR_Mandatory)
prop_var(VR, "VisionResultType", "CreationTime", UtcTime,
         "When the result was produced.", MR_Mandatory)
prop_var(VR, "VisionResultType", "Sensor", NodeId_, "Sensor the frame came from.")
prop_var(VR, "VisionResultType", "Pipeline", NodeId_, "Pipeline that produced it.")
prop_var(VR, "VisionResultType", "ModelVersionUsed", String,
         "Version of the model that produced the result. Required in practice for "
         "auditability when the model can be updated in the field.")
prop_var(VR, "VisionResultType", "Confidence", Double,
         "Overall confidence in the range 0.0 to 1.0, where the model reports one.")
prop_var(VR, "VisionResultType", "ExplanationUri", String,
         "Location of an explanation artefact, for example a saliency map. Treated as "
         "untrusted input.")
data_var(VR, "VisionResultType", "Frame", VisionImageReferenceDataType,
         "Reference to the frame this result was computed from.")

object_type(1021, "InspectionResultType", T(VR),
            "A machine-vision inspection outcome: a verdict plus the characteristics that "
            "produced it. Carrying nominal, actual, tolerance AND uncertainty is what "
            "makes the verdict reproducible by a third party, and is why "
            "VisionResultEvaluationEnum has a NotDecidable value.")
IR = 1021
prop_var(IR, "InspectionResultType", "Evaluation", VisionResultEvaluationEnum,
         "Overall verdict.", MR_Mandatory)
prop_var(IR, "InspectionResultType", "PartId", String,
         "Identifier of the inspected part.")
prop_var(IR, "InspectionResultType", "RecipeId", String,
         "Identifier of the inspection recipe or program applied.")
data_var(IR, "InspectionResultType", "Characteristics", VisionCharacteristicDataType,
         "Measured characteristics.", MR_Mandatory, valuerank="1")

object_type(1022, "DetectionResultType", T(VR),
            "A robotics-vision perception outcome: zero or more detected instances, each "
            "optionally carrying a 6-DoF pose suitable for picking or servoing.")
DR = 1022
data_var(DR, "DetectionResultType", "Detections", VisionDetectionDataType,
         "Detected instances.", MR_Mandatory, valuerank="1")
prop_var(DR, "DetectionResultType", "FrameId", String,
         "FrameId that detection poses are expressed in.")

object_type(1023, "SegmentationResultType", T(VR),
            "A per-pixel labelling outcome. The mask itself is referenced, not inlined.")
SR = 1023
prop_var(SR, "SegmentationResultType", "LabelClasses", String,
         "Class labels present in the mask.", MR_Optional, valuerank="1")
data_var(SR, "SegmentationResultType", "Mask", VisionImageReferenceDataType,
         "Reference to the encoded mask image.", MR_Mandatory)

# ---- Feedback --------------------------------------------------------------
object_type(1024, "VisionFeedbackType", BaseObjectType,
            "The return path into the vision system. It serves three purposes at once: "
            "drawing geometry onto the outgoing stream, recording a downstream verdict "
            "against a result, and - most importantly - accepting corrected labels that "
            "become training data. That last purpose is what turns a deployed inspection "
            "system into a learning one. Every Method here is a WRITE and requires "
            "explicit authorization.")
FB = 1024
prop_var(FB, "VisionFeedbackType", "OverlayEnabled", Boolean,
         "True when submitted geometry is rendered onto the outgoing stream.")
prop_var(FB, "VisionFeedbackType", "OverlayStyle", String,
         "Vendor-defined overlay style identifier.")
prop_var(FB, "VisionFeedbackType", "OverlayTtl", Duration,
         "How long submitted overlay geometry remains rendered.")
prop_var(FB, "VisionFeedbackType", "MaxInlineFeedbackImageSize", UInt32,
         "Largest inline image this surface accepts, in bytes. SHALL NOT exceed "
         "Server.ServerCapabilities.MaxByteStringLength, and a Call request carrying the "
         "value is additionally bounded by the Session's MaxRequestMessageSize. An "
         "oversized payload is rejected with Bad_EncodingLimitsExceeded and the client "
         "uses SubmitImageReference instead. See clause 6.4.")
method(FB, "VisionFeedbackType", "SubmitDetections",
       "Push detected geometry back into the vision system. With Purpose set to Overlay "
       "the boxes are drawn on the stream; with Purpose set to GroundTruthLabel they are "
       "retained as corrected labels for the associated learning job.",
       MR_Optional,
       inargs=[("Purpose", VisionFeedbackPurposeEnum, "Why the geometry is being sent."),
               ("Detections", VisionDetectionDataType, "The detections.", 1),
               ("FrameReference", VisionImageReferenceDataType,
                "Frame the detections belong to."),
               ("InlineImage", ByteString,
                "Optional annotated image, accepted only within "
                "MaxInlineFeedbackImageSize; otherwise use SubmitImageReference.")])
method(FB, "VisionFeedbackType", "SubmitInspectionResult",
       "Record a downstream inspection verdict against a result, for reconciliation with "
       "what the vision system originally reported.",
       MR_Optional,
       inargs=[("ResultId", String, "Result being reconciled."),
               ("Evaluation", VisionResultEvaluationEnum, "Downstream verdict."),
               ("Characteristics", VisionCharacteristicDataType,
                "Downstream measurements, where available.", 1)])
method(FB, "VisionFeedbackType", "SubmitCorrection",
       "Submit a human-in-the-loop or downstream correction of a previous result. This "
       "is the primary source of labelled data for retraining.",
       MR_Optional,
       inargs=[("ResultId", String, "Result being corrected."),
               ("Purpose", VisionFeedbackPurposeEnum, "Normally GroundTruthLabel."),
               ("CorrectedDetections", VisionDetectionDataType,
                "Corrected detections, where the result was a detection.", 1),
               ("CorrectedCharacteristics", VisionCharacteristicDataType,
                "Corrected characteristics, where the result was an inspection.", 1),
               ("Reason", LocalizedText, "Why the correction was made."),
               ("InlineImage", ByteString,
                "Optional corrected or annotated image, accepted only within "
                "MaxInlineFeedbackImageSize; otherwise use SubmitImageReference.")])
method(FB, "VisionFeedbackType", "SubmitImageReference",
       "The default way to hand an image back: by reference. Used whenever the image "
       "exceeds MaxInlineFeedbackImageSize, and preferred in all cases.",
       MR_Optional,
       inargs=[("Purpose", VisionFeedbackPurposeEnum, "Why the image is being sent."),
               ("Image", VisionImageReferenceDataType, "Descriptor of the image."),
               ("ResultId", String, "Associated result, or empty.")])

# ---- Inference pipeline ----------------------------------------------------
object_type(1018, "InferencePipelineType", BaseObjectType,
            "Binds a sensor to a deployment and publishes the results. The same type "
            "serves on-server and off-server inference: when the deployment is remote "
            "the Server publishes results it did not compute, and the only observable "
            "difference is AiDeployment.InferenceLocation.")
IP = 1018
prop_var(IP, "InferencePipelineType", "PipelineId", String,
         "Identifier of the pipeline.", MR_Mandatory)
prop_var(IP, "InferencePipelineType", "Sensor", NodeId_,
         "Sensor supplying frames.", MR_Mandatory)
prop_var(IP, "InferencePipelineType", "Deployment", NodeId_,
         "Deployment executing inference.", MR_Mandatory)
prop_var(IP, "InferencePipelineType", "State", VisionEndpointStateEnum,
         "Runtime state of the pipeline.", MR_Mandatory)
prop_var(IP, "InferencePipelineType", "Continuous", Boolean,
         "True while the pipeline runs on every frame.")
folder_member(IP, "InferencePipelineType", "Results",
              "Recent VisionResultType instances produced by this pipeline.", MR_Optional)
obj_member(IP, "InferencePipelineType", "Feedback", T(FB),
           "Feedback surface for pushing results back into the vision system.")
method(IP, "InferencePipelineType", "RunInference",
       "Run inference once, on the current or a specified frame, and return the "
       "identifier of the result that was produced.",
       MR_Optional,
       inargs=[("Timestamp", UtcTime,
                "Frame nearest this time, or null for the newest.")],
       outargs=[("ResultId", String, "Identifier of the produced result.")])
method(IP, "InferencePipelineType", "StartContinuous",
       "Begin running inference on every acquired frame.", MR_Optional)
method(IP, "InferencePipelineType", "Stop",
       "Stop continuous inference.", MR_Optional)

# ---- Learning --------------------------------------------------------------
object_type(1019, "LearningJobType", BaseObjectType,
            "One turn of the capture, label, train and promote loop. It exists so that "
            "corrections arriving through VisionFeedbackType have somewhere to accumulate "
            "and a defined path into a new model version. A Server may implement only the "
            "capture stages and leave training to an external MLOps system - the state "
            "machine is the same either way.")
LJ = 1019
prop_var(LJ, "LearningJobType", "JobId", String, "Identifier of the job.", MR_Mandatory)
prop_var(LJ, "LearningJobType", "State", VisionLearningJobStateEnum,
         "Current stage of the loop.", MR_Mandatory)
prop_var(LJ, "LearningJobType", "Dataset", NodeId_,
         "Dataset being accumulated or used.")
prop_var(LJ, "LearningJobType", "BaseModel", NodeId_, "Model the job starts from.")
prop_var(LJ, "LearningJobType", "CandidateModel", NodeId_,
         "Model produced by the job, awaiting promotion.")
prop_var(LJ, "LearningJobType", "SamplesCollected", UInt64,
         "Samples accumulated so far, including corrections fed back.")
prop_var(LJ, "LearningJobType", "LastError", LocalizedText,
         "Diagnostic for the Failed state.")
method(LJ, "LearningJobType", "StartCollection",
       "Begin accumulating samples and corrections into the dataset.", MR_Optional)
method(LJ, "LearningJobType", "StopCollection",
       "Stop accumulating samples.", MR_Optional)
method(LJ, "LearningJobType", "TriggerTraining",
       "Request that a candidate model be trained from the collected dataset.",
       MR_Optional,
       outargs=[("Accepted", Boolean, "True when the request was queued.")])
method(LJ, "LearningJobType", "PromoteModel",
       "Promote the candidate model so that deployments begin using it. A Server SHOULD "
       "require a distinct authorization for this Method.",
       MR_Optional,
       inargs=[("Deployment", NodeId_, "Deployment to update, or null for all.")],
       outargs=[("PromotedModel", NodeId_, "The model now in use.")])

# ---- Root ------------------------------------------------------------------
object_type(1001, "VisionRootType", BaseObjectType,
            "The single well-known entry point for everything in this model. A client "
            "starts here, enumerates Sensors, and follows references outward. Mirrors "
            "the discovery pattern of OPC UA - OpenUSD Bindings.")
VRT = 1001
folder_member(VRT, "VisionRootType", "Sensors",
              "VisionSensorType instances known to this Server.", MR_Mandatory)
folder_member(VRT, "VisionRootType", "Pipelines",
              "InferencePipelineType instances.", MR_Optional)
folder_member(VRT, "VisionRootType", "Models",
              "AiModelType, AiDatasetType and AiDeploymentType instances.", MR_Optional)
folder_member(VRT, "VisionRootType", "Frames",
              "CoordinateFrameType instances.", MR_Optional)
folder_member(VRT, "VisionRootType", "LearningJobs",
              "LearningJobType instances.", MR_Optional)

# ---- Well-known instance ----------------------------------------------------
well_known(7001, "Vision", T(VRT), Server,
           "The well-known Vision entry point, a component of the Server object. A "
           "conformant Server exposes exactly one.")

# ---------------------------------------------------------------------------
# Appended members
# ---------------------------------------------------------------------------
# Instance-member NodeIds are assigned sequentially from 6001 in declaration order, so
# new members MUST be appended below this line, never inserted above it, to keep every
# previously published member NodeId stable.

# Optional binding to the OPC UA - Data Channels errata proposal (clause 6.7). Declared
# on the shared MediaEndpointType base so a stream endpoint and a clip endpoint inherit
# it identically. Both members are inert on a Server that does not implement that
# proposal, and this model deliberately takes NO dependency on it: nothing here
# references its provisional NodeIds, so the Vision NodeSet loads unchanged on a Server
# that has never heard of it.
prop_var(ME, "MediaEndpointType", "DataChannelSource", NodeId_,
         "NodeId of the Object through which this endpoint's bytes can also be obtained "
         "on an OPC UA data channel, per the OPC UA - Data Channels errata proposal. "
         "Non-null means the data channel path is offered IN ADDITION to the endpoint's "
         "out-of-band path; null or absent means out-of-band only. The target is created "
         "by the Server - typically a DataChannelSourceType instance, or any Object "
         "implementing IDataChannelSourceType - and is NOT defined by this "
         "specification. That proposal is a DRAFT: a conformant Server may leave this "
         "null forever. See clause 6.7.")
prop_var(ME, "MediaEndpointType", "DataChannelContentType", String,
         "IANA media type the data channel carries, for example video/H264 or "
         "image/jpeg. Mirrors IDataChannelSourceType.ContentType so a client can learn "
         "the payload type from this model alone, without the Data Channels model being "
         "present. Meaningful only where DataChannelSource is non-null.")


# ===========================================================================
# ==================================  EMIT  =================================
# ===========================================================================
_PRIO = {HasModellingRule: 0, HasSubtype: 0, HasTypeDefinition: 1}


def _sorted_refs(refs):
    return sorted(range(len(refs)), key=lambda i: (_PRIO.get(refs[i][0], 2), i))


def _fmt_reftype(t):
    return REFTYPE_ALIAS.get(t, t)


def _emit_node(n):
    tag = n.cls
    a = [f'{tag} NodeId="{T(n.nid)}"', f'BrowseName="1:{sx.escape(n.bname)}"']
    if n.parent is not None:
        a.append(f'ParentNodeId="{n.parent}"')
    for k in ("DataType", "ValueRank", "ArrayDimensions"):
        if k in n.attrs:
            v = n.attrs[k]
            if k == "DataType":
                v = DATATYPE_ALIAS.get(v, v)
            a.append(f'{k}="{v}"')
    if n.cls == "UAObjectType" and n.abstract:
        a.append('IsAbstract="true"')
    lines = ["  <" + " ".join(a) + ">"]
    lines.append(f"    <DisplayName>{sx.escape(n.display)}</DisplayName>")
    if n.desc:
        lines.append(f"    <Description>{sx.escape(n.desc)}</Description>")
    if n.category:
        lines.append(f"    <Category>{sx.escape(n.category)}</Category>")
    if n.cls == "UAReferenceType" and n.inverse:
        lines.append(f"    <InverseName>{sx.escape(n.inverse)}</InverseName>")
    lines.append("    <References>")
    for i in _sorted_refs(n.refs):
        rt, tgt, fwd = n.refs[i]
        fwd_s = "" if fwd else ' IsForward="false"'
        lines.append(f'      <Reference ReferenceType="{_fmt_reftype(rt)}"{fwd_s}>'
                     f'{tgt}</Reference>')
    lines.append("    </References>")
    if n.definition:
        lines.append("    " + n.definition)
    if n.value:
        lines.append("    " + n.value)
    lines.append(f"  </{tag}>")
    return "\n".join(lines)


def emit():
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<!-- OPC UA - Vision companion model. PROVISIONAL NodeIds and namespace '
           '(final IDs assigned by the OPC Foundation / working group). -->',
           '<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
           'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" '
           'xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
           '  <NamespaceUris>',
           f'    <Uri>{NAMESPACE}</Uri>',
           '  </NamespaceUris>',
           '  <Models>',
           f'    <Model ModelUri="{NAMESPACE}" Version="{VERSION}" '
           f'PublicationDate="{PUBDATE}">',
           f'      <RequiredModel ModelUri="http://opcfoundation.org/UA/" '
           f'Version="{BASE_UA_VERSION}" PublicationDate="{BASE_UA_PUBDATE}" />',
           '    </Model>',
           '  </Models>',
           '  <Aliases>']
    for name, val in ALIASES:
        out.append(f'    <Alias Alias="{name}">{val}</Alias>')
    out.append('  </Aliases>')
    for nid in ORDER:
        out.append(_emit_node(NODES[nid]))
    out.append('</UANodeSet>')
    return "\n".join(out) + "\n"


def emit_csv():
    # OPC Foundation NodeIds.csv format: SymbolicName,NodeId,NodeClass
    return "\n".join(f"{NODES[nid].symbolic},{nid},{NODES[nid].cls[2:]}"
                     for nid in ORDER) + "\n"


def _rule_name(nid):
    for rt, tgt, fwd in NODES[nid].refs:
        if rt == HasModellingRule:
            return {MR_Mandatory: "Mandatory", MR_Optional: "Optional",
                    MR_OptionalPlaceholder: "OptionalPlaceholder",
                    MR_MandatoryPlaceholder: "MandatoryPlaceholder"}.get(tgt, "")
    return ""


def _supertype(nid):
    for rt, tgt, fwd in NODES[nid].refs:
        if rt == HasSubtype and not fwd:
            return tgt
    return ""


BASE_TYPE_NAMES = {
    "i=22": "Structure", "i=29": "Enumeration", "i=58": "BaseObjectType",
    "i=61": "FolderType", "i=68": "PropertyType", "i=63": "BaseDataVariableType",
    "i=17602": "BaseInterfaceType", "i=32": "NonHierarchicalReferences",
    "i=76": "DataTypeEncodingType", "i=24": "BaseDataType",
}


def _dt_name(dt):
    """Render a DataType or supertype NodeId as a readable name."""
    if not dt:
        return ""
    if dt in BASE_TYPE_NAMES:
        return BASE_TYPE_NAMES[dt]
    if dt in DATATYPE_ALIAS:
        return DATATYPE_ALIAS[dt]
    if dt.startswith("ns=1;i="):
        n = NODES.get(int(dt.split("=")[-1]))
        if n is not None:
            return n.bname
    return dt


def _rank(vr):
    return {"-1": "Scalar", "1": "Array"}.get(str(vr), str(vr))


def _members_of(nid):
    """Instance declarations owned by a type, in declaration order."""
    out = []
    for m in ORDER:
        n = NODES[m]
        if n.parent == T(nid) and n.cls in ("UAVariable", "UAObject", "UAMethod"):
            out.append(m)
    return out


def _method_args(nid, which):
    for m in _members_of(nid):
        n = NODES[m]
        if n.bname == which and n.value:
            names = re.findall(r"<uax:Name>([^<]*)</uax:Name>", n.value)
            types = re.findall(r"<uax:Identifier>([^<]*)</uax:Identifier>", n.value)
            types = [t for t in types if t != "i=297"]
            descs = re.findall(r"<uax:Text>([^<]*)</uax:Text>", n.value)
            ranks = re.findall(r"<uax:ValueRank>(-?\d+)</uax:ValueRank>", n.value)
            out = []
            for i, nm in enumerate(names):
                out.append((nm,
                            _dt_name(types[i]) if i < len(types) else "",
                            "Array" if i < len(ranks) and ranks[i] != "-1" else "Scalar",
                            descs[i] if i < len(descs) else ""))
            return out
    return []


def _esc(s):
    return (s or "").replace("|", "\\|")


def emit_md():
    """Annex A. This is the authoritative node reference, so it must carry everything an
    implementer needs: DataType, ValueRank and ModellingRule for every member, the field
    list of every structure, the value of every enumeration literal, and the full
    signature of every Method. A bare NodeId/BrowseName table is not sufficient."""
    obj_types = [n for n in ORDER if NODES[n].cls == "UAObjectType"]
    data_types = [n for n in ORDER if NODES[n].cls == "UADataType"]
    ref_types = [n for n in ORDER if NODES[n].cls == "UAReferenceType"]

    L = ["# OPC UA — Vision — Annex A: Information model (generated)",
         "",
         "> Generated by `build_model.py`. Do not edit by hand. Namespace "
         f"`{NAMESPACE}` (index 1). NodeIds are provisional.",
         "",
         "This annex is the authoritative node reference for the specification: it "
         "carries the DataType, ValueRank and ModellingRule of every member, the field "
         "list of every structure, the value of every enumeration literal, and the full "
         "signature of every Method.",
         ""]

    L += ["## A.1 Type overview", "",
          "| NodeId | BrowseName | NodeClass | Subtype of |", "|---|---|---|---|"]
    for nid in ref_types + obj_types + data_types:
        n = NODES[nid]
        L.append(f"| ns=1;i={nid} | {n.bname} | {n.cls[2:]} | "
                 f"{_dt_name(_supertype(nid))} |")
    L.append("")

    L += ["## A.2 ReferenceTypes", "",
          "| NodeId | BrowseName | InverseName | Subtype of | Description |",
          "|---|---|---|---|---|"]
    for nid in ref_types:
        n = NODES[nid]
        L.append(f"| ns=1;i={nid} | {n.bname} | {n.inverse} | "
                 f"{_dt_name(_supertype(nid))} | {_esc(n.desc)} |")
    L.append("")

    L += ["## A.3 ObjectTypes", ""]
    for nid in obj_types:
        n = NODES[nid]
        abstract = " (abstract)" if n.abstract else ""
        L.append(f"### {n.bname}{abstract} — `ns=1;i={nid}`")
        L.append("")
        L.append(f"*Subtype of:* `{_dt_name(_supertype(nid))}`")
        L.append("")
        if n.desc:
            L.append(_esc(n.desc))
            L.append("")
        members = _members_of(nid)
        variables = [m for m in members if NODES[m].cls in ("UAVariable", "UAObject")]
        methods = [m for m in members if NODES[m].cls == "UAMethod"]
        if variables:
            L.append("| BrowseName | NodeClass | DataType | ValueRank | ModellingRule "
                     "| Description |")
            L.append("|---|---|---|---|---|---|")
            for m in variables:
                mn = NODES[m]
                dt = _dt_name(mn.attrs.get("DataType", ""))
                vr = _rank(mn.attrs.get("ValueRank", "-1")) if mn.cls == "UAVariable" else ""
                L.append(f"| {mn.bname} | {mn.cls[2:]} | {dt} | {vr} | "
                         f"{_rule_name(m)} | {_esc(mn.desc)} |")
            L.append("")
        for m in methods:
            mn = NODES[m]
            L.append(f"**Method `{mn.bname}`** ({_rule_name(m)}) — {_esc(mn.desc)}")
            L.append("")
            for which, label in (("InputArguments", "In"),
                                 ("OutputArguments", "Out")):
                args = _method_args(m, which)
                if not args:
                    continue
                L.append(f"| {label} | DataType | ValueRank | Meaning |")
                L.append("|---|---|---|---|")
                for (an, at, ar, ad) in args:
                    L.append(f"| {an} | {at} | {ar} | {_esc(ad)} |")
                L.append("")
            if not _method_args(m, "InputArguments") and \
                    not _method_args(m, "OutputArguments"):
                L.append("Takes no arguments and returns none.")
                L.append("")

    L += ["## A.4 DataTypes", ""]
    for nid in data_types:
        n = NODES[nid]
        defn = n.definition or ""
        is_enum = 'Value="' in defn
        L.append(f"### {n.bname} — `ns=1;i={nid}`")
        L.append("")
        L.append(f"*Subtype of:* `{_dt_name(_supertype(nid))}`")
        L.append("")
        if n.desc:
            L.append(_esc(n.desc))
            L.append("")
        if is_enum:
            L.append("| Name | Value | Description |")
            L.append("|---|---|---|")
            for mm in re.finditer(
                    r'<Field Name="([^"]+)" Value="(\d+)"\s*(?:/>|>'
                    r'(?:<Description>([^<]*)</Description>)?</Field>)', defn):
                L.append(f"| {mm.group(1)} | {mm.group(2)} | "
                         f"{_esc(mm.group(3) or '')} |")
        else:
            L.append("| Field | DataType | ValueRank | ArrayDimensions | Description |")
            L.append("|---|---|---|---|---|")
            for mm in re.finditer(
                    r'<Field Name="([^"]+)" DataType="([^"]+)"([^>]*?)(?:/>|>'
                    r'(?:<Description>([^<]*)</Description>)?</Field>)', defn):
                extra = mm.group(3) or ""
                vr = re.search(r'ValueRank="(-?\d+)"', extra)
                ad = re.search(r'ArrayDimensions="(\d+)"', extra)
                L.append(f"| {mm.group(1)} | {_dt_name(mm.group(2))} | "
                         f"{_rank(vr.group(1)) if vr else 'Scalar'} | "
                         f"{ad.group(1) if ad else ''} | "
                         f"{_esc(mm.group(4) or '')} |")
        L.append("")

    return "\n".join(L).rstrip() + "\n"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    std = os.path.normpath(os.path.join(
        here, "..", "..", "..", "..",
        "model", "metaverse-specs", "vision"))
    os.makedirs(std, exist_ok=True)
    with open(os.path.join(std, "Opc.Ua.Vision.NodeSet2.xml"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit())
    with open(os.path.join(std, "Opc.Ua.Vision.NodeIds.csv"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit_csv())
    with open(os.path.join(here, "model-reference.md"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit_md())
    n_types = sum(1 for k in NODES
                  if NODES[k].cls in ("UAObjectType", "UADataType", "UAReferenceType"))
    print(f"Wrote NodeSet ({len(ORDER)} nodes, {n_types} types), NodeIds.csv, "
          "model-reference.md")
    print(f"Member id range: 6001..{_next_member[0] - 1}")


# OPC 10000-5 5.2.4: a Server publishes the version and publication date of every namespace it
# hosts as a NamespaceMetadataType Object under Server/Namespaces. Without one a Client -- and
# the specification publisher, which states the same facts in Annex A -- has no way to read them
# from the model, and has to take them from the file it happens to have been handed.
#
# These Nodes are appended last, so adding them cannot renumber anything above.
Server_Namespaces = "i=11715"
NamespaceMetadataType = "i=11616"


def namespace_metadata(uri, version, pubdate, is_subset=False):
    """Declare this model's namespace metadata, as OPC 10000-5 requires."""
    meta = _mid()
    # The BrowseName is the namespace URI in this model's own namespace; the Properties under
    # it are the base ones, so they keep their namespace-0 BrowseNames.
    add(meta, "UAObject", uri, "NamespaceMetadata", display=uri,
        desc="Metadata for this namespace, as OPC 10000-5 requires a Server to publish it.",
        parent=Server_Namespaces)
    ref(meta, HasTypeDefinition, NamespaceMetadataType)
    ref(meta, HasComponent, Server_Namespaces, forward=False)

    def _prop(name, datatype, xml_type, text):
        nid = _mid()
        add(nid, "UAVariable", name, f"NamespaceMetadata_{name}", parent=T(meta),
            attrs={"DataType": datatype, "ValueRank": "-1"})
        ref(nid, HasTypeDefinition, PropertyType)
        ref(nid, HasProperty, T(meta), forward=False)
        ref(meta, HasProperty, T(nid))
        NODES[nid].value = (
            f'<Value><uax:{xml_type}>{sx.escape(text)}</uax:{xml_type}></Value>')
        return nid

    _prop("NamespaceUri", "i=12", "String", uri)
    _prop("NamespaceVersion", "i=12", "String", version)
    _prop("NamespacePublicationDate", "i=13", "DateTime", pubdate)
    _prop("IsNamespaceSubset", "i=1", "Boolean", "true" if is_subset else "false")
    return meta


namespace_metadata(NAMESPACE, VERSION, PUBDATE)


if __name__ == "__main__":
    main()
