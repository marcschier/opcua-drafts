#!/usr/bin/env python3
"""Validate the generated Scenario Bindings examples.

For each domain overlay NodeSet: well-formedness, unique NodeIds, no dangling internal
references, and full cross-NodeSet reference resolution against the base PubSub Scenario
Binding spec + the companion + DI/IA/Machinery NodeSets. Base companion NodeSets are read
from tools/ref/ (gitignored). Exit non-zero on any error.
"""
import os
import sys
import xml.etree.ElementTree as ET
import nodeset_util as nu
from nodeset_util import UA

HERE = os.path.dirname(os.path.abspath(__file__))
EX = os.path.dirname(HERE)
REF = os.path.join(HERE, "ref")
# The base spec NodeSet and the per-spec example overlays are standardized artifacts under
# core-specs/scenario-binding/; the descriptors + this validator are secondary here in extras.
CORE = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..",
                                    "core-specs", "scenario-binding"))
BIND = os.path.join(CORE, "Opc.Ua.ScenarioBinding.NodeSet2.xml")
NS = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"

DOMAINS = {
    "Pumps": {"base": ["Opc.Ua.Pumps.NodeSet2.xml", "Opc.Ua.Di.NodeSet2.xml",
                       "Opc.Ua.Machinery.NodeSet2.xml"]},
    "Robotics": {"base": ["Opc.Ua.Robotics.NodeSet2.xml", "Opc.Ua.Di.NodeSet2.xml",
                          "Opc.Ua.IA.NodeSet2.xml", "Opc.Ua.Machinery.NodeSet2.xml"]},
    # Facets overlay locates bound items by type-level BrowsePath (values, not node
    # references), so it resolves against the base spec alone - no companion NodeSet needed.
    "Facets": {"base": []},
    # DI facet examples (both live in examples/di/): nameplate identity on IVendorNameplateType
    # (which Pumps extends) and a device-only DeviceHealth binding on IDeviceHealthType.
    "DI": {"base": ["Opc.Ua.Di.NodeSet2.xml"]},
    "DIDeviceHealth": {"base": ["Opc.Ua.Di.NodeSet2.xml"], "folder": "di"},
}

errors = []


def check(domain, spec):
    base_files = spec["base"]
    folder = spec.get("folder", domain.lower())
    f = os.path.join(CORE, folder, f"Opc.Ua.{domain}.ScenarioBinding.NodeSet2.xml")
    tree = ET.parse(f)  # raises on malformed
    root = tree.getroot()
    nodes = [e for e in root if e.tag.startswith(NS + "UA")]
    ids = [e.get("NodeId") for e in nodes]
    if len(ids) != len(set(ids)):
        errors.append(f"{domain}: duplicate NodeIds")
    defined_local = set(ids)
    for e in nodes:
        refs = e.find(NS + "References")
        if refs is None:
            continue
        for r in refs:
            if r.text.startswith("ns=1;") and r.text not in defined_local:
                errors.append(f"{domain}: dangling internal ref {r.text} on {e.get('BrowseName')}")
    # cross-nodeset resolution
    db = nu.NodeSetDB()
    db.load(f)
    db.load(BIND)
    for bf in base_files:
        db.load(os.path.join(REF, bf))
    defined = set(db.nodes.keys())

    def ok(k):
        return (k[0] == UA and isinstance(k[1], int) and k[1] < 60000) or k in defined

    ex = nu.NodeSetDB()
    ex.load(f)
    unresolved = 0
    for k, n in ex.nodes.items():
        if n.datatype and not ok(n.datatype):
            errors.append(f"{domain}: unresolved DataType {n.datatype} on {n.bn_name}")
            unresolved += 1
        for rt, tgt, _ in n.refs:
            for t in (rt, tgt):
                if not ok(t):
                    errors.append(f"{domain}: unresolved ref {t} on {n.bn_name}")
                    unresolved += 1
    print(f"{domain}: {len(nodes)} nodes, {len(set(ids))} unique, "
          f"{unresolved} unresolved refs")


def main():
    if not os.path.exists(BIND):
        sys.exit(f"base spec NodeSet not found: {BIND}")
    for dom, spec in DOMAINS.items():
        if not all(os.path.exists(os.path.join(REF, x)) for x in spec["base"]):
            print(f"{dom}: SKIP (base NodeSets missing under tools/ref/)")
            continue
        check(dom, spec)
    print(f"\nERRORS: {len(errors)}")
    for e in errors[:40]:
        print("  ", e)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
