#!/usr/bin/env python3
"""Widescreen interactive toy-object comparison for SEP and MTObjects."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")
import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table
from astropy.wcs import WCS
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from scipy import ndimage

# The shared processing modules determine the machine at import time. WSL does
# not expose Windows drive roots as Path.exists(), so provide the normal desktop
# identity before importing those modules; --pc can still override the GUI data.
if os.name != "nt" and "FOREGROUND_MASKING_PC" not in os.environ:
    os.environ["FOREGROUND_MASKING_PC"] = "Desktop"

SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
for folder in (PROJECT_ROOT, FOREGROUND_ROOT, *(FOREGROUND_ROOT / name for name in ("Batch tools", "Shared", "Utilities", "PhotUtils"))):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import foreground_display_helpers as display  # noqa: E402
import mtobjects_spike_gate_processing as mto_processing  # noqa: E402
import sep_processing  # noqa: E402
import toy_object_interactive_core as core  # noqa: E402
import apply_optimised_mtobjects_all_galaxies as mto_batch  # noqa: E402
import batch_sep_all_galaxies as sep_batch  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, detect_pc, remove_foreground_folder  # noqa: E402


SEP_KEYS = (
    "detect_on", "detect_thresh", "minarea", "deblend_nthresh", "deblend_cont",
    "back_size", "filter_size", "dilation_radius", "max_area", "max_elongation",
    "exclude_center_pixels",
)
MTO_KEYS = (
    "detect_on", "alpha", "move_factor", "min_distance", "gaussian_fwhm",
    "soft_bias", "gain", "bg_mean", "bg_variance", "minarea", "dilation_radius",
    "max_area", "max_elongation", "exclude_center_pixels",
)
INTEGER_KEYS = {"minarea", "deblend_nthresh", "back_size", "filter_size", "dilation_radius", "max_area"}
REQUIRED_METRIC_VERSION = "paired-toy-metrics-displayed-frame-v2"
CURRENT_OPTIMISATION_DIR = "clean22_displayed_frame_5toy_optimisation"
SEP_WINNER_RELATIVE = Path("SEP_cross_validation/sep_toy_cross_validation_best.json")
MTO_WINNER_RELATIVE = Path("MTObjects_cross_validation/mtobjects_toy_cross_validation_best.json")
MASKING_DIRECTIONS = {
    "SEP parameters": {
        "detect_on": "↔", "detect_thresh": "↓", "minarea": "↓", "deblend_nthresh": "↔",
        "deblend_cont": "↓", "back_size": "↔", "filter_size": "↔", "dilation_radius": "↑",
        "max_area": "↑", "max_elongation": "↑", "exclude_center_pixels": "↓",
    },
    "MTObjects parameters": {
        "detect_on": "↔", "alpha": "↔", "move_factor": "↓", "min_distance": "↓",
        "gaussian_fwhm": "↔", "soft_bias": "↔", "gain": "↔", "bg_mean": "↔",
        "bg_variance": "↓", "minarea": "↓", "dilation_radius": "↑", "max_area": "↑",
        "max_elongation": "↑", "exclude_center_pixels": "↓",
    },
}


def newest_file(root: Path, name: str) -> Path | None:
    candidates = []
    for path in root.rglob(name):
        if not path.is_file():
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("metric_version") == REQUIRED_METRIC_VERSION:
            candidates.append(path)
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def current_optimisation_winner(root: Path, relative_path: Path, fallback_name: str) -> Path | None:
    """Prefer the declared clean-22 winner; only fall back for older installations."""
    candidate = root / CURRENT_OPTIMISATION_DIR / relative_path
    if candidate.is_file():
        try:
            with candidate.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError):
            payload = {}
        if payload.get("metric_version") == REQUIRED_METRIC_VERSION:
            return candidate
    return newest_file(root, fallback_name)


def research_output_root(pc_name: str) -> Path:
    if os.name == "nt":
        return remove_foreground_folder(pc_name)
    drive = "d" if pc_name == "Desktop" else "c"
    return Path(f"/mnt/{drive}/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects")


def production_params(path: Path | None, defaults: dict, loader) -> dict:
    """Load parameters through the exact loader used by the 182-galaxy batch."""
    if path is None:
        return dict(defaults)
    loaded = loader(path)
    return {key: loaded.get(key, value) for key, value in defaults.items()}


def format_parameter(value) -> str:
    """Format editable numeric controls to no more than three significant figures."""
    if isinstance(value, str):
        return value
    number = float(value)
    if math.isnan(number):
        return "nan"
    return f"{number:.3g}"


def finite_gaussian(image: np.ndarray, sigma: float) -> np.ndarray:
    finite = np.isfinite(image)
    fill = float(np.nanmedian(image[finite])) if np.any(finite) else 0.0
    values = np.where(finite, image, fill)
    weights = ndimage.gaussian_filter(finite.astype(float), sigma=max(0.1, sigma), mode="nearest")
    smooth = ndimage.gaussian_filter(values * finite, sigma=max(0.1, sigma), mode="nearest")
    return np.divide(smooth, weights, out=np.full_like(smooth, fill), where=weights > 1.0e-8)


def observed_centered_cutout(image: np.ndarray, geometry: dict, radius_arcsec: float, order: int = 1):
    """Return a galaxy-centred detector-plane view without deprojecting sources."""
    pixel_scale = geometry["pixel_scale"]
    radius_pixels = max(2, int(math.ceil(radius_arcsec / pixel_scale)))
    axis = np.arange(-radius_pixels, radius_pixels + 1, dtype=float) * pixel_scale
    xx, yy = np.meshgrid(axis, axis)
    source_x = geometry["xc"] - 1.0 + xx / pixel_scale
    source_y = geometry["yc"] - 1.0 + yy / pixel_scale
    finite = np.isfinite(image)
    fill = float(np.nanmedian(image[finite])) if np.any(finite) else 0.0
    sampled = ndimage.map_coordinates(
        np.where(finite, image, fill),
        [source_y, source_x],
        order=order,
        mode="constant",
        cval=fill,
        prefilter=order > 1,
    )
    return sampled, axis, axis


def display_orientation_sign(geometry: dict) -> float:
    """Resolve the bar's 180-degree ambiguity to preserve observed vertical orientation."""
    transform = display.image_transform(geometry["disk_pa"], geometry["inclination"], geometry["bar_pa"])
    return 1.0 if transform[1, 1] >= 0 else -1.0


def oriented_deprojected_cutout(image: np.ndarray, geometry: dict, radius_arcsec: float, order: int = 1):
    """Deproject and bar-align without an avoidable 180-degree view reversal."""
    pixel_scale = geometry["pixel_scale"]
    radius_pixels = max(8, int(math.ceil(radius_arcsec / pixel_scale)))
    offsets = np.arange(-radius_pixels, radius_pixels + 1, dtype=float)
    xx, yy = np.meshgrid(offsets, offsets)
    transform = display.image_transform(geometry["disk_pa"], geometry["inclination"], geometry["bar_pa"])
    transform *= display_orientation_sign(geometry)
    input_offsets = np.linalg.inv(transform) @ np.vstack([xx.ravel(), yy.ravel()])
    source_x = geometry["xc"] - 1.0 + input_offsets[0].reshape(xx.shape)
    source_y = geometry["yc"] - 1.0 + input_offsets[1].reshape(yy.shape)
    finite = np.isfinite(image)
    sampled = ndimage.map_coordinates(
        np.where(finite, image, 0.0), [source_y, source_x], order=order,
        mode="constant", cval=0.0, prefilter=order > 1,
    )
    support = ndimage.map_coordinates(
        finite.astype(float), [source_y, source_x], order=0, mode="constant", cval=0.0,
    )
    view = np.divide(sampled, support, out=np.full_like(sampled, np.nan), where=support > 0.5)
    axis = offsets * pixel_scale
    return view, axis, axis


def standardized_gaussian_residual(image: np.ndarray, geometry: dict, blur_sigma: float) -> np.ndarray:
    """Match the cleanliness reviewer's centred Gaussian residual in sigma units."""
    model = finite_gaussian(image, blur_sigma)
    residual = image - model
    yy, xx = np.indices(image.shape)
    x0, y0 = geometry["xc"] - 1.0, geometry["yc"] - 1.0
    radius = np.hypot(xx - x0, yy - y0)
    aperture = max(12.0, 3.0 * geometry["bar_sma"] / geometry["pixel_scale"])
    centre = max(3.0, 0.35 * geometry["bar_sma"] / geometry["pixel_scale"])
    sample_mask = (radius <= aperture) & (radius >= centre) & np.isfinite(residual)
    sample = residual[sample_mask]
    if sample.size < 10:
        location = float(np.nanmedian(residual))
        scale = core.robust_sigma(residual)
    else:
        location = float(np.median(sample))
        scale = 1.4826 * float(np.median(np.abs(sample - location)))
        for _ in range(3):
            clipped = sample[np.abs(sample - location) < 4.0 * scale]
            if clipped.size < 10:
                break
            location = float(np.median(clipped))
            scale = 1.4826 * float(np.median(np.abs(clipped - location)))
        if not math.isfinite(scale) or scale <= 0:
            scale = core.robust_sigma(sample)
    return (residual - location) / scale


def catalogue_residual_products(image: np.ndarray, geometry: dict):
    """Reproduce the fixed five-pixel residual products used for catalogue scoring."""
    model = finite_gaussian(image, 5.0)
    residual = image - model
    yy, xx = np.indices(image.shape)
    x0, y0 = geometry["xc"] - 1.0, geometry["yc"] - 1.0
    radius = np.hypot(xx - x0, yy - y0)
    aperture = max(12.0, 3.0 * geometry["bar_sma"] / geometry["pixel_scale"])
    centre = max(3.0, 0.35 * geometry["bar_sma"] / geometry["pixel_scale"])
    annulus = (radius <= aperture) & (radius >= centre) & np.isfinite(residual)
    sample = residual[annulus]
    if sample.size < 10:
        return standardized_gaussian_residual(image, geometry, 5.0), np.zeros_like(image), aperture, centre
    location = float(np.median(sample))
    scale = 1.4826 * float(np.median(np.abs(sample - location)))
    for _ in range(3):
        clipped = sample[np.abs(sample - location) < 4.0 * scale]
        if clipped.size < 10:
            break
        location = float(np.median(clipped))
        scale = 1.4826 * float(np.median(np.abs(clipped - location)))
    if not math.isfinite(scale) or scale <= 0:
        scale = core.robust_sigma(sample)
    z_image = (residual - location) / scale
    model_sample = model[annulus & np.isfinite(model)]
    model_sky = float(np.percentile(model_sample, 20)) if model_sample.size else 0.0
    underlying = np.maximum((model - model_sky) / scale, 0.0)
    return z_image, underlying, aperture, centre


def catalogue_wcs(header) -> WCS:
    """Build the declared celestial WCS without inconsistent undeclared SIP terms."""
    cleaned = header.copy()
    sip_key = re.compile(r"^(A|B|AP|BP)_(ORDER|DMAX|\d+_\d+)$")
    for key in list(cleaned):
        if sip_key.match(str(key)):
            del cleaned[key]
    return WCS(cleaned).celestial


class CombinedToyTester(tk.Tk):
    def __init__(self, args: argparse.Namespace):
        super().__init__()
        self.title("SEP and MTObjects Interactive Toy Laboratory")
        width = min(3840, self.winfo_screenwidth())
        height = min(1600, self.winfo_screenheight())
        self.geometry(f"{width}x{height}+0+0")
        self.minsize(1600, 900)

        self.pc = args.pc
        self.manifest = args.manifest
        self.mtobjects_root = args.mtobjects_root
        if self.mtobjects_root is None and os.name != "nt":
            compiled_wsl_root = Path("/root/mtobjects-linux-final20")
            if compiled_wsl_root.exists():
                self.mtobjects_root = compiled_wsl_root
        self.data: np.ndarray | None = None
        self.geometry_data: dict[str, float] | None = None
        self.toys: list[dict] = []
        self.toys_enabled = True
        self.last_results: dict[str, dict] = {}

        self.all_rows = display.read_manifest(self.manifest)
        self.rows = display.rows_with_images_for_pc(self.all_rows, self.pc)
        self.rows_by_name = {row["name"]: row for row in self.rows}
        research_root = research_output_root(self.pc)
        self.classifications = self._load_classifications(research_root)
        self.gaia_cache = research_root / "clean_galaxy_ranking_gaia" / "gaia_cache"
        self.twomass_cache: dict[str, Path] = {}
        for cache_dir in (
            research_root / "gaia_zero_57_hybrid_ranking" / "twomass_cache",
            research_root / "catalogue_review_phase2_next30" / "twomass_cache",
            research_root / "catalogue_review_phase3_clean_similarity" / "twomass_cache",
        ):
            if cache_dir.exists():
                for path in cache_dir.glob("*.ecsv"):
                    self.twomass_cache[path.stem] = path
        self.catalogue_sources = {"2MASS": [], "Gaia": []}
        self.research_root = research_root
        self.sep_best = args.sep_best or current_optimisation_winner(
            research_root, SEP_WINNER_RELATIVE, "sep_toy_cross_validation_best.json"
        )
        self.mto_best = args.mto_best or current_optimisation_winner(
            research_root, MTO_WINNER_RELATIVE, "mtobjects_toy_cross_validation_best.json"
        )
        self.sep_defaults = production_params(
            self.sep_best, core.AZURE_MEAN_PARAMS["SEP"], sep_batch.load_best_params
        )
        self.mto_defaults = production_params(
            self.mto_best, core.AZURE_MEAN_PARAMS["MTObjects"], mto_batch.load_best_params
        )
        self.output_dir = research_root / "interactive_sep_mtobjects_toy_laboratory"

        self._build_controls()
        self._build_figure()
        self._populate_galaxies()
        self.after_idle(self._fit_figure)

    @staticmethod
    def _load_classifications(root: Path) -> dict[str, str]:
        paths = list(root.rglob("candidate_union_rereview_decisions.csv"))
        if not paths:
            return {}
        path = max(paths, key=lambda item: item.stat().st_mtime)
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            return {row["name"].strip(): row["classification"].strip() for row in csv.DictReader(handle)}

    def _build_controls(self) -> None:
        controls = ttk.Frame(self, padding=(8, 6), width=600)
        controls.pack(side=tk.LEFT, fill=tk.Y)
        controls.pack_propagate(False)

        selection = ttk.LabelFrame(controls, text="Galaxy and residual", padding=7)
        selection.pack(fill=tk.X, pady=(0, 5))
        self.galaxy_var = tk.StringVar()
        self.galaxy_combo = ttk.Combobox(selection, textvariable=self.galaxy_var, state="readonly", width=32)
        self.galaxy_combo.pack(fill=tk.X)
        self.galaxy_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_galaxy())
        blur_row = ttk.Frame(selection)
        blur_row.pack(fill=tk.X, pady=(7, 0))
        ttk.Label(blur_row, text="Gaussian blur sigma (pixels)").pack(side=tk.LEFT)
        self.blur_var = tk.DoubleVar(value=5.0)
        blur = ttk.Spinbox(blur_row, textvariable=self.blur_var, from_=0.5, to=100, increment=0.5, width=8)
        blur.pack(side=tk.RIGHT)
        blur.configure(command=self.draw_preview)
        blur.bind("<Return>", lambda _event: self.draw_preview())
        blur.bind("<FocusOut>", lambda _event: self.draw_preview())
        view_row = ttk.Frame(selection)
        view_row.pack(fill=tk.X, pady=(7, 0))
        ttk.Label(view_row, text="Display coordinates").pack(side=tk.LEFT)
        self.view_mode = tk.StringVar(value="Galaxy deprojected")
        view_combo = ttk.Combobox(
            view_row,
            textvariable=self.view_mode,
            values=("Galaxy deprojected", "Observed sky"),
            state="readonly",
            width=19,
        )
        view_combo.pack(side=tk.RIGHT)
        view_combo.bind("<<ComboboxSelected>>", lambda _event: self.redraw_current())
        stretch_row = ttk.Frame(selection)
        stretch_row.pack(fill=tk.X, pady=(7, 0))
        ttk.Label(stretch_row, text="Image stretch").pack(side=tk.LEFT)
        self.stretch_mode = tk.StringVar(value="AutoStretch")
        stretch_combo = ttk.Combobox(
            stretch_row,
            textvariable=self.stretch_mode,
            values=("AutoStretch", "Boosted AutoStretch", "Linear", "Log", "Asinh", "Square root"),
            state="readonly",
            width=19,
        )
        stretch_combo.pack(side=tk.RIGHT)
        stretch_combo.bind("<<ComboboxSelected>>", lambda _event: self.redraw_current())
        levels_row = ttk.Frame(selection)
        levels_row.pack(fill=tk.X, pady=(5, 0))
        self.black_percentile = tk.DoubleVar(value=1.0)
        self.white_percentile = tk.DoubleVar(value=99.5)
        self.stretch_strength = tk.DoubleVar(value=10.0)
        for label, variable, width in (
            ("Black %", self.black_percentile, 6),
            ("White %", self.white_percentile, 6),
            ("Strength", self.stretch_strength, 6),
        ):
            ttk.Label(levels_row, text=label).pack(side=tk.LEFT, padx=(0, 2))
            entry = ttk.Entry(levels_row, textvariable=variable, width=width)
            entry.pack(side=tk.LEFT, padx=(0, 6))
            entry.bind("<Return>", lambda _event: self.redraw_current())
            entry.bind("<FocusOut>", lambda _event: self.redraw_current())
        auto_row = ttk.Frame(selection)
        auto_row.pack(fill=tk.X, pady=(5, 0))
        self.autostretch_shadows = tk.DoubleVar(value=-2.8)
        self.autostretch_background = tk.DoubleVar(value=0.25)
        for label, variable in (
            ("Auto shadows (sigma)", self.autostretch_shadows),
            ("Target background", self.autostretch_background),
        ):
            ttk.Label(auto_row, text=label).pack(side=tk.LEFT, padx=(0, 2))
            entry = ttk.Entry(auto_row, textvariable=variable, width=6)
            entry.pack(side=tk.LEFT, padx=(0, 6))
            entry.bind("<Return>", lambda _event: self.redraw_current())
            entry.bind("<FocusOut>", lambda _event: self.redraw_current())
        boost_row = ttk.Frame(selection)
        boost_row.pack(fill=tk.X, pady=(5, 0))
        self.boosted_clipping_factor = tk.DoubleVar(value=0.75)
        self.boosted_background_factor = tk.DoubleVar(value=2.0)
        for label, variable in (
            ("Boost clipping x", self.boosted_clipping_factor),
            ("Boost background x", self.boosted_background_factor),
        ):
            ttk.Label(boost_row, text=label).pack(side=tk.LEFT, padx=(0, 2))
            entry = ttk.Entry(boost_row, textvariable=variable, width=6)
            entry.pack(side=tk.LEFT, padx=(0, 6))
            entry.bind("<Return>", lambda _event: self.redraw_current())
            entry.bind("<FocusOut>", lambda _event: self.redraw_current())
        self.source_var = tk.StringVar()
        ttk.Label(selection, textvariable=self.source_var, wraplength=570, foreground="#555555").pack(fill=tk.X, pady=(7, 0))

        toys = ttk.LabelFrame(controls, text="Toy specification - left-click Original to add", padding=7)
        toys.pack(fill=tk.X, pady=5)
        self.toy_type = tk.StringVar(value="Gaussian star")
        toy_type_combo = ttk.Combobox(
            toys,
            textvariable=self.toy_type,
            values=list(core.TOY_TYPES),
            state="readonly",
            width=20,
        )
        toy_type_combo.grid(row=0, column=0, columnspan=2, sticky="ew")
        toy_type_combo.bind("<<ComboboxSelected>>", self.toy_type_changed)
        self.toy_vars = {
            "peak_sigma": tk.DoubleVar(value=30.0), "fwhm_pixels": tk.DoubleVar(value=1.5),
            "axis_ratio": tk.DoubleVar(value=1.0), "pa_deg": tk.DoubleVar(value=0.0),
            "truth_dilation": tk.IntVar(value=0),
        }
        specs = (("Peak residual sigma", "peak_sigma", .5), ("FWHM pixels", "fwhm_pixels", .5),
                 ("Axis ratio", "axis_ratio", .05), ("Position angle", "pa_deg", 5),
                 ("Truth dilation", "truth_dilation", 1))
        for index, (label, key, step) in enumerate(specs, 1):
            row, col = 1 + (index - 1) // 2, (index - 1) % 2
            cell = ttk.Frame(toys)
            cell.grid(row=row, column=col, sticky="ew", padx=2, pady=2)
            ttk.Label(cell, text=label).pack(anchor="w")
            ttk.Spinbox(cell, textvariable=self.toy_vars[key], from_=-180 if key == "pa_deg" else 0,
                        to=180 if key == "pa_deg" else 200, increment=step, width=8).pack(anchor=tk.W)
        buttons = ttk.Frame(toys)
        buttons.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        ttk.Button(buttons, text="Remove last", command=self.remove_last).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(buttons, text="Clear toys", command=self.clear_toys).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
        self.toy_count = tk.StringVar(value="0 toys")
        ttk.Label(buttons, textvariable=self.toy_count).pack(side=tk.LEFT, padx=5)
        toys.columnconfigure(0, weight=1); toys.columnconfigure(1, weight=1)

        self.sep_vars = self._parameter_box(controls, "SEP parameters", SEP_KEYS, self.sep_defaults)
        self.mto_vars = self._parameter_box(controls, "MTObjects parameters", MTO_KEYS, self.mto_defaults)
        sep_source = self.sep_best.name if self.sep_best else "built-in defaults"
        mto_source = self.mto_best.name if self.mto_best else "built-in defaults"
        self.source_var.set(f"Loaded parameters: SEP {sep_source}; MTObjects {mto_source}")

        action = ttk.Frame(controls, padding=(0, 7, 0, 0))
        action.pack(fill=tk.X)
        ttk.Button(action, text="CALCULATE SEP + MTOBJECTS", command=self.calculate).pack(fill=tk.X, ipady=5)
        self.toys_button_text = tk.StringVar(value="Toys IN — click to show results without toys")
        ttk.Button(action, textvariable=self.toys_button_text, command=self.toggle_toys).pack(
            fill=tk.X, pady=(5, 0), ipady=3
        )
        action_row = ttk.Frame(action)
        action_row.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(action_row, text="Reload current optimum", command=self.reload_optimised_parameters).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(action_row, text="Reset displayed values", command=self.reset_parameters).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        ttk.Button(action_row, text="Save PNG", command=self.save_png).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self.status = tk.StringVar(value="Select a galaxy, add toys on the Original panel, then Calculate.")
        ttk.Label(action, textvariable=self.status, foreground="#1f4d78", wraplength=570).pack(fill=tk.X, pady=(7, 0))
        ttk.Label(
            action,
            text="Red circles = 2MASS   |   Deep-blue circles = Gaia   |   Green boundaries = toy objects",
            foreground="#555555",
            wraplength=570,
        ).pack(fill=tk.X, pady=(5, 0))

    def toy_type_changed(self, _event=None) -> None:
        """Apply morphology-appropriate starting values for a newly selected toy type."""
        defaults = {
            "Gaussian star": {"fwhm_pixels": 1.5, "axis_ratio": 1.0, "pa_deg": 0.0, "truth_dilation": 0},
            "Star cluster": {"fwhm_pixels": 6.0, "axis_ratio": 1.0, "pa_deg": 0.0, "truth_dilation": 1},
            "Compact galaxy": {"fwhm_pixels": 10.0, "axis_ratio": 0.65, "pa_deg": 30.0, "truth_dilation": 1},
        }
        for key, value in defaults[self.toy_type.get()].items():
            self.toy_vars[key].set(value)
        self.status.set(
            "Toy defaults updated. Foreground stars are circular in the observed image; "
            "high-inclination galaxy deprojection can stretch their displayed outline."
        )

    def _parameter_box(self, parent, title: str, keys: tuple[str, ...], defaults: dict) -> dict[str, tk.Variable]:
        frame = ttk.LabelFrame(parent, text=title, padding=7)
        frame.pack(fill=tk.X, pady=5)
        variables: dict[str, tk.Variable] = {}
        directions = MASKING_DIRECTIONS[title]
        for index, key in enumerate(keys):
            row, group = index % 7, index // 7
            label_col = group * 2
            ttk.Label(frame, text=f"{key} {directions[key]}").grid(
                row=row, column=label_col, sticky="e", padx=(2, 3), pady=1
            )
            value = defaults.get(key, "")
            variable = tk.StringVar(value=format_parameter(value))
            variables[key] = variable
            if key == "detect_on":
                widget = ttk.Combobox(frame, textvariable=variable, values=("original", "residual"), state="readonly", width=11)
            else:
                widget = ttk.Entry(frame, textvariable=variable, width=8)
            widget.grid(row=row, column=label_col + 1, sticky="w", pady=1)
        for col in range(4):
            frame.columnconfigure(col, weight=0)
        ttk.Label(
            frame,
            text="↑ higher = more masking   ↓ lower = more masking   ↔ variable/non-monotonic",
            foreground="#555555",
        ).grid(row=7, column=0, columnspan=4, sticky="w", pady=(4, 0))
        return variables

    def _build_figure(self) -> None:
        self.figure = Figure(figsize=(36, 11), dpi=100, constrained_layout=True)
        grid = self.figure.add_gridspec(2, 3)
        self.axes = np.array([[self.figure.add_subplot(grid[r, c]) for c in range(3)] for r in range(2)], dtype=object)
        for axis in self.axes.ravel():
            axis.set_box_aspect(0.72)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self.canvas, self, pack_toolbar=False).pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.mpl_connect("button_press_event", self.on_click)

    def _fit_figure(self) -> None:
        self.update_idletasks()
        widget = self.canvas.get_tk_widget()
        if widget.winfo_width() <= 1:
            self.after(30, self._fit_figure); return
        self.figure.set_size_inches(widget.winfo_width() / 100, widget.winfo_height() / 100, forward=False)
        self.canvas.draw()

    def _populate_galaxies(self) -> None:
        labels = []
        self.label_to_name = {}
        order = {"Clean": 0, "Ambiguous": 1, "Polluted": 2, "Unreviewed": 3}
        for row in self.rows:
            name = row["name"]
            classification = self.classifications.get(name, "Unreviewed")
            label = f"{name} - {classification}"
            labels.append(label); self.label_to_name[label] = name
        labels.sort(key=lambda label: (order.get(label.rsplit(" - ", 1)[-1], 4), self.label_to_name[label]))
        self.galaxy_combo.configure(values=labels)
        if labels:
            self.galaxy_var.set(labels[0]); self.load_galaxy()

    def load_galaxy(self) -> None:
        name = self.label_to_name.get(self.galaxy_var.get(), "")
        row = self.rows_by_name.get(name)
        if row is None:
            return
        geometry = display.required_geometry(row)
        if geometry is None:
            self.status.set(f"{name}: incomplete geometry"); return
        self.geometry_data = geometry
        self.data, header = sep_processing.load_fits(display.image_path_for_pc(row, self.pc))
        if self.mto_best is None:
            residual = self.data - mto_processing.smooth_model(self.data, sigma_pixels=15.0)
            calibrated_variance = core.robust_sigma(residual) ** 2
            self.mto_defaults["bg_variance"] = calibrated_variance
            self.mto_vars["bg_variance"].set(format_parameter(calibrated_variance))
            sep_source = self.sep_best.name if self.sep_best else "built-in defaults"
            self.source_var.set(
                f"Loaded parameters: SEP {sep_source}; MTObjects built-in defaults "
                f"with per-galaxy bg_variance={format_parameter(calibrated_variance)}"
            )
        self.catalogue_sources = self._catalogue_sources(name, header)
        self.toys.clear(); self.last_results.clear(); self._update_toys_state()
        self.draw_preview()

    def _parameter_values(self, variables: dict[str, tk.Variable]) -> dict:
        values = {}
        for key, variable in variables.items():
            text = str(variable.get()).strip()
            if key == "detect_on":
                values[key] = text
            elif key in INTEGER_KEYS:
                values[key] = int(round(float(text)))
            else:
                values[key] = float(text)
        return values

    def reset_parameters(self) -> None:
        for variables, defaults in ((self.sep_vars, self.sep_defaults), (self.mto_vars, self.mto_defaults)):
            for key, variable in variables.items():
                value = defaults[key]
                variable.set(format_parameter(value))
        self.status.set("Restored the most recent optimised parameter sets.")

    def reload_optimised_parameters(self) -> None:
        """Reload completed clean-22 winners using the production batch loaders."""
        sep_path = current_optimisation_winner(
            self.research_root, SEP_WINNER_RELATIVE, "sep_toy_cross_validation_best.json"
        )
        mto_path = current_optimisation_winner(
            self.research_root, MTO_WINNER_RELATIVE, "mtobjects_toy_cross_validation_best.json"
        )
        try:
            sep_defaults = production_params(
                sep_path, core.AZURE_MEAN_PARAMS["SEP"], sep_batch.load_best_params
            )
            mto_defaults = production_params(
                mto_path, core.AZURE_MEAN_PARAMS["MTObjects"], mto_batch.load_best_params
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Parameter reload failed", str(exc))
            return
        self.sep_best, self.mto_best = sep_path, mto_path
        self.sep_defaults, self.mto_defaults = sep_defaults, mto_defaults
        self.reset_parameters()
        sep_source = str(sep_path) if sep_path else "built-in defaults (current winner not yet available)"
        mto_source = str(mto_path) if mto_path else "built-in defaults (current winner not yet available)"
        self.source_var.set(f"Production parameters: SEP {sep_source}; MTObjects {mto_source}")
        self.status.set("Reloaded parameters through the same loaders used by the 182-galaxy batch.")

    def _injected(self) -> tuple[np.ndarray, np.ndarray]:
        assert self.data is not None and self.geometry_data is not None
        sigma = core.robust_sigma(self.data)
        model = np.zeros_like(self.data, dtype=float)
        truth = np.zeros_like(self.data, dtype=bool)
        for spec in self.toys if self.toys_enabled else []:
            x_pix, y_pix = core.deprojected_to_observed_pixel(spec["x_arcsec"], spec["y_arcsec"], self.geometry_data)
            toy = core.toy_model(self.data.shape, spec["toy_type"], x_pix, y_pix,
                                 spec["peak_sigma"] * sigma, spec["fwhm_pixels"], spec["axis_ratio"], spec["pa_deg"])
            footprint = toy > np.nanmax(toy) * 0.08
            if spec["truth_dilation"]:
                footprint = ndimage.binary_dilation(footprint, structure=core.circular_footprint(spec["truth_dilation"]))
            model += toy; truth |= footprint
        injected = np.array(self.data, copy=True)
        injected[np.isfinite(injected)] += model[np.isfinite(injected)]
        return injected, truth

    @staticmethod
    def _clean_2mass_row(row) -> bool:
        ph_qual = str(row["ph_qual"])
        cc_flg = str(row["cc_flg"])
        return (
            len(ph_qual) >= 3 and ph_qual[2] in "ABC" and
            len(cc_flg) >= 3 and cc_flg[2] == "0" and
            int(row["use_src"]) == 1 and float(row["k_snr"]) >= 5.0
        )

    def _catalogue_sources(self, name: str, header) -> dict[str, list[dict]]:
        assert self.data is not None and self.geometry_data is not None
        z_image, underlying, aperture, centre = catalogue_residual_products(self.data, self.geometry_data)
        wcs = catalogue_wcs(header)
        paths = {
            "2MASS": self.twomass_cache.get(name),
            "Gaia": self.gaia_cache / f"{name}_v3.ecsv",
        }
        found: dict[str, list[dict]] = {"2MASS": [], "Gaia": []}
        x0, y0 = self.geometry_data["xc"] - 1.0, self.geometry_data["yc"] - 1.0
        for catalogue, path in paths.items():
            if path is None or not path.exists():
                continue
            try:
                table = Table.read(path, format="ascii.ecsv")
                ra_name, dec_name = ("ra", "dec") if "dec" in table.colnames else ("ra", "decl")
                coords = SkyCoord(np.asarray(table[ra_name]) * u.deg, np.asarray(table[dec_name]) * u.deg)
                xs, ys = wcs.world_to_pixel(coords)
                for row, x, y in zip(table, xs, ys):
                    ix, iy = int(round(float(x))), int(round(float(y)))
                    if ix < 2 or iy < 2 or ix >= z_image.shape[1] - 2 or iy >= z_image.shape[0] - 2:
                        continue
                    distance = float(np.hypot(x - x0, y - y0))
                    if distance < centre or distance > aperture:
                        continue
                    local = z_image[iy - 2 : iy + 3, ix - 2 : ix + 3]
                    peak = float(np.nanmax(local)) if np.any(np.isfinite(local)) else math.nan
                    if not math.isfinite(peak) or peak < 2.5:
                        continue
                    structure = 0.25 + 0.75 / (1.0 + float(underlying[iy, ix]) / 5.0)
                    if catalogue == "2MASS":
                        if not self._clean_2mass_row(row):
                            continue
                        brightness = float(np.clip((16.0 - float(row["k_m"])) / 5.0, 0.1, 1.5))
                        score = structure * brightness * math.log1p(peak - 2.5)
                    else:
                        parallax = float(row["parallax_over_error"])
                        parallax_sig = abs(parallax) if math.isfinite(parallax) else 0.0
                        score = 0.12 * structure * min(parallax_sig / 3.0, 1.0) * math.log1p(peak - 2.5)
                    found[catalogue].append({"x": float(x), "y": float(y), "score": float(score)})
            except Exception:  # A missing/malformed cache must not prevent image inspection.
                continue
            found[catalogue].sort(key=lambda source: source["score"], reverse=True)
            found[catalogue] = found[catalogue][:5]
        return found

    def _catalogue_display_position(self, source: dict) -> tuple[float, float]:
        assert self.geometry_data is not None
        offset = np.array([
            source["x"] - (self.geometry_data["xc"] - 1.0),
            source["y"] - (self.geometry_data["yc"] - 1.0),
        ])
        if self.view_mode.get() == "Galaxy deprojected":
            transform = display.image_transform(
                self.geometry_data["disk_pa"], self.geometry_data["inclination"], self.geometry_data["bar_pa"]
            )
            offset = display_orientation_sign(self.geometry_data) * (transform @ offset)
        return tuple(offset * self.geometry_data["pixel_scale"])

    def _draw_catalogue_sources(self, axis) -> None:
        for catalogue, colour, radius, linewidth in (
            ("2MASS", "#ff0000", 2.0, 2.6),
            ("Gaia", "#0047d7", 1.5, 1.3),
        ):
            for source in self.catalogue_sources[catalogue]:
                axis.add_patch(Circle(
                    self._catalogue_display_position(source), radius,
                    fill=False, edgecolor=colour, linewidth=linewidth, zorder=12,
                ))

    def _draw_image(
        self,
        axis,
        image: np.ndarray,
        title: str,
        *,
        mask: bool = False,
        residual: bool = False,
        catalogue: bool = False,
        truth: np.ndarray | None = None,
    ) -> None:
        assert self.geometry_data is not None
        radius = display.profile_radius_pixels(image, self.geometry_data) * self.geometry_data["pixel_scale"]
        if self.view_mode.get() == "Observed sky":
            view, x_axis, y_axis = observed_centered_cutout(image, self.geometry_data, radius, order=0 if mask else 1)
            coordinate_label = "observed arcsec"
        else:
            view, x_axis, y_axis = oriented_deprojected_cutout(
                image, self.geometry_data, radius, order=0 if mask else 1
            )
            coordinate_label = "bar-aligned arcsec"
        axis.clear()
        if mask:
            limits, colour_map = (0, 1), "gray_r"
        elif residual:
            limits, colour_map = (-5, 10), "coolwarm"
        else:
            view = self._stretched_view(view)
            limits, colour_map = (0, 1), "gist_gray_r"
        axis.imshow(view, origin="lower", extent=[x_axis[0], x_axis[-1], y_axis[0], y_axis[-1]],
                    cmap=colour_map, vmin=limits[0], vmax=limits[1])
        axis.set_title(title, fontsize=12)
        axis.set_xlabel(coordinate_label)
        axis.set_ylabel("observed arcsec" if self.view_mode.get() == "Observed sky" else "deprojected arcsec")
        axis.axvline(0, color="#e53935", linestyle="--", linewidth=0.8, alpha=0.75)
        axis.axhline(0, color="#1976d2", linestyle="--", linewidth=0.8, alpha=0.75)
        if truth is not None and np.any(truth):
            if self.view_mode.get() == "Observed sky":
                truth_view, _, _ = observed_centered_cutout(truth, self.geometry_data, radius, order=0)
            else:
                truth_view, _, _ = oriented_deprojected_cutout(truth, self.geometry_data, radius, order=0)
            axis.contour(x_axis, y_axis, truth_view.astype(float), levels=[0.5], colors=["lime"], linewidths=2)
        if catalogue:
            self._draw_catalogue_sources(axis)

    def _stretched_view(self, view: np.ndarray) -> np.ndarray:
        """Apply a display-only intensity stretch to a finite image view."""
        finite = np.asarray(view, dtype=float)[np.isfinite(view)]
        if finite.size == 0:
            return np.zeros_like(view, dtype=float)
        mode = self.stretch_mode.get()
        if mode in ("AutoStretch", "Boosted AutoStretch"):
            return self._autostretched_view(view, finite)
        low = float(self.black_percentile.get())
        high = float(self.white_percentile.get())
        if not (0 <= low < high <= 100):
            raise ValueError("Display percentiles must satisfy 0 <= black < white <= 100")
        black, white = np.percentile(finite, [low, high])
        if not math.isfinite(black) or not math.isfinite(white) or white <= black:
            black, white = float(np.nanmin(finite)), float(np.nanmax(finite))
        scaled = np.clip((np.asarray(view, dtype=float) - black) / max(white - black, np.finfo(float).eps), 0, 1)
        strength = max(0.01, float(self.stretch_strength.get()))
        if mode == "Log":
            scaled = np.log1p(strength * scaled) / math.log1p(strength)
        elif mode == "Asinh":
            scaled = np.arcsinh(strength * scaled) / np.arcsinh(strength)
        elif mode == "Square root":
            scaled = np.sqrt(scaled)
        return np.where(np.isfinite(view), scaled, np.nan)

    @staticmethod
    def _midtones_transfer(midtones: float, samples: np.ndarray | float):
        """PixInsight/XISF rational midtones transfer function."""
        m = float(np.clip(midtones, np.finfo(float).eps, 1.0 - np.finfo(float).eps))
        x = np.clip(samples, 0.0, 1.0)
        denominator = (2.0 * m - 1.0) * x - m
        with np.errstate(divide="ignore", invalid="ignore"):
            result = ((m - 1.0) * x) / denominator
        return np.where(x <= 0.0, 0.0, np.where(x >= 1.0, 1.0, result))

    def _autostretched_view(self, view: np.ndarray, finite: np.ndarray) -> np.ndarray:
        """Apply a robust, display-only PixInsight-style automatic STF."""
        data_min = float(np.min(finite))
        data_max = float(np.max(finite))
        span = data_max - data_min
        if not math.isfinite(span) or span <= np.finfo(float).eps:
            return np.zeros_like(view, dtype=float)

        normalised = (np.asarray(view, dtype=float) - data_min) / span
        finite_normalised = (finite - data_min) / span
        median = float(np.median(finite_normalised))
        robust_sigma = 1.4826 * float(np.median(np.abs(finite_normalised - median)))
        shadows = float(self.autostretch_shadows.get())
        target = float(self.autostretch_background.get())
        if self.stretch_mode.get() == "Boosted AutoStretch":
            clipping_factor = float(self.boosted_clipping_factor.get())
            background_factor = float(self.boosted_background_factor.get())
            if clipping_factor <= 0.0 or background_factor <= 0.0:
                raise ValueError("Boosted AutoStretch factors must be greater than zero")
            shadows *= clipping_factor
            target *= background_factor
        if not (-20.0 <= shadows <= 0.0):
            raise ValueError("AutoStretch shadows must be between -20 and 0 sigma")
        if not (0.0 < target < 1.0):
            raise ValueError("AutoStretch target background must be between 0 and 1")

        black = float(np.clip(median + shadows * robust_sigma, 0.0, 1.0))
        scaled = np.clip((normalised - black) / max(1.0 - black, np.finfo(float).eps), 0.0, 1.0)
        median_after_black = float(np.clip((median - black) / max(1.0 - black, np.finfo(float).eps), 0.0, 1.0))
        midtones = float(self._midtones_transfer(target, median_after_black))
        stretched = self._midtones_transfer(midtones, scaled)
        return np.where(np.isfinite(view), stretched, np.nan)

    def _display_view(self, image: np.ndarray, *, order: int = 1):
        assert self.geometry_data is not None
        radius = display.profile_radius_pixels(image, self.geometry_data) * self.geometry_data["pixel_scale"]
        if self.view_mode.get() == "Observed sky":
            return observed_centered_cutout(image, self.geometry_data, radius, order=order)
        return oriented_deprojected_cutout(image, self.geometry_data, radius, order=order)

    def _draw_mask_pair(self, mask_axis, recovered_axis, injected: np.ndarray, products: dict, method: str) -> float:
        """Draw the mask and recovery using the established red/orange diagnostic style."""
        mask = np.asarray(products["mask"], dtype=bool)
        cleaned = np.asarray(products["cleaned"], dtype=float)
        mask_view, x_axis, y_axis = self._display_view(mask, order=0)
        injected_view, _, _ = self._display_view(injected, order=1)
        shown_pixels = np.isfinite(injected_view)
        shown_masked_fraction = (
            float(np.count_nonzero((mask_view >= 0.5) & shown_pixels) / np.count_nonzero(shown_pixels))
            if np.any(shown_pixels)
            else 0.0
        )

        self._draw_image(
            mask_axis,
            injected,
            f"{method} Mask | masked {shown_masked_fraction:.1%} of displayed frame",
        )
        if np.any(mask_view >= 0.5):
            mask_axis.contourf(
                x_axis,
                y_axis,
                mask_view.astype(float),
                levels=[0.5, 1.5],
                colors=["#e53935"],
                alpha=0.72,
            )
            # Restore guides above the translucent overlay.
            mask_axis.axvline(0, color="#e53935", linestyle="--", linewidth=0.8, alpha=0.8)
            mask_axis.axhline(0, color="#1976d2", linestyle="--", linewidth=0.8, alpha=0.8)

        self._draw_image(recovered_axis, cleaned, f"{method} Recovered Image | orange={method} mask")
        if np.any(mask_view >= 0.5):
            recovered_axis.contour(
                x_axis,
                y_axis,
                mask_view.astype(float),
                levels=[0.5],
                colors=["#ff7f0e"],
                linewidths=1.6,
            )
        return shown_masked_fraction

    def redraw_current(self) -> None:
        if self.last_results:
            self.draw_results()
        else:
            self.draw_preview()

    def draw_preview(self) -> None:
        if self.data is None:
            return
        try:
            injected, truth = self._injected()
            residual_image = standardized_gaussian_residual(injected, self.geometry_data, float(self.blur_var.get()))
        except (ValueError, tk.TclError):
            return
        self._draw_image(
            self.axes[0, 0], injected,
            f"Original centred — toys {'IN' if self.toys_enabled else 'OUT'} | "
            f"2MASS {len(self.catalogue_sources['2MASS'])}; Gaia {len(self.catalogue_sources['Gaia'])}",
            truth=truth, catalogue=True,
        )
        self._draw_image(
            self.axes[1, 0],
            residual_image,
            f"Gaussian residual in sigma units (blur={float(self.blur_var.get()):g} px)",
            residual=True,
            truth=truth,
        )
        for axis, title in zip(self.axes[:, 1:].ravel(), ("SEP mask", "SEP recovered image", "MTObjects mask", "MTObjects recovered image")):
            axis.clear(); axis.set_title(title); axis.text(.5, .5, "Press Calculate", ha="center", va="center", transform=axis.transAxes, color="0.45")
        self.canvas.draw_idle()

    def on_click(self, event) -> None:
        if event.inaxes is not self.axes[0, 0] or event.xdata is None or event.ydata is None:
            return
        if event.button == 3:
            self.remove_last(); return
        try:
            spec = {key: float(variable.get()) for key, variable in self.toy_vars.items() if key != "truth_dilation"}
            spec["truth_dilation"] = int(self.toy_vars["truth_dilation"].get())
            x_arcsec = float(event.xdata)
            y_arcsec = float(event.ydata)
            if self.view_mode.get() == "Observed sky":
                transform = display.image_transform(
                    self.geometry_data["disk_pa"],
                    self.geometry_data["inclination"],
                    self.geometry_data["bar_pa"],
                )
                x_arcsec, y_arcsec = transform @ np.array([x_arcsec, y_arcsec])
            else:
                sign = display_orientation_sign(self.geometry_data)
                x_arcsec *= sign
                y_arcsec *= sign
            spec.update(toy_type=core.TOY_TYPES[self.toy_type.get()], x_arcsec=x_arcsec, y_arcsec=y_arcsec)
            self.toys.append(spec)
            self.toys_enabled = True
            self._update_toys_state()
            self.last_results.clear(); self.draw_preview()
        except (KeyError, ValueError, tk.TclError) as exc:
            messagebox.showerror("Invalid toy parameters", str(exc))

    def remove_last(self) -> None:
        if self.toys:
            self.toys.pop()
        self._update_toys_state()
        self.last_results.clear(); self.draw_preview()

    def clear_toys(self) -> None:
        self.toys.clear(); self._update_toys_state(); self.last_results.clear(); self.draw_preview()

    def _update_toys_state(self) -> None:
        count = len(self.toys)
        state = "IN" if self.toys_enabled else "OUT"
        self.toy_count.set(f"{count} toy{'s' if count != 1 else ''} stored — {state}")
        self.toys_button_text.set(
            "Toys IN — click to show results without toys"
            if self.toys_enabled else
            "Toys OUT — click to show results with toys"
        )

    def toggle_toys(self) -> None:
        self.toys_enabled = not self.toys_enabled
        self._update_toys_state()
        self.last_results.clear()
        if self.data is not None:
            self.calculate()

    def calculate(self) -> None:
        if self.data is None or self.geometry_data is None:
            return
        try:
            injected, truth = self._injected()
            sep = sep_processing.sep_products(injected, self._parameter_values(self.sep_vars), self.geometry_data)
            root = mto_processing.find_mtobjects_root(self.mtobjects_root)
            mto = mto_processing.mtobjects_products(injected, self._parameter_values(self.mto_vars), self.geometry_data, root)
            self.last_results = {"SEP": sep, "MTObjects": mto}
            shown_fractions = self.draw_results(injected=injected, truth=truth)
            sep_fraction, mto_fraction = shown_fractions
            self.status.set(
                f"Calculated with toys {'IN' if self.toys_enabled else 'OUT'} "
                f"({len(self.toys) if self.toys_enabled else 0} active) | displayed frame masked: "
                f"SEP {sep_fraction:.2%}, MTObjects {mto_fraction:.2%}"
            )
            self.canvas.draw_idle()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Calculation failed", str(exc))

    def draw_results(self, injected: np.ndarray | None = None, truth: np.ndarray | None = None):
        if not self.last_results:
            self.draw_preview()
            return 0.0, 0.0
        if injected is None or truth is None:
            injected, truth = self._injected()
        sep = self.last_results["SEP"]
        mto = self.last_results["MTObjects"]
        self._draw_image(
            self.axes[0, 0], injected,
            f"Original centred — toys {'IN' if self.toys_enabled else 'OUT'} | "
            f"2MASS {len(self.catalogue_sources['2MASS'])}; Gaia {len(self.catalogue_sources['Gaia'])}",
            truth=truth, catalogue=True,
        )
        residual_image = standardized_gaussian_residual(injected, self.geometry_data, float(self.blur_var.get()))
        self._draw_image(
            self.axes[1, 0],
            residual_image,
            f"Gaussian residual in sigma units (blur={float(self.blur_var.get()):g} px)",
            residual=True,
            truth=truth,
        )
        sep_fraction = self._draw_mask_pair(self.axes[0, 1], self.axes[0, 2], injected, sep, "SEP")
        mto_fraction = self._draw_mask_pair(self.axes[1, 1], self.axes[1, 2], injected, mto, "MTObjects")
        self.canvas.draw_idle()
        return sep_fraction, mto_fraction

    def save_png(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        name = self.label_to_name.get(self.galaxy_var.get(), "galaxy")
        path = self.output_dir / f"{display.safe_filename(name)}_SEP_MTObjects_toy_comparison.png"
        self.figure.savefig(path, dpi=160)
        self.status.set(f"Saved {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=display.DEFAULT_MANIFEST)
    parser.add_argument("--pc", choices=sorted(PC_RESEARCH_FOLDERS), default=detect_pc(FOREGROUND_ROOT))
    parser.add_argument("--sep-best", type=Path)
    parser.add_argument("--mto-best", type=Path)
    parser.add_argument("--mtobjects-root", type=Path)
    return parser.parse_args()


def main() -> int:
    CombinedToyTester(parse_args()).mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
