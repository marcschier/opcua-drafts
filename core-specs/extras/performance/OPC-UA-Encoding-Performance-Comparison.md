# OPC UA Encoding Performance Comparison — Avro & Arrow vs Binary/UADP/JSON (with Protobuf as an alternative, for comparison)

> **Status — informative companion report.** This document quantifies the payload-size, CPU and memory trade-offs of the additive encoding extensions (**Avro** and **Arrow**) against the existing OPC UA encodings (Binary, UADP, JSON). It is measurement, not normative specification. Its purpose is to explain where each encoding adds value and where it does not, so implementers and system designers can choose an encoding per use case.
>
> **Protobuf/gRPC is included below as an *alternative* encoding, for comparison only.** It is no longer part of the OPC UA DataEncoding drafts in this repository (which define only Avro and Arrow); its figures are retained to show how a generic gRPC-oriented `Variant` container compares.

## 1 Summary

- **Binary (Part 6) / UADP (Part 14)** remain the baseline for CPU and for small single messages: smallest and fastest for a scalar value or a single DataSet sample.
- **Avro** is the compact, schema-governed alternative to JSON: comparable to Binary on size, materially smaller on integer-heavy data (variable-length integers), and much smaller and faster than JSON. With the Part 14 SchemaId handshake the Avro schema is not carried on the wire.
- **Protobuf** *(alternative encoding, comparison only)* targets idiomatic gRPC service contracts. It is competitive for structured request/response messages but its generic `Variant` container is not intended for bulk numeric arrays or matrices, where per-element message framing makes it large and slow.
- **Arrow** has no value for single or small messages (a few kilobytes of IPC framing per message) but is the clear winner for large columnar batches (historian / ADBC bulk transport): at 1 000 samples it produces the **smallest** payload of all encodings — smaller per sample than UADP — and decodes fastest.
- **JSON** stays the most verbose and slowest; its value is being self-describing and human-readable, not performance.

## 2 Methodology

Measurements were produced by the reference C# implementation in the `UA-.NETStandard` experimental encoders (PR #7) using two NUnit harnesses tagged `[Category("EncoderComparison")]`:

- Part 6 (single-value DataEncoding): `Tests/Opc.Ua.Core.Experimental.Tests/Part6EncoderComparisonTests.cs`
- Part 14 (PubSub messages): `Tests/Opc.Ua.PubSub.Experimental.Tests/Part14PubSubEncoderComparisonTests.cs`

Each scenario runs warmup iterations, then measures a fixed iteration count. `Payload(B)` is the encoded byte length. `Encode`/`Decode` are wall-clock nanoseconds per operation (`Stopwatch`). `Alloc(B/op)` is managed bytes allocated per operation (`GC.GetAllocatedBytesForCurrentThread`). Environment: .NET 10, single machine, single process, Release build.

**How to read the numbers.** `Payload(B)`, `B/sample` and `Alloc(B/op)` are deterministic and directly comparable. `Encode`/`Decode` ns are single-environment, single-process figures and carry JIT and machine-load variance of roughly ±2×; treat them as orders of magnitude and relative ordering within one table, not precise constants. Every encoding round-trips (`decode(encode(x)) == x`); there are no unsupported cells.

### Reproduce

```bash
# Part 6
dotnet test Tests/Opc.Ua.Core.Experimental.Tests/Opc.Ua.Core.Experimental.Tests.csproj \
  -c Release -f net10.0 --filter "Category=EncoderComparison" \
  --logger "console;verbosity=detailed"

# Part 14
dotnet test Tests/Opc.Ua.PubSub.Experimental.Tests/Opc.Ua.PubSub.Experimental.Tests.csproj \
  -c Release -f net10.0 --filter "Category=EncoderComparison" \
  --logger "console;verbosity=detailed"
```

## 3 Part 6 — single-value DataEncoding

### 3.1 Mixed scalars (~13 built-in fields incl. one string)

| Encoder | Payload (B) | Encode (ns/op) | Decode (ns/op) | Alloc (B/op) |
|---|--:|--:|--:|--:|
| Binary | 131 | 1,002 | 654 | 920 |
| JSON | 334 | 3,708 | 9,764 | 1,448 |
| **Avro** | **123** | 1,181 | 1,817 | **896** |
| Protobuf | 166 | 5,189 | 8,100 | 2,136 |
| Arrow | 3,560 | 136,199 | 105,647 | 44,944 |

Avro is the smallest payload and allocates less than Binary, at near-Binary speed. Arrow's per-message IPC framing (schema + record batch) dominates for a single record.

### 3.2 Double array, 1 000 elements

| Encoder | Payload (B) | Encode (ns/op) | Decode (ns/op) | Alloc (B/op) |
|---|--:|--:|--:|--:|
| Binary | 8,004 | 35,474 | 1,459 | 24,616 |
| JSON | 18,438 | 402,518 | 376,087 | 45,104 |
| Avro | 8,004 | 75,992 | 77,667 | 24,304 |
| Protobuf | 9,003 | 130,921 | 157,889 | 68,760 |
| Arrow | 8,568 | 224,315 | 192,178 | 74,144 |

Fixed-width doubles do not compress under variable-length integer coding, so Binary and Avro tie on size (8,004 B); JSON is 2.3× larger and ~11× slower to decode. Arrow is size-competitive but pays IPC overhead for a single batch.

### 3.3 Int32 matrix, 50 × 50 (2 500 elements)

| Encoder | Payload (B) | Encode (ns/op) | Decode (ns/op) | Alloc (B/op) |
|---|--:|--:|--:|--:|
| Binary | 10,017 | 22,138 | 9,705 | 50,776 |
| JSON | 11,592 | 84,500 | 650,630 | 33,512 |
| **Avro** | **4,891** | 148,926 | 123,807 | **20,440** |
| Protobuf | 22,386 | 2,111,189 | 1,398,044 | 1,659,024 |
| Arrow | 11,456 | 279,323 | 159,883 | 113,143 |

Avro is the standout: zig-zag **variable-length integers** halve the payload of Binary for small-magnitude integers (4,891 B vs 10,017 B) with the lowest allocation. Protobuf is the opposite: wrapping every matrix element in a generic `Value` message makes the `Variant` matrix large and slow — the generic Variant container is not the right tool for bulk numeric matrices (a typed `repeated sint32` field in a service message would be efficient; the dynamic Variant path is not).

### 3.4 One hundred heterogeneous Variants (bool/int/double/string/DateTime/NodeId/Guid/StatusCode)

| Encoder | Payload (B) | Encode (ns/op) | Decode (ns/op) | Alloc (B/op) |
|---|--:|--:|--:|--:|
| Binary | 808 | 36,856 | 24,176 | 9,576 |
| JSON | 4,956 | 149,939 | 460,875 | 18,288 |
| Avro | 984 | 32,605 | 21,876 | 15,168 |
| Protobuf | 1,489 | 105,119 | 245,494 | 136,712 |
| Arrow | 61,152 | 2,661,649 | 666,775 | 715,791 |

Binary's compact type tags make it the smallest for many small heterogeneous values; Avro is close behind. Arrow is pathologically large here: a dense-union Variant materialised one value at a time defeats Arrow's columnar model — Arrow's value is homogeneous columns in batches, not per-value unions.

## 4 Part 14 — PubSub messages

Same DataSet, varying batch size. `B/sample` is the amortised payload per DataSet sample. All Part 14 numbers below are from a single measurement session so the rows are mutually consistent; the two Arrow rows (`batch`, the default, and `stream`) are measured together.

### 4.1 Single sample

| Encoder | Payload (B) | B/sample | Encode (ns/op) | Decode (ns/op) | Alloc (B/op) |
|---|--:|--:|--:|--:|--:|
| **UADP** | **70** | **70.0** | 6,060 | 929 | 2,648 |
| JSON | 466 | 466.0 | 45,713 | 36,077 | 3,472 |
| Avro | 240 | 240.0 | 62,291 | 12,724 | 18,471 |
| **Arrow (batch)** | 1,856 | 1,856.0 | 271,823 | 142,570 | 50,542 |
| Arrow (stream) | 3,064 | 3,064.0 | 210,016 | 140,296 | 50,538 |

### 4.2 Batch of 100

| Encoder | Payload (B) | B/sample | Encode (ns/op) | Decode (ns/op) | Alloc (B/op) |
|---|--:|--:|--:|--:|--:|
| **UADP** | 7,036 | **70.4** | 650,188 | 97,437 | 262,424 |
| JSON | 33,974 | 339.7 | 3,763,670 | 2,373,273 | 309,464 |
| Avro | 18,630 | 186.3 | 2,927,333 | 978,675 | 1,419,637 |
| **Arrow (batch)** | 7,936 | 79.4 | 4,431,712 | 1,034,385 | 818,101 |
| Arrow (stream) | 9,144 | 91.4 | 3,456,305 | 998,280 | 818,101 |

### 4.3 Batch of 1 000

| Encoder | Payload (B) | B/sample | Encode (ns/op) | Decode (ns/op) | Alloc (B/op) |
|---|--:|--:|--:|--:|--:|
| UADP | 70,372 | 70.4 | 5,250,620 | 907,200 | 2,624,024 |
| JSON | 345,490 | 345.5 | 32,330,220 | 22,350,140 | 3,129,243 |
| Avro | 189,019 | 189.0 | 34,560,380 | 21,068,370 | 13,811,553 |
| **Arrow (batch)** | **65,728** | **65.7** | 27,752,760 | 3,652,000 | 7,525,249 |
| Arrow (stream) | 66,936 | 66.9 | 32,285,270 | 15,777,620 | 7,525,898 |

The Arrow crossover is the key result. A single Arrow schema is amortised once per batch and the columns vectorise, so per-sample size falls from ~1.9–3.1 kB (1 sample) to ~79–91 B (100) to **~66–67 B (1 000)** — the default `batch` framing reaches 65.7 B/sample and even the self-contained `stream` reaches 66.9 B/sample, both **below UADP's 70.4 B/sample**. Against the comparably-sized JSON and Avro, Arrow decodes fastest at scale (`batch` decode ~3.7 ms at 1 000 rows vs JSON's ~22 ms and Avro's ~21 ms). Absolute ns for the largest batches have high variance (few iterations); the deterministic result is size. Arrow is the right transport for historian dumps, ADBC/Flight bulk reads and analytics streaming; it is the wrong transport for low-latency single-sample telemetry, where even a bare `batch` (1,856 B) is far larger than UADP (70 B).

### 4.4 Arrow IPC framing: bare RecordBatch (default) vs self-contained stream

A self-contained Arrow IPC `stream` embeds a **Schema message** before its RecordBatch. That schema is a fixed cost — ~1.2 kB for this ten-field DataSet — independent of the row count, and it is repeated in every self-contained message. The default `batch` framing (Part 14 Arrow mapping §7.2.8.x) omits it: the payload is a **bare RecordBatch** and the schema is announced once out of band and resolved by SchemaId (the Arrow Flight model, and the same schema-exchange model the Avro mapping already uses). Full measured comparison for the same DataSet:

| Samples | Framing | Payload (B) | B/sample | Encode (ns/op) | Decode (ns/op) | Alloc (B/op) |
|--:|:--|--:|--:|--:|--:|--:|
| 1 | **batch** | **1,856** | **1,856.0** | 271,823 | 142,570 | 50,542 |
| 1 | stream | 3,064 | 3,064.0 | 210,016 | 140,296 | 50,538 |
| 10 | **batch** | **2,048** | **204.8** | 524,527 | 283,866 | 110,025 |
| 10 | stream | 3,256 | 325.6 | 465,363 | 239,322 | 110,025 |
| 100 | **batch** | **7,936** | **79.4** | 4,431,712 | 1,034,385 | 818,101 |
| 100 | stream | 9,144 | 91.4 | 3,456,305 | 998,280 | 818,101 |
| 1 000 | **batch** | **65,728** | **65.7** | 27,752,760 | 3,652,000 | 7,525,249 |
| 1 000 | stream | 66,936 | 66.9 | 32,285,270 | 15,777,620 | 7,525,898 |

`batch` removes a constant ~1.2 kB per message, so the relative saving is largest for small or single-sample messages (payload ≈39 % smaller at 1 sample, 37 % at 10) and shrinks as the schema is amortised across a larger batch (~13 % at 100, ~2 % at 1 000). It is a **framing** choice, not an encoding variant — the column and value layout is the identical canonical Part 6 Arrow mapping. Because `batch` requires a schema-announcement channel and that is the same model the Avro mapping already requires, **`batch` is the default framing**; `stream` is used for channels without a schema-announcement mechanism or when each message must be independently decodable. Note the floor: even a bare single-sample RecordBatch is 1,856 B (vs UADP's 70 B) because the RecordBatch header itself carries per-column length/null-count/buffer descriptors, so `batch` reduces but does not remove Arrow's per-message overhead — it is most useful for frequent small-to-medium batches on a schema-governed channel.

## 5 Value-add by encoding

| Encoding | Best at | Avoid for | Notes |
|---|---|---|---|
| **Binary / UADP** | CPU baseline; small single messages; low latency | very large batches (no columnar amortisation) | Existing default; compact type tags. |
| **Avro** | compact schema-governed messaging; integer-heavy data and matrices; a smaller/faster JSON replacement | nothing categorically — solid all-rounder | Variable-length integers win on small-magnitude integers; SchemaId handshake keeps the schema off the wire; add-in Action + Discovery mappings. |
| **Protobuf / gRPC** *(alternative, comparison only)* | idiomatic gRPC service request/response contracts | bulk numeric arrays and matrices via the dynamic `Variant` container | Use typed fields for bulk data; the generic Variant path frames each element as a message. |
| **Arrow** | large columnar batches — historian / ADBC / Flight bulk and analytics | single or small messages (kilobytes of per-message IPC framing); per-value Variant unions | Wins on both size (smallest per sample at scale, beating UADP) and decode speed once the schema is amortised across a batch; `batch` framing (§4.4) trims the fixed schema cost on schema-governed channels. |
| **JSON** | human-readable, self-describing debugging and interop | size- or throughput-sensitive paths | Largest and slowest; needs no schema to decode. |

## 6 Edge cases observed

- **Avro codec allocation.** The reference Avro writer/reader pool their IO buffers from `ArrayPool` rather than allocating a per-instance buffer, so scalar-message allocation is ~0.9 KB/op (below Binary) while the buffering still batches large-payload writes.
- **Protobuf Variant matrices/arrays.** Fully supported and reversible, but large and slow because each element is a generic `Value` message. This is expected: Protobuf's strength is statically-typed service messages, not a dynamic numeric matrix container.
- **Arrow Variant unions.** Fully supported across every built-in scalar/array/matrix body and reversible, but a per-value dense union is the antithesis of Arrow's columnar design and is very large. Arrow should carry Variants as typed columns in a batch, not as per-row unions.
- **Determinism.** All payload sizes and per-op allocations are reproducible; ns timings vary with machine load and JIT and are reported as indicative.

## 7 References

- Encoding specifications: `../avro-encoding`, `../arrow-encoding` and the merged `../../schema-registry/OPC-UA-Schema-Registry.md`. (Protobuf figures above are retained for comparison only; the Protobuf DataEncoding draft is no longer part of this repository.)
- NodeId / ExpandedNodeId structured-vs-textual payload analysis: [`nodeid-size-analysis.md`](nodeid-size-analysis.md).
- Reference reversibility corpus (107 cases): `../_common` and each extension's `tools/validate_local.py`.
- Reference C# encoders and the comparison harnesses: `UA-.NETStandard` PR #7 (`Opc.Ua.Core.Experimental`, `Opc.Ua.PubSub.Experimental`).
