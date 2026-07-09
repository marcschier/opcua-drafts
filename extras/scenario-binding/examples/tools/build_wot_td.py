#!/usr/bin/env python3
"""build_wot_td.py - render a Scenario Bindings example as W3C WoT Thing Description(s).

Maps a resolved Scenario Binding descriptor to the OPC UA binding for the W3C Web of Things
defined by OPC 10101 (OPC UA WoT Connectivity):

  * BoundVariable  -> WoT Property   (op readproperty/observeproperty for a Publisher,
                                       writeproperty for a Subscriber)
  * event binding  -> WoT Event      (op subscribeevent; data schema = the event fields)
  * BoundMethod    -> WoT Action     (op invokeaction)

Locators/semantics use the OPC 10101 `uav:` ontology (http://opcfoundation.org/UA/WoT-Binding/):
form `href` is `opc.tcp://<endpoint>[/res]/?id=<nodeId>` (split into a Thing-level `base` +
relative `href`); the origin node is tagged with `uav:browsePath` and `uav:browseName`, and the
interaction with the `uav:object`/`uav:variable` @type. Scenario-Bindings-specific metadata that
OPC 10101 does not define (DataSet identity, scenario, cardinality, metric detail, PubSub form
marker, ...) lives under a separate provisional `sb:` extension namespace, NOT under `uav:`.

Two structural mappings are demonstrated (both valid per the base spec Annex/§8):
  * Pumps    -> ONE Thing (device view): each datapoint once, scenarios listed as `sb:scenario`.
  * Robotics -> a Thing COLLECTION (array): cardinality (DataSetCardinalityPath) expands to one
    Thing per matched anchor instance for a representative topology (binding/anchor view).

A PubSub-realized binding is shown with an ADDITIONAL non-opc.tcp form (mqtt://) on the same
affordance, illustrating WoT's protocol-agnostic multi-form model.

All endpoints/ids are illustrative but deterministic. PROVISIONAL, non-normative.
"""
import json
import os
import sys
import uuid
from urllib.parse import quote

from build_bindings import (load_base, build_index, resolve_items, dataset_class_id,
                            _expand)
from nodeset_util import UA

HERE = os.path.dirname(os.path.abspath(__file__))
WOT_TD_CONTEXT = "https://www.w3.org/2019/wot/td/v1"
UAV = "http://opcfoundation.org/UA/WoT-Binding/"
# Terms specific to THIS specification (not part of the OPC 10101 `uav:` ontology, which only
# defines uav:object/uav:variable/uav:browseName/uav:browsePath + security terms) live under a
# separate, provisional Scenario Bindings WoT-extension namespace.
SB = "http://opcfoundation.org/UA/ScenarioBinding/WoT/"
ENDPOINT = "opc.tcp://opcua.example.com:4840"
MQTT_BROKER = "mqtt://broker.example.com:1883"
THING_ID_NS = uuid.uuid5(uuid.NAMESPACE_URL,
                         "http://opcfoundation.org/UA/PubSub/Examples/WoT")

# Standard BaseEventType/AlarmConditionType field DataSchemas (ns0 event fields).
EVENT_FIELD_TYPE = {
    "EventId": "string", "EventType": "string", "SourceNode": "string",
    "SourceName": "string", "Time": "string", "ReceiveTime": "string",
    "Message": "string", "Severity": "integer", "ConditionName": "string",
    "Retain": "boolean", "AckedState": "string", "ActiveState": "string",
}

# op sets keyed by Direction
DATA_OPS = {
    "Publisher": ["readproperty", "observeproperty"],
    "Subscriber": ["writeproperty"],
    "Bidirectional": ["readproperty", "writeproperty", "observeproperty"],
    "ActionInvoker": ["invokeaction"],
    "ActionResponder": ["invokeaction"],
}


def wot_type(datatype):
    """WoT DataSchema `type` from an OPC UA DataType (uri, ident)."""
    if not datatype:
        return None
    uri, ident = datatype
    if uri != UA:
        return None
    if ident == 1:
        return "boolean"
    if ident in (2, 3, 4, 5, 6, 7, 8, 9):
        return "integer"
    if ident in (10, 11):
        return "number"
    return "string"


def pct(nodeid):
    """Percent-encode the two reserved characters the OPC 10101 href BNF requires."""
    return nodeid.replace("#", "%23").replace("&", "%26")


class TDBuilder:
    def __init__(self, descriptor):
        self.d = descriptor
        self.domain = descriptor["domain"]
        self.instance = descriptor["instanceName"]
        self.example_ns = descriptor["exampleNamespaceUri"]
        # namespace list mirrors an OPC UA NamespaceArray: 0 = OPC UA, 1 = the domain model, ...
        self.namespaces = [UA, descriptor["baseModelNamespaceUri"]]

    def ns_index(self, ns):
        if ns not in self.namespaces:
            self.namespaces.append(ns)
        return self.namespaces.index(ns)

    def qname(self, seg):
        return f'{self.ns_index(seg["ns"])}:{seg["name"]}'

    # -- forms ---------------------------------------------------------------
    def _opc_form(self, ops, node_path, browse_path, browse_name, extra=None):
        nodeid = pct(f'nsu={self.example_ns};s={self.instance}{node_path}')
        form = {
            "href": f'/?id={nodeid}',
            "contentType": "application/json",
            "op": ops if len(ops) > 1 else ops[0],
        }
        if browse_path is not None:
            form["uav:browsePath"] = browse_path
        if browse_name is not None:
            form["uav:browseName"] = browse_name
        if extra:
            form.update(extra)
        return form

    def _mqtt_form(self, ops, scenario_short):
        # A PubSub realization publishes the whole DataSet to one topic, so the additional form is
        # DataSet/topic-level (one topic per scenario); the specific field is selected from the
        # message payload by its FieldName (the affordance key).
        topic = f'{self.domain.lower()}/{scenario_short.lower()}'
        return {
            "href": f'{MQTT_BROKER}/{topic}',
            "contentType": "application/json",
            "op": ops if len(ops) > 1 else ops[0],
            "sb:pubSub": True,
        }

    # -- affordances ---------------------------------------------------------
    def property_affordance(self, it, sb, node_path, browse_path):
        rec = it["_rec"]
        seg = rec["path"][-1]
        direction = sb["direction"]
        ops = DATA_OPS.get(direction, ["readproperty", "observeproperty"])
        scen_short = sb["scenarioUri"].rsplit("/", 1)[-1]
        aff = {"title": it["fieldName"], "@type": "uav:variable"}
        t = wot_type(rec.get("datatype"))
        if t:
            aff["type"] = t
        if it.get("unit"):
            aff["unit"] = it["unit"]
        aff["observable"] = "observeproperty" in ops
        if direction in ("Publisher",):
            aff["readOnly"] = True
        elif direction == "Subscriber":
            aff["writeOnly"] = True
        aff["uav:browseName"] = self.qname(seg)
        aff["sb:scenario"] = [sb["scenarioUri"]]
        aff["sb:dataSetClassId"] = [f'urn:uuid:{dataset_class_id(self.d, sb)}']
        if it.get("kind") == "Dimension":
            aff["sb:dimension"] = True
        if it.get("metricInstrumentType"):
            aff["sb:metricInstrumentType"] = it["metricInstrumentType"]
        if it.get("explicitBucketBoundaries"):
            aff["sb:explicitBucketBoundaries"] = it["explicitBucketBoundaries"]
        forms = [self._opc_form(ops, node_path, browse_path, self.qname(seg))]
        if direction == "Publisher":
            forms.append(self._mqtt_form(["observeproperty"], scen_short))
        aff["forms"] = forms
        return aff

    def event_affordance(self, sb):
        scen_short = sb["scenarioUri"].rsplit("/", 1)[-1]
        props = {}
        for it in sb["boundItems"]:
            if it.get("kind") == "Dimension":
                continue
            fn = it["fieldName"]
            props[fn] = {"type": EVENT_FIELD_TYPE.get(fn, "string"),
                         "uav:browseName": f'0:{fn}'}
        src = sb.get("eventSourcePath", "/")
        opc = {
            "href": f'/?id={pct(f"nsu={self.example_ns};s={self.instance}")}',
            "contentType": "application/json",
            "op": "subscribeevent",
            "subprotocol": "opcua.subscribe",
            "sb:eventSourcePath": src,
        }
        forms = [opc]
        if sb["direction"] == "Publisher":
            forms.append(self._mqtt_form(["subscribeevent"], scen_short))
        return {
            "title": sb["name"],
            "@type": "uav:object",
            "sb:scenario": sb["scenarioUri"],
            "sb:dataSetClassId": f'urn:uuid:{dataset_class_id(self.d, sb)}',
            "sb:eventType": sb.get("eventType", "BaseEventType"),
            "data": {"type": "object", "properties": props},
            "forms": forms,
        }

    def action_affordance(self, it, sb, node_path, browse_path):
        rec = it["_rec"]
        seg = rec["path"][-1]
        return {
            "title": it["fieldName"],
            "@type": "uav:object",
            "uav:browseName": self.qname(seg),
            "sb:scenario": sb["scenarioUri"],
            "sb:dataSetClassId": f'urn:uuid:{dataset_class_id(self.d, sb)}',
            "forms": [self._opc_form(["invokeaction"], node_path, browse_path,
                                     self.qname(seg))],
        }

    # -- Thing envelope ------------------------------------------------------
    def envelope(self, thing_id, title, description):
        return {
            "@context": [WOT_TD_CONTEXT, {"uav": UAV, "sb": SB}],
            "@type": "uav:object",
            "id": thing_id,
            "title": title,
            "description": description,
            "sb:namespaces": list(self.namespaces),
            "securityDefinitions": {"auto_sc": {"scheme": "auto"}},
            "security": ["auto_sc"],
            # base carries no resource path so a leading-slash form href "/?id=..." resolves per
            # RFC 3986 to "opc.tcp://host:port/?id=..." (matching the OPC 10101 href BNF) without
            # dropping a resource segment.
            "base": ENDPOINT,
        }


def build_single_thing(d):
    """Device view: one Thing; each datapoint appears once; scenarios are listed per affordance."""
    b = TDBuilder(d)
    properties, events, actions, dims = {}, {}, {}, []
    for sb in d["scenarioBindings"]:
        is_event = sb.get("contentKind", "DataItems") == "Events"
        if is_event:
            events[sb["name"]] = b.event_affordance(sb)
            continue
        for it in sb["boundItems"]:
            if it.get("_constant_dim"):
                if not any(x["name"] == it["fieldName"] for x in dims):
                    dims.append({"name": it["fieldName"],
                                 "value": it["dimensionConstantValue"],
                                 "sb:scenario": sb["scenarioUri"]})
                continue
            rec = it["_rec"]
            node_path = "/" + "/".join(s["name"] for s in rec["path"])
            browse_path = node_path
            fn = it["fieldName"]
            if rec["cls"] == "UAMethod":
                actions.setdefault(fn, b.action_affordance(it, sb, node_path, browse_path))
                continue
            if fn in properties:
                # datapoint already exposed by another scenario: merge scenario provenance
                properties[fn]["sb:scenario"].append(sb["scenarioUri"])
                properties[fn]["sb:dataSetClassId"].append(
                    f'urn:uuid:{dataset_class_id(d, sb)}')
            else:
                properties[fn] = b.property_affordance(it, sb, node_path, browse_path)
    thing_id = f'urn:uuid:{uuid.uuid5(THING_ID_NS, d["baseModelNamespaceUri"] + d["instanceName"])}'
    td = b.envelope(thing_id, d["instanceName"],
                    f'WoT Thing view of the {d["appliesToType"]} instance {d["instanceName"]}, '
                    f'exposing its Scenario-bound datapoints per OPC 10101. Illustrative.')
    if dims:
        td["sb:dimensions"] = dims
    if properties:
        td["properties"] = properties
    if actions:
        td["actions"] = actions
    if events:
        td["events"] = events
    return td


def _pick_topology(d):
    tops = d.get("resolutionTopologies") or []
    # representative: the first multi-device topology, else the first, else None
    for t in tops:
        if len(t.get("devices", [])) > 1:
            return t
    return tops[0] if tops else None


def build_collection(d):
    """Binding/anchor view: a TD collection. Cardinality (DataSetCardinalityPath) expands to one
    Thing per matched anchor instance for a representative topology; placeholders below the anchor
    become per-instance fields (name disambiguated by the matched instance, per base spec §5.10)."""
    topo = _pick_topology(d)
    things = []
    for sb in d["scenarioBindings"]:
        is_event = sb.get("contentKind", "DataItems") == "Events"
        card = (sb.get("dataSetCardinalityPath") or "").strip("/")
        base_cls = dataset_class_id(d, sb)
        if is_event or not card or topo is None:
            things.append(_collection_thing(d, sb, None, {}, topo))
            continue
        card_segs = card.split("/")
        for names, ctx in _expand(card_segs, {}, topo):
            things.append(_collection_thing(d, sb, names, ctx, topo, card_segs))
    return things


def _collection_thing(d, sb, anchor_names, ctx, topo, card_segs=None):
    b = TDBuilder(d)
    anchor = anchor_names[-1] if anchor_names else None
    scen_short = sb["scenarioUri"].rsplit("/", 1)[-1]
    is_event = sb.get("contentKind", "DataItems") == "Events"
    label = anchor or d["instanceName"]
    thing_id = f'urn:uuid:{uuid.uuid5(THING_ID_NS, f"{dataset_class_id(d, sb)}|{label}")}'
    title = f'{d["instanceName"]} · {sb["name"]}' + (f' · {anchor}' if anchor else "")
    desc = (f'WoT Thing for one {sb["name"]} DataSet (class '
            f'urn:uuid:{dataset_class_id(d, sb)})')
    if anchor:
        desc += f' at cardinality anchor {anchor}'
    if topo:
        desc += f' — topology "{topo["name"]}"'
    desc += ". Illustrative."
    td = b.envelope(thing_id, title, desc)
    td["sb:scenario"] = sb["scenarioUri"]
    td["sb:dataSetClassId"] = f'urn:uuid:{dataset_class_id(d, sb)}'
    if sb.get("dataSetCardinalityPath"):
        td["sb:cardinalityPath"] = sb["dataSetCardinalityPath"]
    if is_event:
        td["events"] = {sb["name"]: b.event_affordance(sb)}
        return td
    properties, actions = {}, {}
    for it in sb["boundItems"]:
        if it.get("_constant_dim"):
            continue
        rec = it["_rec"]
        seg_names = [s["name"] for s in rec["path"]]
        type_path = "/" + "/".join(seg_names)
        # substitute the cardinality anchor prefix with the concrete instance; expand sub-anchor
        # placeholders into concrete fields using the topology counts
        below = seg_names[len(card_segs):] if card_segs else seg_names
        prefix = ("/" + "/".join(names_for_prefix(card_segs, anchor_names))) if card_segs else ""
        for pnames, _c in _expand(below, ctx, topo):
            concrete = []
            pi = 0
            for s in below:
                if s.startswith("<") and s.endswith(">"):
                    concrete.append(pnames[pi]); pi += 1
                else:
                    concrete.append(s)
            node_path = prefix + "/" + "/".join(concrete)
            suffix = "".join("_" + n for n in pnames)
            fn = it["fieldName"] + suffix
            aff = b.property_affordance(it, sb, node_path, type_path)
            aff["title"] = fn
            if rec["cls"] == "UAMethod":
                actions[fn] = b.action_affordance(it, sb, node_path, type_path)
            else:
                properties[fn] = aff
    if properties:
        td["properties"] = properties
    if actions:
        td["actions"] = actions
    return td


def names_for_prefix(card_segs, anchor_names):
    """Concrete names for the cardinality-anchor prefix: substitute each placeholder in the
    cardinality path positionally with its matched instance (supports multi-placeholder paths)."""
    out, pi = [], 0
    for s in card_segs:
        if s.startswith("<") and s.endswith(">"):
            out.append(anchor_names[pi])
            pi += 1
        else:
            out.append(s)
    return out


def main():
    descriptor_path = sys.argv[1]
    ref_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "ref")
    outdir = os.path.dirname(os.path.abspath(descriptor_path))
    d = json.load(open(descriptor_path, encoding="utf-8"))
    db = load_base(d, ref_dir)
    _type_key, idx = build_index(db, d["appliesToType"])
    resolve_items(d, idx)
    collection = bool(d.get("resolutionTopologies"))
    if collection:
        doc = build_collection(d)
        n = len(doc)
        kind = f"TD collection ({n} Things)"
    else:
        doc = build_single_thing(d)
        n = 1
        kind = "single Thing"
    out = os.path.join(outdir, f'Opc.Ua.{d["domain"]}.ScenarioBinding.td.json')
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f'{d["domain"]}: {kind} -> {os.path.basename(out)}')


if __name__ == "__main__":
    main()
