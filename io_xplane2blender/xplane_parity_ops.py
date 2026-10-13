"""
"Check in X-Plane": runs the visual parity check (xplane_parity/) on the active root
without leaving Blender, and opens the side-by-side comparison when it's done.
"""
import os
import subprocess
import sys
from typing import Dict, List, Optional

import bpy

from .xplane_ops import _get_active_root

PARITY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xplane_parity")
RESULT_TEXT = "xplane_parity_report"
# The last check, shown in the Scene panel: {"status", "work", "report"}
last_check: Dict[str, str] = {}

MODE_ITEMS = [
    ("palette", "Shapes", "Every material becomes a flat colour: shapes, positions, animation, show/hide and winding, compared exactly"),
    ("textured", "Textures", "The root's Default texture on the model: UV mapping and texture assignment, compared loosely"),
    ("lights", "Lights", "Only the lights: each one's position and colour against where Blender has it"),
]


class XPlane2BlenderPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    xplane_path: bpy.props.StringProperty(
        name="X-Plane Folder",
        description="Your X-Plane 12 installation, for 'Check in X-Plane'. Its Web API must be on (Settings > Network: allow incoming traffic)",
        subtype="DIR_PATH",
        default=os.environ.get("XPLANE_DIR", ""),
    )
    parity_set_aside_plugins: bpy.props.BoolProperty(
        name="Set other plugins aside during the check",
        description="Other plugins' windows would show in the screenshots. Their folders are renamed into Resources/plugins_aside_xp2b for the run and renamed back afterwards",
        default=True,
    )

    def draw(self, context):
        box = self.layout.box()
        box.label(text="Check in X-Plane")
        box.prop(self, "xplane_path")
        box.prop(self, "parity_set_aside_plugins")
        box.label(text="X-Plane must be closed while a check runs, and its Web API turned on.", icon="INFO")


def preferences(context) -> Optional[XPlane2BlenderPreferences]:
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon else None


def dataref_values(root) -> List[str]:
    """NAME=VALUE for every transform dataref under the root, at its current value (the pose on screen)"""
    objects = list(root.all_objects) if isinstance(root, bpy.types.Collection) else list(root.children_recursive)
    values = {}
    for obj in objects:
        holders = [obj.xplane]
        if obj.type == "ARMATURE":
            holders += [bone.xplane for bone in obj.data.bones]
        for holder in holders:
            for dataref in holder.datarefs:
                if dataref.path and dataref.anim_type == "transform" and dataref.path not in values:
                    values[dataref.path] = dataref.value
    return [f"{path}={value:g}" for path, value in values.items()]


class XPLANE_OT_check_in_xplane(bpy.types.Operator):
    """Export the active root, photograph it in X-Plane and compare with Blender's view of it (about three minutes; X-Plane must be closed)"""

    bl_idname = "xplane.check_in_xplane"
    bl_label = "Check in X-Plane"

    mode: bpy.props.EnumProperty(name="Check", items=MODE_ITEMS, default="palette")

    _timer = None
    _process = None
    _log = None
    _work = None

    @classmethod
    def poll(cls, context):
        return _get_active_root(context) is not None and not last_check.get("running")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "mode")
        root = _get_active_root(context)
        layout.label(text=f"Root: {root.name}, datarefs at their current values", icon="INFO")
        layout.label(text="X-Plane will start, run for about three minutes and quit.")

    def execute(self, context):
        prefs = preferences(context)
        # No preferences when the add-on runs from a checkout rather than an install: XPLANE_DIR then
        xplane_path = prefs.xplane_path if prefs and prefs.xplane_path else os.environ.get("XPLANE_DIR", "")
        xplane = os.path.abspath(bpy.path.abspath(xplane_path)) if xplane_path else ""
        if not os.path.exists(os.path.join(xplane, "X-Plane.exe")):
            self.report({"ERROR"}, "Set your X-Plane folder in Edit > Preferences > Add-ons > XPlane2Blender")
            return {"CANCELLED"}
        if not os.path.exists(os.path.join(PARITY_DIR, "plugin", "win.xpl")):
            self.report({"ERROR"}, "This build has no X-Plane plugin (xplane_parity/plugin/win.xpl)")
            return {"CANCELLED"}
        root = _get_active_root(context)
        name = bpy.path.clean_name(root.name)
        work = os.path.join(PARITY_DIR, "work", name)
        os.makedirs(work, exist_ok=True)
        # A copy of the scene as it is now, so nothing has to be saved
        copy = os.path.join(work, "model.blend")
        bpy.ops.wm.save_as_mainfile(filepath=copy, copy=True)

        command = [sys.executable, os.path.join(PARITY_DIR, "parity.py"),
                   "--xplane", xplane, "--blender", bpy.app.binary_path,
                   "run", copy, root.name, "--mode", self.mode, "--work", work]
        for item in dataref_values(root):
            command += ["--dataref", item]
        if prefs and not prefs.parity_set_aside_plugins:
            command.append("--keep-plugins")
        self._log = open(os.path.join(work, "run.log"), "w", encoding="utf-8")
        self._process = subprocess.Popen(command, stdout=self._log, stderr=subprocess.STDOUT, cwd=work)
        self._work = work
        last_check.update(running=True, status="starting", work=work, report="")
        self._timer = context.window_manager.event_timer_add(1.0, window=context.window)
        context.window_manager.modal_handler_add(self)
        self._set_status(context, "starting")
        return {"RUNNING_MODAL"}

    def _set_status(self, context, text):
        last_check["status"] = text
        try:
            context.workspace.status_text_set(f"Check in X-Plane: {text}")
        except (AttributeError, RuntimeError):
            pass

    def _latest_status(self):
        try:
            with open(os.path.join(self._work, "run.log"), encoding="utf-8", errors="replace") as f:
                lines = [l[len("STATUS: "):].strip() for l in f if l.startswith("STATUS: ")]
            return lines[-1] if lines else None
        except OSError:
            return None

    def modal(self, context, event):
        if event.type != "TIMER":
            return {"PASS_THROUGH"}
        status = self._latest_status()
        if status and status != last_check.get("status"):
            self._set_status(context, status)
            for area in context.screen.areas:
                area.tag_redraw()
        if self._process.poll() is None:
            return {"PASS_THROUGH"}
        return self._finish(context)

    def _finish(self, context):
        context.window_manager.event_timer_remove(self._timer)
        self._log.close()
        try:
            context.workspace.status_text_set(None)
        except (AttributeError, RuntimeError):
            pass
        report_path = os.path.join(self._work, "report.txt")
        report = open(report_path, encoding="utf-8").read() if os.path.exists(report_path) else ""
        passed = self._process.returncode == 0 and "RESULT: PASS" in report
        last_check.update(running=False, status="PASS" if passed else "FAIL", report=report)
        text = bpy.data.texts.get(RESULT_TEXT) or bpy.data.texts.new(RESULT_TEXT)
        text.clear()
        text.write(report or open(os.path.join(self._work, "run.log"), encoding="utf-8", errors="replace").read())
        comparison = os.path.join(self._work, "comparison.png")
        if os.path.exists(comparison):
            bpy.ops.xplane.open_parity_results("EXEC_DEFAULT", filepath=comparison)
            self.report({"INFO" if passed else "WARNING"},
                        f"Check in X-Plane: {'PASS' if passed else 'FAIL'}, see the '{RESULT_TEXT}' text block and the comparison image")
        else:
            self.report({"WARNING"}, f"Check in X-Plane did not finish; see the '{RESULT_TEXT}' text block")
        return {"FINISHED"}


class XPLANE_OT_open_parity_results(bpy.types.Operator):
    """Shows the last check's comparison image (Blender | X-Plane | differences in red, one row per view) in an Image Editor"""

    bl_idname = "xplane.open_parity_results"
    bl_label = "Show Comparison"

    filepath: bpy.props.StringProperty(options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return bool(cls.default_path())

    @classmethod
    def default_path(cls):
        work = last_check.get("work")
        path = os.path.join(work, "comparison.png") if work else ""
        return path if path and os.path.exists(path) else ""

    def execute(self, context):
        path = self.filepath or self.default_path()
        if not path:
            return {"CANCELLED"}
        image = bpy.data.images.get("xplane_parity_comparison")
        if image:
            bpy.data.images.remove(image)
        image = bpy.data.images.load(path)
        image.name = "xplane_parity_comparison"
        if bpy.app.background or context.window is None or context.screen is None:
            return {"FINISHED"}
        for area in context.screen.areas:
            if area.type == "IMAGE_EDITOR":
                area.spaces.active.image = image
                area.tag_redraw()
                return {"FINISHED"}
        try:
            bpy.ops.wm.window_new()
        except RuntimeError:
            return {"FINISHED"}
        area = context.window_manager.windows[-1].screen.areas[0]
        area.type = "IMAGE_EDITOR"
        area.spaces.active.image = image
        return {"FINISHED"}


def parity_layout(layout: bpy.types.UILayout, context) -> None:
    """The Scene panel's box"""
    box = layout.box()
    row = box.row(align=True)
    row.operator(XPLANE_OT_check_in_xplane.bl_idname, icon="RESTRICT_RENDER_OFF")
    row.operator(XPLANE_OT_open_parity_results.bl_idname, icon="IMAGE_DATA")
    if last_check.get("running"):
        box.label(text=f"Running: {last_check.get('status', '')}", icon="TIME")
    elif last_check.get("status"):
        passed = last_check["status"] == "PASS"
        box.label(text=f"Last check: {last_check['status']}", icon="CHECKMARK" if passed else "ERROR")
        for line in last_check.get("report", "").splitlines():
            if "<--" in line or "FAIL" in line:
                box.label(text=line.strip()[:90])


_classes = (XPlane2BlenderPreferences, XPLANE_OT_check_in_xplane, XPLANE_OT_open_parity_results)

register, unregister = bpy.utils.register_classes_factory(_classes)
