"""Canonical OPC UA *type descriptors* shared by every encoding extension.

A type descriptor names an OPC UA data type precisely enough that a
type-directed codec (Avro / Arrow / the JSON control) can encode and
*losslessly* decode a value of that type. Reversibility is defined against these
descriptors: for a descriptor ``T`` and a value ``v``,
``decode(T, encode(T, v))`` must equal ``v`` (see :mod:`opcua_enc.values`
``canonical_equal``).

The 25 built-in types are OPC 10000-6 Table 1. Higher-order descriptors express
1-D arrays, multi-dimensional matrices, enumerations, and the three structure
flavours (plain / with-optional-fields / union) defined by the
``DataTypeDefinition`` Attribute in OPC 10000-3.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class BuiltInType(IntEnum):
    """OPC 10000-6 Table 1 - Built-in Data Types."""

    Boolean = 1
    SByte = 2
    Byte = 3
    Int16 = 4
    UInt16 = 5
    Int32 = 6
    UInt32 = 7
    Int64 = 8
    UInt64 = 9
    Float = 10
    Double = 11
    String = 12
    DateTime = 13
    Guid = 14
    ByteString = 15
    XmlElement = 16
    NodeId = 17
    ExpandedNodeId = 18
    StatusCode = 19
    QualifiedName = 20
    LocalizedText = 21
    ExtensionObject = 22
    DataValue = 23
    Variant = 24
    DiagnosticInfo = 25


#: Integer built-in types and their inclusive [min, max] domains (for corpus
#: edge-case generation and encoder range checks).
INTEGER_RANGES = {
    BuiltInType.SByte: (-(2**7), 2**7 - 1),
    BuiltInType.Byte: (0, 2**8 - 1),
    BuiltInType.Int16: (-(2**15), 2**15 - 1),
    BuiltInType.UInt16: (0, 2**16 - 1),
    BuiltInType.Int32: (-(2**31), 2**31 - 1),
    BuiltInType.UInt32: (0, 2**32 - 1),
    BuiltInType.Int64: (-(2**63), 2**63 - 1),
    BuiltInType.UInt64: (0, 2**64 - 1),
}


class Type:
    """Base class for all type descriptors."""

    __slots__ = ()


@dataclass(frozen=True)
class Builtin(Type):
    """One of the 25 built-in types."""

    id: BuiltInType

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", BuiltInType(self.id))


@dataclass(frozen=True)
class Array(Type):
    """A one-dimensional array.

    ``allow_null_elements`` records whether individual elements may be null
    (the OPC UA convention for arrays of nullable built-ins such as String,
    ByteString, and the composite types). Scalars that are not nullable in OPC
    UA (e.g. Boolean, the integer and floating types) set this to ``False``.
    """

    element: Type
    allow_null_elements: bool = True


@dataclass(frozen=True)
class Matrix(Type):
    """A multi-dimensional array (flat row-major values + Int32 Dimensions)."""

    element: Type
    allow_null_elements: bool = True


@dataclass(frozen=True)
class EnumMember:
    name: str
    value: int


@dataclass(frozen=True)
class Enumeration(Type):
    """An enumeration (Int32 wire representation) or option set.

    ``is_option_set`` marks a bit-mask OptionSet whose members are combined by
    bitwise OR; ``bit_size`` is the width of the backing integer for option
    sets (32 by default).
    """

    name: str
    members: tuple[EnumMember, ...]
    is_option_set: bool = False
    bit_size: int = 32


class StructureKind(IntEnum):
    STRUCTURE = 0  # plain structure
    STRUCTURE_WITH_OPTIONAL_FIELDS = 1
    UNION = 2


@dataclass(frozen=True)
class Field:
    """A structure field.

    ``is_optional`` marks a field controlled by the optional-field encoding
    mask. ``allow_subtypes`` marks a field whose declared type is abstract or
    ``StructureWithSubtypedValues`` such that the concrete type is carried
    inline at runtime (encoded as an ExtensionObject/typed union).
    """

    name: str
    type: Type
    is_optional: bool = False
    allow_subtypes: bool = False


@dataclass(frozen=True)
class Struct(Type):
    """A concrete structured DataType defined by a DataTypeDefinition.

    ``type_id`` / ``encoding_id`` are the (provisional) NodeIds used when the
    value appears inside an ExtensionObject or an abstract/subtyped field; they
    are optional for standalone corpus structures.
    """

    name: str
    fields: tuple[Field, ...]
    kind: StructureKind = StructureKind.STRUCTURE
    type_id: Optional[str] = None
    encoding_id: Optional[str] = None


# Convenient singletons for the built-in scalar types.
BOOLEAN = Builtin(BuiltInType.Boolean)
SBYTE = Builtin(BuiltInType.SByte)
BYTE = Builtin(BuiltInType.Byte)
INT16 = Builtin(BuiltInType.Int16)
UINT16 = Builtin(BuiltInType.UInt16)
INT32 = Builtin(BuiltInType.Int32)
UINT32 = Builtin(BuiltInType.UInt32)
INT64 = Builtin(BuiltInType.Int64)
UINT64 = Builtin(BuiltInType.UInt64)
FLOAT = Builtin(BuiltInType.Float)
DOUBLE = Builtin(BuiltInType.Double)
STRING = Builtin(BuiltInType.String)
DATETIME = Builtin(BuiltInType.DateTime)
GUID = Builtin(BuiltInType.Guid)
BYTESTRING = Builtin(BuiltInType.ByteString)
XMLELEMENT = Builtin(BuiltInType.XmlElement)
NODEID = Builtin(BuiltInType.NodeId)
EXPANDEDNODEID = Builtin(BuiltInType.ExpandedNodeId)
STATUSCODE = Builtin(BuiltInType.StatusCode)
QUALIFIEDNAME = Builtin(BuiltInType.QualifiedName)
LOCALIZEDTEXT = Builtin(BuiltInType.LocalizedText)
EXTENSIONOBJECT = Builtin(BuiltInType.ExtensionObject)
DATAVALUE = Builtin(BuiltInType.DataValue)
VARIANT = Builtin(BuiltInType.Variant)
DIAGNOSTICINFO = Builtin(BuiltInType.DiagnosticInfo)

#: The built-in types that may legally appear as the body of a Variant.
#: (A Variant never nests a Variant directly, and never carries a DataValue or
#: DiagnosticInfo body per OPC 10000-6.)
VARIANT_BODY_TYPES = tuple(
    Builtin(t)
    for t in BuiltInType
    if t not in (BuiltInType.Variant, BuiltInType.DataValue, BuiltInType.DiagnosticInfo)
)
