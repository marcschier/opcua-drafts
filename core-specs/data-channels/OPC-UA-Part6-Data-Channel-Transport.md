# OPC UA Part 6 — Data Channel Transport

**Working draft for submission to the OPC Foundation Working Group**
**Proposed addition to:** OPC 10000-6 Mappings v1.05.07
**Namespace:** `http://opcfoundation.org/UA/` (base OPC UA namespace)
**Version:** 0.1.0 · **Date:** 2026-07-27

> **Status — working draft.** This document proposes the transport layer for OPC UA **data channels**: logical, flow-controlled, bidirectional streams of opaque bytes multiplexed onto a SecureChannel that is already open. It defines an inline framing for the existing `opc.tcp` and `opc.wss` transports and a new `opc.quic` transport. The Services that open and close a data channel are in the companion [Part 4 errata](OPC-UA-Part4-Data-Channel-Services.md); the AddressSpace model that describes where one may be opened is in the [Part 3 errata](OPC-UA-Part3-Data-Channel-Model.md). Nothing here is normative or endorsed by the OPC Foundation.

---

## 1 Scope

This specification defines how a continuous stream of application bytes is carried over an OPC UA SecureChannel, alongside — not instead of — the Service request/response traffic already on it.

It covers the frame layout, the multiplexing of many concurrent channels onto one connection, flow control, sender scheduling, delivery modes including partial reliability, gap notification, half-close, abort and round-trip measurement. It defines the mapping of that framing onto the existing OPC UA TCP and WebSocket transports, and it defines a new QUIC transport in which each data channel is a native QUIC stream and unreliable payload rides QUIC DATAGRAM frames.

It does not define the Services that open, modify or close a data channel, the AddressSpace model that describes a channel endpoint, or any interpretation of the bytes a channel carries. A data channel is content-agnostic: the payload is opaque octets qualified by an IANA media type, and codecs, packetization and presentation timing are the concern of the application at each end.

## 2 Normative references

- [OPC 10000-2](https://reference.opcfoundation.org/specs/OPC-10000-2/) — Security Model.
- [OPC 10000-3](https://reference.opcfoundation.org/specs/OPC-10000-3/) — Address Space Model.
- [OPC 10000-4](https://reference.opcfoundation.org/specs/OPC-10000-4/) — Services.
- [OPC 10000-6 v1.05.07](https://reference.opcfoundation.org/specs/OPC-10000-6/) — Mappings.
- [OPC 10000-7](https://reference.opcfoundation.org/specs/OPC-10000-7/) — Profiles.
- [IETF RFC 9000](https://www.rfc-editor.org/rfc/rfc9000) — QUIC: A UDP-Based Multiplexed and Secure Transport.
- [IETF RFC 9001](https://www.rfc-editor.org/rfc/rfc9001) — Using TLS to Secure QUIC.
- [IETF RFC 9002](https://www.rfc-editor.org/rfc/rfc9002) — QUIC Loss Detection and Congestion Control.
- [IETF RFC 9221](https://www.rfc-editor.org/rfc/rfc9221) — An Unreliable Datagram Extension to QUIC.
- [IETF RFC 6455](https://www.rfc-editor.org/rfc/rfc6455) — The WebSocket Protocol.
- [IETF RFC 7301](https://www.rfc-editor.org/rfc/rfc7301) — TLS Application-Layer Protocol Negotiation (ALPN).

## 3 Terms, definitions and abbreviations

| Term | Definition |
|---|---|
| Data channel | A logical, independently flow-controlled, bidirectional stream of opaque bytes carried over one SecureChannel and identified within it by a ChannelId. |
| Frame | One data channel protocol data unit. In inline framing a frame is exactly one Secure Conversation MessageChunk; in QUIC framing it is one length-delimited unit on a QUIC stream or one QUIC DATAGRAM. |
| Inline framing | The framing of clause 5 as carried over `opc.tcp` and `opc.wss`, interleaved with `MSG` chunks on the same connection. |
| ChannelId | The identifier of a data channel within its SecureChannel, assigned by the Server in `OpenDataChannel`. ChannelId 0 is reserved for connection-level control. |
| Credit | The number of payload bytes a sender is permitted to transmit before the receiver grants more. Maintained per channel and per connection. |
| Droppable frame | A frame the sender is permitted to discard, rather than transmit, once its deadline has passed. |
| Gap | A contiguous run of FrameSequenceNumbers that was discarded or lost and will not be delivered. |
| Logical message | An application-level unit of payload delimited by the `MessageStart` and `MessageEnd` flags, possibly spanning many frames. |
| Control channel | ChannelId 0, which carries connection-level `CREDIT`, `PING` and `PONG` frames and never carries payload. |

Key words **shall**, **should**, **may** and **shall not** are to be interpreted as in the ISO/IEC directives.

## 4 Overview

### 4.1 What is missing today

OPC UA moves data by asking for it. `Read` returns a value, `Publish` returns a batch of notifications, and Part 5 `FileType` returns a slice of a file to a client that keeps asking for the next one. Every one of these is a complete request paired with a complete response, and the Secure Conversation layer is built for exactly that: a Message is chunked, every chunk is reliable and ordered, and nothing is interpreted until the whole Message has arrived.

A camera does not work that way. Neither does a microphone, a log tail, a point cloud, a firmware image being pushed to a drive, or a remote console. These produce a continuous flow whose value decays with age, and the operations that suit them — start it, throttle it, prioritize it against other traffic, drop what is already too late to be useful, stop it — have no expression in OPC UA at all. In practice they are solved by running a second protocol beside the OPC UA endpoint, which means a second port, a second set of certificates, a second authorization model and a second hole in the firewall, for data that came from the same device and is governed by the same policy.

### 4.2 Two realizations, one model

A data channel closes that gap on the connection the client already has. Two transport realizations are defined, and the Services and AddressSpace model above them are identical on both:

| | Inline framing (`opc.tcp`, `opc.wss`) | `opc.quic` |
|---|---|---|
| Deployment | Works on every deployed endpoint, no new port, no new certificate | New transport, new endpoint |
| Multiplexing | Frames of different channels interleave on one byte stream | One QUIC stream per channel |
| Head-of-line blocking | Between channels: none, because a frame is never chunked. Below the framing: TCP still orders the whole connection | None, QUIC orders each stream independently |
| Flow control | Credit windows defined here | QUIC's own per-stream and per-connection windows |
| Genuine loss | Impossible; lossy modes become sender-side discard | Real, over QUIC DATAGRAM |
| Path change | Kills the connection | Survives, through QUIC connection migration |

An implementation that supports only inline framing is a complete implementation of this specification. QUIC adds capability that TCP cannot express; it does not change the contract.

### 4.3 What is deliberately not changed

The value of this design is in what it leaves alone.

- **The Secure Conversation layer.** An inline frame is a `MessageChunk` with a different three-byte `MessageType`. Its Message header, security header, sequence header and footer are byte-for-byte those of a `MSG` chunk, so the securing, verification, sequence-number and channel-token-rollover rules of OPC 10000-6 §6.7.3 to §6.7.7 apply without a word of change.
- **The connection protocol.** `Hello` and `Acknowledge` are **not** modified and `ProtocolVersion` is **not** bumped. A data-channel-capable Client and a legacy Server therefore still connect: the capability is simply never advertised. Annex A explains why the alternative was rejected.
- **The chunk assembler.** A frame is always a single chunk, so `MaxMessageSize` and `MaxChunkCount` are untouched and a partially received data channel frame cannot exist.
- **The security model.** A data channel is opened by a Service call on an activated Session and is authorized by the user identity behind it, exactly as any other operation on the Node it targets.

## 5 Data channel framing

### 5.1 The STR MessageChunk

A data channel frame carried by inline framing is an OPC UA Secure Conversation MessageChunk whose `MessageType` is the three ASCII bytes `STR`. It is added to the values enumerated in OPC 10000-6 §6.7.2.2:

| MessageType | Meaning |
|---|---|
| `MSG` | A Service request or response (unchanged). |
| `OPN` | `OpenSecureChannel` (unchanged). |
| `CLO` | `CloseSecureChannel` (unchanged). |
| `STR` | **New.** One data channel frame. |

The layout is:

```text
Message header            12 bytes   MessageType[3] · IsFinal[1] · MessageSize · SecureChannelId
Symmetric security header  4 bytes   TokenId
Sequence header            8 bytes   SequenceNumber · RequestId
--------------------------------------------- start of the secured body
Stream header             12 bytes   ChannelId · FrameType · Flags · Reserved · FrameSequenceNumber
Deadline                   8 bytes   present only when the DeadlinePresent flag is set
Frame type fields         0-8 bytes  determined by FrameType (§5.3)
Payload                    varies    DATA frames only
--------------------------------------------- end of the secured body
Message footer             varies    PaddingSize, Padding and Signature, per §6.7.2.5
```

The following rules apply to the reused headers:

- `IsFinal` **shall** be `F`. A data channel frame is always a single chunk (§5.5). `A` **may** be sent to abort the SecureChannel under the existing rules; `C` **shall not** be sent and a receiver **shall** treat it as a protocol error.
- `SecureChannelId`, `TokenId` and `SequenceNumber` are those of the enclosing SecureChannel. `STR` frames share the single monotonically increasing `SequenceNumber` sequence with `MSG`, `OPN` and `CLO`, because that sequence is what protects the channel against replay, reordering and injection. A separate sequence per data channel would weaken it.
- `RequestId` **shall** be `0` and a receiver **shall** reject a frame that carries any other value. A data channel frame is not a Service invocation. Folding the ChannelId into `RequestId` was considered and rejected (Annex A): a Client allocates RequestIds, so no allocation rule could keep the two spaces from colliding.

A Server **shall not** send a `STR` frame on a SecureChannel on which no data channel has been opened, and a receiver **shall** treat such a frame as a protocol error and close the SecureChannel.

### 5.2 Stream header

Every frame begins its secured body with the stream header:

| Field | Type | Description |
|---|---|---|
| ChannelId | UInt32 | The data channel this frame belongs to, as assigned by `OpenDataChannel`. `0` is the connection control channel (§5.6). |
| FrameType | Byte | The frame type (§5.3). |
| Flags | Byte | The flags (§5.4). |
| Reserved | UInt16 | **Shall** be `0`; a receiver **shall** reject a non-zero value. Reserved for a future revision, and aligning the following field on a four-byte boundary. |
| FrameSequenceNumber | UInt32 | A per-channel counter, starting at `1` for the first frame the sender emits on the channel in that direction, incremented by one for every frame including control frames, and wrapping to `1` after `4294967295`. |

`FrameSequenceNumber` is therefore **never `0`**, and a receiver **shall** reject a frame that carries `0`. The connection control channel (§5.6) is no exception: it counts its own sequence like any other ChannelId. Reserving `0` costs one value out of four billion and buys an unambiguous "this field was never set" signal, which is worth more than the value.

`FrameSequenceNumber` is what makes loss visible. A receiver detects a gap by observing a discontinuity, without waiting for and without depending on a `GAP` frame — which matters over QUIC DATAGRAM, where the notification may itself be lost.

All integers are little-endian, matching the OPC UA Binary DataEncoding.

### 5.3 Frame types

| Value | Name | Extra fields | Purpose |
|---|---|---|---|
| 0 | `DATA` | — | Carries payload. The only frame type that does. |
| 1 | `CREDIT` | `ChannelCredit` UInt32, `ConnectionCredit` UInt32 | Grants flow control window (§5.8). |
| 2 | `GAP` | `FirstDiscarded` UInt32, `LastDiscarded` UInt32 | Reports a run of frames that will never arrive (§5.10). |
| 3 | `RESET` | `StatusCode` UInt32 | Aborts one data channel (§5.11). |
| 4 | `END` | — | Orderly half-close of one direction (§5.11). |
| 5 | `PING` | `Timestamp` Int64 | Round-trip probe and keepalive (§5.11). |
| 6 | `PONG` | `Timestamp` Int64 | Echo of a `PING` (§5.11). |

Values `7` to `255` are reserved. A receiver **shall** reject a frame carrying a reserved value; silently ignoring it would let a sender believe payload was delivered. Only `DATA` frames carry payload, and a receiver **shall** reject any other frame type that is followed by payload bytes.

### 5.4 Flags

| Bit | Name | Meaning |
|---|---|---|
| `0x01` | `MessageStart` | This frame begins a logical application message. |
| `0x02` | `MessageEnd` | This frame ends a logical application message. A frame with both bits set is a complete message. |
| `0x04` | `Droppable` | The sender **may** discard this frame instead of transmitting it once its deadline passes (§5.9). |
| `0x08` | `DeadlinePresent` | The eight-byte `Deadline` field follows the stream header. |
| `0x10` | `Marker` | An application-defined synchronization point, for example a video key frame. A receiver that has just recovered from a gap can resume at the next `Marker` without understanding the payload. |
| `0xE0` | reserved | **Shall** be `0`; a receiver **shall** reject a frame that sets any of these bits. |

`Deadline` is a signed 64-bit count of 100 ns intervals since 1601-01-01 UTC, on the **sender's** clock. It is never compared across the two ends: it exists so a sender can decide whether a frame it is still holding is worth transmitting, which needs no clock synchronization at all. It is optional precisely so that a reliable channel never pays its eight bytes.

`MessageStart` and `MessageEnd` are how an application delimits a unit larger than one frame without reintroducing chunking into the security layer. A receiver **shall** deliver payload to the application in frame order; whether it withholds delivery until `MessageEnd` is an application decision.

### 5.5 Frame size and the single-chunk rule

A data channel frame **shall** be exactly one MessageChunk. This is the single most important constraint in this specification: a multi-chunk frame would sit in the existing chunk assembler and block every other Message on the connection until it completed, which is the precise failure a streaming layer exists to avoid.

The total encoded size of a frame **shall not** exceed the `ReceiveBufferSize` the peer declared in its `Hello` or `Acknowledge`. The usable payload is that limit less the fixed overhead:

| Framing | Fixed overhead | Optional |
|---|---|---|
| Inline | 12 (message header) + 4 (security header) + 8 (sequence header) + 12 (stream header) = **36 bytes** | + 8 (`Deadline`) + frame type fields + the security policy's footer |
| QUIC | 12 (message header) + 12 (stream header) = **24 bytes** | + 8 (`Deadline`) + frame type fields |

A Server computes the resulting bound and returns it as `RevisedMaxFrameSize` in `OpenDataChannel`, so an application never has to derive it. An application unit larger than one frame is segmented across frames using `MessageStart` and `MessageEnd`.

### 5.6 The connection control channel

ChannelId `0` is reserved and is never assigned by `OpenDataChannel`. It carries only `CREDIT` frames that grant the connection-level window, and `PING` and `PONG`. A receiver **shall** reject any other frame type on ChannelId `0`, and **shall** reject payload on it.

Separating connection-level control from any particular channel is what lets the connection window be replenished while every individual channel is stalled, and lets the round trip be probed on a connection that currently has no data channel open at all.

### 5.7 Interleaving and scheduling

A sender **may** interleave `STR` frames with `MSG`, `OPN` and `CLO` chunks and with `STR` frames of other ChannelIds, in any order. Because a frame is never chunked, a receiver needs no reassembly state and no interleaving rule beyond the existing one.

Two scheduling obligations are normative:

1. **Service traffic has precedence.** A sender **shall not** delay a `MSG`, `OPN` or `CLO` chunk that is ready to send by more than the transmission of one maximum-size data channel frame. Without this, a saturated video channel starves the `Publish` response path and the Session dies of a keepalive timeout while the connection is busy.
2. **No channel starves.** Among data channels that have payload ready and credit available, a sender **shall** serve every such channel at least once before it serves any channel a second time beyond its priority weighting. Priority (0 lowest to 7 highest, negotiated per channel) determines *share*, never *exclusivity*.

A weighted deficit round robin over the ready channels, with the Service queue drained between frames, satisfies both. A reference implementation is `core-specs/extras/data-channels/tools/scheduler_demo.py`.

### 5.8 Flow control

Every data channel has a **channel credit** and the connection has a **connection credit**, both counted in `DATA` payload bytes and both maintained by the sender as the peer's remaining willingness to receive.

- Initial channel credit is `RevisedInitialCredit` from `OpenDataChannel`. Initial connection credit is the Server's `MaxCreditPerChannel` aggregate, announced in the first connection-level `CREDIT` frame.
- A sender **shall not** transmit a `DATA` frame whose payload length exceeds either remaining credit. It waits, and the channel is in the `Paused` state.
- `CREDIT`, `GAP`, `RESET`, `END`, `PING` and `PONG` frames are **exempt** from flow control. A creditable `CREDIT` frame would deadlock a stalled channel permanently, and a channel that cannot be reset or probed while stalled cannot be recovered.
- A `CREDIT` frame on a ChannelId other than `0` grants `ChannelCredit` to that channel and, if `ConnectionCredit` is non-zero, that amount to the connection as well. On ChannelId `0`, `ChannelCredit` **shall** be `0`.
- Credit is additive and **shall not** overflow `2^32 - 1`; a sender that receives a grant that would overflow **shall** reset the channel with `Bad_DataChannelCreditExceeded`.

Backpressure is therefore per channel: a consumer that cannot keep up with a video stream stalls that stream and nothing else. The connection window exists so the sum of channels cannot exhaust the receiver's memory even when each is individually within its window.

### 5.9 Delivery modes and partial reliability

The delivery mode is negotiated per channel by `OpenDataChannel`. What it can actually deliver depends on the transport, and this specification states the difference rather than hiding it:

| Mode | Inline framing over TCP | `opc.quic` |
|---|---|---|
| `ReliableOrdered` | Exact. TCP already provides it. | Exact. One QUIC stream provides it. |
| `ReliableUnordered` | Every frame arrives; the receiver may deliver frames to the application without waiting to restore order. Over TCP this saves buffering, not latency. | Exact, across the DATAGRAM path. |
| `PartiallyReliable` | Sender-side: a droppable frame still queued at its deadline is discarded. `MaxRetransmits` has no effect, because TCP owns retransmission. | Retransmission over DATAGRAM up to `MaxRetransmits` or the deadline, then abandoned. |
| `Unreliable` | Sender-side discard only. Once a byte is written to the socket, TCP will deliver it. | Exact. A DATAGRAM is sent once and never retransmitted. |

The honest summary for inline framing is that **loss happens in the send queue, not on the wire**. That is a real and useful property — it bounds latency and discards stale media in favour of fresh media — and it is what a TCP-based media path can offer. A Server that needs genuine in-flight loss offers an `opc.quic` endpoint and says so through `SupportsUnreliableDatagrams`.

A sender **shall** apply deadline expiry only to frames carrying `Droppable`. A frame without that flag is transmitted however late it is.

### 5.10 Gap notification

When a sender discards one or more frames, it **shall** emit a `GAP` frame on the same channel naming the discarded range in `FirstDiscarded` and `LastDiscarded` inclusive. The `GAP` frame consumes a `FrameSequenceNumber` of its own, so the discarded range is always strictly below it.

A receiver that observes a `FrameSequenceNumber` discontinuity **shall** treat the missing range as lost whether or not a `GAP` frame arrives. `GAP` is an optimization: it tells the receiver immediately, rather than at the next frame, and it distinguishes "discarded, never coming" from "delayed". Without it a media decoder cannot tell a stall from a loss, and therefore cannot decide whether to conceal or to wait.

A `GAP` frame **shall not** be sent for a `ReliableOrdered` or `ReliableUnordered` channel; a receiver **shall** treat one as a protocol error, because on a reliable channel nothing may be discarded.

### 5.11 Reset, half-close and round-trip measurement

- **`RESET`** aborts one data channel and nothing else. The sender discards its queue for that channel, the receiver discards its reassembly state, the channel enters `Faulted`, and the ChannelId becomes reusable once both ends have seen the reset. The SecureChannel, the Session and every other data channel are unaffected. This separation is the point: a failed stream is not a failed connection.
- **`END`** half-closes: the sender will emit no further `DATA` on this channel in this direction, after already-queued frames drain. On a `Bidirectional` channel the opposite direction continues until it sends its own `END`. When both directions have ended, the channel enters `Closed`.
- **`PING`** and **`PONG`** measure the round trip and keep an idle connection alive. A receiver **shall** answer a `PING` with a `PONG` copying the `Timestamp` verbatim and **should** do so ahead of queued `DATA`, so the measurement reflects the path rather than the queue. Copying rather than restamping means the prober keeps no state. `PING` on ChannelId `0` measures the connection; on a data channel it additionally confirms that channel is alive.

### 5.12 Error handling

A frame that violates any **shall** in this clause is a protocol error. The receiver's response depends on how localized the fault is:

| Fault | Response |
|---|---|
| Unknown ChannelId, unsupported frame type on a valid channel, payload on a non-`DATA` frame, `GAP` on a reliable channel, credit overflow | `RESET` that channel with the matching StatusCode. The connection continues. |
| Malformed header, non-zero `Reserved` or reserved flag bits, non-zero `RequestId`, `FrameSequenceNumber` of `0`, `IsFinal` of `C`, a frame too short to hold the header its own `FrameType` and flags imply, frame larger than the negotiated buffer, `STR` with no data channel open | Close the SecureChannel under the existing OPC 10000-6 §6.7.7 rules, sending a transport error Message first if the receiver is the Server. |

The dividing line is whether the sender's framing can still be trusted. A bad ChannelId is a bug in one stream; a bad header means the byte stream is no longer being parsed the way the sender wrote it, and no further frame on it can be believed.

## 6 Transport bindings for inline framing

### 6.1 OPC UA TCP

No change to OPC 10000-6 §7.2 is required. A `STR` frame is a MessageChunk and is written to the socket exactly as `MSG` chunks are. The URL scheme remains `opc.tcp` and the TransportProfileUri is unchanged.

### 6.2 WebSockets

No change to OPC 10000-6 §7.5 is required. Under the `opcua+uacp` sub-protocol each WebSocket binary frame is one MessageChunk, and a `STR` frame is one MessageChunk, so it is one WebSocket binary frame. No new sub-protocol is registered.

### 6.3 HTTPS and SOAP/HTTP

Data channels are **not** available over OPC UA HTTPS (§7.4). That transport carries one Service request and one Service response per HTTP exchange and has no persistent bidirectional byte stream to multiplex onto. A Server **shall** omit the HTTPS TransportProfileUri from `SupportedTransportProfileUris`, and `OpenDataChannel` on an HTTPS endpoint **shall** return `Bad_DataChannelTransportUnsupported`. SOAP/HTTP (§7.3) is deprecated and out of scope.

## 7 OPC UA QUIC

### 7.1 Overview

QUIC provides, in the transport, exactly what clause 5 has to construct by hand: many independently ordered and independently flow-controlled streams over one connection, a datagram extension that really can lose a packet, congestion control, and an identity for the connection that survives the client's IP address changing.

This clause defines `opc.quic`, an OPC UA transport in which the UACP conversation runs on one QUIC stream and each data channel gets its own. Nothing above the transport changes: the same Services open a channel, the same AddressSpace describes it, the same frames flow, and a Client that has both endpoints available may choose either.

### 7.2 URL scheme, ALPN and discovery

| Item | Value |
|---|---|
| URL scheme | `opc.quic` |
| TransportProfileUri | `http://opcfoundation.org/UA-Profile/Transport/quic-uasc-uabinary` |
| ALPN protocol identifier (RFC 7301) | `opcua/1` — **provisional**, pending registration by the OPC Foundation |
| Default port | 4840 (UDP; it does not collide with TCP 4840) |
| Encoding | OPC UA Binary, as for `opc.tcp` |

A Server that offers both transports returns one `EndpointDescription` per transport from `GetEndpoints`, distinguished by `TransportProfileUri` and `EndpointUrl`. A Client **shall** perform ALPN negotiation and **shall** abandon the connection if the Server does not select the OPC UA identifier, so a QUIC endpoint serving another protocol on the same port is never mistaken for an OPC UA Server.

### 7.3 Connection establishment and the control stream

The first client-initiated bidirectional QUIC stream carries the UACP and Secure Conversation conversation — `HEL`, `ACK`, `ERR`, `OPN`, `MSG`, `CLO` — byte for byte as it appears over `opc.tcp`. The QUIC connection is the TransportConnection; the SecureChannel is established on it by `OpenSecureChannel` exactly as today.

`Hello` and `Acknowledge` are exchanged unchanged. Their `ReceiveBufferSize` and `SendBufferSize` continue to bound MessageChunks on the control stream. A data channel frame is bounded by the smaller of `RevisedMaxFrameSize` and the QUIC stream or datagram limit, not by these values.

Losing the control stream **shall** be treated as losing the SecureChannel: every data channel is aborted.

### 7.4 Stream mapping

Each data channel is bound at open to one QUIC stream, whose identifier is returned as `TransportChannelId`:

| Direction | QUIC stream |
|---|---|
| `SourceToSink` | A server-initiated unidirectional stream. |
| `SinkToSource` | A client-initiated unidirectional stream. |
| `Bidirectional` | A bidirectional stream, initiated by whichever end called `OpenDataChannel`. |

A QUIC stream carries a sequence of frames in **QUIC framing**: the Message header followed directly by the stream header, payload and nothing else. The symmetric security header, the sequence header and the message footer are omitted, because QUIC's TLS 1.3 record layer already authenticates and encrypts every byte and QUIC already orders and deduplicates each stream. The Message header is retained so that one decoder serves both transports and an intermediary can delimit frames without possessing keys. `MessageSize` remains the authoritative frame length, so a stream is self-delimiting.

Because QUIC applies its own per-stream and per-connection flow control, `CREDIT` frames **shall not** be sent over `opc.quic` and a receiver **shall** ignore one. Duplicating the window in two layers gains nothing and deadlocks when the two disagree.

Closing a data channel **shall** close its QUIC stream; `RESET` **shall** be realized as a QUIC `RESET_STREAM`, whose application error code carries the StatusCode.

### 7.5 Unreliable datagrams

When the negotiated delivery mode is `Unreliable`, or `PartiallyReliable` and both ends advertised the QUIC DATAGRAM extension in the transport parameters, `DATA` frames **shall** be sent as QUIC DATAGRAM frames (RFC 9221) rather than on the channel's stream. Control frames always use the stream, so a `RESET` or an `END` is never lost.

A datagram carries exactly one frame in QUIC framing, and the frame **shall** fit `max_datagram_frame_size`. Fragmenting a frame across datagrams is **not** permitted: one lost fragment would destroy a frame that the receiver could otherwise have used in part, which defeats the reason for choosing datagrams.

This is the only place in this specification where payload is genuinely lost in transit. `FrameSequenceNumber` is therefore the receiver's own loss detector, and a `GAP` frame is advisory because it too may be lost.

For `PartiallyReliable`, a sender **may** retransmit a datagram up to `MaxRetransmits` times or until its deadline passes, whichever comes first, and **shall** then abandon it and report the gap.

### 7.6 Security

QUIC mandates TLS 1.3 (RFC 9001), so `opc.quic` is a transport-secured protocol in the sense of OPC 10000-6 §7.4, like HTTPS. Two layers are therefore available, and this specification is explicit about which does what:

- **Control stream.** UA-SC message security applies unchanged. `OpenSecureChannel` runs, the security policy is negotiated, the application instance certificates authenticate the two applications, and SecurityMode is honoured. This is what preserves the OPC UA security model — application authentication and user authorization do not become TLS's job.
- **Data channel streams and datagrams.** Frames are protected by QUIC's TLS 1.3 record layer only. This is the `TransportSecured` data channel profile and it is **mandatory** over `opc.quic`; applying UA-SC message security a second time to bulk media would double the cryptographic cost of the hot path for no additional guarantee, since the same TLS connection already authenticates the same peer.

The following are normative consequences:

- A Server **shall** validate the Client's application instance certificate during `OpenSecureChannel` on the control stream, exactly as over `opc.tcp`. The TLS certificate authenticates the transport endpoint; it does **not** substitute for the OPC UA application certificate.
- A Client **shall not** open a data channel on a SecureChannel whose SecurityMode is `None` unless the Server explicitly permits it, because the audit trail then rests on TLS alone.
- **0-RTT data shall not be used to carry `OpenDataChannel`, `OpenSecureChannel` or any data channel frame.** 0-RTT is replayable, and a replayed channel open is a replayed authorization. 0-RTT **may** be used to resume the QUIC connection itself.
- QUIC key updates and OPC UA channel-token renewal are independent and neither triggers the other.

### 7.7 Connection migration

QUIC identifies a connection by its connection ID rather than by the four-tuple, so a client whose address changes — a vehicle moving between access points, a handheld leaving Wi-Fi for cellular — keeps the same QUIC connection, the same SecureChannel, the same Session and every open data channel. Over `opc.tcp` all of that is destroyed and must be rebuilt.

A Server **shall** accept migration under the RFC 9000 path-validation rules and **shall not** treat a validated path change as a security event, since the connection remains cryptographically bound to the same peer. A Server **may** re-evaluate a network-location-based authorization decision after migration; if it does and the decision is now negative, it **shall** abort the affected data channels with `Bad_UserAccessDenied` rather than silently continuing.

### 7.8 Congestion control

Congestion control is the transport's. Over `opc.quic` it is RFC 9002; over `opc.tcp` and `opc.wss` it is TCP's. This specification defines no congestion controller and no rate signalling, because a second controller layered on the first oscillates against it.

What this specification does provide is the information an application needs to adapt: `PING`/`PONG` round-trip measurement, the credit-stall counter, and the discarded-frame counter. An adaptive encoder lowers its bitrate when frames are being discarded and the round trip is climbing; that decision is the application's, and this layer's job is to make it visible.

### 7.9 Fallback and feature parity

A Client that cannot reach an `opc.quic` endpoint — no implementation, blocked UDP, a middlebox that drops QUIC — **shall** fall back to `opc.tcp` or `opc.wss` and use inline framing. The Services, the AddressSpace model, the frame layout above the Message header and the application contract are identical; only the four properties in the table of §4.2 differ.

A Server **shall not** require QUIC for any capability it also exposes over `opc.tcp`, and **shall** report through `SupportsUnreliableDatagrams` whether genuine loss is available, so a Client learns the difference by reading rather than by measuring.

## 8 Conformance units

| Conformance unit | Requires | Content |
|---|---|---|
| Data Channel Framing | — | Clause 5 in full: `STR` frames, stream header, all seven frame types, flags, the single-chunk rule, credit flow control, scheduling obligations, gap notification, reset, half-close, error handling. |
| Data Channel Inline Transport | Data Channel Framing | §6.1 and §6.2: framing over `opc.tcp` and `opc.wss` with no change to `Hello`/`Acknowledge`. |
| Data Channel Partial Reliability | Data Channel Framing | The `Droppable` flag, `Deadline`, sender-side expiry and `GAP` emission (§5.9, §5.10). |
| Data Channel QUIC Transport | Data Channel Framing | Clause 7 except §7.5: `opc.quic`, ALPN, control stream, per-channel QUIC streams, the `TransportSecured` profile, migration. |
| Data Channel Unreliable Datagram | Data Channel QUIC Transport, Data Channel Partial Reliability | §7.5: `DATA` over QUIC DATAGRAM with genuine in-flight loss. |

Data Channel Framing plus Data Channel Inline Transport is the minimum implementation. The Part 4 and Part 3 errata define the Service and Model conformance units that build on these.

## 9 Insertion into OPC 10000-6 v1.05.07

| Draft clause | Target clause in OPC 10000-6 | Notes |
|---|---|---|
| §5.1 `STR` MessageChunk | `6.7.2.2 Message Header` | Adds `STR` to the `MessageType` table and states the `IsFinal`, `SequenceNumber` and `RequestId` rules. No change to the header layout. |
| §5.1 reused headers | `6.7.2.3`, `6.7.2.4`, `6.7.2.5` | No change. A note that these clauses apply unchanged to `STR` is sufficient. |
| §5.2 to §5.6 framing | New `6.7.8 Data channel frames` | The stream header, frame types, flags and the single-chunk rule, as a new subclause of OPC UA Secure Conversation. |
| §5.7 scheduling | New `6.7.9 Data channel scheduling` | The two sender obligations. May instead be folded into `6.7.8` at the editor's discretion. |
| §5.8 to §5.11 | New `6.7.10 Data channel flow control and lifecycle` | Credit, delivery modes, gap notification, reset, half-close, round-trip measurement. |
| §5.12 error handling | `6.7.7 Verifying Message Security` | Extends the existing "close the channel on error" rule with the narrower per-channel `RESET` response, and states which faults take which path. |
| §6.1 | `7.2 OPC UA TCP` | No normative change; a note that `STR` chunks are carried like `MSG` chunks. |
| §6.2 | `7.5 WebSockets` | No normative change; a note that a `STR` frame is one binary WebSocket frame under `opcua+uacp`. No new sub-protocol. |
| §6.3 | `7.4 OPC UA HTTPS` | A statement that data channels are not available over this transport. |
| Clause 7 | New `7.7 OPC UA QUIC` | The complete new transport, parallel in structure to `7.2 OPC UA TCP` and `7.5 WebSockets`. It is appended after `7.6 Well known addresses`, which already occupies `7.6`; the editor may renumber. The QUIC well-known LDS address is added to Table 82 in `7.6`, and the TransportProfileUri is registered in OPC 10000-7. |
| §8 conformance units | OPC 10000-7 | New conformance units and the Profiles that group them. |

The `STR` MessageType, the ALPN identifier and the frame type and flag values are the items an editor must confirm are free before adoption; all are chosen from currently unassigned space. The clause number for the new transport is **not** free — `7.6` is `Well known addresses` in v1.05.07 — so the transport is proposed as `7.7` and the editor assigns the final number.

## Annex A — Rejected alternatives (informative)

**Extending `Hello`/`Acknowledge` with capability fields.** The natural place to negotiate a transport capability is the transport handshake, and it was the first design. It was rejected because `Hello` and `Acknowledge` have no extension point: new fields require a `ProtocolVersion` bump, and a version bump is visible to every existing implementation on the connection, including those that will never open a data channel. Negotiating at the Service level instead costs one round trip that the client was making anyway and leaves the handshake byte-identical, so a data-channel-capable Client and a legacy Server interoperate with no special case on either side.

**Carrying the ChannelId in `RequestId`.** Reusing `RequestId` would let an existing stack demultiplex frames with no new field, and it was attractive for exactly that reason. It was rejected because the Client allocates RequestIds and the Server allocates ChannelIds, so the two spaces cannot be kept disjoint by any rule that does not amount to a negotiation. A collision would deliver a data channel frame to a pending Service call.

**Multi-chunk frames.** Allowing a frame to be chunked would remove the frame size ceiling and let an application send an arbitrarily large unit in one operation. It was rejected because chunk reassembly is per SecureChannel: a large frame in flight blocks every other Message, including the `Publish` response, until it completes. Segmenting at the data channel layer with `MessageStart` and `MessageEnd` gives the application the same unbounded unit with none of the blocking.

**A separate `SequenceNumber` space per data channel.** Per-channel sequence numbers would be a natural fit for per-channel ordering. They were rejected for inline framing because the Secure Conversation sequence number is a security mechanism, not an ordering mechanism: splitting it into independent spaces would weaken replay and injection detection on the SecureChannel. `FrameSequenceNumber` provides per-channel ordering separately, inside the secured body, where it cannot affect the security property.

**A second TCP connection per stream.** Opening a socket per stream is what today's workarounds do. It was rejected because it reintroduces everything data channels exist to avoid: another port to open, another handshake to authenticate, another certificate validation, and no relationship to the Session that authorized the data.

<a id="annex-b"></a>

## Annex B — Annotated byte layouts

<!-- BEGIN GENERATED: wire-layouts -->

This annex is generated by `../extras/data-channels/tools/gen_wire_annex.py` from the reference codec in `../extras/data-channels/tools/frame_codec.py`, and the byte sequences shown are byte-for-byte the vectors published under `../extras/data-channels/examples/`. Do not edit between the markers.

Every span below is verified to be contiguous and non-overlapping, and every vector is verified to decode back to the frame it was encoded from, so a table that disagrees with the bytes cannot be committed.

All integers are little-endian, matching the OPC UA Binary DataEncoding.

### inline_data_first

**Framing** inline (opc.tcp, opc.wss) · **Frame type** `DATA` · **ChannelId** 1 · **Total** 52 bytes

The first frame of a logical application message on channel 1, marked as a synchronization point. This is the layout an implementer needs to get right; every other inline frame is this one with different stream header contents.

| Offset | Length | Section | Field | Value | Bytes |
|---|---|---|---|---|---|
| 0 | 3 | Message header | `MessageType` | 'STR' | `53 54 52` |
| 3 | 1 | Message header | `IsFinal` | 'F' | `46` |
| 4 | 4 | Message header | `MessageSize` | 52 | `34 00 00 00` |
| 8 | 4 | Message header | `SecureChannelId` | 41340 | `7C A1 00 00` |
| 12 | 4 | Symmetric security header | `TokenId` | 7 | `07 00 00 00` |
| 16 | 4 | Sequence header | `SequenceNumber` | 51 | `33 00 00 00` |
| 20 | 4 | Sequence header | `RequestId` | 0 | `00 00 00 00` |
| 24 | 4 | Stream header | `ChannelId` | 1 | `01 00 00 00` |
| 28 | 1 | Stream header | `FrameType` | 0 (DATA) | `00` |
| 29 | 1 | Stream header | `Flags` | 0x11 (MessageStart, Marker) | `11` |
| 30 | 2 | Stream header | `Reserved` | 0 | `00 00` |
| 32 | 4 | Stream header | `FrameSequenceNumber` | 1 | `01 00 00 00` |
| 36 | 16 | Payload | `Payload` | 16 bytes | `00 01 02 03 04 05 06 07 08 09 0A 0B …` |

```text
0000  53 54 52 46 34 00 00 00 7C A1 00 00 07 00 00 00  STRF4...|.......
0010  33 00 00 00 00 00 00 00 01 00 00 00 00 11 00 00  3...............
0020  01 00 00 00 00 01 02 03 04 05 06 07 08 09 0A 0B  ................
0030  0C 0D 0E 0F                                      ....
```

### inline_data_final

**Framing** inline (opc.tcp, opc.wss) · **Frame type** `DATA` · **ChannelId** 1 · **Total** 40 bytes

The closing frame of the same logical message. MessageEnd is what delimits an application message; the frame itself is still a single MessageChunk.

| Offset | Length | Section | Field | Value | Bytes |
|---|---|---|---|---|---|
| 0 | 3 | Message header | `MessageType` | 'STR' | `53 54 52` |
| 3 | 1 | Message header | `IsFinal` | 'F' | `46` |
| 4 | 4 | Message header | `MessageSize` | 40 | `28 00 00 00` |
| 8 | 4 | Message header | `SecureChannelId` | 41340 | `7C A1 00 00` |
| 12 | 4 | Symmetric security header | `TokenId` | 7 | `07 00 00 00` |
| 16 | 4 | Sequence header | `SequenceNumber` | 52 | `34 00 00 00` |
| 20 | 4 | Sequence header | `RequestId` | 0 | `00 00 00 00` |
| 24 | 4 | Stream header | `ChannelId` | 1 | `01 00 00 00` |
| 28 | 1 | Stream header | `FrameType` | 0 (DATA) | `00` |
| 29 | 1 | Stream header | `Flags` | 0x02 (MessageEnd) | `02` |
| 30 | 2 | Stream header | `Reserved` | 0 | `00 00` |
| 32 | 4 | Stream header | `FrameSequenceNumber` | 2 | `02 00 00 00` |
| 36 | 4 | Payload | `Payload` | 4 bytes | `AA BB CC DD` |

```text
0000  53 54 52 46 28 00 00 00 7C A1 00 00 07 00 00 00  STRF(...|.......
0010  34 00 00 00 00 00 00 00 01 00 00 00 00 02 00 00  4...............
0020  02 00 00 00 AA BB CC DD                          ........
```

### inline_data_droppable

**Framing** inline (opc.tcp, opc.wss) · **Frame type** `DATA` · **ChannelId** 2 · **Total** 52 bytes

A self-contained media frame that the sender may discard if it is still queued at the deadline. The Deadline field is present only because the DeadlinePresent flag is set, so a reliable channel never pays its eight bytes.

| Offset | Length | Section | Field | Value | Bytes |
|---|---|---|---|---|---|
| 0 | 3 | Message header | `MessageType` | 'STR' | `53 54 52` |
| 3 | 1 | Message header | `IsFinal` | 'F' | `46` |
| 4 | 4 | Message header | `MessageSize` | 52 | `34 00 00 00` |
| 8 | 4 | Message header | `SecureChannelId` | 41340 | `7C A1 00 00` |
| 12 | 4 | Symmetric security header | `TokenId` | 7 | `07 00 00 00` |
| 16 | 4 | Sequence header | `SequenceNumber` | 53 | `35 00 00 00` |
| 20 | 4 | Sequence header | `RequestId` | 0 | `00 00 00 00` |
| 24 | 4 | Stream header | `ChannelId` | 2 | `02 00 00 00` |
| 28 | 1 | Stream header | `FrameType` | 0 (DATA) | `00` |
| 29 | 1 | Stream header | `Flags` | 0x0F (MessageStart, MessageEnd, Droppable, DeadlinePresent) | `0F` |
| 30 | 2 | Stream header | `Reserved` | 0 | `00 00` |
| 32 | 4 | Stream header | `FrameSequenceNumber` | 97 | `61 00 00 00` |
| 36 | 8 | Stream header | `Deadline` | 133000000000000000 | `00 80 20 9B CB 82 D8 01` |
| 44 | 8 | Payload | `Payload` | 8 bytes | `01 02 03 04 05 06 07 08` |

```text
0000  53 54 52 46 34 00 00 00 7C A1 00 00 07 00 00 00  STRF4...|.......
0010  35 00 00 00 00 00 00 00 02 00 00 00 00 0F 00 00  5...............
0020  61 00 00 00 00 80 20 9B CB 82 D8 01 01 02 03 04  a..... .........
0030  05 06 07 08                                      ....
```

### inline_credit_channel

**Framing** inline (opc.tcp, opc.wss) · **Frame type** `CREDIT` · **ChannelId** 2 · **Total** 44 bytes

A window update for channel 2 alone. CREDIT frames are exempt from flow control; a creditable CREDIT frame would deadlock a stalled channel.

| Offset | Length | Section | Field | Value | Bytes |
|---|---|---|---|---|---|
| 0 | 3 | Message header | `MessageType` | 'STR' | `53 54 52` |
| 3 | 1 | Message header | `IsFinal` | 'F' | `46` |
| 4 | 4 | Message header | `MessageSize` | 44 | `2C 00 00 00` |
| 8 | 4 | Message header | `SecureChannelId` | 41340 | `7C A1 00 00` |
| 12 | 4 | Symmetric security header | `TokenId` | 7 | `07 00 00 00` |
| 16 | 4 | Sequence header | `SequenceNumber` | 54 | `36 00 00 00` |
| 20 | 4 | Sequence header | `RequestId` | 0 | `00 00 00 00` |
| 24 | 4 | Stream header | `ChannelId` | 2 | `02 00 00 00` |
| 28 | 1 | Stream header | `FrameType` | 1 (CREDIT) | `01` |
| 29 | 1 | Stream header | `Flags` | 0x00 (none) | `00` |
| 30 | 2 | Stream header | `Reserved` | 0 | `00 00` |
| 32 | 4 | Stream header | `FrameSequenceNumber` | 98 | `62 00 00 00` |
| 36 | 4 | CREDIT fields | `ChannelCredit` | 65536 | `00 00 01 00` |
| 40 | 4 | CREDIT fields | `ConnectionCredit` | 0 | `00 00 00 00` |

```text
0000  53 54 52 46 2C 00 00 00 7C A1 00 00 07 00 00 00  STRF,...|.......
0010  36 00 00 00 00 00 00 00 02 00 00 00 01 00 00 00  6...............
0020  62 00 00 00 00 00 01 00 00 00 00 00              b...........
```

### inline_credit_connection

**Framing** inline (opc.tcp, opc.wss) · **Frame type** `CREDIT` · **ChannelId** 0 · **Total** 44 bytes

A connection-level window update on the reserved control channel 0, which governs the total across every data channel of the SecureChannel. Channel 0 counts its own FrameSequenceNumber sequence like any other channel.

| Offset | Length | Section | Field | Value | Bytes |
|---|---|---|---|---|---|
| 0 | 3 | Message header | `MessageType` | 'STR' | `53 54 52` |
| 3 | 1 | Message header | `IsFinal` | 'F' | `46` |
| 4 | 4 | Message header | `MessageSize` | 44 | `2C 00 00 00` |
| 8 | 4 | Message header | `SecureChannelId` | 41340 | `7C A1 00 00` |
| 12 | 4 | Symmetric security header | `TokenId` | 7 | `07 00 00 00` |
| 16 | 4 | Sequence header | `SequenceNumber` | 55 | `37 00 00 00` |
| 20 | 4 | Sequence header | `RequestId` | 0 | `00 00 00 00` |
| 24 | 4 | Stream header | `ChannelId` | 0 | `00 00 00 00` |
| 28 | 1 | Stream header | `FrameType` | 1 (CREDIT) | `01` |
| 29 | 1 | Stream header | `Flags` | 0x00 (none) | `00` |
| 30 | 2 | Stream header | `Reserved` | 0 | `00 00` |
| 32 | 4 | Stream header | `FrameSequenceNumber` | 11 | `0B 00 00 00` |
| 36 | 4 | CREDIT fields | `ChannelCredit` | 0 | `00 00 00 00` |
| 40 | 4 | CREDIT fields | `ConnectionCredit` | 262144 | `00 00 04 00` |

```text
0000  53 54 52 46 2C 00 00 00 7C A1 00 00 07 00 00 00  STRF,...|.......
0010  37 00 00 00 00 00 00 00 00 00 00 00 01 00 00 00  7...............
0020  0B 00 00 00 00 00 00 00 00 00 04 00              ............
```

### inline_gap

**Framing** inline (opc.tcp, opc.wss) · **Frame type** `GAP` · **ChannelId** 2 · **Total** 44 bytes

The sender discarded frames 99 through 102 because their deadlines passed. Without this notification the receiver could not tell loss from a stall, and a media decoder could not decide to conceal.

| Offset | Length | Section | Field | Value | Bytes |
|---|---|---|---|---|---|
| 0 | 3 | Message header | `MessageType` | 'STR' | `53 54 52` |
| 3 | 1 | Message header | `IsFinal` | 'F' | `46` |
| 4 | 4 | Message header | `MessageSize` | 44 | `2C 00 00 00` |
| 8 | 4 | Message header | `SecureChannelId` | 41340 | `7C A1 00 00` |
| 12 | 4 | Symmetric security header | `TokenId` | 7 | `07 00 00 00` |
| 16 | 4 | Sequence header | `SequenceNumber` | 56 | `38 00 00 00` |
| 20 | 4 | Sequence header | `RequestId` | 0 | `00 00 00 00` |
| 24 | 4 | Stream header | `ChannelId` | 2 | `02 00 00 00` |
| 28 | 1 | Stream header | `FrameType` | 2 (GAP) | `02` |
| 29 | 1 | Stream header | `Flags` | 0x00 (none) | `00` |
| 30 | 2 | Stream header | `Reserved` | 0 | `00 00` |
| 32 | 4 | Stream header | `FrameSequenceNumber` | 103 | `67 00 00 00` |
| 36 | 4 | GAP fields | `FirstDiscarded` | 99 | `63 00 00 00` |
| 40 | 4 | GAP fields | `LastDiscarded` | 102 | `66 00 00 00` |

```text
0000  53 54 52 46 2C 00 00 00 7C A1 00 00 07 00 00 00  STRF,...|.......
0010  38 00 00 00 00 00 00 00 02 00 00 00 02 00 00 00  8...............
0020  67 00 00 00 63 00 00 00 66 00 00 00              g...c...f...
```

### inline_reset

**Framing** inline (opc.tcp, opc.wss) · **Frame type** `RESET` · **ChannelId** 2 · **Total** 40 bytes

Abort one data channel and leave every other channel and the SecureChannel itself running. This is the difference between a data channel failing and a connection failing.

| Offset | Length | Section | Field | Value | Bytes |
|---|---|---|---|---|---|
| 0 | 3 | Message header | `MessageType` | 'STR' | `53 54 52` |
| 3 | 1 | Message header | `IsFinal` | 'F' | `46` |
| 4 | 4 | Message header | `MessageSize` | 40 | `28 00 00 00` |
| 8 | 4 | Message header | `SecureChannelId` | 41340 | `7C A1 00 00` |
| 12 | 4 | Symmetric security header | `TokenId` | 7 | `07 00 00 00` |
| 16 | 4 | Sequence header | `SequenceNumber` | 57 | `39 00 00 00` |
| 20 | 4 | Sequence header | `RequestId` | 0 | `00 00 00 00` |
| 24 | 4 | Stream header | `ChannelId` | 2 | `02 00 00 00` |
| 28 | 1 | Stream header | `FrameType` | 3 (RESET) | `03` |
| 29 | 1 | Stream header | `Flags` | 0x00 (none) | `00` |
| 30 | 2 | Stream header | `Reserved` | 0 | `00 00` |
| 32 | 4 | Stream header | `FrameSequenceNumber` | 104 | `68 00 00 00` |
| 36 | 4 | RESET fields | `StatusCode` | 2175860736 | `00 00 B1 81` |

```text
0000  53 54 52 46 28 00 00 00 7C A1 00 00 07 00 00 00  STRF(...|.......
0010  39 00 00 00 00 00 00 00 02 00 00 00 03 00 00 00  9...............
0020  68 00 00 00 00 00 B1 81                          h.......
```

### inline_end

**Framing** inline (opc.tcp, opc.wss) · **Frame type** `END` · **ChannelId** 1 · **Total** 36 bytes

Orderly half-close: this direction of channel 1 will send nothing further, while the opposite direction of a Bidirectional channel keeps flowing.

| Offset | Length | Section | Field | Value | Bytes |
|---|---|---|---|---|---|
| 0 | 3 | Message header | `MessageType` | 'STR' | `53 54 52` |
| 3 | 1 | Message header | `IsFinal` | 'F' | `46` |
| 4 | 4 | Message header | `MessageSize` | 36 | `24 00 00 00` |
| 8 | 4 | Message header | `SecureChannelId` | 41340 | `7C A1 00 00` |
| 12 | 4 | Symmetric security header | `TokenId` | 7 | `07 00 00 00` |
| 16 | 4 | Sequence header | `SequenceNumber` | 58 | `3A 00 00 00` |
| 20 | 4 | Sequence header | `RequestId` | 0 | `00 00 00 00` |
| 24 | 4 | Stream header | `ChannelId` | 1 | `01 00 00 00` |
| 28 | 1 | Stream header | `FrameType` | 4 (END) | `04` |
| 29 | 1 | Stream header | `Flags` | 0x00 (none) | `00` |
| 30 | 2 | Stream header | `Reserved` | 0 | `00 00` |
| 32 | 4 | Stream header | `FrameSequenceNumber` | 3 | `03 00 00 00` |

```text
0000  53 54 52 46 24 00 00 00 7C A1 00 00 07 00 00 00  STRF$...|.......
0010  3A 00 00 00 00 00 00 00 01 00 00 00 04 00 00 00  :...............
0020  03 00 00 00                                      ....
```

### inline_ping

**Framing** inline (opc.tcp, opc.wss) · **Frame type** `PING` · **ChannelId** 0 · **Total** 44 bytes

A round trip probe on the control channel. The measured round trip time is what a sender paces against and what a receiver sizes its jitter buffer from.

| Offset | Length | Section | Field | Value | Bytes |
|---|---|---|---|---|---|
| 0 | 3 | Message header | `MessageType` | 'STR' | `53 54 52` |
| 3 | 1 | Message header | `IsFinal` | 'F' | `46` |
| 4 | 4 | Message header | `MessageSize` | 44 | `2C 00 00 00` |
| 8 | 4 | Message header | `SecureChannelId` | 41340 | `7C A1 00 00` |
| 12 | 4 | Symmetric security header | `TokenId` | 7 | `07 00 00 00` |
| 16 | 4 | Sequence header | `SequenceNumber` | 59 | `3B 00 00 00` |
| 20 | 4 | Sequence header | `RequestId` | 0 | `00 00 00 00` |
| 24 | 4 | Stream header | `ChannelId` | 0 | `00 00 00 00` |
| 28 | 1 | Stream header | `FrameType` | 5 (PING) | `05` |
| 29 | 1 | Stream header | `Flags` | 0x00 (none) | `00` |
| 30 | 2 | Stream header | `Reserved` | 0 | `00 00` |
| 32 | 4 | Stream header | `FrameSequenceNumber` | 12 | `0C 00 00 00` |
| 36 | 8 | PING fields | `Timestamp` | 133000000000000000 | `00 80 20 9B CB 82 D8 01` |

```text
0000  53 54 52 46 2C 00 00 00 7C A1 00 00 07 00 00 00  STRF,...|.......
0010  3B 00 00 00 00 00 00 00 00 00 00 00 05 00 00 00  ;...............
0020  0C 00 00 00 00 80 20 9B CB 82 D8 01              ...... .....
```

### inline_pong

**Framing** inline (opc.tcp, opc.wss) · **Frame type** `PONG` · **ChannelId** 0 · **Total** 44 bytes

The echo. The Timestamp is copied verbatim from the PING, so the sender needs to keep no state to compute the round trip.

| Offset | Length | Section | Field | Value | Bytes |
|---|---|---|---|---|---|
| 0 | 3 | Message header | `MessageType` | 'STR' | `53 54 52` |
| 3 | 1 | Message header | `IsFinal` | 'F' | `46` |
| 4 | 4 | Message header | `MessageSize` | 44 | `2C 00 00 00` |
| 8 | 4 | Message header | `SecureChannelId` | 41340 | `7C A1 00 00` |
| 12 | 4 | Symmetric security header | `TokenId` | 7 | `07 00 00 00` |
| 16 | 4 | Sequence header | `SequenceNumber` | 60 | `3C 00 00 00` |
| 20 | 4 | Sequence header | `RequestId` | 0 | `00 00 00 00` |
| 24 | 4 | Stream header | `ChannelId` | 0 | `00 00 00 00` |
| 28 | 1 | Stream header | `FrameType` | 6 (PONG) | `06` |
| 29 | 1 | Stream header | `Flags` | 0x00 (none) | `00` |
| 30 | 2 | Stream header | `Reserved` | 0 | `00 00` |
| 32 | 4 | Stream header | `FrameSequenceNumber` | 13 | `0D 00 00 00` |
| 36 | 8 | PONG fields | `Timestamp` | 133000000000000000 | `00 80 20 9B CB 82 D8 01` |

```text
0000  53 54 52 46 2C 00 00 00 7C A1 00 00 07 00 00 00  STRF,...|.......
0010  3C 00 00 00 00 00 00 00 00 00 00 00 06 00 00 00  <...............
0020  0D 00 00 00 00 80 20 9B CB 82 D8 01              ...... .....
```

### inline_data_signed

**Framing** inline (opc.tcp, opc.wss) · **Frame type** `DATA` · **ChannelId** 1 · **Total** 73 bytes

The same inline frame under a signing security policy, showing where the Part 6 message footer lands. The footer bytes here are placeholder filler: they are produced by the security policy, not by this specification.

| Offset | Length | Section | Field | Value | Bytes |
|---|---|---|---|---|---|
| 0 | 3 | Message header | `MessageType` | 'STR' | `53 54 52` |
| 3 | 1 | Message header | `IsFinal` | 'F' | `46` |
| 4 | 4 | Message header | `MessageSize` | 73 | `49 00 00 00` |
| 8 | 4 | Message header | `SecureChannelId` | 41340 | `7C A1 00 00` |
| 12 | 4 | Symmetric security header | `TokenId` | 7 | `07 00 00 00` |
| 16 | 4 | Sequence header | `SequenceNumber` | 61 | `3D 00 00 00` |
| 20 | 4 | Sequence header | `RequestId` | 0 | `00 00 00 00` |
| 24 | 4 | Stream header | `ChannelId` | 1 | `01 00 00 00` |
| 28 | 1 | Stream header | `FrameType` | 0 (DATA) | `00` |
| 29 | 1 | Stream header | `Flags` | 0x03 (MessageStart, MessageEnd) | `03` |
| 30 | 2 | Stream header | `Reserved` | 0 | `00 00` |
| 32 | 4 | Stream header | `FrameSequenceNumber` | 4 | `04 00 00 00` |
| 36 | 4 | Payload | `Payload` | 4 bytes | `10 11 12 13` |
| 40 | 33 | Message footer | `PaddingSize / Padding / Signature` | 33 bytes | `00 5A 5A 5A 5A 5A 5A 5A 5A 5A 5A 5A …` |

```text
0000  53 54 52 46 49 00 00 00 7C A1 00 00 07 00 00 00  STRFI...|.......
0010  3D 00 00 00 00 00 00 00 01 00 00 00 00 03 00 00  =...............
0020  04 00 00 00 10 11 12 13 00 5A 5A 5A 5A 5A 5A 5A  .........ZZZZZZZ
0030  5A 5A 5A 5A 5A 5A 5A 5A 5A 5A 5A 5A 5A 5A 5A 5A  ZZZZZZZZZZZZZZZZ
0040  5A 5A 5A 5A 5A 5A 5A 5A 5A                       ZZZZZZZZZ
```

### quic_data_stream

**Framing** QUIC (opc.quic) · **Frame type** `DATA` · **ChannelId** 1 · **Total** 40 bytes

The same DATA frame carried on a QUIC stream. TLS 1.3 already authenticates and encrypts it and QUIC already orders it, so the security header, the sequence header and the footer are gone and the frame is twelve bytes shorter.

| Offset | Length | Section | Field | Value | Bytes |
|---|---|---|---|---|---|
| 0 | 3 | Message header | `MessageType` | 'STR' | `53 54 52` |
| 3 | 1 | Message header | `IsFinal` | 'F' | `46` |
| 4 | 4 | Message header | `MessageSize` | 40 | `28 00 00 00` |
| 8 | 4 | Message header | `SecureChannelId` | 41340 | `7C A1 00 00` |
| 12 | 4 | Stream header | `ChannelId` | 1 | `01 00 00 00` |
| 16 | 1 | Stream header | `FrameType` | 0 (DATA) | `00` |
| 17 | 1 | Stream header | `Flags` | 0x13 (MessageStart, MessageEnd, Marker) | `13` |
| 18 | 2 | Stream header | `Reserved` | 0 | `00 00` |
| 20 | 4 | Stream header | `FrameSequenceNumber` | 1 | `01 00 00 00` |
| 24 | 16 | Payload | `Payload` | 16 bytes | `00 01 02 03 04 05 06 07 08 09 0A 0B …` |

```text
0000  53 54 52 46 28 00 00 00 7C A1 00 00 01 00 00 00  STRF(...|.......
0010  00 13 00 00 01 00 00 00 00 01 02 03 04 05 06 07  ................
0020  08 09 0A 0B 0C 0D 0E 0F                          ........
```

### quic_datagram_unreliable

**Framing** QUIC (opc.quic) · **Frame type** `DATA` · **ChannelId** 3 · **Total** 30 bytes

An Unreliable frame in a QUIC DATAGRAM. This is the only place in the specification where data is genuinely lost in flight rather than discarded at the sender, which is why FrameSequenceNumber is the receiver's own gap detector.

| Offset | Length | Section | Field | Value | Bytes |
|---|---|---|---|---|---|
| 0 | 3 | Message header | `MessageType` | 'STR' | `53 54 52` |
| 3 | 1 | Message header | `IsFinal` | 'F' | `46` |
| 4 | 4 | Message header | `MessageSize` | 30 | `1E 00 00 00` |
| 8 | 4 | Message header | `SecureChannelId` | 41340 | `7C A1 00 00` |
| 12 | 4 | Stream header | `ChannelId` | 3 | `03 00 00 00` |
| 16 | 1 | Stream header | `FrameType` | 0 (DATA) | `00` |
| 17 | 1 | Stream header | `Flags` | 0x07 (MessageStart, MessageEnd, Droppable) | `07` |
| 18 | 2 | Stream header | `Reserved` | 0 | `00 00` |
| 20 | 4 | Stream header | `FrameSequenceNumber` | 4096 | `00 10 00 00` |
| 24 | 6 | Payload | `Payload` | 6 bytes | `F0 F1 F2 F3 F4 F5` |

```text
0000  53 54 52 46 1E 00 00 00 7C A1 00 00 03 00 00 00  STRF....|.......
0010  00 07 00 00 00 10 00 00 F0 F1 F2 F3 F4 F5        ..............
```

<!-- END GENERATED: wire-layouts -->
