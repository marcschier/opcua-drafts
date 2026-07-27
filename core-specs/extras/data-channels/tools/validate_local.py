#!/usr/bin/env python3
"""
Local acceptance gate for the OPC UA Data Channels wire tooling.

Checks, in order:
  1. Round-trip - every published vector decodes back to the frame it was encoded from,
     in both framing modes and with and without a message footer.
  2. Rejection - every rule the Part 6 errata states as a "shall" for receivers is
     actually enforced by the reference decoder. A specification whose reference
     implementation accepts what the prose forbids is worse than no reference.
  3. Vector drift - the committed `.hex.txt` files and `index.md` match what the
     generator produces now.
  4. Annex drift - the annex embedded in both specification documents matches the
     generated rendering, and every annotation covers its frame exactly once.
  5. Sender obligations - the scheduler demo actually exhibits flow control,
     RPC precedence and deadline expiry with gap notification.

Runs with no untracked base data, so it belongs to the CI self-contained set.

Usage (from repo root):
    python core-specs/extras/data-channels/tools/validate_local.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import frame_codec as fc  # noqa: E402
import gen_vectors  # noqa: E402
import gen_wire_annex  # noqa: E402
import scheduler_demo  # noqa: E402

EXAMPLES = os.path.abspath(os.path.join(HERE, "..", "examples"))
SPEC_DIR = gen_wire_annex.SPEC_DIR

errors: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def expect_reject(reason: str, fn) -> None:
    """Assert the reference decoder rejects something the errata says it must."""
    try:
        fn()
    except fc.FrameError:
        return
    except Exception as exc:  # noqa: BLE001
        err(f"rejection check '{reason}' raised {type(exc).__name__} instead of FrameError")
        return
    err(f"rejection check '{reason}': the decoder accepted a frame the errata forbids")


# --- 1. Round-trip ----------------------------------------------------------
vs = gen_vectors.vectors()
for v in vs:
    footer_size = len(v["footer"])
    try:
        back = fc.decode(v["bytes"], v["mode"], footer_size=footer_size)
    except fc.FrameError as exc:
        err(f"{v['name']}: published vector does not decode ({exc})")
        continue
    original = v["frame"]
    for attr in ("channel_id", "frame_type", "flags", "frame_sequence_number",
                 "payload", "deadline", "extras", "secure_channel_id"):
        if getattr(back, attr) != getattr(original, attr):
            err(f"{v['name']}: {attr} does not round-trip "
                f"({getattr(back, attr)!r} != {getattr(original, attr)!r})")
    if v["mode"] == fc.INLINE:
        for attr in ("token_id", "sequence_number"):
            if getattr(back, attr) != getattr(original, attr):
                err(f"{v['name']}: {attr} does not round-trip")
    reencoded = fc.encode(back, v["mode"], footer=v["footer"])
    if reencoded != v["bytes"]:
        err(f"{v['name']}: re-encoding the decoded frame produced different bytes")

# Every frame type must round-trip, not only the ones that happen to be published.
covered = {v["frame"].frame_type for v in vs}
missing = set(fc.FRAME_TYPE_NAMES) - covered
if missing:
    err("frame types with no published vector: "
        + ", ".join(sorted(fc.FRAME_TYPE_NAMES[t] for t in missing)))

# Both framing modes must be exercised.
for mode in (fc.INLINE, fc.QUIC):
    if not any(v["mode"] == mode for v in vs):
        err(f"no published vector uses {mode} framing")

# --- 2. Receiver rejection rules -------------------------------------------
good = fc.encode(
    fc.Frame(channel_id=1, frame_type=fc.FT_DATA, frame_sequence_number=1, payload=b"\x01"),
    fc.INLINE)

# The credit-cost probes below use a valid FrameSequenceNumber for the same reason.
expect_reject("wrong MessageType", lambda: fc.decode(b"MSG" + good[3:], fc.INLINE))
expect_reject("IsFinal 'C' (a frame is never chunked)",
              lambda: fc.decode(good[:3] + b"C" + good[4:], fc.INLINE))
expect_reject("MessageSize disagreeing with the received length",
              lambda: fc.decode(good + b"\x00", fc.INLINE))
expect_reject("non-zero RequestId",
              lambda: fc.decode(good[:20] + b"\x01\x00\x00\x00" + good[24:], fc.INLINE))
expect_reject("non-zero Reserved",
              lambda: fc.decode(good[:30] + b"\x01\x00" + good[32:], fc.INLINE))
expect_reject("reserved flag bits set",
              lambda: fc.decode(good[:29] + bytes([fc.FLAG_RESERVED_MASK]) + good[30:], fc.INLINE))
expect_reject("unknown frame type",
              lambda: fc.decode(good[:28] + b"\x7F" + good[29:], fc.INLINE))
expect_reject("truncated frame", lambda: fc.decode(good[:20], fc.INLINE))
expect_reject("FrameSequenceNumber 0 on decode",
              lambda: fc.decode(good[:32] + b"\x00\x00\x00\x00" + good[36:], fc.INLINE))
expect_reject("FrameSequenceNumber 0 on encode", lambda: fc.encode(
    fc.Frame(channel_id=1, frame_type=fc.FT_DATA, frame_sequence_number=0), fc.INLINE))
expect_reject("payload on a non-DATA frame", lambda: fc.encode(
    fc.Frame(channel_id=1, frame_type=fc.FT_END, frame_sequence_number=1, payload=b"x"),
    fc.INLINE))
expect_reject("DATA on the connection control channel", lambda: fc.encode(
    fc.Frame(channel_id=fc.CONNECTION_CHANNEL_ID, frame_type=fc.FT_DATA,
             frame_sequence_number=1, payload=b"x"), fc.INLINE))
expect_reject("CREDIT frame without its fields", lambda: fc.encode(
    fc.Frame(channel_id=1, frame_type=fc.FT_CREDIT, frame_sequence_number=1), fc.INLINE))
expect_reject("unknown framing mode", lambda: fc.encode(
    fc.Frame(channel_id=1, frame_type=fc.FT_DATA, frame_sequence_number=1), "sctp"))
expect_reject("UA-SC footer under QUIC framing", lambda: fc.encode(
    fc.Frame(channel_id=1, frame_type=fc.FT_DATA, frame_sequence_number=1), fc.QUIC,
    footer=b"\x00"))

# Self-consistent truncation: MessageSize is patched to the truncated length, so the frame
# is a structurally valid MessageChunk and only the frame-type-dependent length check can
# catch it. These are the frames a hostile peer would actually send.
def _truncate(frame, mode, keep):
    raw = bytearray(fc.encode(frame, mode))[:keep]
    raw[4:8] = len(raw).to_bytes(4, "little")
    return bytes(raw)


for name, frame, keep in (
    ("CREDIT missing its second field",
     fc.Frame(channel_id=1, frame_type=fc.FT_CREDIT, frame_sequence_number=1,
              extras={"ChannelCredit": 1, "ConnectionCredit": 2}), 40),
    ("GAP missing its second field",
     fc.Frame(channel_id=1, frame_type=fc.FT_GAP, frame_sequence_number=1,
              extras={"FirstDiscarded": 1, "LastDiscarded": 2}), 40),
    ("RESET with a half StatusCode",
     fc.Frame(channel_id=1, frame_type=fc.FT_RESET, frame_sequence_number=1,
              extras={"StatusCode": 1}), 38),
    ("PING with a half Timestamp",
     fc.Frame(channel_id=fc.CONNECTION_CHANNEL_ID, frame_type=fc.FT_PING,
              frame_sequence_number=1, extras={"Timestamp": 1}), 40),
    ("DeadlinePresent with no Deadline",
     fc.Frame(channel_id=1, frame_type=fc.FT_DATA, frame_sequence_number=1,
              deadline=1), 36),
):
    expect_reject(name, lambda f=frame, k=keep: fc.decode(_truncate(f, fc.INLINE, k), fc.INLINE))

# A footer that overlaps the frame's own extra fields must be rejected, not silently
# absorbed: annotate() already refuses these bytes, and the two halves of the reference
# codec must agree about the same frame.
_credit = fc.encode(fc.Frame(channel_id=1, frame_type=fc.FT_CREDIT, frame_sequence_number=1,
                             extras={"ChannelCredit": 0, "ConnectionCredit": 123}), fc.INLINE)
for fsize in (4, 8):
    expect_reject(f"message footer of {fsize} bytes overlapping the extra fields",
                  lambda s=fsize: fc.decode(_credit, fc.INLINE, footer_size=s))

# Control frames are exempt from flow control; DATA is not.
if fc.Frame(channel_id=1, frame_type=fc.FT_DATA, payload=b"1234").credit_cost() != 4:
    err("a DATA frame must consume credit equal to its payload length")
for ft in fc.CREDIT_EXEMPT:
    if fc.Frame(channel_id=1, frame_type=ft).credit_cost() != 0:
        err(f"{fc.FRAME_TYPE_NAMES[ft]} must be exempt from flow control")

# The documented overhead figures must match the codec.
if fc.max_payload(fc.INLINE, 8192) != 8192 - 36:
    err("inline fixed overhead is not the 36 bytes the errata states")
if fc.max_payload(fc.QUIC, 8192) != 8192 - 24:
    err("QUIC fixed overhead is not the 24 bytes the errata states")
if fc.max_payload(fc.INLINE, 8192, deadline=True) != 8192 - 36 - 8:
    err("the optional Deadline field does not cost the 8 bytes the errata states")

# --- 3. Vector drift --------------------------------------------------------
for v in vs:
    path = os.path.join(EXAMPLES, f"{v['name']}.hex.txt")
    if not os.path.exists(path):
        err(f"missing published vector {v['name']}.hex.txt")
        continue
    with open(path, encoding="utf-8") as f:
        if f.read() != fc.hexdump(v["bytes"]) + "\n":
            err(f"{v['name']}.hex.txt is stale; run gen_vectors.py")
published = {n[:-8] for n in os.listdir(EXAMPLES) if n.endswith(".hex.txt")}
extra = published - {v["name"] for v in vs}
if extra:
    err("orphaned vector files: " + ", ".join(sorted(extra)))
if not os.path.exists(os.path.join(EXAMPLES, "index.md")):
    err("examples/index.md is missing")

# --- 4. Annex drift and annotation contiguity -------------------------------
for v in vs:
    spans = fc.annotate(v["bytes"], v["mode"], footer_size=len(v["footer"]))
    try:
        fc.check_contiguous(spans, len(v["bytes"]))
    except fc.FrameError as exc:
        err(f"{v['name']}: {exc}")

rendered = gen_wire_annex.generate()
sidecar = os.path.join(HERE, "annex-wire-layouts.md")
if not os.path.exists(sidecar):
    err("annex-wire-layouts.md is missing; run gen_wire_annex.py")
else:
    with open(sidecar, encoding="utf-8") as f:
        if f.read() != rendered:
            err("annex-wire-layouts.md is stale; run gen_wire_annex.py")

for name in gen_wire_annex.DOCS:
    path = os.path.join(SPEC_DIR, name)
    if not os.path.exists(path):
        err(f"{name} is missing")
        continue
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if gen_wire_annex.BEGIN not in text or gen_wire_annex.END not in text:
        err(f"{name}: wire-layouts markers are missing")
        continue
    start = text.index(gen_wire_annex.BEGIN) + len(gen_wire_annex.BEGIN)
    embedded = text[start:text.index(gen_wire_annex.END)]
    if embedded.strip() != rendered.strip():
        err(f"{name}: the embedded Annex B differs from the generated rendering")

# --- 5. Sender obligations --------------------------------------------------
sim = scheduler_demo.simulate()
if sim["rpc_sent"] != ["Publish#0", "Publish#1", "Publish#2"]:
    err(f"RPC traffic was starved or reordered: {sim['rpc_sent']}")
if not sim["video_discarded"]:
    err("the scenario did not exercise deadline expiry")
if not sim["gaps"]:
    err("frames were discarded without a GAP notification")

# Part 6 §5.10: a GAP names one contiguous inclusive run, and shall not name a frame the
# sender may still transmit. A non-contiguous discard set must therefore produce one GAP
# per run -- widening to first..last would declare a surviving frame lost and then send it.
expected_runs = scheduler_demo._runs(sim["video_discarded"])
actual_runs = [(g[2], g[3]) for g in sim["gaps"]]
if actual_runs != expected_runs:
    err(f"GAP runs {actual_runs} do not match the contiguous runs of the discarded "
        f"frames {sim['video_discarded']} (expected {expected_runs})")
if len(expected_runs) < 2:
    err("the scenario did not exercise a non-contiguous discard set, so the per-run "
        "GAP rule of §5.10 is untested")
named = {n for first, last in actual_runs for n in range(first, last + 1)}
transmitted = {t[4] for t in sim["sends"] if t[1] == 1 and t[2] == "DATA"}
if named & set(sim["video_discarded"]) != named:
    err(f"a GAP named a FrameSequenceNumber that was not discarded: "
        f"{named - set(sim['video_discarded'])}")
if named & transmitted:
    err(f"a GAP named a frame that was subsequently transmitted: {named & transmitted}")

if sim["video_stalls"] == 0 or sim["bulk_stalls"] == 0:
    err("the scenario did not exercise credit-based backpressure on both channels")
if sim["remaining"] != {1: 0, 2: 0}:
    err(f"the scenario did not drain: {sim['remaining']}")

# Obligation 2 is testable directly: while RPC is pending, no two data frames may be
# sent back to back, because an RPC chunk goes out between them.
pending = len(sim["rpc_sent"])
consecutive = 0
for kind, channel, _label, _cost, _fsn in sim["sends"]:
    if channel is None:
        pending -= 1
        consecutive = 0
        continue
    if pending <= 0:
        break
    consecutive += 1
    if consecutive > 1:
        err("two data frames were sent back to back while Service traffic was pending")
        break

# --- Report -----------------------------------------------------------------
print(f"vectors: {len(vs)}   frame types covered: {len(covered)}/{len(fc.FRAME_TYPE_NAMES)}   "
      f"documents checked: {len(gen_wire_annex.DOCS)}")
print(f"ERRORS: {len(errors)}")
for e in errors[:50]:
    print("  ERR", e)
if errors:
    sys.exit(1)
print("data-channels wire tooling OK")
