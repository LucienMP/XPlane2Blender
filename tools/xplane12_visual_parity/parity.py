"""
Visual parity test: does X-Plane draw an OBJ the way Blender shows the model? See README.md.

    python parity.py sample                                  # makes work/sample/sample.blend
    python parity.py install                                 # copies the plugin into X-Plane, backs up its preferences
    python parity.py run BLEND ROOT [--dataref NAME=VALUE ...] [--views VIEWS.json] [--name NAME] [--skip-xplane]
    python parity.py cleanup                                 # removes the plugin, restores the backups

run: exports ROOT with XPlane2Blender, screenshots it in X-Plane from each view, renders the
same views in Blender, compares, and prints work/NAME/report.txt. X-Plane must be closed.
BLENDER and XPLANE_DIR override the default locations.
"""
import argparse
import glob
import http.client
import json
import os
import shutil
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
XP = os.environ.get("XPLANE_DIR", r"E:\X-Plane 12")
BLENDER = os.environ.get("BLENDER", r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
PLUGIN_NAME = "xp2b_parity"
PLUGIN = os.path.join(XP, "Resources", "plugins", PLUGIN_NAME)
BACKUP = os.path.join(HERE, "backup")
WORK = os.path.join(HERE, "work")
TIMEOUT = 600

# Midnight at Shelton, WA (KSHN), the instancing test's site: all its neighbouring tiles are installed
FLIGHT = {
    "aircraft": {"path": "Aircraft/Laminar Research/Cessna 172 SP/Cessna_172SP.acf"},
    "lle_ground_start": {"latitude": 47.2310765, "longitude": -123.1565485, "heading_true": 67.87},
    "local_time": {"day_of_year": 172, "time_in_24_hours": 0.5},
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


def blender_user_scripts():
    sys.path.insert(0, REPO)
    import tests  # the repo's test runner knows how Blender finds the add-on
    return tests.blender_user_scripts()


def blender(*args, blend=None):
    """Runs blender/parity_blender.py in background Blender with the add-on"""
    command = [BLENDER, "-b", "--factory-startup", "--addons", "io_xplane2blender", "-noaudio"]
    if blend:
        command.append(blend)
    command += ["--python", os.path.join(HERE, "blender", "parity_blender.py"), "--", *args]
    env = dict(os.environ, BLENDER_USER_SCRIPTS=blender_user_scripts())
    result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            encoding="utf-8", errors="replace")
    keep = [l for l in result.stdout.splitlines()
            if l.startswith(("SAMPLE", "EXPORTED", "RENDERED", "WARNING", "ERROR", "RESULT", "    ")) or ": agreement" in l
            or "Traceback" in l or "Error" in l]
    print("\n".join(keep))
    if result.returncode != 0 or "Traceback" in result.stdout:
        print(result.stdout[-3000:])
    return result.returncode


def png_size(path):
    with open(path, "rb") as f:
        header = f.read(24)
    return struct.unpack(">II", header[16:24])


# --- X-Plane --------------------------------------------------------------------------------
def install():
    xpl = os.path.join(HERE, "plugin", "win.xpl")
    if not os.path.exists(xpl):
        raise SystemExit("ERROR: build the plugin first: plugin\\build.bat PATH\\TO\\XPSDK430\\SDK")
    if not os.path.exists(os.path.join(BACKUP, "Log.txt")):
        os.makedirs(BACKUP, exist_ok=True)
        shutil.copytree(os.path.join(XP, "Output", "preferences"), os.path.join(BACKUP, "preferences"))
        shutil.copy(os.path.join(XP, "Log.txt"), BACKUP)
    restore_other_plugins()
    os.makedirs(os.path.join(PLUGIN, "64"), exist_ok=True)
    os.makedirs(os.path.join(PLUGIN, "objects"), exist_ok=True)
    shutil.copy(xpl, os.path.join(PLUGIN, "64", "win.xpl"))
    print("installed", PLUGIN)


KEEP_PLUGINS = {PLUGIN_NAME, "PluginAdmin"}
# Next to the plugins folder, on the same drive: a rename, never a copy and delete
ASIDE = os.path.join(XP, "Resources", "plugins_aside_xp2b")


def set_aside_other_plugins():
    """
    Other plugins draw windows and overlays into the screenshots, so their folders are
    renamed into Resources/plugins_aside_xp2b for the run and put back by
    restore_other_plugins(), which install, cleanup and the next run also do
    """
    plugins = os.path.join(XP, "Resources", "plugins")
    os.makedirs(ASIDE, exist_ok=True)
    moved = []
    for entry in os.listdir(plugins):
        path = os.path.join(plugins, entry)
        if entry in KEEP_PLUGINS or not os.path.isdir(path) or entry.startswith(("XPLM", "XPWidgets")):
            continue
        os.rename(path, os.path.join(ASIDE, entry))
        moved.append(entry)
    print("plugins set aside:", ", ".join(moved) or "none")


def restore_other_plugins():
    if not os.path.isdir(ASIDE):
        return
    plugins = os.path.join(XP, "Resources", "plugins")
    for entry in os.listdir(ASIDE):
        os.rename(os.path.join(ASIDE, entry), os.path.join(plugins, entry))
    os.rmdir(ASIDE)


def cleanup():
    restore_other_plugins()
    shutil.rmtree(PLUGIN, ignore_errors=True)
    if os.path.exists(BACKUP):
        # The preferences folder has subfolders too (plugins keep theirs there)
        shutil.copytree(os.path.join(BACKUP, "preferences"), os.path.join(XP, "Output", "preferences"),
                        dirs_exist_ok=True)
        shutil.copy(os.path.join(BACKUP, "Log.txt"), os.path.join(XP, "Log.txt"))
        shutil.rmtree(BACKUP)
    print("cleaned up: plugin removed, preferences and Log.txt restored")


def web(method, path, body=None, timeout=10):
    """X-Plane's Web API on localhost:8086"""
    conn = http.client.HTTPConnection("localhost", 8086, timeout=timeout)
    try:
        conn.request(method, path, body=json.dumps(body).encode() if body is not None else None,
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        return resp.status, resp.read()
    finally:
        conn.close()


def current_aircraft():
    """The loaded aircraft's path through the Web API, or None if it can't be read"""
    import base64
    try:
        status, raw = web("GET", "/api/v2/datarefs?filter[name]=sim/aircraft/view/acf_relative_path")
        if status != 200:
            return None
        dataref_id = json.loads(raw)["data"][0]["id"]
        status, raw = web("GET", f"/api/v2/datarefs/{dataref_id}/value")
        if status != 200:
            return None
        value = json.loads(raw)["data"]
        if isinstance(value, str):
            value = base64.b64decode(value).split(b"\0", 1)[0].decode(errors="replace")
        return value
    except (OSError, ValueError, KeyError, IndexError):
        return None


def post_flight():
    try:
        status, raw = web("POST", "/api/v3/flight", {"data": FLIGHT}, timeout=TIMEOUT)
    except http.client.RemoteDisconnected:
        return None  # X-Plane drops the connection once the new flight has loaded
    except OSError as e:
        return f"POST /api/v3/flight failed: {e}"
    if status >= 400:
        return f"POST /api/v3/flight: HTTP {status} {raw[:300]!r}"
    return None


def start_flight(proc):
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
    wanted = os.path.basename(FLIGHT["aircraft"]["path"])
    aircraft = None
    for attempt in range(3):
        error = post_flight()
        if error:
            return error
        # X-Plane may still apply the user's own start-up flight after ours (seen with a
        # "Start new flight" Flight Configuration); check what is loaded and ask again
        time.sleep(20)
        aircraft = current_aircraft()
        print(f"flight request {attempt + 1}: aircraft now {aircraft!r}", flush=True)
        if aircraft is None or aircraft.endswith(wanted):
            return None
    return f"X-Plane keeps loading {aircraft!r} instead of {wanted}"


def wait_for_exit(proc, start):
    """X-Plane can stop at a quit confirmation dialog; force-close 60 s after the plugin asked"""
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


def xplane_running():
    """True if an X-Plane process exists. A second instance can't bind the Web API port,
    stops at an alert, and the runner's flight request would go to the first one"""
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq X-Plane.exe"], capture_output=True,
                         text=True, errors="replace").stdout
    return "X-Plane.exe" in out


def run_xplane(work, view_names):
    """One X-Plane run: screenshots of the model in work/ become work/xplane_<view>.png"""
    if not os.path.exists(os.path.join(PLUGIN, "64", "win.xpl")):
        raise SystemExit("ERROR: run 'parity.py install' first")
    if xplane_running():
        raise SystemExit("ERROR: X-Plane is already running. Close it first: a second instance can't "
                         "use the Web API, and the flight request would change the running session")
    objects = os.path.join(PLUGIN, "objects")
    for name in ("model.obj", "booth.obj", "palette.png"):
        shutil.copy(os.path.join(work, name), objects)
    for name in ("VIEWS", "DATAREFS"):
        shutil.copy(os.path.join(work, name), PLUGIN)
    for name in ("log.txt",):
        if os.path.exists(os.path.join(PLUGIN, name)):
            os.remove(os.path.join(PLUGIN, name))
    open(os.path.join(PLUGIN, "ARMED"), "w").close()
    shots_dir = os.path.join(XP, "Output", "screenshots")
    before = set(glob.glob(os.path.join(shots_dir, "*.png")))
    start = time.time()
    restore_other_plugins()  # from a run that didn't get to restore them
    set_aside_other_plugins()
    try:
        proc = subprocess.Popen([os.path.join(XP, "X-Plane.exe")], cwd=XP)
        status = start_flight(proc) or wait_for_exit(proc, start)
        if proc.poll() is None:
            proc.kill()
            proc.wait()
            status += ", force-closed"
    finally:
        restore_other_plugins()
    shutil.copy(os.path.join(PLUGIN, "log.txt"), os.path.join(work, "plugin_log.txt"))
    shutil.copy(os.path.join(XP, "Log.txt"), os.path.join(work, "XPlane_Log.txt"))
    shots = sorted(set(glob.glob(os.path.join(shots_dir, "*.png"))) - before)
    print(f"X-Plane: {status} in {time.time() - start:.0f}s, {len(shots)} screenshots for {len(view_names)} views")
    for shot, name in zip(shots, view_names):
        shutil.move(shot, os.path.join(work, f"xplane_{name}.png"))
    for extra in shots[len(view_names):]:
        shutil.move(extra, os.path.join(work, os.path.basename(extra)))
    if len(shots) < len(view_names):
        print(open(os.path.join(work, "plugin_log.txt"), errors="replace").read()[-2000:])
        raise SystemExit("ERROR: X-Plane produced fewer screenshots than views; see plugin_log.txt")


# --- Commands -------------------------------------------------------------------------------
def cmd_sample(args):
    blend = os.path.join(WORK, "sample", "sample.blend")
    os.makedirs(os.path.dirname(blend), exist_ok=True)
    return blender("sample", blend)


def cmd_run(args):
    blend = os.path.abspath(args.blend)
    name = args.name or os.path.splitext(os.path.basename(blend))[0]
    work = os.path.join(WORK, name)
    os.makedirs(work, exist_ok=True)
    export_args = ["export", blend, args.root, work, "--views", os.path.abspath(args.views)]
    for item in args.dataref or []:
        export_args += ["--dataref", item]
    if blender(*export_args):
        return 1
    with open(os.path.join(work, "views_resolved.json"), encoding="utf-8") as f:
        view_names = [v["name"] for v in json.load(f)["views"]]
    if not args.skip_xplane:
        run_xplane(work, view_names)
    first = os.path.join(work, f"xplane_{view_names[0]}.png")
    if not os.path.exists(first):
        raise SystemExit(f"ERROR: no {first}; run without --skip-xplane first")
    width, height = png_size(first)
    if blender("render", blend, args.root, work, "--size", f"{width}x{height}"):
        return 1
    code = blender("compare", work)
    print("report:", os.path.join(work, "report.txt"))
    return code


def main():
    parser = argparse.ArgumentParser(prog="parity.py")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sample")
    sub.add_parser("install")
    sub.add_parser("cleanup")
    p = sub.add_parser("run")
    p.add_argument("blend")
    p.add_argument("root")
    p.add_argument("--dataref", action="append", help="NAME=VALUE, the model's animation datarefs")
    p.add_argument("--views", default=os.path.join(HERE, "views.json"))
    p.add_argument("--name", help="work folder name, default the .blend's name")
    p.add_argument("--skip-xplane", action="store_true", help="reuse the X-Plane screenshots already in the work folder")
    args = parser.parse_args()
    if args.command == "sample":
        return cmd_sample(args)
    if args.command == "install":
        return install()
    if args.command == "cleanup":
        return cleanup()
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
