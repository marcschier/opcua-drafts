The ObjectTypes this specification defines are described below, each with the table that defines it.

### GeneratorSetType {#sec-generatorsettype}

`GeneratorSetType` is the central type of this specification. Its mandatory content is the `OperatingState`, the `OperatingMode`, the `Engine`, `Alternator` and `Controller` components, the `Identification` add-in and a `Ratings` folder. Its optional content is the fuel, cooling, lubrication and starting subsystems, the `EmissionsStandard` and `Application`, the breaker and readiness signals, and the building blocks of OPC 40001-1.

The Methods are `Start`, which starts the set in its current mode, `Stop`, `EmergencyStop`, `ResetFaults`, `SetOperatingMode` and `StartTest`. The type generates events of `GeneratorProtectionAlarmType`.

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

### GeneratorIdentificationType {#sec-generatoridentificationtype}

`GeneratorIdentificationType` specialises the `MachineIdentificationType` of OPC 40001-1 with the nameplate fields a generator set has beyond those of a machine in general: the engine and alternator models, the rated power, and the emissions standard the set is certified to.

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

### EngineType {#sec-enginetype}

`EngineType` exposes the classic engine telemetry: `Speed`, `OilPressure`, `CoolantTemperature`, `FuelRate`, `EngineHours`, the boost, exhaust and intake temperatures, and the percentages of load and torque. The parameter number each variable corresponds to is recorded in the variable description, so that a gateway can map the signals of SAE J1939 directly onto the model.

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

### J1939DiagnosticInterfaceType {#sec-j1939diagnosticinterfacetype}

`J1939DiagnosticInterfaceType` models the CAN bus network itself: the `ProtocolName`, `NetworkName`, `SourceAddress`, `Baudrate` and `BusState`, the four lamp statuses defined by SAE J1939 — each a `J1939LampStatusEnum` conveying Off, On, SlowFlash or FastFlash — and the arrays of active and previously active diagnostic trouble codes.

Each diagnostic trouble code carries an `Spn`, an `Fmi`, an `OccurrenceCount`, a `SourceAddress` and `SourceName` so that faults from several control units on the bus remain distinguishable, and a `Severity`. The `ClearPreviouslyActiveDtcs` Method clears the previously active codes.

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

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-CANbus |  |  |  |  |  |

### ExhaustAftertreatmentType {#sec-exhaustaftertreatmenttype}

`ExhaustAftertreatmentType` models the exhaust aftertreatment a set needs to meet the stricter emissions standards: the state of the aftertreatment system, the level of diesel exhaust fluid, and the soot load of the particulate filter.

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

### AlternatorType {#sec-alternatortype}

`AlternatorType` provides the aggregate electrical values: the `Frequency`, the total real, reactive and apparent power, the average voltages and current, the `AveragePowerFactor`, the `TotalRealEnergy`, the `LoadPercent`, the winding and bearing temperatures, the `Connection`, the `ExcitationType` and the `NumberOfPoles`. It carries three phase objects, `L1`, `L2` and `L3`. A single-phase set populates only `L1`, which is mandatory; a three-phase set populates all three.

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

### AlternatorPhaseType {#sec-alternatorphasetype}

`AlternatorPhaseType` carries the per-phase voltage, current, power and power factor of one phase of an alternator.

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

### FuelSystemType {#sec-fuelsystemtype}

`FuelSystemType` models the fuel supply: the fuel type, level, rate and pressure, the gas supply pressure where the set burns gas, the runtime remaining, the level of diesel exhaust fluid where the set has aftertreatment, and the detection of water in the fuel.

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

`CoolingSystemType` models the cooling circuit: the coolant temperature, level and pressure, the cooling method, and the state of the radiator fan and the jacket-water heater.

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

`LubricationSystemType` models the lubrication circuit: the oil pressure, temperature and level, and the differential pressure across the oil filter.

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

`StartingSystemType` models the starting and battery circuit: the battery voltage and charging current, the status of the charger, and the number of start attempts.

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

### GeneratorControllerType {#sec-generatorcontrollertype}

`GeneratorControllerType` represents the control panel. It carries the identity of the controller — the `ControllerFamily`, `FirmwareVersion`, `ApplicationSoftwareVersion` and `ConfigurationVersion` — the operating annunciation `InAutoMode` and `NotInAuto`, the remote enablement `RemoteStartEnabled` and `RemoteControlEnabled`, and the remote-monitoring status `CloudConnected`, `ModbusEnabled` and `SignalStrength`.

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

### GeneratorRatingType {#sec-generatorratingtype}

A set is usually certified for several duties, so ratings are modelled as a list rather than as a single set of values. The `Ratings` folder on a `GeneratorSetType` contains zero or more `GeneratorRatingType` objects, each carrying an `ApplicationRating` and the rated power, voltage, current, frequency, speed, power factor and phase count, together with the reference ambient temperature and altitude they are quoted at.

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

### GeneratorStateMachineType {#sec-generatorstatemachinetype}

`OperatingState` is a finite state machine with twelve states and the transitions shown in [](#fig-generator-operating-state-machine). It is the detailed, generator-specific complement to the generic `MachineryItemState` of OPC 40001-1.

```{figure}
id: fig-generator-operating-state-machine
caption: The generator operating state machine
source: figures/generator-operating-state-machine.pptx
freeform: true
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

### GeneratorProtectionAlarmType {#sec-generatorprotectionalarmtype}

`GeneratorProtectionAlarmType` reports any protection or shutdown condition. Its `ProtectionFunction` Property, a `GeneratorProtectionFunctionEnum`, identifies the condition; the `GeneratorAlarmSeverity`, `IsShutdown`, `Spn`, `Fmi` and `SubsystemName` add context.

Because the type is an `OffNormalAlarmType`, the normal state is the healthy, untripped state: on an instance, the inherited `NormalState` references the Node representing the healthy value, `InputNode` references the supervised input, and `SourceNode` references the owning generator set or subsystem so that Clients can locate the origin. Analog limit conditions such as over-voltage and under-voltage **may** additionally be surfaced with the standard level alarms of OPC 10000-9 on the corresponding measured Variables.

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

| **Conformance Units** |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| GEN-Alarms |  |  |  |  |  |

### AutomaticTransferSwitchType {#sec-automatictransferswitchtype}

`AutomaticTransferSwitchType` models an automatic transfer switch: the `Position`, `OperatingState` and `TransitionType`, two structured sources `Source1` and `Source2`, the `PreferredSource`, the source connection flags, `TransferInhibited` and `TransferInhibitReason`, the ratings, the load metering, and the transfer timers and counters. Its Methods are `Transfer`, `Retransfer` and `InhibitTransfer`.

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

### TransferSwitchSourceType {#sec-transferswitchsourcetype}

`TransferSwitchSourceType` describes one source of an automatic transfer switch: whether it is `Available` and `Acceptable`, and its `Voltage`, `Frequency` and `PhaseRotation`.

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

### ParallelingControllerType {#sec-parallelingcontrollertype}

`ParallelingControllerType` models synchronising and load sharing across a common bus: the `SystemState`, the bus voltage, frequency and power, the synchronising deltas `SynchronizationAngle`, `SlipFrequency`, the voltage and frequency differences, `SyncCheckPermissive` and `DeadBus`, the load-share and capacity values, the breaker states, and the utility import and export. Its Methods are `ConnectToBus` and `DisconnectFromBus`.

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

### GeneratorSystemType {#sec-generatorsystemtype}

`GeneratorSystemType` aggregates a paralleled plant: a mandatory `GeneratorSets` folder of `GeneratorSetType` instances, an optional `ParallelingController`, an optional `TransferSwitches` folder, and the system totals `NumberOfGeneratorSets`, `TotalSystemCapacity`, `TotalSystemLoad` and `RedundancyScheme`.

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
