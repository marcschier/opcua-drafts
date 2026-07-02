#!/usr/bin/env python3
"""build_bindings.py - generate a PubSub Scenario Binding *example* from a descriptor.

Input: a ScenarioBindingConfiguration descriptor (JSON, the skill's authoring DSL) plus
the base companion NodeSet(s). The tool:
  1. walks the target companion ObjectType and validates every boundItem.browsePath,
     enriching it with the real namespace-qualified BrowseName, DataType and TypeDefinition;
  2. synthesises a compact *theoretical instance* (only the bound signals) in an example
     namespace, hangs a ScenarioBindings container (PubSubScenarioBindingsType) off it and
     emits ScenarioBinding + BoundItem instances (BindsToNode -> the concrete signal node);
  3. emits the per-scenario annex tables (Markdown, with reference.opcfoundation.org and
     base-spec links) and two mermaid diagram sources (bindings overview + instance placement).

All base-namespace (ns0) binding NodeIds (PubSubScenarioBindingsType i=60010 etc.) are the
PROVISIONAL ids from the draft PubSub Scenario Binding spec.
"""
import json
import os
import sys
import uuid
import xml.sax.saxutils as sx
from nodeset_util import NodeSetDB, UA

HERE = os.path.dirname(os.path.abspath(__file__))
# stable namespace for deterministic DataSetFieldId GUIDs
FIELD_ID_NS = uuid.uuid5(uuid.NAMESPACE_URL,
                         "http://opcfoundation.org/UA/PubSub/Examples/ScenarioBinding")

# --- base-namespace (ns0) PubSub Scenario Binding provisional ids -----------
BIND = {
    "PubSubScenarioBindingsType": 60010, "ScenarioBindingType": 60011,
    "BoundItemType": 60012, "BoundVariableType": 60013, "BoundMethodType": 60014,
    "ScenarioProfileType": 60015, "IPubSubScenarioBoundType": 60016,
    "BoundEventFieldType": 60017, "ScenarioBindingGroupType": 60018,
    "ScenarioBindingDirectionEnum": 60050, "BoundItemKindEnum": 60051,
    "ScenarioContentKindEnum": 60052,
    "BindsToNode": 60001, "ScenarioRealizedVia": 60002,
}
DIRECTION = {"Publisher": 0, "Subscriber": 1, "ActionInvoker": 2,
             "ActionResponder": 3, "Bidirectional": 4}
KIND = {"Telemetry": 0, "Status": 1, "Configuration": 2, "Metric": 3, "Counter": 4,
        "Event": 5, "Command": 6, "Setpoint": 7, "Identification": 8, "Other": 9}
CONTENT_KIND = {"DataItems": 0, "Events": 1}
# well-known base event types (ns0) whose fields an event DataSet selects
EVENT_TYPES = {"BaseEventType": 2041, "ConditionType": 2782,
               "AlarmConditionType": 2915, "SystemEventType": 2130}
# fixed namespace UUID (defined by the base spec) for deterministic DataSetClassIds
DATASET_CLASS_NS = uuid.UUID("fc164bdb-8705-58e9-ab11-7b1ed155b4e8")


def dataset_class_id(descriptor, sb):
    """Deterministic DataSetClassId: uuid5 over ScenarioUri | <ns>;<Type> | MajorVersion."""
    major = descriptor.get("configurationVersion", {}).get("majorVersion", 1)
    applies = f'{descriptor["baseModelNamespaceUri"]};{descriptor["appliesToType"]}'
    return uuid.uuid5(DATASET_CLASS_NS, f'{sb["scenarioUri"]}|{applies}|{major}')
# base UA aliases used in the emitted file
ALIASES = {
    "HasComponent": "i=47", "HasProperty": "i=46", "HasTypeDefinition": "i=40",
    "HasInterface": "i=17603", "Organizes": "i=35",
    "BindsToNode": f"i={BIND['BindsToNode']}",
    "String": "i=12", "Int32": "i=6", "QualifiedName": "i=20", "NodeId": "i=17",
    "Guid": "i=14", "BaseDataVariableType": "i=63", "PropertyType": "i=68",
    "BaseObjectType": "i=58", "FolderType": "i=61", "SimpleAttributeOperand": "i=601",
    "RelativePath": "i=540",
}
# reference.opcfoundation.org links for base types used in the annex
REF = {
    "AnalogUnitType": "https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.4",
    "AnalogUnitRangeType": "https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.5",
    "BaseAnalogType": "https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2",
    "AnalogItemType": "https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.3",
    "BaseDataVariableType": "https://reference.opcfoundation.org/specs/OPC-10000-5/7.4",
    "PropertyType": "https://reference.opcfoundation.org/specs/OPC-10000-5/7.3",
    "TwoStateDiscreteType": "https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.6",
    "MultiStateDiscreteType": "https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.7",
}
SPEC = "../../OPC-UA-PubSub-Scenario-Binding.md"  # relative from a domain subfolder


def load_base(descriptor, ref_dir):
    db = NodeSetDB()
    for fn in descriptor["baseNodeSets"]:
        db.load(os.path.join(ref_dir, fn))
    return db


def build_index(db, type_name):
    root = None
    for k, n in db.nodes.items():
        if n.cls == "UAObjectType" and n.bn_name == type_name:
            root = k
    if root is None:
        raise SystemExit(f"type {type_name} not found in base nodesets")
    idx = {}
    for rec in db.walk(root, max_depth=8):
        names = tuple(s["name"] for s in rec["path"])
        idx.setdefault(names, rec)
    return root, idx


def resolve_items(descriptor, idx):
    """Validate each data boundItem.browsePath against the walked type; enrich in place.
    Event bindings (contentKind=Events) select standard event-type fields and are not
    resolved against the companion type."""
    errors = []
    for sb in descriptor["scenarioBindings"]:
        if sb.get("contentKind", "DataItems") == "Events":
            for it in sb["boundItems"]:
                it.setdefault("fieldName",
                              it.get("browsePath", "/").strip("/").split("/")[-1])
            continue
        for it in sb["boundItems"]:
            names = tuple(p for p in it["browsePath"].strip("/").split("/"))
            rec = idx.get(names)
            if rec is None:
                errors.append(f'{sb["name"]}: path not found: {it["browsePath"]}')
                continue
            it["_rec"] = rec
            it.setdefault("fieldName", names[-1])
    if errors:
        raise SystemExit("PATH RESOLUTION ERRORS:\n  " + "\n  ".join(errors))
    return descriptor


# ---------------------------------------------------------------------------
# NodeSet emission
# ---------------------------------------------------------------------------
class Emitter:
    def __init__(self, descriptor, db):
        self.d = descriptor
        self.db = db
        self.out = []
        self.next_id = 5000
        # namespace index map for the emitted file: 0=base UA, 1=example, then models
        self.nsmap = {UA: 0, descriptor["exampleNamespaceUri"]: 1}
        self.file_uris = [descriptor["exampleNamespaceUri"]]
        for i, m in enumerate(descriptor["requiredModels"], start=2):
            self.nsmap[m["uri"]] = i
            self.file_uris.append(m["uri"])
        self.signal_nodes = {}   # names-tuple -> nodeid(int, example ns)

    def nid(self):
        self.next_id += 1
        return self.next_id

    def ex(self, i):
        return f"ns=1;i={i}"

    def qn(self, uri, name):
        return f'{self.nsmap[uri]}:{name}'

    def base_nodeid_str(self, key):
        """render a (uri,id) key as a NodeId string in the emitted file."""
        uri, ident = key
        ns = self.nsmap.get(uri)
        if ns is None:  # model not in our required list; fall back to raw
            return f"i={ident}" if uri == UA else f"ns=?;i={ident}"
        return f"i={ident}" if ns == 0 else f"ns={ns};i={ident}"

    # -- low-level node writers --------------------------------------------
    def _open(self, tag, nid, browsename, parent=None, extra=""):
        p = f' ParentNodeId="{parent}"' if parent else ""
        self.out.append(f'  <{tag} NodeId="{self.ex(nid)}" BrowseName="{browsename}"{p}{extra}>')

    def _refs(self, refs):
        self.out.append("    <References>")
        for rt, tgt, fwd in refs:
            f = "" if fwd else ' IsForward="false"'
            self.out.append(f'      <Reference ReferenceType="{rt}"{f}>{tgt}</Reference>')
        self.out.append("    </References>")

    def object(self, nid, browsename, typedef, parent, refs_extra=(), display=None):
        self._open("UAObject", nid, browsename, parent)
        self.out.append(f"    <DisplayName>{sx.escape(display or browsename.split(':')[-1])}</DisplayName>")
        refs = [("HasTypeDefinition", typedef, True)] + list(refs_extra)
        self._refs(refs)
        self.out.append("  </UAObject>")

    def prop(self, nid, name, datatype_alias, value_xml, parent_id, valuerank=None):
        vr = f' ValueRank="{valuerank}" ArrayDimensions="0"' if valuerank else ""
        self._open("UAVariable", nid, f"1:{name}", self.ex(parent_id),
                   extra=f' DataType="{datatype_alias}"{vr}')
        self.out.append(f"    <DisplayName>{name}</DisplayName>")
        self._refs([("HasTypeDefinition", "PropertyType", True),
                    ("HasProperty", self.ex(parent_id), False)])
        self.out.append(f"    <Value>{value_xml}</Value>")
        self.out.append("  </UAVariable>")

    # -- higher-level structures -------------------------------------------
    def ensure_signal(self, rec):
        """Create the parent-chain objects + leaf variable for a bound path once."""
        names = tuple(s["name"] for s in rec["path"])
        if names in self.signal_nodes:
            return self.signal_nodes[names]
        parent = self.root_id
        for depth, seg in enumerate(rec["path"]):
            key = tuple(s["name"] for s in rec["path"][:depth + 1])
            if key in self.signal_nodes:
                parent = self.signal_nodes[key]
                continue
            nid = self.nid()
            bn = self.qn(seg["ns"], concrete_name(seg["name"]))
            is_leaf = depth == len(rec["path"]) - 1
            if is_leaf and rec["cls"] == "UAVariable":
                dt = rec["datatype"]
                dt_str = self.base_nodeid_str(dt) if dt else "i=24"
                td_ref = "BaseDataVariableType"
                tdk = rec["typedef"]
                if tdk and tdk[0] in self.nsmap:
                    td_ref = self.base_nodeid_str(tdk)
                self._open("UAVariable", nid, bn, self.ex(parent),
                           extra=f' DataType="{dt_str}"')
                self.out.append(f"    <DisplayName>{concrete_name(seg['name'])}</DisplayName>")
                self._refs([("HasTypeDefinition", td_ref, True),
                            ("HasComponent", self.ex(parent), False)])
                self.out.append("  </UAVariable>")
            else:
                self.object(nid, bn, "FolderType", self.ex(parent),
                            refs_extra=[("HasComponent", self.ex(parent), False)])
            self.signal_nodes[key] = nid
            parent = nid
        self.signal_nodes[names] = parent
        return parent

    def emit(self):
        d = self.d
        # instance root
        self.root_id = self.nid()
        root_bn = f'1:{d["instanceName"]}'
        pump_type = self.base_nodeid_str(self.type_key)
        # ScenarioBindings container id (allocated now, filled later)
        self._open("UAObject", self.root_id, root_bn)
        self.out.append(f'    <DisplayName>{d["instanceName"]}</DisplayName>')
        self.out.append(f'    <Description>Illustrative theoretical instance of '
                        f'{d["appliesToType"]} carrying example scenario bindings. Only the '
                        f'bound signals are shown; not a conformant full instance.</Description>')
        self.sb_container = self.nid()
        self._refs([("HasTypeDefinition", pump_type, True),
                    ("HasInterface", f'i={BIND["IPubSubScenarioBoundType"]}', True),
                    ("HasComponent", self.ex(self.sb_container), True)])
        self.out.append("  </UAObject>")
        # ScenarioBindings container
        self._open("UAObject", self.sb_container, "1:ScenarioBindings", self.ex(self.root_id))
        self.out.append("    <DisplayName>ScenarioBindings</DisplayName>")
        self._refs([("HasTypeDefinition", f'i={BIND["PubSubScenarioBindingsType"]}', True),
                    ("HasComponent", self.ex(self.root_id), False)])
        self.out.append("  </UAObject>")
        # per-companion-specification group anchor (avoids cross-spec name collisions)
        self.group_id = self.nid()
        group_bn = d.get("groupName", d["domain"])
        cs_uri = d.get("companionSpecificationUri", d["baseModelNamespaceUri"])
        ns_uris = d.get("modelNamespaceUris") or [m["uri"] for m in d["requiredModels"]]
        U = 'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd"'
        self._open("UAObject", self.group_id, f"1:{group_bn}", self.ex(self.sb_container))
        self.out.append(f"    <DisplayName>{sx.escape(group_bn)}</DisplayName>")
        self._refs([("HasTypeDefinition", f'i={BIND["ScenarioBindingGroupType"]}', True),
                    ("HasComponent", self.ex(self.sb_container), False)])
        self.out.append("  </UAObject>")
        self.prop(self.nid(), "CompanionSpecificationUri", "String",
                  f'<uax:String {U}>{sx.escape(cs_uri)}</uax:String>', self.group_id)
        lst = "".join(f'<uax:String>{sx.escape(u)}</uax:String>' for u in ns_uris)
        self.prop(self.nid(), "ModelNamespaceUris", "String",
                  f'<uax:ListOfString {U}>{lst}</uax:ListOfString>', self.group_id,
                  valuerank="1")
        # scenario bindings (under the group)
        for sb in d["scenarioBindings"]:
            self.emit_binding(sb)

    def emit_binding(self, sb):
        bid = self.nid()
        name = sb["name"]
        self._open("UAObject", bid, f"1:{name}", self.ex(self.group_id))
        self.out.append(f"    <DisplayName>{name}</DisplayName>")
        self._refs([("HasTypeDefinition", f'i={BIND["ScenarioBindingType"]}', True),
                    ("HasComponent", self.ex(self.group_id), False)])
        self.out.append("  </UAObject>")
        # ScenarioUri + Direction properties
        self.prop(self.nid(), "ScenarioUri", "String",
                  f'<uax:String xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd">'
                  f'{sx.escape(sb["scenarioUri"])}</uax:String>', bid)
        self.prop(self.nid(), "Direction", f'i={BIND["ScenarioBindingDirectionEnum"]}',
                  f'<uax:Int32 xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd">'
                  f'{DIRECTION[sb["direction"]]}</uax:Int32>', bid)
        U = 'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd"'
        # DataSetClassId (deterministic; recognizable across servers) + ContentKind
        dscid = dataset_class_id(self.d, sb)
        sb["_dataSetClassId"] = str(dscid)
        self.prop(self.nid(), "DataSetClassId", "Guid",
                  f'<uax:Guid {U}><uax:String>{dscid}</uax:String></uax:Guid>', bid)
        ck = sb.get("contentKind", "DataItems")
        self.prop(self.nid(), "ContentKind", f'i={BIND["ScenarioContentKindEnum"]}',
                  f'<uax:Int32 {U}>{CONTENT_KIND[ck]}</uax:Int32>', bid)
        # A "/" or empty dataSetCardinalityPath is an alias for omitted (the bound root is the
        # cardinality anchor), so it is normalized away rather than emitted as an empty segment.
        card = (sb.get("dataSetCardinalityPath") or "").strip("/")
        if card:
            self.prop(self.nid(), "DataSetCardinalityPath", "RelativePath",
                      self._rel_path_value(card, sb, U), bid)
        if ck == "Events":
            for it in sb["boundItems"]:
                self.emit_event_item(bid, sb, it)
        else:
            for it in sb["boundItems"]:
                self.emit_item(bid, sb, it)

    def _rel_path_value(self, path_str, sb, U):
        """Encode a RelativePath value; segment namespaces are taken from the binding's
        first resolved data item (whose path shares this cardinality prefix)."""
        segs = path_str.strip("/").split("/")
        ns_by_idx = {}
        for it in sb["boundItems"]:
            rec = it.get("_rec")
            if rec:
                for i, s in enumerate(rec["path"]):
                    if i < len(segs) and s["name"] == segs[i]:
                        ns_by_idx[i] = s["ns"]
                break
        els = []
        for i, s in enumerate(segs):
            nsidx = self.nsmap.get(ns_by_idx.get(i), 0)
            els.append('<uax:RelativePathElement>'
                       '<uax:ReferenceTypeId><uax:Identifier>i=33</uax:Identifier>'
                       '</uax:ReferenceTypeId><uax:IsInverse>false</uax:IsInverse>'
                       '<uax:IncludeSubtypes>true</uax:IncludeSubtypes>'
                       f'<uax:TargetName><uax:NamespaceIndex>{nsidx}</uax:NamespaceIndex>'
                       f'<uax:Name>{sx.escape(s)}</uax:Name></uax:TargetName>'
                       '</uax:RelativePathElement>')
        return f'<uax:RelativePath {U}><uax:Elements>{"".join(els)}</uax:Elements></uax:RelativePath>'

    def _browsepath_value(self, it, U):
        """Encode the RECOMMENDED type-level BrowsePath locator (RelativePath from the bound
        root) for a bound item, preserving placeholder segment names so a browse-only consumer
        can resolve cardinality per instance. Per-segment namespaces come from the resolved
        item path; HierarchicalReferences + IncludeSubtypes so it resolves via
        TranslateBrowsePathsToNodeIds regardless of the concrete hierarchical reference type."""
        els = []
        for seg in it["_rec"]["path"]:
            nsidx = self.nsmap.get(seg["ns"], 0)
            els.append('<uax:RelativePathElement>'
                       '<uax:ReferenceTypeId><uax:Identifier>i=33</uax:Identifier>'
                       '</uax:ReferenceTypeId><uax:IsInverse>false</uax:IsInverse>'
                       '<uax:IncludeSubtypes>true</uax:IncludeSubtypes>'
                       f'<uax:TargetName><uax:NamespaceIndex>{nsidx}</uax:NamespaceIndex>'
                       f'<uax:Name>{sx.escape(seg["name"])}</uax:Name></uax:TargetName>'
                       '</uax:RelativePathElement>')
        return f'<uax:RelativePath {U}><uax:Elements>{"".join(els)}</uax:Elements></uax:RelativePath>'

    def emit_event_item(self, binding_id, sb, it):
        """An event-DataSet field: a BoundEventFieldType selecting a field of a standard
        event type (no BindsToNode - event fields are not AddressSpace instance nodes)."""
        iid = self.nid()
        fn = it["fieldName"]
        evtype = EVENT_TYPES.get(sb.get("eventType", "BaseEventType"), 2041)
        U = 'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd"'
        self._open("UAObject", iid, f"1:{fn}", self.ex(binding_id))
        self.out.append(f"    <DisplayName>{sx.escape(fn)}</DisplayName>")
        self._refs([("HasTypeDefinition", f'i={BIND["BoundEventFieldType"]}', True),
                    ("HasComponent", self.ex(binding_id), False)])
        self.out.append("  </UAObject>")
        self.prop(self.nid(), "FieldName", "String",
                  f'<uax:String {U}>{sx.escape(fn)}</uax:String>', iid)
        self.prop(self.nid(), "Kind", f'i={BIND["BoundItemKindEnum"]}',
                  f'<uax:Int32 {U}>{KIND["Event"]}</uax:Int32>', iid)
        self.prop(self.nid(), "ModelNamespaceUri", "String",
                  f'<uax:String {U}>{UA}</uax:String>', iid)
        self.prop(self.nid(), "SourceBrowseName", "QualifiedName",
                  f'<uax:QualifiedName {U}><uax:NamespaceIndex>0</uax:NamespaceIndex>'
                  f'<uax:Name>{sx.escape(fn)}</uax:Name></uax:QualifiedName>', iid)
        self.prop(self.nid(), "SourceTypeDefinition", "NodeId",
                  f'<uax:NodeId {U}><uax:Identifier>i={evtype}</uax:Identifier></uax:NodeId>', iid)
        # EventFieldOperand: the authoritative Part 14 SimpleAttributeOperand for the field
        segs = it.get("browsePath", "/" + fn).strip("/").split("/")
        qn = "".join(
            f'<uax:QualifiedName><uax:NamespaceIndex>0</uax:NamespaceIndex>'
            f'<uax:Name>{sx.escape(s)}</uax:Name></uax:QualifiedName>' for s in segs)
        self.prop(self.nid(), "EventFieldOperand", "SimpleAttributeOperand",
                  f'<uax:SimpleAttributeOperand {U}>'
                  f'<uax:TypeDefinitionId><uax:Identifier>i={evtype}</uax:Identifier></uax:TypeDefinitionId>'
                  f'<uax:BrowsePath>{qn}</uax:BrowsePath>'
                  f'<uax:AttributeId>13</uax:AttributeId>'
                  f'</uax:SimpleAttributeOperand>', iid)
        dsfid = uuid.uuid5(FIELD_ID_NS, f'{self.d["domain"]}|{sb["scenarioUri"]}|{fn}|event')
        self.prop(self.nid(), "DataSetFieldId", "Guid",
                  f'<uax:Guid {U}><uax:String>{dsfid}</uax:String></uax:Guid>', iid)

    def emit_item(self, binding_id, sb, it):
        rec = it["_rec"]
        signal = self.ensure_signal(rec)
        iid = self.nid()
        is_method = rec["cls"] == "UAMethod"
        td = BIND["BoundMethodType"] if is_method else BIND["BoundVariableType"]
        fn = it["fieldName"]
        self._open("UAObject", iid, f"1:{fn}", self.ex(binding_id))
        self.out.append(f"    <DisplayName>{sx.escape(fn)}</DisplayName>")
        self._refs([("HasTypeDefinition", f'i={td}', True),
                    ("HasComponent", self.ex(binding_id), False),
                    ("BindsToNode", self.ex(signal), True)])
        self.out.append("  </UAObject>")
        U = 'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd"'
        # FieldName
        self.prop(self.nid(), "FieldName", "String",
                  f'<uax:String {U}>{sx.escape(fn)}</uax:String>', iid)
        # Kind
        self.prop(self.nid(), "Kind", f'i={BIND["BoundItemKindEnum"]}',
                  f'<uax:Int32 {U}>{KIND[it["kind"]]}</uax:Int32>', iid)
        # BrowsePath: the RECOMMENDED type-level locator (RelativePath from the bound root),
        # placeholders preserved, so a browse-only consumer can reconstruct the placeholder
        # cardinality semantics from the AddressSpace alone (BindsToNode is one concrete match).
        self.prop(self.nid(), "BrowsePath", "RelativePath",
                  self._browsepath_value(it, U), iid)
        # ModelNamespaceUri = the namespace URI that DEFINES the source node (its BrowseName ns)
        seg = rec["path"][-1]
        self.prop(self.nid(), "ModelNamespaceUri", "String",
                  f'<uax:String {U}>{sx.escape(seg["ns"])}</uax:String>', iid)
        # SourceBrowseName
        self.prop(self.nid(), "SourceBrowseName", "QualifiedName",
                  f'<uax:QualifiedName {U}><uax:NamespaceIndex>{self.nsmap[seg["ns"]]}'
                  f'</uax:NamespaceIndex><uax:Name>{sx.escape(seg["name"])}</uax:Name>'
                  f'</uax:QualifiedName>', iid)
        # SourceTypeDefinition
        if rec["typedef"]:
            self.prop(self.nid(), "SourceTypeDefinition", "NodeId",
                      f'<uax:NodeId {U}><uax:Identifier>'
                      f'{self.base_nodeid_str(rec["typedef"])}</uax:Identifier></uax:NodeId>', iid)
        # DataSetFieldId (deterministic: stable across regenerations)
        dsfid = uuid.uuid5(FIELD_ID_NS,
                           f'{self.d["domain"]}|{sb["scenarioUri"]}|{fn}|{it["browsePath"]}')
        self.prop(self.nid(), "DataSetFieldId", "Guid",
                  f'<uax:Guid {U}><uax:String>{dsfid}</uax:String></uax:Guid>', iid)

    def document(self, type_key):
        self.type_key = type_key
        self.emit()
        header = ['<?xml version="1.0" encoding="utf-8"?>',
                  '<UANodeSet xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" '
                  'xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">']
        header.append("  <NamespaceUris>")
        for u in self.file_uris:
            header.append(f"    <Uri>{u}</Uri>")
        header.append("  </NamespaceUris>")
        header.append("  <Models>")
        header.append(f'    <Model ModelUri="{self.d["exampleNamespaceUri"]}" Version="0.1.0" '
                      f'PublicationDate="2026-07-01T00:00:00Z">')
        for m in self.d["requiredModels"]:
            header.append(f'      <RequiredModel ModelUri="{m["uri"]}"/>')
        header.append("    </Model>")
        header.append("  </Models>")
        header.append("  <Aliases>")
        for a, v in ALIASES.items():
            header.append(f'    <Alias Alias="{a}">{v}</Alias>')
        header.append("  </Aliases>")
        return "\n".join(header + self.out + ["</UANodeSet>"]) + "\n"


def parent_int(parent_str):
    return int(str(parent_str).split("=")[-1])


def concrete_name(name):
    """A placeholder segment '<AxisIdentifier>' -> a concrete instance name 'Axis_1'."""
    if name.startswith("<") and name.endswith(">"):
        base = name[1:-1]
        if base.endswith("Identifier"):
            base = base[:-len("Identifier")]
        return base + "_1"
    return name


# ---------------------------------------------------------------------------
# Annex + diagrams
# ---------------------------------------------------------------------------
def load_base_names(ref_dir):
    """id -> SymbolicName for base UA nodes, from the vendored UA.NodeIds.csv (if present)."""
    names = {}
    p = os.path.join(ref_dir, "UA.NodeIds.csv")
    if os.path.exists(p):
        import csv
        with open(p, encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[1].strip().isdigit():
                    names[int(row[1])] = row[0]
    return names


def emit_annex(descriptor, db, base_names):
    d = descriptor
    L = [f"### Scenario bindings for `{d['appliesToType']}`", "",
         f"Bindings for the `{d['appliesToType']}` of the "
         f"`{d['baseModelNamespaceUri']}` companion specification, per the "
         f"[PubSub Scenario Binding]({SPEC}) base specification. Each binding is **one Part 14 "
         f"DataSet** with a deterministic `DataSetClassId`. Every data-DataSet `BrowsePath` "
         f"below was resolved against the published companion NodeSet; event-DataSet fields "
         f"select standard event-type fields.", ""]
    for sb in d["scenarioBindings"]:
        ck = sb.get("contentKind", "DataItems")
        dscid = sb.get("_dataSetClassId") or str(dataset_class_id(d, sb))
        content = ("event DataSet (PublishedEvents)" if ck == "Events"
                   else "data DataSet (PublishedDataItems)")
        L.append(f"#### Scenario: {sb['name']}")
        L.append("")
        hdr = (f"*URI:* `{sb['scenarioUri']}` · *Direction:* {sb['direction']} · "
               f"*Content:* {content} · *DataSetClassId:* `{dscid}`")
        card = sb.get("dataSetCardinalityPath")
        hdr += (f" · *Cardinality:* one DataSet per `{card}`" if card
                else " · *Cardinality:* one DataSet (bound root)")
        if ck == "Events":
            hdr += (f" · *Event source:* `{sb.get('eventSourcePath', '/')}` · "
                    f"*Event type:* {sb.get('eventType', 'BaseEventType')}")
        L.append(hdr)
        L.append("")
        if ck == "Events":
            L.append("| Field | Kind | Event field (of the event type) |")
            L.append("|---|---|---|")
            for it in sb["boundItems"]:
                L.append(f"| {it['fieldName']} | {it['kind']} | "
                         f"`{it.get('browsePath', '/' + it['fieldName'])}` |")
        else:
            L.append("| Field | Kind | BrowsePath | Source type | DataType |")
            L.append("|---|---|---|---|---|")
            for it in sb["boundItems"]:
                rec = it["_rec"]
                tdname = td_name(rec["typedef"], db, base_names)
                dt = dt_name(rec["datatype"])
                L.append(f"| {it['fieldName']} | {it['kind']} | `{it['browsePath']}` | "
                         f"{tdname} | {dt} |")
        L.append("")
    return "\n".join(L) + "\n"


def td_name(td, db, base_names):
    if not td:
        return "—"
    n = db.get(td)
    if n:
        name = n.bn_name
    elif td[0] == UA and td[1] in base_names:
        name = base_names[td[1]]
    else:
        name = f"i={td[1]}"
    url = REF.get(name)
    return f"[{name}]({url})" if url else f"`{name}`"


def emit_addendum(descriptor, db, base_names):
    d = descriptor
    cs = d.get("companionSpec", {})
    im = d.get("instanceModel", {})
    nitems = sum(len(sb["boundItems"]) for sb in d["scenarioBindings"])
    scen = ", ".join(sb["name"] for sb in d["scenarioBindings"])
    L = []
    L.append(f"# OPC UA {d['domain']} — PubSub Scenario Binding Addendum")
    L.append("")
    L.append(f"**Working draft — a worked example of the "
             f"[PubSub Scenario Binding]({SPEC}) base specification applied to "
             f"{cs.get('name', d['domain'])}.**")
    L.append("")
    L.append(f"> **Status — illustrative example.** This addendum shows how the instances of "
             f"the `{d['appliesToType']}` ({d['baseModelNamespaceUri']}) can be exposed over "
             f"OPC UA PubSub for integration scenarios, without modifying the companion "
             f"specification. All NodeIds in the example namespace "
             f"`{d['exampleNamespaceUri']}` are provisional and the base-namespace binding "
             f"types it references (`PubSubScenarioBindingsType` etc.) carry the **provisional** "
             f"NodeIds of the draft base specification.")
    L.append("")
    L.append("## 1 Scope")
    L.append("")
    L.append(f"This addendum defines example **scenario bindings** for the "
             f"`{d['appliesToType']}` — {nitems} bound items across the scenarios *{scen}* — "
             f"per the [PubSub Scenario Binding]({SPEC}) base specification. "
             f"{d.get('summary', '')}")
    L.append("")
    L.append("## 2 Normative references")
    L.append("")
    L.append(f"- [PubSub Scenario Binding]({SPEC}) — the base binding model (types, "
             f"discovery, the two-layer routing/semantic contract).")
    if cs.get("ref"):
        L.append(f"- [{cs.get('name', d['domain'])}]({cs['ref']}) — the companion "
                 f"specification whose type is bound.")
    L.append("- [OPC 10000-14](https://reference.opcfoundation.org/specs/OPC-10000-14/) — "
             "PubSub (optional realization).")
    L.append("")
    L.append("## 3 How the bindings are applied")
    L.append("")
    L.append(f"The bindings are authored at **two levels**, exactly as the base "
             f"specification recommends:")
    L.append("")
    L.append(f"1. **Type-level definitions (reusable).** The machine-readable descriptor "
             f"[`{d['domain']}.ScenarioBinding.json`]({d['domain']}.ScenarioBinding.json) "
             f"lists each bound item as a `BrowsePath` (RelativePath) from the "
             f"`{d['appliesToType']}` root, with its routing `Kind` and scenario. Every path "
             f"in §4 was **resolved against the published companion NodeSet**, so the bindings "
             f"apply to *any* conforming instance.")
    L.append(f"2. **Instance overlay (concrete).** "
             f"[`Opc.Ua.{d['domain']}.ScenarioBinding.NodeSet2.xml`]"
             f"(Opc.Ua.{d['domain']}.ScenarioBinding.NodeSet2.xml) instantiates a compact "
             f"theoretical instance `{d['instanceName']}`, applies the "
             f"`IPubSubScenarioBoundType` interface, and hangs a `ScenarioBindings` container "
             f"holding the `ScenarioBinding`/`BoundItem` instances. On the instance each "
             f"`BoundItem` uses **`BindsToNode`** to point at the concrete signal node "
             f"(the type-level `BrowsePath` and the instance `BindsToNode` are the two "
             f"locators defined by the base specification).")
    if im.get("note"):
        L.append("")
        L.append(f"> **Theoretical instance model.** {im['note']}"
                 + (f" See the reference model: [{im.get('refName', 'instance example')}]"
                    f"({im['ref']})." if im.get("ref") else ""))
    L.append("")
    L.append("Only the bound signals are materialised in the overlay; it is an *illustrative* "
             "instance, not a conformant full instance of the companion type.")
    L.append("")
    L.append("## 4 " + emit_annex(d, db, base_names).split("\n", 1)[0].lstrip("# ").strip())
    L.append("")
    L.append("\n".join(emit_annex(d, db, base_names).split("\n")[2:]))
    L.append("## 5 Where the bindings live")
    L.append("")
    L.append("Overview of the scenario bindings, then their placement on the theoretical "
             "instance (`ScenarioBindings` hangs off the instance; each `BoundItem` "
             "`BindsToNode` its signal):")
    L.append("")
    L.append(emit_diagrams(d))
    res = emit_resolution_examples(d)
    deliv_no = 6
    if res:
        L.append("## 6 BrowsePath resolution — worked examples")
        L.append("")
        L.append(res)
        deliv_no = 7
    L.append(f"## {deliv_no} Deliverables")
    L.append("")
    L.append(f"| File | Content |")
    L.append(f"|---|---|")
    L.append(f"| [`{d['domain']}.ScenarioBinding.json`]({d['domain']}.ScenarioBinding.json) | "
             f"Machine-readable ScenarioBindingConfiguration descriptor (single source). |")
    L.append(f"| [`Opc.Ua.{d['domain']}.ScenarioBinding.NodeSet2.xml`]"
             f"(Opc.Ua.{d['domain']}.ScenarioBinding.NodeSet2.xml) | The binding instances on "
             f"the theoretical `{d['instanceName']}` instance. |")
    L.append("")
    L.append("Regenerate with `python ../tools/build_bindings.py "
             f"{d['domain'].lower()}/{d['domain']}.ScenarioBinding.json`.")
    L.append("")
    return "\n".join(L) + "\n"


# --- BrowsePath resolution worked examples ---------------------------------
def _enum_placeholder(seg, ctx, topo):
    """Concrete instances a placeholder segment expands to, given the topology + context."""
    if seg == "<MotionDeviceIdentifier>":
        return [(dv["name"], {"device": dv}) for dv in topo["devices"]]
    if seg == "<AxisIdentifier>":
        return [(f"Axis_{i+1}", {}) for i in range(ctx.get("device", {}).get("axes", 1))]
    if seg == "<PowerTrainIdentifier>":
        return [(f"PowerTrain_{i+1}", {}) for i in range(ctx.get("device", {}).get("motors", 1))]
    if seg == "<MotorIdentifier>":
        return [("Motor_1", {})]
    if seg == "<ControllerIdentifier>":
        return [(c, {}) for c in topo.get("controllers", ["Controller_1"])]
    return [(seg.strip("<>") + "_1", {})]


def _expand(segs, ctx, topo):
    """Expand path segments within ctx -> list of (matched placeholder-instance names, ctx).
    Literal segments do not expand; only <Placeholder> segments do."""
    out = [([], dict(ctx))]
    for s in segs:
        nxt = []
        for names, c in out:
            if s.startswith("<") and s.endswith(">"):
                for inst, upd in _enum_placeholder(s, c, topo):
                    c2 = dict(c)
                    c2.update(upd)
                    nxt.append((names + [inst], c2))
            else:
                nxt.append((names, c))
        out = nxt
    return out


def emit_resolution_examples(descriptor):
    d = descriptor
    tops = d.get("resolutionTopologies")
    if not tops:
        return ""
    L = ["The type-level bindings above use placeholder BrowsePaths. A bridge resolves them "
         "against a concrete instance (via `TranslateBrowsePathsToNodeIds`) and produces **one "
         "DataSet per matched instance of each binding's cardinality anchor** "
         "(`DataSetCardinalityPath`); placeholders **below** the anchor become fields, their "
         "name disambiguated by the matched instance (per §5.10 of the base spec). The "
         "`DataSetClassId` is identical for every DataSet of a scenario — it names the *class*, "
         "of which there are many DataSetWriters. The same bindings resolve differently for "
         "different instance topologies:", ""]
    for ti, topo in enumerate(tops, 1):
        devdesc = ", ".join(f'{dv["name"]} ({dv["axes"]} axes, {dv["motors"]} motors)'
                            for dv in topo["devices"])
        L.append(f"### Topology {ti}: {topo['name']}")
        L.append("")
        L.append(f"*MotionDevices:* {devdesc} · *Controllers:* "
                 f"{', '.join(topo.get('controllers', []))}")
        L.append("")
        L.append("| Scenario | DataSet (cardinality instance) | # fields | Example fields |")
        L.append("|---|---|---|---|")
        total = 0
        for sb in d["scenarioBindings"]:
            ck = sb.get("contentKind", "DataItems")
            card = (sb.get("dataSetCardinalityPath") or "").strip("/")
            if ck == "Events" or not card:
                fields = [it["fieldName"] for it in sb["boundItems"]]
                ex = ", ".join(fields[:4]) + (" …" if len(fields) > 4 else "")
                L.append(f"| {sb['name']} | {d['instanceName']} | {len(fields)} | {ex} |")
                total += 1
                continue
            card_segs = card.split("/")
            for names, ctx in _expand(card_segs, {}, topo):
                dsname = names[-1] if names else d["instanceName"]
                fields = []
                for it in sb["boundItems"]:
                    suffix = it["browsePath"].strip("/").split("/")[len(card_segs):]
                    for pnames, _c in _expand(suffix, ctx, topo):
                        fields.append(it["fieldName"] + "".join("_" + n for n in pnames))
                ex = ", ".join(fields[:4]) + (" …" if len(fields) > 4 else "")
                L.append(f"| {sb['name']} | {dsname} | {len(fields)} | {ex} |")
                total += 1
        L.append("")
        L.append(f"→ **{total} DataSets** produced by the bridge for this topology.")
        L.append("")
    L.append("Across all topologies the `DataSetClassId` per scenario is unchanged — a "
             "subscriber recognizes each DataSet's class regardless of how many robots, axes or "
             "controllers a particular cell has; only the number of DataSets (writers) and the "
             "field counts differ.")
    L.append("")
    return "\n".join(L) + "\n"


def dt_name(dt):
    if not dt:
        return "—"
    base = {11: "Double", 12: "String", 7: "UInt32", 6: "Int32", 5: "UInt16",
            13: "DateTime", 21: "LocalizedText", 20: "QualifiedName", 1: "Boolean"}
    uri, ident = dt
    if uri == UA and ident in base:
        return base[ident]
    return f"i={ident}"


def emit_diagrams(descriptor):
    d = descriptor
    # overview
    ov = ["```mermaid", "graph LR",
          f'  ROOT["{d["instanceName"]} : {d["appliesToType"]}"] --> SB["ScenarioBindings"]']
    for i, sb in enumerate(d["scenarioBindings"]):
        tag = "Events" if sb.get("contentKind") == "Events" else "Data"
        ov.append(f'  SB --> S{i}["{sb["name"]}<br/>{sb["direction"]} · {tag}"]')
        for j, it in enumerate(sb["boundItems"][:6]):
            ov.append(f'  S{i} --> S{i}_{j}["{it["fieldName"]} : {it["kind"]}"]')
    ov.append("```")
    # instance placement: the first (data) binding + the first event binding, if any
    picks = [d["scenarioBindings"][0]]
    ev = next((s for s in d["scenarioBindings"] if s.get("contentKind") == "Events"), None)
    if ev is not None and ev is not picks[0]:
        picks.append(ev)
    group = d.get("groupName", d["domain"])
    inst = ["```mermaid", "graph TD",
            f'  R["{d["instanceName"]} : {d["appliesToType"]}"]',
            "  R -->|HasInterface| I([IPubSubScenarioBoundType])",
            '  R -->|HasComponent| SB["ScenarioBindings"]',
            f'  SB -->|HasComponent| G["{group} : ScenarioBindingGroupType"]']
    for i, sb in enumerate(picks):
        ck = sb.get("contentKind", "DataItems")
        inst.append(f'  G -->|HasComponent| B{i}["{sb["name"]} : ScenarioBindingType"]')
        for j, it in enumerate(sb["boundItems"][:3]):
            if ck == "Events" or "_rec" not in it:
                et = sb.get("eventType", "BaseEventType")
                inst.append(f'  B{i} -->|HasComponent| IT{i}{j}["{it["fieldName"]} : BoundEventFieldType"]')
                inst.append(f'  IT{i}{j} -.event field.-> N{i}{j}["{et}/{it["fieldName"]}"]')
            else:
                rec = it["_rec"]
                path = "/".join(concrete_name(s["name"]) for s in rec["path"])
                inst.append(f'  B{i} -->|HasComponent| IT{i}{j}["{it["fieldName"]} : BoundVariableType"]')
                inst.append(f'  IT{i}{j} -->|BindsToNode| N{i}{j}["{path}"]')
    inst.append("```")
    return "\n".join(ov) + "\n\n" + "\n".join(inst) + "\n"


def main():
    descriptor_path = sys.argv[1]
    ref_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "ref")
    outdir = os.path.dirname(os.path.abspath(descriptor_path))
    d = json.load(open(descriptor_path, encoding="utf-8"))
    db = load_base(d, ref_dir)
    base_names = load_base_names(ref_dir)
    type_key, idx = build_index(db, d["appliesToType"])
    resolve_items(d, idx)
    em = Emitter(d, db)
    xml = em.document(type_key)
    base = f'Opc.Ua.{d["domain"]}.ScenarioBinding'
    open(os.path.join(outdir, base + ".NodeSet2.xml"), "w", encoding="utf-8").write(xml)
    addendum = f'OPC-UA-{d["domain"]}-PubSub-Scenario-Binding-Addendum.md'
    open(os.path.join(outdir, addendum), "w", encoding="utf-8").write(
        emit_addendum(d, db, base_names))
    nitems = sum(len(sb["boundItems"]) for sb in d["scenarioBindings"])
    print(f'{d["domain"]}: {len(d["scenarioBindings"])} scenarios, {nitems} bound items, '
          f'{em.next_id-5000} nodes emitted; all paths resolved OK')


if __name__ == "__main__":
    main()
