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

Each OPC UA DataType maps to exactly one Avro schema. Primitive built-ins use Avro primitives where the Avro type can carry the complete OPC UA domain; composite built-ins use Avro records; nullable OPC UA values use Avro unions with `"null"` as the first branch. Avro schema names are stable qualified names under the namespace `org.opcfoundation.ua.avro` unless a companion or vendor namespace is mapped to a more specific Avro namespace by configuration. Annex A gives generated per-type examples and byte layouts.

The content type for a standalone Avro payload using this DataEncoding shall be `application/vnd.apache.avro`. Where a transport distinguishes container files from schemaless Avro binary payloads it may use the parameter `encoding=binary` or `container=object-container-file`; PubSub messages defined by the companion Part 14 mapping use schemaless Avro binary with schema resolution from configuration or registry.

A DataTypeEncoding Object named **Default Avro** would be added for DataTypes that support this encoding. The Object would be linked from the DataType with `HasEncoding` in the same pattern as `Default Binary`, `Default XML` and `Default JSON`. This working draft intentionally describes that node only and does not assign or ship NodeIds.

## 5 Avro mapping

### 5.1 General rules

Avro records preserve OPC UA field order as defined by the DataTypeDefinition. Record field names shall be the OPC UA field names converted to legal Avro names by replacing non-name characters with `_` and prefixing `_` if required. The published `.avsc` schema documents are the canonical wire contract; encoders and decoders shall use those schemas directly and shall not substitute implementation-specific alternate branches or abbreviated records. See Annex A for the generated reference schemas, example values and annotated bytes for each built-in and composite category.

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

Variant shall be a record carrying `builtInType`, nullable `dimensions`, and `body`. A null Variant has `builtInType = 0`, `dimensions = null`, and `body = null`. A scalar body uses one record-wrapped Avro union branch for the selected built-in body type. A one-dimensional array body uses the corresponding `Array` wrapper. A matrix body uses the corresponding Matrix wrapper and sets `dimensions`. The `body` union excludes nested Variant, DataValue and DiagnosticInfo. Its member set is the set of body types the Variant may carry: a self-describing encoding may include the full set of built-in body types (including ExtensionObject), whereas a schema-governed encoding may narrow the union to the aggregated set for the field and grow it across MinorVersions under the append-only rule of the Schema Registry (see *OPC UA — Schema Registry* §5.6), so an existing branch keeps its Avro union branch index in every later minor of the same major. The branch wrappers and the `builtInType` field are both present so decoders can disambiguate Avro unions and recover the exact OPC UA type.

### 5.9 ExtensionObject and abstract or subtyped fields

ExtensionObject shall be a record `{ "typeId": NodeId, "body": ["null", <known-struct-records...>, "bytes"] }`. The `typeId` shall identify the concrete DataType or DataTypeEncoding NodeId. If the concrete structured DataType is known to the decoder, the body shall use that record branch. If the type is unknown but the sender has an opaque encoded representation, the body may use the `bytes` branch and the receiver shall preserve the bytes with the TypeId. Fields declared as abstract structures or fields that allow subtypes shall use the same representation so the concrete runtime type is carried inline. The `known-struct` branches are the aggregated concrete-type set for the field per the Schema Registry (see *OPC UA — Schema Registry* §5.6): generated from the subtype hierarchy where bounded, or grown append-only across MinorVersions as new concrete types are encoded, with an existing branch keeping its Avro union branch index. Under aggregation the `bytes` fallback branch is reserved ahead of the appended known-struct branches so its ordinal is stable; it continues to carry any concrete type not yet aggregated.

### 5.10 DataValue

DataValue shall be an Avro record with fields `value`, `status`, `sourceTimestamp`, `sourcePicoseconds`, `serverTimestamp`, and `serverPicoseconds`, each nullable and defaulting to null. The `value` field is a nullable Variant. StatusCode uses the UInt32-as-signed-int rule. Timestamps use raw DateTime ticks. Picoseconds use Avro `int` and retain the OPC UA UInt16 domain.

### 5.11 DiagnosticInfo

DiagnosticInfo shall be an Avro record with nullable fields `symbolicId`, `namespaceUri`, `locale`, `localizedText`, `additionalInfo`, `innerStatusCode`, and `innerDiagnosticInfo`. `innerDiagnosticInfo` is a recursive reference to DiagnosticInfo. Null means the corresponding mask bit is not present; zero is a present numeric value and shall not be treated as absent.

## 6 Deterministic schema generation and SchemaId

### 6.1 Inputs

An encoder shall derive the Avro schema from the OPC UA DataTypeDefinition of the value's declared DataType. For Variant values and for fields declared as abstract or allowing subtypes, the encoder shall also use the concrete runtime built-in type or concrete structured DataType of the value. A decoder that re-derives a schema shall use the same inputs: the DataTypeDefinition read from the AddressSpace and, where present, the inline Variant built-in type or ExtensionObject TypeId.

### 6.2 Generation algorithm

The schema generator shall apply the following deterministic algorithm.

1. Resolve the DataTypeDefinition and all recursively referenced DataTypes. Built-in DataTypes use the mappings in §5.2. Enumerations and OptionSets use the numeric representation in §5.3.
2. Assign Avro names by converting OPC UA DataType and field names to legal Avro names: replace each character outside `[A-Za-z0-9_]` with `_`; if the first character is not `[A-Za-z_]`, prefix `T_`. Names in the base namespace use Avro namespace `org.opcfoundation.ua.avro`.
3. Emit record fields in exactly the DataTypeDefinition field order. The generator shall not sort fields, omit disabled optional fields from the schema, or reorder union branches for local convenience.
4. For nullable values, emit an Avro union ordered as `["null", T]` and set the default to `null` where Avro requires a default. Mandatory nullable fields remain mandatory record fields whose value type is nullable.
5. For StructureWithOptionalFields, emit one nullable wrapper record per optional field, named `<Structure>_<Field>_Optional`, with a single `value` field. The wrapper null means absent; a non-null wrapper whose value is null means present-null.
6. For Union DataTypes, emit a record with `switch` and `value`. The `value` union starts with null and then one single-field branch record for each union field in DataTypeDefinition order.
7. For arrays, emit an Avro array whose item schema is nullable only when the element type can carry null. For matrices, emit a record with `dimensions` as an array of Avro `int` and `values` as the row-major Avro array of elements.
8. For Variant, abstract fields, and fields allowing subtypes, carry the runtime type inline: Variant carries `builtInType`, dimensions and one record-wrapped body branch; abstract or subtyped structured values use ExtensionObject TypeId and the concrete body branch. The same runtime type information is used by encoder and decoder to choose the schema branch.
9. Before computing a SchemaId or announcing a schema, make the schema self-contained: inline every referenced named type at its first occurrence, using the recursively resolved definitions from step 1; for recursive or repeated named types, use Avro named references after the first definition.

The canonical form used for SchemaId shall be the Apache Avro Parsing Canonical Form of that self-contained schema. The **SchemaId** shall be the CRC-64-AVRO Rabin fingerprint of the Parsing Canonical Form bytes, represented as the 8 fingerprint bytes in little-endian hexadecimal. This is the same byte order used by Avro single-object encoding (`0xC3 0x01` followed by the 8-byte little-endian Rabin fingerprint).

### 6.3 SchemaId use

A producer shall recompute the SchemaId from the self-contained canonical schema before writing a value or message. Two schemas with different field order, optional-field wrappers, union branch order, runtime Variant body type, matrix record shape, or referenced concrete structured DataType definition shall have different SchemaIds. A consumer shall treat the SchemaId as identifying the exact self-contained Avro Parsing Canonical Form, not merely a DataType NodeId or a PubSub ConfigurationVersion.

## 7 Decoder schema resolution

A decoder shall use one of the following schema resolution paths.

**Schema-driven path.** If the decoder already has a schema for the SchemaId, from a local cache, announcement, schema registry or configured catalog, it shall parse that schema and decode the Avro binary payload directly. If the payload uses Avro single-object encoding, the decoder shall verify the two magic bytes and the embedded little-endian Rabin fingerprint before decoding the body.

**AddressSpace-driven path.** If the decoder does not have a schema body but can read the DataType from the server, it shall read the DataTypeDefinition and recursively referenced definitions from the AddressSpace and run the same schema-generation function defined in §6. For Variant and abstract/subtyped fields, it shall use the inline built-in type, dimensions and TypeId carried in the value to select the same concrete branch as the encoder. The re-derived self-contained Parsing Canonical Form shall produce the same SchemaId. When this check fails, the value shall not be decoded with the mismatched schema.

The encoder and decoder therefore run the same deterministic generation function. When both sides already have the relevant DataTypeDefinitions, schema bodies need not be transferred for every value; the SchemaId is sufficient to verify that both sides selected the same schema.

## 8 Insertion into OPC 10000-6 v1.05.07

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
| §6-§7 Schema generation, SchemaId and decoding | `5.5.x Schema resolution` | Defines Parsing Canonical Form, CRC-64-AVRO SchemaId, schema-driven decoding and AddressSpace-driven re-derivation. |

Conformance text should require that senders and receivers claiming Default Avro support use the canonical schema generated from the DataTypeDefinition and reject non-canonical alternate encodings where a reversible decode cannot be guaranteed.

## 9 Appendix B PubSub Action and Discovery schema examples

The Part 14 Avro mapping publishes compact envelope schemas for Action and Discovery messages in `../extras/avro-encoding/schemas/`. The Action request/response envelopes are `AvroActionRequestNetworkMessage.avsc` and `AvroActionResponseNetworkMessage.avsc`, each containing an array of request/response DataSetMessages. Discovery examples include `AvroDataSetMetaData.avsc`, `AvroDataSetWriterConfigurationAnnouncement.avsc`, `AvroActionResponderConfigurationAnnouncement.avsc`, `AvroDiscoveryProbe.avsc` and `AvroPublisherEndpointsAnnouncement.avsc`. The generated schemas use the built-in `Variant`, `DataValue`, `NodeId`, `StatusCode`, `DiagnosticInfo` and `ExtensionObject` records from this annex; reduced base-UA shapes and fallbacks are documented in the Part 14 draft.

Compact examples publish the exact generated schema files below. Do not edit these JSON blocks by hand; copy them from `..\extras\avro-encoding\schemas\*.avsc`.

The published Action request DataSetMessage schema is `../extras/avro-encoding/schemas/AvroActionRequestDataSetMessage.avsc`:

```json
{
  "fields": [
    {
      "name": "ActionTargetId",
      "type": [
        "null",
        "org.opcfoundation.ua.avro.NodeId"
      ]
    },
    {
      "name": "RequestId",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "name": "CorrelationData",
      "type": [
        "null",
        "bytes"
      ]
    },
    {
      "name": "InputArguments",
      "type": {
        "items": [
          "null",
          "org.opcfoundation.ua.avro.Variant"
        ],
        "type": "array"
      }
    }
  ],
  "name": "AvroActionRequestDataSetMessage",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

The published Action request NetworkMessage schema is `../extras/avro-encoding/schemas/AvroActionRequestNetworkMessage.avsc`:

```json
{
  "fields": [
    {
      "name": "PublisherId",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "name": "WriterGroupId",
      "type": "int"
    },
    {
      "name": "NetworkMessageNumber",
      "type": "int"
    },
    {
      "name": "SequenceNumber",
      "type": "int"
    },
    {
      "name": "Timestamp",
      "type": "long"
    },
    {
      "name": "Messages",
      "type": {
        "items": [
          "null",
          "org.opcfoundation.ua.avro.AvroActionRequestDataSetMessage"
        ],
        "type": "array"
      }
    },
    {
      "name": "SchemaId",
      "type": [
        "null",
        "string"
      ]
    }
  ],
  "name": "AvroActionRequestNetworkMessage",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

The published Action response DataSetMessage schema is `../extras/avro-encoding/schemas/AvroActionResponseDataSetMessage.avsc`:

```json
{
  "fields": [
    {
      "name": "ActionTargetId",
      "type": [
        "null",
        "org.opcfoundation.ua.avro.NodeId"
      ]
    },
    {
      "name": "RequestId",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "name": "CorrelationData",
      "type": [
        "null",
        "bytes"
      ]
    },
    {
      "name": "Status",
      "type": "int"
    },
    {
      "name": "OutputArguments",
      "type": {
        "items": [
          "null",
          "org.opcfoundation.ua.avro.Variant"
        ],
        "type": "array"
      }
    },
    {
      "name": "DiagnosticInfos",
      "type": {
        "items": [
          "null",
          "org.opcfoundation.ua.avro.DiagnosticInfo"
        ],
        "type": "array"
      }
    }
  ],
  "name": "AvroActionResponseDataSetMessage",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

The published Action response NetworkMessage schema is `../extras/avro-encoding/schemas/AvroActionResponseNetworkMessage.avsc`:

```json
{
  "fields": [
    {
      "name": "PublisherId",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "name": "WriterGroupId",
      "type": "int"
    },
    {
      "name": "NetworkMessageNumber",
      "type": "int"
    },
    {
      "name": "SequenceNumber",
      "type": "int"
    },
    {
      "name": "Timestamp",
      "type": "long"
    },
    {
      "name": "Messages",
      "type": {
        "items": [
          "null",
          "org.opcfoundation.ua.avro.AvroActionResponseDataSetMessage"
        ],
        "type": "array"
      }
    },
    {
      "name": "SchemaId",
      "type": [
        "null",
        "string"
      ]
    }
  ],
  "name": "AvroActionResponseNetworkMessage",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

The published DataSetWriter configuration announcement schema is `../extras/avro-encoding/schemas/AvroDataSetWriterConfigurationAnnouncement.avsc`:

```json
{
  "fields": [
    {
      "name": "PublisherId",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "name": "WriterGroupId",
      "type": "int"
    },
    {
      "name": "DataSetWriterId",
      "type": "int"
    },
    {
      "name": "ConfigurationVersion",
      "type": "org.opcfoundation.ua.avro.AvroConfigurationVersionDataType"
    },
    {
      "name": "DataSetMetaData",
      "type": "org.opcfoundation.ua.avro.AvroDataSetMetaData"
    },
    {
      "name": "SchemaId",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "name": "SchemaJson",
      "type": [
        "null",
        "string"
      ]
    }
  ],
  "name": "AvroDataSetWriterConfigurationAnnouncement",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

## Annex A Generated type reference

<!-- BEGIN GENERATED: type-reference -->
The following reference material is generated from the published `.avsc` schemas and the shared conformance corpus. Do not edit it by hand; run `python ..\extras\avro-encoding\tools\gen_type_reference.py`.

### Built-in Boolean

**SchemaId** `64f7d4a478fc429f`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `"boolean"` | nullable where schema is a null union | OPC UA BuiltInType 1. |

**Avro schema fragment**

```json
"boolean"
```

**Example value** (`bool_true`)

```json
true
```

**Encoded bytes** (1 bytes)

```text
01
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `01` | $: boolean |

### Built-in SByte

**SchemaId** `8f5c393f1ad57572`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `"int"` | nullable where schema is a null union | OPC UA BuiltInType 2. |

**Avro schema fragment**

```json
"int"
```

**Example value** (`sbyte_min`)

```json
-128
```

**Encoded bytes** (2 bytes)

```text
ff01
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 2 | `ff 01` | $: int = -128 |

### Built-in Byte

**SchemaId** `8f5c393f1ad57572`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `"int"` | nullable where schema is a null union | OPC UA BuiltInType 3. |

**Avro schema fragment**

```json
"int"
```

**Example value** (`byte_max`)

```json
255
```

**Encoded bytes** (2 bytes)

```text
fe03
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 2 | `fe 03` | $: int = 255 |

### Built-in Int16

**SchemaId** `8f5c393f1ad57572`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `"int"` | nullable where schema is a null union | OPC UA BuiltInType 4. |

**Avro schema fragment**

```json
"int"
```

**Example value** (`int16_min`)

```json
-32768
```

**Encoded bytes** (3 bytes)

```text
ffff03
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 3 | `ff ff 03` | $: int = -32768 |

### Built-in UInt16

**SchemaId** `8f5c393f1ad57572`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `"int"` | nullable where schema is a null union | OPC UA BuiltInType 5. |

**Avro schema fragment**

```json
"int"
```

**Example value** (`uint16_max`)

```json
65535
```

**Encoded bytes** (3 bytes)

```text
feff07
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 3 | `fe ff 07` | $: int = 65535 |

### Built-in Int32

**SchemaId** `8f5c393f1ad57572`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `"int"` | nullable where schema is a null union | OPC UA BuiltInType 6. |

**Avro schema fragment**

```json
"int"
```

**Example value** (`int32_min`)

```json
-2147483648
```

**Encoded bytes** (5 bytes)

```text
ffffffff0f
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 5 | `ff ff ff ff 0f` | $: int = -2147483648 |

### Built-in UInt32

**SchemaId** `8f5c393f1ad57572`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `"int"` | nullable where schema is a null union | OPC UA BuiltInType 7. |

**Avro schema fragment**

```json
"int"
```

**Example value** (`uint32_max`)

```json
4294967295
```

**Encoded bytes** (1 bytes)

```text
01
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `01` | $: int = -1 |

### Built-in Int64

**SchemaId** `b71df49344e154d0`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `"long"` | nullable where schema is a null union | OPC UA BuiltInType 8. |

**Avro schema fragment**

```json
"long"
```

**Example value** (`int64_min`)

```json
-9223372036854775808
```

**Encoded bytes** (10 bytes)

```text
ffffffffffffffffff01
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 10 | `ff ff ff ff ff ff ff ff ff 01` | $: long = -9223372036854775808 |

### Built-in UInt64

**SchemaId** `b71df49344e154d0`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `"long"` | nullable where schema is a null union | OPC UA BuiltInType 9. |

**Avro schema fragment**

```json
"long"
```

**Example value** (`uint64_max`)

```json
18446744073709551615
```

**Encoded bytes** (1 bytes)

```text
01
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `01` | $: long = -1 |

### Built-in Float

**SchemaId** `90d7a83ecb027c4d`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `"float"` | nullable where schema is a null union | OPC UA BuiltInType 10. |

**Avro schema fragment**

```json
"float"
```

**Example value** (`float_normal`)

```json
1.5
```

**Encoded bytes** (4 bytes)

```text
0000c03f
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 4 | `00 00 c0 3f` | $: float32 little-endian |

### Built-in Double

**SchemaId** `7e95ab32c035758e`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `"double"` | nullable where schema is a null union | OPC UA BuiltInType 11. |

**Avro schema fragment**

```json
"double"
```

**Example value** (`double_nan`)

```json
"NaN"
```

**Encoded bytes** (8 bytes)

```text
000000000000f87f
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 8 | `00 00 00 00 00 00 f8 7f` | $: float64 little-endian |

### Built-in String

**SchemaId** `9dc47eb71ef24598`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `["null", "string"]` | nullable where schema is a null union | OPC UA BuiltInType 12. |

**Avro schema fragment**

```json
[
  "null",
  "string"
]
```

**Example value** (`string_unicode`)

```json
"grüße-中文-😀"
```

**Encoded bytes** (21 bytes)

```text
02266772c3bcc39f652de4b8ade696872df09f9880
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $: union branch index = 1 |
| 1 | 1 | `26` | $: branch 1 (string): string length = 19 |
| 2 | 19 | `67 72 c3 bc c3 9f 65 2d e4 b8 ad e6 96 87 2d f0 … (+3 B)` | $: branch 1 (string): string data |

### Built-in DateTime

**SchemaId** `b71df49344e154d0`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `"long"` | nullable where schema is a null union | OPC UA BuiltInType 13. |

**Avro schema fragment**

```json
"long"
```

**Example value** (`datetime_now`)

```json
{"ticks": 133000000000000000}
```

**Encoded bytes** (9 bytes)

```text
808084b2f3b2c1d803
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 9 | `80 80 84 b2 f3 b2 c1 d8 03` | $: long = 133000000000000000 |

### Built-in Guid

**SchemaId** `cde4c366633fdfe6`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `"org.opcfoundation.ua.avro.Guid"` | nullable where schema is a null union | OPC UA BuiltInType 14. |

**Avro schema fragment**

```json
"org.opcfoundation.ua.avro.Guid"
```

**Example value** (`guid`)

```json
{"bytes": "0x0102030405060708090a0b0c0d0e0f10"}
```

**Encoded bytes** (16 bytes)

```text
0102030405060708090a0b0c0d0e0f10
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 16 | `01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f 10` | $: fixed org.opcfoundation.ua.avro.Guid (16 bytes) |

### Built-in ByteString

**SchemaId** `9d4c3eb5447b4848`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `["null", "bytes"]` | nullable where schema is a null union | OPC UA BuiltInType 15. |

**Avro schema fragment**

```json
[
  "null",
  "bytes"
]
```

**Example value** (`bytestring`)

```json
"0x0001020304050607"
```

**Encoded bytes** (10 bytes)

```text
02100001020304050607
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $: union branch index = 1 |
| 1 | 1 | `10` | $: branch 1 (bytes): bytes length = 8 |
| 2 | 8 | `00 01 02 03 04 05 06 07` | $: branch 1 (bytes): bytes data |

### Built-in XmlElement

**SchemaId** `9dc47eb71ef24598`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `["null", "string"]` | nullable where schema is a null union | OPC UA BuiltInType 16. |

**Avro schema fragment**

```json
[
  "null",
  "string"
]
```

**Example value** (`xml`)

```json
{"value": "<a x='1'>t</a>"}
```

**Encoded bytes** (16 bytes)

```text
021c3c6120783d2731273e743c2f613e
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $: union branch index = 1 |
| 1 | 1 | `1c` | $: branch 1 (string): string length = 14 |
| 2 | 14 | `3c 61 20 78 3d 27 31 27 3e 74 3c 2f 61 3e` | $: branch 1 (string): string data |

### Built-in NodeId

**SchemaId** `7a72f202d5e8e102`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `{"fields": [{"name": "namespace", "type": "int"}, {"name": "idType", "type": "int"}, {"default": null, "name": "numeric", "type": ["null", "long"]}, {"default": null, "name": "string", "type": ["null", "string"]}, {"default": null, "name": "guid", "type": ["null", {"logicalType": "opcua-guid", "name": "Guid", "namespace": "org.opcfoundation.ua.avro", "size": 16, "type": "fixed"}]}, {"default": null, "name": "opaque", "type": ["null", "bytes"]}], "name": "NodeId", "namespace": "org.opcfoundation.ua.avro", "type": "record"}` | nullable where schema is a null union | OPC UA BuiltInType 17. |

**Avro schema fragment**

```json
{
  "fields": [
    {
      "name": "namespace",
      "type": "int"
    },
    {
      "name": "idType",
      "type": "int"
    },
    {
      "default": null,
      "name": "numeric",
      "type": [
        "null",
        "long"
      ]
    },
    {
      "default": null,
      "name": "string",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "default": null,
      "name": "guid",
      "type": [
        "null",
        {
          "logicalType": "opcua-guid",
          "name": "Guid",
          "namespace": "org.opcfoundation.ua.avro",
          "size": 16,
          "type": "fixed"
        }
      ]
    },
    {
      "default": null,
      "name": "opaque",
      "type": [
        "null",
        "bytes"
      ]
    }
  ],
  "name": "NodeId",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

**Example value** (`nodeid_numeric`)

```json
{"id_type": 0, "identifier": 2258, "namespace": 0}
```

**Encoded bytes** (9 bytes)

```text
02000002a423000000
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $: union branch index = 1 |
| 1 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.NodeId).namespace: int = 0 |
| 2 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.NodeId).idType: int = 0 |
| 3 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.NodeId).numeric: union branch index = 1 |
| 4 | 2 | `a4 23` | $: branch 1 (org.opcfoundation.ua.avro.NodeId).numeric: branch 1 (long): long = 2258 |
| 6 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.NodeId).string: union branch index = 0 |
| 7 | 0 | `—` | $: branch 1 (org.opcfoundation.ua.avro.NodeId).string: branch 0 (null): null |
| 7 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.NodeId).guid: union branch index = 0 |
| 8 | 0 | `—` | $: branch 1 (org.opcfoundation.ua.avro.NodeId).guid: branch 0 (null): null |
| 8 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.NodeId).opaque: union branch index = 0 |
| 9 | 0 | `—` | $: branch 1 (org.opcfoundation.ua.avro.NodeId).opaque: branch 0 (null): null |

### Built-in ExpandedNodeId

**SchemaId** `eff6df8ff05db838`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `{"fields": [{"name": "nodeId", "type": "org.opcfoundation.ua.avro.NodeId"}, {"default": null, "name": "namespaceUri", "type": ["null", "string"]}, {"default": 0, "name": "serverIndex", "type": "long"}], "name": "ExpandedNodeId", "namespace": "org.opcfoundation.ua.avro", "type": "record"}` | nullable where schema is a null union | OPC UA BuiltInType 18. |

**Avro schema fragment**

```json
{
  "fields": [
    {
      "name": "nodeId",
      "type": "org.opcfoundation.ua.avro.NodeId"
    },
    {
      "default": null,
      "name": "namespaceUri",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "default": 0,
      "name": "serverIndex",
      "type": "long"
    }
  ],
  "name": "ExpandedNodeId",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

**Example value** (`expnodeid_full`)

```json
{"namespace_uri": "http://example.org/UA/", "node_id": {"id_type": 1, "identifier": "X", "namespace": 1}, "server_index": 5}
```

**Encoded bytes** (34 bytes)

```text
020202000202580000022c687474703a2f2f6578616d706c652e6f72672f55412f0a
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $: union branch index = 1 |
| 1 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).nodeId.namespace: int = 1 |
| 2 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).nodeId.idType: int = 1 |
| 3 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).nodeId.numeric: union branch index = 0 |
| 4 | 0 | `—` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).nodeId.numeric: branch 0 (null): null |
| 4 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).nodeId.string: union branch index = 1 |
| 5 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).nodeId.string: branch 1 (string): string length = 1 |
| 6 | 1 | `58` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).nodeId.string: branch 1 (string): string data |
| 7 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).nodeId.guid: union branch index = 0 |
| 8 | 0 | `—` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).nodeId.guid: branch 0 (null): null |
| 8 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).nodeId.opaque: union branch index = 0 |
| 9 | 0 | `—` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).nodeId.opaque: branch 0 (null): null |
| 9 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).namespaceUri: union branch index = 1 |
| 10 | 1 | `2c` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).namespaceUri: branch 1 (string): string length = 22 |
| 11 | 22 | `68 74 74 70 3a 2f 2f 65 78 61 6d 70 6c 65 2e 6f … (+6 B)` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).namespaceUri: branch 1 (string): string data |
| 33 | 1 | `0a` | $: branch 1 (org.opcfoundation.ua.avro.ExpandedNodeId).serverIndex: long = 5 |

### Built-in StatusCode

**SchemaId** `8f5c393f1ad57572`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `"int"` | nullable where schema is a null union | OPC UA BuiltInType 19. |

**Avro schema fragment**

```json
"int"
```

**Example value** (`status_bad`)

```json
{"value": 2158755840}
```

**Encoded bytes** (5 bytes)

```text
ffff9ff50f
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 5 | `ff ff 9f f5 0f` | $: int = -2136211456 |

### Built-in QualifiedName

**SchemaId** `5ea7a40e898d19ec`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `{"fields": [{"name": "namespace", "type": "int"}, {"default": null, "name": "name", "type": ["null", "string"]}], "name": "QualifiedName", "namespace": "org.opcfoundation.ua.avro", "type": "record"}` | nullable where schema is a null union | OPC UA BuiltInType 20. |

**Avro schema fragment**

```json
{
  "fields": [
    {
      "name": "namespace",
      "type": "int"
    },
    {
      "default": null,
      "name": "name",
      "type": [
        "null",
        "string"
      ]
    }
  ],
  "name": "QualifiedName",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

**Example value** (`qname`)

```json
{"name": "Temp", "namespace": 1}
```

**Encoded bytes** (8 bytes)

```text
0202020854656d70
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $: union branch index = 1 |
| 1 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.QualifiedName).namespace: int = 1 |
| 2 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.QualifiedName).name: union branch index = 1 |
| 3 | 1 | `08` | $: branch 1 (org.opcfoundation.ua.avro.QualifiedName).name: branch 1 (string): string length = 4 |
| 4 | 4 | `54 65 6d 70` | $: branch 1 (org.opcfoundation.ua.avro.QualifiedName).name: branch 1 (string): string data |

### Built-in LocalizedText

**SchemaId** `2d8ba35586039a65`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `{"fields": [{"default": null, "name": "locale", "type": ["null", "string"]}, {"default": null, "name": "text", "type": ["null", "string"]}], "name": "LocalizedText", "namespace": "org.opcfoundation.ua.avro", "type": "record"}` | nullable where schema is a null union | OPC UA BuiltInType 21. |

**Avro schema fragment**

```json
{
  "fields": [
    {
      "default": null,
      "name": "locale",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "default": null,
      "name": "text",
      "type": [
        "null",
        "string"
      ]
    }
  ],
  "name": "LocalizedText",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

**Example value** (`ltext_full`)

```json
{"locale": "en", "text": "Hello"}
```

**Encoded bytes** (12 bytes)

```text
020204656e020a48656c6c6f
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $: union branch index = 1 |
| 1 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.LocalizedText).locale: union branch index = 1 |
| 2 | 1 | `04` | $: branch 1 (org.opcfoundation.ua.avro.LocalizedText).locale: branch 1 (string): string length = 2 |
| 3 | 2 | `65 6e` | $: branch 1 (org.opcfoundation.ua.avro.LocalizedText).locale: branch 1 (string): string data |
| 5 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.LocalizedText).text: union branch index = 1 |
| 6 | 1 | `0a` | $: branch 1 (org.opcfoundation.ua.avro.LocalizedText).text: branch 1 (string): string length = 5 |
| 7 | 5 | `48 65 6c 6c 6f` | $: branch 1 (org.opcfoundation.ua.avro.LocalizedText).text: branch 1 (string): string data |

### Built-in ExtensionObject

**SchemaId** `f50df9bab1852efe`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `{"fields": [{"name": "typeId", "type": "org.opcfoundation.ua.avro.NodeId"}, {"default": null, "doc": "Known ExtensionObject bodies use typed record branches; bytes is reserved for genuinely unknown type ids.", "name": "body", "type": ["null", {"fields": [{"name": "X", "type": "double"}, {"name": "Y", "type": "double"}], "name": "Point", "namespace": "org.opcfoundation.ua.avro", "type": "record"}, {"fields": [{"name": "Name", "type": ["null", "string"]}, {"name": "Age", "type": "int"}, {"default": null, "name": "Email", "type": ["null", {"fields": [{"name": "value", "type": ["null", "string"]}], "name": "Person_Email_Optional", "namespace": "org.opcfoundation.ua.avro", "type": "record"}]}, {"default": null, "name": "Nickname", "type": ["null", {"fields": [{"name": "value", "type": ["null", "string"]}], "name": "Person_Nickname_Optional", "namespace": "org.opcfoundation.ua.avro", "type": "record"}]}], "name": "Person", "namespace": "org.opcfoundation.ua.avro", "type": "record"}, {"fields": [{"default": null, "name": "switch", "type": ["null", "string"]}, {"default": null, "name": "value", "type": ["null", {"fields": [{"name": "AsInt", "type": "int"}], "name": "Measurement_AsInt_Branch", "namespace": "org.opcfoundation.ua.avro", "type": "record"}, {"fields": [{"name": "AsText", "type": ["null", "string"]}], "name": "Measurement_AsText_Branch", "namespace": "org.opcfoundation.ua.avro", "type": "record"}, {"fields": [{"name": "AsPoint", "type": "org.opcfoundation.ua.avro.Point"}], "name": "Measurement_AsPoint_Branch", "namespace": "org.opcfoundation.ua.avro", "type": "record"}]}], "name": "Measurement", "namespace": "org.opcfoundation.ua.avro", "type": "record"}, {"fields": [{"name": "Id", "type": ["null", "string"]}, {"name": "Location", "type": "org.opcfoundation.ua.avro.Point"}, {"name": "Tags", "type": {"items": ["null", "string"], "type": "array"}}, {"name": "Payload", "type": ["null", "org.opcfoundation.ua.avro.ExtensionObject"]}], "name": "Envelope", "namespace": "org.opcfoundation.ua.avro", "type": "record"}, {"fields": [{"name": "Id", "type": "int"}, {"default": null, "name": "Flag", "type": ["null", {"fields": [{"name": "value", "type": "boolean"}], "name": "OptionalScalars_Flag_Optional", "namespace": "org.opcfoundation.ua.avro", "type": "record"}]}, {"default": null, "name": "Count", "type": ["null", {"fields": [{"name": "value", "type": "int"}], "name": "OptionalScalars_Count_Optional", "namespace": "org.opcfoundation.ua.avro", "type": "record"}]}, {"default": null, "name": "Ratio", "type": ["null", {"fields": [{"name": "value", "type": "double"}], "name": "OptionalScalars_Ratio_Optional", "namespace": "org.opcfoundation.ua.avro", "type": "record"}]}], "name": "OptionalScalars", "namespace": "org.opcfoundation.ua.avro", "type": "record"}, {"fields": [{"name": "A", "type": "float"}, {"default": null, "name": "B", "type": ["null", {"fields": [{"name": "value", "type": "float"}], "name": "FloatHolder_B_Optional", "namespace": "org.opcfoundation.ua.avro", "type": "record"}]}], "name": "FloatHolder", "namespace": "org.opcfoundation.ua.avro", "type": "record"}, {"fields": [{"name": "FieldName", "type": ["null", "string"]}, {"name": "Kind", "type": "int"}, {"name": "AttributeId", "type": "int"}, {"name": "SamplingIntervalHint", "type": "double"}, {"name": "IndexRange", "type": ["null", "string"]}, {"name": "StartingNode", "type": ["null", "org.opcfoundation.ua.avro.NodeId"]}, {"name": "BrowsePath", "type": ["null", "org.opcfoundation.ua.avro.ExtensionObject"]}, {"name": "SourceNodeId", "type": ["null", "org.opcfoundation.ua.avro.NodeId"]}, {"name": "OwningObjectPath", "type": ["null", "org.opcfoundation.ua.avro.ExtensionObject"]}, {"name": "SourceTypeDefinition", "type": ["null", "org.opcfoundation.ua.avro.NodeId"]}, {"name": "SourceBrowseName", "type": ["null", "org.opcfoundation.ua.avro.QualifiedName"]}, {"name": "ModelNamespaceUri", "type": ["null", "string"]}, {"name": "DataSetFieldId", "type": "org.opcfoundation.ua.avro.Guid"}, {"name": "SemanticReferenceUri", "type": ["null", "string"]}], "name": "BoundItemDataType", "namespace": "org.opcfoundation.ua.avro", "type": "record"}, {"fields": [{"name": "Name", "type": ["null", "string"]}, {"name": "ScenarioUri", "type": ["null", "string"]}, {"name": "Direction", "type": "int"}, {"name": "ConfigurationVersion", "type": ["null", "org.opcfoundation.ua.avro.ExtensionObject"]}, {"name": "BoundItems", "type": {"items": ["null", "org.opcfoundation.ua.avro.BoundItemDataType"], "type": "array"}}, {"name": "PublishedDataSetName", "type": ["null", "string"]}, {"name": "WriterGroupName", "type": ["null", "string"]}], "name": "ScenarioBindingDataType", "namespace": "org.opcfoundation.ua.avro", "type": "record"}, {"fields": [{"name": "ModelNamespaceUri", "type": ["null", "string"]}, {"name": "AppliesToType", "type": ["null", "org.opcfoundation.ua.avro.QualifiedName"]}, {"name": "ConfigurationVersion", "type": ["null", "org.opcfoundation.ua.avro.ExtensionObject"]}, {"name": "ScenarioBindings", "type": {"items": ["null", "org.opcfoundation.ua.avro.ScenarioBindingDataType"], "type": "array"}}], "name": "ScenarioBindingConfigurationDataType", "namespace": "org.opcfoundation.ua.avro", "type": "record"}, "bytes"]}], "name": "ExtensionObject", "namespace": "org.opcfoundation.ua.avro", "type": "record"}` | nullable where schema is a null union | OPC UA BuiltInType 22. |

**Avro schema fragment**

```json
{
  "fields": [
    {
      "name": "typeId",
      "type": "org.opcfoundation.ua.avro.NodeId"
    },
    {
      "default": null,
      "doc": "Known ExtensionObject bodies use typed record branches; bytes is reserved for genuinely unknown type ids.",
      "name": "body",
      "type": [
        "null",
        {
          "fields": [
            {
              "name": "X",
              "type": "double"
            },
            {
              "name": "Y",
              "type": "double"
            }
          ],
          "name": "Point",
          "namespace": "org.opcfoundation.ua.avro",
          "type": "record"
        },
        {
          "fields": [
            {
              "name": "Name",
              "type": [
                "null",
                "string"
              ]
            },
            {
              "name": "Age",
              "type": "int"
            },
            {
              "default": null,
              "name": "Email",
              "type": [
                "null",
                {
                  "fields": [
                    {
                      "name": "value",
                      "type": [
                        "null",
                        "string"
                      ]
                    }
                  ],
                  "name": "Person_Email_Optional",
                  "namespace": "org.opcfoundation.ua.avro",
                  "type": "record"
                }
              ]
            },
            {
              "default": null,
              "name": "Nickname",
              "type": [
                "null",
                {
                  "fields": [
                    {
                      "name": "value",
                      "type": [
                        "null",
                        "string"
                      ]
                    }
                  ],
                  "name": "Person_Nickname_Optional",
                  "namespace": "org.opcfoundation.ua.avro",
                  "type": "record"
                }
              ]
            }
          ],
          "name": "Person",
          "namespace": "org.opcfoundation.ua.avro",
          "type": "record"
        },
        {
          "fields": [
            {
              "default": null,
              "name": "switch",
              "type": [
                "null",
                "string"
              ]
            },
            {
              "default": null,
              "name": "value",
              "type": [
                "null",
                {
                  "fields": [
                    {
                      "name": "AsInt",
                      "type": "int"
                    }
                  ],
                  "name": "Measurement_AsInt_Branch",
                  "namespace": "org.opcfoundation.ua.avro",
                  "type": "record"
                },
                {
                  "fields": [
                    {
                      "name": "AsText",
                      "type": [
                        "null",
                        "string"
                      ]
                    }
                  ],
                  "name": "Measurement_AsText_Branch",
                  "namespace": "org.opcfoundation.ua.avro",
                  "type": "record"
                },
                {
                  "fields": [
                    {
                      "name": "AsPoint",
                      "type": "org.opcfoundation.ua.avro.Point"
                    }
                  ],
                  "name": "Measurement_AsPoint_Branch",
                  "namespace": "org.opcfoundation.ua.avro",
                  "type": "record"
                }
              ]
            }
          ],
          "name": "Measurement",
          "namespace": "org.opcfoundation.ua.avro",
          "type": "record"
        },
        {
          "fields": [
            {
              "name": "Id",
              "type": [
                "null",
                "string"
              ]
            },
            {
              "name": "Location",
              "type": "org.opcfoundation.ua.avro.Point"
            },
            {
              "name": "Tags",
              "type": {
                "items": [
                  "null",
                  "string"
                ],
                "type": "array"
              }
            },
            {
              "name": "Payload",
              "type": [
                "null",
                "org.opcfoundation.ua.avro.ExtensionObject"
              ]
            }
          ],
          "name": "Envelope",
          "namespace": "org.opcfoundation.ua.avro",
          "type": "record"
        },
        {
          "fields": [
            {
              "name": "Id",
              "type": "int"
            },
            {
              "default": null,
              "name": "Flag",
              "type": [
                "null",
                {
                  "fields": [
                    {
                      "name": "value",
                      "type": "boolean"
                    }
                  ],
                  "name": "OptionalScalars_Flag_Optional",
                  "namespace": "org.opcfoundation.ua.avro",
                  "type": "record"
                }
              ]
            },
            {
              "default": null,
              "name": "Count",
              "type": [
                "null",
                {
                  "fields": [
                    {
                      "name": "value",
                      "type": "int"
                    }
                  ],
                  "name": "OptionalScalars_Count_Optional",
                  "namespace": "org.opcfoundation.ua.avro",
                  "type": "record"
                }
              ]
            },
            {
              "default": null,
              "name": "Ratio",
              "type": [
                "null",
                {
                  "fields": [
                    {
                      "name": "value",
                      "type": "double"
                    }
                  ],
                  "name": "OptionalScalars_Ratio_Optional",
                  "namespace": "org.opcfoundation.ua.avro",
                  "type": "record"
                }
              ]
            }
          ],
          "name": "OptionalScalars",
          "namespace": "org.opcfoundation.ua.avro",
          "type": "record"
        },
        {
          "fields": [
            {
              "name": "A",
              "type": "float"
            },
            {
              "default": null,
              "name": "B",
              "type": [
                "null",
                {
                  "fields": [
                    {
                      "name": "value",
                      "type": "float"
                    }
                  ],
                  "name": "FloatHolder_B_Optional",
                  "namespace": "org.opcfoundation.ua.avro",
                  "type": "record"
                }
              ]
            }
          ],
          "name": "FloatHolder",
          "namespace": "org.opcfoundation.ua.avro",
          "type": "record"
        },
        {
          "fields": [
            {
              "name": "FieldName",
              "type": [
                "null",
                "string"
              ]
            },
            {
              "name": "Kind",
              "type": "int"
            },
            {
              "name": "AttributeId",
              "type": "int"
            },
            {
              "name": "SamplingIntervalHint",
              "type": "double"
            },
            {
              "name": "IndexRange",
              "type": [
                "null",
                "string"
              ]
            },
            {
              "name": "StartingNode",
              "type": [
                "null",
                "org.opcfoundation.ua.avro.NodeId"
              ]
            },
            {
              "name": "BrowsePath",
              "type": [
                "null",
                "org.opcfoundation.ua.avro.ExtensionObject"
              ]
            },
            {
              "name": "SourceNodeId",
              "type": [
                "null",
                "org.opcfoundation.ua.avro.NodeId"
              ]
            },
            {
              "name": "OwningObjectPath",
              "type": [
                "null",
                "org.opcfoundation.ua.avro.ExtensionObject"
              ]
            },
            {
              "name": "SourceTypeDefinition",
              "type": [
                "null",
                "org.opcfoundation.ua.avro.NodeId"
              ]
            },
            {
              "name": "SourceBrowseName",
              "type": [
                "null",
                "org.opcfoundation.ua.avro.QualifiedName"
              ]
            },
            {
              "name": "ModelNamespaceUri",
              "type": [
                "null",
                "string"
              ]
            },
            {
              "name": "DataSetFieldId",
              "type": "org.opcfoundation.ua.avro.Guid"
            },
            {
              "name": "SemanticReferenceUri",
              "type": [
                "null",
                "string"
              ]
            }
          ],
          "name": "BoundItemDataType",
          "namespace": "org.opcfoundation.ua.avro",
          "type": "record"
        },
        {
          "fields": [
            {
              "name": "Name",
              "type": [
                "null",
                "string"
              ]
            },
            {
              "name": "ScenarioUri",
              "type": [
                "null",
                "string"
              ]
            },
            {
              "name": "Direction",
              "type": "int"
            },
            {
              "name": "ConfigurationVersion",
              "type": [
                "null",
                "org.opcfoundation.ua.avro.ExtensionObject"
              ]
            },
            {
              "name": "BoundItems",
              "type": {
                "items": [
                  "null",
                  "org.opcfoundation.ua.avro.BoundItemDataType"
                ],
                "type": "array"
              }
            },
            {
              "name": "PublishedDataSetName",
              "type": [
                "null",
                "string"
              ]
            },
            {
              "name": "WriterGroupName",
              "type": [
                "null",
                "string"
              ]
            }
          ],
          "name": "ScenarioBindingDataType",
          "namespace": "org.opcfoundation.ua.avro",
          "type": "record"
        },
        {
          "fields": [
            {
              "name": "ModelNamespaceUri",
              "type": [
                "null",
                "string"
              ]
            },
            {
              "name": "AppliesToType",
              "type": [
                "null",
                "org.opcfoundation.ua.avro.QualifiedName"
              ]
            },
            {
              "name": "ConfigurationVersion",
              "type": [
                "null",
                "org.opcfoundation.ua.avro.ExtensionObject"
              ]
            },
            {
              "name": "ScenarioBindings",
              "type": {
                "items": [
                  "null",
                  "org.opcfoundation.ua.avro.ScenarioBindingDataType"
                ],
                "type": "array"
              }
            }
          ],
          "name": "ScenarioBindingConfigurationDataType",
          "namespace": "org.opcfoundation.ua.avro",
          "type": "record"
        },
        "bytes"
      ]
    }
  ],
  "name": "ExtensionObject",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

**Example value** (`extobj_point`)

```json
{"body": {"fields": {"X": 1.0, "Y": 1.0}, "type_name": "Point"}, "type_id": {"id_type": 0, "identifier": 3001, "namespace": 0}}
```

**Encoded bytes** (26 bytes)

```text
02000002f22e00000002000000000000f03f000000000000f03f
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $: union branch index = 1 |
| 1 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.namespace: int = 0 |
| 2 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.idType: int = 0 |
| 3 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.numeric: union branch index = 1 |
| 4 | 2 | `f2 2e` | $: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.numeric: branch 1 (long): long = 3001 |
| 6 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.string: union branch index = 0 |
| 7 | 0 | `—` | $: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.string: branch 0 (null): null |
| 7 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.guid: union branch index = 0 |
| 8 | 0 | `—` | $: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.guid: branch 0 (null): null |
| 8 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.opaque: union branch index = 0 |
| 9 | 0 | `—` | $: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.opaque: branch 0 (null): null |
| 9 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).body: union branch index = 1 |
| 10 | 8 | `00 00 00 00 00 00 f0 3f` | $: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).body: branch 1 (org.opcfoundation.ua.avro.Point).X: float64 little-endian |
| 18 | 8 | `00 00 00 00 00 00 f0 3f` | $: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).body: branch 1 (org.opcfoundation.ua.avro.Point).Y: float64 little-endian |

### Built-in DataValue

**SchemaId** `2abf014fafc0cfa5`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `{"fields": [{"default": null, "name": "value", "type": ["null", "org.opcfoundation.ua.avro.Variant"]}, {"default": null, "name": "status", "type": ["null", "int"]}, {"default": null, "name": "sourceTimestamp", "type": ["null", "long"]}, {"default": null, "name": "sourcePicoseconds", "type": ["null", "int"]}, {"default": null, "name": "serverTimestamp", "type": ["null", "long"]}, {"default": null, "name": "serverPicoseconds", "type": ["null", "int"]}], "name": "DataValue", "namespace": "org.opcfoundation.ua.avro", "type": "record"}` | nullable where schema is a null union | OPC UA BuiltInType 23. |

**Avro schema fragment**

```json
{
  "fields": [
    {
      "default": null,
      "name": "value",
      "type": [
        "null",
        "org.opcfoundation.ua.avro.Variant"
      ]
    },
    {
      "default": null,
      "name": "status",
      "type": [
        "null",
        "int"
      ]
    },
    {
      "default": null,
      "name": "sourceTimestamp",
      "type": [
        "null",
        "long"
      ]
    },
    {
      "default": null,
      "name": "sourcePicoseconds",
      "type": [
        "null",
        "int"
      ]
    },
    {
      "default": null,
      "name": "serverTimestamp",
      "type": [
        "null",
        "long"
      ]
    },
    {
      "default": null,
      "name": "serverPicoseconds",
      "type": [
        "null",
        "int"
      ]
    }
  ],
  "name": "DataValue",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

**Example value** (`datavalue_full`)

```json
{"server_picoseconds": 250, "server_timestamp": {"ticks": 2000}, "source_picoseconds": 500, "source_timestamp": {"ticks": 1000}, "status": {"value": 0}, "value": {"dimensions": null, "value": 42, "vtype": {"id": 6}}}
```

**Encoded bytes** (19 bytes)

```text
020c002054020002d00f02e80702a01f02f403
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $.value: union branch index = 1 |
| 1 | 1 | `0c` | $.value: branch 1 (org.opcfoundation.ua.avro.Variant).builtInType: int = 6 |
| 2 | 1 | `00` | $.value: branch 1 (org.opcfoundation.ua.avro.Variant).dimensions: union branch index = 0 |
| 3 | 0 | `—` | $.value: branch 1 (org.opcfoundation.ua.avro.Variant).dimensions: branch 0 (null): null |
| 3 | 1 | `20` | $.value: branch 1 (org.opcfoundation.ua.avro.Variant).body: union branch index = 16 |
| 4 | 1 | `54` | $.value: branch 1 (org.opcfoundation.ua.avro.Variant).body: branch 16 (org.opcfoundation.ua.avro.VariantInt32Scalar).value: int = 42 |
| 5 | 1 | `02` | $.status: union branch index = 1 |
| 6 | 1 | `00` | $.status: branch 1 (int): int = 0 |
| 7 | 1 | `02` | $.sourceTimestamp: union branch index = 1 |
| 8 | 2 | `d0 0f` | $.sourceTimestamp: branch 1 (long): long = 1000 |
| 10 | 1 | `02` | $.sourcePicoseconds: union branch index = 1 |
| 11 | 2 | `e8 07` | $.sourcePicoseconds: branch 1 (int): int = 500 |
| 13 | 1 | `02` | $.serverTimestamp: union branch index = 1 |
| 14 | 2 | `a0 1f` | $.serverTimestamp: branch 1 (long): long = 2000 |
| 16 | 1 | `02` | $.serverPicoseconds: union branch index = 1 |
| 17 | 2 | `f4 03` | $.serverPicoseconds: branch 1 (int): int = 250 |

### Built-in Variant

**SchemaId** `e4991bff0397acd7`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `{"fields": [{"name": "builtInType", "type": "int"}, {"default": null, "name": "dimensions", "type": ["null", {"items": "int", "type": "array"}]}, {"default": null, "name": "body", "type": ["null", "org.opcfoundation.ua.avro.VariantBooleanScalar", "org.opcfoundation.ua.avro.VariantBooleanArray", "org.opcfoundation.ua.avro.VariantBooleanMatrixBody", "org.opcfoundation.ua.avro.VariantSByteScalar", "org.opcfoundation.ua.avro.VariantSByteArray", "org.opcfoundation.ua.avro.VariantSByteMatrixBody", "org.opcfoundation.ua.avro.VariantByteScalar", "org.opcfoundation.ua.avro.VariantByteArray", "org.opcfoundation.ua.avro.VariantByteMatrixBody", "org.opcfoundation.ua.avro.VariantInt16Scalar", "org.opcfoundation.ua.avro.VariantInt16Array", "org.opcfoundation.ua.avro.VariantInt16MatrixBody", "org.opcfoundation.ua.avro.VariantUInt16Scalar", "org.opcfoundation.ua.avro.VariantUInt16Array", "org.opcfoundation.ua.avro.VariantUInt16MatrixBody", "org.opcfoundation.ua.avro.VariantInt32Scalar", "org.opcfoundation.ua.avro.VariantInt32Array", "org.opcfoundation.ua.avro.VariantInt32MatrixBody", "org.opcfoundation.ua.avro.VariantUInt32Scalar", "org.opcfoundation.ua.avro.VariantUInt32Array", "org.opcfoundation.ua.avro.VariantUInt32MatrixBody", "org.opcfoundation.ua.avro.VariantInt64Scalar", "org.opcfoundation.ua.avro.VariantInt64Array", "org.opcfoundation.ua.avro.VariantInt64MatrixBody", "org.opcfoundation.ua.avro.VariantUInt64Scalar", "org.opcfoundation.ua.avro.VariantUInt64Array", "org.opcfoundation.ua.avro.VariantUInt64MatrixBody", "org.opcfoundation.ua.avro.VariantFloatScalar", "org.opcfoundation.ua.avro.VariantFloatArray", "org.opcfoundation.ua.avro.VariantFloatMatrixBody", "org.opcfoundation.ua.avro.VariantDoubleScalar", "org.opcfoundation.ua.avro.VariantDoubleArray", "org.opcfoundation.ua.avro.VariantDoubleMatrixBody", "org.opcfoundation.ua.avro.VariantStringScalar", "org.opcfoundation.ua.avro.VariantStringArray", "org.opcfoundation.ua.avro.VariantStringMatrixBody", "org.opcfoundation.ua.avro.VariantDateTimeScalar", "org.opcfoundation.ua.avro.VariantDateTimeArray", "org.opcfoundation.ua.avro.VariantDateTimeMatrixBody", "org.opcfoundation.ua.avro.VariantGuidScalar", "org.opcfoundation.ua.avro.VariantGuidArray", "org.opcfoundation.ua.avro.VariantGuidMatrixBody", "org.opcfoundation.ua.avro.VariantByteStringScalar", "org.opcfoundation.ua.avro.VariantByteStringArray", "org.opcfoundation.ua.avro.VariantByteStringMatrixBody", "org.opcfoundation.ua.avro.VariantXmlElementScalar", "org.opcfoundation.ua.avro.VariantXmlElementArray", "org.opcfoundation.ua.avro.VariantXmlElementMatrixBody", "org.opcfoundation.ua.avro.VariantNodeIdScalar", "org.opcfoundation.ua.avro.VariantNodeIdArray", "org.opcfoundation.ua.avro.VariantNodeIdMatrixBody", "org.opcfoundation.ua.avro.VariantExpandedNodeIdScalar", "org.opcfoundation.ua.avro.VariantExpandedNodeIdArray", "org.opcfoundation.ua.avro.VariantExpandedNodeIdMatrixBody", "org.opcfoundation.ua.avro.VariantStatusCodeScalar", "org.opcfoundation.ua.avro.VariantStatusCodeArray", "org.opcfoundation.ua.avro.VariantStatusCodeMatrixBody", "org.opcfoundation.ua.avro.VariantQualifiedNameScalar", "org.opcfoundation.ua.avro.VariantQualifiedNameArray", "org.opcfoundation.ua.avro.VariantQualifiedNameMatrixBody", "org.opcfoundation.ua.avro.VariantLocalizedTextScalar", "org.opcfoundation.ua.avro.VariantLocalizedTextArray", "org.opcfoundation.ua.avro.VariantLocalizedTextMatrixBody", "org.opcfoundation.ua.avro.VariantExtensionObjectScalar", "org.opcfoundation.ua.avro.VariantExtensionObjectArray", "org.opcfoundation.ua.avro.VariantExtensionObjectMatrixBody"]}], "name": "Variant", "namespace": "org.opcfoundation.ua.avro", "type": "record"}` | nullable where schema is a null union | OPC UA BuiltInType 24. |

**Avro schema fragment**

```json
{
  "fields": [
    {
      "name": "builtInType",
      "type": "int"
    },
    {
      "default": null,
      "name": "dimensions",
      "type": [
        "null",
        {
          "items": "int",
          "type": "array"
        }
      ]
    },
    {
      "default": null,
      "name": "body",
      "type": [
        "null",
        "org.opcfoundation.ua.avro.VariantBooleanScalar",
        "org.opcfoundation.ua.avro.VariantBooleanArray",
        "org.opcfoundation.ua.avro.VariantBooleanMatrixBody",
        "org.opcfoundation.ua.avro.VariantSByteScalar",
        "org.opcfoundation.ua.avro.VariantSByteArray",
        "org.opcfoundation.ua.avro.VariantSByteMatrixBody",
        "org.opcfoundation.ua.avro.VariantByteScalar",
        "org.opcfoundation.ua.avro.VariantByteArray",
        "org.opcfoundation.ua.avro.VariantByteMatrixBody",
        "org.opcfoundation.ua.avro.VariantInt16Scalar",
        "org.opcfoundation.ua.avro.VariantInt16Array",
        "org.opcfoundation.ua.avro.VariantInt16MatrixBody",
        "org.opcfoundation.ua.avro.VariantUInt16Scalar",
        "org.opcfoundation.ua.avro.VariantUInt16Array",
        "org.opcfoundation.ua.avro.VariantUInt16MatrixBody",
        "org.opcfoundation.ua.avro.VariantInt32Scalar",
        "org.opcfoundation.ua.avro.VariantInt32Array",
        "org.opcfoundation.ua.avro.VariantInt32MatrixBody",
        "org.opcfoundation.ua.avro.VariantUInt32Scalar",
        "org.opcfoundation.ua.avro.VariantUInt32Array",
        "org.opcfoundation.ua.avro.VariantUInt32MatrixBody",
        "org.opcfoundation.ua.avro.VariantInt64Scalar",
        "org.opcfoundation.ua.avro.VariantInt64Array",
        "org.opcfoundation.ua.avro.VariantInt64MatrixBody",
        "org.opcfoundation.ua.avro.VariantUInt64Scalar",
        "org.opcfoundation.ua.avro.VariantUInt64Array",
        "org.opcfoundation.ua.avro.VariantUInt64MatrixBody",
        "org.opcfoundation.ua.avro.VariantFloatScalar",
        "org.opcfoundation.ua.avro.VariantFloatArray",
        "org.opcfoundation.ua.avro.VariantFloatMatrixBody",
        "org.opcfoundation.ua.avro.VariantDoubleScalar",
        "org.opcfoundation.ua.avro.VariantDoubleArray",
        "org.opcfoundation.ua.avro.VariantDoubleMatrixBody",
        "org.opcfoundation.ua.avro.VariantStringScalar",
        "org.opcfoundation.ua.avro.VariantStringArray",
        "org.opcfoundation.ua.avro.VariantStringMatrixBody",
        "org.opcfoundation.ua.avro.VariantDateTimeScalar",
        "org.opcfoundation.ua.avro.VariantDateTimeArray",
        "org.opcfoundation.ua.avro.VariantDateTimeMatrixBody",
        "org.opcfoundation.ua.avro.VariantGuidScalar",
        "org.opcfoundation.ua.avro.VariantGuidArray",
        "org.opcfoundation.ua.avro.VariantGuidMatrixBody",
        "org.opcfoundation.ua.avro.VariantByteStringScalar",
        "org.opcfoundation.ua.avro.VariantByteStringArray",
        "org.opcfoundation.ua.avro.VariantByteStringMatrixBody",
        "org.opcfoundation.ua.avro.VariantXmlElementScalar",
        "org.opcfoundation.ua.avro.VariantXmlElementArray",
        "org.opcfoundation.ua.avro.VariantXmlElementMatrixBody",
        "org.opcfoundation.ua.avro.VariantNodeIdScalar",
        "org.opcfoundation.ua.avro.VariantNodeIdArray",
        "org.opcfoundation.ua.avro.VariantNodeIdMatrixBody",
        "org.opcfoundation.ua.avro.VariantExpandedNodeIdScalar",
        "org.opcfoundation.ua.avro.VariantExpandedNodeIdArray",
        "org.opcfoundation.ua.avro.VariantExpandedNodeIdMatrixBody",
        "org.opcfoundation.ua.avro.VariantStatusCodeScalar",
        "org.opcfoundation.ua.avro.VariantStatusCodeArray",
        "org.opcfoundation.ua.avro.VariantStatusCodeMatrixBody",
        "org.opcfoundation.ua.avro.VariantQualifiedNameScalar",
        "org.opcfoundation.ua.avro.VariantQualifiedNameArray",
        "org.opcfoundation.ua.avro.VariantQualifiedNameMatrixBody",
        "org.opcfoundation.ua.avro.VariantLocalizedTextScalar",
        "org.opcfoundation.ua.avro.VariantLocalizedTextArray",
        "org.opcfoundation.ua.avro.VariantLocalizedTextMatrixBody",
        "org.opcfoundation.ua.avro.VariantExtensionObjectScalar",
        "org.opcfoundation.ua.avro.VariantExtensionObjectArray",
        "org.opcfoundation.ua.avro.VariantExtensionObjectMatrixBody"
      ]
    }
  ],
  "name": "Variant",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

**Example value** (`variant_matrix_int`)

```json
{"dimensions": [2, 2], "value": [1, 2, 3, 4], "vtype": {"id": 6}}
```

**Encoded bytes** (17 bytes)

```text
0c02040404002404040400080204060800
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `0c` | $.builtInType: int = 6 |
| 1 | 1 | `02` | $.dimensions: union branch index = 1 |
| 2 | 1 | `04` | $.dimensions: branch 1 (array): array block 0 count = 2 |
| 3 | 1 | `04` | $.dimensions: branch 1 (array)[0]: int = 2 |
| 4 | 1 | `04` | $.dimensions: branch 1 (array)[1]: int = 2 |
| 5 | 1 | `00` | $.dimensions: branch 1 (array): array block 1 count = 0 |
| 6 | 1 | `24` | $.body: union branch index = 18 |
| 7 | 1 | `04` | $.body: branch 18 (org.opcfoundation.ua.avro.VariantInt32MatrixBody).matrix.dimensions: array block 0 count = 2 |
| 8 | 1 | `04` | $.body: branch 18 (org.opcfoundation.ua.avro.VariantInt32MatrixBody).matrix.dimensions[0]: int = 2 |
| 9 | 1 | `04` | $.body: branch 18 (org.opcfoundation.ua.avro.VariantInt32MatrixBody).matrix.dimensions[1]: int = 2 |
| 10 | 1 | `00` | $.body: branch 18 (org.opcfoundation.ua.avro.VariantInt32MatrixBody).matrix.dimensions: array block 1 count = 0 |
| 11 | 1 | `08` | $.body: branch 18 (org.opcfoundation.ua.avro.VariantInt32MatrixBody).matrix.values: array block 0 count = 4 |
| 12 | 1 | `02` | $.body: branch 18 (org.opcfoundation.ua.avro.VariantInt32MatrixBody).matrix.values[0]: int = 1 |
| 13 | 1 | `04` | $.body: branch 18 (org.opcfoundation.ua.avro.VariantInt32MatrixBody).matrix.values[1]: int = 2 |
| 14 | 1 | `06` | $.body: branch 18 (org.opcfoundation.ua.avro.VariantInt32MatrixBody).matrix.values[2]: int = 3 |
| 15 | 1 | `08` | $.body: branch 18 (org.opcfoundation.ua.avro.VariantInt32MatrixBody).matrix.values[3]: int = 4 |
| 16 | 1 | `00` | $.body: branch 18 (org.opcfoundation.ua.avro.VariantInt32MatrixBody).matrix.values: array block 1 count = 0 |

### Built-in DiagnosticInfo

**SchemaId** `1f23716837bba69d`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `value` | `{"fields": [{"default": null, "name": "symbolicId", "type": ["null", "int"]}, {"default": null, "name": "namespaceUri", "type": ["null", "int"]}, {"default": null, "name": "locale", "type": ["null", "int"]}, {"default": null, "name": "localizedText", "type": ["null", "int"]}, {"default": null, "name": "additionalInfo", "type": ["null", "string"]}, {"default": null, "name": "innerStatusCode", "type": ["null", "int"]}, {"default": null, "name": "innerDiagnosticInfo", "type": ["null", "DiagnosticInfo"]}], "name": "DiagnosticInfo", "namespace": "org.opcfoundation.ua.avro", "type": "record"}` | nullable where schema is a null union | OPC UA BuiltInType 25. |

**Avro schema fragment**

```json
{
  "fields": [
    {
      "default": null,
      "name": "symbolicId",
      "type": [
        "null",
        "int"
      ]
    },
    {
      "default": null,
      "name": "namespaceUri",
      "type": [
        "null",
        "int"
      ]
    },
    {
      "default": null,
      "name": "locale",
      "type": [
        "null",
        "int"
      ]
    },
    {
      "default": null,
      "name": "localizedText",
      "type": [
        "null",
        "int"
      ]
    },
    {
      "default": null,
      "name": "additionalInfo",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "default": null,
      "name": "innerStatusCode",
      "type": [
        "null",
        "int"
      ]
    },
    {
      "default": null,
      "name": "innerDiagnosticInfo",
      "type": [
        "null",
        "DiagnosticInfo"
      ]
    }
  ],
  "name": "DiagnosticInfo",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

**Example value** (`diaginfo_nested`)

```json
{"additional_info": "outer", "inner_diagnostic_info": {"additional_info": "inner", "inner_diagnostic_info": null, "inner_status_code": null, "locale": 5, "localized_text": null, "namespace_uri": null, "symbolic_id": null}, "inner_status_code": {"value": 2158755840}, "locale": null, "localized_text": null, "namespace_uri": 2, "symbolic_id": 1}
```

**Encoded bytes** (34 bytes)

```text
020202040000020a6f7574657202ffff9ff50f020000020a00020a696e6e65720000
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $.symbolicId: union branch index = 1 |
| 1 | 1 | `02` | $.symbolicId: branch 1 (int): int = 1 |
| 2 | 1 | `02` | $.namespaceUri: union branch index = 1 |
| 3 | 1 | `04` | $.namespaceUri: branch 1 (int): int = 2 |
| 4 | 1 | `00` | $.locale: union branch index = 0 |
| 5 | 0 | `—` | $.locale: branch 0 (null): null |
| 5 | 1 | `00` | $.localizedText: union branch index = 0 |
| 6 | 0 | `—` | $.localizedText: branch 0 (null): null |
| 6 | 1 | `02` | $.additionalInfo: union branch index = 1 |
| 7 | 1 | `0a` | $.additionalInfo: branch 1 (string): string length = 5 |
| 8 | 5 | `6f 75 74 65 72` | $.additionalInfo: branch 1 (string): string data |
| 13 | 1 | `02` | $.innerStatusCode: union branch index = 1 |
| 14 | 5 | `ff ff 9f f5 0f` | $.innerStatusCode: branch 1 (int): int = -2136211456 |
| 19 | 1 | `02` | $.innerDiagnosticInfo: union branch index = 1 |
| 20 | 1 | `00` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).symbolicId: union branch index = 0 |
| 21 | 0 | `—` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).symbolicId: branch 0 (null): null |
| 21 | 1 | `00` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).namespaceUri: union branch index = 0 |
| 22 | 0 | `—` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).namespaceUri: branch 0 (null): null |
| 22 | 1 | `02` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).locale: union branch index = 1 |
| 23 | 1 | `0a` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).locale: branch 1 (int): int = 5 |
| 24 | 1 | `00` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).localizedText: union branch index = 0 |
| 25 | 0 | `—` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).localizedText: branch 0 (null): null |
| 25 | 1 | `02` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).additionalInfo: union branch index = 1 |
| 26 | 1 | `0a` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).additionalInfo: branch 1 (string): string length = 5 |
| 27 | 5 | `69 6e 6e 65 72` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).additionalInfo: branch 1 (string): string data |
| 32 | 1 | `00` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).innerStatusCode: union branch index = 0 |
| 33 | 0 | `—` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).innerStatusCode: branch 0 (null): null |
| 33 | 1 | `00` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).innerDiagnosticInfo: union branch index = 0 |
| 34 | 0 | `—` | $.innerDiagnosticInfo: branch 1 (org.opcfoundation.ua.avro.DiagnosticInfo).innerDiagnosticInfo: branch 0 (null): null |

### One-dimensional array

**SchemaId** `fe961155c29ee867`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `array` | `["null", {"items": ["null", "string"], "type": "array"}]` | array nullable at top level | Array: nullable String elements, preserves null array elements. |
| `items` | `["null", "string"]` | per element as configured | Avro array blocks are count-prefixed and zero-terminated. |

**Avro schema fragment**

```json
[
  "null",
  {
    "items": [
      "null",
      "string"
    ],
    "type": "array"
  }
]
```

**Example value** (`array_string_with_nulls`)

```json
["a", null, ""]
```

**Encoded bytes** (9 bytes)

```text
020602026100020000
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $: union branch index = 1 |
| 1 | 1 | `06` | $: branch 1 (array): array block 0 count = 3 |
| 2 | 1 | `02` | $: branch 1 (array)[0]: union branch index = 1 |
| 3 | 1 | `02` | $: branch 1 (array)[0]: branch 1 (string): string length = 1 |
| 4 | 1 | `61` | $: branch 1 (array)[0]: branch 1 (string): string data |
| 5 | 1 | `00` | $: branch 1 (array)[1]: union branch index = 0 |
| 6 | 0 | `—` | $: branch 1 (array)[1]: branch 0 (null): null |
| 6 | 1 | `02` | $: branch 1 (array)[2]: union branch index = 1 |
| 7 | 1 | `00` | $: branch 1 (array)[2]: branch 1 (string): string length = 0 |
| 8 | 0 | `—` | $: branch 1 (array)[2]: branch 1 (string): string data |
| 8 | 1 | `00` | $: branch 1 (array): array block 1 count = 0 |

### Matrix

**SchemaId** `2ffc7ee0a94fbeb3`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `dimensions` | `{"items": "int", "type": "array"}` | record field | Matrix dimensions then row-major values. |
| `values` | `{"items": ["null", "double"], "type": "array"}` | record field | Matrix dimensions then row-major values. |

**Avro schema fragment**

```json
[
  "null",
  {
    "fields": [
      {
        "name": "dimensions",
        "type": {
          "items": "int",
          "type": "array"
        }
      },
      {
        "name": "values",
        "type": {
          "items": [
            "null",
            "double"
          ],
          "type": "array"
        }
      }
    ],
    "name": "TopMatrixOfDouble",
    "namespace": "org.opcfoundation.ua.avro",
    "type": "record"
  }
]
```

**Example value** (`matrix_double_2x2_special`)

```json
{"dimensions": [2, 2], "values": [1.0, "NaN", "-Infinity", -0.0]}
```

**Encoded bytes** (43 bytes)

```text
02040404000802000000000000f03f02000000000000f87f02000000000000f0ff02000000000000008000
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $: union branch index = 1 |
| 1 | 1 | `04` | $: branch 1 (org.opcfoundation.ua.avro.TopMatrixOfDouble).dimensions: array block 0 count = 2 |
| 2 | 1 | `04` | $: branch 1 (org.opcfoundation.ua.avro.TopMatrixOfDouble).dimensions[0]: int = 2 |
| 3 | 1 | `04` | $: branch 1 (org.opcfoundation.ua.avro.TopMatrixOfDouble).dimensions[1]: int = 2 |
| 4 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.TopMatrixOfDouble).dimensions: array block 1 count = 0 |
| 5 | 1 | `08` | $: branch 1 (org.opcfoundation.ua.avro.TopMatrixOfDouble).values: array block 0 count = 4 |
| 6 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.TopMatrixOfDouble).values[0]: union branch index = 1 |
| 7 | 8 | `00 00 00 00 00 00 f0 3f` | $: branch 1 (org.opcfoundation.ua.avro.TopMatrixOfDouble).values[0]: branch 1 (double): float64 little-endian |
| 15 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.TopMatrixOfDouble).values[1]: union branch index = 1 |
| 16 | 8 | `00 00 00 00 00 00 f8 7f` | $: branch 1 (org.opcfoundation.ua.avro.TopMatrixOfDouble).values[1]: branch 1 (double): float64 little-endian |
| 24 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.TopMatrixOfDouble).values[2]: union branch index = 1 |
| 25 | 8 | `00 00 00 00 00 00 f0 ff` | $: branch 1 (org.opcfoundation.ua.avro.TopMatrixOfDouble).values[2]: branch 1 (double): float64 little-endian |
| 33 | 1 | `02` | $: branch 1 (org.opcfoundation.ua.avro.TopMatrixOfDouble).values[3]: union branch index = 1 |
| 34 | 8 | `00 00 00 00 00 00 00 80` | $: branch 1 (org.opcfoundation.ua.avro.TopMatrixOfDouble).values[3]: branch 1 (double): float64 little-endian |
| 42 | 1 | `00` | $: branch 1 (org.opcfoundation.ua.avro.TopMatrixOfDouble).values: array block 1 count = 0 |

### Structure

**SchemaId** `088588111c53429d`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `X` | `"double"` | present | Plain structure: record fields in DataTypeDefinition order. |
| `Y` | `"double"` | present | Plain structure: record fields in DataTypeDefinition order. |

**Avro schema fragment**

```json
{
  "fields": [
    {
      "name": "X",
      "type": "double"
    },
    {
      "name": "Y",
      "type": "double"
    }
  ],
  "name": "Point",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

**Example value** (`struct_point`)

```json
{"fields": {"X": 1.25, "Y": -3.5}, "type_name": "Point"}
```

**Encoded bytes** (16 bytes)

```text
000000000000f43f0000000000000cc0
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 8 | `00 00 00 00 00 00 f4 3f` | $.X: float64 little-endian |
| 8 | 8 | `00 00 00 00 00 00 0c c0` | $.Y: float64 little-endian |

### Structure with optional fields

**SchemaId** `87352c988d4b795d`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `Name` | `["null", "string"]` | optional wrapper | Optional wrapper distinguishes absent from present-null. |
| `Age` | `"int"` | present | Optional wrapper distinguishes absent from present-null. |
| `Email` | `["null", {"fields": [{"name": "value", "type": ["null", "string"]}], "name": "Person_Email_Optional", "namespace": "org.opcfoundation.ua.avro", "type": "record"}]` | optional wrapper | Optional wrapper distinguishes absent from present-null. |
| `Nickname` | `["null", {"fields": [{"name": "value", "type": ["null", "string"]}], "name": "Person_Nickname_Optional", "namespace": "org.opcfoundation.ua.avro", "type": "record"}]` | optional wrapper | Optional wrapper distinguishes absent from present-null. |

**Avro schema fragment**

```json
{
  "fields": [
    {
      "name": "Name",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "name": "Age",
      "type": "int"
    },
    {
      "default": null,
      "name": "Email",
      "type": [
        "null",
        {
          "fields": [
            {
              "name": "value",
              "type": [
                "null",
                "string"
              ]
            }
          ],
          "name": "Person_Email_Optional",
          "namespace": "org.opcfoundation.ua.avro",
          "type": "record"
        }
      ]
    },
    {
      "default": null,
      "name": "Nickname",
      "type": [
        "null",
        {
          "fields": [
            {
              "name": "value",
              "type": [
                "null",
                "string"
              ]
            }
          ],
          "name": "Person_Nickname_Optional",
          "namespace": "org.opcfoundation.ua.avro",
          "type": "record"
        }
      ]
    }
  ],
  "name": "Person",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

**Example value** (`struct_person_present_null`)

```json
{"fields": {"Age": 9, "Email": null, "Name": "Zed"}, "type_name": "Person"}
```

**Encoded bytes** (9 bytes)

```text
02065a656412020000
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $.Name: union branch index = 1 |
| 1 | 1 | `06` | $.Name: branch 1 (string): string length = 3 |
| 2 | 3 | `5a 65 64` | $.Name: branch 1 (string): string data |
| 5 | 1 | `12` | $.Age: int = 9 |
| 6 | 1 | `02` | $.Email: union branch index = 1 |
| 7 | 1 | `00` | $.Email: branch 1 (org.opcfoundation.ua.avro.Person_Email_Optional).value: union branch index = 0 |
| 8 | 0 | `—` | $.Email: branch 1 (org.opcfoundation.ua.avro.Person_Email_Optional).value: branch 0 (null): null |
| 8 | 1 | `00` | $.Nickname: union branch index = 0 |
| 9 | 0 | `—` | $.Nickname: branch 0 (null): null |

### Union

**SchemaId** `f906a398dbbd6787`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `switch` | `["null", "string"]` | optional wrapper | Union record: switch field plus record-wrapped selected value. |
| `value` | `["null", {"fields": [{"name": "AsInt", "type": "int"}], "name": "Measurement_AsInt_Branch", "namespace": "org.opcfoundation.ua.avro", "type": "record"}, {"fields": [{"name": "AsText", "type": ["null", "string"]}], "name": "Measurement_AsText_Branch", "namespace": "org.opcfoundation.ua.avro", "type": "record"}, {"fields": [{"name": "AsPoint", "type": "org.opcfoundation.ua.avro.Point"}], "name": "Measurement_AsPoint_Branch", "namespace": "org.opcfoundation.ua.avro", "type": "record"}]` | optional wrapper | Union record: switch field plus record-wrapped selected value. |

**Avro schema fragment**

```json
{
  "fields": [
    {
      "default": null,
      "name": "switch",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "default": null,
      "name": "value",
      "type": [
        "null",
        {
          "fields": [
            {
              "name": "AsInt",
              "type": "int"
            }
          ],
          "name": "Measurement_AsInt_Branch",
          "namespace": "org.opcfoundation.ua.avro",
          "type": "record"
        },
        {
          "fields": [
            {
              "name": "AsText",
              "type": [
                "null",
                "string"
              ]
            }
          ],
          "name": "Measurement_AsText_Branch",
          "namespace": "org.opcfoundation.ua.avro",
          "type": "record"
        },
        {
          "fields": [
            {
              "name": "AsPoint",
              "type": "org.opcfoundation.ua.avro.Point"
            }
          ],
          "name": "Measurement_AsPoint_Branch",
          "namespace": "org.opcfoundation.ua.avro",
          "type": "record"
        }
      ]
    }
  ],
  "name": "Measurement",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

**Example value** (`union_point`)

```json
{"field_name": "AsPoint", "value": {"fields": {"X": 9.0, "Y": 8.0}, "type_name": "Point"}}
```

**Encoded bytes** (26 bytes)

```text
020e4173506f696e740600000000000022400000000000002040
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $.switch: union branch index = 1 |
| 1 | 1 | `0e` | $.switch: branch 1 (string): string length = 7 |
| 2 | 7 | `41 73 50 6f 69 6e 74` | $.switch: branch 1 (string): string data |
| 9 | 1 | `06` | $.value: union branch index = 3 |
| 10 | 8 | `00 00 00 00 00 00 22 40` | $.value: branch 3 (org.opcfoundation.ua.avro.Measurement_AsPoint_Branch).AsPoint.X: float64 little-endian |
| 18 | 8 | `00 00 00 00 00 00 20 40` | $.value: branch 3 (org.opcfoundation.ua.avro.Measurement_AsPoint_Branch).AsPoint.Y: float64 little-endian |

### Worked structured DataType: Envelope

**SchemaId** `d5b98856c5cee45e`

| Field | Avro type | Presence / nullability | Notes |
|---|---|---|---|
| `Id` | `["null", "string"]` | optional wrapper | Nested structure with array and subtyped ExtensionObject payload. |
| `Location` | `"org.opcfoundation.ua.avro.Point"` | present | Nested structure with array and subtyped ExtensionObject payload. |
| `Tags` | `{"items": ["null", "string"], "type": "array"}` | present | Nested structure with array and subtyped ExtensionObject payload. |
| `Payload` | `["null", "org.opcfoundation.ua.avro.ExtensionObject"]` | optional wrapper | Nested structure with array and subtyped ExtensionObject payload. |

**Avro schema fragment**

```json
{
  "fields": [
    {
      "name": "Id",
      "type": [
        "null",
        "string"
      ]
    },
    {
      "name": "Location",
      "type": "org.opcfoundation.ua.avro.Point"
    },
    {
      "name": "Tags",
      "type": {
        "items": [
          "null",
          "string"
        ],
        "type": "array"
      }
    },
    {
      "name": "Payload",
      "type": [
        "null",
        "org.opcfoundation.ua.avro.ExtensionObject"
      ]
    }
  ],
  "name": "Envelope",
  "namespace": "org.opcfoundation.ua.avro",
  "type": "record"
}
```

**Example value** (`envelope`)

```json
{"fields": {"Id": "E1", "Location": {"fields": {"X": 0.0, "Y": 0.0}, "type_name": "Point"}, "Payload": {"body": {"fields": {"X": 2.0, "Y": 3.0}, "type_name": "Point"}, "type_id": {"id_type": 0, "identifier": 3001, "namespace": 0}}, "Tags": ["x", null, "z"]}, "type_name": "Envelope"}
```

**Encoded bytes** (55 bytes)

```text
0204453100000000000000000000000000000000060202780002027a0002000002f22e0000000200000000000000400000000000000840
```

**Annotated byte-level breakdown**

| Offset | Len | Bytes | Field |
|---:|---:|---|---|
| 0 | 1 | `02` | $.Id: union branch index = 1 |
| 1 | 1 | `04` | $.Id: branch 1 (string): string length = 2 |
| 2 | 2 | `45 31` | $.Id: branch 1 (string): string data |
| 4 | 8 | `00 00 00 00 00 00 00 00` | $.Location.X: float64 little-endian |
| 12 | 8 | `00 00 00 00 00 00 00 00` | $.Location.Y: float64 little-endian |
| 20 | 1 | `06` | $.Tags: array block 0 count = 3 |
| 21 | 1 | `02` | $.Tags[0]: union branch index = 1 |
| 22 | 1 | `02` | $.Tags[0]: branch 1 (string): string length = 1 |
| 23 | 1 | `78` | $.Tags[0]: branch 1 (string): string data |
| 24 | 1 | `00` | $.Tags[1]: union branch index = 0 |
| 25 | 0 | `—` | $.Tags[1]: branch 0 (null): null |
| 25 | 1 | `02` | $.Tags[2]: union branch index = 1 |
| 26 | 1 | `02` | $.Tags[2]: branch 1 (string): string length = 1 |
| 27 | 1 | `7a` | $.Tags[2]: branch 1 (string): string data |
| 28 | 1 | `00` | $.Tags: array block 1 count = 0 |
| 29 | 1 | `02` | $.Payload: union branch index = 1 |
| 30 | 1 | `00` | $.Payload: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.namespace: int = 0 |
| 31 | 1 | `00` | $.Payload: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.idType: int = 0 |
| 32 | 1 | `02` | $.Payload: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.numeric: union branch index = 1 |
| 33 | 2 | `f2 2e` | $.Payload: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.numeric: branch 1 (long): long = 3001 |
| 35 | 1 | `00` | $.Payload: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.string: union branch index = 0 |
| 36 | 0 | `—` | $.Payload: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.string: branch 0 (null): null |
| 36 | 1 | `00` | $.Payload: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.guid: union branch index = 0 |
| 37 | 0 | `—` | $.Payload: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.guid: branch 0 (null): null |
| 37 | 1 | `00` | $.Payload: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.opaque: union branch index = 0 |
| 38 | 0 | `—` | $.Payload: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).typeId.opaque: branch 0 (null): null |
| 38 | 1 | `02` | $.Payload: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).body: union branch index = 1 |
| 39 | 8 | `00 00 00 00 00 00 00 40` | $.Payload: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).body: branch 1 (org.opcfoundation.ua.avro.Point).X: float64 little-endian |
| 47 | 8 | `00 00 00 00 00 00 08 40` | $.Payload: branch 1 (org.opcfoundation.ua.avro.ExtensionObject).body: branch 1 (org.opcfoundation.ua.avro.Point).Y: float64 little-endian |
<!-- END GENERATED: type-reference -->
