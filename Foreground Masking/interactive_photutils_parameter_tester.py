#!/usr/bin/env python3
"""Interactive global Photutils foreground-mask parameter tester.

The tool lets you choose an S4G galaxy from the geometry manifest, adjust the
global Photutils masking parameters, and immediately inspect the detected
foreground candidates against the observed and deprojected bar-aligned views.
"""

from __future__ import annotations

import csv
import math
import sys
import tkinter as tk
import argparse
from pathlib import Path
from tkinter import messagebox, ttk

import numpy as np
from astropy.io import fits
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from scipy.ndimage import map_coordinates, median_filter


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
S4G_PLOTTER_DIR = PROJECT_ROOT / "Erwin_s4g_image_downloader"
BARPROFILES_DIR = PROJECT_ROOT / "Erwin_barprofiles_paper_GB_working_copy"
for path in (PROJECT_ROOT, SCRIPT_DIR, S4G_PLOTTER_DIR, BARPROFILES_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

import angle_utils as angles  # noqa: E402
import foreground_mask_photutils as fgmask  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, erwin_folder, remove_foreground_folder  # noqa: E402


DEFAULT_MANIFEST = S4G_PLOTTER_DIR / "geometry_output" / "s4g_image_geometry_manifest.csv"
DEFAULT_PC = "Laptop"
PARAMETER_DEFAULTS: dict[str, float | int | bool] = {
    "smooth_sigma_pixels": 15.0,
    "detection_nsigma": 5.0,
    "npixels": 8,
    "dilation_radius_pixels": 3,
    "max_area": 500,
    "max_elongation": 6.0,
    "exclude_center_radius_pixels": 12.0,
    "min_peak_residual_nsigma": 0.0,
    "profile_width": 3,
    "deblend": True,
}


def parse_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in value)


def image_path_for_pc(row: dict[str, str], pc_name: str) -> Path:
    """Return the selected machine's S4G FITS path for a manifest row."""
    machine_path = erwin_folder(pc_name) / "s4g_images_36um" / f"{row['name']}.phot.1.fits"
    if machine_path.exists():
        return machine_path
    manifest_path = Path(row.get("image_path", ""))
    return manifest_path


def rows_with_images_for_pc(rows: list[dict[str, str]], pc_name: str) -> list[dict[str, str]]:
    return sorted(
        [row for row in rows if image_path_for_pc(row, pc_name).exists()],
        key=lambda row: row["name"].casefold(),
    )


def required_geometry(row: dict[str, str]) -> dict[str, float] | None:
    keys = {
        "xc": "center_x_pix",
        "yc": "center_y_pix",
        "disk_pa": "disk_pa_deg",
        "inclination": "inclination_deg",
        "bar_pa": "bar_pa_deg",
        "bar_sma": "bar_sma_arcsec",
        "pixel_scale": "pixel_scale_arcsec_y",
    }
    values = {name: parse_float(row.get(column)) for name, column in keys.items()}
    required = ["xc", "yc", "disk_pa", "inclination", "bar_pa", "bar_sma", "pixel_scale"]
    if any(values[name] is None for name in required):
        return None
    values["pixel_scale"] = abs(values["pixel_scale"]) or 0.75
    values["bar_pa"] = angles.RectifyPA(values["bar_pa"], 180.0)
    values["disk_pa"] = angles.RectifyPA(values["disk_pa"], 180.0)
    return values  # type: ignore[return-value]


def pa_endpoint(pa_deg: float, radius: float) -> tuple[float, float]:
    return (
        -radius * math.sin(math.radians(pa_deg)),
        radius * math.cos(math.radians(pa_deg)),
    )


def profile_radius_pixels(data: np.ndarray, geometry: dict[str, float]) -> int:
    xc = geometry["xc"]
    yc = geometry["yc"]
    bar_sma = geometry["bar_sma"]
    pixel_scale = geometry["pixel_scale"]
    max_radius_pix = int(max(20, min(xc - 1, yc - 1, data.shape[1] - xc, data.shape[0] - yc)))
    target_radius_arcsec = max(3.0 * bar_sma, 45.0)
    radius = min(max_radius_pix, int(math.ceil(target_radius_arcsec / pixel_scale)))
    return max(radius, int(math.ceil(1.4 * bar_sma / pixel_scale)))


def robust_log_image(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    finite = data[np.isfinite(data)]
    positive = finite[finite > 0]
    if positive.size == 0:
        positive = np.array([1.0])
    floor = np.nanpercentile(positive, 1)
    if not math.isfinite(floor) or floor <= 0:
        floor = float(np.nanmin(positive))
    log_data = np.log10(np.where(data > floor, data, floor))
    valid = log_data[np.isfinite(log_data)]
    if valid.size < 2:
        lo, hi = -0.5, 0.5
    else:
        lo, hi = np.nanpercentile(valid, [8, 99.5])
    if not math.isfinite(lo) or not math.isfinite(hi) or lo >= hi:
        lo, hi = float(np.nanmin(valid)), float(np.nanmax(valid))
    if lo >= hi:
        hi = lo + 1.0
    return log_data, np.linspace(lo, hi, 16)


def robust_residual_image(data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        return np.zeros_like(data, dtype=float), np.linspace(-1.0, 1.0, 16)

    centre = float(np.nanmedian(finite))
    spread = float(np.nanpercentile(np.abs(finite - centre), 99.0))
    if not math.isfinite(spread) or spread <= 0:
        spread = float(np.nanstd(finite))
    if not math.isfinite(spread) or spread <= 0:
        spread = 1.0

    display = np.clip(data - centre, -spread, spread)
    positive = finite[finite > centre]
    if positive.size >= 2:
        contour_levels = np.nanpercentile(positive - centre, [70, 78, 84, 89, 93, 96, 98, 99.2])
        contour_levels = np.unique(contour_levels[np.isfinite(contour_levels)])
        if contour_levels.size >= 2:
            return display, contour_levels
    return display, np.linspace(0.25 * spread, spread, 8)


def profile_at_pa(
    data: np.ndarray,
    xc: float,
    yc: float,
    pa_deg: float,
    radius_pix: int,
    *,
    width: int,
) -> tuple[np.ndarray, np.ndarray]:
    dx, dy = pa_endpoint(pa_deg, float(radius_pix))
    unit_x = dx / radius_pix
    unit_y = dy / radius_pix
    perp_x = -unit_y
    perp_y = unit_x
    radii = np.linspace(-radius_pix, radius_pix, 2 * radius_pix + 1)
    offsets = np.arange(-(width // 2), width // 2 + 1, dtype=float)
    values = []
    finite = np.isfinite(data)
    filled = np.where(finite, data, 0.0)
    for offset in offsets:
        xs = xc - 1 + unit_x * radii + perp_x * offset
        ys = yc - 1 + unit_y * radii + perp_y * offset
        sampled = map_coordinates(filled, [ys, xs], order=1, mode="constant", cval=0.0)
        support = map_coordinates(finite.astype(float), [ys, xs], order=1, mode="constant", cval=0.0)
        values.append(np.where(support > 0.5, sampled, np.nan))
    value_stack = np.vstack(values)
    finite_counts = np.count_nonzero(np.isfinite(value_stack), axis=0)
    summed = np.nansum(value_stack, axis=0)
    profile = np.divide(
        summed,
        finite_counts,
        out=np.full(radii.shape, np.nan, dtype=float),
        where=finite_counts > 0,
    )
    return radii, profile


def profile_mask_at_pa(
    mask: np.ndarray,
    xc: float,
    yc: float,
    pa_deg: float,
    radius_pix: int,
    *,
    width: int,
) -> np.ndarray:
    _, fraction = profile_at_pa(mask.astype(float), xc, yc, pa_deg, radius_pix, width=width)
    return np.isfinite(fraction) & (fraction > 0.0)


def deprojected_profile_radius(
    pa_deg: float,
    disk_pa_deg: float,
    inclination_deg: float,
    radii_arcsec: np.ndarray,
) -> np.ndarray:
    return angles.deprojectr(pa_deg - disk_pa_deg, inclination_deg, 1.0) * radii_arcsec


def image_transform(disk_pa: float, inclination: float, bar_pa: float) -> np.ndarray:
    disk = np.radians(disk_pa)
    bar = np.radians(bar_pa)
    disk_major = np.array([-np.sin(disk), np.cos(disk)])
    disk_minor = np.array([np.cos(disk), np.sin(disk)])
    deproject = np.outer(disk_major, disk_major) + np.outer(disk_minor, disk_minor) / np.cos(
        np.radians(inclination)
    )
    observed_bar = np.array([-np.sin(bar), np.cos(bar)])
    face_on_bar = deproject @ observed_bar
    angle = math.atan2(face_on_bar[1], face_on_bar[0])
    rotate = np.array([[math.cos(angle), math.sin(angle)], [-math.sin(angle), math.cos(angle)]])
    return rotate @ deproject


def deproject_bar_aligned_cutout(
    data: np.ndarray,
    geometry: dict[str, float],
    radius_arcsec: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    pixel_scale = geometry["pixel_scale"]
    radius_pix = max(8, int(math.ceil(radius_arcsec / pixel_scale)))
    offsets_pix = np.arange(-radius_pix, radius_pix + 1, dtype=float)
    xx_pix, yy_pix = np.meshgrid(offsets_pix, offsets_pix)
    transform_xy = image_transform(geometry["disk_pa"], geometry["inclination"], geometry["bar_pa"])
    inverse_xy = np.linalg.inv(transform_xy)
    input_offsets = inverse_xy @ np.vstack([xx_pix.ravel(), yy_pix.ravel()])
    input_x = (geometry["xc"] - 1.0) + input_offsets[0].reshape(xx_pix.shape)
    input_y = (geometry["yc"] - 1.0) + input_offsets[1].reshape(yy_pix.shape)
    valid = np.isfinite(data)
    filled = np.where(valid, data, 0.0)
    sampled = map_coordinates(filled, [input_y, input_x], order=1, mode="constant", cval=0.0)
    support = map_coordinates(valid.astype(float), [input_y, input_x], order=1, mode="constant", cval=0.0)
    deprojected = np.divide(
        sampled,
        support,
        out=np.full_like(sampled, np.nan, dtype=float),
        where=support > 1.0e-3,
    )
    axis_arcsec = offsets_pix * pixel_scale
    return deprojected, axis_arcsec, axis_arcsec, transform_xy


def mask_products(data: np.ndarray, geometry: dict[str, float], params: dict[str, float | int | bool]):
    smooth = fgmask.make_smooth_galaxy_model(data, float(params["smooth_sigma_pixels"]))
    residual = fgmask.make_residual_image(data, smooth)
    segm = fgmask.detect_compact_sources(
        residual,
        nsigma=float(params["detection_nsigma"]),
        npixels=int(params["npixels"]),
        deblend=bool(params["deblend"]),
    )
    filtered, rows = fgmask.filter_segments(
        segm,
        data,
        residual,
        max_area=int(params["max_area"]),
        max_elongation=float(params["max_elongation"]),
        galaxy_center=(geometry["xc"] - 1, geometry["yc"] - 1),
        exclude_center_radius_pixels=float(params["exclude_center_radius_pixels"]),
        min_peak_residual_nsigma=(
            None
            if float(params["min_peak_residual_nsigma"]) <= 0
            else float(params["min_peak_residual_nsigma"])
        ),
    )
    raw_mask = fgmask.segmentation_to_mask(filtered, data.shape)
    mask = fgmask.dilate_mask(raw_mask, int(params["dilation_radius_pixels"]))
    return mask, [row for row in rows if row["kept"]], residual


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


class ParameterTester(tk.Tk):
    def __init__(self, manifest: Path, pc_name: str):
        super().__init__()
        self.title("Global Photutils Foreground Parameter Tester")
        self.geometry("1420x930")
        self.manifest = manifest
        self.all_rows = read_manifest(manifest)
        self.pc_var = tk.StringVar(value=pc_name)
        self.output_dir = remove_foreground_folder(pc_name) / "interactive_photutils_parameter_tester"
        self.rows: list[dict[str, str]] = []
        self.rows_by_name: dict[str, dict[str, str]] = {}
        self.data_cache: dict[str, tuple[np.ndarray, dict[str, float]]] = {}
        self.after_id: str | None = None

        self._build_controls()
        self._build_figure()
        self.refresh_pc_paths(initial=True)

    def _build_controls(self) -> None:
        control = ttk.Frame(self, padding=8)
        control.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(control, text="Machine").pack(anchor=tk.W)
        pc_combo = ttk.Combobox(
            control,
            textvariable=self.pc_var,
            values=sorted(PC_RESEARCH_FOLDERS),
            width=28,
            state="readonly",
        )
        pc_combo.pack(fill=tk.X, pady=(0, 8))
        pc_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_pc_paths())

        ttk.Label(control, text="Galaxy").pack(anchor=tk.W)
        self.galaxy_var = tk.StringVar()
        self.galaxy_combo = ttk.Combobox(
            control,
            textvariable=self.galaxy_var,
            width=28,
            state="readonly",
        )
        self.galaxy_combo.pack(fill=tk.X, pady=(0, 8))
        self.galaxy_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_selected_galaxy())

        self.auto_update = tk.BooleanVar(value=True)
        ttk.Checkbutton(control, text="Auto redraw", variable=self.auto_update).pack(anchor=tk.W, pady=(0, 8))

        self.vars: dict[str, tk.Variable] = {}
        self.readouts: dict[str, ttk.Label] = {}
        self._scale(control, "smooth_sigma_pixels", "Smooth sigma [px]", 3.0, 40.0, 0.5)
        self._scale(control, "detection_nsigma", "Detection nsigma", 2.0, 10.0, 0.1)
        self._spin(control, "npixels", "Minimum pixels", 1, 80, 1)
        self._spin(control, "dilation_radius_pixels", "Dilation radius [px]", 0, 15, 1)
        self._spin(control, "max_area", "Max segment area [px]", 10, 5000, 10)
        self._scale(control, "max_elongation", "Max elongation", 1.0, 15.0, 0.25)
        self._scale(control, "exclude_center_radius_pixels", "Central exclusion [px]", 0.0, 80.0, 1.0)
        self._scale(control, "min_peak_residual_nsigma", "Min peak nsigma (0 off)", 0.0, 20.0, 0.5)
        self._spin(control, "profile_width", "Profile width [px]", 1, 21, 2)

        deblend_row = ttk.Frame(control)
        deblend_row.pack(fill=tk.X, pady=(8, 4))
        self.vars["deblend"] = tk.BooleanVar(value=bool(PARAMETER_DEFAULTS["deblend"]))
        ttk.Checkbutton(
            deblend_row,
            text="Deblend sources",
            variable=self.vars["deblend"],
            command=self.schedule_redraw,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, anchor=tk.W)
        ttk.Button(deblend_row, text="Reset", width=7, command=lambda: self.reset_one_parameter("deblend")).pack(
            side=tk.RIGHT
        )

        button_row = ttk.Frame(control)
        button_row.pack(fill=tk.X, pady=(10, 4))
        ttk.Button(button_row, text="Redraw", command=self.redraw).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(button_row, text="Reset", command=self.reset_parameters).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(control, text="Save PNG", command=self.save_current_png).pack(fill=tk.X, pady=(0, 4))

        self.status = tk.StringVar(value="")
        ttk.Label(control, textvariable=self.status, wraplength=250, justify=tk.LEFT).pack(fill=tk.X, pady=(10, 0))

    def _scale(
        self,
        parent: ttk.Frame,
        key: str,
        label: str,
        minimum: float,
        maximum: float,
        resolution: float,
    ) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=3)
        var = tk.DoubleVar(value=float(PARAMETER_DEFAULTS[key]))
        self.vars[key] = var
        label_row = ttk.Frame(frame)
        label_row.pack(fill=tk.X)
        ttk.Label(label_row, text=label).pack(side=tk.LEFT, anchor=tk.W)
        ttk.Button(label_row, text="Reset", width=7, command=lambda k=key: self.reset_one_parameter(k)).pack(
            side=tk.RIGHT
        )
        readout = ttk.Label(label_row, width=8)
        readout.pack(side=tk.RIGHT)
        self.readouts[key] = readout
        scale = tk.Scale(
            frame,
            variable=var,
            from_=minimum,
            to=maximum,
            resolution=resolution,
            orient=tk.HORIZONTAL,
            showvalue=False,
            command=lambda _value, k=key, r=readout: self._scale_changed(k, r),
        )
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._scale_changed(key, readout, schedule=False)

    def _spin(
        self,
        parent: ttk.Frame,
        key: str,
        label: str,
        minimum: int,
        maximum: int,
        increment: int,
    ) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=3)
        var = tk.IntVar(value=int(PARAMETER_DEFAULTS[key]))
        self.vars[key] = var
        ttk.Label(frame, text=label).pack(side=tk.LEFT)
        ttk.Button(frame, text="Reset", width=7, command=lambda k=key: self.reset_one_parameter(k)).pack(
            side=tk.RIGHT
        )
        spin = ttk.Spinbox(
            frame,
            textvariable=var,
            from_=minimum,
            to=maximum,
            increment=increment,
            width=8,
            command=self.schedule_redraw,
        )
        spin.pack(side=tk.RIGHT)
        spin.bind("<Return>", lambda _event: self.schedule_redraw())
        spin.bind("<FocusOut>", lambda _event: self.schedule_redraw())

    def _scale_changed(self, key: str, readout: ttk.Label, schedule: bool = True) -> None:
        readout.configure(text=f"{float(self.vars[key].get()):.2f}")
        if schedule:
            self.schedule_redraw()

    def _build_figure(self) -> None:
        frame = ttk.Frame(self)
        frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.figure = Figure(figsize=(11.5, 8.6), dpi=100, constrained_layout=False)
        self.figure.subplots_adjust(left=0.06, right=0.985, bottom=0.07, top=0.97, hspace=0.16, wspace=0.18)
        grid = self.figure.add_gridspec(2, 2, height_ratios=[1.12, 0.74], width_ratios=[1.0, 1.0])
        self.ax_residual = self.figure.add_subplot(grid[0, 0])
        self.ax_deprojected = self.figure.add_subplot(grid[0, 1])
        self.ax_profile = self.figure.add_subplot(grid[1, 1], sharex=self.ax_deprojected)
        self.ax_empty = self.figure.add_subplot(grid[1, 0])
        self.ax_empty.set_axis_off()
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(self.canvas, frame)
        toolbar.update()

    def _align_profile_axis_to_image(self) -> None:
        image_position = self.ax_deprojected.get_position()
        profile_position = self.ax_profile.get_position()
        self.ax_profile.set_position(
            [image_position.x0, profile_position.y0, image_position.width, profile_position.height]
        )

    def refresh_pc_paths(self, initial: bool = False) -> None:
        pc_name = self.pc_var.get()
        self.output_dir = remove_foreground_folder(pc_name) / "interactive_photutils_parameter_tester"
        self.rows = rows_with_images_for_pc(self.all_rows, pc_name)
        if not self.rows:
            self.rows_by_name = {}
            self.galaxy_combo.configure(values=[])
            self.galaxy_var.set("")
            raise RuntimeError(
                f"No FITS images were found for {pc_name} in "
                f"{erwin_folder(pc_name) / 's4g_images_36um'}."
            )

        current = self.galaxy_var.get()
        names = [row["name"] for row in self.rows]
        self.rows_by_name = {row["name"]: row for row in self.rows}
        self.data_cache.clear()
        self.galaxy_combo.configure(values=names)
        self.galaxy_var.set(current if current in self.rows_by_name else names[0])
        if initial:
            self.status.set(f"{pc_name} input folder: {erwin_folder(pc_name) / 's4g_images_36um'}")
        self.load_selected_galaxy()

    def reset_one_parameter(self, key: str) -> None:
        self.vars[key].set(PARAMETER_DEFAULTS[key])
        if key in self.readouts:
            self.readouts[key].configure(text=f"{float(self.vars[key].get()):.2f}")
        self.redraw()

    def reset_parameters(self) -> None:
        for key, value in PARAMETER_DEFAULTS.items():
            self.vars[key].set(value)
            if key in self.readouts:
                self.readouts[key].configure(text=f"{float(self.vars[key].get()):.2f}")
        self.redraw()

    def current_params(self) -> dict[str, float | int | bool]:
        return {key: var.get() for key, var in self.vars.items()}

    def save_current_png(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        params = self.current_params()
        stem = (
            f"{safe_filename(self.galaxy_var.get())}_"
            f"{self.pc_var.get()}_"
            f"nsigma{float(params['detection_nsigma']):.1f}_"
            f"dil{int(params['dilation_radius_pixels'])}_"
            f"area{int(params['max_area'])}"
        )
        path = self.output_dir / f"{stem}.png"
        self.figure.savefig(path, dpi=180)
        self.status.set(f"Saved {path}")

    def schedule_redraw(self) -> None:
        if not self.auto_update.get():
            return
        if self.after_id is not None:
            self.after_cancel(self.after_id)
        self.after_id = self.after(300, self.redraw)

    def load_selected_galaxy(self) -> None:
        try:
            self._load_galaxy(self.galaxy_var.get())
            self.redraw()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Could not load galaxy", str(exc))

    def _load_galaxy(self, name: str) -> tuple[np.ndarray, dict[str, float]]:
        if name in self.data_cache:
            return self.data_cache[name]
        row = self.rows_by_name[name]
        geometry = required_geometry(row)
        if geometry is None:
            raise ValueError(f"{name} has incomplete geometry in {self.manifest}.")
        data = np.squeeze(fits.getdata(image_path_for_pc(row, self.pc_var.get())).astype(float))
        if data.ndim != 2:
            raise ValueError(f"{name} image is not 2D after squeezing: {data.shape}")
        self.data_cache[name] = (data, geometry)
        return data, geometry

    def redraw(self) -> None:
        self.after_id = None
        name = self.galaxy_var.get()
        try:
            data, geometry = self._load_galaxy(name)
            params = self.current_params()
            profile_width = max(1, int(params["profile_width"]))
            mask, kept_rows, residual = mask_products(data, geometry, params)
            self.draw_products(name, data, geometry, params, mask, kept_rows, residual, profile_width)
            masked_fraction = np.count_nonzero(mask) / mask.size
            self.status.set(
                f"{self.pc_var.get()} | {name}: {len(kept_rows)} kept segments, "
                f"{np.count_nonzero(mask)} masked pixels ({masked_fraction:.3%}).\n"
                f"Input: {erwin_folder(self.pc_var.get()) / 's4g_images_36um'}\n"
                f"Output: {self.output_dir}"
            )
        except Exception as exc:  # noqa: BLE001
            self.status.set(f"Error: {exc}")
            messagebox.showerror("Photutils redraw failed", str(exc))

    def draw_products(
        self,
        name: str,
        data: np.ndarray,
        geometry: dict[str, float],
        params: dict[str, float | int | bool],
        mask: np.ndarray,
        kept_rows: list[dict[str, float | int | bool]],
        residual: np.ndarray,
        profile_width: int,
    ) -> None:
        self.ax_residual.clear()
        self.ax_deprojected.clear()
        self.ax_profile.clear()
        self.ax_empty.clear()
        self.ax_empty.set_axis_off()

        pixel_scale = geometry["pixel_scale"]
        radius_pix = profile_radius_pixels(data, geometry)
        bar_pa = geometry["bar_pa"]
        disk_pa = geometry["disk_pa"]
        inclination = geometry["inclination"]
        bar_sma = geometry["bar_sma"]
        rr_pix, intensity = profile_at_pa(
            data, geometry["xc"], geometry["yc"], bar_pa, radius_pix, width=profile_width
        )
        masked_data = np.where(mask, np.nan, data)
        _, masked_intensity = profile_at_pa(
            masked_data, geometry["xc"], geometry["yc"], bar_pa, radius_pix, width=profile_width
        )
        mask_profile = profile_mask_at_pa(
            mask, geometry["xc"], geometry["yc"], bar_pa, radius_pix, width=profile_width
        )
        rr_deproj = deprojected_profile_radius(bar_pa, disk_pa, inclination, rr_pix * pixel_scale)
        bar_sma_deproj = angles.deprojectr(bar_pa - disk_pa, inclination, 1.0) * bar_sma
        profile_limit_arcsec = float(np.nanmax(np.abs(rr_deproj[np.isfinite(rr_deproj)])))

        smoothed = median_filter(data, size=3)
        deproj, x_deproj, y_deproj, transform_xy = deproject_bar_aligned_cutout(
            smoothed, geometry, profile_limit_arcsec
        )
        log_deproj, deproj_levels = robust_log_image(deproj)
        residual_deproj, x_resid, y_resid, _ = deproject_bar_aligned_cutout(
            residual, geometry, profile_limit_arcsec
        )
        residual_display, residual_levels = robust_residual_image(residual_deproj)
        deproj_extent = [x_deproj[0], x_deproj[-1], y_deproj[0], y_deproj[-1]]

        self._draw_residual_view(
            deproj_extent,
            x_resid,
            y_resid,
            residual_display,
            residual_levels,
            transform_xy,
            geometry,
            bar_sma_deproj,
            kept_rows,
            params,
        )
        self._draw_deprojected_view(
            name,
            deproj_extent,
            x_deproj,
            y_deproj,
            log_deproj,
            deproj_levels,
            transform_xy,
            geometry,
            bar_sma_deproj,
            kept_rows,
            params,
        )
        self._draw_profile(
            name,
            rr_deproj,
            intensity,
            masked_intensity,
            mask_profile,
            bar_sma_deproj,
            (deproj_extent[0], deproj_extent[1]),
        )
        self.canvas.draw()
        self._align_profile_axis_to_image()
        self.canvas.draw_idle()

    def _draw_residual_view(
        self,
        extent: list[float],
        x_arcsec: np.ndarray,
        y_arcsec: np.ndarray,
        residual_image: np.ndarray,
        levels: np.ndarray,
        transform_xy: np.ndarray,
        geometry: dict[str, float],
        bar_sma_deproj: float,
        kept_rows: list[dict[str, float | int | bool]],
        params: dict[str, float | int | bool],
    ) -> None:
        ax = self.ax_residual
        finite = residual_image[np.isfinite(residual_image)]
        vmax = float(np.nanmax(np.abs(finite))) if finite.size else 1.0
        if not math.isfinite(vmax) or vmax <= 0:
            vmax = 1.0
        ax.imshow(
            residual_image,
            origin="lower",
            extent=extent,
            cmap="RdBu_r",
            vmin=-vmax,
            vmax=vmax,
        )
        ax.contour(x_arcsec, y_arcsec, residual_image, levels=levels, colors="0.15", linewidths=0.42)
        self._draw_profile_aperture_guides(ax, geometry, params, bar_sma_deproj)
        self._draw_central_exclusion(ax, geometry, params, transform_xy)
        self._add_candidate_circles(ax, kept_rows, geometry, params, extent, transform_xy)
        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])
        ax.set_title("Residual isophotes", loc="left", pad=3)
        ax.set_xlabel("deprojected bar-axis radius [arcsec]")
        ax.set_ylabel("deprojected arcsec")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, alpha=0.18)
        ax.tick_params(axis="x", pad=1)

    def _draw_deprojected_view(
        self,
        name: str,
        extent: list[float],
        x_arcsec: np.ndarray,
        y_arcsec: np.ndarray,
        log_image: np.ndarray,
        levels: np.ndarray,
        transform_xy: np.ndarray,
        geometry: dict[str, float],
        bar_sma_deproj: float,
        kept_rows: list[dict[str, float | int | bool]],
        params: dict[str, float | int | bool],
    ) -> None:
        ax = self.ax_deprojected
        ax.imshow(log_image, origin="lower", extent=extent, cmap="Greys", vmin=levels[0], vmax=levels[-1])
        ax.contour(x_arcsec, y_arcsec, log_image, levels=levels, colors="0.25", linewidths=0.42)
        self._draw_profile_aperture_guides(ax, geometry, params, bar_sma_deproj)
        self._draw_central_exclusion(ax, geometry, params, transform_xy)
        self._add_candidate_circles(ax, kept_rows, geometry, params, extent, transform_xy)
        ax.set_xlim(extent[0], extent[1])
        ax.set_ylim(extent[2], extent[3])
        ax.set_title(f"{name} | deprojected isophotes, bar on x-axis", loc="left", pad=3)
        ax.set_xlabel("deprojected bar-axis radius [arcsec]")
        ax.set_ylabel("deprojected arcsec")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, alpha=0.18)
        ax.tick_params(axis="x", pad=1)

    def _draw_profile_aperture_guides(
        self,
        ax,
        geometry: dict[str, float],
        params: dict[str, float | int | bool],
        bar_sma_deproj: float,
    ) -> None:
        ax.axhline(0, color="#1f77b4", linewidth=1.5)
        half_profile_width_arcsec = 0.5 * int(params["profile_width"]) * geometry["pixel_scale"]
        ax.axhline(
            half_profile_width_arcsec,
            color="#1f77b4",
            linestyle="--",
            linewidth=1.0,
            alpha=0.9,
        )
        ax.axhline(
            -half_profile_width_arcsec,
            color="#1f77b4",
            linestyle="--",
            linewidth=1.0,
            alpha=0.9,
        )
        ax.axvline(0, color="#d62728", linestyle="--", linewidth=1.1)
        ax.plot([-bar_sma_deproj, bar_sma_deproj], [0, 0], "o", color="#1f77b4", ms=4)

    def _draw_central_exclusion(
        self,
        ax,
        geometry: dict[str, float],
        params: dict[str, float | int | bool],
        transform_xy: np.ndarray,
    ) -> None:
        radius_arcsec = float(params["exclude_center_radius_pixels"]) * geometry["pixel_scale"]
        if radius_arcsec <= 0:
            return
        theta = np.linspace(0.0, 2.0 * np.pi, 241)
        observed_circle = np.vstack([radius_arcsec * np.cos(theta), radius_arcsec * np.sin(theta)])
        deprojected_circle = transform_xy @ observed_circle
        ax.plot(
            deprojected_circle[0],
            deprojected_circle[1],
            color="#ffd400",
            linestyle="--",
            linewidth=1.4,
            alpha=0.95,
        )

    def _add_candidate_circles(
        self,
        ax,
        kept_rows: list[dict[str, float | int | bool]],
        geometry: dict[str, float],
        params: dict[str, float | int | bool],
        extent: list[float],
        transform_xy: np.ndarray | None,
    ) -> None:
        pixel_scale = geometry["pixel_scale"]
        for row in kept_rows:
            x_arcsec = pixel_scale * (float(row["x_centroid"]) + 1 - geometry["xc"])
            y_arcsec = pixel_scale * (float(row["y_centroid"]) + 1 - geometry["yc"])
            if transform_xy is not None:
                x_arcsec, y_arcsec = transform_xy @ np.array([x_arcsec, y_arcsec])
            radius = pixel_scale * math.sqrt(float(row["area"]) / math.pi)
            radius += pixel_scale * int(params["dilation_radius_pixels"])
            radius = max(radius, 2.2 * pixel_scale)
            if extent[0] <= x_arcsec <= extent[1] and extent[2] <= y_arcsec <= extent[3]:
                ax.add_patch(
                    Circle(
                        (x_arcsec, y_arcsec),
                        radius,
                        edgecolor="red",
                        facecolor="none",
                        linewidth=1.15,
                        alpha=0.95,
                    )
                )

    def _draw_profile(
        self,
        name: str,
        radii: np.ndarray,
        intensity: np.ndarray,
        masked_intensity: np.ndarray,
        mask_profile: np.ndarray,
        bar_sma_deproj: float,
        x_limits: tuple[float, float],
    ) -> None:
        ax = self.ax_profile
        positive = np.isfinite(intensity) & (intensity > 0)
        if np.any(positive):
            ymin = np.nanpercentile(intensity[positive], 2) * 0.8
            ymax = np.nanmax(intensity[positive]) * 1.25
        else:
            ymin, ymax = 1.0, 10.0
        for start, stop in contiguous_true_runs(mask_profile):
            ax.axvspan(radii[start], radii[stop], color="red", alpha=0.16, linewidth=0)
        ax.semilogy(radii, intensity, color="#1f77b4", linewidth=1.4, label="original major-axis profile")
        ax.semilogy(radii, masked_intensity, color="#ff7f0e", linewidth=1.25, label="masked profile")
        ax.axvline(bar_sma_deproj, color="#1f77b4", linewidth=1.0)
        ax.axvline(-bar_sma_deproj, color="#1f77b4", linewidth=1.0)
        ax.axvline(0, color="0.6", linewidth=0.7)
        ax.set_xlim(x_limits[0], x_limits[1])
        ax.set_ylim(ymin, ymax)
        ax.set_xlabel("deprojected bar-major radius [arcsec]")
        ax.set_ylabel("intensity")
        ax.grid(True, which="both", alpha=0.2)
        ax.legend(loc="best")
        ax.tick_params(axis="x", pad=1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive global Photutils parameter tester.")
    parser.add_argument(
        "--pc",
        choices=sorted(PC_RESEARCH_FOLDERS),
        default=DEFAULT_PC,
        help=(
            "Select the machine-specific Dropbox folders. "
            "Laptop uses C:\\Users\\gordo\\Dropbox; Desktop uses D:\\Dropbox."
        ),
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = ParameterTester(args.manifest, args.pc)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
