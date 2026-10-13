"""
Export progress (#354): each exportable root is reported before it is collected,
and the export operator's progress cursor and status text are no-ops in
background Blender
"""
from pathlib import Path
from typing import List

import bpy

from io_xplane2blender import xplane_constants, xplane_export
from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers
from io_xplane2blender.xplane_types import xplane_file


class TestExportProgress(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        test_creation_helpers.delete_everything()
        self.roots = []
        for name in ("root_a", "root_b"):
            root = test_creation_helpers.create_datablock_empty(
                test_creation_helpers.DatablockInfo("EMPTY", name)
            )
            root.xplane.isExportableRoot = True
            root.xplane.layer.export_type = xplane_constants.EXPORT_TYPE_SCENERY
            test_creation_helpers.create_datablock_mesh(
                test_creation_helpers.DatablockInfo(
                    "MESH", f"{name}_cube", parent_info=test_creation_helpers.ParentInfo(root)
                )
            )
            self.roots.append(root)
        # A non-root object is never reported
        test_creation_helpers.create_datablock_empty(
            test_creation_helpers.DatablockInfo("EMPTY", "not_a_root")
        )
        logger.clearMessages()

    def test_on_root_called_per_exportable_root(self) -> None:
        names: List[str] = []
        files = xplane_file.createFilesFromBlenderRootObjects(
            bpy.context.scene, bpy.context.view_layer, on_root=names.append
        )
        self.assertEqual(len(files), 2)
        self.assertEqual(sorted(names), ["root_a", "root_b"])

    def test_only_selected_roots_reports_only_those(self) -> None:
        for obj in bpy.context.view_layer.objects:
            obj.select_set(obj.name == "root_b")
        names: List[str] = []
        files = xplane_file.createFilesFromBlenderRootObjects(
            bpy.context.scene, bpy.context.view_layer, True, on_root=names.append
        )
        self.assertEqual(len(files), 1)
        self.assertEqual(names, ["root_b"])

    def test_progress_steps_counted_in_background(self) -> None:
        progress = xplane_export.ExportProgress(bpy.context)
        progress.begin(4)
        progress.step("Collecting root_a")
        progress.step("Writing root_a")
        self.assertEqual(progress.current, 2)
        self.assertEqual(progress.total, 4)
        progress.end()
        self.assertFalse(progress.started)

    def test_export_operator_still_exports(self) -> None:
        bpy.context.scene.xplane.plugin_development = True
        bpy.context.scene.xplane.dev_export_as_dry_run = True
        try:
            result = bpy.ops.export.xplane_obj(
                filepath=str(get_tmp_folder() / Path("progress.obj"))
            )
        finally:
            bpy.context.scene.xplane.dev_export_as_dry_run = False
            bpy.context.scene.xplane.plugin_development = False
        self.assertEqual(result, {"FINISHED"})
        self.assertFalse(logger.hasErrors())


runTestCases([TestExportProgress])
