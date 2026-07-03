# OPC UA Apache Arrow DataEncoding extension

This working area contains the Apache Arrow (columnar) OPC UA DataEncoding draft, historian/ADBC access mapping, PubSub batch message mapping draft, reference schemas, examples, and a local reversibility harness. Arrow is for columnar historian access and Part 14 batch publish/subscribe; it does not map OPC UA Actions.

## Contents

- [`OPC-UA-Part6-Arrow-DataEncoding.md`](OPC-UA-Part6-Arrow-DataEncoding.md) — proposed insertion into OPC 10000-6 v1.05.07.
- [`OPC-UA-Arrow-Historian-ADBC-Access.md`](OPC-UA-Arrow-Historian-ADBC-Access.md) — ADBC-style HistoryRead result mapping to ArrowArrayStream.
- [`OPC-UA-Part14-Arrow-MessageMapping.md`](OPC-UA-Part14-Arrow-MessageMapping.md) — proposed insertion into OPC 10000-14 v1.05.06.
- `tools\build_schemas.py` — builds deterministic JSON descriptions of the shared Arrow type mapping into `schemas\`.
- `tools\arrow_codec.py` — pyarrow IPC stream codec used by the local reversibility harness.
- `tools\roundtrip.py` — runs the shared 100-case corpus through `decode(encode(x))`.
- `tools\validate_local.py` — acceptance gate: schema determinism, corpus roundtrip, stable examples, ADBC access demo.
- `examples\` — representative Arrow IPC stream payloads plus `index.json`.

## Run

Install `pyarrow`, then run from the repository root:

```powershell
python core-specs\arrow-encoding\tools\validate_local.py
```

Expected success line:

```text
validate_local: schemas ok, schemaids ok, examples ok, type-reference ok, byte-annotations ok, handshake ok, adbc-access ok, conformance gate 102/102 corpus passed, 102/102 corpus passed, 0 failures
```

## Shared model

The codec and generator import the read-only shared API from `core-specs\_common\opcua_enc`: type descriptors, canonical values, the NodeSet loader, and the 102-case corpus. The Arrow Part 6 field/type mapping, historian/ADBC `Value` column mapping, and Part 14 DataSet column mapping are intentionally the same mapping.

Schema sharing across sibling extensions is catalogued centrally by `core-specs\xregistry-catalog\`; this folder only emits the Arrow-specific reference schema descriptions.
