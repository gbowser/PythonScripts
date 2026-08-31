#!/usr/bin/env python3
"""Run 22-fold SEP and MTObjects CV on revised Haigh-aligned injections."""

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
    supported = {
        "haigh-aligned-s4g-injections-v1",
        "haigh-aligned-s4g-empty-field-injections-v2",
    }
    if manifest.get("injection_model_version") not in supported:
        raise ValueError(f"Not a supported Haigh-aligned manifest: {path}")
    available = set((manifest.get("injection_sets") or {}).keys())
    missing = set(TRAINING_SETS + VALIDATION_SETS) - available
    if missing:
        raise ValueError(f"Injection manifest is missing: {', '.join(sorted(missing))}")


def run(command: list[str], label: str) -> None:
    print(f"\n=== {label} ===", flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        raise RuntimeError(f"{label} failed with exit code {completed.returncode}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, help="182-galaxy science manifest")
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--injection-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--mtobjects-root", type=Path, required=True)
    parser.add_argument("--study-storage-root", type=Path, default=Path("/root/haigh-aligned-optuna-studies"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--initial-points", type=int, default=8)
    parser.add_argument("--max-iter", type=int, default=72, help="72 plus 8 initial = 80 maximum trials")
    parser.add_argument("--convergence-min-trials", type=int, default=40)
    parser.add_argument("--convergence-patience", type=int, default=20)
    parser.add_argument("--convergence-relative-tolerance", type=float, default=0.001)
    parser.add_argument("--convergence-absolute-tolerance", type=float, default=1.0e-5)
    parser.add_argument("--only", choices=("SEP", "MTObjects", "both"), default="both")
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
        "--workers", str(args.workers), "--initial-points", str(args.initial_points),
        "--max-iter", str(args.max_iter), "--toys-per-image", "5",
        "--convergence-min-trials", str(args.convergence_min_trials),
        "--convergence-patience", str(args.convergence_patience),
        "--convergence-relative-tolerance", str(args.convergence_relative_tolerance),
        "--convergence-absolute-tolerance", str(args.convergence_absolute_tolerance),
    ]
    if args.only in ("SEP", "both"):
        run([
            sys.executable, str(SCRIPT_DIR / "cross_validate_toy_objects_SEP.py"), *common,
            "--output-dir", str(args.output_root / "SEP_cross_validation"),
            "--study-storage-dir", str(args.study_storage_root / "SEP"),
        ], "SEP Haigh-aligned 22-fold cross-validation")
    if args.only in ("MTObjects", "both"):
        run([
            sys.executable, str(SCRIPT_DIR / "cross_validate_toy_objects_MTObjects.py"), *common,
            "--output-dir", str(args.output_root / "MTObjects_cross_validation"),
            "--study-storage-dir", str(args.study_storage_root / "MTObjects"),
            "--mtobjects-root", str(args.mtobjects_root), "--bg-variance-log", "--bg-variance-step", "0",
            "--calibrate-bg-variance", "--max-mask-exceedance-fraction", "0.20",
            "--catastrophic-masked-fraction", "0.30", "--excess-masking-penalty", "1.0",
        ], "MTObjects Haigh-aligned 22-fold cross-validation")
    print("\nRevised optimisation completed; no 182-galaxy deployment was started.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
