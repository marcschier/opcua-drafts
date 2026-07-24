#!/usr/bin/env python3
"""Headless schematic renderer for the OPC UA -> OpenUSD robotics demo.

usdview is not always available. This script reads the composed stage when pxr is installed, or falls back to parsing live.usda, and writes a PNG schematic of the robot cell: two articulated arms, safety beacon, robot warning visibility, and the dynamic R1 gripper tool.

Usage:  python render_robot.py [stage.usda] [out.png]
Optional: pxr (usd-core), Pillow (or matplotlib fallback).
"""
from __future__ import annotations
import math
import os
import re
import sys

stage_path = sys.argv[1] if len(sys.argv) > 1 else "stage.usda"
out_path = sys.argv[2] if len(sys.argv) > 2 else "robot_render.png"

AXES = [
    ("Base/J1", "xformOp:rotateZ", 0.0),
    ("Base/J1/J2", "xformOp:rotateY", -30.0),
    ("Base/J1/J2/J3", "xformOp:rotateY", 45.0),
    ("Base/J1/J2/J3/J4", "xformOp:rotateX", 0.0),
    ("Base/J1/J2/J3/J4/J5", "xformOp:rotateY", 60.0),
    ("Base/J1/J2/J3/J4/J5/J6", "xformOp:rotateX", 0.0),
]


def _from_pxr(stage_file):
    from pxr import Usd
    s = Usd.Stage.Open(stage_file)

    def attr(path, name, default=None):
        p = s.GetPrimAtPath(path)
        if not p or not p.IsValid():
            return default
        a = p.GetAttribute(name)
        v = a.Get() if a else None
        return default if v is None else v

    data = {"robots": {}, "beacon": attr("/Cell/SafetyBeacon", "visibility", "invisible"), "tool": bool(s.GetPrimAtPath("/Cell/Robots/R1/Base/J1/J2/J3/J4/J5/J6/Flange/Tool"))}
    for robot in ("R1", "R2"):
        vals = []
        for rel, op, home in AXES:
            vals.append(float(attr(f"/Cell/Robots/{robot}/{rel}", op, home)))
        warning = attr(f"/Cell/Robots/{robot}/Warning", "visibility", "invisible")
        data["robots"][robot] = {"axes": vals, "warning": warning}
    return data


def _from_text(stage_file):
    live = os.path.join(os.path.dirname(os.path.abspath(stage_file)), "live.usda")
    txt = open(live, encoding="utf-8").read() if os.path.exists(live) else ""
    data = {"robots": {}, "beacon": "invisible", "tool": "Tool" in txt}
    m = re.search(r'visibility\s*=\s*"([^"]+)"', txt)
    if m:
        data["beacon"] = m.group(1)
    for robot in ("R1", "R2"):
        vals = []
        for _rel, op, home in AXES:
            # Values are emitted in descriptor order, so constrain only by op and consume progressively.
            vals.append(home)
        block = txt.split(f'over "{robot}"', 1)[1] if f'over "{robot}"' in txt else ""
        nums = re.findall(r'xformOp:rotate[XYZ]\s*=\s*([-+0-9.]+)', block)
        for i, n in enumerate(nums[:6]):
            vals[i] = float(n)
        wm = re.search(r'over "Warning"\s*\{[^}]*visibility\s*=\s*"([^"]+)"', block, re.S)
        data["robots"][robot] = {"axes": vals, "warning": wm.group(1) if wm else "invisible"}
    return data


def load_state(stage_file):
    try:
        return _from_pxr(stage_file), "pxr"
    except Exception as e:
        print(f"pxr stage read unavailable ({type(e).__name__}); using text fallback.")
        return _from_text(stage_file), "text"


def rgb(c):
    return tuple(int(255 * max(0, min(1, float(x)))) for x in c)


def arm_points(origin, axes, mirror=1):
    # Schematic 2D projection: use first three joints and keep wrist compact.
    a1, a2, a3, *_ = [math.radians(x) for x in axes]
    base = origin
    lengths = [70, 110, 90, 35]
    theta = a1
    pts = [base, (base[0], base[1] - lengths[0])]
    theta += -a2 * mirror
    pts.append((pts[-1][0] + lengths[1] * math.cos(theta), pts[-1][1] - lengths[1] * math.sin(theta)))
    theta += -a3 * mirror
    pts.append((pts[-1][0] + lengths[2] * math.cos(theta), pts[-1][1] - lengths[2] * math.sin(theta)))
    pts.append((pts[-1][0] + lengths[3] * math.cos(theta), pts[-1][1] - lengths[3] * math.sin(theta)))
    return pts


def draw_with_pillow(data, source):
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1100, 620
    img = Image.new("RGB", (W, H), (24, 26, 32))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 18)
        fsm = ImageFont.truetype("arial.ttf", 14)
        fbig = ImageFont.truetype("arialbd.ttf", 24)
    except Exception:
        font = fsm = fbig = ImageFont.load_default()
    d.text((24, 18), "OPC UA -> OpenUSD  |  robotics live composed stage", font=fbig, fill=(235, 235, 240))
    d.text((24, 52), f"stage: {stage_path} ({source})", font=fsm, fill=(150, 150, 160))
    d.rectangle([120, 130, 980, 530], outline=(210, 180, 40), width=3)
    beacon_on = data["beacon"] != "invisible"
    d.ellipse([520, 112, 580, 172], fill=(230, 20, 20) if beacon_on else (55, 35, 35), outline=(240, 240, 240), width=2)
    d.text((500, 178), f"SafetyBeacon visibility={data['beacon']}", font=fsm, fill=(190, 190, 200))
    for robot, origin, mirror in [("R1", (360, 465), 1), ("R2", (740, 465), -1)]:
        state = data["robots"].get(robot, {"axes": [0, -30, 45, 0, 60, 0], "color": (0, .55, .18)})
        warning_on = state.get("warning") != "invisible"
        pts = arm_points(origin, state["axes"], mirror)
        d.ellipse([origin[0]-35, origin[1]-18, origin[0]+35, origin[1]+18], fill=(0, 140, 46), outline=(230, 230, 230), width=2)
        if warning_on:
            d.ellipse([origin[0]-48, origin[1]-48, origin[0]+48, origin[1]+48], outline=(255, 30, 30), width=5)
        for a, b in zip(pts, pts[1:]):
            d.line([a, b], fill=(235, 150, 40), width=14)
            d.ellipse([b[0]-9, b[1]-9, b[0]+9, b[1]+9], fill=(210, 210, 220))
        if robot == "R1" and data.get("tool"):
            tip = pts[-1]
            d.rectangle([tip[0]+6, tip[1]-14, tip[0]+48, tip[1]+14], fill=(50, 55, 60), outline=(220, 220, 230))
            d.text((tip[0]+2, tip[1]+22), "dynamic Tool", font=fsm, fill=(150, 210, 150))
        d.text((origin[0]-80, origin[1]+35), f"{robot} Warning.visibility={state.get('warning')}", font=fsm, fill=(200, 200, 210))
        d.text((origin[0]-80, origin[1]+54), "A1..A6=" + ", ".join(f"{v:.1f}" for v in state["axes"]), font=fsm, fill=(150, 150, 160))
    d.text((24, H - 40), "MotionDeviceSystem -> MotionDevices references -> Axes  •  Rotation bindings drive joints  •  Warning.visibility shows e-stop", font=fsm, fill=(150, 150, 160))
    img.save(out_path)
    print("wrote", out_path)


def main():
    data, source = load_state(stage_path)
    try:
        draw_with_pillow(data, source)
        return 0
    except ImportError:
        print("No PNG backend available. Install Pillow (preferred) or open stage.usda in usdview/Omniverse.")
        print(data)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
