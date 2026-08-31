#!/usr/bin/env python3
"""Diagnose why held-out toy objects are missed by an MTObjects winner.

The analysis preserves the immutable injections and the canonical displayed-frame
metrics.  It adds per-toy environment measurements, raw/filtered/final overlap
stages, per-galaxy summaries, binned recovery tables, an Optuna mask-cap curve,
and controlled one-factor counterfactuals.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import multiprocessing as mp
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import evaluate_mtobjects_multiseed_winner as winner  # noqa: E402
import generate_paired_toy_manifest as generator  # noqa: E402
import optimise_toy_objects_MTObjects as opt  # noqa: E402


_CASES = None
_ROOT = None


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def robust_sigma(values: np.ndarray) -> float:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return math.nan
    median = float(np.median(finite))
    sigma = 1.4826 * float(np.median(np.abs(finite - median)))
    if not math.isfinite(sigma) or sigma <= 0:
        sigma = float(np.std(finite))
    return sigma if math.isfinite(sigma) and sigma > 0 else math.nan


def initialise(cases, root) -> None:
    global _CASES, _ROOT
    _CASES = cases
    _ROOT = root


def case_seed_and_name(case_name: str) -> tuple[str, str]:
    if case_name.endswith("]") and " [" in case_name:
        name, seed = case_name.rsplit(" [", 1)
        return seed[:-1], name
    return "unknown", case_name


def analyse_case(task):
    case_index, variant, params = task
    case = _CASES[case_index]
    products = opt.mto.mtobjects_products(case.injected, params, case.geometry, _ROOT)
    region = np.asarray(case.analysis_region, dtype=bool)
    baseline = np.asarray(case.baseline_mask, dtype=bool) & region
    raw = np.asarray(products["raw_segmentation"]) > 0
    filtered = np.asarray(products["filtered_segmentation"]) > 0
    final = np.asarray(products["mask"], dtype=bool) & region
    incremental = final & ~baseline
    metric = opt.paired_toy_common.evaluate_mask(case, products["mask"], len(products["rows"]))
    seed_set, image = case_seed_and_name(case.name)
    height, width = case.data.shape
    cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
    region_y, region_x = np.nonzero(region)
    region_radius = float(np.max(np.hypot(region_x - cx, region_y - cy))) if region_x.size else 1.0
    toy_rows: list[dict[str, object]] = []
    yy, xx = np.indices(case.data.shape)
    finite_data = np.asarray(case.data, dtype=float)
    global_fill = float(np.nanmedian(finite_data[region & np.isfinite(finite_data)]))
    gy, gx = np.gradient(np.nan_to_num(finite_data, nan=global_fill))
    gradient_magnitude = np.hypot(gx, gy)
    for toy in case.toys:
        truth = np.asarray(case.truth_labels) == int(toy.toy_id)
        pixels = int(np.count_nonzero(truth))
        inc_recall = int(np.count_nonzero(incremental & truth)) / pixels if pixels else 0.0
        final_recall = int(np.count_nonzero(final & truth)) / pixels if pixels else 0.0
        baseline_recall = int(np.count_nonzero(baseline & truth)) / pixels if pixels else 0.0
        raw_recall = int(np.count_nonzero(raw & truth)) / pixels if pixels else 0.0
        filtered_recall = int(np.count_nonzero(filtered & truth)) / pixels if pixels else 0.0
        radius = np.hypot(xx - float(toy.x), yy - float(toy.y))
        inner = max(2.0, 1.5 * float(toy.fwhm_pixels))
        outer = max(inner + 2.0, 3.0 * float(toy.fwhm_pixels))
        annulus = (radius >= inner) & (radius <= outer) & region & np.isfinite(case.data)
        local = np.asarray(case.data)[annulus]
        local_median = float(np.median(local)) if local.size else math.nan
        local_sigma = robust_sigma(local)
        delta = np.asarray(case.injected) - np.asarray(case.data)
        peak_delta = float(np.nanmax(delta[truth])) if pixels else math.nan
        local_contrast = peak_delta / local_sigma if math.isfinite(local_sigma) and local_sigma > 0 else math.nan
        local_gradient = float(np.median(gradient_magnitude[annulus])) if np.any(annulus) else math.nan
        edge_distance = min(float(toy.x), float(toy.y), width - 1 - float(toy.x), height - 1 - float(toy.y))
        centre_distance = math.hypot(float(toy.x) - cx, float(toy.y) - cy)
        if inc_recall >= 0.5:
            failure = "detected"
        elif baseline_recall >= 0.5 and final_recall >= 0.5:
            failure = "preexisting_baseline_overlap"
        elif raw_recall == 0:
            failure = "algorithmic_non_detection"
        elif filtered_recall == 0:
            failure = "rejected_by_post_filter"
        elif inc_recall > 0:
            failure = "partial_insufficient_overlap"
        else:
            failure = "mask_overlap_removed_by_baseline"
        toy_rows.append({
            "variant": variant, "seed_set": seed_set, "image": image,
            "toy_id": toy.toy_id, "object_type": toy.object_type,
            "peak_sigma": toy.peak_sigma, "fwhm_pixels": toy.fwhm_pixels,
            "axis_ratio": toy.axis_ratio, "pa_deg": toy.pa_deg,
            "x": toy.x, "y": toy.y, "truth_pixels": pixels,
            "centre_distance_pixels": centre_distance,
            "normalised_centre_distance": centre_distance / max(region_radius, 1.0),
            "edge_distance_pixels": edge_distance,
            "local_median": local_median, "local_sigma": local_sigma,
            "local_gradient": local_gradient, "local_peak_contrast_sigma": local_contrast,
            "raw_recall": raw_recall, "filtered_recall": filtered_recall,
            "baseline_recall": baseline_recall, "final_recall": final_recall,
            "toy_recall": inc_recall, "detected": int(inc_recall >= 0.5),
            "failure_mode": failure,
        })
    case_row = {
        "variant": variant, "seed_set": seed_set, "image": image,
        **{key: value for key, value in metric.items() if key != "image"},
    }
    return case_row, toy_rows


def aggregate_variant(case_rows, max_mask=0.15):
    metrics = opt.aggregate_score(
        case_rows, max_masked_fraction=max_mask, data_loss_penalty=0.5,
        false_positive_penalty=0.1, min_toy_detection_rate=0.25,
        min_mean_toy_recall=0.20,
    )
    successful = sum(int(row["recovered_toys"]) > 0 for row in case_rows)
    return {**metrics, "successful_cases": successful, "total_cases": len(case_rows)}


def summarise_bins(rows, field: str, edges: list[float], labels: list[str]):
    result = []
    for lower, upper, label in zip(edges[:-1], edges[1:], labels):
        selected = [r for r in rows if math.isfinite(float(r[field])) and lower <= float(r[field]) < upper]
        if selected:
            result.append({
                "variable": field, "bin": label, "lower": lower, "upper": upper,
                "toys": len(selected),
                "detection_rate": sum(int(r["detected"]) for r in selected) / len(selected),
                "mean_toy_recall": float(np.mean([float(r["toy_recall"]) for r in selected])),
            })
    return result


def optuna_cap_curve(summary_path: Path):
    with summary_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    output = []
    for cap in (0.15, 0.175, 0.20, 0.25, 0.30, 0.40, 0.60):
        eligible = [
            r for r in rows
            if r.get("status") == "ok"
            and float(r["max_masked_fraction"]) <= cap
            and float(r["toy_detection_rate"]) >= 0.25
            and float(r["mean_toy_recall"]) >= 0.20
        ]
        if eligible:
            best = max(eligible, key=lambda r: (float(r["toy_detection_rate"]), float(r["score"])))
            output.append({
                "mask_cap": cap, "eligible_trials": len(eligible),
                "trial_number": best["trial_number"],
                "toy_detection_rate": best["toy_detection_rate"],
                "mean_toy_recall": best["mean_toy_recall"],
                "mean_masked_fraction": best["mean_masked_fraction"],
                "max_masked_fraction": best["max_masked_fraction"],
                "score": best["score"],
            })
        else:
            output.append({"mask_cap": cap, "eligible_trials": 0})
    return output


def plot_outputs(output: Path, toy_rows, galaxy_rows, bin_rows, cap_rows, variant_rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    selected = [r for r in toy_rows if r["variant"] == "selected"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    axes[0, 0].scatter([r["peak_sigma"] for r in selected], [r["toy_recall"] for r in selected], c=[r["detected"] for r in selected], cmap="coolwarm", alpha=.7)
    axes[0, 0].set(xlabel="Toy peak (sigma)", ylabel="Incremental toy recall", title="Recovery versus brightness")
    axes[0, 1].scatter([r["fwhm_pixels"] for r in selected], [r["toy_recall"] for r in selected], c=[r["detected"] for r in selected], cmap="coolwarm", alpha=.7)
    axes[0, 1].set(xlabel="FWHM (pixels)", ylabel="Incremental toy recall", title="Recovery versus size")
    axes[1, 0].scatter([r["normalised_centre_distance"] for r in selected], [r["toy_recall"] for r in selected], c=[r["detected"] for r in selected], cmap="coolwarm", alpha=.7)
    axes[1, 0].set(xlabel="Normalised centre distance", ylabel="Incremental toy recall", title="Recovery versus position")
    valid = [r for r in selected if math.isfinite(float(r["local_peak_contrast_sigma"]))]
    axes[1, 1].scatter([r["local_peak_contrast_sigma"] for r in valid], [r["toy_recall"] for r in valid], c=[r["detected"] for r in valid], cmap="coolwarm", alpha=.7)
    axes[1, 1].set(xlabel="Peak / local sigma", ylabel="Incremental toy recall", title="Recovery versus local contrast")
    fig.tight_layout(); fig.savefig(output / "toy_recovery_diagnostics.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    names = [r["variant"] for r in variant_rows]
    x = np.arange(len(names))
    ax.bar(x - .2, [100 * float(r["toy_detection_rate"]) for r in variant_rows], .4, label="Detection")
    ax.bar(x + .2, [100 * float(r["max_masked_fraction"]) for r in variant_rows], .4, label="Max mask")
    ax.axhline(15, color="black", ls="--", lw=1, label="15% cap")
    ax.set_xticks(x, names, rotation=35, ha="right"); ax.set_ylabel("Percent"); ax.legend(); ax.set_title("Controlled MTObjects counterfactuals")
    fig.tight_layout(); fig.savefig(output / "counterfactual_comparison.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    valid_caps = [r for r in cap_rows if int(r["eligible_trials"]) > 0]
    ax.plot([100 * float(r["mask_cap"]) for r in valid_caps], [100 * float(r["toy_detection_rate"]) for r in valid_caps], marker="o")
    ax.axhline(50, color="red", ls="--", label="50% target"); ax.axvline(15, color="black", ls=":", label="current cap")
    ax.set(xlabel="Allowed maximum displayed-frame masking (%)", ylabel="Best training toy detection (%)", title="Observed recovery–mask-cap frontier"); ax.legend()
    fig.tight_layout(); fig.savefig(output / "mask_cap_frontier.png", dpi=160); plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--best-json", type=Path, required=True)
    parser.add_argument("--clean-list", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--injection-manifest", type=Path, required=True)
    parser.add_argument("--optimisation-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mtobjects-root", type=Path, required=True)
    parser.add_argument("--pc", default="Desktop")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    names = generator.read_names(args.clean_list)
    build_args = SimpleNamespace(
        manifest=args.manifest, pc=args.pc, mtobjects_root=args.mtobjects_root,
        names=names, max_images=len(names), seed=0, detect_on="original",
        toys_per_image=5, truth_dilation=1, toy_peak_sigma_min=6.0,
        toy_peak_sigma_max=30.0, injection_manifest=args.injection_manifest,
        injection_set="validation_seed_1",
        injection_sets=["validation_seed_1", "validation_seed_2"],
    )
    print("Preparing 44 immutable held-out galaxy/seed cases...", flush=True)
    cases = opt.build_cases(build_args)
    params = winner.load_params(args.best_json)
    variants = {
        "selected": dict(params),
        "minarea_1": {**params, "minarea": 1},
        "maxarea_unlimited": {**params, "max_area": 1_000_000_000},
        "elongation_unlimited": {**params, "max_elongation": 1_000_000.0},
        "postfilters_relaxed": {**params, "minarea": 1, "max_area": 1_000_000_000, "max_elongation": 1_000_000.0},
        "dilation_0": {**params, "dilation_radius": 0},
        "dilation_2": {**params, "dilation_radius": 2},
        "detect_residual": {**params, "detect_on": "residual"},
        "bg_variance_half": {**params, "bg_variance": float(params["bg_variance"]) * 0.5},
        "bg_variance_double": {**params, "bg_variance": float(params["bg_variance"]) * 2.0},
    }
    root = opt.mto.find_mtobjects_root(args.mtobjects_root)
    all_case_rows: list[dict[str, object]] = []
    all_toy_rows: list[dict[str, object]] = []
    variant_rows: list[dict[str, object]] = []
    context = mp.get_context("fork" if sys.platform != "win32" else "spawn")
    with context.Pool(
        min(args.workers, len(cases)), initializer=initialise,
        initargs=(cases, root), maxtasksperchild=24,
    ) as pool:
        for index, (variant, variant_params) in enumerate(variants.items(), start=1):
            print(f"[{index}/{len(variants)}] Evaluating {variant} on {len(cases)} cases...", flush=True)
            tasks = [(case_index, variant, variant_params) for case_index in range(len(cases))]
            results = pool.map(analyse_case, tasks, chunksize=1)
            case_rows = [result[0] for result in results]
            toy_rows = [row for result in results for row in result[1]]
            all_case_rows.extend(case_rows); all_toy_rows.extend(toy_rows)
            aggregate = aggregate_variant(case_rows)
            variant_rows.append({"variant": variant, **aggregate})
            print(
                f"{variant}: detection={aggregate['toy_detection_rate']:.1%}, "
                f"recall={aggregate['mean_toy_recall']:.1%}, "
                f"max_mask={aggregate['max_masked_fraction']:.1%}", flush=True,
            )
            write_csv(args.output_dir / "counterfactual_summary.csv", variant_rows)

    selected_toys = [row for row in all_toy_rows if row["variant"] == "selected"]
    selected_cases = [row for row in all_case_rows if row["variant"] == "selected"]
    galaxy_rows = []
    for image in sorted({str(row["image"]) for row in selected_cases}):
        cases_for_image = [row for row in selected_cases if row["image"] == image]
        toys_for_image = [row for row in selected_toys if row["image"] == image]
        galaxy_rows.append({
            "image": image, "seed_cases": len(cases_for_image), "toys": len(toys_for_image),
            "detected_toys": sum(int(row["detected"]) for row in toys_for_image),
            "detection_rate": sum(int(row["detected"]) for row in toys_for_image) / max(1, len(toys_for_image)),
            "mean_toy_recall": float(np.mean([float(row["toy_recall"]) for row in toys_for_image])),
            "mean_masked_fraction": float(np.mean([float(row["masked_fraction"]) for row in cases_for_image])),
            "max_masked_fraction": float(np.max([float(row["masked_fraction"]) for row in cases_for_image])),
            "dominant_failure_mode": max(
                {str(row["failure_mode"]) for row in toys_for_image},
                key=lambda mode: sum(str(row["failure_mode"]) == mode for row in toys_for_image),
            ),
        })

    failure_rows = []
    for mode in sorted({str(row["failure_mode"]) for row in selected_toys}):
        chosen = [row for row in selected_toys if row["failure_mode"] == mode]
        failure_rows.append({
            "failure_mode": mode, "toys": len(chosen), "fraction": len(chosen) / len(selected_toys),
            "mean_peak_sigma": float(np.mean([float(row["peak_sigma"]) for row in chosen])),
            "mean_fwhm_pixels": float(np.mean([float(row["fwhm_pixels"]) for row in chosen])),
            "mean_local_contrast_sigma": float(np.nanmean([float(row["local_peak_contrast_sigma"]) for row in chosen])),
        })

    bin_rows = []
    bin_rows += summarise_bins(selected_toys, "peak_sigma", [6, 10, 15, 20, 25, 31], ["6-10", "10-15", "15-20", "20-25", "25-30"])
    bin_rows += summarise_bins(selected_toys, "fwhm_pixels", [0, 3, 5, 8, 12, 18, 100], ["<3", "3-5", "5-8", "8-12", "12-18", ">=18"])
    bin_rows += summarise_bins(selected_toys, "normalised_centre_distance", [0, .2, .4, .6, .8, 1.01], ["0-.2", ".2-.4", ".4-.6", ".6-.8", ".8-1"])
    contrast_values = [float(r["local_peak_contrast_sigma"]) for r in selected_toys if math.isfinite(float(r["local_peak_contrast_sigma"]))]
    if contrast_values:
        qs = list(np.quantile(contrast_values, [0, .25, .5, .75, 1]))
        qs[-1] += 1e-9
        bin_rows += summarise_bins(selected_toys, "local_peak_contrast_sigma", qs, ["Q1", "Q2", "Q3", "Q4"])

    cap_rows = optuna_cap_curve(args.optimisation_summary)
    write_csv(args.output_dir / "failure_analysis_per_toy.csv", selected_toys)
    write_csv(args.output_dir / "failure_analysis_per_galaxy.csv", galaxy_rows)
    write_csv(args.output_dir / "failure_mode_summary.csv", failure_rows)
    write_csv(args.output_dir / "recovery_by_bin.csv", bin_rows)
    write_csv(args.output_dir / "mask_cap_frontier.csv", cap_rows)
    write_csv(args.output_dir / "counterfactual_per_case.csv", all_case_rows)
    write_csv(args.output_dir / "counterfactual_summary.csv", variant_rows)
    plot_outputs(args.output_dir, selected_toys, galaxy_rows, bin_rows, cap_rows, variant_rows)
    report = {
        "status": "complete", "toys": len(selected_toys), "cases": len(selected_cases),
        "failure_modes": failure_rows, "counterfactuals": variant_rows,
        "mask_cap_frontier": cap_rows,
        "recommended_next_step": "Interpret dominant failure modes and only then revise the objective or mask cap.",
    }
    (args.output_dir / "failure_mode_analysis.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (args.output_dir / "failure_analysis.complete").touch()
    print(f"Failure-mode analysis complete: {args.output_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
