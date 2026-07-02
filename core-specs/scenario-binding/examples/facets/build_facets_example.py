#!/usr/bin/env python3
"""Worked example for §5.12 (binding inheritance & facet composition).

Demonstrates, against the self-contained `Opc.Ua.FacetDemo.NodeSet2.xml` model, how a
`MachineType` reuses and EXTENDS base-facet scenario bindings across all three OPC UA
composition axes instead of duplicating fields:

  * subtype  : MachineType is-a DeviceType        -> inherits the Device Observability binding
  * AddIn    : MachineType HasAddIn Location       -> composes the Location Observability binding
  * interface: MachineType HasInterface IMaintenance-> inherits the Maintenance binding

It emits `Opc.Ua.Facets.ScenarioBinding.NodeSet2.xml` (an illustrative overlay showing the four
base bindings plus the two DERIVED bindings, with `BaseDataSetClassIds`/`HasBaseBinding` lineage
and per-field `SourceScenarioBindingClassId` provenance) and an addendum that resolves the merged
Machine DataSets and shows how a facet-scoped subscriber extracts its field subset.

Deterministic. Run:  python build_facets_example.py
"""
import os
import sys
import uuid
import xml.sax.saxutils as sx

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
from nodeset_util import NodeSetDB  # noqa: E402
from build_bindings import DATASET_CLASS_NS, FIELD_ID_NS  # noqa: E402  (shared formula)

UA = "http://opcfoundation.org/UA/"
BASE = "http://opcfoundation.org/UA/FacetDemo/"
EX = "http://opcfoundation.org/UA/PubSub/Examples/Facets/"
OBS = "http://opcfoundation.org/UA/PubSub/Scenarios/Observability"
MAINT = "http://opcfoundation.org/UA/PubSub/Scenarios/Maintenance"
MAJOR = 1

# provisional base-spec type ids (see the base model)
T_BINDINGS, T_GROUP, T_BINDING, T_BOUNDVAR = 60010, 60018, 60011, 60013
KIND = {"Telemetry": 0, "Identity": 3, "Maintenance": 5, "Status": 1}


def class_id(scenario_uri, applies_type):
    return uuid.uuid5(DATASET_CLASS_NS, f"{scenario_uri}|{BASE};{applies_type}|{MAJOR}")


def field_id(scenario_uri, applies_type, field):
    return uuid.uuid5(FIELD_ID_NS, f"Facets|{scenario_uri}|{applies_type}|{field}")


# --- binding catalogue: base facets + derived (composed) bindings ------------
# Each item: (fieldName, browsePath-relative-to-target, kind)
BASE_BINDINGS = {
    "DeviceObservability": {
        "scenario": OBS, "target": "DeviceType", "axis": "ObjectType (subtype base)",
        "items": [("Manufacturer", "/Manufacturer", "Identity"),
                  ("SerialNumber", "/SerialNumber", "Identity"),
                  ("DeviceHealth", "/DeviceHealth", "Status")]},
    "LocationObservability": {
        "scenario": OBS, "target": "LocationAddInType", "axis": "AddIn (structural facet)",
        "items": [("Latitude", "/Latitude", "Telemetry"),
                  ("Longitude", "/Longitude", "Telemetry"),
                  ("Altitude", "/Altitude", "Telemetry")]},
    "Maintenance": {
        "scenario": MAINT, "target": "IMaintenanceFacetType", "axis": "Interface (contract facet)",
        "items": [("LastMaintenanceDate", "/LastMaintenanceDate", "Maintenance")]},
}

# Derived bindings: only DELTA fields; `extends` names base bindings + the mount path the base
# fields acquire on the derived instance (empty for subtype/interface, the AddIn BrowseName for
# an AddIn).
DERIVED_BINDINGS = {
    "MachineObservability": {
        "scenario": OBS, "target": "MachineType", "axis": "MachineType (is-a Device + Location AddIn)",
        "delta": [("SpindleSpeed", "/SpindleSpeed", "Telemetry"),
                  ("AxisLoad", "/AxisLoad", "Telemetry")],
        # override-by-FieldName: refine the inherited Device `DeviceHealth` (e.g. faster sampling)
        # while keeping it part of the Device facet (base provenance retained).
        "overrides": [("DeviceHealth", "/DeviceHealth", "Status", "DeviceObservability")],
        "extends": [("DeviceObservability", ""), ("LocationObservability", "Location")]},
    "MachineMaintenance": {
        "scenario": MAINT, "target": "MachineType", "axis": "MachineType implements IMaintenance",
        "delta": [], "overrides": [],
        "extends": [("Maintenance", "")]},
}


def compose(name):
    """Return (own_class, [(fieldName, path, provenanceClassId, sourceLabel, overridden)]).
    Base fields are re-rooted under their mount path; an override replaces the inherited field
    but keeps its base facet provenance; the derived binding's own delta fields carry the derived
    class as provenance."""
    d = DERIVED_BINDINGS[name]
    own_cls = class_id(d["scenario"], d["target"])
    by_name, order = {}, []
    for base_name, mount in d["extends"]:
        b = BASE_BINDINGS[base_name]
        bcls = class_id(b["scenario"], b["target"])
        for fn, path, _kind in b["items"]:
            full = (f"/{mount}" if mount else "") + path
            if fn not in by_name:
                order.append(fn)
            by_name[fn] = (fn, full, bcls, base_name, False)
    for fn, path, _kind, base_name in d.get("overrides", []):
        b = BASE_BINDINGS[base_name]
        bcls = class_id(b["scenario"], b["target"])
        if fn not in by_name:
            order.append(fn)
        by_name[fn] = (fn, path, bcls, base_name, True)
    for fn, path, _kind in d["delta"]:
        if fn not in by_name:
            order.append(fn)
        # own delta fields omit provenance (implicitly the composing binding's own class)
        by_name[fn] = (fn, path, None, name, False)
    return own_cls, [by_name[fn] for fn in order]


# ===========================================================================
# NodeSet emission (compact illustrative overlay)
# ===========================================================================
NSMAP = {UA: 0, EX: 1, BASE: 2}
U = 'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd"'


class Emit:
    def __init__(self):
        self.out = []
        self.nid = 5000
        self.node_by_binding = {}

    def _id(self):
        self.nid += 1
        return self.nid

    def _open(self, cls, nid, bn, parent=None):
        p = f' ParentNodeId="ns=1;i={parent}"' if parent else ""
        self.out.append(f'  <{cls} NodeId="ns=1;i={nid}" BrowseName="{bn}"{p}>')
        self.out.append(f'    <DisplayName>{sx.escape(bn.split(":",1)[-1])}</DisplayName>')

    def _refs(self, refs):
        self.out.append("    <References>")
        for rt, tgt, fwd in refs:
            f = "" if fwd else ' IsForward="false"'
            self.out.append(f'      <Reference ReferenceType="{rt}"{f}>{tgt}</Reference>')
        self.out.append("    </References>")

    def prop(self, name, datatype, value, parent, valuerank=None):
        nid = self._id()
        vr = ' ValueRank="1" ArrayDimensions="0"' if valuerank else ""
        self.out.append(f'  <UAVariable NodeId="ns=1;i={nid}" BrowseName="1:{name}" '
                        f'ParentNodeId="ns=1;i={parent}" DataType="{datatype}"{vr}>')
        self.out.append(f'    <DisplayName>{name}</DisplayName>')
        self._refs([("i=40", "i=68", True), ("i=46", f"ns=1;i={parent}", False)])
        self.out.append(f'    <Value>{value}</Value>')
        self.out.append('  </UAVariable>')
        return nid

    def rel_path(self, path):
        els = []
        for seg in path.strip("/").split("/"):
            els.append('<uax:RelativePathElement>'
                       '<uax:ReferenceTypeId><uax:Identifier>i=33</uax:Identifier>'
                       '</uax:ReferenceTypeId><uax:IsInverse>false</uax:IsInverse>'
                       '<uax:IncludeSubtypes>true</uax:IncludeSubtypes>'
                       f'<uax:TargetName><uax:NamespaceIndex>{NSMAP[BASE]}</uax:NamespaceIndex>'
                       f'<uax:Name>{sx.escape(seg)}</uax:Name></uax:TargetName>'
                       '</uax:RelativePathElement>')
        return (f'<uax:RelativePath {U}><uax:Elements>{"".join(els)}'
                f'</uax:Elements></uax:RelativePath>')

    def guid(self, g):
        return f'<uax:Guid {U}><uax:String>{g}</uax:String></uax:Guid>'

    def bound_item(self, binding_id, scenario, target, fn, path, kind, prov=None):
        iid = self._id()
        self._open("UAObject", iid, f"1:{fn}", binding_id)
        self._refs([("i=40", f"i={T_BOUNDVAR}", True),
                    ("i=47", f"ns=1;i={binding_id}", False)])
        self.out.append('  </UAObject>')
        self.prop("FieldName", "i=12",
                  f'<uax:String {U}>{sx.escape(fn)}</uax:String>', iid)
        self.prop("Kind", "i=60051",
                  f'<uax:Int32 {U}>{KIND[kind]}</uax:Int32>', iid)
        self.prop("BrowsePath", "i=540", self.rel_path(path), iid)
        if prov is not None:
            self.prop("SourceScenarioBindingClassId", "i=14", self.guid(prov), iid)
        self.prop("DataSetFieldId", "i=14",
                  self.guid(field_id(scenario, target, fn)), iid)

    def binding(self, group_id, name, spec):
        bid = self._id()
        self.node_by_binding[name] = bid
        self._open("UAObject", bid, f"1:{name}", group_id)
        self._refs([("i=40", f"i={T_BINDING}", True),
                    ("i=47", f"ns=1;i={group_id}", False)])
        self.out.append('  </UAObject>')
        self.prop("ScenarioUri", "i=12",
                  f'<uax:String {U}>{sx.escape(spec["scenario"])}</uax:String>', bid)
        self.prop("Direction", "i=60050", f'<uax:Int32 {U}>0</uax:Int32>', bid)
        self.prop("DataSetClassId", "i=14",
                  self.guid(class_id(spec["scenario"], spec["target"])), bid)
        return bid

    def base_binding(self, group_id, name):
        spec = BASE_BINDINGS[name]
        bid = self.binding(group_id, name, spec)
        for fn, path, kind in spec["items"]:
            self.bound_item(bid, spec["scenario"], spec["target"], fn, path, kind)

    def derived_binding(self, group_id, name):
        spec = DERIVED_BINDINGS[name]
        bid = self.binding(group_id, name, spec)
        # lineage: BaseDataSetClassIds + HasBaseBinding to the base binding nodes
        base_cls = [class_id(BASE_BINDINGS[b]["scenario"], BASE_BINDINGS[b]["target"])
                    for b, _m in spec["extends"]]
        lst = "".join(self.guid(c) for c in base_cls)
        self.prop("BaseDataSetClassIds", "i=14",
                  f'<uax:ListOfGuid {U}>{lst}</uax:ListOfGuid>', bid, valuerank=True)
        extra = [("i=60003", f"ns=1;i={self.node_by_binding[b]}", True)
                 for b, _m in spec["extends"] if b in self.node_by_binding]
        if extra:
            # append HasBaseBinding references onto the binding node's reference block
            self._append_refs(bid, extra)
        # delta fields are this binding's OWN -> no SourceScenarioBindingClassId
        for fn, path, kind in spec["delta"]:
            self.bound_item(bid, spec["scenario"], spec["target"], fn, path, kind)
        # override fields refine an inherited field -> carry the overridden base's class as provenance
        for fn, path, kind, base_name in spec.get("overrides", []):
            b = BASE_BINDINGS[base_name]
            self.bound_item(bid, spec["scenario"], spec["target"], fn, path, kind,
                            prov=class_id(b["scenario"], b["target"]))

    def _append_refs(self, nid, refs):
        marker = f'  <UAObject NodeId="ns=1;i={nid}" '
        for i, line in enumerate(self.out):
            if line.startswith(marker):
                # find this node's </References> and inject before it
                for j in range(i, len(self.out)):
                    if self.out[j].strip() == "</References>":
                        inj = [f'      <Reference ReferenceType="{rt}"'
                               f'{"" if fwd else " IsForward=\"false\""}>{tgt}</Reference>'
                               for rt, tgt, fwd in refs]
                        self.out[j:j] = inj
                        return

    def document(self):
        cont = self._id()
        self._open("UAObject", cont, "1:ExampleFacetBindings")
        self._refs([("i=40", f"i={T_BINDINGS}", True),
                    ("i=35", "i=85", False)])   # Organizes from Objects folder (illustrative)
        self.out.append('  </UAObject>')
        gid = self._id()
        self._open("UAObject", gid, "1:FacetDemo", cont)
        self._refs([("i=40", f"i={T_GROUP}", True),
                    ("i=47", f"ns=1;i={cont}", False)])
        self.out.append('  </UAObject>')
        self.prop("CompanionSpecificationUri", "i=12",
                  f'<uax:String {U}>{sx.escape(BASE)}</uax:String>', gid)
        self.prop("ModelNamespaceUris", "i=12",
                  f'<uax:ListOfString {U}><uax:String>{sx.escape(BASE)}</uax:String>'
                  f'</uax:ListOfString>', gid, valuerank=True)
        for name in BASE_BINDINGS:
            self.base_binding(gid, name)
        for name in DERIVED_BINDINGS:
            self.derived_binding(gid, name)
        header = ['<?xml version="1.0" encoding="utf-8"?>',
                  '<!-- Facets: illustrative overlay for the Scenario Bindings '
                  'inheritance/composition example. PROVISIONAL. -->',
                  '<UANodeSet xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" '
                  'xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
                  '  <NamespaceUris>',
                  f'    <Uri>{EX}</Uri>', f'    <Uri>{BASE}</Uri>',
                  '  </NamespaceUris>', '  <Models>',
                  f'    <Model ModelUri="{EX}" Version="0.1.0" '
                  'PublicationDate="2026-07-01T00:00:00Z" />', '  </Models>', '  <Aliases>',
                  '    <Alias Alias="Int32">i=6</Alias>',
                  '    <Alias Alias="Guid">i=14</Alias>',
                  '    <Alias Alias="String">i=12</Alias>',
                  '    <Alias Alias="RelativePath">i=540</Alias>',
                  '    <Alias Alias="HasComponent">i=47</Alias>',
                  '    <Alias Alias="HasProperty">i=46</Alias>',
                  '    <Alias Alias="Organizes">i=35</Alias>',
                  '    <Alias Alias="HasTypeDefinition">i=40</Alias>',
                  '    <Alias Alias="HasBaseBinding">i=60003</Alias>',
                  '  </Aliases>']
        return "\n".join(header) + "\n" + "\n".join(self.out) + "\n</UANodeSet>\n"


# ===========================================================================
# Addendum
# ===========================================================================
def guid_short(g):
    return f"`{str(g)[:8]}…`"


def emit_addendum(db):
    L = []
    A = L.append
    A("# OPC UA — Scenario Bindings — Facets & Inheritance Addendum")
    A("")
    A("*Non-normative. Companion to the base specification, section “Binding inheritance and "
      "facet composition” (§5.12). Generated by `build_facets_example.py` from the self-contained "
      "`Opc.Ua.FacetDemo.NodeSet2.xml` model.*")
    A("")
    A("## 1. The model")
    A("")
    A("A `MachineType` reuses base-facet scenario bindings across **all three** OPC UA "
      "composition axes, instead of restating their fields:")
    A("")
    A("- **subtype** — `MachineType` *is-a* `DeviceType`, so it inherits the **Device "
      "Observability** binding;")
    A("- **AddIn** — `MachineType` *composes* a `Location` block (`HasAddIn` → "
      "`LocationAddInType`), so it composes the **Location Observability** binding;")
    A("- **interface** — `MachineType` *implements* `IMaintenanceFacetType` (`HasInterface`), so "
      "it inherits the **Maintenance** binding.")
    A("")
    A("```mermaid")
    A("classDiagram")
    A("  class DeviceType")
    A("  class LocationAddInType")
    A("  class IMaintenanceFacetType {")
    A("    <<interface>>")
    A("  }")
    A("  class MachineType")
    A("  DeviceType <|-- MachineType : HasSubtype")
    A("  MachineType --> LocationAddInType : HasAddIn (Location)")
    A("  MachineType ..|> IMaintenanceFacetType : HasInterface")
    A("```")
    A("")
    A("## 2. Base facet bindings")
    A("")
    A("Each facet defines its scenario binding **once**, on its own type:")
    A("")
    A("| Binding | Defined on (axis) | Scenario | `DataSetClassId` | Fields |")
    A("|---|---|---|---|---|")
    for name, b in BASE_BINDINGS.items():
        cid = class_id(b["scenario"], b["target"])
        scen = b["scenario"].rsplit("/", 1)[-1]
        fields = ", ".join(f"`{fn}`" for fn, _p, _k in b["items"])
        A(f"| **{name}** | `{b['target']}` — {b['axis']} | {scen} | {guid_short(cid)} | {fields} |")
    A("")
    A("## 3. Derived bindings — delta only")
    A("")
    A("A derived binding lists **only its added (delta) fields** and references the base classes "
      "it builds on via `BaseDataSetClassIds` (and, where the base node is local, `HasBaseBinding`). "
      "It never restates or removes an inherited field, so its DataSet is always a **superset** of "
      "each base.")
    A("")
    A("| Derived binding | Scenario | Own `DataSetClassId` | Delta fields | `BaseDataSetClassIds` |")
    A("|---|---|---|---|---|")
    for name, d in DERIVED_BINDINGS.items():
        cid = class_id(d["scenario"], d["target"])
        scen = d["scenario"].rsplit("/", 1)[-1]
        delta = ", ".join(f"`{fn}`" for fn, _p, _k in d["delta"]) or "*(none — pure inheritance)*"
        if d.get("overrides"):
            delta += " · overrides " + ", ".join(f"`{o[0]}`" for o in d["overrides"])
        bases = ", ".join(guid_short(class_id(BASE_BINDINGS[b]["scenario"],
                                              BASE_BINDINGS[b]["target"]))
                          for b, _m in d["extends"])
        A(f"| **{name}** | {scen} | {guid_short(cid)} | {delta} | {bases} |")
    A("")
    A("## 4. What the bridge produces — the composed DataSets")
    A("")
    A("A bridge composes the effective DataSet for `MachineType` + a scenario by **unioning** the "
      "bindings reachable via subtype, `HasAddIn` and `HasInterface` (override by `FieldName`), "
      "re-rooting each base facet's BrowsePaths under its mount point (the AddIn is mounted at "
      "`/Location`), and tagging every field with the `SourceScenarioBindingClassId` of the base "
      "binding it came from. The composed DataSet keeps `MachineType`'s own `DataSetClassId` and "
      "advertises the contributing base classes in `BaseDataSetClassIds`.")
    for name in DERIVED_BINDINGS:
        own, fields = compose(name)
        d = DERIVED_BINDINGS[name]
        scen = d["scenario"].rsplit("/", 1)[-1]
        A("")
        A(f"### 4.{list(DERIVED_BINDINGS).index(name)+1} `{name}` — {scen} DataSet "
          f"({len(fields)} fields, class {guid_short(own)})")
        A("")
        A("| Field | Resolved BrowsePath (on a Machine instance) | From facet | Provenance "
          "`SourceScenarioBindingClassId` | Note |")
        A("|---|---|---|---|---|")
        for fn, path, prov, src, overridden in fields:
            note = ("overrides base field" if overridden
                    else ("own field" if src == name else "inherited"))
            A(f"| `{fn}` | `{path}` | {src} | {guid_short(prov) if prov else '—'} | {note} |")
    A("")
    A("## 5. Facet-scoped subset recognition")
    A("")
    A("A semantics-agnostic subscriber that understands only a **base facet** recognises the base "
      "`DataSetClassId` in the composed DataSet's `BaseDataSetClassIds` and consumes exactly the "
      "fields tagged with that class in `SourceScenarioBindingClassId` — without understanding "
      "`MachineType`:")
    A("")
    own, machine_fields = compose("MachineObservability")
    for base_name in ("DeviceObservability", "LocationObservability"):
        b = BASE_BINDINGS[base_name]
        bcls = class_id(b["scenario"], b["target"])
        subset = [fn for fn, _p, prov, _s, _o in machine_fields if prov == bcls]
        A(f"- A **{base_name}** subscriber (knows {guid_short(bcls)}) selects "
          f"{len(subset)} of {len(machine_fields)} fields: " + ", ".join(f"`{f}`" for f in subset) + ".")
    A(f"- A subscriber that understands the full `MachineObservability` class "
      f"({guid_short(own)}) consumes all {len(machine_fields)} fields.")
    A("")
    A("## 6. Where the binding nodes live")
    A("")
    A("`Opc.Ua.Facets.ScenarioBinding.NodeSet2.xml` in this folder shows the four base bindings "
      "and the two derived bindings under one `ScenarioBindingGroup` (`FacetDemo`) for readability. "
      "In a real Server each facet's binding is exposed on that facet type's own `ScenarioBindings` "
      "container (Device on `DeviceType`, Location on `LocationAddInType`, Maintenance on "
      "`IMaintenanceFacetType`); a `MachineType` instance's container exposes the derived bindings, "
      "which the Server/bridge composes with the inherited/AddIn/interface bindings at resolve time "
      "per §5.12. NodeIds and the example namespace are provisional.")
    A("")
    return "\n".join(L) + "\n"


def main():
    db = NodeSetDB()
    db.load(os.path.join(HERE, "Opc.Ua.FacetDemo.NodeSet2.xml"))
    em = Emit()
    xml = em.document()
    open(os.path.join(HERE, "Opc.Ua.Facets.ScenarioBinding.NodeSet2.xml"), "w",
         encoding="utf-8", newline="\n").write(xml)
    open(os.path.join(HERE, "OPC-UA-Facets-Scenario-Bindings-Addendum.md"), "w",
         encoding="utf-8", newline="\n").write(emit_addendum(db))
    n = em.nid - 5000
    print(f"Facets: {len(BASE_BINDINGS)} base + {len(DERIVED_BINDINGS)} derived bindings, "
          f"{n} nodes emitted")


if __name__ == "__main__":
    main()
