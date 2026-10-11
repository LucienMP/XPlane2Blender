import bpy

from io_xplane2blender.tests import *
from io_xplane2blender.xplane_constants import (
    COCKPIT_FEATURE_DEVICE,
    DEVICE_G1000_PFD1,
    DEVICE_PLUGIN,
    EXPORT_TYPE_COCKPIT,
    MANIP_DEVICE,
    VERSION_1210,
)


class TestManipDevice(XPlaneTestCase):
    """ATTR_manip_device, the touch screen manipulator of X-Plane 12.10+"""

    def setUp(self):
        super().setUp()
        bpy.context.scene.xplane.version = VERSION_1210
        self.cube = bpy.data.objects["Cube"]
        self.cube.xplane.isExportableRoot = True
        self.cube.xplane.layer.export_type = EXPORT_TYPE_COCKPIT

        # The manipulator mesh, invisible, as recommended
        self.manip_mat = self.cube.active_material
        self.manip_mat.xplane.draw = False
        manip = self.cube.xplane.manip
        manip.enabled = True
        manip.type = MANIP_DEVICE
        manip.tooltip = "Touch"

        # The screen's material
        self.screen_mat = bpy.data.materials.new("screen")
        self.screen_mat.xplane.cockpit_feature = COCKPIT_FEATURE_DEVICE
        self.screen_mat.xplane.device_name = DEVICE_G1000_PFD1

    def _attr_lines(self):
        return [
            line.split()
            for line in self.exportExportableRoot(self.cube).splitlines()
            if line.startswith(("ATTR_manip", "ATTR_cockpit_device", "ATTR_draw"))
        ]

    def test_screen_material(self) -> None:
        self.cube.xplane.manip.screen_material = self.screen_mat
        lines = self._attr_lines()
        self.assertIn(["ATTR_manip_device", "hand", DEVICE_G1000_PFD1, "Touch"], lines)
        self.assertIn(DEVICE_G1000_PFD1, [l[1] for l in lines if l[0] == "ATTR_cockpit_device"])
        self.assertIn(["ATTR_draw_disable"], lines)

    def test_own_material_plugin_device(self) -> None:
        self.manip_mat.xplane.cockpit_feature = COCKPIT_FEATURE_DEVICE
        self.manip_mat.xplane.device_name = DEVICE_PLUGIN
        self.manip_mat.xplane.plugin_device = "tablet_screen"
        lines = self._attr_lines()
        self.assertIn(["ATTR_manip_device", "hand", "tablet_screen", "Touch"], lines)

    def test_no_device_material_is_an_error(self) -> None:
        self.exportExportableRoot(self.cube)
        self.assertLoggerErrors(1)


runTestCases([TestManipDevice])
