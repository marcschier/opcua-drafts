#!/usr/bin/env python3
"""
Generator for the OPC UA WoT Connectivity 1.1 companion NodeSet (WG draft).

Emits, from a single deterministic source of truth (in-code registry model plus
the pinned legacy sources under legacy/):
  * Opc.Ua.WoTCon.NodeSet2.xml   - the combined machine-readable information model
  * Opc.Ua.WoTCon.NodeIds.csv    - the numeric NodeId assignments
  * tools/model-reference.md     - the generated Annex A node reference

WoT Connectivity 1.1 is an *additive* revision of OPC 10100-1 (WoT Connectivity,
namespace http://opcfoundation.org/UA/WoT-Con/, published baseline v1.02.0). It
keeps the same NamespaceUri and incorporates the full published 1.02 model into
one combined NodeSet, then adds a registry-first document-registry layer over
the abstract OPC UA xRegistry base model: a WoTRegistryType RegistryType holds
ThingDescriptionGroupType / ThingModelGroupType groups whose files are
ThingDescriptionFileType / ThingModelFileType resources (concrete subtypes of
the abstract WoTDocumentType xRegistry ResourceType). The registry files and
versions are canonical; the projected AddressSpace (types from Thing Models,
instances from Thing Descriptions) is derived and refreshed.

Namespace layout inside this combined NodeSet:
    index 0 (implicit) : http://opcfoundation.org/UA/            (Core)
    index 1            : http://opcfoundation.org/UA/xRegistry/  (xRegistry base, RequiredModel)
    index 2            : http://opcfoundation.org/UA/WoT-Con/     (this spec, own - legacy + registry)

The published 1.02 model is emitted in the SAME own namespace (index 2). Because
xRegistry occupies index 1 in this combined document, the 1.02 nodes are the
own-namespace nodes at index 2; every published numeric NodeId (1..172) and
NodeClass is preserved exactly from the pinned legacy/WotConnection.csv table,
and the legacy management/upload surface is marked ReleaseStatus="Deprecated"
(machine-readable, per OPC 11030) without being removed. The additive registry
types/members use a non-conflicting 64000+ block. The legacy sources are a
source INPUT (parsed at generation time), not hand-copied output.

The revised WoT Binding JSON-LD vocabulary (http://opcfoundation.org/UA/WoT-Binding/)
is a normative dependency but NOT a NodeSet RequiredModel - it is a JSON-LD
vocabulary, not an OPC UA information model.

Additive registry numeric identifiers are PROVISIONAL and drawn from a dedicated
64000+ block (types) with members allocated append-only from 64500; final NodeIds
are assigned by the OPC Foundation. The 64000 block was chosen to avoid the ranges
already used by sibling drafts in this repository (Generators 1001-6xxx,
Schema Registry 62000, xRegistry 63000) and does not overlap any published
OPC Foundation range or the preserved 1.02 range (1..172).
"""
from __future__ import annotations
import os
import re
import xml.sax.saxutils as sx
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Well-known base NodeIds (Core, ns=0)
# ---------------------------------------------------------------------------
HasComponent = "i=47"
HasProperty = "i=46"
HasSubtype = "i=45"
Organizes = "i=35"
HasTypeDefinition = "i=40"
HasModellingRule = "i=37"
HasEncoding = "i=38"
GeneratesEvent = "i=41"
HasNotifier = "i=48"

MR_Mandatory = "i=78"
MR_Optional = "i=80"
MR_OptionalPlaceholder = "i=11508"

BaseObjectType = "i=58"
FolderType = "i=61"
BaseDataVariableType = "i=63"
PropertyType = "i=68"
DataTypeEncodingType = "i=76"
BaseEventType = "i=2041"
NonHierarchicalReferences = "i=32"

Boolean = "i=1"
UInt32 = "i=7"
UInt64 = "i=9"
Double = "i=11"
String = "i=12"
DateTime = "i=13"
ByteString = "i=15"
NodeId = "i=17"
ExpandedNodeId = "i=18"
LocalizedText = "i=21"
Structure = "i=22"
Enumeration = "i=29"
Duration = "i=290"
Argument = "i=296"

Server = "i=2253"

# --- additional Core (ns=0) NodeIds used by the incorporated 1.02 legacy model ---
Byte = "i=3"
UInt16 = "i=5"
Int32 = "i=6"
BaseDataType = "i=24"
UtcTime = "i=294"
IdType = "i=256"
NumericRange = "i=291"
RolePermissionType = "i=96"
AccessRestrictionType = "i=95"
SemanticVersionString = "i=24263"
VersionTime = "i=20998"
UriString = "i=23751"
BaseInterfaceType = "i=17602"
HasInterface = "i=17603"
FileType = "i=11575"
NamespaceMetadataType = "i=11616"
ObjectsFolder = "i=85"
Server_Namespaces = "i=11715"
MR_Mandatory_ = MR_Mandatory
MR_MandatoryPlaceholder = "i=11510"

# ---------------------------------------------------------------------------
# Namespace indices
# ---------------------------------------------------------------------------
XR_NS = 1          # required model: abstract xRegistry base
OWN_NS = 2         # this specification's own namespace (WoT-Con, index 2)
OWN_MIN = 64000
_next_member = [64500]


def T(nid):
    return f"ns={OWN_NS};i={nid}"


def X(nid):
    """Reference to an abstract xRegistry base type (required model, ns=1)."""
    return f"ns={XR_NS};i={nid}"


# abstract xRegistry base types this spec extends
XRegistry_RegistryType = X(63000)
XRegistry_GroupType = X(63001)
XRegistry_ResourceType = X(63002)


class Node:
    __slots__ = ("nid", "cls", "bname", "symbolic", "display", "desc", "parent",
                 "attrs", "refs", "category", "definition", "value", "abstract",
                 "inverse")

    def __init__(self, nid, cls, bname, symbolic, display=None, desc=None,
                 parent=None, attrs=None, category=None, abstract=False, inverse=None):
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
        self.inverse = inverse


NODES = {}
ORDER = []
ENUM_FIELDS = {}
STRUCT_FIELDS = {}


def _mid():
    v = _next_member[0]
    _next_member[0] += 1
    return v


def add(nid, cls, bname, symbolic, display=None, desc=None, parent=None,
        attrs=None, category=None, abstract=False, inverse=None):
    n = Node(nid, cls, bname, symbolic, display, desc, parent, attrs, category,
             abstract, inverse)
    NODES[nid] = n
    ORDER.append(nid)
    return n


def ref(nid, reftype, target, forward=True):
    NODES[nid].refs.append((reftype, target, forward))


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def object_type(nid, name, base, desc, category, abstract=False):
    add(nid, "UAObjectType", name, name, desc=desc, category=category, abstract=abstract)
    ref(nid, HasSubtype, base, forward=False)
    return nid


def event_type(nid, name, base, desc, category, abstract=False):
    add(nid, "UAObjectType", name, name, desc=desc, category=category, abstract=abstract)
    ref(nid, HasSubtype, base, forward=False)
    return nid


def reference_type(nid, name, base, inverse, desc, category, abstract=False):
    add(nid, "UAReferenceType", name, name, desc=desc, category=category,
        abstract=abstract, inverse=inverse)
    ref(nid, HasSubtype, base, forward=False)
    return nid


def _member_var(owner, owner_sym, name, datatype, typedef, rule, reftype, desc,
                valuerank="-1"):
    nid = _mid()
    attrs = {"DataType": datatype, "ValueRank": valuerank}
    if valuerank == "1":
        attrs["ArrayDimensions"] = "0"
    add(nid, "UAVariable", name, f"{owner_sym}_{name.strip('<>')}", desc=desc,
        parent=T(owner), attrs=attrs)
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid


def prop_var(owner, owner_sym, name, datatype, desc, rule=MR_Optional, valuerank="-1"):
    return _member_var(owner, owner_sym, name, datatype, PropertyType, rule,
                        HasProperty, desc, valuerank)


def obj_member(owner, owner_sym, name, typedef, desc, rule=MR_Optional,
               reftype=HasComponent):
    nid = _mid()
    add(nid, "UAObject", name, f"{owner_sym}_{name.strip('<>')}", desc=desc,
        parent=T(owner))
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid


def placeholder_obj(owner, owner_sym, name, typedef, desc,
                    rule=MR_OptionalPlaceholder, reftype=Organizes):
    return obj_member(owner, owner_sym, name, typedef, desc, rule, reftype)


def event_field(owner, owner_sym, name, datatype, desc, rule=MR_Mandatory, valuerank="-1"):
    """An event type field: a HasProperty PropertyType Variable of the event type."""
    return _member_var(owner, owner_sym, name, datatype, PropertyType, rule,
                        HasProperty, desc, valuerank)


def generates_event(owner, event_nid):
    ref(owner, GeneratesEvent, T(event_nid))


def method(owner, owner_sym, name, desc, rule=MR_Optional, inargs=None, outargs=None):
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


def instance_method(owner, owner_sym, name, decl_nid, desc, inargs=None, outargs=None):
    """Materialize a concrete (instance) method under a well-known instance object."""
    nid = _mid()
    add(nid, "UAMethod", name, f"{owner_sym}_{name}", desc=desc, parent=T(owner),
        category=CAT_INST, attrs={"MethodDeclarationId": T(decl_nid)})
    ref(nid, HasComponent, T(owner), forward=False)
    ref(owner, HasComponent, T(nid))
    if inargs:
        _args(nid, f"{owner_sym}_{name}", "InputArguments", inargs, instance=True)
    if outargs:
        _args(nid, f"{owner_sym}_{name}", "OutputArguments", outargs, instance=True)
    return nid


def _scalar_value(uax_type, value):
    """A <Value> fragment for a scalar built-in-typed Property, e.g. String or UInt32."""
    return (f'<Value><uax:{uax_type} xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd">'
            f'{sx.escape(str(value))}</uax:{uax_type}></Value>')


def instance_var(owner, owner_sym, name, datatype, desc, value_xml):
    """Materialize a concrete (instance) Property Variable with a Value under a well-known
    instance object. Used to make every Mandatory member (own or inherited) of a well-known
    instance's type present at load time, since a well-known instance carries values rather
    than a HasModellingRule declaration."""
    nid = _mid()
    add(nid, "UAVariable", name, f"{owner_sym}_{name}", desc=desc, parent=T(owner),
        category=CAT_INST, attrs={"DataType": datatype, "ValueRank": "-1"})
    ref(nid, HasTypeDefinition, PropertyType)
    ref(nid, HasProperty, T(owner), forward=False)
    ref(owner, HasProperty, T(nid))
    NODES[nid].value = value_xml
    return nid


def _args(method_nid, method_sym, bname, args, instance=False):
    nid = _mid()
    add(nid, "UAVariable", bname, f"{method_sym}_{bname}", parent=T(method_nid),
        attrs={"DataType": Argument, "ValueRank": "1", "ArrayDimensions": str(len(args)),
               "_ns0bn": True},
        category=(CAT_INST if instance else None))
    if not instance:
        ref(nid, HasModellingRule, MR_Mandatory)
    ref(nid, HasTypeDefinition, PropertyType)
    ref(nid, HasProperty, T(method_nid), forward=False)
    ref(method_nid, HasProperty, T(nid))
    parts = ['<Value>', '<ListOfExtensionObject xmlns="http://opcfoundation.org/UA/2008/02/Types.xsd">']
    for arg in args:
        aname, adtype, adesc = arg[0], arg[1], arg[2]
        arank = arg[3] if len(arg) > 3 else -1
        parts.append("<ExtensionObject><TypeId><Identifier>i=297</Identifier></TypeId><Body><Argument>")
        parts.append(f"<Name>{sx.escape(aname)}</Name><DataType><Identifier>{adtype}</Identifier></DataType>")
        if arank is not None and arank >= 0:
            parts.append(f"<ValueRank>{arank}</ValueRank><ArrayDimensions><UInt32>0</UInt32></ArrayDimensions>")
        else:
            parts.append("<ValueRank>-1</ValueRank><ArrayDimensions/>")
        if adesc:
            parts.append(f"<Description><Text>{sx.escape(adesc)}</Text></Description>")
        parts.append("</Argument></Body></ExtensionObject>")
    parts.append("</ListOfExtensionObject></Value>")
    NODES[nid].value = "".join(parts)


def enum_type(nid, name, desc, category, fields):
    """fields: list of (fieldname, value_int, description)."""
    add(nid, "UADataType", name, name, desc=desc, category=category)
    ref(nid, HasSubtype, Enumeration, forward=False)
    ENUM_FIELDS[nid] = fields
    dparts = [f'<Definition Name="{OWN_NS}:{sx.escape(name)}">']
    for (fname, val, fdesc) in fields:
        if fdesc:
            dparts.append(f'<Field Name="{sx.escape(fname)}" Value="{val}">')
            dparts.append(f'<Description>{sx.escape(fdesc)}</Description></Field>')
        else:
            dparts.append(f'<Field Name="{sx.escape(fname)}" Value="{val}"/>')
    dparts.append("</Definition>")
    NODES[nid].definition = "".join(dparts)
    es = _mid()
    ref(nid, HasProperty, T(es))
    add(es, "UAVariable", "EnumStrings", f"{name}_EnumStrings", parent=T(nid),
        attrs={"DataType": LocalizedText, "ValueRank": "1", "ArrayDimensions": str(len(fields)),
               "_ns0bn": True})
    ref(es, HasModellingRule, MR_Mandatory)
    ref(es, HasTypeDefinition, PropertyType)
    ref(es, HasProperty, T(nid), forward=False)
    vp = ['<Value>', '<ListOfLocalizedText xmlns="http://opcfoundation.org/UA/2008/02/Types.xsd">']
    for (fname, val, fdesc) in fields:
        vp.append(f"<LocalizedText><Text>{sx.escape(fname)}</Text></LocalizedText>")
    vp.append("</ListOfLocalizedText></Value>")
    NODES[es].value = "".join(vp)
    return nid


def struct_type(nid, name, fields, desc, category, base=Structure):
    """fields: list of (fieldname, datatype, description, valuerank) - valuerank optional (default -1)."""
    add(nid, "UADataType", name, name, desc=desc, category=category)
    ref(nid, HasSubtype, base, forward=False)
    STRUCT_FIELDS[nid] = fields
    parts = [f'<Definition Name="{OWN_NS}:{sx.escape(name)}">']
    for f in fields:
        fname, fdt, fdesc = f[0], f[1], f[2]
        frank = f[3] if len(f) > 3 else -1
        attrs = f'Name="{sx.escape(fname)}" DataType="{fdt}"'
        if frank is not None and frank >= 0:
            attrs += f' ValueRank="{frank}"'
        parts.append(f"<Field {attrs}>")
        if fdesc:
            parts.append(f"<Description>{sx.escape(fdesc)}</Description>")
        parts.append("</Field>")
    parts.append("</Definition>")
    NODES[nid].definition = "".join(parts)
    for enc in ("Binary", "JSON"):
        enc_nid = _mid()
        add(enc_nid, "UAObject", f"Default {enc}", f"{name}_Default{enc}", parent=T(nid),
            attrs={"_ns0bn": True})
        ref(enc_nid, HasTypeDefinition, DataTypeEncodingType)
        ref(enc_nid, HasEncoding, T(nid), forward=False)
        ref(nid, HasEncoding, T(enc_nid))
    return nid


# ---------------------------------------------------------------------------
# xRegistry attributes common to a registry/group/resource entity (ns=1 base
# types already declare them; concrete WoT subtypes inherit them and add their
# own members below, so we do NOT re-declare the inherited attributes here).
# ---------------------------------------------------------------------------

# ===========================================================================
# ==============================  MODEL DEFINITION  =========================
# ===========================================================================
CAT = "WoT Connectivity 1.1"
CAT_DT = "WoT Connectivity 1.1 DataTypes"
CAT_EV = "WoT Connectivity 1.1 Events"
CAT_REF = "WoT Connectivity 1.1 References"
CAT_INST = "WoT Connectivity 1.1 Instances"

# --- DataTypes: enumerations ----------------------------------------------
enum_type(64020, "WoTDocumentKindEnum",
          "The kind of WoT document a resource carries: a Thing Description (a concrete instance) "
          "or a Thing Model (a reusable type template).", CAT_DT,
          [("ThingDescription", 0, "A W3C WoT Thing Description (WoT-TD/1.1); projects to OPC UA instances."),
           ("ThingModel", 1, "A W3C WoT Thing Model (WoT-TM/1.1); projects to OPC UA types.")])

enum_type(64021, "WoTLoadStateEnum",
          "The lifecycle state of a WoT document's derived projection in the AddressSpace. The registry "
          "file always remains stored; this enum reflects only the state of the code-behind projection.", CAT_DT,
          [("Unloaded", 0, "Stored but not projected into the AddressSpace."),
           ("Validating", 1, "Format and compatibility validation is in progress."),
           ("Loading", 2, "The projection is being materialized under a shadow generation."),
           ("Active", 3, "The projection is committed and serving as the active generation."),
           ("Failed", 4, "Validation or projection failed; the last valid projection (if any) stays active."),
           ("Superseded", 5, "A newer generation has replaced this one; retained until monitored items drain."),
           ("Retiring", 6, "Being retired; awaiting monitored-item drain before node removal."),
           ("Retired", 7, "The projection has been removed from the AddressSpace.")])

enum_type(64022, "WoTRefreshModeEnum",
          "How a registry or document triggers refresh of its derived projection.", CAT_DT,
          [("Manual", 0, "Only an explicit Refresh Method call re-projects."),
           ("Periodic", 1, "The registry re-projects on a fixed interval (RefreshInterval)."),
           ("EventDriven", 2, "The registry re-projects when a stored document changes (write/CloseAndUpdate)."),
           ("Scheduled", 3, "The registry re-projects on an implementation-defined schedule.")])

enum_type(64023, "WoTAtomicityEnum",
          "The commit granularity applied when a refresh projects one or more documents.", CAT_DT,
          [("PerResource", 0, "Each resource commits independently; a failure isolates to that resource."),
           ("PerGroup", 1, "All resources of a group commit together or not at all."),
           ("PerClosure", 2, "A document and its full dependency closure (DAG) commit atomically."),
           ("PerRegistry", 3, "All selected documents commit as a single all-or-nothing transaction.")])

enum_type(64024, "WoTDeletePolicyEnum",
          "How the registry treats dependents when a document version is unloaded or deleted.", CAT_DT,
          [("Reject", 0, "Reject the operation while any other loaded document still depends on it."),
           ("Retire", 1, "Retire the projection but keep the stored document for dependents to resolve."),
           ("Cascade", 2, "Unload dependents that resolve only through this document."),
           ("Force", 3, "Force-unload the projection even while dependents remain, marking them Failed.")])

enum_type(64025, "WoTOutcomeEnum",
          "The outcome of a validation, projection or refresh operation on a document or the registry.", CAT_DT,
          [("Success", 0, "The operation completed and changed the projection."),
           ("Unchanged", 1, "The operation was idempotent; the content digest matched and nothing changed."),
           ("Warning", 2, "The operation completed with non-fatal warnings."),
           ("Skipped", 3, "The operation was not applicable and was skipped."),
           ("Rejected", 4, "The operation was rejected by policy (for example concurrency or delete policy)."),
           ("Failed", 5, "The operation failed; the previous valid projection (if any) remains active.")])

enum_type(64026, "WoTPhaseEnum",
          "The processing phase a document reached, used to locate where an outcome was produced.", CAT_DT,
          [("Fetch", 0, "Fetching the document bytes and its @context/schema references."),
           ("Parse", 1, "Parsing the JSON-LD document."),
           ("FormatValidation", 2, "Validating the document against its WoT-TD/WoT-TM format."),
           ("CompatibilityValidation", 3, "Validating the version against the resource compatibility policy."),
           ("DependencyResolution", 4, "Resolving the dependency closure (tm:extends, tm:ref, links rel=type)."),
           ("Projection", 5, "Materializing types/instances into a shadow generation."),
           ("Activation", 6, "Committing the shadow generation as active."),
           ("Retirement", 7, "Retiring a superseded generation after monitored items drain.")])

enum_type(64027, "WoTBindingCapabilityEnum",
          "A single interaction operation a protocol binding supports, aligned with the WoT form op vocabulary.", CAT_DT,
          [("ReadProperty", 0, "Read a property affordance."),
           ("WriteProperty", 1, "Write a property affordance."),
           ("ObserveProperty", 2, "Observe (subscribe to) a property affordance."),
           ("InvokeAction", 3, "Invoke an action affordance."),
           ("SubscribeEvent", 4, "Subscribe to an event affordance."),
           ("UnsubscribeEvent", 5, "Unsubscribe from an event affordance.")])

# --- DataTypes: structures -------------------------------------------------
struct_type(64040, "WoTValidationOutcomeDataType",
            [("FormatValidated", Boolean, "True if format validation was performed."),
             ("FormatOutcome", T(64025), "Outcome of format validation (WoT-TD/WoT-TM conformance)."),
             ("FormatReason", String, "Human-readable reason for the format outcome (empty on success)."),
             ("CompatibilityValidated", Boolean, "True if compatibility validation was performed."),
             ("CompatibilityOutcome", T(64025), "Outcome of compatibility validation against the resource policy."),
             ("CompatibilityReason", String, "Human-readable reason for the compatibility outcome (empty on success)."),
             ("CompatibilityPolicy", String, "The compatibility policy in force (for example NONE, BACKWARD, FULL)."),
             ("ValidatedAt", DateTime, "UTC time the validation completed."),
             ("VocabularyVersion", String, "The pinned WoT Binding JSON-LD vocabulary version used for validation.")],
            "An immutable snapshot of a document's format and compatibility validation result. Read as a single "
            "Variant value; a new snapshot is produced on each validation and never mutated in place.", CAT_DT)

struct_type(64041, "WoTBindingCapabilityDataType",
            [("BindingUri", String, "The WoT protocol-binding vocabulary URI (for example the OPC UA, HTTP or Modbus binding)."),
             ("Title", String, "Human-readable binding title."),
             ("ProfileVersion", String, "The version-pinned W3C binding document version this capability snapshot was built against."),
             ("DraftMaturity", String, "The W3C maturity of the pinned binding document (for example WD, CR, PR, REC)."),
             ("Capabilities", T(64027), "The interaction operations this binding supports.", 1),
             ("ContentTypes", String, "The content types this binding produces/consumes.", 1)],
            "An immutable snapshot of a protocol binding's identity, version-pinned W3C document, maturity and "
            "supported operations. Held as an array element only for immutable snapshots; browseable binding "
            "objects (WoTBindingType) carry the live, per-field form.", CAT_DT)

struct_type(64042, "WoTRefreshOptionsDataType",
            [("Atomicity", T(64023), "Commit granularity for this refresh."),
             ("Force", Boolean, "Re-project even when the content digest is unchanged."),
             ("DryRun", Boolean, "Validate and compute results without committing any projection change."),
             ("IncludeDependents", Boolean, "Also refresh documents that depend on the selected documents."),
             ("DeletePolicy", T(64024), "How to treat dependents when a selected document is unloaded/retired."),
             ("MaxParallelism", UInt32, "Maximum number of documents projected concurrently; 0 lets the server decide."),
             ("Timeout", Duration, "Overall time budget for the refresh; 0 lets the server decide.")],
            "Immutable options controlling a single Refresh invocation.", CAT_DT)

struct_type(64043, "WoTResourceSelectorDataType",
            [("Kind", T(64020), "Restrict to Thing Descriptions or Thing Models; omit to select both."),
             ("GroupId", String, "Restrict to a group by groupid; empty selects all groups."),
             ("ResourceId", String, "Restrict to a resource by resourceid; empty selects all resources."),
             ("VersionId", String, "Restrict to a version by versionid; empty selects the resource's default version."),
             ("Xid", String, "Select a single entity by its xRegistry xid; overrides the other fields when set.")],
            "An immutable selector identifying which stored documents a Refresh applies to. An empty selector "
            "array selects the whole registry.", CAT_DT)

struct_type(64044, "WoTResourceLoadResultDataType",
            [("Xid", String, "The xRegistry xid of the affected resource/version."),
             ("GroupId", String, "The groupid of the resource's group."),
             ("ResourceId", String, "The resourceid of the affected resource."),
             ("VersionId", String, "The versionid that was projected."),
             ("Kind", T(64020), "Whether the document is a Thing Description or a Thing Model."),
             ("Outcome", T(64025), "The per-resource outcome."),
             ("Phase", T(64026), "The phase the resource reached (the failing phase on failure)."),
             ("LoadState", T(64021), "The resulting load state of the projection."),
             ("Generation", UInt32, "The refresh generation this result belongs to."),
             ("MaterializedNodeCount", UInt32, "Number of AddressSpace nodes materialized for this resource."),
             ("RootNodeId", NodeId, "The root node of the materialized projection, if any."),
             ("ContentDigest", ByteString, "The content digest (hash) of the projected document bytes."),
             ("Message", String, "Human-readable detail for the outcome.")],
            "An immutable per-resource result row of a Refresh. Never mutated; the array is a point-in-time "
            "snapshot for one generation.", CAT_DT)

struct_type(64045, "WoTRefreshSummaryDataType",
            [("RequestId", String, "The caller-supplied request identifier echoed back for correlation."),
             ("Generation", UInt32, "The committed refresh generation (0 on a dry run or full failure)."),
             ("Outcome", T(64025), "The overall outcome of the refresh."),
             ("Atomicity", T(64023), "The commit granularity that was applied."),
             ("StartTime", DateTime, "UTC start time of the refresh."),
             ("EndTime", DateTime, "UTC end time of the refresh."),
             ("Total", UInt32, "Total number of resources considered."),
             ("Succeeded", UInt32, "Number of resources that changed successfully."),
             ("Unchanged", UInt32, "Number of resources that were idempotently unchanged."),
             ("Failed", UInt32, "Number of resources that failed."),
             ("Skipped", UInt32, "Number of resources skipped by selection or policy."),
             ("Retired", UInt32, "Number of superseded generations retired.")],
            "An immutable summary of one Refresh invocation, also carried by the WoTRefreshCompletedEventType and "
            "cached on the registry as LastRefreshSummary.", CAT_DT)

struct_type(64046, "WoTDependencyDataType",
            [("SourceXid", String, "The xid of the dependent document."),
             ("TargetXid", String, "The xid of the document depended upon (empty if unresolved)."),
             ("TargetUri", String, "The raw href/URI of the dependency as authored in the document."),
             ("RefType", String, "The dependency kind (for example tm:extends, tm:ref, links.rel=type)."),
             ("Resolved", Boolean, "True if the dependency resolved to a stored document.")],
            "An immutable edge of the document dependency DAG, used to describe closures in results and diagnostics.",
            CAT_DT)

# --- ObjectTypes: registry, groups, documents, bindings --------------------
object_type(64000, "WoTRegistryType", XRegistry_RegistryType,
            "The WoT Connectivity 1.1 registry root - an xRegistry RegistryType (a FolderType) that holds "
            "ThingDescriptionGroupType and ThingModelGroupType groups. The stored Thing Description / Thing Model "
            "files and their versions are canonical; the projected AddressSpace (types from Thing Models, instances "
            "from Thing Descriptions) is derived code-behind. Exposed as a well-known WoTRegistry object under the "
            "Server object (i=2253). Adds registry-wide refresh, generation and validation-policy state and the "
            "Refresh Method.", CAT)

object_type(64001, "ThingDescriptionGroupType", XRegistry_GroupType,
            "An xRegistry GroupType that collects related ThingDescriptionFileType resources (a Thing Description "
            "Group per the WoT xRegistry model). Adds the group-level format/compatibility validation policy. Its "
            "<ThingDescription> placeholder constrains members to the Thing Description subtype.", CAT)

object_type(64002, "ThingModelGroupType", XRegistry_GroupType,
            "An xRegistry GroupType that collects related ThingModelFileType resources (a Thing Model Group per the "
            "WoT xRegistry model). Adds the group-level format/compatibility validation policy. Its <ThingModel> "
            "placeholder constrains members to the Thing Model subtype.", CAT)

object_type(64003, "WoTDocumentType", XRegistry_ResourceType,
            "The abstract base of a stored WoT document resource - an xRegistry ResourceType (a FileType) whose "
            "content bytes are the JSON-LD document, read/written with the inherited Open/Read/Write/Close Methods. "
            "Adds the derived-projection metadata (load state, desired/active version, validation and compatibility "
            "outcomes, content digest, materialized-node count and root, selected bindings) and the Validate, "
            "SetEnabled and SetDefaultVersion Methods. Concrete subtypes fix the document kind.", CAT, abstract=True)

object_type(64004, "ThingDescriptionFileType", T(64003),
            "A concrete WoTDocumentType whose content is a W3C WoT Thing Description (WoT-TD/1.1, "
            "application/td+json). Projects to OPC UA instances: affordances become Variables, Methods and event "
            "sources; forms become binder plans. Adds the Thing instance identity (ThingId, base URI) and the link "
            "to the Thing Model it derives from.", CAT)

object_type(64005, "ThingModelFileType", T(64003),
            "A concrete WoTDocumentType whose content is a W3C WoT Thing Model (WoT-TM/1.1, application/tm+json). "
            "Projects to OPC UA types: it materializes an ObjectType or VariableType and the affordance member "
            "declarations and modelling rules. Adds the derived type NodeId and model version.", CAT)

object_type(64006, "WoTBindingType", BaseObjectType,
            "A browseable protocol-binding descriptor: the live, per-field representation of one W3C WoT protocol "
            "binding the server can realize (its URI, title, version-pinned W3C document, draft maturity, enabled "
            "state, content types and a capability snapshot). Selected/active binding sets are additionally exposed "
            "as immutable WoTBindingCapabilityDataType array snapshots. Policy and identity are browseable; no "
            "credentials or secrets are ever exposed here.", CAT)

# --- Event types -----------------------------------------------------------
event_type(64010, "WoTResourceEventType", BaseEventType,
           "The common base event for a WoT resource lifecycle notification. Carries the identity of the affected "
           "resource/version, the document kind, the refresh generation, the phase reached and the outcome. Abstract; "
           "servers emit one of its concrete subtypes.", CAT_EV, abstract=True)

event_type(64011, "WoTValidationFailureEventType", T(64010),
           "Raised when a document fails format or compatibility validation. The failing resource is the event "
           "source; the stored document is retained and any previous valid projection stays active.", CAT_EV)

event_type(64012, "WoTLoadFailureEventType", T(64010),
           "Raised when a validated document fails to project (materialize) into the AddressSpace, or when its "
           "shadow generation cannot be activated. The failing resource is the event source.", CAT_EV)

event_type(64013, "WoTBindingFailureEventType", T(64010),
           "Raised when a form cannot be bound to its protocol binding (unknown binding, unsupported operation or a "
           "runtime binder error). The failing resource is the event source.", CAT_EV)

event_type(64014, "WoTRefreshCompletedEventType", BaseEventType,
           "Raised by the registry when a Refresh completes (including automatic refreshes). Carries the refresh "
           "summary and the committed generation. The registry object is the event source.", CAT_EV)

# --- Reference type --------------------------------------------------------
reference_type(64060, "HasWoTProjection", NonHierarchicalReferences, "WoTProjectionOf",
               "Links a stored WoT document resource (source) to the root node of its derived AddressSpace "
               "projection (target). Used to correlate materialized nodes and their NodeVersion with the canonical "
               "document, and to find the document behind a projected node.", CAT_REF)

# ===========================================================================
# Members
# ===========================================================================

# ---- WoTRegistryType members ---------------------------------------------
RG = "WoTRegistryType"
prop_var(64000, RG, "AutoRefresh", Boolean,
         "True if the registry automatically re-projects stored documents (per RefreshMode); false if only explicit "
         "Refresh calls re-project.", rule=MR_Optional)
prop_var(64000, RG, "RefreshMode", T(64022), "How automatic refresh is triggered when AutoRefresh is true.")
prop_var(64000, RG, "RefreshInterval", Duration, "The interval used when RefreshMode is Periodic.")
prop_var(64000, RG, "RefreshGeneration", UInt32,
         "The current committed projection generation; incremented on every committed refresh. Materialized nodes "
         "carry the generation in their NodeVersion for correlation.", rule=MR_Mandatory)
prop_var(64000, RG, "LastRefreshTime", DateTime, "UTC time of the last completed refresh.")
prop_var(64000, RG, "LastRefreshSummary", T(64045), "An immutable snapshot summarizing the last completed refresh.")
prop_var(64000, RG, "DefaultAtomicity", T(64023), "The commit granularity applied when a Refresh omits an explicit atomicity.")
prop_var(64000, RG, "DeletePolicy", T(64024), "The default policy for treating dependents on unload/delete.")
prop_var(64000, RG, "ValidateFormat", Boolean, "Registry-wide default: validate document format on ingest/refresh.")
prop_var(64000, RG, "ValidateCompatibility", Boolean, "Registry-wide default: validate version compatibility on ingest/refresh.")
prop_var(64000, RG, "StrictValidation", Boolean, "If true, a validation warning is treated as a failure.")
prop_var(64000, RG, "VocabularyVersion", String,
         "The version-pinned WoT Binding JSON-LD vocabulary this registry validates and projects against.")
prop_var(64000, RG, "SelectedBindings", T(64041),
         "An immutable snapshot array of the protocol bindings currently selected/active registry-wide.", valuerank="1")
obj_member(64000, RG, "SupportedBindings", FolderType,
           "A folder of browseable WoTBindingType binding descriptors the server can realize (the live, per-field "
           "form of the selected-bindings snapshot).")
placeholder_obj(64000, RG, "<ThingDescriptionGroup>", T(64001),
                "A Thing Description Group held by this registry (constrained to the ThingDescriptionGroupType subtype).")
placeholder_obj(64000, RG, "<ThingModelGroup>", T(64002),
                "A Thing Model Group held by this registry (constrained to the ThingModelGroupType subtype).")
refresh_decl = method(64000, RG, "Refresh",
       "Re-project selected stored documents into the AddressSpace. Idempotent: a document whose content digest is "
       "unchanged is reported Unchanged and not re-materialized unless Options.Force is set. Projects into a shadow "
       "generation and switches atomically per Options.Atomicity; superseded generations are retired after their "
       "monitored items drain. If ExpectedGeneration is non-zero and does not equal RefreshGeneration, the call "
       "fails with Bad_InvalidState and changes nothing (optimistic concurrency). An empty Selection selects the "
       "whole registry.",
       inargs=[("Selection", T(64043), "The documents to refresh; empty selects the whole registry.", 1),
               ("Options", T(64042), "Options controlling atomicity, force, dry-run and dependents."),
               ("ExpectedGeneration", UInt32, "Expected current RefreshGeneration for optimistic concurrency; 0 disables the check."),
               ("RequestId", String, "Caller-supplied identifier echoed into the summary and the completion event.")],
       outargs=[("Summary", T(64045), "The refresh summary."),
                ("Results", T(64044), "The per-resource results.", 1),
                ("NewGeneration", UInt32, "The committed generation (unchanged on dry run or full failure).")])
generates_event(64000, 64014)

# ---- ThingDescriptionGroupType members ------------------------------------
DG = "ThingDescriptionGroupType"
prop_var(64001, DG, "ValidateFormat", Boolean, "Group-level policy: validate Thing Description format (WoT-TD/1.1) on ingest.")
prop_var(64001, DG, "ValidateCompatibility", Boolean, "Group-level policy: validate version compatibility on ingest.")
prop_var(64001, DG, "ConsistentFormat", Boolean, "Group-level policy: require all versions of a resource to share one format.")
placeholder_obj(64001, DG, "<ThingDescription>", T(64004),
                "A Thing Description resource held by this group (constrained to the ThingDescriptionFileType subtype).")

# ---- ThingModelGroupType members ------------------------------------------
MG = "ThingModelGroupType"
prop_var(64002, MG, "ValidateFormat", Boolean, "Group-level policy: validate Thing Model format (WoT-TM/1.1) on ingest.")
prop_var(64002, MG, "ValidateCompatibility", Boolean, "Group-level policy: validate version compatibility on ingest.")
prop_var(64002, MG, "ConsistentFormat", Boolean, "Group-level policy: require all versions of a resource to share one format.")
placeholder_obj(64002, MG, "<ThingModel>", T(64005),
                "A Thing Model resource held by this group (constrained to the ThingModelFileType subtype).")

# ---- WoTDocumentType members (abstract) -----------------------------------
DOC = "WoTDocumentType"
prop_var(64003, DOC, "DocumentKind", T(64020),
         "Whether this document is a Thing Description or a Thing Model. Fixed by the concrete subtype.", rule=MR_Mandatory)
prop_var(64003, DOC, "Enabled", Boolean,
         "The desired enabled state: true requests that the document be validated and projected; false requests unload.",
         rule=MR_Mandatory)
prop_var(64003, DOC, "LoadState", T(64021), "The actual lifecycle state of this document's derived projection.", rule=MR_Mandatory)
prop_var(64003, DOC, "DesiredVersionId", String,
         "The versionid the operator wants active for this resource (the desired/pinned version).")
prop_var(64003, DOC, "ActiveVersionId", String, "The versionid whose projection is currently active.")
prop_var(64003, DOC, "IsDefault", Boolean, "xRegistry isdefault: true when this version is the resource's default (sticky) version.")
prop_var(64003, DOC, "Ancestor", String, "xRegistry ancestor: the versionid this version derives from (version lineage).")
prop_var(64003, DOC, "Compatibility", String, "The compatibility policy all versions of this resource adhere to (for example NONE, BACKWARD, FULL).")
prop_var(64003, DOC, "AutoRefresh", Boolean, "Per-document override of the registry AutoRefresh setting.")
prop_var(64003, DOC, "RefreshGeneration", UInt32, "The registry generation at which this document was last projected.")
prop_var(64003, DOC, "LastRefreshTime", DateTime, "UTC time this document was last projected.")
prop_var(64003, DOC, "ContentDigest", ByteString, "The content digest (hash) of the stored document bytes; used to make refresh idempotent.")
prop_var(64003, DOC, "ValidationOutcome", T(64040), "An immutable snapshot of this document's format and compatibility validation result.")
prop_var(64003, DOC, "MaterializedNodeCount", UInt32, "The number of AddressSpace nodes materialized from this document's active projection.")
prop_var(64003, DOC, "RootNodeId", NodeId, "The root node of this document's active projection (the type or instance root).")
prop_var(64003, DOC, "SelectedBindings", T(64041),
         "An immutable snapshot array of the protocol bindings selected for this document's forms.", valuerank="1")
method(64003, DOC, "Validate",
       "Validate the stored document (format and, when enabled, compatibility) without changing its projection. "
       "Returns the outcome snapshot; also refreshes the ValidationOutcome Property.",
       outargs=[("Outcome", T(64040), "The validation outcome snapshot.")])
method(64003, DOC, "SetEnabled",
       "Set the desired Enabled state of this document. Enabling requests validation and projection; disabling "
       "requests unload per the registry DeletePolicy. If ExpectedEpoch is non-zero and does not equal the "
       "resource's current Epoch the call fails with Bad_InvalidState and changes nothing.",
       inargs=[("Enabled", Boolean, "The desired enabled state."),
               ("ExpectedEpoch", UInt32, "Expected current Epoch for optimistic concurrency; 0 disables the check.")])
method(64003, DOC, "SetDefaultVersion",
       "Make a specific version of this resource its default (sticky) version, so that resolvers selecting the "
       "resource without a versionid resolve to it. If ExpectedEpoch is non-zero and does not equal the resource's "
       "current Epoch the call fails with Bad_InvalidState and changes nothing.",
       inargs=[("VersionId", String, "The versionid to make default."),
               ("ExpectedEpoch", UInt32, "Expected current Epoch for optimistic concurrency; 0 disables the check.")])
generates_event(64003, 64011)
generates_event(64003, 64012)
generates_event(64003, 64013)

# ---- ThingDescriptionFileType members -------------------------------------
TD = "ThingDescriptionFileType"
prop_var(64004, TD, "ThingId", String, "The Thing Description id (a URI/URN identifying the concrete Thing instance).")
prop_var(64004, TD, "ThingTitle", String, "The Thing Description human-readable title.")
prop_var(64004, TD, "BaseUri", String, "The Thing Description base URI used to resolve relative form hrefs.")
prop_var(64004, TD, "ModelReference", String,
         "The xid or href of the Thing Model this Thing Description derives from (links rel=type), when present.")

# ---- ThingModelFileType members -------------------------------------------
TM = "ThingModelFileType"
prop_var(64005, TM, "ModelTitle", String, "The Thing Model human-readable title.")
prop_var(64005, TM, "ModelVersion", String, "The Thing Model version (WoT version.model), when present.")
prop_var(64005, TM, "DerivedTypeNodeId", NodeId, "The ObjectType or VariableType materialized from this Thing Model.")

# ---- WoTBindingType members -----------------------------------------------
BD = "WoTBindingType"
prop_var(64006, BD, "BindingUri", String, "The WoT protocol-binding vocabulary URI this descriptor represents.", rule=MR_Mandatory)
prop_var(64006, BD, "Title", String, "Human-readable binding title.")
prop_var(64006, BD, "ProfileVersion", String, "The version-pinned W3C binding document version.")
prop_var(64006, BD, "DraftMaturity", String, "The W3C maturity of the pinned binding document (for example WD, CR, PR, REC).")
prop_var(64006, BD, "Enabled", Boolean, "True if the server currently realizes forms of this binding.")
prop_var(64006, BD, "ContentTypes", String, "The content types this binding produces/consumes.", valuerank="1")
prop_var(64006, BD, "Capabilities", T(64041), "An immutable capability snapshot for this binding.")

# ---- Event type fields ----------------------------------------------------
RE = "WoTResourceEventType"
event_field(64010, RE, "Xid", String, "The xRegistry xid of the affected resource/version.")
event_field(64010, RE, "ResourceId", String, "The resourceid of the affected resource.")
event_field(64010, RE, "VersionId", String, "The versionid of the affected version.")
event_field(64010, RE, "DocumentKind", T(64020), "Whether the document is a Thing Description or a Thing Model.")
event_field(64010, RE, "Generation", UInt32, "The refresh generation the notification relates to.")
event_field(64010, RE, "Phase", T(64026), "The phase reached (the failing phase on a failure event).")
event_field(64010, RE, "Outcome", T(64025), "The outcome the notification reports.")

VF = "WoTValidationFailureEventType"
event_field(64011, VF, "ValidationOutcome", T(64040), "The full validation outcome snapshot for the failure.")

LF = "WoTLoadFailureEventType"
event_field(64012, LF, "LoadState", T(64021), "The load state after the failed projection/activation.")
event_field(64012, LF, "FailedNodeId", NodeId, "The node whose materialization failed, if identifiable.")
event_field(64012, LF, "Reason", String, "Human-readable failure reason.")

BF = "WoTBindingFailureEventType"
event_field(64013, BF, "BindingUri", String, "The binding URI that could not be bound.")
event_field(64013, BF, "Reason", String, "Human-readable binding failure reason.")

RC = "WoTRefreshCompletedEventType"
event_field(64014, RC, "Summary", T(64045), "The refresh summary snapshot.")
event_field(64014, RC, "RequestId", String, "The caller-supplied request identifier echoed from the Refresh call.")
event_field(64014, RC, "Generation", UInt32, "The committed generation.")

# ---- Well-known WoTRegistry instance (component of the Server object) -----
add(64100, "UAObject", "WoTRegistry", "WoTRegistry",
    desc="The server-wide WoT Connectivity 1.1 registry, a well-known component of the Server object. Its stored "
         "Thing Description / Thing Model files are canonical; the projected AddressSpace is derived. It is the "
         "notifier for the WoT resource lifecycle events raised by its groups and resources.",
    parent=Server, category=CAT_INST, attrs={"EventNotifier": "1"})
ref(64100, HasTypeDefinition, T(64000))
ref(64100, HasComponent, Server, forward=False)
ref(64100, HasNotifier, Server, forward=False)
instance_method(64100, "WoTRegistry", "Refresh", refresh_decl,
    "Re-project selected stored documents into the AddressSpace. The functional Refresh Method on the well-known "
    "WoTRegistry object; a server binds the concrete handler.",
    inargs=[("Selection", T(64043), "The documents to refresh; empty selects the whole registry.", 1),
            ("Options", T(64042), "Options controlling atomicity, force, dry-run and dependents."),
            ("ExpectedGeneration", UInt32, "Expected current RefreshGeneration for optimistic concurrency; 0 disables the check."),
            ("RequestId", String, "Caller-supplied identifier echoed into the summary and the completion event.")],
    outargs=[("Summary", T(64045), "The refresh summary."),
             ("Results", T(64044), "The per-resource results.", 1),
             ("NewGeneration", UInt32, "The committed generation (unchanged on dry run or full failure).")])
# Materialize the well-known instance's Mandatory members (own and inherited) with stable
# default values, so loading the NodeSet alone yields a structurally complete registry
# instance rather than one that depends on a server populating Mandatory properties later.
instance_var(64100, "WoTRegistry", "RegistryId", String,
    "xRegistry registryid: the stable identifier of this registry (Mandatory, inherited from "
    "the xRegistry RegistryType). Default value for the well-known instance; a server MAY "
    "override it.", _scalar_value("String", "WoTRegistry"))
instance_var(64100, "WoTRegistry", "RefreshGeneration", UInt32,
    "The current committed projection generation; incremented on every committed refresh "
    "(Mandatory). Materialized as 0 at load time, before any Refresh has committed.",
    _scalar_value("UInt32", 0))

# ===========================================================================
# ==============  LEGACY OPC 10100-1 v1.02 MODEL (incorporated)  ============
# ===========================================================================
# The published WoT Connectivity 1.02 model (NamespaceUri
# http://opcfoundation.org/UA/WoT-Con/) is incorporated into THIS combined
# NodeSet from the pinned authoring sources under legacy/:
#   * legacy/WotConnection.csv  - the authoritative NodeId/NodeClass table
#                                 (every published id 1..172 preserved exactly)
#   * legacy/WotConnection.xml  - the ModelDesign (type bases, method signatures)
# The nodes are emitted in the own namespace (index 2), because xRegistry
# occupies index 1 in this combined document; numeric identifiers are unchanged.
# The management/upload surface is marked ReleaseStatus="Deprecated" (per OPC
# 11030); nothing is removed. Standard inherited members (FileType, Part 20;
# NamespaceMetadataType, Part 5) are expanded from OPC UA base definitions.
CAT_LEGACY = "WoT Connectivity 1.02 legacy (deprecated)"
CAT_LEGACY_INST = "WoT Connectivity 1.02 Legacy Instances"

_HERE = os.path.dirname(os.path.abspath(__file__))
LEGACY_DIR = os.path.join(os.path.dirname(_HERE), "legacy")
LEGACY_CSV = os.path.join(LEGACY_DIR, "WotConnection.csv")
LEGACY_XML = os.path.join(LEGACY_DIR, "WotConnection.xml")
_OPC = "{http://opcfoundation.org/UA/ModelDesign.xsd}"

# The 1.02 namespace this legacy surface belongs to, and the additive revision
# it is re-published under (values carried by the generated NamespaceMetadata).
LEGACY_NS = "http://opcfoundation.org/UA/WoT-Con/"

# BrowseNames that are namespace-0 well-known inherited members.
_NS0_LEAF = {
    "Size", "Writable", "UserWritable", "OpenCount", "MimeType", "MaxByteStringLength",
    "LastModifiedTime", "Open", "Close", "Read", "Write", "GetPosition", "SetPosition",
    "InputArguments", "OutputArguments", "ExportNamespace",
    "NamespaceUri", "NamespaceVersion", "NamespacePublicationDate", "IsNamespaceSubset",
    "StaticNodeIdTypes", "StaticNumericNodeIdRange", "StaticStringNodeIdPattern",
    "ConfigurationVersion", "ModelVersion",
    "DefaultRolePermissions", "DefaultUserRolePermissions", "DefaultAccessRestrictions",
}
# Placeholder leaf -> emitted BrowseName.
_PLACEHOLDER_BN = {
    "WoTAssetName_Placeholder": "<WoTAssetName>",
    "WoTPropertyName_Placeholder": "<WoTPropertyName>",
    "WoTConfigurationParameterName_Placeholder": "<WoTConfigurationParameterName>",
}
# Standard FileType Property member -> (DataType, modelling rule when a type member).
_FILE_VAR = {
    "Size": (UInt64, "Mandatory"), "Writable": (Boolean, "Mandatory"),
    "UserWritable": (Boolean, "Mandatory"), "OpenCount": (UInt16, "Mandatory"),
    "MimeType": (String, "Optional"), "MaxByteStringLength": (UInt32, "Optional"),
    "LastModifiedTime": (UtcTime, "Optional"),
}
# Standard method signatures (Part 20 FileType + the NamespaceMetadata export)
# not carried by the WoT ModelDesign. arg = (Name, DataType, ValueRank).
_STD_METHOD_ARGS = {
    "Open": ([("Mode", Byte, -1)], [("FileHandle", UInt32, -1)]),
    "Close": ([("FileHandle", UInt32, -1)], []),
    "Read": ([("FileHandle", UInt32, -1), ("Length", Int32, -1)], [("Data", ByteString, -1)]),
    "Write": ([("FileHandle", UInt32, -1), ("Data", ByteString, -1)], []),
    "GetPosition": ([("FileHandle", UInt32, -1)], [("Position", UInt64, -1)]),
    "SetPosition": ([("FileHandle", UInt32, -1), ("Position", UInt64, -1)], []),
    "ExportNamespace": ([], []),
}
_FILE_METHOD_LEAVES = set(_STD_METHOD_ARGS) | {"CloseAndUpdate"}
# NamespaceMetadataType member -> (DataType, ValueRank as str).
_NS_META_DT = {
    "NamespaceUri": (String, "-1"), "NamespaceVersion": (String, "-1"),
    "NamespacePublicationDate": (DateTime, "-1"), "IsNamespaceSubset": (Boolean, "-1"),
    "StaticNodeIdTypes": (IdType, "1"), "StaticNumericNodeIdRange": (NumericRange, "1"),
    "StaticStringNodeIdPattern": (String, "-1"), "ConfigurationVersion": (VersionTime, "-1"),
    "ModelVersion": (SemanticVersionString, "-1"),
    "DefaultRolePermissions": (RolePermissionType, "1"),
    "DefaultUserRolePermissions": (RolePermissionType, "1"),
    "DefaultAccessRestrictions": (AccessRestrictionType, "-1"),
}
# Model-specific member -> (DataType, ValueRank as str).
_WOT_MEMBER_DT = {
    "SupportedWoTBindings": (UriString, "1"), "AssetEndpoint": (String, "-1"),
    "License": (String, "-1"), "WoTConfigurationParameterName_Placeholder": (BaseDataType, "-1"),
    "WoTPropertyName_Placeholder": (BaseDataType, "-1"),
}
# Modelling rule of model-specific members when declared on a type.
_WOT_MEMBER_RULE = {
    "WoTAssetName_Placeholder": "OptionalPlaceholder",
    "WoTPropertyName_Placeholder": "OptionalPlaceholder",
    "WoTConfigurationParameterName_Placeholder": "OptionalPlaceholder",
    "WoTFile": "Mandatory", "AssetEndpoint": "Optional", "SupportedWoTBindings": "Optional",
    "CreateAsset": "Mandatory", "DeleteAsset": "Mandatory", "DiscoverAssets": "Optional",
    "CreateAssetForEndpoint": "Optional", "ConnectionTest": "Optional",
    "Configuration": "Optional", "License": "Optional", "CloseAndUpdate": "Mandatory",
}
_RULE_ID = {"Mandatory": MR_Mandatory, "Optional": MR_Optional,
            "OptionalPlaceholder": MR_OptionalPlaceholder, "MandatoryPlaceholder": MR_MandatoryPlaceholder}
# ModelDesign ua:Type name -> NodeId (for parsed DataTypes/base types).
_UA_NAME = {
    "String": String, "NodeId": NodeId, "Boolean": Boolean, "UInt32": UInt32, "UInt64": UInt64,
    "UInt16": UInt16, "Byte": Byte, "Int32": Int32, "ByteString": ByteString, "DateTime": DateTime,
    "UriString": UriString, "SemanticVersionString": SemanticVersionString, "IdType": IdType,
    "NumericRange": NumericRange, "BaseDataType": BaseDataType,
    "BaseObjectType": BaseObjectType, "BaseInterfaceType": BaseInterfaceType, "FileType": FileType,
    "HasComponent": HasComponent, "BaseDataVariableType": BaseDataVariableType,
}
# Instance root symbolics carry values / no modelling rule; type roots carry modelling rules.
_LEGACY_INSTANCE_ROOTS = {"WoTAssetConnectionManagement", "WotConNamespaceMetadata"}
_LEGACY_TYPE_ROOTS = {"WoTAssetConnectionManagementType", "IWoTAssetType",
                      "WoTAssetConfigurationType", "WoTAssetFileType"}
# Roots (and their whole subtree) marked deprecated: the entire 1.02 management/
# upload surface is superseded by the additive registry. NamespaceMetadata is not.
_LEGACY_DEPRECATED_ROOTS = _LEGACY_TYPE_ROOTS | {"WoTAssetConnectionManagement",
                                                 "HasWoTComponent"}


def _ua(name):
    return _UA_NAME.get((name or "").split(":")[-1], BaseDataType)


def _parse_modeldesign():
    """Parse the pinned ModelDesign for type bases/abstract/inverse and the WoT
    method-argument signatures (the parts a NodeId table cannot carry)."""
    root = ET.parse(LEGACY_XML).getroot()
    types, methodsig, concrete_mt = {}, {}, {}

    def args_of(mel, which):
        out = []
        grp = mel.find(_OPC + which)
        if grp is None:
            return out
        for a in grp.findall(_OPC + "Argument"):
            vr = (a.get("ValueRank") or "").lower()
            out.append((a.get("Name"), _ua(a.get("DataType")), 1 if vr == "array" else -1))
        return out

    for e in list(root):
        tag = e.tag.split("}")[-1]
        sym = e.get("SymbolicName")
        if tag in ("ObjectType", "ReferenceType"):
            inv = e.find(_OPC + "InverseName")
            types[sym] = (tag, e.get("BaseType"), e.get("IsAbstract", "false") == "true",
                          inv.text if inv is not None else None)
        elif tag == "Method":
            methodsig[sym] = (args_of(e, "InputArguments"), args_of(e, "OutputArguments"))
    for m in root.iter(_OPC + "Method"):
        td, sym = m.get("TypeDefinition"), m.get("SymbolicName")
        if td and sym:
            concrete_mt[sym] = td
    return types, methodsig, concrete_mt


def _argument_value(args):
    """Build the <Value> Argument[] fragment for a method InputArguments/OutputArguments."""
    parts = ['<Value>', '<ListOfExtensionObject xmlns="http://opcfoundation.org/UA/2008/02/Types.xsd">']
    for (aname, adtype, arank) in args:
        parts.append("<ExtensionObject><TypeId><Identifier>i=297</Identifier></TypeId><Body><Argument>")
        parts.append(f"<Name>{sx.escape(aname)}</Name><DataType><Identifier>{adtype}</Identifier></DataType>")
        if arank is not None and arank >= 0:
            parts.append(f"<ValueRank>{arank}</ValueRank><ArrayDimensions><UInt32>0</UInt32></ArrayDimensions>")
        else:
            parts.append("<ValueRank>-1</ValueRank><ArrayDimensions/>")
        parts.append("</Argument></Body></ExtensionObject>")
    parts.append("</ListOfExtensionObject></Value>")
    return "".join(parts)


def build_legacy():
    """Reconstruct the incorporated 1.02 nodes from the pinned sources, preserving
    every numeric NodeId and NodeClass. Reserved ('Unspecified') CSV rows are kept
    in the CSV but not emitted as nodes."""
    types_md, methodsig_md, concrete_mt = _parse_modeldesign()

    rows = []
    with open(LEGACY_CSV, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            sym, sid, cls = line.split(",")
            rows.append((sym, int(sid), cls))
    sym2id = {sym: sid for sym, sid, cls in rows}

    def parent_sym(sym):
        best = None
        for other in sym2id:
            if other != sym and sym.startswith(other + "_") and (best is None or len(other) > len(best)):
                best = other
        return best

    parents = {sym: parent_sym(sym) for sym, _, _ in rows}

    def root_sym(sym):
        cur = sym
        while parents[cur] is not None:
            cur = parents[cur]
        return cur

    def leaf_of(sym):
        p = parents[sym]
        return sym[len(p) + 1:] if p else sym

    def method_args(method_leaf):
        if method_leaf in _STD_METHOD_ARGS:
            return _STD_METHOD_ARGS[method_leaf]
        mt = concrete_mt.get(method_leaf)
        if mt is None and method_leaf in methodsig_md:
            mt = method_leaf
        return methodsig_md.get(mt, ([], []))

    # ---- pass 1: create the node objects (ids/classes from the pinned CSV) -----
    meta = {}
    for sym, sid, cls in rows:
        if cls == "Unspecified":
            continue  # reserved id, retained in CSV only
        p = parents[sym]
        leaf = leaf_of(sym)
        root = root_sym(sym)
        is_instance = root in _LEGACY_INSTANCE_ROOTS
        bn = LEGACY_NS if sym == "WotConNamespaceMetadata" else _PLACEHOLDER_BN.get(leaf, leaf)
        attrs = {}
        if leaf in _NS0_LEAF:
            attrs["_ns0bn"] = True
        if root in _LEGACY_DEPRECATED_ROOTS:
            attrs["_release_status"] = "Deprecated"
        if p is not None:
            parent_nid = T(sym2id[p])
        elif sym == "WoTAssetConnectionManagement":
            parent_nid = ObjectsFolder
        elif sym == "WotConNamespaceMetadata":
            parent_nid = Server_Namespaces
        else:
            parent_nid = None
        add(sid, "UA" + cls, bn, sym, desc=None, parent=parent_nid, attrs=attrs,
            category=(CAT_LEGACY_INST if is_instance else CAT_LEGACY))
        meta[sid] = (sym, cls, p, leaf, root, is_instance)

    # ---- pass 2: attributes and references (all nodes now exist) ---------------
    for sid, (sym, cls, p, leaf, root, is_instance) in meta.items():
        n = NODES[sid]
        pid = sym2id[p] if p else None
        is_type_member = root in _LEGACY_TYPE_ROOTS and p is not None
        is_method_template_child = root.endswith("MethodType") and p is not None

        if cls == "ObjectType":
            _, base, abstract, _inv = types_md.get(sym, ("ObjectType", "ua:BaseObjectType", False, None))
            ref(sid, HasSubtype, _ua(base), forward=False)
            n.abstract = abstract
            continue
        if cls == "ReferenceType":
            _, base, abstract, inv = types_md.get(sym, ("ReferenceType", "ua:HasComponent", False, None))
            ref(sid, HasSubtype, _ua(base), forward=False)
            n.inverse = inv
            continue

        # Instance/type roots (Objects with no legacy parent).
        if p is None and sym == "WoTAssetConnectionManagement":
            ref(sid, HasTypeDefinition, T(1))
            ref(sid, Organizes, ObjectsFolder, forward=False)
            continue
        if p is None and sym == "WotConNamespaceMetadata":
            ref(sid, HasTypeDefinition, NamespaceMetadataType)
            ref(sid, HasComponent, Server_Namespaces, forward=False)
            continue
        if p is None:
            # Standalone *MethodType declaration node (Method).
            continue

        # Hierarchical reference to the (legacy) parent.
        if leaf == "WoTAssetName_Placeholder":
            reftype = Organizes
        elif leaf == "WoTPropertyName_Placeholder":
            reftype = T(142)  # HasWoTComponent
        elif cls == "Variable":
            reftype = HasProperty
        else:
            reftype = HasComponent
        ref(sid, reftype, T(pid), forward=False)
        ref(pid, reftype, T(sid))

        # Modelling rule (type members and method-template args only).
        if (is_type_member or is_method_template_child) and not is_instance:
            if leaf in _WOT_MEMBER_RULE:
                rule = _WOT_MEMBER_RULE[leaf]
            elif leaf in _FILE_VAR:
                rule = _FILE_VAR[leaf][1]
            elif leaf in _FILE_METHOD_LEAVES or leaf == "ExportNamespace":
                rule = "Mandatory"
            elif leaf in ("InputArguments", "OutputArguments"):
                rule = "Mandatory"
            else:
                rule = "Optional"
            ref(sid, HasModellingRule, _RULE_ID[rule])

        # TypeDefinition + DataType by NodeClass.
        if cls == "Object":
            if leaf == "WoTFile":
                td = T(110)
            elif leaf == "NamespaceFile":
                td = FileType
            elif leaf == "Configuration":
                td = T(105)
            elif leaf == "WoTAssetName_Placeholder":
                td = BaseObjectType
            else:
                td = BaseObjectType
            ref(sid, HasTypeDefinition, td)
        elif cls == "Variable":
            if leaf in ("InputArguments", "OutputArguments"):
                which = 0 if leaf == "InputArguments" else 1
                margs = method_args(leaf_of(p))[which]
                n.attrs["DataType"] = Argument
                n.attrs["ValueRank"] = "1"
                n.attrs["ArrayDimensions"] = str(len(margs))
                n.value = _argument_value(margs)
                ref(sid, HasTypeDefinition, PropertyType)
            else:
                if leaf in _WOT_MEMBER_DT:
                    dt, vr = _WOT_MEMBER_DT[leaf]
                elif leaf in _FILE_VAR:
                    dt, vr = _FILE_VAR[leaf][0], "-1"
                elif leaf in _NS_META_DT:
                    dt, vr = _NS_META_DT[leaf]
                else:
                    dt, vr = BaseDataType, "-1"
                n.attrs["DataType"] = dt
                n.attrs["ValueRank"] = vr
                if vr == "1":
                    n.attrs["ArrayDimensions"] = "0"
                td = BaseDataVariableType if leaf == "WoTPropertyName_Placeholder" else PropertyType
                ref(sid, HasTypeDefinition, td)
                # NamespaceMetadata instance property values reflect the 1.1 revision.
                if is_instance and leaf in _NS_META_VALUE:
                    n.value = _NS_META_VALUE[leaf]

    # HasInterface on the <WoTAssetName> placeholder (implements IWoTAssetType).
    if 2 in NODES and 42 in NODES:
        ref(2, HasInterface, T(42))


# NamespaceMetadata property values for the incorporated legacy namespace, carrying
# the new 1.1 revision metadata while the stable NodeIds are preserved.
_NS_META_VALUE = {
    "NamespaceUri": _scalar_value("String", LEGACY_NS),
    "NamespaceVersion": _scalar_value("String", "1.1.0"),
    "NamespacePublicationDate": _scalar_value("DateTime", "2026-07-22T00:00:00Z"),
    "IsNamespaceSubset": _scalar_value("Boolean", "false"),
    "StaticStringNodeIdPattern": _scalar_value("String", ""),
    "ModelVersion": _scalar_value("String", "1.1.0"),
}

build_legacy()

# ===========================================================================
# Emission
# ===========================================================================
NAMESPACE = "http://opcfoundation.org/UA/WoT-Con/"
VERSION = "1.1.0"
PUBDATE = "2026-07-22T00:00:00Z"
XR_NAMESPACE = "http://opcfoundation.org/UA/xRegistry/"
XR_VERSION = "0.1.0"
XR_PUBDATE = "2026-07-16T00:00:00Z"
UA_REQUIRED_VERSION = "1.05.04"
UA_REQUIRED_PUBDATE = "2024-05-01T00:00:00Z"

ALIASES = [
    ("Boolean", Boolean), ("Byte", Byte), ("UInt16", UInt16), ("Int32", Int32),
    ("UInt32", UInt32), ("UInt64", UInt64), ("Double", Double),
    ("String", String), ("DateTime", DateTime), ("UtcTime", UtcTime), ("ByteString", ByteString),
    ("NodeId", NodeId), ("ExpandedNodeId", ExpandedNodeId), ("LocalizedText", LocalizedText),
    ("Duration", Duration), ("Argument", Argument), ("Structure", Structure),
    ("Enumeration", Enumeration), ("UriString", UriString), ("BaseDataType", BaseDataType),
    ("Organizes", Organizes), ("HasModellingRule", HasModellingRule),
    ("HasTypeDefinition", HasTypeDefinition), ("HasSubtype", HasSubtype),
    ("HasProperty", HasProperty), ("HasComponent", HasComponent), ("HasEncoding", HasEncoding),
    ("HasInterface", HasInterface),
    ("GeneratesEvent", GeneratesEvent), ("HasNotifier", HasNotifier),
    ("NonHierarchicalReferences", NonHierarchicalReferences),
]
REFTYPE_ALIAS = {v: k for k, v in ALIASES}
DATATYPE_ALIAS = {v: k for k, v in ALIASES}
_PRIO = {HasModellingRule: 0, HasSubtype: 1}


def _sorted_refs(refs):
    return sorted(range(len(refs)), key=lambda i: (_PRIO.get(refs[i][0], 2), i))


def _fmt_reftype(t):
    return REFTYPE_ALIAS.get(t, t)


def _fmt_datatype(t):
    return DATATYPE_ALIAS.get(t, t)


def _fmt_browse_name(n):
    if n.attrs.get("_ns0bn"):
        return sx.escape(n.bname)
    return f"{OWN_NS}:{sx.escape(n.bname)}"


def _emit_node(n):
    a = [f'{n.cls} NodeId="{T(n.nid)}"', f'BrowseName="{_fmt_browse_name(n)}"']
    if n.parent is not None:
        a.append(f'ParentNodeId="{n.parent}"')
    for k in ("DataType", "ValueRank", "ArrayDimensions", "MethodDeclarationId", "EventNotifier"):
        if k in n.attrs:
            v = _fmt_datatype(n.attrs[k]) if k == "DataType" else n.attrs[k]
            a.append(f'{k}="{v}"')
    if n.cls in ("UAObjectType", "UAReferenceType") and n.abstract:
        a.append('IsAbstract="true"')
    if n.attrs.get("_release_status"):
        a.append(f'ReleaseStatus="{n.attrs["_release_status"]}"')
    lines = ["  <" + " ".join(a) + ">"]
    lines.append(f"    <DisplayName>{sx.escape(n.display)}</DisplayName>")
    if n.desc:
        lines.append(f"    <Description>{sx.escape(n.desc)}</Description>")
    if n.inverse:
        lines.append(f"    <InverseName>{sx.escape(n.inverse)}</InverseName>")
    if n.category:
        lines.append(f"    <Category>{sx.escape(n.category)}</Category>")
    lines.append("    <References>")
    for i in _sorted_refs(n.refs):
        rt, tgt, fwd = n.refs[i]
        lines.append(f'      <Reference ReferenceType="{_fmt_reftype(rt)}"{("" if fwd else " IsForward=\"false\"")}>{tgt}</Reference>')
    lines.append("    </References>")
    if n.definition:
        lines.append("    " + n.definition)
    if n.value:
        lines.append("    " + n.value)
    lines.append(f"  </{n.cls}>")
    return "\n".join(lines)


def emit():
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<!-- OPC UA WoT Connectivity 1.1 combined namespace (incorporated 1.02 legacy + additive registry).'
           ' PROVISIONAL registry NodeIds (final IDs assigned by the OPC Foundation); 1.02 NodeIds 1..172 preserved. -->',
           '<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
           '  <NamespaceUris>', f'    <Uri>{XR_NAMESPACE}</Uri>', f'    <Uri>{NAMESPACE}</Uri>', '  </NamespaceUris>',
           '  <Models>', f'    <Model ModelUri="{NAMESPACE}" Version="{VERSION}" PublicationDate="{PUBDATE}">',
           f'      <RequiredModel ModelUri="http://opcfoundation.org/UA/" Version="{UA_REQUIRED_VERSION}" PublicationDate="{UA_REQUIRED_PUBDATE}" />',
           f'      <RequiredModel ModelUri="{XR_NAMESPACE}" Version="{XR_VERSION}" PublicationDate="{XR_PUBDATE}" />',
           '    </Model>', '  </Models>', '  <Aliases>']
    for name, val in ALIASES:
        out.append(f'    <Alias Alias="{name}">{val}</Alias>')
    out.append('  </Aliases>')
    for nid in ORDER:
        out.append(_emit_node(NODES[nid]))
    out.append('</UANodeSet>')
    return "\n".join(out) + "\n"


def emit_csv():
    """Combined NodeId table: the pinned 1.02 rows verbatim (every id 1..172 and
    NodeClass preserved, including reserved 'Unspecified' rows) followed by the
    additive registry rows (64000+)."""
    legacy = open(LEGACY_CSV, encoding="utf-8").read().replace("\r\n", "\n").strip("\n")
    registry = "\n".join(f"{NODES[nid].symbolic},{nid},{NODES[nid].cls[2:]}"
                         for nid in ORDER if nid >= OWN_MIN)
    return legacy + "\n" + registry + "\n"


# ---------------------------------------------------------------------------
# Annex A (model-reference.md) generation
# ---------------------------------------------------------------------------
XREGISTRY_SPEC = (
    "https://github.com/marcschier/opcua-drafts/blob/main/"
    "core-specs/xregistry/OPC-UA-xRegistry.md"
)
WOT_BINDING_SPEC = "../WoT-Binding/OPC-UA-WoT-Binding.md"

LINK_MAP = {
    "BaseObjectType": "https://reference.opcfoundation.org/specs/OPC-10000-5/6.2",
    "FolderType": "https://reference.opcfoundation.org/specs/OPC-10000-5/6.6",
    "PropertyType": "https://reference.opcfoundation.org/specs/OPC-10000-5/7.3",
    "BaseDataVariableType": "https://reference.opcfoundation.org/specs/OPC-10000-5/7.4",
    "BaseEventType": "https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.2",
    "FileType": "https://reference.opcfoundation.org/specs/OPC-10000-20/4.2",
    "Structure": "https://reference.opcfoundation.org/specs/OPC-10000-5/8.24",
    "Enumeration": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.40",
    "NonHierarchicalReferences": "https://reference.opcfoundation.org/specs/OPC-10000-5/11.3",
    "NodeId": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.2.1",
    "ExpandedNodeId": "https://reference.opcfoundation.org/specs/OPC-10000-3/8.2.3",
    "BaseInterfaceType": "https://reference.opcfoundation.org/specs/OPC-10000-5/6.2",
    "HasComponent": "https://reference.opcfoundation.org/specs/OPC-10000-5/11.3",
    "RegistryType": XREGISTRY_SPEC + "#type-RegistryType",
    "GroupType": XREGISTRY_SPEC + "#type-GroupType",
    "ResourceType": XREGISTRY_SPEC + "#type-ResourceType",
}
_BASE_NAMES = {
    BaseObjectType: "BaseObjectType", FolderType: "FolderType", BaseDataVariableType: "BaseDataVariableType",
    PropertyType: "PropertyType", BaseEventType: "BaseEventType", Structure: "Structure",
    Enumeration: "Enumeration", NonHierarchicalReferences: "NonHierarchicalReferences",
    BaseInterfaceType: "BaseInterfaceType", FileType: "FileType", HasComponent: "HasComponent",
}
_XR_NAMES = {XRegistry_RegistryType: "RegistryType", XRegistry_GroupType: "GroupType",
             XRegistry_ResourceType: "ResourceType"}
_OWN = None


def _friendly(tgt):
    if tgt in _BASE_NAMES:
        return _BASE_NAMES[tgt]
    if tgt in _XR_NAMES:
        return _XR_NAMES[tgt]
    if tgt in DATATYPE_ALIAS:
        return DATATYPE_ALIAS[tgt]
    if tgt.startswith(f"ns={OWN_NS};i="):
        num = int(tgt.split("i=")[1])
        if num in NODES:
            return NODES[num].bname
    return tgt


def _anchor(name):
    return "type-" + name


def _link(display):
    if not display:
        return display
    arr = ""
    core = display
    if core.endswith("[]"):
        arr = r"\[\]"; core = core[:-2]
    if core in _OWN:
        return f"[{core}](#{_anchor(core)})" + arr
    if core in LINK_MAP:
        return f"[{core}]({LINK_MAP[core]})" + arr
    return core + arr


def _member_rule(n):
    for rt, tgt, fwd in n.refs:
        if rt == HasModellingRule:
            return {MR_Mandatory: "Mandatory", MR_Optional: "Optional",
                    MR_OptionalPlaceholder: "OptionalPlaceholder"}.get(tgt, "")
    return ""


def _supertype(n):
    for rt, tgt, fwd in n.refs:
        if rt == HasSubtype and not fwd:
            return tgt
    return ""


def _members_of(nid):
    out = []
    for rt, tgt, fwd in NODES[nid].refs:
        if rt in (HasComponent, HasProperty, Organizes) and fwd and tgt.startswith(f"ns={OWN_NS};i="):
            num = int(tgt.split("i=")[1])
            if num in NODES:
                out.append(num)
    return out


def _generated_events(nid):
    out = []
    for rt, tgt, fwd in NODES[nid].refs:
        if rt == GeneratesEvent and fwd and tgt.startswith(f"ns={OWN_NS};i="):
            out.append(int(tgt.split("i=")[1]))
    return out


def _dt_display(mn):
    dt = _friendly(mn.attrs.get("DataType", "")) if mn.attrs.get("DataType") else ""
    if mn.attrs.get("ValueRank") == "1" and dt:
        dt += "[]"
    return _link(dt)


def emit_md():
    global _OWN
    _OWN = {NODES[nid].bname for nid in ORDER
            if NODES[nid].cls in ("UAObjectType", "UADataType", "UAReferenceType")}
    obj_types = [nid for nid in ORDER if NODES[nid].cls == "UAObjectType" and NODES[nid].category in (CAT,)]
    event_types = [nid for nid in ORDER if NODES[nid].cls == "UAObjectType" and NODES[nid].category == CAT_EV]
    enum_types = [nid for nid in ORDER if nid in ENUM_FIELDS]
    struct_types = [nid for nid in ORDER if nid in STRUCT_FIELDS]
    ref_types = [nid for nid in ORDER if NODES[nid].cls == "UAReferenceType" and NODES[nid].category == CAT_REF]
    legacy_types = [nid for nid in ORDER if NODES[nid].category == CAT_LEGACY
                    and NODES[nid].cls in ("UAObjectType", "UAReferenceType")]
    legacy_instances = [nid for nid in ORDER if NODES[nid].category == CAT_LEGACY_INST
                        and NODES[nid].cls == "UAObject" and NODES[nid].parent
                        and not NODES[nid].parent.startswith(f"ns={OWN_NS};")
                        and any(rt == HasTypeDefinition and str(tgt).startswith(f"ns={OWN_NS};")
                                for rt, tgt, fwd in NODES[nid].refs)]
    method_args, method_out = {}, {}
    for nid in ORDER:
        n = NODES[nid]
        if n.cls == "UAVariable" and n.bname in ("InputArguments", "OutputArguments") and n.value:
            names = re.findall(r"<Name>([^<]+)</Name>", n.value)
            pid = int(n.parent.split("i=")[1]) if n.parent else None
            (method_args if n.bname == "InputArguments" else method_out)[pid] = names

    md = ['<a id="annex-a"></a>', '', '## Annex A — Information model\n',
          'This annex is the normative node reference. It is generated from `tools/build_model.py` and always '
          'matches `Opc.Ua.WoTCon.NodeSet2.xml`. It documents one combined model in the companion namespace '
          f'`{NAMESPACE}` (namespace index `2` in this NodeSet, after the required '
          f'`{XR_NAMESPACE}` base model at index `1`). The additive **WoT Connectivity 1.1** registry types '
          f'**extend the abstract [OPC UA — xRegistry]({XREGISTRY_SPEC}) base types** '
          '(`RegistryType`/`GroupType`/`ResourceType`) and use provisional NodeIds in the `64000+` block (final IDs '
          'are assigned by the OPC Foundation). The incorporated **OPC 10100-1 v1.02** legacy model is preserved '
          'unchanged at its published NodeIds `1..172` and is documented, with its `Deprecated` release status, under '
          '*Legacy model* below. The **Declared in** column marks members inherited from a supertype.\n']

    md.append('### Type overview\n')
    md.append('| NodeId | BrowseName | NodeClass | Subtype of |')
    md.append('|---|---|---|---|')
    for nid in obj_types + event_types + enum_types + struct_types + ref_types:
        n = NODES[nid]
        md.append(f"| ns={OWN_NS};i={nid} | {_link(n.bname)} | {n.cls[2:]} | {_link(_friendly(_supertype(n)))} |")
    md.append('')

    md.append('### Object types\n')
    for nid in obj_types:
        n = NODES[nid]
        md.append(f'<a id="{_anchor(n.bname)}"></a>')
        md.append('')
        abstract = " *(abstract)*" if n.abstract else ""
        md.append(f"#### {n.bname}  (ns={OWN_NS};i={nid}){abstract}\n")
        md.append(f"*Inherits from:* {_link(_friendly(_supertype(n)))}\n")
        if n.desc:
            md.append(n.desc + "\n")
        rows = []
        for m in _members_of(nid):
            mn = NODES[m]
            rows.append((mn.bname, mn.cls[2:], _dt_display(mn), _member_rule(mn), n.bname,
                         (mn.desc or "").replace("|", "/")))
        if rows:
            md.append('| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |')
            md.append('|---|---|---|---|---|---|')
            for r in rows:
                md.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")
            md.append('')
        ge = _generated_events(nid)
        if ge:
            md.append("*Generates events:* " + ", ".join(_link(NODES[e].bname) for e in ge) + "\n")

    md.append('### Event types\n')
    for nid in event_types:
        n = NODES[nid]
        md.append(f'<a id="{_anchor(n.bname)}"></a>')
        md.append('')
        abstract = " *(abstract)*" if n.abstract else ""
        md.append(f"#### {n.bname}  (ns={OWN_NS};i={nid}){abstract}\n")
        md.append(f"*Subtype of:* {_link(_friendly(_supertype(n)))}\n")
        if n.desc:
            md.append(n.desc + "\n")
        rows = []
        for m in _members_of(nid):
            mn = NODES[m]
            rows.append((mn.bname, _dt_display(mn), _member_rule(mn), n.bname, (mn.desc or "").replace("|", "/")))
        if rows:
            md.append('| Field | DataType | ModellingRule | Declared in | Description |')
            md.append('|---|---|---|---|---|')
            for r in rows:
                md.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |")
            md.append('')

    md.append('### DataTypes\n')
    for nid in enum_types:
        n = NODES[nid]
        md.append(f'<a id="{_anchor(n.bname)}"></a>')
        md.append('')
        md.append(f"#### {n.bname}  (ns={OWN_NS};i={nid})\n")
        md.append(f"*Subtype of:* {_link(_friendly(_supertype(n)))}\n")
        if n.desc:
            md.append(n.desc + "\n")
        md.append("| Name | Value | Description |")
        md.append("|---|---|---|")
        for (fname, val, fdesc) in ENUM_FIELDS[nid]:
            md.append(f"| {fname} | {val} | {(fdesc or '').replace('|', '/')} |")
        md.append('')
    for nid in struct_types:
        n = NODES[nid]
        md.append(f'<a id="{_anchor(n.bname)}"></a>')
        md.append('')
        md.append(f"#### {n.bname}  (ns={OWN_NS};i={nid})\n")
        md.append(f"*Subtype of:* {_link(_friendly(_supertype(n)))}\n")
        if n.desc:
            md.append(n.desc + "\n")
        md.append("| Field | DataType | Description |")
        md.append("|---|---|---|")
        for f in STRUCT_FIELDS[nid]:
            fname, fdt, fdesc = f[0], f[1], f[2]
            frank = f[3] if len(f) > 3 else -1
            dt = _friendly(fdt)
            if frank is not None and frank >= 0:
                dt += "[]"
            md.append(f"| {fname} | {_link(dt)} | {(fdesc or '').replace('|', '/')} |")
        md.append('')

    md.append('### Reference types\n')
    for nid in ref_types:
        md.append(f'<a id="{_anchor(NODES[nid].bname)}"></a>')
        md.append('')
    md.append('| NodeId | BrowseName | InverseName | Subtype of | Description |')
    md.append('|---|---|---|---|---|')
    for nid in ref_types:
        n = NODES[nid]
        md.append(f"| ns={OWN_NS};i={nid} | {n.bname} | {n.inverse or ''} | {_link(_friendly(_supertype(n)))} | "
                  f"{(n.desc or '').replace('|', '/')} |")
    md.append('')

    md.append('### Methods\n')
    md.append('| Method | Owning type | Input arguments | Output arguments |')
    md.append('|---|---|---|---|')
    for nid in ORDER:
        n = NODES[nid]
        if n.cls != "UAMethod" or n.category is not None:
            continue  # registry declaration methods only; legacy methods are listed under §13.1
        owner = NODES[int(n.parent.split("i=")[1])].bname if n.parent else ""
        ins = ", ".join(method_args.get(nid, [])) or "(none)"
        outs = ", ".join(method_out.get(nid, [])) or "(none)"
        md.append(f"| {n.bname} | {_link(owner)} | {ins} | {outs} |")
    md.append('')

    md.append('### Well-known instances\n')
    md.append('| BrowseName | NodeId | TypeDefinition | Note |')
    md.append('|---|---|---|---|')
    for nid in ORDER:
        n = NODES[nid]
        if n.category != CAT_INST or n.cls != "UAObject":
            continue
        td = ""
        for rt, tgt, fwd in n.refs:
            if rt == HasTypeDefinition:
                td = _link(_friendly(tgt))
        md.append(f"| {n.bname} | ns={OWN_NS};i={nid} | {td} | {(n.desc or '').replace('|','/')} |")
    md.append('')

    # ---- Legacy model (OPC 10100-1 v1.02, incorporated and deprecated) --------
    md.append('### Legacy model (OPC 10100-1 v1.02 — preserved, deprecated)\n')
    md.append('The published OPC 10100-1 v1.02 WoT Connectivity model is incorporated into this combined NodeSet '
              'unchanged, at its exact published NodeIds (`1..172`) and NodeClasses (preserved from the pinned '
              '`legacy/WotConnection.csv`). Because the additive registry supersedes it, the whole management/upload '
              'surface carries `ReleaseStatus="Deprecated"` — it is deprecated, not removed, so existing 1.02 clients '
              'keep working. The `WoTAssetConnectionManagement` object remains at its published NodeId and callable. '
              'Method signatures are unchanged and are listed in §13.1.\n')
    for nid in legacy_types:
        md.append(f'<a id="{_anchor(NODES[nid].bname)}"></a>')
    md.append('')
    md.append('| NodeId | BrowseName | NodeClass | Subtype of | Release status |')
    md.append('|---|---|---|---|---|')
    for nid in legacy_types:
        n = NODES[nid]
        status = n.attrs.get("_release_status", "Released")
        md.append(f"| ns={OWN_NS};i={nid} | {n.bname} | {n.cls[2:]} | {_link(_friendly(_supertype(n)))} | {status} |")
    md.append('')
    if legacy_instances:
        md.append('| Well-known instance | NodeId | TypeDefinition | Release status |')
        md.append('|---|---|---|---|')
        for nid in legacy_instances:
            n = NODES[nid]
            td = ""
            for rt, tgt, fwd in n.refs:
                if rt == HasTypeDefinition:
                    td = _link(_friendly(tgt))
            status = n.attrs.get("_release_status", "Released")
            md.append(f"| {n.bname} | ns={OWN_NS};i={nid} | {td} | {status} |")
        md.append('')
    return "\n".join(md).rstrip("\n") + "\n"


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.dirname(here)
    with open(os.path.join(outdir, "Opc.Ua.WoTCon.NodeSet2.xml"), "w", encoding="utf-8") as f:
        f.write(emit())
    with open(os.path.join(outdir, "Opc.Ua.WoTCon.NodeIds.csv"), "w", encoding="utf-8") as f:
        f.write(emit_csv())
    with open(os.path.join(here, "model-reference.md"), "w", encoding="utf-8") as f:
        f.write(emit_md())
    nt = sum(1 for k in NODES if NODES[k].cls in ("UAObjectType", "UADataType", "UAReferenceType"))
    print(f"Nodes: {len(NODES)}  (types: {nt})")
    print(f"Member id range: 64500..{_next_member[0] - 1}")
