# Running the XPlane2Blender tests

XPlane2Blender has two test runners. Both run the same test files in the same way; they
differ in how many run at once.

- **`tests_parallel.py`** runs several test files at once and takes about a minute for the
  whole suite. Use it while you work.
- **`tests.py`** runs one file at a time, about 6 minutes. It can stop at the first
  failure and show each file's output as it goes, and the GitHub Actions workflow uses it.

Both need Blender 5.2 and the full source code: the `tests` folder next to the
`io_xplane2blender` folder.

## Quick start

From the repository's folder:

```
python tests_parallel.py --blender "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
```

Set the `BLENDER` environment variable to the same path, or put Blender on your PATH, and
`--blender` can be left out. When everything passes, the last line says so:

```
188 files, 701 tests, 0 errors, 0 failures, 8 skipped, 0 files failed, in 68 s
```

The exit code is 0 when every file passed and 1 otherwise, so the runner can be used in a
script or a git hook.

## How the parallel runner works

Each test file is a Python script that Blender runs in the background, with the file's
`.blend` of the same name when there is one. `tests_parallel.py` starts these Blender
processes exactly as `tests.py` does, with the same arguments and the add-on found the
same way, so a test passes or fails the same under both. The difference is that it keeps
several Blender processes running at once, by default one per CPU, at most 8.

Each Blender process is separate, so test files can't affect each other, with two
exceptions. These run on their own after all the others:

- **`tests/utils/lights_parser.test.py`** temporarily replaces the add-on's `lights.txt`
  with test versions. Any light test running at the same time would read the wrong file.
- **`tests/xplane_visual/`**, the X-Plane checks, which only run with `--xplane`. Each one
  starts X-Plane, and only one X-Plane can run at a time.

If you add a test file that changes a file other tests read, add it to the `ALONE`
pattern at the top of `tests_parallel.py`.

Before it starts, the runner empties `tests/tmp`, as `tests.py` does. Test files write their
output there, so copy anything you want to keep from it before the next run.

## Options

| Option | What it does |
|---|---|
| `--blender PATH` | Blender executable. Default: `$BLENDER`, or `blender` on the PATH. |
| `-j N`, `--jobs N` | Blender processes at once. Default: the number of CPUs, at most 8. Use fewer if the machine runs short of memory. |
| `-f REGEX`, `--filter REGEX` | Only test files whose path matches, for example `-f "lights\|animation"`. Paths use `/`, as in `tests/lights/...`. |
| `--exclude REGEX` | Leave out test files whose path matches. |
| `--xplane` | Also run the X-Plane checks in `tests/xplane_visual`, one at a time at the end. X-Plane must be installed and closed, with its Web API on. They add about 20 minutes. |
| `--timeout SECONDS` | Stop a test file that runs longer. Default 600. |
| `--force-xplane-debug` | As in `tests.py`: debug comments in the exported OBJs. |
| `--list` | Print the files that would run, in order, and stop. |
| `-v`, `--verbose` | Print every file's result as it finishes, not only failures. |

## Reading the output

While it runs, the runner prints one line per failed file as soon as it finishes:

```
FAILED  tests/features/lod.test.py: 0 errors, 2 failures
FAILED  tests/lights/lights.test.py: no test result: Blender or the test file crashed
```

At the end, it prints the last part of each failed file's output, then the totals.
"No test result" means the file never reached the end of its tests: Blender crashed, the
test script raised an error outside a test, or the file timed out. The output above it
says which.

To look at one failure more closely, run that file alone with the serial runner, which
prints its whole output:

```
python tests.py --blender "C:\...\blender.exe" -f "features/lod.test"
```

## Comparing what an exporter change does

Set `XP2B_TEST_OUTPUT_DIR` to a folder, and every test that compares its export against
a fixture also saves that export there, named after the fixture's path. It works with
both runners. Run the suite once before your change and once after, into different
folders, and compare the folders to see every OBJ your change affected. The same files
can replace fixtures when a change of output is intended.

## The X-Plane checks

`tests/xplane_visual` holds the checks that photograph exports in X-Plane and compare them
with Blender's renders (see `io_xplane2blender/xplane_parity/README.md`). They only run
with `--xplane`, with either runner, because they start X-Plane: about three minutes per
check, 20 minutes for all of them. Point the checks at X-Plane with the `XPLANE_DIR`
environment variable (default `E:\X-Plane 12`). X-Plane must be closed, and the checks
refuse to start while it's running.

## Continuous integration

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs `tests.py` on every push,
on Windows with Blender 5.2.2. It doesn't run the X-Plane checks, since there's no X-Plane
there. If something passes locally but fails there, check the drive: the runner checks
the repository out on `D:`, and Windows can't make a path relative across drives.

## Which runner to use

| | `tests_parallel.py` | `tests.py` |
|---|---|---|
| Whole suite, this machine (16 CPUs) | about 70 s | about 6 minutes (374 s) |
| Output | Failures only, as they happen; full output of failed files at the end | Every file's output as it runs (`-q` and `-p` to cut it down) |
| On a failure | Keeps going | Stops, unless `-c` |
| Start part-way | No | `-s REGEX` |
| Blender's own debug output | No | `--force-blender-debug` |
| Your Blender preferences instead of factory settings | No | `-n` |
