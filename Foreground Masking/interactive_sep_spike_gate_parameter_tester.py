#!/usr/bin/env python3
"""Interactive SEP plus Spike-Gate foreground-mask parameter tester.

SEP is a Python library based on the core algorithms of SExtractor. This tester
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
DEFAULT_SPIKE_CENTER_EXCLUSION_ARCSEC = 8.0
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
    center_exclusion_arcsec: float = DEFAULT_SPIKE_CENTER_EXCLUSION_ARCSEC,
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
    gate_params["detect_thresh"] = SPIKE_GATE_DETECT_THRESH
    low_threshold_products = sep_products(data, gate_params, geometry)

    radius_arcsec = display.profile_radius_pixels(data, geometry) * geometry["pixel_scale"]
    original_view, x_axis, y_axis = display.deproject_bar_aligned_cutout(data, geometry, radius_arcsec)
    half_width = 0.5 * DEFAULT_PROFILE_WIDTH_PIXELS * geometry["pixel_scale"]
    radii, intensity = display.bar_major_axis_profile(original_view, x_axis, y_axis, half_width)
    spike_samples = detect_profile_spikes(radii, intensity)
    spike_samples = expand_boolean_mask(spike_samples, DEFAULT_SPIKE_WINDOW_SAMPLES)

    selected_labels: set[int] = set()
    filtered = np.asarray(low_threshold_products["filtered_segmentation"])
    if np.any(spike_samples) and np.any(filtered > 0):
        for label in np.unique(filtered):
            label = int(label)
            if label <= 0:
                continue
            label_mask = dilate_mask(filtered == label, int(params["dilation_radius"]))
            label_view, _, _ = display.deproject_bar_aligned_cutout(label_mask.astype(float), geometry, radius_arcsec, order=0)
            label_profile = profile_mask_at_bar_major(np.isfinite(label_view) & (label_view > 0.5), y_axis, half_width)
            if np.any(label_profile & spike_samples):
                selected_labels.add(label)

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
        "spike_gate_detect_thresh": SPIKE_GATE_DETECT_THRESH,
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
        self.geometry("1760x1320")
        self.minsize(1400, 950)
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

        self._build_controls()
        self._build_figure()
        self.refresh_pc_paths(initial=True)

    def _build_controls(self) -> None:
        control = ttk.Frame(self, padding=10)
        control.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(control, text="Machine").pack(anchor=tk.W)
        pc_combo = ttk.Combobox(control, textvariable=self.pc_var, values=sorted(PC_RESEARCH_FOLDERS), state="readonly")
        pc_combo.pack(fill=tk.X, pady=(0, 8))
        pc_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_pc_paths())

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
        self._scale(control, "detect_thresh", "Detection threshold", 0.5, 10.0, 0.1, DEFAULT_DETECT_THRESH)
        self._spin(control, "minarea", "Minimum area [px]", 1, 80, 1, DEFAULT_MINAREA)
        self._spin(control, "deblend_nthresh", "Deblend thresholds", 8, 64, 1, DEFAULT_DEBLEND_NTHRESH)
        self._scale(control, "deblend_cont", "Deblend contrast", 0.0001, 0.1, 0.0005, DEFAULT_DEBLEND_CONT)
        self._spin(control, "back_size", "Background box [px]", 16, 256, 8, DEFAULT_BACK_SIZE)
        self._spin(control, "filter_size", "Filter size [px]", 1, 9, 2, DEFAULT_FILTER_SIZE)
        self._spin(control, "dilation_radius", "Mask dilation [px]", 0, 12, 1, DEFAULT_DILATION_RADIUS)
        self._spin(control, "max_area", "Max segment area [px]", 10, 5000, 10, DEFAULT_MAX_AREA)
        self._scale(control, "max_elongation", "Max elongation", 1.0, 20.0, 0.25, DEFAULT_MAX_ELONGATION)
        self._scale(control, "exclude_center_pixels", "Central exclusion [px]", 0.0, 120.0, 1.0, DEFAULT_EXCLUDE_CENTER_PIXELS)

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
        label_widget = ttk.Label(frame, text=self.label_for_display(key, label))
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
        label_widget = ttk.Label(frame, text=self.label_for_display(key, label))
        label_widget.pack(side=tk.LEFT)
        self.parameter_labels[key] = label_widget
        self.parameter_label_texts[key] = label
        if key in PIXEL_LINEAR_PARAMS or key in PIXEL_AREA_PARAMS:
            var = tk.DoubleVar(value=float(self.convert_from_pixels(key, default)))
        else:
            var = tk.IntVar(value=default)
        self.vars[key] = var
        spin = ttk.Spinbox(
            frame,
            textvariable=var,
            from_=self.convert_from_pixels(key, minimum),
            to=self.convert_from_pixels(key, maximum),
            increment=self.convert_from_pixels(key, increment),
            width=10,
        )
        spin.pack(side=tk.RIGHT)
        spin.configure(command=self.mark_needs_calculation)
        spin.bind("<Return>", lambda _event: self.mark_needs_calculation())
        spin.bind("<FocusOut>", lambda _event: self.mark_needs_calculation())

    def _build_figure(self) -> None:
        frame = ttk.Frame(self)
        frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.figure = Figure(figsize=(12.0, 15.6), dpi=100, constrained_layout=True)
        grid = self.figure.add_gridspec(5, 2, height_ratios=[0.26, 1.0, 0.72, 0.72, 0.72])
        self.ax_parameters = self.figure.add_subplot(grid[0, :])
        self.ax_original = self.figure.add_subplot(grid[1, 0])
        self.ax_residual = self.figure.add_subplot(grid[1, 1])
        self.ax_original_isophote = self.figure.add_subplot(grid[2, 0])
        self.ax_original_profile = self.figure.add_subplot(grid[2, 1])
        self.ax_cleaned_isophote = self.figure.add_subplot(grid[3:, 0])
        self.ax_cleaned_profile = self.figure.add_subplot(grid[3, 1])
        self.ax_cleaned = self.figure.add_subplot(grid[4, 1])
        self.ax_parameters.set_axis_off()
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(self.canvas, frame)
        toolbar.update()

    def parameter_changed(self, key: str, mark: bool = True) -> None:
        if key in self.readouts:
            self.readouts[key].configure(text=f"{float(self.vars[key].get()):.4g}")
        if mark:
            self.mark_needs_calculation()

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
                self.readouts[key].configure(text=f"{float(var.get()):.4g}")
        self.display_units = new_units
        self.refresh_parameter_unit_labels()
        self.mark_needs_calculation()

    def current_params(self) -> dict[str, float | int | str]:
        return {
            "detect_on": self.detect_on_var.get(),
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
        }
        for key, value in defaults.items():
            self.vars[key].set(self.convert_from_pixels(key, value))
            self.parameter_changed(key, mark=False)
        self.detect_on_var.set("residual")
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
            f"SEP & Spike Gate bar profile | thresh={SPIKE_GATE_DETECT_THRESH:.1f}",
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
            "SEP / SExtractor-style   "
            f"units={self.unit_var.get()}   "
            f"detect_on={params['detect_on']}   "
            f"thresh={float(params['detect_thresh']):.1f}   "
            f"minarea={int(params['minarea'])}   "
            f"deblend={int(params['deblend_nthresh'])}/{float(params['deblend_cont']):.4f}   "
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = SEPTester(args.manifest, args.pc)
    app.mainloop()


if __name__ == "__main__":
    main()
