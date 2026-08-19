#!/usr/bin/env python3
"""Evaluate four fold winners on held-out folds and all 40 calibration galaxies."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT, ROOT / "Optimisation", ROOT / "Shared", ROOT / "Interactive tools", ROOT / "Batch tools"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))

import optimise_spike_gate_SEP as sep_opt  # noqa: E402
import optimise_spike_gate_MTObjects as mto_opt  # noqa: E402


def read_names(path: Path) -> list[str]:
    names = [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(names) != 40 or len(set(n.casefold() for n in names)) != 40:
        raise ValueError(f"Expected 40 unique names in {path}; found {len(names)}.")
    return names


def namespace_from_config(config_path: Path, names: list[str]) -> SimpleNamespace:
    values = json.loads(config_path.read_text(encoding="utf-8"))
    for key in ("manifest", "output_dir", "resume_output_dir", "results_workbook", "mtobjects_root"):
        if values.get(key) not in (None, "None", ""):
            values[key] = Path(values[key])
        else:
            values[key] = None
    values["names"] = names
    values["max_images"] = len(names)
    values["require_spikes"] = False
    values["progress_galaxies"] = False
    return SimpleNamespace(**values)


def evaluate(module, cases, params, mtobjects_root=None):
    rows = []
    for case in cases:
        if module is sep_opt:
            rows.append(module.score_case(case, params, 3))
        else:
            rows.append(module.score_case(case, params, mtobjects_root, 3))
    return rows, module.gate_objective.aggregate_constrained(rows)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    keys = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algorithm", choices=["SEP", "MTObjects"], required=True)
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--candidate-json", type=Path, nargs=4, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    names = read_names(args.clean_list)
    module = sep_opt if args.algorithm == "SEP" else mto_opt
    first_config_name = "sep_spike_optimisation_config.json" if module is sep_opt else "mtobjects_spike_optimisation_config.json"
    first_config = args.candidate_json[0].parent / first_config_name
    ns = namespace_from_config(first_config, names)
    cases = module.build_cases(ns)
    by_name = {case.name.casefold(): case for case in cases}
    candidate_rows = []
    detail_rows = []
    for fold, candidate_path in enumerate(args.candidate_json, start=1):
        payload = json.loads(candidate_path.read_text(encoding="utf-8"))
        params = payload["params"]
        held_names = names[(fold - 1) * 10 : fold * 10]
        held_cases = [by_name[name.casefold()] for name in held_names if name.casefold() in by_name]
        held_rows, held = evaluate(module, held_cases, params, getattr(ns, "mtobjects_root", None))
        all_rows, all40 = evaluate(module, cases, params, getattr(ns, "mtobjects_root", None))
        candidate_rows.append({
            "fold": fold,
            "candidate_json": str(candidate_path),
            "heldout_objective": held["objective"],
            "heldout_gate_recovery": held.get("mean_gate_recovery"),
            "heldout_candidate_detection": held.get("mean_candidate_detection_rate"),
            "heldout_masked_fraction": held.get("mean_masked_fraction"),
            "heldout_excess_mask_fraction": held.get("mean_excess_mask_fraction"),
            "heldout_protected_galaxy_loss": held.get("mean_protected_galaxy_loss"),
            "heldout_infeasible": held.get("infeasible"),
            "all40_objective": all40["objective"],
            "all40_gate_recovery": all40.get("mean_gate_recovery"),
            "all40_candidate_detection": all40.get("mean_candidate_detection_rate"),
            "all40_masked_fraction": all40.get("mean_masked_fraction"),
            "all40_excess_mask_fraction": all40.get("mean_excess_mask_fraction"),
            "all40_protected_galaxy_loss": all40.get("mean_protected_galaxy_loss"),
            "all40_infeasible": all40.get("infeasible"),
        })
        for row in held_rows:
            detail_rows.append({"fold": fold, "set": "heldout", **row})
    feasible = [row for row in candidate_rows if not float(row["heldout_infeasible"]) and not float(row["all40_infeasible"])]
    pool = feasible or candidate_rows
    winner_row = min(pool, key=lambda row: (float(row["all40_infeasible"]), float(row["all40_objective"])))
    winner_source = Path(str(winner_row["candidate_json"]))
    winner = json.loads(winner_source.read_text(encoding="utf-8"))
    winner["cross_validation"] = {
        "design": "four-fold; 30 train / 10 held out; all 40 final comparison",
        "winner_fold": int(winner_row["fold"]),
        "winner_metrics": winner_row,
        "feasible_candidate_count": len(feasible),
    }
    winner_path = args.output_dir / ("sep_spike_constrained_cv_best.json" if module is sep_opt else "mtobjects_spike_constrained_cv_best.json")
    winner_path.write_text(json.dumps(winner, indent=2), encoding="utf-8")
    write_csv(args.output_dir / "fold_candidate_comparison.csv", candidate_rows)
    write_csv(args.output_dir / "heldout_galaxy_metrics.csv", detail_rows)
    print(f"Winner: fold {winner_row['fold']} objective={winner_row['all40_objective']}", flush=True)
    print(f"Best JSON: {winner_path}", flush=True)


if __name__ == "__main__":
    main()
