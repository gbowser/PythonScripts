#!/usr/bin/env python3
"""Evaluate a SEP CV winner (or best rejected candidate) by toy source type."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
for folder in (PROJECT_ROOT, FOREGROUND_ROOT, SCRIPT_DIR, FOREGROUND_ROOT / "Shared"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import optimise_toy_objects_SEP as sep_opt  # noqa: E402
import sep_processing  # noqa: E402


def read_names(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def params_from_result(path: Path) -> tuple[dict, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload.get("params"), dict):
        return payload["params"], "accepted_winner"
    diagnostic = payload.get("best_diagnostic_candidate") or {}
    encoded = diagnostic.get("parameter_set_json")
    if encoded:
        return json.loads(encoded), "best_rejected_candidate"
    raise ValueError(f"No usable SEP parameters in {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--injection-manifest", type=Path, required=True)
    parser.add_argument("--result-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    params, result_status = params_from_result(args.result_json)
    names = read_names(args.clean_list)
    case_args = SimpleNamespace(
        manifest=args.manifest, pc="Desktop", names=names, max_images=len(names),
        seed=202608199, detect_on="original", toys_per_image=5, truth_dilation=1,
        toy_peak_sigma_min=5.0, toy_peak_sigma_max=25.0,
        injection_manifest=args.injection_manifest,
        injection_set="winner_selection",
        injection_sets=["validation_seed_1", "validation_seed_2"],
    )
    cases = sep_opt.build_cases(case_args)
    rows: list[dict[str, object]] = []
    for case in cases:
        products = sep_processing.sep_products(case.injected, params, case.geometry)
        mask = np.asarray(products["mask"], dtype=bool) & np.asarray(case.analysis_region, dtype=bool)
        baseline = np.asarray(case.baseline_mask, dtype=bool) & np.asarray(case.analysis_region, dtype=bool)
        incremental = mask & ~baseline
        for toy in case.toys:
            truth = (np.asarray(case.truth_labels) == int(toy.toy_id)) & np.asarray(case.analysis_region, dtype=bool)
            truth_pixels = int(np.count_nonzero(truth))
            overlap = int(np.count_nonzero(incremental & truth))
            recall = overlap / truth_pixels if truth_pixels else 0.0
            rows.append({
                "image": case.name,
                "toy_id": toy.toy_id,
                "object_type": toy.object_type,
                "peak_sigma": toy.peak_sigma,
                "fwhm_pixels": toy.fwhm_pixels,
                "axis_ratio": toy.axis_ratio,
                "truth_pixels": truth_pixels,
                "overlap_pixels": overlap,
                "recall": recall,
                "detected_at_50_percent": int(recall >= 0.5),
            })

    with (args.output_dir / "sep_source_type_recovery_details.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

    groups: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        groups.setdefault(str(row["object_type"]), []).append(row)
    summary = {
        "result_status": result_status,
        "result_json": str(args.result_json),
        "params": params,
        "overall": {
            "toys": len(rows),
            "detected": sum(int(row["detected_at_50_percent"]) for row in rows),
            "detection_rate": float(np.mean([row["detected_at_50_percent"] for row in rows])),
            "mean_toy_recall": float(np.mean([row["recall"] for row in rows])),
        },
        "by_source_type": {
            key: {
                "toys": len(values),
                "detected": sum(int(row["detected_at_50_percent"]) for row in values),
                "detection_rate": float(np.mean([row["detected_at_50_percent"] for row in values])),
                "mean_toy_recall": float(np.mean([row["recall"] for row in values])),
                "median_peak_sigma": float(np.median([row["peak_sigma"] for row in values])),
                "median_fwhm_pixels": float(np.median([row["fwhm_pixels"] for row in values])),
            }
            for key, values in sorted(groups.items())
        },
    }
    (args.output_dir / "sep_source_type_recovery_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
