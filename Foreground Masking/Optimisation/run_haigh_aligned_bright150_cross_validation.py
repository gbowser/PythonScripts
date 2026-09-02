#!/usr/bin/env python3
"""Run SEP and MTObjects CV using the immutable 150%-brightness injections."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
TRAINING_SETS = ("training_seed_1", "training_seed_2", "training_seed_3")
VALIDATION_SETS = ("validation_seed_1", "validation_seed_2")


def validate_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    peak_range = (manifest.get("source_configuration") or {}).get("peak_sigma")
    if peak_range != [9.0, 45.0] and peak_range != [9, 45]:
        raise ValueError(f"Expected the 150%-brightness 9--45 sigma manifest, found {peak_range!r}")
    available = set((manifest.get("injection_sets") or {}).keys())
    missing = set(TRAINING_SETS + VALIDATION_SETS) - available
    if missing:
        raise ValueError(f"Injection manifest is missing: {', '.join(sorted(missing))}")


def run(command: list[str], label: str, rejection_marker: Path) -> bool:
    print(f"\n=== {label} ===", flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        if rejection_marker.is_file():
            print(
                f"{label} completed with a scientific feasibility rejection; "
                "continuing to the other masking method.",
                flush=True,
            )
            return False
        raise RuntimeError(f"{label} failed with exit code {completed.returncode}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--injection-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--mtobjects-root", type=Path, required=True)
    parser.add_argument("--study-storage-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_manifest(args.injection_manifest)
    args.output_root.mkdir(parents=True, exist_ok=True)
    common = [
        "--clean-list", str(args.clean_list), "--manifest", str(args.manifest), "--pc", "Desktop",
        "--injection-manifest", str(args.injection_manifest),
        "--cv-injection-sets", *TRAINING_SETS,
        "--evaluation-injection-sets", *VALIDATION_SETS,
        "--workers", str(args.workers), "--initial-points", "8", "--max-iter", "72",
        "--toys-per-image", "5", "--convergence-min-trials", "40",
        "--convergence-patience", "20", "--convergence-relative-tolerance", "0.001",
        "--convergence-absolute-tolerance", "1e-5",
    ]
    sep_accepted = run([
        sys.executable, str(SCRIPT_DIR / "cross_validate_toy_objects_SEP.py"), *common,
        "--output-dir", str(args.output_root / "SEP_cross_validation"),
        "--study-storage-dir", str(args.study_storage_root / "SEP"),
        "--min-toy-detection-rate", "0.50", "--min-mean-toy-recall", "0.30",
        "--pixel-recall-weight", "0.25", "--f-score-weight", "0.30",
        "--toy-recall-weight", "0.25", "--toy-detection-weight", "0.20",
        "--data-loss-penalty", "0.50", "--false-positive-penalty", "0.25",
        "--max-masked-fraction", "0.15", "--require-final-feasible",
    ], "SEP 150%-brightness recovery-constrained 22-fold cross-validation",
       args.output_root / "SEP_cross_validation/sep_toy_cross_validation_rejected.json")
    mto_accepted = run([
        sys.executable, str(SCRIPT_DIR / "cross_validate_toy_objects_MTObjects.py"), *common,
        "--output-dir", str(args.output_root / "MTObjects_cross_validation"),
        "--study-storage-dir", str(args.study_storage_root / "MTObjects"),
        "--mtobjects-root", str(args.mtobjects_root), "--bg-variance-log", "--bg-variance-step", "0",
        "--calibrate-bg-variance", "--max-mask-exceedance-fraction", "0.20",
        "--catastrophic-masked-fraction", "0.30", "--excess-masking-penalty", "1.0",
        "--final-min-toy-detection-rate", "0.50", "--final-min-mean-toy-recall", "0.30",
    ], "MTObjects 150%-brightness 22-fold cross-validation",
       args.output_root / "MTObjects_cross_validation/mtobjects_toy_cross_validation_rejected.json")
    print(
        f"\n150%-brightness optimisation completed; SEP accepted={sep_accepted}, "
        f"MTObjects accepted={mto_accepted}; no 182-galaxy deployment was started.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
