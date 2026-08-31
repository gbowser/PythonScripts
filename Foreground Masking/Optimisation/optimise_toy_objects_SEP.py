#!/usr/bin/env python3
"""Optimise SEP parameters using injected toy-object recovery.

This follows the same broad idea as Haigh et al. (2021): create data with a
known truth, run a source-extraction tool, score the segmentation, and let a
black-box optimiser choose better parameters. Here the known truth is a set of
synthetic compact foreground/background objects injected into local S4G science
images.
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
import paired_toy_common

# The optimiser prints its own concise trial progress and ETA.  Suppress
# Optuna's duplicate INFO records, which PowerShell renders as red stderr and
# misleading NativeCommandError messages even when trials succeed.
optuna.logging.set_verbosity(optuna.logging.WARNING)

SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
SUPPORT_DIRS = tuple(FOREGROUND_ROOT / name for name in ("Batch tools", "PhotUtils", "Interactive tools", "Shared", "Utilities"))
for path in (PROJECT_ROOT, FOREGROUND_ROOT, SCRIPT_DIR, *SUPPORT_DIRS):
    if str(path) not in sys.path:
        sys.path.append(str(path))

if os.name != "nt":
    os.environ.setdefault("FOREGROUND_MASKING_PC", "Desktop")

import sep_processing as sep_tool  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, detect_pc, remove_foreground_folder  # noqa: E402
from optimisation_results_workbook import append_run_to_workbook  # noqa: E402


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


DEFAULT_MAX_IMAGES = 20
DEFAULT_TOYS_PER_IMAGE = 6
DEFAULT_INITIAL_POINTS = 8
DEFAULT_MAX_ITER = 32
DEFAULT_RANDOM_SEED = 20260719
DEFAULT_MAX_MASKED_FRACTION = 0.15
DEFAULT_DATA_LOSS_PENALTY = 0.35
DEFAULT_FALSE_POSITIVE_PENALTY = 0.05
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
PARAMETER_BOUNDS = {
    # Guide2source_extractor.pdf recommends starting near 1.2 sigma, gives
    # published examples spanning 0.6--2 sigma and 5--35 pixels, identifies
    # 32 deblend levels as the common choice, and recommends MINCONT of order
    # 0.01.  These ranges remain broad enough for Optuna without inviting
    # physically implausible edge solutions.
    "detect_thresh": (0.6, 2.0),
    "minarea": (5, 35),
    "deblend_nthresh": [16, 32, 64],
    "deblend_cont": (0.001, 0.03),
    # Use the power-of-two mesh sizes demonstrated in Guide2source_extractor.
    # Exclude intermediate meshes so the search remains inside that documented
    # Source Extractor operating region.
    "back_size": [32, 64, 128, 256],
    "filter_size": [1, 3, 5, 7, 9],
    "dilation_radius": (1, 6),
    "max_area": (20, 8000),
    "max_elongation": (1.5, 30.0),
}


@dataclass
class ToyObject:
    image_name: str
    toy_id: int
    object_type: str
    x: float
    y: float
    peak_sigma: float
    fwhm_pixels: float
    axis_ratio: float
    pa_deg: float
    truth_pixels: int


@dataclass
class ImageCase:
    name: str
    data: np.ndarray
    geometry: dict[str, float]
    injected: np.ndarray
    truth_mask: np.ndarray
    truth_labels: np.ndarray
    toys: list[ToyObject]
    baseline_mask: np.ndarray
    analysis_region: np.ndarray


_WORKER_CASES: list[ImageCase] | None = None


def initialise_score_worker(cases: list[ImageCase]) -> None:
    global _WORKER_CASES
    _WORKER_CASES = cases


def score_case_worker(task: tuple[int, dict[str, float | int | str]]) -> dict[str, float | int | str]:
    case_index, params = task
    if _WORKER_CASES is None:
        raise RuntimeError("SEP scoring worker was not initialised.")
    return score_case(_WORKER_CASES[case_index], params)


def robust_sigma(data: np.ndarray) -> float:
    values = np.asarray(data, dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return 1.0
    median = float(np.nanmedian(finite))
    mad = float(np.nanmedian(np.abs(finite - median)))
    sigma = 1.4826 * mad
    if not math.isfinite(sigma) or sigma <= 0:
        sigma = float(np.nanstd(finite))
    return sigma if math.isfinite(sigma) and sigma > 0 else 1.0


def circular_dilate(mask: np.ndarray, radius_pixels: int) -> np.ndarray:
    return sep_tool.dilate_mask(mask, int(max(0, radius_pixels)))


def gaussian_model(
    shape: tuple[int, int],
    x0: float,
    y0: float,
    peak: float,
    fwhm_pixels: float,
    axis_ratio: float = 1.0,
    pa_deg: float = 0.0,
) -> np.ndarray:
    yy, xx = np.indices(shape, dtype=float)
    sigma_major = max(0.25, float(fwhm_pixels) / 2.3548)
    sigma_minor = max(0.25, sigma_major * float(axis_ratio))
    theta = math.radians(float(pa_deg))
    dx = xx - float(x0)
    dy = yy - float(y0)
    major = dx * math.cos(theta) + dy * math.sin(theta)
    minor = -dx * math.sin(theta) + dy * math.cos(theta)
    radius2 = (major / sigma_major) ** 2 + (minor / sigma_minor) ** 2
    return peak * np.exp(-0.5 * radius2)


def toy_model(
    shape: tuple[int, int],
    toy_type: str,
    x0: float,
    y0: float,
    peak: float,
    fwhm_pixels: float,
    axis_ratio: float,
    pa_deg: float,
) -> np.ndarray:
    if toy_type == "cluster":
        model = np.zeros(shape, dtype=float)
        for dx, dy, scale in [(-0.55, -0.25, 0.75), (0.45, 0.18, 0.55), (0.05, 0.65, 0.38)]:
            model += gaussian_model(shape, x0 + dx * fwhm_pixels, y0 + dy * fwhm_pixels, peak * scale, fwhm_pixels * 0.85)
        return model
    if toy_type == "galaxy":
        return gaussian_model(shape, x0, y0, peak, fwhm_pixels, axis_ratio, pa_deg)
    return gaussian_model(shape, x0, y0, peak, fwhm_pixels)


def truth_from_model(model: np.ndarray, truth_dilation: int) -> np.ndarray:
    peak = float(np.nanmax(model))
    if not math.isfinite(peak) or peak <= 0:
        return np.zeros(model.shape, dtype=bool)
    return circular_dilate(model >= 0.08 * peak, truth_dilation)


def default_params(detect_on: str) -> dict[str, float | int | str]:
    if detect_on != "original":
        raise ValueError("SEP Toy Objects optimisation must detect on the original science image.")
    return {
        "detect_on": "original",
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
    }


def vector_to_params(values: np.ndarray, detect_on: str) -> dict[str, float | int | str]:
    params = default_params(detect_on)
    vector = np.asarray(values, dtype=float).ravel()
    settings = dict(zip(OPTIMISED_PARAMETER_NAMES, vector))
    params["detect_thresh"] = float(settings["detect_thresh"])
    params["minarea"] = max(1, int(round(float(settings["minarea"]))))
    params["deblend_nthresh"] = max(1, int(round(float(settings["deblend_nthresh"]))))
    params["deblend_cont"] = float(settings["deblend_cont"])
    params["back_size"] = max(1, int(round(float(settings["back_size"]))))
    params["filter_size"] = max(1, int(round(float(settings["filter_size"]))))
    params["dilation_radius"] = max(0, int(round(float(settings["dilation_radius"]))))
    params["max_area"] = max(1, int(round(float(settings["max_area"]))))
    params["max_elongation"] = float(settings["max_elongation"])
    return params


def optuna_trial_to_params(trial: optuna.Trial, detect_on: str) -> dict[str, float | int | str]:
    params = default_params(detect_on)
    params["detect_thresh"] = trial.suggest_float("detect_thresh", *PARAMETER_BOUNDS["detect_thresh"])
    params["minarea"] = trial.suggest_int("minarea", *PARAMETER_BOUNDS["minarea"])
    params["deblend_nthresh"] = trial.suggest_categorical("deblend_nthresh", PARAMETER_BOUNDS["deblend_nthresh"])
    params["deblend_cont"] = trial.suggest_float("deblend_cont", *PARAMETER_BOUNDS["deblend_cont"], log=True)
    params["back_size"] = trial.suggest_categorical("back_size", PARAMETER_BOUNDS["back_size"])
    params["filter_size"] = trial.suggest_categorical("filter_size", PARAMETER_BOUNDS["filter_size"])
    params["dilation_radius"] = trial.suggest_int("dilation_radius", *PARAMETER_BOUNDS["dilation_radius"])
    params["max_area"] = trial.suggest_int("max_area", *PARAMETER_BOUNDS["max_area"])
    params["max_elongation"] = trial.suggest_float("max_elongation", *PARAMETER_BOUNDS["max_elongation"])
    return params


def params_to_jsonable(params: dict[str, float | int | str]) -> dict[str, float | int | str]:
    return {
        key: ("NaN" if isinstance(value, float) and math.isnan(value) else value)
        for key, value in params.items()
    }


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


def investigated_region_mask(data: np.ndarray, geometry: dict[str, float]) -> np.ndarray:
    radius_pix = sep_tool.display.profile_radius_pixels(data, geometry)
    yy, xx = np.indices(data.shape, dtype=float)
    offsets = np.vstack([(xx - (geometry["xc"] - 1.0)).ravel(), (yy - (geometry["yc"] - 1.0)).ravel()])
    transform_xy = sep_tool.display.image_transform(geometry["disk_pa"], geometry["inclination"], geometry["bar_pa"])
    aligned = transform_xy @ offsets
    aligned_x = aligned[0].reshape(data.shape)
    aligned_y = aligned[1].reshape(data.shape)
    return (
        np.isfinite(data)
        & (np.abs(aligned_x) <= radius_pix)
        & (np.abs(aligned_y) <= radius_pix)
    )


def inject_toys(
    name: str,
    data: np.ndarray,
    geometry: dict[str, float],
    *,
    toys_per_image: int,
    rng: np.random.Generator,
    truth_dilation: int,
    peak_sigma_min: float = 5.0,
    peak_sigma_max: float = 25.0,
    fwhm_scale: float = 1.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[ToyObject]]:
    if not (0.0 < peak_sigma_min < peak_sigma_max):
        raise ValueError("Toy peak-sigma bounds must satisfy 0 < minimum < maximum.")
    if not (0.0 < fwhm_scale <= 1.0):
        raise ValueError("Toy FWHM scale must satisfy 0 < scale <= 1.")
    sigma = robust_sigma(data)
    injected = np.array(data, dtype=float, copy=True)
    truth_mask = np.zeros(data.shape, dtype=bool)
    truth_labels = np.zeros(data.shape, dtype=np.int32)
    toys: list[ToyObject] = []
    analysis_region = investigated_region_mask(data, geometry)
    margin = max(16, int(round(min(data.shape) * 0.04)))
    valid_y, valid_x = np.nonzero(analysis_region)
    valid = (
        (valid_x >= margin)
        & (valid_x < data.shape[1] - margin)
        & (valid_y >= margin)
        & (valid_y < data.shape[0] - margin)
    )
    candidates = np.flatnonzero(valid)
    if candidates.size == 0:
        raise ValueError(f"{name} has no injection candidates inside the investigated galaxy area.")

    for toy_id in range(1, toys_per_image + 1):
        selected: tuple[str, float, float, float, float, float, float, np.ndarray, np.ndarray] | None = None
        for _attempt in range(10000):
            chosen = int(rng.choice(candidates))
            x0 = float(valid_x[chosen])
            y0 = float(valid_y[chosen])
            toy_type = str(rng.choice(["star", "cluster", "galaxy"], p=[0.5, 0.2, 0.3]))
            peak_sigma = float(rng.uniform(peak_sigma_min, peak_sigma_max))
            fwhm_pixels = float(
                (rng.uniform(2.0, 10.0) if toy_type != "galaxy" else rng.uniform(5.0, 22.0))
                * fwhm_scale
            )
            axis_ratio = float(rng.uniform(0.35, 0.95) if toy_type == "galaxy" else 1.0)
            pa_deg = float(rng.uniform(0.0, 180.0))
            model = toy_model(data.shape, toy_type, x0, y0, peak_sigma * sigma, fwhm_pixels, axis_ratio, pa_deg)
            truth = truth_from_model(model, truth_dilation)
            if np.any(truth & ~analysis_region):
                continue
            local_radius = max(8, int(math.ceil(2.5 * fwhm_pixels + truth_dilation)))
            local = truth_mask[
                max(0, int(y0) - local_radius) : min(data.shape[0], int(y0) + local_radius + 1),
                max(0, int(x0) - local_radius) : min(data.shape[1], int(x0) + local_radius + 1),
            ]
            if np.any(local):
                continue
            selected = (toy_type, x0, y0, peak_sigma, fwhm_pixels, axis_ratio, pa_deg, model, truth)
            break
        if selected is None:
            raise ValueError(f"{name} could not place toy {toy_id} wholly inside the investigated galaxy area.")
        toy_type, x0, y0, peak_sigma, fwhm_pixels, axis_ratio, pa_deg, model, truth = selected
        injected += model
        label = len(toys) + 1
        truth_mask |= truth
        truth_labels[truth] = label
        toys.append(
            ToyObject(
                image_name=name,
                toy_id=label,
                object_type=toy_type,
                x=x0,
                y=y0,
                peak_sigma=peak_sigma,
                fwhm_pixels=fwhm_pixels,
                axis_ratio=axis_ratio,
                pa_deg=pa_deg,
                truth_pixels=int(np.count_nonzero(truth)),
            )
        )
    return injected, truth_mask, truth_labels, toys


def build_cases(args: argparse.Namespace) -> list[ImageCase]:
    rng = np.random.default_rng(int(args.seed))
    cases = []
    injection_sets = list(getattr(args, "injection_sets", None) or [args.injection_set])
    rows = select_rows(args.manifest, args.pc, args.names, int(args.max_images), int(args.seed))
    baseline_params = default_params(args.detect_on)
    # The historic shared defaults were tuned on residual images and are far
    # too permissive for a science-frame baseline.  Use a conservative point
    # wholly inside the documented optimisation bounds; this baseline exists
    # only to distinguish newly injected toy detections from pre-existing
    # science-image detections.
    baseline_params.update(
        {
            "detect_thresh": 2.0,
            "minarea": 35,
            "deblend_nthresh": 16,
            "deblend_cont": 0.03,
            "back_size": 64,
            "filter_size": 9,
            "dilation_radius": 1,
            "max_area": 8000,
            "max_elongation": 30.0,
        }
    )
    for row in rows:
        name = row["name"]
        geometry = sep_tool.display.required_geometry(row)
        if geometry is None:
            continue
        image_path = sep_tool.display.image_path_for_pc(row, args.pc)
        data, _header = sep_tool.load_fits(image_path)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            baseline_products = sep_tool.sep_products(data, baseline_params, geometry)
        if args.injection_manifest:
            for injection_set in injection_sets:
                delta, truth_mask, truth_labels, toy_rows, _record = paired_toy_common.load_materialized_injection(
                    Path(args.injection_manifest), injection_set, name, Path(image_path)
                )
                injected = np.asarray(data, dtype=float) + delta
                toys = [ToyObject(**{key: toy_row[key] for key in ToyObject.__dataclass_fields__}) for toy_row in toy_rows]
                cases.append(
                    ImageCase(
                        name=f"{name} [{injection_set}]" if len(injection_sets) > 1 else name,
                        data=data, geometry=geometry, injected=injected,
                        truth_mask=truth_mask, truth_labels=truth_labels, toys=toys,
                        baseline_mask=np.asarray(baseline_products["mask"], dtype=bool),
                        analysis_region=investigated_region_mask(data, geometry),
                    )
                )
                print(f"Prepared {name} [{injection_set}]: {len(toys)} injected toy objects.")
            continue
        else:
            injected, truth_mask, truth_labels, toys = inject_toys(
                name, data, geometry, toys_per_image=int(args.toys_per_image), rng=rng,
                truth_dilation=int(args.truth_dilation), peak_sigma_min=float(args.toy_peak_sigma_min),
                peak_sigma_max=float(args.toy_peak_sigma_max),
            )
        cases.append(
            ImageCase(
                name=name,
                data=data,
                geometry=geometry,
                injected=injected,
                truth_mask=truth_mask,
                truth_labels=truth_labels,
                toys=toys,
                baseline_mask=np.asarray(baseline_products["mask"], dtype=bool),
                analysis_region=investigated_region_mask(data, geometry),
            )
        )
        print(f"Prepared {name}: {len(toys)} injected toy objects.")
    return cases


def score_case(
    case: ImageCase,
    params: dict[str, float | int | str],
) -> dict[str, float | int | str]:
    products = sep_tool.sep_products(case.injected, params, case.geometry)
    return paired_toy_common.evaluate_mask(case, products["mask"], len(products["rows"]))


def aggregate_score(
    case_rows: list[dict[str, float | int | str]],
    *,
    max_masked_fraction: float,
    data_loss_penalty: float,
    false_positive_penalty: float,
) -> dict[str, float]:
    if not case_rows:
        return {"objective": 1.0, "score": 0.0}
    mean_recall = float(np.mean([float(row["recall"]) for row in case_rows]))
    mean_precision = float(np.mean([float(row["precision"]) for row in case_rows]))
    mean_f = float(np.mean([float(row["f_score"]) for row in case_rows]))
    mean_toy_recall = float(np.mean([float(row["mean_toy_recall"]) for row in case_rows]))
    mean_masked = float(np.mean([float(row["masked_fraction"]) for row in case_rows]))
    max_masked = float(np.max([float(row["masked_fraction"]) for row in case_rows]))
    false_positive = float(np.mean([float(row["false_positive_fraction"]) for row in case_rows]))
    recovered = sum(int(row["recovered_toys"]) for row in case_rows)
    toy_count = sum(int(row["toy_count"]) for row in case_rows)
    toy_detection_rate = recovered / toy_count if toy_count else 0.0
    recovery_score = 0.45 * mean_recall + 0.20 * mean_f + 0.25 * mean_toy_recall + 0.20 * toy_detection_rate
    data_loss = data_loss_penalty * mean_masked + false_positive_penalty * min(false_positive, 1.0)
    score = recovery_score - data_loss
    cap_excess = max(0.0, max_masked - max_masked_fraction)
    if cap_excess > 0.0:
        objective = 10.0 + 100.0 * cap_excess + data_loss - recovery_score
    else:
        objective = -score
    return {
        "objective": objective,
        "score": score,
        "mean_recall": mean_recall,
        "mean_precision": mean_precision,
        "mean_f_score": mean_f,
        "mean_toy_recall": mean_toy_recall,
        "toy_detection_rate": toy_detection_rate,
        "mean_masked_fraction": mean_masked,
        "max_masked_fraction": max_masked,
        "max_masked_fraction_limit": max_masked_fraction,
        "masked_fraction_cap_excess": cap_excess,
        "false_positive_fraction": false_positive,
    }


def append_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def write_toys(path: Path, cases: list[ImageCase]) -> None:
    rows = []
    for case in cases:
        for toy in case.toys:
            rows.append(toy.__dict__)
    append_csv(
        path,
        rows,
        ["image_name", "toy_id", "object_type", "x", "y", "peak_sigma", "fwhm_pixels", "axis_ratio", "pa_deg", "truth_pixels"],
    )


class OptimisationRun:
    def __init__(self, args: argparse.Namespace, cases: list[ImageCase]):
        self.args = args
        self.cases = cases
        self.output_dir = args.output_dir
        self.summary_path = self.output_dir / "sep_toy_object_optimisation_summary.csv"
        self.detail_path = self.output_dir / "sep_toy_object_optimisation_details.csv"
        self.best_path = self.output_dir / "sep_toy_object_optimisation_best.json"
        self.evaluation_index = 0
        self.best: dict[str, object] | None = None
        self.total_trials = 0
        self.completed_before_run = 0
        self.trial_durations: list[float] = []
        self.worker_pool: mp.pool.Pool | None = None
        worker_count = min(max(1, int(args.workers)), len(cases))
        self.result_metadata = {
            "algorithm": "SEP", **paired_toy_common.runtime_metadata(PROJECT_ROOT),
            "worker_count": worker_count, "injection_manifest": str(args.injection_manifest),
            "injection_set": args.injection_set,
        }
        if worker_count > 1:
            start_method = "fork" if os.name == "posix" else "spawn"
            context = mp.get_context(start_method)
            self.worker_pool = context.Pool(
                processes=worker_count,
                initializer=initialise_score_worker,
                initargs=(cases,),
            )
            print(f"Using {worker_count} SEP image workers ({start_method}).", flush=True)

    def close(self) -> None:
        if self.worker_pool is not None:
            self.worker_pool.close()
            self.worker_pool.join()
            self.worker_pool = None

    def evaluate_params(
        self,
        params: dict[str, float | int | str],
        parameter_values: dict[str, float | int],
        trial_number: int | None = None,
    ) -> float:
        self.evaluation_index += 1
        started = time.perf_counter()
        summary: dict[str, object]
        detail_rows: list[dict[str, object]] = []
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                if self.worker_pool is None:
                    case_rows = [score_case(case, params) for case in self.cases]
                else:
                    tasks = [(index, params) for index in range(len(self.cases))]
                    case_rows = self.worker_pool.map(score_case_worker, tasks)
            aggregate = aggregate_score(
                case_rows,
                max_masked_fraction=float(self.args.max_masked_fraction),
                data_loss_penalty=float(self.args.data_loss_penalty),
                false_positive_penalty=float(self.args.false_positive_penalty),
            )
            objective = float(aggregate["objective"])
            status = "ok"
            error = ""
            parameter_set_json = json.dumps(params_to_jsonable(params), sort_keys=True)
            for row in case_rows:
                detail_rows.append({"evaluation": self.evaluation_index, **self.result_metadata, "parameter_set_json": parameter_set_json, **row})
        except Exception as exc:  # noqa: BLE001
            aggregate = {"objective": 1.0e6, "score": -1.0e6}
            objective = 1.0e6
            status = "error"
            error = "".join(traceback.format_exception_only(type(exc), exc)).strip()

        elapsed = time.perf_counter() - started
        summary = {
            "evaluation": self.evaluation_index,
            **self.result_metadata,
            "parameter_set_json": json.dumps(params_to_jsonable(params), sort_keys=True),
            "status": status,
            "objective": objective,
            "score": aggregate.get("score", math.nan),
            "mean_recall": aggregate.get("mean_recall", math.nan),
            "mean_precision": aggregate.get("mean_precision", math.nan),
            "mean_f_score": aggregate.get("mean_f_score", math.nan),
            "mean_toy_recall": aggregate.get("mean_toy_recall", math.nan),
            "toy_detection_rate": aggregate.get("toy_detection_rate", math.nan),
            "mean_masked_fraction": aggregate.get("mean_masked_fraction", math.nan),
            "max_masked_fraction": aggregate.get("max_masked_fraction", math.nan),
            "max_masked_fraction_limit": aggregate.get("max_masked_fraction_limit", math.nan),
            "masked_fraction_cap_excess": aggregate.get("masked_fraction_cap_excess", math.nan),
            "false_positive_fraction": aggregate.get("false_positive_fraction", math.nan),
            "elapsed_seconds": elapsed,
            "error": error,
            "trial_number": "" if trial_number is None else trial_number,
            **parameter_values,
            **params_to_jsonable(params),
        }
        append_csv(
            self.summary_path,
            [summary],
            [
                "evaluation",
                "algorithm", "software_version", "python_version", "runtime_platform", "metric_version",
                "worker_count", "injection_manifest", "injection_set", "parameter_set_json",
                "status",
                "objective",
                "score",
                "mean_recall",
                "mean_precision",
                "mean_f_score",
                "mean_toy_recall",
                "toy_detection_rate",
                "mean_masked_fraction",
                "max_masked_fraction",
                "max_masked_fraction_limit",
                "masked_fraction_cap_excess",
                "false_positive_fraction",
                "elapsed_seconds",
                "error",
                "trial_number",
                *OPTIMISED_PARAMETER_NAMES,
                "detect_on",
            ],
        )
        if detail_rows:
            append_csv(
                self.detail_path,
                detail_rows,
                [
                    "evaluation",
                    "algorithm", "software_version", "python_version", "runtime_platform", "metric_version",
                    "worker_count", "injection_manifest", "injection_set", "parameter_set_json",
                    "image",
                    "truth_pixels",
                    "incremental_pixels",
                    "overlap_pixels",
                    "masked_fraction",
                    "recall",
                    "precision",
                    "f_score",
                    "mean_toy_recall",
                    "recovered_toys",
                    "toy_count",
                    "false_positive_fraction",
                    "incremental_overlap_pixels", "incremental_masked_fraction", "incremental_recall", "incremental_precision", "incremental_f_score", "incremental_false_positive_fraction",
                    "final_pixels", "final_overlap_pixels", "final_masked_fraction", "final_recall", "final_precision", "final_f_score", "final_false_positive_fraction",
                    "final_mean_toy_recall", "final_recovered_toys",
                    "segments",
                ],
            )
        if status == "ok" and (self.best is None or objective < float(self.best["objective"])):
            self.best = dict(summary)
            self.best["params"] = params_to_jsonable(params)
            self.best_path.write_text(json.dumps(self.best, indent=2), encoding="utf-8")
        self.trial_durations.append(elapsed)
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
        print(
            f"[{timestamp()}] eval {self.evaluation_index:03d}: "
            f"score={float(aggregate.get('score', -1)):.4f} status={status} "
            f"mean_masked={float(aggregate.get('mean_masked_fraction', math.nan)):.3%} "
            f"max_masked={float(aggregate.get('max_masked_fraction', math.nan)):.3%} "
            f"elapsed={format_duration(elapsed)}{remaining_text}",
            flush=True,
        )
        return objective

    def evaluate_trial(self, trial: optuna.Trial) -> float:
        params = optuna_trial_to_params(trial, self.args.detect_on)
        parameter_values = {name: params[name] for name in OPTIMISED_PARAMETER_NAMES}
        objective = self.evaluate_params(params, parameter_values, trial.number)
        score = -objective
        trial.set_user_attr("score", score)
        if self.best is not None:
            trial.set_user_attr("best_json", str(self.best_path))
        return objective

    def evaluate_vector(self, x: np.ndarray) -> float:
        params = vector_to_params(x, self.args.detect_on)
        parameter_values = {name: params[name] for name in OPTIMISED_PARAMETER_NAMES}
        return self.evaluate_params(params, parameter_values)


def run_optuna(run: OptimisationRun) -> None:
    total_trials = int(run.args.initial_points) + int(run.args.max_iter)
    run.total_trials = total_trials
    sampler = optuna.samplers.TPESampler(
        seed=int(run.args.seed),
        n_startup_trials=int(run.args.initial_points),
    )
    storage_dir = run.args.study_storage_dir or run.output_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_path = storage_dir / f"{run.args.study_name}.sqlite3"
    storage_url = f"sqlite:///{storage_path.as_posix()}"
    study = optuna.create_study(
        study_name=run.args.study_name,
        direction="minimize",
        sampler=sampler,
        storage=storage_url,
        load_if_exists=True,
    )
    interrupted = 0
    for trial in study.get_trials(deepcopy=False):
        if trial.state == optuna.trial.TrialState.RUNNING:
            study._storage.set_trial_state_values(trial._trial_id, optuna.trial.TrialState.FAIL)
            interrupted += 1
    if interrupted:
        print(f"Recovered {interrupted} interrupted Optuna trial(s) as failed; replacement trials will run.")
    run.completed_before_run = len(study.trials)
    completed_count = sum(
        trial.state == optuna.trial.TrialState.COMPLETE for trial in study.trials
    )
    remaining = max(0, total_trials - completed_count)
    converged, convergence = convergence_status(study, run.args)
    if converged:
        remaining = 0
    print(
        f"Optuna study '{study.study_name}' using TPESampler: "
        f"{completed_count} completed trials, {remaining} new trials."
    )
    if converged:
        print(
            "Early-stop criterion already satisfied: "
            f"{convergence['stagnant_trials']} completed trials without meaningful improvement."
        )
    if remaining:
        study.optimize(
            run.evaluate_trial,
            n_trials=remaining,
            callbacks=[convergence_callback(run.args)],
            gc_after_trial=True,
            show_progress_bar=False,
        )
    converged, convergence = convergence_status(study, run.args)
    convergence.update({
        "study_name": study.study_name,
        "maximum_trials": total_trials,
        "stopped_early": bool(converged and convergence["completed_trials"] < total_trials),
    })
    (run.output_dir / "optuna_convergence.json").write_text(
        json.dumps(convergence, indent=2), encoding="utf-8"
    )
    if study.best_trial is not None:
        print(f"Optuna best objective={study.best_value:.6g}, params={study.best_params}")


def convergence_status(study, args: argparse.Namespace) -> tuple[bool, dict]:
    """Return study-level convergence using completed trials in chronological order."""
    completed = [
        trial for trial in study.trials
        if trial.state == optuna.trial.TrialState.COMPLETE and trial.value is not None
    ]
    meaningful_best = None
    last_improvement = 0
    for position, trial in enumerate(completed, start=1):
        value = float(trial.value)
        if meaningful_best is None:
            meaningful_best = value
            last_improvement = position
            continue
        tolerance = max(
            float(args.convergence_absolute_tolerance),
            float(args.convergence_relative_tolerance) * max(abs(meaningful_best), abs(value)),
        )
        if meaningful_best - value > tolerance:
            meaningful_best = value
            last_improvement = position
    stagnant = len(completed) - last_improvement
    converged = (
        int(args.convergence_min_trials) > 0
        and int(args.convergence_patience) > 0
        and len(completed) >= int(args.convergence_min_trials)
        and stagnant >= int(args.convergence_patience)
    )
    return converged, {
        "converged": bool(converged),
        "completed_trials": len(completed),
        "minimum_trials": int(args.convergence_min_trials),
        "patience": int(args.convergence_patience),
        "relative_tolerance": float(args.convergence_relative_tolerance),
        "absolute_tolerance": float(args.convergence_absolute_tolerance),
        "last_meaningful_improvement_trial": last_improvement,
        "stagnant_trials": stagnant,
        "meaningful_best_objective": meaningful_best,
    }


def convergence_callback(args: argparse.Namespace):
    def callback(study, _trial) -> None:
        converged, status = convergence_status(study, args)
        if converged:
            print(
                "Study convergence detected after "
                f"{status['completed_trials']} trials; stopping this fold early.",
                flush=True,
            )
            study.stop()
    return callback


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    try:
        default_pc = detect_pc(SCRIPT_DIR)
    except RuntimeError:
        default_pc = "Desktop"
    parser.add_argument("--manifest", type=Path, default=sep_tool.DEFAULT_MANIFEST)
    parser.add_argument("--pc", choices=sorted(PC_RESEARCH_FOLDERS), default=default_pc)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--names", nargs="*", help="Optional explicit galaxy names. Defaults to the first usable images.")
    parser.add_argument("--max-images", type=int, default=DEFAULT_MAX_IMAGES)
    parser.add_argument("--toys-per-image", type=int, default=DEFAULT_TOYS_PER_IMAGE)
    parser.add_argument("--truth-dilation", type=int, default=1)
    parser.add_argument("--toy-peak-sigma-min", type=float, default=5.0)
    parser.add_argument("--toy-peak-sigma-max", type=float, default=25.0)
    parser.add_argument("--injection-manifest", type=Path, default=None)
    parser.add_argument("--injection-set", default="cross_validation")
    parser.add_argument(
        "--injection-sets", nargs="+", default=None,
        help="Optional immutable injection sets scored together in every trial.",
    )
    parser.add_argument(
        "--detect-on",
        dest="detect_on",
        choices=["original"],
        default="original",
        help=(
            "Image SEP uses during toy-object optimisation. SEP is constrained to "
            "the original science image."
        ),
    )
    parser.add_argument("--initial-points", type=int, default=DEFAULT_INITIAL_POINTS)
    parser.add_argument("--max-iter", type=int, default=DEFAULT_MAX_ITER)
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of process workers used to score images within each Optuna trial.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument("--study-name", default="sep-toy-object-optimisation")
    parser.add_argument("--study-storage-dir", type=Path, default=None)
    parser.add_argument("--convergence-min-trials", type=int, default=0)
    parser.add_argument("--convergence-patience", type=int, default=0)
    parser.add_argument("--convergence-relative-tolerance", type=float, default=0.001)
    parser.add_argument("--convergence-absolute-tolerance", type=float, default=1.0e-5)
    parser.add_argument(
        "--max-masked-fraction",
        type=float,
        default=DEFAULT_MAX_MASKED_FRACTION,
        help="Hard worst-image masked-fraction ceiling for a trial.",
    )
    parser.add_argument(
        "--data-loss-penalty",
        type=float,
        default=DEFAULT_DATA_LOSS_PENALTY,
        help="Penalty weight applied to the mean masked fraction.",
    )
    parser.add_argument(
        "--false-positive-penalty",
        type=float,
        default=DEFAULT_FALSE_POSITIVE_PENALTY,
        help="Penalty weight applied to foreground-mask pixels outside injected toy-object truth.",
    )
    parser.add_argument(
        "--results-workbook",
        type=Path,
        default=None,
        help="Optional shared XLSX workbook to append this run's trial results to.",
    )
    parser.add_argument("--prepare-only", action="store_true", help="Prepare injections and write toy catalogue, but do not optimise.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_parent = args.output_dir or (remove_foreground_folder(args.pc) / "sep toy optimisation")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    args.output_dir = output_parent / timestamp
    args.output_dir.mkdir(parents=True, exist_ok=True)
    config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    (args.output_dir / "sep_toy_object_optimisation_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    cases = build_cases(args)
    write_toys(args.output_dir / "sep_toy_object_optimisation_toys.csv", cases)
    print(f"Prepared {len(cases)} images and {sum(len(case.toys) for case in cases)} toy objects.")
    print(f"Output: {args.output_dir}")
    if args.prepare_only:
        return

    run = OptimisationRun(args, cases)
    try:
        run_optuna(run)
    finally:
        run.close()
    print(f"Best result: {run.best_path}")
    if os.name != "nt" and args.results_workbook is None:
        print("Results workbook: skipped on non-Windows host (pass --results-workbook to enable).")
        return
    try:
        workbook_path = append_run_to_workbook(
            algorithm="SEP",
            method="Toy Object",
            run_dir=args.output_dir,
            prefix="sep_toy_object_optimisation",
            workbook_path=args.results_workbook,
        )
        print(f"Results workbook: {workbook_path}")
    except Exception as exc:
        print(f"Could not update results workbook: {exc}")


if __name__ == "__main__":
    main()
