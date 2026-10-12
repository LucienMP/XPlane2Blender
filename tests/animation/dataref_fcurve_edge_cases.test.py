import bpy
from mathutils import Euler

from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers
from io_xplane2blender.xplane_constants import ANIM_TYPE_SHOW


class TestDatarefFCurveEdgeCases(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        # Every test starts from an empty scene
        test_creation_helpers.delete_everything()
        self.root = bpy.data.objects.new("root", None)
        bpy.context.scene.collection.objects.link(self.root)
        self.root.xplane.isExportableRoot = True
        self.cube = test_creation_helpers.create_datablock_mesh(
            test_creation_helpers.DatablockInfo("MESH", "Cube")
        )
        self.cube.parent = self.root
        test_creation_helpers.set_animation_data(
            self.cube,
            [
                test_creation_helpers.KeyframeInfo(
                    idx=1,
                    dataref_path="sim/test",
                    dataref_value=0.0,
                    rotation=Euler((0, 0, 0)),
                ),
                test_creation_helpers.KeyframeInfo(
                    idx=2,
                    dataref_path="sim/test",
                    dataref_value=1.0,
                    rotation=Euler((0, 0, 1.0)),
                ),
            ],
        )

    def _lines(self):
        return [
            line.split()
            for line in self.exportExportableRoot(self.root).splitlines()
            if line.strip().startswith("ANIM")
        ]

    def test_keyframed_other_dataref_field_is_ignored(self) -> None:
        """
        Only a dataref's Value animates it. A keyframe on another field of the
        dataref used to be parsed as a value index and crash the export
        """
        show = self.cube.xplane.datarefs.add()
        show.path = "sim/show"
        show.anim_type = ANIM_TYPE_SHOW
        show.show_hide_v1 = 1
        show.show_hide_v2 = 2
        self.cube.keyframe_insert(data_path="xplane.datarefs[1].show_hide_v1", frame=1)
        self.cube.keyframe_insert(data_path="xplane.datarefs[0].loop", frame=1)
        lines = self._lines()
        # Blender's Z is X-Plane's Y
        self.assertIn(["ANIM_rotate_begin", "0", "1", "-0", "sim/test"], lines)
        self.assertIn(["ANIM_show", "1", "2", "sim/show"], lines)
        self.assertTrue(
            any("show_hide_v1" in w["message"] for w in logger.findWarnings()),
            "The ignored keyframe should be warned about",
        )
        # Clears the logger, so it goes last
        self.assertLoggerErrors(0)

    def test_negative_loop_is_written(self) -> None:
        """Loop values may be negative since #767; they were silently dropped"""
        self.cube.xplane.datarefs[0].loop = -5
        lines = self._lines()
        self.assertIn(["ANIM_keyframe_loop", "-5.0"], lines)

    def test_fractional_keyframe_rounds_and_warns(self) -> None:
        """
        A keyframe on frame 2.4 (after scaling keys in the Dope Sheet) is read at
        frame 2 and warned about; it used to be left out of the frame scan and
        silently get frame 1's rotation
        """
        action_fcurves = xplane_helpers.get_action_fcurves(self.cube.animation_data)
        for fcurve in action_fcurves:
            for kf in fcurve.keyframe_points:
                if kf.co[0] == 2:
                    kf.co[0] = 2.4
        lines = self._lines()
        keys = [l for l in lines if l[0] == "ANIM_rotate_key"]
        self.assertEqual(len(keys), 2)
        self.assertNotEqual(keys[0][2], keys[1][2], "The second key must not repeat frame 1's rotation")
        self.assertTrue(any("2.4" in w["message"] for w in logger.findWarnings()))


runTestCases([TestDatarefFCurveEdgeCases])
