#!/usr/bin/env python3
"""Run final-20 SEP then MTObjects leave-one-galaxy-out cross-validation."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent


def run(command: list[str], label: str) -> None:
    print(f"\n=== Starting {label} ===", flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        raise RuntimeError(f"{label} failed with exit code {completed.returncode}")
    print(f"=== Completed {label} ===", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--injection-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--mtobjects-root", type=Path, required=True)
    parser.add_argument("--study-storage-root", type=Path, default=Path("/root/final20-optuna-studies"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--initial-points", type=int, default=8)
    parser.add_argument("--max-iter", type=int, default=32)
    parser.add_argument("--toys-per-image", type=int, default=10)
    args = parser.parse_args()
    common = [
        "--clean-list", str(args.clean_list),
        "--manifest", str(args.manifest),
        "--pc", "Desktop",
        "--injection-manifest", str(args.injection_manifest),
        "--cv-injection-set", "cross_validation",
        "--evaluation-injection-set", "winner_selection",
        "--workers", str(args.workers),
        "--initial-points", str(args.initial_points),
        "--max-iter", str(args.max_iter),
        "--toys-per-image", str(args.toys_per_image),
        "--toy-peak-sigma-min", "6",
        "--toy-peak-sigma-max", "30",
    ]
    run(
        [sys.executable, str(SCRIPT_DIR / "cross_validate_toy_objects_SEP.py"),
         *common, "--output-dir", str(args.output_root / "SEP_cross_validation"),
         "--study-storage-dir", str(args.study_storage_root / "SEP")],
        "SEP 20-fold cross-validation",
    )
    run(
        [sys.executable, str(SCRIPT_DIR / "cross_validate_toy_objects_MTObjects.py"),
         *common, "--output-dir", str(args.output_root / "MTObjects_cross_validation"),
         "--study-storage-dir", str(args.study_storage_root / "MTObjects"),
         "--mtobjects-root", str(args.mtobjects_root),
         "--bg-variance-log", "--bg-variance-step", "0", "--calibrate-bg-variance"],
        "MTObjects 20-fold cross-validation",
    )
    print("\nAll final-20 cross-validation stages completed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
