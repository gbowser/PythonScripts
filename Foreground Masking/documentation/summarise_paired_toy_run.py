#!/usr/bin/env python3
"""Summarise one paired SEP/MTObjects Toy Objects run for reporting."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def distribution(values: pd.Series) -> dict[str, float | int]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    return {
        "n": int(clean.size),
        "mean": float(clean.mean()),
        "sd": float(clean.std(ddof=1)),
        "minimum": float(clean.min()),
        "p10": float(clean.quantile(0.10)),
        "p25": float(clean.quantile(0.25)),
        "median": float(clean.median()),
        "p75": float(clean.quantile(0.75)),
        "p90": float(clean.quantile(0.90)),
        "maximum": float(clean.max()),
    }


def bootstrap_mean_ci(values: np.ndarray, seed: int = 20260824) -> list[float]:
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(20_000, values.size), replace=True).mean(axis=1)
    return [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]


def fold_summary(frame: pd.DataFrame) -> dict[str, object]:
    fields = [
        "held_out_score",
        "held_out_mean_recall",
        "held_out_mean_precision",
        "held_out_mean_f_score",
        "held_out_mean_toy_recall",
        "held_out_toy_detection_rate",
        "held_out_mean_masked_fraction",
        "held_out_max_masked_fraction",
        "held_out_false_positive_fraction",
    ]
    return {
        "folds": frame[["fold", *fields]].to_dict(orient="records"),
        "distributions": {field: distribution(frame[field]) for field in fields},
    }


def winner_summary(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cv = data["cross_validation_metrics"]
    return {
        "winning_fold": int(data["winning_fold"]),
        "params": data["params"],
        "software_version": data["software_version"],
        "python_version": data["python_version"],
        "runtime_platform": data["runtime_platform"],
        "metric_version": data["metric_version"],
        "worker_count": int(data["worker_count"]),
        "independent_selection_all40": {
            key.removeprefix("all40_"): value
            for key, value in cv.items()
            if key.startswith("all40_")
        },
        "winning_fold_held_out": {
            key.removeprefix("held_out_"): value
            for key, value in cv.items()
            if key.startswith("held_out_")
        },
    }


def production_summary(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    frame = pd.read_csv(path)
    ok = frame[frame["status"] == "ok"].copy()
    failed = frame[frame["status"] != "ok"].copy()
    kept_column = "segments_kept" if "segments_kept" in ok.columns else "kept_segments"
    raw_column = "segments_raw" if "segments_raw" in ok.columns else "raw_segments"
    return {
        "rows": int(len(frame)),
        "successful": int(len(ok)),
        "failed": int(len(failed)),
        "failed_names": failed.get("name", pd.Series(dtype=str)).astype(str).tolist(),
        "masked_fraction": distribution(ok["masked_fraction"]),
        "masked_fraction_threshold_counts": {
            "above_10_percent": int((ok["masked_fraction"] > 0.10).sum()),
            "above_15_percent": int((ok["masked_fraction"] > 0.15).sum()),
            "above_20_percent": int((ok["masked_fraction"] > 0.20).sum()),
        },
        "segments_kept": distribution(ok[kept_column]),
        "segments_raw": distribution(ok[raw_column]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--run-stamp", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    root = args.research_root
    stamp = args.run_stamp
    sep_root = root / "SEP" / "Toy Objects" / stamp
    mto_root = root / "MTObjects" / "Toy Objects" / stamp
    control = root / "Toy Objects paired optimisation" / stamp
    sep_opt = sep_root / "optimisation"
    mto_opt = mto_root / "optimisation"

    sep_detail = pd.read_csv(sep_opt / "held_out_details.csv")
    mto_detail = pd.read_csv(mto_opt / "held_out_details.csv")
    paired = sep_detail.merge(mto_detail, on="image", suffixes=("_sep", "_mtobjects"), validate="one_to_one")
    paired = paired.sort_values("image", key=lambda series: series.str.casefold()).reset_index(drop=True)

    metrics = [
        "mean_toy_recall",
        "recovered_toys",
        "recall",
        "precision",
        "f_score",
        "masked_fraction",
        "false_positive_fraction",
        "final_mean_toy_recall",
        "final_recovered_toys",
        "final_masked_fraction",
        "final_false_positive_fraction",
    ]
    comparisons: dict[str, object] = {}
    for index, metric in enumerate(metrics):
        sep_values = paired[f"{metric}_sep"].astype(float)
        mto_values = paired[f"{metric}_mtobjects"].astype(float)
        difference = (mto_values - sep_values).to_numpy()
        comparisons[metric] = {
            "sep": distribution(sep_values),
            "mtobjects": distribution(mto_values),
            "mtobjects_minus_sep_mean": float(difference.mean()),
            "mtobjects_minus_sep_median": float(np.median(difference)),
            "mean_difference_bootstrap_95_ci": bootstrap_mean_ci(difference, 20260824 + index),
            "mtobjects_higher": int(np.count_nonzero(difference > 0)),
            "sep_higher": int(np.count_nonzero(difference < 0)),
            "ties": int(np.count_nonzero(difference == 0)),
        }

    paired_export = pd.DataFrame({"galaxy": paired["image"]})
    for metric in metrics:
        paired_export[f"sep_{metric}"] = paired[f"{metric}_sep"]
        paired_export[f"mtobjects_{metric}"] = paired[f"{metric}_mtobjects"]
        paired_export[f"difference_mtobjects_minus_sep_{metric}"] = (
            paired[f"{metric}_mtobjects"] - paired[f"{metric}_sep"]
        )

    manifest_path = control / "immutable_injections" / "paired_toy_injection_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    injection_sets = manifest["injection_sets"]
    manifest_summary = {
        "path": str(manifest_path),
        "sha256": sha256_file(manifest_path),
        "schema_version": manifest["schema_version"],
        "created_utc": manifest["created_utc"],
        "immutable_after_generation": manifest["immutable_after_generation"],
        "fold_seed": manifest["fold_seed"],
        "folds": manifest["folds"],
        "toy_configuration": manifest["toy_configuration"],
        "sets": {
            name: {
                "global_seed": value["global_seed"],
                "galaxies": len(value["galaxies"]),
                "toys": sum(len(record["toys"]) for record in value["galaxies"].values()),
            }
            for name, value in injection_sets.items()
        },
    }

    sep_candidates = pd.read_csv(sep_opt / "cross_validation_candidates.csv")
    mto_candidates = pd.read_csv(mto_opt / "cross_validation_candidates.csv")
    result = {
        "run_stamp": stamp,
        "research_root": str(root),
        "manifest": manifest_summary,
        "run_configuration": json.loads((control / "paired_run_config.json").read_text(encoding="utf-8-sig")),
        "paired_held_out_galaxies": int(len(paired)),
        "paired_held_out_comparisons": comparisons,
        "sep": {
            "configuration": json.loads((sep_opt / "cross_validation_config.json").read_text(encoding="utf-8")),
            "winner": winner_summary(sep_opt / "sep_toy_cross_validation_best.json"),
            "cross_validation": fold_summary(sep_candidates),
            "production_182": production_summary(sep_root / "PNG batch" / "sep_optimised_apply_summary.csv"),
        },
        "mtobjects": {
            "configuration": json.loads((mto_opt / "cross_validation_config.json").read_text(encoding="utf-8")),
            "winner": winner_summary(mto_opt / "mtobjects_toy_cross_validation_best.json"),
            "cross_validation": fold_summary(mto_candidates),
            "production_182": production_summary(mto_root / "PNG batch" / "mtobjects_optimised_apply_summary.csv"),
        },
        "png_outputs": {
            "sep": str(sep_root / "PNG batch"),
            "mtobjects": str(mto_root / "PNG batch"),
            "combined": str(root / "Toy Objects comparison" / stamp),
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "paired_toy_run_analysis.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    paired_export.to_csv(args.output_dir / "paired_toy_held_out_comparison.csv", index=False)

    recall = comparisons["mean_toy_recall"]
    recovered = comparisons["recovered_toys"]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), constrained_layout=True)
    colours = ["#2E74B5", "#D97904"]
    axes[0].bar(["SEP", "MTObjects"], [recall["sep"]["mean"], recall["mtobjects"]["mean"]], color=colours)
    axes[0].set_ylim(0, 1)
    axes[0].set_ylabel("Mean fraction of each toy recovered")
    axes[0].set_title("Held-out toy recovery (40 galaxies)")
    axes[1].bar(["SEP", "MTObjects"], [recovered["sep"]["mean"], recovered["mtobjects"]["mean"]], color=colours)
    axes[1].set_ylim(0, 6)
    axes[1].set_ylabel("Mean toys recovered out of six")
    axes[1].set_title("Held-out objects recovered")
    for ax in axes:
        ax.grid(axis="y", alpha=0.25)
    fig.savefig(args.output_dir / "paired_toy_held_out_recovery.png", dpi=180)
    plt.close(fig)
    print(json.dumps({"analysis": str(args.output_dir / 'paired_toy_run_analysis.json'), "paired_csv": str(args.output_dir / 'paired_toy_held_out_comparison.csv')}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
