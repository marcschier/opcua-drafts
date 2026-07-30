# OPC UA Data Channel Throughput — inline framing vs `opc.quic`, with and without a competing Publish load

> **Status — informative companion report.** This document records what a data channel sustains in the reference C# implementation, and what a concurrent Subscription costs it. It is measurement, not normative specification. Nothing here is endorsed by the OPC Foundation.

## 1 Summary

- **`opc.quic` carries roughly twice what inline framing does** — 768 Mbit/s against 390 Mbit/s on the same machine, the same frames and the same application code. This is the one difference in the report large enough to be resolvable well beyond the run-to-run spread. It is what the outer-protocol model buys: the transport multiplexes and flow-controls, so the stack is not building a credit window by hand and not interleaving `STR` chunks with `MSG` chunks in one sequence space.
- **A competing Publish load did not measurably change data channel throughput** on either transport, at 100 monitored items and publishing intervals of 10 ms, 100 ms and 1000 ms. Every loaded case landed inside the baseline's own spread. The medians can be ranked; the ranking is not supported by the data.
- **Neither path starved the other.** The Subscription kept its idle notification rate while the data channel was saturated, and the data channel kept its unloaded throughput while the Subscription ran. This is the property the scheduling obligations of the Part 6 errata §5.7 exist to provide, and it is the result they predict.
- **The Publish rate a single Subscription can offer is bounded by the Client's outstanding-request pipeline, not by the publishing interval.** With one Subscription the Client held only a couple of Publish requests in flight, so notifications arrived at roughly 100/s whether the interval was 10 ms or 100 ms. Shortening the interval changes how much each Publish response carries, not how often the Client asks. Anyone sizing a Server for "Publish plus streaming" should size against that ceiling rather than against `items / interval`.

## 2 Methodology

Measurements come from the worked sample in the reference implementation, `samples/ConsoleDataChannelStreaming`, run in `--mode benchmark`. It stands up a real `StandardServer`, connects a real Client, creates a Session and opens a data channel through `OpenDataChannel`, so the Service dispatch, the Session binding and the parameter negotiation are all exercised rather than only the framing.

One Server, one Session and one data channel serve the whole matrix; only the Subscription changes between cases. Every case therefore runs on the same channel with the same negotiated credit.

### Reproduce

```sh
cd samples/ConsoleDataChannelStreaming
dotnet run -- --transport tcp  --mode benchmark --frames 280000 --size 1200 \
  --monitored-items 100 --repeat 4
dotnet run -- --transport quic --mode benchmark --frames 280000 --size 1200 \
  --monitored-items 100 --repeat 4
```

Environment: .NET 10, single machine, single process, Debug build, Windows, loopback.

### How the runs are ordered

Cases are **round-robined inside each pass** rather than run to completion one after another, and the first pass is discarded. This matters more than it sounds. Run sequentially, a process that keeps warming up over a long matrix hands every later case an advantage the earlier ones never had. An earlier sequential run of this same benchmark produced a clean monotonic curve — 107%, 114%, 117% of baseline — in which throughput appeared to *improve* as the competing load grew. That curve was entirely an artefact of the order.

### How to read the numbers

- **These are loopback figures.** Client and Server are in one process; the numbers are bound by CPU and cryptography, not by a network interface. They compare the cases against each other. They are not a statement about throughput over a real link.
- **What is measured is drain rate.** `DataChannel.Write` enqueues without blocking, so the window runs from the first write to the moment the sink has received the last frame — not the time to hand frames to the queue.
- **`notif/s idle` is the control.** It is the rate the Subscription reaches with the data channel idle. Without it there is no way to distinguish a Publish path being starved by the data channel from one that was never going to run faster, and the two support opposite conclusions.
- **The spread column decides what may be concluded.** Where a loaded case overlaps the baseline's own spread, the difference is smaller than the noise and the benchmark says so rather than leaving a reader to rank four medians.

## 3 Inline framing over `opc.tcp`

280 000 frames of 1200 bytes, 100 monitored items, 4 measured passes after a discarded warm-up.

| Publishing interval | Revised | Items | notif/s idle | notif/s loaded | Mbit/s (median) | Spread | Credit stalls |
|---|--:|--:|--:|--:|--:|---|--:|
| none | — | 0 | — | — | 390.0 | 382.0-397.1 | 0 |
| 10 ms | 10 ms | 100 | 100 | 104 | 401.6 | 388.3-405.1 | 0 |
| 100 ms | 100 ms | 100 | 100 | 106 | 401.5 | 392.7-438.9 | 0 |
| 1000 ms | 1000 ms | 100 | 67 | 78 | 390.0 | 388.1-426.2 | 0 |

**Not resolvable.** Every loaded case overlaps the baseline spread of 382-397 Mbit/s. The correct reading is that a Publish load of this size did not change data channel throughput measurably, not that it improved it by 3%.

The credit-stall counter stayed at zero throughout, which is the expected result: the credit window was never the binding constraint at this frame size and initial credit.

## 4 `opc.quic`

Same parameters.

| Publishing interval | Revised | Items | notif/s idle | notif/s loaded | Mbit/s (median) | Spread |
|---|--:|--:|--:|--:|--:|---|
| none | — | 0 | — | — | 767.8 | 724.6-806.5 |
| 10 ms | 10 ms | 100 | 100 | 111 | 749.0 | 712.4-768.4 |
| 100 ms | 100 ms | 100 | 100 | 113 | 760.8 | 743.8-784.7 |
| 1000 ms | 1000 ms | 100 | 67 | 84 | 750.9 | 746.1-775.1 |

**Not resolvable** against the baseline spread of 725-806 Mbit/s, exactly as over `opc.tcp`.

**Resolvable, and the headline of this report:** `opc.quic` sustains about **1.97×** the inline figure — 767.8 against 390.0 Mbit/s — and the two spreads are nowhere near touching.

> **The credit-stall counter is not meaningful over `opc.quic` in this implementation.** It reported hundreds of thousands of stalls on runs that simultaneously produced the highest throughput measured anywhere in this report. The cause is that the send window is still consulted on a transport where credit is not in force and `CREDIT` frames are neither sent nor expected, so the counter increments without anything actually stalling. The figure is omitted from the table above rather than reproduced, because a reader would reasonably interpret it as congestion. This is an implementation defect in the counter, not a property of the transport, and it does not affect the throughput figures.

## 5 What this does and does not establish

It establishes that the outer-protocol model is worth roughly a factor of two on this implementation, and that a data channel and a Subscription coexist on one SecureChannel without either starving the other at these load levels.

It does not establish where the crossover is. The competing load here — 100 monitored items on one Subscription, delivering about 100 notifications per second — is modest, and it is modest for a structural reason given in §1: one Subscription cannot offer much more, whatever its publishing interval. A Server carrying dozens of Subscriptions, or Clients with deeper Publish pipelines, would present a materially larger Service load than anything measured here, and this report says nothing about that case.

It also says nothing about behaviour over a real network. Every figure is loopback, so bandwidth, latency, loss and the congestion controllers that respond to them are all absent — and those are precisely the conditions under which the delivery modes, the partial reliability and the `opc.quic` datagram path exist to be used.
