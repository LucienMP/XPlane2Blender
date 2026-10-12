import math

import bpy
from mathutils import Matrix, Vector

from io_xplane2blender.tests import *
from io_xplane2blender.xplane_constants import LIGHT_AUTOMATIC
from io_xplane2blender.xplane_helpers import vec_b_to_x, vec_x_to_b
from io_xplane2blender.xplane_utils import xplane_lights_txt_parser


class TestOppositeDirectionAutocorrect(XPlaneTestCase):
    """
    A light aimed exactly opposite to its lights.txt direction has no rotation
    axis from the cross product, and used to export "ANIM_rotate 0 0 0 180 180",
    which X-Plane treats as no rotation at all
    """

    def setUp(self) -> None:
        super().setUp()
        # Done by the file load handler, which a test without a .blend never runs
        xplane_lights_txt_parser.parse_lights_file()

    def test_opposite_direction(self) -> None:
        root = bpy.data.objects.new("root", None)
        bpy.context.collection.objects.link(root)
        root.xplane.isExportableRoot = True

        # A light with a fixed direction in lights.txt (no dataref callback changes it)
        light_name = "taillight"
        overload = xplane_lights_txt_parser.get_parsed_light(light_name).best_overload()
        dxyz_xp = Vector(overload[column] for column in ("DX", "DY", "DZ")).normalized()
        aimed_b = -vec_x_to_b(dxyz_xp)

        light_data = bpy.data.lights.new("tail", "SPOT")
        light_data.xplane.type = LIGHT_AUTOMATIC
        light_data.xplane.name = light_name
        light = bpy.data.objects.new("tail", light_data)
        bpy.context.collection.objects.link(light)
        light.parent = root
        light.location = (1, 2, 3)
        # A spot light points down its -Z
        light.rotation_mode = "QUATERNION"
        light.rotation_quaternion = Vector((0, 0, -1)).rotation_difference(aimed_b)
        bpy.context.view_layer.update()

        out = self.exportExportableRoot(root)
        lines = {
            line.split()[0]: line.split()[1:]
            for line in out.splitlines()
            if line.strip().startswith(("ANIM_rotate", "LIGHT_NAMED"))
        }
        self.assertIn("ANIM_rotate", lines)
        axis = Vector(float(v) for v in lines["ANIM_rotate"][:3])
        angle = float(lines["ANIM_rotate"][3])
        self.assertAlmostEqual(axis.magnitude, 1.0, places=4)
        self.assertAlmostEqual(angle, 180.0, places=3)

        # The rotation must turn the lights.txt direction into the aimed one, and
        # the position written after it must still land on the light
        rotation = Matrix.Rotation(math.radians(angle), 3, axis)
        self.assertFloatVectorsEqual(rotation @ dxyz_xp, vec_b_to_x(aimed_b), 0.0001)
        position = Vector(float(v) for v in lines["LIGHT_NAMED"][1:4])
        self.assertFloatVectorsEqual(
            rotation @ position, vec_b_to_x(Vector((1, 2, 3))), 0.0001
        )


runTestCases([TestOppositeDirectionAutocorrect])
