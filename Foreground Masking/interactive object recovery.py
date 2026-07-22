#!/usr/bin/env python3
"""Interactive synthetic-object recovery tester for foreground masking.

This tool starts from a user-selected baseline S4G galaxy, injects one toy
foreground/background object at a deprojected-image location, runs the current
Photutils foreground-mask code unchanged, and reports how well the injected
object is recovered.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sqlite3
import sys
import tkinter as tk
import time
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

import numpy as np
from astropy.io import fits
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

import foreground_mask_photutils as fgmask  # noqa: E402
import interactive_photutils_parameter_tester as baseline  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, erwin_folder, remove_foreground_folder  # noqa: E402


DEFAULT_MANIFEST = baseline.DEFAULT_MANIFEST
DEFAULT_PC = "Laptop"
DEFAULT_GALAXY = "NGC0986"
PNG_OUTPUT_DIR = remove_foreground_folder(DEFAULT_PC) / "interactive_object_recovery"
STARTUP_CACHE_PATH = SCRIPT_DIR / "startup_cache.sqlite3"
REDRAW_DEBOUNCE_MS = 450
CACHE_SCHEMA_VERSION = 1
IRAC_36_VEGA_ZERO_JY = 280.9
AB_ZERO_JY = 3631.0
OBJECT_TYPES = {
    "Gaussian star": "gaussian",
    "Star cluster": "cluster",
    "Compact galaxy": "galaxy",
}
OBJECT_DESCRIPTIONS = {
    "Gaussian star": (
        "Model: one circular 2D Gaussian point source. Characterised by centroid x,y; peak residual-sigma "
        "or integrated magnitude; and FWHM. It is radially symmetric, has no PA or axis ratio, and has no "
        "extended stellar wings."
    ),
    "Star cluster": (
        "Model: fixed blend of three compact circular Gaussian components. Characterised by one centroid x,y; "
        "peak residual-sigma or integrated magnitude; and component FWHM. Fixed offsets and relative peaks make "
        "it asymmetric and clumpy while still compact."
    ),
    "Compact galaxy": (
        "Model: one smooth elliptical Gaussian extended source. Characterised by centroid x,y; peak residual-sigma "
        "or integrated magnitude; major-axis FWHM; axis ratio; and object PA. It represents a flattened compact "
        "background galaxy."
    ),
}
METHOD_LABELS = {
    "Global": "global",
    "Spike-gated": "spike-gated",
}
BRIGHTNESS_MODES = {
    "Peak residual sigma": "sigma",
    "Integrated magnitude": "magnitude",
}


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def geometry_signature(geometry: dict[str, float]) -> str:
    rounded = {key: round(float(value), 8) for key, value in sorted(geometry.items())}
    return json.dumps(rounded, sort_keys=True, separators=(",", ":"))


def array_blob(values: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    np.save(buffer, np.asarray(values), allow_pickle=False)
    return buffer.getvalue()


def array_from_blob(blob: bytes) -> np.ndarray:
    return np.load(io.BytesIO(blob), allow_pickle=False)


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


def deprojected_to_observed_pixel(
    x_deproj_arcsec: float,
    y_deproj_arcsec: float,
    geometry: dict[str, float],
) -> tuple[float, float]:
    transform_xy = baseline.image_transform(
        geometry["disk_pa"],
        geometry["inclination"],
        geometry["bar_pa"],
    )
    observed_arcsec = np.linalg.inv(transform_xy) @ np.array([x_deproj_arcsec, y_deproj_arcsec])
    x_pix = geometry["xc"] - 1.0 + observed_arcsec[0] / geometry["pixel_scale"]
    y_pix = geometry["yc"] - 1.0 + observed_arcsec[1] / geometry["pixel_scale"]
    return float(x_pix), float(y_pix)


def observed_pixel_to_deprojected_arcsec(
    x_pix: np.ndarray,
    y_pix: np.ndarray,
    geometry: dict[str, float],
) -> tuple[np.ndarray, np.ndarray]:
    pixel_scale = geometry["pixel_scale"]
    observed = np.vstack(
        [
            pixel_scale * (x_pix.ravel() + 1.0 - geometry["xc"]),
            pixel_scale * (y_pix.ravel() + 1.0 - geometry["yc"]),
        ]
    )
    transform_xy = baseline.image_transform(
        geometry["disk_pa"],
        geometry["inclination"],
        geometry["bar_pa"],
    )
    deprojected = transform_xy @ observed
    return deprojected[0].reshape(x_pix.shape), deprojected[1].reshape(y_pix.shape)


def elliptical_radius(
    x: np.ndarray,
    y: np.ndarray,
    x0: float,
    y0: float,
    sigma_major: float,
    axis_ratio: float,
    pa_deg: float,
) -> np.ndarray:
    theta = math.radians(pa_deg)
    dx = x - x0
    dy = y - y0
    along_major = dx * math.cos(theta) + dy * math.sin(theta)
    along_minor = -dx * math.sin(theta) + dy * math.cos(theta)
    sigma_minor = max(0.2, sigma_major * axis_ratio)
    return np.hypot(along_major / sigma_major, along_minor / sigma_minor)


def make_gaussian(
    shape: tuple[int, int],
    x0: float,
    y0: float,
    peak: float,
    sigma_major: float,
    axis_ratio: float = 1.0,
    pa_deg: float = 0.0,
) -> np.ndarray:
    yy, xx = np.indices(shape, dtype=float)
    radius = elliptical_radius(xx, yy, x0, y0, sigma_major, axis_ratio, pa_deg)
    return peak * np.exp(-0.5 * radius * radius)


def make_toy_object(
    shape: tuple[int, int],
    x0: float,
    y0: float,
    *,
    object_type: str,
    peak: float,
    fwhm_pixels: float,
    axis_ratio: float,
    pa_deg: float,
) -> np.ndarray:
    sigma = max(0.2, fwhm_pixels / 2.3548)
    if object_type == "cluster":
        offsets = [(-0.55, -0.25, 0.75), (0.45, 0.18, 0.55), (0.05, 0.65, 0.38)]
        model = np.zeros(shape, dtype=float)
        for dx, dy, scale in offsets:
            model += make_gaussian(
                shape,
                x0 + dx * fwhm_pixels,
                y0 + dy * fwhm_pixels,
                peak * scale,
                sigma * (0.85 + 0.25 * scale),
            )
        return model
    if object_type == "galaxy":
        return make_gaussian(shape, x0, y0, peak, sigma, axis_ratio, pa_deg)
    return make_gaussian(shape, x0, y0, peak, sigma)


def truth_mask_from_model(model: np.ndarray, peak: float, dilation_radius_pixels: int) -> np.ndarray:
    threshold = max(peak * 0.08, np.nanmax(model) * 0.08)
    core = np.asarray(model > threshold, dtype=bool)
    return fgmask.dilate_mask(core, max(0, dilation_radius_pixels))


def magnitude_to_flux_jy(magnitude: float, zero_flux_jy: float) -> float:
    if zero_flux_jy <= 0 or not math.isfinite(zero_flux_jy):
        raise ValueError("Magnitude zero flux must be a positive finite value in Jy.")
    return float(zero_flux_jy * 10.0 ** (-0.4 * magnitude))


def pixel_area_sr(pixel_scale_arcsec: float) -> float:
    arcsec_to_radian = math.pi / (180.0 * 3600.0)
    return float((abs(pixel_scale_arcsec) * arcsec_to_radian) ** 2)


def model_integrated_flux_jy(
    model: np.ndarray,
    geometry: dict[str, float],
    header: fits.Header,
) -> float | None:
    bunit = str(header.get("BUNIT", "")).strip().upper().replace(" ", "")
    if bunit in {"MJY/SR", "MJY/STERADIAN", "MJY/SR."}:
        return float(np.nansum(model) * 1.0e6 * pixel_area_sr(geometry["pixel_scale"]))
    return None


def integrated_flux_to_data_peak(
    unit_peak_model: np.ndarray,
    target_magnitude: float,
    target_flux_jy: float,
    geometry: dict[str, float],
    header: fits.Header,
) -> float:
    unit_flux_jy = model_integrated_flux_jy(unit_peak_model, geometry, header)
    if unit_flux_jy is not None and unit_flux_jy > 0:
        return float(target_flux_jy / unit_flux_jy)
    zero_point_mag = header.get("MAGZP", header.get("MAGZERO", header.get("ZEROPOINT")))
    if zero_point_mag is not None:
        target_counts = 10.0 ** (0.4 * (float(zero_point_mag) - target_magnitude))
        unit_sum = float(np.nansum(unit_peak_model))
        if unit_sum > 0:
            return target_counts / unit_sum
    raise ValueError(
        "Magnitude injection needs BUNIT=MJy/sr or a count-based magnitude zero point in the FITS header."
    )


def data_model_to_integrated_magnitude(
    model: np.ndarray,
    zero_flux_jy: float,
    geometry: dict[str, float],
    header: fits.Header,
) -> float | None:
    flux_jy = model_integrated_flux_jy(model, geometry, header)
    if flux_jy is not None and flux_jy > 0 and zero_flux_jy > 0:
        return float(-2.5 * math.log10(flux_jy / zero_flux_jy))

    zero_point_mag = header.get("MAGZP", header.get("MAGZERO", header.get("ZEROPOINT")))
    if zero_point_mag is not None:
        total_counts = float(np.nansum(model))
        if total_counts > 0:
            return float(float(zero_point_mag) - 2.5 * math.log10(total_counts))
    return None


def deproject_for_display(
    data: np.ndarray,
    geometry: dict[str, float],
) -> tuple[np.ndarray, list[float], np.ndarray, np.ndarray]:
    radius_pix = baseline.profile_radius_pixels(data, geometry)
    radius_arcsec = radius_pix * geometry["pixel_scale"]
    deprojected, x_axis, y_axis, _ = baseline.deproject_bar_aligned_cutout(data, geometry, radius_arcsec)
    extent = [float(x_axis[0]), float(x_axis[-1]), float(y_axis[0]), float(y_axis[-1])]
    return deprojected, extent, x_axis, y_axis


def investigated_region_mask(data: np.ndarray, geometry: dict[str, float]) -> np.ndarray:
    radius_pix = baseline.profile_radius_pixels(data, geometry)
    yy, xx = np.indices(data.shape, dtype=float)
    x_arcsec, y_arcsec = observed_pixel_to_deprojected_arcsec(xx, yy, geometry)
    radius_arcsec = radius_pix * geometry["pixel_scale"]
    return (
        np.isfinite(data)
        & (np.abs(x_arcsec) <= radius_arcsec)
        & (np.abs(y_arcsec) <= radius_arcsec)
    )


def bar_sma_deprojected_arcsec(geometry: dict[str, float]) -> float:
    factor = baseline.angles.deprojectr(
        geometry["bar_pa"] - geometry["disk_pa"],
        geometry["inclination"],
        1.0,
    )
    return float(abs(factor * geometry["bar_sma"]))


def draw_bar_aligned_guides(
    ax,
    geometry: dict[str, float],
    extent: list[float],
    *,
    profile_width_pixels: int | None = None,
) -> None:
    bar_sma_deproj = bar_sma_deprojected_arcsec(geometry)
    line_radius = min(
        0.82 * max(abs(extent[0]), abs(extent[1]), abs(extent[2]), abs(extent[3])),
        max(1.5 * bar_sma_deproj, bar_sma_deproj + 15.0),
    )
    ax.axhline(0, color="#1f77b4", linewidth=1.5, alpha=0.95, zorder=4)
    if profile_width_pixels is not None and profile_width_pixels > 0:
        half_width_arcsec = 0.5 * int(profile_width_pixels) * geometry["pixel_scale"]
        ax.axhline(
            half_width_arcsec,
            color="#1f77b4",
            linestyle="--",
            linewidth=1.0,
            alpha=0.9,
            zorder=4,
        )
        ax.axhline(
            -half_width_arcsec,
            color="#1f77b4",
            linestyle="--",
            linewidth=1.0,
            alpha=0.9,
            zorder=4,
        )
    ax.axvline(0, color="#d62728", linestyle="--", linewidth=1.2, alpha=0.9, zorder=4)
    ax.plot(
        [-bar_sma_deproj, bar_sma_deproj],
        [0, 0],
        "o",
        color="#1f77b4",
        ms=4.0,
        alpha=0.8,
        zorder=5,
    )
    ax.annotate(
        "",
        xy=(0.72 * line_radius, 0),
        xytext=(0.18 * line_radius, 0),
        arrowprops={
            "arrowstyle": "-|>",
            "color": "#1f77b4",
            "linewidth": 1.7,
            "mutation_scale": 13,
            "shrinkA": 0,
            "shrinkB": 0,
        },
        zorder=6,
    )
    label_kwargs = {
        "fontsize": 9,
        "fontweight": "bold",
        "color": "#1f77b4",
        "ha": "center",
        "va": "center",
        "bbox": {"boxstyle": "round,pad=0.12", "facecolor": "white", "edgecolor": "none", "alpha": 0.78},
        "zorder": 7,
    }
    x_label_radius = min(100.0, 0.92 * max(abs(extent[0]), abs(extent[1])))
    ax.text(x_label_radius, 0, "+r", **label_kwargs)
    ax.text(-x_label_radius, 0, "-r", **label_kwargs)


class ObjectRecoveryApp(tk.Tk):
    def __init__(self, manifest: Path, pc_name: str):
        super().__init__()
        self.title("Interactive Object Recovery")
        self.geometry("1720x1160")
        self.minsize(1380, 900)

        self.manifest = manifest
        self.pc_var = tk.StringVar(value=pc_name)
        self.galaxy_var = tk.StringVar()
        self.method_var = tk.StringVar(value="Spike-gated")
        self.object_type_var = tk.StringVar(value="Gaussian star")
        self.object_description_var = tk.StringVar(value=OBJECT_DESCRIPTIONS["Gaussian star"])
        self.status = tk.StringVar(value="Loading manifest...")
        self.after_id: str | None = None
        self.data_cache: dict[str, tuple[np.ndarray, dict[str, float], fits.Header]] = {}
        self.baseline_products_cache: dict[tuple[str, tuple[tuple[str, object], ...]], dict[str, object]] = {}
        self.display_cache: dict[str, dict[str, object]] = {}
        self.startup_cache_path = STARTUP_CACHE_PATH

        self.all_rows = read_manifest(manifest)
        self.rows: list[dict[str, str]] = []
        self.rows_by_name: dict[str, dict[str, str]] = {}

        self.brightness_mode_var = tk.StringVar(value="Integrated magnitude")
        self.implied_mag_var = tk.StringVar(value="calculate to update")
        self.x_deproj = tk.DoubleVar(value=75.0)
        self.y_deproj = tk.DoubleVar(value=0.0)
        self.peak_sigma = tk.DoubleVar(value=30.0)
        self.integrated_mag = tk.DoubleVar(value=14.0)
        self.zero_flux_jy = tk.DoubleVar(value=IRAC_36_VEGA_ZERO_JY)
        self.fwhm_arcsec = tk.DoubleVar(value=4.0)
        self.axis_ratio = tk.DoubleVar(value=0.65)
        self.object_pa = tk.DoubleVar(value=25.0)
        self.truth_dilation = tk.IntVar(value=2)
        self.toy_parameter_rows: dict[str, tuple[ttk.Widget, ttk.Widget]] = {}

        defaults = baseline.METHOD_DEFAULTS["spike-gated"]
        self.smooth_sigma = tk.DoubleVar(value=float(defaults["smooth_sigma_pixels"]))
        self.detection_nsigma = tk.DoubleVar(value=float(defaults["detection_nsigma"]))
        self.npixels = tk.IntVar(value=int(defaults["npixels"]))
        self.dilation_radius = tk.IntVar(value=int(defaults["dilation_radius_pixels"]))
        self.max_area = tk.IntVar(value=int(defaults["max_area"]))
        self.max_elongation = tk.DoubleVar(value=float(defaults["max_elongation"]))
        self.exclude_center = tk.DoubleVar(value=float(defaults["exclude_center_radius_pixels"]))

        self._build_ui()
        self.refresh_galaxy_list(initial=True)

    def ensure_startup_cache(self) -> None:
        self.startup_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.startup_cache_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS display_products (
                    schema_version INTEGER NOT NULL,
                    pc_name TEXT NOT NULL,
                    galaxy_name TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    image_mtime_ns INTEGER NOT NULL,
                    image_size INTEGER NOT NULL,
                    geometry_signature TEXT NOT NULL,
                    deproj BLOB NOT NULL,
                    extent BLOB NOT NULL,
                    x_axis BLOB NOT NULL,
                    y_axis BLOB NOT NULL,
                    log_deproj BLOB NOT NULL,
                    levels BLOB NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (
                        schema_version,
                        pc_name,
                        galaxy_name,
                        image_path,
                        image_mtime_ns,
                        image_size,
                        geometry_signature
                    )
                )
                """
            )

    def cache_lookup_metadata(self, name: str, geometry: dict[str, float]) -> tuple[Path, int, int, str]:
        row = self.rows_by_name[name]
        image_path = baseline.image_path_for_pc(row, self.pc_var.get())
        stat = image_path.stat()
        return image_path, int(stat.st_mtime_ns), int(stat.st_size), geometry_signature(geometry)

    def load_display_products_from_startup_cache(
        self,
        name: str,
        geometry: dict[str, float],
    ) -> dict[str, object] | None:
        try:
            image_path, image_mtime_ns, image_size, signature = self.cache_lookup_metadata(name, geometry)
            self.ensure_startup_cache()
            with sqlite3.connect(self.startup_cache_path) as connection:
                row = connection.execute(
                    """
                    SELECT deproj, extent, x_axis, y_axis, log_deproj, levels
                    FROM display_products
                    WHERE schema_version = ?
                      AND pc_name = ?
                      AND galaxy_name = ?
                      AND image_path = ?
                      AND image_mtime_ns = ?
                      AND image_size = ?
                      AND geometry_signature = ?
                    """,
                    (
                        CACHE_SCHEMA_VERSION,
                        self.pc_var.get(),
                        name,
                        str(image_path),
                        image_mtime_ns,
                        image_size,
                        signature,
                    ),
                ).fetchone()
            if row is None:
                return None
            products = {
                "deproj": array_from_blob(row[0]),
                "extent": array_from_blob(row[1]).tolist(),
                "x_axis": array_from_blob(row[2]),
                "y_axis": array_from_blob(row[3]),
                "log_deproj": array_from_blob(row[4]),
                "levels": array_from_blob(row[5]),
            }
            self.display_cache[name] = products
            return products
        except Exception:
            return None

    def save_display_products_to_startup_cache(
        self,
        name: str,
        geometry: dict[str, float],
        products: dict[str, object],
    ) -> None:
        try:
            image_path, image_mtime_ns, image_size, signature = self.cache_lookup_metadata(name, geometry)
            self.ensure_startup_cache()
            with sqlite3.connect(self.startup_cache_path) as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO display_products (
                        schema_version,
                        pc_name,
                        galaxy_name,
                        image_path,
                        image_mtime_ns,
                        image_size,
                        geometry_signature,
                        deproj,
                        extent,
                        x_axis,
                        y_axis,
                        log_deproj,
                        levels,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        CACHE_SCHEMA_VERSION,
                        self.pc_var.get(),
                        name,
                        str(image_path),
                        image_mtime_ns,
                        image_size,
                        signature,
                        array_blob(np.asarray(products["deproj"], dtype=float)),
                        array_blob(np.asarray(products["extent"], dtype=float)),
                        array_blob(np.asarray(products["x_axis"], dtype=float)),
                        array_blob(np.asarray(products["y_axis"], dtype=float)),
                        array_blob(np.asarray(products["log_deproj"], dtype=float)),
                        array_blob(np.asarray(products["levels"], dtype=float)),
                        time.time(),
                    ),
                )
        except Exception:
            return

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=8)
        root.pack(fill=tk.BOTH, expand=True)

        controls = ttk.Frame(root)
        controls.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        plot_frame = ttk.Frame(root)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_controls(controls)

        self.figure = Figure(figsize=(11.8, 8.6), dpi=100, constrained_layout=True)
        self.ax_baseline = self.figure.add_subplot(2, 2, 1)
        self.ax_injected = self.figure.add_subplot(2, 2, 2)
        self.ax_recovery = self.figure.add_subplot(2, 2, 3)
        self.ax_profile = self.figure.add_subplot(2, 2, 4)

        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.canvas.mpl_connect("button_press_event", self.on_plot_click)
        toolbar = NavigationToolbar2Tk(self.canvas, plot_frame, pack_toolbar=False)
        toolbar.update()
        toolbar.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Label(plot_frame, textvariable=self.status, justify=tk.LEFT).pack(side=tk.BOTTOM, fill=tk.X, pady=(4, 0))

    def _build_controls(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(parent, text="Baseline galaxy", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 4)
        )
        row += 1

        ttk.Label(parent, text="PC").grid(row=row, column=0, sticky=tk.W)
        self.pc_combo = ttk.Combobox(
            parent,
            textvariable=self.pc_var,
            values=sorted(PC_RESEARCH_FOLDERS),
            state="readonly",
            width=18,
        )
        self.pc_combo.grid(row=row, column=1, sticky=tk.EW)
        self.pc_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_galaxy_list())
        row += 1

        ttk.Label(parent, text="Galaxy").grid(row=row, column=0, sticky=tk.W)
        self.galaxy_combo = ttk.Combobox(parent, textvariable=self.galaxy_var, state="readonly", width=22)
        self.galaxy_combo.grid(row=row, column=1, sticky=tk.EW)
        self.galaxy_combo.bind("<<ComboboxSelected>>", lambda _event: self.draw_preview())
        row += 1

        self.calculate_button = ttk.Button(parent, text="Calculate", command=self.redraw_now)
        self.calculate_button.grid(row=row, column=0, sticky=tk.EW, pady=(5, 10))
        ttk.Button(parent, text="Open PNG Folder", command=self.open_png_folder).grid(
            row=row, column=1, sticky=tk.EW, pady=(5, 10)
        )
        row += 1

        ttk.Separator(parent).grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=5)
        row += 1

        ttk.Label(parent, text="Toy object", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(4, 4)
        )
        row += 1
        ttk.Label(parent, text="Type").grid(row=row, column=0, sticky=tk.W)
        type_combo = ttk.Combobox(
            parent,
            textvariable=self.object_type_var,
            values=list(OBJECT_TYPES),
            state="readonly",
            width=22,
        )
        type_combo.grid(row=row, column=1, sticky=tk.EW)
        type_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_toy_settings_changed())
        row += 1

        ttk.Label(
            parent,
            textvariable=self.object_description_var,
            foreground="#5A5A5A",
            wraplength=270,
            justify=tk.LEFT,
        ).grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=(0, 5))
        row += 1

        ttk.Label(parent, text="Brightness").grid(row=row, column=0, sticky=tk.W)
        brightness_combo = ttk.Combobox(
            parent,
            textvariable=self.brightness_mode_var,
            values=list(BRIGHTNESS_MODES),
            state="readonly",
            width=22,
        )
        brightness_combo.grid(row=row, column=1, sticky=tk.EW)
        brightness_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_toy_settings_changed())
        row += 1

        implied_mag_label = ttk.Label(parent, text="implied integrated mag")
        implied_mag_label.grid(row=row, column=0, sticky=tk.W)
        implied_mag_value = ttk.Label(parent, textvariable=self.implied_mag_var, foreground="#5A5A5A")
        implied_mag_value.grid(row=row, column=1, sticky=tk.EW)
        self.toy_parameter_rows["implied_mag"] = (implied_mag_label, implied_mag_value)
        row += 1

        for key, label, var, low, high, step in [
            ("x_deproj", "x deproj [arcsec]", self.x_deproj, -250.0, 250.0, 0.5),
            ("y_deproj", "y deproj [arcsec]", self.y_deproj, -250.0, 250.0, 0.5),
            ("peak_sigma", "peak [resid sigma]", self.peak_sigma, 1.0, 80.0, 0.5),
            ("integrated_mag", "integrated mag", self.integrated_mag, 5.0, 25.0, 0.1),
            ("zero_flux_jy", "zero flux [Jy]", self.zero_flux_jy, 1.0, 5000.0, 1.0),
            ("fwhm_arcsec", "FWHM [arcsec]", self.fwhm_arcsec, 0.3, 12.0, 0.1),
            ("axis_ratio", "axis ratio", self.axis_ratio, 0.15, 1.0, 0.05),
            ("object_pa", "object PA [deg]", self.object_pa, -180.0, 180.0, 1.0),
        ]:
            label_widget = ttk.Label(parent, text=label)
            label_widget.grid(row=row, column=0, sticky=tk.W)
            spin = ttk.Spinbox(parent, textvariable=var, from_=low, to=high, increment=step, width=10)
            spin.grid(row=row, column=1, sticky=tk.EW)
            spin.bind("<Return>", lambda _event: self.on_toy_numeric_changed())
            spin.bind("<FocusOut>", lambda _event: self.on_toy_numeric_changed())
            self.toy_parameter_rows[key] = (label_widget, spin)
            row += 1

        ttk.Label(parent, text="truth dilation [px]").grid(row=row, column=0, sticky=tk.W)
        truth_spin = ttk.Spinbox(parent, textvariable=self.truth_dilation, from_=0, to=20, increment=1, width=10)
        truth_spin.grid(row=row, column=1, sticky=tk.EW)
        truth_spin.bind("<Return>", lambda _event: self.on_toy_numeric_changed())
        truth_spin.bind("<FocusOut>", lambda _event: self.on_toy_numeric_changed())
        row += 1

        ttk.Label(parent, text="Click either image panel to set the deprojected x,y location.", wraplength=270).grid(
            row=row, column=0, columnspan=2, sticky=tk.EW, pady=(4, 10)
        )
        row += 1
        self.refresh_toy_parameter_visibility()

        ttk.Separator(parent).grid(row=row, column=0, columnspan=2, sticky=tk.EW, pady=5)
        row += 1

        ttk.Label(parent, text="Mask baseline", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(4, 4)
        )
        row += 1
        ttk.Label(parent, text="Method").grid(row=row, column=0, sticky=tk.W)
        method_combo = ttk.Combobox(
            parent,
            textvariable=self.method_var,
            values=list(METHOD_LABELS),
            state="readonly",
            width=18,
        )
        method_combo.grid(row=row, column=1, sticky=tk.EW)
        method_combo.bind("<<ComboboxSelected>>", lambda _event: self.apply_method_defaults())
        row += 1

        for label, var, low, high, step in [
            ("smooth sigma [px]", self.smooth_sigma, 1.0, 60.0, 1.0),
            ("detect nsigma", self.detection_nsigma, 1.0, 15.0, 0.1),
            ("npixels", self.npixels, 1, 80, 1),
            ("dilation [px]", self.dilation_radius, 0, 20, 1),
            ("max area [px]", self.max_area, 5, 4000, 5),
            ("max elongation", self.max_elongation, 1.0, 30.0, 0.2),
            ("central exclusion [px]", self.exclude_center, 0.0, 200.0, 1.0),
        ]:
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W)
            spin = ttk.Spinbox(parent, textvariable=var, from_=low, to=high, increment=step, width=10)
            spin.grid(row=row, column=1, sticky=tk.EW)
            spin.bind("<Return>", lambda _event: self.mark_pending())
            spin.bind("<FocusOut>", lambda _event: self.mark_pending())
            row += 1

    def on_toy_settings_changed(self) -> None:
        self.refresh_toy_parameter_visibility()
        self.implied_mag_var.set("calculate to update")
        self.mark_pending()

    def on_toy_numeric_changed(self) -> None:
        self.implied_mag_var.set("calculate to update")
        self.mark_pending()

    def refresh_toy_parameter_visibility(self) -> None:
        object_type = OBJECT_TYPES.get(self.object_type_var.get(), "gaussian")
        brightness_mode = BRIGHTNESS_MODES.get(self.brightness_mode_var.get(), "sigma")
        self.object_description_var.set(
            OBJECT_DESCRIPTIONS.get(self.object_type_var.get(), OBJECT_DESCRIPTIONS["Gaussian star"])
        )
        visible_keys = {
            "x_deproj",
            "y_deproj",
            "fwhm_arcsec",
        }
        if brightness_mode == "magnitude":
            visible_keys.update({"integrated_mag", "zero_flux_jy"})
        else:
            visible_keys.update({"peak_sigma", "implied_mag"})
        if object_type == "galaxy":
            visible_keys.update({"axis_ratio", "object_pa"})

        for key, widgets in self.toy_parameter_rows.items():
            for widget in widgets:
                if key in visible_keys:
                    widget.grid()
                else:
                    widget.grid_remove()

    def refresh_galaxy_list(self, initial: bool = False) -> None:
        pc_name = self.pc_var.get()
        self.startup_cache_path = STARTUP_CACHE_PATH
        self.rows = baseline.rows_with_images_for_pc(self.all_rows, pc_name)
        self.rows_by_name = {row["name"]: row for row in self.rows}
        self.data_cache.clear()
        self.baseline_products_cache.clear()
        self.display_cache.clear()
        names = [row["name"] for row in self.rows]
        self.galaxy_combo.configure(values=names)
        if not names:
            self.galaxy_var.set("")
            self.status.set(f"No FITS images found in {erwin_folder(pc_name) / 's4g_images_36um'}")
            return
        current = self.galaxy_var.get()
        if current in self.rows_by_name:
            selected = current
        elif initial and DEFAULT_GALAXY in self.rows_by_name:
            selected = DEFAULT_GALAXY
        else:
            selected = names[0]
        self.galaxy_var.set(selected)
        self.draw_preview()

    def apply_method_defaults(self) -> None:
        method = METHOD_LABELS.get(self.method_var.get(), "global")
        defaults = baseline.METHOD_DEFAULTS[method]
        self.smooth_sigma.set(float(defaults["smooth_sigma_pixels"]))
        self.detection_nsigma.set(float(defaults["detection_nsigma"]))
        self.npixels.set(int(defaults["npixels"]))
        self.dilation_radius.set(int(defaults["dilation_radius_pixels"]))
        self.max_area.set(int(defaults["max_area"]))
        self.max_elongation.set(float(defaults["max_elongation"]))
        self.exclude_center.set(float(defaults["exclude_center_radius_pixels"]))
        self.mark_pending("Mask defaults updated. Press Calculate to run recovery.")

    def mark_pending(self, message: str | None = None) -> None:
        if message is None:
            message = "Settings changed. Press Calculate to run recovery."
        self.status.set(message)

    def draw_preview(self) -> None:
        name = self.galaxy_var.get()
        if not name:
            return
        try:
            row = self.rows_by_name[name]
            geometry = baseline.required_geometry(row)
            if geometry is None:
                raise ValueError(f"{name} has incomplete geometry in {self.manifest}.")
            display = self.load_display_products_from_startup_cache(name, geometry)
            loaded_from_cache = display is not None
            if display is None:
                data, geometry, _header = self.load_galaxy(name)
                display = self.display_products(name, data, geometry)
            params = self.current_mask_params()
            profile_width = max(1, int(params["profile_width"]))
            extent = display["extent"]
            log_deproj = np.asarray(display["log_deproj"], dtype=float)
            levels = np.asarray(display["levels"], dtype=float)
            for ax in (self.ax_baseline, self.ax_injected, self.ax_recovery, self.ax_profile):
                ax.clear()
            self.ax_baseline.imshow(
                log_deproj,
                origin="lower",
                extent=extent,
                cmap="Greys",
                vmin=levels[0],
                vmax=levels[-1],
            )
            self.ax_baseline.contour(
                np.linspace(extent[0], extent[1], log_deproj.shape[1]),
                np.linspace(extent[2], extent[3], log_deproj.shape[0]),
                log_deproj,
                levels=levels,
                colors="0.25",
                linewidths=0.42,
            )
            draw_bar_aligned_guides(
                self.ax_baseline,
                geometry,
                extent,
                profile_width_pixels=profile_width,
            )
            self.ax_baseline.plot(
                float(self.x_deproj.get()),
                float(self.y_deproj.get()),
                "x",
                color="#d62728",
                ms=8,
                mew=1.8,
            )
            self.ax_baseline.set_title(f"{name} baseline | deprojected, bar-aligned", loc="left")
            self.ax_injected.text(0.5, 0.5, "Press Calculate", ha="center", va="center", transform=self.ax_injected.transAxes)
            self.ax_recovery.text(0.5, 0.5, "Recovery results appear here", ha="center", va="center", transform=self.ax_recovery.transAxes)
            self.ax_profile.text(0.5, 0.5, "Profile comparison appears here", ha="center", va="center", transform=self.ax_profile.transAxes)
            for ax in (self.ax_baseline, self.ax_injected, self.ax_recovery):
                ax.set_xlim(extent[0], extent[1])
                ax.set_ylim(extent[2], extent[3])
                ax.set_aspect("equal", adjustable="box")
                ax.set_xlabel("deprojected bar-axis x [arcsec]")
                ax.set_ylabel("deprojected y [arcsec]")
                ax.grid(True, alpha=0.15)
            self.canvas.draw_idle()
            cache_text = "cached baseline preview loaded" if loaded_from_cache else "baseline preview loaded and cached"
            self.status.set(
                f"{self.pc_var.get()} | {name}: {cache_text}. "
                "Choose settings and press Calculate to run recovery."
            )
        except Exception as exc:  # noqa: BLE001
            self.status.set(f"Preview error: {exc}")
            messagebox.showerror("Could not draw preview", str(exc))

    def current_mask_params(self) -> dict[str, float | int | bool | str]:
        method = METHOD_LABELS.get(self.method_var.get(), "global")
        defaults = dict(baseline.METHOD_DEFAULTS[method])
        defaults.update(
            {
                "smooth_sigma_pixels": float(self.smooth_sigma.get()),
                "detection_nsigma": float(self.detection_nsigma.get()),
                "npixels": int(self.npixels.get()),
                "dilation_radius_pixels": int(self.dilation_radius.get()),
                "max_area": int(self.max_area.get()),
                "max_elongation": float(self.max_elongation.get()),
                "exclude_center_radius_pixels": float(self.exclude_center.get()),
                "masking_method": method,
            }
        )
        return defaults

    def mask_params_cache_key(self, params: dict[str, float | int | bool | str]) -> tuple[tuple[str, object], ...]:
        return tuple(sorted(params.items()))

    def load_galaxy(self, name: str) -> tuple[np.ndarray, dict[str, float], fits.Header]:
        if name in self.data_cache:
            return self.data_cache[name]
        row = self.rows_by_name[name]
        geometry = baseline.required_geometry(row)
        if geometry is None:
            raise ValueError(f"{name} has incomplete geometry in {self.manifest}.")
        with fits.open(baseline.image_path_for_pc(row, self.pc_var.get())) as hdul:
            data = np.squeeze(np.asarray(hdul[0].data, dtype=float))
            header = hdul[0].header.copy()
        if data.ndim != 2:
            raise ValueError(f"{name} image is not 2D after squeezing: {data.shape}")
        self.data_cache[name] = (data, geometry, header)
        return data, geometry, header

    def baseline_products(
        self,
        name: str,
        data: np.ndarray,
        geometry: dict[str, float],
        params: dict[str, float | int | bool | str],
    ) -> dict[str, object]:
        key = (name, self.mask_params_cache_key(params))
        cached = self.baseline_products_cache.get(key)
        if cached is not None:
            return cached

        smooth = fgmask.make_smooth_galaxy_model(data, float(params["smooth_sigma_pixels"]))
        sigma = robust_sigma(fgmask.make_residual_image(data, smooth))
        baseline_mask, _, _, _ = baseline.mask_products(data, geometry, params)
        radius_pix = baseline.profile_radius_pixels(data, geometry)
        profile_width = max(1, int(params["profile_width"]))
        radii, clean_profile = baseline.profile_at_pa(
            data, geometry["xc"], geometry["yc"], geometry["bar_pa"], radius_pix, width=profile_width
        )
        radii_deproj = baseline.deprojected_profile_radius(
            geometry["bar_pa"],
            geometry["disk_pa"],
            geometry["inclination"],
            radii * geometry["pixel_scale"],
        )
        products = {
            "sigma": sigma,
            "baseline_mask": baseline_mask,
            "radius_pix": radius_pix,
            "profile_width": profile_width,
            "radii": radii,
            "clean_profile": clean_profile,
            "radii_deproj": radii_deproj,
        }
        self.baseline_products_cache[key] = products
        return products

    def display_products(self, name: str, data: np.ndarray, geometry: dict[str, float]) -> dict[str, object]:
        cached = self.display_cache.get(name)
        if cached is not None:
            return cached
        deproj, extent, x_axis, y_axis = deproject_for_display(data, geometry)
        log_deproj, levels = baseline.robust_log_image(deproj)
        products = {
            "deproj": deproj,
            "extent": extent,
            "x_axis": x_axis,
            "y_axis": y_axis,
            "log_deproj": log_deproj,
            "levels": levels,
        }
        self.display_cache[name] = products
        self.save_display_products_to_startup_cache(name, geometry, products)
        return products

    def schedule_redraw(self) -> None:
        self.mark_pending()

    def redraw_now(self) -> None:
        if self.after_id is not None:
            self.after_cancel(self.after_id)
            self.after_id = None
        self.redraw()

    def mark_display_stale_during_calculation(self) -> None:
        for ax in (self.ax_baseline, self.ax_injected, self.ax_recovery, self.ax_profile):
            ax.add_patch(
                Rectangle(
                    (0, 0),
                    1,
                    1,
                    transform=ax.transAxes,
                    facecolor="0.82",
                    edgecolor="none",
                    alpha=0.48,
                    zorder=1000,
                )
            )
            ax.text(
                0.03,
                0.97,
                "Calculating...",
                transform=ax.transAxes,
                ha="left",
                va="top",
                fontsize=14,
                fontweight="bold",
                color="0.15",
                bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "0.55", "alpha": 0.82},
                zorder=1001,
            )
        self.canvas.draw()
        self.canvas.flush_events()

    def redraw(self) -> None:
        self.after_id = None
        name = self.galaxy_var.get()
        if not name:
            return
        try:
            self.status.set(f"Calculating injection recovery for {name}...")
            self.calculate_button.configure(state=tk.DISABLED)
            self.mark_display_stale_during_calculation()
            self.update_idletasks()
            start_time = time.perf_counter()
            data, geometry, header = self.load_galaxy(name)
            result = self.calculate_recovery(name, data, geometry, header)
            self.draw_result(name, data, geometry, result)
            self.update_implied_mag_display(result)
            result["elapsed_seconds"] = time.perf_counter() - start_time
            saved_path = self.save_png()
            self.status.set(f"{self.format_status(name, result)}\nSaved PNG: {saved_path}")
        except Exception as exc:  # noqa: BLE001
            self.status.set(f"Error: {exc}")
            messagebox.showerror("Object recovery failed", str(exc))
        finally:
            self.calculate_button.configure(state=tk.NORMAL)

    def calculate_recovery(
        self,
        name: str,
        data: np.ndarray,
        geometry: dict[str, float],
        header: fits.Header,
    ) -> dict[str, object]:
        params = self.current_mask_params()
        x0, y0 = deprojected_to_observed_pixel(float(self.x_deproj.get()), float(self.y_deproj.get()), geometry)
        baseline_products = self.baseline_products(name, data, geometry, params)
        sigma = float(baseline_products["sigma"])
        fwhm_pixels = max(0.2, float(self.fwhm_arcsec.get()) / geometry["pixel_scale"])
        object_type = OBJECT_TYPES.get(self.object_type_var.get(), "gaussian")
        unit_peak_model = make_toy_object(
            data.shape,
            x0,
            y0,
            object_type=object_type,
            peak=1.0,
            fwhm_pixels=fwhm_pixels,
            axis_ratio=float(self.axis_ratio.get()),
            pa_deg=float(self.object_pa.get()),
        )
        target_flux_jy: float | None = None
        if BRIGHTNESS_MODES.get(self.brightness_mode_var.get(), "sigma") == "magnitude":
            target_magnitude = float(self.integrated_mag.get())
            target_flux_jy = magnitude_to_flux_jy(target_magnitude, float(self.zero_flux_jy.get()))
            peak = integrated_flux_to_data_peak(
                unit_peak_model,
                target_magnitude,
                target_flux_jy,
                geometry,
                header,
            )
        else:
            target_magnitude = None
            peak = float(self.peak_sigma.get()) * sigma
        model = make_toy_object(
            data.shape,
            x0,
            y0,
            object_type=object_type,
            peak=peak,
            fwhm_pixels=fwhm_pixels,
            axis_ratio=float(self.axis_ratio.get()),
            pa_deg=float(self.object_pa.get()),
        )
        implied_integrated_mag = data_model_to_integrated_magnitude(
            model,
            float(self.zero_flux_jy.get()),
            geometry,
            header,
        )
        truth = truth_mask_from_model(model, peak, int(self.truth_dilation.get()))
        analysis_region = investigated_region_mask(data, geometry)
        ix = int(round(x0))
        iy = int(round(y0))
        if ix < 0 or ix >= data.shape[1] or iy < 0 or iy >= data.shape[0] or not analysis_region[iy, ix]:
            raise ValueError("Toy-object centre is outside the investigated bar-aligned galaxy area.")
        if np.any(truth & ~analysis_region):
            raise ValueError("Toy-object truth mask extends outside the investigated bar-aligned galaxy area.")
        injected = data + model

        baseline_mask = np.asarray(baseline_products["baseline_mask"], dtype=bool)
        recovered_mask, kept_rows, residual, spike_samples = baseline.mask_products(injected, geometry, params)
        incremental_mask = recovered_mask & ~baseline_mask

        truth_pixels = int(np.count_nonzero(truth))
        overlap_pixels = int(np.count_nonzero(recovered_mask & truth))
        incremental_overlap = int(np.count_nonzero(incremental_mask & truth))
        incremental_pixels = int(np.count_nonzero(incremental_mask))
        recall = overlap_pixels / truth_pixels if truth_pixels else 0.0
        incremental_recall = incremental_overlap / truth_pixels if truth_pixels else 0.0
        incremental_precision = incremental_overlap / incremental_pixels if incremental_pixels else 0.0

        radius_pix = int(baseline_products["radius_pix"])
        profile_width = int(baseline_products["profile_width"])
        clean_profile = np.asarray(baseline_products["clean_profile"], dtype=float)
        _, injected_profile = baseline.profile_at_pa(
            injected, geometry["xc"], geometry["yc"], geometry["bar_pa"], radius_pix, width=profile_width
        )
        recovered_profile_mask = baseline.profile_mask_at_pa(
            recovered_mask, geometry["xc"], geometry["yc"], geometry["bar_pa"], radius_pix, width=profile_width
        )
        bridge_mask = recovered_profile_mask
        masked_profile = np.array(injected_profile, copy=True)
        masked_profile[bridge_mask] = np.nan
        bridged_profile, bridged_samples = baseline.fill_profile_with_log_linear_bridges(
            masked_profile,
            bridge_mask,
        )
        radii_deproj = np.asarray(baseline_products["radii_deproj"], dtype=float)
        valid_profile = np.isfinite(clean_profile) & np.isfinite(bridged_profile) & (clean_profile > 0)
        profile_fraction_error = np.full_like(clean_profile, np.nan, dtype=float)
        profile_fraction_error[valid_profile] = (bridged_profile[valid_profile] - clean_profile[valid_profile]) / clean_profile[
            valid_profile
        ]
        profile_abs_error = float(np.nanmedian(np.abs(profile_fraction_error[valid_profile]))) if np.any(valid_profile) else np.nan

        return {
            "params": params,
            "model": model,
            "truth": truth,
            "injected": injected,
            "baseline_mask": baseline_mask,
            "recovered_mask": recovered_mask,
            "incremental_mask": incremental_mask,
            "kept_rows": kept_rows,
            "residual": residual,
            "spike_samples": spike_samples,
            "x0": x0,
            "y0": y0,
            "peak": peak,
            "sigma": sigma,
            "object_type_label": self.object_type_var.get(),
            "fwhm_arcsec": float(self.fwhm_arcsec.get()),
            "peak_sigma": float(self.peak_sigma.get()),
            "axis_ratio": float(self.axis_ratio.get()),
            "object_pa": float(self.object_pa.get()),
            "truth_dilation": int(self.truth_dilation.get()),
            "brightness_mode": BRIGHTNESS_MODES.get(self.brightness_mode_var.get(), "sigma"),
            "target_magnitude": target_magnitude,
            "target_flux_jy": target_flux_jy,
            "implied_integrated_mag": implied_integrated_mag,
            "zero_flux_jy": float(self.zero_flux_jy.get()),
            "bunit": str(header.get("BUNIT", "")),
            "truth_pixels": truth_pixels,
            "overlap_pixels": overlap_pixels,
            "incremental_pixels": incremental_pixels,
            "recall": recall,
            "incremental_recall": incremental_recall,
            "incremental_precision": incremental_precision,
            "radii_deproj": radii_deproj,
            "clean_profile": clean_profile,
            "injected_profile": injected_profile,
            "masked_profile": masked_profile,
            "bridged_profile": bridged_profile,
            "bridged_samples": bridged_samples,
            "profile_abs_error": profile_abs_error,
        }

    def draw_result(
        self,
        name: str,
        data: np.ndarray,
        geometry: dict[str, float],
        result: dict[str, object],
    ) -> None:
        for ax in (self.ax_baseline, self.ax_injected, self.ax_recovery, self.ax_profile):
            ax.clear()

        injected = np.asarray(result["injected"], dtype=float)
        truth = np.asarray(result["truth"], dtype=bool)
        recovered = np.asarray(result["recovered_mask"], dtype=bool)
        incremental = np.asarray(result["incremental_mask"], dtype=bool)
        params = result["params"]
        profile_width = max(1, int(params["profile_width"])) if isinstance(params, dict) else None

        display = self.display_products(name, data, geometry)
        extent = display["extent"]
        log_base = np.asarray(display["log_deproj"], dtype=float)
        levels = np.asarray(display["levels"], dtype=float)
        inj_deproj, _, _, _ = deproject_for_display(injected, geometry)
        truth_deproj, _, _, _ = deproject_for_display(truth.astype(float), geometry)
        recovered_deproj, _, _, _ = deproject_for_display(recovered.astype(float), geometry)
        incremental_deproj, _, _, _ = deproject_for_display(incremental.astype(float), geometry)

        log_inj, _ = baseline.robust_log_image(inj_deproj)

        self.ax_baseline.imshow(log_base, origin="lower", extent=extent, cmap="Greys", vmin=levels[0], vmax=levels[-1])
        self.ax_baseline.contour(
            np.linspace(extent[0], extent[1], log_base.shape[1]),
            np.linspace(extent[2], extent[3], log_base.shape[0]),
            log_base,
            levels=levels,
            colors="0.25",
            linewidths=0.42,
        )
        draw_bar_aligned_guides(
            self.ax_baseline,
            geometry,
            extent,
            profile_width_pixels=profile_width,
        )
        self.ax_baseline.plot(float(self.x_deproj.get()), float(self.y_deproj.get()), "x", color="#d62728", ms=8, mew=1.8)
        self.ax_baseline.set_title(f"{name} baseline | deprojected, bar-aligned", loc="left")

        self.ax_injected.imshow(log_inj, origin="lower", extent=extent, cmap="Greys", vmin=levels[0], vmax=levels[-1])
        self.ax_injected.contour(
            np.linspace(extent[0], extent[1], log_inj.shape[1]),
            np.linspace(extent[2], extent[3], log_inj.shape[0]),
            log_inj,
            levels=levels,
            colors="0.25",
            linewidths=0.42,
        )
        draw_bar_aligned_guides(
            self.ax_injected,
            geometry,
            extent,
            profile_width_pixels=profile_width,
        )
        self._contour_mask(self.ax_injected, truth_deproj, extent, "#2ca02c", "truth")
        self.ax_injected.plot(float(self.x_deproj.get()), float(self.y_deproj.get()), "x", color="#d62728", ms=8, mew=1.8)
        self.ax_injected.set_title("Injected toy object", loc="left")

        self.ax_recovery.imshow(log_inj, origin="lower", extent=extent, cmap="Greys", vmin=levels[0], vmax=levels[-1])
        self.ax_recovery.contour(
            np.linspace(extent[0], extent[1], log_inj.shape[1]),
            np.linspace(extent[2], extent[3], log_inj.shape[0]),
            log_inj,
            levels=levels,
            colors="0.25",
            linewidths=0.42,
        )
        draw_bar_aligned_guides(
            self.ax_recovery,
            geometry,
            extent,
            profile_width_pixels=profile_width,
        )
        self._contour_mask(self.ax_recovery, truth_deproj, extent, "#2ca02c", "truth")
        self._contour_mask(self.ax_recovery, recovered_deproj, extent, "#d62728", "recovered")
        self._contour_mask(self.ax_recovery, incremental_deproj, extent, "#1f77b4", "new mask")
        self.ax_recovery.set_title(
            f"Recovery: recall {float(result['recall']):.1%}, new precision {float(result['incremental_precision']):.1%}",
            loc="left",
        )
        self.ax_recovery.legend(loc="upper right", fontsize=8)

        radii = np.asarray(result["radii_deproj"], dtype=float)
        clean_profile = np.asarray(result["clean_profile"], dtype=float)
        injected_profile = np.asarray(result["injected_profile"], dtype=float)
        bridged_profile = np.asarray(result["bridged_profile"], dtype=float)
        bridged_samples = np.asarray(result["bridged_samples"], dtype=bool)
        self.ax_profile.semilogy(radii, clean_profile, color="#1f77b4", lw=1.4, label="baseline")
        self.ax_profile.semilogy(radii, injected_profile, color="#ff7f0e", lw=1.0, alpha=0.65, label="injected")
        bridge_label = "masked + bridge"
        for start, stop in baseline.contiguous_true_runs(bridged_samples):
            plot_start = max(0, start - 1)
            plot_stop = min(bridged_profile.size - 1, stop + 1)
            bridge_slice = slice(plot_start, plot_stop + 1)
            bridge_good = (
                np.isfinite(radii[bridge_slice])
                & np.isfinite(bridged_profile[bridge_slice])
                & (bridged_profile[bridge_slice] > 0)
            )
            if np.count_nonzero(bridge_good) < 2:
                continue
            self.ax_profile.semilogy(
                radii[bridge_slice][bridge_good],
                bridged_profile[bridge_slice][bridge_good],
                color="#2ca02c",
                lw=1.3,
                ls="--",
                label=bridge_label,
            )
            bridge_label = "_nolegend_"
        self.ax_profile.axvline(float(self.x_deproj.get()), color="#d62728", lw=0.9, alpha=0.7)
        self.ax_profile.axvline(-float(self.x_deproj.get()), color="#d62728", lw=0.6, alpha=0.25)
        self.ax_profile.set_title(
            f"Profile recovery | median abs frac error {float(result['profile_abs_error']):.3f}",
            loc="left",
        )
        self.ax_profile.set_xlabel("deprojected bar-major radius [arcsec]")
        self.ax_profile.set_ylabel("intensity")
        self.ax_profile.grid(True, which="both", alpha=0.2)
        self.ax_profile.text(
            0.02,
            0.98,
            self.format_profile_annotation(result),
            transform=self.ax_profile.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            bbox={
                "boxstyle": "round,pad=0.35",
                "facecolor": "white",
                "edgecolor": "0.75",
                "alpha": 0.88,
            },
        )
        self.ax_profile.legend(loc="best", fontsize=8)

        for ax in (self.ax_baseline, self.ax_injected, self.ax_recovery):
            ax.set_xlim(extent[0], extent[1])
            ax.set_ylim(extent[2], extent[3])
            ax.set_aspect("equal", adjustable="box")
            ax.set_xlabel("deprojected bar-axis x [arcsec]")
            ax.set_ylabel("deprojected y [arcsec]")
            ax.grid(True, alpha=0.15)

        self.canvas.draw_idle()

    def _contour_mask(self, ax, mask_image: np.ndarray, extent: list[float], color: str, label: str) -> None:
        if np.nanmax(mask_image) <= 0:
            return
        ax.contour(mask_image, levels=[0.5], origin="lower", extent=extent, colors=[color], linewidths=1.2)
        ax.plot([], [], color=color, label=label)

    def update_implied_mag_display(self, result: dict[str, object]) -> None:
        implied_mag = result.get("implied_integrated_mag")
        if implied_mag is None or not math.isfinite(float(implied_mag)):
            self.implied_mag_var.set("unavailable from FITS header")
            return
        self.implied_mag_var.set(f"{float(implied_mag):.2f}")

    def format_profile_annotation(self, result: dict[str, object]) -> str:
        object_type = str(result.get("object_type_label", self.object_type_var.get()))
        if result.get("brightness_mode") == "magnitude":
            brightness = f"mag {float(result['target_magnitude']):.2f}"
        else:
            brightness = f"peak {float(result['peak_sigma']):.1f} sigma"

        lines = [
            object_type,
            brightness,
            f"FWHM {float(result['fwhm_arcsec']):.1f} arcsec",
        ]
        if OBJECT_TYPES.get(object_type) == "galaxy":
            lines.append(f"q {float(result['axis_ratio']):.2f}, PA {float(result['object_pa']):.0f} deg")
        lines.append(f"truth dilation {int(result['truth_dilation'])} px")
        return "\n".join(lines)

    def format_status(self, name: str, result: dict[str, object]) -> str:
        method = self.method_var.get()
        x0 = float(result["x0"])
        y0 = float(result["y0"])
        implied_mag = result.get("implied_integrated_mag")
        if implied_mag is None or not math.isfinite(float(implied_mag)):
            implied_text = "implied mag unavailable"
        else:
            implied_text = f"implied mag {float(implied_mag):.2f}"
        if result.get("brightness_mode") == "magnitude":
            brightness = (
                f"mag {float(result['target_magnitude']):.2f} "
                f"(F0={float(result['zero_flux_jy']):.1f} Jy, "
                f"flux={float(result['target_flux_jy']):.3e} Jy, BUNIT={result['bunit']})"
            )
        else:
            brightness = f"peak {float(self.peak_sigma.get()):.1f} residual sigma ({implied_text})"
        elapsed = result.get("elapsed_seconds")
        elapsed_text = f"; elapsed: {float(elapsed):.2f}s" if elapsed is not None else ""
        return (
            f"{self.pc_var.get()} | {name} | {method} | {self.object_type_var.get()} "
            f"| {brightness} "
            f"at deproj ({float(self.x_deproj.get()):.2f}, {float(self.y_deproj.get()):.2f}) arcsec "
            f"-> observed pixel ({x0:.1f}, {y0:.1f})\n"
            f"Truth pixels: {int(result['truth_pixels'])}; overlap: {int(result['overlap_pixels'])}; "
            f"recall: {float(result['recall']):.1%}; "
            f"incremental recall: {float(result['incremental_recall']):.1%}; "
            f"incremental precision: {float(result['incremental_precision']):.1%}; "
            f"kept segments: {len(result['kept_rows'])}{elapsed_text}"
        )

    def on_plot_click(self, event) -> None:
        if event.inaxes not in {self.ax_baseline, self.ax_injected, self.ax_recovery}:
            return
        if event.xdata is None or event.ydata is None:
            return
        self.x_deproj.set(round(float(event.xdata), 2))
        self.y_deproj.set(round(float(event.ydata), 2))
        self.implied_mag_var.set("calculate to update")
        self.draw_preview()
        self.status.set(
            f"Object location set to deproj ({float(self.x_deproj.get()):.2f}, "
            f"{float(self.y_deproj.get()):.2f}) arcsec. Press Calculate to run recovery."
        )

    def save_png(self) -> Path:
        name = baseline.safe_filename(self.galaxy_var.get())
        object_name = baseline.safe_filename(self.object_type_var.get().lower().replace(" ", "_"))
        if BRIGHTNESS_MODES.get(self.brightness_mode_var.get(), "sigma") == "magnitude":
            brightness = f"mag{float(self.integrated_mag.get()):.2f}"
        else:
            brightness = f"sig{float(self.peak_sigma.get()):.1f}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        PNG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = PNG_OUTPUT_DIR / (
            f"{name}_{object_name}_x{float(self.x_deproj.get()):.1f}_"
            f"y{float(self.y_deproj.get()):.1f}_{brightness}_{timestamp}.png"
        )
        self.figure.savefig(path, dpi=180)
        return path

    def open_png_folder(self) -> None:
        PNG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        try:
            import os

            os.startfile(PNG_OUTPUT_DIR)
        except OSError as exc:
            self.status.set(f"Could not open PNG folder: {exc}")
            messagebox.showerror("Open PNG folder failed", str(exc))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive synthetic object recovery tester.")
    parser.add_argument("--pc", choices=sorted(PC_RESEARCH_FOLDERS), default=DEFAULT_PC)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = ObjectRecoveryApp(args.manifest, args.pc)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
