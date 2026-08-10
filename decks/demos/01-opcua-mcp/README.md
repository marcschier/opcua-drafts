# Demo 1 — OPC UA MCP server

An OPC UA Server's address space is driven by a language model through the Model Context Protocol.
The MCP server exposes OPC UA Part 4 services as tools, so the model can discover endpoints, connect,
browse, read, write, subscribe, publish and call methods without a hand-written OPC UA client.

## What it proves

It proves the stack can expose a standard OPC UA Server as an MCP tool surface used directly by agents
and by the later Robot Intent demo.

## Prerequisites

- PowerShell 7.4 or later.
- .NET SDK 10.0 or later.
- A `UA-.NETStandard` checkout on `master`.
- An MCP-capable client if you want to make the tool calls live.

## Run it

```powershell
.\decks\demos\01-opcua-mcp\run-demo.ps1 -StackRoot D:\git\UA-.NETStandard6
```

## Step by step

1. **Build the reference server and MCP server.** On screen: the script builds
   `ConsoleReferenceServer.csproj` and `Opc.Ua.Mcp.csproj`. Say: "This demo only needs a normal OPC
   UA Server and the MCP tool host."
2. **Start the OPC UA reference server.** On screen: the endpoint
   `opc.tcp://localhost:62541/Quickstarts/ReferenceServer` accepts connections. Say: "This is an
   ordinary server; no AI-specific code is in it."
3. **Start the MCP server with the services profile.** On screen: `http://localhost:5100/mcp` is
   listening. Say: "The services profile exposes the client-service tools: connection, browsing,
   attributes, methods, subscriptions and monitored items."
4. **Connect the model to the OPC UA Server.** On screen: the presenter calls `Connect` from the MCP
   client and reads the session resources. Say: "The model now has a named OPC UA session and can see
   the namespace table."
5. **Browse, read, write, subscribe and call methods.** On screen: `BrowseAll` starts at `i=85`,
   `ReadValue` reads `i=2258`, and subscription tools stream changes. Say: "Natural language becomes
   bounded OPC UA service calls, not a private protocol."

## Talking points

- `opcua-mcp` supports stdio for local clients and Streamable HTTP at `/mcp` for remote clients.
- Profiles bound the tool catalog: `core`, `services`, `administration`, `pubsub`, `diagnostics`,
  and `full`.
- Sessions are MCP resources, so a client can inspect active connections and namespace tables.
- The same tool surface is used in demo 5 to drive Robot Intent.

## Troubleshooting

- If port `62541` is busy, stop the other reference server before running the script.
- If `5100` is busy, run `opcua-mcp` manually with another `--port` and update your MCP client.
- `autoAcceptCerts` and `--autoaccept` are for local demos only.

## Links

- MCP server guide: `D:\git\UA-.NETStandard6\docs\McpServer.md`
- MCP source: `D:\git\UA-.NETStandard6\tools\Opc.Ua.Mcp`
- OPC UA reference server: `D:\git\UA-.NETStandard6\samples\ConsoleReferenceServer`
- Model Context Protocol: https://modelcontextprotocol.io
