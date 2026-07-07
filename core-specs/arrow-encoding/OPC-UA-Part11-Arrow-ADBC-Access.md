# OPC UA Arrow Historian and ADBC Access Mapping

**Working draft for submission to the OPC Foundation Working Group**  
**Scope:** OPC UA Historical Access result mapping to Apache Arrow RecordBatch streams  
**Version:** 0.1.0 · **Date:** 2026-07-03

> **Status — working draft.** This document defines how OPC UA historical and data access results are exposed as Arrow for historian and analytical clients. It aligns with ADBC-style client APIs and reuses the Part 6 OPC UA Arrow value mapping. It does not define OPC UA Actions and does not define a new database protocol.

## 1 Scope

This mapping exposes OPC UA Historical Access results as Arrow IPC streams for clients that use an ADBC-like access pattern:

```text
Connection -> Statement -> ExecuteQuery -> ArrowArrayStream
```

ADBC (Arrow Database Connectivity) is a client API surface. Arrow Flight SQL is the natural Arrow wire transport for remote ADBC clients. This specification defines the OPC-UA-to-Arrow result mapping returned by such a surface; it is not a new database wire protocol and does not replace OPC UA services.

## 2 Access basis

The normative access basis is OPC 10000-11 Historical Access, especially `HistoryRead`.

The following HistoryRead details map to Arrow result sets:

- `ReadRawModifiedDetails` produces one row per raw or modified historical sample.
- `ReadProcessedDetails` produces one row per aggregate interval result.
- `ReadAtTimeDetails` produces one row per requested timestamp result.

The same Part 6 Arrow DataType mapping used for PubSub DataSet fields is used for the result `Value` column.

## 3 ADBC-style statement model

An implementation exposing this mapping shall provide an ADBC-style logical surface:

1. A `Connection` represents the OPC UA session, historian endpoint, or gateway context.
2. A `Statement` is parameterized with HistoryRead inputs.
3. `ExecuteQuery` returns an `ArrowArrayStream`, i.e. a stream of Arrow RecordBatches with one stable schema.

Statement parameters include:

- `nodeIds`: one or more Variables to read.
- `startTime`, `endTime`: OPC UA DateTime values, represented as signed 64-bit 100 ns ticks since 1601-01-01 UTC.
- `historyReadDetails`: raw/modified, processed, or at-time mode.
- `maxValuesPerNode` or service-level maximum values.
- For processed reads: `aggregateType`, `processingInterval`, and optional aggregate configuration.
- For at-time reads: the requested timestamps and interpolation policy.
- `maxRowsPerRecordBatch`: the client or service batching target.

Continuation points returned by `HistoryRead` map to Arrow stream batching. Each service page or continuation page shall be emitted as one or more RecordBatches; the Arrow stream order is the HistoryRead result order. A continuation point is not encoded as a data row. If a transport needs explicit continuation metadata, it shall carry it outside the rows as stream, batch, or transport metadata.

## 4 Canonical result shape

The canonical result shape is **long form**. Every row identifies the source node and one historical sample:

| Column | Arrow type | Requirement |
|---|---|---|
| `NodeId` | Part 6 Arrow mapping for `NodeId` | Non-null source Variable NodeId. |
| `SourceTimestamp` | `int64` | OPC UA DateTime ticks for the sample source timestamp. |
| `ServerTimestamp` | `int64` | Nullable OPC UA DateTime ticks for the server timestamp. |
| `Value` | Part 6 Arrow mapping for the node DataType | Nullable according to the value DataType and sample. |
| `StatusCode` | `uint32` | Non-null OPC UA StatusCode. If absent in a DataValue, encode `Good` (`0`). |

Long form is canonical because it is stable for ADBC consumers, composes naturally with SQL predicates, and avoids schema changes when the node set changes. A column-per-node shape is useful for specialized time-series pivots, but it changes the schema with every node selection and is not canonical.

The canonical long-form stream has one `Value` Arrow DataType. Therefore, a multi-node statement shall include nodes with the same OPC UA DataType. If a client requests mixed DataTypes, the access layer shall split the request into one ArrowArrayStream per Value DataType, or explicitly request a non-canonical Variant-valued result where `Value` uses the Part 6 `Variant` mapping.

## 5 Raw, modified, and at-time reads

For `ReadRawModifiedDetails` and `ReadAtTimeDetails`, each returned DataValue becomes one row in the canonical result shape. `SourceTimestamp`, `ServerTimestamp`, `Value`, and `StatusCode` are copied from the DataValue using the Part 6 Arrow mapping for the node DataType.

For modified reads, implementations may add metadata columns such as modification time, update type, or user name when requested by the statement. Such columns are extensions and shall not alter the canonical meaning of the five base columns.

## 6 Processed aggregate reads

For `ReadProcessedDetails`, the base columns are followed by aggregate interval columns:

| Column | Arrow type | Requirement |
|---|---|---|
| `AggregateId` | Part 6 Arrow mapping for `NodeId` | Non-null AggregateFunction NodeId. |
| `ProcessingInterval` | `int64` | Interval duration in 100 ns ticks. |
| `IntervalStart` | `int64` | Inclusive interval start in OPC UA DateTime ticks. |
| `IntervalEnd` | `int64` | Exclusive interval end in OPC UA DateTime ticks. |

The aggregate result value is encoded in `Value` using the aggregate result DataType. Aggregate status and quality are encoded in `StatusCode`; additional aggregate diagnostics such as percent good or percent bad may be added as extension columns.

## 7 Content types and transport

The Arrow IPC stream content type is:

```text
application/vnd.apache.arrow.stream
```

The Arrow IPC file content type for bounded exports is:

```text
application/vnd.apache.arrow.file
```

For remote ADBC clients, Arrow Flight SQL is the natural transport for `ExecuteQuery` and `ArrowArrayStream`. Other transports may carry the same Arrow IPC stream when they preserve the schema and RecordBatch boundaries.

## 8 Relationship to Part 14 PubSub

This historian/ADBC mapping complements OPC UA Part 14 Arrow batch publish/subscribe. Part 14 batch PubSub uses the same Part 6 Arrow value mapping for DataSet fields; historian access uses it for `HistoryRead` result values. PubSub is optimized for publishing batches of live or buffered DataSetMessages, while this mapping is optimized for query-style historical access.

## 9 Exclusions

This Arrow mapping does not map OPC UA Actions, invoke requests, or invoke responses. Actions shall use the OPC UA Avro mapping for action invocation and response payloads.
