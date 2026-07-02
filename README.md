# opcua-drafts

A scratch pad for **OPC UA specification drafts**.

This repository is a working area for authoring and iterating on draft OPC UA information models and companion specifications. It is intentionally informal: contents are experimental drafts used to explore modelling approaches, try out tooling, and prototype NodeSets before anything is proposed or released. Nothing here is normative, official, or final, and everything is subject to change or removal without notice.

## Layout

- `companion-specs/` — draft OPC UA companion specifications, one folder per domain.
  - `Generators/` — draft Companion Specification for electrical power **Generator Sets (GenSets)**: the information model (`Opc.Ua.Generators.NodeSet2.xml`), the NodeId assignments (`Opc.Ua.Generators.NodeIds.csv`), the specification document, and `tools/build_model.py` — a generator that emits the NodeSet, CSV, and reference tables from a single source of truth.
- `core-specs/` — draft **extensions to the base OPC UA specification** (proposed additions to the `http://opcfoundation.org/UA/` namespace), intended for submission to an OPC Foundation Working Group.
  - `pubsub-binding/` — draft *OPC UA — PubSub Scenario Binding*: a small, transport-neutral binding and discovery layer that lets a server expose the instances of **any** companion specification over PubSub (Part 14) for extensible integration **Scenarios** (observability, predictive maintenance, anomaly detection, …), so a generic client can bridge them to other systems without understanding the domain. Contains the NodeSet, CSV, specification document, and `tools/build_model.py`.
  - `avro-encoding/`, `protobuf-encoding/`, `arrow-encoding/` — draft **DataEncoding extensions** that add an Apache Avro (binary), Protobuf, and Apache Arrow (columnar) mapping of the full OPC UA type model, mirroring the existing Binary/XML/JSON encodings. Each folder contains a *Part 6* addition (data-model mapping), a *Part 14* addition (PubSub message mapping), generated reference schemas/IDL, examples, and a NodeSet-driven generator + reversibility harness. One canonical form per encoding; every value round-trips (`decode(encode(x)) == x`).
  - `xregistry-catalog/` — draft *OPC UA — xRegistry Schema Catalog*: how the schema-based encodings' schemas (and JSON Schema) are published in and resolved from a central [xRegistry](https://github.com/xregistry/spec) Schema Registry, so a disconnected PubSub consumer can fetch the schema it needs to decode.
  - `_common/` — shared tooling (not a spec): the `opcua_enc` Python package with the canonical OPC UA type model, the reversibility **corpus**, a NodeSet DataType loader, and a JSON control codec that all encoding folders validate against.
- `skills/` — reusable authoring **skills** (agent instructions) that operate on the drafts.
  - `opcua-scenario-binding/` — a skill that generates PubSub Scenario Bindings for any companion specification from its NodeSet (a machine-readable binding descriptor, a human-readable annex, and an optional NodeSet fragment).

## Status

Draft / experimental. These drafts are not affiliated with, reviewed by, or endorsed by the OPC Foundation, and the use of `opcfoundation.org` namespace URIs is for prototyping only.
