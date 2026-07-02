# OPC UA Part 6 Apache Arrow DataEncoding

**Working draft for submission to the OPC Foundation Working Group**  
**Proposed insertion:** OPC 10000-6 v1.05.07, new clause `5.7 OPC UA Arrow`  
**Version:** 0.1.0 · **Date:** 2026-07-02

> **Status — working draft.** This document specifies a single canonical Apache Arrow representation for OPC UA values. It is an additive DataEncoding beside Binary, XML and JSON and shares the same OPC UA type model, DataTypeDefinition metadata and ExtensionObject type identity rules.

## 1 Scope

This specification defines how every OPC UA value is represented as an Apache Arrow `DataType` and serialized as Arrow IPC. The mapping is reversible: for each OPC UA type descriptor `T` and value `x`, `decode(T, encode(T, x))` shall reconstruct an OPC UA value canonically equal to `x`.

Arrow is columnar. A single Part 6 scalar value is encoded as a length-1 Arrow Array or StructArray. A PubSub DataSet field uses the same Arrow `DataType` as its column type in Part 14; there is no separate PubSub type mapping.

## 2 Normative references

- OPC 10000-3, Address Space Model, including `DataTypeDefinition`.
- OPC 10000-5, Information Model, including built-in DataTypes.
- OPC 10000-6 v1.05.07, Mappings.
- OPC 10000-14 v1.05.06, PubSub.
- Apache Arrow Columnar Format and Arrow IPC stream/file format.

## 3 Terms, definitions and abbreviations

| Term | Definition |
|---|---|
| Arrow value array | The length-1 Arrow Array carrying one OPC UA value. |
| DataSet column | An Arrow RecordBatch column whose `DataType` is the Part 6 mapping for the DataSet field DataType. |
| Null slot | An Arrow validity-bitmap null. Null slots are the canonical null mechanism. |
| Matrix | An OPC UA multi-dimensional array represented as dimensions plus row-major values. |
| Default Arrow | The described DataTypeEncoding Object for the Arrow encoding of an OPC UA DataType. |

## 4 Overview

The canonical Arrow encoding is type-directed. Encoders determine the Arrow `DataType` from the OPC UA DataType, construct a length-1 Array for a standalone value, and serialize it using Arrow IPC stream or file format. Decoders use the expected OPC UA DataType and the Arrow schema to reconstruct NodeIds, Variants, DataValues, Structures, Unions and nullable members exactly.

There is one canonical form. Encoders shall not choose alternative Arrow layouts for the same OPC UA DataType. Informative Arrow extension types, such as tensor extension types for matrices, may be exposed by tools but are not the canonical interchange representation.

## 5 Insertion into OPC 10000-6 v1.05.07

Insert the following new clause after `5.4 OPC UA JSON` and after the sibling additive clauses `5.5 OPC UA Avro` and `5.6 OPC UA Protobuf`, before clause `6`.

### 5.7 OPC UA Arrow

OPC UA Arrow maps each OPC UA DataType to one Apache Arrow `DataType`. A value encoded by this mapping is a length-1 Arrow Array with that `DataType`. When used by OPC UA PubSub, the same `DataType` is used as the column type for the corresponding DataSet field.

#### 5.7.1 General rules

Null OPC UA values shall be encoded as Arrow null slots using the native validity bitmap. Empty strings, empty ByteStrings and empty lists shall be encoded as present non-null slots with zero length content. Optional Structure fields shall use `struct<present:bool, value:T>` so an absent optional field (`present=false`) is distinct from a present field whose value is null (`present=true, value=null`).

Arrow IPC stream content shall use media type `application/vnd.apache.arrow.stream`. Arrow IPC file content shall use media type `application/vnd.apache.arrow.file`.

OPC UA DataTypes that support DataTypeEncoding Objects may describe a `Default Arrow` DataTypeEncoding Node. This draft describes that Node but does not allocate final NodeIds.

#### 5.7.2 Built-in DataTypes

| OPC UA Built-in DataType | Arrow `DataType` | Canonical notes |
|---|---|---|
| Boolean | `bool` | Valid values `true` and `false`. |
| SByte | `int8` | Exact-width signed integer. |
| Byte | `uint8` | Exact-width unsigned integer. |
| Int16 | `int16` | Exact-width signed integer. |
| UInt16 | `uint16` | Exact-width unsigned integer. |
| Int32 | `int32` | Exact-width signed integer. |
| UInt32 | `uint32` | Exact-width unsigned integer. |
| Int64 | `int64` | Exact-width signed integer. |
| UInt64 | `uint64` | Full unsigned 64-bit range is preserved. |
| Float | `float32` | IEEE-754 single precision; signed zero is significant; NaN payload canonicalization by Arrow implementations is not significant. |
| Double | `float64` | IEEE-754 double precision; signed zero is significant; NaN payload canonicalization by Arrow implementations is not significant. |
| String | `utf8` | Null String is an Arrow null slot; empty String is a present zero-length string. |
| DateTime | `int64` | Raw OPC UA 100 ns ticks since 1601-01-01 UTC. `timestamp(ns)` is informative only and is not canonical due to epoch, precision and range differences. |
| Guid | `fixed_size_binary(16)` | Raw 16 octets. |
| ByteString | `binary` | Null ByteString is an Arrow null slot; empty ByteString is present zero-length binary. |
| XmlElement | `utf8` | XML fragment text; null XML value is an Arrow null slot. |
| NodeId | `struct<namespace:uint16, id_type:uint8, numeric:uint32, string:utf8, guid:fixed_size_binary(16), opaque:binary>` | `id_type` selects the active identifier child: Numeric, String, Guid or Opaque. Inactive identifier children are null. |
| ExpandedNodeId | `struct<node_id:NodeId, namespace_uri:utf8, server_index:uint32>` | `namespace_uri` is nullable. |
| StatusCode | `uint32` | Full StatusCode bit pattern. |
| QualifiedName | `struct<namespace:uint16, name:utf8>` | `name` is nullable. |
| LocalizedText | `struct<locale:utf8, text:utf8>` | Members are nullable independently. |
| ExtensionObject | `struct<type_id:NodeId, body:dense_union<null, known structs, binary>>` | `type_id` carries the concrete DataType or Encoding NodeId. `body` selects the `null` branch for a null ExtensionObject. Unknown bodies may be carried as binary. |
| DataValue | `struct<value:Variant, status:uint32, source_timestamp:int64, source_picoseconds:uint16, server_timestamp:int64, server_picoseconds:uint16>` | All child fields are nullable; DateTime children use raw ticks. |
| Variant | `dense_union<null, scalar built-ins, list built-ins, matrix, ExtensionObject>` | Carries exact runtime type identity and dimensions. A null Variant is a null slot. |
| DiagnosticInfo | `struct<symbolic_id:int32, namespace_uri:int32, locale:int32, localized_text:int32, additional_info:utf8, inner_status_code:uint32, inner_diagnostic_info:list<DiagnosticInfoFrame>>` | All scalar child fields are nullable. `inner_diagnostic_info` is an ordered list of non-recursive DiagnosticInfo frames, outermost inner first, which preserves the recursive OPC UA chain without embedding JSON or opaque binary. |

#### 5.7.3 Enumerations and OptionSets

Enumerations shall be represented as `int32`; symbolic labels in generated schema metadata are informative and the integer value is normative for decoding. OptionSets shall be represented by the exact-width unsigned integer required by the OptionSet bit size (`uint32` for 32-bit OptionSets unless the DataTypeDefinition states otherwise).

#### 5.7.4 Structures, optional fields and Unions

An OPC UA Structure shall be represented as an Arrow `struct` with one child field per DataTypeDefinition field in definition order. A StructureWithOptionalFields uses the `struct<present:bool, value:T>` optional wrapper for optional members; mandatory fields are nullable only when the field DataType itself is nullable.

An OPC UA Union shall be represented as an Arrow dense `union` with a `null` branch followed by one branch per OPC UA union field. Each non-null branch is `struct<value:T>` so selecting a nullable branch with `value=null` is distinct from selecting the union `null` branch. Type codes shall be stable for the DataTypeDefinition field order.

#### 5.7.5 Arrays and Matrices

A one-dimensional OPC UA array shall be represented as `list<Elem>`, where `Elem` is the Arrow mapping of the element DataType. A null array is a null list slot. An empty array is a present list slot with length zero. Null elements are represented by the element validity bitmap when the element type permits nulls.

A multi-dimensional OPC UA Matrix shall be represented as `struct<dimensions:list<int32>, values:list<Elem>>`. `dimensions` contains the OPC UA dimension lengths. `values` contains the elements in row-major order. The product of `dimensions` shall equal the length of `values`. Arrow `fixed_shape_tensor` and `variable_shape_tensor` extension types may be referenced informatively, but this struct is the only canonical Matrix carrier.

#### 5.7.6 Variant

Variant shall be represented as a recursive dense union whose child arrays cover all legal Variant body forms: scalar built-ins except Variant, DataValue and DiagnosticInfo; one-dimensional list forms of those built-ins; the canonical Matrix struct; and ExtensionObject. The union type code, list-vs-scalar form and Matrix dimensions are sufficient to reconstruct the exact OPC UA Variant type and dimensionality.

#### 5.7.7 ExtensionObject and abstract/subtyped fields

ExtensionObject and fields declared with abstract or subtyped values shall carry concrete type identity inline. The canonical carrier is `struct<type_id:NodeId, body:dense_union<null, known structs, binary>>`. The `type_id` is the DataType NodeId or DataTypeEncoding NodeId needed to resolve the body schema. The known-struct union branches are generated from the active schema registry; if the receiver does not know the body type, the body may be retained as opaque binary without claiming decoded structured content.

#### 5.7.8 Default Arrow DataTypeEncoding Node

For every structured DataType with a Default Binary, Default XML or Default JSON DataTypeEncoding, a companion `Default Arrow` DataTypeEncoding Object may be described. Its browse name is `Default Arrow`, its encoding format is Arrow IPC using this clause, and its schema is the canonical Arrow `DataType` generated from the DataTypeDefinition.

#### 5.7.9 Conformance

An implementation conforms to OPC UA Arrow when it implements the single mapping in this clause for all 25 built-in DataTypes, Structures, Unions, Enumerations, OptionSets, Arrays, Matrices, Variant, ExtensionObject, DataValue and DiagnosticInfo, and demonstrates `decode(encode(x)) == x` for conforming OPC UA values.
