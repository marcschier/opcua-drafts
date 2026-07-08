#!/usr/bin/env python3
"""Generate JSON Schema (Draft 2020-12) documents for OPC UA DataTypes.

This is the xRegistry catalog's own contribution (the Avro/Protobuf/Arrow
documents come from the sibling encoding folders). The schemas describe the
*structure* of the OPC UA JSON DataEncoding for each DataType and are intended
for validation, code generation and documentation — JSON does not require a
schema to decode. Built-in types are described once under ``$defs`` and
referenced.
"""
from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))

from opcua_enc import types as t  # noqa: E402

_B = t.BuiltInType

# Structural JSON Schema for each built-in as it appears in the OPC UA JSON
# DataEncoding (approximate; governance/validation reference, not decode-driving).
_BUILTIN_DEFS: dict[str, Any] = {
    "Boolean": {"type": "boolean"},
    "SByte": {"type": "integer", "minimum": -128, "maximum": 127},
    "Byte": {"type": "integer", "minimum": 0, "maximum": 255},
    "Int16": {"type": "integer", "minimum": -32768, "maximum": 32767},
    "UInt16": {"type": "integer", "minimum": 0, "maximum": 65535},
    "Int32": {"type": "integer", "minimum": -2147483648, "maximum": 2147483647},
    "UInt32": {"type": "integer", "minimum": 0, "maximum": 4294967295},
    "Int64": {"type": ["integer", "string"], "description": "Int64; large values as JSON string"},
    "UInt64": {"type": ["integer", "string"], "description": "UInt64; large values as JSON string"},
    "Float": {"type": ["number", "string"], "description": "may be 'Infinity'/'-Infinity'/'NaN'"},
    "Double": {"type": ["number", "string"], "description": "may be 'Infinity'/'-Infinity'/'NaN'"},
    "String": {"type": ["string", "null"]},
    "DateTime": {"type": "string", "format": "date-time"},
    "Guid": {"type": "string", "format": "uuid"},
    "ByteString": {"type": ["string", "null"], "contentEncoding": "base64"},
    "XmlElement": {"type": ["string", "null"]},
    "NodeId": {"type": "string", "description": "NodeId in the OPC UA string form, e.g. 'ns=1;i=42'"},
    "ExpandedNodeId": {"type": "string"},
    "StatusCode": {"type": "integer", "minimum": 0, "maximum": 4294967295},
    "QualifiedName": {
        "type": "object",
        "properties": {"Name": {"type": ["string", "null"]}, "Uri": {"type": "integer"}},
        "required": ["Name"],
    },
    "LocalizedText": {
        "type": "object",
        "properties": {"Locale": {"type": ["string", "null"]}, "Text": {"type": ["string", "null"]}},
    },
    "ExtensionObject": {
        "type": "object",
        "properties": {
            "UaTypeId": {"$ref": "#/$defs/NodeId"},
            "UaEncoding": {"type": "integer"},
            "UaBody": {},
        },
        "required": ["UaTypeId"],
    },
    "Variant": {
        "type": "object",
        "properties": {
            "UaType": {"type": "integer", "minimum": 0, "maximum": 25},
            "Value": {},
            "Dimensions": {"type": "array", "items": {"type": "integer"}},
        },
    },
    "DataValue": {
        "type": "object",
        "properties": {
            "Value": {"$ref": "#/$defs/Variant"},
            "Status": {"$ref": "#/$defs/StatusCode"},
            "SourceTimestamp": {"$ref": "#/$defs/DateTime"},
            "SourcePicoseconds": {"type": "integer"},
            "ServerTimestamp": {"$ref": "#/$defs/DateTime"},
            "ServerPicoseconds": {"type": "integer"},
        },
    },
    "DiagnosticInfo": {"type": "object", "description": "DiagnosticInfo (recursive)"},
}


def _ref(name: str) -> dict:
    return {"$ref": f"#/$defs/{name}"}


def _type_schema(ty: t.Type) -> dict:
    if isinstance(ty, t.Builtin):
        return _ref(ty.id.name)
    if isinstance(ty, t.Enumeration):
        return _ref(ty.name)
    if isinstance(ty, t.Struct):
        return _ref(ty.name)
    if isinstance(ty, t.Array):
        items = _type_schema(ty.element)
        if ty.allow_null_elements:
            items = {"oneOf": [items, {"type": "null"}]}
        return {"type": ["array", "null"], "items": items}
    if isinstance(ty, t.Matrix):
        return {
            "type": "object",
            "description": "OPC UA JSON inline matrix",
            "properties": {
                "Dimensions": {"type": "array", "items": {"type": "integer"}},
                "Array": {"type": "array", "items": _type_schema(ty.element)},
            },
            "required": ["Dimensions", "Array"],
        }
    raise TypeError(ty)


def enum_schema(e: t.Enumeration) -> dict:
    if e.is_option_set:
        return {
            "title": e.name,
            "type": "integer",
            "description": "OptionSet bit mask: " + ", ".join(f"{m.name}={m.value}" for m in e.members),
        }
    return {
        "title": e.name,
        "type": "integer",
        "enum": [m.value for m in e.members],
        "x-opcua-enum": {m.name: m.value for m in e.members},
    }


def struct_schema(s: t.Struct) -> dict:
    if s.kind == t.StructureKind.UNION:
        return {
            "title": s.name,
            "oneOf": [
                {
                    "type": "object",
                    "properties": {"SwitchField": {"const": i + 1}, "Value": _type_schema(f.type)},
                    "required": ["SwitchField", "Value"],
                }
                for i, f in enumerate(s.fields)
            ]
            + [{"type": "object", "properties": {"SwitchField": {"const": 0}}}],
        }
    props: dict[str, Any] = {}
    required: list[str] = []
    for f in s.fields:
        props[f.name] = _type_schema(f.type)
        if not f.is_optional:
            required.append(f.name)
    out: dict[str, Any] = {"title": s.name, "type": "object", "properties": props}
    if required:
        out["required"] = required
    return out


def build_document(structs: list[t.Struct], enums: list[t.Enumeration]) -> dict:
    """A self-contained JSON Schema document with all types under $defs."""
    defs: dict[str, Any] = dict(_BUILTIN_DEFS)
    for e in enums:
        defs[e.name] = enum_schema(e)
    for s in structs:
        defs[s.name] = struct_schema(s)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://opcfoundation.org/UA/schemas/jsonschema",
        "title": "OPC UA DataTypes (JSON DataEncoding)",
        "$defs": defs,
    }


def schema_for(name: str, structs: list[t.Struct], enums: list[t.Enumeration]) -> dict:
    """A single-type JSON Schema (referencing shared $defs) for one DataType."""
    doc = build_document(structs, enums)
    doc["$ref"] = f"#/$defs/{name}"
    doc["title"] = f"OPC UA {name} (JSON DataEncoding)"
    return doc
