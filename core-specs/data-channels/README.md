# OPC UA Data Channels

This folder contains the working draft for **OPC UA — Data Channels**: logical, flow-controlled, bidirectional streams of opaque bytes multiplexed onto a SecureChannel that is already open, so that media and other continuous content can flow over the connection an OPC UA Client already has instead of over a second protocol beside it.

It is written as an **errata package** against three core Parts. OPC UA today has no streaming primitive at all — the Secure Conversation layer carries only the request/response `MSG`, `OPN` and `CLO` message types, and continuous data has to be faked through Part 5 FileTransfer polling or pushed out of the RPC path into Part 14 PubSub.

## Contents

- `OPC-UA-Data-Channels.md` — **standalone combined spec**: a self-contained read merging the three errata below, plus a worked H.264 + Opus + control-channel session, a WebRTC feature-parity comparison, and guidance on when to use a data channel instead of FileTransfer, PubSub or a Subscription. The three errata documents remain the authoritative, insertion-ready proposals.
- `OPC-UA-Part6-Data-Channel-Transport.md` — Part 6 errata: the `STR` frame, flow control, scheduling, partial reliability, and the new `opc.quic` transport.
- `OPC-UA-Part4-Data-Channel-Services.md` — Part 4 errata: the DataChannel Service Set, server-initiated offers, lifecycle, authorization, auditing and StatusCodes.
- `OPC-UA-Part3-Data-Channel-Model.md` — Part 3 errata: `IDataChannelSourceType`, `DataChannelSourceType`, `HasDataChannel`, the DataTypes, the Events and `ServerCapabilities.DataChannelCapabilities`.
- `Opc.Ua.DataChannels.NodeSet2.xml` — generated NodeSet.
- `Opc.Ua.DataChannels.NodeIds.csv` — generated NodeIds.
- `tools/build_model.py` — the single source of truth for the model; emits the NodeSet, the CSV and Annex A.
- `tools/model-reference.md` — generated Annex A, embedded verbatim in the Part 3 errata and the combined spec.
- `tools/validate_local.py` — NodeSet, CSV, Annex and determinism gate.
- `..\extras\data-channels\tools\frame_codec.py` — reference frame encoder/decoder, the executable definition of the wire format.
- `..\extras\data-channels\tools\scheduler_demo.py` — executable demonstration of the three sender obligations.
- `..\extras\data-channels\tools\gen_vectors.py` — deterministic hex wire vectors.
- `..\extras\data-channels\tools\gen_wire_annex.py` — regenerates the annotated byte-layout Annex B.
- `..\extras\data-channels\tools\validate_local.py` — wire tooling acceptance gate.
- `..\extras\data-channels\examples\` — the generated `.hex.txt` wire vectors.

## Two transports, one contract

| | Inline framing (`opc.tcp`, `opc.wss`) | `opc.quic` |
|---|---|---|
| Deployment | Every deployed endpoint, no new port | New transport |
| Multiplexing | Interleaved frames, never chunked | One QUIC stream per channel |
| Genuine loss | No — lossy modes become sender-side discard | Yes, over QUIC DATAGRAM |
| Path change | Kills the connection | Survives, via connection migration |

The Services and the information model are identical on both, so an application is written once and a Client that cannot use QUIC falls back without changing a line.

## Regenerate and validate

From the repository root:

```powershell
python core-specs\data-channels\tools\build_model.py
python core-specs\extras\data-channels\tools\gen_vectors.py
python core-specs\extras\data-channels\tools\gen_wire_annex.py
python core-specs\data-channels\tools\validate_local.py
python core-specs\extras\data-channels\tools\validate_local.py
```

`build_model.py` writes the NodeSet, the CSV and `tools/model-reference.md`, and injects Annex A into the Part 3 errata and the combined spec. `gen_wire_annex.py` injects Annex B into the Part 6 errata and the combined spec. Both generators are deterministic and use no clock or randomness, so regenerating without a source change produces byte-identical output. Neither validator needs untracked base data, so both run in CI through `python core-specs\extras\validate_all.py --self-contained`.

## Provisional identifiers

This is an errata overlay on the **base** OPC UA namespace `http://opcfoundation.org/UA/`, so the NodeSet declares no additional `NamespaceUri`, emits unqualified BrowseNames and plain `i=<n>` NodeIds, and is intended to be merged into the base UA NodeSet rather than loaded beside it.

Draft numeric NodeIds use the provisional `65000+` block (`65000..65099` types, `65100..65199` well-known instances, `65900..65999` EnumStrings, `66000+` members), chosen because `60000`, `62000`, `63000` and `64000` are already used by other drafts in this repository. The `STR` MessageType, the `opcua/1` ALPN identifier, the frame type and flag values and the twelve new StatusCodes are equally provisional. Final assignments are made by the OPC Foundation.
