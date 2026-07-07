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
| Canonical form | The serialized, normalized transitive `FileDescriptorSet` for the generated per-type or service schema, and the only permitted wire representation for a given OPC UA value and declared type. |
| SchemaId | The first 8 bytes of SHA-256 over the canonical form, rendered as lowercase hex when textual. |

Key words **shall**, **should**, **may**, **shall not** are to be interpreted as in ISO/IEC directives.

## 4 Overview

The Protobuf DataEncoding is schema driven. A generator reads OPC UA DataTypeDefinition metadata from a NodeSet and emits one proto3 message per structured DataType and one enum or OptionSet message per enumeration DataType. Field numbers are stable and are assigned from DataTypeDefinition field order starting at 1. Built-in and envelope messages are defined once in `opcua_builtins.proto` and imported by generated namespace schemas. A receiver may compile the `.proto`, load a self-describing `FileDescriptorSet`, or re-derive the same schema from the AddressSpace.

The transport content type for complete Protobuf encoded OPC UA values should be `application/vnd.google.protobuf`; the OPC UA gRPC TransportProtocol defined in clause 7 uses `application/grpc+proto` for service calls. Profiles or transports that require a schema identifier shall carry the SchemaId, Protobuf package name, message name and OPC UA DataType/Encoding NodeId in their service contract, call metadata or a catalog record. There is no PubSub schema announcement for this DataEncoding.

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

The generated per-type byte examples and SchemaIds are listed in [Annex A](#annex-a--generated-protobuf-type-reference).

### 5.6.3 Enumerations and OptionSets

Enumerations shall encode as signed `int32` values or generated proto enum symbols with the same numeric values. Decoders shall preserve unknown numeric values when the OPC UA DataType permits forward-compatible enumeration extension. OptionSets shall encode as an unsigned integer message (`uint32` for 32-bit OptionSets and `uint64` for wider OptionSets) carrying the exact bit mask; symbolic decomposition is non-normative.

### 5.6.4 Structures, optional fields and unions

A Structure DataType shall map to its generated proto3 `message`; that per-type message is the canonical wire form and reflective name/value envelopes are not an alternate encoding. Non-optional fields use stable field numbers derived from DataTypeDefinition field order. OPC UA optional nullable fields shall use an optional nullable wrapper (for example `optional StringValue`) so that absent is distinct from present-null and present-empty. A Union DataType shall map to a proto3 `oneof`; nullable built-in branches use nullable wrappers so a selected null branch is distinct from a null union. A null union is represented by no selected `oneof` arm.

### 5.6.5 Arrays, matrices and nullability

A one-dimensional OPC UA array shall map to `repeated` values. A null array is represented by absence of the containing array message, while an empty array is a present message with zero elements. Proto3 `repeated` fields cannot contain nulls; therefore this encoding uses one canonical nullable-element wrapper strategy. If the element type is nullable, each element shall be encoded as a wrapper message with explicit presence (for the reference schema this is `Value`); an empty wrapper is a null element. If the element type is not nullable, producers should use a plain `repeated` scalar or message field.

A Matrix shall be encoded as `message Matrix<T> { repeated int32 dimensions = 1; repeated <Elem> values = 2; }` where values are row-major and `<Elem>` is the nullable wrapper when the element type is nullable. The number of values shall equal the product of all dimensions. Dimensions are signed Int32 values as in OPC UA.

### 5.6.6 Variant

A Variant shall contain an optional OPC UA BuiltInType numeric id and exactly one payload: scalar, array or matrix. The empty Variant message is the null Variant. Scalar payloads use the built-in mapping in 5.6.2. Array and matrix payloads use the nullability rules in 5.6.5. A Variant shall not directly contain a nested Variant, DataValue or DiagnosticInfo body. The built-in body kinds are a finite, complete set carried dynamically by the `built_in_type` id and the generic `Value` payload; unlike the Avro and Arrow body unions they are not narrowed or aggregated. Where a Variant body is an ExtensionObject, the reachable concrete Structure types are aggregated as for ExtensionObject (5.6.7).

### 5.6.7 ExtensionObject and abstract-subtyped fields

An ExtensionObject shall carry the concrete TypeId or DataTypeEncoding NodeId and a `oneof` body. If the type is known, the body shall be the generated message for the concrete Structure DataType, carried as a typed `Any` in the reference schema. If the type is unknown and the receiver supports opaque forwarding, the body may be opaque bytes; otherwise decoding shall fail. Fields declared as abstract or allowing subtypes shall be encoded in the same way as an ExtensionObject so that the concrete schema is resolved from the inline type id. The concrete body is carried in a stable `google.protobuf.Any message_body` field (with an opaque `bytes` alternative); aggregating a new concrete type per the Schema Registry (see *OPC UA — Schema Registry* §5.6) adds that type to the descriptor closure of `Any`-resolvable types and does not change any wire field number. Where an abstract-or-subtyped field is instead generated as a `oneof` over concrete messages, that `oneof`'s field numbers are the append-only ordinals. Opaque bytes continue to carry any concrete type not yet resolvable.

### 5.6.8 DataValue and DiagnosticInfo

A DataValue shall be a message whose Value, StatusCode, SourceTimestamp, SourcePicoseconds, ServerTimestamp and ServerPicoseconds members are independently present or absent. A present StatusCode with value `0` is distinct from absent StatusCode. DiagnosticInfo shall be recursive and shall preserve the presence of each index member, AdditionalInfo, InnerStatusCode and InnerDiagnosticInfo.

### 5.6.9 Schema-generation algorithm

For a declared OPC UA DataType `T`, producers and consumers shall use the same deterministic generation function:

1. Read `T` and, for Structure and Union DataTypes, its `DataTypeDefinition` Attribute. Resolve field names, field DataTypes, optional flags and subtype/abstract flags from the AddressSpace.
2. Select the canonical proto3 package for the namespace and a stable message name derived from the DataType BrowseName. Built-in envelope messages are imported from `opcua_builtins.proto`.
3. Assign field numbers in exact `DataTypeDefinition` field order starting at 1. Numbers shall not be re-used for reordered or deleted fields; any changed definition produces a different schema and SchemaId.
4. Map built-in fields using Table 5.6.2. Nullable built-ins use wrapper messages (`StringValue`, `ByteStringValue`, `XmlElementValue`, etc.) when null must be distinct from empty/default.
5. Map arrays to a containing array message with `repeated Value` element wrappers when null elements are allowed; an absent containing message is a null array and a present empty message is an empty array.
6. Map matrices to `MatrixValue { repeated int32 dimensions = 1; repeated Value values = 2; }`, using row-major values and the same nullable element wrappers.
7. Map Structures to proto3 `message`; optional OPC UA fields use explicit proto3 presence where scalar default values would otherwise collapse.
8. Map Unions, Variants and abstract/subtyped fields to `oneof` choices. No selected arm represents a null union/variant/abstract value; a selected nullable wrapper may itself hold null.
9. Emit the normalized transitive `FileDescriptorSet`: the target `FileDescriptorProto` plus every imported file needed for dynamic decoding, recursively, with deterministic file names, packages, imports, options, messages, enums and fields; no source-code-location data; and a stable dependency-first file order with dependencies sorted by file name.

The canonical form is the deterministic serialization of this normalized transitive `FileDescriptorSet`. The Protobuf SchemaId shall be `sha256_id_hex(canonical_form, 8)`, i.e. the first 8 bytes of SHA-256 over the canonical bytes rendered as lowercase hexadecimal. SchemaId identifies the complete descriptor closure for the value schema or service contract, not a service request handle, Session, SecureChannel token or individual value.

### 5.6.10 Decoder algorithm

A decoder shall first resolve the schema for the declared type and SchemaId, then parse the Protobuf wire bytes using that schema. In an OPC UA gRPC service call, the schema is the service `.proto` or its equivalent transitive `FileDescriptorSet`; the SchemaId is resolved from the shared service contract or from the xRegistry catalog record selected by call metadata:

* **Schema-driven decoding.** If the concrete `.proto` is pre-compiled, the decoder instantiates the generated per-type message and decodes the body. If it receives a self-describing `FileDescriptorSet`, it shall load the descriptors into a dynamic descriptor pool, find the carried package/message name, construct the dynamic message class, and parse the body. Dynamic decoding shall produce the same canonical value as static per-type decoding.
* **Catalog-driven decoding.** If no descriptor is pre-compiled, the decoder may retrieve the service `.proto` or `FileDescriptorSet` from the xRegistry catalog by SchemaId. The retrieved descriptor closure shall hash to the advertised SchemaId before any request or response body is decoded.
* **AddressSpace-driven decoding.** If no descriptor is pre-compiled or registered in the catalog, the decoder may read the DataType's `DataTypeDefinition` from the AddressSpace and re-run the schema-generation algorithm above. The resulting canonical transitive `FileDescriptorSet` and SchemaId shall match the sender's for the same DataType definition and imports.

After parsing, the decoder applies the OPC UA type rules: integer range checks, matrix value-count checks, null-versus-empty preservation, union single-arm validation, ExtensionObject type resolution and canonical equality of value semantics. Unknown fields may be preserved by a forwarding implementation but shall not change the decoded OPC UA value.

## 6 Insertion into OPC 10000-6 v1.05.07

Insert a new clause **5.6 OPC UA Protobuf** after **5.4 OPC UA JSON** and the sibling **5.5 OPC UA Avro** addition, and before clause 6. The child clauses shall parallel the JSON mapping: **5.6.1 General**, **5.6.2 Built-in DataTypes**, **5.6.3 Enumerations and OptionSets**, **5.6.4 Structures**, **5.6.5 Arrays and matrices**, **5.6.6 Variant**, **5.6.7 ExtensionObject**, **5.6.8 DataValue**, and **5.6.9 DiagnosticInfo**. Add `Default Protobuf` to DataTypeEncoding discussions wherever `Default Binary`, `Default XML` and `Default JSON` are listed. Add `application/vnd.google.protobuf` and compatibility alias `application/x-protobuf` to content-type guidance for Protobuf encoded bodies.

## Annex A — Generated Protobuf type reference

<!-- BEGIN GENERATED: type-reference -->

This annex is generated by `../extras/protobuf-encoding/tools/gen_type_reference.py`; edit the generator, not this block.

### Built-in Boolean

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `boolean_value` | `bool` in `Value.kind` | selected `oneof` arm | BuiltInType `1`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    bool boolean_value = 1;
  }
}
```

Example corpus case: `bool_true`

```text
True
```

Encoded bytes: `0801`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `08` | boolean_value: tag field=1 wire=0 |
| 1 | 1 | `01` | boolean_value: varint value |

### Built-in SByte

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `sbyte_value` | `int32` in `Value.kind` | selected `oneof` arm | BuiltInType `2`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    int32 sbyte_value = 2;
  }
}
```

Example corpus case: `sbyte_min`

```text
-128
```

Encoded bytes: `1080ffffffffffffffff01`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `10` | sbyte_value: tag field=2 wire=0 |
| 1 | 10 | `80 ff ff ff ff ff ff ff ff 01` | sbyte_value: varint value |

### Built-in Byte

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `byte_value` | `uint32` in `Value.kind` | selected `oneof` arm | BuiltInType `3`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    uint32 byte_value = 3;
  }
}
```

Example corpus case: `byte_max`

```text
255
```

Encoded bytes: `18ff01`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `18` | byte_value: tag field=3 wire=0 |
| 1 | 2 | `ff 01` | byte_value: varint value |

### Built-in Int16

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `int16_value` | `int32` in `Value.kind` | selected `oneof` arm | BuiltInType `4`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    int32 int16_value = 4;
  }
}
```

Example corpus case: `int16_min`

```text
-32768
```

Encoded bytes: `208080feffffffffffff01`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `20` | int16_value: tag field=4 wire=0 |
| 1 | 10 | `80 80 fe ff ff ff ff ff ff 01` | int16_value: varint value |

### Built-in UInt16

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `uint16_value` | `uint32` in `Value.kind` | selected `oneof` arm | BuiltInType `5`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    uint32 uint16_value = 5;
  }
}
```

Example corpus case: `uint16_max`

```text
65535
```

Encoded bytes: `28ffff03`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `28` | uint16_value: tag field=5 wire=0 |
| 1 | 3 | `ff ff 03` | uint16_value: varint value |

### Built-in Int32

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `int32_value` | `int32` in `Value.kind` | selected `oneof` arm | BuiltInType `6`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    int32 int32_value = 6;
  }
}
```

Example corpus case: `int32_min`

```text
-2147483648
```

Encoded bytes: `3080808080f8ffffffff01`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `30` | int32_value: tag field=6 wire=0 |
| 1 | 10 | `80 80 80 80 f8 ff ff ff ff 01` | int32_value: varint value |

### Built-in UInt32

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `uint32_value` | `uint32` in `Value.kind` | selected `oneof` arm | BuiltInType `7`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    uint32 uint32_value = 7;
  }
}
```

Example corpus case: `uint32_max`

```text
4294967295
```

Encoded bytes: `38ffffffff0f`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `38` | uint32_value: tag field=7 wire=0 |
| 1 | 5 | `ff ff ff ff 0f` | uint32_value: varint value |

### Built-in Int64

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `int64_value` | `int64` in `Value.kind` | selected `oneof` arm | BuiltInType `8`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    int64 int64_value = 8;
  }
}
```

Example corpus case: `int64_min`

```text
-9223372036854775808
```

Encoded bytes: `4080808080808080808001`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `40` | int64_value: tag field=8 wire=0 |
| 1 | 10 | `80 80 80 80 80 80 80 80 80 01` | int64_value: varint value |

### Built-in UInt64

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `uint64_value` | `uint64` in `Value.kind` | selected `oneof` arm | BuiltInType `9`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    uint64 uint64_value = 9;
  }
}
```

Example corpus case: `uint64_max`

```text
18446744073709551615
```

Encoded bytes: `48ffffffffffffffffff01`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `48` | uint64_value: tag field=9 wire=0 |
| 1 | 10 | `ff ff ff ff ff ff ff ff ff 01` | uint64_value: varint value |

### Built-in Float

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `float_value` | `float` in `Value.kind` | selected `oneof` arm | BuiltInType `10`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    float float_value = 10;
  }
}
```

Example corpus case: `float_normal`

```text
1.5
```

Encoded bytes: `550000c03f`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `55` | float_value: tag field=10 wire=5 |
| 1 | 4 | `00 00 c0 3f` | float_value: 32-bit value |

### Built-in Double

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `double_value` | `double` in `Value.kind` | selected `oneof` arm | BuiltInType `11`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    double double_value = 11;
  }
}
```

Example corpus case: `double_tiny`

```text
5e-324
```

Encoded bytes: `590100000000000000`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `59` | double_value: tag field=11 wire=1 |
| 1 | 8 | `01 00 00 00 00 00 00 00` | double_value: 64-bit value |

### Built-in String

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `string_value` | `string` in `Value.kind` | selected `oneof` arm | BuiltInType `12`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    string string_value = 12;
  }
}
```

Example corpus case: `string_unicode`

```text
'grüße-中文-😀'
```

Encoded bytes: `62136772c3bcc39f652de4b8ade696872df09f9880`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `62` | string_value: tag field=12 wire=2 |
| 1 | 1 | `13` | string_value: length=19 |
| 2 | 19 | `67 72 c3 bc c3 9f 65 2d e4 b8 ad e6 96 87 2d f0 … (+3 B)` | string_value: payload |

### Built-in DateTime

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `datetime_value` | `sfixed64` in `Value.kind` | selected `oneof` arm | BuiltInType `13`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    sfixed64 datetime_value = 13;
  }
}
```

Example corpus case: `datetime_now`

```text
DateTime(ticks=133000000000000000)
```

Encoded bytes: `690080209bcb82d801`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `69` | datetime_value: tag field=13 wire=1 |
| 1 | 8 | `00 80 20 9b cb 82 d8 01` | datetime_value: 64-bit value |

### Built-in Guid

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `guid_value` | `bytes` in `Value.kind` | selected `oneof` arm | BuiltInType `14`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    bytes guid_value = 14;
  }
}
```

Example corpus case: `guid`

```text
Guid(bytes=b'\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10')
```

Encoded bytes: `72100102030405060708090a0b0c0d0e0f10`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `72` | guid_value: tag field=14 wire=2 |
| 1 | 1 | `10` | guid_value: length=16 |
| 2 | 16 | `01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f 10` | guid_value: payload |

### Built-in ByteString

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `bytestring_value` | `bytes` in `Value.kind` | selected `oneof` arm | BuiltInType `15`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    bytes bytestring_value = 15;
  }
}
```

Example corpus case: `bytestring`

```text
b'\x00\x01\x02\x03\x04\x05\x06\x07'
```

Encoded bytes: `7a080001020304050607`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `7a` | bytestring_value: tag field=15 wire=2 |
| 1 | 1 | `08` | bytestring_value: length=8 |
| 2 | 8 | `00 01 02 03 04 05 06 07` | bytestring_value: payload |

### Built-in XmlElement

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `xml_element_value` | `opcua.protobuf.v1.XmlElementValue` in `Value.kind` | selected `oneof` arm | BuiltInType `16`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    opcua.protobuf.v1.XmlElementValue xml_element_value = 16;
  }
}
```

Example corpus case: `xml`

```text
XmlElement(value="<a x='1'>t</a>")
```

Encoded bytes: `8201100a0e3c6120783d2731273e743c2f613e`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 2 | `82 01` | xml_element_value: tag field=16 wire=2 |
| 2 | 1 | `10` | xml_element_value: length=16 |
| 3 | 1 | `0a` | xml_element_value.value: tag field=1 wire=2 |
| 4 | 1 | `0e` | xml_element_value.value: length=14 |
| 5 | 14 | `3c 61 20 78 3d 27 31 27 3e 74 3c 2f 61 3e` | xml_element_value.value: payload |

### Built-in NodeId

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `node_id_value` | `opcua.protobuf.v1.NodeId` in `Value.kind` | selected `oneof` arm | BuiltInType `17`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    opcua.protobuf.v1.NodeId node_id_value = 17;
  }
}
```

Example corpus case: `nodeid_guid`

```text
NodeId(namespace=3, id_type=<IdType.GUID: 2>, identifier=Guid(bytes=b'\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10\x11\x12\x13\x14\x15\x16'))
```

Encoded bytes: `8a0116080310022a100708090a0b0c0d0e0f10111213141516`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 2 | `8a 01` | node_id_value: tag field=17 wire=2 |
| 2 | 1 | `16` | node_id_value: length=22 |
| 3 | 1 | `08` | node_id_value.namespace: tag field=1 wire=0 |
| 4 | 1 | `03` | node_id_value.namespace: varint value |
| 5 | 1 | `10` | node_id_value.id_type: tag field=2 wire=0 |
| 6 | 1 | `02` | node_id_value.id_type: varint value |
| 7 | 1 | `2a` | node_id_value.guid: tag field=5 wire=2 |
| 8 | 1 | `10` | node_id_value.guid: length=16 |
| 9 | 16 | `07 08 09 0a 0b 0c 0d 0e 0f 10 11 12 13 14 15 16` | node_id_value.guid: payload |

### Built-in ExpandedNodeId

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `expanded_node_id_value` | `opcua.protobuf.v1.ExpandedNodeId` in `Value.kind` | selected `oneof` arm | BuiltInType `18`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    opcua.protobuf.v1.ExpandedNodeId expanded_node_id_value = 18;
  }
}
```

Example corpus case: `expnodeid_full`

```text
ExpandedNodeId(node_id=NodeId(namespace=1, id_type=<IdType.STRING: 1>, identifier='X'), namespace_uri='http://example.org/UA/', server_index=5)
```

Encoded bytes: `9201230a07080110012201581216687474703a2f2f6578616d706c652e6f72672f55412f1805`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 2 | `92 01` | expanded_node_id_value: tag field=18 wire=2 |
| 2 | 1 | `23` | expanded_node_id_value: length=35 |
| 3 | 1 | `0a` | expanded_node_id_value.node_id: tag field=1 wire=2 |
| 4 | 1 | `07` | expanded_node_id_value.node_id: length=7 |
| 5 | 1 | `08` | expanded_node_id_value.node_id.namespace: tag field=1 wire=0 |
| 6 | 1 | `01` | expanded_node_id_value.node_id.namespace: varint value |
| 7 | 1 | `10` | expanded_node_id_value.node_id.id_type: tag field=2 wire=0 |
| 8 | 1 | `01` | expanded_node_id_value.node_id.id_type: varint value |
| 9 | 1 | `22` | expanded_node_id_value.node_id.string: tag field=4 wire=2 |
| 10 | 1 | `01` | expanded_node_id_value.node_id.string: length=1 |
| 11 | 1 | `58` | expanded_node_id_value.node_id.string: payload |
| 12 | 1 | `12` | expanded_node_id_value.namespace_uri: tag field=2 wire=2 |
| 13 | 1 | `16` | expanded_node_id_value.namespace_uri: length=22 |
| 14 | 22 | `68 74 74 70 3a 2f 2f 65 78 61 6d 70 6c 65 2e 6f … (+6 B)` | expanded_node_id_value.namespace_uri: payload |
| 36 | 1 | `18` | expanded_node_id_value.server_index: tag field=3 wire=0 |
| 37 | 1 | `05` | expanded_node_id_value.server_index: varint value |

### Built-in StatusCode

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `status_code_value` | `fixed32` in `Value.kind` | selected `oneof` arm | BuiltInType `19`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    fixed32 status_code_value = 19;
  }
}
```

Example corpus case: `status_bad`

```text
StatusCode(value=2158755840)
```

Encoded bytes: `9d010000ac80`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 2 | `9d 01` | status_code_value: tag field=19 wire=5 |
| 2 | 4 | `00 00 ac 80` | status_code_value: 32-bit value |

### Built-in QualifiedName

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `qualified_name_value` | `opcua.protobuf.v1.QualifiedName` in `Value.kind` | selected `oneof` arm | BuiltInType `20`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    opcua.protobuf.v1.QualifiedName qualified_name_value = 20;
  }
}
```

Example corpus case: `qname`

```text
QualifiedName(namespace=1, name='Temp')
```

Encoded bytes: `a201080801120454656d70`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 2 | `a2 01` | qualified_name_value: tag field=20 wire=2 |
| 2 | 1 | `08` | qualified_name_value: length=8 |
| 3 | 1 | `08` | qualified_name_value.namespace: tag field=1 wire=0 |
| 4 | 1 | `01` | qualified_name_value.namespace: varint value |
| 5 | 1 | `12` | qualified_name_value.name: tag field=2 wire=2 |
| 6 | 1 | `04` | qualified_name_value.name: length=4 |
| 7 | 4 | `54 65 6d 70` | qualified_name_value.name: payload |

### Built-in LocalizedText

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `localized_text_value` | `opcua.protobuf.v1.LocalizedText` in `Value.kind` | selected `oneof` arm | BuiltInType `21`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    opcua.protobuf.v1.LocalizedText localized_text_value = 21;
  }
}
```

Example corpus case: `ltext_full`

```text
LocalizedText(locale='en', text='Hello')
```

Encoded bytes: `aa010b0a02656e120548656c6c6f`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 2 | `aa 01` | localized_text_value: tag field=21 wire=2 |
| 2 | 1 | `0b` | localized_text_value: length=11 |
| 3 | 1 | `0a` | localized_text_value.locale: tag field=1 wire=2 |
| 4 | 1 | `02` | localized_text_value.locale: length=2 |
| 5 | 2 | `65 6e` | localized_text_value.locale: payload |
| 7 | 1 | `12` | localized_text_value.text: tag field=2 wire=2 |
| 8 | 1 | `05` | localized_text_value.text: length=5 |
| 9 | 5 | `48 65 6c 6c 6f` | localized_text_value.text: payload |

### Built-in ExtensionObject

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `extension_object_value` | `opcua.protobuf.v1.ExtensionObject` in `Value.kind` | selected `oneof` arm | BuiltInType `22`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    opcua.protobuf.v1.ExtensionObject extension_object_value = 22;
  }
}
```

Example corpus case: `extobj_point`

```text
ExtensionObject(type_id=NodeId(namespace=0, id_type=<IdType.NUMERIC: 0>, identifier=3001), body=StructValue(fields={'X': 1.0, 'Y': 1.0}, type_name='Point'))
```

Encoded bytes: `b2014f0a0318b91712480a32747970652e676f6f676c65617069732e636f6d2f6f706375612e70726f746f6275662e67656e6572617465642e506f696e74121209000000000000f03f11000000000000f03f`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 2 | `b2 01` | extension_object_value: tag field=22 wire=2 |
| 2 | 1 | `4f` | extension_object_value: length=79 |
| 3 | 1 | `0a` | extension_object_value.type_id: tag field=1 wire=2 |
| 4 | 1 | `03` | extension_object_value.type_id: length=3 |
| 5 | 1 | `18` | extension_object_value.type_id.numeric: tag field=3 wire=0 |
| 6 | 2 | `b9 17` | extension_object_value.type_id.numeric: varint value |
| 8 | 1 | `12` | extension_object_value.message_body: tag field=2 wire=2 |
| 9 | 1 | `48` | extension_object_value.message_body: length=72 |
| 10 | 1 | `0a` | extension_object_value.message_body.type_url: tag field=1 wire=2 |
| 11 | 1 | `32` | extension_object_value.message_body.type_url: length=50 |
| 12 | 50 | `74 79 70 65 2e 67 6f 6f 67 6c 65 61 70 69 73 2e … (+34 B)` | extension_object_value.message_body.type_url: payload |
| 62 | 1 | `12` | extension_object_value.message_body.value: tag field=2 wire=2 |
| 63 | 1 | `12` | extension_object_value.message_body.value: length=18 |
| 64 | 18 | `09 00 00 00 00 00 00 f0 3f 11 00 00 00 00 00 00 … (+2 B)` | extension_object_value.message_body.value: payload |

### Built-in DataValue

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `data_value` | `opcua.protobuf.v1.DataValue` in `Value.kind` | selected `oneof` arm | BuiltInType `23`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    opcua.protobuf.v1.DataValue data_value = 23;
  }
}
```

Example corpus case: `datavalue_full`

```text
DataValue(value=Variant(vtype=Builtin(id=<BuiltInType.Int32: 6>), value=42, dimensions=None), status=StatusCode(value=0), source_timestamp=DateTime(ticks=1000), source_picoseconds=500, server_timestamp=DateTime(ticks=2000), server_picoseconds=250)
```

Encoded bytes: `ba01250a0608061202302a150000000019e80300000000000020f40329d00700000000000030fa01`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 2 | `ba 01` | data_value: tag field=23 wire=2 |
| 2 | 1 | `25` | data_value: length=37 |
| 3 | 1 | `0a` | data_value.value: tag field=1 wire=2 |
| 4 | 1 | `06` | data_value.value: length=6 |
| 5 | 1 | `08` | data_value.value.built_in_type: tag field=1 wire=0 |
| 6 | 1 | `06` | data_value.value.built_in_type: varint value |
| 7 | 1 | `12` | data_value.value.scalar: tag field=2 wire=2 |
| 8 | 1 | `02` | data_value.value.scalar: length=2 |
| 9 | 1 | `30` | data_value.value.scalar.int32_value: tag field=6 wire=0 |
| 10 | 1 | `2a` | data_value.value.scalar.int32_value: varint value |
| 11 | 1 | `15` | data_value.status: tag field=2 wire=5 |
| 12 | 4 | `00 00 00 00` | data_value.status: 32-bit value |
| 16 | 1 | `19` | data_value.source_timestamp: tag field=3 wire=1 |
| 17 | 8 | `e8 03 00 00 00 00 00 00` | data_value.source_timestamp: 64-bit value |
| 25 | 1 | `20` | data_value.source_picoseconds: tag field=4 wire=0 |
| 26 | 2 | `f4 03` | data_value.source_picoseconds: varint value |
| 28 | 1 | `29` | data_value.server_timestamp: tag field=5 wire=1 |
| 29 | 8 | `d0 07 00 00 00 00 00 00` | data_value.server_timestamp: 64-bit value |
| 37 | 1 | `30` | data_value.server_picoseconds: tag field=6 wire=0 |
| 38 | 2 | `fa 01` | data_value.server_picoseconds: varint value |

### Built-in Variant

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `variant_value` | `opcua.protobuf.v1.Variant` in `Value.kind` | selected `oneof` arm | BuiltInType `24`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    opcua.protobuf.v1.Variant variant_value = 24;
  }
}
```

Example corpus case: `variant_matrix_int`

```text
Variant(vtype=Builtin(id=<BuiltInType.Int32: 6>), value=[1, 2, 3, 4], dimensions=(2, 2))
```

Encoded bytes: `c20118080622140a02020212023001120230021202300312023004`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 2 | `c2 01` | variant_value: tag field=24 wire=2 |
| 2 | 1 | `18` | variant_value: length=24 |
| 3 | 1 | `08` | variant_value.built_in_type: tag field=1 wire=0 |
| 4 | 1 | `06` | variant_value.built_in_type: varint value |
| 5 | 1 | `22` | variant_value.matrix: tag field=4 wire=2 |
| 6 | 1 | `14` | variant_value.matrix: length=20 |
| 7 | 1 | `0a` | variant_value.matrix.dimensions: tag field=1 wire=2 |
| 8 | 1 | `02` | variant_value.matrix.dimensions: length=2 |
| 9 | 2 | `02 02` | variant_value.matrix.dimensions: payload |
| 11 | 1 | `12` | variant_value.matrix.values: tag field=2 wire=2 |
| 12 | 1 | `02` | variant_value.matrix.values: length=2 |
| 13 | 1 | `30` | variant_value.matrix.values.int32_value: tag field=6 wire=0 |
| 14 | 1 | `01` | variant_value.matrix.values.int32_value: varint value |
| 15 | 1 | `12` | variant_value.matrix.values: tag field=2 wire=2 |
| 16 | 1 | `02` | variant_value.matrix.values: length=2 |
| 17 | 1 | `30` | variant_value.matrix.values.int32_value: tag field=6 wire=0 |
| 18 | 1 | `02` | variant_value.matrix.values.int32_value: varint value |
| 19 | 1 | `12` | variant_value.matrix.values: tag field=2 wire=2 |
| 20 | 1 | `02` | variant_value.matrix.values: length=2 |
| 21 | 1 | `30` | variant_value.matrix.values.int32_value: tag field=6 wire=0 |
| 22 | 1 | `03` | variant_value.matrix.values.int32_value: varint value |
| 23 | 1 | `12` | variant_value.matrix.values: tag field=2 wire=2 |
| 24 | 1 | `02` | variant_value.matrix.values: length=2 |
| 25 | 1 | `30` | variant_value.matrix.values.int32_value: tag field=6 wire=0 |
| 26 | 1 | `04` | variant_value.matrix.values.int32_value: varint value |

### Built-in DiagnosticInfo

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `diagnostic_info_value` | `opcua.protobuf.v1.DiagnosticInfo` in `Value.kind` | selected `oneof` arm | BuiltInType `25`. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message Value {
  oneof kind {
    opcua.protobuf.v1.DiagnosticInfo diagnostic_info_value = 25;
  }
}
```

Example corpus case: `diaginfo_nested`

```text
DiagnosticInfo(symbolic_id=1, namespace_uri=2, locale=None, localized_text=None, additional_info='outer', inner_status_code=StatusCode(value=2158755840), inner_diagnostic_info=DiagnosticInfo(symbolic_id=None, namespace_uri=None, locale=5, localized_text=None, additional_info='inner', inner_status_code=None, inner_diagnostic_info=None))
```

Encoded bytes: `ca011b080110022a056f75746572350000ac803a0918052a05696e6e6572`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 2 | `ca 01` | diagnostic_info_value: tag field=25 wire=2 |
| 2 | 1 | `1b` | diagnostic_info_value: length=27 |
| 3 | 1 | `08` | diagnostic_info_value.symbolic_id: tag field=1 wire=0 |
| 4 | 1 | `01` | diagnostic_info_value.symbolic_id: varint value |
| 5 | 1 | `10` | diagnostic_info_value.namespace_uri: tag field=2 wire=0 |
| 6 | 1 | `02` | diagnostic_info_value.namespace_uri: varint value |
| 7 | 1 | `2a` | diagnostic_info_value.additional_info: tag field=5 wire=2 |
| 8 | 1 | `05` | diagnostic_info_value.additional_info: length=5 |
| 9 | 5 | `6f 75 74 65 72` | diagnostic_info_value.additional_info: payload |
| 14 | 1 | `35` | diagnostic_info_value.inner_status_code: tag field=6 wire=5 |
| 15 | 4 | `00 00 ac 80` | diagnostic_info_value.inner_status_code: 32-bit value |
| 19 | 1 | `3a` | diagnostic_info_value.inner_diagnostic_info: tag field=7 wire=2 |
| 20 | 1 | `09` | diagnostic_info_value.inner_diagnostic_info: length=9 |
| 21 | 1 | `18` | diagnostic_info_value.inner_diagnostic_info.locale: tag field=3 wire=0 |
| 22 | 1 | `05` | diagnostic_info_value.inner_diagnostic_info.locale: varint value |
| 23 | 1 | `2a` | diagnostic_info_value.inner_diagnostic_info.additional_info: tag field=5 wire=2 |
| 24 | 1 | `05` | diagnostic_info_value.inner_diagnostic_info.additional_info: length=5 |
| 25 | 5 | `69 6e 6e 65 72` | diagnostic_info_value.inner_diagnostic_info.additional_info: payload |

### Array with nullable elements

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `array_value.values` | `repeated Value` | containing `Value.kind`; each element wrapper present | Empty element wrapper is a null element. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message ArrayValue {
  repeated Value values = 1;
}
```

Example corpus case: `array_string_with_nulls`

```text
['a', None, '']
```

Encoded bytes: `d2010b0a036201610a000a026200`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 2 | `d2 01` | array_value: tag field=26 wire=2 |
| 2 | 1 | `0b` | array_value: length=11 |
| 3 | 1 | `0a` | array_value.values: tag field=1 wire=2 |
| 4 | 1 | `03` | array_value.values: length=3 |
| 5 | 1 | `62` | array_value.values.string_value: tag field=12 wire=2 |
| 6 | 1 | `01` | array_value.values.string_value: length=1 |
| 7 | 1 | `61` | array_value.values.string_value: payload |
| 8 | 1 | `0a` | array_value.values: tag field=1 wire=2 |
| 9 | 1 | `00` | array_value.values: length=0 |
| 10 | 0 | `—` | array_value.values: payload |
| 10 | 1 | `0a` | array_value.values: tag field=1 wire=2 |
| 11 | 1 | `02` | array_value.values: length=2 |
| 12 | 1 | `62` | array_value.values.string_value: tag field=12 wire=2 |
| 13 | 1 | `00` | array_value.values.string_value: length=0 |
| 14 | 0 | `—` | array_value.values.string_value: payload |

### Matrix

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `matrix_value.dimensions` | `repeated int32` | present matrix | Row-major dimensions. |
| `matrix_value.values` | `repeated Value` | present matrix | Count shall equal product of dimensions. |

SchemaId: `7fc4be352f884550`

Schema file: [`opcua_builtins.proto`](schemas/opcua_builtins.proto)

```proto
message MatrixValue {
  repeated int32 dimensions = 1;
  repeated Value values = 2;
}
```

Example corpus case: `matrix_double_2x2_special`

```text
Matrix(dimensions=(2, 2), values=[1.0, nan, -inf, -0.0])
```

Encoded bytes: `da01300a020202120959000000000000f03f120959000000000000f87f120959000000000000f0ff1209590000000000000080`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 2 | `da 01` | matrix_value: tag field=27 wire=2 |
| 2 | 1 | `30` | matrix_value: length=48 |
| 3 | 1 | `0a` | matrix_value.dimensions: tag field=1 wire=2 |
| 4 | 1 | `02` | matrix_value.dimensions: length=2 |
| 5 | 2 | `02 02` | matrix_value.dimensions: payload |
| 7 | 1 | `12` | matrix_value.values: tag field=2 wire=2 |
| 8 | 1 | `09` | matrix_value.values: length=9 |
| 9 | 1 | `59` | matrix_value.values.double_value: tag field=11 wire=1 |
| 10 | 8 | `00 00 00 00 00 00 f0 3f` | matrix_value.values.double_value: 64-bit value |
| 18 | 1 | `12` | matrix_value.values: tag field=2 wire=2 |
| 19 | 1 | `09` | matrix_value.values: length=9 |
| 20 | 1 | `59` | matrix_value.values.double_value: tag field=11 wire=1 |
| 21 | 8 | `00 00 00 00 00 00 f8 7f` | matrix_value.values.double_value: 64-bit value |
| 29 | 1 | `12` | matrix_value.values: tag field=2 wire=2 |
| 30 | 1 | `09` | matrix_value.values: length=9 |
| 31 | 1 | `59` | matrix_value.values.double_value: tag field=11 wire=1 |
| 32 | 8 | `00 00 00 00 00 00 f0 ff` | matrix_value.values.double_value: 64-bit value |
| 40 | 1 | `12` | matrix_value.values: tag field=2 wire=2 |
| 41 | 1 | `09` | matrix_value.values: length=9 |
| 42 | 1 | `59` | matrix_value.values.double_value: tag field=11 wire=1 |
| 43 | 8 | `00 00 00 00 00 00 00 80` | matrix_value.values.double_value: 64-bit value |

### Structure

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `x` | `Double` = 1 | present for mandatory fields | DataTypeDefinition field `X`. |
| `y` | `Double` = 2 | present for mandatory fields | DataTypeDefinition field `Y`. |

SchemaId: `7d8f4f0cab37e77f`

Schema file: [`point.proto`](../extras/protobuf-encoding/schemas/point.proto)

```proto
// Generated by tools/build_schemas.py. Do not edit.
syntax = "proto3";

package opcua.protobuf.generated;

import "opcua_builtins.proto";

option java_multiple_files = true;

message Point {
  double x = 1;
  double y = 2;
}
```

Example corpus case: `struct_point`

```text
StructValue(fields={'X': 1.25, 'Y': -3.5}, type_name='Point')
```

Encoded bytes: `09000000000000f43f110000000000000cc0`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `09` | x: tag field=1 wire=1 |
| 1 | 8 | `00 00 00 00 00 00 f4 3f` | x: 64-bit value |
| 9 | 1 | `11` | y: tag field=2 wire=1 |
| 10 | 8 | `00 00 00 00 00 00 0c c0` | y: 64-bit value |

### Structure with optional fields

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `name` | `String` = 1 | present for mandatory fields | DataTypeDefinition field `Name`. |
| `age` | `Int32` = 2 | present for mandatory fields | DataTypeDefinition field `Age`. |
| `email` | `String` = 3 | optional | DataTypeDefinition field `Email`. |
| `nickname` | `String` = 4 | optional | DataTypeDefinition field `Nickname`. |

SchemaId: `1d957f6758d8d1a5`

Schema file: [`person.proto`](../extras/protobuf-encoding/schemas/person.proto)

```proto
// Generated by tools/build_schemas.py. Do not edit.
syntax = "proto3";

package opcua.protobuf.generated;

import "opcua_builtins.proto";

option java_multiple_files = true;

message Person {
  opcua.protobuf.v1.StringValue name = 1;
  int32 age = 2;
  optional opcua.protobuf.v1.StringValue email = 3;
  optional opcua.protobuf.v1.StringValue nickname = 4;
}
```

Example corpus case: `struct_person_one_opt`

```text
StructValue(fields={'Name': 'Cy', 'Age': 5, 'Email': 'c@x'}, type_name='Person')
```

Encoded bytes: `0a040a02437910051a050a03634078`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `0a` | name: tag field=1 wire=2 |
| 1 | 1 | `04` | name: length=4 |
| 2 | 1 | `0a` | name.value: tag field=1 wire=2 |
| 3 | 1 | `02` | name.value: length=2 |
| 4 | 2 | `43 79` | name.value: payload |
| 6 | 1 | `10` | age: tag field=2 wire=0 |
| 7 | 1 | `05` | age: varint value |
| 8 | 1 | `1a` | email: tag field=3 wire=2 |
| 9 | 1 | `05` | email: length=5 |
| 10 | 1 | `0a` | email.value: tag field=1 wire=2 |
| 11 | 1 | `03` | email.value: length=3 |
| 12 | 3 | `63 40 78` | email.value: payload |

### Optional scalar presence

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `id` | `Int32` = 1 | present for mandatory fields | DataTypeDefinition field `Id`. |
| `flag` | `Boolean` = 2 | optional | DataTypeDefinition field `Flag`. |
| `count` | `Int32` = 3 | optional | DataTypeDefinition field `Count`. |
| `ratio` | `Double` = 4 | optional | DataTypeDefinition field `Ratio`. |

SchemaId: `3bf5d258c6e0aa53`

Schema file: [`optionalscalars.proto`](../extras/protobuf-encoding/schemas/optionalscalars.proto)

```proto
// Generated by tools/build_schemas.py. Do not edit.
syntax = "proto3";

package opcua.protobuf.generated;

import "opcua_builtins.proto";

option java_multiple_files = true;

message OptionalScalars {
  int32 id = 1;
  optional bool flag = 2;
  optional int32 count = 3;
  optional double ratio = 4;
}
```

Example corpus case: `optscalars_zero_present`

```text
StructValue(fields={'Id': 7, 'Flag': False, 'Count': 0, 'Ratio': 0.0}, type_name='OptionalScalars')
```

Encoded bytes: `080710001800210000000000000000`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `08` | id: tag field=1 wire=0 |
| 1 | 1 | `07` | id: varint value |
| 2 | 1 | `10` | flag: tag field=2 wire=0 |
| 3 | 1 | `00` | flag: varint value |
| 4 | 1 | `18` | count: tag field=3 wire=0 |
| 5 | 1 | `00` | count: varint value |
| 6 | 1 | `21` | ratio: tag field=4 wire=1 |
| 7 | 8 | `00 00 00 00 00 00 00 00` | ratio: 64-bit value |

### Optional Float presence

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `a` | `Float` = 1 | present for mandatory fields | DataTypeDefinition field `A`. |
| `b` | `Float` = 2 | optional | DataTypeDefinition field `B`. |

SchemaId: `1ffe9d3b330d2ba8`

Schema file: [`floatholder.proto`](../extras/protobuf-encoding/schemas/floatholder.proto)

```proto
// Generated by tools/build_schemas.py. Do not edit.
syntax = "proto3";

package opcua.protobuf.generated;

import "opcua_builtins.proto";

option java_multiple_files = true;

message FloatHolder {
  float a = 1;
  optional float b = 2;
}
```

Example corpus case: `floatholder_full`

```text
StructValue(fields={'A': -0.25, 'B': 0.5}, type_name='FloatHolder')
```

Encoded bytes: `0d000080be150000003f`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `0d` | a: tag field=1 wire=5 |
| 1 | 4 | `00 00 80 be` | a: 32-bit value |
| 5 | 1 | `15` | b: tag field=2 wire=5 |
| 6 | 4 | `00 00 00 3f` | b: 32-bit value |

### Union oneof

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `value` | `oneof` | zero or one selected arm | Field numbers follow DataTypeDefinition order. |
| `as_int` | `Int32` = 1 | oneof arm | DataTypeDefinition field `AsInt`. |
| `as_text` | `String` = 2 | oneof arm | DataTypeDefinition field `AsText`. |
| `as_point` | `Point` = 3 | oneof arm | DataTypeDefinition field `AsPoint`. |

SchemaId: `2eec643ca40196f0`

Schema file: [`measurement.proto`](../extras/protobuf-encoding/schemas/measurement.proto)

```proto
// Generated by tools/build_schemas.py. Do not edit.
syntax = "proto3";

package opcua.protobuf.generated;

import "opcua_builtins.proto";
import "point.proto";

option java_multiple_files = true;

message Measurement {
  oneof value {
    int32 as_int = 1;
    opcua.protobuf.v1.StringValue as_text = 2;
    opcua.protobuf.generated.Point as_point = 3;
  }
}
```

Example corpus case: `union_point`

```text
UnionValue(field_name='AsPoint', value=StructValue(fields={'X': 9.0, 'Y': 8.0}, type_name='Point'))
```

Encoded bytes: `1a12090000000000002240110000000000002040`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `1a` | as_point: tag field=3 wire=2 |
| 1 | 1 | `12` | as_point: length=18 |
| 2 | 1 | `09` | as_point.x: tag field=1 wire=1 |
| 3 | 8 | `00 00 00 00 00 00 22 40` | as_point.x: 64-bit value |
| 11 | 1 | `11` | as_point.y: tag field=2 wire=1 |
| 12 | 8 | `00 00 00 00 00 00 20 40` | as_point.y: 64-bit value |

### Worked structured DataType: Envelope

| Field | proto3 type/label | Presence | Notes |
|---|---|---|---|
| `id` | `String` = 1 | present for mandatory fields | DataTypeDefinition field `Id`. |
| `location` | `Point` = 2 | present for mandatory fields | DataTypeDefinition field `Location`. |
| `tags` | `Array<String>` = 3 | present for mandatory fields | DataTypeDefinition field `Tags`. |
| `payload` | `ExtensionObject` = 4 | present for mandatory fields | DataTypeDefinition field `Payload`. |

SchemaId: `30bfcd3d6d9f9b43`

Schema file: [`envelope.proto`](../extras/protobuf-encoding/schemas/envelope.proto)

```proto
// Generated by tools/build_schemas.py. Do not edit.
syntax = "proto3";

package opcua.protobuf.generated;

import "opcua_builtins.proto";
import "point.proto";

option java_multiple_files = true;

message Envelope {
  opcua.protobuf.v1.StringValue id = 1;
  opcua.protobuf.generated.Point location = 2;
  opcua.protobuf.v1.ArrayValue tags = 3;
  opcua.protobuf.v1.ExtensionObject payload = 4;
}
```

Example corpus case: `envelope`

```text
StructValue(fields={'Id': 'E1', 'Location': StructValue(fields={'X': 0.0, 'Y': 0.0}, type_name='Point'), 'Tags': ['x', None, 'z'], 'Payload': ExtensionObject(type_id=NodeId(namespace=0, id_type=<IdType.NUMERIC: 0>, identifier=3001), body=StructValue(fields={'X': 2.0, 'Y': 3.0}, type_name='Point'))}, type_name='Envelope')
```

Encoded bytes: `0a040a02453112001a0c0a036201780a000a0362017a224f0a0318b91712480a32747970652e676f6f676c65617069732e636f6d2f6f706375612e70726f746f6275662e67656e6572617465642e506f696e741212090000000000000040110000000000000840`

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `0a` | id: tag field=1 wire=2 |
| 1 | 1 | `04` | id: length=4 |
| 2 | 1 | `0a` | id.value: tag field=1 wire=2 |
| 3 | 1 | `02` | id.value: length=2 |
| 4 | 2 | `45 31` | id.value: payload |
| 6 | 1 | `12` | location: tag field=2 wire=2 |
| 7 | 1 | `00` | location: length=0 |
| 8 | 0 | `—` | location: payload |
| 8 | 1 | `1a` | tags: tag field=3 wire=2 |
| 9 | 1 | `0c` | tags: length=12 |
| 10 | 1 | `0a` | tags.values: tag field=1 wire=2 |
| 11 | 1 | `03` | tags.values: length=3 |
| 12 | 1 | `62` | tags.values.string_value: tag field=12 wire=2 |
| 13 | 1 | `01` | tags.values.string_value: length=1 |
| 14 | 1 | `78` | tags.values.string_value: payload |
| 15 | 1 | `0a` | tags.values: tag field=1 wire=2 |
| 16 | 1 | `00` | tags.values: length=0 |
| 17 | 0 | `—` | tags.values: payload |
| 17 | 1 | `0a` | tags.values: tag field=1 wire=2 |
| 18 | 1 | `03` | tags.values: length=3 |
| 19 | 1 | `62` | tags.values.string_value: tag field=12 wire=2 |
| 20 | 1 | `01` | tags.values.string_value: length=1 |
| 21 | 1 | `7a` | tags.values.string_value: payload |
| 22 | 1 | `22` | payload: tag field=4 wire=2 |
| 23 | 1 | `4f` | payload: length=79 |
| 24 | 1 | `0a` | payload.type_id: tag field=1 wire=2 |
| 25 | 1 | `03` | payload.type_id: length=3 |
| 26 | 1 | `18` | payload.type_id.numeric: tag field=3 wire=0 |
| 27 | 2 | `b9 17` | payload.type_id.numeric: varint value |
| 29 | 1 | `12` | payload.message_body: tag field=2 wire=2 |
| 30 | 1 | `48` | payload.message_body: length=72 |
| 31 | 1 | `0a` | payload.message_body.type_url: tag field=1 wire=2 |
| 32 | 1 | `32` | payload.message_body.type_url: length=50 |
| 33 | 50 | `74 79 70 65 2e 67 6f 6f 67 6c 65 61 70 69 73 2e … (+34 B)` | payload.message_body.type_url: payload |
| 83 | 1 | `12` | payload.message_body.value: tag field=2 wire=2 |
| 84 | 1 | `12` | payload.message_body.value: length=18 |
| 85 | 18 | `09 00 00 00 00 00 00 00 40 11 00 00 00 00 00 00 … (+2 B)` | payload.message_body.value: payload |

<!-- END GENERATED: type-reference -->
