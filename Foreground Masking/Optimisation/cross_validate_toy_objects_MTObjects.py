#!/usr/bin/env python3
"""Four-fold cross-validation driver for MTObjects Toy Objects optimisation."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
import multiprocessing as mp
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
for path in (PROJECT_ROOT, FOREGROUND_ROOT, SCRIPT_DIR, FOREGROUND_ROOT / "Shared"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import cross_validate_toy_objects_SEP as cv_common  # noqa: E402
import optimise_toy_objects_MTObjects as mto_opt  # noqa: E402
from machine_paths import detect_pc, remove_foreground_folder  # noqa: E402


def build_evaluation_cases(args: argparse.Namespace, names: list[str]):
    case_args = SimpleNamespace(
        manifest=args.manifest,
        pc=args.pc,
        mtobjects_root=args.mtobjects_root,
        names=names,
        max_images=len(names),
        seed=args.evaluation_seed,
        detect_on=args.detect_on,
        toys_per_image=args.toys_per_image,
        truth_dilation=args.truth_dilation,
    )
    return mto_opt.build_cases(case_args)


def score_cases(cases, params: dict[str, object], args: argparse.Namespace) -> tuple[dict[str, float], list[dict[str, object]]]:
    root = mto_opt.mto.find_mtobjects_root(args.mtobjects_root)
    worker_count = min(max(1, int(args.workers)), len(cases))
    if worker_count == 1:
        detail = [mto_opt.score_case(case, params, root) for case in cases]
    else:
        context = mp.get_context("spawn")
        with context.Pool(
            processes=worker_count,
            initializer=mto_opt.initialise_score_worker,
            initargs=(cases, root),
        ) as pool:
            detail = pool.map(mto_opt.score_case_worker, [(index, params) for index in range(len(cases))])
    aggregate = mto_opt.aggregate_score(
        detail,
        max_masked_fraction=args.max_masked_fraction,
        data_loss_penalty=args.data_loss_penalty,
        false_positive_penalty=args.false_positive_penalty,
        min_toy_detection_rate=args.min_toy_detection_rate,
        min_mean_toy_recall=args.min_mean_toy_recall,
    )
    return aggregate, detail


def calibrate_bg_variance(cases, args: argparse.Namespace, root: Path) -> None:
    grid = [1.0e-4, 1.0e-3, 1.0e-2, 1.0e-1, 1.0, 10.0, 100.0, 1000.0, 3000.0, 6000.0, 10000.0]
    rows: list[dict[str, object]] = []
    calibration_path = root / "bg_variance_calibration.csv"
    if calibration_path.exists():
        with calibration_path.open(newline="", encoding="utf-8") as handle:
            cached = list(csv.DictReader(handle))
        cached_values = [float(row["bg_variance"]) for row in cached]
        if cached_values == grid:
            rows = [{key: float(value) for key, value in row.items()} for row in cached]
            print("Reusing completed bg_variance calibration (11/11 points).", flush=True)

    if not rows:
        print("Calibrating bg_variance on the common 40-galaxy injection set...", flush=True)
        for index, value in enumerate(grid, start=1):
            params = mto_opt.default_params(args.detect_on)
            params.update(
                move_factor=1.0,
                min_distance=0.0,
                gaussian_fwhm=2.0,
                bg_variance=value,
                minarea=1,
                dilation_radius=2,
                max_area=3000,
                max_elongation=15.0,
            )
            metrics, _ = score_cases(cases, params, args)
            row = {"bg_variance": value, **metrics}
            rows.append(row)
            print(
                f"  calibration {index:02d}/{len(grid)}: bg_variance={value:g}, "
                f"detection={metrics['toy_detection_rate']:.1%}, recall={metrics['mean_toy_recall']:.1%}, "
                f"max_masked={metrics['max_masked_fraction']:.1%}",
                flush=True,
            )
            cv_common.write_csv(calibration_path, rows)

    viable_indices = [
        index for index, row in enumerate(rows)
        if float(row["toy_detection_rate"]) >= args.min_toy_detection_rate
        and float(row["mean_toy_recall"]) >= args.min_mean_toy_recall
        and float(row["max_masked_fraction"]) <= args.max_masked_fraction
    ]
    if not viable_indices:
        detectable = [index for index, row in enumerate(rows) if float(row["toy_detection_rate"]) > 0.0]
        if not detectable:
            raise RuntimeError("bg_variance calibration found no toy detections at any tested scale; optimisation was not started")
        best_index = max(detectable, key=lambda i: float(rows[i]["recovery_score"]))
        viable_indices = [best_index]
        print("Warning: calibration did not meet both recovery gates; using the best non-zero recovery neighbourhood.", flush=True)

    lower_index = max(0, min(viable_indices) - 1)
    upper_index = min(len(grid) - 1, max(viable_indices) + 1)
    args.bg_variance_min = grid[lower_index]
    args.bg_variance_max = grid[upper_index]
    args.bg_variance_step = 0.0
    args.bg_variance_log = True
    print(f"Calibrated search range: {args.bg_variance_min:g} to {args.bg_variance_max:g} (log scale).", flush=True)


def run_fold(args: argparse.Namespace, root: Path, fold_number: int, training: list[str], held_out: list[str]) -> Path:
    fold_dir = root / f"fold_{fold_number}"
    optimiser_parent = fold_dir / "training_optimisation"
    fold_dir.mkdir(parents=True, exist_ok=True)
    (fold_dir / "training_names.txt").write_text("\n".join(training) + "\n", encoding="utf-8")
    (fold_dir / "held_out_names.txt").write_text("\n".join(held_out) + "\n", encoding="utf-8")
    existing = sorted(optimiser_parent.glob("*/mtobjects_parameter_optimisation_best.json"), key=lambda p: p.stat().st_mtime)
    required_trials = int(args.initial_points) + int(args.max_iter)
    if existing:
        summary = existing[-1].with_name("mtobjects_parameter_optimisation_summary.csv")
        completed = 0
        if summary.exists():
            with summary.open(newline="", encoding="utf-8") as handle:
                completed = sum(1 for _row in csv.DictReader(handle))
        if completed >= required_trials:
            print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Reusing completed fold {fold_number}/4 ({completed} trials).", flush=True)
            return existing[-1]

    command = [
        sys.executable,
        str(SCRIPT_DIR / "optimise_toy_objects_MTObjects.py"),
        "--manifest", str(args.manifest),
        "--pc", args.pc,
        "--mtobjects-root", str(args.mtobjects_root),
        "--output-dir", str(optimiser_parent),
        "--names", *training,
        "--max-images", str(len(training)),
        "--toys-per-image", str(args.toys_per_image),
        "--truth-dilation", str(args.truth_dilation),
        "--mtobjects-detect-on", args.detect_on,
        "--initial-points", str(args.initial_points),
        "--max-iter", str(args.max_iter),
        "--workers", str(args.workers),
        "--seed", str(args.seed + fold_number),
        "--study-name", f"mtobjects-toy-cv-fold-{fold_number}",
        "--bg-variance-min", str(args.bg_variance_min),
        "--bg-variance-max", str(args.bg_variance_max),
        "--bg-variance-step", str(args.bg_variance_step),
        "--bg-variance-log" if args.bg_variance_log else "--no-bg-variance-log",
        "--max-masked-fraction", str(args.max_masked_fraction),
        "--data-loss-penalty", str(args.data_loss_penalty),
        "--false-positive-penalty", str(args.false_positive_penalty),
        "--min-toy-detection-rate", str(args.min_toy_detection_rate),
        "--min-mean-toy-recall", str(args.min_mean_toy_recall),
    ]
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Starting MTObjects fold {fold_number}/4: train=30, validate=10", flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        raise RuntimeError(f"MTObjects fold {fold_number} failed with exit code {completed.returncode}")
    outputs = sorted(optimiser_parent.glob("*/mtobjects_parameter_optimisation_best.json"), key=lambda p: p.stat().st_mtime)
    if not outputs:
        raise FileNotFoundError(f"MTObjects fold {fold_number} did not produce a best JSON")
    return outputs[-1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    try:
        default_pc = detect_pc(SCRIPT_DIR)
    except RuntimeError:
        default_pc = "Desktop"
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=mto_opt.mto.DEFAULT_MANIFEST)
    parser.add_argument("--pc", choices=["Desktop", "Laptop"], default=default_pc)
    parser.add_argument("--mtobjects-root", type=Path, default=PROJECT_ROOT / "mtobjects")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--fold-seed", type=int, default=202608150)
    parser.add_argument("--seed", type=int, default=202608251)
    parser.add_argument("--evaluation-seed", type=int, default=202608299)
    parser.add_argument("--initial-points", type=int, default=8)
    parser.add_argument("--max-iter", type=int, default=32)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--toys-per-image", type=int, default=6)
    parser.add_argument("--truth-dilation", type=int, default=1)
    parser.add_argument("--detect-on", choices=["original", "residual"], default="original")
    parser.add_argument("--bg-variance-min", type=float, default=mto_opt.DEFAULT_BG_VARIANCE_MIN)
    parser.add_argument("--bg-variance-max", type=float, default=mto_opt.DEFAULT_BG_VARIANCE_MAX)
    parser.add_argument("--bg-variance-step", type=float, default=mto_opt.DEFAULT_BG_VARIANCE_STEP)
    parser.add_argument("--bg-variance-log", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--calibrate-bg-variance", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-masked-fraction", type=float, default=mto_opt.DEFAULT_MAX_MASKED_FRACTION)
    parser.add_argument("--data-loss-penalty", type=float, default=mto_opt.DEFAULT_DATA_LOSS_PENALTY)
    parser.add_argument("--false-positive-penalty", type=float, default=mto_opt.DEFAULT_FALSE_POSITIVE_PENALTY)
    parser.add_argument("--min-toy-detection-rate", type=float, default=mto_opt.DEFAULT_MIN_TOY_DETECTION_RATE)
    parser.add_argument("--min-mean-toy-recall", type=float, default=mto_opt.DEFAULT_MIN_MEAN_TOY_RECALL)
    parser.add_argument("--final-min-toy-detection-rate", type=float, default=0.50)
    parser.add_argument("--final-min-mean-toy-recall", type=float, default=0.30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    names = cv_common.read_names(args.clean_list)
    folds = cv_common.make_folds(names, args.fold_seed)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    root = args.output_dir or (remove_foreground_folder(args.pc) / "mtobjects toy cross validation" / stamp)
    root.mkdir(parents=True, exist_ok=True)
    print(f"MTObjects cross-validation output: {root}", flush=True)

    evaluation_cases = build_evaluation_cases(args, names)
    if args.calibrate_bg_variance:
        calibrate_bg_variance(evaluation_cases, args, root)
    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    config["parameter_bounds"] = mto_opt.PARAMETER_BOUNDS
    config["folds"] = {f"fold_{i + 1}": fold for i, fold in enumerate(folds)}
    (root / "cross_validation_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    cases_by_name = {case.name: case for case in evaluation_cases}
    candidates: list[dict[str, object]] = []
    details: list[dict[str, object]] = []
    started = time.perf_counter()
    for index, held_out in enumerate(folds, start=1):
        training = sorted(set(names) - set(held_out))
        best_path = run_fold(args, root, index, training, held_out)
        best = json.loads(best_path.read_text(encoding="utf-8"))
        params = best["params"]
        held_metrics, held_detail = score_cases([cases_by_name[name] for name in held_out], params, args)
        all_metrics, _ = score_cases(evaluation_cases, params, args)
        fold_metrics = [score_cases([cases_by_name[name] for name in fold], params, args)[0] for fold in folds]
        min_fold_detection = min(float(metrics["toy_detection_rate"]) for metrics in fold_metrics)
        min_fold_recall = min(float(metrics["mean_toy_recall"]) for metrics in fold_metrics)
        max_fold_masked = max(float(metrics["max_masked_fraction"]) for metrics in fold_metrics)
        feasible = (
            float(all_metrics["toy_detection_rate"]) >= args.final_min_toy_detection_rate
            and float(all_metrics["mean_toy_recall"]) >= args.final_min_mean_toy_recall
            and float(all_metrics["max_masked_fraction"]) <= args.max_masked_fraction
            and min_fold_detection > 0.0
            and min_fold_recall > 0.0
        )
        row = {
            "fold": index,
            "best_json": str(best_path),
            "training_objective": best.get("objective"),
            "candidate_feasible": int(feasible),
            "min_fold_toy_detection_rate": min_fold_detection,
            "min_fold_mean_toy_recall": min_fold_recall,
            "max_fold_masked_fraction": max_fold_masked,
            **{f"held_out_{key}": value for key, value in held_metrics.items()},
            **{f"all40_{key}": value for key, value in all_metrics.items()},
        }
        candidates.append(row)
        details.extend({"fold": index, **detail} for detail in held_detail)
        eta = (time.perf_counter() - started) / index * (4 - index)
        print(
            f"MTObjects fold {index}/4 complete: held_out_score={held_metrics['score']:.4f}, "
            f"all40_score={all_metrics['score']:.4f}, remaining_eta={mto_opt.format_duration(eta)}",
            flush=True,
        )
        cv_common.write_csv(root / "cross_validation_candidates.csv", candidates)
        cv_common.write_csv(root / "held_out_details.csv", details)

    feasible_candidates = [row for row in candidates if int(row["candidate_feasible"]) == 1]
    if not feasible_candidates:
        rejection = {
            "status": "rejected",
            "reason": "No candidate met the final all-40 recovery thresholds and non-zero recovery in every fold.",
            "required_toy_detection_rate": args.final_min_toy_detection_rate,
            "required_mean_toy_recall": args.final_min_mean_toy_recall,
            "required_max_masked_fraction": args.max_masked_fraction,
            "candidates": candidates,
        }
        (root / "mtobjects_toy_cross_validation_rejected.json").write_text(json.dumps(rejection, indent=2), encoding="utf-8")
        raise RuntimeError(rejection["reason"])
    winner = min(feasible_candidates, key=lambda row: float(row["all40_objective"]))
    source = json.loads(Path(str(winner["best_json"])).read_text(encoding="utf-8"))
    final = {
        **source,
        "selection_method": "four-fold-30-train-10-held-out; winner selected on common independent 40-galaxy injection set",
        "winning_fold": int(winner["fold"]),
        "cross_validation_metrics": winner,
        "cross_validation_root": str(root),
    }
    winner_path = root / "mtobjects_toy_cross_validation_best.json"
    winner_path.write_text(json.dumps(final, indent=2), encoding="utf-8")
    print(f"MTObjects cross-validation winner: fold {winner['fold']} -> {winner_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
