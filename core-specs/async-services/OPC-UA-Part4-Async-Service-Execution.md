# OPC UA Part 4 — Asynchronous Service Execution

**Working draft for submission to the OPC Foundation Working Group**
**Proposed addition to:** OPC 10000-4 Services v1.05.07
**Namespace:** `http://opcfoundation.org/UA/` (base OPC UA namespace)
**Version:** 0.1.0 · **Date:** 2026-08-03

> **Status — working draft.** This document proposes one Service — `Continue` — and the rules that let a Server answer any request later than the Client asked for it: when a Server may park a request, how it says so, how a Client collects the parked response, how it abandons one, and what happens when the Session that issued the request goes away. The Nodes a Client reads to discover all of this, and the Events that report it, are in the [Part 5 errata](OPC-UA-Part5-Async-Service-Model.md). Nothing here is normative or endorsed by the OPC Foundation.

---

## 1 Scope

This specification defines the `Continue` Service and the **deferral** mechanism it completes: a Server that cannot produce a response within the time the Client is willing to wait parks the request, answers `Bad_RequestNotComplete` with a cooperative retry hint, and hands the response to the first `Continue` that arrives after the work finishes.

It defines which Services may be deferred, how a parked request is identified, how long a Server holds a parked response, how a Client abandons one, what a Server does when the Session that issued a request closes, and how all of that is audited.

It does not define the Nodes through which a Client discovers a Server's deferral limits or the Events that report completion, which are in the Part 5 errata. It defines no Service-specific behaviour: what a deferred `Call` or a deferred `Write` actually does while it is parked is the business of the Service being deferred, not of this mechanism.

## 2 Normative references

- [OPC 10000-2](https://reference.opcfoundation.org/specs/OPC-10000-2/) — Security Model.
- [OPC 10000-3](https://reference.opcfoundation.org/specs/OPC-10000-3/) — Address Space Model.
- [OPC 10000-4 v1.05.07](https://reference.opcfoundation.org/specs/OPC-10000-4/) — Services.
- [OPC 10000-5](https://reference.opcfoundation.org/specs/OPC-10000-5/) — Information Model.
- [OPC 10000-6](https://reference.opcfoundation.org/specs/OPC-10000-6/) — Mappings.
- [OPC 10000-12](https://reference.opcfoundation.org/specs/OPC-10000-12/) — Discovery and Global Services.
- [OPC 10000-18](https://reference.opcfoundation.org/specs/OPC-10000-18/) — Role-Based Security.
- [OPC UA Part 5 — Asynchronous Service Model](OPC-UA-Part5-Async-Service-Model.md) — the companion information model errata.

## 3 Terms, definitions and abbreviations

| Term | Definition |
|---|---|
| Deferral | A Server's decision to answer a request later than the request itself, by parking it. |
| Parked request | A request the Server has accepted and is still working on, or has finished and is holding an answer for. |
| Parked response | The response of a parked request, held by the Server until a Client collects it, the Client abandons it, or it expires. |
| Issuing Session | The Session on which the parked request arrived. |
| Durable deferral | A deferral whose parked response outlives its issuing Session and can be collected by a later Session of the same user identity. |
| Deferrable Service | A Service the Server is willing to defer, as listed in `AsyncServiceCapabilities.DeferrableServices`. |

Key words **shall**, **should**, **may** and **shall not** are to be interpreted as in the ISO/IEC directives.

## 4 Overview

### 4.1 The problem

A Server that is the front of something else cannot answer within the time its Client will wait. A gateway asked to distribute a TrustList to the devices behind it, an aggregating Server asked to write a value that lives in an underlying Server, a Server asked to run a Method that turns a machine: in every case the work outlasts `RequestHeader.timeoutHint`, and OPC UA has nothing to say about it. The Client gets `Bad_Timeout` and cannot tell a Server that failed from a Server that is still working, and cannot retry without risking the effect a second time.

The certificate push Methods of OPC 10000-12 show the shape at full size. `TrustList.CloseAndUpdate`, `UpdateCertificate`, `CreateSigningRequest` and `ApplyChanges` are single Method calls on the gateway that become one exchange per device behind it. A device may answer promptly, answer slowly, be unreachable for a moment, be unreachable for good, or have been replaced since the last time anyone looked — and the Method has to return one result while some of those are still unknown. The transaction model of OPC 10000-12 §7.10.2 sequences the changes and defers their *effect* until `ApplyChanges`, which is real progress, but `ApplyChanges` itself still has to answer synchronously.

### 4.2 What OPC UA has today, and why none of it is this

**`Good_CompletesAsynchronously`** announces that processing will finish later. It provides no way to learn the outcome, so it tells a Client to stop waiting without telling it what to do instead.

**Ticket Methods.** OPC 10000-12 pull management already solves this once, privately: `StartSigningRequest` returns a `requestId`, `FinishRequest` polls it, and `Bad_RequestNotComplete` means *not yet*. It works, and it is the model this specification generalizes — but it is a pattern rebuilt by hand in every specification that needs it, with its own identifier, its own poll Method, its own lifetime rules and its own failure modes, and it is available only where someone thought to add it. It cannot be applied to a `Write`.

**`Publish`.** A long poll: the Client leaves requests outstanding and the Server answers when it has something. It solves a different problem — a stream of unsolicited notifications — and it works by keeping requests in flight, which is exactly what a Client cannot afford to do for an operation that takes an hour.

**Raising `timeoutHint`.** A Client that waits an hour holds a socket, a thread and a Session for an hour, learns nothing while it waits, and loses everything if the connection blinks. The whole point of a deferral is that the Client can go away.

### 4.3 Why a Service, and not another Method

A ticket Method is defined by whoever owns the Object it hangs on, which means the mechanism only exists where a companion specification put it. Deferral belongs to the Service layer because that is the only layer that every Service already passes through: a Client that understands `Continue` can collect a deferred `Write`, a deferred `Call` and a deferred `HistoryUpdate` with the same code, from a Server that never anticipated any of them.

It also belongs there because it needs no new identifier. `RequestHeader.requestHandle` already identifies an outstanding request well enough for `Cancel` to act on it (OPC 10000-4 §5.7.5). `Continue` uses the same key, so a Server returns no ticket, a Client stores no cookie, and the two Services that act on an outstanding request are symmetric: `Cancel` gives it up, `Continue` asks for it.

### 4.4 Deferral in one paragraph

A Server that cannot answer in time **parks** the request and returns `Bad_RequestNotComplete` with a `RetryAfter` hint. The Client calls `Continue` with the same `requestHandle` and gets either the parked Service's own response — a `CallResponse`, a `WriteResponse`, whatever the original request was — or `Bad_RequestNotComplete` again with a fresh hint. A Client that has lost interest calls `Cancel`. A Client that would rather be told than ask subscribes to `DeferredRequestCompletedEventType`. A Client that understands none of this sees a Bad service result and treats the call as failed, which is what it does today when the Server times out instead.

## 5 The Continue Service

### 5.1 Continue

Collects the response of a parked request.

**Request**

| Name | Type | Description |
|---|---|---|
| requestHeader | RequestHeader | Common request parameters (OPC 10000-4 §7.32). |
| requestHandle | IntegerId | The `requestHandle` of the parked request, as it appeared in the `RequestHeader` of the deferred request. |

**Response**

A `Continue` has three kinds of answer, and they are kept apart on the wire rather than by a header a stack may discard.

**The parked Service's own response message**, when the parked request succeeded — the `CallResponse`, `WriteResponse` or `HistoryUpdateResponse` the original request would have produced had the Server answered it immediately. Its `ResponseHeader.requestHandle` **shall** carry the `requestHandle` of the `Continue` request, not of the parked one, so the response matches the request that fetched it; the parked handle is the request parameter and needs no echo.

**A `ContinueResponse`**, when the parked request *failed*. Its own `serviceResult` is `Good` — the `Continue` succeeded — and `deferredServiceResult` carries the Bad `serviceResult` the parked response had, with `deferredDiagnosticInfo` beside it.

**A `ServiceFault`**, when the `Continue` itself failed, carrying one of the results below.

The middle case is why `ContinueResponse` exists and is not the empty placeholder a Service definition would otherwise need. Without it, a parked `ApplyChanges` that failed with `Bad_ServerTooBusy` and a `Continue` refused by the retry floor with `Bad_ServerTooBusy` would be the same message, and a Client could not tell *the work failed* from *ask again later*. Every Bad `serviceResult` travels as a `ServiceFault` under OPC 10000-4 §7.34, so the two would be indistinguishable at exactly the moment the distinction matters most. Moving the parked failure into a `Good` response separates them by message type, which every Client can see.

**Preconditions.** The Session **shall** be activated. `requestHandle` **shall** identify a parked request the calling Session is entitled to collect (§7.5).

**Service results**

| Result | When |
|---|---|
| *the parked response, or a `ContinueResponse`* | The work has finished and the outcome is being handed over. |
| `Bad_RequestNotComplete` | The work has not finished. A fresh hint accompanies it (§6.3). |
| `Bad_DeferredRequestUnknown` | No parked request with that `requestHandle` is known to this Session. |
| `Bad_DeferredRequestExpired` | A parked request with that `requestHandle` existed and the Server discarded it (§7.3). |
| `Bad_RequestCancelledByRequest` | A parked request with that `requestHandle` was abandoned with `Cancel` (§7.4). |
| `Bad_DeferralNotSupported` | The Server implements `Continue` but defers no Service. A Server that does not implement the Service at all returns `Bad_ServiceUnsupported`, as it does for any Service it has not implemented. |
| `Bad_ServerTooBusy` | The call arrived sooner than `MinRetryAfter` after the previous one while the request was still `Executing` (§6.3). |

`Bad_DeferredRequestExpired` and `Bad_RequestCancelledByRequest` are distinguished from `Bad_DeferredRequestUnknown` for as long as the Server keeps a record of the request, which §7.1 bounds from below. Once the required retention has elapsed a Server **may** discard the record and answer `Bad_DeferredRequestUnknown` instead; a Client **shall** treat all three as *there is nothing to collect and there never will be*.

### 5.2 Why the response is polymorphic

`Continue` is answered with a message that is not the response its request declares. This looks like a new obligation on implementations and is not one.

A Client already cannot assume that the message it receives is the response type it asked for: **any** request may be answered with a `ServiceFault` instead, which is a different message with a different TypeId, and OPC 10000-6 identifies every message by its own TypeId rather than by the request it answers. Dispatching a response by reading what arrived — rather than by assuming what was sent — is therefore something every conforming stack already does. `Continue` asks for no new capability; it widens the set of legal answers from *two* to *the response of whichever Service was parked*.

The alternative — wrapping *every* parked response in an `ExtensionObject` inside a `ContinueResponse` — was considered and rejected. It preserves a one-to-one request-to-response mapping that the `ServiceFault` rule has already broken, and it does so by making every Client decode a response twice and by giving the same response two different on-wire forms depending on how it was collected. A response that is byte-identical however it is fetched is worth more than a mapping that is already not true. `ContinueResponse` therefore carries a parked *failure*, which has no response message of its own, and never a parked success, which does.

A Server **shall not** send a parked response to a `Continue` whose calling Session is not entitled to it, and **shall not** send any message other than the parked response, a `ContinueResponse` or a `ServiceFault` (§5.1).

### 5.3 Placement

`Continue` belongs to the Session Service Set, beside `Cancel`. It operates on a request outstanding within a Session, requires an activated Session, and is meaningless outside one — the same three properties that place `Cancel` there.

## 6 Deferring a request

### 6.1 When a Server may defer

A Server **may** defer a request when all of the following hold, and **shall not** otherwise:

- The request's message type is listed in `AsyncServiceCapabilities.DeferrableServices`.
- The Service is not one of those §8 excludes.
- Parking the request would not take the Server past `MaxDeferredRequests`, nor the Session past `MaxDeferredRequestsPerSession`.

A Server that would exceed a parking limit **shall** either answer the request synchronously or refuse it with `Bad_TooManyDeferredRequests`. It **shall not** park a request and then discard it to make room: a parked request that vanishes is indistinguishable, to the Client, from one that was never accepted, and the effect may already be in flight.

**Admission is decided before the work starts, not after.** A Server **shall** reserve the parking slot before it begins any work whose effect it cannot undo and whose outcome it might have to defer. Discovering at the end that there is no room to park the answer is the one outcome the mechanism must never produce: it leaves the effect done and the outcome unreachable, which is the failure this specification exists to remove. Where a Server cannot reserve in advance — because it could not know the work would run long — it **shall** exceed `MaxDeferredRequests` rather than discard the outcome, and **shall** report the excess through `DeferredRequestCount`, whose value is therefore a measurement and not a bound.

The decision to defer is the **Server's alone**. A Client neither opts in nor opts out, for the same reason a Client does not opt in to `Bad_Timeout`: the condition that causes a deferral is a property of the Server's situation, not of the Client's preference, and a mechanism that only worked for Clients that asked for it would leave the Server with nothing to do about the Clients that did not.

### 6.2 The deferral headers

A response that reports a request as parked **shall** carry a `DeferralResponseHeaderDataType` in `ResponseHeader.additionalHeader`, which OPC 10000-4 §7.33 reserves for exactly this purpose and which an application that does not understand it ignores.

A request **may** carry a `DeferralRequestHeaderDataType` in `RequestHeader.additionalHeader`. Every member of it is a **preference and never a precondition**: a request that carries it may still be answered synchronously, and a request that omits it may still be deferred. A Server **shall** ignore a member it does not honour rather than fail the request, so a Client that expresses a preference is never worse off than one that expresses none.

Both structures are defined by the Part 5 errata.

### 6.3 The retry contract

`RetryAfter` in the response header tells the Client how long to wait before its next `Continue`. It is a hint the Server computes from what it knows — a gateway distributing to five hundred devices knows more about how long that takes than any Client does — and a Client **should** honour it.

Because a Bad `serviceResult` travels as a `ServiceFault`, and an implementation may surface a fault as an exception that discards the header it arrived on, **the retry contract shall not depend on the header alone**. A Server **shall** publish `DefaultRetryAfter` and `MinRetryAfter` in `AsyncServiceCapabilities`, both readable by any Client with a `Read`. A Client that cannot read `additionalHeader` **shall** use `DefaultRetryAfter`.

`MinRetryAfter` is the floor, and it is normative in both directions. A Server **shall not** return a `RetryAfter` below it, and **shall** refuse a `Continue` that arrives sooner than `MinRetryAfter` after the previous `Continue` for the same parked request with `Bad_ServerTooBusy`. Without an enforced floor, a Client that ignores the hint converts a deferral into a poll loop against a Server that deferred because it was already busy.

The floor applies **only while the parked request is `Executing`**. A `Continue` for a request that is `Ready`, `Delivered`, `Cancelled` or `Expired` is answered immediately, however soon it arrives. Throttling a Client that has something to collect would be perverse in general, and specifically incompatible with `DeferredRequestCompletedEventType`, which exists to tell a Client to call `Continue` the moment the response is ready: a floor that outranked readiness would make the Server refuse the call it had just asked for.

Refusing a `Continue` with `Bad_ServerTooBusy` **shall not** affect the parked request: it is not collected, not expired and not cancelled, it is **not** a `Continued` transition and **shall not** be audited as one, and it **shall not** increment `ContinueCount`. The next `Continue` after the floor has elapsed behaves as though the refused one had not been sent, and every observable of the parked request says so.

### 6.4 requestHandle uniqueness

`Cancel` is defined against *"one or more requests"* with a given `requestHandle` (OPC 10000-4 §5.7.5), so OPC UA does not require handles to be unique. `Continue` returns exactly one response and therefore does.

A Client **shall** use a `requestHandle` that is unique among the requests it has outstanding and parked. A Server **shall** refuse, with `Bad_RequestHandleInUse`, any new request whose `requestHandle` matches a parked request in the same **scope**, except in the case §6.5 defines:

| The parked request is | Its handle is reserved against |
|---|---|
| not durable | other requests on the same Session |
| durable | other requests on **any** Session of the same principal (§7.5), for as long as the record exists |

The wider scope for a durable request is not a convenience. A durable response is collected by principal and handle alone, so two Sessions of one user that both parked handle 42 would leave `Continue(42)` with two candidate answers and no way to choose — and picking either discloses one Client's result to another. Reserving the handle across the principal is what makes the lookup single-valued.

`Continue` and `Cancel` are **exempt**. Their own `RequestHeader.requestHandle` is the handle of *that* call and has nothing to do with the `requestHandle` parameter naming the parked request, so a collision between the two is not a collision at all. A Server **shall not** refuse a `Continue` or a `Cancel` under this clause.

### 6.5 Duplicate suppression

A Client that does not implement this specification reads `Bad_RequestNotComplete` as a failure. Some such Clients retry. If the Server executes the retry, the effect the first request set in motion happens twice — and for `UpdateCertificate` or a Method that moves a machine, twice is not a rounding error.

A Server that has parked a request **shall** treat a subsequent request on the same Session as an implicit `Continue` when it carries the same `requestHandle`, the same message type, **and** a request body equivalent to the parked one. It **shall not** execute such a request a second time, and **shall** answer it exactly as it would have answered a `Continue` for that parked request.

Equivalence is of the **body**, not of the bytes: two requests are equivalent when every Service parameter outside the `RequestHeader` is equal. The `RequestHeader` is excluded because a legitimate retry carries a new `timestamp` and may carry a different `timeoutHint`, `returnDiagnostics` or `auditEntryId`, none of which changes what the Server was asked to do.

A request that matches the handle but **not** the body is a different request wearing the same name, and is refused with `Bad_RequestHandleInUse` (§6.4). Treating it as an implicit `Continue` would hand a Client the answer to a question it did not ask — a `Write` of one value answered with the result of writing another — which is worse than either executing it or refusing it.

This does not make deferral safe for every legacy Client: a Client that generates a fresh handle for each attempt is not helped, and cannot be, by anything a Server can observe. It makes the *repeatable* case safe, and it costs nothing, because a Server already holds the request it parked.

## 7 Lifecycle

### 7.1 States and the retention deadline

A parked request is `Executing`, then `Ready`, and then terminal: `Delivered`, `Cancelled` or `Expired`. `DeferredRequestState` in the Part 5 errata is the normative enumeration.

`Executing` and `Ready` are the states of a live parked request. The three terminal states are records of one that is not, kept so that `Continue` can say *why* there is nothing new to collect — and, for `Delivered`, so that it can hand over the same answer again (§7.2).

**One deadline governs retention**, and a Server **shall** compute it as

> `RetentionDeadline` = `ParkedAt` + min(`MaxDeferralTime`, `RequestedDeferralTime` if non-zero)

extended, while the record is terminal, to at least the greater of `MinRetryAfter` and the last `RetryAfter` the Server issued for that request. That extension is what the Client can plan against: it was told when to come back, so the record is still there when it does.

For a durable parked request whose issuing Session has closed, the deadline is additionally capped at `SessionClosedAt` + `MaxDurableDeferralTime`, and the **earlier** of the two applies. `ExpiryTime` in the response header **shall** state the deadline in force at the moment the header is written; a Server that later shortens it — only ever by the durable cap — **shall** report the new value in the next header it writes.

`RetentionDeadline` bounds retention from above and the extension bounds it from below. It does **not** bound it from below against the events of §7.5: a Session that closes, a user identity that changes and a Server that shuts down all discard parked responses before their deadline, and are audited as `Discarded` so that the difference is visible.

### 7.2 An effect happens once; a response may be replayed

A parked response is handed over on `Continue`, and the parked request becomes `Delivered`. It is **not** discarded. Until its retention deadline the Server **shall** answer a further `Continue` for the same handle with the same response.

This is deliberate, and it is the difference between a mechanism that solves the problem and one that moves it. A Server cannot know whether a response it transmitted arrived: if the connection fails between transmission and receipt — which is precisely the condition that makes long operations hard — a delete-on-delivery rule leaves the Client with an effect it caused and an outcome it can never learn. That is the failure this specification exists to remove, and reintroducing it at the last step would be a poor joke.

What happens once is the **effect**. A Server **shall not** execute a parked request a second time under any circumstances, and a replayed response is byte-equivalent to the first, not a re-execution.

After the retention deadline a further `Continue` returns `Bad_DeferredRequestExpired`, or `Bad_DeferredRequestUnknown` once the Server has discarded the record. A Server **shall not** answer `Bad_DeferredRequestExpired` while the response is still retained and collectable.

### 7.3 Expiry

A Server **shall** discard a parked response at its retention deadline (§7.1), whether or not the work has finished and whether or not the response was collected, and **shall** answer a subsequent `Continue` with `Bad_DeferredRequestExpired` for as long as it keeps the record.

The deadline runs from the moment the request is parked, not from the moment the response becomes ready, so a Client can compute it the instant it receives `Bad_RequestNotComplete` — before it knows anything else about how long the work will take. `ExpiryTime` states the same deadline as an absolute time, so a Client with a skewed clock and a Client with a slow link agree on it.

Expiry discards the **answer**. It does not stop the work, and it **shall not** be read as an undo (§7.6). Where the work later finishes, its outcome still reaches the audit trail as a `Completed` transition (§7.7).

### 7.4 Cancel

`Cancel` (OPC 10000-4 §5.7.5) acts on a parked request as it acts on any other outstanding request: the parked response is discarded and the request counts towards `cancelCount`. A subsequent `Continue` returns `Bad_RequestCancelledByRequest`.

`Cancel` and `Continue` are the two halves of the same decision, which is why `Continue` reuses `Cancel`'s parameter and placement: a Client that has a parked request either wants the answer or does not, and the Service it calls says which.

### 7.5 The Session, the principal, and durable deferral

A parked request belongs to its issuing Session. A Server **shall** discard every parked response of a Session when that Session closes or is abandoned, **shall** discard them when the Session's user identity changes through a subsequent `ActivateSession`, and **shall** answer a `Continue` from any other Session with `Bad_DeferredRequestUnknown` — not with `Bad_UserAccessDenied`, which would confirm that the handle exists.

A parked request **shall not** be treated as Session activity for the purpose of the Session timeout. Work the Server is doing on its own is not evidence that the Client is still there, and a Session that stayed alive because of it would keep a user identity unexamined for as long as the work ran.

**The principal.** Durable deferral needs a notion of "the same user" that survives a Session, and `ActivateSession` does not provide one: it authenticates a token, and says nothing about when two tokens presented at different times denote the same user. A Server **shall** therefore derive, for each activated Session, a stable **principal identifier** — the value it already uses to select the Session's Roles under OPC 10000-18 — and **shall** compare principal identifiers, never tokens, when deciding entitlement.

A Server **shall not** make a request durable when the Session's identity token is anonymous. Every anonymous Session denotes the same non-user, so an anonymous principal would entitle every anonymous Client on the Server to every other anonymous Client's parked responses. Where a Client asks for durability on an anonymous Session, the Server **shall** park the request non-durably and report `Durable` as FALSE.

**One entitlement predicate.** A Session is entitled to a parked request when it is the issuing Session, or when the request is durable, its issuing Session has ended, and the Session's principal identifier equals the issuing principal. That single predicate **shall** govern `Continue` (§5.1), the delivery of `DeferredRequestCompletedEventType`, and the per-Session projection of `DeferredRequests` alike. Three mechanisms expose the same fact, and a Server that used three different rules would leak through whichever was loosest.

**Durable deferral** is an exception to the first of those discard rules only — it survives Session *closure*, and never an identity change — and it is what makes the mechanism usable for work that outlives a connection. A Server that supports it — `DurableDeferralSupported` is TRUE — **shall**, for a parked request whose `DeferralRequestHeaderDataType` set `RequestDurable`:

- hold the parked response after the issuing Session closes, until the retention deadline of §7.1;
- deliver it only to a Session the entitlement predicate admits;
- re-evaluate the authorization the deferred Service requires against that Session's Roles at the moment of delivery, not at the moment of parking, and answer `Bad_UserAccessDenied` where it now fails — **without** discarding the parked response, so a Client whose Roles were momentarily wrong is not punished with the loss of an outcome;
- reserve the `requestHandle` across the principal for as long as the record exists (§6.4);
- report the collection as a `Reclaimed` transition in the audit trail, so a response collected by a Session other than the one that asked for it is visible as such.

**Not every response can be durable.** A response that carries Session-scoped artifacts — a continuation point, a registered NodeId alias, a MonitoredItem or Subscription identifier — is meaningless once its Session has gone. A Server **shall not** make such a request durable, **shall** park it non-durably instead, and **shall** report `Durable` as FALSE, so the Client learns that it must collect within the Session rather than discovering it from a continuation point the Server cannot resolve.

A Server whose `DurableDeferralSupported` is FALSE **shall** ignore `RequestDurable` and report `Durable` as FALSE in the response header, so a Client learns that its preference had no effect rather than assuming it did.

### 7.6 Authorization, and what a deferral does not do

Deferral moves *when* a response is delivered. It **shall not** move when the request is authorized: a Server **shall** perform every authorization check the Service requires before it parks the request, exactly as it would before executing it. A request the user may not make is refused, not parked.

**Abandoning the answer is not cancelling the effect.** `Cancel` and expiry both discard a parked response. Whether the work that response describes is undone is a property of the Service being deferred and of the Server, and this specification requires nothing of it. A Server **shall not** state or imply that discarding a parked response rolls anything back, and a Client **shall not** assume it.

That is not a gap left open; it is the honest description of a distributed operation. A gateway that has already written a TrustList to two hundred devices cannot un-write it because the Client stopped listening, and a mechanism that promised otherwise would be promising something no implementation could keep. What the specification does require instead is that the outcome remains **observable**: §7.7 requires a `Completed` audit transition when the work finishes, whether or not any response was still being held and whether or not anyone collected it.

### 7.7 Auditing

A Server that supports auditing **shall** generate an `AuditDeferredRequestEventType` Event for every transition of a parked request. `DeferredRequestTransition` in the Part 5 errata is the normative enumeration; the table below is the complete set, with the `Outcome` each carries.

| Transition | Raised when | `Outcome` |
|---|---|---|
| `Deferred` | The Server parked the request. | `Good_CompletesAsynchronously` — not yet known. |
| `Continued` | A `Continue` arrived and the response was not ready. A call refused with `Bad_ServerTooBusy` is **not** a `Continued` transition (§6.3). | `Good_CompletesAsynchronously` — not yet known. |
| `Completed` | The work finished and its outcome became known. Raised whether or not a response is still held. | The `serviceResult` of the response. |
| `Delivered` | A Session collected the response, including a replay (§7.2). | The `serviceResult` of the response. |
| `Reclaimed` | A Session other than the issuing one collected it. It **replaces** `Delivered` for that collection rather than accompanying it, so one collection raises one Event. | The `serviceResult` of the response. |
| `Cancelled` | A Client abandoned the response with `Cancel`. | The `serviceResult` where the work had finished, `Good_CompletesAsynchronously` where it had not. |
| `Expired` | The retention deadline passed. | As `Cancelled`. |
| `Discarded` | The response was discarded before its deadline because the issuing Session closed, its identity changed, or the Server shut down. | As `Cancelled`. |

This is deliberately stricter than the auditing of an ordinary request. A deferral separates the moment an effect is authorized from the moment its outcome is known, and permits the Client that authorized it to walk away in between, so the audit trail is the only record that spans both.

`Completed` is what makes that promise good. `MaxDeferralTime` expires a parked request whether or not the work is done (§7.3), so an `Expired` transition alone would record `Good_CompletesAsynchronously` for the very requests whose outcome nobody else will ever see. `Completed` is raised when the answer exists, even if no Client is left to receive it, and it is therefore the transition an auditor reads to learn what actually happened.

### 7.8 Order of evaluation

Two things can happen to a parked request at once — a `Cancel` while a `Continue` is in flight, a deadline that passes while a response is being handed over — and a Client's view of the outcome must not depend on which the Server noticed first. A Server **shall** apply every transition of a parked request atomically, and **shall** resolve a `Continue` against the state in force when it began, in this order:

1. **A terminal state wins over throttling.** `Ready`, `Delivered`, `Cancelled` and `Expired` are answered immediately; the retry floor is evaluated only for `Executing` (§6.3).
2. **A `Continue` already resolved as `Ready` completes.** A `Cancel` or a deadline that arrives after it began does not turn its answer into a fault; the collection is audited as `Delivered` or `Reclaimed`, and the `Cancel` then applies to the `Delivered` record.
3. **Otherwise `Cancel` wins over expiry**, which wins over a `Continue` that has not yet resolved. A Client that abandoned a response is told it abandoned it, rather than that it ran out of time.

The single-execution rule of §7.2 is unaffected by all of this: whichever order the Server resolves these in, the parked request's effect happened once.

## 8 Interaction with other Services

**Services that are never deferred.** A Server **shall not** defer `Continue`, `Cancel`, `Publish`, `Republish`, `CreateSession`, `ActivateSession`, `CloseSession`, or any Service of the SecureChannel or Discovery Service Sets.

`Continue` and `Cancel` cannot be deferred without recursion. `Publish` is already a long poll and deferring it would replace one waiting mechanism with two. The Session Services establish the very context a parked request is scoped to: a parked `ActivateSession` would be a parked request belonging to a Session that does not yet exist, or whose identity is the thing in question. The Discovery Services are answered without a Session and therefore have nowhere to park.

**Discovering deferral is never deferred.** A `Browse` of `ServerCapabilities` and a `Read` of any Property of the `AsyncServiceCapabilities` Object **shall** be answered synchronously. Deferring them would be a bootstrap loop: a Client cannot learn `DefaultRetryAfter` — the value it needs in order to respond to a deferral at all — from a call that is itself deferred. Every other `Browse` and `Read` may be deferred like any other Service, subject to §6.1.

**`Call`.** Deferral is per request, not per operation. A `Call` carrying several `methodsToCall` is parked as a whole and its response is delivered as a whole, once every operation has settled. A Server **shall not** deliver a partial `CallResponse`.

This costs some parallelism — one slow device holds up the answers about nineteen fast ones — and buys a mechanism that is identical for every Service. Per-operation deferral would need a continuation identifier per operation, a partial-response encoding per Service, and a rule for what a Client does with a response half of whose entries are placeholders; and the Client that wants the fast answers separately can send them as separate requests, which is a thing it can already do.

**`Cancel`.** Covered by §7.4. A `Cancel` naming a handle that identifies both an in-flight request and a parked one cancels both, and counts both.

**Subscriptions.** Unaffected. A Client that would rather be told than ask subscribes to `DeferredRequestCompletedEventType` on the Server Object (Part 5 errata) and calls `Continue` once, when there is something to collect. The Event is an optimization of the retry contract and never a replacement: a Server **shall** honour a `Continue` that arrives without one, and a Client that receives no Event **shall** fall back on `RetryAfter`.

**Server shutdown.** A Server that is shutting down **shall** discard its parked responses, **shall** audit each as `Discarded`, and **should** answer any `Continue` that arrives with `Bad_Shutdown`. Parked responses are not required to survive a restart; the retention deadline is the only guarantee a Client has, and it is bounded.

## 9 StatusCodes

Five StatusCodes are new. The most important one is not.

| Symbolic id | Meaning |
|---|---|
| `Bad_DeferralNotSupported` | `Continue` was called on a Server that does not defer requests. |
| `Bad_DeferredRequestUnknown` | No parked request with that `requestHandle` is known to the calling Session. |
| `Bad_DeferredRequestExpired` | A parked request with that `requestHandle` existed and the Server discarded it. |
| `Bad_TooManyDeferredRequests` | A parking limit would be exceeded, and the Server could not answer synchronously. |
| `Bad_RequestHandleInUse` | A new request carries a `requestHandle` that already identifies a parked request on the same Session. |

Numeric values are **provisional**; final assignments are made by the OPC Foundation alongside the existing StatusCode registry.

The following are existing StatusCodes, reused:

| Symbolic id | Reused as |
|---|---|
| `Bad_RequestNotComplete` | *"The request has not been processed by the server yet."* Already OPC UA's poll-again code, defined for the pull-management `FinishRequest` Method of OPC 10000-12. Deferral generalizes the pattern it was written for, so it generalizes the code rather than adding a synonym beside it. |
| `Bad_RequestCancelledByRequest` | Returned by `Continue` for a parked request abandoned with `Cancel`, which is what the code already describes. |
| `Bad_ServerTooBusy` | Returned by `Continue` when it arrives sooner than `MinRetryAfter` after the previous one. |
| `Bad_Shutdown` | Returned by `Continue` when the Server is shutting down and has discarded its parked responses. |
| `Bad_ServiceUnsupported` | Returned for `Continue` by a Server that does not implement the Service, exactly as for any unimplemented Service. It is what distinguishes *"I do not have this Service"* from `Bad_DeferralNotSupported`, which says *"I have it, and there is nothing I would defer"*. |
| `Bad_SecurityModeInsufficient` | Returned when `DeferredRequests` is read over an unencrypted SecureChannel (Part 5 errata §6). |
| `Good_CompletesAsynchronously` | Carried as the `Outcome` of a `Deferred` audit transition, whose result is not yet known. This specification adds no new use of it on the Service path: a deferred request is reported by `Bad_RequestNotComplete`, because a Client that does not implement `Continue` must not read a deferral as a success. |

## 10 Conformance units

| Conformance unit | Requires | Content |
|---|---|---|
| `ASE-Execution` | `ASE-Model` | `Continue` (§5), the deferral rules of §6 including the retry contract and duplicate suppression, the lifecycle of §7 excluding §7.5 durable deferral and §7.7 auditing, the `ContinueRequest`, `ContinueResponse`, `DeferralRequestHeaderDataType`, `DeferralResponseHeaderDataType` and `DeferredRequestState` DataTypes defined by the Part 5 errata, and the StatusCodes of §9. |
| `ASE-Model` | `ASE-Execution` | `AsyncServiceCapabilitiesType` and its well-known `AsyncServiceCapabilities` instance, defined by the Part 5 errata. |
| `ASE-Durable` | `ASE-Execution`, `ASE-Auditing` | Durable deferral (§7.5): parked responses that outlive their issuing Session and are reclaimable by the same principal. |
| `ASE-Diagnostics` | `ASE-Execution` | `AsyncServiceDiagnostics` and its per-Session projection, defined by the Part 5 errata. |
| `ASE-CompletionEvents` | `ASE-Execution` | `DeferredRequestCompletedEventType` (Part 5 errata). |
| `ASE-Auditing` | `ASE-Execution` | `AuditDeferredRequestEventType` on every transition, with the outcomes of §7.7. |

`ASE-Model` and `ASE-Execution` **require each other**, and are two units rather than one because the model and the Services land in different Parts. Neither is claimable alone: a Server that published `AsyncServiceCapabilities` without implementing `Continue` would be advertising limits on something it does not do, and a Server that deferred without publishing the Object would contradict §5 of the Part 5 errata, which makes the Object's absence the statement that a Server never defers.

`ASE-Auditing` is a prerequisite of `ASE-Durable` rather than an optional companion: a response collected by a Session other than the one that requested it is a security-relevant event, and §7.5 requires it to be visible as one.

### 10.1 Test assertions

Deferral cannot be provoked by a Service call: no legal request obliges a Server to be slow. Every assertion below whose stimulus says *defer* therefore presumes a **test operation** — a Node the Server under test exposes whose invocation the test harness can make outlast the Client's `timeoutHint`, and which the Server lists in `DeferrableServices`. Providing one is a precondition of testing this specification, in the same way that a testable alarm is a precondition of testing OPC 10000-9.

| Id | Assertion | Stimulus | Expected |
|---|---|---|---|
| ASE-001 | A Server that never defers says so by omission | Browse `ServerCapabilities` on a Server claiming none of these units | No `AsyncServiceCapabilities` Object |
| ASE-002 | `Continue` is refused where nothing can be deferred | `Continue` with any handle, on a Server claiming none of these units | `Bad_ServiceUnsupported`, or `Bad_DeferralNotSupported` where the Service is implemented but no Service is deferrable (§5.1) |
| ASE-003 | An unactivated Session cannot continue | `Continue` before `ActivateSession` | `Bad_SessionNotActivated` |
| ASE-004 | An unknown handle is refused | `Continue` with a handle never used | `Bad_DeferredRequestUnknown` |
| ASE-005 | A deferral is reported as Bad, not Good | Invoke the test operation | `Bad_RequestNotComplete`, not `Good_CompletesAsynchronously` |
| ASE-006 | The deferral header rides the fault | Read `ResponseHeader.additionalHeader` of the deferred response | A `DeferralResponseHeaderDataType` whose `RequestHandle` matches the request |
| ASE-007 | `RetryAfter` respects the floor | Compare `RetryAfter` with `MinRetryAfter` | `RetryAfter` ≥ `MinRetryAfter` |
| ASE-008 | The floor is enforced while executing | Two `Continue` calls separated by less than `MinRetryAfter`, while the test operation is still running | First returns `Bad_RequestNotComplete`; second returns `Bad_ServerTooBusy` |
| ASE-009 | A refused `Continue` is inert | After ASE-008, wait `MinRetryAfter`, then `Continue` and read the diagnostics record | Answered normally; `ContinueCount` counts the permitted calls only, and no `Continued` audit Event was raised for the refused one (§6.3). Requires `ASE-Diagnostics` and `ASE-Auditing` |
| ASE-010 | `Continue` returns the parked Service's response | Defer a `Call` that will succeed, let it finish, `Continue` | A `CallResponse`, with `ResponseHeader.requestHandle` equal to the `Continue` request's handle |
| ASE-010a | The floor never delays a ready response | `Continue` immediately after `DeferredRequestCompletedEventType` arrives, sooner than `MinRetryAfter` after the previous `Continue` | The parked response, not `Bad_ServerTooBusy` (§6.3) |
| ASE-010b | A parked failure is distinguishable from a `Continue` failure | Defer an operation that will fail with `Bad_ServerTooBusy`, let it finish, `Continue` | A `ContinueResponse` with `serviceResult` `Good` and `deferredServiceResult` `Bad_ServerTooBusy`, never a bare `ServiceFault` (§5.1) |
| ASE-011 | A collected response is replayed, not destroyed | `Continue` twice after collection, both within the retention deadline | Both return the same response; the effect happened once (§7.2) |
| ASE-011a | The effect is not repeated by replay | Compare the observable effect after ASE-011 with its state after the first collection | Unchanged |
| ASE-012 | An expired response is distinguishable | Let the retention deadline pass, then `Continue` | `Bad_DeferredRequestExpired`, answered without the retry floor delaying it (§6.3, §7.1) |
| ASE-013 | `Cancel` abandons a parked response | `Cancel` the handle, then `Continue` | `cancelCount` ≥ 1, then `Bad_RequestCancelledByRequest` |
| ASE-013a | `Cancel` and `Continue` are not refused for handle collision | `Continue` and `Cancel` whose own `RequestHeader.requestHandle` equals the parked handle | Both answered normally, never `Bad_RequestHandleInUse` (§6.4) |
| ASE-014 | A handle collision is refused | Issue a new request reusing a parked handle with a different message type | `Bad_RequestHandleInUse` |
| ASE-014a | A different body under the same handle is refused | Re-send the deferred request with the same handle and message type but a different body | `Bad_RequestHandleInUse`, and the parked response is unaffected (§6.5) |
| ASE-015 | A repeated request is not re-executed | Re-send the deferred request with the same handle, message type and body | Answered as a `Continue`; the effect happens once (§6.5) |
| ASE-016 | Another Session cannot collect | `Continue` the handle from a second Session, non-durable | `Bad_DeferredRequestUnknown`, indistinguishable from an unknown handle |
| ASE-016a | A completion Event reaches only the entitled | Subscribe two Sessions of different users to the Server Object, park a request as one | Only the entitled Session receives the Event; the other observes neither `RequestHandle` nor `ServiceResult` (Part 5 errata) |
| ASE-017 | Session close discards | Close the Session, reconnect, `Continue`, non-durable | `Bad_DeferredRequestUnknown`, and a `Discarded` audit transition |
| ASE-018 | Identity change discards | `ActivateSession` with a different user, then `Continue` | `Bad_DeferredRequestUnknown`, even when the request was parked durably (§7.5) |
| ASE-019 | A parked request is not Session activity | Park a request, issue no Service call for the Session timeout plus one `MinRetryAfter`, then call any Service | `Bad_SessionIdInvalid` (§7.5) |
| ASE-020 | Authorization precedes parking | Invoke the test operation as a user who may not | `Bad_UserAccessDenied`, not `Bad_RequestNotComplete` |
| ASE-021 | Excluded Services are never deferred | Under saturation, issue every Service §8 excludes, and a `Read` of `AsyncServiceCapabilities` | Never `Bad_RequestNotComplete` (§8) |
| ASE-022 | A parking limit is refused before the work starts | Park `MaxDeferredRequestsPerSession`, then invoke the test operation once more | Answered within `MaxDeferralTime` with `Bad_TooManyDeferredRequests` or a synchronous result, and `RejectedCount` increases |
| ASE-023 | A partial response is never delivered | Defer a `Call` with one fast and one slow operation | One `CallResponse` after both settle (§8) |
| ASE-024 | Completion is auditable without collection | Park a request, let the work finish, then let the retention deadline pass uncollected | A `Completed` transition carrying the `serviceResult`, then an `Expired` transition (§7.7) |
| ASE-024a | A late outcome still reaches the trail | Park a request whose work outlasts the retention deadline, let it expire, then let the work finish | `Expired` with `Outcome` `Good_CompletesAsynchronously`, then `Completed` carrying the real `serviceResult` (§7.7) |
| ASE-025 | Durable reclaim requires the same principal | Park durably, close the Session, `Continue` from a Session of a different user | `Bad_DeferredRequestUnknown` |
| ASE-025a | Anonymous is never durable | Park with `RequestDurable` on a Session whose token is anonymous | `Durable` FALSE in the response header, and no cross-Session reclaim (§7.5) |
| ASE-026 | Durable reclaim succeeds for the same principal | Park durably, let the work finish, close the Session, `Continue` from a new Session of the same user | The parked response, and a `Reclaimed` audit transition with no accompanying `Delivered` |
| ASE-026a | A durable handle is reserved across the principal | Park durably on one Session, then issue a request with the same handle on a second Session of the same user | `Bad_RequestHandleInUse` (§6.4) |
| ASE-027 | An unsupported preference is reported, not honoured silently | Set `RequestDurable` and invoke the test operation, on a Server whose `DurableDeferralSupported` is FALSE | The request is deferred and `Durable` is FALSE in the response header |
| ASE-028 | Diagnostics are projected per Session | Park requests from two Sessions of different users and read `DeferredRequests` as each, over an encrypted SecureChannel | Each Session sees only the records it is entitled to collect (Part 5 errata) |
| ASE-028a | Diagnostics require encryption | Read `DeferredRequests` over a SecureChannel whose SecurityMode is `None` | `Bad_SecurityModeInsufficient` (Part 5 errata) |

## 11 Insertion into OPC 10000-4 v1.05.07

| Draft clause | Target clause in OPC 10000-4 | Notes |
|---|---|---|
| §4 Overview | New `5.7.6.1 Overview` | Introduces deferral and its relationship to `Cancel`. |
| §5.1 `Continue` | New `5.7.6 Continue`, with `5.7.6.2 Parameters` and `5.7.6.3 Service results` | Parameter tables in the standard Request/Response form. `ContinueRequest` and `ContinueResponse` are added to the Service message DataTypes alongside every other Service's pair. |
| §5.2 Polymorphic response | `7.34 ServiceFault`, and `5.7.6.2` | A statement that the existing substitution rule already admits a response other than the declared one, cross-referenced from the Service. |
| §6.2 Deferral headers | `7.32 RequestHeader` and `7.33 ResponseHeader` | The two structures are named as defined uses of `additionalHeader`; the DataTypes themselves are defined by the Part 5 errata. |
| §6.4, §6.5 Handles and duplicates | `7.32 RequestHeader`, `requestHandle` | The uniqueness obligation belongs where `requestHandle` is defined. |
| §7.5 Session and durable deferral | `5.7 Session Service Set`, and the Role-selection text of OPC 10000-18 | The effects of Session close and identity change are stated where those operations are defined, and cross-referenced from `5.7.6`; the principal identifier is the one Role selection already uses. |
| §7.6 Authorization | `OPC 10000-2` and the `RolePermissions` text of OPC 10000-3 | No new mechanism; a statement that the existing one governs and runs before parking. |
| §7.7 Auditing | `Audit Events` clause of OPC 10000-5 | The audit EventType is defined by the Part 5 errata; the obligation to raise it, and the transition/outcome table, belong here. |
| §7.8 Order of evaluation | `5.7.6`, beside the Service | A linearization rule, stated once for every transition. |
| §8 Interaction | `5.5 Discovery Service Set`, `5.6 SecureChannel Service Set`, `5.7 Session Service Set`, `5.14 Subscription Service Set` | The exclusion list is stated where the excluded Services are defined. |
| §9 StatusCodes | Common Service Result Codes (Table 178) and the numeric registry maintained with OPC 10000-6 | Five new symbolic ids; `Bad_RequestNotComplete` gains a second documented use. Every `Continue` result is service-level, so Table 179 is not involved. |
| §10 Conformance units | OPC 10000-7 | Six new conformance units and the Profiles that group them. |

`Continue` is proposed as a new `5.7.6`, after `5.7.5 Cancel`, so the existing Service Set numbering is unchanged.
