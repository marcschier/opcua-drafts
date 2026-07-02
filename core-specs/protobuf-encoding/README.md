# OPC UA Protobuf Encoding extension

Working draft assets for the OPC UA proto3 DataEncoding extension. This folder is self-contained; shared type descriptors, values, the corpus, NodeSet loader, and JSON control codec are read from `core-specs\_common\opcua_enc` as a read-only API.

## Contents

- `OPC-UA-Part6-Protobuf-DataEncoding.md` — proposed insertion for OPC 10000-6 v1.05.07.
- `OPC-UA-Part14-Protobuf-MessageMapping.md` — proposed insertion for OPC 10000-14 v1.05.06.
- `tools\build_schemas.py` — deterministic NodeSet/corpus-driven `.proto` generator.
- `tools\protobuf_codec.py` — reversible reference codec over compiled protobuf messages.
- `tools\roundtrip.py` — runs the 100-case shared `CORPUS` through `decode(encode(x))`.
- `tools\validate_local.py` — local acceptance gate: schema determinism, `.proto` compilation, corpus round-trip, and byte-stable examples.
- `schemas\` — generated reference proto3 schemas, including `opcua_builtins.proto`.
- `examples\` — representative encoded payload bytes and `index.json`.

## Usage

Install the protobuf compiler plugin once if needed:

```powershell
python -m pip install grpcio-tools
```

Run the acceptance gate from the repository root:

```powershell
python core-specs\protobuf-encoding\tools\validate_local.py
```

Regenerate schemas only:

```powershell
python core-specs\protobuf-encoding\tools\build_schemas.py
```

Run only the reversibility harness:

```powershell
python core-specs\protobuf-encoding\tools\roundtrip.py
```

## Design notes

The canonical wire form is proto3 with explicit presence. Structures and unions are encoded as the generated per-type messages in `schemas\`; the reflective `Value` envelope is not an alternate structure encoding. Nullable scalar values and optional structure fields use nullable wrappers (`StringValue`, `ByteStringValue`) or message/oneof presence. Nullable elements inside `repeated` fields use a wrapper message strategy: an empty `Value` wrapper is the canonical null element, while a present `Value` with an empty string or empty bytes is an empty value. `DateTime` is raw signed 100 ns ticks in `sfixed64`; `UInt64` is protobuf `uint64`; `Guid` is exactly 16 bytes. `Variant` carries the OPC UA built-in type id plus exactly one scalar, array, or matrix payload; the empty `Variant` message is null. Known `ExtensionObject` bodies carry the generated per-type message in `Any`.

Central schema-sharing/discovery material for all encoding extensions belongs in `core-specs\xregistry-catalog\`; this folder contains only the Protobuf-specific draft, schemas, examples, and tools.
