# OPC UA — xRegistry Schema Catalog

Central schema sharing for the schema-based OPC UA DataEncodings (Avro, Protobuf, Apache Arrow) and JSON Schema, profiled onto the [xRegistry Schema Registry Service](https://github.com/xregistry/spec/blob/main/schema/spec.md) (`schemagroups → schemas → versions`).

- **Spec:** [`OPC-UA-xRegistry-Schema-Catalog.md`](OPC-UA-xRegistry-Schema-Catalog.md) — the mapping (namespaces→groups, DataTypes/DataSets→schemas, model/ConfigurationVersion→versions), formats & content-types, the on-the-wire schema reference, and the consumer resolution flow.
- **Why:** Avro/Protobuf/Arrow need the schema to *decode*; a disconnected consumer (PubSub, gRPC, or historian/ADBC) resolves it here. JSON is self-describing, so JSON Schema is registered for governance/validation only.

## Tools

| Command | Purpose |
|---|---|
| `python core-specs/xregistry-catalog/tools/build_catalog.py [NodeSet.xml]` | Emit `examples/opcua-catalog.xregistry.json` from a NodeSet. Generates the JSON Schema documents itself and embeds the Avro/Protobuf/Arrow documents from the sibling `*-encoding/schemas/` folders when present (else references them by `schemaurl`). |
| `python core-specs/xregistry-catalog/tools/jsonschema_gen.py` | (library) OPC UA DataType → JSON Schema (Draft 2020-12). |
| `python core-specs/xregistry-catalog/tools/validate_local.py` | Structural conformance of the catalog: required attributes, unique ids, allowed formats, embedded documents parse, JSON Schemas valid (needs `pip install jsonschema`). |

Re-run `build_catalog.py` after the three encoding folders have generated their schemas to embed the real Avro/Protobuf/Arrow documents (rather than URL references).

## Relationship

This is a **new companion specification**, not an addition to Part 6 or Part 14. It references the encoding additions in `../avro-encoding/`, `../protobuf-encoding/`, `../arrow-encoding/`, and the shared type model in `../_common/`.
