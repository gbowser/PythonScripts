"""Reusable SEP foreground-mask processing functions for batch and optimisation runs."""

from __future__ import annotations

import math
from pathlib import Path
import sys

import numpy as np
import sep
from astropy.io import fits
from scipy import ndimage


SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
SUPPORT_DIRS = tuple(FOREGROUND_ROOT / name for name in ("Batch tools", "PhotUtils", "Interactive tools", "Shared", "Utilities"))
for path in (PROJECT_ROOT, FOREGROUND_ROOT, SCRIPT_DIR, *SUPPORT_DIRS):
    if str(path) not in sys.path:
        sys.path.append(str(path))

import foreground_display_helpers as display  # noqa: E402
from machine_paths import detect_pc  # noqa: E402


DEFAULT_MANIFEST = display.DEFAULT_MANIFEST
DEFAULT_PC = detect_pc(FOREGROUND_ROOT)
DEFAULT_DETECT_THRESH = 0.7319079268449962
DEFAULT_MINAREA = 1
DEFAULT_DEBLEND_NTHRESH = 36
DEFAULT_DEBLEND_CONT = 0.0001033730789529874
DEFAULT_BACK_SIZE = 192
DEFAULT_FILTER_SIZE = 5
DEFAULT_DILATION_RADIUS = 0
DEFAULT_MAX_AREA = 203
DEFAULT_MAX_ELONGATION = 16.87855306159276
DEFAULT_EXCLUDE_CENTER_PIXELS = 8.0
DEFAULT_PROFILE_WIDTH_PIXELS = 3
PROFILE_BRIDGE_MERGE_GAP_SAMPLES = 12


def load_fits(path: Path) -> tuple[np.ndarray, fits.Header]:
    with fits.open(path) as hdul:
        data = np.squeeze(np.asarray(hdul[0].data, dtype=float))
        header = hdul[0].header.copy()
    if data.ndim != 2:
        raise ValueError(f"Expected a 2D FITS image after squeezing, got {data.shape}.")
    return data, header


def smooth_model(data: np.ndarray, sigma_pixels: float = 15.0) -> np.ndarray:
    finite = np.isfinite(data)
    filled = np.where(finite, data, 0.0)
    weights = finite.astype(float)
    smooth_data = ndimage.gaussian_filter(filled, sigma=sigma_pixels, mode="nearest")
    smooth_weights = ndimage.gaussian_filter(weights, sigma=sigma_pixels, mode="nearest")
    return np.divide(
        smooth_data,
        smooth_weights,
        out=np.full_like(data, np.nan, dtype=float),
        where=smooth_weights > 1.0e-6,
    )


def prepare_detection_image(data: np.ndarray, mode: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    residual = data - smooth_model(data, sigma_pixels=15.0)
    detection = residual if mode == "residual" else data
    finite = np.isfinite(detection)
    if not np.any(finite):
        raise ValueError("Detection image contains no finite pixels.")
    safe = np.array(detection, dtype=np.float32, copy=True)
    safe[~finite] = float(np.nanmedian(safe[finite]))
    return np.ascontiguousarray(safe), residual, ~finite


def make_filter_kernel(size: int) -> np.ndarray:
    size = max(1, int(size))
    if size % 2 == 0:
        size += 1
    if size == 1:
        return np.ones((1, 1), dtype=np.float32)
    sigma = max(0.5, size / 3.0)
    yy, xx = np.indices((size, size), dtype=float)
    center = (size - 1) / 2.0
    kernel = np.exp(-0.5 * (((xx - center) / sigma) ** 2 + ((yy - center) / sigma) ** 2))
    return np.asarray(kernel / np.sum(kernel), dtype=np.float32)


def robust_sigma(data: np.ndarray) -> float:
    values = np.asarray(data, dtype=float)
    sample = values[np.isfinite(values)]
    if sample.size == 0:
        return 1.0
    median = float(np.nanmedian(sample))
    mad = float(np.nanmedian(np.abs(sample - median)))
    sigma = 1.4826 * mad
    if not math.isfinite(sigma) or sigma <= 0:
        sigma = float(np.nanstd(sample))
    return sigma if math.isfinite(sigma) and sigma > 0 else 1.0


def circular_footprint(radius: int) -> np.ndarray:
    yy, xx = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    return (xx * xx + yy * yy) <= radius * radius


def dilate_mask(mask: np.ndarray, radius_pixels: int) -> np.ndarray:
    if radius_pixels <= 0:
        return np.asarray(mask, dtype=bool)
    return ndimage.binary_dilation(np.asarray(mask, dtype=bool), structure=circular_footprint(int(radius_pixels)))


def contiguous_true_runs(values: np.ndarray) -> list[tuple[int, int]]:
    indices = np.flatnonzero(values)
    if indices.size == 0:
        return []
    runs = []
    start = previous = int(indices[0])
    for index in indices[1:]:
        index = int(index)
        if index != previous + 1:
            runs.append((start, previous))
            start = index
        previous = index
    runs.append((start, previous))
    return runs


def merge_boolean_runs(masked: np.ndarray, max_gap: int) -> np.ndarray:
    merged = np.asarray(masked, dtype=bool).copy()
    if max_gap <= 0 or not np.any(merged):
        return merged

    indices = np.flatnonzero(merged)
    start = previous = int(indices[0])
    runs: list[tuple[int, int]] = []
    for index in indices[1:]:
        index = int(index)
        if index - previous > max_gap + 1:
            runs.append((start, previous))
            start = index
        previous = index
    runs.append((start, previous))

    merged[:] = False
    for start, stop in runs:
        merged[start : stop + 1] = True
    return merged


def fill_profile_with_log_linear_bridges(
    profile: np.ndarray,
    masked_samples: np.ndarray,
    *,
    merge_gap_samples: int = PROFILE_BRIDGE_MERGE_GAP_SAMPLES,
) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(profile, dtype=float)
    filled = np.array(values, copy=True)
    replacement_mask = np.asarray(masked_samples, dtype=bool) | ~np.isfinite(values) | (values <= 0)
    bridge_context = merge_boolean_runs(replacement_mask, merge_gap_samples)
    replaced = np.zeros(values.size, dtype=bool)
    indices = np.arange(values.size)

    index = 0
    while index < values.size:
        if not bridge_context[index]:
            index += 1
            continue

        start = index
        while index + 1 < values.size and bridge_context[index + 1]:
            index += 1
        stop = index

        left = start - 1
        while left >= 0 and (~np.isfinite(values[left]) or values[left] <= 0):
            left -= 1
        right = stop + 1
        while right < values.size and (~np.isfinite(values[right]) or values[right] <= 0):
            right += 1

        fill_indices = indices[start : stop + 1][replacement_mask[start : stop + 1]]
        if fill_indices.size == 0:
            index += 1
            continue

        if left >= 0 and right < values.size:
            log_left = math.log(float(values[left]))
            log_right = math.log(float(values[right]))
            weight = (fill_indices - left) / (right - left)
            filled[fill_indices] = np.exp(log_left + weight * (log_right - log_left))
            replaced[fill_indices] = True
        elif left >= 0:
            filled[fill_indices] = values[left]
            replaced[fill_indices] = True
        elif right < values.size:
            filled[fill_indices] = values[right]
            replaced[fill_indices] = True

        index += 1

    return filled, replaced


def profile_mask_at_bar_major(mask_view: np.ndarray, y_axis: np.ndarray, half_width: float) -> np.ndarray:
    aperture_rows = np.abs(y_axis) <= half_width
    if not np.any(aperture_rows):
        aperture_rows[np.argmin(np.abs(y_axis))] = True
    return np.any(np.asarray(mask_view, dtype=bool)[aperture_rows, :], axis=0)


def measure_objects(objects: np.ndarray, residual: np.ndarray, geometry: dict[str, float]) -> list[dict[str, float | int]]:
    sigma = robust_sigma(residual)
    median = float(np.nanmedian(residual[np.isfinite(residual)]))
    rows: list[dict[str, float | int]] = []
    for index, obj in enumerate(objects, start=1):
        label = index
        area = int(obj["npix"])
        x = float(obj["x"])
        y = float(obj["y"])
        a = float(obj["a"])
        b = float(obj["b"])
        elongation = a / b if b > 0 else np.inf
        peak = float(obj["peak"])
        distance = float(np.hypot(x - (geometry["xc"] - 1.0), y - (geometry["yc"] - 1.0)))
        rows.append(
            {
                "label": label,
                "area": area,
                "x_centroid": x,
                "y_centroid": y,
                "elongation": elongation,
                "peak_residual_nsigma": (peak - median) / sigma if sigma > 0 else np.nan,
                "distance_from_center": distance,
            }
        )
    return rows


def filter_segmentation(segmentation: np.ndarray, rows: list[dict[str, float | int]], params: dict[str, float | int | str]):
    kept_labels: set[int] = set()
    updated_rows: list[dict[str, float | int | bool]] = []
    for row in rows:
        keep = True
        if int(row["area"]) > int(params["max_area"]):
            keep = False
        if float(row["elongation"]) > float(params["max_elongation"]):
            keep = False
        if float(row["distance_from_center"]) < float(params["exclude_center_pixels"]):
            keep = False
        if keep:
            kept_labels.add(int(row["label"]))
        updated = dict(row)
        updated["kept"] = keep
        updated_rows.append(updated)
    filtered = np.where(np.isin(segmentation, list(kept_labels)), segmentation, 0)
    return filtered, updated_rows


def sep_products(data: np.ndarray, params: dict[str, float | int | str], geometry: dict[str, float]):
    detection, residual, nonfinite_mask = prepare_detection_image(data, str(params["detect_on"]))
    # Science-image detection can leave substantially more pixels above the
    # threshold than residual-image detection.  SEP's default 300k-pixel
    # extraction stack is therefore too small for some full science frames.
    # Size the process-local stack to the image so valid detections do not
    # abort the optimisation or all-galaxy batch.
    sep.set_extract_pixstack(max(300_000, int(detection.size)))
    # A structured science frame can also create a large deblending tree.
    # Keep a generous but image-bounded limit so this valid workload does not
    # fail at SEP's much smaller library default.
    sep.set_sub_object_limit(8_192)
    bw = bh = max(8, int(params["back_size"]))
    background = sep.Background(detection, mask=nonfinite_mask, bw=bw, bh=bh)
    subtracted = np.ascontiguousarray(detection - background.back(), dtype=np.float32)
    kernel = make_filter_kernel(int(params["filter_size"]))
    objects, segmentation = sep.extract(
        subtracted,
        float(params["detect_thresh"]),
        err=float(background.globalrms),
        mask=nonfinite_mask,
        minarea=int(params["minarea"]),
        filter_kernel=kernel,
        deblend_nthresh=int(params["deblend_nthresh"]),
        deblend_cont=float(params["deblend_cont"]),
        clean=True,
        clean_param=1.0,
        segmentation_map=True,
    )
    rows = measure_objects(objects, residual, geometry)
    filtered, rows = filter_segmentation(segmentation, rows, params)
    mask = dilate_mask(filtered > 0, int(params["dilation_radius"]))
    cleaned = np.array(data, copy=True)
    finite_unmasked = np.isfinite(data) & ~mask
    replacement = float(np.nanmedian(data[finite_unmasked])) if np.any(finite_unmasked) else 0.0
    cleaned[mask] = replacement
    return {
        "objects": objects,
        "raw_segmentation": segmentation,
        "filtered_segmentation": filtered,
        "mask": mask,
        "cleaned": cleaned,
        "residual": residual,
        "background_rms": float(background.globalrms),
        "background_level": float(background.globalback),
        "rows": rows,
    }
