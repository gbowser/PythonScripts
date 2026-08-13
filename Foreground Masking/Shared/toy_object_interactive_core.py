#!/usr/bin/env python3
"""Interactive toy-object placement tester for SEP and MTObjects."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from scipy import ndimage


SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
SUPPORT_DIRS = tuple(FOREGROUND_ROOT / name for name in ("Batch tools", "PhotUtils", "Interactive tools", "Shared", "Utilities"))
for path in (PROJECT_ROOT, FOREGROUND_ROOT, SCRIPT_DIR, *SUPPORT_DIRS):
    if str(path) not in sys.path:
        sys.path.append(str(path))

import foreground_display_helpers as display  # noqa: E402
import mtobjects_spike_gate_processing as mtobjects_tool  # noqa: E402
import sep_processing as sep_tool  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, detect_pc, remove_foreground_folder  # noqa: E402


DEFAULT_PC = detect_pc(FOREGROUND_ROOT)
DEFAULT_GALAXY = "ESO120-012"
TOY_TYPES = {
    "Gaussian star": "star",
    "Star cluster": "cluster",
    "Compact galaxy": "galaxy",
}

# Arithmetic means from the four Azure stability runs (seeds
# 202608041--202608044); integer-valued parameters were rounded to integers.
AZURE_MEAN_PARAMS = {
    "SEP": {
        "detect_on": "residual",
        "detect_thresh": 2.185542184039657,
        "minarea": 15,
        "deblend_nthresh": 23,
        "deblend_cont": 0.0005499685701731268,
        "back_size": 24,
        "filter_size": 3,
        "dilation_radius": 5,
        "max_area": 4590,
        "max_elongation": 9.731347513447435,
        "exclude_center_pixels": 8.0,
    },
    "MTObjects": {
        "detect_on": "original",
        "alpha": 1.0e-6,
        "move_factor": 0.7034586786406456,
        "min_distance": 0.4483894774965874,
        "gaussian_fwhm": 2.666209712021782,
        "soft_bias": 0.0,
        "gain": -1.0,
        "bg_mean": math.nan,
        "bg_variance": 7653.334425,
        "minarea": 59,
        "dilation_radius": 4,
        "max_area": 455,
        "max_elongation": 14.02348530181493,
        "exclude_center_pixels": 8.0,
    },
}

SEP_DOCUMENTED_DEFAULTS: dict[str, float | int | str] = {
    "detect_on": "original",
    "detect_thresh": 3.0,
    "minarea": 5,
    "deblend_nthresh": 32,
    "deblend_cont": 0.005,
    "back_size": 64,
    "filter_size": 3,
    "dilation_radius": 2,
    "max_area": 230,
    "max_elongation": 6.0,
    "exclude_center_pixels": 8.0,
}


def latest_best_json(pc_name: str, algorithm: str) -> Path | None:
    root = remove_foreground_folder(pc_name)
    folders = {
        "SEP": ["sep toy optimisation", "sep spike optimisation"],
        "MTObjects": ["mtobjects toy optimisation", "mtobjects spike optimisation"],
    }
    patterns = {
        "SEP": ["sep_toy_object_optimisation_best.json", "sep_spike_optimisation_best.json"],
        "MTObjects": ["mtobjects_parameter_optimisation_best.json", "mtobjects_spike_optimisation_best.json"],
    }
    candidates: list[Path] = []
    for folder in folders[algorithm]:
        for pattern in patterns[algorithm]:
            candidates.extend((root / folder).glob(f"*/{pattern}"))
    candidates = sorted([path for path in candidates if path.is_file()], key=lambda path: path.stat().st_mtime)
    return candidates[-1] if candidates else None


def load_json_params(path: Path | None) -> dict:
    if path is None:
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    params = payload.get("params", payload)
    return params if isinstance(params, dict) else {}


def sep_params(best_json: Path | None) -> dict[str, float | int | str]:
    params = dict(AZURE_MEAN_PARAMS["SEP"])
    for key, value in load_json_params(best_json).items():
        if key in params:
            params[key] = value
    return params


def mtobjects_params(best_json: Path | None) -> dict[str, float | int | str]:
    params = dict(AZURE_MEAN_PARAMS["MTObjects"])
    for key, value in load_json_params(best_json).items():
        if key in params:
            params[key] = value
    return params


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


def deprojected_to_observed_pixel(x_arcsec: float, y_arcsec: float, geometry: dict[str, float]) -> tuple[float, float]:
    transform_xy = display.image_transform(geometry["disk_pa"], geometry["inclination"], geometry["bar_pa"])
    observed_arcsec = np.linalg.inv(transform_xy) @ np.array([x_arcsec, y_arcsec])
    x_pix = geometry["xc"] - 1.0 + observed_arcsec[0] / geometry["pixel_scale"]
    y_pix = geometry["yc"] - 1.0 + observed_arcsec[1] / geometry["pixel_scale"]
    return float(x_pix), float(y_pix)


def gaussian_model(shape, x0, y0, peak, sigma_major, axis_ratio=1.0, pa_deg=0.0) -> np.ndarray:
    yy, xx = np.indices(shape, dtype=float)
    theta = math.radians(pa_deg)
    dx = xx - x0
    dy = yy - y0
    major = dx * math.cos(theta) + dy * math.sin(theta)
    minor = -dx * math.sin(theta) + dy * math.cos(theta)
    sigma_minor = max(0.2, sigma_major * axis_ratio)
    radius = np.hypot(major / sigma_major, minor / sigma_minor)
    return peak * np.exp(-0.5 * radius * radius)


def toy_model(shape, toy_type: str, x0, y0, peak, fwhm_pixels, axis_ratio, pa_deg) -> np.ndarray:
    sigma = max(0.2, fwhm_pixels / 2.3548)
    if toy_type == "cluster":
        model = np.zeros(shape, dtype=float)
        for dx, dy, scale in [(-0.55, -0.25, 0.75), (0.45, 0.18, 0.55), (0.05, 0.65, 0.38)]:
            model += gaussian_model(shape, x0 + dx * fwhm_pixels, y0 + dy * fwhm_pixels, peak * scale, sigma)
        return model
    if toy_type == "galaxy":
        return gaussian_model(shape, x0, y0, peak, sigma, axis_ratio, pa_deg)
    return gaussian_model(shape, x0, y0, peak, sigma)


def circular_footprint(radius: int) -> np.ndarray:
    yy, xx = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    return (xx * xx + yy * yy) <= radius * radius


class ToyObjectTester(tk.Tk):
    def __init__(self, algorithm: str, manifest: Path, pc_name: str, best_json: Path | None, mtobjects_root: Path | None):
        super().__init__()
        self.algorithm = algorithm
        self.title(f"{algorithm} Toy Object Interactive Tester")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(1700, max(1150, int(screen_width * 0.92)))
        height = min(1200, max(760, int(screen_height * 0.90)))
        x_position = max(0, (screen_width - width) // 2)
        y_position = max(0, (screen_height - height) // 2)
        self.geometry(f"{width}x{height}+{x_position}+{y_position}")
        self.minsize(1150, 760)
        self.manifest = manifest
        self.pc_var = tk.StringVar(value=pc_name)
        self.best_json = best_json
        self.mtobjects_root = mtobjects_root
        self.all_rows = display.read_manifest(manifest)
        self.rows: list[dict[str, str]] = []
        self.rows_by_name: dict[str, dict[str, str]] = {}
        self.data: np.ndarray | None = None
        self.geometry_data: dict[str, float] | None = None
        self.toys: list[dict[str, float | int | str]] = []
        self.toy_position_active = False
        self.output_dir = remove_foreground_folder(pc_name) / f"interactive_{algorithm.lower()}_toy_object_tester"

        self._build_controls()
        self._build_figure()
        self.refresh_pc_paths()
        # The first Matplotlib draw happens before Tk has assigned the packed
        # canvas its real dimensions.  Repeat the size/layout pass once the
        # window is mapped so the right-hand column is correct immediately.
        self.after_idle(self._finalize_initial_figure_layout)

    def _build_controls(self) -> None:
        control = ttk.Frame(self, padding=10, width=310)
        control.pack(side=tk.LEFT, fill=tk.Y)
        control.pack_propagate(False)

        ttk.Label(control, text=f"{self.algorithm} Toy Object", font=("", 11, "bold")).pack(anchor=tk.W)
        ttk.Label(control, text="Machine").pack(anchor=tk.W, pady=(10, 0))
        self.pc_combo = ttk.Combobox(control, textvariable=self.pc_var, values=sorted(PC_RESEARCH_FOLDERS), state="readonly")
        self.pc_combo.pack(fill=tk.X)
        self.pc_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_pc_paths())

        ttk.Label(control, text="Galaxy").pack(anchor=tk.W, pady=(8, 0))
        self.galaxy_var = tk.StringVar()
        self.galaxy_combo = ttk.Combobox(control, textvariable=self.galaxy_var, state="readonly")
        self.galaxy_combo.pack(fill=tk.X)
        self.galaxy_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_galaxy())

        self.status = tk.StringVar(value="Choose a galaxy, then click the image to place a toy object.")
        ttk.Label(control, textvariable=self.status, wraplength=285, foreground="#1f4d78").pack(fill=tk.X, pady=(10, 8))

        self.toy_type_var = tk.StringVar(value="Gaussian star")
        self.x_var = tk.DoubleVar(value=45.0)
        self.y_var = tk.DoubleVar(value=0.0)
        self.peak_var = tk.DoubleVar(value=30.0)
        self.fwhm_var = tk.DoubleVar(value=5.0)
        self.axis_ratio_var = tk.DoubleVar(value=0.65)
        self.pa_var = tk.DoubleVar(value=30.0)
        self.truth_dilation_var = tk.IntVar(value=1)

        toy_frame = ttk.LabelFrame(control, text="Toy object specification", padding=5)
        toy_frame.pack(fill=tk.X)
        ttk.Label(toy_frame, text="Toy type").grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=2, pady=(3, 0))
        ttk.Combobox(
            toy_frame,
            textvariable=self.toy_type_var,
            values=list(TOY_TYPES),
            state="readonly",
        ).grid(row=1, column=0, columnspan=2, sticky=tk.EW, padx=2)

        coordinate_controls = [
            ("x deprojected arcsec", self.x_var),
            ("y deprojected arcsec", self.y_var),
        ]
        for column, (label, variable) in enumerate(coordinate_controls):
            ttk.Label(toy_frame, text=label).grid(row=2, column=column, sticky=tk.W, padx=2, pady=(3, 0))
            spinbox = ttk.Spinbox(toy_frame, textvariable=variable, from_=-250, to=250, increment=1, width=12)
            spinbox.grid(row=3, column=column, sticky=tk.EW, padx=2)
            spinbox.configure(command=self.position_changed)
            spinbox.bind("<Return>", self.position_changed)
            spinbox.bind("<FocusOut>", self.position_changed)

        toy_controls = [
            ("peak residual sigma", self.peak_var, 0.5, 60, 0.5),
            ("FWHM pixels", self.fwhm_var, 1, 40, 0.5),
            ("axis ratio", self.axis_ratio_var, 0.1, 1.0, 0.05),
            ("object PA deg", self.pa_var, -180, 180, 5),
            ("truth dilation pixels", self.truth_dilation_var, 0, 10, 1),
        ]
        for index, (label, variable, low, high, increment) in enumerate(toy_controls):
            column = index % 2
            label_row = 4 + 2 * (index // 2)
            ttk.Label(toy_frame, text=label).grid(row=label_row, column=column, sticky=tk.W, padx=2, pady=(3, 0))
            spinbox = ttk.Spinbox(toy_frame, textvariable=variable, from_=low, to=high, increment=increment, width=12)
            spinbox.grid(row=label_row + 1, column=column, sticky=tk.EW, padx=2)

        toy_button_row = ttk.Frame(toy_frame)
        toy_button_row.grid(row=10, column=0, columnspan=2, sticky=tk.EW, pady=(6, 0))
        ttk.Button(toy_button_row, text="Add toy", command=self.add_toy).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(toy_button_row, text="Remove last", command=self.remove_last_toy).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        ttk.Button(toy_button_row, text="Clear", command=self.clear_toys).pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.toy_count_var = tk.StringVar(value="No toys placed; click the image or use Add toy.")
        ttk.Label(toy_frame, textvariable=self.toy_count_var, wraplength=270).grid(
            row=11,
            column=0,
            columnspan=2,
            sticky=tk.W,
            padx=2,
            pady=(4, 0),
        )
        toy_frame.columnconfigure(0, weight=1)
        toy_frame.columnconfigure(1, weight=1)

        self.mtobjects_vars: dict[str, tk.Variable] = {}
        self.sep_vars: dict[str, tk.Variable] = {}
        if self.algorithm == "MTObjects":
            self._build_mtobjects_controls(control)
        else:
            self._build_sep_controls(control)

        ttk.Button(control, text="Calculate", command=self.calculate).pack(fill=tk.X, pady=(14, 4))
        ttk.Button(control, text="Save PNG", command=self.save_png).pack(fill=tk.X, pady=(0, 4))
        ttk.Button(control, text="Open Output Folder", command=self.open_output_folder).pack(fill=tk.X)

        if self.algorithm == "MTObjects":
            source = "shared MTObjects defaults; background variance calibrated per galaxy"
        else:
            source = "documented SEP interactive defaults"
        ttk.Label(control, text=f"Parameters: {source}", wraplength=285).pack(fill=tk.X, pady=(12, 0))

    def _build_sep_controls(self, parent) -> None:
        """Add SEP controls with the defaults stated in the SEP documentation."""
        frame = ttk.LabelFrame(parent, text="SEP parameters", padding=5)
        frame.pack(fill=tk.X, pady=(10, 0))

        detect_on = tk.StringVar(value=str(SEP_DOCUMENTED_DEFAULTS["detect_on"]))
        self.sep_vars["detect_on"] = detect_on
        ttk.Label(frame, text="detect_on").grid(row=0, column=0, sticky=tk.W, padx=2)
        ttk.Combobox(
            frame,
            textvariable=detect_on,
            values=["original", "residual"],
            state="readonly",
            width=12,
        ).grid(row=1, column=0, sticky=tk.EW, padx=2)

        specifications = [
            ("detect_thresh", 0.1, 20.0, 0.1, False, "↓"),
            ("minarea", 1, 500, 1, True, "↓"),
            ("deblend_nthresh", 1, 128, 1, True, "variable"),
            ("deblend_cont", 0.0001, 1.0, 0.001, False, "↓ split"),
            ("back_size", 8, 512, 8, True, "variable"),
            ("filter_size", 1, 15, 1, True, "variable"),
            ("dilation_radius", 0, 50, 1, True, "↑"),
            ("max_area", 10, 100000, 10, True, "↑"),
            ("max_elongation", 1.0, 100.0, 0.25, False, "↑"),
            ("exclude_center_pixels", 0.0, 500.0, 1.0, False, "↓"),
        ]
        for index, (key, low, high, increment, integer, direction) in enumerate(specifications, start=1):
            column = index % 2
            label_row = 2 * ((index + 1) // 2)
            default = SEP_DOCUMENTED_DEFAULTS[key]
            value = str(int(default)) if integer else f"{float(default):.4g}"
            variable = tk.StringVar(value=value)
            self.sep_vars[key] = variable
            ttk.Label(frame, text=f"{key} {direction}").grid(
                row=label_row,
                column=column,
                sticky=tk.W,
                padx=2,
                pady=(3, 0),
            )
            spinbox = ttk.Spinbox(
                frame,
                textvariable=variable,
                from_=low,
                to=high,
                increment=increment,
                width=12,
                command=lambda v=variable, i=integer: self._format_mtobjects_value(v, i),
            )
            spinbox.grid(row=label_row + 1, column=column, sticky=tk.EW, padx=2)
            spinbox.bind("<Return>", lambda _event, v=variable, i=integer: self._format_mtobjects_value(v, i))
            spinbox.bind("<FocusOut>", lambda _event, v=variable, i=integer: self._format_mtobjects_value(v, i))

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        ttk.Button(frame, text="Reset SEP parameters", command=self.reset_sep_parameters).grid(
            row=14,
            column=0,
            columnspan=2,
            sticky=tk.EW,
            padx=2,
            pady=(7, 0),
        )
        ttk.Label(
            frame,
            text="Arrow = parameter direction for more masking; variable = image-dependent.",
            wraplength=270,
            foreground="#555555",
        ).grid(row=15, column=0, columnspan=2, sticky=tk.W, padx=2, pady=(6, 0))

    def reset_sep_parameters(self) -> None:
        integer_keys = {"minarea", "deblend_nthresh", "back_size", "filter_size", "dilation_radius", "max_area"}
        for key, value in SEP_DOCUMENTED_DEFAULTS.items():
            if key == "detect_on":
                self.sep_vars[key].set(str(value))
            elif key in integer_keys:
                self.sep_vars[key].set(str(int(value)))
            else:
                self.sep_vars[key].set(f"{float(value):.4g}")
        self.status.set("SEP parameters reset to their documented initial values.")

    def current_sep_params(self) -> dict[str, float | int | str]:
        params = dict(SEP_DOCUMENTED_DEFAULTS)
        integer_keys = {"minarea", "deblend_nthresh", "back_size", "filter_size", "dilation_radius", "max_area"}
        for key, variable in self.sep_vars.items():
            if key == "detect_on":
                params[key] = str(variable.get())
            elif key in integer_keys:
                params[key] = int(round(float(variable.get())))
            else:
                params[key] = float(variable.get())
        return params

    def _build_mtobjects_controls(self, parent) -> None:
        """Add compact controls using the shared MTObjects interactive defaults."""
        frame = ttk.LabelFrame(parent, text="MTObjects parameters", padding=5)
        frame.pack(fill=tk.X, pady=(10, 0))

        detect_on = tk.StringVar(value="original")
        self.mtobjects_vars["detect_on"] = detect_on
        ttk.Label(frame, text="detect_on").grid(row=0, column=0, sticky=tk.W, padx=2)
        ttk.Combobox(
            frame,
            textvariable=detect_on,
            values=["original", "residual"],
            state="readonly",
            width=12,
        ).grid(row=1, column=0, sticky=tk.EW, padx=2)

        specifications = [
            ("alpha", mtobjects_tool.DEFAULT_ALPHA, 1.0e-8, 1.0e-3, 1.0e-6, False),
            ("move_factor", mtobjects_tool.DEFAULT_MOVE_FACTOR, 0.0, 1.0, 0.05, False),
            ("min_distance", mtobjects_tool.DEFAULT_MIN_DISTANCE, 0.0, 100.0, 0.5, False),
            ("gaussian_fwhm", mtobjects_tool.DEFAULT_GAUSSIAN_FWHM, 0.0, 8.0, 0.25, False),
            ("soft_bias", mtobjects_tool.DEFAULT_SOFT_BIAS, -1000.0, 1000.0, 1.0, False),
            ("gain", mtobjects_tool.DEFAULT_GAIN, -1.0, 50.0, 0.5, False),
            ("bg_mean", mtobjects_tool.DEFAULT_BG_MEAN, -1.0e6, 1.0e6, 1.0, False),
            ("bg_variance", mtobjects_tool.DEFAULT_BG_VARIANCE, 0.0, 1.0e6, 100.0, False),
            ("minarea", mtobjects_tool.DEFAULT_MINAREA, 1, 500, 1, True),
            ("dilation_radius", mtobjects_tool.DEFAULT_DILATION_RADIUS, 0, 50, 1, True),
            ("max_area", mtobjects_tool.DEFAULT_MAX_AREA, 10, 100000, 10, True),
            ("max_elongation", mtobjects_tool.DEFAULT_MAX_ELONGATION, 1.0, 100.0, 0.25, False),
            ("exclude_center_pixels", mtobjects_tool.DEFAULT_EXCLUDE_CENTER_PIXELS, 0.0, 500.0, 1.0, False),
        ]
        masking_direction = {
            "alpha": "(fixed)",
            "move_factor": "↓",
            "min_distance": "↓",
            "gaussian_fwhm": "(variable)",
            "soft_bias": "(variable)",
            "gain": "(variable)",
            "bg_mean": "(variable)",
            "bg_variance": "↓",
            "minarea": "↓",
            "dilation_radius": "↑",
            "max_area": "↑",
            "max_elongation": "↑",
            "exclude_center_pixels": "↓",
        }
        for index, (key, default, low, high, increment, integer) in enumerate(specifications, start=1):
            column = index % 2
            label_row = 2 * ((index + 1) // 2)
            display_value = str(int(default)) if integer else f"{float(default):.4g}"
            variable = tk.StringVar(value=display_value)
            self.mtobjects_vars[key] = variable
            ttk.Label(frame, text=f"{key} {masking_direction[key]}").grid(
                row=label_row,
                column=column,
                sticky=tk.W,
                padx=2,
                pady=(3, 0),
            )
            spinbox = ttk.Spinbox(
                frame,
                textvariable=variable,
                from_=low,
                to=high,
                increment=increment,
                width=12,
                command=lambda v=variable, i=integer: self._format_mtobjects_value(v, i),
            )
            spinbox.grid(row=label_row + 1, column=column, sticky=tk.EW, padx=2)
            spinbox.bind("<Return>", lambda _event, v=variable, i=integer: self._format_mtobjects_value(v, i))
            spinbox.bind("<FocusOut>", lambda _event, v=variable, i=integer: self._format_mtobjects_value(v, i))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        ttk.Button(frame, text="Reset MTObjects parameters", command=self.reset_mtobjects_parameters).grid(
            row=16,
            column=0,
            columnspan=2,
            sticky=tk.EW,
            padx=2,
            pady=(7, 0),
        )
        ttk.Label(
            frame,
            text="Arrow = parameter direction for more masking; variable = image-dependent.",
            wraplength=270,
            foreground="#555555",
        ).grid(row=18, column=0, columnspan=2, sticky=tk.W, padx=2, pady=(6, 0))

    def reset_mtobjects_parameters(self) -> None:
        defaults: dict[str, float | int | str] = {
            "detect_on": "original",
            "alpha": mtobjects_tool.DEFAULT_ALPHA,
            "move_factor": mtobjects_tool.DEFAULT_MOVE_FACTOR,
            "min_distance": mtobjects_tool.DEFAULT_MIN_DISTANCE,
            "gaussian_fwhm": mtobjects_tool.DEFAULT_GAUSSIAN_FWHM,
            "soft_bias": mtobjects_tool.DEFAULT_SOFT_BIAS,
            "gain": mtobjects_tool.DEFAULT_GAIN,
            "bg_mean": mtobjects_tool.DEFAULT_BG_MEAN,
            "bg_variance": mtobjects_tool.DEFAULT_BG_VARIANCE,
            "minarea": mtobjects_tool.DEFAULT_MINAREA,
            "dilation_radius": mtobjects_tool.DEFAULT_DILATION_RADIUS,
            "max_area": mtobjects_tool.DEFAULT_MAX_AREA,
            "max_elongation": mtobjects_tool.DEFAULT_MAX_ELONGATION,
            "exclude_center_pixels": mtobjects_tool.DEFAULT_EXCLUDE_CENTER_PIXELS,
        }
        if self.data is not None:
            residual = self.data - mtobjects_tool.smooth_model(self.data, sigma_pixels=15.0)
            residual_sigma = robust_sigma(residual)
            defaults["bg_variance"] = residual_sigma * residual_sigma
        integer_keys = {"minarea", "dilation_radius", "max_area"}
        for key, value in defaults.items():
            if key == "detect_on":
                self.mtobjects_vars[key].set(str(value))
            elif key in integer_keys:
                self.mtobjects_vars[key].set(str(int(value)))
            else:
                self.mtobjects_vars[key].set(f"{float(value):.4g}")
        self.status.set("MTObjects parameters reset to their initial values.")

    @staticmethod
    def _format_mtobjects_value(variable: tk.Variable, integer: bool) -> None:
        try:
            value = float(variable.get())
        except (tk.TclError, ValueError):
            return
        variable.set(str(int(round(value))) if integer else f"{value:.4g}")

    def current_mtobjects_params(self) -> dict[str, float | int | str]:
        params = mtobjects_params(self.best_json)
        integer_keys = {"minarea", "dilation_radius", "max_area"}
        for key, variable in self.mtobjects_vars.items():
            if key == "detect_on":
                params[key] = str(variable.get())
            elif key in integer_keys:
                params[key] = int(round(float(variable.get())))
            else:
                params[key] = float(variable.get())
        return params

    def _build_figure(self) -> None:
        self.figure = Figure(figsize=(14.5, 8.6), dpi=100, constrained_layout=True)
        grid = self.figure.add_gridspec(2, 3, width_ratios=(1.0, 1.0, 1.0))
        self.axes = np.array(
            [
                [self.figure.add_subplot(grid[0, 0]), self.figure.add_subplot(grid[0, 1])],
                [self.figure.add_subplot(grid[1, 0]), self.figure.add_subplot(grid[1, 1])],
            ],
            dtype=object,
        )
        self.profile_axes = (
            self.figure.add_subplot(grid[0, 2]),
            self.figure.add_subplot(grid[1, 2]),
        )
        for panel_ax in (*self.axes.ravel(), *self.profile_axes):
            panel_ax.set_box_aspect(1)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self.canvas, self, pack_toolbar=False).pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.mpl_connect("button_press_event", self.on_click)

    def _finalize_initial_figure_layout(self) -> None:
        """Size Matplotlib from the mapped canvas instead of its 1-pixel startup size."""
        self.update_idletasks()
        canvas_widget = self.canvas.get_tk_widget()
        width = canvas_widget.winfo_width()
        height = canvas_widget.winfo_height()
        if width <= 1 or height <= 1:
            self.after(25, self._finalize_initial_figure_layout)
            return
        self.figure.set_size_inches(width / self.figure.dpi, height / self.figure.dpi, forward=False)
        self.canvas.draw()

    def refresh_pc_paths(self) -> None:
        pc_name = self.pc_var.get()
        self.output_dir = remove_foreground_folder(pc_name) / f"interactive_{self.algorithm.lower()}_toy_object_tester"
        self.rows = display.rows_with_images_for_pc(self.all_rows, pc_name)
        self.rows_by_name = {row["name"]: row for row in self.rows}
        names = [row["name"] for row in self.rows]
        self.galaxy_combo.configure(values=names)
        default = DEFAULT_GALAXY if DEFAULT_GALAXY in self.rows_by_name else (names[0] if names else "")
        self.galaxy_var.set(default)
        self.load_galaxy()

    def load_galaxy(self) -> None:
        row = self.rows_by_name.get(self.galaxy_var.get())
        if row is None:
            return
        self.toys.clear()
        self.toy_position_active = False
        self._update_toy_count()
        self.geometry_data = display.required_geometry(row)
        if self.geometry_data is None:
            self.status.set("Selected galaxy has incomplete geometry.")
            return
        self.data, _header = sep_tool.load_fits(display.image_path_for_pc(row, self.pc_var.get()))
        if self.algorithm == "MTObjects":
            # The S4G images are in small floating-point surface-brightness
            # units.  A fixed variance imported from a differently scaled run
            # can suppress every MTObjects significance test.  Calibrate the
            # noise in the same residual domain used to specify toy peak sigma.
            residual = self.data - mtobjects_tool.smooth_model(self.data, sigma_pixels=15.0)
            residual_sigma = robust_sigma(residual)
            self.mtobjects_vars["bg_variance"].set(f"{residual_sigma * residual_sigma:.4g}")
        self.draw_preview()

    def draw_preview(self) -> None:
        if self.data is None or self.geometry_data is None:
            return
        radius_arcsec = display.profile_radius_pixels(self.data, self.geometry_data) * self.geometry_data["pixel_scale"]
        view, x_axis, y_axis = display.deproject_bar_aligned_cutout(self.data, self.geometry_data, radius_arcsec)
        ax = self.axes[0, 0]
        for item in (*self.axes.ravel(), *self.profile_axes):
            item.clear()
            item.set_box_aspect(1)
        vmin, vmax = display.robust_limits(view)
        ax.imshow(view, origin="lower", extent=[x_axis[0], x_axis[-1], y_axis[0], y_axis[-1]], cmap="gist_gray_r", vmin=vmin, vmax=vmax)
        for index, toy in enumerate(self.toys, start=1):
            x_value = float(toy["x_arcsec"])
            y_value = float(toy["y_arcsec"])
            ax.plot(x_value, y_value, "bo", ms=6, mfc="none", mew=1.5)
            ax.text(x_value, y_value, str(index), color="blue", fontsize=8, ha="left", va="bottom")
        if self.toy_position_active:
            ax.plot(float(self.x_var.get()), float(self.y_var.get()), "rx", ms=9, mew=2)
        ax.set_title("Toy position (click to move)")
        self._draw_major_axis_profiles(view, x_axis, y_axis)
        self.canvas.draw_idle()

    def _draw_profile_curve(
        self,
        ax,
        radii: np.ndarray,
        intensity: np.ndarray,
        *,
        title: str,
        masked_samples: np.ndarray | None = None,
        y_limits: tuple[float, float] | None = None,
    ) -> None:
        displayed = np.array(intensity, copy=True)
        bridged = None
        bridged_samples = np.zeros(intensity.size, dtype=bool)
        if masked_samples is not None:
            bridged, bridged_samples = sep_tool.fill_profile_with_log_linear_bridges(intensity, masked_samples)
            displayed[bridged_samples] = np.nan

        ax.semilogy(radii, displayed, color="#1f77b4", linewidth=1.25)
        if bridged is not None:
            for start, stop in sep_tool.contiguous_true_runs(bridged_samples):
                plot_slice = slice(max(0, start - 1), min(bridged.size, stop + 2))
                good = np.isfinite(radii[plot_slice]) & np.isfinite(bridged[plot_slice]) & (bridged[plot_slice] > 0)
                if np.count_nonzero(good) >= 2:
                    ax.semilogy(
                        radii[plot_slice][good],
                        bridged[plot_slice][good],
                        color="#1f77b4",
                        linestyle="--",
                        linewidth=1.25,
                    )
        if y_limits is not None:
            ax.set_ylim(*y_limits)
        ax.set_title(title)
        ax.set_xlabel("bar major axis [arcsec]")
        ax.set_ylabel("mean intensity")
        ax.grid(True, which="both", color="0.88", linewidth=0.5)

    def _draw_major_axis_profiles(
        self,
        before_view: np.ndarray,
        x_axis: np.ndarray,
        y_axis: np.ndarray,
        mask_view: np.ndarray | None = None,
    ) -> None:
        half_width = 0.5 * sep_tool.DEFAULT_PROFILE_WIDTH_PIXELS * self.geometry_data["pixel_scale"]
        radii, intensity = display.bar_major_axis_profile(before_view, x_axis, y_axis, half_width)
        masked_samples = None
        bridged = None
        if mask_view is not None:
            _mask_radii, mask_fraction = display.bar_major_axis_profile(mask_view, x_axis, y_axis, half_width)
            masked_samples = np.isfinite(mask_fraction) & (mask_fraction > 0)
            bridged, _replaced = sep_tool.fill_profile_with_log_linear_bridges(intensity, masked_samples)

        positive_parts = [intensity[np.isfinite(intensity) & (intensity > 0)]]
        if bridged is not None:
            positive_parts.append(bridged[np.isfinite(bridged) & (bridged > 0)])
        positive = np.concatenate([part for part in positive_parts if part.size]) if any(part.size for part in positive_parts) else np.array([])
        y_limits = None
        if positive.size:
            low = max(float(np.nanpercentile(positive, 2)) * 0.8, np.finfo(float).tiny)
            high = float(np.nanmax(positive)) * 1.25
            if math.isfinite(low) and math.isfinite(high) and high > low:
                y_limits = (low, high)

        for profile_ax in self.profile_axes:
            profile_ax.clear()
        self._draw_profile_curve(self.profile_axes[0], radii, intensity, title="Before", y_limits=y_limits)
        if masked_samples is None:
            self.profile_axes[1].set_title("Post masking")
            self.profile_axes[1].set_xlabel("bar major axis [arcsec]")
            self.profile_axes[1].set_ylabel("mean intensity")
            self.profile_axes[1].text(0.5, 0.5, "Press Calculate", ha="center", va="center", transform=self.profile_axes[1].transAxes, color="0.45")
            self.profile_axes[1].grid(True, which="both", color="0.88", linewidth=0.5)
        else:
            self._draw_profile_curve(
                self.profile_axes[1],
                radii,
                intensity,
                title="Post masking",
                masked_samples=masked_samples,
                y_limits=y_limits,
            )

    def current_toy_specification(self) -> dict[str, float | int | str]:
        return {
            "toy_type": TOY_TYPES[self.toy_type_var.get()],
            "x_arcsec": float(self.x_var.get()),
            "y_arcsec": float(self.y_var.get()),
            "peak_sigma": float(self.peak_var.get()),
            "fwhm_pixels": float(self.fwhm_var.get()),
            "axis_ratio": float(self.axis_ratio_var.get()),
            "pa_deg": float(self.pa_var.get()),
            "truth_dilation": int(self.truth_dilation_var.get()),
        }

    def _update_toy_count(self) -> None:
        count = len(self.toys)
        if self.toy_position_active:
            prefix = f"{count} committed; " if count else ""
            self.toy_count_var.set(f"{prefix}one pending toy at the red cross.")
        elif count:
            self.toy_count_var.set(f"{count} toy{'s' if count != 1 else ''} added; Calculate uses the added toys.")
        else:
            self.toy_count_var.set("No toys placed; click the image or use Add toy.")

    def add_toy(self) -> None:
        try:
            self.toys.append(self.current_toy_specification())
        except (KeyError, tk.TclError, ValueError) as exc:
            messagebox.showerror("Invalid toy specification", str(exc))
            return
        self.toy_position_active = False
        self._update_toy_count()
        self.draw_preview()

    def remove_last_toy(self) -> None:
        if self.toys:
            self.toys.pop()
        self._update_toy_count()
        self.draw_preview()

    def clear_toys(self) -> None:
        self.toys.clear()
        self.toy_position_active = False
        self._update_toy_count()
        self.draw_preview()

    def position_changed(self, _event=None) -> None:
        """Redraw the placement marker after either coordinate control changes."""
        try:
            float(self.x_var.get())
            float(self.y_var.get())
        except (tk.TclError, ValueError):
            return
        self.draw_preview()

    def calculate(self) -> None:
        if self.data is None or self.geometry_data is None:
            return
        try:
            result = self.make_result()
            self.draw_result(result)
            if result["toy_count"]:
                prefix = (
                    f"{self.algorithm} processed {result['toy_count']} toy{'s' if result['toy_count'] != 1 else ''}; "
                    f"recovered {result['overlap_pixels']}/{result['truth_pixels']} truth pixels "
                    f"({result['recall']:.1%}); "
                )
            else:
                prefix = f"{self.algorithm} baseline on the unaltered image; "
            self.status.set(
                prefix
                + f"kept {result['kept_segments']}/{result['raw_segments']} segments; "
                f"masked {result['masked_fraction']:.2%}; background RMS={result['background_rms']:.4g}."
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Toy object calculation failed", str(exc))

    def make_result(self) -> dict:
        assert self.data is not None and self.geometry_data is not None
        sigma = robust_sigma(self.data)
        specifications = list(self.toys)
        if self.toy_position_active:
            specifications.append(self.current_toy_specification())
        model = np.zeros(self.data.shape, dtype=float)
        truth = np.zeros(self.data.shape, dtype=bool)
        for specification in specifications:
            x_pix, y_pix = deprojected_to_observed_pixel(
                float(specification["x_arcsec"]),
                float(specification["y_arcsec"]),
                self.geometry_data,
            )
            toy = toy_model(
                self.data.shape,
                str(specification["toy_type"]),
                x_pix,
                y_pix,
                float(specification["peak_sigma"]) * sigma,
                float(specification["fwhm_pixels"]),
                float(specification["axis_ratio"]),
                float(specification["pa_deg"]),
            )
            toy_truth = toy > max(np.nanmax(toy) * 0.08, 0)
            dilation = int(specification["truth_dilation"])
            if dilation > 0:
                toy_truth = ndimage.binary_dilation(toy_truth, structure=circular_footprint(dilation))
            model += toy
            truth |= toy_truth
        injected = np.array(self.data, copy=True)
        injected[np.isfinite(injected)] += model[np.isfinite(injected)]

        if self.algorithm == "SEP":
            products = sep_tool.sep_products(injected, self.current_sep_params(), self.geometry_data)
        else:
            root = mtobjects_tool.find_mtobjects_root(self.mtobjects_root)
            products = mtobjects_tool.mtobjects_products(injected, self.current_mtobjects_params(), self.geometry_data, root)

        mask = np.asarray(products["mask"], dtype=bool)
        overlap = int(np.count_nonzero(mask & truth))
        truth_pixels = int(np.count_nonzero(truth))
        rows = list(products.get("rows", []))
        return {
            "injected": injected,
            "model": model,
            "truth": truth,
            "mask": mask,
            "cleaned": np.asarray(products["cleaned"], dtype=float),
            "toy_count": len(specifications),
            "raw_segments": len(rows),
            "kept_segments": sum(bool(row.get("kept")) for row in rows),
            "background_rms": float(products.get("background_rms", math.nan)),
            "overlap_pixels": overlap,
            "truth_pixels": truth_pixels,
            "recall": overlap / truth_pixels if truth_pixels else 0.0,
            "masked_fraction": float(np.count_nonzero(mask) / mask.size),
        }

    def draw_result(self, result: dict) -> None:
        assert self.data is not None and self.geometry_data is not None
        radius_arcsec = display.profile_radius_pixels(self.data, self.geometry_data) * self.geometry_data["pixel_scale"]
        panels = [
            ("Toy position (click to move)", self.data, "gist_gray_r", None, 1),
            ("Injected toy", result["injected"], "gist_gray_r", None, 1),
            (f"{self.algorithm} mask", result["mask"].astype(float), "gray_r", (0, 1), 0),
            ("Recovered image", result["cleaned"], "gist_gray_r", None, 1),
        ]
        panel_views = []
        for ax, (title, image, cmap, fixed_limits, interpolation_order) in zip(self.axes.ravel(), panels):
            ax.clear()
            view, x_axis, y_axis = display.deproject_bar_aligned_cutout(
                image,
                self.geometry_data,
                radius_arcsec,
                order=interpolation_order,
            )
            panel_views.append((view, x_axis, y_axis))
            vmin, vmax = fixed_limits if fixed_limits is not None else display.robust_limits(view)
            ax.imshow(view, origin="lower", extent=[x_axis[0], x_axis[-1], y_axis[0], y_axis[-1]], cmap=cmap, vmin=vmin, vmax=vmax)
            ax.set_title(title)

        # The placement cross belongs only on the original image.  The other
        # panels show the actual injected signal and MTObjects products.
        for index, toy in enumerate(self.toys, start=1):
            x_value = float(toy["x_arcsec"])
            y_value = float(toy["y_arcsec"])
            self.axes[0, 0].plot(x_value, y_value, "bo", ms=6, mfc="none", mew=1.5)
            self.axes[0, 0].text(x_value, y_value, str(index), color="blue", fontsize=8, ha="left", va="bottom")
        if self.toy_position_active:
            self.axes[0, 0].plot(float(self.x_var.get()), float(self.y_var.get()), "rx", ms=9, mew=2)

        # Classify complete connected mask regions.  For a toy detection, show
        # the correctly covered truth footprint in green.  If that connected
        # component extends beyond the truth, contour the *solid full component*
        # in red; this gives one outer over-masking boundary without the false
        # inner red boundary produced by contouring an annulus.
        labelled_mask, component_count = ndimage.label(np.asarray(result["mask"], dtype=bool))
        correct_removal = np.zeros_like(labelled_mask, dtype=bool)
        incorrect_removal = np.zeros_like(labelled_mask, dtype=bool)
        truth = np.asarray(result["truth"], dtype=bool)
        for component_label in range(1, component_count + 1):
            component = labelled_mask == component_label
            if np.any(component & truth):
                correct_removal |= component & truth
                if np.any(component & ~truth):
                    incorrect_removal |= component
            else:
                incorrect_removal |= component
        recovered_ax = self.axes[1, 1]
        _recovered_view, recovered_x, recovered_y = panel_views[3]
        for region, colour in ((correct_removal, "lime"), (incorrect_removal, "red")):
            region_view, _x_axis, _y_axis = display.deproject_bar_aligned_cutout(
                region,
                self.geometry_data,
                radius_arcsec,
                order=0,
            )
            if np.any(region_view):
                recovered_ax.contour(
                    recovered_x,
                    recovered_y,
                    region_view.astype(float),
                    levels=[0.5],
                    colors=[colour],
                    linewidths=1.2,
                )
        recovered_ax.set_title("Recovered image (green=correct, red=incorrect)")
        self._draw_major_axis_profiles(panel_views[1][0], panel_views[1][1], panel_views[1][2], panel_views[2][0])
        self.canvas.draw_idle()

    def on_click(self, event) -> None:
        if event.inaxes is not self.axes[0, 0] or event.xdata is None or event.ydata is None:
            return
        self.x_var.set(round(float(event.xdata), 2))
        self.y_var.set(round(float(event.ydata), 2))
        self.toy_position_active = True
        self._update_toy_count()
        self.draw_preview()

    def save_png(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / (
            f"{display.safe_filename(self.galaxy_var.get())}_{self.algorithm.lower()}_toy_"
            f"x{float(self.x_var.get()):.1f}_y{float(self.y_var.get()):.1f}_{datetime.now():%Y%m%d_%H%M%S}.png"
        )
        self.figure.savefig(path, dpi=180)
        self.status.set(f"Saved PNG: {path}")

    def open_output_folder(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(self.output_dir)])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--algorithm", choices=["SEP", "MTObjects"], required=True)
    parser.add_argument("--manifest", type=Path, default=display.DEFAULT_MANIFEST)
    parser.add_argument("--pc", choices=sorted(PC_RESEARCH_FOLDERS), default=DEFAULT_PC)
    parser.add_argument("--best-json", type=Path, default=None)
    parser.add_argument("--mtobjects-root", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = ToyObjectTester(args.algorithm, args.manifest, args.pc, args.best_json, args.mtobjects_root)
    app.mainloop()


if __name__ == "__main__":
    main()
