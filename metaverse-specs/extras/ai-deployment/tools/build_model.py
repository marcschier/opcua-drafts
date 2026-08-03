#!/usr/bin/env python3
"""
Generator for the OPC UA - AI Deployment and Learning companion specification.

Emits, from a single in-code source of truth:
  * ../../../ai-deployment/Opc.Ua.AiDeployment.NodeSet2.xml - the information model
  * ../../../ai-deployment/Opc.Ua.AiDeployment.NodeIds.csv  - the NodeId assignments
  * model-reference.md                                      - the generated Annex A

The model is a COMPANION specification in its OWN namespace
(http://opcfoundation.org/UA/AI/, namespace index 1). Nodes therefore use
`ns=1;i=<n>` NodeIds; references to base UA types use plain `i=<n>`.

It is deliberately STANDALONE and deliberately DOMAIN-NEUTRAL: the only
<RequiredModel> is the base UA namespace, and nothing here mentions a camera, a robot
or any other kind of equipment. A model is trained on a dataset, deployed somewhere,
and replaced by a better one; that story is the same whether the input is an image, a
vibration spectrum or a process trace.

NodeIds are PROVISIONAL (final IDs assigned by the OPC Foundation) and follow the repo
convention: ObjectTypes/Interfaces 1001+, Enumerations 3001+ (EnumStrings = enum + 900),
Structures 3050+, ReferenceTypes 4001+, DataType encodings 5001+, well-known instances
7001+, and all remaining instance declarations sequentially from 6001. New members must
be APPENDED so that previously published member NodeIds stay stable.

Design notes:
  * This model was factored OUT of OPC UA - Vision, where it had accumulated because
    vision happened to be the first specification in this repository that needed it.
    Nothing in it was vision-specific except one sentence about class indices, which is
    now stated as a general contract on LabelClasses.
  * A consuming specification binds to this one through a NodeId Property, not a
    reference and not a RequiredModel, so a Server can implement either alone.
  * Digest and DigestAlgorithm are Mandatory because the provenance chain from a
    published result back to the model artefact is the only reason several of the
    other members are worth reading at all.
"""
from __future__ import annotations
import os
import re
import xml.sax.saxutils as sx

NAMESPACE = "http://opcfoundation.org/UA/AI/"
VERSION = "0.1.0"
PUBDATE = "2026-08-02T00:00:00Z"
BASE_UA_VERSION = "1.05.04"
BASE_UA_PUBDATE = "2023-12-15T00:00:00Z"

# --- base UA NodeIds (namespace 0) -----------------------------------------
HasComponent = "i=47"
HasProperty = "i=46"
HasSubtype = "i=45"
Organizes = "i=35"
HasTypeDefinition = "i=40"
HasModellingRule = "i=37"
HasInterface = "i=17603"
HasEncoding = "i=38"

MR_Mandatory = "i=78"
MR_Optional = "i=80"
MR_OptionalPlaceholder = "i=11508"
MR_MandatoryPlaceholder = "i=11510"

BaseObjectType = "i=58"
FolderType = "i=61"
PropertyType = "i=68"
BaseDataVariableType = "i=63"
BaseInterfaceType = "i=17602"
DataTypeEncodingType = "i=76"
Enumeration = "i=29"
Structure = "i=22"
NonHierarchicalReferences = "i=32"

BaseDataType = "i=24"
Boolean = "i=1"
Int32 = "i=6"
UInt32 = "i=7"
UInt64 = "i=9"
Double = "i=11"
String = "i=12"
Guid = "i=14"
ByteString = "i=15"
NodeId_ = "i=17"
QualifiedName = "i=20"
LocalizedText = "i=21"
UtcTime = "i=294"
Duration = "i=290"
Argument = "i=296"
EUInformation = "i=887"
KeyValuePair = "i=14533"

Server = "i=2253"

ALIASES = [
    ("Boolean", Boolean), ("Int32", Int32), ("UInt32", UInt32), ("UInt64", UInt64),
    ("Double", Double), ("String", String), ("Guid", Guid), ("ByteString", ByteString),
    ("NodeId", NodeId_), ("QualifiedName", QualifiedName), ("LocalizedText", LocalizedText),
    ("UtcTime", UtcTime), ("Duration", Duration), ("Argument", Argument),
    ("EUInformation", EUInformation), ("KeyValuePair", KeyValuePair),
    ("BaseDataType", BaseDataType),
    ("HasComponent", HasComponent), ("HasProperty", HasProperty),
    ("HasSubtype", HasSubtype), ("Organizes", Organizes),
    ("HasTypeDefinition", HasTypeDefinition), ("HasModellingRule", HasModellingRule),
    ("HasInterface", HasInterface), ("HasEncoding", HasEncoding),
    ("Mandatory", MR_Mandatory), ("Optional", MR_Optional),
    ("OptionalPlaceholder", MR_OptionalPlaceholder),
    ("MandatoryPlaceholder", MR_MandatoryPlaceholder),
]

REFTYPE_ALIAS = {v: k for k, v in ALIASES}
DATATYPE_ALIAS = {v: k for k, v in ALIASES}


# --- node registry ---------------------------------------------------------
class Node:
    __slots__ = ("nid", "cls", "bname", "symbolic", "display", "desc", "parent",
                 "attrs", "refs", "category", "definition", "value", "abstract",
                 "inverse")

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


NODES = {}
ORDER = []
_next_member = [6001]
_next_encoding = [5001]


def _mid():
    v = _next_member[0]
    _next_member[0] += 1
    return v


def T(nid):
    """Own-namespace NodeId (ns=1)."""
    return f"ns=1;i={nid}"


def add(nid, cls, bname, symbolic, display=None, desc=None, parent=None,
        attrs=None, category=None, abstract=False):
    n = Node(nid, cls, bname, symbolic, display, desc, parent, attrs, category, abstract)
    NODES[nid] = n
    ORDER.append(nid)
    return n


def ref(nid, reftype, target, forward=True):
    NODES[nid].refs.append((reftype, target, forward))


# --- builders --------------------------------------------------------------
def object_type(nid, name, base, desc, abstract=False):
    add(nid, "UAObjectType", name, name, desc=desc, category=CAT, abstract=abstract)
    ref(nid, HasSubtype, base, forward=False)
    return nid


def interface_type(nid, name, base, desc):
    add(nid, "UAObjectType", name, name, desc=desc, category=CAT, abstract=True)
    ref(nid, HasSubtype, base, forward=False)
    return nid


def reference_type(nid, name, inverse, desc, base=NonHierarchicalReferences):
    n = add(nid, "UAReferenceType", name, name, desc=desc, category=CAT_RT)
    n.inverse = inverse
    ref(nid, HasSubtype, base, forward=False)
    return nid


def _member_var(owner, owner_sym, name, datatype, typedef, rule, reftype, desc,
                valuerank="-1"):
    nid = _mid()
    attrs = {"DataType": datatype, "ValueRank": valuerank}
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


def data_var(owner, owner_sym, name, datatype, desc, rule=MR_Optional, valuerank="-1"):
    return _member_var(owner, owner_sym, name, datatype, BaseDataVariableType, rule,
                       HasComponent, desc, valuerank)


def folder_member(owner, owner_sym, name, desc, rule=MR_Mandatory):
    nid = _mid()
    add(nid, "UAObject", name, f"{owner_sym}_{name}", desc=desc, parent=T(owner))
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, FolderType)
    ref(nid, HasComponent, T(owner), forward=False)
    ref(owner, HasComponent, T(nid))
    return nid


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


def _args(method_nid, method_sym, bname, args):
    """Emit an InputArguments / OutputArguments Property for a Method."""
    nid = _mid()
    add(nid, "UAVariable", bname, f"{method_sym}_{bname}", parent=T(method_nid),
        attrs={"DataType": Argument, "ValueRank": "1",
               "ArrayDimensions": str(len(args))})
    ref(nid, HasModellingRule, MR_Mandatory)
    ref(nid, HasTypeDefinition, PropertyType)
    ref(nid, HasProperty, T(method_nid), forward=False)
    ref(method_nid, HasProperty, T(nid))
    parts = ['<Value>',
             '<uax:ListOfExtensionObject xmlns:uax='
             '"http://opcfoundation.org/UA/2008/02/Types.xsd">']
    for arg in args:
        aname, adtype, adesc = arg[0], arg[1], arg[2]
        arank = arg[3] if len(arg) > 3 else -1
        parts.append("<uax:ExtensionObject><uax:TypeId><uax:Identifier>i=297"
                     "</uax:Identifier></uax:TypeId>")
        parts.append("<uax:Body><uax:Argument>")
        parts.append(f"<uax:Name>{sx.escape(aname)}</uax:Name>")
        parts.append(f"<uax:DataType><uax:Identifier>{adtype}</uax:Identifier>"
                     "</uax:DataType>")
        if arank is not None and arank >= 0:
            parts.append(f"<uax:ValueRank>{arank}</uax:ValueRank>"
                         "<uax:ArrayDimensions><uax:UInt32>0</uax:UInt32>"
                         "</uax:ArrayDimensions>")
        else:
            parts.append("<uax:ValueRank>-1</uax:ValueRank>"
                         "<uax:ArrayDimensions/>")
        if adesc:
            parts.append("<uax:Description><uax:Text>"
                         f"{sx.escape(adesc)}</uax:Text></uax:Description>")
        parts.append("</uax:Argument></uax:Body></uax:ExtensionObject>")
    parts.append("</uax:ListOfExtensionObject></Value>")
    NODES[nid].value = "".join(parts)
    return nid


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


def enum_type(nid, name, desc, fields):
    add(nid, "UADataType", name, name, desc=desc, category=CAT_DT)
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
    ref(es, HasModellingRule, MR_Mandatory)
    ref(es, HasTypeDefinition, PropertyType)
    ref(es, HasProperty, T(nid), forward=False)
    vp = ['<Value>',
          '<uax:ListOfLocalizedText xmlns:uax='
          '"http://opcfoundation.org/UA/2008/02/Types.xsd">']
    for (fname, _val, _fdesc) in fields:
        vp.append("<uax:LocalizedText><uax:Text>"
                  f"{sx.escape(fname)}</uax:Text></uax:LocalizedText>")
    vp.append("</uax:ListOfLocalizedText></Value>")
    NODES[es].value = "".join(vp)
    return nid


ABSTRACT_STRUCTS = set()


def struct_type(nid, name, desc, fields, base=Structure, abstract=False):
    """A Structure DataType plus, unless it is abstract, its Default Binary encoding.

    fields: list of (FieldName, DataType, Description[, ValueRank[, ArrayDimensions]])
            ArrayDimensions 0 means "any length" and is omitted from the emitted
            Definition, matching how the base UA NodeSet writes unbounded arrays.
    base:   the DataType this one extends. A subtype's Definition lists only the
            fields it ADDS - the inherited ones are reached through HasSubtype, which
            is how the base UA NodeSet does it.
    abstract: an abstract structure gets no encoding, because nothing is ever encoded
            as one; values are always of a concrete subtype.

    A field whose DataType is an abstract structure declared here is emitted with
    AllowSubTypes="true", so polymorphic members are self-describing rather than
    relying on the reader to notice the DataType is abstract.
    """
    add(nid, "UADataType", name, name, desc=desc, category=CAT_DT, abstract=abstract)
    ref(nid, HasSubtype, base, forward=False)
    if abstract:
        ABSTRACT_STRUCTS.add(T(nid))
    dparts = [f'<Definition Name="{name}">']
    for f in fields:
        fname, fdtype, fdesc = f[0], f[1], f[2]
        frank = f[3] if len(f) > 3 else None
        fdims = f[4] if len(f) > 4 else None
        a = [f'Name="{sx.escape(fname)}"', f'DataType="{fdtype}"']
        if frank is not None:
            a.append(f'ValueRank="{frank}"')
        if fdims:
            a.append(f'ArrayDimensions="{fdims}"')
        if fdtype in ABSTRACT_STRUCTS:
            a.append('AllowSubTypes="true"')
        attr = " ".join(a)
        if fdesc:
            dparts.append(f'<Field {attr}>')
            dparts.append(f'<Description>{sx.escape(fdesc)}</Description></Field>')
        else:
            dparts.append(f'<Field {attr}/>')
    dparts.append("</Definition>")
    NODES[nid].definition = "".join(dparts)
    if abstract:
        return nid
    enc = _next_encoding[0]
    _next_encoding[0] += 1
    ref(nid, HasEncoding, T(enc))
    add(enc, "UAObject", "Default Binary", f"{name}_Encoding_DefaultBinary",
        desc="Default Binary encoding of the structure.",
        attrs={"BrowseNameNamespace": 0, "SymbolicName": "DefaultBinary"})
    ref(enc, HasTypeDefinition, DataTypeEncodingType)
    ref(enc, HasEncoding, T(nid), forward=False)
    return nid


def well_known(nid, name, typedef, parent_nodeid, desc, reftype=HasComponent):
    add(nid, "UAObject", name, name, desc=desc, parent=parent_nodeid)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, parent_nodeid, forward=False)
    return nid



# ===========================================================================
# ==============================  MODEL DEFINITION  =========================
# ===========================================================================
CAT = "AiDeployment"
CAT_DT = "AiDeployment DataTypes"
CAT_RT = "AiDeployment ReferenceTypes"

# ---------------------------------------------------------------------------
# Enumerations (3001+)
# ---------------------------------------------------------------------------
enum_type(3001, "InferenceLocationEnum",
          "Where inference executes. The result contract is identical in every case; "
          "this property exists so a client can reason about latency, availability and "
          "the trust boundary without changing how it reads results.",
          [("OnServer", 0, "In the OPC UA Server process or on its host."),
           ("EdgeOffServer", 1, "On a separate edge node reached over the network."),
           ("Cloud", 2, "In a remote or cloud service."),
           ("InSimulator", 3, "Inside a simulator that also produces the input.")])
InferenceLocationEnum = T(3001)

enum_type(3002, "AcceleratorKindEnum",
          "Compute device executing the model.",
          [("Cpu", 0, None), ("Gpu", 1, None), ("Npu", 2, None), ("Fpga", 3, None),
           ("Tpu", 4, None), ("Other", 5, None)])
AcceleratorKindEnum = T(3002)

enum_type(3003, "DeploymentStateEnum",
          "Runtime lifecycle state of a deployment.",
          [("Inactive", 0, "Declared but not serving."),
           ("Ready", 1, "Able to serve; no work in progress."),
           ("Active", 2, "Serving at least one request."),
           ("Degraded", 3, "Serving below configured quality."),
           ("Faulted", 4, "Unable to serve.")])
DeploymentStateEnum = T(3003)

enum_type(3004, "DatasetSourceEnum",
          "Provenance of the samples in a dataset.",
          [("Real", 0, "Captured from physical equipment."),
           ("Synthetic", 1, "Generated or rendered by a simulator."),
           ("Mixed", 2, "Both, for example synthetic pre-training with real "
                        "fine-tuning.")])
DatasetSourceEnum = T(3004)

enum_type(3005, "LearningJobStateEnum",
          "State of a dataset-capture, retraining and promotion cycle.",
          [("Idle", 0, None), ("Collecting", 1, None), ("Labelling", 2, None),
           ("Training", 3, None), ("Validating", 4, None),
           ("Ready", 5, "A candidate model is available for promotion."),
           ("Promoted", 6, None), ("Failed", 7, None)])
LearningJobStateEnum = T(3005)

# ---------------------------------------------------------------------------
# Structured DataTypes (3050+)
# ---------------------------------------------------------------------------
struct_type(3050, "TensorSignatureDataType",
            "Shape and element type of one model input or output tensor. This is what "
            "lets a client check that what it intends to send matches what the model "
            "expects, before it sends it.",
            [("Name", String, "Tensor name as declared by the model."),
             ("ElementType", String, "Element type, for example float32, uint8 or "
                                     "int64."),
             ("Shape", Int32, "Dimensions; -1 marks a dynamic axis.", 1),
             ("Layout", String, "Optional axis layout hint, for example NCHW or "
                                "NHWC.")])
TensorSignatureDataType = T(3050)

# ---------------------------------------------------------------------------
# ReferenceTypes (4001+)
# ---------------------------------------------------------------------------
reference_type(4001, "UsesModel", "IsUsedByDeployment",
               "Links a Deployment to the Model it executes. Clause 5.5 requires "
               "exactly one such reference per deployment; it is the only defined path "
               "from a result to the model artefact and its Digest, on which the "
               "provenance requirement of clause 7 depends.")
UsesModel = T(4001)

reference_type(4002, "TrainedOn", "IsTrainingDataFor",
               "Links a Model to a Dataset it was trained or validated on. A model "
               "whose training data cannot be named is a model whose behaviour cannot "
               "be explained, which is why this reference exists rather than a string.")
TrainedOn = T(4002)

# ---------------------------------------------------------------------------
# ObjectTypes (1001+)
# ---------------------------------------------------------------------------
object_type(1001, "AiRootType", BaseObjectType,
            "Server-level entry point. A client that has just connected browses here to "
            "find every model, dataset, deployment and learning job the Server "
            "describes, without knowing its layout.")
RT_ = 1001
folder_member(RT_, "AiRootType", "Models", "ModelType instances.")
folder_member(RT_, "AiRootType", "Datasets", "DatasetType instances.", MR_Optional)
folder_member(RT_, "AiRootType", "Deployments", "DeploymentType instances.")
folder_member(RT_, "AiRootType", "LearningJobs", "LearningJobType instances.",
              MR_Optional)
prop_var(RT_, "AiRootType", "SpecificationVersion", String,
         "Release of this specification the Server implements, for example '0.1.0'.",
         MR_Mandatory)

object_type(1002, "ModelType", BaseObjectType,
            "Nameplate of a trained model. The member set is deliberately aligned with "
            "the IDTA 02060 AI Model Nameplate submodel template, which is currently the "
            "only standardised description of an industrial AI model, so an Asset "
            "Administration Shell can be populated from this node without loss.")
AM = 1002
prop_var(AM, "ModelType", "ModelId", String, "Identifier of the model.", MR_Mandatory)
prop_var(AM, "ModelType", "Name", LocalizedText, "Human-readable model name.",
         MR_Mandatory)
prop_var(AM, "ModelType", "Version", String, "Model version.", MR_Mandatory)
prop_var(AM, "ModelType", "Framework", String,
         "Producing framework, for example PyTorch, TensorFlow or scikit-learn.")
prop_var(AM, "ModelType", "Format", String,
         "Serialization format, for example ONNX, TensorRT or OpenVINO IR.")
prop_var(AM, "ModelType", "TaskKind", String,
         "What the model does, for example Detection2D, Classification, Segmentation, "
         "Forecasting or AnomalyDetection. Free text because the set of tasks is not "
         "closed and a closed enumeration would date faster than the model does.")
prop_var(AM, "ModelType", "Digest", ByteString,
         "Cryptographic digest of the model artefact, for provenance and integrity. "
         "Mandatory: clause 7 requires it for every model whose artefact is obtainable "
         "through ArtifactUri, and it is the terminus of the provenance chain that "
         "UsesModel keeps intact.",
         MR_Mandatory)
prop_var(AM, "ModelType", "DigestAlgorithm", String,
         "Hash function used for Digest. SHALL name a function with at least 256-bit "
         "output and no known collision weakness; SHA-256 is the default and is always "
         "acceptable. SHALL NOT be MD5, SHA-1 or a truncated variant - chosen-prefix "
         "collisions against those are practical, so a substituted artefact would pass "
         "verification. SHALL be non-empty where Digest is non-empty. See clause 7.",
         MR_Mandatory)
prop_var(AM, "ModelType", "ArtifactUri", String,
         "Where the model artefact can be obtained. Treated as untrusted input.")
prop_var(AM, "ModelType", "ProvenanceUri", String,
         "Training provenance or model card location.")
prop_var(AM, "ModelType", "LabelClasses", String,
         "Ordered class label set, where the model produces classified output. The "
         "INDEX is what a consuming specification's class identifier refers to, so the "
         "order is part of the contract and a Server SHALL NOT reorder it in place.",
         MR_Optional, valuerank="1")
data_var(AM, "ModelType", "Inputs", TensorSignatureDataType,
         "Input tensor signatures.", MR_Optional, valuerank="1")
data_var(AM, "ModelType", "Outputs", TensorSignatureDataType,
         "Output tensor signatures.", MR_Optional, valuerank="1")

object_type(1003, "DatasetType", BaseObjectType,
            "A dataset used to train or validate a model. Aligned with the IDTA 02058 AI "
            "Dataset submodel template. SourceKind distinguishes real capture from "
            "simulator output, which is the provenance a reviewer needs when synthetic "
            "data is involved.")
AD = 1003
prop_var(AD, "DatasetType", "DatasetId", String, "Identifier of the dataset.",
         MR_Mandatory)
prop_var(AD, "DatasetType", "Name", LocalizedText, "Human-readable dataset name.")
prop_var(AD, "DatasetType", "Version", String, "Dataset version.")
prop_var(AD, "DatasetType", "SourceKind", DatasetSourceEnum,
         "Whether samples are real, synthetic or mixed.", MR_Mandatory)
prop_var(AD, "DatasetType", "SampleCount", UInt64, "Number of samples.")
prop_var(AD, "DatasetType", "LabelClasses", String, "Class labels present.",
         MR_Optional, valuerank="1")
prop_var(AD, "DatasetType", "CreatedAt", UtcTime, "Creation time.")
prop_var(AD, "DatasetType", "ArtifactUri", String,
         "Where the dataset can be obtained. Treated as untrusted input.")
prop_var(AD, "DatasetType", "Digest", ByteString, "Digest of the dataset artefact.")

object_type(1004, "DeploymentType", BaseObjectType,
            "A model made executable somewhere. Aligned with the IDTA 02059 AI "
            "Deployment submodel template. InferenceLocation is the on-server versus "
            "off-server switch: it changes where the computation happens and therefore "
            "the trust boundary, and it changes nothing else.")
AY = 1004
prop_var(AY, "DeploymentType", "DeploymentId", String,
         "Identifier of the deployment.", MR_Mandatory)
prop_var(AY, "DeploymentType", "InferenceLocation", InferenceLocationEnum,
         "Where inference executes.", MR_Mandatory)
prop_var(AY, "DeploymentType", "AcceleratorKind", AcceleratorKindEnum,
         "Compute device executing the model.")
prop_var(AY, "DeploymentType", "AcceleratorName", String,
         "Free-text accelerator identification, for example an NPU or GPU part name.")
prop_var(AY, "DeploymentType", "EndpointUri", String,
         "Inference endpoint when InferenceLocation is not OnServer. Treated as "
         "untrusted input and subject to the resolver policy of clause 7.")
prop_var(AY, "DeploymentType", "LatencyBudget", Duration,
         "Latency the deployment is expected to meet, so a client can detect "
         "regression.")
prop_var(AY, "DeploymentType", "BatchSize", UInt32,
         "Configured inference batch size.")
prop_var(AY, "DeploymentType", "State", DeploymentStateEnum,
         "Runtime state of the deployment.", MR_Mandatory)

object_type(1005, "LearningJobType", BaseObjectType,
            "One turn of the capture, label, train and promote loop. It exists so that "
            "corrections arriving from a consuming application have somewhere to "
            "accumulate and a defined path into a new model version. A Server may "
            "implement only the capture stages and leave training to an external MLOps "
            "system - the state machine is the same either way.")
LJ = 1005
prop_var(LJ, "LearningJobType", "JobId", String, "Identifier of the job.", MR_Mandatory)
prop_var(LJ, "LearningJobType", "State", LearningJobStateEnum,
         "Current stage of the loop.", MR_Mandatory)
prop_var(LJ, "LearningJobType", "Dataset", NodeId_,
         "Dataset being accumulated or used.")
prop_var(LJ, "LearningJobType", "BaseModel", NodeId_, "Model the job starts from.")
prop_var(LJ, "LearningJobType", "CandidateModel", NodeId_,
         "Model produced by the job, awaiting promotion.")
prop_var(LJ, "LearningJobType", "SamplesCollected", UInt64,
         "Samples accumulated so far, including corrections fed back.")
prop_var(LJ, "LearningJobType", "LastError", LocalizedText,
         "Diagnostic for the Failed state.")
method(LJ, "LearningJobType", "StartCollection",
       "Begin accumulating samples and corrections into the dataset.", MR_Optional)
method(LJ, "LearningJobType", "StopCollection",
       "Stop accumulating samples.", MR_Optional)
method(LJ, "LearningJobType", "TriggerTraining",
       "Request that a candidate model be trained from the collected dataset.",
       MR_Optional,
       outargs=[("Accepted", Boolean, "True when the request was queued.")])
method(LJ, "LearningJobType", "PromoteModel",
       "Promote the candidate model so that deployments begin using it. A Server SHALL "
       "require a distinct authorization for this Method: it changes what the equipment "
       "does without changing anything a reader of the address space would notice, "
       "which is precisely the change that needs a separate permission.",
       MR_Optional,
       inargs=[("Deployment", NodeId_, "Deployment to update, or null for all.")],
       outargs=[("PromotedModel", NodeId_, "The model now in use.")])

# ---------------------------------------------------------------------------
# Well-known instance (7001+)
# ---------------------------------------------------------------------------
well_known(7001, "AiDeployment", T(1001), Server,
           "Entry point for AI deployment and learning on this Server. A client browses "
           "Server/AiDeployment/Models to find what this Server describes.")


# ===========================================================================
# ==================================  EMIT  =================================
# ===========================================================================
_PRIO = {HasModellingRule: 0, HasSubtype: 0, HasTypeDefinition: 1}


def _sorted_refs(refs):
    return sorted(range(len(refs)), key=lambda i: (_PRIO.get(refs[i][0], 2), i))


def _fmt_reftype(t):
    return REFTYPE_ALIAS.get(t, t)


def _emit_node(n):
    tag = n.cls
    # A DataTypeEncoding browses as "Default Binary" in namespace 0: the BrowseName is
    # standard, not model-defined. Emitting it as 1:Default Binary is what every real
    # companion NodeSet avoids, and tooling that resolves encodings by BrowseName
    # cannot find it.
    prefix = "" if n.attrs.get("BrowseNameNamespace") == 0 else "1:"
    a = [f'{tag} NodeId="{T(n.nid)}"', f'BrowseName="{prefix}{sx.escape(n.bname)}"']
    if "SymbolicName" in n.attrs:
        a.append(f'SymbolicName="{sx.escape(n.attrs["SymbolicName"])}"')
    if n.parent is not None:
        a.append(f'ParentNodeId="{n.parent}"')
    for k in ("DataType", "ValueRank", "ArrayDimensions"):
        if k in n.attrs:
            v = n.attrs[k]
            if k == "DataType":
                v = DATATYPE_ALIAS.get(v, v)
            a.append(f'{k}="{v}"')
    if n.cls in ("UAObjectType", "UADataType") and n.abstract:
        a.append('IsAbstract="true"')
    lines = ["  <" + " ".join(a) + ">"]
    lines.append(f"    <DisplayName>{sx.escape(n.display)}</DisplayName>")
    if n.desc:
        lines.append(f"    <Description>{sx.escape(n.desc)}</Description>")
    if n.category:
        lines.append(f"    <Category>{sx.escape(n.category)}</Category>")
    if n.cls == "UAReferenceType" and n.inverse:
        lines.append(f"    <InverseName>{sx.escape(n.inverse)}</InverseName>")
    lines.append("    <References>")
    for i in _sorted_refs(n.refs):
        rt, tgt, fwd = n.refs[i]
        fwd_s = "" if fwd else ' IsForward="false"'
        lines.append(f'      <Reference ReferenceType="{_fmt_reftype(rt)}"{fwd_s}>'
                     f'{tgt}</Reference>')
    lines.append("    </References>")
    if n.definition:
        lines.append("    " + n.definition)
    if n.value:
        lines.append("    " + n.value)
    lines.append(f"  </{tag}>")
    return "\n".join(lines)


def emit():
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<!-- OPC UA - AI Deployment and Learning companion model. PROVISIONAL NodeIds and namespace '
           '(final IDs assigned by the OPC Foundation / working group). -->',
           '<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
           'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" '
           'xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
           '  <NamespaceUris>',
           f'    <Uri>{NAMESPACE}</Uri>',
           '  </NamespaceUris>',
           '  <Models>',
           f'    <Model ModelUri="{NAMESPACE}" Version="{VERSION}" '
           f'PublicationDate="{PUBDATE}">',
           f'      <RequiredModel ModelUri="http://opcfoundation.org/UA/" '
           f'Version="{BASE_UA_VERSION}" PublicationDate="{BASE_UA_PUBDATE}" />',
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
    # OPC Foundation NodeIds.csv format: SymbolicName,NodeId,NodeClass
    return "\n".join(f"{NODES[nid].symbolic},{nid},{NODES[nid].cls[2:]}"
                     for nid in ORDER) + "\n"


def _rule_name(nid):
    for rt, tgt, fwd in NODES[nid].refs:
        if rt == HasModellingRule:
            return {MR_Mandatory: "Mandatory", MR_Optional: "Optional",
                    MR_OptionalPlaceholder: "OptionalPlaceholder",
                    MR_MandatoryPlaceholder: "MandatoryPlaceholder"}.get(tgt, "")
    return ""


def _supertype(nid):
    for rt, tgt, fwd in NODES[nid].refs:
        if rt == HasSubtype and not fwd:
            return tgt
    return ""


BASE_TYPE_NAMES = {
    "i=22": "Structure", "i=29": "Enumeration", "i=58": "BaseObjectType",
    "i=61": "FolderType", "i=68": "PropertyType", "i=63": "BaseDataVariableType",
    "i=17602": "BaseInterfaceType", "i=32": "NonHierarchicalReferences",
    "i=76": "DataTypeEncodingType", "i=24": "BaseDataType",
    "i=2391": "ProgramStateMachineType",
}


def _dt_name(dt):
    """Render a DataType or supertype NodeId as a readable name."""
    if not dt:
        return ""
    if dt in BASE_TYPE_NAMES:
        return BASE_TYPE_NAMES[dt]
    if dt in DATATYPE_ALIAS:
        return DATATYPE_ALIAS[dt]
    if dt.startswith("ns=1;i="):
        n = NODES.get(int(dt.split("=")[-1]))
        if n is not None:
            return n.bname
    return dt


def _rank(vr):
    return {"-1": "Scalar", "1": "Array"}.get(str(vr), str(vr))


def _members_of(nid):
    """Instance declarations owned by a type, in declaration order."""
    out = []
    for m in ORDER:
        n = NODES[m]
        if n.parent == T(nid) and n.cls in ("UAVariable", "UAObject", "UAMethod"):
            out.append(m)
    return out


def _method_args(nid, which):
    for m in _members_of(nid):
        n = NODES[m]
        if n.bname == which and n.value:
            names = re.findall(r"<uax:Name>([^<]*)</uax:Name>", n.value)
            types = re.findall(r"<uax:Identifier>([^<]*)</uax:Identifier>", n.value)
            types = [t for t in types if t != "i=297"]
            descs = re.findall(r"<uax:Text>([^<]*)</uax:Text>", n.value)
            ranks = re.findall(r"<uax:ValueRank>(-?\d+)</uax:ValueRank>", n.value)
            out = []
            for i, nm in enumerate(names):
                out.append((nm,
                            _dt_name(types[i]) if i < len(types) else "",
                            "Array" if i < len(ranks) and ranks[i] != "-1" else "Scalar",
                            descs[i] if i < len(descs) else ""))
            return out
    return []


def _esc(s):
    return (s or "").replace("|", "\\|")


def emit_md():
    """Annex A. This is the authoritative node reference, so it must carry everything an
    implementer needs: DataType, ValueRank and ModellingRule for every member, the field
    list of every structure, the value of every enumeration literal, and the full
    signature of every Method. A bare NodeId/BrowseName table is not sufficient."""
    obj_types = [n for n in ORDER if NODES[n].cls == "UAObjectType"]
    data_types = [n for n in ORDER if NODES[n].cls == "UADataType"]
    ref_types = [n for n in ORDER if NODES[n].cls == "UAReferenceType"]

    L = ["# OPC UA — AI Deployment and Learning — Annex A: Information model (generated)",
         "",
         "> Generated by `build_model.py`. Do not edit by hand. Namespace "
         f"`{NAMESPACE}` (index 1). NodeIds are provisional.",
         "",
         "This annex is the authoritative node reference for the specification: it "
         "carries the DataType, ValueRank and ModellingRule of every member, the field "
         "list of every structure, the value of every enumeration literal, and the full "
         "signature of every Method.",
         ""]

    L += ["## A.1 Type overview", "",
          "| NodeId | BrowseName | NodeClass | Subtype of |", "|---|---|---|---|"]
    for nid in ref_types + obj_types + data_types:
        n = NODES[nid]
        L.append(f"| ns=1;i={nid} | {n.bname} | {n.cls[2:]} | "
                 f"{_dt_name(_supertype(nid))} |")
    L.append("")

    L += ["## A.2 ReferenceTypes", "",
          "| NodeId | BrowseName | InverseName | Subtype of | Description |",
          "|---|---|---|---|---|"]
    for nid in ref_types:
        n = NODES[nid]
        L.append(f"| ns=1;i={nid} | {n.bname} | {n.inverse} | "
                 f"{_dt_name(_supertype(nid))} | {_esc(n.desc)} |")
    L.append("")

    L += ["## A.3 ObjectTypes", ""]
    for nid in obj_types:
        n = NODES[nid]
        abstract = " (abstract)" if n.abstract else ""
        L.append(f"### {n.bname}{abstract} — `ns=1;i={nid}`")
        L.append("")
        L.append(f"*Subtype of:* `{_dt_name(_supertype(nid))}`")
        L.append("")
        if n.desc:
            L.append(_esc(n.desc))
            L.append("")
        members = _members_of(nid)
        variables = [m for m in members if NODES[m].cls in ("UAVariable", "UAObject")]
        methods = [m for m in members if NODES[m].cls == "UAMethod"]
        if variables:
            L.append("| BrowseName | NodeClass | DataType | ValueRank | ModellingRule "
                     "| Description |")
            L.append("|---|---|---|---|---|---|")
            for m in variables:
                mn = NODES[m]
                dt = _dt_name(mn.attrs.get("DataType", ""))
                vr = _rank(mn.attrs.get("ValueRank", "-1")) if mn.cls == "UAVariable" else ""
                L.append(f"| {mn.bname} | {mn.cls[2:]} | {dt} | {vr} | "
                         f"{_rule_name(m)} | {_esc(mn.desc)} |")
            L.append("")
        for m in methods:
            mn = NODES[m]
            L.append(f"**Method `{mn.bname}`** ({_rule_name(m)}) — {_esc(mn.desc)}")
            L.append("")
            for which, label in (("InputArguments", "In"),
                                 ("OutputArguments", "Out")):
                args = _method_args(m, which)
                if not args:
                    continue
                L.append(f"| {label} | DataType | ValueRank | Meaning |")
                L.append("|---|---|---|---|")
                for (an, at, ar, ad) in args:
                    L.append(f"| {an} | {at} | {ar} | {_esc(ad)} |")
                L.append("")
            if not _method_args(m, "InputArguments") and \
                    not _method_args(m, "OutputArguments"):
                L.append("Takes no arguments and returns none.")
                L.append("")

    L += ["## A.4 DataTypes", ""]
    for nid in data_types:
        n = NODES[nid]
        defn = n.definition or ""
        is_enum = 'Value="' in defn
        L.append(f"### {n.bname} — `ns=1;i={nid}`")
        L.append("")
        L.append(f"*Subtype of:* `{_dt_name(_supertype(nid))}`")
        L.append("")
        if n.desc:
            L.append(_esc(n.desc))
            L.append("")
        if is_enum:
            L.append("| Name | Value | Description |")
            L.append("|---|---|---|")
            for mm in re.finditer(
                    r'<Field Name="([^"]+)" Value="(\d+)"\s*(?:/>|>'
                    r'(?:<Description>([^<]*)</Description>)?</Field>)', defn):
                L.append(f"| {mm.group(1)} | {mm.group(2)} | "
                         f"{_esc(mm.group(3) or '')} |")
        else:
            L.append("| Field | DataType | ValueRank | ArrayDimensions | Description |")
            L.append("|---|---|---|---|---|")
            for mm in re.finditer(
                    r'<Field Name="([^"]+)" DataType="([^"]+)"([^>]*?)(?:/>|>'
                    r'(?:<Description>([^<]*)</Description>)?</Field>)', defn):
                extra = mm.group(3) or ""
                vr = re.search(r'ValueRank="(-?\d+)"', extra)
                ad = re.search(r'ArrayDimensions="(\d+)"', extra)
                L.append(f"| {mm.group(1)} | {_dt_name(mm.group(2))} | "
                         f"{_rank(vr.group(1)) if vr else 'Scalar'} | "
                         f"{ad.group(1) if ad else ''} | "
                         f"{_esc(mm.group(4) or '')} |")
        L.append("")

    return "\n".join(L).rstrip() + "\n"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    std = os.path.normpath(os.path.join(here, "..", "..", "..", "ai-deployment"))
    os.makedirs(std, exist_ok=True)
    with open(os.path.join(std, "Opc.Ua.AiDeployment.NodeSet2.xml"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit())
    with open(os.path.join(std, "Opc.Ua.AiDeployment.NodeIds.csv"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit_csv())
    with open(os.path.join(here, "model-reference.md"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(emit_md())
    n_types = sum(1 for k in NODES
                  if NODES[k].cls in ("UAObjectType", "UADataType", "UAReferenceType"))
    print(f"Wrote NodeSet ({len(ORDER)} nodes, {n_types} types), NodeIds.csv, "
          "model-reference.md")
    print(f"Member id range: 6001..{_next_member[0] - 1}")


if __name__ == "__main__":
    main()
