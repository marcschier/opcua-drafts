---
name: opcua-scenario-binding
description: >-
  Generate OPC UA PubSub Scenario Bindings for any companion specification. Given a
  companion-spec NodeSet2.xml, classify its Variables and Methods into integration
  Scenarios (Observability, PredictiveMaintenance, AnomalyDetection, …) and routing
  Kinds (Telemetry, Status, Event, Command, …), emit type-level bindings as
  RelativePaths, and produce (a) a machine-readable ScenarioBindingConfiguration
  descriptor, (b) a human-readable binding annex, and optionally (c) a UANodeSet
  binding fragment. Implements the "OPC UA — PubSub Scenario Binding" base-namespace
  specification (core-specs/pubsub-binding). WHEN: add PubSub bindings to a companion
  spec, expose a companion spec over PubSub, generate scenario bindings, PubSub
  scenario annex, bind variables to scenarios, make a model observable/analytics-ready.
---

# OPC UA PubSub Scenario Binding

This skill makes any OPC UA Information Model **consumable over PubSub for integration
scenarios** by producing the bindings defined in the *OPC UA — PubSub Scenario Binding*
specification (`core-specs/pubsub-binding/OPC-UA-PubSub-Scenario-Binding.md`). It does the
*authoring* (semantic classification, which a human/LLM is good at); a deterministic
generator does the *expansion* into artifacts (which a program is good at).

Read the specification first — this skill assumes its two-layer contract:

- **Routing** (for a generic bridge): a `ScenarioUri` per binding + a `Kind` per item.
- **Semantic cross-reference** (for the ultimate consumer): each item retains
  `TypeDefinition`, namespace-qualified `BrowseName`, `ModelNamespaceUri` and any
  dictionary entry, and this is propagated into Part 14 `DataSetMetaData`.

## When to use

Use this skill when a user wants to expose a companion specification (or any device /
vendor model) over OPC UA PubSub for analytics, observability, predictive maintenance,
anomaly detection, energy management, alarm distribution, or fleet/compliance — without
hand-writing PubSub configuration per project.

## Inputs

1. The companion spec **NodeSet2.xml** (required) — the source of types, members and BrowseNames.
2. The companion spec **document** (optional but recommended) — for its own scenario/PubSub
   section, EU/engineering-unit hints, and any existing analytics guidance.
3. The **target Scenario set** (optional) — defaults to the six baseline Scenarios below;
   the user may add vendor Scenarios (their own URI authority).

## Outputs

- `bindings/<Model>.ScenarioBinding.json` — the machine-readable
  **ScenarioBindingConfiguration** descriptor (single source of truth).
- `bindings/<Model>-scenario-binding-annex.md` — the human-readable **annex** (tables per
  Scenario listing each bound item, its RelativePath, Kind and semantic reference).
- *(optional)* `bindings/<Model>.ScenarioBinding.NodeSet2.xml` — a **UANodeSet fragment**
  instantiating the bindings on the model's types, ready to merge into a server.

Do **not** invent a domain example annex inside this skill; always generate from the actual
input NodeSet.

## Procedure

### 1. Parse the model

Enumerate every `UAObjectType`/`UAVariableType` and, within each, its member Variables
(including nested Objects' Variables to a sensible depth) and Methods. For each member record:
`BrowseName` (with namespace), the RelativePath from the owning type root, `DataType`,
`ValueRank`, `ModellingRule`, and the member's TypeDefinition. Note placeholders
(`OptionalPlaceholder`/`MandatoryPlaceholder`) — they become multi-match BrowsePaths.

### 2. Classify each item's Kind (routing role)

`Kind` is domain-agnostic. Apply, in order:

| Signal in the model | Kind |
|---|---|
| Method node | `Command` |
| Variable whose TypeDefinition derives from a condition/alarm/event type, or whose name ends `Event`/`Alarm`/`Fault`/`Trip` | `Event` |
| Variable named `*State`, `*Status`, `*Mode`, `Enabled`, `Ready`, `Health`, or DataType is an Enumeration/Boolean state | `Status` |
| Variable named `*SetPoint`, `*Setpoint`, `*Command`, `*Target`, writable and control-like | `Setpoint` |
| Static nameplate/identity property (`Manufacturer`, `Model`, `SerialNumber`, `*Rating`, asset id) | `Identification` |
| Configuration/parameter property that changes rarely (`*Configuration`, thresholds, limits) | `Configuration` |
| Numeric measured Variable (`AnalogItemType`/has `EngineeringUnits`, or continuous physical quantity) | `Telemetry` |
| Monotonic total/accumulator (`*Count`, `*Hours`, `*Energy`, `*Total`) | `Counter` |
| Aggregated KPI or computed value | `Metric` |
| Anything else exposed | `Other` |

`Kind` values are exactly the members of `BoundItemKindEnum` in the spec:
`Telemetry`, `Status`, `Configuration`, `Metric`, `Counter`, `Event`, `Command`,
`Setpoint`, `Identification`, `Other`. When unsure between `Telemetry` and a total,
prefer `Telemetry` for instantaneous values and `Counter` for monotonic accumulators.

### 3. Assign items to Scenarios

An item may belong to **several** Scenarios. Use these heuristics; a binding is created per
(Scenario, Direction) with the items assigned to it.

| Scenario URI (`…/UA/PubSub/Scenarios/<Name>`) | Include items that are… |
|---|---|
| `Observability` | operational Telemetry + Status + primary Events; the "what's happening now" set an HMI would show. |
| `PredictiveMaintenance` | usage/wear Counters and Metrics (`*Hours`, `*Count`, temperatures, pressures, vibration), plus maintenance-relevant Status/Events. |
| `AnomalyDetection` | high-resolution correlated Telemetry (electrical, thermal, mechanical signals) suitable for baseline/deviation models. |
| `EnergyAndLoadManagement` | power/load/energy/demand Telemetry & Metrics and related Setpoints/Commands. |
| `AlarmAndEventDistribution` | all Event/Alarm items and their acknowledge/reset Methods. |
| `FleetAndCompliance` | identity/nameplate `Identification` + compliance-relevant Metrics/Events for multi-site reporting. |

Set each binding's **Direction** (a `ScenarioBindingDirectionEnum` value — the role the
*server* offers): `Publisher` for read/telemetry scenarios (a client sets up a subscriber);
`Subscriber` when a client feeds data into the server; `ActionInvoker` for delivering
Commands to bound Methods; `ActionResponder` when clients invoke bound Actions;
`Bidirectional` when both apply.

Give each item a stable `FieldName` (default: the BrowseName; disambiguate placeholders by
appending the matched BrowseName as the spec requires).

### 4. Fill the semantic cross-reference (mechanical)

For every item, populate from the NodeSet (do not guess):
`SourceTypeDefinition`, `SourceBrowseName` (with namespace), `ModelNamespaceUri`,
`AttributeId` (13/Value unless otherwise), and `SemanticReferenceUri` — set the last from
the identifier of any `HasDictionaryEntry` target (OPC 10000-19) or a known IRDI/CDD, if the
model has one. Set `BrowsePath` to the RelativePath from the type root (recommended
locator); leave absolute NodeIds unset for type-level bindings.

### 5. Emit the descriptor

Write `ScenarioBindingConfiguration` (see format below). This is the single source; the
annex and the NodeSet fragment are **derived** from it, never authored separately.

### 6. Generate annex (+ optional NodeSet fragment)

Render one annex table per Scenario. Link each Scenario URI and each referenced base type
to `https://reference.opcfoundation.org/` and each own concept to the spec's Annex A anchors,
matching the style of `core-specs/pubsub-binding` and `companion-specs/Generators`. If a
NodeSet fragment is requested, instantiate `ScenarioBindingType`/`BoundVariableType`/
`BoundMethodType` under an `IPubSubScenarioBoundType` interface applied to each bound type,
with `BrowsePath` values from the descriptor. Leave transport/security/addressing as
deployment parameters — never bake them in.

### 7. Validate

- Every `BrowsePath` resolves against the input NodeSet (dry-run TranslateBrowsePath).
- Every item has a `Kind`, a `FieldName` and a complete semantic cross-reference.
- Scenario URIs are well-formed; vendor Scenarios use the vendor's own URI authority and
  **not** the reserved `…/opcfoundation.org/UA/PubSub/Scenarios/` root.
- Field names are unique within a binding.

## ScenarioBindingConfiguration descriptor (format)

A single JSON object that is an **authoring DSL** for the spec's
`ScenarioBindingConfigurationDataType` (§5.8): it carries exactly the same fields, but in a
human-writable form. The deterministic generator converts it to the OPC UA DataType (and to
the annex and NodeSet fragment). It is *not* raw OPC UA JSON encoding — the conversion rules
below define the mapping so the result is unambiguous.

```json
{
  "modelNamespaceUri": "http://example.org/UA/<Model>/",
  "appliesToType": "1:<BrowseName of the bound ObjectType, e.g. GeneratorType>",
  "configurationVersion": { "majorVersion": 1, "minorVersion": 0 },
  "scenarioBindings": [
    {
      "name": "Observability",
      "scenarioUri": "http://opcfoundation.org/UA/PubSub/Scenarios/Observability",
      "direction": "Publisher",
      "boundItems": [
        {
          "fieldName": "ActivePower",
          "kind": "Telemetry",
          "browsePath": "/1:ElectricalMeasurements/1:ActivePower",
          "attributeId": 13,
          "sourceTypeDefinition": "1:AnalogUnitType",
          "sourceBrowseName": "1:ActivePower",
          "modelNamespaceUri": "http://example.org/UA/<Model>/",
          "semanticReferenceUri": null,
          "dataSetFieldId": null,
          "samplingIntervalHint": 1000
        }
      ]
    }
  ]
}
```

Conversion rules (DSL → `ScenarioBindingConfigurationDataType`):
- `appliesToType`, `sourceBrowseName` → `QualifiedName`, written `"<nsIndex>:<Name>"`; the
  generator resolves `<nsIndex>` against `modelNamespaceUri` and the target NodeSet's namespace table.
- `browsePath`, `owningObjectPath` → `RelativePath`, written in the standard OPC UA
  RelativePath text form (`/1:Child/1:Grandchild`); the generator parses it to a `RelativePath` value.
- `sourceTypeDefinition`, `sourceNodeId`, `startingNode` → `NodeId`, written as an
  expanded NodeId string (`nsu=<uri>;i=…` or `<nsIndex>:<BrowseName>` for a type, which the
  generator resolves).
- `dataSetFieldId` → `Guid`; **omit or `null`** to have the generator assign a stable GUID
  (recommended). It becomes `FieldMetaData.dataSetFieldId` in the realized PublishedDataSet.
- `direction` ∈ `Publisher` | `Subscriber` | `ActionInvoker` | `ActionResponder` |
  `Bidirectional` (`ScenarioBindingDirectionEnum`).
- `kind` ∈ `Telemetry` | `Status` | `Configuration` | `Metric` | `Counter` | `Event` |
  `Command` | `Setpoint` | `Identification` | `Other` (`BoundItemKindEnum`).
- For a Method, use a `boundItems` entry with `kind: "Command"`, `browsePath` to the Method,
  and `owningObjectPath` (RelativePath to the owning Object; default: the bound root).

## Annex template (per Scenario)

```markdown
### Scenario: <Name>

*URI:* `http://opcfoundation.org/UA/PubSub/Scenarios/<Name>` · *Direction:* <Direction>

| Field | Kind | BrowsePath | Source type | DataType | Semantic ref |
|---|---|---|---|---|---|
| ActivePower | Telemetry | `/ElectricalMeasurements/ActivePower` | [AnalogUnitType](https://reference.opcfoundation.org/…) | Double | — |
```

Prefix the annex with a note that all NodeIds/paths are relative to the companion model and
that the bindings realize the *PubSub Scenario Binding* base specification.

## Quality bar

- Author intent (which items, which scenarios, which Kind) is the human/LLM contribution;
  everything mechanical (semantic fields, paths, tables) is generated from the NodeSet so it
  cannot drift.
- Never require a bridge to understand the domain — Kind + ScenarioUri must be enough to route.
- Keep the descriptor the single source of truth; regenerate the annex and fragment from it.
