## Type overview

| NodeId | BrowseName | NodeClass | Subtype of |
|---|---|---|---|
| ns=1;i=1016 | GeneratorIdentificationType | ObjectType | MachineIdentificationType [Machinery] |
| ns=1;i=1011 | GeneratorStateMachineType | ObjectType | FiniteStateMachineType |
| ns=1;i=1010 | J1939DiagnosticInterfaceType | ObjectType | BaseObjectType |
| ns=1;i=1018 | ExhaustAftertreatmentType | ObjectType | ComponentType [DI] |
| ns=1;i=1002 | EngineType | ObjectType | ComponentType [DI] |
| ns=1;i=1004 | AlternatorPhaseType | ObjectType | BaseObjectType |
| ns=1;i=1003 | AlternatorType | ObjectType | ComponentType [DI] |
| ns=1;i=1005 | FuelSystemType | ObjectType | ComponentType [DI] |
| ns=1;i=1006 | CoolingSystemType | ObjectType | ComponentType [DI] |
| ns=1;i=1007 | LubricationSystemType | ObjectType | ComponentType [DI] |
| ns=1;i=1008 | StartingSystemType | ObjectType | ComponentType [DI] |
| ns=1;i=1009 | GeneratorControllerType | ObjectType | ComponentType [DI] |
| ns=1;i=1012 | GeneratorRatingType | ObjectType | BaseObjectType |
| ns=1;i=1017 | GeneratorProtectionAlarmType | ObjectType | OffNormalAlarmType |
| ns=1;i=1001 | GeneratorSetType | ObjectType | DeviceType [DI] |
| ns=1;i=1019 | TransferSwitchSourceType | ObjectType | BaseObjectType |
| ns=1;i=1013 | AutomaticTransferSwitchType | ObjectType | DeviceType [DI] |
| ns=1;i=1014 | ParallelingControllerType | ObjectType | ComponentType [DI] |
| ns=1;i=1015 | GeneratorSystemType | ObjectType | BaseObjectType |
| ns=1;i=3001 | GeneratorOperatingModeEnum | DataType | Enumeration |
| ns=1;i=3002 | FuelTypeEnum | DataType | Enumeration |
| ns=1;i=3003 | GeneratorApplicationRatingEnum | DataType | Enumeration |
| ns=1;i=3004 | ElectricalConnectionEnum | DataType | Enumeration |
| ns=1;i=3005 | ExcitationTypeEnum | DataType | Enumeration |
| ns=1;i=3006 | CoolingMethodEnum | DataType | Enumeration |
| ns=1;i=3007 | AspirationEnum | DataType | Enumeration |
| ns=1;i=3008 | EmissionsStandardEnum | DataType | Enumeration |
| ns=1;i=3009 | CanBusStateEnum | DataType | Enumeration |
| ns=1;i=3010 | TransferSwitchPositionEnum | DataType | Enumeration |
| ns=1;i=3011 | TransferTransitionTypeEnum | DataType | Enumeration |
| ns=1;i=3012 | AtsOperatingStateEnum | DataType | Enumeration |
| ns=1;i=3013 | AlarmSeverityEnum | DataType | Enumeration |
| ns=1;i=3014 | GeneratorProtectionFunctionEnum | DataType | Enumeration |
| ns=1;i=3015 | ParallelingSystemStateEnum | DataType | Enumeration |
| ns=1;i=3016 | AftertreatmentStateEnum | DataType | Enumeration |
| ns=1;i=3017 | J1939LampStatusEnum | DataType | Enumeration |
| ns=1;i=3050 | DiagnosticTroubleCodeType | DataType | Structure |

## ObjectTypes

### GeneratorIdentificationType  (ns=1;i=1016)

Identification and nameplate of a generator set. Extends the Machinery MachineIdentificationType with generator-specific nameplate data.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| SpecificationNumber | Variable | String | PropertyType | Optional | Manufacturer build/specification code (e.g. Cummins spec number). |
| ProductFamily | Variable | String | PropertyType | Optional | Product family or series (e.g. QuietConnect, C-Series, QSK, QSV). |
| EngineModel | Variable | String | PropertyType | Optional | Model designation of the prime-mover engine. |
| EngineSerialNumber | Variable | String | PropertyType | Optional | Serial number of the prime-mover engine. |
| AlternatorModel | Variable | String | PropertyType | Optional | Model designation of the alternator. |
| AlternatorSerialNumber | Variable | String | PropertyType | Optional | Serial number of the alternator. |
| ControllerModel | Variable | String | PropertyType | Optional | Model of the control panel (e.g. PCC1301, PCC2300, PCC3300). |
| FuelType | Variable | FuelTypeEnum | PropertyType | Optional | Primary fuel of the set. |
| EmissionsStandard | Variable | EmissionsStandardEnum | PropertyType | Optional | Emissions certification standard. |
| RatedRealPower | Variable | Double | AnalogUnitType | Optional | Nameplate rated real power. EngineeringUnits: kW. |
| RatedApparentPower | Variable | Double | AnalogUnitType | Optional | Nameplate rated apparent power. EngineeringUnits: kVA. |
| RatedVoltage | Variable | Double | AnalogUnitType | Optional | Nameplate rated line-to-line voltage. EngineeringUnits: V. |
| RatedFrequency | Variable | Double | AnalogUnitType | Optional | Nameplate rated frequency. EngineeringUnits: Hz. |
| SoundRatingAt7m | Variable | Double | PropertyType | Optional | Sound pressure level at 7 m (23 ft) in dB(A). |

### GeneratorStateMachineType  (ns=1;i=1011)

Finite state machine describing the operating state of a generator set: Off, Ready, Starting, Warmup, Running, Loaded, Synchronizing, Paralleled, Cooldown, Stopping, Fault and EmergencyStopped.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| Off | Object |  | InitialStateType |  | State 'Off' of the generator set operating state machine. |
| Ready | Object |  | StateType |  | State 'Ready' of the generator set operating state machine. |
| Starting | Object |  | StateType |  | State 'Starting' of the generator set operating state machine. |
| Warmup | Object |  | StateType |  | State 'Warmup' of the generator set operating state machine. |
| Running | Object |  | StateType |  | State 'Running' of the generator set operating state machine. |
| Loaded | Object |  | StateType |  | State 'Loaded' of the generator set operating state machine. |
| Synchronizing | Object |  | StateType |  | State 'Synchronizing' of the generator set operating state machine. |
| Paralleled | Object |  | StateType |  | State 'Paralleled' of the generator set operating state machine. |
| Cooldown | Object |  | StateType |  | State 'Cooldown' of the generator set operating state machine. |
| Stopping | Object |  | StateType |  | State 'Stopping' of the generator set operating state machine. |
| Fault | Object |  | StateType |  | State 'Fault' of the generator set operating state machine. |
| EmergencyStopped | Object |  | StateType |  | State 'EmergencyStopped' of the generator set operating state machine. |
| OffToReady | Object |  | TransitionType |  | Transition 'OffToReady'. |
| ReadyToStarting | Object |  | TransitionType |  | Transition 'ReadyToStarting'. |
| ReadyToOff | Object |  | TransitionType |  | Transition 'ReadyToOff'. |
| StartingToWarmup | Object |  | TransitionType |  | Transition 'StartingToWarmup'. |
| StartingToFault | Object |  | TransitionType |  | Transition 'StartingToFault'. |
| WarmupToRunning | Object |  | TransitionType |  | Transition 'WarmupToRunning'. |
| RunningToLoaded | Object |  | TransitionType |  | Transition 'RunningToLoaded'. |
| RunningToSynchronizing | Object |  | TransitionType |  | Transition 'RunningToSynchronizing'. |
| SynchronizingToParalleled | Object |  | TransitionType |  | Transition 'SynchronizingToParalleled'. |
| SynchronizingToRunning | Object |  | TransitionType |  | Transition 'SynchronizingToRunning'. |
| ParalleledToLoaded | Object |  | TransitionType |  | Transition 'ParalleledToLoaded'. |
| LoadedToCooldown | Object |  | TransitionType |  | Transition 'LoadedToCooldown'. |
| RunningToCooldown | Object |  | TransitionType |  | Transition 'RunningToCooldown'. |
| CooldownToStopping | Object |  | TransitionType |  | Transition 'CooldownToStopping'. |
| StoppingToOff | Object |  | TransitionType |  | Transition 'StoppingToOff'. |
| RunningToFault | Object |  | TransitionType |  | Transition 'RunningToFault'. |
| LoadedToFault | Object |  | TransitionType |  | Transition 'LoadedToFault'. |
| ParalleledToFault | Object |  | TransitionType |  | Transition 'ParalleledToFault'. |
| FaultToOff | Object |  | TransitionType |  | Transition 'FaultToOff'. |
| RunningToEmergencyStopped | Object |  | TransitionType |  | Transition 'RunningToEmergencyStopped'. |
| LoadedToEmergencyStopped | Object |  | TransitionType |  | Transition 'LoadedToEmergencyStopped'. |
| ParalleledToEmergencyStopped | Object |  | TransitionType |  | Transition 'ParalleledToEmergencyStopped'. |
| EmergencyStoppedToOff | Object |  | TransitionType |  | Transition 'EmergencyStoppedToOff'. |

### J1939DiagnosticInterfaceType  (ns=1;i=1010)

The engine CAN bus / SAE J1939 diagnostic interface. Surfaces the network connection parameters, J1939 lamp status and active/previously-active diagnostic trouble codes reported by the engine ECU.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| ProtocolName | Variable | String | PropertyType | Mandatory | Name of the diagnostic protocol, e.g. 'SAE J1939'. |
| NetworkName | Variable | String | PropertyType | Optional | Name/identifier of the CAN network (e.g. CAN0). |
| SourceAddress | Variable | Byte | PropertyType | Optional | J1939 source address of the engine ECU. |
| Baudrate | Variable | UInt32 | PropertyType | Optional | CAN bit rate in bit/s (typically 250000 or 500000). |
| BusState | Variable | CanBusStateEnum | BaseDataVariableType | Optional | State of the CAN bus interface. |
| AmberWarningLamp | Variable | J1939LampStatusEnum | BaseDataVariableType | Optional | J1939 DM1 amber warning lamp status. |
| RedStopLamp | Variable | J1939LampStatusEnum | BaseDataVariableType | Optional | J1939 DM1 red stop lamp status. |
| MalfunctionIndicatorLamp | Variable | J1939LampStatusEnum | BaseDataVariableType | Optional | J1939 DM1 malfunction indicator lamp status. |
| ProtectLamp | Variable | J1939LampStatusEnum | BaseDataVariableType | Optional | J1939 DM1 protect lamp status. |
| ActiveDiagnosticTroubleCodes | Variable | DiagnosticTroubleCodeType[] | BaseDataVariableType | Optional | Currently active DTCs (J1939 DM1). |
| PreviouslyActiveDiagnosticTroubleCodes | Variable | DiagnosticTroubleCodeType[] | BaseDataVariableType | Optional | Previously active DTCs (J1939 DM2). |
| ClearPreviouslyActiveDtcs | Method |  |  | Optional | Clear previously active diagnostic trouble codes (J1939 DM3/DM11). |

### ExhaustAftertreatmentType  (ns=1;i=1018)

Exhaust aftertreatment subsystem (DPF/SCR/DEF) for Tier 4 / Stage V engines.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| AftertreatmentState | Variable | AftertreatmentStateEnum | BaseDataVariableType | Optional | State of the aftertreatment system. |
| DefLevel | Variable | Double | AnalogUnitType | Optional | Diesel Exhaust Fluid tank level. SAE J1939 SPN 1761. EngineeringUnits: %. |
| DefTemperature | Variable | Double | AnalogUnitType | Optional | DEF tank temperature. SAE J1939 SPN 3031. EngineeringUnits: degC. |
| DefQuality | Variable | Double | AnalogUnitType | Optional | DEF concentration/quality. SAE J1939 SPN 3364. EngineeringUnits: %. |
| DpfSootLoad | Variable | Double | AnalogUnitType | Optional | Diesel particulate filter soot load. SAE J1939 SPN 3719. EngineeringUnits: %. |
| DpfAshLoad | Variable | Double | AnalogUnitType | Optional | Diesel particulate filter ash load. SAE J1939 SPN 3720. EngineeringUnits: %. |
| ExhaustGasTemperature | Variable | Double | AnalogUnitType | Optional | Exhaust gas temperature. SAE J1939 SPN 173. EngineeringUnits: degC. |
| RegenerationRequired | Variable | Boolean | BaseDataVariableType | Optional | A DPF regeneration is required. |
| RegenerationInhibited | Variable | Boolean | BaseDataVariableType | Optional | DPF regeneration is currently inhibited. |
| InitiateRegeneration | Method |  |  | Optional | Request a manual DPF regeneration. |
| InhibitRegeneration | Method |  |  | Optional | Enable or disable the inhibit of automatic regeneration. |

### EngineType  (ns=1;i=1002)

The prime-mover engine of a generator set. Exposes engine telemetry, typically obtained over the CAN bus / SAE J1939 interface, and identification.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| Speed | Variable | Double | AnalogUnitType | Mandatory | Engine speed. SAE J1939 SPN 190. EngineeringUnits: rpm. |
| PercentLoad | Variable | Double | AnalogUnitType | Optional | Engine percent load at current speed. SAE J1939 SPN 92. EngineeringUnits: %. |
| PercentTorque | Variable | Double | AnalogUnitType | Optional | Actual engine percent torque. SAE J1939 SPN 513. EngineeringUnits: %. |
| OilPressure | Variable | Double | AnalogUnitType | Optional | Engine oil pressure. SAE J1939 SPN 100. EngineeringUnits: kPa. |
| OilTemperature | Variable | Double | AnalogUnitType | Optional | Engine oil temperature. SAE J1939 SPN 175. EngineeringUnits: degC. |
| CoolantTemperature | Variable | Double | AnalogUnitType | Optional | Engine coolant temperature. SAE J1939 SPN 110. EngineeringUnits: degC. |
| CoolantPressure | Variable | Double | AnalogUnitType | Optional | Engine coolant pressure. SAE J1939 SPN 109. EngineeringUnits: kPa. |
| FuelRate | Variable | Double | AnalogUnitType | Optional | Engine fuel consumption rate. SAE J1939 SPN 183. EngineeringUnits: L/h. |
| FuelTemperature | Variable | Double | AnalogUnitType | Optional | Engine fuel temperature. SAE J1939 SPN 174. EngineeringUnits: degC. |
| IntakeManifoldPressure | Variable | Double | AnalogUnitType | Optional | Intake manifold (boost) pressure. SAE J1939 SPN 102. EngineeringUnits: kPa. |
| IntakeManifoldTemperature | Variable | Double | AnalogUnitType | Optional | Intake manifold temperature. SAE J1939 SPN 105. EngineeringUnits: degC. |
| ExhaustGasTemperature | Variable | Double | AnalogUnitType | Optional | Exhaust gas temperature. SAE J1939 SPN 173. EngineeringUnits: degC. |
| BarometricPressure | Variable | Double | AnalogUnitType | Optional | Ambient barometric pressure. SAE J1939 SPN 108. EngineeringUnits: kPa. |
| EngineHours | Variable | Double | AnalogUnitType | Mandatory | Total engine run hours. SAE J1939 SPN 247. EngineeringUnits: h. |
| NumberOfStarts | Variable | UInt32 | BaseDataVariableType | Optional | Total number of engine start attempts. |
| Aspiration | Variable | AspirationEnum | BaseDataVariableType | Optional | Air induction method of the engine. |
| Displacement | Variable | Double | AnalogUnitType | Optional | Engine displacement. EngineeringUnits: l. |
| CylinderCount | Variable | UInt16 | BaseDataVariableType | Optional | Number of cylinders. |
| RatedSpeed | Variable | Double | AnalogUnitType | Optional | Rated (synchronous) engine speed, e.g. 1500 or 1800 rpm. EngineeringUnits: rpm. |
| CanInterface | Object |  | J1939DiagnosticInterfaceType | Optional | CAN bus / SAE J1939 diagnostic interface of the engine ECU. |
| Aftertreatment | Object |  | ExhaustAftertreatmentType | Optional | Exhaust aftertreatment subsystem, when equipped. |

### AlternatorPhaseType  (ns=1;i=1004)

Per-phase electrical measurements of the alternator output.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| LineToNeutralVoltage | Variable | Double | AnalogUnitType | Optional | Phase (line-to-neutral) RMS voltage. EngineeringUnits: V. |
| LineToLineVoltage | Variable | Double | AnalogUnitType | Optional | Line-to-line RMS voltage referenced to the next phase. EngineeringUnits: V. |
| Current | Variable | Double | AnalogUnitType | Mandatory | Phase RMS current. EngineeringUnits: A. |
| RealPower | Variable | Double | AnalogUnitType | Optional | Per-phase real power. EngineeringUnits: kW. |
| ReactivePower | Variable | Double | AnalogUnitType | Optional | Per-phase reactive power. EngineeringUnits: kvar. |
| ApparentPower | Variable | Double | AnalogUnitType | Optional | Per-phase apparent power. EngineeringUnits: kVA. |
| PowerFactor | Variable | Double | BaseDataVariableType | Optional | Per-phase power factor (-1..1). |

### AlternatorType  (ns=1;i=1003)

The alternator (generator end) that converts mechanical power into AC electrical power. Exposes aggregate and per-phase electrical measurements.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| Frequency | Variable | Double | AnalogUnitType | Mandatory | Output frequency. EngineeringUnits: Hz. |
| AverageLineToLineVoltage | Variable | Double | AnalogUnitType | Optional | Average line-to-line RMS voltage. EngineeringUnits: V. |
| AverageLineToNeutralVoltage | Variable | Double | AnalogUnitType | Optional | Average line-to-neutral RMS voltage. EngineeringUnits: V. |
| AverageCurrent | Variable | Double | AnalogUnitType | Optional | Average line RMS current. EngineeringUnits: A. |
| TotalRealPower | Variable | Double | AnalogUnitType | Mandatory | Total three-phase real power. EngineeringUnits: kW. |
| TotalReactivePower | Variable | Double | AnalogUnitType | Optional | Total three-phase reactive power. EngineeringUnits: kvar. |
| TotalApparentPower | Variable | Double | AnalogUnitType | Optional | Total three-phase apparent power. EngineeringUnits: kVA. |
| AveragePowerFactor | Variable | Double | BaseDataVariableType | Optional | Average power factor (-1..1). |
| TotalRealEnergy | Variable | Double | AnalogUnitType | Optional | Cumulative generated real energy. EngineeringUnits: kW.h. |
| LoadPercent | Variable | Double | AnalogUnitType | Optional | Output as a percentage of rated power. EngineeringUnits: %. |
| WindingTemperature1 | Variable | Double | AnalogUnitType | Optional | Stator winding temperature, phase 1. EngineeringUnits: degC. |
| WindingTemperature2 | Variable | Double | AnalogUnitType | Optional | Stator winding temperature, phase 2. EngineeringUnits: degC. |
| WindingTemperature3 | Variable | Double | AnalogUnitType | Optional | Stator winding temperature, phase 3. EngineeringUnits: degC. |
| BearingTemperatureDriveEnd | Variable | Double | AnalogUnitType | Optional | Drive-end bearing temperature. EngineeringUnits: degC. |
| BearingTemperatureNonDriveEnd | Variable | Double | AnalogUnitType | Optional | Non-drive-end bearing temperature. EngineeringUnits: degC. |
| Connection | Variable | ElectricalConnectionEnum | BaseDataVariableType | Optional | Winding connection configuration. |
| ExcitationType | Variable | ExcitationTypeEnum | BaseDataVariableType | Optional | Excitation method. |
| NumberOfPoles | Variable | UInt16 | BaseDataVariableType | Optional | Number of alternator poles. |
| VoltageSetpoint | Variable | Double | AnalogUnitType | Optional | AVR voltage setpoint. EngineeringUnits: V. |
| FieldCurrent | Variable | Double | AnalogUnitType | Optional | Excitation field current. EngineeringUnits: A. |
| L1 | Object |  | AlternatorPhaseType | Mandatory | Phase 1 (A) measurements. |
| L2 | Object |  | AlternatorPhaseType | Optional | Phase 2 (B) measurements. |
| L3 | Object |  | AlternatorPhaseType | Optional | Phase 3 (C) measurements. |

### FuelSystemType  (ns=1;i=1005)

The fuel storage and delivery subsystem of a generator set.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| FuelType | Variable | FuelTypeEnum | BaseDataVariableType | Mandatory | Primary fuel of the set. |
| FuelLevel | Variable | Double | AnalogUnitType | Optional | Fuel tank level. EngineeringUnits: %. |
| FuelVolume | Variable | Double | AnalogUnitType | Optional | Usable fuel volume remaining. EngineeringUnits: l. |
| FuelConsumptionRate | Variable | Double | AnalogUnitType | Optional | Fuel consumption rate. EngineeringUnits: L/h. |
| FuelPressure | Variable | Double | AnalogUnitType | Optional | Fuel supply pressure. EngineeringUnits: kPa. |
| FuelTemperature | Variable | Double | AnalogUnitType | Optional | Fuel temperature. EngineeringUnits: degC. |
| GasSupplyPressure | Variable | Double | AnalogUnitType | Optional | Gas inlet pressure for gaseous-fuel sets. EngineeringUnits: kPa. |
| RuntimeRemaining | Variable | Double | AnalogUnitType | Optional | Estimated runtime remaining at current load. EngineeringUnits: h. |
| TotalFuelConsumed | Variable | Double | AnalogUnitType | Optional | Cumulative fuel consumed. EngineeringUnits: l. |
| WaterInFuel | Variable | Boolean | BaseDataVariableType | Optional | Water detected in the fuel/water separator. |

### CoolingSystemType  (ns=1;i=1006)

The engine cooling subsystem of a generator set.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| CoolantTemperature | Variable | Double | AnalogUnitType | Optional | Engine coolant temperature. EngineeringUnits: degC. |
| CoolantLevel | Variable | Double | AnalogUnitType | Optional | Coolant level. SAE J1939 SPN 111. EngineeringUnits: %. |
| CoolantPressure | Variable | Double | AnalogUnitType | Optional | Coolant pressure. EngineeringUnits: kPa. |
| CoolingMethod | Variable | CoolingMethodEnum | BaseDataVariableType | Optional | Cooling method (air- or liquid-cooled). |
| AmbientTemperature | Variable | Double | AnalogUnitType | Optional | Ambient air temperature at the set. EngineeringUnits: degC. |
| RadiatorFanRunning | Variable | Boolean | BaseDataVariableType | Optional | The radiator fan is running. |
| JacketWaterHeaterActive | Variable | Boolean | BaseDataVariableType | Optional | The jacket-water block heater is active. |

### LubricationSystemType  (ns=1;i=1007)

The engine lubrication subsystem of a generator set.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| OilPressure | Variable | Double | AnalogUnitType | Optional | Engine oil pressure. SAE J1939 SPN 100. EngineeringUnits: kPa. |
| OilTemperature | Variable | Double | AnalogUnitType | Optional | Engine oil temperature. SAE J1939 SPN 175. EngineeringUnits: degC. |
| OilLevel | Variable | Double | AnalogUnitType | Optional | Engine oil level. EngineeringUnits: %. |
| OilFilterDifferentialPressure | Variable | Double | AnalogUnitType | Optional | Oil filter differential pressure. EngineeringUnits: kPa. |

### StartingSystemType  (ns=1;i=1008)

The starting/battery subsystem of a generator set.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| BatteryVoltage | Variable | Double | AnalogUnitType | Mandatory | Starting battery voltage. SAE J1939 SPN 168. EngineeringUnits: V. |
| BatteryChargingCurrent | Variable | Double | AnalogUnitType | Optional | Battery charging current. EngineeringUnits: A. |
| BatteryChargerActive | Variable | Boolean | BaseDataVariableType | Optional | The battery charger is active. |
| StartAttempts | Variable | UInt32 | BaseDataVariableType | Optional | Number of start attempts in the last start sequence. |

### GeneratorControllerType  (ns=1;i=1009)

The generator set control panel (e.g. Cummins PowerCommand). Provides controller identity, mode/state visibility and remote-monitoring status.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| ControllerFamily | Variable | String | PropertyType | Optional | Controller family, e.g. 'PowerCommand'. |
| FirmwareVersion | Variable | String | PropertyType | Optional | Controller firmware version. |
| ApplicationSoftwareVersion | Variable | String | PropertyType | Optional | Application software version. |
| ConfigurationVersion | Variable | String | PropertyType | Optional | Configuration/calibration version. |
| InAutoMode | Variable | Boolean | BaseDataVariableType | Optional | The controller is in automatic mode. |
| NotInAuto | Variable | Boolean | BaseDataVariableType | Optional | The controller is NOT in automatic mode (NFPA annunciation). |
| RemoteStartEnabled | Variable | Boolean | BaseDataVariableType | Optional | Remote start is enabled. |
| RemoteControlEnabled | Variable | Boolean | BaseDataVariableType | Optional | Remote control is enabled. |
| CloudConnected | Variable | Boolean | BaseDataVariableType | Optional | Connected to the remote-monitoring cloud. |
| ModbusEnabled | Variable | Boolean | BaseDataVariableType | Optional | The Modbus interface is enabled. |
| SignalStrength | Variable | Double | AnalogUnitType | Optional | Cellular/network signal strength. EngineeringUnits: %. |

### GeneratorRatingType  (ns=1;i=1012)

A single nameplate power rating point of a generator set for a given application/duty (ISO 8528).

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| ApplicationRating | Variable | GeneratorApplicationRatingEnum | BaseDataVariableType | Mandatory | Application/duty of this rating. |
| RatedRealPower | Variable | Double | AnalogUnitType | Mandatory | Rated real power. EngineeringUnits: kW. |
| RatedApparentPower | Variable | Double | AnalogUnitType | Optional | Rated apparent power. EngineeringUnits: kVA. |
| RatedPowerFactor | Variable | Double | BaseDataVariableType | Optional | Rated power factor. |
| RatedVoltage | Variable | Double | AnalogUnitType | Optional | Rated line-to-line voltage. EngineeringUnits: V. |
| RatedCurrent | Variable | Double | AnalogUnitType | Optional | Rated line current. EngineeringUnits: A. |
| RatedFrequency | Variable | Double | AnalogUnitType | Optional | Rated frequency. EngineeringUnits: Hz. |
| RatedSpeed | Variable | Double | AnalogUnitType | Optional | Rated engine speed. EngineeringUnits: rpm. |
| PhaseCount | Variable | Byte | PropertyType | Optional | Number of phases (1 or 3). |
| Connection | Variable | ElectricalConnectionEnum | BaseDataVariableType | Optional | Winding connection for this rating. |
| AmbientTemperature | Variable | Double | AnalogUnitType | Optional | Reference ambient temperature for the rating. EngineeringUnits: degC. |
| Altitude | Variable | Double | AnalogUnitType | Optional | Reference altitude for the rating. EngineeringUnits: m. |

### GeneratorProtectionAlarmType  (ns=1;i=1017)

Alarm raised by a generator protection/shutdown function. Extends OffNormalAlarmType with the protection function, severity and J1939 origin.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| ProtectionFunction | Variable | GeneratorProtectionFunctionEnum | PropertyType | Mandatory | The protection function that raised the alarm. |
| GeneratorAlarmSeverity | Variable | AlarmSeverityEnum | PropertyType | Optional | Severity class of the alarm. |
| IsShutdown | Variable | Boolean | PropertyType | Optional | TRUE if the condition caused an engine shutdown. |
| Spn | Variable | UInt32 | PropertyType | Optional | SAE J1939 SPN when the alarm originates from the engine ECU. |
| Fmi | Variable | Byte | PropertyType | Optional | SAE J1939 FMI when the alarm originates from the engine ECU. |
| SubsystemName | Variable | String | PropertyType | Optional | Name of the originating subsystem. |

### GeneratorSetType  (ns=1;i=1001)

A generator set (GenSet): a complete electrical power generation asset composed of a prime-mover engine, an alternator, a fuel system, cooling, lubrication, starting and control subsystems. Applicable to the whole industry, from small home-standby units to house-sized multi-megawatt industrial sets.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| Identification | Object |  | GeneratorIdentificationType | Mandatory | Generator identification and nameplate (Machinery building block). |
| MachineryBuildingBlocks | Object |  | FolderType | Optional | Container for standardized Machinery building blocks. |
| OperatingState | Object |  | GeneratorStateMachineType | Mandatory | Detailed generator-set operating state machine. |
| OperatingMode | Variable | GeneratorOperatingModeEnum | BaseDataVariableType | Mandatory | Selector mode of the control panel (Off/Manual/Auto/Test/...). |
| EmissionsStandard | Variable | EmissionsStandardEnum | BaseDataVariableType | Optional | Emissions certification standard of the set. |
| Application | Variable | String | PropertyType | Optional | Application segment, e.g. Residential, DataCenter, Healthcare, Rental, PrimePower. |
| GeneratorBreakerClosed | Variable | Boolean | BaseDataVariableType | Optional | The generator (output) breaker is closed. |
| GeneratorBreakerAvailable | Variable | Boolean | BaseDataVariableType | Optional | The generator breaker is available to close. |
| RemoteStartInput | Variable | Boolean | BaseDataVariableType | Optional | The remote start input is asserted. |
| RunRequest | Variable | Boolean | BaseDataVariableType | Optional | A run request is active from any source. |
| LoadInhibit | Variable | Boolean | BaseDataVariableType | Optional | Loading of the set is inhibited. |
| AvailableToLoad | Variable | Boolean | BaseDataVariableType | Optional | The set is up to speed and voltage and is ready to accept load. |
| Engine | Object |  | EngineType | Mandatory | The prime-mover engine. |
| Alternator | Object |  | AlternatorType | Mandatory | The alternator (generator end). |
| Controller | Object |  | GeneratorControllerType | Mandatory | The control panel. |
| FuelSystem | Object |  | FuelSystemType | Optional | The fuel subsystem. |
| CoolingSystem | Object |  | CoolingSystemType | Optional | The cooling subsystem. |
| LubricationSystem | Object |  | LubricationSystemType | Optional | The lubrication subsystem. |
| StartingSystem | Object |  | StartingSystemType | Optional | The starting/battery subsystem. |
| Ratings | Object |  | FolderType | Mandatory | Nameplate power ratings of the set (e.g. Standby and Prime). |
| Start | Method |  |  | Optional | Command the set to start in the current operating mode. |
| Stop | Method |  |  | Optional | Command a normal stop (with cooldown). |
| EmergencyStop | Method |  |  | Optional | Command an immediate emergency stop. |
| ResetFaults | Method |  |  | Optional | Reset latched faults / lockout. |
| SetOperatingMode | Method |  |  | Optional | Set the control-panel selector mode. |
| StartTest | Method |  |  | Optional | Start a test run for a given duration. |

### TransferSwitchSourceType  (ns=1;i=1019)

One power source (normal/utility or emergency/generator) of an automatic transfer switch, with its availability and measurements.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| Available | Variable | Boolean | BaseDataVariableType | Mandatory | The source is present and energized. |
| Acceptable | Variable | Boolean | BaseDataVariableType | Optional | The source is within acceptable voltage/frequency limits. |
| Voltage | Variable | Double | AnalogUnitType | Optional | Source line-to-line voltage. EngineeringUnits: V. |
| Frequency | Variable | Double | AnalogUnitType | Optional | Source frequency. EngineeringUnits: Hz. |
| PhaseRotation | Variable | String | PropertyType | Optional | Phase rotation of the source (e.g. ABC or CBA). |

### AutomaticTransferSwitchType  (ns=1;i=1013)

An automatic transfer switch (ATS) that transfers a load between a normal source (utility) and an emergency source (generator).

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| Identification | Object |  | MachineIdentificationType [Machinery] | Optional | ATS identification and nameplate. |
| Position | Variable | TransferSwitchPositionEnum | BaseDataVariableType | Mandatory | Contact position of the switch. |
| OperatingState | Variable | AtsOperatingStateEnum | BaseDataVariableType | Optional | Operating state of the switch. |
| TransitionType | Variable | TransferTransitionTypeEnum | BaseDataVariableType | Optional | Transition method of the switch. |
| Source1 | Object |  | TransferSwitchSourceType | Mandatory | Source 1 (normal/utility). |
| Source2 | Object |  | TransferSwitchSourceType | Mandatory | Source 2 (emergency/generator). |
| PreferredSource | Variable | Byte | PropertyType | Optional | The preferred source (1 = normal, 2 = emergency). |
| Source1Connected | Variable | Boolean | BaseDataVariableType | Optional | The load is connected to Source 1. |
| Source2Connected | Variable | Boolean | BaseDataVariableType | Optional | The load is connected to Source 2. |
| TransferInhibited | Variable | Boolean | BaseDataVariableType | Optional | Transfer is currently inhibited. |
| TransferInhibitReason | Variable | String | PropertyType | Optional | Reason transfer is inhibited, if any. |
| RatedCurrent | Variable | Double | AnalogUnitType | Optional | Rated current of the switch. EngineeringUnits: A. |
| PoleCount | Variable | Byte | PropertyType | Optional | Number of poles. |
| ServiceEntranceRated | Variable | Boolean | BaseDataVariableType | Optional | The switch is service-entrance rated. |
| LoadCurrent | Variable | Double | AnalogUnitType | Optional | Load current through the switch. EngineeringUnits: A. |
| TransferCount | Variable | UInt32 | BaseDataVariableType | Optional | Cumulative number of transfers. |
| LastTransferTime | Variable | DateTime | BaseDataVariableType | Optional | Timestamp of the last transfer. |
| EngineStartDelay | Variable | Duration | BaseDataVariableType | Optional | Engine-start (outage confirmation) delay. |
| TransferToEmergencyDelay | Variable | Duration | BaseDataVariableType | Optional | Delay before transferring to emergency. |
| RetransferToNormalDelay | Variable | Duration | BaseDataVariableType | Optional | Delay before retransferring to normal. |
| CooldownDelay | Variable | Duration | BaseDataVariableType | Optional | Engine cooldown (unloaded run) delay. |
| Transfer | Method |  |  | Optional | Command a transfer to the emergency source. |
| Retransfer | Method |  |  | Optional | Command a retransfer to the normal source. |
| InhibitTransfer | Method |  |  | Optional | Enable or disable the transfer inhibit. |

### ParallelingControllerType  (ns=1;i=1014)

A paralleling / switchgear controller that synchronizes and shares load among generator sets on a common bus, and optionally parallels with the utility.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| SystemState | Variable | ParallelingSystemStateEnum | BaseDataVariableType | Mandatory | Operating state of the paralleling system. |
| BusVoltage | Variable | Double | AnalogUnitType | Optional | Common bus voltage. EngineeringUnits: V. |
| BusFrequency | Variable | Double | AnalogUnitType | Optional | Common bus frequency. EngineeringUnits: Hz. |
| TotalBusRealPower | Variable | Double | AnalogUnitType | Optional | Total real power on the bus. EngineeringUnits: kW. |
| TotalBusReactivePower | Variable | Double | AnalogUnitType | Optional | Total reactive power on the bus. EngineeringUnits: kvar. |
| SynchronizationAngle | Variable | Double | AnalogUnitType | Optional | Phase angle difference during synchronizing. EngineeringUnits: deg. |
| SlipFrequency | Variable | Double | AnalogUnitType | Optional | Slip frequency during synchronizing. EngineeringUnits: Hz. |
| VoltageDifference | Variable | Double | AnalogUnitType | Optional | Voltage difference during synchronizing. EngineeringUnits: V. |
| FrequencyDifference | Variable | Double | AnalogUnitType | Optional | Frequency difference during synchronizing. EngineeringUnits: Hz. |
| SyncCheckPermissive | Variable | Boolean | BaseDataVariableType | Optional | Synchronism-check permissive to close. |
| DeadBus | Variable | Boolean | BaseDataVariableType | Optional | The bus is dead (de-energized). |
| LoadSharePercent | Variable | Double | AnalogUnitType | Optional | This set's share of the total bus load. EngineeringUnits: %. |
| AvailableCapacity | Variable | Double | AnalogUnitType | Optional | Available spare capacity on the bus. EngineeringUnits: kW. |
| SpinningReserve | Variable | Double | AnalogUnitType | Optional | Spinning reserve on the bus. EngineeringUnits: kW. |
| GeneratorBreakerClosed | Variable | Boolean | BaseDataVariableType | Optional | The generator breaker is closed. |
| UtilityBreakerClosed | Variable | Boolean | BaseDataVariableType | Optional | The utility breaker is closed. |
| UtilityImportPower | Variable | Double | AnalogUnitType | Optional | Power imported from the utility. EngineeringUnits: kW. |
| UtilityExportPower | Variable | Double | AnalogUnitType | Optional | Power exported to the utility. EngineeringUnits: kW. |
| ConnectToBus | Method |  |  | Optional | Synchronize and close onto the common bus. |
| DisconnectFromBus | Method |  |  | Optional | Soft-unload and open from the common bus. |

### GeneratorSystemType  (ns=1;i=1015)

A power-generation system aggregating one or more paralleled generator sets, an optional paralleling controller and transfer switches. Models integrated power systems such as data-center and healthcare plants.

| BrowseName | NodeClass | DataType | TypeDefinition | ModellingRule | Description |
|---|---|---|---|---|---|
| GeneratorSets | Object |  | FolderType | Mandatory | The generator sets that make up the system. |
| ParallelingController | Object |  | ParallelingControllerType | Optional | The paralleling/switchgear controller of the system. |
| TransferSwitches | Object |  | FolderType | Optional | The transfer switches in the system. |
| NumberOfGeneratorSets | Variable | UInt16 | BaseDataVariableType | Optional | Number of generator sets in the system. |
| TotalSystemCapacity | Variable | Double | AnalogUnitType | Optional | Total installed capacity of the system. EngineeringUnits: kW. |
| TotalSystemLoad | Variable | Double | AnalogUnitType | Optional | Total load currently served by the system. EngineeringUnits: kW. |
| RedundancyScheme | Variable | String | PropertyType | Optional | Redundancy scheme, e.g. N, N+1, N+2, 2N, DistributedRedundant. |

## DataTypes

### GeneratorOperatingModeEnum  (ns=1;i=3001)

Selector mode of the generator set control panel (e.g. Cummins PowerCommand).

| Name | Value | Description |
|---|---|---|
| Off | 0 | Control is off; the set will not start automatically or manually. |
| Manual | 1 | Manual/hand mode; the set runs on operator command. |
| Auto | 2 | Automatic mode; the set starts/stops on remote or utility-failure signals. |
| Test | 3 | Test mode; a commanded test run, optionally with load. |
| Exercise | 4 | Scheduled exercise/self-test run. |
| RemoteStart | 5 | Started by a remote start signal. |
| Maintenance | 6 | Maintenance/service mode; starting is inhibited or restricted. |
| Lockout | 7 | Locked out; starting is blocked until reset. |

### FuelTypeEnum  (ns=1;i=3002)

Primary fuel of the generator set.

| Name | Value | Description |
|---|---|---|
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

### GeneratorApplicationRatingEnum  (ns=1;i=3003)

Application/duty rating per ISO 8528 plus the data-center-continuous rating.

| Name | Value | Description |
|---|---|---|
| EmergencyStandby | 0 | ESP: standby power at variable load, limited hours, no overload. |
| Prime | 1 | PRP: unlimited hours at variable load, typically 10% overload 1h/12h. |
| Continuous | 2 | COP: unlimited hours at constant load, no overload. |
| LimitedTime | 3 | LTP: limited hours per year at defined load. |
| DataCenterContinuous | 4 | DCC: continuous operation for data-center loads. |

### ElectricalConnectionEnum  (ns=1;i=3004)

Winding/connection configuration of the alternator output.

| Name | Value | Description |
|---|---|---|
| Unknown | 0 |  |
| Wye | 1 |  |
| WyeSolidlyGrounded | 2 |  |
| WyeResistanceGrounded | 3 |  |
| WyeUngrounded | 4 |  |
| Delta | 5 |  |
| OpenDelta | 6 |  |
| ZigZag | 7 |  |
| SinglePhaseThreeWire | 8 |  |

### ExcitationTypeEnum  (ns=1;i=3005)

Excitation method of the alternator.

| Name | Value | Description |
|---|---|---|
| Unknown | 0 |  |
| Shunt | 1 |  |
| PMG | 2 | Permanent Magnet Generator - independent excitation supply. |
| AREP | 3 |  |
| AuxiliaryWinding | 4 |  |
| StaticExciter | 5 |  |

### CoolingMethodEnum  (ns=1;i=3006)

Primary cooling method of the engine.

| Name | Value | Description |
|---|---|---|
| AirCooled | 0 |  |
| LiquidCooled | 1 |  |

### AspirationEnum  (ns=1;i=3007)

Air induction method of the engine.

| Name | Value | Description |
|---|---|---|
| NaturallyAspirated | 0 |  |
| Turbocharged | 1 |  |
| TurbochargedAftercooled | 2 |  |

### EmissionsStandardEnum  (ns=1;i=3008)

Emissions certification standard of the engine.

| Name | Value | Description |
|---|---|---|
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

### CanBusStateEnum  (ns=1;i=3009)

State of the engine CAN bus / SAE J1939 network interface.

| Name | Value | Description |
|---|---|---|
| Offline | 0 |  |
| Online | 1 |  |
| ErrorWarning | 2 |  |
| ErrorPassive | 3 |  |
| BusOff | 4 |  |

### TransferSwitchPositionEnum  (ns=1;i=3010)

Contact position of an automatic transfer switch.

| Name | Value | Description |
|---|---|---|
| Unknown | 0 |  |
| Source1 | 1 | Connected to Source 1 (normal/utility). |
| Source2 | 2 | Connected to Source 2 (emergency/generator). |
| Neutral | 3 | Center-off / neutral position. |
| InTransition | 4 |  |
| BypassSource1 | 5 |  |
| BypassSource2 | 6 |  |
| Isolated | 7 |  |

### TransferTransitionTypeEnum  (ns=1;i=3011)

Transition method of an automatic transfer switch.

| Name | Value | Description |
|---|---|---|
| OpenTransition | 0 | Break-before-make. |
| DelayedTransition | 1 | Break-before-make with center-off delay. |
| ClosedTransition | 2 | Make-before-break; momentary paralleling. |
| SoftLoadTransition | 3 | Ramped, no-break transfer while paralleled. |
| BypassIsolation | 4 |  |

### AtsOperatingStateEnum  (ns=1;i=3012)

Operating state of an automatic transfer switch.

| Name | Value | Description |
|---|---|---|
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

### AlarmSeverityEnum  (ns=1;i=3013)

Severity class of a generator protection event.

| Name | Value | Description |
|---|---|---|
| Info | 0 |  |
| Warning | 1 |  |
| Derate | 2 | The set continues to run at reduced output. |
| Shutdown | 3 | The engine is shut down. |
| ElectricalTrip | 4 | The generator breaker is tripped. |
| Lockout | 5 | The set is locked out and requires manual reset. |
| EmergencyStop | 6 |  |

### GeneratorProtectionFunctionEnum  (ns=1;i=3014)

Protection / fault function that raised a generator alarm.

| Name | Value | Description |
|---|---|---|
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

### ParallelingSystemStateEnum  (ns=1;i=3015)

Operating state of a paralleling / switchgear system.

| Name | Value | Description |
|---|---|---|
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

### AftertreatmentStateEnum  (ns=1;i=3016)

State of the exhaust aftertreatment system.

| Name | Value | Description |
|---|---|---|
| NotEquipped | 0 |  |
| Normal | 1 |  |
| PassiveRegen | 2 |  |
| ActiveRegen | 3 |  |
| RegenInhibited | 4 |  |
| RegenRequired | 5 |  |
| DerateActive | 6 |  |
| Faulted | 7 |  |

### J1939LampStatusEnum  (ns=1;i=3017)

SAE J1939 DM1 diagnostic lamp status (lamp state plus flash rate).

| Name | Value | Description |
|---|---|---|
| Off | 0 | The lamp is off. |
| On | 1 | The lamp is on (steady). |
| SlowFlash | 2 | The lamp is flashing slowly. |
| FastFlash | 3 | The lamp is flashing fast. |
| NotAvailable | 4 | The lamp status is not available. |

### DiagnosticTroubleCodeType  (ns=1;i=3050)

A SAE J1939 diagnostic trouble code (DTC) reported by an engine ECU.

| Field | DataType | Description |
|---|---|---|
| Spn | UInt32 | Suspect Parameter Number identifying the faulty subsystem. |
| Fmi | Byte | Failure Mode Identifier describing the type of failure. |
| OccurrenceCount | Byte | Number of times the fault has become active. |
| ConversionMethod | Boolean | J1939 SPN conversion method flag. |
| Active | Boolean | TRUE while the fault is currently active (DM1). |
| SourceAddress | Byte | J1939 source address of the ECU that reported the code. |
| SourceName | String | Name of the ECU/controller that reported the code. |
| Severity | AlarmSeverityEnum | Severity classification of the fault. |
| Description | String | Human-readable description of the fault. |

