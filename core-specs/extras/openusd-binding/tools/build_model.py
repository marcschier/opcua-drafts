#!/usr/bin/env python3
"""
Generator for the OPC UA — OpenUSD Bindings companion specification (WG draft).

Emits, from a single in-code source of truth:
  * ../../../openusd-binding/Opc.Ua.OpenUsdBinding.NodeSet2.xml  - the information model (UANodeSet)
  * ../../../openusd-binding/Opc.Ua.OpenUsdBinding.NodeIds.csv   - the NodeId assignments (SymbolicName,Id,NodeClass)
  * model-reference.md                                           - the generated Annex A (node reference)

The model is a COMPANION specification in its OWN namespace
(http://opcfoundation.org/UA/OpenUSD/, namespace index 1). Nodes therefore use
`ns=1;i=<n>` NodeIds; references to base UA types use plain `i=<n>`.

NodeIds are PROVISIONAL (final IDs assigned by the OPC Foundation) and follow the
repo convention: ObjectTypes 1001+, DataTypes/Enums 3001+, EnumStrings = datatype+900,
all remaining instance declarations sequentially from 6001.

Edition 1 scope (see the research report §0): Part 1 Representation (mandatory
well-known discovery + AddIn) + Part 2 read-only Variable.Value live bindings with
conversion/quality/timestamp HINTS. Methods/Events/PubSub/USD-side mirror are deferred.
The base NodeSet depends ONLY on the base UA model, so a server can adopt it without
pulling in RSL/DI; the RSL transform profile is described in the spec text and carried
by String/URI properties, not by structured RSL NodeSet types.
"""
from __future__ import annotations
import os
import xml.sax.saxutils as sx

NAMESPACE = "http://opcfoundation.org/UA/OpenUSD/"
VERSION = "0.1.0"
PUBDATE = "2026-07-12T00:00:00Z"
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

MR_Mandatory = "i=78"
MR_Optional = "i=80"
MR_OptionalPlaceholder = "i=11508"

BaseObjectType = "i=58"
FolderType = "i=61"
PropertyType = "i=68"
BaseInterfaceType = "i=17602"
Enumeration = "i=29"

Boolean = "i=1"
UInt32 = "i=7"
Double = "i=11"
String = "i=12"
Guid = "i=14"
ByteString = "i=15"
NodeId_ = "i=17"
QualifiedName = "i=20"
LocalizedText = "i=21"
RelativePath = "i=540"
EUInformation = "i=887"

Server = "i=2253"

ALIASES = [
    ("Boolean", Boolean), ("UInt32", UInt32), ("Double", Double), ("String", String),
    ("Guid", Guid), ("ByteString", ByteString), ("NodeId", NodeId_), ("QualifiedName", QualifiedName),
    ("LocalizedText", LocalizedText), ("RelativePath", RelativePath),
    ("EUInformation", EUInformation),
    ("HasComponent", HasComponent), ("HasProperty", HasProperty),
    ("HasSubtype", HasSubtype), ("Organizes", Organizes),
    ("HasTypeDefinition", HasTypeDefinition), ("HasModellingRule", HasModellingRule),
    ("HasInterface", HasInterface),
    ("Mandatory", MR_Mandatory), ("Optional", MR_Optional),
    ("OptionalPlaceholder", MR_OptionalPlaceholder),
]

REFTYPE_ALIAS = {v: k for k, v in ALIASES}
DATATYPE_ALIAS = {v: k for k, v in ALIASES}

# --- node registry ---------------------------------------------------------
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
_next_member = [6001]


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


def _member_var(owner, owner_sym, name, datatype, typedef, rule, reftype, desc,
                valuerank="-1"):
    nid = _mid()
    attrs = {"DataType": datatype, "ValueRank": valuerank}
    add(nid, "UAVariable", name, f"{owner_sym}_{name}", desc=desc, parent=T(owner),
        attrs=attrs)
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid


def prop_var(owner, owner_sym, name, datatype, desc, rule=MR_Optional):
    return _member_var(owner, owner_sym, name, datatype, PropertyType, rule,
                       HasProperty, desc)


def static_qname_prop(owner, owner_sym, name, ns_index, qname_value, desc):
    """A Property with a fixed value and NO ModellingRule (type-level constant,
    e.g. DefaultInstanceBrowseName on an AddIn type)."""
    nid = _mid()
    add(nid, "UAVariable", name, f"{owner_sym}_{name}", desc=desc, parent=T(owner),
        attrs={"DataType": QualifiedName})
    ref(nid, HasTypeDefinition, PropertyType)
    ref(nid, HasProperty, T(owner), forward=False)
    ref(owner, HasProperty, T(nid))
    NODES[nid].value = (
        '<Value><uax:QualifiedName xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd">'
        f'<uax:NamespaceIndex>{ns_index}</uax:NamespaceIndex>'
        f'<uax:Name>{sx.escape(qname_value)}</uax:Name></uax:QualifiedName></Value>')
    return nid


def folder_member(owner, owner_sym, name, desc, rule=MR_Mandatory):
    nid = _mid()
    add(nid, "UAObject", name, f"{owner_sym}_{name}", desc=desc, parent=T(owner))
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, FolderType)
    ref(nid, HasComponent, T(owner), forward=False)
    ref(owner, HasComponent, T(nid))
    return nid


def placeholder_obj(owner, owner_sym, name, typedef, desc,
                    rule=MR_OptionalPlaceholder, reftype=HasComponent):
    nid = _mid()
    add(nid, "UAObject", name, f"{owner_sym}_{name.strip('<>')}", desc=desc,
        parent=T(owner))
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
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
          '<uax:ListOfLocalizedText xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd">']
    for (fname, val, fdesc) in fields:
        vp.append(f"<uax:LocalizedText><uax:Text>{sx.escape(fname)}</uax:Text></uax:LocalizedText>")
    vp.append("</uax:ListOfLocalizedText></Value>")
    NODES[es].value = "".join(vp)
    return nid


def well_known(nid, name, typedef, parent_nodeid, desc, reftype=HasComponent):
    add(nid, "UAObject", name, name, desc=desc, parent=parent_nodeid)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, parent_nodeid, forward=False)
    return nid


def instance_folder(nid, name, parent_nid, desc, reftype=HasComponent):
    # Concrete instance folder under a concrete instance: NO ModellingRule
    # (ModellingRules belong to type InstanceDeclarations, not concrete instances).
    add(nid, "UAObject", name, name, desc=desc, parent=T(parent_nid))
    ref(nid, HasTypeDefinition, FolderType)
    ref(nid, reftype, T(parent_nid), forward=False)
    ref(parent_nid, reftype, T(nid))
    return nid


# ===========================================================================
# ==============================  MODEL DEFINITION  =========================
# ===========================================================================
CAT = "OpenUSD Binding"
CAT_DT = "OpenUSD Binding DataTypes"

# ---- DataTypes (enums) ----------------------------------------------------
enum_type(3001, "OpenUsdIntentProfileEnum",
          "The intent/direction of a binding. UaToUsdTelemetry (read-only UA -> USD) is "
          "the default; UaAlarmToUsd and UaHistoryToUsd are read-only variants; "
          "UsdToUaCommand is the opt-in, authorized control direction (USD -> UA).",
          [("UaToUsdTelemetry", 0, "Read-only UA Variable value drives a USD attribute."),
           ("UaAlarmToUsd", 1, "Read-only A&C condition aspect drives a USD attribute."),
           ("UaHistoryToUsd", 2, "Read-only history (HistoryRead) authored as USD time samples."),
           ("UsdToUaCommand", 3, "Opt-in, authorized USD-side intent drives an UA write/Method call.")])

enum_type(3002, "OpenUsdRenderTargetKindEnum",
          "Classifies the USD render target a live value drives (advisory routing hint).",
          [("Translation", 0, None), ("Rotation", 1, None), ("Scale", 2, None),
           ("Transform", 3, None), ("Visibility", 4, None), ("DisplayColor", 5, None),
           ("EmissiveColor", 6, None), ("Opacity", 7, None), ("Custom", 8, None)])

enum_type(3003, "OpenUsdBadQualityActionEnum",
          "What the connector does with a non-Good source value.",
          [("Skip", 0, "Do not update the target."),
           ("HoldLast", 1, "Keep the last Good value."),
           ("ClearOpinion", 2, "Remove the authored opinion (reveal a weaker layer)."),
           ("Fallback", 3, "Author a configured fallback value.")])

enum_type(3004, "OpenUsdBindingStateEnum",
          "Runtime lifecycle state of a live binding, exposed for diagnostics.",
          [("Disabled", 0, None), ("Unresolved", 1, None), ("Ready", 2, None),
           ("Active", 3, None), ("Degraded", 4, None), ("Error", 5, None)])

OpenUsdIntentProfileEnum = T(3001)
OpenUsdRenderTargetKindEnum = T(3002)
OpenUsdBadQualityActionEnum = T(3003)
OpenUsdBindingStateEnum = T(3004)

# ---- ObjectType: OpenUsdLiveBindingType (1004) ----------------------------
# Defined first so the representation AddIn can reference it as a placeholder typedef.
object_type(1004, "OpenUsdLiveBindingType", BaseObjectType,
            "One read-only live binding: a source OPC UA Variable value drives one "
            "target USD attribute. The binding declaration is portable; the runtime "
            "connector resolves and applies it. The effective runtime identity is "
            "(represented object, BindingDefinitionId).")
B = 1004
prop_var(B, "OpenUsdLiveBindingType", "BindingDefinitionId", Guid,
         "Stable declaration identifier used for override/tombstone matching across "
         "type and instance levels. NOT a runtime instance key.", MR_Mandatory)
prop_var(B, "OpenUsdLiveBindingType", "Enabled", Boolean,
         "False acts as a tombstone that suppresses an inherited binding.", MR_Mandatory)
prop_var(B, "OpenUsdLiveBindingType", "IntentProfile", OpenUsdIntentProfileEnum,
         "The binding intent/direction; default UaToUsdTelemetry.", MR_Mandatory)
# Source locator (exactly one of SourceNodeId / SourceBrowsePath resolves)
prop_var(B, "OpenUsdLiveBindingType", "SourceNodeId", NodeId_,
         "Absolute NodeId of the source Variable (instance-level). Optional; prefer "
         "SourceBrowsePath for type-level declarations.", MR_Optional)
prop_var(B, "OpenUsdLiveBindingType", "SourceBrowsePath", RelativePath,
         "RelativePath to the source Variable, resolved from the represented object. "
         "Preferred, instance-portable form.", MR_Optional)
prop_var(B, "OpenUsdLiveBindingType", "AttributeId", UInt32,
         "Source attribute id; default 13 (Value). Telemetry binds Value only.", MR_Optional)
# Target locator
prop_var(B, "OpenUsdLiveBindingType", "TargetStage", NodeId_,
         "NodeId of the OpenUsdStageType instance holding the target prim.", MR_Mandatory)
prop_var(B, "OpenUsdLiveBindingType", "TargetPrimPath", String,
         "Prim path of the target: absolute, or relative to the representation PrimPath.",
         MR_Mandatory)
prop_var(B, "OpenUsdLiveBindingType", "TargetPropertyName", String,
         "USD attribute name on the target prim, e.g. 'xformOp:rotateZ' or "
         "'primvars:displayColor'.", MR_Mandatory)
prop_var(B, "OpenUsdLiveBindingType", "TargetUsdTypeName", String,
         "Expected USD Sdf value type name, e.g. 'double', 'float', 'bool', 'color3f'.",
         MR_Mandatory)
prop_var(B, "OpenUsdLiveBindingType", "RenderTargetKind", OpenUsdRenderTargetKindEnum,
         "Advisory routing hint for the render target category.", MR_Optional)
# Conversion (scalar + unit; transform is a documented RSL profile carried by URI)
prop_var(B, "OpenUsdLiveBindingType", "ValueSemanticUri", String,
         "Value semantics: scalar/angle/length/point/vector/quaternion/matrix. The "
         "transform profile uses RSL CartesianFrameAngleOrientationType semantics.",
         MR_Optional)
prop_var(B, "OpenUsdLiveBindingType", "Scale", Double,
         "Linear conversion scale: target = Scale * converted + Offset.", MR_Optional)
prop_var(B, "OpenUsdLiveBindingType", "Offset", Double,
         "Linear conversion offset.", MR_Optional)
prop_var(B, "OpenUsdLiveBindingType", "SourceEngineeringUnits", EUInformation,
         "Asserted source engineering units (UNECE).", MR_Optional)
prop_var(B, "OpenUsdLiveBindingType", "TargetEngineeringUnits", EUInformation,
         "Requested target engineering units.", MR_Optional)
# Quality / hints (hints only; Subscription config is per-client, not here)
prop_var(B, "OpenUsdLiveBindingType", "BadQualityAction", OpenUsdBadQualityActionEnum,
         "How the connector treats a non-Good source value. Default Skip.", MR_Optional)
prop_var(B, "OpenUsdLiveBindingType", "SamplingIntervalHint", Double,
         "Requested sampling interval hint in milliseconds. A HINT only; the actual "
         "MonitoredItem parameters are negotiated per client Subscription.", MR_Optional)
# Diagnostics (read-only, server-populated)
prop_var(B, "OpenUsdLiveBindingType", "State", OpenUsdBindingStateEnum,
         "Runtime lifecycle state (diagnostic).", MR_Optional)
prop_var(B, "OpenUsdLiveBindingType", "LastError", LocalizedText,
         "Last operation error text (diagnostic).", MR_Optional)

# ---- ObjectType: OpenUsdStageType (1002) ----------------------------------
object_type(1002, "OpenUsdStageType", BaseObjectType,
            "Describes one OpenUSD stage available to the server. Identity is the "
            "root layer identifier plus, where used, the session layer and resolver "
            "context; the stage Object NodeId is its same-server identity.")
S = 1002
prop_var(S, "OpenUsdStageType", "RootLayerIdentifier", String,
         "Opaque authored root-layer / resolver identifier (NOT necessarily a URI).",
         MR_Mandatory)
prop_var(S, "OpenUsdStageType", "SessionLayerIdentifier", String,
         "Opaque session-layer identifier, if any. Contributes to stage identity.",
         MR_Optional)
prop_var(S, "OpenUsdStageType", "ResolverContext", String,
         "Opaque resolver-context descriptor (e.g. a named context profile).",
         MR_Optional)
prop_var(S, "OpenUsdStageType", "ResolvedRootLayerUri", String,
         "Informative current resolution as a URI, when representable. Not authoritative.",
         MR_Optional)

# ---- ObjectType: OpenUsdRepresentationType (1003, the AddIn) ---------------
object_type(1003, "OpenUsdRepresentationType", BaseObjectType,
            "AddIn that binds a domain Object to a canonical composed USD prim path on "
            "a specific stage. Mounted with HasAddIn; carries live bindings as children.")
R = 1003
static_qname_prop(R, "OpenUsdRepresentationType", "DefaultInstanceBrowseName", 1,
                  "OpenUsdRepresentation",
                  "Default BrowseName for instances of this AddIn (Part 3 AddIn convention).")
prop_var(R, "OpenUsdRepresentationType", "Stage", NodeId_,
         "NodeId of the OpenUsdStageType instance this representation targets.", MR_Mandatory)
prop_var(R, "OpenUsdRepresentationType", "PrimPath", String,
         "Canonical, absolute, composed-stage prim path (SdfPath) for this instance. "
         "Instance-level: a reusable type cannot supply an absolute instance path.",
         MR_Mandatory)
placeholder_obj(R, "OpenUsdRepresentationType", "<Binding>", T(1004),
                "A live binding whose source resolves relative to the represented object.")

# ---- ObjectType: OpenUsdRootType (1001, the well-known root) ---------------
object_type(1001, "OpenUsdRootType", BaseObjectType,
            "Root of the server-wide OpenUSD facility. Contains the stage registry and "
            "the representation registry for deterministic discovery.")
ROOT = 1001
folder_member(ROOT, "OpenUsdRootType", "Stages",
              "Registry of OpenUsdStageType instances available to the server.")
folder_member(ROOT, "OpenUsdRootType", "Representations",
              "Registry that Organizes every OpenUsdRepresentation AddIn in the server, "
              "so a connector can enumerate all representations from one place.")

# ---- Interface: IOpenUsdRepresentedType (1010) ----------------------------
interface_type(1010, "IOpenUsdRepresentedType", BaseInterfaceType,
               "Optional interface advertising that a domain ObjectType participates in "
               "OpenUSD representation. Applied with HasInterface; informative for browsing.")
placeholder_obj(1010, "IOpenUsdRepresentedType", "<OpenUsdRepresentation>", T(1003),
                "Placeholder for the representation AddIn on an implementing instance.",
                reftype=HasComponent)

# NOTE: The mandatory well-known Server/OpenUSD facility (OpenUsdRootType instance with
# its Stages/Representations folders) is created by the SERVER at runtime, not baked into
# this type-only base NodeSet. This keeps the base model free of cross-namespace instance
# references and lets any server mount the facility under Server or Objects. See the spec
# §4.2 (a conforming server SHALL expose it) and the PumpDeviceIntegrationServer sample.


# ===========================================================================
# ============  0.2.0 ADDITIONS (appended so 0.1 NodeIds are stable)  ========
# ===========================================================================
# New DataTypes use explicit NodeIds (3005+); new members are appended here so
# every 0.1 member keeps its original sequential NodeId. Do not reorder.

enum_type(3005, "OpenUsdSignalRoleEnum",
          "Role of the bound signal, mirroring the asset-definition observable/controllable "
          "tagging. Only Controllable signals are eligible for a command binding.",
          [("Observable", 0, "Read-only; drives USD but cannot be commanded."),
           ("Controllable", 1, "May be commanded via an opt-in, authorized command binding.")])

enum_type(3006, "OpenUsdAlarmAspectEnum",
          "For UaAlarmToUsd bindings: which A&C condition aspect drives the target attribute.",
          [("ActiveState", 0, "Condition ActiveState (boolean)."),
           ("Severity", 1, "Condition Severity (numeric)."),
           ("AckedState", 2, "Condition AckedState (boolean)."),
           ("EnabledState", 3, "Condition EnabledState (boolean).")])

enum_type(3007, "OpenUsdDigestAlgorithmEnum",
          "Digest algorithm for OpenUsdStageType.RootLayerDigest (Twin BOM content integrity).",
          [("None", 0, None), ("SHA-256", 1, None), ("SHA-384", 2, None), ("SHA-512", 3, None)])

OpenUsdSignalRoleEnum = T(3005)
OpenUsdAlarmAspectEnum = T(3006)
OpenUsdDigestAlgorithmEnum = T(3007)

# --- OpenUsdLiveBindingType (1004): appended members -----------------------
prop_var(B, "OpenUsdLiveBindingType", "SignalRole", OpenUsdSignalRoleEnum,
         "Observable (read-only, default) or Controllable (eligible for a command binding).",
         MR_Optional)
prop_var(B, "OpenUsdLiveBindingType", "SourceSemanticId", String,
         "Semantic identifier (e.g. ECLASS / IEC CDD IRDI) of the source signal; resolved "
         "against the source's semantic annotations for cross-vendor portability.", MR_Optional)
prop_var(B, "OpenUsdLiveBindingType", "AlarmAspect", OpenUsdAlarmAspectEnum,
         "For UaAlarmToUsd: which A&C condition aspect drives the target.", MR_Optional)
prop_var(B, "OpenUsdLiveBindingType", "TimeSampled", Boolean,
         "For UaHistoryToUsd: author values as USD time samples (playback) rather than "
         "the latest default.", MR_Optional)
prop_var(B, "OpenUsdLiveBindingType", "CommandTargetNodeId", NodeId_,
         "For UsdToUaCommand: the Variable to write, or the Object on which to Call "
         "CommandMethodId.", MR_Optional)
prop_var(B, "OpenUsdLiveBindingType", "CommandMethodId", NodeId_,
         "For UsdToUaCommand: optional Method to invoke instead of a Variable write.",
         MR_Optional)
prop_var(B, "OpenUsdLiveBindingType", "CommandTriggerPropertyName", String,
         "For UsdToUaCommand: the USD attribute whose change is interpreted as the command "
         "intent/value.", MR_Optional)

# --- OpenUsdStageType (1002): appended content-integrity members -----------
prop_var(S, "OpenUsdStageType", "RootLayerDigest", ByteString,
         "Cryptographic digest of the resolved root layer, for content-integrity "
         "verification (Twin BOM). Verify before composing the stage.", MR_Optional)
prop_var(S, "OpenUsdStageType", "RootLayerDigestAlgorithm", OpenUsdDigestAlgorithmEnum,
         "Digest algorithm for RootLayerDigest (default SHA-256).", MR_Optional)
prop_var(S, "OpenUsdStageType", "Signature", ByteString,
         "Optional detached signature over the digest / stage identity, for provenance.",
         MR_Optional)
prop_var(S, "OpenUsdStageType", "ProvenanceUri", String,
         "Optional URI locating provenance / a signed Twin BOM manifest for the stage.",
         MR_Optional)


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
    lines.append(f"  </{tag}>")
    return "\n".join(lines)


def emit():
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<!-- OPC UA - OpenUSD Bindings companion model. PROVISIONAL NodeIds and '
           'namespace (final IDs assigned by the OPC Foundation / working group). -->',
           '<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
           'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" '
           'xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
           '  <NamespaceUris>',
           f'    <Uri>{NAMESPACE}</Uri>',
           '  </NamespaceUris>',
           '  <Models>',
           f'    <Model ModelUri="{NAMESPACE}" Version="{VERSION}" PublicationDate="{PUBDATE}">',
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


def emit_md():
    lines = ["# OPC UA — OpenUSD Bindings — Annex A: Information model (generated)",
             "",
             "> Generated by `build_model.py`. Do not edit by hand. Namespace "
             f"`{NAMESPACE}` (index 1). NodeIds are provisional.",
             "",
             "| NodeId | BrowseName | NodeClass | Description |",
             "|---|---|---|---|"]
    for nid in ORDER:
        n = NODES[nid]
        desc = (n.desc or "").replace("|", "\\|")
        lines.append(f"| ns=1;i={nid} | {n.bname} | {n.cls[2:]} | {desc} |")
    return "\n".join(lines) + "\n"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    std = os.path.normpath(os.path.join(here, "..", "..", "..", "openusd-binding"))
    os.makedirs(std, exist_ok=True)
    with open(os.path.join(std, "Opc.Ua.OpenUsdBinding.NodeSet2.xml"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit())
    with open(os.path.join(std, "Opc.Ua.OpenUsdBinding.NodeIds.csv"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit_csv())
    with open(os.path.join(here, "model-reference.md"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit_md())
    print(f"Wrote NodeSet ({len(ORDER)} nodes), NodeIds.csv, model-reference.md")


if __name__ == "__main__":
    main()
