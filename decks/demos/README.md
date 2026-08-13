# Demos

Ten demos showing the drafts in this repository running on the
[OPC UA .NET Standard stack](https://github.com/OPCFoundation/UA-.NETStandard).

Each folder holds a **presenter walkthrough** (`README.md`) — what the demo shows, a topology
diagram of the processes it starts, what to say at each step, and what to do when it misbehaves —
and, where the code exists, a **runnable script** (`run-demo.ps1`) that checks prerequisites, builds
only what it needs, starts the servers, runs the client, and tears everything down again.

Each demo also has one slide in [the deck](../README.md), placed next to the draft it demonstrates.

## The ten

| # | Demo | Shows | State |
|---|---|---|---|
| 1 | [OPC UA MCP server](01-opcua-mcp/) | Any address space, driven by a language model | Runs on `master` |
| 2 | [Robot with GPOS/RSL and USD](02-robot-gpos-rsl-usd/) | Robot Intent · OpenUSD · Parts 210/211 | Runs on `master` |
| 3 | [Pump USD and composition](03-pump-usd-composition/) | OpenUSD Parts 1 and 2, site composition | Runs on `master` |
| 4 | [Pumps via WoT Connectivity](04-pumps-wotcon/) | WoT Binding and Connectivity | Runs on `master` |
| 5 | [Robot intent viewer plus MCP](05-robot-intent-viewer-mcp/) | Robot Intent lifecycle, live viewer | Runs on `master` |
| 6 | [Server redundancy](06-server-redundancy/) | Transparent failover, subscription transfer | Runs on `master` |
| 7 | [AAS + WoT + xRegistry](07-aas-wot-xregistry/) | One asset, three projections | Walkthrough only |
| 8 | [Media over Data Channels](08-media-data-channels/) | Video on an already-open SecureChannel | Feature branch |
| 9 | [Vision](09-vision/) | Camera, inference, published result | Walkthrough only |
| 10 | [AI model loading](10-ai-model-loading/) | Model lifecycle, provenance, rollout | Feature branch |

**Walkthrough only** means there is no runnable implementation yet; the folder holds the narrative
and, where an implementation is in flight, says where it is and what is still missing. **Feature
branch** means the code exists but is not on the stack's `master` — the script says which branch and
refuses to run without it.

## Prerequisites, once

1. **PowerShell 7.4 or later.** The scripts declare `#Requires -Version 7.4`.
2. **The .NET 10 SDK.** `Assert-DotNetSdk` checks this and fails with a clear message.
3. **A checkout of the stack.** Point the scripts at it once per session:

   ```powershell
   $env:OPCUA_STACK_ROOT = '<path-to-your-UA-.NETStandard-checkout>'
   ```

   or pass `-StackRoot` per run. With neither, the scripts look for a sibling checkout containing
   `UA.slnx` that also carries the specific sample the demo needs — which is what makes them work
   on a machine holding several checkouts on different branches.

4. **First run takes longer.** The first build restores packages, and the first server start creates
   an application instance certificate.

## Certificates on a demo machine

Every sample is a real OPC UA application with a real PKI, so a client and server that have never
met do not trust each other. On first run a server creates a self-signed application certificate
under `%LocalApplicationData%\OPC Foundation\pki\own`, and puts any client certificate it does not
trust into `pki\rejected\certs`.

Two ways through it:

- **Auto-accept**, which several samples support with `-a` / `--autoaccept`. Fine for a demo, wrong
  for anything else. The scripts use it where the sample offers it.
- **Trust explicitly** — move the certificate from `rejected\certs` to `trusted\certs` and re-run.
  Slower, but it is what an audience asking "so how does trust work" wants to see.

To start from nothing, delete the `pki` folder; everything is recreated on the next run.

See [`Certificates.md`](https://github.com/OPCFoundation/UA-.NETStandard/blob/master/docs/Certificates.md)
in the stack for the full store layout.

## Running one

```powershell
# the default: build, run, tear down
pwsh decks/demos/05-robot-intent-viewer-mcp/run-demo.ps1

# skip the build when you have just run another demo
pwsh decks/demos/05-robot-intent-viewer-mcp/run-demo.ps1 -NoBuild

# leave the servers up afterwards to poke at them
pwsh decks/demos/05-robot-intent-viewer-mcp/run-demo.ps1 -KeepRunning
```

Every script takes `-StackRoot`, `-NoBuild` and `-KeepRunning`. Stop a demo with `Ctrl+C`; the
`finally` block stops everything the script started, by process id.

## Shared machinery

[`_shared/Demo.psm1`](_shared/Demo.psm1) holds what all the scripts have in common, so each script
is about its demo rather than about process management:

| Function | Does |
|---|---|
| `Write-DemoBanner` / `Write-DemoStep` / `Write-DemoNote` | Numbered narration matching the walkthrough |
| `Resolve-StackRoot` | Finds the right stack checkout, given the paths the demo needs |
| `Assert-DotNetSdk` | Fails early when the SDK is missing or too old |
| `Assert-StackBranch` | Refuses to run when the checkout lacks the feature-branch code, and says how to get it |
| `Invoke-DemoBuild` | Builds just the projects the demo needs |
| `Start-DemoProcess` | Starts a server and registers it for teardown |
| `Wait-DemoEndpoint` | Waits for a TCP endpoint instead of guessing with `Start-Sleep` |
| `Stop-DemoProcesses` | Stops everything started, in reverse order, by process id |
| `Wait-DemoKeypress` | Pauses so the presenter can talk over what is on screen |

## Presenting well

- **Run it once before the room fills.** The first run builds and creates certificates; the second
  is fast. `-NoBuild` afterwards keeps it that way.
- **The script pauses on purpose.** `Wait-DemoKeypress` marks the points where something has just
  happened and is worth explaining. Do not race past them.
- **Say what it proves.** Each walkthrough has a one-line *What it proves* near the top; it is the
  sentence that connects the terminal output to the specification slide before it.
- **Be straight about the gaps.** Four of the ten do not fully run yet, and the walkthroughs say so.
  An audience trusts a demo set that admits what is not built. Demo 9 is the sharpest case: the
  implementation exists on a feature branch, it is what moved the Vision draft to 0.2.0, and it
  still does not run the loop end to end — say all three.
