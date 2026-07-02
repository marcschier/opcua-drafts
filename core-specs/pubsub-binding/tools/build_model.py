#!/usr/bin/env python3
"""
Generator for the OPC UA PubSub Scenario Binding specification (WG draft).

Emits, from a single in-code source of truth:
  * Opc.Ua.PubSubBinding.NodeSet2.xml  - the information model (UANodeSet)
  * Opc.Ua.PubSubBinding.NodeIds.csv   - the NodeId assignments
  * model-reference.md                 - the generated Annex A (node reference)

The model is a proposed addition to the OPC UA BASE namespace
(http://opcfoundation.org/UA/, namespace index 0). All nodes therefore use plain
`i=<n>` NodeIds. NodeIds are PROVISIONAL and drawn from a currently-free block
(60000+); the final NodeIds are assigned by the OPC Foundation. The model builds
on the Part 14 PubSub types (which are themselves in the base namespace), so there
are no cross-namespace references.
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
ActionTargetDataType = "i=18593"
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
CAT = "PubSub Scenario Binding"
CAT_DT = "PubSub Scenario Binding DataTypes"

# --- ReferenceTypes --------------------------------------------------------
reference_type(60001, "BindsToNode", NonHierarchicalReferences, "IsBoundBy",
               "Links a BoundItem to the companion-specification Variable or Method "
               "in the AddressSpace that it exposes for a scenario. The target is the "
               "authoritative semantic node; the BoundItem does not copy its meaning.",
               CAT)
reference_type(60002, "ScenarioRealizedVia", NonHierarchicalReferences,
               "SupportsScenario",
               "Links a ScenarioBinding to the optional OPC UA Part 14 PubSub node(s) that "
               "realize it (a PublishedDataSet, DataSetWriter, DataSetReader or an "
               "ActionTarget). Forward 'ScenarioRealizedVia' reads binding -> realization; "
               "the inverse 'SupportsScenario' reads realization -> binding. Absent (and "
               "never required) when the binding is not realized over PubSub.",
               CAT)

# --- Enumerations ----------------------------------------------------------
enum_type(60050, "ScenarioBindingDirectionEnum",
          "The role the server offers for a ScenarioBinding, and hence what a client "
          "sets up on the other side.", CAT_DT, [
    ("Publisher", 0, "The server publishes the bound data; a client sets up a subscriber."),
    ("Subscriber", 1, "The server subscribes to the bound data; a client sets up a publisher."),
    ("ActionInvoker", 2, "The server invokes bound Methods/Actions on receipt; a client sends the trigger."),
    ("ActionResponder", 3, "The server responds to bound Actions; a client invokes them."),
    ("Bidirectional", 4, "Both data and action directions apply."),
])

enum_type(60051, "BoundItemKindEnum",
          "Generic role of a bound item for routing/bridging. It is intentionally "
          "domain-agnostic: a bridge maps each Kind to its target system without "
          "understanding the companion-specification semantics.", CAT_DT, [
    ("Telemetry", 0, "A measured/process value that changes continuously (maps to a time series)."),
    ("Status", 1, "A discrete state/health/mode value."),
    ("Configuration", 2, "A configuration/parameter value that changes rarely."),
    ("Metric", 3, "An aggregated KPI or computed value."),
    ("Counter", 4, "A monotonically increasing counter/total."),
    ("Event", 5, "An event or condition (maps to a log/alarm stream)."),
    ("Command", 6, "A bound Method/Action invocation (maps to an action)."),
    ("Setpoint", 7, "A writable setpoint/target value."),
    ("Identification", 8, "Static nameplate/identity information."),
    ("Other", 9, "Any other role."),
])

enum_type(60052, "ScenarioContentKindEnum",
          "Whether a scenario binding realizes as a Part 14 data DataSet "
          "(PublishedDataItems) or an event DataSet (PublishedEvents). A binding is exactly "
          "one DataSet.", CAT_DT, [
    ("DataItems", 0, "A data DataSet: grouped Variable values (PublishedDataItemsType)."),
    ("Events", 1, "An event DataSet: selected event fields from a notifier (PublishedEventsType)."),
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
    ("OwningObjectPath", RelativePath, None, "For a bound Method: RelativePath to the Object it is called on (default: the bound root)."),
    ("SourceTypeDefinition", NodeId_, None, "TypeDefinition of the source node (semantic identity)."),
    ("SourceBrowseName", QualifiedName, None, "Namespace-qualified BrowseName of the source node."),
    ("ModelNamespaceUri", String, None, "Namespace URI of the companion model that defines the source."),
    ("DataSetFieldId", Guid, None, "GUID correlating this item to Part 14 FieldMetaData.dataSetFieldId."),
    ("SemanticReferenceUri", String, None, "Optional external semantic identifier (e.g. IRDI/CDD) for the item."),
    ("EventFieldOperand", SimpleAttributeOperand, None, "For an event-DataSet field: the Part 14 SimpleAttributeOperand that selects it (alternative/complement to BrowsePath, whose segments are then relative to the event TypeDefinition)."),
])

struct_type(60065, "ScenarioBindingDataType",
            "Machine-readable descriptor of one scenario binding: a scenario URI, the "
            "offered direction and the list of bound items, plus optional names of the "
            "Part 14 artifacts that realize it.", CAT_DT, [
    ("Name", String, None, "Human-readable name of the binding."),
    ("ScenarioUri", String, None, "URI of the integration scenario this binding serves."),
    ("Direction", T(60050), None, "Role the server offers for this binding."),
    ("ConfigurationVersion", ConfigurationVersionDataType, None, "Version of the binding, aligned with the realizing DataSetMetaData."),
    ("BoundItems", T(60060), "1", "The bound items (the DataSet fields)."),
    ("DataSetClassId", Guid, None, "Stable DataSetClassId (Part 14) identifying the class of this DataSet across servers."),
    ("ContentKind", T(60052), None, "Whether this binding is a data or an event DataSet."),
    ("DataSetCardinalityPath", RelativePath, None, "RelativePath to the cardinality level: one DataSet is produced per matched instance of it (default: the bound root); placeholders below it become fields."),
    ("EventSourcePath", RelativePath, None, "For an event DataSet: RelativePath to the event notifier (default: the cardinality anchor, i.e. the bound root when DataSetCardinalityPath is omitted)."),
    ("Filter", ContentFilter, None, "For an event DataSet: optional ContentFilter (event where-clause)."),
    ("PublishedDataSetName", String, None, "Name of the realizing Part 14 PublishedDataSet, if any."),
    ("WriterGroupName", String, None, "Name of the realizing Part 14 WriterGroup, if any."),
])

struct_type(60070, "ScenarioBindingConfigurationDataType",
            "Portable, machine-readable 'full binding' for a companion specification or "
            "type: the set of scenario bindings plus the model they apply to. Mirrors the "
            "Part 14 PubSubConfigurationDataType pattern; a generator expands it into "
            "AddressSpace nodes and Part 14 runtime configuration.", CAT_DT, [
    ("CompanionSpecificationUri", String, None, "Stable spec-level identifier of the companion specification (the per-spec group anchor identity; distinct from a namespace URI)."),
    ("ModelNamespaceUris", String, "1", "All namespace URIs the companion specification defines/covers."),
    ("AppliesToType", QualifiedName, None, "BrowseName of the companion ObjectType the bindings are defined on."),
    ("ConfigurationVersion", ConfigurationVersionDataType, None, "Version of this binding configuration."),
    ("ScenarioBindings", T(60065), "1", "The scenario bindings."),
])

# --- ObjectTypes -----------------------------------------------------------
# BoundItemType and subtypes
object_type(60012, "BoundItemType", BaseObjectType,
            "A single item bound into a scenario: it references the companion-spec node "
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
prop_var(60012, BI, "SemanticReferenceUri", String, "Optional external semantic identifier (e.g. IRDI/CDD).")

object_type(60013, "BoundVariableType", T(60012),
            "A bound Variable exposed as a PubSub DataSet field.", CAT)

object_type(60014, "BoundMethodType", T(60012),
            "A bound Method exposed as an invokable action; may be realized as a Part 14 "
            "Action/ActionTarget.", CAT)
prop_var(60014, "BoundMethodType", "OwningObjectPath", RelativePath,
         "RelativePath to the Object the Method is called on (default: the bound root).")

object_type(60017, "BoundEventFieldType", T(60012),
            "A bound event field of an event DataSet, selected by a Part 14 "
            "SimpleAttributeOperand. Its BrowsePath is resolved relative to the event "
            "TypeDefinition (SourceTypeDefinition), not the AddressSpace instance; the "
            "EventSourcePath on the ScenarioBinding names the notifier it is selected from.", CAT)
prop_var(60017, "BoundEventFieldType", "EventFieldOperand", SimpleAttributeOperand,
         "The Part 14 SimpleAttributeOperand that selects this field (TypeDefinitionId, "
         "BrowsePath, AttributeId); maps directly to a PublishedEvents SelectedFields entry.")

# ScenarioBindingType
object_type(60011, "ScenarioBindingType", BaseObjectType,
            "One scenario binding on a bound object or type. It declares the scenario "
            "URI and direction, lists the bound items (browsable and/or as a compact "
            "array), and may reference the Part 14 nodes that realize it.", CAT)
SB = "ScenarioBindingType"
prop_var(60011, SB, "ScenarioUri", String, "URI of the integration scenario this binding serves.", rule=MR_Mandatory)
prop_var(60011, SB, "Direction", T(60050), "Role the server offers for this binding.", rule=MR_Mandatory)
prop_var(60011, SB, "ConfigurationVersion", ConfigurationVersionDataType,
         "Version of the binding, aligned with the realizing DataSetMetaData.")
prop_var(60011, SB, "DataSetClassId", Guid,
         "Stable DataSetClassId (Part 14) identifying the class of the DataSet this binding "
         "defines, so subscribers recognize the same DataSet class across servers. It is a "
         "semantic class identity, not a guarantee of a fixed field layout (see the "
         "DataSetClassId clause). Deterministic.", rule=MR_Mandatory)
prop_var(60011, SB, "ContentKind", T(60052),
         "Whether the binding realizes as a data DataSet (PublishedDataItems) or an event "
         "DataSet (PublishedEvents).", rule=MR_Mandatory)
prop_var(60011, SB, "DataSetCardinalityPath", RelativePath,
         "RelativePath to the cardinality level: the Server/bridge produces one DataSet per "
         "matched instance of it (default: the bound root); placeholders below it become "
         "fields. The DataSetClassId is shared across those DataSets (one class, many writers).")
prop_var(60011, SB, "DataSetMetaData", DataSetMetaDataType,
         "Part 14 DataSetMetaData for this DataSet (fields, dataSetClassId, "
         "configurationVersion), exposed so a consumer gets the class schema offline.")
prop_var(60011, SB, "EventSourcePath", RelativePath,
         "For an event DataSet: RelativePath to the event notifier to subscribe to "
         "(default: the cardinality anchor, i.e. the bound root when DataSetCardinalityPath "
         "is omitted).")
prop_var(60011, SB, "Filter", ContentFilter,
         "For an event DataSet: optional ContentFilter (event where-clause).")
prop_var(60011, SB, "BoundItems", T(60060), "Compact machine-readable list of bound items (the DataSet fields).", valuerank="1")
placeholder_obj(60011, SB, "<BoundItem>", T(60012),
                "A browsable bound item (rich form of a BoundItems entry).")

# ScenarioBindingGroupType (per-companion-spec anchor) + registry
object_type(60018, "ScenarioBindingGroupType", FolderType,
            "A per-companion-specification anchor grouping that spec's ScenarioBinding "
            "objects, so bindings from different companion specifications registered in one "
            "container never collide by BrowseName. Identified by CompanionSpecificationUri "
            "(a stable spec-level identifier, distinct from a namespace URI, because a "
            "companion specification may define several namespace URIs).", CAT)
SG = "ScenarioBindingGroupType"
prop_var(60018, SG, "CompanionSpecificationUri", String,
         "Stable spec-level identifier of the companion specification this group anchors. "
         "Groups are unique per CompanionSpecificationUri.", rule=MR_Mandatory)
prop_var(60018, SG, "ModelNamespaceUris", String,
         "All namespace URIs the companion specification defines/covers.",
         rule=MR_Mandatory, valuerank="1")
placeholder_obj(60018, SG, "<ScenarioBinding>", T(60011),
                "A scenario binding of this companion specification.")

# PubSubScenarioBindingsType (container)
object_type(60010, "PubSubScenarioBindingsType", FolderType,
            "A discoverable container of per-companion-spec ScenarioBindingGroup objects, "
            "enumerated by Browse. A server exposes one server-wide instance under the Server "
            "object, and/or a local instance on any object that implements "
            "IPubSubScenarioBoundType.", CAT)
BC = "PubSubScenarioBindingsType"
placeholder_obj(60010, BC, "<ScenarioBindingGroup>", T(60018),
                "A per-companion-specification group of scenario bindings.")
# No query Method: clients enumerate the <ScenarioBindingGroup> components (per companion
# spec) and their <ScenarioBinding> children by Browse, reading each ScenarioUri. Browse +
# Read is sufficient and OPC UA-native, and keeps the type usable on a classic server.

# ScenarioProfileType (registry entry)
object_type(60015, "ScenarioProfileType", BaseObjectType,
            "A registered integration scenario: its URI plus human-readable metadata. "
            "The registry is extensible; vendors and other specifications add profiles "
            "with their own URIs.", CAT)
SP = "ScenarioProfileType"
prop_var(60015, SP, "ScenarioUri", String, "The scenario URI.", rule=MR_Mandatory)
prop_var(60015, SP, "Title", LocalizedText, "Short human-readable title.")
prop_var(60015, SP, "Summary", LocalizedText, "Human-readable description of the scenario and its intended consumers.")
prop_var(60015, SP, "Keywords", String, "Keywords describing the scenario.", valuerank="1")

# IPubSubScenarioBoundType (interface)
interface_type(60016, "IPubSubScenarioBoundType", BaseInterfaceType,
               "Interface implemented by a companion-specification ObjectType (or "
               "instance) to advertise that it participates in scenario bindings, by "
               "exposing a local ScenarioBindings container.", CAT)
obj_member(60016, "IPubSubScenarioBoundType", "ScenarioBindings", T(60010),
           "The scenario bindings defined on this object.", rule=MR_Mandatory)

# --- Well-known instances --------------------------------------------------
CAT_INST = "PubSub Scenario Binding Instances"
# Server-wide registry hooked onto the well-known Server object (i=2253) - always present,
# so discovery never assumes a PubSub configuration surface.
well_known(60100, "ScenarioBindings", T(60010), int(Server.split("=")[1]),
           "Server-wide registry of scenario bindings, discoverable by browsing the "
           "Server object. Its presence does not require any PubSub configuration.")
NODES[60100].category = CAT_INST
# Scenarios registry folder under the server-wide container.
add(60101, "UAObject", "Scenarios", "Scenarios",
    desc="Registry of known integration scenarios (extensible).",
    parent=T(60100))
NODES[60101].category = CAT_INST
ref(60101, HasTypeDefinition, FolderType)
ref(60101, Organizes, T(60100), forward=False)
ref(60100, Organizes, T(60101))

SCENARIOS = [
    (60110, "Observability",
     "Real-time operational monitoring: SCADA/HMI, dashboards and observability "
     "platforms (e.g. OpenTelemetry). Low latency, cyclic telemetry and status."),
    (60111, "PredictiveMaintenance",
     "Condition- and usage-based trending fed to maintenance analytics to forecast "
     "wear and schedule service."),
    (60112, "AnomalyDetection",
     "High-resolution, correlated signals for baseline modelling and deviation/"
     "outlier detection."),
    (60113, "EnergyAndLoadManagement",
     "Power, load, demand and energy signals for load management, peak shaving and "
     "grid-services coordination."),
    (60114, "AlarmAndEventDistribution",
     "Condition and event streams for operators, CMMS/EAM and safety functions."),
    (60115, "FleetAndCompliance",
     "Multi-site supervision, contractual reporting and regulatory compliance."),
]
SCENARIO_ROOT = "http://opcfoundation.org/UA/PubSub/Scenarios/"
for (snid, sname, sdesc) in SCENARIOS:
    add(snid, "UAObject", sname, f"Scenario_{sname}", desc=sdesc, parent=T(60101))
    NODES[snid].category = CAT_INST
    ref(snid, HasTypeDefinition, T(60015))
    ref(snid, Organizes, T(60101), forward=False)
    ref(60101, Organizes, T(snid))
    set_string(snid, f"Scenario_{sname}", "ScenarioUri", SCENARIO_ROOT + sname)

# ===========================================================================
# ==============================  EMISSION  =================================
# ===========================================================================
NAMESPACE = "http://opcfoundation.org/UA/"
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


def _emit_node(n):
    tag = n.cls
    a = [f'{tag} NodeId="{T(n.nid)}"', f'BrowseName="{sx.escape(n.bname)}"']
    if n.parent is not None:
        a.append(f'ParentNodeId="{n.parent}"')
    for k in ("DataType", "ValueRank", "ArrayDimensions"):
        if k in n.attrs:
            v = n.attrs[k]
            if k == "DataType":
                v = DATATYPE_ALIAS.get(v, v)
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
        lines.append(f'      <Reference ReferenceType="{_fmt_reftype(rt)}"{fwd_s}>{tgt}</Reference>')
    lines.append("    </References>")
    if n.cls == "UAReferenceType" and n.inverse and not n.symmetric:
        lines.append(f"    <InverseName>{sx.escape(n.inverse)}</InverseName>")
    if n.definition:
        lines.append("    " + n.definition)
    if n.value:
        lines.append("    " + n.value)
    lines.append(f"  </{tag}>")
    return "\n".join(lines)


def emit():
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<!-- OPC UA PubSub Scenario Binding - proposed addition to the base UA '
           'namespace. PROVISIONAL NodeIds (final IDs assigned by the OPC Foundation). -->',
           '<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
           'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" '
           'xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
           '  <Models>',
           f'    <Model ModelUri="{NAMESPACE}" Version="{VERSION}" PublicationDate="{PUBDATE}" />',
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
    "ActionTargetDataType": "https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.10.3",
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
          "`tools/build_model.py` and always matches `Opc.Ua.PubSubBinding.NodeSet2.xml`. "
          "All nodes are proposed additions to the base OPC UA namespace "
          "`http://opcfoundation.org/UA/`; the NodeIds shown are **provisional** (final "
          "IDs are assigned by the OPC Foundation). The **Declared in** column marks "
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
        if n.category != "PubSub Scenario Binding Instances" or n.cls != "UAObject":
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
    outdir = os.path.dirname(here)
    with open(os.path.join(outdir, "Opc.Ua.PubSubBinding.NodeSet2.xml"), "w",
              encoding="utf-8") as f:
        f.write(emit())
    with open(os.path.join(outdir, "Opc.Ua.PubSubBinding.NodeIds.csv"), "w",
              encoding="utf-8") as f:
        f.write(emit_csv())
    with open(os.path.join(here, "model-reference.md"), "w", encoding="utf-8") as f:
        f.write(emit_md())
    nt = sum(1 for k in NODES if NODES[k].cls in ("UAObjectType", "UADataType", "UAReferenceType"))
    print(f"Nodes: {len(NODES)}  (types: {nt})")
    print(f"Member id range: 60500..{_next_member[0] - 1}")
