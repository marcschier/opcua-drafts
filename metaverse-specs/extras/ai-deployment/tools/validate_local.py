#!/usr/bin/env python3
"""
Local structural + modelling-rule validator for the OPC UA - AI Deployment and Learning NodeSet.

Reproducible in-repo gate (mirrors the vision and openusd-binding validate_local.py
convention). Everything is re-derived from the committed artifacts with the standard
library alone; nothing here imports the generator, because a checker that asks the
emitter what it emitted validates nothing.

Structural checks, against Opc.Ua.AiDeployment.NodeSet2.xml:
  * XML well-formedness and a single <Model> whose ONLY <RequiredModel> is the base UA
    namespace - this model is deliberately standalone.
  * Unique NodeIds; every reference target resolves (own ns=1 node or a base-UA id).
  * Every UAObjectType/UADataType/UAReferenceType has an inverse HasSubtype to a base.
  * Every UAReferenceType carries an InverseName.
  * Every instance-declaration member has a HasTypeDefinition (Objects/Variables) and a
    HasModellingRule, unless it is the concrete well-known object under the Server.
  * ParentNodeId is backed by an inverse hierarchical reference, and forward/inverse
    hierarchical pairs are consistent.
  * Enum EnumStrings ArrayDimensions equals the number of enum fields.
  * A CONCRETE Structure has a Definition and a HasEncoding to a resolvable Default
    Binary encoding Object; an ABSTRACT Structure has a Definition and NO encoding,
    because nothing is ever encoded as an abstract type.
  * Every Definition Field DataType resolves, and any field typed by an abstract
    structure declared here carries AllowSubTypes="true" - polymorphic members must be
    self-describing rather than leaving a reader to notice the DataType is abstract.
  * Every Method's InputArguments/OutputArguments ArrayDimensions matches the number of
    encoded Argument entries.
  * Opc.Ua.AiDeployment.NodeIds.csv and the NodeSet agree exactly - same id set in both
    directions, same NodeClass, and the CSV name resolves to the NodeSet BrowseName.

Specification invariants (the reason this file is not generic):
  * ModelType.Digest and DigestAlgorithm MUST be Mandatory. The provenance chain from a
    published result back to the model artefact is the only reason several of the other
    members are worth reading, and an Optional digest breaks it silently.
  * DeploymentType.InferenceLocation and State MUST be Mandatory: a deployment whose
    location is unknown cannot be reasoned about, and clause 6 depends on the state.
  * LearningJobStateEnum MUST carry exactly the eight states clause 6 tabulates.
  * DatasetSourceEnum MUST number Real 0, Synthetic 1, Mixed 2.
  * InferenceLocationEnum MUST number OnServer 0 - the on-server case is the default a
    Server that says nothing else is describing.
  * UsesModel MUST exist as a ReferenceType: it is the only defined path from a
    deployment to the artefact its results depend on.
  * NOTHING in this model may name a sensor, a camera, an image or a robot. This model
    was factored out of a vision specification precisely so that it does not; a check
    that fails loudly is what keeps it that way.

Specification/model cross-checks, in BOTH directions:
  * Every ObjectType, DataType and ReferenceType the model declares is named in
    OPC-UA-AI-Deployment.md, and every enumeration literal it declares appears there.
  * Every `ns=1;i=<n>` the specification cites exists in the NodeSet.

Exit code 0 and "OK" on success; non-zero with an ERRORS list otherwise.
"""
from __future__ import annotations
import csv
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
STD = os.path.normpath(os.path.join(HERE, "..", "..", "..", "ai-deployment"))
NODESET = os.path.join(STD, "Opc.Ua.AiDeployment.NodeSet2.xml")
CSVFILE = os.path.join(STD, "Opc.Ua.AiDeployment.NodeIds.csv")
SPEC = os.path.join(STD, "OPC-UA-AI-Deployment.md")

NS = {"u": "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"}
UAX = {"uax": "http://opcfoundation.org/UA/2008/02/Types.xsd"}
UA_NAMESPACE = "http://opcfoundation.org/UA/"
NAMESPACE = "http://opcfoundation.org/UA/AI/"
XREG_NS = "http://opcfoundation.org/UA/xRegistry/"
PROGRAM_STATE_MACHINE = "i=2391"


# Reference types that make a node a child of its ParentNodeId.
HIERARCHICAL = {"HasComponent", "HasProperty", "Organizes", "HasSubtype",
                "i=47", "i=46", "i=35", "i=45"}
ALIAS_OF = {"HasComponent": "i=47", "HasProperty": "i=46", "Organizes": "i=35",
            "HasSubtype": "i=45", "HasTypeDefinition": "i=40",
            "HasModellingRule": "i=37", "HasEncoding": "i=38",
            "HasInterface": "i=17603"}

ERRORS: list[str] = []


def err(msg: str) -> None:
    ERRORS.append(msg)


def canon(ref: str) -> str:
    return ALIAS_OF.get(ref, ref)


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class Model:
    """The NodeSet, re-read from XML with no help from the generator."""

    def __init__(self, path: str):
        self.tree = ET.parse(path)
        self.root = self.tree.getroot()
        self.nodes: dict[str, ET.Element] = {}
        self.order: list[str] = []
        self.aliases: dict[str, str] = {}
        for a in self.root.findall("u:Aliases/u:Alias", NS):
            self.aliases[a.get("Alias", "")] = (a.text or "").strip()
        for el in self.root:
            t = local(el.tag)
            if not t.startswith("UA") or t in ("UANodeSet",):
                continue
            nid = el.get("NodeId", "")
            if not nid:
                continue
            if nid in self.nodes:
                err(f"duplicate NodeId {nid}")
            self.nodes[nid] = el
            self.order.append(nid)

    def cls(self, nid: str) -> str:
        return local(self.nodes[nid].tag)

    def bname(self, nid: str) -> str:
        return (self.nodes[nid].get("BrowseName", "").split(":", 1)[-1])

    def refs(self, nid: str):
        out = []
        for r in self.nodes[nid].findall("u:References/u:Reference", NS):
            out.append((canon(r.get("ReferenceType", "")),
                        (r.text or "").strip(),
                        r.get("IsForward", "true") != "false"))
        return out

    def supertype(self, nid: str) -> str:
        for rt, tgt, fwd in self.refs(nid):
            if rt == "i=45" and not fwd:
                return tgt
        return ""

    @property
    def own(self) -> str:
        """NodeId prefix of this model's OWN namespace.

        Derived from NamespaceUris, never assumed: a RequiredModel puts its namespace
        in that list too, so the own index moves when a dependency is added. A
        validator that assumed ns=1 would resolve nothing and report success.
        """
        uris = [(u.text or "").strip()
                for u in self.root.findall("u:NamespaceUris/u:Uri", NS)]
        return "ns=%d;" % (uris.index(NAMESPACE) + 1) if NAMESPACE in uris else "ns=1;"

    @property
    def xreg(self) -> str:
        """NodeId prefix of the xRegistry namespace this model extends."""
        uris = [(u.text or "").strip()
                for u in self.root.findall("u:NamespaceUris/u:Uri", NS)]
        return "ns=%d;" % (uris.index(XREG_NS) + 1) if XREG_NS in uris else ""

    def resolves(self, target: str) -> bool:
        """Own-namespace targets must exist here; imported ids are taken on trust."""
        if target in self.nodes:
            return True
        if self.xreg and target.startswith(self.xreg):
            # Declared by the xRegistry model, which this one requires. Resolving it
            # would mean parsing that NodeSet; the RequiredModel is the contract.
            return True
        if target.startswith(self.own):
            return False
        return bool(re.fullmatch(r"i=\d+", target)) or target in self.aliases

    def definition(self, nid: str):
        for child in self.nodes[nid]:
            if local(child.tag) == "Definition":
                return child
        return None

    def members_of(self, nid: str) -> list[str]:
        want = (nid if nid.startswith(self.own)
                else f"{self.own}i={nid.split('=')[-1]}")
        return [m for m in self.order if self.nodes[m].get("ParentNodeId") == want]

    def member_named(self, owner: str, name: str) -> str:
        for m in self.members_of(owner):
            if self.bname(m) == name:
                return m
        return ""

    def modelling_rule(self, nid: str) -> str:
        for rt, tgt, fwd in self.refs(nid):
            if rt == "i=37":
                return {"i=78": "Mandatory", "i=80": "Optional",
                        "i=11508": "OptionalPlaceholder",
                        "i=11510": "MandatoryPlaceholder"}.get(tgt, tgt)
        return ""

    def enum_fields(self, nid: str) -> list[tuple[str, int]]:
        d = self.definition(nid)
        if d is None:
            return []
        out = []
        for f in d:
            if local(f.tag) == "Field":
                try:
                    out.append((f.get("Name", ""), int(f.get("Value", "0"))))
                except ValueError:
                    err(f"enum {self.bname(nid)} field {f.get('Name')} has a "
                        "non-integer Value")
        return out

    def struct_fields(self, nid: str) -> list[ET.Element]:
        d = self.definition(nid)
        return [] if d is None else [f for f in d if local(f.tag) == "Field"]

    def by_name(self, name: str) -> str:
        for nid in self.order:
            if self.bname(nid) == name:
                return nid
        return ""


def check_model_header(m: Model) -> None:
    models = m.root.findall("u:Models/u:Model", NS)
    if len(models) != 1:
        err(f"expected exactly one <Model>, found {len(models)}")
        return
    req = models[0].findall("u:RequiredModel", NS)
    uris = [r.get("ModelUri") for r in req]
    if uris != [UA_NAMESPACE, XREG_NS]:
        err("RequiredModel must be exactly the base UA namespace and "
            f"{XREG_NS}, in that order, found {uris}")
    uris_declared = [(u.text or "").strip()
                     for u in m.root.findall("u:NamespaceUris/u:Uri", NS)]
    # Order is load-bearing: it fixes every namespace index in the file. Required
    # namespaces first, own namespace last, matching the Schema Registry precedent.
    if uris_declared != [XREG_NS, NAMESPACE]:
        err(f"NamespaceUris must be exactly [{XREG_NS}, {NAMESPACE}] in that order, "
            f"found {uris_declared}")
    elif uris_declared[-1] != models[0].get("ModelUri"):
        err("the last NamespaceUris entry and Model ModelUri must be this model")


def check_references(m: Model) -> None:
    for nid in m.order:
        for rt, tgt, fwd in m.refs(nid):
            if not m.resolves(tgt):
                err(f"{m.bname(nid)} ({nid}) references unresolvable target {tgt}")
            if not m.resolves(rt):
                err(f"{m.bname(nid)} ({nid}) uses unresolvable ReferenceType {rt}")


def check_types(m: Model) -> None:
    for nid in m.order:
        c = m.cls(nid)
        if c in ("UAObjectType", "UADataType", "UAReferenceType", "UAVariableType"):
            if not m.supertype(nid):
                err(f"{c} {m.bname(nid)} ({nid}) has no inverse HasSubtype")
        if c == "UAReferenceType":
            inv = m.nodes[nid].find("u:InverseName", NS)
            if inv is None or not (inv.text or "").strip():
                err(f"ReferenceType {m.bname(nid)} ({nid}) has no InverseName")


def check_instance_declarations(m: Model) -> None:
    for nid in m.order:
        el = m.nodes[nid]
        parent = el.get("ParentNodeId")
        if not parent:
            continue
        c = m.cls(nid)
        if c in ("UAObject", "UAVariable"):
            if not any(rt == "i=40" for rt, _, _ in m.refs(nid)):
                err(f"{m.bname(nid)} ({nid}) has no HasTypeDefinition")
        external_root = parent not in m.nodes
        if not external_root and not m.modelling_rule(nid):
            # A node parented on a base-UA node (the well-known object under the
            # Server) is a concrete instance, not an instance declaration, so it
            # carries no ModellingRule.
            err(f"{m.bname(nid)} ({nid}) has no HasModellingRule")
        backed = any(canon(rt) in HIERARCHICAL and not fwd and tgt == parent
                     for rt, tgt, fwd in m.refs(nid))
        if not backed:
            err(f"{m.bname(nid)} ({nid}) ParentNodeId {parent} is not backed by an "
                "inverse hierarchical reference")
        # the forward half must exist on the parent
        if parent in m.nodes:
            fwd_ok = any(canon(rt) in HIERARCHICAL and fwd and tgt == nid
                         for rt, tgt, fwd in m.refs(parent))
            if not fwd_ok:
                err(f"parent {m.bname(parent)} ({parent}) has no forward hierarchical "
                    f"reference to {m.bname(nid)} ({nid})")


def check_datatypes(m: Model) -> None:
    abstract_structs = {
        nid for nid in m.order
        if m.cls(nid) == "UADataType"
        and m.nodes[nid].get("IsAbstract") == "true"
    }
    for nid in m.order:
        if m.cls(nid) != "UADataType":
            continue
        name = m.bname(nid)
        d = m.definition(nid)
        if d is None:
            err(f"DataType {name} ({nid}) has no Definition")
            continue
        sup = m.supertype(nid)
        is_enum = sup == "i=29"
        encodings = [tgt for rt, tgt, fwd in m.refs(nid) if rt == "i=38" and fwd]
        if is_enum:
            fields = m.enum_fields(nid)
            es = m.by_name("EnumStrings")
            # EnumStrings is a property of THIS enum, found by parent
            es = ""
            for mm in m.members_of(nid):
                if m.bname(mm) == "EnumStrings":
                    es = mm
            if not es:
                err(f"enum {name} ({nid}) has no EnumStrings property")
            else:
                dims = m.nodes[es].get("ArrayDimensions", "")
                if dims != str(len(fields)):
                    err(f"enum {name} EnumStrings ArrayDimensions {dims!r} does not "
                        f"match its {len(fields)} fields")
            if len({v for _, v in fields}) != len(fields):
                err(f"enum {name} has duplicate field values")
        else:
            if nid in abstract_structs:
                if encodings:
                    err(f"abstract DataType {name} ({nid}) must have no encoding, "
                        f"found {encodings}")
            else:
                if len(encodings) != 1:
                    err(f"concrete Structure {name} ({nid}) must have exactly one "
                        f"HasEncoding, found {encodings}")
                elif encodings[0] not in m.nodes:
                    err(f"Structure {name} encoding {encodings[0]} does not resolve")
            for f in m.struct_fields(nid):
                fdt = f.get("DataType", "")
                if not m.resolves(fdt):
                    err(f"Structure {name} field {f.get('Name')} has unresolvable "
                        f"DataType {fdt}")
                if fdt in abstract_structs and f.get("AllowSubTypes") != "true":
                    err(f"Structure {name} field {f.get('Name')} is typed by the "
                        f"abstract {m.bname(fdt)} and must carry "
                        'AllowSubTypes="true"')


def check_method_arguments(m: Model) -> None:
    for nid in m.order:
        if m.cls(nid) != "UAMethod":
            continue
        for which in ("InputArguments", "OutputArguments"):
            arg = ""
            for mm in m.members_of(nid):
                if m.bname(mm) == which:
                    arg = mm
            if not arg:
                continue
            el = m.nodes[arg]
            count = len(el.findall(".//uax:Argument", UAX))
            dims = el.get("ArrayDimensions", "")
            if dims != str(count):
                err(f"{m.bname(nid)}.{which} ArrayDimensions {dims!r} does not match "
                    f"its {count} encoded Argument entries")
            if el.get("ValueRank") != "1":
                err(f"{m.bname(nid)}.{which} must have ValueRank 1")


def check_csv(m: Model) -> None:
    if not os.path.exists(CSVFILE):
        err(f"missing {CSVFILE}")
        return
    rows = []
    with open(CSVFILE, newline="", encoding="utf-8") as fh:
        for row in csv.reader(fh):
            if row and row[0].strip():
                rows.append(row)
    csv_ids = {}
    for row in rows:
        if len(row) != 3:
            err(f"NodeIds.csv row is not 3 columns: {row}")
            continue
        name, sid, cls = row[0].strip(), row[1].strip(), row[2].strip()
        if sid in csv_ids:
            err(f"NodeIds.csv has duplicate id {sid}")
        csv_ids[sid] = (name, cls)
    ns_ids = {nid.split("=")[-1]: nid for nid in m.order}
    for sid, (name, cls) in csv_ids.items():
        nid = ns_ids.get(sid)
        if nid is None:
            err(f"NodeIds.csv lists {name} ({sid}) which is not in the NodeSet")
            continue
        if m.cls(nid)[2:] != cls:
            err(f"NodeIds.csv says {name} ({sid}) is {cls}; NodeSet says "
                f"{m.cls(nid)[2:]}")
        bn = m.bname(nid)
        # Members are qualified Owner_Member in the CSV, and a structure's encoding
        # object browses as "Default Binary" but is published as Type_Encoding_...
        if name.endswith("_Encoding_DefaultBinary"):
            owner = name[: -len("_Encoding_DefaultBinary")]
            if bn != "Default Binary":
                err(f"NodeIds.csv {name!r} ({sid}) should be the Default Binary "
                    f"encoding object; NodeSet BrowseName is {bn!r}")
            elif not m.by_name(owner):
                err(f"NodeIds.csv {name!r} ({sid}) names an encoding of {owner!r}, "
                    "which is not a type in the NodeSet")
        elif (name != bn and not name.endswith("_" + bn)
              and name != bn.strip("<>") and not name.endswith("_" + bn.strip("<>"))):
            err(f"NodeIds.csv name {name!r} ({sid}) does not resolve to NodeSet "
                f"BrowseName {bn!r}")
    for sid, nid in ns_ids.items():
        if sid not in csv_ids:
            err(f"NodeSet node {m.bname(nid)} ({nid}) is missing from NodeIds.csv")


def _arg_names(m, method_nid, which):
    """Argument names declared in a Method's InputArguments/OutputArguments node."""
    for mem in m.members_of(method_nid):
        if m.bname(mem) == which:
            return [(el.text or "").strip() for el in m.nodes[mem].iter()
                    if local(el.tag) == "Name" and (el.text or "").strip()]
    return []


def _check_new_invariants(m, dt) -> None:
    """Invariants for the 0.2.0 additions. Separate so each stays readable."""

    # A BrowseName is namespace-qualified, and its index is INDEPENDENT of the NodeId's.
    # Migrating one and not the other leaves every node named in a namespace it does not
    # belong to - browse paths resolve against the wrong model and the names collide
    # with whatever that model defines. Nothing else in this file would notice.
    own_idx = m.own[3:-1]
    for nid in m.order:
        raw = m.nodes[nid].get("BrowseName", "")
        idx = raw.split(":", 1)[0] if ":" in raw else "0"
        if not idx.isdigit():
            err(f"{raw!r} ({nid}) has a malformed BrowseName")
            continue
        if idx == "0":
            continue  # deliberate: base-UA names such as the encoding objects
        if idx != own_idx:
            err(f"{raw!r} ({nid}) is named in namespace index {idx} but its NodeId is "
                f"in {m.own[:-1]}. A BrowseName index is not derived from the NodeId, "
                "so a namespace change has to move both")

    # Clause 8 is only enforceable if the members it turns on are Mandatory. A rule
    # resting on an Optional member is a rule a conformant Server can silently not
    # satisfy, which is the failure this whole file exists to prevent.
    dep_t = dt("DeploymentType")
    if dep_t:
        for name in ("VersionBinding", "FallbackPolicy", "DataJurisdiction",
                     "EgressPermitted"):
            mm = m.member_named(dep_t, name)
            if not mm:
                err(f"DeploymentType must declare {name}")
            elif m.modelling_rule(mm) != "Mandatory":
                err(f"DeploymentType.{name} must be Mandatory: clause 8 depends on "
                    "it, and a rule resting on an Optional member can be silently "
                    "not satisfied")

        # Clause 7.2 - the outputs that make a response auditable and interpretable.
        inv = m.member_named(dep_t, "Invoke")
        if inv:
            got = set(_arg_names(m, inv, "OutputArguments"))
            for need in ("ModelUsed", "Usage", "FinishReason"):
                if need not in got:
                    err(f"DeploymentType.Invoke must return {need}; without it a "
                        "caller cannot tell what answered, what it cost, or whether "
                        "the answer is complete")

    # Clause 8.2 forbids credential material in the address space. A member NAMED like
    # a secret is how that prohibition gets violated by accident - and the address
    # space is browsable, subscribable and historisable, so a secret placed here is
    # not merely readable, it is archived.
    secretish = re.compile(r"Secret|Password|PrivateKey|ApiKeyValue|AccessToken"
                           r"|SharedKey|Passphrase")
    for nid in m.order:
        bn = m.bname(nid)
        if secretish.search(bn):
            err(f"{bn} ({nid}) is named like credential material. Clause 8.2 forbids "
                "exposing it: CredentialReference names a credential, it never "
                "carries one")

    # Clause 9.1 - a domain extension that inherits the placeholders unchanged adds
    # metadata while restricting nothing, and a client cannot then tell one kind of
    # registry from another except by convention.
    # The BrowseName is the whole mechanism: an InstanceDeclaration is overridden only
    # by one with the SAME BrowseName. A subtype that invents a new placeholder name
    # looks narrowed and is not - the inherited declaration stays fully open beside it.
    for owner, placeholder, wanted in (
            ("ModelRegistryType", "<Group>", "ModelPublisherType"),
            ("ModelPublisherType", "<Resource>", "AiResourceType")):
        nid = dt(owner)
        if not nid:
            continue
        mem = m.member_named(nid, placeholder)
        if not mem:
            err(f"{owner} must override the inherited {placeholder} placeholder. It "
                f"declares {sorted(m.bname(x) for x in m.members_of(nid) if m.bname(x).startswith('<'))} "
                "instead, which narrows nothing: a placeholder is overridden only by "
                "one with the same BrowseName")
            continue
        td = [tgt for rt, tgt, fwd in m.refs(mem)
              if fwd and rt in ("i=40", "HasTypeDefinition")]
        got = m.bname(td[0]) if td and td[0] in m.nodes else (td[0] if td else "?")
        if got != wanted:
            err(f"{owner}.{placeholder} must be typed {wanted}, found {got}")
        if not any(rt in ("i=35", "Organizes") for rt, _, fwd in m.refs(mem) if not fwd):
            err(f"{owner}.{placeholder} must keep the inherited Organizes reference; "
                "changing it means the declaration does not override")


def check_spec_invariants(m: Model) -> None:
    def dt(name: str) -> str:
        nid = m.by_name(name)
        if not nid:
            err(f"required type {name} is missing from the model")
        return nid

    _check_new_invariants(m, dt)
    # The provenance chain is the reason this model is worth reading, and an Optional
    # digest breaks it without any Server appearing to be non-conformant.
    model_t = dt("ModelType")
    if model_t:
        for name in ("ModelId", "Name", "Version", "Digest", "DigestAlgorithm"):
            mm = m.member_named(model_t, name)
            if not mm:
                err(f"ModelType must declare {name}")
            elif m.modelling_rule(mm) != "Mandatory":
                err(f"ModelType.{name} must be Mandatory; found "
                    f"{m.modelling_rule(mm)!r}. The provenance rule of clause 7 cannot "
                    "depend on a member a conformant Server may omit.")

    dep_t = dt("DeploymentType")
    if dep_t:
        for name in ("DeploymentId", "InferenceLocation", "State"):
            mm = m.member_named(dep_t, name)
            if not mm:
                err(f"DeploymentType must declare {name}")
            elif m.modelling_rule(mm) != "Mandatory":
                err(f"DeploymentType.{name} must be Mandatory")

    base_t = dt("AiJobType")
    if base_t:
        mm = m.member_named(base_t, "JobId")
        if not mm or m.modelling_rule(mm) != "Mandatory":
            err("AiJobType.JobId must be declared Mandatory")
        if m.supertype(base_t) != PROGRAM_STATE_MACHINE:
            err("AiJobType must derive from the Part 10 ProgramStateMachineType "
                f"({PROGRAM_STATE_MACHINE}); a hand-rolled lifecycle would have to "
                "reinvent its transition events")
    for sub in ("LearningJobType", "ModelImportJobType", "InferenceJobType"):
        st = dt(sub)
        if st and m.supertype(st) != m.by_name("AiJobType"):
            err(f"{sub} must derive from AiJobType so that every long-running "
                "operation in this model is observed the same way")
    job_t = dt("LearningJobType")
    if job_t:
        mm = m.member_named(job_t, "State")
        if not mm or m.modelling_rule(mm) != "Mandatory":
            err("LearningJobType.State must be declared Mandatory")

    if not m.by_name("UsesModel"):
        err("UsesModel must exist: it is the only defined path from a deployment to "
            "the artefact its results depend on")

    expect_values = {
        "DatasetSourceEnum": {"Real": 0, "Synthetic": 1, "Mixed": 2},
        "InferenceLocationEnum": {"OnServer": 0},
        "DeploymentStateEnum": {"Inactive": 0},
    }
    for ename, wanted in expect_values.items():
        nid = dt(ename)
        if not nid:
            continue
        got = dict(m.enum_fields(nid))
        for field, value in wanted.items():
            if got.get(field) != value:
                err(f"{ename}.{field} must be {value}; found {got.get(field)!r}")

    job_states = dt("LearningJobStateEnum")
    if job_states:
        want = {"Idle", "Collecting", "Labelling", "Training", "Validating", "Ready",
                "Promoted", "Failed"}
        got = {f for f, _ in m.enum_fields(job_states)}
        if got != want:
            err(f"LearningJobStateEnum must carry exactly {sorted(want)}; "
                f"found {sorted(got)}")

    # This model was factored out of a vision specification so that it would be
    # domain-neutral. Nothing enforces that but a check that fails loudly.
    # Matched on CamelCase word boundaries, so "Framework" is not a hit for "Frame".
    banned = ("Camera", "Image", "Pixel", "Sensor", "Vision", "Robot", "Frame",
              "Detection", "Weld", "Grasp")
    for nid in m.order:
        name = m.bname(nid)
        words = set(re.findall(r"[A-Z][a-z]*", name))
        for word in banned:
            if word in words:
                err(f"{name} ({nid}) names '{word}', which is domain-specific. This "
                    "model is deliberately neutral: a consuming specification owns "
                    "that vocabulary, not this one.")


def check_spec_crossref(m: Model) -> None:
    if not os.path.exists(SPEC):
        err(f"missing {SPEC}")
        return
    with open(SPEC, encoding="utf-8") as fh:
        text = fh.read()

    for nid in m.order:
        if m.cls(nid) not in ("UAObjectType", "UADataType", "UAReferenceType"):
            continue
        name = m.bname(nid)
        if name not in text:
            err(f"model declares {m.cls(nid)[2:]} {name} but the specification never "
                "names it")
        if m.supertype(nid) == "i=29":
            for field, _ in m.enum_fields(nid):
                if not re.search(rf"\b{re.escape(field)}\b", text):
                    err(f"model declares {name}.{field} but the specification never "
                        "names it")

    own = m.own
    for cited in set(re.findall(r"ns=\d+;i=(\d+)", text)):
        if f"{own}i={cited}" not in m.nodes:
            err(f"specification cites {own}i={cited}, which is not in the NodeSet")
    stale = sorted(set(re.findall(r"ns=(\d+);i=\d+", text)) - {own[3:-1]})
    if stale:
        err(f"specification writes NodeIds in namespace index {stale}; this model's "
            f"own namespace is {own[:-1]} and a stale index does not merely go "
            "stale, it points into a different model")

    # Forward, at member granularity. Checking only type NAMES lets a whole Method or
    # a Mandatory member ship undocumented - a Server is obliged to implement it and a
    # client has nothing to read about it. Optional members are not required to be
    # named: many are self-evident and demanding prose for each would produce padding.
    for nid in m.order:
        if m.cls(nid) not in ("UAObjectType",):
            continue
        owner = m.bname(nid)
        for mem in m.members_of(nid):
            name = m.bname(mem)
            if name.startswith("<") or name in ("InputArguments", "OutputArguments"):
                continue
            is_method = m.cls(mem) == "UAMethod"
            if not (is_method or m.modelling_rule(mem) == "Mandatory"):
                continue
            if not re.search(rf"`{re.escape(name)}`", text):
                kind = "Method" if is_method else "Mandatory member"
                err(f"{owner}.{name} is a {kind} the specification never names. A "
                    "Server is obliged to implement it and a client has nothing to "
                    "read about it")

    # The other direction. Every `SomeType.SomeMember` the prose writes must exist,
    # otherwise the document describes a member no Server can implement. Only
    # qualified names are checked, because a bare backticked word is as likely to be
    # an enumeration literal or a term of art as it is to be a member.
    declared = {m.bname(nid) for nid in m.order}
    members = set()
    for nid in m.order:
        owner = m.bname(nid)
        for rt, tgt, fwd in m.refs(nid):
            if fwd and rt in ("i=46", "i=47") and tgt in m.nodes:
                members.add((owner, m.bname(tgt)))
        # A structure's fields are Definition/Field, not references, but the prose
        # writes them with the same `Type.Field` notation.
        d = m.definition(nid)
        if d is not None:
            for f in d:
                if local(f.tag) == "Field" and f.get("Name"):
                    members.add((owner, f.get("Name")))
    for owner, member in set(re.findall(r"`([A-Z][A-Za-z0-9]*Type)\.([A-Za-z][A-Za-z0-9]*)`",
                                        text)):
        # An owner this model does not declare belongs to a consuming specification -
        # 4.2 names one deliberately. Only a validator that loads BOTH models can tell
        # an outside type from a nonexistent one, so that check lives in Vision's.
        if owner not in declared:
            continue
        if (owner, member) not in members:
            err(f"specification names {owner}.{member}, which the model does not declare")


def main() -> int:
    if not os.path.exists(NODESET):
        print(f"ERROR: missing {NODESET}")
        return 2
    try:
        m = Model(NODESET)
    except ET.ParseError as exc:
        print(f"ERROR: NodeSet is not well-formed XML: {exc}")
        return 2

    check_model_header(m)
    check_references(m)
    check_types(m)
    check_instance_declarations(m)
    check_datatypes(m)
    check_method_arguments(m)
    check_csv(m)
    check_spec_invariants(m)
    check_spec_crossref(m)

    if ERRORS:
        print(f"ERRORS ({len(ERRORS)}):")
        for e in ERRORS:
            print(f"  - {e}")
        return 1
    n_types = sum(1 for nid in m.order
                  if m.cls(nid) in ("UAObjectType", "UADataType", "UAReferenceType"))
    print(f"OK - ai-deployment: {len(m.order)} nodes, {n_types} types, "
          "NodeSet/CSV/specification consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
