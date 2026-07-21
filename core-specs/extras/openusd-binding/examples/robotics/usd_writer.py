#!/usr/bin/env python3
"""
OpenUSD reference writer for the OPC UA - OpenUSD Bindings Robotics Annex.

This consumes Robotics.OpenUsdBinding.json and authors a live USD override layer (`live.usda`) whose attributes are driven by OPC UA values. The connector is generic: it operates on representation and binding metadata, not on robot-specific code.

Two modes:
  * --demo      Author a deterministic live.usda from the descriptor (no server, no pxr required).
  * --connect URL
                Skeleton for a live OPC UA connector path (needs asyncua + pxr); discovery follows Server/OpenUSD/Representations like the pump writer.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DESCRIPTOR = os.path.join(HERE, "Robotics.OpenUsdBinding.json")
LIVE_USDA = os.path.join(HERE, "live.usda")


def load_descriptor(path=DESCRIPTOR):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def demo_joint_value(axis: dict, amplitude: float, period: float, phase_seconds: float, sample_seconds: float = 2.0):
    # Use a deterministic snapshot of the descriptor's sinusoidal simulation.
    angle = 2.0 * math.pi * ((sample_seconds + phase_seconds) / period)
    return axis["home"] + amplitude * math.sin(angle)


def demo_rows(desc: dict, emergency_stop: bool = False):
    sim = desc["simulation"]
    axes = desc["kinematics"]["axisTemplate"]
    rows = []  # (prim_path, prop, usd_type, value)
    references = []  # (prim_path, asset_reference, def_or_over)
    system_component = desc["representations"]["system"]["components"][0]
    robot_asset = system_component["componentAssetReference"]
    for robot in desc["representations"]["robots"]:
        browse = robot["browseName"]
        phase = sim["robotPhaseOffsetSeconds"].get(browse, 0.0)
        base = robot["primPath"].rstrip("/")
        references.append((base, robot_asset, "over"))
        for axis in axes:
            # Optional marker prims mirroring the generic connector's AxesAggregation child composition.
            rows.append((f"{base}/{axis['name']}", "", "", None))
            prim = f"{base}/{axis['linkPrimPath']}"
            value = demo_joint_value(axis, sim["sweepAmplitudeDeg"], sim["sweepPeriodSeconds"], phase)
            rows.append((prim, axis["rotateOp"], "double", value))
    beacon = desc["representations"]["system"]["bindings"][0]["targetPrimPath"]
    rows.append((beacon, "visibility", "token", "inherited" if emergency_stop else "invisible"))
    warning_visibility = "inherited" if emergency_stop else "invisible"
    for robot in desc["representations"]["robots"]:
        for binding in robot.get("bindings", []):
            if binding["name"] == "EmergencyStopWarning":
                rows.append((binding["targetPrimPath"], binding["targetPropertyName"], "token", warning_visibility))
    command = next(b for b in desc["representations"]["system"]["bindings"] if b["name"] == "SpeedOverrideCommand")
    rows.append((command["targetPrimPath"], command["targetPropertyName"], "double", 75.0))
    tool = next(c for c in desc["representations"]["robots"][0]["components"] if c["name"] == "GripperTool")
    references.append((tool["targetPrimPath"], tool["componentAssetReference"], "def"))
    return rows, references


def write_demo(desc: dict, out=LIVE_USDA, emergency_stop: bool = False):
    rows, references = demo_rows(desc, emergency_stop)
    try:
        from pxr import Usd  # noqa: F401
        _write_usda_text(out, rows, references)
        stage = Usd.Stage.Open(out)
        if stage is None:
            raise RuntimeError("Usd.Stage.Open returned None")
        print(f"[pxr] wrote and validated {out} with {len(rows)} authored opinions and references")
    except Exception as e:
        _write_usda_text(out, rows, references)
        print(f"[fallback] wrote {out} with {len(rows)} authored opinions and references ({type(e).__name__})")


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


def _fmt(usd_type, value):
    if usd_type == "color3f":
        return f"({value[0]:.4f}, {value[1]:.4f}, {value[2]:.4f})"
    if usd_type == "color3f[]":
        v = value[0]
        return f"[({v[0]:.4f}, {v[1]:.4f}, {v[2]:.4f})]"
    if usd_type == "double3":
        return f"({value[0]:.4f}, {value[1]:.4f}, {value[2]:.4f})"
    if usd_type == "uniform token[]":
        return "[" + ", ".join(f'"{v}"' for v in value) + "]"
    if usd_type == "token":
        return f'"{value}"'
    if usd_type == "bool":
        return "true" if value else "false"
    return f"{float(value):.4f}"


def _write_usda_text(out, rows, references):
    tree = {}
    for prim_path, prop, usd_type, val in rows:
        node = tree
        for seg in [s for s in prim_path.strip("/").split("/") if s]:
            node = node.setdefault(seg, {})
        if prop:
            node.setdefault("__props__", []).append((prop, usd_type, val))
    for prim_path, asset_ref, specifier in references:
        node = tree
        for seg in [s for s in prim_path.strip("/").split("/") if s]:
            node = node.setdefault(seg, {})
        node["__reference__"] = asset_ref
        node["__specifier__"] = specifier

    lines = ['#usda 1.0', '(', '    doc = "OPC UA -> OpenUSD robotics live bindings (override layer)"', ')', '']

    def emit(node, name, indent):
        ref = node.get("__reference__")
        specifier = node.get("__specifier__", "over")
        if ref:
            if specifier == "def":
                lines.append(f'{indent}def Xform "{name}" (')
            else:
                lines.append(f'{indent}over "{name}" (')
            lines.append(f'{indent}    prepend references = {ref}')
            lines.append(f'{indent})')
        else:
            lines.append(f'{indent}over "{name}"')
        lines.append(f'{indent}{{')
        for prop, usd_type, val in node.get("__props__", []):
            prefix = "" if usd_type in ("double3", "uniform token[]") or prop.startswith("xformOp:") else "custom "
            lines.append(f'{indent}    {prefix}{usd_type} {prop} = {_fmt(usd_type, val)}')
        for child, cnode in node.items():
            if child.startswith("__"):
                continue
            emit(cnode, child, indent + "    ")
        lines.append(f'{indent}}}')

    for name, cnode in tree.items():
        emit(cnode, name, "")
        lines.append("")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))


async def run_connect(url: str):
    try:
        import asyncua  # noqa: F401
    except ImportError:
        print("ERROR: --connect requires `asyncua` (pip install asyncua)", file=sys.stderr)
        return 2
    try:
        from pxr import Usd  # noqa: F401
    except ImportError:
        print("ERROR: --connect requires `pxr` (OpenUSD python) to author live.usda", file=sys.stderr)
        return 2
    print(f"Connect skeleton for {url}: discover Server/OpenUSD/Representations, subscribe, and write target USD attributes.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="OPC UA -> OpenUSD live writer (Robotics demo)")
    ap.add_argument("--demo", action="store_true", help="author a static live.usda (no server)")
    ap.add_argument("--connect", metavar="URL", help="opc.tcp:// server URL for live authoring")
    ap.add_argument("--emergency-stop", action="store_true", help="demo e-stop active state (warning prims and beacon visible)")
    args = ap.parse_args(argv)
    desc = load_descriptor()
    if args.connect:
        import asyncio
        return asyncio.run(run_connect(args.connect))
    write_demo(desc, emergency_stop=args.emergency_stop)
    return 0


if __name__ == "__main__":
    sys.exit(main())
