#!/usr/bin/env python3
"""Interactive MTObjects foreground-mask parameter tester.

MTObjects detects astronomical sources with max-tree statistical attribute
filtering. This tester keeps the local S4G manifest workflow and exposes
MTObjects masks through the same product/display boundary used by the SEP tools,
so later side-by-side comparisons can be made without reshaping outputs.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
from datetime import datetime
import math
import os
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from types import SimpleNamespace

import matplotlib

matplotlib.use("TkAgg")

import numpy as np
from astropy.io import fits
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from scipy import ndimage


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
for path in (PROJECT_ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

import interactive_galclean_parameter_tester as display  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, erwin_folder, remove_foreground_folder  # noqa: E402


DEFAULT_MANIFEST = display.DEFAULT_MANIFEST
DEFAULT_PC = "Desktop"
DEFAULT_GALAXY = "ESO120-012"
DEFAULT_MTOBJECTS_ROOT = os.environ.get("MTOBJECTS_ROOT")
MTOBJECTS_ROOT_CANDIDATES = [
    Path(DEFAULT_MTOBJECTS_ROOT).expanduser() if DEFAULT_MTOBJECTS_ROOT else None,
    SCRIPT_DIR / "mtobjects",
    PROJECT_ROOT / "mtobjects",
    PROJECT_ROOT.parent / "mtobjects",
    Path.home() / "Documents" / "Github" / "mtobjects",
    Path.home() / "Documents" / "GitHub" / "mtobjects",
]
MTOBJECTS_REQUIRED_LIBS = (
    "maxtree.so",
    "maxtree_double.so",
    "mt_objects.so",
    "mt_objects_double.so",
)
MTOBJECTS_DLL_DIR_CANDIDATES = [
    Path(os.environ["MTOBJECTS_DLL_DIR"]).expanduser() if os.environ.get("MTOBJECTS_DLL_DIR") else None,
    Path("C:/msys64/ucrt64/bin"),
    Path("C:/msys64/mingw64/bin"),
]
_MTOBJECTS_DLL_DIRECTORY_HANDLES = []
DEFAULT_ALPHA = 1.0e-6
DEFAULT_MOVE_FACTOR = 0.6557861773895259
SPIKE_GATE_MOVE_FACTOR = 0.3
DEFAULT_MIN_DISTANCE = 0.8413587368696457
DEFAULT_GAUSSIAN_FWHM = 2.2358188477217373
DEFAULT_SOFT_BIAS = 0.0
DEFAULT_GAIN = -1.0
DEFAULT_BG_MEAN = math.nan
DEFAULT_BG_VARIANCE = -1.0
DEFAULT_MINAREA = 13
DEFAULT_DILATION_RADIUS = 1
DEFAULT_MAX_AREA = 901
DEFAULT_MAX_ELONGATION = 19.140975911476875
DEFAULT_EXCLUDE_CENTER_PIXELS = 8.0
DEFAULT_PROFILE_WIDTH_PIXELS = 3
DEFAULT_SPIKE_EXCESS_FRACTION = 0.25
DEFAULT_SPIKE_NEIGHBOUR_INNER_ARCSEC = 4.0
DEFAULT_SPIKE_NEIGHBOUR_OUTER_ARCSEC = 15.0
DEFAULT_SPIKE_SIDE_OFFSET_SAMPLES = 3
DEFAULT_SPIKE_SIDE_DROP_FRACTION = 0.4
DEFAULT_SPIKE_WINDOW_SAMPLES = 2
PROFILE_BRIDGE_MERGE_GAP_SAMPLES = 12
PARAMETER_UNIT_LABELS = {
    "Pixels": "pixels",
    "Arcsec": "arcsec",
}
PIXEL_LINEAR_PARAMS = {
    "dilation_radius",
    "exclude_center_pixels",
}
PIXEL_AREA_PARAMS = {
    "minarea",
    "max_area",
}
FLOAT_SPIN_PARAMS = {
    "alpha",
    "move_factor",
    "spike_gate_move_factor",
    "min_distance",
    "gaussian_fwhm",
    "soft_bias",
    "gain",
    "bg_mean",
    "bg_variance",
}


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


def spike_samples_to_image_aperture(
    shape: tuple[int, int],
    geometry: dict[str, float],
    spike_radii_arcsec: np.ndarray,
    *,
    half_width_arcsec: float,
    sample_half_width_arcsec: float,
) -> np.ndarray:
    """Return original-image pixels lying in the bar aperture at spike radii."""
    spike_radii = np.asarray(spike_radii_arcsec, dtype=float)
    spike_radii = spike_radii[np.isfinite(spike_radii)]
    if spike_radii.size == 0:
        return np.zeros(shape, dtype=bool)

    yy, xx = np.indices(shape, dtype=float)
    pixel_scale = geometry["pixel_scale"]
    x_arcsec = pixel_scale * (xx - (geometry["xc"] - 1.0))
    y_arcsec = pixel_scale * (yy - (geometry["yc"] - 1.0))
    transform_xy = display.image_transform(geometry["disk_pa"], geometry["inclination"], geometry["bar_pa"])
    bar_x, bar_y = transform_xy @ np.vstack([x_arcsec.ravel(), y_arcsec.ravel()])
    bar_x = bar_x.reshape(shape)
    bar_y = bar_y.reshape(shape)

    in_bar_strip = np.abs(bar_y) <= half_width_arcsec
    in_spike_column = np.zeros(shape, dtype=bool)
    for spike_radius in spike_radii:
        in_spike_column |= np.abs(bar_x - spike_radius) <= sample_half_width_arcsec
    return in_bar_strip & in_spike_column


def is_mtobjects_root(path: Path) -> bool:
    return (path / "mtolib").is_dir()


def find_mtobjects_root(explicit_root: Path | None = None) -> Path | None:
    candidates = [explicit_root] if explicit_root is not None else []
    candidates.extend(candidate for candidate in MTOBJECTS_ROOT_CANDIDATES if candidate is not None)
    seen: set[Path] = set()
    for candidate in candidates:
        root = candidate.expanduser()
        try:
            root = root.resolve()
        except OSError:
            continue
        if root in seen:
            continue
        seen.add(root)
        if is_mtobjects_root(root):
            return root
    return None


def mtobjects_setup_message(explicit_root: Path | None = None) -> str:
    checked = []
    for candidate in MTOBJECTS_ROOT_CANDIDATES:
        if candidate is not None:
            checked.append(str(candidate))
    if explicit_root is not None:
        checked.insert(0, str(explicit_root))
    checked_text = "\n  - ".join(checked) if checked else "(none)"
    return (
        "Could not find the MTObjects Python package 'mtolib'.\n\n"
        "Clone CarolineHaigh/mtobjects locally, then either:\n"
        "  1. Start this tester with --mtobjects-root C:\\path\\to\\mtobjects, or\n"
        "  2. Set the MTOBJECTS_ROOT environment variable, or\n"
        "  3. Use the MTObjects root picker in the tester sidebar.\n\n"
        "Checked:\n  - "
        f"{checked_text}\n\n"
        "Note: MTObjects also needs its compiled libraries under mtolib/lib."
    )


def mtobjects_missing_libraries(root: Path) -> list[Path]:
    lib_dir = root / "mtolib" / "lib"
    return [lib_dir / name for name in MTOBJECTS_REQUIRED_LIBS if not (lib_dir / name).is_file()]


def mtobjects_library_message(root: Path) -> str:
    missing = mtobjects_missing_libraries(root)
    missing_text = "\n  - ".join(str(path) for path in missing)
    return (
        "MTObjects found, but its compiled C libraries are missing.\n\n"
        f"MTObjects root:\n  {root}\n\n"
        "Missing:\n  - "
        f"{missing_text}\n\n"
        "Compile MTObjects with a Windows-native gcc/MinGW toolchain, then restart this tester. "
        "The repository script is recompile.sh; WSL-built Linux .so files will not load into Windows Python."
    )


def add_mtobjects_dll_directories() -> None:
    if os.name != "nt" or not hasattr(os, "add_dll_directory"):
        return
    for candidate in MTOBJECTS_DLL_DIR_CANDIDATES:
        if candidate is None or not candidate.is_dir():
            continue
        _MTOBJECTS_DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(candidate.resolve())))


def expand_boolean_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    expanded = np.asarray(mask, dtype=bool).copy()
    if radius <= 0 or not np.any(expanded):
        return expanded
    for index in np.flatnonzero(expanded):
        start = max(0, int(index) - radius)
        stop = min(expanded.size, int(index) + radius + 1)
        expanded[start:stop] = True
    return expanded


def detect_profile_spikes(
    radii_arcsec: np.ndarray,
    values: np.ndarray,
    *,
    excess_fraction: float = DEFAULT_SPIKE_EXCESS_FRACTION,
    neighbour_inner_arcsec: float = DEFAULT_SPIKE_NEIGHBOUR_INNER_ARCSEC,
    neighbour_outer_arcsec: float = DEFAULT_SPIKE_NEIGHBOUR_OUTER_ARCSEC,
    side_offset_samples: int = DEFAULT_SPIKE_SIDE_OFFSET_SAMPLES,
    side_drop_fraction: float = DEFAULT_SPIKE_SIDE_DROP_FRACTION,
    center_exclusion_arcsec: float,
) -> np.ndarray:
    radii = np.asarray(radii_arcsec, dtype=float)
    profile = np.asarray(values, dtype=float)
    spikes = np.zeros(profile.size, dtype=bool)
    good = np.isfinite(radii) & np.isfinite(profile) & (profile > 0)
    if np.count_nonzero(good) < 12:
        return spikes

    side_offset_samples = max(1, int(side_offset_samples))
    for index in range(side_offset_samples, profile.size - side_offset_samples):
        if not good[index]:
            continue
        if abs(radii[index]) < center_exclusion_arcsec:
            continue
        if profile[index] < profile[index - 1] or profile[index] < profile[index + 1]:
            continue

        distance = np.abs(radii - radii[index])
        neighbour = good & (distance >= neighbour_inner_arcsec) & (distance <= neighbour_outer_arcsec)
        left_neighbour = neighbour & (radii < radii[index])
        right_neighbour = neighbour & (radii > radii[index])
        if np.count_nonzero(left_neighbour) >= 2 and np.count_nonzero(right_neighbour) >= 2:
            neighbour_values = np.concatenate([profile[left_neighbour], profile[right_neighbour]])
        elif np.count_nonzero(neighbour) >= 4:
            neighbour_values = profile[neighbour]
        else:
            continue

        neighbour_level = np.nanmedian(neighbour_values)
        if not np.isfinite(neighbour_level) or neighbour_level <= 0:
            continue
        if profile[index] < (1.0 + excess_fraction) * neighbour_level:
            continue

        side_level = np.nanmedian([profile[index - side_offset_samples], profile[index + side_offset_samples]])
        if not np.isfinite(side_level) or side_level <= 0:
            continue
        if profile[index] < (1.0 + side_drop_fraction) * side_level:
            continue

        spikes[index] = True
    return spikes


@contextlib.contextmanager
def mtobjects_context(mtobjects_root: Path | None):
    """Temporarily import/run MTObjects from its checkout root.

    MTObjects loads compiled C libraries with relative paths such as
    ``mtolib/lib/maxtree.so``. Running from the checkout root keeps those paths
    valid while still letting this tester live in the local Foreground Masking
    folder.
    """
    previous_cwd = Path.cwd()
    root = find_mtobjects_root(mtobjects_root)
    if root is None:
        raise ModuleNotFoundError(mtobjects_setup_message(mtobjects_root))
    if mtobjects_missing_libraries(root):
        raise RuntimeError(mtobjects_library_message(root))
    add_mtobjects_dll_directories()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.chdir(root)
    try:
        yield
    except ModuleNotFoundError as exc:
        if exc.name == "mtolib":
            raise ModuleNotFoundError(mtobjects_setup_message(mtobjects_root)) from exc
        raise
    except OSError as exc:
        raise RuntimeError(
            "MTObjects could not load its compiled C libraries. Set --mtobjects-root "
            "or MTOBJECTS_ROOT to a compiled CarolineHaigh/mtobjects checkout and run "
            "its recompile.sh if the mtolib/lib shared libraries are missing."
        ) from exc
    finally:
        os.chdir(previous_cwd)


def mtobjects_parameter_namespace(params: dict[str, float | int | str], image: np.ndarray) -> SimpleNamespace:
    d_type = ctypes.c_double if np.issubdtype(image.dtype, np.float64) else ctypes.c_float
    bg_mean = float(params["bg_mean"])
    return SimpleNamespace(
        filename=None,
        out="out.png",
        par_out="parameters.csv",
        soft_bias=float(params["soft_bias"]),
        gain=float(params["gain"]),
        bg_mean=None if math.isnan(bg_mean) else bg_mean,
        bg_variance=float(params["bg_variance"]),
        alpha=float(params["alpha"]),
        move_factor=float(params["move_factor"]),
        min_distance=float(params["min_distance"]),
        verbosity=0,
        d_type=d_type,
    )


def stabilize_mtobjects_background(params: SimpleNamespace, image: np.ndarray) -> None:
    variance = float(params.bg_variance)
    if not math.isfinite(variance) or variance <= 0:
        sigma = robust_sigma(image)
        params.bg_variance = max(float(sigma * sigma), 1.0e-12)
    gain = float(params.gain)
    if not math.isfinite(gain) or gain <= 0:
        params.gain = 1.0


def init_mtobjects_ctype_classes(mt_classes, d_type) -> None:
    if getattr(mt_classes.MtImageLocation, "_fields_", None):
        return
    mt_classes.init_classes(d_type)


def mtobjects_products(
    data: np.ndarray,
    params: dict[str, float | int | str],
    geometry: dict[str, float],
    mtobjects_root: Path | None,
):
    detection, residual, nonfinite_mask = prepare_detection_image(data, str(params["detect_on"]))
    # MTObjects uses finite positive images after background subtraction. The
    # non-finite mask is restored after relabeling so NaNs cannot become objects.
    mt_image = np.ascontiguousarray(detection, dtype=np.float64)
    with mtobjects_context(mtobjects_root):
        from mtolib import _ctype_classes as mt_classes
        from mtolib import maxtree
        from mtolib.postprocessing import relabel_segments
        from mtolib.preprocessing import preprocess_image
        from mtolib.tree_filtering import filter_tree, init_double_filtering

        mto_params = mtobjects_parameter_namespace(params, mt_image)
        if mto_params.d_type == ctypes.c_double:
            init_double_filtering(mto_params)
        init_mtobjects_ctype_classes(mt_classes, mto_params.d_type)
        processed = preprocess_image(
            np.array(mt_image, copy=True),
            mto_params,
            gaussian_blur=float(params["gaussian_fwhm"]) > 0,
            n=float(params["gaussian_fwhm"]),
            nan_value=np.inf,
        )
        stabilize_mtobjects_background(mto_params, mt_image)
        mt = maxtree.OriginalMaxTree(processed, mto_params.verbosity, mto_params)
        try:
            mt.flood()
            raw_segmentation, significant_ancestors = filter_tree(mt, processed, mto_params)
        finally:
            mt.free_objects()
        segmentation = relabel_segments(raw_segmentation, shuffle_labels=False)

    segmentation = np.asarray(segmentation, dtype=np.int32)
    segmentation[nonfinite_mask] = -1
    segmentation = np.where(segmentation > 0, segmentation, 0)
    rows = measure_segments(segmentation, residual, geometry)
    filtered, rows = filter_segmentation(segmentation, rows, params)
    mask = dilate_mask(filtered > 0, int(params["dilation_radius"]))
    cleaned = np.array(data, copy=True)
    finite_unmasked = np.isfinite(data) & ~mask
    replacement = float(np.nanmedian(data[finite_unmasked])) if np.any(finite_unmasked) else 0.0
    cleaned[mask] = replacement
    return {
        "objects": rows,
        "raw_segmentation": segmentation,
        "filtered_segmentation": filtered,
        "mask": mask,
        "cleaned": cleaned,
        "residual": residual,
        "background_rms": math.sqrt(float(mto_params.bg_variance)) if float(mto_params.bg_variance) >= 0 else math.nan,
        "background_level": float(mto_params.bg_mean) if mto_params.bg_mean is not None else math.nan,
        "significant_ancestors": significant_ancestors,
        "rows": rows,
    }


def spike_gated_mtobjects_products(
    data: np.ndarray,
    params: dict[str, float | int | str],
    geometry: dict[str, float],
    mtobjects_root: Path | None,
) -> dict[str, object]:
    gate_params = dict(params)
    gate_params["move_factor"] = float(params["spike_gate_move_factor"])
    low_threshold_products = mtobjects_products(data, gate_params, geometry, mtobjects_root)

    radius_arcsec = display.profile_radius_pixels(data, geometry) * geometry["pixel_scale"]
    original_view, x_axis, y_axis = display.deproject_bar_aligned_cutout(data, geometry, radius_arcsec)
    half_width = 0.5 * DEFAULT_PROFILE_WIDTH_PIXELS * geometry["pixel_scale"]
    radii, intensity = display.bar_major_axis_profile(original_view, x_axis, y_axis, half_width)
    spike_samples = detect_profile_spikes(
        radii,
        intensity,
        excess_fraction=float(params["spike_excess_fraction"]),
        neighbour_inner_arcsec=float(params["spike_neighbour_inner_arcsec"]),
        neighbour_outer_arcsec=float(params["spike_neighbour_outer_arcsec"]),
        side_offset_samples=int(params["spike_side_offset_samples"]),
        side_drop_fraction=float(params["spike_side_drop_fraction"]),
        center_exclusion_arcsec=float(params["exclude_center_pixels"]) * geometry["pixel_scale"],
    )
    spike_samples = expand_boolean_mask(spike_samples, int(params["spike_window_samples"]))

    selected_labels: set[int] = set()
    filtered = np.asarray(low_threshold_products["filtered_segmentation"])
    if np.any(spike_samples) and np.any(filtered > 0):
        spike_aperture = spike_samples_to_image_aperture(
            data.shape,
            geometry,
            radii[spike_samples],
            half_width_arcsec=half_width,
            sample_half_width_arcsec=0.5 * geometry["pixel_scale"],
        )
        # Equivalent to testing each dilated segment against the spike aperture,
        # but vectorized: dilate the aperture once, then read intersecting labels.
        aperture_for_labels = dilate_mask(spike_aperture, int(params["dilation_radius"]))
        selected_labels = {int(label) for label in np.unique(filtered[aperture_for_labels]) if int(label) > 0}

    gated_segmentation = np.where(np.isin(filtered, list(selected_labels)), filtered, 0)
    gated_mask = dilate_mask(gated_segmentation > 0, int(params["dilation_radius"]))
    cleaned = np.array(data, copy=True)
    finite_unmasked = np.isfinite(data) & ~gated_mask
    replacement = float(np.nanmedian(data[finite_unmasked])) if np.any(finite_unmasked) else 0.0
    cleaned[gated_mask] = replacement

    rows = []
    for row in low_threshold_products["rows"]:
        updated = dict(row)
        updated["kept"] = int(row["label"]) in selected_labels
        rows.append(updated)

    return {
        **low_threshold_products,
        "filtered_segmentation": gated_segmentation,
        "mask": gated_mask,
        "cleaned": cleaned,
        "rows": rows,
        "spike_samples": spike_samples,
        "spike_gate_move_factor": float(params["spike_gate_move_factor"]),
    }


def measure_segments(segmentation: np.ndarray, residual: np.ndarray, geometry: dict[str, float]) -> list[dict[str, float | int]]:
    sigma = robust_sigma(residual)
    median = float(np.nanmedian(residual[np.isfinite(residual)]))
    rows: list[dict[str, float | int]] = []
    labels = [int(label) for label in np.unique(segmentation) if int(label) > 0]
    for label in labels:
        ys, xs = np.nonzero(segmentation == label)
        area = int(xs.size)
        if area == 0:
            continue
        values = np.asarray(residual[ys, xs], dtype=float)
        finite_values = np.isfinite(values)
        weights = np.where(finite_values, np.maximum(values - median, 0.0), 0.0)
        if np.sum(weights) <= 0:
            weights = np.ones(area, dtype=float)
        weight_sum = float(np.sum(weights))
        x = float(np.sum(xs * weights) / weight_sum)
        y = float(np.sum(ys * weights) / weight_sum)
        dx = xs - x
        dy = ys - y
        cov_xx = float(np.sum(weights * dx * dx) / weight_sum)
        cov_yy = float(np.sum(weights * dy * dy) / weight_sum)
        cov_xy = float(np.sum(weights * dx * dy) / weight_sum)
        common = math.sqrt(max(0.0, (cov_xx - cov_yy) ** 2 + 4.0 * cov_xy * cov_xy))
        major_var = max(0.0, 0.5 * (cov_xx + cov_yy + common))
        minor_var = max(0.0, 0.5 * (cov_xx + cov_yy - common))
        a = math.sqrt(major_var)
        b = math.sqrt(minor_var)
        elongation = a / b if b > 0 else np.inf
        peak = float(np.nanmax(values)) if np.any(finite_values) else math.nan
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
        if int(row["area"]) < int(params["minarea"]):
            keep = False
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


class MTObjectsTester(tk.Tk):
    def __init__(self, manifest: Path, pc_name: str, mtobjects_root: Path | None):
        super().__init__()
        self.title("MTObjects Parameter Tester")
        self._configure_window_size()
        self.manifest = manifest
        self.mtobjects_root = find_mtobjects_root(mtobjects_root)
        self.all_rows = display.read_manifest(manifest)
        self.pc_var = tk.StringVar(value=pc_name)
        self.mtobjects_root_var = tk.StringVar(value=str(self.mtobjects_root) if self.mtobjects_root else "Not found")
        self.unit_var = tk.StringVar(value="Pixels")
        self.display_units = "pixels"
        self.output_dir = remove_foreground_folder(pc_name) / "interactive_mtobjects_parameter_tester"
        self.rows: list[dict[str, str]] = []
        self.rows_by_name: dict[str, dict[str, str]] = {}
        self.data_cache: dict[str, tuple[np.ndarray, fits.Header, dict[str, float]]] = {}
        self.calculating_overlay = None
        self.control_canvas: tk.Canvas | None = None
        self.control_canvas_window: int | None = None

        self._build_controls()
        self._build_figure()
        self.refresh_pc_paths(initial=True)

    def _configure_window_size(self) -> None:
        screen_width = max(900, self.winfo_screenwidth())
        screen_height = max(700, self.winfo_screenheight())
        width = min(1760, max(960, int(screen_width * 0.82)))
        height = min(1320, max(680, int(screen_height * 0.82)))
        x_pos = max(0, min(40, (screen_width - width) // 2))
        y_pos = max(0, min(40, (screen_height - height) // 2))
        self.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        self.minsize(900, 620)
        self.maxsize(screen_width * 2, screen_height * 2)
        self.resizable(True, True)

    def _build_controls(self) -> None:
        control_outer = ttk.Frame(self, width=370)
        control_outer.pack(side=tk.LEFT, fill=tk.Y)
        control_outer.pack_propagate(False)

        self.control_canvas = tk.Canvas(control_outer, width=350, highlightthickness=0)
        control_scrollbar = ttk.Scrollbar(control_outer, orient=tk.VERTICAL, command=self.control_canvas.yview)
        self.control_canvas.configure(yscrollcommand=control_scrollbar.set)
        control_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.control_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        control = ttk.Frame(self.control_canvas, padding=10)
        self.control_canvas_window = self.control_canvas.create_window((0, 0), window=control, anchor=tk.NW)
        control.bind("<Configure>", self._update_control_scroll_region)
        self.control_canvas.bind("<Configure>", self._fit_control_width)
        self.bind_all("<MouseWheel>", self._scroll_controls_with_mousewheel, add="+")
        self.bind_all("<Button-4>", self._scroll_controls_with_mousewheel, add="+")
        self.bind_all("<Button-5>", self._scroll_controls_with_mousewheel, add="+")

        ttk.Label(control, text="Machine").pack(anchor=tk.W)
        pc_combo = ttk.Combobox(control, textvariable=self.pc_var, values=sorted(PC_RESEARCH_FOLDERS), state="readonly")
        pc_combo.pack(fill=tk.X, pady=(0, 8))
        pc_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_pc_paths())

        ttk.Label(control, text="MTObjects root").pack(anchor=tk.W)
        mtobjects_row = ttk.Frame(control)
        mtobjects_row.pack(fill=tk.X, pady=(0, 8))
        mtobjects_entry = ttk.Entry(mtobjects_row, textvariable=self.mtobjects_root_var)
        mtobjects_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        mtobjects_entry.bind("<Return>", lambda _event: self.set_mtobjects_root_from_entry())
        mtobjects_entry.bind("<FocusOut>", lambda _event: self.set_mtobjects_root_from_entry(silent=True))
        ttk.Button(mtobjects_row, text="Browse", command=self.browse_mtobjects_root).pack(side=tk.LEFT, padx=(4, 0))

        ttk.Label(control, text="Galaxy").pack(anchor=tk.W)
        self.galaxy_var = tk.StringVar()
        self.galaxy_combo = ttk.Combobox(control, textvariable=self.galaxy_var, state="readonly")
        self.galaxy_combo.pack(fill=tk.X, pady=(0, 10))
        self.galaxy_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_selected_galaxy())

        ttk.Label(control, text="Detect on").pack(anchor=tk.W)
        self.detect_on_var = tk.StringVar(value="residual")
        detect_combo = ttk.Combobox(control, textvariable=self.detect_on_var, values=["residual", "original"], state="readonly")
        detect_combo.pack(fill=tk.X, pady=(0, 8))
        detect_combo.bind("<<ComboboxSelected>>", lambda _event: self.mark_needs_calculation())

        ttk.Label(control, text="Parameter units").pack(anchor=tk.W)
        unit_combo = ttk.Combobox(
            control,
            textvariable=self.unit_var,
            values=list(PARAMETER_UNIT_LABELS),
            state="readonly",
        )
        unit_combo.pack(fill=tk.X, pady=(0, 8))
        unit_combo.bind("<<ComboboxSelected>>", lambda _event: self.change_parameter_units())

        self.vars: dict[str, tk.Variable] = {}
        self.readouts: dict[str, ttk.Label] = {}
        self.parameter_labels: dict[str, ttk.Label] = {}
        self.parameter_label_texts: dict[str, str] = {}

        spike_frame = ttk.LabelFrame(control, text="Spike Gate", padding=8)
        spike_frame.pack(fill=tk.X, pady=(4, 10))
        self._scale(spike_frame, "spike_gate_move_factor", "spike_gate_move_factor (higher = more aggressive gate)", 0.0, 1.0, 0.05, SPIKE_GATE_MOVE_FACTOR)
        self._scale(spike_frame, "spike_excess_fraction", "spike_excess_fraction (lower = more sensitive)", 0.05, 1.0, 0.05, DEFAULT_SPIKE_EXCESS_FRACTION)
        self._scale(
            spike_frame,
            "spike_neighbour_inner_arcsec",
            "spike_neighbour_inner_arcsec",
            1.0,
            20.0,
            0.5,
            DEFAULT_SPIKE_NEIGHBOUR_INNER_ARCSEC,
        )
        self._scale(
            spike_frame,
            "spike_neighbour_outer_arcsec",
            "spike_neighbour_outer_arcsec",
            5.0,
            40.0,
            0.5,
            DEFAULT_SPIKE_NEIGHBOUR_OUTER_ARCSEC,
        )
        self._spin(spike_frame, "spike_side_offset_samples", "spike_side_offset_samples", 1, 12, 1, DEFAULT_SPIKE_SIDE_OFFSET_SAMPLES)
        self._scale(spike_frame, "spike_side_drop_fraction", "spike_side_drop_fraction (lower = more sensitive)", 0.05, 1.5, 0.05, DEFAULT_SPIKE_SIDE_DROP_FRACTION)
        self._spin(spike_frame, "spike_window_samples", "spike_window_samples (higher = wider removal)", 0, 10, 1, DEFAULT_SPIKE_WINDOW_SAMPLES)

        mto_frame = ttk.LabelFrame(control, text="MTObjects", padding=8)
        mto_frame.pack(fill=tk.X, pady=(0, 8))
        self._spin(mto_frame, "alpha", "Significance alpha", 1.0e-8, 1.0e-3, 1.0e-6, DEFAULT_ALPHA)
        self._spin(mto_frame, "move_factor", "move_factor (higher = more aggressive)", 0.0, 1.0, 0.05, DEFAULT_MOVE_FACTOR)
        self._spin(mto_frame, "min_distance", "min_distance (lower = more aggressive)", 0.0, 100.0, 0.5, DEFAULT_MIN_DISTANCE)
        self._spin(mto_frame, "gaussian_fwhm", "gaussian_fwhm [px] (higher = smoother/broader)", 0.0, 8.0, 0.25, DEFAULT_GAUSSIAN_FWHM)
        self._spin(mto_frame, "soft_bias", "Soft bias", -1000.0, 1000.0, 1.0, DEFAULT_SOFT_BIAS)
        self._spin(mto_frame, "gain", "Gain (-1=estimate)", -1.0, 50.0, 0.5, DEFAULT_GAIN)
        self._spin(mto_frame, "bg_mean", "Background mean (NaN=estimate)", -1000.0, 1000.0, 1.0, DEFAULT_BG_MEAN)
        self._spin(mto_frame, "bg_variance", "Background variance (-1=estimate)", -1.0, 10000.0, 10.0, DEFAULT_BG_VARIANCE)

        filter_frame = ttk.LabelFrame(control, text="Post-filter", padding=8)
        filter_frame.pack(fill=tk.X, pady=(0, 8))
        self._spin(filter_frame, "minarea", "minarea [px] (lower = more aggressive)", 1, 80, 1, DEFAULT_MINAREA)
        self._spin(filter_frame, "dilation_radius", "dilation_radius [px] (higher = more aggressive)", 0, 12, 1, DEFAULT_DILATION_RADIUS)
        self._spin(filter_frame, "max_area", "max_area [px] (higher = more aggressive)", 10, 5000, 10, DEFAULT_MAX_AREA)
        self._scale(filter_frame, "max_elongation", "max_elongation (higher = more aggressive)", 1.0, 20.0, 0.25, DEFAULT_MAX_ELONGATION)
        self._scale(filter_frame, "exclude_center_pixels", "exclude_center_pixels [px] (lower = more aggressive)", 0.0, 120.0, 1.0, DEFAULT_EXCLUDE_CENTER_PIXELS)

        button_row = ttk.Frame(control)
        button_row.pack(fill=tk.X, pady=(12, 4))
        ttk.Button(button_row, text="Calculate", command=self.calculate_now).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(button_row, text="Reset", command=self.reset_parameters).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(control, text="Open PNG Folder", command=self.open_output_folder).pack(fill=tk.X, pady=(0, 4))

        self.status = tk.StringVar(value="")
        ttk.Label(control, textvariable=self.status, wraplength=310, justify=tk.LEFT).pack(fill=tk.X, pady=(10, 0))

    def _scale(self, parent, key, label, minimum, maximum, resolution, default) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=4)
        label_widget = ttk.Label(frame, text=self.label_for_display(key, label), wraplength=315, justify=tk.LEFT)
        label_widget.pack(anchor=tk.W)
        self.parameter_labels[key] = label_widget
        self.parameter_label_texts[key] = label
        row = ttk.Frame(frame)
        row.pack(fill=tk.X)
        var = tk.DoubleVar(value=float(self.convert_from_pixels(key, default)))
        self.vars[key] = var
        readout = ttk.Label(row, width=9)
        readout.pack(side=tk.RIGHT)
        self.readouts[key] = readout
        scale = tk.Scale(
            row,
            variable=var,
            from_=minimum,
            to=maximum,
            resolution=resolution,
            orient=tk.HORIZONTAL,
            showvalue=False,
            command=lambda _value, k=key: self.parameter_changed(k),
        )
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.parameter_changed(key, mark=False)

    def _spin(self, parent, key, label, minimum, maximum, increment, default) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=4)
        label_widget = ttk.Label(frame, text=self.label_for_display(key, label), wraplength=315, justify=tk.LEFT)
        label_widget.pack(anchor=tk.W)
        self.parameter_labels[key] = label_widget
        self.parameter_label_texts[key] = label
        if key in PIXEL_LINEAR_PARAMS or key in PIXEL_AREA_PARAMS or key in FLOAT_SPIN_PARAMS:
            var = tk.DoubleVar(value=float(self.convert_from_pixels(key, default)))
        else:
            var = tk.IntVar(value=default)
        spin_options = {}
        if key in FLOAT_SPIN_PARAMS:
            spin_options["format"] = "%.6g"
        self.vars[key] = var
        spin = ttk.Spinbox(
            frame,
            textvariable=var,
            from_=self.convert_from_pixels(key, minimum),
            to=self.convert_from_pixels(key, maximum),
            increment=self.convert_from_pixels(key, increment),
            width=10,
            **spin_options,
        )
        spin.pack(anchor=tk.E, pady=(2, 0))
        spin.configure(command=self.mark_needs_calculation)
        spin.bind("<Return>", lambda _event: self.mark_needs_calculation())
        spin.bind("<FocusOut>", lambda _event: self.mark_needs_calculation())

    def _build_figure(self) -> None:
        frame = ttk.Frame(self)
        frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.figure = Figure(figsize=(11.0, 8.0), dpi=100, constrained_layout=True)
        grid = self.figure.add_gridspec(5, 2, height_ratios=[0.26, 1.0, 1.0, 1.0, 1.0])
        profile_grid = grid[1:, 1].subgridspec(3, 1)
        self.ax_parameters = self.figure.add_subplot(grid[0, :])
        self.ax_original = self.figure.add_subplot(grid[1, 0])
        self.ax_residual = self.figure.add_subplot(grid[2, 0])
        self.ax_original_isophote = self.figure.add_subplot(grid[3, 0])
        self.ax_cleaned_isophote = self.figure.add_subplot(grid[4, 0])
        self.ax_original_profile = self.figure.add_subplot(profile_grid[0, 0])
        self.ax_cleaned_profile = self.figure.add_subplot(profile_grid[1, 0])
        self.ax_cleaned = self.figure.add_subplot(profile_grid[2, 0])
        self.ax_parameters.set_axis_off()
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(self.canvas, frame)
        toolbar.update()
        frame.bind("<Configure>", self._resize_figure_to_panel)

    def _update_control_scroll_region(self, _event: tk.Event) -> None:
        if self.control_canvas is not None:
            self.control_canvas.configure(scrollregion=self.control_canvas.bbox("all"))

    def _fit_control_width(self, event: tk.Event) -> None:
        if self.control_canvas is not None and self.control_canvas_window is not None:
            self.control_canvas.itemconfigure(self.control_canvas_window, width=max(1, int(event.width)))

    def _pointer_is_over_controls(self) -> bool:
        if self.control_canvas is None:
            return False
        pointer_x = self.control_canvas.winfo_pointerx()
        pointer_y = self.control_canvas.winfo_pointery()
        left = self.control_canvas.winfo_rootx()
        top = self.control_canvas.winfo_rooty()
        right = left + self.control_canvas.winfo_width()
        bottom = top + self.control_canvas.winfo_height()
        return left <= pointer_x <= right and top <= pointer_y <= bottom

    def _scroll_controls_with_mousewheel(self, event: tk.Event) -> str | None:
        if self.control_canvas is None or not self._pointer_is_over_controls():
            return None
        if getattr(event, "num", None) == 4:
            units = -3
        elif getattr(event, "num", None) == 5:
            units = 3
        else:
            delta = int(getattr(event, "delta", 0))
            units = -1 * (delta // 120) if delta else 0
        if units:
            self.control_canvas.yview_scroll(units, "units")
        return "break"

    def _resize_figure_to_panel(self, event: tk.Event) -> None:
        if not hasattr(self, "figure") or not hasattr(self, "canvas"):
            return
        toolbar_allowance = 44
        width_inches = max(6.0, float(event.width) / self.figure.dpi)
        height_inches = max(5.0, float(max(1, event.height - toolbar_allowance)) / self.figure.dpi)
        current_width, current_height = self.figure.get_size_inches()
        if abs(current_width - width_inches) > 0.1 or abs(current_height - height_inches) > 0.1:
            self.figure.set_size_inches(width_inches, height_inches, forward=False)
            self.canvas.draw_idle()

    def browse_mtobjects_root(self) -> None:
        initial_dir = str(self.mtobjects_root) if self.mtobjects_root else str(Path.home() / "Documents" / "Github")
        selected = filedialog.askdirectory(title="Select CarolineHaigh/mtobjects checkout", initialdir=initial_dir)
        if not selected:
            return
        self.mtobjects_root_var.set(selected)
        self.set_mtobjects_root_from_entry()

    def set_mtobjects_root_from_entry(self, silent: bool = False) -> None:
        value = self.mtobjects_root_var.get().strip()
        if not value or value == "Not found":
            self.mtobjects_root = None
            return
        root = Path(value).expanduser()
        if is_mtobjects_root(root):
            self.mtobjects_root = root.resolve()
            self.mtobjects_root_var.set(str(self.mtobjects_root))
            self.mark_needs_calculation()
            return
        self.mtobjects_root = None
        if not silent:
            messagebox.showerror("Invalid MTObjects root", f"Could not find an mtolib folder in:\n{root}")

    def parameter_changed(self, key: str, mark: bool = True) -> None:
        if key in self.readouts:
            self.readouts[key].configure(text=self.format_parameter_value(key, float(self.vars[key].get())))
        if mark:
            self.mark_needs_calculation()

    def format_parameter_value(self, key: str, value: float) -> str:
        if key == "alpha":
            return f"{value:.0e}"
        if abs(value) >= 1000 or (0 < abs(value) < 0.01):
            return f"{value:.3g}"
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def pixel_scale_for_units(self) -> float:
        name = self.galaxy_var.get() if hasattr(self, "galaxy_var") else ""
        if not name:
            return 1.0
        try:
            _data, _header, geometry = self._load_galaxy(name)
        except Exception:  # noqa: BLE001
            return 1.0
        return float(geometry.get("pixel_scale", 1.0)) or 1.0

    def convert_from_pixels(self, key: str, value: float | int, units: str | None = None) -> float:
        units = self.display_units if units is None else units
        number = float(value)
        if units != "arcsec":
            return number
        pixel_scale = self.pixel_scale_for_units()
        if key in PIXEL_LINEAR_PARAMS:
            return number * pixel_scale
        if key in PIXEL_AREA_PARAMS:
            return number * pixel_scale * pixel_scale
        return number

    def convert_to_pixels(self, key: str, value: float | int, units: str | None = None) -> float:
        units = self.display_units if units is None else units
        number = float(value)
        if units != "arcsec":
            return number
        pixel_scale = self.pixel_scale_for_units()
        if key in PIXEL_LINEAR_PARAMS:
            return number / pixel_scale
        if key in PIXEL_AREA_PARAMS:
            return number / (pixel_scale * pixel_scale)
        return number

    def label_for_display(self, key: str, label: str) -> str:
        if self.display_units != "arcsec":
            return label
        if key in PIXEL_AREA_PARAMS:
            return label.replace("[px]", "[as^2]")
        if key in PIXEL_LINEAR_PARAMS:
            return label.replace("[px]", "[as]")
        return label

    def refresh_parameter_unit_labels(self) -> None:
        for key, label in self.parameter_labels.items():
            label.configure(text=self.label_for_display(key, self.parameter_label_texts[key]))

    def change_parameter_units(self) -> None:
        new_units = PARAMETER_UNIT_LABELS.get(self.unit_var.get(), "pixels")
        old_units = self.display_units
        if new_units == old_units:
            return
        for key, var in self.vars.items():
            if key not in PIXEL_LINEAR_PARAMS and key not in PIXEL_AREA_PARAMS:
                continue
            pixel_value = self.convert_to_pixels(key, float(var.get()), old_units)
            var.set(self.convert_from_pixels(key, pixel_value, new_units))
            if key in self.readouts:
                self.readouts[key].configure(text=self.format_parameter_value(key, float(var.get())))
        self.display_units = new_units
        self.refresh_parameter_unit_labels()
        self.mark_needs_calculation()

    def current_params(self) -> dict[str, float | int | str]:
        return {
            "detect_on": self.detect_on_var.get(),
            "alpha": float(self.vars["alpha"].get()),
            "move_factor": float(self.vars["move_factor"].get()),
            "min_distance": float(self.vars["min_distance"].get()),
            "gaussian_fwhm": float(self.vars["gaussian_fwhm"].get()),
            "soft_bias": float(self.vars["soft_bias"].get()),
            "gain": float(self.vars["gain"].get()),
            "bg_mean": float(self.vars["bg_mean"].get()),
            "bg_variance": float(self.vars["bg_variance"].get()),
            "minarea": max(1, int(round(self.convert_to_pixels("minarea", float(self.vars["minarea"].get()))))),
            "dilation_radius": max(
                0, int(round(self.convert_to_pixels("dilation_radius", float(self.vars["dilation_radius"].get()))))
            ),
            "max_area": max(1, int(round(self.convert_to_pixels("max_area", float(self.vars["max_area"].get()))))),
            "max_elongation": float(self.vars["max_elongation"].get()),
            "exclude_center_pixels": self.convert_to_pixels(
                "exclude_center_pixels", float(self.vars["exclude_center_pixels"].get())
            ),
            "spike_gate_move_factor": float(self.vars["spike_gate_move_factor"].get()),
            "spike_excess_fraction": float(self.vars["spike_excess_fraction"].get()),
            "spike_neighbour_inner_arcsec": float(self.vars["spike_neighbour_inner_arcsec"].get()),
            "spike_neighbour_outer_arcsec": float(self.vars["spike_neighbour_outer_arcsec"].get()),
            "spike_side_offset_samples": int(self.vars["spike_side_offset_samples"].get()),
            "spike_side_drop_fraction": float(self.vars["spike_side_drop_fraction"].get()),
            "spike_window_samples": int(self.vars["spike_window_samples"].get()),
        }

    def reset_parameters(self) -> None:
        defaults = {
            "alpha": DEFAULT_ALPHA,
            "move_factor": DEFAULT_MOVE_FACTOR,
            "min_distance": DEFAULT_MIN_DISTANCE,
            "gaussian_fwhm": DEFAULT_GAUSSIAN_FWHM,
            "soft_bias": DEFAULT_SOFT_BIAS,
            "gain": DEFAULT_GAIN,
            "bg_mean": DEFAULT_BG_MEAN,
            "bg_variance": DEFAULT_BG_VARIANCE,
            "minarea": DEFAULT_MINAREA,
            "dilation_radius": DEFAULT_DILATION_RADIUS,
            "max_area": DEFAULT_MAX_AREA,
            "max_elongation": DEFAULT_MAX_ELONGATION,
            "exclude_center_pixels": DEFAULT_EXCLUDE_CENTER_PIXELS,
            "spike_gate_move_factor": SPIKE_GATE_MOVE_FACTOR,
            "spike_excess_fraction": DEFAULT_SPIKE_EXCESS_FRACTION,
            "spike_neighbour_inner_arcsec": DEFAULT_SPIKE_NEIGHBOUR_INNER_ARCSEC,
            "spike_neighbour_outer_arcsec": DEFAULT_SPIKE_NEIGHBOUR_OUTER_ARCSEC,
            "spike_side_offset_samples": DEFAULT_SPIKE_SIDE_OFFSET_SAMPLES,
            "spike_side_drop_fraction": DEFAULT_SPIKE_SIDE_DROP_FRACTION,
            "spike_window_samples": DEFAULT_SPIKE_WINDOW_SAMPLES,
        }
        for key, value in defaults.items():
            self.vars[key].set(self.convert_from_pixels(key, value))
            self.parameter_changed(key, mark=False)
        self.detect_on_var.set("residual")
        self.mark_needs_calculation()

    def refresh_pc_paths(self, initial: bool = False) -> None:
        pc_name = self.pc_var.get()
        self.output_dir = remove_foreground_folder(pc_name) / "interactive_mtobjects_parameter_tester"
        self.rows = display.rows_with_images_for_pc(self.all_rows, pc_name)
        if not self.rows:
            raise RuntimeError(f"No FITS images were found for {pc_name} in {erwin_folder(pc_name) / 's4g_images_36um'}.")
        names = [row["name"] for row in self.rows]
        self.rows_by_name = {row["name"]: row for row in self.rows}
        self.data_cache.clear()
        self.galaxy_combo.configure(values=names)
        current = self.galaxy_var.get()
        selected = current if current in self.rows_by_name else (DEFAULT_GALAXY if initial and DEFAULT_GALAXY in self.rows_by_name else names[0])
        self.galaxy_var.set(selected)
        self.load_selected_galaxy()

    def load_selected_galaxy(self) -> None:
        try:
            self._load_galaxy(self.galaxy_var.get())
            self.mark_needs_calculation()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Could not load galaxy", str(exc))

    def _load_galaxy(self, name: str) -> tuple[np.ndarray, fits.Header, dict[str, float]]:
        if name in self.data_cache:
            return self.data_cache[name]
        row = self.rows_by_name[name]
        geometry = display.required_geometry(row)
        if geometry is None:
            raise ValueError(f"{name} has incomplete geometry in {self.manifest}.")
        data, header = load_fits(display.image_path_for_pc(row, self.pc_var.get()))
        self.data_cache[name] = (data, header, geometry)
        return data, header, geometry

    def mark_needs_calculation(self) -> None:
        name = self.galaxy_var.get()
        if name:
            if self.mtobjects_root is None:
                self.status.set(
                    f"{self.pc_var.get()} | {name}: select a CarolineHaigh/mtobjects checkout before calculating."
                )
            else:
                self.status.set(f"{self.pc_var.get()} | {name}: click Calculate to run MTObjects.")

    def output_png_path(self, params: dict[str, float | int | str]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = (
            f"{display.safe_filename(self.galaxy_var.get())}_mtobjects_"
            f"move{float(params['move_factor']):.2f}_"
            f"alpha{float(params['alpha']):.0e}_"
            f"area{int(params['minarea'])}_"
            f"dil{int(params['dilation_radius'])}_"
            f"{timestamp}"
        )
        path = self.output_dir / f"{display.safe_filename(stem)}.png"
        counter = 1
        while path.exists():
            path = self.output_dir / f"{display.safe_filename(stem)}_{counter}.png"
            counter += 1
        return path

    def open_output_folder(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(["explorer", str(self.output_dir)])
        except OSError as exc:
            messagebox.showerror("Could not open PNG folder", str(exc))

    def calculate_now(self) -> None:
        name = self.galaxy_var.get()
        try:
            self.status.set(f"Calculating {name} with MTObjects...")
            self._show_calculating_overlay()
            self.update_idletasks()
            data, _header, geometry = self._load_galaxy(name)
            params = self.current_params()
            products = mtobjects_products(data, params, geometry, self.mtobjects_root)
            spike_products = spike_gated_mtobjects_products(data, params, geometry, self.mtobjects_root)
            self.draw_products(name, data, products, spike_products, params, geometry)
            png_path = self.output_png_path(params)
            self.figure.savefig(png_path, dpi=180)
            kept = sum(1 for row in products["rows"] if row.get("kept"))
            spike_kept = sum(1 for row in spike_products["rows"] if row.get("kept"))
            spike_count = int(np.count_nonzero(spike_products["spike_samples"]))
            masked_fraction = np.count_nonzero(products["mask"]) / products["mask"].size
            spike_masked_fraction = np.count_nonzero(spike_products["mask"]) / spike_products["mask"].size
            self.status.set(
                f"{self.pc_var.get()} | {name} | MTObjects kept {kept} segments, "
                f"masked {masked_fraction:.2%} of pixels. "
                f"Spike gate kept {spike_kept} gate-run segments from {spike_count} spike samples, "
                f"masked {spike_masked_fraction:.2%}.\n"
                f"Output: {self.output_dir}\nSaved PNG: {png_path.name}"
            )
        except Exception as exc:  # noqa: BLE001
            self._remove_calculating_overlay()
            self.status.set(f"Error: {exc}")
            messagebox.showerror("MTObjects calculation failed", str(exc))

    def draw_products(self, name, original, products, spike_products, params, geometry) -> None:
        self._remove_calculating_overlay()
        cleaned = np.asarray(products["cleaned"], dtype=float)
        residual = np.asarray(products["residual"], dtype=float)
        mask = np.asarray(products["mask"], dtype=bool)
        spike_mask = np.asarray(spike_products["mask"], dtype=bool)
        spike_samples = np.asarray(spike_products["spike_samples"], dtype=bool)
        radius_arcsec = display.profile_radius_pixels(original, geometry) * geometry["pixel_scale"]
        original_view, x_axis, y_axis = display.deproject_bar_aligned_cutout(original, geometry, radius_arcsec)
        cleaned_view, _, _ = display.deproject_bar_aligned_cutout(cleaned, geometry, radius_arcsec)
        residual_view, _, _ = display.deproject_bar_aligned_cutout(residual, geometry, radius_arcsec)
        mask_view, _, _ = display.deproject_bar_aligned_cutout(mask.astype(float), geometry, radius_arcsec, order=0)
        mask_view = np.isfinite(mask_view) & (mask_view > 0.5)
        spike_mask_view, _, _ = display.deproject_bar_aligned_cutout(spike_mask.astype(float), geometry, radius_arcsec, order=0)
        spike_mask_view = np.isfinite(spike_mask_view) & (spike_mask_view > 0.5)
        extent = [x_axis[0], x_axis[-1], y_axis[0], y_axis[-1]]
        half_width = 0.5 * DEFAULT_PROFILE_WIDTH_PIXELS * geometry["pixel_scale"]
        mask_profile = profile_mask_at_bar_major(mask_view, y_axis, half_width)
        spike_mask_profile = profile_mask_at_bar_major(spike_mask_view, y_axis, half_width)
        bar_sma = display.bar_sma_deprojected_arcsec(geometry)
        central_exclusion_arcsec = float(params["exclude_center_pixels"]) * geometry["pixel_scale"]
        profile_y_limits = self.shared_profile_y_limits(
            original_view,
            x_axis,
            y_axis,
            half_width,
            mask_profile,
            spike_mask_profile,
        )
        axes = [
            self.ax_parameters,
            self.ax_original,
            self.ax_residual,
            self.ax_original_isophote,
            self.ax_cleaned_isophote,
            self.ax_original_profile,
            self.ax_cleaned_profile,
            self.ax_cleaned,
        ]
        for ax in axes:
            ax.clear()
        self.ax_parameters.set_axis_off()
        self.draw_parameter_box(params, products)
        for ax in axes[1:]:
            ax.set_xlabel("bar-aligned arcsec")
            ax.set_ylabel("deprojected arcsec")

        vmin, vmax = display.robust_limits(original_view)
        self.ax_original.imshow(original_view, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax, extent=extent)
        self.draw_bar_guides(self.ax_original, half_width, bar_sma)
        self.draw_central_exclusion(self.ax_original, central_exclusion_arcsec)
        self.ax_original.set_title(f"{name} centered original")

        rvmin, rvmax = display.robust_limits(residual_view, 1.0, 99.0)
        limit = max(abs(rvmin), abs(rvmax))
        self.ax_residual.imshow(residual_view, origin="lower", cmap="coolwarm", vmin=-limit, vmax=limit, extent=extent)
        self.draw_bar_guides(self.ax_residual, half_width, bar_sma)
        self.draw_central_exclusion(self.ax_residual, central_exclusion_arcsec)
        self.ax_residual.set_title("Residual detection image")

        self.draw_isophote(
            self.ax_original_isophote,
            original_view,
            x_axis,
            y_axis,
            extent,
            f"{name} original isophotes",
            half_width,
            bar_sma,
            central_exclusion_arcsec,
        )
        self.draw_isophote(
            self.ax_cleaned_isophote,
            cleaned_view,
            x_axis,
            y_axis,
            extent,
            "MTObjects processed isophotes",
            half_width,
            bar_sma,
            central_exclusion_arcsec,
        )
        self.draw_profile(
            self.ax_original_profile,
            original_view,
            x_axis,
            y_axis,
            half_width,
            bar_sma,
            central_exclusion_arcsec,
            f"{name} original bar-major profile",
            y_limits=profile_y_limits,
        )
        self.draw_profile(
            self.ax_cleaned_profile,
            original_view,
            x_axis,
            y_axis,
            half_width,
            bar_sma,
            central_exclusion_arcsec,
            "MTObjects processed bar-major profile",
            mask_profile=mask_profile,
            y_limits=profile_y_limits,
        )
        self.draw_profile(
            self.ax_cleaned,
            original_view,
            x_axis,
            y_axis,
            half_width,
            bar_sma,
            central_exclusion_arcsec,
            f"MTObjects spike-gated bar profile | move={float(params['spike_gate_move_factor']):.2f}",
            mask_profile=spike_mask_profile,
            spike_samples=spike_samples,
            y_limits=profile_y_limits,
        )
        self.canvas.draw_idle()

    def draw_parameter_box(self, params, products) -> None:
        kept = sum(1 for row in products["rows"] if row.get("kept"))
        raw = len(products["rows"])
        masked_fraction = np.count_nonzero(products["mask"]) / products["mask"].size
        text = (
            "MTObjects max-tree filtering   "
            f"units={self.unit_var.get()}   "
            f"detect_on={params['detect_on']}   "
            f"alpha={float(params['alpha']):.0e}   "
            f"move={float(params['move_factor']):.2f}   "
            f"min_distance={float(params['min_distance']):.2g}   "
            f"minarea={int(params['minarea'])}   "
            f"dilation={int(params['dilation_radius'])}   "
            f"bkg={float(products['background_level']):.4g}, rms={float(products['background_rms']):.4g}   |   "
            f"segments={kept}/{raw}   masked={masked_fraction:.2%}"
        )
        self.ax_parameters.text(
            0.5,
            0.5,
            text,
            transform=self.ax_parameters.transAxes,
            ha="center",
            va="center",
            fontsize=9.3,
            color="0.12",
            bbox={"boxstyle": "round,pad=0.45", "facecolor": "#F4F6F9", "edgecolor": "#6B7280", "linewidth": 0.8},
        )

    def draw_bar_guides(self, ax, half_width: float, bar_sma: float) -> None:
        ax.axhline(0.0, color="#1f77b4", linewidth=1.5)
        ax.axhline(half_width, color="#1f77b4", linestyle="--", linewidth=1.0, alpha=0.9)
        ax.axhline(-half_width, color="#1f77b4", linestyle="--", linewidth=1.0, alpha=0.9)
        ax.axvline(0.0, color="#d62728", linestyle="--", linewidth=1.0, alpha=0.8)
        ax.plot([-bar_sma, bar_sma], [0.0, 0.0], "o", color="#1f77b4", ms=4)

    def draw_central_exclusion(self, ax, radius_arcsec: float) -> None:
        if radius_arcsec <= 0:
            return
        theta = np.linspace(0.0, 2.0 * np.pi, 241)
        ax.plot(
            radius_arcsec * np.cos(theta),
            radius_arcsec * np.sin(theta),
            color="#ffd400",
            linestyle="--",
            linewidth=1.4,
            alpha=0.95,
        )

    def shared_profile_y_limits(
        self,
        image,
        x_axis,
        y_axis,
        half_width,
        *mask_profiles: np.ndarray,
    ) -> tuple[float, float]:
        _radii, intensity = display.bar_major_axis_profile(image, x_axis, y_axis, half_width)
        values = [intensity]
        for mask_profile in mask_profiles:
            bridged_intensity, _bridged_samples = fill_profile_with_log_linear_bridges(intensity, mask_profile)
            values.append(bridged_intensity)
        finite_positive = np.concatenate([item[np.isfinite(item) & (item > 0)] for item in values])
        if finite_positive.size == 0:
            return (1.0, 10.0)
        ymin = max(float(np.nanpercentile(finite_positive, 2)) * 0.8, np.finfo(float).tiny)
        ymax = float(np.nanmax(finite_positive)) * 1.25
        if not math.isfinite(ymin) or not math.isfinite(ymax) or ymax <= ymin:
            return (1.0, 10.0)
        return ymin, ymax

    def draw_isophote(self, ax, image, x_axis, y_axis, extent, title, half_width, bar_sma, central_exclusion_arcsec) -> None:
        log_image, levels = display.robust_log_image(image)
        ax.imshow(log_image, origin="lower", extent=extent, cmap="Greys", vmin=levels[0], vmax=levels[-1])
        ax.contour(x_axis, y_axis, log_image, levels=levels[1:-1], colors="0.25", linewidths=0.45)
        self.draw_bar_guides(ax, half_width, bar_sma)
        self.draw_central_exclusion(ax, central_exclusion_arcsec)
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(title)

    def draw_profile(
        self,
        ax,
        image,
        x_axis,
        y_axis,
        half_width,
        bar_sma,
        central_exclusion_arcsec,
        title,
        mask_profile: np.ndarray | None = None,
        spike_samples: np.ndarray | None = None,
        y_limits: tuple[float, float] | None = None,
    ) -> None:
        radii, intensity = display.bar_major_axis_profile(image, x_axis, y_axis, half_width)
        if mask_profile is not None:
            bridged_intensity, bridged_samples = fill_profile_with_log_linear_bridges(intensity, mask_profile)
            displayed_intensity = np.array(intensity, copy=True)
            displayed_intensity[bridged_samples] = np.nan
        else:
            bridged_intensity = None
            bridged_samples = np.zeros(intensity.size, dtype=bool)
            displayed_intensity = intensity
        positive = np.isfinite(intensity) & (intensity > 0)
        if bridged_intensity is not None:
            positive |= np.isfinite(bridged_intensity) & (bridged_intensity > 0)
        ymin, ymax = (1.0, 10.0)
        if np.any(positive):
            reference = bridged_intensity if bridged_intensity is not None else intensity
            ymin = max(float(np.nanpercentile(reference[positive], 2)) * 0.8, np.finfo(float).tiny)
            ymax = float(np.nanmax(reference[positive])) * 1.25
        if y_limits is not None:
            ymin, ymax = y_limits
        if mask_profile is not None:
            for start, stop in contiguous_true_runs(mask_profile):
                ax.axvspan(radii[start], radii[stop], color="red", alpha=0.14, linewidth=0)
        if spike_samples is not None and spike_samples.size == radii.size:
            finite_spikes = spike_samples & np.isfinite(radii)
            if np.any(finite_spikes):
                ax.vlines(
                    radii[finite_spikes],
                    ymin,
                    ymax,
                    color="#2ca02c",
                    linewidth=0.7,
                    alpha=0.28,
                    label="spike-gate samples",
                )
        ax.semilogy(radii, displayed_intensity, color="#1f77b4", linewidth=1.4)
        if bridged_intensity is not None:
            bridge_label = "log-linear interpolation"
            for start, stop in contiguous_true_runs(bridged_samples):
                plot_start = max(0, start - 1)
                plot_stop = min(bridged_intensity.size - 1, stop + 1)
                bridge_slice = slice(plot_start, plot_stop + 1)
                bridge_good = (
                    np.isfinite(radii[bridge_slice])
                    & np.isfinite(bridged_intensity[bridge_slice])
                    & (bridged_intensity[bridge_slice] > 0)
                )
                if np.count_nonzero(bridge_good) < 2:
                    continue
                ax.semilogy(
                    radii[bridge_slice][bridge_good],
                    bridged_intensity[bridge_slice][bridge_good],
                    color="#1f77b4",
                    linestyle="--",
                    linewidth=1.4,
                    label=bridge_label,
                )
                bridge_label = "_nolegend_"
        ax.axvline(bar_sma, color="#1f77b4", linewidth=1.0)
        ax.axvline(-bar_sma, color="#1f77b4", linewidth=1.0)
        if central_exclusion_arcsec > 0:
            ax.axvline(central_exclusion_arcsec, color="#b59b00", linestyle="--", linewidth=1.1, alpha=0.95)
            ax.axvline(-central_exclusion_arcsec, color="#b59b00", linestyle="--", linewidth=1.1, alpha=0.95)
        ax.axvline(0.0, color="0.6", linewidth=0.7)
        ax.set_xlim(float(x_axis[0]), float(x_axis[-1]))
        ax.set_ylim(ymin, ymax)
        ax.set_xlabel("deprojected bar-major radius [arcsec]")
        ax.set_ylabel("intensity")
        ax.set_title(title)
        ax.grid(True, which="both", alpha=0.2)
        if spike_samples is not None:
            ax.legend(loc="best", fontsize=8)

    def _show_calculating_overlay(self) -> None:
        self._remove_calculating_overlay()
        overlay = self.figure.add_axes((0, 0, 1, 1), zorder=1000)
        overlay.set_axis_off()
        overlay.patch.set_facecolor("0.78")
        overlay.patch.set_alpha(0.68)
        overlay.text(
            0.5,
            0.5,
            "Calculating",
            transform=overlay.transAxes,
            ha="center",
            va="center",
            fontsize=30,
            fontweight="bold",
            color="0.12",
            bbox={"boxstyle": "round,pad=0.45", "facecolor": "white", "edgecolor": "0.35", "alpha": 0.92},
        )
        self.calculating_overlay = overlay
        self.canvas.draw()
        self.canvas.flush_events()

    def _remove_calculating_overlay(self) -> None:
        if self.calculating_overlay is None:
            return
        self.calculating_overlay.remove()
        self.calculating_overlay = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--pc", choices=sorted(PC_RESEARCH_FOLDERS), default=DEFAULT_PC)
    parser.add_argument(
        "--mtobjects-root",
        type=Path,
        default=Path(DEFAULT_MTOBJECTS_ROOT) if DEFAULT_MTOBJECTS_ROOT else None,
        help="Path to a compiled CarolineHaigh/mtobjects checkout. Can also be set with MTOBJECTS_ROOT.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = MTObjectsTester(args.manifest, args.pc, args.mtobjects_root)
    app.mainloop()


if __name__ == "__main__":
    main()
