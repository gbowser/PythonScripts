#!/usr/bin/env python3
"""Audit objective convergence and near-optimal parameter stability in Optuna folds."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import optuna


def normalise(value: Any, distribution) -> float:
    if isinstance(distribution, optuna.distributions.CategoricalDistribution):
        return float(distribution.choices.index(value)) / max(1, len(distribution.choices) - 1)
    low, high = float(distribution.low), float(distribution.high)
    number = float(value)
    if getattr(distribution, "log", False):
        low, high, number = math.log(low), math.log(high), math.log(number)
    return (number - low) / max(high - low, np.finfo(float).eps)


def objective_state(trials, minimum: int, patience: int, relative: float, absolute: float) -> dict:
    meaningful_best = None
    last_improvement = 0
    for position, trial in enumerate(trials, 1):
        value = float(trial.value)
        if meaningful_best is None:
            meaningful_best, last_improvement = value, position
            continue
        tolerance = max(absolute, relative * max(abs(meaningful_best), abs(value)))
        if meaningful_best - value > tolerance:
            meaningful_best, last_improvement = value, position
    stagnant = len(trials) - last_improvement
    return {
        "stable": len(trials) >= minimum and stagnant >= patience,
        "last_meaningful_improvement_trial": last_improvement,
        "stagnant_trials": stagnant,
        "meaningful_best_objective": meaningful_best,
    }


def connected_clusters(vectors: np.ndarray, threshold: float = 0.25) -> int:
    if len(vectors) < 2:
        return len(vectors)
    remaining = set(range(len(vectors)))
    clusters = 0
    while remaining:
        clusters += 1
        stack = [remaining.pop()]
        while stack:
            index = stack.pop()
            distances = np.sqrt(np.mean((vectors[list(remaining)] - vectors[index]) ** 2, axis=1)) if remaining else []
            neighbours = [candidate for candidate, distance in zip(list(remaining), distances) if distance <= threshold]
            for candidate in neighbours:
                remaining.remove(candidate)
                stack.append(candidate)
    return clusters


def rank_values(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = np.arange(len(values), dtype=float)
    for value in np.unique(values):
        mask = values == value
        ranks[mask] = np.mean(ranks[mask])
    return ranks


def audit_study(database: Path, args) -> dict | None:
    storage = f"sqlite:///{database.as_posix()}"
    summaries = optuna.get_all_study_summaries(storage=storage)
    if not summaries:
        return None
    study = optuna.load_study(study_name=summaries[0].study_name, storage=storage)
    trials = sorted(
        (trial for trial in study.trials if trial.state == optuna.trial.TrialState.COMPLETE and trial.value is not None),
        key=lambda trial: trial.number,
    )
    if not trials:
        return None
    ranked = sorted(trials, key=lambda trial: float(trial.value))
    elite_count = min(args.elite_max, max(args.elite_min, math.ceil(args.elite_fraction * len(ranked))))
    elite = ranked[: min(elite_count, len(ranked))]
    parameter_names = sorted(set.intersection(*(set(trial.params) for trial in elite))) if elite else []
    diagnostics = {}
    unstable = []
    numeric_names = []
    vectors = []
    for name in parameter_names:
        distribution = elite[0].distributions[name]
        values = [trial.params[name] for trial in elite]
        if isinstance(distribution, optuna.distributions.CategoricalDistribution):
            counts = {str(value): values.count(value) for value in set(values)}
            dominant = max(counts.values()) / len(values)
            diagnostics[name] = {"kind": "categorical", "dominant_fraction": dominant, "counts": counts}
            if dominant < args.categorical_dominance:
                unstable.append(name)
        else:
            scaled = np.asarray([normalise(value, distribution) for value in values], dtype=float)
            q25, q75 = np.percentile(scaled, [25, 75])
            iqr = float(q75 - q25)
            diagnostics[name] = {
                "kind": "numeric", "normalised_iqr": iqr,
                "normalised_range": float(np.ptp(scaled)), "median": float(np.median(np.asarray(values, dtype=float))),
            }
            numeric_names.append(name)
            if iqr > args.numeric_iqr:
                unstable.append(name)
    for trial in elite:
        vectors.append([normalise(trial.params[name], trial.distributions[name]) for name in parameter_names])
    vector_array = np.asarray(vectors, dtype=float) if vectors and parameter_names else np.empty((0, 0))
    cluster_count = connected_clusters(vector_array, args.cluster_distance) if vector_array.size else 0

    correlations = []
    for left_index, left in enumerate(numeric_names):
        left_values = rank_values(np.asarray([normalise(t.params[left], t.distributions[left]) for t in elite]))
        for right in numeric_names[left_index + 1:]:
            right_values = rank_values(np.asarray([normalise(t.params[right], t.distributions[right]) for t in elite]))
            if np.std(left_values) == 0 or np.std(right_values) == 0:
                continue
            rho = float(np.corrcoef(left_values, right_values)[0, 1])
            if abs(rho) >= args.correlation_threshold:
                correlations.append({"parameters": [left, right], "spearman_rho": rho})

    objective = objective_state(trials, args.minimum_trials, args.patience, args.relative_tolerance, args.absolute_tolerance)
    parameter_stable = not unstable and cluster_count <= 1
    if objective["stable"] and parameter_stable:
        classification = "objective_stable_parameters_stable"
    elif objective["stable"]:
        classification = "objective_stable_parameters_multimodal"
    elif parameter_stable:
        classification = "objective_improving_parameters_compact"
    else:
        classification = "objective_improving_parameters_unstable"
    method = "MTObjects" if "mtobjects" in database.name.lower() else "SEP"
    fold_text = database.stem.rsplit("-", 1)[-1]
    return {
        "method": method, "fold": int(fold_text), "study_name": study.study_name,
        "database": str(database), "completed_trials": len(trials), "best_objective": float(ranked[0].value),
        "best_trial": int(ranked[0].number) + 1, "elite_trials": len(elite),
        "objective": objective, "parameter_stable": parameter_stable,
        "cluster_count": cluster_count, "unstable_parameters": unstable,
        "parameter_diagnostics": diagnostics, "strong_parameter_correlations": correlations,
        "classification": classification, "best_params": ranked[0].params,
    }


def write_outputs(results: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = {"generated_at_utc": generated, "folds": results}
    json_path = output_dir / "optuna_parameter_stability.json"
    temp_json = json_path.with_suffix(".json.tmp")
    temp_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temp_json.replace(json_path)

    fields = ["method", "fold", "completed_trials", "best_trial", "best_objective", "elite_trials",
              "objective_stable", "stagnant_trials", "parameter_stable", "cluster_count",
              "unstable_parameters", "strong_correlations", "classification"]
    csv_path = output_dir / "optuna_parameter_stability.csv"
    temp_csv = csv_path.with_suffix(".csv.tmp")
    with temp_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in results:
            writer.writerow({
                "method": result["method"], "fold": result["fold"],
                "completed_trials": result["completed_trials"], "best_trial": result["best_trial"],
                "best_objective": result["best_objective"], "elite_trials": result["elite_trials"],
                "objective_stable": result["objective"]["stable"],
                "stagnant_trials": result["objective"]["stagnant_trials"],
                "parameter_stable": result["parameter_stable"], "cluster_count": result["cluster_count"],
                "unstable_parameters": ";".join(result["unstable_parameters"]),
                "strong_correlations": ";".join("~".join(item["parameters"]) for item in result["strong_parameter_correlations"]),
                "classification": result["classification"],
            })
    temp_csv.replace(csv_path)

    cross_rows = []
    for method in sorted({result["method"] for result in results}):
        method_results = [result for result in results if result["method"] == method]
        names = sorted(set().union(*(result["best_params"] for result in method_results)))
        for name in names:
            values = [result["best_params"].get(name) for result in method_results if name in result["best_params"]]
            if not values:
                continue
            if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
                numbers = np.asarray(values, dtype=float)
                cross_rows.append({"method": method, "parameter": name, "folds": len(values), "kind": "numeric",
                                   "median": float(np.median(numbers)), "iqr": float(np.percentile(numbers, 75) - np.percentile(numbers, 25)),
                                   "dominant_value": "", "dominant_fraction": ""})
            else:
                dominant = max(set(values), key=values.count)
                cross_rows.append({"method": method, "parameter": name, "folds": len(values), "kind": "categorical",
                                   "median": "", "iqr": "", "dominant_value": dominant,
                                   "dominant_fraction": values.count(dominant) / len(values)})
    cross_path = output_dir / "optuna_parameter_stability_across_folds.csv"
    temp_cross = cross_path.with_suffix(".csv.tmp")
    with temp_cross.open("w", newline="", encoding="utf-8") as handle:
        fields = ["method", "parameter", "folds", "kind", "median", "iqr", "dominant_value", "dominant_fraction"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(cross_rows)
    temp_cross.replace(cross_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--minimum-trials", type=int, default=40)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--relative-tolerance", type=float, default=0.001)
    parser.add_argument("--absolute-tolerance", type=float, default=1e-5)
    parser.add_argument("--elite-fraction", type=float, default=0.20)
    parser.add_argument("--elite-min", type=int, default=5)
    parser.add_argument("--elite-max", type=int, default=20)
    parser.add_argument("--numeric-iqr", type=float, default=0.15)
    parser.add_argument("--categorical-dominance", type=float, default=0.70)
    parser.add_argument("--cluster-distance", type=float, default=0.25)
    parser.add_argument("--correlation-threshold", type=float, default=0.75)
    args = parser.parse_args()
    results = [result for database in sorted(args.study_root.rglob("*.sqlite3")) if (result := audit_study(database, args))]
    write_outputs(results, args.output_dir)
    print(f"Audited {len(results)} Optuna fold studies; outputs written to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
