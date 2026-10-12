"""
Builds the EXPORT_SEASON test: four coloured boxes (spring green, summer red, autumn blue,
winter white) published under one library path by season, and DSFs that place that path
in front of the aircraft at Shelton, WA (47N), Nadi, Fiji (17.8S), Hobart (42.8S)
and Moorabbin, Melbourne (38.0S).

    python make_season_test.py PATH\\TO\\DSFTool.exe
"""
import math
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OBJ = os.path.join(HERE, "objects")
R = 6371000.0

# The coloured boxes come from make_visual_objects.py's write(); reuse its box OBJs by colour
COLOURS = {"spr": "green", "sum": "red", "fal": "blue", "win": "white"}
sys.argv_saved = sys.argv
sys.argv = [sys.argv[0], OBJ]
import make_visual_objects as mvo  # writes the visual objects, and gives us write()
sys.argv = sys.argv_saved
for season, colour in COLOURS.items():
    mvo.write(f"season_{season}", [colour], ["{TRIS0}"])

LIBRARY = ["A", "1200", "LIBRARY", ""] + [
    f"EXPORT_SEASON {season}\tlib/xp2btest/season_box.obj\tobjects/season_{season}.obj" for season in COLOURS
]
open(os.path.join(HERE, "season_library.txt"), "w", newline="\n").write("\n".join(LIBRARY) + "\n")


def bearing(lat1, lon1, lat2, lon2):
    y = math.sin(math.radians(lon2 - lon1)) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(
        math.radians(lat2)) * math.cos(math.radians(lon2 - lon1))
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def offset(lat, lon, hdg, fwd, right):
    h = math.radians(hdg)
    dn = fwd * math.cos(h) - right * math.sin(h)
    de = fwd * math.sin(h) + right * math.cos(h)
    return lat + math.degrees(dn / R), lon + math.degrees(de / (R * math.cos(math.radians(lat))))


SITES = {
    # name: runway threshold, far end
    "kshn": ((47.2309749, -123.1569165), (47.2361390, -123.1382110)),
    "nffn": ((-17.7727813, 177.4290957), (-17.7498943, 177.4475213)),
    "ymhb": ((-42.8282235, 147.5010241), (-42.8455863, 147.5246001)),  # Hobart, 42.8S
    "ymmb": ((-37.9721540, 145.0978984), (-37.9803148, 145.1059491)),  # Moorabbin, 38.0S
    # Open ocean at 45N and 45S, so no missing base scenery; flown with the seaplane
    "ocean45n": ((45.5, -150.5), (45.6, -150.5)),
    "ocean45s": ((-45.5, -150.5), (-45.4, -150.5)),
}
starts = {}
for name, ((lat1, lon1), (lat2, lon2)) in SITES.items():
    hdg = bearing(lat1, lon1, lat2, lon2)
    slat, slon = offset(lat1, lon1, hdg, 30, 0)
    starts[name] = {"latitude": round(slat, 7), "longitude": round(slon, 7), "heading_true": round(hdg, 2)}
    tile_lat, tile_lon = math.floor(slat), math.floor(slon)
    tile = f"{tile_lat:+03d}{tile_lon:+04d}"
    lines = ["I", "800", "DSF2TEXT", "",
             "PROPERTY sim/planet earth", "PROPERTY sim/overlay 1", "PROPERTY sim/require_object 1/0",
             "PROPERTY sim/creation_agent XPlane2Blender-season-test",
             f"PROPERTY sim/west {tile_lon}", f"PROPERTY sim/east {tile_lon + 1}",
             f"PROPERTY sim/north {tile_lat + 1}", f"PROPERTY sim/south {tile_lat}", "",
             "OBJECT_DEF lib/xp2btest/season_box.obj", ""]
    for right in (-5.0, 0.0, 5.0):
        lat, lon = offset(slat, slon, hdg, 30.0, right)
        lines.append(f"OBJECT 0 {lon:.8f} {lat:.8f} {hdg:.2f}")
    out_dir = os.path.join(HERE, f"dsf_season_{name}")
    os.makedirs(out_dir, exist_ok=True)
    txt = os.path.join(out_dir, f"{tile}.txt")
    open(txt, "w", newline="\n").write("\n".join(lines) + "\n")
    block = f"{math.floor(tile_lat / 10) * 10:+03d}{math.floor(tile_lon / 10) * 10:+04d}"
    subprocess.run([sys.argv[1], "--text2dsf", txt, os.path.join(out_dir, f"{tile}.dsf")], check=True,
                   stdout=subprocess.DEVNULL)
    starts[name]["tile"] = f"{block}/{tile}.dsf"
print(starts)
