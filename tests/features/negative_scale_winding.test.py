import bpy
from mathutils import Vector

from io_xplane2blender.tests import *


class TestNegativeScaleWinding(XPlaneTestCase):
    """
    Mirrored (negatively scaled) objects must keep triangles facing the
    same way as their normals (#747)
    """

    def _winding_vs_normals(self, scale, custom_normals: bool = False):
        """Returns the sign of each triangle's winding normal dotted with its vertex normals"""
        # A root's own transform isn't exported, so the mirrored mesh is a child
        root = bpy.data.objects.new("root", None)
        bpy.context.collection.objects.link(root)
        root.xplane.isExportableRoot = True
        cube = bpy.data.objects["Cube"]
        cube.parent = root
        cube.scale = scale
        if custom_normals:
            cube.data.normals_split_custom_set_from_vertices(
                [v.co.normalized() for v in cube.data.vertices]
            )
        bpy.context.view_layer.update()
        out = self.exportExportableRoot(root)
        vts = [
            [float(v) for v in line.split()[1:7]]
            for line in out.splitlines()
            if line.startswith("VT")
        ]
        idx = [
            int(i)
            for line in out.splitlines()
            if line.startswith("IDX")
            for i in line.split()[1:]
        ]
        self.assertEqual(len(idx), 36)
        self.assertAlmostEqual(max(abs(vt[0]) for vt in vts), abs(scale[0]))
        signs = set()
        for a, b, c in zip(idx[0::3], idx[1::3], idx[2::3]):
            pa, pb, pc = (Vector(vts[i][:3]) for i in (a, b, c))
            # X-Plane triangles are clockwise
            face_normal = (pc - pa).cross(pb - pa)
            for i in (a, b, c):
                signs.add(face_normal.dot(Vector(vts[i][3:6])) > 0)
        return signs

    def test_positive_scale_reference(self) -> None:
        self.assertEqual(self._winding_vs_normals((2, 1, 1)), {True})

    def test_negative_scale(self) -> None:
        self.assertEqual(self._winding_vs_normals((-2, 1, 1)), {True})

    def test_negative_scale_two_axes(self) -> None:
        self.assertEqual(self._winding_vs_normals((-2, -1, 1)), {True})

    def test_negative_scale_custom_normals(self) -> None:
        self.assertEqual(
            self._winding_vs_normals((-2, 1, 1), custom_normals=True), {True}
        )


runTestCases([TestNegativeScaleWinding])
