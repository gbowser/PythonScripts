#!/usr/bin/env python3
"""Galaxy-fold cross-validation driver for SEP Toy Objects optimisation.

For the canonical 40-galaxy sample this retains four 30/10 folds.  Other sample
sizes use leave-one-galaxy-out folds.  Fold candidates are compared on a common,
independently injected evaluation set.  The winning JSON remains compatible
with the canonical all-galaxy SEP batch tool.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import random
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

import optimise_toy_objects_SEP as sep_opt  # noqa: E402
from machine_paths import detect_pc, remove_foreground_folder  # noqa: E402


def read_names(path: Path) -> list[str]:
    names = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines()]
    names = [name for name in names if name and not name.startswith("#")]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValueError(f"Duplicate galaxy names: {', '.join(duplicates)}")
    if len(names) < 2:
        raise ValueError(f"Expected at least two unique galaxies, found {len(names)}")
    return names


def make_folds(names: list[str], seed: int) -> list[list[str]]:
    shuffled = list(names)
    random.Random(seed).shuffle(shuffled)
    fold_count = 4 if len(shuffled) == 40 else len(shuffled)
    return [sorted(shuffled[index::fold_count]) for index in range(fold_count)]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_evaluation_cases(args: argparse.Namespace, names: list[str]):
    case_args = SimpleNamespace(
        manifest=args.manifest,
        pc=args.pc,
        names=names,
        max_images=len(names),
        seed=args.evaluation_seed,
        detect_on=args.detect_on,
        toys_per_image=args.toys_per_image,
        truth_dilation=args.truth_dilation,
        toy_peak_sigma_min=args.toy_peak_sigma_min,
        toy_peak_sigma_max=args.toy_peak_sigma_max,
        injection_manifest=args.injection_manifest,
        injection_set=args.evaluation_injection_set,
    )
    return sep_opt.build_cases(case_args)


def score_cases(cases, params: dict[str, object], args: argparse.Namespace) -> tuple[dict[str, float], list[dict[str, object]]]:
    detail = [sep_opt.score_case(case, params) for case in cases]
    aggregate = sep_opt.aggregate_score(
        detail,
        max_masked_fraction=args.max_masked_fraction,
        data_loss_penalty=args.data_loss_penalty,
        false_positive_penalty=args.false_positive_penalty,
    )
    return aggregate, detail


def run_fold(args: argparse.Namespace, root: Path, fold_number: int, fold_count: int, training: list[str], held_out: list[str]) -> Path:
    fold_dir = root / f"fold_{fold_number}"
    optimiser_parent = fold_dir / "training_optimisation"
    fold_dir.mkdir(parents=True, exist_ok=True)
    (fold_dir / "training_names.txt").write_text("\n".join(training) + "\n", encoding="utf-8")
    (fold_dir / "held_out_names.txt").write_text("\n".join(held_out) + "\n", encoding="utf-8")
    existing = sorted(optimiser_parent.glob("*/sep_toy_object_optimisation_best.json"), key=lambda p: p.stat().st_mtime)
    required_trials = int(args.initial_points) + int(args.max_iter)
    if existing:
        summary_path = existing[-1].with_name("sep_toy_object_optimisation_summary.csv")
        completed_trials = 0
        if summary_path.exists():
            with summary_path.open(newline="", encoding="utf-8") as handle:
                completed_trials = sum(1 for _row in csv.DictReader(handle))
        if completed_trials >= required_trials:
            print(
                f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Reusing completed fold {fold_number}/{fold_count} "
                f"({completed_trials} trials): {existing[-1]}",
                flush=True,
            )
            return existing[-1]
    command = [
        sys.executable,
        str(SCRIPT_DIR / "optimise_toy_objects_SEP.py"),
        "--manifest", str(args.manifest),
        "--pc", args.pc,
        "--output-dir", str(optimiser_parent),
        "--names", *training,
        "--max-images", str(len(training)),
        "--toys-per-image", str(args.toys_per_image),
        "--truth-dilation", str(args.truth_dilation),
        "--toy-peak-sigma-min", str(args.toy_peak_sigma_min),
        "--toy-peak-sigma-max", str(args.toy_peak_sigma_max),
        "--injection-manifest", str(args.injection_manifest),
        "--injection-set", args.cv_injection_set,
        "--detect-on", args.detect_on,
        "--initial-points", str(args.initial_points),
        "--max-iter", str(args.max_iter),
        "--workers", str(args.workers),
        "--seed", str(args.seed + fold_number),
        "--study-name", f"sep-toy-cv-fold-{fold_number}",
        "--study-storage-dir", str(args.study_storage_dir),
        "--max-masked-fraction", str(args.max_masked_fraction),
        "--data-loss-penalty", str(args.data_loss_penalty),
        "--false-positive-penalty", str(args.false_positive_penalty),
    ]
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Starting fold {fold_number}/{fold_count}: train={len(training)}, validate={len(held_out)}", flush=True)
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        raise RuntimeError(f"Fold {fold_number} optimiser failed with exit code {completed.returncode}")
    run_dirs = sorted(optimiser_parent.glob("*/sep_toy_object_optimisation_best.json"), key=lambda p: p.stat().st_mtime)
    if not run_dirs:
        raise FileNotFoundError(f"Fold {fold_number} did not produce a best-parameter JSON")
    return run_dirs[-1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    try:
        default_pc = detect_pc(SCRIPT_DIR)
    except RuntimeError:
        default_pc = "Desktop"
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=sep_opt.sep_tool.DEFAULT_MANIFEST)
    parser.add_argument("--pc", choices=["Desktop", "Laptop"], default=default_pc)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--study-storage-dir", type=Path, default=Path("/tmp/sep-toy-cv-optuna"))
    parser.add_argument("--fold-seed", type=int, default=202608150)
    parser.add_argument("--seed", type=int, default=202608151)
    parser.add_argument("--evaluation-seed", type=int, default=202608199)
    parser.add_argument("--initial-points", type=int, default=8)
    parser.add_argument("--max-iter", type=int, default=32)
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--toys-per-image", type=int, default=6)
    parser.add_argument("--truth-dilation", type=int, default=1)
    parser.add_argument("--toy-peak-sigma-min", type=float, default=5.0)
    parser.add_argument("--toy-peak-sigma-max", type=float, default=25.0)
    parser.add_argument("--injection-manifest", type=Path, required=True)
    parser.add_argument("--cv-injection-set", default="cross_validation")
    parser.add_argument("--evaluation-injection-set", default="winner_selection")
    parser.add_argument(
        "--detect-on",
        choices=["original"],
        default="original",
        help="SEP detection image; constrained to the original science image.",
    )
    parser.add_argument("--max-masked-fraction", type=float, default=sep_opt.DEFAULT_MAX_MASKED_FRACTION)
    parser.add_argument("--data-loss-penalty", type=float, default=sep_opt.DEFAULT_DATA_LOSS_PENALTY)
    parser.add_argument("--false-positive-penalty", type=float, default=sep_opt.DEFAULT_FALSE_POSITIVE_PENALTY)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    names = read_names(args.clean_list)
    folds = make_folds(names, args.fold_seed)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    root = args.output_dir or (remove_foreground_folder(args.pc) / "sep toy cross validation" / timestamp)
    root.mkdir(parents=True, exist_ok=True)
    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    config["parameter_bounds"] = sep_opt.PARAMETER_BOUNDS
    config["folds"] = {f"fold_{i + 1}": fold for i, fold in enumerate(folds)}
    (root / "cross_validation_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"Cross-validation output: {root}", flush=True)

    evaluation_cases = build_evaluation_cases(args, names)
    cases_by_name = {case.name: case for case in evaluation_cases}
    candidate_rows: list[dict[str, object]] = []
    detail_rows: list[dict[str, object]] = []
    result_metadata = {"algorithm": "SEP", **sep_opt.paired_toy_common.runtime_metadata(PROJECT_ROOT), "worker_count": args.workers, "injection_manifest": str(args.injection_manifest)}
    started = time.perf_counter()
    fold_count = len(folds)
    sample_label = f"all{len(names)}"
    for index, held_out in enumerate(folds, start=1):
        training = sorted(set(names) - set(held_out))
        best_path = run_fold(args, root, index, fold_count, training, held_out)
        best = json.loads(best_path.read_text(encoding="utf-8"))
        params = best["params"]
        held_cases = [cases_by_name[name] for name in held_out]
        held_metrics, held_detail = score_cases(held_cases, params, args)
        all_metrics, _ = score_cases(evaluation_cases, params, args)
        row = {
            "fold": index,
            **result_metadata,
            "parameter_set_json": json.dumps(params, sort_keys=True),
            "best_json": str(best_path),
            "training_objective": best.get("objective"),
            **{f"held_out_{key}": value for key, value in held_metrics.items()},
            **{f"{sample_label}_{key}": value for key, value in all_metrics.items()},
        }
        candidate_rows.append(row)
        detail_rows.extend({"fold": index, **result_metadata, "injection_set": args.evaluation_injection_set, "parameter_set_json": json.dumps(params, sort_keys=True), **detail} for detail in held_detail)
        elapsed = time.perf_counter() - started
        eta = elapsed / index * (fold_count - index)
        print(
            f"Fold {index}/{fold_count} complete: held_out_score={held_metrics['score']:.4f}, "
            f"{sample_label}_score={all_metrics['score']:.4f}, remaining_eta={sep_opt.format_duration(eta)}",
            flush=True,
        )
        write_csv(root / "cross_validation_candidates.csv", candidate_rows)
        write_csv(root / "held_out_details.csv", detail_rows)

    winner = min(candidate_rows, key=lambda row: float(row[f"{sample_label}_objective"]))
    source = json.loads(Path(str(winner["best_json"])).read_text(encoding="utf-8"))
    final = {
        **source,
        "selection_method": f"{fold_count}-fold galaxy CV; winner selected on common independent {len(names)}-galaxy injection set",
        "winning_fold": int(winner["fold"]),
        "cross_validation_metrics": winner,
        "cross_validation_root": str(root),
    }
    winner_path = root / "sep_toy_cross_validation_best.json"
    winner_path.write_text(json.dumps(final, indent=2), encoding="utf-8")
    print(f"Cross-validation winner: fold {winner['fold']} -> {winner_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
