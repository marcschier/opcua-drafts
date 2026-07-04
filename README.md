# opcua-drafts

A scratch pad for **OPC UA specification drafts**.

This repository is a working area for authoring and iterating on draft OPC UA information models and companion specifications. It is intentionally informal: contents are experimental drafts used to explore modelling approaches, try out tooling, and prototype NodeSets before anything is proposed or released. Nothing here is normative, official, or final, and everything is subject to change or removal without notice.

## Layout

- `companion-specs/` — draft OPC UA companion specifications, one folder per domain.
  - `Generators/` — draft Companion Specification for electrical power **Generator Sets (GenSets)**: the information model (`Opc.Ua.Generators.NodeSet2.xml`), the NodeId assignments (`Opc.Ua.Generators.NodeIds.csv`), the specification document, and `tools/build_model.py` — a generator that emits the NodeSet, CSV, and reference tables from a single source of truth.
- `core-specs/` — draft **extensions to the base OPC UA specification** (proposed additions to the `http://opcfoundation.org/UA/` namespace), intended for submission to an OPC Foundation Working Group.
  - `scenario-binding/` — draft *OPC UA — Scenario Bindings*: a small, transport-neutral **binding and discovery layer** that lets a Server expose the instances of **any** companion specification for extensible integration **Scenarios** (observability, predictive maintenance, anomaly detection, …) over the **classic client/server (RPC) interface** and, **optionally**, over **PubSub (Part 14)**, so a generic client can bridge them to other systems without understanding the domain. Contains the base NodeSet, CSV, and specification document, plus one **standardized subfolder per companion spec** (`pumps/`, `robotics/`, `facets/`, `di/`), each holding the companion-spec **addendum(s)** and the instance-overlay `NodeSet2.xml`. The generator tooling and example descriptor sources live under `extras/scenario-binding/` (below).
- `extras/` — **secondary** material that supports, but is not itself part of, standardization, mirroring the `core-specs/` per-spec layout.
  - `scenario-binding/tools/` — the base-model generator (`build_model.py`, which emits the NodeSet, CSV, and Annex A tables into `core-specs/scenario-binding/` from a single source of truth) and its structural validator.
  - `scenario-binding/examples/` — the per-companion-spec **descriptor sources** and generators: `tools/build_bindings.py` resolves every BrowsePath against the published companion NodeSet and emits the standardized addendum + overlay into `core-specs/scenario-binding/<spec>/`; `tools/build_wot_td.py` renders the same descriptor as a W3C WoT Thing Description. Per-spec folders (`pumps/`, `robotics/`, `facets/`, `di/`) hold the machine-readable `ScenarioBinding.json` descriptors and generated `td.json` Thing Descriptions.
- `skills/` — reusable authoring **skills** (agent instructions) that operate on the drafts.
  - `opcua-scenario-binding/` — a skill that generates Scenario Bindings for any companion specification from its NodeSet (over RPC, optionally realized over PubSub; a machine-readable binding descriptor, an instance-overlay NodeSet, and a companion-spec addendum with annex tables and diagrams).

## Status

Draft / experimental. These drafts are not affiliated with, reviewed by, or endorsed by the OPC Foundation, and the use of `opcfoundation.org` namespace URIs is for prototyping only.
