# Robot with GPOS/RSL and USD

**What this shows**

A two-robot cell runs from `MinimalRobotServer`. The same OPC UA node manager publishes OPC 40010 Robotics topology, OPC 10000-210 RSL frame chains, OPC 10000-211 GPOS global locations, and OpenUSD representations. The generic OpenUSD connector discovers the mappings, fetches the served stage, and animates the robots without robot-specific bridge code.

**What it proves**

It proves OpenUSD Part 1 and Part 2 can render a companion-model robot cell directly, while the Robot Intent draft sits beside Robotics as the command model for the same robot domain.

**Prerequisites**

- PowerShell 7.4 or later.
- .NET 10 SDK on `PATH`.
- A `UA-.NETStandard` checkout on `master`.
- The optional `Opc.Ua.OpenUsd.Connector.Viewer` assembly and native OpenUSD payload available to the connector for `--view`.

**Run it**

```powershell
.\decks\demos\02-robot-gpos-rsl-usd\run-demo.ps1 -StackRoot $env:OPCUA_STACK_ROOT
```

**Step by step**

1. **Build the robot server and OpenUSD viewer**
   - On screen: the script builds `MinimalRobotServer`, the OpenUSD connector, and the optional viewer project.
   - What to say: "The demo is not a special viewer. It builds the same generic connector used by the other OpenUSD demos."

2. **Start the robot cell server**
   - On screen: `MinimalRobotServer` listens at `opc.tcp://localhost:62830/MinimalRobotServer`.
   - What to say: "This one server composes Robotics, RSL, GPOS, and OpenUSD in one manager. The Robotics guide calls out this exact pattern: the sample combines Robotics with OPC 10000-210 RSL frames and OPC 10000-211 GPOS locations and binds the whole cell to OpenUSD."

3. **Open the generic OpenUSD viewer**
   - On screen: the connector opens a viewport and the two mobile robots move through the cell.
   - What to say: "The connector starts at `Server/OpenUSD/Representations`. It does not know the Robotics model. It reads the binding contract and writes USD attributes."

4. **Point out the positioning model in the live twin**
   - On screen: robot bases, joints, warnings, and cell parts update in the stage.
   - What to say: "RSL gives the relative frame chain: world, robot base, flange, attach point. GPOS gives global longitude, latitude, and elevation. The pose drives the stage, so the robot knows where it is locally and globally."

**Talking points**

- OPC 40010 describes the robot; it does not carry motion verbs.
- RSL is for relative spatial location and frame chains.
- GPOS is for global position and zone context.
- OpenUSD Part 1 makes the Object-to-prim and Variable-to-attribute mapping discoverable.
- OpenUSD Part 2 is the scene-materialization direction: the same scene model can become address-space content.
- The viewer is generic. The server owns the model and the mapping.

**Troubleshooting**

- If the stack checkout is not found, pass `-StackRoot` explicitly.
- If the viewer does not open, confirm the optional viewer assembly and native OpenUSD runtime are installed beside the connector output.
- If port 62830 is busy, stop the other server or change the script and the endpoint consistently.
- If the connector reports certificate warnings, keep `--insecure` only for this local demo.

**Links**

- Draft in the private review repository: `spec-drafts/metaverse-specs/openusd-binding/`
- Draft in the private review repository: `spec-drafts/metaverse-specs/openusd-scene/`
- Draft: [metaverse-specs/robot-intent](../../../metaverse-specs/robot-intent/)
- Stack docs in the stack checkout: `docs/Robotics.md`
- Stack docs in the stack checkout: `docs/Positioning.md`
- Stack docs in the stack checkout: `docs/OpenUsd.md`
- Sample source in the stack checkout: `samples/Robotics/MinimalRobotServer/`
- Viewer source in the stack checkout: `tools/Opc.Ua.OpenUsd.Connector.Viewer/`
