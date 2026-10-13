"""
The Blender side of the visual parity test (see ../README.md). Runs inside Blender,
with the XPlane2Blender add-on loaded, as parity.py invokes it:

    blender -b --factory-startup --addons io_xplane2blender --python parity_blender.py -- COMMAND ...

    sample OUT.blend
        Makes the sample scene: coloured boxes, an animated flap, a part hidden by a dataref.
    export BLEND ROOT WORK [--views VIEWS.json] [--dataref NAME=VALUE ...]
        Exports ROOT to WORK/model.obj (textures renamed to palette.png), writes palette.png,
        booth.obj, VIEWS and DATAREFS for the plugin, and views_resolved.json.
    render BLEND ROOT WORK --size WxH
        Renders WORK/blender_<view>.png for each resolved view, posed by the datarefs.
    compare WORK
        Classifies blender_<view>.png and xplane_<view>.png into palette colours and
        compares them; writes report.txt and diff_<view>.png. Exit code 1 on failure.
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
sys.path.insert(0, os.path.dirname(HERE))
import make_booth  # noqa: E402

from io_xplane2blender.xplane_helpers import get_action_fcurves, logger, vec_b_to_x  # noqa: E402
from io_xplane2blender.xplane_types import xplane_file  # noqa: E402

BACKGROUND = make_booth.BACKGROUND
MODEL_COLOURS = [name for name, _ in make_booth.PALETTE if name != BACKGROUND]


# --- Sample scene --------------------------------------------------------------------------
def make_material(name, image):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    principled = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    mat.node_tree.links.new(tex.outputs["Color"], principled.inputs["Base Color"])
    nodes.active = tex  # Workbench's texture colour mode draws the active image node
    return mat


def box(name, colour, size, location, rotation=(0, 0, 0), parent=None, materials=None):
    sx, sy, sz = (s / 2 for s in size)
    verts = [(x, y, z) for z in (-sz, sz) for y in (-sy, sy) for x in (-sx, sx)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    # Outward normals: X-Plane culls back faces, Blender's Workbench draws both sides, and
    # the first version of this sample had its top and bottom faces inside out. The parity
    # test found that in the top view, which is the kind of thing it is for
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    uv = mesh.uv_layers.new()
    u, v = make_booth.cell_uv(colour)
    for loop in mesh.loops:
        uv.data[loop.index].uv = (u, v)
    mesh.materials.append(materials[colour])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = [math.radians(r) for r in rotation]
    obj.parent = parent
    return obj


def cmd_sample(args):
    from io_xplane2blender.tests import test_creation_helpers as tch

    out_dir = os.path.dirname(os.path.abspath(args.blend))
    os.makedirs(out_dir, exist_ok=True)
    tch.delete_everything()
    make_booth.write_palette(os.path.join(out_dir, "palette.png"))
    image = bpy.data.images.load(os.path.join(out_dir, "palette.png"))
    materials = {name: make_material(name, image) for name in MODEL_COLOURS}

    root = bpy.data.objects.new("parity_sample", None)
    bpy.context.scene.collection.objects.link(root)
    root.xplane.isExportableRoot = True
    root.xplane.layer.name = "model"
    root.xplane.layer.export_type = "scenery"
    root.xplane.layer.texture = "//palette.png"
    root.xplane.layer.texture_lit = "//palette.png"

    box("cube_red", "red", (2, 2, 2), (0, 0, 1), parent=root, materials=materials)
    box("post_blue", "blue", (0.6, 0.6, 4), (3, 0, 2), parent=root, materials=materials)
    box("wedge_yellow", "yellow", (2, 1, 0.5), (-3, 1, 0.25), rotation=(0, 0, 30), parent=root, materials=materials)
    box("bar_white", "white", (6, 0.3, 0.3), (0, -1.5, 3.5), parent=root, materials=materials)
    box("hidden_white", "white", (1, 1, 1), (0, 2.5, 0.5), parent=root, materials=materials)
    box("flag_magenta", "magenta", (0.2, 1.5, 1), (-1.5, 2.5, 3), parent=root, materials=materials)

    # The flap hinges 0..60 degrees about X with sim/cockpit2/controls/flap_ratio 0..1,
    # keyed at frames 1 and 11, so frame = 1 + 10 * value
    flap = box("flap_cyan", "cyan", (2, 0.2, 1), (0, -2.5, 1.5), parent=root, materials=materials)
    dataref = "sim/cockpit2/controls/flap_ratio"
    tch.set_animation_data(flap, [
        tch.KeyframeInfo(idx=1, dataref_path=dataref, dataref_value=0.0, rotation=(0, 0, 0)),
        tch.KeyframeInfo(idx=11, dataref_path=dataref, dataref_value=1.0, rotation=(60, 0, 0)),
    ])
    # The white cube is hidden once the flaps pass half way
    hidden = bpy.data.objects["hidden_white"]
    hide = hidden.xplane.datarefs.add()
    hide.path = dataref
    hide.anim_type = "hide"
    hide.show_hide_v1, hide.show_hide_v2 = 0.5, 1.0

    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.blend))
    print("SAMPLE", args.blend)


# --- Export, views ------------------------------------------------------------------------
def open_blend(path):
    bpy.ops.wm.open_mainfile(filepath=os.path.abspath(path))


def find_root(name):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    return bpy.data.objects[name]


def root_matrix(root):
    if isinstance(root, bpy.types.Object):
        return root.matrix_world.copy()
    from mathutils import Matrix
    return Matrix.Identity(4)


def mesh_objects(root):
    if isinstance(root, bpy.types.Object):
        def walk(o):
            for c in o.children:
                yield c
                yield from walk(c)
        objects = list(walk(root))
    else:
        objects = list(root.all_objects)
    return [o for o in objects if o.type == "MESH" and o.visible_get()]


def model_bounds_obj_frame(root):
    """Min and max of every mesh corner, in OBJ coordinates relative to the root"""
    inverse = root_matrix(root).inverted()
    points = []
    for obj in mesh_objects(root):
        for corner in obj.bound_box:
            points.append(vec_b_to_x(inverse @ (obj.matrix_world @ Vector(corner))))
    if not points:
        raise SystemExit("ERROR: no meshes under the root")
    lo = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    hi = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return lo, hi


def resolve_views(views_spec, lo, hi):
    """Camera and target offsets (OBJ frame) for each orbit view, framed to the model's bounds"""
    fov = views_spec.get("fov_deg", 60)
    fill = views_spec.get("fill", 0.6)
    centre = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 0.5)
    # Frame for a 16:9 window; the vertical field of view is the tighter one
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
        # Keep the camera above the booth floor
        camera.y = max(camera.y, make_booth.BOOTH_FLOOR + 0.5)
        resolved.append({
            "name": view["name"],
            "camera_obj": list(camera),
            "target_obj": list(centre),
        })
    return {"fov_deg": fov, "fov_axis": views_spec.get("fov_axis", "horizontal"),
            "distance": distance, "bounds_obj": [list(lo), list(hi)], "views": resolved,
            "ignore": views_spec.get("ignore", [])}


def cmd_export(args):
    open_blend(args.blend)
    root = find_root(args.root)
    work = os.path.abspath(args.work)
    os.makedirs(work, exist_ok=True)
    bpy.context.scene.frame_set(1)
    xp = xplane_file.createFileFromBlenderRootObject(root, bpy.context.scene.view_layers[0])
    xp.export_dir = work
    text = xp.write()
    xplane_file._all_keyframe_infos.clear()
    errors = [e["message"] for e in logger.findErrors()]
    if errors:
        raise SystemExit("ERROR: export failed:\n" + "\n".join(errors))
    # The plugin loads textures next to the OBJ, so every texture is palette.png there
    lines = []
    for line in text.splitlines():
        if line.startswith("TEXTURE"):
            parts = line.split("\t")
            parts[-1] = os.path.basename(parts[-1])
            line = "\t".join(parts)
        lines.append(line)
    with open(os.path.join(work, "model.obj"), "w", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    make_booth.write_palette(os.path.join(work, "palette.png"))
    make_booth.write_booth(os.path.join(work, "booth.obj"))

    with open(args.views, encoding="utf-8") as f:
        views_spec = json.load(f)
    lo, hi = model_bounds_obj_frame(root)
    resolved = resolve_views(views_spec, lo, hi)
    datarefs = {}
    for item in args.dataref or []:
        name, _, value = item.partition("=")
        datarefs[name] = float(value)
    resolved["datarefs"] = datarefs
    with open(os.path.join(work, "views_resolved.json"), "w", encoding="utf-8") as f:
        json.dump(resolved, f, indent=2)
    with open(os.path.join(work, "VIEWS"), "w", newline="\n") as f:
        f.write(f"FOV {resolved['fov_deg']}\n")
        for view in resolved["views"]:
            f.write(" ".join(f"{c:.4f}" for c in view["camera_obj"] + view["target_obj"]) + "\n")
    with open(os.path.join(work, "DATAREFS"), "w", newline="\n") as f:
        for name, value in datarefs.items():
            f.write(f"{name} {value:g}\n")
    print(f"EXPORTED {len(lines)} lines, bounds {[round(c, 2) for c in lo]} to {[round(c, 2) for c in hi]},"
          f" camera distance {resolved['distance']:.1f} m, {len(resolved['views'])} views")


# --- Render ---------------------------------------------------------------------------------
def frame_for_dataref_values(root, values):
    """
    The frame that poses every animated object at the given dataref values. Each
    dataref's keyframes map value to frame linearly; every object must agree
    """
    frames = []
    for obj in mesh_objects(root) + [o for o in bpy.data.objects if o.type == "ARMATURE"]:
        for index, dataref in enumerate(obj.xplane.datarefs):
            if dataref.path not in values or dataref.anim_type != "transform":
                continue
            fcurve = next(
                (f for f in get_action_fcurves(obj.animation_data)
                 if f.data_path == f"xplane.datarefs[{index}].value"),
                None,
            )
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
    for obj in mesh_objects(root):
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
    scene.world.color = tuple(c / 255 for c in dict(make_booth.PALETTE)[BACKGROUND])
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


# --- Compare --------------------------------------------------------------------------------
def load_rgb(path):
    import numpy as np
    image = bpy.data.images.load(path)
    w, h = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(h, w, image.channels)
    bpy.data.images.remove(image)
    return pixels[:, :, :3]


def classify(rgb):
    """
    Palette index per pixel (make_booth.PALETTE order): dark pixels are the black
    background, -1 is a colour that matches nothing. Each other pixel is normalised
    by its brightest channel first, so exposure doesn't matter
    """
    import numpy as np
    names = [n for n, _ in make_booth.PALETTE]
    brightest = rgb.max(axis=2)
    dark = brightest < 0.08
    normalised = rgb / np.maximum(brightest, 1e-6)[:, :, None]
    labels = np.full(brightest.shape, -1, dtype=np.int8)
    best = np.full(brightest.shape, 1e9, dtype=np.float32)
    for index, (name, colour) in enumerate(make_booth.PALETTE):
        if name == BACKGROUND:
            continue
        reference = np.array(colour, dtype=np.float32) / max(colour)
        distance = ((normalised - reference) ** 2).sum(axis=2)
        closer = distance < best
        labels[closer] = index
        best[closer] = distance[closer]
    # X-Plane's night rendering shifts hues a little; 0.45 is about half way between palette colours
    labels[best > 0.45] = -1
    labels[dark] = names.index(BACKGROUND)
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


def save_png(path, rgb):
    import numpy as np
    h, w = rgb.shape[:2]
    image = bpy.data.images.new("diff", w, h, alpha=False)
    rgba = np.concatenate([rgb, np.ones((h, w, 1), dtype=np.float32)], axis=2)
    image.pixels[:] = rgba.ravel()
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)


def extent(labels, background, keep):
    """Bounding box of the model's compared pixels: (x0, y0, x1, y1) or None"""
    import numpy as np
    model = (labels >= 0) & (labels != background) & keep
    ys, xs = np.nonzero(model)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def cmd_compare(args):
    import numpy as np
    work = os.path.abspath(args.work)
    with open(os.path.join(work, "views_resolved.json"), encoding="utf-8") as f:
        resolved = json.load(f)
    background = [n for n, _ in make_booth.PALETTE].index(BACKGROUND)
    names = [n for n, _ in make_booth.PALETTE]
    report = []
    failed = False
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
        la, lb = classify(a), classify(b)
        keep = ~(edge_mask(la) | edge_mask(lb))
        # Ignored regions, as fractions of the image from the top left (overlays such as X-Plane's data output)
        h, w = la.shape
        for x0, y0, x1, y1 in resolved.get("ignore", []):
            # Blender's pixel rows start at the bottom
            keep[int(h - y1 * h) : int(h - y0 * h), int(x0 * w) : int(x1 * w)] = False
        agree = (la == lb) & keep
        agreement = agree.sum() / max(keep.sum(), 1)
        lines = [f"{name}: agreement {agreement * 100:.1f}% of {int(keep.sum())} compared pixels"]
        view_ok = agreement >= args.min_agreement
        total = la.size
        for index, colour in enumerate(names):
            in_a, in_b = (la == index) & keep, (lb == index) & keep
            cover = max(in_a.sum(), in_b.sum()) / total
            if cover < 0.005:
                continue
            union = (in_a | in_b).sum()
            iou = (in_a & in_b).sum() / max(union, 1)
            flag = "" if iou >= args.min_iou or index == background else "  <-- low"
            if flag:
                view_ok = False
            lines.append(f"    {colour:8s} IoU {iou:.3f}  Blender {in_a.sum() / total * 100:5.2f}%  X-Plane {in_b.sum() / total * 100:5.2f}%{flag}")
        unknown_b = ((lb == -1) & keep).sum() / total
        lines.append(f"    pixels matching no colour in X-Plane: {unknown_b * 100:.2f}%")
        ea, eb = extent(la, background, keep), extent(lb, background, keep)
        if ea and eb:
            wa, ha, wb, hb = ea[2] - ea[0], ea[3] - ea[1], eb[2] - eb[0], eb[3] - eb[1]
            lines.append(f"    model extent Blender {wa}x{ha} px at ({(ea[0] + ea[2]) // 2},{(ea[1] + ea[3]) // 2}),"
                         f" X-Plane {wb}x{hb} px at ({(eb[0] + eb[2]) // 2},{(eb[1] + eb[3]) // 2}),"
                         f" width ratio {wb / max(wa, 1):.3f}, height ratio {hb / max(ha, 1):.3f}")
        lines[0] += "  PASS" if view_ok else "  FAIL"
        failed |= not view_ok
        report.extend(lines)
        # Diff image: X-Plane's classification dimmed (background dark grey, unknown
        # white), disagreements in red, ignored edges black
        diff = np.zeros(a.shape, dtype=np.float32)
        for index, (name, colour) in enumerate(make_booth.PALETTE):
            diff[lb == index] = (0.15, 0.15, 0.15) if name == BACKGROUND else np.array(colour, dtype=np.float32) / 255 * 0.4
        diff[lb == -1] = (1, 1, 1)
        diff[~keep] = (0, 0, 0)
        diff[(la != lb) & keep] = (1, 0, 0)
        save_png(os.path.join(work, f"diff_{name}.png"), diff)
    report.append("RESULT: " + ("FAIL" if failed else "PASS"))
    text = "\n".join(report)
    with open(os.path.join(work, "report.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    if failed:
        sys.exit(1)


# --- Main -----------------------------------------------------------------------------------
def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="parity_blender.py")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("sample")
    p.add_argument("blend")
    p = sub.add_parser("export")
    p.add_argument("blend")
    p.add_argument("root")
    p.add_argument("work")
    p.add_argument("--views", default=os.path.join(os.path.dirname(HERE), "views.json"))
    p.add_argument("--dataref", action="append")
    p = sub.add_parser("render")
    p.add_argument("blend")
    p.add_argument("root")
    p.add_argument("work")
    p.add_argument("--size", required=True)
    p = sub.add_parser("compare")
    p.add_argument("work")
    p.add_argument("--min-agreement", type=float, default=0.97)
    p.add_argument("--min-iou", type=float, default=0.85)
    args = parser.parse_args(argv)
    {"sample": cmd_sample, "export": cmd_export, "render": cmd_render, "compare": cmd_compare}[args.command](args)


main()
