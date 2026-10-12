import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import bpy

from io_xplane2blender import xplane_library
from io_xplane2blender.tests import *
from io_xplane2blender.xplane_constants import (
    EXPORT_TYPE_SCENERY,
    LIBRARY_MODE_BACKUP,
    LIBRARY_MODE_EXCLUDE,
    LIBRARY_MODE_EXPORT,
    LIBRARY_MODE_EXTEND,
)

PACK = Path(get_tmp_folder()) / "library_txt_export" / "Custom Scenery" / "XP2B Library Test"
LOOSE = Path(get_tmp_folder()) / "library_txt_export" / "loose"


def props(**kwargs) -> SimpleNamespace:
    """Stands in for XPlaneLibraryExport"""
    defaults = dict(
        enabled=True, virtual_path="lib/xp2b/oak.obj", mode=LIBRARY_MODE_EXPORT, use_ratio=False,
        ratio=1.0, seasonal=False, season_spr=False, season_sum=False, season_fal=False, season_win=False,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestLibraryTxtExport(XPlaneTestCase):
    """library_line, update_library_txt, and the whole export: seasonal OBJs in a scenery pack"""

    SEASONS = {"green": ("spr", "sum"), "bare": ("fal",), "snow": ("win",)}

    def setUp(self):
        super().setUp()
        shutil.rmtree(LOOSE.parent, ignore_errors=True)
        os.makedirs(LOOSE)
        os.makedirs(PACK)
        self.txt = str(LOOSE / "library.txt")
        # The scene isn't reloaded between tests
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj)
        quad = bpy.data.meshes.new("quad")
        quad.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
        quad.materials.append(bpy.data.materials.get("oak") or bpy.data.materials.new("oak"))
        for name, seasons in self.SEASONS.items():
            root = bpy.data.objects.new(f"oak_{name}", None)
            bpy.context.collection.objects.link(root)
            root.xplane.isExportableRoot = True
            layer = root.xplane.layer
            layer.name = f"objects/oak_{name}"
            layer.export_type = EXPORT_TYPE_SCENERY
            layer.library.enabled = True
            layer.library.virtual_path = "lib/xp2b_test/oak.obj"
            layer.library.seasonal = True
            for s in seasons:
                setattr(layer.library, f"season_{s}", True)
            mesh = bpy.data.objects.new(f"oak_{name}_mesh", quad)
            bpy.context.collection.objects.link(mesh)
            mesh.parent = root

    def test_modes(self) -> None:
        for mode, command in [
            (LIBRARY_MODE_EXPORT, "EXPORT"),
            (LIBRARY_MODE_EXTEND, "EXPORT_EXTEND"),
            (LIBRARY_MODE_EXCLUDE, "EXPORT_EXCLUDE"),
            (LIBRARY_MODE_BACKUP, "EXPORT_BACKUP"),
        ]:
            with self.subTest(mode=mode):
                self.assertEqual(
                    xplane_library.library_line(props(mode=mode), "objects/oak.obj", "oak"),
                    f"{command}\tlib/xp2b/oak.obj\tobjects/oak.obj",
                )

    def test_ratio(self) -> None:
        self.assertEqual(
            xplane_library.library_line(props(use_ratio=True, ratio=0.25), "objects/oak.obj", "oak"),
            "EXPORT_RATIO\t0.25\tlib/xp2b/oak.obj\tobjects/oak.obj",
        )

    def test_seasons(self) -> None:
        for mode, command in [
            (LIBRARY_MODE_EXPORT, "EXPORT_SEASON"),
            (LIBRARY_MODE_EXTEND, "EXPORT_EXTEND_SEASON"),
            (LIBRARY_MODE_EXCLUDE, "EXPORT_EXCLUDE_SEASON"),
        ]:
            with self.subTest(mode=mode):
                p = props(mode=mode, seasonal=True, season_fal=True, season_win=True)
                self.assertEqual(
                    xplane_library.library_line(p, "objects/oak_bare.obj", "oak"),
                    f"{command}\tfal,win\tlib/xp2b/oak.obj\tobjects/oak_bare.obj",
                )

    def test_errors(self) -> None:
        for p, message in [
            (props(virtual_path=""), "Library Path is empty"),
            (props(virtual_path="lib/my trees/oak.obj"), "can't contain spaces"),
            (props(seasonal=True), "no season is ticked"),
            (props(seasonal=True, season_spr=True, mode=LIBRARY_MODE_BACKUP), "no seasonal version"),
        ]:
            with self.subTest(message=message):
                logger.clearMessages()
                self.assertIsNone(xplane_library.library_line(p, "objects/oak.obj", "oak"))
                self.assertIn(message, logger.findErrors()[0]["message"])
        logger.clearMessages()

    def read(self) -> str:
        return Path(self.txt).read_text(encoding="utf8")

    def test_new_file_has_header_and_block(self) -> None:
        xplane_library.update_library_txt(
            self.txt, "trees.blend", ["a.obj"], ["EXPORT\tlib/xp2b/a.obj\ta.obj"]
        )
        self.assertEqual(
            self.read(),
            "A\n1200\nLIBRARY\n\n"
            "# BEGIN XPlane2Blender: trees.blend\n"
            "EXPORT\tlib/xp2b/a.obj\ta.obj\n"
            "# END XPlane2Blender: trees.blend\n",
        )

    def test_nothing_to_add_leaves_no_file(self) -> None:
        xplane_library.update_library_txt(self.txt, "trees.blend", ["a.obj"], [])
        self.assertFalse(os.path.exists(self.txt))

    def test_keeps_other_content(self) -> None:
        Path(self.txt).write_text(
            "I\n800\nLIBRARY\n\n# hand written\nEXPORT lib/other.obj other.obj\n", encoding="utf8"
        )
        xplane_library.update_library_txt(self.txt, "trees.blend", ["a.obj"], ["EXPORT\tlib/a.obj\ta.obj"])
        xplane_library.update_library_txt(self.txt, "rocks.blend", ["r.obj"], ["EXPORT\tlib/r.obj\tr.obj"])
        # Re-exporting a.obj with a new path replaces only its line
        xplane_library.update_library_txt(self.txt, "trees.blend", ["a.obj"], ["EXPORT\tlib/a2.obj\ta.obj"])
        self.assertEqual(
            self.read(),
            "I\n800\nLIBRARY\n\n# hand written\nEXPORT lib/other.obj other.obj\n\n"
            "# BEGIN XPlane2Blender: trees.blend\nEXPORT\tlib/a2.obj\ta.obj\n# END XPlane2Blender: trees.blend\n\n"
            "# BEGIN XPlane2Blender: rocks.blend\nEXPORT\tlib/r.obj\tr.obj\n# END XPlane2Blender: rocks.blend\n",
        )

    def test_turning_off_removes_lines_and_empty_block(self) -> None:
        xplane_library.update_library_txt(
            self.txt, "trees.blend", ["a.obj", "b.obj"], ["EXPORT\tlib/a.obj\ta.obj", "EXPORT\tlib/b.obj\tb.obj"]
        )
        xplane_library.update_library_txt(self.txt, "trees.blend", ["a.obj"], [])
        self.assertIn("EXPORT\tlib/b.obj\tb.obj", self.read())
        self.assertNotIn("a.obj", self.read())
        xplane_library.update_library_txt(self.txt, "trees.blend", ["b.obj"], [])
        self.assertEqual(self.read(), "A\n1200\nLIBRARY\n\n")

    def test_broken_markers(self) -> None:
        Path(self.txt).write_text("A\n1200\nLIBRARY\n# BEGIN XPlane2Blender: trees.blend\n", encoding="utf8")
        self.assertFalse(xplane_library.update_library_txt(self.txt, "trees.blend", ["a.obj"], []))
        self.assertIn("are broken", logger.findErrors()[0]["message"])
        logger.clearMessages()

    def test_mixing_seasonal_and_not_is_an_error(self) -> None:
        xplane_library.update_library_txt(
            self.txt,
            "trees.blend",
            ["a.obj", "b.obj"],
            ["EXPORT\tlib/oak.obj\ta.obj", "EXPORT_SEASON\tspr,sum,fal,win\tlib/oak.obj\tb.obj"],
        )
        self.assertIn("both by season and not by season", logger.findErrors()[0]["message"])
        logger.clearMessages()

    def test_missing_season_is_a_warning(self) -> None:
        xplane_library.update_library_txt(
            self.txt, "trees.blend", ["a.obj"], ["EXPORT_SEASON\tspr,sum\tlib/oak.obj\ta.obj"]
        )
        self.assertFalse(logger.hasErrors())
        self.assertIn("no OBJ for fal, win", logger.findWarnings()[0]["message"])
        logger.clearMessages()

    def export(self) -> set:
        return bpy.ops.export.xplane_obj(filepath=str(PACK / "export.obj"))

    def test_seasonal_library(self) -> None:
        self.assertEqual(self.export(), {"FINISHED"})
        for name in self.SEASONS:
            self.assertTrue((PACK / "objects" / f"oak_{name}.obj").exists())
        lines = (PACK / "library.txt").read_text(encoding="utf8").splitlines()
        self.assertEqual(lines[:3], ["A", "1200", "LIBRARY"])
        self.assertEqual(
            [l for l in lines if l.startswith("EXPORT")],
            [
                "EXPORT_SEASON\tfal\tlib/xp2b_test/oak.obj\tobjects/oak_bare.obj",
                "EXPORT_SEASON\tspr,sum\tlib/xp2b_test/oak.obj\tobjects/oak_green.obj",
                "EXPORT_SEASON\twin\tlib/xp2b_test/oak.obj\tobjects/oak_snow.obj",
            ],
        )

    def test_turning_off_one_obj(self) -> None:
        self.export()
        bpy.data.objects["oak_snow"].xplane.layer.library.enabled = False
        self.export()  # A missing season is only a warning
        text = (PACK / "library.txt").read_text(encoding="utf8")
        self.assertNotIn("oak_snow", text)
        self.assertIn("oak_green", text)

    def test_error_cancels(self) -> None:
        bpy.data.objects["oak_snow"].xplane.layer.library.virtual_path = ""
        self.assertEqual(self.export(), {"CANCELLED"})
        self.assertFalse((PACK / "library.txt").exists())


runTestCases([TestLibraryTxtExport])
