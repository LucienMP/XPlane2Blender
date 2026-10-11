import os
from pathlib import Path

import bpy

from io_xplane2blender.tests import *
from io_xplane2blender.xplane_constants import MANIP_DRAG_ROTATE

__dirname__ = Path(__file__).parent


class TestDragRotateMouseWheel(XPlaneTestCase):
    """Drag Rotate manipulators can have a mouse wheel step (#621)"""

    def setUp(self):
        super().setUp()
        # A valid Drag Rotate setup from another test
        bpy.ops.wm.open_mainfile(filepath=str(__dirname__ / "drag_rotate_start_end_the_same.test.blend"))

    def test_wheel_written_after_drag_rotate(self) -> None:
        manips = [o for o in bpy.data.objects if o.xplane.manip.enabled and o.xplane.manip.type == MANIP_DRAG_ROTATE]
        self.assertTrue(manips)
        for obj in manips:
            obj.xplane.manip.wheel_delta = 0.5

        out = self.exportExportableRoot("drag_rotate_start_end_the_same")
        lines = [l.strip().split("\t")[0] for l in out.splitlines() if l.strip().startswith("ATTR_manip")]
        self.assertIn("ATTR_manip_wheel", lines)
        # In the manipulator it belongs to: after ATTR_manip_drag_rotate and its keyframes
        wheel = lines.index("ATTR_manip_wheel")
        before = lines[:wheel]
        self.assertIn("ATTR_manip_drag_rotate", before)
        self.assertTrue(
            all(l == "ATTR_manip_keyframe" for l in before[before.index("ATTR_manip_drag_rotate") + 1:])
        )
        self.assertIn("ATTR_manip_wheel\t0.500", out)
        with open(get_tmp_folder() / Path("drag_rotate_mouse_wheel.obj"), "w") as f:
            f.write(out)  # For loading in X-Plane

    def test_no_wheel_by_default(self) -> None:
        out = self.exportExportableRoot("drag_rotate_start_end_the_same")
        self.assertNotIn("ATTR_manip_wheel", out)


runTestCases([TestDragRotateMouseWheel])
