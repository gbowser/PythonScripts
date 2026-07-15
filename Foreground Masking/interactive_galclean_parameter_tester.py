#!/usr/bin/env python3
"""Interactive GalClean parameter tester for S4G FITS images.

This adapts the algorithm from astroferreira/galclean for the local S4G
manifest/input-folder workflow used by the other foreground masking tools.
GalClean replaces detected external sources with sampled sky pixels and saves
both a cleaned FITS image and an inspection PNG for each calculation.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import math
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from photutils.segmentation import detect_sources
from scipy.ndimage import binary_dilation, zoom


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
S4G_PLOTTER_DIR = PROJECT_ROOT / "Erwin_s4g_image_downloader"
for path in (PROJECT_ROOT, SCRIPT_DIR, S4G_PLOTTER_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

from machine_paths import PC_RESEARCH_FOLDERS, erwin_folder, remove_foreground_folder  # noqa: E402


DEFAULT_MANIFEST = S4G_PLOTTER_DIR / "geometry_output" / "s4g_image_geometry_manifest.csv"
DEFAULT_PC = "Desktop"
DEFAULT_GALAXY = "ESO120-012"
DEFAULT_SIGLEVEL = 4.0
DEFAULT_MIN_SIZE = 0.01
DEFAULT_SCALE_FACTOR = 4.0


def finite_float(value: str | float | int | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in value)


def image_path_for_pc(row: dict[str, str], pc_name: str) -> Path:
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


def generate_circular_kernel(diameter: float) -> np.ndarray:
    """Return the circular dilation kernel used by GalClean."""
    d = max(1, int(round(diameter)))
    if d % 2 == 0:
        d += 1
    radius = d / 2.0
    yy, xx = np.ogrid[:d, :d]
    center = (d - 1) / 2.0
    return ((xx - center) ** 2 + (yy - center) ** 2 <= radius**2)


def detect_sources_compat(data: np.ndarray, threshold: float, npixels: int):
    try:
        return detect_sources(data, threshold=threshold, n_pixels=npixels)
    except TypeError:
        return detect_sources(data, threshold=threshold, npixels=npixels)


def measure_background(data: np.ndarray, iterations: int, mask: np.ndarray | None = None) -> tuple[float, float, float]:
    """Iteratively measure sky background, dilating detected source masks."""
    finite = np.isfinite(data)
    if mask is not None:
        finite &= ~np.asarray(mask, dtype=bool)
    if not np.any(finite):
        raise ValueError("No finite unmasked pixels are available for background measurement.")

    mean, median, std = sigma_clipped_stats(data, sigma=3.0, mask=~finite)
    if iterations <= 0:
        return float(mean), float(median), float(std)

    threshold = float(median + 2.0 * std)
    filled = np.where(np.isfinite(data), data, median)
    segm = detect_sources_compat(filled, threshold, npixels=5)
    if segm is None:
        return float(mean), float(median), float(std)

    next_mask = binary_dilation(segm.data > 0, generate_circular_kernel(5))
    return measure_background(data, iterations - 1, next_mask)


def rescale(data: np.ndarray, scale_factor: float) -> np.ndarray:
    """Wrapper around scipy zoom, matching GalClean's maximum upscaled size."""
    factor = float(scale_factor)
    if factor <= 0:
        raise ValueError("scale_factor must be positive.")
    max_side = max(data.shape)
    if max_side * factor > 2000:
        factor = 2000.0 / max_side
    return zoom(data, factor, prefilter=True)


def center_label(segm_data: np.ndarray) -> int:
    y_center = segm_data.shape[0] // 2
    x_center = segm_data.shape[1] // 2
    label = int(segm_data[y_center, x_center])
    if label > 0:
        return label

    labels = np.unique(segm_data[segm_data > 0])
    if labels.size == 0:
        return 0

    best_label = 0
    best_distance = np.inf
    for candidate in labels:
        yy, xx = np.nonzero(segm_data == candidate)
        distance = (float(np.mean(yy)) - y_center) ** 2 + (float(np.mean(xx)) - x_center) ** 2
        if distance < best_distance:
            best_distance = distance
            best_label = int(candidate)
    return best_label


def segmentation_map(data: np.ndarray, threshold: float, min_size: float = DEFAULT_MIN_SIZE) -> tuple[np.ndarray, np.ndarray]:
    """Create the GalClean external-source segmentation map."""
    min_side = min(data.shape)
    npixels = max(1, int(round((min_side * float(min_size)) ** 2)))
    filled = np.where(np.isfinite(data), data, np.nanmedian(data))
    segm = detect_sources_compat(filled, threshold, npixels=npixels)
    if segm is None:
        return np.zeros_like(data, dtype=bool), data[np.isfinite(data)]

    seg_map = np.asarray(segm.data, dtype=int)
    galaxy_label = center_label(seg_map)
    galaxy_mask = seg_map == galaxy_label if galaxy_label > 0 else np.zeros_like(seg_map, dtype=bool)
    galaxy_mask = binary_dilation(galaxy_mask, generate_circular_kernel(min_side / 10.0))

    background_pixels = data[(seg_map == 0) & np.isfinite(data)]
    if background_pixels.size == 0:
        background_pixels = data[np.isfinite(data)]

    external = (seg_map > 0) & ~galaxy_mask
    external = binary_dilation(external, generate_circular_kernel(min_side / 20.0))
    return external.astype(bool), background_pixels


def galclean_products(
    original: np.ndarray,
    siglevel: float = DEFAULT_SIGLEVEL,
    min_size: float = DEFAULT_MIN_SIZE,
    scale_factor: float = DEFAULT_SCALE_FACTOR,
    random_seed: int = 0,
) -> dict[str, np.ndarray | float | int]:
    """Run the GalClean replacement algorithm and return all display products."""
    image = np.squeeze(np.asarray(original, dtype=float))
    if image.ndim != 2:
        raise ValueError(f"Expected a 2D FITS image after squeezing, got shape {image.shape}.")
    if not np.any(np.isfinite(image)):
        raise ValueError("The FITS image contains no finite pixels.")

    finite = np.isfinite(image)
    mean, median, std = measure_background(image, 2)
    working_image = np.where(finite, image, median)
    threshold = median + float(siglevel) * std
    scaled_image = rescale(working_image, scale_factor)
    seg_map, background_pixels = segmentation_map(scaled_image, threshold, min_size=min_size)

    segmented_scaled = np.array(scaled_image, copy=True)
    replace_count = int(np.count_nonzero(seg_map))
    if replace_count > 0:
        rng = np.random.default_rng(random_seed)
        segmented_scaled[seg_map] = rng.choice(background_pixels, replace_count, replace=True)

    downscale_factor = image.shape[0] / segmented_scaled.shape[0]
    cleaned = rescale(segmented_scaled, downscale_factor)
    if cleaned.shape != image.shape:
        cleaned = cleaned[: image.shape[0], : image.shape[1]]
        padded = np.array(working_image, copy=True)
        padded[: cleaned.shape[0], : cleaned.shape[1]] = cleaned
        cleaned = padded
    cleaned[~finite] = np.nan

    mask_original = zoom(seg_map.astype(float), image.shape[0] / seg_map.shape[0], order=0, prefilter=False) > 0.5
    if mask_original.shape != image.shape:
        fixed = np.zeros_like(image, dtype=bool)
        fixed[: mask_original.shape[0], : mask_original.shape[1]] = mask_original[: image.shape[0], : image.shape[1]]
        mask_original = fixed

    return {
        "cleaned": cleaned,
        "residual": image - cleaned,
        "mask": mask_original,
        "scaled_mask": seg_map,
        "threshold": float(threshold),
        "background_mean": float(mean),
        "background_median": float(median),
        "background_std": float(std),
        "replaced_pixels": int(np.count_nonzero(mask_original)),
    }


def robust_limits(data: np.ndarray, low: float = 1.0, high: float = 99.5) -> tuple[float, float]:
    finite = np.asarray(data)[np.isfinite(data)]
    if finite.size == 0:
        return 0.0, 1.0
    vmin, vmax = np.percentile(finite, [low, high])
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
        vmin, vmax = float(np.nanmin(finite)), float(np.nanmax(finite))
    if vmin == vmax:
        vmax = vmin + 1.0
    return float(vmin), float(vmax)


class GalCleanTester(tk.Tk):
    def __init__(self, manifest: Path, pc_name: str):
        super().__init__()
        self.title("GalClean Parameter Tester")
        self.geometry("1700x1100")
        self.minsize(1350, 900)
        self.manifest = manifest
        self.all_rows = read_manifest(manifest)
        self.pc_var = tk.StringVar(value=pc_name)
        self.output_dir = remove_foreground_folder(pc_name) / "interactive_galclean_parameter_tester"
        self.rows: list[dict[str, str]] = []
        self.rows_by_name: dict[str, dict[str, str]] = {}
        self.data_cache: dict[str, tuple[np.ndarray, fits.Header]] = {}
        self.calculating_overlay = None

        self._build_controls()
        self._build_figure()
        self.refresh_pc_paths(initial=True)

    def _build_controls(self) -> None:
        control = ttk.Frame(self, padding=10)
        control.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(control, text="Machine").pack(anchor=tk.W)
        pc_combo = ttk.Combobox(
            control,
            textvariable=self.pc_var,
            values=sorted(PC_RESEARCH_FOLDERS),
            width=30,
            state="readonly",
        )
        pc_combo.pack(fill=tk.X, pady=(0, 8))
        pc_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_pc_paths())

        ttk.Label(control, text="Galaxy").pack(anchor=tk.W)
        self.galaxy_var = tk.StringVar()
        self.galaxy_combo = ttk.Combobox(control, textvariable=self.galaxy_var, width=30, state="readonly")
        self.galaxy_combo.pack(fill=tk.X, pady=(0, 10))
        self.galaxy_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_selected_galaxy())

        self.vars: dict[str, tk.Variable] = {}
        self.readouts: dict[str, ttk.Label] = {}
        self._scale(control, "siglevel", "Detection sigma level", 1.0, 12.0, 0.1, DEFAULT_SIGLEVEL)
        self._scale(control, "min_size", "Minimum source size fraction", 0.001, 0.05, 0.001, DEFAULT_MIN_SIZE)
        self._scale(control, "scale_factor", "Upscale factor", 1.0, 6.0, 0.25, DEFAULT_SCALE_FACTOR)
        self._spin(control, "random_seed", "Replacement random seed", 0, 999999, 1, 0)

        button_row = ttk.Frame(control)
        button_row.pack(fill=tk.X, pady=(12, 4))
        ttk.Button(button_row, text="Calculate", command=self.calculate_now).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(button_row, text="Reset", command=self.reset_parameters).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(control, text="Open PNG Folder", command=self.open_output_folder).pack(fill=tk.X, pady=(0, 4))

        self.status = tk.StringVar(value="")
        ttk.Label(control, textvariable=self.status, wraplength=300, justify=tk.LEFT).pack(fill=tk.X, pady=(10, 0))

    def _scale(
        self,
        parent: ttk.Frame,
        key: str,
        label: str,
        minimum: float,
        maximum: float,
        resolution: float,
        default: float,
    ) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=4)
        ttk.Label(frame, text=label).pack(anchor=tk.W)
        row = ttk.Frame(frame)
        row.pack(fill=tk.X)
        var = tk.DoubleVar(value=default)
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

    def _spin(
        self,
        parent: ttk.Frame,
        key: str,
        label: str,
        minimum: int,
        maximum: int,
        increment: int,
        default: int,
    ) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=4)
        ttk.Label(frame, text=label).pack(side=tk.LEFT)
        var = tk.IntVar(value=default)
        self.vars[key] = var
        spin = ttk.Spinbox(
            frame,
            textvariable=var,
            from_=minimum,
            to=maximum,
            increment=increment,
            width=10,
            command=self.mark_needs_calculation,
        )
        spin.pack(side=tk.RIGHT)
        spin.bind("<Return>", lambda _event: self.mark_needs_calculation())
        spin.bind("<FocusOut>", lambda _event: self.mark_needs_calculation())

    def _build_figure(self) -> None:
        frame = ttk.Frame(self)
        frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.figure = Figure(figsize=(12.0, 9.0), dpi=100, constrained_layout=True)
        grid = self.figure.add_gridspec(2, 2)
        self.ax_original = self.figure.add_subplot(grid[0, 0])
        self.ax_cleaned = self.figure.add_subplot(grid[0, 1])
        self.ax_residual = self.figure.add_subplot(grid[1, 0])
        self.ax_mask = self.figure.add_subplot(grid[1, 1])
        self.canvas = FigureCanvasTkAgg(self.figure, master=frame)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(self.canvas, frame)
        toolbar.update()

    def parameter_changed(self, key: str, mark: bool = True) -> None:
        if key in self.readouts:
            self.readouts[key].configure(text=f"{float(self.vars[key].get()):.3f}")
        if mark:
            self.mark_needs_calculation()

    def current_params(self) -> dict[str, float | int]:
        return {
            "siglevel": float(self.vars["siglevel"].get()),
            "min_size": float(self.vars["min_size"].get()),
            "scale_factor": float(self.vars["scale_factor"].get()),
            "random_seed": int(self.vars["random_seed"].get()),
        }

    def reset_parameters(self) -> None:
        self.vars["siglevel"].set(DEFAULT_SIGLEVEL)
        self.vars["min_size"].set(DEFAULT_MIN_SIZE)
        self.vars["scale_factor"].set(DEFAULT_SCALE_FACTOR)
        self.vars["random_seed"].set(0)
        for key in ("siglevel", "min_size", "scale_factor"):
            self.parameter_changed(key, mark=False)
        self.mark_needs_calculation()

    def refresh_pc_paths(self, initial: bool = False) -> None:
        pc_name = self.pc_var.get()
        self.output_dir = remove_foreground_folder(pc_name) / "interactive_galclean_parameter_tester"
        self.rows = rows_with_images_for_pc(self.all_rows, pc_name)
        if not self.rows:
            self.rows_by_name = {}
            self.galaxy_combo.configure(values=[])
            self.galaxy_var.set("")
            raise RuntimeError(f"No FITS images were found for {pc_name} in {erwin_folder(pc_name) / 's4g_images_36um'}.")

        names = [row["name"] for row in self.rows]
        self.rows_by_name = {row["name"]: row for row in self.rows}
        self.data_cache.clear()
        self.galaxy_combo.configure(values=names)
        current = self.galaxy_var.get()
        if current in self.rows_by_name:
            selected = current
        elif initial and DEFAULT_GALAXY in self.rows_by_name:
            selected = DEFAULT_GALAXY
        else:
            selected = names[0]
        self.galaxy_var.set(selected)
        self.load_selected_galaxy()

    def load_selected_galaxy(self) -> None:
        try:
            self._load_galaxy(self.galaxy_var.get())
            self.mark_needs_calculation()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Could not load galaxy", str(exc))

    def _load_galaxy(self, name: str) -> tuple[np.ndarray, fits.Header]:
        if name in self.data_cache:
            return self.data_cache[name]
        row = self.rows_by_name[name]
        path = image_path_for_pc(row, self.pc_var.get())
        with fits.open(path) as hdul:
            data = np.squeeze(np.asarray(hdul[0].data, dtype=float))
            header = hdul[0].header.copy()
        if data.ndim != 2:
            raise ValueError(f"{name} image is not 2D after squeezing: {data.shape}")
        self.data_cache[name] = (data, header)
        return data, header

    def mark_needs_calculation(self) -> None:
        name = self.galaxy_var.get()
        if name:
            self.status.set(f"{self.pc_var.get()} | {name}: click Calculate to run GalClean.")

    def output_stem(self, params: dict[str, float | int]) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem = (
            f"{safe_filename(self.galaxy_var.get())}_{self.pc_var.get()}_galclean_"
            f"sig{float(params['siglevel']):.1f}_"
            f"min{float(params['min_size']):.3f}_"
            f"scale{float(params['scale_factor']):.2f}_"
            f"seed{int(params['random_seed'])}_"
            f"{timestamp}"
        )
        return safe_filename(stem)

    def output_paths(self, params: dict[str, float | int]) -> tuple[Path, Path]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stem = self.output_stem(params)
        png_path = self.output_dir / f"{stem}.png"
        fits_path = self.output_dir / f"{stem}_seg.fits"
        counter = 1
        while png_path.exists() or fits_path.exists():
            png_path = self.output_dir / f"{stem}_{counter}.png"
            fits_path = self.output_dir / f"{stem}_{counter}_seg.fits"
            counter += 1
        return png_path, fits_path

    def open_output_folder(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(["explorer", str(self.output_dir)])
        except OSError as exc:
            messagebox.showerror("Could not open PNG folder", str(exc))

    def calculate_now(self) -> None:
        name = self.galaxy_var.get()
        try:
            self.status.set(f"Calculating {name} with GalClean...")
            self._show_calculating_overlay()
            self.update_idletasks()
            data, header = self._load_galaxy(name)
            params = self.current_params()
            products = galclean_products(
                data,
                siglevel=float(params["siglevel"]),
                min_size=float(params["min_size"]),
                scale_factor=float(params["scale_factor"]),
                random_seed=int(params["random_seed"]),
            )
            self.draw_products(name, data, products, params)
            png_path, fits_path = self.output_paths(params)
            self.figure.savefig(png_path, dpi=180)
            output_header = header.copy()
            output_header["HISTORY"] = "Cleaned with interactive_galclean_parameter_tester.py"
            output_header["HISTORY"] = "Algorithm adapted from https://github.com/astroferreira/galclean"
            fits.writeto(fits_path, np.asarray(products["cleaned"], dtype=float), output_header, overwrite=True)
            self.status.set(
                f"{self.pc_var.get()} | {name} | GalClean replaced {int(products['replaced_pixels'])} pixels.\n"
                f"threshold={float(products['threshold']):.6g}, "
                f"sky median={float(products['background_median']):.6g}, "
                f"sky std={float(products['background_std']):.6g}\n"
                f"Output: {self.output_dir}\n"
                f"Saved PNG: {png_path.name}\n"
                f"Saved FITS: {fits_path.name}"
            )
        except Exception as exc:  # noqa: BLE001
            self._remove_calculating_overlay()
            self.status.set(f"Error: {exc}")
            messagebox.showerror("GalClean calculation failed", str(exc))

    def draw_products(
        self,
        name: str,
        original: np.ndarray,
        products: dict[str, np.ndarray | float | int],
        params: dict[str, float | int],
    ) -> None:
        self._remove_calculating_overlay()
        cleaned = np.asarray(products["cleaned"], dtype=float)
        residual = np.asarray(products["residual"], dtype=float)
        mask = np.asarray(products["mask"], dtype=bool)

        for ax in (self.ax_original, self.ax_cleaned, self.ax_residual, self.ax_mask):
            ax.clear()
            ax.set_xticks([])
            ax.set_yticks([])

        vmin, vmax = robust_limits(original)
        self.ax_original.imshow(original, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax)
        self.ax_original.set_title(f"{name} original")

        self.ax_cleaned.imshow(cleaned, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax)
        self.ax_cleaned.set_title("GalClean cleaned")

        rvmin, rvmax = robust_limits(residual, 1.0, 99.0)
        abs_limit = max(abs(rvmin), abs(rvmax))
        self.ax_residual.imshow(residual, origin="lower", cmap="coolwarm", vmin=-abs_limit, vmax=abs_limit)
        self.ax_residual.set_title("Original - cleaned")

        self.ax_mask.imshow(original, origin="lower", cmap="gist_gray_r", vmin=vmin, vmax=vmax)
        self.ax_mask.imshow(np.ma.masked_where(~mask, mask), origin="lower", cmap="autumn", alpha=0.55)
        self.ax_mask.set_title(
            f"Mask | sigma={float(params['siglevel']):.1f}, min={float(params['min_size']):.3f}"
        )

        self.canvas.draw_idle()

    def _show_calculating_overlay(self) -> None:
        self._remove_calculating_overlay()
        overlay = self.figure.add_axes((0, 0, 1, 1), zorder=1000)
        overlay.set_axis_off()
        overlay.patch.set_facecolor("black")
        overlay.patch.set_alpha(0.34)
        overlay.text(
            0.5,
            0.5,
            "Calculating",
            transform=overlay.transAxes,
            ha="center",
            va="center",
            fontsize=30,
            fontweight="bold",
            color="white",
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
    parser.add_argument(
        "--pc",
        choices=sorted(PC_RESEARCH_FOLDERS),
        default=DEFAULT_PC,
        help="Machine path preset. Laptop uses C:\\Users\\gordo\\Dropbox; Desktop uses D:\\Dropbox.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = GalCleanTester(args.manifest, args.pc)
    app.mainloop()


if __name__ == "__main__":
    main()
