"""
The Blender side of the visual parity check (see README.md). Runs inside Blender with the
XPlane2Blender add-on loaded, as parity.py invokes it:

    blender -b --factory-startup --addons io_xplane2blender --python parity_blender.py -- COMMAND ...

    sample BLEND
        Makes the sample scene: coloured boxes, an animated flap, a part hidden by a dataref,
        a light.
    export BLEND ROOT WORK --mode M [--views VIEWS.json] [--dataref NAME=VALUE ...]
        Exports ROOT to WORK/model.obj with the mode's textures, writes palette.png, booth.obj,
        VIEWS and DATAREFS for the plugin, and views_resolved.json.
    render BLEND ROOT WORK --mode M --size WxH
        Renders WORK/blender_<view>.png for each resolved view, posed by the datarefs.
    compare WORK --mode M
        Compares blender_<view>.png with xplane_<view>.png; writes report.txt, diff_<view>.png
        and comparison.png. Exit code 1 on failure.

Modes:
    palette   every material becomes a flat palette colour (one per material): shapes,
              positions, animation, show/hide and winding, compared exactly
    textured  the model's own albedo texture, also as the lit texture: UV mapping and
              texture assignment, compared loosely (X-Plane's tone mapping shifts colours)
    lights    only the lights, as X-Plane draws them, against spheres Blender renders at the
              lights' positions: position and colour of each light
"""
import argparse
import json
import math
import os
import shutil
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_booth  # noqa: E402

from io_xplane2blender.xplane_helpers import get_action_fcurves, logger, vec_b_to_x  # noqa: E402
from io_xplane2blender.xplane_types import xplane_file  # noqa: E402

BACKGROUND = make_booth.BACKGROUND
MODEL_COLOURS = [name for name, _ in make_booth.PALETTE if name != BACKGROUND]
PALETTE_NAMES = [name for name, _ in make_booth.PALETTE]
PALETTE_RGB = dict(make_booth.PALETTE)
DARK = 0.08  # below this brightness a pixel is background


# --- Scene helpers ------------------------------------------------------------------------
def open_blend(path):
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(path))


def find_root(name):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    if name in bpy.data.objects:
        return bpy.data.objects[name]
    raise SystemExit(f"ERROR: no object or collection named {name!r}")


def root_matrix(root):
    if isinstance(root, bpy.types.Object):
        return root.matrix_world.copy()
    from mathutils import Matrix
    return Matrix.Identity(4)


def objects_under(root):
    if isinstance(root, bpy.types.Object):
        def walk(o):
            for c in o.children:
                yield c
                yield from walk(c)
        return list(walk(root))
    return list(root.all_objects)


def mesh_objects(root):
    return [o for o in objects_under(root) if o.type == "MESH" and o.visible_get()]


def light_objects(root):
    return [o for o in objects_under(root) if o.type == "LIGHT" and o.visible_get()
            and o.data.xplane.type != "nonexporting"]


def palette_material(name, colour, image):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    principled = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    mat.node_tree.links.new(tex.outputs["Color"], principled.inputs["Base Color"])
    nodes.active = tex  # Workbench's texture colour mode draws the active image node
    mat.diffuse_color = (*(c / 255 for c in PALETTE_RGB[colour]), 1.0)
    return mat


def convert_to_palette(root, palette_png):
    """
    Replaces every material under the root with a flat palette material, one colour per
    original material name (repeating when there are more materials than colours), and
    puts every UV in that colour's cell. Only in memory: the file isn't saved
    """
    image = bpy.data.images.load(palette_png, check_existing=True)
    originals = sorted({slot.material.name if slot.material else "" for o in mesh_objects(root) for slot in o.material_slots} | {""})
    colour_of = {name: MODEL_COLOURS[i % len(MODEL_COLOURS)] for i, name in enumerate(originals)}
    materials = {}
    for obj in mesh_objects(root):
        mesh = obj.data
        if not obj.material_slots:
            mesh.materials.append(None)
        colours = []
        for slot in obj.material_slots:
            colour = colour_of[slot.material.name if slot.material else ""]
            if colour not in materials:
                materials[colour] = palette_material(f"parity_{colour}", colour, image)
            slot.material = materials[colour]
            colours.append(colour)
        uv = mesh.uv_layers.active or mesh.uv_layers.new()
        for poly in mesh.polygons:
            u, v = make_booth.cell_uv(colours[min(poly.material_index, len(colours) - 1)])
            for loop_index in poly.loop_indices:
                uv.data[loop_index].uv = (u, v)
    return colour_of


def model_bounds_obj_frame(root, objects):
    """Min and max of every object's corners, in OBJ coordinates relative to the root"""
    inverse = root_matrix(root).inverted()
    points = []
    for obj in objects:
        corners = obj.bound_box if obj.type == "MESH" else [(0, 0, 0)]
        for corner in corners:
            points.append(vec_b_to_x(inverse @ (obj.matrix_world @ Vector(corner))))
    if not points:
        raise SystemExit("ERROR: nothing under the root to look at")
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


def resolve_views(views_spec, lo, hi):
    """Camera and target offsets (OBJ frame) for each orbit view, framed to the bounds"""
    fov = views_spec.get("fov_deg", 60)
    fill = views_spec.get("fill", 0.6)
    centre = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 0.5)
    fov_h = math.radians(fov) if views_spec.get("fov_axis", "horizontal") == "horizontal" else None
    fov_v = 2 * math.atan(math.tan(fov_h / 2) * 9 / 16) if fov_h else math.radians(fov)
    distance = radius / math.tan(fov_v / 2) / fill
    limit = make_booth.BOOTH_HALF - 2
    if distance > limit:
        print(f"WARNING: model radius {radius:.1f} m needs {distance:.1f} m of camera distance, clamped to {limit} m inside the booth")
        distance = limit
    resolved = []
    for view in views_spec["views"]:
        az, el = math.radians(view["azimuth"]), math.radians(view["elevation"])
        # OBJ frame: X east, Y up, Z south; azimuth 0 looks at the model's front (-Z side)
        direction = Vector((math.sin(az) * math.cos(el), math.sin(el), -math.cos(az) * math.cos(el)))
        camera = centre + direction * distance
        camera.y = max(camera.y, make_booth.BOOTH_FLOOR + 0.5)
        resolved.append({"name": view["name"], "camera_obj": list(camera), "target_obj": list(centre)})
    return {"fov_deg": fov, "fov_axis": views_spec.get("fov_axis", "horizontal"), "distance": distance,
            "bounds_obj": [list(lo), list(hi)], "views": resolved, "ignore": views_spec.get("ignore", [])}


# --- Sample scene -------------------------------------------------------------------------
def box(name, size, location, rotation=(0, 0, 0), parent=None, material=None):
    sx, sy, sz = (s / 2 for s in size)
    verts = [(x, y, z) for z in (-sz, sz) for y in (-sy, sy) for x in (-sx, sx)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)  # X-Plane culls back faces
    bm.to_mesh(mesh)
    bm.free()
    mesh.uv_layers.new()
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = [math.radians(r) for r in rotation]
    obj.parent = parent
    return obj


def sample_root(out_dir, material_names):
    """An empty scene with a palette, an exportable root and plain materials"""
    from io_xplane2blender.tests import test_creation_helpers as tch

    os.makedirs(out_dir, exist_ok=True)
    tch.delete_everything()
    make_booth.write_palette(os.path.join(out_dir, "palette.png"))
    materials = {name: bpy.data.materials.new(name) for name in material_names}
    for mat in materials.values():
        mat.use_nodes = True
    root = bpy.data.objects.new("parity_sample", None)
    bpy.context.scene.collection.objects.link(root)
    root.xplane.isExportableRoot = True
    root.xplane.layer.name = "model"
    root.xplane.layer.export_type = "scenery"
    root.xplane.layer.texture = "//palette.png"
    return root, materials


def save_sample(blend):
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(blend))
    print("SAMPLE", blend)


def sample_static(blend):
    """
    #253: objects with two datarefs where the second one's keyframe table doesn't move
    them, which the exporter writes as a static ANIM_trans / ANIM_rotate
    """
    from io_xplane2blender.tests import test_creation_helpers as tch

    root, materials = sample_root(os.path.dirname(os.path.abspath(blend)), ("base", "slider", "spinner"))
    box("base", (6, 4, 0.2), (0, 0, 0.1), parent=root, material=materials["base"])
    mover, other = "sim/graphics/animation/sin_wave_2", "sim/cockpit2/engine/actuators/throttle_ratio_all"
    # The slider moves from x=2 to x=1 with the mover; the other dataref's keys both see x=2
    slider = box("slider", (1, 1, 1), (2, 0, 0.7), parent=root, material=materials["slider"])
    tch.set_animation_data(slider, [
        tch.KeyframeInfo(idx=1, dataref_path=mover, dataref_value=0.0, location=(2, 0, 0.7)),
        tch.KeyframeInfo(idx=11, dataref_path=mover, dataref_value=1.0, location=(1, 0, 0.7)),
    ])
    tch.set_animation_data(slider, [
        tch.KeyframeInfo(idx=1, dataref_path=other, dataref_value=0.0, location=(2, 0, 0.7)),
        tch.KeyframeInfo(idx=21, dataref_path=other, dataref_value=1.0, location=(2, 0, 0.7)),
    ])
    # The spinner turns 0 to 45 degrees about Z with the mover; the other dataref's keys both see 45
    spinner = box("spinner", (2, 0.4, 0.6), (-1.5, 1, 0.5), parent=root, material=materials["spinner"])
    tch.set_animation_data(spinner, [
        tch.KeyframeInfo(idx=1, dataref_path=mover, dataref_value=0.0, rotation=(0, 0, 0)),
        tch.KeyframeInfo(idx=11, dataref_path=mover, dataref_value=1.0, rotation=(0, 0, 45)),
    ])
    tch.set_animation_data(spinner, [
        tch.KeyframeInfo(idx=11, dataref_path=other, dataref_value=0.0, rotation=(0, 0, 45)),
        tch.KeyframeInfo(idx=21, dataref_path=other, dataref_value=1.0, rotation=(0, 0, 45)),
    ])
    save_sample(blend)


def sample_conditions(blend):
    """
    #284: an IF / ELSE IF / ELSE chain on SCENERY_SHADOWS, an ELSE that's always taken, and
    Laminar's IF NOT SCENERY_SHADOWS. With scenery shadows on, a_if and e_else show; off,
    c_elseif, e_else and f_ifnot show
    """
    root, materials = sample_root(os.path.dirname(os.path.abspath(blend)),
                                  ("a_if", "b_else", "c_elseif", "d_never", "e_else", "f_ifnot"))
    objects = {}
    for name, location in (("a_if", (-3, 0, 0.5)), ("b_else", (-1, 0, 0.5)), ("c_elseif", (1, 0, 0.5)),
                           ("d_never", (-2, 2.5, 0.5)), ("e_else", (0, 2.5, 0.5)), ("f_ifnot", (2, 2.5, 0.5))):
        objects[name] = box(name, (1.2, 1.2, 1), location, parent=root, material=materials[name])

    def condition(obj, variable, value):
        c = obj.xplane.conditions.add()
        c.variable = variable
        c.value = value

    condition(objects["a_if"], "SCENERY_SHADOWS", True)
    objects["b_else"].xplane.else_of = objects["a_if"]
    objects["c_elseif"].xplane.else_of = objects["a_if"]
    condition(objects["c_elseif"], "VERSION10", True)
    condition(objects["d_never"], "VERSION10", False)
    objects["e_else"].xplane.else_of = objects["d_never"]
    condition(objects["f_ifnot"], "SCENERY_SHADOWS", False)
    save_sample(blend)


def cmd_sample(args):
    {"basic": sample_basic, "static": sample_static, "conditions": sample_conditions}[args.kind](args.blend)


def sample_basic(blend):
    """A designer-style scene: ordinary materials, a texture, a flap, a hidden part, a light"""
    from io_xplane2blender.tests import test_creation_helpers as tch

    root, materials = sample_root(os.path.dirname(os.path.abspath(blend)),
                                  ("body", "post", "wedge", "bar", "cover", "flag", "flap"))

    box("cube", (2, 2, 2), (0, 0, 1), parent=root, material=materials["body"])
    box("post", (0.6, 0.6, 4), (3, 0, 2), parent=root, material=materials["post"])
    box("wedge", (2, 1, 0.5), (-3, 1, 0.25), rotation=(0, 0, 30), parent=root, material=materials["wedge"])
    box("bar", (6, 0.3, 0.3), (0, -1.5, 3.5), parent=root, material=materials["bar"])
    box("cover", (1, 1, 1), (0, 2.5, 0.5), parent=root, material=materials["cover"])
    box("flag", (0.2, 1.5, 1), (-1.5, 2.5, 3), parent=root, material=materials["flag"])

    # The flap hinges 0..60 degrees about X with sim/cockpit2/controls/flap_ratio 0..1,
    # keyed at frames 1 and 11, so frame = 1 + 10 * value
    flap = box("flap", (2, 0.2, 1), (0, -2.5, 1.5), parent=root, material=materials["flap"])
    dataref = "sim/cockpit2/controls/flap_ratio"
    tch.set_animation_data(flap, [
        tch.KeyframeInfo(idx=1, dataref_path=dataref, dataref_value=0.0, rotation=(0, 0, 0)),
        tch.KeyframeInfo(idx=11, dataref_path=dataref, dataref_value=1.0, rotation=(60, 0, 0)),
    ])
    hide = bpy.data.objects["cover"].xplane.datarefs.add()
    hide.path = dataref
    hide.anim_type = "hide"
    hide.show_hide_v1, hide.show_hide_v2 = 0.5, 1.0

    # A named light on the post: taxi_r, red, omnidirectional and steady. airplane_beacon
    # flashes, so a screenshot could catch it dark or flaring
    light = tch.create_datablock_light(tch.DatablockInfo("LIGHT", "beacon", parent_info=tch.ParentInfo(root)), "POINT")
    light.location = (3, 0, 4.5)
    light.data.xplane.type = "named"
    light.data.xplane.name = "taxi_r"
    light.data.color = (1.0, 0.0, 0.0)
    save_sample(blend)


# --- Export ---------------------------------------------------------------------------------
def prepare_scene(root, mode, work):
    """Changes the in-memory scene for the mode; returns (objects to frame, albedo path or None)"""
    layer = root.xplane.layer
    albedo = None
    palette = os.path.join(work, "palette.png")
    if mode != "lights":
        # Lights have their own check; here their billboards would only be stray bright pixels
        for obj in light_objects(root):
            bpy.data.objects.remove(obj)
    if mode == "palette":
        convert_to_palette(root, palette)
        layer.texture, layer.texture_lit = palette, palette
    elif mode == "textured":
        source = bpy.path.abspath(layer.texture) if layer.texture else ""
        if not os.path.isfile(source):
            raise SystemExit(f"ERROR: textured mode needs the root's Default texture on disk, got {layer.texture!r}")
        albedo = os.path.join(work, "albedo" + os.path.splitext(source)[1].lower())
        shutil.copy(source, albedo)
        # The albedo as the lit texture too: its colours show at night without lighting
        layer.texture_lit = layer.texture
    elif mode == "lights":
        for obj in mesh_objects(root):
            bpy.data.objects.remove(obj)
        layer.texture, layer.texture_lit = palette, palette
    framed = mesh_objects(root) if mode != "lights" else light_objects(root)
    if mode == "lights" and not framed:
        raise SystemExit("ERROR: lights mode needs at least one exporting light under the root")
    return framed, albedo


def cmd_export(args):
    open_blend(args.blend)
    root = find_root(args.root)
    work = os.path.abspath(args.work)
    os.makedirs(work, exist_ok=True)
    make_booth.write_palette(os.path.join(work, "palette.png"))
    make_booth.write_booth(os.path.join(work, "booth.obj"))
    framed, albedo = prepare_scene(root, args.mode, work)
    bpy.context.scene.frame_set(1)
    xp = xplane_file.createFileFromBlenderRootObject(root, bpy.context.scene.view_layers[0])
    xp.export_dir = work
    text = xp.write()
    xplane_file._all_keyframe_infos.clear()
    errors = [e["message"] for e in logger.findErrors()]
    if errors:
        raise SystemExit("ERROR: export failed:\n" + "\n".join(errors))
    # The plugin loads textures next to the OBJ
    lines = []
    for line in text.splitlines():
        if line.startswith("TEXTURE"):
            parts = line.split("\t")
            parts[-1] = os.path.basename(albedo) if albedo and line.startswith(("TEXTURE\t", "TEXTURE_LIT\t")) else "palette.png"
            line = "\t".join(parts)
        lines.append(line)
    with open(os.path.join(work, "model.obj"), "w", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    with open(args.views, encoding="utf-8") as f:
        views_spec = json.load(f)
    lo, hi = model_bounds_obj_frame(root, framed)
    resolved = resolve_views(views_spec, lo, hi)
    datarefs = {}
    for item in args.dataref or []:
        name, _, value = item.partition("=")
        datarefs[name] = float(value)
    resolved["datarefs"] = datarefs
    resolved["mode"] = args.mode
    resolved["lights"] = [o.name for o in light_objects(root)]
    with open(os.path.join(work, "views_resolved.json"), "w", encoding="utf-8") as f:
        json.dump(resolved, f, indent=2)
    with open(os.path.join(work, "VIEWS"), "w", newline="\n") as f:
        f.write(f"FOV {resolved['fov_deg']}\n")
        for view in resolved["views"]:
            f.write(" ".join(f"{c:.4f}" for c in view["camera_obj"] + view["target_obj"]) + "\n")
    with open(os.path.join(work, "DATAREFS"), "w", newline="\n") as f:
        for name, value in datarefs.items():
            f.write(f"{name} {value:g}\n")
    print(f"EXPORTED {len(lines)} lines in {args.mode} mode, bounds {[round(c, 2) for c in lo]} to {[round(c, 2) for c in hi]},"
          f" camera distance {resolved['distance']:.1f} m, {len(resolved['views'])} views")


# --- Render -----------------------------------------------------------------------------------
def frame_for_dataref_values(root, values):
    """
    The frame that poses every animated object at the given dataref values. Each
    dataref's keyframes map value to frame linearly; every object must agree
    """
    frames = []
    candidates = objects_under(root) + [o for o in bpy.data.objects if o.type == "ARMATURE"]
    for obj in candidates:
        for index, dataref in enumerate(obj.xplane.datarefs):
            if dataref.path not in values or dataref.anim_type != "transform":
                continue
            fcurve = next((f for f in get_action_fcurves(obj.animation_data)
                           if f.data_path == f"xplane.datarefs[{index}].value"), None)
            if fcurve is None or len(fcurve.keyframe_points) < 2:
                continue
            keys = sorted((k.co[0], k.co[1]) for k in fcurve.keyframe_points)
            value = values[dataref.path]
            frame = None
            for (f0, v0), (f1, v1) in zip(keys, keys[1:]):
                if min(v0, v1) <= value <= max(v0, v1) and v1 != v0:
                    frame = f0 + (value - v0) / (v1 - v0) * (f1 - f0)
                    break
            if frame is None:
                frame = keys[0][0] if value < keys[0][1] else keys[-1][0]
            frames.append((obj.name, dataref.path, frame))
    if not frames:
        return None
    chosen = frames[0][2]
    for name, path, frame in frames[1:]:
        if abs(frame - chosen) > 0.5:
            print(f"WARNING: {name}'s {path} wants frame {frame:.1f}, using {chosen:.1f}; key every animated object's datarefs at the same frames")
    return chosen


def apply_show_hide(root, values):
    """X-Plane's rule: start visible, then each Show/Hide in order applies when the value is in its range"""
    for obj in objects_under(root):
        visible = True
        for dataref in obj.xplane.datarefs:
            if dataref.anim_type not in ("show", "hide") or dataref.path not in values:
                continue
            v1, v2 = sorted((dataref.show_hide_v1, dataref.show_hide_v2))
            if v1 <= values[dataref.path] <= v2:
                visible = dataref.anim_type == "show"
        if not visible:
            obj.hide_render = True
            for child in obj.children_recursive:
                child.hide_render = True


def apply_albedo(root, albedo_path):
    """
    X-Plane draws the whole OBJ with the root's one texture, so Blender shows that texture on
    every material too: the check is then about the UVs, which is what the exporter controls
    """
    image = bpy.data.images.load(albedo_path, check_existing=True)
    done = set()
    for obj in mesh_objects(root):
        if not obj.material_slots:
            obj.data.materials.append(None)
        for slot in obj.material_slots:
            if slot.material is None:
                slot.material = bpy.data.materials.new("parity_albedo")
            mat = slot.material
            if mat.name in done:
                continue
            done.add(mat.name)
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            tex = next((n for n in nodes if n.type == "TEX_IMAGE" and n.image == image), None)
            if tex is None:
                tex = nodes.new("ShaderNodeTexImage")
                tex.image = image
            nodes.active = tex
            principled = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
            if principled:
                mat.node_tree.links.new(tex.outputs["Color"], principled.inputs["Base Color"])
        if not obj.data.uv_layers:
            obj.data.uv_layers.new()


def condition_holds(obj, states):
    """True when all the object's conditions (its own and its materials') hold in states"""
    conditions = list(obj.xplane.conditions)
    for slot in obj.material_slots:
        if slot.material:
            conditions += list(slot.material.xplane.conditions)
    for condition in conditions:
        if condition.variable not in states:
            raise SystemExit(f"ERROR: {obj.name} has the condition {condition.variable};"
                             f" give its state with --condition {condition.variable}=0 or 1")
        if states[condition.variable] != condition.value:
            return False
    return True


def apply_conditions(root, states):
    """
    Hides what X-Plane skips: objects whose IF is false, and in each ELSE IF / ELSE chain
    every branch but the first that holds (ELSE IF branches first, then the ELSE, as exported)
    """
    objects = mesh_objects(root)

    def hide(obj):
        obj.hide_render = True
        for child in obj.children_recursive:
            child.hide_render = True

    for obj in objects:
        if obj.xplane.else_of is not None:
            continue
        taken = condition_holds(obj, states)
        if not taken:
            hide(obj)
        alternatives = sorted((o for o in objects if o.xplane.else_of == obj),
                              key=lambda o: (not o.xplane.conditions, o.name))
        for alternative in alternatives:
            if not taken and condition_holds(alternative, states):
                taken = True
            else:
                hide(alternative)


def light_spheres(root):
    """A small sphere in the light's colour where each exporting light is, meshes hidden"""
    for obj in mesh_objects(root):
        obj.hide_render = True
    for light in light_objects(root):
        mesh = bpy.data.meshes.new("parity_light")
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.3)
        bm.to_mesh(mesh)
        bm.free()
        mat = bpy.data.materials.new("parity_light")
        colour = light.data.color
        mat.diffuse_color = (colour[0], colour[1], colour[2], 1.0)
        mesh.materials.append(mat)
        sphere = bpy.data.objects.new("parity_light_" + light.name, mesh)
        bpy.context.scene.collection.objects.link(sphere)
        sphere.matrix_world = light.matrix_world.copy()
        sphere.scale = (1, 1, 1)


def cmd_render(args):
    open_blend(args.blend)
    root = find_root(args.root)
    work = os.path.abspath(args.work)
    with open(os.path.join(work, "views_resolved.json"), encoding="utf-8") as f:
        resolved = json.load(f)
    width, height = (int(n) for n in args.size.lower().split("x"))
    scene = bpy.context.scene

    frame = frame_for_dataref_values(root, resolved["datarefs"])
    if frame is None:
        scene.frame_set(1)
    else:
        scene.frame_set(int(frame), subframe=frame - int(frame))
    apply_show_hide(root, resolved["datarefs"])
    states = {}
    for item in args.condition or []:
        name, _, value = item.partition("=")
        states[name] = value.strip() not in ("0", "false", "False", "")
    apply_conditions(root, states)
    if args.mode == "palette":
        convert_to_palette(root, os.path.join(work, "palette.png"))
    elif args.mode == "textured":
        albedo = next((p for p in os.listdir(work) if p.startswith("albedo.")), None)
        if albedo is None:
            raise SystemExit("ERROR: no albedo texture in the work folder; export in textured mode first")
        apply_albedo(root, os.path.join(work, albedo))
    elif args.mode == "lights":
        light_spheres(root)

    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "FLAT"
    shading.color_type = "TEXTURE"
    shading.background_type = "WORLD"
    shading.show_object_outline = False
    shading.show_cavity = False
    shading.show_shadows = False
    shading.show_specular_highlight = False
    scene.display.render_aa = "8"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new("parity")
    scene.world.use_nodes = False
    scene.world.color = tuple(c / 255 for c in PALETTE_RGB[BACKGROUND])
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    cam_data = bpy.data.cameras.new("parity_camera")
    cam_data.type = "PERSP"
    cam_data.clip_end = 1000
    if resolved["fov_axis"] == "horizontal":
        cam_data.sensor_fit = "HORIZONTAL"
        cam_data.angle_x = math.radians(resolved["fov_deg"])
    else:
        cam_data.sensor_fit = "VERTICAL"
        cam_data.angle_y = math.radians(resolved["fov_deg"])
    camera = bpy.data.objects.new("parity_camera", cam_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    matrix = root_matrix(root)

    def to_world(obj_frame):
        x, y, z = obj_frame
        return matrix @ Vector((x, -z, y))  # OBJ (X, Y up, Z south) to Blender (X, Y north, Z up)

    for view in resolved["views"]:
        position, target = to_world(view["camera_obj"]), to_world(view["target_obj"])
        camera.location = position
        camera.rotation_euler = (target - position).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(work, f"blender_{view['name']}.png")
        bpy.ops.render.render(write_still=True)
        print("RENDERED", scene.render.filepath)


# --- Compare ------------------------------------------------------------------------------------
def load_rgb(path):
    import numpy as np
    image = bpy.data.images.load(path)
    w, h = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(h, w, image.channels)
    bpy.data.images.remove(image)
    return pixels[:, :, :3]


def normalised(rgb):
    import numpy as np
    brightest = rgb.max(axis=2)
    return rgb / np.maximum(brightest, 1e-6)[:, :, None], brightest


def classify(rgb):
    """
    Palette index per pixel (make_booth.PALETTE order): dark pixels are the background, -1 a
    colour matching nothing. Pixels are normalised by their brightest channel first
    """
    import numpy as np
    norm, brightest = normalised(rgb)
    labels = np.full(brightest.shape, -1, dtype=np.int8)
    best = np.full(brightest.shape, 1e9, dtype=np.float32)
    for index, (name, colour) in enumerate(make_booth.PALETTE):
        if name == BACKGROUND:
            continue
        reference = np.array(colour, dtype=np.float32) / max(colour)
        distance = ((norm - reference) ** 2).sum(axis=2)
        closer = distance < best
        labels[closer] = index
        best[closer] = distance[closer]
    # X-Plane's night rendering shifts hues a little; 0.45 is about half way between colours
    labels[best > 0.45] = -1
    labels[brightest < DARK] = PALETTE_NAMES.index(BACKGROUND)
    return labels


def edge_mask(labels, width=2):
    """True near any label change: anti-aliasing and bloom live there"""
    import numpy as np
    edges = np.zeros(labels.shape, dtype=bool)
    edges[:-1, :] |= labels[:-1, :] != labels[1:, :]
    edges[:, :-1] |= labels[:, :-1] != labels[:, 1:]
    grown = edges.copy()
    for _ in range(width):
        shifted = grown.copy()
        shifted[1:, :] |= grown[:-1, :]
        shifted[:-1, :] |= grown[1:, :]
        shifted[:, 1:] |= grown[:, :-1]
        shifted[:, :-1] |= grown[:, 1:]
        grown = shifted
    return grown


def ignore_mask(shape, regions):
    """True where the comparison looks, after the ignored regions (fractions from the top left)"""
    import numpy as np
    keep = np.ones(shape, dtype=bool)
    h, w = shape
    for x0, y0, x1, y1 in regions:
        keep[int(h - y1 * h): int(h - y0 * h), int(x0 * w): int(x1 * w)] = False  # rows start at the bottom
    return keep


def save_png(path, rgb):
    import numpy as np
    h, w = rgb.shape[:2]
    image = bpy.data.images.new("parity_out", w, h, alpha=False)
    rgba = np.concatenate([rgb, np.ones((h, w, 1), dtype=np.float32)], axis=2)
    image.pixels[:] = rgba.ravel()
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def extent(mask):
    import numpy as np
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def extent_line(mask_a, mask_b):
    ea, eb = extent(mask_a), extent(mask_b)
    if not (ea and eb):
        return "    model extent: missing on one side", None
    wa, ha, wb, hb = ea[2] - ea[0], ea[3] - ea[1], eb[2] - eb[0], eb[3] - eb[1]
    ratios = (wb / max(wa, 1), hb / max(ha, 1))
    return (f"    model extent Blender {wa}x{ha} px at ({(ea[0] + ea[2]) // 2},{(ea[1] + ea[3]) // 2}),"
            f" X-Plane {wb}x{hb} px at ({(eb[0] + eb[2]) // 2},{(eb[1] + eb[3]) // 2}),"
            f" width ratio {ratios[0]:.3f}, height ratio {ratios[1]:.3f}"), ratios


def blobs(bright, min_pixels=20):
    """Connected bright regions: list of (count, cx, cy, x0, y0, x1, y1). Lights are small, so a BFS is fine"""
    import numpy as np
    h, w = bright.shape
    seen = np.zeros_like(bright)
    ys, xs = np.nonzero(bright)
    found = []
    for y, x in zip(ys, xs):
        if seen[y, x]:
            continue
        stack = [(y, x)]
        seen[y, x] = True
        pts = []
        while stack:
            cy, cx = stack.pop()
            pts.append((cy, cx))
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < h and 0 <= nx < w and bright[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(pts) >= min_pixels:
            py, px = zip(*pts)
            found.append((len(pts), sum(px) / len(pts), sum(py) / len(pts), min(px), min(py), max(px), max(py)))
    return sorted(found, key=lambda b: -b[0])


def compare_palette(a, b, keep, args, lines):
    import numpy as np
    la, lb = classify(a), classify(b)
    keep = keep & ~(edge_mask(la) | edge_mask(lb))
    agreement = ((la == lb) & keep).sum() / max(keep.sum(), 1)
    lines.append(f"agreement {agreement * 100:.1f}% of {int(keep.sum())} compared pixels")
    ok = agreement >= args.min_agreement
    total = la.size
    background = PALETTE_NAMES.index(BACKGROUND)
    for index, colour in enumerate(PALETTE_NAMES):
        in_a, in_b = (la == index) & keep, (lb == index) & keep
        if max(in_a.sum(), in_b.sum()) / total < 0.005:
            continue
        iou = (in_a & in_b).sum() / max((in_a | in_b).sum(), 1)
        flag = "" if iou >= args.min_iou or index == background else "  <-- low"
        ok &= not flag
        lines.append(f"    {colour:8s} IoU {iou:.3f}  Blender {in_a.sum() / total * 100:5.2f}%  X-Plane {in_b.sum() / total * 100:5.2f}%{flag}")
    lines.append(f"    pixels matching no colour in X-Plane: {((lb == -1) & keep).sum() / total * 100:.2f}%")
    line, _ = extent_line((la >= 0) & (la != background) & keep, (lb >= 0) & (lb != background) & keep)
    lines.append(line)
    diff = np.zeros(a.shape, dtype=np.float32)
    for index, (name, colour) in enumerate(make_booth.PALETTE):
        diff[lb == index] = (0.15, 0.15, 0.15) if name == BACKGROUND else np.array(colour, dtype=np.float32) / 255 * 0.4
    diff[lb == -1] = (1, 1, 1)
    diff[~keep] = (0, 0, 0)
    diff[(la != lb) & keep] = (1, 0, 0)
    return ok, diff


def compare_textured(a, b, keep, args, lines):
    """How much of the model's area has the same normalised colour; loose, because of X-Plane's tone mapping"""
    import numpy as np
    na, ba = normalised(a)
    nb, bb = normalised(b)
    model_a, model_b = ba >= DARK, bb >= DARK
    model = (model_a | model_b) & keep
    distance = ((na - nb) ** 2).sum(axis=2)
    within = (distance < 0.35) & model_a & model_b
    score = within.sum() / max(model.sum(), 1)
    overlap = (model_a & model_b & keep).sum() / max(model.sum(), 1)
    lines.append(f"texture agreement {score * 100:.1f}% of {int(model.sum())} model pixels, silhouettes overlap {overlap * 100:.1f}%")
    line, ratios = extent_line(model_a & keep, model_b & keep)
    lines.append(line)
    ok = score >= args.min_texture and overlap >= 0.9 and ratios is not None and all(abs(r - 1) < 0.05 for r in ratios)
    diff = b * 0.4
    diff[~keep] = (0, 0, 0)
    diff[model & ~within] = (1, 0, 0)
    return ok, diff


def compare_lights(a, b, keep, args, lines):
    """Each sphere Blender drew must have a bright X-Plane blob close to it, and the same colour"""
    import numpy as np
    na, ba = normalised(a)
    nb, bb = normalised(b)
    blobs_a = blobs((ba > 0.3) & keep)
    total = ba.size
    # A glow bigger than 2% of the picture is either a billboard flaring (a flash caught at
    # its peak has a white core) or a spill light on the floor (no core). A flare's position
    # is its core's; its colour comes from the whole glow
    blobs_b, spill = [], []
    for blob in blobs((bb > 0.3) & keep):
        if blob[0] / total <= 0.02:
            blobs_b.append(blob)
            continue
        x0, y0, x1, y1 = blob[3:7]
        core = np.zeros_like(keep)
        core[y0:y1 + 1, x0:x1 + 1] = (bb[y0:y1 + 1, x0:x1 + 1] > 0.9) & keep[y0:y1 + 1, x0:x1 + 1]
        cores = [c for c in blobs(core) if c[0] / total <= 0.02]
        if cores:
            blobs_b += [(c[0], c[1], c[2], x0, y0, x1, y1) for c in cores]
        else:
            spill.append(blob)
    lines.append(f"lights: Blender {len(blobs_a)}, X-Plane {len(blobs_b)} billboards, {len(spill)} spill glow(s)")
    ok = True
    used = set()
    for count, cx, cy, *_ in blobs_a:
        nearest = min(((math.hypot(bx - cx, by - cy), i) for i, (_, bx, by, *_) in enumerate(blobs_b) if i not in used), default=None)
        if nearest is None or nearest[0] > args.max_light_offset:
            lines.append(f"    light at ({cx:.0f},{cy:.0f}): no X-Plane light within {args.max_light_offset} px  <-- missing")
            ok = False
            continue
        used.add(nearest[1])
        _, bx, by, x0, y0, x1, y1 = blobs_b[nearest[1]]
        colour_a = na[int(cy), int(cx)]
        # The glow, not the white-hot core, carries the light's colour
        brightness = bb[y0:y1 + 1, x0:x1 + 1]
        patch = nb[y0:y1 + 1, x0:x1 + 1][(brightness > 0.3) & (brightness <= 0.9)]
        if not len(patch):
            patch = nb[y0:y1 + 1, x0:x1 + 1][brightness > 0.3]
        colour_b = patch.mean(axis=0) if len(patch) else np.zeros(3)
        hue_distance = float(((colour_a - colour_b) ** 2).sum())
        flag = "" if hue_distance < 0.6 else "  <-- colour differs"
        lines.append(f"    light at ({cx:.0f},{cy:.0f}): X-Plane at ({bx:.0f},{by:.0f}), {nearest[0]:.0f} px away,"
                     f" colour Blender {tuple(round(float(c), 2) for c in colour_a)} X-Plane {tuple(round(float(c), 2) for c in colour_b)}{flag}")
    for i, (_, bx, by, *_) in enumerate(blobs_b):
        if i not in used:
            lines.append(f"    X-Plane light at ({bx:.0f},{by:.0f}) has no Blender light  <-- extra")
            ok = False
    diff = b * 0.6
    diff[~keep] = (0, 0, 0)
    for _, cx, cy, *_ in blobs_a:
        y, x = int(cy), int(cx)
        diff[max(y - 2, 0): y + 3, :] = np.maximum(diff[max(y - 2, 0): y + 3, :], (0.3, 0, 0))
        diff[:, max(x - 2, 0): x + 3] = np.maximum(diff[:, max(x - 2, 0): x + 3], (0.3, 0, 0))
    return ok, diff


def cmd_compare(args):
    import numpy as np
    work = os.path.abspath(args.work)
    with open(os.path.join(work, "views_resolved.json"), encoding="utf-8") as f:
        resolved = json.load(f)
    mode = args.mode or resolved.get("mode", "palette")
    comparer = {"palette": compare_palette, "textured": compare_textured, "lights": compare_lights}[mode]
    report = [f"mode: {mode}"]
    failed = False
    strips = []
    for view in resolved["views"]:
        name = view["name"]
        paths = [os.path.join(work, f"{side}_{name}.png") for side in ("blender", "xplane")]
        if not all(os.path.exists(p) for p in paths):
            report.append(f"{name}: MISSING image(s)")
            failed = True
            continue
        a, b = (load_rgb(p) for p in paths)
        if a.shape != b.shape:
            report.append(f"{name}: sizes differ, Blender {a.shape[1]}x{a.shape[0]} vs X-Plane {b.shape[1]}x{b.shape[0]}")
            failed = True
            continue
        keep = ignore_mask(a.shape[:2], resolved.get("ignore", []))
        lines = []
        ok, diff = comparer(a, b, keep, args, lines)
        lines[0] = f"{name}: {lines[0]}  {'PASS' if ok else 'FAIL'}"
        failed |= not ok
        report.extend(lines)
        save_png(os.path.join(work, f"diff_{name}.png"), diff)
        # Blender | X-Plane | diff, at half size, one strip per view, for comparison.png
        strips.append(np.concatenate([a[::2, ::2], b[::2, ::2], diff[::2, ::2]], axis=1))
    if strips:
        # Pixel rows start at the bottom, so the first view goes last in the array
        save_png(os.path.join(work, "comparison.png"), np.concatenate(strips[::-1], axis=0))
    report.append("RESULT: " + ("FAIL" if failed else "PASS"))
    text = "\n".join(report)
    with open(os.path.join(work, "report.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    if failed:
        sys.exit(1)


# --- Main -----------------------------------------------------------------------------------------
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="parity_blender.py")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("sample")
    p.add_argument("blend")
    p.add_argument("--kind", choices=("basic", "static", "conditions"), default="basic")
    p = sub.add_parser("export")
    p.add_argument("blend")
    p.add_argument("root")
    p.add_argument("work")
    p.add_argument("--mode", default="palette")
    p.add_argument("--views", default=os.path.join(HERE, "views.json"))
    p.add_argument("--dataref", action="append")
    p = sub.add_parser("render")
    p.add_argument("blend")
    p.add_argument("root")
    p.add_argument("work")
    p.add_argument("--mode", default="palette")
    p.add_argument("--size", required=True)
    p.add_argument("--condition", action="append", help="NAME=0|1, the state X-Plane's conditions are in")
    p = sub.add_parser("compare")
    p.add_argument("work")
    p.add_argument("--mode")
    p.add_argument("--min-agreement", type=float, default=0.97)
    p.add_argument("--min-iou", type=float, default=0.85)
    p.add_argument("--min-texture", type=float, default=0.85)
    p.add_argument("--max-light-offset", type=float, default=30)
    args = parser.parse_args(argv)
    {"sample": cmd_sample, "export": cmd_export, "render": cmd_render, "compare": cmd_compare}[args.command](args)


main()
