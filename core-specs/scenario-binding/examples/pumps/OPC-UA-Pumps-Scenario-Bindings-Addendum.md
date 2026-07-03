# OPC UA Pumps — Scenario Bindings Addendum

**Working draft — a worked example of the [Scenario Bindings](../../OPC-UA-Scenario-Bindings.md) base specification applied to OPC UA for Pumps and Vacuum Pumps.**

> **Status — illustrative example.** This addendum shows how the instances of the `PumpType` (http://opcfoundation.org/UA/Pumps/) can be exposed for integration scenarios over the classic client/server (RPC) interface and, optionally, over OPC UA PubSub — without modifying the companion specification. All NodeIds in the example namespace `http://opcfoundation.org/UA/PubSub/Examples/Pumps/` are provisional and the base-namespace binding types it references (`ScenarioBindingGroupType` etc.) carry the **provisional** NodeIds of the draft base specification.

## 1 Scope

This addendum defines example **scenario bindings** for the `PumpType` — 38 bound items across the scenarios *Observability, EnergyAndLoadManagement, PredictiveMaintenance, AnomalyDetection, FleetAndCompliance, AlarmAndEventDistribution* — per the [Scenario Bindings](../../OPC-UA-Scenario-Bindings.md) base specification. Pumps expose rich operational telemetry (flow, head, pressure, power, temperatures, efficiencies, rotor loads) plus identity and maintenance data, so most industrial scenarios map cleanly onto the pump measurement model.

## 2 Normative references

- [Scenario Bindings](../../OPC-UA-Scenario-Bindings.md) — the base binding model (types, discovery, the two-layer routing/semantic contract).
- [OPC UA for Pumps and Vacuum Pumps](https://reference.opcfoundation.org/Pumps/v100/docs/) — the companion specification whose type is bound.
- [OPC 10000-14](https://reference.opcfoundation.org/specs/OPC-10000-14/) — PubSub (optional realization).

## 3 How the bindings are applied

The bindings are authored at **two levels**, exactly as the base specification recommends:

1. **Type-level definitions (reusable).** The machine-readable descriptor [`Pumps.ScenarioBinding.json`](Pumps.ScenarioBinding.json) lists each bound item as a `BrowsePath` (RelativePath) from the `PumpType` root, with its routing `Kind` and scenario. Every path in §4 was **resolved against the published companion NodeSet**, so the bindings apply to *any* conforming instance.
2. **Instance overlay (concrete).** [`Opc.Ua.Pumps.ScenarioBinding.NodeSet2.xml`](Opc.Ua.Pumps.ScenarioBinding.NodeSet2.xml) instantiates a compact theoretical instance `ExamplePump`, applies the `IScenarioBoundType` interface, and exposes one `ScenarioBindingGroup` per scenario holding that scenario's `ScenarioBinding`/`BoundItem` instances. On the instance each `BoundItem` uses **`BindsToNode`** to point at the concrete signal node (the type-level `BrowsePath` and the instance `BindsToNode` are the two locators defined by the base specification).

> **Theoretical instance model.** The theoretical instance mirrors the official Pumps `instanceexample.xml` (an `ExamplePump : PumpType` with `Operational/Measurements`, `Identification`, `Supervision*`, `Maintenance` and a `<Drive>`); the bound BrowsePaths resolve against exactly that structure. See the reference model: [Pumps/instanceexample.xml](https://github.com/OPCFoundation/UA-Nodeset/blob/latest/Pumps/instanceexample.xml).

Only the bound signals are materialised in the overlay; it is an *illustrative* instance, not a conformant full instance of the companion type.

## 4 Scenario bindings for `PumpType`

Bindings for the `PumpType` of the `http://opcfoundation.org/UA/Pumps/` companion specification, per the [Scenario Bindings](../../OPC-UA-Scenario-Bindings.md) base specification. Each binding is **one Part 14 DataSet** with a deterministic `DataSetClassId`. Every data-DataSet `BrowsePath` below was resolved against the published companion NodeSet; event-DataSet fields select standard event-type fields.

#### Scenario: Observability

*URI:* `http://opcfoundation.org/UA/PubSub/Scenarios/Observability` · *Direction:* Publisher · *Content:* data DataSet (PublishedDataItems) · *DataSetClassId:* `96490f93-6c92-59cd-981d-4203ab067313` · *Cardinality:* one DataSet (bound root)

| Field | Kind | BrowsePath | Source type | DataType | OTEL |
|---|---|---|---|---|---|
| Speed | Telemetry | `/Operational/Measurements/Speed` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | Gauge [1/min] |
| Throughput | Telemetry | `/Operational/Measurements/Throughput` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | Gauge [m3/s] |
| MassFlow | Telemetry | `/Operational/Measurements/MassFlow` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | Gauge [kg/s] |
| ProcessPressure | Telemetry | `/Operational/Measurements/ProcessPressure` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | Gauge [Pa] |
| DifferentialPressure | Telemetry | `/Operational/Measurements/DifferentialPressure` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | Gauge [Pa] |
| PumpTotalHead | Telemetry | `/Operational/Measurements/PumpTotalHead` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | Gauge [m] |
| PumpPowerInput | Telemetry | `/Operational/Measurements/PumpPowerInput` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | Gauge [W] |
| FluidTemperature | Telemetry | `/Operational/Measurements/FluidTemperature` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | Gauge [Cel] |
| BearingTemperature | Telemetry | `/Operational/Measurements/BearingTemperature` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | Histogram [Cel] buckets 40,60,80,100,120 |
| PumpTemperature | Telemetry | `/Operational/Measurements/PumpTemperature` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | Gauge [Cel] |
| NumberOfStarts | Counter | `/Operational/Measurements/NumberOfStarts` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | UInt32 | Counter cumulative monotonic |
| Manufacturer | Dimension | `/Identification/Manufacturer` | [PropertyType](https://reference.opcfoundation.org/specs/OPC-10000-5/7.3) | LocalizedText | dimension |
| SerialNumber | Dimension | `/Identification/SerialNumber` | [PropertyType](https://reference.opcfoundation.org/specs/OPC-10000-5/7.3) | String | dimension |
| service.name | Dimension | — | — | — | dimension = `pump-observability` (const) |

#### Scenario: EnergyAndLoadManagement

*URI:* `http://opcfoundation.org/UA/PubSub/Scenarios/EnergyAndLoadManagement` · *Direction:* Publisher · *Content:* data DataSet (PublishedDataItems) · *DataSetClassId:* `605ca065-f5d7-5400-a9fe-995d21ad75ce` · *Cardinality:* one DataSet (bound root)

| Field | Kind | BrowsePath | Source type | DataType | OTEL |
|---|---|---|---|---|---|
| PumpPowerInput | Telemetry | `/Operational/Measurements/PumpPowerInput` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | — |
| PumpPowerOutput | Telemetry | `/Operational/Measurements/PumpPowerOutput` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | — |
| OverallEfficiency | Metric | `/Operational/Measurements/OverallEfficiency` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | — |
| PumpEfficiency | Metric | `/Operational/Measurements/PumpEfficiency` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | — |
| HydraulicEfficiency | Metric | `/Operational/Measurements/HydraulicEfficiency` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | — |

#### Scenario: PredictiveMaintenance

*URI:* `http://opcfoundation.org/UA/PubSub/Scenarios/PredictiveMaintenance` · *Direction:* Publisher · *Content:* data DataSet (PublishedDataItems) · *DataSetClassId:* `a96b90d3-7b07-55d8-8343-9c7e4df85bab` · *Cardinality:* one DataSet (bound root)

| Field | Kind | BrowsePath | Source type | DataType | OTEL |
|---|---|---|---|---|---|
| BearingTemperature | Telemetry | `/Operational/Measurements/BearingTemperature` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | — |
| AxialLoadOfPumpRotor | Telemetry | `/Operational/Measurements/AxialLoadOfPumpRotor` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | — |
| RadialLoadOfPumpRotor | Telemetry | `/Operational/Measurements/RadialLoadOfPumpRotor` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | — |
| LubricatingOilPressure | Telemetry | `/Operational/Measurements/LubricatingOilPressure` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | — |
| AxialRotorPosition | Telemetry | `/Operational/Measurements/AxialRotorPosition` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | — |
| NumberOfStarts | Counter | `/Operational/Measurements/NumberOfStarts` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | UInt32 | — |

#### Scenario: AnomalyDetection

*URI:* `http://opcfoundation.org/UA/PubSub/Scenarios/AnomalyDetection` · *Direction:* Publisher · *Content:* data DataSet (PublishedDataItems) · *DataSetClassId:* `d4eb3d5b-5ffb-580e-b96f-142cb3f998ad` · *Cardinality:* one DataSet (bound root)

| Field | Kind | BrowsePath | Source type | DataType | OTEL |
|---|---|---|---|---|---|
| SoundPower | Telemetry | `/Operational/Measurements/SoundPower` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | — |
| SoundPressureLevel | Telemetry | `/Operational/Measurements/SoundPressureLevel` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | — |
| DifferentialPressure | Telemetry | `/Operational/Measurements/DifferentialPressure` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | — |
| BearingTemperature | Telemetry | `/Operational/Measurements/BearingTemperature` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double | — |

#### Scenario: FleetAndCompliance

*URI:* `http://opcfoundation.org/UA/PubSub/Scenarios/FleetAndCompliance` · *Direction:* Publisher · *Content:* data DataSet (PublishedDataItems) · *DataSetClassId:* `c5ad94e3-12f1-5fa4-b69f-b8aeaf40106a` · *Cardinality:* one DataSet (bound root)

| Field | Kind | BrowsePath | Source type | DataType | OTEL |
|---|---|---|---|---|---|
| AssetId | Identification | `/Identification/AssetId` | [PropertyType](https://reference.opcfoundation.org/specs/OPC-10000-5/7.3) | String | — |
| Location | Identification | `/Identification/Location` | [PropertyType](https://reference.opcfoundation.org/specs/OPC-10000-5/7.3) | String | — |

#### Scenario: AlarmAndEventDistribution

*URI:* `http://opcfoundation.org/UA/PubSub/Scenarios/AlarmAndEventDistribution` · *Direction:* Publisher · *Content:* event DataSet (PublishedEvents) · *DataSetClassId:* `700f61a4-4e97-52ed-b72e-f085d406ced9` · *Cardinality:* one DataSet (bound root) · *Event source:* `/` · *Event type:* BaseEventType

| Field | Kind | Event field / attribute |
|---|---|---|
| EventId | Event | `/EventId` |
| EventType | Event | `/EventType` |
| SourceName | Event | `/SourceName` |
| Time | Event | `/Time` |
| Severity | Event | `/Severity` |
| Message | Event | `/Message` |
| service.name | Dimension | dimension = `pump-observability` (const) |

*Structured-log mapping (OTEL LogRecord):* body template `{SourceName}: {Message} (severity {Severity})`; severity = `Severity`, body = `Message`, timestamp = `Time`.


## 5 Where the bindings live

Overview of the scenario bindings, then their placement on the theoretical instance (one `ScenarioBindingGroup` per scenario hangs off the instance; each `BoundItem` `BindsToNode` its signal):

```mermaid
graph LR
  ROOT["ExamplePump : PumpType"]
  ROOT --> G0["Observability<br/>ScenarioBindingGroup"]
  G0 --> S0["Observability<br/>Publisher · Data"]
  S0 --> S0_0["Speed : Telemetry"]
  S0 --> S0_1["Throughput : Telemetry"]
  S0 --> S0_2["MassFlow : Telemetry"]
  S0 --> S0_3["ProcessPressure : Telemetry"]
  S0 --> S0_4["DifferentialPressure : Telemetry"]
  S0 --> S0_5["PumpTotalHead : Telemetry"]
  ROOT --> G1["EnergyAndLoadManagement<br/>ScenarioBindingGroup"]
  G1 --> S1["EnergyAndLoadManagement<br/>Publisher · Data"]
  S1 --> S1_0["PumpPowerInput : Telemetry"]
  S1 --> S1_1["PumpPowerOutput : Telemetry"]
  S1 --> S1_2["OverallEfficiency : Metric"]
  S1 --> S1_3["PumpEfficiency : Metric"]
  S1 --> S1_4["HydraulicEfficiency : Metric"]
  ROOT --> G2["PredictiveMaintenance<br/>ScenarioBindingGroup"]
  G2 --> S2["PredictiveMaintenance<br/>Publisher · Data"]
  S2 --> S2_0["BearingTemperature : Telemetry"]
  S2 --> S2_1["AxialLoadOfPumpRotor : Telemetry"]
  S2 --> S2_2["RadialLoadOfPumpRotor : Telemetry"]
  S2 --> S2_3["LubricatingOilPressure : Telemetry"]
  S2 --> S2_4["AxialRotorPosition : Telemetry"]
  S2 --> S2_5["NumberOfStarts : Counter"]
  ROOT --> G3["AnomalyDetection<br/>ScenarioBindingGroup"]
  G3 --> S3["AnomalyDetection<br/>Publisher · Data"]
  S3 --> S3_0["SoundPower : Telemetry"]
  S3 --> S3_1["SoundPressureLevel : Telemetry"]
  S3 --> S3_2["DifferentialPressure : Telemetry"]
  S3 --> S3_3["BearingTemperature : Telemetry"]
  ROOT --> G4["FleetAndCompliance<br/>ScenarioBindingGroup"]
  G4 --> S4["FleetAndCompliance<br/>Publisher · Data"]
  S4 --> S4_0["AssetId : Identification"]
  S4 --> S4_1["Location : Identification"]
  ROOT --> G5["AlarmAndEventDistribution<br/>ScenarioBindingGroup"]
  G5 --> S5["AlarmAndEventDistribution<br/>Publisher · Events"]
  S5 --> S5_0["EventId : Event"]
  S5 --> S5_1["EventType : Event"]
  S5 --> S5_2["SourceName : Event"]
  S5 --> S5_3["Time : Event"]
  S5 --> S5_4["Severity : Event"]
  S5 --> S5_5["Message : Event"]
```

```mermaid
graph TD
  R["ExamplePump : PumpType"]
  R -->|HasInterface| I([IScenarioBoundType])
  R -->|HasComponent| G0["Observability : ScenarioBindingGroupType"]
  G0 -.Realizes.-> P0["Observability : ScenarioProfileType<br/>under Server/Scenarios"]
  G0 -->|HasComponent| B0["Observability : ScenarioBindingType"]
  B0 -->|HasComponent| IT00["Speed : BoundVariableType"]
  IT00 -->|BindsToNode| N00["Operational/Measurements/Speed"]
  B0 -->|HasComponent| IT01["Throughput : BoundVariableType"]
  IT01 -->|BindsToNode| N01["Operational/Measurements/Throughput"]
  B0 -->|HasComponent| IT02["MassFlow : BoundVariableType"]
  IT02 -->|BindsToNode| N02["Operational/Measurements/MassFlow"]
  R -->|HasComponent| G1["AlarmAndEventDistribution : ScenarioBindingGroupType"]
  G1 -.Realizes.-> P1["AlarmAndEventDistribution : ScenarioProfileType<br/>under Server/Scenarios"]
  G1 -->|HasComponent| B1["AlarmAndEventDistribution : ScenarioBindingType"]
  B1 -->|HasComponent| IT10["EventId : BoundEventFieldType"]
  IT10 -.event field.-> N10["BaseEventType/EventId"]
  B1 -->|HasComponent| IT11["EventType : BoundEventFieldType"]
  IT11 -.event field.-> N11["BaseEventType/EventType"]
  B1 -->|HasComponent| IT12["SourceName : BoundEventFieldType"]
  IT12 -.event field.-> N12["BaseEventType/SourceName"]
```

## 6 Deliverables

| File | Content |
|---|---|
| [`Pumps.ScenarioBinding.json`](Pumps.ScenarioBinding.json) | Machine-readable ScenarioBindingConfiguration descriptor (single source). |
| [`Opc.Ua.Pumps.ScenarioBinding.NodeSet2.xml`](Opc.Ua.Pumps.ScenarioBinding.NodeSet2.xml) | The binding instances on the theoretical `ExamplePump` instance. |

Regenerate with `python ../tools/build_bindings.py pumps/Pumps.ScenarioBinding.json`.

