#!/usr/bin/env python3
"""
Generator for the OPC UA Companion Specification for Generators (GenSets).

Emits two artifacts that are guaranteed to stay consistent with each other:
  * Opc.Ua.Generators.NodeSet2.xml  - the machine-readable information model
  * Opc.Ua.Generators.NodeIds.csv   - the numeric NodeId assignments

The model is hand-authored here as data. Types get stable NodeIds; instance
declarations (members), enum strings, method arguments, state-machine states
and transitions receive sequential NodeIds from a dedicated range.

Namespace layout inside the NodeSet:
    index 0 (implicit) : http://opcfoundation.org/UA/            (Core)
    index 1            : http://opcfoundation.org/UA/Generators/ (this spec)
    index 2            : http://opcfoundation.org/UA/DI/         (Devices)
    index 3            : http://opcfoundation.org/UA/Machinery/  (Machinery)
"""
from __future__ import annotations
import os
import xml.sax.saxutils as sx

# ---------------------------------------------------------------------------
# Namespace indices as they appear in this NodeSet
# ---------------------------------------------------------------------------
GEN = 1   # Generators (own)
DI = 2    # Devices
MC = 3    # Machinery

# ---------------------------------------------------------------------------
# Well-known base NodeIds (verified against UA-Nodeset)
# ---------------------------------------------------------------------------
# Core UA reference types
HasComponent = "i=47"
HasProperty = "i=46"
HasSubtype = "i=45"
Organizes = "i=35"
HasTypeDefinition = "i=40"
HasModellingRule = "i=37"
HasInterface = "i=17603"
HasAddIn = "i=17604"
HasEncoding = "i=38"
GeneratesEvent = "i=41"
FromState = "i=51"
ToState = "i=52"

# Modelling rules (targets of HasModellingRule)
MR_Mandatory = "i=78"
MR_Optional = "i=80"
MR_OptionalPlaceholder = "i=11508"
MR_MandatoryPlaceholder = "i=11510"

# Core type definitions
BaseObjectType = "i=58"
FolderType = "i=61"
BaseDataVariableType = "i=63"
PropertyType = "i=68"
BaseInterfaceType = "i=17602"
FiniteStateMachineType = "i=2771"
StateType = "i=2307"
InitialStateType = "i=2309"
TransitionType = "i=2310"
AnalogUnitType = "i=17497"
DataTypeEncodingType = "i=76"

# Core data types
Boolean = "i=1"
Byte = "i=3"
UInt16 = "i=5"
UInt32 = "i=7"
Int32 = "i=6"
Float = "i=10"
Double = "i=11"
String = "i=12"
DateTime = "i=13"
LocalizedText = "i=21"
Structure = "i=22"
Enumeration = "i=29"
Duration = "i=290"
Argument = "i=296"
Range = "i=884"
EUInformation = "i=887"

# DI (ns=2)
DI_TopologyElementType = f"ns={DI};i=1001"
DI_DeviceType = f"ns={DI};i=1002"
DI_ComponentType = f"ns={DI};i=15063"
DI_IVendorNameplateType = f"ns={DI};i=15035"

# Machinery (ns=3)
MC_MachineryItemState_SMT = f"ns={MC};i=1002"
MC_MachineIdentificationType = f"ns={MC};i=1012"
MC_MachineryOperationMode_SMT = f"ns={MC};i=1008"

# Alarms (Part 9, ns=0)
OffNormalAlarmType = "i=10637"

# ---------------------------------------------------------------------------
# Node registry
# ---------------------------------------------------------------------------
class Node:
    __slots__ = ("nid", "cls", "bns", "bname", "symbolic", "display", "desc",
                 "parent", "attrs", "refs", "category", "definition", "value",
                 "abstract")

    def __init__(self, nid, cls, bns, bname, symbolic, display, desc, parent,
                 attrs, category, abstract):
        self.nid = nid
        self.cls = cls
        self.bns = bns
        self.bname = bname
        self.symbolic = symbolic
        self.display = display
        self.desc = desc
        self.parent = parent
        self.attrs = attrs or {}
        self.refs = []            # list of (reftype, target, forward)
        self.category = category
        self.definition = None    # raw xml for <Definition>
        self.value = None         # raw xml for <Value>
        self.abstract = abstract


NODES = {}
ORDER = []
_next_member = [6001]


def _mid():
    v = _next_member[0]
    _next_member[0] += 1
    return v


def add(nid, cls, bname, symbolic, display=None, desc=None, parent=None,
        attrs=None, category=None, bns=GEN, abstract=False):
    n = Node(nid, cls, bns, bname, symbolic, display or bname, desc, parent,
             attrs, category, abstract)
    NODES[nid] = n
    ORDER.append(nid)
    return n


def ref(nid, reftype, target, forward=True):
    NODES[nid].refs.append((reftype, target, forward))


def T(nid):
    """Format a NodeId in this (Generators) namespace."""
    return f"ns={GEN};i={nid}"


# ---------------------------------------------------------------------------
# High-level builders
# ---------------------------------------------------------------------------
def object_type(nid, name, base, desc, category, abstract=False):
    add(nid, "UAObjectType", name, name, desc=desc, category=category,
        abstract=abstract)
    ref(nid, HasSubtype, base, forward=False)
    return nid


def _member_var(owner, owner_sym, name, datatype, typedef, rule, reftype, desc,
                valuerank="-1", array=None, bns=GEN):
    nid = _mid()
    attrs = {"DataType": datatype, "ValueRank": valuerank}
    if array is not None:
        attrs["ArrayDimensions"] = str(array)
    add(nid, "UAVariable", name, f"{owner_sym}_{name}", desc=desc,
        parent=T(owner), attrs=attrs, bns=bns)
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid


def analog(owner, owner_sym, name, unit, desc, rule=MR_Optional):
    full = f"{desc} EngineeringUnits: {unit}."
    nid = _member_var(owner, owner_sym, name, Double, AnalogUnitType, rule,
                      HasComponent, full)
    _engineering_units(nid, f"{owner_sym}_{name}", unit)
    return nid


# UNECE Rec 20 unit codes (UNECECode, UnitId, DisplayName, Description)
UNITS = {
    "rpm": ("RPM", 5394509, "r/min", "revolutions per minute"),
    "%": ("P1", 20529, "%", "percent"),
    "kPa": ("KPA", 4935745, "kPa", "kilopascal"),
    "degC": ("CEL", 4408652, "\u00b0C", "degree Celsius"),
    "L/h": ("E32", 4535090, "l/h", "litre per hour"),
    "V": ("VLT", 5655636, "V", "volt"),
    "A": ("AMP", 4279632, "A", "ampere"),
    "kW": ("KWT", 4937556, "kW", "kilowatt"),
    "kvar": ("KVR", 4937298, "kvar", "kilovar"),
    "kVA": ("KVA", 4937281, "kV\u00b7A", "kilovolt ampere"),
    "Hz": ("HTZ", 4740186, "Hz", "hertz"),
    "h": ("HUR", 4740434, "h", "hour"),
    "kW.h": ("KWH", 4937544, "kW\u00b7h", "kilowatt hour"),
    "l": ("LTR", 5002322, "l", "litre"),
    "m": ("MTR", 5067858, "m", "metre"),
    "deg": ("DD", 17476, "\u00b0", "degree"),
}
_UN_NS = "http://www.opcfoundation.org/UA/units/un/cefact"


def _engineering_units(parent_nid, parent_sym, unit):
    code, uid, disp, descr = UNITS.get(unit, (None, 0, unit, unit))
    nid = _mid()
    add(nid, "UAVariable", "EngineeringUnits", f"{parent_sym}_EngineeringUnits",
        parent=T(parent_nid), attrs={"DataType": EUInformation}, bns=0)
    ref(nid, HasModellingRule, MR_Mandatory)
    ref(nid, HasTypeDefinition, PropertyType)
    ref(nid, HasProperty, T(parent_nid), forward=False)
    ref(parent_nid, HasProperty, T(nid))
    NODES[nid].value = (
        '<Value><ExtensionObject xmlns="http://opcfoundation.org/UA/2008/02/Types.xsd">'
        '<TypeId><Identifier>i=889</Identifier></TypeId>'
        '<Body><EUInformation>'
        f'<NamespaceUri>{_UN_NS}</NamespaceUri>'
        f'<UnitId>{uid}</UnitId>'
        f'<DisplayName><Text>{sx.escape(disp)}</Text></DisplayName>'
        f'<Description><Text>{sx.escape(descr)}</Text></Description>'
        '</EUInformation></Body></ExtensionObject></Value>')
    return nid


def comp_var(owner, owner_sym, name, datatype, desc, rule=MR_Optional,
             typedef=BaseDataVariableType, valuerank="-1", array=None):
    return _member_var(owner, owner_sym, name, datatype, typedef, rule,
                       HasComponent, desc, valuerank, array)


def prop_var(owner, owner_sym, name, datatype, desc, rule=MR_Optional,
             valuerank="-1", array=None):
    return _member_var(owner, owner_sym, name, datatype, PropertyType, rule,
                       HasProperty, desc, valuerank, array)


def obj_member(owner, owner_sym, name, typedef, desc, rule=MR_Optional,
               reftype=HasComponent, bns=GEN):
    nid = _mid()
    add(nid, "UAObject", name, f"{owner_sym}_{name}", desc=desc,
        parent=T(owner), bns=bns)
    ref(nid, HasModellingRule, rule)
    ref(nid, HasTypeDefinition, typedef)
    ref(nid, reftype, T(owner), forward=False)
    ref(owner, reftype, T(nid))
    return nid


def method(owner, owner_sym, name, desc, rule=MR_Optional, inargs=None,
           outargs=None):
    nid = _mid()
    add(nid, "UAMethod", name, f"{owner_sym}_{name}", desc=desc,
        parent=T(owner))
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
    add(nid, "UAVariable", bname, f"{method_sym}_{bname}",
        parent=T(method_nid),
        attrs={"DataType": Argument, "ValueRank": "1",
               "ArrayDimensions": str(len(args))}, bns=0)
    ref(nid, HasModellingRule, MR_Mandatory)
    ref(nid, HasTypeDefinition, PropertyType)
    ref(nid, HasProperty, T(method_nid), forward=False)
    ref(method_nid, HasProperty, T(nid))
    parts = ['<Value>',
             '<ListOfExtensionObject xmlns="http://opcfoundation.org/UA/2008/02/Types.xsd">']
    for (aname, adtype, adesc) in args:
        parts.append("<ExtensionObject><TypeId><Identifier>i=297</Identifier></TypeId>")
        parts.append("<Body><Argument>")
        parts.append(f"<Name>{sx.escape(aname)}</Name>")
        parts.append(f"<DataType><Identifier>{adtype}</Identifier></DataType>")
        parts.append("<ValueRank>-1</ValueRank><ArrayDimensions/>")
        if adesc:
            parts.append(f"<Description><Text>{sx.escape(adesc)}</Text></Description>")
        parts.append("</Argument></Body></ExtensionObject>")
    parts.append("</ListOfExtensionObject></Value>")
    NODES[nid].value = "".join(parts)
    return nid


def enum_type(nid, name, desc, category, fields):
    """fields: list of (fieldname, value_int, description)."""
    add(nid, "UADataType", name, name, desc=desc, category=category)
    ref(nid, HasSubtype, Enumeration, forward=False)
    dparts = [f'<Definition Name="{GEN}:{name}">']
    for (fname, val, fdesc) in fields:
        if fdesc:
            dparts.append(f'<Field Name="{sx.escape(fname)}" Value="{val}">')
            dparts.append(f'<Description>{sx.escape(fdesc)}</Description></Field>')
        else:
            dparts.append(f'<Field Name="{sx.escape(fname)}" Value="{val}"/>')
    dparts.append("</Definition>")
    NODES[nid].definition = "".join(dparts)
    es = nid + 900  # EnumStrings id convention: datatype id + 900
    ref(nid, HasProperty, T(es))
    add(es, "UAVariable", "EnumStrings", f"{name}_EnumStrings", parent=T(nid),
        attrs={"DataType": LocalizedText, "ValueRank": "1",
               "ArrayDimensions": str(len(fields))}, bns=0)
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
    """fields: list of (fieldname, datatype_id, valuerank, description)."""
    add(nid, "UADataType", name, name, desc=desc, category=category)
    ref(nid, HasSubtype, Structure, forward=False)
    dparts = [f'<Definition Name="{GEN}:{name}">']
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
        add(enc, "UAObject", enc_bname, f"{name}_{enc_sym}", parent=T(nid),
            bns=0)
        ref(enc, HasTypeDefinition, DataTypeEncodingType)
        ref(enc, HasEncoding, T(nid), forward=False)
        ref(nid, HasEncoding, T(enc))
    return nid


def state(sm_nid, sm_sym, name, number, initial=False):
    nid = _mid()
    add(nid, "UAObject", name, f"{sm_sym}_{name}",
        desc=f"State '{name}' of the generator set operating state machine.",
        parent=T(sm_nid))
    ref(nid, HasTypeDefinition, InitialStateType if initial else StateType)
    ref(nid, HasComponent, T(sm_nid), forward=False)
    ref(sm_nid, HasComponent, T(nid))
    snum = _mid()
    add(snum, "UAVariable", "StateNumber", f"{sm_sym}_{name}_StateNumber",
        parent=T(nid), attrs={"DataType": UInt32}, bns=0)
    ref(snum, HasModellingRule, MR_Mandatory)
    ref(snum, HasTypeDefinition, PropertyType)
    ref(snum, HasProperty, T(nid), forward=False)
    ref(nid, HasProperty, T(snum))
    NODES[snum].value = ('<Value><uax:UInt32 '
                         'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd">'
                         f'{number}</uax:UInt32></Value>')
    return nid


def transition(sm_nid, sm_sym, name, number, from_nid, to_nid):
    nid = _mid()
    add(nid, "UAObject", name, f"{sm_sym}_{name}",
        desc=f"Transition '{name}'.", parent=T(sm_nid))
    ref(nid, HasTypeDefinition, TransitionType)
    ref(nid, HasComponent, T(sm_nid), forward=False)
    ref(sm_nid, HasComponent, T(nid))
    ref(nid, FromState, T(from_nid))
    ref(nid, ToState, T(to_nid))
    tnum = _mid()
    add(tnum, "UAVariable", "TransitionNumber",
        f"{sm_sym}_{name}_TransitionNumber", parent=T(nid),
        attrs={"DataType": UInt32}, bns=0)
    ref(tnum, HasModellingRule, MR_Mandatory)
    ref(tnum, HasTypeDefinition, PropertyType)
    ref(tnum, HasProperty, T(nid), forward=False)
    ref(nid, HasProperty, T(tnum))
    NODES[tnum].value = ('<Value><uax:UInt32 '
                         'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd">'
                         f'{number}</uax:UInt32></Value>')
    return nid


# ===========================================================================
# ============================  MODEL DEFINITION  ===========================
# ===========================================================================

# --- Enumerations ----------------------------------------------------------
CAT_EN = "Generators DataTypes"

enum_type(3001, "GeneratorOperatingModeEnum",
          "Selector mode of the generator set control panel.",
          CAT_EN, [
    ("Off", 0, "Control is off; the set will not start automatically or manually."),
    ("Manual", 1, "Manual/hand mode; the set runs on operator command."),
    ("Auto", 2, "Automatic mode; the set starts/stops on remote or utility-failure signals."),
    ("Test", 3, "Test mode; a commanded test run, optionally with load."),
    ("Exercise", 4, "Scheduled exercise/self-test run."),
    ("RemoteStart", 5, "Started by a remote start signal."),
    ("Maintenance", 6, "Maintenance/service mode; starting is inhibited or restricted."),
    ("Lockout", 7, "Locked out; starting is blocked until reset."),
])

enum_type(3002, "FuelTypeEnum",
          "Primary fuel of the generator set.", CAT_EN, [
    ("Diesel", 0, None), ("NaturalGas", 1, None), ("Propane", 2, None),
    ("LPG", 3, None), ("Gasoline", 4, None), ("BiFuel", 5, None),
    ("DualFuel", 6, None), ("Biodiesel", 7, None), ("HVO", 8, None),
    ("RenewableDiesel", 9, None), ("Hydrogen", 10, None), ("Biogas", 11, None),
    ("LandfillGas", 12, None), ("FieldGas", 13, None), ("Syngas", 14, None),
    ("Other", 15, None),
])

enum_type(3003, "GeneratorApplicationRatingEnum",
          "Application/duty rating per ISO 8528 plus the data-center-continuous rating.",
          CAT_EN, [
    ("EmergencyStandby", 0, "ESP: standby power at variable load, limited hours, no overload."),
    ("Prime", 1, "PRP: unlimited hours at variable load, typically 10% overload 1h/12h."),
    ("Continuous", 2, "COP: unlimited hours at constant load, no overload."),
    ("LimitedTime", 3, "LTP: limited hours per year at defined load."),
    ("DataCenterContinuous", 4, "DCC: continuous operation for data-center loads."),
])

enum_type(3004, "ElectricalConnectionEnum",
          "Winding/connection configuration of the alternator output.", CAT_EN, [
    ("Unknown", 0, None), ("Wye", 1, None), ("WyeSolidlyGrounded", 2, None),
    ("WyeResistanceGrounded", 3, None), ("WyeUngrounded", 4, None),
    ("Delta", 5, None), ("OpenDelta", 6, None), ("ZigZag", 7, None),
    ("SinglePhaseThreeWire", 8, None),
])

enum_type(3005, "ExcitationTypeEnum",
          "Excitation method of the alternator.", CAT_EN, [
    ("Unknown", 0, None), ("Shunt", 1, None),
    ("PMG", 2, "Permanent Magnet Generator - independent excitation supply."),
    ("AREP", 3, None), ("AuxiliaryWinding", 4, None), ("StaticExciter", 5, None),
])

enum_type(3006, "CoolingMethodEnum",
          "Primary cooling method of the engine.", CAT_EN, [
    ("AirCooled", 0, None), ("LiquidCooled", 1, None),
])

enum_type(3007, "AspirationEnum",
          "Air induction method of the engine.", CAT_EN, [
    ("NaturallyAspirated", 0, None), ("Turbocharged", 1, None),
    ("TurbochargedAftercooled", 2, None),
])

enum_type(3008, "EmissionsStandardEnum",
          "Emissions certification standard of the engine.", CAT_EN, [
    ("Unregulated", 0, None), ("EPATier1", 1, None), ("EPATier2", 2, None),
    ("EPATier3", 3, None), ("EPATier4Interim", 4, None),
    ("EPATier4Final", 5, None), ("EUStageIII", 6, None), ("EUStageIV", 7, None),
    ("EUStageV", 8, None), ("Other", 9, None),
])

enum_type(3009, "CanBusStateEnum",
          "State of the engine CAN bus / SAE J1939 network interface.", CAT_EN, [
    ("Offline", 0, None), ("Online", 1, None), ("ErrorWarning", 2, None),
    ("ErrorPassive", 3, None), ("BusOff", 4, None),
])

enum_type(3010, "TransferSwitchPositionEnum",
          "Contact position of an automatic transfer switch.", CAT_EN, [
    ("Unknown", 0, None), ("Source1", 1, "Connected to Source 1 (normal/utility)."),
    ("Source2", 2, "Connected to Source 2 (emergency/generator)."),
    ("Neutral", 3, "Center-off / neutral position."),
    ("InTransition", 4, None), ("BypassSource1", 5, None),
    ("BypassSource2", 6, None), ("Isolated", 7, None),
])

enum_type(3011, "TransferTransitionTypeEnum",
          "Transition method of an automatic transfer switch.", CAT_EN, [
    ("OpenTransition", 0, "Break-before-make."),
    ("DelayedTransition", 1, "Break-before-make with center-off delay."),
    ("ClosedTransition", 2, "Make-before-break; momentary paralleling."),
    ("SoftLoadTransition", 3, "Ramped, no-break transfer while paralleled."),
    ("BypassIsolation", 4, None),
])

enum_type(3012, "AtsOperatingStateEnum",
          "Operating state of an automatic transfer switch.", CAT_EN, [
    ("Unknown", 0, None), ("NormalAvailable", 1, None),
    ("EmergencyAvailable", 2, None), ("NormalConnected", 3, None),
    ("EmergencyConnected", 4, None), ("TransferPending", 5, None),
    ("Transferring", 6, None), ("RetransferPending", 7, None),
    ("Exercising", 8, None), ("Test", 9, None), ("Faulted", 10, None),
    ("Bypassed", 11, None), ("Isolated", 12, None),
])

enum_type(3013, "AlarmSeverityEnum",
          "Severity class of a generator protection event.", CAT_EN, [
    ("Info", 0, None), ("Warning", 1, None),
    ("Derate", 2, "The set continues to run at reduced output."),
    ("Shutdown", 3, "The engine is shut down."),
    ("ElectricalTrip", 4, "The generator breaker is tripped."),
    ("Lockout", 5, "The set is locked out and requires manual reset."),
    ("EmergencyStop", 6, None),
])

enum_type(3014, "GeneratorProtectionFunctionEnum",
          "Protection / fault function that raised a generator alarm.", CAT_EN, [
    ("Other", 0, None), ("LowOilPressure", 1, None), ("HighOilTemperature", 2, None),
    ("HighCoolantTemperature", 3, None), ("LowCoolantTemperature", 4, None),
    ("LowCoolantLevel", 5, None), ("HighCoolantPressure", 6, None),
    ("Overspeed", 7, None), ("Underspeed", 8, None),
    ("Overcrank", 9, "Fail to start within the crank limit."),
    ("FailToCrank", 10, None), ("StarterFailure", 11, None),
    ("LowFuelLevel", 12, None), ("CriticalLowFuel", 13, None),
    ("FuelLeak", 14, None), ("LowFuelPressure", 15, None),
    ("HighFuelPressure", 16, None), ("WaterInFuel", 17, None),
    ("FuelFilterRestriction", 18, None), ("AirFilterRestriction", 19, None),
    ("HighExhaustTemperature", 20, None), ("TurbochargerFault", 21, None),
    ("EcuFault", 22, None), ("EngineDerate", 23, None),
    ("Overvoltage", 24, None), ("Undervoltage", 25, None),
    ("Overfrequency", 26, None), ("Underfrequency", 27, None),
    ("Overload", 28, None), ("Overcurrent", 29, None),
    ("ShortCircuit", 30, None), ("GroundFault", 31, None),
    ("PhaseLoss", 32, None), ("PhaseReversal", 33, None),
    ("VoltageImbalance", 34, None), ("CurrentImbalance", 35, None),
    ("ReversePower", 36, None), ("LossOfExcitation", 37, None),
    ("Overexcitation", 38, None), ("Underexcitation", 39, None),
    ("AvrFault", 40, None), ("HighWindingTemperature", 41, None),
    ("HighBearingTemperature", 42, None), ("LowBatteryVoltage", 43, None),
    ("HighBatteryVoltage", 44, None), ("BatteryChargerFailure", 45, None),
    ("WeakBattery", 46, None), ("ControllerFault", 47, None),
    ("CommunicationLost", 48, None), ("SensorFailure", 49, None),
    ("EmergencyStop", 50, None), ("DefLevelLow", 51, None),
    ("DefQualityPoor", 52, None), ("DpfSootHigh", 53, None),
    ("RegenerationRequired", 54, None), ("AftertreatmentFault", 55, None),
    ("EnclosureHighTemperature", 56, None), ("DoorOpen", 57, None),
    ("FuelBasinLeak", 58, None), ("RadiatorFanFailure", 59, None),
    ("JacketWaterHeaterFailure", 60, None), ("AtsFailedToTransfer", 61, None),
    ("BreakerFailedToClose", 62, None), ("SynchronizationFailure", 63, None),
])

enum_type(3015, "ParallelingSystemStateEnum",
          "Operating state of a paralleling / switchgear system.", CAT_EN, [
    ("Off", 0, None), ("Standby", 1, None), ("StartSequence", 2, None),
    ("DeadBusClose", 3, None), ("Synchronizing", 4, None),
    ("Paralleling", 5, None), ("LoadSharing", 6, None), ("LoadDemand", 7, None),
    ("UtilityParallel", 8, None), ("PeakShaving", 9, None), ("BaseLoad", 10, None),
    ("LoadShed", 11, None), ("SoftUnload", 12, None), ("Cooldown", 13, None),
    ("Faulted", 14, None), ("EmergencyStop", 15, None),
    ("MaintenanceBypass", 16, None),
])

enum_type(3016, "AftertreatmentStateEnum",
          "State of the exhaust aftertreatment system.", CAT_EN, [
    ("NotEquipped", 0, None), ("Normal", 1, None), ("PassiveRegen", 2, None),
    ("ActiveRegen", 3, None), ("RegenInhibited", 4, None),
    ("RegenRequired", 5, None), ("DerateActive", 6, None), ("Faulted", 7, None),
])

enum_type(3017, "J1939LampStatusEnum",
          "SAE J1939 DM1 diagnostic lamp status (lamp state plus flash rate).", CAT_EN, [
    ("Off", 0, "The lamp is off."),
    ("On", 1, "The lamp is on (steady)."),
    ("SlowFlash", 2, "The lamp is flashing slowly."),
    ("FastFlash", 3, "The lamp is flashing fast."),
    ("NotAvailable", 4, "The lamp status is not available."),
])

# --- Structure -------------------------------------------------------------
struct_type(3050, "DiagnosticTroubleCodeType",
            "A SAE J1939 diagnostic trouble code (DTC) reported by an engine ECU.",
            CAT_EN, [
    ("Spn", UInt32, None, "Suspect Parameter Number identifying the faulty subsystem."),
    ("Fmi", Byte, None, "Failure Mode Identifier describing the type of failure."),
    ("OccurrenceCount", Byte, None, "Number of times the fault has become active."),
    ("ConversionMethod", Boolean, None, "J1939 SPN conversion method flag."),
    ("Active", Boolean, None, "TRUE while the fault is currently active (DM1)."),
    ("SourceAddress", Byte, None, "J1939 source address of the ECU that reported the code."),
    ("SourceName", String, None, "Name of the ECU/controller that reported the code."),
    ("Severity", T(3013), None, "Severity classification of the fault."),
    ("Description", String, None, "Human-readable description of the fault."),
])

# --- GeneratorIdentificationType (: MachineIdentificationType) --------------
CAT_ID = "Generators Identification"
object_type(1016, "GeneratorIdentificationType", MC_MachineIdentificationType,
            "Identification and nameplate of a generator set. Extends the Machinery "
            "MachineIdentificationType with generator-specific nameplate data.", CAT_ID)
S = "GeneratorIdentificationType"
prop_var(1016, S, "SpecificationNumber", String,
         "Vendor build/specification code that identifies the exact configuration.")
prop_var(1016, S, "ProductFamily", String,
         "Vendor product family or series to which the set belongs.")
prop_var(1016, S, "EngineModel", String, "Model designation of the prime-mover engine.")
prop_var(1016, S, "EngineSerialNumber", String, "Serial number of the prime-mover engine.")
prop_var(1016, S, "AlternatorModel", String, "Model designation of the alternator.")
prop_var(1016, S, "AlternatorSerialNumber", String, "Serial number of the alternator.")
prop_var(1016, S, "ControllerModel", String,
         "Model designation of the control panel.")
prop_var(1016, S, "FuelType", T(3002), "Primary fuel of the set.")
prop_var(1016, S, "EmissionsStandard", T(3008), "Emissions certification standard.")
analog(1016, S, "RatedRealPower", "kW", "Nameplate rated real power.")
analog(1016, S, "RatedApparentPower", "kVA", "Nameplate rated apparent power.")
analog(1016, S, "RatedVoltage", "V", "Nameplate rated line-to-line voltage.")
analog(1016, S, "RatedFrequency", "Hz", "Nameplate rated frequency.")
prop_var(1016, S, "SoundRatingAt7m", "i=11",
         "Sound pressure level at 7 m (23 ft) in dB(A).")

# --- GeneratorStateMachineType ---------------------------------------------
CAT_SM = "Generators StateMachine"
object_type(1011, "GeneratorStateMachineType", FiniteStateMachineType,
            "Finite state machine describing the operating state of a generator set: "
            "Off, Ready, Starting, Warmup, Running, Loaded, Synchronizing, Paralleled, "
            "Cooldown, Stopping, Fault and EmergencyStopped.", CAT_SM)
SM = "GeneratorStateMachineType"
st = {}
st["Off"] = state(1011, SM, "Off", 1, initial=True)
st["Ready"] = state(1011, SM, "Ready", 2)
st["Starting"] = state(1011, SM, "Starting", 3)
st["Warmup"] = state(1011, SM, "Warmup", 4)
st["Running"] = state(1011, SM, "Running", 5)
st["Loaded"] = state(1011, SM, "Loaded", 6)
st["Synchronizing"] = state(1011, SM, "Synchronizing", 7)
st["Paralleled"] = state(1011, SM, "Paralleled", 8)
st["Cooldown"] = state(1011, SM, "Cooldown", 9)
st["Stopping"] = state(1011, SM, "Stopping", 10)
st["Fault"] = state(1011, SM, "Fault", 11)
st["EmergencyStopped"] = state(1011, SM, "EmergencyStopped", 12)
_tn = [0]


def _tr(a, b):
    _tn[0] += 1
    transition(1011, SM, f"{a}To{b}", _tn[0], st[a], st[b])


for a, b in [("Off", "Ready"), ("Ready", "Starting"), ("Ready", "Off"),
             ("Starting", "Warmup"), ("Starting", "Fault"), ("Warmup", "Running"),
             ("Running", "Loaded"), ("Running", "Synchronizing"),
             ("Synchronizing", "Paralleled"), ("Synchronizing", "Running"),
             ("Paralleled", "Loaded"), ("Loaded", "Cooldown"),
             ("Running", "Cooldown"), ("Cooldown", "Stopping"),
             ("Stopping", "Off"), ("Running", "Fault"), ("Loaded", "Fault"),
             ("Paralleled", "Fault"), ("Fault", "Off"),
             ("Running", "EmergencyStopped"), ("Loaded", "EmergencyStopped"),
             ("Paralleled", "EmergencyStopped"), ("EmergencyStopped", "Off")]:
    _tr(a, b)

# --- J1939DiagnosticInterfaceType ------------------------------------------
CAT_CAN = "Generators CANbus"
object_type(1010, "J1939DiagnosticInterfaceType", BaseObjectType,
            "The engine CAN bus / SAE J1939 diagnostic interface. Surfaces the network "
            "connection parameters, J1939 lamp status and active/previously-active "
            "diagnostic trouble codes reported by the engine ECU.", CAT_CAN)
J = "J1939DiagnosticInterfaceType"
prop_var(1010, J, "ProtocolName", String,
         "Name of the diagnostic protocol, e.g. 'SAE J1939'.", rule=MR_Mandatory)
prop_var(1010, J, "NetworkName", String, "Name/identifier of the CAN network (e.g. CAN0).")
prop_var(1010, J, "SourceAddress", Byte, "J1939 source address of the engine ECU.")
prop_var(1010, J, "Baudrate", UInt32, "CAN bit rate in bit/s (typically 250000 or 500000).")
comp_var(1010, J, "BusState", T(3009), "State of the CAN bus interface.")
comp_var(1010, J, "AmberWarningLamp", T(3017), "J1939 DM1 amber warning lamp status.")
comp_var(1010, J, "RedStopLamp", T(3017), "J1939 DM1 red stop lamp status.")
comp_var(1010, J, "MalfunctionIndicatorLamp", T(3017), "J1939 DM1 malfunction indicator lamp status.")
comp_var(1010, J, "ProtectLamp", T(3017), "J1939 DM1 protect lamp status.")
comp_var(1010, J, "ActiveDiagnosticTroubleCodes", T(3050),
         "Currently active DTCs (J1939 DM1).", valuerank="1")
comp_var(1010, J, "PreviouslyActiveDiagnosticTroubleCodes", T(3050),
         "Previously active DTCs (J1939 DM2).", valuerank="1")
method(1010, J, "ClearPreviouslyActiveDtcs",
       "Clear previously active diagnostic trouble codes (J1939 DM3/DM11).")

# --- ExhaustAftertreatmentType ---------------------------------------------
CAT_COMP = "Generators Components"
object_type(1018, "ExhaustAftertreatmentType", DI_ComponentType,
            "Exhaust aftertreatment subsystem (DPF/SCR/DEF) for Tier 4 / Stage V engines.",
            CAT_COMP)
AT = "ExhaustAftertreatmentType"
comp_var(1018, AT, "AftertreatmentState", T(3016), "State of the aftertreatment system.")
analog(1018, AT, "DefLevel", "%", "Diesel Exhaust Fluid tank level. SAE J1939 SPN 1761.")
analog(1018, AT, "DefTemperature", "degC", "DEF tank temperature. SAE J1939 SPN 3031.")
analog(1018, AT, "DefQuality", "%", "DEF concentration/quality. SAE J1939 SPN 3364.")
analog(1018, AT, "DpfSootLoad", "%", "Diesel particulate filter soot load. SAE J1939 SPN 3719.")
analog(1018, AT, "DpfAshLoad", "%", "Diesel particulate filter ash load. SAE J1939 SPN 3720.")
analog(1018, AT, "ExhaustGasTemperature", "degC", "Exhaust gas temperature. SAE J1939 SPN 173.")
comp_var(1018, AT, "RegenerationRequired", Boolean, "A DPF regeneration is required.")
comp_var(1018, AT, "RegenerationInhibited", Boolean, "DPF regeneration is currently inhibited.")
method(1018, AT, "InitiateRegeneration", "Request a manual DPF regeneration.")
method(1018, AT, "InhibitRegeneration",
       "Enable or disable the inhibit of automatic regeneration.",
       inargs=[("Inhibit", Boolean, "TRUE to inhibit regeneration.")])

# --- EngineType ------------------------------------------------------------
object_type(1002, "EngineType", DI_ComponentType,
            "The prime-mover engine of a generator set. Exposes engine telemetry, "
            "typically obtained over the CAN bus / SAE J1939 interface, and identification.",
            CAT_COMP)
E = "EngineType"
analog(1002, E, "Speed", "rpm", "Engine speed. SAE J1939 SPN 190.", rule=MR_Mandatory)
analog(1002, E, "PercentLoad", "%", "Engine percent load at current speed. SAE J1939 SPN 92.")
analog(1002, E, "PercentTorque", "%", "Actual engine percent torque. SAE J1939 SPN 513.")
analog(1002, E, "OilPressure", "kPa", "Engine oil pressure. SAE J1939 SPN 100.")
analog(1002, E, "OilTemperature", "degC", "Engine oil temperature. SAE J1939 SPN 175.")
analog(1002, E, "CoolantTemperature", "degC", "Engine coolant temperature. SAE J1939 SPN 110.")
analog(1002, E, "CoolantPressure", "kPa", "Engine coolant pressure. SAE J1939 SPN 109.")
analog(1002, E, "FuelRate", "L/h", "Engine fuel consumption rate. SAE J1939 SPN 183.")
analog(1002, E, "FuelTemperature", "degC", "Engine fuel temperature. SAE J1939 SPN 174.")
analog(1002, E, "IntakeManifoldPressure", "kPa", "Intake manifold (boost) pressure. SAE J1939 SPN 102.")
analog(1002, E, "IntakeManifoldTemperature", "degC", "Intake manifold temperature. SAE J1939 SPN 105.")
analog(1002, E, "ExhaustGasTemperature", "degC", "Exhaust gas temperature. SAE J1939 SPN 173.")
analog(1002, E, "BarometricPressure", "kPa", "Ambient barometric pressure. SAE J1939 SPN 108.")
analog(1002, E, "EngineHours", "h", "Total engine run hours. SAE J1939 SPN 247.", rule=MR_Mandatory)
comp_var(1002, E, "NumberOfStarts", UInt32, "Total number of engine start attempts.")
comp_var(1002, E, "Aspiration", T(3007), "Air induction method of the engine.")
analog(1002, E, "Displacement", "l", "Engine displacement.")
comp_var(1002, E, "CylinderCount", UInt16, "Number of cylinders.")
analog(1002, E, "RatedSpeed", "rpm", "Rated (synchronous) engine speed, e.g. 1500 or 1800 rpm.")
obj_member(1002, E, "CanInterface", T(1010),
           "CAN bus / SAE J1939 diagnostic interface of the engine ECU.")
obj_member(1002, E, "Aftertreatment", T(1018),
           "Exhaust aftertreatment subsystem, when equipped.")

# --- AlternatorPhaseType ---------------------------------------------------
object_type(1004, "AlternatorPhaseType", BaseObjectType,
            "Per-phase electrical measurements of the alternator output.", CAT_COMP)
PH = "AlternatorPhaseType"
analog(1004, PH, "LineToNeutralVoltage", "V", "Phase (line-to-neutral) RMS voltage.")
analog(1004, PH, "LineToLineVoltage", "V", "Line-to-line RMS voltage referenced to the next phase.")
analog(1004, PH, "Current", "A", "Phase RMS current.", rule=MR_Mandatory)
analog(1004, PH, "RealPower", "kW", "Per-phase real power.")
analog(1004, PH, "ReactivePower", "kvar", "Per-phase reactive power.")
analog(1004, PH, "ApparentPower", "kVA", "Per-phase apparent power.")
comp_var(1004, PH, "PowerFactor", Double, "Per-phase power factor (-1..1).")

# --- AlternatorType --------------------------------------------------------
object_type(1003, "AlternatorType", DI_ComponentType,
            "The alternator (generator end) that converts mechanical power into AC "
            "electrical power. Exposes aggregate and per-phase electrical measurements.",
            CAT_COMP)
A = "AlternatorType"
analog(1003, A, "Frequency", "Hz", "Output frequency.", rule=MR_Mandatory)
analog(1003, A, "AverageLineToLineVoltage", "V", "Average line-to-line RMS voltage.")
analog(1003, A, "AverageLineToNeutralVoltage", "V", "Average line-to-neutral RMS voltage.")
analog(1003, A, "AverageCurrent", "A", "Average line RMS current.")
analog(1003, A, "TotalRealPower", "kW", "Total three-phase real power.", rule=MR_Mandatory)
analog(1003, A, "TotalReactivePower", "kvar", "Total three-phase reactive power.")
analog(1003, A, "TotalApparentPower", "kVA", "Total three-phase apparent power.")
comp_var(1003, A, "AveragePowerFactor", Double, "Average power factor (-1..1).")
analog(1003, A, "TotalRealEnergy", "kW.h", "Cumulative generated real energy.")
analog(1003, A, "LoadPercent", "%", "Output as a percentage of rated power.")
analog(1003, A, "WindingTemperature1", "degC", "Stator winding temperature, phase 1.")
analog(1003, A, "WindingTemperature2", "degC", "Stator winding temperature, phase 2.")
analog(1003, A, "WindingTemperature3", "degC", "Stator winding temperature, phase 3.")
analog(1003, A, "BearingTemperatureDriveEnd", "degC", "Drive-end bearing temperature.")
analog(1003, A, "BearingTemperatureNonDriveEnd", "degC", "Non-drive-end bearing temperature.")
comp_var(1003, A, "Connection", T(3004), "Winding connection configuration.")
comp_var(1003, A, "ExcitationType", T(3005), "Excitation method.")
comp_var(1003, A, "NumberOfPoles", UInt16, "Number of alternator poles.")
analog(1003, A, "VoltageSetpoint", "V", "AVR voltage setpoint.")
analog(1003, A, "FieldCurrent", "A", "Excitation field current.")
obj_member(1003, A, "L1", T(1004), "Phase 1 (A) measurements.", rule=MR_Mandatory)
obj_member(1003, A, "L2", T(1004), "Phase 2 (B) measurements.")
obj_member(1003, A, "L3", T(1004), "Phase 3 (C) measurements.")

# --- FuelSystemType --------------------------------------------------------
object_type(1005, "FuelSystemType", DI_ComponentType,
            "The fuel storage and delivery subsystem of a generator set.", CAT_COMP)
F = "FuelSystemType"
comp_var(1005, F, "FuelType", T(3002), "Primary fuel of the set.", rule=MR_Mandatory)
analog(1005, F, "FuelLevel", "%", "Fuel tank level.")
analog(1005, F, "FuelVolume", "l", "Usable fuel volume remaining.")
analog(1005, F, "FuelConsumptionRate", "L/h", "Fuel consumption rate.")
analog(1005, F, "FuelPressure", "kPa", "Fuel supply pressure.")
analog(1005, F, "FuelTemperature", "degC", "Fuel temperature.")
analog(1005, F, "GasSupplyPressure", "kPa", "Gas inlet pressure for gaseous-fuel sets.")
analog(1005, F, "RuntimeRemaining", "h", "Estimated runtime remaining at current load.")
analog(1005, F, "TotalFuelConsumed", "l", "Cumulative fuel consumed.")
comp_var(1005, F, "WaterInFuel", Boolean, "Water detected in the fuel/water separator.")

# --- CoolingSystemType -----------------------------------------------------
object_type(1006, "CoolingSystemType", DI_ComponentType,
            "The engine cooling subsystem of a generator set.", CAT_COMP)
C = "CoolingSystemType"
analog(1006, C, "CoolantTemperature", "degC", "Engine coolant temperature.")
analog(1006, C, "CoolantLevel", "%", "Coolant level. SAE J1939 SPN 111.")
analog(1006, C, "CoolantPressure", "kPa", "Coolant pressure.")
comp_var(1006, C, "CoolingMethod", T(3006), "Cooling method (air- or liquid-cooled).")
analog(1006, C, "AmbientTemperature", "degC", "Ambient air temperature at the set.")
comp_var(1006, C, "RadiatorFanRunning", Boolean, "The radiator fan is running.")
comp_var(1006, C, "JacketWaterHeaterActive", Boolean, "The jacket-water block heater is active.")

# --- LubricationSystemType -------------------------------------------------
object_type(1007, "LubricationSystemType", DI_ComponentType,
            "The engine lubrication subsystem of a generator set.", CAT_COMP)
L = "LubricationSystemType"
analog(1007, L, "OilPressure", "kPa", "Engine oil pressure. SAE J1939 SPN 100.")
analog(1007, L, "OilTemperature", "degC", "Engine oil temperature. SAE J1939 SPN 175.")
analog(1007, L, "OilLevel", "%", "Engine oil level.")
analog(1007, L, "OilFilterDifferentialPressure", "kPa", "Oil filter differential pressure.")

# --- StartingSystemType ----------------------------------------------------
object_type(1008, "StartingSystemType", DI_ComponentType,
            "The starting/battery subsystem of a generator set.", CAT_COMP)
ST = "StartingSystemType"
analog(1008, ST, "BatteryVoltage", "V", "Starting battery voltage. SAE J1939 SPN 168.",
       rule=MR_Mandatory)
analog(1008, ST, "BatteryChargingCurrent", "A", "Battery charging current.")
comp_var(1008, ST, "BatteryChargerActive", Boolean, "The battery charger is active.")
comp_var(1008, ST, "StartAttempts", UInt32, "Number of start attempts in the last start sequence.")

# --- GeneratorControllerType -----------------------------------------------
object_type(1009, "GeneratorControllerType", DI_ComponentType,
            "The generator set control panel. Provides controller identity, mode/state "
            "visibility and remote-monitoring status.",
            CAT_COMP)
G = "GeneratorControllerType"
prop_var(1009, G, "ControllerFamily", String, "Vendor controller product family or product line.")
prop_var(1009, G, "FirmwareVersion", String, "Controller firmware version.")
prop_var(1009, G, "ApplicationSoftwareVersion", String, "Application software version.")
prop_var(1009, G, "ConfigurationVersion", String, "Configuration/calibration version.")
comp_var(1009, G, "InAutoMode", Boolean, "The controller is in automatic mode.")
comp_var(1009, G, "NotInAuto", Boolean, "The controller is NOT in automatic mode (NFPA annunciation).")
comp_var(1009, G, "RemoteStartEnabled", Boolean, "Remote start is enabled.")
comp_var(1009, G, "RemoteControlEnabled", Boolean, "Remote control is enabled.")
comp_var(1009, G, "CloudConnected", Boolean, "Connected to the remote-monitoring cloud.")
comp_var(1009, G, "ModbusEnabled", Boolean, "The Modbus interface is enabled.")
analog(1009, G, "SignalStrength", "%", "Cellular/network signal strength.")

# --- GeneratorRatingType ---------------------------------------------------
CAT_RATE = "Generators Rating"
object_type(1012, "GeneratorRatingType", BaseObjectType,
            "A single nameplate power rating point of a generator set for a given "
            "application/duty (ISO 8528).", CAT_RATE)
R = "GeneratorRatingType"
comp_var(1012, R, "ApplicationRating", T(3003), "Application/duty of this rating.",
         rule=MR_Mandatory)
analog(1012, R, "RatedRealPower", "kW", "Rated real power.", rule=MR_Mandatory)
analog(1012, R, "RatedApparentPower", "kVA", "Rated apparent power.")
comp_var(1012, R, "RatedPowerFactor", Double, "Rated power factor.")
analog(1012, R, "RatedVoltage", "V", "Rated line-to-line voltage.")
analog(1012, R, "RatedCurrent", "A", "Rated line current.")
analog(1012, R, "RatedFrequency", "Hz", "Rated frequency.")
analog(1012, R, "RatedSpeed", "rpm", "Rated engine speed.")
prop_var(1012, R, "PhaseCount", Byte, "Number of phases (1 or 3).")
comp_var(1012, R, "Connection", T(3004), "Winding connection for this rating.")
analog(1012, R, "AmbientTemperature", "degC", "Reference ambient temperature for the rating.")
analog(1012, R, "Altitude", "m", "Reference altitude for the rating.")

# --- GeneratorProtectionAlarmType (: OffNormalAlarmType) --------------------
CAT_AL = "Generators Alarms"
object_type(1017, "GeneratorProtectionAlarmType", OffNormalAlarmType,
            "Alarm raised by a generator protection/shutdown function. Extends "
            "OffNormalAlarmType with the protection function, severity and J1939 origin.",
            CAT_AL)
AL = "GeneratorProtectionAlarmType"
prop_var(1017, AL, "ProtectionFunction", T(3014),
         "The protection function that raised the alarm.", rule=MR_Mandatory)
prop_var(1017, AL, "GeneratorAlarmSeverity", T(3013), "Severity class of the alarm.")
prop_var(1017, AL, "IsShutdown", Boolean, "TRUE if the condition caused an engine shutdown.")
prop_var(1017, AL, "Spn", UInt32, "SAE J1939 SPN when the alarm originates from the engine ECU.")
prop_var(1017, AL, "Fmi", Byte, "SAE J1939 FMI when the alarm originates from the engine ECU.")
prop_var(1017, AL, "SubsystemName", String, "Name of the originating subsystem.")

# --- GeneratorSetType (the whole asset) ------------------------------------
CAT_MAIN = "Generators GeneratorSet"
object_type(1001, "GeneratorSetType", DI_DeviceType,
            "A generator set (GenSet): a complete electrical power generation asset "
            "composed of a prime-mover engine, an alternator, a fuel system, cooling, "
            "lubrication, starting and control subsystems. Applicable to the whole "
            "industry, from small home-standby units to house-sized multi-megawatt "
            "industrial sets.", CAT_MAIN)
GS = "GeneratorSetType"
# Machinery interoperability building blocks
obj_member(1001, GS, "Identification", T(1016),
           "Generator identification and nameplate (Machinery building block).",
           rule=MR_Mandatory, reftype=HasAddIn, bns=DI)
bb = obj_member(1001, GS, "MachineryBuildingBlocks", FolderType,
                "Container for standardized Machinery building blocks.",
                reftype=HasAddIn, bns=MC)
mis = _mid()
add(mis, "UAObject", "MachineryItemState",
    f"{GS}_MachineryBuildingBlocks_MachineryItemState",
    desc="Generic Machinery availability state machine (interoperability).",
    parent=T(bb), bns=MC)
ref(mis, HasModellingRule, MR_Optional)
ref(mis, HasTypeDefinition, MC_MachineryItemState_SMT)
ref(mis, HasAddIn, T(bb), forward=False)
ref(bb, HasAddIn, T(mis))
mom = _mid()
add(mom, "UAObject", "MachineryOperationMode",
    f"{GS}_MachineryBuildingBlocks_MachineryOperationMode",
    desc="Generic Machinery operation-mode state machine (interoperability).",
    parent=T(bb), bns=MC)
ref(mom, HasModellingRule, MR_Optional)
ref(mom, HasTypeDefinition, MC_MachineryOperationMode_SMT)
ref(mom, HasAddIn, T(bb), forward=False)
ref(bb, HasAddIn, T(mom))
# Domain state & mode
obj_member(1001, GS, "OperatingState", T(1011),
           "Detailed generator-set operating state machine.", rule=MR_Mandatory)
comp_var(1001, GS, "OperatingMode", T(3001),
         "Selector mode of the control panel (Off/Manual/Auto/Test/...).",
         rule=MR_Mandatory)
comp_var(1001, GS, "EmissionsStandard", T(3008),
         "Emissions certification standard of the set.")
prop_var(1001, GS, "Application", String,
         "Application segment, e.g. Residential, DataCenter, Healthcare, Rental, PrimePower.")
# Operational status / interlocks
comp_var(1001, GS, "GeneratorBreakerClosed", Boolean, "The generator (output) breaker is closed.")
comp_var(1001, GS, "GeneratorBreakerAvailable", Boolean, "The generator breaker is available to close.")
comp_var(1001, GS, "RemoteStartInput", Boolean, "The remote start input is asserted.")
comp_var(1001, GS, "RunRequest", Boolean, "A run request is active from any source.")
comp_var(1001, GS, "LoadInhibit", Boolean, "Loading of the set is inhibited.")
comp_var(1001, GS, "AvailableToLoad", Boolean,
         "The set is up to speed and voltage and is ready to accept load.")
# Subassemblies
obj_member(1001, GS, "Engine", T(1002), "The prime-mover engine.", rule=MR_Mandatory)
obj_member(1001, GS, "Alternator", T(1003), "The alternator (generator end).", rule=MR_Mandatory)
obj_member(1001, GS, "Controller", T(1009), "The control panel.", rule=MR_Mandatory)
obj_member(1001, GS, "FuelSystem", T(1005), "The fuel subsystem.")
obj_member(1001, GS, "CoolingSystem", T(1006), "The cooling subsystem.")
obj_member(1001, GS, "LubricationSystem", T(1007), "The lubrication subsystem.")
obj_member(1001, GS, "StartingSystem", T(1008), "The starting/battery subsystem.")
# Ratings folder with a placeholder for one or more rating points
ratings = obj_member(1001, GS, "Ratings", FolderType,
                     "Nameplate power ratings of the set (e.g. Standby and Prime).",
                     rule=MR_Mandatory)
rp = _mid()
add(rp, "UAObject", "<Rating>", f"{GS}_Ratings_Rating",
    desc="A nameplate rating point of the set.", parent=T(ratings))
ref(rp, HasModellingRule, MR_OptionalPlaceholder)
ref(rp, HasTypeDefinition, T(1012))
ref(rp, HasComponent, T(ratings), forward=False)
ref(ratings, HasComponent, T(rp))
# Methods
method(1001, GS, "Start", "Command the set to start in the current operating mode.")
method(1001, GS, "Stop", "Command a normal stop (with cooldown).")
method(1001, GS, "EmergencyStop", "Command an immediate emergency stop.")
method(1001, GS, "ResetFaults", "Reset latched faults / lockout.")
method(1001, GS, "SetOperatingMode", "Set the control-panel selector mode.",
       inargs=[("Mode", T(3001), "The requested operating mode.")])
method(1001, GS, "StartTest", "Start a test run for a given duration.",
       inargs=[("DurationMinutes", UInt32, "Test duration in minutes."),
               ("WithLoad", Boolean, "TRUE to run the test with load.")])
# Alarm event source
ref(1001, GeneratesEvent, T(1017))

# --- TransferSwitchSourceType ----------------------------------------------
CAT_ATS = "Generators TransferSwitch"
object_type(1019, "TransferSwitchSourceType", BaseObjectType,
            "One power source (normal/utility or emergency/generator) of an automatic "
            "transfer switch, with its availability and measurements.", CAT_ATS)
SRC = "TransferSwitchSourceType"
comp_var(1019, SRC, "Available", Boolean, "The source is present and energized.", rule=MR_Mandatory)
comp_var(1019, SRC, "Acceptable", Boolean, "The source is within acceptable voltage/frequency limits.")
analog(1019, SRC, "Voltage", "V", "Source line-to-line voltage.")
analog(1019, SRC, "Frequency", "Hz", "Source frequency.")
prop_var(1019, SRC, "PhaseRotation", String, "Phase rotation of the source (e.g. ABC or CBA).")

# --- AutomaticTransferSwitchType -------------------------------------------
object_type(1013, "AutomaticTransferSwitchType", DI_DeviceType,
            "An automatic transfer switch (ATS) that transfers a load between a normal "
            "source (utility) and an emergency source (generator).", CAT_ATS)
TS = "AutomaticTransferSwitchType"
obj_member(1013, TS, "Identification", MC_MachineIdentificationType,
           "ATS identification and nameplate.", reftype=HasAddIn, bns=DI)
comp_var(1013, TS, "Position", T(3010), "Contact position of the switch.", rule=MR_Mandatory)
comp_var(1013, TS, "OperatingState", T(3012), "Operating state of the switch.")
comp_var(1013, TS, "TransitionType", T(3011), "Transition method of the switch.")
obj_member(1013, TS, "Source1", T(1019), "Source 1 (normal/utility).", rule=MR_Mandatory)
obj_member(1013, TS, "Source2", T(1019), "Source 2 (emergency/generator).", rule=MR_Mandatory)
prop_var(1013, TS, "PreferredSource", Byte, "The preferred source (1 = normal, 2 = emergency).")
comp_var(1013, TS, "Source1Connected", Boolean, "The load is connected to Source 1.")
comp_var(1013, TS, "Source2Connected", Boolean, "The load is connected to Source 2.")
comp_var(1013, TS, "TransferInhibited", Boolean, "Transfer is currently inhibited.")
prop_var(1013, TS, "TransferInhibitReason", String, "Reason transfer is inhibited, if any.")
analog(1013, TS, "RatedCurrent", "A", "Rated current of the switch.")
prop_var(1013, TS, "PoleCount", Byte, "Number of poles.")
comp_var(1013, TS, "ServiceEntranceRated", Boolean, "The switch is service-entrance rated.")
analog(1013, TS, "LoadCurrent", "A", "Load current through the switch.")
comp_var(1013, TS, "TransferCount", UInt32, "Cumulative number of transfers.")
comp_var(1013, TS, "LastTransferTime", DateTime, "Timestamp of the last transfer.")
comp_var(1013, TS, "EngineStartDelay", Duration, "Engine-start (outage confirmation) delay.")
comp_var(1013, TS, "TransferToEmergencyDelay", Duration, "Delay before transferring to emergency.")
comp_var(1013, TS, "RetransferToNormalDelay", Duration, "Delay before retransferring to normal.")
comp_var(1013, TS, "CooldownDelay", Duration, "Engine cooldown (unloaded run) delay.")
method(1013, TS, "Transfer", "Command a transfer to the emergency source.")
method(1013, TS, "Retransfer", "Command a retransfer to the normal source.")
method(1013, TS, "InhibitTransfer", "Enable or disable the transfer inhibit.",
       inargs=[("Inhibit", Boolean, "TRUE to inhibit transfer.")])

# --- ParallelingControllerType ---------------------------------------------
CAT_PAR = "Generators Paralleling"
object_type(1014, "ParallelingControllerType", DI_ComponentType,
            "A paralleling / switchgear controller that synchronizes and shares load "
            "among generator sets on a common bus, and optionally parallels with the utility.",
            CAT_PAR)
P = "ParallelingControllerType"
comp_var(1014, P, "SystemState", T(3015), "Operating state of the paralleling system.",
         rule=MR_Mandatory)
analog(1014, P, "BusVoltage", "V", "Common bus voltage.")
analog(1014, P, "BusFrequency", "Hz", "Common bus frequency.")
analog(1014, P, "TotalBusRealPower", "kW", "Total real power on the bus.")
analog(1014, P, "TotalBusReactivePower", "kvar", "Total reactive power on the bus.")
analog(1014, P, "SynchronizationAngle", "deg", "Phase angle difference during synchronizing.")
analog(1014, P, "SlipFrequency", "Hz", "Slip frequency during synchronizing.")
analog(1014, P, "VoltageDifference", "V", "Voltage difference during synchronizing.")
analog(1014, P, "FrequencyDifference", "Hz", "Frequency difference during synchronizing.")
comp_var(1014, P, "SyncCheckPermissive", Boolean, "Synchronism-check permissive to close.")
comp_var(1014, P, "DeadBus", Boolean, "The bus is dead (de-energized).")
analog(1014, P, "LoadSharePercent", "%", "This set's share of the total bus load.")
analog(1014, P, "AvailableCapacity", "kW", "Available spare capacity on the bus.")
analog(1014, P, "SpinningReserve", "kW", "Spinning reserve on the bus.")
comp_var(1014, P, "GeneratorBreakerClosed", Boolean, "The generator breaker is closed.")
comp_var(1014, P, "UtilityBreakerClosed", Boolean, "The utility breaker is closed.")
analog(1014, P, "UtilityImportPower", "kW", "Power imported from the utility.")
analog(1014, P, "UtilityExportPower", "kW", "Power exported to the utility.")
method(1014, P, "ConnectToBus", "Synchronize and close onto the common bus.")
method(1014, P, "DisconnectFromBus", "Soft-unload and open from the common bus.")

# --- GeneratorSystemType (multi-set power plant) ---------------------------
CAT_SYS = "Generators System"
object_type(1015, "GeneratorSystemType", BaseObjectType,
            "A power-generation system aggregating one or more paralleled generator sets, "
            "an optional paralleling controller and transfer switches. Models integrated "
            "power systems such as data-center and healthcare plants.", CAT_SYS)
SY = "GeneratorSystemType"
gsets = obj_member(1015, SY, "GeneratorSets", FolderType,
                   "The generator sets that make up the system.", rule=MR_Mandatory)
gp = _mid()
add(gp, "UAObject", "<GeneratorSet>", f"{SY}_GeneratorSets_GeneratorSet",
    desc="A generator set participating in the system.", parent=T(gsets))
ref(gp, HasModellingRule, MR_MandatoryPlaceholder)
ref(gp, HasTypeDefinition, T(1001))
ref(gp, HasComponent, T(gsets), forward=False)
ref(gsets, HasComponent, T(gp))
obj_member(1015, SY, "ParallelingController", T(1014),
           "The paralleling/switchgear controller of the system.")
tswitches = obj_member(1015, SY, "TransferSwitches", FolderType,
                       "The transfer switches in the system.")
tp = _mid()
add(tp, "UAObject", "<TransferSwitch>", f"{SY}_TransferSwitches_TransferSwitch",
    desc="A transfer switch in the system.", parent=T(tswitches))
ref(tp, HasModellingRule, MR_OptionalPlaceholder)
ref(tp, HasTypeDefinition, T(1013))
ref(tp, HasComponent, T(tswitches), forward=False)
ref(tswitches, HasComponent, T(tp))
comp_var(1015, SY, "NumberOfGeneratorSets", UInt16, "Number of generator sets in the system.")
analog(1015, SY, "TotalSystemCapacity", "kW", "Total installed capacity of the system.")
analog(1015, SY, "TotalSystemLoad", "kW", "Total load currently served by the system.")
prop_var(1015, SY, "RedundancyScheme", String,
         "Redundancy scheme, e.g. N, N+1, N+2, 2N, DistributedRedundant.")

# ===========================================================================
# ==============================  EMISSION  =================================
# ===========================================================================
NAMESPACE = "http://opcfoundation.org/UA/Generators/"
VERSION = "1.0.0"
PUBDATE = "2026-07-01T00:00:00Z"

ALIASES = [
    ("Boolean", "i=1"), ("Byte", "i=3"), ("UInt16", "i=5"), ("UInt32", "i=7"),
    ("Int32", "i=6"), ("Double", "i=11"), ("String", "i=12"),
    ("DateTime", "i=13"), ("LocalizedText", "i=21"), ("Duration", "i=290"),
    ("Argument", "i=296"), ("Organizes", "i=35"), ("HasModellingRule", "i=37"),
    ("HasEncoding", "i=38"), ("HasTypeDefinition", "i=40"),
    ("EUInformation", "i=887"),
    ("GeneratesEvent", "i=41"), ("HasSubtype", "i=45"), ("HasProperty", "i=46"),
    ("HasComponent", "i=47"), ("FromState", "i=51"), ("ToState", "i=52"),
    ("HasInterface", "i=17603"), ("HasAddIn", "i=17604"),
]

REFTYPE_ALIAS = {v: k for k, v in ALIASES}
DATATYPE_ALIAS = {v: k for k, v in ALIASES}

_PRIO = {HasModellingRule: 0, HasSubtype: 1}


def _sorted_refs(refs):
    return sorted(range(len(refs)), key=lambda i: (_PRIO.get(refs[i][0], 2), i))


def _bn(n):
    if n.bns == 0:
        return n.bname
    return f"{n.bns}:{n.bname}"


def _fmt_reftype(t):
    return REFTYPE_ALIAS.get(t, t)


def _emit_node(n):
    tag = n.cls
    a = [f'{tag} NodeId="{T(n.nid)}"', f'BrowseName="{sx.escape(_bn(n))}"']
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
    if n.definition:
        lines.append("    " + n.definition)
    if n.value:
        lines.append("    " + n.value)
    lines.append(f"  </{tag}>")
    return "\n".join(lines)


def emit():
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<!-- OPC UA Companion Specification for Generators (GenSets) - generated model -->',
           '<UANodeSet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
           'xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
           'xmlns:uax="http://opcfoundation.org/UA/2008/02/Types.xsd" '
           'xmlns="http://opcfoundation.org/UA/2011/03/UANodeSet.xsd">',
           '  <NamespaceUris>',
           f'    <Uri>{NAMESPACE}</Uri>',
           '    <Uri>http://opcfoundation.org/UA/DI/</Uri>',
           '    <Uri>http://opcfoundation.org/UA/Machinery/</Uri>',
           '  </NamespaceUris>',
           '  <Models>',
           f'    <Model ModelUri="{NAMESPACE}" Version="{VERSION}" PublicationDate="{PUBDATE}">',
           '      <RequiredModel ModelUri="http://opcfoundation.org/UA/" Version="1.05.04" PublicationDate="2023-12-15T00:00:00Z" />',
           '      <RequiredModel ModelUri="http://opcfoundation.org/UA/DI/" Version="1.04.0" PublicationDate="2022-11-03T00:00:00Z" />',
           '      <RequiredModel ModelUri="http://opcfoundation.org/UA/Machinery/" Version="1.04.1" PublicationDate="2026-01-01T00:00:00Z" />',
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
    rows = []
    for nid in ORDER:
        n = NODES[nid]
        rows.append(f"{n.symbolic},{n.nid},{n.cls[2:]}")
    return "\n".join(rows) + "\n"


# --- Markdown reference-table generation (reconstructed from the model) -----
import re

# Auto-extracted transitive members of base types (do not edit by hand).
# (BrowseName, NodeClass, DataType, ModellingRule, DeclaringType)
BASE_MEMBERS = {
    'DeviceType': [
        ('Manufacturer', 'Variable', 'LocalizedText', 'Mandatory', 'DeviceType'),
        ('ManufacturerUri', 'Variable', 'String', 'Optional', 'DeviceType'),
        ('Model', 'Variable', 'LocalizedText', 'Mandatory', 'DeviceType'),
        ('HardwareRevision', 'Variable', 'String', 'Mandatory', 'DeviceType'),
        ('SoftwareRevision', 'Variable', 'String', 'Mandatory', 'DeviceType'),
        ('DeviceRevision', 'Variable', 'String', 'Mandatory', 'DeviceType'),
        ('ProductCode', 'Variable', 'String', 'Optional', 'DeviceType'),
        ('DeviceManual', 'Variable', 'String', 'Mandatory', 'DeviceType'),
        ('DeviceClass', 'Variable', 'String', 'Optional', 'DeviceType'),
        ('SerialNumber', 'Variable', 'String', 'Mandatory', 'DeviceType'),
        ('ProductInstanceUri', 'Variable', 'String', 'Optional', 'DeviceType'),
        ('RevisionCounter', 'Variable', 'Int32', 'Mandatory', 'DeviceType'),
        ('<CPIdentifier>', 'Object', '', 'OptionalPlaceholder', 'DeviceType'),
        ('DeviceHealth', 'Variable', 'DeviceHealthEnumeration', 'Optional', 'DeviceType'),
        ('DeviceHealthAlarms', 'Object', '', 'Optional', 'DeviceType'),
        ('DeviceTypeImage', 'Object', '', 'Optional', 'DeviceType'),
        ('Documentation', 'Object', '', 'Optional', 'DeviceType'),
        ('ProtocolSupport', 'Object', '', 'Optional', 'DeviceType'),
        ('ImageSet', 'Object', '', 'Optional', 'DeviceType'),
        ('AssetId', 'Variable', 'String', 'Optional', 'ComponentType'),
        ('ComponentName', 'Variable', 'LocalizedText', 'Optional', 'ComponentType'),
        ('ParameterSet', 'Object', '', 'Optional', 'TopologyElementType'),
        ('MethodSet', 'Object', '', 'Optional', 'TopologyElementType'),
        ('<GroupIdentifier>', 'Object', '', 'OptionalPlaceholder', 'TopologyElementType'),
        ('Identification', 'Object', '', 'Optional', 'TopologyElementType'),
        ('Lock', 'Object', '', 'Optional', 'TopologyElementType'),
    ],
    'ComponentType': [
        ('Manufacturer', 'Variable', 'LocalizedText', 'Optional', 'ComponentType'),
        ('ManufacturerUri', 'Variable', 'String', 'Optional', 'ComponentType'),
        ('Model', 'Variable', 'LocalizedText', 'Optional', 'ComponentType'),
        ('HardwareRevision', 'Variable', 'String', 'Optional', 'ComponentType'),
        ('SoftwareRevision', 'Variable', 'String', 'Optional', 'ComponentType'),
        ('DeviceRevision', 'Variable', 'String', 'Optional', 'ComponentType'),
        ('ProductCode', 'Variable', 'String', 'Optional', 'ComponentType'),
        ('DeviceManual', 'Variable', 'String', 'Optional', 'ComponentType'),
        ('DeviceClass', 'Variable', 'String', 'Optional', 'ComponentType'),
        ('SerialNumber', 'Variable', 'String', 'Optional', 'ComponentType'),
        ('ProductInstanceUri', 'Variable', 'String', 'Optional', 'ComponentType'),
        ('RevisionCounter', 'Variable', 'Int32', 'Optional', 'ComponentType'),
        ('AssetId', 'Variable', 'String', 'Optional', 'ComponentType'),
        ('ComponentName', 'Variable', 'LocalizedText', 'Optional', 'ComponentType'),
        ('ParameterSet', 'Object', '', 'Optional', 'TopologyElementType'),
        ('MethodSet', 'Object', '', 'Optional', 'TopologyElementType'),
        ('<GroupIdentifier>', 'Object', '', 'OptionalPlaceholder', 'TopologyElementType'),
        ('Identification', 'Object', '', 'Optional', 'TopologyElementType'),
        ('Lock', 'Object', '', 'Optional', 'TopologyElementType'),
    ],
    'MachineIdentificationType': [
        ('Location', 'Variable', 'String', 'Optional', 'MachineIdentificationType'),
        ('ProductInstanceUri', 'Variable', 'String', 'Mandatory', 'MachineIdentificationType'),
        ('AssetId', 'Variable', 'String', 'Optional', 'MachineryItemIdentificationType'),
        ('ComponentName', 'Variable', 'LocalizedText', 'Optional', 'MachineryItemIdentificationType'),
        ('DeviceClass', 'Variable', 'String', 'Optional', 'MachineryItemIdentificationType'),
        ('HardwareRevision', 'Variable', 'String', 'Optional', 'MachineryItemIdentificationType'),
        ('InitialOperationDate', 'Variable', 'DateTime', 'Optional', 'MachineryItemIdentificationType'),
        ('Manufacturer', 'Variable', 'LocalizedText', 'Mandatory', 'MachineryItemIdentificationType'),
        ('ManufacturerUri', 'Variable', 'String', 'Optional', 'MachineryItemIdentificationType'),
        ('Model', 'Variable', 'LocalizedText', 'Optional', 'MachineryItemIdentificationType'),
        ('MonthOfConstruction', 'Variable', 'Byte', 'Optional', 'MachineryItemIdentificationType'),
        ('ProductCode', 'Variable', 'String', 'Optional', 'MachineryItemIdentificationType'),
        ('SerialNumber', 'Variable', 'String', 'Mandatory', 'MachineryItemIdentificationType'),
        ('SoftwareRevision', 'Variable', 'String', 'Optional', 'MachineryItemIdentificationType'),
        ('YearOfConstruction', 'Variable', 'UInt16', 'Optional', 'MachineryItemIdentificationType'),
        ('<GroupIdentifier>', 'Object', '', 'OptionalPlaceholder', 'FunctionalGroupType'),
        ('UIElement', 'Variable', '', 'Optional', 'FunctionalGroupType'),
    ],
    'FiniteStateMachineType': [
        ('CurrentState', 'Variable', 'LocalizedText', 'Mandatory', 'FiniteStateMachineType'),
        ('LastTransition', 'Variable', 'LocalizedText', 'Optional', 'FiniteStateMachineType'),
        ('AvailableStates', 'Variable', 'NodeId[]', 'Optional', 'FiniteStateMachineType'),
        ('AvailableTransitions', 'Variable', 'NodeId[]', 'Optional', 'FiniteStateMachineType'),
    ],
    'OffNormalAlarmType': [
        ('NormalState', 'Variable', 'NodeId', 'Mandatory', 'OffNormalAlarmType'),
        ('EnabledState', 'Variable', 'LocalizedText', 'Mandatory', 'AlarmConditionType'),
        ('ActiveState', 'Variable', 'LocalizedText', 'Mandatory', 'AlarmConditionType'),
        ('InputNode', 'Variable', 'NodeId', 'Mandatory', 'AlarmConditionType'),
        ('SuppressedState', 'Variable', 'LocalizedText', 'Optional', 'AlarmConditionType'),
        ('OutOfServiceState', 'Variable', 'LocalizedText', 'Optional', 'AlarmConditionType'),
        ('ShelvingState', 'Object', '', 'Optional', 'AlarmConditionType'),
        ('SuppressedOrShelved', 'Variable', 'Boolean', 'Mandatory', 'AlarmConditionType'),
        ('MaxTimeShelved', 'Variable', 'Duration', 'Optional', 'AlarmConditionType'),
        ('AudibleEnabled', 'Variable', 'Boolean', 'Optional', 'AlarmConditionType'),
        ('AudibleSound', 'Variable', 'AudioDataType', 'Optional', 'AlarmConditionType'),
        ('SilenceState', 'Variable', 'LocalizedText', 'Optional', 'AlarmConditionType'),
        ('OnDelay', 'Variable', 'Duration', 'Optional', 'AlarmConditionType'),
        ('OffDelay', 'Variable', 'Duration', 'Optional', 'AlarmConditionType'),
        ('FirstInGroupFlag', 'Variable', 'Boolean', 'Optional', 'AlarmConditionType'),
        ('FirstInGroup', 'Object', '', 'Optional', 'AlarmConditionType'),
        ('LatchedState', 'Variable', 'LocalizedText', 'Optional', 'AlarmConditionType'),
        ('ReAlarmTime', 'Variable', 'Duration', 'Optional', 'AlarmConditionType'),
        ('ReAlarmRepeatCount', 'Variable', 'Int16', 'Optional', 'AlarmConditionType'),
        ('Silence', 'Method', '', 'Optional', 'AlarmConditionType'),
        ('Suppress', 'Method', '', 'Optional', 'AlarmConditionType'),
        ('Suppress2', 'Method', '', 'Optional', 'AlarmConditionType'),
        ('Unsuppress', 'Method', '', 'Optional', 'AlarmConditionType'),
        ('Unsuppress2', 'Method', '', 'Optional', 'AlarmConditionType'),
        ('RemoveFromService', 'Method', '', 'Optional', 'AlarmConditionType'),
        ('RemoveFromService2', 'Method', '', 'Optional', 'AlarmConditionType'),
        ('PlaceInService', 'Method', '', 'Optional', 'AlarmConditionType'),
        ('PlaceInService2', 'Method', '', 'Optional', 'AlarmConditionType'),
        ('Reset', 'Method', '', 'Optional', 'AlarmConditionType'),
        ('Reset2', 'Method', '', 'Optional', 'AlarmConditionType'),
        ('GetGroupMemberships', 'Method', '', 'Optional', 'AlarmConditionType'),
        ('AckedState', 'Variable', 'LocalizedText', 'Mandatory', 'AcknowledgeableConditionType'),
        ('ConfirmedState', 'Variable', 'LocalizedText', 'Optional', 'AcknowledgeableConditionType'),
        ('Acknowledge', 'Method', '', 'Mandatory', 'AcknowledgeableConditionType'),
        ('Confirm', 'Method', '', 'Optional', 'AcknowledgeableConditionType'),
        ('ConditionClassId', 'Variable', 'NodeId', 'Mandatory', 'ConditionType'),
        ('ConditionClassName', 'Variable', 'LocalizedText', 'Mandatory', 'ConditionType'),
        ('ConditionSubClassId', 'Variable', 'NodeId[]', 'Optional', 'ConditionType'),
        ('ConditionSubClassName', 'Variable', 'LocalizedText[]', 'Optional', 'ConditionType'),
        ('ConditionName', 'Variable', 'String', 'Mandatory', 'ConditionType'),
        ('BranchId', 'Variable', 'NodeId', 'Mandatory', 'ConditionType'),
        ('Retain', 'Variable', 'Boolean', 'Mandatory', 'ConditionType'),
        ('Quality', 'Variable', 'StatusCode', 'Mandatory', 'ConditionType'),
        ('LastSeverity', 'Variable', 'UInt16', 'Mandatory', 'ConditionType'),
        ('Comment', 'Variable', 'LocalizedText', 'Mandatory', 'ConditionType'),
        ('ClientUserId', 'Variable', 'String', 'Mandatory', 'ConditionType'),
        ('Disable', 'Method', '', 'Mandatory', 'ConditionType'),
        ('Enable', 'Method', '', 'Mandatory', 'ConditionType'),
        ('AddComment', 'Method', '', 'Mandatory', 'ConditionType'),
        ('EventId', 'Variable', 'ByteString', 'Mandatory', 'BaseEventType'),
        ('EventType', 'Variable', 'NodeId', 'Mandatory', 'BaseEventType'),
        ('SourceNode', 'Variable', 'NodeId', 'Mandatory', 'BaseEventType'),
        ('SourceName', 'Variable', 'String', 'Mandatory', 'BaseEventType'),
        ('Time', 'Variable', 'UtcTime', 'Mandatory', 'BaseEventType'),
        ('ReceiveTime', 'Variable', 'UtcTime', 'Mandatory', 'BaseEventType'),
        ('LocalTime', 'Variable', 'TimeZoneDataType', 'Optional', 'BaseEventType'),
        ('Message', 'Variable', 'LocalizedText', 'Mandatory', 'BaseEventType'),
        ('Severity', 'Variable', 'UInt16', 'Mandatory', 'BaseEventType'),
    ],
}

# Auto-extracted reference.opcfoundation.org deep-links (BrowseName -> url).
LINK_MAP = {
    '3DCartesianCoordinates': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.26',
    '3DCartesianCoordinatesType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.24',
    '3DFrame': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.30',
    '3DFrameType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.28',
    '3DOrientation': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.28',
    '3DOrientationType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.26',
    '3DVector': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.24',
    '3DVectorType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.22',
    'AccessLevelExType': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.58',
    'AccessLevelType': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.57',
    'AccessRestrictionType': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.56',
    'AcknowledgeableConditionType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.7.2',
    'ActionMethodDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.10.5',
    'ActionState': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.11#6.2.11.2.1',
    'ActionTargetDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.10.3',
    'AddNodesItem': 'https://reference.opcfoundation.org/specs/OPC-10000-4/5.8.2#5.8.2.2',
    'AddReferencesItem': 'https://reference.opcfoundation.org/specs/OPC-10000-4/5.8.3#5.8.3.2',
    'AdditionalParametersType': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.1',
    'AddressSpaceFileType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.12',
    'AggregateConfiguration': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.22.4',
    'AggregateConfigurationType': 'https://reference.opcfoundation.org/specs/OPC-10000-13/4.2.1#4.2.1.2',
    'AggregateFunctionType': 'https://reference.opcfoundation.org/specs/OPC-10000-13/4.2.2#4.2.2.2',
    'Aggregates': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.6',
    'AlarmConditionType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.2',
    'AlarmGroupMember': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.4.5',
    'AlarmGroupType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.3',
    'AlarmMask': 'https://reference.opcfoundation.org/specs/OPC-10000-9/8.3',
    'AlarmMetricsType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/9.2',
    'AlarmRateVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/9.3',
    'AlarmStateVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/8.2',
    'AlarmSuppressionGroupMember': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.4.6',
    'AlarmSuppressionGroupType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.4',
    'AliasCategoryUpdateDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-17/D.2.1',
    'AliasFor': 'https://reference.opcfoundation.org/specs/OPC-10000-17/8.2',
    'AliasNameCategoryType': 'https://reference.opcfoundation.org/specs/OPC-10000-17/6.3.1',
    'AliasNameDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-17/7.2',
    'AliasNameType': 'https://reference.opcfoundation.org/specs/OPC-10000-17/6.2',
    'AliasNameVerboseDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-17/7.3',
    'AliasUpdateDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-17/D.2.2',
    'AllowedSubtype': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.29',
    'AlternativeUnitType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/6.4.2#6.4.2.4',
    'AlwaysGeneratesEvent': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.16',
    'AnalogItemType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2#5.3.2.3',
    'AnalogNumberItemType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2#5.3.2.6',
    'AnalogNumberUnitRangeType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2#5.3.2.7',
    'AnalogUnitRangeType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2#5.3.2.5',
    'AnalogUnitType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2#5.3.2.4',
    'Annotation': 'https://reference.opcfoundation.org/specs/OPC-10000-11/6.6.6',
    'AnnotationDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/6.6.1',
    'AnonymousIdentityToken': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.40.3',
    'ApplicationCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.2',
    'ApplicationConfigurationDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.10.19',
    'ApplicationConfigurationFileType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.10.20',
    'ApplicationConfigurationFolderType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.10.15',
    'ApplicationConfigurationType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.10.14',
    'ApplicationDescription': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.2',
    'ApplicationIdentityDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.10.21',
    'ApplicationInstanceCertificate': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.3',
    'ApplicationType': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.4',
    'Argument': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.6',
    'ArrayItemType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.4#5.3.4.1',
    'AssociatedWith': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.23',
    'AttributeOperand': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.7.4#7.7.4.4',
    'AttributeWriteMask': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.60',
    'AudioDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.53',
    'AudioVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.19',
    'AuditActivateSessionEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.10',
    'AuditAddNodesEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.20',
    'AuditAddReferencesEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.22',
    'AuditCancelEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.11',
    'AuditCertificateDataMismatchEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.13',
    'AuditCertificateEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.12',
    'AuditCertificateExpiredEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.14',
    'AuditCertificateInvalidEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.15',
    'AuditCertificateMismatchEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.18',
    'AuditCertificateRevokedEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.17',
    'AuditCertificateUntrustedEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.16',
    'AuditChannelEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.5',
    'AuditClientEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.36',
    'AuditClientUpdateMethodResultEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.37',
    'AuditConditionAcknowledgeEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.10.6',
    'AuditConditionCommentEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.10.4',
    'AuditConditionConfirmEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.10.7',
    'AuditConditionEnableEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.10.3',
    'AuditConditionEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.10.2',
    'AuditConditionOutOfServiceEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.10.12',
    'AuditConditionResetEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.10.11',
    'AuditConditionRespondEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.10.5',
    'AuditConditionShelvingEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.10.8',
    'AuditConditionSilenceEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.10.10',
    'AuditConditionSuppressionEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.10.9',
    'AuditCreateSessionEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.8',
    'AuditDeleteNodesEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.21',
    'AuditDeleteReferencesEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.23',
    'AuditEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.3',
    'AuditHistoryAnnotationUpdateEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.8.4',
    'AuditHistoryAtTimeDeleteEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.8.7',
    'AuditHistoryBulkInsertEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.8.10',
    'AuditHistoryConfigurationChangeEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.8.9',
    'AuditHistoryDeleteEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.8.5',
    'AuditHistoryEventDeleteEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.8.8',
    'AuditHistoryEventUpdateEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.8.2',
    'AuditHistoryRawModifyDeleteEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.8.6',
    'AuditHistoryUpdateEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.26',
    'AuditHistoryValueUpdateEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.8.3',
    'AuditNodeManagementEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.19',
    'AuditOpenSecureChannelEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.6',
    'AuditProgramTransitionEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-10/5.2.6',
    'AuditSecurityEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.4',
    'AuditSessionEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.7',
    'AuditUpdateEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.24',
    'AuditUpdateMethodEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.27',
    'AuditUpdateStateEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.17',
    'AuditUrlMismatchEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.9',
    'AuditWriteUpdateEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.25',
    'AuthorizationServiceConfigurationDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/9.7.5',
    'AuthorizationServiceConfigurationType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/9.7.4',
    'AuthorizationServicesConfigurationFolderType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/9.7.2',
    'AxisInformation': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.6.7',
    'AxisScaleEnumeration': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.6.8',
    'BaseAnalogType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2#5.3.2.2',
    'BaseConditionClassType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.9.2',
    'BaseConfigurationDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.5#7.8.5.4',
    'BaseConfigurationRecordDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.5#7.8.5.5',
    'BaseDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.7',
    'BaseDataVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.4',
    'BaseEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.2',
    'BaseInterfaceType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.9',
    'BaseLifetimeIndicationType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/10.3',
    'BaseLogEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-26/6.3',
    'BaseModelChangeEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.31',
    'BaseObjectType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.2',
    'BaseVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.2',
    'BitFieldDefinition': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.45',
    'BitFieldMaskDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.18',
    'BitFieldType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.29',
    'BlockType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.11',
    'Boolean': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.8',
    'BrokerConnectionTransportDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.2#6.4.2.2.3',
    'BrokerConnectionTransportType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.3.2#9.3.2.1',
    'BrokerDataSetReaderTransportDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.2#6.4.2.6.6',
    'BrokerDataSetReaderTransportType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.3.2#9.3.2.4',
    'BrokerDataSetWriterTransportDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.2#6.4.2.5.7',
    'BrokerDataSetWriterTransportType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.3.2#9.3.2.3',
    'BrokerTransportQualityOfService': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.2#6.4.2.1',
    'BrokerWriterGroupTransportDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.2#6.4.2.3.5',
    'BrokerWriterGroupTransportType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.3.2#9.3.2.2',
    'BuildInfo': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.4',
    'BuildInfoType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.7',
    'Byte': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.9',
    'ByteString': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.10',
    'CachedLoadingType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.4.5#8.4.5.1',
    'CanUpdate': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.6.2',
    'CartesianCoordinates': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.25',
    'CartesianCoordinatesType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.23',
    'CertificateExpirationAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.24#5.8.24.7',
    'CertificateGroupDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.3#7.8.3.4',
    'CertificateGroupFolderType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.3#7.8.3.3',
    'CertificateGroupType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.3#7.8.3.1',
    'CertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.1',
    'CertificateUpdateRequestedAuditEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.10.26',
    'CertificateUpdatedAuditEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.10.27',
    'ChassisIdSubtype': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.1#5.3.1.9',
    'CheckFunctionAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.12.4',
    'ChoiceStateType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.6.2',
    'ComplexNumberType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.6.5',
    'ComponentType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.6',
    'ConditionType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.5.2',
    'ConditionVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.3',
    'ConfigurableObjectType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/9.2.2',
    'ConfigurationFileType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.5#7.8.5.1',
    'ConfigurationUpdateTargetType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.5#7.8.5.6',
    'ConfigurationUpdateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.5#7.8.5.7',
    'ConfigurationUpdatedAuditEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.5#7.8.5.8',
    'ConfigurationVersionDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.2.6',
    'ConfirmationStateMachineType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.4.11#8.4.11.1',
    'ConnectionPointType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/5.4',
    'ConnectionTransportDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.7#6.2.7.5.2',
    'ConnectionTransportType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.5#9.1.5.8',
    'ConnectsTo': 'https://reference.opcfoundation.org/specs/OPC-10000-100/5.5',
    'ConnectsToParent': 'https://reference.opcfoundation.org/specs/OPC-10000-100/5.5',
    'ContentFilter': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.7.1',
    'ContentFilterElement': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.7.1',
    'ContinuationPoint': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.9',
    'Controls': 'https://reference.opcfoundation.org/specs/OPC-10000-23/4.4.2',
    'ConversionLimitEnum': 'https://reference.opcfoundation.org/specs/OPC-10000-8/6.6.3',
    'Counter': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.8',
    'CubeItemType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.4#5.3.4.5',
    'CurrencyUnitType': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.61',
    'DataItemType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.1',
    'DataSetFieldContentMask': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.4#6.2.4.2',
    'DataSetFieldFlags': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.2.5',
    'DataSetFolderType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.4#9.1.4.5.1',
    'DataSetMetaDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.2.3',
    'DataSetOrderingType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.3.1#6.3.1.1.3',
    'DataSetReaderDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.9#6.2.9.13.1',
    'DataSetReaderMessageDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.9#6.2.9.13.3',
    'DataSetReaderMessageType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.8#9.1.8.4',
    'DataSetReaderTransportDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.9#6.2.9.13.2',
    'DataSetReaderTransportType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.8#9.1.8.3',
    'DataSetReaderType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.8#9.1.8.2',
    'DataSetToWriter': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.4#9.1.4.2.5',
    'DataSetWriterDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.4#6.2.4.5.1',
    'DataSetWriterMessageDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.4#6.2.4.5.3',
    'DataSetWriterMessageType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.7#9.1.7.4',
    'DataSetWriterTransportDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.4#6.2.4.5.2',
    'DataSetWriterTransportType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.7#9.1.7.3',
    'DataSetWriterType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.7#9.1.7.2',
    'DataTypeDefinition': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.47',
    'DataTypeDescription': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.32',
    'DataTypeEncodingType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.7',
    'DataTypeRefinementType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.12',
    'DataTypeSchemaHeader': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.31',
    'DataValue': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.11.1',
    'DatagramConnectionTransport2DataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.1#6.4.1.2.7',
    'DatagramConnectionTransportDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.1#6.4.1.2.2',
    'DatagramConnectionTransportType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.3.1#9.3.1.1',
    'DatagramDataSetReaderTransportDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.1#6.4.1.6.5',
    'DatagramDataSetReaderTransportType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.3.1#9.3.1.4',
    'DatagramWriterGroupTransport2DataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.1#6.4.1.3.9',
    'DatagramWriterGroupTransportDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.1#6.4.1.3.3',
    'DatagramWriterGroupTransportType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.3.1#9.3.1.2',
    'DateString': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.42',
    'DateTime': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.11',
    'Decimal': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.54',
    'DecimalString': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.43',
    'DeleteNodesItem': 'https://reference.opcfoundation.org/specs/OPC-10000-4/5.8.4#5.8.4.2',
    'DeleteReferencesItem': 'https://reference.opcfoundation.org/specs/OPC-10000-4/5.8.5#5.8.5.1',
    'DeviceFailureEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.29',
    'DeviceHealthDiagnosticAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.12.2',
    'DeviceHealthEnumeration': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.5.4',
    'DeviceType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.7',
    'DiagnosticInfo': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.12',
    'DiagnosticsLevel': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.11#9.1.11.4',
    'DialogConditionType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.6.2',
    'DiameterIndicationType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/10.8',
    'DictionaryEntryType': 'https://reference.opcfoundation.org/specs/OPC-10000-19/5.1',
    'DictionaryFolderType': 'https://reference.opcfoundation.org/specs/OPC-10000-19/5.2',
    'DirectLoadingType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.4.4#8.4.4.1',
    'DiscoveryConfiguration': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.13.1',
    'DiscrepancyAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.25',
    'DiscreteAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.24#5.8.24.1',
    'DiscreteItemType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.3#5.3.3.1',
    'Double': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.12',
    'DoubleComplexNumberType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.6.6',
    'DtlsPubSubConnectionDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.1#6.4.1.7.6',
    'Duplex': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.1#5.3.1.1',
    'Duration': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.13',
    'DurationString': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.44',
    'EUInformation': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.6.4#5.6.4.3',
    'EccApplicationCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.10',
    'EccBrainpoolP256r1ApplicationCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.13',
    'EccBrainpoolP384r1ApplicationCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.14',
    'EccCurve25519ApplicationCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.15',
    'EccCurve448ApplicationCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.16',
    'EccNistP256ApplicationCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.11',
    'EccNistP384ApplicationCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.12',
    'ElementOperand': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.7.4#7.7.4.2',
    'ElseGuardVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.6.6',
    'EncodedTicket': 'https://reference.opcfoundation.org/specs/OPC-10000-21/8.2.1',
    'EndpointDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.10.22',
    'EndpointDescription': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.14',
    'EndpointType': 'https://reference.opcfoundation.org/specs/OPC-10000-18/4.4.2',
    'EndpointUrlListDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.20',
    'EnumDefinition': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.50',
    'EnumDescription': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.34',
    'EnumField': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.52',
    'EnumValueType': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.39',
    'Enumeration': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.14',
    'EphemeralKeyType': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.15',
    'EventFilter': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.22.3',
    'EventNotifierType': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.59',
    'EventQueueOverflowEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.34',
    'ExceptionDeviationFormat': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.2.2',
    'ExclusiveDeviationAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.22#5.8.22.3',
    'ExclusiveLevelAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.21#5.8.21.3',
    'ExclusiveLimitAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.19#5.8.19.3',
    'ExclusiveLimitStateMachineType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.19#5.8.19.2',
    'ExclusiveRateOfChangeAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.23#5.8.23.3',
    'ExpandedNodeId': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.16',
    'ExpressionGuardVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.6.5',
    'ExtensionFieldsType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.4#9.1.4.2.2',
    'FailureAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.12.3',
    'FetchResultDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/6.4.6',
    'FieldMetaData': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.2.4',
    'FieldTargetDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.10#6.2.10.2.3',
    'FileDirectoryType': 'https://reference.opcfoundation.org/specs/OPC-10000-20/4.3.1',
    'FileSystemLoadingType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.4.6#8.4.6.1',
    'FileTransferStateMachineType': 'https://reference.opcfoundation.org/specs/OPC-10000-20/4.4.6',
    'FileType': 'https://reference.opcfoundation.org/specs/OPC-10000-20/4.2.1',
    'FilterOperand': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.7.4',
    'FilterOperator': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.7.3',
    'FiniteStateMachineType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.5',
    'FiniteStateVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.6',
    'FiniteTransitionVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.7',
    'Float': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.15',
    'FolderType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.6',
    'Frame': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.29',
    'FrameType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.27',
    'FromState': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.11',
    'FunctionalGroupType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.4.1',
    'GeneralModelChangeEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.32',
    'GeneratesEvent': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.15',
    'GuardVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.6.4',
    'Guid': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.16',
    'Handle': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.42',
    'HasAddIn': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.20',
    'HasAlarmSuppressionGroup': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.4.4',
    'HasArgumentDescription': 'https://reference.opcfoundation.org/specs/OPC-10000-3/5.7.2',
    'HasAttachedComponent': 'https://reference.opcfoundation.org/specs/OPC-10000-23/1',
    'HasCause': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.13',
    'HasChild': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.5',
    'HasComponent': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.7',
    'HasCondition': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.12',
    'HasContainedComponent': 'https://reference.opcfoundation.org/specs/OPC-10000-23/4.13.2',
    'HasCurrentData': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.3.3',
    'HasCurrentEvent': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.3.4',
    'HasDataSetReader': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.6#9.1.6.12',
    'HasDataSetWriter': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.6#9.1.6.6',
    'HasDataTypeRefinement': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.30',
    'HasDictionaryEntry': 'https://reference.opcfoundation.org/specs/OPC-10000-19/6.1',
    'HasEffect': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.14',
    'HasEffectDisable': 'https://reference.opcfoundation.org/specs/OPC-10000-9/7.2',
    'HasEffectEnable': 'https://reference.opcfoundation.org/specs/OPC-10000-9/7.3',
    'HasEffectSuppressed': 'https://reference.opcfoundation.org/specs/OPC-10000-9/7.4',
    'HasEffectUnsuppressed': 'https://reference.opcfoundation.org/specs/OPC-10000-9/7.5',
    'HasEncoding': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.14',
    'HasEngineeringUnitDetails': 'https://reference.opcfoundation.org/specs/OPC-10000-8/6.5.1',
    'HasEventSource': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.17',
    'HasFalseSubState': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.4.3',
    'HasFieldDescription': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.25',
    'HasFieldDescriptionSetMandatory': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.26',
    'HasGuard': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.6.3',
    'HasHistoricalConfiguration': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.3.2',
    'HasInterface': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.19',
    'HasKeyValueDescription': 'https://reference.opcfoundation.org/specs/OPC-10000-5/11.25',
    'HasLowerLayerInterface': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.6.2',
    'HasModellingRule': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.12',
    'HasNotifier': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.18',
    'HasOptionalInputArgumentDescription': 'https://reference.opcfoundation.org/specs/OPC-10000-3/5.7.3',
    'HasOrderedComponent': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.9',
    'HasPhysicalComponent': 'https://reference.opcfoundation.org/specs/OPC-10000-23/4.12.2',
    'HasProperty': 'https://reference.opcfoundation.org/specs/OPC-10000-3/5.3.3#5.3.3.2',
    'HasPubSubConnection': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.3#9.1.3.6',
    'HasPushedSecurityGroup': 'https://reference.opcfoundation.org/specs/OPC-10000-14/8.6.6',
    'HasQuantity': 'https://reference.opcfoundation.org/specs/OPC-10000-8/6.5.2',
    'HasReaderGroup': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.5#9.1.5.10',
    'HasSerializationEntity': 'https://reference.opcfoundation.org/specs/OPC-10000-25/6.5',
    'HasStructuredComponent': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.22.1',
    'HasSubStateMachine': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.15',
    'HasSubtype': 'https://reference.opcfoundation.org/specs/OPC-10000-3/5.3.3#5.3.3.3',
    'HasTrueSubState': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.4.2',
    'HasTypeDefinition': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.13',
    'HasWriterGroup': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.5#9.1.5.9',
    'HierarchicalReferences': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.3',
    'HighlyManagedAlarmConditionClassType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.9.7',
    'HistoricalDataConfigurationType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.2.2',
    'HistoricalEventConfigurationType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.4.3',
    'HistoricalExternalEventSourceType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.5.2',
    'HistoryEvent': 'https://reference.opcfoundation.org/specs/OPC-10000-11/6.6.4',
    'HistoryEventFieldList': 'https://reference.opcfoundation.org/specs/OPC-10000-11/6.6.4',
    'HistoryModifiedEvent': 'https://reference.opcfoundation.org/specs/OPC-10000-11/6.6.5',
    'HistoryServerCapabilitiesType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/5.7.2',
    'HistoryUpdateType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/6.7',
    'HttpsCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.3',
    'IAssetLocationIndicationType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.5.7',
    'IBaseEthernetCapabilitiesType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.4',
    'IDeviceHealthType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.5.4',
    'IIeeeAutoNegotiationStatusType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.3',
    'IIeeeBaseEthernetPortType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.2',
    'IIeeeBaseTsnStatusStreamType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.9',
    'IIeeeBaseTsnStreamType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.7',
    'IIeeeBaseTsnTrafficSpecificationType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.8',
    'IIeeeTsnInterfaceConfigurationListenerType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.12',
    'IIeeeTsnInterfaceConfigurationTalkerType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.11',
    'IIeeeTsnInterfaceConfigurationType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.10',
    'IIeeeTsnMacAddressType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.13',
    'IIeeeTsnVlanTagType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.14',
    'IIetfBaseNetworkInterfaceType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.1',
    'IMachineTagNameplateType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/8.5',
    'IMachineVendorNameplateType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/8.4',
    'IMachineryEquipmentType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/17.3',
    'IMachineryItemVendorNameplateType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/8.2',
    'IOperationCounterType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.5.5',
    'IOrderedObjectType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.11',
    'IPriorityMappingEntryType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.15',
    'ISrClassType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.6',
    'ISupportInfoType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.5.6',
    'ITagNameplateType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.5.3',
    'IVendorNameplateType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.5.2',
    'IVlanIdType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.2.5',
    'IdType': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.2.3',
    'IdentityCriteriaType': 'https://reference.opcfoundation.org/specs/OPC-10000-18/4.4.4',
    'IdentityMappingRuleType': 'https://reference.opcfoundation.org/specs/OPC-10000-18/4.4.3',
    'IetfBaseNetworkInterfaceType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.5.1#5.5.1.2',
    'Image': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.19',
    'ImageBMP': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.20',
    'ImageGIF': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.21',
    'ImageItemType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.4#5.3.4.4',
    'ImageJPG': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.22',
    'ImagePNG': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.23',
    'Index': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.18',
    'InitialStateType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.9',
    'InstallationStateMachineType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.4.9#8.4.9.1',
    'InstrumentDiagnosticAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.24#5.8.24.5',
    'Int16': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.25',
    'Int32': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.26',
    'Int64': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.27',
    'Integer': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.24',
    'IntegerId': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.19',
    'InterfaceAdminStatus': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.1#5.3.1.2',
    'InterfaceOperStatus': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.1#5.3.1.3',
    'IrdiDictionaryEntryType': 'https://reference.opcfoundation.org/specs/OPC-10000-19/5.3',
    'IsDeprecated': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.21',
    'IsDisabledOptionalField': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.27',
    'IsExecutableOn': 'https://reference.opcfoundation.org/specs/OPC-10000-23/4.2.2',
    'IsExecutingOn': 'https://reference.opcfoundation.org/specs/OPC-10000-23/4.3.2',
    'IsHostedBy': 'https://reference.opcfoundation.org/specs/OPC-10000-23/4.11.2',
    'IsOnline': 'https://reference.opcfoundation.org/specs/OPC-10000-100/6.3.2',
    'IsPhysicallyConnectedTo': 'https://reference.opcfoundation.org/specs/OPC-10000-23/4.7.2',
    'IssuedIdentityToken': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.40.6',
    'JsonDataSetMessageContentMask': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.3.2#6.3.2.3.1',
    'JsonDataSetReaderMessageDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.3.2#6.3.2.4.3',
    'JsonDataSetReaderMessageType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.2.2#9.2.2.3',
    'JsonDataSetWriterMessageDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.3.2#6.3.2.3.2',
    'JsonDataSetWriterMessageType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.2.2#9.2.2.2',
    'JsonNetworkMessageContentMask': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.3.2#6.3.2.1.1',
    'JsonWriterGroupMessageDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.3.2#6.3.2.1.2',
    'JsonWriterGroupMessageType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.2.2#9.2.2.1',
    'KeyCredentialAuditEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/8.5.8',
    'KeyCredentialConfigurationFolderType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/8.6.2',
    'KeyCredentialConfigurationType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/8.6.5',
    'KeyCredentialDeletedAuditEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/8.6.10',
    'KeyCredentialUpdatedAuditEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/8.6.9',
    'KeyValuePair': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.21',
    'LengthIndicationType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/10.7',
    'LifetimeVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/10.2',
    'LimitAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.18',
    'LinearConversionDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/6.6.2',
    'LiteralOperand': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.7.4#7.7.4.3',
    'LldpInformationType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.5.3',
    'LldpLocalSystemType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.5.4',
    'LldpManagementAddressTxPortType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.2#5.3.2.2',
    'LldpManagementAddressType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.2#5.3.2.3',
    'LldpPortInformationType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.5.5',
    'LldpRemoteStatisticsType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.5.4',
    'LldpRemoteSystemType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.5.6',
    'LldpSystemCapabilitiesMap': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.3#5.3.3.1',
    'LldpTlvType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.2#5.3.2.4',
    'LocaleId': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.4',
    'LocalizedText': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.5.1',
    'LocationIndicationType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.5.8',
    'LockingServicesType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/7.2',
    'LogEntryConditionClassType': 'https://reference.opcfoundation.org/specs/OPC-10000-26/6.5',
    'LogObjectType': 'https://reference.opcfoundation.org/specs/OPC-10000-26/5.2',
    'LogOverflowEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-26/6.4',
    'LogRecord': 'https://reference.opcfoundation.org/specs/OPC-10000-26/5.5',
    'LogRecordMask': 'https://reference.opcfoundation.org/specs/OPC-10000-26/5.8',
    'LogRecordsDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-26/5.10',
    'MachineComponentsType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/11.2',
    'MachineIdentificationType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/8.6',
    'MachineryComponentIdentificationType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/10.2',
    'MachineryEquipmentFolderType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/17.2',
    'MachineryItemIdentificationType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/8.3',
    'MachineryItemState_StateMachineType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/12.2',
    'MachineryLifetimeCounterType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/15.2',
    'MachineryOperationCounterType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/14.2',
    'MachineryOperationModeStateMachineType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/13.2',
    'MaintenanceConditionClassType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.9.4',
    'MaintenanceRequiredAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.12.6',
    'ManAddrIfSubtype': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.1#5.3.1.11',
    'MdnsDiscoveryConfiguration': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.13.2',
    'MessageSecurityMode': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.20',
    'ModelChangeStructureDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.16',
    'ModellingRuleType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.5',
    'ModificationInfo': 'https://reference.opcfoundation.org/specs/OPC-10000-11/6.6.5',
    'MonitoringFilter': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.22.1',
    'MonitoringType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/16.2',
    'MultiStateDictionaryEntryDiscreteBaseType': 'https://reference.opcfoundation.org/specs/OPC-10000-19/7.1',
    'MultiStateDictionaryEntryDiscreteType': 'https://reference.opcfoundation.org/specs/OPC-10000-19/7.2',
    'MultiStateDiscreteType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.3#5.3.3.3',
    'MultiStateValueDiscreteType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.3#5.3.3.4',
    'NDimensionArrayItemType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.4#5.3.4.6',
    'NameValuePair': 'https://reference.opcfoundation.org/specs/OPC-10000-26/5.7',
    'NamespaceMetadataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.13',
    'NamespacesType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.14',
    'NegotiationStatus': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.1#5.3.1.4',
    'NetworkAddressDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.7#6.2.7.5.3',
    'NetworkAddressType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.5#9.1.5.6',
    'NetworkAddressUrlDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.7#6.2.7.5.4',
    'NetworkAddressUrlType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.5#9.1.5.7',
    'NetworkGroupDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.19',
    'NetworkType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/5.3',
    'NodeClass': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.29',
    'NodeId': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.2.1',
    'NonExclusiveDeviationAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.22#5.8.22.2',
    'NonExclusiveLevelAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.21#5.8.21.2',
    'NonExclusiveLimitAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.20',
    'NonExclusiveRateOfChangeAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.23#5.8.23.2',
    'NonHierarchicalReferences': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.4',
    'NonTransparentBackupRedundancyType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.15',
    'NonTransparentNetworkRedundancyType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.10',
    'NonTransparentRedundancyType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.9',
    'NormalizedString': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.45',
    'NotificationsType': 'https://reference.opcfoundation.org/specs/OPC-40001-1/18.2',
    'Number': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.30',
    'NumberOfPartsIndicationType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/10.5',
    'NumberOfUsagesIndicationType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/10.6',
    'NumberRange': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.6.3',
    'NumericRange': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.27',
    'OffNormalAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.24#5.8.24.2',
    'OffSpecAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.12.5',
    'OperationLimitsType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.11',
    'OptionSet': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.40',
    'OptionSetType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.17',
    'OrderedListType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.10',
    'Organizes': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.11',
    'Orientation': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.27',
    'OrientationType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.25',
    'OverrideValueHandling': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.10#6.2.10.2.4',
    'PackageLoadingType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.4.3#8.4.3.1',
    'ParameterResultDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/6.4.6',
    'PasswordOptionsMask': 'https://reference.opcfoundation.org/specs/OPC-10000-18/5.2.2',
    'PerformUpdateType': 'https://reference.opcfoundation.org/specs/OPC-10000-11/6.8',
    'PermissionType': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.55',
    'PortIdSubtype': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.1#5.3.1.10',
    'PortableNodeId': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.38',
    'PortableQualifiedName': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.37',
    'PowerCycleStateMachineType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.4.10',
    'PrepareForUpdateStateMachineType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.4.8#8.4.8.1',
    'PriorityMappingEntryType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.2#5.3.2.1',
    'PriorityMappingTableType': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.5.2#5.5.2.2',
    'ProcessConditionClassType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.9.3',
    'ProgramDiagnostic2DataType': 'https://reference.opcfoundation.org/specs/OPC-10000-10/5.2.8',
    'ProgramDiagnostic2Type': 'https://reference.opcfoundation.org/specs/OPC-10000-10/5.2.9',
    'ProgramStateMachineType': 'https://reference.opcfoundation.org/specs/OPC-10000-10/5.2.1',
    'ProgramTransitionEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-10/5.2.5#5.2.5.2',
    'ProgressEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.35',
    'PropertyType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.3',
    'ProtocolType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/5.2',
    'ProvisionableDeviceType': 'https://reference.opcfoundation.org/specs/OPC-10000-21/9.3.3',
    'PubSubCapabilitiesType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.12#9.1.12.1',
    'PubSubCommunicationFailureEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.13#9.1.13.3',
    'PubSubConfiguration2DataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.12#6.2.12.4',
    'PubSubConfigurationDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.12#6.2.12.1',
    'PubSubConfigurationRefDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.3#9.1.3.7.3',
    'PubSubConfigurationRefMask': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.3#9.1.3.7.2',
    'PubSubConfigurationType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.3#9.1.3.7.1',
    'PubSubConfigurationValueDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.3#9.1.3.7.4',
    'PubSubConnectionDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.7#6.2.7.5.1',
    'PubSubConnectionType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.5#9.1.5.2',
    'PubSubDiagnosticsConnectionType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.11#9.1.11.8',
    'PubSubDiagnosticsCounterClassification': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.11#9.1.11.6',
    'PubSubDiagnosticsCounterType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.11#9.1.11.5',
    'PubSubDiagnosticsDataSetReaderType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.11#9.1.11.12',
    'PubSubDiagnosticsDataSetWriterType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.11#9.1.11.11',
    'PubSubDiagnosticsReaderGroupType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.11#9.1.11.10',
    'PubSubDiagnosticsRootType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.11#9.1.11.7',
    'PubSubDiagnosticsType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.11#9.1.11.2',
    'PubSubDiagnosticsWriterGroupType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.11#9.1.11.9',
    'PubSubGroupDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.5#6.2.5.7',
    'PubSubGroupType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.6#9.1.6.2',
    'PubSubKeyPushTargetDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.12#6.2.12.3',
    'PubSubKeyPushTargetFolderType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/8.7.1',
    'PubSubKeyPushTargetType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/8.6.1',
    'PubSubKeyServiceType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/8.3.1',
    'PubSubState': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.1',
    'PubSubStatusEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.13#9.1.13.1',
    'PubSubStatusType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.10#9.1.10.1',
    'PubSubTransportLimitsExceedEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.13#9.1.13.2',
    'PublishSubscribeType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.3#9.1.3.2',
    'PublishedActionDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.10.4',
    'PublishedActionMethodDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.10.6',
    'PublishedDataItemsDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.7.2',
    'PublishedDataItemsType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.4#9.1.4.3.1',
    'PublishedDataSetCustomSourceDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.9.2',
    'PublishedDataSetDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.5',
    'PublishedDataSetSourceDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.6',
    'PublishedDataSetType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.4#9.1.4.2.1',
    'PublishedEventsDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.8.4',
    'PublishedEventsType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.4#9.1.4.4.1',
    'PublishedVariableDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.3#6.2.3.7.1',
    'QosDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.1#6.4.1.1.2',
    'QualifiedName': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.3',
    'QuantityDimension': 'https://reference.opcfoundation.org/specs/OPC-10000-8/6.6.4',
    'QuantityType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/6.4.1',
    'Range': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.6.2',
    'RationalNumber': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.22',
    'RationalNumberType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.20',
    'ReaderGroupDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.8#6.2.8.2.1',
    'ReaderGroupMessageDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.8#6.2.8.2.3',
    'ReaderGroupMessageType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.6#9.1.6.14',
    'ReaderGroupTransportDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.8#6.2.8.2.2',
    'ReaderGroupTransportType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.6#9.1.6.13',
    'ReaderGroupType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.6#9.1.6.9',
    'ReceiveQosDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.1#6.4.1.1.5',
    'ReceiveQosPriorityDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.1#6.4.1.1.6.2',
    'RedundancySupport': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.5',
    'RedundantServerDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.7',
    'RedundantServerMode': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.44',
    'References': 'https://reference.opcfoundation.org/specs/OPC-10000-8/6.5.1',
    'RefreshEndEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.11.3',
    'RefreshRequiredEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.11.4',
    'RefreshStartEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.11.2',
    'RegisteredServer': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.31',
    'RelativePath': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.30',
    'RelativePathElement': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.30',
    'RepresentsSameEntityAs': 'https://reference.opcfoundation.org/specs/OPC-10000-23/4.8.2',
    'RepresentsSameFunctionalityAs': 'https://reference.opcfoundation.org/specs/OPC-10000-23/4.10.2',
    'RepresentsSameHardwareAs': 'https://reference.opcfoundation.org/specs/OPC-10000-23/4.9.2',
    'Requires': 'https://reference.opcfoundation.org/specs/OPC-10000-23/4.6.2',
    'RoleMappingRuleChangedAuditEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-18/4.5',
    'RolePermissionType': 'https://reference.opcfoundation.org/specs/OPC-10000-3/5.2.9',
    'RoleSetType': 'https://reference.opcfoundation.org/specs/OPC-10000-18/4.2.1',
    'RoleType': 'https://reference.opcfoundation.org/specs/OPC-10000-18/4.4.1',
    'RsaMinApplicationCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.8',
    'RsaSha256ApplicationCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.9',
    'SByte': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.2.9#12.2.9.9',
    'SafetyConditionClassType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.9.6',
    'SamplingIntervalDiagnosticsArrayType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.9',
    'SamplingIntervalDiagnosticsDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.8',
    'SamplingIntervalDiagnosticsType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.10',
    'SecurityGroupDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.12#6.2.12.2',
    'SecurityGroupFolderType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/8.5.1',
    'SecurityGroupType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/8.4.1',
    'SecuritySettingsDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.10.24',
    'SecurityTokenRequestType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.3.12',
    'SelectionListType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.18',
    'SemanticChangeEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.33',
    'SemanticChangeStructureDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.17',
    'SemanticVersionString': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.41',
    'SerializationEntityType': 'https://reference.opcfoundation.org/specs/OPC-10000-25/6.3.1',
    'ServerCapabilitiesType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.2',
    'ServerConfigurationType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.10.3',
    'ServerDiagnosticsSummaryDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.9',
    'ServerDiagnosticsSummaryType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.8',
    'ServerDiagnosticsType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.3',
    'ServerEndpointDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.10.23',
    'ServerOnNetwork': 'https://reference.opcfoundation.org/specs/OPC-10000-4/5.5.3#5.5.3.2',
    'ServerRedundancyType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.7',
    'ServerState': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.6',
    'ServerStatusDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.10',
    'ServerStatusType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.6',
    'ServerType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.1',
    'ServerUnitType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/6.4.2#6.4.2.3',
    'ServerVendorCapabilityType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.5',
    'ServiceCertificateDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/9.7.5',
    'ServiceCounterDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.13',
    'SessionAuthenticationToken': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.35',
    'SessionDiagnosticsArrayType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.13',
    'SessionDiagnosticsDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.11',
    'SessionDiagnosticsObjectType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.5',
    'SessionDiagnosticsVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.14',
    'SessionSecurityDiagnosticsArrayType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.15',
    'SessionSecurityDiagnosticsDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.12',
    'SessionSecurityDiagnosticsType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.16',
    'SessionsDiagnosticsSummaryType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.4',
    'ShelvedStateMachineType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.17#5.8.17.1',
    'SignatureData': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.36',
    'SignedSoftwareCertificate': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.37',
    'SimpleAttributeOperand': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.7.4#7.7.4.5',
    'SimpleTypeDescription': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.35',
    'SoftwareClass': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.5.3',
    'SoftwareFolderType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.4.12',
    'SoftwareLoadingType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.4.2#8.4.2.1',
    'SoftwareType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.8',
    'SoftwareUpdateType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.4.1#8.4.1.1',
    'SoftwareVersionFileType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.5.1',
    'SoftwareVersionType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.4.7#8.4.7.1',
    'SpanContextDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-26/5.6.2',
    'StandaloneSubscribedDataSetDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.10#6.2.10.5',
    'StandaloneSubscribedDataSetRefDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.10#6.2.10.4',
    'StandaloneSubscribedDataSetType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.9#9.1.9.5',
    'StateMachineType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.2',
    'StateType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.8',
    'StateVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.3',
    'StatisticalConditionClassType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.9.9',
    'StatusCode': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.11.5',
    'StatusResult': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.14',
    'String': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.31',
    'Structure': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.32',
    'StructureDefinition': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.48',
    'StructureDescription': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.33',
    'StructureField': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.51',
    'StructureType': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.49',
    'SubscribedDataSetDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.10#6.2.10.1',
    'SubscribedDataSetFolderType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.9#9.1.9.4.1',
    'SubscribedDataSetMirrorDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.10#6.2.10.3.4',
    'SubscribedDataSetMirrorType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.9#9.1.9.3',
    'SubscribedDataSetType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.9#9.1.9.1',
    'SubscriptionDiagnosticsArrayType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.11',
    'SubscriptionDiagnosticsDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.15',
    'SubscriptionDiagnosticsType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.12',
    'SubstanceVolumeIndicationType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/10.9',
    'SubtypeRestrictionType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.13',
    'SyntaxReferenceEntryType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/6.4.3',
    'SystemConditionClassType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.9.5',
    'SystemDiagnosticAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.24#5.8.24.6',
    'SystemEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.28',
    'SystemOffNormalAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.24#5.8.24.3',
    'SystemStatusChangeEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.4.30',
    'TargetVariablesDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.10#6.2.10.2.2',
    'TargetVariablesType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.9#9.1.9.2.1',
    'TemporaryFileTransferType': 'https://reference.opcfoundation.org/specs/OPC-10000-20/4.4.1',
    'TestingConditionClassType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.9.10',
    'TimeIndicationType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/10.4',
    'TimeString': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.46',
    'TimeZoneDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.28',
    'TlsCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.5',
    'TlsClientCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.7',
    'TlsServerCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.6',
    'ToState': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.12',
    'TopologyElementType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.3',
    'TraceContextDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-26/5.6.3',
    'TrainingConditionClassType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.9.8',
    'TransactionDiagnosticsType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.10.17',
    'TransactionErrorType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.10.18',
    'TransferResultDataDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/6.4.6',
    'TransferResultErrorDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/6.4.6',
    'TransferServicesType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/6.4.2',
    'TransitionEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.16',
    'TransitionType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.10',
    'TransitionVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-16/4.4.4',
    'TransmitQosDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.1#6.4.1.1.3',
    'TransmitQosPriorityDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.4.1#6.4.1.1.4.2',
    'TransparentRedundancyType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.8',
    'TrimmedString': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.43',
    'TripAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.8.24#5.8.24.4',
    'TrustListDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.2#7.8.2.8',
    'TrustListMasks': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.2#7.8.2.9',
    'TrustListOutOfDateAlarmType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.2#7.8.2.11',
    'TrustListType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.2#7.8.2.1',
    'TrustListUpdateRequestedAuditEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.2#7.8.2.12',
    'TrustListUpdatedAuditEventType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.2#7.8.2.13',
    'TrustListValidationOptions': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.2#7.8.2.10',
    'TsnFailureCode': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.1#5.3.1.5',
    'TsnListenerStatus': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.1#5.3.1.8',
    'TsnStreamState': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.1#5.3.1.6',
    'TsnTalkerStatus': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.3.1#5.3.1.7',
    'TwoStateDiscreteType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.3#5.3.3.2',
    'TwoStateVariableType': 'https://reference.opcfoundation.org/specs/OPC-10000-9/5.2',
    'UABinaryFileDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.36',
    'UIElementType': 'https://reference.opcfoundation.org/specs/OPC-10000-100/4.4.3',
    'UInt16': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.34',
    'UInt32': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.35',
    'UInt64': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.36',
    'UInteger': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.33',
    'UadpDataSetMessageContentMask': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.3.1#6.3.1.3.2',
    'UadpDataSetReaderMessageDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.3.1#6.3.1.4.10',
    'UadpDataSetReaderMessageType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.2.1#9.2.1.3',
    'UadpDataSetWriterMessageDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.3.1#6.3.1.3.6',
    'UadpDataSetWriterMessageType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.2.1#9.2.1.2',
    'UadpNetworkMessageContentMask': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.3.1#6.3.1.1.4',
    'UadpWriterGroupMessageDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.3.1#6.3.1.1.7',
    'UadpWriterGroupMessageType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.2.1#9.2.1.1',
    'Union': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.41',
    'UnitType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/6.4.2#6.4.2.2',
    'UnsignedRationalNumber': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.40',
    'UpdateBehavior': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.5.2',
    'UpdateParent': 'https://reference.opcfoundation.org/specs/OPC-10000-100/8.6.1',
    'UriDictionaryEntryType': 'https://reference.opcfoundation.org/specs/OPC-10000-19/5.4',
    'UriString': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.39',
    'UserCertificateType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.8.4#7.8.4.4',
    'UserConfigurationMask': 'https://reference.opcfoundation.org/specs/OPC-10000-18/5.2.3',
    'UserIdentityToken': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.40.1',
    'UserManagementDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-18/5.2.4',
    'UserManagementType': 'https://reference.opcfoundation.org/specs/OPC-10000-18/5.2.1',
    'UserNameIdentityToken': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.40.4',
    'UserTokenPolicy': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.41',
    'UserTokenSettingsDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-12/7.10.25',
    'UserTokenType': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.42',
    'UsesDataTypeRefinement': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.24',
    'UsesPriorityMappingTable': 'https://reference.opcfoundation.org/specs/OPC-10000-22/5.6.1',
    'UsesSubtypeRestriction': 'https://reference.opcfoundation.org/specs/OPC-10000-3/7.28',
    'UtcTime': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.37',
    'Utilizes': 'https://reference.opcfoundation.org/specs/OPC-10000-23/4.5.2',
    'Vector': 'https://reference.opcfoundation.org/specs/OPC-10000-5/12.23',
    'VectorType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/7.21',
    'VendorServerInfoType': 'https://reference.opcfoundation.org/specs/OPC-10000-5/6.3.6',
    'VersionTime': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.43',
    'WriterGroupDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.6#6.2.6.7.1',
    'WriterGroupMessageDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.6#6.2.6.7.3',
    'WriterGroupMessageType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.6#9.1.6.8',
    'WriterGroupTransportDataType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/6.2.6#6.2.6.7.2',
    'WriterGroupTransportType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.6#9.1.6.7',
    'WriterGroupType': 'https://reference.opcfoundation.org/specs/OPC-10000-14/9.1.6#9.1.6.3',
    'X509IdentityToken': 'https://reference.opcfoundation.org/specs/OPC-10000-4/7.40.5',
    'XVType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.6.9',
    'XYArrayItemType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.4#5.3.4.3',
    'XmlElement': 'https://reference.opcfoundation.org/specs/OPC-10000-3/8.38',
    'YArrayItemType': 'https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.4#5.3.4.2',
}

_FRIENDLY = {
    "i=58": "BaseObjectType", "i=61": "FolderType", "i=63": "BaseDataVariableType",
    "i=68": "PropertyType", "i=17497": "AnalogUnitType", "i=76": "DataTypeEncodingType",
    "i=2771": "FiniteStateMachineType", "i=2307": "StateType", "i=2309": "InitialStateType",
    "i=2310": "TransitionType", "i=10637": "OffNormalAlarmType",
    "i=1": "Boolean", "i=3": "Byte", "i=5": "UInt16", "i=7": "UInt32", "i=6": "Int32",
    "i=11": "Double", "i=12": "String", "i=13": "DateTime", "i=21": "LocalizedText",
    "i=290": "Duration", "i=296": "Argument", "i=29": "Enumeration", "i=22": "Structure",
    f"ns={DI};i=1002": "DeviceType [DI]", f"ns={DI};i=15063": "ComponentType [DI]",
    f"ns={MC};i=1012": "MachineIdentificationType [Machinery]",
    f"ns={MC};i=1002": "MachineryItemState_StateMachineType [Machinery]",
    f"ns={MC};i=1008": "MachineryOperationModeStateMachineType [Machinery]",
}
_RULE = {MR_Mandatory: "Mandatory", MR_Optional: "Optional",
         MR_OptionalPlaceholder: "OptionalPlaceholder",
         MR_MandatoryPlaceholder: "MandatoryPlaceholder"}

# --- reference.opcfoundation.org / intra-doc linking -----------------------
_OWN = {NODES[nid].bname for nid in ORDER
        if NODES[nid].cls in ("UAObjectType", "UADataType")}
_PRIMITIVES = {
    "Boolean", "SByte", "Byte", "Int16", "UInt16", "Int32", "UInt32", "Int64",
    "UInt64", "Float", "Double", "String", "DateTime", "Guid", "ByteString",
    "XmlElement", "NodeId", "ExpandedNodeId", "StatusCode", "QualifiedName",
    "LocalizedText", "DataValue", "Variant", "DiagnosticInfo", "Duration",
    "UtcTime", "Number", "Integer", "UInteger", "BaseDataType", "NumericRange",
}
_NSHINT = re.compile(r"\s*\[(DI|Machinery|IA)\]$")


def _anchor(name):
    return "type-" + name


def _ownlink(name):
    if name in _OWN:
        return f"[{name}](#{_anchor(name)})"
    return name


def _link(display):
    """Wrap an external named type in a reference.opcfoundation.org link, or an
    own type in an intra-doc anchor. Primitive built-ins are left as plain text.
    Namespace hints ('[DI]') and array suffixes ('[]') are kept as literal text
    outside the link so markdown never breaks."""
    if not display:
        return display
    core = display
    arr = ""
    if core.endswith("[]"):
        arr = r"\[\]"
        core = core[:-2]
    hint = ""
    m = _NSHINT.search(core)
    if m:
        hint = " \\[" + m.group(1) + "\\]"
        core = core[:m.start()]
    core = core.strip()
    if core in _OWN:
        body = f"[{core}](#{_anchor(core)})"
    elif core in LINK_MAP and core not in _PRIMITIVES:
        body = f"[{core}]({LINK_MAP[core]})"
    else:
        body = core
    return body + hint + arr


def _clink(name):
    """Linked code-span for prose: `name` -> [`name`](url) when linkable."""
    if name in _OWN:
        return f"[`{name}`](#{_anchor(name)})"
    if name in LINK_MAP and name not in _PRIMITIVES:
        return f"[`{name}`]({LINK_MAP[name]})"
    return f"`{name}`"


def _friendly(tgt):
    if tgt in _FRIENDLY:
        return _FRIENDLY[tgt]
    if tgt in DATATYPE_ALIAS:
        return DATATYPE_ALIAS[tgt]
    if tgt.startswith(f"ns={GEN};i="):
        num = int(tgt.split("i=")[1])
        if num in NODES:
            return NODES[num].bname
    return tgt


def _member_reftype(n):
    for rt, tgt, fwd in n.refs:
        if rt == HasModellingRule:
            return _RULE.get(tgt, tgt)
    return ""


def _typedef(n):
    for rt, tgt, fwd in n.refs:
        if rt == HasTypeDefinition:
            return _friendly(tgt)
    return ""


def _members_of(type_nid):
    out = []
    seen = set()
    for rt, tgt, fwd in NODES[type_nid].refs:
        if rt in (HasComponent, HasProperty, HasAddIn) and fwd and tgt.startswith(f"ns={GEN};i="):
            num = int(tgt.split("i=")[1])
            if num in NODES and num not in seen:
                seen.add(num)
                out.append(num)
    return out


def emit_md():
    _BASE_KEY = {
        DI_DeviceType: "DeviceType", DI_ComponentType: "ComponentType",
        MC_MachineIdentificationType: "MachineIdentificationType",
        FiniteStateMachineType: "FiniteStateMachineType",
        OffNormalAlarmType: "OffNormalAlarmType",
    }
    obj_types = [nid for nid in ORDER if NODES[nid].cls == "UAObjectType"]
    data_types = [nid for nid in ORDER if NODES[nid].cls == "UADataType"]

    def supertype(n):
        for rt, tgt, fwd in n.refs:
            if rt == HasSubtype and not fwd:
                return tgt
        return ""

    # index methods -> input argument names
    method_args = {}
    for nid in ORDER:
        n = NODES[nid]
        if n.cls == "UAVariable" and n.bname == "InputArguments" and n.value:
            names = re.findall(r"<Name>([^<]+)</Name>", n.value)
            pid = int(n.parent.split("i=")[1]) if n.parent else None
            if pid is not None:
                method_args[pid] = names

    md = []
    md.append('<a id="annex-a"></a>')
    md.append("")
    md.append("## Annex A \u2014 Information model\n")
    md.append("This annex is the normative node reference. It is generated directly from "
              "`tools/build_model.py` and therefore always matches "
              "`Opc.Ua.Generators.NodeSet2.xml`. It is organised by NodeClass. For every "
              "ObjectType and DataType the full structure is given, and the **Declared in** "
              "column names the type that declares each member — rows whose *Declared in* "
              "value differs from the type being described are **inherited** from a base type "
              "in OPC UA, Devices (DI) or Machinery.\n")

    md.append("### Type overview\n")
    md.append("| NodeId | BrowseName | NodeClass | Subtype of |")
    md.append("|---|---|---|---|")
    for nid in obj_types + data_types:
        n = NODES[nid]
        md.append(f"| ns=1;i={nid} | {_ownlink(n.bname)} | {n.cls[2:]} | {_link(_friendly(supertype(n)))} |")
    md.append("")

    md.append("### Object types\n")
    for nid in obj_types:
        n = NODES[nid]
        base = _friendly(supertype(n))
        md.append(f'<a id="{_anchor(n.bname)}"></a>')
        md.append("")
        md.append(f"#### {n.bname}  (ns=1;i={nid})\n")
        md.append(f"*Inherits from:* {_link(base)}\n")
        if n.desc:
            md.append(n.desc + "\n")
        md.append("| BrowseName | NodeClass | DataType | ModellingRule | Declared in | Description |")
        md.append("|---|---|---|---|---|---|")
        for m in _members_of(nid):
            mn = NODES[m]
            dt = _friendly(mn.attrs.get("DataType", "")) if mn.attrs.get("DataType") else ""
            if mn.attrs.get("ValueRank", "") == "1" and dt:
                dt += "[]"
            md.append(f"| {mn.bname} | {mn.cls[2:]} | {_link(dt)} | {_member_reftype(mn)} | "
                      f"{n.bname} | {(mn.desc or '').replace('|', '/')} |")
        base_key = _BASE_KEY.get(supertype(n))
        for (bn, cls, dtype, rule, decl) in BASE_MEMBERS.get(base_key, []):
            md.append(f"| {bn} | {cls} | {_link(dtype)} | {rule} | {_link(decl)} | |")
        md.append("")

    md.append("### Data types\n")
    for nid in data_types:
        n = NODES[nid]
        md.append(f'<a id="{_anchor(n.bname)}"></a>')
        md.append("")
        md.append(f"#### {n.bname}  (ns=1;i={nid})\n")
        md.append(f"*Subtype of:* {_link(_friendly(supertype(n)))}\n")
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
            for mm in re.finditer(r'<Field Name="([^"]+)" DataType="([^"]+)"[^>]*?(?:/>|>(?:<Description>([^<]*)</Description>)?</Field>)', n.definition):
                md.append(f"| {mm.group(1)} | {_link(_friendly(mm.group(2)))} | {mm.group(3) or ''} |")
            md.append("")

    md.append("### Objects\n")
    md.append(
        "All Object-class nodes in this model are instance declarations of the ObjectTypes "
        "above and appear in their structure tables. They fall into four groups: sub-assembly "
        f"**components** referenced with {_clink('HasComponent')} (for example `Engine`, "
        "`Alternator`, `L1`/`L2`/`L3`, `Source1`/`Source2`); standardized **Machinery "
        f"building-block add-ins** referenced with {_clink('HasAddIn')} (`Identification`, "
        "`MachineryBuildingBlocks`, `MachineryItemState`, `MachineryOperationMode`); the "
        f"finite-state-machine **States and Transitions** of {_clink('GeneratorStateMachineType')}; "
        "and the **DataType encodings** (`Default Binary`, `Default XML`) of "
        f"{_clink('DiagnosticTroubleCodeType')}. This specification defines no free-standing "
        "Object instances; live instances are created by the server in its address space.\n")

    md.append("### Variables\n")
    md.append(
        "All Variable-class nodes are instance declarations of the types above. Measured values "
        f"are typed {_clink('AnalogUnitType')} and each carries a child `EngineeringUnits` "
        "property whose value is a standard UNECE/CEFACT unit; status and configuration values "
        f"are typed {_clink('BaseDataVariableType')} or {_clink('PropertyType')}. Standard child "
        "variables also appear: `EngineeringUnits` (on every analog value), `EnumStrings` (on "
        "every enumeration DataType), `StateNumber`/`TransitionNumber` (on FSM states and "
        "transitions) and `InputArguments` (on methods that take parameters).\n")

    md.append("### Methods\n")
    md.append("| Method | Owning type | Input arguments |")
    md.append("|---|---|---|")
    for nid in ORDER:
        n = NODES[nid]
        if n.cls != "UAMethod":
            continue
        owner = NODES[int(n.parent.split("i=")[1])].bname if n.parent else ""
        args = ", ".join(method_args.get(nid, [])) or "(none)"
        md.append(f"| {n.bname} | {_ownlink(owner)} | {args} |")
    md.append("")

    md.append("### Reference types\n")
    md.append(
        "This specification defines no custom ReferenceTypes. It uses the standard OPC UA "
        f"references {_clink('HasComponent')}, {_clink('HasProperty')}, {_clink('HasAddIn')}, "
        f"{_clink('HasInterface')}, {_clink('GeneratesEvent')}, {_clink('HasSubtype')}, "
        f"{_clink('HasTypeDefinition')}, {_clink('HasModellingRule')}, {_clink('FromState')}, "
        f"{_clink('ToState')} and {_clink('HasEncoding')}.\n")
    return "\n".join(md).rstrip() + "\n"


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.dirname(here)  # companion-specs/Generators/
    with open(os.path.join(outdir, "Opc.Ua.Generators.NodeSet2.xml"), "w",
              encoding="utf-8") as f:
        f.write(emit())
    with open(os.path.join(outdir, "Opc.Ua.Generators.NodeIds.csv"), "w",
              encoding="utf-8") as f:
        f.write(emit_csv())
    with open(os.path.join(here, "model-reference.md"), "w",
              encoding="utf-8") as f:
        f.write(emit_md())
    n_types = sum(1 for k in NODES if NODES[k].cls in ("UAObjectType", "UADataType"))
    print(f"Nodes: {len(NODES)}  (ObjectTypes+DataTypes: {n_types})")
    print(f"Member id range: 6001..{_next_member[0] - 1}")

