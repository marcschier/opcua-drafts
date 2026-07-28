<a id="annex-a"></a>

## Annex A — Information model

This annex is the normative node reference. It is generated from `core-specs/data-channels/tools/build_model.py` and always matches `Opc.Ua.DataChannels.NodeSet2.xml`. Every node is a proposed **addition to the base OPC UA namespace** `http://opcfoundation.org/UA/` (namespace index 0), so BrowseNames are unqualified and NodeIds are plain `i=<n>`. The numeric NodeIds are **provisional**, drawn from the 65000+ block; final identifiers are assigned by the OPC Foundation. The **Declared in** column marks members inherited from a supertype.

### Type overview

| NodeId | BrowseName | NodeClass | Subtype of |
|---|---|---|---|
| i=65000 | [HasDataChannel](#type-HasDataChannel) | ReferenceType | [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-5/11.4) |
| i=65010 | [IDataChannelSourceType](#type-IDataChannelSourceType) | ObjectType | [BaseInterfaceType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.9) |
| i=65011 | [DataChannelSourceType](#type-DataChannelSourceType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| i=65012 | [DataChannelCapabilitiesType](#type-DataChannelCapabilitiesType) | ObjectType | [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2) |
| i=65020 | [DataChannelOfferedEventType](#type-DataChannelOfferedEventType) | ObjectType | [BaseEventType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.4) |
| i=65021 | [DataChannelStateChangeEventType](#type-DataChannelStateChangeEventType) | ObjectType | [BaseEventType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.4) |
| i=65022 | [AuditOpenDataChannelEventType](#type-AuditOpenDataChannelEventType) | ObjectType | [AuditSessionEventType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.4) |
| i=65030 | [DataChannelDirection](#type-DataChannelDirection) | DataType | [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.14) |
| i=65031 | [DataChannelDeliveryMode](#type-DataChannelDeliveryMode) | DataType | [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.14) |
| i=65032 | [DataChannelState](#type-DataChannelState) | DataType | [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.14) |
| i=65033 | [DataChannelParametersDataType](#type-DataChannelParametersDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32) |
| i=65034 | [DataChannelStatusDataType](#type-DataChannelStatusDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32) |
| i=65035 | [DataChannelOfferDataType](#type-DataChannelOfferDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32) |
| i=65036 | [DataChannelDiagnosticsDataType](#type-DataChannelDiagnosticsDataType) | DataType | [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32) |

### Reference types

<a id="type-HasDataChannel"></a>

#### HasDataChannel  (i=65000)

*Subtype of:* [NonHierarchicalReferences](https://reference.opcfoundation.org/specs/OPC-10000-5/11.4) · *InverseName:* `DataChannelOf`

Links a functional Object or Variable to the DataChannelSource endpoint through which its content can be streamed. The source Node is the target of the reference, so a client that browses a camera, a drive or a log Object finds the data channel it can open without knowing where the server chose to place the endpoint.

### Object types and interfaces

<a id="type-IDataChannelSourceType"></a>

#### IDataChannelSourceType  (i=65010) · *abstract*

*Inherits from:* [BaseInterfaceType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.9)

Interface implemented by any Object or Variable that can act as one end of a data channel. Adding this Interface to an existing type through HasInterface is the only change a companion specification needs in order to become streamable: it does not alter the type's supertype and does not introduce a new Node Attribute.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Direction | Variable | [DataChannelDirection](#type-DataChannelDirection) | Mandatory | IDataChannelSourceType | The directions in which this endpoint can carry data, from the point of view of the Server as the source. |
| SupportedDeliveryModes | Variable | [DataChannelDeliveryMode](#type-DataChannelDeliveryMode)\[\] | Mandatory | IDataChannelSourceType | The delivery modes this endpoint accepts in OpenDataChannel. A mode that is not listed is rejected with Bad_DeliveryModeUnsupported. |
| ContentType | Variable | String | Mandatory | IDataChannelSourceType | The IANA media type of the byte stream this endpoint produces or consumes, for example video/H264 or application/octet-stream. The data channel layer never interprets the payload; this Property is what tells an application how to. |
| ContentParameters | Variable | [KeyValuePair](https://reference.opcfoundation.org/specs/OPC-10000-5/12.19)\[\] | Optional | IDataChannelSourceType | Content-specific parameters that qualify ContentType, for example a codec profile, a sample rate or a frame geometry. Opaque to the data channel layer. |
| MaxFrameSize | Variable | UInt32 | Optional | IDataChannelSourceType | The largest data channel frame payload, in bytes, this endpoint will emit or accept. The value actually used is additionally bounded by the negotiated transport buffer size and is returned as revisedParameters.MaxFrameSize by OpenDataChannel. |
| MaxBitrate | Variable | UInt32 | Optional | IDataChannelSourceType | The peak rate, in bits per second, this endpoint may produce. A client uses it to decide whether the connection can carry the stream before opening it. |
| Priority | Variable | Byte | Optional | IDataChannelSourceType | The default scheduling priority (0 lowest, 7 highest) applied to channels opened on this endpoint when the client requests Priority 255, the no-preference encoding. |
| MaxChannels | Variable | UInt16 | Optional | IDataChannelSourceType | The maximum number of data channels that may be open on this endpoint at the same time. Exceeding it is rejected with Bad_TooManyDataChannels. |
| ActiveChannelCount | Variable | UInt16 | Optional | IDataChannelSourceType | The number of data channels currently open on this endpoint, across all Sessions. |

<a id="type-DataChannelSourceType"></a>

#### DataChannelSourceType  (i=65011)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

*Implements:* [IDataChannelSourceType](#type-IDataChannelSourceType)

The plain, concrete realization of IDataChannelSourceType: a stand-alone Object that exists only to be one end of a data channel. A server uses it where no domain Object is a natural home for the endpoint; where one is, that Object implements the Interface directly and points at nothing.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Channels | Variable | [DataChannelStatusDataType](#type-DataChannelStatusDataType)\[\] | Optional | DataChannelSourceType | The data channels currently open on this endpoint. Empty when none are open. |
| Diagnostics | Variable | [DataChannelDiagnosticsDataType](#type-DataChannelDiagnosticsDataType)\[\] | Optional | DataChannelSourceType | Per-channel counters for the channels currently open on this endpoint. |

<a id="type-DataChannelCapabilitiesType"></a>

#### DataChannelCapabilitiesType  (i=65012)

*Inherits from:* [BaseObjectType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.2)

Server-wide data channel limits and capabilities, exposed as the DataChannelCapabilities component of ServerCapabilities. A client reads it once and knows, before it opens anything, whether the Server supports data channels at all, over which transports, in which delivery modes and within which limits.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| MaxDataChannels | Variable | UInt16 | Mandatory | DataChannelCapabilitiesType | The maximum number of data channels the Server will keep open on one SecureChannel. |
| MaxFrameSize | Variable | UInt32 | Mandatory | DataChannelCapabilitiesType | The largest data channel frame payload, in bytes, the Server will emit or accept on any endpoint, before the transport buffer bound is applied. |
| SupportedDeliveryModes | Variable | [DataChannelDeliveryMode](#type-DataChannelDeliveryMode)\[\] | Mandatory | DataChannelCapabilitiesType | The delivery modes the Server implements. A mode absent here is unsupported everywhere on this Server. |
| SupportedTransportProfileUris | Variable | String\[\] | Mandatory | DataChannelCapabilitiesType | The TransportProfileUris over which this Server carries data channels, for example the uatcp-uasc-uabinary and quic-uasc-uabinary profiles. |
| MaxTotalBitrate | Variable | UInt32 | Optional | DataChannelCapabilitiesType | The aggregate rate, in bits per second, the Server will emit across all data channels of one SecureChannel. |
| MaxCreditPerChannel | Variable | UInt32 | Mandatory | DataChannelCapabilitiesType | The largest flow control credit window, in bytes, the Server will grant to one channel. Mandatory because the connection-level credit bootstrap is bounded by this value multiplied by MaxDataChannels; a Server that omitted it would leave the bound on its own receive memory undefined. |
| SupportsUnreliableDatagrams | Variable | Boolean | Optional | DataChannelCapabilitiesType | True when the Server can carry Unreliable channels over a genuinely lossy path, which requires a transport that provides one. False on a Server reachable only over opc.tcp or opc.wss, where Unreliable degrades to sender-side discard. |
| AllowInsecureDataChannels | Variable | Boolean | Optional | DataChannelCapabilitiesType | True only where the Server permits a data channel to be opened on a SecureChannel whose SecurityMode is None. Absence shall be read as False. On such a channel a frame carries neither signature nor encryption, so its payload and both sequence numbers are attacker-forgeable; the permission is therefore an explicit, separately readable, default-false opt-in rather than something inferred from AccessRestrictions, which defines only restriction bits and no bit that grants anything. |
| ActiveChannelCount | Variable | UInt16 | Optional | DataChannelCapabilitiesType | The number of data channels currently open across the whole Server. |

### Event types

<a id="type-DataChannelOfferedEventType"></a>

#### DataChannelOfferedEventType  (i=65020)

*Inherits from:* [BaseEventType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.4)

Raised when the Server wants to open a data channel towards a Client. OPC UA Services are request/response, so the Server cannot call the Client; it offers instead, and the Client accepts by calling OpenDataChannel with the OfferId. This is what makes server-initiated media possible without inverting the Service model.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| Offer | Variable | [DataChannelOfferDataType](#type-DataChannelOfferDataType) | Mandatory | DataChannelOfferedEventType | The offered channel: its OfferId, its source Node, the parameters the Server proposes and the time after which the offer lapses. |

<a id="type-DataChannelStateChangeEventType"></a>

#### DataChannelStateChangeEventType  (i=65021)

*Inherits from:* [BaseEventType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.4)

Raised whenever a data channel changes state, including the transition to Faulted that follows a transport level reset. A Client that missed the frame level RESET learns of the loss here.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| ChannelId | Variable | UInt32 | Mandatory | DataChannelStateChangeEventType | The data channel whose state changed, unique within its SecureChannel. |
| State | Variable | [DataChannelState](#type-DataChannelState) | Mandatory | DataChannelStateChangeEventType | The state entered. |
| Status | Variable | [StatusCode](https://reference.opcfoundation.org/specs/OPC-10000-4/7.38) | Optional | DataChannelStateChangeEventType | The StatusCode that caused the transition, for a transition into Closed or Faulted. |

<a id="type-AuditOpenDataChannelEventType"></a>

#### AuditOpenDataChannelEventType  (i=65022)

*Inherits from:* [AuditSessionEventType](https://reference.opcfoundation.org/specs/OPC-10000-5/6.4)

Audit event for a successful or rejected OpenDataChannel. A data channel carries application payload out of the Server outside the Read/Subscribe path, so it is auditable in its own right rather than folded into the Session audit trail.

| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |
|---|---|---|---|---|---|
| DataChannelSourceNodeId | Variable | [NodeId](https://reference.opcfoundation.org/specs/OPC-10000-3/8.2) | Mandatory | AuditOpenDataChannelEventType | The endpoint the channel was requested on. |
| Parameters | Variable | [DataChannelParametersDataType](#type-DataChannelParametersDataType) | Mandatory | AuditOpenDataChannelEventType | The parameters as revised by the Server, or as requested when the request was rejected. |
| ChannelId | Variable | UInt32 | Optional | AuditOpenDataChannelEventType | The assigned ChannelId. Omitted when the request was rejected. |

### Data types

<a id="type-DataChannelDirection"></a>

#### DataChannelDirection  (i=65030)

*Subtype of:* [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.14)

The direction in which a data channel carries payload. Directions are named from the point of view of the data channel source, which is normally the Server.

| Name | Value | Description |
|---|---|---|
| SourceToSink | 0 | The source sends and the sink receives, for example a camera feed. |
| SinkToSource | 1 | The sink sends and the source receives, for example a firmware push. |
| Bidirectional | 2 | Both ends send, over the one ChannelId, for example a two-way audio call. |

<a id="type-DataChannelDeliveryMode"></a>

#### DataChannelDeliveryMode  (i=65031)

*Subtype of:* [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.14)

The delivery guarantee requested for a data channel. What a mode can actually deliver depends on the transport: only a transport with a lossy path can genuinely drop data in flight, so over opc.tcp and opc.wss the lossy modes degrade to sender-side discard.

| Name | Value | Description |
|---|---|---|
| ReliableOrdered | 0 | Every frame is delivered, in order. The default, and the only mode a purely reliable transport realizes exactly. |
| ReliableUnordered | 1 | Every frame is delivered, but the receiver may hand frames to the application as they arrive rather than buffering to restore order. |
| PartiallyReliable | 2 | A frame is retried until its deadline passes or MaxRetransmits is reached, then abandoned and reported in a gap notification. |
| Unreliable | 3 | A frame is sent once and never retried. Frames still queued when their deadline passes are discarded. |

<a id="type-DataChannelState"></a>

#### DataChannelState  (i=65032)

*Subtype of:* [Enumeration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.14)

The lifecycle state of a data channel. The normative state transition table - which event causes which transition, which transitions are legal, and what may be sent in each state - is clause 5.13 of the Part 6 Data Channel Transport errata. Paused is maintained per direction.

| Name | Value | Description |
|---|---|---|
| Opening | 0 | OpenDataChannel has been accepted and the endpoint is being prepared; no frame may be sent for this ChannelId until the response has been handed to the transport. |
| Open | 1 | Payload may flow in the negotiated directions. |
| Paused | 2 | The channel is open but the peer's flow control credit is exhausted in this direction, so no payload may be sent. Over opc.quic this is QUIC stream or connection blocking instead. |
| Closing | 3 | This peer has decided to close a direction and is draining it. Closing is per direction, like Paused: receiving END marks only the peer's direction ended. No new payload may be enqueued in a Closing direction; frames already queued may still be sent, and END follows the last of them. |
| Closed | 4 | The channel is closed, either by END in every direction it carries or by a RESET carrying Good. Its ChannelId is not reassigned while the owning SecureChannel remains open. |
| Faulted | 5 | The channel was aborted by a RESET frame carrying a Bad StatusCode, by a timeout, or by loss of the SecureChannel, Session or authorizing user identity. |

<a id="type-DataChannelParametersDataType"></a>

#### DataChannelParametersDataType  (i=65033)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32)

The negotiated properties of one data channel. The same structure carries the client's request and the server's revision, so a client can compare what it asked for with what it got in one comparison.

| Field | DataType | Description |
|---|---|---|
| Direction | [DataChannelDirection](#type-DataChannelDirection) | The direction payload flows in. |
| DeliveryMode | [DataChannelDeliveryMode](#type-DataChannelDeliveryMode) | The delivery guarantee. |
| ContentType | String | IANA media type of the payload. |
| ContentParameters | [KeyValuePair](https://reference.opcfoundation.org/specs/OPC-10000-5/12.19)\[\] | Content-specific parameters qualifying ContentType. |
| MaxFrameSize | UInt32 | Largest frame payload in bytes. |
| InitialCredit | UInt32 | Flow control credit, in payload bytes, granted to the peer at open. |
| Priority | Byte | Scheduling priority, 0 lowest to 7 highest. 255 requests the source's default; other values above 7 are revised to 7. |
| MaxRetransmits | UInt16 | PartiallyReliable only: attempts before a frame is abandoned. Ignored where the transport is already reliable. |
| FrameDeadline | [Duration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.13) | PartiallyReliable and Unreliable only: how long a frame may wait in the send queue before it is discarded. |

<a id="type-DataChannelStatusDataType"></a>

#### DataChannelStatusDataType  (i=65034)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32)

The runtime state of one open data channel, as published by its endpoint.

| Field | DataType | Description |
|---|---|---|
| ChannelId | UInt32 | Identifier of the channel within its SecureChannel. |
| SourceNodeId | [NodeId](https://reference.opcfoundation.org/specs/OPC-10000-3/8.2) | The endpoint the channel was opened on. |
| State | [DataChannelState](#type-DataChannelState) | Current lifecycle state. |
| Parameters | [DataChannelParametersDataType](#type-DataChannelParametersDataType) | The parameters in force, as revised by the Server. |
| TransportChannelId | UInt64 | The underlying transport identifier: the QUIC stream id over opc.quic, 0 for inline framing. |
| StartTime | [UtcTime](https://reference.opcfoundation.org/specs/OPC-10000-3/8.37) | When the channel entered the Open state. |

<a id="type-DataChannelOfferDataType"></a>

#### DataChannelOfferDataType  (i=65035)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32)

A server-initiated offer to open a data channel, carried by DataChannelOfferedEventType and accepted by quoting its OfferId in OpenDataChannel.

| Field | DataType | Description |
|---|---|---|
| OfferId | UInt32 | Identifies the offer. Unique within the SecureChannel until the offer lapses. |
| SourceNodeId | [NodeId](https://reference.opcfoundation.org/specs/OPC-10000-3/8.2) | The endpoint the Server is offering. |
| Parameters | [DataChannelParametersDataType](#type-DataChannelParametersDataType) | The parameters the Server proposes. |
| ExpirationTime | [UtcTime](https://reference.opcfoundation.org/specs/OPC-10000-3/8.37) | After this time the offer lapses and OpenDataChannel returns Bad_DataChannelOfferInvalid. |

<a id="type-DataChannelDiagnosticsDataType"></a>

#### DataChannelDiagnosticsDataType  (i=65036)

*Subtype of:* [Structure](https://reference.opcfoundation.org/specs/OPC-10000-3/8.32)

Per-channel counters. FramesDiscarded and CreditStalls are the two that matter in practice: the first says the stream is outrunning the link, the second says the consumer is outrun by the stream.

| Field | DataType | Description |
|---|---|---|
| ChannelId | UInt32 | The channel these counters belong to. |
| FramesSent | UInt64 | Data frames written to the transport. |
| FramesReceived | UInt64 | Data frames accepted from the transport. |
| BytesSent | UInt64 | Payload bytes written, excluding frame headers. |
| BytesReceived | UInt64 | Payload bytes accepted, excluding frame headers. |
| FramesDiscarded | UInt64 | Frames dropped before transmission because their deadline passed. |
| CreditStalls | UInt32 | Times the sender had payload ready but no flow control credit. |
| RoundTripTime | [Duration](https://reference.opcfoundation.org/specs/OPC-10000-3/8.13) | Most recent round trip time measured by PING/PONG. |
| LastGapSequenceNumber | UInt32 | FrameSequenceNumber of the last frame reported as discarded in a gap notification. |

### Well-known instances

| BrowseName | NodeId | TypeDefinition | Parent | Note |
|---|---|---|---|---|
| DataChannelCapabilities | i=65100 | [DataChannelCapabilitiesType](#type-DataChannelCapabilitiesType) | ServerCapabilities (i=2268) | Server-wide data channel capabilities. Its absence is how a Server says it does not support data channels at all. |
