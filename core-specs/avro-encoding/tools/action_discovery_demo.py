from __future__ import annotations

import json
import os
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

from fastavro import parse_schema, schemaless_reader

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
SCHEMAS = ROOT / "schemas"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc import types as t, values as v
from opcua_enc.values import canonical_equal

sys.path.insert(0, str(TOOLS))
import avro_codec
import message_types as mt
import schema_support


def _nodeid(identifier: int) -> v.NodeId:
    return v.NodeId(0, v.IdType.NUMERIC, identifier)


def _sv(ty: t.Struct, fields: dict[str, Any]) -> v.StructValue:
    return v.StructValue(fields, ty.name)


def _fresh_named_schemas() -> dict[str, object]:
    named: dict[str, object] = {}
    for schema in json.loads((SCHEMAS / "opcua.builtins.avsc").read_text(encoding="utf-8")):
        parse_schema(schema, named_schemas=named)
    return named


def _published_schema(ty: t.Struct) -> object:
    named = dict(avro_codec._load_builtin_named_schemas())
    return parse_schema(json.loads((SCHEMAS / f"{schema_support.avro_name(ty.name)}.avsc").read_text(encoding="utf-8")), named_schemas=named)


def _roundtrip_published(ty: t.Struct, value: v.StructValue) -> int:
    data = avro_codec.encode(ty, value)
    datum = schemaless_reader(BytesIO(data), _published_schema(ty))
    out = avro_codec.decode_value(ty, datum)
    assert canonical_equal(value, out), ty.name
    return len(data)


def _schema_payload(type_name: str) -> tuple[str, str]:
    schemaid = json.loads((SCHEMAS / "schemaids.json").read_text(encoding="utf-8"))[type_name]["schemaid"]
    schema_json = (SCHEMAS / f"{type_name}.avsc").read_text(encoding="utf-8")
    return schemaid, schema_json


def _configuration_version() -> v.StructValue:
    return _sv(mt.CONFIGURATION_VERSION, {"MajorVersion": 1, "MinorVersion": 0})


def _field_metadata(name: str, data_type: v.NodeId, built_in_type: int) -> v.StructValue:
    return _sv(mt.FIELD_METADATA, {
        "Name": name,
        "Description": v.LocalizedText("en", name),
        "DataType": data_type,
        "BuiltInType": built_in_type,
        "ValueRank": -1,
        "ArrayDimensions": [],
    })


def _metadata(schemaid: str, schema_json: str) -> v.StructValue:
    return _sv(mt.DATASET_METADATA, {
        "Name": "TemperatureActionArguments",
        "DataSetClassId": v.Guid(bytes(range(16))),
        "ConfigurationVersion": _configuration_version(),
        "Fields": [
            _field_metadata("SetPoint", _nodeid(11), int(t.BuiltInType.Double)),
            _field_metadata("Comment", _nodeid(12), int(t.BuiltInType.String)),
        ],
        "SchemaId": schemaid,
        "SchemaJson": schema_json,
    })


def build_values() -> list[tuple[t.Struct, v.StructValue]]:
    request_schemaid, request_schema = _schema_payload("AvroActionRequestNetworkMessage")
    response_schemaid, _ = _schema_payload("AvroActionResponseNetworkMessage")

    request = _sv(mt.ACTION_REQUEST_NETWORK_MESSAGE, {
        "PublisherId": "requestor-1",
        "WriterGroupId": 10,
        "NetworkMessageNumber": 1,
        "SequenceNumber": 100,
        "Timestamp": v.DateTime(133485408000000000),
        "Messages": [_sv(mt.ACTION_REQUEST_DATASET_MESSAGE, {
            "ActionTargetId": _nodeid(7001),
            "RequestId": "req-0001",
            "CorrelationData": b"corr-0001",
            "InputArguments": [
                v.Variant(t.DOUBLE, 23.5),
                v.Variant(t.STRING, "manual"),
            ],
        })],
        "SchemaId": request_schemaid,
    })

    response = _sv(mt.ACTION_RESPONSE_NETWORK_MESSAGE, {
        "PublisherId": "responder-1",
        "WriterGroupId": 11,
        "NetworkMessageNumber": 1,
        "SequenceNumber": 101,
        "Timestamp": v.DateTime(133485408000010000),
        "Messages": [_sv(mt.ACTION_RESPONSE_DATASET_MESSAGE, {
            "ActionTargetId": _nodeid(7001),
            "RequestId": "req-0001",
            "CorrelationData": b"corr-0001",
            "Status": v.StatusCode(0),
            "OutputArguments": [v.Variant(t.BOOLEAN, True)],
            "DiagnosticInfos": [],
        })],
        "SchemaId": response_schemaid,
    })

    metadata = _metadata(request_schemaid, request_schema)
    writer_announcement = _sv(mt.DATASET_WRITER_CONFIGURATION_ANNOUNCEMENT, {
        "PublisherId": "responder-1",
        "WriterGroupId": 11,
        "DataSetWriterId": 42,
        "ConfigurationVersion": _configuration_version(),
        "DataSetMetaData": metadata,
        "SchemaId": request_schemaid,
        "SchemaJson": request_schema,
    })

    endpoints = _sv(mt.PUBLISHER_ENDPOINTS_ANNOUNCEMENT, {
        "PublisherId": "responder-1",
        "Endpoints": [_sv(mt.ENDPOINT_DESCRIPTION, {
            "EndpointUrl": "opc.tcp://responder.example:4840",
            "SecurityMode": 1,
            "SecurityPolicyUri": "http://opcfoundation.org/UA/SecurityPolicy#None",
            "TransportProfileUri": "http://opcfoundation.org/UA-Profile/Transport/uatcp-uasc-uabinary",
            "Server": v.ExtensionObject(_nodeid(0), None),
            "UserIdentityTokens": [],
        })],
    })

    return [
        (mt.ACTION_REQUEST_NETWORK_MESSAGE, request),
        (mt.ACTION_RESPONSE_NETWORK_MESSAGE, response),
        (mt.DATASET_WRITER_CONFIGURATION_ANNOUNCEMENT, writer_announcement),
        (mt.PUBLISHER_ENDPOINTS_ANNOUNCEMENT, endpoints),
    ]


def main() -> int:
    sizes = {ty.name: _roundtrip_published(ty, value) for ty, value in build_values()}
    print("action_discovery_demo: " + ", ".join(f"{name}={size} bytes" for name, size in sizes.items()) + "; published-schema canonical_equal=ok; announcement carries SchemaId+schema=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
