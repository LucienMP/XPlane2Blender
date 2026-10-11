import inspect

from typing import Tuple
import os
import sys

import bpy
from io_xplane2blender import xplane_config
from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers
from io_xplane2blender.xplane_constants import VERSION_1130, VERSION_1200

__dirname__ = os.path.dirname(__file__)

class TestLightSpillCustomAttributes(XPlaneTestCase):
    def test_light_attributes(self)->None:
        # These fixtures are the pre-X-Plane 12 output, with the size in meters
        bpy.context.scene.xplane.version = VERSION_1130
        filenames = ["test_light_spill_custom_xyz",
                     "test_light_spill_custom_rgb",
                     "test_light_spill_custom_dxyz",
                     "test_light_spill_custom_size",
                     "test_light_spill_custom_semi_spot",
                     "test_light_spill_custom_semi_point",
                     "test_light_spill_custom_dref",]

        for filename in filenames:
            with self.subTest(filename=filename):
                self.assertExportableRootExportEqualsFixture(
                    filename[5:],
                    os.path.join(__dirname__, "fixtures", "light_spill_custom", f"{filename}.obj"),
                    {"LIGHT_SPILL_CUSTOM"},
                    filename,
                )

    def test_xp12_size_is_intensity_in_candela(self)->None:
        # X-Plane 12 reads the size as candela; a bare size in meters gives little
        # or no light (checked in X-Plane 12.4.4, tools/xplane12_instancing_test)
        bpy.context.scene.xplane.version = VERSION_1200
        for light in bpy.data.lights:
            light.xplane.param_intensity_new = 1234
        out = self.exportExportableRoot("light_spill_custom_size")
        spills = [l.split() for l in out.splitlines() if l.strip().startswith("LIGHT_SPILL_CUSTOM")]
        self.assertTrue(spills)
        # LIGHT_SPILL_CUSTOM x y z r g b a size ...
        self.assertIn("1234cd", [spill[8] for spill in spills])

    def test_incompatible_light_types(self):
        filename = inspect.stack()[0].function
        out = self.exportExportableRoot(filename[5:])
        self.assertLoggerErrors(2)


runTestCases([TestLightSpillCustomAttributes])
