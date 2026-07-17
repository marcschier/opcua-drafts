# opcua-drafts

A scratch pad for **OPC UA specification drafts**.

This repository is a working area for authoring and iterating on draft OPC UA information models and companion specifications. It is intentionally informal: contents are experimental drafts used to explore modelling approaches, try out tooling, and prototype NodeSets before anything is proposed or released. Nothing here is normative, official, or final, and everything is subject to change or removal without notice.

## Contributing

Feedback on these drafts is welcome — and you don't have to write the specification yourself. Fork the repo, create a branch, and either make changes or just **annotate** the drafts (inline comments, notes, or open questions); then open a pull request and discuss. Maintainers use **AI agents** to turn the feedback and discussion into concrete specification text, information-model (NodeSet / CSV) updates, and regenerated artifacts.

1. Fork `marcschier/opcua-drafts` and check out a topic branch.
2. Make your changes or annotations — for generated specs, edit the source (a descriptor or `tools/build_model.py`), not the generated NodeSet / CSV, and regenerate.
3. Open a pull request against `main` and discuss.
4. Maintainers apply the agreed changes with AI, regenerate, and validate (`python core-specs/extras/validate_all.py`).

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full workflow, validation, and conventions.

## Layout

- `companion-specs/` — draft OPC UA companion specifications, one folder per domain.
  - `Generators/` — draft Companion Specification for electrical power **Generator Sets (GenSets)**: the information model (`Opc.Ua.Generators.NodeSet2.xml`), the NodeId assignments (`Opc.Ua.Generators.NodeIds.csv`), the specification document, and `tools/build_model.py` — a generator that emits the NodeSet, CSV, and reference tables from a single source of truth.
- `core-specs/` — draft **extensions to the base OPC UA specification** (proposed additions to the `http://opcfoundation.org/UA/` namespace), intended for submission to an OPC Foundation Working Group. Each encoding/catalog folder below contains only the **normative** spec documents, its `README.md`, and the **base reference schema**; all tooling, examples, generated (non-base) schemas, and the shared validation package live under `core-specs/extras/` (a parallel, mirrored tree).
  - `observability-export/` — draft *OPC UA — Observability Export*: a small, transport-neutral layer that lets a Server, or a companion specification, declare **how its data lands in an observability system** — as OpenTelemetry (OTEL) **metrics, logs and traces** — so a generic read-only **bridge** can forward it over the **classic client/server (RPC) interface** and, **optionally**, over **PubSub (Part 14)** without understanding the domain. Contains the base NodeSet, CSV, and specification document, plus one **standardized subfolder per companion spec** (`pumps/`, `robotics/`, `facets/`, `di/`), each holding the companion-spec **addendum(s)** and the instance-overlay `NodeSet2.xml`. The generator tooling and example descriptor sources live under `core-specs/extras/observability-export/` (below). A non-normative **overview deck** ([`core-specs/observability-export/README.md`](core-specs/observability-export/README.md)) summarizes the why, what and how.
  - `avro-encoding/` — **Apache Avro (binary)** DataEncoding: a Part 6 mapping of the full OPC UA type model and a Part 14 **PubSub** message mapping, including **Action invoke/response** and **Discovery** messages. Reversible (`decode(encode(x)) == x`), with a NodeSet-driven schema generator and a SchemaId handshake.
  - `arrow-encoding/` — **Apache Arrow (columnar)**: a Part 6 mapping, a Part 14 **batch publish/subscribe** mapping, and an **ADBC-style historian access** surface (Part 11 HistoryRead → Arrow RecordBatch streams). Actions are out of scope for Arrow.
  - `schema-registry/` — draft *OPC UA — Schema Registry*: the unified schema registry model, covering both the in-server AddressSpace NodeSet binding and the out-of-band xRegistry catalog projection used by disconnected consumers (PubSub or historian/ADBC).
  - `extras/` — everything **secondary to standardization**, mirroring the structure above: per‑folder `tools/`, `examples/`, and generated (non‑base) `schemas/`; the shared `_common/` (`opcua_enc` package: canonical OPC UA type model, reversibility **corpus**, NodeSet DataType loader, JSON control codec, fingerprint/hexdump helpers); and `validate_all.py` + `requirements.txt`. Run `python core-specs/extras/validate_all.py` to (re)generate and validate every extension.
- `skills/` — reusable authoring **skills** (agent instructions) that operate on the drafts.
  - `opcua-observability-export/` — a skill that generates observability-export bindings for any companion specification from its NodeSet (classifying its Variables and events into OTEL metrics, logs and traces; over RPC, optionally realized over PubSub; a machine-readable binding descriptor, an instance-overlay NodeSet, and a companion-spec addendum with annex tables and diagrams).
