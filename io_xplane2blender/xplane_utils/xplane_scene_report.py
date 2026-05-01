"""
Utilities for generating scene reports as CSV data.

Collects animation datarefs and manipulator/command information from all
objects and bones in a Blender scene and serializes them to CSV strings.
"""

import csv
import io
from typing import Dict, List, Optional, Tuple

import bpy

# --- Field name constants ---

DATAREF_FIELDS = [
    "Object Name",
    "Object Type",
    "Dataref Path",
    "Animation Type",
    "Value 1",
    "Value 2",
    "Loop",
]

MANIPULATOR_FIELDS = [
    "Object Name",
    "Manipulator Type",
    "Tooltip",
    "Cursor",
    "Dataref 1",
    "Dataref 1 Min",
    "Dataref 1 Max",
    "Dataref 2",
    "Dataref 2 Min",
    "Dataref 2 Max",
    "Command",
    "Positive Command",
    "Negative Command",
]


def collect_datarefs(
    scene: bpy.types.Scene, view_layer: bpy.types.ViewLayer
) -> List[Dict]:
    """
    Walk all visible objects and bones in the scene, returning one dict per
    animation dataref. Transform datarefs report their keyframe value range;
    show/hide datarefs report their threshold values.
    """
    rows = []

    for obj in scene.objects:
        if not obj.visible_get(view_layer=view_layer):
            continue
        # Datarefs on the object itself
        for i, dr in enumerate(obj.xplane.datarefs):
            if not dr.path:
                continue
            v1, v2 = _get_transform_range(obj.animation_data, i, dr)
            rows.append({
                "Object Name": obj.name,
                "Object Type": "OBJECT",
                "Dataref Path": dr.path,
                "Animation Type": dr.anim_type,
                "Value 1": v1,
                "Value 2": v2,
                "Loop": dr.loop if dr.loop != 0.0 else "",
            })

        # Datarefs on bones inside armature objects
        if obj.type == "ARMATURE" and obj.data:
            for bone in obj.data.bones:
                for i, dr in enumerate(bone.xplane.datarefs):
                    if not dr.path:
                        continue
                    # Bone keyframes live on the armature's animation_data,
                    # with a data path that includes the bone name.
                    v1, v2 = _get_transform_range(
                        obj.data.animation_data, i, dr, bone_name=bone.name
                    )
                    rows.append({
                        "Object Name": f"{obj.name} / {bone.name}",
                        "Object Type": "BONE",
                        "Dataref Path": dr.path,
                        "Animation Type": dr.anim_type,
                        "Value 1": v1,
                        "Value 2": v2,
                        "Loop": dr.loop if dr.loop != 0.0 else "",
                    })

    return rows


def _get_transform_range(
    anim_data: Optional[bpy.types.AnimData],
    index: int,
    dr,
    bone_name: Optional[str] = None,
) -> Tuple:
    """
    Return (value_1, value_2) for a dataref.

    For show/hide types these are the stored threshold values.
    For transform types these are the min/max keyframe values on the
    dataref's value FCurve, or empty strings if no keyframes exist.
    """
    if dr.anim_type in ("show", "hide"):
        return dr.show_hide_v1, dr.show_hide_v2

    # Build the FCurve data path used when keyframing this dataref's value
    if bone_name:
        data_path = f'bones["{bone_name}"].xplane.datarefs[{index}].value'
    else:
        data_path = f"xplane.datarefs[{index}].value"

    if anim_data and anim_data.action:
        for fcurve in anim_data.action.fcurves:
            if fcurve.data_path == data_path:
                values = [kp.co[1] for kp in fcurve.keyframe_points]
                if values:
                    return min(values), max(values)

    return "", ""


def collect_manipulators(
    scene: bpy.types.Scene, view_layer: bpy.types.ViewLayer
) -> List[Dict]:
    """
    Walk all visible objects in the scene, returning one dict per enabled
    manipulator. Each row includes whatever datarefs or commands the
    manipulator references.
    """
    rows = []

    for obj in scene.objects:
        if not obj.visible_get(view_layer=view_layer):
            continue
        manip = obj.xplane.manip
        if not manip.enabled:
            continue

        rows.append({
            "Object Name": obj.name,
            "Manipulator Type": manip.type,
            "Tooltip": manip.tooltip,
            "Cursor": manip.cursor,
            "Dataref 1": manip.dataref1,
            "Dataref 1 Min": manip.v1_min if manip.dataref1 else "",
            "Dataref 1 Max": manip.v1_max if manip.dataref1 else "",
            "Dataref 2": manip.dataref2,
            "Dataref 2 Min": manip.v2_min if manip.dataref2 else "",
            "Dataref 2 Max": manip.v2_max if manip.dataref2 else "",
            "Command": manip.command,
            "Positive Command": manip.positive_command,
            "Negative Command": manip.negative_command,
        })

    return rows


def write_csv(rows: List[Dict], fieldnames: List[str]) -> str:
    """Serialize a list of row dicts to a CSV string."""
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
