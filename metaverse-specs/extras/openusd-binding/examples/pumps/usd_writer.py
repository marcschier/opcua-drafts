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
                Connect to an OPC UA server (needs `asyncua`), discover
                Server/OpenUSD/Representations, read each binding's SourceNodeId +
                Target* from the server, subscribe, and write the mapped USD
                attributes into live.usda on each change (needs `pxr`). No local
                descriptor and no domain knowledge required.

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


def pressure_to_emissive3f(bar: float, lo=0.0, hi=6.0):
    """Dark -> bright green-white glow, matching RenderTargetKind=EmissiveColor."""
    t = max(0.0, min(1.0, (bar - lo) / (hi - lo)))
    return (0.1 * t, t, 0.2 * t)


def convert_by_target(prop: str, raw, scale=1.0):
    """Server-driven conversion: decide the USD type/value from the target property.

    Used by the registry-discovery connect path, which reads TargetPropertyName
    from the server rather than a local descriptor.
    """
    p = (prop or "").lower()
    if "emissive" in p:
        return "color3f", pressure_to_emissive3f(float(raw))
    if "displaycolor" in p:
        return "color3f[]", [temperature_to_color3f(float(raw))]
    if "visibility" in p:
        return "token", "inherited" if bool(raw) else "invisible"
    return "double", float(raw) * (scale or 1.0)


def apply_binding(binding: dict, raw):
    """Return (usd_type, usd_value) for a raw source value per the binding."""
    kind = binding.get("renderTargetKind")
    scale = binding.get("scale", 1.0)
    offset = binding.get("offset", 0.0)
    if kind == "Rotation":
        return "double", float(raw) * scale + offset
    if kind == "DisplayColor":
        return "color3f[]", [temperature_to_color3f(float(raw))]
    if kind == "EmissiveColor":
        return "color3f", pressure_to_emissive3f(float(raw))
    if kind == "Visibility":
        return "token", "inherited" if bool(raw) else "invisible"
    # default scalar
    return binding.get("targetUsdTypeName", "double"), float(raw) * scale + offset


# --- demo (no server, no pxr required) -------------------------------------
_DEMO_SOURCE = {"MassFlowSpin": 42.0, "BearingTempColor": 72.5, "DiffPressureEmissive": 3.2}


def _fmt_usda_value(usd_type, value):
    if usd_type == "color3f":
        return f"({value[0]:.4f}, {value[1]:.4f}, {value[2]:.4f})"
    if usd_type == "color3f[]":
        v = value[0]
        return f"[({v[0]:.4f}, {v[1]:.4f}, {v[2]:.4f})]"
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
        "color3f[]": Sdf.ValueTypeNames.Color3fArray,
        "token": Sdf.ValueTypeNames.Token,
        "bool": Sdf.ValueTypeNames.Bool,
    }.get(usd_type, Sdf.ValueTypeNames.Double)


def _gf_value(Gf, usd_type, val):
    if usd_type == "color3f":
        return Gf.Vec3f(*val)
    if usd_type == "color3f[]":
        return [Gf.Vec3f(*v) for v in val]
    return val


def _write_usda_text(out, desc, rows):
    # Build one merged prim tree so shared ancestors (e.g. /Plant/Pumps/P101)
    # are authored once, not repeated per property (which would duplicate prims).
    tree = {}
    for prim_path, prop, usd_type, val in rows:
        node = tree
        for seg in [s for s in prim_path.strip("/").split("/") if s]:
            node = node.setdefault(seg, {})
        node.setdefault("__props__", []).append((prop, usd_type, val))

    lines = ['#usda 1.0', '(', '    doc = "OPC UA -> OpenUSD live bindings (override layer)"', ')', '']

    def emit(node, name, indent):
        lines.append(f'{indent}over "{name}"')
        lines.append(f'{indent}{{')
        for prop, usd_type, val in node.get("__props__", []):
            lines.append(f'{indent}    {usd_type} {prop} = {_fmt_usda_value(usd_type, val)}')
        for child, cnode in node.items():
            if child == "__props__":
                continue
            emit(cnode, child, indent + "    ")
        lines.append(f'{indent}}}')

    for name, cnode in tree.items():
        emit(cnode, name, "")
        lines.append("")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


# --- live (OPC UA + pxr) ---------------------------------------------------
async def run_connect(url: str, pump_browse_name: str):
    try:
        from asyncua import Client, ua
    except ImportError:
        print("ERROR: --connect requires `asyncua` (pip install asyncua)", file=sys.stderr)
        return 2
    try:
        from pxr import Usd, Sdf, Gf  # noqa: F401
    except ImportError:
        print("ERROR: --connect requires `pxr` (OpenUSD python) to author live.usda", file=sys.stderr)
        return 2

    openusd_ns = "http://opcfoundation.org/UA/OpenUSD/"
    # Part 1 discovery: enumerate representations from Server/OpenUSD/Representations,
    # read each binding's SourceNodeId + Target* directly from the server, and
    # subscribe. No local descriptor and no domain knowledge is needed.
    async with Client(url=url) as client:
        ns_uris = await client.get_namespace_array()
        if openusd_ns not in ns_uris:
            print(f"ERROR: server does not expose {openusd_ns}", file=sys.stderr)
            return 3
        ns = ns_uris.index(openusd_ns)
        root = client.get_node(ua.NodeId("OpenUSD", ns))
        reps_folder = await _child_by_name(root, "Representations")
        if reps_folder is None:
            print("ERROR: Server/OpenUSD/Representations not found", file=sys.stderr)
            return 3

        stage = Usd.Stage.CreateNew(LIVE_USDA) if not os.path.exists(LIVE_USDA) else Usd.Stage.Open(LIVE_USDA)
        handler = _UsdHandler(stage, Sdf, Gf)
        sub = await client.create_subscription(500, handler)

        count = 0
        for rep in await reps_folder.get_children():
            rep_prim = await _read_named_value(rep, "PrimPath")
            for binding in await rep.get_children():
                props = await _children_by_name(binding)
                if "SourceNodeId" not in props:
                    continue  # e.g. DefaultInstanceBrowseName, not a binding
                src_id = await props["SourceNodeId"].read_value()
                target_prim = (await _read_value_or_none(props.get("TargetPrimPath"))) or rep_prim
                target_prop = await _read_value_or_none(props.get("TargetPropertyName"))
                scale = (await _read_value_or_none(props.get("Scale"))) or 1.0
                if not (src_id and target_prim and target_prop):
                    continue
                src_node = client.get_node(src_id)
                handler.map[src_node.nodeid] = {
                    "targetPrimPath": target_prim,
                    "targetPropertyName": target_prop,
                    "scale": scale,
                }
                await sub.subscribe_data_change(src_node)
                count += 1
        print(f"Subscribed {count} bindings via Server/OpenUSD/Representations; "
              f"writing {LIVE_USDA}. Ctrl+C to stop.")
        import asyncio
        try:
            await asyncio.sleep(float("inf"))
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
    return 0


class _UsdHandler:
    def __init__(self, stage, Sdf, Gf):
        self.stage, self.Sdf, self.Gf = stage, Sdf, Gf
        self.map = {}

    def datachange_notification(self, node, val, data):
        info = self.map.get(node.nodeid)
        if info is None:
            return
        # BadQualityAction: Skip on non-Good (asyncua exposes StatusCode on data).
        sc = getattr(getattr(data, "monitored_item", None), "Value", None)
        if sc is not None and getattr(sc, "StatusCode", None) is not None and sc.StatusCode.value != 0:
            return
        usd_type, usd_val = convert_by_target(info["targetPropertyName"], val, info.get("scale", 1.0))
        prim = self.stage.OverridePrim(info["targetPrimPath"])
        attr = prim.CreateAttribute(info["targetPropertyName"], _sdf_type(self.Sdf, usd_type))
        attr.Set(_gf_value(self.Gf, usd_type, usd_val))
        self.stage.GetRootLayer().Save()


async def _child_by_name(parent, browse_name):
    for child in await parent.get_children():
        bn = await child.read_browse_name()
        if bn.Name == browse_name:
            return child
    return None


async def _children_by_name(parent):
    out = {}
    for child in await parent.get_children():
        bn = await child.read_browse_name()
        out[bn.Name] = child
    return out


async def _read_named_value(parent, browse_name):
    child = await _child_by_name(parent, browse_name)
    return await child.read_value() if child is not None else None


async def _read_value_or_none(node):
    if node is None:
        return None
    try:
        return await node.read_value()
    except Exception:
        return None


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
