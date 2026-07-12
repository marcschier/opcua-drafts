#!/usr/bin/env python3
"""
OpenUSD reference writer for the OPC UA - OpenUSD Bindings Pump Annex.

This is the "real USD" demonstrator for the end-to-end validation: it consumes the
Pump binding descriptor and authors a live USD stage (`live.usda`) whose attributes
are driven by OPC UA values. It is intended to be run locally against a running
PumpDeviceIntegrationServer; Omniverse rendering is out of scope for CI.

Two modes:
  * --demo      Author a static example live.usda from the descriptor (no server,
                no pxr required -> falls back to a hand-written .usda). Deterministic.
  * --connect URL
                Connect to an OPC UA server (needs `asyncua`), Browse Server/OpenUSD,
                subscribe to the bound Variables under the chosen Pump, and write the
                mapped USD attributes into live.usda each change (needs `pxr`).

Design mirrors the base spec: for each enabled binding, resolve source (relative to the
represented object) and target (prim path + property), apply Scale/Offset + a small set
of RenderTargetKind mappings, and author the target attribute. Non-Good values honour
BadQualityAction (default Skip). Both pxr and asyncua are optional; the module degrades
gracefully so it can be inspected without either installed.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DESCRIPTOR = os.path.join(HERE, "Pumps.OpenUsdBinding.json")
LIVE_USDA = os.path.join(HERE, "live.usda")


def load_descriptor(path=DESCRIPTOR):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# --- value conversion (shared by demo and live paths) ----------------------
def temperature_to_color3f(celsius: float, lo=20.0, hi=100.0):
    """Blue (cold) -> red (hot), matching RenderTargetKind=DisplayColor semantics."""
    t = max(0.0, min(1.0, (celsius - lo) / (hi - lo)))
    return (t, 0.0, 1.0 - t)


def apply_binding(binding: dict, raw):
    """Return (usd_type, usd_value) for a raw source value per the binding."""
    kind = binding.get("renderTargetKind")
    scale = binding.get("scale", 1.0)
    offset = binding.get("offset", 0.0)
    if kind == "Rotation":
        # rpm -> degrees delta per tick is a runtime integration; for a snapshot we
        # map rpm directly through Scale/Offset to a rotateZ angle sample.
        return "double", float(raw) * scale + offset
    if kind == "DisplayColor":
        return "color3f", temperature_to_color3f(float(raw))
    if kind == "Visibility":
        return "token", "inherited" if bool(raw) else "invisible"
    # default scalar
    return binding.get("targetUsdTypeName", "double"), float(raw) * scale + offset


# --- demo (no server, no pxr required) -------------------------------------
_DEMO_SOURCE = {"Speed": 1450.0, "BearingTemperature": 72.5, "Running": True}


def _fmt_usda_value(usd_type, value):
    if usd_type == "color3f":
        return f"({value[0]:.4f}, {value[1]:.4f}, {value[2]:.4f})"
    if usd_type == "token":
        return f'"{value}"'
    if usd_type == "bool":
        return "true" if value else "false"
    return f"{float(value):.4f}"


def write_demo(desc: dict, out=LIVE_USDA):
    """Author a static live.usda from the descriptor using demo source values.

    Uses pxr if available for a validated stage; otherwise writes a hand-authored
    .usda with identical content so the demonstrator runs anywhere.
    """
    rep_prim = desc["representation"]["primPath"]
    rows = []  # (prim_path, prop, usd_type, usd_value)
    for b in desc["bindings"]:
        raw = _DEMO_SOURCE.get(b["name"])
        if raw is None:
            continue
        usd_type, val = apply_binding(b, raw)
        target_prim = b.get("targetPrimPath") or ""
        prim = rep_prim if target_prim == "" else target_prim
        rows.append((prim, b["targetPropertyName"], usd_type, val))

    try:
        from pxr import Usd, Sdf, Gf, UsdGeom  # noqa: F401
        stage = Usd.Stage.CreateNew(out) if not os.path.exists(out) else Usd.Stage.Open(out)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        for prim_path, prop, usd_type, val in rows:
            prim = stage.OverridePrim(prim_path)
            attr = prim.CreateAttribute(prop, _sdf_type(Sdf, usd_type))
            attr.Set(_gf_value(Gf, usd_type, val))
        stage.GetRootLayer().Save()
        print(f"[pxr] wrote {out} with {len(rows)} attributes")
    except Exception as e:  # pxr not installed or failed -> hand-authored fallback
        _write_usda_text(out, desc, rows)
        print(f"[fallback] wrote {out} with {len(rows)} attributes ({type(e).__name__})")


def _sdf_type(Sdf, usd_type):
    return {
        "double": Sdf.ValueTypeNames.Double,
        "float": Sdf.ValueTypeNames.Float,
        "color3f": Sdf.ValueTypeNames.Color3f,
        "token": Sdf.ValueTypeNames.Token,
        "bool": Sdf.ValueTypeNames.Bool,
    }.get(usd_type, Sdf.ValueTypeNames.Double)


def _gf_value(Gf, usd_type, val):
    if usd_type == "color3f":
        return Gf.Vec3f(*val)
    return val


def _write_usda_text(out, desc, rows):
    # Group properties by prim.
    by_prim = {}
    for prim_path, prop, usd_type, val in rows:
        by_prim.setdefault(prim_path, []).append((prop, usd_type, val))
    lines = ['#usda 1.0', '(', '    upAxis = "Y"', '    doc = "OPC UA -> OpenUSD live bindings (demo)"', ')', '']
    for prim_path, props in by_prim.items():
        segs = [s for s in prim_path.strip("/").split("/") if s]
        indent = ""
        for i, seg in enumerate(segs):
            lines.append(f'{indent}over "{seg}"')
            lines.append(f'{indent}{{')
            if i == len(segs) - 1:
                for prop, usd_type, val in props:
                    lines.append(f'{indent}    {usd_type} {prop} = {_fmt_usda_value(usd_type, val)}')
            indent += "    "
        for _ in segs:
            indent = indent[:-4]
            lines.append(f'{indent}}}')
        lines.append("")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


# --- live (OPC UA + pxr) ---------------------------------------------------
async def run_connect(url: str, pump_browse_name: str):
    try:
        from asyncua import Client
    except ImportError:
        print("ERROR: --connect requires `asyncua` (pip install asyncua)", file=sys.stderr)
        return 2
    try:
        from pxr import Usd, Sdf, Gf, UsdGeom  # noqa: F401
    except ImportError:
        print("ERROR: --connect requires `pxr` (OpenUSD python) to author live.usda", file=sys.stderr)
        return 2

    desc = load_descriptor()
    # A full implementation Browses Server/OpenUSD/Representations to discover the
    # representation and its bindings. For this reference writer we drive the mapping
    # from the descriptor and resolve sources relative to the named Pump object.
    async with Client(url=url) as client:
        objects = client.nodes.objects
        # Resolve the Pump object by BrowseName under Objects (server-specific path).
        pump = await _find_child(client, objects, pump_browse_name)
        if pump is None:
            print(f"ERROR: pump '{pump_browse_name}' not found under Objects", file=sys.stderr)
            return 3
        stage = Usd.Stage.CreateNew(LIVE_USDA) if not os.path.exists(LIVE_USDA) else Usd.Stage.Open(LIVE_USDA)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        # Subscribe to each binding's source and author on change.
        handler = _UsdHandler(stage, desc, Sdf, Gf)
        sub = await client.create_subscription(500, handler)
        for b in desc["bindings"]:
            node = await _resolve_relative(client, pump, b["sourceBrowsePath"])
            if node is not None:
                handler.map[node.nodeid] = b
                await sub.subscribe_data_change(node)
        print(f"Subscribed {len(handler.map)} bindings; writing {LIVE_USDA}. Ctrl+C to stop.")
        import asyncio
        try:
            await asyncio.sleep(float("inf"))
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
    return 0


class _UsdHandler:
    def __init__(self, stage, desc, Sdf, Gf):
        self.stage, self.desc, self.Sdf, self.Gf = stage, desc, Sdf, Gf
        self.map = {}

    def datachange_notification(self, node, val, data):
        b = self.map.get(node.nodeid)
        if b is None:
            return
        # BadQualityAction: Skip on non-Good (asyncua exposes StatusCode on data).
        sc = getattr(getattr(data, "monitored_item", None), "Value", None)
        if sc is not None and getattr(sc, "StatusCode", None) is not None and sc.StatusCode.value != 0:
            return
        usd_type, usd_val = apply_binding(b, val)
        prim_path = b.get("targetPrimPath") or self.desc["representation"]["primPath"]
        prim = self.stage.OverridePrim(prim_path)
        attr = prim.CreateAttribute(b["targetPropertyName"], _sdf_type(self.Sdf, usd_type))
        attr.Set(_gf_value(self.Gf, usd_type, usd_val))
        self.stage.GetRootLayer().Save()


async def _find_child(client, parent, browse_name):
    for child in await parent.get_children():
        bn = await child.read_browse_name()
        if bn.Name == browse_name:
            return child
    return None


async def _resolve_relative(client, start, browse_path):
    node = start
    for seg in [s for s in browse_path.strip("/").split("/") if s]:
        node = await _find_child(client, node, seg)
        if node is None:
            return None
    return node


def main(argv=None):
    ap = argparse.ArgumentParser(description="OPC UA -> OpenUSD live writer (Pump demo)")
    ap.add_argument("--demo", action="store_true", help="author a static live.usda (no server)")
    ap.add_argument("--connect", metavar="URL", help="opc.tcp:// server URL for live authoring")
    ap.add_argument("--pump", default="Pump #1", help="Pump BrowseName under Objects")
    args = ap.parse_args(argv)
    desc = load_descriptor()
    if args.connect:
        import asyncio
        return asyncio.run(run_connect(args.connect, args.pump))
    # default is demo
    write_demo(desc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
