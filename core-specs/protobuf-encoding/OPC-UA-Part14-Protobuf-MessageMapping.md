# OPC UA Part 14 — Protobuf PubSub Message Mapping

**Working draft for submission to the OPC Foundation Working Group**
**Proposed addition to:** OPC 10000-14 PubSub v1.05.06
**Namespace:** `http://opcfoundation.org/UA/` (base OPC UA namespace)
**Version:** 0.1.0 · **Date:** 2026-07-02

> **Status — working draft.** This document proposes a PubSub NetworkMessage/DataSetMessage mapping that uses the OPC UA Protobuf DataEncoding defined for OPC 10000-6. NodeIds and configuration model entries are described only and provisional.

---

## 1 Scope

This document defines a Protobuf message mapping for OPC UA PubSub. It covers NetworkMessage and DataSetMessage headers, key frame and delta frame bodies, DataSet field representations selected by `DataSetFieldContentMask`, configuration parameters, transport content types and insertion points into OPC 10000-14 v1.05.06. The mapping is reversible with respect to the OPC UA DataValue, Variant and RawData field representations.

## 2 Normative references

- [OPC 10000-6](https://reference.opcfoundation.org/specs/OPC-10000-6/) v1.05.07 — Mappings and the Protobuf DataEncoding addition.
- [OPC 10000-14](https://reference.opcfoundation.org/specs/OPC-10000-14/) v1.05.06 — PubSub.
- [Protocol Buffers proto3 language specification](https://protobuf.dev/programming-guides/proto3/).

## 3 Terms, definitions and abbreviations

| Term | Definition |
|---|---|
| Protobuf NetworkMessage | The PubSub NetworkMessage encoded as a canonical proto3 message. |
| Protobuf DataSetMessage | A key frame or delta frame DataSetMessage encoded as a canonical proto3 message. |
| RawData | A DataSet field encoded with its declared field DataType rather than as a Variant or DataValue. |
| Key frame | A DataSetMessage carrying all configured DataSet fields. |
| Delta frame | A DataSetMessage carrying only changed fields and their field indexes or names. |

Key words **shall**, **should**, **may**, **shall not** are to be interpreted as in ISO/IEC directives.

## 4 Protobuf message mapping

### 4.1 General

The Protobuf message mapping shall use proto3 messages generated from the PubSub configuration and DataSetMetaData. A NetworkMessage contains header fields followed by zero or more DataSetMessage messages. A DataSetMessage is either a key frame or a delta frame. All OPC UA values inside field payloads shall use the Part 6 Protobuf DataEncoding, including explicit presence, nullable repeated wrappers, raw DateTime ticks, `uint64` UInt64 and Variant scalar/array/matrix identity.

The transport content type for a Protobuf NetworkMessage shall be `application/vnd.google.protobuf`; `application/x-protobuf` may be accepted by receivers for compatibility. If a transport supports parameters, the schema or message type parameter should identify the PubSub NetworkMessage schema, for example `type=opcua.protobuf.v1.NetworkMessage`.

### 4.2 NetworkMessage header

The Protobuf NetworkMessage shall carry the PubSubVersion, PublisherId when enabled, DataSetClassId when enabled by metadata, group header fields such as WriterGroupId and GroupVersion when enabled, NetworkMessageNumber and SequenceNumber when enabled, timestamp/status/security header data when enabled, and the repeated DataSetMessages. A header field disabled by the NetworkMessageContentMask shall be absent, not encoded as a default value. A present numeric header value of zero is distinct from an absent header value when the Part 14 header mask permits absence.

### 4.3 DataSetMessage header

The Protobuf DataSetMessage shall carry the DataSetWriterId, DataSetMessage sequence number, timestamp, status, configuration version, picoSeconds and message type flags according to the DataSetMessageContentMask. A boolean `delta_frame` or equivalent enum shall identify delta frames. Header fields disabled by the content mask shall be absent.

### 4.4 Key frame body

A key frame shall contain one field entry for every field in the DataSetMetaData in field order. Each field entry shall carry the field name or stable field index and exactly one representation selected by the DataSetFieldContentMask: DataValue, Variant or RawData. Receivers shall use DataSetMetaData to bind field order, field name, declared type and field flags.

### 4.5 Delta frame body

A delta frame shall contain only changed fields. Each changed field shall carry its stable DataSet field index or field name and exactly one representation selected by the DataSetFieldContentMask. Absence of a field in a delta frame means no change; a present field whose value is a null Variant, null array or null nullable scalar means the value changed to null.

### 4.6 DataSet field representation

| DataSetFieldContentMask selection | Protobuf field representation | Rule |
|---|---|---|
| DataValue | Part 6 Protobuf `DataValue` message | All DataValue members have independent presence. |
| Variant | Part 6 Protobuf `Variant` message | Type id, scalar/array/matrix shape and dimensions are explicit. |
| RawData | Part 6 Protobuf message for the declared DataType | The receiver obtains the declared DataType from DataSetMetaData; nullability uses the Part 6 rules. |

A mapping configuration shall select one representation for a DataSetWriter. Producers shall not mix representations for fields of the same DataSetMessage unless explicitly permitted by a future profile.

### 4.7 Configuration parameters

The PubSubConnection, WriterGroup, ReaderGroup, DataSetWriter and DataSetReader parameters for the Protobuf mapping mirror the JSON message mapping parameters. The following described-only parameters are added: `ProtobufNetworkMessageContentMask`, `ProtobufDataSetMessageContentMask`, `ProtobufDataSetFieldContentMask`, `ProtobufSchemaUri`, `ProtobufPackageName`, `ProtobufMessageName`, `ProtobufUseDeterministicSerialization` and `ProtobufAcceptXProtobufContentType`. Deterministic serialization should be enabled for files, examples and signatures; receivers shall not require byte-for-byte ordering where Protobuf semantics define field-order independence unless a security profile signs the bytes.

### 4.8 Configuration model

The configuration model shall add described-only VariableTypes and DataTypes parallel to the JSON message mapping configuration model. These nodes identify the Protobuf message mapping, content masks, schema identifiers and content types used by WriterGroups and ReaderGroups. The base namespace would add a Protobuf message mapping entry below the existing PubSub configuration model without changing existing Binary, JSON or UADP nodes.

### 4.9 Schema resolution

Protobuf is schema-based: a subscriber cannot decode a `DataSetMessage` without the `.proto` that describes it. The reference schema is published to, and resolved from, a central catalog as defined by *OPC UA — xRegistry Schema Catalog* (`../xregistry-catalog/OPC-UA-xRegistry-Schema-Catalog.md`). A Publisher sets `ProtobufSchemaUri` to the schema Version `self` URL; when it is absent, a subscriber resolves the schema from the DataSet namespace, `<DataSetName>:protobuf` (or the RawData DataType BrowseName), and the `ConfigurationVersion` carried in the DataSetMessage header, exactly as in §6 of that specification. The transport `content-type` selects the format.

## 5 Insertion into OPC 10000-14 v1.05.06

Insert a new clause **7.2.7 Protobuf message mapping** after **7.2.5 JSON message mapping** and the sibling **7.2.6 Avro message mapping** addition. Subclauses shall include **7.2.7.1 General**, **7.2.7.2 NetworkMessage**, **7.2.7.3 DataSetMessage**, **7.2.7.4 Key frame**, **7.2.7.5 Delta frame**, **7.2.7.6 DataSet field representation**, and **7.2.7.7 Error handling**.

Add configuration parameter clauses in **6.3.x** for `ProtobufNetworkMessageContentMask`, `ProtobufDataSetMessageContentMask`, `ProtobufDataSetFieldContentMask`, schema URI/package/message identifiers and deterministic serialization. Add configuration-model nodes in **9.2.x** for Protobuf WriterGroup/DataSetWriter and ReaderGroup/DataSetReader settings, described only until NodeIds are assigned. Add header layout diagrams/tables in **Annex A.x** for Protobuf NetworkMessage and DataSetMessage header presence. Add content-type entries in **7.3.4.x** and **Annex B** for `application/vnd.google.protobuf` and compatibility alias `application/x-protobuf`.

## 6 Error handling

A receiver shall treat the message as invalid if a required schema cannot be resolved, a field selects more than one representation, a RawData field cannot be decoded as the declared DataType, a delta frame lacks a field index/name, a matrix has an invalid dimensions/value count, an integer value is out of range for its OPC UA DataType, or an ExtensionObject body type id cannot be resolved and opaque forwarding is not supported.
