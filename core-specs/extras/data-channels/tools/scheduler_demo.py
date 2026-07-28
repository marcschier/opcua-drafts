#!/usr/bin/env python3
"""
Executable demonstration of the OPC UA Data Channels sender obligations.

The Part 6 errata states three requirements that are easy to write and easy to get
wrong. This module implements them so they can be exercised rather than asserted:

  1. Flow control - a sender shall not transmit a DATA frame whose payload exceeds
     the peer's remaining channel credit or the remaining connection credit. Control
     frames are exempt, otherwise a stalled channel could never be reset or probed.

  2. RPC precedence - Service traffic (MSG chunks) shall never be delayed by more
     than the transmission of one maximum-size data channel frame. This is what keeps
     a video stream from stalling the Publish response path.

  3. Deadline expiry - a droppable frame still queued when its deadline passes is
     discarded rather than sent, and the discarded FrameSequenceNumber range is
     reported to the receiver in a GAP frame. This is the only form of "unreliable"
     a reliable transport can offer, and it is applied at the sender.

Run directly to print a trace. `simulate()` returns the trace for the validator.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from frame_codec import (  # noqa: E402
    CONNECTION_CHANNEL_ID, FLAG_DEADLINE, FLAG_DROPPABLE, FT_DATA, FT_GAP, Frame,
)

MAX_PRIORITY = 7


def _runs(numbers: list[int]) -> list[tuple[int, int]]:
    """Split an ascending list of FrameSequenceNumbers into contiguous inclusive runs."""
    out: list[tuple[int, int]] = []
    for n in sorted(numbers):
        if out and n == out[-1][1] + 1:
            out[-1] = (out[-1][0], n)
        else:
            out.append((n, n))
    return out


@dataclass
class Queued:
    frame: Frame
    deadline: int | None = None


@dataclass
class Channel:
    channel_id: int
    priority: int = 0
    credit: int = 0
    queue: list[Queued] = field(default_factory=list)
    next_fsn: int = 1
    deficit: int = 0
    discarded: list[int] = field(default_factory=list)
    stalls: int = 0

    def enqueue(self, payload: bytes, deadline: int | None = None) -> Frame:
        flags = 0
        if deadline is not None:
            flags |= FLAG_DROPPABLE
        frame = Frame(channel_id=self.channel_id, frame_type=FT_DATA, flags=flags,
                      frame_sequence_number=self.next_fsn, payload=payload,
                      deadline=deadline)
        self.next_fsn += 1
        self.queue.append(Queued(frame, deadline))
        return frame


class Sender:
    """A single-connection sender applying the three obligations above."""

    def __init__(self, connection_credit: int, max_frame_size: int):
        self.connection_credit = connection_credit
        self.max_frame_size = max_frame_size
        self.channels: dict[int, Channel] = {}
        self.rpc_queue: list[str] = []
        self.trace: list[tuple] = []
        self.clock = 0

    def add_channel(self, channel_id: int, priority: int, credit: int) -> Channel:
        if channel_id == CONNECTION_CHANNEL_ID:
            raise ValueError("ChannelId 0 is the connection control channel")
        if not 0 <= priority <= MAX_PRIORITY:
            raise ValueError("priority is 0..7")
        ch = Channel(channel_id, priority, credit)
        self.channels[channel_id] = ch
        return ch

    def enqueue_rpc(self, label: str) -> None:
        self.rpc_queue.append(label)

    # -- obligation 3 -------------------------------------------------------
    def _expire(self, ch: Channel) -> bool:
        kept, dropped = [], []
        for q in ch.queue:
            if q.deadline is not None and q.deadline <= self.clock:
                dropped.append(q.frame.frame_sequence_number)
            else:
                kept.append(q)
        if not dropped:
            return False
        ch.queue = kept
        ch.discarded.extend(dropped)
        # Per-frame deadlines make a NON-CONTIGUOUS discard set the normal case: frames 1
        # and 3 expire while frame 2, enqueued with a longer deadline, is still live. A GAP
        # names one contiguous inclusive run, and shall not name a frame the sender may
        # still transmit, so the discarded set is split into runs and one GAP is emitted
        # per run. Widening to first..last would declare frame 2 lost and then deliver it.
        for first, last in _runs(dropped):
            gap = Frame(channel_id=ch.channel_id, frame_type=FT_GAP,
                        frame_sequence_number=ch.next_fsn,
                        extras={"FirstDiscarded": first, "LastDiscarded": last})
            ch.next_fsn += 1
            self.trace.append(("gap", ch.channel_id, first, last))
            self.trace.append(("send", ch.channel_id, gap.type_name, 0, gap.frame_sequence_number))
        return True

    # -- obligations 1 and 2 ------------------------------------------------
    def _send_one_rpc(self) -> bool:
        if not self.rpc_queue:
            return False
        self.trace.append(("send", None, "MSG", self.rpc_queue.pop(0), None))
        return True

    def _ready(self, ch: Channel) -> Queued | None:
        if not ch.queue:
            return None
        q = ch.queue[0]
        cost = q.frame.credit_cost()
        if cost > ch.credit or cost > self.connection_credit:
            ch.stalls += 1
            self.trace.append(("stall", ch.channel_id, ch.credit, self.connection_credit))
            return None
        return q

    def step(self) -> bool:
        """One scheduling round. Returns False when nothing remains to send."""
        self.clock += 1
        progressed = False
        for ch in self.channels.values():
            progressed |= self._expire(ch)

        # Obligation 2: an RPC chunk goes out before any data frame, and again after
        # every single data frame, so Service traffic is delayed by at most the
        # transmission of one data channel frame.
        progressed |= self._send_one_rpc()

        # Obligation 1 plus priority-weighted deficit round robin over the channels.
        for ch in sorted(self.channels.values(),
                         key=lambda c: (-c.priority, c.channel_id)):
            ch.deficit += (ch.priority + 1) * self.max_frame_size
            while True:
                q = self._ready(ch)
                if q is None:
                    break
                cost = q.frame.credit_cost()
                if cost > ch.deficit:
                    break
                ch.queue.pop(0)
                ch.deficit -= cost
                ch.credit -= cost
                self.connection_credit -= cost
                self.trace.append(("send", ch.channel_id, q.frame.type_name, cost,
                                   q.frame.frame_sequence_number))
                progressed = True
                self._send_one_rpc()
            if not ch.queue:
                ch.deficit = 0
        return progressed

    def run(self, max_rounds: int = 100) -> list[tuple]:
        rounds = 0
        while rounds < max_rounds and self.step():
            rounds += 1
        return self.trace

    def grant(self, channel_id: int, channel_credit: int, connection_credit: int) -> None:
        self.channels[channel_id].credit += channel_credit
        self.connection_credit += connection_credit
        self.trace.append(("credit", channel_id, channel_credit, connection_credit))


def simulate() -> dict:
    """A deterministic scenario exercising all three obligations at once: a
    high-priority video channel whose queued frames outlive their deadline while it is
    credit-stalled, a low-priority bulk channel competing for the shared connection
    window, and RPC traffic that must not be starved by either."""
    s = Sender(connection_credit=3072, max_frame_size=1024)
    video = s.add_channel(1, priority=6, credit=1024)
    bulk = s.add_channel(2, priority=1, credit=8192)

    for i in range(6):
        # The first two frames fit the initial credit and go out immediately. Of the rest,
        # which queue behind the credit stall, frames 3, 4 and 6 carry a short deadline and
        # frame 5 a long one -- so the discarded set is NON-CONTIGUOUS (3, 4 and 6) and must
        # produce two GAP frames rather than one range that would falsely declare frame 5
        # lost and then transmit it.
        video.enqueue(b"V" * 512, deadline=None if i < 2 else (50 if i == 4 else 3))
    for _ in range(4):
        bulk.enqueue(b"B" * 1024)
    for i in range(3):
        s.enqueue_rpc(f"Publish#{i}")

    s.run()
    s.grant(1, 4096, 4096)
    s.grant(2, 4096, 4096)
    s.run()

    sends = [t for t in s.trace if t[0] == "send"]
    return {
        "trace": s.trace,
        "rpc_sent": [t[3] for t in sends if t[1] is None],
        "video_discarded": list(video.discarded),
        "bulk_stalls": bulk.stalls,
        "video_stalls": video.stalls,
        "gaps": [t for t in s.trace if t[0] == "gap"],
        "remaining": {1: len(video.queue), 2: len(bulk.queue)},
        "sends": sends,
    }


if __name__ == "__main__":
    r = simulate()
    for t in r["trace"]:
        print("  ".join(str(x) for x in t))
    print()
    print(f"RPC delivered      : {r['rpc_sent']}")
    print(f"Video frames dropped: {r['video_discarded']} (deadline passed in the send queue)")
    print(f"Gap notifications   : {r['gaps']}")
    print(f"Credit stalls       : video={r['video_stalls']} bulk={r['bulk_stalls']}")
    print(f"Still queued        : {r['remaining']}")
