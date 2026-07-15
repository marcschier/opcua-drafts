#!/usr/bin/env python3
"""Headless schematic renderer for the OPC UA -> OpenUSD pump demo.

usdview is not always available (the usd-core wheel ships pxr but not the GUI).
This renders the *composed* stage (Plant.usda + the connector's live.usda override,
plus pump.usda / remote-pump.usda references) to a PNG so the live-driven state is
viewable without a GUI: impeller angle, body colour, status light, and the
ProductionLine's aggregated pump instances (including the dynamic P_203).

Usage:  python render_pump.py [stage.usda] [out.png]
Requires: pxr (usd-core), Pillow.
"""
import sys
import math
from pxr import Usd, UsdGeom
from PIL import Image, ImageDraw, ImageFont

stage_path = sys.argv[1] if len(sys.argv) > 1 else "stage.usda"
out_path = sys.argv[2] if len(sys.argv) > 2 else "pump_render.png"

s = Usd.Stage.Open(stage_path)


def attr(path, name, default=None):
    p = s.GetPrimAtPath(path)
    if not p or not p.IsValid():
        return default
    a = p.GetAttribute(name)
    return a.Get() if a and a.HasAuthoredValue() or (a and a.Get() is not None) else default


def present(path):
    p = s.GetPrimAtPath(path)
    return bool(p and p.IsValid() and p.IsActive())


# --- read live-driven state from the composed stage ---
rotate_z = attr("/Plant/Pumps/P101/Impeller", "xformOp:rotateZ", 0.0) or 0.0
body_col = attr("/Plant/Pumps/P101/Body", "primvars:displayColor", [(0.4, 0.4, 0.9)])
body_rgb = tuple(int(255 * max(0.0, min(1.0, c))) for c in (body_col[0] if body_col else (0.4, 0.4, 0.9)))
emissive = attr("/Plant/Pumps/P101/StatusLight/Mat/Surface", "inputs:emissiveColor", (0, 0, 0)) or (0, 0, 0)
emis_rgb = tuple(int(255 * max(0.0, min(1.0, c))) for c in emissive)
light_vis = attr("/Plant/Pumps/P101/StatusLight", "visibility", "inherited")

line_pumps = [(name, present(f"/Plant/Line1/Pumps/{name}"))
              for name in ("P_201", "P_202", "P_203")]
remote = present("/Plant/Line1/RemotePump")

# --- draw ---
W, H = 1100, 620
img = Image.new("RGB", (W, H), (24, 26, 32))
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("arial.ttf", 18)
    fsm = ImageFont.truetype("arial.ttf", 14)
    fbig = ImageFont.truetype("arialbd.ttf", 24)
except Exception:
    font = fsm = fbig = ImageFont.load_default()

d.text((24, 18), "OPC UA -> OpenUSD  |  live composed stage", font=fbig, fill=(235, 235, 240))
d.text((24, 52), f"stage: {stage_path}", font=fsm, fill=(150, 150, 160))

# ---- Pump P101 (left) ----
cx, cy = 260, 300
# body (cylinder, coloured by bearing temperature -> displayColor)
d.rounded_rectangle([cx - 90, cy - 40, cx + 90, cy + 130], radius=18, fill=body_rgb, outline=(210, 210, 210), width=2)
d.text((cx - 90, cy + 138), f"Body.displayColor = {tuple(round(c,2) for c in body_col[0])}", font=fsm, fill=(190, 190, 200))

# impeller (rotated blades, angle from MassFlow)
ang = rotate_z if abs(rotate_z) > 0.01 else rotate_z * 1000  # exaggerate tiny rad for visibility
ix, iy, r = cx, cy - 90, 55
d.ellipse([ix - r, iy - r, ix + r, iy + r], outline=(180, 180, 190), width=2)
for k in range(4):
    a = ang + k * math.pi / 2
    d.line([ix, iy, ix + r * math.cos(a), iy + r * math.sin(a)], fill=(235, 235, 240), width=6)
d.ellipse([ix - 6, iy - 6, ix + 6, iy + 6], fill=(120, 120, 130))
d.text((ix - 80, iy - r - 26), f"Impeller.rotateZ = {rotate_z:.4f} rad", font=fsm, fill=(190, 190, 200))

# status light (alarm visibility + differential-pressure emissive)
lx, ly = cx + 120, cy - 60
glow = tuple(min(255, c + 40) for c in emis_rgb)
on = (light_vis != "invisible")
d.ellipse([lx - 22, ly - 22, lx + 22, ly + 22],
          fill=(glow if on else (40, 40, 46)), outline=(210, 210, 210), width=2)
d.text((lx - 44, ly + 28), f"StatusLight\nvis={light_vis}", font=fsm, fill=(190, 190, 200))

d.text((cx - 90, cy + 165), "Pump P101  (represented Object)", font=font, fill=(235, 235, 240))
d.text((cx - 90, cy + 190), "components: Impeller + Bearing (1:1 child prims)", font=fsm, fill=(150, 190, 150))

# ---- ProductionLine (right): 1..n aggregated pumps ----
d.text((640, 120), "ProductionLine  (aggregates 1..n pumps)", font=font, fill=(235, 235, 240))
bx, by = 640, 160
icons = list(line_pumps) + [("RemotePump", remote)]
for i, (name, act) in enumerate(icons):
    px = bx + (i % 3) * 140
    py = by + (i // 3) * 150
    col = (90, 160, 220) if act else (70, 70, 78)
    dyn = name == "P_203"
    rem = name == "RemotePump"
    d.rounded_rectangle([px, py, px + 110, py + 90], radius=12, fill=col, outline=(210, 210, 210), width=2)
    # little impeller glyph
    d.ellipse([px + 40, py + 20, px + 70, py + 50], outline=(240, 240, 245), width=2)
    d.line([px + 55, py + 35, px + 70, py + 35], fill=(240, 240, 245), width=3)
    d.line([px + 55, py + 35, px + 55, py + 20], fill=(240, 240, 245), width=3)
    label = name + ("  (dynamic)" if dyn else "  (cross-server)" if rem else "")
    d.text((px, py + 96), label, font=fsm, fill=(200, 200, 210) if act else (120, 120, 128))
    d.text((px, py + 112), "instanceable @pump.usda@" if act and not rem else ("@remote-pump.usda@" if rem else "inactive"),
           font=fsm, fill=(150, 170, 150) if act else (110, 110, 118))

# legend
d.text((24, H - 40), "1:1 child composition  •  1..n instanceable references  •  dynamic P_203 (model-change events)  •  cross-server federation",
       font=fsm, fill=(150, 150, 160))

img.save(out_path)
print("wrote", out_path)
print(f"  rotateZ={rotate_z:.4f}  body={body_rgb}  emissive={emis_rgb}  light={light_vis}")
print("  line pumps:", {n: a for n, a in line_pumps}, " remote:", remote)
