# OPC UA — xRegistry Schema Catalog

**Working draft for submission to the OPC Foundation Working Group**
**Proposed Part: OPC 10000‑2xx (number to be assigned)**
**Companion namespace:** `http://opcfoundation.org/UA/SchemaCatalog/`
**Version:** 0.1.0 · **Date:** 2026-07-02

> **Status — working draft.** This document defines how OPC UA schema documents — the reference schemas produced by the Avro, Protobuf and Apache Arrow DataEncoding additions, and JSON Schema — are published in, and resolved from, a central **[xRegistry](https://github.com/xregistry/spec) Schema Registry** so that a disconnected consumer of an OPC UA PubSub message can obtain the schema it needs to decode the payload. It is a companion specification that *references* the encoding additions to [OPC 10000‑6](https://reference.opcfoundation.org/specs/OPC-10000-6/) and [OPC 10000‑14](https://reference.opcfoundation.org/specs/OPC-10000-14/); it does not itself change Part 6 or Part 14. Nothing here is normative or endorsed by the OPC Foundation.

---

## 1 Scope

The Avro, Protobuf and Apache Arrow DataEncodings are **schema‑based**: a decoder cannot reconstruct a value without the schema that describes it. Unlike the OPC UA Binary, XML and JSON DataEncodings — which are either self‑describing or resolved through the server AddressSpace — a schema‑based payload that has left the server (in a PubSub message on MQTT/AMQP/Kafka, in a file, in a data lake) must be accompanied by a **reference** to a schema document that the consumer can retrieve out‑of‑band.

This specification defines:

- a deterministic **mapping** from the OPC UA type system (namespaces, DataTypes, and PubSub DataSets) onto the **xRegistry Schema Registry** model (`schemagroups` → `schemas` → `versions`);
- the **schema formats** and content‑types used for the Avro, Protobuf, Apache Arrow and JSON Schema documents;
- the **schema reference** a Publisher places on the wire, and the **resolution flow** a consumer follows from a received `DataSetMessage` to the concrete schema document;
- a **generator** that emits a conformant xRegistry catalog document from any NodeSet, plus a worked example.

It is explicitly **out of scope** to re‑specify the encodings themselves (see the Part 6 additions), the PubSub message framing (see the Part 14 additions), or the xRegistry API — this specification is a *profile* of the [xRegistry Schema Registry Service, v1.0‑rc3](https://github.com/xregistry/spec/blob/main/schema/spec.md) and inherits its API, versioning and export/import behaviour unchanged.

### 1.1 Why a registry (and why JSON is different)

Avro, Protobuf and Arrow achieve their compactness by *externalising* type information into a schema. The registry lets a Publisher publish the schema once and pass a small reference; a consumer retrieves the document and decodes the data. JSON (the OPC UA JSON DataEncoding) does **not** require a schema to decode, so for JSON the registry is **optional** — used for governance, validation, code generation and documentation rather than for decoding. This specification therefore treats JSON Schema as a first‑class but non‑mandatory format.

## 2 Normative references

- [xRegistry Core](https://github.com/xregistry/spec/blob/main/core/spec.md) — the base registry document format and API.
- [xRegistry Schema Registry Service, v1.0‑rc3](https://github.com/xregistry/spec/blob/main/schema/spec.md) — `schemagroup`/`schema`/`version` model, `format`, `self`/`schemaurl`/`schemabase64`.
- [CloudEvents v1.0](https://github.com/cloudevents/spec) — the `dataschema` attribute convention reused for the schema reference.
- [OPC 10000‑3](https://reference.opcfoundation.org/specs/OPC-10000-3/) — Address Space Model (DataTypeDefinition, namespaces).
- [OPC 10000‑6](https://reference.opcfoundation.org/specs/OPC-10000-6/) — Mappings, **with the Avro / Protobuf / Arrow DataEncoding additions** (this repository).
- [OPC 10000‑14](https://reference.opcfoundation.org/specs/OPC-10000-14/) — PubSub, **with the Avro / Protobuf / Arrow message‑mapping additions** (this repository); `DataSetMetaData`, `ConfigurationVersion`, `dataSetFieldId`.
- [OPC 10000‑19](https://reference.opcfoundation.org/specs/OPC-10000-19/) — Dictionary Reference (optional semantic linkage).

## 3 Terms, definitions and abbreviations

| Term | Definition |
|---|---|
| Schema document | A concrete Avro (`.avsc`), Protobuf (`.proto`), Apache Arrow, or JSON Schema document describing an OPC UA DataType or DataSet in one encoding. |
| Schema Group | An xRegistry `schemagroup` — here, the container for all schema documents of one OPC UA namespace. |
| Schema (Resource) | An xRegistry `schema` — the logical umbrella over one or more schema **Versions** of the same DataType/DataSet in one format. |
| Version | An xRegistry schema Version — one concrete document, correlated with an OPC UA model version / `ConfigurationVersion`. |
| Format | The xRegistry `format` string identifying the schema language (e.g. `Avro/1.11`, `Protobuf/3`, `ApacheArrow/1.0`, `JsonSchema/2020-12`). |
| Schema reference | The URI a Publisher places on the wire (the schema Version's `self` URL) so a consumer can fetch the document; modelled on CloudEvents `dataschema`. |

Key words **shall**, **should**, **may** are interpreted as in ISO/IEC directives / RFC 2119.

## 4 Overview

```mermaid
graph LR
  subgraph Publisher
    NS[NodeSet DataTypes / PublishedDataSet]
  end
  NS -->|build_catalog| REG[(xRegistry Schema Registry)]
  REG --> SG["schemagroup = namespace URI"]
  SG --> S1["schema: <DataType>:avro (Avro/1.11)"]
  SG --> S2["schema: <DataType>:protobuf (Protobuf/3)"]
  SG --> S3["schema: <DataType>:arrow (ApacheArrow/1.0)"]
  SG --> S4["schema: <DataType>:jsonschema (JsonSchema/2020-12)"]
  Publisher ==>|"DataSetMessage + schema self-URL + content-type"| Consumer
  Consumer -->|"GET self-URL"| REG
  Consumer -->|"decode with fetched schema"| VALUE[OPC UA value]
```

The Publisher (or an offline tool) generates a catalog from its model and publishes it to a registry. On the wire, each schema‑based `DataSetMessage` carries the **schema reference** (and a **content‑type** identifying the format). A consumer resolves the reference against the registry, retrieves the document, and decodes. For JSON the reference is informative only.

## 5 Mapping OPC UA onto the xRegistry model

### 5.1 Schema Groups = OPC UA namespaces

Each OPC UA namespace URI maps to exactly one `schemagroup`. Because a `schemagroupid` is a registry key, it **shall** be a stable, URL‑safe token derived from the namespace (e.g. a reverse‑DNS‑like slug), and the full namespace URI **shall** be retained verbatim in the group `labels` under the key `opcua.namespaceuri`. A `schemagroup` **may** carry all four formats for its DataTypes.

### 5.2 Schema Resources = DataTypes and DataSets

Within a namespace group, one `schema` Resource is created per **(DataType or PublishedDataSet, format)** pair. Because an xRegistry `schema` Resource holds Versions of a single logical schema in a single `format`, the four encodings of one DataType are four sibling `schema` Resources. Identifiers **shall** be:

- `schemaid` = `<BrowseName>:<fmt>` where `<fmt>` ∈ {`avro`, `protobuf`, `arrow`, `jsonschema`};
- group `labels` / schema `labels`: `opcua.browsename`, `opcua.nodeid`, `opcua.datatypeencoding` (the `Default Avro`/`Default Protobuf`/`Default Arrow` well‑known name), and — for a DataSet — `opcua.datasetname`.

The `name` attribute **shall** be the plain BrowseName so consumers can list all encodings of a DataType by a `name` filter. The PubSub message envelope schemas (NetworkMessage / DataSetMessage) live in the base‑namespace group `http://opcfoundation.org/UA/`.

### 5.3 Versions = model version / ConfigurationVersion

Each schema **Version** correlates with an OPC UA model change. The `versionid` **shall** follow the xRegistry default algorithm (monotonic unsigned integers). The originating OPC UA version **shall** be recorded in Version `labels`: `opcua.modelversion` (the NodeSet `<Models><Model Version=…>`), and, where the schema describes a PubSub DataSet, `opcua.configurationversion` (the `ConfigurationVersion` `{MajorVersion, MinorVersion}` as `major.minor`). This is the key a Part 14 consumer uses to select the correct Version (§6).

### 5.4 Formats and content‑types

| Encoding | xRegistry `format` | Version `contenttype` | Document carrier |
|---|---|---|---|
| Apache Avro | `Avro/1.11` | `application/vnd.apache.avro+json` (schema doc) | inline `schema` (the `.avsc` JSON) |
| Protobuf | `Protobuf/3` | `text/plain` (the `.proto`) | inline `schema` (proto3 source) |
| Apache Arrow | `ApacheArrow/1.0` (extension format) | `application/vnd.apache.arrow.schema+json` | inline `schema` (the JSON schema description) |
| JSON Schema | `JsonSchema/2020-12` | `application/schema+json` | inline `schema` (the JSON Schema) |

`Avro/1.11`, `Protobuf/3` and `JsonSchema/*` are the format names refined by the xRegistry Schema Registry spec; `ApacheArrow/1.0` is an application‑defined extension format (the spec permits extension formats). Where a document is preferred by reference rather than embedded, `schemaurl` **may** be used instead of inline `schema`; binary carriers use `schemabase64`.

### 5.5 The schema reference and the `self` URL

The reference a Publisher puts on the wire is the schema **Version's** `self` URL, e.g.

```
https://registry.example.com/schemagroups/opcfoundation.ua.pumps/schemas/PumpDataType:protobuf/versions/3
```

This reuses the CloudEvents `dataschema` convention, so an OPC UA PubSub payload republished as a CloudEvent carries the same URI in `dataschema`. Registries **may** offer a `shortself` alias. Appending `$details` returns the Version metadata (including `opcua.*` labels) rather than the raw document.

## 6 Resolution flow (Part 14 consumer)

Given a received schema‑based `DataSetMessage`, a consumer **shall** resolve its schema as follows:

1. Determine the **format** from the transport **content‑type** (Part 14 additions: MQTT `ContentType`, AMQP `content-type`, Kafka `content-type` header) — e.g. `application/vnd.apache.avro`, `application/x-protobuf`, `application/vnd.apache.arrow.stream`.
2. If the message header carries an explicit **schema reference** (the Version `self` URL — carried in the Part 14 message header extension or the transport header), GET it and decode. Otherwise:
3. Resolve the **schemagroup** from the DataSet's namespace (`DataSetMetaData` namespace), the **schema** from `<DataSetName>:<fmt>` (or the DataType BrowseName for RawData field schemas), and the **Version** from `opcua.configurationversion` = the message `DataSetMessage` header `ConfigurationVersion`.
4. GET the resolved Version `self` URL to obtain the schema document, then decode the payload per the corresponding Part 6 addition.

The `ConfigurationVersion` correlation (§5.3) is the same mechanism the OPC UA JSON/UADP mappings already use to detect DataSet layout change; a mismatch **shall** cause the consumer to re‑resolve the Version.

### 6.1 JSON is self‑describing

For the OPC UA JSON DataEncoding no schema fetch is required to decode. A Publisher **may** still register JSON Schema (`JsonSchema/2020-12`) for validation, code generation and documentation, and **may** reference it identically; consumers **shall not** be required to fetch it in order to decode JSON.

## 7 Catalog generation and example

The generator `tools/build_catalog.py` emits a single‑document xRegistry catalog (§3 of the Schema Registry spec) from a NodeSet:

- it creates one `schemagroup` per namespace, and — for every structured/enumerated DataType — the four sibling `schema` Resources with one initial Version each;
- it produces the **JSON Schema** documents itself (this specification's contribution) and **embeds** the Avro/Protobuf/Arrow documents generated by the sibling encoding folders (`../avro-encoding/schemas`, `../protobuf-encoding/schemas`, `../arrow-encoding/schemas`) when present, or references them by `schemaurl`;
- it stamps the `opcua.*` labels (§5) so the resolution flow (§6) is data‑driven.

A worked example is generated to `examples/opcua-catalog.xregistry.json`. `tools/validate_local.py` checks the document is structurally conformant (required attributes, unique ids, allowed formats, embedded documents parse).

## 8 Relationship to the base specifications

This is a **new companion specification**, not an addition to Part 6 or Part 14. Its only optional touch‑point on Part 14 is the **schema reference carrier**: the Part 14 message‑mapping additions define an OPTIONAL header field (or transport header) that carries the schema Version `self` URL; when absent, resolution falls back to the `namespace + name + ConfigurationVersion` lookup of §6. A Server **may** additionally expose its registry endpoint as a Property so Clients can discover it; that Property is described in the Part 14 additions and is out of scope here.

## 9 Conformance

An implementation conforms if it (a) publishes an xRegistry catalog whose groups, schemas, versions, formats and `opcua.*` labels follow §5, (b) supports the resolution flow of §6 for at least one schema‑based format, and (c) preserves reversibility end‑to‑end: a value encoded per a registered schema and decoded through the resolved schema equals the original (the acceptance corpus of the encoding additions).

---

## Annex A — Example catalog (informative)

See [`examples/opcua-catalog.xregistry.json`](examples/opcua-catalog.xregistry.json), generated from `core-specs/pubsub-binding/Opc.Ua.PubSubBinding.NodeSet2.xml`. It contains one `schemagroup` for the binding namespace with the four sibling schema Resources per DataType and the PubSub envelope schemas in the base‑namespace group.
