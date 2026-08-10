# Pumps with pump companion spec via WoT Connectivity

**What this shows**

Two flat OPC UA tag servers publish simple values with no Pump companion-model hierarchy. A generic WoT aggregation server receives Thing Model and Thing Description documents, projects a conforming Pump address space from them, and binds the projected variables back to the flat source tags. The documents are canonical; the address space is the derived projection.

**What it proves**

It proves the WoT Binding and WoT Connectivity drafts can materialize a companion-spec-shaped machine from documents without changing the device.

**Prerequisites**

- PowerShell 7.4 or later.
- .NET 10 SDK on `PATH`.
- A `UA-.NETStandard` checkout on `master`.
- Ports 62550, 62551, and 62552 free on localhost.

**Run it**

```powershell
.\decks\demos\04-pumps-wotcon\run-demo.ps1 -StackRoot D:\git\UA-.NETStandard6
```

**Step by step**

1. **Build the WoT aggregation sample projects**
   - On screen: the script builds `FlatTagServer`, `AggregationServer`, and `AggregationClient`.
   - What to say: "None of these projects contains generated Pumps server code in the aggregation server. The pump shape comes from documents."

2. **Start the two flat tag sources**
   - On screen: Source A listens on port 62551 and Source B listens on port 62552.
   - What to say: "These are deliberately dumb sources. They publish variables like DifferentialPressure and BearingTemperature, not a PumpType object."

3. **Start the generic aggregation server**
   - On screen: `AggregationServer` listens on port 62550 and waits for registry documents.
   - What to say: "The server is a document registry and projection host. It does not know this particular pump until the client uploads the model set."

4. **Upload the WoT documents and read the Pump projection**
   - On screen: the client reports four uploaded resources, a successful refresh generation, a browsed Pump hierarchy, and ten Good values.
   - What to say: "DI, Machinery, Pumps, and the Sample Pump Thing Description form a dependency closure. Refresh builds a runtime NodeSet generation, maps each property to Source A or Source B, and reads through the materialized Pump NodeIds."

**Talking points**

- The Thing Models describe what a pump is.
- The Thing Description describes this pump and where its values come from.
- `uav:mapToNodeId` names the target Pump variable in the projected namespace.
- The OPC UA form names the upstream source variable with portable `nsu=` NodeIds.
- Invalid or incomplete document closures do not publish a half-built address space.
- A projection can be replaced by a new generation while old monitored items drain.

**Troubleshooting**

- If the client cannot connect, confirm all three servers are still running.
- If the source namespace is rejected, use the exact Source A and Source B namespace URIs from the script.
- If refresh reports dependency failures, check `Documents\documents.json` and keep the DI -> Machinery -> Pumps -> Pump order.
- If values come from the wrong source, inspect `SamplePump.td.json` endpoint placeholders and property forms.

**Links**

- Draft: `D:\git\spec-drafts\wot-specs\WoT-Binding\`
- Draft: `D:\git\spec-drafts\wot-specs\WoT-Connectivity\`
- Stack docs: `D:\git\UA-.NETStandard6\docs\WoTConnectivity.md`
- Stack docs: `D:\git\UA-.NETStandard6\docs\WotBindings.md`
- Stack docs: `D:\git\UA-.NETStandard6\docs\WoTNodeSetConversion.md`
- Sample source: `D:\git\UA-.NETStandard6\samples\WotCon\`
- Documents: `D:\git\UA-.NETStandard6\samples\WotCon\AggregationClient\Documents\`
