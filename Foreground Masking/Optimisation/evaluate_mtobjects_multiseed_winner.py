#!/usr/bin/env python3
"""Evaluate an MTObjects optimisation winner on untouched injection sets."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import evaluate_mtobjects_multiseed_robustness as robustness  # noqa: E402
import optimise_toy_objects_MTObjects as mto_opt  # noqa: E402


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    robustness.write_csv(path, rows)


def load_params(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    params = dict(payload.get("params") or json.loads(payload["parameter_set_json"]))
    if params.get("bg_mean") == "NaN":
        params["bg_mean"] = math.nan
    return params


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--best-json", type=Path, required=True)
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--injection-manifest", type=Path, required=True)
    parser.add_argument("--injection-sets", nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mtobjects-root", type=Path, required=True)
    parser.add_argument("--pc", default="Desktop")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--max-masked-fraction", type=float, default=0.15)
    parser.add_argument("--max-mask-exceedance-fraction", type=float, default=0.20)
    parser.add_argument("--catastrophic-masked-fraction", type=float, default=0.30)
    parser.add_argument("--excess-masking-penalty", type=float, default=1.0)
    parser.add_argument("--data-loss-penalty", type=float, default=0.5)
    parser.add_argument("--false-positive-penalty", type=float, default=0.1)
    parser.add_argument("--min-toy-detection-rate", type=float, default=0.50)
    parser.add_argument("--min-mean-toy-recall", type=float, default=0.30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    names = robustness.generator.read_names(args.clean_list)
    params = load_params(args.best_json)
    per_set_rows: list[dict[str, object]] = []
    all_case_rows: list[dict[str, object]] = []
    toy_rows: list[dict[str, object]] = []
    for set_name in args.injection_sets:
        build_args = SimpleNamespace(
            manifest=args.manifest,
            pc=args.pc,
            mtobjects_root=args.mtobjects_root,
            names=names,
            max_images=len(names),
            seed=0,
            detect_on="original",
            toys_per_image=5,
            truth_dilation=1,
            toy_peak_sigma_min=6.0,
            toy_peak_sigma_max=30.0,
            injection_manifest=args.injection_manifest,
            injection_set=set_name,
            injection_sets=None,
        )
        cases = mto_opt.build_cases(build_args)
        metrics, details = robustness.score_candidate(cases, params, args)
        all_case_rows.extend(details)
        per_set_rows.append({"injection_set": set_name, **metrics})
        toy_rows.extend(robustness.per_toy_rows(cases, params, set_name, 0, args))
        print(
            f"{set_name}: detection={metrics['toy_detection_rate']:.1%}, "
            f"recall={metrics['mean_toy_recall']:.1%}, max_masked={metrics['max_masked_fraction']:.1%}",
            flush=True,
        )

    pooled = mto_opt.aggregate_score(
        all_case_rows,
        max_masked_fraction=args.max_masked_fraction,
        data_loss_penalty=args.data_loss_penalty,
        false_positive_penalty=args.false_positive_penalty,
        min_toy_detection_rate=0.25,
        min_mean_toy_recall=0.20,
        max_mask_exceedance_fraction=args.max_mask_exceedance_fraction,
        catastrophic_masked_fraction=args.catastrophic_masked_fraction,
        excess_masking_penalty=args.excess_masking_penalty,
    )
    successful_cases = sum(int(row["recovered_toys"]) > 0 for row in all_case_rows)
    required_successful = math.ceil(0.80 * len(all_case_rows))
    passed = (
        float(pooled["toy_detection_rate"]) >= args.min_toy_detection_rate
        and float(pooled["mean_toy_recall"]) >= args.min_mean_toy_recall
        and bool(float(pooled["masking_feasible"]))
        and successful_cases >= required_successful
    )
    type_rows: list[dict[str, object]] = []
    for toy_type in sorted({str(row["object_type"]) for row in toy_rows}):
        selected = [row for row in toy_rows if row["object_type"] == toy_type]
        type_rows.append({
            "object_type": toy_type,
            "toys": len(selected),
            "detection_rate": sum(int(row["detected"]) for row in selected) / len(selected),
            "mean_toy_recall": sum(float(row["toy_recall"]) for row in selected) / len(selected),
        })
    write_csv(args.output_dir / "validation_by_seed.csv", per_set_rows)
    write_csv(args.output_dir / "validation_per_case.csv", all_case_rows)
    write_csv(args.output_dir / "validation_per_toy.csv", toy_rows)
    write_csv(args.output_dir / "validation_by_toy_type.csv", type_rows)
    report = {
        "status": "pass" if passed else "fail",
        "best_json": str(args.best_json),
        "injection_sets": args.injection_sets,
        "criteria": {
            "pooled_toy_detection_rate": args.min_toy_detection_rate,
            "pooled_mean_toy_recall": args.min_mean_toy_recall,
            "galaxy_masking_threshold": args.max_masked_fraction,
            "maximum_fraction_of_galaxies_above_threshold": args.max_mask_exceedance_fraction,
            "catastrophic_individual_masked_fraction": args.catastrophic_masked_fraction,
            "successful_cases": required_successful,
        },
        "pooled": pooled,
        "successful_cases": successful_cases,
        "required_successful_cases": required_successful,
        "by_toy_type": type_rows,
    }
    (args.output_dir / "mtobjects_multiseed_validation.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    print(f"Held-out validation result: {report['status'].upper()}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
