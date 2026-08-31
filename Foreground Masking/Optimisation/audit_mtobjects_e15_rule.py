#!/usr/bin/env python3
"""Re-score stored MTObjects trials using the galaxy-level E15 masking rule."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import optimise_toy_objects_MTObjects as mto  # noqa: E402


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--details", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    details_by_eval: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in read_csv(args.details):
        evaluation = int(row["evaluation"])
        converted: dict[str, object] = dict(row)
        for key in (
            "recall", "precision", "f_score", "mean_toy_recall", "masked_fraction",
            "false_positive_fraction",
        ):
            converted[key] = float(row[key])
        for key in ("recovered_toys", "toy_count", "incremental_pixels"):
            converted[key] = int(float(row[key]))
        details_by_eval[evaluation].append(converted)

    old_summary = {int(row["evaluation"]): row for row in read_csv(args.summary)}
    rows: list[dict[str, object]] = []
    for evaluation, case_rows in sorted(details_by_eval.items()):
        aggregate = mto.aggregate_score(
            case_rows,
            max_masked_fraction=0.15,
            data_loss_penalty=0.5,
            false_positive_penalty=0.1,
            min_toy_detection_rate=0.25,
            min_mean_toy_recall=0.20,
            max_mask_exceedance_fraction=0.20,
            catastrophic_masked_fraction=0.30,
            excess_masking_penalty=1.0,
        )
        old = old_summary.get(evaluation, {})
        old_max = float(old.get("max_masked_fraction") or aggregate["max_masked_fraction"])
        old_recovery_feasible = not bool(float(aggregate["recovery_infeasible"]))
        rows.append({
            "evaluation": evaluation,
            "trial_number": old.get("trial_number", ""),
            "old_objective": old.get("objective", ""),
            "new_objective": aggregate["objective"],
            "toy_detection_rate": aggregate["toy_detection_rate"],
            "mean_toy_recall": aggregate["mean_toy_recall"],
            "mean_masked_fraction": aggregate["mean_masked_fraction"],
            "maximum_masked_fraction": aggregate["max_masked_fraction"],
            "galaxies_above_15_percent": int(aggregate["galaxies_above_masking_cap"]),
            "galaxies_evaluated": int(aggregate["galaxies_evaluated_for_masking"]),
            "E15": aggregate["mask_exceedance_fraction"],
            "mean_excess_above_15_percent": aggregate["mean_excess_above_masking_cap"],
            "old_mask_rule_pass": old_max <= 0.15,
            "new_mask_rule_pass": bool(aggregate["masking_feasible"]),
            "recovery_rule_pass": old_recovery_feasible,
            "new_fully_feasible": old_recovery_feasible and bool(aggregate["masking_feasible"]),
            "parameter_set_json": old.get("parameter_set_json", ""),
        })

    feasible = [row for row in rows if row["new_fully_feasible"]]
    newly_admitted = [row for row in rows if row["new_fully_feasible"] and not row["old_mask_rule_pass"]]
    best = min(feasible, key=lambda row: float(row["new_objective"])) if feasible else None
    report = {
        "stored_trials": len(rows),
        "old_mask_rule_passes": sum(bool(row["old_mask_rule_pass"]) for row in rows),
        "new_mask_rule_passes": sum(bool(row["new_mask_rule_pass"]) for row in rows),
        "new_fully_feasible_trials": len(feasible),
        "newly_admitted_fully_feasible_trials": len(newly_admitted),
        "rule": {
            "galaxy_threshold": 0.15,
            "maximum_E15": 0.20,
            "catastrophic_ceiling": 0.30,
            "galaxy_seed_aggregation": "worst seed per galaxy",
        },
        "best_new_trial": best,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "e15_trial_rescoring.csv", rows)
    (args.output_dir / "e15_trial_rescoring.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if best is not None:
        best_payload = {
            "selection_method": "retrospective E15 re-scoring of stored MTObjects trials",
            "evaluation": best["evaluation"],
            "trial_number": best["trial_number"],
            "objective": best["new_objective"],
            "params": json.loads(str(best["parameter_set_json"])),
            "metrics": {key: value for key, value in best.items() if key != "parameter_set_json"},
        }
        (args.output_dir / "e15_best_candidate.json").write_text(
            json.dumps(best_payload, indent=2), encoding="utf-8"
        )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
