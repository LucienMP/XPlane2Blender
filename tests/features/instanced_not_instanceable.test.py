import bpy

from io_xplane2blender.tests import *
from io_xplane2blender.xplane_constants import (
    ANIM_TYPE_HIDE,
    ANIM_TYPE_TRANSFORM,
    EXPORT_TYPE_INSTANCED_SCENERY,
    EXPORT_TYPE_SCENERY,
    LIGHT_CUSTOM,
    LIGHT_NAMED,
    LIGHT_PARAM,
    LIGHT_SPILL_CUSTOM,
)
from io_xplane2blender.xplane_helpers import logger
from io_xplane2blender.xplane_utils import xplane_lights_txt_parser


class TestInstancedNotInstanceable(XPlaneTestCase):
    """
    Warnings when an Instanced Scenery Object has something X-Plane won't
    instance (#368, #489). Each case matches a test in X-Plane 12.4.4.
    """

    def setUp(self):
        super().setUp()
        # Normally parsed when a .blend file is loaded; these tests start from none
        xplane_lights_txt_parser.parse_lights_file()
        self.root = bpy.data.objects.new("root", None)
        bpy.context.collection.objects.link(self.root)
        self.root.xplane.isExportableRoot = True
        self.root.xplane.layer.export_type = EXPORT_TYPE_INSTANCED_SCENERY
        self.cube = bpy.data.objects["Cube"]
        self.cube.parent = self.root
        # Tests share one Blender session
        self.cube.animation_data_clear()
        self.cube.xplane.datarefs.clear()
        self.cube.location = (0, 0, 0)
        self.light = bpy.data.objects["Light"]
        self.light.parent = self.root
        self.light.data.xplane.type = LIGHT_NAMED
        self.light.data.xplane.name = "headlight"

    def _warnings(self):
        self.exportExportableRoot(self.root)
        return [w["message"] for w in logger.findWarnings() if "won't instance" in w["message"]]

    def _set_light(self, light_type, name="", params="", dataref=""):
        self.light.data.xplane.type = light_type
        self.light.data.xplane.name = name
        self.light.data.xplane.params = params
        self.light.data.xplane.dataref = dataref

    # --- Instanceable: no warning ---------------------------------------
    def test_static_hardware_light_no_warning(self):
        self.assertEqual(self._warnings(), [])

    def test_custom_spill_without_dataref_no_warning(self):
        self._set_light(LIGHT_SPILL_CUSTOM)
        self.assertEqual(self._warnings(), [])

    def test_param_hardware_light_no_warning(self):
        self._set_light(LIGHT_PARAM, "full_custom_halo", "1 1 1 1 5 0 0 1 1")
        self.assertEqual(self._warnings(), [])

    def test_scenery_object_never_warns(self):
        self.root.xplane.layer.export_type = EXPORT_TYPE_SCENERY
        self._set_light(LIGHT_NAMED, "VASI")
        self.assertEqual(self._warnings(), [])

    # --- Not instanceable: warning ---------------------------------------
    def test_animation_warns(self):
        test_creation_helpers.set_animation_data(
            self.cube,
            [
                test_creation_helpers.KeyframeInfo(1, "sim/test", 0, location=(0, 0, 0)),
                test_creation_helpers.KeyframeInfo(10, "sim/test", 1, location=(2, 0, 0)),
            ],
        )
        warnings = self._warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("because Cube is animated", warnings[0])

    def test_show_hide_warns(self):
        dataref = self.cube.xplane.datarefs.add()
        dataref.path = "sim/test"
        dataref.anim_type = ANIM_TYPE_HIDE
        warnings = self._warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("because Cube is animated", warnings[0])

    def test_custom_billboard_warns(self):
        self._set_light(LIGHT_CUSTOM, dataref="NULL")
        warnings = self._warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("custom billboard lights are never instanced", warnings[0])

    def test_custom_spill_with_dataref_warns(self):
        self._set_light(LIGHT_SPILL_CUSTOM, dataref="sim/graphics/animation/lights/strobe")
        warnings = self._warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("its dataref 'sim/graphics/animation/lights/strobe'", warnings[0])

    def test_named_software_light_warns(self):
        self._set_light(LIGHT_NAMED, "VASI")
        warnings = self._warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("defines 'VASI' as dataref-driven", warnings[0])

    def test_param_software_light_warns(self):
        self._set_light(LIGHT_PARAM, "airplane_beacon_rotate", "1 0")
        warnings = self._warnings()
        self.assertEqual(len(warnings), 1)
        self.assertIn("defines 'airplane_beacon_rotate' as dataref-driven", warnings[0])


runTestCases([TestInstancedNotInstanceable])
