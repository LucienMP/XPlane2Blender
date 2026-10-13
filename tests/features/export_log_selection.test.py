"""
After an export with errors, the objects the errors name are selected (#140), and
the log popup and scene panel offer "Open Export Log" (#239) and "Select Objects In Log"
"""
from pathlib import Path
from typing import List

import bpy

from io_xplane2blender import xplane_constants, xplane_export
from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers


def messages(*texts: str) -> List[dict]:
    return [{"type": "error", "message": text, "context": None} for text in texts]


class TestExportLogSelection(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        test_creation_helpers.delete_everything()
        self.root = test_creation_helpers.create_datablock_empty(
            test_creation_helpers.DatablockInfo("EMPTY", "root")
        )
        self.root.xplane.isExportableRoot = True
        self.root.xplane.layer.export_type = xplane_constants.EXPORT_TYPE_SCENERY
        self.cube = test_creation_helpers.create_datablock_mesh(
            test_creation_helpers.DatablockInfo(
                "MESH", "Cube", parent_info=test_creation_helpers.ParentInfo(self.root)
            )
        )
        self.cube_001 = test_creation_helpers.create_datablock_mesh(
            test_creation_helpers.DatablockInfo(
                "MESH", "Cube.001", parent_info=test_creation_helpers.ParentInfo(self.root)
            )
        )
        self.arm = test_creation_helpers.create_datablock_armature(
            test_creation_helpers.DatablockInfo(
                "ARMATURE", "arm", parent_info=test_creation_helpers.ParentInfo(self.root)
            )
        )
        self.bone_name = self.arm.data.bones[0].name
        self.light = test_creation_helpers.create_datablock_light(
            test_creation_helpers.DatablockInfo(
                "LIGHT", "lamp", parent_info=test_creation_helpers.ParentInfo(self.root)
            ),
            "POINT",
        )
        logger.clearMessages()

    def names(self, *texts: str) -> List[str]:
        return sorted(
            obj.name
            for obj in xplane_export.objects_named_in_messages(
                messages(*texts), bpy.context.scene
            )
        )

    def test_names_found_in_messages(self) -> None:
        self.assertEqual(self.names("Cube has no material"), ["Cube"])
        self.assertEqual(self.names("Material \"m\" in object \"Cube.001\" is bad"), ["Cube.001"])
        self.assertEqual(self.names("'Cube' and 'lamp' clash"), ["Cube", "lamp"])
        self.assertEqual(self.names("Nothing about any object"), [])
        self.assertEqual(self.names("Last word is Cube."), ["Cube"])

    def test_bone_name_finds_armature(self) -> None:
        self.assertEqual(self.names(f"Bone: {self.bone_name} has 2 datarefs"), ["arm"])

    def test_failed_export_selects_named_objects(self) -> None:
        self.light.data.xplane.type = xplane_constants.LIGHT_NAMED
        self.light.data.xplane.name = ""
        for obj in bpy.context.view_layer.objects:
            obj.select_set(True)
        result = bpy.ops.export.xplane_obj(filepath=str(get_tmp_folder() / Path("log_selection.obj")))
        self.assertEqual(result, {"CANCELLED"})
        self.assertTrue(logger.hasErrors())
        selected = sorted(obj.name for obj in bpy.context.view_layer.objects if obj.select_get())
        self.assertEqual(selected, ["lamp"])
        self.assertEqual(bpy.context.view_layer.objects.active, self.light)

    def test_select_log_objects_operator(self) -> None:
        logger.error("Cube.001 is upside down")
        logger.error("'arm' does not know what day it is")
        self.assertEqual(bpy.ops.xplane.select_log_objects(), {"FINISHED"})
        selected = sorted(obj.name for obj in bpy.context.view_layer.objects if obj.select_get())
        self.assertEqual(selected, ["Cube.001", "arm"])

    def test_open_log_cancels_without_window(self) -> None:
        if xplane_export.EXPORT_LOG_NAME not in bpy.data.texts:
            bpy.data.texts.new(xplane_export.EXPORT_LOG_NAME)
        # Background Blender has no window to show it in: no crash, cancelled
        self.assertEqual(bpy.ops.xplane.open_export_log(), {"CANCELLED"})


runTestCases([TestExportLogSelection])
