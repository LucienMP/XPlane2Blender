"""
Warnings and checks added in 5.0 for upstream issues:
- #285: a mesh with no UV map in a textured OBJ
- #515: Camera Collision in an Aircraft object (OBJ8 spec: only the cockpit object has a camera plane;
  Scenery types already refused it)
- #279: Slope Limit angles within -90 to 90, and min not above max
- #766: the Data tab's X-Plane panel only shows for lights and (X-Plane 11.30+) empties
"""
from types import SimpleNamespace
from typing import List

import bpy

from io_xplane2blender import xplane_constants, xplane_ui
from io_xplane2blender.tests import *


def warnings_containing(text: str) -> List[str]:
    return [w["message"] for w in logger.findWarnings() if text in w["message"]]


class TestValidationWarnings(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj)
        self.root = bpy.data.objects.new("root", None)
        bpy.context.collection.objects.link(self.root)
        self.root.xplane.isExportableRoot = True
        self.layer = self.root.xplane.layer
        self.layer.export_type = xplane_constants.EXPORT_TYPE_SCENERY
        self.layer.texture = "tex.png"
        mesh = bpy.data.meshes.new("quad")
        mesh.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
        self.mat = bpy.data.materials.new("mat")
        mesh.materials.append(self.mat)
        self.quad = bpy.data.objects.new("quad", mesh)
        bpy.context.collection.objects.link(self.quad)
        self.quad.parent = self.root
        logger.clearMessages()

    def export(self) -> str:
        out = self.exportExportableRoot(self.root)
        return out

    # --- #285 ------------------------------------------------------------
    def test_no_uv_map_with_texture_warns(self) -> None:
        self.export()
        self.assertEqual(len(warnings_containing("has no UV map")), 1)
        logger.clearMessages()

    def test_uv_map_no_warning(self) -> None:
        self.quad.data.uv_layers.new()
        self.export()
        self.assertEqual(warnings_containing("has no UV map"), [])

    def test_no_texture_no_warning(self) -> None:
        self.layer.texture = ""
        self.export()
        self.assertEqual(warnings_containing("has no UV map"), [])

    # --- #515 ------------------------------------------------------------
    def test_camera_collision_in_aircraft_warns(self) -> None:
        self.quad.data.uv_layers.new()
        self.mat.xplane.solid_camera = True
        self.layer.export_type = xplane_constants.EXPORT_TYPE_AIRCRAFT
        out = self.export()
        self.assertEqual(len(warnings_containing("Camera Collision")), 1)
        self.assertFalse(logger.hasErrors())
        self.assertIn("ATTR_solid_camera", out)  # still written, as before
        logger.clearMessages()

    def test_camera_collision_in_scenery_still_an_error(self) -> None:
        self.quad.data.uv_layers.new()
        self.mat.xplane.solid_camera = True
        self.export()
        self.assertTrue(any("camera collision" in e["message"] for e in logger.findErrors()))
        logger.clearMessages()

    def test_camera_collision_in_cockpit_no_warning(self) -> None:
        self.quad.data.uv_layers.new()
        self.mat.xplane.solid_camera = True
        self.layer.export_type = xplane_constants.EXPORT_TYPE_COCKPIT
        self.export()
        self.assertEqual(warnings_containing("Camera Collision"), [])

    # --- #279 ------------------------------------------------------------
    def test_slope_limit_fields_enforce_range_and_order(self) -> None:
        layer = self.layer
        layer.slope_limit_min_pitch = -120  # beyond the field's -90 limit
        self.assertEqual(layer.slope_limit_min_pitch, -90)
        layer.slope_limit_min_pitch, layer.slope_limit_max_pitch = -10, 10
        layer.slope_limit_min_pitch = 20  # above max: max follows
        self.assertEqual((layer.slope_limit_min_pitch, layer.slope_limit_max_pitch), (20, 20))
        layer.slope_limit_max_pitch = 5  # below min: min follows
        self.assertEqual((layer.slope_limit_min_pitch, layer.slope_limit_max_pitch), (5, 5))
        layer.slope_limit_min_roll, layer.slope_limit_max_roll = -30, -40
        self.assertEqual((layer.slope_limit_min_roll, layer.slope_limit_max_roll), (-40, -40))
        layer.slope_limit_min_roll = 0
        self.assertEqual((layer.slope_limit_min_roll, layer.slope_limit_max_roll), (0, 0))

    def test_slope_limit_bad_old_values_warn(self) -> None:
        """Values saved before the fields had limits (#279) are still caught at export"""
        self.quad.data.uv_layers.new()
        layer = self.layer
        layer.slope_limit = True
        stored = layer.bl_system_properties_get(do_create=True)
        stored["slope_limit_min_pitch"] = -300.0
        stored["slope_limit_max_pitch"] = 10.0
        stored["slope_limit_min_roll"] = 30.0
        stored["slope_limit_max_roll"] = 10.0
        self.export()
        self.assertEqual(len(warnings_containing("must be within -90 to 90")), 1)
        self.assertEqual(len(warnings_containing("Min. Roll (30.0) is above Max. Roll (10.0)")), 1)
        logger.clearMessages()

    # --- #766 ------------------------------------------------------------
    def test_data_panel_only_for_lights_and_empties(self) -> None:
        scene = bpy.context.scene
        poll = xplane_ui.DATA_PT_xplane.poll
        light = bpy.data.objects.new("light", bpy.data.lights.new("light", "POINT"))
        empty = bpy.data.objects.new("empty", None)
        for obj, version, expected in (
            (self.quad, xplane_constants.VERSION_1200, False),
            (light, xplane_constants.VERSION_1200, True),
            (empty, xplane_constants.VERSION_1200, True),
            (empty, xplane_constants.VERSION_1100, False),
            (None, xplane_constants.VERSION_1200, False),
        ):
            with self.subTest(obj=obj and obj.name, version=version):
                scene.xplane.version = version
                self.assertEqual(poll(SimpleNamespace(object=obj, scene=scene)), expected)
        scene.xplane.version = xplane_constants.VERSION_1200


runTestCases([TestValidationWarnings])
