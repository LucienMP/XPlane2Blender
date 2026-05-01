from pathlib import Path
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import bpy

from io_xplane2blender import xplane_props
from io_xplane2blender.xplane_helpers import get_action_fcurves
from io_xplane2blender.xplane_config import *
from io_xplane2blender.xplane_constants import (
    MAX_COCKPIT_REGIONS,
    MAX_LODS,
    EXPORT_TYPE_AIRCRAFT,
    EXPORT_TYPE_COCKPIT,
)
from io_xplane2blender.xplane_ops_dev import *
from io_xplane2blender.xplane_utils import (
    xplane_commands_txt_parser,
    xplane_datarefs_txt_parser,
    xplane_scene_report,
    xplane_wiper_gradient,
)


# Function: findFCurveByPath
# Helper function to find an FCurve by an data-path.
#
# Parameters:
#   list - FCurves
#   string - data path.
#
# Returns:
#   FCurve or None if no FCurve could be found.
def findFCurveByPath(fcurves, path):
    return next((fcurve for fcurve in fcurves if fcurve.data_path == path), None)


def makeKeyframesLinear(anim_data: Optional[bpy.types.AnimData], path: str) -> None:
    """
    Sets the interpolation of the keyframes of path to linear,
    since that is how X-Plane interpolates between them
    """
    fcurve = findFCurveByPath(get_action_fcurves(anim_data), path)
    if fcurve:
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = "LINEAR"


def removeDatarefFCurves(
    anim_data: Optional[bpy.types.AnimData],
    index: int,
    bone: Optional[bpy.types.Bone] = None,
) -> None:
    """
    Removes the FCurve of the XPlaneDataref removed from index and renumbers
    the FCurves of the datarefs after it, so they keep their keyframes
    """
    fcurves = get_action_fcurves(anim_data)
    prefix = getDatarefValuePath(index, bone)[: -len(f"{index}].value")]

    def dataref_index(fcurve: bpy.types.FCurve) -> Optional[int]:
        if not fcurve.data_path.startswith(prefix):
            return None
        idx, _, rest = fcurve.data_path[len(prefix) :].partition("]")
        return int(idx) if idx.isdigit() and rest == ".value" else None

    removed = findFCurveByPath(fcurves, getDatarefValuePath(index, bone))
    if removed:
        fcurves.remove(fcurve=removed)

    later = [
        (i, fcurve)
        for fcurve in fcurves
        if (i := dataref_index(fcurve)) is not None and i > index
    ]
    for i, fcurve in sorted(later, key=lambda pair: pair[0]):
        fcurve.data_path = getDatarefValuePath(i - 1, bone)


# Function: getDatarefValuePath
# Returns the data path for a <XPlaneDataref> value.
#
# Parameters:
#   int index - Index of the <XPlaneDataref>
#
# Returns:
#   string - data path
def getDatarefValuePath(index: int, bone: Optional[bpy.types.Bone] = None) -> str:
    """
    Returns the keyframe data path for an XPlaneDataref value on a bone or object"

    index is tied with the remove_xplane_dataref operator.
    """

    if bone:
        return 'bones["%s"].xplane.datarefs[%d].value' % (bone.name, index)
    else:
        return "xplane.datarefs[" + str(index) + "].value"


class OBJECT_OT_add_xplane_axis_detent_range(bpy.types.Operator):
    bl_label = "Add X-Plane Axis Detent Range"
    bl_idname = "object.add_xplane_axis_detent_range"
    bl_description = "Add X-Plane Axis Detent Range"

    def execute(self, context):
        obj = context.object
        obj.xplane.manip.axis_detent_ranges.add()
        return {"FINISHED"}


class OBJECT_OT_remove_xplane_axis_detent_range(bpy.types.Operator):
    bl_label = "Remove Axis Detent Range"
    bl_idname = "object.remove_xplane_axis_detent_range"
    bl_description = "Remove axis detent range"

    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.object
        obj.xplane.manip.axis_detent_ranges.remove(self.index)
        return {"FINISHED"}


class COLLECTION_OT_add_xplane_layer_attribute(bpy.types.Operator):
    bl_label = "Add Layer Property"
    bl_idname = "collection.add_xplane_layer_attribute"
    bl_description = "Add a custom X-Plane Layer Property"

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        coll = bpy.data.collections[self.collection_name]
        coll.xplane.layer.customAttributes.add()
        return {"FINISHED"}


class COLLECTION_OT_remove_xplane_layer_attribute(bpy.types.Operator):
    bl_label = "Remove Layer Property"
    bl_idname = "collection.remove_xplane_layer_attribute"
    bl_description = "Remove the custom X-Plane Layer Property"

    collection_name: bpy.props.StringProperty()
    index: bpy.props.IntProperty()

    def execute(self, context):
        coll = bpy.data.collections[self.collection_name]
        coll.xplane.layer.customAttributes.remove(self.index)
        return {"FINISHED"}


class OBJECT_OT_add_xplane_layer_attribute(bpy.types.Operator):
    bl_label = "Add Layer Property"
    bl_idname = "object.add_xplane_layer_attribute"
    bl_description = "Add a custom X-Plane Layer Property"

    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.object
        obj.xplane.layer.customAttributes.add()
        return {"FINISHED"}


class OBJECT_OT_remove_xplane_layer_attribute(bpy.types.Operator):
    bl_label = "Remove Layer Property"
    bl_idname = "object.remove_xplane_layer_attribute"
    bl_description = "Remove the custom X-Plane Layer Property"

    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.object
        obj.xplane.layer.customAttributes.remove(self.index)
        return {"FINISHED"}


# Class: OBJECT_OT_add_xplane_object_attribute
# Adds a custom attribute to a Blender Object.
class OBJECT_OT_add_xplane_object_attribute(bpy.types.Operator):
    bl_label = "Add Object Property"
    bl_idname = "object.add_xplane_object_attribute"
    bl_description = "Add a custom X-Plane Object Property"

    def execute(self, context):
        obj = context.object
        obj.xplane.customAttributes.add()
        return {"FINISHED"}


# Class: OBJECT_OT_remove_xplane_object_attribute
# Removes a custom attribute from a Blender Object.
class OBJECT_OT_remove_xplane_object_attribute(bpy.types.Operator):
    bl_label = "Remove Object Property"
    bl_idname = "object.remove_xplane_object_attribute"
    bl_description = "Remove the custom X-Plane Object Property"

    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.object
        obj.xplane.customAttributes.remove(self.index)
        return {"FINISHED"}


# Class: OBJECT_OT_add_xplane_object_anim_attribute
# Adds a custom animation attribute to a Blender Object.
class OBJECT_OT_add_xplane_object_anim_attribute(bpy.types.Operator):
    bl_label = "Add Animation Property"
    bl_idname = "object.add_xplane_object_anim_attribute"
    bl_description = "Add a custom X-Plane Animation Property"

    def execute(self, context):
        obj = context.object
        obj.xplane.customAnimAttributes.add()
        return {"FINISHED"}


# Class: OBJECT_OT_remove_xplane_object_anim_attribute
# Removes a custom animation attribute from a Blender Object.
class OBJECT_OT_remove_xplane_object_anim_attribute(bpy.types.Operator):
    bl_label = "Remove Animation Property"
    bl_idname = "object.remove_xplane_object_anim_attribute"
    bl_description = "Remove the custom X-Plane Animation Property"

    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.object
        obj.xplane.customAnimAttributes.remove(self.index)
        return {"FINISHED"}


# Class: OBJECT_OT_add_xplane_material_attribute
# Adds a custom attribute to a Blender Material.
class OBJECT_OT_add_xplane_material_attribute(bpy.types.Operator):
    bl_label = "Add Material Property"
    bl_idname = "object.add_xplane_material_attribute"
    bl_description = "Add a custom X-Plane Material Property"

    def execute(self, context):
        obj = context.object.active_material
        obj.xplane.customAttributes.add()
        return {"FINISHED"}


# Class: OBJECT_OT_remove_xplane_object_attribute
# Removes a custom attribute from a Blender Material.
class OBJECT_OT_remove_xplane_material_attribute(bpy.types.Operator):
    bl_label = "Remove Material Property"
    bl_idname = "object.remove_xplane_material_attribute"
    bl_description = "Remove the custom X-Plane Material Property"

    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.object.active_material
        obj.xplane.customAttributes.remove(self.index)
        return {"FINISHED"}


# Class: OBJECT_OT_add_xplane_light_attribute
# Adds a custom attribute to a Blender Light.
class OBJECT_OT_add_xplane_light_attribute(bpy.types.Operator):
    bl_label = "Add Light Property"
    bl_idname = "object.add_xplane_light_attribute"
    bl_description = "Add a custom X-Plane Light Property"

    def execute(self, context):
        obj = context.object.data
        obj.xplane.customAttributes.add()
        return {"FINISHED"}


# Class: OBJECT_OT_remove_xplane_object_attribute
# Removes a custom attribute from a Blender Light.
class OBJECT_OT_remove_xplane_light_attribute(bpy.types.Operator):
    bl_label = "Remove Light Property"
    bl_idname = "object.remove_xplane_light_attribute"
    bl_description = "Remove the custom X-Plane Light Property"

    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.object.data
        obj.xplane.customAttributes.remove(self.index)
        return {"FINISHED"}


# Class: OBJECT_OT_add_xplane_dataref
# Adds a <XPlaneDataref> to a Blender Object.
class OBJECT_OT_add_xplane_dataref(bpy.types.Operator):
    bl_label = "Add Dataref"
    bl_idname = "object.add_xplane_dataref"
    bl_description = "Add an X-Plane Dataref"

    def execute(self, context):
        obj = context.object
        obj.xplane.datarefs.add()
        return {"FINISHED"}


# Class: OBJECT_OT_remove_xplane_dataref
# Removes a <XPlaneDataref> from a Blender Object.
class OBJECT_OT_remove_xplane_dataref(bpy.types.Operator):
    bl_label = "Remove Dataref"
    bl_idname = "object.remove_xplane_dataref"
    bl_description = "Remove the X-Plane Dataref"

    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.object
        obj.xplane.datarefs.remove(self.index)
        removeDatarefFCurves(obj.animation_data, self.index)

        return {"FINISHED"}


# Class: OBJECT_OT_add_xplane_dataref_keyframe
# Adds a Keyframe to the value of a <XPlaneDataref> of an object.
class OBJECT_OT_add_xplane_dataref_keyframe(bpy.types.Operator):
    bl_label = "Add Dataref keyframe"
    bl_idname = "object.add_xplane_dataref_keyframe"
    bl_description = "Add/Update an X-Plane Dataref keyframe"

    # index here refers to the index of the datarefs collection,
    # NOT the keyframe index
    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.object
        obj.xplane.datarefs[self.index].keyframe_insert(
            data_path="value", group="XPlane Datarefs"
        )
        makeKeyframesLinear(obj.animation_data, getDatarefValuePath(self.index))

        return {"FINISHED"}


# Class: OBJECT_OT_remove_xplane_dataref_keyframe
# Removes a Keyframe from the value of a <XPlaneDataref> of an object.
class OBJECT_OT_remove_xplane_dataref_keyframe(bpy.types.Operator):
    bl_label = "Remove Dataref keyframe"
    bl_idname = "object.remove_xplane_dataref_keyframe"
    bl_description = "Remove the X-Plane Dataref keyframe"

    # index here refers to the index of the datarefs collection,
    # NOT the keyframe index
    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.object
        path = getDatarefValuePath(self.index)
        obj.xplane.datarefs[self.index].keyframe_delete(
            data_path="value", group="XPlane Datarefs"
        )

        return {"FINISHED"}


class COLLECTION_OT_add_xplane_export_path_directive(bpy.types.Operator):
    bl_label = "Add Laminar Library Directive"
    bl_idname = "collection.add_xplane_export_path_directive"
    bl_description = "Add Laminar Library Directive"

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        coll = bpy.data.collections[self.collection_name]
        coll.xplane.layer.export_path_directives.add()
        return {"FINISHED"}


class COLLECTION_OT_remove_xplane_export_path_directive(bpy.types.Operator):
    bl_label = "Remove Laminar Library Directive"
    bl_idname = "collection.remove_xplane_export_path_directive"
    bl_description = "Remove Laminar Library Directive"

    collection_name: bpy.props.StringProperty()
    index: bpy.props.IntProperty()

    def execute(self, context):
        coll = bpy.data.collections[self.collection_name]
        coll.xplane.layer.export_path_directives.remove(self.index)
        return {"FINISHED"}


class OBJECT_OT_add_xplane_export_path_directive(bpy.types.Operator):
    bl_label = "Add Laminar Library Directive"
    bl_idname = "object.add_xplane_export_path_directive"
    bl_description = "Add Laminar Library Directive"

    def execute(self, context):
        obj = context.object
        obj.xplane.layer.export_path_directives.add()
        return {"FINISHED"}


class OBJECT_OT_remove_xplane_export_path_directive(bpy.types.Operator):
    bl_label = "Remove Laminar Library Directive"
    bl_idname = "object.remove_xplane_export_path_directive"
    bl_description = "Remove Laminar Library Directive"

    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.object
        obj.xplane.layer.export_path_directives.remove(self.index)
        return {"FINISHED"}


# Class: BONE_OT_add_xplane_dataref
# Adds a <XPlaneDataref> to a Blender bone.
class BONE_OT_add_xplane_dataref(bpy.types.Operator):
    bl_label = "Add Dataref"
    bl_idname = "bone.add_xplane_dataref"
    bl_description = "Add/Update an X-Plane Dataref"

    def execute(self, context):
        bone = context.bone
        obj = context.object
        bone.xplane.datarefs.add()
        return {"FINISHED"}


# Class: BONE_OT_remove_xplane_dataref
# Removes a <XPlaneDataref> from a Blender bone.
class BONE_OT_remove_xplane_dataref(bpy.types.Operator):
    bl_label = "Remove Dataref"
    bl_idname = "bone.remove_xplane_dataref"
    bl_description = "Remove the X-Plane Dataref"

    index: bpy.props.IntProperty()

    def execute(self, context):
        bone = context.bone
        armature = context.object
        bone.xplane.datarefs.remove(self.index)
        # Bone dataref keyframes live on the Armature datablock, not the Object
        removeDatarefFCurves(armature.data.animation_data, self.index, bone)

        return {"FINISHED"}


# Class: BONE_OT_add_xplane_dataref_keyframe
# Adds a Keyframe to the value of a <XPlaneDataref> of a bone.
class BONE_OT_add_xplane_dataref_keyframe(bpy.types.Operator):
    bl_label = "Add Dataref keyframe"
    bl_idname = "bone.add_xplane_dataref_keyframe"
    bl_description = "Add/Update an X-Plane Dataref keyframe"

    # index here refers to the index of the datarefs collection,
    # NOT the keyframe index
    index: bpy.props.IntProperty()

    # bpy.data.objects["Armature"].data.keyframe_insert(data_path='bones["Bone"].my_prop_group.nested', group="Nested Property")
    def execute(self, context):
        bone = (
            context.active_bone
        )  # context.bone is not always available, for instance, during test_creation_helpers
        # Other uses will be replaced as needed. context.object doesn't appear to be affected
        # See also: https://blender.stackexchange.com/q/31759
        armature = context.object
        path = getDatarefValuePath(self.index, bone)
        armature.data.keyframe_insert(
            data_path=path, group="XPlane Datarefs " + bone.name
        )
        makeKeyframesLinear(armature.data.animation_data, path)

        return {"FINISHED"}


# Class: BONE_OT_remove_xplane_dataref_keyframe
# Removes a Keyframe from the value of a <XPlaneDataref> of a bone.
class BONE_OT_remove_xplane_dataref_keyframe(bpy.types.Operator):
    bl_label = "Remove Dataref keyframe"
    bl_idname = "bone.remove_xplane_dataref_keyframe"
    bl_description = "Remove the X-Plane Dataref keyframe"

    # index here refers to the index of the datarefs collection,
    # NOT the keyframe index
    index: bpy.props.IntProperty()

    def execute(self, context):
        bone = context.bone
        armature = context.object
        path = getDatarefValuePath(self.index, bone)
        armature.data.keyframe_delete(
            data_path=path, group="XPlane Datarefs " + bone.name
        )

        return {"FINISHED"}


# Class: OBJECT_OT_add_xplane_object_condition
# Adds a custom attribute to a Blender Object.
class OBJECT_OT_add_xplane_object_condition(bpy.types.Operator):
    bl_label = "Add Condition"
    bl_idname = "object.add_xplane_object_condition"
    bl_description = "Add an X-Plane condition"

    def execute(self, context):
        obj = context.object
        obj.xplane.conditions.add()
        return {"FINISHED"}


# Class: OBJECT_OT_remove_xplane_object_condition
# Removes a custom attribute from a Blender Object.
class OBJECT_OT_remove_xplane_object_condition(bpy.types.Operator):
    bl_label = "Remove Condition"
    bl_idname = "object.remove_xplane_object_condition"
    bl_description = "Remove X-Plane Condition"

    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.object
        obj.xplane.conditions.remove(self.index)
        return {"FINISHED"}

    # Class: OBJECT_OT_add_xplane_material_condition


# Adds a custom attribute to a Blender Object.
class OBJECT_OT_add_xplane_material_condition(bpy.types.Operator):
    bl_label = "Add Condition"
    bl_idname = "object.add_xplane_material_condition"
    bl_description = "Add an X-Plane condition"

    def execute(self, context):
        obj = context.object.active_material
        obj.xplane.conditions.add()
        return {"FINISHED"}


# Class: OBJECT_OT_remove_xplane_material_condition
# Removes a custom attribute from a Blender Object.
class OBJECT_OT_remove_xplane_material_condition(bpy.types.Operator):
    bl_label = "Remove Condition"
    bl_idname = "object.remove_xplane_material_condition"
    bl_description = "Remove X-Plane Condition"

    index: bpy.props.IntProperty()

    def execute(self, context):
        obj = context.object.active_material
        obj.xplane.conditions.remove(self.index)
        return {"FINISHED"}


# Class: SCENE_OT_export_to_relative_dir
# Exports OBJS into the same folder as the .blend file, and/or folders beneath it
class SCENE_OT_export_to_relative_dir(bpy.types.Operator):
    bl_label = "Export OBJs"
    bl_idname = "scene.export_to_relative_dir"
    bl_description = "Exports OBJs relative to the .blend file"

    # initial_dir that will be prepended to the path.
    initial_dir: bpy.props.StringProperty()

    def execute(self, context):
        bpy.ops.export.xplane_obj(filepath=self.initial_dir, export_is_relative=True)
        return {"FINISHED"}


class XPLANE_OT_CommandSearchToggle(bpy.types.Operator):
    """
    This operator very simply passes it's associated command to the search window, which then opens it in the UI.
    """

    bl_label = "Open/Close Command Search Window"
    bl_description = "Open/Close Command Search Window"
    bl_idname = "xplane.command_search_toggle"

    # Each operator is placed next to a command string property,
    #
    paired_command_prop: bpy.props.StringProperty()

    def execute(self, context):
        command_search_window_state = context.scene.xplane.command_search_window_state
        # Load on first use
        if len(command_search_window_state.command_search_list) == 0:
            filepath = Path(
                xplane_helpers.get_plugin_resources_folder(), "Commands.txt"
            )
            get_commands_txt_result = xplane_commands_txt_parser.get_commands_txt_file_content(
                filepath.as_posix()
            )
            if isinstance(get_commands_txt_result, str):
                short_filepath = "..." + os.path.sep.join(filepath.parts[-3:])
                bpy.ops.xplane.msg(
                    "INVOKE_DEFAULT", msg_text=short_filepath + " could not be parsed",
                )
                return {"CANCELLED"}
            else:
                file_content = get_commands_txt_result

            command_search_list = (
                bpy.context.scene.xplane.command_search_window_state.command_search_list
            )

            for command_info in file_content:
                command_search_list.add()
                command_search_list[-1].command = command_info.command
                command_search_list[-1].command_description = command_info.description

        prop = command_search_window_state.command_prop_dest

        # Toggle ourselves
        if prop == self.paired_command_prop:
            command_search_window_state.command_prop_dest = ""
        else:
            command_search_window_state.command_prop_dest = self.paired_command_prop

        return {"FINISHED"}


class XPLANE_OT_DatarefSearchToggle(bpy.types.Operator):
    """
    This operator very simply passes it's associated dataref to the search window, which then opens it in the UI.
    """

    bl_label = "Open/Close Dataref Search Window"
    bl_description = "Open/Close Dataref Search Window"
    bl_idname = "xplane.dataref_search_toggle"

    # Each operator is placed next to a dataref string property,
    #
    paired_dataref_prop: bpy.props.StringProperty()

    def execute(self, context):
        dataref_search_window_state = context.scene.xplane.dataref_search_window_state
        # Load on first use
        if len(dataref_search_window_state.dataref_search_list) == 0:
            filepath = Path(
                xplane_helpers.get_plugin_resources_folder(), "DataRefs.txt"
            )
            get_datarefs_txt_result = xplane_datarefs_txt_parser.get_datarefs_txt_file_content(
                filepath.as_posix()
            )
            if isinstance(get_datarefs_txt_result, str):
                short_filepath = "..." + os.path.sep.join(filepath.parts[-3:])

                bpy.ops.xplane.msg(
                    "INVOKE_DEFAULT", msg_text=short_filepath + " could not be parsed",
                )
                return {"CANCELLED"}
            else:
                file_content = get_datarefs_txt_result

            dataref_search_list = (
                bpy.context.scene.xplane.dataref_search_window_state.dataref_search_list
            )

            for dref_info in file_content:
                dataref_search_list.add()
                dataref_search_list[-1].dataref_path = dref_info.path
                dataref_search_list[-1].dataref_type = dref_info.type
                dataref_search_list[-1].dataref_is_writable = dref_info.is_writable
                dataref_search_list[-1].dataref_units = dref_info.units
                dataref_search_list[-1].dataref_description = dref_info.description

        prop = dataref_search_window_state.dataref_prop_dest

        # Toggle ourselves
        if prop == self.paired_dataref_prop:
            dataref_search_window_state.dataref_prop_dest = ""
        else:
            dataref_search_window_state.dataref_prop_dest = self.paired_dataref_prop

        return {"FINISHED"}


class XPLANE_OT_XPlaneMessage(bpy.types.Operator):
    bl_idname = "xplane.msg"
    bl_label = "XPlane2Blender Message"

    msg_text: bpy.props.StringProperty()
    icon: bpy.props.StringProperty(default="ERROR")
    # fmt: off
    invoke_style: bpy.props.EnumProperty(
        items=[
            ("invoke_popup",        "Invoke Popup",        "A popup without confirm button"),
            ("invoke_props_dialog", "Invoke Popup Dialog", "A popup with confirm button"),
        ],
        name="Invoke Style",
        description="Which popup style to use",
        default="invoke_props_dialog",
    )
    # fmt: on

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        wm = context.window_manager
        return getattr(wm, self.invoke_style)(self, width=500)

    def draw(self, context):
        self.layout.row().label(text=self.msg_text, icon=self.icon)


# This code is based off of Christian Brinkmann (p2or)
# and Janne Karhu (jahka)'s "Sequency Bakery" Addon. It is also released under
# the same GPL license as XPlane2Blender
class XPLANE_OT_bake_wiper_gradient_texture(bpy.types.Operator):
    bl_label = "Make Wiper Gradient Texture"
    bl_idname = "xplane.bake_wiper_gradient_texture"
    bl_description = "Makes the Wiper Gradient Texture from the Rain Settings of the active collection (may take more than 30 minutes)"

    # fmt: off
    start: bpy.props.IntProperty(
        name="Start",
        description="Specifies which frame to start baking",
        default=1,
        min=1,
    )

    debug_master_filepath: bpy.props.StringProperty(
        "Override Final Texture Path",
        description="Manual override to set the finished image. Can include '//'.",
    )

    debug_reuse_temps: bpy.props.BoolProperty(
        name="Re-use Temporary Images",
        description="Reuse temporaries instead of re-baking, temp files aren't deleted",
        default=False,
    )

    debug_slots: bpy.props.BoolVectorProperty(
        "Slots To Bake",
        description="'False' slots are skipped, without preventing slots afterwards from being baked themselves",
        default=(True,) * 4,
        size=4,
    )
    # fmt: on

    def execute(self, context):
        scene = context.scene
        rain = _get_active_root(context).xplane.layer.rain

        try:
            windshield = bpy.data.objects[rain.wiper_ext_glass_object]
        except KeyError:
            if rain.wiper_ext_glass_object:
                msg = f"Cannot find '{rain.wiper_ext_glass_object}' to be used for exterior glass. Check your spelling in the Rain Settings"
            else:
                msg = f"Must specify object to be used as the exterior glass. Check your Rain Settings"

            bpy.ops.xplane.msg("INVOKE_DEFAULT", msg_text=msg)
            return {"CANCELLED"}

        def collect_wipers() -> List[xplane_props.XPlaneWiperSettings]:
            wipers = []
            for idx in range(1, 5):
                if getattr(rain, f"wiper_{idx}_enabled"):
                    wiper = getattr(rain, f"wiper_{idx}")
                    try:
                        object_name = wiper.object_name
                        object_datablock = bpy.data.objects[object_name]
                    except KeyError:
                        if object_name:
                            msg = f"Could not find '{object_name}'. Check your spelling"
                        else:
                            msg = f"Wiper slot #{idx} must have an object name"
                        bpy.ops.xplane.msg("INVOKE_DEFAULT", msg_text=msg)
                        raise
                    else:
                        wipers.append(wiper)
                else:
                    break
            return wipers

        try:
            wipers = collect_wipers()
        except KeyError:
            # collect_wipers ensures object_names are given and correct
            return {"CANCELLED"}
        else:
            if not wipers:
                bpy.ops.xplane.msg(
                    "INVOKE_DEFAULT", msg_text="Must have at least 1 wiper enabled"
                )
                return {"CANCELLED"}

        def find_bake_nodes(
            bake_object: bpy.types.Object,
        ) -> Tuple[Optional[bpy.types.Image], List[bpy.types.ShaderNode]]:
            """
            Returns the image Cycles will bake to, and for each material the
            image texture node it will bake into.

            Mimics nodeGetActiveTexture(): the active image node wins,
            then the first selected one, then the first one found
            """
            img = None
            nodes = []
            for mat_slot in bake_object.material_slots:
                mat = mat_slot.material
                if not mat or not mat.node_tree:
                    continue
                candidates = [
                    node
                    for node in mat.node_tree.nodes
                    if node.type in {"TEX_IMAGE", "TEX_ENVIRONMENT"} and node.image
                ]
                if not candidates:
                    continue
                active = mat.node_tree.nodes.active
                if active in candidates:
                    node = active
                else:
                    node = next((n for n in candidates if n.select), candidates[0])
                nodes.append(node)
                img = img or node.image
            return img, nodes

        # --- Errors with what you're trying to bake --------------------------
        # Only single object baking for now
        if windshield.type != "MESH":
            bpy.ops.xplane.msg(
                "INVOKE_DEFAULT",
                msg_text=f"The baked object must be a mesh object, is {windshield.type.title()}",
            )
            return {"CANCELLED"}

        if windshield.mode == "EDIT":
            bpy.ops.xplane.msg("INVOKE_DEFAULT", msg_text="Can't bake in edit-mode")
            return {"CANCELLED"}
        # ---------------------------------------------------------------------
        img, bake_nodes = find_bake_nodes(windshield)
        # --- Errors with the bake image --------------------------------------
        if img is None:
            bpy.ops.xplane.msg(
                "INVOKE_DEFAULT", msg_text="No valid image found to bake to"
            )
            return {"CANCELLED"}

        if img.is_dirty:
            bpy.ops.xplane.msg(
                "INVOKE_DEFAULT",
                msg_text="Save the image that's used for baking before use",
            )
            return {"CANCELLED"}

        if img.packed_file is not None:
            bpy.ops.xplane.msg(
                "INVOKE_DEFAULT", msg_text="Can't animation-bake packed file"
            )
            return {"CANCELLED"}

        if img.depth != 32:
            bpy.ops.xplane.msg(
                "INVOKE_DEFAULT",
                msg_text="Bake image must be a PNG with an alpha channel"
            )
            return {"CANCELLED"}
        # ---------------------------------------------------------------------
        img_filepath = Path(bpy.path.abspath(img.filepath, library=img.library))
        bake_temp_folder = img_filepath.parent / Path("_tmp_bake_images")

        def select_objects(wiper: xplane_props.XPlaneWiperSettings) -> None:
            """Select Wiper Object (already guaranteed to exist) then Windshield"""
            for obj in context.selected_objects:
                obj.select_set(False)
            object_datablock = bpy.data.objects[wiper.object_name]
            object_datablock.select_set(True)
            windshield.select_set(True)
            context.view_layer.objects.active = windshield

        original_active_object = context.active_object
        original_frame = scene.frame_current
        original_engine = scene.render.engine
        original_bake = (
            scene.render.bake.margin,
            scene.render.bake.use_clear,
            scene.render.bake.use_selected_to_active,
        )
        # Cycles bakes into the active *and* selected image node of each material
        original_node_states = [
            (node, node.select, node.id_data.nodes.active) for node in bake_nodes
        ]
        paths = []
        try:
            # Baking is a Cycles only feature
            scene.render.engine = "CYCLES"
            scene.render.bake.margin = 0
            scene.render.bake.use_clear = True
            scene.render.bake.use_selected_to_active = True
            for node in bake_nodes:
                node.select = True
                node.id_data.nodes.active = node
            bake_temp_folder.mkdir(parents=True, exist_ok=True)

            for slot, wiper in enumerate(wipers, start=1):
                if not self.debug_slots[slot - 1]:
                    continue
                select_objects(wiper)

                print(
                    "Animated baking for frames (%d - %d)"
                    % (self.start, self.start + 255)
                )

                for cfra in range(self.start, self.start + 255):
                    assert 1 <= cfra <= 255 * 4, f"Start is {self.start}, cfra is {cfra}"
                    bake_start = time.perf_counter()
                    print("Baking frame %d" % cfra)

                    # update scene to new frame and bake to template image
                    scene.frame_set(cfra)
                    new_img_filepath = bake_temp_folder / Path(
                        f"{img_filepath.stem}_slot{slot}_{cfra:03}.png"
                    )

                    if not self.debug_reuse_temps or (
                        self.debug_reuse_temps and not new_img_filepath.exists()
                    ):
                        ret = bpy.ops.object.bake(type=scene.cycles.bake_type)
                    else:
                        ret = {}

                    if "CANCELLED" in ret:
                        return {"CANCELLED"}
                    print("Bake time:", time.perf_counter() - bake_start)

                    # Currently the api has no img.save_as()
                    orig = img.filepath_raw
                    # !!! IMPORTANT! You must use filepath_raw! !!!
                    img.filepath_raw = str(new_img_filepath)
                    paths.append(Path(img.filepath_raw))
                    if not self.debug_reuse_temps:
                        img.save()
                        print("Saved %r" % new_img_filepath)
                    img.filepath_raw = orig
                print("Baking done!")

            try:
                if self.debug_master_filepath:
                    master_filepath = Path(
                        bpy.path.abspath(self.debug_master_filepath)
                    )
                else:
                    master_filepath = img_filepath.parent / Path(
                        "wiper_gradient_texture.png"
                    )
                xplane_wiper_gradient.make_wiper_images(
                    paths, *img.size, master_filepath
                )
            except OSError as e:
                bpy.ops.xplane.msg("INVOKE_DEFAULT", msg_text=str(e))
                return {"CANCELLED"}
            else:
                rain.wiper_texture = bpy.path.relpath(str(master_filepath)).replace(
                    "\\", "/"
                )
                if not self.debug_reuse_temps:
                    shutil.rmtree(bake_temp_folder, ignore_errors=True)
        finally:
            for node, select, active in original_node_states:
                node.select = select
                node.id_data.nodes.active = active
            for obj in context.selected_objects:
                obj.select_set(False)
            context.view_layer.objects.active = original_active_object
            scene.frame_set(original_frame)
            scene.render.engine = original_engine
            (
                scene.render.bake.margin,
                scene.render.bake.use_clear,
                scene.render.bake.use_selected_to_active,
            ) = original_bake
        return {"FINISHED"}

    @classmethod
    def poll(cls, context):
        active_root = _get_active_root(context)
        return active_root and active_root.xplane.layer.export_type in {
            EXPORT_TYPE_AIRCRAFT,
            EXPORT_TYPE_COCKPIT,
        }


def _get_active_root(
    context: bpy.types.Context,
) -> Optional[Union[bpy.types.Collection, bpy.types.Object]]:
    """The active object or collection, if it is an exportable root"""
    if context.active_object and context.active_object.xplane.isExportableRoot:
        return context.active_object
    elif context.collection and context.collection.xplane.is_exportable_collection:
        return context.collection
    return None


class XPLANE_OT_ExportSceneReport(bpy.types.Operator):
    """Export a CSV report of all datarefs and manipulators used in the scene"""

    bl_idname = "xplane.export_scene_report"
    bl_label = "Export Scene Report (CSV)"

    directory: bpy.props.StringProperty(
        name="Output Directory",
        description="Directory where the CSV report files will be written",
        subtype="DIR_PATH",
    )

    def invoke(self, context, event):
        # Pre-fill with the directory of the open .blend file, falling back
        # to the system temp folder when the file hasn't been saved yet.
        if bpy.data.filepath:
            import os
            self.directory = os.path.dirname(bpy.data.filepath)
        wm = context.window_manager
        wm.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        import os

        scene = context.scene
        blend_name = (
            os.path.splitext(os.path.basename(bpy.data.filepath))[0]
            if bpy.data.filepath
            else "scene"
        )
        out_dir = bpy.path.abspath(self.directory)

        view_layer = context.view_layer

        # --- Datarefs ---
        dr_rows = xplane_scene_report.collect_datarefs(scene, view_layer)
        dr_csv = xplane_scene_report.write_csv(
            dr_rows, xplane_scene_report.DATAREF_FIELDS
        )
        dr_path = os.path.join(out_dir, f"{blend_name}_datarefs.csv")
        with open(dr_path, "w", encoding="utf-8") as f:
            f.write(dr_csv)

        # --- Manipulators ---
        manip_rows = xplane_scene_report.collect_manipulators(scene, view_layer)
        manip_csv = xplane_scene_report.write_csv(
            manip_rows, xplane_scene_report.MANIPULATOR_FIELDS
        )
        manip_path = os.path.join(out_dir, f"{blend_name}_manipulators.csv")
        with open(manip_path, "w", encoding="utf-8") as f:
            f.write(manip_csv)

        self.report(
            {"INFO"},
            f"Wrote {len(dr_rows)} dataref(s) to {dr_path} "
            f"and {len(manip_rows)} manipulator(s) to {manip_path}",
        )
        return {"FINISHED"}


_ops = (
    COLLECTION_OT_add_xplane_export_path_directive,
    COLLECTION_OT_remove_xplane_export_path_directive,
    COLLECTION_OT_add_xplane_layer_attribute,
    COLLECTION_OT_remove_xplane_layer_attribute,
    OBJECT_OT_add_xplane_axis_detent_range,
    OBJECT_OT_remove_xplane_axis_detent_range,
    OBJECT_OT_add_xplane_layer_attribute,
    OBJECT_OT_remove_xplane_layer_attribute,
    OBJECT_OT_add_xplane_object_attribute,
    OBJECT_OT_remove_xplane_object_attribute,
    OBJECT_OT_add_xplane_object_anim_attribute,
    OBJECT_OT_remove_xplane_object_anim_attribute,
    OBJECT_OT_add_xplane_material_attribute,
    OBJECT_OT_remove_xplane_material_attribute,
    OBJECT_OT_add_xplane_light_attribute,
    OBJECT_OT_remove_xplane_light_attribute,
    OBJECT_OT_add_xplane_dataref,
    OBJECT_OT_remove_xplane_dataref,
    OBJECT_OT_add_xplane_dataref_keyframe,
    OBJECT_OT_remove_xplane_dataref_keyframe,
    OBJECT_OT_add_xplane_export_path_directive,
    OBJECT_OT_remove_xplane_export_path_directive,
    BONE_OT_add_xplane_dataref,
    BONE_OT_remove_xplane_dataref,
    BONE_OT_add_xplane_dataref_keyframe,
    BONE_OT_remove_xplane_dataref_keyframe,
    OBJECT_OT_add_xplane_object_condition,
    OBJECT_OT_remove_xplane_object_condition,
    OBJECT_OT_add_xplane_material_condition,
    OBJECT_OT_remove_xplane_material_condition,
    SCENE_OT_export_to_relative_dir,
    XPLANE_OT_CommandSearchToggle,
    XPLANE_OT_DatarefSearchToggle,
    XPLANE_OT_XPlaneMessage,
    XPLANE_OT_bake_wiper_gradient_texture,
    XPLANE_OT_ExportSceneReport,
)

register, unregister = bpy.utils.register_classes_factory(_ops)
