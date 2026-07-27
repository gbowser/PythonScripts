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
from pathlib import Path
import sys
import time
import traceback
import warnings

import numpy as np
import optuna

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SUPPORT_DIRS = tuple(SCRIPT_DIR / name for name in ("Batch tools", "PhotUtils", "Interactive tools", "Shared", "Utilities"))
for path in (SCRIPT_DIR, PROJECT_ROOT, *SUPPORT_DIRS):
    if str(path) not in sys.path:
        sys.path.append(str(path))

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
    "detect_thresh": (0.2, 5.0),
    "minarea": (1, 50),
    "deblend_nthresh": (8, 64),
    "deblend_cont": (0.00001, 0.1),
    "back_size": [16, 24, 32, 48, 64, 96, 128, 192, 256],
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
    params["deblend_nthresh"] = trial.suggest_int("deblend_nthresh", *PARAMETER_BOUNDS["deblend_nthresh"])
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
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[ToyObject]]:
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
        for _attempt in range(1000):
            chosen = int(rng.choice(candidates))
            x0 = float(valid_x[chosen])
            y0 = float(valid_y[chosen])
            toy_type = str(rng.choice(["star", "cluster", "galaxy"], p=[0.5, 0.2, 0.3]))
            peak_sigma = float(rng.uniform(5.0, 25.0))
            fwhm_pixels = float(rng.uniform(2.0, 10.0) if toy_type != "galaxy" else rng.uniform(5.0, 22.0))
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
    rows = select_rows(args.manifest, args.pc, args.names, int(args.max_images), int(args.seed))
    baseline_params = default_params(args.detect_on)
    for row in rows:
        name = row["name"]
        geometry = sep_tool.display.required_geometry(row)
        if geometry is None:
            continue
        data, _header = sep_tool.load_fits(sep_tool.display.image_path_for_pc(row, args.pc))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            baseline_products = sep_tool.sep_products(data, baseline_params, geometry)
        injected, truth_mask, truth_labels, toys = inject_toys(
            name,
            data,
            geometry,
            toys_per_image=int(args.toys_per_image),
            rng=rng,
            truth_dilation=int(args.truth_dilation),
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
            )
        )
        print(f"Prepared {name}: {len(toys)} injected toy objects.")
    return cases


def score_case(
    case: ImageCase,
    params: dict[str, float | int | str],
) -> dict[str, float | int | str]:
    products = sep_tool.sep_products(case.injected, params, case.geometry)
    mask = np.asarray(products["mask"], dtype=bool)
    incremental = mask & ~case.baseline_mask
    truth = case.truth_mask
    truth_pixels = int(np.count_nonzero(truth))
    incremental_pixels = int(np.count_nonzero(incremental))
    overlap = int(np.count_nonzero(incremental & truth))
    masked_fraction = incremental_pixels / incremental.size if incremental.size else 0.0
    recall = overlap / truth_pixels if truth_pixels else 0.0
    precision = overlap / incremental_pixels if incremental_pixels else 0.0
    f_score = 2.0 * recall * precision / (recall + precision) if recall + precision > 0 else 0.0
    toy_recalls = []
    recovered_toys = 0
    for toy in case.toys:
        toy_truth = case.truth_labels == toy.toy_id
        toy_pixels = int(np.count_nonzero(toy_truth))
        toy_overlap = int(np.count_nonzero(incremental & toy_truth))
        toy_recall = toy_overlap / toy_pixels if toy_pixels else 0.0
        toy_recalls.append(toy_recall)
        if toy_recall >= 0.5:
            recovered_toys += 1
    false_positive_fraction = (incremental_pixels - overlap) / max(1, incremental.size - truth_pixels)
    return {
        "image": case.name,
        "truth_pixels": truth_pixels,
        "incremental_pixels": incremental_pixels,
        "overlap_pixels": overlap,
        "masked_fraction": masked_fraction,
        "recall": recall,
        "precision": precision,
        "f_score": f_score,
        "mean_toy_recall": float(np.mean(toy_recalls)) if toy_recalls else 0.0,
        "recovered_toys": recovered_toys,
        "toy_count": len(case.toys),
        "false_positive_fraction": false_positive_fraction,
        "segments": len(products["rows"]),
    }


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
                case_rows = [score_case(case, params) for case in self.cases]
            aggregate = aggregate_score(
                case_rows,
                max_masked_fraction=float(self.args.max_masked_fraction),
                data_loss_penalty=float(self.args.data_loss_penalty),
                false_positive_penalty=float(self.args.false_positive_penalty),
            )
            objective = float(aggregate["objective"])
            status = "ok"
            error = ""
            for row in case_rows:
                detail_rows.append({"evaluation": self.evaluation_index, **row})
        except Exception as exc:  # noqa: BLE001
            aggregate = {"objective": 1.0e6, "score": -1.0e6}
            objective = 1.0e6
            status = "error"
            error = "".join(traceback.format_exception_only(type(exc), exc)).strip()

        elapsed = time.perf_counter() - started
        summary = {
            "evaluation": self.evaluation_index,
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
    storage_url = f"sqlite:///{(run.output_dir / 'sep_toy_object_optimisation_study.sqlite3').as_posix()}"
    study = optuna.create_study(
        study_name=run.args.study_name,
        direction="minimize",
        sampler=sampler,
        storage=storage_url,
        load_if_exists=True,
    )
    run.completed_before_run = len(study.trials)
    remaining = max(0, total_trials - len(study.trials))
    print(
        f"Optuna study '{study.study_name}' using TPESampler: "
        f"{len(study.trials)} existing trials, {remaining} new trials."
    )
    if remaining:
        study.optimize(run.evaluate_trial, n_trials=remaining, gc_after_trial=True, show_progress_bar=False)
    if study.best_trial is not None:
        print(f"Optuna best objective={study.best_value:.6g}, params={study.best_params}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=sep_tool.DEFAULT_MANIFEST)
    parser.add_argument("--pc", choices=sorted(PC_RESEARCH_FOLDERS), default=detect_pc(SCRIPT_DIR))
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--names", nargs="*", help="Optional explicit galaxy names. Defaults to the first usable images.")
    parser.add_argument("--max-images", type=int, default=DEFAULT_MAX_IMAGES)
    parser.add_argument("--toys-per-image", type=int, default=DEFAULT_TOYS_PER_IMAGE)
    parser.add_argument("--truth-dilation", type=int, default=1)
    parser.add_argument(
        "--detect-on",
        dest="detect_on",
        choices=["original", "residual"],
        default="residual",
        help=(
            "Image SEP uses during toy-object optimisation. "
            "Use 'original' for the science image or 'residual' for the smooth-model residual. "
        ),
    )
    parser.add_argument("--initial-points", type=int, default=DEFAULT_INITIAL_POINTS)
    parser.add_argument("--max-iter", type=int, default=DEFAULT_MAX_ITER)
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument("--study-name", default="sep-toy-object-optimisation")
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
    run_optuna(run)
    print(f"Best result: {run.best_path}")
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
