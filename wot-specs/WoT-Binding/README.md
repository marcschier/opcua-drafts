# OPC UA — Web of Things (WoT) Binding

A complete, standalone draft revision of the OPC UA companion specification for Web of Things connectivity. It is not an addendum: the specification can be read on its own. It preserves every namespace, prefix, term, and normative behaviour of the published baseline and adds a collision-safe model and platform vocabulary together with a bidirectional NodeSet2 conversion and a preservation envelope.

> Experimental and non-normative. Nothing here is official or endorsed by the OPC Foundation or the W3C; `opcfoundation.org` namespace URIs are used for prototyping only.

## Purpose

- Describe an OPC UA interface as a W3C Thing Description or Thing Model, using the preserved Read / Write / Observe / Call and security vocabulary.
- Express the structural facts of an OPC UA type — composition, references, groups, units, scaling, configuration, metadata, and modelling rules — in a Thing Model.
- Convert between an OPC UA NodeSet2 information model and a Thing Description or Thing Model without loss, preserving exact constructs in a `uav:nodeSet` envelope and reading everything else natively.

## Sources

- [OPC 10101 — OPC UA for WoT Binding](https://reference.opcfoundation.org/specs/OPC-10101/) — the published baseline this draft re-authors and preserves.
- [W3C Web of Things (WoT) Thing Description 1.1](https://www.w3.org/TR/wot-thing-description11/) and [WoT Binding Templates](https://www.w3.org/TR/wot-binding-templates/).
- [OPC 10000-3](https://reference.opcfoundation.org/specs/OPC-10000-3/), [10000-4](https://reference.opcfoundation.org/specs/OPC-10000-4/), [10000-5](https://reference.opcfoundation.org/specs/OPC-10000-5/), [10000-6](https://reference.opcfoundation.org/specs/OPC-10000-6/), [10000-7](https://reference.opcfoundation.org/specs/OPC-10000-7/).
- [QUDT](http://qudt.org/) for quantity kinds and units; [RFC 6901](https://www.rfc-editor.org/rfc/rfc6901), [RFC 4648](https://www.rfc-editor.org/rfc/rfc4648), and [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986).
- Two architecture decision records (ADR 0029 and ADR 0032) are used only as design inputs for the model vocabulary; a design-input crosswalk is kept, informatively, under [`../extras/WoT-Binding/adr-to-uav-crosswalk.md`](../extras/WoT-Binding/adr-to-uav-crosswalk.md) — **not** in the normative specification. No vocabulary, prefix, or namespace of those inputs is reused.

## Artifacts

- [`OPC-UA-WoT-Binding.md`](OPC-UA-WoT-Binding.md) — the full specification.
- [`opc-ua-wot-binding.context.jsonld`](opc-ua-wot-binding.context.jsonld) — the JSON-LD context binding the `uav` prefix and every documented term.
- [`opc-ua-wot-binding.schema.json`](opc-ua-wot-binding.schema.json) — the extension and preservation JSON Schema (2020-12).
- [`examples/`](examples/) — worked examples:
  - [`01-opcua-td-pump.jsonld`](examples/01-opcua-td-pump.jsonld) — a Thing Description using the preserved Read / Write / Observe / Call and security vocabulary.
  - [`02-thing-model-pump.jsonld`](examples/02-thing-model-pump.jsonld) — a Thing Model using the model and platform vocabulary.
  - [`03-nodeset-preservation-envelope.jsonld`](examples/03-nodeset-preservation-envelope.jsonld) — a `uav:nodeSet` preservation envelope carrying a canonical NodeSet2 baseline.
  - [`04-type-reference-modelling-rule.jsonld`](examples/04-type-reference-modelling-rule.jsonld) — type, reference (including a `HasOrderedComponent` subtype pinned by a typed link), and modelling-rule mappings.
- [`tools/validate_local.py`](tools/validate_local.py) — the deterministic, standard-library validator.

## Namespace and prefix

The vocabulary namespace is `http://opcfoundation.org/UA/WoT-Binding/`, bound to the prefix `uav`. Both are preserved unchanged from the published baseline.

## Validation

Run the validator from the repository root (standard library only, no dependencies):

```bash
python wot-specs/WoT-Binding/tools/validate_local.py
```

It checks that every JSON and JSON-LD artifact parses, that the context contains every documented `uav` term, that each example declares the `uav` context, that each preservation envelope's base64 and SHA-256 are valid and decode to a well-formed `UANodeSet` root, that internal relative references resolve, that every NodeId-valued term in an example is a portable ExpandedNodeId (never the session-local `ns=<index>` form), that `@type: uav:eventType` is never paired with `uav:isEvent: false`, and that no forbidden vendor prefix, namespace, or legacy modelling-language name appears. It prints `OK` and exits `0` on success.
