"""Canonical OPC UA textual NodeId / ExpandedNodeId conversion.

Reference companion to *OPC UA — Apache Avro DataEncoding* §5.2.1. These are the
same helpers used by the Arrow reference (`arrow_codec.py`); they convert a
NodeId / ExpandedNodeId value to and from the canonical textual syntax so a field
declared as Avro `string` round-trips losslessly.
"""
from __future__ import annotations

import base64
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))
from opcua_enc import values as v  # noqa: E402


def nodeid_to_text(n: v.NodeId) -> str:
    prefix = "" if n.namespace == 0 else f"ns={n.namespace};"
    if n.id_type == v.IdType.NUMERIC:
        return f"{prefix}i={int(n.identifier)}"
    if n.id_type == v.IdType.STRING:
        return f"{prefix}s={n.identifier}"
    if n.id_type == v.IdType.GUID:
        return f"{prefix}g={uuid.UUID(bytes=n.identifier.bytes)}"
    return f"{prefix}b={base64.b64encode(n.identifier).decode('ascii')}"


def nodeid_from_text(s: str) -> v.NodeId:
    namespace = 0
    if s.startswith("ns="):
        sep = s.index(";")
        namespace = int(s[3:sep])
        s = s[sep + 1:]
    kind, _, body = s.partition("=")
    if kind == "i":
        return v.NodeId(namespace, v.IdType.NUMERIC, int(body))
    if kind == "s":
        return v.NodeId(namespace, v.IdType.STRING, body)
    if kind == "g":
        return v.NodeId(namespace, v.IdType.GUID, v.Guid(uuid.UUID(body).bytes))
    if kind == "b":
        return v.NodeId(namespace, v.IdType.OPAQUE, base64.b64decode(body))
    raise ValueError(f"unrecognized NodeId text: {s!r}")


def expandednodeid_to_text(e: v.ExpandedNodeId) -> str:
    prefix = ""
    if e.server_index:
        prefix += f"svr={e.server_index};"
    if e.namespace_uri is not None:
        prefix += f"nsu={e.namespace_uri};"
    return prefix + nodeid_to_text(e.node_id)


def expandednodeid_from_text(s: str) -> v.ExpandedNodeId:
    server_index = 0
    if s.startswith("svr="):
        sep = s.index(";")
        server_index = int(s[4:sep])
        s = s[sep + 1:]
    namespace_uri = None
    if s.startswith("nsu="):
        sep = s.index(";")
        namespace_uri = s[4:sep]
        s = s[sep + 1:]
    return v.ExpandedNodeId(nodeid_from_text(s), namespace_uri, server_index)
