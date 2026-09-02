#!/usr/bin/env python3
"""Compare the earlier large-toy SEP CV with the bright compact Haigh-aligned CV."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import statistics


METRICS = {
    "toy_detection_rate": "Toy detection rate",
    "mean_toy_recall": "Mean toy recall",
    "mean_recall": "Pixel recall",
    "mean_precision": "Precision",
    "mean_f_score": "F-score",
    "mean_masked_fraction": "Mean displayed-frame masking",
    "max_masked_fraction": "Maximum displayed-frame masking",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--large-root", type=Path, required=True)
    parser.add_argument("--bright-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def result(root: Path, stem: str) -> tuple[str, dict[str, object]]:
    winner = root / f"{stem}_best.json"
    rejected = root / f"{stem}_rejected.json"
    if winner.is_file():
        payload = json.loads(winner.read_text(encoding="utf-8"))
        return "accepted", dict(payload["cross_validation_metrics"])
    if rejected.is_file():
        payload = json.loads(rejected.read_text(encoding="utf-8"))
        return "rejected", dict(payload["best_diagnostic_candidate"])
    raise FileNotFoundError(f"No completed SEP result in {root}")


def values(rows: list[dict[str, str]], prefix: str, metric: str) -> list[float]:
    key = f"{prefix}_{metric}"
    return [float(row[key]) for row in rows if row.get(key) not in (None, "")]


def summary(rows: list[dict[str, str]], prefix: str, metric: str) -> dict[str, float | int]:
    data = values(rows, prefix, metric)
    return {
        "n": len(data), "mean": statistics.fmean(data), "median": statistics.median(data),
        "minimum": min(data), "maximum": max(data),
        "standard_deviation": statistics.stdev(data) if len(data) > 1 else 0.0,
        "zero_count": sum(value == 0 for value in data),
        "at_least_50_percent_count": sum(value >= 0.5 for value in data),
    }


def manifest_summary(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    toys: list[dict[str, object]] = []
    for injection_set in payload["injection_sets"].values():
        for galaxy in injection_set["galaxies"].values():
            toys.extend(galaxy["toys"])
    peaks = [float(toy["peak_sigma"]) for toy in toys]
    sizes = [float(toy["fwhm_pixels"]) for toy in toys]
    types: dict[str, int] = {}
    for toy in toys:
        key = str(toy["object_type"])
        types[key] = types.get(key, 0) + 1
    return {
        "toy_records": len(toys), "peak_sigma_min": min(peaks), "peak_sigma_mean": statistics.fmean(peaks),
        "peak_sigma_max": max(peaks), "fwhm_pixels_min": min(sizes),
        "fwhm_pixels_mean": statistics.fmean(sizes), "fwhm_pixels_max": max(sizes), "types": types,
        "injection_set_count": len(payload["injection_sets"]),
    }


def percent(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def main() -> int:
    args = parse_args()
    large_cv = args.large_root / "SEP_cross_validation"
    bright_cv = args.bright_root / "SEP_cross_validation"
    large_rows = read_csv(large_cv / "cross_validation_candidates.csv")
    bright_rows = read_csv(bright_cv / "cross_validation_candidates.csv")
    large_status, large_final = result(large_cv, "sep_toy_cross_validation")
    bright_status, bright_final = result(bright_cv, "sep_toy_cross_validation")
    large_manifest = manifest_summary(args.large_root / "paired_injections/paired_toy_injection_manifest.json")
    bright_manifest = manifest_summary(args.bright_root / "paired_injections/paired_toy_injection_manifest.json")
    comparisons: dict[str, object] = {}
    for metric in METRICS:
        old = summary(large_rows, "held_out", metric)
        new = summary(bright_rows, "held_out", metric)
        comparisons[metric] = {
            "large_toys_held_out": old, "bright_compact_held_out": new,
            "mean_absolute_change": float(new["mean"]) - float(old["mean"]),
            "large_toys_selected_all22": float(large_final[f"all22_{metric}"]),
            "bright_compact_selected_all22": float(bright_final[f"all22_{metric}"]),
            "selected_all22_absolute_change": (
                float(bright_final[f"all22_{metric}"]) - float(large_final[f"all22_{metric}"])
            ),
        }
    output = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "comparison_scope": "Raw SEP recovery and masking metrics; objective values are not compared because weights and feasibility gates differ.",
        "large_toys": {"status": large_status, "manifest": large_manifest},
        "bright_compact": {"status": bright_status, "manifest": bright_manifest},
        "metrics": comparisons,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "sep_large_vs_bright_compact_comparison.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )
    lines = [
        "# SEP comparison: larger toys versus 150%-brightness compact toys", "",
        f"Generated: {output['created_at']}", "",
        "## Scope and comparability", "",
        "The table compares raw recovery and masking metrics. Objective values are deliberately omitted because the current run uses stronger recovery gates and different objective weights. The experiments also differ in morphology, size, number of injection sets and source count, so this is diagnostic rather than a single-variable brightness experiment against the older large-toy run.", "",
        "| Property | Earlier larger toys | Current bright compact toys |", "|---|---:|---:|",
        f"| Result status | {large_status} | {bright_status} |",
        f"| Saved toy records | {large_manifest['toy_records']} | {bright_manifest['toy_records']} |",
        f"| Injection sets | {large_manifest['injection_set_count']} | {bright_manifest['injection_set_count']} |",
        f"| Peak range | {large_manifest['peak_sigma_min']:.2f}–{large_manifest['peak_sigma_max']:.2f}σ | {bright_manifest['peak_sigma_min']:.2f}–{bright_manifest['peak_sigma_max']:.2f}σ |",
        f"| Mean peak | {large_manifest['peak_sigma_mean']:.2f}σ | {bright_manifest['peak_sigma_mean']:.2f}σ |",
        f"| Mean FWHM | {large_manifest['fwhm_pixels_mean']:.2f} px | {bright_manifest['fwhm_pixels_mean']:.2f} px |", "",
        "## Results", "",
        "| Metric | Earlier held-out mean | Current held-out mean | Change | Earlier selected all-22 | Current selected all-22 | Change |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for metric, label in METRICS.items():
        item = comparisons[metric]
        lines.append(
            f"| {label} | {percent(item['large_toys_held_out']['mean'])} | "
            f"{percent(item['bright_compact_held_out']['mean'])} | {percent(item['mean_absolute_change'])} | "
            f"{percent(item['large_toys_selected_all22'])} | {percent(item['bright_compact_selected_all22'])} | "
            f"{percent(item['selected_all22_absolute_change'])} |"
        )
    detection = comparisons["toy_detection_rate"]
    recall = comparisons["mean_toy_recall"]
    precision = comparisons["mean_precision"]
    masking = comparisons["mean_masked_fraction"]
    lines += ["", "## Interpretation", ""]
    if float(detection["selected_all22_absolute_change"]) > 0 and float(recall["selected_all22_absolute_change"]) > 0:
        lines.append("- The brighter compact toys improved both selected all-22 toy detection and mean toy recall.")
    else:
        lines.append("- Increasing compact-toy peak brightness did not improve both selected all-22 recovery measures.")
    if float(masking["selected_all22_absolute_change"]) > 0:
        lines.append("- The recovery change was accompanied by more displayed-frame masking.")
    else:
        lines.append("- The recovery change did not require more mean displayed-frame masking.")
    if float(precision["selected_all22_absolute_change"]) < 0:
        lines.append("- Precision fell, indicating that any recovery gain included proportionally more non-toy pixels.")
    else:
        lines.append("- Precision improved, indicating a cleaner correspondence between added masks and toy truth.")
    lines += [
        f"- Current SEP status: **{bright_status}**. A rejected result remains diagnostic and must not become an interactive-tool default.",
        "- A strict causal estimate of brightness alone is obtained by comparing the current run with the original 6–30σ Haigh-aligned run, because those two manifests retain identical positions, types and sizes.", "",
    ]
    (args.output_dir / "SEP Larger Toys vs Bright Compact Toys Review.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
