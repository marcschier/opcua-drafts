## Scope {#sec-scope}

This specification defines the OPC UA ObjectTypes, VariableTypes, DataTypes, ReferenceTypes and their instances required to represent a *generator set* as an automation asset and, at the same time, as a machine that is built around a prime-mover engine exposing a CAN bus interface.

The model covers:

- The generator set as a whole: nameplate and identification, ratings, operating state and mode, health, and control methods.
- The prime-mover engine, its telemetry, and its diagnostic trouble codes.
- The alternator, including per-phase and aggregate electrical measurements.
- The supporting subsystems: fuel, cooling, lubrication, starting and battery, and exhaust aftertreatment.
- The controller and its remote-monitoring status.
- The protection and alarm functions: warnings, shutdowns, electrical trips and lockouts.
- Automatic transfer switches and paralleling switchgear for multi-set power systems.

The model reuses the types defined in OPC 10000-100 and OPC 40001-1 so that generator sets appear as first-class members of the existing OPC UA machine and asset ecosystem.

```{clause}
kind: terms
```

## General description {#sec-general-description}

### What is a generator set? {#sec-what-is-a-generator-set}

A generator set is simultaneously two things: an asset with a nameplate, health and a life cycle; and a machine whose core is an internal-combustion engine coupled to an alternator. Sizes span four orders of magnitude of power. A small residential unit may produce about 13 kW on natural gas; a large industrial set built on a 95 l V16 high-speed diesel engine can deliver 3.0 MW to 3.75 MW, is the size of a small house, and consumes on the order of 500 l/h to 800 l/h of diesel at full load. Between those extremes lie commercial standby, data-centre, healthcare, rental and marine products.

Whatever the size, every set exposes broadly the same information: identity, ratings, an operating state and mode, engine and alternator telemetry, fuel, cooling, lubrication and battery status, protections and alarms, and start and stop control. This specification captures that common information once, so that a single Client can monitor and, where permitted, control any conforming set.

### Relationship to other specifications {#sec-relationship-to-other-specifications}

This model is layered on established OPC UA building blocks rather than reinventing them.

`GeneratorSetType` derives from the `DeviceType` of OPC 10000-100, inheriting a complete nameplate and `DeviceHealth`. Each subsystem — engine, alternator, fuel system and the rest — derives from the `ComponentType` of that same document, the standard base for an identifiable component of a device.

Every set carries the building blocks of OPC 40001-1 so that it is discoverable and interoperable alongside other machines: an `Identification` add-in, which is a `GeneratorIdentificationType` specialising `MachineIdentificationType`, and a `MachineryBuildingBlocks` folder holding the generic `MachineryItemState` and `MachineryOperationMode` state machines.

Protection events are modelled by `GeneratorProtectionAlarmType`, a subtype of the `OffNormalAlarmType` of OPC 10000-9. The detailed run states of a set are modelled by `GeneratorStateMachineType`, a `FiniteStateMachineType` of OPC 10000-16.

```{clause}
kind: namespaces
```

Numeric NodeIds in the namespace of this document are allocated as follows: ObjectTypes 1001 to 1099, DataTypes 3001 to 3099 for enumerations and 3050 upward for structures, EnumStrings Properties at the DataType identifier plus 900, and all remaining instance declarations — members, method arguments, state-machine states and transitions — sequentially from 6001.

## Information model architecture {#sec-information-model-architecture}

### Composition of a generator set {#sec-composition-of-a-generator-set}

The composition of a generator set is shown in [](#fig-generator-set-composition).

```{figure}
id: fig-generator-set-composition
caption: Composition of a generator set
source: figures/generator-set-composition.pptx
freeform: true
```

A multi-set installation — a data centre, a hospital, a campus — is represented by `GeneratorSystemType`, which aggregates one or more `GeneratorSetType` instances, an optional `ParallelingControllerType` and one or more `AutomaticTransferSwitchType` instances.

### Design rationale {#sec-design-rationale}

**Asset and machine, not either or.** Deriving from `DeviceType` gives the set an asset identity and health; adding the building blocks of OPC 40001-1 makes it discoverable as a machine. The `Identification` add-in intentionally mirrors a few nameplate fields already present on `DeviceType`: the add-in is the cross-vendor location and the inherited `DeviceType` fields are the location native to OPC 10000-100. A Server **may** populate either or both, but where both are present the equivalent fields — `Manufacturer`, `Model`, `SerialNumber` and `ProductInstanceUri` — **shall** carry the same value.

**Composition over deep inheritance.** Subsystems are separate `ComponentType` subtypes referenced by `HasComponent`, so a set can be assembled from exactly the components it has: an air-cooled residential unit omits the paralleling controller, and a diesel meeting the strictest emissions standards adds an `ExhaustAftertreatment`. OPC 11030 recommends this.

**Physical quantities carry machine-readable units.** Every measured value is typed `AnalogUnitType` and carries an `EngineeringUnits` Property whose value is a standard unit, so a Client can discover the unit from the type model alone. A Server **may** override this default at instance level to reflect the unit it actually reports; the value range is left to the instance.

**The CAN bus interface of the engine is explicit.** Because a generator set is in part an engine with a CAN bus interface, the engine exposes a dedicated `J1939DiagnosticInterfaceType` add-in carrying the network parameters, the lamp status and the arrays of active and previously active diagnostic trouble codes.

## ObjectTypes {#sec-objecttypes}

```{include objecttypes}
```

## DataTypes {#sec-datatypes}

```{include datatypes}
```

## Coverage of the industry {#sec-coverage-of-the-industry}

The model is vendor-neutral. [](#tbl-product-tiers-and-the-types-that-represent-them) shows how representative product tiers across the generator industry are expressed with the types defined here; products from any manufacturer map the same way.

*Table - Product tiers and the types that represent them* {#tbl-product-tiers-and-the-types-that-represent-them}

| **Product tier** | **Represented by** |
| --- | --- |
| Residential and home standby, about 10 kW to 60 kW, air- or liquid-cooled, natural gas or LPG | `GeneratorSetType` with an air- or liquid-cooled `CoolingSystem`, `FuelType` of NaturalGas or Propane, and a single-phase alternator populating `L1` only |
| Commercial and industrial diesel, up to about 3.75 MW | `GeneratorSetType` with a high-power `EngineType`, a three-phase `AlternatorType`, an `ExhaustAftertreatment`, and several `GeneratorRatingType` instances |
| Natural gas and lean-burn, about 55 kW to 2 MW, continuous or combined heat and power | `GeneratorSetType` with `FuelType` of NaturalGas, Biogas or LandfillGas, a `FuelSystem` reporting `GasSupplyPressure`, and an `ApplicationRating` of Continuous |
| Data centre, several megawatts, redundant, medium-voltage bus | `GeneratorSystemType` aggregating sets with an `ApplicationRating` of DataCenterContinuous, a `ParallelingControllerType`, and a `RedundancyScheme` |
| Healthcare and life safety | `GeneratorSetType` with an `AutomaticTransferSwitchType`; readiness through `StartingSystem`, `FuelSystem.RuntimeRemaining` and `Controller.InAutoMode` |
| Rental, mobile and towable | `GeneratorSetType` with an `ExhaustAftertreatment` and an `Application` of Rental |
| Control panels and cloud monitoring | `GeneratorControllerType` with `ControllerFamily`, the firmware and configuration versions, `CloudConnected` and `ModbusEnabled` |
| Transfer switches, open, closed, soft-load and bypass-isolation | `AutomaticTransferSwitchType` with `TransitionType` and the structured `Source1` and `Source2` |
| Paralleling switchgear and master control | `ParallelingControllerType` with `GeneratorSystemType` |

## Profiles and Conformance Units {#sec-profiles-and-conformance-units}

Mandatory children inherited from the chosen base types are not re-declared in this model, but conforming instances **shall** still expose them. In particular: the nameplate of `DeviceType` defined in OPC 10000-100; the `CurrentState` of the `FiniteStateMachineType` defined in OPC 10000-16, on `OperatingState`; the `EngineeringUnits` of the `AnalogUnitType` defined in OPC 10000-8, on every measured value, which this specification pre-populates with a default unit; and the condition state of the `OffNormalAlarmType` and `AcknowledgeableConditionType` defined in OPC 10000-9. Optional but recommended children, such as `LastTransition` and `EURange`, **should** be provided where the information is available.

Instances of `GeneratorSetType` **should** be made discoverable by organising them under the `Machines` folder that OPC 40001-1 defines.

```{clause}
kind: profiles
```

## PubSub dataset bindings {#sec-pubsub-dataset-bindings}

The information model is transport-neutral: it can be exposed over the Services defined in OPC 10000-4 and, at scale, over the PubSub mechanism defined in OPC 10000-14. This clause gives non-normative recommendations for grouping the Variables of a generator set into PublishedDataSets and WriterGroups so that a Server can efficiently feed several classes of consumer. A Server **may** publish any subset; the field paths below are BrowsePaths relative to a `GeneratorSetType` or `GeneratorSystemType` instance.

### General binding guidance {#sec-general-binding-guidance}

A PublishedDataSet is a named list of published fields, each field bound to a Variable of the model. Group fields by rate of change and by consumer, so that fast telemetry, slow nameplate and configuration data, and event data travel in separate datasets and writer groups.

Use one WriterGroup per publishing rate. Publish cyclic telemetry as delta frames with a periodic key frame; publish nameplate and configuration as low-rate key frames or on change.

Bind alarms and protection events to an event DataSet rather than to a cyclic dataset.

Expose the `DataSetMetaData` including its `ConfigurationVersion` so that Subscribers can detect structural changes, and carry a `SourceTimestamp` and a `StatusCode` per field so that analytics can reason about data quality and gaps.

For multi-set installations, a `GeneratorSystemType` writer publishes aggregated key indicators while each `GeneratorSetType` publishes its own detailed datasets.

### Operational observability {#sec-operational-observability}

Real-time monitoring, operator displays and remote operations. Low latency, small payloads, cyclic. [](#tbl-publisheddatasets-for-operational-observability) lists the datasets.

*Table - PublishedDataSets for operational observability* {#tbl-publisheddatasets-for-operational-observability}

| **PublishedDataSet** | **Suggested fields** | **Rate** | **Frame** |
| --- | --- | --- | --- |
| `GenSet.Live` | `OperatingState/CurrentState`, `OperatingMode`, `Engine/Speed`, `Engine/CoolantTemperature`, `Engine/OilPressure`, `Alternator/Frequency`, `Alternator/TotalRealPower`, `Alternator/AverageLineToLineVoltage`, `Alternator/AverageCurrent`, `FuelSystem/FuelLevel`, `StartingSystem/BatteryVoltage` | 1 s | delta, with a key frame every 10 s |
| `GenSet.Status` | `GeneratorBreakerClosed`, `AvailableToLoad`, `RunRequest`, `LoadInhibit`, `Controller/InAutoMode`, `DeviceHealth` | on change | key |

### Predictive maintenance {#sec-predictive-maintenance}

Trending of wear and condition signals together with diagnostic codes and usage counters, historized at a moderate rate. [](#tbl-publisheddatasets-for-predictive-maintenance) lists the datasets.

*Table - PublishedDataSets for predictive maintenance* {#tbl-publisheddatasets-for-predictive-maintenance}

| **PublishedDataSet** | **Suggested fields** | **Rate** |
| --- | --- | --- |
| `GenSet.Condition` | `Engine/OilPressure`, `Engine/OilTemperature`, `Engine/CoolantTemperature`, `Engine/ExhaustGasTemperature`, `Engine/IntakeManifoldPressure`, `LubricationSystem/OilFilterDifferentialPressure`, `Alternator/WindingTemperature1` to `3`, `Alternator/BearingTemperatureDriveEnd`, `Alternator/BearingTemperatureNonDriveEnd`, `FuelSystem/FuelPressure` | 1 s to 10 s |
| `GenSet.Usage` | `Engine/EngineHours`, `Engine/NumberOfStarts`, `StartingSystem/StartAttempts`, `Alternator/TotalRealEnergy`, `FuelSystem/TotalFuelConsumed` | 1 min, or on change |
| `GenSet.Diagnostics` | `Engine/CanInterface/ActiveDiagnosticTroubleCodes`, `Engine/CanInterface/PreviouslyActiveDiagnosticTroubleCodes`, `Engine/CanInterface/AmberWarningLamp`, `Engine/CanInterface/RedStopLamp` | on change |

Predictive models correlate the condition signals with the usage counters and the history of diagnostic trouble codes to forecast wear in bearings, injectors, and the cooling and lubrication systems, and to schedule service before failure.

### Anomaly detection {#sec-anomaly-detection}

High-resolution, correlated electrical and mechanical signals for baseline modelling and deviation detection: phase imbalance, drift between load and fuel consumption, and incipient faults. [](#tbl-publisheddataset-for-anomaly-detection) lists the dataset.

*Table - PublishedDataSet for anomaly detection* {#tbl-publisheddataset-for-anomaly-detection}

| **PublishedDataSet** | **Suggested fields** | **Rate** |
| --- | --- | --- |
| `GenSet.HiRes` | `Engine/Speed`, `Engine/PercentLoad`, `Engine/FuelRate`, `Alternator/Frequency`, `Alternator/TotalRealPower`, `Alternator/TotalReactivePower`, and for each of `L1`, `L2` and `L3` the `Current`, `LineToNeutralVoltage` and `PowerFactor` | 100 ms to 1 s |

### Energy and load management {#sec-energy-and-load-management}

Load sharing, peak shaving, demand response and grid-services coordination across a bus or a fleet. [](#tbl-publisheddatasets-for-energy-and-load-management) lists the datasets.

*Table - PublishedDataSets for energy and load management* {#tbl-publisheddatasets-for-energy-and-load-management}

| **PublishedDataSet** | **Suggested fields** | **Rate** |
| --- | --- | --- |
| `System.Load` | `ParallelingController/TotalBusRealPower`, `TotalBusReactivePower`, `BusFrequency`, `BusVoltage`, `LoadSharePercent`, `AvailableCapacity`, `SpinningReserve`, `UtilityImportPower` and `UtilityExportPower` | 200 ms to 1 s |
| `GenSet.Power` | `Alternator/TotalRealPower`, `Alternator/LoadPercent`, and the `RatedRealPower` of the applicable rating | 1 s |

### Alarm and event distribution {#sec-alarm-and-event-distribution}

Protection and condition events for operators, maintenance-management systems and safety functions. [](#tbl-event-dataset-for-alarm-and-event-distribution) lists the dataset.

*Table - Event DataSet for alarm and event distribution* {#tbl-event-dataset-for-alarm-and-event-distribution}

| **Event DataSet** | **Source** | **Delivery** |
| --- | --- | --- |
| `GenSet.Events` | `GeneratorProtectionAlarmType` events, carrying `ProtectionFunction`, `GeneratorAlarmSeverity`, `IsShutdown`, `Spn`, `Fmi` and `SubsystemName`, together with the standard `AcknowledgeableConditionType` fields | event-driven, reliable, with keep-alive |

### Fleet monitoring and compliance {#sec-fleet-monitoring-and-compliance}

Multi-site supervision, contractual reporting, and regulatory and emergency-power compliance. [](#tbl-publisheddatasets-for-fleet-monitoring-and-compliance) lists the datasets.

*Table - PublishedDataSets for fleet monitoring and compliance* {#tbl-publisheddatasets-for-fleet-monitoring-and-compliance}

| **PublishedDataSet** | **Suggested fields** | **Rate** |
| --- | --- | --- |
| `GenSet.Nameplate` | `Identification/Manufacturer`, `Identification/Model`, `Identification/SerialNumber`, `Identification/EngineModel`, `Identification/AlternatorModel`, `Identification/RatedRealPower`, `Identification/EmissionsStandard`, `Application`, `Controller/FirmwareVersion`, `Controller/ConfigurationVersion` | on change, with a daily key frame |
| `GenSet.Compliance` | `EmissionsStandard`, `Engine/Aftertreatment/AftertreatmentState`, `Engine/Aftertreatment/DefLevel`, `Engine/Aftertreatment/DpfSootLoad`, `Engine/EngineHours`, `FuelSystem/TotalFuelConsumed`. Test runs are recorded through the `StartTest` Method and the protection and condition events | periodic, and on event |
| `System.Fleet` | For each set the `OperatingState/CurrentState` and `Alternator/TotalRealPower`; for the system the `TotalSystemLoad`, `TotalSystemCapacity` and `NumberOfGeneratorSets` | 1 s to 10 s |

## Information model reference {#anx-a annex=normative}

```{clause}
kind: annex-a
capability-identifiers: true
```
