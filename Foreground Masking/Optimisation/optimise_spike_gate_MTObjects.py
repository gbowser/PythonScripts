#!/usr/bin/env python3
"""Optimise global MTObjects parameters against Spike Gate profile evidence.

Spike Gate supplies the target: narrow positive bar-major profile spikes that
should be covered by the foreground mask. MTObjects supplies the mask itself.
Optuna searches for MTObjects parameters that cover those spike samples while
keeping masked image/profile fractions small.
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

import mtobjects_spike_gate_processing as mto  # noqa: E402
import spike_gate_objective as gate_objective  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, detect_pc, remove_foreground_folder  # noqa: E402
from optimisation_results_workbook import append_run_to_workbook  # noqa: E402


DEFAULT_MAX_IMAGES = 20
DEFAULT_INITIAL_POINTS = 12
DEFAULT_MAX_ITER = 48
DEFAULT_RANDOM_SEED = 20260719
DEFAULT_STUDY_NAME = "mtobjects-spike-gate-optimisation"
OPTIMISED_PARAMETER_NAMES = [
    "move_factor",
    "min_distance",
    "gaussian_fwhm",
    "bg_variance",
    "minarea",
    "dilation_radius",
    "max_area",
    "max_elongation",
]
DEFAULT_BG_VARIANCE_MIN = 0.001
DEFAULT_BG_VARIANCE_MAX = 100.0
DEFAULT_BG_VARIANCE_STEP = 0.0001


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
    spike_gate_detect_on: str


_WORKER_CASES: list[GalaxyCase] | None = None
_WORKER_MTOBJECTS_ROOT: Path | None = None
_WORKER_PROFILE_WIDTH_PIXELS = 0


def initialise_score_worker(
    cases: list[GalaxyCase], mtobjects_root: Path | None, profile_width_pixels: int
) -> None:
    global _WORKER_CASES, _WORKER_MTOBJECTS_ROOT, _WORKER_PROFILE_WIDTH_PIXELS
    _WORKER_CASES = cases
    _WORKER_MTOBJECTS_ROOT = mtobjects_root
    _WORKER_PROFILE_WIDTH_PIXELS = int(profile_width_pixels)


def score_case_worker(
    task: tuple[int, dict[str, float | int | str]],
) -> tuple[dict[str, float | int | str], float]:
    case_index, params = task
    if _WORKER_CASES is None:
        raise RuntimeError("MTObjects Spike Gate scoring worker was not initialised.")
    started = time.perf_counter()
    row = score_case(
        _WORKER_CASES[case_index],
        params,
        _WORKER_MTOBJECTS_ROOT,
        _WORKER_PROFILE_WIDTH_PIXELS,
    )
    return row, time.perf_counter() - started


def default_params(detect_on: str, spike_gate_detect_on: str) -> dict[str, float | int | str]:
    if detect_on != "original":
        raise ValueError("MTObjects Spike Gate optimisation must operate on the original science image.")
    return {
        "detect_on": detect_on,
        "spike_gate_detect_on": spike_gate_detect_on,
        "alpha": mto.DEFAULT_ALPHA,
        "move_factor": mto.DEFAULT_MOVE_FACTOR,
        "min_distance": mto.DEFAULT_MIN_DISTANCE,
        "gaussian_fwhm": mto.DEFAULT_GAUSSIAN_FWHM,
        "soft_bias": mto.DEFAULT_SOFT_BIAS,
        "gain": mto.DEFAULT_GAIN,
        "bg_mean": mto.DEFAULT_BG_MEAN,
        "bg_variance": mto.DEFAULT_BG_VARIANCE,
        "minarea": mto.DEFAULT_MINAREA,
        "dilation_radius": mto.DEFAULT_DILATION_RADIUS,
        "max_area": mto.DEFAULT_MAX_AREA,
        "max_elongation": mto.DEFAULT_MAX_ELONGATION,
        "exclude_center_pixels": mto.DEFAULT_EXCLUDE_CENTER_PIXELS,
        "spike_gate_move_factor": mto.SPIKE_GATE_MOVE_FACTOR,
        "spike_excess_fraction": mto.DEFAULT_SPIKE_EXCESS_FRACTION,
        "spike_neighbour_inner_arcsec": mto.DEFAULT_SPIKE_NEIGHBOUR_INNER_ARCSEC,
        "spike_neighbour_outer_arcsec": mto.DEFAULT_SPIKE_NEIGHBOUR_OUTER_ARCSEC,
        "spike_side_offset_samples": mto.DEFAULT_SPIKE_SIDE_OFFSET_SAMPLES,
        "spike_side_drop_fraction": mto.DEFAULT_SPIKE_SIDE_DROP_FRACTION,
        "spike_window_samples": mto.DEFAULT_SPIKE_WINDOW_SAMPLES,
    }


def suggest_bg_variance(trial: optuna.Trial, args: argparse.Namespace) -> float:
    minimum = float(args.bg_variance_min)
    maximum = float(args.bg_variance_max)
    step = float(args.bg_variance_step)
    if minimum == maximum:
        return minimum
    if step <= 0:
        return trial.suggest_float("bg_variance", minimum, maximum, log=True)
    return trial.suggest_float("bg_variance", minimum, maximum, step=step)


def optuna_trial_to_params(trial: optuna.Trial, args: argparse.Namespace) -> dict[str, float | int | str]:
    params = default_params(args.detect_on, args.spike_gate_detect_on)
    params["move_factor"] = trial.suggest_float("move_factor", 0.05, 0.95)
    params["min_distance"] = trial.suggest_float("min_distance", 0.0, 1.0)
    params["gaussian_fwhm"] = trial.suggest_float("gaussian_fwhm", 0.0, 5.0)
    params["bg_variance"] = suggest_bg_variance(trial, args)
    params["minarea"] = trial.suggest_int("minarea", 1, 100)
    params["dilation_radius"] = trial.suggest_int("dilation_radius", 0, 8)
    params["max_area"] = trial.suggest_int("max_area", 20, 5000)
    params["max_elongation"] = trial.suggest_float("max_elongation", 1.5, 25.0)
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
    rows = mto.display.rows_with_images_for_pc(mto.display.read_manifest(manifest), pc_name)
    if names:
        wanted = {name.casefold() for name in names}
        rows = [row for row in rows if row["name"].casefold() in wanted]

    selected = []
    for row in rows:
        if mto.display.required_geometry(row) is not None:
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
    radius_arcsec = mto.display.profile_radius_pixels(data, geometry) * geometry["pixel_scale"]
    original_view, x_axis, y_axis = mto.display.deproject_bar_aligned_cutout(data, geometry, radius_arcsec)
    if args.spike_gate_detect_on == "residual":
        spike_gate_image, _residual, _nonfinite = mto.prepare_detection_image(data, "residual")
    else:
        spike_gate_image = data
    spike_gate_view, _spike_x_axis, _spike_y_axis = mto.display.deproject_bar_aligned_cutout(
        spike_gate_image,
        geometry,
        radius_arcsec,
    )
    half_width = 0.5 * int(args.profile_width_pixels) * geometry["pixel_scale"]
    radii, original_intensity = mto.display.bar_major_axis_profile(original_view, x_axis, y_axis, half_width)
    _spike_radii, spike_gate_intensity = mto.display.bar_major_axis_profile(spike_gate_view, x_axis, y_axis, half_width)
    spikes = mto.detect_profile_spikes(
        radii,
        spike_gate_intensity,
        excess_fraction=float(args.spike_excess_fraction),
        neighbour_inner_arcsec=float(args.spike_neighbour_inner_arcsec),
        neighbour_outer_arcsec=float(args.spike_neighbour_outer_arcsec),
        side_offset_samples=int(args.spike_side_offset_samples),
        side_drop_fraction=float(args.spike_side_drop_fraction),
        center_exclusion_arcsec=float(args.spike_center_exclusion_arcsec),
    )
    spikes = mto.expand_boolean_mask(spikes, int(args.spike_window_samples))
    return radii, original_intensity, spikes


def build_cases(args: argparse.Namespace) -> list[GalaxyCase]:
    cases: list[GalaxyCase] = []
    row_limit = int(args.max_images) if not args.require_spikes else sys.maxsize
    rows = select_rows(args.manifest, args.pc, args.names, row_limit, int(args.seed))
    for row in rows:
        name = row["name"]
        geometry = mto.display.required_geometry(row)
        if geometry is None:
            continue
        data, _header = mto.load_fits(mto.display.image_path_for_pc(row, args.pc))
        radii, profile, spikes = spike_profile_for_case(data, geometry, args)
        spike_count = int(np.count_nonzero(spikes))
        if spike_count == 0 and args.require_spikes:
            log(f"Skipping {name}: Spike Gate found no spike samples.")
            continue
        cases.append(GalaxyCase(name, data, geometry, radii, profile, spikes, args.spike_gate_detect_on))
        log(f"Prepared {name}: {spike_count} Spike Gate samples.")
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
    radius_arcsec = mto.display.profile_radius_pixels(data, geometry) * geometry["pixel_scale"]
    mask_view, _x_axis, y_axis = mto.display.deproject_bar_aligned_cutout(mask.astype(float), geometry, radius_arcsec, order=0)
    mask_view = np.isfinite(mask_view) & (mask_view > 0.5)
    half_width = 0.5 * int(profile_width_pixels) * geometry["pixel_scale"]
    return mto.profile_mask_at_bar_major(mask_view, y_axis, half_width)


def score_case(
    case: GalaxyCase,
    params: dict[str, float | int | str],
    mtobjects_root: Path | None,
    profile_width_pixels: int,
) -> dict[str, float | int | str]:
    products = mto.mtobjects_products(case.data, params, case.geometry, mtobjects_root)
    radius_arcsec = mto.display.profile_radius_pixels(case.data, case.geometry) * case.geometry["pixel_scale"]
    raw_mask = np.asarray(products["mask"], dtype=bool)
    _raw_view, x_axis, y_axis = mto.display.deproject_bar_aligned_cutout(
        raw_mask.astype(float), case.geometry, radius_arcsec, order=0
    )
    half_width = 0.5 * int(profile_width_pixels) * case.geometry["pixel_scale"]
    def labels_to_view(component_labels: np.ndarray) -> np.ndarray:
        view, _x, _y = mto.display.deproject_bar_aligned_cutout(
            component_labels.astype(float), case.geometry, radius_arcsec, order=0
        )
        return np.where(np.isfinite(view), view, 0.0)
    mask, component_metrics = gate_objective.retain_gate_supported_components(
        raw_mask, labels_to_view, x_axis, y_axis, case.spike_samples, half_width
    )
    profile_mask = profile_mask_for_image_mask(case.data, mask, case.geometry, profile_width_pixels)
    mask_view, _x_axis, _y_axis = mto.display.deproject_bar_aligned_cutout(
        mask.astype(float), case.geometry, radius_arcsec, order=0
    )
    mask_view = np.isfinite(mask_view) & (mask_view > 0.5)
    bar_sma = mto.display.bar_sma_deprojected_arcsec(case.geometry)
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
    bridged_profile, replaced = mto.fill_profile_with_log_linear_bridges(case.original_profile, profile_mask)
    finite = np.isfinite(case.original_profile) & np.isfinite(bridged_profile) & (case.original_profile > 0) & (bridged_profile > 0)
    profile_change = 0.0
    if np.count_nonzero(finite) >= 5:
        profile_change = float(np.nanmedian(np.abs(np.log10(bridged_profile[finite]) - np.log10(case.original_profile[finite]))))
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
        "segments": len(products["rows"]),
        "normalised_bridge_span": 0.0,
    }
    result.update(gate_metrics)
    result.update(component_metrics)
    return result


def aggregate_score(case_rows: list[dict[str, float | int | str]]) -> dict[str, float]:
    constrained = gate_objective.aggregate_constrained(case_rows)
    if "mean_gate_recovery" in constrained:
        return constrained
    spike_rows = [row for row in case_rows if int(row["spike_samples"]) > 0]
    rows_for_coverage = spike_rows if spike_rows else case_rows
    mean_spike_coverage = float(np.mean([float(row["spike_coverage"]) for row in rows_for_coverage]))
    mean_masked_fraction = float(np.mean([float(row["masked_fraction"]) for row in case_rows]))
    mean_profile_affected = float(np.mean([float(row["profile_affected_fraction"]) for row in case_rows]))
    mean_non_spike_profile = float(np.mean([float(row["non_spike_profile_fraction"]) for row in case_rows]))
    mean_profile_change = float(np.mean([float(row["profile_change"]) for row in case_rows]))
    objective = (
        12.0 * (1.0 - mean_spike_coverage)
        + 4.0 * mean_non_spike_profile
        + 2.0 * mean_masked_fraction
        + 1.5 * mean_profile_affected
        + 1.0 * mean_profile_change
    )
    return {
        "objective": objective,
        "mean_spike_coverage": mean_spike_coverage,
        "mean_masked_fraction": mean_masked_fraction,
        "mean_profile_affected_fraction": mean_profile_affected,
        "mean_non_spike_profile_fraction": mean_non_spike_profile,
        "mean_profile_change": mean_profile_change,
    }


class OptimisationRun:
    def __init__(self, args: argparse.Namespace, cases: list[GalaxyCase]):
        self.args = args
        self.cases = cases
        self.mtobjects_root = mto.find_mtobjects_root(args.mtobjects_root)
        self.output_dir = args.output_dir
        self.summary_path = self.output_dir / "mtobjects_spike_optimisation_summary.csv"
        self.detail_path = self.output_dir / "mtobjects_spike_optimisation_details.csv"
        self.best_path = self.output_dir / "mtobjects_spike_optimisation_best.json"
        self.evaluation_index = 0
        self.best: dict[str, object] | None = None
        self.total_trials = 0
        self.completed_before_run = 0
        self.run_started = time.perf_counter()
        self.trial_durations: list[float] = []
        self.worker_pool: mp.pool.Pool | None = None
        worker_count = min(max(1, int(args.workers)), len(cases))
        if worker_count > 1:
            start_method = "fork" if os.name == "posix" else "spawn"
            context = mp.get_context(start_method)
            self.worker_pool = context.Pool(
                processes=worker_count,
                initializer=initialise_score_worker,
                initargs=(cases, self.mtobjects_root, int(args.profile_width_pixels)),
            )
            log(f"Using {worker_count} MTObjects image workers ({start_method}).")

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
        if self.total_trials:
            progress_text = f"{completed_now + 1}/{self.total_trials}"
        else:
            progress_text = str(completed_now + 1)
        log(
            f"eval {self.evaluation_index:03d} trial {trial_label} starting "
            f"({progress_text}); params="
            f"move={float(params['move_factor']):.3f}, min_distance={float(params['min_distance']):.3f}, "
            f"gaussian_fwhm={float(params['gaussian_fwhm']):.3f}, "
            f"bg_variance={float(params['bg_variance']):.8f}, minarea={int(params['minarea'])}, "
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
                        row = score_case(case, params, self.mtobjects_root, int(self.args.profile_width_pixels))
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
            aggregate = aggregate_score(case_rows)
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
            "mean_spike_coverage": aggregate.get("mean_spike_coverage", math.nan),
            "mean_masked_fraction": aggregate.get("mean_masked_fraction", math.nan),
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
            "detect_on": params["detect_on"],
            "spike_gate_detect_on": params["spike_gate_detect_on"],
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
                "mean_spike_coverage",
                "mean_masked_fraction",
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
                "detect_on",
                "spike_gate_detect_on",
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
            eta = format_duration(seconds_remaining)
            remaining_text = (
                f" remaining={remaining_trials}, rough_eta={eta}, "
                f"expected_completion={expected_completion_text(seconds_remaining)}"
            )

        log(
            f"eval {self.evaluation_index:03d}: objective={objective:.5g} "
            f"coverage={float(summary['mean_spike_coverage']):.3f} "
            f"masked={float(summary['mean_masked_fraction']):.3%} "
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
    storage_url = f"sqlite:///{(run.output_dir / 'mtobjects_spike_optimisation_study.sqlite3').as_posix()}"
    study = optuna.create_study(
        study_name=run.args.study_name,
        direction="minimize",
        sampler=sampler,
        storage=storage_url,
        load_if_exists=True,
    )
    run.completed_before_run = len(study.trials)
    remaining = max(0, total_trials - len(study.trials))
    log(
        f"Optuna study '{study.study_name}': {len(study.trials)} existing trials, "
        f"{remaining} new trials."
    )
    if remaining:
        study.optimize(run.evaluate_trial, n_trials=remaining, gc_after_trial=True, show_progress_bar=False)
    log(f"Best objective={study.best_value:.6g}, params={study.best_params}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    try:
        default_pc = detect_pc(SCRIPT_DIR)
    except RuntimeError:
        default_pc = "Desktop"
    parser.add_argument("--manifest", type=Path, default=mto.DEFAULT_MANIFEST)
    parser.add_argument("--pc", choices=sorted(PC_RESEARCH_FOLDERS), default=default_pc)
    parser.add_argument("--mtobjects-root", type=Path, default=Path(mto.DEFAULT_MTOBJECTS_ROOT) if mto.DEFAULT_MTOBJECTS_ROOT else None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument(
        "--resume-output-dir",
        type=Path,
        help=(
            "Resume an existing timestamped optimisation output directory. "
            "The existing Optuna SQLite study is reused and only missing trials are run."
        ),
    )
    parser.add_argument("--names", nargs="*", help="Optional explicit galaxy names. Defaults to first usable manifest images.")
    parser.add_argument("--max-images", type=int, default=DEFAULT_MAX_IMAGES)
    parser.add_argument("--require-spikes", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--mtobjects-detect-on",
        "--detect-on",
        dest="detect_on",
        choices=["original"],
        default="original",
        help=(
            "Image MTObjects uses for the optimised foreground-mask pass. "
            "The older --detect-on spelling is kept as an alias."
        ),
    )
    parser.add_argument(
        "--spike-gate-detect-on",
        choices=["original", "residual"],
        default="original",
        help="Image used to find Spike Gate profile samples before optimisation.",
    )
    parser.add_argument("--profile-width-pixels", type=int, default=mto.DEFAULT_PROFILE_WIDTH_PIXELS)
    parser.add_argument("--spike-excess-fraction", type=float, default=mto.DEFAULT_SPIKE_EXCESS_FRACTION)
    parser.add_argument("--spike-neighbour-inner-arcsec", type=float, default=mto.DEFAULT_SPIKE_NEIGHBOUR_INNER_ARCSEC)
    parser.add_argument("--spike-neighbour-outer-arcsec", type=float, default=mto.DEFAULT_SPIKE_NEIGHBOUR_OUTER_ARCSEC)
    parser.add_argument("--spike-side-offset-samples", type=int, default=mto.DEFAULT_SPIKE_SIDE_OFFSET_SAMPLES)
    parser.add_argument("--spike-side-drop-fraction", type=float, default=mto.DEFAULT_SPIKE_SIDE_DROP_FRACTION)
    parser.add_argument("--spike-center-exclusion-arcsec", type=float, default=mto.DEFAULT_EXCLUDE_CENTER_PIXELS)
    parser.add_argument("--spike-window-samples", type=int, default=mto.DEFAULT_SPIKE_WINDOW_SAMPLES)
    parser.add_argument("--initial-points", type=int, default=DEFAULT_INITIAL_POINTS)
    parser.add_argument("--max-iter", type=int, default=DEFAULT_MAX_ITER)
    parser.add_argument("--bg-variance-min", type=float, default=DEFAULT_BG_VARIANCE_MIN)
    parser.add_argument("--bg-variance-max", type=float, default=DEFAULT_BG_VARIANCE_MAX)
    parser.add_argument(
        "--bg-variance-step",
        type=float,
        default=DEFAULT_BG_VARIANCE_STEP,
        help="Optuna discretisation for bg_variance; use 0 for continuous float sampling.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of process workers used to score galaxies within each Optuna trial.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument("--study-name", default=DEFAULT_STUDY_NAME)
    parser.add_argument(
        "--results-workbook",
        type=Path,
        default=None,
        help="Optional shared XLSX workbook to append this run's trial results to.",
    )
    parser.add_argument(
        "--progress-galaxies",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Print timestamped per-galaxy progress inside each Optuna trial.",
    )
    parser.add_argument("--prepare-only", action="store_true", help="Build cases and write config, but do not optimise.")
    return parser.parse_args()


def prepare_output_dir(args: argparse.Namespace) -> None:
    if args.resume_output_dir is not None:
        args.output_dir = args.resume_output_dir
        if not args.output_dir.is_dir():
            raise FileNotFoundError(f"Cannot resume because output directory does not exist: {args.output_dir}")
        study_path = args.output_dir / "mtobjects_spike_optimisation_study.sqlite3"
        if not study_path.is_file() and not args.prepare_only:
            raise FileNotFoundError(f"Cannot resume because Optuna study database does not exist: {study_path}")
        return

    output_parent = args.output_dir or (remove_foreground_folder(args.pc) / "mtobjects spike optimisation")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    args.output_dir = output_parent / timestamp
    args.output_dir.mkdir(parents=True, exist_ok=True)


def write_run_config(args: argparse.Namespace) -> None:
    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    config_path = args.output_dir / "mtobjects_spike_optimisation_config.json"
    if args.resume_output_dir is not None and config_path.exists():
        resume_config_path = args.output_dir / "mtobjects_spike_optimisation_resume_config.json"
        resume_config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def write_cases(path: Path, cases: list[GalaxyCase], append: bool) -> None:
    if append:
        return
    case_rows = [
        {
            "image": case.name,
            "spike_samples": int(np.count_nonzero(case.spike_samples)),
            "profile_samples": int(case.spike_samples.size),
            "spike_gate_detect_on": case.spike_gate_detect_on,
        }
        for case in cases
    ]
    append_csv(path, case_rows, ["image", "spike_samples", "profile_samples", "spike_gate_detect_on"])


def main() -> None:
    args = parse_args()
    prepare_output_dir(args)
    write_run_config(args)

    cases = build_cases(args)
    write_cases(
        args.output_dir / "mtobjects_spike_optimisation_cases.csv",
        cases,
        append=args.resume_output_dir is not None,
    )
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
            algorithm="MTObjects",
            method="Spike Gate",
            run_dir=args.output_dir,
            prefix="mtobjects_spike_optimisation",
            workbook_path=args.results_workbook,
        )
        log(f"Results workbook: {workbook_path}")
    except Exception as exc:
        log(f"Could not update results workbook: {exc}")


if __name__ == "__main__":
    main()
