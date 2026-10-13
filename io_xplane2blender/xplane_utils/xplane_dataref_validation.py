"""
Checks dataref paths against X-Plane's DataRefs.txt, bundled in the resources
folder (#344, #68, #345).

A path under 'sim/' that isn't in the file is probably misspelt. A plugin's own
datarefs aren't in the file, so other paths are only checked for their shape.
"""
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

from io_xplane2blender import xplane_helpers
from io_xplane2blender.xplane_utils import xplane_datarefs_txt_parser

# None until first used; empty when DataRefs.txt couldn't be read, so that nothing is checked
_known_datarefs: Optional[
    Dict[str, xplane_datarefs_txt_parser.DatarefInfoStruct]
] = None

_PATH_RE = re.compile(r"^(?P<base>[^\[\]]+)(?:\[(?P<index>[^\[\]]*)\])?$")


def get_known_datarefs() -> Dict[str, xplane_datarefs_txt_parser.DatarefInfoStruct]:
    """The bundled DataRefs.txt by path, parsed on first use"""
    global _known_datarefs
    if _known_datarefs is None:
        filepath = Path(
            xplane_helpers.get_plugin_resources_folder(), "DataRefs.txt"
        ).as_posix()
        result = xplane_datarefs_txt_parser.get_datarefs_txt_file_content(filepath)
        if isinstance(result, str):
            _known_datarefs = {}
        else:
            _known_datarefs = {info.path: info for info in result}
    return _known_datarefs


def split_dataref_path(path: str) -> Tuple[str, Optional[str]]:
    """
    'sim/a/b[3]' -> ('sim/a/b', '3'), 'sim/a/b' -> ('sim/a/b', None).
    A path with brackets that don't form one trailing [index] is returned whole
    """
    match = _PATH_RE.match(path)
    if match:
        return match.group("base"), match.group("index")
    return path, None


def dataref_problem(path: str) -> Optional[str]:
    """
    What is wrong with a dataref path as it will be written to the OBJ, or None.
    The answer reads on from "Dataref '{path}' ..."
    """
    path = path.strip()
    if not path or path == "none":
        return None
    if any(c.isspace() for c in path):
        return "has a space in it, X-Plane reads it only up to the space"

    base, index = split_dataref_path(path)
    if "[" in base or "]" in base:
        return "has misplaced [ ] brackets, an element is written as name[0]"
    if index is not None and not index.isdigit():
        return f"has the element [{index}], which must be a whole number like [0]"

    known = get_known_datarefs()
    info = known.get(base)
    if info is None:
        if base.startswith("sim/") and known:
            return (
                "isn't in X-Plane's DataRefs.txt. Check the spelling,"
                " or ignore this if a plugin defines it"
            )
        return None

    if info.is_array_type:
        if index is None:
            size = f"{info.array_size} elements" if info.array_size else "elements"
            return f"is an array of {size}, so add the one to use, like {base}[0]"
        if info.array_size and int(index) >= info.array_size:
            return (
                f"has only {info.array_size} elements,"
                f" [0] to [{info.array_size - 1}]"
            )
    elif index is not None:
        return f"isn't an array, so remove the [{index}]"
    return None
