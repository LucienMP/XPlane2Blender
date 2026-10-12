import bpy

from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers
from io_xplane2blender.xplane_constants import (
    BLEND_OFF,
    CONDITION_GLOBAL_SHADOWS,
    EXPORT_TYPE_AIRCRAFT,
    EXPORT_TYPE_COCKPIT,
    VERSION_1200,
)


def attr_lines(out: str):
    """The commands after the header, without debug comments and geometry"""
    return [
        line.strip()
        for line in out.splitlines()
        if line.strip()
        and line.strip() not in {"I", "A", "800", "OBJ"}
        and not line.strip().startswith(("#", "VT", "IDX", "POINT_COUNTS"))
    ]


class TestAttributeStateResets(XPlaneTestCase):
    """
    Attributes that were set by one object must be undone for the next one that
    doesn't want them. ATTR_poly_os and ATTR_hud_glass were never reset, and
    attributes set inside an IF block were treated as still in effect after ENDIF
    """

    def setUp(self):
        super().setUp()
        # Every test starts from an empty scene
        test_creation_helpers.delete_everything()
        bpy.context.scene.xplane.version = VERSION_1200
        self.root = test_creation_helpers.create_datablock_collection("root")
        self.root.xplane.is_exportable_collection = True
        self.root.xplane.layer.export_type = EXPORT_TYPE_AIRCRAFT
        self.cubes = []
        for weight, name in enumerate(("A", "B", "C")):
            cube = test_creation_helpers.create_datablock_mesh(
                test_creation_helpers.DatablockInfo("MESH", name, parent_info=None, collection=self.root),
                primitive_shape="cube",
                material_name=f"mat_{name}",
            )
            # Written in this order, whatever Blender's object order is
            cube.xplane.override_weight = True
            cube.xplane.weight = weight
            self.cubes.append(cube)

    def _tris_order(self, lines):
        """The attribute lines grouped by the TRIS they precede, in file order"""
        groups, current = [], []
        for line in lines:
            if line.startswith("TRIS"):
                groups.append(current)
                current = []
            else:
                current.append(line)
        return groups

    def test_poly_os_reset(self) -> None:
        a, b, c = self.cubes
        a.active_material.xplane.poly_os = 2
        c.active_material.xplane.poly_os = 2
        groups = self._tris_order(attr_lines(self.exportExportableRoot(self.root)))
        self.assertIn("ATTR_poly_os\t2", groups[0])
        self.assertIn("ATTR_poly_os\t0", groups[1])
        self.assertIn("ATTR_poly_os\t2", groups[2])

    def test_hud_glass_reset(self) -> None:
        self.root.xplane.layer.export_type = EXPORT_TYPE_COCKPIT
        a, b, c = self.cubes
        a.xplane.hud_glass = True
        c.xplane.hud_glass = True
        groups = self._tris_order(attr_lines(self.exportExportableRoot(self.root)))
        self.assertIn("ATTR_hud_glass", groups[0])
        self.assertIn("ATTR_hud_reset", groups[1])
        self.assertNotIn("ATTR_hud_glass", groups[1])
        self.assertIn("ATTR_hud_glass", groups[2])

    def test_state_unknown_after_endif(self) -> None:
        """
        X-Plane skips a false IF block, so what was set inside it must be written
        again by the next object that needs it, and reset by one that doesn't
        """
        a, b, c = self.cubes
        for cube in (a, b):
            cube.active_material.xplane.blend_v1000 = BLEND_OFF
            cube.active_material.xplane.blendRatio = 0.5
        condition = a.xplane.conditions.add()
        condition.variable = CONDITION_GLOBAL_SHADOWS
        condition.value = True
        groups = self._tris_order(attr_lines(self.exportExportableRoot(self.root)))
        self.assertIn("IF GLOBAL_SHADOWS", groups[0])
        self.assertIn("ATTR_no_blend\t0.5", groups[0])
        # B needs it again: A's may never have been loaded
        self.assertIn("ATTR_no_blend\t0.5", groups[1])
        # C doesn't, and B's did load
        self.assertIn("ATTR_blend", groups[2])

    def test_custom_attribute_weight_orders_output(self) -> None:
        """A heavier custom attribute is written after a lighter one, whatever the order they were added"""
        a = self.cubes[0]
        heavy = a.xplane.customAttributes.add()
        heavy.name, heavy.value, heavy.weight = "ATTR_heavy", "1", 10
        light = a.xplane.customAttributes.add()
        light.name, light.value, light.weight = "ATTR_light", "1", 0
        lines = attr_lines(self.exportExportableRoot(self.root))
        self.assertLess(lines.index("ATTR_light\t1"), lines.index("ATTR_heavy\t1"))


runTestCases([TestAttributeStateResets])
