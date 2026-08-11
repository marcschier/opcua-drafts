# Changelog

## 1.2.0 — 2026-08-11

- Added `DiagnosticTroubleCodeDataType` at `i=3051` and retained `DiagnosticTroubleCodeType` at `i=3050` as a deprecated compatibility type. The replacement follows OPC 11030 DataType naming guidance and makes `ProtectionAction` optional.
- Added `GeneratorProtectionActionEnum` at `i=3018` and `ProtectionAction` as an appended alarm member. The legacy `AlarmSeverityEnum` and `GeneratorAlarmSeverity` retain their NodeIds and definitions for compatibility. The standard Part 9 `Severity` field is the sole event-urgency authority; `ProtectionAction` identifies the requested generator response and `IsShutdown` reports the actual outcome.
- Added current DTC arrays using the replacement DataType while retaining the published legacy arrays. No existing NodeId or DataType definition changed.
- Defined the deterministic projection from the authoritative `OperatingMode` and `OperatingState` values to the optional Machinery `MachineryOperationMode` state machine.
- Aligned the specification banner, NodeSet model identity and Word configuration. The generated NodeSet previously identified itself as `1.1.0` while the specification banner still stated `1.0.0`.
- Made the generated Annex A update from `tools/build_model.py` so the specification, NodeSet, NodeId CSV and generated reference cannot drift.
