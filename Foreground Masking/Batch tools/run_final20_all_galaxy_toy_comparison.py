#!/usr/bin/env python3
"""Apply final-20 SEP/MTO toy parameters to all galaxies and combine PNGs."""

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
    if not summary.exists():
        return False
    with summary.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return len(rows) >= expected and all(row.get("status", "").casefold() == "ok" for row in rows)


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
    args = parser.parse_args()

    sep_dir = args.output_root / "SEP"
    mto_dir = args.output_root / "MTObjects"
    combined_dir = args.output_root / "Combined"
    args.output_root.mkdir(parents=True, exist_ok=True)
    common = [
        "--manifest", str(args.manifest), "--pc", "Desktop",
        "--toys-per-image", "10", "--toy-seed", "202608299",
        "--toy-peak-sigma-min", "6", "--toy-peak-sigma-max", "30",
        "--clean-galaxies-file", str(args.clean_list),
        "--expected-clean-galaxies", "20", "--dpi", "120",
    ]

    if not completed(sep_dir / "sep_optimised_apply_summary.csv", args.expected_galaxies):
        mode = "--resume-output-dir" if sep_dir.exists() else "--output-dir"
        run([
            sys.executable, str(HERE / "batch_toy_objects_SEP.py"), *common,
            "--best-json", str(args.sep_best), mode, str(sep_dir),
            "--run-label", "final20_cross_validated",
        ], "SEP on all galaxies")
    else:
        print("SEP all-galaxy batch already complete; reusing it.", flush=True)

    if not completed(mto_dir / "mtobjects_optimised_apply_summary.csv", args.expected_galaxies):
        mode = "--resume-output-dir" if mto_dir.exists() else "--output-dir"
        run([
            sys.executable, str(HERE / "batch_toy_objects_MTObjects.py"), *common,
            "--best-json", str(args.mto_best), "--mtobjects-root", str(args.mtobjects_root),
            mode, str(mto_dir), "--run-label", "final20_relaxed_cv_fold11",
        ], "MTObjects on all galaxies")
    else:
        print("MTObjects all-galaxy batch already complete; reusing it.", flush=True)

    if not combined_dir.exists():
        run([
            sys.executable, str(FOREGROUND / "Utilities" / "combine_toy_method_pngs.py"),
            "--mto-dir", str(mto_dir), "--sep-dir", str(sep_dir),
            "--output-dir", str(combined_dir),
        ], "Combined SEP/MTObjects PNGs")
    print(f"\nAll-galaxy toy comparison complete: {args.output_root}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
