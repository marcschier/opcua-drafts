# End-to-end guide: render a live pump from OPC UA in OpenUSD

This is a hands-on, step-by-step guide that runs the **PumpDeviceIntegrationServer**
bound to an **OpenUSD** model and shows the pump **rendered with live data**: the
impeller spins with mass flow, the body warms from blue to red with bearing
temperature, and a status light glows with differential pressure — all driven live over
OPC UA, with **no pump-specific code** in the connector or the renderer.

It realizes the collaboration flow described in Annex B of the base specification
(`../../../openusd-binding/OPC-UA-OpenUSD-Bindings.md`). This document lives **outside**
the normative spec; it is a tutorial for implementers.

## What you will build

```
PumpDeviceIntegrationServer            (OPC UA server: PumpType + OpenUSD bindings)
        │  Server/OpenUSD/Representations  (discovery)
        ▼
OpenUsdConnector  ──► UsdFileSink ──►  live.usda        (runtime override opinions)
                                          │  subLayers
                                          ▼
                                       stage.usda  =  live.usda  +  Plant.usda
                                          │
                                          ▼
                                 usdview / NVIDIA Omniverse   (the rendered live pump)
```

- **Server** — exposes `Pump #1` with an `OpenUsdRepresentation` (prim `/Plant/Pumps/P101`)
  and three live bindings.
- **Connector** — the standalone C# client app `PumpDeviceIntegrationBridge`. It discovers the
  representation via `Server/OpenUSD/Representations`, subscribes to the bound Variables,
  converts, and writes a USD override layer through `UsdFileSink`.
- **Base asset** — `Plant.usda` (geometry + materials). `stage.usda` composes the live
  override layer on top of it.
- **Viewer** — `usdview` (baseline) or NVIDIA Omniverse (RTX).

## The three live bindings

| Source (Pump measurement) | USD target | Kind | Visible effect |
|---|---|---|---|
| `MassFlow` | `/Plant/Pumps/P101/Impeller` · `xformOp:rotateZ` | Rotation | impeller angle |
| `BearingTemperature` | `/Plant/Pumps/P101/Body` · `primvars:displayColor` | DisplayColor | body colour (blue→red) |
| `DifferentialPressure` | `/Plant/Pumps/P101/StatusLight/Mat/Surface` · `inputs:emissiveColor` | EmissiveColor | status light glow |

## Prerequisites

- **.NET SDK 10** — to build and run the server + connector.
- The **UA-.NETStandard** working copy on the `openusd-binding` branch (pull request:
  *PumpDeviceIntegrationServer: OPC UA — OpenUSD Bindings end-to-end*).
- A USD viewer, either:
  - **usdview** — ships with a full OpenUSD build (e.g. NVIDIA's USD, a source build, or
    Omniverse's `usdview`). *Note:* the `usd-core` PyPI wheel provides the `pxr` Python
    modules used for validation, but **not** the `usdview` GUI.
  - **NVIDIA Omniverse** — USD Composer / Kit, for an RTX render and continuous `.live`
    updates.
- *(Optional)* Python 3 with `usd-core` (`pip install usd-core`) to validate composition,
  and `asyncua` (`pip install asyncua`) for the alternative Python connector.

## Step 1 — Get the code

```bash
# The sample server + connector
git clone https://github.com/marcschier/UA-.NETStandard.git
cd UA-.NETStandard
git checkout openusd-binding

# The base asset + this guide (spec repo)
git clone https://github.com/marcschier/opcua-drafts.git
```

The base asset, composed stage, descriptor, and Python writer are in
`opcua-drafts/core-specs/extras/openusd-binding/examples/pumps/`.

## Step 2 — Build the server and the connector

The **server** (`PumpDeviceIntegrationServer`) and the **connector** (`PumpDeviceIntegrationBridge`)
are two separate console apps — the connector is a standalone OPC UA client.

```bash
cd UA-.NETStandard
dotnet build Applications/PumpDeviceIntegrationServer/PumpDeviceIntegrationServer.csproj -c Release -f net10.0
dotnet build Applications/PumpDeviceIntegrationBridge/PumpDeviceIntegrationBridge.csproj -c Release -f net10.0
```

## Step 3 — Prepare a working folder with the base asset

Copy the base asset and the composed stage into a working folder the connector will
write `live.usda` into:

```bash
mkdir ~/pump-live
cp opcua-drafts/core-specs/extras/openusd-binding/examples/pumps/Plant.usda ~/pump-live/
cp opcua-drafts/core-specs/extras/openusd-binding/examples/pumps/stage.usda ~/pump-live/
```

`stage.usda` sublayers `live.usda` (stronger) over `Plant.usda`. `live.usda` is authored
by the connector in Step 5.

## Step 4 — Start the server (terminal 1)

```bash
cd UA-.NETStandard
dotnet run --project Applications/PumpDeviceIntegrationServer -c Release -f net10.0 -- --host localhost --port 62810
```

Wait for: `OPC UA server listening at opc.tcp://localhost:62810/PumpDeviceIntegrationServer.`
The server simulates the pump, so `MassFlow`, `BearingTemperature`, and
`DifferentialPressure` change over time — that is what makes the render *live*.

## Step 5 — Run the connector (terminal 2)

The connector is a standalone client — point it at the server and the output layer:

```bash
cd UA-.NETStandard
dotnet run --project Applications/PumpDeviceIntegrationBridge -c Release -f net10.0 -- \
  --server opc.tcp://localhost:62810/PumpDeviceIntegrationServer --out ~/pump-live/live.usda
```

You should see:

```
Connecting to opc.tcp://localhost:62810/PumpDeviceIntegrationServer ...
Streaming live OPC UA values into ~/pump-live/live.usda. Press Ctrl+C to stop.
```

Leave it running — it rewrites `live.usda` on every value change. (Use `--seconds N` to
run for a fixed time instead of until Ctrl+C.) `live.usda` now contains, for example:

```usda
over "Plant" { over "Pumps" { over "P101" {
    over "Impeller" { double xformOp:rotateZ = 0.0455 }
    over "Body" { color3f[] primvars:displayColor = [(1.0000, 0.0000, 0.0000)] }
    over "StatusLight" { over "Mat" { over "Surface" {
        color3f inputs:emissiveColor = (0.1000, 1.0000, 0.2000) } } }
} } }
```

## Step 6 — Open the rendered live pump

### Baseline — usdview

```bash
usdview ~/pump-live/stage.usda
```

You will see the pump: a cylindrical **body**, a two-blade **impeller** on top, and a
small **status light** sphere. With the connector running, the composed values are live:

- the **impeller** sits at the `rotateZ` angle from mass flow,
- the **body** is coloured from bearing temperature (blue when cool, red when hot),
- the **status light** glows from differential pressure.

usdview loads a **snapshot**; press **`R`** (Reload All Layers, or *File → Reload All Layers*)
to pull the connector's latest `live.usda`. Watch the impeller angle and body colour step
as you reload.

### Premium — NVIDIA Omniverse (RTX, continuous)

Open `~/pump-live/stage.usda` in **USD Composer**. Omniverse treats the override layer as a
live layer and updates the viewport **continuously** as the connector writes — the impeller
turns, the body shifts colour, and the status light's **emissive** material glows under RTX
without reloading.

> The emissive glow needs a material-aware renderer (Omniverse RTX, or usdview with Storm),
> because it drives a `UsdPreviewSurface` shader input; `displayColor` and the transform
> render everywhere.

## What you should see

A pump whose impeller **spins**, whose body **warms toward red**, and whose status light
**glows brighter** as the simulated pump runs — entirely driven by live OPC UA data through
the declared bindings. Capture a screenshot of your viewport here for your own docs; an RTX
render is not reproducible in CI.

## Alternative — the Python connector/writer

The same flow is available in Python (a secondary demonstrator):

```bash
cd opcua-drafts/core-specs/extras/openusd-binding/examples/pumps

# 1) Static demo layer (no server, no pxr required):
python usd_writer.py --demo

# 2) Live: discover Server/OpenUSD/Representations, subscribe, author live.usda:
pip install asyncua usd-core
python usd_writer.py --connect opc.tcp://localhost:62810/PumpDeviceIntegrationServer
```

Then open `stage.usda` as in Step 6.

## Validate composition without a GUI

If you only have `usd-core` (no `usdview`), confirm the live layer composes over the base:

```bash
python - <<'PY'
from pxr import Usd, UsdGeom
s = Usd.Stage.Open("stage.usda")
g = lambda p, a: s.GetPrimAtPath(p).GetAttribute(a).Get()
print("upAxis      :", UsdGeom.GetStageUpAxis(s))
print("rotateZ     :", g("/Plant/Pumps/P101/Impeller", "xformOp:rotateZ"))
print("displayColor:", g("/Plant/Pumps/P101/Body", "primvars:displayColor"))
print("emissive    :", g("/Plant/Pumps/P101/StatusLight/Mat/Surface", "inputs:emissiveColor"))
PY
```

## Troubleshooting

- **`could not reach the server endpoint`** — start the server (Step 4) first and match the
  `--server` URL/port. The connector retries for ~20 s.
- **Certificate prompts** — both the server and the connector auto-accept untrusted certs
  for this demo; PKI stores are created under the temp directory.
- **Port already in use** — pick another `--port` for the server and the same in
  `--server`.
- **`live.usda` not found in usdview** — run the connector at least once so the file
  exists; `stage.usda` sublayers it.
- **No emissive glow in usdview** — use Storm with materials, or Omniverse; `displayColor`
  and the impeller rotation are visible in any renderer.
- **Values don't change** — the pump simulation drives them; give it a few seconds, and in
  usdview **reload** to see the latest snapshot.

## How this maps to the specification

- **Discovery** — the connector starts at `Server/OpenUSD/Representations` (base spec §4.2),
  never at "the pump". The same connector binary works for any conforming server.
- **Bindings** — each `OpenUsdLiveBinding` declares `SourceNodeId`, target prim/property,
  `RenderTargetKind`, and `Scale`; the connector reads them and applies the conversion
  (§5.7–§5.8).
- **Layering** — OPC UA is the single mapping authority; the base USD asset is never
  modified. Live values live in a composed override layer (`live.usda`), the equivalent of
  an Omniverse Nucleus `.live` layer (Part 3).
- **Actors** — server author, USD asset author, connector vendor, and visualization operator
  each work against the model as the contract (Annex B).
