#!/usr/bin/env python3
"""
Generator for the OPC UA — OpenUSD Bindings companion specification (WG draft).

Emits, from a single in-code source of truth:
  * ../../../openusd-binding/Opc.Ua.OpenUsd.NodeSet2.xml  - the information model (UANodeSet)
  * ../../../openusd-binding/Opc.Ua.OpenUsd.NodeIds.csv   - the NodeId assignments (SymbolicName,Id,NodeClass)
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
VERSION = "0.2.0"
PUBDATE = "2026-07-13T00:00:00Z"
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
FileType = "i=11575"

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

OpenUsdRenderTargetKindEnum = T(3002)
OpenUsdBadQualityActionEnum = T(3003)
OpenUsdBindingStateEnum = T(3004)

# ---- ObjectType: OpenUsdLiveBindingType (1004) ----------------------------
# Defined first so the representation AddIn can reference it as a placeholder typedef.
object_type(1004, "OpenUsdLiveBindingType", BaseObjectType,
            "Abstract base for one read-only live binding: a source OPC UA Variable "
            "value drives one target USD attribute. The binding intent is expressed by "
            "the concrete subtype (ValueChange/Alarm/History/Command), not by an enum. The "
            "declaration is portable; the runtime connector resolves and applies it. The "
            "effective runtime identity is (represented object, BindingDefinitionId).",
            abstract=True)
B = 1004
prop_var(B, "OpenUsdLiveBindingType", "BindingDefinitionId", Guid,
         "Stable declaration identifier used for override/tombstone matching across "
         "type and instance levels. NOT a runtime instance key.", MR_Mandatory)
prop_var(B, "OpenUsdLiveBindingType", "Enabled", Boolean,
         "False acts as a tombstone that suppresses an inherited binding.", MR_Mandatory)
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
          "For OpenUsdAlarmBindingType bindings: which A&C condition aspect drives the target attribute.",
          [("ActiveState", 0, "Condition ActiveState (boolean)."),
           ("Severity", 1, "Condition Severity (numeric)."),
           ("AckedState", 2, "Condition AckedState (boolean)."),
           ("EnabledState", 3, "Condition EnabledState (boolean).")])

enum_type(3007, "OpenUsdDigestAlgorithmEnum",
          "Digest algorithm for OpenUsdStageType.RootLayerDigest (Twin BOM content integrity).",
          [("None", 0, None), ("Sha256", 1, "SHA-256."), ("Sha384", 2, "SHA-384."),
           ("Sha512", 3, "SHA-512.")])

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

# ---- Intent-specific subtypes of OpenUsdLiveBindingType --------------------
# The concrete binding type encodes the intent; intent-specific members live only
# on their subtype (replaces the former IntentProfile enum discriminator).
object_type(1007, "OpenUsdValueChangeBindingType", T(1004),
            "A source UA Variable Value change drives a USD attribute (the default "
            "binding). Adds no members beyond the abstract base; binds the source "
            "Value (AttributeId 13).")

object_type(1008, "OpenUsdAlarmBindingType", T(1004),
            "Read-only OPC UA A&C condition aspect (Part 9) drives a USD attribute.")
AL = 1008
prop_var(AL, "OpenUsdAlarmBindingType", "AlarmAspect", OpenUsdAlarmAspectEnum,
         "Which A&C condition aspect drives the target "
         "(ActiveState/Severity/AckedState/EnabledState).", MR_Optional)

object_type(1009, "OpenUsdHistoryBindingType", T(1004),
            "Read-only history (Part 11 HistoryRead) authored as USD time samples.")
HI = 1009
prop_var(HI, "OpenUsdHistoryBindingType", "TimeSampled", Boolean,
         "Author values as USD time samples (playback) rather than the latest default.",
         MR_Optional)

object_type(1011, "OpenUsdCommandBindingType", T(1004),
            "Opt-in, authorized USD-side intent drives an OPC UA write / Method call (USD -> UA).")
CM = 1011
prop_var(CM, "OpenUsdCommandBindingType", "CommandTargetNodeId", NodeId_,
         "The Variable to write, or the Object on which to Call CommandMethodId.", MR_Mandatory)
prop_var(CM, "OpenUsdCommandBindingType", "CommandMethodId", NodeId_,
         "Optional Method to invoke instead of a Variable write.", MR_Optional)
prop_var(CM, "OpenUsdCommandBindingType", "CommandTriggerPropertyName", String,
         "The USD attribute whose change is interpreted as the command intent/value.",
         MR_Mandatory)

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


# ============  Composition / aggregation (appended; stable NodeIds)  =======
enum_type(3008, "OpenUsdCardinalityEnum",
          "Cardinality of a component binding: 1:1 or 1..n.",
          [("One", 0, "Exactly one component (1:1)."),
           ("Many", 1, "Zero or more components of a type (1..n).")])

enum_type(3009, "OpenUsdCompositionArcEnum",
          "USD composition arc used to place a component prim under its parent.",
          [("Child", 0, "Inline nested prim under the parent prim."),
           ("Reference", 1, "Prim that references the component's external asset."),
           ("Payload", 2, "Prim that payloads (deferred-load) the component's external asset."),
           ("Instance", 3, "Instanceable reference (instanceable=true), for efficient 1..n.")])

OpenUsdCardinalityEnum = T(3008)
OpenUsdCompositionArcEnum = T(3009)

# ---- ObjectType: OpenUsdComponentBindingType (1005) -----------------------
object_type(1005, "OpenUsdComponentBindingType", BaseObjectType,
            "One composition/aggregation binding: maps an OPC UA component relationship of the "
            "represented Object onto a USD composition arc, so a connector assembles the component "
            "prim(s). Carried as a <Component> child of a representation.")
K = 1005
prop_var(K, "OpenUsdComponentBindingType", "BindingDefinitionId", Guid,
         "Stable declaration id for override/tombstone matching.", MR_Mandatory)
prop_var(K, "OpenUsdComponentBindingType", "Enabled", Boolean,
         "False acts as a tombstone that suppresses an inherited component binding.", MR_Mandatory)
prop_var(K, "OpenUsdComponentBindingType", "Cardinality", OpenUsdCardinalityEnum,
         "One (1:1) or Many (1..n).", MR_Mandatory)
prop_var(K, "OpenUsdComponentBindingType", "CompositionArc", OpenUsdCompositionArcEnum,
         "How the component maps into the parent prim: Child, Reference, Payload, Instance.",
         MR_Mandatory)
prop_var(K, "OpenUsdComponentBindingType", "ComponentReferenceType", NodeId_,
         "Aggregating ReferenceType from the represented Object to its component(s); "
         "default HasComponent.", MR_Optional)
prop_var(K, "OpenUsdComponentBindingType", "ComponentBrowsePath", RelativePath,
         "RelativePath to the component Object (One) or to the container from which components "
         "are enumerated (Many).", MR_Optional)
prop_var(K, "OpenUsdComponentBindingType", "ComponentTypeDefinition", NodeId_,
         "Expected component ObjectType; selects children for Many and locates each component's "
         "own representation.", MR_Optional)
prop_var(K, "OpenUsdComponentBindingType", "TargetPrimPath", String,
         "Child prim (One) or parent scope prim (Many), relative to the parent representation "
         "PrimPath (or absolute).", MR_Mandatory)
prop_var(K, "OpenUsdComponentBindingType", "TargetPrimNameSource", String,
         "For Many: how to name each instance prim (BrowseName default, a source-property "
         "RelativePath, or a {...} template).", MR_Optional)
prop_var(K, "OpenUsdComponentBindingType", "ComponentAssetReference", String,
         "For Reference/Payload/Instance: the external USD asset + default prim, e.g. "
         "@pump.usda@</Pump>.", MR_Optional)
prop_var(K, "OpenUsdComponentBindingType", "ComponentRepresentation", NodeId_,
         "NodeId of the component's own OpenUsdRepresentation AddIn (its sub-bindings compose "
         "under the component prim).", MR_Optional)
prop_var(K, "OpenUsdComponentBindingType", "Dynamic", Boolean,
         "The component set may change at runtime (reconciled from model-change events).",
         MR_Optional)
prop_var(K, "OpenUsdComponentBindingType", "ChangeEventSource", NodeId_,
         "Node whose GeneralModelChange/SemanticChange events signal recomposition; default the "
         "Server Object (i=2253).", MR_Optional)
prop_var(K, "OpenUsdComponentBindingType", "ComponentServerUri", String,
         "For a component on another server: the remote Server's application/namespace URI.",
         MR_Optional)
prop_var(K, "OpenUsdComponentBindingType", "ComponentEndpointUrl", String,
         "For a component on another server: the remote endpoint URL (else discovered).",
         MR_Optional)
prop_var(K, "OpenUsdComponentBindingType", "State", OpenUsdBindingStateEnum,
         "Runtime lifecycle state (diagnostic).", MR_Optional)
prop_var(K, "OpenUsdComponentBindingType", "LastError", LocalizedText,
         "Last operation error text (diagnostic).", MR_Optional)

# <Component> placeholder on the representation type (1003)
placeholder_obj(R, "OpenUsdRepresentationType", "<Component>", T(1005),
                "A component/aggregation binding composing this Object's components into the USD "
                "prim tree.")


# ===========================================================================
# ============  0.2.0 (cont.): asset content delivery (optional)  ===========
# ===========================================================================
# Optional server capability (conformance unit OU-AssetDelivery): the server
# serves the artist-authored USD asset layers (the base/root layer plus its full
# dependency closure) through the address space via Part 5 FileType streaming, so
# a generic connector can enumerate, download, verify, cache, compose, and render
# the twin with no external asset resolution — then live-update as usual. Appended
# so every earlier NodeId stays stable; the base NodeSet still depends only on the
# base UA namespace (FileType is a base-UA type).

# ---- DataType: OpenUsdAssetKindEnum (3010) --------------------------------
enum_type(3010, "OpenUsdAssetKindEnum",
          "Role of a served USD asset within a stage's served layer closure.",
          [("RootLayer", 0, "The stage's root/base layer (exactly one served RootLayer per stage)."),
           ("SubLayer", 1, "A sublayer contributing to the root layer's composition."),
           ("Reference", 2, "An asset introduced by a reference arc (e.g. a component's asset)."),
           ("Payload", 3, "An asset introduced by a payload arc (deferred-loaded)."),
           ("Texture", 4, "A texture / image asset referenced by a material."),
           ("Package", 5, "A packaged asset bundle (e.g. USDZ) carrying the whole closure.")])
OpenUsdAssetKindEnum = T(3010)

# ---- ObjectType: OpenUsdAssetType : FileType (1006) -----------------------
# Subtypes the OPC UA Part 5 FileType so the asset node IS the file: its bytes
# are streamed through the node's own Open/Read/Close (no separate File child).
object_type(1006, "OpenUsdAssetType", FileType,
            "One served USD asset/layer: authored content the server delivers through the address "
            "space so a connector can fetch it and compose the stage locally, with no external "
            "resolver. OpenUsdAssetType subtypes the Part 5 FileType, so the asset's bytes are "
            "streamed directly through the node's own Open/Read/Close; AssetIdentifier is the "
            "resolver identifier / relative path used to place the asset in the local cache so "
            "that @...@ references resolve.")
A = 1006
prop_var(A, "OpenUsdAssetType", "AssetIdentifier", String,
         "Resolver identifier / relative path of this asset, matching the stage RootLayerIdentifier "
         "or a ComponentAssetReference asset path; used for @...@ resolution and cache placement.",
         MR_Mandatory)
prop_var(A, "OpenUsdAssetType", "AssetKind", OpenUsdAssetKindEnum,
         "Role of this asset within the stage's served layer closure.", MR_Mandatory)
prop_var(A, "OpenUsdAssetType", "MediaType", String,
         "IANA media type of the content, e.g. 'model/vnd.usda', 'model/vnd.usdz+zip', 'image/png'.",
         MR_Optional)
prop_var(A, "OpenUsdAssetType", "Digest", ByteString,
         "Cryptographic digest of this asset's resolved content, for per-layer integrity "
         "verification. A connector verifies it before composing the asset.",
         MR_Optional)
prop_var(A, "OpenUsdAssetType", "DigestAlgorithm", OpenUsdDigestAlgorithmEnum,
         "Digest algorithm for Digest (default SHA-256).", MR_Optional)
# The streamed bytes are the node's own Part 5 FileType interface (Open/Read/Close/
# GetPosition/SetPosition + Size), inherited by subtyping FileType. Read-only.

# ---- OpenUsdStageType (1002): appended served-asset facility ---------------
folder_member(S, "OpenUsdStageType", "Assets",
              "Optional registry of OpenUsdAssetType instances forming this stage's served layer "
              "closure (exactly one RootLayer). Present only when the server delivers its geometry; "
              "a connector that finds it fetches and composes the stage locally, else it resolves "
              "RootLayerIdentifier externally as before.",
              rule=MR_Optional)

# ---- OpenUsdComponentBindingType (1005): appended component asset pointer ---
prop_var(K, "OpenUsdComponentBindingType", "ComponentAssetNode", NodeId_,
         "NodeId of the OpenUsdAssetType (under the stage's Assets folder) serving this component's "
         "asset, when the server delivers it. Complements ComponentAssetReference.",
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
    with open(os.path.join(std, "Opc.Ua.OpenUsd.NodeSet2.xml"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit())
    with open(os.path.join(std, "Opc.Ua.OpenUsd.NodeIds.csv"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit_csv())
    with open(os.path.join(here, "model-reference.md"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit_md())
    print(f"Wrote NodeSet ({len(ORDER)} nodes), NodeIds.csv, model-reference.md")


if __name__ == "__main__":
    main()
