# OPC UA Part 6 — Protobuf DataEncoding

**Working draft for submission to the OPC Foundation Working Group**
**Proposed addition to:** OPC 10000-6 Mappings v1.05.07
**Namespace:** `http://opcfoundation.org/UA/` (base OPC UA namespace)
**Version:** 0.1.0 · **Date:** 2026-07-02

> **Status — working draft.** This document proposes an additional OPC UA DataEncoding named **Default Protobuf**. It mirrors the reversibility requirements of the existing Binary, XML and JSON encodings while using proto3 messages as the external representation. NodeIds are described only and provisional; final NodeIds are assigned by the OPC Foundation.

---

## 1 Scope

This document defines a proto3 DataEncoding for all OPC UA values described by the OPC UA type model: the 25 built-in types, enumerations, OptionSets, structures with optional fields, unions, one-dimensional arrays, matrices, Variants, DataValues, DiagnosticInfos, ExtensionObjects and fields that allow abstract subtypes. The encoding has exactly one canonical form and shall be reversible: for every value `x` and declared OPC UA type `T`, decoding the Protobuf encoding of `x` as `T` shall produce a value canonically equal to `x`, including null versus empty, absent optional fields, signed zero, NaN, DateTime ticks and exact NodeId identifier kind.

## 2 Normative references

- [OPC 10000-3](https://reference.opcfoundation.org/specs/OPC-10000-3/) — Address Space Model and DataTypeDefinition Attribute.
- [OPC 10000-5](https://reference.opcfoundation.org/specs/OPC-10000-5/) — Information Model and base DataTypes.
- [OPC 10000-6](https://reference.opcfoundation.org/specs/OPC-10000-6/) v1.05.07 — Mappings.
- [Protocol Buffers proto3 language specification](https://protobuf.dev/programming-guides/proto3/) — scalar types, messages, `oneof`, `optional` presence and deterministic serialization.

## 3 Terms, definitions and abbreviations

| Term | Definition |
|---|---|
| Protobuf | Google Protocol Buffers version 3 schema and wire format. |
| Default Protobuf | The OPC UA DataTypeEncoding described by this document. |
| Explicit presence | A proto3 field form (`optional`, message field or `oneof`) that records whether a value was present independently of its default value. |
| Nullable element wrapper | A message wrapper used in `repeated` fields so that a null array element is representable in proto3. |
| Canonical form | The only permitted schema and wire representation for a given OPC UA value and declared type. |

Key words **shall**, **should**, **may**, **shall not** are to be interpreted as in ISO/IEC directives.

## 4 Overview

The Protobuf DataEncoding is schema driven. A generator reads OPC UA DataTypeDefinition metadata from a NodeSet and emits one proto3 message per structured DataType and one enum or OptionSet message per enumeration DataType. Field numbers are stable and are assigned from DataTypeDefinition field order starting at 1. Built-in and envelope messages are defined once in `opcua_builtins.proto` and imported by generated namespace schemas.

The transport content type for complete Protobuf encoded OPC UA values should be `application/vnd.google.protobuf`; `application/x-protobuf` may be accepted for compatibility. Profiles or transports that require a schema identifier shall carry the Protobuf package name, message name and OPC UA DataType/Encoding NodeId out of band or in the containing PubSub metadata.

A described-only DataTypeEncoding Object named `Default Protobuf` would be added as a HasEncoding target for every DataType that supports this encoding, parallel to `Default Binary`, `Default XML` and `Default JSON`.

## 5.6 OPC UA Protobuf

### 5.6.1 General

The Protobuf encoding shall be proto3. Producers shall use the generated canonical schema for the declared OPC UA type and shall not use alternate wrapper shapes, maps, JSON names or application-defined variants for the same value. Consumers shall reject data that selects more than one union/oneof arm, has an unknown required schema for a known DataTypeEncoding, uses an out-of-range integer or contains a matrix whose value count does not equal the product of its dimensions.

### 5.6.2 Built-in DataTypes

| OPC UA Built-in DataType | Protobuf representation | Reversibility rule |
|---|---|---|
| Boolean | `bool` | `false` is a value; presence is supplied by the containing field/oneof where needed. |
| SByte | `int32` | Value shall be in [-128, 127]. |
| Byte | `uint32` | Value shall be in [0, 255]. |
| Int16 | `int32` | Value shall be in [-32768, 32767]. |
| UInt16 | `uint32` | Value shall be in [0, 65535]. |
| Int32 | `int32` | Direct mapping. |
| UInt32 | `uint32` | Direct mapping. |
| Int64 | `int64` | Direct mapping. |
| UInt64 | `uint64` | Direct mapping; the full [0, 2^64-1] domain is preserved. |
| Float | `float` | IEEE 754 single precision bits are preserved by the Protobuf runtime, including NaN, infinities and signed zero. |
| Double | `double` | IEEE 754 double precision bits are preserved, including NaN, infinities and signed zero. |
| String | `StringValue` wrapper when nullable, otherwise `string` with containing presence | Null, empty and non-empty strings are distinct. |
| DateTime | `sfixed64` raw ticks | The value is signed 100 ns ticks since 1601-01-01 UTC; `google.protobuf.Timestamp` shall not be used. |
| Guid | `bytes` | Exactly 16 bytes. |
| ByteString | `ByteStringValue` wrapper when nullable, otherwise `bytes` with containing presence | Null, empty and non-empty byte strings are distinct. |
| XmlElement | message with `optional string value` | Null XML and empty XML string are distinct. |
| NodeId | message with namespace, identifier kind and `oneof` identifier | Numeric, String, Guid and Opaque identifier kinds are preserved. |
| ExpandedNodeId | message containing NodeId, optional namespace URI and server index | Absence of namespace URI is distinct from empty URI. |
| StatusCode | `fixed32` | Raw UInt32 status code bits are preserved. |
| QualifiedName | message with namespace and `optional string name` | Null name and empty name are distinct. |
| LocalizedText | message with `optional string locale` and `optional string text` | Each member has independent presence. |
| ExtensionObject | message with type id and `oneof` body (`Any` for known generated bodies, opaque bytes for forwarding) | The type id identifies the concrete body schema; null body is absence of body. |
| DataValue | message with optional members | Every DataValue member has independent presence. |
| Variant | message with optional built-in type id and scalar/array/matrix `oneof` | Empty Variant message is null; otherwise type identity and dimensions are explicit. |
| DiagnosticInfo | recursive message with optional members | Each index/string/status/inner member has independent presence. |

### 5.6.3 Enumerations and OptionSets

Enumerations shall encode as signed `int32` values or generated proto enum symbols with the same numeric values. Decoders shall preserve unknown numeric values when the OPC UA DataType permits forward-compatible enumeration extension. OptionSets shall encode as an unsigned integer message (`uint32` for 32-bit OptionSets and `uint64` for wider OptionSets) carrying the exact bit mask; symbolic decomposition is non-normative.

### 5.6.4 Structures, optional fields and unions

A Structure DataType shall map to its generated proto3 `message`; that per-type message is the canonical wire form and reflective name/value envelopes are not an alternate encoding. Non-optional fields use stable field numbers derived from DataTypeDefinition field order. OPC UA optional nullable fields shall use an optional nullable wrapper (for example `optional StringValue`) so that absent is distinct from present-null and present-empty. A Union DataType shall map to a proto3 `oneof`; nullable built-in branches use nullable wrappers so a selected null branch is distinct from a null union. A null union is represented by no selected `oneof` arm.

### 5.6.5 Arrays, matrices and nullability

A one-dimensional OPC UA array shall map to `repeated` values. A null array is represented by absence of the containing array message, while an empty array is a present message with zero elements. Proto3 `repeated` fields cannot contain nulls; therefore this encoding uses one canonical nullable-element wrapper strategy. If the element type is nullable, each element shall be encoded as a wrapper message with explicit presence (for the reference schema this is `Value`); an empty wrapper is a null element. If the element type is not nullable, producers should use a plain `repeated` scalar or message field.

A Matrix shall be encoded as `message Matrix<T> { repeated int32 dimensions = 1; repeated <Elem> values = 2; }` where values are row-major and `<Elem>` is the nullable wrapper when the element type is nullable. The number of values shall equal the product of all dimensions. Dimensions are signed Int32 values as in OPC UA.

### 5.6.6 Variant

A Variant shall contain an optional OPC UA BuiltInType numeric id and exactly one payload: scalar, array or matrix. The empty Variant message is the null Variant. Scalar payloads use the built-in mapping in 5.6.2. Array and matrix payloads use the nullability rules in 5.6.5. A Variant shall not directly contain a nested Variant, DataValue or DiagnosticInfo body.

### 5.6.7 ExtensionObject and abstract-subtyped fields

An ExtensionObject shall carry the concrete TypeId or DataTypeEncoding NodeId and a `oneof` body. If the type is known, the body shall be the generated message for the concrete Structure DataType, carried as a typed `Any` in the reference schema. If the type is unknown and the receiver supports opaque forwarding, the body may be opaque bytes; otherwise decoding shall fail. Fields declared as abstract or allowing subtypes shall be encoded in the same way as an ExtensionObject so that the concrete schema is resolved from the inline type id.

### 5.6.8 DataValue and DiagnosticInfo

A DataValue shall be a message whose Value, StatusCode, SourceTimestamp, SourcePicoseconds, ServerTimestamp and ServerPicoseconds members are independently present or absent. A present StatusCode with value `0` is distinct from absent StatusCode. DiagnosticInfo shall be recursive and shall preserve the presence of each index member, AdditionalInfo, InnerStatusCode and InnerDiagnosticInfo.

## 6 Insertion into OPC 10000-6 v1.05.07

Insert a new clause **5.6 OPC UA Protobuf** after **5.4 OPC UA JSON** and the sibling **5.5 OPC UA Avro** addition, and before clause 6. The child clauses shall parallel the JSON mapping: **5.6.1 General**, **5.6.2 Built-in DataTypes**, **5.6.3 Enumerations and OptionSets**, **5.6.4 Structures**, **5.6.5 Arrays and matrices**, **5.6.6 Variant**, **5.6.7 ExtensionObject**, **5.6.8 DataValue**, and **5.6.9 DiagnosticInfo**. Add `Default Protobuf` to DataTypeEncoding discussions wherever `Default Binary`, `Default XML` and `Default JSON` are listed. Add `application/vnd.google.protobuf` and compatibility alias `application/x-protobuf` to content-type guidance for Protobuf encoded bodies.
