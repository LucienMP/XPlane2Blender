"""The starting point for the export process, the start of the addon"""

import os
import os.path
import re
import sys
from typing import IO, Any, Dict, List, Optional, Set

import bpy
import mathutils

import io_xplane2blender
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import xplane_library
from .xplane_config import getDebug
from . import xplane_helpers
from .xplane_helpers import XPlaneLogger, logger
from .xplane_types import xplane_file


EXPORT_LOG_NAME = "xplane2blender.log"


def objects_named_in_messages(
    messages: List[Dict[str, Any]], scene: bpy.types.Scene
) -> List[bpy.types.Object]:
    """
    The scene's objects whose names appear in the log messages (#140). Messages
    name the object they're about, in quotes or at the start, but don't carry it
    as data. A bone's name finds its armature. "Cube" isn't found in "Cube.001"
    """
    texts = [message["message"] for message in messages]

    def named(name: str) -> bool:
        pattern = re.compile(
            r"(?<![\w.\-])" + re.escape(name) + r"(?![\w\-]|\.\w)"
        )
        return any(pattern.search(text) for text in texts)

    return [
        obj
        for obj in scene.objects
        if named(obj.name)
        or (obj.type == "ARMATURE" and any(named(bone.name) for bone in obj.data.bones))
    ]


def select_objects(
    objects: List[bpy.types.Object], view_layer: bpy.types.ViewLayer
) -> int:
    """Selects only objects, the first one active. Returns how many could be selected"""
    for obj in view_layer.objects:
        obj.select_set(False, view_layer=view_layer)
    selected = 0
    for obj in objects:
        try:
            obj.select_set(True, view_layer=view_layer)
        except RuntimeError:
            # Not in this view layer
            continue
        if selected == 0:
            view_layer.objects.active = obj
        selected += 1
    return selected


class XPLANE_OT_open_export_log(bpy.types.Operator):
    """Shows the export log in a Text Editor, in a new window if there is none (#239)"""

    bl_idname = "xplane.open_export_log"
    bl_label = "Open Export Log"

    @classmethod
    def poll(cls, context):
        return EXPORT_LOG_NAME in bpy.data.texts

    def execute(self, context):
        text = bpy.data.texts[EXPORT_LOG_NAME]
        if bpy.app.background or context.window is None or context.screen is None:
            self.report({"WARNING"}, f"No window to show the '{EXPORT_LOG_NAME}' text block in")
            return {"CANCELLED"}
        for area in context.screen.areas:
            if area.type == "TEXT_EDITOR":
                area.spaces.active.text = text
                area.tag_redraw()
                return {"FINISHED"}
        try:
            bpy.ops.wm.window_new()
        except RuntimeError:
            self.report({"WARNING"}, f"Could not open a window for the '{EXPORT_LOG_NAME}' text block")
            return {"CANCELLED"}
        area = context.window_manager.windows[-1].screen.areas[0]
        area.type = "TEXT_EDITOR"
        area.spaces.active.text = text
        return {"FINISHED"}


class XPLANE_OT_select_log_objects(bpy.types.Operator):
    """Selects the objects named in the last export's errors, or in its warnings when there were no errors (#140)"""

    bl_idname = "xplane.select_log_objects"
    bl_label = "Select Objects In Log"

    @classmethod
    def poll(cls, context):
        return bool(logger.messages)

    def execute(self, context):
        messages = logger.findErrors() or logger.findWarnings()
        objects = objects_named_in_messages(messages, context.scene)
        selected = select_objects(objects, context.view_layer)
        self.report({"INFO"}, f"Selected {selected} object(s) named in the export log")
        return {"FINISHED"}


class XPLANE_MT_xplane_export_log(bpy.types.Menu):
    bl_idname = "XPLANE_MT_xplane_export_log"
    bl_label = "XPlane2Blender Export Log"

    def draw(self, context):
        layout = self.layout
        errors, warnings = logger.findErrors(), logger.findWarnings()
        layout.label(
            text=f"Export produced {len(errors)} error(s) and {len(warnings)} warning(s)",
            icon="ERROR" if errors else "INFO",
        )
        for message in (errors or warnings)[:3]:
            layout.label(text=message["message"][:90])
        layout.separator()
        layout.operator(XPLANE_OT_open_export_log.bl_idname, icon="TEXT")
        layout.operator(XPLANE_OT_select_log_objects.bl_idname, icon="RESTRICT_SELECT_OFF")


def showLogDialog():
    if not ("-b" in sys.argv or "--background" in sys.argv):
        bpy.ops.wm.call_menu(name="XPLANE_MT_xplane_export_log")


class ExportProgress:
    """
    Blender's progress cursor and the status bar's text while exporting (#354).
    Blender can't redraw panels during an operator, but it does update these
    """

    def __init__(self, context: bpy.types.Context):
        self.window_manager = context.window_manager
        self.workspace = context.workspace if context.window else None
        self.total = 0
        self.current = 0
        self.started = False

    def begin(self, total: int) -> None:
        self.total = max(total, 1)
        if self.window_manager and not bpy.app.background:
            self.window_manager.progress_begin(0, self.total)
            self.started = True

    def step(self, text: str) -> None:
        self.current += 1
        logger.info(f"{text} ({self.current}/{self.total})")
        if self.started:
            self.window_manager.progress_update(min(self.current, self.total))
        if self.workspace:
            try:
                self.workspace.status_text_set(
                    f"XPlane2Blender: {text} ({self.current}/{self.total})"
                )
            except (AttributeError, RuntimeError):
                self.workspace = None

    def end(self) -> None:
        if self.started:
            self.window_manager.progress_end()
            self.started = False
        if self.workspace:
            try:
                self.workspace.status_text_set(None)
            except (AttributeError, RuntimeError):
                pass
            self.workspace = None


class EXPORT_OT_ExportXPlane(bpy.types.Operator, ExportHelper):
    """Export to X-Plane Object file format (.obj)"""

    bl_idname = "export.xplane_obj"
    bl_label = "Export X-Plane Object"

    filename_ext = ".obj"

    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Filepath used for exporting the X-Plane file(s)",
        maxlen=1024,
        default="",
    )

    only_selected_roots: bpy.props.BoolProperty(
        name = "Only Selected Roots",
        description = "If true, only valid selected roots will be exported",
        default=False
    )

    export_is_relative: bpy.props.BoolProperty(
        name="Export Is Relative",
        description="Set to true when starting the export via the button (with or without the GUI on in case of unit testing)",
        default=False,
    )

    # Method: execute
    # Used from Blender when user invokes export.
    # Invokes the exporting.
    #
    # Parameters:
    #   context - Blender context object.
    def execute(self, context):
        # A progress cursor and status text, so a long export doesn't look frozen (#354)
        self._progress = ExportProgress(context)
        try:
            return self._execute(context)
        finally:
            self._progress.end()

    def _execute(self, context):
        # prepare logging
        self._startLogging()

        debug = getDebug()
        export_directory = self.properties.filepath

        if not self.properties.export_is_relative:
            export_directory = os.path.dirname(export_directory)
        else:
            if bpy.context.blend_data.filepath == "":
                # We can't just save files relative to nothing somewhere on a users HDD (bad usability!) so we say there is an error.
                logger.error(
                    "Save your blend file before using the '%s' button"
                    % io_xplane2blender.xplane_ops.SCENE_OT_export_to_relative_dir.bl_label
                )
                self._endLogging()
                showLogDialog()
                return {"CANCELLED"}

        if (
            bpy.context.scene.xplane.plugin_development
            and bpy.context.scene.xplane.dev_enable_breakpoints
        ):
            breakpoint()

        # store current frame as we will go back to it
        currentFrame = bpy.context.scene.frame_current

        # goto first frame so everything is in inital state
        bpy.context.scene.frame_set(frame=1)
        bpy.context.view_layer.update()

        roots = xplane_helpers.get_exportable_roots_in_scene(
            bpy.context.scene, bpy.context.view_layer
        )
        if self.only_selected_roots:
            roots = [
                root for root in roots
                if isinstance(root, bpy.types.Object) and root.select_get()
            ]
        # One step to collect and one to write each root
        self._progress.begin(2 * len(roots))
        xplaneFiles = xplane_file.createFilesFromBlenderRootObjects(
            bpy.context.scene,
            bpy.context.view_layer,
            self.only_selected_roots,
            on_root=lambda name: self._progress.step(f"Collecting {name}"),
        )
        exported = 0
        # (layer settings, absolute path) of each OBJ written, for library.txt
        self._written = []
        try:
            for xplaneFile in xplaneFiles:
                self._progress.step(f"Writing {xplaneFile.filename}")
                if not xplaneFile.get_xplane_objects():
                    logger.warn(f"{xplaneFile.filename} has nothing to export, skipped")
                    continue
                if not self._writeXPlaneFile(xplaneFile, export_directory):
                    if (
                        bpy.context.scene.xplane.plugin_development
                        and bpy.context.scene.xplane.dev_continue_export_on_error
                    ):
                        logger.info(
                            "Continuing export despite error in %s" % xplaneFile.filename
                        )
                        logger.clearMessages()
                        continue
                    else:
                        return self._cancel()
                else:
                    exported += 1
        finally:
            # return to stored frame
            bpy.context.scene.frame_set(frame=currentFrame)
            bpy.context.view_layer.update()

        if self._written and not logger.hasErrors():
            xplane_library.write_libraries(
                self._written,
                os.path.abspath(
                    os.path.join(
                        os.path.dirname(bpy.context.blend_data.filepath), export_directory
                    )
                ),
                bpy.path.basename(bpy.context.blend_data.filepath) or "untitled.blend",
                self._dry_run(),
            )

        if not xplaneFiles:
            logger.error(
                "Could not find any Exportable Collections or Objects, did you forget check 'Exportable Collection' or 'Exportable Object'?"
            )
            return self._cancel()
        elif logger.hasErrors():
            return self._cancel()
        else:
            logger.success("Export finished without errors")
            self._endLogging()
            self.report({"INFO"}, f"Exported {exported} X-Plane OBJ(s)")
            return {"FINISHED"}

    def _cancel(self) -> Set[str]:
        """Ends logging, and shows the errors to the user"""
        self._endLogging()
        # WARNING, since an ERROR report makes bpy.ops raise for scripts
        if logger.hasErrors():
            self.report(
                {"WARNING"},
                f"Export failed: {logger.findErrors()[0]['message']}"
                f" (see the '{EXPORT_LOG_NAME}' text block)",
            )
            # Leave the objects the errors are about selected (#140)
            select_objects(
                objects_named_in_messages(logger.findErrors(), bpy.context.scene),
                bpy.context.view_layer,
            )
            showLogDialog()
        else:
            self.report({"WARNING"}, "Export cancelled")
        return {"CANCELLED"}

    def _startLogging(self):
        debug = getDebug()
        logLevels = ["error", "warning"]

        self.logFile: Optional[IO[Any]] = None

        logger.clearTransports()
        logger.clearMessages()

        # in debug mode, we log everything
        if debug:
            logLevels.append("info")
            logLevels.append("success")

        # always log to internal text file and console
        logger.addTransport(
            XPlaneLogger.InternalTextTransport(EXPORT_LOG_NAME), logLevels
        )
        logger.addTransport(XPlaneLogger.ConsoleTransport(), logLevels)

        # log out to a file if logging is enabled
        if debug and bpy.context.scene.xplane.log:
            if bpy.context.blend_data.filepath != "":
                filepath = os.path.dirname(bpy.context.blend_data.filepath)
                # Something this? self.logfile = os.path.join(dir,name+'_'+time.strftime("%y-%m-%d-%H-%M-%S")+'_xplane2blender.log')
                self.logFile = open(
                    os.path.join(filepath, "xplane2blender.log"), "w", encoding="utf-8"
                )
                logger.addTransport(XPlaneLogger.FileTransport(self.logFile), logLevels)
            else:
                logger.error("Cannot create log file if .blend file is not saved")

    def _endLogging(self):
        if self.logFile:
            self.logFile.close()

    def _writeXPlaneFile(
        self, xplaneFile: xplane_file.XPlaneFile, directory: str
    ) -> bool:
        """
        Finally, at the end of it all, attempts to write an XPlaneFile.
        Returns False if there was a problem, else True
        """
        debug = getDebug()

        # only write layers that contain objects
        if not xplaneFile.get_xplane_objects():
            return False

        # Change any backslashes to foward slashes for file paths
        xplaneFile.filename = xplaneFile.filename.replace("\\", "/")

        if xplaneFile.filename.find("//") == 0:
            xplaneFile.filename = xplaneFile.filename.replace("//", "", 1)

        if os.path.isabs(xplaneFile.filename):
            logger.error(
                "Bad export path %s: File paths must be relative to the .blend file"
                % (xplaneFile.filename)
            )
            return False

        # Get the relative path
        # Append .obj if needed
        # Make paths based on the absolute path
        # Write
        relpath = os.path.normpath(os.path.join(directory, xplaneFile.filename))
        if os.path.splitext(relpath)[1].lower() != ".obj":
            relpath += ".obj"

        fullpath = os.path.abspath(
            os.path.join(os.path.dirname(bpy.context.blend_data.filepath), relpath)
        )
        xplaneFile.export_dir = os.path.dirname(fullpath)
        out = xplaneFile.write()

        if logger.hasErrors():
            return False

        if not self._dry_run():
            try:
                os.makedirs(os.path.dirname(fullpath), exist_ok=True)
            except OSError as e:
                logger.error(e)
            else:
                with open(fullpath, "w", encoding="utf-8") as objFile:
                    logger.info("Writing %s" % fullpath)
                    objFile.write(out)
                    logger.success("Wrote %s" % fullpath)
        else:
            logger.info('Skipped writing %s due to "Dry Run"' % (fullpath))

        self._written.append((xplaneFile.options, fullpath))
        return True

    @staticmethod
    def _dry_run() -> bool:
        return (
            bpy.context.scene.xplane.plugin_development
            and bpy.context.scene.xplane.dev_export_as_dry_run
        )

    def invoke(self, context, event):
        """
        Used from Blender when user hits the Export-Entry in the File>Export menu.
        Creates a file select window.
        """
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}


_classes = (
    XPLANE_OT_open_export_log,
    XPLANE_OT_select_log_objects,
    XPLANE_MT_xplane_export_log,
    EXPORT_OT_ExportXPlane,
)

register, unregister = bpy.utils.register_classes_factory(_classes)
