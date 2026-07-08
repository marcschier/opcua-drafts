# NodeId / ExpandedNodeId payload-size comparison

All sizes are bytes. Structured Avro/Protobuf are the encoded NodeId or ExpandedNodeId value only. Text rows use the portable `nsu=<uri>` spelling; `ns=index raw` is the server-local spelling shown only for reference.

Representative text constants: default URI `http://example.org/UA/`; case 6 URI `http://example.org/UA/Line3/`; case 7 URI `https://example.org/UA/Very/Long/Namespace/Uri/For/Line3/`; string id `Some.Long.Browse.Path.To.A.Signal`; GUID `00112233-4455-6677-8899-aabbccddeeff`; opaque bytes are 8 bytes rendered as base64 `AQIDBAUGBwg=`.

| case | Avro structured | Protobuf structured | Arrow structured per-value | text nsu raw | Avro text | Protobuf text | Arrow text | ns=index raw |
|---|---|---|---|---|---|---|---|---|
| 1 numeric small | 8 | 5 | 31.5 | 33 | 34 | 35 | 37 | 11 |
| 2 numeric large | 11 | 8 | 31.5 | 39 | 40 | 41 | 43 | 18 |
| 3 string id | 40 | 39 | 64.5 | 62 | 63 | 64 | 66 | 40 |
| 4 guid id | 22 | 22 | 31.5 | 65 | 67 | 67 | 69 | 43 |
| 5 opaque id | 15 | 14 | 39.5 | 41 | 42 | 43 | 45 | 19 |
| 6 Expanded URI numeric | 38 | 34 | 67.625 | 36 | 37 | 38 | 40 | 8 |
| 7 Expanded long URI string+svr | 100 | 100 | 129.625 | 103 | 105 | 105 | 107 | 46 |

## Method

- Avro structured is computed from the current record schema: `namespace:int`, `idType:int`, and four nullable identifier fields. Avro `int`/`long` and string/bytes lengths use zig-zag varints; nullable union branch indexes are Avro longs. Avro fastavro schemaless cross-check: numeric-small=8 B, string-id=40 B.
- Protobuf structured is computed from the current `proto3` `NodeId`/`ExpandedNodeId` messages: tags plus varints/length prefixes. Default-valued scalar fields (`namespace=0`, `id_type=NUMERIC`, `server_index=0`) are omitted, but a selected oneof arm is serialized.
- Arrow structured is an amortized per-added-value contribution for the current columnar struct: NodeId fixed/offset slots plus nullable-child validity bits. It includes fixed-width child slots even when that child is logically null: namespace 2, id_type 1, numeric 4, string offset delta 4, guid 16, opaque offset delta 4, and four validity bits = 31.5 B before active string/opaque data. Batch buffers round bitmaps and final offsets up, so very small batches can differ.
- Text Avro is raw UTF-8 text plus an Avro string length varint; text Protobuf is one small-field string tag plus protobuf length varint; text Arrow is raw UTF-8 text plus one utf8 offset delta (4 B).

## Analysis

- Common numeric NodeId (case 1) is 8 B in Avro structured, 5 B in Protobuf structured, and 31.5 B/value in the current Arrow struct; the portable text is 34/35/37 B respectively.
- For case 1, portable text is therefore 4.25x Avro structured, 7.00x Protobuf structured, and 1.17x the current Arrow per-value struct.
- Numeric-large (case 2) remains compact structurally: 11 B Avro and 8 B Protobuf versus 40/41 B portable text.
- String identifiers are the closest row-wise match: case 3 is 40 B Avro and 39 B Protobuf versus 63/64 B portable text; Arrow struct is 64.5 B versus 66 B text.
- GUID text loses badly for Avro/Protobuf because 16 binary bytes become a 36-character GUID string; Protobuf is 22 B structured versus 67 B text.
- Opaque text also expands because 8 binary bytes become 12 base64 characters, but Arrow text is slightly larger than the Arrow struct because the current struct already has a high fixed-slot cost.
- ExpandedNodeId with a namespace URI is where structured Avro/Protobuf and portable text converge: case 6 is 38/34 B structured versus 37/38 B text.
- Long URI plus string plus server index (case 7) is effectively equal for Avro/Protobuf structured and portable text: Avro 100 vs 105 B, Protobuf 100 vs 105 B.
- Arrow is the outlier: replacing the six-child NodeId struct plus ExpandedNodeId wrapper with a single utf8 column saves schema and buffer complexity, and in cases 3, 6, and 7 it is also smaller or similar per value.
- The `ns=<index>` spelling is much smaller (for example 11 B instead of 33 B in case 1), but it is server/session-local and not portable without the namespace table.
- The `nsu=<uri>` spelling is portable across sessions and endpoints, but pays the URI bytes on every value unless dictionary encoding or separate namespace columns are added.
- Reversibility requires exact escaping for `;` and `=` inside string identifiers, base64 for opaque ByteStrings, canonical GUID formatting, and preserving `svr=<n>` when `serverIndex != 0`.

## Recommendation

Do not replace structured NodeId globally for all encodings if payload size is the primary criterion: Avro and especially Protobuf numeric/GUID/opaque NodeIds are much smaller in structured form. A textual NodeId is defensible for Arrow-only columns, where the current nested nullable struct has high fixed-slot/schema complexity and text is competitive, especially for string and ExpandedNodeId values. For row encodings, use textual form only when portability/readability outweighs the measured size cost, or combine it with dictionary/namespace interning.

The strongest case is Arrow's primary use case — large historian/analytics batches where the same NodeIds repeat across many rows. There a **dictionary-encoded `utf8` NodeId column** is both the simplest schema (one string column instead of a six-child nullable struct plus an ExpandedNodeId wrapper) and, after each distinct value's first occurrence, the most compact representation, because the per-row cost collapses to a dictionary index. This combination of columnar simplicity and repetition-amortised size is why the textual form is worth adopting for Arrow specifically, while the row encodings keep the compact structured form.
