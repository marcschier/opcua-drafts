"""Load OPC UA ``DataTypeDefinition``s from a UANodeSet into shared type
descriptors, so the encoding generators can be driven by *any* NodeSet.

The loader resolves each structured/enumerated ``UADataType`` into an
:class:`opcua_enc.types.Struct` / :class:`~opcua_enc.types.Enumeration`,
mapping field ``DataType`` NodeIds to built-in types (via a default alias table
that callers may extend), to other DataTypes defined in the same NodeSet, or —
when a referenced type is defined elsewhere (e.g. the base UA NodeSet) and no
alias is supplied — to an ExtensionObject/Variant fallback (reported in
``unresolved``).

Dependency-free (xml.etree). Not a full AddressSpace resolver; it is scoped to
DataType encoding generation.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional

from . import types as t

_UA_NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"

B = t.BuiltInType

#: DataType NodeId -> BuiltInType. Covers the 25 built-ins plus the common
#: base subtypes companion specs reference. Extend via ``extra_aliases``.
DEFAULT_BUILTIN_ALIASES: dict[str, t.BuiltInType] = {
    "i=1": B.Boolean, "i=2": B.SByte, "i=3": B.Byte, "i=4": B.Int16,
    "i=5": B.UInt16, "i=6": B.Int32, "i=7": B.UInt32, "i=8": B.Int64,
    "i=9": B.UInt64, "i=10": B.Float, "i=11": B.Double, "i=12": B.String,
    "i=13": B.DateTime, "i=14": B.Guid, "i=15": B.ByteString,
    "i=16": B.XmlElement, "i=17": B.NodeId, "i=18": B.ExpandedNodeId,
    "i=19": B.StatusCode, "i=20": B.QualifiedName, "i=21": B.LocalizedText,
    "i=22": B.ExtensionObject, "i=23": B.DataValue, "i=24": B.Variant,
    "i=25": B.DiagnosticInfo,
    # Common base subtypes aliased to their built-in wire type.
    "i=26": B.Byte,        # Number (abstract) -> treated as numeric; rarely a field type
    "i=27": B.Int64,       # Integer (abstract)
    "i=28": B.UInt64,      # UInteger (abstract)
    "i=50": B.Double,      # Decimal (approx; real Decimal is a special ByteString struct)
    "i=290": B.Double,     # Duration
    "i=294": B.DateTime,   # UtcTime
    "i=295": B.String,     # LocaleId
    "i=291": B.String,     # NumericRange
    "i=296": B.ExtensionObject,  # Argument (structure)
}

#: ValueRank semantics (OPC 10000-3): scalar / array / matrix.
SCALAR_RANKS = (-3, -2, -1)  # ScalarOrOneDimension/Any/Scalar -> scalar shape


@dataclass
class LoadResult:
    structs: list[t.Struct] = field(default_factory=list)
    enums: list[t.Enumeration] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)  # "TypeName.FieldName -> NodeId"

    @property
    def by_name(self) -> dict[str, t.Type]:
        out: dict[str, t.Type] = {}
        for s in self.structs:
            out[s.name] = s
        for e in self.enums:
            out[e.name] = e
        return out


class _Loader:
    def __init__(self, root: ET.Element, aliases: dict[str, t.BuiltInType]):
        self.aliases = aliases
        self.defs: dict[str, ET.Element] = {}       # nodeid -> UADataType element
        self.names: dict[str, str] = {}             # nodeid -> browse name (local part)
        self.encoding_ids: dict[str, str] = {}      # datatype nodeid -> "Default Binary" encoding id
        self.cache: dict[str, t.Type] = {}
        self.in_progress: set[str] = set()
        self.result = LoadResult()

        for dt in root.findall(f"{_UA_NS}UADataType"):
            nid = dt.get("NodeId")
            bn = dt.get("BrowseName", "")
            self.defs[nid] = dt
            self.names[nid] = bn.split(":", 1)[-1]
        # Map DataTypeEncoding objects (HasEncoding targets) if present.
        for obj in root.findall(f"{_UA_NS}UAObject"):
            bn = obj.get("BrowseName", "")
            if bn.endswith("Default Binary") or bn.endswith("Default XML") or bn.endswith("Default JSON"):
                # reverse HasEncoding reference points from the DataType
                pass  # encoding ids are not required for generation; left for future use

    def load(self) -> LoadResult:
        for nid, dt in self.defs.items():
            defn = dt.find(f"{_UA_NS}Definition")
            if defn is None:
                continue
            self._resolve_datatype(nid)
        return self.result

    def _resolve_datatype(self, nid: str) -> Optional[t.Type]:
        if nid in self.cache:
            return self.cache[nid]
        dt = self.defs.get(nid)
        if dt is None:
            return None
        defn = dt.find(f"{_UA_NS}Definition")
        if defn is None:
            return None
        name = self.names[nid]
        is_union = defn.get("IsUnion") == "true"
        is_option_set = defn.get("IsOptionSet") == "true"
        fields = defn.findall(f"{_UA_NS}Field")
        is_enum = bool(fields) and all(f.get("DataType") is None for f in fields) and any(
            f.get("Value") is not None for f in fields
        )

        if is_enum or is_option_set:
            members = tuple(
                t.EnumMember(f.get("Name"), int(f.get("Value", "0"))) for f in fields
            )
            enum = t.Enumeration(name, members, is_option_set=is_option_set)
            self.cache[nid] = enum
            self.result.enums.append(enum)
            return enum

        # Structure (guard recursion; self/cyclic references fall back to EO).
        if nid in self.in_progress:
            return t.EXTENSIONOBJECT
        self.in_progress.add(nid)
        struct_fields: list[t.Field] = []
        for f in fields:
            struct_fields.append(self._resolve_field(name, f))
        self.in_progress.discard(nid)

        kind = t.StructureKind.UNION if is_union else (
            t.StructureKind.STRUCTURE_WITH_OPTIONAL_FIELDS
            if any(sf.is_optional for sf in struct_fields)
            else t.StructureKind.STRUCTURE
        )
        struct = t.Struct(name, tuple(struct_fields), kind, type_id=nid)
        self.cache[nid] = struct
        self.result.structs.append(struct)
        return struct

    def _resolve_field(self, owner: str, f: ET.Element) -> t.Field:
        fname = f.get("Name")
        dtype_id = f.get("DataType", "i=24")  # default BaseDataType -> Variant
        is_optional = f.get("IsOptional") == "true"
        rank = int(f.get("ValueRank", "-1"))
        elem, allow_sub = self._resolve_element(owner, fname, dtype_id)
        if rank in SCALAR_RANKS or rank is None:
            ty: t.Type = elem
        elif rank == 1 or rank == 0:
            ty = t.Array(elem, allow_null_elements=_nullable(elem))
        else:  # rank > 1
            ty = t.Matrix(elem, allow_null_elements=_nullable(elem))
        return t.Field(fname, ty, is_optional=is_optional, allow_subtypes=allow_sub)

    def _resolve_element(self, owner: str, fname: str, dtype_id: str) -> tuple[t.Type, bool]:
        if dtype_id in self.aliases:
            return t.Builtin(self.aliases[dtype_id]), False
        if dtype_id in self.defs:
            resolved = self._resolve_datatype(dtype_id)
            if resolved is not None:
                # Abstract structs are carried as ExtensionObject (subtyped).
                return resolved, False
        # Unknown (defined elsewhere, e.g. base UA NodeSet, without alias).
        self.result.unresolved.append(f"{owner}.{fname} -> {dtype_id}")
        return t.EXTENSIONOBJECT, True


def _nullable(elem: t.Type) -> bool:
    if isinstance(elem, t.Builtin):
        return elem.id in (
            B.String, B.ByteString, B.XmlElement, B.NodeId, B.ExpandedNodeId,
            B.QualifiedName, B.LocalizedText, B.ExtensionObject, B.DataValue,
            B.Variant, B.DiagnosticInfo,
        )
    return True


def load_datatypes(path: str, extra_aliases: Optional[dict[str, t.BuiltInType]] = None) -> LoadResult:
    """Parse ``path`` (a UANodeSet2 XML) and return the DataType descriptors."""
    aliases = dict(DEFAULT_BUILTIN_ALIASES)
    if extra_aliases:
        aliases.update(extra_aliases)
    root = ET.parse(path).getroot()
    return _Loader(root, aliases).load()
