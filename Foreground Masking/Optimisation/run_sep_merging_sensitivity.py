#!/usr/bin/env python3
"""Controlled SEP experiment targeting toy/galaxy segmentation merging.

The experiment keeps the materialised Haigh-aligned injections fixed, tunes on
the three training seeds, and reports untouched validation-seed performance.
Original-image and Gaussian-residual detection are optimised as separate
studies so their results remain directly comparable.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import replace
from datetime import datetime
import json
import math
import multiprocessing as mp
from pathlib import Path
from types import SimpleNamespace
import warnings

import numpy as np
import optuna

import optimise_toy_objects_SEP as sep_opt


TRAINING_SETS = ["training_seed_1", "training_seed_2", "training_seed_3"]
VALIDATION_SETS = ["validation_seed_1", "validation_seed_2"]
_CASES: list[sep_opt.ImageCase] | None = None


def stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def initialise_worker(cases: list[sep_opt.ImageCase]) -> None:
    global _CASES
    _CASES = cases


def component_outcomes(case: sep_opt.ImageCase, products: dict[str, object], params: dict[str, object], mask: np.ndarray) -> dict[str, int]:
    raw_labels = np.asarray(products["raw_segmentation"])
    baseline = np.asarray(case.baseline_mask, dtype=bool) & np.asarray(case.analysis_region, dtype=bool)
    incremental = np.asarray(mask, dtype=bool) & np.asarray(case.analysis_region, dtype=bool) & ~baseline
    object_rows = {int(row["label"]): row for row in products["rows"]}
    counts = {key: 0 for key in ("recovered", "not_extracted", "merged_area_centre", "max_area", "protected_centre", "other_filtered", "other")}
    for toy in case.toys:
        truth = np.asarray(case.truth_labels) == int(toy.toy_id)
        pixels = max(1, int(np.count_nonzero(truth)))
        if np.count_nonzero(incremental & truth) / pixels >= 0.5:
            counts["recovered"] += 1
            continue
        labels = [int(value) for value in np.unique(raw_labels[truth]) if int(value) > 0]
        raw_recall = np.count_nonzero(raw_labels[truth] > 0) / pixels
        if raw_recall < 0.5 or not labels:
            counts["not_extracted"] += 1
            continue
        area = centre = filtered = False
        for label in labels:
            row = object_rows.get(label)
            if row is None or bool(row.get("kept", False)):
                continue
            filtered = True
            area |= int(row["area"]) > int(params["max_area"])
            centre |= float(row["distance_from_center"]) < float(params["exclude_center_pixels"])
        if area and centre:
            counts["merged_area_centre"] += 1
        elif area:
            counts["max_area"] += 1
        elif centre:
            counts["protected_centre"] += 1
        elif filtered:
            counts["other_filtered"] += 1
        else:
            counts["other"] += 1
    return counts


def score_case(task: tuple[int, dict[str, object]]) -> dict[str, object]:
    if _CASES is None:
        raise RuntimeError("SEP sensitivity worker was not initialised")
    index, params = task
    case = _CASES[index]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        products = sep_opt.sep_tool.sep_products(case.injected, params, case.geometry)
    mask = np.asarray(products["mask"], dtype=bool)
    row = dict(sep_opt.paired_toy_common.evaluate_mask(case, mask, len(products["rows"])))
    row.update(component_outcomes(case, products, params, mask))
    return row


def aggregate(rows: list[dict[str, object]]) -> dict[str, float]:
    recovered = sum(int(row["recovered_toys"]) for row in rows)
    toys = sum(int(row["toy_count"]) for row in rows)
    detection = recovered / toys if toys else 0.0
    mean_recall = float(np.mean([float(row["recall"]) for row in rows]))
    toy_recall = float(np.mean([float(row["mean_toy_recall"]) for row in rows]))
    precision = float(np.mean([float(row["precision"]) for row in rows]))
    f_score = float(np.mean([float(row["f_score"]) for row in rows]))
    mean_masked = float(np.mean([float(row["final_masked_fraction"]) for row in rows]))
    maximum_masked = float(np.max([float(row["final_masked_fraction"]) for row in rows]))
    false_positive = float(np.mean([float(row["final_false_positive_fraction"]) for row in rows]))
    galaxy_masks: dict[str, float] = {}
    for row in rows:
        name = str(row["image"])
        galaxy = name.rsplit(" [", 1)[0] if name.endswith("]") and " [" in name else name
        galaxy_masks[galaxy] = max(galaxy_masks.get(galaxy, 0.0), float(row["final_masked_fraction"]))
    above = sum(value > 0.15 for value in galaxy_masks.values())
    exceedance_fraction = above / max(1, len(galaxy_masks))
    mean_excess = float(np.mean([max(0.0, value - 0.15) for value in galaxy_masks.values()]))
    merged = sum(int(row["merged_area_centre"]) for row in rows)
    merged_rate = merged / toys if toys else 0.0
    recovery_score = 0.25 * mean_recall + 0.30 * f_score + 0.25 * toy_recall + 0.20 * detection
    data_loss = mean_masked + false_positive + mean_excess + 0.5 * merged_rate
    detection_deficit = max(0.0, 0.50 - detection)
    recall_deficit = max(0.0, 0.30 - toy_recall)
    exceedance_excess = max(0.0, exceedance_fraction - 0.20)
    catastrophic_excess = max(0.0, maximum_masked - 0.30)
    if detection_deficit or recall_deficit:
        objective = 50.0 + 20.0 * detection_deficit + 20.0 * recall_deficit + data_loss - recovery_score
    elif exceedance_excess or catastrophic_excess:
        objective = 10.0 + 100.0 * exceedance_excess + 100.0 * catastrophic_excess + data_loss - recovery_score
    else:
        objective = data_loss - recovery_score
    outcome_keys = ("recovered", "not_extracted", "merged_area_centre", "max_area", "protected_centre", "other_filtered", "other")
    return {
        "objective": objective, "toy_detection_rate": detection, "mean_toy_recall": toy_recall,
        "mean_recall": mean_recall, "mean_precision": precision, "mean_f_score": f_score,
        "mean_masked_fraction": mean_masked, "max_masked_fraction": maximum_masked,
        "false_positive_fraction": false_positive, "galaxies_above_15_percent": float(above),
        "mask_exceedance_fraction": exceedance_fraction, "merged_component_rate": merged_rate,
        **{f"toys_{key}": float(sum(int(row[key]) for row in rows)) for key in outcome_keys},
    }


def parameters(trial: optuna.Trial, detect_on: str) -> dict[str, object]:
    clean = trial.suggest_categorical("clean", [True, False])
    return {
        "detect_on": detect_on,
        "detect_thresh": trial.suggest_float("detect_thresh", 1.5, 3.0),
        "minarea": trial.suggest_int("minarea", 5, 20),
        "deblend_nthresh": trial.suggest_categorical("deblend_nthresh", [64, 128, 256]),
        "deblend_cont": trial.suggest_float("deblend_cont", 1.0e-4, 3.0e-3, log=True),
        "back_size": trial.suggest_categorical("back_size", [16, 24, 32]),
        "filter_size": trial.suggest_categorical("filter_size", [1, 3]),
        "clean": clean,
        "clean_param": trial.suggest_float("clean_param", 0.1, 1.0) if clean else 1.0,
        "dilation_radius": trial.suggest_int("dilation_radius", 1, 2),
        "max_area": 7541,
        "max_elongation": 27.314079662563053,
        "exclude_center_pixels": 8.0,
    }


def jsonable(value: object) -> object:
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    return value


def append_trial(path: Path, row: dict[str, object]) -> None:
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row), extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def evaluate(cases: list[sep_opt.ImageCase], params: dict[str, object], workers: int) -> tuple[dict[str, float], list[dict[str, object]]]:
    context = mp.get_context("fork") if "fork" in mp.get_all_start_methods() else mp.get_context("spawn")
    if workers <= 1:
        initialise_worker(cases)
        rows = [score_case((index, params)) for index in range(len(cases))]
    else:
        with context.Pool(workers, initializer=initialise_worker, initargs=(cases,)) as pool:
            rows = pool.map(score_case, [(index, params) for index in range(len(cases))])
    return aggregate(rows), rows


def make_cases(args: argparse.Namespace, sets: list[str]) -> list[sep_opt.ImageCase]:
    names = [line.strip() for line in args.clean_list.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    build_args = SimpleNamespace(
        seed=202608151, injection_sets=sets, injection_set=sets[0], manifest=args.geometry_manifest,
        pc=args.pc, names=names, max_images=min(len(names), args.max_images), detect_on="original",
        injection_manifest=args.injection_manifest, toys_per_image=5, truth_dilation=1,
        toy_peak_sigma_min=9.0, toy_peak_sigma_max=45.0,
    )
    return sep_opt.build_cases(build_args)


def run_study(args: argparse.Namespace, detect_on: str, training: list[sep_opt.ImageCase]) -> tuple[dict[str, object], dict[str, float]]:
    db = args.output_dir / f"sep_merging_{detect_on}.sqlite3"
    study = optuna.create_study(
        study_name=f"sep_merging_{detect_on}", direction="minimize",
        storage=f"sqlite:///{db}", load_if_exists=True,
        sampler=optuna.samplers.TPESampler(seed=20260901, n_startup_trials=min(20, args.trials)),
    )
    csv_path = args.output_dir / f"sep_merging_{detect_on}_trials.csv"
    remaining = max(0, args.trials - len(study.trials))
    context = mp.get_context("fork") if "fork" in mp.get_all_start_methods() else mp.get_context("spawn")
    with context.Pool(args.workers, initializer=initialise_worker, initargs=(training,)) as pool:
        def objective(trial: optuna.Trial) -> float:
            params = parameters(trial, detect_on)
            rows = pool.map(score_case, [(index, params) for index in range(len(training))])
            metrics = aggregate(rows)
            for key, value in metrics.items():
                trial.set_user_attr(key, value)
            row = {"time": stamp(), "trial": trial.number, "detect_on": detect_on, **params, **metrics}
            append_trial(csv_path, row)
            print(
                f"[{stamp()}] {detect_on} trial {trial.number + 1:03d}/{args.trials}: "
                f"objective={metrics['objective']:.4f}, detection={metrics['toy_detection_rate']:.1%}, "
                f"toy_recall={metrics['mean_toy_recall']:.1%}, merged={metrics['merged_component_rate']:.1%}, "
                f"mean/max mask={metrics['mean_masked_fraction']:.1%}/{metrics['max_masked_fraction']:.1%}",
                flush=True,
            )
            return float(metrics["objective"])
        if remaining:
            study.optimize(objective, n_trials=remaining, gc_after_trial=True, show_progress_bar=False)
    best_params = parameters(optuna.trial.FixedTrial(study.best_params), detect_on)
    best_metrics = {key: float(value) for key, value in study.best_trial.user_attrs.items() if isinstance(value, (int, float))}
    return best_params, best_metrics


def write_case_rows(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry-manifest", type=Path, required=True)
    parser.add_argument("--injection-manifest", type=Path, required=True)
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pc", default="Desktop")
    parser.add_argument("--trials", type=int, default=80, help="Trials for each detection image (original and residual).")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--max-images", type=int, default=22)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"[{stamp()}] Preparing fixed training injections...", flush=True)
    training = make_cases(args, TRAINING_SETS)
    print(f"[{stamp()}] Preparing untouched validation injections...", flush=True)
    validation = make_cases(args, VALIDATION_SETS)
    results: dict[str, object] = {"created_at": stamp(), "training_sets": TRAINING_SETS, "validation_sets": VALIDATION_SETS, "trials_per_detection_mode": args.trials}
    for mode in ("original", "residual"):
        print(f"[{stamp()}] Starting {mode} detection study.", flush=True)
        params, training_metrics = run_study(args, mode, training)
        validation_metrics, validation_rows = evaluate(validation, params, args.workers)
        all_metrics, all_rows = evaluate(training + validation, params, args.workers)
        write_case_rows(args.output_dir / f"sep_merging_{mode}_validation_cases.csv", validation_rows)
        write_case_rows(args.output_dir / f"sep_merging_{mode}_all_cases.csv", all_rows)
        results[mode] = {"params": params, "training_metrics": training_metrics, "validation_metrics": validation_metrics, "all_seed_metrics": all_metrics}
        print(
            f"[{stamp()}] {mode} validation: detection={validation_metrics['toy_detection_rate']:.1%}, "
            f"toy_recall={validation_metrics['mean_toy_recall']:.1%}, merged={validation_metrics['merged_component_rate']:.1%}, "
            f"mean/max mask={validation_metrics['mean_masked_fraction']:.1%}/{validation_metrics['max_masked_fraction']:.1%}",
            flush=True,
        )
    winner = min(("original", "residual"), key=lambda mode: float(results[mode]["validation_metrics"]["objective"]))
    results["recommended_detection_mode"] = winner
    output = args.output_dir / "sep_merging_sensitivity_result.json"
    output.write_text(json.dumps(jsonable(results), indent=2), encoding="utf-8")
    print(f"[{stamp()}] Experiment complete. Recommended mode: {winner}. Result: {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
