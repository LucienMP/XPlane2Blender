"""
The light name search window (#561): the same window as the dataref search, filled
from the bundled lights.txt, writing the chosen name into the light's Name field
"""
import bpy

from io_xplane2blender import xplane_constants
from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers
from io_xplane2blender.xplane_ops import XPLANE_OT_LightSearchToggle
from io_xplane2blender.xplane_utils import xplane_lights_txt_parser


class TestLightNameSearch(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        test_creation_helpers.delete_everything()
        self.light = test_creation_helpers.create_datablock_light(
            test_creation_helpers.DatablockInfo("LIGHT", "lamp"), "POINT"
        )
        self.light.data.xplane.type = xplane_constants.LIGHT_AUTOMATIC
        bpy.context.view_layer.objects.active = self.light
        self.state = bpy.context.scene.xplane.light_search_window_state
        self.state.light_search_list.clear()
        self.state.light_prop_dest = ""
        self.paired = "bpy.context.active_object.data.xplane.name"

    def test_toggle_loads_lights_and_opens(self) -> None:
        self.assertEqual(bpy.ops.xplane.light_search_toggle(paired_light_prop=self.paired), {"FINISHED"})
        self.assertEqual(self.state.light_prop_dest, self.paired)
        names = [item.light_name for item in self.state.light_search_list]
        self.assertGreater(len(names), 100)
        self.assertEqual(names, sorted(names))
        self.assertIn("airplane_landing_pm", names)
        self.assertIn("full_custom_halo", names)
        self.assertNotIn("flood_merc_XYZTSB", names)  # BAD_LIGHTS

        bpy.ops.xplane.light_search_toggle(paired_light_prop=self.paired)
        self.assertEqual(self.state.light_prop_dest, "")

    def test_kinds(self) -> None:
        xplane_lights_txt_parser.parse_lights_file()
        kind = XPLANE_OT_LightSearchToggle.light_kind
        content = xplane_lights_txt_parser._parsed_lights_txt_content
        self.assertEqual(kind(content["full_custom_halo"]), "Param: R G B A SIZE DX DY DZ WIDTH")
        self.assertEqual(kind(content["apt_beacon_white_axial"]), "Named")
        self.assertEqual(kind(content["airplane_landing_size"]), "Param: SIZE WIDTH INDEX (not for Automatic lights)")

    def test_clicking_writes_name_and_closes(self) -> None:
        bpy.ops.xplane.light_search_toggle(paired_light_prop=self.paired)
        index = next(
            i for i, item in enumerate(self.state.light_search_list)
            if item.light_name == "airplane_landing_pm"
        )
        self.state.light_search_list_idx = index
        self.assertEqual(self.light.data.xplane.name, "airplane_landing_pm")
        self.assertEqual(self.state.light_prop_dest, "")


runTestCases([TestLightNameSearch])
