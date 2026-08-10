#!/usr/bin/env python3
"""
Generator for the OPC UA for Asset Administration Shell companion NodeSet (WG draft).

Emits, from a single in-code source of truth:
  * Opc.Ua.I4AAS.NodeSet2.xml
  * Opc.Ua.I4AAS.NodeIds.csv
  * tools/model-reference.md

This is OPC 30270 for the AAS V3 metamodel, mapped losslessly onto OPC UA together with
an AAS Registry built as a domain extension of the abstract xRegistry base types.

The model uses the namespace http://opcfoundation.org/UA/I4AAS/v3/. The published
http://opcfoundation.org/UA/I4AAS/ namespace identifies the incompatible AAS v1.x
model and therefore cannot be reused. Draft numeric identifiers are provisional;
final NodeIds are assigned by the OPC Foundation.
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

XR_NS = 1          # required model: http://opcfoundation.org/UA/xRegistry/
OWN_NS = 2         # this specification's own namespace (I4AAS)
OWN_MIN = 1001
_next_member = [5000]

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
        # OPC 20020 3.4.1.1: one Category per ConformanceUnit that requires the Node.
        self.category = ((category,) if isinstance(category, str)
                         else tuple(category or ()))
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
def object_type(nid, name, base, desc, category=None, abstract=False):
    add(nid, "UAObjectType", name, name, desc=desc, category=category or _cu(name),
        abstract=abstract)
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

def reserved_var(owner_sym, name, datatype, desc, valuerank="-1"):
    """Consume a published Variable NodeId without declaring it on an ObjectType."""
    nid = _mid()
    add(nid, "UAVariable", name, f"{owner_sym}_{name}", desc=desc,
        attrs={"DataType": datatype, "ValueRank": valuerank})
    ref(nid, HasTypeDefinition, PropertyType)
    return nid

def obj_member(owner, owner_sym, name, typedef, desc, rule=MR_Optional, reftype=HasComponent):
    nid = _mid()
    add(nid, "UAObject", name, f"{owner_sym}_{name.strip('<>')}", desc=desc, parent=T(owner))
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid

def placeholder_obj(owner, owner_sym, name, typedef, desc, rule=MR_OptionalPlaceholder, reftype=HasComponent):
    return obj_member(owner, owner_sym, name, typedef, desc, rule, reftype)

def method(owner, owner_sym, name, desc, rule=MR_Optional, inargs=None, outargs=None,
           category=None):
    nid = _mid()
    add(nid, "UAMethod", name, f"{owner_sym}_{name}", desc=desc, parent=T(owner),
        category=category or _cu(name))
    ref(nid, HasModellingRule, rule)
    ref(nid, HasComponent, T(owner), forward=False)
    ref(owner, HasComponent, T(nid))
    if inargs:
        _args(nid, f"{owner_sym}_{name}", "InputArguments", inargs)
    if outargs:
        _args(nid, f"{owner_sym}_{name}", "OutputArguments", outargs)
    return nid

def _args(method_nid, method_sym, bname, args, instance=False):
    nid = _mid()
    add(nid, "UAVariable", bname, f"{method_sym}_{bname}", parent=T(method_nid), attrs={"DataType": Argument, "ValueRank": "1", "ArrayDimensions": str(len(args)), "_ns0bn": True},
        category=(CAT_INST if instance else None))
    if not instance:
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

def data_type(nid, name, fields, desc, category=None, base=Structure,
              encodings=("Binary", "JSON"), required=()):
    """Emit a Structure DataType with a StructureDefinition and DataTypeEncoding objects.

    fields: list of (FieldName, DataType, Description, valuerank) - valuerank optional
    (default -1 scalar). ``required`` names the fields whose source cardinality is
    mandatory; every other field is emitted with IsOptional="true".
    """
    add(nid, "UADataType", name, name, desc=desc, category=category or _cu(name))
    ref(nid, HasSubtype, base, forward=False)
    required = set(required)
    normalized = []
    parts = [f'<Definition Name="{sx.escape(name)}">']
    for f in fields:
        fname, fdt, fdesc = f[0], f[1], f[2]
        frank = f[3] if len(f) > 3 else -1
        optional = fname not in required
        normalized.append((fname, fdt, fdesc, frank, optional))
        attrs = f'Name="{sx.escape(fname)}" DataType="{fdt}"'
        if frank is not None and frank >= 0:
            attrs += f' ValueRank="{frank}"'
        if optional:
            attrs += ' IsOptional="true"'
        parts.append(f"<Field {attrs}>")
        if fdesc:
            parts.append(f"<Description>{sx.escape(fdesc)}</Description>")
        parts.append("</Field>")
    parts.append("</Definition>")
    DATATYPE_FIELDS[nid] = normalized
    NODES[nid].definition = "".join(parts)
    for enc in encodings:
        enc_nid = _mid()
        bn = f"Default {enc}"
        add(enc_nid, "UAObject", bn, f"{name}_Default{enc}", parent=T(nid), attrs={"_ns0bn": True})
        ref(enc_nid, HasTypeDefinition, DataTypeEncodingType)
        ref(enc_nid, HasEncoding, T(nid), forward=False)
        ref(nid, HasEncoding, T(enc_nid))
    return nid

def common_attrs(nid, sym, name_rule=MR_Optional):
    """The xRegistry attributes common to a registry, group and resource entity."""
    prop_var(nid, sym, "Xid", String, "xRegistry relative identifier (xid): the entity's stable path within the registry, independent of the hosting endpoint.")
    prop_var(nid, sym, "Epoch", UInt32, "xRegistry epoch: a counter that increments on every change to the entity.")
    prop_var(nid, sym, "Name", String,
             "Human-readable name of the entity, and the source of its DisplayName. Where the entity's source "
             "identity is itself readable - a namespace URI, an authored asset identifier - Name is that identity "
             "verbatim, so a Client that shows only an identifier and a name still shows something a human "
             "recognizes.", rule=name_rule)
    prop_var(nid, sym, "Description", String, "Human-readable description of the entity.")
    prop_var(nid, sym, "Documentation", String, "URL to human-readable documentation for the entity.")
    obj_member(nid, sym, "Labels", T(63003),
               "The entity's extensible xRegistry labels/attributes, exposed as an AttributesType container: each label "
               "is a browsable PropertyType Variable, added and removed with the container's AddAttribute/RemoveAttribute "
               "Methods. Deleted together with the entity.", rule=MR_Optional)
    prop_var(nid, sym, "CreatedAt", DateTime, "UTC timestamp when the entity was created.")
    prop_var(nid, sym, "ModifiedAt", DateTime, "UTC timestamp when the entity was last modified.")


Enumeration = "i=29"
Server = "i=2253"
HasOrderedComponent = "i=49"
Decimal = "i=50"
Integer = "i=27"
UInteger = "i=28"
Number = "i=26"
DateString = "i=12881"
TimeString = "i=12880"
DurationString = "i=12879"
BaseDataType = "i=24"

def X(nid):
    """Reference to a node in the abstract xRegistry base namespace (required model)."""
    return f"ns={XR_NS};i={nid}"

XRegistry_RegistryType = X(63000)
XRegistry_GroupType = X(63001)
XRegistry_ResourceType = X(63002)
XRegistry_AttributesType = X(63003)

def ordered_placeholder(owner, owner_sym, name, typedef, desc):
    """Declare a list child through HasComponent.

    HasOrderedComponent is a subtype of HasComponent and is selected on an instance when
    orderRelevant is true. Declaring the base ReferenceType permits both legal instance forms.
    """
    return obj_member(owner, owner_sym, name, typedef, desc, MR_OptionalPlaceholder, HasComponent)


def instance_method(owner, owner_sym, name, decl_nid, desc, inargs=None, outargs=None):
    """Materialize a concrete method under a well-known instance object, so that loading the
    NodeSet yields a functional registry rather than a bare instance. Instances carry no
    HasModellingRule; MethodDeclarationId links to the type's method for the signature."""
    nid = _mid()
    add(nid, "UAMethod", name, f"{owner_sym}_{name}", desc=desc, parent=T(owner),
        category=CAT_INST, attrs={"MethodDeclarationId": T(decl_nid)})
    ref(nid, HasComponent, T(owner), forward=False)
    ref(owner, HasComponent, T(nid))
    if inargs:
        _args(nid, f"{owner_sym}_{name}", "InputArguments", inargs, instance=True)
    if outargs:
        _args(nid, f"{owner_sym}_{name}", "OutputArguments", outargs, instance=True)
    return nid

def enum_type(nid, name, members, desc, category=None):
    """Emit an Enumeration DataType with a Definition listing its members."""
    add(nid, "UADataType", name, name, desc=desc, category=category or _cu(name))
    ref(nid, HasSubtype, Enumeration, forward=False)
    DATATYPE_FIELDS[nid] = [(m[0], "", m[2] if len(m) > 2 else "", -1) for m in members]
    parts = [f'<Definition Name="{sx.escape(name)}">']
    for m in members:
        mname, mval = m[0], m[1]
        mdesc = m[2] if len(m) > 2 else ""
        parts.append(f'<Field Name="{sx.escape(mname)}" Value="{mval}">')
        if mdesc:
            parts.append(f"<Description>{sx.escape(mdesc)}</Description>")
        parts.append("</Field>")
    parts.append("</Definition>")
    NODES[nid].definition = "".join(parts)
    return nid

# Model
# ---------------------------------------------------------------------------
# Conformance units
# ---------------------------------------------------------------------------
# OPC 20020 3.4.1.1: every Type Node and Method names the ConformanceUnits that require it
# in the AddressSpace, as Category elements. This table is the executable form of the
# conformance clause; a unit missing here cannot appear in the document.
CU_METAMODEL = "AAS-Metamodel"
CU_ELEMENTS = "AAS-SubmodelElements"
CU_VALUES = "AAS-ValueFidelity"
CU_ROUNDTRIP = "AAS-LosslessRoundTrip"
CU_MATERIALIZE = "AAS-InstanceMaterialization"
CU_REGISTRY = "AAS-Registry"
CU_IDENTITY = "AAS-RegistryIdentity"
CU_VERSIONING = "AAS-RegistryVersioning"
CU_DISCOVERY = "AAS-Discovery"
CU_FEDERATION = "AAS-Federation"
CU_DISCLOSURE = "AAS-DisclosureTiers"
CU_PACKAGES = "AAS-Packages"
CU_PACKAGE_INTEGRITY = "AAS-PackageIntegrity"
CU_UPDATEABLE = "AAS-UpdateableRegistry"
CU_ENVEXPORT = "AAS-EnvironmentExport"
CU_INVOKE = "AAS-OperationInvoke"

ALL_CONFORMANCE_UNITS = (
    CU_METAMODEL, CU_ELEMENTS, CU_VALUES, CU_ROUNDTRIP, CU_MATERIALIZE,
    CU_REGISTRY, CU_IDENTITY, CU_VERSIONING, CU_DISCOVERY, CU_FEDERATION,
    CU_DISCLOSURE, CU_PACKAGES, CU_PACKAGE_INTEGRITY, CU_UPDATEABLE,
    CU_ENVEXPORT, CU_INVOKE,
)

CU_BY_NAME = {
    # metamodel
    "AASReferableType": (CU_METAMODEL,), "AASIdentifiableType": (CU_METAMODEL,),
    "AASHasSemanticsType": (CU_METAMODEL,), "AASHasKindType": (CU_METAMODEL,),
    "AASHasDataSpecificationType": (CU_METAMODEL,), "AASQualifiableType": (CU_METAMODEL,),
    "AASEnvironmentType": (CU_METAMODEL, CU_MATERIALIZE),
    "AASType": (CU_METAMODEL, CU_MATERIALIZE),
    "AASAssetInformationType": (CU_METAMODEL,),
    "AASSubmodelType": (CU_METAMODEL, CU_MATERIALIZE),
    "AASSubmodelElementType": (CU_ELEMENTS,),
    "AASPropertyType": (CU_ELEMENTS, CU_VALUES),
    "AASMultiLanguagePropertyType": (CU_ELEMENTS, CU_VALUES),
    "AASRangeType": (CU_ELEMENTS, CU_VALUES),
    "AASBlobType": (CU_ELEMENTS, CU_VALUES),
    "AASFileType": (CU_ELEMENTS, CU_VALUES),
    "AASReferenceElementType": (CU_ELEMENTS,),
    "AASRelationshipElementType": (CU_ELEMENTS,),
    "AASAnnotatedRelationshipElementType": (CU_ELEMENTS,),
    "AASSubmodelElementCollectionType": (CU_ELEMENTS, CU_ROUNDTRIP),
    "AASSubmodelElementListType": (CU_ELEMENTS, CU_ROUNDTRIP),
    "AASEntityType": (CU_ELEMENTS,),
    "AASBasicEventElementType": (CU_ELEMENTS,),
    "AASOperationType": (CU_ELEMENTS,),
    "AASCapabilityType": (CU_ELEMENTS,),
    "AASConceptDescriptionType": (CU_METAMODEL,),
    # registry
    "AASRegistryType": (CU_REGISTRY, CU_DISCOVERY, CU_UPDATEABLE, CU_ENVEXPORT),
    "AASShellGroupType": (CU_REGISTRY, CU_IDENTITY, CU_DISCOVERY, CU_DISCLOSURE),
    "AASSubmodelFileType": (CU_REGISTRY, CU_IDENTITY, CU_VERSIONING, CU_DISCLOSURE, CU_UPDATEABLE),
    "AASSubmodelTemplateGroupType": (CU_REGISTRY, CU_IDENTITY),
    "AASConceptDictionaryGroupType": (CU_REGISTRY, CU_IDENTITY),
    "AASConceptDescriptionFileType": (CU_REGISTRY, CU_IDENTITY, CU_UPDATEABLE),
    "AASPackageStoreGroupType": (CU_PACKAGES, CU_IDENTITY),
    "AASPackageFileType": (
        CU_PACKAGES, CU_IDENTITY, CU_PACKAGE_INTEGRITY),
    "AASEnvironmentFileType": (CU_ENVEXPORT, CU_IDENTITY),
    "AASRegistry": (CU_REGISTRY,),
}

def _cu(name):
    return CU_BY_NAME.get(name, ())

CAT_INST = "AAS Registry Instances"

# ---------------------------------------------------------------------------
# DataTypes - enumerations
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# DataTypes - the xsd value carriers
# ---------------------------------------------------------------------------
# Clause 7.1 assigns each of the 30 DataTypeDefXsd values one OPC UA DataType, and no
# DataType to two of them. Where a built-in denotes the xsd type on its own it is used;
# where two xsd types would otherwise share one built-in, a subtype is defined here.
def xsd_type(nid, name, base, desc):
    add(nid, "UADataType", name, name, desc=desc, category=(CU_VALUES,))
    ref(nid, HasSubtype, base, forward=False)
    return T(nid)

xsd_type(1180, "AASAnyUri", String,
         "An xs:anyURI value. A subtype of String, since String carries xs:string.")
xsd_type(1181, "AASHexBinary", ByteString,
         "An xs:hexBinary value. ByteString carries xs:base64Binary, whose octets are the same, so "
         "the hexadecimal form is carried by this subtype.")
xsd_type(1182, "AASNonPositiveInteger", Integer,
         "An xs:nonPositiveInteger value: an integer at most zero.")
xsd_type(1183, "AASNegativeInteger", T(1182),
         "An xs:negativeInteger value: an integer below zero. A subtype of AASNonPositiveInteger, "
         "following the xsd restriction hierarchy.")
xsd_type(1184, "AASPositiveInteger", UInteger,
         "An xs:positiveInteger value: an integer above zero. A subtype of UInteger, which carries "
         "xs:nonNegativeInteger.")
xsd_type(1185, "AASGYear", String,
         "An xs:gYear value, such as 2026. A Gregorian year denotes a period, for which OPC UA has "
         "no DataType, so the value is its lexical form.")
xsd_type(1186, "AASGYearMonth", String,
         "An xs:gYearMonth value, such as 2026-08.")
xsd_type(1187, "AASGMonth", String,
         "An xs:gMonth value, such as --08.")
xsd_type(1188, "AASGMonthDay", String,
         "An xs:gMonthDay value, such as --08-07.")
xsd_type(1189, "AASGDay", String,
         "An xs:gDay value, such as ---07.")

add(1199, "UADataType", "AASValueString", "AASValueString",
    desc="The xsd lexical form of a value whose declared type is carried in a sibling field of the "
         "same Structure. A Structure field has one static DataType and cannot vary with a declared "
         "type, so a qualifier, an extension or a data specification carries its value lexically and "
         "its sibling ValueType or DataType field states how to read it. A subtype of String, as OPC UA defines "
         "DecimalString and DurationString. It is never the DataType of a Variable; a value node "
         "carries the DataType clause 7.1 assigns to its declared xsd type.",
    category=(CU_VALUES,))
ref(1199, HasSubtype, String, forward=False)

enum_type(1200, "AASAssetKindDataType", [
    ("Type", 0, "The shell describes a product model rather than an individual item."),
    ("Instance", 1, "The shell describes one individual physical item."),
    ("Batch", 2, "The shell describes a production lot."),
    ("Role", 3, "The shell describes a role rather than a physical asset."),
    ("NotApplicable", 4, "Asset kind does not apply."),
], "Whether a shell describes a product model, an individual item, a batch, a role, or none of these. The three granularity levels a product passport is issued at map onto Type, Instance and Batch.")

enum_type(1201, "AASModellingKindDataType", [
    ("Template", 0, "Defines the shape other elements are built from; carries no values for an individual asset."),
    ("Instance", 1, "Carries values for one asset."),
], "Whether an element defines a shape or carries values.")

enum_type(1202, "AASEntityTypeDataType", [
    ("CoManagedEntity", 0, "The entity has no shell of its own and is managed within its parent."),
    ("SelfManagedEntity", 1, "The entity has its own shell, identified by GlobalAssetId, so a bill of material is traversable across organizations."),
], "Whether a composition entity is managed within its parent or has a shell of its own.")

enum_type(1203, "AASDirectionDataType", [
    ("Input", 0, "The event is consumed by the element."),
    ("Output", 1, "The event is produced by the element."),
], "The direction of an event element.")

enum_type(1204, "AASStateOfEventDataType", [
    ("Off", 0, "The event source is inactive."),
    ("On", 1, "The event source is active."),
], "Whether an event element is currently active.")

enum_type(1205, "AASQualifierKindDataType", [
    ("ValueQualifier", 0, "Qualifies the value and may change during the element's lifetime."),
    ("ConceptQualifier", 1, "Qualifies the concept and is invariant."),
    ("TemplateQualifier", 2, "Qualifies the template the element was built from."),
], "What a qualifier qualifies, and therefore whether it may change.")

enum_type(1206, "AASReferenceTypesDataType", [
    ("ExternalReference", 0, "Points at something outside the metamodel."),
    ("ModelReference", 1, "Points at a node within the model, navigated key by key."),
], "Whether a reference addresses something inside the model or outside it.")

enum_type(1207, "AASKeyTypesDataType", [
    ("AnnotatedRelationshipElement", 0, ""), ("AssetAdministrationShell", 1, ""),
    ("BasicEventElement", 2, ""), ("Blob", 3, ""), ("Capability", 4, ""),
    ("ConceptDescription", 5, ""), ("DataElement", 6, ""), ("Entity", 7, ""),
    ("EventElement", 8, ""), ("File", 9, ""), ("FragmentReference", 10, ""),
    ("GlobalReference", 11, ""), ("Identifiable", 12, ""), ("MultiLanguageProperty", 13, ""),
    ("Operation", 14, ""), ("Property", 15, ""), ("Range", 16, ""), ("Referable", 17, ""),
    ("ReferenceElement", 18, ""), ("RelationshipElement", 19, ""), ("Submodel", 20, ""),
    ("SubmodelElement", 21, ""), ("SubmodelElementCollection", 22, ""),
    ("SubmodelElementList", 23, ""),
], "The kind of thing a reference key addresses. The enumeration is closed: a value outside it cannot round-trip, so an implementation rejects it rather than dropping it.")

enum_type(1208, "AASDataTypeDefXsdDataType", [
    ("AnyUri", 0, ""), ("Base64Binary", 1, ""), ("Boolean", 2, ""), ("Byte", 3, ""),
    ("Date", 4, ""), ("DateTime", 5, ""), ("Decimal", 6, ""),
    ("Double", 7, ""), ("Duration", 8, ""),
    ("Float", 9, ""), ("GDay", 10, ""), ("GMonth", 11, ""), ("GMonthDay", 12, ""),
    ("GYear", 13, ""), ("GYearMonth", 14, ""),
    ("HexBinary", 15, ""), ("Int", 16, ""), ("Integer", 17, ""),
    ("Long", 18, ""), ("NegativeInteger", 19, ""), ("NonNegativeInteger", 20, ""),
    ("NonPositiveInteger", 21, ""), ("PositiveInteger", 22, ""), ("Short", 23, ""),
    ("String", 24, ""), ("Time", 25, ""), ("UnsignedByte", 26, ""), ("UnsignedInt", 27, ""),
    ("UnsignedLong", 28, ""), ("UnsignedShort", 29, ""),
], "The xsd type a value is expressed in. All thirty of the metamodel's values are listed. Clause 7.1 assigns each one OPC UA DataType, and no DataType to two of them.")

enum_type(1209, "AASDataTypeIec61360DataType", [
    ("Blob", 0, ""), ("Boolean", 1, ""), ("Date", 2, ""), ("File", 3, ""), ("Html", 4, ""),
    ("IntegerCount", 5, ""), ("IntegerCurrency", 6, ""), ("IntegerMeasure", 7, ""),
    ("Irdi", 8, ""), ("Iri", 9, ""), ("Rational", 10, ""), ("RationalMeasure", 11, ""),
    ("RealCount", 12, ""), ("RealCurrency", 13, ""), ("RealMeasure", 14, ""),
    ("String", 15, ""), ("StringTranslatable", 16, ""), ("Time", 17, ""), ("Timestamp", 18, ""),
], "The data type of a concept definition expressed in the IEC 61360 data specification.")

enum_type(1210, "AASSubmodelElementsDataType", [
    ("AnnotatedRelationshipElement", 0, ""), ("BasicEventElement", 1, ""), ("Blob", 2, ""),
    ("Capability", 3, ""), ("DataElement", 4, ""), ("Entity", 5, ""), ("EventElement", 6, ""),
    ("File", 7, ""), ("MultiLanguageProperty", 8, ""), ("Operation", 9, ""), ("Property", 10, ""),
    ("Range", 11, ""), ("ReferenceElement", 12, ""), ("RelationshipElement", 13, ""),
    ("SubmodelElement", 14, ""), ("SubmodelElementCollection", 15, ""), ("SubmodelElementList", 16, ""),
], "The element kind a SubmodelElementList constrains its members to.")

enum_type(1211, "AASDisclosureTierDataType", [
    ("Public", 0, "Readable without authentication."),
    ("Controlled", 1, "Requires an authenticated role."),
], "Whether an entity is readable without authentication. It advertises the tier so a Consumer can discover it; it does not enforce it.")

enum_type(1212, "AASLoadStateDataType", [
    ("Unloaded", 0, "The document is stored but not materialized."),
    ("Loading", 1, "A shadow generation is being prepared and is not yet visible."),
    ("Active", 2, "The materialized nodes are the ones a Client sees."),
    ("Superseded", 3, "A newer generation has been switched in; this one still serves retained work."),
    ("Retiring", 4, "The superseded generation is draining and its nodes will be removed."),
    ("Retired", 5, "The generation's nodes have been removed."),
    ("Failed", 6, "The document did not validate or did not materialize. The stored document is kept and the previously active generation, where there was one, keeps serving."),
], "The materialization state of one stored document under the updateable registry profile.", category=(CU_UPDATEABLE,))

enum_type(1213, "AASMaterializationOutcomeDataType", [
    ("Unchanged", 0, "The document's digest was unchanged, so it was not re-materialized."),
    ("Materialized", 1, "A new generation was prepared and switched in."),
    ("Retired", 2, "The document's projection was removed."),
    ("Failed", 3, "The document did not validate or did not materialize. Diagnostic says why."),
], "What a Materialize call did to one document.", category=(CU_UPDATEABLE,))

# ---------------------------------------------------------------------------
# DataTypes - structures
# ---------------------------------------------------------------------------
data_type(1220, "AASKeyDataType", [
    ("Type", T(1207), "The kind of thing this key addresses."),
    ("Value", String, "The identifier value at this key."),
], "One step of a reference path. Keys are ordered, and the order is part of the reference's meaning.",
    required=("Type", "Value"))

data_type(1221, "AASReferenceDataType", [
    ("Type", T(1206), "Whether the reference is external or navigates the model."),
    ("ReferredSemanticId", T(1221), "The semantic identifier of the thing referred to, where known."),
    ("Keys", T(1220), "The ordered key path. At least one key is present.", 1),
], "A reference, external or model-navigating, expressed as an ordered key path.",
    required=("Type", "Keys"))

data_type(1222, "AASLangStringDataType", [
    ("Language", String, "BCP 47 language tag."),
    ("Text", String, "The text in that language."),
], "One language-tagged string. A multi-language value is an array of these, and the array order is preserved.",
    required=("Language", "Text"))

data_type(1223, "AASSpecificAssetIdDataType", [
    ("Name", String, "The key name, for example serialNumber or manufacturerPartId."),
    ("Value", String, "The key value."),
    ("ExternalSubjectId", T(1221), "The subject this key is disclosed to, where the key is not public."),
    ("SemanticId", T(1221), "The concept this key is an occurrence of."),
    ("SupplementalSemanticIds", T(1221), "Further concepts this key corresponds to.", 1),
], "A domain-specific key an asset is discoverable by.",
    required=("Name", "Value"))

data_type(1224, "AASAdministrativeInformationDataType", [
    ("Version", String, "Version label."),
    ("Revision", String, "Revision label; only meaningful when Version is present."),
    ("Creator", T(1221), "The party that created the entity."),
    ("TemplateId", String, "The template the entity was built from."),
    ("EmbeddedDataSpecifications", T(1226), "Data specifications carried by this administrative information.", 1),
], "Administrative information. It records a single current revision: the entity's history is carried by the registry, which the metamodel has no equivalent of.")

data_type(1225, "AASQualifierDataType", [
    ("Kind", T(1205), "What the qualifier qualifies."),
    ("Type", String, "The qualifier type name."),
    ("ValueType", T(1208), "The xsd type the value is expressed in."),
    ("Value", T(1199), "The value in the xsd lexical form of the type declared in the sibling ValueType field, because a Structure field has one static DataType and cannot vary with a declared type."),
    ("ValueId", T(1221), "A reference to the value, where it is itself an identified concept."),
    ("SemanticId", T(1221), "The concept this qualifier is an occurrence of."),
    ("SupplementalSemanticIds", T(1221), "Further concepts this qualifier corresponds to.", 1),
], "A qualifier constraining or annotating an element.",
    required=("Type", "ValueType"))

data_type(1226, "AASEmbeddedDataSpecificationDataType", [
    ("DataSpecification", T(1221), "Reference to the data specification template."),
    ("DataSpecificationContent", T(1227), "The content, in the IEC 61360 data specification."),
], "A data specification carried by an element, paired with its content.",
    required=("DataSpecification", "DataSpecificationContent"))

data_type(1227, "AASDataSpecificationIec61360DataType", [
    ("PreferredName", T(1222), "Preferred name per language.", 1),
    ("ShortName", T(1222), "Short name per language.", 1),
    ("Unit", String, "Unit symbol."),
    ("UnitId", T(1221), "Reference to the unit concept."),
    ("SourceOfDefinition", String, "Where the definition comes from."),
    ("Symbol", String, "Symbol for the concept."),
    ("DataType", T(1209), "The IEC 61360 data type."),
    ("Definition", T(1222), "Definition per language.", 1),
    ("ValueFormat", String, "Format of the value."),
    ("ValueList", T(1235), "Permitted values and the references identifying their meanings."),
    ("Value", T(1199), "The value in the xsd lexical form of the type declared in the sibling DataType field, because a Structure field has one static DataType and cannot vary with a declared type."),
    ("LevelType", T(1236), "Which of min, nom, typ and max apply."),
], "The IEC 61360 data specification content of a concept definition.",
    required=("PreferredName",))

data_type(1228, "AASExtensionDataType", [
    ("Name", String, "Extension name."),
    ("ValueType", T(1208), "The xsd type the value is expressed in."),
    ("Value", T(1199), "The value in the xsd lexical form of the type declared in the sibling ValueType field, because a Structure field has one static DataType and cannot vary with a declared type."),
    ("RefersTo", T(1221), "What the extension refers to.", 1),
    ("SemanticId", T(1221), "The concept this extension is an occurrence of."),
    ("SupplementalSemanticIds", T(1221), "Further concepts this extension corresponds to.", 1),
], "A proprietary extension carried on a Referable. Extensions round-trip verbatim; a reader that does not understand one preserves it unchanged.",
    required=("Name",))

data_type(1229, "AASResourceDataType", [
    ("Path", String, "Path or URL to the resource."),
    ("ContentType", String, "Media type of the resource."),
], "A pointer to external content, such as a thumbnail.",
    required=("Path",))

data_type(1230, "AASOperationVariableDataType", [
    ("ValueNodeId", NodeId, "The direct HasComponent child of the Operation that carries this variable's value."),
], "One input, output or in-out variable of an operation, carried as a reference to the element node that holds it so that the element's own representation is not duplicated.",
    required=("ValueNodeId",))

data_type(1231, "AASAuthorizationOptionDataType", [
    ("Type", String, "Authorization type, for example OAuth2, Plain, SASL, X509Cert or APIKey."),
    ("Mechanism", String, "SASL mechanism name, used only when Type is SASL."),
    ("ResourceUri", String, "The resource authorization is requested for."),
    ("AuthorityUri", String, "The authority authorization is obtained from."),
], "One authorization option a Consumer may use. It is authorization configuration only and never carries credentials, which are supplied out of band.",
    required=("Type",))

data_type(1232, "AASAttestationDataType", [
    ("ArtifactType", String, "Media type identifying what kind of attestation this is."),
    ("Digest", String, "Digest of the attestation artifact."),
    ("Signer", String, "The party that produced the attestation."),
], "A non-authoritative discovery hint for a separate attestation or OCI referrer Resource. It never "
   "represents a package Version, and its presence is not verification: a Consumer retrieves and verifies "
   "the separate artifact itself.",
    required=("ArtifactType", "Digest"))

data_type(1233, "AASMaterializationResultDataType", [
    ("Xid", String, "The registry-relative path of the document this result is about."),
    ("Outcome", T(1213), "What the call did to it."),
    ("VersionId", String, "The version that is now active for this document, where one is."),
    ("MaterializedNode", NodeId, "The root node of the generation now serving this document, where it materialized."),
    ("Diagnostic", String, "Why the document failed, where it did. Empty otherwise."),
], "The result of materializing one document. A call returns one of these per document it considered, reporting per document whether it was unchanged, materialized, retired or failed.",
    category=(CU_UPDATEABLE,), required=("Xid", "Outcome"))

# ---------------------------------------------------------------------------
# Metamodel ObjectTypes - abstract bases
# ---------------------------------------------------------------------------
object_type(1001, "AASReferableType", BaseObjectType,
            "Abstract base of everything in the metamodel that can be referred to by a short name. Carries the "
            "identifying and descriptive attributes every element has.", abstract=True)
RF = "AASReferableType"
prop_var(1001, RF, "IdShort", String, "The short name, unique only within its parent. It is never an identifier: two elements from different publishers routinely share one. Absent for an element inside a SubmodelElementList, which is addressed by index instead.")
prop_var(1001, RF, "Category", String, "Deprecated in the metamodel and retained only so that a document carrying it round-trips unchanged.")
prop_var(1001, RF, "DisplayNameSet", T(1222), "Display name per language.", valuerank="1")
prop_var(1001, RF, "DescriptionSet", T(1222), "Description per language.", valuerank="1")
prop_var(1001, RF, "Extensions", T(1228), "Proprietary extensions, preserved verbatim.", valuerank="1")
prop_var(1001, RF, "ModelType", String, "The metamodel class name of this element. It is redundant with the ObjectType and is carried so that a serialization produced from the AddressSpace is byte-identical to the one that produced it.", rule=MR_Mandatory)

object_type(1002, "AASIdentifiableType", T(1001),
            "Abstract base of the metamodel elements that carry a globally unique identifier: shells, submodels "
            "and concept descriptions.", abstract=True)
ID = "AASIdentifiableType"
prop_var(1002, ID, "Id", String, "The globally unique identifier, up to 2048 characters. It is arbitrary text and can never be a BrowseName, so it is carried here and the node is named by the derived identifier instead.", rule=MR_Mandatory)
prop_var(1002, ID, "Administration", T(1224), "Administrative information: a single current revision, with no history.")

object_type(1003, "AASHasSemanticsType", BaseObjectType,
            "Abstract base of the elements that declare what concept they are an occurrence of.", abstract=True)
HS = "AASHasSemanticsType"
prop_var(1003, HS, "SemanticId", T(1221), "The concept this element is an occurrence of, by which an element is discoverable by meaning rather than by name.")
prop_var(1003, HS, "SupplementalSemanticIds", T(1221), "Further concepts this element corresponds to, which is how one element is made discoverable through more than one dictionary.", valuerank="1")

object_type(1004, "AASHasKindType", BaseObjectType,
            "Abstract base of the elements that distinguish a template from an instance.", abstract=True)
prop_var(1004, "AASHasKindType", "Kind", T(1201), "Whether this element defines a shape or carries values.")

object_type(1005, "AASHasDataSpecificationType", BaseObjectType,
            "Abstract base of the elements that carry data specifications.", abstract=True)
prop_var(1005, "AASHasDataSpecificationType", "EmbeddedDataSpecifications", T(1226), "Data specifications carried by this element.", valuerank="1")

object_type(1006, "AASQualifiableType", BaseObjectType,
            "Abstract base of the elements that can be qualified.", abstract=True)
prop_var(1006, "AASQualifiableType", "Qualifiers", T(1225), "Qualifiers constraining or annotating this element.", valuerank="1")

# ---------------------------------------------------------------------------
# Metamodel ObjectTypes - Identifiables
# ---------------------------------------------------------------------------
object_type(1010, "AASEnvironmentType", FolderType,
            "The container of shells, submodels and concept descriptions - the unit an AAS serialization "
            "carries and the root a source generator materializes into a Server.")
EN = "AASEnvironmentType"
placeholder_obj(1010, EN, "<AssetAdministrationShell>", T(1011), "A shell held by this environment.", reftype=Organizes)
placeholder_obj(1010, EN, "<Submodel>", T(1013), "A submodel held by this environment. Submodels are top-level: one submodel may be referenced by several shells, which is why they are not nested inside them.", reftype=Organizes)
placeholder_obj(1010, EN, "<ConceptDescription>", T(1030), "A concept description held by this environment.", reftype=Organizes)

object_type(1011, "AASType", T(1002),
            "An Asset Administration Shell: the digital representation of one asset, carrying the asset's identity "
            "and references to the submodels that describe it.")
AS = "AASType"
obj_member(1011, AS, "AssetInformation", T(1012), "The identity of the asset this shell represents.", rule=MR_Mandatory)
prop_var(1011, AS, "SubmodelReferences", T(1221), "References to the submodels describing this asset. A submodel is not owned by the shell that references it.", valuerank="1")
prop_var(1011, AS, "DerivedFrom", T(1221), "The Type shell this Instance shell was derived from, so an individual item can be traced to its product model.")
prop_var(1011, AS, "EmbeddedDataSpecifications", T(1226), "Data specifications carried by this shell.", valuerank="1")

object_type(1012, "AASAssetInformationType", BaseObjectType,
            "The identity of the asset a shell represents, as distinct from the identity of the shell itself.")
AI = "AASAssetInformationType"
prop_var(1012, AI, "AssetKind", T(1200), "Whether the asset is a product model, an individual item, a batch, a role, or none of these.", rule=MR_Mandatory)
prop_var(1012, AI, "GlobalAssetId", String, "The globally unique identifier of the asset itself. Where the asset carries an identification link, that link is this value, and it is what connects a code scanned from a physical product to this Server.")
prop_var(1012, AI, "AssetType", String, "The identifier of the asset type this asset is an occurrence of.")
prop_var(1012, AI, "SpecificAssetIds", T(1223), "The additional keys the asset is discoverable by.", valuerank="1")
prop_var(1012, AI, "DefaultThumbnail", T(1229), "A pointer to a representative image of the asset.")

object_type(1013, "AASSubmodelType", T(1002),
            "One coherent aspect of an asset, identified in its own right and typed by its SemanticId: a nameplate, "
            "technical data, a carbon footprint, a bill of material.")
SM = "AASSubmodelType"
prop_var(1013, SM, "Kind", T(1201), "Whether this submodel carries values or defines a shape other submodels are built from.")
prop_var(1013, SM, "SemanticId", T(1221), "The concept this submodel is an occurrence of.")
prop_var(1013, SM, "SupplementalSemanticIds", T(1221), "Further concepts this submodel corresponds to.", valuerank="1")
prop_var(1013, SM, "Qualifiers", T(1225), "Qualifiers on this submodel.", valuerank="1")
prop_var(1013, SM, "EmbeddedDataSpecifications", T(1226), "Data specifications carried by this submodel.", valuerank="1")
placeholder_obj(1013, SM, "<SubmodelElement>", T(1020), "An element of this submodel.")

object_type(1030, "AASConceptDescriptionType", T(1002),
            "The definition a SemanticId resolves to - what makes two submodels from different vendors comparable.")
CD = "AASConceptDescriptionType"
prop_var(1030, CD, "IsCaseOf", T(1221), "Concepts in other dictionaries this concept corresponds to, which is how a Server bridges two classification systems without asserting that either is canonical.", valuerank="1")
prop_var(1030, CD, "EmbeddedDataSpecifications", T(1226), "The data specifications defining this concept.", valuerank="1")

# ---------------------------------------------------------------------------
# Metamodel ObjectTypes - SubmodelElements
# ---------------------------------------------------------------------------
object_type(1020, "AASSubmodelElementType", T(1001),
            "Abstract base of every element that can appear inside a submodel.", abstract=True)
SE = "AASSubmodelElementType"
prop_var(1020, SE, "SemanticId", T(1221), "The concept this element is an occurrence of.")
prop_var(1020, SE, "SupplementalSemanticIds", T(1221), "Further concepts this element corresponds to.", valuerank="1")
prop_var(1020, SE, "Qualifiers", T(1225), "Qualifiers on this element.", valuerank="1")
prop_var(1020, SE, "EmbeddedDataSpecifications", T(1226), "Data specifications carried by this element.", valuerank="1")
prop_var(1020, SE, "Index", UInt32, "The element's zero-based position within an ordered containing construct: its parent SubmodelElementList or one variable role of its parent Operation. For an Operation variable value it is mandatory and the role array position is authoritative. For a list member it is optional and recommended wherever the list's order is relevant, because Browse is not required to return references in order.")

object_type(1021, "AASPropertyType", T(1020),
            "A single typed value. The value node carries the OPC UA DataType clause 7.1 assigns to the "
            "declared xsd type, from which the declared type is read.")
PR = "AASPropertyType"
prop_var(1021, PR, "ValueType", T(1208), "The xsd type the value is expressed in. Mandatory: the metamodel makes it mandatory and the value optional, so a Property with no value has no value node whose DataType could carry it.", rule=MR_Mandatory)
prop_var(1021, PR, "Value", BaseDataType, "The value. Declared as BaseDataType here because the concrete DataType depends on ValueType; a materialized node carries the specific DataType clause 7.1 assigns.")
prop_var(1021, PR, "ValueId", T(1221), "A reference to the value, where the value is itself an identified concept.")

object_type(1022, "AASMultiLanguagePropertyType", T(1020),
            "A value expressed in one or more languages. The array order is preserved, because the metamodel's "
            "serialization is ordered and a round trip that reordered it would not reproduce its input.")
ML = "AASMultiLanguagePropertyType"
prop_var(1022, ML, "Value", T(1222), "The language-tagged values, in order.", valuerank="1")
prop_var(1022, ML, "ValueId", T(1221), "A reference to the value, where the value is itself an identified concept.")

object_type(1023, "AASRangeType", T(1020), "A closed or half-open interval of a single typed value.")
RA = "AASRangeType"
prop_var(1023, RA, "ValueType", T(1208), "The xsd type the bounds are expressed in. Mandatory: both bounds are optional and the declared type is not.", rule=MR_Mandatory)
prop_var(1023, RA, "Min", BaseDataType, "The lower bound, carrying the DataType clause 7.1 assigns to ValueType. Absent means unbounded below, which is different from a bound of zero.")
prop_var(1023, RA, "Max", BaseDataType, "The upper bound. Absent means unbounded above.")

object_type(1024, "AASBlobType", T(1020), "Binary content carried inline.")
BL = "AASBlobType"
prop_var(1024, BL, "Value", ByteString, "The content bytes.")
prop_var(1024, BL, "ContentType", String, "Media type of the content.", rule=MR_Mandatory)

object_type(1025, "AASFileType", T(1020), "A pointer to content held outside the element.")
FI = "AASFileType"
prop_var(1025, FI, "Value", String, "Path or URL to the content.")
prop_var(1025, FI, "ContentType", String, "Media type of the content.", rule=MR_Mandatory)

object_type(1026, "AASReferenceElementType", T(1020), "An element whose value is a reference.")
prop_var(1026, "AASReferenceElementType", "Value", T(1221), "The reference.")

object_type(1027, "AASRelationshipElementType", T(1020), "A directed relationship between two referenced things.")
RE = "AASRelationshipElementType"
prop_var(1027, RE, "First", T(1221), "The first, or source, end of the relationship.", rule=MR_Mandatory)
prop_var(1027, RE, "Second", T(1221), "The second, or target, end of the relationship.", rule=MR_Mandatory)

object_type(1028, "AASAnnotatedRelationshipElementType", T(1027),
            "A relationship carrying data elements that annotate it, such as a quantity or a position.")
placeholder_obj(1028, "AASAnnotatedRelationshipElementType", "<Annotation>", T(1020), "A data element annotating this relationship.")

object_type(1029, "AASSubmodelElementCollectionType", T(1020),
            "An unordered set of elements, each identified by its own IdShort.")
placeholder_obj(1029, "AASSubmodelElementCollectionType", "<SubmodelElement>", T(1020), "An element of this collection.")

object_type(1031, "AASSubmodelElementListType", T(1020),
            "A list of elements. Its members have no IdShort, so they are named by index. Whether the order "
            "carries meaning is stated by the ReferenceType on each instance, not by a Property: "
            "HasOrderedComponent where it does, HasComponent where the list is a set or a bag. The declaration "
            "uses HasComponent, the base of both legal instance forms.")
SL = "AASSubmodelElementListType"
prop_var(1031, SL, "TypeValueListElement", T(1210), "The element kind every member is constrained to.", rule=MR_Mandatory)
prop_var(1031, SL, "SemanticIdListElement", T(1221), "The concept every member is an occurrence of, where they share one.")
prop_var(1031, SL, "ValueTypeListElement", T(1208), "The xsd type every member's value is expressed in, where they share one. Mandatory in the metamodel when the members are Properties or Ranges.")
ordered_placeholder(1031, SL, "<Element>", T(1020), "A member of this list, named by its index. The declaration uses HasComponent; an instance uses HasOrderedComponent where the list's order is relevant and HasComponent where it is not.")

object_type(1032, "AASEntityType", T(1020),
            "A component of a composition. A self-managed entity carries the identifier of its own shell, so a "
            "bill of material is traversable across organizations.")
ET = "AASEntityType"
prop_var(1032, ET, "EntityType", T(1202), "Whether the component has its own shell or is managed within its parent.", rule=MR_Mandatory)
prop_var(1032, ET, "GlobalAssetId", String, "The identifier of the component's own asset, for a self-managed entity.")
prop_var(1032, ET, "SpecificAssetIds", T(1223), "Additional keys the component is discoverable by.", valuerank="1")
placeholder_obj(1032, ET, "<Statement>", T(1020), "A statement about the component.")

object_type(1033, "AASBasicEventElementType", T(1020), "An event source or sink.")
BE = "AASBasicEventElementType"
prop_var(1033, BE, "Observed", T(1221), "What the event observes.", rule=MR_Mandatory)
prop_var(1033, BE, "Direction", T(1203), "Whether the event is produced or consumed.", rule=MR_Mandatory)
prop_var(1033, BE, "State", T(1204), "Whether the event source is active.", rule=MR_Mandatory)
prop_var(1033, BE, "MessageTopic", String, "The topic events are delivered on. Where the delivery endpoint is itself catalogued, the registry entry points at it.")
prop_var(1033, BE, "MessageBroker", T(1221), "The broker delivering the events.")
prop_var(1033, BE, "LastUpdate", DateTime, "When the event last fired. The metamodel types this xs:dateTime, which clause 7.1 assigns DateTime.")
prop_var(1033, BE, "MinInterval", DurationString, "Minimum interval between events. The metamodel types this xs:duration, which clause 7.1 assigns DurationString.")
prop_var(1033, BE, "MaxInterval", DurationString, "Maximum interval between events. The metamodel types this xs:duration, which clause 7.1 assigns DurationString.")

object_type(1034, "AASOperationType", T(1020), "An invocable operation.")
OP = "AASOperationType"
prop_var(1034, OP, "InputVariables", T(1230), "The operation's input variables, in order. Each entry points to one direct operation-variable child and the array position is authoritative.", valuerank="1")
prop_var(1034, OP, "OutputVariables", T(1230), "The operation's output variables, in order. Each entry points to one direct operation-variable child and the array position is authoritative.", valuerank="1")
prop_var(1034, OP, "InoutputVariables", T(1230), "The operation's in-out variables, in order. Each entry points to one direct operation-variable child and the array position is authoritative.", valuerank="1")
placeholder_obj(1034, OP, "<Variable>", T(1020), "A direct HasComponent child carrying one operation variable value. Its role array entry points to it by ValueNodeId, and its Index equals its position within that role.")
method(1034, OP, "Invoke",
    "Invoke the operation and return its results. The Call counterpart of InvokeOperation in the AAS API of "
    "IDTA-01002 Part 2: a Client that has browsed to the Operation element calls this rather than reaching for "
    "the HTTP interface, and the two carry the same arguments in the same order.",
    inargs=[("InputValues", BaseDataType, "Values for the operation's input variables, positionally matching InputVariables.", 1),
            ("InoutputValues", BaseDataType, "Values for the operation's in-out variables, positionally matching InoutputVariables.", 1),
            ("ClientTimeout", Duration, "How long the caller will wait. Zero means the Server's default. Corresponds to clientTimeoutDuration of the AAS API request.")],
    outargs=[("OutputValues", BaseDataType, "Results, positionally matching OutputVariables.", 1),
             ("InoutputResults", BaseDataType, "The in-out variables after execution, positionally matching InoutputVariables.", 1),
             ("Success", Boolean, "Whether the operation executed successfully. A false result is an executed operation that failed, not a failed Call."),
             ("Diagnostic", String, "Why the operation failed, where it did.")],
    category=(CU_INVOKE,))

object_type(1035, "AASCapabilityType", T(1020),
            "A declared capability of the asset. It carries no value of its own; the element's identity and "
            "semantics are the whole of its content.")

# ---------------------------------------------------------------------------
# Registry ObjectTypes - xRegistry domain extension
# ---------------------------------------------------------------------------
object_type(1100, "AASRegistryType", XRegistry_RegistryType,
            "The AAS Registry root - an xRegistry RegistryType, and therefore a FolderType - whose group folders "
            "hold shells, submodel templates, concept dictionaries and packages. Exposed as a well-known object "
            "under the Server object, so any Client that reaches the standard Server object discovers it.")
RG = "AASRegistryType"
placeholder_obj(1100, RG, "<ShellGroup>", T(1101), "A shell folder held by the registry.", reftype=Organizes)
placeholder_obj(1100, RG, "<SubmodelTemplateGroup>", T(1103), "A submodel template family held by the registry.", reftype=Organizes)
placeholder_obj(1100, RG, "<ConceptDictionaryGroup>", T(1104), "A concept dictionary held by the registry.", reftype=Organizes)
placeholder_obj(1100, RG, "<PackageStoreGroup>", T(1106), "A package store held by the registry.", reftype=Organizes)
placeholder_obj(1100, RG, "<Environment>", T(1108), "A serialization of one materialized environment, held by the registry as a retrievable document.", reftype=Organizes)
GET_SUBMODEL_DESCRIPTION = (
    "Resolve the selected AASSubmodelFileType before returning its document and enforce the same "
    "Session-specific effective RolePermissions, UserRolePermissions, DisclosureTier, Authorization "
    "and FileType Open/Read decision as direct access to that target. Call permission on this Method "
    "does not authorize the target. Return Bad_UserAccessDenied, or Bad_NotFound where policy conceals "
    "existence, without exposing controlled bytes, Format, ContentType, other target metadata or a "
    "distinguishable timing path.")
lookup_type = method(1100, RG, "LookupShellsByAssetLink",
    "Return the shells discoverable by an asset key. This is the discovery question - given a serial number or a "
    "part identifier, which shells describe it - answered without the caller browsing the whole collection.",
    inargs=[("Name", String, "The key name, for example serialNumber."), ("Value", String, "The key value.")],
    outargs=[("Shells", NodeId, "The shell group nodes matching the key.", 1)])
getsm_type = method(1100, RG, "GetSubmodel",
    GET_SUBMODEL_DESCRIPTION,
    inargs=[("SubmodelIdentifier", String, "The submodel's authored identifier.")],
    outargs=[("Document", ByteString, "The submodel document bytes."), ("Format", String, "xRegistry format string."), ("ContentType", String, "Document media type.")])
prop_var(1100, RG, "AutoMaterialize", Boolean, "Whether a change to a stored document re-materializes the AddressSpace without being asked. Part of the updateable registry profile.")
prop_var(1100, RG, "MaterializationGeneration", UInt32, "Increments once on each committed switch. A Client correlates a node's NodeVersion with the generation that produced it.")
materialize_type = method(1100, RG, "Materialize",
    "Re-materialize the AddressSpace from the stored documents. Part of the updateable registry profile: the "
    "documents are canonical and the nodes are derived, so this is the operation that makes the derived side agree "
    "with the canonical one.",
    inargs=[("Targets", String, "The documents to consider, as registry-relative paths. An empty array means every document.", 1),
            ("Force", Boolean, "Re-materialize even a document whose digest is unchanged.")],
    outargs=[("Generation", UInt32, "The generation in force after the call."),
             ("Results", T(1233), "One result per document considered.", 1)])

object_type(1101, "AASShellGroupType", XRegistry_GroupType,
            "An xRegistry GroupType holding the submodel documents of one shell. Its source identity is the shell's "
            "authored identifier, from which the GroupId is constructed. It is distinct from AASType, which models "
            "the same shell as a live node tree rather than as a catalogue entry.")
SG = "AASShellGroupType"
prop_var(1101, SG, "AasIdentifier", String, "The shell's authored identifier, verbatim. It is the group's source identity: the GroupId is the symbolic identifier constructed from it, and Name is this identifier.", rule=MR_Mandatory)
prop_var(1101, SG, "AssetKind", T(1200), "Whether the shell describes a product model, an individual item or a batch.", rule=MR_Mandatory)
prop_var(1101, SG, "GlobalAssetId", String, "The identifier of the asset itself, as distinct from the shell describing it.")
prop_var(1101, SG, "AssetType", String, "The identifier of the asset type this asset is an occurrence of.")
prop_var(1101, SG, "SpecificAssetIds", T(1223), "The keys this shell is discoverable by.", valuerank="1")
prop_var(1101, SG, "Administration", T(1224), "Administrative information carried by the shell.")
prop_var(1101, SG, "DerivedFrom", String, "The identifier of the Type shell this Instance shell was derived from.")
prop_var(1101, SG, "DisclosureTier", T(1211), "Whether this entity is readable without authentication.")
prop_var(1101, SG, "Authorization", T(1231), "The authorization options a Consumer may use to obtain access.", valuerank="1")
prop_var(1101, SG, "EventEndpoint", String, "The catalogued endpoint delivering change events for this shell, where one is published.")
prop_var(1101, SG, "ShellNode", NodeId, "The AASType node modelling this same shell as a live node tree, where the Server also implements the metamodel half. The catalogue entry and the node tree are different nodes for the same shell, and this is the link between them.")
placeholder_obj(1101, SG, "<Submodel>", T(1102), "A submodel document held by this shell.", reftype=Organizes)

object_type(1102, "AASSubmodelFileType", XRegistry_ResourceType,
            "An xRegistry ResourceType whose file content is one submodel document. Each version is one revision, "
            "which is what gives a shell the lifecycle history the metamodel does not itself provide.")
SF = "AASSubmodelFileType"
prop_var(1102, SF, "SubmodelIdentifier", String, "The submodel's authored identifier, verbatim. It is the resource's source identity, from which the ResourceId is constructed, and it is invariant across the submodel's versions.", rule=MR_Mandatory)
prop_var(1102, SF, "SemanticId", String, "The concept this submodel is an occurrence of - the attribute a Consumer filters on to find, for example, every carbon footprint submodel in a registry.")
prop_var(1102, SF, "SupplementalSemanticIds", String, "Further concepts this submodel corresponds to.", valuerank="1")
prop_var(1102, SF, "Kind", T(1201), "Whether the submodel carries values or defines a shape.")
prop_var(1102, SF, "Template", String, "The identifier of the template this submodel was built from. It is an identifier and not a pointer, so it resolves identically whether or not this registry also serves the template.")
prop_var(1102, SF, "Digest", String, "Digest of the exact document bytes a Consumer retrieves. A registry does not publish one for bytes it has not itself seen.")
prop_var(1102, SF, "DigestAlg", String, "The algorithm used to compute Digest. Present whenever Digest is.")
prop_var(1102, SF, "IsDefault", Boolean, "Whether this is the version served when none is selected.")
prop_var(1102, SF, "Ancestor", String, "The version this one derives from. A root version's ancestor is itself.")
prop_var(1102, SF, "DisclosureTier", T(1211), "Whether this document is readable without authentication. A document is wholly one tier or the other: a boundary falling between elements inside a document cannot be expressed here.")
prop_var(1102, SF, "Authorization", T(1231), "The authorization options a Consumer may use to obtain access.", valuerank="1")
prop_var(1102, SF, "SubmodelNode", NodeId, "The AASSubmodelType node modelling this same submodel as a live node tree, where the Server also implements the metamodel half.")
prop_var(1102, SF, "LoadState", T(1212), "The materialization state of this document. Part of the updateable registry profile.")
prop_var(1102, SF, "DesiredVersionId", String, "The version an operator wants materialized. Part of the updateable registry profile.")
prop_var(1102, SF, "ActiveVersionId", String, "The version currently materialized. It differs from DesiredVersionId while a switch is in flight, and persistently when the desired version failed to validate.")

object_type(1103, "AASSubmodelTemplateGroupType", XRegistry_GroupType,
            "An xRegistry GroupType holding one publisher's family of submodel templates. Templates are held in "
            "a group of their own so that a Consumer lists templates and instances separately.")
STG = "AASSubmodelTemplateGroupType"
prop_var(1103, STG, "TemplateNamespace", String, "The publisher's template namespace, verbatim. It is the group's source identity.", rule=MR_Mandatory)
prop_var(1103, STG, "Publisher", String, "The organization publishing this template family.")
placeholder_obj(1103, STG, "<Submodel>", T(1102), "A submodel template held by this family.", reftype=Organizes)

object_type(1104, "AASConceptDictionaryGroupType", XRegistry_GroupType,
            "An xRegistry GroupType holding one dictionary of concept definitions - the definitions a SemanticId "
            "elsewhere in the registry resolves to.")
CDG = "AASConceptDictionaryGroupType"
prop_var(1104, CDG, "DictionaryIdentifier", String, "The dictionary's identifier, verbatim. It is the group's source identity.", rule=MR_Mandatory)
placeholder_obj(1104, CDG, "<ConceptDescription>", T(1105), "A concept definition held by this dictionary.", reftype=Organizes)

object_type(1105, "AASConceptDescriptionFileType", XRegistry_ResourceType,
            "An xRegistry ResourceType whose file content is one concept description document.")
CDF = "AASConceptDescriptionFileType"
prop_var(1105, CDF, "ConceptIdentifier", String, "The concept's authored identifier, verbatim, which is the value that appears as a SemanticId elsewhere. It is the resource's source identity. Dictionary identifiers frequently use a syntax unrelated to any URI scheme, so the authored identifier is carried here and the node is named by the derived one.", rule=MR_Mandatory)
prop_var(1105, CDF, "IsCaseOf", String, "Concepts in other dictionaries this concept corresponds to.", valuerank="1")
prop_var(1105, CDF, "ConceptNode", NodeId, "The AASConceptDescriptionType node modelling this same concept as a live node tree, where the Server also implements the metamodel half.")
prop_var(1105, CDF, "LoadState", T(1212), "The materialization state of this document. Part of the updateable registry profile.")
prop_var(1105, CDF, "DesiredVersionId", String, "The version an operator wants materialized. Part of the updateable registry profile.")
prop_var(1105, CDF, "ActiveVersionId", String, "The version currently materialized.")

object_type(1106, "AASPackageStoreGroupType", XRegistry_GroupType,
            "An xRegistry GroupType holding packages - one store, or one namespace within one.")
PSG = "AASPackageStoreGroupType"
prop_var(1106, PSG, "StoreIdentifier", String, "The store's identifier, verbatim. It is the group's source identity.", rule=MR_Mandatory)
prop_var(1106, PSG, "RegistryUrl", String, "Base URL of the backing package store.")
placeholder_obj(1106, PSG, "<Package>", T(1107), "A package held by this store.", reftype=Organizes)

object_type(1107, "AASPackageFileType", XRegistry_ResourceType,
            "An xRegistry ResourceType whose file content is one package. Every package carries mandatory strong "
            "integrity metadata for the exact returned blob; an OCI-backed version also carries the immutable "
            "manifest digest that is its version identity. Mutable tags are Resource-level discovery aliases, "
            "never Version identity, and OCI referrers are separate Resources rather than package Versions and "
            "cannot affect the package default Version.")
PF = "AASPackageFileType"
prop_var(1107, PF, "PackageIdentifier", String, "The package's name as held by the backing store, verbatim. It is the resource's source identity.", rule=MR_Mandatory)
prop_var(1107, PF, "ArtifactType", String, "The media type identifying what the artifact is, where the backing store carries one.")
prop_var(1107, PF, "Digest", String,
         "Immutable lower-case hexadecimal digest, without an algorithm prefix, of the exact package blob bytes "
         "returned by FileType Read. It is Mandatory on every Version. The Server verifies it before publication, "
         "and a Consumer recomputes it before parsing, materializing or otherwise using the package.",
         rule=MR_Mandatory)
prop_var(1107, PF, "DigestAlg", String,
         "Immutable case-sensitive algorithm used to compute Digest. Only the exact spellings Sha256, Sha384 and "
         "Sha512 are valid. OCI descriptor algorithms sha256, sha384 and sha512 map respectively to those values; "
         "all other algorithms or casing are rejected.", rule=MR_Mandatory)
prop_var(1107, PF, "AasIdentifiers", String, "The shell identifiers this package contains, so a Consumer can tell what it holds without retrieving and opening it.", valuerank="1")
reserved_var(PF, "Subject", String,
             "Reserved Variable NodeId. It is not an InstanceDeclaration of AASPackageFileType; an attestation or "
             "OCI referrer is a separate immutable Resource and never a package Version.")
reserved_var(PF, "Attestations", T(1232),
             "Reserved Variable NodeId. It is not an InstanceDeclaration of AASPackageFileType; attestations and "
             "OCI referrers are separate immutable Resources and never affect the package default Version.",
             valuerank="1")

object_type(1108, "AASEnvironmentFileType", XRegistry_ResourceType,
            "An xRegistry ResourceType whose file content is one serialization of a materialized environment: an "
            "AAS JSON or XML environment document, or an AASX package. It is the retrievable form of an "
            "AASEnvironmentType folder, and its content is filtered to what the calling Session is permitted to "
            "read.")
EF = "AASEnvironmentFileType"
prop_var(1108, EF, "EnvironmentIdentifier", String, "The environment's identifier, verbatim. It is the resource's source identity, from which the ResourceId is constructed.", rule=MR_Mandatory)
prop_var(1108, EF, "Format", String, "The serialization of the document: an xRegistry format string such as aas/3.0+json, aas/3.0+xml or aasx/3.0.", rule=MR_Mandatory)
prop_var(1108, EF, "EnvironmentNode", NodeId, "The AASEnvironmentType folder this document serializes.", rule=MR_Mandatory)
prop_var(1108, EF, "Digest", String, "Digest of the exact document bytes a Consumer retrieves. A Server does not publish one for a document whose content depends on the caller's permissions.")
prop_var(1108, EF, "DigestAlg", String, "The algorithm used to compute Digest. Present whenever Digest is.")
prop_var(1108, EF, "Filtered", Boolean, "Whether the document served to this Session omits content the Session is not permitted to read.", rule=MR_Mandatory)
prop_var(1108, EF, "DisclosureTier", T(1211), "Whether this document is readable without authentication.")
prop_var(1108, EF, "Authorization", T(1231), "The authorization options a Consumer may use to obtain access.", valuerank="1")

# Well-known instance on the Server object.
add(1150, "UAObject", "AASRegistry", "AASRegistry",
    desc="Server-wide AAS Registry, a well-known component of the Server object.",
    parent=Server, category=CAT_INST)
ref(1150, HasTypeDefinition, T(1100))
ref(1150, HasComponent, Server, forward=False)
instance_method(1150, "AASRegistry", "LookupShellsByAssetLink", lookup_type,
    "Return the shells discoverable by an asset key. The functional method on the well-known AASRegistry object.",
    inargs=[("Name", String, "The key name, for example serialNumber."), ("Value", String, "The key value.")],
    outargs=[("Shells", NodeId, "The shell group nodes matching the key.", 1)])
instance_method(1150, "AASRegistry", "GetSubmodel", getsm_type,
    GET_SUBMODEL_DESCRIPTION,
    inargs=[("SubmodelIdentifier", String, "The submodel's authored identifier.")],
    outargs=[("Document", ByteString, "The submodel document bytes."), ("Format", String, "xRegistry format string."), ("ContentType", String, "Document media type.")])
instance_method(1150, "AASRegistry", "Materialize", materialize_type,
    "Re-materialize the AddressSpace from the stored documents. The functional method on the well-known AASRegistry object.",
    inargs=[("Targets", String, "The documents to consider, as registry-relative paths. An empty array means every document.", 1),
            ("Force", Boolean, "Re-materialize even a document whose digest is unchanged.")],
    outargs=[("Generation", UInt32, "The generation in force after the call."),
             ("Results", T(1233), "One result per document considered.", 1)])

# Appended after every published declaration so their encoding nodes take the
# next free member NodeIds without renumbering any existing node.
data_type(1234, "AASValueReferencePairDataType", [
    ("Value", String, "One permitted IEC 61360 value."),
    ("ValueId", T(1221), "The reference identifying the meaning of Value."),
], "One permitted value paired with the reference identifying its meaning.",
    required=("Value", "ValueId"))

data_type(1235, "AASValueListDataType", [
    ("ValueReferencePairs", T(1234), "The permitted values. At least one pair is present.", 1),
], "The non-empty list of permitted values for an IEC 61360 data specification.",
    required=("ValueReferencePairs",))

data_type(1236, "AASLevelTypeDataType", [
    ("Min", Boolean, "Whether a minimum value applies."),
    ("Nom", Boolean, "Whether a nominal value applies."),
    ("Typ", Boolean, "Whether a typical value applies."),
    ("Max", Boolean, "Whether a maximum value applies."),
], "The four IEC 61360 level flags. Every flag is explicit.",
    required=("Min", "Nom", "Typ", "Max"))

# Appended after every existing declaration to preserve all allocated NodeIds.
prop_var(1107, PF, "ManifestDigest", String,
         "Immutable exact OCI manifest digest with its lower-case algorithm prefix and lower-case hexadecimal "
         "value. It is Mandatory for every OCI-backed Version, is the sole authority for that Version's identity, "
         "and produces its always-hashed symbolic VersionId; a mutable tag is never identity. It verifies only the "
         "exact manifest bytes, never the returned package blob. The verified manifest has exactly one package-layer "
         "descriptor whose algorithm and encoded digest map to DigestAlg and Digest; the Server verifies this chain "
         "before publication and a Consumer repeats it before use.")

NAMESPACE = "http://opcfoundation.org/UA/I4AAS/v3/"
VERSION = "3.03"
PUBDATE = "2026-08-10T16:54:40Z"
UA_REQUIRED_VERSION = "1.05.04"
UA_REQUIRED_PUBDATE = "2024-05-01T00:00:00Z"
XR_NAMESPACE = "http://opcfoundation.org/UA/xRegistry/"
XR_VERSION = "0.3.0"
XR_PUBDATE = "2026-07-31T00:00:00Z"
ALIASES = [
    ("Boolean", Boolean), ("UInt32", UInt32), ("String", String), ("DateTime", DateTime),
    ("ByteString", ByteString), ("ExpandedNodeId", ExpandedNodeId), ("Duration", Duration),
    ("BaseDataType", BaseDataType), ("Integer", Integer), ("UInteger", UInteger),
    ("DurationString", DurationString),
    ("Argument", Argument), ("KeyValuePair", KeyValuePair), ("NodeId", NodeId),
    ("Enumeration", Enumeration), ("Organizes", Organizes),
    ("HasOrderedComponent", HasOrderedComponent), ("HasModellingRule", HasModellingRule),
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
    for k in ("DataType", "ValueRank", "ArrayDimensions",
              "MethodDeclarationId"):
        if k in n.attrs:
            v = _fmt_datatype(n.attrs[k]) if k == "DataType" else n.attrs[k]
            a.append(f'{k}="{v}"')
    if n.cls == "UAObjectType" and n.abstract:
        a.append('IsAbstract="true"')
    lines = ["  <" + " ".join(a) + ">"]
    lines.append(f"    <DisplayName>{sx.escape(n.display)}</DisplayName>")
    if n.desc:
        lines.append(f"    <Description>{sx.escape(n.desc)}</Description>")
    for cat in n.category:
        lines.append(f"    <Category>{sx.escape(cat)}</Category>")
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
           '<!-- OPC UA for Asset Administration Shell V3 companion namespace. Draft NodeIds (final IDs assigned by the OPC Foundation). -->',
           '<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
           '  <NamespaceUris>', f'    <Uri>{XR_NAMESPACE}</Uri>', f'    <Uri>{NAMESPACE}</Uri>', '  </NamespaceUris>',
           '  <Models>', f'    <Model ModelUri="{NAMESPACE}" Version="{VERSION}" PublicationDate="{PUBDATE}">',
           f'      <RequiredModel ModelUri="http://opcfoundation.org/UA/" Version="{UA_REQUIRED_VERSION}" PublicationDate="{UA_REQUIRED_PUBDATE}" />',
           f'      <RequiredModel ModelUri="{XR_NAMESPACE}" Version="{XR_VERSION}" PublicationDate="{XR_PUBDATE}" />',
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
        if rt in (HasComponent, HasOrderedComponent, HasProperty, Organizes) and fwd and tgt.startswith(f"ns={OWN_NS};i="):
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
          f'This annex is the normative node reference. It is generated from `tools/build_model.py` and always matches `Opc.Ua.I4AAS.NodeSet2.xml`. All nodes are defined in the companion namespace `{NAMESPACE}` (which requires the base OPC UA and xRegistry namespaces); the numeric NodeIds shown are **draft** identifiers within that namespace. The **Declared in** column marks members inherited from a supertype.\n']
    md.append('### Type overview\n')
    md.append('| NodeId | BrowseName | NodeClass | Subtype of |')
    md.append('|---|---|---|---|')
    for nid in obj_types + dt_types:
        n = NODES[nid]
        md.append(f"| ns={OWN_NS};i={nid} | {_link(n.bname)} | {n.cls[2:]} | {_link(_friendly(_supertype(n)))} |")
    md.append('')
    md.append('### Object types\n')
    for nid in obj_types:
        n = NODES[nid]
        md.append(f'<a id="{_anchor(n.bname)}"></a>')
        md.append('')
        md.append(f"#### {n.bname}  (ns={OWN_NS};i={nid})\n")
        md.append(f"*Inherits from:* {_link(_friendly(_supertype(n)))}\n")
        if n.desc: md.append(n.desc + "\n")
        rows = []
        for m in _members_of(nid):
            mn = NODES[m]
            dt = _link(_friendly(mn.attrs.get("DataType", ""))) if mn.attrs.get("DataType") else ""
            if mn.attrs.get("ValueRank", "") == "1" and dt:
                dt += r"\[\]"
            rows.append((mn.bname, mn.cls[2:], dt, _member_rule(mn), n.bname,
                         (mn.desc or "").replace("|", "/")))
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
            md.append(f"#### {n.bname}  (ns={OWN_NS};i={nid})\n")
            md.append(f"*Subtype of:* {_link(_friendly(_supertype(n)))}\n")
            if n.desc: md.append(n.desc + "\n")
            flds = DATATYPE_FIELDS.get(nid, [])
            if flds:
                is_structure = _supertype(n) == Structure
                if is_structure:
                    md.append("| Field | DataType | Cardinality | Description |")
                    md.append("|---|---|---|---|")
                else:
                    md.append("| Field | DataType | Description |")
                    md.append("|---|---|---|")
                for f in flds:
                    fname, fdt, fdesc = f[0], f[1], f[2]
                    frank = f[3] if len(f) > 3 else -1
                    dt = _link(_friendly(fdt))
                    if frank is not None and frank >= 0:
                        dt += r"\[\]"
                    if is_structure:
                        optional = f[4] if len(f) > 4 else False
                        md.append(f"| {fname} | {dt} | {'Optional' if optional else 'Mandatory'} | {(fdesc or '').replace('|', '/')} |")
                    else:
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


def inject(path, rendered):
    """Replace the embedded Annex A in a specification document.

    The annex runs from the ``annex-a`` anchor to the next ``## Annex`` heading, so the
    document cannot drift from the model: it is the same text ``model-reference.md``
    holds, and `validate_local.py` checks the two are equal.
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    start = text.index('<a id="annex-a"></a>')
    finish = text.index("\n## Annex ", text.index("## Annex A")) + 1
    new_text = text[:start] + rendered.rstrip("\n") + "\n\n" + text[finish:]
    if new_text != text:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_text)
        return True
    return False


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.abspath(os.path.join(here, ".."))
    with open(os.path.join(outdir, "Opc.Ua.I4AAS.NodeSet2.xml"), "w", encoding="utf-8") as f:
        f.write(emit())
    with open(os.path.join(outdir, "Opc.Ua.I4AAS.NodeIds.csv"), "w", encoding="utf-8") as f:
        f.write(emit_csv())
    annex = emit_md()
    with open(os.path.join(here, "model-reference.md"), "w", encoding="utf-8") as f:
        f.write(annex)
    if inject(os.path.join(outdir, "OPC-UA-AAS.md"), annex):
        print("Injected Annex A into OPC-UA-AAS.md")
    nt = sum(1 for k in NODES if NODES[k].cls in ("UAObjectType", "UADataType", "UAReferenceType"))
    print(f"Nodes: {len(NODES)}  (types: {nt})  member range: 5000..{_next_member[0]-1}")
