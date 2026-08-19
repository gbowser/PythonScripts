"""Shared two-dimensional Spike Gate metrics and constrained objective.

Spike Gate is a one-dimensional identifier along the deprojected bar-major
profile.  This module expands each contiguous gated run into a compact 2-D
target region and a larger permitted support region.  SEP and MTObjects are
then scored identically, preventing either optimiser from gaining recovery
credit simply by masking a very large connected part of the galaxy.
"""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np


DEFAULT_MIN_GATE_RECOVERY = 0.50
DEFAULT_MIN_CANDIDATE_DETECTION = 0.50
DEFAULT_MEAN_MASK_CAP = 0.02
DEFAULT_IMAGE_MASK_CAP = 0.05
DEFAULT_MEAN_EXCESS_CAP = 0.02
DEFAULT_MEAN_GALAXY_LOSS_CAP = 0.01


def contiguous_runs(values: np.ndarray) -> Iterable[tuple[int, int]]:
    active = np.asarray(values, dtype=bool)
    padded = np.pad(active.astype(np.int8), 1)
    changes = np.diff(padded)
    starts = np.flatnonzero(changes == 1)
    stops = np.flatnonzero(changes == -1) - 1
    return zip(starts.tolist(), stops.tolist())


def build_gate_regions(
    x_axis: np.ndarray,
    y_axis: np.ndarray,
    spike_samples: np.ndarray,
    profile_half_width_arcsec: float,
    *,
    support_scale: float = 2.5,
) -> tuple[np.ndarray, np.ndarray, list[np.ndarray]]:
    """Return compact target, permitted support, and per-candidate masks."""
    x = np.asarray(x_axis, dtype=float)
    y = np.asarray(y_axis, dtype=float)
    spikes = np.asarray(spike_samples, dtype=bool)
    if x.size != spikes.size:
        raise ValueError(f"Spike/profile size mismatch: {spikes.size} versus {x.size}.")
    xx, yy = np.meshgrid(x, y)
    target = np.zeros(xx.shape, dtype=bool)
    support = np.zeros(xx.shape, dtype=bool)
    candidates: list[np.ndarray] = []
    dx = float(np.nanmedian(np.abs(np.diff(x)))) if x.size > 1 else 1.0
    if not math.isfinite(dx) or dx <= 0:
        dx = 1.0
    base_y = max(float(profile_half_width_arcsec), 2.0 * dx)
    for start, stop in contiguous_runs(spikes):
        centre_x = 0.5 * (float(x[start]) + float(x[stop]))
        half_run = 0.5 * abs(float(x[stop]) - float(x[start]))
        radius_x = max(2.0 * dx, half_run + dx)
        radius_y = base_y
        candidate = ((xx - centre_x) / radius_x) ** 2 + (yy / radius_y) ** 2 <= 1.0
        allowed = (
            ((xx - centre_x) / (support_scale * radius_x)) ** 2
            + (yy / (support_scale * radius_y)) ** 2
            <= 1.0
        )
        target |= candidate
        support |= allowed
        candidates.append(candidate)
    return target, support, candidates


def score_mask(
    mask_view: np.ndarray,
    x_axis: np.ndarray,
    y_axis: np.ndarray,
    spike_samples: np.ndarray,
    profile_half_width_arcsec: float,
    protected_radius_arcsec: float,
    *,
    candidate_overlap_threshold: float = 0.25,
) -> dict[str, float | int]:
    mask = np.asarray(mask_view, dtype=bool)
    target, support, candidates = build_gate_regions(
        x_axis, y_axis, spike_samples, profile_half_width_arcsec
    )
    target_pixels = int(np.count_nonzero(target))
    mask_pixels = int(np.count_nonzero(mask))
    overlap_pixels = int(np.count_nonzero(mask & target))
    supported_pixels = int(np.count_nonzero(mask & support))
    gate_recovery = overlap_pixels / target_pixels if target_pixels else 1.0
    supported_precision = supported_pixels / mask_pixels if mask_pixels else (1.0 if not candidates else 0.0)
    recovered = 0
    for candidate in candidates:
        pixels = int(np.count_nonzero(candidate))
        overlap = int(np.count_nonzero(mask & candidate))
        if pixels and overlap / pixels >= float(candidate_overlap_threshold):
            recovered += 1
    candidate_count = len(candidates)
    candidate_detection = recovered / candidate_count if candidate_count else 1.0
    excess_mask_fraction = float(np.count_nonzero(mask & ~support) / max(1, mask.size))

    xx, yy = np.meshgrid(np.asarray(x_axis, dtype=float), np.asarray(y_axis, dtype=float))
    protected = (xx * xx + yy * yy <= float(protected_radius_arcsec) ** 2) & ~support
    protected_pixels = int(np.count_nonzero(protected))
    galaxy_loss = float(np.count_nonzero(mask & protected) / max(1, protected_pixels))
    return {
        "gate_candidate_count": candidate_count,
        "recovered_gate_candidates": recovered,
        "gate_target_pixels": target_pixels,
        "gate_overlap_pixels": overlap_pixels,
        "gate_recovery": float(gate_recovery),
        "candidate_detection_rate": float(candidate_detection),
        "supported_mask_precision": float(supported_precision),
        "excess_mask_fraction": excess_mask_fraction,
        "protected_galaxy_loss": galaxy_loss,
        "zero_detection_with_gate": int(candidate_count > 0 and overlap_pixels == 0),
    }


def aggregate_constrained(case_rows: list[dict[str, object]]) -> dict[str, float]:
    if not case_rows:
        return {"objective": 1.0e6}
    gated = [row for row in case_rows if int(row.get("gate_candidate_count", 0)) > 0]
    recovery_rows = gated if gated else case_rows
    mean_recovery = float(np.mean([float(row["gate_recovery"]) for row in recovery_rows]))
    min_recovery = float(np.min([float(row["gate_recovery"]) for row in recovery_rows]))
    mean_detection = float(np.mean([float(row["candidate_detection_rate"]) for row in recovery_rows]))
    mean_precision = float(np.mean([float(row["supported_mask_precision"]) for row in case_rows]))
    mean_excess = float(np.mean([float(row["excess_mask_fraction"]) for row in case_rows]))
    mean_galaxy_loss = float(np.mean([float(row["protected_galaxy_loss"]) for row in case_rows]))
    mean_masked = float(np.mean([float(row["masked_fraction"]) for row in case_rows]))
    max_masked = float(np.max([float(row["masked_fraction"]) for row in case_rows]))
    mean_non_gate_profile = float(np.mean([float(row["non_spike_profile_fraction"]) for row in case_rows]))
    mean_profile_affected = float(np.mean([float(row["profile_affected_fraction"]) for row in case_rows]))
    mean_profile_change = float(np.mean([float(row["profile_change"]) for row in case_rows]))
    max_bridge_arcsec = float(np.max([float(row.get("longest_bridge_span_arcsec", 0.0)) for row in case_rows]))
    mean_bridge = float(np.mean([float(row.get("normalised_bridge_span", 0.0)) for row in case_rows]))
    zero_cases = int(sum(int(row["zero_detection_with_gate"]) for row in gated))

    base = (
        5.0 * (1.0 - mean_recovery)
        + 3.0 * (1.0 - mean_detection)
        + 8.0 * mean_excess
        + 12.0 * mean_galaxy_loss
        + 2.0 * mean_masked
        + 4.0 * mean_non_gate_profile
        + 2.0 * mean_bridge
        + 25.0 * zero_cases / max(1, len(gated))
    )
    deficits = (
        max(0.0, DEFAULT_MIN_GATE_RECOVERY - mean_recovery)
        + max(0.0, DEFAULT_MIN_CANDIDATE_DETECTION - mean_detection)
    )
    cap_excess = (
        max(0.0, mean_masked - DEFAULT_MEAN_MASK_CAP)
        + max(0.0, max_masked - DEFAULT_IMAGE_MASK_CAP)
        + max(0.0, mean_excess - DEFAULT_MEAN_EXCESS_CAP)
        + max(0.0, mean_galaxy_loss - DEFAULT_MEAN_GALAXY_LOSS_CAP)
    )
    infeasible = bool(zero_cases or deficits > 0.0 or cap_excess > 0.0)
    objective = base + (50.0 + 100.0 * deficits + 200.0 * cap_excess if infeasible else 0.0)
    return {
        "objective": float(objective),
        "base_objective": float(base),
        "mean_gate_recovery": mean_recovery,
        "min_gate_recovery": min_recovery,
        "mean_spike_coverage": mean_recovery,
        "min_spike_coverage": min_recovery,
        "mean_candidate_detection_rate": mean_detection,
        "mean_supported_mask_precision": mean_precision,
        "mean_excess_mask_fraction": mean_excess,
        "mean_protected_galaxy_loss": mean_galaxy_loss,
        "mean_masked_fraction": mean_masked,
        "max_masked_fraction": max_masked,
        "mean_non_spike_profile_fraction": mean_non_gate_profile,
        "mean_profile_affected_fraction": mean_profile_affected,
        "mean_profile_change": mean_profile_change,
        "max_longest_bridge_span_arcsec": max_bridge_arcsec,
        "zero_detection_cases": float(zero_cases),
        "constraint_deficit": float(deficits),
        "constraint_cap_excess": float(cap_excess),
        "infeasible": float(infeasible),
    }
