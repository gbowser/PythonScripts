#!/usr/bin/env python3
"""Create PNG examples showing injected toy objects from optimisation runs."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from matplotlib.patches import Circle
from scipy.ndimage import binary_dilation


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
S4G_PLOTTER_DIR = PROJECT_ROOT / "Erwin_s4g_image_downloader"
for path in (PROJECT_ROOT, SCRIPT_DIR, S4G_PLOTTER_DIR):
    if str(path) not in sys.path:
        sys.path.append(str(path))

from machine_paths import erwin_folder  # noqa: E402


DEFAULT_MANIFEST = S4G_PLOTTER_DIR / "geometry_output" / "s4g_image_geometry_manifest.csv"


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def image_path_for_pc(row: dict[str, str], pc_name: str) -> Path:
    machine_path = erwin_folder(pc_name) / "s4g_images_36um" / f"{row['name']}.phot.1.fits"
    if machine_path.exists():
        return machine_path
    manifest_path = Path(row.get("image_path", ""))
    return manifest_path


def safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in "._-" else "_" for char in value)


def robust_sigma(data: np.ndarray) -> float:
    finite = np.asarray(data, dtype=float)[np.isfinite(data)]
    if finite.size == 0:
        return 1.0
    median = float(np.nanmedian(finite))
    mad = float(np.nanmedian(np.abs(finite - median)))
    sigma = 1.4826 * mad
    if not math.isfinite(sigma) or sigma <= 0:
        sigma = float(np.nanstd(finite))
    return sigma if math.isfinite(sigma) and sigma > 0 else 1.0


def circular_kernel(radius_pixels: int) -> np.ndarray:
    radius = max(0, int(radius_pixels))
    if radius <= 0:
        return np.ones((1, 1), dtype=bool)
    yy, xx = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    return (xx * xx + yy * yy) <= radius * radius


def gaussian_model(
    shape: tuple[int, int],
    x0: float,
    y0: float,
    peak: float,
    fwhm_pixels: float,
    axis_ratio: float = 1.0,
    pa_deg: float = 0.0,
) -> np.ndarray:
    yy, xx = np.indices(shape, dtype=float)
    sigma_major = max(0.25, float(fwhm_pixels) / 2.3548)
    sigma_minor = max(0.25, sigma_major * float(axis_ratio))
    theta = math.radians(float(pa_deg))
    dx = xx - float(x0)
    dy = yy - float(y0)
    major = dx * math.cos(theta) + dy * math.sin(theta)
    minor = -dx * math.sin(theta) + dy * math.cos(theta)
    radius2 = (major / sigma_major) ** 2 + (minor / sigma_minor) ** 2
    return peak * np.exp(-0.5 * radius2)


def toy_model(
    shape: tuple[int, int],
    toy_type: str,
    x0: float,
    y0: float,
    peak: float,
    fwhm_pixels: float,
    axis_ratio: float,
    pa_deg: float,
) -> np.ndarray:
    if toy_type == "cluster":
        model = np.zeros(shape, dtype=float)
        for dx, dy, scale in [(-0.55, -0.25, 0.75), (0.45, 0.18, 0.55), (0.05, 0.65, 0.38)]:
            model += gaussian_model(shape, x0 + dx * fwhm_pixels, y0 + dy * fwhm_pixels, peak * scale, fwhm_pixels * 0.85)
        return model
    if toy_type == "galaxy":
        return gaussian_model(shape, x0, y0, peak, fwhm_pixels, axis_ratio, pa_deg)
    return gaussian_model(shape, x0, y0, peak, fwhm_pixels)


def truth_from_model(model: np.ndarray, truth_dilation: int) -> np.ndarray:
    peak = float(np.nanmax(model))
    if not math.isfinite(peak) or peak <= 0:
        return np.zeros(model.shape, dtype=bool)
    truth = model >= 0.08 * peak
    return binary_dilation(truth, structure=circular_kernel(truth_dilation))


def robust_log_image(data: np.ndarray) -> np.ndarray:
    values = np.asarray(data, dtype=float)
    finite = values[np.isfinite(values)]
    positive = finite[finite > 0]
    if positive.size == 0:
        positive = np.array([1.0])
    floor = float(np.nanpercentile(positive, 1))
    if not math.isfinite(floor) or floor <= 0:
        floor = float(np.nanmin(positive))
    return np.log10(np.where(values > floor, values, floor))


def percentile_limits(*arrays: np.ndarray, low: float = 5.0, high: float = 99.5) -> tuple[float, float]:
    finite = np.concatenate([np.asarray(array, dtype=float)[np.isfinite(array)] for array in arrays])
    if finite.size == 0:
        return 0.0, 1.0
    vmin, vmax = np.nanpercentile(finite, [low, high])
    if not math.isfinite(float(vmin)) or not math.isfinite(float(vmax)) or vmin >= vmax:
        vmin, vmax = float(np.nanmin(finite)), float(np.nanmax(finite))
    if vmin >= vmax:
        vmax = vmin + 1.0
    return float(vmin), float(vmax)


def load_run_files(run_dir: Path) -> tuple[dict[str, object], Path]:
    config_files = sorted(run_dir.glob("*toy*object*config.json")) or sorted(run_dir.glob("*config.json"))
    toy_files = sorted(run_dir.glob("*toy*object*toys.csv")) or sorted(run_dir.glob("*toys.csv"))
    if not config_files or not toy_files:
        raise FileNotFoundError(f"Could not find toy-object config/toys CSV in {run_dir}")
    with config_files[0].open(encoding="utf-8") as handle:
        config = json.load(handle)
    return config, toy_files[0]


def load_toys(path: Path) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            grouped[row["image_name"]].append(row)
    return dict(grouped)


def build_toy_arrays(data: np.ndarray, toy_rows: list[dict[str, str]], truth_dilation: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sigma = robust_sigma(data)
    toy_sum = np.zeros(data.shape, dtype=float)
    truth_mask = np.zeros(data.shape, dtype=bool)
    truth_labels = np.zeros(data.shape, dtype=np.int32)
    for row in toy_rows:
        model = toy_model(
            data.shape,
            row["object_type"],
            float(row["x"]),
            float(row["y"]),
            float(row["peak_sigma"]) * sigma,
            float(row["fwhm_pixels"]),
            float(row["axis_ratio"]),
            float(row["pa_deg"]),
        )
        truth = truth_from_model(model, truth_dilation)
        toy_sum += model
        truth_mask |= truth
        truth_labels[truth] = int(row["toy_id"])
    return toy_sum, truth_mask, truth_labels


def annotate_toys(ax: plt.Axes, toy_rows: list[dict[str, str]], scale: float) -> None:
    for row in toy_rows:
        x = float(row["x"])
        y = float(row["y"])
        radius = max(10.0, float(row["fwhm_pixels"]) * 1.8) * scale
        ax.add_patch(Circle((x, y), radius=radius, fill=False, edgecolor="tab:red", linewidth=1.4))
        ax.text(x + radius + 3, y, row["toy_id"], color="white", fontsize=8, weight="bold")


def format_table(toy_rows: list[dict[str, str]]) -> str:
    lines = ["id  type      peak sigma  FWHM px  axis ratio"]
    for row in toy_rows:
        lines.append(
            f"{int(row['toy_id']):>2}  {row['object_type']:<8}  "
            f"{float(row['peak_sigma']):>9.2f}  {float(row['fwhm_pixels']):>7.2f}  {float(row['axis_ratio']):>10.2f}"
        )
    return "\n".join(lines)


def render_example(
    output_path: Path,
    name: str,
    data: np.ndarray,
    toy_rows: list[dict[str, str]],
    truth_dilation: int,
    algorithm: str,
    detect_on: str,
) -> None:
    toy_sum, truth_mask, truth_labels = build_toy_arrays(data, toy_rows, truth_dilation)
    injected = data + toy_sum

    original_log = robust_log_image(data)
    injected_log = robust_log_image(injected)
    image_vmin, image_vmax = percentile_limits(original_log, injected_log, low=8.0, high=99.5)
    toy_vmin, toy_vmax = percentile_limits(toy_sum[toy_sum > 0], low=1.0, high=99.8)

    fig = plt.figure(figsize=(14, 10), dpi=160, constrained_layout=True)
    grid = fig.add_gridspec(2, 3, height_ratios=[1.0, 0.7])
    axes = [
        fig.add_subplot(grid[0, 0]),
        fig.add_subplot(grid[0, 1]),
        fig.add_subplot(grid[0, 2]),
        fig.add_subplot(grid[1, 0]),
        fig.add_subplot(grid[1, 1]),
        fig.add_subplot(grid[1, 2]),
    ]

    panels = [
        (axes[0], original_log, "Original image", "gray", image_vmin, image_vmax),
        (axes[1], injected_log, "Original plus injected toys", "gray", image_vmin, image_vmax),
        (axes[2], toy_sum, "Toy-object signal only", "magma", toy_vmin, toy_vmax),
        (axes[3], np.where(truth_mask, truth_labels, np.nan), "Toy-object truth mask", "tab20", None, None),
    ]
    for ax, image, title, cmap, vmin, vmax in panels:
        ax.imshow(image, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_title(title, fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
    annotate_toys(axes[0], toy_rows, 1.0)
    annotate_toys(axes[1], toy_rows, 1.0)
    annotate_toys(axes[2], toy_rows, 1.0)
    annotate_toys(axes[3], toy_rows, 1.0)

    axes[4].axis("off")
    axes[4].text(0.0, 1.0, format_table(toy_rows), va="top", family="monospace", fontsize=9)

    axes[5].axis("off")
    axes[5].text(
        0.0,
        1.0,
        (
            f"{name}\n"
            f"Algorithm run: {algorithm}\n"
            f"Detect-on setting: {detect_on}\n"
            f"Toy objects: {len(toy_rows)}\n"
            f"Truth dilation: {truth_dilation} px\n\n"
            "The optimiser scores whether the foreground-removal mask captures these known injected objects "
            "while penalising unnecessary masking outside the toy-object truth mask."
        ),
        va="top",
        wrap=True,
        fontsize=10,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.suptitle(f"{name}: injected toy-object optimisation example", fontsize=14)
    fig.savefig(output_path)
    plt.close(fig)


def infer_algorithm(run_dir: Path, toy_csv: Path) -> str:
    text = f"{run_dir.name} {toy_csv.name}".casefold()
    if "sep" in text:
        return "SEP"
    if "mtobjects" in text:
        return "MTObjects"
    return "Toy-object"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="Completed SEP or MTObjects toy-object optimisation folder.")
    parser.add_argument("--output-dir", type=Path, default=None, help="PNG output folder. Defaults to run-dir/toy_object_example_pngs.")
    parser.add_argument("--max-examples", type=int, default=4, help="Maximum number of galaxy examples to write.")
    parser.add_argument("--manifest", type=Path, default=None, help="Override manifest path.")
    parser.add_argument("--pc", default=None, help="Override PC name used to locate FITS images.")
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    config, toy_csv = load_run_files(run_dir)
    manifest = args.manifest or Path(str(config.get("manifest") or DEFAULT_MANIFEST))
    pc_name = args.pc or str(config.get("pc") or "Desktop")
    truth_dilation = int(config.get("truth_dilation") or 0)
    detect_on = str(config.get("detect_on") or "unknown")
    output_dir = args.output_dir or (run_dir / "toy_object_example_pngs")
    algorithm = infer_algorithm(run_dir, toy_csv)

    manifest_rows = {row["name"]: row for row in read_manifest(manifest)}
    grouped_toys = load_toys(toy_csv)
    written = 0
    for name, toy_rows in grouped_toys.items():
        if written >= int(args.max_examples):
            break
        row = manifest_rows.get(name)
        if row is None:
            print(f"Skipping {name}: not found in manifest.")
            continue
        image_path = image_path_for_pc(row, pc_name)
        if not image_path.exists():
            print(f"Skipping {name}: FITS image not found at {image_path}.")
            continue
        with fits.open(image_path, memmap=False) as hdul:
            data = np.asarray(hdul[0].data, dtype=float)
        output_path = output_dir / f"{safe_filename(name)}_toy_object_example.png"
        render_example(output_path, name, data, toy_rows, truth_dilation, algorithm, detect_on)
        written += 1
        print(f"Wrote {output_path}")

    print(f"Created {written} toy-object example PNG(s) in {output_dir}")


if __name__ == "__main__":
    main()
