# This is a small python script that launches Blender from the command line with the X-Plane exporter out of your GIT repo.  This
# saves having to work "in" the Blender add-ons dir, having to check out code to the Blender add-ons dir, or any fancy sim-linking.
#
# Like the test script, --blender lets you specify an executable, and it injects the code via the --addons flag, e.g.
#
# python3 run.py --blender /Applications/Blender.app/Contents/MacOS/Blender

import argparse
import os
import subprocess
import sys


def blender_user_scripts() -> str:
    """
    The BLENDER_USER_SCRIPTS folder that lets Blender load io_xplane2blender from this repo:
    the repo itself, through its addons/modules symlink. On Windows clones without symlink
    support (git's core.symlinks=false), that symlink is a small text file, so a folder in the
    temp directory gets an addons/modules junction to the repo instead (#710)
    """
    here = os.path.dirname(os.path.realpath(__file__))
    if os.path.isdir(os.path.join(here, "addons", "modules")):
        return here
    import hashlib
    import tempfile

    scripts = os.path.join(
        tempfile.gettempdir(),
        "xplane2blender_scripts_" + hashlib.sha1(here.encode()).hexdigest()[:8],
    )
    link = os.path.join(scripts, "addons", "modules")
    if not os.path.isdir(link):
        os.makedirs(os.path.dirname(link), exist_ok=True)
        if os.name == "nt":
            subprocess.run(["cmd", "/c", "mklink", "/J", link, here], check=True, capture_output=True)
        else:
            os.symlink(here, link)
    return scripts

def _make_argparse():
    parser = argparse.ArgumentParser(description="Runs the XPlane2Blender test suite")
    blender_options = parser.add_argument_group("Blender Options")

    blender_options.add_argument(
        "--blender",
        default="blender",  # Use the blender in the system path
        type=str,
        help="Provide alternative path to Blender executable",
    )
    blender_options.add_argument(
        "--force-blender-debug",
        help="Turn on Blender's --debug flag",
        action="store_true",
    )
    blender_options.add_argument(
        "-n",
        "--no-factory-startup",
        help="Run Blender with current prefs rather than factory prefs",
        action="store_true",
    )
    return parser


def main(argv=None) -> int:

    if argv is None:
        argv = _make_argparse().parse_args(sys.argv[1:])

    blender_args = [
        argv.blender,
        "--addons",
        "io_xplane2blender",
                "--factory-startup",
    ]

    if argv.no_factory_startup:
        blender_args.remove("--factory-startup")

    if argv.force_blender_debug:
        blender_args.append("--debug")

    # Small Hack!
    # Blender stops parsing after '--', so we can append the test runner
    # args and bridge the gap without anything fancy!
    blender_args.extend(["--"] + sys.argv[1:])

    # print the command used to execute the script
    # to be able to easily re-run it manually to get better error output
    print(" ".join(blender_args))

    # Environment variables - in order for --addons to work, we need to have OUR folder
    # exist, and we need to have "addons/modules" simlink BACK to us to create the illusion
    # of the directory structure Blender expects.
    # Keep the rest of the environment: without it (e.g. SYSTEMROOT), Blender's Python
    # can't start on Windows (#710)
    enviro = dict(os.environ)
    enviro["BLENDER_USER_SCRIPTS"] = blender_user_scripts()

    # Run Blender, normalize output line endings because Windows is dumb
    out = subprocess.run(
        blender_args, universal_newlines=True, env=enviro
    )  # type: str


main()

