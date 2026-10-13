"""
Dataref checks against the bundled DataRefs.txt (#344, #68, #345): a misspelt sim/
dataref, an array used without an element, an element that doesn't exist, and a
space in the path each warn on export, once per OBJ. A plugin's own datarefs can't
be in the file, so they only get the shape checks.
"""
from typing import List

import bpy

from io_xplane2blender import xplane_constants
from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers
from io_xplane2blender.xplane_utils import xplane_dataref_validation


def dataref_warnings() -> List[str]:
    return [w["message"] for w in logger.findWarnings() if ": dataref '" in w["message"]]


class TestDatarefValidation(XPlaneTestCase):
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
        logger.clearMessages()

    # --- The checker itself, on X-Plane 12.4's DataRefs.txt --------------------
    def problem(self, path: str):
        return xplane_dataref_validation.dataref_problem(path)

    def test_known_datarefs_pass(self) -> None:
        self.assertIsNone(self.problem("sim/cockpit2/engine/actuators/throttle_ratio_all"))
        self.assertIsNone(self.problem("sim/cockpit2/engine/actuators/throttle_ratio[1]"))
        self.assertIsNone(self.problem("sim/flightmodel2/wing/elements/element_AOA_deg[479]"))
        self.assertIsNone(self.problem("  sim/graphics/animation/sin_wave_2  "))

    def test_empty_and_none_pass(self) -> None:
        self.assertIsNone(self.problem(""))
        self.assertIsNone(self.problem("none"))

    def test_plugin_datarefs_pass(self) -> None:
        self.assertIsNone(self.problem("myplane/gear/door"))
        self.assertIsNone(self.problem("myplane/gear/doors[3]"))
        self.assertIsNone(self.problem("show_hide_dataref_show"))

    def test_unknown_sim_dataref(self) -> None:
        self.assertIn("isn't in X-Plane's DataRefs.txt", self.problem("sim/cockpit2/engine/actuators/throtle_ratio_all"))
        self.assertIn("isn't in X-Plane's DataRefs.txt", self.problem("sim/test/door"))

    def test_array_without_element(self) -> None:
        problem = self.problem("sim/cockpit2/engine/actuators/throttle_ratio")
        self.assertIn("is an array of 16 elements", problem)
        self.assertIn("throttle_ratio[0]", problem)
        self.assertIn("is an array", self.problem("sim/aircraft/view/acf_livery_path"))

    def test_element_out_of_range(self) -> None:
        self.assertIn("has only 16 elements, [0] to [15]", self.problem("sim/cockpit2/engine/actuators/throttle_ratio[16]"))
        # float[48][10] is read flat, so 480 elements
        self.assertIn("has only 480 elements", self.problem("sim/flightmodel2/wing/elements/element_AOA_deg[480]"))

    def test_element_on_scalar(self) -> None:
        self.assertIn("isn't an array, so remove the [0]", self.problem("sim/cockpit2/engine/actuators/throttle_ratio_all[0]"))

    def test_bad_shapes(self) -> None:
        self.assertIn("has a space in it", self.problem("sim/cockpit2/engine/actuators/throttle ratio"))
        self.assertIn("whole number", self.problem("sim/cockpit2/engine/actuators/throttle_ratio[a]"))
        self.assertIn("whole number", self.problem("sim/cockpit2/engine/actuators/throttle_ratio[]"))
        self.assertIn("brackets", self.problem("sim/cockpit2/engine/actuators/throttle_ratio[0"))
        self.assertIn("brackets", self.problem("sim/cockpit2/engine/actuators/throttle_ratio[0][1]"))

    # --- On export ----------------------------------------------------------------
    def _export(self) -> List[str]:
        self.exportExportableRoot(self.root)
        return dataref_warnings()

    def _animate(self, obj: bpy.types.Object, path: str) -> None:
        test_creation_helpers.set_animation_data(
            obj,
            [
                test_creation_helpers.KeyframeInfo(idx=1, dataref_path=path, dataref_value=0.0, location=(0, 0, 0)),
                test_creation_helpers.KeyframeInfo(idx=2, dataref_path=path, dataref_value=1.0, location=(1, 0, 0)),
            ],
        )

    def test_transform_dataref_warns_with_object_name(self) -> None:
        self._animate(self.cube, "sim/test/door")
        warnings = self._export()
        self.assertEqual(len(warnings), 1)
        self.assertTrue(warnings[0].startswith("Mesh: cube: dataref 'sim/test/door'"), warnings[0])
        self.assertIn("isn't in X-Plane's DataRefs.txt", warnings[0])

    def test_known_datarefs_do_not_warn(self) -> None:
        self._animate(self.cube, "sim/cockpit2/engine/actuators/throttle_ratio[2]")
        self.assertEqual(self._export(), [])

    def test_warned_once_per_obj(self) -> None:
        other = test_creation_helpers.create_datablock_mesh(
            test_creation_helpers.DatablockInfo(
                "MESH", "other", parent_info=test_creation_helpers.ParentInfo(self.root)
            )
        )
        self._animate(self.cube, "sim/test/door")
        self._animate(other, "sim/test/door")
        self.assertEqual(len(self._export()), 1)

    def test_show_hide_on_object_and_bone(self) -> None:
        dataref = self.cube.xplane.datarefs.add()
        dataref.path = "sim/cockpit2/engine/actuators/throttle_ratio"
        dataref.anim_type = xplane_constants.ANIM_TYPE_HIDE
        arm = test_creation_helpers.create_datablock_armature(
            test_creation_helpers.DatablockInfo(
                "ARMATURE", "arm", parent_info=test_creation_helpers.ParentInfo(self.root)
            )
        )
        bone_dataref = arm.data.bones[0].xplane.datarefs.add()
        bone_dataref.path = "sim/test/bone_shown"
        bone_dataref.anim_type = xplane_constants.ANIM_TYPE_SHOW
        warnings = self._export()
        self.assertEqual(len(warnings), 2, warnings)
        self.assertTrue(any("is an array of 16 elements" in w for w in warnings), warnings)
        self.assertTrue(any(w.startswith("Bone: ") and "sim/test/bone_shown" in w for w in warnings), warnings)

    def test_light_and_light_level_and_manipulator(self) -> None:
        light = test_creation_helpers.create_datablock_light(
            test_creation_helpers.DatablockInfo(
                "LIGHT", "light", parent_info=test_creation_helpers.ParentInfo(self.root)
            ),
            "POINT",
        )
        light.data.xplane.type = xplane_constants.LIGHT_CUSTOM
        light.data.xplane.dataref = "sim/test/light"
        self.cube.xplane.lightLevel = True
        self.cube.xplane.lightLevel_dataref = "sim/test/light_level"
        self.cube.xplane.manip.enabled = True
        self.cube.xplane.manip.type = xplane_constants.MANIP_TOGGLE
        self.cube.xplane.manip.dataref1 = "sim/test/toggle"
        self.root.xplane.layer.export_type = xplane_constants.EXPORT_TYPE_COCKPIT
        warnings = self._export()
        self.assertEqual(len(warnings), 3, warnings)
        for path in ("sim/test/light", "sim/test/light_level", "sim/test/toggle"):
            self.assertTrue(any(f"'{path}'" in w for w in warnings), (path, warnings))

    def test_command_manipulator_not_checked(self) -> None:
        self.cube.xplane.manip.enabled = True
        self.cube.xplane.manip.type = xplane_constants.MANIP_COMMAND
        self.cube.xplane.manip.command = "sim/test/command"
        self.cube.xplane.manip.dataref1 = "sim/test/not_used"
        self.root.xplane.layer.export_type = xplane_constants.EXPORT_TYPE_COCKPIT
        self.assertEqual(self._export(), [])


runTestCases([TestDatarefValidation])
