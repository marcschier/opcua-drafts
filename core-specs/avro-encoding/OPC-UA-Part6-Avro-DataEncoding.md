# OPC UA Part 6 — Apache Avro DataEncoding

**Working draft for submission to the OPC Foundation Working Group**
**Proposed addition to:** OPC 10000-6 Mappings v1.05.07
**Namespace:** `http://opcfoundation.org/UA/` (base OPC UA namespace)
**Version:** 0.1.0 · **Date:** 2026-07-02

> **Status — working draft.** This document proposes an additional OPC UA DataEncoding named **Default Avro** for lossless Apache Avro binary representation of OPC UA values. NodeIds for the DataTypeEncoding Objects are not assigned here; they would be added to the base namespace by the OPC Foundation. This draft defines one canonical Avro form only and requires `decode(encode(x)) == x` for every value of the described DataType.

---

## 1 Scope

This specification defines how the OPC UA data model is represented as Apache Avro binary data. It covers all 25 Built-in DataTypes, Enumerations, OptionSets, Structures, Structures with optional fields, Union DataTypes, arrays, matrices, Variant, ExtensionObject, DataValue and DiagnosticInfo. The mapping is intended for file, stream and PubSub payloads that already carry or negotiate the Avro schema by configuration, registry or envelope.

This specification does not define a new OPC UA Service, transport protocol or security protocol. It complements the Binary, XML and JSON DataEncodings in OPC 10000-6 and is referenced by the Part 14 Avro PubSub message mapping.

## 2 Normative references

- [OPC 10000-3](https://reference.opcfoundation.org/specs/OPC-10000-3/) — Address Space Model, DataTypes and DataTypeDefinition.
- [OPC 10000-4](https://reference.opcfoundation.org/specs/OPC-10000-4/) — Services.
- [OPC 10000-5](https://reference.opcfoundation.org/specs/OPC-10000-5/) — Information Model.
- [OPC 10000-6 v1.05.07](https://reference.opcfoundation.org/specs/OPC-10000-6/) — Mappings.
- [Apache Avro Specification](https://avro.apache.org/docs/) — Binary encoding, schemas, unions, records, arrays, fixed and logical types.

## 3 Terms, definitions and abbreviations

| Term | Definition |
|---|---|
| Avro binary encoding | The compact binary encoding defined by Apache Avro for a value written with a known Avro schema. |
| Default Avro | The OPC UA DataTypeEncoding Object for this mapping. It is described here; this draft does not ship a NodeSet. |
| Canonical schema | The single Avro schema form generated for an OPC UA DataType by this specification. Equivalent alternative encodings are not allowed on the wire. |
| Matrix | An OPC UA multi-dimensional array represented as row-major values plus dimensions. |
| Reversible | Decoding an encoded value reconstructs the same OPC UA value, including null-vs-empty distinctions, unsigned integer bit patterns, NaN and signed zero. |

Key words **shall**, **should**, **may**, **shall not** are to be interpreted as in ISO/IEC directives.

## 4 Overview

Each OPC UA DataType maps to exactly one Avro schema. Primitive built-ins use Avro primitives where the Avro type can carry the complete OPC UA domain; composite built-ins use Avro records; nullable OPC UA values use Avro unions with `"null"` as the first branch. Avro schema names are stable qualified names under the namespace `org.opcfoundation.ua.avro` unless a companion or vendor namespace is mapped to a more specific Avro namespace by configuration.

The content type for a standalone Avro payload using this DataEncoding shall be `application/vnd.apache.avro`. Where a transport distinguishes container files from schemaless Avro binary payloads it may use the parameter `encoding=binary` or `container=object-container-file`; PubSub messages defined by the companion Part 14 mapping use schemaless Avro binary with schema resolution from configuration or registry.

A DataTypeEncoding Object named **Default Avro** would be added for DataTypes that support this encoding. The Object would be linked from the DataType with `HasEncoding` in the same pattern as `Default Binary`, `Default XML` and `Default JSON`. This working draft intentionally describes that node only and does not assign or ship NodeIds.

## 5 Avro mapping

### 5.1 General rules

Avro records preserve OPC UA field order as defined by the DataTypeDefinition. Record field names shall be the OPC UA field names converted to legal Avro names by replacing non-name characters with `_` and prefixing `_` if required. The published `.avsc` schema documents are the canonical wire contract; encoders and decoders shall use those schemas directly and shall not substitute implementation-specific alternate branches or abbreviated records.

Avro unions used for nullability shall be ordered as `["null", T]`, and the default value for optional fields shall be `null`. A null scalar, a null array, an empty array, a null array element and an absent optional structure field are distinct states and shall not be collapsed.

### 5.2 Built-in DataTypes

| OPC UA Built-in | Avro schema | Reversibility rule |
|---|---|---|
| Boolean | `boolean` | Direct mapping. |
| SByte | `int` | Value range is -128..127. |
| Byte | `int` | Value range is 0..255. |
| Int16 | `int` | Value range is -32768..32767. |
| UInt16 | `int` | Value range is 0..65535. |
| Int32 | `int` | Direct signed 32-bit mapping. |
| UInt32 | `int` | The same 32 bits are carried in Avro's signed `int`; values greater than `2^31-1` are decoded by unsigned reinterpretation. |
| Int64 | `long` | Direct signed 64-bit mapping. |
| UInt64 | `long` | The same 64 bits are carried in Avro's signed `long`; values greater than `2^63-1` are decoded by unsigned reinterpretation. |
| Float | `float` | IEEE-754 single precision, preserving NaN payloads supported by the Avro implementation and signed zero. |
| Double | `double` | IEEE-754 double precision, preserving NaN payloads supported by the Avro implementation and signed zero. |
| String | `["null", "string"]` | `null` and empty string are distinct. |
| DateTime | `long` | Raw signed 100 ns ticks since 1601-01-01 UTC. Avro timestamp logical types shall not be used because they lose epoch and/or precision. |
| Guid | `fixed` size 16 with logical type `opcua-guid` | The 16 OPC UA Guid bytes are preserved exactly. |
| ByteString | `["null", "bytes"]` | `null` and zero-length bytes are distinct. |
| XmlElement | `["null", "string"]` | XML text is not normalized. `null` is distinct from empty XML text. |
| NodeId | `record NodeId` | Fields: namespace Int32, idType enum/int, and exactly one identifier member: numeric UInt32-as-long, string, guid fixed16, or opaque bytes. |
| ExpandedNodeId | `record ExpandedNodeId` | Fields: NodeId, nullable namespaceUri, serverIndex UInt32-as-long. |
| StatusCode | `int` | The UInt32 status bits are carried in signed `int` and reinterpreted unsigned on decode. |
| QualifiedName | `record QualifiedName` | Namespace UInt16-as-int and nullable name string. |
| LocalizedText | `["null", record LocalizedText]` | Locale and text are independently nullable strings. |
| ExtensionObject | `record ExtensionObject` | TypeId NodeId plus nullable body union as described in §5.8. |
| DataValue | `record DataValue` | Optional members as described in §5.10. |
| Variant | `record Variant` | Recursive typed body as described in §5.7. |
| DiagnosticInfo | `record DiagnosticInfo` | Recursive optional members as described in §5.11. |

### 5.3 Enumerations and OptionSets

An OPC UA Enumeration shall be encoded as Avro `int` containing the numeric Int32 value. An OptionSet shall also be encoded as Avro `int` or `long` according to its declared bit size, with each bit preserved. Symbolic Avro enum labels are useful for documentation but shall not replace the numeric value on the wire because OPC UA permits forward-compatible unknown values and bit combinations.

### 5.4 Arrays

A one-dimensional OPC UA array of element type `T` shall be encoded as `["null", {"type":"array","items":T}]` when the array value itself is nullable. If the element can be null, the item schema shall be `["null", T]`; otherwise it shall be `T`. Encoders shall preserve an empty array as an array with zero items, not as `null`.

### 5.5 Matrices

A matrix shall be encoded as a record with fields `dimensions` and `values`: `{ "dimensions": {"type":"array","items":"int"}, "values": {"type":"array","items": <element-or-null>} }`. Values are row-major. The product of dimensions shall equal the length of `values`. A null matrix is the null branch of `["null", MatrixRecord]` and is distinct from a matrix with an empty dimensions vector and empty values vector.

### 5.6 Structures and optional fields

A plain Structure shall be an Avro record with one field per OPC UA field. A StructureWithOptionalFields shall use an outer optional-field wrapper for each optional field: `["null", {"type":"record","name":"<Structure>_<Field>_Optional","fields":[{"name":"value","type":T}]}]` with default `null`. The outer null means the OPC UA optional field is absent. A present wrapper whose `value` is null means the field is present with a null value, when `T` itself is nullable. Mandatory fields whose type is nullable, such as String, still carry their own null union and shall be present in the record.

### 5.7 Union DataTypes

An OPC UA Union DataType shall be encoded canonically as an Avro record with `switch` and `value`. The `switch` field is `["null", "string"]` and contains the selected OPC UA field name, or null for the null union. The `value` field is an Avro union of null plus record-wrapped branches, one branch per union field. Each branch record contains exactly one field with the OPC UA field name and field type, including that type's null branch when the selected field type is nullable. The record wrapper is required so Avro union branch resolution is deterministic even when two union fields have the same Avro primitive type.

### 5.8 Variant

Variant shall be a record carrying `builtInType`, nullable `dimensions`, and `body`. A null Variant has `builtInType = 0`, `dimensions = null`, and `body = null`. A scalar body uses one record-wrapped Avro union branch for the selected built-in body type. A one-dimensional array body uses the corresponding `Array` wrapper. A matrix body uses the corresponding Matrix wrapper and sets `dimensions`. Variant body branches cover every OPC UA built-in type allowed in a Variant body, including ExtensionObject, and exclude nested Variant, DataValue and DiagnosticInfo. The branch wrappers and the `builtInType` field are both present so decoders can disambiguate Avro unions and recover the exact OPC UA type.

### 5.9 ExtensionObject and abstract or subtyped fields

ExtensionObject shall be a record `{ "typeId": NodeId, "body": ["null", <known-struct-records...>, "bytes"] }`. The `typeId` shall identify the concrete DataType or DataTypeEncoding NodeId. If the concrete structured DataType is known to the decoder, the body shall use that record branch. If the type is unknown but the sender has an opaque encoded representation, the body may use the `bytes` branch and the receiver shall preserve the bytes with the TypeId. Fields declared as abstract structures or fields that allow subtypes shall use the same representation so the concrete runtime type is carried inline.

### 5.10 DataValue

DataValue shall be an Avro record with fields `value`, `status`, `sourceTimestamp`, `sourcePicoseconds`, `serverTimestamp`, and `serverPicoseconds`, each nullable and defaulting to null. The `value` field is a nullable Variant. StatusCode uses the UInt32-as-signed-int rule. Timestamps use raw DateTime ticks. Picoseconds use Avro `int` and retain the OPC UA UInt16 domain.

### 5.11 DiagnosticInfo

DiagnosticInfo shall be an Avro record with nullable fields `symbolicId`, `namespaceUri`, `locale`, `localizedText`, `additionalInfo`, `innerStatusCode`, and `innerDiagnosticInfo`. `innerDiagnosticInfo` is a recursive reference to DiagnosticInfo. Null means the corresponding mask bit is not present; zero is a present numeric value and shall not be treated as absent.

## 6 Insertion into OPC 10000-6 v1.05.07

This text is intended to be inserted after clause `5.4 OPC UA JSON` and before clause `6 Message SecurityProtocols` as a new working clause `5.5 OPC UA Avro`.

| Draft section | Target clause in OPC 10000-6 | Notes |
|---|---|---|
| §4 Overview and content type | `5.5.1 General` | Introduces Default Avro, canonical schemas, content type `application/vnd.apache.avro`, schema resolution and reversibility. |
| §5.2 Built-in DataTypes | `5.5.2 Built-in Types` | Adds the full built-in mapping table and unsigned reinterpretation rules. |
| §5.4 Arrays and §5.5 Matrices | `5.5.3 Arrays` | Defines null array, empty array, nullable elements and matrix record layout. |
| §5.6 Structures and optional fields | `5.5.4 Structures` and `5.5.5 Structures with optional fields` | Parallels the JSON clauses while using Avro records and null unions. |
| §5.7 Union DataTypes | `5.5.6 Unions` | Defines the canonical switch plus record-wrapped value branch. |
| §5.3 Enumerations and OptionSets | `5.5.2` or new `5.5.7 Enumerations and OptionSets` | Numeric preservation rule may be a subclause after built-ins if preferred by the editor. |
| §5.8-§5.11 Variant, ExtensionObject, DataValue, DiagnosticInfo | `5.5.2` child subclauses | These are built-in DataTypes but need dedicated detail comparable to JSON Variant/DataValue text. |

Conformance text should require that senders and receivers claiming Default Avro support use the canonical schema generated from the DataTypeDefinition and reject non-canonical alternate encodings where a reversible decode cannot be guaranteed.
