#!/usr/bin/env python3
"""Select unreviewed galaxies most similar to confirmed visually clean fields."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np


FEATURES = (
    "pollution_score", "gaia_catalog_count", "gaia_ir_match_count",
    "strong_match_count", "residual_sigma", "aperture_radius_pixels",
)


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def decision_map(paths: list[Path]) -> dict[str, str]:
    decisions: dict[str, str] = {}
    for path in paths:
        if not path.exists():
            continue
        for row in rows(path):
            value = row.get("decision") or row.get("classification") or ""
            if value in {"Clean", "Polluted"}:
                decisions[row["name"]] = value
    return decisions


def feature_vector(row: dict[str, str]) -> np.ndarray:
    values = np.asarray([float(row[name]) for name in FEATURES], dtype=float)
    # Counts and scores are long-tailed. Log scaling stops one crowded field
    # dominating all other evidence.
    values[:4] = np.log1p(np.maximum(values[:4], 0.0))
    values[4] = np.log1p(max(values[4], 0.0))
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gaia-ranking", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()

    ranking = rows(args.gaia_ranking)
    labels = decision_map(args.decisions)
    by_name = {row["name"]: row for row in ranking}
    labelled_names = [name for name in labels if name in by_name]
    clean_names = [name for name in labelled_names if labels[name] == "Clean"]
    polluted_names = [name for name in labelled_names if labels[name] == "Polluted"]
    if not clean_names or not polluted_names:
        raise ValueError("Both Clean and Polluted reference labels are required")

    all_matrix = np.vstack([feature_vector(row) for row in ranking])
    labelled_matrix = np.vstack([feature_vector(by_name[name]) for name in labelled_names])
    centre = np.nanmedian(labelled_matrix, axis=0)
    scale = 1.4826 * np.nanmedian(np.abs(labelled_matrix - centre), axis=0)
    fallback = np.nanstd(labelled_matrix, axis=0)
    scale = np.where(scale > 1e-9, scale, np.where(fallback > 1e-9, fallback, 1.0))
    standard = (all_matrix - centre) / scale
    index = {row["name"]: i for i, row in enumerate(ranking)}
    clean_ref = standard[[index[name] for name in clean_names]]
    polluted_ref = standard[[index[name] for name in polluted_names]]

    selected = []
    for row, vector in zip(ranking, standard):
        name = row["name"]
        if name in labels:
            continue
        clean_distances = np.sqrt(np.mean((clean_ref - vector) ** 2, axis=1))
        polluted_distances = np.sqrt(np.mean((polluted_ref - vector) ** 2, axis=1))
        clean_distance = float(np.mean(np.partition(clean_distances, min(2, len(clean_distances) - 1))[:3]))
        polluted_distance = float(np.mean(np.partition(polluted_distances, min(4, len(polluted_distances) - 1))[:5]))
        similarity_margin = polluted_distance - clean_distance
        selected.append({
            "name": name,
            "clean_similarity_margin": similarity_margin,
            "distance_to_clean_references": clean_distance,
            "distance_to_polluted_references": polluted_distance,
            "gaia_pollution_score": row["pollution_score"],
            "gaia_ir_match_count": row["gaia_ir_match_count"],
            "gaia_catalog_count": row["gaia_catalog_count"],
        })
    selected.sort(key=lambda row: (-float(row["clean_similarity_margin"]), float(row["distance_to_clean_references"])))
    selected = selected[: args.limit]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(selected[0])
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in selected:
            writer.writerow(row)
    print(f"References: {len(clean_names)} Clean, {len(polluted_names)} Polluted")
    print(f"Selected {len(selected)} unreviewed galaxies -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
