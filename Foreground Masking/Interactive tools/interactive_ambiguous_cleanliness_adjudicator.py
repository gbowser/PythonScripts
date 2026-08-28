#!/usr/bin/env python3
"""Resolve ambiguous cleanliness reviews by measuring their bar-profile impact.

Left-click a suspected contaminant in either image panel to add a circular mask.
Drag a mask to refine its position; right-click a mask to remove it.  The
original FITS image is never modified.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import math
import os
from pathlib import Path
import sys
import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np
from astropy.io import fits
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from scipy.ndimage import gaussian_filter


SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = SCRIPT_DIR.parent / "Shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))
import foreground_display_helpers as display  # noqa: E402


AMBIGUOUS_NAMES = (
    "NGC5669", "UGC09661", "NGC4559", "IC0797", "ESO420-009",
    "UGC04988", "NGC4102", "NGC1255",
)
if os.name == "nt":
    DEFAULT_IMAGE_DIR = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Erwin\s4g_images_36um")
    DEFAULT_OUTPUT = Path(
        r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects"
        r"\ambiguous_profile_adjudication.csv"
    )
else:
    DEFAULT_IMAGE_DIR = Path("/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Erwin/s4g_images_36um")
    DEFAULT_OUTPUT = Path(
        "/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/"
        "ambiguous_profile_adjudication.csv"
    )
INSTRUCTIONS = """Goal

Decide whether a suspected unrelated compact source changes the bar-major-axis
profile enough to matter scientifically. This is a final review of the eight
fields previously labelled Ambiguous.

Workflow

1. Left-click each suspected contaminant in the Original or Corrected panel.
   Drag an existing circle to place it precisely. A new circle can also be
   dragged immediately without releasing the mouse button.
2. Adjust Mask radius so the circle covers the compact object, but as little
   surrounding galaxy structure as possible.
3. Right-click a circle to remove it; Clear masks starts the field again.
4. Inspect the corrected image and the two bar profiles. Shaded profile regions
   show samples directly intersected by a mask.
5. Use the measured maximum local change as evidence, then record Clean or
   Polluted. Add a note for borderline or unusual cases.

Suggested interpretation

Below 3%: normally Clean. Above 10%: normally Polluted. Between 3% and 10%:
compare the change with the local profile scatter and decide whether it could
alter the feature being measured. A source well outside the bar-profile aperture
may have zero impact and can be Clean even if it is visibly foreground.

The corrected view is a diagnostic only. It substitutes a broad local Gaussian
model inside each circle and never writes over the original FITS image."""


def load_image(path: Path) -> np.ndarray:
    with fits.open(path) as hdul:
        image = np.squeeze(np.asarray(hdul[0].data, dtype=float))
    if image.ndim != 2:
        raise ValueError(f"Expected a 2-D FITS image, got {image.shape}")
    return image


def smooth_model(image: np.ndarray, sigma: float) -> np.ndarray:
    finite = np.isfinite(image)
    numerator = gaussian_filter(np.where(finite, image, 0.0), sigma, mode="nearest")
    denominator = gaussian_filter(finite.astype(float), sigma, mode="nearest")
    return np.divide(numerator, denominator, out=np.full_like(image, np.nan), where=denominator > 1e-6)


def image_mask(shape: tuple[int, int], masks: list[tuple[float, float, float]]) -> np.ndarray:
    yy, xx = np.ogrid[:shape[0], :shape[1]]
    result = np.zeros(shape, dtype=bool)
    for x, y, radius in masks:
        result |= (xx - x) ** 2 + (yy - y) ** 2 <= radius ** 2
    return result


def read_saved(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["name"]: row for row in csv.DictReader(handle)}


class Adjudicator(tk.Tk):
    def __init__(self, manifest: Path, image_dir: Path, output: Path, names: list[str]):
        super().__init__()
        self.title("Ambiguous Galaxy Profile-impact Adjudicator")
        self.geometry("1550x940")
        manifest_rows = {row["name"]: row for row in display.read_manifest(manifest)}
        self.rows = [manifest_rows[name] for name in names if name in manifest_rows]
        missing = [name for name in names if name not in manifest_rows]
        if missing:
            raise ValueError(f"Names absent from geometry manifest: {', '.join(missing)}")
        self.image_dir, self.output = image_dir, output
        self.saved = read_saved(output)
        self.index = 0
        self.masks_by_name: dict[str, list[tuple[float, float, float]]] = {}
        self.image: np.ndarray | None = None
        self.geometry_data: dict[str, float] | None = None
        self.radius_var = tk.DoubleVar(value=5.0)
        self.decision_var = tk.StringVar()
        self.notes_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.status_var = tk.StringVar()
        self.metric_var = tk.StringVar()
        self.drag_mask_index: int | None = None
        self.drag_moved = False
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.load_current()

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=7)
        top.pack(fill="x")
        ttk.Button(top, text="◀ Previous", command=self.previous).pack(side="left")
        ttk.Button(top, text="Next ▶", command=self.next).pack(side="left", padx=(5, 15))
        combo = ttk.Combobox(top, textvariable=self.name_var,
                             values=[row["name"] for row in self.rows], state="readonly", width=16)
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", self.jump)
        ttk.Button(top, text="Instructions", command=self.show_instructions).pack(side="left", padx=8)
        ttk.Button(top, text="Clear masks", command=self.clear_masks).pack(side="left")
        ttk.Label(top, textvariable=self.status_var).pack(side="right")

        self.figure = Figure(figsize=(14.5, 7.3), constrained_layout=True)
        grid = self.figure.add_gridspec(2, 2, height_ratios=(3, 2))
        self.ax_original = self.figure.add_subplot(grid[0, 0])
        self.ax_corrected = self.figure.add_subplot(grid[0, 1], sharex=self.ax_original, sharey=self.ax_original)
        self.ax_profile = self.figure.add_subplot(grid[1, :])
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.pack(fill="x")
        NavigationToolbar2Tk(self.canvas, toolbar_frame).update()
        self.canvas.mpl_connect("button_press_event", self.on_button_press)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_motion)
        self.canvas.mpl_connect("button_release_event", self.on_button_release)

        controls = ttk.Frame(self, padding=8)
        controls.pack(fill="x")
        ttk.Label(controls, text="Mask radius (pixels):").grid(row=0, column=0, sticky="w")
        radius = ttk.Scale(controls, from_=2, to=20, variable=self.radius_var, command=lambda _v: self.radius_changed())
        radius.grid(row=0, column=1, sticky="ew", padx=8)
        self.radius_label = ttk.Label(controls, width=5)
        self.radius_label.grid(row=0, column=2)
        ttk.Label(controls, textvariable=self.metric_var).grid(row=0, column=3, columnspan=4, sticky="w", padx=15)
        ttk.Label(controls, text="Final decision:").grid(row=1, column=0, sticky="w", pady=(7, 0))
        for col, label in enumerate(("Clean", "Polluted"), start=1):
            ttk.Radiobutton(controls, text=label, value=label, variable=self.decision_var,
                            command=self.save_current).grid(row=1, column=col, sticky="w", pady=(7, 0))
        ttk.Label(controls, text="Notes:").grid(row=2, column=0, sticky="w", pady=(7, 0))
        notes = ttk.Entry(controls, textvariable=self.notes_var)
        notes.grid(row=2, column=1, columnspan=6, sticky="ew", pady=(7, 0))
        notes.bind("<FocusOut>", lambda _e: self.save_current())
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(6, weight=2)
        self.radius_changed(redraw=False)

    def current_name(self) -> str:
        return self.rows[self.index]["name"]

    def image_path(self) -> Path:
        return self.image_dir / f"{self.current_name()}.phot.1.fits"

    def load_current(self) -> None:
        name = self.current_name()
        self.name_var.set(name)
        path = self.image_path()
        if not path.exists():
            candidate = Path(self.rows[self.index].get("image_path", ""))
            path = candidate if candidate.exists() else path
        self.image = load_image(path)
        self.geometry_data = display.required_geometry(self.rows[self.index])
        if self.geometry_data is None:
            raise ValueError(f"Incomplete bar geometry for {name}")
        saved = self.saved.get(name, {})
        self.decision_var.set(saved.get("decision", ""))
        self.notes_var.set(saved.get("notes", ""))
        if name not in self.masks_by_name:
            encoded = saved.get("masks_x_y_radius", "")
            masks = []
            for item in encoded.split(";"):
                if item.strip():
                    x, y, r = (float(value) for value in item.split(","))
                    masks.append((x, y, r))
            self.masks_by_name[name] = masks
        reviewed = sum(bool(row.get("decision")) for row in self.saved.values())
        self.status_var.set(f"{self.index + 1}/{len(self.rows)}  |  decided {reviewed}/{len(self.rows)}")
        self.redraw()

    def corrected_and_profiles(self):
        assert self.image is not None and self.geometry_data is not None
        masks = self.masks_by_name[self.current_name()]
        mask = image_mask(self.image.shape, masks)
        sigma = max(6.0, 1.5 * max((r for _, _, r in masks), default=4.0))
        model = smooth_model(self.image, sigma)
        corrected = np.where(mask, model, self.image)
        radius_arcsec = max(2.0 * self.geometry_data["bar_sma"], 45.0)
        original_cut, x_axis, y_axis = display.deproject_bar_aligned_cutout(
            self.image, self.geometry_data, radius_arcsec)
        corrected_cut, _, _ = display.deproject_bar_aligned_cutout(
            corrected, self.geometry_data, radius_arcsec)
        mask_cut, _, _ = display.deproject_bar_aligned_cutout(
            mask.astype(float), self.geometry_data, radius_arcsec, order=0)
        half_width = max(display.DEFAULT_PROFILE_WIDTH_PIXELS * self.geometry_data["pixel_scale"] / 2.0, 1.0)
        x, original_profile = display.bar_major_axis_profile(original_cut, x_axis, y_axis, half_width)
        _, corrected_profile = display.bar_major_axis_profile(corrected_cut, x_axis, y_axis, half_width)
        _, mask_profile = display.bar_major_axis_profile(mask_cut, x_axis, y_axis, half_width)
        affected = mask_profile > 0
        bar_limit = display.bar_sma_deprojected_arcsec(self.geometry_data)
        usable = np.isfinite(original_profile) & np.isfinite(corrected_profile) & (np.abs(x) <= 1.25 * bar_limit)
        positive = original_profile[usable & (original_profile > 0)]
        floor = 0.05 * np.nanmax(positive) if positive.size else 0.0
        metric_samples = usable & affected & (original_profile > floor)
        fraction = np.abs(corrected_profile - original_profile) / np.maximum(np.abs(original_profile), floor or 1e-12)
        maximum = 100.0 * float(np.nanmax(fraction[metric_samples])) if np.any(metric_samples) else 0.0
        median = 100.0 * float(np.nanmedian(fraction[metric_samples])) if np.any(metric_samples) else 0.0
        return corrected, mask, x, original_profile, corrected_profile, affected, bar_limit, maximum, median

    def redraw(self) -> None:
        assert self.image is not None and self.geometry_data is not None
        corrected, _mask, x, p0, p1, affected, bar_limit, maximum, median = self.corrected_and_profiles()
        self.ax_original.clear(); self.ax_corrected.clear(); self.ax_profile.clear()
        log_image, levels = display.robust_log_image(self.image)
        log_corrected, _ = display.robust_log_image(corrected)
        extent_radius = max(2.0 * self.geometry_data["bar_sma"] / self.geometry_data["pixel_scale"], 45.0)
        xc, yc = self.geometry_data["xc"] - 1, self.geometry_data["yc"] - 1
        bounds = (xc - extent_radius, xc + extent_radius, yc - extent_radius, yc + extent_radius)
        for axis, shown, title in ((self.ax_original, log_image, "Original — click suspected sources"),
                                   (self.ax_corrected, log_corrected, "Correction preview")):
            axis.imshow(shown, origin="lower", cmap="gray", vmin=levels[0], vmax=levels[-1])
            axis.set_xlim(bounds[0], bounds[1]); axis.set_ylim(bounds[2], bounds[3])
            axis.set_title(title); axis.set_xlabel("image x (pixels)"); axis.set_ylabel("image y (pixels)")
            for mx, my, radius in self.masks_by_name[self.current_name()]:
                axis.add_patch(Circle((mx, my), radius, fill=False, color="cyan", linewidth=1.6))
        self.ax_profile.plot(x, p0, color="black", lw=1.4, label="Original")
        self.ax_profile.plot(x, p1, color="tab:cyan", lw=1.4, label="Candidate-masked")
        if np.any(affected):
            self.ax_profile.fill_between(x, 0, 1, where=affected, transform=self.ax_profile.get_xaxis_transform(),
                                         color="gold", alpha=0.22, label="Mask intersects aperture")
        self.ax_profile.axvline(-bar_limit, color="tab:red", ls="--", alpha=.7)
        self.ax_profile.axvline(bar_limit, color="tab:red", ls="--", alpha=.7, label="deprojected bar radius")
        self.ax_profile.set_xlim(x[0], x[-1]); self.ax_profile.set_xlabel("bar major-axis radius (arcsec)")
        self.ax_profile.set_ylabel("mean 3.6 μm intensity"); self.ax_profile.grid(alpha=.2); self.ax_profile.legend(loc="best")
        if maximum < 3: suggestion = "normally CLEAN"
        elif maximum > 10: suggestion = "normally POLLUTED"
        else: suggestion = "borderline — compare with profile scatter"
        self.metric_var.set(f"Profile impact: max {maximum:.1f}%, median {median:.1f}% — {suggestion}")
        self._last_metrics = (maximum, median)
        self.canvas.draw_idle()

    def nearest_mask(self, x: float, y: float, *, require_hit: bool) -> int | None:
        masks = self.masks_by_name[self.current_name()]
        if not masks:
            return None
        distances = [math.hypot(mx - x, my - y) for mx, my, _radius in masks]
        nearest = int(np.argmin(distances))
        if require_hit and distances[nearest] > masks[nearest][2] + 3.0:
            return None
        return nearest

    def on_button_press(self, event) -> None:
        if event.inaxes not in (self.ax_original, self.ax_corrected) or event.xdata is None or event.ydata is None:
            return
        masks = self.masks_by_name[self.current_name()]
        if event.button == 1:
            hit = self.nearest_mask(float(event.xdata), float(event.ydata), require_hit=True)
            if hit is None:
                masks.append((float(event.xdata), float(event.ydata), float(self.radius_var.get())))
                hit = len(masks) - 1
            self.drag_mask_index = hit
            self.drag_moved = False
        elif event.button == 3 and masks:
            nearest = self.nearest_mask(float(event.xdata), float(event.ydata), require_hit=True)
            if nearest is None:
                return
            masks.pop(nearest)
            self.redraw(); self.save_current()
        else:
            return
        self.redraw()

    def on_mouse_motion(self, event) -> None:
        if self.drag_mask_index is None or event.button != 1:
            return
        if event.inaxes not in (self.ax_original, self.ax_corrected) or event.xdata is None or event.ydata is None:
            return
        masks = self.masks_by_name[self.current_name()]
        if self.drag_mask_index >= len(masks):
            return
        _x, _y, radius = masks[self.drag_mask_index]
        masks[self.drag_mask_index] = (float(event.xdata), float(event.ydata), radius)
        self.drag_moved = True
        self.redraw()

    def on_button_release(self, event) -> None:
        if self.drag_mask_index is None:
            return
        if event.xdata is not None and event.ydata is not None and event.inaxes in (self.ax_original, self.ax_corrected):
            masks = self.masks_by_name[self.current_name()]
            if self.drag_mask_index < len(masks):
                _x, _y, radius = masks[self.drag_mask_index]
                masks[self.drag_mask_index] = (float(event.xdata), float(event.ydata), radius)
        self.drag_mask_index = None
        self.redraw(); self.save_current()

    def radius_changed(self, redraw: bool = True) -> None:
        value = float(self.radius_var.get())
        self.radius_label.configure(text=f"{value:.1f}")
        masks = self.masks_by_name.get(self.current_name(), []) if self.rows else []
        if masks:
            x, y, _ = masks[-1]
            masks[-1] = (x, y, value)
            if redraw and self.image is not None:
                self.redraw()

    def clear_masks(self) -> None:
        self.masks_by_name[self.current_name()] = []
        self.redraw(); self.save_current()

    def save_current(self) -> None:
        if self.image is None:
            return
        name = self.current_name()
        maximum, median = getattr(self, "_last_metrics", (0.0, 0.0))
        masks = self.masks_by_name.get(name, [])
        self.saved[name] = {
            "name": name, "decision": self.decision_var.get().strip(), "notes": self.notes_var.get().strip(),
            "mask_count": str(len(masks)), "masks_x_y_radius": ";".join(f"{x:.2f},{y:.2f},{r:.2f}" for x, y, r in masks),
            "max_local_profile_change_percent": f"{maximum:.4f}",
            "median_affected_profile_change_percent": f"{median:.4f}",
            "reviewed_at": datetime.now().isoformat(timespec="seconds"),
        }
        self.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.output.with_suffix(self.output.suffix + ".tmp")
        fields = ["name", "decision", "notes", "mask_count", "masks_x_y_radius",
                  "max_local_profile_change_percent", "median_affected_profile_change_percent", "reviewed_at"]
        with temporary.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
            for row in self.rows:
                if row["name"] in self.saved: writer.writerow(self.saved[row["name"]])
        temporary.replace(self.output)

    def previous(self) -> None:
        self.save_current(); self.index = (self.index - 1) % len(self.rows); self.load_current()

    def next(self) -> None:
        self.save_current(); self.index = (self.index + 1) % len(self.rows); self.load_current()

    def jump(self, _event=None) -> None:
        self.save_current(); selected = self.name_var.get()
        self.index = next(i for i, row in enumerate(self.rows) if row["name"] == selected); self.load_current()

    def show_instructions(self) -> None:
        messagebox.showinfo("Adjudication instructions", INSTRUCTIONS)

    def close(self) -> None:
        self.save_current(); self.destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=display.DEFAULT_MANIFEST)
    parser.add_argument("--image-dir", type=Path, default=DEFAULT_IMAGE_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--names", nargs="+", default=list(AMBIGUOUS_NAMES))
    args = parser.parse_args()
    app = Adjudicator(args.manifest, args.image_dir, args.output, args.names)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
