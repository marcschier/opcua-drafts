from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc import types as t


CONFIGURATION_VERSION = t.Struct(
    "AvroConfigurationVersionDataType",
    (t.Field("MajorVersion", t.UINT32), t.Field("MinorVersion", t.UINT32)),
)

FIELD_METADATA = t.Struct(
    "AvroFieldMetaData",
    (
        t.Field("Name", t.STRING),
        t.Field("Description", t.LOCALIZEDTEXT),
        t.Field("DataType", t.NODEID),
        t.Field("BuiltInType", t.INT32),
        t.Field("ValueRank", t.INT32),
        t.Field("ArrayDimensions", t.Array(t.UINT32, allow_null_elements=False)),
    ),
)

DATASET_METADATA = t.Struct(
    "AvroDataSetMetaData",
    (
        t.Field("Name", t.STRING),
        t.Field("DataSetClassId", t.GUID),
        t.Field("ConfigurationVersion", CONFIGURATION_VERSION),
        t.Field("Fields", t.Array(FIELD_METADATA)),
        t.Field("SchemaId", t.STRING),
        t.Field("SchemaJson", t.STRING),
    ),
)

ACTION_REQUEST_DATASET_MESSAGE = t.Struct(
    "AvroActionRequestDataSetMessage",
    (
        t.Field("ActionTargetId", t.NODEID),
        t.Field("RequestId", t.STRING),
        t.Field("CorrelationData", t.BYTESTRING),
        t.Field("InputArguments", t.Array(t.VARIANT)),
    ),
)

ACTION_RESPONSE_DATASET_MESSAGE = t.Struct(
    "AvroActionResponseDataSetMessage",
    (
        t.Field("ActionTargetId", t.NODEID),
        t.Field("RequestId", t.STRING),
        t.Field("CorrelationData", t.BYTESTRING),
        t.Field("Status", t.STATUSCODE),
        t.Field("OutputArguments", t.Array(t.VARIANT)),
        t.Field("DiagnosticInfos", t.Array(t.DIAGNOSTICINFO)),
    ),
)

ACTION_REQUEST_NETWORK_MESSAGE = t.Struct(
    "AvroActionRequestNetworkMessage",
    (
        t.Field("PublisherId", t.STRING),
        t.Field("WriterGroupId", t.UINT16),
        t.Field("NetworkMessageNumber", t.UINT16),
        t.Field("SequenceNumber", t.UINT32),
        t.Field("Timestamp", t.DATETIME),
        t.Field("Messages", t.Array(ACTION_REQUEST_DATASET_MESSAGE)),
        t.Field("SchemaId", t.STRING),
    ),
)

ACTION_RESPONSE_NETWORK_MESSAGE = t.Struct(
    "AvroActionResponseNetworkMessage",
    (
        t.Field("PublisherId", t.STRING),
        t.Field("WriterGroupId", t.UINT16),
        t.Field("NetworkMessageNumber", t.UINT16),
        t.Field("SequenceNumber", t.UINT32),
        t.Field("Timestamp", t.DATETIME),
        t.Field("Messages", t.Array(ACTION_RESPONSE_DATASET_MESSAGE)),
        t.Field("SchemaId", t.STRING),
    ),
)

DATASET_WRITER_CONFIGURATION_ANNOUNCEMENT = t.Struct(
    "AvroDataSetWriterConfigurationAnnouncement",
    (
        t.Field("PublisherId", t.STRING),
        t.Field("WriterGroupId", t.UINT16),
        t.Field("DataSetWriterId", t.UINT16),
        t.Field("ConfigurationVersion", CONFIGURATION_VERSION),
        t.Field("DataSetMetaData", DATASET_METADATA),
        t.Field("SchemaId", t.STRING),
        t.Field("SchemaJson", t.STRING),
    ),
)

ACTION_RESPONDER_CONFIGURATION_ANNOUNCEMENT = t.Struct(
    "AvroActionResponderConfigurationAnnouncement",
    (
        t.Field("PublisherId", t.STRING),
        t.Field("ActionTargetId", t.NODEID),
        t.Field("ObjectId", t.NODEID),
        t.Field("MethodId", t.NODEID),
        t.Field("InputArgumentMetaData", DATASET_METADATA),
        t.Field("OutputArgumentMetaData", DATASET_METADATA),
        t.Field("SchemaId", t.STRING),
        t.Field("SchemaJson", t.STRING),
    ),
)

DISCOVERY_PROBE = t.Struct(
    "AvroDiscoveryProbe",
    (
        t.Field("PublisherId", t.STRING),
        t.Field("WriterGroupIds", t.Array(t.UINT16, allow_null_elements=False)),
        t.Field("DataSetWriterIds", t.Array(t.UINT16, allow_null_elements=False)),
        t.Field("ActionTargetIds", t.Array(t.NODEID)),
    ),
)

ENDPOINT_DESCRIPTION = t.Struct(
    "AvroEndpointDescription",
    (
        t.Field("EndpointUrl", t.STRING),
        t.Field("SecurityMode", t.INT32),
        t.Field("SecurityPolicyUri", t.STRING),
        t.Field("TransportProfileUri", t.STRING),
        t.Field("Server", t.EXTENSIONOBJECT),
        t.Field("UserIdentityTokens", t.Array(t.EXTENSIONOBJECT)),
    ),
)

PUBLISHER_ENDPOINTS_ANNOUNCEMENT = t.Struct(
    "AvroPublisherEndpointsAnnouncement",
    (
        t.Field("PublisherId", t.STRING),
        t.Field("Endpoints", t.Array(ENDPOINT_DESCRIPTION)),
    ),
)

# Fixed NetworkMessage envelope (Part 14 Avro mapping §8.1). Each DataSetMessage is carried
# opaquely as a { SchemaId, DataSetMessage } payload entry and decoded via its own per-DataSet
# schema, so the envelope schema is stable and never varies with the DataSets it carries.
DATASET_PAYLOAD_ENTRY = t.Struct(
    "AvroDataSetPayloadEntry",
    (
        t.Field("SchemaId", t.BYTESTRING),
        t.Field("DataSetMessage", t.BYTESTRING),
    ),
)

NETWORK_MESSAGE = t.Struct(
    "AvroNetworkMessage",
    (
        t.Field("PublisherId", t.STRING),
        t.Field("DataSetClassId", t.GUID),
        t.Field("WriterGroupId", t.UINT16),
        t.Field("GroupVersion", t.UINT32),
        t.Field("NetworkMessageNumber", t.UINT16),
        t.Field("SequenceNumber", t.UINT32),
        t.Field("Timestamp", t.DATETIME),
        t.Field("PicoSeconds", t.UINT16),
        t.Field("PromotedFields", t.Array(t.VARIANT)),
        t.Field("Payload", t.Array(DATASET_PAYLOAD_ENTRY)),
    ),
)

# Un-enveloped batch (Part 14 Avro mapping §8.1): the same payload-entry array as the envelope,
# carried directly by the transport without a NetworkMessage wrapper.
DATASET_MESSAGE_BATCH = t.Struct(
    "AvroDataSetMessageBatch",
    (
        t.Field("Payload", t.Array(DATASET_PAYLOAD_ENTRY)),
    ),
)

HAND_AUTHORED_MESSAGE_SCHEMAS: dict[str, object] = {
    "AvroSchemaAnnouncement": {
        "type": "record",
        "name": "AvroSchemaAnnouncement",
        "namespace": "org.opcfoundation.ua.avro",
        "fields": [
            {"name": "SchemaId", "type": "bytes"},
            {"name": "SchemaJson", "type": "string"},
            {"name": "SchemaEpoch", "type": ["null", "long"]},
        ],
    },
    "AvroSchemaRequest": {
        "type": "record",
        "name": "AvroSchemaRequest",
        "namespace": "org.opcfoundation.ua.avro",
        "fields": [
            {"name": "RequesterId", "type": ["null", "string"]},
            {"name": "SchemaIds", "type": {"type": "array", "items": "bytes"}},
        ],
    },
}

MESSAGE_STRUCTS: tuple[t.Struct, ...] = (
    CONFIGURATION_VERSION,
    FIELD_METADATA,
    DATASET_METADATA,
    ACTION_REQUEST_DATASET_MESSAGE,
    ACTION_RESPONSE_DATASET_MESSAGE,
    ACTION_REQUEST_NETWORK_MESSAGE,
    ACTION_RESPONSE_NETWORK_MESSAGE,
    DATASET_WRITER_CONFIGURATION_ANNOUNCEMENT,
    ACTION_RESPONDER_CONFIGURATION_ANNOUNCEMENT,
    DISCOVERY_PROBE,
    ENDPOINT_DESCRIPTION,
    PUBLISHER_ENDPOINTS_ANNOUNCEMENT,
    DATASET_PAYLOAD_ENTRY,
    NETWORK_MESSAGE,
    DATASET_MESSAGE_BATCH,
)
