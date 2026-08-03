# OPC UA Part 4 — Asynchronous Service Execution

**Working draft for submission to the OPC Foundation Working Group**
**Proposed addition to:** OPC 10000-4 Services v1.05.07
**Namespace:** `http://opcfoundation.org/UA/` (base OPC UA namespace)
**Version:** 0.1.0 · **Date:** 2026-08-03

> **Status — working draft.** This document proposes one Service — `Complete` — and the rules that let a Server answer any request later than the Client asked for it: when a Server may park a request, how it says so, how a Client collects the parked response, how it abandons one, and what happens when the Session that issued the request goes away. The Nodes a Client reads to discover all of this, and the Events that report it, are in the [Part 5 errata](OPC-UA-Part5-Async-Service-Model.md). Nothing here is normative or endorsed by the OPC Foundation.

---

## 1 Scope

This specification defines the `Complete` Service and the **deferral** mechanism it completes: a Server that cannot produce a response within the time the Client is willing to wait parks the request, answers `Bad_RequestNotComplete` with a cooperative retry hint, and hands the response to the first `Complete` that arrives after the work finishes.

It defines which Services may be deferred, how a parked request is identified, how long a Server holds a parked response, how a Client abandons one, what a Server does when the Session that issued a request closes, and how all of that is audited.

It does not define the Nodes through which a Client discovers a Server's deferral limits or the Events that report completion, which are in the Part 5 errata. It defines no Service-specific behaviour: what a deferred `Call` or a deferred `Write` actually does while it is parked is the business of the Service being deferred, not of this mechanism.

## 2 Normative references

- [OPC 10000-2](https://reference.opcfoundation.org/specs/OPC-10000-2/) — Security Model.
- [OPC 10000-3](https://reference.opcfoundation.org/specs/OPC-10000-3/) — Address Space Model.
- [OPC 10000-4 v1.05.07](https://reference.opcfoundation.org/specs/OPC-10000-4/) — Services.
- [OPC 10000-5](https://reference.opcfoundation.org/specs/OPC-10000-5/) — Information Model.
- [OPC 10000-6](https://reference.opcfoundation.org/specs/OPC-10000-6/) — Mappings.
- [OPC 10000-12](https://reference.opcfoundation.org/specs/OPC-10000-12/) — Discovery and Global Services.
- [OPC UA Part 5 — Asynchronous Service Model](OPC-UA-Part5-Async-Service-Model.md) — the companion information model errata.

## 3 Terms, definitions and abbreviations

| Term | Definition |
|---|---|
| Deferral | A Server's decision to answer a request later than the request itself, by parking it. |
| Parked request | A request the Server has accepted and is still working on, or has finished and is holding an answer for. |
| Parked response | The response of a parked request, held by the Server until a Client collects it, the Client abandons it, or it expires. |
| Issuing Session | The Session on which the parked request arrived, and the only Session that can collect the response. |
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

A ticket Method is defined by whoever owns the Object it hangs on, which means the mechanism only exists where a companion specification put it. Deferral belongs to the Service layer because that is the only layer that every Service already passes through: a Client that understands `Complete` can collect a deferred `Write`, a deferred `Call` and a deferred `HistoryUpdate` with the same code, from a Server that never anticipated any of them.

It also belongs there because it needs no new identifier. `RequestHeader.requestHandle` already identifies an outstanding request well enough for `Cancel` to act on it (OPC 10000-4 §5.7.5). `Complete` uses the same key, so a Server returns no ticket, a Client stores no cookie, and the two Services that act on an outstanding request are symmetric: `Cancel` gives it up, `Complete` asks for it.

### 4.4 Deferral in one paragraph

A Server that cannot answer in time **parks** the request and returns `Bad_RequestNotComplete` with a `RetryAfter` hint. The Client calls `Complete` with the same `requestHandle` and gets either the parked Service's own response — a `CallResponse`, a `WriteResponse`, whatever the original request was — or `Bad_RequestNotComplete` again with a fresh hint. A Client that has lost interest calls `Cancel`. A Client that would rather be told than ask subscribes to `DeferredRequestCompletedEventType`. A Client that understands none of this sees a Bad service result and treats the call as failed, which is what it does today when the Server times out instead.

## 5 The Complete Service

### 5.1 Complete

Collects the response of a parked request.

**Request**

| Name | Type | Description |
|---|---|---|
| requestHeader | RequestHeader | Common request parameters (OPC 10000-4 §7.32). |
| requestHandle | IntegerId | The `requestHandle` of the parked request, as it appeared in the `RequestHeader` of the deferred request. |

**Response**

A `Complete` has three kinds of answer, and they are kept apart on the wire rather than by a header a stack may discard.

**The parked Service's own response message**, when the parked request succeeded — the `CallResponse`, `WriteResponse` or `HistoryUpdateResponse` the original request would have produced had the Server answered it immediately. Its `ResponseHeader.requestHandle` **shall** carry the `requestHandle` of the `Complete` request, not of the parked one, so the response matches the request that fetched it; the parked handle is the request parameter and needs no echo.

**A `CompleteResponse`**, when the parked request *failed*. Its own `serviceResult` is `Good` — the `Complete` succeeded — and `deferredServiceResult` carries the Bad `serviceResult` the parked response had, with `deferredDiagnosticInfo` beside it.

**A `ServiceFault`**, when the `Complete` itself failed, carrying one of the results below.

The middle case is why `CompleteResponse` exists and is not the empty placeholder a Service definition would otherwise need. Without it, a parked `ApplyChanges` that failed with `Bad_ServerTooBusy` and a `Complete` refused by the retry floor with `Bad_ServerTooBusy` would be the same message, and a Client could not tell *the work failed* from *ask again later*. Every Bad `serviceResult` travels as a `ServiceFault` under OPC 10000-4 §7.34, so the two would be indistinguishable at exactly the moment the distinction matters most. Moving the parked failure into a `Good` response separates them by message type, which every Client can see.

**Preconditions.** The Session **shall** be activated. `requestHandle` **shall** identify a parked request of that same Session (§7.5).

**Service results**

| Result | When |
|---|---|
| *the parked response, or a `CompleteResponse`* | The work has finished and the outcome is being handed over. |
| `Bad_RequestNotComplete` | The work has not finished. A fresh hint accompanies it (§6.3). |
| `Bad_DeferredRequestUnknown` | No parked request with that `requestHandle` is known to this Session. |
| `Bad_DeferredRequestExpired` | A parked request with that `requestHandle` existed and the Server discarded it (§7.3). |
| `Bad_RequestCancelledByRequest` | A parked request with that `requestHandle` was abandoned with `Cancel` (§7.4). |
| `Bad_DeferralNotSupported` | The Server implements `Complete` but defers no Service. A Server that does not implement the Service at all returns `Bad_ServiceUnsupported`, as it does for any Service it has not implemented. |
| `Bad_ServerTooBusy` | The call arrived sooner than `MinRetryAfter` after the previous one while the request was still `Executing` (§6.3). |

`Bad_DeferredRequestExpired` and `Bad_RequestCancelledByRequest` are distinguished from `Bad_DeferredRequestUnknown` for as long as the Server keeps a record of the request, which the record floor of §7.1 bounds from below. Past that floor a Server **may** discard the record and answer `Bad_DeferredRequestUnknown` instead; a Client **shall** treat all three as *there is nothing to collect and there never will be*.

### 5.2 Why the response is polymorphic

`Complete` is answered with a message that is not the response its request declares. This looks like a new obligation on implementations and is not one.

A Client already cannot assume that the message it receives is the response type it asked for: **any** request may be answered with a `ServiceFault` instead, which is a different message with a different TypeId, and OPC 10000-6 identifies every message by its own TypeId rather than by the request it answers. Dispatching a response by reading what arrived — rather than by assuming what was sent — is therefore something every conforming stack already does. `Complete` asks for no new capability; it widens the set of legal answers from *two* to *the response of whichever Service was parked*.

The alternative — wrapping *every* parked response in an `ExtensionObject` inside a `CompleteResponse` — was considered and rejected. It preserves a one-to-one request-to-response mapping that the `ServiceFault` rule has already broken, and it does so by making every Client decode a response twice and by giving the same response two different on-wire forms depending on how it was collected. A response that is byte-identical however it is fetched is worth more than a mapping that is already not true. `CompleteResponse` therefore carries a parked *failure*, which has no response message of its own, and never a parked success, which does.

A Server **shall not** send a parked response to a `Complete` from a Session other than the one that parked it, and **shall not** send any message other than the parked response, a `CompleteResponse` or a `ServiceFault` (§5.1).

### 5.3 Placement

`Complete` belongs to the Session Service Set, beside `Cancel`. It operates on a request outstanding within a Session, requires an activated Session, and is meaningless outside one — the same three properties that place `Cancel` there.

## 6 Deferring a request

### 6.1 When a Server may defer

A Server **may** defer a request when all of the following hold, and **shall not** otherwise:

- The request carries a `DeferralRequestHeaderDataType` in `RequestHeader.additionalHeader` (§6.2).
- The request's message type is listed in `AsyncServiceCapabilities.DeferrableServices`.
- The Service is not one of those §8 excludes.
- Parking the request would not take the Server past `MaxDeferredRequests`, nor the Session past `MaxDeferredRequestsPerSession`.

A Server that would exceed a parking limit **shall** either answer the request synchronously or refuse it with `Bad_TooManyDeferredRequests`. It **shall not** park a request and then discard it to make room: a parked request that vanishes is indistinguishable, to the Client, from one that was never accepted, and the effect may already be in flight.

**Admission is decided before the work starts, not after.** A Server **shall** reserve the parking slot before it begins any work whose effect it cannot undo and whose outcome it might have to defer. Discovering at the end that there is no room to park the answer is the one outcome the mechanism must never produce: it leaves the effect done and the outcome unreachable, which is the failure this specification exists to remove. Where a Server cannot reserve in advance — because it could not know the work would run long — it **shall** exceed `MaxDeferredRequests` rather than discard the outcome, and **shall** report the excess through `DeferredRequestCount`, whose value is therefore a measurement and not a bound.

**Deferral is opt-in, and the first condition is what makes the rest of this specification safe.** A Client that has never heard of `Complete` cannot collect a parked response, so parking one on its behalf would strand the outcome of work it believes failed — and, worse, invite it to retry an `UpdateCertificate` that is still in flight. A Server therefore answers such a Client exactly as it answers it today: synchronously if it can, and with `Bad_Timeout` if it cannot. That is no worse than the present behaviour, and it is the reason this specification needs no rule about recognising a retry.

### 6.2 The deferral headers

A request **may** carry a `DeferralRequestHeaderDataType` in `RequestHeader.additionalHeader`, which OPC 10000-4 §7.32 reserves for exactly this purpose and which an application that does not understand it ignores. **Its presence is the Client's statement that it implements `Complete`**, and therefore the Server's permission to defer (§6.1). Its members are preferences and never preconditions: a request that carries the structure may still be answered synchronously, and a Server **shall** ignore a member it does not honour rather than fail the request.

A response that reports a request as parked **shall** carry a `DeferralResponseHeaderDataType` in `ResponseHeader.additionalHeader`, which OPC 10000-4 §7.33 reserves the same way.

Both structures are defined by the Part 5 errata.

### 6.3 The retry contract

`RetryAfter` in the response header tells the Client how long to wait before its next `Complete`. It is a hint the Server computes from what it knows — a gateway distributing to five hundred devices knows more about how long that takes than any Client does — and a Client **should** honour it.

Because a Bad `serviceResult` travels as a `ServiceFault`, and an implementation may surface a fault as an exception that discards the header it arrived on, **the retry contract shall not depend on the header alone**. A Server **shall** publish `DefaultRetryAfter` and `MinRetryAfter` in `AsyncServiceCapabilities`, both readable by any Client with a `Read`. A Client that cannot read `additionalHeader` **shall** use `DefaultRetryAfter` before every `Complete`, not only the first.

`MinRetryAfter` is the floor, and it is normative in three directions. A Server **shall not** return a `RetryAfter` below it; **shall not** publish a `DefaultRetryAfter` below it, since otherwise the very Clients this clause protects would be throttled for obeying the only value they can read; and **shall** refuse a `Complete` that arrives sooner than `MinRetryAfter` after the previous `Complete` for the same parked request with `Bad_ServerTooBusy`. Without an enforced floor, a Client that ignores the hint converts a deferral into a poll loop against a Server that deferred because it was already busy.

The floor applies **only while the parked request is `Executing`**. A `Complete` for a request that is `Ready`, `Delivered`, `Cancelled` or `Expired` is answered immediately, however soon it arrives. Throttling a Client that has something to collect would be perverse in general, and specifically incompatible with `DeferredRequestCompletedEventType`, which exists to tell a Client to call `Complete` the moment the response is ready: a floor that outranked readiness would make the Server refuse the call it had just asked for.

Refusing a `Complete` with `Bad_ServerTooBusy` **shall not** affect the parked request: it is not collected, not expired and not cancelled, it is **not** a `Continued` transition and **shall not** be audited as one, and it **shall not** increment `CompleteCount`. The next `Complete` after the floor has elapsed behaves as though the refused one had not been sent, and every observable of the parked request says so.

### 6.4 requestHandle uniqueness

`Cancel` is defined against *"one or more requests"* with a given `requestHandle` (OPC 10000-4 §5.7.5), so OPC UA does not require handles to be unique. `Complete` returns exactly one response and therefore does.

A Client **shall** use a `requestHandle` that is unique among the requests it has outstanding and parked on a Session. A Server **shall** refuse, with `Bad_RequestHandleInUse`, any new request whose `requestHandle` matches a parked request on the same Session, and **shall not** park two requests under one handle on one Session. Handles on different Sessions never collide, because a parked request is never visible outside the Session that created it (§7.5).

A Server **shall not** attempt to recognise a re-sent request as a repeat of a parked one. It has no need to: deferral is opt-in (§6.1), so a Client that receives `Bad_RequestNotComplete` is by construction a Client that knows to call `Complete` rather than to retry. Comparing a new request against a parked one would mean retaining or digesting the whole request body — unbounded for a `Write` carrying thousands of values, and ill-defined across encodings — to solve a problem the opt-in has already removed.

`Complete` and `Cancel` are **exempt** from this clause. Their own `RequestHeader.requestHandle` is the handle of *that* call and has nothing to do with the `requestHandle` parameter naming the parked request, so a collision between the two is not a collision at all. A Server **shall not** refuse a `Complete` or a `Cancel` under this clause.

## 7 Lifecycle

### 7.1 States and the two deadlines

A parked request is `Executing`, then `Ready`, and then terminal: `Delivered`, `Cancelled` or `Expired`. `DeferredRequestState` in the Part 5 errata is the normative enumeration.

`Executing` and `Ready` are the states of a live parked request. The three terminal states are records of one that is not, kept so that `Complete` can say *why* there is nothing new to collect — and, for `Delivered`, so that it can hand over the same answer again (§7.2).

**Two deadlines govern a parked request**, and conflating them is what would make an implementation ambiguous.

The **response deadline** is when the Server discards the response itself:

> `ResponseDeadline` = `ParkedAt` + min(`MaxDeferralTime`, `RequestedDeferralTime` where that is non-zero)

`ExpiryTime` in the response header **shall** state this deadline, and §7.3 discards the response at it. Because it depends only on values fixed when the request was parked, it never moves.

The **record floor** is how long the terminal record outlives the response, so that a Client following the retry contract is told *why* there is nothing to collect rather than being told there never was anything. A Server **shall** keep the record until at least

> `RecordFloor` = the later of `LastDeferralResponseAt` + the `RetryAfter` it last issued for that request, and `ParkedAt` + `MinRetryAfter`

The Client was told when to come back, so the record is still there when it does. Past that floor a Server **may** discard the record and answer `Bad_DeferredRequestUnknown` instead (§5.1).

Neither value bounds retention from below against the events of §7.5: a Session that closes holding a parked response, a user identity that changes, and a Server that shuts down all discard a parked response before its response deadline, and are audited as `Discarded` so that the difference is visible.

### 7.2 An effect happens once; a response may be replayed

A parked response is handed over on `Complete`, and the parked request becomes `Delivered`. It is **not** discarded. Until its response deadline the Server **shall** answer a further `Complete` for the same handle with the same response.

This is deliberate, and it is the difference between a mechanism that solves the problem and one that moves it. A Server cannot know whether a response it transmitted arrived: if the connection fails between transmission and receipt — which is precisely the condition that makes long operations hard — a delete-on-delivery rule leaves the Client with an effect it caused and an outcome it can never learn. That is the failure this specification exists to remove, and reintroducing it at the last step would defeat the whole mechanism.

What happens once is the **effect**. A Server **shall not** execute a parked request a second time under any circumstances, and a replayed response is byte-equivalent to the first, not a re-execution.

After the response deadline a further `Complete` returns `Bad_DeferredRequestExpired`, or `Bad_DeferredRequestUnknown` once the record floor has passed and the Server has discarded the record. A Server **shall not** answer `Bad_DeferredRequestExpired` while the response is still retained and collectable.

### 7.3 Expiry

A Server **shall** discard a parked response at its response deadline (§7.1), whether or not the work has finished and whether or not the response was collected, and **shall** answer a subsequent `Complete` with `Bad_DeferredRequestExpired` for as long as it keeps the record.

The response deadline runs from the moment the request is parked, not from the moment the response becomes ready, so a Client can compute it the instant it receives `Bad_RequestNotComplete` — before it knows anything else about how long the work will take. `ExpiryTime` states the same deadline as an absolute time, so a Client with a skewed clock and a Client with a slow link agree on it.

Expiry discards the **answer**. It does not stop the work, and it **shall not** be read as an undo (§7.6). Where the work later finishes, its outcome still reaches the audit trail as a `Completed` transition (§7.7).

### 7.4 Cancel

`Cancel` (OPC 10000-4 §5.7.5) acts on a parked request as it acts on any other outstanding request: the parked response is discarded and the request counts towards `cancelCount`. A subsequent `Complete` returns `Bad_RequestCancelledByRequest`.

`Cancel` and `Complete` are the two halves of the same decision, which is why `Complete` reuses `Cancel`'s parameter and placement: a Client that has a parked request either wants the answer or does not, and the Service it calls says which.

### 7.5 The Session

A parked request belongs to its issuing Session. A Server **shall** discard every parked response of a Session when that Session closes or is abandoned, **shall** discard them when the Session's user identity changes through a subsequent `ActivateSession`, and **shall** answer a `Complete` from any other Session with `Bad_DeferredRequestUnknown` — not with `Bad_UserAccessDenied`, which would confirm that the handle exists to a caller with no business knowing it.

A parked request **shall not** be treated as Session activity for the purpose of the Session timeout. Work the Server is doing on its own is not evidence that the Client is still there, and a Session that stayed alive because of it would keep a user identity unexamined for as long as the work ran.

**A parked response never leaves its Session.** There is no reclaim by a later Session, by the same user or any other, and this is a deliberate limit rather than an omission. Reclaim across Sessions requires a notion of "the same user" that survives a Session, and OPC UA does not supply one: `ActivateSession` authenticates a token and says nothing about when two tokens presented at different times denote the same person. A Server could only approximate it from the value it uses to select Roles, which is routinely a *group* — so a mechanism built on it would entitle one operator to another operator's certificate-management result. No approximation is worth that.

**The Session is a longer-lived thing than the connection, which is why this costs less than it appears.** A Session survives the loss of the SecureChannel that carried it: OPC UA reconnect logic lets a Client re-establish a broken connection and reactivate the same Session, and the parked response is still there. What is lost is only the case where the Client *process* goes away — and for that, §7.7 already puts the outcome in the audit trail, which is what an operator needs and what a departed Client cannot use anyway.

**Reconnect shall not weaken the channel.** Because a Session can be reactivated on a new SecureChannel, the channel that collects a parked response need not be the one that parked it. A Server **shall** record the SecurityMode in force when a request was parked, and **shall** refuse a `Complete` arriving over a SecureChannel whose SecurityMode is weaker with `Bad_SecurityModeInsufficient` — **without** discarding the parked response, so a Client that reconnects badly can reconnect again properly. Without this, a response parked under `SignAndEncrypt` could be collected in cleartext over a `None` endpoint the Server also exposes, which for the certificate-management responses this specification exists to carry would be a downgrade with no warning.

### 7.6 Authorization, and what a deferral does not do

Deferral moves *when* a response is delivered. It **shall not** move when the request is authorized: a Server **shall** perform every authorization check the Service requires before it parks the request, exactly as it would before executing it. A request the user may not make is refused, not parked.

**Abandoning the answer is not cancelling the effect.** `Cancel` and expiry both discard a parked response. Whether the work that response describes is undone is a property of the Service being deferred and of the Server, and this specification requires nothing of it. A Server **shall not** state or imply that discarding a parked response rolls anything back, and a Client **shall not** assume it.

That is not a gap left open; it is what a distributed operation actually is. A gateway that has already written a TrustList to two hundred devices cannot un-write it because the Client stopped listening, and a mechanism that promised otherwise would be promising something no implementation could keep. What the specification does require instead is that the outcome remains **observable**: §7.7 requires a `Completed` audit transition when the work finishes, whether or not any response was still being held and whether or not anyone collected it.

### 7.7 Auditing

A Server that supports auditing **shall** generate an `AuditDeferredRequestEventType` Event for every transition of a parked request. `DeferredRequestTransition` in the Part 5 errata is the normative enumeration; the table below is the complete set, with the `Outcome` each carries.

| Transition | Raised when | `Outcome` |
|---|---|---|
| `Deferred` | The Server parked the request. | `Good_CompletesAsynchronously` — not yet known. |
| `Continued` | A `Complete` arrived and the response was not ready. A call refused with `Bad_ServerTooBusy` is **not** a `Continued` transition (§6.3). | `Good_CompletesAsynchronously` — not yet known. |
| `Completed` | The work finished and its outcome became known. Raised whether or not a response is still held. | The `serviceResult` of the response. |
| `Delivered` | A Session collected the response, including a replay (§7.2). | The `serviceResult` of the response. |
| `Denied` | A `Complete` was refused because the calling Session was not the one that parked the request (§7.5), or because its SecureChannel was too weak to carry the response. A call refused by the retry floor is **not** a `Denied` transition (§6.3). | The refusing StatusCode. |
| `Cancelled` | A Client abandoned the response with `Cancel`. | The `serviceResult` where the work had finished, `Good_CompletesAsynchronously` where it had not. |
| `Expired` | The response deadline passed. | As `Cancelled`. |
| `Discarded` | The response was discarded before its deadline because the issuing Session closed, its identity changed, or the Server shut down. | As `Cancelled`. |

This is deliberately stricter than the auditing of an ordinary request. A deferral separates the moment an effect is authorized from the moment its outcome is known, and permits the Client that authorized it to walk away in between, so the audit trail is the only record that spans both.

`Completed` is what makes that promise good. `MaxDeferralTime` expires a parked request whether or not the work is done (§7.3), so an `Expired` transition alone would record `Good_CompletesAsynchronously` for the very requests whose outcome nobody else will ever see. `Completed` is raised when the answer exists, even if no Client is left to receive it, and it is therefore the transition an auditor reads to learn what actually happened.

`Denied` is what makes probing visible. A `Complete` for a handle the caller does not own is answered `Bad_DeferredRequestUnknown` and is indistinguishable, to that caller, from a handle that never existed — which is the point. Without a transition of its own, a campaign of such calls would leave no trace at all, and the deliberate opacity of the answer would have cost the Server its only signal.

**The audit Event is itself a disclosure surface.** It names the Session, the user, the Service and the timing of every parked request, so it is a strictly larger disclosure than the `DeferredRequests` Variable the Part 5 errata §6 restricts. A Server **shall** deliver `AuditDeferredRequestEventType` only to Sessions whose Roles include `SecurityAdmin`, and only over an encrypted SecureChannel. A Server that delivers it more widely **shall** omit `RequestHandle`, `ServiceId` and the inherited `SessionId` and `ClientUserId` for a Session that did not issue the request. Restricting the Variable and leaving the Event open would restrict nothing, since the Event carries more and arrives unbidden.

### 7.8 Order of evaluation

Two things can happen to a parked request at once — a `Cancel` while a `Complete` is in flight, a deadline that passes while a response is being handed over — and a Client's view of the outcome must not depend on which the Server noticed first. A Server **shall** apply every transition of a parked request atomically, and **shall** resolve a `Complete` against the state in force when it began, in this order:

1. **A terminal state wins over throttling.** `Ready`, `Delivered`, `Cancelled` and `Expired` are answered immediately; the retry floor is evaluated only for `Executing` (§6.3).
2. **A `Complete` already resolved as `Ready` completes.** A `Cancel` or a deadline that arrives after it began does not turn its answer into a fault; the collection is audited as `Delivered`, and the `Cancel` then applies to the `Delivered` record.
3. **Otherwise `Cancel` wins over expiry**, which wins over a `Complete` that has not yet resolved. A Client that abandoned a response is told it abandoned it, rather than that it ran out of time.

The single-execution rule of §7.2 is unaffected by all of this: whichever order the Server resolves these in, the parked request's effect happened once.

## 8 Interaction with other Services

**Services that are never deferred.** A Server **shall not** defer `Complete`, `Cancel`, `Publish`, `Republish`, `CreateSession`, `ActivateSession`, `CloseSession`, or any Service of the SecureChannel or Discovery Service Sets.

`Complete` and `Cancel` cannot be deferred without recursion. `Publish` is already a long poll and deferring it would replace one waiting mechanism with two. The Session Services establish the very context a parked request is scoped to: a parked `ActivateSession` would be a parked request belonging to a Session that does not yet exist, or whose identity is the thing in question. The Discovery Services are answered without a Session and therefore have nowhere to park.

**Discovering deferral is never deferred.** A `Browse` of `ServerCapabilities` and a `Read` of any Property of the `AsyncServiceCapabilities` Object **shall** be answered synchronously. Deferring them would be a bootstrap loop: a Client cannot learn `DefaultRetryAfter` — the value it needs in order to respond to a deferral at all — from a call that is itself deferred. Every other `Browse` and `Read` may be deferred like any other Service, subject to §6.1.

**`Call`.** Deferral is per request, not per operation. A `Call` carrying several `methodsToCall` is parked as a whole and its response is delivered as a whole, once every operation has settled. A Server **shall not** deliver a partial `CallResponse`.

This costs some parallelism — one slow device holds up the answers about nineteen fast ones — and buys a mechanism that is identical for every Service. Per-operation deferral would need a continuation identifier per operation, a partial-response encoding per Service, and a rule for what a Client does with a response half of whose entries are placeholders; and the Client that wants the fast answers separately can send them as separate requests, which is a thing it can already do.

**`Cancel`.** Covered by §7.4. A `Cancel` naming a handle that identifies both an in-flight request and a parked one cancels both, and counts both.

**Subscriptions.** Unaffected. A Client that would rather be told than ask subscribes to `DeferredRequestCompletedEventType` on the Server Object (Part 5 errata) and calls `Complete` once, when there is something to collect. The Event is an optimization of the retry contract and never a replacement: a Server **shall** honour a `Complete` that arrives without one, and a Client that receives no Event **shall** fall back on `RetryAfter`.

**Server shutdown.** A Server that is shutting down **shall** discard its parked responses, **shall** audit each as `Discarded`, and **should** answer any `Complete` that arrives with `Bad_Shutdown`. Parked responses are not required to survive a restart; the response deadline is the only guarantee a Client has, and it is bounded.

## 9 StatusCodes

Five StatusCodes are new. The most important one is not.

| Symbolic id | Meaning |
|---|---|
| `Bad_DeferralNotSupported` | `Complete` was called on a Server that does not defer requests. |
| `Bad_DeferredRequestUnknown` | No parked request with that `requestHandle` is known to the calling Session. |
| `Bad_DeferredRequestExpired` | A parked request with that `requestHandle` existed and the Server discarded it. |
| `Bad_TooManyDeferredRequests` | A parking limit would be exceeded, and the Server could not answer synchronously. |
| `Bad_RequestHandleInUse` | A new request carries a `requestHandle` that already identifies a parked request on the same Session (§6.4). |

Numeric values are **provisional**; final assignments are made by the OPC Foundation alongside the existing StatusCode registry.

The following are existing StatusCodes, reused:

| Symbolic id | Reused as |
|---|---|
| `Bad_RequestNotComplete` | *"The request has not been processed by the server yet."* Already OPC UA's poll-again code, defined for the pull-management `FinishRequest` Method of OPC 10000-12. Deferral generalizes the pattern it was written for, so it generalizes the code rather than adding a synonym beside it. |
| `Bad_RequestCancelledByRequest` | Returned by `Complete` for a parked request abandoned with `Cancel`, which is what the code already describes. |
| `Bad_ServerTooBusy` | Returned by `Complete` when it arrives sooner than `MinRetryAfter` after the previous one. |
| `Bad_Shutdown` | Returned by `Complete` when the Server is shutting down and has discarded its parked responses. |
| `Bad_ServiceUnsupported` | Returned for `Complete` by a Server that does not implement the Service, exactly as for any unimplemented Service. It is what distinguishes *"I do not have this Service"* from `Bad_DeferralNotSupported`, which says *"I have it, and there is nothing I would defer"*. |
| `Bad_SecurityModeInsufficient` | Returned when `DeferredRequests` is read over an unencrypted SecureChannel (Part 5 errata §6), and when a `Complete` arrives over a SecureChannel weaker than the one its request was parked on (§7.5). |
| `Good_CompletesAsynchronously` | Carried as the `Outcome` of a `Deferred` audit transition, whose result is not yet known. This specification adds no new use of it on the Service path: a deferred request is reported by `Bad_RequestNotComplete`, because a Client that does not implement `Complete` must not read a deferral as a success. |

## 10 Conformance units

| Conformance unit | Requires | Content |
|---|---|---|
| `ASE-Execution` | `ASE-Model` | `Complete` (§5), the deferral rules of §6 including the opt-in and the retry contract, the lifecycle of §7 excluding §7.7 auditing, the `CompleteRequest`, `CompleteResponse`, `DeferralRequestHeaderDataType`, `DeferralResponseHeaderDataType` and `DeferredRequestState` DataTypes defined by the Part 5 errata, and the StatusCodes of §9. |
| `ASE-Model` | `ASE-Execution` | `AsyncServiceCapabilitiesType` and its well-known `AsyncServiceCapabilities` instance, defined by the Part 5 errata. |
| `ASE-Diagnostics` | `ASE-Execution` | `AsyncServiceDiagnostics` and its per-Session projection, defined by the Part 5 errata. |
| `ASE-CompletionEvents` | `ASE-Execution` | `DeferredRequestCompletedEventType` (Part 5 errata). |
| `ASE-Auditing` | `ASE-Execution` | `AuditDeferredRequestEventType` on every transition, with the outcomes and the delivery restriction of §7.7. |

`ASE-Model` and `ASE-Execution` **require each other**, and are two units rather than one because the model and the Services land in different Parts. Neither is claimable alone: a Server that published `AsyncServiceCapabilities` without implementing `Complete` would be advertising limits on something it does not do, and a Server that deferred without publishing the Object would contradict §5 of the Part 5 errata, which makes the Object's absence the statement that a Server never defers.

### 10.1 Test assertions

Deferral cannot be provoked by a Service call: no legal request obliges a Server to be slow. Every assertion below whose stimulus says *defer* therefore presumes a **test operation** — a Node the Server under test exposes whose invocation the test harness can make outlast the Client's `timeoutHint`, and which the Server lists in `DeferrableServices`. Providing one is a precondition of testing this specification, in the same way that a testable alarm is a precondition of testing OPC 10000-9.

| Id | Assertion | Stimulus | Expected |
|---|---|---|---|
| ASE-001 | A Server that never defers says so by omission | Browse `ServerCapabilities` on a Server claiming none of these units | No `AsyncServiceCapabilities` Object |
| ASE-002 | `Complete` is refused where nothing can be deferred | `Complete` with any handle, on a Server claiming none of these units | `Bad_ServiceUnsupported`, or `Bad_DeferralNotSupported` where the Service is implemented but no Service is deferrable (§5.1) |
| ASE-003 | An unactivated Session cannot collect | `Complete` before `ActivateSession` | `Bad_SessionNotActivated` |
| ASE-004 | An unknown handle is refused | `Complete` with a handle never used | `Bad_DeferredRequestUnknown` |
| ASE-005 | A deferral is reported as Bad, not Good | Invoke the test operation | `Bad_RequestNotComplete`, not `Good_CompletesAsynchronously` |
| ASE-006 | The deferral header rides the fault | Read `ResponseHeader.additionalHeader` of the deferred response | A `DeferralResponseHeaderDataType` whose `RequestHandle` matches the request |
| ASE-007 | `RetryAfter` respects the floor | Compare `RetryAfter` with `MinRetryAfter` | `RetryAfter` ≥ `MinRetryAfter` |
| ASE-007a | The published fallback respects the floor | Read `DefaultRetryAfter` and `MinRetryAfter` | `DefaultRetryAfter` ≥ `MinRetryAfter` (§6.3) |
| ASE-008 | The floor is enforced while executing | Two `Complete` calls separated by less than `MinRetryAfter`, while the test operation is still running | First returns `Bad_RequestNotComplete`; second returns `Bad_ServerTooBusy` |
| ASE-009 | A refused `Complete` is inert | After ASE-008, wait `MinRetryAfter`, then `Complete` and read the diagnostics record | Answered normally; `CompleteCount` counts the permitted calls only, and no `Continued` audit Event was raised for the refused one (§6.3). Requires `ASE-Diagnostics` and `ASE-Auditing` |
| ASE-010 | `Complete` returns the parked Service's response | Defer a `Call` that will succeed, let it finish, `Complete` | A `CallResponse`, with `ResponseHeader.requestHandle` equal to the `Complete` request's handle |
| ASE-010a | The floor never delays a ready response | `Complete` immediately after `DeferredRequestCompletedEventType` arrives, sooner than `MinRetryAfter` after the previous `Complete` | The parked response, not `Bad_ServerTooBusy` (§6.3) |
| ASE-010b | A parked failure is distinguishable from a `Complete` failure | Defer an operation that will fail with `Bad_ServerTooBusy`, let it finish, `Complete` | A `CompleteResponse` with `serviceResult` `Good` and `deferredServiceResult` `Bad_ServerTooBusy`, never a bare `ServiceFault` (§5.1) |
| ASE-011 | A collected response is replayed, not destroyed | `Complete` twice after collection, both before the response deadline | Both return the same response; the effect happened once (§7.2) |
| ASE-011a | The effect is not repeated by replay | Compare the observable effect after ASE-011 with its state after the first collection | Unchanged |
| ASE-012 | An expired response is distinguishable | Let the response deadline pass, then `Complete` before the record floor elapses | `Bad_DeferredRequestExpired`, answered without the retry floor delaying it (§6.3, §7.1) |
| ASE-013 | `Cancel` abandons a parked response | `Cancel` the handle, then `Complete` | `cancelCount` ≥ 1, then `Bad_RequestCancelledByRequest` |
| ASE-013a | `Cancel` and `Complete` are not refused for handle collision | `Complete` and `Cancel` whose own `RequestHeader.requestHandle` equals the parked handle | Both answered normally, never `Bad_RequestHandleInUse` (§6.4) |
| ASE-014 | A handle collision is refused | Issue a new request reusing a handle parked on the same Session | `Bad_RequestHandleInUse`, and the parked response is unaffected (§6.4) |
| ASE-015 | A Client that does not opt in is never deferred | Invoke the test operation without a `DeferralRequestHeaderDataType` | A synchronous answer or `Bad_Timeout`, never `Bad_RequestNotComplete` (§6.1) |
| ASE-016 | Another Session cannot collect | `Complete` the handle from a second Session | `Bad_DeferredRequestUnknown`, indistinguishable from an unknown handle |
| ASE-016a | A completion Event reaches only the issuing Session | Subscribe two Sessions of different users to the Server Object, park a request as one | Only the issuing Session receives the Event; the other observes neither `RequestHandle` nor `ServiceResult` (Part 5 errata) |
| ASE-016b | A refused collection is audited | `Complete` a handle parked by another Session | `Bad_DeferredRequestUnknown`, and a `Denied` audit transition naming the calling Session (§7.7) |
| ASE-017 | Session close discards | Close the Session, reconnect, `Complete` | `Bad_DeferredRequestUnknown`, and a `Discarded` audit transition |
| ASE-017a | A parked response survives a reconnect | Park a request, drop the SecureChannel, reactivate the same Session on a new one, `Complete` | The parked response (§7.5) |
| ASE-017b | A reconnect may not weaken the channel | Park over `SignAndEncrypt`, reactivate the Session over a `None` endpoint, `Complete` | `Bad_SecurityModeInsufficient`, and the parked response is still collectable over an encrypted channel (§7.5) |
| ASE-018 | Identity change discards | `ActivateSession` with a different user, then `Complete` | `Bad_DeferredRequestUnknown` (§7.5) |
| ASE-019 | A parked request is not Session activity | Park a request, issue no Service call for the Session timeout plus one `MinRetryAfter`, then call any Service | `Bad_SessionIdInvalid` (§7.5) |
| ASE-020 | Authorization precedes parking | Invoke the test operation as a user who may not | `Bad_UserAccessDenied`, not `Bad_RequestNotComplete` |
| ASE-021 | Excluded Services are never deferred | Under saturation, issue every Service §8 excludes, and a `Read` of `AsyncServiceCapabilities` | Never `Bad_RequestNotComplete` (§8) |
| ASE-022 | A parking limit is handled before the work starts | Park `MaxDeferredRequestsPerSession`, then invoke the test operation once more | Either `Bad_TooManyDeferredRequests` with `RejectedCount` increased by one, or a synchronous result with `RejectedCount` unchanged. Never a lost request (§6.1) |
| ASE-023 | A partial response is never delivered | Defer a `Call` with one fast and one slow operation | One `CallResponse` after both settle (§8) |
| ASE-024 | Completion is auditable without collection | Park a request, let the work finish, then let the response deadline pass uncollected | A `Completed` transition carrying the `serviceResult`, then an `Expired` transition (§7.7) |
| ASE-024a | A late outcome still reaches the trail | Park a request whose work outlasts the response deadline, let it expire, then let the work finish | `Expired` with `Outcome` `Good_CompletesAsynchronously`, then `Completed` carrying the real `serviceResult` (§7.7) |
| ASE-025 | The audit Event is not a public feed | As a user without `SecurityAdmin`, subscribe to `AuditDeferredRequestEventType` and park a request as another user | Either no Event, or an Event without `RequestHandle`, `ServiceId`, `SessionId` and `ClientUserId` (§7.7) |
| ASE-026 | The model states the encryption restriction | Read the `AccessRestrictions` Attribute of `DeferredRequests` | The `EncryptionRequired` bit is set (Part 5 errata §6) |
| ASE-027 | An unsupported preference is reported, not honoured silently | Set `RequestedDeferralTime` beyond `MaxDeferralTime` and invoke the test operation | The request is deferred and `ExpiryTime` is no later than `MaxDeferralTime` from parking (§7.1) |
| ASE-028 | Diagnostics are projected per Session | Park requests from two Sessions of different users and read `DeferredRequests` as each, over an encrypted SecureChannel | Each Session sees only its own records (Part 5 errata) |
| ASE-028a | Diagnostics require encryption | Read `DeferredRequests` over a SecureChannel whose SecurityMode is `None` | `Bad_SecurityModeInsufficient` (Part 5 errata) |

## 11 Insertion into OPC 10000-4 v1.05.07

| Draft clause | Target clause in OPC 10000-4 | Notes |
|---|---|---|
| §4 Overview | New `5.7.6.1 Overview` | Introduces deferral and its relationship to `Cancel`. |
| §5.1 `Complete` | New `5.7.6 Complete`, with `5.7.6.2 Parameters` and `5.7.6.3 Service results` | Parameter tables in the standard Request/Response form. `CompleteRequest` and `CompleteResponse` are added to the Service message DataTypes alongside every other Service's pair. |
| §5.2 Polymorphic response | `7.34 ServiceFault`, and `5.7.6.2` | A statement that the existing substitution rule already admits a response other than the declared one, cross-referenced from the Service. |
| §6.1, §6.2 Opt-in and the headers | `7.32 RequestHeader` and `7.33 ResponseHeader` | The two structures are named as defined uses of `additionalHeader`, and the presence of the request header is what permits a deferral. The DataTypes themselves are defined by the Part 5 errata. |
| §6.4 Handles | `7.32 RequestHeader`, `requestHandle` | The uniqueness obligation belongs where `requestHandle` is defined. |
| §7.5 The Session | `5.7 Session Service Set` | The effects of Session close, reconnect and identity change are stated where those operations are defined, and cross-referenced from `5.7.6`. |
| §7.6 Authorization | `OPC 10000-2` and the `RolePermissions` text of OPC 10000-3 | No new mechanism; a statement that the existing one governs and runs before parking. |
| §7.7 Auditing | `Audit Events` clause of OPC 10000-5 | The audit EventType is defined by the Part 5 errata; the obligation to raise it, the transition/outcome table and the delivery restriction belong here. |
| §7.8 Order of evaluation | `5.7.6`, beside the Service | A linearization rule, stated once for every transition. |
| §8 Interaction | `5.5 Discovery Service Set`, `5.6 SecureChannel Service Set`, `5.7 Session Service Set`, `5.14 Subscription Service Set` | The exclusion list is stated where the excluded Services are defined. |
| §9 StatusCodes | Common Service Result Codes (Table 178) and the numeric registry maintained with OPC 10000-6 | Five new symbolic ids; `Bad_RequestNotComplete` gains a second documented use. Every `Complete` result is service-level, so Table 179 is not involved. |
| §10 Conformance units | OPC 10000-7 | Five new conformance units and the Profiles that group them. |

`Complete` is proposed as a new `5.7.6`, after `5.7.5 Cancel`, so the existing Service Set numbering is unchanged.
