#!/usr/bin/env python3
"""Optimise global SEP parameters against Spike Gate profile evidence.

Spike Gate supplies the target: narrow positive bar-major profile spikes that
should be covered by the mask. SEP supplies the global two-dimensional source
segmentation. Optuna searches for SEP settings that cover spike samples while
minimising unnecessary image/profile masking.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import sys
import time
import traceback
import warnings

import numpy as np
import optuna


SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
SUPPORT_DIRS = tuple(FOREGROUND_ROOT / name for name in ("Batch tools", "PhotUtils", "Interactive tools", "Shared", "Utilities"))
for path in (PROJECT_ROOT, FOREGROUND_ROOT, SCRIPT_DIR, *SUPPORT_DIRS):
    if str(path) not in sys.path:
        sys.path.append(str(path))

if os.name != "nt":
    os.environ.setdefault("FOREGROUND_MASKING_PC", "Desktop")

import interactive_sep_spike_gate_parameter_tester as sep_tool  # noqa: E402
import spike_gate_objective as gate_objective  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, detect_pc, remove_foreground_folder  # noqa: E402
from optimisation_results_workbook import append_run_to_workbook  # noqa: E402


DEFAULT_MAX_IMAGES = 20
DEFAULT_INITIAL_POINTS = 16
DEFAULT_MAX_ITER = 64
DEFAULT_RANDOM_SEED = 20260719
DEFAULT_STUDY_NAME = "sep-spike-gate-optimisation"
DEFAULT_MAX_MASKED_FRACTION = 0.15
DEFAULT_DATA_LOSS_PENALTY = 4.0
DEFAULT_PROFILE_LOSS_PENALTY = 2.0
DEFAULT_MEAN_SPIKE_COVERAGE_WEIGHT = 24.0
DEFAULT_MIN_SPIKE_COVERAGE_WEIGHT = 12.0
DEFAULT_MAX_PROFILE_AFFECTED_FRACTION = 1.0
DEFAULT_MAX_NON_SPIKE_PROFILE_FRACTION = 1.0
DEFAULT_MAX_BRIDGE_SPAN_ARCSEC = 1.0e6
DEFAULT_BRIDGE_SPAN_PENALTY = 0.0
DEFAULT_MAX_AREA_SEARCH = 5000
DEFAULT_DETECT_THRESH_MIN = 0.5
DEFAULT_DETECT_THRESH_MAX = 8.0
DEFAULT_MINAREA_MIN = 1
DEFAULT_MINAREA_MAX = 80
DEFAULT_DILATION_RADIUS_MIN = 0
DEFAULT_DILATION_RADIUS_MAX = 8
OPTIMISED_PARAMETER_NAMES = [
    "detect_thresh",
    "minarea",
    "deblend_nthresh",
    "deblend_cont",
    "back_size",
    "filter_size",
    "dilation_radius",
    "max_area",
    "max_elongation",
]


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_duration(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    hours, remainder = divmod(int(round(seconds)), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def expected_completion_text(seconds_remaining: float) -> str:
    return datetime.fromtimestamp(time.time() + max(0.0, float(seconds_remaining))).strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    print(f"[{timestamp()}] {message}", flush=True)


@dataclass
class GalaxyCase:
    name: str
    data: np.ndarray
    geometry: dict[str, float]
    radii: np.ndarray
    original_profile: np.ndarray
    spike_samples: np.ndarray


_WORKER_CASES: list[GalaxyCase] | None = None
_WORKER_PROFILE_WIDTH_PIXELS = 0


def initialise_score_worker(cases: list[GalaxyCase], profile_width_pixels: int) -> None:
    global _WORKER_CASES, _WORKER_PROFILE_WIDTH_PIXELS
    _WORKER_CASES = cases
    _WORKER_PROFILE_WIDTH_PIXELS = int(profile_width_pixels)


def score_case_worker(
    task: tuple[int, dict[str, float | int | str]],
) -> tuple[dict[str, float | int | str], float]:
    case_index, params = task
    if _WORKER_CASES is None:
        raise RuntimeError("SEP Spike Gate scoring worker was not initialised.")
    started = time.perf_counter()
    row = score_case(_WORKER_CASES[case_index], params, _WORKER_PROFILE_WIDTH_PIXELS)
    return row, time.perf_counter() - started


def default_params(detect_on: str) -> dict[str, float | int | str]:
    if detect_on != "original":
        raise ValueError("SEP Spike Gate optimisation must operate on the original science image.")
    return {
        "detect_on": detect_on,
        "detect_thresh": sep_tool.DEFAULT_DETECT_THRESH,
        "minarea": sep_tool.DEFAULT_MINAREA,
        "deblend_nthresh": sep_tool.DEFAULT_DEBLEND_NTHRESH,
        "deblend_cont": sep_tool.DEFAULT_DEBLEND_CONT,
        "back_size": sep_tool.DEFAULT_BACK_SIZE,
        "filter_size": sep_tool.DEFAULT_FILTER_SIZE,
        "dilation_radius": sep_tool.DEFAULT_DILATION_RADIUS,
        "max_area": sep_tool.DEFAULT_MAX_AREA,
        "max_elongation": sep_tool.DEFAULT_MAX_ELONGATION,
        "exclude_center_pixels": sep_tool.DEFAULT_EXCLUDE_CENTER_PIXELS,
        "spike_excess_fraction": sep_tool.DEFAULT_SPIKE_EXCESS_FRACTION,
        "spike_neighbour_inner_arcsec": sep_tool.DEFAULT_SPIKE_NEIGHBOUR_INNER_ARCSEC,
        "spike_neighbour_outer_arcsec": sep_tool.DEFAULT_SPIKE_NEIGHBOUR_OUTER_ARCSEC,
        "spike_side_offset_samples": sep_tool.DEFAULT_SPIKE_SIDE_OFFSET_SAMPLES,
        "spike_side_drop_fraction": sep_tool.DEFAULT_SPIKE_SIDE_DROP_FRACTION,
        "spike_window_samples": sep_tool.DEFAULT_SPIKE_WINDOW_SAMPLES,
    }


def optuna_trial_to_params(trial: optuna.Trial, args: argparse.Namespace) -> dict[str, float | int | str]:
    detect_on = str(args.detect_on)
    params = default_params(detect_on)
    params["spike_gate_detect_on"] = str(args.spike_gate_detect_on)
    params["detect_thresh"] = trial.suggest_float(
        "detect_thresh",
        float(args.detect_thresh_min),
        float(args.detect_thresh_max),
    )
    params["minarea"] = trial.suggest_int("minarea", int(args.minarea_min), int(args.minarea_max))
    params["deblend_nthresh"] = trial.suggest_int("deblend_nthresh", 8, 64)
    params["deblend_cont"] = trial.suggest_float("deblend_cont", 0.0001, 0.1, log=True)
    params["back_size"] = trial.suggest_categorical("back_size", [16, 24, 32, 48, 64, 96, 128, 192, 256])
    params["filter_size"] = trial.suggest_categorical("filter_size", [1, 3, 5, 7, 9])
    params["dilation_radius"] = trial.suggest_int(
        "dilation_radius",
        int(args.dilation_radius_min),
        int(args.dilation_radius_max),
    )
    params["max_area"] = trial.suggest_int("max_area", 20, int(args.max_area_search))
    params["max_elongation"] = trial.suggest_float("max_elongation", 1.5, 20.0)
    return params


def params_to_jsonable(params: dict[str, float | int | str]) -> dict[str, float | int | str]:
    return {
        key: "NaN" if isinstance(value, float) and math.isnan(value) else value
        for key, value in params.items()
    }


def append_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def select_rows(
    manifest: Path, pc_name: str, names: list[str] | None, max_images: int, seed: int
) -> list[dict[str, str]]:
    rows = sep_tool.display.rows_with_images_for_pc(sep_tool.display.read_manifest(manifest), pc_name)
    if names:
        wanted = {name.casefold() for name in names}
        rows = [row for row in rows if row["name"].casefold() in wanted]

    selected = []
    for row in rows:
        if sep_tool.display.required_geometry(row) is not None:
            selected.append(row)
    if not selected:
        raise ValueError("No usable science images found for the requested PC/name selection.")
    rng = np.random.default_rng(seed)
    rng.shuffle(selected)
    return selected[:max_images]


def spike_profile_for_case(
    data: np.ndarray,
    geometry: dict[str, float],
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    radius_arcsec = sep_tool.display.profile_radius_pixels(data, geometry) * geometry["pixel_scale"]
    detection, _residual, _nonfinite_mask = sep_tool.prepare_detection_image(data, str(args.spike_gate_detect_on))
    profile_source_view, x_axis, y_axis = sep_tool.display.deproject_bar_aligned_cutout(
        detection,
        geometry,
        radius_arcsec,
    )
    half_width = 0.5 * int(args.profile_width_pixels) * geometry["pixel_scale"]
    radii, intensity = sep_tool.display.bar_major_axis_profile(profile_source_view, x_axis, y_axis, half_width)
    spikes = sep_tool.detect_profile_spikes(
        radii,
        intensity,
        excess_fraction=float(args.spike_excess_fraction),
        neighbour_inner_arcsec=float(args.spike_neighbour_inner_arcsec),
        neighbour_outer_arcsec=float(args.spike_neighbour_outer_arcsec),
        side_offset_samples=int(args.spike_side_offset_samples),
        side_drop_fraction=float(args.spike_side_drop_fraction),
        center_exclusion_arcsec=float(args.spike_center_exclusion_arcsec),
    )
    spikes = sep_tool.expand_boolean_mask(spikes, int(args.spike_window_samples))
    return radii, intensity, spikes


def build_cases(args: argparse.Namespace) -> list[GalaxyCase]:
    cases: list[GalaxyCase] = []
    row_limit = int(args.max_images) if not args.require_spikes else sys.maxsize
    rows = select_rows(args.manifest, args.pc, args.names, row_limit, int(args.seed))
    for row in rows:
        name = row["name"]
        geometry = sep_tool.display.required_geometry(row)
        if geometry is None:
            continue
        data, _header = sep_tool.load_fits(sep_tool.display.image_path_for_pc(row, args.pc))
        radii, profile, spikes = spike_profile_for_case(data, geometry, args)
        spike_count = int(np.count_nonzero(spikes))
        if spike_count == 0 and args.require_spikes:
            log(f"Skipping {name}: Spike Gate found no spike samples on {args.spike_gate_detect_on}.")
            continue
        cases.append(GalaxyCase(name, data, geometry, radii, profile, spikes))
        log(f"Prepared {name}: {spike_count} Spike Gate samples on {args.spike_gate_detect_on}.")
        if len(cases) >= int(args.max_images):
            break
    if not cases:
        raise ValueError("No optimisation cases remain. Try explicit --names or omit --require-spikes.")
    return cases


def profile_mask_for_image_mask(
    data: np.ndarray,
    mask: np.ndarray,
    geometry: dict[str, float],
    profile_width_pixels: int,
) -> np.ndarray:
    radius_arcsec = sep_tool.display.profile_radius_pixels(data, geometry) * geometry["pixel_scale"]
    mask_view, _x_axis, y_axis = sep_tool.display.deproject_bar_aligned_cutout(mask.astype(float), geometry, radius_arcsec, order=0)
    mask_view = np.isfinite(mask_view) & (mask_view > 0.5)
    half_width = 0.5 * int(profile_width_pixels) * geometry["pixel_scale"]
    return sep_tool.profile_mask_at_bar_major(mask_view, y_axis, half_width)


def score_case(
    case: GalaxyCase,
    params: dict[str, float | int | str],
    profile_width_pixels: int,
) -> dict[str, float | int | str]:
    products = sep_tool.sep_products(case.data, params, case.geometry)
    radius_arcsec = sep_tool.display.profile_radius_pixels(case.data, case.geometry) * case.geometry["pixel_scale"]
    raw_mask = np.asarray(products["mask"], dtype=bool)
    _raw_view, x_axis, y_axis = sep_tool.display.deproject_bar_aligned_cutout(
        raw_mask.astype(float), case.geometry, radius_arcsec, order=0
    )
    half_width = 0.5 * int(profile_width_pixels) * case.geometry["pixel_scale"]
    def labels_to_view(component_labels: np.ndarray) -> np.ndarray:
        view, _x, _y = sep_tool.display.deproject_bar_aligned_cutout(
            component_labels.astype(float), case.geometry, radius_arcsec, order=0
        )
        return np.where(np.isfinite(view), view, 0.0)
    mask, component_metrics = gate_objective.retain_gate_supported_components(
        raw_mask, labels_to_view, x_axis, y_axis, case.spike_samples, half_width
    )
    profile_mask = profile_mask_for_image_mask(case.data, mask, case.geometry, profile_width_pixels)
    mask_view, _x_axis, _y_axis = sep_tool.display.deproject_bar_aligned_cutout(
        mask.astype(float), case.geometry, radius_arcsec, order=0
    )
    mask_view = np.isfinite(mask_view) & (mask_view > 0.5)
    bar_sma = sep_tool.display.bar_sma_deprojected_arcsec(case.geometry)
    gate_metrics = gate_objective.score_mask(
        mask_view,
        x_axis,
        y_axis,
        case.spike_samples,
        half_width,
        max(2.0 * bar_sma, 0.35 * radius_arcsec),
    )

    spike_count = int(np.count_nonzero(case.spike_samples))
    covered_spikes = int(np.count_nonzero(profile_mask & case.spike_samples))
    spike_coverage = 1.0 if spike_count == 0 else covered_spikes / spike_count
    non_spike_profile = profile_mask & ~case.spike_samples
    non_spike_profile_fraction = float(np.count_nonzero(non_spike_profile) / max(1, profile_mask.size - spike_count))
    profile_affected_fraction = float(np.count_nonzero(profile_mask) / max(1, profile_mask.size))
    masked_fraction = float(np.count_nonzero(mask) / mask.size)
    bridged_profile, replaced = sep_tool.fill_profile_with_log_linear_bridges(case.original_profile, profile_mask)
    finite = np.isfinite(case.original_profile) & np.isfinite(bridged_profile) & (case.original_profile > 0) & (bridged_profile > 0)
    profile_change = 0.0
    if np.count_nonzero(finite) >= 5:
        profile_change = float(np.nanmedian(np.abs(np.log10(bridged_profile[finite]) - np.log10(case.original_profile[finite]))))
    longest_bridge_span_arcsec = 0.0
    longest_bridge_run_samples = 0
    for start, stop in sep_tool.contiguous_true_runs(replaced):
        longest_bridge_run_samples = max(longest_bridge_run_samples, int(stop - start + 1))
        if 0 <= start < case.radii.size and 0 <= stop < case.radii.size:
            span = abs(float(case.radii[stop]) - float(case.radii[start]))
            if math.isfinite(span):
                longest_bridge_span_arcsec = max(longest_bridge_span_arcsec, span)
    result = {
        "image": case.name,
        "spike_samples": spike_count,
        "covered_spike_samples": covered_spikes,
        "spike_coverage": spike_coverage,
        "masked_pixels": int(np.count_nonzero(mask)),
        "masked_fraction": masked_fraction,
        "profile_affected_fraction": profile_affected_fraction,
        "non_spike_profile_fraction": non_spike_profile_fraction,
        "profile_change": profile_change,
        "bridged_profile_samples": int(np.count_nonzero(replaced)),
        "longest_bridge_run_samples": longest_bridge_run_samples,
        "longest_bridge_span_arcsec": longest_bridge_span_arcsec,
        "segments": len(products["rows"]),
        "normalised_bridge_span": longest_bridge_span_arcsec / max(1.0, 2.0 * bar_sma),
    }
    result.update(gate_metrics)
    result.update(component_metrics)
    return result


def aggregate_score(
    case_rows: list[dict[str, float | int | str]],
    *,
    max_masked_fraction: float,
    data_loss_penalty: float,
    profile_loss_penalty: float,
    mean_spike_coverage_weight: float,
    min_spike_coverage_weight: float,
    max_profile_affected_fraction: float,
    max_non_spike_profile_fraction: float,
    max_bridge_span_arcsec: float,
    bridge_span_penalty: float,
) -> dict[str, float]:
    constrained = gate_objective.aggregate_constrained(case_rows)
    if "mean_gate_recovery" in constrained:
        return constrained
    spike_rows = [row for row in case_rows if int(row["spike_samples"]) > 0]
    rows_for_coverage = spike_rows if spike_rows else case_rows
    mean_spike_coverage = float(np.mean([float(row["spike_coverage"]) for row in rows_for_coverage]))
    min_spike_coverage = float(np.min([float(row["spike_coverage"]) for row in rows_for_coverage]))
    mean_masked_fraction = float(np.mean([float(row["masked_fraction"]) for row in case_rows]))
    max_masked_fraction_seen = float(np.max([float(row["masked_fraction"]) for row in case_rows]))
    mean_profile_affected = float(np.mean([float(row["profile_affected_fraction"]) for row in case_rows]))
    mean_non_spike_profile = float(np.mean([float(row["non_spike_profile_fraction"]) for row in case_rows]))
    mean_profile_change = float(np.mean([float(row["profile_change"]) for row in case_rows]))
    mean_longest_bridge_span = float(np.mean([float(row["longest_bridge_span_arcsec"]) for row in case_rows]))
    max_longest_bridge_span = float(np.max([float(row["longest_bridge_span_arcsec"]) for row in case_rows]))

    base_objective = (
        mean_spike_coverage_weight * (1.0 - mean_spike_coverage)
        + min_spike_coverage_weight * (1.0 - min_spike_coverage)
        + profile_loss_penalty * mean_non_spike_profile
        + data_loss_penalty * mean_masked_fraction
        + profile_loss_penalty * mean_profile_affected
        + bridge_span_penalty * mean_longest_bridge_span
        + 0.5 * mean_profile_change
    )
    cap_excess = max(0.0, max_masked_fraction_seen - max_masked_fraction)
    profile_cap_excess = max(0.0, mean_profile_affected - max_profile_affected_fraction)
    non_spike_cap_excess = max(0.0, mean_non_spike_profile - max_non_spike_profile_fraction)
    bridge_span_cap_excess = max(0.0, max_longest_bridge_span - max_bridge_span_arcsec)
    cap_penalty = (
        100.0 * cap_excess
        + 80.0 * profile_cap_excess
        + 80.0 * non_spike_cap_excess
        + 4.0 * bridge_span_cap_excess
    )
    objective = base_objective + (10.0 + cap_penalty if cap_penalty > 0.0 else 0.0)
    return {
        "objective": objective,
        "base_objective": base_objective,
        "mean_spike_coverage": mean_spike_coverage,
        "min_spike_coverage": min_spike_coverage,
        "mean_masked_fraction": mean_masked_fraction,
        "max_masked_fraction": max_masked_fraction_seen,
        "max_masked_fraction_limit": max_masked_fraction,
        "masked_fraction_cap_excess": cap_excess,
        "max_profile_affected_fraction_limit": max_profile_affected_fraction,
        "profile_affected_cap_excess": profile_cap_excess,
        "max_non_spike_profile_fraction_limit": max_non_spike_profile_fraction,
        "non_spike_profile_cap_excess": non_spike_cap_excess,
        "mean_longest_bridge_span_arcsec": mean_longest_bridge_span,
        "max_longest_bridge_span_arcsec": max_longest_bridge_span,
        "max_bridge_span_arcsec_limit": max_bridge_span_arcsec,
        "bridge_span_cap_excess": bridge_span_cap_excess,
        "mean_profile_affected_fraction": mean_profile_affected,
        "mean_non_spike_profile_fraction": mean_non_spike_profile,
        "mean_profile_change": mean_profile_change,
    }


class OptimisationRun:
    def __init__(self, args: argparse.Namespace, cases: list[GalaxyCase]):
        self.args = args
        self.cases = cases
        self.output_dir = args.output_dir
        self.summary_path = self.output_dir / "sep_spike_optimisation_summary.csv"
        self.detail_path = self.output_dir / "sep_spike_optimisation_details.csv"
        self.best_path = self.output_dir / "sep_spike_optimisation_best.json"
        self.evaluation_index = 0
        self.best: dict[str, object] | None = None
        self.total_trials = 0
        self.completed_before_run = 0
        self.trial_durations: list[float] = []
        self.worker_pool: mp.pool.Pool | None = None
        worker_count = min(max(1, int(args.workers)), len(cases))
        if worker_count > 1:
            start_method = "fork" if os.name == "posix" else "spawn"
            context = mp.get_context(start_method)
            self.worker_pool = context.Pool(
                processes=worker_count,
                initializer=initialise_score_worker,
                initargs=(cases, int(args.profile_width_pixels)),
            )
            log(f"Using {worker_count} SEP image workers ({start_method}).")

    def close(self) -> None:
        if self.worker_pool is not None:
            self.worker_pool.close()
            self.worker_pool.join()
            self.worker_pool = None

    def evaluate_params(self, params: dict[str, float | int | str], trial_number: int | None) -> float:
        self.evaluation_index += 1
        started = time.perf_counter()
        detail_rows: list[dict[str, object]] = []
        trial_label = "manual" if trial_number is None else str(trial_number)
        completed_now = self.completed_before_run + self.evaluation_index - 1
        progress_text = f"{completed_now + 1}/{self.total_trials}" if self.total_trials else str(completed_now + 1)
        log(
            f"eval {self.evaluation_index:03d} trial {trial_label} starting ({progress_text}); "
            f"params=thresh={float(params['detect_thresh']):.3f}, minarea={int(params['minarea'])}, "
            f"deblend={int(params['deblend_nthresh'])}/{float(params['deblend_cont']):.5f}, "
            f"back={int(params['back_size'])}, filter={int(params['filter_size'])}, "
            f"dilation={int(params['dilation_radius'])}, max_area={int(params['max_area'])}, "
            f"max_elongation={float(params['max_elongation']):.3f}"
        )
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                if self.worker_pool is None:
                    case_results = []
                    for case in self.cases:
                        case_started = time.perf_counter()
                        row = score_case(case, params, int(self.args.profile_width_pixels))
                        case_results.append((row, time.perf_counter() - case_started))
                else:
                    tasks = [(index, params) for index in range(len(self.cases))]
                    case_results = self.worker_pool.map(score_case_worker, tasks)
                case_rows = [row for row, _case_elapsed in case_results]
                for case_index, (row, case_elapsed) in enumerate(case_results, start=1):
                    case = self.cases[case_index - 1]
                    if self.args.progress_galaxies:
                        log(
                            f"eval {self.evaluation_index:03d} galaxy {case_index}/{len(self.cases)} "
                            f"{case.name}: coverage={float(row['spike_coverage']):.3f}, "
                            f"masked={float(row['masked_fraction']):.3%}, "
                            f"segments={int(row['segments'])}, elapsed={format_duration(case_elapsed)}"
                        )
            aggregate = aggregate_score(
                case_rows,
                max_masked_fraction=float(self.args.max_masked_fraction),
                data_loss_penalty=float(self.args.data_loss_penalty),
                profile_loss_penalty=float(self.args.profile_loss_penalty),
                mean_spike_coverage_weight=float(self.args.mean_spike_coverage_weight),
                min_spike_coverage_weight=float(self.args.min_spike_coverage_weight),
                max_profile_affected_fraction=float(self.args.max_profile_affected_fraction),
                max_non_spike_profile_fraction=float(self.args.max_non_spike_profile_fraction),
                max_bridge_span_arcsec=float(self.args.max_bridge_span_arcsec),
                bridge_span_penalty=float(self.args.bridge_span_penalty),
            )
            objective = float(aggregate["objective"])
            status = "ok"
            error = ""
            detail_rows = [{"evaluation": self.evaluation_index, **row} for row in case_rows]
        except Exception as exc:  # noqa: BLE001
            aggregate = {"objective": 1.0e6}
            objective = 1.0e6
            status = "error"
            error = "".join(traceback.format_exception_only(type(exc), exc)).strip()

        elapsed = time.perf_counter() - started
        self.trial_durations.append(elapsed)
        parameter_values = {name: params[name] for name in OPTIMISED_PARAMETER_NAMES}
        summary = {
            "evaluation": self.evaluation_index,
            "trial_number": "" if trial_number is None else trial_number,
            "status": status,
            "objective": objective,
            "base_objective": aggregate.get("base_objective", math.nan),
            "mean_spike_coverage": aggregate.get("mean_spike_coverage", math.nan),
            "min_spike_coverage": aggregate.get("min_spike_coverage", math.nan),
            "mean_masked_fraction": aggregate.get("mean_masked_fraction", math.nan),
            "max_masked_fraction": aggregate.get("max_masked_fraction", math.nan),
            "max_masked_fraction_limit": aggregate.get("max_masked_fraction_limit", math.nan),
            "masked_fraction_cap_excess": aggregate.get("masked_fraction_cap_excess", math.nan),
            "max_profile_affected_fraction_limit": aggregate.get("max_profile_affected_fraction_limit", math.nan),
            "profile_affected_cap_excess": aggregate.get("profile_affected_cap_excess", math.nan),
            "max_non_spike_profile_fraction_limit": aggregate.get("max_non_spike_profile_fraction_limit", math.nan),
            "non_spike_profile_cap_excess": aggregate.get("non_spike_profile_cap_excess", math.nan),
            "mean_longest_bridge_span_arcsec": aggregate.get("mean_longest_bridge_span_arcsec", math.nan),
            "max_longest_bridge_span_arcsec": aggregate.get("max_longest_bridge_span_arcsec", math.nan),
            "max_bridge_span_arcsec_limit": aggregate.get("max_bridge_span_arcsec_limit", math.nan),
            "bridge_span_cap_excess": aggregate.get("bridge_span_cap_excess", math.nan),
            "mean_profile_affected_fraction": aggregate.get("mean_profile_affected_fraction", math.nan),
            "mean_non_spike_profile_fraction": aggregate.get("mean_non_spike_profile_fraction", math.nan),
            "mean_profile_change": aggregate.get("mean_profile_change", math.nan),
            "mean_gate_recovery": aggregate.get("mean_gate_recovery", math.nan),
            "min_gate_recovery": aggregate.get("min_gate_recovery", math.nan),
            "mean_candidate_detection_rate": aggregate.get("mean_candidate_detection_rate", math.nan),
            "mean_supported_mask_precision": aggregate.get("mean_supported_mask_precision", math.nan),
            "mean_excess_mask_fraction": aggregate.get("mean_excess_mask_fraction", math.nan),
            "mean_protected_galaxy_loss": aggregate.get("mean_protected_galaxy_loss", math.nan),
            "zero_detection_cases": aggregate.get("zero_detection_cases", math.nan),
            "infeasible": aggregate.get("infeasible", math.nan),
            "elapsed_seconds": elapsed,
            "error": error,
            **parameter_values,
        }
        append_csv(
            self.summary_path,
            [summary],
            [
                "evaluation",
                "trial_number",
                "status",
                "objective",
                "base_objective",
                "mean_spike_coverage",
                "min_spike_coverage",
                "mean_masked_fraction",
                "max_masked_fraction",
                "max_masked_fraction_limit",
                "masked_fraction_cap_excess",
                "max_profile_affected_fraction_limit",
                "profile_affected_cap_excess",
                "max_non_spike_profile_fraction_limit",
                "non_spike_profile_cap_excess",
                "mean_longest_bridge_span_arcsec",
                "max_longest_bridge_span_arcsec",
                "max_bridge_span_arcsec_limit",
                "bridge_span_cap_excess",
                "mean_profile_affected_fraction",
                "mean_non_spike_profile_fraction",
                "mean_profile_change",
                "mean_gate_recovery",
                "min_gate_recovery",
                "mean_candidate_detection_rate",
                "mean_supported_mask_precision",
                "mean_excess_mask_fraction",
                "mean_protected_galaxy_loss",
                "zero_detection_cases",
                "infeasible",
                "elapsed_seconds",
                "error",
                *OPTIMISED_PARAMETER_NAMES,
            ],
        )
        if detail_rows:
            append_csv(
                self.detail_path,
                detail_rows,
                [
                    "evaluation",
                    "image",
                    "spike_samples",
                    "covered_spike_samples",
                    "spike_coverage",
                    "masked_pixels",
                    "masked_fraction",
                    "profile_affected_fraction",
                    "non_spike_profile_fraction",
                    "profile_change",
                    "bridged_profile_samples",
                    "longest_bridge_run_samples",
                    "longest_bridge_span_arcsec",
                    "segments",
                    "gate_candidate_count",
                    "recovered_gate_candidates",
                    "gate_target_pixels",
                    "gate_overlap_pixels",
                    "gate_recovery",
                    "candidate_detection_rate",
                    "supported_mask_precision",
                    "excess_mask_fraction",
                    "protected_galaxy_loss",
                    "zero_detection_with_gate",
                    "normalised_bridge_span",
                ],
            )

        if status == "ok" and (self.best is None or objective < float(self.best["objective"])):
            self.best = dict(summary)
            self.best["params"] = params_to_jsonable(params)
            self.best_path.write_text(json.dumps(self.best, indent=2), encoding="utf-8")

        remaining_text = ""
        if self.total_trials:
            completed_after = self.completed_before_run + self.evaluation_index
            remaining_trials = max(0, self.total_trials - completed_after)
            average = float(np.mean(self.trial_durations)) if self.trial_durations else elapsed
            seconds_remaining = remaining_trials * average
            remaining_text = (
                f" remaining={remaining_trials}, rough_eta={format_duration(seconds_remaining)}, "
                f"expected_completion={expected_completion_text(seconds_remaining)}"
            )

        log(
            f"eval {self.evaluation_index:03d}: objective={objective:.5g} "
            f"coverage={float(summary['mean_spike_coverage']):.3f} "
            f"min_coverage={float(summary['min_spike_coverage']):.3f} "
            f"masked={float(summary['mean_masked_fraction']):.3%} "
            f"max_masked={float(summary['max_masked_fraction']):.3%} "
            f"profile_affected={float(summary['mean_profile_affected_fraction']):.3%} "
            f"max_bridge={float(summary['max_longest_bridge_span_arcsec']):.2f}arcsec "
            f"status={status} elapsed={format_duration(elapsed)}{remaining_text}"
        )
        return objective

    def evaluate_trial(self, trial: optuna.Trial) -> float:
        params = optuna_trial_to_params(trial, self.args)
        objective = self.evaluate_params(params, trial.number)
        trial.set_user_attr("best_json", str(self.best_path))
        return objective


def run_optuna(run: OptimisationRun) -> None:
    total_trials = int(run.args.initial_points) + int(run.args.max_iter)
    run.total_trials = total_trials
    sampler = optuna.samplers.TPESampler(seed=int(run.args.seed), n_startup_trials=int(run.args.initial_points))
    storage_url = f"sqlite:///{(run.output_dir / 'sep_spike_optimisation_study.sqlite3').as_posix()}"
    study = optuna.create_study(
        study_name=run.args.study_name,
        direction="minimize",
        sampler=sampler,
        storage=storage_url,
        load_if_exists=True,
    )
    run.completed_before_run = len(study.trials)
    remaining = max(0, total_trials - len(study.trials))
    log(f"Optuna study '{study.study_name}': {len(study.trials)} existing trials, {remaining} new trials.")
    if remaining:
        study.optimize(run.evaluate_trial, n_trials=remaining, gc_after_trial=True, show_progress_bar=False)
    log(f"Best objective={study.best_value:.6g}, params={study.best_params}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    try:
        default_pc = detect_pc(SCRIPT_DIR)
    except RuntimeError:
        default_pc = "Desktop"
    parser.add_argument("--manifest", type=Path, default=sep_tool.DEFAULT_MANIFEST)
    parser.add_argument("--pc", choices=sorted(PC_RESEARCH_FOLDERS), default=default_pc)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--resume-output-dir",
        type=Path,
        help="Resume an existing timestamped SEP optimisation output directory.",
    )
    parser.add_argument("--names", nargs="*", help="Optional explicit galaxy names. Defaults to first usable manifest images.")
    parser.add_argument("--max-images", type=int, default=DEFAULT_MAX_IMAGES)
    parser.add_argument("--require-spikes", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--detect-on",
        choices=["original"],
        default="original",
        help="Image used by SEP for the global segmentation being optimised.",
    )
    parser.add_argument(
        "--spike-gate-detect-on",
        choices=["original", "residual"],
        default="residual",
        help="Image used by Spike Gate to define target bar-profile spike samples.",
    )
    parser.add_argument("--profile-width-pixels", type=int, default=sep_tool.DEFAULT_PROFILE_WIDTH_PIXELS)
    parser.add_argument("--spike-excess-fraction", type=float, default=sep_tool.DEFAULT_SPIKE_EXCESS_FRACTION)
    parser.add_argument("--spike-neighbour-inner-arcsec", type=float, default=sep_tool.DEFAULT_SPIKE_NEIGHBOUR_INNER_ARCSEC)
    parser.add_argument("--spike-neighbour-outer-arcsec", type=float, default=sep_tool.DEFAULT_SPIKE_NEIGHBOUR_OUTER_ARCSEC)
    parser.add_argument("--spike-side-offset-samples", type=int, default=sep_tool.DEFAULT_SPIKE_SIDE_OFFSET_SAMPLES)
    parser.add_argument("--spike-side-drop-fraction", type=float, default=sep_tool.DEFAULT_SPIKE_SIDE_DROP_FRACTION)
    parser.add_argument("--spike-center-exclusion-arcsec", type=float, default=sep_tool.DEFAULT_EXCLUDE_CENTER_PIXELS)
    parser.add_argument("--spike-window-samples", type=int, default=sep_tool.DEFAULT_SPIKE_WINDOW_SAMPLES)
    parser.add_argument("--initial-points", type=int, default=DEFAULT_INITIAL_POINTS)
    parser.add_argument("--max-iter", type=int, default=DEFAULT_MAX_ITER)
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of process workers used to score galaxies within each Optuna trial.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument("--study-name", default=DEFAULT_STUDY_NAME)
    parser.add_argument(
        "--max-masked-fraction",
        type=float,
        default=DEFAULT_MAX_MASKED_FRACTION,
        help="Hard worst-galaxy masked-fraction ceiling for a trial.",
    )
    parser.add_argument(
        "--data-loss-penalty",
        type=float,
        default=DEFAULT_DATA_LOSS_PENALTY,
        help="Penalty weight applied to mean image masked fraction.",
    )
    parser.add_argument(
        "--profile-loss-penalty",
        type=float,
        default=DEFAULT_PROFILE_LOSS_PENALTY,
        help="Penalty weight applied to non-spike/profile masking.",
    )
    parser.add_argument(
        "--mean-spike-coverage-weight",
        type=float,
        default=DEFAULT_MEAN_SPIKE_COVERAGE_WEIGHT,
        help="Objective weight for average Spike Gate sample coverage.",
    )
    parser.add_argument(
        "--min-spike-coverage-weight",
        type=float,
        default=DEFAULT_MIN_SPIKE_COVERAGE_WEIGHT,
        help="Objective weight for worst-galaxy Spike Gate sample coverage.",
    )
    parser.add_argument(
        "--max-profile-affected-fraction",
        type=float,
        default=DEFAULT_MAX_PROFILE_AFFECTED_FRACTION,
        help="Soft hard cap for mean bar-profile samples affected by the mask.",
    )
    parser.add_argument(
        "--max-non-spike-profile-fraction",
        type=float,
        default=DEFAULT_MAX_NON_SPIKE_PROFILE_FRACTION,
        help="Soft hard cap for non-spike bar-profile samples affected by the mask.",
    )
    parser.add_argument(
        "--max-bridge-span-arcsec",
        type=float,
        default=DEFAULT_MAX_BRIDGE_SPAN_ARCSEC,
        help="Soft hard cap for the longest single log-linear bridge span in any optimisation galaxy.",
    )
    parser.add_argument(
        "--bridge-span-penalty",
        type=float,
        default=DEFAULT_BRIDGE_SPAN_PENALTY,
        help="Penalty weight applied to mean longest bridge span in arcsec.",
    )
    parser.add_argument(
        "--max-area-search",
        type=int,
        default=DEFAULT_MAX_AREA_SEARCH,
        help="Upper bound for the Optuna max_area search range.",
    )
    parser.add_argument(
        "--detect-thresh-min",
        type=float,
        default=DEFAULT_DETECT_THRESH_MIN,
        help="Lower bound for the Optuna detect_thresh search range.",
    )
    parser.add_argument(
        "--detect-thresh-max",
        type=float,
        default=DEFAULT_DETECT_THRESH_MAX,
        help="Upper bound for the Optuna detect_thresh search range.",
    )
    parser.add_argument(
        "--minarea-min",
        type=int,
        default=DEFAULT_MINAREA_MIN,
        help="Lower bound for the Optuna minarea search range.",
    )
    parser.add_argument(
        "--minarea-max",
        type=int,
        default=DEFAULT_MINAREA_MAX,
        help="Upper bound for the Optuna minarea search range.",
    )
    parser.add_argument(
        "--dilation-radius-min",
        type=int,
        default=DEFAULT_DILATION_RADIUS_MIN,
        help="Lower bound for the Optuna dilation_radius search range.",
    )
    parser.add_argument(
        "--dilation-radius-max",
        type=int,
        default=DEFAULT_DILATION_RADIUS_MAX,
        help="Upper bound for the Optuna dilation_radius search range.",
    )
    parser.add_argument(
        "--results-workbook",
        type=Path,
        default=None,
        help="Optional shared XLSX workbook to append this run's trial results to.",
    )
    parser.add_argument("--progress-galaxies", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--prepare-only", action="store_true", help="Build cases and write config, but do not optimise.")
    args = parser.parse_args()
    if args.detect_thresh_min > args.detect_thresh_max:
        parser.error("--detect-thresh-min must be <= --detect-thresh-max")
    if args.minarea_min > args.minarea_max:
        parser.error("--minarea-min must be <= --minarea-max")
    if args.dilation_radius_min > args.dilation_radius_max:
        parser.error("--dilation-radius-min must be <= --dilation-radius-max")
    if args.minarea_min < 1:
        parser.error("--minarea-min must be >= 1")
    if args.dilation_radius_min < 0:
        parser.error("--dilation-radius-min must be >= 0")
    return args


def prepare_output_dir(args: argparse.Namespace) -> None:
    if args.resume_output_dir is not None:
        args.output_dir = args.resume_output_dir
        if not args.output_dir.is_dir():
            raise FileNotFoundError(f"Cannot resume because output directory does not exist: {args.output_dir}")
        study_path = args.output_dir / "sep_spike_optimisation_study.sqlite3"
        if not study_path.is_file() and not args.prepare_only:
            raise FileNotFoundError(f"Cannot resume because Optuna study database does not exist: {study_path}")
        return

    output_parent = args.output_dir or (remove_foreground_folder(args.pc) / "sep spike optimisation")
    timestamp_dir = datetime.now().strftime("%Y%m%d_%H%M%S")
    args.output_dir = output_parent / timestamp_dir
    args.output_dir.mkdir(parents=True, exist_ok=True)


def write_run_config(args: argparse.Namespace) -> None:
    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    config_path = args.output_dir / "sep_spike_optimisation_config.json"
    if args.resume_output_dir is not None and config_path.exists():
        (args.output_dir / "sep_spike_optimisation_resume_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
        return
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def write_cases(path: Path, cases: list[GalaxyCase], append: bool) -> None:
    if append:
        return
    rows = [
        {
            "image": case.name,
            "spike_samples": int(np.count_nonzero(case.spike_samples)),
            "profile_samples": int(case.spike_samples.size),
        }
        for case in cases
    ]
    append_csv(path, rows, ["image", "spike_samples", "profile_samples"])


def main() -> None:
    args = parse_args()
    prepare_output_dir(args)
    write_run_config(args)
    cases = build_cases(args)
    write_cases(args.output_dir / "sep_spike_optimisation_cases.csv", cases, append=args.resume_output_dir is not None)
    log(f"Prepared {len(cases)} galaxies. Output: {args.output_dir}")
    if args.prepare_only:
        return

    run = OptimisationRun(args, cases)
    try:
        run_optuna(run)
    finally:
        run.close()
    log(f"Best result: {run.best_path}")
    if os.name != "nt" and args.results_workbook is None:
        log("Results workbook: skipped on non-Windows host (pass --results-workbook to enable).")
        return
    try:
        workbook_path = append_run_to_workbook(
            algorithm="SEP",
            method="Spike Gate",
            run_dir=args.output_dir,
            prefix="sep_spike_optimisation",
            workbook_path=args.results_workbook,
        )
        log(f"Results workbook: {workbook_path}")
    except Exception as exc:
        log(f"Could not update results workbook: {exc}")


if __name__ == "__main__":
    main()
