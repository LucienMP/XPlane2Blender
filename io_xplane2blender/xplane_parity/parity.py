"""
Visual parity check: does X-Plane draw an exported OBJ the way Blender shows the model?
See README.md. The "Check in X-Plane" button runs this; so can you:

    python parity.py run BLEND ROOT [--mode palette|textured|lights] [--dataref NAME=VALUE ...]
                         [--views VIEWS.json] [--work DIR] [--xplane DIR] [--blender EXE] [--skip-xplane]
    python parity.py sample [--blend PATH]           # a sample scene to try it on
    python parity.py cleanup [--xplane DIR]          # removes the plugin from X-Plane, restores its backups

run: exports ROOT with XPlane2Blender, screenshots it in X-Plane from each view, renders
the same views in Blender, compares, and writes report.txt and comparison.png into the
work folder. X-Plane must be closed. Lines starting with STATUS: tell a caller where it is.
Plain Python, no Blender modules: it starts Blender and X-Plane itself.
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
# The add-on's own folder (io_xplane2blender) and, in a checkout, the repository above it
ADDON = os.path.dirname(HERE)
REPO = os.path.dirname(ADDON)
DEFAULT_XPLANE = os.environ.get("XPLANE_DIR", r"E:\X-Plane 12")
DEFAULT_BLENDER = os.environ.get("BLENDER", "blender")
PLUGIN_NAME = "xp2b_parity"
TIMEOUT = 600
MODES = ("palette", "textured", "lights")

# Midnight at Shelton, WA (KSHN): its neighbouring tiles are installed, and the X-Plane 12
# instancing tests used it
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


def status(text):
    print(f"STATUS: {text}", flush=True)


class XPlane:
    """One X-Plane installation: where the plugin, backups and screenshots go"""

    def __init__(self, folder):
        self.folder = folder
        self.exe = os.path.join(folder, "X-Plane.exe")
        self.plugins = os.path.join(folder, "Resources", "plugins")
        self.plugin = os.path.join(self.plugins, PLUGIN_NAME)
        # Next to the plugins folder, on the same drive: renamed, never copied
        self.aside = os.path.join(folder, "Resources", "plugins_aside_xp2b")
        self.backup = os.path.join(HERE, "backup")
        self.screenshots = os.path.join(folder, "Output", "screenshots")

    def check(self):
        if not os.path.exists(self.exe):
            raise SystemExit(f"ERROR: no X-Plane.exe in {self.folder}. Set the X-Plane folder in the add-on preferences, or --xplane")

    @staticmethod
    def running():
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq X-Plane.exe"], capture_output=True,
                             text=True, errors="replace").stdout
        return "X-Plane.exe" in out

    def install(self):
        """Copies the bundled plugin into X-Plane and backs up what the runs change"""
        xpl = os.path.join(HERE, "plugin", "win.xpl")
        if not os.path.exists(xpl):
            raise SystemExit("ERROR: plugin/win.xpl is missing; build it with plugin\\build.bat PATH\\TO\\XPSDK430\\SDK")
        self.restore_other_plugins()
        if not os.path.exists(os.path.join(self.backup, "Log.txt")):
            os.makedirs(self.backup, exist_ok=True)
            shutil.copytree(os.path.join(self.folder, "Output", "preferences"), os.path.join(self.backup, "preferences"))
            shutil.copy(os.path.join(self.folder, "Log.txt"), self.backup)
        os.makedirs(os.path.join(self.plugin, "64"), exist_ok=True)
        os.makedirs(os.path.join(self.plugin, "objects"), exist_ok=True)
        target = os.path.join(self.plugin, "64", "win.xpl")
        if not os.path.exists(target) or os.path.getmtime(target) < os.path.getmtime(xpl):
            shutil.copy(xpl, target)

    def cleanup(self):
        self.restore_other_plugins()
        shutil.rmtree(self.plugin, ignore_errors=True)
        if os.path.exists(self.backup):
            # The preferences folder has subfolders too (plugins keep theirs there)
            shutil.copytree(os.path.join(self.backup, "preferences"), os.path.join(self.folder, "Output", "preferences"),
                            dirs_exist_ok=True)
            shutil.copy(os.path.join(self.backup, "Log.txt"), os.path.join(self.folder, "Log.txt"))
            shutil.rmtree(self.backup)
        print("cleaned up: plugin removed, preferences and Log.txt restored")

    def set_aside_other_plugins(self):
        """
        Other plugins draw windows and overlays into the screenshots, so their folders are
        renamed aside for the run and put back by restore_other_plugins()
        """
        os.makedirs(self.aside, exist_ok=True)
        moved = []
        for entry in os.listdir(self.plugins):
            path = os.path.join(self.plugins, entry)
            if entry in (PLUGIN_NAME, "PluginAdmin") or not os.path.isdir(path) or entry.startswith(("XPLM", "XPWidgets")):
                continue
            os.rename(path, os.path.join(self.aside, entry))
            moved.append(entry)
        print("plugins set aside:", ", ".join(moved) or "none")

    def restore_other_plugins(self):
        if not os.path.isdir(self.aside):
            return
        for entry in os.listdir(self.aside):
            os.rename(os.path.join(self.aside, entry), os.path.join(self.plugins, entry))
        os.rmdir(self.aside)

    # --- Web API --------------------------------------------------------------------------
    @staticmethod
    def web(method, path, body=None, timeout=10):
        conn = http.client.HTTPConnection("localhost", 8086, timeout=timeout)
        try:
            conn.request(method, path, body=json.dumps(body).encode() if body is not None else None,
                         headers={"Content-Type": "application/json"})
            resp = conn.getresponse()
            return resp.status, resp.read()
        finally:
            conn.close()

    def current_aircraft(self):
        """The loaded aircraft's path, or None if it can't be read"""
        import base64
        try:
            code, raw = self.web("GET", "/api/v2/datarefs?filter[name]=sim/aircraft/view/acf_relative_path")
            if code != 200:
                return None
            dataref_id = json.loads(raw)["data"][0]["id"]
            code, raw = self.web("GET", f"/api/v2/datarefs/{dataref_id}/value")
            if code != 200:
                return None
            value = json.loads(raw)["data"]
            if isinstance(value, str):
                value = base64.b64decode(value).split(b"\0", 1)[0].decode(errors="replace")
            return value
        except (OSError, ValueError, KeyError, IndexError):
            return None

    def post_flight(self):
        try:
            code, raw = self.web("POST", "/api/v3/flight", {"data": FLIGHT}, timeout=TIMEOUT)
        except http.client.RemoteDisconnected:
            return None  # X-Plane drops the connection once the new flight has loaded
        except OSError as e:
            return f"POST /api/v3/flight failed: {e}"
        if code >= 400:
            return f"POST /api/v3/flight: HTTP {code} {raw[:300]!r}"
        return None

    def start_flight(self, proc):
        status("X-Plane starting")
        deadline = time.time() + 300
        while time.time() < deadline:
            if proc.poll() is not None:
                return f"X-Plane exited early ({proc.returncode})"
            try:
                if self.web("GET", "/api/capabilities")[0] == 200:
                    break
            except OSError:
                pass
            time.sleep(3)
        else:
            return "Web API never answered (X-Plane Settings > Network: allow incoming traffic?)"
        status("X-Plane loading the flight")
        wanted = os.path.basename(FLIGHT["aircraft"]["path"])
        aircraft = None
        for attempt in range(3):
            error = self.post_flight()
            if error:
                return error
            # X-Plane may still apply the user's own start-up flight after ours (seen with a
            # "Start new flight" Flight Configuration); check what is loaded and ask again
            time.sleep(20)
            aircraft = self.current_aircraft()
            print(f"flight request {attempt + 1}: aircraft now {aircraft!r}", flush=True)
            if aircraft is None or aircraft.endswith(wanted):
                return None
        return f"X-Plane keeps loading {aircraft!r} instead of {wanted}"

    def wait_for_exit(self, proc, start, views):
        """
        Follows the plugin's log for progress. X-Plane can stop at a quit confirmation
        dialog, so it's force-closed 60 s after the plugin asked it to quit
        """
        asked = None
        log = os.path.join(self.plugin, "log.txt")
        last = ""
        while proc.poll() is None:
            text = open(log, errors="replace").read() if os.path.exists(log) else ""
            shots = text.count("command sim/operation/screenshot")
            line = f"X-Plane shooting view {min(shots + 1, views)} of {views}" if "camera taken" in text else "X-Plane waiting for the scenery"
            if line != last:
                status(line)
                last = line
            if asked is None and "quitting" in text:
                asked = time.time()
            if asked and time.time() - asked > 60:
                return "did not quit within 60 s of being asked (quit dialog?)"
            if time.time() - start > TIMEOUT:
                return "timed out"
            time.sleep(2)
        return f"exited {proc.returncode}"

    def set_preferences(self, prefs):
        """
        Sets X-Plane.prf entries for one run, e.g. renopt_shadow_quality_04=0 (scenery shadows
        off: settings.txt ties it to the SCENERY_SHADOWS condition). Returns the file's old text
        """
        path = os.path.join(self.folder, "Output", "preferences", "X-Plane.prf")
        original = open(path, encoding="utf-8", errors="surrogateescape").read()
        text = original
        for item in prefs:
            key, _, value = item.partition("=")
            lines = text.split("\n")
            for index, line in enumerate(lines):
                if line.split(" ", 1)[0] == key:
                    lines[index] = f"{key} {value}"
                    break
            else:
                raise SystemExit(f"ERROR: X-Plane.prf has no {key}")
            text = "\n".join(lines)
            print(f"X-Plane preference for this run: {key} {value}", flush=True)
        with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
            f.write(text)
        return original

    def restore_preferences(self, original):
        path = os.path.join(self.folder, "Output", "preferences", "X-Plane.prf")
        with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
            f.write(original)

    def run(self, work, view_names, set_aside=True, prefs=()):
        """One X-Plane run: screenshots of the model in work/ become work/xplane_<view>.png"""
        self.check()
        if self.running():
            raise SystemExit("ERROR: X-Plane is already running. Close it first: a second instance can't "
                             "use the Web API, and the flight request would change the running session")
        self.install()
        objects = os.path.join(self.plugin, "objects")
        for name in ("model.obj", "booth.obj", "palette.png"):
            shutil.copy(os.path.join(work, name), objects)
        for extra in glob.glob(os.path.join(work, "albedo.*")):
            shutil.copy(extra, objects)
        for name in ("VIEWS", "DATAREFS"):
            shutil.copy(os.path.join(work, name), self.plugin)
        if os.path.exists(os.path.join(self.plugin, "log.txt")):
            os.remove(os.path.join(self.plugin, "log.txt"))
        open(os.path.join(self.plugin, "ARMED"), "w").close()
        before = set(glob.glob(os.path.join(self.screenshots, "*.png")))
        start = time.time()
        if set_aside:
            self.set_aside_other_plugins()
        original_prefs = self.set_preferences(prefs) if prefs else None
        try:
            proc = subprocess.Popen([self.exe], cwd=self.folder)
            result = self.start_flight(proc) or self.wait_for_exit(proc, start, len(view_names))
            if proc.poll() is None:
                proc.kill()
                proc.wait()
                result += ", force-closed"
        finally:
            self.restore_other_plugins()
            if original_prefs is not None:
                self.restore_preferences(original_prefs)
        for name, target in (("log.txt", "plugin_log.txt"),):
            if os.path.exists(os.path.join(self.plugin, name)):
                shutil.copy(os.path.join(self.plugin, name), os.path.join(work, target))
        shutil.copy(os.path.join(self.folder, "Log.txt"), os.path.join(work, "XPlane_Log.txt"))
        shots = sorted(set(glob.glob(os.path.join(self.screenshots, "*.png"))) - before)
        print(f"X-Plane: {result} in {time.time() - start:.0f}s, {len(shots)} screenshots for {len(view_names)} views", flush=True)
        for shot, name in zip(shots, view_names):
            shutil.move(shot, os.path.join(work, f"xplane_{name}.png"))
        for extra in shots[len(view_names):]:
            shutil.move(extra, os.path.join(work, os.path.basename(extra)))
        if len(shots) < len(view_names):
            log = os.path.join(work, "plugin_log.txt")
            if os.path.exists(log):
                print(open(log, errors="replace").read()[-2000:])
            raise SystemExit("ERROR: X-Plane produced fewer screenshots than views; see plugin_log.txt in the work folder")


# --- Blender ----------------------------------------------------------------------------
def blender(exe, *args, blend=None):
    """Runs parity_blender.py in background Blender with the add-on loaded"""
    command = [exe, "-b", "--factory-startup", "--addons", "io_xplane2blender", "-noaudio"]
    if blend:
        command.append(blend)
    command += ["--python", os.path.join(HERE, "parity_blender.py"), "--", *args]
    env = dict(os.environ)
    if os.path.exists(os.path.join(REPO, "tests.py")) and "BLENDER_USER_SCRIPTS" not in env:
        # A checkout, not an installed add-on: the test runner knows how Blender finds it
        sys.path.insert(0, REPO)
        import tests
        env["BLENDER_USER_SCRIPTS"] = tests.blender_user_scripts()
    result = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            encoding="utf-8", errors="replace")
    for line in result.stdout.splitlines():
        if line.startswith(("SAMPLE", "EXPORTED", "RENDERED", "WARNING", "ERROR", "RESULT", "    ")) or ": agreement" in line \
                or ": lights" in line or ": texture" in line or "Traceback" in line:
            print(line, flush=True)
    if result.returncode != 0 or "Traceback" in result.stdout:
        print(result.stdout[-3000:], flush=True)
    return result.returncode


def png_size(path):
    with open(path, "rb") as f:
        header = f.read(24)
    return struct.unpack(">II", header[16:24])


# --- Commands ---------------------------------------------------------------------------
def cmd_run(args):
    blend = os.path.abspath(args.blend)
    name = args.name or os.path.splitext(os.path.basename(blend))[0]
    work = os.path.abspath(args.work) if args.work else os.path.join(HERE, "work", name)
    os.makedirs(work, exist_ok=True)
    status("exporting with XPlane2Blender")
    export_args = ["export", blend, args.root, work, "--mode", args.mode, "--views", os.path.abspath(args.views)]
    for item in args.dataref or []:
        export_args += ["--dataref", item]
    if blender(args.blender, *export_args):
        status("failed: export")
        return 1
    with open(os.path.join(work, "views_resolved.json"), encoding="utf-8") as f:
        view_names = [v["name"] for v in json.load(f)["views"]]
    if args.obj:
        # Test this OBJ instead of the export (same views, booth and textures)
        shutil.copy(os.path.abspath(args.obj), os.path.join(work, "model.obj"))
        print(f"testing {args.obj} instead of the export", flush=True)
    if not args.skip_xplane:
        XPlane(args.xplane).run(work, view_names, set_aside=not args.keep_plugins, prefs=args.xplane_pref or ())
    first = os.path.join(work, f"xplane_{view_names[0]}.png")
    if not os.path.exists(first):
        raise SystemExit(f"ERROR: no {first}; run without --skip-xplane first")
    width, height = png_size(first)
    if args.against:
        # X-Plane against X-Plane: another run's screenshots stand in for Blender's renders
        status("comparing with " + args.against)
        for name in view_names:
            shutil.copy(os.path.join(os.path.abspath(args.against), f"xplane_{name}.png"),
                        os.path.join(work, f"blender_{name}.png"))
    else:
        status("rendering in Blender")
        render_args = ["render", blend, args.root, work, "--mode", args.mode, "--size", f"{width}x{height}"]
        for item in args.condition or []:
            render_args += ["--condition", item]
        if blender(args.blender, *render_args):
            status("failed: render")
            return 1
    status("comparing")
    code = blender(args.blender, "compare", work, "--mode", args.mode)
    status("done " + ("PASS" if code == 0 else "FAIL"))
    print("report:", os.path.join(work, "report.txt"), flush=True)
    return code


def cmd_sample(args):
    folder = "sample" if args.kind == "basic" else f"sample_{args.kind}"
    blend = os.path.abspath(args.blend) if args.blend else os.path.join(HERE, "work", folder, "sample.blend")
    os.makedirs(os.path.dirname(blend), exist_ok=True)
    return blender(args.blender, "sample", blend, "--kind", args.kind)


def main():
    parser = argparse.ArgumentParser(prog="parity.py")
    parser.add_argument("--xplane", default=DEFAULT_XPLANE, help="X-Plane folder")
    parser.add_argument("--blender", default=DEFAULT_BLENDER, help="Blender executable")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("sample")
    p.add_argument("--blend")
    p.add_argument("--kind", choices=("basic", "static", "conditions"), default="basic",
                   help="basic: the general sample; static: #253's static keyframe tables; conditions: #284's IF / ELSE chains")
    sub.add_parser("install")
    sub.add_parser("cleanup")
    p = sub.add_parser("run")
    p.add_argument("blend")
    p.add_argument("root")
    p.add_argument("--mode", choices=MODES, default="palette")
    p.add_argument("--dataref", action="append", help="NAME=VALUE, the model's animation datarefs")
    p.add_argument("--views", default=os.path.join(HERE, "views.json"))
    p.add_argument("--work", help="work folder, default work/<blend name> next to this script")
    p.add_argument("--name", help="work folder name under work/")
    p.add_argument("--skip-xplane", action="store_true", help="reuse the X-Plane screenshots already in the work folder")
    p.add_argument("--keep-plugins", action="store_true", help="don't set other plugins aside during the run")
    p.add_argument("--condition", action="append", help="NAME=0|1: the state of an OBJ condition in this X-Plane run, for Blender's render")
    p.add_argument("--xplane-pref", action="append", help="KEY=VALUE: an X-Plane.prf entry for this run only, e.g. renopt_shadow_quality_04=0")
    p.add_argument("--obj", help="test this OBJ instead of the export")
    p.add_argument("--against", help="compare with the X-Plane screenshots in this other work folder instead of Blender's renders")
    args = parser.parse_args()
    if args.command == "sample":
        return cmd_sample(args)
    if args.command == "install":
        XPlane(args.xplane).check()
        return XPlane(args.xplane).install()
    if args.command == "cleanup":
        return XPlane(args.xplane).cleanup()
    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
