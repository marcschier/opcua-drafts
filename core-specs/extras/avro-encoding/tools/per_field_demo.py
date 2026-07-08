"""Reference check for the per-field Variant/ExtensionObject schema model.

Unlike the shared model (one `Variant` record per self-contained schema), the
per-field model gives each Variant/ExtensionObject occurrence its own record,
named by field path, so fields evolve independently. This demo builds one
self-contained schema exercising the hard positions — a top-level Variant, a
Variant nested inside an ExtensionObject struct, a `DataValue.value` Variant, and
a Variant whose body is an ExtensionObject whose struct holds a Variant
(recursion, to observed depth) — round-trips a value through it, and shows that
two Variant fields carry independent unions and evolve independently.

Run standalone; the process exits non-zero if any assertion fails.
"""
from __future__ import annotations

import copy
import sys
from io import BytesIO

from fastavro import parse_schema, schemaless_reader, schemaless_writer

NS = "org.opcfoundation.ua.avro"
SCALAR = {"Int32": "int", "Double": "double", "Boolean": "boolean", "Float": "float",
          "String": ["null", "string"]}


def _scalar_branch(name: str, key: str) -> dict:
    return {"type": "record", "name": name, "namespace": NS,
            "fields": [{"name": "value", "type": SCALAR[key]}]}


def _variant(name: str, scalar_keys: list[str], extra_branches: list = ()) -> dict:
    """A per-field Variant record whose body union is named after this field."""
    body: list = ["null"]
    for k in scalar_keys:
        body.append(_scalar_branch(f"{name}_{k}Scalar", k))
    body.extend(extra_branches)
    return {"type": "record", "name": name, "namespace": NS, "fields": [
        {"name": "builtInType", "type": "int"},
        {"name": "dimensions", "type": ["null", {"type": "array", "items": "int"}], "default": None},
        {"name": "body", "type": body, "default": None}]}


def _ext(name: str, struct_defs: list[dict]) -> dict:
    """A per-field ExtensionObject record whose struct-type union is named after this field."""
    return {"type": "record", "name": name, "namespace": NS, "fields": [
        {"name": "typeId", "type": "string"},
        {"name": "body", "type": ["null", *struct_defs], "default": None}]}


def _sample_schema(detail_keys: list[str]) -> dict:
    """The self-contained per-field `Sample` schema; `detail_keys` lets us grow the
    nested detail Variant independently to show it does not touch `signal`."""
    signal = _variant("VariantSignal", ["Int32", "Double"])

    detail = _variant("VariantEventDetail", detail_keys)
    sensor = {"type": "record", "name": "SensorEventEvent", "namespace": NS, "fields": [
        {"name": "deviceId", "type": "string"},
        {"name": "detail", "type": detail}]}
    event = _ext("ExtensionObjectEvent", [sensor])

    reading_value = _variant("VariantReadingValue", ["String"])
    reading = {"type": "record", "name": "DataValueReading", "namespace": NS, "fields": [
        {"name": "value", "type": ["null", reading_value], "default": None},
        {"name": "status", "type": ["null", "int"], "default": None}]}

    # Recursion: a Variant whose body is an ExtensionObject whose struct holds a
    # Variant (built to the one level actually observed).
    inner = _variant("VariantPayloadInner", ["String"])
    wrapper = {"type": "record", "name": "WrapperPayload", "namespace": NS,
               "fields": [{"name": "inner", "type": inner}]}
    ext_payload = _ext("ExtObjPayloadBody", [wrapper])
    eo_scalar = {"type": "record", "name": "VariantPayload_ExtensionObjectScalar", "namespace": NS,
                 "fields": [{"name": "value", "type": ext_payload}]}
    payload = _variant("VariantPayload", ["Int32"], [eo_scalar])

    return {"type": "record", "name": "Sample", "namespace": NS, "fields": [
        {"name": "signal", "type": signal},
        {"name": "event", "type": event},
        {"name": "reading", "type": reading},
        {"name": "payload", "type": payload}]}


def _sample_value() -> dict:
    signal = {"builtInType": 6, "dimensions": None,
              "body": (f"{NS}.VariantSignal_Int32Scalar", {"value": 42})}
    detail = {"builtInType": 10, "dimensions": None,
              "body": (f"{NS}.VariantEventDetail_FloatScalar", {"value": 1.5})}
    event = {"typeId": "i=1",
             "body": (f"{NS}.SensorEventEvent", {"deviceId": "d1", "detail": detail})}
    reading = {"value": {"builtInType": 12, "dimensions": None,
                         "body": (f"{NS}.VariantReadingValue_StringScalar", {"value": "hello"})},
               "status": 0}
    inner = {"builtInType": 12, "dimensions": None,
             "body": (f"{NS}.VariantPayloadInner_StringScalar", {"value": "nested"})}
    wrapper = (f"{NS}.WrapperPayload", {"inner": inner})
    eo_body = {"typeId": "i=2", "body": wrapper}
    payload = {"builtInType": 22, "dimensions": None,
               "body": (f"{NS}.VariantPayload_ExtensionObjectScalar", {"value": eo_body})}
    return {"signal": signal, "event": event, "reading": reading, "payload": payload}


def _roundtrip(schema: dict, datum: dict) -> dict:
    parsed = parse_schema(copy.deepcopy(schema))
    bio = BytesIO()
    schemaless_writer(bio, parsed, datum)
    return schemaless_reader(BytesIO(bio.getvalue()), parse_schema(copy.deepcopy(schema)),
                             return_record_name=True)


def _find_record(node, name: str):
    if isinstance(node, dict):
        if node.get("name") == name and node.get("type") == "record":
            return node
        for v in node.values():
            r = _find_record(v, name)
            if r:
                return r
    if isinstance(node, list):
        for v in node:
            r = _find_record(v, name)
            if r:
                return r
    return None


def main() -> int:
    schema = _sample_schema(["Boolean", "Float"])

    # Reversibility: a value touching every hard position round-trips losslessly.
    got = _roundtrip(schema, _sample_value())
    assert got["signal"]["body"][0] == f"{NS}.VariantSignal_Int32Scalar"
    assert got["signal"]["body"][1]["value"] == 42
    assert got["event"]["body"][1]["detail"]["body"][0] == f"{NS}.VariantEventDetail_FloatScalar"
    assert got["reading"]["value"][1]["body"][0] == f"{NS}.VariantReadingValue_StringScalar"
    assert got["payload"]["body"][1]["value"]["body"][1]["inner"]["body"][1]["value"] == "nested"

    # Independence: the two Variant fields are distinct records with disjoint
    # body-type sets (signal carries Int32/Double; detail carries Boolean/Float).
    sig = _find_record(schema, "VariantSignal")
    det = _find_record(schema, "VariantEventDetail")
    sig_branches = [b["name"].split("_")[-1] for b in sig["fields"][2]["type"] if isinstance(b, dict)]
    det_branches = [b["name"].split("_")[-1] for b in det["fields"][2]["type"] if isinstance(b, dict)]
    assert sig_branches == ["Int32Scalar", "DoubleScalar"], sig_branches
    assert det_branches == ["BooleanScalar", "FloatScalar"], det_branches

    # Independent evolution: growing the nested `detail` Variant (append String)
    # leaves the `signal` Variant record byte-identical.
    grown = _sample_schema(["Boolean", "Float", "String"])
    assert _find_record(grown, "VariantEventDetail")["fields"][2]["type"] != det["fields"][2]["type"]
    assert _find_record(grown, "VariantSignal") == sig, "signal changed when detail grew"

    # Cycle-tying (§6.6): a bounded recursive shape where a Variant's ExtObj body
    # struct has a `child` field that references the ancestor Variant record by
    # name. This closes the Variant->ExtObj->struct->Variant cycle, keeping the
    # schema finite and valid, and a nested value round-trips through the tie.
    assert _cycle_roundtrip() == 5, "cycle-tied recursive value did not round-trip"

    print("per_field_demo: roundtrip=ok independence=ok independent-evolution=ok cycle-tie=ok; ok")
    return 0


def _cycle_schema() -> dict:
    return {"type": "record", "name": "VariantNode", "namespace": NS, "fields": [
        {"name": "builtInType", "type": "int"},
        {"name": "dimensions", "type": ["null", {"type": "array", "items": "int"}], "default": None},
        {"name": "body", "type": ["null",
            {"type": "record", "name": "VariantNode_Int32Scalar", "namespace": NS,
             "fields": [{"name": "value", "type": "int"}]},
            {"type": "record", "name": "VariantNode_ExtObjScalar", "namespace": NS, "fields": [
                {"name": "value", "type": {"type": "record", "name": "ExtObjNode", "namespace": NS, "fields": [
                    {"name": "typeId", "type": "string"},
                    {"name": "body", "type": ["null",
                        {"type": "record", "name": "WrapperNode", "namespace": NS,
                         "fields": [{"name": "child", "type": f"{NS}.VariantNode"}]}], "default": None}]}}]}],
         "default": None}]}


def _cycle_roundtrip():
    schema = _cycle_schema()
    child = {"builtInType": 6, "dimensions": None,
             "body": (f"{NS}.VariantNode_Int32Scalar", {"value": 5})}
    wrapper = (f"{NS}.WrapperNode", {"child": child})
    value = {"builtInType": 22, "dimensions": None, "body": (
        f"{NS}.VariantNode_ExtObjScalar", {"value": {"typeId": "i=9", "body": wrapper}})}
    got = _roundtrip(schema, value)
    return got["body"][1]["value"]["body"][1]["child"]["body"][1]["value"]


if __name__ == "__main__":
    sys.exit(main())
