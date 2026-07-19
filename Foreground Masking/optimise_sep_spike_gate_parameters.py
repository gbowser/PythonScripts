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
from pathlib import Path
import sys
import time
import traceback
import warnings

import numpy as np
import optuna


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
for path in (SCRIPT_DIR, PROJECT_ROOT):
    if str(path) not in sys.path:
        sys.path.append(str(path))

import interactive_sep_spike_gate_parameter_tester as sep_tool  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, remove_foreground_folder  # noqa: E402


DEFAULT_OUTPUT_DIR = remove_foreground_folder("Desktop") / "sep spike optimisation"
DEFAULT_MAX_IMAGES = 20
DEFAULT_INITIAL_POINTS = 16
DEFAULT_MAX_ITER = 64
DEFAULT_RANDOM_SEED = 20260719
DEFAULT_STUDY_NAME = "sep-spike-gate-optimisation"
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


def default_params(detect_on: str) -> dict[str, float | int | str]:
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


def optuna_trial_to_params(trial: optuna.Trial, detect_on: str) -> dict[str, float | int | str]:
    params = default_params(detect_on)
    params["detect_thresh"] = trial.suggest_float("detect_thresh", 0.5, 8.0)
    params["minarea"] = trial.suggest_int("minarea", 1, 80)
    params["deblend_nthresh"] = trial.suggest_int("deblend_nthresh", 8, 64)
    params["deblend_cont"] = trial.suggest_float("deblend_cont", 0.0001, 0.1, log=True)
    params["back_size"] = trial.suggest_categorical("back_size", [16, 24, 32, 48, 64, 96, 128, 192, 256])
    params["filter_size"] = trial.suggest_categorical("filter_size", [1, 3, 5, 7, 9])
    params["dilation_radius"] = trial.suggest_int("dilation_radius", 0, 8)
    params["max_area"] = trial.suggest_int("max_area", 20, 5000)
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


def select_rows(manifest: Path, pc_name: str, names: list[str] | None, max_images: int) -> list[dict[str, str]]:
    rows = sep_tool.display.rows_with_images_for_pc(sep_tool.display.read_manifest(manifest), pc_name)
    if names:
        wanted = {name.casefold() for name in names}
        rows = [row for row in rows if row["name"].casefold() in wanted]

    selected = []
    for row in rows:
        if sep_tool.display.required_geometry(row) is not None:
            selected.append(row)
        if len(selected) >= max_images:
            break
    if not selected:
        raise ValueError("No usable science images found for the requested PC/name selection.")
    return selected


def spike_profile_for_case(
    data: np.ndarray,
    geometry: dict[str, float],
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    radius_arcsec = sep_tool.display.profile_radius_pixels(data, geometry) * geometry["pixel_scale"]
    original_view, x_axis, y_axis = sep_tool.display.deproject_bar_aligned_cutout(data, geometry, radius_arcsec)
    half_width = 0.5 * int(args.profile_width_pixels) * geometry["pixel_scale"]
    radii, intensity = sep_tool.display.bar_major_axis_profile(original_view, x_axis, y_axis, half_width)
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
    rows = select_rows(args.manifest, args.pc, args.names, row_limit)
    for row in rows:
        name = row["name"]
        geometry = sep_tool.display.required_geometry(row)
        if geometry is None:
            continue
        data, _header = sep_tool.load_fits(sep_tool.display.image_path_for_pc(row, args.pc))
        radii, profile, spikes = spike_profile_for_case(data, geometry, args)
        spike_count = int(np.count_nonzero(spikes))
        if spike_count == 0 and args.require_spikes:
            log(f"Skipping {name}: Spike Gate found no spike samples.")
            continue
        cases.append(GalaxyCase(name, data, geometry, radii, profile, spikes))
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
    mask = np.asarray(products["mask"], dtype=bool)
    profile_mask = profile_mask_for_image_mask(case.data, mask, case.geometry, profile_width_pixels)

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
    return {
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
    }


def aggregate_score(case_rows: list[dict[str, float | int | str]]) -> dict[str, float]:
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
        self.output_dir = args.output_dir
        self.summary_path = self.output_dir / "sep_spike_optimisation_summary.csv"
        self.detail_path = self.output_dir / "sep_spike_optimisation_details.csv"
        self.best_path = self.output_dir / "sep_spike_optimisation_best.json"
        self.evaluation_index = 0
        self.best: dict[str, object] | None = None
        self.total_trials = 0
        self.completed_before_run = 0
        self.trial_durations: list[float] = []

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
                case_rows = []
                for case_index, case in enumerate(self.cases, start=1):
                    case_started = time.perf_counter()
                    row = score_case(case, params, int(self.args.profile_width_pixels))
                    case_rows.append(row)
                    if self.args.progress_galaxies:
                        case_elapsed = time.perf_counter() - case_started
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
                "mean_spike_coverage",
                "mean_masked_fraction",
                "mean_profile_affected_fraction",
                "mean_non_spike_profile_fraction",
                "mean_profile_change",
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
                    "segments",
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
            remaining_text = f" remaining={remaining_trials}, rough_eta={format_duration(remaining_trials * average)}"

        log(
            f"eval {self.evaluation_index:03d}: objective={objective:.5g} "
            f"coverage={float(summary['mean_spike_coverage']):.3f} "
            f"masked={float(summary['mean_masked_fraction']):.3%} "
            f"status={status} elapsed={format_duration(elapsed)}{remaining_text}"
        )
        return objective

    def evaluate_trial(self, trial: optuna.Trial) -> float:
        params = optuna_trial_to_params(trial, self.args.detect_on)
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
    parser.add_argument("--manifest", type=Path, default=sep_tool.DEFAULT_MANIFEST)
    parser.add_argument("--pc", choices=sorted(PC_RESEARCH_FOLDERS), default=sep_tool.DEFAULT_PC)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--resume-output-dir",
        type=Path,
        help="Resume an existing timestamped SEP optimisation output directory.",
    )
    parser.add_argument("--names", nargs="*", help="Optional explicit galaxy names. Defaults to first usable manifest images.")
    parser.add_argument("--max-images", type=int, default=DEFAULT_MAX_IMAGES)
    parser.add_argument("--require-spikes", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--detect-on", choices=["original", "residual"], default="residual")
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
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument("--study-name", default=DEFAULT_STUDY_NAME)
    parser.add_argument("--progress-galaxies", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--prepare-only", action="store_true", help="Build cases and write config, but do not optimise.")
    return parser.parse_args()


def prepare_output_dir(args: argparse.Namespace) -> None:
    if args.resume_output_dir is not None:
        args.output_dir = args.resume_output_dir
        if not args.output_dir.is_dir():
            raise FileNotFoundError(f"Cannot resume because output directory does not exist: {args.output_dir}")
        study_path = args.output_dir / "sep_spike_optimisation_study.sqlite3"
        if not study_path.is_file() and not args.prepare_only:
            raise FileNotFoundError(f"Cannot resume because Optuna study database does not exist: {study_path}")
        return

    timestamp_dir = datetime.now().strftime("%Y%m%d_%H%M%S")
    args.output_dir = args.output_dir / timestamp_dir
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
    run_optuna(run)
    log(f"Best result: {run.best_path}")


if __name__ == "__main__":
    main()
