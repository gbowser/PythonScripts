#!/usr/bin/env python3
"""Benchmark identical SEP toy-object scoring at several process counts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import statistics
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


def read_names(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def append_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--names-file", type=Path, required=True)
    parser.add_argument("--injection-manifest", type=Path, required=True)
    parser.add_argument("--params-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", nargs="+", type=int, default=[8, 12, 16])
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--pc", choices=["Desktop", "Laptop"], default="Desktop")
    args = parser.parse_args()

    names = read_names(args.names_file)
    params_payload = json.loads(args.params_json.read_text(encoding="utf-8"))
    params = params_payload.get("params", params_payload)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    case_args = SimpleNamespace(
        manifest=args.manifest,
        pc=args.pc,
        names=names,
        max_images=len(names),
        seed=202608165,
        detect_on="original",
        toys_per_image=5,
        truth_dilation=1,
        toy_peak_sigma_min=5.0,
        toy_peak_sigma_max=25.0,
        injection_manifest=args.injection_manifest,
        injection_set="cross_validation",
        injection_sets=["training_seed_1", "training_seed_2", "training_seed_3"],
    )
    build_started = time.perf_counter()
    cases = sep_opt.build_cases(case_args)
    build_seconds = time.perf_counter() - build_started
    print(f"Prepared {len(cases)} identical cases in {build_seconds:.2f}s.", flush=True)

    rows: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    reference_objective: float | None = None
    for worker_count in args.workers:
        run_dir = args.output_dir / f"workers_{worker_count}"
        run_dir.mkdir(parents=True, exist_ok=True)
        run_args = SimpleNamespace(
            output_dir=run_dir,
            workers=worker_count,
            injection_manifest=args.injection_manifest,
            injection_set="training_seed_1,training_seed_2,training_seed_3",
            max_masked_fraction=0.15,
            data_loss_penalty=0.35,
            false_positive_penalty=0.05,
        )
        run = sep_opt.OptimisationRun(run_args, cases)
        try:
            durations: list[float] = []
            objectives: list[float] = []
            total = args.warmups + args.repetitions
            for repetition in range(total):
                is_warmup = repetition < args.warmups
                started = time.perf_counter()
                objective = run.evaluate_params(params, {})
                wall_seconds = time.perf_counter() - started
                if not is_warmup:
                    durations.append(wall_seconds)
                    objectives.append(objective)
                rows.append({
                    "workers": worker_count,
                    "phase": "warmup" if is_warmup else "measured",
                    "repetition": repetition + 1,
                    "wall_seconds": f"{wall_seconds:.6f}",
                    "objective": f"{objective:.12g}",
                    "cases": len(cases),
                })
        finally:
            run.close()

        median_seconds = statistics.median(durations)
        objective = objectives[0]
        if reference_objective is None:
            reference_objective = objective
        objective_match = all(abs(value - reference_objective) <= 1e-10 for value in objectives)
        summaries.append({
            "workers": worker_count,
            "median_seconds": median_seconds,
            "minimum_seconds": min(durations),
            "maximum_seconds": max(durations),
            "objective": objective,
            "objective_matches_reference": objective_match,
            "cases": len(cases),
            "build_seconds_excluded": build_seconds,
        })
        print(
            f"workers={worker_count}: median={median_seconds:.3f}s "
            f"range={min(durations):.3f}-{max(durations):.3f}s "
            f"objective_match={objective_match}",
            flush=True,
        )

    baseline = float(summaries[0]["median_seconds"])
    for row in summaries:
        row["speedup_vs_first"] = baseline / float(row["median_seconds"])
    acceptable = [row for row in summaries if row["objective_matches_reference"]]
    winner = min(acceptable, key=lambda row: float(row["median_seconds"]))
    result = {
        "method": "SEP fixed-parameter worker-scaling benchmark",
        "names_file": str(args.names_file),
        "params_json": str(args.params_json),
        "injection_manifest": str(args.injection_manifest),
        "warmups": args.warmups,
        "repetitions": args.repetitions,
        "summaries": summaries,
        "recommended_workers": int(winner["workers"]),
    }
    append_csv(args.output_dir / "worker_scaling_trials.csv", rows)
    append_csv(args.output_dir / "worker_scaling_summary.csv", summaries)
    (args.output_dir / "worker_scaling_result.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(f"Recommended SEP workers: {winner['workers']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
