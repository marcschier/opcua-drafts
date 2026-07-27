#!/usr/bin/env python3
"""
Reference frame codec for the OPC UA Data Channels wire format.

This module is the executable definition of the `STR` frame described in
`core-specs/data-channels/OPC-UA-Part6-Data-Channel-Transport.md`. It exists so the
byte layouts in that document and the test vectors under
`core-specs/extras/data-channels/examples/` can never drift from the prose: both are
generated from here.

Two framing modes are defined, differing only in which headers precede the stream
header:

  INLINE  (opc.tcp, opc.wss) - the frame is a normal OPC UA Secure Conversation
          MessageChunk. The Message header, symmetric security header, sequence
          header and message footer are exactly those of a `MSG` chunk, so signing,
          encryption, sequence-number verification and channel-token rollover apply
          unchanged. The stream header is the first thing in the encrypted body.

  QUIC    (opc.quic) - the frame rides a QUIC stream or DATAGRAM, whose TLS 1.3
          record layer already authenticates and encrypts it and whose per-stream
          ordering already sequences it. The UA-SC security header, sequence header
          and footer are therefore omitted; the Message header is retained so one
          decoder serves both transports and so a relay can frame without decrypting.

Every integer is little-endian, matching the OPC UA Binary DataEncoding.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

# --- Framing modes ---------------------------------------------------------
INLINE = "inline"
QUIC = "quic"

MESSAGE_TYPE = b"STR"
CHUNK_TYPE_FINAL = b"F"
CHUNK_TYPE_ABORT = b"A"

MESSAGE_HEADER_SIZE = 12       # MessageType[3] + IsFinal[1] + MessageSize + SecureChannelId
SECURITY_HEADER_SIZE = 4       # TokenId
SEQUENCE_HEADER_SIZE = 8       # SequenceNumber + RequestId
STREAM_HEADER_SIZE = 12        # ChannelId + FrameType + Flags + Reserved + FrameSequenceNumber
DEADLINE_SIZE = 8              # Int64, present only when FLAG_DEADLINE is set

# The connection-level control channel. CREDIT frames for the connection window and
# PING/PONG frames use it; it never carries payload.
CONNECTION_CHANNEL_ID = 0

# --- Frame types -----------------------------------------------------------
FT_DATA = 0
FT_CREDIT = 1
FT_GAP = 2
FT_RESET = 3
FT_END = 4
FT_PING = 5
FT_PONG = 6

FRAME_TYPE_NAMES = {
    FT_DATA: "DATA",
    FT_CREDIT: "CREDIT",
    FT_GAP: "GAP",
    FT_RESET: "RESET",
    FT_END: "END",
    FT_PING: "PING",
    FT_PONG: "PONG",
}
FRAME_TYPE_VALUES = {v: k for k, v in FRAME_TYPE_NAMES.items()}

# Frames that are exempt from flow control. Making CREDIT itself creditable would
# deadlock a stalled channel, and the control frames must always be able to abort or
# probe a channel that has run out of window.
CREDIT_EXEMPT = frozenset({FT_CREDIT, FT_GAP, FT_RESET, FT_END, FT_PING, FT_PONG})

# --- Flags -----------------------------------------------------------------
FLAG_MESSAGE_START = 0x01
FLAG_MESSAGE_END = 0x02
FLAG_DROPPABLE = 0x04
FLAG_DEADLINE = 0x08
FLAG_MARKER = 0x10
FLAG_RESERVED_MASK = 0xE0

FLAG_NAMES = [
    (FLAG_MESSAGE_START, "MessageStart"),
    (FLAG_MESSAGE_END, "MessageEnd"),
    (FLAG_DROPPABLE, "Droppable"),
    (FLAG_DEADLINE, "DeadlinePresent"),
    (FLAG_MARKER, "Marker"),
]

# Fixed extra fields carried by each frame type, in order, as (name, struct code, size).
EXTRA_FIELDS = {
    FT_DATA: (),
    FT_CREDIT: (("ChannelCredit", "<I", 4), ("ConnectionCredit", "<I", 4)),
    FT_GAP: (("FirstDiscarded", "<I", 4), ("LastDiscarded", "<I", 4)),
    FT_RESET: (("StatusCode", "<I", 4),),
    FT_END: (),
    FT_PING: (("Timestamp", "<q", 8),),
    FT_PONG: (("Timestamp", "<q", 8),),
}


class FrameError(ValueError):
    """Raised when a frame cannot be encoded or decoded as specified."""


def flag_names(flags: int) -> list[str]:
    return [name for bit, name in FLAG_NAMES if flags & bit]


@dataclass
class Frame:
    """One data channel frame.

    `secure_channel_id`, `token_id` and `sequence_number` belong to the enclosing
    SecureChannel, not to the data channel: they are carried here only so a frame can
    be encoded and decoded standalone.
    """

    channel_id: int
    frame_type: int = FT_DATA
    flags: int = 0
    frame_sequence_number: int = 0
    payload: bytes = b""
    deadline: int | None = None
    extras: dict = field(default_factory=dict)
    secure_channel_id: int = 0
    token_id: int = 0
    sequence_number: int = 0
    abort: bool = False

    def __post_init__(self):
        if self.deadline is not None:
            self.flags |= FLAG_DEADLINE
        elif self.flags & FLAG_DEADLINE:
            raise FrameError("FLAG_DEADLINE set but no deadline supplied")

    @property
    def type_name(self) -> str:
        return FRAME_TYPE_NAMES.get(self.frame_type, f"Reserved({self.frame_type})")

    def credit_cost(self) -> int:
        """Payload bytes this frame consumes from the peer's window."""
        return 0 if self.frame_type in CREDIT_EXEMPT else len(self.payload)


def prefix_size(mode: str) -> int:
    """Bytes preceding the stream header in the given framing mode."""
    if mode == INLINE:
        return MESSAGE_HEADER_SIZE + SECURITY_HEADER_SIZE + SEQUENCE_HEADER_SIZE
    if mode == QUIC:
        return MESSAGE_HEADER_SIZE
    raise FrameError(f"unknown framing mode {mode!r}")


def max_payload(mode: str, buffer_size: int, *, deadline: bool = False,
                frame_type: int = FT_DATA, footer_size: int = 0) -> int:
    """Largest payload that fits a frame bounded by `buffer_size`.

    `footer_size` is the Part 6 message footer (padding plus signature) the security
    policy in force adds to an INLINE frame; it is zero for SecurityMode None and for
    QUIC framing, which has no UA-SC footer.
    """
    overhead = prefix_size(mode) + STREAM_HEADER_SIZE + footer_size
    overhead += DEADLINE_SIZE if deadline else 0
    overhead += sum(size for _n, _c, size in EXTRA_FIELDS[frame_type])
    return max(0, buffer_size - overhead)


def _extras_bytes(frame: Frame) -> bytes:
    out = b""
    for name, code, _size in EXTRA_FIELDS[frame.frame_type]:
        if name not in frame.extras:
            raise FrameError(f"{frame.type_name} frame requires the {name} field")
        out += struct.pack(code, frame.extras[name])
    return out


def encode(frame: Frame, mode: str = INLINE, *, footer: bytes = b"") -> bytes:
    """Serialize a frame. `footer` is the already-computed padding+signature for
    INLINE framing under a signing or encrypting security policy."""
    if frame.frame_type not in FRAME_TYPE_NAMES:
        raise FrameError(f"unknown frame type {frame.frame_type}")
    if frame.flags & FLAG_RESERVED_MASK:
        raise FrameError("reserved flag bits shall be zero")
    if frame.payload and frame.frame_type != FT_DATA:
        raise FrameError(f"{frame.type_name} frames carry no payload")
    if frame.channel_id == CONNECTION_CHANNEL_ID and frame.frame_type not in (
            FT_CREDIT, FT_PING, FT_PONG):
        raise FrameError("ChannelId 0 carries only CREDIT, PING and PONG frames")
    if frame.frame_sequence_number == 0:
        raise FrameError("FrameSequenceNumber starts at 1 and wraps to 1; 0 is never valid")
    if mode == QUIC and footer:
        raise FrameError("QUIC framing has no UA-SC message footer")

    body = struct.pack("<IBBHI", frame.channel_id, frame.frame_type, frame.flags, 0,
                       frame.frame_sequence_number)
    if frame.flags & FLAG_DEADLINE:
        body += struct.pack("<q", frame.deadline)
    body += _extras_bytes(frame)
    body += frame.payload

    if mode == INLINE:
        # RequestId is 0: a data channel frame is not a Service invocation, and the
        # ChannelId in the stream header is the demultiplexing key. Folding the
        # ChannelId into RequestId would risk colliding with an in-flight RPC.
        body = struct.pack("<I", frame.token_id) + \
            struct.pack("<II", frame.sequence_number, 0) + body
    elif mode != QUIC:
        raise FrameError(f"unknown framing mode {mode!r}")

    total = MESSAGE_HEADER_SIZE + len(body) + len(footer)
    chunk = CHUNK_TYPE_ABORT if frame.abort else CHUNK_TYPE_FINAL
    head = MESSAGE_TYPE + chunk + struct.pack("<II", total, frame.secure_channel_id)
    return head + body + footer


def decode(data: bytes, mode: str = INLINE, *, footer_size: int = 0) -> Frame:
    """Parse a frame. Raises FrameError on anything a conforming receiver must reject."""
    least = prefix_size(mode) + STREAM_HEADER_SIZE + footer_size
    if len(data) < least:
        raise FrameError(f"frame shorter than the {least} byte minimum")
    if data[0:3] != MESSAGE_TYPE:
        raise FrameError(f"not a data channel frame: MessageType {data[0:3]!r}")
    chunk = data[3:4]
    if chunk not in (CHUNK_TYPE_FINAL, CHUNK_TYPE_ABORT):
        raise FrameError("a data channel frame is always a single chunk: IsFinal "
                         "shall be 'F', or 'A' to abort the SecureChannel")
    size, secure_channel_id = struct.unpack("<II", data[4:12])
    if size != len(data):
        raise FrameError(f"MessageSize {size} does not match the {len(data)} bytes received")

    off = MESSAGE_HEADER_SIZE
    token_id = sequence_number = 0
    if mode == INLINE:
        (token_id,) = struct.unpack("<I", data[off:off + 4])
        off += SECURITY_HEADER_SIZE
        sequence_number, request_id = struct.unpack("<II", data[off:off + 8])
        off += SEQUENCE_HEADER_SIZE
        if request_id != 0:
            raise FrameError("RequestId shall be 0 in a data channel frame")

    channel_id, frame_type, flags, reserved, fsn = struct.unpack("<IBBHI", data[off:off + 12])
    off += STREAM_HEADER_SIZE
    if reserved != 0:
        raise FrameError("reserved stream header bytes shall be zero")
    if flags & FLAG_RESERVED_MASK:
        raise FrameError("reserved flag bits shall be zero")
    if frame_type not in FRAME_TYPE_NAMES:
        raise FrameError(f"unknown frame type {frame_type}")
    if channel_id == CONNECTION_CHANNEL_ID and frame_type not in (FT_CREDIT, FT_PING, FT_PONG):
        raise FrameError("ChannelId 0 carries only CREDIT, PING and PONG frames")
    if fsn == 0:
        raise FrameError("FrameSequenceNumber starts at 1 and wraps to 1; 0 is never valid")

    # Only now is the true minimum length known: the optional Deadline and the extra
    # fields are both determined by bytes inside the stream header. Checking it up front
    # would either under-count (and let struct.unpack read past the end of a frame whose
    # MessageSize was set to its own truncated length) or over-count.
    needed = off + (DEADLINE_SIZE if flags & FLAG_DEADLINE else 0)
    needed += sum(size for _n, _c, size in EXTRA_FIELDS[frame_type])
    if len(data) - footer_size < needed:
        raise FrameError(f"{FRAME_TYPE_NAMES[frame_type]} frame is truncated: "
                         f"{needed} bytes of header required before payload, "
                         f"{len(data) - footer_size} available")

    deadline = None
    if flags & FLAG_DEADLINE:
        (deadline,) = struct.unpack("<q", data[off:off + DEADLINE_SIZE])
        off += DEADLINE_SIZE

    extras = {}
    for name, code, fsize in EXTRA_FIELDS[frame_type]:
        (extras[name],) = struct.unpack(code, data[off:off + fsize])
        off += fsize

    end = len(data) - footer_size
    if end < off:
        raise FrameError("the message footer overlaps the frame header")
    payload = data[off:end]
    if payload and frame_type != FT_DATA:
        raise FrameError(f"{FRAME_TYPE_NAMES[frame_type]} frames carry no payload")

    return Frame(channel_id=channel_id, frame_type=frame_type, flags=flags & ~FLAG_DEADLINE,
                 frame_sequence_number=fsn, payload=payload, deadline=deadline,
                 extras=extras, secure_channel_id=secure_channel_id, token_id=token_id,
                 sequence_number=sequence_number, abort=(chunk == CHUNK_TYPE_ABORT))


# --- Byte-layout annotation -------------------------------------------------
@dataclass
class Span:
    offset: int
    length: int
    field: str
    value: str
    section: str

    @property
    def end(self) -> int:
        return self.offset + self.length


def annotate(data: bytes, mode: str = INLINE, *, footer_size: int = 0) -> list[Span]:
    """Break a frame into contiguous, fully covering byte spans for the generated annex."""
    spans: list[Span] = []
    mh = "Message header"
    spans.append(Span(0, 3, "MessageType", f"'{data[0:3].decode('ascii')}'", mh))
    spans.append(Span(3, 1, "IsFinal", f"'{data[3:4].decode('ascii')}'", mh))
    size, scid = struct.unpack("<II", data[4:12])
    spans.append(Span(4, 4, "MessageSize", str(size), mh))
    spans.append(Span(8, 4, "SecureChannelId", str(scid), mh))

    off = MESSAGE_HEADER_SIZE
    if mode == INLINE:
        (token_id,) = struct.unpack("<I", data[off:off + 4])
        spans.append(Span(off, 4, "TokenId", str(token_id), "Symmetric security header"))
        off += 4
        seq, rid = struct.unpack("<II", data[off:off + 8])
        spans.append(Span(off, 4, "SequenceNumber", str(seq), "Sequence header"))
        spans.append(Span(off + 4, 4, "RequestId", str(rid), "Sequence header"))
        off += 8

    sh = "Stream header"
    channel_id, frame_type, flags, reserved, fsn = struct.unpack("<IBBHI", data[off:off + 12])
    spans.append(Span(off, 4, "ChannelId", str(channel_id), sh))
    spans.append(Span(off + 4, 1, "FrameType",
                      f"{frame_type} ({FRAME_TYPE_NAMES[frame_type]})", sh))
    spans.append(Span(off + 5, 1, "Flags",
                      f"0x{flags:02X} ({', '.join(flag_names(flags)) or 'none'})", sh))
    spans.append(Span(off + 6, 2, "Reserved", str(reserved), sh))
    spans.append(Span(off + 8, 4, "FrameSequenceNumber", str(fsn), sh))
    off += STREAM_HEADER_SIZE

    if flags & FLAG_DEADLINE:
        (deadline,) = struct.unpack("<q", data[off:off + DEADLINE_SIZE])
        spans.append(Span(off, DEADLINE_SIZE, "Deadline", str(deadline), sh))
        off += DEADLINE_SIZE

    for name, code, fsize in EXTRA_FIELDS[frame_type]:
        (val,) = struct.unpack(code, data[off:off + fsize])
        spans.append(Span(off, fsize, name, str(val),
                          f"{FRAME_TYPE_NAMES[frame_type]} fields"))
        off += fsize

    end = len(data) - footer_size
    if end > off:
        spans.append(Span(off, end - off, "Payload", f"{end - off} bytes", "Payload"))
    if footer_size:
        spans.append(Span(end, footer_size, "PaddingSize / Padding / Signature",
                          f"{footer_size} bytes", "Message footer"))
    return spans


def check_contiguous(spans: list[Span], total: int) -> None:
    """Assert the annotation covers every byte exactly once."""
    pos = 0
    for s in spans:
        if s.offset != pos:
            raise FrameError(f"annotation gap or overlap at offset {pos} (span {s.field})")
        pos = s.end
    if pos != total:
        raise FrameError(f"annotation covers {pos} of {total} bytes")


def hexdump(data: bytes, width: int = 16) -> str:
    lines = []
    for i in range(0, len(data), width):
        row = data[i:i + width]
        hexpart = " ".join(f"{b:02X}" for b in row)
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        lines.append(f"{i:04X}  {hexpart:<{width * 3 - 1}}  {text}")
    return "\n".join(lines)
