#!/usr/bin/env python3
"""Emit a tiny, self-contained example companion model, `Opc.Ua.FacetDemo.NodeSet2.xml`,
used only to demonstrate binding inheritance & facet composition (§5.12 of the base spec).

It defines four binding targets exercising all three OPC UA composition axes:
  * DeviceType            - a base ObjectType facet (Manufacturer, SerialNumber, DeviceHealth)
  * LocationAddInType     - a reusable structural AddIn (Latitude, Longitude, Altitude)
  * IMaintenanceFacetType - an Interface (contract) facet (LastMaintenanceDate)
  * MachineType           - is-a DeviceType, composes a Location AddIn (HasAddIn) and
                            implements IMaintenanceFacetType (HasInterface); adds SpindleSpeed,
                            AxisLoad. So a MachineType instance inherits/derives bindings along
                            subtype + AddIn + interface at once.

Deterministic; regenerate with `python build_facetdemo.py`.
"""

NSURI = "http://opcfoundation.org/UA/FacetDemo/"
OUT = "Opc.Ua.FacetDemo.NodeSet2.xml"

# base (ns0) ids
BaseObjectType, BaseDataVariableType, PropertyType = 58, 63, 68
BaseInterfaceType = 17602
HasSubtype, HasTypeDefinition, HasModellingRule = 45, 40, 37
HasProperty, HasComponent, HasInterface, HasAddIn = 46, 47, 17603, 17604
Mandatory = 78
String, Double, DateTime, Int32 = 12, 11, 13, 6

LINES = []


def _refs(refs):
    LINES.append("    <References>")
    for rt, tgt, fwd in refs:
        f = "" if fwd else ' IsForward="false"'
        LINES.append(f'      <Reference ReferenceType="{rt}"{f}>{tgt}</Reference>')
    LINES.append("    </References>")


def _ref(nid):
    """Format a node id: FacetDemo ids (1000-1099) are ns=1, base UA ids are ns0."""
    return f"ns=1;i={nid}" if 1000 <= nid < 1100 else f"i={nid}"


def obj_type(nid, name, base, abstract=False, refs=()):
    a = ' IsAbstract="true"' if abstract else ""
    LINES.append(f'  <UAObjectType NodeId="ns=1;i={nid}" BrowseName="1:{name}"{a}>')
    LINES.append(f"    <DisplayName>{name}</DisplayName>")
    # HasSubtype (inverse) MUST be first so validators register the type hierarchy
    _refs([(f"i={HasSubtype}", _ref(base), False)] + list(refs))
    LINES.append("  </UAObjectType>")


def member_var(nid, name, parent, datatype, reftype=HasComponent,
               typedef=BaseDataVariableType):
    LINES.append(f'  <UAVariable NodeId="ns=1;i={nid}" BrowseName="1:{name}" '
                 f'ParentNodeId="ns=1;i={parent}" DataType="i={datatype}">')
    LINES.append(f"    <DisplayName>{name}</DisplayName>")
    # HasModellingRule MUST be first so validators register the modelling rule
    _refs([(f"i={HasModellingRule}", f"i={Mandatory}", True),
           (f"i={HasTypeDefinition}", f"i={typedef}", True),
           (f"i={reftype}", f"ns=1;i={parent}", False)])
    LINES.append("  </UAVariable>")


def member_prop(nid, name, parent, datatype):
    member_var(nid, name, parent, datatype, reftype=HasProperty, typedef=PropertyType)


def addin_obj(nid, name, parent, typedef):
    LINES.append(f'  <UAObject NodeId="ns=1;i={nid}" BrowseName="1:{name}" '
                 f'ParentNodeId="ns=1;i={parent}">')
    LINES.append(f"    <DisplayName>{name}</DisplayName>")
    _refs([(f"i={HasModellingRule}", f"i={Mandatory}", True),
           (f"i={HasTypeDefinition}", f"ns=1;i={typedef}", True),
           (f"i={HasAddIn}", f"ns=1;i={parent}", False)])
    LINES.append("  </UAObject>")


# --- DeviceType (subtype base facet) ---------------------------------------
obj_type(1001, "DeviceType", BaseObjectType, refs=[
    (f"i={HasProperty}", "ns=1;i=1002", True),
    (f"i={HasProperty}", "ns=1;i=1003", True),
    (f"i={HasComponent}", "ns=1;i=1004", True)])
member_prop(1002, "Manufacturer", 1001, String)
member_prop(1003, "SerialNumber", 1001, String)
member_var(1004, "DeviceHealth", 1001, Int32)

# --- LocationAddInType (structural AddIn facet) ----------------------------
obj_type(1010, "LocationAddInType", BaseObjectType, refs=[
    (f"i={HasComponent}", "ns=1;i=1011", True),
    (f"i={HasComponent}", "ns=1;i=1012", True),
    (f"i={HasComponent}", "ns=1;i=1013", True)])
member_var(1011, "Latitude", 1010, Double)
member_var(1012, "Longitude", 1010, Double)
member_var(1013, "Altitude", 1010, Double)

# --- IMaintenanceFacetType (interface/contract facet) ----------------------
obj_type(1020, "IMaintenanceFacetType", BaseInterfaceType, abstract=True, refs=[
    (f"i={HasProperty}", "ns=1;i=1021", True)])
member_prop(1021, "LastMaintenanceDate", 1020, DateTime)

# --- MachineType (is-a Device + Location AddIn + IMaintenance interface) ----
obj_type(1030, "MachineType", 1001, refs=[
    (f"i={HasComponent}", "ns=1;i=1031", True),
    (f"i={HasComponent}", "ns=1;i=1032", True),
    (f"i={HasAddIn}", "ns=1;i=1033", True),
    (f"i={HasInterface}", "ns=1;i=1020", True)])
member_var(1031, "SpindleSpeed", 1030, Double)
member_var(1032, "AxisLoad", 1030, Double)
addin_obj(1033, "Location", 1030, 1010)

HEADER = f'''<?xml version="1.0" encoding="utf-8"?>
<!-- FacetDemo: a minimal illustrative companion model for the Scenario Bindings
     inheritance/facet-composition example. PROVISIONAL, non-normative. -->
<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">
  <NamespaceUris>
    <Uri>{NSURI}</Uri>
  </NamespaceUris>
  <Models>
    <Model ModelUri="{NSURI}" Version="1.0.0" PublicationDate="2026-07-01T00:00:00Z">
      <RequiredModel ModelUri="http://opcfoundation.org/UA/" Version="1.05.0" PublicationDate="2023-12-15T00:00:00Z" />
    </Model>
  </Models>
  <Aliases>
    <Alias Alias="Int32">i=6</Alias>
    <Alias Alias="Double">i=11</Alias>
    <Alias Alias="String">i=12</Alias>
    <Alias Alias="DateTime">i=13</Alias>
    <Alias Alias="HasModellingRule">i=37</Alias>
    <Alias Alias="HasTypeDefinition">i=40</Alias>
    <Alias Alias="HasSubtype">i=45</Alias>
    <Alias Alias="HasProperty">i=46</Alias>
    <Alias Alias="HasComponent">i=47</Alias>
    <Alias Alias="HasInterface">i=17603</Alias>
    <Alias Alias="HasAddIn">i=17604</Alias>
  </Aliases>
'''

with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(HEADER + "\n".join(LINES) + "\n</UANodeSet>\n")
print(f"wrote {OUT}: {len(LINES)} lines")
