"""Shared paired Toy Objects injection loading, checksums, metrics and metadata."""
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np


SCHEMA_VERSION = "paired-toy-injections-v1"
METRIC_VERSION = "paired-toy-metrics-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_array(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(str(contiguous.dtype).encode("ascii"))
    digest.update(np.asarray(contiguous.shape, dtype=np.int64).tobytes())
    digest.update(contiguous.tobytes())
    return digest.hexdigest()


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported paired injection manifest schema: {manifest.get('schema_version')!r}")
    return manifest


def load_materialized_injection(
    manifest_path: Path,
    set_name: str,
    galaxy_name: str,
    science_path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    manifest = load_manifest(manifest_path)
    try:
        record = manifest["injection_sets"][set_name]["galaxies"][galaxy_name]
    except KeyError as exc:
        raise KeyError(f"No paired injection for set={set_name!r}, galaxy={galaxy_name!r}") from exc
    actual_image_sha = sha256_file(science_path)
    if actual_image_sha != record["science_image_sha256"]:
        raise ValueError(f"Science-image checksum mismatch for {galaxy_name}: {actual_image_sha} != {record['science_image_sha256']}")
    payload_path = Path(record["payload_path"])
    actual_payload_sha = sha256_file(payload_path)
    if actual_payload_sha != record["payload_sha256"]:
        raise ValueError(f"Injection payload checksum mismatch for {galaxy_name}")
    with np.load(payload_path, allow_pickle=False) as payload:
        delta = np.asarray(payload["delta"], dtype=float)
        truth_mask = np.asarray(payload["truth_mask"], dtype=bool)
        truth_labels = np.asarray(payload["truth_labels"], dtype=np.int32)
    if sha256_array(truth_mask.astype(np.uint8)) != record["truth_mask_sha256"]:
        raise ValueError(f"Truth-mask checksum mismatch for {galaxy_name}")
    if sha256_array(delta.astype(np.float32)) != record["delta_sha256"]:
        raise ValueError(f"Injection-delta checksum mismatch for {galaxy_name}")
    return delta, truth_mask, truth_labels, list(record["toys"]), record


def evaluate_mask(case: Any, mask: np.ndarray, segments: int) -> dict[str, float | int | str]:
    """Common per-image evaluator used without alteration by SEP and MTObjects."""
    mask = np.asarray(mask, dtype=bool)
    baseline = np.asarray(case.baseline_mask, dtype=bool)
    truth = np.asarray(case.truth_mask, dtype=bool)
    incremental = mask & ~baseline
    truth_pixels = int(np.count_nonzero(truth))

    def measures(candidate: np.ndarray, prefix: str) -> dict[str, float | int]:
        pixels = int(np.count_nonzero(candidate))
        overlap = int(np.count_nonzero(candidate & truth))
        fraction = pixels / candidate.size if candidate.size else 0.0
        recall = overlap / truth_pixels if truth_pixels else 0.0
        precision = overlap / pixels if pixels else 0.0
        f_score = 2.0 * recall * precision / (recall + precision) if recall + precision > 0 else 0.0
        false_positive = (pixels - overlap) / max(1, candidate.size - truth_pixels)
        return {
            f"{prefix}_pixels": pixels,
            f"{prefix}_overlap_pixels": overlap,
            f"{prefix}_masked_fraction": fraction,
            f"{prefix}_recall": recall,
            f"{prefix}_precision": precision,
            f"{prefix}_f_score": f_score,
            f"{prefix}_false_positive_fraction": false_positive,
        }

    inc = measures(incremental, "incremental")
    final = measures(mask, "final")
    toy_recalls: list[float] = []
    final_toy_recalls: list[float] = []
    recovered_toys = 0
    final_recovered_toys = 0
    for toy in case.toys:
        toy_truth = np.asarray(case.truth_labels) == int(toy.toy_id)
        toy_pixels = int(np.count_nonzero(toy_truth))
        toy_recall = int(np.count_nonzero(incremental & toy_truth)) / toy_pixels if toy_pixels else 0.0
        final_toy_recall = int(np.count_nonzero(mask & toy_truth)) / toy_pixels if toy_pixels else 0.0
        toy_recalls.append(toy_recall)
        final_toy_recalls.append(final_toy_recall)
        recovered_toys += int(toy_recall >= 0.5)
        final_recovered_toys += int(final_toy_recall >= 0.5)
    # Existing names remain aliases for incremental metrics so current objectives are unchanged.
    return {
        "metric_version": METRIC_VERSION,
        "image": case.name,
        "truth_pixels": truth_pixels,
        "incremental_pixels": inc["incremental_pixels"],
        "overlap_pixels": inc["incremental_overlap_pixels"],
        "masked_fraction": inc["incremental_masked_fraction"],
        "recall": inc["incremental_recall"],
        "precision": inc["incremental_precision"],
        "f_score": inc["incremental_f_score"],
        "mean_toy_recall": float(np.mean(toy_recalls)) if toy_recalls else 0.0,
        "recovered_toys": recovered_toys,
        "toy_count": len(case.toys),
        "false_positive_fraction": inc["incremental_false_positive_fraction"],
        "final_mean_toy_recall": float(np.mean(final_toy_recalls)) if final_toy_recalls else 0.0,
        "final_recovered_toys": final_recovered_toys,
        "segments": int(segments),
        **inc,
        **final,
    }


def runtime_metadata(repo_root: Path) -> dict[str, str]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True
        ).stdout.strip()
    except Exception:
        commit = "unavailable"
    return {
        "software_version": commit,
        "python_version": sys.version.replace("\n", " "),
        "runtime_platform": platform.platform(),
        "metric_version": METRIC_VERSION,
    }
