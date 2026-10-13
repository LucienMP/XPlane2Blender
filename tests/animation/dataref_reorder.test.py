"""
Reordering datarefs with the panel's arrows (#401): a dataref keeps its keyframes
when it moves, and Show/Hide are written in the list's order. Also the Unit Scale
warning (#466)
"""
from pathlib import Path
from typing import List

import bpy

from io_xplane2blender import xplane_constants, xplane_helpers
from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers
from io_xplane2blender.xplane_helpers import get_action_fcurves


class TestDatarefReorder(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        test_creation_helpers.delete_everything()
        self.root = test_creation_helpers.create_datablock_empty(
            test_creation_helpers.DatablockInfo("EMPTY", "root")
        )
        self.root.xplane.isExportableRoot = True
        self.root.xplane.layer.export_type = xplane_constants.EXPORT_TYPE_AIRCRAFT
        self.cube = test_creation_helpers.create_datablock_mesh(
            test_creation_helpers.DatablockInfo(
                "MESH", "cube", parent_info=test_creation_helpers.ParentInfo(self.root)
            )
        )
        self.arm = test_creation_helpers.create_datablock_armature(
            test_creation_helpers.DatablockInfo(
                "ARMATURE", "arm", parent_info=test_creation_helpers.ParentInfo(self.root)
            )
        )
        self.bone = self.arm.data.bones[0]
        logger.clearMessages()

    def _key_datarefs(self, datarefs, add_keyframe) -> None:
        """Datarefs a, b, c with values 1/2/3 on frame 1 and 10/20/30 on frame 10"""
        for path in "abc":
            datarefs.add().path = path
        for frame, factor in ((1, 1), (10, 10)):
            bpy.context.scene.frame_set(frame)
            for i, dataref in enumerate(datarefs):
                dataref.value = (i + 1) * factor
                add_keyframe(i)

    def _fcurve_values(self, anim_data, prefix) -> dict:
        return {
            fcurve.data_path[len(prefix) :]: [kf.co[1] for kf in fcurve.keyframe_points]
            for fcurve in get_action_fcurves(anim_data)
            if fcurve.data_path.startswith(prefix)
        }

    def test_object_dataref_moves_with_keyframes(self) -> None:
        obj = self.cube
        bpy.context.view_layer.objects.active = obj
        obj.keyframe_insert("location", frame=1)

        def add_keyframe(index):
            with bpy.context.temp_override(object=obj):
                bpy.ops.object.add_xplane_dataref_keyframe(index=index)

        self._key_datarefs(obj.xplane.datarefs, add_keyframe)
        with bpy.context.temp_override(object=obj):
            bpy.ops.object.move_xplane_dataref(index=0, direction="DOWN")
        self.assertEqual([d.path for d in obj.xplane.datarefs], ["b", "a", "c"])
        self.assertEqual(
            self._fcurve_values(obj.animation_data, "xplane.datarefs"),
            {"[0].value": [2, 20], "[1].value": [1, 10], "[2].value": [3, 30]},
        )
        with bpy.context.temp_override(object=obj):
            bpy.ops.object.move_xplane_dataref(index=2, direction="UP")
            # The ends don't move
            bpy.ops.object.move_xplane_dataref(index=0, direction="UP")
            bpy.ops.object.move_xplane_dataref(index=2, direction="DOWN")
        self.assertEqual([d.path for d in obj.xplane.datarefs], ["b", "c", "a"])
        self.assertEqual(
            self._fcurve_values(obj.animation_data, "xplane.datarefs"),
            {"[0].value": [2, 20], "[1].value": [3, 30], "[2].value": [1, 10]},
        )

    def test_bone_dataref_moves_with_keyframes(self) -> None:
        arm, bone = self.arm, self.bone
        bpy.context.view_layer.objects.active = arm
        arm.data.bones.active = bone
        arm.pose.bones[bone.name].keyframe_insert("location", frame=1)

        def add_keyframe(index):
            with bpy.context.temp_override(object=arm, bone=bone, active_bone=bone):
                bpy.ops.bone.add_xplane_dataref_keyframe(index=index)

        self._key_datarefs(bone.xplane.datarefs, add_keyframe)
        with bpy.context.temp_override(object=arm, bone=bone, active_bone=bone):
            bpy.ops.bone.move_xplane_dataref(index=1, direction="UP")
        self.assertEqual([d.path for d in bone.xplane.datarefs], ["b", "a", "c"])
        prefix = f'bones["{bone.name}"].xplane.datarefs'
        self.assertEqual(
            self._fcurve_values(arm.data.animation_data, prefix),
            {"[0].value": [2, 20], "[1].value": [1, 10], "[2].value": [3, 30]},
        )

    def test_show_hide_written_in_list_order(self) -> None:
        for path, anim_type in (("sim/test/first", "show"), ("sim/test/second", "hide")):
            dataref = self.cube.xplane.datarefs.add()
            dataref.path = path
            dataref.anim_type = anim_type
            dataref.show_hide_v1 = 0
            dataref.show_hide_v2 = 1

        def anim_lines() -> List[str]:
            out = self.exportExportableRoot(self.root)
            return [l.strip() for l in out.splitlines() if l.strip().startswith(("ANIM_show", "ANIM_hide"))]

        self.assertEqual(anim_lines(), ["ANIM_show\t0\t1\tsim/test/first", "ANIM_hide\t0\t1\tsim/test/second"])
        with bpy.context.temp_override(object=self.cube):
            bpy.ops.object.move_xplane_dataref(index=1, direction="UP")
        self.assertEqual(anim_lines(), ["ANIM_hide\t0\t1\tsim/test/second", "ANIM_show\t0\t1\tsim/test/first"])

    def test_unit_scale_warning(self) -> None:
        scene = bpy.context.scene
        self.assertIsNone(xplane_helpers.unit_scale_problem(scene))
        scene.unit_settings.scale_length = 0.01
        try:
            problem = xplane_helpers.unit_scale_problem(scene)
            self.assertIn("Unit Scale is 0.01", problem)
            self.assertIn("exports as 100 m", problem)
            scene.xplane.plugin_development = True
            scene.xplane.dev_export_as_dry_run = True
            result = bpy.ops.export.xplane_obj(filepath=str(get_tmp_folder() / Path("unit_scale.obj")))
            self.assertEqual(result, {"FINISHED"})
            self.assertEqual(
                [w["message"] for w in logger.findWarnings() if "Unit Scale" in w["message"]],
                [problem],
            )
        finally:
            scene.unit_settings.scale_length = 1.0
            scene.xplane.dev_export_as_dry_run = False
            scene.xplane.plugin_development = False


runTestCases([TestDatarefReorder])
