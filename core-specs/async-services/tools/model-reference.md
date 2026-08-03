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
