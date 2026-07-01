# OPC UA Pumps — PubSub Scenario Binding Addendum

**Working draft — a worked example of the [PubSub Scenario Binding](../../OPC-UA-PubSub-Scenario-Binding.md) base specification applied to OPC UA for Pumps and Vacuum Pumps.**

> **Status — illustrative example.** This addendum shows how the instances of the `PumpType` (http://opcfoundation.org/UA/Pumps/) can be exposed over OPC UA PubSub for integration scenarios, without modifying the companion specification. All NodeIds in the example namespace `http://opcfoundation.org/UA/PubSub/Examples/Pumps/` are provisional and the base-namespace binding types it references (`PubSubScenarioBindingsType` etc.) carry the **provisional** NodeIds of the draft base specification.

## 1 Scope

This addendum defines example **scenario bindings** for the `PumpType` — 31 bound items across the scenarios *Observability, EnergyAndLoadManagement, PredictiveMaintenance, AnomalyDetection, FleetAndCompliance* — per the [PubSub Scenario Binding](../../OPC-UA-PubSub-Scenario-Binding.md) base specification. Pumps expose rich operational telemetry (flow, head, pressure, power, temperatures, efficiencies, rotor loads) plus identity and maintenance data, so most industrial scenarios map cleanly onto the pump measurement model.

## 2 Normative references

- [PubSub Scenario Binding](../../OPC-UA-PubSub-Scenario-Binding.md) — the base binding model (types, discovery, the two-layer routing/semantic contract).
- [OPC UA for Pumps and Vacuum Pumps](https://reference.opcfoundation.org/Pumps/v100/docs/) — the companion specification whose type is bound.
- [OPC 10000-14](https://reference.opcfoundation.org/specs/OPC-10000-14/) — PubSub (optional realization).

## 3 How the bindings are applied

The bindings are authored at **two levels**, exactly as the base specification recommends:

1. **Type-level definitions (reusable).** The machine-readable descriptor [`Pumps.ScenarioBinding.json`](Pumps.ScenarioBinding.json) lists each bound item as a `BrowsePath` (RelativePath) from the `PumpType` root, with its routing `Kind` and scenario. Every path in §4 was **resolved against the published companion NodeSet**, so the bindings apply to *any* conforming instance.
2. **Instance overlay (concrete).** [`Opc.Ua.Pumps.ScenarioBinding.NodeSet2.xml`](Opc.Ua.Pumps.ScenarioBinding.NodeSet2.xml) instantiates a compact theoretical instance `ExamplePump`, applies the `IPubSubScenarioBoundType` interface, and hangs a `ScenarioBindings` container holding the `ScenarioBinding`/`BoundItem` instances. On the instance each `BoundItem` uses **`BindsToNode`** to point at the concrete signal node (the type-level `BrowsePath` and the instance `BindsToNode` are the two locators defined by the base specification).

> **Theoretical instance model.** The theoretical instance mirrors the official Pumps `instanceexample.xml` (an `ExamplePump : PumpType` with `Operational/Measurements`, `Identification`, `Supervision*`, `Maintenance` and a `<Drive>`); the bound BrowsePaths resolve against exactly that structure. See the reference model: [Pumps/instanceexample.xml](https://github.com/OPCFoundation/UA-Nodeset/blob/latest/Pumps/instanceexample.xml).

Only the bound signals are materialised in the overlay; it is an *illustrative* instance, not a conformant full instance of the companion type.

## 4 Scenario bindings for `PumpType`

Bindings for the `PumpType` of the `http://opcfoundation.org/UA/Pumps/` companion specification, per the [PubSub Scenario Binding](../../OPC-UA-PubSub-Scenario-Binding.md) base specification. Every `BrowsePath` below was resolved against the published companion NodeSet.

#### Scenario: Observability

*URI:* `http://opcfoundation.org/UA/PubSub/Scenarios/Observability` · *Direction:* Publisher

| Field | Kind | BrowsePath | Source type | DataType |
|---|---|---|---|---|
| Speed | Telemetry | `/Operational/Measurements/Speed` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| Throughput | Telemetry | `/Operational/Measurements/Throughput` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| MassFlow | Telemetry | `/Operational/Measurements/MassFlow` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| ProcessPressure | Telemetry | `/Operational/Measurements/ProcessPressure` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| DifferentialPressure | Telemetry | `/Operational/Measurements/DifferentialPressure` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| PumpTotalHead | Telemetry | `/Operational/Measurements/PumpTotalHead` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| PumpPowerInput | Telemetry | `/Operational/Measurements/PumpPowerInput` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| FluidTemperature | Telemetry | `/Operational/Measurements/FluidTemperature` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| BearingTemperature | Telemetry | `/Operational/Measurements/BearingTemperature` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| PumpTemperature | Telemetry | `/Operational/Measurements/PumpTemperature` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |

#### Scenario: EnergyAndLoadManagement

*URI:* `http://opcfoundation.org/UA/PubSub/Scenarios/EnergyAndLoadManagement` · *Direction:* Publisher

| Field | Kind | BrowsePath | Source type | DataType |
|---|---|---|---|---|
| PumpPowerInput | Telemetry | `/Operational/Measurements/PumpPowerInput` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| PumpPowerOutput | Telemetry | `/Operational/Measurements/PumpPowerOutput` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| OverallEfficiency | Metric | `/Operational/Measurements/OverallEfficiency` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| PumpEfficiency | Metric | `/Operational/Measurements/PumpEfficiency` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| HydraulicEfficiency | Metric | `/Operational/Measurements/HydraulicEfficiency` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |

#### Scenario: PredictiveMaintenance

*URI:* `http://opcfoundation.org/UA/PubSub/Scenarios/PredictiveMaintenance` · *Direction:* Publisher

| Field | Kind | BrowsePath | Source type | DataType |
|---|---|---|---|---|
| BearingTemperature | Telemetry | `/Operational/Measurements/BearingTemperature` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| AxialLoadOfPumpRotor | Telemetry | `/Operational/Measurements/AxialLoadOfPumpRotor` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| RadialLoadOfPumpRotor | Telemetry | `/Operational/Measurements/RadialLoadOfPumpRotor` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| LubricatingOilPressure | Telemetry | `/Operational/Measurements/LubricatingOilPressure` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| AxialRotorPosition | Telemetry | `/Operational/Measurements/AxialRotorPosition` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| NumberOfStarts | Counter | `/Operational/Measurements/NumberOfStarts` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | UInt32 |

#### Scenario: AnomalyDetection

*URI:* `http://opcfoundation.org/UA/PubSub/Scenarios/AnomalyDetection` · *Direction:* Publisher

| Field | Kind | BrowsePath | Source type | DataType |
|---|---|---|---|---|
| SoundPower | Telemetry | `/Operational/Measurements/SoundPower` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| SoundPressureLevel | Telemetry | `/Operational/Measurements/SoundPressureLevel` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| DifferentialPressure | Telemetry | `/Operational/Measurements/DifferentialPressure` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |
| BearingTemperature | Telemetry | `/Operational/Measurements/BearingTemperature` | [BaseAnalogType](https://reference.opcfoundation.org/specs/OPC-10000-8/5.3.2) | Double |

#### Scenario: FleetAndCompliance

*URI:* `http://opcfoundation.org/UA/PubSub/Scenarios/FleetAndCompliance` · *Direction:* Publisher

| Field | Kind | BrowsePath | Source type | DataType |
|---|---|---|---|---|
| Manufacturer | Identification | `/Identification/Manufacturer` | [PropertyType](https://reference.opcfoundation.org/specs/OPC-10000-5/7.3) | LocalizedText |
| Model | Identification | `/Identification/Model` | [PropertyType](https://reference.opcfoundation.org/specs/OPC-10000-5/7.3) | LocalizedText |
| SerialNumber | Identification | `/Identification/SerialNumber` | [PropertyType](https://reference.opcfoundation.org/specs/OPC-10000-5/7.3) | String |
| ProductInstanceUri | Identification | `/Identification/ProductInstanceUri` | [PropertyType](https://reference.opcfoundation.org/specs/OPC-10000-5/7.3) | String |
| AssetId | Identification | `/Identification/AssetId` | [PropertyType](https://reference.opcfoundation.org/specs/OPC-10000-5/7.3) | String |
| Location | Identification | `/Identification/Location` | [PropertyType](https://reference.opcfoundation.org/specs/OPC-10000-5/7.3) | String |


## 5 Where the bindings live

Overview of the scenario bindings, then their placement on the theoretical instance (`ScenarioBindings` hangs off the instance; each `BoundItem` `BindsToNode` its signal):

```mermaid
graph LR
  ROOT["ExamplePump : PumpType"] --> SB["ScenarioBindings"]
  SB --> S0["Observability<br/>Publisher"]
  S0 --> S0_0["Speed : Telemetry"]
  S0 --> S0_1["Throughput : Telemetry"]
  S0 --> S0_2["MassFlow : Telemetry"]
  S0 --> S0_3["ProcessPressure : Telemetry"]
  S0 --> S0_4["DifferentialPressure : Telemetry"]
  S0 --> S0_5["PumpTotalHead : Telemetry"]
  SB --> S1["EnergyAndLoadManagement<br/>Publisher"]
  S1 --> S1_0["PumpPowerInput : Telemetry"]
  S1 --> S1_1["PumpPowerOutput : Telemetry"]
  S1 --> S1_2["OverallEfficiency : Metric"]
  S1 --> S1_3["PumpEfficiency : Metric"]
  S1 --> S1_4["HydraulicEfficiency : Metric"]
  SB --> S2["PredictiveMaintenance<br/>Publisher"]
  S2 --> S2_0["BearingTemperature : Telemetry"]
  S2 --> S2_1["AxialLoadOfPumpRotor : Telemetry"]
  S2 --> S2_2["RadialLoadOfPumpRotor : Telemetry"]
  S2 --> S2_3["LubricatingOilPressure : Telemetry"]
  S2 --> S2_4["AxialRotorPosition : Telemetry"]
  S2 --> S2_5["NumberOfStarts : Counter"]
  SB --> S3["AnomalyDetection<br/>Publisher"]
  S3 --> S3_0["SoundPower : Telemetry"]
  S3 --> S3_1["SoundPressureLevel : Telemetry"]
  S3 --> S3_2["DifferentialPressure : Telemetry"]
  S3 --> S3_3["BearingTemperature : Telemetry"]
  SB --> S4["FleetAndCompliance<br/>Publisher"]
  S4 --> S4_0["Manufacturer : Identification"]
  S4 --> S4_1["Model : Identification"]
  S4 --> S4_2["SerialNumber : Identification"]
  S4 --> S4_3["ProductInstanceUri : Identification"]
  S4 --> S4_4["AssetId : Identification"]
  S4 --> S4_5["Location : Identification"]
```

```mermaid
graph TD
  R["ExamplePump : PumpType"]
  R -->|HasInterface| I([IPubSubScenarioBoundType])
  R -->|HasComponent| SB["ScenarioBindings"]
  SB -->|HasComponent| B0["Observability : ScenarioBindingType"]
  B0 -->|HasComponent| IT00["Speed : BoundVariableType"]
  IT00 -->|BindsToNode| N00["Operational/Measurements/Speed"]
  B0 -->|HasComponent| IT01["Throughput : BoundVariableType"]
  IT01 -->|BindsToNode| N01["Operational/Measurements/Throughput"]
  B0 -->|HasComponent| IT02["MassFlow : BoundVariableType"]
  IT02 -->|BindsToNode| N02["Operational/Measurements/MassFlow"]
  SB -->|HasComponent| B1["EnergyAndLoadManagement : ScenarioBindingType"]
  B1 -->|HasComponent| IT10["PumpPowerInput : BoundVariableType"]
  IT10 -->|BindsToNode| N10["Operational/Measurements/PumpPowerInput"]
  B1 -->|HasComponent| IT11["PumpPowerOutput : BoundVariableType"]
  IT11 -->|BindsToNode| N11["Operational/Measurements/PumpPowerOutput"]
  B1 -->|HasComponent| IT12["OverallEfficiency : BoundVariableType"]
  IT12 -->|BindsToNode| N12["Operational/Measurements/OverallEfficiency"]
```

## 6 Deliverables

| File | Content |
|---|---|
| [`Pumps.ScenarioBinding.json`](Pumps.ScenarioBinding.json) | Machine-readable ScenarioBindingConfiguration descriptor (single source). |
| [`Opc.Ua.Pumps.ScenarioBinding.NodeSet2.xml`](Opc.Ua.Pumps.ScenarioBinding.NodeSet2.xml) | The binding instances on the theoretical `ExamplePump` instance. |

Regenerate with `python ../tools/build_bindings.py pumps/Pumps.ScenarioBinding.json`.

