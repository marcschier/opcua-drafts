# OPC UA Part 6 Apache Arrow DataEncoding

**Working draft for submission to the OPC Foundation Working Group**  
**Proposed insertion:** OPC 10000-6 v1.05.07, new clause `5.7 OPC UA Arrow`  
**Version:** 0.1.0 · **Date:** 2026-07-02

> **Status — working draft.** This document specifies a single canonical Apache Arrow representation for OPC UA values. It is an additive DataEncoding beside Binary, XML and JSON and shares the same OPC UA type model, DataTypeDefinition metadata and ExtensionObject type identity rules.

## 1 Scope

This specification defines how every OPC UA value is represented as an Apache Arrow `DataType` and serialized as Arrow IPC. The mapping is reversible: for each OPC UA type descriptor `T` and value `x`, `decode(T, encode(T, x))` shall reconstruct an OPC UA value canonically equal to `x`.

Arrow is columnar. A single Part 6 scalar value is encoded as a length-1 Arrow Array or StructArray. A PubSub DataSet field uses the same Arrow `DataType` as its column type in Part 14; there is no separate PubSub type mapping.

**Normative exclusion:** OPC UA Arrow does not map OPC UA Actions, action invoke requests, or action invoke responses. Actions shall use the OPC UA Avro mapping. Arrow remains defined for columnar historian access and Part 14 batch publish/subscribe payloads.

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

For generated per-type schemas and examples, see [Annex A](#annex-a-generated-per-type-reference).

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

#### 5.7.9 Schema-generation algorithm

Given an OPC UA DataType, an encoder or decoder shall derive the canonical Arrow `DataType` by applying the mapping in this clause recursively to the DataTypeDefinition. Built-in DataTypes map as specified in 5.7.2. Enumerations map to `int32`; OptionSets map to the unsigned integer width required by their DataTypeDefinition. A one-dimensional array maps to `list<Elem>`. A Matrix maps to `struct<dimensions:list<int32>, values:list<Elem>>`. A Structure maps to an Arrow `struct` whose child fields appear in DataTypeDefinition order. A StructureWithOptionalFields shall wrap each optional field as `struct<present:bool not null, value:T>` and shall not use a null child slot to mean absent. A Union shall map to a dense union with a `null` branch followed by one branch per union field in definition order; each non-null branch is `struct<value:T>`. Fields declared abstract or allowing subtyped values, and `ExtensionObject`, shall carry the concrete runtime type identity with the value using the canonical `type_id` plus dense-union body carrier. `Variant` and abstract values use the runtime type to select the scalar, array, matrix or ExtensionObject branch. Numeric NodeIds shall use a `uint32` numeric identifier field.

The canonical Arrow `Schema` for a standalone Part 6 value is a single field named `value` with metadata `opcua-arrow=1`. For PubSub, the same generation function is applied to each DataSet field to form the RecordBatch schema. The canonical form of a schema is the serialized Arrow Schema IPC message bytes, for example `schema.serialize().to_pybytes()`. The `SchemaId` is the lowercase hexadecimal SHA-256 fingerprint truncated to the first 8 bytes (16 hex chars) of the canonical schema bytes, unless a profile specifies a longer length.

#### 5.7.10 Decoder algorithm

A schema-driven decoder shall treat an Arrow IPC stream as self-contained because the stream embeds its Schema message before any RecordBatch. The decoder reads that Schema message, validates that each field uses the canonical mapping, then decodes each Arrow Array using this Part 6 mapping. If a decoder must validate a message before receiving the stream, or must enforce a governed schema, it shall look up the `SchemaId` in a local cache or registry and compare the received serialized Arrow Schema with the cached canonical form.

An AddressSpace-driven decoder may instead read the DataTypeDefinition for the expected DataType from the AddressSpace and re-run the schema-generation algorithm in 5.7.9. Encoders and decoders shall use the same generation function, so the AddressSpace-derived Arrow Schema serializes to the same canonical form and therefore the same `SchemaId`. A mismatch between the received SchemaId and the re-derived SchemaId is a schema error.

#### 5.7.11 Conformance

An implementation conforms to OPC UA Arrow when it implements the single mapping in this clause for all 25 built-in DataTypes, Structures, Unions, Enumerations, OptionSets, Arrays, Matrices, Variant, ExtensionObject, DataValue and DiagnosticInfo, and demonstrates `decode(encode(x)) == x` for conforming OPC UA values.

## Annex A Generated per-type reference

<!-- BEGIN GENERATED: type-reference -->
This annex is generated by `../extras/arrow-encoding/tools/gen_type_reference.py`. Do not edit between the markers.

### Built-in Boolean

Published schema source: `schemas\base.json builtins`. SchemaId: `eb9e462ff1431ec8`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `bool` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: bool
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
True
```

### Built-in SByte

Published schema source: `schemas\base.json builtins`. SchemaId: `574fba8aebe6986c`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `int8` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: int8
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
-128
```

### Built-in Byte

Published schema source: `schemas\base.json builtins`. SchemaId: `f3f67e3b5b8a4c33`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `uint8` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: uint8
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
255
```

### Built-in Int16

Published schema source: `schemas\base.json builtins`. SchemaId: `9b9ed1fb78bb0504`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `int16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: int16
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
-32768
```

### Built-in UInt16

Published schema source: `schemas\base.json builtins`. SchemaId: `5e48d7a9fb0e260a`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `uint16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: uint16
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
65535
```

### Built-in Int32

Published schema source: `schemas\base.json builtins`. SchemaId: `a94e58013dcc0ace`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: int32
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
2147483647
```

### Built-in UInt32

Published schema source: `schemas\base.json builtins`. SchemaId: `3a7d0fa718aba078`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: uint32
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
4294967295
```

### Built-in Int64

Published schema source: `schemas\base.json builtins`. SchemaId: `0ca4cf7abab461b5`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `int64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: int64
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
9223372036854775807
```

### Built-in UInt64

Published schema source: `schemas\base.json builtins`. SchemaId: `adde7d8c9e746c67`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `uint64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: uint64
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
18446744073709551615
```

### Built-in Float

Published schema source: `schemas\base.json builtins`. SchemaId: `4760b7d7322090d7`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `float` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: float
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
1.5
```

### Built-in Double

Published schema source: `schemas\base.json builtins`. SchemaId: `2ea3b1f1a51b7231`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `double` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: double
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
-0.0
```

### Built-in String

Published schema source: `schemas\base.json builtins`. SchemaId: `dd43171d093a54aa`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: string
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
'grüße-中文-😀'
```

### Built-in DateTime

Published schema source: `schemas\base.json builtins`. SchemaId: `0ca4cf7abab461b5`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `int64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: int64
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
DateTime(ticks=133000000000000000)
```

### Built-in Guid

Published schema source: `schemas\base.json builtins`. SchemaId: `81e222e0fec2ba07`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |

Arrow schema:

```text
value: fixed_size_binary[16]
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
Guid(bytes=b'\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10')
```

### Built-in ByteString

Published schema source: `schemas\base.json builtins`. SchemaId: `0b3084b7b66d58c5`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: binary
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
b'\x00\x01\x02\x03\x04\x05\x06\x07'
```

### Built-in XmlElement

Published schema source: `schemas\base.json builtins`. SchemaId: `dd43171d093a54aa`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: string
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
XmlElement(value="<a x='1'>t</a>")
```

### Built-in NodeId

Published schema source: `schemas\base.json builtins`. SchemaId: `48ad8cbe55122414`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted)
  child 0, namespace: uint16 not null
  child 1, id_type: uint8 not null
  child 2, numeric: uint32
  child 3, string: string
  child 4, guid: fixed_size_binary[16]
  child 5, opaque: binary
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
NodeId(namespace=3,
       id_type=<IdType.GUID: 2>,
       identifier=Guid(bytes=b'\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12'
                             b'\x13\x14\x15\x16'))
```

### Built-in ExpandedNodeId

Published schema source: `schemas\base.json builtins`. SchemaId: `b3501c1264fb49ae`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.node_id` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.node_id.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.node_id.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.node_id.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.node_id.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.node_id.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.node_id.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.namespace_uri` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.server_index` | `uint32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 117 chars omitted)
  child 0, node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
      child 0, namespace: uint16 not null
      child 1, id_type: uint8 not null
      child 2, numeric: uint32
      child 3, string: string
      child 4, guid: fixed_size_binary[16]
      child 5, opaque: binary
  child 1, namespace_uri: string
  child 2, server_index: uint32 not null
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
ExpandedNodeId(node_id=NodeId(namespace=1,
                              id_type=<IdType.STRING: 1>,
                              identifier='X'),
               namespace_uri='http://example.org/UA/',
               server_index=5)
```

### Built-in StatusCode

Published schema source: `schemas\base.json builtins`. SchemaId: `3a7d0fa718aba078`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: uint32
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
StatusCode(value=2158755840)
```

### Built-in QualifiedName

Published schema source: `schemas\base.json builtins`. SchemaId: `4aefacb2875f7e9c`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `struct<namespace: uint16 not null, name: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.name` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: struct<namespace: uint16 not null, name: string>
  child 0, namespace: uint16 not null
  child 1, name: string
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
QualifiedName(namespace=1, name='Temp')
```

### Built-in LocalizedText

Published schema source: `schemas\base.json builtins`. SchemaId: `def6b87ad887cc5b`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `struct<locale: string, text: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.locale` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.text` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: struct<locale: string, text: string>
  child 0, locale: string
  child 1, text: string
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
LocalizedText(locale='en', text='Hello')
```

### Built-in ExtensionObject

Published schema source: `schemas\base.json builtins`. SchemaId: `64f76d44068bde04`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.type_id` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.type_id.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.type_id.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.type_id.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.type_id.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.type_id.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.type_id.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body` | `dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7>` | not nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.body.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Point` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Point.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Point.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Person` | `struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Person.Name` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Person.Age` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Person.Email` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.body.Person.Email.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Person.Email.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Person.Nickname` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.body.Person.Nickname.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Person.Nickname.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Measurement` | `dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>` | nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.body.Measurement.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Measurement.AsInt` | `struct<value: int32>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Measurement.AsInt.value` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Measurement.AsText` | `struct<value: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Measurement.AsText.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Measurement.AsPoint` | `struct<value: struct<X: double not null, Y: double not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Measurement.AsPoint.value` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Measurement.AsPoint.value.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Measurement.AsPoint.value.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope` | `struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Id` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Location` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Location.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Location.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Tags` | `list<item: string>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.body.Envelope.Tags[]` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload` | `struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.type_id` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.type_id.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.type_id.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.type_id.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.type_id.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.type_id.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.body.Envelope.Payload.type_id.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body` | `dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7>` | not nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.body.Envelope.Payload.body.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Point` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Point.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Point.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Person` | `struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Person.Name` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Person.Age` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Person.Email` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.body.Envelope.Payload.body.Person.Email.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Person.Email.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Person.Nickname` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.body.Envelope.Payload.body.Person.Nickname.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Person.Nickname.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Measurement` | `dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>` | nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.body.Envelope.Payload.body.Measurement.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Measurement.AsInt` | `struct<value: int32>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Measurement.AsInt.value` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Measurement.AsText` | `struct<value: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Measurement.AsText.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Measurement.AsPoint` | `struct<value: struct<X: double not null, Y: double not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Measurement.AsPoint.value` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Measurement.AsPoint.value.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Measurement.AsPoint.value.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.Envelope` | `struct<>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.OptionalScalars` | `struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.OptionalScalars.Id` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.OptionalScalars.Flag` | `struct<present: bool not null, value: bool>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.OptionalScalars.Flag.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.OptionalScalars.Flag.value` | `bool` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.OptionalScalars.Count` | `struct<present: bool not null, value: int32>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.OptionalScalars.Count.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.OptionalScalars.Count.value` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.OptionalScalars.Ratio` | `struct<present: bool not null, value: double>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.OptionalScalars.Ratio.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.OptionalScalars.Ratio.value` | `double` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.FloatHolder` | `struct<A: float not null, B: struct<present: bool not null, value: float> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.FloatHolder.A` | `float` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.FloatHolder.B` | `struct<present: bool not null, value: float>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.FloatHolder.B.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.Envelope.Payload.body.FloatHolder.B.value` | `float` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.body.…` | `null` | nullable; Arrow validity bitmap when needed | Nested field list abbreviated for compactness. |

Arrow schema:

```text
value: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 1997 chars omitted)
  child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
      child 0, namespace: uint16 not null
      child 1, id_type: uint8 not null
      child 2, numeric: uint32
      child 3, string: string
      child 4, guid: fixed_size_binary[16]
      child 5, opaque: binary
  child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 1817 chars omitted) not null
      child 0, null: null
      child 1, Point: struct<X: double not null, Y: double not null>
          child 0, X: double not null
          child 1, Y: double not null
      child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
          child 0, Name: string
          child 1, Age: int32 not null
          child 2, Email: struct<present: bool not null, value: string> not null
              child 0, present: bool not null
              child 1, value: string
          child 3, Nickname: struct<present: bool not null, value: string> not null
              child 0, present: bool not null
              child 1, value: string
      child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
          child 0, null: null
          child 1, AsInt: struct<value: int32>
              child 0, value: int32
          child 2, AsText: struct<value: string>
              child 0, value: string
          child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
              child 0, value: struct<X: double not null, Y: double not null>
                  child 0, X: double not null
                  child 1, Y: double not null
      child 4, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string (... 1009 chars omitted)
          child 0, Id: string
          child 1, Location: struct<X: double not null, Y: double not null>
              child 0, X: double not null
              child 1, Y: double not null
          child 2, Tags: list<item: string>
              child 0, item: string
          child 3, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 896 chars omitted)
              child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
                  child 0, namespace: uint16 not null
                  child 1, id_type: uint8 not null
                  child 2, numeric: uint32
                  child 3, string: string
                  child 4, guid: fixed_size_binary[16]
                  child 5, opaque: binary
              child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 716 chars omitted) not null
                  child 0, null: null
                  child 1, Point: struct<X: double not null, Y: double not null>
                      child 0, X: double not null
                      child 1, Y: double not null
                  child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
                      child 0, Name: string
                      child 1, Age: int32 not null
                      child 2, Email: struct<present: bool not null, value: string> not null
                          child 0, present: bool not null
                          child 1, value: string
                      child 3, Nickname: struct<present: bool not null, value: string> not null
                          child 0, present: bool not null
                          child 1, value: string
                  child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
                      child 0, null: null
                      child 1, AsInt: struct<value: int32>
                          child 0, value: int32
                      child 2, AsText: struct<value: string>
                          child 0, value: string
                      child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
                          child 0, value: struct<X: double not null, Y: double not null>
                              child 0, X: double not null
                              child 1, Y: double not null
                  child 4, Envelope: struct<>
                  child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
                      child 0, Id: int32 not null
                      child 1, Flag: struct<present: bool not null, value: bool> not null
                          child 0, present: bool not null
                          child 1, value: bool
                      child 2, Count: struct<present: bool not null, value: int32> not null
                          child 0, present: bool not null
                          child 1, value: int32
                      child 3, Ratio: struct<present: bool not null, value: double> not null
                          child 0, present: bool not null
                          child 1, value: double
                  child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
                      child 0, A: float not null
                      child 1, B: struct<present: bool not null, value: float> not null
                          child 0, present: bool not null
                          child 1, value: float
                  child 7, binary: binary
      child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
          child 0, Id: int32 not null
          child 1, Flag: struct<present: bool not null, value: bool> not null
              child 0, present: bool not null
              child 1, value: bool
          child 2, Count: struct<present: bool not null, value: int32> not null
              child 0, present: bool not null
              child 1, value: int32
          child 3, Ratio: struct<present: bool not null, value: double> not null
              child 0, present: bool not null
              child 1, value: double
      child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
          child 0, A: float not null
          child 1, B: struct<present: bool not null, value: float> not null
              child 0, present: bool not null
              child 1, value: float
      child 7, binary: binary
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
ExtensionObject(type_id=NodeId(namespace=0,
                               id_type=<IdType.NUMERIC: 0>,
                               identifier=3001),
                body=StructValue(fields={'X': 1.0, 'Y': 1.0}, type_name='Point'))
```

### Built-in DataValue

Published schema source: `schemas\base.json builtins`. SchemaId: `83d9b3877406f207`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `struct<value: dense_union<null: null=0, scalar_Boolean: bool=1, array_Boolean: list<item: bool>=2, matrix_Boolean: struct<dimensions: list<item: int32> not null, values: list<item: bool> not null>=3, scalar_SByte: int8=4, array_SByte: list<item: int8>=5, matrix_SByte: struct<dimensions: list<item: int32> not null, values: list<item: int8> not null>=6, scalar_Byte: uint8=7, array_Byte: list<item: uint8>=8, matrix_Byte: struct<dimensions: list<item: int32> not null, values: list<item: uint8> not null>=9, scalar_Int16: int16=10, array_Int16: list<item: int16>=11, matrix_Int16: struct<dimensions: list<item: int32> not null, values: list<item: int16> not null>=12, scalar_UInt16: uint16=13, array_UInt16: list<item: uint16>=14, matrix_UInt16: struct<dimensions: list<item: int32> not null, values: list<item: uint16> not null>=15, scalar_Int32: int32=16, array_Int32: list<item: int32>=17, matrix_Int32: struct<dimensions: list<item: int32> not null, values: list<item: int32> not null>=18, scalar_UInt32: uint32=19, array_UInt32: list<item: uint32>=20, matrix_UInt32: struct<dimensions: list<item: int32> not null, values: list<item: uint32> not null>=21, scalar_Int64: int64=22, array_Int64: list<item: int64>=23, matrix_Int64: struct<dimensions: list<item: int32> not null, values: list<item: int64> not null>=24, scalar_UInt64: uint64=25, array_UInt64: list<item: uint64>=26, matrix_UInt64: struct<dimensions: list<item: int32> not null, values: list<item: uint64> not null>=27, scalar_Float: float=28, array_Float: list<item: float>=29, matrix_Float: struct<dimensions: list<item: int32> not null, values: list<item: float> not null>=30, scalar_Double: double=31, array_Double: list<item: double>=32, matrix_Double: struct<dimensions: list<item: int32> not null, values: list<item: double> not null>=33, scalar_String: string=34, array_String: list<item: string>=35, matrix_String: struct<dimensions: list<item: int32> not null, values: list<item: string> not null>=36, scalar_DateTime: int64=37, array_DateTime: list<item: int64>=38, matrix_DateTime: struct<dimensions: list<item: int32> not null, values: list<item: int64> not null>=39, scalar_Guid: fixed_size_binary[16]=40, array_Guid: list<item: fixed_size_binary[16]>=41, matrix_Guid: struct<dimensions: list<item: int32> not null, values: list<item: fixed_size_binary[16]> not null>=42, scalar_ByteString: binary=43, array_ByteString: list<item: binary>=44, matrix_ByteString: struct<dimensions: list<item: int32> not null, values: list<item: binary> not null>=45, scalar_XmlElement: string=46, array_XmlElement: list<item: string>=47, matrix_XmlElement: struct<dimensions: list<item: int32> not null, values: list<item: string> not null>=48, scalar_NodeId: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>=49, array_NodeId: list<item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>>=50, matrix_NodeId: struct<dimensions: list<item: int32> not null, values: list<item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>> not null>=51, scalar_ExpandedNodeId: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>=52, array_ExpandedNodeId: list<item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>>=53, matrix_ExpandedNodeId: struct<dimensions: list<item: int32> not null, values: list<item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>> not null>=54, scalar_StatusCode: uint32=55, array_StatusCode: list<item: uint32>=56, matrix_StatusCode: struct<dimensions: list<item: int32> not null, values: list<item: uint32> not null>=57, scalar_QualifiedName: struct<namespace: uint16 not null, name: string>=58, array_QualifiedName: list<item: struct<namespace: uint16 not null, name: string>>=59, matrix_QualifiedName: struct<dimensions: list<item: int32> not null, values: list<item: struct<namespace: uint16 not null, name: string>> not null>=60, scalar_LocalizedText: struct<locale: string, text: string>=61, array_LocalizedText: list<item: struct<locale: string, text: string>>=62, matrix_LocalizedText: struct<dimensions: list<item: int32> not null, values: list<item: struct<locale: string, text: string>> not null>=63, scalar_ExtensionObject: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>=64, array_ExtensionObject: list<item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=65, matrix_ExtensionObject: struct<dimensions: list<item: int32> not null, values: list<item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>> not null>=66>, status: uint32, source_timestamp: int64, source_picoseconds: uint16, server_timestamp: int64, server_picoseconds: uint16>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value` | `dense_union<null: null=0, scalar_Boolean: bool=1, array_Boolean: list<item: bool>=2, matrix_Boolean: struct<dimensions: list<item: int32> not null, values: list<item: bool> not null>=3, scalar_SByte: int8=4, array_SByte: list<item: int8>=5, matrix_SByte: struct<dimensions: list<item: int32> not null, values: list<item: int8> not null>=6, scalar_Byte: uint8=7, array_Byte: list<item: uint8>=8, matrix_Byte: struct<dimensions: list<item: int32> not null, values: list<item: uint8> not null>=9, scalar_Int16: int16=10, array_Int16: list<item: int16>=11, matrix_Int16: struct<dimensions: list<item: int32> not null, values: list<item: int16> not null>=12, scalar_UInt16: uint16=13, array_UInt16: list<item: uint16>=14, matrix_UInt16: struct<dimensions: list<item: int32> not null, values: list<item: uint16> not null>=15, scalar_Int32: int32=16, array_Int32: list<item: int32>=17, matrix_Int32: struct<dimensions: list<item: int32> not null, values: list<item: int32> not null>=18, scalar_UInt32: uint32=19, array_UInt32: list<item: uint32>=20, matrix_UInt32: struct<dimensions: list<item: int32> not null, values: list<item: uint32> not null>=21, scalar_Int64: int64=22, array_Int64: list<item: int64>=23, matrix_Int64: struct<dimensions: list<item: int32> not null, values: list<item: int64> not null>=24, scalar_UInt64: uint64=25, array_UInt64: list<item: uint64>=26, matrix_UInt64: struct<dimensions: list<item: int32> not null, values: list<item: uint64> not null>=27, scalar_Float: float=28, array_Float: list<item: float>=29, matrix_Float: struct<dimensions: list<item: int32> not null, values: list<item: float> not null>=30, scalar_Double: double=31, array_Double: list<item: double>=32, matrix_Double: struct<dimensions: list<item: int32> not null, values: list<item: double> not null>=33, scalar_String: string=34, array_String: list<item: string>=35, matrix_String: struct<dimensions: list<item: int32> not null, values: list<item: string> not null>=36, scalar_DateTime: int64=37, array_DateTime: list<item: int64>=38, matrix_DateTime: struct<dimensions: list<item: int32> not null, values: list<item: int64> not null>=39, scalar_Guid: fixed_size_binary[16]=40, array_Guid: list<item: fixed_size_binary[16]>=41, matrix_Guid: struct<dimensions: list<item: int32> not null, values: list<item: fixed_size_binary[16]> not null>=42, scalar_ByteString: binary=43, array_ByteString: list<item: binary>=44, matrix_ByteString: struct<dimensions: list<item: int32> not null, values: list<item: binary> not null>=45, scalar_XmlElement: string=46, array_XmlElement: list<item: string>=47, matrix_XmlElement: struct<dimensions: list<item: int32> not null, values: list<item: string> not null>=48, scalar_NodeId: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>=49, array_NodeId: list<item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>>=50, matrix_NodeId: struct<dimensions: list<item: int32> not null, values: list<item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>> not null>=51, scalar_ExpandedNodeId: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>=52, array_ExpandedNodeId: list<item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>>=53, matrix_ExpandedNodeId: struct<dimensions: list<item: int32> not null, values: list<item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>> not null>=54, scalar_StatusCode: uint32=55, array_StatusCode: list<item: uint32>=56, matrix_StatusCode: struct<dimensions: list<item: int32> not null, values: list<item: uint32> not null>=57, scalar_QualifiedName: struct<namespace: uint16 not null, name: string>=58, array_QualifiedName: list<item: struct<namespace: uint16 not null, name: string>>=59, matrix_QualifiedName: struct<dimensions: list<item: int32> not null, values: list<item: struct<namespace: uint16 not null, name: string>> not null>=60, scalar_LocalizedText: struct<locale: string, text: string>=61, array_LocalizedText: list<item: struct<locale: string, text: string>>=62, matrix_LocalizedText: struct<dimensions: list<item: int32> not null, values: list<item: struct<locale: string, text: string>> not null>=63, scalar_ExtensionObject: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>=64, array_ExtensionObject: list<item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=65, matrix_ExtensionObject: struct<dimensions: list<item: int32> not null, values: list<item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>> not null>=66>` | nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.value.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.scalar_Boolean` | `bool` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.array_Boolean` | `list<item: bool>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.array_Boolean[]` | `bool` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Boolean` | `struct<dimensions: list<item: int32> not null, values: list<item: bool> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Boolean.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_Boolean.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Boolean.values` | `list<item: bool>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_Boolean.values[]` | `bool` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.scalar_SByte` | `int8` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.array_SByte` | `list<item: int8>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.array_SByte[]` | `int8` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_SByte` | `struct<dimensions: list<item: int32> not null, values: list<item: int8> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_SByte.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_SByte.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_SByte.values` | `list<item: int8>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_SByte.values[]` | `int8` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.scalar_Byte` | `uint8` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.array_Byte` | `list<item: uint8>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.array_Byte[]` | `uint8` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Byte` | `struct<dimensions: list<item: int32> not null, values: list<item: uint8> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Byte.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_Byte.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Byte.values` | `list<item: uint8>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_Byte.values[]` | `uint8` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.scalar_Int16` | `int16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.array_Int16` | `list<item: int16>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.array_Int16[]` | `int16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Int16` | `struct<dimensions: list<item: int32> not null, values: list<item: int16> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Int16.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_Int16.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Int16.values` | `list<item: int16>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_Int16.values[]` | `int16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.scalar_UInt16` | `uint16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.array_UInt16` | `list<item: uint16>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.array_UInt16[]` | `uint16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_UInt16` | `struct<dimensions: list<item: int32> not null, values: list<item: uint16> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_UInt16.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_UInt16.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_UInt16.values` | `list<item: uint16>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_UInt16.values[]` | `uint16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.scalar_Int32` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.array_Int32` | `list<item: int32>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.array_Int32[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Int32` | `struct<dimensions: list<item: int32> not null, values: list<item: int32> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Int32.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_Int32.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Int32.values` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_Int32.values[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.scalar_UInt32` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.array_UInt32` | `list<item: uint32>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.array_UInt32[]` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_UInt32` | `struct<dimensions: list<item: int32> not null, values: list<item: uint32> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_UInt32.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_UInt32.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_UInt32.values` | `list<item: uint32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_UInt32.values[]` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.scalar_Int64` | `int64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.array_Int64` | `list<item: int64>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.array_Int64[]` | `int64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Int64` | `struct<dimensions: list<item: int32> not null, values: list<item: int64> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Int64.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_Int64.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Int64.values` | `list<item: int64>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_Int64.values[]` | `int64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.scalar_UInt64` | `uint64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.array_UInt64` | `list<item: uint64>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.array_UInt64[]` | `uint64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_UInt64` | `struct<dimensions: list<item: int32> not null, values: list<item: uint64> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_UInt64.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_UInt64.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_UInt64.values` | `list<item: uint64>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_UInt64.values[]` | `uint64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.scalar_Float` | `float` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.array_Float` | `list<item: float>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.array_Float[]` | `float` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Float` | `struct<dimensions: list<item: int32> not null, values: list<item: float> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.matrix_Float.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.value.matrix_Float.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.value.…` | `null` | nullable; Arrow validity bitmap when needed | Nested field list abbreviated for compactness. |
| `value.status` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.source_timestamp` | `int64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.source_picoseconds` | `uint16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.server_timestamp` | `int64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.server_picoseconds` | `uint16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: struct<value: dense_union<null: null=0, scalar_Boolean: bool=1, array_Boolean: list<item: bool>=2, m (... 11346 chars omitted)
  child 0, value: dense_union<null: null=0, scalar_Boolean: bool=1, array_Boolean: list<item: bool>=2, matrix_Boolean: (... 11209 chars omitted)
      child 0, null: null
      child 1, scalar_Boolean: bool
      child 2, array_Boolean: list<item: bool>
          child 0, item: bool
      child 3, matrix_Boolean: struct<dimensions: list<item: int32> not null, values: list<item: bool> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: bool> not null
              child 0, item: bool
      child 4, scalar_SByte: int8
      child 5, array_SByte: list<item: int8>
          child 0, item: int8
      child 6, matrix_SByte: struct<dimensions: list<item: int32> not null, values: list<item: int8> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: int8> not null
              child 0, item: int8
      child 7, scalar_Byte: uint8
      child 8, array_Byte: list<item: uint8>
          child 0, item: uint8
      child 9, matrix_Byte: struct<dimensions: list<item: int32> not null, values: list<item: uint8> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: uint8> not null
              child 0, item: uint8
      child 10, scalar_Int16: int16
      child 11, array_Int16: list<item: int16>
          child 0, item: int16
      child 12, matrix_Int16: struct<dimensions: list<item: int32> not null, values: list<item: int16> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: int16> not null
              child 0, item: int16
      child 13, scalar_UInt16: uint16
      child 14, array_UInt16: list<item: uint16>
          child 0, item: uint16
      child 15, matrix_UInt16: struct<dimensions: list<item: int32> not null, values: list<item: uint16> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: uint16> not null
              child 0, item: uint16
      child 16, scalar_Int32: int32
      child 17, array_Int32: list<item: int32>
          child 0, item: int32
      child 18, matrix_Int32: struct<dimensions: list<item: int32> not null, values: list<item: int32> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: int32> not null
              child 0, item: int32
      child 19, scalar_UInt32: uint32
      child 20, array_UInt32: list<item: uint32>
          child 0, item: uint32
      child 21, matrix_UInt32: struct<dimensions: list<item: int32> not null, values: list<item: uint32> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: uint32> not null
              child 0, item: uint32
      child 22, scalar_Int64: int64
      child 23, array_Int64: list<item: int64>
          child 0, item: int64
      child 24, matrix_Int64: struct<dimensions: list<item: int32> not null, values: list<item: int64> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: int64> not null
              child 0, item: int64
      child 25, scalar_UInt64: uint64
      child 26, array_UInt64: list<item: uint64>
          child 0, item: uint64
      child 27, matrix_UInt64: struct<dimensions: list<item: int32> not null, values: list<item: uint64> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: uint64> not null
              child 0, item: uint64
      child 28, scalar_Float: float
      child 29, array_Float: list<item: float>
          child 0, item: float
      child 30, matrix_Float: struct<dimensions: list<item: int32> not null, values: list<item: float> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: float> not null
              child 0, item: float
      child 31, scalar_Double: double
      child 32, array_Double: list<item: double>
          child 0, item: double
      child 33, matrix_Double: struct<dimensions: list<item: int32> not null, values: list<item: double> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: double> not null
              child 0, item: double
      child 34, scalar_String: string
      child 35, array_String: list<item: string>
          child 0, item: string
      child 36, matrix_String: struct<dimensions: list<item: int32> not null, values: list<item: string> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: string> not null
              child 0, item: string
      child 37, scalar_DateTime: int64
      child 38, array_DateTime: list<item: int64>
          child 0, item: int64
      child 39, matrix_DateTime: struct<dimensions: list<item: int32> not null, values: list<item: int64> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: int64> not null
              child 0, item: int64
      child 40, scalar_Guid: fixed_size_binary[16]
      child 41, array_Guid: list<item: fixed_size_binary[16]>
          child 0, item: fixed_size_binary[16]
      child 42, matrix_Guid: struct<dimensions: list<item: int32> not null, values: list<item: fixed_size_binary[16]> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: fixed_size_binary[16]> not null
              child 0, item: fixed_size_binary[16]
      child 43, scalar_ByteString: binary
      child 44, array_ByteString: list<item: binary>
          child 0, item: binary
      child 45, matrix_ByteString: struct<dimensions: list<item: int32> not null, values: list<item: binary> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: binary> not null
              child 0, item: binary
      child 46, scalar_XmlElement: string
      child 47, array_XmlElement: list<item: string>
          child 0, item: string
      child 48, matrix_XmlElement: struct<dimensions: list<item: int32> not null, values: list<item: string> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: string> not null
              child 0, item: string
      child 49, scalar_NodeId: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted)
          child 0, namespace: uint16 not null
          child 1, id_type: uint8 not null
          child 2, numeric: uint32
          child 3, string: string
          child 4, guid: fixed_size_binary[16]
          child 5, opaque: binary
      child 50, array_NodeId: list<item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: stri (... 49 chars omitted)
          child 0, item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted)
              child 0, namespace: uint16 not null
              child 1, id_type: uint8 not null
              child 2, numeric: uint32
              child 3, string: string
              child 4, guid: fixed_size_binary[16]
              child 5, opaque: binary
      child 51, matrix_NodeId: struct<dimensions: list<item: int32> not null, values: list<item: struct<namespace: uint16 not null, (... 114 chars omitted)
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: stri (... 49 chars omitted) not null
              child 0, item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted)
                  child 0, namespace: uint16 not null
                  child 1, id_type: uint8 not null
                  child 2, numeric: uint32
                  child 3, string: string
                  child 4, guid: fixed_size_binary[16]
                  child 5, opaque: binary
      child 52, scalar_ExpandedNodeId: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 117 chars omitted)
          child 0, node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
              child 0, namespace: uint16 not null
              child 1, id_type: uint8 not null
              child 2, numeric: uint32
              child 3, string: string
              child 4, guid: fixed_size_binary[16]
              child 5, opaque: binary
          child 1, namespace_uri: string
          child 2, server_index: uint32 not null
      child 53, array_ExpandedNodeId: list<item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint (... 129 chars omitted)
          child 0, item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 117 chars omitted)
              child 0, node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
                  child 0, namespace: uint16 not null
                  child 1, id_type: uint8 not null
                  child 2, numeric: uint32
                  child 3, string: string
                  child 4, guid: fixed_size_binary[16]
                  child 5, opaque: binary
              child 1, namespace_uri: string
              child 2, server_index: uint32 not null
      child 54, matrix_ExpandedNodeId: struct<dimensions: list<item: int32> not null, values: list<item: struct<node_id: struct<namespace:  (... 194 chars omitted)
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint (... 129 chars omitted) not null
              child 0, item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 117 chars omitted)
                  child 0, node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
                      child 0, namespace: uint16 not null
                      child 1, id_type: uint8 not null
                      child 2, numeric: uint32
                      child 3, string: string
                      child 4, guid: fixed_size_binary[16]
                      child 5, opaque: binary
                  child 1, namespace_uri: string
                  child 2, server_index: uint32 not null
      child 55, scalar_StatusCode: uint32
      child 56, array_StatusCode: list<item: uint32>
          child 0, item: uint32
      child 57, matrix_StatusCode: struct<dimensions: list<item: int32> not null, values: list<item: uint32> not null>
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: uint32> not null
              child 0, item: uint32
      child 58, scalar_QualifiedName: struct<namespace: uint16 not null, name: string>
          child 0, namespace: uint16 not null
          child 1, name: string
      child 59, array_QualifiedName: list<item: struct<namespace: uint16 not null, name: string>>
          child 0, item: struct<namespace: uint16 not null, name: string>
              child 0, namespace: uint16 not null
              child 1, name: string
      child 60, matrix_QualifiedName: struct<dimensions: list<item: int32> not null, values: list<item: struct<namespace: uint16 not null, (... 25 chars omitted)
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: struct<namespace: uint16 not null, name: string>> not null
              child 0, item: struct<namespace: uint16 not null, name: string>
                  child 0, namespace: uint16 not null
                  child 1, name: string
      child 61, scalar_LocalizedText: struct<locale: string, text: string>
          child 0, locale: string
          child 1, text: string
      child 62, array_LocalizedText: list<item: struct<locale: string, text: string>>
          child 0, item: struct<locale: string, text: string>
              child 0, locale: string
              child 1, text: string
      child 63, matrix_LocalizedText: struct<dimensions: list<item: int32> not null, values: list<item: struct<locale: string, text: strin (... 13 chars omitted)
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: struct<locale: string, text: string>> not null
              child 0, item: struct<locale: string, text: string>
                  child 0, locale: string
                  child 1, text: string
      child 64, scalar_ExtensionObject: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 1997 chars omitted)
          child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
              child 0, namespace: uint16 not null
              child 1, id_type: uint8 not null
              child 2, numeric: uint32
              child 3, string: string
              child 4, guid: fixed_size_binary[16]
              child 5, opaque: binary
          child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 1817 chars omitted) not null
              child 0, null: null
              child 1, Point: struct<X: double not null, Y: double not null>
                  child 0, X: double not null
                  child 1, Y: double not null
              child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
                  child 0, Name: string
                  child 1, Age: int32 not null
                  child 2, Email: struct<present: bool not null, value: string> not null
                      child 0, present: bool not null
                      child 1, value: string
                  child 3, Nickname: struct<present: bool not null, value: string> not null
                      child 0, present: bool not null
                      child 1, value: string
              child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
                  child 0, null: null
                  child 1, AsInt: struct<value: int32>
                      child 0, value: int32
                  child 2, AsText: struct<value: string>
                      child 0, value: string
                  child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
                      child 0, value: struct<X: double not null, Y: double not null>
                          child 0, X: double not null
                          child 1, Y: double not null
              child 4, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string (... 1009 chars omitted)
                  child 0, Id: string
                  child 1, Location: struct<X: double not null, Y: double not null>
                      child 0, X: double not null
                      child 1, Y: double not null
                  child 2, Tags: list<item: string>
                      child 0, item: string
                  child 3, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 896 chars omitted)
                      child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
                          child 0, namespace: uint16 not null
                          child 1, id_type: uint8 not null
                          child 2, numeric: uint32
                          child 3, string: string
                          child 4, guid: fixed_size_binary[16]
                          child 5, opaque: binary
                      child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 716 chars omitted) not null
                          child 0, null: null
                          child 1, Point: struct<X: double not null, Y: double not null>
                              child 0, X: double not null
                              child 1, Y: double not null
                          child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
                              child 0, Name: string
                              child 1, Age: int32 not null
                              child 2, Email: struct<present: bool not null, value: string> not null
                                  child 0, present: bool not null
                                  child 1, value: string
                              child 3, Nickname: struct<present: bool not null, value: string> not null
                                  child 0, present: bool not null
                                  child 1, value: string
                          child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
                              child 0, null: null
                              child 1, AsInt: struct<value: int32>
                                  child 0, value: int32
                              child 2, AsText: struct<value: string>
                                  child 0, value: string
                              child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
                                  child 0, value: struct<X: double not null, Y: double not null>
                                      child 0, X: double not null
                                      child 1, Y: double not null
                          child 4, Envelope: struct<>
                          child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
                              child 0, Id: int32 not null
                              child 1, Flag: struct<present: bool not null, value: bool> not null
                                  child 0, present: bool not null
                                  child 1, value: bool
                              child 2, Count: struct<present: bool not null, value: int32> not null
                                  child 0, present: bool not null
                                  child 1, value: int32
                              child 3, Ratio: struct<present: bool not null, value: double> not null
                                  child 0, present: bool not null
                                  child 1, value: double
                          child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
                              child 0, A: float not null
                              child 1, B: struct<present: bool not null, value: float> not null
                                  child 0, present: bool not null
                                  child 1, value: float
                          child 7, binary: binary
              child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
                  child 0, Id: int32 not null
                  child 1, Flag: struct<present: bool not null, value: bool> not null
                      child 0, present: bool not null
                      child 1, value: bool
                  child 2, Count: struct<present: bool not null, value: int32> not null
                      child 0, present: bool not null
                      child 1, value: int32
                  child 3, Ratio: struct<present: bool not null, value: double> not null
                      child 0, present: bool not null
                      child 1, value: double
              child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
                  child 0, A: float not null
                  child 1, B: struct<present: bool not null, value: float> not null
                      child 0, present: bool not null
                      child 1, value: float
              child 7, binary: binary
      child 65, array_ExtensionObject: list<item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint (... 2009 chars omitted)
          child 0, item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 1997 chars omitted)
              child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
                  child 0, namespace: uint16 not null
                  child 1, id_type: uint8 not null
                  child 2, numeric: uint32
                  child 3, string: string
                  child 4, guid: fixed_size_binary[16]
                  child 5, opaque: binary
              child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 1817 chars omitted) not null
                  child 0, null: null
                  child 1, Point: struct<X: double not null, Y: double not null>
                      child 0, X: double not null
                      child 1, Y: double not null
                  child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
                      child 0, Name: string
                      child 1, Age: int32 not null
                      child 2, Email: struct<present: bool not null, value: string> not null
                          child 0, present: bool not null
                          child 1, value: string
                      child 3, Nickname: struct<present: bool not null, value: string> not null
                          child 0, present: bool not null
                          child 1, value: string
                  child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
                      child 0, null: null
                      child 1, AsInt: struct<value: int32>
                          child 0, value: int32
                      child 2, AsText: struct<value: string>
                          child 0, value: string
                      child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
                          child 0, value: struct<X: double not null, Y: double not null>
                              child 0, X: double not null
                              child 1, Y: double not null
                  child 4, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string (... 1009 chars omitted)
                      child 0, Id: string
                      child 1, Location: struct<X: double not null, Y: double not null>
                          child 0, X: double not null
                          child 1, Y: double not null
                      child 2, Tags: list<item: string>
                          child 0, item: string
                      child 3, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 896 chars omitted)
                          child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
                              child 0, namespace: uint16 not null
                              child 1, id_type: uint8 not null
                              child 2, numeric: uint32
                              child 3, string: string
                              child 4, guid: fixed_size_binary[16]
                              child 5, opaque: binary
                          child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 716 chars omitted) not null
                              child 0, null: null
                              child 1, Point: struct<X: double not null, Y: double not null>
                                  child 0, X: double not null
                                  child 1, Y: double not null
                              child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
                                  child 0, Name: string
                                  child 1, Age: int32 not null
                                  child 2, Email: struct<present: bool not null, value: string> not null
                                      child 0, present: bool not null
                                      child 1, value: string
                                  child 3, Nickname: struct<present: bool not null, value: string> not null
                                      child 0, present: bool not null
                                      child 1, value: string
                              child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
                                  child 0, null: null
                                  child 1, AsInt: struct<value: int32>
                                      child 0, value: int32
                                  child 2, AsText: struct<value: string>
                                      child 0, value: string
                                  child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
                                      child 0, value: struct<X: double not null, Y: double not null>
                                          child 0, X: double not null
                                          child 1, Y: double not null
                              child 4, Envelope: struct<>
                              child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
                                  child 0, Id: int32 not null
                                  child 1, Flag: struct<present: bool not null, value: bool> not null
                                      child 0, present: bool not null
                                      child 1, value: bool
                                  child 2, Count: struct<present: bool not null, value: int32> not null
                                      child 0, present: bool not null
                                      child 1, value: int32
                                  child 3, Ratio: struct<present: bool not null, value: double> not null
                                      child 0, present: bool not null
                                      child 1, value: double
                              child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
                                  child 0, A: float not null
                                  child 1, B: struct<present: bool not null, value: float> not null
                                      child 0, present: bool not null
                                      child 1, value: float
                              child 7, binary: binary
                  child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
                      child 0, Id: int32 not null
                      child 1, Flag: struct<present: bool not null, value: bool> not null
                          child 0, present: bool not null
                          child 1, value: bool
                      child 2, Count: struct<present: bool not null, value: int32> not null
                          child 0, present: bool not null
                          child 1, value: int32
                      child 3, Ratio: struct<present: bool not null, value: double> not null
                          child 0, present: bool not null
                          child 1, value: double
                  child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
                      child 0, A: float not null
                      child 1, B: struct<present: bool not null, value: float> not null
                          child 0, present: bool not null
                          child 1, value: float
                  child 7, binary: binary
      child 66, matrix_ExtensionObject: struct<dimensions: list<item: int32> not null, values: list<item: struct<type_id: struct<namespace:  (... 2074 chars omitted)
          child 0, dimensions: list<item: int32> not null
              child 0, item: int32
          child 1, values: list<item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint (... 2009 chars omitted) not null
              child 0, item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 1997 chars omitted)
                  child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
                      child 0, namespace: uint16 not null
                      child 1, id_type: uint8 not null
                      child 2, numeric: uint32
                      child 3, string: string
                      child 4, guid: fixed_size_binary[16]
                      child 5, opaque: binary
                  child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 1817 chars omitted) not null
                      child 0, null: null
                      child 1, Point: struct<X: double not null, Y: double not null>
                          child 0, X: double not null
                          child 1, Y: double not null
                      child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
                          child 0, Name: string
                          child 1, Age: int32 not null
                          child 2, Email: struct<present: bool not null, value: string> not null
                              child 0, present: bool not null
                              child 1, value: string
                          child 3, Nickname: struct<present: bool not null, value: string> not null
                              child 0, present: bool not null
                              child 1, value: string
                      child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
                          child 0, null: null
                          child 1, AsInt: struct<value: int32>
                              child 0, value: int32
                          child 2, AsText: struct<value: string>
                              child 0, value: string
                          child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
                              child 0, value: struct<X: double not null, Y: double not null>
                                  child 0, X: double not null
                                  child 1, Y: double not null
                      child 4, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string (... 1009 chars omitted)
                          child 0, Id: string
                          child 1, Location: struct<X: double not null, Y: double not null>
                              child 0, X: double not null
                              child 1, Y: double not null
                          child 2, Tags: list<item: string>
                              child 0, item: string
                          child 3, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 896 chars omitted)
                              child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
                                  child 0, namespace: uint16 not null
                                  child 1, id_type: uint8 not null
                                  child 2, numeric: uint32
                                  child 3, string: string
                                  child 4, guid: fixed_size_binary[16]
                                  child 5, opaque: binary
                              child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 716 chars omitted) not null
                                  child 0, null: null
                                  child 1, Point: struct<X: double not null, Y: double not null>
                                      child 0, X: double not null
                                      child 1, Y: double not null
                                  child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
                                      child 0, Name: string
                                      child 1, Age: int32 not null
                                      child 2, Email: struct<present: bool not null, value: string> not null
                                          child 0, present: bool not null
                                          child 1, value: string
                                      child 3, Nickname: struct<present: bool not null, value: string> not null
                                          child 0, present: bool not null
                                          child 1, value: string
                                  child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
                                      child 0, null: null
                                      child 1, AsInt: struct<value: int32>
                                          child 0, value: int32
                                      child 2, AsText: struct<value: string>
                                          child 0, value: string
                                      child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
                                          child 0, value: struct<X: double not null, Y: double not null>
                                              child 0, X: double not null
                                              child 1, Y: double not null
                                  child 4, Envelope: struct<>
                                  child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
                                      child 0, Id: int32 not null
                                      child 1, Flag: struct<present: bool not null, value: bool> not null
                                          child 0, present: bool not null
                                          child 1, value: bool
                                      child 2, Count: struct<present: bool not null, value: int32> not null
                                          child 0, present: bool not null
                                          child 1, value: int32
                                      child 3, Ratio: struct<present: bool not null, value: double> not null
                                          child 0, present: bool not null
                                          child 1, value: double
                                  child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
                                      child 0, A: float not null
                                      child 1, B: struct<present: bool not null, value: float> not null
                                          child 0, present: bool not null
                                          child 1, value: float
                                  child 7, binary: binary
                      child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
                          child 0, Id: int32 not null
                          child 1, Flag: struct<present: bool not null, value: bool> not null
                              child 0, present: bool not null
                              child 1, value: bool
                          child 2, Count: struct<present: bool not null, value: int32> not null
                              child 0, present: bool not null
                              child 1, value: int32
                          child 3, Ratio: struct<present: bool not null, value: double> not null
                              child 0, present: bool not null
                              child 1, value: double
                      child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
                          child 0, A: float not null
                          child 1, B: struct<present: bool not null, value: float> not null
                              child 0, present: bool not null
                              child 1, value: float
                      child 7, binary: binary
  child 1, status: uint32
  child 2, source_timestamp: int64
  child 3, source_picoseconds: uint16
  child 4, server_timestamp: int64
  child 5, server_picoseconds: uint16
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
DataValue(value=Variant(vtype=Builtin(id=<BuiltInType.Int32: 6>),
                        value=42,
                        dimensions=None),
          status=StatusCode(value=0),
          source_timestamp=DateTime(ticks=1000),
          source_picoseconds=500,
          server_timestamp=DateTime(ticks=2000),
          server_picoseconds=250)
```

### Built-in Variant

Published schema source: `schemas\base.json builtins`. SchemaId: `bb30bbf4a4cc8cbd`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `dense_union<null: null=0, scalar_Boolean: bool=1, array_Boolean: list<item: bool>=2, matrix_Boolean: struct<dimensions: list<item: int32> not null, values: list<item: bool> not null>=3, scalar_SByte: int8=4, array_SByte: list<item: int8>=5, matrix_SByte: struct<dimensions: list<item: int32> not null, values: list<item: int8> not null>=6, scalar_Byte: uint8=7, array_Byte: list<item: uint8>=8, matrix_Byte: struct<dimensions: list<item: int32> not null, values: list<item: uint8> not null>=9, scalar_Int16: int16=10, array_Int16: list<item: int16>=11, matrix_Int16: struct<dimensions: list<item: int32> not null, values: list<item: int16> not null>=12, scalar_UInt16: uint16=13, array_UInt16: list<item: uint16>=14, matrix_UInt16: struct<dimensions: list<item: int32> not null, values: list<item: uint16> not null>=15, scalar_Int32: int32=16, array_Int32: list<item: int32>=17, matrix_Int32: struct<dimensions: list<item: int32> not null, values: list<item: int32> not null>=18, scalar_UInt32: uint32=19, array_UInt32: list<item: uint32>=20, matrix_UInt32: struct<dimensions: list<item: int32> not null, values: list<item: uint32> not null>=21, scalar_Int64: int64=22, array_Int64: list<item: int64>=23, matrix_Int64: struct<dimensions: list<item: int32> not null, values: list<item: int64> not null>=24, scalar_UInt64: uint64=25, array_UInt64: list<item: uint64>=26, matrix_UInt64: struct<dimensions: list<item: int32> not null, values: list<item: uint64> not null>=27, scalar_Float: float=28, array_Float: list<item: float>=29, matrix_Float: struct<dimensions: list<item: int32> not null, values: list<item: float> not null>=30, scalar_Double: double=31, array_Double: list<item: double>=32, matrix_Double: struct<dimensions: list<item: int32> not null, values: list<item: double> not null>=33, scalar_String: string=34, array_String: list<item: string>=35, matrix_String: struct<dimensions: list<item: int32> not null, values: list<item: string> not null>=36, scalar_DateTime: int64=37, array_DateTime: list<item: int64>=38, matrix_DateTime: struct<dimensions: list<item: int32> not null, values: list<item: int64> not null>=39, scalar_Guid: fixed_size_binary[16]=40, array_Guid: list<item: fixed_size_binary[16]>=41, matrix_Guid: struct<dimensions: list<item: int32> not null, values: list<item: fixed_size_binary[16]> not null>=42, scalar_ByteString: binary=43, array_ByteString: list<item: binary>=44, matrix_ByteString: struct<dimensions: list<item: int32> not null, values: list<item: binary> not null>=45, scalar_XmlElement: string=46, array_XmlElement: list<item: string>=47, matrix_XmlElement: struct<dimensions: list<item: int32> not null, values: list<item: string> not null>=48, scalar_NodeId: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>=49, array_NodeId: list<item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>>=50, matrix_NodeId: struct<dimensions: list<item: int32> not null, values: list<item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>> not null>=51, scalar_ExpandedNodeId: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>=52, array_ExpandedNodeId: list<item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>>=53, matrix_ExpandedNodeId: struct<dimensions: list<item: int32> not null, values: list<item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>> not null>=54, scalar_StatusCode: uint32=55, array_StatusCode: list<item: uint32>=56, matrix_StatusCode: struct<dimensions: list<item: int32> not null, values: list<item: uint32> not null>=57, scalar_QualifiedName: struct<namespace: uint16 not null, name: string>=58, array_QualifiedName: list<item: struct<namespace: uint16 not null, name: string>>=59, matrix_QualifiedName: struct<dimensions: list<item: int32> not null, values: list<item: struct<namespace: uint16 not null, name: string>> not null>=60, scalar_LocalizedText: struct<locale: string, text: string>=61, array_LocalizedText: list<item: struct<locale: string, text: string>>=62, matrix_LocalizedText: struct<dimensions: list<item: int32> not null, values: list<item: struct<locale: string, text: string>> not null>=63, scalar_ExtensionObject: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>=64, array_ExtensionObject: list<item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=65, matrix_ExtensionObject: struct<dimensions: list<item: int32> not null, values: list<item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>> not null>=66>` | nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_Boolean` | `bool` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_Boolean` | `list<item: bool>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_Boolean[]` | `bool` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Boolean` | `struct<dimensions: list<item: int32> not null, values: list<item: bool> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Boolean.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Boolean.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Boolean.values` | `list<item: bool>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Boolean.values[]` | `bool` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_SByte` | `int8` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_SByte` | `list<item: int8>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_SByte[]` | `int8` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_SByte` | `struct<dimensions: list<item: int32> not null, values: list<item: int8> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_SByte.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_SByte.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_SByte.values` | `list<item: int8>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_SByte.values[]` | `int8` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_Byte` | `uint8` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_Byte` | `list<item: uint8>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_Byte[]` | `uint8` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Byte` | `struct<dimensions: list<item: int32> not null, values: list<item: uint8> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Byte.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Byte.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Byte.values` | `list<item: uint8>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Byte.values[]` | `uint8` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_Int16` | `int16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_Int16` | `list<item: int16>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_Int16[]` | `int16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Int16` | `struct<dimensions: list<item: int32> not null, values: list<item: int16> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Int16.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Int16.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Int16.values` | `list<item: int16>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Int16.values[]` | `int16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_UInt16` | `uint16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_UInt16` | `list<item: uint16>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_UInt16[]` | `uint16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_UInt16` | `struct<dimensions: list<item: int32> not null, values: list<item: uint16> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_UInt16.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_UInt16.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_UInt16.values` | `list<item: uint16>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_UInt16.values[]` | `uint16` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_Int32` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_Int32` | `list<item: int32>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_Int32[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Int32` | `struct<dimensions: list<item: int32> not null, values: list<item: int32> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Int32.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Int32.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Int32.values` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Int32.values[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_UInt32` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_UInt32` | `list<item: uint32>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_UInt32[]` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_UInt32` | `struct<dimensions: list<item: int32> not null, values: list<item: uint32> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_UInt32.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_UInt32.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_UInt32.values` | `list<item: uint32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_UInt32.values[]` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_Int64` | `int64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_Int64` | `list<item: int64>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_Int64[]` | `int64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Int64` | `struct<dimensions: list<item: int32> not null, values: list<item: int64> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Int64.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Int64.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Int64.values` | `list<item: int64>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Int64.values[]` | `int64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_UInt64` | `uint64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_UInt64` | `list<item: uint64>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_UInt64[]` | `uint64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_UInt64` | `struct<dimensions: list<item: int32> not null, values: list<item: uint64> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_UInt64.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_UInt64.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_UInt64.values` | `list<item: uint64>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_UInt64.values[]` | `uint64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_Float` | `float` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_Float` | `list<item: float>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_Float[]` | `float` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Float` | `struct<dimensions: list<item: int32> not null, values: list<item: float> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Float.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Float.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Float.values` | `list<item: float>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Float.values[]` | `float` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_Double` | `double` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_Double` | `list<item: double>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_Double[]` | `double` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Double` | `struct<dimensions: list<item: int32> not null, values: list<item: double> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Double.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Double.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Double.values` | `list<item: double>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Double.values[]` | `double` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_String` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_String` | `list<item: string>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_String[]` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_String` | `struct<dimensions: list<item: int32> not null, values: list<item: string> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_String.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_String.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_String.values` | `list<item: string>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_String.values[]` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_DateTime` | `int64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_DateTime` | `list<item: int64>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_DateTime[]` | `int64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_DateTime` | `struct<dimensions: list<item: int32> not null, values: list<item: int64> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_DateTime.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_DateTime.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_DateTime.values` | `list<item: int64>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_DateTime.values[]` | `int64` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_Guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.array_Guid` | `list<item: fixed_size_binary[16]>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_Guid[]` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.matrix_Guid` | `struct<dimensions: list<item: int32> not null, values: list<item: fixed_size_binary[16]> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Guid.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Guid.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_Guid.values` | `list<item: fixed_size_binary[16]>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_Guid.values[]` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.scalar_ByteString` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ByteString` | `list<item: binary>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_ByteString[]` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ByteString` | `struct<dimensions: list<item: int32> not null, values: list<item: binary> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ByteString.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_ByteString.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ByteString.values` | `list<item: binary>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_ByteString.values[]` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_XmlElement` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_XmlElement` | `list<item: string>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_XmlElement[]` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_XmlElement` | `struct<dimensions: list<item: int32> not null, values: list<item: string> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_XmlElement.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_XmlElement.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_XmlElement.values` | `list<item: string>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_XmlElement.values[]` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_NodeId` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_NodeId.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_NodeId.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_NodeId.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_NodeId.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_NodeId.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.scalar_NodeId.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_NodeId` | `list<item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_NodeId[]` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_NodeId[].namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_NodeId[].id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_NodeId[].numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_NodeId[].string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_NodeId[].guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.array_NodeId[].opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_NodeId` | `struct<dimensions: list<item: int32> not null, values: list<item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_NodeId.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_NodeId.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_NodeId.values` | `list<item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_NodeId.values[]` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_NodeId.values[].namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_NodeId.values[].id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_NodeId.values[].numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_NodeId.values[].string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_NodeId.values[].guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.matrix_NodeId.values[].opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExpandedNodeId` | `struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExpandedNodeId.node_id` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExpandedNodeId.node_id.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExpandedNodeId.node_id.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExpandedNodeId.node_id.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExpandedNodeId.node_id.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExpandedNodeId.node_id.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.scalar_ExpandedNodeId.node_id.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExpandedNodeId.namespace_uri` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExpandedNodeId.server_index` | `uint32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExpandedNodeId` | `list<item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_ExpandedNodeId[]` | `struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExpandedNodeId[].node_id` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExpandedNodeId[].node_id.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExpandedNodeId[].node_id.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExpandedNodeId[].node_id.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExpandedNodeId[].node_id.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExpandedNodeId[].node_id.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.array_ExpandedNodeId[].node_id.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExpandedNodeId[].namespace_uri` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExpandedNodeId[].server_index` | `uint32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExpandedNodeId` | `struct<dimensions: list<item: int32> not null, values: list<item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExpandedNodeId.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_ExpandedNodeId.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExpandedNodeId.values` | `list<item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_ExpandedNodeId.values[]` | `struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, namespace_uri: string, server_index: uint32 not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExpandedNodeId.values[].node_id` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExpandedNodeId.values[].node_id.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExpandedNodeId.values[].node_id.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExpandedNodeId.values[].node_id.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExpandedNodeId.values[].node_id.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExpandedNodeId.values[].node_id.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.matrix_ExpandedNodeId.values[].node_id.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExpandedNodeId.values[].namespace_uri` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExpandedNodeId.values[].server_index` | `uint32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_StatusCode` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_StatusCode` | `list<item: uint32>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_StatusCode[]` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_StatusCode` | `struct<dimensions: list<item: int32> not null, values: list<item: uint32> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_StatusCode.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_StatusCode.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_StatusCode.values` | `list<item: uint32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_StatusCode.values[]` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_QualifiedName` | `struct<namespace: uint16 not null, name: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_QualifiedName.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_QualifiedName.name` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_QualifiedName` | `list<item: struct<namespace: uint16 not null, name: string>>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_QualifiedName[]` | `struct<namespace: uint16 not null, name: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_QualifiedName[].namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_QualifiedName[].name` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_QualifiedName` | `struct<dimensions: list<item: int32> not null, values: list<item: struct<namespace: uint16 not null, name: string>> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_QualifiedName.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_QualifiedName.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_QualifiedName.values` | `list<item: struct<namespace: uint16 not null, name: string>>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_QualifiedName.values[]` | `struct<namespace: uint16 not null, name: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_QualifiedName.values[].namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_QualifiedName.values[].name` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_LocalizedText` | `struct<locale: string, text: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_LocalizedText.locale` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_LocalizedText.text` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_LocalizedText` | `list<item: struct<locale: string, text: string>>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_LocalizedText[]` | `struct<locale: string, text: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_LocalizedText[].locale` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_LocalizedText[].text` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_LocalizedText` | `struct<dimensions: list<item: int32> not null, values: list<item: struct<locale: string, text: string>> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_LocalizedText.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_LocalizedText.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_LocalizedText.values` | `list<item: struct<locale: string, text: string>>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_LocalizedText.values[]` | `struct<locale: string, text: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_LocalizedText.values[].locale` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_LocalizedText.values[].text` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject` | `struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.type_id` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.type_id.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.type_id.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.type_id.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.type_id.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.type_id.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.scalar_ExtensionObject.type_id.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body` | `dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7>` | not nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.scalar_ExtensionObject.body.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Point` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Point.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Point.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Person` | `struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Person.Name` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Person.Age` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Person.Email` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.scalar_ExtensionObject.body.Person.Email.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Person.Email.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Person.Nickname` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.scalar_ExtensionObject.body.Person.Nickname.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Person.Nickname.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Measurement` | `dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>` | nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.scalar_ExtensionObject.body.Measurement.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Measurement.AsInt` | `struct<value: int32>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Measurement.AsInt.value` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Measurement.AsText` | `struct<value: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Measurement.AsText.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Measurement.AsPoint` | `struct<value: struct<X: double not null, Y: double not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Measurement.AsPoint.value` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Measurement.AsPoint.value.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Measurement.AsPoint.value.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope` | `struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Id` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Location` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Location.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Location.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Tags` | `list<item: string>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.scalar_ExtensionObject.body.Envelope.Tags[]` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload` | `struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.type_id` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.type_id.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.type_id.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.type_id.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.type_id.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.type_id.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.type_id.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body` | `dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7>` | not nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Point` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Point.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Point.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Person` | `struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Person.Name` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Person.Age` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Person.Email` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Person.Email.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Person.Email.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Person.Nickname` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Person.Nickname.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Person.Nickname.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Measurement` | `dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>` | nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Measurement.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Measurement.AsInt` | `struct<value: int32>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Measurement.AsInt.value` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Measurement.AsText` | `struct<value: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Measurement.AsText.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Measurement.AsPoint` | `struct<value: struct<X: double not null, Y: double not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Measurement.AsPoint.value` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Measurement.AsPoint.value.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Measurement.AsPoint.value.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.Envelope` | `struct<>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.OptionalScalars` | `struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.OptionalScalars.Id` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.OptionalScalars.Flag` | `struct<present: bool not null, value: bool>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.OptionalScalars.Flag.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.OptionalScalars.Flag.value` | `bool` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.OptionalScalars.Count` | `struct<present: bool not null, value: int32>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.OptionalScalars.Count.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.body.Envelope.Payload.body.OptionalScalars.Count.value` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.scalar_ExtensionObject.…` | `null` | nullable; Arrow validity bitmap when needed | Nested field list abbreviated for compactness. |
| `value.array_ExtensionObject` | `list<item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_ExtensionObject[]` | `struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].type_id` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].type_id.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].type_id.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].type_id.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].type_id.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].type_id.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.array_ExtensionObject[].type_id.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body` | `dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7>` | not nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.array_ExtensionObject[].body.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Point` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Point.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Point.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Person` | `struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Person.Name` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Person.Age` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Person.Email` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.array_ExtensionObject[].body.Person.Email.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Person.Email.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Person.Nickname` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.array_ExtensionObject[].body.Person.Nickname.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Person.Nickname.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Measurement` | `dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>` | nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.array_ExtensionObject[].body.Measurement.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Measurement.AsInt` | `struct<value: int32>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Measurement.AsInt.value` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Measurement.AsText` | `struct<value: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Measurement.AsText.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Measurement.AsPoint` | `struct<value: struct<X: double not null, Y: double not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Measurement.AsPoint.value` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Measurement.AsPoint.value.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Measurement.AsPoint.value.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope` | `struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Id` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Location` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Location.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Location.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Tags` | `list<item: string>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.array_ExtensionObject[].body.Envelope.Tags[]` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload` | `struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.type_id` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.type_id.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.type_id.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.type_id.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.type_id.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.type_id.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.array_ExtensionObject[].body.Envelope.Payload.type_id.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body` | `dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7>` | not nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Point` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Point.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Point.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Person` | `struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Person.Name` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Person.Age` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Person.Email` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Person.Email.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Person.Email.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Person.Nickname` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Person.Nickname.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Person.Nickname.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Measurement` | `dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>` | nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Measurement.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Measurement.AsInt` | `struct<value: int32>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Measurement.AsInt.value` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Measurement.AsText` | `struct<value: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Measurement.AsText.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Measurement.AsPoint` | `struct<value: struct<X: double not null, Y: double not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Measurement.AsPoint.value` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Measurement.AsPoint.value.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Measurement.AsPoint.value.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.Envelope` | `struct<>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.OptionalScalars` | `struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.OptionalScalars.Id` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.OptionalScalars.Flag` | `struct<present: bool not null, value: bool>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.OptionalScalars.Flag.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.OptionalScalars.Flag.value` | `bool` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.OptionalScalars.Count` | `struct<present: bool not null, value: int32>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject[].body.Envelope.Payload.body.OptionalScalars.Count.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.array_ExtensionObject.…` | `null` | nullable; Arrow validity bitmap when needed | Nested field list abbreviated for compactness. |
| `value.matrix_ExtensionObject` | `struct<dimensions: list<item: int32> not null, values: list<item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_ExtensionObject.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values` | `list<item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_ExtensionObject.values[]` | `struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].type_id` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].type_id.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].type_id.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].type_id.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].type_id.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].type_id.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.matrix_ExtensionObject.values[].type_id.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body` | `dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7>` | not nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.matrix_ExtensionObject.values[].body.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Point` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Point.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Point.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Person` | `struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Person.Name` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Person.Age` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Person.Email` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.matrix_ExtensionObject.values[].body.Person.Email.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Person.Email.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Person.Nickname` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.matrix_ExtensionObject.values[].body.Person.Nickname.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Person.Nickname.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Measurement` | `dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>` | nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.matrix_ExtensionObject.values[].body.Measurement.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Measurement.AsInt` | `struct<value: int32>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Measurement.AsInt.value` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Measurement.AsText` | `struct<value: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Measurement.AsText.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Measurement.AsPoint` | `struct<value: struct<X: double not null, Y: double not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Measurement.AsPoint.value` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Measurement.AsPoint.value.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Measurement.AsPoint.value.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope` | `struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Id` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Location` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Location.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Location.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Tags` | `list<item: string>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Tags[]` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload` | `struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.type_id` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.type_id.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.type_id.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.type_id.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.type_id.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.type_id.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.type_id.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body` | `dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7>` | not nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Point` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Point.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Point.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Person` | `struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Person.Name` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Person.Age` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Person.Email` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Person.Email.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Person.Email.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Person.Nickname` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Person.Nickname.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Person.Nickname.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Measurement` | `dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>` | nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Measurement.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Measurement.AsInt` | `struct<value: int32>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Measurement.AsInt.value` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Measurement.AsText` | `struct<value: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Measurement.AsText.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Measurement.AsPoint` | `struct<value: struct<X: double not null, Y: double not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Measurement.AsPoint.value` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Measurement.AsPoint.value.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Measurement.AsPoint.value.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.Envelope` | `struct<>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.OptionalScalars` | `struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.OptionalScalars.Id` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.OptionalScalars.Flag` | `struct<present: bool not null, value: bool>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.values[].body.Envelope.Payload.body.OptionalScalars.Flag.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.matrix_ExtensionObject.…` | `null` | nullable; Arrow validity bitmap when needed | Nested field list abbreviated for compactness. |

Arrow schema:

```text
value: dense_union<null: null=0, scalar_Boolean: bool=1, array_Boolean: list<item: bool>=2, matrix_Boolean: (... 11209 chars omitted)
  child 0, null: null
  child 1, scalar_Boolean: bool
  child 2, array_Boolean: list<item: bool>
      child 0, item: bool
  child 3, matrix_Boolean: struct<dimensions: list<item: int32> not null, values: list<item: bool> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: bool> not null
          child 0, item: bool
  child 4, scalar_SByte: int8
  child 5, array_SByte: list<item: int8>
      child 0, item: int8
  child 6, matrix_SByte: struct<dimensions: list<item: int32> not null, values: list<item: int8> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: int8> not null
          child 0, item: int8
  child 7, scalar_Byte: uint8
  child 8, array_Byte: list<item: uint8>
      child 0, item: uint8
  child 9, matrix_Byte: struct<dimensions: list<item: int32> not null, values: list<item: uint8> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: uint8> not null
          child 0, item: uint8
  child 10, scalar_Int16: int16
  child 11, array_Int16: list<item: int16>
      child 0, item: int16
  child 12, matrix_Int16: struct<dimensions: list<item: int32> not null, values: list<item: int16> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: int16> not null
          child 0, item: int16
  child 13, scalar_UInt16: uint16
  child 14, array_UInt16: list<item: uint16>
      child 0, item: uint16
  child 15, matrix_UInt16: struct<dimensions: list<item: int32> not null, values: list<item: uint16> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: uint16> not null
          child 0, item: uint16
  child 16, scalar_Int32: int32
  child 17, array_Int32: list<item: int32>
      child 0, item: int32
  child 18, matrix_Int32: struct<dimensions: list<item: int32> not null, values: list<item: int32> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: int32> not null
          child 0, item: int32
  child 19, scalar_UInt32: uint32
  child 20, array_UInt32: list<item: uint32>
      child 0, item: uint32
  child 21, matrix_UInt32: struct<dimensions: list<item: int32> not null, values: list<item: uint32> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: uint32> not null
          child 0, item: uint32
  child 22, scalar_Int64: int64
  child 23, array_Int64: list<item: int64>
      child 0, item: int64
  child 24, matrix_Int64: struct<dimensions: list<item: int32> not null, values: list<item: int64> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: int64> not null
          child 0, item: int64
  child 25, scalar_UInt64: uint64
  child 26, array_UInt64: list<item: uint64>
      child 0, item: uint64
  child 27, matrix_UInt64: struct<dimensions: list<item: int32> not null, values: list<item: uint64> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: uint64> not null
          child 0, item: uint64
  child 28, scalar_Float: float
  child 29, array_Float: list<item: float>
      child 0, item: float
  child 30, matrix_Float: struct<dimensions: list<item: int32> not null, values: list<item: float> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: float> not null
          child 0, item: float
  child 31, scalar_Double: double
  child 32, array_Double: list<item: double>
      child 0, item: double
  child 33, matrix_Double: struct<dimensions: list<item: int32> not null, values: list<item: double> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: double> not null
          child 0, item: double
  child 34, scalar_String: string
  child 35, array_String: list<item: string>
      child 0, item: string
  child 36, matrix_String: struct<dimensions: list<item: int32> not null, values: list<item: string> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: string> not null
          child 0, item: string
  child 37, scalar_DateTime: int64
  child 38, array_DateTime: list<item: int64>
      child 0, item: int64
  child 39, matrix_DateTime: struct<dimensions: list<item: int32> not null, values: list<item: int64> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: int64> not null
          child 0, item: int64
  child 40, scalar_Guid: fixed_size_binary[16]
  child 41, array_Guid: list<item: fixed_size_binary[16]>
      child 0, item: fixed_size_binary[16]
  child 42, matrix_Guid: struct<dimensions: list<item: int32> not null, values: list<item: fixed_size_binary[16]> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: fixed_size_binary[16]> not null
          child 0, item: fixed_size_binary[16]
  child 43, scalar_ByteString: binary
  child 44, array_ByteString: list<item: binary>
      child 0, item: binary
  child 45, matrix_ByteString: struct<dimensions: list<item: int32> not null, values: list<item: binary> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: binary> not null
          child 0, item: binary
  child 46, scalar_XmlElement: string
  child 47, array_XmlElement: list<item: string>
      child 0, item: string
  child 48, matrix_XmlElement: struct<dimensions: list<item: int32> not null, values: list<item: string> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: string> not null
          child 0, item: string
  child 49, scalar_NodeId: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted)
      child 0, namespace: uint16 not null
      child 1, id_type: uint8 not null
      child 2, numeric: uint32
      child 3, string: string
      child 4, guid: fixed_size_binary[16]
      child 5, opaque: binary
  child 50, array_NodeId: list<item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: stri (... 49 chars omitted)
      child 0, item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted)
          child 0, namespace: uint16 not null
          child 1, id_type: uint8 not null
          child 2, numeric: uint32
          child 3, string: string
          child 4, guid: fixed_size_binary[16]
          child 5, opaque: binary
  child 51, matrix_NodeId: struct<dimensions: list<item: int32> not null, values: list<item: struct<namespace: uint16 not null, (... 114 chars omitted)
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: stri (... 49 chars omitted) not null
          child 0, item: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted)
              child 0, namespace: uint16 not null
              child 1, id_type: uint8 not null
              child 2, numeric: uint32
              child 3, string: string
              child 4, guid: fixed_size_binary[16]
              child 5, opaque: binary
  child 52, scalar_ExpandedNodeId: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 117 chars omitted)
      child 0, node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
          child 0, namespace: uint16 not null
          child 1, id_type: uint8 not null
          child 2, numeric: uint32
          child 3, string: string
          child 4, guid: fixed_size_binary[16]
          child 5, opaque: binary
      child 1, namespace_uri: string
      child 2, server_index: uint32 not null
  child 53, array_ExpandedNodeId: list<item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint (... 129 chars omitted)
      child 0, item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 117 chars omitted)
          child 0, node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
              child 0, namespace: uint16 not null
              child 1, id_type: uint8 not null
              child 2, numeric: uint32
              child 3, string: string
              child 4, guid: fixed_size_binary[16]
              child 5, opaque: binary
          child 1, namespace_uri: string
          child 2, server_index: uint32 not null
  child 54, matrix_ExpandedNodeId: struct<dimensions: list<item: int32> not null, values: list<item: struct<node_id: struct<namespace:  (... 194 chars omitted)
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint (... 129 chars omitted) not null
          child 0, item: struct<node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 117 chars omitted)
              child 0, node_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
                  child 0, namespace: uint16 not null
                  child 1, id_type: uint8 not null
                  child 2, numeric: uint32
                  child 3, string: string
                  child 4, guid: fixed_size_binary[16]
                  child 5, opaque: binary
              child 1, namespace_uri: string
              child 2, server_index: uint32 not null
  child 55, scalar_StatusCode: uint32
  child 56, array_StatusCode: list<item: uint32>
      child 0, item: uint32
  child 57, matrix_StatusCode: struct<dimensions: list<item: int32> not null, values: list<item: uint32> not null>
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: uint32> not null
          child 0, item: uint32
  child 58, scalar_QualifiedName: struct<namespace: uint16 not null, name: string>
      child 0, namespace: uint16 not null
      child 1, name: string
  child 59, array_QualifiedName: list<item: struct<namespace: uint16 not null, name: string>>
      child 0, item: struct<namespace: uint16 not null, name: string>
          child 0, namespace: uint16 not null
          child 1, name: string
  child 60, matrix_QualifiedName: struct<dimensions: list<item: int32> not null, values: list<item: struct<namespace: uint16 not null, (... 25 chars omitted)
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: struct<namespace: uint16 not null, name: string>> not null
          child 0, item: struct<namespace: uint16 not null, name: string>
              child 0, namespace: uint16 not null
              child 1, name: string
  child 61, scalar_LocalizedText: struct<locale: string, text: string>
      child 0, locale: string
      child 1, text: string
  child 62, array_LocalizedText: list<item: struct<locale: string, text: string>>
      child 0, item: struct<locale: string, text: string>
          child 0, locale: string
          child 1, text: string
  child 63, matrix_LocalizedText: struct<dimensions: list<item: int32> not null, values: list<item: struct<locale: string, text: strin (... 13 chars omitted)
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: struct<locale: string, text: string>> not null
          child 0, item: struct<locale: string, text: string>
              child 0, locale: string
              child 1, text: string
  child 64, scalar_ExtensionObject: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 1997 chars omitted)
      child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
          child 0, namespace: uint16 not null
          child 1, id_type: uint8 not null
          child 2, numeric: uint32
          child 3, string: string
          child 4, guid: fixed_size_binary[16]
          child 5, opaque: binary
      child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 1817 chars omitted) not null
          child 0, null: null
          child 1, Point: struct<X: double not null, Y: double not null>
              child 0, X: double not null
              child 1, Y: double not null
          child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
              child 0, Name: string
              child 1, Age: int32 not null
              child 2, Email: struct<present: bool not null, value: string> not null
                  child 0, present: bool not null
                  child 1, value: string
              child 3, Nickname: struct<present: bool not null, value: string> not null
                  child 0, present: bool not null
                  child 1, value: string
          child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
              child 0, null: null
              child 1, AsInt: struct<value: int32>
                  child 0, value: int32
              child 2, AsText: struct<value: string>
                  child 0, value: string
              child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
                  child 0, value: struct<X: double not null, Y: double not null>
                      child 0, X: double not null
                      child 1, Y: double not null
          child 4, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string (... 1009 chars omitted)
              child 0, Id: string
              child 1, Location: struct<X: double not null, Y: double not null>
                  child 0, X: double not null
                  child 1, Y: double not null
              child 2, Tags: list<item: string>
                  child 0, item: string
              child 3, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 896 chars omitted)
                  child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
                      child 0, namespace: uint16 not null
                      child 1, id_type: uint8 not null
                      child 2, numeric: uint32
                      child 3, string: string
                      child 4, guid: fixed_size_binary[16]
                      child 5, opaque: binary
                  child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 716 chars omitted) not null
                      child 0, null: null
                      child 1, Point: struct<X: double not null, Y: double not null>
                          child 0, X: double not null
                          child 1, Y: double not null
                      child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
                          child 0, Name: string
                          child 1, Age: int32 not null
                          child 2, Email: struct<present: bool not null, value: string> not null
                              child 0, present: bool not null
                              child 1, value: string
                          child 3, Nickname: struct<present: bool not null, value: string> not null
                              child 0, present: bool not null
                              child 1, value: string
                      child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
                          child 0, null: null
                          child 1, AsInt: struct<value: int32>
                              child 0, value: int32
                          child 2, AsText: struct<value: string>
                              child 0, value: string
                          child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
                              child 0, value: struct<X: double not null, Y: double not null>
                                  child 0, X: double not null
                                  child 1, Y: double not null
                      child 4, Envelope: struct<>
                      child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
                          child 0, Id: int32 not null
                          child 1, Flag: struct<present: bool not null, value: bool> not null
                              child 0, present: bool not null
                              child 1, value: bool
                          child 2, Count: struct<present: bool not null, value: int32> not null
                              child 0, present: bool not null
                              child 1, value: int32
                          child 3, Ratio: struct<present: bool not null, value: double> not null
                              child 0, present: bool not null
                              child 1, value: double
                      child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
                          child 0, A: float not null
                          child 1, B: struct<present: bool not null, value: float> not null
                              child 0, present: bool not null
                              child 1, value: float
                      child 7, binary: binary
          child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
              child 0, Id: int32 not null
              child 1, Flag: struct<present: bool not null, value: bool> not null
                  child 0, present: bool not null
                  child 1, value: bool
              child 2, Count: struct<present: bool not null, value: int32> not null
                  child 0, present: bool not null
                  child 1, value: int32
              child 3, Ratio: struct<present: bool not null, value: double> not null
                  child 0, present: bool not null
                  child 1, value: double
          child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
              child 0, A: float not null
              child 1, B: struct<present: bool not null, value: float> not null
                  child 0, present: bool not null
                  child 1, value: float
          child 7, binary: binary
  child 65, array_ExtensionObject: list<item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint (... 2009 chars omitted)
      child 0, item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 1997 chars omitted)
          child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
              child 0, namespace: uint16 not null
              child 1, id_type: uint8 not null
              child 2, numeric: uint32
              child 3, string: string
              child 4, guid: fixed_size_binary[16]
              child 5, opaque: binary
          child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 1817 chars omitted) not null
              child 0, null: null
              child 1, Point: struct<X: double not null, Y: double not null>
                  child 0, X: double not null
                  child 1, Y: double not null
              child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
                  child 0, Name: string
                  child 1, Age: int32 not null
                  child 2, Email: struct<present: bool not null, value: string> not null
                      child 0, present: bool not null
                      child 1, value: string
                  child 3, Nickname: struct<present: bool not null, value: string> not null
                      child 0, present: bool not null
                      child 1, value: string
              child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
                  child 0, null: null
                  child 1, AsInt: struct<value: int32>
                      child 0, value: int32
                  child 2, AsText: struct<value: string>
                      child 0, value: string
                  child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
                      child 0, value: struct<X: double not null, Y: double not null>
                          child 0, X: double not null
                          child 1, Y: double not null
              child 4, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string (... 1009 chars omitted)
                  child 0, Id: string
                  child 1, Location: struct<X: double not null, Y: double not null>
                      child 0, X: double not null
                      child 1, Y: double not null
                  child 2, Tags: list<item: string>
                      child 0, item: string
                  child 3, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 896 chars omitted)
                      child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
                          child 0, namespace: uint16 not null
                          child 1, id_type: uint8 not null
                          child 2, numeric: uint32
                          child 3, string: string
                          child 4, guid: fixed_size_binary[16]
                          child 5, opaque: binary
                      child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 716 chars omitted) not null
                          child 0, null: null
                          child 1, Point: struct<X: double not null, Y: double not null>
                              child 0, X: double not null
                              child 1, Y: double not null
                          child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
                              child 0, Name: string
                              child 1, Age: int32 not null
                              child 2, Email: struct<present: bool not null, value: string> not null
                                  child 0, present: bool not null
                                  child 1, value: string
                              child 3, Nickname: struct<present: bool not null, value: string> not null
                                  child 0, present: bool not null
                                  child 1, value: string
                          child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
                              child 0, null: null
                              child 1, AsInt: struct<value: int32>
                                  child 0, value: int32
                              child 2, AsText: struct<value: string>
                                  child 0, value: string
                              child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
                                  child 0, value: struct<X: double not null, Y: double not null>
                                      child 0, X: double not null
                                      child 1, Y: double not null
                          child 4, Envelope: struct<>
                          child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
                              child 0, Id: int32 not null
                              child 1, Flag: struct<present: bool not null, value: bool> not null
                                  child 0, present: bool not null
                                  child 1, value: bool
                              child 2, Count: struct<present: bool not null, value: int32> not null
                                  child 0, present: bool not null
                                  child 1, value: int32
                              child 3, Ratio: struct<present: bool not null, value: double> not null
                                  child 0, present: bool not null
                                  child 1, value: double
                          child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
                              child 0, A: float not null
                              child 1, B: struct<present: bool not null, value: float> not null
                                  child 0, present: bool not null
                                  child 1, value: float
                          child 7, binary: binary
              child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
                  child 0, Id: int32 not null
                  child 1, Flag: struct<present: bool not null, value: bool> not null
                      child 0, present: bool not null
                      child 1, value: bool
                  child 2, Count: struct<present: bool not null, value: int32> not null
                      child 0, present: bool not null
                      child 1, value: int32
                  child 3, Ratio: struct<present: bool not null, value: double> not null
                      child 0, present: bool not null
                      child 1, value: double
              child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
                  child 0, A: float not null
                  child 1, B: struct<present: bool not null, value: float> not null
                      child 0, present: bool not null
                      child 1, value: float
              child 7, binary: binary
  child 66, matrix_ExtensionObject: struct<dimensions: list<item: int32> not null, values: list<item: struct<type_id: struct<namespace:  (... 2074 chars omitted)
      child 0, dimensions: list<item: int32> not null
          child 0, item: int32
      child 1, values: list<item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint (... 2009 chars omitted) not null
          child 0, item: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 1997 chars omitted)
              child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
                  child 0, namespace: uint16 not null
                  child 1, id_type: uint8 not null
                  child 2, numeric: uint32
                  child 3, string: string
                  child 4, guid: fixed_size_binary[16]
                  child 5, opaque: binary
              child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 1817 chars omitted) not null
                  child 0, null: null
                  child 1, Point: struct<X: double not null, Y: double not null>
                      child 0, X: double not null
                      child 1, Y: double not null
                  child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
                      child 0, Name: string
                      child 1, Age: int32 not null
                      child 2, Email: struct<present: bool not null, value: string> not null
                          child 0, present: bool not null
                          child 1, value: string
                      child 3, Nickname: struct<present: bool not null, value: string> not null
                          child 0, present: bool not null
                          child 1, value: string
                  child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
                      child 0, null: null
                      child 1, AsInt: struct<value: int32>
                          child 0, value: int32
                      child 2, AsText: struct<value: string>
                          child 0, value: string
                      child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
                          child 0, value: struct<X: double not null, Y: double not null>
                              child 0, X: double not null
                              child 1, Y: double not null
                  child 4, Envelope: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string (... 1009 chars omitted)
                      child 0, Id: string
                      child 1, Location: struct<X: double not null, Y: double not null>
                          child 0, X: double not null
                          child 1, Y: double not null
                      child 2, Tags: list<item: string>
                          child 0, item: string
                      child 3, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 896 chars omitted)
                          child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
                              child 0, namespace: uint16 not null
                              child 1, id_type: uint8 not null
                              child 2, numeric: uint32
                              child 3, string: string
                              child 4, guid: fixed_size_binary[16]
                              child 5, opaque: binary
                          child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 716 chars omitted) not null
                              child 0, null: null
                              child 1, Point: struct<X: double not null, Y: double not null>
                                  child 0, X: double not null
                                  child 1, Y: double not null
                              child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
                                  child 0, Name: string
                                  child 1, Age: int32 not null
                                  child 2, Email: struct<present: bool not null, value: string> not null
                                      child 0, present: bool not null
                                      child 1, value: string
                                  child 3, Nickname: struct<present: bool not null, value: string> not null
                                      child 0, present: bool not null
                                      child 1, value: string
                              child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
                                  child 0, null: null
                                  child 1, AsInt: struct<value: int32>
                                      child 0, value: int32
                                  child 2, AsText: struct<value: string>
                                      child 0, value: string
                                  child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
                                      child 0, value: struct<X: double not null, Y: double not null>
                                          child 0, X: double not null
                                          child 1, Y: double not null
                              child 4, Envelope: struct<>
                              child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
                                  child 0, Id: int32 not null
                                  child 1, Flag: struct<present: bool not null, value: bool> not null
                                      child 0, present: bool not null
                                      child 1, value: bool
                                  child 2, Count: struct<present: bool not null, value: int32> not null
                                      child 0, present: bool not null
                                      child 1, value: int32
                                  child 3, Ratio: struct<present: bool not null, value: double> not null
                                      child 0, present: bool not null
                                      child 1, value: double
                              child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
                                  child 0, A: float not null
                                  child 1, B: struct<present: bool not null, value: float> not null
                                      child 0, present: bool not null
                                      child 1, value: float
                              child 7, binary: binary
                  child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
                      child 0, Id: int32 not null
                      child 1, Flag: struct<present: bool not null, value: bool> not null
                          child 0, present: bool not null
                          child 1, value: bool
                      child 2, Count: struct<present: bool not null, value: int32> not null
                          child 0, present: bool not null
                          child 1, value: int32
                      child 3, Ratio: struct<present: bool not null, value: double> not null
                          child 0, present: bool not null
                          child 1, value: double
                  child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
                      child 0, A: float not null
                      child 1, B: struct<present: bool not null, value: float> not null
                          child 0, present: bool not null
                          child 1, value: float
                  child 7, binary: binary
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
Variant(vtype=Builtin(id=<BuiltInType.Int32: 6>), value=99, dimensions=None)
```

### Built-in DiagnosticInfo

Published schema source: `schemas\base.json builtins`. SchemaId: `f771456f4d1d0ab7`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `struct<symbolic_id: int32, namespace_uri: int32, locale: int32, localized_text: int32, additional_info: string, inner_status_code: uint32, inner_diagnostic_info: list<item: struct<symbolic_id: int32, namespace_uri: int32, locale: int32, localized_text: int32, additional_info: string, inner_status_code: uint32> not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.symbolic_id` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.namespace_uri` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.locale` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.localized_text` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.additional_info` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.inner_status_code` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.inner_diagnostic_info` | `list<item: struct<symbolic_id: int32, namespace_uri: int32, locale: int32, localized_text: int32, additional_info: string, inner_status_code: uint32> not null>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.inner_diagnostic_info[]` | `struct<symbolic_id: int32, namespace_uri: int32, locale: int32, localized_text: int32, additional_info: string, inner_status_code: uint32>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.inner_diagnostic_info[].symbolic_id` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.inner_diagnostic_info[].namespace_uri` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.inner_diagnostic_info[].locale` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.inner_diagnostic_info[].localized_text` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.inner_diagnostic_info[].additional_info` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.inner_diagnostic_info[].inner_status_code` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: struct<symbolic_id: int32, namespace_uri: int32, locale: int32, localized_text: int32, additional_in (... 222 chars omitted)
  child 0, symbolic_id: int32
  child 1, namespace_uri: int32
  child 2, locale: int32
  child 3, localized_text: int32
  child 4, additional_info: string
  child 5, inner_status_code: uint32
  child 6, inner_diagnostic_info: list<item: struct<symbolic_id: int32, namespace_uri: int32, locale: int32, localized_text: int32, ad (... 59 chars omitted)
      child 0, item: struct<symbolic_id: int32, namespace_uri: int32, locale: int32, localized_text: int32, additional_in (... 38 chars omitted) not null
          child 0, symbolic_id: int32
          child 1, namespace_uri: int32
          child 2, locale: int32
          child 3, localized_text: int32
          child 4, additional_info: string
          child 5, inner_status_code: uint32
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
DiagnosticInfo(symbolic_id=1,
               namespace_uri=2,
               locale=None,
               localized_text=None,
               additional_info='outer',
               inner_status_code=StatusCode(value=2158755840),
               inner_diagnostic_info=DiagnosticInfo(symbolic_id=None,
                                                    namespace_uri=None,
                                                    locale=5,
                                                    localized_text=None,
                                                    additional_info='inner',
                                                    inner_status_code=None,
                                                    inner_diagnostic_info=None))
```

### Composite Array<String>

Published schema source: `schemas\base.json corpusTypes`. SchemaId: `29fbb0deb2fca279`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `list<item: string>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value[]` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: list<item: string>
  child 0, item: string
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
['a', None, '']
```

### Composite Matrix<Double>

Published schema source: `schemas\base.json matrix/corpusTypes`. SchemaId: `80fc271958993aff`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `struct<dimensions: list<item: int32> not null, values: list<item: double> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.dimensions` | `list<item: int32>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.dimensions[]` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.values` | `list<item: double>` | not nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.values[]` | `double` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: struct<dimensions: list<item: int32> not null, values: list<item: double> not null>
  child 0, dimensions: list<item: int32> not null
      child 0, item: int32
  child 1, values: list<item: double> not null
      child 0, item: double
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
Matrix(dimensions=(2, 2), values=[1.0, nan, -inf, -0.0])
```

### Composite plain Structure Point

Published schema source: `../extras/arrow-encoding/schemas/struct-Point.json`. SchemaId: `beb88baa5c498682`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: struct<X: double not null, Y: double not null>
  child 0, X: double not null
  child 1, Y: double not null
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
StructValue(fields={'X': 1.25, 'Y': -3.5}, type_name='Point')
```

### Composite StructureWithOptionalFields Person

Published schema source: `../extras/arrow-encoding/schemas/struct-Person.json`. SchemaId: `38e92bc671144ea6`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Name` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Age` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Email` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.Email.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Email.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Nickname` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.Nickname.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Nickname.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
  child 0, Name: string
  child 1, Age: int32 not null
  child 2, Email: struct<present: bool not null, value: string> not null
      child 0, present: bool not null
      child 1, value: string
  child 3, Nickname: struct<present: bool not null, value: string> not null
      child 0, present: bool not null
      child 1, value: string
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
StructValue(fields={'Name': 'Zed', 'Age': 9, 'Email': None}, type_name='Person')
```

### Composite dense Union Measurement

Published schema source: `../extras/arrow-encoding/schemas/struct-Measurement.json`. SchemaId: `916f95c2e1d7e908`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>` | nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.AsInt` | `struct<value: int32>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.AsInt.value` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.AsText` | `struct<value: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.AsText.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.AsPoint` | `struct<value: struct<X: double not null, Y: double not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.AsPoint.value` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.AsPoint.value.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.AsPoint.value.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
  child 0, null: null
  child 1, AsInt: struct<value: int32>
      child 0, value: int32
  child 2, AsText: struct<value: string>
      child 0, value: string
  child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
      child 0, value: struct<X: double not null, Y: double not null>
          child 0, X: double not null
          child 1, Y: double not null
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
UnionValue(field_name='AsText', value=None)
```

### Worked structured DataType Envelope

Published schema source: `../extras/arrow-encoding/schemas/struct-Envelope.json`. SchemaId: `306f13a2fa40fc28`.

| Field | Arrow DataType | Nullable/validity | Notes |
|---|---|---|---|
| `value` | `struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string>, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Id` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Location` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Location.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Location.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Tags` | `list<item: string>` | nullable; Arrow validity bitmap when needed | List offsets identify the element range; null list differs from empty list. |
| `value.Tags[]` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload` | `struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary> not null, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.type_id` | `struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: fixed_size_binary[16], opaque: binary>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.type_id.namespace` | `uint16` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.type_id.id_type` | `uint8` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.type_id.numeric` | `uint32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.type_id.string` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.type_id.guid` | `fixed_size_binary[16]` | nullable; Arrow validity bitmap when needed | Fixed-width bytes. |
| `value.Payload.type_id.opaque` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body` | `dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>=2, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>=3, Envelope: struct<>=4, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>=5, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>=6, binary: binary=7>` | not nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.Payload.body.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Point` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Point.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Point.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Person` | `struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not null, Nickname: struct<present: bool not null, value: string> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Person.Name` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Person.Age` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Person.Email` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.Payload.body.Person.Email.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Person.Email.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Person.Nickname` | `struct<present: bool not null, value: string>` | not nullable; Arrow validity bitmap when needed | `present` distinguishes absent optional fields from present null values. |
| `value.Payload.body.Person.Nickname.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Person.Nickname.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Measurement` | `dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: struct<value: struct<X: double not null, Y: double not null>>=3>` | nullable; Arrow validity bitmap when needed | Dense-union type id plus value offset selects the active branch. |
| `value.Payload.body.Measurement.null` | `null` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Measurement.AsInt` | `struct<value: int32>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Measurement.AsInt.value` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Measurement.AsText` | `struct<value: string>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Measurement.AsText.value` | `string` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Measurement.AsPoint` | `struct<value: struct<X: double not null, Y: double not null>>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Measurement.AsPoint.value` | `struct<X: double not null, Y: double not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Measurement.AsPoint.value.X` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Measurement.AsPoint.value.Y` | `double` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.Envelope` | `struct<>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.OptionalScalars` | `struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct<present: bool not null, value: int32> not null, Ratio: struct<present: bool not null, value: double> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.OptionalScalars.Id` | `int32` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.OptionalScalars.Flag` | `struct<present: bool not null, value: bool>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.OptionalScalars.Flag.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.OptionalScalars.Flag.value` | `bool` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.OptionalScalars.Count` | `struct<present: bool not null, value: int32>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.OptionalScalars.Count.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.OptionalScalars.Count.value` | `int32` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.OptionalScalars.Ratio` | `struct<present: bool not null, value: double>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.OptionalScalars.Ratio.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.OptionalScalars.Ratio.value` | `double` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.FloatHolder` | `struct<A: float not null, B: struct<present: bool not null, value: float> not null>` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.FloatHolder.A` | `float` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.FloatHolder.B` | `struct<present: bool not null, value: float>` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.FloatHolder.B.present` | `bool` | not nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.FloatHolder.B.value` | `float` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |
| `value.Payload.body.binary` | `binary` | nullable; Arrow validity bitmap when needed | Canonical Part 6 Arrow mapping. |

Arrow schema:

```text
value: struct<Id: string, Location: struct<X: double not null, Y: double not null>, Tags: list<item: string (... 1009 chars omitted)
  child 0, Id: string
  child 1, Location: struct<X: double not null, Y: double not null>
      child 0, X: double not null
      child 1, Y: double not null
  child 2, Tags: list<item: string>
      child 0, item: string
  child 3, Payload: struct<type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: (... 896 chars omitted)
      child 0, type_id: struct<namespace: uint16 not null, id_type: uint8 not null, numeric: uint32, string: string, guid: f (... 37 chars omitted) not null
          child 0, namespace: uint16 not null
          child 1, id_type: uint8 not null
          child 2, numeric: uint32
          child 3, string: string
          child 4, guid: fixed_size_binary[16]
          child 5, opaque: binary
      child 1, body: dense_union<null: null=0, Point: struct<X: double not null, Y: double not null>=1, Person: struct<Na (... 716 chars omitted) not null
          child 0, null: null
          child 1, Point: struct<X: double not null, Y: double not null>
              child 0, X: double not null
              child 1, Y: double not null
          child 2, Person: struct<Name: string, Age: int32 not null, Email: struct<present: bool not null, value: string> not n (... 70 chars omitted)
              child 0, Name: string
              child 1, Age: int32 not null
              child 2, Email: struct<present: bool not null, value: string> not null
                  child 0, present: bool not null
                  child 1, value: string
              child 3, Nickname: struct<present: bool not null, value: string> not null
                  child 0, present: bool not null
                  child 1, value: string
          child 3, Measurement: dense_union<null: null=0, AsInt: struct<value: int32>=1, AsText: struct<value: string>=2, AsPoint: s (... 63 chars omitted)
              child 0, null: null
              child 1, AsInt: struct<value: int32>
                  child 0, value: int32
              child 2, AsText: struct<value: string>
                  child 0, value: string
              child 3, AsPoint: struct<value: struct<X: double not null, Y: double not null>>
                  child 0, value: struct<X: double not null, Y: double not null>
                      child 0, X: double not null
                      child 1, Y: double not null
          child 4, Envelope: struct<>
          child 5, OptionalScalars: struct<Id: int32 not null, Flag: struct<present: bool not null, value: bool> not null, Count: struct (... 111 chars omitted)
              child 0, Id: int32 not null
              child 1, Flag: struct<present: bool not null, value: bool> not null
                  child 0, present: bool not null
                  child 1, value: bool
              child 2, Count: struct<present: bool not null, value: int32> not null
                  child 0, present: bool not null
                  child 1, value: int32
              child 3, Ratio: struct<present: bool not null, value: double> not null
                  child 0, present: bool not null
                  child 1, value: double
          child 6, FloatHolder: struct<A: float not null, B: struct<present: bool not null, value: float> not null>
              child 0, A: float not null
              child 1, B: struct<present: bool not null, value: float> not null
                  child 0, present: bool not null
                  child 1, value: float
          child 7, binary: binary
-- schema metadata --
opcua-arrow: '1'
```

Example value:

```text
StructValue(fields={'Id': 'E1',
                    'Location': StructValue(fields={'X': 0.0, 'Y': 0.0},
                                            type_name='Point'),
                    'Payload': ExtensionObject(type_id=NodeId(namespace=0,
                                                              id_type=<IdType.NUMERIC: 0>,
                                                              identifier=3001),
                                               body=StructValue(fields={'X': 2.0,
                                                                        'Y': 3.0},
                                                                type_name='Point')),
                    'Tags': ['x', None, 'z']},
            type_name='Envelope')
```
<!-- END GENERATED: type-reference -->
