"""
Keyframe tables whose keys all give the same transform are written as a static
ANIM_trans / ANIM_rotate instead (#253, #653, #562). That happens on a bone with two
datarefs when only one of them really moves it: every dataref's table samples the
object's transform at its own keyframes.
"""
from typing import List

import bpy
from mathutils import Vector

from io_xplane2blender import xplane_constants
from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers
from io_xplane2blender.tests.test_creation_helpers import KeyframeInfo

MOVER = "sim/graphics/animation/sin_wave_2"
OTHER = "sim/cockpit2/engine/actuators/throttle_ratio_all"


class TestStaticTableCollapse(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        test_creation_helpers.delete_everything()
        self.root = test_creation_helpers.create_datablock_empty(
            test_creation_helpers.DatablockInfo("EMPTY", "root")
        )
        self.root.xplane.isExportableRoot = True
        self.root.xplane.layer.export_type = xplane_constants.EXPORT_TYPE_AIRCRAFT
        self.cube = test_creation_helpers.create_datablock_mesh(
            test_creation_helpers.DatablockInfo(
                "MESH", "cube", parent_info=test_creation_helpers.ParentInfo(self.root)
            )
        )
        logger.clearMessages()

    def _anim_lines(self) -> List[str]:
        out = self.exportExportableRoot(self.root)
        return [
            l.strip()
            for l in out.splitlines()
            if l.strip().startswith("ANIM_")
        ]

    def test_static_translation_table_becomes_anim_trans(self) -> None:
        # The mover goes from x=2 to x=1 between frames 1 and 10. The other dataref's
        # keys, at frames 1 and 20, both see x=2
        test_creation_helpers.set_animation_data(self.cube, [
            KeyframeInfo(idx=1, dataref_path=MOVER, dataref_value=0.0, location=(2, 0, 0)),
            KeyframeInfo(idx=10, dataref_path=MOVER, dataref_value=1.0, location=(1, 0, 0)),
        ])
        test_creation_helpers.set_animation_data(self.cube, [
            KeyframeInfo(idx=1, dataref_path=OTHER, dataref_value=0.0, location=(2, 0, 0)),
            KeyframeInfo(idx=20, dataref_path=OTHER, dataref_value=1.0, location=(2, 0, 0)),
        ])
        lines = self._anim_lines()
        self.assertIn(f"ANIM_trans_begin\t{MOVER}", lines)
        self.assertNotIn(f"ANIM_trans_begin\t{OTHER}", lines)
        self.assertIn("ANIM_trans\t2\t0\t0\t2\t0\t0", lines)
        self.assertEqual(lines.count("ANIM_begin"), 1)

    def test_static_zero_translation_table_is_dropped(self) -> None:
        test_creation_helpers.set_animation_data(self.cube, [
            KeyframeInfo(idx=1, dataref_path=MOVER, dataref_value=0.0, location=(0, 0, 0)),
            KeyframeInfo(idx=10, dataref_path=MOVER, dataref_value=1.0, location=(0, 0, 3)),
        ])
        test_creation_helpers.set_animation_data(self.cube, [
            KeyframeInfo(idx=1, dataref_path=OTHER, dataref_value=0.0, location=(0, 0, 0)),
            KeyframeInfo(idx=20, dataref_path=OTHER, dataref_value=1.0, location=(0, 0, 0)),
        ])
        lines = self._anim_lines()
        self.assertIn(f"ANIM_trans_begin\t{MOVER}", lines)
        self.assertEqual([l for l in lines if l.startswith("ANIM_trans\t")], [])

    def test_static_rotation_table_becomes_anim_rotate(self) -> None:
        # The mover rotates 0 to 45 about Z between frames 1 and 10; the other
        # dataref's keys at frames 10 and 20 both see 45
        test_creation_helpers.set_animation_data(self.cube, [
            KeyframeInfo(idx=1, dataref_path=MOVER, dataref_value=0.0, rotation=(0, 0, 0)),
            KeyframeInfo(idx=10, dataref_path=MOVER, dataref_value=1.0, rotation=(0, 0, 45)),
        ])
        test_creation_helpers.set_animation_data(self.cube, [
            KeyframeInfo(idx=10, dataref_path=OTHER, dataref_value=0.0, rotation=(0, 0, 45)),
            KeyframeInfo(idx=20, dataref_path=OTHER, dataref_value=1.0, rotation=(0, 0, 45)),
        ])
        lines = self._anim_lines()
        self.assertEqual(len([l for l in lines if l.startswith("ANIM_rotate_begin")]), 1)
        self.assertTrue(any(l.startswith("ANIM_rotate_begin") and l.endswith(MOVER) for l in lines), lines)
        static = [l for l in lines if l.startswith("ANIM_rotate\t")]
        self.assertEqual(len(static), 1, lines)
        parts = static[0].split("\t")
        self.assertEqual(parts[1:4], ["0", "1", "0"])
        self.assertEqual(parts[4], parts[5])
        self.assertAlmostEqual(float(parts[4]), 45, places=3)

    def test_really_animated_tables_are_untouched(self) -> None:
        test_creation_helpers.set_animation_data(self.cube, [
            KeyframeInfo(idx=1, dataref_path=MOVER, dataref_value=0.0, location=(0, 0, 0)),
            KeyframeInfo(idx=10, dataref_path=MOVER, dataref_value=1.0, location=(1, 0, 0)),
        ])
        test_creation_helpers.set_animation_data(self.cube, [
            KeyframeInfo(idx=10, dataref_path=OTHER, dataref_value=0.0, location=(1, 0, 0)),
            KeyframeInfo(idx=20, dataref_path=OTHER, dataref_value=1.0, location=(0, 1, 0)),
        ])
        lines = self._anim_lines()
        self.assertEqual(len([l for l in lines if l.startswith("ANIM_trans_begin")]), 2)
        self.assertEqual([l for l in lines if l.startswith("ANIM_trans\t")], [])


runTestCases([TestStaticTableCollapse])
