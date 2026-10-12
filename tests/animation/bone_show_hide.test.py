"""
Show/Hide on an armature bone (#643, #516). The Bone tab always offered it, but it was never
exported. It's written in the bone's ANIM_begin/ANIM_end, so it applies to every object under the bone.
"""
from typing import List

import bpy

from io_xplane2blender import xplane_constants
from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers


class TestBoneShowHide(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        test_creation_helpers.delete_everything()
        self.root = test_creation_helpers.create_datablock_empty(
            test_creation_helpers.DatablockInfo("EMPTY", "root")
        )
        self.root.xplane.isExportableRoot = True
        self.root.xplane.layer.export_type = xplane_constants.EXPORT_TYPE_AIRCRAFT
        self.arm = test_creation_helpers.create_datablock_armature(
            test_creation_helpers.DatablockInfo(
                "ARMATURE", "arm", parent_info=test_creation_helpers.ParentInfo(self.root)
            )
        )
        self.bone_name = self.arm.data.bones[0].name
        self.door = test_creation_helpers.create_datablock_mesh(
            test_creation_helpers.DatablockInfo(
                "MESH",
                "door",
                parent_info=test_creation_helpers.ParentInfo(
                    self.arm, test_creation_helpers._BONE, self.bone_name
                ),
            )
        )
        self.door.data.materials.append(test_creation_helpers.create_material_default())

    def _lines(self) -> List[str]:
        out = self.exportExportableRoot(self.root)
        return [l.strip() for l in out.splitlines() if l.strip() and not l.strip().startswith("#")]

    def _add_bone_dataref(self, anim_type: str, path: str, v1: float, v2: float, loop: float = 0):
        dataref = self.arm.data.bones[self.bone_name].xplane.datarefs.add()
        dataref.path = path
        dataref.anim_type = anim_type
        dataref.show_hide_v1 = v1
        dataref.show_hide_v2 = v2
        dataref.loop = loop

    def _assert_wraps_door(self, lines: List[str], directive: str) -> None:
        """directive is in an ANIM_begin/ANIM_end block that contains the door's TRIS"""
        at = next(i for i, l in enumerate(lines) if l.startswith(directive))
        begin = max(i for i in range(at) if lines[i] == "ANIM_begin")
        depth, end = 0, None
        for i in range(begin, len(lines)):
            depth += lines[i] == "ANIM_begin"
            depth -= lines[i] == "ANIM_end"
            if depth == 0:
                end = i
                break
        tris = [i for i, l in enumerate(lines) if l.startswith("TRIS")]
        self.assertEqual(len(tris), 1)
        self.assertTrue(at < tris[0] < end, lines)

    def test_bone_hide_exported(self) -> None:
        self._add_bone_dataref(xplane_constants.ANIM_TYPE_HIDE, "sim/test/door_hidden", 0.5, 1)
        lines = self._lines()
        self.assertIn("ANIM_hide\t0.5\t1\tsim/test/door_hidden", lines)
        self._assert_wraps_door(lines, "ANIM_hide")

    def test_bone_show_with_loop_exported(self) -> None:
        self._add_bone_dataref(xplane_constants.ANIM_TYPE_SHOW, "sim/test/door_shown", 0, 1, loop=2)
        lines = self._lines()
        self.assertIn("ANIM_show\t0\t1\tsim/test/door_shown", lines)
        self.assertIn("ANIM_keyframe_loop\t2", lines)
        self._assert_wraps_door(lines, "ANIM_show")

    def test_bone_custom_anim_attribute_exported(self) -> None:
        attr = self.arm.data.bones[self.bone_name].xplane.customAnimAttributes.add()
        attr.name = "ANIM_hide"
        attr.value = "0 1 sim/test/custom"
        lines = self._lines()
        self.assertIn("ANIM_hide\t0 1 sim/test/custom", lines)
        self._assert_wraps_door(lines, "ANIM_hide")

    def test_no_bone_animation_no_block(self) -> None:
        self.assertNotIn("ANIM_begin", self._lines())


runTestCases([TestBoneShowHide])
