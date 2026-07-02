# `_common` — shared OPC UA type model, corpus & reference codec

Infrastructure shared by the encoding extensions (`avro-encoding/`, `protobuf-encoding/`, `arrow-encoding/`, `xregistry-catalog/`).
It is **not** an extension itself and is not proposed for the base namespace; it exists so that every encoding is generated from, and validated against, the *same* canonical OPC UA type model, values, and reversibility corpus.

## Package `opcua_enc`

| Module | Purpose |
|---|---|
| `types.py` | Type descriptors: the 25 `BuiltInType`s, `Array`, `Matrix`, `Enumeration`, `Struct`/`Field`/`StructureKind`. A descriptor names an OPC UA type precisely enough to encode/decode a value of it. |
| `values.py` | Canonical in-memory values (`NodeId`, `Variant`, `DataValue`, `ExtensionObject`, `Matrix`, `DiagnosticInfo`, …) and `canonical_equal` — bit-exact equality (NaN/`-0.0`, null-vs-empty-vs-absent). |
| `corpus.py` | `CORPUS`: 100 `(name, type, value)` cases covering every built-in edge, arrays (incl. null elements), matrices, plain/optional/union structs, subtyped ExtensionObject fields, enums/option sets, recursive DiagnosticInfo, and Variant scalar/array/matrix/ExtensionObject bodies. |
| `json_control.py` | A type-directed **reference codec** (JSON) that round-trips the whole corpus. Not the OPC UA JSON DataEncoding — it is the template the Avro/Protobuf/Arrow codecs follow, and the control that proves the corpus + equality are sound. |
| `nodeset.py` | `load_datatypes(path)` — parse a UANodeSet2 XML's `DataTypeDefinition`s into `Struct`/`Enumeration` descriptors so the generators are **NodeSet-driven**. |

## The reversibility contract

For a descriptor `T` and value `v`: `decode(T, encode(T, v))` must `canonical_equal` `v`.
Each encoding extension implements `encode`/`decode` against its wire library (fastavro / protobuf / pyarrow) and runs the shared `CORPUS` through it.

## Using it from an extension folder

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_common"))
from opcua_enc import types as t, values as v, corpus, nodeset
from opcua_enc.values import canonical_equal
```

Extensions **must treat `opcua_enc` as a read-only API** — add code only under your own folder. If you believe a shared module has a bug, report it rather than editing here (a change ripples to every encoding).

## Validate

```
python core-specs/_common/validate_local.py     # 100 cases, 0 failures
```
