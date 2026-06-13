"""Render illustrative simulation animations and dump strided frames to disk.

For each of two hard-coded cases (an Optimal attempt and a Fitz attempt,
each defaulting to ``want_success=None`` so either a catch or a miss is
accepted) the script:

  * loads the simulation code from ``main.ipynb`` (without triggering the
    notebook's driver cells, so no stray batches are run);
  * searches for a randomized attempt that matches the desired outcome;
  * renders the MP4 of that attempt into ``videos/`` via the normal
    ``simulate(seed=...)`` path; and
  * extracts every third frame of that MP4 as numbered PNGs into a
    per-case subdirectory under ``simulation_frames/``.

With ``--n-runs N`` the script renders ``N`` independent examples per case,
each into its own subdirectory.

Output layout (with ``--n-runs 1``, the default)::

    simulation_frames/
        optimal/
            run_01/
                frame_0001.png     # original frame 1
                frame_0004.png     # original frame 4
                frame_0007.png     # ... every third frame
                ...
                intercept_marker.txt   # records seed, object, outcome, intercept frame
        fitz/
            run_01/
                frame_0001.png
                ...

With ``--n-runs 3``::

    simulation_frames/
        optimal/
            run_01/ ...
            run_02/ ...
            run_03/ ...
        fitz/
            run_01/ ...
            ...

Requires ``ffmpeg`` on ``$PATH`` (the simulation already uses it for MP4
output).

Usage::

    python scripts/screenshot_simulation.py            # 1 run per case
    python scripts/screenshot_simulation.py --n-runs 5 # 5 runs per case
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import types

import numpy as np


# ---------------------------------------------------------------------------
# Hard-coded cases. Edit here if you want different prefixes, to filter the
# search by a specific object, or to require a specific outcome.
#
# ``want_success``:
#   True  -> only catches
#   False -> only misses
#   None  -> either outcome (the run is labelled by what we actually find)
# ---------------------------------------------------------------------------
CASES = [
    {"prefix": "optimal", "dog": "optimal",
     "want_success": None, "object_filter": None},
    {"prefix": "fitz",    "dog": "fitz",
     "want_success": None, "object_filter": None},
]
MAX_SEARCH_ATTEMPTS = 2000
DEFAULT_SEARCH_SEED = 0  # makes the example selection reproducible

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

VIDEOS_DIR = os.path.join(ROOT, "videos")
DEFAULT_OUT_DIR = os.path.join(ROOT, "assets/figures/simulation_frames")
DEFAULT_FRAME_STRIDE = 2  # save every Nth frame from the rendered MP4


# ---------------------------------------------------------------------------
# Load the simulation code from main.ipynb without executing driver cells.
# ---------------------------------------------------------------------------
_DRIVER_CALL_PREFIXES = (
    "run_batch(", "simulate(", "simulate_silent(",
    "print_drag_table(", "print(",
)
_DISPLAY_EXPRESSIONS = {"OPTIMAL, FITZ", "FITZ, OPTIMAL"}


def _is_driver_only_cell(src: str) -> bool:
    lines = [ln.strip() for ln in src.splitlines()]
    payload = [ln for ln in lines if ln and not ln.startswith("#")]
    if not payload:
        return False
    for ln in payload:
        if ln in _DISPLAY_EXPRESSIONS:
            continue
        if any(ln.startswith(pref) for pref in _DRIVER_CALL_PREFIXES):
            continue
        return False
    return True


def _load_notebook_simulation_module() -> types.ModuleType:
    nb_path = os.path.join(ROOT, "main.ipynb")
    with open(nb_path, encoding="utf-8") as f:
        nb = json.load(f)

    sources = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if _is_driver_only_cell(src):
            continue
        sources.append(src)
    code = "\n\n".join(sources)

    mod = types.ModuleType("main_notebook")
    mod.__file__ = nb_path
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        exec(compile(code, nb_path, "exec"), mod.__dict__)
    finally:
        os.chdir(cwd)
    return mod


# ---------------------------------------------------------------------------
# Locate a matching attempt, compute the intercept frame index.
# ---------------------------------------------------------------------------
def _wanted_label(want_success):
    """Human-readable description of the requested outcome filter."""
    if want_success is None:
        return "catch or miss"
    return "successful catch" if want_success else "failed attempt"


def _find_matching_attempt(mod, dog, want_success, object_filter, max_attempts):
    """Return (seed, thrown_object, success, intercept_frame_index, total_frames).

    ``want_success`` may be ``True`` (only catches), ``False`` (only misses),
    or ``None`` (accept either outcome).
    """
    for _ in range(max_attempts):
        candidate_seed = random.randint(0, 2**31 - 1)
        result = mod.simulate_silent(seed=candidate_seed, dog=dog)
        if result is None:
            continue
        success, seed, thrown_object = result
        if object_filter and thrown_object != object_filter:
            continue
        if want_success is not None and success != want_success:
            continue

        # Re-seed and re-run the deterministic setup + attempt so we can
        # read back the timeline and intercept_t to locate the catch frame.
        random.seed(seed)
        np.random.seed(seed)
        setup = mod._setup_throw(dog)
        if setup is None:
            continue
        t, num_frames, _dog_positions, _intercept_target, intercept_t, \
            _intercept_is_q2, _jaw_target = mod._run_attempt(dog, setup)
        if intercept_t is None:
            # Failure mode with no plan; skip and keep searching.
            continue
        intercept_idx = int(np.argmin(np.abs(t - intercept_t)))
        return seed, thrown_object, success, intercept_idx, num_frames

    raise RuntimeError(
        f"Could not find a {_wanted_label(want_success)} attempt "
        f"for dog={dog.name}"
        + (f" with object={object_filter}" if object_filter else "")
        + f" in {max_attempts} tries."
    )


def _ensure_ffmpeg():
    if subprocess.run(["which", "ffmpeg"], capture_output=True).returncode != 0:
        sys.exit("ffmpeg not found on PATH; please install it first.")


def _extract_strided_frames(video_path, out_dir, stride):
    """Dump every ``stride``-th frame of ``video_path`` into ``out_dir``.

    Frames are written as ``frame_NNNN.png`` using the *original* (full)
    1-based frame number, so e.g. ``stride=3`` produces ``frame_0001.png``,
    ``frame_0004.png``, ``frame_0007.png``, ... and intercept indices computed
    against the full timeline still refer to the right PNG when present.
    """
    os.makedirs(out_dir, exist_ok=True)
    if stride < 1:
        raise ValueError("stride must be >= 1")
    out_pattern = os.path.join(out_dir, "frame_%04d.png")
    # ``not(mod(n,stride))`` keeps frames whose 0-based index is a multiple
    # of ``stride`` (i.e. 0, stride, 2*stride, ...). With -start_number 1
    # ffmpeg then writes ``frame_0001.png`` for the first kept frame, but
    # we want the filename to carry the *original* frame number so the user
    # can match it against the intercept marker. We therefore re-mux with
    # the ``select`` filter and a frame-number expression.
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", video_path,
        "-vf", f"select='not(mod(n\\,{stride}))'",
        "-frame_pts", "1",
        "-fps_mode", "vfr",
        out_pattern,
    ]
    print("  " + " ".join(cmd))
    subprocess.run(cmd, check=True)

    # ffmpeg's ``-frame_pts 1`` names the file after the PTS, which for our
    # MP4s (CFR at 30 fps with PTS = frame index in source) gives the
    # original 0-based index. Rename to 1-based ``frame_NNNN.png`` so the
    # numbering matches the intercept marker, which is 1-based.
    for name in sorted(os.listdir(out_dir)):
        if not (name.startswith("frame_") and name.endswith(".png")):
            continue
        zero_based = int(name[len("frame_"):-len(".png")])
        new_name = f"frame_{zero_based + 1:04d}.png"
        if new_name != name:
            os.replace(os.path.join(out_dir, name),
                       os.path.join(out_dir, new_name))


def _write_intercept_marker(out_dir, intercept_idx, total_frames, seed,
                            thrown_object, stride, success):
    """Tiny text file recording which frame is the catch moment for this run."""
    # PNGs are named with the original 1-based frame number, so the catch
    # frame is ``frame_{intercept_idx + 1:04d}.png``. With stride > 1 that
    # exact frame is only present if (intercept_idx % stride) == 0.
    intercept_png_idx = intercept_idx + 1
    saved = (intercept_idx % stride) == 0
    nearest_zero_based = (intercept_idx // stride) * stride
    marker_path = os.path.join(out_dir, "intercept_marker.txt")
    with open(marker_path, "w", encoding="utf-8") as f:
        f.write(
            "seed={seed}\n"
            "object={obj}\n"
            "outcome={outcome}\n"
            "total_frames={total}\n"
            "frame_stride={stride}\n"
            "intercept_frame_index_zero_based={zb}\n"
            "intercept_frame_png=frame_{png:04d}.png\n"
            "intercept_frame_saved={saved}\n"
            "nearest_saved_frame_png=frame_{near:04d}.png\n".format(
                seed=seed, obj=thrown_object,
                outcome="catch" if success else "miss",
                total=total_frames,
                stride=stride, zb=intercept_idx, png=intercept_png_idx,
                saved="yes" if saved else "no",
                near=nearest_zero_based + 1,
            )
        )


def _process_case(mod, case, run_index, base_out_dir, stride):
    dog_obj = mod.OPTIMAL if case["dog"] == "optimal" else mod.FITZ
    run_tag = f"run_{run_index:02d}"
    print(f"\n[{case['prefix']} / {run_tag}] searching for a "
          f"{_wanted_label(case['want_success'])} attempt "
          f"(dog={dog_obj.name}"
          + (f", object={case['object_filter']}" if case["object_filter"] else "")
          + ") ...")

    seed, thrown_object, success, intercept_idx, num_frames = _find_matching_attempt(
        mod, dog_obj, case["want_success"],
        case["object_filter"], MAX_SEARCH_ATTEMPTS,
    )
    label = "catch" if success else "miss"
    print(f"[{case['prefix']} / {run_tag}] found seed={seed} "
          f"({thrown_object}, {label}); intercept frame = {intercept_idx} "
          f"of {num_frames}")

    os.makedirs(VIDEOS_DIR, exist_ok=True)
    video_path = mod.simulate(seed=seed, dog=dog_obj, video_dir='temp')
    if video_path is None:
        sys.exit(f"simulate() returned None for seed={seed}")

    out_dir = os.path.join(base_out_dir, case["prefix"], run_tag)
    print(f"[{case['prefix']} / {run_tag}] extracting every {stride}rd/th "
          f"frame into {out_dir} ...")
    _extract_strided_frames(video_path, out_dir, stride)
    _write_intercept_marker(out_dir, intercept_idx, num_frames,
                            seed, thrown_object, stride, success)


def _parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--n-runs", type=int, default=1,
                   help="Number of independent runs per case (default: 1).")
    p.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                   help=f"Base output directory (default: {DEFAULT_OUT_DIR}).")
    p.add_argument("--frame-stride", type=int, default=DEFAULT_FRAME_STRIDE,
                   help=("Save every Nth frame from each MP4 (default: "
                         f"{DEFAULT_FRAME_STRIDE}). Use 1 to save every frame."))
    p.add_argument("--search-seed", type=int, default=DEFAULT_SEARCH_SEED,
                   help=("Seed for the RNG that picks candidate attempts "
                         f"during the outcome search (default: {DEFAULT_SEARCH_SEED}). "
                         "Use a different value to get different examples."))
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    if args.n_runs < 1:
        sys.exit("--n-runs must be >= 1.")
    if args.frame_stride < 1:
        sys.exit("--frame-stride must be >= 1.")

    _ensure_ffmpeg()
    print("Loading simulation code from main.ipynb ...")
    mod = _load_notebook_simulation_module()
    # Reproducible candidate-seed exploration across script runs.
    random.seed(args.search_seed)

    for case in CASES:
        for run_index in range(1, args.n_runs + 1):
            _process_case(mod, case, run_index, args.out_dir, args.frame_stride)

    print("\nDone.")


if __name__ == "__main__":
    main()
