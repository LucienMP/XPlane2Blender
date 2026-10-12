"""
Writes the library.txt entries for exported OBJs that are published under a library path.

library.txt goes in the scenery pack's root folder when the OBJs are exported into
'Custom Scenery/<pack>/', otherwise in the export folder. XPlane2Blender only manages its
own block in it, marked with the .blend file's name, so hand written entries and other
.blend files' blocks are kept:

    # BEGIN XPlane2Blender: trees.blend
    EXPORT_SEASON	spr,sum	lib/my_library/oak.obj	objects/oak_green.obj
    EXPORT_SEASON	fal,win	lib/my_library/oak.obj	objects/oak_bare.obj
    # END XPlane2Blender: trees.blend

Exporting an OBJ replaces its own lines in the block, so roots exported on their own or
with "Add to library.txt" turned off don't disturb the rest.
"""

import collections
import os
import re
from typing import Dict, Iterable, List, Optional, Tuple

from io_xplane2blender.xplane_constants import (
    LIBRARY_MODE_BACKUP,
    LIBRARY_MODE_EXCLUDE,
    LIBRARY_MODE_EXPORT,
    LIBRARY_MODE_EXTEND,
    LIBRARY_SEASONS,
)
from io_xplane2blender.xplane_helpers import logger

LIBRARY_FILENAME = "library.txt"
LIBRARY_HEADER = ["A", "1200", "LIBRARY"]

_PACK_ROOT = re.compile(r"^(.*/(?:Custom Scenery|default_scenery)/[^/]+)/.+$", re.IGNORECASE)

_COMMANDS = {
    LIBRARY_MODE_EXPORT: "EXPORT",
    LIBRARY_MODE_EXTEND: "EXPORT_EXTEND",
    LIBRARY_MODE_EXCLUDE: "EXPORT_EXCLUDE",
    LIBRARY_MODE_BACKUP: "EXPORT_BACKUP",
}
_SEASON_COMMANDS = {
    LIBRARY_MODE_EXPORT: "EXPORT_SEASON",
    LIBRARY_MODE_EXTEND: "EXPORT_EXTEND_SEASON",
    LIBRARY_MODE_EXCLUDE: "EXPORT_EXCLUDE_SEASON",
}


def begin_marker(blend_name: str) -> str:
    return f"# BEGIN XPlane2Blender: {blend_name}"


def end_marker(blend_name: str) -> str:
    return f"# END XPlane2Blender: {blend_name}"


def library_folder(obj_path: str, export_folder: str) -> str:
    """The folder whose library.txt publishes obj_path: its scenery pack's root, else export_folder"""
    match = _PACK_ROOT.match(obj_path.replace("\\", "/"))
    return os.path.normpath(match.group(1)) if match else os.path.normpath(export_folder)


def library_line(library_props, real_path: str, obj_name: str) -> Optional[str]:
    """
    The library.txt line publishing real_path (relative to library.txt) as library_props say,
    or None after logging an error
    """
    virtual_path = library_props.virtual_path.strip().replace("\\", "/")
    if not virtual_path:
        logger.error(f"{obj_name}: 'Add to library.txt' is on, but its Library Path is empty")
        return None
    if any(c.isspace() for c in virtual_path) or virtual_path.startswith("/"):
        logger.error(
            f"{obj_name}: Library Path '{virtual_path}' must be relative, e.g. 'lib/my_library/oak.obj',"
            " and can't contain spaces"
        )
        return None
    if os.path.splitext(virtual_path)[1].lower() != ".obj":
        logger.warn(f"{obj_name}: Library Path '{virtual_path}' doesn't end in .obj, X-Plane may not find it")

    if library_props.seasonal:
        seasons = [s for s in LIBRARY_SEASONS if getattr(library_props, f"season_{s}")]
        if not seasons:
            logger.error(f"{obj_name}: 'By Season' is on, but no season is ticked")
            return None
        if library_props.mode not in _SEASON_COMMANDS:
            logger.error(f"{obj_name}: X-Plane has no seasonal version of '{library_props.mode.title()}'")
            return None
        if library_props.use_ratio:
            logger.warn(f"{obj_name}: X-Plane has no seasonal Ratio, the Ratio is ignored")
        fields = [_SEASON_COMMANDS[library_props.mode], ",".join(seasons)]
    elif library_props.use_ratio:
        if library_props.mode != LIBRARY_MODE_EXPORT:
            logger.warn(f"{obj_name}: Ratio only applies to the 'Export' mode, the Ratio is ignored")
            fields = [_COMMANDS[library_props.mode]]
        else:
            fields = ["EXPORT_RATIO", f"{library_props.ratio:g}"]
    else:
        fields = [_COMMANDS[library_props.mode]]

    return "\t".join(fields + [virtual_path, real_path])


def _real_path(line: str) -> str:
    return line.rsplit("\t", 1)[-1]


def _check_paths(lines: Iterable[str], library_txt: str) -> None:
    """X-Plane's rules for one library path: seasonal or not, and seasonal covering the whole year"""
    by_path = collections.defaultdict(list)
    for line in lines:
        fields = line.split("\t")
        if len(fields) >= 3:
            by_path[fields[-2]].append(fields)
    for virtual_path, entries in by_path.items():
        seasonal = [e for e in entries if e[0].endswith("_SEASON")]
        if seasonal and len(seasonal) != len(entries):
            logger.error(
                f"{library_txt}: '{virtual_path}' is published both by season and not by season."
                " X-Plane allows one or the other for a library path"
            )
        elif seasonal:
            covered = {s for e in seasonal for s in e[1].split(",")}
            missing = [s for s in LIBRARY_SEASONS if s not in covered]
            if missing:
                logger.warn(
                    f"{library_txt}: '{virtual_path}' has no OBJ for {', '.join(missing)}."
                    " X-Plane needs every season covered, or it shows nothing then"
                )


def update_library_txt(
    library_txt: str,
    blend_name: str,
    exported_real_paths: Iterable[str],
    new_lines: Iterable[str],
    dry_run: bool = False,
) -> bool:
    """
    Replaces the lines for exported_real_paths in the .blend file's block of library_txt with
    new_lines, keeping everything else. Returns False after logging an error.
    """
    begin, end = begin_marker(blend_name), end_marker(blend_name)
    if os.path.exists(library_txt):
        with open(library_txt, "r", encoding="utf8", errors="surrogateescape") as f:
            lines = f.read().splitlines()
    else:
        lines = []

    begin_i = next((i for i, l in enumerate(lines) if l.strip() == begin), None)
    end_i = next((i for i, l in enumerate(lines) if l.strip() == end), None)
    if (begin_i is None) != (end_i is None) or (begin_i is not None and end_i < begin_i):
        logger.error(
            f"{library_txt}: the '{begin}' / '{end}' lines are broken, fix or remove them and export again"
        )
        return False

    exported = set(exported_real_paths)
    block = [] if begin_i is None else lines[begin_i + 1 : end_i]
    block = [l for l in block if l.strip() and _real_path(l.strip()) not in exported]
    block = sorted(set(block) | set(new_lines), key=lambda l: (l.split("\t")[-2:], l))
    _check_paths(block, library_txt)

    if begin_i is not None:
        before, after = lines[:begin_i], lines[end_i + 1 :]
    else:
        if not block:
            return True  # Nothing of ours to add, leave the file alone
        before, after = lines, []
        if not any(l.strip() and not l.lstrip().startswith("#") for l in before):
            before = before + LIBRARY_HEADER + [""]
        elif before and before[-1].strip():
            before = before + [""]

    lines = before + ([begin] + block + [end] if block else []) + after
    if dry_run:
        logger.info(f'Skipped writing {library_txt} due to "Dry Run"')
        return True
    try:
        with open(library_txt, "w", encoding="utf8", errors="surrogateescape", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
    except OSError as e:
        logger.error(f"Could not write {library_txt}: {e}")
        return False
    logger.success(f"Wrote {library_txt}")
    return True


def write_libraries(
    exported: List[Tuple["xplane_props.XPlaneLayer", str]],
    export_folder: str,
    blend_name: str,
    dry_run: bool = False,
) -> bool:
    """
    exported is each written OBJ's layer settings and absolute path. Updates the library.txt
    of every folder they were written into. Returns False after logging an error.
    """
    by_folder: Dict[str, Tuple[List[str], List[str]]] = collections.defaultdict(lambda: ([], []))
    for layer, obj_path in exported:
        folder = library_folder(obj_path, export_folder)
        real_path = os.path.relpath(obj_path, folder).replace("\\", "/")
        if real_path.startswith("../"):
            if layer.library.enabled:
                logger.error(
                    f"{layer.name}: {obj_path} isn't inside {folder}, so library.txt can't publish it."
                    " Export it inside the export folder or a scenery pack"
                )
                return False
            continue
        real_paths, new_lines = by_folder[folder]
        real_paths.append(real_path)
        if layer.library.enabled:
            line = library_line(layer.library, real_path, layer.name)
            if line is None:
                return False
            new_lines.append(line)

    for folder, (real_paths, new_lines) in by_folder.items():
        if not update_library_txt(
            os.path.join(folder, LIBRARY_FILENAME), blend_name, real_paths, new_lines, dry_run
        ):
            return False
    return True
