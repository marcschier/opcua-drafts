#!/usr/bin/env python3
"""build_bindings.py - generate an Observability Export example from a descriptor.

Input: an ObservabilityExport descriptor (JSON) plus the base companion NodeSet(s).
The tool resolves type-level BrowsePaths, synthesizes a compact illustrative instance
implementing IObservableType, emits ObservabilityBinding/BoundItem instances, and
generates the corresponding addendum.

All base-namespace (ns0) binding NodeIds are the provisional ids from the draft
Observability Export spec.
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
                         "http://opcfoundation.org/UA/ObservabilityExport/Examples/FieldId")

# --- Observability Export model namespace provisional ids -----------------
OBS_NS = "http://opcfoundation.org/UA/ObservabilityExport/"
BIND = {
    "ObservabilityFolderType": 60010, "ObservabilityBindingType": 60011,
    "BoundItemType": 60012, "BoundVariableType": 60013,
    "IObservableType": 60016, "BoundEventFieldType": 60017,
    "ObservabilityBindingGroupType": 60018,
    "BoundItemKindEnum": 60051, "ObservabilitySignalKindEnum": 60052,
    "MetricInstrumentTypeEnum": 60053, "MetricTemporalityEnum": 60054,
    "BindsToNode": 60001, "ExportedBy": 60002,
    "HasBaseBinding": 60003, "Collects": 60004,
    "Observability": 60101,
}
KIND = {"Telemetry": 0, "Status": 1, "Metric": 2, "Counter": 3,
        "Event": 4, "Dimension": 5, "Identification": 6, "Other": 7}
SIGNAL_KIND = {"Metrics": 0, "Logs": 1, "Traces": 2}
INSTRUMENT = {"Counter": 0, "UpDownCounter": 1, "Histogram": 2, "Gauge": 3,
              "ObservableCounter": 4, "ObservableUpDownCounter": 5, "ObservableGauge": 6}
TEMPORALITY = {"Cumulative": 0, "Delta": 1}
# well-known base event types (ns0) whose fields an event DataSet selects
EVENT_TYPES = {"BaseEventType": 2041, "ConditionType": 2782,
               "AlarmConditionType": 2915, "SystemEventType": 2130}
# fixed namespace UUID (defined by the base spec) for deterministic DataSetClassIds
DATASET_CLASS_NS = uuid.UUID("8d3280be-2bf7-5ab1-9898-15a237192577")


def bindings(descriptor):
    if "observabilityBindings" not in descriptor:
        raise SystemExit("descriptor is missing required observabilityBindings array")
    return descriptor["observabilityBindings"]


def dataset_class_id(descriptor, sb):
    """Deterministic DataSetClassId: uuid5 over ObservabilityExport|<ns>;<Type>|SignalKind|MajorVersion."""
    major = descriptor.get("configurationVersion", {}).get("majorVersion", 1)
    applies = f'{descriptor["baseModelNamespaceUri"]};{descriptor["appliesToType"]}'
    signal = sb.get("signalKind", "Metrics")
    return uuid.uuid5(DATASET_CLASS_NS, f'ObservabilityExport|{applies}|{signal}|{major}')
# base UA aliases used in the emitted file
ALIASES = {
    "HasComponent": "i=47", "HasProperty": "i=46", "HasTypeDefinition": "i=40",
    "HasInterface": "i=17603", "Organizes": "i=35",
    "String": "i=12", "Int32": "i=6", "QualifiedName": "i=20", "NodeId": "i=17",
    "Guid": "i=14", "BaseDataVariableType": "i=63", "PropertyType": "i=68",
    "BaseObjectType": "i=58", "FolderType": "i=61", "SimpleAttributeOperand": "i=601",
    "RelativePath": "i=540", "Boolean": "i=1", "Double": "i=11",
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
SPEC = "../OPC-UA-Observability-Export.md"  # relative from a domain subfolder of observability-export


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


def _check_item(sb, it, errors):
    """Validate OTEL/dimension constraints on a bound item (§5.13)."""
    where = f'{sb["name"]}/{it.get("fieldName", "?")}'
    # A dimension is either constant (dimensionConstantValue) or node-sourced (browsePath).
    if it.get("kind") == "Dimension" and it.get("dimensionConstantValue") is not None \
            and "browsePath" in it:
        errors.append(f'{where}: a dimension has both browsePath and dimensionConstantValue; '
                      f'use exactly one')
    # Monotonicity must not contradict the metric instrument.
    mi, mono = it.get("metricInstrumentType"), it.get("monotonic")
    if mi and mono is not None:
        monotonic = mi in ("Counter", "ObservableCounter")
        if monotonic and mono is False:
            errors.append(f'{where}: {mi} is monotonic; monotonic:false contradicts it')
        if not monotonic and mono is True:
            errors.append(f'{where}: {mi} is not monotonic; monotonic:true contradicts it')


def resolve_items(descriptor, idx):
    """Validate each bound item and enrich it in place. A Kind=Dimension item is a binding-level
    attribute (§5.13): constant dimensions (dimensionConstantValue, no source node) are not
    resolved; node-sourced dimensions resolve their BrowsePath like data items — in both data and
    event bindings. Non-dimension items in an event binding are event fields (not resolved against
    the companion type)."""
    errors = []
    for sb in bindings(descriptor):
        is_event = sb.get("signalKind", "Metrics") in ("Logs", "Traces")
        for it in sb["boundItems"]:
            _check_item(sb, it, errors)
            is_dim = it.get("kind") == "Dimension"
            # constant dimension: fixed attribute value, no source node
            if is_dim and it.get("dimensionConstantValue") is not None and "browsePath" not in it:
                it["_constant_dim"] = True
                if "fieldName" not in it:
                    errors.append(f'{sb["name"]}: constant dimension needs a fieldName')
                continue
            # event field (non-dimension item in an event binding): not resolved against the type
            if is_event and not is_dim:
                it.setdefault("fieldName",
                              it.get("browsePath", "/").strip("/").split("/")[-1])
                continue
            # data item OR node-sourced dimension: resolve the BrowsePath against the type
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
        self.obs_ns = len(self.file_uris) + 1
        self.nsmap[OBS_NS] = self.obs_ns
        self.file_uris.append(OBS_NS)
        self.signal_nodes = {}   # names-tuple -> nodeid(int, example ns)

    def nid(self):
        self.next_id += 1
        return self.next_id

    def ex(self, i):
        return f"ns=1;i={i}"

    def b(self, key):
        return f"ns={self.obs_ns};i={BIND[key]}"

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
            elif is_leaf and rec["cls"] == "UAMethod":
                # A bound Method leaf: BindsToNode targets a Method node (Methods are not typed,
                # so no HasTypeDefinition); it is a HasComponent of its owning Object.
                self._open("UAMethod", nid, bn, self.ex(parent))
                self.out.append(f"    <DisplayName>{concrete_name(seg['name'])}</DisplayName>")
                self._refs([("HasComponent", self.ex(parent), False)])
                self.out.append("  </UAMethod>")
            else:
                self.object(nid, bn, "FolderType", self.ex(parent),
                            refs_extra=[("HasComponent", self.ex(parent), False)])
            self.signal_nodes[key] = nid
            parent = nid
        self.signal_nodes[names] = parent
        return parent

    def emit(self):
        d = self.d
        self.root_id = self.nid()
        root_bn = f'1:{d["instanceName"]}'
        type_ref = self.base_nodeid_str(self.type_key)
        U = 'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd"'
        cs_uri = d.get("companionSpecificationUri", d["baseModelNamespaceUri"])
        ns_uris = d.get("modelNamespaceUris") or [m["uri"] for m in d["requiredModels"]]
        group_id = self.nid()
        group_bn = d.get("groupName", d["domain"])

        self._open("UAObject", self.root_id, root_bn)
        self.out.append(f'    <DisplayName>{d["instanceName"]}</DisplayName>')
        self.out.append(f'    <Description>Illustrative theoretical instance of '
                        f'{d["appliesToType"]} carrying example observability bindings. Only the '
                        f'bound signals are shown; not a conformant full instance.</Description>')
        self._refs([("HasTypeDefinition", type_ref, True),
                    ("HasInterface", self.b("IObservableType"), True),
                    ("HasComponent", self.ex(group_id), True)])
        self.out.append("  </UAObject>")

        self.group_id = group_id
        self._open("UAObject", group_id, f"1:{group_bn}", self.ex(self.root_id))
        self.out.append(f"    <DisplayName>{sx.escape(group_bn)}</DisplayName>")
        self._refs([("HasTypeDefinition", self.b("ObservabilityBindingGroupType"), True),
                    ("HasComponent", self.ex(self.root_id), False),
                    ("Collects", self.b("Observability"), False)])
        self.out.append("  </UAObject>")
        self.prop(self.nid(), "CompanionSpecificationUri", "String",
                  f'<uax:String {U}>{sx.escape(cs_uri)}</uax:String>', group_id)
        lst = "".join(f'<uax:String>{sx.escape(u)}</uax:String>' for u in ns_uris)
        self.prop(self.nid(), "ModelNamespaceUris", "String",
                  f'<uax:ListOfString {U}>{lst}</uax:ListOfString>', group_id, valuerank="1")
        for sb in bindings(d):
            self.emit_binding(sb)

    def emit_binding(self, sb):
        bid = self.nid()
        name = sb["name"]
        U = 'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd"'
        self._open("UAObject", bid, f"1:{name}", self.ex(self.group_id))
        self.out.append(f"    <DisplayName>{name}</DisplayName>")
        self._refs([("HasTypeDefinition", self.b("ObservabilityBindingType"), True),
                    ("HasComponent", self.ex(self.group_id), False)])
        self.out.append("  </UAObject>")
        sig = sb.get("signalKind", "Metrics")
        self.prop(self.nid(), "SignalKind", self.b("ObservabilitySignalKindEnum"),
                  f'<uax:Int32 {U}>{SIGNAL_KIND[sig]}</uax:Int32>', bid)
        dscid = dataset_class_id(self.d, sb)
        sb["_dataSetClassId"] = str(dscid)
        self.prop(self.nid(), "DataSetClassId", "Guid",
                  f'<uax:Guid {U}><uax:String>{dscid}</uax:String></uax:Guid>', bid)
        base_cls = sb.get("baseDataSetClassIds")
        if base_cls:
            lst = "".join(f'<uax:Guid><uax:String>{sx.escape(str(g))}</uax:String></uax:Guid>'
                          for g in base_cls)
            self.prop(self.nid(), "BaseDataSetClassIds", "Guid",
                      f'<uax:ListOfGuid {U}>{lst}</uax:ListOfGuid>', bid, valuerank=1)
        card = (sb.get("dataSetCardinalityPath") or "").strip("/")
        if card:
            self.prop(self.nid(), "DataSetCardinalityPath", "RelativePath",
                      self._rel_path_value(card, sb, U), bid)
        evsrc = (sb.get("eventSourcePath") or "").strip("/")
        if evsrc:
            self.prop(self.nid(), "EventSourcePath", "RelativePath",
                      self._rel_path_value(evsrc, sb, U), bid)
        for key, propname in (("logTemplate", "LogTemplate"),
                              ("logSeverityFieldName", "LogSeverityFieldName"),
                              ("logBodyFieldName", "LogBodyFieldName"),
                              ("logTimestampFieldName", "LogTimestampFieldName"),
                              ("spanNameTemplate", "SpanNameTemplate"),
                              ("spanNameFieldName", "SpanNameFieldName"),
                              ("traceIdFieldName", "TraceIdFieldName"),
                              ("spanIdFieldName", "SpanIdFieldName"),
                              ("parentSpanIdFieldName", "ParentSpanIdFieldName"),
                              ("spanStartTimeFieldName", "SpanStartTimeFieldName"),
                              ("spanEndTimeFieldName", "SpanEndTimeFieldName"),
                              ("spanStatusFieldName", "SpanStatusFieldName"),
                              ("spanKind", "SpanKind"),
                              ("spanCorrelationFieldName", "SpanCorrelationFieldName")):
            v = sb.get(key)
            if v:
                self.prop(self.nid(), propname, "String",
                          f'<uax:String {U}>{sx.escape(v)}</uax:String>', bid)
        if sig in ("Logs", "Traces"):
            for it in sb["boundItems"]:
                if it.get("kind") == "Dimension":
                    if it.get("_constant_dim"):
                        self.emit_constant_dimension(bid, sb, it)
                    else:
                        self.emit_item(bid, sb, it)
                else:
                    self.emit_event_item(bid, sb, it)
        else:
            for it in sb["boundItems"]:
                if it.get("_constant_dim"):
                    self.emit_constant_dimension(bid, sb, it)
                else:
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

    def _relpath_from_segments(self, segs, U):
        """Encode a RelativePath from already-resolved path segments (each with name/ns), e.g. a
        bound Method's OwningObjectPath = its resolved path minus the Method segment. Namespaces
        come from the resolved segments; HierarchicalReferences + IncludeSubtypes."""
        els = []
        for seg in segs:
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
        self._refs([("HasTypeDefinition", self.b("BoundEventFieldType"), True),
                    ("HasComponent", self.ex(binding_id), False)])
        self.out.append("  </UAObject>")
        self.prop(self.nid(), "FieldName", "String",
                  f'<uax:String {U}>{sx.escape(fn)}</uax:String>', iid)
        self.prop(self.nid(), "Kind", self.b("BoundItemKindEnum"),
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
        dsfid = uuid.uuid5(FIELD_ID_NS, f'{self.d["domain"]}|{sb.get("signalKind", "Metrics")}|{fn}|event')
        self.prop(self.nid(), "DataSetFieldId", "Guid",
                  f'<uax:Guid {U}><uax:String>{dsfid}</uax:String></uax:Guid>', iid)
        # Facet provenance (§5.12): base binding class an inherited/overriding event field came from.
        prov = it.get("sourceBindingClassId")
        if prov:
            self.prop(self.nid(), "SourceBindingClassId", "Guid",
                      f'<uax:Guid {U}><uax:String>{sx.escape(str(prov))}</uax:String>'
                      f'</uax:Guid>', iid)

    def emit_item(self, binding_id, sb, it):
        rec = it["_rec"]
        signal = self.ensure_signal(rec)
        iid = self.nid()
        if rec["cls"] == "UAMethod":
            raise SystemExit(f"{sb['name']}/{it.get('fieldName', it.get('browsePath'))}: Methods/actions are not part of Observability Export")
        fn = it["fieldName"]
        self._open("UAObject", iid, f"1:{fn}", self.ex(binding_id))
        self.out.append(f"    <DisplayName>{sx.escape(fn)}</DisplayName>")
        self._refs([("HasTypeDefinition", self.b("BoundVariableType"), True),
                    ("HasComponent", self.ex(binding_id), False),
                    ("BindsToNode", self.ex(signal), True)])
        self.out.append("  </UAObject>")
        U = 'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd"'
        # FieldName
        self.prop(self.nid(), "FieldName", "String",
                  f'<uax:String {U}>{sx.escape(fn)}</uax:String>', iid)
        # Kind
        self.prop(self.nid(), "Kind", self.b("BoundItemKindEnum"),
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
                           f'{self.d["domain"]}|{sb.get("signalKind", "Metrics")}|{fn}|{it["browsePath"]}')
        self.prop(self.nid(), "DataSetFieldId", "Guid",
                  f'<uax:Guid {U}><uax:String>{dsfid}</uax:String></uax:Guid>', iid)
        # Facet provenance (§5.12): the base binding class an inherited/overriding field came from.
        prov = it.get("sourceBindingClassId")
        if prov:
            self.prop(self.nid(), "SourceBindingClassId", "Guid",
                      f'<uax:Guid {U}><uax:String>{sx.escape(str(prov))}</uax:String>'
                      f'</uax:Guid>', iid)
        # DimensionConstantValue for a node-sourced item is unusual, but supported.
        if it.get("dimensionConstantValue") is not None:
            self.prop(self.nid(), "DimensionConstantValue", "String",
                      f'<uax:String {U}>{sx.escape(str(it["dimensionConstantValue"]))}'
                      f'</uax:String>', iid)
        # Observability/OTEL metric detail (§5.13): instrument, unit, buckets, temporality, monotonic.
        self._emit_metric_props(iid, it, U)

    def _emit_metric_props(self, iid, it, U):
        mi = it.get("metricInstrumentType")
        if mi:
            self.prop(self.nid(), "MetricInstrumentType", self.b("MetricInstrumentTypeEnum"),
                      f'<uax:Int32 {U}>{INSTRUMENT[mi]}</uax:Int32>', iid)
        unit = it.get("unit")
        if unit:
            self.prop(self.nid(), "Unit", "String",
                      f'<uax:String {U}>{sx.escape(unit)}</uax:String>', iid)
        buckets = it.get("explicitBucketBoundaries")
        if buckets:
            lst = "".join(f'<uax:Double>{float(b)}</uax:Double>' for b in buckets)
            self.prop(self.nid(), "ExplicitBucketBoundaries", "Double",
                      f'<uax:ListOfDouble {U}>{lst}</uax:ListOfDouble>', iid, valuerank=1)
        temp = it.get("metricTemporality")
        if temp:
            self.prop(self.nid(), "MetricTemporality", self.b("MetricTemporalityEnum"),
                      f'<uax:Int32 {U}>{TEMPORALITY[temp]}</uax:Int32>', iid)
        mono = it.get("monotonic")
        if mono is not None:
            self.prop(self.nid(), "Monotonic", "Boolean",
                      f'<uax:Boolean {U}>{"true" if mono else "false"}</uax:Boolean>', iid)

    def emit_constant_dimension(self, binding_id, sb, it):
        """A constant-valued dimension: a Kind=Dimension bound item whose attribute value is a
        fixed string (DimensionConstantValue), with no source node/BrowsePath/BindsToNode."""
        iid = self.nid()
        fn = it["fieldName"]
        U = 'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd"'
        self._open("UAObject", iid, f"1:{fn}", self.ex(binding_id))
        self.out.append(f"    <DisplayName>{sx.escape(fn)}</DisplayName>")
        self._refs([("HasTypeDefinition", self.b("BoundVariableType"), True),
                    ("HasComponent", self.ex(binding_id), False)])
        self.out.append("  </UAObject>")
        self.prop(self.nid(), "FieldName", "String",
                  f'<uax:String {U}>{sx.escape(fn)}</uax:String>', iid)
        self.prop(self.nid(), "Kind", self.b("BoundItemKindEnum"),
                  f'<uax:Int32 {U}>{KIND["Dimension"]}</uax:Int32>', iid)
        self.prop(self.nid(), "DimensionConstantValue", "String",
                  f'<uax:String {U}>{sx.escape(str(it["dimensionConstantValue"]))}</uax:String>', iid)
        dsfid = uuid.uuid5(FIELD_ID_NS, f'{self.d["domain"]}|{sb.get("signalKind", "Metrics")}|{fn}|dimension')
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
        header.append(f'      <RequiredModel ModelUri="{OBS_NS}"/>')
        header.append("    </Model>")
        header.append("  </Models>")
        header.append("  <Aliases>")
        for a, v in ALIASES.items():
            header.append(f'    <Alias Alias="{a}">{v}</Alias>')
        for a in ("BindsToNode", "ExportedBy", "HasBaseBinding", "Collects"):
            header.append(f'    <Alias Alias="{a}">{self.b(a)}</Alias>')
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


def emit_annex(descriptor, db, base_names, binding_heading="####"):
    d = descriptor
    L = [f"### Observability export bindings for `{d['appliesToType']}`", "",
         f"Bindings for `{d['appliesToType']}` in `{d['baseModelNamespaceUri']}`, per the "
         f"[Observability Export]({SPEC}) base specification. Each binding exposes one OTEL "
         f"signal (`Metrics`, `Logs` or `Traces`) with a deterministic `DataSetClassId`.", ""]
    for sb in bindings(d):
        sig = sb.get("signalKind", "Metrics")
        dscid = sb.get("_dataSetClassId") or str(dataset_class_id(d, sb))
        content = {"Metrics": "OTEL metrics (PublishedDataItems)",
                   "Logs": "OTEL logs (PublishedEvents)",
                   "Traces": "OTEL traces/spans (PublishedEvents)"}[sig]
        L.append(f"{binding_heading} {sb['name']} — {sig}")
        L.append("")
        hdr = f"*Signal:* {content} · *DataSetClassId:* `{dscid}`"
        card = sb.get("dataSetCardinalityPath")
        hdr += f" · *Cardinality:* one DataSet per `{card}`" if card else " · *Cardinality:* one DataSet (bound root)"
        if sig in ("Logs", "Traces"):
            hdr += f" · *Event source:* `{sb.get('eventSourcePath', '/')}` · *Event type:* {sb.get('eventType', 'BaseEventType')}"
        L.append(hdr)
        L.append("")
        if sig in ("Logs", "Traces"):
            L.append("| Field | Kind | Event field / attribute |")
            L.append("|---|---|---|")
            for it in sb["boundItems"]:
                detail = _otel_note(it) if it.get("kind") == "Dimension" else f"`{it.get('browsePath', '/' + it['fieldName'])}`"
                L.append(f"| {it['fieldName']} | {it['kind']} | {detail} |")
            if sig == "Logs" and (sb.get("logTemplate") or sb.get("logBodyFieldName")):
                L.append("")
                L.append(f"*OTEL LogRecord mapping:* body template `{sb.get('logTemplate', '—')}`; "
                         f"severity = `{sb.get('logSeverityFieldName', '—')}`, body = "
                         f"`{sb.get('logBodyFieldName', '—')}`, timestamp = "
                         f"`{sb.get('logTimestampFieldName', '—')}`.")
            if sig == "Traces":
                L.append("")
                L.append(f"*OTEL Span mapping:* name template `{sb.get('spanNameTemplate', '—')}`, "
                         f"start = `{sb.get('spanStartTimeFieldName', '—')}`, end = "
                         f"`{sb.get('spanEndTimeFieldName', '—')}`, status = "
                         f"`{sb.get('spanStatusFieldName', '—')}`, kind = `{sb.get('spanKind', 'Internal')}`.")
        else:
            L.append("| Field | Kind | BrowsePath | Source type | DataType | OTEL |")
            L.append("|---|---|---|---|---|---|")
            for it in sb["boundItems"]:
                otel = _otel_note(it)
                if it.get("_constant_dim") or "_rec" not in it:
                    bp, tdname, dt = "—", "—", "—"
                else:
                    rec = it["_rec"]
                    tdname = td_name(rec["typedef"], db, base_names)
                    dt = dt_name(rec["datatype"])
                    bp = f"`{it['browsePath']}`"
                L.append(f"| {it['fieldName']} | {it['kind']} | {bp} | {tdname} | {dt} | {otel} |")
        L.append("")
    return "\n".join(L) + "\n"

def _otel_note(it):
    """A compact OTEL annotation for the annex item table."""
    if it.get("kind") == "Dimension":
        if it.get("dimensionConstantValue") is not None:
            return f"dimension = `{it['dimensionConstantValue']}` (const)"
        return "dimension"
    parts = []
    if it.get("metricInstrumentType"):
        parts.append(it["metricInstrumentType"])
    if it.get("unit"):
        parts.append(f"[{it['unit']}]")
    if it.get("metricTemporality"):
        parts.append(it["metricTemporality"].lower())
    if it.get("monotonic"):
        parts.append("monotonic")
    if it.get("explicitBucketBoundaries"):
        parts.append("buckets " + ",".join(str(b) for b in it["explicitBucketBoundaries"]))
    return " ".join(parts) if parts else "—"


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


def emit_addendum(descriptor, db, base_names, spec_folder, desc_base):
    d = descriptor
    desc_rel = f"../../extras/observability-export/examples/{spec_folder}/{desc_base}"
    cs = d.get("companionSpec", {})
    im = d.get("instanceModel", {})
    nitems = sum(len(sb["boundItems"]) for sb in bindings(d))
    sigs = ", ".join(f"{sb['name']} ({sb.get('signalKind', 'Metrics')})" for sb in bindings(d))
    L = []
    A = L.append
    A(f"# OPC UA {d['domain']} — Observability Export Addendum")
    A("")
    A(f"**Working draft — a worked example of the [Observability Export]({SPEC}) base specification applied to {cs.get('name', d['domain'])}.**")
    A("")
    A(f"> **Status — illustrative example.** The `{d['exampleNamespaceUri']}` namespace and NodeIds are provisional. The example shows how `{d['appliesToType']}` data is declared for OTEL metrics, logs and traces over classic OPC UA and optional PubSub.")
    A("")
    A("## 1 Scope")
    A("")
    A(f"This addendum defines example **observability export bindings** for `{d['appliesToType']}` — {nitems} bound items across {sigs}. {d.get('summary', '')}")
    A("")
    A("## 2 Normative references")
    A("")
    A(f"- [Observability Export]({SPEC}) — the base binding model (discovery and OTEL mapping).")
    if cs.get("ref"):
        A(f"- [{cs.get('name', d['domain'])}]({cs['ref']}) — the companion specification whose type is bound.")
    A("- [OPC 10000-14](https://reference.opcfoundation.org/specs/OPC-10000-14/) — PubSub (optional realization).")
    A("")
    A("## 3 How the bindings are applied")
    A("")
    A(f"The machine-readable descriptor [`{desc_base}`]({desc_rel}) lists each bound item as a `BrowsePath` from `{d['appliesToType']}`, with its observability `Kind` and OTEL `SignalKind`. The generated overlay [`Opc.Ua.{d['domain']}.ObservabilityExport.NodeSet2.xml`](Opc.Ua.{d['domain']}.ObservabilityExport.NodeSet2.xml) instantiates a compact `{d['instanceName']}` object, applies `IObservableType`, and exposes an `ObservabilityBindingGroup` collected by (`CollectedBy`) the server-wide `Observability` registry.")
    if im.get("note"):
        A("")
        A(f"> **Theoretical instance model.** {im['note']}" + (f" See [{im.get('refName', 'instance example')}]({im['ref']})." if im.get("ref") else ""))
    A("")
    A("Only the bound signals are materialised in the overlay; it is illustrative, not a full companion instance.")
    A("")
    annex = emit_annex(d, db, base_names, binding_heading="###")
    A("## 4 " + annex.split("\n", 1)[0].lstrip("# ").strip())
    A("")
    A("\n".join(annex.split("\n")[2:]).rstrip())
    A("## 5 Where the bindings live")
    A("")
    A("Overview of the observability bindings and their placement on the theoretical instance:")
    A("")
    A(emit_diagrams(d).rstrip())
    res = emit_resolution_examples(d)
    if res:
        A("## 6 BrowsePath resolution — worked examples")
        A("")
        A(res.rstrip())
    A("## 7 Deliverables")
    A("")
    A("| File | Content |")
    A("|---|---|")
    A(f"| [`{desc_base}`]({desc_rel}) | Machine-readable ObservabilityExport descriptor (single source). |")
    A(f"| [`Opc.Ua.{d['domain']}.ObservabilityExport.NodeSet2.xml`](Opc.Ua.{d['domain']}.ObservabilityExport.NodeSet2.xml) | The binding instances on the theoretical `{d['instanceName']}` instance. |")
    A("")
    A(f"Regenerate from [`core-specs/extras/observability-export/examples/`](../../extras/observability-export/examples/) with `python tools/build_bindings.py {spec_folder}/{desc_base} tools/ref`.")
    A("")
    return "\n".join(L).rstrip() + "\n"


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
         "`DataSetClassId` is identical for every DataSet of a signal — it names the *class*, "
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
        L.append("| Binding | DataSet (cardinality instance) | # fields | Example fields |")
        L.append("|---|---|---|---|")
        total = 0
        for sb in bindings(d):
            sig = sb.get("signalKind", "Metrics")
            card = (sb.get("dataSetCardinalityPath") or "").strip("/")
            if sig in ("Logs", "Traces") or not card:
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
                    if "browsePath" not in it:
                        # a constant dimension is a binding-level attribute, not a value field
                        fields.append(it["fieldName"])
                        continue
                    suffix = it["browsePath"].strip("/").split("/")[len(card_segs):]
                    for pnames, _c in _expand(suffix, ctx, topo):
                        fields.append(it["fieldName"] + "".join("_" + n for n in pnames))
                ex = ", ".join(fields[:4]) + (" …" if len(fields) > 4 else "")
                L.append(f"| {sb['name']} | {dsname} | {len(fields)} | {ex} |")
                total += 1
        L.append("")
        L.append(f"→ **{total} DataSets** produced by the bridge for this topology.")
        L.append("")
    L.append("Across all topologies the `DataSetClassId` per signal is unchanged — a "
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
    ov = ["```mermaid", "graph LR",
          f'  ROOT["{d["instanceName"]} : {d["appliesToType"]}"]',
          f'  ROOT --> G["{d.get("groupName", d["domain"])}<br/>ObservabilityBindingGroup"]',
          '  G -.CollectedBy.-> O["Observability registry i=60101"]']
    for i, sb in enumerate(bindings(d)):
        sig = sb.get("signalKind", "Metrics")
        ov.append(f'  G --> S{i}["{sb["name"]}<br/>{sig}"]')
        for j, it in enumerate(sb["boundItems"][:6]):
            ov.append(f'  S{i} --> S{i}_{j}["{it["fieldName"]} : {it["kind"]}"]')
    ov.append("```")
    inst = ["```mermaid", "graph TD",
            f'  R["{d["instanceName"]} : {d["appliesToType"]}"]',
            "  R -->|HasInterface| I([IObservableType])",
            f'  R -->|HasComponent| G["{d.get("groupName", d["domain"])} : ObservabilityBindingGroupType"]',
            '  G -.CollectedBy.-> O["Observability : ObservabilityFolderType"]']
    for i, sb in enumerate(bindings(d)[:3]):
        sig = sb.get("signalKind", "Metrics")
        inst.append(f'  G -->|HasComponent| B{i}["{sb["name"]} : ObservabilityBindingType<br/>{sig}"]')
        for j, it in enumerate(sb["boundItems"][:3]):
            if sig in ("Logs", "Traces") or "_rec" not in it:
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
    # The descriptor is a secondary source under core-specs/extras/observability-export/examples/<spec>/;
    # the standardized outputs (overlay + addendum) land in core-specs/observability-export/<spec>/.
    desc_dir = os.path.dirname(os.path.abspath(descriptor_path))
    spec_folder = os.path.basename(desc_dir)
    desc_base = os.path.basename(os.path.abspath(descriptor_path))
    core = os.path.abspath(os.path.join(desc_dir, "..", "..", "..", ".."))
    outdir = os.path.join(core, "observability-export", spec_folder)
    os.makedirs(outdir, exist_ok=True)
    d = json.load(open(descriptor_path, encoding="utf-8"))
    # DataSetClassId encodes MajorVersion; a browsing subscriber recomputes it from the binding's
    # exposed attributes. Per spec §5.7 a binding at MajorVersion != 1 SHALL expose
    # ConfigurationVersion so that computation matches. This example generator does not yet emit the
    # ConfigurationVersion property, so refuse MajorVersion != 1 rather than emit a non-recognizable
    # overlay (all current descriptors use majorVersion 1).
    if d.get("configurationVersion", {}).get("majorVersion", 1) != 1:
        raise SystemExit("majorVersion != 1 requires emitting ConfigurationVersion on each binding "
                         "(spec §5.7); not implemented by this example generator.")
    db = load_base(d, ref_dir)
    base_names = load_base_names(ref_dir)
    type_key, idx = build_index(db, d["appliesToType"])
    resolve_items(d, idx)
    em = Emitter(d, db)
    xml = em.document(type_key)
    base = f'Opc.Ua.{d["domain"]}.ObservabilityExport'
    open(os.path.join(outdir, base + ".NodeSet2.xml"), "w", encoding="utf-8").write(xml)
    addendum = f'OPC-UA-{d["domain"]}-Observability-Export-Addendum.md'
    open(os.path.join(outdir, addendum), "w", encoding="utf-8").write(
        emit_addendum(d, db, base_names, spec_folder, desc_base))
    nitems = sum(len(sb["boundItems"]) for sb in bindings(d))
    print(f'{d["domain"]}: {len(bindings(d))} signals, {nitems} bound items, '
          f'{em.next_id-5000} nodes emitted; all paths resolved OK')


if __name__ == "__main__":
    main()
