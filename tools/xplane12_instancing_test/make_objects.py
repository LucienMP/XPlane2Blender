"""Writes the test OBJ variants and their texture: a textured 3 m box, each variant adding one feature."""
import os
import sys

from PIL import Image

out = sys.argv[1]
os.makedirs(out, exist_ok=True)

# Checker texture, with a white disc in the top-right quarter for the custom billboard light
img = Image.new("RGBA", (256, 256))
px = img.load()
for y in range(256):
    for x in range(256):
        c = 220 if (x // 32 + y // 32) % 2 else 60
        px[x, y] = (c, c // 2, 40, 255)
for y in range(128):
    for x in range(128, 256):
        if (x - 192) ** 2 + (y - 64) ** 2 < 60 ** 2:
            px[x, y] = (255, 255, 255, 255)
img.save(os.path.join(out, "tex.png"))

# Box: 6 faces, 4 verts each, size 3 m, sitting on the ground (y = 0..3)
s, h = 1.5, 3.0
faces = [  # (normal, 4 corners counter-clockwise seen from outside)
    ((0, 0, 1), [(-s, 0, s), (s, 0, s), (s, h, s), (-s, h, s)]),
    ((0, 0, -1), [(s, 0, -s), (-s, 0, -s), (-s, h, -s), (s, h, -s)]),
    ((1, 0, 0), [(s, 0, s), (s, 0, -s), (s, h, -s), (s, h, s)]),
    ((-1, 0, 0), [(-s, 0, -s), (-s, 0, s), (-s, h, s), (-s, h, -s)]),
    ((0, 1, 0), [(-s, h, s), (s, h, s), (s, h, -s), (-s, h, -s)]),
    ((0, -1, 0), [(-s, 0, -s), (s, 0, -s), (s, 0, s), (-s, 0, s)]),
]
uvs = [(0, 0), (0.5, 0), (0.5, 0.5), (0, 0.5)]
vt, idx = [], []
for n, corners in faces:
    base = len(vt)
    for (x, y, z), (u, v) in zip(corners, uvs):
        vt.append(f"VT\t{x}\t{y}\t{z}\t{n[0]}\t{n[1]}\t{n[2]}\t{u}\t{v}")
    # X-Plane triangles are clockwise
    for a, b, c in ((0, 2, 1), (0, 3, 2)):
        idx += [base + a, base + b, base + c]

HEADER = ["I", "800", "OBJ", "", "TEXTURE\ttex.png", "TEXTURE_LIT\ttex.png", ""]
TOP = "0\t3.5\t0"

VARIANTS = {
    # name: (lines before TRIS, wrap in animation, lines after TRIS)
    "control": ([], False, []),
    "anim": ([], True, []),
    "anim_trans": ([], False, []),
    "anim_hide": ([], False, []),
    "attr_shiny_rat": (["ATTR_shiny_rat\t0.5"], False, []),
    "attr_hard": (["ATTR_hard"], False, []),
    "light_custom": ([], False, [f"LIGHT_CUSTOM\t{TOP}\t1\t1\t1\t1\t1\t0.5\t0.5\t1\t1\tNULL"]),
    "spill_custom_none": ([], False, [f"LIGHT_SPILL_CUSTOM\t{TOP}\t1\t1\t1\t1\t10\t0\t0\t0\t1\tnone"]),
    "spill_custom_dref": ([], False, [f"LIGHT_SPILL_CUSTOM\t{TOP}\t1\t1\t1\t1\t10\t0\t0\t0\t1\tsim/graphics/animation/lights/strobe"]),
    "named_hw_headlight": ([], False, [f"LIGHT_NAMED\theadlight\t{TOP}"]),
    "named_hw_obs_red_night": ([], False, [f"LIGHT_NAMED\tobs_red_night\t{TOP}"]),
    "named_sw_VASI": ([], False, [f"LIGHT_NAMED\tVASI\t{TOP}"]),
    "named_sw_airplane_beacon": ([], False, [f"LIGHT_NAMED\tairplane_beacon\t{TOP}"]),
    "param_hw_full_custom_halo": ([], False, [f"LIGHT_PARAM\tfull_custom_halo\t{TOP}\t1\t1\t1\t1\t5\t0\t0\t1\t1"]),
    "param_sw_airplane_beacon_rotate": ([], False, [f"LIGHT_PARAM\tairplane_beacon_rotate\t{TOP}\t1\t0"]),
}

for name, (before, anim, after) in VARIANTS.items():
    body = [f"POINT_COUNTS\t{len(vt)}\t0\t0\t{len(idx)}", ""] + vt + [""]
    for i in range(0, len(idx), 10):
        chunk = idx[i:i + 10]
        body.append(("IDX10\t" if len(chunk) == 10 else "IDX\t") + "\t".join(map(str, chunk)) if len(chunk) == 10
                    else "\n".join(f"IDX\t{v}" for v in chunk))
    body.append("")
    cmds = list(before)
    tris = f"TRIS\t0\t{len(idx)}"
    if name == "anim_trans":
        cmds += ["ANIM_begin", "ANIM_trans\t0\t0\t0\t0\t1\t0\t0\t10\tsim/time/total_running_time_sec", tris, "ANIM_end"]
    elif name == "anim_hide":
        cmds += ["ANIM_begin", "ANIM_hide\t-2\t-1\tsim/time/total_running_time_sec", tris, "ANIM_end"]
    elif anim:
        cmds += ["ANIM_begin", "ANIM_rotate\t0\t1\t0\t0\t360\t0\t10\tsim/time/total_running_time_sec", tris, "ANIM_end"]
    else:
        cmds.append(tris)
    cmds += after
    with open(os.path.join(out, f"{name}.obj"), "w", newline="\n") as f:
        f.write("\n".join(HEADER + body + cmds) + "\n")
print("wrote", len(VARIANTS), "variants to", out)
