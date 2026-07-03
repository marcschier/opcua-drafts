# OPC UA Part 14 — Apache Avro PubSub Message Mapping

**Working draft for submission to the OPC Foundation Working Group**
**Proposed addition to:** OPC 10000-14 PubSub v1.05.06
**Namespace:** `http://opcfoundation.org/UA/` (base OPC UA namespace)
**Version:** 0.1.0 · **Date:** 2026-07-02

> **Status — working draft.** This document proposes an Apache Avro binary message mapping for OPC UA PubSub. It depends on the Default Avro DataEncoding defined in `OPC-UA-Part6-Avro-DataEncoding.md` and describes only the mapping and configuration additions; no NodeSet or assigned NodeIds are shipped in this draft.

---

## 1 Scope

This specification defines a PubSub NetworkMessage and DataSetMessage mapping using Apache Avro binary encoding. It covers data key frame messages, data delta frame messages, field representation according to `DataSetFieldContentMask`, message header fields, configuration parameters and transport content type metadata for MQTT, AMQP and Kafka.

This specification does not change PubSub discovery, security, writer group semantics, dataset metadata semantics or transport bindings except where content type metadata identifies Avro payloads.

## 2 Normative references

- [OPC 10000-6 v1.05.07](https://reference.opcfoundation.org/specs/OPC-10000-6/) — Mappings and the Default Avro DataEncoding addition.
- [OPC 10000-14 v1.05.06](https://reference.opcfoundation.org/specs/OPC-10000-14/) — PubSub.
- [Apache Avro Specification](https://avro.apache.org/docs/) — Schemas and binary encoding.

## 3 Terms, definitions and abbreviations

| Term | Definition |
|---|---|
| Avro NetworkMessage | A PubSub NetworkMessage whose headers and payload are encoded with the canonical Avro schema defined here. |
| Avro DataSetMessage | A DataSetMessage encoded as an Avro record, either key frame or delta frame. |
| RawData field | A DataSet field encoded using the Default Avro schema for the field DataType rather than Variant or DataValue wrapping. |
| SchemaId | A stable identifier for the Avro schema or schema bundle used by a WriterGroup or DataSetWriter. |

## 4 Overview

The Avro message mapping uses one canonical Avro schema for the NetworkMessage envelope and one canonical schema for each DataSetMessage shape. The schema is derived from PubSub configuration and DataSetMetaData. A receiver shall know the writer configuration and schema identifier before decoding, either from configured PubSub metadata, a schema registry, an AddressSpace re-derivation or a negotiated out-of-band catalog such as `core-specs\xregistry-catalog\`.

Each value or message shall reference its schema by SchemaId. The SchemaId is the CRC-64-AVRO Rabin fingerprint over the Avro Parsing Canonical Form of the self-contained schema, with every referenced named type defined inline at its first occurrence, represented in the little-endian byte order used by Avro single-object encoding. SchemaId derivation is independent of PubSub ConfigurationVersion: ConfigurationVersion tracks PubSub metadata versioning, while SchemaId identifies the exact Avro schema bytes needed to decode a payload.

The transport content type shall be `application/vnd.apache.avro`. A PubSub-specific parameter should identify this mapping, for example `application/vnd.apache.avro; opcua=pubsub; encoding=binary`.

## 5 NetworkMessage

An Avro NetworkMessage shall be an Avro record with the selected PubSub header fields represented as nullable Avro fields and a `payload` array of DataSetMessage records. Header fields that are disabled by the NetworkMessageContentMask shall be null or omitted according to the canonical schema for the configured writer group; enabled fields shall be present. The following fields are defined for the canonical envelope: PublisherId, DataSetClassId, GroupHeader fields, WriterGroupId, GroupVersion, NetworkMessageNumber, SequenceNumber, Timestamp, PicoSeconds, PromotedFields and Payload.

The Payload field shall contain one or more Avro DataSetMessage records unless the transport mapping uses a single DataSetMessage without NetworkMessage wrapper by explicit configuration. When promoted fields are enabled, the values shall use Default Avro DataEncoding and shall preserve their configured DataTypes.

## 6 DataSetMessage

### 6.1 Common header

Each Avro DataSetMessage shall carry DataSetWriterId, DataSetMessage type, ConfigurationVersion, SequenceNumber, Status, Timestamp, PicoSeconds and message flags according to the DataSetMessageContentMask. Disabled header fields shall be nullable and default to null in the canonical schema. DataSetWriterId and message type are mandatory because they select the DataSetMetaData and frame interpretation.

### 6.2 Data key frame

A data key frame shall contain all fields defined by the PublishedDataSet in FieldMetaData order. The Avro payload field is an array or record whose members correspond exactly to that order. A key frame is self-contained for the current ConfigurationVersion.

### 6.3 Data delta frame

A data delta frame shall contain only changed fields. Each changed field entry shall carry the field index or field name and the encoded value. The canonical Avro representation is an array of records `{ "fieldIndex": int, "fieldName": ["null","string"], "value": FieldValue }`; fieldIndex is the normative selector and fieldName is optional diagnostic metadata when configured.

### 6.4 Field representation and DataSetFieldContentMask

If the DataSetFieldContentMask selects StatusCode, timestamps or picoseconds, the field shall be encoded as a DataValue using the Default Avro DataValue mapping. If it selects Value wrapped as Variant, the field shall be encoded as a Variant. If RawData is selected, the field shall be encoded directly with the published Default Avro `.avsc` schema for the FieldMetaData DataType, including array dimensions, nullable element rules, and optional-field wrapper records. RawData shall not be used when the field DataType is not known to the receiver schema.

Null field values shall be represented using the null branch of the field schema. A missing delta-frame field means unchanged, not null.

## 7 Configuration parameters

The Avro mapping adds the following configuration parameters to the JSON mapping style configuration model in Part 14:

| Parameter | Type | Description |
|---|---|---|
| `AvroSchemaId` | String | Stable identifier of the Avro schema bundle for the WriterGroup or DataSetWriter. |
| `AvroSchemaUri` | String | Optional URI from which the schema bundle can be retrieved. |
| `AvroUseObjectContainerFile` | Boolean | False for PubSub network payloads by default; true only for transports that explicitly carry Avro object container files. |
| `AvroRawDataAllowed` | Boolean | Whether RawData fields may be emitted for this writer. |
| `AvroSchemaHash` | ByteString | Optional copy of the little-endian CRC-64-AVRO SchemaId bytes for mismatch detection. |

## 8 SchemaId handshake

### 8.1 Framing

Single OPC UA values encoded with Default Avro should use Avro single-object encoding: the two magic bytes `0xC3 0x01`, followed by the 8-byte little-endian Rabin fingerprint, followed by the Avro binary body. The fingerprint bytes are the SchemaId. PubSub DataSetMessages or NetworkMessages that do not use single-object encoding shall carry the same SchemaId in the DataSetMessage header, NetworkMessage header, or transport metadata agreed for the mapping.

### 8.2 Schema announcements

A schema announcement frame shall contain `{ SchemaId, canonical Avro schema JSON }`, where the schema JSON is the self-contained Avro Parsing Canonical Form or a self-contained schema document that has exactly that Parsing Canonical Form. The announcement shall define every named type needed to parse the payload without external named-schema state. An encoder shall send the announcement once per SchemaId and destination, at stream start, on first use, or in response to a decoder request. The announcement is lightweight and independent of data frames.

### 8.3 Encoder change tracking

An encoder shall maintain `announced: set[SchemaId]` per destination. Before sending each value or message, it shall recompute the SchemaId from the generated self-contained Avro schema. If the SchemaId is not in the destination's announced set, the encoder shall emit the schema announcement before the first value using that SchemaId and then add it to the set. A changed DataType, referenced DataType, DataSet field list, field order, optional-field shape, Variant body type or RawData schema produces a different SchemaId and therefore automatically triggers a new announcement. An optional monotonic `SchemaEpoch` may be sent for operator correlation, but receivers shall not use it as the decoding key.

### 8.4 Decoder behavior

A decoder shall maintain `cache: SchemaId -> parsed Avro schema`. If a value references an unknown SchemaId, the decoder shall wait for an announcement, fetch the canonical schema from an xRegistry or schema registry by SchemaId, or re-derive the schema from the AddressSpace DataType and verify the derived SchemaId. A decoder may send `SchemaRequest(SchemaId)` when it joins late or detects a cache miss. Encoders should periodically re-announce active schemas on lossy transports or when late joiners are expected.

### 8.5 Relationship to ConfigurationVersion

SchemaId derives only from the Avro schema. It does not depend on PubSub ConfigurationVersion, writer group version numbers, sequence numbers or transport session state. A ConfigurationVersion change that does not alter the Avro schema keeps the same SchemaId. A schema change produces a new SchemaId even if a deployment accidentally fails to advance ConfigurationVersion; decoders shall use SchemaId to select the Avro decoder and may use ConfigurationVersion for the existing PubSub metadata checks.

## 9 Transport content types

For MQTT, the MQTT 5 `ContentType` property shall be `application/vnd.apache.avro; opcua=pubsub; encoding=binary`. For MQTT 3.1.1, the same string should be carried in configured metadata or topic documentation because the protocol has no ContentType property.

For AMQP, the message `content-type` property shall carry the same content type. For Kafka, a header named `content-type` or `Content-Type` shall carry the same value. Kafka and AMQP deployments that use a schema registry should also carry `opcua-avro-schema-id` with the configured SchemaId.

## 10 Information model additions

The PubSub configuration model would add Avro message mapping ObjectTypes parallel to the JSON message mapping configuration ObjectTypes. The model would describe Avro NetworkMessage mapping parameters, Avro DataSetMessage mapping parameters and the SchemaId/SchemaUri properties. This draft describes the ObjectTypes only; assigned NodeIds and a NodeSet are out of scope.

## 11 Insertion into OPC 10000-14 v1.05.06

| Draft section | Target in OPC 10000-14 | Notes |
|---|---|---|
| §7 Configuration parameters | New `6.3.x Avro message mapping parameters` | Add `AvroSchemaId`, `AvroSchemaUri`, object-container flag, RawData flag and schema hash. |
| §8 SchemaId handshake | New `7.2.6.x SchemaId handshake` | Defines single-object framing, schema announcements, cache misses, SchemaRequest and ConfigurationVersion independence. |
| §4-§6 Message mapping | New `7.2.6 Avro message mapping` | Mirrors `7.2.5 JSON message mapping` with Avro NetworkMessage, DataSetMessage, key frame and delta frame definitions. |
| §9 MQTT content type | New `7.3.4.x MQTT Avro content type` | Defines MQTT `ContentType` string. |
| §10 Configuration model | New `9.2.x Avro message mapping ObjectTypes` | Describes ObjectTypes and Properties only; no NodeSet in this draft. |
| §5-§6 Header fields | New `Annex A.x Avro header layouts` | Tables list NetworkMessage and DataSetMessage header fields and their Avro field names. |
| §9 Kafka/AMQP metadata | `Annex B` additions | Adds AMQP `content-type`, Kafka content-type header and optional schema-id header. |

The editor should place `7.2.6 Avro message mapping` after `7.2.5 JSON message mapping` so the Avro text can reuse the same PubSub concepts and masks while replacing JSON object representation with canonical Avro records.
