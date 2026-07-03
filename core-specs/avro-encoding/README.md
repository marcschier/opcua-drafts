# OPC UA Avro encoding extension

This folder contains the working draft for a canonical Apache Avro binary DataEncoding for OPC UA and its PubSub message mapping.

## Contents

- `OPC-UA-Part6-Avro-DataEncoding.md` — Part 6 Default Avro DataEncoding proposal.
- `OPC-UA-Part14-Avro-MessageMapping.md` — Part 14 Avro PubSub message mapping proposal.
- `tools\build_schemas.py` — NodeSet-driven Avro schema generator.
- `tools\avro_codec.py` — reversible fastavro codec over `core-specs\_common\opcua_enc` descriptors.
- `tools\wire_annotate.py` — Avro-binary byte layout annotator used by the generated Part 6 annex.
- `tools\gen_type_reference.py` — regenerates and drift-checks the Part 6 per-type reference annex.
- `tools\schema_handshake_demo.py` — executable SchemaId announcement/cache demo.
- `tools\roundtrip.py` — runs the shared CORPUS through `decode(encode(x))`.
- `tools\validate_local.py` — local acceptance gate.
- `schemas\` — generated `.avsc` schemas.
- `schemas\schemaids.json` — generated on-wire SchemaId catalog for built-ins, composites and generated DataTypes.
- `examples\` — generated representative Avro payload hex files.

## Regenerate and validate

Install the runtime dependency into the current Python interpreter:

```powershell
pip install fastavro
```

From the repository root:

```powershell
python core-specs\avro-encoding\tools\build_schemas.py
python core-specs\avro-encoding\tools\roundtrip.py
python core-specs\avro-encoding\tools\validate_local.py
```

`build_schemas.py` defaults to `core-specs\pubsub-binding\Opc.Ua.PubSubBinding.NodeSet2.xml` and writes deterministic schemas to `schemas\`, including the shared corpus structures/enumerations used by the examples. Pass another UANodeSet2 XML path to generate schemas for a different model.

`validate_local.py` verifies normal codec round-trips, an independent conformance gate that decodes every corpus payload and generated example from freshly loaded published `.avsc` schemas, `schemaids.json` drift, type-reference drift, byte annotation contiguity, self-contained composite SchemaId changes, and the SchemaId handshake demo.

The codec and tests use the read-only shared API in `core-specs\_common\opcua_enc`. Central schema sharing and registry/catalog mechanics are specified separately in `core-specs\xregistry-catalog\`.
