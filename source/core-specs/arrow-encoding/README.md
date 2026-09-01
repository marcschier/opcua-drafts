# OPC UA Apache Arrow DataEncoding extension

This working area contains the Apache Arrow (columnar) OPC UA DataEncoding draft, historian/ADBC access mapping, PubSub batch message mapping draft, and the base reference schema. Supplemental schemas, examples, and local tooling live under `extras/core-specs/arrow-encoding/`. Arrow is for columnar historian access and Part 14 batch publish/subscribe; it does not map OPC UA Actions.

## Contents

- [`OPC-UA-Arrow-Encoding.md`](spec.md) — **the specification**: a self-contained read covering the Arrow DataEncoding, the PubSub batch message mapping and the historian/ADBC access mapping (with the base OPC UA context a standalone reader needs) plus the generated per-type reference annex.
- `extras/core-specs/arrow-encoding/tools/build_schemas.py` — builds deterministic JSON descriptions of the shared Arrow type mapping into `source/core-specs/arrow-encoding/schemas/base.json` and `extras/core-specs/arrow-encoding/schemas/`.
- `extras/core-specs/arrow-encoding/tools/arrow_codec.py` — pyarrow IPC stream codec used by the local reversibility harness.
- `extras/core-specs/arrow-encoding/tools/roundtrip.py` — runs the shared 102-case corpus through `decode(encode(x))`.
- `extras/core-specs/arrow-encoding/tools/validate_local.py` — acceptance gate: schema determinism, corpus roundtrip, stable examples, ADBC access demo.
- `extras/core-specs/arrow-encoding/examples/` — representative Arrow IPC stream payloads plus `index.json`.

## Run

Install `pyarrow`, then run from the repository root:

```powershell
python extras\core-specs\arrow-encoding\tools\validate_local.py
```

Expected success line:

```text
validate_local: schemas ok, schemaids ok, examples ok, type-reference ok, byte-annotations ok, handshake ok, adbc-access ok, conformance gate 102/102 corpus passed, 102/102 corpus passed, 0 failures
```

## Shared model

The codec and generator import the read-only shared API from `extras\core-specs\_common\opcua_enc`: type descriptors, canonical values, the NodeSet loader, and the 102-case corpus. The Arrow Part 6 field/type mapping, historian/ADBC `Value` column mapping, and Part 14 DataSet column mapping are intentionally the same mapping.

Schema sharing across sibling extensions is catalogued by [OPC UA for Schema Registry](https://github.com/OPCF-Members/spec-drafts/blob/main/source/cloud-specs/schema-registry/spec.md), which is under OPC Foundation review. This folder only emits the Arrow-specific reference schema descriptions.
