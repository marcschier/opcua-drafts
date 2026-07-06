# OPC UA Protobuf Encoding extension

Working draft assets for OPC UA service calls over gRPC using proto3. The standard draft docs and base schema live here; executable tooling and generated non-base assets live under `core-specs\extras\protobuf-encoding\`. Shared type descriptors, values, the corpus, NodeSet loader, and JSON control codec are read from `core-specs\extras\_common\opcua_enc` as a read-only API.

## Contents

- `OPC-UA-Part6-Protobuf-DataEncoding.md` — proposed OPC 10000-6 v1.05.07 DataEncoding insertion for OPC UA Protobuf values and service Structures.
- `OPC-UA-Part6-Protobuf-gRPC-Transport.md` — proposed OPC 10000-6 v1.05.07 TransportProtocol insertion for OPC UA gRPC service calls.
- `../extras/protobuf-encoding/tools/build_schemas.py` — deterministic NodeSet/corpus-driven `.proto` generator.
- `../extras/protobuf-encoding/tools/protobuf_codec.py` — reversible reference codec over compiled protobuf messages.
- `../extras/protobuf-encoding/tools/roundtrip.py` — runs the 102-case shared `CORPUS` through `decode(encode(x))`.
- `../extras/protobuf-encoding/tools/validate_local.py` — local acceptance gate: schema determinism, `.proto` compilation, 102-case corpus round-trip, published-schema conformance, byte annotations, SchemaId drift checks, nested SchemaId closure checks, dynamic decode, and byte-stable examples.
- `schemas\opcua_builtins.proto` — base OPC UA Protobuf value/envelope schema.
- `../extras/protobuf-encoding/schemas/` — generated non-base reference proto3 schemas and `schemaids.json`.
- `../extras/protobuf-encoding/examples/` — representative encoded payload bytes and `index.json`.

## Usage

Install the protobuf compiler plugin once if needed:

```powershell
python -m pip install grpcio-tools
```

Run the acceptance gate from the repository root:

```powershell
python core-specs\extras\protobuf-encoding\tools\validate_local.py
```

Regenerate schemas only:

```powershell
python core-specs\extras\protobuf-encoding\tools\build_schemas.py
```

Run only the reversibility harness:

```powershell
python core-specs\extras\protobuf-encoding\tools\roundtrip.py
```

## Design notes

The canonical wire form is proto3 with explicit presence. OPC UA Services map to gRPC unary methods, with Publish/subscription-style Services using streaming where the service semantics require it. Request and response messages encode the OPC UA Part 4 Service request/response Structures using the Part 6 Protobuf DataEncoding. Structures and unions are encoded as the generated per-type messages in `../extras/protobuf-encoding/schemas/`; the reflective `Value` envelope is not an alternate structure encoding. Nullable scalar values and optional structure fields use nullable wrappers (`StringValue`, `ByteStringValue`) or message/oneof presence. Nullable elements inside `repeated` fields use a wrapper message strategy: an empty `Value` wrapper is the canonical null element, while a present `Value` with an empty string or empty bytes is an empty value. `DateTime` is raw signed 100 ns ticks in `sfixed64`; `UInt64` is protobuf `uint64`; `Guid` is exactly 16 bytes. `Variant` carries the OPC UA built-in type id plus exactly one scalar, array, or matrix payload; the empty `Variant` message is null. Known `ExtensionObject` bodies carry the generated per-type message in `Any`.

The service `.proto` or transitive `FileDescriptorSet` is the shared contract. Its SchemaId is the existing transitive-closure SHA-256 identifier and is registered in the xRegistry catalog for discovery. gRPC calls use `application/grpc+proto`; OPC UA Session/authentication tokens and request headers ride in gRPC metadata.

Central schema-sharing/discovery material for all encoding extensions belongs in `core-specs\schema-registry\OPC-UA-Schema-Registry.md`; this folder contains only the Protobuf-specific draft, schemas, examples, and tools.
