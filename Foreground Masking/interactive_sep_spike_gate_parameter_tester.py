#!/usr/bin/env python3
"""Interactive SEP plus Spike-Gate foreground-mask parameter tester.

SEP is a Python library for source detection and segmentation. This tester
keeps the local S4G manifest workflow and compares normal SEP profile masking
against a low-threshold SEP pass gated by bar-profile spike detection.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import math
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")

import numpy as np
import sep
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
DEFAULT_DETECT_THRESH = 3.0
SPIKE_GATE_DETECT_THRESH = 0.5
DEFAULT_MINAREA = 5
DEFAULT_DEBLEND_NTHRESH = 32
DEFAULT_DEBLEND_CONT = 0.005
DEFAULT_BACK_SIZE = 64
DEFAULT_FILTER_SIZE = 3
DEFAULT_DILATION_RADIUS = 2
DEFAULT_MAX_AREA = 230
DEFAULT_MAX_ELONGATION = 6.0
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
    "back_size",
    "filter_size",
    "dilation_radius",
    "exclude_center_pixels",
}
PIXEL_AREA_PARAMS = {
    "minarea",
    "max_area",
}
FLOAT_SPIN_PARAMS = {
    "detect_thresh",
}
INTEGER_SPIN_PARAMS = {
    "deblend_nthresh",
    "spike_side_offset_samples",
    "spike_window_samples",
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


def sep_products(data: np.ndarray, params: dict[str, float | int | str], geometry: dict[str, float]):
    detection, residual, nonfinite_mask = prepare_detection_image(data, str(params["detect_on"]))
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


def spike_gated_sep_products(
    data: np.ndarray,
    params: dict[str, float | int | str],
    geometry: dict[str, float],
) -> dict[str, object]:
    gate_params = dict(params)
    gate_params["detect_on"] = str(params.get("spike_gate_detect_on", "residual"))
    gate_params["detect_thresh"] = float(params["spike_gate_detect_thresh"])
    low_threshold_products = sep_products(data, gate_params, geometry)

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
        "spike_gate_detect_thresh": float(params["spike_gate_detect_thresh"]),
    }


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


class SEPTester(tk.Tk):
    def __init__(self, manifest: Path, pc_name: str):
        super().__init__()
        self.title("SEP + Spike Gate Parameter Tester")
        self._configure_window_size()
        self.manifest = manifest
        self.all_rows = display.read_manifest(manifest)
        self.pc_var = tk.StringVar(value=pc_name)
        self.unit_var = tk.StringVar(value="Pixels")
        self.display_units = "pixels"
        self.output_dir = remove_foreground_folder(pc_name) / "interactive_sep_spike_gate_parameter_tester"
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
        width = min(2100, max(1100, int(screen_width * 0.96)))
        height = min(1600, max(760, int(screen_height * 0.94)))
        x_pos = max(0, min(40, (screen_width - width) // 2))
        y_pos = max(0, min(40, (screen_height - height) // 2))
        self.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        self.minsize(900, 620)
        self.maxsize(screen_width * 2, screen_height * 2)
        self.resizable(True, True)

    def _build_controls(self) -> None:
        control_outer = ttk.Frame(self, width=305)
        control_outer.pack(side=tk.LEFT, fill=tk.Y)
        control_outer.pack_propagate(False)

        self.control_canvas = tk.Canvas(control_outer, width=285, highlightthickness=0)
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

        ttk.Label(control, text="Galaxy").pack(anchor=tk.W)
        self.galaxy_var = tk.StringVar()
        self.galaxy_combo = ttk.Combobox(control, textvariable=self.galaxy_var, state="readonly")
        self.galaxy_combo.pack(fill=tk.X, pady=(0, 10))
        self.galaxy_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_selected_galaxy())

        detect_row = ttk.Frame(control)
        detect_row.pack(fill=tk.X, pady=(0, 6))
        detect_row.columnconfigure(0, weight=1)
        detect_row.columnconfigure(1, weight=1)

        spike_gate_detect_frame = ttk.Frame(detect_row)
        spike_gate_detect_frame.grid(row=0, column=0, sticky=tk.EW, padx=(0, 4))
        ttk.Label(spike_gate_detect_frame, text="Spike Gate detects on").pack(anchor=tk.W)
        self.spike_gate_detect_on_var = tk.StringVar(value="residual")
        spike_gate_detect_combo = ttk.Combobox(
            spike_gate_detect_frame,
            textvariable=self.spike_gate_detect_on_var,
            values=["original", "residual"],
            state="readonly",
        )
        spike_gate_detect_combo.pack(fill=tk.X)
        spike_gate_detect_combo.bind("<<ComboboxSelected>>", lambda _event: self.mark_needs_calculation())

        sep_detect_frame = ttk.Frame(detect_row)
        sep_detect_frame.grid(row=0, column=1, sticky=tk.EW, padx=(4, 0))
        ttk.Label(sep_detect_frame, text="SEP detects on").pack(anchor=tk.W)
        self.detect_on_var = tk.StringVar(value="original")
        detect_combo = ttk.Combobox(sep_detect_frame, textvariable=self.detect_on_var, values=["original", "residual"], state="readonly")
        detect_combo.pack(fill=tk.X)
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
        self.spinboxes: dict[str, ttk.Spinbox] = {}
        self.parameter_labels: dict[str, ttk.Label] = {}
        self.parameter_label_texts: dict[str, str] = {}

        spike_frame = ttk.LabelFrame(control, text="Spike Gate", padding=6)
        spike_frame.pack(fill=tk.X, pady=(2, 6))
        self._scale(spike_frame, "spike_gate_detect_thresh", "spike_gate_detect_thresh (↓ = aggressive)", 0.5, 3.0, 0.1, SPIKE_GATE_DETECT_THRESH)
        self._scale(spike_frame, "spike_excess_fraction", "spike_excess_fraction (↓ = aggressive)", 0.05, 1.0, 0.05, DEFAULT_SPIKE_EXCESS_FRACTION)
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
        self._scale(spike_frame, "spike_side_drop_fraction", "spike_side_drop_fraction (↓ = aggressive)", 0.05, 1.5, 0.05, DEFAULT_SPIKE_SIDE_DROP_FRACTION)
        self._spin(spike_frame, "spike_window_samples", "spike_window_samples (↑ = aggressive)", 0, 10, 1, DEFAULT_SPIKE_WINDOW_SAMPLES)

        sep_frame = ttk.LabelFrame(control, text="SEP", padding=6)
        sep_frame.pack(fill=tk.X, pady=(0, 6))
        self._spin(sep_frame, "detect_thresh", "detect_thresh (↓ = aggressive)", 0.5, 10.0, 0.1, DEFAULT_DETECT_THRESH)
        self._spin(sep_frame, "minarea", "minarea [px] (↓ = aggressive)", 1, 80, 1, DEFAULT_MINAREA)
        self._spin(sep_frame, "deblend_nthresh", "deblend_nthresh", 8, 64, 1, DEFAULT_DEBLEND_NTHRESH)
        self._scale(sep_frame, "deblend_cont", "deblend_cont (↓ = aggressive split)", 0.0001, 0.1, 0.0005, DEFAULT_DEBLEND_CONT)
        self._spin(sep_frame, "back_size", "back_size [px]", 16, 256, 8, DEFAULT_BACK_SIZE)
        self._spin(sep_frame, "filter_size", "filter_size [px] (↑ = smoother/broader)", 1, 9, 2, DEFAULT_FILTER_SIZE)
        self._spin(sep_frame, "dilation_radius", "dilation_radius [px] (↑ = aggressive)", 0, 12, 1, DEFAULT_DILATION_RADIUS)
        self._spin(sep_frame, "max_area", "max_area [px] (↑ = aggressive)", 10, 5000, 10, DEFAULT_MAX_AREA)
        self._scale(sep_frame, "max_elongation", "max_elongation (↑ = aggressive)", 1.0, 20.0, 0.25, DEFAULT_MAX_ELONGATION)
        self._scale(sep_frame, "exclude_center_pixels", "exclude_center_pixels [px] (↓ = aggressive)", 0.0, 120.0, 1.0, DEFAULT_EXCLUDE_CENTER_PIXELS)

        button_row = ttk.Frame(control)
        button_row.pack(fill=tk.X, pady=(8, 3))
        ttk.Button(button_row, text="Calculate", command=self.calculate_now).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(button_row, text="Reset", command=self.reset_parameters).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(control, text="Open PNG Folder", command=self.open_output_folder).pack(fill=tk.X, pady=(0, 4))

        self.status = tk.StringVar(value="")
        ttk.Label(control, textvariable=self.status, wraplength=250, justify=tk.LEFT).pack(fill=tk.X, pady=(6, 0))

    def _scale(self, parent, key, label, minimum, maximum, resolution, default) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        label_widget = ttk.Label(frame, text=self.label_for_display(key, label), wraplength=250, justify=tk.LEFT)
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
        frame.pack(fill=tk.X, pady=2)
        frame.columnconfigure(0, weight=1)
        label_widget = ttk.Label(frame, text=self.label_for_display(key, label), wraplength=145, justify=tk.LEFT)
        label_widget.grid(row=0, column=0, sticky=tk.NW, padx=(0, 6))
        self.parameter_labels[key] = label_widget
        self.parameter_label_texts[key] = label
        if key in PIXEL_LINEAR_PARAMS or key in PIXEL_AREA_PARAMS or key in FLOAT_SPIN_PARAMS:
            var = tk.DoubleVar(value=float(self.convert_from_pixels(key, default)))
        else:
            var = tk.IntVar(value=default)
        spin_options = {"format": self.spinbox_format_for_key(key)}
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
        self.spinboxes[key] = spin
        spin.grid(row=0, column=1, sticky=tk.NE)
        self.format_spinbox_value(key)
        spin.configure(command=lambda k=key: self.spinbox_parameter_changed(k))
        spin.bind("<Return>", lambda _event, k=key: self.spinbox_parameter_changed(k))
        spin.bind("<FocusOut>", lambda _event, k=key: self.spinbox_parameter_changed(k))

    def _build_figure(self) -> None:
        frame = ttk.Frame(self)
        frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.figure = Figure(figsize=(13.0, 11.0), dpi=100, constrained_layout=False)
        self.figure.subplots_adjust(left=0.025, right=0.995, top=0.990, bottom=0.030, wspace=0.06, hspace=0.26)
        grid = self.figure.add_gridspec(
            5,
            2,
            height_ratios=[0.12, 1.18, 1.18, 1.18, 1.18],
            width_ratios=[1.0, 1.55],
        )
        profile_grid = grid[1:, 1].subgridspec(3, 1, hspace=0.34)
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

    def parameter_changed(self, key: str, mark: bool = True) -> None:
        if key in self.readouts:
            self.readouts[key].configure(text=self.format_parameter_value(key, float(self.vars[key].get())))
        if mark:
            self.mark_needs_calculation()

    def spinbox_parameter_changed(self, key: str, mark: bool = True) -> None:
        self.format_spinbox_value(key)
        if mark:
            self.mark_needs_calculation()

    def format_spinbox_value(self, key: str) -> None:
        spinbox = self.spinboxes.get(key)
        if spinbox is None:
            return
        value = float(self.vars[key].get())
        display_value = self.format_parameter_value(key, value)
        if spinbox.get() != display_value:
            spinbox.delete(0, tk.END)
            spinbox.insert(0, display_value)

    def format_parameter_value(self, key: str, value: float) -> str:
        if self.parameter_uses_integer_display(key):
            return f"{int(round(value))}"
        return f"{value:.2f}"

    def parameter_uses_integer_display(self, key: str) -> bool:
        if key in INTEGER_SPIN_PARAMS:
            return True
        return self.display_units == "pixels" and (key in PIXEL_LINEAR_PARAMS or key in PIXEL_AREA_PARAMS)

    def spinbox_format_for_key(self, key: str) -> str:
        if self.parameter_uses_integer_display(key):
            return "%.0f"
        return "%.2f"

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
        self.display_units = new_units
        for key, spinbox in self.spinboxes.items():
            spinbox.configure(format=self.spinbox_format_for_key(key))
            self.format_spinbox_value(key)
        for key, readout in self.readouts.items():
            readout.configure(text=self.format_parameter_value(key, float(self.vars[key].get())))
        self.refresh_parameter_unit_labels()
        self.mark_needs_calculation()

    def current_params(self) -> dict[str, float | int | str]:
        return {
            "detect_on": self.detect_on_var.get(),
            "spike_gate_detect_on": self.spike_gate_detect_on_var.get(),
            "detect_thresh": float(self.vars["detect_thresh"].get()),
            "minarea": max(1, int(round(self.convert_to_pixels("minarea", float(self.vars["minarea"].get()))))),
            "deblend_nthresh": int(self.vars["deblend_nthresh"].get()),
            "deblend_cont": float(self.vars["deblend_cont"].get()),
            "back_size": max(1, int(round(self.convert_to_pixels("back_size", float(self.vars["back_size"].get()))))),
            "filter_size": max(1, int(round(self.convert_to_pixels("filter_size", float(self.vars["filter_size"].get()))))),
            "dilation_radius": max(
                0, int(round(self.convert_to_pixels("dilation_radius", float(self.vars["dilation_radius"].get()))))
            ),
            "max_area": max(1, int(round(self.convert_to_pixels("max_area", float(self.vars["max_area"].get()))))),
            "max_elongation": float(self.vars["max_elongation"].get()),
            "exclude_center_pixels": self.convert_to_pixels(
                "exclude_center_pixels", float(self.vars["exclude_center_pixels"].get())
            ),
            "spike_gate_detect_thresh": float(self.vars["spike_gate_detect_thresh"].get()),
            "spike_excess_fraction": float(self.vars["spike_excess_fraction"].get()),
            "spike_neighbour_inner_arcsec": float(self.vars["spike_neighbour_inner_arcsec"].get()),
            "spike_neighbour_outer_arcsec": float(self.vars["spike_neighbour_outer_arcsec"].get()),
            "spike_side_offset_samples": int(self.vars["spike_side_offset_samples"].get()),
            "spike_side_drop_fraction": float(self.vars["spike_side_drop_fraction"].get()),
            "spike_window_samples": int(self.vars["spike_window_samples"].get()),
        }

    def reset_parameters(self) -> None:
        defaults = {
            "detect_thresh": DEFAULT_DETECT_THRESH,
            "minarea": DEFAULT_MINAREA,
            "deblend_nthresh": DEFAULT_DEBLEND_NTHRESH,
            "deblend_cont": DEFAULT_DEBLEND_CONT,
            "back_size": DEFAULT_BACK_SIZE,
            "filter_size": DEFAULT_FILTER_SIZE,
            "dilation_radius": DEFAULT_DILATION_RADIUS,
            "max_area": DEFAULT_MAX_AREA,
            "max_elongation": DEFAULT_MAX_ELONGATION,
            "exclude_center_pixels": DEFAULT_EXCLUDE_CENTER_PIXELS,
            "spike_gate_detect_thresh": SPIKE_GATE_DETECT_THRESH,
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
            self.format_spinbox_value(key)
        self.detect_on_var.set("original")
        self.spike_gate_detect_on_var.set("residual")
        self.mark_needs_calculation()

    def refresh_pc_paths(self, initial: bool = False) -> None:
        pc_name = self.pc_var.get()
        self.output_dir = remove_foreground_folder(pc_name) / "interactive_sep_spike_gate_parameter_tester"
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
            self.status.set(f"{self.pc_var.get()} | {name}: click Calculate to run SEP.")

    def output_png_path(self, params: dict[str, float | int | str]) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = (
            f"{display.safe_filename(self.galaxy_var.get())}_sep_"
            f"thr{float(params['detect_thresh']):.1f}_"
            f"area{int(params['minarea'])}_"
            f"deb{float(params['deblend_cont']):.4f}_"
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
            self.status.set(f"Calculating {name} with SEP...")
            self._show_calculating_overlay()
            self.update_idletasks()
            data, _header, geometry = self._load_galaxy(name)
            params = self.current_params()
            products = sep_products(data, params, geometry)
            spike_products = spike_gated_sep_products(data, params, geometry)
            self.draw_products(name, data, products, spike_products, params, geometry)
            png_path = self.output_png_path(params)
            self.figure.savefig(png_path, dpi=180)
            kept = sum(1 for row in products["rows"] if row.get("kept"))
            spike_kept = sum(1 for row in spike_products["rows"] if row.get("kept"))
            spike_count = int(np.count_nonzero(spike_products["spike_samples"]))
            masked_fraction = np.count_nonzero(products["mask"]) / products["mask"].size
            spike_masked_fraction = np.count_nonzero(spike_products["mask"]) / spike_products["mask"].size
            self.status.set(
                f"{self.pc_var.get()} | {name} | SEP kept {kept} segments, "
                f"masked {masked_fraction:.2%} of pixels. "
                f"Spike gate kept {spike_kept} low-threshold segments from {spike_count} spike samples, "
                f"masked {spike_masked_fraction:.2%}.\n"
                f"Output: {self.output_dir}\nSaved PNG: {png_path.name}"
            )
        except Exception as exc:  # noqa: BLE001
            self._remove_calculating_overlay()
            self.status.set(f"Error: {exc}")
            messagebox.showerror("SEP calculation failed", str(exc))

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
            ax.set_xlabel("bar-aligned arcsec", fontsize=8, labelpad=1)
            ax.set_ylabel("deprojected arcsec", fontsize=8, labelpad=1)
            ax.tick_params(labelsize=8, pad=1)

        vmin, vmax = display.robust_limits(original_view)
        self.ax_original.imshow(original_view, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax, extent=extent)
        self.draw_bar_guides(self.ax_original, half_width, bar_sma)
        self.draw_central_exclusion(self.ax_original, central_exclusion_arcsec)
        self.ax_original.set_title(f"{name} centered original", fontsize=10, pad=2)

        rvmin, rvmax = display.robust_limits(residual_view, 1.0, 99.0)
        limit = max(abs(rvmin), abs(rvmax))
        self.ax_residual.imshow(residual_view, origin="lower", cmap="coolwarm", vmin=-limit, vmax=limit, extent=extent)
        self.draw_bar_guides(self.ax_residual, half_width, bar_sma)
        self.draw_central_exclusion(self.ax_residual, central_exclusion_arcsec)
        self.ax_residual.set_title("Residual detection image", fontsize=10, pad=2)

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
            "SEP processed isophotes",
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
            "SEP processed bar-major profile",
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
            f"SEP & Spike Gate bar profile | thresh={float(params['spike_gate_detect_thresh']):.1f}",
            mask_profile=spike_mask_profile,
            spike_samples=spike_samples,
            y_limits=profile_y_limits,
        )
        self.match_profile_axes_to_image_column()
        self.canvas.draw_idle()

    def match_profile_axes_to_image_column(self) -> None:
        image_axes = [
            self.ax_original,
            self.ax_residual,
            self.ax_original_isophote,
            self.ax_cleaned_isophote,
        ]
        for ax in image_axes:
            ax.set_box_aspect(1.0)
        self.canvas.draw()

    def draw_parameter_box(self, params, products) -> None:
        kept = sum(1 for row in products["rows"] if row.get("kept"))
        raw = len(products["rows"])
        masked_fraction = np.count_nonzero(products["mask"]) / products["mask"].size
        text = (
            f"units={self.unit_var.get()}   "
            f"SEP detects on={params['detect_on']}   "
            f"Spike Gate detects on={params['spike_gate_detect_on']}   "
            f"detect_thresh={float(params['detect_thresh']):.2f}\n"
            f"minarea={int(params['minarea'])}   "
            f"deblend={int(params['deblend_nthresh'])}/{float(params['deblend_cont']):.4f}   "
            f"dilation_radius={int(params['dilation_radius'])}   "
            f"bkg={float(products['background_level']):.3g}, rms={float(products['background_rms']):.3g}   |   "
            f"segments={kept}/{raw}   masked={masked_fraction:.2%}"
        )
        label = self.ax_parameters.text(
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
        label.set_in_layout(False)

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
        ax.set_title(title, fontsize=10, pad=2)

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
        ax.set_xlabel("deprojected bar-major radius [arcsec]", fontsize=8, labelpad=1)
        ax.set_ylabel("intensity", fontsize=8, labelpad=1)
        ax.tick_params(labelsize=8, pad=1)
        ax.set_title(title, fontsize=10, pad=2)
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = SEPTester(args.manifest, args.pc)
    app.mainloop()


if __name__ == "__main__":
    main()
