"""The canonical reversibility corpus.

A single, shared set of ``(name, type, value)`` cases that every encoding
extension (Avro / Protobuf / Arrow) — and the JSON control — must round-trip
losslessly: ``decode(type, encode(type, value))`` must ``canonical_equal`` the
original ``value``.

The corpus deliberately exercises the hard cases from the design matrix: every
built-in type at its edges, 1-D arrays (incl. null elements), multi-dimensional
matrices, plain/optional/union structures, subtyped ExtensionObject fields,
enumerations & option sets, recursive DiagnosticInfo, Variant (scalar/array/
matrix/ExtensionObject bodies) and the null-vs-empty-vs-absent distinctions.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import types as t
from . import values as v

INT64_MAX = 2**63 - 1
UINT64_MAX = 2**64 - 1


@dataclass(frozen=True)
class Case:
    name: str
    type: t.Type
    value: Any


def _guid(seed: int) -> v.Guid:
    return v.Guid(bytes((seed + i) % 256 for i in range(16)))


# --------------------------------------------------------------------------
# Sample structured DataTypes (provisional NodeIds in a free block)
# --------------------------------------------------------------------------
POINT = t.Struct(
    "Point",
    (t.Field("X", t.DOUBLE), t.Field("Y", t.DOUBLE)),
    t.StructureKind.STRUCTURE,
    type_id="i=3001",
    encoding_id="i=3002",
)

PERSON = t.Struct(
    "Person",
    (
        t.Field("Name", t.STRING),
        t.Field("Age", t.INT32),
        t.Field("Email", t.STRING, is_optional=True),
        t.Field("Nickname", t.STRING, is_optional=True),
    ),
    t.StructureKind.STRUCTURE_WITH_OPTIONAL_FIELDS,
    type_id="i=3010",
    encoding_id="i=3011",
)

MEASUREMENT = t.Struct(
    "Measurement",
    (
        t.Field("AsInt", t.INT32),
        t.Field("AsText", t.STRING),
        t.Field("AsPoint", POINT),
    ),
    t.StructureKind.UNION,
    type_id="i=3020",
    encoding_id="i=3021",
)

ENVELOPE = t.Struct(
    "Envelope",
    (
        t.Field("Id", t.STRING),
        t.Field("Location", POINT),
        t.Field("Tags", t.Array(t.STRING)),
        t.Field("Payload", t.EXTENSIONOBJECT, allow_subtypes=True),
    ),
    t.StructureKind.STRUCTURE,
    type_id="i=3030",
    encoding_id="i=3031",
)

COLOR = t.Enumeration(
    "Color",
    (t.EnumMember("Red", 0), t.EnumMember("Green", 1), t.EnumMember("Blue", 2)),
)

PERMISSIONS = t.Enumeration(
    "AccessPermissions",
    (
        t.EnumMember("Browse", 1),
        t.EnumMember("Read", 2),
        t.EnumMember("Write", 4),
        t.EnumMember("Call", 8),
    ),
    is_option_set=True,
    bit_size=32,
)

# A structure with optional NON-String scalar fields: absent must stay distinct
# from present-with-zero (exercises proto3 presence for scalars).
OPTIONAL_SCALARS = t.Struct(
    "OptionalScalars",
    (
        t.Field("Id", t.INT32),
        t.Field("Flag", t.BOOLEAN, is_optional=True),
        t.Field("Count", t.INT32, is_optional=True),
        t.Field("Ratio", t.DOUBLE, is_optional=True),
    ),
    t.StructureKind.STRUCTURE_WITH_OPTIONAL_FIELDS,
    type_id="i=3040",
    encoding_id="i=3041",
)

# Float32 fields inside a structure (values are float32-exact so double-precision
# equality holds), covering the Float-in-composite path.
FLOAT_HOLDER = t.Struct(
    "FloatHolder",
    (t.Field("A", t.FLOAT), t.Field("B", t.FLOAT, is_optional=True)),
    t.StructureKind.STRUCTURE_WITH_OPTIONAL_FIELDS,
    type_id="i=3050",
    encoding_id="i=3051",
)

#: Structured DataTypes referenced by the corpus, for schema generators.
STRUCT_TYPES: tuple[t.Struct, ...] = (POINT, PERSON, MEASUREMENT, ENVELOPE, OPTIONAL_SCALARS, FLOAT_HOLDER)
ENUM_TYPES: tuple[t.Enumeration, ...] = (COLOR, PERMISSIONS)


def _point(x: float, y: float) -> v.StructValue:
    return v.StructValue({"X": x, "Y": y}, "Point")


def _eo_point(x: float, y: float) -> v.ExtensionObject:
    return v.ExtensionObject(v.NodeId(0, v.IdType.NUMERIC, 3001), _point(x, y))


def build_corpus() -> list[Case]:
    c: list[Case] = []
    add = c.append

    # ---- Boolean ----
    add(Case("bool_true", t.BOOLEAN, True))
    add(Case("bool_false", t.BOOLEAN, False))

    # ---- Integers at their domain edges ----
    for bt, (lo, hi) in t.INTEGER_RANGES.items():
        add(Case(f"{bt.name.lower()}_min", t.Builtin(bt), lo))
        add(Case(f"{bt.name.lower()}_max", t.Builtin(bt), hi))
        add(Case(f"{bt.name.lower()}_zero", t.Builtin(bt), 0))

    # ---- Float / Double special values ----
    for name, ty in (("float", t.FLOAT), ("double", t.DOUBLE)):
        add(Case(f"{name}_normal", ty, 1.5))
        add(Case(f"{name}_neg_zero", ty, -0.0))
        add(Case(f"{name}_pos_inf", ty, float("inf")))
        add(Case(f"{name}_neg_inf", ty, float("-inf")))
        add(Case(f"{name}_nan", ty, float("nan")))
    add(Case("double_tiny", t.DOUBLE, 5e-324))
    add(Case("double_big", t.DOUBLE, 1.7976931348623157e308))

    # ---- String / null / empty / unicode ----
    add(Case("string_ascii", t.STRING, "hello"))
    add(Case("string_empty", t.STRING, ""))
    add(Case("string_null", t.STRING, None))
    add(Case("string_unicode", t.STRING, "grüße-\u4e2d\u6587-\U0001f600"))

    # ---- DateTime (100-ns ticks) ----
    add(Case("datetime_zero", t.DATETIME, v.DateTime(0)))
    add(Case("datetime_now", t.DATETIME, v.DateTime(133_000_000_000_000_000)))
    add(Case("datetime_max", t.DATETIME, v.DateTime(INT64_MAX)))

    # ---- Guid ----
    add(Case("guid", t.GUID, _guid(1)))

    # ---- ByteString / XmlElement ----
    add(Case("bytestring", t.BYTESTRING, bytes(range(8))))
    add(Case("bytestring_empty", t.BYTESTRING, b""))
    add(Case("bytestring_null", t.BYTESTRING, None))
    add(Case("xml", t.XMLELEMENT, v.XmlElement("<a x='1'>t</a>")))
    add(Case("xml_null", t.XMLELEMENT, v.XmlElement(None)))

    # ---- NodeId (all four identifier kinds) ----
    add(Case("nodeid_numeric", t.NODEID, v.NodeId(0, v.IdType.NUMERIC, 2258)))
    add(Case("nodeid_string", t.NODEID, v.NodeId(2, v.IdType.STRING, "Demo.Tag1")))
    add(Case("nodeid_guid", t.NODEID, v.NodeId(3, v.IdType.GUID, _guid(7))))
    add(Case("nodeid_opaque", t.NODEID, v.NodeId(4, v.IdType.OPAQUE, b"\x01\x02\x03")))

    # ---- ExpandedNodeId ----
    add(Case("expnodeid_plain", t.EXPANDEDNODEID, v.ExpandedNodeId(v.NodeId(0, v.IdType.NUMERIC, 1))))
    add(
        Case(
            "expnodeid_full",
            t.EXPANDEDNODEID,
            v.ExpandedNodeId(v.NodeId(1, v.IdType.STRING, "X"), "http://example.org/UA/", 5),
        )
    )

    # ---- StatusCode ----
    add(Case("status_good", t.STATUSCODE, v.StatusCode(0)))
    add(Case("status_bad", t.STATUSCODE, v.StatusCode(0x80AC0000)))

    # ---- QualifiedName / LocalizedText (nullability of members) ----
    add(Case("qname", t.QUALIFIEDNAME, v.QualifiedName(1, "Temp")))
    add(Case("qname_null_name", t.QUALIFIEDNAME, v.QualifiedName(0, None)))
    add(Case("ltext_full", t.LOCALIZEDTEXT, v.LocalizedText("en", "Hello")))
    add(Case("ltext_text_only", t.LOCALIZEDTEXT, v.LocalizedText(None, "Hello")))
    add(Case("ltext_null", t.LOCALIZEDTEXT, v.LocalizedText(None, None)))

    # ---- Enumeration & OptionSet ----
    add(Case("enum_blue", COLOR, 2))
    add(Case("optionset", PERMISSIONS, 2 | 4))  # Read|Write

    # ---- 1-D arrays: empty / non-null elements / null elements ----
    add(Case("array_int_empty", t.Array(t.INT32, allow_null_elements=False), []))
    add(Case("array_int", t.Array(t.INT32, allow_null_elements=False), [1, 2, 3]))
    add(Case("array_int_null", t.Array(t.INT32, allow_null_elements=False), None))
    add(Case("array_string_with_nulls", t.Array(t.STRING), ["a", None, ""]))
    add(Case("array_point", t.Array(POINT, allow_null_elements=False), [_point(1.0, 2.0), _point(3.0, 4.0)]))

    # ---- Matrices ----
    add(Case("matrix_int_2x3", t.Matrix(t.INT32), v.Matrix((2, 3), [1, 2, 3, 4, 5, 6])))
    add(
        Case(
            "matrix_double_2x2_special",
            t.Matrix(t.DOUBLE),
            v.Matrix((2, 2), [1.0, float("nan"), float("-inf"), -0.0]),
        )
    )
    add(
        Case(
            "matrix_string_2x2_null_elem",
            t.Matrix(t.STRING),
            v.Matrix((2, 2), ["a", "b", None, "d"]),
        )
    )
    add(Case("matrix_int_2x2x2", t.Matrix(t.INT32), v.Matrix((2, 2, 2), list(range(8)))))

    # ---- Structures ----
    add(Case("struct_point", POINT, _point(1.25, -3.5)))
    add(Case("struct_person_full", PERSON, v.StructValue({"Name": "Ann", "Age": 30, "Email": "a@x", "Nickname": "A"}, "Person")))
    add(Case("struct_person_min", PERSON, v.StructValue({"Name": "Bo", "Age": 41}, "Person")))
    add(Case("struct_person_one_opt", PERSON, v.StructValue({"Name": "Cy", "Age": 5, "Email": "c@x"}, "Person")))
    # present-but-null optional field (mask bit set, value null) must NOT collapse to absent
    add(Case("struct_person_present_null", PERSON, v.StructValue({"Name": "Zed", "Age": 9, "Email": None}, "Person")))
    # optional NON-String scalars: absent must differ from present-with-zero
    add(Case("optscalars_absent", OPTIONAL_SCALARS, v.StructValue({"Id": 7}, "OptionalScalars")))
    add(Case("optscalars_present", OPTIONAL_SCALARS, v.StructValue({"Id": 7, "Flag": True, "Count": -3, "Ratio": 2.5}, "OptionalScalars")))
    add(Case("optscalars_zero_present", OPTIONAL_SCALARS, v.StructValue({"Id": 7, "Flag": False, "Count": 0, "Ratio": 0.0}, "OptionalScalars")))
    # Float32 fields inside a struct (float32-exact values); optional B absent vs present
    add(Case("floatholder_min", FLOAT_HOLDER, v.StructValue({"A": 1.5}, "FloatHolder")))
    add(Case("floatholder_full", FLOAT_HOLDER, v.StructValue({"A": -0.25, "B": 0.5}, "FloatHolder")))

    # ---- Union (each branch + null) ----
    add(Case("union_int", MEASUREMENT, v.UnionValue("AsInt", 7)))
    add(Case("union_text", MEASUREMENT, v.UnionValue("AsText", "hot")))
    add(Case("union_point", MEASUREMENT, v.UnionValue("AsPoint", _point(9.0, 8.0))))
    add(Case("union_null", MEASUREMENT, v.UnionValue(None, None)))
    # a union whose selected branch is a nullable built-in holding null
    add(Case("union_text_null", MEASUREMENT, v.UnionValue("AsText", None)))

    # ---- Struct with subtyped ExtensionObject field + nested + array ----
    add(
        Case(
            "envelope",
            ENVELOPE,
            v.StructValue(
                {
                    "Id": "E1",
                    "Location": _point(0.0, 0.0),
                    "Tags": ["x", None, "z"],
                    "Payload": _eo_point(2.0, 3.0),
                },
                "Envelope",
            ),
        )
    )

    # ---- ExtensionObject (with body / null) ----
    add(Case("extobj_point", t.EXTENSIONOBJECT, _eo_point(1.0, 1.0)))
    add(Case("extobj_null", t.EXTENSIONOBJECT, v.ExtensionObject(v.NodeId(0, v.IdType.NUMERIC, 0), None)))

    # ---- Variant (null / scalar / array / matrix / ExtensionObject body) ----
    add(Case("variant_null", t.VARIANT, v.Variant(None, None)))
    add(Case("variant_int", t.VARIANT, v.Variant(t.INT32, 99)))
    add(Case("variant_double_nan", t.VARIANT, v.Variant(t.DOUBLE, float("nan"))))
    add(Case("variant_string", t.VARIANT, v.Variant(t.STRING, "v")))
    add(Case("variant_array_int", t.VARIANT, v.Variant(t.INT32, [1, 2, 3])))
    add(Case("variant_array_with_nulls", t.VARIANT, v.Variant(t.STRING, ["a", None])))
    add(Case("variant_matrix_int", t.VARIANT, v.Variant(t.INT32, [1, 2, 3, 4], dimensions=(2, 2))))
    add(Case("variant_extobj", t.VARIANT, v.Variant(t.EXTENSIONOBJECT, _eo_point(4.0, 5.0))))
    add(Case("variant_array_extobj", t.VARIANT, v.Variant(t.EXTENSIONOBJECT, [_eo_point(1.0, 1.0), _eo_point(2.0, 2.0)])))

    # ---- DataValue (full / partial / status-only / empty) ----
    add(
        Case(
            "datavalue_full",
            t.DATAVALUE,
            v.DataValue(v.Variant(t.INT32, 42), v.StatusCode(0), v.DateTime(1000), 500, v.DateTime(2000), 250),
        )
    )
    add(Case("datavalue_value_only", t.DATAVALUE, v.DataValue(value=v.Variant(t.DOUBLE, 3.14))))
    add(Case("datavalue_status_only", t.DATAVALUE, v.DataValue(status=v.StatusCode(0x80AC0000))))
    add(Case("datavalue_empty", t.DATAVALUE, v.DataValue()))

    # ---- DiagnosticInfo (recursive) ----
    add(
        Case(
            "diaginfo_nested",
            t.DIAGNOSTICINFO,
            v.DiagnosticInfo(
                symbolic_id=1,
                namespace_uri=2,
                additional_info="outer",
                inner_status_code=v.StatusCode(0x80AC0000),
                inner_diagnostic_info=v.DiagnosticInfo(locale=5, additional_info="inner"),
            ),
        )
    )

    return c


CORPUS: list[Case] = build_corpus()
