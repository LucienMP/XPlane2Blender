"""
Runs the XPlane2Blender test suite in parallel: several Blender processes at once, one per
test file, invoked exactly as tests.py invokes them. See TESTING.md.

    python tests_parallel.py --blender "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe"
    python tests_parallel.py -f "lights|animation" -j 4
    python tests_parallel.py --xplane            # also the X-Plane checks, one at a time at the end
    python tests_parallel.py --list              # which files would run, and in what order

Exit code 0 when every file passed, 1 otherwise.
"""
import argparse
import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import time
from typing import List, NamedTuple, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tests  # noqa: E402  the serial runner: blender_user_scripts() and clean_tmp_folder()

RESULTS = re.compile(
    r"RESULT: After (?P<run>\d+) tests got (?P<errors>\d+) errors, (?P<failures>\d+) failures, and (?P<skipped>\d+) skipped"
)
# Files that change something other test files read, so they run alone after the others:
# lights_parser temporarily replaces the add-on's lights.txt
ALONE = re.compile(r"tests/utils/lights_parser\.test\.py$")
# The X-Plane checks start X-Plane, and there can only be one
XPLANE = re.compile(r"tests/xplane_visual/")


class Result(NamedTuple):
    path: str
    seconds: float
    run: int
    errors: int
    failures: int
    skipped: int
    output: str
    problem: Optional[str]  # why no result could be read: a crash, a timeout

    @property
    def passed(self) -> bool:
        return self.problem is None and self.errors == 0 and self.failures == 0


def find_test_files(filter_re: Optional[str], exclude_re: Optional[str], xplane: bool) -> List[str]:
    found = []
    for root, _, files in os.walk(os.path.join(HERE, "tests")):
        for name in files:
            if not name.endswith(".test.py"):
                continue
            path = os.path.relpath(os.path.join(root, name), HERE).replace(os.sep, "/")
            if XPLANE.search(path) and not xplane:
                continue
            if filter_re and not re.search(filter_re, path):
                continue
            if exclude_re and re.search(exclude_re, path):
                continue
            found.append(path)
    return sorted(found)


def run_file(path: str, blender: str, env: dict, timeout: float, debug: bool) -> Result:
    blend = path[: -len(".py")] + ".blend"
    command = [blender, "--addons", "io_xplane2blender", "--factory-startup", "-noaudio", "-b"]
    if os.path.exists(os.path.join(HERE, blend)):
        command.append(blend)
    command += ["--python", path, "--"]
    if debug:
        command.append("--force-xplane-debug")
    start = time.perf_counter()
    try:
        output = subprocess.run(
            command, cwd=HERE, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            encoding="utf-8", errors="replace", timeout=timeout,
        ).stdout
    except subprocess.TimeoutExpired as e:
        output = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        return Result(path, time.perf_counter() - start, 0, 0, 0, 0, output, f"timed out after {timeout:.0f} s")
    except OSError as e:
        return Result(path, time.perf_counter() - start, 0, 0, 0, 0, "", f"Blender didn't start: {e}")
    seconds = time.perf_counter() - start
    match = RESULTS.search(output)
    if not match:
        return Result(path, seconds, 0, 0, 0, 0, output, "no test result: Blender or the test file crashed")
    return Result(path, seconds, int(match["run"]), int(match["errors"]), int(match["failures"]),
                  int(match["skipped"]), output, None)


def main() -> int:
    parser = argparse.ArgumentParser(description="Runs the XPlane2Blender test suite in parallel (see TESTING.md)")
    parser.add_argument("--blender", default=os.environ.get("BLENDER", "blender"),
                        help="Blender executable (default: $BLENDER, or blender on the PATH)")
    parser.add_argument("-j", "--jobs", type=int, default=min(os.cpu_count() or 4, 8),
                        help="Blender processes at once (default: the number of CPUs, at most 8)")
    parser.add_argument("-f", "--filter", help="only test files whose path matches this regular expression")
    parser.add_argument("--exclude", help="leave out test files whose path matches this regular expression")
    parser.add_argument("--xplane", action="store_true",
                        help="also run tests/xplane_visual, which start X-Plane (closed, Web API on), one at a time at the end")
    parser.add_argument("--timeout", type=float, default=600, help="seconds before a test file is stopped (default 600)")
    parser.add_argument("--force-xplane-debug", action="store_true", help="as in tests.py: debug output in the exported OBJs")
    parser.add_argument("--list", action="store_true", help="print the files that would run, in order, and stop")
    parser.add_argument("-v", "--verbose", action="store_true", help="print every file's result, not only failures")
    args = parser.parse_args()

    files = find_test_files(args.filter, args.exclude, args.xplane)
    parallel = [f for f in files if not (ALONE.search(f) or XPLANE.search(f))]
    alone = [f for f in files if ALONE.search(f)] + [f for f in files if XPLANE.search(f)]
    if args.list:
        for path in parallel:
            print(f"parallel  {path}")
        for path in alone:
            print(f"alone     {path}")
        return 0
    if not files:
        print("No test files match.")
        return 1
    if not (os.path.isfile(args.blender) or shutil.which(args.blender)):
        print(f"Blender not found: {args.blender!r}. Give its path with --blender, or set BLENDER.")
        return 1

    os.chdir(HERE)
    tests.clean_tmp_folder()
    env = dict(os.environ)
    env["BLENDER_USER_SCRIPTS"] = tests.blender_user_scripts()
    if args.xplane:
        env["XP2B_XPLANE_TESTS"] = "1"

    print(f"{len(parallel)} files on {args.jobs} jobs, then {len(alone)} alone", flush=True)
    start = time.perf_counter()
    results: List[Result] = []

    def report(result: Result) -> None:
        results.append(result)
        if not result.passed:
            why = result.problem or f"{result.errors} errors, {result.failures} failures"
            print(f"FAILED  {result.path}: {why}", flush=True)
        elif args.verbose:
            print(f"passed  {result.path} ({result.run} tests, {result.seconds:.0f} s)", flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(args.jobs, 1)) as pool:
        futures = [pool.submit(run_file, f, args.blender, env, args.timeout, args.force_xplane_debug) for f in parallel]
        for future in concurrent.futures.as_completed(futures):
            report(future.result())
    for path in alone:
        report(run_file(path, args.blender, env, args.timeout, args.force_xplane_debug))

    failed = sorted((r for r in results if not r.passed), key=lambda r: r.path)
    for result in failed:
        print("\n" + "=" * 75)
        print(f"{result.path}: {result.problem or 'FAILED'}")
        print("=" * 75)
        print(result.output[-6000:])
    totals = [sum(getattr(r, field) for r in results) for field in ("run", "errors", "failures", "skipped")]
    print(f"\n{len(results)} files, {totals[0]} tests, {totals[1]} errors, {totals[2]} failures, "
          f"{totals[3]} skipped, {len(failed)} files failed, in {time.perf_counter() - start:.0f} s")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
