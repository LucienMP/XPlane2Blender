"""
Runs the X-Plane 12 tests (see README.md).

    python runner.py install            # back up, then copy the test scenery + plugin into X-Plane
    python runner.py run NAME [...]     # one X-Plane run each: a counting variant, "none", or "scene:<name>"
    python runner.py cleanup            # remove everything and restore the backups

X-Plane must be closed for install and cleanup. XPLANE_DIR overrides the X-Plane folder.
"""
import glob
import http.client
import json
import os
import shutil
import subprocess
import sys
import time

XP = os.environ.get("XPLANE_DIR", r"E:\X-Plane 12")
HERE = os.path.dirname(os.path.abspath(__file__))
PACK_NAME = "XP2B_instancing_test"
PACK = os.path.join(XP, "Custom Scenery", PACK_NAME)
PLUGIN = os.path.join(XP, "Resources", "plugins", PACK_NAME)
INI = os.path.join(XP, "Custom Scenery", "scenery_packs.ini")
BACKUP = os.path.join(HERE, "backup")
RESULTS = os.path.join(HERE, "results")
TIMEOUT = 600

FLIGHT = {
    "aircraft": {"path": "Aircraft/Laminar Research/Cessna 172 SP/Cessna_172SP.acf"},
    "lle_ground_start": {"latitude": 47.2310765, "longitude": -123.1565485, "heading_true": 67.87},
    "local_time": {"day_of_year": 172, "time_in_24_hours": 13.0},
    "weather": {
        "definition": "vfr_few_clouds",
        "vertical_speed_in_thermal_in_feet_per_minute": 0,
        "wave_height_in_meters": 0,
        "wave_direction_in_degrees": 0,
        "terrain_state": "dry",
        "variation_across_region_percentage": 0,
        "evolution_over_time_enum": "static",
    },
}


def install():
    # Back up what X-Plane or this test changes, unless an earlier install already did
    if not os.path.exists(os.path.join(BACKUP, "scenery_packs.ini")):
        os.makedirs(BACKUP, exist_ok=True)
        shutil.copy(INI, BACKUP)
        shutil.copytree(os.path.join(XP, "Output", "preferences"), os.path.join(BACKUP, "preferences"))
        shutil.copy(os.path.join(XP, "Log.txt"), os.path.join(BACKUP, "Log.txt"))
    os.makedirs(os.path.join(PACK, "Earth nav data", "+40-130"), exist_ok=True)
    os.makedirs(os.path.join(PACK, "objects"), exist_ok=True)
    for png in glob.glob(os.path.join(HERE, "objects", "*.png")):
        shutil.copy(png, os.path.join(PACK, "objects"))
    os.makedirs(os.path.join(PLUGIN, "64"), exist_ok=True)
    shutil.copy(os.path.join(HERE, "plugin", "win.xpl"), os.path.join(PLUGIN, "64", "win.xpl"))
    lines = open(INI, encoding="utf8").read().splitlines()
    entry = f"SCENERY_PACK Custom Scenery/{PACK_NAME}/"
    if entry not in lines:
        # First pack line = highest priority
        first = next(i for i, l in enumerate(lines) if l.startswith("SCENERY_PACK"))
        lines.insert(first, entry)
        open(INI, "w", encoding="utf8", newline="\n").write("\n".join(lines) + "\n")
    print("installed")


SLOTS = 6
EMPTY_OBJ = "I\n800\nOBJ\n\nPOINT_COUNTS\t0\t0\t0\t0\n"


def run(name):
    """
    One X-Plane run. name is a counting variant ("none" or an OBJ in objects/, placed 10,000 times)
    or "scene:<name>" from scenes.py: up to 6 OBJs side by side 30 m ahead, for screenshots,
    or a whole tile, library.txt and date for the season tests.
    """
    import copy
    import importlib
    flight = copy.deepcopy(FLIGHT)
    # Start each run with only the tiles and library it needs
    nav = os.path.join(PACK, "Earth nav data")
    shutil.rmtree(nav, ignore_errors=True)
    os.makedirs(os.path.join(nav, "+40-130"))
    library = os.path.join(PACK, "library.txt")
    if os.path.exists(library):
        os.remove(library)
    dsf = os.path.join(nav, "+40-130", "+47-124.dsf")
    if name.startswith("scene:"):
        scenes = importlib.import_module("scenes").SCENES
        scene = scenes[name[len("scene:"):]]
        flight["local_time"]["time_in_24_hours"] = scene.get("time", 13.0)
        flight["local_time"]["day_of_year"] = scene.get("day", 172)
        if "aircraft" in scene:
            flight["aircraft"] = {"path": scene["aircraft"]}
        if "start" in scene:
            flight["lle_ground_start"] = {k: scene["start"][k] for k in ("latitude", "longitude", "heading_true")}
        if "datarefs" in scene:  # the plugin sets these at X-Plane's start, before the flight loads
            with open(os.path.join(PLUGIN, "SETDREFS"), "w") as f:
                f.writelines(f"{k} {v}\n" for k, v in scene["datarefs"].items())
        if "redate" in scene:  # the plugin changes the date after the first screenshot
            open(os.path.join(PLUGIN, "REDATE"), "w").write(str(scene["redate"]))
        if "library" in scene:
            shutil.copy(os.path.join(HERE, scene["library"]), library)
        if "pack" in scene:  # files exported straight into a copy of the pack, e.g. by XPlane2Blender
            shutil.copytree(os.path.join(HERE, scene["pack"]), PACK, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("*.blend", "*.blend1"))
        for obj in scene.get("objects", ()):
            shutil.copy(os.path.join(HERE, "objects", f"{obj}.obj"), os.path.join(PACK, "objects", f"{obj}.obj"))
        if "tile" in scene:  # a whole tile from a DSF folder, e.g. ("dsf_season_nffn", "-20+170/-18+177.dsf")
            src_dir, tile = scene["tile"]
            os.makedirs(os.path.join(nav, os.path.dirname(tile)), exist_ok=True)
            shutil.copy(os.path.join(HERE, src_dir, os.path.basename(tile)), os.path.join(nav, tile))
            scene = dict(scene, slots=[])
        else:
            shutil.copy(os.path.join(HERE, "dsf_visual", "+47-124.dsf"), dsf)
        slots = list(scene["slots"]) + [None] * (SLOTS - len(scene["slots"]))
        for i, variant in enumerate(slots, start=1):
            target = os.path.join(PACK, "objects", f"slot{i}.obj")
            if variant:
                shutil.copy(os.path.join(HERE, "objects", f"{variant}.obj"), target)
            else:
                open(target, "w", newline="\n").write(EMPTY_OBJ)
    else:
        shutil.copy(os.path.join(HERE, "dsf_empty" if name == "none" else "dsf_full", "+47-124.dsf"), dsf)
        if name != "none":
            shutil.copy(os.path.join(HERE, "objects", f"{name}.obj"), os.path.join(PACK, "objects", "test.obj"))
    for f in ("log.txt", "datarefs.tsv"):
        p = os.path.join(PLUGIN, f)
        if os.path.exists(p):
            os.remove(p)
    # The plugin only acts when armed, and disarms itself
    open(os.path.join(PLUGIN, "ARMED"), "w").close()
    shots_before = set(glob.glob(os.path.join(XP, "Output", "screenshots", "*")))
    start = time.time()
    proc = subprocess.Popen([os.path.join(XP, "X-Plane.exe")], cwd=XP)
    status = start_flight(proc, flight) or wait_for_exit(proc, start)
    if proc.poll() is None:
        proc.kill()
        proc.wait()
        status += ", force-closed"
    out = os.path.join(RESULTS, name.replace(":", "_"))
    os.makedirs(out, exist_ok=True)
    for f in ("log.txt", "datarefs.tsv"):
        p = os.path.join(PLUGIN, f)
        if os.path.exists(p):
            shutil.copy(p, out)
    shutil.copy(os.path.join(XP, "Log.txt"), os.path.join(out, "XPlane_Log.txt"))
    for shot in set(glob.glob(os.path.join(XP, "Output", "screenshots", "*"))) - shots_before:
        shutil.move(shot, os.path.join(out, os.path.basename(shot)))
    print(f"{name}: {status} in {time.time() - start:.0f}s -> {out}", flush=True)


def wait_for_exit(proc, start):
    """
    Waits for X-Plane to quit after the plugin's run. X-Plane can stop at a quit
    confirmation dialog, so it's force-closed 60 s after the plugin asked it to quit
    """
    asked = None
    log = os.path.join(PLUGIN, "log.txt")
    while proc.poll() is None:
        if asked is None and os.path.exists(log) and "quitting" in open(log, errors="replace").read():
            asked = time.time()
        if asked and time.time() - asked > 60:
            return "did not quit within 60 s of being asked (quit dialog?)"
        if time.time() - start > TIMEOUT:
            return "timed out"
        time.sleep(2)
    return f"exited {proc.returncode}"


def web(method, path, body=None, timeout=10):
    """X-Plane's Web API (localhost:8086), as FSSR's tools/xplane/xpweb.py uses it"""
    conn = http.client.HTTPConnection("localhost", 8086, timeout=timeout)
    try:
        conn.request(method, path, body=json.dumps(body).encode() if body is not None else None,
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        return resp.status, resp.read()
    finally:
        conn.close()


def start_flight(proc, flight):
    """Waits for the Web API, then starts the test flight. Returns None, or why it failed."""
    deadline = time.time() + 300
    while time.time() < deadline:
        if proc.poll() is not None:
            return f"X-Plane exited early ({proc.returncode})"
        try:
            if web("GET", "/api/capabilities")[0] == 200:
                break
        except OSError:
            pass
        time.sleep(3)
    else:
        return "Web API never answered (Settings > Network: allow incoming traffic?)"
    try:
        status, raw = web("POST", "/api/v3/flight", {"data": flight}, timeout=TIMEOUT)
    except http.client.RemoteDisconnected:
        # X-Plane drops the connection once the new flight has loaded
        return None
    except OSError as e:
        return f"POST /api/v3/flight failed: {e}"
    if status >= 400:
        return f"POST /api/v3/flight: HTTP {status} {raw[:300]!r}"
    return None



def cleanup():
    shutil.rmtree(PACK, ignore_errors=True)
    shutil.rmtree(PLUGIN, ignore_errors=True)
    shutil.copy(os.path.join(BACKUP, "scenery_packs.ini"), INI)
    prefs = os.path.join(XP, "Output", "preferences")
    for f in os.listdir(os.path.join(BACKUP, "preferences")):
        shutil.copy(os.path.join(BACKUP, "preferences", f), os.path.join(prefs, f))
    shutil.copy(os.path.join(BACKUP, "Log.txt"), os.path.join(XP, "Log.txt"))
    # So the next install takes a fresh backup
    shutil.rmtree(BACKUP)
    print("cleaned up: pack and plugin removed; scenery_packs.ini, preferences and Log.txt restored")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "install":
        install()
    elif cmd == "run":
        for v in sys.argv[2:]:
            run(v)
    elif cmd == "cleanup":
        cleanup()
