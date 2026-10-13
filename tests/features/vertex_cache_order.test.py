"""
With Optimize on, each object's triangles are ordered for the GPU's post-transform
vertex cache (#134): the same triangles come out, in an order with fewer cache
misses. With Optimize off nothing changes.
"""
import random
from typing import List, Tuple

import bpy

from io_xplane2blender import xplane_constants
from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers
from io_xplane2blender.xplane_utils import xplane_vertex_cache


def parse_tris(out: str) -> Tuple[List[tuple], List[int], List[Tuple[int, int]]]:
    """(VT rows, IDX list, [(TRIS offset, count)])"""
    vts, idx, tris = [], [], []
    for line in out.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "VT":
            vts.append(tuple(round(float(p), 4) for p in parts[1:]))
        elif parts[0] in ("IDX", "IDX10"):
            idx.extend(int(p) for p in parts[1:])
        elif parts[0] == "TRIS":
            tris.append((int(parts[1]), int(parts[2])))
    return vts, idx, tris


def triangle_set(out: str):
    """Every triangle as its three VT rows, independent of VT and IDX order"""
    vts, idx, tris = parse_tris(out)
    found = set()
    for offset, count in tris:
        for i in range(offset, offset + count, 3):
            found.add(frozenset(vts[v] for v in idx[i : i + 3]))
    return found, len(idx) // 3


class TestVertexCacheOrder(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        test_creation_helpers.delete_everything()
        self.root = test_creation_helpers.create_datablock_empty(
            test_creation_helpers.DatablockInfo("EMPTY", "root")
        )
        self.root.xplane.isExportableRoot = True
        self.root.xplane.layer.export_type = xplane_constants.EXPORT_TYPE_SCENERY
        # A 20x20 grid with its faces shuffled: a cache-hostile order
        n = 20
        verts = [(x, y, 0.0) for y in range(n + 1) for x in range(n + 1)]
        faces = []
        for y in range(n):
            for x in range(n):
                a = y * (n + 1) + x
                faces.append((a, a + 1, a + n + 2, a + n + 1))
        random.seed(7)
        random.shuffle(faces)
        mesh = bpy.data.meshes.new("grid")
        mesh.from_pydata(verts, [], faces)
        mesh.materials.append(test_creation_helpers.create_material_default())
        self.grid = bpy.data.objects.new("grid", mesh)
        bpy.context.scene.collection.objects.link(self.grid)
        self.grid.parent = self.root
        bpy.context.scene.xplane.optimize = False
        logger.clearMessages()

    def tearDown(self):
        bpy.context.scene.xplane.optimize = False

    def _export(self, optimize: bool) -> str:
        bpy.context.scene.xplane.optimize = optimize
        return self.exportExportableRoot(self.root)

    def test_same_triangles_fewer_misses(self) -> None:
        plain = self._export(False)
        optimized = self._export(True)
        plain_set, plain_count = triangle_set(plain)
        opt_set, opt_count = triangle_set(optimized)
        self.assertEqual(plain_count, 800)
        self.assertEqual(opt_count, 800)
        self.assertEqual(plain_set, opt_set)

        def acmr(out: str) -> float:
            vts, idx, _ = parse_tris(out)
            return xplane_vertex_cache.average_cache_miss_ratio(
                [tuple(idx[i : i + 3]) for i in range(0, len(idx), 3)]
            )

        # Optimize alone shares vertices but keeps the shuffled order
        self.assertLess(acmr(optimized), 1.0)
        self.assertLess(acmr(optimized), acmr(plain) / 2)

    def test_winding_kept(self) -> None:
        # Every triangle faces +Z in Blender, +Y in X-Plane, and X-Plane winds
        # clockwise seen from the front: the corners' cross product points -Y.
        # The same holds with and without the reordering
        for optimize in (False, True):
            vts, idx, _ = parse_tris(self._export(optimize))
            for i in range(0, len(idx), 3):
                a, b, c = (vts[idx[i + k]][:3] for k in range(3))
                ab = tuple(b[k] - a[k] for k in range(3))
                ac = tuple(c[k] - a[k] for k in range(3))
                cross_y = ab[2] * ac[0] - ab[0] * ac[2]
                self.assertLess(cross_y, 0, (optimize, a, b, c))
                self.assertEqual(vts[idx[i]][3:6], (0.0, 1.0, 0.0))

    def test_optimizer_is_a_permutation(self) -> None:
        tris = [(i, i + 1, i + 2) for i in range(0, 30, 3)] + [(0, 1, 2)]
        order = xplane_vertex_cache.optimize_triangle_order(tris)
        self.assertEqual(sorted(order), list(range(len(tris))))


runTestCases([TestVertexCacheOrder])
