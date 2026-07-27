#!/usr/bin/env python3
"""
Generate the deterministic OPC UA Data Channels wire test vectors.

Writes one `.hex.txt` per vector into `core-specs/extras/data-channels/examples/`,
plus an `index.md` listing them. Every input is fixed in this file - no clock, no
randomness - so regenerating without a source change produces byte-identical output
and the determinism check stays green.

The same vector list drives `gen_wire_annex.py`, so the byte layouts printed in the
Part 6 errata and the bytes shipped here are provably the same bytes.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from frame_codec import (  # noqa: E402
    CONNECTION_CHANNEL_ID, FLAG_DROPPABLE, FLAG_MARKER, FLAG_MESSAGE_END,
    FLAG_MESSAGE_START, FT_CREDIT, FT_DATA, FT_END, FT_GAP, FT_PING, FT_PONG, FT_RESET,
    INLINE, QUIC, Frame, encode, hexdump,
)

EXAMPLES = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples"))

# A fixed SecureChannel context shared by the inline vectors.
SCID = 0x0000A17C
TOKEN = 0x00000007

# Bad_DataChannelClosed, from the provisional StatusCode block proposed by the Part 4
# errata. The numeric value is provisional exactly as the NodeIds are.
BAD_DATA_CHANNEL_CLOSED = 0x81B10000

# A fixed 100 ns tick value, so PING/PONG vectors are reproducible.
FIXED_TICKS = 133_000_000_000_000_000


def _v(name, frame, mode, description, footer=b""):
    return {
        "name": name,
        "frame": frame,
        "mode": mode,
        "description": description,
        "footer": footer,
        "bytes": encode(frame, mode, footer=footer),
    }


def vectors() -> list[dict]:
    """The canonical vector list. Order is significant: it is the order of the annex."""
    out = []

    out.append(_v(
        "inline_data_first",
        Frame(channel_id=1, frame_type=FT_DATA,
              flags=FLAG_MESSAGE_START | FLAG_MARKER, frame_sequence_number=1,
              payload=bytes(range(0x10)), secure_channel_id=SCID, token_id=TOKEN,
              sequence_number=51),
        INLINE,
        "The first frame of a logical application message on channel 1, marked as a "
        "synchronization point. This is the layout an implementer needs to get right; "
        "every other inline frame is this one with different stream header contents."))

    out.append(_v(
        "inline_data_final",
        Frame(channel_id=1, frame_type=FT_DATA, flags=FLAG_MESSAGE_END,
              frame_sequence_number=2, payload=b"\xAA\xBB\xCC\xDD",
              secure_channel_id=SCID, token_id=TOKEN, sequence_number=52),
        INLINE,
        "The closing frame of the same logical message. MessageEnd is what delimits an "
        "application message; the frame itself is still a single MessageChunk."))

    out.append(_v(
        "inline_data_droppable",
        Frame(channel_id=2, frame_type=FT_DATA,
              flags=FLAG_MESSAGE_START | FLAG_MESSAGE_END | FLAG_DROPPABLE,
              frame_sequence_number=97, payload=b"\x01\x02\x03\x04\x05\x06\x07\x08",
              deadline=FIXED_TICKS, secure_channel_id=SCID, token_id=TOKEN,
              sequence_number=53),
        INLINE,
        "A self-contained media frame that the sender may discard if it is still queued "
        "at the deadline. The Deadline field is present only because the DeadlinePresent "
        "flag is set, so a reliable channel never pays its eight bytes."))

    out.append(_v(
        "inline_credit_channel",
        Frame(channel_id=2, frame_type=FT_CREDIT, frame_sequence_number=98,
              extras={"ChannelCredit": 65536, "ConnectionCredit": 0},
              secure_channel_id=SCID, token_id=TOKEN, sequence_number=54),
        INLINE,
        "A window update for channel 2 alone. CREDIT frames are exempt from flow "
        "control; a creditable CREDIT frame would deadlock a stalled channel."))

    out.append(_v(
        "inline_credit_connection",
        Frame(channel_id=CONNECTION_CHANNEL_ID, frame_type=FT_CREDIT,
              frame_sequence_number=11,
              extras={"ChannelCredit": 0, "ConnectionCredit": 262144},
              secure_channel_id=SCID, token_id=TOKEN, sequence_number=55),
        INLINE,
        "A connection-level window update on the reserved control channel 0, which "
        "governs the total across every data channel of the SecureChannel. Channel 0 "
        "counts its own FrameSequenceNumber sequence like any other channel."))

    out.append(_v(
        "inline_gap",
        Frame(channel_id=2, frame_type=FT_GAP, frame_sequence_number=103,
              extras={"FirstDiscarded": 99, "LastDiscarded": 102},
              secure_channel_id=SCID, token_id=TOKEN, sequence_number=56),
        INLINE,
        "The sender discarded frames 99 through 102 because their deadlines passed. "
        "Without this notification the receiver could not tell loss from a stall, and a "
        "media decoder could not decide to conceal."))

    out.append(_v(
        "inline_reset",
        Frame(channel_id=2, frame_type=FT_RESET, frame_sequence_number=104,
              extras={"StatusCode": BAD_DATA_CHANNEL_CLOSED},
              secure_channel_id=SCID, token_id=TOKEN, sequence_number=57),
        INLINE,
        "Abort one data channel and leave every other channel and the SecureChannel "
        "itself running. This is the difference between a data channel failing and a "
        "connection failing."))

    out.append(_v(
        "inline_end",
        Frame(channel_id=1, frame_type=FT_END, frame_sequence_number=3,
              secure_channel_id=SCID, token_id=TOKEN, sequence_number=58),
        INLINE,
        "Orderly half-close: this direction of channel 1 will send nothing further, "
        "while the opposite direction of a Bidirectional channel keeps flowing."))

    out.append(_v(
        "inline_ping",
        Frame(channel_id=CONNECTION_CHANNEL_ID, frame_type=FT_PING,
              frame_sequence_number=12, extras={"Timestamp": FIXED_TICKS},
              secure_channel_id=SCID, token_id=TOKEN, sequence_number=59),
        INLINE,
        "A round trip probe on the control channel. The measured round trip time is "
        "what a sender paces against and what a receiver sizes its jitter buffer from."))

    out.append(_v(
        "inline_pong",
        Frame(channel_id=CONNECTION_CHANNEL_ID, frame_type=FT_PONG,
              frame_sequence_number=13, extras={"Timestamp": FIXED_TICKS},
              secure_channel_id=SCID, token_id=TOKEN, sequence_number=60),
        INLINE,
        "The echo. The Timestamp is copied verbatim from the PING, so the sender needs "
        "to keep no state to compute the round trip."))

    out.append(_v(
        "inline_data_signed",
        Frame(channel_id=1, frame_type=FT_DATA,
              flags=FLAG_MESSAGE_START | FLAG_MESSAGE_END, frame_sequence_number=4,
              payload=b"\x10\x11\x12\x13", secure_channel_id=SCID, token_id=TOKEN,
              sequence_number=61),
        INLINE,
        "The same inline frame under a signing security policy, showing where the Part 6 "
        "message footer lands. The footer bytes here are placeholder filler: they are "
        "produced by the security policy, not by this specification.",
        footer=b"\x00" + b"\x5A" * 32))

    out.append(_v(
        "quic_data_stream",
        Frame(channel_id=1, frame_type=FT_DATA,
              flags=FLAG_MESSAGE_START | FLAG_MESSAGE_END | FLAG_MARKER,
              frame_sequence_number=1, payload=bytes(range(0x10)),
              secure_channel_id=SCID),
        QUIC,
        "The same DATA frame carried on a QUIC stream. TLS 1.3 already authenticates and "
        "encrypts it and QUIC already orders it, so the security header, the sequence "
        "header and the footer are gone and the frame is twelve bytes shorter."))

    out.append(_v(
        "quic_datagram_unreliable",
        Frame(channel_id=3, frame_type=FT_DATA,
              flags=FLAG_MESSAGE_START | FLAG_MESSAGE_END | FLAG_DROPPABLE,
              frame_sequence_number=4096, payload=b"\xF0\xF1\xF2\xF3\xF4\xF5",
              secure_channel_id=SCID),
        QUIC,
        "An Unreliable frame in a QUIC DATAGRAM. This is the only place in the "
        "specification where data is genuinely lost in flight rather than discarded at "
        "the sender, which is why FrameSequenceNumber is the receiver's own gap detector."))

    return out


def main() -> int:
    os.makedirs(EXAMPLES, exist_ok=True)
    vs = vectors()
    lines = ["# OPC UA Data Channels wire vectors", "",
             "Generated by `core-specs/extras/data-channels/tools/gen_vectors.py`. Each "
             "`.hex.txt` is one complete data channel frame as it appears on the wire, "
             "annotated byte by byte in Annex B of "
             "[the Part 6 errata](../../../data-channels/OPC-UA-Part6-Data-Channel-Transport.md). "
             "Do not edit by hand.", ""]
    for v in vs:
        path = os.path.join(EXAMPLES, f"{v['name']}.hex.txt")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(hexdump(v["bytes"]) + "\n")
        lines.append(f"- `{v['name']}.hex.txt` — {v['mode']} framing, "
                     f"{v['frame'].type_name} frame, {len(v['bytes'])} bytes")
    lines.append("")
    with open(os.path.join(EXAMPLES, "index.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(vs)} vectors to {EXAMPLES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
