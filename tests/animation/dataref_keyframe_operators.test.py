import bpy

from io_xplane2blender.tests import *
from io_xplane2blender.xplane_helpers import get_action_fcurves


class TestDatarefKeyframeOperators(XPlaneTestCase):
    """
    The add/remove dataref (keyframe) operators on objects and bones,
    including Blender 4.4+ slotted Actions where bone dataref keyframes
    live on the Armature datablock, separate from the Object
    """

    def _keyframe_datarefs(self, datarefs, add_keyframe) -> None:
        """Gives datarefs a, b, c values 1/2/3 on frame 1 and 10/20/30 on frame 10"""
        for path, scale in zip("abc", (1, 2, 3)):
            datarefs.add().path = path
        for frame, factor in ((1, 1), (10, 10)):
            bpy.context.scene.frame_set(frame)
            for i, dataref in enumerate(datarefs):
                dataref.value = (i + 1) * factor
                add_keyframe(i)

    def _assertDatarefFCurves(self, anim_data, prefix, expected) -> None:
        """expected is {index: (value at frame 1, value at frame 10)}"""
        fcurves = {
            f.data_path: f
            for f in get_action_fcurves(anim_data)
            if f.data_path.startswith(prefix)
        }
        self.assertEqual(
            sorted(fcurves), sorted(f"{prefix}[{i}].value" for i in expected)
        )
        for i, values in expected.items():
            keyframes = fcurves[f"{prefix}[{i}].value"].keyframe_points
            self.assertEqual([kf.co[1] for kf in keyframes], list(values))
            self.assertEqual({kf.interpolation for kf in keyframes}, {"LINEAR"})

    def test_object_dataref_keyframes(self) -> None:
        obj = bpy.data.objects["Cube"]
        bpy.context.view_layer.objects.active = obj
        obj.keyframe_insert("location", frame=1)

        def add_keyframe(index):
            with bpy.context.temp_override(object=obj):
                bpy.ops.object.add_xplane_dataref_keyframe(index=index)

        self._keyframe_datarefs(obj.xplane.datarefs, add_keyframe)
        self._assertDatarefFCurves(
            obj.animation_data,
            "xplane.datarefs",
            {0: (1, 10), 1: (2, 20), 2: (3, 30)},
        )

        with bpy.context.temp_override(object=obj):
            bpy.ops.object.remove_xplane_dataref(index=0)
        self.assertEqual([d.path for d in obj.xplane.datarefs], ["b", "c"])
        self._assertDatarefFCurves(
            obj.animation_data, "xplane.datarefs", {0: (2, 20), 1: (3, 30)}
        )

    def test_bone_dataref_keyframes(self) -> None:
        bpy.ops.object.armature_add()
        armature = bpy.context.active_object
        bone = armature.data.bones[0]
        armature.data.bones.active = bone
        armature.pose.bones[0].keyframe_insert("location", frame=1)

        def add_keyframe(index):
            with bpy.context.temp_override(object=armature, bone=bone):
                bpy.ops.bone.add_xplane_dataref_keyframe(index=index)

        self._keyframe_datarefs(bone.xplane.datarefs, add_keyframe)
        prefix = f'bones["{bone.name}"].xplane.datarefs'
        # Not on the Object, which animates the pose
        self.assertFalse(
            [
                f
                for f in get_action_fcurves(armature.animation_data)
                if "xplane" in f.data_path
            ]
        )
        self._assertDatarefFCurves(
            armature.data.animation_data,
            prefix,
            {0: (1, 10), 1: (2, 20), 2: (3, 30)},
        )

        with bpy.context.temp_override(object=armature, bone=bone):
            bpy.ops.bone.remove_xplane_dataref(index=1)
        self.assertEqual([d.path for d in bone.xplane.datarefs], ["a", "c"])
        self._assertDatarefFCurves(
            armature.data.animation_data, prefix, {0: (1, 10), 1: (3, 30)}
        )

        bpy.context.scene.frame_set(10)
        with bpy.context.temp_override(object=armature, bone=bone):
            bpy.ops.bone.remove_xplane_dataref_keyframe(index=1)
        self._assertDatarefFCurves(
            armature.data.animation_data, prefix, {0: (1, 10), 1: (3,)}
        )


runTestCases([TestDatarefKeyframeOperators])
