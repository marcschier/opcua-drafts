#!/usr/bin/env python3
"""
Generator for the OPC UA — OpenUSD Scene Materialization companion specification (WG draft).

Emits, from a single in-code source of truth:
  * ../../../openusd-scene/Opc.Ua.OpenUsdScene.NodeSet2.xml - the information model (UANodeSet)
  * ../../../openusd-scene/Opc.Ua.OpenUsdScene.NodeIds.csv  - the NodeId assignments (SymbolicName,Id,NodeClass)
  * model-reference.md                                      - the generated Annex A (node reference)

The model is a COMPANION specification in its OWN namespace
(http://opcfoundation.org/UA/OpenUSD/Scene/, namespace index 1). Nodes therefore
use `ns=1;i=<n>` NodeIds; references to base UA types use plain `i=<n>`.

NodeIds are PROVISIONAL (final IDs assigned by the OPC Foundation) and follow the
repo convention: ObjectTypes 1001+, VariableTypes 2001+, DataTypes/Enums 3001+,
ReferenceTypes 4001+, EnumStrings = datatype+900, all remaining instance
declarations sequentially from 6001.
"""
from __future__ import annotations
import os
import xml.sax.saxutils as sx

NAMESPACE = "http://opcfoundation.org/UA/OpenUSD/Scene/"
VERSION = "0.1.0"
PUBDATE = "2026-07-21T00:00:00Z"
BASE_UA_VERSION = "1.05.04"
BASE_UA_PUBDATE = "2023-12-15T00:00:00Z"

# --- base UA NodeIds (namespace 0) -----------------------------------------
HasComponent = "i=47"
HasProperty = "i=46"
HasSubtype = "i=45"
Organizes = "i=35"
HasTypeDefinition = "i=40"
HasModellingRule = "i=37"
HasAddIn = "i=17604"
Aggregates = "i=44"
NonHierarchicalReferences = "i=32"
HasInterface = "i=17603"

MR_Mandatory = "i=78"
MR_Optional = "i=80"
MR_OptionalPlaceholder = "i=11508"

BaseObjectType = "i=58"
BaseDataVariableType = "i=63"
PropertyType = "i=68"
FolderType = "i=61"
BaseVariableType = "i=62"
BaseInterfaceType = "i=17602"
Enumeration = "i=29"
Structure = "i=22"
BaseDataType = "i=24"

Boolean = "i=1"
SByte = "i=2"
Int32 = "i=6"
UInt32 = "i=7"
Int64 = "i=8"
Float = "i=10"
Double = "i=11"
String = "i=12"
ByteString = "i=15"
NodeId_ = "i=17"
QualifiedName = "i=20"
LocalizedText = "i=21"
Duration = "i=290"

ALIASES = [
    ("Boolean", Boolean), ("SByte", SByte), ("Int32", Int32), ("UInt32", UInt32),
    ("Int64", Int64), ("Float", Float), ("Double", Double), ("String", String),
    ("ByteString", ByteString), ("NodeId", NodeId_), ("QualifiedName", QualifiedName),
    ("LocalizedText", LocalizedText), ("Duration", Duration), ("BaseDataType", BaseDataType),
    ("HasComponent", HasComponent), ("HasProperty", HasProperty),
    ("HasSubtype", HasSubtype), ("Organizes", Organizes),
    ("HasTypeDefinition", HasTypeDefinition), ("HasModellingRule", HasModellingRule),
    ("HasAddIn", HasAddIn), ("Aggregates", Aggregates),
    ("NonHierarchicalReferences", NonHierarchicalReferences), ("HasInterface", HasInterface),
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


def variable_type(nid, name, base, datatype, valuerank, desc):
    add(nid, "UAVariableType", name, name, desc=desc, category=CAT,
        attrs={"DataType": datatype, "ValueRank": str(valuerank)})
    ref(nid, HasSubtype, base, forward=False)
    return nid


def _member_var(owner, owner_sym, name, datatype, typedef, rule, reftype, desc,
                valuerank="-1"):
    nid = _mid()
    attrs = {"DataType": datatype, "ValueRank": str(valuerank)}
    add(nid, "UAVariable", name, f"{owner_sym}_{name.strip('<>')}", desc=desc, parent=T(owner),
        attrs=attrs)
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid


def prop_var(owner, owner_sym, name, datatype, desc, rule=MR_Optional, valuerank="-1"):
    return _member_var(owner, owner_sym, name, datatype, PropertyType, rule,
                       HasProperty, desc, valuerank)


def component_var(owner, owner_sym, name, datatype, typedef, desc,
                  rule=MR_OptionalPlaceholder, valuerank="-2"):
    return _member_var(owner, owner_sym, name, datatype, typedef, rule,
                       HasComponent, desc, valuerank)


def static_qname_prop(owner, owner_sym, name, ns_index, qname_value, desc):
    """A Property with a fixed value and NO ModellingRule (type-level constant)."""
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


def subtype_datatype(nid, name, base, desc):
    add(nid, "UADataType", name, name, desc=desc, category=CAT_DT)
    ref(nid, HasSubtype, base, forward=False)
    return nid


def struct_datatype(nid, name, desc, fields):
    add(nid, "UADataType", name, name, desc=desc, category=CAT_DT)
    ref(nid, HasSubtype, Structure, forward=False)
    dparts = [f'<Definition Name="{name}">']
    for field_name, datatype, valuerank in fields:
        vr = f' ValueRank="{valuerank}"' if valuerank is not None else ""
        dparts.append(f'<Field Name="{sx.escape(field_name)}" DataType="{datatype}"{vr}/>')
    dparts.append("</Definition>")
    NODES[nid].definition = "".join(dparts)
    return nid


def reference_type(nid, name, base, inverse, desc, symmetric=False):
    add(nid, "UAReferenceType", name, name, desc=desc, category=CAT_REF)
    ref(nid, HasSubtype, base, forward=False)
    NODES[nid].inverse = inverse
    NODES[nid].symmetric = symmetric
    return nid


def well_known(nid, name, typedef, parent_nodeid, desc, reftype=HasComponent):
    add(nid, "UAObject", name, name, desc=desc, parent=parent_nodeid)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, parent_nodeid, forward=False)
    return nid


def instance_folder(nid, name, parent_nid, desc, reftype=HasComponent):
    add(nid, "UAObject", name, name, desc=desc, parent=T(parent_nid))
    ref(nid, HasTypeDefinition, FolderType)
    ref(nid, reftype, T(parent_nid), forward=False)
    ref(parent_nid, reftype, T(nid))
    return nid


# ===========================================================================
# ==============================  MODEL DEFINITION  =========================
# ===========================================================================
CAT = "OpenUSD Scene Materialization"
CAT_DT = "OpenUSD Scene DataTypes"
CAT_REF = "OpenUSD Scene ReferenceTypes"

# ---- DataTypes -------------------------------------------------------------
enum_type(3001, "UsdSpecifierEnum", "USD prim specifier kind.",
          [("Def", 0, None), ("Over", 1, None), ("Class", 2, None)])
enum_type(3002, "UsdVariabilityEnum", "USD attribute variability.",
          [("Varying", 0, None), ("Uniform", 1, None)])
enum_type(3003, "UsdPrimKindEnum", "USD model kind metadata.",
          [("Unspecified", 0, None), ("Model", 1, None), ("Group", 2, None),
           ("Assembly", 3, None), ("Component", 4, None), ("Subcomponent", 5, None)])
enum_type(3004, "UsdListOpTypeEnum", "USD list operation position/type.",
          [("Explicit", 0, None), ("Prepend", 1, None), ("Append", 2, None),
           ("Delete", 3, None), ("Ordered", 4, None)])
enum_type(3005, "UsdArcKindEnum", "USD composition arc kind.",
          [("Reference", 0, None), ("Payload", 1, None), ("Inherit", 2, None),
           ("Specialize", 3, None), ("VariantSet", 4, None), ("Sublayer", 5, None),
           ("Instance", 6, None)])
subtype_datatype(3006, "UsdToken", String, "USD token value represented as a UA String subtype.")
subtype_datatype(3007, "UsdAssetPath", String, "USD asset path represented as a UA String subtype.")
subtype_datatype(3008, "UsdTimeCode", Double, "USD time code represented as a UA Double subtype.")
# Role-carrying value types. Following the OPC UA idiom of subtyping a built-in
# primitive to convey semantics (e.g. Duration : Double), these DataTypes carry
# the USD SdfValueTypeName role that a raw Float/Double array cannot express:
# color3f/normal3f/point3f/vector3f all decompose to a Float[3] but differ only
# by role. Each is the element DataType of a fixed-length array Variable, so the
# renderer-friendly array encoding of the built-in supertype is preserved while
# the role becomes discoverable from the type system (and reversible without the
# UsdTypeName annotation). Generic float3/int3/... tuples with no role beyond
# shape stay as the plain built-in + ArrayDimensions.
subtype_datatype(3013, "UsdColor3f", Float,
                 "USD color3f value (RGB float triple); UA Float subtype carried as a 3-element Float array.")
subtype_datatype(3014, "UsdNormal3f", Float,
                 "USD normal3f value (float triple); UA Float subtype carried as a 3-element Float array.")
subtype_datatype(3015, "UsdPoint3f", Float,
                 "USD point3f value (float triple); UA Float subtype carried as a 3-element Float array.")
subtype_datatype(3016, "UsdVector3f", Float,
                 "USD vector3f value (float triple); UA Float subtype carried as a 3-element Float array.")
subtype_datatype(3017, "UsdTexCoord2f", Float,
                 "USD texCoord2f value (float pair); UA Float subtype carried as a 2-element Float array.")
subtype_datatype(3018, "UsdQuatf", Float,
                 "USD quatf value (float quaternion); UA Float subtype carried as a 4-element Float array.")
subtype_datatype(3019, "UsdQuatd", Double,
                 "USD quatd value (double quaternion); UA Double subtype carried as a 4-element Double array.")
subtype_datatype(3020, "UsdMatrix4d", Double,
                 "USD matrix4d value (row-major); UA Double subtype carried as a 16-element Double array.")
struct_datatype(3010, "UsdLayerOffset", "USD layer offset and scale.",
                [("Offset", Double, None), ("Scale", Double, None)])
struct_datatype(3011, "UsdReferenceSpec", "USD reference specification.",
                [("AssetPath", T(3007), None), ("PrimPath", String, None),
                 ("Offset", Double, None), ("Scale", Double, None)])
struct_datatype(3012, "UsdVariantSelection", "USD variant set selection.",
                [("SetName", String, None), ("VariantName", String, None)])

UsdSpecifierEnum = T(3001)
UsdVariabilityEnum = T(3002)
UsdPrimKindEnum = T(3003)
UsdListOpTypeEnum = T(3004)
UsdArcKindEnum = T(3005)
UsdToken = T(3006)
UsdAssetPath = T(3007)
UsdTimeCode = T(3008)
UsdColor3f = T(3013)
UsdNormal3f = T(3014)
UsdPoint3f = T(3015)
UsdVector3f = T(3016)
UsdTexCoord2f = T(3017)
UsdQuatf = T(3018)
UsdQuatd = T(3019)
UsdMatrix4d = T(3020)

# ---- ReferenceTypes --------------------------------------------------------
reference_type(4001, "UsdRelationshipTarget", NonHierarchicalReferences,
               "UsdRelationshipTargetOf",
               "Browsable relationship edge from a prim or relationship to its target prim.")
reference_type(4002, "UsdConnection", NonHierarchicalReferences,
               "UsdConnectionOf", "Browsable USD attribute-connection edge.")

# ---- VariableTypes ---------------------------------------------------------
variable_type(2001, "UsdAttributeType", BaseDataVariableType, BaseDataType, -2,
              "USD attribute value variable. The runtime DataType and ValueRank reflect the composed Sdf value type.")
A = 2001
prop_var(A, "UsdAttributeType", "UsdTypeName", UsdToken,
         "Exact SdfValueTypeName, e.g. 'float3', 'token', 'asset', or 'color3f[]'.")
prop_var(A, "UsdAttributeType", "Variability", UsdVariabilityEnum,
         "USD attribute variability.")
prop_var(A, "UsdAttributeType", "Custom", Boolean,
         "True if the attribute is a custom USD attribute.")
prop_var(A, "UsdAttributeType", "Namespace", UsdToken,
         "Attribute namespace, e.g. 'primvars' or 'xformOp'.")
prop_var(A, "UsdAttributeType", "Interpolation", UsdToken,
         "Interpolation metadata for primvars and similar authored values.")

# ---- ObjectTypes -----------------------------------------------------------
object_type(1001, "UsdStageType", BaseObjectType,
            "A materialized composed OpenUSD stage.")
STAGE = 1001
prop_var(STAGE, "UsdStageType", "DefaultPrim", UsdToken, "Default prim token.")
prop_var(STAGE, "UsdStageType", "UpAxis", UsdToken, "Stage up axis token.")
prop_var(STAGE, "UsdStageType", "MetersPerUnit", Double, "Stage meters-per-unit metadata.")
prop_var(STAGE, "UsdStageType", "KilogramsPerUnit", Double, "Stage kilograms-per-unit metadata.")
prop_var(STAGE, "UsdStageType", "TimeCodesPerSecond", Double, "Stage time-codes-per-second metadata.")
prop_var(STAGE, "UsdStageType", "StartTimeCode", UsdTimeCode, "Stage start time code.")
prop_var(STAGE, "UsdStageType", "EndTimeCode", UsdTimeCode, "Stage end time code.")
prop_var(STAGE, "UsdStageType", "RootLayerIdentifier", String, "Root layer identifier.")
prop_var(STAGE, "UsdStageType", "Documentation", String, "Stage documentation metadata.")

object_type(1002, "UsdPrimType", BaseObjectType,
            "A materialized composed USD prim (untyped/over base).")
PRIM = 1002
prop_var(PRIM, "UsdPrimType", "Specifier", UsdSpecifierEnum, "Prim specifier.")
prop_var(PRIM, "UsdPrimType", "TypeName", UsdToken, "Composed USD type name token.")
prop_var(PRIM, "UsdPrimType", "Kind", UsdPrimKindEnum, "Model kind metadata.")
prop_var(PRIM, "UsdPrimType", "Active", Boolean, "Whether the prim is active.")
prop_var(PRIM, "UsdPrimType", "Instanceable", Boolean, "Whether the prim is instanceable.")
prop_var(PRIM, "UsdPrimType", "Documentation", String, "Prim documentation metadata.")
placeholder_obj(STAGE, "UsdStageType", "<UsdPrim>", T(PRIM),
                "Composed root prims of the materialized stage.")
placeholder_obj(PRIM, "UsdPrimType", "<UsdPrim>", T(PRIM),
                "Child prims of this composed prim.")
component_var(PRIM, "UsdPrimType", "<UsdAttribute>", BaseDataType, T(2001),
              "USD attributes authored on this prim.")
placeholder_obj(PRIM, "UsdPrimType", "<UsdRelationship>", T(1017),
                "USD relationships authored on this prim.")
applied_schemas = folder_member(PRIM, "UsdPrimType", "AppliedSchemas",
                                "Applied API schema AddIns for this prim.", MR_Optional)
composition = folder_member(PRIM, "UsdPrimType", "Composition",
                            "Composition arcs contributing to this prim.", MR_Optional)
variant_sets = folder_member(PRIM, "UsdPrimType", "VariantSets",
                             "Variant sets authored or composed for this prim.", MR_Optional)
metadata = folder_member(PRIM, "UsdPrimType", "Metadata",
                         "Arbitrary metadata Property variables for this prim.", MR_Optional)

object_type(1003, "UsdTypedType", T(PRIM), "Typed (IsA-schema) prim base.", abstract=True)
object_type(1004, "UsdGeomImageableType", T(1003), "Abstract USD imageable prim base.", abstract=True)
IMAGEABLE = 1004
prop_var(IMAGEABLE, "UsdGeomImageableType", "Visibility", UsdToken, "Visibility token.")
prop_var(IMAGEABLE, "UsdGeomImageableType", "Purpose", UsdToken, "Purpose token.")
object_type(1005, "UsdGeomXformableType", T(IMAGEABLE), "Abstract USD xformable prim base.", abstract=True)
XFORMABLE = 1005
prop_var(XFORMABLE, "UsdGeomXformableType", "XformOpOrder", UsdToken,
         "Ordered xformOp token array.", valuerank="1")
object_type(1006, "UsdGeomXformType", T(XFORMABLE), "USD Xform prim.")
object_type(1007, "UsdGeomScopeType", T(IMAGEABLE), "USD Scope prim.")
object_type(1008, "UsdGeomGprimType", T(XFORMABLE), "Abstract USD geometric prim base.", abstract=True)
GPRIM = 1008
prop_var(GPRIM, "UsdGeomGprimType", "DisplayColor", Float,
         "Display color array (color3f[]).", valuerank="2")
prop_var(GPRIM, "UsdGeomGprimType", "DisplayOpacity", Float,
         "Display opacity array.", valuerank="1")
prop_var(GPRIM, "UsdGeomGprimType", "DoubleSided", Boolean, "Double-sided rendering hint.")
object_type(1009, "UsdGeomMeshType", T(GPRIM), "USD Mesh prim.")
MESH = 1009
prop_var(MESH, "UsdGeomMeshType", "Points", Float, "Mesh points array.", valuerank="2")
prop_var(MESH, "UsdGeomMeshType", "FaceVertexCounts", Int32, "Mesh face vertex counts.", valuerank="1")
prop_var(MESH, "UsdGeomMeshType", "FaceVertexIndices", Int32, "Mesh face vertex indices.", valuerank="1")
object_type(1010, "UsdGeomCylinderType", T(GPRIM), "USD Cylinder prim.")
CYL = 1010
prop_var(CYL, "UsdGeomCylinderType", "Height", Double, "Cylinder height.")
prop_var(CYL, "UsdGeomCylinderType", "Radius", Double, "Cylinder radius.")
prop_var(CYL, "UsdGeomCylinderType", "Axis", UsdToken, "Cylinder axis token.")
object_type(1011, "UsdGeomSphereType", T(GPRIM), "USD Sphere prim.")
prop_var(1011, "UsdGeomSphereType", "Radius", Double, "Sphere radius.")
object_type(1012, "UsdGeomCubeType", T(GPRIM), "USD Cube prim.")
prop_var(1012, "UsdGeomCubeType", "Size", Double, "Cube size.")
object_type(1013, "UsdGeomConeType", T(GPRIM), "USD Cone prim.")
CONE = 1013
prop_var(CONE, "UsdGeomConeType", "Height", Double, "Cone height.")
prop_var(CONE, "UsdGeomConeType", "Radius", Double, "Cone radius.")
prop_var(CONE, "UsdGeomConeType", "Axis", UsdToken, "Cone axis token.")
object_type(1014, "UsdGeomCapsuleType", T(GPRIM), "USD Capsule prim.")
CAPSULE = 1014
prop_var(CAPSULE, "UsdGeomCapsuleType", "Height", Double, "Capsule height.")
prop_var(CAPSULE, "UsdGeomCapsuleType", "Radius", Double, "Capsule radius.")
prop_var(CAPSULE, "UsdGeomCapsuleType", "Axis", UsdToken, "Capsule axis token.")
object_type(1015, "UsdShadeMaterialType", T(1003), "USD Shade material prim hook.")
object_type(1016, "UsdShadeShaderType", T(1003), "USD Shade shader prim hook.")
prop_var(1016, "UsdShadeShaderType", "Info_Id", UsdToken, "Shader implementation identifier token.")
object_type(1017, "UsdRelationshipType", BaseObjectType, "USD relationship object.")
REL = 1017
prop_var(REL, "UsdRelationshipType", "Custom", Boolean, "True if this is a custom relationship.")
prop_var(REL, "UsdRelationshipType", "Targets", NodeId_, "Ordered target NodeId list.", MR_Mandatory, valuerank="1")
prop_var(REL, "UsdRelationshipType", "TargetPaths", String,
         "Ordered SdfPath target strings for fidelity.", MR_Mandatory, valuerank="1")
object_type(1018, "UsdVariantSetType", BaseObjectType, "USD variant set materialization.")
VS = 1018
prop_var(VS, "UsdVariantSetType", "SetName", String, "Variant set name.")
prop_var(VS, "UsdVariantSetType", "Selection", UsdToken, "Selected variant token.")
placeholder_obj(VS, "UsdVariantSetType", "<Variant>", T(PRIM),
                "Variant branch holding prim overrides.")
object_type(1019, "UsdCompositionArcType", BaseObjectType, "USD composition arc materialization.")
ARC = 1019
prop_var(ARC, "UsdCompositionArcType", "ArcKind", UsdArcKindEnum, "Composition arc kind.")
prop_var(ARC, "UsdCompositionArcType", "AssetPath", UsdAssetPath, "Referenced or payload asset path.")
prop_var(ARC, "UsdCompositionArcType", "PrimPath", String, "Target prim path.")
prop_var(ARC, "UsdCompositionArcType", "ListPosition", UsdListOpTypeEnum, "List operation position/type.")
prop_var(ARC, "UsdCompositionArcType", "VariantSet", String, "Variant set name for variant arcs.")
prop_var(ARC, "UsdCompositionArcType", "VariantSelection", String, "Variant selection name.")
object_type(1020, "UsdApiSchemaType", BaseObjectType,
            "Abstract base for applied USD API schema AddIns.", abstract=True)
API = 1020
prop_var(API, "UsdApiSchemaType", "SchemaName", UsdToken, "Applied API schema name.")
object_type(1021, "UsdCollectionAPIType", T(API), "USD CollectionAPI applied API schema.")
COL = 1021
prop_var(COL, "UsdCollectionAPIType", "ExpansionRule", UsdToken, "Collection expansion rule token.")
prop_var(COL, "UsdCollectionAPIType", "IncludesTargets", NodeId_,
         "Included target NodeIds.", valuerank="1")
prop_var(COL, "UsdCollectionAPIType", "ExcludesTargets", NodeId_,
         "Excluded target NodeIds.", valuerank="1")
object_type(1022, "UsdGeoreferenceApiType", T(API),
            "Portable stage georeference applied API schema: the geodetic origin that anchors the "
            "stage's local Cartesian frame to the globe. Vendor-neutral materialization of Cesium "
            "CesiumGeoreferencePrim / NVIDIA WGS84ReferencePositionAPI; maps to OPC UA GPOS "
            "(OPC 10000-211) GlobalPosition + GroundControlPoints (Annex B).")
GEOREF = 1022
prop_var(GEOREF, "UsdGeoreferenceApiType", "Latitude", Double,
         "Origin latitude in decimal degrees (WGS84 unless EpsgCode indicates otherwise).")
prop_var(GEOREF, "UsdGeoreferenceApiType", "Longitude", Double, "Origin longitude in decimal degrees.")
prop_var(GEOREF, "UsdGeoreferenceApiType", "Height", Double, "Origin height above the ellipsoid in metres.")
prop_var(GEOREF, "UsdGeoreferenceApiType", "EpsgCode", UInt32,
         "EPSG coordinate reference system code (0 = local, 4326 = WGS84/GPS).")
prop_var(GEOREF, "UsdGeoreferenceApiType", "TangentPlane", UsdToken,
         "Local tangent-plane convention token (e.g. ENU or NED).")
object_type(1023, "UsdGlobeAnchorApiType", T(API),
            "Portable per-prim globe anchor applied API schema: the geodetic position of an "
            "individual prim, resolved against the stage UsdGeoreferenceApiType. Vendor-neutral "
            "materialization of Cesium CesiumGlobeAnchorAPI / NVIDIA WGS84LocalPositionAPI; maps to "
            "a per-asset OPC UA GPOS GlobalPosition.")
ANCHOR = 1023
prop_var(ANCHOR, "UsdGlobeAnchorApiType", "Latitude", Double, "Prim latitude in decimal degrees.")
prop_var(ANCHOR, "UsdGlobeAnchorApiType", "Longitude", Double, "Prim longitude in decimal degrees.")
prop_var(ANCHOR, "UsdGlobeAnchorApiType", "Height", Double, "Prim height above the ellipsoid in metres.")

placeholder_obj(applied_schemas, "UsdPrimType_AppliedSchemas", "<UsdApiSchema>", T(API),
                "Applied API schema AddIn instances.", reftype=HasAddIn)
placeholder_obj(composition, "UsdPrimType_Composition", "<UsdCompositionArc>", T(ARC),
                "Composition arcs contributing opinions.")
placeholder_obj(variant_sets, "UsdPrimType_VariantSets", "<UsdVariantSet>", T(VS),
                "Variant sets available on this prim.")
_member_var(metadata, "UsdPrimType_Metadata", "<Metadata>", BaseDataType, PropertyType,
            MR_OptionalPlaceholder, HasProperty, "Arbitrary metadata properties.")

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
    if n.cls in ("UAObjectType", "UAVariableType") and n.abstract:
        a.append('IsAbstract="true"')
    if n.cls == "UAReferenceType" and n.symmetric:
        a.append('Symmetric="true"')
    lines = ["  <" + " ".join(a) + ">"]
    lines.append(f"    <DisplayName>{sx.escape(n.display)}</DisplayName>")
    if n.inverse:
        lines.append(f"    <InverseName>{sx.escape(n.inverse)}</InverseName>")
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
           '<!-- OPC UA - OpenUSD Scene Materialization companion model. PROVISIONAL NodeIds and '
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
    return "\n".join(f"{NODES[nid].symbolic},{nid},{NODES[nid].cls[2:]}"
                     for nid in ORDER) + "\n"


def emit_md():
    lines = ["# OPC UA — OpenUSD Scene Materialization — Annex A: Information model (generated)",
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
    std = os.path.normpath(os.path.join(here, "..", "..", "..", "openusd-scene"))
    os.makedirs(std, exist_ok=True)
    with open(os.path.join(std, "Opc.Ua.OpenUsdScene.NodeSet2.xml"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit())
    with open(os.path.join(std, "Opc.Ua.OpenUsdScene.NodeIds.csv"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit_csv())
    with open(os.path.join(here, "model-reference.md"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit_md())
    print(f"Wrote NodeSet ({len(ORDER)} nodes), NodeIds.csv, model-reference.md")


if __name__ == "__main__":
    main()
