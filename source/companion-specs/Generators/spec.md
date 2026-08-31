## Scope {#sec-scope}

This specification defines the OPC UA ObjectTypes, VariableTypes, DataTypes, ReferenceTypes and their instances required to represent a generator set as an automation **asset** and, at the same time, as a machine that is **built around a prime‑mover engine** exposing a CAN bus / SAE J1939 interface.

The model covers:

- The generator set as a whole (nameplate/identification, ratings, operating state and mode, health, control methods).
- The prime‑mover **engine**, its telemetry (typically read over CAN/J1939) and its diagnostic trouble codes (DTCs).
- The **alternator** (generator end), including per‑phase and aggregate electrical measurements.
- Supporting subsystems: **fuel**, **cooling**, **lubrication**, **starting/battery**, and **exhaust aftertreatment**.
- The **controller / control panel** and its remote‑monitoring status.
- **Protection and alarm** functions (warnings, shutdowns, electrical trips, lockouts).
- **Automatic transfer switches (ATS)** and **paralleling / switchgear** for multi‑set power systems.

The model deliberately reuses the OPC UA **Devices (DI)** and **Machinery** companion specifications so that generator sets appear as first‑class members of the existing OPC UA machine/asset ecosystem.

## General description {#sec-general-description}

### What is a generator set? {#sec-what-is-a-generator-set}

A generator set is simultaneously two things: an **asset** with a nameplate, health and a life‑cycle; and a **machine** whose core is an internal‑combustion engine coupled to an alternator. Sizes span four orders of magnitude of power. A small residential unit may produce ~13 kW on natural gas; a large industrial set built on a ~95 L V16 high‑speed diesel engine can deliver **3.0–3.75 MW**, is the size of a small house, and consumes on the order of **130–210 US gal/h** of diesel at full load. Between those extremes lie commercial standby, data‑center, healthcare, rental/mobile and marine products.

Whatever the size, every set exposes broadly the same information: identity, ratings, an operating state and mode, engine and alternator telemetry, fuel/cooling/lubrication/battery status, protections/alarms and start/stop control. This specification captures that common information once, so that a single client can monitor and (where permitted) control any conforming set.

### Relationship to other companion specifications {#sec-relationship-to-other-companion-specifications}

This model is layered on established OPC UA building blocks rather than reinventing them:

- **DI (Devices).** [`GeneratorSetType`](#sec-generatorsettype) derives from the DI `DeviceType`, inheriting a complete nameplate (`Manufacturer`, `Model`, `SerialNumber`, `HardwareRevision`, `SoftwareRevision`, `DeviceRevision`, `RevisionCounter`, …) and `DeviceHealth` (`NORMAL`/`FAILURE`/`CHECK_FUNCTION`/`OFF_SPEC`/`MAINTENANCE_REQUIRED`). Each subsystem (engine, alternator, fuel system, …) derives from the DI `ComponentType`, the standard base for an identifiable component of a device.
- **Machinery.** Every set carries the Machinery building blocks so that it is discoverable and interoperable alongside other machines: an `Identification` add‑in (a [`GeneratorIdentificationType`](#sec-generatoridentificationtype), which specialises the Machinery `MachineIdentificationType`) and a `MachineryBuildingBlocks` folder holding the generic `MachineryItemState` and `MachineryOperationMode` state machines.
- **Part 9 (Alarms & Conditions).** Protection events are modelled by [`GeneratorProtectionAlarmType`](#sec-generatorprotectionalarmtype), a subtype of `OffNormalAlarmType`.
- **Part 5 / Part 16 (State machines).** The detailed run states of a set are modelled by [`GeneratorStateMachineType`](#sec-generatorstatemachinetype), a `FiniteStateMachineType`.

### Namespaces {#sec-namespaces}

| Index | Namespace URI | Role |
|---|---|---|
| 0 | `http://opcfoundation.org/UA/` | OPC UA core |
| 1 | `http://opcfoundation.org/UA/Generators/` | This specification |
| 2 | `http://opcfoundation.org/UA/DI/` | Devices |
| 3 | `http://opcfoundation.org/UA/Machinery/` | Machinery |

Numeric NodeIds in namespace 1 are allocated as follows: ObjectTypes `1001–1099`, DataTypes `3001–3099` (enumerations) and `3050+` (structures), EnumStrings properties `datatype‑id + 900`, and all remaining instance declarations (members, method arguments, state‑machine states and transitions) sequentially from `6001`.

## Information‑model architecture {#sec-information-model-architecture}

The AddressSpace figures in this document use the OPC UA graphical notation of OPC 10000-3. A Node of an instance NodeClass — Object, Variable or View — is a plain rectangle, a Method is a rounded rectangle, and a type — ObjectType, VariableType, ReferenceType or DataType — is a rectangle standing on a shadow. An abstract type is set in *italics*, and a Node whose BrowseName is a placeholder is written in angle brackets. A `HasTypeDefinition` reference carries a solid arrowhead; a `HasComponent` reference is the plain unlabelled arrow; every other ReferenceType is drawn with its BrowseName on the arrow. A figure shows the part of the model its clause describes, never the whole of it.

```{figure}
id: fig-gen-notation
caption: Graphical notation used by the AddressSpace figures
source: figures/Generators-FigNotation.png
```

### Composition of a generator set {#sec-composition-of-a-generator-set}

```{figure}
id: fig-gen-composition
caption: Composition of a generator set
source: figures/Generators-Fig1-Composition.png
```

A multi‑set installation (data‑center, healthcare, campus) is represented by [`GeneratorSystemType`](#sec-generatorsystemtype), which aggregates one or more [`GeneratorSetType`](#sec-generatorsettype) instances, an optional [`ParallelingControllerType`](#sec-parallelingcontrollertype) and one or more [`AutomaticTransferSwitchType`](#sec-automatictransferswitchtype) instances.

### Design rationale {#sec-design-rationale}

- **Asset + machine, not either/or.** Deriving from `DeviceType` gives the set an asset identity and health; adding the Machinery building blocks makes it discoverable as a machine. The `Identification` add‑in intentionally mirrors a few nameplate fields already present on `DeviceType`; the add‑in is the cross‑vendor, Machinery‑standard location, whereas the inherited `DeviceType` fields are the DI‑native location. Servers may populate either or both, but where both are present the equivalent fields (`Manufacturer`, `Model`, `SerialNumber`, `ProductInstanceUri`) **shall** carry the same value.
- **Composition over deep inheritance** (OPC 11030 §7.2.4). Subsystems are separate `ComponentType` subtypes referenced by `HasComponent`, so a set can be assembled from exactly the components it has (a home‑standby air‑cooled unit omits the paralleling controller; a Tier 4 diesel adds [`ExhaustAftertreatment`](#sec-exhaustaftertreatmenttype)).
- **Physical quantities use `AnalogUnitType` with machine‑readable units.** Every measured value is typed `AnalogUnitType` and carries an `EngineeringUnits` property whose value is a standard UNECE/CEFACT unit (e.g. `r/min`, `kPa`, `°C`, `kW`, `Hz`), so a client can discover the unit from the type model alone. A server **may** override this default at instance level to reflect the unit it actually reports (e.g. `psi`, `gal/h`, `°F`); the value range (`EURange`) is left to the instance.
- **The engine's CAN/J1939 interface is explicit.** Because a generator is "part engine with a CAN bus interface", the engine exposes a dedicated [`J1939DiagnosticInterfaceType`](#sec-j1939diagnosticinterfacetype) add‑in carrying the network parameters, the J1939 lamp status and the active/previously‑active DTC arrays.

## ObjectTypes {#sec-objecttypes}

The full member tables for every type are in **[Annex A](#anx-a)**. This clause summarises the intent of each type.

### [GeneratorSetType](#sec-generatorsettype) {#sec-generatorsettype}

The central type. Mandatory content: `OperatingState` (a `GeneratorStateMachineType`), `OperatingMode`, the `Engine`, `Alternator` and `Controller` components, the `Identification` add‑in and a `Ratings` folder. Optional content: fuel/cooling/lubrication/starting subsystems, `EmissionsStandard`, `Application`, breaker and readiness signals (`GeneratorBreakerClosed`, `GeneratorBreakerAvailable`, `RemoteStartInput`, `RunRequest`, `LoadInhibit`, `AvailableToLoad`), and the Machinery building blocks. Methods: `Start` (no argument — starts in the current mode), `Stop`, `EmergencyStop`, `ResetFaults`, `SetOperatingMode`, `StartTest`. The type `GeneratesEvent` `GeneratorProtectionAlarmType`.

The figure shows the Mandatory content — what a conforming generator set always has. The optional subsystems, signals and Methods listed above are omitted; Annex A carries the full member list.

<!-- model-figure: root=ns=1;i=1001 require=mandatory external=DeviceType  graph=figures/fig-gen-setmembers.mmd -->

```{figure}
id: fig-gen-setmembers
caption: The Mandatory content of a generator set
source: figures/Generators-FigSetMembers.png
```

*Table - GeneratorSetType Definition* {#tbl-generatorsettype-definition defines=GeneratorSetType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:GeneratorSetType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:DeviceType defined in OPC 10000-100 |  |  |  |  |  |
| 0:HasAddIn | Object | 2:Identification |  | 1:GeneratorIdentificationType | M |
| 0:HasAddIn | Object | 3:MachineryBuildingBlocks |  | 0:FolderType | O |
| 0:HasComponent | Object | 1:OperatingState |  | 1:GeneratorStateMachineType | M |
| 0:HasComponent | Variable | 1:OperatingMode | 1:GeneratorOperatingModeEnum | 0:BaseDataVariableType | M |
| 0:HasComponent | Variable | 1:EmissionsStandard | 1:EmissionsStandardEnum | 0:BaseDataVariableType | O |
| 0:HasProperty | Variable | 1:Application | 0:String | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:GeneratorBreakerClosed | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:GeneratorBreakerAvailable | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:RemoteStartInput | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:RunRequest | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:LoadInhibit | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:AvailableToLoad | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Object | 1:Engine |  | 1:EngineType | M |
| 0:HasComponent | Object | 1:Alternator |  | 1:AlternatorType | M |
| 0:HasComponent | Object | 1:Controller |  | 1:GeneratorControllerType | M |
| 0:HasComponent | Object | 1:FuelSystem |  | 1:FuelSystemType | O |
| 0:HasComponent | Object | 1:CoolingSystem |  | 1:CoolingSystemType | O |
| 0:HasComponent | Object | 1:LubricationSystem |  | 1:LubricationSystemType | O |
| 0:HasComponent | Object | 1:StartingSystem |  | 1:StartingSystemType | O |
| 0:HasComponent | Object | 1:Ratings |  | 0:FolderType | M |
| 0:HasComponent | Method | 1:Start |  |  | O |
| 0:HasComponent | Method | 1:Stop |  |  | O |
| 0:HasComponent | Method | 1:EmergencyStop |  |  | O |
| 0:HasComponent | Method | 1:ResetFaults |  |  | O |
| 0:HasComponent | Method | 1:SetOperatingMode |  |  | O |
| 0:HasComponent | Method | 1:StartTest |  |  | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

#### Start {#sec-generatorsettype-start type=GeneratorSetType method=Start}

Command the set to start in the current operating mode.

**Signature**

```text
Start ();
```

*Table - Start Method Arguments* {#tbl-start-method-arguments}

| **Argument** | **Description** |
| --- | --- |

#### Stop {#sec-generatorsettype-stop type=GeneratorSetType method=Stop}

Command a normal stop (with cooldown).

**Signature**

```text
Stop ();
```

*Table - Stop Method Arguments* {#tbl-stop-method-arguments}

| **Argument** | **Description** |
| --- | --- |

#### EmergencyStop {#sec-generatorsettype-emergencystop type=GeneratorSetType method=EmergencyStop}

Command an immediate emergency stop.

**Signature**

```text
EmergencyStop ();
```

*Table - EmergencyStop Method Arguments* {#tbl-emergencystop-method-arguments}

| **Argument** | **Description** |
| --- | --- |

#### ResetFaults {#sec-generatorsettype-resetfaults type=GeneratorSetType method=ResetFaults}

Reset latched faults / lockout.

**Signature**

```text
ResetFaults ();
```

*Table - ResetFaults Method Arguments* {#tbl-resetfaults-method-arguments}

| **Argument** | **Description** |
| --- | --- |

#### SetOperatingMode {#sec-generatorsettype-setoperatingmode type=GeneratorSetType method=SetOperatingMode}

Set the control-panel selector mode.

**Signature**

```text
SetOperatingMode (
  [in]  1:GeneratorOperatingModeEnum Mode);
```

*Table - SetOperatingMode Method Arguments* {#tbl-setoperatingmode-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Mode | The requested operating mode. |

#### StartTest {#sec-generatorsettype-starttest type=GeneratorSetType method=StartTest}

Start a test run for a given duration.

**Signature**

```text
StartTest (
  [in]  0:UInt32  DurationMinutes,
  [in]  0:Boolean WithLoad);
```

*Table - StartTest Method Arguments* {#tbl-starttest-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| DurationMinutes | Test duration in minutes. |
| WithLoad | TRUE to run the test with load. |

### [EngineType](#sec-enginetype-and-the-can-bus-sae-j1939-interface) and the CAN bus / SAE J1939 interface {#sec-enginetype-and-the-can-bus-sae-j1939-interface}

`EngineType` exposes the classic engine telemetry — `Speed` (SPN 190), `OilPressure` (SPN 100), `CoolantTemperature` (SPN 110), `FuelRate` (SPN 183), `EngineHours` (SPN 247), boost, exhaust and intake temperatures, percent load/torque, etc. The referenced SPN for each variable is recorded in the variable description so that a gateway can map J1939 signals directly onto the model.

The engine's `CanInterface` (a `J1939DiagnosticInterfaceType`) models the network itself: `ProtocolName` ("SAE J1939"), `NetworkName`, `SourceAddress`, `Baudrate` (250 000 or 500 000 bit/s), `BusState`, the four J1939 DM1 lamp statuses (`AmberWarningLamp`, `RedStopLamp`, `MalfunctionIndicatorLamp`, `ProtectLamp`, each a `J1939LampStatusEnum` conveying Off / On / SlowFlash / FastFlash), and the `ActiveDiagnosticTroubleCodeDetails` (DM1) and `PreviouslyActiveDiagnosticTroubleCodeDetails` (DM2) arrays of `DiagnosticTroubleCodeDataType`. Each DTC carries `Spn`, `Fmi`, `OccurrenceCount`, `SourceAddress`/`SourceName` (so faults from multiple ECUs on the bus remain distinguishable) and an optional `ProtectionAction`. The method `ClearPreviouslyActiveDtcs` corresponds to J1939 DM3/DM11.

The legacy `ActiveDiagnosticTroubleCodes` and `PreviouslyActiveDiagnosticTroubleCodes` arrays of `DiagnosticTroubleCodeType` remain for compatibility. A new Server **should** expose the `*Details` members. Where both forms are present, they **shall** describe the same DTCs in the same order. The legacy `Severity` field keeps its published semantics and **shall not** be derived mechanically from `ProtectionAction`; a Server populates it only when its legacy classification is true for the reported DTC.

*Table - EngineType Definition* {#tbl-enginetype-definition defines=EngineType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:EngineType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:ComponentType defined in OPC 10000-100 |  |  |  |  |  |
| 0:HasComponent | Variable | 1:Speed | 0:Double | 0:AnalogUnitType | M |
| 0:HasComponent | Variable | 1:PercentLoad | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:PercentTorque | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:OilPressure | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:OilTemperature | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:CoolantTemperature | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:CoolantPressure | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:FuelRate | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:FuelTemperature | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:IntakeManifoldPressure | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:IntakeManifoldTemperature | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:ExhaustGasTemperature | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:BarometricPressure | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:EngineHours | 0:Double | 0:AnalogUnitType | M |
| 0:HasComponent | Variable | 1:NumberOfStarts | 0:UInt32 | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:Aspiration | 1:AspirationEnum | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:Displacement | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:CylinderCount | 0:UInt16 | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:RatedSpeed | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Object | 1:CanInterface |  | 1:J1939DiagnosticInterfaceType | O |
| 0:HasComponent | Object | 1:Aftertreatment |  | 1:ExhaustAftertreatmentType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-Components |  |  |  |  |  |

### [AlternatorType](#sec-alternatortype) and [AlternatorPhaseType](#sec-alternatorphasetype) {#sec-alternatortype-and-alternatorphasetype}

`AlternatorType` provides aggregate values — `Frequency`, `TotalRealPower`/`TotalReactivePower`/`TotalApparentPower`, average voltages and current, `AveragePowerFactor`, `TotalRealEnergy`, `LoadPercent`, winding and bearing temperatures, `Connection`, `ExcitationType`, `NumberOfPoles` — and three phase objects (`L1`, `L2`, `L3`, each an `AlternatorPhaseType`) carrying per‑phase voltage, current, power and power factor. Single‑phase sets populate only `L1` (mandatory); three‑phase sets populate all three.

### Support subsystems {#sec-support-subsystems}

[`FuelSystemType`](#sec-fuelsystemtype) (fuel type/level/rate/pressure, gas supply pressure, runtime remaining, DEF for aftertreatment, water‑in‑fuel), [`CoolingSystemType`](#sec-coolingsystemtype) (coolant temperature/level/pressure, cooling method, radiator fan and jacket‑water heater), [`LubricationSystemType`](#sec-lubricationsystemtype) (oil pressure/temperature/level, filter Δp) and [`StartingSystemType`](#sec-startingsystemtype) (battery voltage/charging current, charger status, start attempts) model the balance‑of‑plant. All are optional so the type fits both a bare air‑cooled residential set and a fully instrumented industrial set.

### [GeneratorControllerType](#sec-generatorcontrollertype) {#sec-generatorcontrollertype}

Represents the control panel. Carries controller identity (`ControllerFamily`, `FirmwareVersion`, `ApplicationSoftwareVersion`, `ConfigurationVersion`), operating annunciation (`InAutoMode`, `NotInAuto`), remote enablement (`RemoteStartEnabled`, `RemoteControlEnabled`) and remote‑monitoring status (`CloudConnected`, `ModbusEnabled`, `SignalStrength`).

*Table - GeneratorControllerType Definition* {#tbl-generatorcontrollertype-definition defines=GeneratorControllerType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:GeneratorControllerType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:ComponentType defined in OPC 10000-100 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:ControllerFamily | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:FirmwareVersion | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:ApplicationSoftwareVersion | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:ConfigurationVersion | 0:String | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:InAutoMode | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:NotInAuto | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:RemoteStartEnabled | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:RemoteControlEnabled | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:CloudConnected | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:ModbusEnabled | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:SignalStrength | 0:Double | 0:AnalogUnitType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-Components |  |  |  |  |  |

### [GeneratorRatingType](#sec-generatorratingtype-and-ratings) and ratings {#sec-generatorratingtype-and-ratings}

Because a set is usually certified for several ISO 8528 duties, ratings are modelled as a placeholder list. The `Ratings` folder on `GeneratorSetType` contains zero or more `GeneratorRatingType` objects, each with an `ApplicationRating` (ESP/PRP/COP/LTP/DCC) and the rated power, voltage, current, frequency, speed, power factor, phase count and reference ambient/altitude.

*Table - GeneratorRatingType Definition* {#tbl-generatorratingtype-definition defines=GeneratorRatingType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:GeneratorRatingType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasComponent | Variable | 1:ApplicationRating | 1:GeneratorApplicationRatingEnum | 0:BaseDataVariableType | M |
| 0:HasComponent | Variable | 1:RatedRealPower | 0:Double | 0:AnalogUnitType | M |
| 0:HasComponent | Variable | 1:RatedApparentPower | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:RatedPowerFactor | 0:Double | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:RatedVoltage | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:RatedCurrent | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:RatedFrequency | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:RatedSpeed | 0:Double | 0:AnalogUnitType | O |
| 0:HasProperty | Variable | 1:PhaseCount | 0:Byte | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:Connection | 1:ElectricalConnectionEnum | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:AmbientTemperature | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:Altitude | 0:Double | 0:AnalogUnitType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-Rating |  |  |  |  |  |

### [GeneratorStateMachineType](#sec-generatorstatemachinetype) {#sec-generatorstatemachinetype}

`OperatingState` is a finite state machine with twelve states and the transitions shown below. It is the detailed, generator‑specific complement to the generic Machinery `MachineryItemState`.

```{figure}
id: fig-gen-statemachine
caption: The generator operating state machine
source: figures/Generators-Fig2-StateMachine.png
```

*Table - GeneratorStateMachineType Definition* {#tbl-generatorstatemachinetype-definition defines=GeneratorStateMachineType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:GeneratorStateMachineType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:FiniteStateMachineType defined in OPC 10000-16 |  |  |  |  |  |
| 0:HasComponent | Object | 1:Off |  | 0:InitialStateType |  |
| 0:HasComponent | Object | 1:Ready |  | 0:StateType |  |
| 0:HasComponent | Object | 1:Starting |  | 0:StateType |  |
| 0:HasComponent | Object | 1:Warmup |  | 0:StateType |  |
| 0:HasComponent | Object | 1:Running |  | 0:StateType |  |
| 0:HasComponent | Object | 1:Loaded |  | 0:StateType |  |
| 0:HasComponent | Object | 1:Synchronizing |  | 0:StateType |  |
| 0:HasComponent | Object | 1:Paralleled |  | 0:StateType |  |
| 0:HasComponent | Object | 1:Cooldown |  | 0:StateType |  |
| 0:HasComponent | Object | 1:Stopping |  | 0:StateType |  |
| 0:HasComponent | Object | 1:Fault |  | 0:StateType |  |
| 0:HasComponent | Object | 1:EmergencyStopped |  | 0:StateType |  |
| 0:HasComponent | Object | 1:OffToReady |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:ReadyToStarting |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:ReadyToOff |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:StartingToWarmup |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:StartingToFault |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:WarmupToRunning |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:RunningToLoaded |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:RunningToSynchronizing |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:SynchronizingToParalleled |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:SynchronizingToRunning |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:ParalleledToLoaded |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:LoadedToCooldown |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:RunningToCooldown |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:CooldownToStopping |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:StoppingToOff |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:RunningToFault |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:LoadedToFault |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:ParalleledToFault |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:FaultToOff |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:RunningToEmergencyStopped |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:LoadedToEmergencyStopped |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:ParalleledToEmergencyStopped |  | 0:TransitionType |  |
| 0:HasComponent | Object | 1:EmergencyStoppedToOff |  | 0:TransitionType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-StateMachine |  |  |  |  |  |

### Operating modes {#sec-operating-modes}

`OperatingMode` (a [`GeneratorOperatingModeEnum`](#sec-generatoroperatingmodeenum) value) is the authoritative control-panel selector: `Off`, `Manual`, `Auto`, `Test`, `Exercise`, `RemoteStart`, `Maintenance`, `Lockout`. `SetOperatingMode` changes this value; a Server **shall not** accept an independent command that changes the optional Machinery `MachineryOperationMode` state machine.

Where `MachineryOperationMode` is present under `MachineryBuildingBlocks`, it is a derived interoperability projection. Its `CurrentState` **shall** equal the row below for the authoritative `OperatingMode` value:

| `OperatingMode` | `MachineryOperationMode.CurrentState` |
|---|---|
| `Maintenance` | `Maintenance` |
| `Test` or `Exercise` | `Setup` |
| `Manual`, `Auto` or `RemoteStart` | `Processing` |
| `Off` or `Lockout` | `None` |

The projection does not create a second source of truth. `OperatingState` and `MachineryItemState` separately report whether the selected mode is executing, idle, unavailable or faulted. If the two operation-mode representations disagree, `OperatingMode` decides and the `MachineryOperationMode` state is incorrect.

### Protections and alarms {#sec-protections-and-alarms}

`GeneratorProtectionAlarmType` (subtype of `OffNormalAlarmType`) reports any protection or shutdown condition. Its `ProtectionFunction` property (a [`GeneratorProtectionFunctionEnum`](#sec-generatorprotectionfunctionenum) with 64 values — low oil pressure, high coolant temperature, overspeed, overcrank, over/under voltage and frequency, overload, reverse power, ground fault, emergency stop, aftertreatment faults, ATS/breaker failures, …) identifies the condition. `ProtectionAction` classifies the automatic response requested by that function: no automatic action, warning, derate, shutdown, electrical trip, lockout or emergency stop.

The inherited Part 9 `Severity` field is the sole authority for event urgency and **shall** be populated independently of `ProtectionAction`. `IsShutdown` reports the actual engine outcome and **shall not** be inferred from `ProtectionAction`: for example, an alarm may request `Shutdown` while `IsShutdown` remains false until shutdown completes or if the action fails. `Spn`, `Fmi` and `SubsystemName` add origin context.

The legacy `GeneratorAlarmSeverity` property remains for compatibility. A new Server **should** expose `ProtectionAction` instead. `GeneratorAlarmSeverity` keeps its published semantics and **shall not** be derived mechanically from `ProtectionAction`; for example, legacy `Shutdown` is valid only when the engine is shut down, not merely when shutdown was requested. Neither property changes the meaning or authority of inherited `Severity`.

Because the type is an `OffNormalAlarmType`, the *normal* state is "healthy / not tripped": on an instance, the inherited `NormalState` references the node representing the healthy value, `InputNode` references the supervised input (e.g. the shutdown latch or the measured variable), and `SourceNode` references the owning `GeneratorSetType` or subsystem so that clients can locate the origin. Analog limit conditions (e.g. over/under voltage) may additionally be surfaced with standard `ExclusiveLevelAlarmType` instances on the corresponding measured variables.

### Transfer switches and paralleling {#sec-transfer-switches-and-paralleling}

[`AutomaticTransferSwitchType`](#sec-automatictransferswitchtype) (a `DeviceType`) models an ATS: `Position`, `OperatingState`, `TransitionType`, two structured sources (`Source1`, `Source2`, each a [`TransferSwitchSourceType`](#sec-transferswitchsourcetype) carrying `Available`, `Acceptable`, `Voltage`, `Frequency` and `PhaseRotation`), `PreferredSource`, source connection flags, `TransferInhibited`/`TransferInhibitReason`, ratings, load metering, transfer timers and counters, and the `Transfer`/`Retransfer`/`InhibitTransfer` methods. [`ParallelingControllerType`](#sec-parallelingcontrollertype) models synchronising and load sharing across a common bus: `SystemState`, bus voltage/frequency/power, synchronising deltas (`SynchronizationAngle`, `SlipFrequency`, voltage/frequency difference, `SyncCheckPermissive`, `DeadBus`), load‑share and capacity values, breaker states, utility import/export, and the `ConnectToBus`/`DisconnectFromBus` methods.

### [GeneratorSystemType](#sec-generatorsystemtype) {#sec-generatorsystemtype}

Aggregates a paralleled plant: a mandatory `GeneratorSets` folder of `GeneratorSetType` instances, an optional `ParallelingController`, an optional `TransferSwitches` folder, and system totals (`NumberOfGeneratorSets`, `TotalSystemCapacity`, `TotalSystemLoad`, `RedundancyScheme`).

*Table - GeneratorSystemType Definition* {#tbl-generatorsystemtype-definition defines=GeneratorSystemType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:GeneratorSystemType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasComponent | Object | 1:GeneratorSets |  | 0:FolderType | M |
| 0:HasComponent | Object | 1:ParallelingController |  | 1:ParallelingControllerType | O |
| 0:HasComponent | Object | 1:TransferSwitches |  | 0:FolderType | O |
| 0:HasComponent | Variable | 1:NumberOfGeneratorSets | 0:UInt16 | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:TotalSystemCapacity | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:TotalSystemLoad | 0:Double | 0:AnalogUnitType | O |
| 0:HasProperty | Variable | 1:RedundancyScheme | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-System |  |  |  |  |  |

## DataTypes {#sec-datatypes}

Eighteen enumerations and two structures are defined; see [Annex A](#anx-a) for the full value lists. The enumerations are extensible (each provides an `Other`/`Unknown` member where appropriate) and cover fuel types, application/duty ratings, electrical connection, excitation, cooling method, aspiration, emissions standard, CAN bus state, J1939 lamp status, transfer-switch position/transition/state, generator protection action, the 64-value protection-function list, paralleling-system state and aftertreatment state. The [`DiagnosticTroubleCodeDataType`](#sec-diagnostictroublecodedatatype) structure carries a single SAE J1939 DTC (`Spn`, `Fmi`, `OccurrenceCount`, `ConversionMethod`, `Active`, `SourceAddress`, `SourceName`, optional `ProtectionAction`, `Description`). `DiagnosticTroubleCodeType` and `AlarmSeverityEnum` are retained only as compatibility types.

## Coverage of the industry {#sec-coverage-of-the-industry}

The model is vendor‑neutral. The following mapping shows how representative product tiers across the generator industry are expressed with the types defined here; products from any manufacturer map the same way.

| Product tier | Represented by |
|---|---|
| Residential / home standby (~10–60 kW, air‑ or liquid‑cooled, natural gas / LPG) | [`GeneratorSetType`](#sec-generatorsettype) with an air‑ or liquid‑cooled `CoolingSystem`, `FuelType` = NaturalGas/Propane, and a single‑phase alternator (`L1` only) |
| Commercial & industrial diesel (up to ~3.75 MW) | `GeneratorSetType` with a high‑power `EngineType`, three‑phase `AlternatorType`, `ExhaustAftertreatment` (Tier 4 / Stage V), and multiple `GeneratorRatingType` (Standby / Prime) |
| Natural‑gas / lean‑burn (~55 kW–2 MW, CHP / continuous) | `GeneratorSetType` with `FuelType` = NaturalGas/Biogas/LandfillGas, `FuelSystem.GasSupplyPressure`, and `ApplicationRating` = Continuous |
| Data‑center (multi‑MW, N+1 / 2N, medium‑voltage bus) | [`GeneratorSystemType`](#sec-generatorsystemtype) aggregating sets with `ApplicationRating` = DataCenterContinuous, a `ParallelingControllerType`, and a `RedundancyScheme` |
| Healthcare / life‑safety (NFPA 110 Level 1) | `GeneratorSetType` + `AutomaticTransferSwitchType`; readiness via `StartingSystem`, `FuelSystem.RuntimeRemaining` and `Controller.InAutoMode` |
| Rental / mobile / towable (Tier 4 Final) | `GeneratorSetType` with `ExhaustAftertreatment` (DEF / DPF / SCR) and `Application` = Rental |
| Control panels & cloud monitoring | `GeneratorControllerType` (`ControllerFamily`, firmware/config versions, `CloudConnected`, `ModbusEnabled`) |
| Transfer switches (open / closed / soft‑load, bypass‑isolation) | `AutomaticTransferSwitchType` (`TransitionType`, structured `Source1`/`Source2`) |
| Paralleling switchgear / master control | `ParallelingControllerType` + `GeneratorSystemType` |

## Profiles and conformance {#sec-profiles-and-conformance}

```{clause}
kind: profiles
```

A server implementing this specification should implement the [`GeneratorSetType`](#sec-generatorsettype) and its mandatory content. Support for individual subsystems (fuel, cooling, lubrication, starting, aftertreatment), for [`AutomaticTransferSwitchType`](#sec-automatictransferswitchtype), [`ParallelingControllerType`](#sec-parallelingcontrollertype) and [`GeneratorSystemType`](#sec-generatorsystemtype), and for the control methods is optional and should be advertised through appropriate profiles/facets. Instances of `GeneratorSetType` should be made discoverable by organising them under the Machinery `Machines` folder, as recommended by OPC 40001‑1.

Mandatory children inherited from the chosen base types are **not** re‑declared in this NodeSet, but conforming instances must still expose them. In particular: the DI `DeviceType` nameplate (`Manufacturer`, `Model`, `SerialNumber`, `HardwareRevision`, `SoftwareRevision`, `DeviceRevision`, `DeviceManual`, `RevisionCounter`); the `FiniteStateMachineType` `CurrentState` on `OperatingState`; the `AnalogUnitType` `EngineeringUnits` on every measured value (this specification pre‑populates it with a default unit); and the `OffNormalAlarmType` / `AcknowledgeableConditionType` condition state (`EnabledState`, `ActiveState`, `AckedState`, `NormalState`). Optional but recommended children — such as the `FiniteStateMachineType` `LastTransition` and the `AnalogUnitType` `EURange` / `InstrumentRange` — should be provided where the information is available.

Conformance is composed from independently implementable **conformance units (CUs)**, one per subsystem. Only `GEN-GeneratorSet` is mandatory; every other unit may be claimed on its own.

| Conformance unit | Requires |
|---|---|
| `GEN-GeneratorSet` | **Mandatory.** `GeneratorSetType` with its mandatory content, and the enumerations and structures the model is written in. |
| `GEN-Components` | The engine, alternator, alternator phase and support subsystems (fuel, cooling, lubrication, starting, aftertreatment). |
| `GEN-Identification` | The generator-set nameplate beyond the inherited DI nameplate. |
| `GEN-StateMachine` | `GeneratorStateMachineType`, its states and transitions, and the operating modes. |
| `GEN-Rating` | `GeneratorRatingType` and the rating set of a generator set. |
| `GEN-Alarms` | The protection and alarm conditions and their condition state. |
| `GEN-CANbus` | The CAN bus / SAE J1939 interface of the engine. |
| `GEN-TransferSwitch` | `AutomaticTransferSwitchType` and its transfer behaviour. |
| `GEN-Paralleling` | `ParallelingControllerType` and the paralleling and load-sharing behaviour. |
| `GEN-System` | `GeneratorSystemType`, the aggregate of several generator sets. |

**Profiles.** *Generator Set Server* = `GEN-GeneratorSet` + `GEN-Components` + `GEN-Identification` + `GEN-StateMachine` + `GEN-Rating`. *Generator Set Server with alarms* adds `GEN-Alarms` and `GEN-CANbus`. *Generator Plant Server* adds `GEN-TransferSwitch`, `GEN-Paralleling` and `GEN-System`.

## PubSub dataset bindings {#sec-pubsub-dataset-bindings}

The information model is transport‑neutral: it can be exposed over OPC UA client/server and, at scale, over **OPC UA PubSub** (OPC 10000‑14). This clause gives *non‑normative* recommendations for grouping the Variables of a generator set into **PublishedDataSets** (PDS) and **WriterGroups** so that a server can efficiently feed several classes of consumer. A server may publish any subset; the field paths below are BrowsePaths relative to a [`GeneratorSetType`](#sec-generatorsettype) (or [`GeneratorSystemType`](#sec-generatorsystemtype)) instance.

### General binding guidance {#sec-general-binding-guidance}

- A **PublishedDataSet** is a named list of published fields, each field bound to a Variable of the model (for example `Alternator/TotalRealPower`). Group fields by **rate of change** and **consumer** so that fast telemetry, slow nameplate/configuration, and event data travel in separate datasets and writer groups.
- Use one **WriterGroup** per publishing rate. Publish cyclic telemetry as **delta frames** with a periodic **key frame**; publish nameplate/configuration as low‑rate key frames or on change.
- Bind alarms and protection events to an **event DataSet** (the Part 14 event message mapping) rather than to a cyclic dataset.
- Expose `DataSetMetaData` including its `ConfigurationVersion` so subscribers can detect structural changes, and carry `SourceTimestamp` and `StatusCode` per field so analytics can reason about data quality and gaps.
- For multi‑set installations, a `GeneratorSystemType` writer publishes aggregated key indicators while each `GeneratorSetType` publishes its own detailed datasets.

### Scenario — Operational observability {#sec-scenario-operational-observability}

Real‑time monitoring, SCADA/HMI and remote operations. Low latency, small payloads, cyclic.

| PublishedDataSet | Suggested fields | Rate | Frame |
|---|---|---|---|
| `GenSet.Live` | `OperatingState/CurrentState`, `OperatingMode`, `Engine/Speed`, `Engine/CoolantTemperature`, `Engine/OilPressure`, `Alternator/Frequency`, `Alternator/TotalRealPower`, `Alternator/AverageLineToLineVoltage`, `Alternator/AverageCurrent`, `FuelSystem/FuelLevel`, `StartingSystem/BatteryVoltage` | 1 s | delta + 10 s key |
| `GenSet.Status` | `GeneratorBreakerClosed`, `AvailableToLoad`, `RunRequest`, `LoadInhibit`, `Controller/InAutoMode`, `DeviceHealth` | on change | key |

### Scenario — Analytics: predictive maintenance {#sec-scenario-analytics-predictive-maintenance}

Trending of wear‑ and condition‑related signals together with diagnostic codes and usage counters; historized. Moderate rate.

| PublishedDataSet | Suggested fields | Rate |
|---|---|---|
| `GenSet.Condition` | `Engine/OilPressure`, `Engine/OilTemperature`, `Engine/CoolantTemperature`, `Engine/ExhaustGasTemperature`, `Engine/IntakeManifoldPressure`, `LubricationSystem/OilFilterDifferentialPressure`, `Alternator/WindingTemperature1..3`, `Alternator/BearingTemperatureDriveEnd`, `Alternator/BearingTemperatureNonDriveEnd`, `FuelSystem/FuelPressure` | 1–10 s |
| `GenSet.Usage` | `Engine/EngineHours`, `Engine/NumberOfStarts`, `StartingSystem/StartAttempts`, `Alternator/TotalRealEnergy`, `FuelSystem/TotalFuelConsumed` | 1 min / on change |
| `GenSet.Diagnostics` | `Engine/CanInterface/ActiveDiagnosticTroubleCodes`, `Engine/CanInterface/PreviouslyActiveDiagnosticTroubleCodes`, `Engine/CanInterface/AmberWarningLamp`, `Engine/CanInterface/RedStopLamp` | on change |

Predictive models correlate the condition signals with usage counters and DTC history to forecast wear (bearings, injectors, cooling and lubrication systems) and to schedule service before failure.

### Scenario — Analytics: anomaly detection {#sec-scenario-analytics-anomaly-detection}

High‑resolution, correlated electrical and mechanical signals for baseline modelling and deviation/outlier detection (phase imbalance, load‑vs‑fuel drift, incipient faults).

| PublishedDataSet | Suggested fields | Rate |
|---|---|---|
| `GenSet.HiRes` | `Engine/Speed`, `Engine/PercentLoad`, `Engine/FuelRate`, `Alternator/Frequency`, `Alternator/TotalRealPower`, `Alternator/TotalReactivePower`, and per‑phase `Alternator/L1..L3/Current`, `.../LineToNeutralVoltage`, `.../PowerFactor` | 100 ms – 1 s |

### Scenario — Energy & load management and paralleling {#sec-scenario-energy-load-management-and-paralleling}

Load sharing, peak shaving, demand response and grid‑services coordination across a bus or fleet.

| PublishedDataSet | Suggested fields | Rate |
|---|---|---|
| `System.Load` | `ParallelingController/TotalBusRealPower`, `.../TotalBusReactivePower`, `.../BusFrequency`, `.../BusVoltage`, `.../LoadSharePercent`, `.../AvailableCapacity`, `.../SpinningReserve`, `.../UtilityImportPower`, `.../UtilityExportPower` | 200 ms – 1 s |
| `GenSet.Power` | `Alternator/TotalRealPower`, `Alternator/LoadPercent`, `Ratings/<Rating>/RatedRealPower` | 1 s |

### Scenario — Alarm & event distribution {#sec-scenario-alarm-event-distribution}

Protection and condition events for operators, CMMS/EAM systems and safety functions.

| Event DataSet | Source | Delivery |
|---|---|---|
| `GenSet.Events` | `GeneratorProtectionAlarmType` events (`ProtectionFunction`, `ProtectionAction`, `IsShutdown`, `Spn`, `Fmi`, `SubsystemName`) plus the standard `AcknowledgeableConditionType` fields, including the authoritative Part 9 `Severity`; `GeneratorAlarmSeverity` is a compatibility projection only | event‑driven, reliable, with keep‑alive |

### Scenario — Fleet monitoring & compliance {#sec-scenario-fleet-monitoring-compliance}

Multi‑site supervision, contractual reporting and regulatory / emergency‑power compliance (for example NFPA 110 test records and emissions reporting).

| PublishedDataSet | Suggested fields | Rate |
|---|---|---|
| `GenSet.Nameplate` | `Identification/Manufacturer`, `Identification/Model`, `Identification/SerialNumber`, `Identification/EngineModel`, `Identification/AlternatorModel`, `Identification/RatedRealPower`, `Identification/EmissionsStandard`, `Application`, `Controller/FirmwareVersion`, `Controller/ConfigurationVersion` | on change / daily key |
| `GenSet.Compliance` | `EmissionsStandard`, `Engine/Aftertreatment/AftertreatmentState`, `Engine/Aftertreatment/DefLevel`, `Engine/Aftertreatment/DpfSootLoad`, `Engine/EngineHours`, `FuelSystem/TotalFuelConsumed` (test runs are recorded via the `StartTest` method and protection/condition events) | periodic / event |
| `System.Fleet` | per set `OperatingState/CurrentState` and `Alternator/TotalRealPower`; system `TotalSystemLoad`, `TotalSystemCapacity`, `NumberOfGeneratorSets` | 1–10 s |

## Deliverables and reproducibility {#sec-deliverables-and-reproducibility}

| File | Content |
|---|---|
| [`Opc.Ua.Generators.NodeSet2.xml`](../../../model/companion-specs/Generators/Opc.Ua.Generators.NodeSet2.xml) | The normative machine‑readable information model (UANodeSet). |
| [`Opc.Ua.Generators.NodeIds.csv`](../../../model/companion-specs/Generators/Opc.Ua.Generators.NodeIds.csv) | Numeric NodeId assignments (`SymbolicName,NodeId,NodeClass`). |
| [`OPC-UA-Companion-Specification-for-Generators.md`](spec.md) | This document. |
| [`tools/build_model.py`](tools/build_model.py) | The generator that emits the NodeSet, the CSV and the [Annex A](#anx-a) tables from a single source of truth. |

The NodeSet has been validated to be structurally correct: XML well‑formedness, unique NodeIds, CSV↔NodeSet consistency, and resolution of **every** external base NodeId against the official OPC UA, DI and Machinery NodeId tables. Representative constructs (analog measurements, enumerations, a structure with encodings, methods with arguments, the finite state machine, the alarm subtype and the Machinery add‑ins) were additionally checked with the OPC Foundation modelling validator and reported **0 errors**.

---

## Information model reference {#anx-a annex=normative}

```{clause}
kind: annex-a
```

## Types the prose does not introduce {#sec-types-not-introduced}

The types below are declared by the model. Each clause was generated because no clause of this document named its type; fold them into the prose where they belong.

### GeneratorIdentificationType {#sec-generatoridentificationtype}

Identification and nameplate of a generator set. Extends the Machinery MachineIdentificationType with generator-specific nameplate data.

*Table - GeneratorIdentificationType Definition* {#tbl-generatoridentificationtype-definition defines=GeneratorIdentificationType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:GeneratorIdentificationType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 3:MachineIdentificationType defined in OPC 40001-1 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:SpecificationNumber | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:ProductFamily | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:EngineModel | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:EngineSerialNumber | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:AlternatorModel | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:AlternatorSerialNumber | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:ControllerModel | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:FuelType | 1:FuelTypeEnum | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:EmissionsStandard | 1:EmissionsStandardEnum | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:RatedRealPower | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:RatedApparentPower | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:RatedVoltage | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:RatedFrequency | 0:Double | 0:AnalogUnitType | O |
| 0:HasProperty | Variable | 1:SoundRatingAt7m | 0:Double | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-Identification |  |  |  |  |  |

### J1939DiagnosticInterfaceType {#sec-j1939diagnosticinterfacetype}

The engine CAN bus / SAE J1939 diagnostic interface. Surfaces the network connection parameters, J1939 lamp status and active/previously-active diagnostic trouble codes reported by the engine ECU.

*Table - J1939DiagnosticInterfaceType Definition* {#tbl-j1939diagnosticinterfacetype-definition defines=J1939DiagnosticInterfaceType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:J1939DiagnosticInterfaceType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:ProtocolName | 0:String | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:NetworkName | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:SourceAddress | 0:Byte | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Baudrate | 0:UInt32 | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:BusState | 1:CanBusStateEnum | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:AmberWarningLamp | 1:J1939LampStatusEnum | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:RedStopLamp | 1:J1939LampStatusEnum | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:MalfunctionIndicatorLamp | 1:J1939LampStatusEnum | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:ProtectLamp | 1:J1939LampStatusEnum | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:ActiveDiagnosticTroubleCodes | 1:DiagnosticTroubleCodeType[] | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:PreviouslyActiveDiagnosticTroubleCodes | 1:DiagnosticTroubleCodeType[] | 0:BaseDataVariableType | O |
| 0:HasComponent | Method | 1:ClearPreviouslyActiveDtcs |  |  | O |
| 0:HasComponent | Variable | 1:ActiveDiagnosticTroubleCodeDetails | 1:DiagnosticTroubleCodeDataType[] | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:PreviouslyActiveDiagnosticTroubleCodeDetails | 1:DiagnosticTroubleCodeDataType[] | 0:BaseDataVariableType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-CANbus |  |  |  |  |  |

#### ClearPreviouslyActiveDtcs {#sec-j1939diagnosticinterfacetype-clearpreviouslyactivedtcs type=J1939DiagnosticInterfaceType method=ClearPreviouslyActiveDtcs}

Clear previously active diagnostic trouble codes (J1939 DM3/DM11).

**Signature**

```text
ClearPreviouslyActiveDtcs ();
```

*Table - ClearPreviouslyActiveDtcs Method Arguments* {#tbl-clearpreviouslyactivedtcs-method-arguments}

| **Argument** | **Description** |
| --- | --- |

### ExhaustAftertreatmentType {#sec-exhaustaftertreatmenttype}

Exhaust aftertreatment subsystem (DPF/SCR/DEF) for Tier 4 / Stage V engines.

*Table - ExhaustAftertreatmentType Definition* {#tbl-exhaustaftertreatmenttype-definition defines=ExhaustAftertreatmentType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ExhaustAftertreatmentType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:ComponentType defined in OPC 10000-100 |  |  |  |  |  |
| 0:HasComponent | Variable | 1:AftertreatmentState | 1:AftertreatmentStateEnum | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:DefLevel | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:DefTemperature | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:DefQuality | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:DpfSootLoad | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:DpfAshLoad | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:ExhaustGasTemperature | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:RegenerationRequired | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:RegenerationInhibited | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Method | 1:InitiateRegeneration |  |  | O |
| 0:HasComponent | Method | 1:InhibitRegeneration |  |  | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-Components |  |  |  |  |  |

#### InitiateRegeneration {#sec-exhaustaftertreatmenttype-initiateregeneration type=ExhaustAftertreatmentType method=InitiateRegeneration}

Request a manual DPF regeneration.

**Signature**

```text
InitiateRegeneration ();
```

*Table - InitiateRegeneration Method Arguments* {#tbl-initiateregeneration-method-arguments}

| **Argument** | **Description** |
| --- | --- |

#### InhibitRegeneration {#sec-exhaustaftertreatmenttype-inhibitregeneration type=ExhaustAftertreatmentType method=InhibitRegeneration}

Enable or disable the inhibit of automatic regeneration.

**Signature**

```text
InhibitRegeneration (
  [in]  0:Boolean Inhibit);
```

*Table - InhibitRegeneration Method Arguments* {#tbl-inhibitregeneration-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Inhibit | TRUE to inhibit regeneration. |

### AlternatorPhaseType {#sec-alternatorphasetype}

Per-phase electrical measurements of the alternator output.

*Table - AlternatorPhaseType Definition* {#tbl-alternatorphasetype-definition defines=AlternatorPhaseType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:AlternatorPhaseType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasComponent | Variable | 1:LineToNeutralVoltage | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:LineToLineVoltage | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:Current | 0:Double | 0:AnalogUnitType | M |
| 0:HasComponent | Variable | 1:RealPower | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:ReactivePower | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:ApparentPower | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:PowerFactor | 0:Double | 0:BaseDataVariableType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-Components |  |  |  |  |  |

### AlternatorType {#sec-alternatortype}

The alternator (generator end) that converts mechanical power into AC electrical power. Exposes aggregate and per-phase electrical measurements.

*Table - AlternatorType Definition* {#tbl-alternatortype-definition defines=AlternatorType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:AlternatorType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:ComponentType defined in OPC 10000-100 |  |  |  |  |  |
| 0:HasComponent | Variable | 1:Frequency | 0:Double | 0:AnalogUnitType | M |
| 0:HasComponent | Variable | 1:AverageLineToLineVoltage | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:AverageLineToNeutralVoltage | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:AverageCurrent | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:TotalRealPower | 0:Double | 0:AnalogUnitType | M |
| 0:HasComponent | Variable | 1:TotalReactivePower | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:TotalApparentPower | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:AveragePowerFactor | 0:Double | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:TotalRealEnergy | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:LoadPercent | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:WindingTemperature1 | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:WindingTemperature2 | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:WindingTemperature3 | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:BearingTemperatureDriveEnd | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:BearingTemperatureNonDriveEnd | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:Connection | 1:ElectricalConnectionEnum | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:ExcitationType | 1:ExcitationTypeEnum | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:NumberOfPoles | 0:UInt16 | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:VoltageSetpoint | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:FieldCurrent | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Object | 1:L1 |  | 1:AlternatorPhaseType | M |
| 0:HasComponent | Object | 1:L2 |  | 1:AlternatorPhaseType | O |
| 0:HasComponent | Object | 1:L3 |  | 1:AlternatorPhaseType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-Components |  |  |  |  |  |

### FuelSystemType {#sec-fuelsystemtype}

The fuel storage and delivery subsystem of a generator set.

*Table - FuelSystemType Definition* {#tbl-fuelsystemtype-definition defines=FuelSystemType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:FuelSystemType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:ComponentType defined in OPC 10000-100 |  |  |  |  |  |
| 0:HasComponent | Variable | 1:FuelType | 1:FuelTypeEnum | 0:BaseDataVariableType | M |
| 0:HasComponent | Variable | 1:FuelLevel | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:FuelVolume | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:FuelConsumptionRate | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:FuelPressure | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:FuelTemperature | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:GasSupplyPressure | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:RuntimeRemaining | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:TotalFuelConsumed | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:WaterInFuel | 0:Boolean | 0:BaseDataVariableType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-Components |  |  |  |  |  |

### CoolingSystemType {#sec-coolingsystemtype}

The engine cooling subsystem of a generator set.

*Table - CoolingSystemType Definition* {#tbl-coolingsystemtype-definition defines=CoolingSystemType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:CoolingSystemType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:ComponentType defined in OPC 10000-100 |  |  |  |  |  |
| 0:HasComponent | Variable | 1:CoolantTemperature | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:CoolantLevel | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:CoolantPressure | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:CoolingMethod | 1:CoolingMethodEnum | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:AmbientTemperature | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:RadiatorFanRunning | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:JacketWaterHeaterActive | 0:Boolean | 0:BaseDataVariableType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-Components |  |  |  |  |  |

### LubricationSystemType {#sec-lubricationsystemtype}

The engine lubrication subsystem of a generator set.

*Table - LubricationSystemType Definition* {#tbl-lubricationsystemtype-definition defines=LubricationSystemType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:LubricationSystemType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:ComponentType defined in OPC 10000-100 |  |  |  |  |  |
| 0:HasComponent | Variable | 1:OilPressure | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:OilTemperature | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:OilLevel | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:OilFilterDifferentialPressure | 0:Double | 0:AnalogUnitType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-Components |  |  |  |  |  |

### StartingSystemType {#sec-startingsystemtype}

The starting/battery subsystem of a generator set.

*Table - StartingSystemType Definition* {#tbl-startingsystemtype-definition defines=StartingSystemType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:StartingSystemType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:ComponentType defined in OPC 10000-100 |  |  |  |  |  |
| 0:HasComponent | Variable | 1:BatteryVoltage | 0:Double | 0:AnalogUnitType | M |
| 0:HasComponent | Variable | 1:BatteryChargingCurrent | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:BatteryChargerActive | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:StartAttempts | 0:UInt32 | 0:BaseDataVariableType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-Components |  |  |  |  |  |

### GeneratorProtectionAlarmType {#sec-generatorprotectionalarmtype}

Alarm raised by a generator protection/shutdown function. Extends OffNormalAlarmType with the protection function, automatic protection action and J1939 origin. The inherited Severity field is the sole event urgency.

*Table - GeneratorProtectionAlarmType Definition* {#tbl-generatorprotectionalarmtype-definition defines=GeneratorProtectionAlarmType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:GeneratorProtectionAlarmType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:OffNormalAlarmType defined in OPC 10000-9 |  |  |  |  |  |
| 0:HasProperty | Variable | 1:ProtectionFunction | 1:GeneratorProtectionFunctionEnum | 0:PropertyType | M |
| 0:HasProperty | Variable | 1:GeneratorAlarmSeverity | 1:AlarmSeverityEnum | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:IsShutdown | 0:Boolean | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Spn | 0:UInt32 | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:Fmi | 0:Byte | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:SubsystemName | 0:String | 0:PropertyType | O |
| 0:HasProperty | Variable | 1:ProtectionAction | 1:GeneratorProtectionActionEnum | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-Alarms |  |  |  |  |  |

### TransferSwitchSourceType {#sec-transferswitchsourcetype}

One power source (normal/utility or emergency/generator) of an automatic transfer switch, with its availability and measurements.

*Table - TransferSwitchSourceType Definition* {#tbl-transferswitchsourcetype-definition defines=TransferSwitchSourceType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:TransferSwitchSourceType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:BaseObjectType defined in OPC 10000-5 |  |  |  |  |  |
| 0:HasComponent | Variable | 1:Available | 0:Boolean | 0:BaseDataVariableType | M |
| 0:HasComponent | Variable | 1:Acceptable | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:Voltage | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:Frequency | 0:Double | 0:AnalogUnitType | O |
| 0:HasProperty | Variable | 1:PhaseRotation | 0:String | 0:PropertyType | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-TransferSwitch |  |  |  |  |  |

### AutomaticTransferSwitchType {#sec-automatictransferswitchtype}

An automatic transfer switch (ATS) that transfers a load between a normal source (utility) and an emergency source (generator).

*Table - AutomaticTransferSwitchType Definition* {#tbl-automatictransferswitchtype-definition defines=AutomaticTransferSwitchType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:AutomaticTransferSwitchType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:DeviceType defined in OPC 10000-100 |  |  |  |  |  |
| 0:HasAddIn | Object | 2:Identification |  | 3:MachineIdentificationType | O |
| 0:HasComponent | Variable | 1:Position | 1:TransferSwitchPositionEnum | 0:BaseDataVariableType | M |
| 0:HasComponent | Variable | 1:OperatingState | 1:AtsOperatingStateEnum | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:TransitionType | 1:TransferTransitionTypeEnum | 0:BaseDataVariableType | O |
| 0:HasComponent | Object | 1:Source1 |  | 1:TransferSwitchSourceType | M |
| 0:HasComponent | Object | 1:Source2 |  | 1:TransferSwitchSourceType | M |
| 0:HasProperty | Variable | 1:PreferredSource | 0:Byte | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:Source1Connected | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:Source2Connected | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:TransferInhibited | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasProperty | Variable | 1:TransferInhibitReason | 0:String | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:RatedCurrent | 0:Double | 0:AnalogUnitType | O |
| 0:HasProperty | Variable | 1:PoleCount | 0:Byte | 0:PropertyType | O |
| 0:HasComponent | Variable | 1:ServiceEntranceRated | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:LoadCurrent | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:TransferCount | 0:UInt32 | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:LastTransferTime | 0:DateTime | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:EngineStartDelay | 0:Duration | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:TransferToEmergencyDelay | 0:Duration | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:RetransferToNormalDelay | 0:Duration | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:CooldownDelay | 0:Duration | 0:BaseDataVariableType | O |
| 0:HasComponent | Method | 1:Transfer |  |  | O |
| 0:HasComponent | Method | 1:Retransfer |  |  | O |
| 0:HasComponent | Method | 1:InhibitTransfer |  |  | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-TransferSwitch |  |  |  |  |  |

#### Transfer {#sec-automatictransferswitchtype-transfer type=AutomaticTransferSwitchType method=Transfer}

Command a transfer to the emergency source.

**Signature**

```text
Transfer ();
```

*Table - Transfer Method Arguments* {#tbl-transfer-method-arguments}

| **Argument** | **Description** |
| --- | --- |

#### Retransfer {#sec-automatictransferswitchtype-retransfer type=AutomaticTransferSwitchType method=Retransfer}

Command a retransfer to the normal source.

**Signature**

```text
Retransfer ();
```

*Table - Retransfer Method Arguments* {#tbl-retransfer-method-arguments}

| **Argument** | **Description** |
| --- | --- |

#### InhibitTransfer {#sec-automatictransferswitchtype-inhibittransfer type=AutomaticTransferSwitchType method=InhibitTransfer}

Enable or disable the transfer inhibit.

**Signature**

```text
InhibitTransfer (
  [in]  0:Boolean Inhibit);
```

*Table - InhibitTransfer Method Arguments* {#tbl-inhibittransfer-method-arguments}

| **Argument** | **Description** |
| --- | --- |
| Inhibit | TRUE to inhibit transfer. |

### ParallelingControllerType {#sec-parallelingcontrollertype}

A paralleling / switchgear controller that synchronizes and shares load among generator sets on a common bus, and optionally parallels with the utility.

*Table - ParallelingControllerType Definition* {#tbl-parallelingcontrollertype-definition defines=ParallelingControllerType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ParallelingControllerType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 2:ComponentType defined in OPC 10000-100 |  |  |  |  |  |
| 0:HasComponent | Variable | 1:SystemState | 1:ParallelingSystemStateEnum | 0:BaseDataVariableType | M |
| 0:HasComponent | Variable | 1:BusVoltage | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:BusFrequency | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:TotalBusRealPower | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:TotalBusReactivePower | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:SynchronizationAngle | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:SlipFrequency | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:VoltageDifference | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:FrequencyDifference | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:SyncCheckPermissive | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:DeadBus | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:LoadSharePercent | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:AvailableCapacity | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:SpinningReserve | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:GeneratorBreakerClosed | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:UtilityBreakerClosed | 0:Boolean | 0:BaseDataVariableType | O |
| 0:HasComponent | Variable | 1:UtilityImportPower | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Variable | 1:UtilityExportPower | 0:Double | 0:AnalogUnitType | O |
| 0:HasComponent | Method | 1:ConnectToBus |  |  | O |
| 0:HasComponent | Method | 1:DisconnectFromBus |  |  | O |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-Paralleling |  |  |  |  |  |

#### ConnectToBus {#sec-parallelingcontrollertype-connecttobus type=ParallelingControllerType method=ConnectToBus}

Synchronize and close onto the common bus.

**Signature**

```text
ConnectToBus ();
```

*Table - ConnectToBus Method Arguments* {#tbl-connecttobus-method-arguments}

| **Argument** | **Description** |
| --- | --- |

#### DisconnectFromBus {#sec-parallelingcontrollertype-disconnectfrombus type=ParallelingControllerType method=DisconnectFromBus}

Soft-unload and open from the common bus.

**Signature**

```text
DisconnectFromBus ();
```

*Table - DisconnectFromBus Method Arguments* {#tbl-disconnectfrombus-method-arguments}

| **Argument** | **Description** |
| --- | --- |

### GeneratorOperatingModeEnum {#sec-generatoroperatingmodeenum}

Selector mode of the generator set control panel.

*Table - GeneratorOperatingModeEnum Definition* {#tbl-generatoroperatingmodeenum-definition defines=GeneratorOperatingModeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:GeneratorOperatingModeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[8] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### FuelTypeEnum {#sec-fueltypeenum}

Primary fuel of the generator set.

*Table - FuelTypeEnum Definition* {#tbl-fueltypeenum-definition defines=FuelTypeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:FuelTypeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[16] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### GeneratorApplicationRatingEnum {#sec-generatorapplicationratingenum}

Application/duty rating per ISO 8528 plus the data-center-continuous rating.

*Table - GeneratorApplicationRatingEnum Definition* {#tbl-generatorapplicationratingenum-definition defines=GeneratorApplicationRatingEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:GeneratorApplicationRatingEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[5] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### ElectricalConnectionEnum {#sec-electricalconnectionenum}

Winding/connection configuration of the alternator output.

*Table - ElectricalConnectionEnum Definition* {#tbl-electricalconnectionenum-definition defines=ElectricalConnectionEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ElectricalConnectionEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[9] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### ExcitationTypeEnum {#sec-excitationtypeenum}

Excitation method of the alternator.

*Table - ExcitationTypeEnum Definition* {#tbl-excitationtypeenum-definition defines=ExcitationTypeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ExcitationTypeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[6] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### CoolingMethodEnum {#sec-coolingmethodenum}

Primary cooling method of the engine.

*Table - CoolingMethodEnum Definition* {#tbl-coolingmethodenum-definition defines=CoolingMethodEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:CoolingMethodEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[2] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### AspirationEnum {#sec-aspirationenum}

Air induction method of the engine.

*Table - AspirationEnum Definition* {#tbl-aspirationenum-definition defines=AspirationEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:AspirationEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[3] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### EmissionsStandardEnum {#sec-emissionsstandardenum}

Emissions certification standard of the engine.

*Table - EmissionsStandardEnum Definition* {#tbl-emissionsstandardenum-definition defines=EmissionsStandardEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:EmissionsStandardEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[10] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### CanBusStateEnum {#sec-canbusstateenum}

State of the engine CAN bus / SAE J1939 network interface.

*Table - CanBusStateEnum Definition* {#tbl-canbusstateenum-definition defines=CanBusStateEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:CanBusStateEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[5] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### TransferSwitchPositionEnum {#sec-transferswitchpositionenum}

Contact position of an automatic transfer switch.

*Table - TransferSwitchPositionEnum Definition* {#tbl-transferswitchpositionenum-definition defines=TransferSwitchPositionEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:TransferSwitchPositionEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[8] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### TransferTransitionTypeEnum {#sec-transfertransitiontypeenum}

Transition method of an automatic transfer switch.

*Table - TransferTransitionTypeEnum Definition* {#tbl-transfertransitiontypeenum-definition defines=TransferTransitionTypeEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:TransferTransitionTypeEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[5] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### AtsOperatingStateEnum {#sec-atsoperatingstateenum}

Operating state of an automatic transfer switch.

*Table - AtsOperatingStateEnum Definition* {#tbl-atsoperatingstateenum-definition defines=AtsOperatingStateEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:AtsOperatingStateEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[13] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### AlarmSeverityEnum {#sec-alarmseverityenum}

Severity class of a generator protection event.

*Table - AlarmSeverityEnum Definition* {#tbl-alarmseverityenum-definition defines=AlarmSeverityEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:AlarmSeverityEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[7] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### GeneratorProtectionFunctionEnum {#sec-generatorprotectionfunctionenum}

Protection / fault function that raised a generator alarm.

*Table - GeneratorProtectionFunctionEnum Definition* {#tbl-generatorprotectionfunctionenum-definition defines=GeneratorProtectionFunctionEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:GeneratorProtectionFunctionEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[64] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### ParallelingSystemStateEnum {#sec-parallelingsystemstateenum}

Operating state of a paralleling / switchgear system.

*Table - ParallelingSystemStateEnum Definition* {#tbl-parallelingsystemstateenum-definition defines=ParallelingSystemStateEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:ParallelingSystemStateEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[17] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### AftertreatmentStateEnum {#sec-aftertreatmentstateenum}

State of the exhaust aftertreatment system.

*Table - AftertreatmentStateEnum Definition* {#tbl-aftertreatmentstateenum-definition defines=AftertreatmentStateEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:AftertreatmentStateEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[8] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### J1939LampStatusEnum {#sec-j1939lampstatusenum}

SAE J1939 DM1 diagnostic lamp status (lamp state plus flash rate).

*Table - J1939LampStatusEnum Definition* {#tbl-j1939lampstatusenum-definition defines=J1939LampStatusEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:J1939LampStatusEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[5] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### DiagnosticTroubleCodeType {#sec-diagnostictroublecodetype}

A SAE J1939 diagnostic trouble code (DTC) reported by an engine ECU.

*Table - DiagnosticTroubleCodeType Definition* {#tbl-diagnostictroublecodetype-definition defines=DiagnosticTroubleCodeType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:DiagnosticTroubleCodeType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### GeneratorProtectionActionEnum {#sec-generatorprotectionactionenum}

Automatic response requested by a generator protection function. This is independent of the standard Part 9 event Severity.

*Table - GeneratorProtectionActionEnum Definition* {#tbl-generatorprotectionactionenum-definition defines=GeneratorProtectionActionEnum}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:GeneratorProtectionActionEnum |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Enumeration defined in OPC 10000-3 |  |  |  |  |  |
| 0:HasProperty | Variable | 0:EnumStrings | 0:LocalizedText[7] | 0:PropertyType |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |

### DiagnosticTroubleCodeDataType {#sec-diagnostictroublecodedatatype}

A SAE J1939 diagnostic trouble code (DTC) reported by an engine ECU.

*Table - DiagnosticTroubleCodeDataType Definition* {#tbl-diagnostictroublecodedatatype-definition defines=DiagnosticTroubleCodeDataType}

| **Attribute** | **Value** |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| BrowseName | 1:DiagnosticTroubleCodeDataType |  |  |  |  |
| IsAbstract | False |  |  |  |  |

| **References** | **Node Class** | **BrowseName** | **DataType** | **TypeDefinition** | **Other** |
| --- | --- | --- | --- | --- | --- |
| Subtype of the 0:Structure defined in OPC 10000-3 |  |  |  |  |  |

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-GeneratorSet |  |  |  |  |  |
