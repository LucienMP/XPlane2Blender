"""
#253, #653, #562 in X-Plane: a keyframe table whose keys all give the same transform is
now written as one static ANIM_trans / ANIM_rotate. X-Plane must draw that exactly as it
drew the two-key table the exporter used to write, so the same scene is photographed
twice, once with each form, and the two X-Plane runs are compared.

Opt-in: python tests.py --xplane (X-Plane closed, Web API on).
"""
import os
import re
import subprocess
import sys
import unittest

import bpy

from io_xplane2blender.tests import *

ADDON = os.path.dirname(os.path.abspath(__import__("io_xplane2blender").__file__))
PARITY_PY = os.path.join(ADDON, "xplane_parity", "parity.py")
MOVER = "sim/graphics/animation/sin_wave_2"
OTHER = "sim/cockpit2/engine/actuators/throttle_ratio_all"


def expand_static(text: str, dataref: str) -> str:
    """The OBJ as the exporter wrote it before #253: each static step as a two-key table"""
    out = []
    for line in text.splitlines():
        indent = line[: len(line) - len(line.lstrip())]
        parts = line.split()
        if parts and parts[0] == "ANIM_trans" and len(parts) == 7:
            x, y, z = parts[1:4]
            out += [f"{indent}ANIM_trans_begin\t{dataref}",
                    f"{indent}ANIM_trans_key\t0\t{x}\t{y}\t{z}",
                    f"{indent}ANIM_trans_key\t1\t{x}\t{y}\t{z}",
                    f"{indent}ANIM_trans_end"]
        elif parts and parts[0] == "ANIM_rotate" and len(parts) == 6:
            ax, ay, az, deg = parts[1:5]
            out += [f"{indent}ANIM_rotate_begin\t{ax}\t{ay}\t{az}\t{dataref}",
                    f"{indent}ANIM_rotate_key\t0\t{deg}",
                    f"{indent}ANIM_rotate_key\t1\t{deg}",
                    f"{indent}ANIM_rotate_end"]
        else:
            out.append(line)
    return "\n".join(out) + "\n"


@unittest.skipUnless(os.environ.get("XP2B_XPLANE_TESTS"), "X-Plane visual checks run only with tests.py --xplane")
class TestParityStatic(XPlaneTestCase):
    work = os.path.join(get_tmp_folder(), "parity_static")

    def _parity(self, *args):
        command = [sys.executable, PARITY_PY, "--blender", bpy.app.binary_path, *args]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
        print(result.stdout[-4000:])
        return result

    def test_static_steps_draw_like_the_old_tables(self) -> None:
        blend = os.path.join(self.work, "sample.blend")
        self.assertEqual(self._parity("sample", "--kind", "static", "--blend", blend).returncode, 0)
        new, old = os.path.join(self.work, "new"), os.path.join(self.work, "old")
        datarefs = ["--dataref", f"{MOVER}=0.5", "--dataref", f"{OTHER}=0.5"]

        # 1. The export as it is now. Its comparison with Blender is kept for the record:
        # X-Plane adds every dataref's table on an object, Blender shows one pose
        self._parity("run", blend, "parity_sample", "--work", new, *datarefs)
        exported = open(os.path.join(new, "model.obj")).read()
        self.assertEqual(len(re.findall(r"(?m)^\s*ANIM_trans\t", exported)), 2, exported)
        self.assertEqual(len(re.findall(r"(?m)^\s*ANIM_rotate\t", exported)), 1, exported)

        # 2. The same OBJ with every static step written as the old two-key table
        os.makedirs(old, exist_ok=True)
        old_obj = os.path.join(old, "old_form.obj")
        with open(old_obj, "w", newline="\n") as f:
            f.write(expand_static(exported, OTHER))
        result = self._parity("run", blend, "parity_sample", "--work", old, "--obj", old_obj, "--against", new, *datarefs)
        report = open(os.path.join(old, "report.txt"), encoding="utf-8").read()
        self.assertIn("RESULT: PASS", report, report)
        self.assertEqual(result.returncode, 0)


runTestCases([TestParityStatic])
