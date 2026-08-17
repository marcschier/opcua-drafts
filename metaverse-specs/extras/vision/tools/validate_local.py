#!/usr/bin/env python3
"""
Local structural + modelling-rule validator for the OPC UA for Vision Systems NodeSet.

Reproducible in-repo gate (mirrors the openusd-binding validate_local.py convention).
Checks, against Opc.Ua.Vision.NodeSet2.xml:
  * XML well-formedness and a single <Model> whose ONLY <RequiredModel> is the base UA
    namespace - this model is deliberately standalone.
  * Unique NodeIds; every reference target resolves (own ns=1 node or known base-UA id).
  * Every UAObjectType/UADataType/UAReferenceType has an inverse HasSubtype to a base.
  * Every UAReferenceType carries an InverseName.
  * Every instance-declaration member (has ParentNodeId) has a HasTypeDefinition (for
    Objects/Variables) and a HasModellingRule, unless it is a concrete instance rooted
    at an external node (the well-known Vision object under the Server).
  * ParentNodeId is backed by an inverse hierarchical reference.
  * Forward/inverse hierarchical reference pairs are consistent.
  * Enum EnumStrings ArrayDimensions equals the number of enum fields.
  * Every Structure DataType has a Definition and a HasEncoding to a resolvable
    Default Binary encoding Object.
  * Every Definition Field DataType resolves.
  * Every Method's InputArguments/OutputArguments ArrayDimensions matches the number of
    encoded Argument entries.
  * Opc.Ua.Vision.NodeIds.csv and the NodeSet agree exactly - same id set in both
    directions, same NodeClass, and the CSV name resolves to the NodeSet BrowseName
    (the CSV qualifies members as Owner_Member), so the two published artifacts and
    their NodeId assignments cannot drift apart.

Specification invariants (the reason this file is not generic):
  * VisionStreamProtocolEnum.Rtsp MUST be value 0 - RTSP is the mandatory default
    streaming protocol.
  * VisionClipFormatEnum.Jpeg MUST be value 0 - JPEG is the mandatory default clip
    format.
  * ClipEndpointType MUST declare both LatestClip and MaxInlineClipSize, so that the
    size-gated inline delivery facet cannot be half-implemented in the model.

Exit code 0 and "OK" on success; non-zero with an ERRORS list otherwise.
"""
from __future__ import annotations
import csv
import os
import re
import sys
import xml.etree.ElementTree as ET

NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"

# The AI Model Management model is a separate specification. This validator reads its
# NodeSet rather than importing its generator, for the same reason it reads Vision's:
# a checker that asks the emitter what it emitted validates nothing.
AI_NS = "http://opcfoundation.org/UA/AI/"
_HERE = os.path.dirname(os.path.abspath(__file__))
AI_NODESET = os.path.normpath(os.path.join(
    _HERE, "..", "..", "..", "ai-model-management", "Opc.Ua.AiModelManagement.NodeSet2.xml"))


def _ai_prefix():
    """The NodeId prefix the AI Model Management model uses for its OWN namespace.

    Not necessarily ns=1: a NodeSet lists its RequiredModel namespaces in
    NamespaceUris too, so adding a dependency shifts the model's own index. Reading
    it from the file rather than assuming is the difference between this validator
    noticing a change and silently resolving nothing, which would pass.
    """
    if not os.path.exists(AI_NODESET):
        return None
    root = ET.parse(AI_NODESET).getroot()
    uris = [u.text for u in root.findall(f"{NS}NamespaceUris/{NS}Uri")]
    if AI_NS not in uris:
        return None
    return "ns=%d;i=" % (uris.index(AI_NS) + 1)


AI_PREFIX = _ai_prefix()


def _load_ai_types():
    """BrowseName -> numeric id for every type the AI Model Management model declares."""
    out = {}
    if not os.path.exists(AI_NODESET) or not AI_PREFIX:
        return out
    for el in ET.parse(AI_NODESET).getroot():
        tag = el.tag[len(NS):] if el.tag.startswith(NS) else ""
        if tag in ("UAObjectType", "UADataType", "UAReferenceType"):
            bn = (el.get("BrowseName") or "").split(":", 1)[-1]
            nid = el.get("NodeId", "")
            if bn and nid.startswith(AI_PREFIX):
                out[bn] = int(nid.split("i=")[1])
    return out


AI_TYPE_ID = _load_ai_types()


def _load_ai_ids():
    """Every numeric NodeId the AI Model Management model declares, for reference checking."""
    out = set()
    if not os.path.exists(AI_NODESET) or not AI_PREFIX:
        return out
    for el in ET.parse(AI_NODESET).getroot():
        nid = el.get("NodeId", "") if el.tag.startswith(NS) else ""
        if nid.startswith(AI_PREFIX):
            out.add(int(nid.split("i=")[1]))
    return out


AI_IDS = _load_ai_ids()

# Base-UA NodeIds that this model legitimately references (namespace 0).
KNOWN_BASE = {
    # built-in DataTypes
    "i=1", "i=6", "i=7", "i=9", "i=11", "i=12", "i=14", "i=15", "i=17", "i=20",
    "i=21", "i=24", "i=290", "i=294", "i=296", "i=887",
    # abstract bases
    "i=22", "i=29", "i=32",
    # reference types
    "i=35", "i=37", "i=38", "i=40", "i=45", "i=46", "i=47", "i=17603",
    # type definitions
    "i=58", "i=61", "i=63", "i=68", "i=76", "i=17602",
    # modelling rules
    "i=78", "i=80", "i=11508", "i=11510",
    # the Server object, parent of the well-known Vision entry point
    "i=2253",
}
HIER = {"i=47", "i=46", "i=35", "i=17603"}  # HasComponent/HasProperty/Organizes/HasInterface

# Alias -> NodeId, so a DataType written as an alias in one NodeSet can be compared with
# the same DataType written either way in another.
ALIAS_TARGETS = {
    "Boolean": "i=1", "Int32": "i=6", "UInt32": "i=7", "UInt64": "i=9",
    "Double": "i=11", "String": "i=12", "Guid": "i=14", "ByteString": "i=15",
    "NodeId": "i=17", "QualifiedName": "i=20", "LocalizedText": "i=21",
    "UtcTime": "i=294", "Duration": "i=290", "Argument": "i=296",
    "EUInformation": "i=887", "BaseDataType": "i=24",
}


def norm_dt(dt):
    """Normalise a DataType written as an alias, a base NodeId, or a Vision NodeId."""
    if dt is None:
        return None
    return ALIAS_TARGETS.get(dt, dt)

ERR = []


def err(m):
    ERR.append(m)


def check_model_figures(nodeset_path, spec_path):
    """AddressSpace figures must agree with the NodeSet they draw.

    A node table is generated from the NodeSet and so cannot drift. A figure is authored,
    and a wrong arrow looks exactly like a right one, so every Node and Reference a figure
    claims is re-derived from the model rather than read from the prose beside it.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.normpath(os.path.join(here, "..", "..", "..", ".."))
    tools = os.path.join(repo, "word-drafts", "tools")
    if not os.path.isdir(tools) or not os.path.exists(spec_path):
        err("model-figure check could not run: word-drafts/tools or the specification "
            "markdown was not found")
        return
    if tools not in sys.path:
        sys.path.insert(0, tools)
    try:
        from opcdocx import nodeset_diagram
    except ImportError as exc:
        # The parser lives in the Word tooling, whose dependencies are optional here.
        # A missing one is a skip, not a wrong figure; CI installs them so the gate runs.
        print(f"note: model-figure check skipped: {exc}")
        return
    try:
        for message in nodeset_diagram.check_markdown(spec_path, nodeset_path):
            err(message)
    except ValueError as exc:
        err(f"model figure: {exc}")


def _name_matches(csv_name: str, browse_name: str) -> bool:
    """True if a CSV symbolic name resolves to a NodeSet BrowseName.

    The CSV follows the OPC Foundation NodeIds.csv convention: members are qualified as
    Owner_Member, and the symbolic form drops the characters that are legal in a
    BrowseName but not in an identifier - the space in "Default Binary" and the angle
    brackets on a placeholder such as <StreamEndpoint>.
    """
    bn = browse_name.replace(" ", "").replace("<", "").replace(">", "")
    return csv_name == bn or csv_name.endswith("_" + bn)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.normpath(os.path.join(here, "..", "..", "..", "vision",
                                         "Opc.Ua.Vision.NodeSet2.xml"))
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        print(f"ERRORS: 1\n  XML parse error: {e}")
        sys.exit(1)
    check_model_figures(path, os.path.normpath(
        os.path.join(here, "..", "..", "..", "vision", "OPC-UA-Vision.md")))
    root = tree.getroot()

    models = root.findall(f"{NS}Models/{NS}Model")
    if len(models) != 1:
        err(f"expected exactly one <Model>, found {len(models)}")
    else:
        reqs = models[0].findall(f"{NS}RequiredModel")
        uris = [r.get("ModelUri") for r in reqs]
        if "http://opcfoundation.org/UA/" not in uris:
            err("missing <RequiredModel> for the base UA namespace")
        extra = [u for u in uris if u != "http://opcfoundation.org/UA/"]
        if extra:
            err("model must stay standalone (base UA only); unexpected RequiredModel: "
                + ", ".join(extra))

    nodes = [e for e in root if e.tag.startswith(NS) and e.tag[len(NS):].startswith("UA")]
    by_id = {}
    for n in nodes:
        nid = n.get("NodeId")
        if nid in by_id:
            err(f"duplicate NodeId {nid}")
        by_id[nid] = n

    def resolves(tid):
        return tid in by_id or tid in KNOWN_BASE

    def simple_name(n):
        return n.get("BrowseName", "").split(":")[-1]

    # A node is a concrete instance (no ModellingRule expected) when the root of its
    # ParentNodeId chain hangs off an EXTERNAL/base node - e.g. the well-known Vision
    # object under Server i=2253. Type members hang off a Type node in this set and DO
    # require a ModellingRule.
    def is_concrete_instance(node):
        cur = node
        seen = set()
        while True:
            p = cur.get("ParentNodeId")
            if not p or cur.get("NodeId") in seen:
                return False
            seen.add(cur.get("NodeId"))
            if p not in by_id:
                return True
            cur = by_id[p]
            if cur.tag[len(NS):] in ("UAObjectType", "UAVariableType", "UADataType",
                                     "UAReferenceType"):
                return False

    # ---- per-node checks --------------------------------------------------
    for n in nodes:
        cls = n.tag[len(NS):]
        nid = n.get("NodeId")
        bname = n.get("BrowseName", "")
        refs = n.findall(f"{NS}References/{NS}Reference")
        for r in refs:
            tgt = (r.text or "").strip()
            if not resolves(tgt):
                err(f"{nid} ({bname}) references unresolved target {tgt}")
        reftypes = [(r.get("ReferenceType"), (r.text or "").strip(),
                     r.get("IsForward", "true") != "false") for r in refs]

        if cls in ("UAObjectType", "UADataType", "UAReferenceType"):
            if not any(rt == "HasSubtype" and not fwd for rt, _, fwd in reftypes):
                err(f"{cls} {nid} ({bname}) missing inverse HasSubtype to a base type")

        if cls == "UAReferenceType":
            if n.find(f"{NS}InverseName") is None:
                err(f"UAReferenceType {nid} ({bname}) missing <InverseName>")

        if n.get("ParentNodeId"):
            parent = n.get("ParentNodeId")
            if cls in ("UAVariable", "UAObject"):
                if not any(rt == "HasTypeDefinition" for rt, _, _ in reftypes):
                    err(f"{cls} {nid} ({bname}) has ParentNodeId but no HasTypeDefinition")
            if not is_concrete_instance(n):
                if not any(rt == "HasModellingRule" for rt, _, _ in reftypes):
                    err(f"{cls} {nid} ({bname}) has ParentNodeId but no HasModellingRule")
            if not any((rt in ("HasComponent", "HasProperty", "Organizes", "HasInterface")
                        and not fwd and tgt == parent) for rt, tgt, fwd in reftypes):
                err(f"{cls} {nid} ({bname}) ParentNodeId {parent} not backed by an "
                    "inverse hierarchical reference")

        # The DataType attribute is as much a reference as anything in <References>;
        # a typo here would otherwise pass silently.
        if cls == "UAVariable" and n.get("DataType"):
            dt = n.get("DataType")
            if norm_dt(dt) not in KNOWN_BASE and not resolves(dt):
                err(f"{cls} {nid} ({bname}) has unresolved DataType {dt}")

    # ---- forward/inverse hierarchical pairing -----------------------------
    for n in nodes:
        nid = n.get("NodeId")
        for r in n.findall(f"{NS}References/{NS}Reference"):
            rt = r.get("ReferenceType")
            tgt = (r.text or "").strip()
            fwd = r.get("IsForward", "true") != "false"
            if rt in ("HasComponent", "HasProperty", "Organizes") and fwd and tgt in by_id:
                back = by_id[tgt].findall(f"{NS}References/{NS}Reference")
                if not any(b.get("ReferenceType") == rt
                           and (b.text or "").strip() == nid
                           and b.get("IsForward", "true") == "false" for b in back):
                    err(f"{nid} -> {tgt} ({rt}) has no matching inverse reference on target")

    # ---- DataType checks ---------------------------------------------------
    enum_values = {}
    for n in nodes:
        if n.tag[len(NS):] != "UADataType":
            continue
        nid = n.get("NodeId")
        bname = simple_name(n)
        defn = n.find(f"{NS}Definition")
        if defn is None:
            err(f"UADataType {nid} ({bname}) has no <Definition>")
            continue
        fields = defn.findall(f"{NS}Field")
        is_enum = any(f.get("Value") is not None for f in fields)

        if is_enum:
            enum_values[bname] = {f.get("Name"): int(f.get("Value")) for f in fields}
            # EnumStrings is index-addressed, so the literals must be contiguous from 0
            # or the string mapping is silently wrong.
            vals = sorted(int(f.get("Value")) for f in fields)
            if vals != list(range(len(fields))):
                err(f"enum {nid} ({bname}) values {vals} are not contiguous from 0; "
                    "EnumStrings is index-addressed and would mis-map")
            es_id = None
            for r in n.findall(f"{NS}References/{NS}Reference"):
                if (r.get("ReferenceType") == "HasProperty"
                        and r.get("IsForward", "true") != "false"):
                    cand = by_id.get((r.text or "").strip())
                    if cand is not None and simple_name(cand) == "EnumStrings":
                        es_id = (r.text or "").strip()
            if not es_id:
                err(f"enum {nid} ({bname}) has no EnumStrings property")
            else:
                ad = by_id[es_id].get("ArrayDimensions")
                if ad != str(len(fields)):
                    err(f"{nid} ({bname}) EnumStrings ArrayDimensions={ad} != field "
                        f"count {len(fields)}")
        else:
            # Structure: must have a resolvable Default Binary encoding
            encs = [(r.text or "").strip()
                    for r in n.findall(f"{NS}References/{NS}Reference")
                    if r.get("ReferenceType") == "HasEncoding"
                    and r.get("IsForward", "true") != "false"]
            if not encs:
                err(f"structure {nid} ({bname}) has no HasEncoding reference")
            for e in encs:
                if e not in by_id:
                    err(f"structure {nid} ({bname}) HasEncoding target {e} unresolved")
            for f in fields:
                fdt = f.get("DataType")
                if fdt and not resolves(fdt):
                    err(f"structure {nid} ({bname}) field {f.get('Name')} has "
                        f"unresolved DataType {fdt}")

    # ---- Method argument checks -------------------------------------------
    TYPES_NS = "{http://opcfoundation.org/UA/2008/02/Types.xsd}"
    for n in nodes:
        if n.tag[len(NS):] != "UAVariable":
            continue
        if simple_name(n) not in ("InputArguments", "OutputArguments"):
            continue
        val = n.find(f"{NS}Value")
        if val is None:
            err(f"{n.get('NodeId')} ({simple_name(n)}) has no <Value>")
            continue
        count = sum(1 for e in val.iter() if e.tag == f"{TYPES_NS}Argument")
        ad = n.get("ArrayDimensions")
        if ad != str(count):
            err(f"{n.get('NodeId')} ({simple_name(n)}) ArrayDimensions={ad} != "
                f"encoded Argument count {count}")

    # ---- specification invariants -----------------------------------------
    proto = enum_values.get("VisionStreamProtocolEnum", {})
    if proto.get("Rtsp") != 0:
        err("VisionStreamProtocolEnum.Rtsp must be value 0 (RTSP is the mandatory "
            f"default streaming protocol); found {proto.get('Rtsp')}")
    clip = enum_values.get("VisionClipFormatEnum", {})
    if clip.get("Jpeg") != 0:
        err("VisionClipFormatEnum.Jpeg must be value 0 (JPEG is the mandatory default "
            f"clip format); found {clip.get('Jpeg')}")

    # Clause 6.7 is defined against the OPC UA - Data Channels DRAFT. The whole design
    # rests on taking no dependency on it, so the literal must be an append that leaves
    # Rtsp at 0, and the members carrying the binding must exist on the shared base.
    if "DataChannel" not in proto:
        err("VisionStreamProtocolEnum is missing the 'DataChannel' literal required by "
            "clause 6.7")
    elif proto["DataChannel"] != max(proto.values()):
        err("VisionStreamProtocolEnum.DataChannel must be the highest literal (it was "
            f"appended so earlier values stay stable); found {proto['DataChannel']} "
            f"with max {max(proto.values())}")
    me_members = set()
    for n in nodes:
        p = n.get("ParentNodeId")
        if p and p in by_id and simple_name(by_id[p]) == "MediaEndpointType":
            me_members.add(simple_name(n))
    for required in ("DataChannelSource", "DataChannelContentType"):
        if required not in me_members:
            err(f"MediaEndpointType is missing '{required}', required by the optional "
                "clause 6.7 data channel facet. It belongs on the shared base so that "
                "StreamEndpointType and ClipEndpointType both inherit it.")

    # The load-bearing guard for clause 6.7: OPC UA - Data Channels is a base-namespace
    # errata using PROVISIONAL ids. Its README allocates 65000..65099 types,
    # 65100..65199 well-known instances, 65900..65999 EnumStrings and 66000+ members,
    # so the guarded range has to run to the top of the member block, not stop at
    # 65999. Emitting any of them here would dangle on every Server that has not
    # adopted that draft, so the NodeSet must contain none.
    for n in nodes:
        for r in n.findall(f"{NS}References/{NS}Reference"):
            tgt = (r.text or "").strip()
            if tgt.startswith("i="):
                num = tgt[2:]
                if num.isdigit() and 65000 <= int(num) <= 66999:
                    err(f"{n.get('NodeId')} references {tgt}, a PROVISIONAL Data "
                        "Channels identifier. Clause 6.7 is deliberately a prose-only "
                        "binding: this model takes no dependency on that draft, so its "
                        "NodeSet must reference none of its ids.")

    clip_members = set()
    for n in nodes:
        p = n.get("ParentNodeId")
        if p and p in by_id and simple_name(by_id[p]) == "ClipEndpointType":
            clip_members.add(simple_name(n))
    for required in ("LatestClip", "MaxInlineClipSize", "LatestClipMetadata",
                     "InlineDeliveryEnabled"):
        if required not in clip_members:
            err(f"ClipEndpointType is missing '{required}', required by the size-gated "
                "inline delivery facet")

    # ---- NodeId CSV <-> NodeSet cross-check --------------------------------
    # Convention shared with the other extension validators (observability-export,
    # schema-registry, xregistry, WoT-Connectivity): the published CSV and the NodeSet
    # are two views of one model, so every id must appear in both with the same
    # NodeClass and BrowseName. This is what catches a hand-edited artifact, or one of
    # the pair being regenerated without the other.
    csv_path = os.path.normpath(os.path.join(here, "..", "..", "..", "vision",
                                             "Opc.Ua.Vision.NodeIds.csv"))
    if not os.path.exists(csv_path):
        err("Opc.Ua.Vision.NodeIds.csv not found next to the NodeSet")
    else:
        csv_ids = {}
        with open(csv_path, encoding="utf-8") as f:
            for r in csv.reader(f):
                if not r:
                    continue
                if len(r) != 3:
                    err(f"csv bad row {r}")
                    continue
                if not r[1].isdigit():
                    err(f"csv nonnumeric id {r}")
                    continue
                num = int(r[1])
                if num in csv_ids:
                    err(f"csv duplicate id {num}")
                csv_ids[num] = (r[2], r[0])
        xml_ids = {}
        for n in nodes:
            nid = n.get("NodeId", "")
            if not nid.startswith("ns=1;i="):
                continue
            xml_ids[int(nid.split("i=")[1])] = (n.tag[len(NS) + 2:], simple_name(n))
        for num, (cls, bn) in sorted(xml_ids.items()):
            if num not in csv_ids:
                err(f"i={num} {bn} is in the NodeSet but missing from the CSV")
            elif csv_ids[num][0] != cls:
                err(f"i={num} {bn}: CSV NodeClass {csv_ids[num][0]} != NodeSet {cls}")
            elif not _name_matches(csv_ids[num][1], bn):
                err(f"i={num}: CSV name {csv_ids[num][1]} does not resolve to NodeSet "
                    f"BrowseName {bn}")
        for num in sorted(csv_ids):
            if num not in xml_ids:
                err(f"csv id {num} ({csv_ids[num][1]}) is not defined in the NodeSet")

    print(f"nodes: {len(nodes)}")

    # ---- generated annexes in the base spec --------------------------------
    # Annexes F and G are spliced into OPC-UA-Vision.md by build_examples.py. If the
    # markers go missing the splice silently stops updating them, so the spec would
    # keep stale worked examples while every other artifact regenerated.
    spec_path = os.path.normpath(os.path.join(here, "..", "..", "..", "vision",
                                              "OPC-UA-Vision.md"))
    if not os.path.exists(spec_path):
        err("OPC-UA-Vision.md not found")
    else:
        with open(spec_path, encoding="utf-8") as f:
            spec_text = f.read()
        for marker, letter in (("annex-robotics", "F"),
                               ("annex-machine-vision", "G")):
            begin = f"<!-- BEGIN GENERATED: {marker} -->"
            end = f"<!-- END GENERATED: {marker} -->"
            if begin not in spec_text or end not in spec_text:
                err(f"OPC-UA-Vision.md is missing the '{marker}' generated-annex "
                    "markers; build_examples.py cannot splice the annex")
                continue
            body = spec_text[spec_text.index(begin) + len(begin):
                             spec_text.index(end)]
            if f"## Annex {letter} " not in body:
                err(f"OPC-UA-Vision.md '{marker}' region does not contain an "
                    f"'Annex {letter}' heading; regenerate with build_examples.py")

        # ---- specification <-> model, in both directions -------------------
        # Every type and enumeration literal the model declares must be named in the
        # prose, and every `SomeType.SomeMember` the prose writes must exist in the
        # model. Neither direction alone catches drift: the first misses a document
        # that describes a member no Server can implement, the second misses a member
        # that ships undocumented. Only qualified member names are checked in the
        # reverse direction, because a bare backticked word is as likely to be an
        # enumeration literal or a term of art as it is to be a member.
        for n in nodes:
            cls = n.tag[len(NS):]
            if cls not in ("UAObjectType", "UAVariableType", "UADataType",
                           "UAReferenceType"):
                continue
            bn = simple_name(n)
            if bn not in spec_text:
                err(f"model declares {cls[2:]} {bn} but OPC-UA-Vision.md never "
                    "names it")
            for f_el in n.findall(f"{NS}Definition/{NS}Field"):
                fname = f_el.get("Name") or ""
                if fname and not re.search(rf"\b{re.escape(fname)}\b", spec_text):
                    err(f"model declares {bn}.{fname} but OPC-UA-Vision.md never "
                        "names it")

        member_of = set()
        for n in nodes:
            owner = simple_name(n)
            for r in n.findall(f"{NS}References/{NS}Reference"):
                rt = (r.get("ReferenceType") or "").strip()
                tgt = (r.text or "").strip()
                if r.get("IsForward", "true") != "false" and \
                        rt in ("HasComponent", "HasProperty", "i=47", "i=46") and \
                        tgt in by_id:
                    member_of.add((owner, simple_name(by_id[tgt])))
            # A structure's fields are Definition/Field, not references, but the prose
            # writes them with the same `Type.Field` notation.
            for f_el in n.findall(f"{NS}Definition/{NS}Field"):
                member_of.add((owner, f_el.get("Name") or ""))
        declared = {simple_name(n) for n in nodes}
        # AI_TYPE_ID holds every type the AI Model Management model declares. Between the two
        # sets, a `SomeType.Member` whose owner appears in NEITHER names a type that
        # exists nowhere - which is how a reference to a renamed or retired type
        # survives. Skipping it, as the check first did, made exactly that invisible.
        # Types defined by companion specifications this document cites but does not
        # load. Listed explicitly rather than pattern-matched, so that adding a
        # dependency on an outside type is a deliberate edit rather than a silent one.
        EXTERNAL_TYPES = {
            "ResultDataType",        # OPC 40100-1
            "UsdGeomCameraType",     # OPC UA - OpenUSD Scene Materialization
            "UsdApiSchemaType",      # OPC UA - OpenUSD Scene Materialization
            "DataChannelSourceType",  # OPC UA - Data Channels (draft)
        }
        known_elsewhere = set(AI_TYPE_ID) | EXTERNAL_TYPES
        for owner, member in set(re.findall(
                r"`([A-Z][A-Za-z0-9]*Type)\.([A-Za-z][A-Za-z0-9]*)`", spec_text)):
            if owner in declared:
                if (owner, member) not in member_of:
                    err(f"OPC-UA-Vision.md names {owner}.{member}, which the model "
                        "does not declare")
            elif owner not in known_elsewhere:
                err(f"OPC-UA-Vision.md names {owner}.{member}, but neither this model "
                    f"nor the AI Model Management model declares {owner} - a type that "
                    "exists nowhere resolves to nothing")

        # Every MEMBER the model declares must be named in the prose too. The check
        # above covers types and enumeration literals only, which is how six members
        # - CoordinateFrameType.Transform, SegmentationResultType.LabelClasses,
        # IlluminationType.LampType and LightingMode, InferencePipelineType.LearningJob
        # - shipped declared in the NodeSet and CSV and described nowhere, leaving an
        # implementer to guess the semantics or read the XML. A member that no prose
        # names is a member no two Servers will populate the same way.
        #
        # The standard namespace-0 Properties are excluded: they are generated from the
        # Method and enumeration declarations, carry meanings OPC 10000-3 and -5 fix,
        # and are not this document's to define.
        GENERATED_MEMBERS = {"InputArguments", "OutputArguments", "EnumStrings",
                             "Default Binary", "Default XML", "Default JSON"}
        for owner, member in sorted(member_of):
            if owner not in declared or member in GENERATED_MEMBERS:
                continue
            # A <Placeholder> is the instance-declaration idiom for "any number of
            # these live here". The prose names the folder that holds them, which is
            # the thing a client browses; the placeholder itself has no semantics to
            # document beyond its ModellingRule.
            if member.startswith("<"):
                continue
            if not re.search(rf"\b{re.escape(member)}\b", spec_text):
                err(f"model declares {owner}.{member} but OPC-UA-Vision.md never "
                    "names it - an undocumented member is one every implementer "
                    "guesses differently")

    # ---- standard BrowseNames stay in namespace 0 --------------------------
    # The repo-wide guard in .github/scripts/check_browsename_namespace.py covers this
    # for every NodeSet; repeating it here means a single-extension run catches it too,
    # without the repo-wide job. A Method whose InputArguments is qualified into this
    # model's namespace is not found by a client resolving the signature, so the Method
    # appears to take no arguments and every call fails with Bad_TooManyArguments.
    for n in nodes:
        bn = n.get("BrowseName") or ""
        if ":" not in bn:
            continue
        local = bn.split(":", 1)[1]
        if local in ("InputArguments", "OutputArguments", "EnumStrings",
                     "Default Binary", "Default XML", "Default JSON"):
            err(f'{n.get("NodeId")} BrowseName="{bn}": {local} is a standard '
                "namespace-0 BrowseName and must carry no namespace prefix")

    # ---- example overlays --------------------------------------------------
    # Each overlay instantiates the base model. Verify it is well-formed, declares the
    # Vision namespace as a RequiredModel, and only references type NodeIds that this
    # base NodeSet actually defines - the failure mode a hand-authored overlay has.
    vision_dir = os.path.normpath(os.path.join(here, "..", "..", "..", "vision"))
    overlays = []
    for sub in sorted(os.listdir(vision_dir)):
        subdir = os.path.join(vision_dir, sub)
        if not os.path.isdir(subdir):
            continue
        for fn in sorted(os.listdir(subdir)):
            if fn.endswith(".NodeSet2.xml"):
                overlays.append(os.path.join(subdir, fn))

    own_ids = {int(k.split("i=")[1]) for k in by_id if k.startswith("ns=1;i=")}

    # Base-model type BrowseName -> numeric id, so overlay checks can name the types
    # they care about instead of hard-coding provisional NodeIds.
    own_by_name = {}
    for n in nodes:
        if n.tag[len(NS):] in ("UAObjectType", "UADataType", "UAReferenceType"):
            nid = n.get("NodeId", "")
            if nid.startswith("ns=1;i="):
                own_by_name[simple_name(n)] = int(nid.split("i=")[1])

    # Resolve, per type, its Mandatory instance declarations and each member's declared
    # DataType - including inherited ones - so an overlay can be checked against them.
    def type_chain(tid):
        chain, cur, guard = [], tid, 0
        while cur is not None and guard < 20:
            guard += 1
            chain.append(cur)
            nxt = None
            node = by_id.get(f"ns=1;i={cur}")
            if node is not None:
                for r in node.findall(f"{NS}References/{NS}Reference"):
                    if (r.get("ReferenceType") == "HasSubtype"
                            and r.get("IsForward", "true") == "false"):
                        t = (r.text or "").strip()
                        if t.startswith("ns=1;i="):
                            nxt = int(t.split("i=")[1])
            cur = nxt
        return chain

    members_by_type = {}
    for n in nodes:
        p = n.get("ParentNodeId")
        if not p or not p.startswith("ns=1;i="):
            continue
        owner = int(p.split("i=")[1])
        rule = ""
        for r in n.findall(f"{NS}References/{NS}Reference"):
            if r.get("ReferenceType") == "HasModellingRule":
                rule = {"i=78": "Mandatory", "i=80": "Optional",
                        "i=11508": "OptionalPlaceholder",
                        "i=11510": "MandatoryPlaceholder"}.get((r.text or "").strip(), "")
        members_by_type.setdefault(owner, []).append(
            (simple_name(n), rule, n.get("DataType")))

    # Interfaces are applied with HasInterface, so their members count too.
    iface_members = {}
    for n in nodes:
        if n.tag[len(NS):] == "UAObjectType":
            tid = int(n.get("NodeId").split("i=")[1])
            iface_members[tid] = members_by_type.get(tid, [])

    total_overlay_nodes = 0
    for ov_path in overlays:
        label = os.path.relpath(ov_path, vision_dir).replace("\\", "/")
        try:
            ov_root = ET.parse(ov_path).getroot()
        except ET.ParseError as e:
            err(f"{label}: XML parse error: {e}")
            continue
        uris = [u.text for u in ov_root.findall(f"{NS}NamespaceUris/{NS}Uri")]
        if len(uris) < 2 or uris[1] != "http://opcfoundation.org/UA/Vision/":
            err(f"{label}: expected the Vision namespace at NamespaceUris index 2 "
                f"(ns=2); found {uris}")
        # The worked examples show a camera whose inference runs on a described
        # deployment, so they instantiate types from BOTH models. The base Vision
        # NodeSet still requires only base UA; it is the example overlay that composes.
        if len(uris) < 3 or uris[2] != AI_NS:
            err(f"{label}: expected the AI Model Management namespace at NamespaceUris "
                f"index 3 (ns=3); found {uris}")
        req = [r.get("ModelUri")
               for r in ov_root.findall(f"{NS}Models/{NS}Model/{NS}RequiredModel")]
        if "http://opcfoundation.org/UA/Vision/" not in req:
            err(f"{label}: missing <RequiredModel> for the Vision namespace")
        if AI_NS not in req:
            err(f"{label}: missing <RequiredModel> for the AI Model Management namespace")
        ov_nodes = [e for e in ov_root
                    if e.tag.startswith(NS) and e.tag[len(NS):].startswith("UA")]
        total_overlay_nodes += len(ov_nodes)
        ov_ids = {e.get("NodeId") for e in ov_nodes}
        for e in ov_nodes:
            for r in e.findall(f"{NS}References/{NS}Reference"):
                tgt = (r.text or "").strip()
                if tgt.startswith("ns=2;i="):
                    tid = int(tgt.split("i=")[1])
                    if tid not in own_ids:
                        err(f"{label}: {e.get('NodeId')} references {tgt}, which the "
                            "base Vision model does not define")
                elif tgt.startswith("ns=1;i="):
                    if tgt not in ov_ids:
                        err(f"{label}: {e.get('NodeId')} references {tgt}, which the "
                            "overlay does not define")
                elif tgt.startswith("ns=3;i="):
                    if int(tgt.split("i=")[1]) not in AI_IDS:
                        err(f"{label}: {e.get('NodeId')} references {tgt}, which the "
                            "AI Model Management model does not define")
                elif not tgt.startswith("i="):
                    err(f"{label}: {e.get('NodeId')} has malformed reference {tgt}")
            if e.tag[len(NS):] in ("UAObject", "UAVariable"):
                if not any(r.get("ReferenceType") == "HasTypeDefinition"
                           for r in e.findall(f"{NS}References/{NS}Reference")):
                    err(f"{label}: {e.get('NodeId')} has no HasTypeDefinition")

        # Mandatory-member and DataType conformance against the base model. Without
        # this an overlay can instantiate a type and omit the members that make it
        # meaningful, or narrow a member to an incompatible DataType.
        ov_by_id = {e.get("NodeId"): e for e in ov_nodes}
        children = {}
        for e in ov_nodes:
            p = e.get("ParentNodeId")
            if p:
                children.setdefault(p, []).append(e)
        for e in ov_nodes:
            td = None
            ifaces = []
            for r in e.findall(f"{NS}References/{NS}Reference"):
                t = (r.text or "").strip()
                if r.get("ReferenceType") == "HasTypeDefinition":
                    td = t
                elif (r.get("ReferenceType") == "HasInterface"
                      and r.get("IsForward", "true") != "false"):
                    ifaces.append(t)
            if not td or not td.startswith("ns=2;i="):
                continue
            tid = int(td.split("i=")[1])
            present = {simple_name(c) for c in children.get(e.get("NodeId"), [])}
            declared = {}
            for t in type_chain(tid) + [int(i.split("i=")[1]) for i in ifaces
                                        if i.startswith("ns=2;i=")]:
                for (mname, rule, mdt) in members_by_type.get(t, []):
                    declared.setdefault(mname, (rule, mdt))
            missing = sorted(m for m, (rule, _dt) in declared.items()
                             if rule == "Mandatory" and m not in present)
            if missing:
                err(f"{label}: {e.get('NodeId')} ({simple_name(e)}) instantiates "
                    f"ns=2;i={tid} but omits Mandatory member(s) {missing}")
            for c in children.get(e.get("NodeId"), []):
                cname = simple_name(c)
                if cname in declared and c.get("DataType"):
                    # The base model writes its own types as ns=1; in an overlay the
                    # Vision namespace is index 2. Same type, different index.
                    decl_dt = norm_dt(declared[cname][1])
                    if decl_dt and decl_dt.startswith("ns=1;i="):
                        decl_dt = decl_dt.replace("ns=1;i=", "ns=2;i=")
                    if decl_dt and norm_dt(c.get("DataType")) != decl_dt:
                        err(f"{label}: {c.get('NodeId')} ({cname}) has DataType "
                            f"{c.get('DataType')} but the declaration on ns=2;i={tid} "
                            f"is {declared[cname][1]}")

        # ---- spec invariants the overlays must satisfy ----------------------
        # These are the rules a worked example is most likely to quietly break, and
        # every one of them was in fact broken before this check existed.
        type_of = {}
        for e in ov_nodes:
            for r in e.findall(f"{NS}References/{NS}Reference"):
                if r.get("ReferenceType") == "HasTypeDefinition":
                    type_of[e.get("NodeId")] = (r.text or "").strip()

        def type_named(name):
            tid = own_by_name.get(name)
            return f"ns=2;i={tid}" if tid else None

        # The deployment-to-model rule moved with the types it constrains, into the
        # AI Model Management specification. The overlays are still checked against it there,
        # because they instantiate those types; what this validator keeps is the Vision
        # side of the seam - that the pipeline names a deployment at all.
        def ai_type_named(name):
            tid = AI_TYPE_ID.get(name)
            return f"ns=3;i={tid}" if tid else None

        dep_td = ai_type_named("DeploymentType")
        model_td = ai_type_named("ModelType")
        uses_model = ai_type_named("UsesModel")
        for e in ov_nodes:
            if type_of.get(e.get("NodeId")) != dep_td:
                continue
            targets = [(r.text or "").strip()
                       for r in e.findall(f"{NS}References/{NS}Reference")
                       if r.get("ReferenceType") in ("UsesModel", uses_model)
                       and r.get("IsForward", "true") != "false"]
            if len(targets) != 1:
                err(f"{label}: {e.get('NodeId')} is a DeploymentType with "
                    f"{len(targets)} UsesModel references; the AI Model Management "
                    "specification requires exactly one, and its provenance rule "
                    "depends on it")
            for t in targets:
                if type_of.get(t) != model_td:
                    err(f"{label}: {e.get('NodeId')} UsesModel targets {t}, which is "
                        "not a ModelType instance")

        # Clause 11: VIS-Media-Inline is all four members or none.
        clip_td = type_named("ClipEndpointType")
        inline = ("InlineDeliveryEnabled", "MaxInlineClipSize", "LatestClip",
                  "LatestClipMetadata")
        for e in ov_nodes:
            if type_of.get(e.get("NodeId")) != clip_td:
                continue
            have = {simple_name(c) for c in children.get(e.get("NodeId"), [])}
            got = [m for m in inline if m in have]
            if got and len(got) != len(inline):
                err(f"{label}: {e.get('NodeId')} declares a proper subset of the "
                    f"VIS-Media-Inline members {sorted(got)}; clause 11 requires all "
                    f"of {list(inline)} together or none")

        # Clause 6.7: an endpoint that says its protocol IS a data channel must say
        # where that channel is, or a client has no way to open it.
        stream_td = type_named("StreamEndpointType")
        dc_value = enum_values.get("VisionStreamProtocolEnum", {}).get("DataChannel")
        for e in ov_nodes:
            if type_of.get(e.get("NodeId")) != stream_td or dc_value is None:
                continue
            kids = {simple_name(c): c for c in children.get(e.get("NodeId"), [])}
            proto_node = kids.get("StreamProtocol")
            if proto_node is None:
                continue
            # Read the encoded scalar, not the surrounding prose - a Description
            # containing the digit would otherwise trip this.
            val = None
            for v in proto_node.findall(f"{NS}Value"):
                for child in v:
                    if (child.text or "").strip().lstrip("-").isdigit():
                        val = int((child.text or "").strip())
            if val == dc_value and "DataChannelSource" not in kids:
                err(f"{label}: {e.get('NodeId')} ({simple_name(e)}) declares "
                    "StreamProtocol=DataChannel but no DataChannelSource, so a client "
                    "cannot open the channel (clause 6.7)")

        # 4.2: exactly one well-known Vision root, a component of the Server Object,
        # with its BrowseName qualified by the Vision namespace (index 2 here).
        root_td = type_named("VisionRootType")
        roots = [e for e in ov_nodes if type_of.get(e.get("NodeId")) == root_td]
        if len(roots) != 1:
            err(f"{label}: expected exactly one VisionRootType instance, found "
                f"{len(roots)} (clause 4.2)")
        for e in roots:
            if not any((r.text or "").strip() == "i=2253"
                       for r in e.findall(f"{NS}References/{NS}Reference")):
                err(f"{label}: {e.get('NodeId')} is the Vision root but has no "
                    "reference to the Server Object i=2253, so it is unreachable "
                    "after import (clause 4.2)")
            if not (e.get("BrowseName") or "").startswith("2:"):
                err(f"{label}: Vision root BrowseName is "
                    f"{e.get('BrowseName')}; clause 4.2 qualifies it with the Vision "
                    "namespace, which is index 2 in an overlay")

    if overlays:
        print(f"overlays: {len(overlays)} ({total_overlay_nodes} instance nodes)")

    if ERR:
        print(f"ERRORS: {len(ERR)}")
        for e in ERR:
            print(f"  - {e}")
        sys.exit(1)
    print("OK - 0 errors")


if __name__ == "__main__":
    main()
