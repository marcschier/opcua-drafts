#!/usr/bin/env python3
"""
Generator for the OPC UA - AI Model Management and Inference companion specification.

Emits, from a single in-code source of truth:
  * ../../../ai-model-management/Opc.Ua.AiModelManagement.NodeSet2.xml - the model
  * ../../../ai-model-management/Opc.Ua.AiModelManagement.NodeIds.csv - the NodeIds
  * model-reference.md                                      - the generated Annex A

The model is a COMPANION specification in its OWN namespace
(http://opcfoundation.org/UA/AI/). Its namespace index is DERIVED from NAMESPACE_URIS
and is not 1: the xRegistry RequiredModel occupies index 1. Nodes use ns={OWN_NS} for
both NodeIds and BrowseNames; references to base UA types use plain `i=<n>`.

It is deliberately STANDALONE and deliberately DOMAIN-NEUTRAL: the only
<RequiredModel> is the base UA namespace, and nothing here mentions a camera, a robot
or any other kind of equipment. A model is trained on a dataset, deployed somewhere,
and replaced by a better one; that story is the same whether the input is an image, a
vibration spectrum or a process trace.

NodeIds are PROVISIONAL (final IDs assigned by the OPC Foundation) and follow the repo
convention: ObjectTypes/Interfaces 1001+, Enumerations 3001+ (EnumStrings = enum + 900),
Structures 3050+, ReferenceTypes 4001+, DataType encodings 5001+, well-known instances
7001+, and all remaining instance declarations sequentially from 6001. New members must
be APPENDED so that previously published member NodeIds stay stable.

Design notes:
  * The model is domain-neutral by construction: nothing here names a camera, a robot
    or a sensor, and validate_local.py fails the build if a type name acquires one.
  * A consuming specification binds to this one through a NodeId Property, not a
    reference and not a RequiredModel, so a Server can implement either alone.
  * Digest and DigestAlgorithm are Mandatory because the provenance chain from a
    published result back to the model artefact is the only reason several of the
    other members are worth reading at all.
"""
from __future__ import annotations
import os
import re
import xml.sax.saxutils as sx

NAMESPACE = "http://opcfoundation.org/UA/AI/"
VERSION = "0.6.0"
PUBDATE = "2026-08-31T00:00:00Z"
BASE_UA_VERSION = "1.05.04"
BASE_UA_PUBDATE = "2023-12-15T00:00:00Z"

# The model catalogue is a domain extension of OPC UA - xRegistry, so that a model
# registry is the same shape as every other registry in this repository rather than a
# private invention. See clause 10.
XREG_NS = "http://opcfoundation.org/UA/xRegistry/"
XREG_VERSION = "0.4.0"
XREG_PUBDATE = "2026-08-31T00:00:00Z"

# NamespaceUris order fixes the namespace indices for the whole file. Required-model
# namespaces come first and the own namespace last, matching the Schema Registry
# precedent. Both indices are DERIVED from this list - a hardcoded ns=N would not merely
# go stale when a dependency is added, it would start pointing into a different model.
NAMESPACE_URIS = [XREG_NS, NAMESPACE]
OWN_NS = NAMESPACE_URIS.index(NAMESPACE) + 1
XREG_IDX = NAMESPACE_URIS.index(XREG_NS) + 1

# --- base UA NodeIds (namespace 0) -----------------------------------------
HasComponent = "i=47"
HasProperty = "i=46"
HasSubtype = "i=45"
Organizes = "i=35"
HasTypeDefinition = "i=40"
HasModellingRule = "i=37"
HasInterface = "i=17603"
HasEncoding = "i=38"
# Event plumbing. HasNotifier builds the notifier hierarchy a client walks to find what
# it can subscribe to; without it an EventType is declared but unreachable, because a
# Subscription is created against a node whose EventNotifier says it emits events.
HasNotifier = "i=48"
HasEventSource = "i=36"
EVENTNOTIFIER_SUBSCRIBE = "1"
BaseEventType = "i=2041"

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
KeyValuePair = "i=14533"

Server = "i=2253"

# OPC 10000-10 Programs. A long-running AI job is a program instance, which is how
# Robot Intent models its intents; the transition events and the auditability that a
# hand-rolled state variable would have to reinvent come with the base type.
ProgramStateMachineType = "i=2391"

# OPC 10000-5 FileType. A large inference payload is a file in every respect that
# matters - it is opened, written or read in bounded chunks, and closed.
FileType = "i=11575"

Float = "i=10"
Int64 = "i=8"
DateTime = "i=13"

ALIASES = [
    ("Boolean", Boolean), ("Int32", Int32), ("UInt32", UInt32), ("UInt64", UInt64),
    ("Double", Double), ("String", String), ("Guid", Guid), ("ByteString", ByteString),
    ("Float", Float), ("Int64", Int64), ("DateTime", DateTime),
    ("NodeId", NodeId_), ("QualifiedName", QualifiedName), ("LocalizedText", LocalizedText),
    ("UtcTime", UtcTime), ("Duration", Duration), ("Argument", Argument),
    ("EUInformation", EUInformation), ("KeyValuePair", KeyValuePair),
    ("BaseDataType", BaseDataType),
    ("HasComponent", HasComponent), ("HasProperty", HasProperty),
    ("HasSubtype", HasSubtype), ("Organizes", Organizes),
    ("HasTypeDefinition", HasTypeDefinition), ("HasModellingRule", HasModellingRule),
    ("HasInterface", HasInterface), ("HasEncoding", HasEncoding),
    ("HasNotifier", HasNotifier), ("HasEventSource", HasEventSource),
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
    """Own-namespace NodeId. The index is derived, never assumed."""
    return f"ns={OWN_NS};i={nid}"


def X(nid):
    """A NodeId in the xRegistry namespace this model extends."""
    return f"ns={XREG_IDX};i={nid}"


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


def event_type(nid, name, base, desc, abstract=False):
    """An EventType. Its members are Properties, exactly as OPC 10000-5 declares the
    fields of BaseEventType, so a client selects them with a SimpleAttributeOperand and
    the Server can filter on them before it sends anything."""
    add(nid, "UAObjectType", name, name, desc=desc, category=CAT_EV, abstract=abstract)
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
    """Emit an InputArguments / OutputArguments Property for a Method.

    BrowseNameNamespace 0: InputArguments and OutputArguments are standard Properties
    defined by OPC 10000-3 / 10000-5 and live in namespace 0. A stack resolves a
    Method's signature by looking for the child Property named InputArguments IN
    NAMESPACE 0; qualified into the model namespace it is not found, the Method is
    treated as taking zero arguments, and every real call is rejected with
    Bad_TooManyArguments. Setting the flag here fixes every Method of this model,
    including ones added later.
    """
    nid = _mid()
    add(nid, "UAVariable", bname, f"{method_sym}_{bname}", parent=T(method_nid),
        attrs={"DataType": Argument, "ValueRank": "1",
               "ArrayDimensions": str(len(args)), "BrowseNameNamespace": 0})
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
    # EnumStrings is a standard Property of an enumeration DataType (OPC 10000-3) and
    # lives in namespace 0, exactly like the Method argument Properties above.
    add(es, "UAVariable", "EnumStrings", f"{name}_EnumStrings", parent=T(nid),
        attrs={"DataType": LocalizedText, "ValueRank": "1",
               "ArrayDimensions": str(len(fields)), "BrowseNameNamespace": 0})
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


ABSTRACT_STRUCTS = set()


def struct_type(nid, name, desc, fields, base=Structure, abstract=False):
    """A Structure DataType plus, unless it is abstract, its Default Binary encoding.

    fields: list of (FieldName, DataType, Description[, ValueRank[, ArrayDimensions]])
            ArrayDimensions 0 means "any length" and is omitted from the emitted
            Definition, matching how the base UA NodeSet writes unbounded arrays.
    base:   the DataType this one extends. A subtype's Definition lists only the
            fields it ADDS - the inherited ones are reached through HasSubtype, which
            is how the base UA NodeSet does it.
    abstract: an abstract structure gets no encoding, because nothing is ever encoded
            as one; values are always of a concrete subtype.

    A field whose DataType is an abstract structure declared here is emitted with
    AllowSubTypes="true", so polymorphic members are self-describing rather than
    relying on the reader to notice the DataType is abstract.
    """
    add(nid, "UADataType", name, name, desc=desc, category=CAT_DT, abstract=abstract)
    ref(nid, HasSubtype, base, forward=False)
    if abstract:
        ABSTRACT_STRUCTS.add(T(nid))
    dparts = [f'<Definition Name="{name}">']
    for f in fields:
        fname, fdtype, fdesc = f[0], f[1], f[2]
        frank = f[3] if len(f) > 3 else None
        fdims = f[4] if len(f) > 4 else None
        a = [f'Name="{sx.escape(fname)}"', f'DataType="{fdtype}"']
        if frank is not None:
            a.append(f'ValueRank="{frank}"')
        if fdims:
            a.append(f'ArrayDimensions="{fdims}"')
        if fdtype in ABSTRACT_STRUCTS:
            a.append('AllowSubTypes="true"')
        attr = " ".join(a)
        if fdesc:
            dparts.append(f'<Field {attr}>')
            dparts.append(f'<Description>{sx.escape(fdesc)}</Description></Field>')
        else:
            dparts.append(f'<Field {attr}/>')
    dparts.append("</Definition>")
    NODES[nid].definition = "".join(dparts)
    if abstract:
        return nid
    enc = _next_encoding[0]
    _next_encoding[0] += 1
    ref(nid, HasEncoding, T(enc))
    add(enc, "UAObject", "Default Binary", f"{name}_Encoding_DefaultBinary",
        desc="Default Binary encoding of the structure.",
        attrs={"BrowseNameNamespace": 0, "SymbolicName": "DefaultBinary"})
    ref(enc, HasTypeDefinition, DataTypeEncodingType)
    ref(enc, HasEncoding, T(nid), forward=False)
    return nid


def well_known(nid, name, typedef, parent_nodeid, desc, reftype=HasComponent,
               event_notifier=None):
    attrs = {"EventNotifier": event_notifier} if event_notifier else None
    add(nid, "UAObject", name, name, desc=desc, parent=parent_nodeid, attrs=attrs)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, parent_nodeid, forward=False)
    if event_notifier:
        # Server HasNotifier this object, so a client subscribing at the Server object
        # receives what is raised here without knowing this node exists.
        ref(nid, HasNotifier, parent_nodeid, forward=False)
    return nid



# ===========================================================================
# ==============================  MODEL DEFINITION  =========================
# ===========================================================================
CAT = "AiModelManagement"
CAT_DT = "AiModelManagement DataTypes"
CAT_RT = "AiModelManagement ReferenceTypes"
CAT_EV = "AiModelManagement Events"

# ---------------------------------------------------------------------------
# Enumerations (3001+)
# ---------------------------------------------------------------------------
enum_type(3001, "InferenceLocationEnum",
          "Where inference executes. The result contract is identical in every case; "
          "this property exists so a client can reason about latency, availability and "
          "the trust boundary without changing how it reads results.",
          [("OnServer", 0, "In the OPC UA Server process or on its host."),
           ("EdgeOffServer", 1, "On a separate edge node reached over the network."),
           ("Cloud", 2, "In a remote or cloud service."),
           ("InSimulator", 3, "Inside a simulator that also produces the input.")])
InferenceLocationEnum = T(3001)

enum_type(3002, "AcceleratorKindEnum",
          "Compute device executing the model.",
          [("Cpu", 0, None), ("Gpu", 1, None), ("Npu", 2, None), ("Fpga", 3, None),
           ("Tpu", 4, None), ("Other", 5, None)])
AcceleratorKindEnum = T(3002)

enum_type(3003, "DeploymentStateEnum",
          "Runtime lifecycle state of a deployment.",
          [("Inactive", 0, "Declared but not serving."),
           ("Ready", 1, "Able to serve; no work in progress."),
           ("Active", 2, "Serving at least one request."),
           ("Degraded", 3, "Serving below configured quality."),
           ("Faulted", 4, "Unable to serve.")])
DeploymentStateEnum = T(3003)

enum_type(3004, "DatasetSourceEnum",
          "Provenance of the samples in a dataset.",
          [("Real", 0, "Captured from physical equipment."),
           ("Synthetic", 1, "Generated or rendered by a simulator."),
           ("Mixed", 2, "Both, for example synthetic pre-training with real "
                        "fine-tuning.")])
DatasetSourceEnum = T(3004)

enum_type(3005, "LearningJobStateEnum",
          "State of a dataset-capture, retraining and promotion cycle.",
          [("Idle", 0, None), ("Collecting", 1, None), ("Labelling", 2, None),
           ("Training", 3, None), ("Validating", 4, None),
           ("Ready", 5, "A candidate model is available for promotion."),
           ("Promoted", 6, None), ("Failed", 7, None)])
LearningJobStateEnum = T(3005)

enum_type(3006, "FinishReasonEnum",
          "Why an inference call stopped producing output. A client that treats every "
          "non-error response as complete will silently accept a truncated one, which "
          "is why this is Mandatory on a response rather than a diagnostic.",
          [("Stop", 0, "The model finished normally."),
           ("Length", 1, "Output was truncated by a length or budget limit. The "
                         "result is incomplete and SHALL NOT be treated as final."),
           ("ToolCall", 2, "The model requested a tool or function call and is "
                           "waiting for its result."),
           ("Filtered", 3, "Output was withheld by a safety policy; see the "
                           "SafetyAssessment."),
           ("Cancelled", 4, "The caller or the Server cancelled the call."),
           ("Error", 5, "The call failed; the StatusCode carries the reason.")])
FinishReasonEnum = T(3006)

enum_type(3007, "ApiDialectEnum",
          "Wire contract a remote inference endpoint speaks. A Server needs this to "
          "call an endpoint it did not deploy; without it EndpointUri is a string "
          "nobody can act on. It describes the REMOTE endpoint and never affects how "
          "an OPC UA client calls this Server.",
          [("OpcUaInference", 0, "Another OPC UA Server implementing this "
                                 "specification's Invoke Method."),
           ("RestChatCompletions", 1, "The de-facto REST contract for chat and "
                                      "embeddings that most serving runtimes expose, "
                                      "including ones that run on a single "
                                      "workstation."),
           ("OpenInferenceProtocol", 2, "The Open Inference Protocol (KServe v2) "
                                        "predict contract."),
           ("TensorRemoteProcedure", 3, "A tensor-oriented RPC contract such as those "
                                        "used by dedicated inference servers."),
           ("EmbeddedRuntime", 4, "An in-process runtime reached through a local "
                                  "library rather than a network protocol."),
           ("Proprietary", 5, "A contract this specification does not name. "
                              "EndpointDescriptionUri SHOULD then say where it is "
                              "documented.")])
ApiDialectEnum = T(3007)

enum_type(3008, "AuthenticationKindEnum",
          "How the Server authenticates ITSELF to a remote inference endpoint. This is "
          "not how a client authenticates to this Server, which is the ordinary OPC UA "
          "Session security and is unaffected.",
          [("Anonymous", 0, "No credential. Permitted only where the endpoint is "
                            "reachable solely from a trusted network segment."),
           ("ApiKey", 1, "A shared secret presented as a key."),
           ("BearerToken", 2, "A token obtained from an authorization service."),
           ("WorkloadIdentity", 3, "An identity the hosting platform assigns to the "
                                   "Server, so no secret is stored at all. Preferred "
                                   "where the platform offers it."),
           ("MutualTls", 4, "Both ends present certificates.")])
AuthenticationKindEnum = T(3008)

enum_type(3009, "FallbackPolicyEnum",
          "What the Server does when a deployment cannot serve. This is the question a "
          "plant asks that no cloud inference API answers, because a cloud API assumes "
          "the caller can simply wait.",
          [("Fail", 0, "Report the failure to the caller and produce nothing. The "
                       "safe default: a caller that is told nothing happened can "
                       "decide for itself."),
           ("HoldLast", 1, "Continue reporting the most recent successful result, "
                           "marked stale. Legitimate only where a stale answer is "
                           "safe, and the caller SHALL be able to see the staleness."),
           ("FallBackTo", 2, "Route to the deployment named by the FallsBackTo "
                             "reference. The answer comes from a different model and "
                             "the response SHALL say so.")])
FallbackPolicyEnum = T(3009)

enum_type(3010, "VersionBindingEnum",
          "Whether a deployment is bound to one immutable model version or follows a "
          "moving pointer. Stated structurally rather than as an upgrade policy, "
          "because what a client needs to know is whether the artefact can change "
          "under it, not what schedule someone intends to change it on.",
          [("Pinned", 0, "Bound to one immutable version. The artefact behind this "
                         "deployment cannot change without an observable change to "
                         "the deployment."),
           ("FollowsRef", 1, "Bound to a mutable pointer such as a branch or channel. "
                             "The artefact CAN change without any other change, which "
                             "is why clause 12 requires the resulting promotion to be "
                             "as authorized as an explicit one.")])
VersionBindingEnum = T(3010)

enum_type(3011, "ImportModeEnum",
          "Whether an import job brings the model's description or its bytes.",
          [("Federate", 0, "Materialize the catalogue entry as a ModelType and leave "
                           "the artefact where it is. Nothing is downloaded and "
                           "inference runs at the source."),
           ("Stage", 1, "Fetch the artefact, verify its Digest, and make it locally "
                        "available so inference can run without the source."),
           ("Auto", 2, "Federate, then stage if the target deployment's "
                       "InferenceLocation is OnServer or EdgeOffServer - because "
                       "those cannot reach the source at inference time.")])
ImportModeEnum = T(3011)

enum_type(3012, "SafetySeverityEnum",
          "Severity of one safety finding. The scale is the convergent industry one; "
          "what each level means for a given category is the policy's business, not "
          "this specification's.",
          [("None", 0, None), ("Low", 1, None), ("Medium", 2, None),
           ("High", 3, None)])
SafetySeverityEnum = T(3012)

enum_type(3013, "ReachabilityEnum",
          "Whether the Server can currently reach a deployment's execution site.",
          [("Unknown", 0, "Never attempted, or the Server does not probe."),
           ("Reachable", 1, "The most recent attempt succeeded."),
           ("Unreachable", 2, "The most recent attempt failed."),
           ("Throttled", 3, "Reachable, but the endpoint is refusing work for "
                            "capacity reasons. RetryAfter SHOULD be populated.")])
ReachabilityEnum = T(3013)

enum_type(3014, "TransferStateEnum",
          "Stage of a chunked inference exchange. A client reads this rather than "
          "inferring progress from which Methods have succeeded, because a transfer "
          "that failed mid-write and one that has not started look alike from "
          "outside.",
          [("Building", 0, "The request is being written and is not yet complete."),
           ("Ready", 1, "The request is complete and inference has not started."),
           ("Executing", 2, "Inference is running."),
           ("Completed", 3, "The response is readable."),
           ("Failed", 4, "The exchange failed; LastError carries the reason."),
           ("Expired", 5, "The Server reclaimed the transfer before it completed.")])
TransferStateEnum = T(3014)

enum_type(3015, "DigestProvenanceEnum",
          "Where a Digest came from, or why there is none. Digest is Mandatory so "
          "that its absence is uniform and browsable rather than indistinguishable "
          "from a Server that does not implement digests - but 'empty' then carries "
          "two different meanings, and a client that must decide whether to trust an "
          "artefact needs them apart. This member is what tells them apart, and it "
          "does the same job for a digest that IS present: a value the source "
          "asserted and a value this Server computed over bytes are not the same "
          "evidence, and only one of them survives a substituted artefact.",
          [("NotAvailable", 0,
            "There is no digest and the source does not publish one. Digest is "
            "empty. This is the honest answer for an endpoint that names models but "
            "never their content, and it is what most hosted inference APIs "
            "require."),
           ("DeclaredBySource", 1,
            "Digest carries what the source declared. No party this Server can "
            "speak for has hashed the artefact, so the value is an assertion "
            "forwarded rather than evidence held."),
           ("ComputedByServer", 2,
            "This Server hashed the artefact it holds. The value is evidence, but "
            "nothing independent agrees with it - a substitution that happened "
            "before the Server obtained the bytes is not detected."),
           ("VerifiedOnStage", 3,
            "This Server hashed the artefact during a staging import (clause 10.4) "
            "and it matched what the source declared. Two independent parties agree, "
            "which is the strongest statement this model can carry.")])
DigestProvenanceEnum = T(3015)

enum_type(3016, "ModelChangeKindEnum",
          "The trigger that caused a deployment's UsesModel reference to be "
          "substituted. Classification is by the administrative trigger, never by "
          "comparing model versions: version strings are not necessarily ordered and "
          "a rollback can target a version whose spelling sorts later.",
          [("Promotion", 0, "An approved candidate replaced the serving model."),
           ("Rollback", 1, "An operator or policy restored a previously used model."),
           ("AutomaticSubstitution", 2,
            "The Server changed the deployment's configured UsesModel target "
            "automatically. Per-invocation fallback that leaves UsesModel unchanged "
            "is not this value and creates no promotion record."),
           ("MutableReferenceRepoint", 3,
            "A followed mutable reference resolved to a different model."),
           ("OtherAdministrativeReplacement", 4,
            "Another administrative action replaced the configured model.")])
ModelChangeKindEnum = T(3016)

# ---------------------------------------------------------------------------
# Structured DataTypes (3050+)
# ---------------------------------------------------------------------------
struct_type(3050, "TensorSignatureDataType",
            "Shape and element type of one model input or output tensor. This is what "
            "lets a client check that what it intends to send matches what the model "
            "expects, before it sends it.",
            [("Name", String, "Tensor name as declared by the model."),
             ("ElementType", String, "Element type, for example float32, uint8 or "
                                     "int64."),
             ("Shape", Int32, "Dimensions; -1 marks a dynamic axis.", 1),
             ("Layout", String, "Optional axis layout hint, for example NCHW or "
                                "NHWC.")])
TensorSignatureDataType = T(3050)

struct_type(3051, "ModelReferenceDataType",
            "Identity of a model as a publisher, name and version triple. Every model "
            "catalogue in practice identifies a model this way, which is why an import "
            "job takes this rather than a URL: a URL says where a copy is today, the "
            "triple says which artefact is meant.",
            [("Publisher", String, "Organisation or namespace that published the "
                                   "model."),
             ("Name", String, "Model name within that publisher."),
             ("Version", String, "Immutable version identifier, or a mutable pointer "
                                 "such as a branch or channel name. Which one it is "
                                 "is stated by VersionBinding, not guessable from the "
                                 "string.")])
ModelReferenceDataType = T(3051)

struct_type(3052, "UsageDataType",
            "What one inference call consumed. Deliberately NOT named in tokens: a "
            "token is one accounting unit among several, and a model that consumes "
            "images, samples or seconds of audio needs the same accounting. UnitKind "
            "says which unit the counts are in.",
            [("UnitKind", String, "Unit the counts are expressed in, for example "
                                  "'tokens', 'images', 'samples' or 'seconds'."),
             ("InputUnits", UInt64, "Units consumed by the input."),
             ("OutputUnits", UInt64, "Units produced as output."),
             ("TotalUnits", UInt64, "Total units billed or metered for the call, "
                                    "which is not always the sum: cached or "
                                    "deduplicated input may be counted once.")])
UsageDataType = T(3052)

struct_type(3053, "CapabilityDataType",
            "One capability a deployment does or does not have. An open list rather "
            "than an enumeration because the set of things a model can do is not "
            "closed, and a client that cannot recognise a capability name is no worse "
            "off than one that cannot recognise an enumeration value it has never "
            "seen.",
            [("Name", String, "Capability name, for example 'chat', 'embeddings', "
                              "'streaming', 'tool-call' or 'structured-output'."),
             ("Supported", Boolean, "Whether this deployment supports it.")])
CapabilityDataType = T(3053)

struct_type(3054, "SafetyAssessmentDataType",
            "One finding from a safety policy applied to an inference call. Category "
            "is a String and not an enumeration because harm categories are set by the "
            "policy an installation adopts, and an industrial taxonomy looks nothing "
            "like a consumer one.",
            [("Category", String, "Category the policy assessed, for example "
                                  "'out-of-distribution-input' or a policy-defined "
                                  "name."),
             ("Severity", SafetySeverityEnum, "Severity of the finding."),
             ("Filtered", Boolean, "True when the content was withheld or altered "
                                   "rather than merely flagged."),
             ("Detail", String, "Human-readable explanation. For a human; SHALL NOT "
                                "be parsed.")])
SafetyAssessmentDataType = T(3054)

struct_type(3055, "EvaluationMetricDataType",
            "One measured metric from an evaluation run, with the threshold it was "
            "judged against. The threshold travels with the metric because a metric "
            "without its acceptance criterion cannot be acted on, and a reviewer "
            "reading it a year later has no way to recover what 'good' meant.",
            [("Name", String, "Metric name, for example 'accuracy' or "
                              "'false-negative-rate'."),
             ("Value", Double, "Measured value."),
             ("Unit", String, "Unit of the value, or empty when dimensionless."),
             ("Threshold", Double, "Acceptance threshold applied."),
             ("Comparison", String, "How Value was compared with Threshold: one of "
                                    "'>=', '<=', '>', '<' or '=='."),
             ("Passed", Boolean, "Outcome of that comparison.")])
EvaluationMetricDataType = T(3055)

struct_type(3056, "RateLimitDataType",
            "Capacity a remote endpoint is currently granting. Surfaced so a client "
            "can distinguish 'the model said no' from 'the quota said no', which are "
            "different faults with different remedies.",
            [("UnitKind", String, "Unit the limit is expressed in, matching "
                                  "UsageDataType.UnitKind, or 'requests'."),
             ("Limit", UInt64, "Units permitted per interval, or 0 when not "
                               "published."),
             ("Remaining", UInt64, "Units still available in the current interval."),
             ("Interval", Duration, "Length of the interval the limit applies to."),
             ("RetryAfter", Duration, "How long to wait before retrying. Zero when "
                                      "the endpoint gave no guidance.")])
RateLimitDataType = T(3056)

struct_type(3057, "ModelIdentitySnapshotDataType",
            "Durable identity of a model at the instant a deployment's UsesModel "
            "reference changed. It is copied into a promotion record rather than "
            "resolved through a retained NodeId, so the history remains complete "
            "after the ModelType instance or artefact location disappears. Digest "
            "trust provenance is retained with the digest so a later reader can tell "
            "whether it was declared, computed or verified.",
            [("ModelId", String, "ModelType.ModelId at the instant of change."),
             ("Version", String, "ModelType.Version at the instant of change."),
             ("Digest", ByteString,
              "ModelType.Digest at the instant of change, including an empty value "
              "where DigestProvenance was NotAvailable."),
             ("DigestAlgorithm", String,
              "ModelType.DigestAlgorithm at the instant of change."),
             ("DigestProvenance", DigestProvenanceEnum,
              "ModelType.DigestProvenance at the instant of change. Retained because "
              "the same digest bytes carry different evidentiary weight when declared "
              "by a source, computed by this Server, or verified during staging.")])
ModelIdentitySnapshotDataType = T(3057)

# ---------------------------------------------------------------------------
# ReferenceTypes (4001+)
# ---------------------------------------------------------------------------
reference_type(4001, "UsesModel", "IsUsedByDeployment",
               "Links a Deployment to the Model it executes. Clause 6.5 requires "
               "exactly one such reference per deployment so the model serving now is "
               "unambiguous. Historical result provenance uses the ModelUsed identity "
               "returned by invocation and retained by the consuming specification.")
UsesModel = T(4001)

reference_type(4002, "TrainedOn", "IsTrainingDataFor",
               "Links a Model to a Dataset it was trained or validated on. A model "
               "whose training data cannot be named is a model whose behaviour cannot "
               "be explained, which is why this reference exists rather than a string.")
TrainedOn = T(4002)

reference_type(4003, "DerivedFrom", "IsBaseOfModel",
               "Links a Model to the Model it was fine-tuned, distilled or quantized "
               "from. Lineage is a chain, not a field: a model three derivations from "
               "its base is answerable for all three, and a string naming the "
               "immediate parent cannot be walked.")
DerivedFrom = T(4003)

reference_type(4004, "FallsBackTo", "IsFallbackFor",
               "Links a Deployment to the Deployment that serves in its place when it "
               "cannot. Clause 9 forbids a cycle, and requires the response to say "
               "which deployment actually answered.")
FallsBackTo = T(4004)

reference_type(4005, "ImportedFrom", "WasImportedAs",
               "Links a Model to the catalogue resource an import job materialized it "
               "from. This is what makes 'where did this model come from' answerable "
               "after the fact, rather than only at the moment of import.")
ImportedFrom = T(4005)

reference_type(4006, "EvaluatedBy", "Evaluates",
               "Links a Model to an EvaluationRun that measured it. Optional and "
               "repeating: a model may be evaluated many times, and the run that "
               "gated its promotion is not necessarily the last one.")
EvaluatedBy = T(4006)

# ---------------------------------------------------------------------------
# ObjectTypes (1001+)
# ---------------------------------------------------------------------------
object_type(1001, "AiRootType", BaseObjectType,
            "Server-level entry point. A client that has just connected browses here to "
            "find every model, dataset, deployment and learning job the Server "
            "describes, without knowing its layout.")
RT_ = 1001
folder_member(RT_, "AiRootType", "Models", "ModelType instances.")
folder_member(RT_, "AiRootType", "Datasets", "DatasetType instances.", MR_Optional)
folder_member(RT_, "AiRootType", "Deployments", "DeploymentType instances.")
folder_member(RT_, "AiRootType", "LearningJobs", "LearningJobType instances.",
              MR_Optional)
prop_var(RT_, "AiRootType", "SpecificationVersion", String,
         "Release of this specification the Server implements, for example '0.1.0'.",
         MR_Mandatory)

object_type(1002, "ModelType", BaseObjectType,
            "Nameplate of a trained model. The member set is deliberately aligned with "
            "the IDTA 02060 AI Model Nameplate submodel template, which is currently the "
            "only standardised description of an industrial AI model, so an Asset "
            "Administration Shell can be populated from this node without loss.")
AM = 1002
prop_var(AM, "ModelType", "ModelId", String, "Identifier of the model.", MR_Mandatory)
prop_var(AM, "ModelType", "Name", LocalizedText,
         "Human-readable model name. Its Text SHALL be the name the source system "
         "uses for the model, carried across unchanged. A LocalizedText because the "
         "base model types names that way and retyping it would break every "
         "implementation, but the localizable part is the presentation: a Server MAY "
         "add a translation for display and SHALL NOT translate, reformat or "
         "prettify the Text itself. Two Servers that fetched one model from two "
         "mirrors are meant to produce the same string, and a name adjusted for "
         "house style is a name that no longer matches.",
         MR_Mandatory)
prop_var(AM, "ModelType", "Version", String, "Model version.", MR_Mandatory)
prop_var(AM, "ModelType", "Framework", String,
         "Producing framework, for example PyTorch, TensorFlow or scikit-learn.")
prop_var(AM, "ModelType", "Format", String,
         "Serialization format, for example ONNX, TensorRT or OpenVINO IR.")
prop_var(AM, "ModelType", "TaskKind", String,
         "What the model does, for example Detection2D, Classification, Segmentation, "
         "Forecasting or AnomalyDetection. Free text because the set of tasks is not "
         "closed and a closed enumeration would date faster than the model does.")
prop_var(AM, "ModelType", "Digest", ByteString,
         "Cryptographic digest of the model artefact, for provenance and integrity. "
         "Mandatory: clause 12 requires it for every model whose artefact is obtainable "
         "through ArtifactUri, and it is the terminus of the historical provenance "
         "chain from ModelUsed.",
         MR_Mandatory)
prop_var(AM, "ModelType", "DigestAlgorithm", String,
         "Hash function used for Digest. SHALL name a function with at least 256-bit "
         "output and no known collision weakness; SHA-256 is the default and is always "
         "acceptable. SHALL NOT be MD5, SHA-1 or a truncated variant - chosen-prefix "
         "collisions against those are practical, so a substituted artefact would pass "
         "verification. SHALL be non-empty where Digest is non-empty. See clause 12.",
         MR_Mandatory)
prop_var(AM, "ModelType", "ArtifactUri", String,
         "Where the model artefact can be obtained. Treated as untrusted input.")
prop_var(AM, "ModelType", "ProvenanceUri", String,
         "Training provenance or model card location.")
prop_var(AM, "ModelType", "LabelClasses", String,
         "Ordered class label set, where the model produces classified output. The "
         "INDEX is what a consuming specification's class identifier refers to, so the "
         "order is part of the contract and a Server SHALL NOT reorder it in place.",
         MR_Optional, valuerank="1")
data_var(AM, "ModelType", "Inputs", TensorSignatureDataType,
         "Input tensor signatures.", MR_Optional, valuerank="1")
data_var(AM, "ModelType", "Outputs", TensorSignatureDataType,
         "Output tensor signatures.", MR_Optional, valuerank="1")

object_type(1003, "DatasetType", BaseObjectType,
            "A dataset used to train or validate a model. Aligned with the IDTA 02058 AI "
            "Dataset submodel template. SourceKind distinguishes real capture from "
            "simulator output, which is the provenance a reviewer needs when synthetic "
            "data is involved.")
AD = 1003
prop_var(AD, "DatasetType", "DatasetId", String, "Identifier of the dataset.",
         MR_Mandatory)
prop_var(AD, "DatasetType", "Name", LocalizedText, "Human-readable dataset name.")
prop_var(AD, "DatasetType", "Version", String, "Dataset version.")
prop_var(AD, "DatasetType", "SourceKind", DatasetSourceEnum,
         "Whether samples are real, synthetic or mixed.", MR_Mandatory)
prop_var(AD, "DatasetType", "SampleCount", UInt64, "Number of samples.")
prop_var(AD, "DatasetType", "LabelClasses", String, "Class labels present.",
         MR_Optional, valuerank="1")
prop_var(AD, "DatasetType", "CreatedAt", UtcTime, "Creation time.")
prop_var(AD, "DatasetType", "ArtifactUri", String,
         "Where the dataset can be obtained. Treated as untrusted input.")
prop_var(AD, "DatasetType", "Digest", ByteString, "Digest of the dataset artefact.")

object_type(1004, "DeploymentType", BaseObjectType,
            "A model made executable somewhere. Aligned with the IDTA 02059 AI "
            "Deployment submodel template. InferenceLocation is the on-server versus "
            "off-server switch: it changes where the computation happens and therefore "
            "the trust boundary, and it changes nothing else.")
AY = 1004
prop_var(AY, "DeploymentType", "DeploymentId", String,
         "Identifier of the deployment.", MR_Mandatory)
prop_var(AY, "DeploymentType", "InferenceLocation", InferenceLocationEnum,
         "Where inference executes.", MR_Mandatory)
prop_var(AY, "DeploymentType", "AcceleratorKind", AcceleratorKindEnum,
         "Compute device executing the model.")
prop_var(AY, "DeploymentType", "AcceleratorName", String,
         "Free-text accelerator identification, for example an NPU or GPU part name.")
prop_var(AY, "DeploymentType", "EndpointUri", String,
         "Inference endpoint when InferenceLocation is not OnServer. Treated as "
         "untrusted input and subject to the resolver policy of clause 12.")
prop_var(AY, "DeploymentType", "LatencyBudget", Duration,
         "Latency the deployment is expected to meet. Set by whoever commissioned the "
         "deployment; ObservedLatency is what it actually achieved, and clause 6.4.3 "
         "compares the two.")
prop_var(AY, "DeploymentType", "BatchSize", UInt32,
         "Configured inference batch size.")
prop_var(AY, "DeploymentType", "State", DeploymentStateEnum,
         "Runtime state of the deployment.", MR_Mandatory)

object_type(1005, "LearningJobType", T(1006),
            "One turn of the capture, label, train and promote loop. It exists so that "
            "corrections arriving from a consuming application have somewhere to "
            "accumulate and a defined path into a new model version. A Server may "
            "implement only the capture stages and leave training to an external MLOps "
            "system - the state machine is the same either way.")
LJ = 1005
prop_var(LJ, "LearningJobType", "State", LearningJobStateEnum,
         "Current stage of the loop. This is the PHASE, not the program lifecycle: "
         "the inherited CurrentState says whether the job is running, this says what "
         "it is doing. Clause 7 requires the two to agree.", MR_Mandatory)
prop_var(LJ, "LearningJobType", "Dataset", NodeId_,
         "Dataset being accumulated or used.")
prop_var(LJ, "LearningJobType", "BaseModel", NodeId_, "Model the job starts from.")
prop_var(LJ, "LearningJobType", "CandidateModel", NodeId_,
         "Model produced by the job, awaiting promotion.")
prop_var(LJ, "LearningJobType", "SamplesCollected", UInt64,
         "Samples accumulated so far, including corrections fed back.")
method(LJ, "LearningJobType", "StartCollection",
       "Begin accumulating samples and corrections into the dataset.", MR_Optional)
method(LJ, "LearningJobType", "StopCollection",
       "Stop accumulating samples.", MR_Optional)
method(LJ, "LearningJobType", "TriggerTraining",
       "Request that a candidate model be trained from the collected dataset.",
       MR_Optional,
       outargs=[("Accepted", Boolean, "True when the request was queued.")])
method(LJ, "LearningJobType", "PromoteModel",
       "Promote the candidate model so that deployments begin using it. A Server SHALL "
       "require a distinct authorization for this Method: it changes what the equipment "
       "does without changing anything a reader of the address space would notice, "
       "which is precisely the change that needs a separate permission.",
       MR_Optional,
       inargs=[("Deployment", NodeId_, "Deployment to update, or null for all.")],
       outargs=[("PromotedModel", NodeId_, "The model now in use.")])

# ---------------------------------------------------------------------------
# ObjectTypes added in 0.2.0.
#
# Their MEMBERS necessarily sit at the end of the member id space even where the type
# is conceptually a base of an earlier one: member ids are assigned in declaration
# order and are append-only, so declaring AiJobType's members where the type "belongs"
# would renumber everything after it.
# ---------------------------------------------------------------------------
object_type(1006, "AiJobType", ProgramStateMachineType,
            "Abstract base of every long-running AI operation: learning, model import "
            "and asynchronous inference. It derives from the OPC 10000-10 "
            "ProgramStateMachineType, so the lifecycle - Ready, Running, Suspended, "
            "Halted - its transition events and its Start/Suspend/Resume/Halt Methods "
            "are inherited rather than reinvented, and every job in this model is "
            "auditable the same way.",
            abstract=True)
AJ = 1006
prop_var(AJ, "AiJobType", "JobId", String,
         "Identifier of the job, unique within the Server.", MR_Mandatory)
prop_var(AJ, "AiJobType", "LastError", LocalizedText,
         "Diagnostic for the most recent failure. For a human; SHALL NOT be parsed.")
prop_var(AJ, "AiJobType", "StartedAt", UtcTime, "When the job last entered Running.")
prop_var(AJ, "AiJobType", "FinishedAt", UtcTime,
         "When the job last left Running, or null while it is running.")
prop_var(AJ, "AiJobType", "Progress", Double,
         "Fraction complete, 0.0 to 1.0, or null where the job cannot estimate it. A "
         "Server SHALL NOT report a value it is guessing: null is informative, a "
         "fabricated 0.5 is not.")
prop_var(AJ, "AiJobType", "RequestedBy", String,
         "Identity that requested the job, recorded at the moment it started. Clause 12 "
         "requires this for any job that can promote a model.")

object_type(1007, "ModelImportJobType", T(1006),
            "Brings a model from a catalogue into this Server. It federates by default "
            "- materializing the catalogue entry as a ModelType whose artefact stays "
            "where it is - and stages the artefact when the target deployment could "
            "not otherwise reach it. Staging is the moment a substituted artefact "
            "would enter, which is why clause 10 requires the Digest to be verified "
            "there and nowhere else.")
MI = 1007
prop_var(MI, "ModelImportJobType", "Source", NodeId_,
         "ModelSourceType instance the model is pulled from, where the import calls "
         "an endpoint. Null where the import reads a catalogue instead, in which "
         "case Registry names it. Exactly one of the two is non-null.", MR_Mandatory)
prop_var(MI, "ModelImportJobType", "ModelReference", ModelReferenceDataType,
         "Publisher, name and version being imported.", MR_Mandatory)
prop_var(MI, "ModelImportJobType", "Mode", ImportModeEnum,
         "Whether to federate, stage, or decide from the target's InferenceLocation.",
         MR_Mandatory)
prop_var(MI, "ModelImportJobType", "TargetDeployment", NodeId_,
         "Deployment to create or update on success, or null to import the model "
         "without deploying it.")
prop_var(MI, "ModelImportJobType", "ImportedModel", NodeId_,
         "ModelType instance the job produced. Null until the job succeeds.")
prop_var(MI, "ModelImportJobType", "BytesTransferred", UInt64,
         "Artefact bytes fetched so far. Zero for a federating import, which moves "
         "none.")
prop_var(MI, "ModelImportJobType", "DigestVerified", Boolean,
         "Whether the staged artefact's computed digest matched the one the catalogue "
         "declared. False on a staging import means the artefact SHALL NOT be "
         "deployed.")
method(MI, "ModelImportJobType", "Cancel",
       "Abandon the import. A partially staged artefact SHALL be discarded rather "
       "than left where a later deployment could pick it up.", MR_Optional)

object_type(1008, "InferenceJobType", T(1006),
            "One asynchronous inference request. It exists because not every inference "
            "returns while the caller waits: a batch scored overnight and a long "
            "analysis over recorded data are ordinary industrial cases, and modelling "
            "them as a Method that blocks for hours is not.")
IJ = 1008
prop_var(IJ, "InferenceJobType", "Deployment", NodeId_,
         "Deployment executing the request.", MR_Mandatory)
prop_var(IJ, "InferenceJobType", "RequestPayload", ByteString,
         "Request body, encoded as RequestContentType states.")
prop_var(IJ, "InferenceJobType", "RequestContentType", String,
         "Media type of RequestPayload.")
prop_var(IJ, "InferenceJobType", "ResponsePayload", ByteString,
         "Response body once the job succeeds.")
prop_var(IJ, "InferenceJobType", "ResponseContentType", String,
         "Media type of ResponsePayload.")
prop_var(IJ, "InferenceJobType", "ModelUsed", NodeId_,
         "Model that ACTUALLY executed the request, which is not always the one the "
         "deployment named when the job was submitted - a fallback or a followed "
         "reference can change it in between. The provenance chain of clause 12 walks "
         "this, not the deployment's current model.")
prop_var(IJ, "InferenceJobType", "Usage", UsageDataType,
         "What the call consumed.")
prop_var(IJ, "InferenceJobType", "FinishReason", FinishReasonEnum,
         "Why the call stopped producing output.")
prop_var(IJ, "InferenceJobType", "SafetyAssessment", SafetyAssessmentDataType,
         "Findings from the safety policy, if any were applied.", valuerank="1")

object_type(1009, "ModelSourceType", BaseObjectType,
            "An externally hosted inference or catalogue endpoint this Server can "
            "reach. It carries everything needed to actually call something the Server "
            "did not deploy - the wire contract, how to authenticate, what the endpoint "
            "can do and whether it is answering - because a URI on its own is a string "
            "nobody can act on.")
MS = 1009
prop_var(MS, "ModelSourceType", "SourceId", String,
         "Identifier of the source.", MR_Mandatory)
prop_var(MS, "ModelSourceType", "EndpointUri", String,
         "Base URI of the endpoint. Untrusted input, subject to the resolver policy of "
         "clause 12.", MR_Mandatory)
prop_var(MS, "ModelSourceType", "ApiDialect", ApiDialectEnum,
         "Wire contract the endpoint speaks.", MR_Mandatory)
prop_var(MS, "ModelSourceType", "EndpointDescriptionUri", String,
         "Where the contract is documented. SHOULD be populated when ApiDialect is "
         "Proprietary, because otherwise nothing in the address space says how to call "
         "it.")
prop_var(MS, "ModelSourceType", "AuthenticationKind", AuthenticationKindEnum,
         "How the Server authenticates itself to the endpoint.", MR_Mandatory)
prop_var(MS, "ModelSourceType", "CredentialReference", String,
         "Opaque handle naming the credential in whatever store the Server uses. It is "
         "a NAME, never a secret: clause 12 forbids a Server from exposing credential "
         "material through any Attribute of this model, and a client that can read this "
         "value learns only which credential is used, not what it is.")
prop_var(MS, "ModelSourceType", "TokenAudience", String,
         "Audience or scope a bearer token is requested for, where "
         "AuthenticationKind is BearerToken.")
prop_var(MS, "ModelSourceType", "Reachability", ReachabilityEnum,
         "Whether the Server can currently reach the endpoint.", MR_Mandatory)
prop_var(MS, "ModelSourceType", "LastSuccessAt", UtcTime,
         "When the endpoint last answered successfully.")
prop_var(MS, "ModelSourceType", "ConsecutiveFailures", UInt32,
         "Failures since the last success. Reset to zero on success.")
prop_var(MS, "ModelSourceType", "RateLimit", RateLimitDataType,
         "Capacity the endpoint is currently granting.")
prop_var(MS, "ModelSourceType", "Capabilities", CapabilityDataType,
         "What the endpoint reports it can do.", valuerank="1")
method(MS, "ModelSourceType", "TestConnection",
       "Probe the endpoint and update Reachability. Defined so that a commissioning "
       "engineer can establish that credentials and network policy are right BEFORE a "
       "deployment depends on them, rather than discovering it from a failed "
       "inference.", MR_Optional,
       outargs=[("Reachable", Boolean, "Whether the probe succeeded."),
                ("Detail", LocalizedText, "Diagnostic. For a human.")])
method(MS, "ModelSourceType", "ListModels",
       "Enumerate the models the source offers.", MR_Optional,
       inargs=[("Filter", String, "Optional substring or expression; empty for all."),
               ("MaxResults", UInt32, "Upper bound on returned entries."),
               ("ContinuationPoint", ByteString,
                "Empty on the first call; otherwise the value the previous call "
                "returned. A cap without a cursor bounds the response and puts every "
                "entry past it out of reach, which against a public catalogue means "
                "most of them.")],
       outargs=[("Models", ModelReferenceDataType,
                 "Publisher, name and version of each model offered.", 1),
                ("ContinuationPoint", ByteString,
                 "Pass to the next call to continue. Empty when the enumeration is "
                 "complete, which is how a client knows to stop rather than by "
                 "comparing counts.")])

object_type(1014, "EvaluationRunType", BaseObjectType,
            "One measurement of a model against a dataset. It is a first-class object "
            "and not a field on the model because the same model is evaluated many "
            "times, and because the run that gated a promotion has to remain readable "
            "afterwards to answer why the promotion was allowed.")
ER = 1014
prop_var(ER, "EvaluationRunType", "RunId", String, "Identifier of the run.",
         MR_Mandatory)
prop_var(ER, "EvaluationRunType", "EvaluatedModel", NodeId_,
         "Model that was measured.", MR_Mandatory)
prop_var(ER, "EvaluationRunType", "Dataset", NodeId_,
         "Dataset the model was measured against.")
prop_var(ER, "EvaluationRunType", "CompletedAt", UtcTime, "When the run finished.")
prop_var(ER, "EvaluationRunType", "Metrics", EvaluationMetricDataType,
         "Measured metrics, each with the threshold it was judged against.",
         MR_Mandatory, valuerank="1")
prop_var(ER, "EvaluationRunType", "Passed", Boolean,
         "Whether every metric met its threshold. A Server SHALL NOT report true while "
         "any entry in Metrics has Passed false - a summary that disagrees with its "
         "own detail is worse than no summary.", MR_Mandatory)
prop_var(ER, "EvaluationRunType", "ReportUri", String,
         "Where the full report lives. Untrusted input, subject to clause 12.")

object_type(1015, "ModelCardType", BaseObjectType,
            "What a human needs to decide whether a model may be used here: what it is "
            "for, where it stops working, and under what terms. Separate from the "
            "nameplate because a nameplate answers 'which artefact is this' and a card "
            "answers 'should this be running on my line'.")
MC = 1015
prop_var(MC, "ModelCardType", "IntendedUse", LocalizedText,
         "What the model is for.", MR_Mandatory)
prop_var(MC, "ModelCardType", "Limitations", LocalizedText,
         "Where it is known not to work. Mandatory because a card that lists only "
         "capabilities is marketing, and the failure modes are the half a commissioning "
         "engineer needs.", MR_Mandatory)
prop_var(MC, "ModelCardType", "OutOfScopeUse", LocalizedText,
         "Uses the supplier explicitly excludes.")
prop_var(MC, "ModelCardType", "License", String,
         "Licence identifier or URI governing use of the artefact.")
prop_var(MC, "ModelCardType", "TrainingDataCutoff", UtcTime,
         "Latest date represented in the training data. A model cannot know about "
         "anything after this, which is often the explanation for a field failure.")
prop_var(MC, "ModelCardType", "EthicalConsiderations", LocalizedText,
         "Risks the supplier records.")
prop_var(MC, "ModelCardType", "ContactUri", String,
         "Where to report a problem with the model.")

# ---------------------------------------------------------------------------
# The catalogue, as a domain extension of OPC UA - xRegistry (clause 10).
#
# A model catalogue IS a registry: publishers own namespaces, models and datasets are
# resources within them, and versions are immutable. Subtyping the abstract registry
# gets that structure, its browse and lifecycle behaviour, and - because ResourceType
# is itself a Part 5 FileType - artefact streaming through the inherited Open/Read/
# Close, which is what a staging import needs.
# ---------------------------------------------------------------------------
XRegistry_RegistryType = X(63000)
XRegistry_GroupType = X(63001)
XRegistry_ResourceType = X(63002)

object_type(1010, "ModelRegistryType", XRegistry_RegistryType,
            "A catalogue of models and the datasets they were trained on. It narrows "
            "the abstract registry's group placeholder to model publishers, so that a "
            "client browsing it knows what it will find rather than discovering it.")
MR_ = 1010
# An InstanceDeclaration is overridden only by one with the SAME BrowseName, so the
# narrowing has to reuse the inherited <Group> and <Resource> names and the inherited
# Organizes. Declaring new placeholder names would leave the inherited ones fully open
# - the subtype would look narrowed while still admitting any GroupType at all.

object_type(1011, "ModelPublisherType", XRegistry_GroupType,
            "One publisher's namespace within a model registry: the organisation or "
            "project that released the models it contains. Publisher is the first "
            "element of the publisher/name/version triple by which every catalogue in "
            "practice identifies a model.")
MP = 1011

object_type(1016, "AiResourceType", XRegistry_ResourceType,
            "Abstract base of everything a model registry holds. It exists so that the "
            "inherited <Resource> placeholder can be narrowed ONCE to something that "
            "admits models and datasets and nothing else - a publisher holds both, and "
            "a placeholder can be overridden only by one declaration.",
            abstract=True)

object_type(1012, "ModelResourceType", T(1016),
            "One model in a catalogue. Its versions are immutable and identified by "
            "content, so a version that has been seen cannot change meaning; mutable "
            "names such as a branch or a release channel are pointers AT versions, "
            "never versions themselves. Because the base type is a FileType, a Server "
            "that holds the artefact serves it through the inherited Open, Read and "
            "Close; one that only describes it leaves those unimplemented and points "
            "at the artefact instead.")
MRS = 1012
prop_var(MRS, "ModelResourceType", "TaskKind", String,
         "What the model does, for example 'object-detection' or "
         "'anomaly-detection'. A String and not an enumeration, for the same reason it "
         "is one on ModelType: the set is not closed, and every catalogue in practice "
         "uses a free tag here.")
prop_var(MRS, "ModelResourceType", "Framework", String,
         "Runtime or library the artefact targets.")
prop_var(MRS, "ModelResourceType", "Digest", ByteString,
         "Digest of the artefact this version names, as the catalogue declares it. A "
         "staging import compares its own computed digest with this and refuses on "
         "mismatch.")
prop_var(MRS, "ModelResourceType", "DigestAlgorithm", String,
         "Algorithm of Digest. Subject to the strength requirement of clause 12.")
prop_var(MRS, "ModelResourceType", "SizeBytes", UInt64,
         "Artefact size, so a staging import can decide whether it has room before "
         "it starts rather than after it fails.")
prop_var(MRS, "ModelResourceType", "Gated", Boolean,
         "Whether obtaining the artefact requires an acceptance or entitlement beyond "
         "ordinary authentication. A client that ignores this discovers it as a "
         "failure part-way through a staging import.")
prop_var(MRS, "ModelResourceType", "MutableRefs", String,
         "Mutable pointers this resource publishes - branches, tags or channels - that "
         "a deployment may follow instead of pinning. Naming them is what makes "
         "VersionBinding FollowsRef checkable.", valuerank="1")

object_type(1013, "DatasetResourceType", T(1016),
            "One dataset in a catalogue, a sibling of ModelResourceType rather than "
            "something beneath it: a dataset outlives the models trained on it and is "
            "cited by several.")
DRS = 1013
prop_var(DRS, "DatasetResourceType", "SourceKind", DatasetSourceEnum,
         "Whether the samples are real, synthetic or mixed.")
prop_var(DRS, "DatasetResourceType", "SampleCount", UInt64, "Samples in the dataset.")
prop_var(DRS, "DatasetResourceType", "Digest", ByteString,
         "Digest of the dataset artefact as the catalogue declares it.")
prop_var(DRS, "DatasetResourceType", "DigestAlgorithm", String,
         "Algorithm of Digest.")
prop_var(DRS, "DatasetResourceType", "SizeBytes", UInt64, "Dataset size.")

# ---------------------------------------------------------------------------
# Members appended to types declared in 0.1.0. All append; nothing renumbers.
# ---------------------------------------------------------------------------

# --- AiRootType: the new collections ---------------------------------------
folder_member(RT_, "AiRootType", "Sources",
              "ModelSourceType instances - the externally hosted endpoints and "
              "catalogues this Server can reach.", MR_Optional)
folder_member(RT_, "AiRootType", "Registries",
              "ModelRegistryType instances this Server serves or mirrors.",
              MR_Optional)
folder_member(RT_, "AiRootType", "Evaluations",
              "EvaluationRunType instances.", MR_Optional)
folder_member(RT_, "AiRootType", "Jobs",
              "Import and asynchronous inference jobs. Learning jobs remain under "
              "LearningJobs.", MR_Optional)

# --- ModelType: provenance, card and lineage -------------------------------
obj_member(AM, "ModelType", "Card", T(1015),
           "What a human needs to decide whether this model may run here.", MR_Optional)
prop_var(AM, "ModelType", "Publisher", String,
         "Organisation or namespace that published the model. With Name and Version "
         "this is the triple every catalogue identifies a model by, and it is what "
         "makes the same model recognisable across two installations that fetched it "
         "from different mirrors.")
prop_var(AM, "ModelType", "ParameterCount", UInt64,
         "Parameters in the model, or 0 where not published. A crude but universally "
         "available proxy for what it will cost to run.")
prop_var(AM, "ModelType", "Quantization", String,
         "Numeric precision the artefact is stored in, for example 'fp32', 'int8' or "
         "'fp8'. A quantized model is a DIFFERENT artefact with different behaviour, "
         "not a packaging detail, which is why it is stated rather than left to the "
         "format string.")
prop_var(AM, "ModelType", "SafetyPolicyUri", String,
         "Safety or content policy applied to this model's output, where one is. "
         "Untrusted input, subject to clause 12.")

# --- DeploymentType: federation --------------------------------------------
prop_var(AY, "DeploymentType", "Source", NodeId_,
         "ModelSourceType instance this deployment executes through, where inference "
         "is not local. Null when InferenceLocation is OnServer.")
prop_var(AY, "DeploymentType", "VersionBinding", VersionBindingEnum,
         "Whether the deployment is pinned to an immutable model version or follows a "
         "mutable pointer.", MR_Mandatory)
prop_var(AY, "DeploymentType", "BoundRef", String,
         "The mutable pointer being followed, where VersionBinding is FollowsRef. "
         "Empty when Pinned.")
prop_var(AY, "DeploymentType", "FallbackPolicy", FallbackPolicyEnum,
         "What the Server does when this deployment cannot serve.", MR_Mandatory)
prop_var(AY, "DeploymentType", "Reachability", ReachabilityEnum,
         "Whether the execution site is currently reachable. Always Reachable for an "
         "OnServer deployment that is not Faulted.")
prop_var(AY, "DeploymentType", "ConsecutiveFailures", UInt32,
         "Failed calls since the last success.")
prop_var(AY, "DeploymentType", "LastSuccessAt", UtcTime,
         "When this deployment last answered successfully. With FallbackPolicy "
         "HoldLast this is how a caller judges whether the held answer is still worth "
         "having.")
prop_var(AY, "DeploymentType", "RateLimit", RateLimitDataType,
         "Capacity the execution site is currently granting.")
prop_var(AY, "DeploymentType", "Capabilities", CapabilityDataType,
         "What this deployment can do. A client checks here before calling a typed "
         "profile rather than discovering the answer from a rejection.", valuerank="1")

# --- DeploymentType: data residency and egress -----------------------------
prop_var(AY, "DeploymentType", "DataJurisdiction", String,
         "Where input data is processed, named in whatever scheme the operator uses - "
         "a site, a legal jurisdiction, or a named zone. This is the question a plant "
         "actually asks, and no amount of latency or accuracy data answers it.",
         MR_Mandatory)
prop_var(AY, "DeploymentType", "EgressPermitted", Boolean,
         "Whether calling this deployment sends input data outside the operator's "
         "boundary. A Server SHALL set this true for every deployment whose "
         "InferenceLocation is Cloud, and SHALL NOT set it false merely because the "
         "channel is encrypted - the question is where the data goes, not who can "
         "read it in flight.", MR_Mandatory)
prop_var(AY, "DeploymentType", "RetainsInput", Boolean,
         "Whether the execution site retains input beyond serving the request, for "
         "example for provider-side logging or training. Unknown is not a value: a "
         "Server that cannot establish this SHALL report true, because the safe "
         "assumption is the one that keeps data in.")
prop_var(AY, "DeploymentType", "EgressPolicyUri", String,
         "Where the governing data policy is documented.")

# --- DeploymentType: the invocation surface --------------------------------
method(AY, "DeploymentType", "Invoke",
       "Run inference and return the result. The payload is opaque here: what goes in "
       "and comes out is the consuming specification's vocabulary, and an envelope "
       "that tried to type it would have to be extended for every domain. What this "
       "Method fixes is everything AROUND the payload - routing, parameters, "
       "accounting, why it stopped, and which model actually ran.\n\n"
       "The signature does not change with InferenceLocation. A deployment served from "
       "the Server's own process and one served from a remote service are called "
       "identically; the location changes the trust boundary and the latency, and "
       "nothing else.", MR_Optional,
       inargs=[("Payload", ByteString, "Request body."),
               ("PayloadUri", String,
                "Location the request body is read from, where it is supplied by "
                "reference rather than carried. A Server SHALL accept exactly one of "
                "Payload and PayloadUri and SHALL reject a call supplying both or "
                "neither. Untrusted input subject to clause 12.2, and named data the "
                "execution site will read, so clause 9.5 applies to it."),
               ("ContentType", String, "Media type of Payload."),
               ("Parameters", KeyValuePair,
                "Call parameters such as a sampling temperature or an output length "
                "bound. A Server SHALL reject a parameter it does not support rather "
                "than ignore it: a caller whose parameter was silently dropped "
                "believes it took effect.", 1),
               ("Timeout", Duration,
                "How long the caller will wait. Zero means the Server's default.")],
       outargs=[("ResponsePayload", ByteString, "Response body."),
                ("ResponseContentType", String, "Media type of ResponsePayload."),
                ("ModelUsed", NodeId_,
                 "The model that ACTUALLY produced this response. Not necessarily the "
                 "one the deployment names now: a fallback answered from a different "
                 "deployment, and a FollowsRef binding may have moved. The provenance "
                 "chain of clause 12 walks this."),
                ("Usage", UsageDataType, "What the call consumed."),
                ("FinishReason", FinishReasonEnum,
                 "Why output stopped. A caller that ignores this will accept a "
                 "truncated answer as a complete one."),
                ("SafetyAssessment", SafetyAssessmentDataType,
                 "Findings from the safety policy, if any applied.", 1),
                ("RetryAfter", Duration,
                 "How long to wait before retrying, where the failure was a capacity "
                 "one. Zero when retrying immediately is as good as waiting, and "
                 "meaningless when the failure was not retryable."),
                ("TransferRequired", Boolean,
                 "True when the deployment produced a response too large to return "
                 "inline. ResponsePayload is then empty and the work is NOT lost - "
                 "Transfer names where to read it. A client that ignores this reads "
                 "an empty payload and concludes the model returned nothing."),
                ("Transfer", NodeId_,
                 "InferenceTransferType instance holding the response, where "
                 "TransferRequired is true. Null otherwise.")])
method(AY, "DeploymentType", "InvokeAsync",
       "Submit inference to be completed later, returning immediately with the job "
       "that will carry the result. For work that does not finish while a caller "
       "waits - a batch scored overnight, an analysis over recorded data.",
       MR_Optional,
       inargs=[("Payload", ByteString, "Request body."),
               ("PayloadUri", String,
                "Location the request body is read from, where it is supplied by "
                "reference rather than carried. Exactly one of Payload and PayloadUri "
                "on the same terms as Invoke. This is the argument that lets a batch "
                "already sitting in the plant's object store be scored without being "
                "copied through the Session first."),
               ("ContentType", String, "Media type of Payload."),
               ("Parameters", KeyValuePair, "Call parameters.", 1)],
       outargs=[("Job", NodeId_,
                 "InferenceJobType instance tracking the request. The caller "
                 "subscribes to it rather than polling.")])
method(AY, "DeploymentType", "GetCapabilities",
       "Report what this deployment can do, refreshed from the execution site rather "
       "than from cache. Defined because a remote endpoint's capabilities change "
       "without anything in this address space changing.", MR_Optional,
       outargs=[("Capabilities", CapabilityDataType, "Current capabilities.", 1)])

obj_member(MR_, "ModelRegistryType", "<Group>", T(1011),
           "A publisher namespace held by this registry. Narrows the inherited "
           "placeholder so a model registry admits ModelPublisherType and nothing "
           "else.", MR_OptionalPlaceholder, reftype=Organizes)
obj_member(MP, "ModelPublisherType", "<Resource>", T(1016),
           "A model or dataset published in this namespace. Narrows the inherited "
           "placeholder to this model's own resource types.", MR_OptionalPlaceholder,
           reftype=Organizes)

prop_var(AY, "DeploymentType", "MaxInlinePayloadSize", UInt32,
         "Largest request or response this deployment will carry inline through "
         "Invoke, in bytes. Zero means the deployment accepts no inline payload at "
         "all and BeginTransfer is the only way in.\n\n"
         "A client reads this BEFORE calling rather than discovering the bound from "
         "a rejection, and a Server SHALL NOT publish a value larger than its own "
         "MaxByteStringLength, the negotiated MaxMessageSize or the Session's "
         "MaxResponseMessageSize permit - the smallest of those is the real limit "
         "and a client cannot see all of them.", MR_Mandatory)
method(AY, "DeploymentType", "BeginTransfer",
       "Opens a chunked exchange for a payload that will not fit inline, returning "
       "the InferenceTransferType instance to write into. This is the general path: "
       "Invoke is the shortcut that happens to work when everything is small.",
       MR_Optional,
       inargs=[("ContentType", String, "Media type of the request body."),
               ("RequestSize", UInt64,
                "Expected request size in bytes, or 0 when not known in advance. A "
                "Server that cannot accommodate the stated size refuses here rather "
                "than after the client has uploaded it.")],
       outargs=[("Transfer", NodeId_,
                 "InferenceTransferType instance to write the request into."),
                ("Accepted", Boolean,
                 "False when the Server declined to open the exchange.")])
# ---------------------------------------------------------------------------
# Well-known instance (7001+)
# ---------------------------------------------------------------------------
well_known(7001, "AiModelManagement", T(1001), Server,
           "Entry point for the AI models this Server runs. A client browses "
           "Server/AiModelManagement/Models to find what this Server describes. It "
           "carries EventNotifier because it is the notifier for the events of clause "
           "7.4: a client subscribes here, or at the Server object above it.",
           event_notifier=EVENTNOTIFIER_SUBSCRIBE)

object_type(1017, "InferenceTransferType", BaseObjectType,
            "One chunked inference exchange. It exists because Invoke carries its "
            "payload as a ByteString, and a ByteString is bounded by "
            "MaxByteStringLength, the negotiated MaxMessageSize and the Session's "
            "MaxResponseMessageSize - none of which the model gets to choose. An "
            "image, a point cloud or a window of high-rate samples exceeds those "
            "routinely, and a call that cannot carry the input is not a call.\n\n"
            "Request and Response are Part 5 FileType objects: the client opens the "
            "request, writes it in chunks it selects, and closes it; after Execute "
            "the response is read the same way. Nothing here invents a transfer "
            "protocol, because OPC UA already has one and every client already "
            "implements it.")
TR = 1017
prop_var(TR, "InferenceTransferType", "TransferId", String,
         "Identifier of this exchange.", MR_Mandatory)
prop_var(TR, "InferenceTransferType", "State", TransferStateEnum,
         "Stage the exchange has reached.", MR_Mandatory)
obj_member(TR, "InferenceTransferType", "Request", FileType,
           "The request body, written by the client in chunks of its own choosing. "
           "Inference does not begin until Execute is called, so a partially written "
           "request is never acted on.", MR_Mandatory)
obj_member(TR, "InferenceTransferType", "Response", FileType,
           "The response body, readable once State is Completed. Empty before that.",
           MR_Mandatory)
prop_var(TR, "InferenceTransferType", "ContentType", String,
         "Media type of the request body.", MR_Mandatory)
prop_var(TR, "InferenceTransferType", "ResponseContentType", String,
         "Media type of the response body.")
prop_var(TR, "InferenceTransferType", "ModelUsed", NodeId_,
         "The model that ACTUALLY produced the response, on the same terms as "
         "Invoke: a fallback or a followed reference can change it between the call "
         "and the read.")
prop_var(TR, "InferenceTransferType", "Usage", UsageDataType,
         "What the call consumed.")
prop_var(TR, "InferenceTransferType", "FinishReason", FinishReasonEnum,
         "Why output stopped.")
prop_var(TR, "InferenceTransferType", "SafetyAssessment", SafetyAssessmentDataType,
         "Findings from the safety policy, if any applied.", valuerank="1")
prop_var(TR, "InferenceTransferType", "LastError", LocalizedText,
         "Diagnostic for the Failed state. For a human; SHALL NOT be parsed.")
prop_var(TR, "InferenceTransferType", "ExpiresAt", UtcTime,
         "When the Server may reclaim this transfer if it has not completed. A "
         "client that abandons an exchange would otherwise hold Server resources "
         "until the Session ends, and a Server that never reclaimed them would be "
         "one denial of service away from unusable.")
method(TR, "InferenceTransferType", "Execute",
       "Runs inference over the written request. The Method returns as soon as the "
       "request is accepted; State and the envelope members carry the outcome, which "
       "is what lets one exchange span a payload too large to have been a single "
       "call in the first place.", MR_Mandatory,
       outargs=[("Accepted", Boolean,
                 "False when the request was incomplete or already executed.")])
method(TR, "InferenceTransferType", "Abort",
       "Abandons the exchange and releases what it holds. A client that has stopped "
       "caring about a response SHOULD say so rather than leaving the Server to wait "
       "out ExpiresAt.", MR_Optional)

# ---------------------------------------------------------------------------
# Members appended in 0.3.0. All append; nothing renumbers.
# ---------------------------------------------------------------------------

# --- Why a Digest is what it is --------------------------------------------
# Mandatory on ModelType for the reason Digest itself is: clause 12 depends on
# it, and a rule that depends on an Optional member is one a conformant Server
# can silently not satisfy. Optional on ModelResourceType, mirroring the Digest
# it qualifies, which is Optional there.
prop_var(1002, "ModelType", "DigestProvenance", DigestProvenanceEnum,
         "Where Digest came from, or why there is none. NotAvailable is the only "
         "value permitted with an empty Digest, and it SHALL be used rather than "
         "leaving a client to guess whether the source publishes no digest or this "
         "Server declined to carry one.\n\n"
         "A Server SHALL NOT put a non-content identifier in Digest to avoid saying "
         "NotAvailable. A response fingerprint, a resource name, a storage entity tag "
         "and a repository commit identifier are none of them digests of the artefact "
         "that ran, and a client that verified against one would believe it had "
         "checked something it had not. Where such an identifier is worth publishing "
         "it belongs in ArtifactUri or ProvenanceUri, which promise nothing about "
         "content.",
         MR_Mandatory)
prop_var(1012, "ModelResourceType", "DigestProvenance", DigestProvenanceEnum,
         "Where this resource's Digest came from, on the same terms as ModelType. A "
         "catalogue that declares a digest it did not compute is DeclaredBySource; "
         "one serving the artefact through the inherited Open, Read and Close can "
         "reach ComputedByServer.")

# --- The registry an import job read from ----------------------------------
prop_var(1007, "ModelImportJobType", "Registry", NodeId_,
         "ModelRegistryType instance the model is imported from, where the import "
         "reads a catalogue rather than calling an endpoint. Null otherwise.\n\n"
         "A Server SHALL populate exactly one of Source and Registry, and SHALL "
         "leave the other null. The two name the two things an import can read from, "
         "and a job that named both would not say which one produced the artefact "
         "whose digest clause 10.4 verifies.")

# ---------------------------------------------------------------------------
# Members appended in 0.4.0. All append; nothing renumbers.
#
# Every one of these answers something a real system publishes and this model
# had nowhere to put, found by mapping it onto eleven of them. None is
# Mandatory: each is governed by a conditional SHALL in the specification
# instead, so the obligation binds exactly where a Server can discharge it.
# ---------------------------------------------------------------------------

# --- ModelType: when the artefact appeared, and when it last moved ----------
prop_var(1002, "ModelType", "PublishedAt", UtcTime,
         "When the source first published this model, where the source states it. "
         "The same question DatasetType.CreatedAt answers for a dataset, and the same "
         "reason: a model trained before a process change may no longer represent the "
         "line it runs on, and Version is a vendor string that often cannot be "
         "ordered.\n\n"
         "This is the source's date, not when this Server learned of it - a Server "
         "SHALL NOT substitute its own acquisition time, which would make every model "
         "appear to date from the last restart.")
prop_var(1002, "ModelType", "LastModifiedAt", UtcTime,
         "When the artefact behind this model last changed at the source.\n\n"
         "It exists for the FollowsRef case of clause 9.3, where the artefact can "
         "change with nothing else changing. Clause 12.3.1 requires repointing to be "
         "treated as an authorization-bearing act and points at AiJobType.RequestedBy "
         "for the record - but a reference that moves AT THE SOURCE produces no job, "
         "so without this member the audit trail that clause demands cannot be "
         "constructed on the one path it exists to cover. A Server that follows a "
         "mutable reference SHALL populate it.")

# --- ModelCardType: the dates that end a model's working life ---------------
prop_var(1015, "ModelCardType", "DeprecatedFrom", UtcTime,
         "When the source stops treating this model as current while continuing to "
         "serve it. The date that starts a requalification, not the one that ends "
         "production.")
prop_var(1015, "ModelCardType", "SupportedUntil", UtcTime,
         "When the source stops serving this model altogether.\n\n"
         "Its consequence is not degradation. On this date the deployment stops, "
         "Reachability goes Unreachable, and FallbackPolicy decides what happens next "
         "- which, where it is FallBackTo, means the line keeps producing and "
         "something outside the qualified configuration is answering. A date that was "
         "knowable a year in advance therefore becomes an unplanned change of model, "
         "and it is published by the serving system in machine-readable form.")

# --- DeploymentType: what a client must send, and what is serving it --------
prop_var(1004, "DeploymentType", "ApiDialect", ApiDialectEnum,
         "The contract a client's Payload must satisfy when calling Invoke on this "
         "deployment. RestChatCompletions means the Payload is a chat-completions "
         "request body; OpenInferenceProtocol means it is an OIP inference body; "
         "EmbeddedRuntime and TensorRemoteProcedure name the tensor contracts "
         "described by Inputs and Outputs; Proprietary means the contract is named "
         "only by EndpointDescriptionUri.\n\n"
         "This does not type the payload - clause 8.2 keeps it opaque and that is "
         "unchanged. It names WHICH contract the opaque bytes are expected to satisfy, "
         "which is what a client browsing an unfamiliar deployment needs before it can "
         "send anything at all.")
prop_var(1004, "DeploymentType", "EndpointDescriptionUri", String,
         "Where the request and response contract for this deployment is documented. "
         "Untrusted input, subject to clause 12.2. Required in practice wherever "
         "ApiDialect is Proprietary, because nothing else then says what to send.")
prop_var(1004, "DeploymentType", "RuntimeIdentity", String,
         "Opaque identifier of the serving configuration currently behind this "
         "deployment - a serving-stack fingerprint, an engine profile, a container "
         "image digest. Compared for equality and never parsed, on the same terms as "
         "Digest.\n\n"
         "It is not the model. The same artefact served by two runtime builds can "
         "produce different numbers, and where the execution site publishes such an "
         "identity it is the only thing that records the difference. A change to it "
         "under a Pinned binding IS the observable change to the deployment that "
         "clause 9.3 says a pinned artefact cannot move without.")
prop_var(1004, "DeploymentType", "ObservedLatency", Duration,
         "Most recent inference latency this Server measured for this deployment.\n\n"
         "LatencyBudget states what the deployment is expected to meet, and clause "
         "6.4.3 makes Degraded the state of a deployment that is answering but missing "
         "it. Without a measurement the comparison has no published input, so the "
         "state transition could not be checked against a Server that claimed it. A "
         "Server that reports Degraded on latency grounds SHALL populate this.")

# --- InferenceJobType: the large-payload path Invoke already had ------------
prop_var(1008, "InferenceJobType", "RequestUri", String,
         "Where the request body was read from, where it was supplied by reference "
         "rather than carried. Untrusted input under clause 12.2, and an egress path "
         "under clause 9.5.")
prop_var(1008, "InferenceJobType", "ResponseUri", String,
         "Where the result was written, where the execution site returns a location "
         "rather than bytes. Empty when the response is carried inline or through "
         "Transfer.")
prop_var(1008, "InferenceJobType", "TransferRequired", Boolean,
         "True when the job produced a response too large to carry inline. "
         "ResponsePayload is then empty and the work is NOT lost - Transfer names "
         "where to read it.")
prop_var(1008, "InferenceJobType", "Transfer", NodeId_,
         "InferenceTransferType instance holding the response, where TransferRequired "
         "is true. Null otherwise.\n\n"
         "Invoke carries the same pair, and the asymmetry would otherwise leave the "
         "jobs most likely to produce a large result - a batch scored overnight, an "
         "analysis over recorded data - bounded by exactly the three limits clause "
         "8.2.4 says this model does not get to choose.")

# ---------------------------------------------------------------------------
# Event types (1018+)
# ---------------------------------------------------------------------------
# Promotion is the one act in this model that changes what the equipment decides, and
# it is the one a later audit has to reconstruct. A client can already subscribe to a
# deployment's model reference and see that it changed, but not who changed it, nor
# which evaluation justified it, nor what it was before - and those are exactly the
# questions asked after a batch is rejected. This event carries them at the moment they
# are known, rather than leaving them to be recovered from whatever logging the Server
# happens to keep.
MPE = 1018
event_type(MPE, "ModelPromotedEventType", BaseEventType,
           "A deployment's configured UsesModel target changed. Raised on promotion, "
           "and also on a rollback or any other Server-initiated substitution, because "
           "a consumer auditing what decided a verdict cares that the model changed and "
           "not why the operator called it a promotion.")
prop_var(MPE, "ModelPromotedEventType", "Deployment", NodeId_,
         "The DeploymentType instance whose model changed.", MR_Mandatory)
prop_var(MPE, "ModelPromotedEventType", "NewModel", NodeId_,
         "The ModelType now being served. Its Digest is what ties a later verdict to a "
         "verifiable artefact, so a consumer that records only one field records this.",
         MR_Mandatory)
prop_var(MPE, "ModelPromotedEventType", "PreviousModel", NodeId_,
         "The ModelType that was being served, or null where the deployment was serving "
         "none. A rollback is distinguishable from a promotion only by comparing the "
         "two, which is why both are carried.")
prop_var(MPE, "ModelPromotedEventType", "EvaluationRun", NodeId_,
         "The EvaluationRunType whose Passed result gated this promotion, or null where "
         "none did. Clause 7.2 says promotion SHOULD be gated on one; null here is the "
         "observable consequence of a Server that promoted without it, which is the "
         "fact an audit is looking for.")
prop_var(MPE, "ModelPromotedEventType", "PromotedBy", String,
         "Identity that authorized or initiated the change, as the Server "
         "authenticated it. For an automatic substitution this is the Server's stable "
         "system identity. BaseEventType carries no user field, and clause 12.3 "
         "requires promotion to be separately authorized - a requirement whose "
         "satisfaction is unobservable if the identity is not recorded where the act "
         "is.")

# ---------------------------------------------------------------------------
# Promotion history added in 0.5.1. All member ids append after the 0.5.0
# event fields. A record snapshots identities rather than retaining target nodes:
# history must survive deletion of the ModelType and EvaluationRunType instances.
# ---------------------------------------------------------------------------
PR = 1019
object_type(PR, "PromotionRecordType", BaseObjectType,
            "Immutable, authoritative record of one successful substitution of a "
            "DeploymentType UsesModel target. The record is created atomically with "
            "the substitution, is read-only after creation, and remains available for "
            "at least the lifetime of the deployment.")
prop_var(PR, "PromotionRecordType", "RecordId", String,
         "Server-wide unique identifier of this record.", MR_Mandatory)
prop_var(PR, "PromotionRecordType", "Deployment", NodeId_,
         "Convenience NodeId of the DeploymentType whose UsesModel target changed.",
         MR_Mandatory)
prop_var(PR, "PromotionRecordType", "DeploymentId", String,
         "Snapshot of DeploymentType.DeploymentId at the instant of change.",
         MR_Mandatory)
prop_var(PR, "PromotionRecordType", "PreviousModel", NodeId_,
         "Convenience NodeId of the previous ModelType. The identity snapshot, not "
         "this reference, is durable when that node disappears.", MR_Mandatory)
prop_var(PR, "PromotionRecordType", "NewModel", NodeId_,
         "Convenience NodeId of the new ModelType. The identity snapshot, not this "
         "reference, is durable when that node disappears.", MR_Mandatory)
prop_var(PR, "PromotionRecordType", "PreviousModelIdentity",
         ModelIdentitySnapshotDataType,
         "Self-contained identity of the model replaced by the substitution.",
         MR_Mandatory)
prop_var(PR, "PromotionRecordType", "NewModelIdentity",
         ModelIdentitySnapshotDataType,
         "Self-contained identity of the model selected by the substitution.",
         MR_Mandatory)
prop_var(PR, "PromotionRecordType", "EvaluationRun", NodeId_,
         "Convenience NodeId of the EvaluationRunType that gated the change, or null "
         "where none did.")
prop_var(PR, "PromotionRecordType", "EvaluationRunId", String,
         "Snapshot of EvaluationRunType.RunId. SHALL be populated when EvaluationRun "
         "is populated and remains authoritative if that node disappears.")
prop_var(PR, "PromotionRecordType", "ChangedAt", UtcTime,
         "Time at which the successful UsesModel substitution took effect.",
         MR_Mandatory)
prop_var(PR, "PromotionRecordType", "ChangedBy", String,
         "Authenticated identity that authorized or initiated the change. For an "
         "automatic substitution, the Server SHALL use its stable system identity.",
         MR_Mandatory)
prop_var(PR, "PromotionRecordType", "ChangeKind", ModelChangeKindEnum,
         "Trigger for the change, classified by cause and never by version ordering.",
         MR_Mandatory)
prop_var(PR, "PromotionRecordType", "Reason", LocalizedText,
         "Optional human-readable administrative reason. SHALL NOT be parsed.")

promotion_records = folder_member(
    AY, "DeploymentType", "PromotionRecords",
    "Complete immutable history of successful UsesModel substitutions for this "
    "deployment. Conditionally required wherever the configured UsesModel target can "
    "change and retained for at least the deployment lifetime.", MR_Optional)
obj_member(promotion_records, "DeploymentType_PromotionRecords",
           "<PromotionRecord>", T(PR),
           "One immutable PromotionRecordType in this deployment's history.",
           MR_OptionalPlaceholder)

prop_var(MPE, "ModelPromotedEventType", "PromotionRecord", NodeId_,
         "PromotionRecordType created atomically with this substitution. It SHALL be "
         "populated whenever the event is raised by a Server claiming AI-Events, and "
         "the event's deployment, model, evaluation and actor fields SHALL agree with "
         "the authoritative record.")

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
    # A DataTypeEncoding browses as "Default Binary" in namespace 0: the BrowseName is
    # standard, not model-defined. Emitting it as 1:Default Binary is what every real
    # companion NodeSet avoids, and tooling that resolves encodings by BrowseName
    # cannot find it.
    prefix = "" if n.attrs.get("BrowseNameNamespace") == 0 else f"{OWN_NS}:"
    a = [f'{tag} NodeId="{T(n.nid)}"', f'BrowseName="{prefix}{sx.escape(n.bname)}"']
    if "SymbolicName" in n.attrs:
        a.append(f'SymbolicName="{sx.escape(n.attrs["SymbolicName"])}"')
    if n.parent is not None:
        a.append(f'ParentNodeId="{n.parent}"')
    for k in ("DataType", "ValueRank", "ArrayDimensions", "EventNotifier"):
        if k in n.attrs:
            v = n.attrs[k]
            if k == "DataType":
                v = DATATYPE_ALIAS.get(v, v)
            a.append(f'{k}="{v}"')
    if n.cls in ("UAObjectType", "UADataType") and n.abstract:
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
           '<!-- OPC UA - AI Model Management and Inference companion model. PROVISIONAL NodeIds and namespace '
           '(final IDs assigned by the OPC Foundation / working group). -->',
           '<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
           'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" '
           'xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
           '  <NamespaceUris>']
    out += [f'    <Uri>{u}</Uri>' for u in NAMESPACE_URIS]
    out += ['  </NamespaceUris>',
           '  <Models>',
           f'    <Model ModelUri="{NAMESPACE}" Version="{VERSION}" '
           f'PublicationDate="{PUBDATE}">',
           f'      <RequiredModel ModelUri="http://opcfoundation.org/UA/" '
           f'Version="{BASE_UA_VERSION}" PublicationDate="{BASE_UA_PUBDATE}" />',
           f'      <RequiredModel ModelUri="{XREG_NS}" '
           f'Version="{XREG_VERSION}" PublicationDate="{XREG_PUBDATE}" />',
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
    "i=2391": "ProgramStateMachineType",
}


def _dt_name(dt):
    """Render a DataType or supertype NodeId as a readable name."""
    if not dt:
        return ""
    if dt in BASE_TYPE_NAMES:
        return BASE_TYPE_NAMES[dt]
    if dt in DATATYPE_ALIAS:
        return DATATYPE_ALIAS[dt]
    if dt.startswith(f"ns={OWN_NS};i="):
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


def _cell(s):
    """A description as ONE table cell.

    A member description may hold paragraphs, and a raw newline inside a row ends the
    row: everything after it renders as prose and the following member starts a second
    table. Paragraph breaks become <br><br>, which keeps the structure and keeps the row
    on one line. MD033 is off for exactly this reason.
    """
    return _esc(s).replace("\n\n", "<br><br>").replace("\n", " ")


def emit_md():
    """Annex A. This is the authoritative node reference, so it must carry everything an
    implementer needs: DataType, ValueRank and ModellingRule for every member, the field
    list of every structure, the value of every enumeration literal, and the full
    signature of every Method. A bare NodeId/BrowseName table is not sufficient."""
    obj_types = [n for n in ORDER if NODES[n].cls == "UAObjectType"]
    data_types = [n for n in ORDER if NODES[n].cls == "UADataType"]
    ref_types = [n for n in ORDER if NODES[n].cls == "UAReferenceType"]

    L = ["# OPC UA — AI Model Management and Inference — Annex A: Information model (generated)",
         "",
         "> Generated by `build_model.py`. Do not edit by hand. Namespace "
         f"`{NAMESPACE}` (index {OWN_NS}). NodeIds are provisional.",
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
        L.append(f"| {T(nid)} | {n.bname} | {n.cls[2:]} | "
                 f"{_dt_name(_supertype(nid))} |")
    L.append("")

    L += ["## A.2 ReferenceTypes", "",
          "| NodeId | BrowseName | InverseName | Subtype of | Description |",
          "|---|---|---|---|---|"]
    for nid in ref_types:
        n = NODES[nid]
        L.append(f"| {T(nid)} | {n.bname} | {n.inverse} | "
                 f"{_dt_name(_supertype(nid))} | {_cell(n.desc)} |")
    L.append("")

    L += ["## A.3 ObjectTypes", ""]
    for nid in obj_types:
        n = NODES[nid]
        abstract = " (abstract)" if n.abstract else ""
        L.append(f"### {n.bname}{abstract} — `{T(nid)}`")
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
                         f"{_rule_name(m)} | {_cell(mn.desc)} |")
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
                    L.append(f"| {an} | {at} | {ar} | {_cell(ad)} |")
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
        L.append(f"### {n.bname} — `{T(nid)}`")
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
                         f"{_cell(mm.group(3) or '')} |")
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
                         f"{_cell(mm.group(4) or '')} |")
        L.append("")

    return "\n".join(L).rstrip() + "\n"


Server_Namespaces = "i=11715"
NamespaceMetadataType = "i=11616"


def namespace_metadata(uri, version, pubdate, is_subset=False):
    """Declare this model's namespace metadata."""
    meta = _mid()
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

    _prop("NamespaceUri", "i=12", "String", uri)
    _prop("NamespaceVersion", "i=12", "String", version)
    _prop("NamespacePublicationDate", "i=13", "DateTime", pubdate)
    _prop("IsNamespaceSubset", "i=1", "Boolean", "true" if is_subset else "false")


namespace_metadata(NAMESPACE, VERSION, PUBDATE)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    std = os.path.normpath(os.path.join(
        here, "..", "..", "..", "..",
        "model", "metaverse-specs", "ai-model-management"))
    os.makedirs(std, exist_ok=True)
    with open(os.path.join(std, "Opc.Ua.AiModelManagement.NodeSet2.xml"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit())
    with open(os.path.join(std, "Opc.Ua.AiModelManagement.NodeIds.csv"), "w",
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


if __name__ == "__main__":
    main()
