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

A sender **shall** assign a `DATA` frame its `FrameSequenceNumber` when the frame is **enqueued**, and **shall** transmit the `DATA` frames of a channel in ascending `FrameSequenceNumber` order. Assignment at enqueue is what allows a `GAP` frame to name a frame that was never transmitted; ascending transmission is what keeps the receiver's arithmetic in §5.2.1 monotonic despite the holes that expiry leaves behind.

#### 5.2.1 Sequence number comparison and gap detection

`FrameSequenceNumber` is what makes loss visible, so the comparison must be an algorithm rather than an intuition: a bare "is it bigger" test cannot distinguish the wrap from a four-billion gap, and cannot recognize a datagram retransmission at all.

Comparison is performed in serial-number arithmetic over the `2^32 - 1` values `1 .. 4294967295`. For two values `a` and `b`, `a` is **after** `b` when `(a - b) mod (2^32 - 1)` lies in the range `1 .. 2^31 - 1`, and the **distance** from `b` to `a` is that value. The modulus is `2^32 - 1` rather than `2^32` because `0` is excluded from the value space, so the wrap from `4294967295` to `1` is a distance of `1` and is in sequence with no special case required.

A receiver **shall** apply this clause to `DATA` frames only. `CREDIT`, `GAP`, `RESET`, `END`, `PING` and `PONG` frames carry a `FrameSequenceNumber` for audit and duplicate detection but **shall not** advance `HighestReceived` and **shall not** cause a gap to be reported. Were control frames to advance it, a `GAP` announcing an expiry would push `HighestReceived` past a lower-numbered frame that survived and is still to be transmitted, and the receiver would then discard as a duplicate precisely the frame the per-run rule of §5.10 exists to protect.

A receiver **shall** maintain, per channel and per direction, a `HighestReceived` value initialized to the first `DATA` `FrameSequenceNumber` it accepts, and a **replay window** of at least the last 64 sequence numbers at or below `HighestReceived`. It **shall** retain a run named by a `GAP` until `HighestReceived` has advanced past that run's `LastDiscarded` by more than the size of the replay window, and **shall** then discard the run. Bounding the retained runs matters for the same reason bounding the replay window does: an unbounded set grows without limit on a lossy media channel, and after the sequence wraps a legitimate frame whose number was named four billion frames earlier would be silently discarded. Because `DATA` is transmitted in ascending order (§5.2), no frame within a run can legitimately arrive after that point.

For each accepted `DATA` frame a receiver **shall** apply exactly these rules, in order:

| Condition | Receiver action |
|---|---|
| The number falls inside a run already named by a `GAP` on this channel | **Shall** be discarded without delivery (§5.10). |
| Distance from `HighestReceived` is `1` | In sequence. Deliver, and advance `HighestReceived`. |
| Frame is after `HighestReceived` by more than `1` | The intervening range is lost. Report the gap to the application, deliver this frame, and advance `HighestReceived`. |
| Frame is not after `HighestReceived`, and lies within the replay window | A duplicate or a datagram retransmission (§7.5). **Shall** be discarded silently and **shall not** be reported as a gap. |
| Frame is not after `HighestReceived`, and lies outside the replay window | Protocol error. **Shall** `RESET` the channel with `Bad_DataChannelClosed`. |

A receiver reports a gap on its own from a discontinuity, without waiting for and without depending on a `GAP` frame — which matters over QUIC DATAGRAM, where the notification may itself be lost.

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

**Direction enforcement.** A peer **shall not** transmit a `DATA` frame in a direction the channel's negotiated `Direction` does not permit: on a `SourceToSink` channel only the source sends `DATA`, on a `SinkToSource` channel only the sink does, and on a `Bidirectional` channel both may. A receiver **shall** treat a `DATA` frame arriving in a direction the channel does not permit as a protocol error and **shall** `RESET` the channel with `Bad_DataChannelDirectionUnsupported`.

`CREDIT`, `GAP`, `RESET`, `END`, `PING` and `PONG` **may** be sent in either direction on any channel regardless of `Direction`. This is not an exception but a requirement: on a `SourceToSink` channel the sink is the only party that can grant credit, so a rule confining every frame to the payload direction would make flow control impossible.

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

A sender that has negotiated a non-zero `FrameDeadline` **shall**, on each frame it marks `Droppable`, set `DeadlinePresent` and set `Deadline` to the sender's clock at the moment the frame was enqueued plus `FrameDeadline` × 10 000, expressed in 100 ns intervals since 1601-01-01 UTC. The factor 10 000 is the conversion from the `Duration` millisecond unit of `FrameDeadline` to the 100 ns unit of `Deadline`.

A sender **shall not** set `Droppable` on a channel whose negotiated `DeliveryMode` is `ReliableOrdered` or `ReliableUnordered`, and a receiver **shall** treat such a frame as a protocol error and `RESET` the channel with `Bad_DeliveryModeUnsupported`. Without this rule a sender could expire a frame on a reliable channel, which §5.10 would then require it to announce with a `GAP` frame that the same clause forbids on a reliable channel.

`MessageStart` and `MessageEnd` are how an application delimits a unit larger than one frame without reintroducing chunking into the security layer. On a `ReliableOrdered` channel a receiver **shall** deliver payload to the application in ascending `FrameSequenceNumber` order; on a `ReliableUnordered`, `PartiallyReliable` or `Unreliable` channel a receiver **may** deliver each frame as it arrives. Whether a receiver withholds delivery until `MessageEnd` is in every mode an application decision.

### 5.5 Frame size and the single-chunk rule

A data channel frame **shall** be exactly one MessageChunk. This is the single most important constraint in this specification: a multi-chunk frame would sit in the existing chunk assembler and block every other Message on the connection until it completed, which is the precise failure a streaming layer exists to avoid.

The total encoded size of a frame **shall not** exceed the `ReceiveBufferSize` the peer declared in its `Hello` or `Acknowledge`. The usable payload is that limit less the fixed overhead:

| Framing | Fixed overhead | Optional |
|---|---|---|
| Inline | 12 (message header) + 4 (security header) + 8 (sequence header) + 12 (stream header) = **36 bytes** | + 8 (`Deadline`) + frame type fields + the security policy's footer |
| QUIC | 12 (message header) + 12 (stream header) = **24 bytes** | + 8 (`Deadline`) + frame type fields |

A Server computes the resulting bound and returns it as `revisedParameters.MaxFrameSize` in the `OpenDataChannel` response, so an application never has to derive it. An application unit larger than one frame is segmented across frames using `MessageStart` and `MessageEnd`.

### 5.6 The connection control channel

ChannelId `0` is reserved and is never assigned by `OpenDataChannel`. It carries only `CREDIT` frames that grant the connection-level window, and `PING` and `PONG`. A receiver **shall** reject any other frame type on ChannelId `0`, and **shall** reject payload on it.

Separating connection-level control from any particular channel is what lets the connection window be replenished while every individual channel is stalled, and lets the round trip be probed on a connection that currently has no data channel open at all.

### 5.7 Interleaving and scheduling

A sender **may** interleave `STR` frames with `MSG`, `OPN` and `CLO` chunks and with `STR` frames of other ChannelIds, in any order. Because a frame is never chunked, a receiver needs no reassembly state and no interleaving rule beyond the existing one.

Two scheduling obligations are normative:

1. **Service traffic has precedence.** A sender **shall not** delay a `MSG`, `OPN` or `CLO` chunk that is ready to send by more than the transmission of one maximum-size data channel frame. Without this, a saturated video channel starves the `Publish` response path and the Session dies of a keepalive timeout while the connection is busy.
2. **No channel starves.** Among data channels that have payload ready and credit available, a sender **shall** serve every such channel at least once before it serves any channel a second time beyond its priority weighting. Priority (0 lowest to 7 highest, negotiated per channel) determines *share*, never *exclusivity*.

A sender **should** realize both obligations as a **deficit round robin** in which each scheduling round adds a quantum of (`Priority` + 1) × `MaxFrameSize` bytes to each ready channel's deficit counter, serves head-of-queue frames while the deficit covers them, resets a channel's deficit to zero when its queue empties, and drains one pending Service chunk after each data channel frame. The quantum is stated here because "priority weighting" is otherwise undefined: two implementations that read only obligation 2 would produce different bandwidth shares for the same `Priority` values, which is exactly the interoperability difference a specification exists to remove. A sender **may** use any other algorithm that satisfies both obligations and produces the same long-run share.

`core-specs/extras/data-channels/tools/scheduler_demo.py` is an **informative** executable realization of this algorithm. It is not normative; where it and this clause differ, this clause governs.

### 5.8 Flow control

Every data channel has a **channel credit** and the connection has a **connection credit**, both counted in `DATA` payload bytes and both maintained by the sender as the peer's remaining willingness to receive.

**Credit is per-direction.** Channel credit and connection credit are maintained independently for each direction of transfer. On a `Bidirectional` channel there are therefore two channel windows and two connection windows, and each peer maintains the window describing what *it* may send. `InitialCredit` seeds the window in **both** directions of a `Bidirectional` channel.

**Subclauses 5.8.1 and 5.8.2 apply to the inline framing of clause 6 only.** Over `opc.quic` both are replaced in their entirety by QUIC's own connection- and stream-level flow control (§7.4): no `CREDIT` frame is sent or expected, no peer withholds `DATA` pending one, and `Paused` is entered on QUIC stream or connection blocking instead. Scoping this at the head of the clause matters, because the "no `DATA` before a connection-level `CREDIT`" gate of §5.8.1 would otherwise block every QUIC channel forever against a frame §7.4 forbids anyone to send.

#### 5.8.1 Bootstrap

Before either peer transmits its first `DATA` frame on a SecureChannel, that peer's connection credit is **zero**. Channel credit is seeded by the Service; connection credit is not, because the Service response is per channel and the connection window is not.

- Initial channel credit, in each permitted direction, is `revisedParameters.InitialCredit` from the `OpenDataChannel` response.
- A Server **shall** send a connection-level `CREDIT` frame on ChannelId `0`, granting the Client's send direction, within one round trip of accepting the first `OpenDataChannel` on a SecureChannel, and **shall not** wait for the Client to solicit it.
- A Client **shall** send a connection-level `CREDIT` frame on ChannelId `0`, granting the Server's send direction, within one round trip of receiving its first `OpenDataChannel` response on a SecureChannel, and **shall not** wait for the Server to solicit it.
- A sender **shall not** transmit a `DATA` frame until it has received a connection-level `CREDIT` frame from its peer.
- The value a peer grants as connection credit **shall not** exceed `MaxCreditPerChannel` × `MaxDataChannels`, both read from `ServerCapabilities.DataChannelCapabilities`, capped at `2^32 - 1` so that the bound is always representable in the `ConnectionCredit` field. Both Properties are Mandatory, so this bound is always computable.

Each peer's obligation is triggered by the **peer's** need to send, not by its own. A `CREDIT` frame flows opposite to the data it authorizes, so the Client's grant is what unblocks the Server's send direction — and on a `SourceToSink` channel, the primary case, the Client never sends `DATA` at all. Conditioning the Client's grant on the Client's own sending would leave the camera feed permanently blocked with both peers conformant.

Stating who sends first, and that the window is zero until they do, is what makes the bootstrap decidable. Without it a sender holding a healthy channel credit cannot tell whether it is waiting for a grant that is coming or one that will never arrive.

#### 5.8.2 Spending and replenishing

- A sender **shall not** transmit a `DATA` frame whose payload length exceeds either its remaining channel credit or its remaining connection credit for that direction. It waits, and the channel is in the `Paused` state (§5.13).
- A receiver **shall** `RESET` the channel with `Bad_DataChannelCreditExceeded` on receiving a `DATA` frame whose payload length exceeds the credit it currently has outstanding to that sender.
- `CREDIT`, `GAP`, `RESET`, `END`, `PING` and `PONG` frames are **exempt** from flow control. A creditable `CREDIT` frame would deadlock a stalled channel permanently, and a channel that cannot be reset or probed while stalled cannot be recovered.
- A `CREDIT` frame on a ChannelId other than `0` grants `ChannelCredit` to that channel and, if `ConnectionCredit` is non-zero, that amount to the connection as well. On ChannelId `0`, `ChannelCredit` **shall** be `0`.
- Credit is additive and **shall not** overflow `2^32 - 1`; a sender that receives a grant that would overflow **shall** reset the channel with `Bad_DataChannelCreditExceeded`.
- **A receiver shall replenish.** Whenever a receiver has consumed payload and released the buffer holding it, and its outstanding grant for that channel has fallen below the greater of one half of the value it most recently granted and the channel's `MaxFrameSize`, it **shall** issue a `CREDIT` frame granting at least the bytes it has released. Without this obligation a receiver may legally consume its whole window and never grant another byte, leaving the channel `Paused` forever with neither the sender nor a certification lab able to call it non-conforming.
- A receiver that is deliberately withholding credit as backpressure **shall** nevertheless answer `PING` and **shall** accept and act on `RESET` and `END`.

Backpressure is therefore per channel and per direction: a consumer that cannot keep up with a video stream stalls that stream and nothing else. The connection window exists so the sum of channels cannot exhaust the receiver's memory even when each is individually within its window.

### 5.9 Delivery modes and partial reliability

The delivery mode is negotiated per channel by `OpenDataChannel`. What it can actually deliver depends on the transport, and this specification states the difference rather than hiding it:

| Mode | Inline framing over TCP | `opc.quic` |
|---|---|---|
| `ReliableOrdered` | Exact. TCP already provides it. | Exact. One QUIC stream provides it. |
| `ReliableUnordered` | Every frame arrives; the receiver may deliver frames to the application without waiting to restore order. Over TCP this saves buffering, not latency. | Carried on the channel's QUIC stream. Delivery is ordered by the transport; the receiver is relieved of reassembly buffering but gains no latency. |
| `PartiallyReliable` | Sender-side: a droppable frame still queued at its deadline is discarded. `MaxRetransmits` has no effect, because TCP owns retransmission. | Retransmission over DATAGRAM up to `MaxRetransmits` or the deadline, then abandoned. |
| `Unreliable` | Sender-side discard only. Once a byte is written to the socket, TCP will deliver it. | Exact. A DATAGRAM is sent once and never retransmitted. |

The honest summary for inline framing is that **loss happens in the send queue, not on the wire**. That is a real and useful property — it bounds latency and discards stale media in favour of fresh media — and it is what a TCP-based media path can offer. A Server that needs genuine in-flight loss offers an `opc.quic` endpoint and says so through `SupportsUnreliableDatagrams`.

A sender **shall** apply deadline expiry only to frames carrying `Droppable`. A frame without that flag is transmitted however late it is.

### 5.10 Gap notification

When a sender discards one or more frames, it **shall** emit a `GAP` frame on the same channel naming the discarded range in `FirstDiscarded` and `LastDiscarded`, both **inclusive**.

Per-frame deadlines make a **non-contiguous** discard set the normal case rather than the exception: frames 1 and 3 expire while frame 2, enqueued with a longer deadline, is still live and will be sent. A `GAP` frame names exactly one contiguous, inclusive run, so:

- A sender **shall** emit one `GAP` frame per contiguous run of discarded `FrameSequenceNumber`s.
- A sender **shall not** name in a `GAP` frame any `FrameSequenceNumber` it may still transmit. Widening a range across a surviving frame would declare that frame lost and then deliver it.
- A receiver **shall** discard, without delivering, a frame whose `FrameSequenceNumber` falls inside a run previously named by a `GAP` on the same channel.

A `GAP` frame consumes a `FrameSequenceNumber` of its own from the sender's sequence. Comparison between that number and the range it reports is performed in the serial-number arithmetic of §5.2.1; no ordering invariant between them is asserted, because a discard of frames immediately below the wrap produces a `GAP` whose own number is numerically smaller than the range it carries.

A receiver that observes a `FrameSequenceNumber` discontinuity **shall** treat the missing range as lost whether or not a `GAP` frame arrives, applying §5.2.1. `GAP` is an optimization: it tells the receiver immediately, rather than at the next frame, and it distinguishes "discarded, never coming" from "delayed". Without it a media decoder cannot tell a stall from a loss, and therefore cannot decide whether to conceal or to wait.

A `GAP` frame **shall not** be sent for a `ReliableOrdered` or `ReliableUnordered` channel; a receiver **shall** treat one as a protocol error, because on a reliable channel nothing may be discarded. The `Droppable` restriction in §5.4 is what makes this consistent: on a reliable channel no frame may be marked droppable, so no frame may expire, so no `GAP` can arise.

### 5.11 Reset, half-close and round-trip measurement

- **`RESET`** aborts or summarily closes one data channel and nothing else. The sender discards its queue for that channel and the receiver discards its reassembly state. The `StatusCode` it carries determines the outcome, and is the only wire signal distinguishing the two: a `RESET` carrying `Good` is an **orderly discard-and-close** and both peers transition to `Closed`; a `RESET` carrying a Bad StatusCode is an **abort** and both peers transition to `Faulted`. Without this distinction a `CloseDataChannel` with `deleteQueued` `True` would leave the Server in `Closed` and the Client — which sees only the frame — in `Faulted`, reporting contradictory states for the same channel. The SecureChannel, the Session and every other data channel are unaffected. This separation is the point: a failed stream is not a failed connection.
- **`END`** half-closes. A sender **shall** emit `END` only after every `DATA` frame already queued in that direction has been handed to the transport, and **no `DATA` frame shall follow `END` in that direction**; a receiver **shall** `RESET` the channel with `Bad_DataChannelClosed` on any subsequent `DATA` in that direction. A sender **may** continue to emit `CREDIT`, `GAP`, `PING`, `PONG`, `RESET` and `END` on the channel after `END`, as §5.3 and §5.13 require — on a `SourceToSink` channel the sink's direction is ended at open yet it remains the only party that can grant credit, so a rule silencing it entirely would stall the source the moment its initial window ran out. Making `END` terminal for payload rather than merely announcing an intent to drain is what lets a receiver tell a legitimate draining frame from a violation: it never has to, because there are none. On a `SourceToSink` or `SinkToSource` channel the direction that carries no payload is considered ended at open, so a single `END` closes the channel. On a `Bidirectional` channel both directions **shall** send `END`, and the channel enters `Closed` when both have been observed.
- **`PING`** and **`PONG`** measure the round trip and keep an idle connection alive. A receiver **shall** answer a `PING` with a `PONG` copying the `Timestamp` verbatim and **should** do so ahead of queued `DATA`, so the measurement reflects the path rather than the queue. Copying rather than restamping means the prober keeps no state. `PING` on ChannelId `0` measures the connection; on a data channel it additionally confirms that channel is alive.

**ChannelId reuse.** A Server **shall not** reassign a ChannelId while the SecureChannel that owns it is open. ChannelIds are allocated monotonically from `1`; when the space is exhausted `OpenDataChannel` **shall** return `Bad_TooManyDataChannels`. The alternative — reusing an identifier once "both ends have seen" the close — is not decidable, because no acknowledgement of `RESET` or `END` exists, and a Server guessing wrongly delivers a stale frame from the previous occupant of the identifier to its successor. Monotonic allocation costs a 32-bit counter and removes the hazard entirely; a connection that genuinely opens four billion channels can be recycled by renewing the SecureChannel.

**`PING` rate limiting.** `PING` is exempt from flow control and compels a `PONG` ahead of queued payload, which without a bound is an amplification surface: a peer could emit `PING` at line rate on every open ChannelId and compel the other end to answer at line rate ahead of its own traffic, with no window to close against it. A peer **shall not** have more than one unanswered `PING` outstanding per ChannelId, and **shall not** emit `PING` on a given ChannelId more than once per second. A receiver **may** discard a `PING` that violates either bound, and **may** `RESET` the channel with `Bad_DataChannelLimitsExceeded` if the violation persists.

### 5.12 Error handling

A frame that violates any **shall** in this clause is a protocol error. The receiver's response depends on how localized the fault is:

| Fault | Response |
|---|---|
| Unknown ChannelId, unsupported frame type on a valid channel, payload on a non-`DATA` frame, `GAP` on a reliable channel, credit overflow | `RESET` that channel with the matching StatusCode. The connection continues. |
| Malformed header, non-zero `Reserved` or reserved flag bits, non-zero `RequestId`, `FrameSequenceNumber` of `0`, `IsFinal` of `C`, a frame too short to hold the header its own `FrameType` and flags imply, frame larger than the negotiated buffer, `STR` with no data channel open | Close the SecureChannel under the existing OPC 10000-6 §6.7.7 rules, sending a transport error Message first if the receiver is the Server. |

The dividing line is whether the sender's framing can still be trusted. A bad ChannelId is a bug in one stream; a bad header means the byte stream is no longer being parsed the way the sender wrote it, and no further frame on it can be believed.

### 5.13 Channel state machine

`DataChannelState` (Part 3) has six values. This clause is their normative contract: which event causes which transition, and what may be sent afterwards. A transition not listed here is illegal, and a peer that observes one **shall** `RESET` the channel with `Bad_DataChannelClosed`.

| From | Event | To | Frames permitted after the transition |
|---|---|---|---|
| — | `OpenDataChannel` accepted, response not yet handed to the transport | `Opening` | none |
| `Opening` | response handed to the transport | `Open` | all |
| `Opening` | Service failure, or `OpenTimeout` expires | `Faulted` | none |
| `Open` | remaining send window for this direction is less than the payload length of the head frame ready to send | `Paused` (that direction only) | all except `DATA` in that direction |
| `Paused` | `CREDIT` received making the window at least the head frame's payload length | `Open` | all |
| `Open`, `Paused` | `END` sent or received | `Closing` | `GAP`, `CREDIT`, `PING`, `PONG`, `RESET`, `END` — no `DATA` in the ended direction |
| `Open`, `Paused` | `CloseDataChannel` with `deleteQueued` `False` | `Closing` | `DATA` already queued at the transition, until the drain completes, then `END`; plus `GAP`, `CREDIT`, `PING`, `PONG`, `RESET` |
| `Closing` | `END` observed in every direction the channel carries | `Closed` | none |
| `Closing` | `DrainTimeout` expires before this peer has emitted its own `END` | `Faulted` | none |
| any | `RESET` carrying `Good` sent or received | `Closed` | none |
| any | `RESET` carrying a Bad StatusCode sent or received | `Faulted` | none |
| any | SecureChannel closed, transport lost, Session closed, authorizing user identity changed, or the Session transferred to a different SecureChannel | `Faulted` | none |

The following are normative consequences:

- `Paused` is **per direction**. A `Bidirectional` channel whose send window is exhausted while its receive window is open is `Paused` in the send direction only, and the `DataChannelStatusDataType.State` reported for it is the state of the direction the reader is sending in. Entry and exit use the same test — the window against the head frame's payload length — so a channel cannot be stalled under §5.8.2 while still reporting `Open`.
- A sender **shall not** enqueue **new** payload on a channel in `Closing`; frames already queued when it entered `Closing` may still be sent, and `END` follows the last of them. `END` is terminal for payload in its direction (§5.11), so once a peer has emitted `END` no `DATA` follows it and a receiver never has to distinguish a draining frame from a violation.
- The two entry paths into `Closing` differ deliberately. Entering through `END` means the drain has already happened, so no `DATA` may follow. Entering through `CloseDataChannel` with `deleteQueued` `False` means the drain is the point, so queued `DATA` still flows until `END`.
- `DrainTimeout` bounds a peer's **own** drain — the interval between entering `Closing` and emitting its own `END` — not the wait for the peer's reverse `END`. A `Bidirectional` channel on which one end half-closes while the other is still legitimately sending a long upload must not be destroyed five seconds later; the wait for the reverse `END` is bounded by `PingTimeout` instead, which tests whether the peer is alive rather than whether it is finished.
- `CloseDataChannel` with `deleteQueued` `True` is realized as a `RESET` carrying `Good` and therefore reaches `Closed` by that row, on both peers.
- Over `opc.quic` there are no `CREDIT` frames (§5.8, §7.4), so `Paused` is entered when the channel's QUIC stream or the QUIC connection is flow-control blocked, and left when it unblocks.
- A `DataChannelStateChangeEventType` Event **shall** be raised for every transition **except** `Open` ⇄ `Paused`, which a Server **shall** report at no more than one Event per channel per second and which is otherwise observed through the `CreditStalls` counter of `DataChannelDiagnosticsDataType`. Without this ceiling a saturated media channel would generate an Event per credit stall — an Event storm at frame rate, on the very Subscription path §5.7 exists to protect.

### 5.14 Timeouts

Every timeout below is a named constant so that a test plan can reference it and two implementations cannot silently disagree about when a peer is dead. The values are defaults; a Server **may** use different values and **should** publish them, but **shall not** leave `OpenTimeout`, `DrainTimeout` or `PingTimeout` unbounded.

| Constant | Applies to | Default | On expiry |
|---|---|---|---|
| `OpenTimeout` | `Opening` | 10 s | The channel enters `Faulted`; `OpenDataChannel` returns `Bad_Timeout`. |
| `DrainTimeout` | the interval between a peer entering `Closing` and emitting its own `END` | 5 s | Queued frames are discarded and the channel enters `Faulted`. It does **not** bound the wait for the peer's reverse `END`, which `PingTimeout` covers. |
| `PingTimeout` | an unanswered `PING` | 3 × the most recently measured round trip, floored at 1 s and capped at 30 s | The peer **may** `RESET` the channel, or close the SecureChannel if the `PING` was on ChannelId `0`. |
| `IdleTimeout` | an `Open` channel carrying no `DATA` | Server-defined; `0` disables it | The Server **may** `RESET` the channel with `Bad_DataChannelClosed`. |

A peer **shall not** `RESET` a channel for idleness while a `PING` it issued on that channel is being answered within `PingTimeout`: a channel that is demonstrably alive is not idle in the sense that matters.

### 5.15 Sender and receiver algorithms

These algorithms are **informative**; they are one correct realization of the normative rules of §5.4 to §5.13, collected here because the rules are otherwise scattered across nine clauses and an implementer has to assemble them. Where an algorithm and a normative clause differ, the clause governs.

**Sender, once per scheduling round:**

```text
for each channel C with a non-empty queue:
    expire: remove queued frames of C that carry Droppable and whose Deadline has passed
    for each contiguous run R of removed FrameSequenceNumbers:
        queue GAP(C, first(R), last(R)) for transmission            # §5.10, one frame per run
    C.deficit += (C.priority + 1) * C.maxFrameSize                  # §5.7
drain one pending MSG/OPN/CLO chunk if any                          # §5.7 obligation 1
for each channel C in descending priority:
    emit any queued control frames for C   # exempt from credit and deficit, §5.8.2
    while C.queue is non-empty:
        F = head(C.queue)              # DATA frames leave in ascending FSN order, §5.2
        if len(F.payload) > C.deficit:            break
        if len(F.payload) > C.credit[dir]:        record CreditStall; break   # §5.8.2
        if len(F.payload) > connectionCredit[dir]: record CreditStall; break
        emit F
        C.deficit             -= len(F.payload)
        C.credit[dir]         -= len(F.payload)
        connectionCredit[dir] -= len(F.payload)
        drain one pending MSG/OPN/CLO chunk if any  # at most one frame of delay
    if C.queue is empty: C.deficit = 0
```

`GAP` frames are queued rather than emitted inside the expiry loop so that they interleave with the surviving `DATA` frames instead of preceding all of them, but they are drained ahead of the credit-gated loop because §5.8.2 exempts control frames from flow control — a `GAP` stuck behind a credit-blocked `DATA` frame would never be sent, and a credit stall is exactly what caused the expiry it reports. Either relative order is legal on the wire, because §5.2.1 does not let a control frame advance the receiver's `HighestReceived`.

**Receiver, per frame:**

```text
decode and validate per §5.12                     # reject or RESET as the table directs
if ChannelId unknown and an OpenDataChannel for it is outstanding:
    buffer for up to one round-trip, then re-evaluate   # §7.4 ordering rule
if FrameType is not DATA:
    handle the control frame; do NOT advance HighestReceived        # §5.2.1
    for GAP: record the named run so later frames in it are dropped # §5.10
else:
    if the number falls inside a range named by an earlier GAP: discard, done  # §5.10
    compare FrameSequenceNumber per §5.2.1:
        in sequence      -> deliver
        ahead by > 1     -> report gap, deliver, advance
        duplicate        -> discard silently, done
        outside window   -> RESET the channel, done
    account len(payload) against the inbound channel and connection windows
    deliver per the mode's ordering rule                            # §5.4
    when the buffer is released and the outstanding grant has fallen below
        max(half the last grant, MaxFrameSize):  emit CREDIT         # §5.8.2
```

**Buffer sizing.** `InitialCredit` **should** be at least the bandwidth-delay product of the path — the channel's expected rate multiplied by the round trip measured by `PING`/`PONG` — because a window smaller than that caps throughput at `InitialCredit` / RTT regardless of available bandwidth. `MaxFrameSize` trades per-frame overhead against latency and loss granularity: the 36-byte inline and 24-byte QUIC overheads of §5.5 are amortized better by large frames, while a small frame lowers the time an urgent frame waits behind the one in front of it and reduces what a single loss destroys. For media over `opc.quic` the frame size **should** be chosen so that a whole frame fits one QUIC DATAGRAM without IP fragmentation, which is what fixes the 1200-byte figure used in the worked example of the combined specification.

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

`Hello` and `Acknowledge` are exchanged unchanged. Their `ReceiveBufferSize` and `SendBufferSize` continue to bound MessageChunks on the control stream. A data channel frame is bounded by the smaller of `revisedParameters.MaxFrameSize` and the QUIC stream or datagram limit, not by these values.

Losing the control stream **shall** be treated as losing the SecureChannel: every data channel is aborted.

### 7.4 Stream mapping

Each data channel is bound at open to one QUIC stream, whose identifier is carried in `transportChannelId`:

| Direction | QUIC stream | Initiator | Where `transportChannelId` is carried |
|---|---|---|---|
| `SourceToSink` | server-initiated unidirectional | Server | `OpenDataChannel` **response** |
| `SinkToSource` | client-initiated unidirectional | Client | `OpenDataChannel` **request**, echoed in the response |
| `Bidirectional` | client-initiated bidirectional | Client | `OpenDataChannel` **request**, echoed in the response |

`OpenDataChannel` is a Service and is therefore always invoked by the Client, so for the two Client-initiated directions the Server cannot report an identifier it does not choose. The Client **shall** open the QUIC stream **before** issuing the call, carry its stream id in the request, and **shall not** write any frame to it until the response arrives. A Server **shall** return `Bad_DataChannelLimitsExceeded` if a request over `opc.quic` omits `transportChannelId` for a Client-initiated direction, and **shall** echo the value it was given in the response. Over inline framing `transportChannelId` is `0` in both directions.

**Ordering against the Service response.** QUIC provides no ordering between streams, so a `DATA` frame written to a data channel's stream can overtake the `OpenDataChannel` response written to the control stream. Left unstated this is a live race, because §5.1 and §5.12 both punish a receiver that sees an unrecognized ChannelId. Therefore:

- A peer **shall not** transmit a `DATA`, `GAP`, `END` or `RESET` frame for a ChannelId before the `OpenDataChannel` response carrying that ChannelId has been handed to the transport. Over `opc.quic` a Server **shall not** write to a data channel's QUIC stream before that response has been written to the control stream.
- A receiver **shall** buffer, for at least one round-trip time, a frame naming a ChannelId for which an `OpenDataChannel` call is outstanding, and **shall** apply the unknown-ChannelId rule of §5.12 only after that call has completed.

The same obligation applies to inline framing, where the sender controls the byte order and can simply serialize the two.

A QUIC stream carries a sequence of frames in **QUIC framing**: the Message header followed directly by the stream header, payload and nothing else. The symmetric security header, the sequence header and the message footer are omitted, because QUIC's TLS 1.3 record layer already authenticates and encrypts every byte and QUIC already orders and deduplicates each stream. The Message header is retained so that one decoder serves both transports and an intermediary can delimit frames without possessing keys. `MessageSize` remains the authoritative frame length, so a stream is self-delimiting.

Because QUIC applies its own per-stream and per-connection flow control, `CREDIT` frames **shall not** be sent over `opc.quic` and a receiver **shall** ignore one. Duplicating the window in two layers gains nothing and deadlocks when the two disagree.

Closing a data channel **shall** close its QUIC stream; `RESET` **shall** be realized as a QUIC `RESET_STREAM`, whose application error code carries the StatusCode.

### 7.5 Unreliable datagrams

When the negotiated delivery mode is `Unreliable`, or `PartiallyReliable` and both ends advertised the QUIC DATAGRAM extension in the transport parameters, `DATA` frames **shall** be sent as QUIC DATAGRAM frames (RFC 9221) rather than on the channel's stream. Control frames always use the stream, so a `RESET` or an `END` is never lost.

A datagram carries exactly one frame in QUIC framing, and the frame **shall** fit `max_datagram_frame_size`. Fragmenting a frame across datagrams is **not** permitted: one lost fragment would destroy a frame that the receiver could otherwise have used in part, which defeats the reason for choosing datagrams.

Where the peer's `max_datagram_frame_size` transport parameter is absent or zero, the QUIC DATAGRAM extension is unavailable and a Server **shall** reject an `Unreliable` or `PartiallyReliable` request with `Bad_DeliveryModeUnsupported` rather than silently carrying it on the channel's stream, which would deliver a reliability guarantee the application did not ask for and did not budget latency for.

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
| Data Channel Framing | — | Clause 5 in full: `STR` frames, stream header, all seven frame types, flags, the single-chunk rule, sequence arithmetic (§5.2.1), credit flow control, scheduling obligations, gap notification, reset, half-close, error handling, the state machine (§5.13) and the timeouts (§5.14). |
| Data Channel Inline Transport | Data Channel Framing | §6.1 and §6.2: framing over `opc.tcp` and `opc.wss` with no change to `Hello`/`Acknowledge`. |
| Data Channel Partial Reliability | Data Channel Framing | The `Droppable` flag, `Deadline`, sender-side expiry and per-run `GAP` emission (§5.9, §5.10). |
| Data Channel QUIC Transport | Data Channel Framing | Clause 7 except §7.5: `opc.quic`, ALPN, control stream, per-channel QUIC streams and their stream-id ownership, the response-ordering rule, the `TransportSecured` profile, migration. |
| Data Channel Unreliable Datagram | Data Channel QUIC Transport, Data Channel Partial Reliability | §7.5: `DATA` over QUIC DATAGRAM with genuine in-flight loss. |

Data Channel Framing plus Data Channel Inline Transport is the minimum implementation. The Part 4 and Part 3 errata define the Service and Model conformance units that build on these.

### 8.1 Test assertions

A conformance unit is only useful if a laboratory can derive test cases from it, so each is decomposed into individually checkable assertions. Every one below is a receiver- or sender-observable behaviour required by a **shall** in clause 5, 6 or 7.

**Data Channel Framing**

| Id | Assertion | Stimulus | Expected |
|---|---|---|---|
| DCF-001 | A `STR` chunk with `IsFinal` `C` is rejected | Send one | SecureChannel closed (§5.12) |
| DCF-002 | A non-zero `RequestId` is rejected | Send one | SecureChannel closed |
| DCF-003 | `FrameSequenceNumber` `0` is rejected | Send one | SecureChannel closed |
| DCF-004 | A non-zero `Reserved` is rejected | Send one | SecureChannel closed |
| DCF-005 | A reserved flag bit is rejected | `Flags` = `0x20` | SecureChannel closed |
| DCF-006 | A reserved `FrameType` is rejected | `FrameType` = `7` | `RESET` on that channel |
| DCF-007 | Payload on a non-`DATA` frame is rejected | `END` plus one byte | `RESET` on that channel |
| DCF-008 | Only `CREDIT`/`PING`/`PONG` are accepted on ChannelId `0` | `DATA` on ChannelId `0` | `RESET` or SecureChannel closed |
| DCF-009 | A frame too short for the header its `FrameType` and flags imply is rejected | `CREDIT` truncated to one of its two fields, `MessageSize` patched to match | SecureChannel closed |
| DCF-010 | A sender honours channel credit | Grant `N`, offer `N`+1 bytes of payload | No `DATA` frame beyond `N` payload bytes |
| DCF-011 | A sender honours connection credit | As DCF-010 at connection level | No `DATA` frame beyond `N` payload bytes |
| DCF-012 | A sender does not transmit before connection credit arrives | Open a channel, withhold the connection `CREDIT` | No `DATA` frame emitted (§5.8.1) |
| DCF-013 | A receiver replenishes credit | Consume and release a full window | `CREDIT` frame issued (§5.8.2) |
| DCF-014 | Control frames flow while credit is `0` | `PING` on a stalled channel | `PONG` returned |
| DCF-015 | Service traffic is not starved | Saturate a channel, then issue a `Read` | Response not delayed beyond one maximum-size frame (§5.7) |
| DCF-016 | No ready channel starves | Two channels, `Priority` 6 and 1, both saturated | Both progress; neither is served twice while the other is ready and unserved (§5.7 obligation 2) |
| DCF-017 | The sequence number wraps without a reported gap | Drive `4294967295` → `1` | No gap reported (§5.2.1) |
| DCF-018 | A duplicate inside the replay window is discarded silently | Retransmit a `DATA` frame | No gap reported, no `RESET`, payload not delivered twice |
| DCF-019 | A control frame does not advance `HighestReceived` | A `GAP`, then a surviving lower-numbered `DATA` frame | The survivor is delivered, not discarded as a duplicate (§5.2.1) |
| DCF-020 | A `GAP` on a reliable channel is rejected | Send one on `ReliableOrdered` | `RESET` on that channel |
| DCF-021 | `Droppable` on a reliable channel is rejected | Set the flag on `ReliableOrdered` | `RESET` with `Bad_DeliveryModeUnsupported` (§5.4) |
| DCF-022 | `DATA` in a direction the channel forbids is rejected | Sink sends on `SourceToSink` | `RESET` with `Bad_DataChannelDirectionUnsupported` (§5.3) |
| DCF-023 | `DATA` after `END` in the same direction is rejected | Send one | `RESET` with `Bad_DataChannelClosed` (§5.11) |
| DCF-024 | `Open` ⇄ `Paused` Events are rate-limited | Saturate a channel for 10 s | At most 10 such Events for that channel; `CreditStalls` increments freely (§5.13) |
| DCF-025 | A ChannelId is not reused while the SecureChannel is open | Open and close channels repeatedly | Every assigned ChannelId is distinct (§5.11) |
| DCF-026 | A sender bounds its own `PING` rate | Observe a sender for 10 s | At most one `PING` per ChannelId per second, and never a second while one is unanswered (§5.11) |
| DCF-027 | `DrainTimeout` bounds a peer's own drain | Enter `Closing`, then withhold the local `END` | Channel reaches `Faulted` within `DrainTimeout`; a peer awaiting the *reverse* `END` is not faulted by it (§5.14) |
| DCF-028 | A `RESET` carrying `Good` closes rather than faults | Send one | Channel reports `Closed`, not `Faulted` (§5.11, §5.13) |

**Data Channel Partial Reliability**

| Id | Assertion | Stimulus | Expected |
|---|---|---|---|
| DCP-001 | An expired droppable frame is discarded, not sent late | Enqueue with a short deadline behind a stall | Frame never appears on the wire |
| DCP-002 | One `GAP` is emitted per contiguous run | Expire frames 1 and 3 while 2 survives | Two `GAP` frames, `1..1` and `3..3` (§5.10) |
| DCP-003 | A `GAP` never names a frame that is later sent | As DCP-002 | Frame 2 is transmitted and was not named |
| DCP-004 | A receiver discards a frame inside a previously named `GAP` run | Send a frame whose number was named | Not delivered to the application |

**Data Channel QUIC Transport**

| Id | Assertion | Stimulus | Expected |
|---|---|---|---|
| DCQ-001 | ALPN is negotiated | Offer a foreign ALPN | Connection abandoned (§7.2) |
| DCQ-002 | The Client supplies the stream id for Client-initiated directions | `OpenDataChannel` for `Bidirectional` with no `transportChannelId` | `Bad_DataChannelLimitsExceeded` (§7.4) |
| DCQ-003 | No frame precedes the `OpenDataChannel` response | Observe the control stream and the data stream | Response written first (§7.4) |
| DCQ-004 | `CREDIT` frames are not sent over `opc.quic` | Open a channel and saturate it | No `CREDIT` frame observed (§7.4) |
| DCQ-005 | 0-RTT carries no channel open | Attempt one | Rejected (§7.6) |
| DCQ-006 | Datagram modes are refused without the extension | Request `Unreliable` with `max_datagram_frame_size` absent | `Bad_DeliveryModeUnsupported` (§7.5) |

DCF-015 and DCF-016 fail only under load, which is what makes them the assertions that most often distinguish a conforming implementation from one that merely interoperates in the laboratory. DCF-016 checks the anti-starvation `shall` of §5.7 obligation 2 rather than a particular bandwidth ratio, because the (`Priority` + 1) × `MaxFrameSize` quantum that would fix the ratio is a `should` and a laboratory cannot fail an implementation on a recommendation. `OpenTimeout` has no assertion of its own: §5.13 ends `Opening` when the Server hands its own response to the transport, so no external harness can stall it.

## 9 Insertion into OPC 10000-6 v1.05.07

| Draft clause | Target clause in OPC 10000-6 | Notes |
|---|---|---|
| §5.1 `STR` MessageChunk | `6.7.2.2 Message Header` | Adds `STR` to the `MessageType` table and states the `IsFinal`, `SequenceNumber` and `RequestId` rules. No change to the header layout. |
| §5.1 reused headers | `6.7.2.3`, `6.7.2.4`, `6.7.2.5` | No change. A note that these clauses apply unchanged to `STR` is sufficient. |
| §5.2 to §5.6 framing | New `6.7.8 Data channel frames` | The stream header, frame types, flags and the single-chunk rule, as a new subclause of OPC UA Secure Conversation. §5.2.1 adds the serial-number arithmetic and gap-detection rules. |
| §5.7 scheduling | New `6.7.9 Data channel scheduling` | The two sender obligations and the deficit-round-robin quantum. May instead be folded into `6.7.8` at the editor's discretion. |
| §5.8 to §5.11 | New `6.7.10 Data channel flow control and lifecycle` | Credit bootstrap and replenishment, delivery modes, gap notification, reset, half-close, ChannelId allocation, round-trip measurement and `PING` bounds. |
| §5.12 error handling | `6.7.7 Verifying Message Security` | Extends the existing "close the channel on error" rule with the narrower per-channel `RESET` response, and states which faults take which path. |
| §5.13 state machine | New `6.7.11 Data channel states` | The state transition table. Referenced normatively by the Part 3 `DataChannelState` enumeration. |
| §5.14 timeouts | New `6.7.12 Data channel timeouts` | The four named constants and their defaults. |
| §5.15 algorithms | A new informative annex of OPC 10000-6 | Sender and receiver algorithms and buffer-sizing guidance; informative, and marked as such. |
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
