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
PROJECT_ROOT = SCRIPT_DIR.parent
for path in (PROJECT_ROOT, SCRIPT_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

import foreground_display_helpers as display  # noqa: E402
import mtobjects_spike_gate_processing as mtobjects_tool  # noqa: E402
import sep_processing as sep_tool  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, remove_foreground_folder  # noqa: E402


DEFAULT_PC = "Desktop"
DEFAULT_GALAXY = "ESO120-012"
TOY_TYPES = {
    "Gaussian star": "star",
    "Star cluster": "cluster",
    "Compact galaxy": "galaxy",
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
    params = {
        "detect_on": "residual",
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
    for key, value in load_json_params(best_json).items():
        if key in params:
            params[key] = value
    return params


def mtobjects_params(best_json: Path | None) -> dict[str, float | int | str]:
    params = {
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
        self.geometry("1600x980")
        self.minsize(1150, 760)
        self.manifest = manifest
        self.pc_var = tk.StringVar(value=pc_name)
        self.best_json = best_json or latest_best_json(pc_name, algorithm)
        self.mtobjects_root = mtobjects_root
        self.all_rows = display.read_manifest(manifest)
        self.rows: list[dict[str, str]] = []
        self.rows_by_name: dict[str, dict[str, str]] = {}
        self.data: np.ndarray | None = None
        self.geometry_data: dict[str, float] | None = None
        self.output_dir = remove_foreground_folder(pc_name) / f"interactive_{algorithm.lower()}_toy_object_tester"

        self._build_controls()
        self._build_figure()
        self.refresh_pc_paths()

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
        self.peak_var = tk.DoubleVar(value=8.0)
        self.fwhm_var = tk.DoubleVar(value=5.0)
        self.axis_ratio_var = tk.DoubleVar(value=0.65)
        self.pa_var = tk.DoubleVar(value=30.0)
        self.truth_dilation_var = tk.IntVar(value=1)

        ttk.Label(control, text="Toy type").pack(anchor=tk.W)
        ttk.Combobox(control, textvariable=self.toy_type_var, values=list(TOY_TYPES), state="readonly").pack(fill=tk.X)
        for label, variable, low, high, increment in [
            ("x deprojected arcsec", self.x_var, -250, 250, 1),
            ("y deprojected arcsec", self.y_var, -250, 250, 1),
            ("peak residual sigma", self.peak_var, 0.5, 60, 0.5),
            ("FWHM pixels", self.fwhm_var, 1, 40, 0.5),
            ("axis ratio", self.axis_ratio_var, 0.1, 1.0, 0.05),
            ("object PA deg", self.pa_var, -180, 180, 5),
            ("truth dilation pixels", self.truth_dilation_var, 0, 10, 1),
        ]:
            ttk.Label(control, text=label).pack(anchor=tk.W, pady=(6, 0))
            ttk.Spinbox(control, textvariable=variable, from_=low, to=high, increment=increment).pack(fill=tk.X)

        ttk.Button(control, text="Calculate", command=self.calculate).pack(fill=tk.X, pady=(14, 4))
        ttk.Button(control, text="Save PNG", command=self.save_png).pack(fill=tk.X, pady=(0, 4))
        ttk.Button(control, text="Open Output Folder", command=self.open_output_folder).pack(fill=tk.X)

        source = str(self.best_json) if self.best_json else "built-in defaults"
        ttk.Label(control, text=f"Parameters: {source}", wraplength=285).pack(fill=tk.X, pady=(12, 0))

    def _build_figure(self) -> None:
        self.figure = Figure(figsize=(11.5, 8.6), dpi=100, constrained_layout=True)
        self.axes = self.figure.subplots(2, 2)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(self.canvas, self, pack_toolbar=False).pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.mpl_connect("button_press_event", self.on_click)

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
        self.geometry_data = display.required_geometry(row)
        if self.geometry_data is None:
            self.status.set("Selected galaxy has incomplete geometry.")
            return
        self.data, _header = sep_tool.load_fits(display.image_path_for_pc(row, self.pc_var.get()))
        self.draw_preview()

    def draw_preview(self) -> None:
        if self.data is None or self.geometry_data is None:
            return
        radius_arcsec = display.profile_radius_pixels(self.data, self.geometry_data) * self.geometry_data["pixel_scale"]
        view, x_axis, y_axis = display.deproject_bar_aligned_cutout(self.data, self.geometry_data, radius_arcsec)
        ax = self.axes[0, 0]
        for item in self.axes.ravel():
            item.clear()
        vmin, vmax = display.robust_limits(view)
        ax.imshow(view, origin="lower", extent=[x_axis[0], x_axis[-1], y_axis[0], y_axis[-1]], cmap="gist_gray_r", vmin=vmin, vmax=vmax)
        ax.plot(float(self.x_var.get()), float(self.y_var.get()), "rx", ms=9, mew=2)
        ax.set_title("Click to place toy")
        self.canvas.draw_idle()

    def calculate(self) -> None:
        if self.data is None or self.geometry_data is None:
            return
        try:
            result = self.make_result()
            self.draw_result(result)
            self.status.set(
                f"{self.algorithm} recovered {result['overlap_pixels']}/{result['truth_pixels']} truth pixels "
                f"({result['recall']:.1%}); masked {result['masked_fraction']:.2%}."
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Toy object calculation failed", str(exc))

    def make_result(self) -> dict:
        assert self.data is not None and self.geometry_data is not None
        x_pix, y_pix = deprojected_to_observed_pixel(float(self.x_var.get()), float(self.y_var.get()), self.geometry_data)
        sigma = robust_sigma(self.data)
        model = toy_model(
            self.data.shape,
            TOY_TYPES[self.toy_type_var.get()],
            x_pix,
            y_pix,
            float(self.peak_var.get()) * sigma,
            float(self.fwhm_var.get()),
            float(self.axis_ratio_var.get()),
            float(self.pa_var.get()),
        )
        truth = model > max(np.nanmax(model) * 0.08, 0)
        dilation = int(self.truth_dilation_var.get())
        if dilation > 0:
            truth = ndimage.binary_dilation(truth, structure=circular_footprint(dilation))
        injected = np.array(self.data, copy=True)
        injected[np.isfinite(injected)] += model[np.isfinite(injected)]

        if self.algorithm == "SEP":
            products = sep_tool.sep_products(injected, sep_params(self.best_json), self.geometry_data)
        else:
            root = mtobjects_tool.find_mtobjects_root(self.mtobjects_root)
            products = mtobjects_tool.mtobjects_products(injected, mtobjects_params(self.best_json), self.geometry_data, root)

        mask = np.asarray(products["mask"], dtype=bool)
        overlap = int(np.count_nonzero(mask & truth))
        truth_pixels = int(np.count_nonzero(truth))
        return {
            "injected": injected,
            "model": model,
            "truth": truth,
            "mask": mask,
            "cleaned": np.asarray(products["cleaned"], dtype=float),
            "overlap_pixels": overlap,
            "truth_pixels": truth_pixels,
            "recall": overlap / truth_pixels if truth_pixels else 0.0,
            "masked_fraction": float(np.count_nonzero(mask) / mask.size),
        }

    def draw_result(self, result: dict) -> None:
        assert self.data is not None and self.geometry_data is not None
        radius_arcsec = display.profile_radius_pixels(self.data, self.geometry_data) * self.geometry_data["pixel_scale"]
        panels = [
            ("Original", self.data, "gist_gray_r"),
            ("Injected toy", result["injected"], "gist_gray_r"),
            (f"{self.algorithm} mask", result["mask"].astype(float), "Reds"),
            ("Recovered truth overlay", result["truth"].astype(float) + result["mask"].astype(float), "viridis"),
        ]
        for ax, (title, image, cmap) in zip(self.axes.ravel(), panels):
            ax.clear()
            view, x_axis, y_axis = display.deproject_bar_aligned_cutout(image, self.geometry_data, radius_arcsec, order=0 if image.dtype == bool else 1)
            vmin, vmax = (0, 2) if "overlay" in title.lower() else display.robust_limits(view)
            ax.imshow(view, origin="lower", extent=[x_axis[0], x_axis[-1], y_axis[0], y_axis[-1]], cmap=cmap, vmin=vmin, vmax=vmax)
            ax.plot(float(self.x_var.get()), float(self.y_var.get()), "cx", ms=8, mew=1.7)
            ax.set_title(title)
        self.canvas.draw_idle()

    def on_click(self, event) -> None:
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            return
        self.x_var.set(round(float(event.xdata), 2))
        self.y_var.set(round(float(event.ydata), 2))
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
