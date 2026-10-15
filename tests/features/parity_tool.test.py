"""
The parts of the visual parity check (io_xplane2blender/xplane_parity) that don't need
X-Plane: the palette conversion of a model, the classifier, the comparison and the blob
finder, on the sample scene and on synthetic images.
"""
import importlib.util
import os
import subprocess
import sys

import bpy

from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers

PARITY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__import__("io_xplane2blender").__file__))),
                          "io_xplane2blender", "xplane_parity")


def load_module(name):
    """parity_blender.py runs main() on import, so its functions are loaded with argv emptied"""
    spec = importlib.util.spec_from_file_location(name, os.path.join(PARITY_DIR, name + ".py"))
    module = importlib.util.module_from_spec(spec)
    saved = sys.argv
    sys.argv = ["blender", "--", "compare", "--help"] if name == "parity_blender" else saved
    try:
        if name == "parity_blender":
            # argparse's --help exits; swallow it and keep the module's definitions
            try:
                spec.loader.exec_module(module)
            except SystemExit:
                pass
        else:
            spec.loader.exec_module(module)
    finally:
        sys.argv = saved
    return module


class TestParityTool(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        test_creation_helpers.delete_everything()
        self.booth = load_module("make_booth")
        self.pb = load_module("parity_blender")
        self.tmp = get_tmp_folder()

    def test_palette_and_booth(self) -> None:
        import struct
        self.booth.write_palette(os.path.join(self.tmp, "palette.png"))
        self.booth.write_booth(os.path.join(self.tmp, "booth.obj"))
        with open(os.path.join(self.tmp, "palette.png"), "rb") as f:
            self.assertEqual(struct.unpack(">II", f.read(24)[16:24]), (512, 256))
        booth = open(os.path.join(self.tmp, "booth.obj")).read()
        self.assertIn("ATTR_no_cull", booth)
        self.assertIn("GLOBAL_specular\t0", booth)
        self.assertIn("TRIS\t0\t36", booth)
        u, v = self.booth.cell_uv("red")
        self.assertEqual((u, v), (0.125, 0.75))

    def test_convert_to_palette(self) -> None:
        root = test_creation_helpers.create_datablock_empty(test_creation_helpers.DatablockInfo("EMPTY", "root"))
        a = test_creation_helpers.create_datablock_mesh(test_creation_helpers.DatablockInfo(
            "MESH", "a", parent_info=test_creation_helpers.ParentInfo(root)), material_name="wood")
        b = test_creation_helpers.create_datablock_mesh(test_creation_helpers.DatablockInfo(
            "MESH", "b", parent_info=test_creation_helpers.ParentInfo(root)), material_name="steel")
        b.data.materials.append(bpy.data.materials.new("glass"))
        self.booth.write_palette(os.path.join(self.tmp, "palette.png"))
        colour_of = self.pb.convert_to_palette(root, os.path.join(self.tmp, "palette.png"))
        # One colour per original material, no two the same while colours last
        self.assertEqual(len(set(colour_of.values())), len(colour_of))
        for obj in (a, b):
            for slot in obj.material_slots:
                self.assertTrue(slot.material.name.startswith("parity_"))
                self.assertIsNotNone(slot.material.node_tree.nodes.active)
            uv = obj.data.uv_layers.active
            for poly in obj.data.polygons:
                colour = slot_colour = obj.material_slots[poly.material_index].material.name[len("parity_"):]
                expected = self.booth.cell_uv(colour)
                for loop_index in poly.loop_indices:
                    self.assertAlmostEqual(uv.data[loop_index].uv[0], expected[0])
                    self.assertAlmostEqual(uv.data[loop_index].uv[1], expected[1])

    def test_classify_and_blobs(self) -> None:
        import numpy as np
        rgb = np.zeros((20, 30, 3), dtype=np.float32)
        rgb[2:8, 2:8] = (0.48, 0.14, 0.0)  # X-Plane's night red
        rgb[10:16, 10:20] = (0.0, 0.15, 0.52)  # its blue
        rgb[0:2, 25:30] = (0.5, 0.5, 0.5)  # grey matches nothing
        labels = self.pb.classify(rgb)
        names = self.pb.PALETTE_NAMES
        self.assertEqual(labels[4, 4], names.index("red"))
        self.assertEqual(labels[12, 15], names.index("blue"))
        self.assertEqual(labels[18, 1], names.index("black"))
        self.assertEqual(labels[1, 27], names.index("white"))  # grey normalises to white
        found = self.pb.blobs(rgb.max(axis=2) > 0.3, min_pixels=5)
        self.assertEqual(len(found), 3)
        self.assertEqual(found[0][0], 60)  # the blue block is the biggest

    def test_compare_palette_passes_on_identical_and_fails_on_shift(self) -> None:
        import numpy as np
        from types import SimpleNamespace
        a = np.zeros((60, 80, 3), dtype=np.float32)
        a[20:40, 30:50] = (1, 0, 0)
        b = a.copy() * 0.5  # darker, as X-Plane would show it
        keep = np.ones((60, 80), dtype=bool)
        args = SimpleNamespace(min_agreement=0.97, min_iou=0.85)
        ok, _ = self.pb.compare_palette(a, b, keep, args, lines := [])
        self.assertTrue(ok, lines)
        shifted = np.zeros_like(a)
        shifted[20:40, 45:65] = (1, 0, 0)
        ok, diff = self.pb.compare_palette(a, shifted, keep, args, lines := [])
        self.assertFalse(ok, lines)
        self.assertTrue(any("red" in l and "<-- low" in l for l in lines), lines)
        self.assertTrue((diff[30, 32] == (1, 0, 0)).all())  # disagreement painted red

    def test_compare_lights(self) -> None:
        import numpy as np
        from types import SimpleNamespace
        a = np.zeros((60, 80, 3), dtype=np.float32)
        a[28:33, 38:43] = (1, 0, 0)
        b = np.zeros_like(a)
        b[30:36, 40:46] = (0.9, 0.2, 0.1)
        keep = np.ones((60, 80), dtype=bool)
        args = SimpleNamespace(max_light_offset=30)
        ok, _ = self.pb.compare_lights(a, b, keep, args, lines := [])
        self.assertTrue(ok, lines)
        b[:, :] = 0
        ok, _ = self.pb.compare_lights(a, b, keep, args, lines := [])
        self.assertFalse(ok, lines)
        self.assertTrue(any("missing" in l for l in lines), lines)

    def test_compare_lights_flare_is_a_billboard(self) -> None:
        """A flash caught at its peak: a red glow bigger than 2% of the picture with a white core"""
        import numpy as np
        from types import SimpleNamespace
        a = np.zeros((60, 80, 3), dtype=np.float32)
        a[28:33, 38:43] = (1, 0, 0)
        b = np.zeros_like(a)
        b[15:50, 25:60] = (0.7, 0.1, 0.05)  # the red glow, a quarter of the picture
        b[29:34, 39:44] = (1, 1, 1)  # its white core
        keep = np.ones((60, 80), dtype=bool)
        ok, _ = self.pb.compare_lights(a, b, keep, SimpleNamespace(max_light_offset=30), lines := [])
        self.assertTrue(ok, lines)
        self.assertIn("X-Plane 1 billboards, 0 spill", lines[0])
        # Without a core it's a spill on the floor
        b[29:34, 39:44] = (0.7, 0.1, 0.05)
        ok, _ = self.pb.compare_lights(a, b, keep, SimpleNamespace(max_light_offset=30), lines := [])
        self.assertFalse(ok, lines)
        self.assertIn("X-Plane 0 billboards, 1 spill", lines[0])

    def test_sample_scene_and_export_modes(self) -> None:
        """The sample builds, and each mode exports it: the OBJ has the mode's textures"""
        blend = os.path.join(self.tmp, "parity_sample", "sample.blend")
        env = dict(os.environ)
        env.setdefault("BLENDER_USER_SCRIPTS", os.environ.get("BLENDER_USER_SCRIPTS", ""))
        script = os.path.join(PARITY_DIR, "parity_blender.py")

        def run(*args):
            command = [bpy.app.binary_path, "-b", "--factory-startup", "--addons", "io_xplane2blender", "-noaudio",
                       "--python", script, "--", *args]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8",
                                    errors="replace", env=env)
            self.assertEqual(result.returncode, 0, result.stdout[-3000:])
            return result.stdout

        run("sample", blend)
        for mode, texture in (("palette", "palette.png"), ("textured", "albedo.png"), ("lights", "palette.png")):
            work = os.path.join(self.tmp, "parity_sample", mode)
            out = run("export", blend, "parity_sample", work, "--mode", mode, "--dataref", "sim/cockpit2/controls/flap_ratio=0.75")
            self.assertIn("EXPORTED", out)
            obj = open(os.path.join(work, "model.obj")).read()
            self.assertIn(f"TEXTURE\t{texture}", obj)
            self.assertIn(f"TEXTURE_LIT\t{texture}", obj)
            # Lights only in the lights check, meshes in the others
            self.assertEqual("LIGHT_NAMED\ttaxi_r" in obj, mode == "lights")
            self.assertEqual("TRIS" in obj, mode != "lights")
            self.assertTrue(os.path.exists(os.path.join(work, "VIEWS")))
            self.assertIn("sim/cockpit2/controls/flap_ratio 0.75", open(os.path.join(work, "DATAREFS")).read())


runTestCases([TestParityTool])
