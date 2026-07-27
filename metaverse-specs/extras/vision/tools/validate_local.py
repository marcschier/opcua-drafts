#!/usr/bin/env python3
"""
Local structural + modelling-rule validator for the OPC UA — Vision NodeSet.

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
import os
import sys
import xml.etree.ElementTree as ET

NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"

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
    "i=78", "i=80", "i=11508",
    # the Server object, parent of the well-known Vision entry point
    "i=2253",
}
HIER = {"i=47", "i=46", "i=35", "i=17603"}  # HasComponent/HasProperty/Organizes/HasInterface

ERR = []


def err(m):
    ERR.append(m)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.normpath(os.path.join(here, "..", "..", "..", "vision",
                                         "Opc.Ua.Vision.NodeSet2.xml"))
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        print(f"ERRORS: 1\n  XML parse error: {e}")
        sys.exit(1)
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

    print(f"nodes: {len(nodes)}")

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
        req = [r.get("ModelUri")
               for r in ov_root.findall(f"{NS}Models/{NS}Model/{NS}RequiredModel")]
        if "http://opcfoundation.org/UA/Vision/" not in req:
            err(f"{label}: missing <RequiredModel> for the Vision namespace")
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
                elif not tgt.startswith("i="):
                    err(f"{label}: {e.get('NodeId')} has malformed reference {tgt}")
            if e.tag[len(NS):] in ("UAObject", "UAVariable"):
                if not any(r.get("ReferenceType") == "HasTypeDefinition"
                           for r in e.findall(f"{NS}References/{NS}Reference")):
                    err(f"{label}: {e.get('NodeId')} has no HasTypeDefinition")

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
