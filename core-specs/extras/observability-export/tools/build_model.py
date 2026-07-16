#!/usr/bin/env python3
"""
Generator for the OPC UA Observability Export specification (WG draft).

Emits, from a single in-code source of truth:
  * Opc.Ua.ObservabilityExport.NodeSet2.xml  - the information model (UANodeSet)
  * Opc.Ua.ObservabilityExport.NodeIds.csv   - the NodeId assignments
  * model-reference.md                       - the generated Annex A (node reference)

The model is a COMPANION SPECIFICATION in its OWN namespace
(http://opcfoundation.org/UA/ObservabilityExport/, namespace index 1). Its own nodes
are emitted as `ns=1;i=<n>`; references to base OPC UA nodes (BaseObjectType, the
Server object, the Part 14 PubSub types, base DataTypes) stay `i=<n>` (namespace 0),
which the NodeSet declares as a <RequiredModel>. NodeIds are draft numeric identifiers
in the 60000+ block within this specification's namespace.
"""
from __future__ import annotations
import os
import re
import xml.sax.saxutils as sx

# ---------------------------------------------------------------------------
# Base NodeIds (verified against the base UA NodeSet)
# ---------------------------------------------------------------------------
HasComponent = "i=47"
HasProperty = "i=46"
HasSubtype = "i=45"
Organizes = "i=35"
HasTypeDefinition = "i=40"
HasModellingRule = "i=37"
HasInterface = "i=17603"
HasEncoding = "i=38"
HasDictionaryEntry = "i=17597"

MR_Mandatory = "i=78"
MR_Optional = "i=80"
MR_OptionalPlaceholder = "i=11508"
MR_MandatoryPlaceholder = "i=11510"

BaseObjectType = "i=58"
FolderType = "i=61"
BaseDataVariableType = "i=63"
PropertyType = "i=68"
BaseInterfaceType = "i=17602"
DataTypeEncodingType = "i=76"
NonHierarchicalReferences = "i=32"

Boolean = "i=1"
Byte = "i=3"
UInt32 = "i=7"
Int32 = "i=6"
Double = "i=11"
String = "i=12"
Guid = "i=14"
NodeId_ = "i=17"
QualifiedName = "i=20"
LocalizedText = "i=21"
Structure = "i=22"
Enumeration = "i=29"
Duration = "i=290"
NumericRange = "i=291"
Argument = "i=296"
RelativePath = "i=540"

# Server object (base namespace)
Server = "i=2253"

# Part 14 PubSub (base namespace) - referenced only as optional realization target types
PublishedDataSetType = "i=14509"
DataSetWriterType = "i=15298"
DataSetReaderType = "i=15306"
WriterGroupType = "i=17725"
ConfigurationVersionDataType = "i=14593"

# Part 14 DataSet / event modelling (base namespace)
DataSetMetaDataType = "i=14523"
SimpleAttributeOperand = "i=601"
ContentFilter = "i=586"
PublishedDataItemsType = "i=15535"
PublishedEventsType = "i=15536"

# ---------------------------------------------------------------------------
# Node registry
# ---------------------------------------------------------------------------
class Node:
    __slots__ = ("nid", "cls", "bname", "symbolic", "display", "desc", "parent",
                 "attrs", "refs", "category", "definition", "value", "abstract",
                 "inverse", "symmetric")

    def __init__(self, nid, cls, bname, symbolic, display, desc, parent, attrs,
                 category, abstract):
        self.nid = nid
        self.cls = cls
        self.bname = bname
        self.symbolic = symbolic
        self.display = display or bname
        self.desc = desc
        self.parent = parent
        self.attrs = attrs or {}
        self.refs = []
        self.category = category
        self.definition = None
        self.value = None
        self.abstract = abstract
        self.inverse = None
        self.symmetric = False


NODES = {}
ORDER = []
_next_member = [60500]


def _mid():
    v = _next_member[0]
    _next_member[0] += 1
    return v


def T(nid):
    return f"i={nid}"


def add(nid, cls, bname, symbolic, display=None, desc=None, parent=None,
        attrs=None, category=None, abstract=False):
    n = Node(nid, cls, bname, symbolic, display, desc, parent, attrs, category,
             abstract)
    NODES[nid] = n
    ORDER.append(nid)
    return n


def ref(nid, reftype, target, forward=True):
    NODES[nid].refs.append((reftype, target, forward))


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def object_type(nid, name, base, desc, category, abstract=False):
    add(nid, "UAObjectType", name, name, desc=desc, category=category,
        abstract=abstract)
    ref(nid, HasSubtype, base, forward=False)
    return nid


def interface_type(nid, name, base, desc, category):
    add(nid, "UAObjectType", name, name, desc=desc, category=category,
        abstract=True)
    ref(nid, HasSubtype, base, forward=False)
    return nid


def reference_type(nid, name, base, inverse, desc, category, symmetric=False,
                   abstract=False):
    n = add(nid, "UAReferenceType", name, name, desc=desc, category=category,
            abstract=abstract)
    n.inverse = inverse
    n.symmetric = symmetric
    ref(nid, HasSubtype, base, forward=False)
    return nid


def _member_var(owner, owner_sym, name, datatype, typedef, rule, reftype, desc,
                valuerank="-1", array=None):
    nid = _mid()
    attrs = {"DataType": datatype, "ValueRank": valuerank}
    if array is not None:
        attrs["ArrayDimensions"] = str(array)
    add(nid, "UAVariable", name, f"{owner_sym}_{name}", desc=desc,
        parent=T(owner), attrs=attrs)
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid


def prop_var(owner, owner_sym, name, datatype, desc, rule=MR_Optional,
             valuerank="-1", array=None):
    return _member_var(owner, owner_sym, name, datatype, PropertyType, rule,
                       HasProperty, desc, valuerank, array)


def comp_var(owner, owner_sym, name, datatype, desc, rule=MR_Optional,
             valuerank="-1", array=None):
    return _member_var(owner, owner_sym, name, datatype, BaseDataVariableType,
                       rule, HasComponent, desc, valuerank, array)


def obj_member(owner, owner_sym, name, typedef, desc, rule=MR_Optional,
               reftype=HasComponent):
    nid = _mid()
    add(nid, "UAObject", name, f"{owner_sym}_{name}", desc=desc, parent=T(owner))
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid


def method(owner, owner_sym, name, desc, rule=MR_Optional, inargs=None,
           outargs=None):
    nid = _mid()
    add(nid, "UAMethod", name, f"{owner_sym}_{name}", desc=desc, parent=T(owner))
    ref(nid, HasModellingRule, rule)
    ref(nid, HasComponent, T(owner), forward=False)
    ref(owner, HasComponent, T(nid))
    if inargs:
        _args(nid, f"{owner_sym}_{name}", "InputArguments", inargs)
    if outargs:
        _args(nid, f"{owner_sym}_{name}", "OutputArguments", outargs)
    return nid


def _args(method_nid, method_sym, bname, args):
    nid = _mid()
    add(nid, "UAVariable", bname, f"{method_sym}_{bname}", parent=T(method_nid),
        attrs={"DataType": Argument, "ValueRank": "1",
               "ArrayDimensions": str(len(args))})
    ref(nid, HasModellingRule, MR_Mandatory)
    ref(nid, HasTypeDefinition, PropertyType)
    ref(nid, HasProperty, T(method_nid), forward=False)
    ref(method_nid, HasProperty, T(nid))
    parts = ['<Value>',
             '<ListOfExtensionObject xmlns="http://opcfoundation.org/UA/2008/02/Types.xsd">']
    for arg in args:
        aname, adtype, adesc = arg[0], arg[1], arg[2]
        arank = arg[3] if len(arg) > 3 else -1
        parts.append("<ExtensionObject><TypeId><Identifier>i=297</Identifier></TypeId>")
        parts.append("<Body><Argument>")
        parts.append(f"<Name>{sx.escape(aname)}</Name>")
        parts.append(f"<DataType><Identifier>{adtype}</Identifier></DataType>")
        if arank is not None and arank >= 0:
            parts.append(f"<ValueRank>{arank}</ValueRank>"
                         "<ArrayDimensions><UInt32>0</UInt32></ArrayDimensions>")
        else:
            parts.append("<ValueRank>-1</ValueRank><ArrayDimensions/>")
        if adesc:
            parts.append(f"<Description><Text>{sx.escape(adesc)}</Text></Description>")
        parts.append("</Argument></Body></ExtensionObject>")
    parts.append("</ListOfExtensionObject></Value>")
    NODES[nid].value = "".join(parts)
    return nid


def placeholder_obj(owner, owner_sym, name, typedef, desc, rule=MR_OptionalPlaceholder,
                    reftype=HasComponent):
    nid = _mid()
    add(nid, "UAObject", name, f"{owner_sym}_{name.strip('<>')}", desc=desc,
        parent=T(owner))
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid


def enum_type(nid, name, desc, category, fields):
    add(nid, "UADataType", name, name, desc=desc, category=category)
    ref(nid, HasSubtype, Enumeration, forward=False)
    dparts = [f'<Definition Name="{name}">']
    for (fname, val, fdesc) in fields:
        if fdesc:
            dparts.append(f'<Field Name="{sx.escape(fname)}" Value="{val}">')
            dparts.append(f'<Description>{sx.escape(fdesc)}</Description></Field>')
        else:
            dparts.append(f'<Field Name="{sx.escape(fname)}" Value="{val}"/>')
    dparts.append("</Definition>")
    NODES[nid].definition = "".join(dparts)
    es = nid + 900
    ref(nid, HasProperty, T(es))
    add(es, "UAVariable", "EnumStrings", f"{name}_EnumStrings", parent=T(nid),
        attrs={"DataType": LocalizedText, "ValueRank": "1",
               "ArrayDimensions": str(len(fields))})
    ref(es, HasTypeDefinition, PropertyType)
    ref(es, HasProperty, T(nid), forward=False)
    vp = ['<Value>',
          '<ListOfLocalizedText xmlns="http://opcfoundation.org/UA/2008/02/Types.xsd">']
    for (fname, val, fdesc) in fields:
        vp.append(f"<LocalizedText><Text>{sx.escape(fname)}</Text></LocalizedText>")
    vp.append("</ListOfLocalizedText></Value>")
    NODES[es].value = "".join(vp)
    return nid


def struct_type(nid, name, desc, category, fields):
    add(nid, "UADataType", name, name, desc=desc, category=category)
    ref(nid, HasSubtype, Structure, forward=False)
    dparts = [f'<Definition Name="{name}">']
    for (fname, dtype, vrank, fdesc) in fields:
        extra = f' ValueRank="{vrank}"' if vrank is not None else ""
        if fdesc:
            dparts.append(f'<Field Name="{sx.escape(fname)}" DataType="{dtype}"{extra}>')
            dparts.append(f'<Description>{sx.escape(fdesc)}</Description></Field>')
        else:
            dparts.append(f'<Field Name="{sx.escape(fname)}" DataType="{dtype}"{extra}/>')
    dparts.append("</Definition>")
    NODES[nid].definition = "".join(dparts)
    for enc_bname, enc_sym in (("Default Binary", "DefaultBinary"),
                               ("Default XML", "DefaultXml")):
        enc = _mid()
        add(enc, "UAObject", enc_bname, f"{name}_{enc_sym}", parent=T(nid))
        ref(enc, HasTypeDefinition, DataTypeEncodingType)
        ref(enc, HasEncoding, T(nid), forward=False)
        ref(nid, HasEncoding, T(enc))
    return nid


def well_known(nid, name, typedef, parent, desc, reftype=HasComponent):
    add(nid, "UAObject", name, name, desc=desc, parent=T(parent) if isinstance(parent, int) else parent)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(parent) if isinstance(parent, int) else parent, forward=False)
    return nid


def set_string(owner, owner_sym, name, value, datatype=String):
    nid = _mid()
    add(nid, "UAVariable", name, f"{owner_sym}_{name}", parent=T(owner),
        attrs={"DataType": datatype})
    ref(nid, HasTypeDefinition, PropertyType)
    ref(nid, HasProperty, T(owner), forward=False)
    ref(owner, HasProperty, T(nid))
    NODES[nid].value = (f'<Value><uax:String xmlns:uax="http://opcfoundation.org/'
                        f'UA/2008/02/Types.xsd">{sx.escape(value)}</uax:String></Value>')
    return nid


# ===========================================================================
# ============================  MODEL DEFINITION  ===========================
# ===========================================================================
CAT = "Observability Export"
CAT_DT = "Observability Export DataTypes"

# --- ReferenceTypes --------------------------------------------------------
reference_type(60001, "BindsToNode", NonHierarchicalReferences, "IsBoundBy",
               "Links a BoundItem to the companion-specification Variable, event source or "
               "Program in the AddressSpace that it exposes for observability export. The "
               "target is the authoritative semantic node; the BoundItem does not copy its "
               "meaning.",
               CAT)
reference_type(60002, "ExportedBy", NonHierarchicalReferences,
               "Exports",
               "Links an ObservabilityBinding to the optional OPC UA Part 14 PubSub node(s) that "
               "export it (a PublishedDataSet, DataSetWriter or DataSetReader) - the concrete OTEL "
               "exporter for the binding's signal. Forward 'ExportedBy' reads binding -> exporter; "
               "the inverse 'Exports' reads exporter -> binding. Absent (and never required) when "
               "the binding is not exported over PubSub - a Server may instead serve the binding "
               "over the classic client/server (RPC) interface.",
               CAT)
reference_type(60003, "HasBaseBinding", NonHierarchicalReferences, "IsBaseBindingOf",
               "Links a derived or composing ObservabilityBinding to a base ObservabilityBinding "
               "whose fields it extends or composes (e.g. a Machine binding to the Device-facet "
               "binding it builds on). Optional browse convenience used where the base binding "
               "node is present in the same AddressSpace; the portable, cross-specification "
               "lineage carrier is ObservabilityBinding.BaseDataSetClassIds.",
               CAT)
reference_type(60004, "Collects", NonHierarchicalReferences, "CollectedBy",
               "Links the server-wide Observability registry to the ObservabilityBindingGroups it "
               "collects. Forward 'Collects' reads registry -> group (the discovery path to every "
               "group that exports observability data, across instances and specifications); the "
               "inverse 'CollectedBy' reads group -> registry. Non-hierarchical: a group's single "
               "hierarchical parent is the IObservableType object that contains it, so this "
               "cross-link never forms a hierarchy loop. Distinct from ExportedBy/Exports, which "
               "links a binding to its optional Part 14 PubSub exporter.",
               CAT)

# --- Enumerations ----------------------------------------------------------
enum_type(60051, "BoundItemKindEnum",
          "Generic role of a bound item for routing/bridging to an observability backend. It "
          "is intentionally domain-agnostic: a bridge maps each Kind to its target signal "
          "without understanding the companion-specification semantics.", CAT_DT, [
    ("Telemetry", 0, "A measured/process value that changes continuously (maps to a metric time series)."),
    ("Status", 1, "A discrete state/health/mode value (maps to a numeric-state gauge)."),
    ("Metric", 2, "An aggregated KPI or computed value."),
    ("Counter", 3, "A monotonically increasing counter/total."),
    ("Event", 4, "An event or condition field (maps to a log record or a span)."),
    ("Dimension", 5, "An attribute/label that qualifies the metrics, logs and traces of its binding (an OTEL attribute or Resource dimension), not a measured value. Applied to every data point the binding produces."),
    ("Identification", 6, "Static nameplate/identity information, typically emitted as an OTEL Resource attribute."),
    ("Other", 7, "Any other role."),
])

enum_type(60053, "MetricInstrumentTypeEnum",
          "The OpenTelemetry-style metric instrument a bound value maps to. Lets a bridge "
          "emit the correct instrument without domain knowledge; complements the coarser "
          "BoundItemKindEnum.", CAT_DT, [
    ("Counter", 0, "Monotonically increasing synchronous sum (OTEL Counter)."),
    ("UpDownCounter", 1, "Non-monotonic synchronous sum (OTEL UpDownCounter)."),
    ("Histogram", 2, "Synchronous distribution of values (OTEL Histogram)."),
    ("Gauge", 3, "Synchronous last-value sample (OTEL Gauge)."),
    ("ObservableCounter", 4, "Asynchronous monotonic sum, observed on collect (OTEL ObservableCounter)."),
    ("ObservableUpDownCounter", 5, "Asynchronous non-monotonic sum (OTEL ObservableUpDownCounter)."),
    ("ObservableGauge", 6, "Asynchronous last-value sample (OTEL ObservableGauge)."),
])

enum_type(60054, "MetricTemporalityEnum",
          "Aggregation temporality of a metric value, so a bridge accumulates or reports it "
          "correctly.", CAT_DT, [
    ("Cumulative", 0, "The value is a running total since a fixed start (OTEL cumulative)."),
    ("Delta", 1, "The value is the change since the previous report (OTEL delta)."),
])

enum_type(60052, "ObservabilitySignalKindEnum",
          "The OTEL signal an observability binding exposes: metrics (a Part 14 data DataSet, "
          "PublishedDataItems), logs (an event DataSet, PublishedEvents), or traces (spans "
          "produced from Program executions, audit events or correlated events). A binding is "
          "exactly one signal kind.", CAT_DT, [
    ("Metrics", 0, "A metric set: grouped Variable values mapped to OTEL metric instruments (PublishedDataItemsType)."),
    ("Logs", 1, "A log stream: selected event fields from a notifier mapped to OTEL LogRecords (PublishedEventsType)."),
    ("Traces", 2, "A trace/span stream: Program executions, audit events or correlated events mapped to OTEL spans (PublishedEventsType)."),
])

# --- Structures ------------------------------------------------------------
struct_type(60060, "BoundItemDataType",
            "Machine-readable descriptor of a single bound item: how to LOCATE it "
            "(BrowsePath relative to StartingNode, or an absolute SourceNodeId), its "
            "routing role (Kind) and the SEMANTIC cross-reference back to the companion "
            "model (TypeDefinition, BrowseName, ModelNamespaceUri, SemanticReferenceUri), "
            "which is retained so it can be exported to a disconnected consumer.", CAT_DT, [
    ("FieldName", String, None, "Stable logical field name; matches the PubSub DataSet field name."),
    ("Kind", T(60051), None, "Generic routing role of the item."),
    ("AttributeId", UInt32, None, "Attribute of the source node to expose (default 13 = Value)."),
    ("SamplingIntervalHint", Duration, None, "Recommended sampling/publishing interval, in ms."),
    ("IndexRange", NumericRange, None, "Optional sub-range for array values."),
    ("StartingNode", NodeId_, None, "Node the BrowsePath is resolved from (default: the bound root)."),
    ("BrowsePath", RelativePath, None, "RECOMMENDED locator: RelativePath from StartingNode (type-level, portable)."),
    ("SourceNodeId", NodeId_, None, "Alternative absolute locator (instance/server-specific)."),
    ("SourceTypeDefinition", NodeId_, None, "TypeDefinition of the source node (semantic identity)."),
    ("SourceBrowseName", QualifiedName, None, "Namespace-qualified BrowseName of the source node."),
    ("ModelNamespaceUri", String, None, "Namespace URI of the companion model that defines the source."),
    ("DataSetFieldId", Guid, None, "GUID correlating this item to Part 14 FieldMetaData.dataSetFieldId."),
    ("SourceBindingClassId", Guid, None, "Provenance: DataSetClassId of the base observability binding this field originates from (its facet). Lets a subscriber partition a composed DataSet into exact per-base-class field subsets. Absent for fields defined by this binding itself."),
    ("SemanticReferenceUri", String, None, "Optional external semantic identifier (e.g. IRDI/CDD) for the item."),
    ("EventFieldOperand", SimpleAttributeOperand, None, "For a log/trace (event-DataSet) field: the Part 14 SimpleAttributeOperand that selects it (alternative/complement to BrowsePath, whose segments are then relative to the event TypeDefinition)."),
    ("MetricInstrumentType", T(60053), None, "OTEL metric instrument this value maps to (Counter, Histogram, Gauge, …), for a Metrics binding."),
    ("Unit", String, None, "UCUM unit annotation for the metric; if absent a bridge derives it from the source node's EngineeringUnits."),
    ("ExplicitBucketBoundaries", Double, "1", "For a Histogram instrument: the explicit bucket boundaries."),
    ("MetricTemporality", T(60054), None, "Aggregation temporality (Cumulative/Delta) of the metric value."),
    ("Monotonic", Boolean, None, "Whether the metric is monotonic; if absent it is implied by MetricInstrumentType."),
    ("DimensionConstantValue", String, None, "For a Kind=Dimension item with a constant value: the attribute value (key is FieldName). Absent when the dimension value is read from the source node."),
])

# Note: the portable "full binding" interchange DataTypes (ObservabilityBindingDataType,
# ObservabilityBindingConfigurationDataType) are deferred to a future revision; a binding is
# authored from the browsable model and an out-of-band descriptor for now.

# --- ObjectTypes -----------------------------------------------------------
# BoundItemType and subtypes
object_type(60012, "BoundItemType", BaseObjectType,
            "A single item bound for observability export: it references the companion-spec node "
            "it exposes (BindsToNode and/or a BrowsePath) and carries the routing role "
            "(Kind) and the semantic cross-reference retained for export.", CAT)
BI = "BoundItemType"
prop_var(60012, BI, "FieldName", String, "Stable logical field name of the item.", rule=MR_Mandatory)
prop_var(60012, BI, "Kind", T(60051), "Generic routing role of the item.", rule=MR_Mandatory)
prop_var(60012, BI, "AttributeId", UInt32, "Attribute of the source node to expose (default 13 = Value).")
prop_var(60012, BI, "BrowsePath", RelativePath, "RECOMMENDED locator: RelativePath from the bound root; resolved per instance.")
prop_var(60012, BI, "StartingNode", NodeId_, "Node the BrowsePath is resolved from (default: the bound root).")
prop_var(60012, BI, "SourceNodeId", NodeId_, "Alternative absolute locator (instance/server-specific).")
prop_var(60012, BI, "SamplingIntervalHint", Duration, "Recommended sampling/publishing interval (ms).")
prop_var(60012, BI, "IndexRange", NumericRange, "Optional sub-range for array values.")
prop_var(60012, BI, "SourceTypeDefinition", NodeId_, "TypeDefinition of the source node (semantic identity).")
prop_var(60012, BI, "SourceBrowseName", QualifiedName, "Namespace-qualified BrowseName of the source node.")
prop_var(60012, BI, "ModelNamespaceUri", String, "Namespace URI of the companion model defining the source.")
prop_var(60012, BI, "DataSetFieldId", Guid, "GUID correlating the item to Part 14 FieldMetaData.")
prop_var(60012, BI, "SourceBindingClassId", Guid,
         "Provenance: DataSetClassId of the base observability binding this field originates from "
         "(its facet). Lets a subscriber partition a composed DataSet into exact per-base-class "
         "field subsets. Absent for fields defined by this binding itself.")
prop_var(60012, BI, "SemanticReferenceUri", String, "Optional external semantic identifier (e.g. IRDI/CDD).")
prop_var(60012, BI, "DimensionConstantValue", String,
         "For a Kind=Dimension item whose attribute value is a constant (not read from a node): "
         "the attribute value; the attribute key is FieldName. Absent for a node-sourced dimension "
         "(which uses its BrowsePath).")

object_type(60013, "BoundVariableType", T(60012),
            "A bound Variable exposed as a PubSub DataSet field.", CAT)
BV = "BoundVariableType"
prop_var(60013, BV, "MetricInstrumentType", T(60053),
         "OTEL metric instrument this value maps to (Counter, UpDownCounter, Histogram, Gauge and "
         "the observable variants). When absent a bridge applies the default for the item's "
         "Kind.")
prop_var(60013, BV, "Unit", String,
         "UCUM unit annotation for the metric. When absent a bridge derives the unit from the "
         "source node's EngineeringUnits (EUInformation) where present.")
prop_var(60013, BV, "ExplicitBucketBoundaries", Double,
         "For a Histogram instrument: the explicit bucket boundaries a bridge configures.",
         valuerank="1")
prop_var(60013, BV, "MetricTemporality", T(60054),
         "Aggregation temporality (Cumulative/Delta) of the metric value, so a bridge accumulates "
         "or reports it correctly.")
prop_var(60013, BV, "Monotonic", Boolean,
         "Whether the metric is monotonically increasing. When absent, monotonicity is implied by "
         "MetricInstrumentType (e.g. Counter is monotonic, UpDownCounter is not).")

object_type(60017, "BoundEventFieldType", T(60012),
            "A bound event field of a log or trace (event-sourced) binding, selected by a Part 14 "
            "SimpleAttributeOperand. Its BrowsePath is resolved relative to the event "
            "TypeDefinition (SourceTypeDefinition), not the AddressSpace instance; the "
            "EventSourcePath on the ObservabilityBinding names the notifier it is selected from.", CAT)
prop_var(60017, "BoundEventFieldType", "EventFieldOperand", SimpleAttributeOperand,
         "The Part 14 SimpleAttributeOperand that selects this field (TypeDefinitionId, "
         "BrowsePath, AttributeId); maps directly to a PublishedEvents SelectedFields entry.")

# ObservabilityBindingType
object_type(60011, "ObservabilityBindingType", BaseObjectType,
            "One observability binding on a bound object or type. It declares the OTEL signal "
            "kind it exposes (metrics, logs or traces), lists the bound items (browsable and/or "
            "as a compact array), carries the OTEL mapping metadata, and may reference the Part 14 "
            "nodes that realize it. It lives in an ObservabilityBindingGroup contained by the "
            "bound instance; its stable DataSetClassId already encodes the bound type, the signal "
            "kind and the major version.", CAT)
SB = "ObservabilityBindingType"
prop_var(60011, SB, "SignalKind", T(60052),
         "The OTEL signal this binding exposes: Metrics (a data DataSet), Logs (an event "
         "DataSet) or Traces (spans from Program executions, audit or correlated events).",
         rule=MR_Mandatory)
prop_var(60011, SB, "ConfigurationVersion", ConfigurationVersionDataType,
         "Version of the binding, aligned with the realizing DataSetMetaData.")
prop_var(60011, SB, "DataSetClassId", Guid,
         "Stable DataSetClassId (Part 14) identifying the observability class this binding defines "
         "- a metric set, a log stream, or a trace stream - so subscribers recognize the same "
         "class across servers. It is a semantic class identity, not a guarantee of a fixed field "
         "layout (see the DataSetClassId clause). Deterministic.", rule=MR_Mandatory)
prop_var(60011, SB, "BaseDataSetClassIds", Guid,
         "DataSetClassIds of the base facet bindings this binding extends or composes (its "
         "class lineage). This binding's own DataSetClassId identifies the composed/derived "
         "class; a subscriber that knows a base class-id consumes the matching field subset "
         "(see BoundItemType.SourceBindingClassId).", valuerank="1")
prop_var(60011, SB, "DataSetCardinalityPath", RelativePath,
         "RelativePath to the cardinality level: the Server/bridge produces one DataSet per matched "
         "instance of it (default: the bound root); placeholders below it become fields within that "
         "produced DataSet. The DataSetClassId is shared across those DataSets (one class, many "
         "writers).")
prop_var(60011, SB, "DataSetMetaData", DataSetMetaDataType,
         "Part 14 DataSetMetaData for this DataSet (fields, dataSetClassId, "
         "configurationVersion), exposed so a consumer gets the class schema offline.")
prop_var(60011, SB, "EventSourcePath", RelativePath,
         "For a Logs or Traces binding: RelativePath to the event notifier to subscribe to "
         "(default: the cardinality anchor, i.e. the bound root when DataSetCardinalityPath "
         "is omitted).")
prop_var(60011, SB, "Filter", ContentFilter,
         "For a Logs or Traces binding: optional ContentFilter (event where-clause).")
prop_var(60011, SB, "LogTemplate", String,
         "For a Logs binding: a structured-log message template with {FieldName} holes that "
         "reference the binding's bound event fields, so a bridge can render an OTEL LogRecord Body "
         "while still carrying the fields as attributes.")
prop_var(60011, SB, "LogSeverityFieldName", String,
         "For a Logs binding: FieldName of the bound field carrying severity, mapped to the "
         "OTEL LogRecord SeverityNumber/SeverityText.")
prop_var(60011, SB, "LogBodyFieldName", String,
         "For a Logs binding: FieldName of the bound field carrying the rendered body, an "
         "alternative to LogTemplate when the Server already produces the message text.")
prop_var(60011, SB, "LogTimestampFieldName", String,
         "For a Logs binding: FieldName of the bound field carrying the record timestamp, "
         "mapped to the OTEL LogRecord Timestamp.")
prop_var(60011, SB, "SpanNameTemplate", String,
         "For a Traces binding: a span-name template with {FieldName} holes referencing bound "
         "event fields, rendered by a bridge to the OTEL span name.")
prop_var(60011, SB, "SpanNameFieldName", String,
         "For a Traces binding: FieldName of the bound field carrying the span name (alternative "
         "to SpanNameTemplate).")
prop_var(60011, SB, "TraceIdFieldName", String,
         "For a Traces binding: FieldName of the bound field carrying the trace id (16-byte hex "
         "or opaque). When absent a bridge derives or generates a trace id.")
prop_var(60011, SB, "SpanIdFieldName", String,
         "For a Traces binding: FieldName of the bound field carrying the span id (8-byte hex or "
         "opaque). When absent a bridge generates a span id.")
prop_var(60011, SB, "ParentSpanIdFieldName", String,
         "For a Traces binding: FieldName of the bound field carrying the parent span id, so a "
         "bridge can nest the span under its caller.")
prop_var(60011, SB, "SpanStartTimeFieldName", String,
         "For a Traces binding: FieldName of the bound field carrying the span start time "
         "(default: the event Time/SourceTimestamp).")
prop_var(60011, SB, "SpanEndTimeFieldName", String,
         "For a Traces binding: FieldName of the bound field carrying the span end time. When "
         "absent (and no correlation is configured) the event is a zero-duration span.")
prop_var(60011, SB, "SpanStatusFieldName", String,
         "For a Traces binding: FieldName of the bound field carrying the span status "
         "(Ok/Error/Unset); when absent a bridge derives it from the event Severity/Quality.")
prop_var(60011, SB, "SpanKind", String,
         "For a Traces binding: the OTEL SpanKind for spans produced by this binding "
         "(Internal, Server, Client, Producer, Consumer). Constant per binding; default Internal.")
prop_var(60011, SB, "SpanCorrelationFieldName", String,
         "For a Traces binding: FieldName of the bound field whose value pairs a start event with "
         "its matching end event into one span (e.g. a Program run id). When absent, each event is "
         "an independent span.")
prop_var(60011, SB, "BoundItems", T(60060), "Compact machine-readable list of bound items (the DataSet fields).", valuerank="1")
placeholder_obj(60011, SB, "<BoundItem>", T(60012),
                "A browsable bound item (rich form of a BoundItems entry).")

# ObservabilityBindingGroupType (per-companion-spec anchor) + registry
object_type(60018, "ObservabilityBindingGroupType", FolderType,
            "A per-companion-specification group of that spec's ObservabilityBinding objects. It is "
            "contained (HasComponent) in the IObservableType object that owns the bindings, and is "
            "collected by the server-wide Observability registry (the registry Collects it; the "
            "group carries the inverse CollectedBy reference). Identified by "
            "CompanionSpecificationUri (a stable spec-level identifier, distinct from a namespace "
            "URI, because a companion specification may define several namespace URIs), so groups "
            "from different specifications on one object never collide by BrowseName.", CAT)
SG = "ObservabilityBindingGroupType"
prop_var(60018, SG, "CompanionSpecificationUri", String,
         "Stable spec-level identifier of the companion specification this group anchors. Sibling "
         "groups on one IObservableType object are unique by CompanionSpecificationUri, and each "
         "group's BrowseName is derived from this identity so sibling BrowseNames do not collide.",
         rule=MR_Mandatory)
prop_var(60018, SG, "ModelNamespaceUris", String,
         "All namespace URIs the companion specification defines/covers.",
         rule=MR_Mandatory, valuerank="1")
placeholder_obj(60018, SG, "<ObservabilityBinding>", T(60011),
                "An observability binding of this companion specification.")

# ObservabilityFolderType (the Observability registry container)
object_type(60010, "ObservabilityFolderType", FolderType,
            "The type of the server-wide Observability registry, exposed as a component of the "
            "Server Object. It is the discovery entry point: it Collects every "
            "ObservabilityBindingGroup that exports observability data through non-hierarchical "
            "Collects references (the groups themselves stay contained by their bound instances). "
            "Extensible - companion specifications contribute their instances' groups.", CAT)
SF = "ObservabilityFolderType"
# No placeholder children and no query Method: the registry Collects the ObservabilityBindingGroups
# (which live on the bound instances); a client browses those references, then each
# group's ObservabilityBinding children. Browse + Read is sufficient and keeps the type usable on a
# classic server.

# IObservableType (interface) - contains its observability binding groups directly
interface_type(60016, "IObservableType", BaseInterfaceType,
               "Interface implemented by a companion-specification ObjectType (or instance) to "
               "advertise that it exports observability data, by containing its "
               "ObservabilityBindingGroup objects directly (one per companion specification it "
               "covers; typically one for a single-specification instance). Each contained group "
               "is collected by the server-wide Observability registry (CollectedBy).", CAT)
placeholder_obj(60016, "IObservableType", "<ObservabilityBindingGroup>", T(60018),
                "A group of this object's observability bindings for one companion specification, "
                "contained here (HasComponent) and collected by the Observability registry (the "
                "inverse CollectedBy reference). Sibling groups have unique BrowseNames, "
                "distinguished by specification when several specifications are observable on the "
                "instance.")

# --- Well-known instances --------------------------------------------------
CAT_INST = "Observability Export Instances"
# The Observability registry, hooked onto the well-known Server object (i=2253) as a component -
# always present, so discovery never assumes a PubSub configuration surface. It is the discovery
# entry point for observability export.
well_known(60101, "Observability", T(60010), int(Server.split("=")[1]),
           "Server-wide registry of observability bindings, discoverable as a component of the "
           "Server object. It Collects every ObservabilityBindingGroup exposed by "
           "the Server's instances; its presence does not require any PubSub configuration.")
NODES[60101].category = CAT_INST

# ===========================================================================
# ==============================  EMISSION  =================================
# ===========================================================================
NAMESPACE = "http://opcfoundation.org/UA/"
# This model now lives in its OWN namespace (a companion specification), not the base UA
# namespace. Own nodes are emitted as ns=1;i=<n>; base UA nodes stay i=<n> (ns 0).
MODEL_NS = "http://opcfoundation.org/UA/ObservabilityExport/"
# Base UA namespace RequiredModel coordinates (informational; targets UA 1.05).
UA_REQUIRED_VERSION = "1.05.04"
UA_REQUIRED_PUBDATE = "2024-05-01T00:00:00Z"
VERSION = "0.1.0"
PUBDATE = "2026-07-01T00:00:00Z"

ALIASES = [
    ("Boolean", "i=1"), ("Byte", "i=3"), ("UInt32", "i=7"), ("Int32", "i=6"),
    ("Double", "i=11"), ("String", "i=12"), ("Guid", "i=14"), ("NodeId", "i=17"),
    ("QualifiedName", "i=20"), ("LocalizedText", "i=21"), ("Duration", "i=290"),
    ("NumericRange", "i=291"), ("Argument", "i=296"), ("RelativePath", "i=540"),
    ("Organizes", "i=35"), ("HasModellingRule", "i=37"), ("HasEncoding", "i=38"),
    ("HasTypeDefinition", "i=40"), ("HasSubtype", "i=45"), ("HasProperty", "i=46"),
    ("HasComponent", "i=47"), ("HasInterface", "i=17603"),
    ("HasDictionaryEntry", "i=17597"), ("NonHierarchicalReferences", "i=32"),
    ("DataSetMetaDataType", "i=14523"), ("SimpleAttributeOperand", "i=601"),
    ("ContentFilter", "i=586"),
]
REFTYPE_ALIAS = {v: k for k, v in ALIASES}
DATATYPE_ALIAS = {v: k for k, v in ALIASES}
_PRIO = {HasModellingRule: 0, HasSubtype: 1}


def _sorted_refs(refs):
    return sorted(range(len(refs)), key=lambda i: (_PRIO.get(refs[i][0], 2), i))


def _fmt_reftype(t):
    return REFTYPE_ALIAS.get(t, t)


def _q(s):
    """Qualify an own NodeId string with the model namespace (ns=1); base UA ids stay i=<n> (ns 0)."""
    if isinstance(s, str) and s.startswith("i="):
        tail = s[2:]
        if tail.isdigit() and int(tail) in NODES:
            return "ns=1;i=" + tail
    return s


# BrowseNames that stay in namespace 0 even on own (ns=1) nodes: the standard
# EnumStrings property and the standard DataType encoding names.
STD_BROWSENAMES = {"EnumStrings", "Default Binary", "Default XML"}


def _qbn(bname):
    """Namespace-qualify an own node's BrowseName (1:Name), except standard base names."""
    return bname if bname in STD_BROWSENAMES else "1:" + bname


def _qdef(defstr):
    """Namespace-qualify own DataType ids embedded in an enum/struct Definition string."""
    return re.sub(r'DataType="i=(\d+)"',
                  lambda m: f'DataType="{_q("i=" + m.group(1))}"', defstr)


def _emit_node(n):
    tag = n.cls
    a = [f'{tag} NodeId="{_q(T(n.nid))}"', f'BrowseName="{sx.escape(_qbn(n.bname))}"']
    if n.parent is not None:
        a.append(f'ParentNodeId="{_q(n.parent)}"')
    for k in ("DataType", "ValueRank", "ArrayDimensions"):
        if k in n.attrs:
            v = n.attrs[k]
            if k == "DataType":
                v = _q(DATATYPE_ALIAS.get(v, v))
            a.append(f'{k}="{v}"')
    if n.cls == "UAObjectType" and n.abstract:
        a.append('IsAbstract="true"')
    if n.cls == "UAReferenceType":
        a.append('Symmetric="true"' if n.symmetric else 'Symmetric="false"')
    lines = ["  <" + " ".join(a) + ">"]
    lines.append(f"    <DisplayName>{sx.escape(n.display)}</DisplayName>")
    if n.desc:
        lines.append(f"    <Description>{sx.escape(n.desc)}</Description>")
    if n.category:
        lines.append(f"    <Category>{sx.escape(n.category)}</Category>")
    lines.append("    <References>")
    for i in _sorted_refs(n.refs):
        rt, tgt, fwd = n.refs[i]
        fwd_s = "" if fwd else ' IsForward="false"'
        lines.append(f'      <Reference ReferenceType="{_q(_fmt_reftype(rt))}"{fwd_s}>{_q(tgt)}</Reference>')
    lines.append("    </References>")
    if n.cls == "UAReferenceType" and n.inverse and not n.symmetric:
        lines.append(f"    <InverseName>{sx.escape(n.inverse)}</InverseName>")
    if n.definition:
        lines.append("    " + _qdef(n.definition))
    if n.value:
        lines.append("    " + n.value)
    lines.append(f"  </{tag}>")
    return "\n".join(lines)


def emit():
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<!-- OPC UA Observability Export - a companion specification in its own namespace '
           '(http://opcfoundation.org/UA/ObservabilityExport/). Draft NodeIds. -->',
           '<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
           'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" '
           'xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
           '  <NamespaceUris>',
           f'    <Uri>{MODEL_NS}</Uri>',
           '  </NamespaceUris>',
           '  <Models>',
           f'    <Model ModelUri="{MODEL_NS}" Version="{VERSION}" PublicationDate="{PUBDATE}">',
           f'      <RequiredModel ModelUri="{NAMESPACE}" Version="{UA_REQUIRED_VERSION}" '
           f'PublicationDate="{UA_REQUIRED_PUBDATE}" />',
           '    </Model>',
           '  </Models>',
           '  <Aliases>']
    for name, val in ALIASES:
        out.append(f'    <Alias Alias="{name}">{val}</Alias>')
    out.append('  </Aliases>')
    for nid in ORDER:
        out.append(_emit_node(NODES[nid]))
    out.append('</UANodeSet>')
    return "\n".join(out) + "\n"


def emit_csv():
    return "\n".join(f"{NODES[nid].symbolic},{nid},{NODES[nid].cls[2:]}"
                     for nid in ORDER) + "\n"


# --- Annex (reference tables) ----------------------------------------------
LINK_MAP = {
    "Argument": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.6",
    "BaseDataVariableType": "https://reference.opcfoundation.org/specs/OPC-10000-5/7.4",
    "BaseInterfaceType": "https://reference.opcfoundation.org/specs/OPC-10000-5/6.9",
    "BaseObjectType": "https://reference.opcfoundation.org/specs/OPC-10000-5/6.2",
    "ConfigurationVersionDataType": "https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.2.6",
    "DataSetMetaDataType": "https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.2.4",
    "SimpleAttributeOperand": "https://reference.opcfoundation.org/specs/OPC-10000-4/7.4.4",
    "ContentFilter": "https://reference.opcfoundation.org/specs/OPC-10000-4/7.4.1",
    "PublishedDataItemsType": "https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.4",
    "PublishedEventsType": "https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.4",
    "DataSetMetaDataType": "https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.2.3",
    "DataSetReaderType": "https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.8#9.1.8.2",
    "DataSetWriterType": "https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.7#9.1.7.2",
    "Duration": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.13",
    "Enumeration": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.14",
    "FolderType": "https://reference.opcfoundation.org/specs/OPC-10000-5/6.6",
    "Guid": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.16",
    "HasComponent": "https://reference.opcfoundation.org/specs/OPC-10000-3/7.7",
    "HasDictionaryEntry": "https://reference.opcfoundation.org/specs/OPC-10000-19/6.1",
    "HasInterface": "https://reference.opcfoundation.org/specs/OPC-10000-3/7.19",
    "HasProperty": "https://reference.opcfoundation.org/specs/OPC-10000-3/5.3.3#5.3.3.2",
    "HasTypeDefinition": "https://reference.opcfoundation.org/specs/OPC-10000-3/7.13",
    "KeyValuePair": "https://reference.opcfoundation.org/specs/OPC-10000-5/12.21",
    "NodeId": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.2.1",
    "NonHierarchicalReferences": "https://reference.opcfoundation.org/specs/OPC-10000-3/7.4",
    "NumericRange": "https://reference.opcfoundation.org/specs/OPC-10000-4/7.27",
    "Organizes": "https://reference.opcfoundation.org/specs/OPC-10000-3/7.6",
    "PropertyType": "https://reference.opcfoundation.org/specs/OPC-10000-5/7.3",
    "PublishSubscribeType": "https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.3#9.1.3.2",
    "PublishedDataItemsType": "https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.4#9.1.4.3.1",
    "PublishedDataSetType": "https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.4#9.1.4.2.1",
    "QualifiedName": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.3",
    "RelativePath": "https://reference.opcfoundation.org/specs/OPC-10000-4/7.30",
    "Structure": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.32",
    "WriterGroupType": "https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.6#9.1.6.3",
    "LocalizedText": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.5",
    "String": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.26",
    "UInt32": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.37",
}
_PRIMITIVES = {"Boolean", "Byte", "UInt16", "UInt32", "Int32", "Int64", "UInt64",
               "Double", "Float", "String", "DateTime", "Guid", "NodeId",
               "QualifiedName", "LocalizedText", "Duration", "NumericRange",
               "Structure", "Enumeration"}
_OWN = None
_BASE_NAMES = {
    "i=58": "BaseObjectType", "i=61": "FolderType", "i=63": "BaseDataVariableType",
    "i=68": "PropertyType", "i=17602": "BaseInterfaceType", "i=29": "Enumeration",
    "i=22": "Structure", "i=32": "NonHierarchicalReferences",
    "i=76": "DataTypeEncodingType",
}


def _friendly(tgt):
    if tgt in _BASE_NAMES:
        return _BASE_NAMES[tgt]
    if tgt in DATATYPE_ALIAS:
        return DATATYPE_ALIAS[tgt]
    if tgt.startswith("i="):
        num = int(tgt.split("=")[1])
        if num in NODES:
            return NODES[num].bname
    return tgt


def _anchor(name):
    return "type-" + name


def _link(display):
    if not display:
        return display
    core = display
    arr = ""
    if core.endswith("[]"):
        arr = r"\[\]"
        core = core[:-2]
    core = core.strip()
    if core in _OWN:
        return f"[{core}](#{_anchor(core)})" + arr
    if core in LINK_MAP and core not in _PRIMITIVES:
        return f"[{core}]({LINK_MAP[core]})" + arr
    return core + arr


def _clink(name):
    if name in _OWN:
        return f"[`{name}`](#{_anchor(name)})"
    if name in LINK_MAP and name not in _PRIMITIVES:
        return f"[`{name}`]({LINK_MAP[name]})"
    return f"`{name}`"


def _member_rule(n):
    for rt, tgt, fwd in n.refs:
        if rt == HasModellingRule:
            return {MR_Mandatory: "Mandatory", MR_Optional: "Optional",
                    MR_OptionalPlaceholder: "OptionalPlaceholder",
                    MR_MandatoryPlaceholder: "MandatoryPlaceholder"}.get(tgt, "")
    return ""


def _supertype(n):
    for rt, tgt, fwd in n.refs:
        if rt == HasSubtype and not fwd:
            return tgt
    return ""


def _members_of(nid):
    out = []
    for rt, tgt, fwd in NODES[nid].refs:
        if rt in (HasComponent, HasProperty, HasInterface) and fwd and tgt.startswith("i="):
            num = int(tgt.split("=")[1])
            if num in NODES:
                out.append(num)
    return out


def _own_chain(nid):
    """Members inherited from OUR OWN supertypes (walk within the model)."""
    out = []
    sup = _supertype(NODES[nid])
    guard = 0
    while sup and sup.startswith("i=") and guard < 20:
        guard += 1
        snum = int(sup.split("=")[1])
        if snum not in NODES:
            break
        for m in _members_of(snum):
            out.append((m, NODES[snum].bname))
        sup = _supertype(NODES[snum])
    return out


def emit_md():
    global _OWN
    _OWN = {NODES[nid].bname for nid in ORDER
            if NODES[nid].cls in ("UAObjectType", "UADataType", "UAReferenceType")}
    obj_types = [nid for nid in ORDER if NODES[nid].cls == "UAObjectType"]
    data_types = [nid for nid in ORDER if NODES[nid].cls == "UADataType"]
    ref_types = [nid for nid in ORDER if NODES[nid].cls == "UAReferenceType"]

    method_args = {}
    for nid in ORDER:
        n = NODES[nid]
        if n.cls == "UAVariable" and n.bname == "InputArguments" and n.value:
            names = re.findall(r"<Name>([^<]+)</Name>", n.value)
            pid = int(n.parent.split("=")[1]) if n.parent else None
            if pid is not None:
                method_args[pid] = names

    md = ['<a id="annex-a"></a>', "## Annex A \u2014 Information model\n",
          "This annex is the normative node reference. It is generated from "
          "[`core-specs/extras/observability-export/tools/build_model.py`]"
          "(../extras/observability-export/tools/build_model.py) and always matches `Opc.Ua.ObservabilityExport.NodeSet2.xml`. "
          "All nodes are defined in this specification's own namespace "
          "`http://opcfoundation.org/UA/ObservabilityExport/` (namespace index 1 in the NodeSet, "
          "which requires the base OPC UA namespace); the NodeIds shown are the draft numeric "
          "identifiers within that namespace. The **Declared in** column marks "
          "members inherited from a supertype.\n"]

    md.append("### Type overview\n")
    md.append("| NodeId | BrowseName | NodeClass | Subtype of |")
    md.append("|---|---|---|---|")
    for nid in ref_types + obj_types + data_types:
        n = NODES[nid]
        md.append(f"| i={nid} | {_link(n.bname) if n.bname in _OWN else n.bname} | "
                  f"{n.cls[2:]} | {_link(_friendly(_supertype(n)))} |")
    md.append("")

    md.append("### Reference types\n")
    for nid in ref_types:
        n = NODES[nid]
        md.append(f'<a id="{_anchor(n.bname)}"></a>')
        md.append(f"#### {n.bname}  (i={nid})\n")
        md.append(f"*Subtype of:* {_link(_friendly(_supertype(n)))} \u00b7 *InverseName:* `{n.inverse}`\n")
        if n.desc:
            md.append(n.desc + "\n")

    md.append("### Object types\n")
    for nid in obj_types:
        n = NODES[nid]
        md.append(f'<a id="{_anchor(n.bname)}"></a>')
        md.append(f"#### {n.bname}  (i={nid})\n")
        md.append(f"*Inherits from:* {_link(_friendly(_supertype(n)))}\n")
        if n.desc:
            md.append(n.desc + "\n")
        rows = []
        for m in _members_of(nid):
            mn = NODES[m]
            dt = _friendly(mn.attrs.get("DataType", "")) if mn.attrs.get("DataType") else ""
            if mn.attrs.get("ValueRank", "") == "1" and dt:
                dt += "[]"
            rows.append((mn.bname, mn.cls[2:], _link(dt), _member_rule(mn), n.bname,
                         (mn.desc or "").replace("|", "/")))
        for (m, decl) in _own_chain(nid):
            mn = NODES[m]
            dt = _friendly(mn.attrs.get("DataType", "")) if mn.attrs.get("DataType") else ""
            if mn.attrs.get("ValueRank", "") == "1" and dt:
                dt += "[]"
            rows.append((mn.bname, mn.cls[2:], _link(dt), _member_rule(mn),
                         _link(decl), (mn.desc or "").replace("|", "/")))
        if rows:
            md.append("| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |")
            md.append("|---|---|---|---|---|---|")
            for r in rows:
                md.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")
            md.append("")

    md.append("### Data types\n")
    for nid in data_types:
        n = NODES[nid]
        md.append(f'<a id="{_anchor(n.bname)}"></a>')
        md.append(f"#### {n.bname}  (i={nid})\n")
        md.append(f"*Subtype of:* {_link(_friendly(_supertype(n)))}\n")
        if n.desc:
            md.append(n.desc + "\n")
        if n.definition and "Value=" in n.definition:
            md.append("| Name | Value | Description |")
            md.append("|---|---|---|")
            for mm in re.finditer(r'<Field Name="([^"]+)" Value="(\d+)"\s*(?:/>|>(?:<Description>([^<]*)</Description>)?</Field>)', n.definition):
                md.append(f"| {mm.group(1)} | {mm.group(2)} | {mm.group(3) or ''} |")
            md.append("")
        elif n.definition:
            md.append("| Field | DataType | Description |")
            md.append("|---|---|---|")
            for mm in re.finditer(r'<Field Name="([^"]+)" DataType="([^"]+)"([^>]*?)(?:/>|>(?:<Description>([^<]*)</Description>)?</Field>)', n.definition):
                dt = _link(_friendly(mm.group(2)))
                if 'ValueRank="1"' in mm.group(3):
                    dt += r"\[\]"
                md.append(f"| {mm.group(1)} | {dt} | {mm.group(4) or ''} |")
            md.append("")

    md.append("### Methods\n")
    md.append("| Method | Owning type | Input arguments | Output arguments |")
    md.append("|---|---|---|---|")
    for nid in ORDER:
        n = NODES[nid]
        if n.cls != "UAMethod":
            continue
        owner = NODES[int(n.parent.split("=")[1])].bname if n.parent else ""
        ins = ", ".join(method_args.get(nid, [])) or "(none)"
        outs = "(none)"
        for rt, tgt, fwd in n.refs:
            if rt == HasProperty and fwd and tgt.startswith("i="):
                t = int(tgt.split("=")[1])
                if NODES[t].bname == "OutputArguments" and NODES[t].value:
                    outs = ", ".join(re.findall(r"<Name>([^<]+)</Name>", NODES[t].value)) or "(none)"
        md.append(f"| {n.bname} | {_link(owner)} | {ins} | {outs} |")
    md.append("")

    md.append("### Well-known instances\n")
    md.append("| BrowseName | NodeId | TypeDefinition | Note |")
    md.append("|---|---|---|---|")
    for nid in ORDER:
        n = NODES[nid]
        if n.category != "Observability Export Instances" or n.cls != "UAObject":
            continue
        td = ""
        for rt, tgt, fwd in n.refs:
            if rt == HasTypeDefinition:
                td = _link(_friendly(tgt))
        md.append(f"| {n.bname} | i={nid} | {td} | {(n.desc or '').replace('|','/')} |")
    md.append("")
    return "\n".join(md) + "\n"


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    # The standardized NodeSet/CSV live in core-specs/observability-export; this generator lives
    # alongside the other specs' secondary tooling under core-specs/extras/observability-export.
    outdir = os.path.abspath(os.path.join(here, "..", "..", "..", "observability-export"))
    with open(os.path.join(outdir, "Opc.Ua.ObservabilityExport.NodeSet2.xml"), "w",
              encoding="utf-8") as f:
        f.write(emit())
    with open(os.path.join(outdir, "Opc.Ua.ObservabilityExport.NodeIds.csv"), "w",
              encoding="utf-8") as f:
        f.write(emit_csv())
    with open(os.path.join(here, "model-reference.md"), "w", encoding="utf-8") as f:
        f.write(emit_md())
    nt = sum(1 for k in NODES if NODES[k].cls in ("UAObjectType", "UADataType", "UAReferenceType"))
    print(f"Nodes: {len(NODES)}  (types: {nt})")
    print(f"Member id range: 60500..{_next_member[0] - 1}")
