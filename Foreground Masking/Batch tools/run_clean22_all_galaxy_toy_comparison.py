#!/usr/bin/env python3
"""Apply clean-22 winners to 182 galaxies and create SEP, MTO and combined PNG sets."""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
FOREGROUND = HERE.parent


def completed(summary: Path, expected: int) -> bool:
    if not summary.is_file():
        return False
    with summary.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    latest = {row.get("name", ""): row for row in rows if row.get("name")}
    return len(latest) == expected and all(row.get("status", "").casefold() == "ok" for row in latest.values())


def png_count(folder: Path) -> int:
    return sum(1 for path in folder.glob("*.png") if path.is_file()) if folder.is_dir() else 0


def run(command: list[str], label: str) -> None:
    print(f"\n=== {label} ===", flush=True)
    environment = os.environ.copy()
    environment["FOREGROUND_MASKING_PC"] = "Desktop"
    result = subprocess.run(command, check=False, env=environment)
    if result.returncode:
        raise RuntimeError(f"{label} failed with exit code {result.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--sep-best", type=Path, required=True)
    parser.add_argument("--mto-best", type=Path, required=True)
    parser.add_argument("--mtobjects-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--expected-galaxies", type=int, default=182)
    parser.add_argument("--toys-per-image", type=int, default=5)
    args = parser.parse_args()

    for winner in (args.sep_best, args.mto_best):
        if not winner.is_file():
            raise FileNotFoundError(f"Successful cross-validation winner is missing: {winner}")

    sep_dir = args.output_root / "SEP"
    mto_dir = args.output_root / "MTObjects"
    combined_dir = args.output_root / "Combined"
    args.output_root.mkdir(parents=True, exist_ok=True)
    common = [
        "--manifest", str(args.manifest), "--pc", "Desktop",
        "--toys-per-image", str(args.toys_per_image), "--toy-seed", "202608299",
        "--toy-peak-sigma-min", "6", "--toy-peak-sigma-max", "30",
        "--clean-galaxies-file", str(args.clean_list),
        "--expected-clean-galaxies", "22", "--dpi", "120",
    ]

    if not completed(sep_dir / "sep_optimised_apply_summary.csv", args.expected_galaxies):
        mode = "--resume-output-dir" if sep_dir.exists() else "--output-dir"
        run([
            sys.executable, str(HERE / "batch_toy_objects_SEP.py"), *common,
            "--best-json", str(args.sep_best), mode, str(sep_dir),
            "--run-label", "clean22_displayed_frame_5toy_cv",
        ], "SEP PNGs for all 182 galaxies")

    if not completed(mto_dir / "mtobjects_optimised_apply_summary.csv", args.expected_galaxies):
        mode = "--resume-output-dir" if mto_dir.exists() else "--output-dir"
        run([
            sys.executable, str(HERE / "batch_toy_objects_MTObjects.py"), *common,
            "--best-json", str(args.mto_best), "--mtobjects-root", str(args.mtobjects_root),
            mode, str(mto_dir), "--run-label", "clean22_displayed_frame_5toy_cv",
        ], "MTObjects PNGs for all 182 galaxies")

    if not completed(sep_dir / "sep_optimised_apply_summary.csv", args.expected_galaxies):
        raise RuntimeError("SEP did not finish all 182 galaxies successfully; combined PNGs were not started.")
    if not completed(mto_dir / "mtobjects_optimised_apply_summary.csv", args.expected_galaxies):
        raise RuntimeError("MTObjects did not finish all 182 galaxies successfully; combined PNGs were not started.")

    if png_count(combined_dir) != args.expected_galaxies:
        run([
            sys.executable, str(FOREGROUND / "Utilities" / "combine_toy_method_pngs.py"),
            "--mto-dir", str(mto_dir), "--sep-dir", str(sep_dir),
            "--output-dir", str(combined_dir), "--resume",
        ], "Combined SEP/MTObjects PNGs")

    if png_count(combined_dir) != args.expected_galaxies:
        raise RuntimeError(f"Expected {args.expected_galaxies} combined PNGs; found {png_count(combined_dir)}.")
    print(f"\nAll three 182-galaxy PNG sets are complete: {args.output_root}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
