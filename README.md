# opcua-drafts

A scratch pad for **OPC UA specification drafts**.

This repository is a working area for authoring and iterating on draft OPC UA information models and companion specifications. It is intentionally informal: contents are experimental drafts used to explore modelling approaches, try out tooling, and prototype NodeSets before anything is proposed or released. Nothing here is normative, official, or final, and everything is subject to change or removal without notice.

## Layout

- `companion-specs/` — draft OPC UA companion specifications, one folder per domain.
  - `Generators/` — draft Companion Specification for electrical power **Generator Sets (GenSets)**: the information model (`Opc.Ua.Generators.NodeSet2.xml`), the NodeId assignments (`Opc.Ua.Generators.NodeIds.csv`), the specification document, and `tools/build_model.py` — a generator that emits the NodeSet, CSV, and reference tables from a single source of truth.
- `core-specs/` — draft **extensions to the base OPC UA specification** (proposed additions to the `http://opcfoundation.org/UA/` namespace), intended for submission to an OPC Foundation Working Group. Each encoding/catalog folder below contains only the **normative** spec documents, its `README.md`, and the **base reference schema**; all tooling, examples, generated (non-base) schemas, and the shared validation package live under `core-specs/extras/` (a parallel, mirrored tree).
  - `pubsub-binding/` — draft *OPC UA — PubSub Scenario Binding*: a small, transport-neutral binding and discovery layer that lets a server expose the instances of **any** companion specification over PubSub (Part 14) for extensible integration **Scenarios** (observability, predictive maintenance, anomaly detection, …), so a generic client can bridge them to other systems without understanding the domain. Contains the NodeSet, CSV, specification document, and `tools/build_model.py`.
  - `avro-encoding/` — **Apache Avro (binary)** DataEncoding: a Part 6 mapping of the full OPC UA type model and a Part 14 **PubSub** message mapping, including **Action invoke/response** and **Discovery** messages. Reversible (`decode(encode(x)) == x`), with a NodeSet-driven schema generator and a SchemaId handshake.
  - `protobuf-encoding/` — **Protobuf** encoding for **OPC UA gRPC service calls**: a Part 6 type mapping plus a Part 6 §7.6 *OPC UA over gRPC* TransportProtocol (Service → RPC). Not a PubSub encoding.
  - `arrow-encoding/` — **Apache Arrow (columnar)**: a Part 6 mapping, a Part 14 **batch publish/subscribe** mapping, and an **ADBC-style historian access** surface (Part 11 HistoryRead → Arrow RecordBatch streams). Actions are out of scope for Arrow.
  - `schema-registry/` — draft *OPC UA — Schema Registry*: the unified schema registry model, covering both the in-server AddressSpace NodeSet binding and the out-of-band xRegistry catalog projection used by disconnected consumers (PubSub, gRPC, or historian/ADBC).
  - `extras/` — everything **secondary to standardization**, mirroring the structure above: per‑folder `tools/`, `examples/`, and generated (non‑base) `schemas/`; the shared `_common/` (`opcua_enc` package: canonical OPC UA type model, reversibility **corpus**, NodeSet DataType loader, JSON control codec, fingerprint/hexdump helpers); and `validate_all.py` + `requirements.txt`. Run `python core-specs/extras/validate_all.py` to (re)generate and validate every extension.
- `skills/` — reusable authoring **skills** (agent instructions) that operate on the drafts.
  - `opcua-scenario-binding/` — a skill that generates PubSub Scenario Bindings for any companion specification from its NodeSet (a machine-readable binding descriptor, a human-readable annex, and an optional NodeSet fragment).

## Status

Draft / experimental. These drafts are not affiliated with, reviewed by, or endorsed by the OPC Foundation, and the use of `opcfoundation.org` namespace URIs is for prototyping only.
