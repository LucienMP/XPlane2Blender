"""
Writes the two DSF text files for the instancing test and compiles them with Laminar's DSFTool:
dsf_full (10,000 copies of objects/test.obj beside KSHN runway 05) and dsf_empty (no objects).

    python gen_dsf.py PATH\TO\DSFTool.exe
"""
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SLAT, SLON, HDG = 47.2310765, -123.1565485, 67.87  # aircraft start, facing up runway 05
R = 6371000.0


def offset(lat, lon, fwd, right):
    h = math.radians(HDG)
    dn = fwd * math.cos(h) - right * math.sin(h)
    de = fwd * math.sin(h) + right * math.cos(h)
    return lat + math.degrees(dn / R), lon + math.degrees(de / (R * math.cos(math.radians(lat))))


HEAD = ["I", "800", "DSF2TEXT", "",
        "PROPERTY sim/planet earth", "PROPERTY sim/overlay 1", "PROPERTY sim/require_object 1/0",
        "PROPERTY sim/creation_agent XPlane2Blender-instancing-test",
        "PROPERTY sim/west -124", "PROPERTY sim/east -123", "PROPERTY sim/north 48", "PROPERTY sim/south 47", ""]
objects = []
for row in range(100):  # 100 x 100, 4 m apart, 60-456 m right of the centre line and ahead
    for col in range(100):
        lat, lon = offset(SLAT, SLON, 60 + col * 4.0, 60 + row * 4.0)
        objects.append(f"OBJECT 0 {lon:.8f} {lat:.8f} {HDG:.2f}")

for name, lines in (("dsf_full", HEAD + ["OBJECT_DEF objects/test.obj", ""] + objects), ("dsf_empty", HEAD)):
    os.makedirs(os.path.join(HERE, name), exist_ok=True)
    txt = os.path.join(HERE, name + ".txt")
    open(txt, "w", newline="\n").write("\n".join(lines) + "\n")
    subprocess.run([sys.argv[1], "--text2dsf", txt, os.path.join(HERE, name, "+47-124.dsf")], check=True)
