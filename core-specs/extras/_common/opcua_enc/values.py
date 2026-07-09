"""Canonical in-memory OPC UA *values* and bit-exact equality.

Every encoding extension maps these Python objects to/from its wire form. The
representation is deliberately explicit so that reversibility can be checked
precisely, including the OPC UA distinctions that lossy mappings tend to drop:

* ``None`` (absent / null) vs an empty collection vs an empty string;
* ``float`` ``NaN``/``+Inf``/``-Inf`` and ``-0.0`` (compared bit-exactly);
* ``DateTime`` as raw 100-ns ticks (no epoch/precision conversion);
* the exact ``NodeId`` identifier kind and namespace index.
"""
from __future__ import annotations

import dataclasses
import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Optional, Union


class IdType(IntEnum):
    NUMERIC = 0
    STRING = 1
    GUID = 2
    OPAQUE = 3  # ByteString identifier


@dataclass(frozen=True)
class Guid:
    """A 16-byte GUID (stored as raw bytes, compared by value)."""

    bytes: bytes

    def __post_init__(self) -> None:
        if len(self.bytes) != 16:
            raise ValueError("Guid requires exactly 16 bytes")


@dataclass(frozen=True)
class DateTime:
    """A UTC DateTime as signed 100-ns ticks since 1601-01-01 (OPC UA epoch)."""

    ticks: int


@dataclass(frozen=True)
class XmlElement:
    """An XML fragment (kept distinct from String)."""

    value: Optional[str]


@dataclass(frozen=True)
class StatusCode:
    value: int = 0  # UInt32


@dataclass(frozen=True)
class NodeId:
    namespace: int = 0
    id_type: IdType = IdType.NUMERIC
    identifier: Union[int, str, Guid, bytes, None] = 0


@dataclass(frozen=True)
class ExpandedNodeId:
    node_id: NodeId = field(default_factory=NodeId)
    namespace_uri: Optional[str] = None
    server_index: int = 0


@dataclass(frozen=True)
class QualifiedName:
    namespace: int = 0
    name: Optional[str] = None


@dataclass(frozen=True)
class LocalizedText:
    locale: Optional[str] = None
    text: Optional[str] = None


@dataclass(frozen=True)
class ExtensionObject:
    """A structured value carried with its concrete type identity.

    ``type_id`` is the DataType or DataTypeEncoding NodeId; ``body`` is a
    :class:`StructValue` (or ``None`` for a null ExtensionObject).
    """

    type_id: NodeId
    body: Optional["StructValue"] = None


@dataclass(frozen=True)
class StructValue:
    """A structure instance: an ordered mapping of field name -> value.

    Absent optional fields are simply not present as keys. ``type_name`` links
    the value back to its :class:`opcua_enc.types.Struct` descriptor for
    diagnostics; it is not part of equality.
    """

    fields: dict[str, Any]
    type_name: Optional[str] = None

    def __eq__(self, other: object) -> bool:  # type_name excluded
        if not isinstance(other, StructValue):
            return NotImplemented
        if set(self.fields) != set(other.fields):
            return False
        return all(canonical_equal(self.fields[k], other.fields[k]) for k in self.fields)

    def __hash__(self) -> int:  # structural values are used as dict values only
        return hash(tuple(sorted(self.fields)))


@dataclass(frozen=True)
class UnionValue:
    """A union instance: the selected field name and its value.

    A null union (SwitchField 0) is represented with ``field_name=None`` and
    ``value=None``.
    """

    field_name: Optional[str]
    value: Any = None


@dataclass(frozen=True)
class Matrix:
    """A multi-dimensional array: row-major flat ``values`` + ``dimensions``."""

    dimensions: tuple[int, ...]
    values: list

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimensions", tuple(self.dimensions))


@dataclass(frozen=True)
class Variant:
    """A Variant: an inner type descriptor plus its value.

    * A *null* Variant has ``vtype=None`` and ``value=None``.
    * A scalar Variant has a :class:`opcua_enc.types.Builtin`/``Struct`` vtype
      and a scalar value.
    * An array Variant has ``value`` as a ``list`` and ``dimensions=None``.
    * A matrix Variant has ``value`` as a row-major ``list`` and ``dimensions``
      set to the shape.
    """

    vtype: Any = None  # opcua_enc.types.Type or None
    value: Any = None
    dimensions: Optional[tuple[int, ...]] = None

    def __post_init__(self) -> None:
        if self.dimensions is not None:
            object.__setattr__(self, "dimensions", tuple(self.dimensions))


@dataclass(frozen=True)
class DataValue:
    """A DataValue. All members are optional; absent members are ``None``."""

    value: Optional[Variant] = None
    status: Optional[StatusCode] = None
    source_timestamp: Optional[DateTime] = None
    source_picoseconds: Optional[int] = None
    server_timestamp: Optional[DateTime] = None
    server_picoseconds: Optional[int] = None


@dataclass(frozen=True)
class DiagnosticInfo:
    """A DiagnosticInfo (recursive via ``inner_diagnostic_info``)."""

    symbolic_id: Optional[int] = None
    namespace_uri: Optional[int] = None
    locale: Optional[int] = None
    localized_text: Optional[int] = None
    additional_info: Optional[str] = None
    inner_status_code: Optional[StatusCode] = None
    inner_diagnostic_info: Optional["DiagnosticInfo"] = None


# --------------------------------------------------------------------------
# Bit-exact equality
# --------------------------------------------------------------------------

def _float_bits(f: float, single: bool) -> bytes:
    return struct.pack("<f" if single else "<d", f)


def canonical_equal(a: Any, b: Any, *, single_float: bool = False) -> bool:
    """Deep equality that is exact about OPC UA-significant distinctions.

    Floats are compared by their IEEE-754 bit pattern so that ``NaN == NaN``
    and ``0.0 != -0.0``. ``None`` never equals a non-``None`` value (null vs
    empty). Lists compare element-wise; dicts key-and-value-wise; value
    dataclasses field-by-field (ignoring the non-normative ``type_name``).
    """
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, float) or isinstance(b, float):
        if not (isinstance(a, float) and isinstance(b, float)):
            return False
        # Compare bit patterns; NaN-exact and signed-zero-exact.
        return _float_bits(a, single_float) == _float_bits(b, single_float)
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return False
        return all(canonical_equal(x, y, single_float=single_float) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False
        return all(canonical_equal(a[k], b[k], single_float=single_float) for k in a)
    if isinstance(a, Variant) and isinstance(b, Variant):
        return (
            a.vtype == b.vtype
            and a.dimensions == b.dimensions
            and canonical_equal(a.value, b.value, single_float=_variant_is_single(a))
        )
    if dataclasses.is_dataclass(a) and dataclasses.is_dataclass(b):
        if type(a) is not type(b):
            return False
        for f in dataclasses.fields(a):
            if f.name == "type_name":
                continue
            if not canonical_equal(getattr(a, f.name), getattr(b, f.name), single_float=single_float):
                return False
        return True
    return a == b


def _variant_is_single(v: Variant) -> bool:
    from .types import Builtin, BuiltInType

    return isinstance(v.vtype, Builtin) and v.vtype.id == BuiltInType.Float


def is_single_float_type(t: Any) -> bool:
    from .types import Builtin, BuiltInType

    return isinstance(t, Builtin) and t.id == BuiltInType.Float
