"""
Writes the OBJs for the visual scenes (scenes.py): boxes coloured by texture quadrant,
with the lights, conditionals or specular settings under test.

Texture quadrants (vtex.png): red (top left), green (top right), blue (bottom left), white (bottom right).
Each slot OBJ faces the camera: the camera is at the OBJ's local +Z.
"""
import os
import sys

from PIL import Image

out = sys.argv[1]
os.makedirs(out, exist_ok=True)

img = Image.new("RGBA", (256, 256))
px = img.load()
for y in range(256):
    for x in range(256):
        top, left = y < 128, x < 128
        px[x, y] = {
            (True, True): (230, 30, 30, 255),
            (True, False): (30, 200, 40, 255),
            (False, True): (30, 60, 230, 255),
            (False, False): (235, 235, 235, 255),
        }[(top, left)]
img.save(os.path.join(out, "vtex.png"))

# A flat normal map: RGB = straight-up normal, alpha = full specular (legacy normal map)
nrm = Image.new("RGBA", (64, 64), (128, 128, 255, 255))
nrm.save(os.path.join(out, "vtex_nml.png"))

# UV rectangles (u0, v0, u1, v1); v = 0 is the bottom of the image
QUAD = {"red": (0.02, 0.52, 0.48, 0.98), "green": (0.52, 0.52, 0.98, 0.98),
        "blue": (0.02, 0.02, 0.48, 0.48), "white": (0.52, 0.02, 0.98, 0.48)}


def box(colour, x0=0.0, size=3.0, height=3.0):
    """VT lines and clockwise indices (relative) for a box standing on the ground"""
    s = size / 2
    u0, v0, u1, v1 = QUAD[colour]
    faces = [
        ((0, 0, 1), [(x0 - s, 0, s), (x0 + s, 0, s), (x0 + s, height, s), (x0 - s, height, s)]),
        ((0, 0, -1), [(x0 + s, 0, -s), (x0 - s, 0, -s), (x0 - s, height, -s), (x0 + s, height, -s)]),
        ((1, 0, 0), [(x0 + s, 0, s), (x0 + s, 0, -s), (x0 + s, height, -s), (x0 + s, height, s)]),
        ((-1, 0, 0), [(x0 - s, 0, -s), (x0 - s, 0, s), (x0 - s, height, s), (x0 - s, height, -s)]),
        ((0, 1, 0), [(x0 - s, height, s), (x0 + s, height, s), (x0 + s, height, -s), (x0 - s, height, -s)]),
    ]
    uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    vt, idx = [], []
    for n, corners in faces:
        base = len(vt)
        for (x, y, z), (u, v) in zip(corners, uvs):
            vt.append(f"VT\t{x}\t{y}\t{z}\t{n[0]}\t{n[1]}\t{n[2]}\t{u}\t{v}")
        for a, b, c in ((0, 2, 1), (0, 3, 2)):
            idx += [base + a, base + b, base + c]
    return vt, idx


def write(name, boxes, commands, header_extra=()):
    """boxes: list of colours; commands may use {TRIS0}, {TRIS1}... for each box's TRIS line"""
    vt, idx, tris = [], [], []
    for colour in boxes:
        bvt, bidx = box(colour)
        offset = len(vt)
        start = len(idx)
        vt += bvt
        idx += [i + offset for i in bidx]
        tris.append(f"TRIS\t{start}\t{len(bidx)}")
    lines = ["I", "800", "OBJ", "", "TEXTURE\tvtex.png", *header_extra, "",
             f"POINT_COUNTS\t{len(vt)}\t0\t0\t{len(idx)}", ""] + vt + [""]
    for i in range(0, len(idx), 10):
        chunk = idx[i:i + 10]
        if len(chunk) == 10:
            lines.append("IDX10\t" + "\t".join(map(str, chunk)))
        else:
            lines += [f"IDX\t{v}" for v in chunk]
    lines.append("")
    lines += [c.format(**{f"TRIS{i}": t for i, t in enumerate(tris)}) for c in commands]
    with open(os.path.join(out, f"{name}.obj"), "w", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


LIGHT = "0\t3.5\t0"  # just above the box top; spot lights aim at the camera (+Z)

# --- #755 parameterized light intensity: "500cd" (what XPlane2Blender writes) vs "500" ---
write("v_control", ["white"], ["{TRIS0}"])
write("v_spot_500cd", ["white"], ["{TRIS0}", f"LIGHT_PARAM\tspot_params_bb_pm\t{LIGHT}\t1\t1\t1\t500cd\t0\t0\t1\t0.5"])
write("v_spot_500", ["white"], ["{TRIS0}", f"LIGHT_PARAM\tspot_params_bb_pm\t{LIGHT}\t1\t1\t1\t500\t0\t0\t1\t0.5"])
write("v_spot_50cd", ["white"], ["{TRIS0}", f"LIGHT_PARAM\tspot_params_bb_pm\t{LIGHT}\t1\t1\t1\t50cd\t0\t0\t1\t0.5"])
write("v_spot_50", ["white"], ["{TRIS0}", f"LIGHT_PARAM\tspot_params_bb_pm\t{LIGHT}\t1\t1\t1\t50\t0\t0\t1\t0.5"])
# Bare numbers on a ratio-like scale, in case that's what X-Plane expects without "cd"
write("v_spot_1", ["white"], ["{TRIS0}", f"LIGHT_PARAM\tspot_params_bb_pm\t{LIGHT}\t1\t1\t1\t1\t0\t0\t1\t0.5"])
write("v_spot_5", ["white"], ["{TRIS0}", f"LIGHT_PARAM\tspot_params_bb_pm\t{LIGHT}\t1\t1\t1\t5\t0\t0\t1\t0.5"])

# --- Custom spill: no dataref token (what XPlane2Blender writes) vs "none" (the spec) ---
write("v_spill_notoken", ["white"], ["{TRIS0}", f"LIGHT_SPILL_CUSTOM\t{LIGHT}\t1\t0.6\t0.2\t1\t6\t0\t-1\t0\t0.7 "])
write("v_spill_none", ["white"], ["{TRIS0}", f"LIGHT_SPILL_CUSTOM\t{LIGHT}\t1\t0.6\t0.2\t1\t6\t0\t-1\t0\t0.7\tnone"])

# --- #284 conditionals: red box when true, blue box otherwise ---
for var in ("VERSION10", "GLOBAL_LIGHTING", "GLOBAL_SHADOWS", "SCENERY_SHADOWS"):
    write(f"v_if_{var}", ["red", "blue"], [f"IF {var}", "{TRIS0}", "ELSE", "{TRIS1}", "ENDIF"])
# ELSE IF chain: red if not VERSION10, else green if GLOBAL_LIGHTING, else blue
write("v_elseif", ["red", "green", "blue"],
      ["IF NOT VERSION10", "{TRIS0}", "ELSE IF GLOBAL_LIGHTING", "{TRIS1}", "ELSE", "{TRIS2}", "ENDIF"])
# IF NOT: red if HDR (GLOBAL_LIGHTING) is off, else green
write("v_ifnot_GLOBAL_LIGHTING", ["red", "green"], ["IF NOT GLOBAL_LIGHTING", "{TRIS0}", "ELSE", "{TRIS1}", "ENDIF"])

# --- #461 specular with a (legacy) normal map ---
NML = "TEXTURE_NORMAL\tvtex_nml.png"
write("v_nml_none", ["white"], ["{TRIS0}"], [NML])
write("v_nml_shiny05", ["white"], ["ATTR_shiny_rat\t0.5", "{TRIS0}"], [NML])
write("v_nml_global1", ["white"], ["{TRIS0}"], [NML, "GLOBAL_specular\t1.0"])
write("v_nml_global0", ["white"], ["{TRIS0}"], [NML, "GLOBAL_specular\t0.0"])
write("v_plain_global1", ["white"], ["{TRIS0}"], ["GLOBAL_specular\t1.0"])

# --- #461 again, as panels angled to mirror the 13:00 sun into the camera ---
# Sun at azimuth 172.4, elevation 65.8 (recorded); camera behind, at the object's local +Z
import math

def write_panel(name, header_extra=(), before=()):
    n = (0.268, 0.607, 0.747)
    ln = math.sqrt(sum(c * c for c in n))
    n = tuple(c / ln for c in n)
    up = (0.0, 1.0, 0.0)
    u = (up[1] * n[2] - up[2] * n[1], up[2] * n[0] - up[0] * n[2], up[0] * n[1] - up[1] * n[0])  # up x n
    lu = math.sqrt(sum(c * c for c in u))
    u = tuple(c / lu for c in u)
    v = (n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2], n[0] * u[1] - n[1] * u[0])  # n x u
    c, h = (0.0, 2.5, 0.0), 2.0
    corners = [tuple(c[k] + a * u[k] * h + b * v[k] * h for k in range(3)) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    u0, v0, u1, v1 = QUAD["blue"]  # dark diffuse, so a specular highlight shows
    uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    vt = [f"VT\t{x:.4f}\t{y:.4f}\t{z:.4f}\t{n[0]:.4f}\t{n[1]:.4f}\t{n[2]:.4f}\t{s}\t{t}" for (x, y, z), (s, t) in zip(corners, uvs)]
    idx = [0, 2, 1, 0, 3, 2]
    lines = ["I", "800", "OBJ", "", "TEXTURE\tvtex.png", *header_extra, "", "POINT_COUNTS\t4\t0\t0\t6", ""] + vt
    lines += ["", *[f"IDX\t{i}" for i in idx], "", *before, "TRIS\t0\t6"]
    with open(os.path.join(out, f"{name}.obj"), "w", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

write_panel("v_glint_nml_none", [NML])
write_panel("v_glint_nml_global0", [NML, "GLOBAL_specular\t0.0"])
write_panel("v_glint_nml_global05", [NML, "GLOBAL_specular\t0.5"])
write_panel("v_glint_nml_global1", [NML, "GLOBAL_specular\t1.0"])
write_panel("v_glint_plain_none")
write_panel("v_glint_plain_global1", ["GLOBAL_specular\t1.0"])

# --- #621 mouse wheel on a drag-rotate manipulator ---
write("v_manip_rotate_wheel", ["green"],
      ["ATTR_manip_drag_rotate\thand\t0\t0\t0\t0\t1\t0\t0\t360\t0\t0\t360\t0\t0\tsim/graphics/animation/airport_beacon_rotation\tnone\tRotate",
       "ATTR_manip_wheel\t1", "{TRIS0}", "ATTR_manip_none"])
print("wrote visual objects to", out)

# --- Night scenes, round 2 ---
# An emissive box: keeps auto-exposure from brightening the night sky
write("v_anchor_lit", ["white"], ["{TRIS0}"], ["TEXTURE_LIT\tvtex.png"])
# Bigger, brighter custom spills: omnidirectional, white, 25 m
write("v_spill25_notoken", ["blue"], ["{TRIS0}", "LIGHT_SPILL_CUSTOM\t0\t3.5\t0\t1\t1\t1\t1\t25\t0\t0\t0\t1 "])
write("v_spill25_none", ["blue"], ["{TRIS0}", "LIGHT_SPILL_CUSTOM\t0\t3.5\t0\t1\t1\t1\t1\t25\t0\t0\t0\t1\tnone"])
write("v_spot_5000cd", ["blue"], ["{TRIS0}", "LIGHT_PARAM\tspot_params_bb_pm\t0\t3.5\t0\t1\t1\t1\t5000cd\t0\t0\t1\t0.5"])

# --- Round 3 ---
# Custom spills: size as a bare number (as XPlane2Blender writes it) vs candela
def spill(name, size, token):
    tail = f"\t{token}" if token else " "
    write(name, ["blue"], ["{TRIS0}", f"LIGHT_SPILL_CUSTOM\t0\t3.5\t0\t1\t1\t1\t1\t{size}\t0\t0\t0\t1{tail}"])
spill("v_spillB_notoken_5", "5", None)
spill("v_spillB_none_5", "5", "none")
spill("v_spillB_notoken_15", "15", None)
spill("v_spillB_none_15", "15", "none")
spill("v_spillB_none_500cd", "500cd", "none")
spill("v_spillB_none_5000cd", "5000cd", "none")

# Glint controls: a blue panel facing the camera straight on (should look blue, no glint)
def write_facing(name, header_extra=()):
    u0, v0, u1, v1 = QUAD["blue"]
    corners = [(-2, 0.5, 0), (2, 0.5, 0), (2, 4.5, 0), (-2, 4.5, 0)]
    uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    vt = [f"VT\t{x}\t{y}\t{z}\t0\t0\t1\t{s}\t{t}" for (x, y, z), (s, t) in zip(corners, uvs)]
    lines = ["I", "800", "OBJ", "", "TEXTURE\tvtex.png", *header_extra, "", "POINT_COUNTS\t4\t0\t0\t6", ""] + vt
    lines += ["", *[f"IDX\t{i}" for i in (0, 2, 1, 0, 3, 2)], "", "TRIS\t0\t6"]
    with open(os.path.join(out, f"{name}.obj"), "w", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
write_facing("v_facing_plain")
write_facing("v_facing_nml_global1", [NML, "GLOBAL_specular\t1.0"])
spill("v_spillB_notoken_5000cd", "5000cd", None)
spill("v_spillB_none_500", "500", "none")
