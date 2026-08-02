#!/usr/bin/env python3
"""
Generator for the OPC UA - Robot Intent companion specification (WG draft).

Emits, from a single in-code source of truth:
  * ../../../robot-intent/Opc.Ua.RobotIntent.NodeSet2.xml - the information model
  * ../../../robot-intent/Opc.Ua.RobotIntent.NodeIds.csv  - the NodeId assignments
  * model-reference.md                                    - the generated Annex A

The model is a COMPANION specification in its OWN namespace
(http://opcfoundation.org/UA/RobotIntent/, namespace index 1). Nodes therefore use
`ns=1;i=<n>` NodeIds; references to base UA types use plain `i=<n>`.

It is deliberately STANDALONE: the only <RequiredModel> is the base UA namespace, so a
Server can adopt it without pulling in DI, Machinery or Robotics. Binding to an OPC
40010-1 MotionDeviceSystem is an optional profile carried by a ReferenceType, not by a
NodeSet dependency.

NodeIds are PROVISIONAL (final IDs assigned by the OPC Foundation) and follow the repo
convention: ObjectTypes/Interfaces 1001+, Enumerations 3001+ (EnumStrings = enum + 900),
Structures 3050+, ReferenceTypes 4001+, DataType encodings 5001+, well-known instances
7001+, and all remaining instance declarations sequentially from 6001. New members must
be APPENDED so that previously published member NodeIds stay stable.

Design notes (see ../../../robot-intent/OPC-UA-Robot-Intent-Research.md for the
evidence base):
  * OPC 40010-1 describes robot TOPOLOGY and defines no motion verbs. This model
    supplies the verbs, and nothing else, so the two compose rather than compete.
  * An intent outlives an OPC UA Call, so the lifecycle is a Part 10 program instance:
    submission returns a NodeId handle, progress arrives as ProgramTransitionEvents,
    and the result survives in FinalResultData.
  * Verbs are a DataType HIERARCHY rather than one Method each, so a single intent and
    a mission step are the same shape and extension is a subtyping act.
  * Queueing is PLCopen MC_BufferMode and concurrency is VDA 5050 blockingType, both
    adopted unchanged because both are already implemented everywhere.
  * Orientation is a unit quaternion (x, y, z, w). OPC UA defines no quaternion type,
    and the Euler triple in ThreeDOrientation carries no convention of its own; Annex C
    gives the normative conversion to and from ThreeDFrame.
"""
from __future__ import annotations
import os
import re
import xml.sax.saxutils as sx

NAMESPACE = "http://opcfoundation.org/UA/RobotIntent/"
VERSION = "0.1.0"
PUBDATE = "2026-08-02T00:00:00Z"
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
KeyValuePair = "i=14533"

Server = "i=2253"

ALIASES = [
    ("Boolean", Boolean), ("Int32", Int32), ("UInt32", UInt32), ("UInt64", UInt64),
    ("Double", Double), ("String", String), ("Guid", Guid), ("ByteString", ByteString),
    ("NodeId", NodeId_), ("QualifiedName", QualifiedName), ("LocalizedText", LocalizedText),
    ("UtcTime", UtcTime), ("Duration", Duration), ("Argument", Argument),
    ("EUInformation", EUInformation), ("KeyValuePair", KeyValuePair),
    ("BaseDataType", BaseDataType),
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


def well_known(nid, name, typedef, parent_nodeid, desc, reftype=HasComponent):
    add(nid, "UAObject", name, name, desc=desc, parent=parent_nodeid)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, parent_nodeid, forward=False)
    return nid


# ===========================================================================
# ==============================  MODEL DEFINITION  =========================
# ===========================================================================
CAT = "RobotIntent"
CAT_DT = "RobotIntent DataTypes"
CAT_RT = "RobotIntent ReferenceTypes"

# Part 10 program model - the lifecycle this specification builds on.
ProgramStateMachineType = "i=2391"

# ---------------------------------------------------------------------------
# Enumerations (3001+)
# ---------------------------------------------------------------------------
enum_type(3001, "ExecutionStateEnum",
          "Fine-grained execution state of an intent or a mission. This REFINES the "
          "Part 10 program state machine rather than restating it: Queued, Cancelling "
          "and the three terminal outcomes cannot be told apart from CurrentState "
          "alone. Clause 6.3 fixes which ExecutionState may accompany which Part 10 "
          "state, and a Server shall satisfy that table.",
          [("Accepted", 0, "Admitted and validated, not yet queued or executing."),
           ("Queued", 1, "Waiting behind another intent because BufferMode is "
                         "Buffered or a blending mode. Corresponds to PLCopen Busy "
                         "without Active."),
           ("Executing", 2, "Commanding the robot now."),
           ("Suspended", 3, "Paused by request; position is retained and execution "
                            "can resume."),
           ("Cancelling", 4, "A cancel was accepted and the Server is bringing the "
                             "motion to a controlled end. Not yet terminal."),
           ("Succeeded", 5, "Terminal. Completed as requested."),
           ("Failed", 6, "Terminal. Did not complete; Failure carries the reason."),
           ("Cancelled", 7, "Terminal. Ended early because a cancel was accepted."),
           ("Retriable", 8, "Terminal for now, but the Server can re-attempt it on "
                            "Retry. A Server that does not offer Retry never enters "
                            "this state and reports Failed instead.")])
ExecutionStateEnum = T(3001)

enum_type(3002, "BufferModeEnum",
          "How a newly submitted intent relates to the one already executing. The "
          "values and their meanings are those of PLCopen Motion Control MC_BufferMode, "
          "adopted unchanged because every motion runtime already implements them. In "
          "all blending modes the robot does not decelerate to a stop at the boundary, "
          "and the predecessor reaches Succeeded when blending begins rather than when "
          "its target is exactly attained.",
          [("Aborting", 0, "Abort what is executing and start immediately. The aborted "
                           "intent terminates as Cancelled. This is the default."),
           ("Buffered", 1, "Queue; start when the predecessor succeeds."),
           ("BlendingLow", 2, "Blend at the lower of the two boundary speeds."),
           ("BlendingPrevious", 3, "Blend at the predecessor's boundary speed."),
           ("BlendingNext", 4, "Blend at the successor's boundary speed."),
           ("BlendingHigh", 5, "Blend at the higher of the two boundary speeds.")])
BufferModeEnum = T(3002)

enum_type(3003, "BlockingModeEnum",
          "Whether an intent tolerates motion and other intents running alongside it. "
          "The four values are the two-by-two matrix of VDA 5050 blockingType, adopted "
          "because it is the only widely deployed concurrency annotation for robot "
          "actions.",
          [("None", 0, "Runs in the background; motion may continue and other intents "
                       "may run concurrently."),
           ("Soft", 1, "Motion stops for the duration; other intents may still run."),
           ("Single", 2, "Motion may continue; no other intent may run concurrently."),
           ("Hard", 3, "Motion stops and no other intent may run concurrently. The "
                       "intent has exclusive use of the robot.")])
BlockingModeEnum = T(3003)

enum_type(3004, "TerminationModeEnum",
          "Whether a motion ends exactly on its target or is blended into the next "
          "one. This is the only distinction every vendor expresses identically; the "
          "blend magnitude in BlendDataType.Radius is a request, not a guarantee.",
          [("Exact", 0, "Come to rest on the target before the next motion begins. "
                        "ABB fine, FANUC FINE, Yaskawa PL=0, KUKA no approximation."),
           ("Blend", 1, "Round the corner into the next motion without stopping.")])
TerminationModeEnum = T(3004)

enum_type(3005, "ReleaseModeEnum",
          "How a held object is given up.",
          [("Drop", 0, "Open the end effector where it is, without placing."),
           ("Place", 1, "Set the object down under control at the target."),
           ("Handover", 2, "Retain the object until the Server judges a receiving "
                           "party has taken it.")])
ReleaseModeEnum = T(3005)

enum_type(3006, "ApproachModeEnum",
          "Direction from which an end effector approaches an object or a placement.",
          [("Default", 0, "The Server chooses."),
           ("ToolZ", 1, "Along the tool's own Z axis."),
           ("Top", 2, "From above, in the frame the target is expressed in."),
           ("Side", 3, "Laterally, in the frame the target is expressed in.")])
ApproachModeEnum = T(3006)

enum_type(3007, "FrameRoleEnum",
          "Role of a coordinate frame, following the coordinate systems ISO 9787 "
          "standardises. The roles say WHICH frames exist; no standard says how to "
          "calibrate between them, which is why CoordinateFrameType carries the "
          "transform explicitly.",
          [("World", 0, "The cell-level reference frame."),
           ("Base", 1, "The robot base frame."),
           ("MechanicalInterface", 2, "The flange at the end of the last link, to "
                                      "which an end effector is fitted."),
           ("Tool", 3, "A tool frame, whose origin is a tool centre point."),
           ("Object", 4, "A workpiece or work-object frame."),
           ("Other", 5, "A frame whose role is none of the above.")])
FrameRoleEnum = T(3007)

enum_type(3008, "OperationalModeEnum",
          "Operational mode of the robot system, as defined by ISO 10218-1 and "
          "reported identically by OPC 40010-1. It is READ-ONLY here: mode selection "
          "is a safety function performed by safety-rated means, and this "
          "specification defines no way to command it. Clause 10 restricts intent "
          "submission to Automatic and AutomaticExternal.",
          [("Other", 0, "Booting, uncalibrated, or a safety system fault."),
           ("ManualReducedSpeed", 1, "Teaching mode with a speed ceiling and a held "
                                     "enabling device."),
           ("ManualHighSpeed", 2, "Program verification with an enabling device."),
           ("Automatic", 3, "Automatic operation with the safeguarded space secured."),
           ("AutomaticExternal", 4, "Automatic operation commanded by an external "
                                    "system. This is the mode this specification is "
                                    "written for.")])
OperationalModeEnum = T(3008)

enum_type(3009, "IntentFailureEnum",
          "Why an intent did not succeed. The set is deliberately small and "
          "diagnosable: a client decides whether to retry, re-plan or escalate from "
          "this value alone, and reads Message only to show a human.",
          [("None", 0, "No failure. Reported on a successful outcome."),
           ("Unreachable", 1, "The target lies outside the reachable workspace."),
           ("Kinematics", 2, "No kinematic solution, or a singularity on the path."),
           ("Collision", 3, "A collision was predicted or detected."),
           ("JointLimit", 4, "A joint limit would be or was exceeded."),
           ("SpeedLimit", 5, "The requested speed or acceleration is not permitted in "
                             "the active mode."),
           ("ToolMissing", 6, "The required tool is not fitted or not identified."),
           ("ObjectNotFound", 7, "The object to act on was not present."),
           ("GraspFailed", 8, "The object was not acquired, or was lost in transit."),
           ("Timeout", 9, "The intent did not complete within its permitted time."),
           ("NotPermittedInMode", 10, "Refused because the operational mode does not "
                                      "permit it. See clause 10."),
           ("ControlNotOwned", 11, "Refused because the caller does not hold command "
                                   "authority. See clause 8."),
           ("CapabilityNotSupported", 12, "The Server does not implement this intent "
                                          "type, or this combination of options."),
           ("ParameterInvalid", 13, "A parameter was missing, malformed or out of "
                                    "range."),
           ("QueueFull", 14, "The queue is at MaxQueueDepth."),
           ("Superseded", 15, "An Aborting submission or a mission update replaced it "
                              "before it could run."),
           ("HardwareFault", 16, "A fault in the robot, the end effector or the "
                                 "controller."),
           ("SafetyStop", 17, "A safety function acted. The safety system, not this "
                              "interface, decided this."),
           ("Other", 18, "A reason none of the above describes; see Message."),
           ("SafetyLimitExceeded", 19,
            "Refused because the request would exceed a limit the safety system is "
            "enforcing. See clause 10.3.")])
IntentFailureEnum = T(3009)

enum_type(3010, "StopModeEnum",
          "How urgently a cancellation should bring motion to an end. The values are "
          "those of PossibleStopModes in OPC 40010-1, so a Server implementing both "
          "reports one vocabulary. This is an APPLICATION-LEVEL request: it does not "
          "select, imply or guarantee any IEC 60204-1 stop category, which only the "
          "robot's safety system determines. See clause 10.",
          [("OnPath", 1, "Decelerate along the programmed path."),
           ("EndOfCycle", 2, "Stop when the current cycle completes."),
           ("ProcessStop", 3, "Stop at a point the process defines as safe."),
           ("QuickStop", 4, "Decelerate as quickly as the drives allow."),
           ("EndOfInstruction", 5, "Stop when the current instruction completes.")])
StopModeEnum = T(3010)

enum_type(3011, "AxisKindEnum",
          "Whether an axis rotates or translates. This fixes the unit of the "
          "corresponding entry of JointMoveIntentDataType.JointTargets.",
          [("Revolute", 0, "Rotates. Its joint target is in radians."),
           ("Prismatic", 1, "Translates. Its joint target is in metres.")])
AxisKindEnum = T(3011)

enum_type(3012, "MissionUpdateResultEnum",
          "Outcome of a mission update, reported so a client can tell a stale update "
          "from a rejected one without parsing a StatusCode.",
          [("Accepted", 0, "The horizon was replaced as requested."),
           ("Outdated", 1, "MissionUpdateId was not greater than the current one."),
           ("BaseConflict", 2, "The update would have altered a released step."),
           ("UnknownMission", 3, "No mission with that MissionId is held."),
           ("Rejected", 4, "Refused for a reason the Server states in a message.")])
MissionUpdateResultEnum = T(3012)

# ---------------------------------------------------------------------------
# Structured DataTypes (3050+)
# ---------------------------------------------------------------------------
struct_type(3050, "Pose3DDataType",
            "A rigid-body pose. Position is metres; Orientation is a UNIT QUATERNION "
            "ordered (x, y, z, w). Quaternions are used because OPC UA defines no "
            "quaternion type and the Euler triple in ThreeDOrientation is ambiguous "
            "without an external convention; Annex C gives the normative conversion to "
            "and from ThreeDFrame. All frames are right-handed. FrameId names the "
            "CoordinateFrame the pose is expressed in; an empty FrameId means the "
            "Server's default work frame.",
            [("FrameId", String, "FrameId of the CoordinateFrame this pose is "
                                 "expressed in; empty for the default work frame."),
             ("Position", Double, "Translation (x, y, z) in metres.", 1, 3),
             ("Orientation", Double, "Unit quaternion (x, y, z, w).", 1, 4)])
Pose3DDataType = T(3050)

struct_type(3051, "MotionConstraintsDataType",
            "Limits a motion is to respect. Every field is a REQUEST bounded by what "
            "the robot is configured to permit: a Server clamps rather than refuses, "
            "except where clause 10 requires refusal. A value of zero or less means "
            "the field is unspecified and the Server chooses.",
            [("SpeedFraction", Double, "Fraction of the configured maximum speed, in "
                                       "the range 0 to 1. This is the portable speed "
                                       "control: every vendor supports it."),
             ("CartesianSpeed", Double, "Tool centre point speed in metres per "
                                        "second. Ignored by joint moves."),
             ("CartesianAcceleration", Double, "Tool centre point acceleration in "
                                               "metres per second squared."),
             ("Jerk", Double, "Rate of change of acceleration in metres per second "
                              "cubed.")])
MotionConstraintsDataType = T(3051)

struct_type(3052, "BlendDataType",
            "How a motion ends. Radius is interpreted only when Termination is Blend, "
            "and is a request: controllers that expose a unitless blend scale rather "
            "than a distance map it as best they can, and a Server that cannot honour "
            "the exact radius still succeeds.",
            [("Termination", TerminationModeEnum, "Exact stop, or blend into the next "
                                                  "motion."),
             ("Radius", Double, "Blend radius in metres, measured from the target. "
                                "Zero or less means the Server chooses.")])
BlendDataType = T(3052)

struct_type(3053, "IntentDataType",
            "Abstract base of every intent. An intent is a single task-level request; "
            "it is what a client submits and what a mission step holds, so the two are "
            "the same shape. Extension is by SUBTYPING this structure, which keeps new "
            "intents discoverable through IntentCapabilitiesType rather than by "
            "probing for BrowseNames.",
            [("IntentId", String, "Client-assigned identifier, unique among the "
                                  "intents the client has outstanding. Empty asks the "
                                  "Server to assign one, which it returns."),
             ("Label", LocalizedText, "Human-readable description. Never interpreted."),
             ("BufferMode", BufferModeEnum, "How this intent relates to one already "
                                            "executing."),
             ("BlockingMode", BlockingModeEnum, "Whether motion and other intents may "
                                                "proceed alongside it.")],
            abstract=True)
IntentDataType = T(3053)

struct_type(3054, "MotionIntentDataType",
            "Abstract base of the intents that move the robot. ToolFrame names the "
            "frame whose origin is driven to the target - without it a pose target is "
            "meaningless, and OPC 40010-1 defines no tool centre point at all.",
            [("ToolFrame", NodeId_, "The CoordinateFrame, of role Tool, whose origin "
                                    "is driven to the target. Null means the tool "
                                    "currently fitted."),
             ("Constraints", MotionConstraintsDataType, "Speed and acceleration "
                                                        "limits for this motion."),
             ("Blend", BlendDataType, "How this motion ends.")],
            base=IntentDataType, abstract=True)
MotionIntentDataType = T(3054)

struct_type(3055, "JointMoveIntentDataType",
            "Move by interpolating in joint space. This is the fastest way between two "
            "configurations and the path the tool centre point takes is not "
            "controlled. It is the portable equivalent of PTP, MoveJ, J and MOVJ. "
            "Giving a pose rather than joint values asks the Server to solve the "
            "kinematics itself, which is the 'move to this pose, you choose how' case.",
            [("HasJointTargets", Boolean, "True when JointTargets is meaningful; "
                                          "False when TargetPose is."),
             ("JointTargets", Double, "One value per axis, in the order the axes are "
                                      "declared under the controller: radians for a "
                                      "Revolute axis, metres for a Prismatic one.",
              1, 0),
             ("TargetPose", Pose3DDataType, "Pose to reach, used when HasJointTargets "
                                            "is False.")],
            base=MotionIntentDataType)
JointMoveIntentDataType = T(3055)

struct_type(3056, "LinearMoveIntentDataType",
            "Move the tool centre point along a straight line to the target. The "
            "portable equivalent of LIN, MoveL, L and MOVL.",
            [("Target", Pose3DDataType, "Pose to reach.")],
            base=MotionIntentDataType)
LinearMoveIntentDataType = T(3056)

struct_type(3057, "CircularMoveIntentDataType",
            "Move the tool centre point along the circular arc that passes through "
            "ViaPoint and ends at Target. The portable equivalent of CIRC, MoveC, C "
            "and MOVC. Only the position of ViaPoint defines the arc; its orientation "
            "is ignored.",
            [("ViaPoint", Pose3DDataType, "A pose on the arc between the start and "
                                          "the target. Only its position is used."),
             ("Target", Pose3DDataType, "Pose to reach.")],
            base=MotionIntentDataType)
CircularMoveIntentDataType = T(3057)

struct_type(3058, "GraspIntentDataType",
            "Close the end effector on an object. Force and Width are requests; an "
            "end effector that cannot regulate force ignores Force and still succeeds.",
            [("Tool", NodeId_, "The Tool to actuate. Null means the tool currently "
                               "fitted."),
             ("Force", Double, "Grasp force in newtons. Zero or less means the Server "
                               "chooses."),
             ("Width", Double, "Opening at which to close, in metres. Zero or less "
                               "means the Server chooses."),
             ("Approach", ApproachModeEnum, "Direction of approach.")],
            base=IntentDataType)
GraspIntentDataType = T(3058)

struct_type(3059, "ReleaseIntentDataType",
            "Give up a held object.",
            [("Tool", NodeId_, "The Tool to actuate. Null means the tool currently "
                               "fitted."),
             ("Mode", ReleaseModeEnum, "How the object is given up."),
             ("HasTarget", Boolean, "True when Target is meaningful."),
             ("Target", Pose3DDataType, "Where to place the object, when Mode is "
                                        "Place.")],
            base=IntentDataType)
ReleaseIntentDataType = T(3059)

struct_type(3060, "PickIntentDataType",
            "Take an object from a location. Source is a REFERENCE TO A LOCATION NODE, "
            "not a name: the location's pose and its properties are then read from the "
            "address space, so the station identity has exactly one definition.",
            [("Source", NodeId_, "The Location to pick from."),
             ("Tool", NodeId_, "The Tool to use. Null means the tool currently "
                               "fitted."),
             ("ObjectClass", String, "What to pick, when the location can hold more "
                                     "than one kind. Empty means whatever is there."),
             ("Force", Double, "Grasp force in newtons. Zero or less means the Server "
                               "chooses."),
             ("Approach", ApproachModeEnum, "Direction of approach."),
             ("Attributes", KeyValuePair, "Further named parameters the Server "
                                          "declares in its capabilities.", 1, 0)],
            base=IntentDataType)
PickIntentDataType = T(3060)

struct_type(3061, "PlaceIntentDataType",
            "Put a held object at a location. Destination is a reference to a Location "
            "node, for the same reason as PickIntentDataType.Source.",
            [("Destination", NodeId_, "The Location to place at."),
             ("Tool", NodeId_, "The Tool to use. Null means the tool currently "
                               "fitted."),
             ("Approach", ApproachModeEnum, "Direction of approach."),
             ("Attributes", KeyValuePair, "Further named parameters the Server "
                                          "declares in its capabilities.", 1, 0)],
            base=IntentDataType)
PlaceIntentDataType = T(3061)

struct_type(3062, "ToolChangeIntentDataType",
            "Exchange the fitted end effector.",
            [("Tool", NodeId_, "The Tool to fit. Null means release the fitted tool "
                               "and fit nothing."),
             ("DockStation", NodeId_, "The Location of the tool changer. Null lets "
                                      "the Server choose.")],
            base=IntentDataType)
ToolChangeIntentDataType = T(3062)

struct_type(3063, "SetOutputIntentDataType",
            "Set a discrete or analogue output. Output references an OutputSignal "
            "node, so the signal's meaning, range and unit are described once in the "
            "address space instead of being implied by a string.",
            [("Output", NodeId_, "The OutputSignal to write."),
             ("Value", BaseDataType, "Value to write, of the signal's own DataType.")],
            base=IntentDataType)
SetOutputIntentDataType = T(3063)

struct_type(3064, "CallProgramIntentDataType",
            "Run a program that already exists on the controller. This is the escape "
            "hatch for capability this specification does not model, and the bridge to "
            "the OPC 40010-1 task control surface.",
            [("Program", NodeId_, "The Program to run."),
             ("Arguments", KeyValuePair, "Named arguments for the program.", 1, 0)],
            base=IntentDataType)
CallProgramIntentDataType = T(3064)

struct_type(3065, "WaitIntentDataType",
            "Do nothing for a while, or until released. A mission needs this to "
            "express a rendezvous with something the robot does not control; without "
            "it a client has to hold the queue open from outside.",
            [("Duration", Duration, "How long to wait, in milliseconds. Zero or less "
                                    "waits until Signal is released."),
             ("Signal", NodeId_, "An OutputSignal or other node whose becoming true "
                                 "ends the wait. Null waits only for Duration.")],
            base=IntentDataType)
WaitIntentDataType = T(3065)

struct_type(3066, "IntentResultDataType",
            "The outcome of one intent, preserved after it terminates. AchievedPose "
            "records where the tool centre point actually ended, which is what lets a "
            "client tell a blended corner from an exact stop and audit a placement.",
            [("IntentId", String, "The intent this describes."),
             ("State", ExecutionStateEnum, "Terminal state reached."),
             ("Failure", IntentFailureEnum, "Reason, or None on success."),
             ("Message", LocalizedText, "Human-readable detail. Never parsed."),
             ("HasAchievedPose", Boolean, "True when AchievedPose is meaningful."),
             ("AchievedPose", Pose3DDataType, "Where the tool centre point came to "
                                              "rest, or was when blending began."),
             ("StartTime", UtcTime, "When execution began."),
             ("EndTime", UtcTime, "When the terminal state was reached."),
             ("Outputs", KeyValuePair, "Named results the intent produced, for "
                                       "example the identity of a picked object.",
              1, 0)])
IntentResultDataType = T(3066)

struct_type(3067, "MissionStepDataType",
            "One step of a mission. Released is what splits a mission into its "
            "immutable base and its revisable horizon: a released step has been "
            "committed and may already be executing, so an update may not touch it. "
            "Status is a HINT - where Operation is not null, that IntentOperation's "
            "state machine decides.",
            [("StepId", String, "Identifier unique within the mission."),
             ("SequenceId", UInt32, "Execution order within the mission, ascending."),
             ("Released", Boolean, "True for a base step, which is committed and "
                                   "immutable. False for a horizon step, which an "
                                   "update may replace or remove."),
             ("Intent", IntentDataType, "The intent this step executes."),
             ("Status", ExecutionStateEnum, "Reported status. Where Operation is not "
                                            "null its state machine is authoritative "
                                            "and this reflects it."),
             ("Operation", NodeId_, "The IntentOperation executing this step, or null "
                                    "while the step has not begun."),
             # ErrorPolicyEnum and MissionTransitionDataType are appended further
             # down, so they are referenced by id here. A field DataType is emitted as
             # a NodeId string; the node it names only has to exist in the finished
             # NodeSet, which the validator checks.
             ("ErrorPolicy", T(3016), "What the mission does when this step "
                                              "does not succeed."),
             ("FallbackStepId", String, "The step to continue at, when ErrorPolicy is "
                                        "Fallback or Compensate.")])
MissionStepDataType = T(3067)

struct_type(3068, "MissionDataType",
            "An ordered sequence of intents submitted and tracked as a unit. "
            "MissionUpdateId increases with every update, so a Server can reject an "
            "update that crossed with another in flight instead of applying it out of "
            "order.",
            [("MissionId", String, "Client-assigned identifier. Empty asks the Server "
                                   "to assign one, which it returns."),
             ("MissionUpdateId", UInt32, "Revision of this mission, increasing. The "
                                         "first submission is 0."),
             ("Label", LocalizedText, "Human-readable description. Never interpreted."),
             ("Steps", MissionStepDataType, "The steps, in ascending SequenceId "
                                            "order.", 1, 0),
             ("Transitions", T(3083),
              "The step graph. An empty array means the steps run in order, which is "
              "the flat sequence a mission without branching has always been.", 1, 0)])
MissionDataType = T(3068)

struct_type(3069, "IntentCapabilityDataType",
            "What the Server will accept for one intent type. This is the machine-"
            "readable declaration that makes an intent surface discoverable: a client "
            "reads it once and knows what it may submit, instead of submitting to find "
            "out. It is the analogue of the VDA 5050 factsheet.",
            [("IntentType", NodeId_, "The DataType of the intent, a subtype of "
                                     "IntentDataType."),
             ("Description", LocalizedText, "What this Server does with it."),
             ("CancelSupported", Boolean, "True when Cancel is honoured for it. A "
                                          "Server may still refuse a particular "
                                          "cancel; see clause 6.5."),
             ("PauseSupported", Boolean, "True when Pause and Resume are honoured."),
             ("RetrySupported", Boolean, "True when it can terminate Retriable and be "
                                         "re-attempted."),
             ("SupportedBufferModes", BufferModeEnum, "Buffer modes accepted for it. "
                                                      "Aborting is always accepted "
                                                      "and always listed.", 1, 0),
             ("SupportedBlockingModes", BlockingModeEnum, "Blocking modes accepted "
                                                          "for it.", 1, 0),
             ("Attributes", KeyValuePair, "Named parameters this Server recognises in "
                                          "the intent's Attributes field.", 1, 0)])
IntentCapabilityDataType = T(3069)

# ---------------------------------------------------------------------------
# ReferenceTypes (4001+)
# ---------------------------------------------------------------------------
reference_type(4001, "HasIntentController", "IntentControllerOf",
               "Binds an intent surface to the thing it commands. This is how the "
               "model attaches to a robot described by another specification - an OPC "
               "40010-1 MotionDeviceSystem, say - without depending on it. Annex B "
               "defines that binding.")
HasIntentController = T(4001)

reference_type(4002, "HasFrameParent", "FrameParentOf",
               "From a CoordinateFrame to the frame its Transform is expressed in. "
               "Frames form a tree, so a pose given in one frame can be re-expressed "
               "in another by composing the transforms along the path between them.")
HasFrameParent = T(4002)

# ---------------------------------------------------------------------------
# ObjectTypes (1001+)
# ---------------------------------------------------------------------------
object_type(1001, "RobotIntentRootType", BaseObjectType,
            "Server-level entry point. A client that has just connected browses here "
            "to find every robot it can command, without knowing the Server's layout.")
RT_ = 1001
folder_member(RT_, "RobotIntentRootType", "Controllers",
              "The intent surfaces this Server offers, one per commandable robot.")
prop_var(RT_, "RobotIntentRootType", "SpecificationVersion", String,
         "Release of this specification the Server implements, for example '0.1.0'.",
         MR_Mandatory)

object_type(1002, "IntentControllerType", BaseObjectType,
            "The intent surface for one robot: what it can be asked to do, the frames "
            "and objects those requests refer to, and the intents and missions "
            "currently outstanding. Everything a client needs in order to command the "
            "robot hangs from here.")
IC = 1002
prop_var(IC, "IntentControllerType", "OperationalMode", OperationalModeEnum,
         "Operational mode reported by the robot. Read-only: mode selection is a "
         "safety function and this specification defines no way to command it. Clause "
         "10 restricts submission to Automatic and AutomaticExternal.", MR_Mandatory)
prop_var(IC, "IntentControllerType", "Ready", Boolean,
         "True when the robot will accept intents now. A client checks this before "
         "submitting rather than inferring readiness from OperationalMode alone.",
         MR_Mandatory)
prop_var(IC, "IntentControllerType", "ControlOwner", NodeId_,
         "SessionId of the client that currently holds command authority, or null "
         "when no client does. Only that client may submit; see clause 8.",
         MR_Mandatory)
prop_var(IC, "IntentControllerType", "MaxQueueDepth", UInt32,
         "How many intents may be queued behind the executing one. Zero means the "
         "Server accepts only Aborting submissions.", MR_Mandatory)
data_var(IC, "IntentControllerType", "ActiveIntent", NodeId_,
         "The IntentOperation executing now, or null.", MR_Mandatory)
data_var(IC, "IntentControllerType", "ActiveMission", NodeId_,
         "The Mission executing now, or null.")
obj_member(IC, "IntentControllerType", "Capabilities", T(1005),
           "What this robot will accept.", MR_Mandatory)
folder_member(IC, "IntentControllerType", "Frames",
              "The coordinate frames poses may be expressed in.")
folder_member(IC, "IntentControllerType", "Tools",
              "The end effectors this robot can use.")
folder_member(IC, "IntentControllerType", "Locations",
              "The named places intents refer to.")
folder_member(IC, "IntentControllerType", "Axes",
              "The axes, in the order JointMoveIntentDataType.JointTargets uses.")
folder_member(IC, "IntentControllerType", "Outputs",
              "The signals SetOutput can write.", MR_Optional)
folder_member(IC, "IntentControllerType", "Programs",
              "The controller programs CallProgram can run.", MR_Optional)
folder_member(IC, "IntentControllerType", "Intents",
              "Outstanding and recently completed intents, one Object each.")
folder_member(IC, "IntentControllerType", "Missions",
              "Outstanding and recently completed missions, one Object each.",
              MR_Optional)

method(IC, "IntentControllerType", "RequestControl",
       "Take command authority. A Server grants it only when no other Session holds "
       "it, or when the holder's Session has closed. Holding authority is a "
       "precondition for submitting, and exists so that two clients cannot interleave "
       "motion; it is NOT the single point of control that ISO 10218-2 requires, "
       "which is enforced by safety-rated means outside this interface.",
       MR_Mandatory,
       outargs=[("Granted", Boolean, "True when the caller now holds authority."),
                ("CurrentOwner", NodeId_,
                 "SessionId of the holder after the call.")])
method(IC, "IntentControllerType", "ReleaseControl",
       "Give up command authority. Outstanding intents are unaffected; use "
       "CancelAll to stop them.", MR_Mandatory)
method(IC, "IntentControllerType", "SubmitIntent",
       "Submit one intent. Returns as soon as the intent is admitted - NOT when the "
       "robot has finished, which may be minutes later. The returned Operation is a "
       "node the client subscribes to for progress and reads for the result. This is "
       "the whole reason the model is built on the Part 10 program lifecycle: an OPC "
       "UA Call cannot stay open for the duration of a motion.",
       MR_Mandatory,
       inargs=[("Intent", IntentDataType, "The intent to execute.")],
       outargs=[("IntentId", String, "Identifier of the intent, assigned by the "
                                     "Server when the request left it empty."),
                ("Operation", NodeId_, "The IntentOperation that tracks it.")])
method(IC, "IntentControllerType", "CancelIntent",
       "Ask the Server to end an intent early. The Server MAY refuse, and says so in "
       "Accepted, because some motions cannot be abandoned safely part-way. This is "
       "not the OPC UA Cancel Service, which discards a pending response and leaves "
       "the robot moving; see clause 6.5.",
       MR_Mandatory,
       inargs=[("IntentId", String, "The intent to cancel."),
               ("StopMode", StopModeEnum, "How urgently to stop.")],
       outargs=[("Accepted", Boolean, "True when the Server will act on it.")])
method(IC, "IntentControllerType", "CancelAll",
       "Ask the Server to end every outstanding intent and mission.", MR_Mandatory,
       inargs=[("StopMode", StopModeEnum, "How urgently to stop.")],
       outargs=[("Cancelled", UInt32, "How many were acted on.")])
method(IC, "IntentControllerType", "Pause",
       "Suspend execution, retaining position so it can be resumed.", MR_Optional,
       outargs=[("Accepted", Boolean, "True when execution is suspending.")])
method(IC, "IntentControllerType", "Resume",
       "Continue execution suspended by Pause.", MR_Optional,
       outargs=[("Accepted", Boolean, "True when execution is resuming.")])
method(IC, "IntentControllerType", "Retry",
       "Re-attempt an intent that terminated Retriable.", MR_Optional,
       inargs=[("IntentId", String, "The intent to re-attempt.")],
       outargs=[("Operation", NodeId_, "The IntentOperation that tracks the new "
                                       "attempt.")])
method(IC, "IntentControllerType", "SubmitMission",
       "Submit an ordered sequence of intents as one unit. Steps marked Released form "
       "the base and are committed; the rest form the horizon and may still be "
       "revised by UpdateMission.", MR_Optional,
       inargs=[("Mission", MissionDataType, "The mission to execute.")],
       outargs=[("MissionId", String, "Identifier of the mission, assigned by the "
                                      "Server when the request left it empty."),
                ("Operation", NodeId_, "The Mission that tracks it.")])
method(IC, "IntentControllerType", "UpdateMission",
       "Replace the horizon of a mission already submitted. The base is untouchable: "
       "it has been committed and may already have executed, so an update that would "
       "alter a released step is refused rather than partly applied.", MR_Optional,
       inargs=[("MissionId", String, "The mission to update."),
               ("MissionUpdateId", UInt32, "Revision of the update. Must be greater "
                                           "than the mission's current value."),
               ("Steps", MissionStepDataType, "The steps that replace the horizon.",
                1)],
       outargs=[("Result", MissionUpdateResultEnum, "Outcome of the update."),
                ("Message", LocalizedText, "Human-readable detail on a refusal.")])
method(IC, "IntentControllerType", "CancelMission",
       "Ask the Server to end a mission and every intent belonging to it.",
       MR_Optional,
       inargs=[("MissionId", String, "The mission to cancel."),
               ("StopMode", StopModeEnum, "How urgently to stop.")],
       outargs=[("Accepted", Boolean, "True when the Server will act on it.")])

object_type(1003, "IntentOperationType", ProgramStateMachineType,
            "One submitted intent, tracked to completion. It is a Part 10 program "
            "instance, so its lifecycle is the one OPC UA already defines for work "
            "that outlives a service call: transitions raise ProgramTransitionEvents, "
            "the terminal result survives in FinalResultData, and "
            "ProgramDiagnostic2DataType records which Session commanded it without "
            "this specification having to model provenance itself.")
IO = 1003
prop_var(IO, "IntentOperationType", "IntentId", String,
         "Identifier of the intent this instance executes.", MR_Mandatory)
data_var(IO, "IntentOperationType", "Intent", IntentDataType,
         "The intent as admitted, after the Server applied its defaults. A client "
         "reads this to learn what it actually asked for.", MR_Mandatory)
prop_var(IO, "IntentOperationType", "ExecutionState", ExecutionStateEnum,
         "Fine-grained state. It refines CurrentState rather than restating it; "
         "clause 6.3 fixes which pairs are legal.", MR_Mandatory)
prop_var(IO, "IntentOperationType", "Progress", Double,
         "Fraction of the intent completed, 0 to 1, where the Server can estimate it. "
         "Negative means it cannot.")
data_var(IO, "IntentOperationType", "CurrentPose", Pose3DDataType,
         "Where the driven tool centre point is now. Subscribe for tracking; this is "
         "a status report at the sampling rate the client asks for, not a control "
         "signal, and clause 4.3 explains why it must not be used as one.")
data_var(IO, "IntentOperationType", "Result", IntentResultDataType,
         "Outcome, meaningful once ExecutionState is terminal. The same value is "
         "placed under FinalResultData so a Part 10 client finds it where Part 10 "
         "says it will be.", MR_Mandatory)
prop_var(IO, "IntentOperationType", "MissionId", String,
         "The mission this intent belongs to, or empty when it was submitted alone.")
prop_var(IO, "IntentOperationType", "QueuePosition", UInt32,
         "Place in the queue while ExecutionState is Queued, 1 being next. Zero once "
         "it is no longer queued.")

object_type(1004, "MissionType", ProgramStateMachineType,
            "One submitted mission, tracked to completion. It is a Part 10 program "
            "instance for the same reasons an IntentOperation is, and it owns the "
            "IntentOperations of its steps.")
MI = 1004
prop_var(MI, "MissionType", "MissionId", String,
         "Identifier of the mission this instance executes.", MR_Mandatory)
prop_var(MI, "MissionType", "MissionUpdateId", UInt32,
         "Revision currently in force.", MR_Mandatory)
data_var(MI, "MissionType", "Mission", MissionDataType,
         "The mission as it now stands, base and horizon together.", MR_Mandatory)
prop_var(MI, "MissionType", "ExecutionState", ExecutionStateEnum,
         "Fine-grained state, refining CurrentState as clause 6.3 fixes.",
         MR_Mandatory)
prop_var(MI, "MissionType", "CurrentStepId", String,
         "The step executing now, or empty.", MR_Mandatory)
prop_var(MI, "MissionType", "ReleasedStepCount", UInt32,
         "How many steps are in the base. The first this many steps of Mission.Steps "
         "are committed; the rest are the horizon.", MR_Mandatory)

object_type(1005, "IntentCapabilitiesType", BaseObjectType,
            "What one robot will accept. A client reads this once, before it submits "
            "anything, and knows what the robot can do and under what constraints.")
CP = 1005
data_var(CP, "IntentCapabilitiesType", "SupportedIntents", IntentCapabilityDataType,
         "One entry per intent type this Server accepts.", MR_Mandatory, valuerank="1")
prop_var(CP, "IntentCapabilitiesType", "MissionsSupported", Boolean,
         "True when SubmitMission is implemented.", MR_Mandatory)
prop_var(CP, "IntentCapabilitiesType", "MissionHorizonSupported", Boolean,
         "True when UpdateMission can revise the horizon of a running mission.",
         MR_Mandatory)
prop_var(CP, "IntentCapabilitiesType", "BlendingSupported", Boolean,
         "True when the blending buffer modes actually blend. A Server that treats "
         "them as Buffered reports False, so a client is not misled about the path.",
         MR_Mandatory)
prop_var(CP, "IntentCapabilitiesType", "MaxBlendRadius", Double,
         "Largest blend radius the robot will honour, in metres. Zero or less means "
         "it is not bounded here.")
prop_var(CP, "IntentCapabilitiesType", "AxisCount", UInt32,
         "How many axes JointMoveIntentDataType.JointTargets must carry.",
         MR_Mandatory)

object_type(1006, "CoordinateFrameType", BaseObjectType,
            "A named right-handed Cartesian frame. Frames form a tree through "
            "HasFrameParent, so a client can compose a chain from a tool frame to a "
            "world frame. Roles follow ISO 9787, which standardises which frames "
            "exist; the transform between them is carried explicitly because no "
            "standard says how to calibrate it.")
CFR = 1006
prop_var(CFR, "CoordinateFrameType", "FrameId", String,
         "Identifier referenced by Pose3DDataType.FrameId. Unique among the frames "
         "of one controller.", MR_Mandatory)
prop_var(CFR, "CoordinateFrameType", "Role", FrameRoleEnum,
         "Role of this frame.", MR_Mandatory)
data_var(CFR, "CoordinateFrameType", "Transform", Pose3DDataType,
         "Pose of this frame within its parent. Ignored for a root frame.")

object_type(1007, "ToolType", BaseObjectType,
            "An end effector. Its tool centre point is a CoordinateFrame of role "
            "Tool, which is what a motion intent drives to a target - OPC 40010-1 "
            "models robot topology in detail but has no tool centre point at all, so "
            "this specification supplies one.")
TL = 1007
prop_var(TL, "ToolType", "ToolId", String, "Identifier unique within the controller.",
         MR_Mandatory)
prop_var(TL, "ToolType", "Name", LocalizedText, "Human-readable name.", MR_Mandatory)
prop_var(TL, "ToolType", "Fitted", Boolean,
         "True when this tool is on the robot now.", MR_Mandatory)
prop_var(TL, "ToolType", "TcpFrame", NodeId_,
         "The CoordinateFrame, of role Tool, that is this tool's centre point.",
         MR_Mandatory)
prop_var(TL, "ToolType", "Mass", Double, "Mass in kilograms. Zero or less when "
                                         "not stated.")
prop_var(TL, "ToolType", "MaxGraspForce", Double,
         "Largest grasp force in newtons, or zero when the tool does not grasp.")
prop_var(TL, "ToolType", "MaxOpening", Double,
         "Largest opening in metres, or zero when the tool does not grasp.")

object_type(1008, "LocationType", BaseObjectType,
            "A named place an intent can refer to. Pick and Place reference these "
            "nodes rather than naming a station in a string, so a location has one "
            "definition that a client can read, subscribe to and reason about.")
LC = 1008
prop_var(LC, "LocationType", "LocationId", String,
         "Identifier unique within the controller.", MR_Mandatory)
prop_var(LC, "LocationType", "Name", LocalizedText, "Human-readable name.",
         MR_Mandatory)
data_var(LC, "LocationType", "Pose", Pose3DDataType,
         "Where the location is.", MR_Mandatory)
prop_var(LC, "LocationType", "Occupied", Boolean,
         "True when the Server believes something is there.")
prop_var(LC, "LocationType", "ObjectClass", String,
         "What the location holds, when it holds one kind of thing. Empty otherwise.")
prop_var(LC, "LocationType", "Capacity", UInt32,
         "How many objects it can hold. Zero means unstated.")

object_type(1009, "AxisType", BaseObjectType,
            "One axis of the robot. The order of these nodes under the controller's "
            "Axes folder fixes the order of JointMoveIntentDataType.JointTargets, and "
            "Kind fixes each entry's unit.")
AX = 1009
prop_var(AX, "AxisType", "AxisId", String, "Identifier unique within the controller.",
         MR_Mandatory)
prop_var(AX, "AxisType", "Index", UInt32,
         "Position in JointTargets, counting from zero.", MR_Mandatory)
prop_var(AX, "AxisType", "Kind", AxisKindEnum,
         "Whether it rotates or translates, which fixes the unit of its joint "
         "target.", MR_Mandatory)
prop_var(AX, "AxisType", "MinPosition", Double,
         "Lower limit, in radians or metres by Kind.", MR_Mandatory)
prop_var(AX, "AxisType", "MaxPosition", Double,
         "Upper limit, in radians or metres by Kind.", MR_Mandatory)
prop_var(AX, "AxisType", "MaxSpeed", Double,
         "Largest speed, in radians or metres per second by Kind.")
data_var(AX, "AxisType", "Position", Double,
         "Where the axis is now, in radians or metres by Kind.")

object_type(1010, "OutputSignalType", BaseObjectType,
            "A signal SetOutput can write. Modelling it as a node means the range, "
            "the unit and the meaning are described once, instead of every client "
            "having to know what a line name implies.")
OS = 1010
prop_var(OS, "OutputSignalType", "SignalId", String,
         "Identifier unique within the controller.", MR_Mandatory)
prop_var(OS, "OutputSignalType", "Name", LocalizedText, "Human-readable name.",
         MR_Mandatory)
data_var(OS, "OutputSignalType", "Value", BaseDataType,
         "Current value.", MR_Mandatory)
prop_var(OS, "OutputSignalType", "Writable", Boolean,
         "True when SetOutput may write it.", MR_Mandatory)
prop_var(OS, "OutputSignalType", "EngineeringUnits", EUInformation,
         "Unit of an analogue signal.")

object_type(1011, "ProgramType", BaseObjectType,
            "A program held on the controller that CallProgram can run. This is the "
            "bridge to capability this specification does not model, and to the "
            "programs an OPC 40010-1 task control already exposes.")
PG = 1011
prop_var(PG, "ProgramType", "ProgramId", String,
         "Identifier unique within the controller.", MR_Mandatory)
prop_var(PG, "ProgramType", "Name", LocalizedText, "Human-readable name.",
         MR_Mandatory)
prop_var(PG, "ProgramType", "Description", LocalizedText, "What the program does.")
data_var(PG, "ProgramType", "Parameters", KeyValuePair,
         "Named parameters it accepts, with their default values.", valuerank="1")

# ---------------------------------------------------------------------------
# Well-known instance (7001+)
# ---------------------------------------------------------------------------
well_known(7001, "RobotIntent", T(1001), Server,
           "Entry point for robot intent on this Server. A client browses "
           "Server/RobotIntent/Controllers to find every robot it can command.")



# ===========================================================================
# ===  APPENDED MEMBERS  ====================================================
# ===========================================================================
# Everything below APPENDS. New enumerations take 3013+, structures 3070+,
# encodings continue from 5019, ObjectTypes 1012+, and every instance
# declaration takes the next free member id, so no previously assigned NodeId
# moves. Members of types declared earlier are added here rather than beside
# their siblings for exactly that reason.

ContentFilter = "i=586"

# ---------------------------------------------------------------------------
# Enumerations (3013+)
# ---------------------------------------------------------------------------
enum_type(3013, "SafeMotionFunctionEnum",
          "The safe motion function a safety system is enforcing, as defined by "
          "IEC 61800-5-2. This is a REPORT. The safety system enforces these "
          "independently of this interface, and a client reading them has not thereby "
          "obtained any safety function - see clause 10.",
          [("None", 0, "No safe motion function is active."),
           ("Sto", 1, "Safe Torque Off: torque is removed."),
           ("Ss1", 2, "Safe Stop 1: a controlled ramp to standstill, then Safe Torque "
                      "Off."),
           ("Ss2", 3, "Safe Stop 2: a controlled ramp to standstill, which is then "
                      "held under power."),
           ("Sos", 4, "Safe Operating Stop: standstill is monitored while the drive "
                      "remains energised."),
           ("Sls", 5, "Safely Limited Speed: speed is monitored against a limit."),
           ("Slp", 6, "Safely Limited Position: position is monitored against a "
                      "limit."),
           ("Sdi", 7, "Safe Direction: motion is permitted in one direction only."),
           ("Sbc", 8, "Safe Brake Control: a brake is commanded safely.")])
SafeMotionFunctionEnum = T(3013)

enum_type(3014, "RealTimeTransportEnum",
          "The transport of a brokered real-time channel. This specification defines "
          "none of these: it describes them so a client can find and open one, and the "
          "samples never traverse this interface.",
          [("Rtde", 0, "Universal Robots Real-Time Data Exchange."),
           ("Egm", 1, "ABB Externally Guided Motion."),
           ("Fri", 2, "KUKA Fast Research Interface."),
           ("Rsi", 3, "KUKA Robot Sensor Interface."),
           ("MotoRos2", 4, "Yaskawa MotoROS2."),
           ("OpcUaFx", 5, "OPC UA FX (OPC 10000-80 to -84). The open path, and the "
                          "only one in this list that is an OPC Foundation "
                          "specification."),
           ("Other", 6, "A transport identified by the channel's own descriptor.")])
RealTimeTransportEnum = T(3014)

enum_type(3015, "ChannelInitiatorEnum",
          "Which end opens the transport connection of a brokered channel. Getting "
          "this wrong is the usual reason a first connection attempt fails, so it is "
          "stated rather than left to the reader.",
          [("Server", 0, "The Server connects to an endpoint the client is listening "
                         "on."),
           ("Client", 1, "The client connects to the endpoint the Server publishes.")])
ChannelInitiatorEnum = T(3015)

enum_type(3016, "ErrorPolicyEnum",
          "What a mission does when one of its steps does not succeed. Without this a "
          "mission can only abort, which forces every recovery out into the client.",
          [("Abort", 0, "End the mission. This is the default and the behaviour of a "
                        "mission that declares no policy."),
           ("Retry", 1, "Re-attempt the step. A Server bounds the attempts and reports "
                        "Failed when they are exhausted."),
           ("Skip", 2, "Record the failure and continue with the next step."),
           ("Fallback", 3, "Continue at FallbackStepId instead."),
           ("Compensate", 4, "Run the fallback step to undo the work already done, "
                             "then end the mission.")])
ErrorPolicyEnum = T(3016)

enum_type(3017, "DivergenceKindEnum",
          "How the transitions leaving one step relate to each other, following the "
          "divergence of an IEC 61131-3 sequential function chart.",
          [("Alternative", 0, "Exactly one transition is taken - the first whose "
                              "condition holds. An OR divergence."),
           ("Parallel", 1, "Every transition is taken and the branches run "
                           "concurrently. An AND divergence.")])
DivergenceKindEnum = T(3017)

enum_type(3018, "WeaveShapeEnum",
          "The oscillation applied across an arc weld seam.",
          [("None", 0, "No weave."),
           ("Sine", 1, "Sinusoidal oscillation."),
           ("Zigzag", 2, "Triangular oscillation."),
           ("Trapezoid", 3, "Trapezoidal oscillation, with a dwell at each edge.")])
WeaveShapeEnum = T(3018)

# ---------------------------------------------------------------------------
# Structured DataTypes (3070+)
# ---------------------------------------------------------------------------
struct_type(3070, "TrajectoryPointDataType",
            "One point of a time-parameterised path. Positions are per axis in the "
            "order the axes are declared, in radians or metres by AxisKind. "
            "TimeFromStart is measured from the start of the trajectory, which is what "
            "makes the path a trajectory rather than a list of waypoints. Velocities "
            "and Accelerations are optional and may be empty.",
            [("TimeFromStart", Duration, "Milliseconds from the start of the "
                                         "trajectory."),
             ("Positions", Double, "One value per axis.", 1, 0),
             ("Velocities", Double, "One value per axis, or empty.", 1, 0),
             ("Accelerations", Double, "One value per axis, or empty.", 1, 0)])
TrajectoryPointDataType = T(3070)

struct_type(3071, "MotionToleranceDataType",
            "How far execution may deviate before it is a failure. A tolerance of zero "
            "or less means the Server applies its own.",
            [("Position", Double, "Positional tolerance in metres."),
             ("Orientation", Double, "Orientation tolerance in radians."),
             ("Time", Duration, "Timing tolerance in milliseconds.")])
MotionToleranceDataType = T(3071)

struct_type(3072, "TrajectoryIntentDataType",
            "Execute a time-parameterised path. The Server's own motion kernel runs "
            "it; this interface hands the whole trajectory over in one submission and "
            "does not stream it. That is what makes trajectory execution expressible "
            "here when real-time control is not - see clause 4.3.",
            [("Points", TrajectoryPointDataType, "The trajectory, in ascending "
                                                 "TimeFromStart order.", 1, 0),
             ("PathTolerance", MotionToleranceDataType, "Permitted deviation while "
                                                        "following the path."),
             ("GoalTolerance", MotionToleranceDataType, "Permitted deviation at the "
                                                        "final point."),
             ("GoalTimeTolerance", Duration, "How much later than the final point's "
                                             "TimeFromStart completion may be, in "
                                             "milliseconds.")],
            base=MotionIntentDataType)
TrajectoryIntentDataType = T(3072)

struct_type(3073, "PathWaypointDataType",
            "One waypoint of a Cartesian path, with the blend that applies at it. "
            "Per-waypoint blending is what distinguishes a path from a sequence of "
            "separate linear moves: the robot need not stop between them.",
            [("Pose", Pose3DDataType, "Where the tool centre point passes."),
             ("Blend", BlendDataType, "How this waypoint is left.")])
PathWaypointDataType = T(3073)

struct_type(3074, "CartesianPathIntentDataType",
            "Follow a list of Cartesian waypoints. This is the portable form of a "
            "taught path, and unlike a trajectory it carries no timing: the Server "
            "paces it from the motion constraints.",
            [("Waypoints", PathWaypointDataType, "The path, in order.", 1, 0)],
            base=MotionIntentDataType)
CartesianPathIntentDataType = T(3074)

struct_type(3075, "ForceIntentDataType",
            "Move until contact. The portable subset of the force-controlled moves "
            "every vendor offers: travel along a direction until a contact force is "
            "reached or a distance is exhausted, whichever comes first. Reaching the "
            "distance without contact is a failure, because the intent was to touch "
            "something.",
            [("Direction", Double, "Unit direction of travel (x, y, z) in the frame of "
                                   "the target.", 1, 3),
             ("FrameId", String, "The CoordinateFrame Direction is expressed in; empty "
                                 "for the default work frame."),
             ("ContactForce", Double, "The force in newtons at which contact is "
                                      "declared."),
             ("MaxDistance", Double, "How far to travel before giving up, in metres."),
             ("HoldForce", Boolean, "True to keep pressing at ContactForce after "
                                    "contact rather than stopping.")],
            base=MotionIntentDataType)
ForceIntentDataType = T(3075)

struct_type(3076, "ProcessIntentDataType",
            "Abstract base of the intents that run an application process along a "
            "path. Every process needs the same two things beyond its own parameters: "
            "a reference to the process program or procedure the equipment holds, and "
            "room for the parameters this specification has not standardised.",
            [("ProcessProgram", NodeId_, "The Program or equipment-side procedure to "
                                         "run, or null when the parameters here are "
                                         "sufficient."),
             ("Attributes", KeyValuePair, "Further named parameters the Server "
                                          "declares in its capabilities.", 1, 0)],
            base=MotionIntentDataType, abstract=True)
ProcessIntentDataType = T(3076)

struct_type(3077, "ArcWeldIntentDataType",
            "Lay an arc weld along the path. The parameters are the subset ABB "
            "seamdata/welddata/weavedata, FANUC weld schedules and KUKA ArcTech all "
            "carry. WeldProcedureRef points at a welding procedure specification "
            "(ISO 15609) where the installation works to one; this specification does "
            "not restate its content.",
            [("Voltage", Double, "Arc voltage in volts."),
             ("WireFeedSpeed", Double, "Wire feed speed in metres per minute."),
             ("TravelSpeed", Double, "Tool centre point speed in metres per second."),
             ("GasPreflowTime", Duration, "Shielding gas pre-flow, in milliseconds."),
             ("GasPostflowTime", Duration, "Shielding gas post-flow, in milliseconds."),
             ("ArcStartDelay", Duration, "Delay before travel begins, in milliseconds."),
             ("CraterFillTime", Duration, "Crater fill at the end of the seam, in "
                                          "milliseconds."),
             ("WeaveShape", WeaveShapeEnum, "Oscillation across the seam."),
             ("WeaveAmplitude", Double, "Peak-to-peak weave width in metres."),
             ("WeaveFrequency", Double, "Weave frequency in hertz."),
             ("SeamTrackingEnabled", Boolean, "True to enable seam tracking where the "
                                              "equipment provides it."),
             ("WeldProcedureRef", String, "Identifier of the welding procedure "
                                          "specification this weld works to.")],
            base=ProcessIntentDataType)
ArcWeldIntentDataType = T(3077)

struct_type(3078, "SpotWeldIntentDataType",
            "Make a resistance spot weld at the target. WeldSchedule selects the weld "
            "controller's own program: current and time are the weld controller's "
            "business, and are carried here only where the installation drives them "
            "from the robot.",
            [("WeldSchedule", UInt32, "The weld controller program to run."),
             ("GunForce", Double, "Electrode force in newtons."),
             ("ApproachDistance", Double, "Gun open distance before the weld, in "
                                          "metres."),
             ("RetractDistance", Double, "Gun open distance after the weld, in "
                                         "metres."),
             ("MaterialThickness", Double, "Total stack thickness in metres, where the "
                                           "schedule is chosen adaptively."),
             ("TipDressRequested", Boolean, "True to dress the tips after this weld.")],
            base=ProcessIntentDataType)
SpotWeldIntentDataType = T(3078)

struct_type(3079, "DispenseIntentDataType",
            "Lay a bead of adhesive, sealant or paint along the path. The trigger "
            "distances exist because material does not start and stop instantly: a "
            "Server begins dispensing before the path and stops before its end.",
            [("FlowRate", Double, "Nominal flow in millilitres per minute."),
             ("TriggerOnDistance", Double, "Distance before the path start at which "
                                           "dispensing begins, in metres."),
             ("TriggerOffDistance", Double, "Distance before the path end at which "
                                            "dispensing stops, in metres."),
             ("BeadWidth", Double, "Target bead width in metres."),
             ("MaterialTemperature", Double, "Material temperature in degrees Celsius, "
                                             "for hot-melt work."),
             ("PurgeCycles", UInt32, "Nozzle purge cycles before starting.")],
            base=ProcessIntentDataType)
DispenseIntentDataType = T(3079)

struct_type(3080, "FastenIntentDataType",
            "Drive a fastener at the target. This intent is deliberately THIN: "
            "OPC 40450 and OPC 40451 already define joining and tightening in full, "
            "so Joint references the joint in that model and the result belongs there. "
            "Restating those parameters here would create a second definition of the "
            "same fact.",
            [("Joint", NodeId_, "The joint being fastened, in an OPC UA joining or "
                                "tightening model where one is implemented."),
             ("ProgramNumber", UInt32, "The tightening program the tool is to run."),
             ("TargetTorque", Double, "Target torque in newton metres, where the robot "
                                      "supplies it rather than the tool."),
             ("TargetAngle", Double, "Target angle in radians, for angle-controlled "
                                     "strategies."),
             ("SnugTorque", Double, "Torque at which angle counting begins, in newton "
                                    "metres.")],
            base=ProcessIntentDataType)
FastenIntentDataType = T(3080)

struct_type(3081, "PalletiseIntentDataType",
            "Place an item into a pattern. The pattern itself is a Location, so its "
            "geometry has one definition that a client can read rather than being "
            "recomputed from indices on both sides.",
            [("Pattern", NodeId_, "The Location describing the pallet or pattern."),
             ("Layer", UInt32, "Layer index, counting from zero."),
             ("Row", UInt32, "Row index within the layer, counting from zero."),
             ("Column", UInt32, "Column index within the row, counting from zero."),
             ("ItemOrientation", Double, "Rotation of the item about the pattern "
                                         "normal, in radians.")],
            base=ProcessIntentDataType)
PalletiseIntentDataType = T(3081)

struct_type(3082, "SurfaceFinishIntentDataType",
            "Follow the path pressing into the surface - grinding, polishing, "
            "deburring or sanding. ContactForce is what distinguishes it from a plain "
            "path: the robot yields normal to the surface to hold that force.",
            [("ContactForce", Double, "Force normal to the surface, in newtons."),
             ("FeedRate", Double, "Travel speed along the surface, in metres per "
                                  "second."),
             ("ToolSpeed", Double, "Rotational speed of the tool, in revolutions per "
                                   "minute."),
             ("StepOver", Double, "Lateral offset between adjacent passes, in "
                                  "metres.")],
            base=ProcessIntentDataType)
SurfaceFinishIntentDataType = T(3082)

struct_type(3083, "MissionTransitionDataType",
            "One edge of a mission's step graph, following the step-and-transition "
            "form of an IEC 61131-3 sequential function chart. Condition is an OPC UA "
            "ContentFilter - the base specification's own filter grammar, reused so "
            "that this specification does not invent an expression language for "
            "implementers to write a parser for.",
            [("FromStepId", String, "The step this transition leaves."),
             ("ToStepId", String, "The step this transition enters."),
             ("Condition", ContentFilter, "The condition under which it is taken. An "
                                          "empty filter is always true."),
             ("DivergenceKind", DivergenceKindEnum, "How this transition relates to "
                                                    "the others leaving the same "
                                                    "step.")])
MissionTransitionDataType = T(3083)

struct_type(3084, "KinematicJointDataType",
            "One joint of the kinematic chain: where it sits relative to its "
            "predecessor and which way it acts. OPC 40010-1 describes a robot's "
            "topology and its axes but defines no kinematic chain, so this is additive "
            "rather than a second account of the same thing.",
            [("AxisId", String, "The AxisType this joint corresponds to."),
             ("Kind", AxisKindEnum, "Whether it rotates or translates."),
             ("OriginTransform", Pose3DDataType, "Pose of this joint's frame within "
                                                 "its predecessor's, at zero "
                                                 "position."),
             ("AxisVector", Double, "Unit vector (x, y, z) the joint rotates about or "
                                    "translates along, in its own frame.", 1, 3)])
KinematicJointDataType = T(3084)

# ---------------------------------------------------------------------------
# ObjectTypes (1012+)
# ---------------------------------------------------------------------------
object_type(1012, "SafetyStateType", BaseObjectType,
            "What the robot's safety system is doing, reported so a client can act "
            "sensibly around it. Every member is READ-ONLY and every one is a report: "
            "the safety system enforces these independently, remains effective when "
            "this interface is unreachable, and is not commanded from here. Clause 10 "
            "states the boundary and this type does not cross it.")
SS = 1012
prop_var(SS, "SafetyStateType", "ActiveFunction", SafeMotionFunctionEnum,
         "The safe motion function currently enforced, per IEC 61800-5-2.",
         MR_Mandatory)
prop_var(SS, "SafetyStateType", "EmergencyStopActive", Boolean,
         "True while an emergency stop is asserted.", MR_Mandatory)
prop_var(SS, "SafetyStateType", "ProtectiveStopActive", Boolean,
         "True while a protective stop is asserted.", MR_Mandatory)
prop_var(SS, "SafetyStateType", "SafeSpeedLimitActive", Boolean,
         "True while a safely limited speed is being enforced.", MR_Mandatory)
prop_var(SS, "SafetyStateType", "SafeSpeedLimit", Double,
         "The tool centre point speed limit being enforced, in metres per second. "
         "Meaningful only while SafeSpeedLimitActive. Clause 10.3 requires a Server to "
         "refuse an intent that asks to exceed it.", MR_Mandatory)
prop_var(SS, "SafetyStateType", "SafetyControllerOk", Boolean,
         "False when the safety system reports its own fault. A Server accepts no "
         "intent while it is false.", MR_Mandatory)
prop_var(SS, "SafetyStateType", "LastStopReason", LocalizedText,
         "Why the last stop occurred, for a human. Never parsed.")

object_type(1013, "RealTimeChannelType", BaseObjectType,
            "A high-rate channel this Server can offer, described so a client can open "
            "it. The samples never traverse OPC UA: this brokers the endpoint and "
            "nothing more, in the same way the Vision model brokers a media endpoint "
            "rather than carrying pixels. Clause 4.3 explains why the alternative is "
            "not available.")
RC = 1013
prop_var(RC, "RealTimeChannelType", "ChannelId", String,
         "Identifier unique within the controller.", MR_Mandatory)
prop_var(RC, "RealTimeChannelType", "Transport", RealTimeTransportEnum,
         "The transport this channel speaks.", MR_Mandatory)
prop_var(RC, "RealTimeChannelType", "EndpointUrl", String,
         "Where the channel is reached. Its scheme and form are the transport's, not "
         "this specification's.", MR_Mandatory)
prop_var(RC, "RealTimeChannelType", "Initiator", ChannelInitiatorEnum,
         "Which end opens the connection.", MR_Mandatory)
prop_var(RC, "RealTimeChannelType", "NominalRate", Double,
         "The rate the channel runs at, in hertz.", MR_Mandatory)
prop_var(RC, "RealTimeChannelType", "PayloadDescriptor", String,
         "The recipe, signal list or configuration the transport requires, in the "
         "transport's own form.")
prop_var(RC, "RealTimeChannelType", "RequiredMode", OperationalModeEnum,
         "The operational mode the robot must be in before the channel will carry "
         "motion.", MR_Mandatory)
prop_var(RC, "RealTimeChannelType", "Available", Boolean,
         "True when the channel can be opened now.", MR_Mandatory)
prop_var(RC, "RealTimeChannelType", "LeaseHolder", NodeId_,
         "SessionId of the client currently holding the channel, or null.",
         MR_Mandatory)
prop_var(RC, "RealTimeChannelType", "LeaseExpiry", UtcTime,
         "When the current lease lapses. A lease that is not renewed frees the "
         "channel, so a client that dies does not hold it for good.")

object_type(1014, "RobotDescriptionType", BaseObjectType,
            "Enough of the robot's construction for a client to plan against it "
            "without a second specification: the kinematic chain, the space it can "
            "reach, and what it can carry. OPC 40010-1 describes topology and axes and "
            "defines no kinematic chain and no tool centre point, so this adds rather "
            "than restates - Annex B says which side decides where both are present.")
RD = 1014
prop_var(RD, "RobotDescriptionType", "Manufacturer", LocalizedText,
         "Who made the robot.")
prop_var(RD, "RobotDescriptionType", "Model", String, "The robot's model designation.")
data_var(RD, "RobotDescriptionType", "KinematicChain", KinematicJointDataType,
         "The joints from the base outwards, in order.", MR_Mandatory, valuerank="1")
data_var(RD, "RobotDescriptionType", "MountingPose", Pose3DDataType,
         "Pose of the robot base within the world frame.")
prop_var(RD, "RobotDescriptionType", "ReachRadius", Double,
         "Radius of the reachable workspace from the base, in metres.", MR_Mandatory)
prop_var(RD, "RobotDescriptionType", "PayloadLimit", Double,
         "Largest payload at the mechanical interface, in kilograms.", MR_Mandatory)
prop_var(RD, "RobotDescriptionType", "MaxCartesianSpeed", Double,
         "Largest tool centre point speed the robot will produce, in metres per "
         "second.", MR_Mandatory)
prop_var(RD, "RobotDescriptionType", "MaxCartesianAcceleration", Double,
         "Largest tool centre point acceleration, in metres per second squared.")

# ---------------------------------------------------------------------------
# Members appended to types declared earlier
# ---------------------------------------------------------------------------
obj_member(IC, "IntentControllerType", "SafetyState", T(1012),
           "What the safety system is doing. A client reads this before it plans, and "
           "subscribes to it so that it learns of a stop rather than inferring one "
           "from a refusal.", MR_Mandatory)
obj_member(IC, "IntentControllerType", "Description", T(1014),
           "The robot's kinematics and limits.")
folder_member(IC, "IntentControllerType", "RealTimeChannels",
              "The high-rate channels this Server can broker.", MR_Optional)

method(IC, "IntentControllerType", "OpenRealTimeChannel",
       "Take a lease on a brokered real-time channel. The Server prepares the "
       "transport and returns what the client needs in order to connect; it does not "
       "carry the samples. A lease that is not renewed lapses, which is what stops a "
       "dead client from holding the channel.", MR_Optional,
       inargs=[("ChannelId", String, "The channel to open."),
               ("RequestedLease", Duration, "How long the lease is wanted for, in "
                                            "milliseconds.")],
       outargs=[("Granted", Boolean, "True when the lease was taken."),
                ("EndpointUrl", String, "Where to connect."),
                ("PayloadDescriptor", String, "The transport's own configuration."),
                ("LeaseExpiry", UtcTime, "When the lease lapses.")])
method(IC, "IntentControllerType", "CloseRealTimeChannel",
       "Give up a lease on a brokered channel.", MR_Optional,
       inargs=[("ChannelId", String, "The channel to release.")],
       outargs=[("Released", Boolean, "True when the lease was held and is now "
                                      "released.")])

prop_var(CP, "IntentCapabilitiesType", "TrajectorySupported", Boolean,
         "True when trajectory and Cartesian path intents are accepted.", MR_Mandatory)
prop_var(CP, "IntentCapabilitiesType", "ForceControlSupported", Boolean,
         "True when force intents are accepted and the robot can actually regulate "
         "force. A Server that would ignore the force reports false rather than "
         "accepting an intent it cannot honour.", MR_Mandatory)
prop_var(CP, "IntentCapabilitiesType", "RealTimeChannelsSupported", Boolean,
         "True when the Server brokers real-time channels.", MR_Mandatory)
prop_var(CP, "IntentCapabilitiesType", "MissionBranchingSupported", Boolean,
         "True when mission transitions are evaluated. A Server that reports false "
         "executes the steps in order and ignores any transitions supplied.",
         MR_Mandatory)
prop_var(CP, "IntentCapabilitiesType", "MaxTrajectoryPoints", UInt32,
         "Largest number of points accepted in one trajectory. Zero means the Server "
         "states no limit.")


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
    prefix = "" if n.attrs.get("BrowseNameNamespace") == 0 else "1:"
    a = [f'{tag} NodeId="{T(n.nid)}"', f'BrowseName="{prefix}{sx.escape(n.bname)}"']
    if "SymbolicName" in n.attrs:
        a.append(f'SymbolicName="{sx.escape(n.attrs["SymbolicName"])}"')
    if n.parent is not None:
        a.append(f'ParentNodeId="{n.parent}"')
    for k in ("DataType", "ValueRank", "ArrayDimensions"):
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
           '<!-- OPC UA - Robot Intent companion model. PROVISIONAL NodeIds and namespace '
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

    L = ["# OPC UA — Robot Intent — Annex A: Information model (generated)",
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
    std = os.path.normpath(os.path.join(here, "..", "..", "..", "robot-intent"))
    os.makedirs(std, exist_ok=True)
    with open(os.path.join(std, "Opc.Ua.RobotIntent.NodeSet2.xml"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit())
    with open(os.path.join(std, "Opc.Ua.RobotIntent.NodeIds.csv"), "w",
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
