#!/usr/bin/env python3
"""
Local structural + modelling-rule validator for the OPC UA - Robot Intent NodeSet.

Reproducible in-repo gate (mirrors the vision and openusd-binding validate_local.py
convention). Everything is re-derived from the committed artifacts with the standard
library alone; nothing here imports the generator, because a checker that asks the
emitter what it emitted validates nothing.

Structural checks, against Opc.Ua.RobotIntent.NodeSet2.xml:
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
  * Opc.Ua.RobotIntent.NodeIds.csv and the NodeSet agree exactly - same id set in both
    directions, same NodeClass, and the CSV name resolves to the NodeSet BrowseName.

Specification invariants (the reason this file is not generic):
  * IntentOperationType and MissionType MUST subtype ProgramStateMachineType (i=2391).
    The whole lifecycle argument of clause 6 rests on this, so a refactor that quietly
    reparented them would otherwise pass.
  * IntentDataType and MotionIntentDataType MUST be abstract, and every other
    *IntentDataType MUST descend from IntentDataType - the hierarchy is what makes a
    mission step and a submission the same shape.
  * BufferModeEnum.Aborting MUST be 0: it is the default and every Server accepts it.
  * IntentFailureEnum.None MUST be 0, so that a default-initialised result reads as
    "no failure".
  * OperationalModeEnum MUST number Automatic 3 and AutomaticExternal 4, and
    StopModeEnum MUST number OnPath 1 through EndOfInstruction 5, matching OPC 40010-1.
    These are cited as interoperable in Annex B; renumbering them breaks that claim.
  * ExecutionStateEnum MUST carry exactly the nine states clause 6.3 tabulates.
  * Pose3DDataType MUST carry Position[3] and Orientation[4] - clause 5.2 fixes the
    quaternion form.
  * IntentControllerType MUST declare SubmitIntent, CancelIntent, CancelAll,
    RequestControl and ReleaseControl as Mandatory: they are the RI-Base facet, and
    SafetyState as Mandatory, because clause 10.4 drives refusals from it.
  * ProcessIntentDataType MUST be abstract and all six process intents MUST descend
    from it, so a client that understands the base can carry one it has never seen.
  * MissionTransitionDataType.Condition MUST be the base UA ContentFilter. Replacing it
    with a bespoke expression would oblige every implementer to write a parser.
  * SafetyStateType's reported members MUST be Mandatory: a refusal rule cannot depend
    on a member a conformant Server is allowed to omit.

Specification/model cross-checks, in BOTH directions:
  * Every ObjectType, DataType and ReferenceType the model declares is named in
    OPC-UA-Robot-Intent.md, and every enumeration literal it declares appears there.
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
STD = os.path.normpath(os.path.join(HERE, "..", "..", "..", "robot-intent"))
NODESET = os.path.join(STD, "Opc.Ua.RobotIntent.NodeSet2.xml")
CSVFILE = os.path.join(STD, "Opc.Ua.RobotIntent.NodeIds.csv")
SPEC = os.path.join(STD, "OPC-UA-Robot-Intent.md")

NS = {"u": "http://opcfoundation.org/UA/2011/03/UANodeSet.xsd"}
UAX = {"uax": "http://opcfoundation.org/UA/2008/02/Types.xsd"}
UA_NAMESPACE = "http://opcfoundation.org/UA/"
PROGRAM_STATE_MACHINE = "i=2391"
CONTENT_FILTER = "i=586"

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

    def resolves(self, target: str) -> bool:
        """Own-namespace targets must exist here; base-UA ids are taken on trust."""
        if target in self.nodes:
            return True
        if target.startswith("ns=1;"):
            return False
        return bool(re.fullmatch(r"i=\d+", target)) or target in self.aliases

    def definition(self, nid: str):
        for child in self.nodes[nid]:
            if local(child.tag) == "Definition":
                return child
        return None

    def members_of(self, nid: str) -> list[str]:
        want = f"ns=1;i={nid.split('=')[-1]}" if not nid.startswith("ns=1;") else nid
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
    if uris != [UA_NAMESPACE]:
        err("this model is standalone: the only RequiredModel must be "
            f"{UA_NAMESPACE}, found {uris}")
    uris_declared = [(u.text or "").strip()
                     for u in m.root.findall("u:NamespaceUris/u:Uri", NS)]
    if len(uris_declared) != 1:
        err(f"expected exactly one NamespaceUri, found {uris_declared}")
    elif uris_declared[0] != models[0].get("ModelUri"):
        err("NamespaceUris entry and Model ModelUri disagree")


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
        elif name != bn and not name.endswith("_" + bn):
            err(f"NodeIds.csv name {name!r} ({sid}) does not resolve to NodeSet "
                f"BrowseName {bn!r}")
    for sid, nid in ns_ids.items():
        if sid not in csv_ids:
            err(f"NodeSet node {m.bname(nid)} ({nid}) is missing from NodeIds.csv")


def check_spec_invariants(m: Model) -> None:
    def dt(name: str) -> str:
        nid = m.by_name(name)
        if not nid:
            err(f"required type {name} is missing from the model")
        return nid

    for name in ("IntentOperationType", "MissionType"):
        nid = dt(name)
        if nid and m.supertype(nid) != PROGRAM_STATE_MACHINE:
            err(f"{name} must subtype ProgramStateMachineType "
                f"({PROGRAM_STATE_MACHINE}); found {m.supertype(nid)!r}. Clause 6 "
                "rests on the Part 10 lifecycle.")

    for name in ("IntentDataType", "MotionIntentDataType"):
        nid = dt(name)
        if nid and m.nodes[nid].get("IsAbstract") != "true":
            err(f"{name} must be abstract")

    intent_base = m.by_name("IntentDataType")
    if intent_base:
        for nid in m.order:
            n = m.bname(nid)
            if m.cls(nid) != "UADataType" or not n.endswith("IntentDataType"):
                continue
            if n in ("IntentDataType",):
                continue
            seen, cur = set(), m.supertype(nid)
            while cur.startswith("ns=1;") and cur not in seen:
                seen.add(cur)
                cur = m.supertype(cur)
            if intent_base not in seen:
                err(f"{n} does not descend from IntentDataType")

    expect_values = {
        "BufferModeEnum": {"Aborting": 0},
        "IntentFailureEnum": {"None": 0},
        "OperationalModeEnum": {"Automatic": 3, "AutomaticExternal": 4},
        "StopModeEnum": {"OnPath": 1, "EndOfCycle": 2, "ProcessStop": 3,
                         "QuickStop": 4, "EndOfInstruction": 5},
        "AxisKindEnum": {"Revolute": 0, "Prismatic": 1},
        "TerminationModeEnum": {"Exact": 0, "Blend": 1},
        # Abort is what a mission without a declared policy gets, so it must be zero.
        "ErrorPolicyEnum": {"Abort": 0},
        "DivergenceKindEnum": {"Alternative": 0, "Parallel": 1},
        "SafeMotionFunctionEnum": {"None": 0},
    }
    for ename, wanted in expect_values.items():
        nid = dt(ename)
        if not nid:
            continue
        got = dict(m.enum_fields(nid))
        for field, value in wanted.items():
            if got.get(field) != value:
                err(f"{ename}.{field} must be {value}; found {got.get(field)!r}")

    exec_nid = dt("ExecutionStateEnum")
    if exec_nid:
        want = {"Accepted", "Queued", "Executing", "Suspended", "Cancelling",
                "Succeeded", "Failed", "Cancelled", "Retriable"}
        got = {f for f, _ in m.enum_fields(exec_nid)}
        if got != want:
            err(f"ExecutionStateEnum must carry exactly {sorted(want)}; "
                f"found {sorted(got)}")

    pose = dt("Pose3DDataType")
    if pose:
        dims = {f.get("Name"): f.get("ArrayDimensions")
                for f in m.struct_fields(pose)}
        if dims.get("Position") != "3":
            err("Pose3DDataType.Position must be a 3-element array")
        if dims.get("Orientation") != "4":
            err("Pose3DDataType.Orientation must be a 4-element quaternion array")

    ctl = dt("IntentControllerType")
    if ctl:
        for name in ("SubmitIntent", "CancelIntent", "CancelAll", "RequestControl",
                     "ReleaseControl"):
            mm = m.member_named(ctl, name)
            if not mm:
                err(f"IntentControllerType must declare {name} (RI-Base facet)")
            elif m.modelling_rule(mm) != "Mandatory":
                err(f"IntentControllerType.{name} must be Mandatory for RI-Base; "
                    f"found {m.modelling_rule(mm)!r}")
        # Clause 10.4 requires a Server to refuse on what the safety system reports,
        # which it cannot do if the state is not there to read.
        safety = m.member_named(ctl, "SafetyState")
        if not safety:
            err("IntentControllerType must declare SafetyState: clause 10.4 requires "
                "refusals to be driven from it")
        elif m.modelling_rule(safety) != "Mandatory":
            err("IntentControllerType.SafetyState must be Mandatory")

    # Every process intent descends from ProcessIntentDataType, so a client that
    # understands the base can carry one it has never seen.
    process_base = m.by_name("ProcessIntentDataType")
    if process_base:
        if m.nodes[process_base].get("IsAbstract") != "true":
            err("ProcessIntentDataType must be abstract")
        for name in ("ArcWeldIntentDataType", "SpotWeldIntentDataType",
                     "DispenseIntentDataType", "FastenIntentDataType",
                     "PalletiseIntentDataType", "SurfaceFinishIntentDataType"):
            nid = m.by_name(name)
            if not nid:
                err(f"required process intent {name} is missing from the model")
            elif m.supertype(nid) != process_base:
                err(f"{name} must subtype ProcessIntentDataType")

    # The transition condition reuses the base UA ContentFilter rather than inventing
    # an expression language; a change here would oblige implementers to write a parser.
    transition = m.by_name("MissionTransitionDataType")
    if transition:
        fields = {f.get("Name"): f.get("DataType") for f in m.struct_fields(transition)}
        if fields.get("Condition") != CONTENT_FILTER:
            err("MissionTransitionDataType.Condition must be the base UA ContentFilter "
                f"({CONTENT_FILTER}); found {fields.get('Condition')!r}")

    safety_state = m.by_name("SafetyStateType")
    if safety_state:
        for name in ("ActiveFunction", "EmergencyStopActive", "ProtectiveStopActive",
                     "SafeSpeedLimitActive", "SafeSpeedLimit", "SafetyControllerOk"):
            mm = m.member_named(safety_state, name)
            if not mm:
                err(f"SafetyStateType must declare {name} (clause 10.4)")
            elif m.modelling_rule(mm) != "Mandatory":
                err(f"SafetyStateType.{name} must be Mandatory: a refusal rule cannot "
                    "depend on an optional member")


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

    for cited in set(re.findall(r"ns=1;i=(\d+)", text)):
        if f"ns=1;i={cited}" not in m.nodes:
            err(f"specification cites ns=1;i={cited}, which is not in the NodeSet")


def main() -> int:
    if not os.path.exists(NODESET):
        print(f"ERROR: missing {NODESET}")
        return 2

    # AddressSpace figures must agree with the model they draw. A node table is generated
    # from the NodeSet and cannot drift; a figure is authored, and a wrong arrow looks
    # exactly like a right one, so every claim is re-derived from the model.
    _tools = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..",
                                           "word-drafts", "tools"))
    if os.path.isdir(_tools) and os.path.exists(SPEC):
        if _tools not in sys.path:
            sys.path.insert(0, _tools)
        try:
            from opcdocx import nodeset_diagram as _nd
        except ImportError as _exc:
            # The parser lives in the Word tooling, whose dependencies are optional here.
            # A missing one is a skip, not a wrong figure; CI installs them so the gate runs.
            print(f"note: model-figure check skipped: {_exc}")
        else:
            try:
                for _msg in _nd.check_markdown(SPEC, NODESET):
                    err(_msg)
            except ValueError as _exc:
                err(f"model figure: {_exc}")
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
    print(f"OK - robot-intent: {len(m.order)} nodes, {n_types} types, "
          "NodeSet/CSV/specification consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
