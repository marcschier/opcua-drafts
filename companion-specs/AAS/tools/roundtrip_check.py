#!/usr/bin/env python3
"""
Round-trip check for the OPC UA for Asset Administration Shell mapping (clause 8).

Losslessness is only a claim until it is executed. This runs both directions defined by
clause 8 over the fixture corpus:

  materialize -> serialize   an AAS environment becomes an AddressSpace subtree and comes
                             back equal to what it started as
  serialize -> materialize   a subtree becomes an environment and becomes the same subtree

The materializer here implements clause 5.6 exactly - it is a reference implementation of
the algorithm, not a general-purpose AAS server - so that a failure means the mapping is
lossy rather than that a tool is clever. The check also parses the generated NodeSet, CSV
and Annex A, derives Structure cardinalities from the pinned AAS schema, checks every
ObjectType and direct declaration against an independent semantic manifest, and
mutation-tests the generated artifact. Anything the mapping cannot carry shows up as a
difference, which is the point.

Usage (from the repository root):
    python companion-specs/AAS/tools/roundtrip_check.py
"""
from __future__ import annotations
import copy
import csv
import hashlib
import io
import json
import os
import sys
import urllib.parse
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.dirname(HERE)
FIXTURES = os.path.join(HERE, "fixtures")
NODESET = os.path.join(GEN, "Opc.Ua.I4AAS.NodeSet2.xml")
NODEIDS = os.path.join(GEN, "Opc.Ua.I4AAS.NodeIds.csv")
ANNEX = os.path.join(HERE, "model-reference.md")
SPEC = os.path.join(GEN, "OPC-UA-AAS.md")
SCHEMA = os.path.join(GEN, "jsonld", "upstream", "aas.schema.json")
VENDORED_TEMPLATES = os.path.join(
    HERE, "jsonld", "vendor", "templates")

NS = 2  # the server namespace instances live in
UANODESET_NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"
MODEL_NAMESPACE = "http://opcfoundation.org/UA/I4AAS/v3/"
MODEL_VERSION = "3.00-draft2"
MODEL_PUBLICATION_DATE = "2026-08-10T16:54:40Z"
PUBLISHED_NAMESPACE = "http://opcfoundation.org/UA/I4AAS/"
MAX_STRING_NODEID_LENGTH = 4096

# Published OPC 30270 v1.00 sentinels from OPCFoundation/UA-Nodeset,
# I4AAS/NodeIds.csv. These are deliberately independent of build_model.py.
# If the published namespace is ever selected again, every sentinel must retain
# its published identity rather than being rebound by a model-version change.
PUBLISHED_NODEIDS = {
    1002: ("AASAssetAdministrationShellType", "ObjectType"),
    1003: ("AASViewType", "ObjectType"),
    1004: ("AASReferenceType", "ObjectType"),
    1005: ("AASAssetType", "ObjectType"),
    1006: ("AASSubmodelType", "ObjectType"),
    1007: ("AASConceptDictionaryType", "ObjectType"),
    1009: ("AASSubmodelElementType", "ObjectType"),
    1010: ("AASSubmodelElementCollectionType", "ObjectType"),
    1011: ("AASOrderedSubmodelElementCollectionType", "ObjectType"),
    1012: ("AASMultiLanguagePropertyType", "ObjectType"),
    1013: ("AASPropertyType", "ObjectType"),
    1014: ("AASCapabilityType", "ObjectType"),
    1015: ("AASOperationType", "ObjectType"),
    1016: ("AASBlobType", "ObjectType"),
    1017: ("AASFileType", "ObjectType"),
    1018: ("AASRelationshipElementType", "ObjectType"),
    1019: ("AASAnnotatedRelationshipElementType", "ObjectType"),
    1020: ("AASReferenceElementType", "ObjectType"),
    1021: ("AASEventType", "ObjectType"),
    1022: ("AASEntityType", "ObjectType"),
    1023: ("AASRangeType", "ObjectType"),
    1024: ("AASIrdiConceptDescriptionType", "ObjectType"),
    1025: ("AASIriConceptDescriptionType", "ObjectType"),
    1026: ("AASCustomConceptDescriptionType", "ObjectType"),
    1027: ("AASDataSpecificationType", "ObjectType"),
    1028: ("AASDataSpecificationIEC61360Type", "ObjectType"),
    1029: ("AASIdentifierType", "ObjectType"),
    1030: ("AASAdministrativeInformationType", "ObjectType"),
    1031: ("ValueListType", "ObjectType"),
    1032: ("AASQualifierType", "ObjectType"),
    1033: ("IAASReferableType", "ObjectType"),
    1034: ("IAASIdentifiableType", "ObjectType"),
    5001: ("AASAssetAdministrationShellType_DataSpecification", "Object"),
    5002: ("AASAssetAdministrationShellType_Asset", "Object"),
}

# ---------------------------------------------------------------------------
# The metamodel classes this mapping covers, and the ObjectType each becomes.
# A class absent here has no representation, which clause 5.1 makes a defect.
# ---------------------------------------------------------------------------
ELEMENT_TYPES = {
    "Property": "AASPropertyType",
    "MultiLanguageProperty": "AASMultiLanguagePropertyType",
    "Range": "AASRangeType",
    "Blob": "AASBlobType",
    "File": "AASFileType",
    "ReferenceElement": "AASReferenceElementType",
    "RelationshipElement": "AASRelationshipElementType",
    "AnnotatedRelationshipElement": "AASAnnotatedRelationshipElementType",
    "SubmodelElementCollection": "AASSubmodelElementCollectionType",
    "SubmodelElementList": "AASSubmodelElementListType",
    "Entity": "AASEntityType",
    "BasicEventElement": "AASBasicEventElementType",
    "Operation": "AASOperationType",
    "Capability": "AASCapabilityType",
}

# Child-bearing fields, per element class: the metamodel field, and whether it is ordered.
CHILD_FIELDS = {
    "SubmodelElementCollection": ("value", False),
    "SubmodelElementList": ("value", True),
    "AnnotatedRelationshipElement": ("annotations", False),
    "Entity": ("statements", False),
}

OPERATION_ROLES = (
    ("inputVariables", "InputVariables"),
    ("outputVariables", "OutputVariables"),
    ("inoutputVariables", "InoutputVariables"),
)

IDENTIFIABLE_GROUPS = (
    ("assetAdministrationShells", "AssetAdministrationShell", "A"),
    ("submodels", "Submodel", "S"),
    ("conceptDescriptions", "ConceptDescription", "C"),
)

INSTANCE_METHOD_DECLARATIONS = (
    "LookupShellsByAssetLink",
    "GetSubmodel",
    "Materialize",
)

GET_SUBMODEL_SPEC_FRAGMENTS = (
    "first resolve",
    "`AASSubmodelFileType`",
    "`RolePermissions`",
    "`UserRolePermissions`",
    "disclosure tier",
    "authorization policy",
    "`FileType.Open`",
    "`FileType.Read`",
    "Permission to Call",
    "`Bad_UserAccessDenied`",
    "`Bad_NotFound`",
    "document bytes",
    "same externally observable failure behavior",
    "response timing",
)

GET_SUBMODEL_DESCRIPTION_FRAGMENTS = (
    "Resolve the selected",
    "AASSubmodelFileType",
    "RolePermissions",
    "UserRolePermissions",
    "DisclosureTier",
    "Authorization",
    "FileType Open/Read",
    "Call permission on this Method does not authorize the target",
    "Bad_UserAccessDenied",
    "Bad_NotFound",
    "controlled bytes",
    "Format",
    "ContentType",
    "target metadata",
    "distinguishable timing",
)

FEDERATION_SECURITY_SPEC_FRAGMENTS = (
    "scheme, host and port allowlists",
    "loopback, link-local, private",
    "cloud-metadata destinations",
    "prevent DNS rebinding",
    "no ambient cookies, credentials",
    "sent to another peer or redirect target",
    "validate the endpoint certificate",
    "certificate ApplicationUri",
    "returning or caching any bytes",
)

PACKAGE_INTEGRITY_SPEC_FRAGMENTS = (
    "Every Version of an `AASPackageFileType` **shall** instantiate",
    "`Digest`",
    "`DigestAlg`",
    "`ManifestDigest`",
    "`Sha256`",
    "`Sha384`",
    "`Sha512`",
    "lowercase hexadecimal",
    "shall not** contain an algorithm prefix",
    "`sha256`, `sha384` or `sha512`",
    "immutable within that Version",
    "exactly one package-layer descriptor",
    "equal\n   `DigestAlg` and `Digest`",
    "verifies only those exact manifest",
    "shall not** be treated as verification of the returned package blob",
    "sole authority for OCI Version identity",
    "always-hashed symbolic identifier",
    "mutable Resource-level alias",
    "[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}",
    "preserved byte-for-byte",
    "create and retain a distinct immutable Version",
    "OCI referrer",
    "shall not** instantiate `Subject` or `Attestations`",
    "separate immutable Resource",
    "Version of the package Resource it refers to",
    "shall not** change that package Resource's Version collection",
    "default Version",
    "`Epoch` or `ModifiedAt`",
)

# Fields carrying a value that clause 5.2 requires to be kept lexically.
LEXICAL_VALUE = {"Property": "value", "Range": None}

# ---------------------------------------------------------------------------
# Clause 5.2 / clause 8: a value is compared in the xsd value space, and a serializer
# emits the XSD canonical lexical representation. canonical_value() below is that
# representation - it is deliberately total: a form this mapping does not normalize is
# returned unchanged, which makes it compare equal to itself and nothing else.
# ---------------------------------------------------------------------------
import decimal
import re

_INTEGER_TYPES = {
    "xs:byte", "xs:unsignedByte", "xs:short", "xs:unsignedShort", "xs:int",
    "xs:unsignedInt", "xs:long", "xs:unsignedLong", "xs:integer",
    "xs:nonNegativeInteger", "xs:positiveInteger", "xs:nonPositiveInteger",
    "xs:negativeInteger",
}


def _canon_decimal(s):
    """The XSD canonical form of an xs:decimal, computed textually.

    Deliberately not via the decimal module: its default context rounds to 28
    significant digits, which silently truncated a 62-digit fixture value. xs:decimal is
    arbitrary precision, so anything that imposes a working precision is wrong here.
    """
    s = s.strip()
    neg = s.startswith("-")
    if s[:1] in ("+", "-"):
        s = s[1:]
    ip, _, fp = s.partition(".")
    ip = ip.lstrip("0") or "0"
    fp = fp.rstrip("0") or "0"
    out = f"{ip}.{fp}"
    return "-" + out if neg and (ip != "0" or fp != "0") else out


def canonical_value(value, value_type):
    """The XSD canonical lexical representation of `value` read as `value_type`."""
    if value is None or value_type is None:
        return value
    try:
        if value_type == "xs:boolean":
            if value in ("true", "1"):
                return "true"
            if value in ("false", "0"):
                return "false"
            return value
        if value_type in _INTEGER_TYPES:
            return str(int(value))     # Python ints are arbitrary precision
        if value_type == "xs:decimal":
            return _canon_decimal(value)
        if value_type in ("xs:double", "xs:float"):
            f = float(value)
            if f != f:
                return "NaN"
            if f in (float("inf"), float("-inf")):
                return "INF" if f > 0 else "-INF"
            m, _, e = repr(f).partition("e")
            exp = int(e) if e else 0
            d = decimal.Decimal(m).scaleb(exp).normalize()
            sign, digits, dexp = d.as_tuple()
            mant = "".join(str(x) for x in digits)
            exp10 = dexp + len(digits) - 1
            mant = mant[0] + "." + (mant[1:] or "0")
            return f"{'-' if sign else ''}{mant}E{exp10}"
        if value_type == "xs:dateTime":
            m = re.match(r"^(-?\d{4,}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)"
                         r"(Z|[+-]\d{2}:\d{2})?$", value)
            if not m:
                return value
            import datetime
            body, tz = m.group(1), m.group(2)
            if tz in (None, "Z"):
                base = body
            else:
                dt = datetime.datetime.fromisoformat(body)
                sign = 1 if tz[0] == "+" else -1
                off = datetime.timedelta(hours=int(tz[1:3]), minutes=int(tz[4:6]))
                base = (dt - sign * off).isoformat()
            if "." in base:
                head, frac = base.split(".")
                frac = frac.rstrip("0")
                base = f"{head}.{frac}" if frac else head
            return base + "Z"
    except (ValueError, ArithmeticError):
        return value
    return value


def _fail(msg):
    raise AssertionError(msg)


# ---------------------------------------------------------------------------
# Generated-model validation. These expectations are derived from the pinned
# AAS schema and from OPC UA modelling semantics, not from build_model.py.
# ---------------------------------------------------------------------------
SOURCE_STRUCTURES = {
    "AASKeyDataType": ("Key", {
        "Type": "type", "Value": "value",
    }),
    "AASReferenceDataType": ("Reference", {
        "Type": "type", "ReferredSemanticId": "referredSemanticId", "Keys": "keys",
    }),
    "AASLangStringDataType": ("AbstractLangString", {
        "Language": "language", "Text": "text",
    }),
    "AASSpecificAssetIdDataType": ("SpecificAssetId", {
        "Name": "name", "Value": "value", "ExternalSubjectId": "externalSubjectId",
        "SemanticId": "semanticId", "SupplementalSemanticIds": "supplementalSemanticIds",
    }),
    "AASAdministrativeInformationDataType": ("AdministrativeInformation", {
        "Version": "version", "Revision": "revision", "Creator": "creator",
        "TemplateId": "templateId",
        "EmbeddedDataSpecifications": "embeddedDataSpecifications",
    }),
    "AASQualifierDataType": ("Qualifier", {
        "Kind": "kind", "Type": "type", "ValueType": "valueType",
        "Value": "value", "ValueId": "valueId", "SemanticId": "semanticId",
        "SupplementalSemanticIds": "supplementalSemanticIds",
    }),
    "AASEmbeddedDataSpecificationDataType": ("EmbeddedDataSpecification", {
        "DataSpecification": "dataSpecification",
        "DataSpecificationContent": "dataSpecificationContent",
    }),
    "AASDataSpecificationIec61360DataType": ("DataSpecificationIec61360", {
        "PreferredName": "preferredName", "ShortName": "shortName", "Unit": "unit",
        "UnitId": "unitId", "SourceOfDefinition": "sourceOfDefinition",
        "Symbol": "symbol", "DataType": "dataType", "Definition": "definition",
        "ValueFormat": "valueFormat", "ValueList": "valueList", "Value": "value",
        "LevelType": "levelType",
    }),
    "AASExtensionDataType": ("Extension", {
        "Name": "name", "ValueType": "valueType", "Value": "value",
        "RefersTo": "refersTo", "SemanticId": "semanticId",
        "SupplementalSemanticIds": "supplementalSemanticIds",
    }),
    "AASResourceDataType": ("Resource", {
        "Path": "path", "ContentType": "contentType",
    }),
    "AASOperationVariableDataType": ("OperationVariable", {
        "ValueNodeId": "value",
    }),
    "AASValueReferencePairDataType": ("ValueReferencePair", {
        "Value": "value", "ValueId": "valueId",
    }),
    "AASValueListDataType": ("ValueList", {
        "ValueReferencePairs": "valueReferencePairs",
    }),
    "AASLevelTypeDataType": ("LevelType", {
        "Min": "min", "Nom": "nom", "Typ": "typ", "Max": "max",
    }),
}

CUSTOM_STRUCTURE_REQUIRED = {
    "AASAuthorizationOptionDataType": {"Type"},
    "AASAttestationDataType": {"ArtifactType", "Digest"},
    "AASMaterializationResultDataType": {"Xid", "Outcome"},
}

IEC61360_SCHEMA_FIELDS = {
    ("DataSpecificationIec61360", "valueList"):
        ("ValueList", False, None, False),
    ("DataSpecificationIec61360", "levelType"):
        ("LevelType", False, None, False),
    ("ValueReferencePair", "value"):
        ("string", False, None, True),
    ("ValueReferencePair", "valueId"):
        ("Reference", False, None, True),
    ("ValueList", "valueReferencePairs"):
        ("ValueReferencePair", True, 1, True),
    ("LevelType", "min"): ("boolean", False, None, True),
    ("LevelType", "nom"): ("boolean", False, None, True),
    ("LevelType", "typ"): ("boolean", False, None, True),
    ("LevelType", "max"): ("boolean", False, None, True),
}

EXPECTED_NODEIDS = {
    "BaseObjectType": "i=58",
    "FolderType": "i=61",
    "PropertyType": "i=68",
    "String": "i=12",
    "Boolean": "i=1",
    "UInt32": "i=7",
    "DateTime": "i=13",
    "ByteString": "i=15",
    "NodeId": "i=17",
    "BaseDataType": "i=24",
    "Integer": "i=27",
    "UInteger": "i=28",
    "Enumeration": "i=29",
    "Structure": "i=22",
    "DurationString": "i=12879",
    "xRegistry.RegistryType": "ns=1;i=63000",
    "xRegistry.GroupType": "ns=1;i=63001",
    "xRegistry.ResourceType": "ns=1;i=63002",
    "Organizes": "i=35",
    "HasProperty": "i=46",
    "HasComponent": "i=47",
    "Mandatory": "i=78",
    "Optional": "i=80",
    "OptionalPlaceholder": "i=11508",
}

EXPECTED_DATA_TYPES = {
    "AASAnyUri": (1180, "String"),
    "AASHexBinary": (1181, "ByteString"),
    "AASNonPositiveInteger": (1182, "Integer"),
    "AASNegativeInteger": (1183, "AASNonPositiveInteger"),
    "AASPositiveInteger": (1184, "UInteger"),
    "AASGYear": (1185, "String"),
    "AASGYearMonth": (1186, "String"),
    "AASGMonth": (1187, "String"),
    "AASGMonthDay": (1188, "String"),
    "AASGDay": (1189, "String"),
    "AASValueString": (1199, "String"),
    "AASAssetKindDataType": (1200, "Enumeration"),
    "AASModellingKindDataType": (1201, "Enumeration"),
    "AASEntityTypeDataType": (1202, "Enumeration"),
    "AASDirectionDataType": (1203, "Enumeration"),
    "AASStateOfEventDataType": (1204, "Enumeration"),
    "AASQualifierKindDataType": (1205, "Enumeration"),
    "AASReferenceTypesDataType": (1206, "Enumeration"),
    "AASKeyTypesDataType": (1207, "Enumeration"),
    "AASDataTypeDefXsdDataType": (1208, "Enumeration"),
    "AASDataTypeIec61360DataType": (1209, "Enumeration"),
    "AASSubmodelElementsDataType": (1210, "Enumeration"),
    "AASDisclosureTierDataType": (1211, "Enumeration"),
    "AASLoadStateDataType": (1212, "Enumeration"),
    "AASMaterializationOutcomeDataType": (1213, "Enumeration"),
    "AASKeyDataType": (1220, "Structure"),
    "AASReferenceDataType": (1221, "Structure"),
    "AASLangStringDataType": (1222, "Structure"),
    "AASSpecificAssetIdDataType": (1223, "Structure"),
    "AASAdministrativeInformationDataType": (1224, "Structure"),
    "AASQualifierDataType": (1225, "Structure"),
    "AASEmbeddedDataSpecificationDataType": (1226, "Structure"),
    "AASDataSpecificationIec61360DataType": (1227, "Structure"),
    "AASExtensionDataType": (1228, "Structure"),
    "AASResourceDataType": (1229, "Structure"),
    "AASOperationVariableDataType": (1230, "Structure"),
    "AASAuthorizationOptionDataType": (1231, "Structure"),
    "AASAttestationDataType": (1232, "Structure"),
    "AASMaterializationResultDataType": (1233, "Structure"),
    "AASValueReferencePairDataType": (1234, "Structure"),
    "AASValueListDataType": (1235, "Structure"),
    "AASLevelTypeDataType": (1236, "Structure"),
}

EXPECTED_STRUCTURE_FIELDS = {
    "AASKeyDataType": {
        "Type": ("AASKeyTypesDataType", "-1"),
        "Value": ("String", "-1"),
    },
    "AASReferenceDataType": {
        "Type": ("AASReferenceTypesDataType", "-1"),
        "ReferredSemanticId": ("AASReferenceDataType", "-1"),
        "Keys": ("AASKeyDataType", "1"),
    },
    "AASLangStringDataType": {
        "Language": ("String", "-1"),
        "Text": ("String", "-1"),
    },
    "AASSpecificAssetIdDataType": {
        "Name": ("String", "-1"),
        "Value": ("String", "-1"),
        "ExternalSubjectId": ("AASReferenceDataType", "-1"),
        "SemanticId": ("AASReferenceDataType", "-1"),
        "SupplementalSemanticIds": ("AASReferenceDataType", "1"),
    },
    "AASAdministrativeInformationDataType": {
        "Version": ("String", "-1"),
        "Revision": ("String", "-1"),
        "Creator": ("AASReferenceDataType", "-1"),
        "TemplateId": ("String", "-1"),
        "EmbeddedDataSpecifications": (
            "AASEmbeddedDataSpecificationDataType", "1"),
    },
    "AASQualifierDataType": {
        "Kind": ("AASQualifierKindDataType", "-1"),
        "Type": ("String", "-1"),
        "ValueType": ("AASDataTypeDefXsdDataType", "-1"),
        "Value": ("AASValueString", "-1"),
        "ValueId": ("AASReferenceDataType", "-1"),
        "SemanticId": ("AASReferenceDataType", "-1"),
        "SupplementalSemanticIds": ("AASReferenceDataType", "1"),
    },
    "AASEmbeddedDataSpecificationDataType": {
        "DataSpecification": ("AASReferenceDataType", "-1"),
        "DataSpecificationContent": (
            "AASDataSpecificationIec61360DataType", "-1"),
    },
    "AASDataSpecificationIec61360DataType": {
        "PreferredName": ("AASLangStringDataType", "1"),
        "ShortName": ("AASLangStringDataType", "1"),
        "Unit": ("String", "-1"),
        "UnitId": ("AASReferenceDataType", "-1"),
        "SourceOfDefinition": ("String", "-1"),
        "Symbol": ("String", "-1"),
        "DataType": ("AASDataTypeIec61360DataType", "-1"),
        "Definition": ("AASLangStringDataType", "1"),
        "ValueFormat": ("String", "-1"),
        "ValueList": ("AASValueListDataType", "-1"),
        "Value": ("AASValueString", "-1"),
        "LevelType": ("AASLevelTypeDataType", "-1"),
    },
    "AASExtensionDataType": {
        "Name": ("String", "-1"),
        "ValueType": ("AASDataTypeDefXsdDataType", "-1"),
        "Value": ("AASValueString", "-1"),
        "RefersTo": ("AASReferenceDataType", "1"),
        "SemanticId": ("AASReferenceDataType", "-1"),
        "SupplementalSemanticIds": ("AASReferenceDataType", "1"),
    },
    "AASResourceDataType": {
        "Path": ("String", "-1"),
        "ContentType": ("String", "-1"),
    },
    "AASOperationVariableDataType": {
        "ValueNodeId": ("NodeId", "-1"),
    },
    "AASAuthorizationOptionDataType": {
        "Type": ("String", "-1"),
        "Mechanism": ("String", "-1"),
        "ResourceUri": ("String", "-1"),
        "AuthorityUri": ("String", "-1"),
    },
    "AASAttestationDataType": {
        "ArtifactType": ("String", "-1"),
        "Digest": ("String", "-1"),
        "Signer": ("String", "-1"),
    },
    "AASMaterializationResultDataType": {
        "Xid": ("String", "-1"),
        "Outcome": ("AASMaterializationOutcomeDataType", "-1"),
        "VersionId": ("String", "-1"),
        "MaterializedNode": ("NodeId", "-1"),
        "Diagnostic": ("String", "-1"),
    },
    "AASValueReferencePairDataType": {
        "Value": ("String", "-1"),
        "ValueId": ("AASReferenceDataType", "-1"),
    },
    "AASValueListDataType": {
        "ValueReferencePairs": ("AASValueReferencePairDataType", "1"),
    },
    "AASLevelTypeDataType": {
        "Min": ("Boolean", "-1"),
        "Nom": ("Boolean", "-1"),
        "Typ": ("Boolean", "-1"),
        "Max": ("Boolean", "-1"),
    },
}

MANDATORY = "Mandatory"
OPTIONAL = "Optional"
OPTIONAL_PLACEHOLDER = "OptionalPlaceholder"


def _v(name, data_type, rank="-1", rule=OPTIONAL):
    return (
        name, "Variable", data_type, rank, rule, "PropertyType", "HasProperty")


def _o(name, type_definition, rule=OPTIONAL, reference_type="HasComponent"):
    return (
        name, "Object", None, None, rule, type_definition, reference_type)


def _m(name, rule=OPTIONAL):
    return (
        name, "Method", None, None, rule, None, "HasComponent")


# Independent semantic manifest for every ObjectType and direct declaration.
# It never imports or evaluates build_model.py. Metamodel member names,
# cardinalities and ranks are cross-checked against the pinned AAS schema below;
# registry and OPC UA mapping semantics are stated explicitly here so a generator
# defect cannot teach the validator the same defect.
EXPECTED_OBJECT_TYPES = {
    "AASReferableType": (1001, "BaseObjectType", True, (
        _v("IdShort", "String"),
        _v("Category", "String"),
        _v("DisplayNameSet", "AASLangStringDataType", "1"),
        _v("DescriptionSet", "AASLangStringDataType", "1"),
        _v("Extensions", "AASExtensionDataType", "1"),
        _v("ModelType", "String", rule=MANDATORY),
    )),
    "AASIdentifiableType": (1002, "AASReferableType", True, (
        _v("Id", "String", rule=MANDATORY),
        _v("Administration", "AASAdministrativeInformationDataType"),
    )),
    "AASHasSemanticsType": (1003, "BaseObjectType", True, (
        _v("SemanticId", "AASReferenceDataType"),
        _v("SupplementalSemanticIds", "AASReferenceDataType", "1"),
    )),
    "AASHasKindType": (1004, "BaseObjectType", True, (
        _v("Kind", "AASModellingKindDataType"),
    )),
    "AASHasDataSpecificationType": (1005, "BaseObjectType", True, (
        _v("EmbeddedDataSpecifications",
           "AASEmbeddedDataSpecificationDataType", "1"),
    )),
    "AASQualifiableType": (1006, "BaseObjectType", True, (
        _v("Qualifiers", "AASQualifierDataType", "1"),
    )),
    "AASEnvironmentType": (1010, "FolderType", False, (
        _o("<AssetAdministrationShell>", "AASType",
           OPTIONAL_PLACEHOLDER, "Organizes"),
        _o("<Submodel>", "AASSubmodelType",
           OPTIONAL_PLACEHOLDER, "Organizes"),
        _o("<ConceptDescription>", "AASConceptDescriptionType",
           OPTIONAL_PLACEHOLDER, "Organizes"),
    )),
    "AASType": (1011, "AASIdentifiableType", False, (
        _o("AssetInformation", "AASAssetInformationType", MANDATORY),
        _v("SubmodelReferences", "AASReferenceDataType", "1"),
        _v("DerivedFrom", "AASReferenceDataType"),
        _v("EmbeddedDataSpecifications",
           "AASEmbeddedDataSpecificationDataType", "1"),
    )),
    "AASAssetInformationType": (1012, "BaseObjectType", False, (
        _v("AssetKind", "AASAssetKindDataType", rule=MANDATORY),
        _v("GlobalAssetId", "String"),
        _v("AssetType", "String"),
        _v("SpecificAssetIds", "AASSpecificAssetIdDataType", "1"),
        _v("DefaultThumbnail", "AASResourceDataType"),
    )),
    "AASSubmodelType": (1013, "AASIdentifiableType", False, (
        _v("Kind", "AASModellingKindDataType"),
        _v("SemanticId", "AASReferenceDataType"),
        _v("SupplementalSemanticIds", "AASReferenceDataType", "1"),
        _v("Qualifiers", "AASQualifierDataType", "1"),
        _v("EmbeddedDataSpecifications",
           "AASEmbeddedDataSpecificationDataType", "1"),
        _o("<SubmodelElement>", "AASSubmodelElementType",
           OPTIONAL_PLACEHOLDER),
    )),
    "AASConceptDescriptionType": (
        1030, "AASIdentifiableType", False, (
            _v("IsCaseOf", "AASReferenceDataType", "1"),
            _v("EmbeddedDataSpecifications",
               "AASEmbeddedDataSpecificationDataType", "1"),
        )),
    "AASSubmodelElementType": (1020, "AASReferableType", True, (
        _v("SemanticId", "AASReferenceDataType"),
        _v("SupplementalSemanticIds", "AASReferenceDataType", "1"),
        _v("Qualifiers", "AASQualifierDataType", "1"),
        _v("EmbeddedDataSpecifications",
           "AASEmbeddedDataSpecificationDataType", "1"),
        _v("Index", "UInt32"),
    )),
    "AASPropertyType": (1021, "AASSubmodelElementType", False, (
        _v("ValueType", "AASDataTypeDefXsdDataType", rule=MANDATORY),
        _v("Value", "BaseDataType"),
        _v("ValueId", "AASReferenceDataType"),
    )),
    "AASMultiLanguagePropertyType": (
        1022, "AASSubmodelElementType", False, (
            _v("Value", "AASLangStringDataType", "1"),
            _v("ValueId", "AASReferenceDataType"),
        )),
    "AASRangeType": (1023, "AASSubmodelElementType", False, (
        _v("ValueType", "AASDataTypeDefXsdDataType", rule=MANDATORY),
        _v("Min", "BaseDataType"),
        _v("Max", "BaseDataType"),
    )),
    "AASBlobType": (1024, "AASSubmodelElementType", False, (
        _v("Value", "ByteString"),
        _v("ContentType", "String", rule=MANDATORY),
    )),
    "AASFileType": (1025, "AASSubmodelElementType", False, (
        _v("Value", "String"),
        _v("ContentType", "String", rule=MANDATORY),
    )),
    "AASReferenceElementType": (
        1026, "AASSubmodelElementType", False, (
            _v("Value", "AASReferenceDataType"),
        )),
    "AASRelationshipElementType": (
        1027, "AASSubmodelElementType", False, (
            _v("First", "AASReferenceDataType", rule=MANDATORY),
            _v("Second", "AASReferenceDataType", rule=MANDATORY),
        )),
    "AASAnnotatedRelationshipElementType": (
        1028, "AASRelationshipElementType", False, (
            _o("<Annotation>", "AASSubmodelElementType",
               OPTIONAL_PLACEHOLDER),
        )),
    "AASSubmodelElementCollectionType": (
        1029, "AASSubmodelElementType", False, (
            _o("<SubmodelElement>", "AASSubmodelElementType",
               OPTIONAL_PLACEHOLDER),
        )),
    "AASSubmodelElementListType": (
        1031, "AASSubmodelElementType", False, (
            _v("TypeValueListElement", "AASSubmodelElementsDataType",
               rule=MANDATORY),
            _v("SemanticIdListElement", "AASReferenceDataType"),
            _v("ValueTypeListElement", "AASDataTypeDefXsdDataType"),
            _o("<Element>", "AASSubmodelElementType",
               OPTIONAL_PLACEHOLDER),
        )),
    "AASEntityType": (1032, "AASSubmodelElementType", False, (
        _v("EntityType", "AASEntityTypeDataType", rule=MANDATORY),
        _v("GlobalAssetId", "String"),
        _v("SpecificAssetIds", "AASSpecificAssetIdDataType", "1"),
        _o("<Statement>", "AASSubmodelElementType", OPTIONAL_PLACEHOLDER),
    )),
    "AASBasicEventElementType": (
        1033, "AASSubmodelElementType", False, (
            _v("Observed", "AASReferenceDataType", rule=MANDATORY),
            _v("Direction", "AASDirectionDataType", rule=MANDATORY),
            _v("State", "AASStateOfEventDataType", rule=MANDATORY),
            _v("MessageTopic", "String"),
            _v("MessageBroker", "AASReferenceDataType"),
            _v("LastUpdate", "DateTime"),
            _v("MinInterval", "DurationString"),
            _v("MaxInterval", "DurationString"),
        )),
    "AASOperationType": (1034, "AASSubmodelElementType", False, (
        _v("InputVariables", "AASOperationVariableDataType", "1"),
        _v("OutputVariables", "AASOperationVariableDataType", "1"),
        _v("InoutputVariables", "AASOperationVariableDataType", "1"),
        _o("<Variable>", "AASSubmodelElementType", OPTIONAL_PLACEHOLDER),
        _m("Invoke"),
    )),
    "AASCapabilityType": (
        1035, "AASSubmodelElementType", False, ()),
    "AASRegistryType": (1100, "xRegistry.RegistryType", False, (
        _o("<ShellGroup>", "AASShellGroupType",
           OPTIONAL_PLACEHOLDER, "Organizes"),
        _o("<SubmodelTemplateGroup>", "AASSubmodelTemplateGroupType",
           OPTIONAL_PLACEHOLDER, "Organizes"),
        _o("<ConceptDictionaryGroup>", "AASConceptDictionaryGroupType",
           OPTIONAL_PLACEHOLDER, "Organizes"),
        _o("<PackageStoreGroup>", "AASPackageStoreGroupType",
           OPTIONAL_PLACEHOLDER, "Organizes"),
        _o("<Environment>", "AASEnvironmentFileType",
           OPTIONAL_PLACEHOLDER, "Organizes"),
        _m("LookupShellsByAssetLink"),
        _m("GetSubmodel"),
        _v("AutoMaterialize", "Boolean"),
        _v("MaterializationGeneration", "UInt32"),
        _m("Materialize"),
    )),
    "AASShellGroupType": (1101, "xRegistry.GroupType", False, (
        _v("AasIdentifier", "String", rule=MANDATORY),
        _v("AssetKind", "AASAssetKindDataType", rule=MANDATORY),
        _v("GlobalAssetId", "String"),
        _v("AssetType", "String"),
        _v("SpecificAssetIds", "AASSpecificAssetIdDataType", "1"),
        _v("Administration", "AASAdministrativeInformationDataType"),
        _v("DerivedFrom", "String"),
        _v("DisclosureTier", "AASDisclosureTierDataType"),
        _v("Authorization", "AASAuthorizationOptionDataType", "1"),
        _v("EventEndpoint", "String"),
        _v("ShellNode", "NodeId"),
        _o("<Submodel>", "AASSubmodelFileType",
           OPTIONAL_PLACEHOLDER, "Organizes"),
    )),
    "AASSubmodelFileType": (1102, "xRegistry.ResourceType", False, (
        _v("SubmodelIdentifier", "String", rule=MANDATORY),
        _v("SemanticId", "String"),
        _v("SupplementalSemanticIds", "String", "1"),
        _v("Kind", "AASModellingKindDataType"),
        _v("Template", "String"),
        _v("Digest", "String"),
        _v("DigestAlg", "String"),
        _v("IsDefault", "Boolean"),
        _v("Ancestor", "String"),
        _v("DisclosureTier", "AASDisclosureTierDataType"),
        _v("Authorization", "AASAuthorizationOptionDataType", "1"),
        _v("SubmodelNode", "NodeId"),
        _v("LoadState", "AASLoadStateDataType"),
        _v("DesiredVersionId", "String"),
        _v("ActiveVersionId", "String"),
    )),
    "AASSubmodelTemplateGroupType": (
        1103, "xRegistry.GroupType", False, (
            _v("TemplateNamespace", "String", rule=MANDATORY),
            _v("Publisher", "String"),
            _o("<Submodel>", "AASSubmodelFileType",
               OPTIONAL_PLACEHOLDER, "Organizes"),
        )),
    "AASConceptDictionaryGroupType": (
        1104, "xRegistry.GroupType", False, (
            _v("DictionaryIdentifier", "String", rule=MANDATORY),
            _o("<ConceptDescription>", "AASConceptDescriptionFileType",
               OPTIONAL_PLACEHOLDER, "Organizes"),
        )),
    "AASConceptDescriptionFileType": (
        1105, "xRegistry.ResourceType", False, (
            _v("ConceptIdentifier", "String", rule=MANDATORY),
            _v("IsCaseOf", "String", "1"),
            _v("ConceptNode", "NodeId"),
            _v("LoadState", "AASLoadStateDataType"),
            _v("DesiredVersionId", "String"),
            _v("ActiveVersionId", "String"),
        )),
    "AASPackageStoreGroupType": (
        1106, "xRegistry.GroupType", False, (
            _v("StoreIdentifier", "String", rule=MANDATORY),
            _v("RegistryUrl", "String"),
            _o("<Package>", "AASPackageFileType",
               OPTIONAL_PLACEHOLDER, "Organizes"),
        )),
    "AASPackageFileType": (1107, "xRegistry.ResourceType", False, (
        _v("PackageIdentifier", "String", rule=MANDATORY),
        _v("ArtifactType", "String"),
        _v("Digest", "String", rule=MANDATORY),
        _v("DigestAlg", "String", rule=MANDATORY),
        _v("AasIdentifiers", "String", "1"),
        _v("ManifestDigest", "String"),
    )),
    "AASEnvironmentFileType": (
        1108, "xRegistry.ResourceType", False, (
            _v("EnvironmentIdentifier", "String", rule=MANDATORY),
            _v("Format", "String", rule=MANDATORY),
            _v("EnvironmentNode", "NodeId", rule=MANDATORY),
            _v("Digest", "String"),
            _v("DigestAlg", "String"),
            _v("Filtered", "Boolean", rule=MANDATORY),
            _v("DisclosureTier", "AASDisclosureTierDataType"),
            _v("Authorization", "AASAuthorizationOptionDataType", "1"),
        )),
}

SOURCE_OBJECT_DEFINITIONS = {
        "AASReferableType": "Referable",
        "AASIdentifiableType": "Identifiable",
        "AASHasSemanticsType": "HasSemantics",
        "AASHasKindType": "HasKind",
        "AASHasDataSpecificationType": "HasDataSpecification",
        "AASQualifiableType": "Qualifiable",
        "AASEnvironmentType": "Environment",
        "AASType": "AssetAdministrationShell",
        "AASAssetInformationType": "AssetInformation",
        "AASSubmodelType": "Submodel",
        "AASConceptDescriptionType": "ConceptDescription",
        "AASSubmodelElementType": "SubmodelElement",
        "AASPropertyType": "Property",
        "AASMultiLanguagePropertyType": "MultiLanguageProperty",
        "AASRangeType": "Range",
        "AASBlobType": "Blob",
        "AASFileType": "File",
        "AASReferenceElementType": "ReferenceElement",
        "AASRelationshipElementType": "RelationshipElement",
        "AASAnnotatedRelationshipElementType": "AnnotatedRelationshipElement",
        "AASSubmodelElementCollectionType": "SubmodelElementCollection",
        "AASSubmodelElementListType": "SubmodelElementList",
        "AASEntityType": "Entity",
        "AASBasicEventElementType": "BasicEventElement",
        "AASOperationType": "Operation",
        "AASCapabilityType": "Capability",
}

SOURCE_MEMBER_PROPERTIES = {
        ("AASReferableType", "DisplayNameSet"): "displayName",
        ("AASReferableType", "DescriptionSet"): "description",
        ("AASEnvironmentType", "<AssetAdministrationShell>"):
            "assetAdministrationShells",
        ("AASEnvironmentType", "<Submodel>"): "submodels",
        ("AASEnvironmentType", "<ConceptDescription>"): "conceptDescriptions",
        ("AASType", "SubmodelReferences"): "submodels",
        ("AASSubmodelType", "<SubmodelElement>"): "submodelElements",
        ("AASAnnotatedRelationshipElementType", "<Annotation>"): "annotations",
        ("AASSubmodelElementCollectionType", "<SubmodelElement>"): "value",
        ("AASSubmodelElementListType", "<Element>"): "value",
        ("AASEntityType", "<Statement>"): "statements",
}

SOURCE_SYNTHETIC_MEMBERS = {
        ("AASSubmodelElementType", "Index"),
        ("AASOperationType", "<Variable>"),
        ("AASOperationType", "Invoke"),
}


def _local_browse_name(node):
    browse = node.get("BrowseName", "")
    prefix, sep, local = browse.partition(":")
    return local if sep and prefix.isdigit() else browse


def _aliases(root):
    aliases = {}
    parent = root.find(UANODESET_NS + "Aliases")
    if parent is not None:
        for alias in parent:
            aliases[alias.get("Alias")] = alias.text
    return aliases


def _resolved(value, aliases):
    return aliases.get(value, value)


def _numeric_nodeid(value, aliases):
    value = _resolved(value, aliases)
    match = re.fullmatch(r"(?:ns=(\d+);)?i=(\d+)", value or "")
    if not match:
        return None
    return int(match.group(1) or 0), int(match.group(2))


def _schema_shape(schema, definition_name):
    definitions = schema["definitions"]

    def collect(fragment, visiting):
        properties = {}
        required = set(fragment.get("required", ()))
        ref_name = fragment.get("$ref", "").removeprefix("#/definitions/")
        if ref_name:
            if ref_name in visiting:
                return properties, required
            p, r = collect(definitions[ref_name], visiting | {ref_name})
            properties.update(p)
            required.update(r)
        for part in fragment.get("allOf", ()):
            p, r = collect(part, visiting)
            properties.update(p)
            required.update(r)
        properties.update(fragment.get("properties", {}))
        return properties, required

    return collect(definitions[definition_name], {definition_name})


def _schema_property_is_array(schema, fragment, visiting=frozenset()):
    if fragment.get("type") == "array":
        return True
    ref_name = fragment.get("$ref", "").removeprefix("#/definitions/")
    if ref_name and ref_name not in visiting:
        return _schema_property_is_array(
            schema, schema["definitions"][ref_name], visiting | {ref_name})
    return any(
        _schema_property_is_array(schema, part, visiting)
        for keyword in ("allOf", "anyOf", "oneOf")
        for part in fragment.get(keyword, ())
    )


def _validate_manifest_against_schema(schema):
    errors = []
    for owner_name, definition_name in SOURCE_OBJECT_DEFINITIONS.items():
        properties, required = _schema_shape(schema, definition_name)
        members = EXPECTED_OBJECT_TYPES[owner_name][3]
        for member in members:
            member_name, member_class, _, rank, rule, _, _ = member
            key = (owner_name, member_name)
            if key in SOURCE_SYNTHETIC_MEMBERS:
                continue
            property_name = SOURCE_MEMBER_PROPERTIES.get(key)
            if property_name is None and not member_name.startswith("<"):
                property_name = member_name[0].lower() + member_name[1:]
            if property_name not in properties:
                errors.append(
                    f"independent manifest {owner_name}.{member_name} has no "
                    f"source property {definition_name}.{property_name}")
                continue
            expected_rule = (
                MANDATORY if property_name in required
                else OPTIONAL_PLACEHOLDER
                if member_name.startswith("<") else OPTIONAL
            )
            if rule != expected_rule:
                errors.append(
                    f"independent manifest {owner_name}.{member_name} rule "
                    f"{rule}, source {definition_name}.{property_name} "
                    f"requires {expected_rule}")
            if member_class == "Variable":
                expected_rank = (
                    "1" if _schema_property_is_array(
                        schema, properties[property_name]) else "-1")
                if rank != expected_rank:
                    errors.append(
                        f"independent manifest {owner_name}.{member_name} "
                        f"ValueRank {rank}, source "
                        f"{definition_name}.{property_name} requires "
                        f"{expected_rank}")
    for (definition_name, property_name), expected in (
            IEC61360_SCHEMA_FIELDS.items()):
        properties, required = _schema_shape(schema, definition_name)
        fragment = properties.get(property_name)
        if fragment is None:
            errors.append(
                f"pinned schema omits "
                f"{definition_name}.{property_name}")
            continue
        is_array = _schema_property_is_array(schema, fragment)
        leaf = fragment.get("items", {}) if is_array else fragment
        reference = leaf.get("$ref", "").removeprefix("#/definitions/")
        target = reference or leaf.get("type")
        actual = (
            target,
            is_array,
            fragment.get("minItems"),
            property_name in required,
        )
        if actual != expected:
            errors.append(
                f"pinned schema {definition_name}.{property_name} is "
                f"{actual!r}, expected {expected!r}")
    return errors


def _csv_rows(text):
    rows = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) == 3 and row[1].isdigit():
            rows[int(row[1])] = (row[0], row[2])
    return rows


def _structure_definitions(root, aliases=None):
    aliases = aliases or {}
    result = {}
    for node in root:
        if node.tag != UANODESET_NS + "UADataType":
            continue
        definition = node.find(UANODESET_NS + "Definition")
        if definition is None:
            continue
        fields = {}
        for field in definition.findall(UANODESET_NS + "Field"):
            value_rank = field.get("ValueRank", "-1")
            fields[field.get("Name")] = {
                "optional": field.get("IsOptional", "false").lower() == "true",
                "array": value_rank == "1",
                "value_rank": value_rank,
                "data_type": _resolved(field.get("DataType"), aliases),
            }
        result[_local_browse_name(node)] = fields
    return result


def _find_declaration(root, aliases, owner_name, child_name):
    nodes_by_id = {node.get("NodeId"): node for node in root
                   if node.get("NodeId") is not None}
    owner = next((node for node in root
                  if _local_browse_name(node) == owner_name), None)
    if owner is None:
        return None, None, None
    refs = owner.find(UANODESET_NS + "References")
    if refs is None:
        return owner, None, None
    for reference in refs:
        if reference.get("IsForward", "true") == "false":
            continue
        child = nodes_by_id.get(reference.text)
        if child is not None and _local_browse_name(child) == child_name:
            return owner, child, _resolved(reference.get("ReferenceType"), aliases)
    return owner, None, None


def _expected_nodeid(symbol):
    if symbol is None:
        return None
    if symbol in EXPECTED_NODEIDS:
        return EXPECTED_NODEIDS[symbol]
    if symbol in EXPECTED_DATA_TYPES:
        return f"ns=2;i={EXPECTED_DATA_TYPES[symbol][0]}"
    if symbol in EXPECTED_OBJECT_TYPES:
        return f"ns=2;i={EXPECTED_OBJECT_TYPES[symbol][0]}"
    raise KeyError(f"no independent NodeId expectation for {symbol}")


def _node_class(node):
    return node.tag.removeprefix(UANODESET_NS)[2:]


def _reference_targets(node, aliases, reference_type, forward=True):
    references = node.find(UANODESET_NS + "References")
    if references is None:
        return []
    return [
        _resolved(reference.text, aliases)
        for reference in references
        if (_resolved(reference.get("ReferenceType"), aliases)
            == reference_type)
        and ((reference.get("IsForward", "true") != "false") == forward)
    ]


def _md_plain(value):
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value.strip())
    return value.replace(r"\[\]", "[]")


def _annex_semantics(text):
    overview = {}
    object_rows = {}
    data_type_rows = {}
    section = None
    owner = None
    for line in text.splitlines():
        if line == "### Type overview":
            section = "overview"
            owner = None
            continue
        if line == "### Object types":
            section = "objects"
            owner = None
            continue
        if line == "### DataTypes":
            section = "data_types"
            owner = None
            continue
        if line.startswith("### "):
            section = None
            owner = None
            continue
        if section in {"objects", "data_types"} and line.startswith("#### "):
            match = re.fullmatch(r"#### (.+?)  \(ns=2;i=\d+\)", line)
            owner = match.group(1) if match else None
            if owner is not None:
                target = (
                    object_rows if section == "objects"
                    else data_type_rows)
                target.setdefault(owner, [])
            continue
        if not line.startswith("| ") or line.startswith("| ---"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if section == "overview" and len(cells) == 4 and cells[0] != "NodeId":
            overview[cells[0]] = (
                _md_plain(cells[1]), cells[2], _md_plain(cells[3]))
        elif (section == "objects" and owner is not None
              and len(cells) == 6 and cells[0] != "BrowseName"):
            object_rows[owner].append((
                cells[0], cells[1], _md_plain(cells[2]),
                cells[3], _md_plain(cells[4])))
        elif (section == "data_types" and owner is not None
              and len(cells) == 4 and cells[0] != "Field"):
            data_type_rows[owner].append((
                cells[0], _md_plain(cells[1]), cells[2]))
    return overview, object_rows, data_type_rows


def _expected_annex_data_type(data_type, value_rank):
    if data_type is None:
        return ""
    rendered = data_type
    if value_rank == "1":
        rendered += "[]"
    return rendered


def _validate_object_types_and_annex(root, aliases, annex_text, schema):
    errors = []
    nodes_by_id = {
        _resolved(node.get("NodeId"), aliases): node
        for node in root if node.get("NodeId") is not None
    }
    actual_object_type_ids = {
        node_id for node_id, node in nodes_by_id.items()
        if node_id.startswith("ns=2;") and _node_class(node) == "ObjectType"
    }
    expected_object_type_ids = {
        f"ns=2;i={definition[0]}"
        for definition in EXPECTED_OBJECT_TYPES.values()
    }
    for node_id in sorted(actual_object_type_ids - expected_object_type_ids):
        errors.append(f"unexpected generated ObjectType {node_id}")
    for node_id in sorted(expected_object_type_ids - actual_object_type_ids):
        errors.append(f"expected ObjectType {node_id} is missing")

    hierarchical = {"i=35", "i=46", "i=47", "i=49"}
    for owner_name, (owner_numeric_id, base_name, abstract, members) in (
            EXPECTED_OBJECT_TYPES.items()):
        owner_id = f"ns=2;i={owner_numeric_id}"
        owner = nodes_by_id.get(owner_id)
        if owner is None:
            continue
        if _node_class(owner) != "ObjectType":
            errors.append(
                f"{owner_id} is {_node_class(owner)}, expected ObjectType")
            continue
        expected_browse_name = f"2:{owner_name}"
        if owner.get("BrowseName") != expected_browse_name:
            errors.append(
                f"{owner_id} BrowseName {owner.get('BrowseName')!r}, "
                f"expected {expected_browse_name!r}")
        actual_abstract = owner.get("IsAbstract", "false").lower() == "true"
        if actual_abstract != abstract:
            errors.append(
                f"{owner_name} IsAbstract={actual_abstract}, expected {abstract}")
        supertypes = _reference_targets(owner, aliases, "i=45", forward=False)
        expected_base = _expected_nodeid(base_name)
        if supertypes != [expected_base]:
            errors.append(
                f"{owner_name} supertypes {supertypes!r}, "
                f"expected [{expected_base!r}]")

        references = owner.find(UANODESET_NS + "References")
        forward_members = []
        if references is not None:
            for reference in references:
                reference_type = _resolved(
                    reference.get("ReferenceType"), aliases)
                if (reference.get("IsForward", "true") != "false"
                        and reference_type in hierarchical):
                    child_id = _resolved(reference.text, aliases)
                    child = nodes_by_id.get(child_id)
                    if child is not None:
                        forward_members.append(
                            (reference_type, child_id, child))
        parent_members = {
            node_id for node_id, node in nodes_by_id.items()
            if _resolved(node.get("ParentNodeId"), aliases) == owner_id
            and _node_class(node) in {"Object", "Variable", "Method"}
        }
        forward_member_ids = {child_id for _, child_id, _ in forward_members}
        if parent_members != forward_member_ids:
            errors.append(
                f"{owner_name} ParentNodeId children "
                f"{sorted(parent_members)!r} do not match hierarchical "
                f"references {sorted(forward_member_ids)!r}")

        actual_by_name = {}
        for reference_type, child_id, child in forward_members:
            child_name = _local_browse_name(child)
            if child_name in actual_by_name:
                errors.append(
                    f"{owner_name} has duplicate declaration {child_name!r}")
            actual_by_name[child_name] = (
                reference_type, child_id, child)
        expected_by_name = {member[0]: member for member in members}
        for child_name in sorted(actual_by_name.keys() - expected_by_name.keys()):
            errors.append(
                f"{owner_name} has unexpected declaration {child_name}")
        for child_name in sorted(expected_by_name.keys() - actual_by_name.keys()):
            errors.append(
                f"{owner_name} declaration {child_name} is missing")

        for child_name, expected in expected_by_name.items():
            actual = actual_by_name.get(child_name)
            if actual is None:
                continue
            (expected_name, expected_class, expected_data_type,
             expected_rank, expected_rule, expected_type_definition,
             expected_reference_type) = expected
            actual_reference_type, child_id, child = actual
            expected_browse_name = f"2:{expected_name}"
            if child.get("BrowseName") != expected_browse_name:
                errors.append(
                    f"{owner_name}.{expected_name} BrowseName "
                    f"{child.get('BrowseName')!r}, "
                    f"expected {expected_browse_name!r}")
            if _node_class(child) != expected_class:
                errors.append(
                    f"{owner_name}.{expected_name} NodeClass "
                    f"{_node_class(child)!r}, expected {expected_class!r}")
            actual_data_type = _resolved(child.get("DataType"), aliases)
            expected_data_type_id = _expected_nodeid(expected_data_type)
            if actual_data_type != expected_data_type_id:
                errors.append(
                    f"{owner_name}.{expected_name} DataType "
                    f"{actual_data_type!r}, expected {expected_data_type_id!r}")
            if child.get("ValueRank") != expected_rank:
                errors.append(
                    f"{owner_name}.{expected_name} ValueRank "
                    f"{child.get('ValueRank')!r}, expected {expected_rank!r}")
            actual_rules = _reference_targets(
                child, aliases, "i=37", forward=True)
            expected_rule_id = _expected_nodeid(expected_rule)
            if actual_rules != [expected_rule_id]:
                errors.append(
                    f"{owner_name}.{expected_name} ModellingRule "
                    f"{actual_rules!r}, expected [{expected_rule_id!r}]")
            actual_type_definitions = _reference_targets(
                child, aliases, "i=40", forward=True)
            expected_type_definition_id = _expected_nodeid(
                expected_type_definition)
            expected_type_definitions = (
                [] if expected_type_definition_id is None
                else [expected_type_definition_id])
            if actual_type_definitions != expected_type_definitions:
                errors.append(
                    f"{owner_name}.{expected_name} TypeDefinition "
                    f"{actual_type_definitions!r}, "
                    f"expected {expected_type_definitions!r}")
            expected_reference_type_id = _expected_nodeid(
                expected_reference_type)
            if actual_reference_type != expected_reference_type_id:
                errors.append(
                    f"{owner_name}.{expected_name} ReferenceType "
                    f"{actual_reference_type!r}, "
                    f"expected {expected_reference_type_id!r}")
            if _resolved(child.get("ParentNodeId"), aliases) != owner_id:
                errors.append(
                    f"{owner_name}.{expected_name} ParentNodeId "
                    f"{child.get('ParentNodeId')!r}, expected {owner_id!r}")
            inverse_parents = _reference_targets(
                child, aliases, expected_reference_type_id, forward=False)
            if inverse_parents != [owner_id]:
                errors.append(
                    f"{owner_name}.{expected_name} inverse parent references "
                    f"{inverse_parents!r}, expected [{owner_id!r}]")
            child_references = child.find(UANODESET_NS + "References")
            inverse_hierarchical = []
            if child_references is not None:
                inverse_hierarchical = [
                    (_resolved(reference.get("ReferenceType"), aliases),
                     _resolved(reference.text, aliases))
                    for reference in child_references
                    if reference.get("IsForward", "true") == "false"
                    and _resolved(
                        reference.get("ReferenceType"), aliases)
                    in hierarchical
                ]
            if inverse_hierarchical != [
                    (expected_reference_type_id, owner_id)]:
                errors.append(
                    f"{owner_name}.{expected_name} inverse hierarchical "
                    f"references {inverse_hierarchical!r}, expected "
                    f"{[(expected_reference_type_id, owner_id)]!r}")

    for data_type_name, (numeric_id, base_name) in EXPECTED_DATA_TYPES.items():
        node_id = f"ns=2;i={numeric_id}"
        node = nodes_by_id.get(node_id)
        if node is None:
            errors.append(f"expected DataType {node_id} is missing")
            continue
        if _node_class(node) != "DataType":
            errors.append(
                f"{node_id} is {_node_class(node)}, expected DataType")
        expected_browse_name = f"2:{data_type_name}"
        if node.get("BrowseName") != expected_browse_name:
            errors.append(
                f"{node_id} BrowseName {node.get('BrowseName')!r}, "
                f"expected {expected_browse_name!r}")
        supertypes = _reference_targets(node, aliases, "i=45", forward=False)
        expected_base = _expected_nodeid(base_name)
        if supertypes != [expected_base]:
            errors.append(
                f"{data_type_name} supertypes {supertypes!r}, "
                f"expected [{expected_base!r}]")

    def child_methods(parent_id):
        return {
            _local_browse_name(node): node
            for node_id, node in nodes_by_id.items()
            if _node_class(node) == "Method"
            and _resolved(node.get("ParentNodeId"), aliases) == parent_id
        }

    declarations = child_methods("ns=2;i=1100")
    concrete_methods = child_methods("ns=2;i=1150")
    expected_method_names = set(INSTANCE_METHOD_DECLARATIONS)
    if set(declarations) != expected_method_names:
        errors.append(
            "AASRegistryType method declarations are "
            f"{sorted(declarations)}, expected "
            f"{sorted(expected_method_names)}")
    if set(concrete_methods) != expected_method_names:
        errors.append(
            "AASRegistry concrete methods are "
            f"{sorted(concrete_methods)}, expected "
            f"{sorted(expected_method_names)}")
    for method_name in INSTANCE_METHOD_DECLARATIONS:
        declaration = declarations.get(method_name)
        concrete = concrete_methods.get(method_name)
        if declaration is None or concrete is None:
            continue
        expected_declaration_id = _resolved(
            declaration.get("NodeId"), aliases)
        actual_declaration_id = _resolved(
            concrete.get("MethodDeclarationId"), aliases)
        if actual_declaration_id != expected_declaration_id:
            errors.append(
                f"AASRegistry.{method_name} MethodDeclarationId "
                f"{actual_declaration_id!r}, expected "
                f"{expected_declaration_id!r}")

    overview, annex_object_rows, annex_data_type_rows = _annex_semantics(
        annex_text)
    expected_overview = {}
    for name, (numeric_id, base_name, _, _) in EXPECTED_OBJECT_TYPES.items():
        base = (
            _expected_nodeid(base_name)
            if base_name.startswith("xRegistry.") else base_name)
        expected_overview[f"ns=2;i={numeric_id}"] = (
            name, "ObjectType", base)
    for name, (numeric_id, base_name) in EXPECTED_DATA_TYPES.items():
        expected_overview[f"ns=2;i={numeric_id}"] = (
            name, "DataType", base_name)
    for node_id in sorted(overview.keys() - expected_overview.keys()):
        errors.append(f"Annex A has unexpected type row {node_id}")
    for node_id in sorted(expected_overview.keys() - overview.keys()):
        errors.append(f"Annex A omits type row {node_id}")
    for node_id in sorted(overview.keys() & expected_overview.keys()):
        if overview[node_id] != expected_overview[node_id]:
            errors.append(
                f"Annex A type row {node_id} is {overview[node_id]!r}, "
                f"expected {expected_overview[node_id]!r}")

    for owner_name, (_, _, _, members) in EXPECTED_OBJECT_TYPES.items():
        rows = annex_object_rows.get(owner_name)
        if rows is None:
            errors.append(f"Annex A omits ObjectType section {owner_name}")
            continue
        actual_by_name = {}
        for row in rows:
            if row[0] in actual_by_name:
                errors.append(
                    f"Annex A duplicates {owner_name}.{row[0]}")
            actual_by_name[row[0]] = row
        expected_rows = {
            member[0]: (
                member[0], member[1],
                _expected_annex_data_type(member[2], member[3]),
                member[4], owner_name)
            for member in members
        }
        for member_name in sorted(
                actual_by_name.keys() - expected_rows.keys()):
            errors.append(
                f"Annex A has unexpected member {owner_name}.{member_name}")
        for member_name in sorted(
                expected_rows.keys() - actual_by_name.keys()):
            errors.append(
                f"Annex A omits member {owner_name}.{member_name}")
        for member_name in sorted(
                actual_by_name.keys() & expected_rows.keys()):
            if actual_by_name[member_name] != expected_rows[member_name]:
                errors.append(
                    f"Annex A member {owner_name}.{member_name} is "
                    f"{actual_by_name[member_name]!r}, expected "
                    f"{expected_rows[member_name]!r}")

    for owner_name in sorted(
            annex_object_rows.keys() - EXPECTED_OBJECT_TYPES.keys()):
        errors.append(f"Annex A has unexpected ObjectType section {owner_name}")

    for structure_name, expected_fields in EXPECTED_STRUCTURE_FIELDS.items():
        rows = annex_data_type_rows.get(structure_name)
        if rows is None:
            errors.append(f"Annex A omits DataType section {structure_name}")
            continue
        actual_by_name = {row[0]: row for row in rows}
        if len(actual_by_name) != len(rows):
            errors.append(f"Annex A duplicates a field of {structure_name}")
        if structure_name in SOURCE_STRUCTURES:
            definition_name, field_map = SOURCE_STRUCTURES[structure_name]
            _, required_properties = _schema_shape(schema, definition_name)
            required_fields = {
                ua_name for ua_name, property_name in field_map.items()
                if property_name in required_properties
            }
        else:
            required_fields = CUSTOM_STRUCTURE_REQUIRED[structure_name]
        expected_rows = {
            field_name: (
                field_name,
                _expected_annex_data_type(data_type, value_rank),
                "Mandatory" if field_name in required_fields else "Optional",
            )
            for field_name, (data_type, value_rank)
            in expected_fields.items()
        }
        for field_name in sorted(
                actual_by_name.keys() - expected_rows.keys()):
            errors.append(
                f"Annex A has unexpected field "
                f"{structure_name}.{field_name}")
        for field_name in sorted(
                expected_rows.keys() - actual_by_name.keys()):
            errors.append(
                f"Annex A omits field {structure_name}.{field_name}")
        for field_name in sorted(
                actual_by_name.keys() & expected_rows.keys()):
            if actual_by_name[field_name] != expected_rows[field_name]:
                errors.append(
                    f"Annex A field {structure_name}.{field_name} is "
                    f"{actual_by_name[field_name]!r}, expected "
                    f"{expected_rows[field_name]!r}")
    return errors


def _markdown_clause(text, number):
    marker = f"### {number} "
    start = text.find(marker)
    if start < 0:
        return ""
    end = text.find("\n### ", start + len(marker))
    return text[start:] if end < 0 else text[start:end]


def _description(node):
    element = node.find(UANODESET_NS + "Description")
    return "" if element is None else "".join(element.itertext())


def _require_fragments(errors, label, text, fragments):
    for fragment in fragments:
        if fragment not in text:
            errors.append(f"{label} omits required text {fragment!r}")


def _validate_security_integrity_contracts(root, aliases, spec_text):
    errors = []
    nodes_by_id = {
        _resolved(node.get("NodeId"), aliases): node
        for node in root if node.get("NodeId") is not None
    }

    discovery_clause = _markdown_clause(spec_text, "9.5")
    _require_fragments(
        errors, "clause 9.5 GetSubmodel security contract",
        discovery_clause, GET_SUBMODEL_SPEC_FRAGMENTS)
    disclosure_clause = _markdown_clause(spec_text, "9.7")
    _require_fragments(
        errors, "clause 9.7 indirect-access disclosure contract",
        disclosure_clause, ("`GetSubmodel`", "clause 9.5",
                            "Method-level Call permission"))
    federation_clause = _markdown_clause(spec_text, "9.6")
    _require_fragments(
        errors, "clause 9.6 federation security contract",
        federation_clause, FEDERATION_SECURITY_SPEC_FRAGMENTS)

    get_submodel_methods = [
        node for node in nodes_by_id.values()
        if _node_class(node) == "Method"
        and _local_browse_name(node) == "GetSubmodel"
        and _resolved(node.get("ParentNodeId"), aliases)
        in {"ns=2;i=1100", "ns=2;i=1150"}
    ]
    if len(get_submodel_methods) != 2:
        errors.append(
            "expected GetSubmodel declaration and concrete Method, found "
            f"{len(get_submodel_methods)}")
    for method_node in get_submodel_methods:
        _require_fragments(
            errors,
            f"{method_node.get('NodeId')} GetSubmodel Description",
            _description(method_node),
            GET_SUBMODEL_DESCRIPTION_FRAGMENTS)

    integrity_clause = _markdown_clause(spec_text, "9.4")
    _require_fragments(
        errors, "clause 9.4 package integrity contract",
        integrity_clause, PACKAGE_INTEGRITY_SPEC_FRAGMENTS)
    conformance_clause = spec_text[
        spec_text.find("## 10 Profiles and conformance"):
        spec_text.find("## 11 NodeSet validation")]
    _require_fragments(
        errors, "package integrity conformance profile",
        conformance_clause,
        ("`AAS-PackageIntegrity`", "requires `AAS-PackageIntegrity`",
         "claiming `AAS-Packages`", "manifest-to-blob binding",
         "referrer separation"))

    package_type = nodes_by_id.get("ns=2;i=1107")
    if package_type is None:
        errors.append("AASPackageFileType is missing")
        return errors
    categories = [
        category.text or ""
        for category in package_type.findall(UANODESET_NS + "Category")
    ]
    if "AAS-PackageIntegrity" not in categories:
        errors.append(
            "AASPackageFileType omits AAS-PackageIntegrity Category")
    _require_fragments(
        errors, "AASPackageFileType Description",
        _description(package_type),
        ("Resource-level discovery aliases",
         "OCI referrers are separate Resources",
         "rather than package Versions",
         "cannot affect the package default Version"))

    package_descriptions = {
        name: child
        for name in ("Digest", "DigestAlg", "ManifestDigest")
        for _, child, _ in [
            _find_declaration(root, aliases, "AASPackageFileType", name)]
        if child is not None
    }
    if set(package_descriptions) != {
            "Digest", "DigestAlg", "ManifestDigest"}:
        errors.append(
            "AASPackageFileType integrity members are "
            f"{sorted(package_descriptions)}, expected "
            "['Digest', 'DigestAlg', 'ManifestDigest']")
    description_requirements = {
        "Digest": (
            "Immutable lower-case hexadecimal",
            "without an algorithm prefix", "exact package blob bytes",
            "Mandatory on every Version",
            "Server verifies it before publication",
            "Consumer recomputes it before parsing"),
        "DigestAlg": (
            "Immutable case-sensitive", "Sha256", "Sha384", "Sha512",
            "sha256, sha384 and sha512 map respectively",
            "all other algorithms or casing are rejected"),
        "ManifestDigest": (
            "Immutable exact OCI manifest digest",
            "lower-case algorithm prefix",
            "Mandatory for every OCI-backed Version",
            "sole authority", "always-hashed symbolic VersionId",
            "tag is never identity", "never the returned package blob",
            "exactly one package-layer descriptor",
            "map to DigestAlg and Digest",
            "Server verifies this chain before publication",
            "Consumer repeats it before use"),
    }
    for name, fragments in description_requirements.items():
        member = package_descriptions.get(name)
        if member is not None:
            _require_fragments(
                errors, f"AASPackageFileType.{name} Description",
                _description(member), fragments)

    reserved_package_nodes = {
        "Subject": (
            "ns=2;i=5168", "i=12", "-1",
            ("Reserved Variable NodeId",
             "not an InstanceDeclaration of AASPackageFileType",
             "separate immutable Resource",
             "never a package Version")),
        "Attestations": (
            "ns=2;i=5169", "ns=2;i=1232", "1",
            ("Reserved Variable NodeId",
             "not an InstanceDeclaration of AASPackageFileType",
             "separate immutable Resources",
             "never affect the package default Version")),
    }
    for name, (node_id, data_type, value_rank, fragments) in (
            reserved_package_nodes.items()):
        _, declaration, _ = _find_declaration(
            root, aliases, "AASPackageFileType", name)
        if declaration is not None:
            errors.append(
                f"AASPackageFileType must not declare reserved {name}")
        node = nodes_by_id.get(node_id)
        if node is None:
            errors.append(f"reserved {name} node {node_id} is missing")
            continue
        if _node_class(node) != "Variable":
            errors.append(
                f"reserved {name} is {_node_class(node)}, expected Variable")
        if _local_browse_name(node) != name:
            errors.append(
                f"reserved {name} BrowseName is "
                f"{_local_browse_name(node)!r}")
        if node.get("ParentNodeId") is not None:
            errors.append(
                f"reserved {name} must not have ParentNodeId")
        actual_data_type = _resolved(node.get("DataType"), aliases)
        if actual_data_type != data_type:
            errors.append(
                f"reserved {name} DataType {actual_data_type!r}, "
                f"expected {data_type!r}")
        if node.get("ValueRank", "-1") != value_rank:
            errors.append(
                f"reserved {name} ValueRank "
                f"{node.get('ValueRank', '-1')!r}, expected {value_rank!r}")
        if _reference_targets(node, aliases, "i=37"):
            errors.append(
                f"reserved {name} must not have a ModellingRule")
        if _reference_targets(node, aliases, "i=40") != ["i=68"]:
            errors.append(
                f"reserved {name} must retain PropertyType")
        for reference_type in ("i=35", "i=46", "i=47", "i=49"):
            if _reference_targets(
                    node, aliases, reference_type, forward=False):
                errors.append(
                    f"reserved {name} must not be attached by "
                    f"{reference_type}")
        _require_fragments(
            errors, f"reserved {name} Description",
            _description(node), fragments)

    attestation_type = nodes_by_id.get("ns=2;i=1232")
    if attestation_type is None:
        errors.append("AASAttestationDataType is missing")
    else:
        _require_fragments(
            errors, "AASAttestationDataType Description",
            _description(attestation_type),
            ("non-authoritative discovery hint",
             "separate attestation or OCI referrer Resource",
             "never represents a package Version",
             "presence is not verification"))
    return errors


def validate_generated_artifacts(root=None, csv_text=None, annex_text=None,
                                 schema=None, spec_text=None):
    if root is None:
        root = ET.parse(NODESET).getroot()
    if csv_text is None:
        with open(NODEIDS, encoding="utf-8") as stream:
            csv_text = stream.read()
    if annex_text is None:
        with open(ANNEX, encoding="utf-8") as stream:
            annex_text = stream.read()
    if schema is None:
        with open(SCHEMA, encoding="utf-8") as stream:
            schema = json.load(stream)
    if spec_text is None:
        with open(SPEC, encoding="utf-8") as stream:
            spec_text = stream.read()

    errors = _validate_manifest_against_schema(schema)
    aliases = _aliases(root)
    namespace_uris = [
        uri.text for uri in root.findall(
            f"{UANODESET_NS}NamespaceUris/{UANODESET_NS}Uri")
    ]
    model = root.find(f"{UANODESET_NS}Models/{UANODESET_NS}Model")
    if model is None:
        return ["NodeSet has no Model declaration"]
    model_uri = model.get("ModelUri")
    if model_uri != MODEL_NAMESPACE:
        errors.append(
            f"ModelUri {model_uri!r} is not the AAS V3 namespace {MODEL_NAMESPACE!r}")
    if model.get("Version") != MODEL_VERSION:
        errors.append(
            f"model Version {model.get('Version')!r} is not {MODEL_VERSION!r}")
    if model.get("PublicationDate") != MODEL_PUBLICATION_DATE:
        errors.append(
            f"model PublicationDate {model.get('PublicationDate')!r} is not "
            f"{MODEL_PUBLICATION_DATE!r}")
    if model_uri not in namespace_uris:
        errors.append(f"ModelUri {model_uri!r} is absent from NamespaceUris")
        own_ns = None
    else:
        own_ns = namespace_uris.index(model_uri) + 1
        if own_ns != 2:
            errors.append(f"AAS own namespace index is ns={own_ns}, expected ns=2")

    csv_by_id = _csv_rows(csv_text)
    for node_id, expected_identity in {
        5168: ("AASPackageFileType_Subject", "Variable"),
        5169: ("AASPackageFileType_Attestations", "Variable"),
    }.items():
        if csv_by_id.get(node_id) != expected_identity:
            errors.append(
                f"reserved CSV i={node_id} is {csv_by_id.get(node_id)!r}, "
                f"expected {expected_identity!r}")
    own_nodes = {}
    if own_ns is not None:
        for node in root:
            parsed = _numeric_nodeid(node.get("NodeId"), aliases)
            if parsed and parsed[0] == own_ns:
                own_nodes[parsed[1]] = (
                    _local_browse_name(node), node.tag.removeprefix(UANODESET_NS)[2:])
        for node_id, identity in own_nodes.items():
            csv_identity = csv_by_id.get(node_id)
            if csv_identity is None or csv_identity[1] != identity[1]:
                errors.append(
                    f"CSV identity for i={node_id} is {csv_identity!r}, "
                    f"NodeSet defines {identity!r}")
            elif identity[1] in {
                    "ObjectType", "VariableType", "ReferenceType", "DataType"}:
                if csv_identity[0] != identity[0]:
                    errors.append(
                        f"CSV symbolic name for type i={node_id} is "
                        f"{csv_identity[0]!r}, NodeSet BrowseName is {identity[0]!r}")
        for node_id in csv_by_id:
            if node_id not in own_nodes:
                errors.append(f"CSV i={node_id} has no node in the AAS namespace")

    if model_uri == PUBLISHED_NAMESPACE:
        for node_id, published in PUBLISHED_NODEIDS.items():
            current = csv_by_id.get(node_id)
            if current != published:
                errors.append(
                    f"published NodeId {PUBLISHED_NAMESPACE} i={node_id} was "
                    f"{published!r} and is rebound or removed as {current!r}")

    structures = _structure_definitions(root, aliases)
    for structure_name, (definition_name, field_map) in SOURCE_STRUCTURES.items():
        actual = structures.get(structure_name)
        if actual is None:
            errors.append(f"{structure_name} has no StructureDefinition")
            continue
        properties, required = _schema_shape(schema, definition_name)
        if set(actual) != set(field_map):
            errors.append(
                f"{structure_name} fields {sorted(actual)} do not match mapped "
                f"source fields {sorted(field_map)}")
        for ua_name, property_name in field_map.items():
            if ua_name not in actual:
                continue
            if property_name not in properties:
                errors.append(
                    f"{structure_name}.{ua_name} maps unknown schema property "
                    f"{definition_name}.{property_name}")
                continue
            expected_optional = property_name not in required
            if actual[ua_name]["optional"] != expected_optional:
                errors.append(
                    f"{structure_name}.{ua_name} IsOptional="
                    f"{actual[ua_name]['optional']} but source "
                    f"{definition_name}.{property_name} optionality is "
                    f"{expected_optional}")
            expected_array = _schema_property_is_array(
                schema, properties[property_name])
            if actual[ua_name]["array"] != expected_array:
                errors.append(
                    f"{structure_name}.{ua_name} array rank does not match "
                    f"{definition_name}.{property_name}")

    for structure_name, required in CUSTOM_STRUCTURE_REQUIRED.items():
        actual = structures.get(structure_name)
        if actual is None:
            errors.append(f"{structure_name} has no StructureDefinition")
            continue
        for field_name, field in actual.items():
            expected_optional = field_name not in required
            if field["optional"] != expected_optional:
                errors.append(
                    f"{structure_name}.{field_name} IsOptional={field['optional']}, "
                    f"expected {expected_optional}")

    for structure_name, expected_fields in EXPECTED_STRUCTURE_FIELDS.items():
        actual = structures.get(structure_name)
        if actual is None:
            errors.append(f"{structure_name} has no StructureDefinition")
            continue
        if set(actual) != set(expected_fields):
            errors.append(
                f"{structure_name} fields {sorted(actual)} do not match "
                f"independent type expectations {sorted(expected_fields)}")
        for field_name, (data_type, value_rank) in expected_fields.items():
            field = actual.get(field_name)
            if field is None:
                continue
            expected_data_type = _expected_nodeid(data_type)
            if field["data_type"] != expected_data_type:
                errors.append(
                    f"{structure_name}.{field_name} DataType "
                    f"{field['data_type']!r}, expected "
                    f"{expected_data_type!r}")
            if field["value_rank"] != value_rank:
                errors.append(
                    f"{structure_name}.{field_name} ValueRank "
                    f"{field['value_rank']!r}, expected {value_rank!r}")

    errors.extend(
        _validate_object_types_and_annex(
            root, aliases, annex_text, schema))
    errors.extend(
        _validate_security_integrity_contracts(
            root, aliases, spec_text))

    if own_ns is not None:
        if MODEL_NAMESPACE not in annex_text:
            errors.append("Annex A does not state the AAS V3 namespace")
        referred_rows = [
            line for line in annex_text.splitlines()
            if line.startswith("| ReferredSemanticId |")
        ]
        if not any("| Optional |" in line for line in referred_rows):
            errors.append(
                "Annex A does not mark Reference.ReferredSemanticId Optional")

    return errors


def _structure_presence_roundtrip(fields, value):
    encoded = []
    for name, field in fields.items():
        if name in value:
            encoded.append((name, True, value[name]))
        elif field["optional"]:
            encoded.append((name, False, None))
        else:
            raise ValueError(f"mandatory Structure field {name} is absent")
    return {name: field_value for name, present, field_value in encoded if present}


def _map_structure_field(data_type, value_rank, value, schema, encode):
    if data_type not in SOURCE_STRUCTURES:
        return copy.deepcopy(value)
    transform = (
        _encode_source_structure if encode else _decode_source_structure)
    if value_rank == "1":
        if not isinstance(value, list):
            raise ValueError(f"{data_type} array field is not an array")
        return [transform(data_type, item, schema) for item in value]
    if not isinstance(value, dict):
        raise ValueError(f"{data_type} field is not a Structure")
    return transform(data_type, value, schema)


def _encode_source_structure(structure_name, source, schema):
    if not isinstance(source, dict):
        raise ValueError(f"{structure_name} source value is not an object")
    definition_name, field_map = SOURCE_STRUCTURES[structure_name]
    properties, required = _schema_shape(schema, definition_name)
    allowed = set(field_map.values())
    if structure_name == "AASDataSpecificationIec61360DataType":
        allowed.add("modelType")
        model_type = source.get("modelType")
        if model_type != "DataSpecificationIec61360":
            raise ValueError(
                f"{structure_name} has modelType {model_type!r}")
    unknown = set(source) - allowed
    if unknown:
        raise ValueError(
            f"{structure_name} has unmapped source fields {sorted(unknown)}")
    encoded = {}
    for ua_name, property_name in field_map.items():
        if property_name not in source:
            if property_name in required:
                raise ValueError(
                    f"{definition_name}.{property_name} is mandatory")
            continue
        value = source[property_name]
        minimum = properties[property_name].get("minItems")
        if minimum is not None and len(value) < minimum:
            raise ValueError(
                f"{definition_name}.{property_name} requires at least "
                f"{minimum} item(s)")
        data_type, value_rank = EXPECTED_STRUCTURE_FIELDS[
            structure_name][ua_name]
        encoded[ua_name] = _map_structure_field(
            data_type, value_rank, value, schema, True)
    return encoded


def _decode_source_structure(structure_name, encoded, schema):
    if not isinstance(encoded, dict):
        raise ValueError(f"{structure_name} encoded value is not a Structure")
    definition_name, field_map = SOURCE_STRUCTURES[structure_name]
    properties, required = _schema_shape(schema, definition_name)
    if set(encoded) - set(field_map):
        raise ValueError(
            f"{structure_name} has unknown UA fields "
            f"{sorted(set(encoded) - set(field_map))}")
    decoded = {}
    for ua_name, property_name in field_map.items():
        if ua_name not in encoded:
            continue
        data_type, value_rank = EXPECTED_STRUCTURE_FIELDS[
            structure_name][ua_name]
        minimum = properties[property_name].get("minItems")
        if minimum is not None and len(encoded[ua_name]) < minimum:
            raise ValueError(
                f"{definition_name}.{property_name} requires at least "
                f"{minimum} item(s)")
        decoded[property_name] = _map_structure_field(
            data_type, value_rank, encoded[ua_name], schema, False)
    if structure_name == "AASDataSpecificationIec61360DataType":
        decoded["modelType"] = "DataSpecificationIec61360"
    missing = required - set(decoded)
    if missing:
        raise ValueError(
            f"{structure_name} lacks mandatory fields {sorted(missing)}")
    return decoded


# ---------------------------------------------------------------------------
# Materialization - clause 5.6
# ---------------------------------------------------------------------------
def id_short_path(parent_path, elem, index):
    """Clause 5.3: short names joined by '.', with [n] for a member of a list."""
    if index is not None:
        return f"{parent_path}[{index}]"
    seg = elem.get("idShort")
    if seg is None:
        _fail(f"element without idShort outside a list at {parent_path!r}")
    return f"{parent_path}.{seg}" if parent_path else seg


def _encode_nodeid_component(value):
    """Encode one source component without normalization or control characters."""
    encoded = []
    for character in value:
        codepoint = ord(character)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise ValueError("a NodeId component must contain Unicode scalar values")
        if character == "%" or codepoint <= 0x1F or 0x7F <= codepoint <= 0x9F:
            encoded.extend(f"%{byte:02X}" for byte in character.encode("utf-8"))
        else:
            encoded.append(character)
    return "".join(encoded)


def _decode_nodeid_component(value):
    """Decode one canonical clause 5.3 component."""
    if any(ord(character) <= 0x1F or 0x7F <= ord(character) <= 0x9F
           for character in value):
        raise ValueError("encoded NodeId component contains a raw control character")
    try:
        decoded = urllib.parse.unquote_to_bytes(value).decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("encoded NodeId component is not valid UTF-8") from error
    if _encode_nodeid_component(decoded) != value:
        raise ValueError("NodeId component is not canonically escaped")
    return decoded


def node_identifier(kind, owner_id, path=None):
    """Return the collision-free, control-free clause 5.3 String identifier.

    Each raw component is escaped independently. Lengths count Unicode code
    points in the escaped components, so the decoder can split the payload
    before reversing the escaping.
    """
    if kind not in {"A", "S", "C", "E"}:
        raise ValueError(f"unknown AAS node kind {kind!r}")
    encoded_owner = _encode_nodeid_component(owner_id)
    if kind == "E":
        if path is None:
            raise ValueError("an element NodeId requires an idShortPath")
        encoded_path = _encode_nodeid_component(path)
        identifier = (
            f"i4aas3:E:{len(encoded_owner)}:{len(encoded_path)}:"
            f"{encoded_owner}{encoded_path}"
        )
    else:
        if path is not None:
            raise ValueError(f"node kind {kind} cannot carry an idShortPath")
        identifier = f"i4aas3:{kind}:{len(encoded_owner)}:{encoded_owner}"
    if len(identifier) > MAX_STRING_NODEID_LENGTH:
        raise ValueError(
            f"derived String NodeId is {len(identifier)} characters; "
            f"OPC UA permits at most {MAX_STRING_NODEID_LENGTH}"
        )
    return identifier


def decode_node_identifier(identifier):
    """Decode a clause 5.3 identifier; used by the injectivity regression."""
    if len(identifier) > MAX_STRING_NODEID_LENGTH:
        raise ValueError(
            f"String NodeId is {len(identifier)} characters; "
            f"OPC UA permits at most {MAX_STRING_NODEID_LENGTH}"
        )
    if not identifier.startswith("i4aas3:"):
        raise ValueError("not an I4AAS V3 identifier")
    kind, sep, rest = identifier[len("i4aas3:"):].partition(":")
    if not sep or kind not in {"A", "S", "C", "E"}:
        raise ValueError("invalid node-kind discriminator")

    def take_length(text):
        token, found, tail = text.partition(":")
        if not found or re.fullmatch(r"0|[1-9][0-9]*", token) is None:
            raise ValueError("invalid length prefix")
        return int(token), tail

    owner_len, rest = take_length(rest)
    if kind == "E":
        path_len, payload = take_length(rest)
        if len(payload) != owner_len + path_len:
            raise ValueError("element payload does not match its length prefixes")
        return (
            kind,
            _decode_nodeid_component(payload[:owner_len]),
            _decode_nodeid_component(payload[owner_len:]),
        )
    if len(rest) != owner_len:
        raise ValueError("identifier payload does not match its length prefix")
    return kind, _decode_nodeid_component(rest), None


def node_id(owner_id, path=None, kind="S"):
    actual_kind = "E" if path is not None else kind
    return f"ns={NS};s={node_identifier(actual_kind, owner_id, path)}"


def browse_name(elem, index):
    """Clause 5.3: the short name, or the index for a list member which has none."""
    return str(index) if index is not None else elem["idShort"]


def materialize_element(elem, owner_id, parent_path, index, out):
    model_type = elem.get("modelType")
    if model_type not in ELEMENT_TYPES:
        _fail(f"element class {model_type!r} has no ObjectType in the mapping")
    path = id_short_path(parent_path, elem, index)
    node = {
        "NodeId": node_id(owner_id, path),
        "BrowseName": browse_name(elem, index),
        "TypeDefinition": ELEMENT_TYPES[model_type],
        "Members": {},
        "Children": [],
    }
    m = node["Members"]

    # clause 5.5: a field present in the source gets a member; an absent one gets none.
    for f in ("idShort", "category", "displayName", "description", "extensions",
              "semanticId", "supplementalSemanticIds", "qualifiers",
              "embeddedDataSpecifications"):
        if f in elem:
            m[f] = elem[f]
    m["ModelType"] = model_type
    if index is not None:
        m["Index"] = index  # clause 5.4

    child_field = CHILD_FIELDS.get(model_type)
    operation_source_fields = {
        source_name for source_name, _ in OPERATION_ROLES}
    for f, v in elem.items():
        if f in ("modelType", "idShort", "category", "displayName", "description",
                 "extensions", "semanticId", "supplementalSemanticIds", "qualifiers",
                 "embeddedDataSpecifications"):
            continue
        if child_field and f == child_field[0]:
            continue
        if model_type == "Operation" and f in operation_source_fields:
            continue
        if model_type == "Property" and f == "value":
            # clause 5.2: one Value node, typed by the DataType clause 7.1 assigns.
            m["Value"] = v
            continue
        if model_type == "Range" and f in ("min", "max"):
            m[f] = v
            continue
        m[f] = v

    if child_field:
        field, is_list = child_field
        m["_childReference"] = "HasComponent"
        if field in elem:
            ordered = is_list and elem.get("orderRelevant", True)
            for i, child in enumerate(elem[field]):
                node["Children"].append(
                    materialize_element(child, owner_id, path,
                                        i if is_list else None, out))
            if not elem[field]:
                m["_emptyChildren"] = True  # clause 5.5: present but empty
            if is_list:
                # clause 5.4: the ReferenceType, not a Property, states whether the
                # order carries meaning. Index is materialized either way here, because
                # this implementation claims AAS-LosslessRoundTrip.
                m["_childReference"] = "HasOrderedComponent" if ordered else "HasComponent"
    if model_type == "Operation":
        for source_name, member_name in OPERATION_ROLES:
            if source_name not in elem:
                continue
            m["_childReference"] = "HasComponent"
            entries = []
            for role_index, wrapper in enumerate(elem[source_name]):
                child = wrapper.get("value") if isinstance(wrapper, dict) else None
                if not isinstance(child, dict):
                    _fail(
                        f"{path}.{source_name}[{role_index}] has no "
                        "OperationVariable.value")
                child_node = materialize_element(
                    child, owner_id, f"{path}.{source_name}",
                    role_index, out)
                if "idShort" not in child:
                    _fail(
                        f"{path}.{source_name}[{role_index}].value "
                        "has no idShort")
                child_node["BrowseName"] = child["idShort"]
                node["Children"].append(child_node)
                entries.append({"ValueNodeId": child_node["NodeId"]})
            m[member_name] = entries
    out.append(node)
    return node


def identifiable_browse_names(env, digest_function=None):
    """Return deterministic top-level BrowseNames keyed by (collection, index).

    The full environment is required because authored idShort values and
    digest collisions are resolved across all children of the Environment.
    """
    digest_function = digest_function or (
        lambda identifier: hashlib.sha256(
            identifier.encode("utf-8")).hexdigest())
    names = {}
    occupied = set()
    derived = []
    for collection_name, kind_name, _ in IDENTIFIABLE_GROUPS:
        values = env.get(collection_name, [])
        if not isinstance(values, list):
            _fail(f"{collection_name} must be an array")
        identifiers = set()
        for index, value in enumerate(values):
            if not isinstance(value, dict):
                _fail(f"{collection_name}[{index}] must be an object")
            identifier = value.get("id")
            if not isinstance(identifier, str) or not identifier:
                _fail(
                    f"{collection_name}[{index}].id must be a "
                    "non-empty string")
            if identifier in identifiers:
                _fail(
                    f"{collection_name} contains duplicate identifier "
                    f"{identifier!r}")
            identifiers.add(identifier)
            if "idShort" in value:
                id_short = value["idShort"]
                if not isinstance(id_short, str) or not id_short:
                    _fail(
                        f"{collection_name}[{index}].idShort must be a "
                        "non-empty string when present")
                names[(collection_name, index)] = id_short
                occupied.add(id_short)
                continue
            digest = digest_function(identifier)
            base = f"{kind_name}_{digest}"
            derived.append((
                base, identifier.encode("utf-8"), collection_name, index))

    for base, _, collection_name, index in sorted(
            derived, key=lambda entry: (entry[0], entry[1])):
        browse_name = base
        suffix = 0
        while browse_name in occupied:
            browse_name = f"{base}_{suffix}"
            suffix += 1
        names[(collection_name, index)] = browse_name
        occupied.add(browse_name)
    return names


# Compatibility alias for consumers that imported the initially private name.
_identifiable_browse_names = identifiable_browse_names


def materialize(env):
    """Clause 5.6, steps 1-6."""
    space = {"Type": "AASEnvironmentType", "Shells": [], "Submodels": [], "Concepts": []}
    browse_names = identifiable_browse_names(env)
    for index, shell in enumerate(env.get("assetAdministrationShells", [])):
        space["Shells"].append({
            "NodeId": node_id(shell["id"], kind="A"),
            "BrowseName": browse_names[
                ("assetAdministrationShells", index)],
            "TypeDefinition": "AASType",
            "Members": {k: v for k, v in shell.items() if k != "modelType"},
            "ModelType": shell.get("modelType", "AssetAdministrationShell"),
        })
    for index, sm in enumerate(env.get("submodels", [])):
        nodes = []
        for i, e in enumerate(sm.get("submodelElements", [])):
            materialize_element(e, sm["id"], "", None, nodes)
        space["Submodels"].append({
            "NodeId": node_id(sm["id"], kind="S"),
            "BrowseName": browse_names[("submodels", index)],
            "TypeDefinition": "AASSubmodelType",
            "Members": {k: v for k, v in sm.items()
                        if k not in ("modelType", "submodelElements")},
            "ModelType": sm.get("modelType", "Submodel"),
            "Elements": [materialize_element(e, sm["id"], "", None, [])
                         for e in sm.get("submodelElements", [])],
            "HasElements": "submodelElements" in sm,
        })
    for index, cd in enumerate(env.get("conceptDescriptions", [])):
        space["Concepts"].append({
            "NodeId": node_id(cd["id"], kind="C"),
            "BrowseName": browse_names[
                ("conceptDescriptions", index)],
            "TypeDefinition": "AASConceptDescriptionType",
            "Members": {k: v for k, v in cd.items() if k != "modelType"},
            "ModelType": cd.get("modelType", "ConceptDescription"),
        })
    return space


# ---------------------------------------------------------------------------
# Serialization - the reverse direction
# ---------------------------------------------------------------------------
def serialize_element(node):
    model_type = node["Members"]["ModelType"]
    elem = {"modelType": model_type}
    child_field = CHILD_FIELDS.get(model_type)
    members = node["Members"]
    value_type = members.get("valueType")
    operation_member_names = {
        member_name for _, member_name in OPERATION_ROLES}
    for k, v in members.items():
        if (k in ("ModelType", "Index", "_emptyChildren", "_childReference")
                or k in operation_member_names):
            continue
        if k == "Value":
            # clause 8: emit the XSD canonical lexical representation of the value.
            elem["value"] = canonical_value(v, value_type)
            continue
        if model_type == "Range" and k in ("min", "max"):
            elem[k] = canonical_value(v, value_type)
            continue
        elem[k] = v
    if child_field:
        field, is_list = child_field
        kids = node["Children"]
        if kids:
            if is_list:
                kids = sorted(kids, key=lambda n: n["Members"]["Index"])  # clause 5.4
            elem[field] = [serialize_element(k) for k in kids]
        elif members.get("_emptyChildren"):
            elem[field] = []
    if model_type == "Operation":
        children_by_id = {child["NodeId"]: child for child in node["Children"]}
        if len(children_by_id) != len(node["Children"]):
            _fail("Operation has duplicate child NodeIds")
        if (node["Children"]
                and members.get("_childReference") != "HasComponent"):
            _fail(
                "Operation variable values must be direct HasComponent children")
        used = set()
        identifier = node["NodeId"].split(";s=", 1)[-1]
        kind, owner_id, operation_path = decode_node_identifier(identifier)
        if kind != "E" or operation_path is None:
            _fail(f"Operation has invalid NodeId {node['NodeId']!r}")
        for source_name, member_name in OPERATION_ROLES:
            if member_name not in members:
                continue
            wrappers = []
            for role_index, entry in enumerate(members[member_name]):
                if not isinstance(entry, dict) or set(entry) != {"ValueNodeId"}:
                    _fail(
                        f"{member_name}[{role_index}] is not one "
                        "AASOperationVariableDataType")
                target_id = entry["ValueNodeId"]
                child = children_by_id.get(target_id)
                if child is None:
                    _fail(
                        f"{member_name}[{role_index}].ValueNodeId "
                        f"{target_id!r} is not an Operation child")
                if target_id in used:
                    _fail(
                        f"Operation child {target_id!r} is referenced "
                        "by more than one variable wrapper")
                expected_id = node_id(
                    owner_id,
                    f"{operation_path}.{source_name}[{role_index}]")
                if target_id != expected_id:
                    _fail(
                        f"{member_name}[{role_index}].ValueNodeId "
                        f"{target_id!r}, expected {expected_id!r}")
                if child["Members"].get("Index") != role_index:
                    _fail(
                        f"{target_id}: Index "
                        f"{child['Members'].get('Index')!r}, "
                        f"expected {role_index}")
                expected_type = ELEMENT_TYPES.get(
                    child["Members"].get("ModelType"))
                if child["TypeDefinition"] != expected_type:
                    _fail(
                        f"{target_id}: TypeDefinition "
                        f"{child['TypeDefinition']!r}, "
                        f"expected {expected_type!r}")
                if child["BrowseName"] != child["Members"].get("idShort"):
                    _fail(
                        f"{target_id}: BrowseName does not equal the "
                        "operation variable value's idShort")
                used.add(target_id)
                wrappers.append({"value": serialize_element(child)})
            elem[source_name] = wrappers
        if used != set(children_by_id):
            _fail(
                "Operation has a <Variable> child that no role array references")
    return elem


def serialize(space):
    env = {}
    if space["Shells"]:
        env["assetAdministrationShells"] = [
            dict({"modelType": s["ModelType"]}, **s["Members"]) for s in space["Shells"]]
    if space["Submodels"]:
        out = []
        for s in space["Submodels"]:
            sm = dict({"modelType": s["ModelType"]}, **s["Members"])
            if s["HasElements"]:
                sm["submodelElements"] = [serialize_element(e) for e in s["Elements"]]
            out.append(sm)
        env["submodels"] = out
    if space["Concepts"]:
        env["conceptDescriptions"] = [
            dict({"modelType": c["ModelType"]}, **c["Members"]) for c in space["Concepts"]]
    expected_browse_names = identifiable_browse_names(env)
    for collection_name, _, _ in IDENTIFIABLE_GROUPS:
        source_nodes = {
            "assetAdministrationShells": space["Shells"],
            "submodels": space["Submodels"],
            "conceptDescriptions": space["Concepts"],
        }[collection_name]
        for index, node in enumerate(source_nodes):
            expected = expected_browse_names[(collection_name, index)]
            if node["BrowseName"] != expected:
                _fail(
                    f"{collection_name}[{index}] BrowseName "
                    f"{node['BrowseName']!r}, expected {expected!r}")
    return env


# ---------------------------------------------------------------------------
# Comparison - clause 8: equivalence, not byte equality
# ---------------------------------------------------------------------------
def canon(x):
    if isinstance(x, dict):
        return {k: canon(x[k]) for k in sorted(x)}
    if isinstance(x, list):
        return [canon(i) for i in x]
    return x


def _bag_key(x):
    return json.dumps(canon(x), sort_keys=True, ensure_ascii=False)


def equivalize(x):
    """Clause 8: reduce to the form equivalence is judged on.

    Values become their XSD canonical lexical representation, so that two lexical forms
    of one value compare equal. A SubmodelElementList whose orderRelevant is false is a
    bag, so its members are sorted into a deterministic order; an ordered list is left
    alone, because its order is part of what is being compared.
    """
    if isinstance(x, list):
        return [equivalize(i) for i in x]
    if not isinstance(x, dict):
        return x
    out = {k: equivalize(v) for k, v in x.items()}
    vt = out.get("valueType")
    if vt is not None:
        for field in ("value", "min", "max", "Value"):
            v = out.get(field)
            if isinstance(v, str):
                out[field] = canonical_value(v, vt)
    if out.get("modelType") == "SubmodelElementList" and out.get("orderRelevant") is False:
        members = out.get("value")
        if isinstance(members, list):
            out["value"] = sorted(members, key=_bag_key)
    if out.get("_childReference") == "HasComponent" and isinstance(out.get("Children"), list):
        out["Children"] = sorted(out["Children"], key=_bag_key)
    return out


def diff(a, b, path="$"):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                return f"{path}.{k}: missing after round trip"
            if k not in b:
                return f"{path}.{k}: appeared during round trip"
            d = diff(a[k], b[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return f"{path}: length {len(a)} became {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = diff(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    if a != b:
        return f"{path}: {a!r} became {b!r}"
    return None


def run(path):
    with open(path, encoding="utf-8") as f:
        env = json.load(f)
    space = materialize(env)
    back = serialize(space)
    d = diff(canon(equivalize(env)), canon(equivalize(back)))
    if d:
        return f"materialize/serialize: {d}"
    space2 = materialize(back)
    d = diff(canon(equivalize(space)), canon(equivalize(space2)))
    if d:
        return f"serialize/materialize: {d}"
    return None


# ---------------------------------------------------------------------------
# Negative control
# ---------------------------------------------------------------------------
# A round-trip check that cannot fail proves nothing. Each control below breaks exactly
# one of the normative rules and asserts the harness notices - so a green run above means
# the rules are load-bearing, not that the comparison is blind.
def _self_test():
    original = globals()["serialize_element"]

    def plain(node, reverse=False, drop_empty=False, corrupt_values=False,
              canonicalize=True, round_precision=0):
        mt = node["Members"]["ModelType"]
        elem = {"modelType": mt}
        members = node["Members"]
        vt = members.get("valueType")

        def out_value(v):
            if corrupt_values:
                try:
                    return str(float(v) + 1)   # a different value, not a re-writing
                except (TypeError, ValueError):
                    return (v or "") + "!"
            if round_precision and vt == "xs:decimal":
                with decimal.localcontext() as ctx:
                    ctx.prec = round_precision
                    return str(+decimal.Decimal(v))
            return canonical_value(v, vt) if canonicalize else v

        for k, v in members.items():
            if k in ("ModelType", "Index", "_emptyChildren", "_childReference"):
                continue
            if k == "Value":
                elem["value"] = out_value(v)
                continue
            if mt == "Range" and k in ("min", "max"):
                elem[k] = out_value(v)
                continue
            elem[k] = v
        cf = CHILD_FIELDS.get(mt)
        if cf:
            field, is_list = cf
            kids = node["Children"]
            if kids:
                if reverse:
                    kids = list(reversed(kids))
                elif is_list:
                    kids = sorted(kids, key=lambda n: n["Members"]["Index"])
                elem[field] = [plain(k, reverse, drop_empty, corrupt_values, canonicalize,
                                     round_precision)
                               for k in kids]
            elif members.get("_emptyChildren") and not drop_empty:
                elem[field] = []
        return elem

    controls = [
        ("clause 5.2 - a value altered rather than re-written",
         "non-canonical-lexical-forms.json",
         lambda n: plain(n, corrupt_values=True), True),
        # xs:decimal is arbitrary precision. Canonicalizing it through a fixed working
        # precision loses digits while still producing a plausible-looking decimal, and
        # loses them on both sides of the comparison, so nothing else here would notice.
        ("clause 7.1 - xs:decimal truncated to a working precision",
         "non-canonical-lexical-forms.json",
         lambda n: plain(n, round_precision=28), True),
        ("clause 5.4 - ordered list not restored from Index",
         "ordering-and-nesting.json",
         lambda n: plain(n, reverse=True), True),
        ("clause 5.5 - absent conflated with empty",
         "absent-versus-empty.json",
         lambda n: plain(n, drop_empty=True), True),
        # The converse control. Equivalence is value-based, so a serializer that re-writes
        # a value into its canonical lexical form must NOT be reported: a check that fires
        # on every difference is as useless as one that fires on none.
        ("clause 8 - canonical re-writing accepted as equivalent",
         "non-canonical-lexical-forms.json",
         lambda n: plain(n, canonicalize=True), False),
    ]

    ok = 0
    for name, fixture, broken, expect_error in controls:
        globals()["serialize_element"] = broken
        try:
            err = run(os.path.join(FIXTURES, fixture))
        finally:
            globals()["serialize_element"] = original
        if bool(err) == expect_error:
            ok += 1
            print(f"{'detected ' if expect_error else 'accepted '} {name}")
        else:
            print(f"MISSED     {name}" + (f" ({err})" if err else ""))
    print(f"\n{ok}/{len(controls)} controls behaved as specified")
    return 0 if ok == len(controls) else 1


def _artifact_self_test():
    root = ET.parse(NODESET).getroot()
    with open(NODEIDS, encoding="utf-8") as stream:
        csv_text = stream.read()
    with open(ANNEX, encoding="utf-8") as stream:
        annex_text = stream.read()
    with open(SCHEMA, encoding="utf-8") as stream:
        schema = json.load(stream)
    with open(SPEC, encoding="utf-8") as stream:
        spec_text = stream.read()

    controls = []

    def declaration(tree, owner_name, member_name):
        _, member, _ = _find_declaration(
            tree, _aliases(tree), owner_name, member_name)
        if member is None:
            raise AssertionError(
                f"test prerequisite {owner_name}.{member_name} is missing")
        return member

    def member_reference(member, aliases, reference_type):
        references = member.find(UANODESET_NS + "References")
        if references is None:
            raise AssertionError("test prerequisite References is missing")
        return next(
            reference for reference in references
            if (_resolved(reference.get("ReferenceType"), aliases)
                == reference_type)
        )

    def structure_field(tree, structure_name, field_name):
        structure = next(
            node for node in tree
            if _local_browse_name(node) == structure_name)
        definition = structure.find(UANODESET_NS + "Definition")
        if definition is None:
            raise AssertionError(
                f"test prerequisite {structure_name} Definition is missing")
        return next(
            field for field in definition.findall(UANODESET_NS + "Field")
            if field.get("Name") == field_name)

    optionality = copy.deepcopy(root)
    reference_type = next(
        node for node in optionality
        if _local_browse_name(node) == "AASReferenceDataType")
    referred = next(
        field for field in reference_type.find(
            UANODESET_NS + "Definition").findall(UANODESET_NS + "Field")
        if field.get("Name") == "ReferredSemanticId")
    referred.attrib.pop("IsOptional", None)
    controls.append((
        "generated Structure optionality mutation",
        validate_generated_artifacts(
            optionality, csv_text, annex_text, schema)))

    iec_data_type = copy.deepcopy(root)
    structure_field(
        iec_data_type,
        "AASDataSpecificationIec61360DataType",
        "ValueList").set("DataType", "String")
    controls.append((
        "IEC 61360 ValueList DataType mutation",
        validate_generated_artifacts(
            iec_data_type, csv_text, annex_text, schema)))

    iec_pair_optional = copy.deepcopy(root)
    structure_field(
        iec_pair_optional,
        "AASValueReferencePairDataType",
        "ValueId").set("IsOptional", "true")
    controls.append((
        "IEC 61360 ValueReferencePair cardinality mutation",
        validate_generated_artifacts(
            iec_pair_optional, csv_text, annex_text, schema)))

    iec_value_rank = copy.deepcopy(root)
    structure_field(
        iec_value_rank,
        "AASValueListDataType",
        "ValueReferencePairs").set("ValueRank", "-1")
    controls.append((
        "IEC 61360 ValueList ValueRank mutation",
        validate_generated_artifacts(
            iec_value_rank, csv_text, annex_text, schema)))

    iec_level_optional = copy.deepcopy(root)
    structure_field(
        iec_level_optional,
        "AASLevelTypeDataType",
        "Min").set("IsOptional", "true")
    controls.append((
        "IEC 61360 LevelType cardinality mutation",
        validate_generated_artifacts(
            iec_level_optional, csv_text, annex_text, schema)))

    containment = copy.deepcopy(root)
    owner, child, _ = _find_declaration(
        containment, _aliases(containment),
        "AASSubmodelElementCollectionType", "<SubmodelElement>")
    owner_ref = next(
        reference for reference in owner.find(
            UANODESET_NS + "References")
        if reference.text == child.get("NodeId"))
    owner_ref.set("ReferenceType", "Organizes")
    controls.append((
        "generated containment ReferenceType mutation",
        validate_generated_artifacts(
            containment, csv_text, annex_text, schema)))

    data_type = copy.deepcopy(root)
    declaration(
        data_type, "AASPropertyType", "Value").set("DataType", "String")
    controls.append((
        "generated member DataType mutation",
        validate_generated_artifacts(
            data_type, csv_text, annex_text, schema)))

    value_rank = copy.deepcopy(root)
    declaration(
        value_rank, "AASMultiLanguagePropertyType", "Value").set(
            "ValueRank", "-1")
    controls.append((
        "generated member ValueRank mutation",
        validate_generated_artifacts(
            value_rank, csv_text, annex_text, schema)))

    modelling_rule = copy.deepcopy(root)
    modelling_member = declaration(
        modelling_rule, "AASPropertyType", "Value")
    member_reference(
        modelling_member, _aliases(modelling_rule), "i=37").text = "i=78"
    controls.append((
        "generated member ModellingRule mutation",
        validate_generated_artifacts(
            modelling_rule, csv_text, annex_text, schema)))

    type_definition = copy.deepcopy(root)
    type_member = declaration(
        type_definition, "AASPropertyType", "Value")
    member_reference(
        type_member, _aliases(type_definition), "i=40").text = "i=63"
    controls.append((
        "generated member TypeDefinition mutation",
        validate_generated_artifacts(
            type_definition, csv_text, annex_text, schema)))

    browse_name = copy.deepcopy(root)
    declaration(
        browse_name, "AASPropertyType", "Value").set(
            "BrowseName", "2:WrongValue")
    controls.append((
        "generated member BrowseName mutation",
        validate_generated_artifacts(
            browse_name, csv_text, annex_text, schema)))

    node_class = copy.deepcopy(root)
    declaration(
        node_class, "AASPropertyType", "Value").tag = UANODESET_NS + "UAObject"
    controls.append((
        "generated member NodeClass mutation",
        validate_generated_artifacts(
            node_class, csv_text, annex_text, schema)))

    parent = copy.deepcopy(root)
    declaration(
        parent, "AASPropertyType", "Value").set(
            "ParentNodeId", "ns=2;i=1020")
    controls.append((
        "generated member parent mutation",
        validate_generated_artifacts(
            parent, csv_text, annex_text, schema)))

    supertype = copy.deepcopy(root)
    property_type = next(
        node for node in supertype
        if _local_browse_name(node) == "AASPropertyType")
    member_reference(
        property_type, _aliases(supertype), "i=45").text = "i=58"
    controls.append((
        "generated ObjectType supertype mutation",
        validate_generated_artifacts(
            supertype, csv_text, annex_text, schema)))

    method_declaration = copy.deepcopy(root)
    concrete_get_submodel = next(
        node for node in method_declaration
        if (_node_class(node) == "Method"
            and _local_browse_name(node) == "GetSubmodel"
            and node.get("ParentNodeId") == "ns=2;i=1150"))
    concrete_get_submodel.attrib.pop("MethodDeclarationId", None)
    controls.append((
        "concrete MethodDeclarationId mutation",
        validate_generated_artifacts(
            method_declaration, csv_text, annex_text, schema)))

    method_security = copy.deepcopy(root)
    get_submodel = next(
        node for node in method_security
        if (_node_class(node) == "Method"
            and _local_browse_name(node) == "GetSubmodel"
            and node.get("ParentNodeId") == "ns=2;i=1100"))
    get_submodel_description = get_submodel.find(
        UANODESET_NS + "Description")
    get_submodel_description.text = get_submodel_description.text.replace(
        "UserRolePermissions", "UserPermissions", 1)
    controls.append((
        "GetSubmodel target-authorization Description mutation",
        validate_generated_artifacts(
            method_security, csv_text, annex_text, schema, spec_text)))

    get_submodel_spec = spec_text.replace(
        "`Bad_UserAccessDenied`", "`Bad_SecurityChecksFailed`", 1)
    controls.append((
        "GetSubmodel security prose mutation",
        validate_generated_artifacts(
            root, csv_text, annex_text, schema, get_submodel_spec)))

    federation_spec = spec_text.replace(
        "prevent DNS rebinding", "permit DNS rebinding", 1)
    controls.append((
        "federation egress security prose mutation",
        validate_generated_artifacts(
            root, csv_text, annex_text, schema, federation_spec)))

    package_digest_optional = copy.deepcopy(root)
    digest_member = declaration(
        package_digest_optional, "AASPackageFileType", "Digest")
    member_reference(
        digest_member, _aliases(package_digest_optional),
        "i=37").text = "i=80"
    controls.append((
        "package Digest cardinality mutation",
        validate_generated_artifacts(
            package_digest_optional, csv_text, annex_text, schema, spec_text)))

    package_digest_prefix = copy.deepcopy(root)
    digest_description = declaration(
        package_digest_prefix, "AASPackageFileType",
        "Digest").find(UANODESET_NS + "Description")
    digest_description.text = digest_description.text.replace(
        "without an algorithm prefix", "including an algorithm prefix", 1)
    controls.append((
        "package Digest prefix mutation",
        validate_generated_artifacts(
            package_digest_prefix, csv_text, annex_text, schema, spec_text)))

    package_digest_alg_optional = copy.deepcopy(root)
    digest_alg_member = declaration(
        package_digest_alg_optional, "AASPackageFileType", "DigestAlg")
    member_reference(
        digest_alg_member, _aliases(package_digest_alg_optional),
        "i=37").text = "i=80"
    controls.append((
        "package DigestAlg cardinality mutation",
        validate_generated_artifacts(
            package_digest_alg_optional, csv_text, annex_text, schema,
            spec_text)))

    package_digest_alg_spelling = copy.deepcopy(root)
    digest_alg_description = declaration(
        package_digest_alg_spelling, "AASPackageFileType",
        "DigestAlg").find(UANODESET_NS + "Description")
    digest_alg_description.text = digest_alg_description.text.replace(
        "Sha512", "SHA512", 1)
    controls.append((
        "package DigestAlg exact-case mutation",
        validate_generated_artifacts(
            package_digest_alg_spelling, csv_text, annex_text, schema,
            spec_text)))

    package_category = copy.deepcopy(root)
    package_type = next(
        node for node in package_category
        if _local_browse_name(node) == "AASPackageFileType")
    integrity_category = next(
        category for category in package_type.findall(
            UANODESET_NS + "Category")
        if category.text == "AAS-PackageIntegrity")
    package_type.remove(integrity_category)
    controls.append((
        "package integrity conformance-unit mutation",
        validate_generated_artifacts(
            package_category, csv_text, annex_text, schema, spec_text)))

    manifest_semantics = copy.deepcopy(root)
    manifest_member = declaration(
        manifest_semantics, "AASPackageFileType", "ManifestDigest")
    manifest_description = manifest_member.find(
        UANODESET_NS + "Description")
    manifest_description.text = manifest_description.text.replace(
        "tag is never identity", "tag may be identity", 1)
    controls.append((
        "package ManifestDigest semantics mutation",
        validate_generated_artifacts(
            manifest_semantics, csv_text, annex_text, schema, spec_text)))

    manifest_chain = copy.deepcopy(root)
    manifest_chain_member = declaration(
        manifest_chain, "AASPackageFileType", "ManifestDigest")
    manifest_chain_description = manifest_chain_member.find(
        UANODESET_NS + "Description")
    manifest_chain_description.text = manifest_chain_description.text.replace(
        "exactly one package-layer descriptor",
        "one or more package-layer descriptors", 1)
    controls.append((
        "package manifest-to-blob binding mutation",
        validate_generated_artifacts(
            manifest_chain, csv_text, annex_text, schema, spec_text)))

    package_spec = spec_text.replace("`Sha512`", "`SHA512`")
    controls.append((
        "package integrity prose mutation",
        validate_generated_artifacts(
            root, csv_text, annex_text, schema, package_spec)))

    package_referrer_spec = spec_text.replace(
        "represented as a separate immutable Resource",
        "represented as a Version of the package Resource", 1)
    controls.append((
        "package referrer separation prose mutation",
        validate_generated_artifacts(
            root, csv_text, annex_text, schema, package_referrer_spec)))

    package_default_spec = spec_text.replace(
        "**shall not** change that package Resource's Version collection",
        "**may** change that package Resource's Version collection", 1)
    controls.append((
        "package referrer default-Version mutation",
        validate_generated_artifacts(
            root, csv_text, annex_text, schema, package_default_spec)))

    package_attestation_summary = copy.deepcopy(root)
    package_type = next(
        node for node in package_attestation_summary
        if node.get("NodeId") == "ns=2;i=1107")
    attestation_member = next(
        node for node in package_attestation_summary
        if node.get("NodeId") == "ns=2;i=5169")
    attestation_member.set("ParentNodeId", "ns=2;i=1107")
    ET.SubElement(
        attestation_member.find(UANODESET_NS + "References"),
        UANODESET_NS + "Reference",
        {"ReferenceType": "HasModellingRule"}).text = "i=80"
    ET.SubElement(
        attestation_member.find(UANODESET_NS + "References"),
        UANODESET_NS + "Reference",
        {"ReferenceType": "HasProperty", "IsForward": "false"}
    ).text = "ns=2;i=1107"
    ET.SubElement(
        package_type.find(UANODESET_NS + "References"),
        UANODESET_NS + "Reference",
        {"ReferenceType": "HasProperty"}).text = "ns=2;i=5169"
    controls.append((
        "package attestation declaration mutation",
        validate_generated_artifacts(
            package_attestation_summary, csv_text, annex_text, schema,
            spec_text)))

    annex_data_type = annex_text.replace(
        "| Value | Variable | BaseDataType | Optional | AASPropertyType |",
        "| Value | Variable | String | Optional | AASPropertyType |",
        1)
    controls.append((
        "generated Annex member DataType mutation",
        validate_generated_artifacts(
            root, csv_text, annex_data_type, schema)))

    annex_lines = annex_text.splitlines(keepends=True)
    property_start = next(
        index for index, line in enumerate(annex_lines)
        if line.startswith("#### AASPropertyType  "))
    property_end = next(
        index for index in range(property_start + 1, len(annex_lines))
        if annex_lines[index].startswith("#### "))
    value_row = next(
        index for index in range(property_start, property_end)
        if annex_lines[index].startswith(
            "| Value | Variable | BaseDataType |"))
    annex_missing_row = "".join(
        annex_lines[:value_row] + annex_lines[value_row + 1:])
    controls.append((
        "generated Annex member row deletion",
        validate_generated_artifacts(
            root, csv_text, annex_missing_row, schema)))

    annex_iec_data_type = annex_text.replace(
        "| ValueList | [AASValueListDataType](#type-AASValueListDataType) "
        "| Optional |",
        "| ValueList | String | Optional |",
        1)
    controls.append((
        "IEC 61360 Annex field DataType mutation",
        validate_generated_artifacts(
            root, csv_text, annex_iec_data_type, schema)))

    annex_package_rule = annex_text.replace(
        "| Digest | Variable | String | Mandatory | AASPackageFileType |",
        "| Digest | Variable | String | Optional | AASPackageFileType |",
        1)
    controls.append((
        "package integrity Annex cardinality mutation",
        validate_generated_artifacts(
            root, csv_text, annex_package_rule, schema, spec_text)))

    rebound = copy.deepcopy(root)
    model = rebound.find(f"{UANODESET_NS}Models/{UANODESET_NS}Model")
    model.set("ModelUri", PUBLISHED_NAMESPACE)
    for uri in rebound.findall(
            f"{UANODESET_NS}NamespaceUris/{UANODESET_NS}Uri"):
        if uri.text == MODEL_NAMESPACE:
            uri.text = PUBLISHED_NAMESPACE
    controls.append((
        "published namespace NodeId rebinding mutation",
        validate_generated_artifacts(
            rebound, csv_text, annex_text, schema)))

    annex_ns = annex_text.replace(
        "| ns=2;i=1031 |", "| ns=1;i=1031 |", 1)
    controls.append((
        "generated Annex namespace mutation",
        validate_generated_artifacts(root, csv_text, annex_ns, schema)))

    detected = 0
    for name, errors in controls:
        if errors:
            detected += 1
            print(f"detected  {name}")
        else:
            print(f"MISSED    {name}")

    fields = _structure_definitions(
        root, _aliases(root))["AASReferenceDataType"]
    absent = {
        "Type": "ModelReference",
        "Keys": [{"Type": "Submodel", "Value": "urn:example"}],
    }
    present_default = dict(absent, ReferredSemanticId=None)
    absent_after = _structure_presence_roundtrip(fields, absent)
    present_after = _structure_presence_roundtrip(fields, present_default)
    presence_ok = (
        "ReferredSemanticId" not in absent_after
        and "ReferredSemanticId" in present_after
        and present_after["ReferredSemanticId"] is None
    )
    print(
        f"{'preserved ' if presence_ok else 'LOST      '}"
        "Reference.referredSemanticId absent versus present-default")
    if presence_ok:
        detected += 1

    total = len(controls) + 1
    print(f"\n{detected}/{total} generated-artifact controls behaved as specified")
    return 0 if detected == total else 1


def _nodeid_self_test():
    pairs = [
        (node_identifier("A", "a#b"), node_identifier("E", "a", "b")),
        (node_identifier("E", "a", "bc"), node_identifier("E", "ab", "c")),
        (node_identifier("A", "same"), node_identifier("S", "same")),
        (node_identifier("S", "a\nb"), node_identifier("S", "a%0Ab")),
        (node_identifier("S", "a\0b"), node_identifier("S", "a%00b")),
    ]
    unique = all(left != right for left, right in pairs)
    samples = [
        ("A", "a#b", None),
        ("S", "urn:example:ä", None),
        ("C", "0173-1#02-AAO677#002", None),
        ("E", "a#b", "Collection.Child[10]"),
        ("S", "line\nbreak", None),
        ("S", "nul\0inside", None),
        ("S", "c1\u0085inside", None),
        ("E", "owner\nid", "Path\0Child\u0085"),
        ("C", "literal%0A", None),
    ]
    reversible = all(
        decode_node_identifier(node_identifier(kind, owner, path))
        == (kind, owner, path)
        for kind, owner, path in samples
    )
    exact_escapes = (
        (node_identifier("S", "a\nb"), "i4aas3:S:5:a%0Ab"),
        (node_identifier("S", "a\0b"), "i4aas3:S:5:a%00b"),
        (node_identifier("S", "\u0085"), "i4aas3:S:6:%C2%85"),
        (node_identifier("S", "%0A"), "i4aas3:S:5:%250A"),
    )
    escaping_ok = (
        all(actual == expected for actual, expected in exact_escapes)
        and all(
            not any(ord(character) <= 0x1F
                    or 0x7F <= ord(character) <= 0x9F
                    for character in identifier)
            for identifier, _ in exact_escapes
        )
    )
    invalid_encodings = (
        "i4aas3:S:3:a\nb",
        "i4aas3:S:3:%0a",
        "i4aas3:S:3:%41",
        "i4aas3:S:2:%0",
        "i4aas3:S:3:%FF",
        "i4aas3:S:01:a",
        "i4aas3:S:\u0661:x",
        f"i4aas3:S:{MAX_STRING_NODEID_LENGTH}:"
        f"{'x' * MAX_STRING_NODEID_LENGTH}",
    )
    canonical_rejection = True
    for identifier in invalid_encodings:
        try:
            decode_node_identifier(identifier)
        except ValueError:
            continue
        canonical_rejection = False
        break

    max_owner = max(
        length for length in range(MAX_STRING_NODEID_LENGTH + 1)
        if len(f"i4aas3:S:{length}:{'x' * length}")
        <= MAX_STRING_NODEID_LENGTH
    )
    boundary_identifier = node_identifier("S", "x" * max_owner)
    boundary_ok = (
        len(boundary_identifier) == MAX_STRING_NODEID_LENGTH
    )
    try:
        node_identifier("S", "x" * (max_owner + 1))
    except ValueError:
        overlength_rejected = True
    else:
        overlength_rejected = False

    control_prefix = "\0" * 100
    control_tail = max(
        length for length in range(MAX_STRING_NODEID_LENGTH + 1)
        if len(
            f"i4aas3:S:{len(_encode_nodeid_component(control_prefix + 'x' * length))}:"
            f"{_encode_nodeid_component(control_prefix + 'x' * length)}")
        <= MAX_STRING_NODEID_LENGTH
    )
    control_boundary = node_identifier(
        "S", control_prefix + "x" * control_tail)
    try:
        node_identifier("S", control_prefix + "x" * (control_tail + 1))
    except ValueError:
        control_overlength_rejected = True
    else:
        control_overlength_rejected = False
    escaped_boundary_ok = (
        len(control_boundary) == MAX_STRING_NODEID_LENGTH
        and control_overlength_rejected
    )

    max_path = max(
        length for length in range(MAX_STRING_NODEID_LENGTH + 1)
        if len(f"i4aas3:E:1:{length}:o{'x' * length}")
        <= MAX_STRING_NODEID_LENGTH
    )
    element_boundary = node_identifier("E", "o", "x" * max_path)
    try:
        node_identifier("E", "o", "x" * (max_path + 1))
    except ValueError:
        element_overlength_rejected = True
    else:
        element_overlength_rejected = False
    element_boundary_ok = (
        len(element_boundary) == MAX_STRING_NODEID_LENGTH
        and element_overlength_rejected
    )

    with open(SPEC, encoding="utf-8") as stream:
        spec_text = stream.read()
    spec_examples = all(identifier in spec_text for identifier in (
        node_identifier("A", "a#b"),
        node_identifier("E", "a", "b"),
        node_identifier("S", "a\nb"),
        node_identifier("S", "a\0b"),
        node_identifier("S", "\u0085"),
        node_identifier("S", "%0A"),
        node_identifier("S", "https://fabrikam.com/ids/sm/ordering"),
        node_identifier(
            "E", "https://fabrikam.com/ids/sm/ordering",
            "CollectionsInsideAList[0]"),
    ))

    checks = [
        ("node-kind and owner/path collision resistance", unique),
        ("control-free canonical component escaping",
         escaping_ok and canonical_rejection),
        ("escaped length-prefixed NodeId reversibility", reversible),
        ("4096-character identifiable NodeId boundary",
         boundary_ok and overlength_rejected),
        ("4096-character escaped-component boundary", escaped_boundary_ok),
        ("4096-character element NodeId boundary", element_boundary_ok),
        ("specification NodeId examples", spec_examples),
    ]
    for name, ok in checks:
        print(f"{'ok        ' if ok else 'FAIL      '}{name}")
    return 0 if all(ok for _, ok in checks) else 1


def _identifiable_browse_name_self_test():
    identifier = "urn:example:identifier\nwith\0controls"
    expected = (
        "AssetAdministrationShell_"
        "61ad70a2ef78e2769dac842ca25846e2ae1a16c436536de4ddb7354b7992d210")
    control_environment = {
        "assetAdministrationShells": [{
            "modelType": "AssetAdministrationShell",
            "id": identifier,
        }],
    }
    control_name = materialize(
        control_environment)["Shells"][0]["BrowseName"]
    safe_name_ok = (
        control_name == expected
        and identifier not in control_name
        and not any(
            ord(character) <= 0x1F
            or 0x7F <= ord(character) <= 0x9F
            for character in control_name)
    )
    mutated_space = materialize(control_environment)
    mutated_space["Shells"][0]["BrowseName"] = identifier
    try:
        serialize(mutated_space)
    except AssertionError:
        browse_name_mutation_caught = True
    else:
        browse_name_mutation_caught = False

    digest = "0" * 64

    def constant_digest(_):
        return digest

    def assignments(environment):
        names = identifiable_browse_names(
            environment, digest_function=constant_digest)
        return {
            value["id"]: names[("assetAdministrationShells", index)]
            for index, value in enumerate(
                environment["assetAdministrationShells"])
        }

    first = {
        "assetAdministrationShells": [
            {"id": "urn:example:z"},
            {"id": "urn:example:a"},
        ],
    }
    second = {
        "assetAdministrationShells": list(reversed(
            first["assetAdministrationShells"])),
    }
    base = f"AssetAdministrationShell_{digest}"
    collision_ok = (
        assignments(first) == assignments(second) == {
            "urn:example:a": base,
            "urn:example:z": f"{base}_0",
        }
    )

    explicit_collision = {
        "assetAdministrationShells": [{"id": "urn:example:a"}],
        "conceptDescriptions": [{
            "id": "urn:example:concept",
            "idShort": base,
        }],
    }
    explicit_names = identifiable_browse_names(
        explicit_collision, digest_function=constant_digest)
    disambiguation_ok = (
        explicit_names[("assetAdministrationShells", 0)] == f"{base}_0"
        and explicit_names[("conceptDescriptions", 0)] == base
    )

    duplicate_rejected = False
    try:
        identifiable_browse_names({
            "submodels": [
                {"id": "urn:example:duplicate"},
                {"id": "urn:example:duplicate"},
            ],
        })
    except AssertionError:
        duplicate_rejected = True

    invalid_id_short_rejected = True
    for invalid in ("", None):
        try:
            identifiable_browse_names({
                "conceptDescriptions": [{
                    "id": "urn:example:concept",
                    "idShort": invalid,
                }],
            })
        except AssertionError:
            continue
        invalid_id_short_rejected = False
        break

    checks = [
        ("control-safe identifiable BrowseName", safe_name_ok),
        ("identifiable BrowseName mutation", browse_name_mutation_caught),
        ("deterministic derived BrowseName collision suffix", collision_ok),
        ("derived BrowseName avoids explicit-name collision",
         disambiguation_ok),
        ("duplicate identifiable identifier rejection", duplicate_rejected),
        ("invalid identifiable idShort rejection",
         invalid_id_short_rejected),
    ]
    for name, ok in checks:
        print(f"{'ok        ' if ok else 'FAIL      '}{name}")
    return 0 if all(ok for _, ok in checks) else 1


def _operation_contract_self_test():
    with open(
            os.path.join(FIXTURES, "every-element-type.json"),
            encoding="utf-8") as stream:
        source = json.load(stream)
    source_operation = next(
        element
        for element in source["submodels"][0]["submodelElements"]
        if element.get("modelType") == "Operation")
    space = materialize(source)

    def descendants(nodes):
        for candidate in nodes:
            yield candidate
            yield from descendants(candidate["Children"])

    operation = next(
        candidate
        for candidate in descendants(space["Submodels"][0]["Elements"])
        if candidate["Members"].get("ModelType") == "Operation")
    expected = {
        "InputVariables": (
            ("AnOperation.inputVariables[0]", "InputTemperature", 0),
            ("AnOperation.inputVariables[1]", "InputPressure", 1),
        ),
        "OutputVariables": (
            ("AnOperation.outputVariables[0]", "OutputAccepted", 0),
        ),
        "InoutputVariables": (
            ("AnOperation.inoutputVariables[0]", "InoutputCounter", 0),
        ),
    }
    owner = source["submodels"][0]["id"]
    children_by_id = {
        child["NodeId"]: child for child in operation["Children"]}
    contract_ok = (
        operation["Members"].get("_childReference") == "HasComponent"
        and len(children_by_id) == 4
    )
    for member_name, entries in expected.items():
        expected_structures = [
            {"ValueNodeId": node_id(owner, path)}
            for path, _, _ in entries
        ]
        contract_ok = (
            contract_ok
            and operation["Members"].get(member_name) == expected_structures
        )
        for path, browse_name_value, index in entries:
            child = children_by_id.get(node_id(owner, path))
            contract_ok = (
                contract_ok
                and child is not None
                and child["BrowseName"] == browse_name_value
                and child["TypeDefinition"] == "AASPropertyType"
                and child["Members"].get("idShort") == browse_name_value
                and child["Members"].get("Index") == index
            )

    serialized_ok = (
        canon(serialize_element(operation)) == canon(source_operation))

    empty_source = {
        "modelType": "Operation",
        "idShort": "EmptyOperation",
        "inputVariables": [],
    }
    empty_node = materialize_element(
        empty_source, "urn:example:operation", "", None, [])
    empty_back = serialize_element(empty_node)
    presence_ok = (
        empty_node["Members"].get("InputVariables") == []
        and "OutputVariables" not in empty_node["Members"]
        and empty_back == empty_source
    )

    def mutation_caught(change):
        mutated = copy.deepcopy(operation)
        change(mutated)
        try:
            serialize_element(mutated)
        except AssertionError:
            return True
        return False

    wrong_target = mutation_caught(
        lambda node: node["Members"]["InputVariables"][0].__setitem__(
            "ValueNodeId", node["NodeId"]))
    wrong_index = mutation_caught(
        lambda node: node["Children"][0]["Members"].__setitem__("Index", 9))
    wrong_reference = mutation_caught(
        lambda node: node["Members"].__setitem__(
            "_childReference", "HasOrderedComponent"))
    duplicate_target = mutation_caught(
        lambda node: node["Members"]["InputVariables"][1].__setitem__(
            "ValueNodeId",
            node["Members"]["InputVariables"][0]["ValueNodeId"]))
    wrong_browse_name = mutation_caught(
        lambda node: node["Children"][0].__setitem__(
            "BrowseName", "WrongBrowseName"))
    wrong_type_definition = mutation_caught(
        lambda node: node["Children"][0].__setitem__(
            "TypeDefinition", "AASFileType"))

    def invalid_source_rejected(candidate):
        try:
            materialize_element(
                candidate, "urn:example:operation", "", None, [])
        except AssertionError:
            return True
        return False

    missing_value = invalid_source_rejected({
        "modelType": "Operation",
        "idShort": "InvalidOperation",
        "inputVariables": [{}],
    })
    missing_id_short = invalid_source_rejected({
        "modelType": "Operation",
        "idShort": "InvalidOperation",
        "inputVariables": [{
            "value": {
                "modelType": "Property",
                "valueType": "xs:string",
            },
        }],
    })

    checks = [
        ("Operation wrappers reference direct value children", contract_ok),
        ("Operation wrapper roles round-trip", serialized_ok),
        ("Operation absent versus empty roles", presence_ok),
        ("Operation ValueNodeId mutation", wrong_target),
        ("Operation role Index mutation", wrong_index),
        ("Operation ReferenceType mutation", wrong_reference),
        ("Operation duplicate child mutation", duplicate_target),
        ("Operation BrowseName mutation", wrong_browse_name),
        ("Operation TypeDefinition mutation", wrong_type_definition),
        ("Operation wrapper without value", missing_value),
        ("Operation value without idShort", missing_id_short),
    ]
    for name, ok in checks:
        print(f"{'ok        ' if ok else 'FAIL      '}{name}")
    return 0 if all(ok for _, ok in checks) else 1


def _iec61360_structure_self_test():
    with open(SCHEMA, encoding="utf-8") as stream:
        schema = json.load(stream)

    def objects(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from objects(child)
        elif isinstance(value, list):
            for child in value:
                yield from objects(child)

    checked = 0
    vendor_ok = True
    for file_name in sorted(os.listdir(VENDORED_TEMPLATES)):
        if not file_name.endswith(".json"):
            continue
        with open(
                os.path.join(VENDORED_TEMPLATES, file_name),
                encoding="utf-8") as stream:
            document = json.load(stream)
        for candidate in objects(document):
            if (candidate.get("modelType") != "DataSpecificationIec61360"
                    or not ({"valueList", "levelType"} & set(candidate))):
                continue
            encoded = _encode_source_structure(
                "AASDataSpecificationIec61360DataType",
                candidate, schema)
            decoded = _decode_source_structure(
                "AASDataSpecificationIec61360DataType",
                encoded, schema)
            if canon(candidate) != canon(decoded):
                vendor_ok = False
            checked += 1

    synthetic = {
        "preferredName": [{"language": "en", "text": "Rated value"}],
        "valueList": {
            "valueReferencePairs": [{
                "value": "nominal",
                "valueId": {
                    "type": "ExternalReference",
                    "keys": [{
                        "type": "GlobalReference",
                        "value": "urn:example:nominal",
                    }],
                },
            }],
        },
        "levelType": {
            "min": False,
            "nom": True,
            "typ": False,
            "max": False,
        },
        "modelType": "DataSpecificationIec61360",
    }
    encoded = _encode_source_structure(
        "AASDataSpecificationIec61360DataType", synthetic, schema)
    decoded = _decode_source_structure(
        "AASDataSpecificationIec61360DataType", encoded, schema)
    structured_ok = (
        canon(decoded) == canon(synthetic)
        and encoded["ValueList"] == {
            "ValueReferencePairs": [{
                "Value": "nominal",
                "ValueId": {
                    "Type": "ExternalReference",
                    "Keys": [{
                        "Type": "GlobalReference",
                        "Value": "urn:example:nominal",
                    }],
                },
            }],
        }
        and encoded["LevelType"] == {
            "Min": False, "Nom": True, "Typ": False, "Max": False,
        }
    )
    absent = {
        "preferredName": [{"language": "en", "text": "No optional values"}],
        "modelType": "DataSpecificationIec61360",
    }
    absent_encoded = _encode_source_structure(
        "AASDataSpecificationIec61360DataType", absent, schema)
    presence_ok = (
        "ValueList" not in absent_encoded
        and "LevelType" not in absent_encoded
        and _decode_source_structure(
            "AASDataSpecificationIec61360DataType",
            absent_encoded, schema) == absent
    )
    empty_value_list_rejected = False
    try:
        _encode_source_structure(
            "AASDataSpecificationIec61360DataType",
            dict(synthetic, valueList={"valueReferencePairs": []}),
            schema)
    except ValueError:
        empty_value_list_rejected = True
    empty_encoded_value_list_rejected = False
    malformed_encoded = copy.deepcopy(encoded)
    malformed_encoded["ValueList"]["ValueReferencePairs"] = []
    try:
        _decode_source_structure(
            "AASDataSpecificationIec61360DataType",
            malformed_encoded, schema)
    except ValueError:
        empty_encoded_value_list_rejected = True

    checks = [
        (f"{checked} vendored IEC 61360 value-list cases round-trip",
         vendor_ok and checked > 0),
        ("IEC 61360 nested Structure mapping", structured_ok),
        ("IEC 61360 optional Structure presence", presence_ok),
        ("IEC 61360 non-empty ValueList",
         empty_value_list_rejected and empty_encoded_value_list_rejected),
    ]
    for name, ok in checks:
        print(f"{'ok        ' if ok else 'FAIL      '}{name}")
    return 0 if all(ok for _, ok in checks) else 1


def main():
    artifact_errors = validate_generated_artifacts()
    if artifact_errors:
        print("generated model validation failed:")
        for error in artifact_errors:
            print("  ERR", error)
        return 1
    print(
        "ok   generated NodeSet, CSV, all ObjectType declarations, "
        "Structure cardinalities and Annex A")

    if not os.path.isdir(FIXTURES):
        print(f"no fixture corpus at {FIXTURES}", file=sys.stderr)
        return 1
    names = sorted(n for n in os.listdir(FIXTURES) if n.endswith(".json"))
    if not names:
        print("fixture corpus is empty", file=sys.stderr)
        return 1
    failed = 0
    for n in names:
        err = run(os.path.join(FIXTURES, n))
        if err:
            print(f"FAIL {n}: {err}")
            failed += 1
        else:
            print(f"ok   {n}")
    print(f"\n{len(names) - failed}/{len(names)} fixtures round-trip losslessly")
    if failed:
        return 1
    print()
    results = [
        _self_test(),
        _artifact_self_test(),
        _nodeid_self_test(),
        _identifiable_browse_name_self_test(),
        _operation_contract_self_test(),
        _iec61360_structure_self_test(),
    ]
    return 1 if any(results) else 0


if __name__ == "__main__":
    sys.exit(main())
