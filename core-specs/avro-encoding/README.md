# OPC UA Avro encoding extension

This folder contains the working draft for a canonical Apache Avro binary DataEncoding for OPC UA and its PubSub message mapping, now including PubSub data frames, Action invoke/response envelopes and Discovery announcements.

## Contents

- `OPC-UA-Part6-Avro-DataEncoding.md` — Part 6 Default Avro DataEncoding proposal.
- `OPC-UA-Part14-Avro-MessageMapping.md` — Part 14 Avro PubSub message mapping proposal.
- `schemas\opcua.builtins.avsc` — normative base schema.
- `..\extras\avro-encoding\tools\build_schemas.py` — NodeSet-driven Avro schema generator.
- `..\extras\avro-encoding\tools\avro_codec.py` — reversible fastavro codec over `core-specs\extras\_common\opcua_enc` descriptors.
- `..\extras\avro-encoding\tools\wire_annotate.py` — Avro-binary byte layout annotator used by the generated Part 6 annex.
- `..\extras\avro-encoding\tools\gen_type_reference.py` — regenerates and drift-checks the Part 6 per-type reference annex.
- `..\extras\avro-encoding\tools\schema_handshake_demo.py` — executable SchemaId announcement/cache demo.
- `..\extras\avro-encoding\tools\action_discovery_demo.py` — executable Action request/response and Discovery announcement demo using published `.avsc`.
- `..\extras\avro-encoding\tools\roundtrip.py` — runs the shared CORPUS through `decode(encode(x))`.
- `..\extras\avro-encoding\tools\validate_local.py` — local acceptance gate.
- `..\extras\avro-encoding\schemas\` — generated non-base `.avsc` schemas.
- `..\extras\avro-encoding\schemas\schemaids.json` — generated on-wire SchemaId catalog for built-ins, composites and generated DataTypes.
- `..\extras\avro-encoding\examples\` — generated representative Avro payload hex files.

## Regenerate and validate

Install the runtime dependency into the current Python interpreter:

```powershell
pip install fastavro
```

From the repository root:

```powershell
python core-specs\extras\avro-encoding\tools\build_schemas.py
python core-specs\extras\avro-encoding\tools\roundtrip.py
python core-specs\extras\avro-encoding\tools\validate_local.py
```

`build_schemas.py` defaults to `core-specs\pubsub-binding\Opc.Ua.PubSubBinding.NodeSet2.xml` and writes the base schema to `core-specs\avro-encoding\schemas\` and deterministic non-base schemas to `core-specs\extras\avro-encoding\schemas\`, including the shared corpus structures/enumerations used by the examples. Pass another UANodeSet2 XML path to generate schemas for a different model.

`validate_local.py` verifies normal codec round-trips, an independent conformance gate that decodes every corpus payload and generated example from freshly loaded published `.avsc` schemas, `schemaids.json` drift, type-reference drift, byte annotation contiguity, self-contained composite SchemaId changes, the SchemaId handshake demo, and the Action/Discovery demo.

The codec and tests use the read-only shared API in `core-specs\extras\_common\opcua_enc`. Central schema sharing and registry/catalog mechanics are specified separately in `core-specs\schema-registry\OPC-UA-Schema-Registry.md`.
