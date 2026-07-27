#!/usr/bin/env python3
"""
Generator for the OPC UA Data Channels information model (WG draft errata).

Emits, from a single in-code source of truth:
  * Opc.Ua.DataChannels.NodeSet2.xml  - the information model (UANodeSet)
  * Opc.Ua.DataChannels.NodeIds.csv   - the NodeId assignments
  * tools/model-reference.md          - the generated Annex A (node reference)

This model is an ERRATA OVERLAY on the BASE OPC UA namespace
(http://opcfoundation.org/UA/, namespace index 0), not a companion namespace: the
Part 3 errata adds these types to the core address space model, so every node is
emitted as `i=<n>` with an unqualified BrowseName and the NodeSet declares no
additional NamespaceUri. A tool merges this overlay into the base UA NodeSet.

Draft numeric identifiers are PROVISIONAL and drawn from the 65000+ block (unused
by the other drafts in this repository, which use 60000/62000/63000/64000); final
NodeIds are assigned by the OPC Foundation. Id ranges:

    65000..65099   types (ReferenceType, Interface, ObjectTypes, EventTypes)
    65100..65199   well-known instances
    65930..65999   EnumStrings properties (DataType id + 900)
    66000..        all remaining member declarations, allocated in declaration order
"""
from __future__ import annotations
import os
import re
import xml.sax.saxutils as sx

# ---------------------------------------------------------------------------
# Base NodeIds (base OPC UA namespace)
# ---------------------------------------------------------------------------
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

BaseObjectType = "i=58"
BaseDataVariableType = "i=63"
PropertyType = "i=68"
BaseInterfaceType = "i=17602"
DataTypeEncodingType = "i=76"
NonHierarchicalReferences = "i=32"

BaseEventType = "i=2041"
AuditSessionEventType = "i=2069"
ServerCapabilities = "i=2268"

Boolean = "i=1"
Byte = "i=3"
UInt16 = "i=5"
UInt32 = "i=7"
UInt64 = "i=9"
String = "i=12"
NodeId_ = "i=17"
StatusCode = "i=19"
LocalizedText = "i=21"
Structure = "i=22"
Enumeration = "i=29"
Duration = "i=290"
UtcTime = "i=294"
Argument = "i=296"
KeyValuePair = "i=14533"

# ---------------------------------------------------------------------------
# Node registry
# ---------------------------------------------------------------------------
TYPE_MIN, TYPE_MAX = 65000, 65099
INSTANCE_MIN, INSTANCE_MAX = 65100, 65199
ENUMSTRINGS_MIN = 65900
MEMBER_MIN = 66000


class Node:
    __slots__ = ("nid", "cls", "bname", "symbolic", "display", "desc", "parent",
                 "attrs", "refs", "category", "definition", "value", "abstract",
                 "inverse", "symmetric")

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
        self.symmetric = False


NODES = {}
ORDER = []
_next_member = [MEMBER_MIN]

CAT_REF = "Data Channels Reference Types"
CAT_TYPE = "Data Channels Types"
CAT_EVENT = "Data Channels Event Types"
CAT_DT = "Data Channels Data Types"
CAT_INST = "Data Channels Instances"


def _mid():
    v = _next_member[0]
    _next_member[0] += 1
    return v


def T(nid):
    return f"i={nid}"


def add(nid, cls, bname, symbolic, display=None, desc=None, parent=None,
        attrs=None, category=None, abstract=False):
    if nid in NODES:
        raise ValueError(f"duplicate NodeId i={nid} ({bname})")
    n = Node(nid, cls, bname, symbolic, display, desc, parent, attrs, category, abstract)
    NODES[nid] = n
    ORDER.append(nid)
    return n


def ref(nid, reftype, target, forward=True):
    NODES[nid].refs.append((reftype, target, forward))


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def object_type(nid, name, base, desc, category=CAT_TYPE, abstract=False):
    add(nid, "UAObjectType", name, name, desc=desc, category=category, abstract=abstract)
    ref(nid, HasSubtype, base, forward=False)
    return nid


def interface_type(nid, name, base, desc):
    return object_type(nid, name, base, desc, category=CAT_TYPE, abstract=True)


def event_type(nid, name, base, desc):
    return object_type(nid, name, base, desc, category=CAT_EVENT)


def reference_type(nid, name, base, inverse, desc, abstract=False):
    n = add(nid, "UAReferenceType", name, name, desc=desc, category=CAT_REF, abstract=abstract)
    n.inverse = inverse
    ref(nid, HasSubtype, base, forward=False)
    return nid


def _member_var(owner, owner_sym, name, datatype, typedef, rule, reftype, desc,
                valuerank="-1"):
    nid = _mid()
    attrs = {"DataType": datatype, "ValueRank": valuerank}
    if valuerank == "1":
        attrs["ArrayDimensions"] = "0"
    add(nid, "UAVariable", name, f"{owner_sym}_{name}", desc=desc, parent=T(owner),
        attrs=attrs)
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid


def prop_var(owner, owner_sym, name, datatype, desc, rule=MR_Optional, valuerank="-1"):
    return _member_var(owner, owner_sym, name, datatype, PropertyType, rule,
                       HasProperty, desc, valuerank)


def comp_var(owner, owner_sym, name, datatype, desc, rule=MR_Optional, valuerank="-1"):
    return _member_var(owner, owner_sym, name, datatype, BaseDataVariableType, rule,
                       HasComponent, desc, valuerank)


def enum_type(nid, name, desc, fields):
    add(nid, "UADataType", name, name, desc=desc, category=CAT_DT)
    ref(nid, HasSubtype, Enumeration, forward=False)
    dparts = [f'<Definition Name="{name}">']
    for (fname, val, fdesc) in fields:
        dparts.append(f'<Field Name="{sx.escape(fname)}" Value="{val}">')
        dparts.append(f"<Description>{sx.escape(fdesc)}</Description></Field>")
    dparts.append("</Definition>")
    NODES[nid].definition = "".join(dparts)
    es = nid + 900
    if es < ENUMSTRINGS_MIN:
        raise ValueError(f"EnumStrings id i={es} outside the reserved range")
    ref(nid, HasProperty, T(es))
    add(es, "UAVariable", "EnumStrings", f"{name}_EnumStrings", parent=T(nid),
        attrs={"DataType": LocalizedText, "ValueRank": "1",
               "ArrayDimensions": str(len(fields))})
    ref(es, HasTypeDefinition, PropertyType)
    ref(es, HasProperty, T(nid), forward=False)
    vp = ['<Value>',
          '<ListOfLocalizedText xmlns="http://opcfoundation.org/UA/2008/02/Types.xsd">']
    for (fname, _val, _fdesc) in fields:
        vp.append(f"<LocalizedText><Text>{sx.escape(fname)}</Text></LocalizedText>")
    vp.append("</ListOfLocalizedText></Value>")
    NODES[es].value = "".join(vp)
    return nid


ENCODINGS = (("Default Binary", "DefaultBinary"),
             ("Default XML", "DefaultXml"),
             ("Default JSON", "DefaultJson"))


def struct_type(nid, name, desc, fields):
    add(nid, "UADataType", name, name, desc=desc, category=CAT_DT)
    ref(nid, HasSubtype, Structure, forward=False)
    dparts = [f'<Definition Name="{name}">']
    for (fname, dtype, vrank, fdesc) in fields:
        extra = f' ValueRank="{vrank}"' if vrank is not None else ""
        dparts.append(f'<Field Name="{sx.escape(fname)}" DataType="{dtype}"{extra}>')
        dparts.append(f"<Description>{sx.escape(fdesc)}</Description></Field>")
    dparts.append("</Definition>")
    NODES[nid].definition = "".join(dparts)
    for enc_bname, enc_sym in ENCODINGS:
        enc = _mid()
        add(enc, "UAObject", enc_bname, f"{name}_{enc_sym}", parent=T(nid))
        ref(enc, HasTypeDefinition, DataTypeEncodingType)
        ref(enc, HasEncoding, T(nid), forward=False)
        ref(nid, HasEncoding, T(enc))
    return nid


def well_known(nid, name, typedef, parent, desc, reftype=HasComponent):
    add(nid, "UAObject", name, name, desc=desc, parent=parent, category=CAT_INST)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, parent, forward=False)
    return nid


# ===========================================================================
# ============================  MODEL DEFINITION  ===========================
# ===========================================================================

# --- Reference type --------------------------------------------------------
reference_type(
    65000, "HasDataChannel", NonHierarchicalReferences, "DataChannelOf",
    "Links a functional Object or Variable to the DataChannelSource endpoint through which its "
    "content can be streamed. The source Node is the target of the reference, so a client that "
    "browses a camera, a drive or a log Object finds the data channel it can open without "
    "knowing where the server chose to place the endpoint.")

# --- Interface -------------------------------------------------------------
IDCS = "IDataChannelSourceType"
interface_type(
    65010, IDCS, BaseInterfaceType,
    "Interface implemented by any Object or Variable that can act as one end of a data channel. "
    "Adding this Interface to an existing type through HasInterface is the only change a "
    "companion specification needs in order to become streamable: it does not alter the type's "
    "supertype and does not introduce a new Node Attribute.")

prop_var(65010, IDCS, "Direction", T(65030),
         "The directions in which this endpoint can carry data, from the point of view of the "
         "Server as the source.", rule=MR_Mandatory)
prop_var(65010, IDCS, "SupportedDeliveryModes", T(65031),
         "The delivery modes this endpoint accepts in OpenDataChannel. A mode that is not listed "
         "is rejected with Bad_DeliveryModeUnsupported.", rule=MR_Mandatory, valuerank="1")
prop_var(65010, IDCS, "ContentType", String,
         "The IANA media type of the byte stream this endpoint produces or consumes, for example "
         "video/H264 or application/octet-stream. The data channel layer never interprets the "
         "payload; this Property is what tells an application how to.", rule=MR_Mandatory)
prop_var(65010, IDCS, "ContentParameters", KeyValuePair,
         "Content-specific parameters that qualify ContentType, for example a codec profile, a "
         "sample rate or a frame geometry. Opaque to the data channel layer.", valuerank="1")
prop_var(65010, IDCS, "MaxFrameSize", UInt32,
         "The largest data channel frame payload, in bytes, this endpoint will emit or accept. "
         "The value actually used is additionally bounded by the negotiated transport buffer size "
         "and is returned as revisedParameters.MaxFrameSize by OpenDataChannel.")
prop_var(65010, IDCS, "MaxBitrate", UInt32,
         "The peak rate, in bits per second, this endpoint may produce. A client uses it to decide "
         "whether the connection can carry the stream before opening it.")
prop_var(65010, IDCS, "Priority", Byte,
         "The default scheduling priority (0 lowest, 7 highest) applied to channels opened on "
         "this endpoint when the client requests Priority 255, the no-preference encoding.")
prop_var(65010, IDCS, "MaxChannels", UInt16,
         "The maximum number of data channels that may be open on this endpoint at the same time. "
         "Exceeding it is rejected with Bad_TooManyDataChannels.")
comp_var(65010, IDCS, "ActiveChannelCount", UInt16,
         "The number of data channels currently open on this endpoint, across all Sessions.")

# --- Object types ----------------------------------------------------------
DCS = "DataChannelSourceType"
object_type(
    65011, DCS, BaseObjectType,
    "The plain, concrete realization of IDataChannelSourceType: a stand-alone Object that exists "
    "only to be one end of a data channel. A server uses it where no domain Object is a natural "
    "home for the endpoint; where one is, that Object implements the Interface directly and points "
    "at nothing.")
ref(65011, HasInterface, T(65010))
comp_var(65011, DCS, "Channels", T(65034),
         "The data channels currently open on this endpoint. Empty when none are open.",
         valuerank="1")
comp_var(65011, DCS, "Diagnostics", T(65036),
         "Per-channel counters for the channels currently open on this endpoint.", valuerank="1")

DCC = "DataChannelCapabilitiesType"
object_type(
    65012, DCC, BaseObjectType,
    "Server-wide data channel limits and capabilities, exposed as the DataChannelCapabilities "
    "component of ServerCapabilities. A client reads it once and knows, before it opens anything, "
    "whether the Server supports data channels at all, over which transports, in which delivery "
    "modes and within which limits.")
prop_var(65012, DCC, "MaxDataChannels", UInt16,
         "The maximum number of data channels the Server will keep open on one SecureChannel.",
         rule=MR_Mandatory)
prop_var(65012, DCC, "MaxFrameSize", UInt32,
         "The largest data channel frame payload, in bytes, the Server will emit or accept on any "
         "endpoint, before the transport buffer bound is applied.", rule=MR_Mandatory)
prop_var(65012, DCC, "SupportedDeliveryModes", T(65031),
         "The delivery modes the Server implements. A mode absent here is unsupported everywhere "
         "on this Server.", rule=MR_Mandatory, valuerank="1")
prop_var(65012, DCC, "SupportedTransportProfileUris", String,
         "The TransportProfileUris over which this Server carries data channels, for example the "
         "uatcp-uasc-uabinary and quic-uasc-uabinary profiles.", rule=MR_Mandatory, valuerank="1")
prop_var(65012, DCC, "MaxTotalBitrate", UInt32,
         "The aggregate rate, in bits per second, the Server will emit across all data channels "
         "of one SecureChannel.")
prop_var(65012, DCC, "MaxCreditPerChannel", UInt32,
         "The largest flow control credit window, in bytes, the Server will grant to one channel. "
         "Mandatory because the connection-level credit bootstrap is bounded by this value "
         "multiplied by MaxDataChannels; a Server that omitted it would leave the bound on its "
         "own receive memory undefined.", rule=MR_Mandatory)
prop_var(65012, DCC, "SupportsUnreliableDatagrams", Boolean,
         "True when the Server can carry Unreliable channels over a genuinely lossy path, which "
         "requires a transport that provides one. False on a Server reachable only over opc.tcp "
         "or opc.wss, where Unreliable degrades to sender-side discard.")
comp_var(65012, DCC, "ActiveChannelCount", UInt16,
         "The number of data channels currently open across the whole Server.")

# --- Event types -----------------------------------------------------------
DCO = "DataChannelOfferedEventType"
event_type(
    65020, DCO, BaseEventType,
    "Raised when the Server wants to open a data channel towards a Client. OPC UA Services are "
    "request/response, so the Server cannot call the Client; it offers instead, and the Client "
    "accepts by calling OpenDataChannel with the OfferId. This is what makes server-initiated "
    "media possible without inverting the Service model.")
prop_var(65020, DCO, "Offer", T(65035),
         "The offered channel: its OfferId, its source Node, the parameters the Server proposes "
         "and the time after which the offer lapses.", rule=MR_Mandatory)

DCSC = "DataChannelStateChangeEventType"
event_type(
    65021, DCSC, BaseEventType,
    "Raised whenever a data channel changes state, including the transition to Faulted that "
    "follows a transport level reset. A Client that missed the frame level RESET learns of the "
    "loss here.")
prop_var(65021, DCSC, "ChannelId", UInt32,
         "The data channel whose state changed, unique within its SecureChannel.", rule=MR_Mandatory)
prop_var(65021, DCSC, "State", T(65032), "The state entered.", rule=MR_Mandatory)
prop_var(65021, DCSC, "Status", StatusCode,
         "The StatusCode that caused the transition, for a transition into Closed or Faulted.")

AODC = "AuditOpenDataChannelEventType"
event_type(
    65022, AODC, AuditSessionEventType,
    "Audit event for a successful or rejected OpenDataChannel. A data channel carries application "
    "payload out of the Server outside the Read/Subscribe path, so it is auditable in its own "
    "right rather than folded into the Session audit trail.")
prop_var(65022, AODC, "DataChannelSourceNodeId", NodeId_,
         "The endpoint the channel was requested on.", rule=MR_Mandatory)
prop_var(65022, AODC, "Parameters", T(65033),
         "The parameters as revised by the Server, or as requested when the request was rejected.",
         rule=MR_Mandatory)
prop_var(65022, AODC, "ChannelId", UInt32,
         "The assigned ChannelId. Omitted when the request was rejected.")

# --- Data types ------------------------------------------------------------
enum_type(65030, "DataChannelDirection",
          "The direction in which a data channel carries payload. Directions are named from the "
          "point of view of the data channel source, which is normally the Server.",
          [("SourceToSink", 0, "The source sends and the sink receives, for example a camera feed."),
           ("SinkToSource", 1, "The sink sends and the source receives, for example a firmware push."),
           ("Bidirectional", 2, "Both ends send, over the one ChannelId, for example a two-way audio call.")])

enum_type(65031, "DataChannelDeliveryMode",
          "The delivery guarantee requested for a data channel. What a mode can actually deliver "
          "depends on the transport: only a transport with a lossy path can genuinely drop data in "
          "flight, so over opc.tcp and opc.wss the lossy modes degrade to sender-side discard.",
          [("ReliableOrdered", 0, "Every frame is delivered, in order. The default, and the only mode a purely reliable transport realizes exactly."),
           ("ReliableUnordered", 1, "Every frame is delivered, but the receiver may hand frames to the application as they arrive rather than buffering to restore order."),
           ("PartiallyReliable", 2, "A frame is retried until its deadline passes or MaxRetransmits is reached, then abandoned and reported in a gap notification."),
           ("Unreliable", 3, "A frame is sent once and never retried. Frames still queued when their deadline passes are discarded.")])

enum_type(65032, "DataChannelState",
          "The lifecycle state of a data channel. The normative state transition table - which "
          "event causes which transition, which transitions are legal, and what may be sent in "
          "each state - is clause 5.13 of the Part 6 Data Channel Transport errata. Paused is "
          "maintained per direction.",
          [("Opening", 0, "OpenDataChannel has been accepted and the endpoint is being prepared; no frame may be sent for this ChannelId until the response has been handed to the transport."),
           ("Open", 1, "Payload may flow in the negotiated directions."),
           ("Paused", 2, "The channel is open but the peer's flow control credit is exhausted in this direction, so no payload may be sent. Over opc.quic this is QUIC stream or connection blocking instead."),
           ("Closing", 3, "This peer has decided to close a direction and is draining it. Closing is per direction, like Paused: receiving END marks only the peer's direction ended. No new payload may be enqueued in a Closing direction; frames already queued may still be sent, and END follows the last of them."),
           ("Closed", 4, "The channel is closed, either by END in every direction it carries or by a RESET carrying Good. Its ChannelId is not reassigned while the owning SecureChannel remains open."),
           ("Faulted", 5, "The channel was aborted by a RESET frame carrying a Bad StatusCode, by a timeout, or by loss of the SecureChannel, Session or authorizing user identity.")])

struct_type(65033, "DataChannelParametersDataType",
            "The negotiated properties of one data channel. The same structure carries the "
            "client's request and the server's revision, so a client can compare what it asked "
            "for with what it got in one comparison.",
            [("Direction", T(65030), None, "The direction payload flows in."),
             ("DeliveryMode", T(65031), None, "The delivery guarantee."),
             ("ContentType", String, None, "IANA media type of the payload."),
             ("ContentParameters", KeyValuePair, "1", "Content-specific parameters qualifying ContentType."),
             ("MaxFrameSize", UInt32, None, "Largest frame payload in bytes."),
             ("InitialCredit", UInt32, None, "Flow control credit, in payload bytes, granted to the peer at open."),
             ("Priority", Byte, None, "Scheduling priority, 0 lowest to 7 highest. 255 requests the source's default; other values above 7 are revised to 7."),
             ("MaxRetransmits", UInt16, None, "PartiallyReliable only: attempts before a frame is abandoned. Ignored where the transport is already reliable."),
             ("FrameDeadline", Duration, None, "PartiallyReliable and Unreliable only: how long a frame may wait in the send queue before it is discarded.")])

struct_type(65034, "DataChannelStatusDataType",
            "The runtime state of one open data channel, as published by its endpoint.",
            [("ChannelId", UInt32, None, "Identifier of the channel within its SecureChannel."),
             ("SourceNodeId", NodeId_, None, "The endpoint the channel was opened on."),
             ("State", T(65032), None, "Current lifecycle state."),
             ("Parameters", T(65033), None, "The parameters in force, as revised by the Server."),
             ("TransportChannelId", UInt64, None, "The underlying transport identifier: the QUIC stream id over opc.quic, 0 for inline framing."),
             ("StartTime", UtcTime, None, "When the channel entered the Open state.")])

struct_type(65035, "DataChannelOfferDataType",
            "A server-initiated offer to open a data channel, carried by "
            "DataChannelOfferedEventType and accepted by quoting its OfferId in OpenDataChannel.",
            [("OfferId", UInt32, None, "Identifies the offer. Unique within the SecureChannel until the offer lapses."),
             ("SourceNodeId", NodeId_, None, "The endpoint the Server is offering."),
             ("Parameters", T(65033), None, "The parameters the Server proposes."),
             ("ExpirationTime", UtcTime, None, "After this time the offer lapses and OpenDataChannel returns Bad_DataChannelOfferInvalid.")])

struct_type(65036, "DataChannelDiagnosticsDataType",
            "Per-channel counters. FramesDiscarded and CreditStalls are the two that matter in "
            "practice: the first says the stream is outrunning the link, the second says the "
            "consumer is outrun by the stream.",
            [("ChannelId", UInt32, None, "The channel these counters belong to."),
             ("FramesSent", UInt64, None, "Data frames written to the transport."),
             ("FramesReceived", UInt64, None, "Data frames accepted from the transport."),
             ("BytesSent", UInt64, None, "Payload bytes written, excluding frame headers."),
             ("BytesReceived", UInt64, None, "Payload bytes accepted, excluding frame headers."),
             ("FramesDiscarded", UInt64, None, "Frames dropped before transmission because their deadline passed."),
             ("CreditStalls", UInt32, None, "Times the sender had payload ready but no flow control credit."),
             ("RoundTripTime", Duration, None, "Most recent round trip time measured by PING/PONG."),
             ("LastGapSequenceNumber", UInt32, None, "FrameSequenceNumber of the last frame reported as discarded in a gap notification.")])

# --- Well-known instance ---------------------------------------------------
well_known(65100, "DataChannelCapabilities", T(65012), ServerCapabilities,
           "Server-wide data channel capabilities. Its absence is how a Server says it does not "
           "support data channels at all.")

# ===========================================================================
# ==============================  EMISSION  =================================
# ===========================================================================
NAMESPACE = "http://opcfoundation.org/UA/"
VERSION = "1.05.05-draft"
PUBDATE = "2026-07-27T00:00:00Z"

ALIASES = [
    ("Boolean", Boolean), ("Byte", Byte), ("UInt16", UInt16), ("UInt32", UInt32),
    ("UInt64", UInt64), ("String", String), ("NodeId", NodeId_),
    ("StatusCode", StatusCode), ("LocalizedText", LocalizedText),
    ("Structure", Structure), ("Enumeration", Enumeration), ("Duration", Duration),
    ("UtcTime", UtcTime), ("Argument", Argument), ("KeyValuePair", KeyValuePair),
    ("Organizes", Organizes), ("HasModellingRule", HasModellingRule),
    ("HasEncoding", HasEncoding), ("HasTypeDefinition", HasTypeDefinition),
    ("HasSubtype", HasSubtype), ("HasProperty", HasProperty),
    ("HasComponent", HasComponent), ("HasInterface", HasInterface),
    ("NonHierarchicalReferences", NonHierarchicalReferences),
]
REFTYPE_ALIAS = {v: k for k, v in ALIASES}
DATATYPE_ALIAS = {v: k for k, v in ALIASES}
_PRIO = {HasModellingRule: 0, HasSubtype: 1}


def _sorted_refs(refs):
    return sorted(range(len(refs)), key=lambda i: (_PRIO.get(refs[i][0], 2), i))


def _fmt_reftype(t):
    return REFTYPE_ALIAS.get(t, t)


def _emit_node(n):
    a = [f'{n.cls} NodeId="{T(n.nid)}"', f'BrowseName="{sx.escape(n.bname)}"']
    if n.parent is not None:
        a.append(f'ParentNodeId="{n.parent}"')
    for k in ("DataType", "ValueRank", "ArrayDimensions"):
        if k in n.attrs:
            v = n.attrs[k]
            if k == "DataType":
                v = DATATYPE_ALIAS.get(v, v)
            a.append(f'{k}="{v}"')
    if n.cls in ("UAObjectType", "UAReferenceType") and n.abstract:
        a.append('IsAbstract="true"')
    if n.cls == "UAReferenceType":
        a.append('Symmetric="true"' if n.symmetric else 'Symmetric="false"')
    lines = ["  <" + " ".join(a) + ">"]
    lines.append(f"    <DisplayName>{sx.escape(n.display)}</DisplayName>")
    if n.desc:
        lines.append(f"    <Description>{sx.escape(n.desc)}</Description>")
    if n.category:
        lines.append(f"    <Category>{sx.escape(n.category)}</Category>")
    lines.append("    <References>")
    for i in _sorted_refs(n.refs):
        rt, tgt, fwd = n.refs[i]
        fwd_s = "" if fwd else ' IsForward="false"'
        lines.append(f'      <Reference ReferenceType="{_fmt_reftype(rt)}"{fwd_s}>{tgt}</Reference>')
    lines.append("    </References>")
    if n.cls == "UAReferenceType" and n.inverse and not n.symmetric:
        lines.append(f"    <InverseName>{sx.escape(n.inverse)}</InverseName>")
    if n.definition:
        lines.append("    " + n.definition)
    if n.value:
        lines.append("    " + n.value)
    lines.append(f"  </{n.cls}>")
    return "\n".join(lines)


def emit():
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<!-- OPC UA Data Channels - an ERRATA OVERLAY on the base OPC UA namespace',
           '     (http://opcfoundation.org/UA/). Every node below is a proposed ADDITION to the',
           '     base namespace, so it carries an unqualified BrowseName and an i=<n> NodeId and',
           '     the NodeSet declares no additional NamespaceUri. Merge this overlay into the base',
           '     UA NodeSet; it is not a stand-alone model. PROVISIONAL NodeIds from the 65000+',
           '     block - final identifiers are assigned by the OPC Foundation. -->',
           '<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
           'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" '
           'xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
           '  <NamespaceUris />',
           '  <Models>',
           '    <!-- An overlay on the base namespace has no RequiredModel: naming its own',
           '         ModelUri would be a cycle in the model dependency graph, and a loader that',
           '         topologically sorts by RequiredModel before import would not resolve it. -->',
           f'    <Model ModelUri="{NAMESPACE}" Version="{VERSION}" PublicationDate="{PUBDATE}" />',
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
    return "\n".join(f"{NODES[nid].symbolic},{nid},{NODES[nid].cls[2:]}"
                     for nid in ORDER) + "\n"


# --- Annex A (generated node reference) -------------------------------------
LINK_MAP = {
    "AuditSessionEventType": "https://reference.opcfoundation.org/specs/OPC-10000-5/6.4",
    "BaseDataVariableType": "https://reference.opcfoundation.org/specs/OPC-10000-5/7.4",
    "BaseEventType": "https://reference.opcfoundation.org/specs/OPC-10000-5/6.4",
    "BaseInterfaceType": "https://reference.opcfoundation.org/specs/OPC-10000-5/6.9",
    "BaseObjectType": "https://reference.opcfoundation.org/specs/OPC-10000-5/6.2",
    "Duration": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.13",
    "Enumeration": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.14",
    "KeyValuePair": "https://reference.opcfoundation.org/specs/OPC-10000-5/12.19",
    "NodeId": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.2",
    "NonHierarchicalReferences": "https://reference.opcfoundation.org/specs/OPC-10000-5/11.4",
    "PropertyType": "https://reference.opcfoundation.org/specs/OPC-10000-5/7.3",
    "StatusCode": "https://reference.opcfoundation.org/specs/OPC-10000-4/7.38",
    "Structure": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.32",
    "UtcTime": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.37",
}
_BASE_NAMES = {
    BaseObjectType: "BaseObjectType", BaseDataVariableType: "BaseDataVariableType",
    PropertyType: "PropertyType", BaseInterfaceType: "BaseInterfaceType",
    BaseEventType: "BaseEventType", AuditSessionEventType: "AuditSessionEventType",
    ServerCapabilities: "ServerCapabilities", DataTypeEncodingType: "DataTypeEncodingType",
}
_OWN = None


def _friendly(tgt):
    if tgt in _BASE_NAMES:
        return _BASE_NAMES[tgt]
    if tgt in DATATYPE_ALIAS:
        return DATATYPE_ALIAS[tgt]
    if tgt.startswith("i="):
        tail = tgt[2:]
        if tail.isdigit() and int(tail) in NODES:
            return NODES[int(tail)].bname
    return tgt


def _anchor(name):
    return "type-" + name


def _link(display):
    if not display:
        return display
    arr = ""
    core = display
    if core.endswith("[]"):
        arr = r"\[\]"
        core = core[:-2]
    if core in _OWN:
        return f"[{core}](#{_anchor(core)})" + arr
    if core in LINK_MAP:
        return f"[{core}]({LINK_MAP[core]})" + arr
    return core + arr


def _member_rule(n):
    for rt, tgt, _fwd in n.refs:
        if rt == HasModellingRule:
            return {MR_Mandatory: "Mandatory", MR_Optional: "Optional"}.get(tgt, "")
    return ""


def _supertype(n):
    for rt, tgt, fwd in n.refs:
        if rt == HasSubtype and not fwd:
            return tgt
    return ""


def _members_of(nid):
    out = []
    for rt, tgt, fwd in NODES[nid].refs:
        if rt in (HasComponent, HasProperty, Organizes) and fwd and tgt.startswith("i="):
            num = int(tgt[2:])
            if num in NODES and NODES[num].bname != "EnumStrings":
                out.append(num)
    return out


def _dt_of(mn):
    dt = _friendly(mn.attrs.get("DataType", "")) if mn.attrs.get("DataType") else ""
    if mn.attrs.get("ValueRank", "") == "1" and dt:
        dt += "[]"
    return dt


def emit_md():
    global _OWN
    _OWN = {NODES[nid].bname for nid in ORDER
            if NODES[nid].cls in ("UAObjectType", "UADataType", "UAReferenceType")}
    ref_types = [nid for nid in ORDER if NODES[nid].cls == "UAReferenceType"]
    obj_types = [nid for nid in ORDER
                 if NODES[nid].cls == "UAObjectType" and NODES[nid].category == CAT_TYPE]
    evt_types = [nid for nid in ORDER
                 if NODES[nid].cls == "UAObjectType" and NODES[nid].category == CAT_EVENT]
    data_types = [nid for nid in ORDER if NODES[nid].cls == "UADataType"]

    md = ['<a id="annex-a"></a>', "", "## Annex A — Information model\n",
          "This annex is the normative node reference. It is generated from "
          "`core-specs/data-channels/tools/build_model.py` and always matches "
          "`Opc.Ua.DataChannels.NodeSet2.xml`. Every node is a proposed **addition to the base "
          "OPC UA namespace** `http://opcfoundation.org/UA/` (namespace index 0), so BrowseNames "
          "are unqualified and NodeIds are plain `i=<n>`. The numeric NodeIds are **provisional**, "
          "drawn from the 65000+ block; final identifiers are assigned by the OPC Foundation. The "
          "**Declared in** column marks members inherited from a supertype.\n"]

    md.append("### Type overview\n")
    md.append("| NodeId | BrowseName | NodeClass | Subtype of |")
    md.append("|---|---|---|---|")
    for nid in ref_types + obj_types + evt_types + data_types:
        n = NODES[nid]
        md.append(f"| i={nid} | {_link(n.bname)} | {n.cls[2:]} | "
                  f"{_link(_friendly(_supertype(n)))} |")
    md.append("")

    md.append("### Reference types\n")
    for nid in ref_types:
        n = NODES[nid]
        md.append(f'<a id="{_anchor(n.bname)}"></a>')
        md.append("")
        md.append(f"#### {n.bname}  (i={nid})\n")
        md.append(f"*Subtype of:* {_link(_friendly(_supertype(n)))} · "
                  f"*InverseName:* `{n.inverse}`\n")
        if n.desc:
            md.append(n.desc + "\n")

    def _type_block(nids, heading):
        md.append(f"### {heading}\n")
        for nid in nids:
            n = NODES[nid]
            md.append(f'<a id="{_anchor(n.bname)}"></a>')
            md.append("")
            abstract = " · *abstract*" if n.abstract else ""
            md.append(f"#### {n.bname}  (i={nid}){abstract}\n")
            md.append(f"*Inherits from:* {_link(_friendly(_supertype(n)))}\n")
            ifaces = [t for rt, t, fwd in n.refs if rt == HasInterface and fwd]
            if ifaces:
                md.append("*Implements:* "
                          + ", ".join(_link(_friendly(t)) for t in ifaces) + "\n")
            if n.desc:
                md.append(n.desc + "\n")
            rows = []
            for m in _members_of(nid):
                mn = NODES[m]
                rows.append((mn.bname, mn.cls[2:], _link(_dt_of(mn)), _member_rule(mn),
                             n.bname, (mn.desc or "").replace("|", "/")))
            if rows:
                md.append("| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |")
                md.append("|---|---|---|---|---|---|")
                for r in rows:
                    md.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")
                md.append("")

    _type_block(obj_types, "Object types and interfaces")
    _type_block(evt_types, "Event types")

    md.append("### Data types\n")
    for nid in data_types:
        n = NODES[nid]
        md.append(f'<a id="{_anchor(n.bname)}"></a>')
        md.append("")
        md.append(f"#### {n.bname}  (i={nid})\n")
        md.append(f"*Subtype of:* {_link(_friendly(_supertype(n)))}\n")
        if n.desc:
            md.append(n.desc + "\n")
        if n.definition and "Value=" in n.definition:
            md.append("| Name | Value | Description |")
            md.append("|---|---|---|")
            for mm in re.finditer(
                    r'<Field Name="([^"]+)" Value="(\d+)">'
                    r"<Description>([^<]*)</Description></Field>", n.definition):
                md.append(f"| {mm.group(1)} | {mm.group(2)} | {mm.group(3)} |")
            md.append("")
        elif n.definition:
            md.append("| Field | DataType | Description |")
            md.append("|---|---|---|")
            for mm in re.finditer(
                    r'<Field Name="([^"]+)" DataType="([^"]+)"([^>]*)>'
                    r"<Description>([^<]*)</Description></Field>", n.definition):
                dt = _link(_friendly(mm.group(2)))
                if 'ValueRank="1"' in mm.group(3):
                    dt += r"\[\]"
                md.append(f"| {mm.group(1)} | {dt} | {mm.group(4)} |")
            md.append("")

    md.append("### Well-known instances\n")
    md.append("| BrowseName | NodeId | TypeDefinition | Parent | Note |")
    md.append("|---|---|---|---|---|")
    for nid in ORDER:
        n = NODES[nid]
        if n.category != CAT_INST or n.cls != "UAObject":
            continue
        td = ""
        for rt, tgt, _fwd in n.refs:
            if rt == HasTypeDefinition:
                td = _link(_friendly(tgt))
        md.append(f"| {n.bname} | i={nid} | {td} | {_friendly(n.parent)} "
                  f"({n.parent}) | {(n.desc or '').replace('|', '/')} |")
    md.append("")
    return "\n".join(md).rstrip() + "\n"


BEGIN_MARK = "<!-- BEGIN GENERATED: model-reference -->"
END_MARK = "<!-- END GENERATED: model-reference -->"


def inject(path, rendered):
    """Replace the generated annex between the markers in a specification document."""
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if BEGIN_MARK not in text or END_MARK not in text:
        raise SystemExit(f"model-reference markers not found in {path}")
    start = text.index(BEGIN_MARK) + len(BEGIN_MARK)
    finish = text.index(END_MARK)
    new_text = text[:start] + "\n\n" + rendered + "\n" + text[finish:]
    if new_text != text:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)
    return True


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.abspath(os.path.join(here, ".."))
    with open(os.path.join(outdir, "Opc.Ua.DataChannels.NodeSet2.xml"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit())
    with open(os.path.join(outdir, "Opc.Ua.DataChannels.NodeIds.csv"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit_csv())
    annex = emit_md()
    with open(os.path.join(here, "model-reference.md"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(annex)
    for doc in ("OPC-UA-Part3-Data-Channel-Model.md", "OPC-UA-Data-Channels.md"):
        if inject(os.path.join(outdir, doc), annex):
            print(f"Injected Annex A into {doc}")
    nt = sum(1 for k in NODES
             if NODES[k].cls in ("UAObjectType", "UADataType", "UAReferenceType"))
    print(f"Nodes: {len(NODES)}  (types: {nt})")
    print(f"Member id range: {MEMBER_MIN}..{_next_member[0] - 1}")
