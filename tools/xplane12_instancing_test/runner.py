"""
Runs the instancing test in X-Plane 12 (see README.md).

    python runner.py install            # back up, then copy the test scenery + plugin into X-Plane
    python runner.py run VARIANT [...]  # one X-Plane run per OBJ variant ("none" = no objects)
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
TIMEOUT = 420

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
    shutil.copy(os.path.join(HERE, "objects", "tex.png"), os.path.join(PACK, "objects", "tex.png"))
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


def run(variant):
    # "none" places no objects at all; the others place 10,000 copies of the variant
    dsf = os.path.join(PACK, "Earth nav data", "+40-130", "+47-124.dsf")
    shutil.copy(os.path.join(HERE, "dsf_empty" if variant == "none" else "dsf_full", "+47-124.dsf"), dsf)
    if variant != "none":
        shutil.copy(os.path.join(HERE, "objects", f"{variant}.obj"), os.path.join(PACK, "objects", "test.obj"))
    for name in ("log.txt", "datarefs.tsv"):
        p = os.path.join(PLUGIN, name)
        if os.path.exists(p):
            os.remove(p)
    # The plugin only acts when armed, and disarms itself
    open(os.path.join(PLUGIN, "ARMED"), "w").close()
    shots_before = set(glob.glob(os.path.join(XP, "Output", "screenshots", "*")))
    start = time.time()
    proc = subprocess.Popen([os.path.join(XP, "X-Plane.exe")], cwd=XP)
    status = start_flight(proc)
    if status is None:
        try:
            proc.wait(timeout=max(30, TIMEOUT - (time.time() - start)))
            status = f"exited {proc.returncode}"
        except subprocess.TimeoutExpired:
            status = "timed out"
    if proc.poll() is None:
        quit_xplane(proc)
        status += ", closed by runner"
    out = os.path.join(RESULTS, variant)
    os.makedirs(out, exist_ok=True)
    for name in ("log.txt", "datarefs.tsv"):
        p = os.path.join(PLUGIN, name)
        if os.path.exists(p):
            shutil.copy(p, out)
    shutil.copy(os.path.join(XP, "Log.txt"), os.path.join(out, "XPlane_Log.txt"))
    for shot in set(glob.glob(os.path.join(XP, "Output", "screenshots", "*"))) - shots_before:
        shutil.move(shot, os.path.join(out, os.path.basename(shot)))
    print(f"{variant}: {status} in {time.time() - start:.0f}s -> {out}")


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


def start_flight(proc):
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
        status, raw = web("POST", "/api/v3/flight", {"data": FLIGHT}, timeout=TIMEOUT)
    except http.client.RemoteDisconnected:
        # X-Plane drops the connection once the new flight has loaded
        return None
    except OSError as e:
        return f"POST /api/v3/flight failed: {e}"
    if status >= 400:
        return f"POST /api/v3/flight: HTTP {status} {raw[:300]!r}"
    return None


def quit_xplane(proc):
    """Asks X-Plane to quit, as its window's close button does, then forces it"""
    subprocess.run(["taskkill", "/PID", str(proc.pid)], capture_output=True)
    try:
        proc.wait(timeout=90)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


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
