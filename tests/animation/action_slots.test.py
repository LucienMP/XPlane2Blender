"""
Blender 4.4+ slotted Actions (#765): one Action can animate several datablocks, each through its
own slot. Each object must export only its own slot's animation, and an Action assigned with no
slot chosen (which animates nothing) gives a warning instead of silently exporting no animation.
"""
import math
import re
from typing import Dict, List

import bpy

from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers as tch
from io_xplane2blender.xplane_types import xplane_file


def warnings_containing(text: str) -> List[str]:
    return [w["message"] for w in logger.findWarnings() if text in w["message"]]


class TestActionSlots(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        tch.delete_everything()
        self.mat = bpy.data.materials.new("mat")
        self.root = bpy.data.objects.new("root", None)
        bpy.context.scene.collection.objects.link(self.root)
        self.root.xplane.isExportableRoot = True
        logger.clearMessages()

    def tri(self, name: str, x: float) -> bpy.types.Object:
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [], [(0, 1, 2)])
        mesh.materials.append(self.mat)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = self.root
        obj.location = (x, 0, 0)
        return obj

    def animate(self, obj: bpy.types.Object, path: str, degrees: float) -> None:
        """A dataref 0..1 rotating obj 0..degrees about Z"""
        dataref = obj.xplane.datarefs.add()
        dataref.path = path
        for frame, value, angle in ((1, 0, 0.0), (10, 1, math.radians(degrees))):
            dataref.value = value
            obj.rotation_euler = (0, 0, angle)
            obj.keyframe_insert(data_path="xplane.datarefs[0].value", frame=frame)
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)

    def export(self) -> str:
        bpy.context.scene.frame_set(1)
        # The way the Export button does it, which also clears the keyframe cache
        files = xplane_file.createFilesFromBlenderRootObjects(bpy.context.scene, bpy.context.view_layer)
        return files[0].write()

    def rotations(self, out: str) -> Dict[str, float]:
        """dataref -> last ANIM_rotate_key angle"""
        found, current = {}, None
        for line in out.splitlines():
            f = line.split()
            if f and f[0] == "ANIM_rotate_begin":
                current = f[4]
            elif f and f[0] == "ANIM_rotate_key" and current:
                found[current] = round(float(f[2]), 2)
        return found

    def test_shared_action_two_slots(self) -> None:
        door, flap = self.tri("door", -2), self.tri("flap", 2)
        self.animate(door, "sim/test/door", 90)
        self.animate(flap, "sim/test/flap", 30)
        # Move flap's channels into a second slot of door's Action, and give flap that slot
        shared = door.animation_data.action
        flap_action = flap.animation_data.action
        slot = shared.slots.new(id_type="OBJECT", name="flap")
        bag = shared.layers[0].strips[0].channelbag(slot, ensure=True)
        for fcurve in flap_action.layers[0].strips[0].channelbag(flap_action.slots[0]).fcurves:
            new = bag.fcurves.new(fcurve.data_path, index=fcurve.array_index)
            for point in fcurve.keyframe_points:
                new.keyframe_points.insert(point.co[0], point.co[1]).interpolation = "LINEAR"
        flap.animation_data.action = shared
        flap.animation_data.action_slot = slot
        bpy.data.actions.remove(flap_action)
        self.assertEqual(door.animation_data.action, flap.animation_data.action)
        self.assertNotEqual(door.animation_data.action_slot, flap.animation_data.action_slot)

        self.assertEqual(self.rotations(self.export()), {"sim/test/door": 90.0, "sim/test/flap": 30.0})
        self.assertEqual(warnings_containing("none of its slots"), [])

    def test_missing_slot_warns(self) -> None:
        door = self.tri("door", 0)
        self.animate(door, "sim/test/door", 90)
        door.animation_data.action_slot = None
        out = self.export()
        self.assertNotIn("ANIM_rotate_begin", out)
        self.assertEqual(len(warnings_containing("'door' has the Action")), 1)
        logger.clearMessages()

    def test_missing_slot_on_armature_warns_once(self) -> None:
        arm = tch.create_datablock_armature(
            tch.DatablockInfo("ARMATURE", "arm", parent_info=tch.ParentInfo(self.root)),
            extra_bones=2,
            bone_direction=tch.Vector((0, 0, 1)),
        )
        for bone in arm.data.bones:
            dataref = bone.xplane.datarefs.add()
            dataref.path = "sim/test/" + bone.name
            for frame, value in ((1, 0), (10, 1)):
                dataref.value = value
                arm.data.keyframe_insert(data_path=f'bones["{bone.name}"].xplane.datarefs[0].value', frame=frame)
        self.assertGreater(len(arm.data.bones), 1)
        arm.data.animation_data.action_slot = None
        self.export()
        self.assertEqual(len(warnings_containing("The armature data of 'arm'")), 1)
        logger.clearMessages()


runTestCases([TestActionSlots])
