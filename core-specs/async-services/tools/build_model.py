#!/usr/bin/env python3
"""
Generator for the OPC UA Asynchronous Service Execution information model (WG draft errata).

Emits, from a single in-code source of truth:
  * Opc.Ua.AsyncServices.NodeSet2.xml  - the information model (UANodeSet)
  * Opc.Ua.AsyncServices.NodeIds.csv   - the NodeId assignments
  * tools/model-reference.md           - the generated Annex A (node reference)

This model is an ERRATA OVERLAY on the BASE OPC UA namespace
(http://opcfoundation.org/UA/, namespace index 0), not a companion namespace: the
Part 5 errata adds these types to the core information model, so every node is emitted
as `i=<n>` with an unqualified BrowseName and the NodeSet declares no additional
NamespaceUri. A tool merges this overlay into the base UA NodeSet.

Draft numeric identifiers are PROVISIONAL and drawn from the 70000+ block (disjoint from
the 65000..69999 block the Data Channels draft in this repository uses, and from the
60000/62000/63000/64000 blocks the companion-namespace drafts use); final NodeIds are
assigned by the OPC Foundation. Id ranges:

    70000..70099   types (ObjectTypes, EventTypes, DataTypes)
    70100..70199   well-known instances
    70900..70999   EnumStrings properties (DataType id + 900)
    71000..        all remaining member declarations, allocated in declaration order
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
HasEncoding = "i=38"

MR_Mandatory = "i=78"
MR_Optional = "i=80"

BaseObjectType = "i=58"
BaseDataVariableType = "i=63"
PropertyType = "i=68"
DataTypeEncodingType = "i=76"

BaseEventType = "i=2041"
AuditSessionEventType = "i=2069"
ServerCapabilities = "i=2268"
ServerDiagnostics = "i=2274"

Boolean = "i=1"
UInt32 = "i=7"
String = "i=12"
NodeId_ = "i=17"
StatusCode = "i=19"
Structure = "i=22"
DiagnosticInfo = "i=25"
Enumeration = "i=29"
LocalizedText = "i=21"
IntegerId = "i=288"
Counter = "i=289"
Duration = "i=290"
UtcTime = "i=294"
RequestHeader_ = "i=389"
ResponseHeader_ = "i=392"

# ---------------------------------------------------------------------------
# Node registry
# ---------------------------------------------------------------------------
TYPE_MIN, TYPE_MAX = 70000, 70099
INSTANCE_MIN, INSTANCE_MAX = 70100, 70199
ENUMSTRINGS_MIN = 70900
MEMBER_MIN = 71000


class Node:
    __slots__ = ("nid", "cls", "bname", "symbolic", "display", "desc", "parent",
                 "attrs", "refs", "category", "definition", "value", "abstract")

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


NODES = {}
ORDER = []
_next_member = [MEMBER_MIN]

CAT_TYPE = "Async Service Types"
CAT_EVENT = "Async Service Event Types"
CAT_DT = "Async Service Data Types"
CAT_INST = "Async Service Instances"

# ---------------------------------------------------------------------------
# Conformance units
# ---------------------------------------------------------------------------
# OPC 20020 requires each type's definition table to name the conformance units that carry
# it, and a unit has to be an identifier token rather than the prose name used in the
# conformance clause. The CAT_* values above group nodes for generation only; they are not
# conformance units and are never emitted as <Category>.
CU_EXECUTION = "ASE-Execution"
CU_MODEL = "ASE-Model"
CU_DIAGNOSTICS = "ASE-Diagnostics"
CU_EVENTS = "ASE-CompletionEvents"
CU_AUDITING = "ASE-Auditing"

# Every unit, in the order the conformance clause lists them. The documents and this table
# have to agree, or the check that each emitted unit is named in the clause is circular.
ALL_CONFORMANCE_UNITS = (
    CU_EXECUTION, CU_MODEL, CU_DIAGNOSTICS, CU_EVENTS, CU_AUDITING,
)

UNITS_BY_NAME = {
    "AsyncServiceCapabilitiesType": (CU_MODEL,),
    "AsyncServiceDiagnosticsType": (CU_DIAGNOSTICS,),

    "DeferredRequestCompletedEventType": (CU_EVENTS,),
    "AuditDeferredRequestEventType": (CU_AUDITING,),

    "DeferredRequestState": (CU_EXECUTION, CU_DIAGNOSTICS),
    "DeferredRequestTransition": (CU_AUDITING,),
    "DeferralRequestHeaderDataType": (CU_EXECUTION,),
    "DeferralResponseHeaderDataType": (CU_EXECUTION,),
    "DeferredRequestDiagnosticsDataType": (CU_DIAGNOSTICS,),
    "CompleteRequest": (CU_EXECUTION,),
    "CompleteResponse": (CU_EXECUTION,),

    "AsyncServiceCapabilities": (CU_MODEL,),
    "AsyncServiceDiagnostics": (CU_DIAGNOSTICS,),
}

UNITS_BY_CATEGORY = {
    CAT_TYPE: (CU_MODEL,), CAT_EVENT: (CU_EVENTS,), CAT_DT: (CU_MODEL,),
    CAT_INST: (CU_MODEL,),
}


def units_of(n):
    """The conformance units a Node declares, as <Category> elements."""
    if n.bname in UNITS_BY_NAME:
        return UNITS_BY_NAME[n.bname]
    if n.category:
        return UNITS_BY_CATEGORY.get(n.category, ())
    return ()


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


def event_type(nid, name, base, desc):
    return object_type(nid, name, base, desc, category=CAT_EVENT)


def _member_var(owner, owner_sym, name, datatype, typedef, rule, reftype, desc,
                valuerank="-1", access_restrictions=None):
    nid = _mid()
    attrs = {"DataType": datatype, "ValueRank": valuerank}
    if valuerank == "1":
        attrs["ArrayDimensions"] = "0"
    if access_restrictions is not None:
        attrs["AccessRestrictions"] = access_restrictions
    add(nid, "UAVariable", name, f"{owner_sym}_{name}", desc=desc, parent=T(owner),
        attrs=attrs)
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid


def prop_var(owner, owner_sym, name, datatype, desc, rule=MR_Mandatory, valuerank="-1",
             access_restrictions=None):
    return _member_var(owner, owner_sym, name, datatype, PropertyType, rule,
                       HasProperty, desc, valuerank, access_restrictions)


def comp_var(owner, owner_sym, name, datatype, desc, rule=MR_Mandatory, valuerank="-1",
             access_restrictions=None):
    return _member_var(owner, owner_sym, name, datatype, BaseDataVariableType, rule,
                       HasComponent, desc, valuerank, access_restrictions)


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

# --- Object types ----------------------------------------------------------
ASC = "AsyncServiceCapabilitiesType"
object_type(
    70000, ASC, BaseObjectType,
    "Server-wide deferral limits and capabilities, exposed as the AsyncServiceCapabilities "
    "component of ServerCapabilities. Its absence is how a Server says it never defers a "
    "request, so a Client learns that from one Browse rather than from a Bad_RequestNotComplete "
    "it did not expect.")
prop_var(70000, ASC, "MaxDeferredRequests", UInt32,
         "The greatest number of parked responses the Server holds at one time, across every "
         "Session. A request that would take the Server past this number is answered "
         "synchronously or refused with Bad_TooManyDeferredRequests; it is never silently "
         "dropped.")
prop_var(70000, ASC, "MaxDeferredRequestsPerSession", UInt32,
         "The greatest number of parked responses the Server holds for one Session. It bounds "
         "one Session and nothing wider: a Client may open as many Sessions as MaxSessions "
         "allows, so this Property is not by itself a bound on what one user can reserve, and "
         "isolating users from one another is a Server matter this model does not describe.")
prop_var(70000, ASC, "MaxDeferralTime", Duration,
         "The longest a Server holds a parked response before discarding it. It starts when the "
         "request is parked, not when the response becomes ready, so a Client can compute the "
         "deadline from the moment it receives Bad_RequestNotComplete.")
prop_var(70000, ASC, "DefaultRetryAfter", Duration,
         "The interval a Client waits before each Complete when it cannot read the "
         "DeferralResponseHeaderDataType carried in ResponseHeader.additionalHeader. It is "
         "never below MinRetryAfter, so a Client that can read nothing else is never throttled "
         "for obeying the only value available to it. Every Client can read this Property, so "
         "the retry contract does not depend on a header that a stack may discard with the "
         "fault that carries it.")
prop_var(70000, ASC, "MinRetryAfter", Duration,
         "The shortest interval the Server accepts between two Complete calls for the same "
         "parked request. A Client that calls more often is refused with Bad_ServerTooBusy. "
         "Without a published floor, a Client that ignores RetryAfter turns a deferral into a "
         "poll loop against the very Server that deferred because it was busy.")
prop_var(70000, ASC, "DeferrableServices", NodeId_,
         "The DataType NodeIds of the request messages this Server may defer, listed "
         "exhaustively. A Service absent from the list is never deferred, so a Client knows "
         "before it calls whether an answer can arrive late.", valuerank="1")

ASD = "AsyncServiceDiagnosticsType"
object_type(
    70001, ASD, BaseObjectType,
    "Counters and per-request records for deferred requests, exposed as the "
    "AsyncServiceDiagnostics component of ServerDiagnostics. It is what an operator reads to "
    "tell a Server that is slow from a Server whose Clients never collect what they asked for.")
comp_var(70001, ASD, "DeferredRequestCount", UInt32,
         "The number of parked responses the Server currently holds, in any state.")
comp_var(70001, ASD, "TotalDeferredCount", Counter,
         "The number of requests the Server has parked since it started.")
comp_var(70001, ASD, "CompletedCount", Counter,
         "The number of parked responses collected by a Complete since the Server started.")
comp_var(70001, ASD, "ExpiredCount", Counter,
         "The number of parked responses discarded because MaxDeferralTime elapsed before they "
         "were collected. A rising count is the signature of Clients that defer and never "
         "return.")
comp_var(70001, ASD, "CancelledCount", Counter,
         "The number of parked responses abandoned with Cancel since the Server started.")
comp_var(70001, ASD, "RejectedCount", Counter,
         "The number of requests refused with Bad_TooManyDeferredRequests because a parking "
         "limit would have been exceeded.")
comp_var(70001, ASD, "DeferredRequests", T(70034),
         "One record per parked response the reading Session issued. Empty when it holds none. "
         "It names who is running what long operation and when, so it carries the "
         "EncryptionRequired AccessRestriction and is projected per Session.",
         valuerank="1", access_restrictions="2")

# --- Event types -----------------------------------------------------------
DRC = "DeferredRequestCompletedEventType"
event_type(
    70010, DRC, BaseEventType,
    "Raised when a parked response becomes ready to collect. A Client that subscribes to it "
    "calls Complete once, when there is something to collect, instead of polling until there "
    "is; a Client that cannot subscribe is unaffected, because RetryAfter remains the "
    "contract.")
prop_var(70010, DRC, "RequestHandle", IntegerId,
         "The requestHandle of the parked request, as the Client sent it in the RequestHeader. "
         "It is the only identifier the mechanism uses, so a Client keys the Event to its own "
         "outstanding work without holding a Server-assigned ticket.")
prop_var(70010, DRC, "ServiceId", NodeId_,
         "The DataType NodeId of the parked request message, so a Client that deferred several "
         "different Services can tell which one completed.")
prop_var(70010, DRC, "ServiceResult", StatusCode,
         "The service-level serviceResult the parked response carries. For a Service whose "
         "response holds per-operation results it says the request was processed, not that "
         "every operation in it succeeded.")
prop_var(70010, DRC, "CompletionTime", UtcTime,
         "When the response became ready.")
prop_var(70010, DRC, "ExpiryTime", UtcTime,
         "When the Server discards the parked response. A Client has until this time to call "
         "Complete.")

ADR = "AuditDeferredRequestEventType"
event_type(
    70011, ADR, AuditSessionEventType,
    "Audit event for every transition of a parked request. A deferred request separates the "
    "moment an effect is authorized from the moment its outcome is known, and the Client that "
    "authorized it may never collect the answer, so the audit trail is the only record that "
    "spans both. It follows AuditCancelEventType, which is likewise an AuditSessionEventType "
    "carrying a requestHandle. It names the Session and the user behind every parked request, "
    "so it is delivered only to Sessions authorized to audit.")
prop_var(70011, ADR, "RequestHandle", IntegerId,
         "The requestHandle of the request this transition belongs to.")
prop_var(70011, ADR, "ServiceId", NodeId_,
         "The DataType NodeId of the deferred request message.")
prop_var(70011, ADR, "Transition", T(70031),
         "The transition being reported.")
prop_var(70011, ADR, "Outcome", StatusCode,
         "The serviceResult of the parked response for a Delivered transition, and for an "
         "Expired transition whose work had finished. It is the refusing StatusCode for a "
         "Denied transition, and Good_CompletesAsynchronously wherever the outcome is not yet "
         "known: a Deferred transition, and an Expired transition for a request whose work had "
         "not finished. It is the service result, not the audit result: the inherited Status "
         "Property says whether the audited action succeeded, which is a different question "
         "from what the deferred Service returned.")

# --- Data types ------------------------------------------------------------
enum_type(70030, "DeferredRequestState",
          "The state of a parked request. Delivered, Expired and Cancelled are terminal "
          "records rather than live requests: a Server keeps them so that Complete can say "
          "why there is nothing new to collect, and so that a response lost on the network "
          "can be collected again.",
          [("Executing", 0, "The Server is still working on the request. Complete returns Bad_RequestNotComplete."),
           ("Ready", 1, "The response is complete and parked. The next Complete returns it."),
           ("Expired", 2, "The response deadline passed before the response was collected and the Server discarded it. Complete returns Bad_DeferredRequestExpired."),
           ("Cancelled", 3, "The Client abandoned the response with Cancel. Complete returns Bad_RequestCancelledByRequest."),
           ("Delivered", 4, "The response was collected and is retained for replay until the response deadline. A Complete returns the same response again, so a Client that lost it to a broken connection is not left with an effect whose outcome it can never learn.")])

enum_type(70031, "DeferredRequestTransition",
          "The transitions of a parked request, as reported by AuditDeferredRequestEventType. "
          "They are transitions rather than states because Continued and Denied are actions "
          "that leave the state unchanged, and an audit trail that recorded only states would "
          "not show that a Client asked, or that one was turned away.",
          [("Deferred", 0, "The Server parked the request and answered Bad_RequestNotComplete."),
           ("Continued", 1, "A Client called Complete and the response was not yet ready."),
           ("Delivered", 2, "A Client collected the parked response, or collected it again by replay."),
           ("Denied", 3, "A Complete was refused because the calling Session was not the one that parked the request, or because the SecureChannel was too weak to carry the response. It is what makes a campaign of handle probing visible; a call refused by the retry floor is not a Denied transition, because it never examined the request."),
           ("Cancelled", 4, "A Client abandoned the parked response with Cancel."),
           ("Expired", 5, "The Server discarded the parked response because the response deadline passed."),
           ("Completed", 6, "The work finished and its outcome became known. It is raised even when no response is held any longer, which is the only way the outcome of a request that outlived its response deadline reaches the audit trail."),
           ("Discarded", 7, "The Server discarded the parked response before its response deadline because the issuing Session closed, its user identity changed, or the Server shut down.")])

struct_type(70032, "DeferralRequestHeaderDataType",
            "Carried in RequestHeader.additionalHeader, where its presence is how a Client "
            "says it understands deferral. A Server defers only a request that carries it, so "
            "a Client that has never heard of this specification is answered exactly as it is "
            "answered today. Its members are preferences and never preconditions: a request "
            "that carries the structure may still be answered synchronously.",
            [("RequestedDeferralTime", Duration, None, "How long the Client would like the response held. The Server revises it down to MaxDeferralTime and never up. 0 means no preference and selects MaxDeferralTime.")])

struct_type(70033, "DeferralResponseHeaderDataType",
            "Carried in ResponseHeader.additionalHeader of every response that reports a "
            "request as parked. Because a Bad serviceResult travels as a ServiceFault, this "
            "structure is the only place a per-request hint can ride; the Client that cannot "
            "read it falls back on DefaultRetryAfter, which every Client can read.",
            [("RequestHandle", IntegerId, None, "Echo of the requestHandle that identifies the parked request. It is echoed rather than assumed so that a Client whose stack does not surface the RequestHeader it sent can still key the parked request."),
             ("RetryAfter", Duration, None, "How long to wait before the next Complete. Never below MinRetryAfter."),
             ("ExpiryTime", UtcTime, None, "When the Server discards the parked response."),
             ("EstimatedCompletionTime", UtcTime, None, "The Server's estimate of when the response will be ready, or a null DateTime when it cannot estimate. It is a forecast and never a commitment; ExpiryTime is the only deadline that binds.")])

struct_type(70034, "DeferredRequestDiagnosticsDataType",
            "One parked request, as reported by AsyncServiceDiagnostics. CompleteCount and "
            "StartTime are the two that matter in practice: together they separate a Client "
            "that is waiting patiently from one that is polling a Server it was asked not to.",
            [("SessionId", NodeId_, None, "The Session that issued the request."),
             ("RequestHandle", IntegerId, None, "The requestHandle that identifies the parked request within that Session."),
             ("ServiceId", NodeId_, None, "The DataType NodeId of the parked request message."),
             ("State", T(70030), None, "The state of the parked request."),
             ("StartTime", UtcTime, None, "When the Server parked the request."),
             ("ExpiryTime", UtcTime, None, "When the Server discards the parked response."),
             ("CompleteCount", UInt32, None, "How many times a Client has called Complete for this request. A call refused with Bad_ServerTooBusy is not counted, because it never examined the request.")])

# The Service message types. OPC UA models every Service request and response as a
# Structure with the three encodings, so a Service that is not in the model cannot be
# named by DeferrableServices, which identifies a Service by its request message NodeId.
struct_type(70035, "CompleteRequest",
            "The Complete Service request. Its DataType NodeId is what "
            "AsyncServiceCapabilities.DeferrableServices uses to name a Service, and Complete "
            "itself is never deferrable.",
            [("RequestHeader", T(389), None, "Common request parameters."),
             ("RequestHandle", IntegerId, None, "The requestHandle of the parked request, as it appeared in the RequestHeader of the deferred request.")])

struct_type(70036, "CompleteResponse",
            "The Complete Service response, returned when the parked response is itself a "
            "failure. A successful Complete for a parked request that succeeded is answered "
            "with the parked Service's own response message instead; a Complete that fails on "
            "its own account travels as a ServiceFault. This message is what keeps those two "
            "apart, which a bare ServiceFault could not: a parked ApplyChanges that failed and "
            "a Complete that arrived too soon would otherwise be the same message.",
            [("ResponseHeader", T(392), None, "Common response parameters. Its serviceResult is Good: the Complete succeeded, whatever the parked Service returned."),
             ("DeferredServiceResult", StatusCode, None, "The serviceResult of the parked response. Always a Bad StatusCode; a parked response with a Good serviceResult is returned as the parked Service's own response message."),
             ("DeferredDiagnosticInfo", T(25), None, "The serviceDiagnostics the parked response carried, whose string table is the ResponseHeader's.")])

# --- Well-known instances --------------------------------------------------
well_known(70100, "AsyncServiceCapabilities", T(70000), ServerCapabilities,
           "Server-wide deferral capabilities. Its absence is how a Server says it never "
           "defers a request.")
well_known(70101, "AsyncServiceDiagnostics", T(70001), ServerDiagnostics,
           "Deferred request counters and the per-request records of the reading Session.")

# ===========================================================================
# ==============================  EMISSION  =================================
# ===========================================================================
NAMESPACE = "http://opcfoundation.org/UA/"
VERSION = "1.05.05-draft"
PUBDATE = "2026-08-03T00:00:00Z"

ALIASES = [
    ("Boolean", Boolean), ("UInt32", UInt32), ("String", String), ("NodeId", NodeId_),
    ("StatusCode", StatusCode), ("LocalizedText", LocalizedText),
    ("Structure", Structure), ("DiagnosticInfo", DiagnosticInfo),
    ("Enumeration", Enumeration), ("IntegerId", IntegerId),
    ("Counter", Counter), ("Duration", Duration), ("UtcTime", UtcTime),
    ("RequestHeader", RequestHeader_), ("ResponseHeader", ResponseHeader_),
    ("Organizes", Organizes), ("HasModellingRule", HasModellingRule),
    ("HasEncoding", HasEncoding), ("HasTypeDefinition", HasTypeDefinition),
    ("HasSubtype", HasSubtype), ("HasProperty", HasProperty),
    ("HasComponent", HasComponent),
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
    for k in ("DataType", "ValueRank", "ArrayDimensions", "AccessRestrictions"):
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
    for unit in units_of(n):
        lines.append(f"    <Category>{sx.escape(unit)}</Category>")
    lines.append("    <References>")
    for i in _sorted_refs(n.refs):
        rt, tgt, fwd = n.refs[i]
        fwd_s = "" if fwd else ' IsForward="false"'
        lines.append(f'      <Reference ReferenceType="{_fmt_reftype(rt)}"{fwd_s}>{tgt}</Reference>')
    lines.append("    </References>")
    if n.definition:
        lines.append("    " + n.definition)
    if n.value:
        lines.append("    " + n.value)
    lines.append(f"  </{n.cls}>")
    return "\n".join(lines)


def emit():
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<!-- OPC UA Asynchronous Service Execution - an ERRATA OVERLAY on the base OPC UA',
           '     namespace (http://opcfoundation.org/UA/). Every node below is a proposed ADDITION',
           '     to the base namespace, so it carries an unqualified BrowseName and an i=<n> NodeId',
           '     and the NodeSet declares no additional NamespaceUri. Merge this overlay into the',
           '     base UA NodeSet; it is not a stand-alone model. PROVISIONAL NodeIds from the',
           '     70000+ block - final identifiers are assigned by the OPC Foundation. -->',
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
    "BaseObjectType": "https://reference.opcfoundation.org/specs/OPC-10000-5/6.2",
    "Counter": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.11",
    "DiagnosticInfo": "https://reference.opcfoundation.org/specs/OPC-10000-4/7.8",
    "Duration": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.13",
    "Enumeration": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.14",
    "IntegerId": "https://reference.opcfoundation.org/specs/OPC-10000-4/7.19",
    "NodeId": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.2",
    "PropertyType": "https://reference.opcfoundation.org/specs/OPC-10000-5/7.3",
    "RequestHeader": "https://reference.opcfoundation.org/specs/OPC-10000-4/7.32",
    "ResponseHeader": "https://reference.opcfoundation.org/specs/OPC-10000-4/7.33",
    "StatusCode": "https://reference.opcfoundation.org/specs/OPC-10000-4/7.38",
    "Structure": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.32",
    "UtcTime": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.37",
}
_BASE_NAMES = {
    BaseObjectType: "BaseObjectType", BaseDataVariableType: "BaseDataVariableType",
    PropertyType: "PropertyType", BaseEventType: "BaseEventType",
    AuditSessionEventType: "AuditSessionEventType",
    ServerCapabilities: "ServerCapabilities", ServerDiagnostics: "ServerDiagnostics",
    DataTypeEncodingType: "DataTypeEncodingType",
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
            if NODES[nid].cls in ("UAObjectType", "UADataType")}
    obj_types = [nid for nid in ORDER
                 if NODES[nid].cls == "UAObjectType" and NODES[nid].category == CAT_TYPE]
    evt_types = [nid for nid in ORDER
                 if NODES[nid].cls == "UAObjectType" and NODES[nid].category == CAT_EVENT]
    data_types = [nid for nid in ORDER if NODES[nid].cls == "UADataType"]

    md = ['<a id="annex-a"></a>', "", "## Annex A — Information model\n",
          "This annex is the normative node reference. It is generated from "
          "`core-specs/async-services/tools/build_model.py` and always matches "
          "`Opc.Ua.AsyncServices.NodeSet2.xml`. Every node is a proposed **addition to the base "
          "OPC UA namespace** `http://opcfoundation.org/UA/` (namespace index 0), so BrowseNames "
          "are unqualified and NodeIds are plain `i=<n>`. The numeric NodeIds are **provisional**, "
          "drawn from the 70000+ block; final identifiers are assigned by the OPC Foundation. The "
          "**Declared in** column marks members inherited from a supertype.\n"]

    md.append("### Type overview\n")
    md.append("| NodeId | BrowseName | NodeClass | Subtype of |")
    md.append("|---|---|---|---|")
    for nid in obj_types + evt_types + data_types:
        n = NODES[nid]
        md.append(f"| i={nid} | {_link(n.bname)} | {n.cls[2:]} | "
                  f"{_link(_friendly(_supertype(n)))} |")
    md.append("")

    def _type_block(nids, heading):
        md.append(f"### {heading}\n")
        for nid in nids:
            n = NODES[nid]
            md.append(f'<a id="{_anchor(n.bname)}"></a>')
            md.append("")
            abstract = " · *abstract*" if n.abstract else ""
            md.append(f"#### {n.bname}  (i={nid}){abstract}\n")
            md.append(f"*Inherits from:* {_link(_friendly(_supertype(n)))}\n")
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

    _type_block(obj_types, "Object types")
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
    with open(os.path.join(outdir, "Opc.Ua.AsyncServices.NodeSet2.xml"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit())
    with open(os.path.join(outdir, "Opc.Ua.AsyncServices.NodeIds.csv"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit_csv())
    annex = emit_md()
    with open(os.path.join(here, "model-reference.md"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(annex)
    for doc in ("OPC-UA-Part5-Async-Service-Model.md", "OPC-UA-Async-Services.md"):
        if inject(os.path.join(outdir, doc), annex):
            print(f"Injected Annex A into {doc}")
    nt = sum(1 for k in NODES if NODES[k].cls in ("UAObjectType", "UADataType"))
    print(f"Nodes: {len(NODES)}  (types: {nt})")
    print(f"Member id range: {MEMBER_MIN}..{_next_member[0] - 1}")
