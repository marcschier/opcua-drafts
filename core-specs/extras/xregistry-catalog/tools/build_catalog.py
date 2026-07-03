#!/usr/bin/env python3
"""Build an xRegistry Schema Registry catalog document from an OPC UA NodeSet.

Maps namespaces -> schemagroups and DataTypes -> schema Resources per §5 of
OPC-UA-xRegistry-Schema-Catalog.md. The JSON Schema documents are generated
here (jsonschema_gen); the Avro/Protobuf/Arrow documents are embedded from the
sibling encoding folders' ``schemas/`` when present, otherwise referenced by
``schemaurl``.

Usage (from repo root):
  python core-specs/xregistry-catalog/tools/build_catalog.py [NODESET_XML]
Writes: core-specs/xregistry-catalog/examples/opcua-catalog.xregistry.json
"""
from __future__ import annotations

import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_common")))

from opcua_enc import nodeset  # noqa: E402
from opcua_enc import types as t  # noqa: E402
from opcua_enc import fingerprint  # noqa: E402

import jsonschema_gen as jsg  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# After the reorg this tool lives under core-specs/extras/xregistry-catalog/tools,
# so this resolves to core-specs/extras (where the sibling encodings' generated
# schemas live). pubsub-binding was NOT moved, so it is one level up in core-specs.
EXTRAS = os.path.abspath(os.path.join(HERE, "..", ".."))
CORE_SPECS = EXTRAS
DEFAULT_NODESET = os.path.join(EXTRAS, "..", "pubsub-binding", "Opc.Ua.PubSubBinding.NodeSet2.xml")
OUT = os.path.abspath(os.path.join(HERE, "..", "examples", "opcua-catalog.xregistry.json"))
BASE_UA = "http://opcfoundation.org/UA/"
_UA_NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"

FORMATS = {
    "avro": ("Avro/1.11", "application/vnd.apache.avro+json", "avsc"),
    "protobuf": ("Protobuf/3", "text/plain", "proto"),
    "arrow": ("ApacheArrow/1.0", "application/vnd.apache.arrow.schema+json", "json"),
    "jsonschema": ("JsonSchema/2020-12", "application/schema+json", "json"),
}
SIBLING_DIR = {"avro": "avro-encoding", "protobuf": "protobuf-encoding", "arrow": "arrow-encoding"}


def _slug(uri: str) -> str:
    body = re.sub(r"^https?://", "", uri).strip("/")
    return re.sub(r"[^a-zA-Z0-9]+", ".", body).strip(".").lower()


def _namespace_and_version(path: str) -> tuple[str, str]:
    root = ET.parse(path).getroot()
    model = root.find(f"{_UA_NS}Models/{_UA_NS}Model")
    if model is not None and model.get("ModelUri"):
        return model.get("ModelUri"), model.get("Version", "1.0.0")
    uris = root.find(f"{_UA_NS}NamespaceUris")
    if uris is not None:
        first = uris.find(f"{_UA_NS}Uri")
        if first is not None and first.text:
            return first.text, "1.0.0"
    return BASE_UA, "1.0.0"


def _find_sibling_schema(fmt: str, browse_name: str) -> str | None:
    d = os.path.join(CORE_SPECS, SIBLING_DIR[fmt], "schemas")
    if not os.path.isdir(d):
        return None
    ext = FORMATS[fmt][2]
    cands = [
        f for f in os.listdir(d)
        if f.lower().endswith("." + ext) and browse_name.lower() in f.lower()
    ]
    return os.path.join(d, sorted(cands)[0]) if cands else None


def _embed(fmt: str, browse_name: str) -> tuple[object | None, str | None]:
    """Return (inline_schema, schemaurl). Inline for text formats; else url."""
    path = _find_sibling_schema(fmt, browse_name)
    if not path:
        rel = f"../{SIBLING_DIR.get(fmt, '')}/schemas/"
        return None, rel + browse_name
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if FORMATS[fmt][2] == "json":
        try:
            return json.loads(text), None
        except json.JSONDecodeError:
            return text, None
    return text, None


def _load_schemaids(fmt_key: str) -> dict[str, dict]:
    """Read a sibling encoding's ``schemas/schemaids.json`` (type -> {schemaid, algorithm})."""
    sib = SIBLING_DIR.get(fmt_key)
    if not sib:
        return {}
    path = os.path.join(CORE_SPECS, sib, "schemas", "schemaids.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


def _content_id(doc: object) -> str:
    if isinstance(doc, str):
        data = doc.encode("utf-8")
    elif doc is None:
        return ""
    else:
        data = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return fingerprint.sha256_id_hex(data)


def _wire_schemaid(fmt_key: str, name: str, doc: object, ids: dict[str, dict]) -> tuple[str, str]:
    """The authoritative on-wire SchemaId from schemaids.json, else a content fallback."""
    entry = ids.get(name)
    if entry and entry.get("schemaid"):
        return entry["schemaid"], entry.get("algorithm", "unspecified")
    return _content_id(doc), "SHA-256 over document (fallback)"


def _schema_resource(schemaid, name, fmt_key, doc, url, nodeid, ns_uri, model_ver, wire_id, wire_alg):
    fmt, ctype, _ = FORMATS[fmt_key]
    labels = {
        "opcua.browsename": name,
        "opcua.nodeid": nodeid or "",
        "opcua.format": fmt_key,
        "opcua.namespaceuri": ns_uri,
        "opcua.schemaid": wire_id,
        "opcua.schemaid.alg": wire_alg,
    }
    version = {
        "schemaid": schemaid,
        "versionid": "1",
        "isdefault": True,
        "format": fmt,
        "contenttype": ctype,
        "labels": {**labels, "opcua.modelversion": model_ver},
    }
    if doc is not None:
        version["schema"] = doc
    elif url is not None:
        version["schemaurl"] = url
    resource = {
        "schemaid": schemaid,
        "versionid": "1",
        "name": name,
        **{k: v for k, v in version.items() if k not in ("schemaid", "versionid")},
        "versionscount": 1,
        "versions": {"1": version},
    }
    return resource


def build(nodeset_path: str) -> dict:
    ns_uri, model_ver = _namespace_and_version(nodeset_path)
    loaded = nodeset.load_datatypes(nodeset_path)
    named: list[tuple[str, str | None]] = [(s.name, s.type_id) for s in loaded.structs]
    named += [(e.name, None) for e in loaded.enums]

    schemas: dict[str, dict] = {}
    schemaid_maps = {fk: _load_schemaids(fk) for fk in ("avro", "protobuf", "arrow")}
    for name, nid in sorted(named):
        for fmt_key in ("avro", "protobuf", "arrow", "jsonschema"):
            schemaid = f"{name}:{fmt_key}"
            if fmt_key == "jsonschema":
                doc, url = jsg.schema_for(name, list(loaded.structs), list(loaded.enums)), None
            else:
                doc, url = _embed(fmt_key, name)
            wire_id, wire_alg = _wire_schemaid(fmt_key, name, doc, schemaid_maps.get(fmt_key, {}))
            schemas[schemaid] = _schema_resource(
                schemaid, name, fmt_key, doc, url, nid, ns_uri, model_ver, wire_id, wire_alg
            )

    slug = _slug(ns_uri)
    catalog = {
        "specversion": "1.0-rc3",
        "registryid": "opcua-schema-catalog",
        "self": "https://registry.example.com/",
        "description": "OPC UA DataType schemas (Avro, Protobuf, Apache Arrow, JSON Schema).",
        "schemagroupscount": 1,
        "schemagroups": {
            slug: {
                "schemagroupid": slug,
                "name": ns_uri,
                "labels": {"opcua.namespaceuri": ns_uri, "opcua.modelversion": model_ver},
                "schemascount": len(schemas),
                "schemas": schemas,
            }
        },
    }
    return catalog


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_NODESET
    catalog = build(path)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(catalog, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    groups = catalog["schemagroups"]
    total = sum(g["schemascount"] for g in groups.values())
    print(f"wrote {OUT}\n  groups={len(groups)} schemas={total} (from {os.path.basename(path)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
