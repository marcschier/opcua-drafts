# OPC UA Part 14 Apache Arrow PubSub Message Mapping

**Working draft for submission to the OPC Foundation Working Group**  
**Proposed insertion:** OPC 10000-14 v1.05.06, new `7.2.8 Arrow message mapping`  
**Version:** 0.1.0 · **Date:** 2026-07-02

> **Status — working draft.** This document specifies a columnar Arrow message mapping for OPC UA PubSub. A NetworkMessage is an Arrow IPC stream or file containing one or more RecordBatches; each row is a DataSetMessage sample and each column is a DataSet field encoded with the Part 6 Arrow DataType mapping.

## 1 Scope

This mapping defines how PubSub NetworkMessages and DataSetMessages are represented using Apache Arrow. It is optimized for analytics and historian consumers that benefit from columnar batches while preserving OPC UA PubSub metadata and the exact Part 6 value mapping.

## 2 Overview

An Arrow NetworkMessage is an Arrow IPC stream whose schema describes one PublishedDataSet. Each RecordBatch contains zero or more DataSetMessage rows. A single DataSetMessage is a one-row RecordBatch. Key frames carry a full set of DataSet fields. Delta frames carry only changed fields, either as a batch with nullable omitted columns and a field-index selection column or as a selection RecordBatch whose columns are the changed field subset.

The batching advantage is that many samples from the same DataSet can be transmitted in one message: timestamps, status values and field values become cache-friendly columns, and subscribers can process a batch without per-sample decoding overhead.

## 3 Insertion into OPC 10000-14 v1.05.06

Insert a new message mapping `7.2.8 Arrow message mapping` after the existing message mappings, mirroring the structure of `7.2.5 JSON message mapping`. Add configuration parameters in `6.3.x`, configuration model entries in `9.2.x`, header layout descriptions in `Annex A.x`, and content-type entries in `7.3.4.x` and `Annex B`.

### 6.3.x Arrow mapping parameters

The WriterGroup MessageSettings for the Arrow mapping shall include: `ArrowIpcFormat` (`stream` or `file`, default `stream`), `MaxRowsPerRecordBatch`, `IncludeSchemaMetadata`, `DeltaFrameMode` (`nullable-columns` or `selected-columns`), and `Compression` (`none` or an Arrow IPC-supported codec). The DataSetWriter MessageSettings shall identify the DataSet schema version and whether DataSet fields are represented as RawData, Variant or DataValue according to `DataSetFieldContentMask`.

### 7.2.8 Arrow message mapping

The payload of an Arrow NetworkMessage shall be an Arrow IPC stream (`application/vnd.apache.arrow.stream`) or Arrow IPC file (`application/vnd.apache.arrow.file`). The stream schema contains one column per DataSet field, using the OPC UA Part 6 Arrow mapping for that field DataType. Schema metadata carries NetworkMessage header fields such as PublisherId, WriterGroupId, DataSetWriterId, NetworkMessageNumber, SequenceNumber, ConfigurationVersion, MessageType, Timestamp, PicoSeconds, PromotedFields and security-related flags when present.

Each RecordBatch row is one DataSetMessage sample for the DataSet. Columns are DataSet fields. If `DataSetFieldContentMask` selects RawData, the column type is the field DataType mapping. If it selects Variant, the column type is the Part 6 Variant mapping. If it selects DataValue, the column type is the Part 6 DataValue mapping. The selected representation shall be the same for every row in the batch.

Key frames shall contain all fields in DataSetMetaData field order. Delta frames shall identify changed fields using a `field_index:list<uint16>` selection column, a schema-level changed-field list, or a selected-column RecordBatch whose metadata lists the original field indexes. Omitted unchanged fields shall not be decoded as null values; they are absent by delta-frame selection.

### 7.3.4.x Content types

The Arrow IPC stream content type shall be `application/vnd.apache.arrow.stream`. The Arrow IPC file content type shall be `application/vnd.apache.arrow.file`. Transports that expose MIME content types shall use these values for Arrow PubSub messages.

### 9.2.x Configuration model

The PubSub configuration model shall describe an Arrow message mapping option for WriterGroup and DataSetWriter MessageSettings. The described-only configuration nodes reference the `Default Arrow` DataTypeEncoding from Part 6 and the schema generated from DataSetMetaData. Final BrowseNames and NodeIds are assigned by the OPC Foundation.

### Annex A.x Header layouts

Arrow NetworkMessage header fields shall be represented as schema metadata key-value pairs when they apply to the whole stream or batch, and as columns when they vary per row. DataSetMessage header fields that vary per sample, such as status, timestamp, picoSeconds or sequence number, shall be represented as leading metadata columns before DataSet field columns.

### Annex B Arrow content type entries

Annex B shall list `application/vnd.apache.arrow.stream` for Arrow IPC streaming PubSub payloads and `application/vnd.apache.arrow.file` for bounded Arrow IPC file payloads.

## 4 DataSet schema mapping

A PublishedDataSet maps to one Arrow schema. For each `FieldMetaData` entry, the field name becomes the Arrow column name and the field DataType becomes the Arrow column `DataType` using OPC UA Part 6 Arrow. Field properties from DataSetMetaData are copied into Arrow field metadata so a disconnected subscriber can retain engineering units, semantic references, model namespace, SourceBrowseName and SourceTypeDefinition.

## 5 NetworkMessage and DataSetMessage envelopes

The canonical envelope is an IPC stream with schema metadata for NetworkMessage-level values and RecordBatch rows for DataSetMessages. A bridge may wrap multiple DataSet schemas in a transport-level envelope, but each Arrow IPC stream schema shall describe exactly one DataSet schema to preserve column homogeneity.

### 5.1 Schema resolution

Arrow is schema-based: the Arrow schema of the IPC stream is required to decode the batch. The reference schema is published to, and resolved from, a central catalog as defined by *OPC UA — xRegistry Schema Catalog* (`../xregistry-catalog/OPC-UA-xRegistry-Schema-Catalog.md`). While an Arrow IPC stream embeds its own schema in the stream header (so a message is self-contained once received), a subscriber that must decode before receiving the stream — or that validates against a governed schema — resolves it from the DataSet namespace, `<DataSetName>:arrow`, and the `ConfigurationVersion`, per §6 of that specification. The transport `content-type` (`application/vnd.apache.arrow.stream` or `application/vnd.apache.arrow.file`) selects the format.

## 6 Conformance

An Arrow PubSub publisher conforms when it emits RecordBatches whose columns use the Part 6 Arrow mapping, whose rows reconstruct the intended DataSetMessages, and whose key-frame and delta-frame rules preserve null-vs-absent semantics. A subscriber conforms when it reconstructs DataSet field values with the same Part 6 reversibility guarantees and uses DataSetMetaData plus Arrow schema metadata to interpret the batch.
