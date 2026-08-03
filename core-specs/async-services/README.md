# OPC UA Asynchronous Service Execution

This folder contains the working draft for **OPC UA — Asynchronous Service Execution**: a way for a Server to answer a request later than the Client asked for it, without a ticket, a cookie or a per-specification poll Method.

A Server that cannot produce a response within the time its Client will wait **parks** the request, answers `Bad_RequestNotComplete` with a retry hint, and hands the response to the first `Continue` that arrives once the work has finished. `Continue` is a new Service beside `Cancel` and uses the same key — `RequestHeader.requestHandle` — so the two Services that act on an outstanding request are symmetric: `Cancel` gives it up, `Continue` asks for it.

It answers [Mantis 10606](https://mantis.opcfoundation.org/view.php?id=10606), which asks for *"an async solution for synchronizing such calls in one general matter"* after observing that a Server acting as a gateway cannot answer the certificate push Methods of OPC 10000-12 while the devices behind it are still being reached.

## Contents

- `OPC-UA-Async-Services.md` — **standalone combined spec**: a self-contained read merging the two errata below, plus a worked GDS-to-gateway deployment, the five field scenarios and which of them a deferral actually solves, and a comparison with the mechanisms OPC UA already has. The two errata documents remain the authoritative, insertion-ready proposals.
- `OPC-UA-Part4-Async-Service-Execution.md` — Part 4 errata: the `Continue` Service, the deferral and retry rules, the lifecycle, durable deferral, auditing, five StatusCodes and thirty-eight test assertions.
- `OPC-UA-Part5-Async-Service-Model.md` — Part 5 errata: `AsyncServiceCapabilitiesType`, `AsyncServiceDiagnosticsType`, the DataTypes and the two EventTypes.
- `Opc.Ua.AsyncServices.NodeSet2.xml` — generated NodeSet.
- `Opc.Ua.AsyncServices.NodeIds.csv` — generated NodeIds.
- `tools/build_model.py` — the single source of truth for the model; emits the NodeSet, the CSV and Annex A.
- `tools/model-reference.md` — generated Annex A, embedded verbatim in the Part 5 errata and the combined spec.
- `tools/validate_local.py` — NodeSet, CSV, Annex, specification agreement and determinism gate.

## The shape of it

| | What it is |
|---|---|
| The Service | `Continue(requestHandle)`, in the Session Service Set beside `Cancel`. |
| The answer | The parked Service's own response — a `CallResponse`, a `WriteResponse` — or `Bad_RequestNotComplete` again. |
| The key | `RequestHeader.requestHandle`. No ticket comes back from the Server. |
| The hint | `RetryAfter` in `ResponseHeader.additionalHeader`, with `DefaultRetryAfter` and `MinRetryAfter` readable from the AddressSpace for Clients whose stack drops the header. |
| Giving up | `Cancel(requestHandle)`, which discards the answer and never implies the effect was undone. |
| Being told instead of asking | `DeferredRequestCompletedEventType` on the Server Object, delivered only to the Sessions entitled to collect. |
| Outliving a connection | Optional durable deferral: a later Session of the same user identity collects the response. |
| A Client that knows none of this | Sees a Bad service result, exactly as it sees `Bad_Timeout` today. |

## Regenerate and validate

From the repository root:

```powershell
python core-specs\async-services\tools\build_model.py
python core-specs\async-services\tools\validate_local.py
```

`build_model.py` writes the NodeSet, the CSV and `tools/model-reference.md`, and injects Annex A into the Part 5 errata and the combined spec. It is deterministic and uses no clock or randomness, so regenerating without a source change produces byte-identical output. The validator needs no untracked base data, so it runs in CI through `python core-specs\extras\validate_all.py --self-contained`.

## Provisional identifiers

This is an errata overlay on the **base** OPC UA namespace `http://opcfoundation.org/UA/`, so the NodeSet declares no additional `NamespaceUri`, emits unqualified BrowseNames and plain `i=<n>` NodeIds, and is intended to be merged into the base UA NodeSet rather than loaded beside it.

Draft numeric NodeIds use the provisional `70000+` block (`70000..70099` types, `70100..70199` well-known instances, `70900..70999` EnumStrings, `71000+` members), chosen because `60000`, `62000`, `63000` and `64000` are used by the companion-namespace drafts in this repository and `65000..69999` by the Data Channels draft. The five new StatusCodes and the proposed `5.7.6` clause number are equally provisional. Final assignments are made by the OPC Foundation.

`Bad_RequestNotComplete` is **not** provisional: it is the existing `0x81130000`, *"The request has not been processed by the server yet"*, already used by the pull-management `FinishRequest` Method of OPC 10000-12. Generalizing the code the pattern already uses seemed better than adding a synonym beside it.
