# Pump USD and composition

**What this shows**

A pump server publishes several simulated OPC 40223 PumpType machines through the DI stack and OpenUSD bindings. A separate site server owns no pumps; it publishes a site shell and a cross-server component binding to the pump server. The generic connector runs with federation enabled and assembles the live machines into one USD stage.

**What it proves**

It proves OpenUSD Part 1 and Part 2 can describe both the machine-to-prim binding and the composed scene, so a site is assembled through USD composition rather than a bespoke aggregator.

**Prerequisites**

- PowerShell 7.4 or later.
- .NET 10 SDK on `PATH`.
- A `UA-.NETStandard` checkout on `master`.
- The optional `Opc.Ua.OpenUsd.Connector.Viewer` assembly and native OpenUSD payload available to the connector for `--view`.

**Run it**

```powershell
.\decks\demos\03-pump-usd-composition\run-demo.ps1 -StackRoot $env:OPCUA_STACK_ROOT
```

**Step by step**

1. **Build the pump, site, and OpenUSD projects**
   - On screen: the script builds the pump server, site server, connector, and viewer project.
   - What to say: "There are two server roles. The device server owns pumps. The site server owns composition."

2. **Start the DI pump server**
   - On screen: `PumpDeviceIntegrationServer` listens at `opc.tcp://localhost:62542/PumpDeviceIntegrationServer` with three pumps.
   - What to say: "Each pump is a DI and Pumps companion-model object. Each pump also has an OpenUSD representation, so the stage can show several independent machines."

3. **Start the site composition server**
   - On screen: `SiteCompositionServer` listens at `opc.tcp://localhost:62544/SiteCompositionServer` and names the pump server as the Pump Hall owner.
   - What to say: "This server does not mirror the pump address space. It publishes a site shell and a component endpoint. There is no cache of pump data here."

4. **Render the federated site stage**
   - On screen: the connector opens the site, follows the component endpoint, and shows live pumps in the composed stage.
   - What to say: "Composition is the point. The site is a USD composition layer over machines owned by another server. Federation is explicit because the connector opens endpoints named by the server."

**Talking points**

- The pump server is the source of device truth.
- The site server is the source of layout and composition truth.
- `--federate` is opt-in because cross-server endpoints are a trust decision.
- Each pump keeps its own live bindings: impeller rotation, colour, gauges, alarms, and bay position.
- USD composition lets several machines land on one stage without a new aggregator protocol.

**Troubleshooting**

- If the site shows only the shell, confirm the pump server is running and reachable on port 62542.
- If the connector skips a federated component, check the endpoint printed by the site server.
- If the viewer does not open, confirm the optional viewer assembly and native OpenUSD runtime are installed beside the connector output.
- If ports 62542 or 62544 are busy, stop the other process or update all matching endpoints in the script.

**Links**

- Draft in the private review repository: `spec-drafts/metaverse-specs/openusd-binding/`
- Draft in the private review repository: `spec-drafts/metaverse-specs/openusd-scene/`
- Stack docs in the stack checkout: `docs/OpenUsd.md`
- Stack docs in the stack checkout: `docs/DeviceIntegration.md`
- Sample source in the stack checkout: `samples/PumpDeviceIntegrationServer/`
- Sample source in the stack checkout: `samples/SiteCompositionServer/`
- Viewer source in the stack checkout: `tools/Opc.Ua.OpenUsd.Connector.Viewer/`
