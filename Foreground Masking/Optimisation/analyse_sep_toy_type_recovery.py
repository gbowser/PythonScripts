#!/usr/bin/env python3
"""Report SEP recovery separately for saved stars and Sersic galaxies."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from types import SimpleNamespace
import warnings

import numpy as np

import optimise_toy_objects_SEP as sep_opt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry-manifest", type=Path, required=True)
    parser.add_argument("--injection-manifest", type=Path, required=True)
    parser.add_argument("--candidate-json", type=Path, required=True)
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case-output", type=Path,
                        help="Optional per-galaxy/seed metrics using the common paired-toy evaluator.")
    parser.add_argument("--pc", default="Desktop")
    args = parser.parse_args()

    names = [line.strip() for line in args.clean_list.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    build_args = SimpleNamespace(
        seed=202608151,
        injection_sets=["training_seed_1", "training_seed_2", "training_seed_3", "validation_seed_1", "validation_seed_2"],
        injection_set="training_seed_1",
        manifest=args.geometry_manifest,
        pc=args.pc,
        names=names,
        max_images=len(names),
        detect_on="original",
        injection_manifest=args.injection_manifest,
        toys_per_image=5,
        truth_dilation=1,
        toy_peak_sigma_min=9.0,
        toy_peak_sigma_max=45.0,
    )
    candidate = json.loads(args.candidate_json.read_text(encoding="utf-8-sig"))
    params = candidate.get("params") or json.loads(candidate["parameter_set_json"])
    injection_catalogue = json.loads(args.injection_manifest.read_text(encoding="utf-8-sig"))["injection_sets"]
    cases = sep_opt.build_cases(build_args)

    rows: list[dict[str, object]] = []
    case_rows: list[dict[str, object]] = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for case in cases:
            galaxy_name, set_suffix = case.name.split(" [", 1)
            set_name = set_suffix.rstrip("]")
            source_metadata = {
                int(item["toy_id"]): item
                for item in injection_catalogue[set_name]["galaxies"][galaxy_name]["toys"]
            }
            products = sep_opt.sep_tool.sep_products(case.injected, params, case.geometry)
            case_row = dict(sep_opt.paired_toy_common.evaluate_mask(case, products["mask"], len(products["rows"])))
            case_row.update({"parameter_source": str(args.candidate_json), "injection_set": set_name})
            case_rows.append(case_row)
            mask = np.asarray(products["mask"], dtype=bool) & np.asarray(case.analysis_region, dtype=bool)
            baseline = np.asarray(case.baseline_mask, dtype=bool) & np.asarray(case.analysis_region, dtype=bool)
            incremental = mask & ~baseline
            raw = np.asarray(products["raw_segmentation"]) > 0
            filtered = np.asarray(products["filtered_segmentation"]) > 0
            region = np.asarray(case.analysis_region, dtype=bool)
            yy, xx = np.indices(case.data.shape, dtype=float)
            xc = float(case.geometry["xc"]) - 1.0
            yc = float(case.geometry["yc"]) - 1.0
            equivalent_radius = np.sqrt(max(1, np.count_nonzero(region)) / np.pi)
            outer = region & (np.hypot(xx - xc, yy - yc) >= 0.58 * equivalent_radius)
            sample = np.asarray(case.data)[outer & np.isfinite(case.data)]
            global_median = float(np.median(sample)) if sample.size else 0.0
            mad = float(np.median(np.abs(sample - global_median))) if sample.size else 0.0
            global_sigma = max(1e-12, 1.4826 * mad)
            for toy in case.toys:
                metadata = source_metadata[int(toy.toy_id)]
                truth = np.asarray(case.truth_labels) == int(toy.toy_id)
                pixels = int(np.count_nonzero(truth))
                overlap = int(np.count_nonzero(incremental & truth))
                recall = overlap / pixels if pixels else 0.0
                raw_recall = int(np.count_nonzero(raw & truth)) / pixels if pixels else 0.0
                filtered_recall = int(np.count_nonzero(filtered & truth)) / pixels if pixels else 0.0
                final_recall = int(np.count_nonzero(mask & truth)) / pixels if pixels else 0.0
                x = int(round(float(toy.x)))
                y = int(round(float(toy.y)))
                y0, y1 = max(0, y - 4), min(case.data.shape[0], y + 5)
                x0, x1 = max(0, x - 4), min(case.data.shape[1], x + 5)
                local = np.asarray(case.data)[y0:y1, x0:x1]
                local = local[np.isfinite(local)]
                local_median = float(np.median(local)) if local.size else global_median
                labels, counts = np.unique(np.asarray(products["raw_segmentation"])[truth], return_counts=True)
                labels = labels[labels > 0]
                rejection_reasons: set[str] = set()
                for label in labels:
                    row = next((item for item in products["rows"] if int(item["label"]) == int(label)), None)
                    if row is None or bool(row["kept"]):
                        continue
                    if int(row["area"]) > int(params["max_area"]):
                        rejection_reasons.add("max_area")
                    if float(row["elongation"]) > float(params["max_elongation"]):
                        rejection_reasons.add("max_elongation")
                    if float(row["distance_from_center"]) < float(params["exclude_center_pixels"]):
                        rejection_reasons.add("protected_centre")
                if recall >= 0.5:
                    failure_mode = "recovered"
                elif raw_recall < 0.5:
                    failure_mode = "not_extracted_or_undersegmented"
                elif filtered_recall < 0.5:
                    failure_mode = "filtered:" + ("+".join(sorted(rejection_reasons)) or "component_filter")
                elif final_recall >= 0.5:
                    failure_mode = "baseline_overlap_removed_increment"
                else:
                    failure_mode = "dilation_or_edge_effect"
                rows.append({
                    "case": case.name,
                    "toy_id": toy.toy_id,
                    "object_type": toy.object_type,
                    "peak_sigma": toy.peak_sigma,
                    "fwhm_pixels": toy.fwhm_pixels,
                    "effective_radius_arcsec": metadata.get("effective_radius_arcsec"),
                    "sersic_index": metadata.get("sersic_index"),
                    "axis_ratio": getattr(toy, "axis_ratio", None),
                    "distance_normalised": float(np.hypot(float(toy.x) - xc, float(toy.y) - yc) / equivalent_radius),
                    "local_background_z": (local_median - global_median) / global_sigma,
                    "truth_pixels": pixels,
                    "overlap_pixels": overlap,
                    "raw_recall": raw_recall,
                    "filtered_recall": filtered_recall,
                    "final_recall": final_recall,
                    "recall": recall,
                    "detected": int(recall >= 0.5),
                    "failure_mode": failure_mode,
                })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if args.case_output:
        args.case_output.parent.mkdir(parents=True, exist_ok=True)
        with args.case_output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(case_rows[0]))
            writer.writeheader()
            writer.writerows(case_rows)

    for object_type in ("star", "galaxy"):
        selected = [row for row in rows if row["object_type"] == object_type]
        recalls = np.asarray([float(row["recall"]) for row in selected])
        detected = sum(int(row["detected"]) for row in selected)
        print(
            f"{object_type}: n={len(selected)}, detection={detected / len(selected):.3%}, "
            f"mean_recall={np.mean(recalls):.3%}, median_recall={np.median(recalls):.3%}"
        )
        for low, high in ((9, 18), (18, 30), (30, 46)):
            subset = [row for row in selected if low <= float(row["peak_sigma"]) < high]
            subset_recall = np.asarray([float(row["recall"]) for row in subset])
            subset_detected = sum(int(row["detected"]) for row in subset)
            print(
                f"  peak {low}-{high:g} sigma: n={len(subset)}, "
                f"detection={subset_detected / len(subset):.3%}, mean_recall={np.mean(subset_recall):.3%}"
            )
        failures: dict[str, int] = {}
        for row in selected:
            key = str(row["failure_mode"])
            failures[key] = failures.get(key, 0) + 1
        print("  outcomes: " + ", ".join(f"{key}={value}" for key, value in sorted(failures.items())))
    print(f"Per-toy output: {args.output}")
    if args.case_output:
        print(f"Per-case output: {args.case_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
