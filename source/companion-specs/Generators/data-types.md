The DataTypes this specification defines are the enumerations the model is written in and one structure carrying a diagnostic trouble code. The enumerations each provide a member for a value the list does not name, so that a Server can report a value this specification did not foresee.

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

*Table - GeneratorOperatingModeEnum Structure* {#tbl-generatoroperatingmodeenum-structure datatype=GeneratorOperatingModeEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| Off | 0 | Control is off; the set will not start automatically or manually. |
| Manual | 1 | Manual/hand mode; the set runs on operator command. |
| Auto | 2 | Automatic mode; the set starts/stops on remote or utility-failure signals. |
| Test | 3 | Test mode; a commanded test run, optionally with load. |
| Exercise | 4 | Scheduled exercise/self-test run. |
| RemoteStart | 5 | Started by a remote start signal. |
| Maintenance | 6 | Maintenance/service mode; starting is inhibited or restricted. |
| Lockout | 7 | Locked out; starting is blocked until reset. |

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

*Table - FuelTypeEnum Structure* {#tbl-fueltypeenum-structure datatype=FuelTypeEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| Diesel | 0 |  |
| NaturalGas | 1 |  |
| Propane | 2 |  |
| LPG | 3 |  |
| Gasoline | 4 |  |
| BiFuel | 5 |  |
| DualFuel | 6 |  |
| Biodiesel | 7 |  |
| HVO | 8 |  |
| RenewableDiesel | 9 |  |
| Hydrogen | 10 |  |
| Biogas | 11 |  |
| LandfillGas | 12 |  |
| FieldGas | 13 |  |
| Syngas | 14 |  |
| Other | 15 |  |

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

*Table - GeneratorApplicationRatingEnum Structure* {#tbl-generatorapplicationratingenum-structure datatype=GeneratorApplicationRatingEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| EmergencyStandby | 0 | ESP: standby power at variable load, limited hours, no overload. |
| Prime | 1 | PRP: unlimited hours at variable load, typically 10% overload 1h/12h. |
| Continuous | 2 | COP: unlimited hours at constant load, no overload. |
| LimitedTime | 3 | LTP: limited hours per year at defined load. |
| DataCenterContinuous | 4 | DCC: continuous operation for data-center loads. |

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

*Table - ElectricalConnectionEnum Structure* {#tbl-electricalconnectionenum-structure datatype=ElectricalConnectionEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| Unknown | 0 |  |
| Wye | 1 |  |
| WyeSolidlyGrounded | 2 |  |
| WyeResistanceGrounded | 3 |  |
| WyeUngrounded | 4 |  |
| Delta | 5 |  |
| OpenDelta | 6 |  |
| ZigZag | 7 |  |
| SinglePhaseThreeWire | 8 |  |

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

*Table - ExcitationTypeEnum Structure* {#tbl-excitationtypeenum-structure datatype=ExcitationTypeEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| Unknown | 0 |  |
| Shunt | 1 |  |
| PMG | 2 | Permanent Magnet Generator - independent excitation supply. |
| AREP | 3 |  |
| AuxiliaryWinding | 4 |  |
| StaticExciter | 5 |  |

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

*Table - CoolingMethodEnum Structure* {#tbl-coolingmethodenum-structure datatype=CoolingMethodEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| AirCooled | 0 |  |
| LiquidCooled | 1 |  |

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

*Table - AspirationEnum Structure* {#tbl-aspirationenum-structure datatype=AspirationEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| NaturallyAspirated | 0 |  |
| Turbocharged | 1 |  |
| TurbochargedAftercooled | 2 |  |

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

*Table - EmissionsStandardEnum Structure* {#tbl-emissionsstandardenum-structure datatype=EmissionsStandardEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| Unregulated | 0 |  |
| EPATier1 | 1 |  |
| EPATier2 | 2 |  |
| EPATier3 | 3 |  |
| EPATier4Interim | 4 |  |
| EPATier4Final | 5 |  |
| EUStageIII | 6 |  |
| EUStageIV | 7 |  |
| EUStageV | 8 |  |
| Other | 9 |  |

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

*Table - CanBusStateEnum Structure* {#tbl-canbusstateenum-structure datatype=CanBusStateEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| Offline | 0 |  |
| Online | 1 |  |
| ErrorWarning | 2 |  |
| ErrorPassive | 3 |  |
| BusOff | 4 |  |

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

*Table - TransferSwitchPositionEnum Structure* {#tbl-transferswitchpositionenum-structure datatype=TransferSwitchPositionEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| Unknown | 0 |  |
| Source1 | 1 | Connected to Source 1 (normal/utility). |
| Source2 | 2 | Connected to Source 2 (emergency/generator). |
| Neutral | 3 | Center-off / neutral position. |
| InTransition | 4 |  |
| BypassSource1 | 5 |  |
| BypassSource2 | 6 |  |
| Isolated | 7 |  |

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

*Table - TransferTransitionTypeEnum Structure* {#tbl-transfertransitiontypeenum-structure datatype=TransferTransitionTypeEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| OpenTransition | 0 | Break-before-make. |
| DelayedTransition | 1 | Break-before-make with center-off delay. |
| ClosedTransition | 2 | Make-before-break; momentary paralleling. |
| SoftLoadTransition | 3 | Ramped, no-break transfer while paralleled. |
| BypassIsolation | 4 |  |

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

*Table - AtsOperatingStateEnum Structure* {#tbl-atsoperatingstateenum-structure datatype=AtsOperatingStateEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| Unknown | 0 |  |
| NormalAvailable | 1 |  |
| EmergencyAvailable | 2 |  |
| NormalConnected | 3 |  |
| EmergencyConnected | 4 |  |
| TransferPending | 5 |  |
| Transferring | 6 |  |
| RetransferPending | 7 |  |
| Exercising | 8 |  |
| Test | 9 |  |
| Faulted | 10 |  |
| Bypassed | 11 |  |
| Isolated | 12 |  |

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

*Table - AlarmSeverityEnum Structure* {#tbl-alarmseverityenum-structure datatype=AlarmSeverityEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| Info | 0 |  |
| Warning | 1 |  |
| Derate | 2 | The set continues to run at reduced output. |
| Shutdown | 3 | The engine is shut down. |
| ElectricalTrip | 4 | The generator breaker is tripped. |
| Lockout | 5 | The set is locked out and requires manual reset. |
| EmergencyStop | 6 |  |

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

*Table - GeneratorProtectionFunctionEnum Structure* {#tbl-generatorprotectionfunctionenum-structure datatype=GeneratorProtectionFunctionEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| Other | 0 |  |
| LowOilPressure | 1 |  |
| HighOilTemperature | 2 |  |
| HighCoolantTemperature | 3 |  |
| LowCoolantTemperature | 4 |  |
| LowCoolantLevel | 5 |  |
| HighCoolantPressure | 6 |  |
| Overspeed | 7 |  |
| Underspeed | 8 |  |
| Overcrank | 9 | Fail to start within the crank limit. |
| FailToCrank | 10 |  |
| StarterFailure | 11 |  |
| LowFuelLevel | 12 |  |
| CriticalLowFuel | 13 |  |
| FuelLeak | 14 |  |
| LowFuelPressure | 15 |  |
| HighFuelPressure | 16 |  |
| WaterInFuel | 17 |  |
| FuelFilterRestriction | 18 |  |
| AirFilterRestriction | 19 |  |
| HighExhaustTemperature | 20 |  |
| TurbochargerFault | 21 |  |
| EcuFault | 22 |  |
| EngineDerate | 23 |  |
| Overvoltage | 24 |  |
| Undervoltage | 25 |  |
| Overfrequency | 26 |  |
| Underfrequency | 27 |  |
| Overload | 28 |  |
| Overcurrent | 29 |  |
| ShortCircuit | 30 |  |
| GroundFault | 31 |  |
| PhaseLoss | 32 |  |
| PhaseReversal | 33 |  |
| VoltageImbalance | 34 |  |
| CurrentImbalance | 35 |  |
| ReversePower | 36 |  |
| LossOfExcitation | 37 |  |
| Overexcitation | 38 |  |
| Underexcitation | 39 |  |
| AvrFault | 40 |  |
| HighWindingTemperature | 41 |  |
| HighBearingTemperature | 42 |  |
| LowBatteryVoltage | 43 |  |
| HighBatteryVoltage | 44 |  |
| BatteryChargerFailure | 45 |  |
| WeakBattery | 46 |  |
| ControllerFault | 47 |  |
| CommunicationLost | 48 |  |
| SensorFailure | 49 |  |
| EmergencyStop | 50 |  |
| DefLevelLow | 51 |  |
| DefQualityPoor | 52 |  |
| DpfSootHigh | 53 |  |
| RegenerationRequired | 54 |  |
| AftertreatmentFault | 55 |  |
| EnclosureHighTemperature | 56 |  |
| DoorOpen | 57 |  |
| FuelBasinLeak | 58 |  |
| RadiatorFanFailure | 59 |  |
| JacketWaterHeaterFailure | 60 |  |
| AtsFailedToTransfer | 61 |  |
| BreakerFailedToClose | 62 |  |
| SynchronizationFailure | 63 |  |

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

*Table - ParallelingSystemStateEnum Structure* {#tbl-parallelingsystemstateenum-structure datatype=ParallelingSystemStateEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| Off | 0 |  |
| Standby | 1 |  |
| StartSequence | 2 |  |
| DeadBusClose | 3 |  |
| Synchronizing | 4 |  |
| Paralleling | 5 |  |
| LoadSharing | 6 |  |
| LoadDemand | 7 |  |
| UtilityParallel | 8 |  |
| PeakShaving | 9 |  |
| BaseLoad | 10 |  |
| LoadShed | 11 |  |
| SoftUnload | 12 |  |
| Cooldown | 13 |  |
| Faulted | 14 |  |
| EmergencyStop | 15 |  |
| MaintenanceBypass | 16 |  |

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

*Table - AftertreatmentStateEnum Structure* {#tbl-aftertreatmentstateenum-structure datatype=AftertreatmentStateEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| NotEquipped | 0 |  |
| Normal | 1 |  |
| PassiveRegen | 2 |  |
| ActiveRegen | 3 |  |
| RegenInhibited | 4 |  |
| RegenRequired | 5 |  |
| DerateActive | 6 |  |
| Faulted | 7 |  |

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

*Table - J1939LampStatusEnum Structure* {#tbl-j1939lampstatusenum-structure datatype=J1939LampStatusEnum}

| **Name** | **Value** | **Description** |
| --- | --- | --- |
| Off | 0 | The lamp is off. |
| On | 1 | The lamp is on (steady). |
| SlowFlash | 2 | The lamp is flashing slowly. |
| FastFlash | 3 | The lamp is flashing fast. |
| NotAvailable | 4 | The lamp status is not available. |

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

*Table - DiagnosticTroubleCodeType Structure* {#tbl-diagnostictroublecodetype-structure datatype=DiagnosticTroubleCodeType}

| **Name** | **Type** | **Description** |
| --- | --- | --- |
| DiagnosticTroubleCodeType | 0:Structure | Subtype of the 0:Structure defined in OPC 10000-3 |
|   Spn | 0:UInt32 | Suspect Parameter Number identifying the faulty subsystem. |
|   Fmi | 0:Byte | Failure Mode Identifier describing the type of failure. |
|   OccurrenceCount | 0:Byte | Number of times the fault has become active. |
|   ConversionMethod | 0:Boolean | J1939 SPN conversion method flag. |
|   Active | 0:Boolean | TRUE while the fault is currently active (DM1). |
|   SourceAddress | 0:Byte | J1939 source address of the ECU that reported the code. |
|   SourceName | 0:String | Name of the ECU/controller that reported the code. |
|   Severity | 1:AlarmSeverityEnum | Severity classification of the fault. |
|   Description | 0:String | Human-readable description of the fault. |
