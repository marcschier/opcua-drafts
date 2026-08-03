# OPC UA Part 5 — Asynchronous Service Model

**Working draft for submission to the OPC Foundation Working Group**
**Proposed addition to:** OPC 10000-5 Information Model v1.05.06
**Namespace:** `http://opcfoundation.org/UA/` (base OPC UA namespace)
**Version:** 0.1.0 · **Date:** 2026-08-03

> **Status — working draft.** This document proposes the information model for **asynchronous Service execution**: the Object a Client reads to learn whether and how a Server defers requests, the Object an operator reads to see what it is holding, the DataTypes the deferral headers carry, and the Events that report completion and audit the lifecycle. The Services themselves are in the [Part 4 errata](OPC-UA-Part4-Async-Service-Execution.md). Numeric NodeIds are **provisional**, drawn from the 70000+ block; final identifiers are assigned by the OPC Foundation. Nothing here is normative or endorsed by the OPC Foundation.

---

## 1 Scope

This specification defines two ObjectTypes and their well-known instances, five Structures, two Enumerations and two EventTypes, added to the base OPC UA namespace.

Together they let a Client discover, by browsing and reading alone, whether a Server defers requests at all, which Services it may defer, how long it holds a parked response, how often it will accept a `Continue`, and whether a parked response can outlive the Session that asked for it — all before it issues a request that might be deferred. They let an operator see what the Server is currently holding and for whom. And they let a Client learn that a parked response is ready by Subscription instead of by polling.

It does not define the `Continue` Service, the deferral rules or the StatusCodes, which are in the Part 4 errata.

## 2 Normative references

- [OPC 10000-3](https://reference.opcfoundation.org/specs/OPC-10000-3/) — Address Space Model.
- [OPC 10000-4 v1.05.07](https://reference.opcfoundation.org/specs/OPC-10000-4/) — Services.
- [OPC 10000-5 v1.05.06](https://reference.opcfoundation.org/specs/OPC-10000-5/) — Information Model.
- [OPC 10000-6](https://reference.opcfoundation.org/specs/OPC-10000-6/) — Mappings.
- [OPC UA Part 4 — Asynchronous Service Execution](OPC-UA-Part4-Async-Service-Execution.md) — the companion Services errata.

## 3 Terms, definitions and abbreviations

The terms of the Part 4 errata §3 apply. Key words **shall**, **should**, **may** and **shall not** are to be interpreted as in the ISO/IEC directives.

## 4 Overview

The model exists to make three questions answerable before anything goes wrong.

**"Will this Server ever answer me late?"** A Client that cannot handle a deferral needs to know that before it calls, not after. The absence of the `AsyncServiceCapabilities` Object is the Server's answer, and it is a Browse rather than a failed call.

**"How long do I have, and how often may I ask?"** The Part 4 errata carries a per-request hint in `ResponseHeader.additionalHeader`, and a Bad service result travels as a `ServiceFault`, which some implementations surface as an exception that discards the header with it. The retry contract therefore cannot rest on the header alone: `DefaultRetryAfter` and `MinRetryAfter` are Properties any Client can `Read`, and they are what makes the contract reachable for every Client rather than only for the well-equipped ones.

**"What is this Server holding, and for whom?"** A Server that parks requests accumulates state on behalf of Clients that may never come back. `AsyncServiceDiagnostics` is what distinguishes a Server that is slow from a Server whose Clients do not collect.

## 5 Server capabilities

`AsyncServiceCapabilitiesType`, instanced as the well-known `AsyncServiceCapabilities` Object under `ServerCapabilities`, is the Server-wide answer. **Its absence is how a Server says it never defers a request** — a Client checks for the Object rather than discovering the fact from a `Bad_RequestNotComplete` it was not expecting.

`DeferrableServices` lists the request message DataTypes the Server may defer, **exhaustively**. A Service absent from the list is never deferred. The list is exhaustive rather than open because the alternative — an empty array meaning "anything" — would make the useful reading and the uninitialized reading identical, and a Client cannot tell a Server that defers everything from a Server that has not filled the Property in.

`DurableDeferralSupported` and `MaxDurableDeferralTime` are both Mandatory, and `MaxDurableDeferralTime` **shall** be `0` exactly when `DurableDeferralSupported` is FALSE. The pair is stated this way rather than as one Mandatory Boolean and one Optional Duration because `ASE-Durable` is a conformance unit that has to be testable: a Server that simply omitted the Duration would satisfy any test written against it.

Every member of this type is Mandatory for the same reason. A conformance unit that named an Optional member could not be verified against a legal Server, because omitting the member would be conformant. Where a capability is genuinely absent, it is expressed as a **value** — `0`, FALSE, an empty array — which a Client can read and act on.

## 6 Diagnostics

`AsyncServiceDiagnosticsType`, instanced as `AsyncServiceDiagnostics` under `ServerDiagnostics`, carries the counters and one record per parked request.

`ExpiredCount` and `ContinueCount` are the two an operator watches. A rising `ExpiredCount` says Clients are deferring and never returning, which is a Client defect that presents as Server memory. A high `ContinueCount` against a long `StartTime` says a Client is polling a Server that asked it not to.

**`DeferredRequests` is security-related.** It names the Session behind every parked request, the Service it called, when it called it and how often it has asked since. Aggregated across a Server, that is a record of which user is doing what long-running work and when — including work whose response they have not yet seen. A Server **shall** restrict the Variable to an encrypted SecureChannel, answering `Bad_SecurityModeInsufficient` otherwise, and **shall** express that restriction through the `AccessRestrictions` Attribute so a Client can discover it by reading rather than by failing.

**Two projections, not one.** A Server **shall** project `DeferredRequests` per Session by the single entitlement predicate of the Part 4 errata §7.5 — a Session sees the records of the parked requests it is entitled to collect, and no others. A Server **shall** additionally allow a Session whose Roles include `SecurityAdmin` to read **every** record, because an operator diagnosing a Server full of uncollected responses is by definition not the user who parked them, and a projection that hid them from the only person who can act would make the diagnostics decorative. The administrative projection is a deliberate, Role-gated widening and not a hole: it is the same trade OPC 10000-5 §6.3.4 makes for `SessionSecurityDiagnosticsArray`.

The counters are Server-wide and are not projected. They aggregate without naming anyone, so they carry no information about an individual Session — which is why they can be read by an operator who is entitled to neither projection of `DeferredRequests`.

`ReclaimedCount` is `0` on a Server whose `DurableDeferralSupported` is FALSE, rather than absent, so an operator reading the diagnostics of two Servers compares the same set of counters.

## 7 DataTypes

`ContinueRequest` and `ContinueResponse` are the Service message types of the `Continue` Service, modelled as Structures with the three encodings exactly as every other Service's request and response pair is. They are in the model rather than only in the Service definition for a concrete reason: `AsyncServiceCapabilities.DeferrableServices` names a Service by the NodeId of its request message, so a Service absent from the model could not be named at all.

`ContinueResponse` carries `DeferredServiceResult` because a parked request that *failed* has no response message of its own to return, and a bare `ServiceFault` could not be told apart from a `Continue` that failed on its own account. The Part 4 errata §5.1 sets out why that distinction is load-bearing.

`DeferralRequestHeaderDataType` and `DeferralResponseHeaderDataType` are the two defined uses of the `additionalHeader` member that OPC 10000-4 §7.32 and §7.33 reserve. An application that does not understand them ignores them, which is what those clauses already require, so a Server that sends the response header to a Client that has never heard of it loses nothing.

The request header expresses a **preference and never a precondition** (Part 4 errata §6.2). A Server that cannot honour `RequestedDeferralTime` revises it down — never up, and never beyond `MaxDeferralTime` — and a Server that cannot honour `RequestDurable` reports `Durable` as FALSE in the response rather than failing the request: a Client that asks for something is never worse off than a Client that asks for nothing.

`EstimatedCompletionTime` is a forecast and `ExpiryTime` is a deadline. Only the second binds. They are separate members rather than one, because a Server that can estimate and a Server that cannot both have a deadline, and folding them together would make the honest answer — *I do not know when, but you have until this time* — inexpressible.

`DeferredRequestState` describes a parked request. `DeferredRequestTransition` describes what happened to one. They are separate enumerations because `Continued` is an action that leaves the state unchanged, and an audit trail that recorded only states would not show that a Client asked; and because `Completed` and `Discarded` are things that happen to a request without corresponding to any state it rests in.

## 8 Events

`DeferredRequestCompletedEventType` is raised on the Server Object when a parked response becomes ready. It is an optimization of the retry contract, never a replacement for it: a Client that subscribes calls `Continue` once, when there is something to collect, and a Client that does not is unaffected because `RetryAfter` still governs.

The Event names a parked request, so it **shall** reach only the Sessions the entitlement predicate of the Part 4 errata §7.5 admits — the issuing Session, and for a durable request whose Session has ended, a Session of the same principal. A Server **shall not** deliver it to any other Session, however that Session's Event filter is written. Delivering it more widely would tell every subscriber which user is running which long operation, which is the same disclosure §6 restricts `DeferredRequests` to prevent, arriving by a different route.

`ServiceResult` carries the **service-level** `serviceResult` of the parked response and nothing more. For a Service whose response carries per-operation results — `Call`, `Write`, `HistoryUpdate` — a `Good` `ServiceResult` says the request was processed, not that every operation in it succeeded, and a Client that needs the per-operation outcomes **shall** call `Continue` and read them. What the Event saves is the polling, not the collection.

A Server **shall** hold the response until it is collected, cancelled or expires, whether or not the Event was delivered and whether or not any Client read it: a Client that receives the Event is not thereby deemed to have collected anything.

`AuditDeferredRequestEventType` reports every transition. It subtypes `AuditSessionEventType` and carries its own `RequestHandle`, following `AuditCancelEventType`, which is the existing audit event for the other Service that acts on an outstanding request by its handle.

Its `Outcome` is the `serviceResult` of the parked response and is **not** the audit result. The inherited `Status` says whether the audited action succeeded — whether the `Cancel` was accepted, whether the `Continue` was answered — which is a different question from what the deferred Service returned. A `Delivered` transition with `Status` TRUE and an `Outcome` of `Bad_UserAccessDenied` is a successful delivery of a refusal, and both halves matter.

Where the outcome is not yet known — a `Deferred` transition, and an `Expired` transition for a request whose work had not finished — `Outcome` is `Good_CompletesAsynchronously`. That is the one StatusCode in OPC UA that says *the answer is not here yet* without claiming anything about what it will be, and an audit reader needs to tell "expired holding a result" from "expired still working".

## 9 Conformance units

| Conformance unit | Requires | Content |
|---|---|---|
| `ASE-Model` | `ASE-Execution` | `AsyncServiceCapabilitiesType` and the well-known `AsyncServiceCapabilities` Object. |
| `ASE-Execution` | `ASE-Model` | The `Continue` Service and the deferral rules, defined by the Part 4 errata, together with `ContinueRequest`, `ContinueResponse`, `DeferralRequestHeaderDataType`, `DeferralResponseHeaderDataType` and `DeferredRequestState`. |
| `ASE-Durable` | `ASE-Execution`, `ASE-Auditing` | Durable deferral, defined by the Part 4 errata. |
| `ASE-Diagnostics` | `ASE-Execution` | `AsyncServiceDiagnosticsType`, the well-known `AsyncServiceDiagnostics` Object, `DeferredRequestDiagnosticsDataType` and the two projections of §6. |
| `ASE-CompletionEvents` | `ASE-Execution` | `DeferredRequestCompletedEventType` and the delivery restriction of §8. |
| `ASE-Auditing` | `ASE-Execution` | `AuditDeferredRequestEventType`, `DeferredRequestTransition`, and the obligation to raise an Event on every transition. |

`ASE-Model` and `ASE-Execution` require each other and neither is claimable alone, because §5 makes the absence of the `AsyncServiceCapabilities` Object the statement that a Server never defers: a Server that published the Object without implementing `Continue` would be advertising limits on something it does not do. A Server that exposes the Object **shall** claim both.

## 10 NodeSet validation

The NodeSet, the NodeId CSV and Annex A are generated from `tools/build_model.py` and **shall not** be hand-edited. `tools/validate_local.py` checks XML well-formedness, that every own NodeId lies in the reserved provisional ranges and is unique, that the CSV and the NodeSet agree on every NodeId and NodeClass, that every reference target resolves to a node defined here or to a known base UA NodeId, that every type carries an inverse `HasSubtype`, that every declared member is Mandatory, that every Structure carries its three DataTypeEncoding Objects and every Enumeration its `EnumStrings`, that the two well-known instances are components of `ServerCapabilities` and `ServerDiagnostics`, that every conformance unit the model emits is named in a specification document and every unit a document names is declared by the generator, that every type the model declares is described in prose and every type name the prose uses exists in the model, that every StatusCode the documents use is either new here or reused deliberately, and that Annex A is embedded verbatim in this document. It runs with no untracked base data; the cross-check against the base UA NodeId table is skipped when that table is absent.

## 11 Insertion into OPC 10000-5

| Draft clause | Target in OPC 10000-5 | Notes |
|---|---|---|
| §5 | `ServerCapabilitiesType` | `AsyncServiceCapabilities` added as an Optional component, so its absence remains a valid Server. |
| §6 | `ServerDiagnosticsType` | `AsyncServiceDiagnostics` added as an Optional component, beside the existing diagnostics Objects. |
| §7 | Standard DataTypes | Two Enumerations and five Structures, with `Default Binary`, `Default XML` and `Default JSON` encodings. `ContinueRequest` and `ContinueResponse` join the Service message DataTypes; the two header Structures are additionally referenced from the `additionalHeader` clauses of OPC 10000-4 §7.32 and §7.33. |
| §8 | Standard EventTypes and Audit Events | `DeferredRequestCompletedEventType` beside the other Server Object Events; `AuditDeferredRequestEventType` beside `AuditCancelEventType`. |
| §9 | OPC 10000-7 | Conformance units and the Profiles that group them. |
| Annex A | OPC 10000-5 node tables and the base `Opc.Ua.NodeSet2.xml` | The generated overlay is merged into the base NodeSet; provisional NodeIds are replaced by assigned ones. |

---

<!-- BEGIN GENERATED: model-reference -->

<a id="annex-a"></a>

## Annex A — Information model

This annex is the normative node reference. It is generated from `core-specs/async-services/tools/build_model.py` and always matches `Opc.Ua.AsyncServices.NodeSet2.xml`. Every node is a proposed **addition to the base OPC UA namespace** `http://opcfoundation.org/UA/` (namespace index 0), so BrowseNames are unqualified and NodeIds are plain `i=<n>`. The numeric NodeIds are **provisional**, drawn from the 70000+ block; final identifiers are assigned by the OPC Foundation. The **Declared in** column marks members inherited from a supertype.

### Type overview

| NodeId | BrowseName | NodeClass | Subtype of |
|---|---|---|---|
| i=70000 | [AsyncServiceCapabilitiesType](#type-AsyncServiceCapabilitiesType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| i=70001 | [AsyncServiceDiagnosticsType](#type-AsyncServiceDiagnosticsType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| i=70010 | [DeferredRequestCompletedEventType](#type-DeferredRequestCompletedEventType) | ObjectType | [BaseEventType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.4) |
| i=70011 | [AuditDeferredRequestEventType](#type-AuditDeferredRequestEventType) | ObjectType | [AuditSessionEventType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.4) |
| i=70030 | [DeferredRequestState](#type-DeferredRequestState) | DataType | [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.14) |
| i=70031 | [DeferredRequestTransition](#type-DeferredRequestTransition) | DataType | [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.14) |
| i=70032 | [DeferralRequestHeaderDataType](#type-DeferralRequestHeaderDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32) |
| i=70033 | [DeferralResponseHeaderDataType](#type-DeferralResponseHeaderDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32) |
| i=70034 | [DeferredRequestDiagnosticsDataType](#type-DeferredRequestDiagnosticsDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32) |
| i=70035 | [ContinueRequest](#type-ContinueRequest) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32) |
| i=70036 | [ContinueResponse](#type-ContinueResponse) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32) |

### Object types

<a id="type-AsyncServiceCapabilitiesType"></a>

#### AsyncServiceCapabilitiesType  (i=70000)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

Server-wide deferral limits and capabilities, exposed as the AsyncServiceCapabilities component of ServerCapabilities. Its absence is how a Server says it never defers a request, so a Client learns that from one Browse rather than from a Bad_RequestNotComplete it did not expect.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| MaxDeferredRequests | Variable | UInt32 | Mandatory | AsyncServiceCapabilitiesType | The greatest number of parked responses the Server holds at one time, across every Session. A request that would take the Server past this number is answered synchronously or refused with Bad_TooManyDeferredRequests; it is never silently dropped. |
| MaxDeferredRequestsPerSession | Variable | UInt32 | Mandatory | AsyncServiceCapabilitiesType | The greatest number of parked responses the Server holds for one Session. It bounds what a single Client can reserve, so one Client polling slowly cannot exhaust MaxDeferredRequests for every other Client. |
| MaxDeferralTime | Variable | [Duration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.13) | Mandatory | AsyncServiceCapabilitiesType | The longest a Server holds a parked response before discarding it. It starts when the request is parked, not when the response becomes ready, so a Client can compute the deadline from the moment it receives Bad_RequestNotComplete. |
| DefaultRetryAfter | Variable | [Duration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.13) | Mandatory | AsyncServiceCapabilitiesType | The interval a Client waits before its first Continue when it cannot read the DeferralResponseHeaderDataType carried in ResponseHeader.additionalHeader. Every Client can read this Property, so the retry contract does not depend on a header that a stack may discard with the fault that carries it. |
| MinRetryAfter | Variable | [Duration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.13) | Mandatory | AsyncServiceCapabilitiesType | The shortest interval the Server accepts between two Continue calls for the same parked request. A Client that calls more often is refused with Bad_ServerTooBusy. Without a published floor, a Client that ignores RetryAfter turns a deferral into a poll loop against the very Server that deferred because it was busy. |
| DeferrableServices | Variable | [NodeId](https://reference.opcfoundation.org/specs/OPC-10000-3/8.2)\[\] | Mandatory | AsyncServiceCapabilitiesType | The DataType NodeIds of the request messages this Server may defer, listed exhaustively. A Service absent from the list is never deferred, so a Client knows before it calls whether an answer can arrive late. |
| DurableDeferralSupported | Variable | Boolean | Mandatory | AsyncServiceCapabilitiesType | TRUE when the Server can hold a parked response beyond the Session that issued the request, for reclaim by a later Session of the same user identity. |
| MaxDurableDeferralTime | Variable | [Duration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.13) | Mandatory | AsyncServiceCapabilitiesType | The longest a Server holds a durable parked response, measured from the moment the issuing Session closed. It is 0 exactly when DurableDeferralSupported is FALSE, so the pair is readable and testable together rather than one being present and the other absent. |

<a id="type-AsyncServiceDiagnosticsType"></a>

#### AsyncServiceDiagnosticsType  (i=70001)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

Counters and per-request records for deferred requests, exposed as the AsyncServiceDiagnostics component of ServerDiagnostics. It is what an operator reads to tell a Server that is slow from a Server whose Clients never collect what they asked for.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| DeferredRequestCount | Variable | UInt32 | Mandatory | AsyncServiceDiagnosticsType | The number of parked responses the Server currently holds, in any state. |
| TotalDeferredCount | Variable | [Counter](https://reference.opcfoundation.org/specs/OPC-10000-3/8.11) | Mandatory | AsyncServiceDiagnosticsType | The number of requests the Server has parked since it started. |
| CompletedCount | Variable | [Counter](https://reference.opcfoundation.org/specs/OPC-10000-3/8.11) | Mandatory | AsyncServiceDiagnosticsType | The number of parked responses collected by a Continue since the Server started. |
| ExpiredCount | Variable | [Counter](https://reference.opcfoundation.org/specs/OPC-10000-3/8.11) | Mandatory | AsyncServiceDiagnosticsType | The number of parked responses discarded because MaxDeferralTime elapsed before they were collected. A rising count is the signature of Clients that defer and never return. |
| CancelledCount | Variable | [Counter](https://reference.opcfoundation.org/specs/OPC-10000-3/8.11) | Mandatory | AsyncServiceDiagnosticsType | The number of parked responses abandoned with Cancel since the Server started. |
| ReclaimedCount | Variable | [Counter](https://reference.opcfoundation.org/specs/OPC-10000-3/8.11) | Mandatory | AsyncServiceDiagnosticsType | The number of parked responses collected by a Session other than the one that issued the request. It is 0 on a Server whose DurableDeferralSupported is FALSE. |
| RejectedCount | Variable | [Counter](https://reference.opcfoundation.org/specs/OPC-10000-3/8.11) | Mandatory | AsyncServiceDiagnosticsType | The number of requests refused with Bad_TooManyDeferredRequests because a parking limit would have been exceeded. |
| DeferredRequests | Variable | [DeferredRequestDiagnosticsDataType](#type-DeferredRequestDiagnosticsDataType)\[\] | Mandatory | AsyncServiceDiagnosticsType | One record per parked response the reading Session is entitled to see. Empty when it holds none. |

### Event types

<a id="type-DeferredRequestCompletedEventType"></a>

#### DeferredRequestCompletedEventType  (i=70010)

*Inherits from:* [BaseEventType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.4)

Raised when a parked response becomes ready to collect. A Client that subscribes to it calls Continue once, when there is something to collect, instead of polling until there is; a Client that cannot subscribe is unaffected, because RetryAfter remains the contract.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| RequestHandle | Variable | [IntegerId](https://reference.opcfoundation.org/specs/OPC-10000-4/7.19) | Mandatory | DeferredRequestCompletedEventType | The requestHandle of the parked request, as the Client sent it in the RequestHeader. It is the only identifier the mechanism uses, so a Client keys the Event to its own outstanding work without holding a Server-assigned ticket. |
| ServiceId | Variable | [NodeId](https://reference.opcfoundation.org/specs/OPC-10000-3/8.2) | Mandatory | DeferredRequestCompletedEventType | The DataType NodeId of the parked request message, so a Client that deferred several different Services can tell which one completed. |
| ServiceResult | Variable | [StatusCode](https://reference.opcfoundation.org/specs/OPC-10000-4/7.38) | Mandatory | DeferredRequestCompletedEventType | The serviceResult the parked response carries. It lets a Client that only needs to know whether the work succeeded skip the Continue entirely. |
| CompletionTime | Variable | [UtcTime](https://reference.opcfoundation.org/specs/OPC-10000-3/8.37) | Mandatory | DeferredRequestCompletedEventType | When the response became ready. |
| ExpiryTime | Variable | [UtcTime](https://reference.opcfoundation.org/specs/OPC-10000-3/8.37) | Mandatory | DeferredRequestCompletedEventType | When the Server discards the parked response. A Client has until this time to call Continue. |

<a id="type-AuditDeferredRequestEventType"></a>

#### AuditDeferredRequestEventType  (i=70011)

*Inherits from:* [AuditSessionEventType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.4)

Audit event for every transition of a parked request. A deferred request separates the moment an effect is authorized from the moment its outcome is known, and the Client that authorized it may never collect the answer, so the audit trail is the only record that spans both. It follows AuditCancelEventType, which is likewise an AuditSessionEventType carrying a requestHandle.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| RequestHandle | Variable | [IntegerId](https://reference.opcfoundation.org/specs/OPC-10000-4/7.19) | Mandatory | AuditDeferredRequestEventType | The requestHandle of the request this transition belongs to. |
| ServiceId | Variable | [NodeId](https://reference.opcfoundation.org/specs/OPC-10000-3/8.2) | Mandatory | AuditDeferredRequestEventType | The DataType NodeId of the deferred request message. |
| Transition | Variable | [DeferredRequestTransition](#type-DeferredRequestTransition) | Mandatory | AuditDeferredRequestEventType | The transition being reported. |
| Outcome | Variable | [StatusCode](https://reference.opcfoundation.org/specs/OPC-10000-4/7.38) | Mandatory | AuditDeferredRequestEventType | The serviceResult of the parked response for a Delivered or Reclaimed transition, and for an Expired transition whose work had finished. It is Good_CompletesAsynchronously wherever the outcome is not yet known: a Deferred transition, and an Expired transition for a request whose work had not finished. It is the service result, not the audit result: the inherited Status Property says whether the audited action succeeded, which is a different question from what the deferred Service returned. |
| Durable | Variable | Boolean | Mandatory | AuditDeferredRequestEventType | TRUE when the parked response survives the Session that issued the request. |

### Data types

<a id="type-DeferredRequestState"></a>

#### DeferredRequestState  (i=70030)

*Subtype of:* [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.14)

The state of a parked request. Delivered, Expired and Cancelled are terminal records rather than live requests: a Server keeps them so that Continue can say why there is nothing new to collect, and so that a response lost on the network can be collected again.

| Name | Value | Description |
|---|---|---|
| Executing | 0 | The Server is still working on the request. Continue returns Bad_RequestNotComplete. |
| Ready | 1 | The response is complete and parked. The next Continue returns it. |
| Expired | 2 | The retention deadline passed before the response was collected and the Server discarded it. Continue returns Bad_DeferredRequestExpired. |
| Cancelled | 3 | The Client abandoned the response with Cancel. Continue returns Bad_RequestCancelledByRequest. |
| Delivered | 4 | The response was collected and is retained for replay until the retention deadline. A Continue returns the same response again, so a Client that lost it to a broken connection is not left with an effect whose outcome it can never learn. |

<a id="type-DeferredRequestTransition"></a>

#### DeferredRequestTransition  (i=70031)

*Subtype of:* [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.14)

The transitions of a parked request, as reported by AuditDeferredRequestEventType. They are transitions rather than states because Continued is an action that leaves the state unchanged, and an audit trail that recorded only states would not show that a Client asked.

| Name | Value | Description |
|---|---|---|
| Deferred | 0 | The Server parked the request and answered Bad_RequestNotComplete. |
| Continued | 1 | A Client called Continue and the response was not yet ready. |
| Delivered | 2 | A Client of the issuing Session collected the parked response, or collected it again by replay. |
| Reclaimed | 3 | A Session other than the one that issued the request collected the parked response. It replaces Delivered for that collection rather than accompanying it, so one collection is one transition. |
| Cancelled | 4 | A Client abandoned the parked response with Cancel. |
| Expired | 5 | The Server discarded the parked response because the retention deadline passed. |
| Completed | 6 | The work finished and its outcome became known. It is raised even when no response is held any longer, which is the only way the outcome of a request that outlived its retention deadline reaches the audit trail. |
| Discarded | 7 | The Server discarded the parked response before its retention deadline because the issuing Session closed, its user identity changed, or the Server shut down. |

<a id="type-DeferralRequestHeaderDataType"></a>

#### DeferralRequestHeaderDataType  (i=70032)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32)

Carried in RequestHeader.additionalHeader. It expresses a preference and never a precondition: the Server decides whether to defer, so a request that carries this structure may still be answered synchronously and a request that omits it may still be deferred.

| Field | DataType | Description |
|---|---|---|
| RequestedDeferralTime | [Duration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.13) | How long the Client would like the response held. The Server revises it down to MaxDeferralTime and never up. 0 means no preference and selects MaxDeferralTime. |
| RequestDurable | Boolean | TRUE asks the Server to make the parked response reclaimable by a later Session of the same user identity. A Server whose DurableDeferralSupported is FALSE ignores it and reports Durable as FALSE in the response header. |

<a id="type-DeferralResponseHeaderDataType"></a>

#### DeferralResponseHeaderDataType  (i=70033)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32)

Carried in ResponseHeader.additionalHeader of every response that reports a request as parked. Because a Bad serviceResult travels as a ServiceFault, this structure is the only place a per-request hint can ride; the Client that cannot read it falls back on DefaultRetryAfter, which every Client can read.

| Field | DataType | Description |
|---|---|---|
| RequestHandle | [IntegerId](https://reference.opcfoundation.org/specs/OPC-10000-4/7.19) | Echo of the requestHandle that identifies the parked request. It is echoed rather than assumed so that a Client whose stack does not surface the RequestHeader it sent can still key the parked request. |
| RetryAfter | [Duration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.13) | How long to wait before the next Continue. Never below MinRetryAfter. |
| ExpiryTime | [UtcTime](https://reference.opcfoundation.org/specs/OPC-10000-3/8.37) | When the Server discards the parked response. |
| EstimatedCompletionTime | [UtcTime](https://reference.opcfoundation.org/specs/OPC-10000-3/8.37) | The Server's estimate of when the response will be ready, or a null DateTime when it cannot estimate. It is a forecast and never a commitment; ExpiryTime is the only deadline that binds. |
| Durable | Boolean | TRUE when the parked response survives the Session that issued the request. |

<a id="type-DeferredRequestDiagnosticsDataType"></a>

#### DeferredRequestDiagnosticsDataType  (i=70034)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32)

One parked request, as reported by AsyncServiceDiagnostics. ContinueCount and StartTime are the two that matter in practice: together they separate a Client that is waiting patiently from one that is polling a Server it was asked not to.

| Field | DataType | Description |
|---|---|---|
| SessionId | [NodeId](https://reference.opcfoundation.org/specs/OPC-10000-3/8.2) | The Session that issued the request. |
| RequestHandle | [IntegerId](https://reference.opcfoundation.org/specs/OPC-10000-4/7.19) | The requestHandle that identifies the parked request within that Session. |
| ServiceId | [NodeId](https://reference.opcfoundation.org/specs/OPC-10000-3/8.2) | The DataType NodeId of the parked request message. |
| State | [DeferredRequestState](#type-DeferredRequestState) | The state of the parked request. |
| StartTime | [UtcTime](https://reference.opcfoundation.org/specs/OPC-10000-3/8.37) | When the Server parked the request. |
| ExpiryTime | [UtcTime](https://reference.opcfoundation.org/specs/OPC-10000-3/8.37) | When the Server discards the parked response. |
| ContinueCount | UInt32 | How many times a Client has called Continue for this request. A call refused with Bad_ServerTooBusy is not counted, because it never examined the request. |
| Durable | Boolean | TRUE when the parked response survives the Session that issued the request. |

<a id="type-ContinueRequest"></a>

#### ContinueRequest  (i=70035)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32)

The Continue Service request. Its DataType NodeId is what AsyncServiceCapabilities.DeferrableServices uses to name a Service, and Continue itself is never deferrable.

| Field | DataType | Description |
|---|---|---|
| RequestHeader | [RequestHeader](https://reference.opcfoundation.org/specs/OPC-10000-4/7.32) | Common request parameters. |
| RequestHandle | [IntegerId](https://reference.opcfoundation.org/specs/OPC-10000-4/7.19) | The requestHandle of the parked request, as it appeared in the RequestHeader of the deferred request. |

<a id="type-ContinueResponse"></a>

#### ContinueResponse  (i=70036)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32)

The Continue Service response, returned when the parked response is itself a failure. A successful Continue for a parked request that succeeded is answered with the parked Service's own response message instead; a Continue that fails on its own account travels as a ServiceFault. This message is what keeps those two apart, which a bare ServiceFault could not: a parked ApplyChanges that failed and a Continue that arrived too soon would otherwise be the same message.

| Field | DataType | Description |
|---|---|---|
| ResponseHeader | [ResponseHeader](https://reference.opcfoundation.org/specs/OPC-10000-4/7.33) | Common response parameters. Its serviceResult is Good: the Continue succeeded, whatever the parked Service returned. |
| DeferredServiceResult | [StatusCode](https://reference.opcfoundation.org/specs/OPC-10000-4/7.38) | The serviceResult of the parked response. Always a Bad StatusCode; a parked response with a Good serviceResult is returned as the parked Service's own response message. |
| DeferredDiagnosticInfo | [DiagnosticInfo](https://reference.opcfoundation.org/specs/OPC-10000-4/7.8) | The serviceDiagnostics the parked response carried, whose string table is the ResponseHeader's. |

### Well-known instances

| BrowseName | NodeId | TypeDefinition | Parent | Note |
|---|---|---|---|---|
| AsyncServiceCapabilities | i=70100 | [AsyncServiceCapabilitiesType](#type-AsyncServiceCapabilitiesType) | ServerCapabilities (i=2268) | Server-wide deferral capabilities. Its absence is how a Server says it never defers a request. |
| AsyncServiceDiagnostics | i=70101 | [AsyncServiceDiagnosticsType](#type-AsyncServiceDiagnosticsType) | ServerDiagnostics (i=2274) | Deferred request counters and the per-request records the reading Session is entitled to see. |

<!-- END GENERATED: model-reference -->
