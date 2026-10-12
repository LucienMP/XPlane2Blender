import bpy
from mathutils import Euler, Vector

from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers


class TestNegativeScaleWinding(XPlaneTestCase):
    """
    Mirrored (negatively scaled) objects must keep triangles facing the
    same way as their normals (#747)
    """

    def _winding_vs_normals(
        self, scale, custom_normals: bool = False, animated: bool = False
    ):
        """
        Returns the signs of, for every triangle, the clockwise winding normal and
        each vertex normal against the direction from the cube's centre: True means
        outwards. The cube is convex, so every one must be outwards; a test that only
        compared winding with normals passed when both were inverted
        """
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
        if animated:
            # The scale then goes through the animation's bake matrices
            test_creation_helpers.set_animation_data(
                cube,
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
            bpy.context.scene.frame_set(1)
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
        centre = sum((Vector(vt[:3]) for vt in vts), Vector()) / len(vts)
        signs = set()
        for vt in vts:
            signs.add(Vector(vt[3:6]).dot(Vector(vt[:3]) - centre) > 0)
        for a, b, c in zip(idx[0::3], idx[1::3], idx[2::3]):
            pa, pb, pc = (Vector(vts[i][:3]) for i in (a, b, c))
            # X-Plane triangles are clockwise
            face_normal = (pc - pa).cross(pb - pa)
            signs.add(face_normal.dot((pa + pb + pc) / 3 - centre) > 0)
        return signs

    def test_positive_scale_reference(self) -> None:
        self.assertEqual(self._winding_vs_normals((2, 1, 1)), {True})

    def test_negative_scale(self) -> None:
        self.assertEqual(self._winding_vs_normals((-2, 1, 1)), {True})

    def test_negative_scale_two_axes(self) -> None:
        self.assertEqual(self._winding_vs_normals((-2, -1, 1)), {True})

    def test_negative_scale_animated(self) -> None:
        self.assertEqual(
            self._winding_vs_normals((-2, 1, 1), animated=True), {True}
        )

    def test_negative_scale_custom_normals(self) -> None:
        self.assertEqual(
            self._winding_vs_normals((-2, 1, 1), custom_normals=True), {True}
        )


runTestCases([TestNegativeScaleWinding])
