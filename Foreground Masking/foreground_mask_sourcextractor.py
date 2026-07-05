#!/usr/bin/env python3
"""
Python-controlled SourceXtractor++ foreground-object masking workflow.

The scientific product is a binary contaminant mask:

    0 = usable galaxy pixel
    1 = masked foreground/background contaminant pixel

SourceXtractor++ performs the source detection and segmentation. Python handles
FITS preparation, optional residual-image detection, segment filtering, mask
dilation, FITS mask writing, and diagnostic PNGs.

Examples
--------
python foreground_mask_sourcextractor.py IC2007_deprojected_bar_aligned.fits --output-dir ./sourcex_mask_outputs
python foreground_mask_sourcextractor.py ./s4g_images_36um --glob "NGC*.fits" --limit 5 --output-dir ./sourcex_mask_outputs

SourceXtractor++ installation note
----------------------------------
SourceXtractor++ is installed separately from these Python dependencies. One
common Conda route is:

    conda create -n sourcex -c astrorama -c conda-forge sourcextractor
    conda activate sourcex
    sourcextractor++ --help

On Windows you may prefer to run SourceXtractor++ inside WSL2 or a Linux Conda
environment. In that case, pass the executable through --sourcextractor-cmd,
for example --sourcextractor-cmd "wsl sourcextractor++".
"""

from __future__ import annotations

import argparse
import csv
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from scipy import ndimage


def load_fits_image(path: str | Path, hdu_index: int = 0) -> tuple[np.ndarray, fits.Header]:
    """Load a 2D FITS image and return floating-point data plus a copied header."""
    with fits.open(path) as hdul:
        data = np.asarray(hdul[hdu_index].data, dtype=float)
        header = hdul[hdu_index].header.copy()

    if data.ndim != 2:
        raise ValueError(f"Expected a 2D FITS image, got shape {data.shape}.")
    return data, header


def robust_sigma(data: np.ndarray, mask: np.ndarray | None = None) -> float:
    """Estimate robust scatter with 1.4826 times the median absolute deviation."""
    values = np.asarray(data, dtype=float)
    good = np.isfinite(values)
    if mask is not None:
        good &= ~np.asarray(mask, dtype=bool)
    sample = values[good]
    if sample.size == 0:
        raise ValueError("No finite pixels are available for robust sigma estimation.")

    median = np.median(sample)
    mad = np.median(np.abs(sample - median))
    sigma = 1.4826 * mad
    if not np.isfinite(sigma) or sigma <= 0:
        sigma = float(np.nanstd(sample))
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError("Could not estimate a positive finite scatter.")
    return float(sigma)


def make_smooth_galaxy_model(data: np.ndarray, sigma_pixels: float) -> np.ndarray:
    """Build a broad Gaussian-smoothed galaxy model without spreading NaNs."""
    if sigma_pixels <= 0:
        raise ValueError("smooth_sigma_pixels must be positive.")

    finite = np.isfinite(data)
    filled = np.where(finite, data, 0.0)
    weights = finite.astype(float)
    smooth_data = ndimage.gaussian_filter(filled, sigma=sigma_pixels, mode="nearest")
    smooth_weights = ndimage.gaussian_filter(weights, sigma=sigma_pixels, mode="nearest")

    model = np.full_like(data, np.nan, dtype=float)
    supported = smooth_weights > 1.0e-6
    model[supported] = smooth_data[supported] / smooth_weights[supported]
    return model


def prepare_detection_image(
    data: np.ndarray,
    mode: str = "original",
    smooth_sigma_pixels: float = 15.0,
) -> tuple[np.ndarray, np.ndarray | None]:
    """Prepare an original or residual image for SourceXtractor++ detection."""
    if mode not in {"original", "residual"}:
        raise ValueError("mode must be 'original' or 'residual'.")

    if mode == "original":
        detection = np.array(data, dtype=float, copy=True)
        residual = None
    else:
        smooth = make_smooth_galaxy_model(data, smooth_sigma_pixels)
        residual = data - smooth
        detection = np.array(residual, dtype=float, copy=True)

    finite = np.isfinite(detection)
    if not np.any(finite):
        raise ValueError("Detection image contains no finite pixels.")

    safe_background = float(np.nanmedian(detection[finite]))
    detection[~finite] = safe_background
    return detection, residual


def write_temp_fits(data: np.ndarray, header: fits.Header, path: str | Path) -> None:
    """Write a temporary or intermediate FITS image for SourceXtractor++."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out_header = header.copy()
    out_header["HISTORY"] = "Temporary SourceXtractor++ detection image"
    fits.PrimaryHDU(data=np.asarray(data, dtype=np.float32), header=out_header).writeto(
        output_path, overwrite=True
    )


def write_sourcextractor_config(path: str | Path) -> None:
    """Write a minimal, commented SourceXtractor++ config placeholder.

    SourceXtractor++ configuration syntax can differ between packaged versions.
    This file is intentionally conservative: use it as a local starting point or
    pass a tested config with --sourcex-config. The Python wrapper supplies the
    input image and output filenames through command-line arguments.
    """
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "\n".join(
            [
                "# SourceXtractor++ configuration placeholder.",
                "# Keep local detection/deblending/measurement settings here if your",
                "# installation expects a config file. The Python wrapper passes image,",
                "# catalog, segmentation, and optional check-image filenames on the CLI.",
                "#",
                "# Example local settings to consider, depending on your installed",
                "# SourceXtractor++ version:",
                "#   detection threshold / min area",
                "#   deblending levels and contrast",
                "#   output catalogue columns",
                "#   check-image products",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _split_command(command: str) -> list[str]:
    """Split an executable command, allowing values such as 'wsl sourcextractor++'."""
    if not command.strip():
        raise ValueError("SourceXtractor++ command cannot be empty.")
    return shlex.split(command, posix=False)


def check_sourcextractor_available(sourcextractor_cmd: str) -> bool:
    """Return True if the first executable token is available on PATH."""
    parts = _split_command(sourcextractor_cmd)
    executable = parts[0]
    if executable.lower() == "wsl":
        return shutil.which(executable) is not None
    return shutil.which(executable) is not None


def build_sourcextractor_command(
    input_fits: str | Path,
    output_catalog: str | Path,
    segmentation_fits: str | Path,
    background_fits: str | Path | None = None,
    filtered_fits: str | Path | None = None,
    thresholded_fits: str | Path | None = None,
    config_path: str | Path | None = None,
    sourcextractor_cmd: str = "sourcextractor++",
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build the SourceXtractor++ command-line call.

    The default switches are deliberately explicit and easy to override. If a
    local SourceXtractor++ build uses different option names, provide them with
    --sourcex-arg and/or a tested --sourcex-config.
    """
    command = _split_command(sourcextractor_cmd)
    command.extend(
        [
            "--detection-image",
            str(input_fits),
            "--output-catalog-filename",
            str(output_catalog),
            "--output-catalog-format",
            "FITS",
            "--segmentation-image",
            str(segmentation_fits),
        ]
    )

    if config_path is not None:
        command.extend(["--config-file", str(config_path)])
    if background_fits is not None:
        command.extend(["--background-image", str(background_fits)])
    if filtered_fits is not None:
        command.extend(["--filtered-image", str(filtered_fits)])
    if thresholded_fits is not None:
        command.extend(["--thresholded-image", str(thresholded_fits)])
    if extra_args:
        command.extend(extra_args)
    return command


def run_sourcextractor(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run SourceXtractor++ and capture stdout/stderr for concise diagnostics."""
    try:
        return subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "SourceXtractor++ executable was not found. Install it separately or pass "
            "--sourcextractor-cmd with the correct executable, for example "
            '"--sourcextractor-cmd sourcextractor++" or "--sourcextractor-cmd \\"wsl sourcextractor++\\"".'
        ) from exc
    except subprocess.CalledProcessError as exc:
        message = [
            "SourceXtractor++ failed.",
            f"Command: {shlex.join(command)}",
            f"Return code: {exc.returncode}",
        ]
        if exc.stdout:
            message.extend(["stdout:", exc.stdout])
        if exc.stderr:
            message.extend(["stderr:", exc.stderr])
        raise RuntimeError("\n".join(message)) from exc


def read_segmentation_map(segmentation_fits: str | Path, hdu_index: int = 0) -> np.ndarray:
    """Read the SourceXtractor++ segmentation check-image."""
    segmentation = fits.getdata(segmentation_fits, ext=hdu_index)
    if segmentation.ndim != 2:
        raise ValueError(f"Expected a 2D segmentation image, got shape {segmentation.shape}.")
    return np.asarray(segmentation)


def segmentation_to_mask(segmentation: np.ndarray) -> np.ndarray:
    """Convert non-zero segmentation labels to a boolean contaminant mask."""
    return np.asarray(segmentation) > 0


def _segment_shape_stats(segmentation: np.ndarray, label: int) -> dict[str, float]:
    yy, xx = np.nonzero(segmentation == label)
    area = int(xx.size)
    if area == 0:
        return {
            "area": 0.0,
            "xmin": np.nan,
            "xmax": np.nan,
            "ymin": np.nan,
            "ymax": np.nan,
            "x_centroid": np.nan,
            "y_centroid": np.nan,
            "elongation": np.inf,
            "compactness": 0.0,
        }

    x_centroid = float(np.mean(xx))
    y_centroid = float(np.mean(yy))
    xmin = int(np.min(xx))
    xmax = int(np.max(xx))
    ymin = int(np.min(yy))
    ymax = int(np.max(yy))
    bbox_area = float((xmax - xmin + 1) * (ymax - ymin + 1))
    compactness = float(area / bbox_area) if bbox_area > 0 else 0.0

    if area < 3:
        elongation = 1.0
    else:
        coords = np.column_stack((xx - x_centroid, yy - y_centroid))
        covariance = np.cov(coords, rowvar=False)
        eigenvalues = np.maximum(np.linalg.eigvalsh(covariance), 0.0)
        major = np.sqrt(eigenvalues[-1])
        minor = np.sqrt(eigenvalues[0])
        elongation = float(major / minor) if minor > 0 else np.inf

    return {
        "area": float(area),
        "xmin": float(xmin),
        "xmax": float(xmax),
        "ymin": float(ymin),
        "ymax": float(ymax),
        "x_centroid": x_centroid,
        "y_centroid": y_centroid,
        "elongation": elongation,
        "compactness": compactness,
    }


def measure_segments(
    segmentation: np.ndarray,
    science_data: np.ndarray,
    residual_data: np.ndarray | None = None,
    galaxy_centre: tuple[float, float] | None = None,
) -> list[dict[str, float | int]]:
    """Measure area, centroid, peak value, elongation, compactness, and bbox."""
    labels = sorted(int(label) for label in np.unique(segmentation) if label > 0)
    rows: list[dict[str, float | int]] = []
    residual_sigma = robust_sigma(residual_data) if residual_data is not None else np.nan
    residual_median = (
        float(np.nanmedian(residual_data[np.isfinite(residual_data)])) if residual_data is not None else np.nan
    )

    for label in labels:
        segment_pixels = segmentation == label
        stats = _segment_shape_stats(segmentation, label)
        peak_value = float(np.nanmax(np.where(segment_pixels, science_data, np.nan)))

        if residual_data is not None:
            mean_residual = float(np.nanmean(np.where(segment_pixels, residual_data, np.nan)))
            peak_residual = float(np.nanmax(np.where(segment_pixels, residual_data, np.nan)))
            peak_residual_nsigma = (
                (peak_residual - residual_median) / residual_sigma
                if np.isfinite(residual_sigma) and residual_sigma > 0
                else np.nan
            )
        else:
            mean_residual = np.nan
            peak_residual = np.nan
            peak_residual_nsigma = np.nan

        if galaxy_centre is None:
            distance_from_center = np.nan
        else:
            x0, y0 = galaxy_centre
            distance_from_center = float(np.hypot(stats["x_centroid"] - x0, stats["y_centroid"] - y0))

        rows.append(
            {
                "label": label,
                "area": int(stats["area"]),
                "xmin": int(stats["xmin"]),
                "xmax": int(stats["xmax"]),
                "ymin": int(stats["ymin"]),
                "ymax": int(stats["ymax"]),
                "x_centroid": float(stats["x_centroid"]),
                "y_centroid": float(stats["y_centroid"]),
                "peak_value": peak_value,
                "mean_residual": mean_residual,
                "peak_residual": peak_residual,
                "peak_residual_nsigma": float(peak_residual_nsigma),
                "elongation": float(stats["elongation"]),
                "compactness": float(stats["compactness"]),
                "distance_from_center": distance_from_center,
            }
        )

    return rows


def filter_segments(
    segmentation: np.ndarray,
    properties: list[dict[str, float | int]],
    min_area: int | None = 5,
    max_area: int | None = 500,
    max_elongation: float | None = None,
    min_compactness: float | None = None,
    exclude_central_radius: float = 0.0,
    mask_large_objects: bool = False,
) -> tuple[np.ndarray, list[dict[str, float | int | bool]]]:
    """Filter unwanted detections before creating the binary mask."""
    kept_labels: set[int] = set()
    rows: list[dict[str, float | int | bool]] = []

    for row in properties:
        label = int(row["label"])
        keep = True
        if min_area is not None and int(row["area"]) < min_area:
            keep = False
        if max_area is not None and not mask_large_objects and int(row["area"]) > max_area:
            keep = False
        if max_elongation is not None and float(row["elongation"]) > max_elongation:
            keep = False
        if min_compactness is not None and float(row["compactness"]) < min_compactness:
            keep = False
        if exclude_central_radius > 0:
            distance = float(row["distance_from_center"])
            if np.isfinite(distance) and distance < exclude_central_radius:
                keep = False

        if keep:
            kept_labels.add(label)
        updated = dict(row)
        updated["kept"] = keep
        rows.append(updated)

    filtered = np.where(np.isin(segmentation, list(kept_labels)), segmentation, 0)
    return filtered, rows


def dilate_mask(mask: np.ndarray, radius_pixels: int) -> np.ndarray:
    """Dilate the binary source mask to include PSF wings."""
    mask = np.asarray(mask, dtype=bool)
    if radius_pixels <= 0:
        return mask
    radius = int(radius_pixels)
    yy, xx = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    footprint = (xx * xx + yy * yy) <= radius * radius
    return ndimage.binary_dilation(mask, structure=footprint)


def save_mask_fits(mask: np.ndarray, header: fits.Header, output_path: str | Path) -> None:
    """Save final mask as FITS with 0/1 unsigned integer values."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mask_header = header.copy()
    mask_header["BUNIT"] = "mask"
    mask_header["MASKVAL"] = (1, "Masked contaminant pixel")
    mask_header["HISTORY"] = "Foreground mask created with foreground_mask_sourcextractor.py"
    fits.PrimaryHDU(data=np.asarray(mask, dtype=np.uint8), header=mask_header).writeto(
        output_path, overwrite=True
    )


def save_segment_table(rows: list[dict[str, float | int | bool]], output_path: str | Path) -> None:
    """Save measured segment properties and keep/reject decisions as CSV."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "label",
        "area",
        "xmin",
        "xmax",
        "ymin",
        "ymax",
        "x_centroid",
        "y_centroid",
        "peak_value",
        "mean_residual",
        "peak_residual",
        "peak_residual_nsigma",
        "elongation",
        "compactness",
        "distance_from_center",
        "kept",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _stretch(image: np.ndarray, lower_percentile: float = 1.0, upper_percentile: float = 99.0):
    finite = np.isfinite(image)
    if not np.any(finite):
        return np.zeros_like(image, dtype=float)
    vmin, vmax = np.nanpercentile(image[finite], [lower_percentile, upper_percentile])
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
        vmin = float(np.nanmin(image[finite]))
        vmax = float(np.nanmax(image[finite]))
    if vmax <= vmin:
        vmax = vmin + 1.0
    scaled = np.clip((image - vmin) / (vmax - vmin), 0.0, 1.0)
    return np.arcsinh(10.0 * scaled) / np.arcsinh(10.0)


def _save_png(path: Path, image: np.ndarray, title: str, cmap: str = "gray") -> None:
    fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    ax.imshow(image, origin="lower", cmap=cmap)
    ax.set_title(title)
    ax.set_axis_off()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def make_diagnostic_plots(
    data: np.ndarray,
    segmentation: np.ndarray,
    mask: np.ndarray,
    output_dir: str | Path,
    prefix: str,
    residual: np.ndarray | None = None,
    background: np.ndarray | None = None,
    filtered: np.ndarray | None = None,
    thresholded: np.ndarray | None = None,
) -> None:
    """Create PNG diagnostics showing original image, segmentation, and mask."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    display = _stretch(data)
    _save_png(output_dir / f"{prefix}_original.png", display, "Original image")
    _save_png(
        output_dir / f"{prefix}_segmentation_preview.png",
        np.asarray(segmentation, dtype=float),
        "SourceXtractor++ segmentation",
        cmap="viridis",
    )
    _save_png(output_dir / f"{prefix}_foreground_mask_preview.png", mask.astype(float), "Final binary mask")

    overlay = np.ma.masked_where(~mask, mask)
    fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    ax.imshow(display, origin="lower", cmap="gray")
    ax.imshow(overlay, origin="lower", cmap="autumn", alpha=0.45, vmin=0, vmax=1)
    ax.set_title("Original image with contaminant mask")
    ax.set_axis_off()
    fig.savefig(output_dir / f"{prefix}_masked_preview.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 6), constrained_layout=True)
    axes[0].imshow(display, origin="lower", cmap="gray")
    axes[0].set_title("Original")
    axes[0].set_axis_off()
    axes[1].imshow(display, origin="lower", cmap="gray")
    axes[1].imshow(overlay, origin="lower", cmap="autumn", alpha=0.45, vmin=0, vmax=1)
    axes[1].set_title("Mask overlay")
    axes[1].set_axis_off()
    fig.savefig(output_dir / f"{prefix}_detection_diagnostics.png", dpi=180)
    plt.close(fig)

    if residual is not None:
        _save_png(output_dir / f"{prefix}_residual.png", _stretch(residual), "Residual detection image")
    if background is not None:
        _save_png(output_dir / f"{prefix}_sourcex_background.png", _stretch(background), "SourceXtractor++ background")
    if filtered is not None:
        _save_png(output_dir / f"{prefix}_sourcex_filtered.png", _stretch(filtered), "SourceXtractor++ filtered image")
    if thresholded is not None:
        _save_png(
            output_dir / f"{prefix}_sourcex_thresholded.png",
            _stretch(thresholded),
            "SourceXtractor++ thresholded image",
        )


def _read_optional_fits(path: Path | None) -> np.ndarray | None:
    if path is None or not path.exists():
        return None
    return np.asarray(fits.getdata(path), dtype=float)


def _parse_galaxy_centre(value: str | None, shape: tuple[int, int]) -> tuple[float, float] | None:
    if value is None or value.lower() == "none":
        return None
    if value.lower() == "auto":
        ny, nx = shape
        return (0.5 * (nx - 1), 0.5 * (ny - 1))
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("Galaxy centre must be 'auto', 'none', or x,y.")
    return float(parts[0]), float(parts[1])


def build_foreground_mask(
    fits_path: str | Path,
    output_dir: str | Path,
    sourcextractor_cmd: str = "sourcextractor++",
    detect_on: str = "original",
    smooth_sigma_pixels: float = 15.0,
    dilation_radius: int = 3,
    min_area: int | None = 5,
    max_area: int | None = 500,
    max_elongation: float | None = None,
    min_compactness: float | None = None,
    mask_large_objects: bool = False,
    exclude_central_radius: float = 10.0,
    galaxy_centre: str | None = "auto",
    save_intermediate: bool = False,
    overwrite: bool = False,
    hdu_index: int = 0,
    sourcex_config: str | Path | None = None,
    write_default_config: bool = False,
    extra_sourcex_args: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Path | int | float]:
    """Run the full SourceXtractor++ mask workflow for one FITS image."""
    fits_path = Path(fits_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = fits_path.stem.replace("_deprojected_bar_aligned", "")

    data, header = load_fits_image(fits_path, hdu_index=hdu_index)
    detection_data, residual = prepare_detection_image(data, detect_on, smooth_sigma_pixels)
    centre = _parse_galaxy_centre(galaxy_centre, data.shape)

    outputs: dict[str, Path | int | float] = {
        "catalog": output_dir / f"{prefix}_sourcex_catalog.fits",
        "segmentation": output_dir / f"{prefix}_sourcex_segmentation.fits",
        "mask": output_dir / f"{prefix}_foreground_mask.fits",
        "segments_csv": output_dir / f"{prefix}_sourcex_segments.csv",
        "masked_preview": output_dir / f"{prefix}_masked_preview.png",
        "segmentation_preview": output_dir / f"{prefix}_segmentation_preview.png",
        "detection_diagnostics": output_dir / f"{prefix}_detection_diagnostics.png",
    }

    for key in ("catalog", "segmentation", "mask"):
        output_path = Path(outputs[key])
        if output_path.exists() and not overwrite:
            raise FileExistsError(f"{output_path} exists. Use --overwrite to replace existing outputs.")

    if sourcex_config is None and write_default_config:
        sourcex_config = output_dir / f"{prefix}_sourcextractor_default_config.py"
        write_sourcextractor_config(sourcex_config)

    background_fits = output_dir / f"{prefix}_sourcex_background.fits" if save_intermediate else None
    filtered_fits = output_dir / f"{prefix}_sourcex_filtered.fits" if save_intermediate else None
    thresholded_fits = output_dir / f"{prefix}_sourcex_thresholded.fits" if save_intermediate else None

    temp_context = tempfile.TemporaryDirectory() if not save_intermediate else None
    try:
        if save_intermediate:
            detection_fits = output_dir / f"{prefix}_sourcex_detection_input.fits"
        else:
            assert temp_context is not None
            detection_fits = Path(temp_context.name) / f"{prefix}_sourcex_detection_input.fits"
        write_temp_fits(detection_data, header, detection_fits)

        command = build_sourcextractor_command(
            detection_fits,
            Path(outputs["catalog"]),
            Path(outputs["segmentation"]),
            background_fits=background_fits,
            filtered_fits=filtered_fits,
            thresholded_fits=thresholded_fits,
            config_path=sourcex_config,
            sourcextractor_cmd=sourcextractor_cmd,
            extra_args=extra_sourcex_args,
        )

        if dry_run:
            print(shlex.join(command))
            outputs["dry_run"] = 1
            return outputs

        if not check_sourcextractor_available(sourcextractor_cmd):
            raise RuntimeError(
                f"SourceXtractor++ command is not available: {sourcextractor_cmd!r}. "
                "Install SourceXtractor++ separately or pass --sourcextractor-cmd."
            )

        result = run_sourcextractor(command)
        if result.stdout.strip():
            print(result.stdout.strip())
        if result.stderr.strip():
            print(result.stderr.strip())

        segmentation = read_segmentation_map(Path(outputs["segmentation"]))
        if segmentation.shape != data.shape:
            raise ValueError(
                f"Segmentation shape {segmentation.shape} does not match science image shape {data.shape}."
            )

        properties = measure_segments(segmentation, data, residual_data=residual, galaxy_centre=centre)
        filtered_segmentation, segment_rows = filter_segments(
            segmentation,
            properties,
            min_area=min_area,
            max_area=max_area,
            max_elongation=max_elongation,
            min_compactness=min_compactness,
            exclude_central_radius=exclude_central_radius,
            mask_large_objects=mask_large_objects,
        )
        raw_mask = segmentation_to_mask(filtered_segmentation)
        finite_science = np.isfinite(data)
        mask = dilate_mask(raw_mask, dilation_radius) & finite_science

        save_mask_fits(mask, header, Path(outputs["mask"]))
        save_segment_table(segment_rows, Path(outputs["segments_csv"]))
        make_diagnostic_plots(
            data,
            filtered_segmentation,
            mask,
            output_dir,
            prefix,
            residual=residual,
            background=_read_optional_fits(background_fits),
            filtered=_read_optional_fits(filtered_fits),
            thresholded=_read_optional_fits(thresholded_fits),
        )

        detected = len(properties)
        retained = sum(1 for row in segment_rows if bool(row["kept"]))
        finite_pixels = int(np.sum(finite_science))
        masked_pixels = int(np.sum(mask & finite_science))
        masked_fraction = masked_pixels / finite_pixels if finite_pixels else np.nan
        outputs["detected_segments"] = detected
        outputs["retained_segments"] = retained
        outputs["masked_fraction"] = float(masked_fraction)
        return outputs
    finally:
        if temp_context is not None:
            temp_context.cleanup()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compact-source contaminant masks using SourceXtractor++ segmentation."
    )
    parser.add_argument("input_path", help="Input 2D FITS image, or a folder of FITS images.")
    parser.add_argument("--output-dir", default="./sourcex_mask_outputs")
    parser.add_argument("--glob", default="*.fits", help="Folder-mode filename pattern.")
    parser.add_argument("--limit", type=int, default=None, help="Optional folder-mode file limit.")
    parser.add_argument("--hdu-index", type=int, default=0)
    parser.add_argument("--sourcextractor-cmd", default="sourcextractor++")
    parser.add_argument("--sourcex-config", default=None, help="Optional tested SourceXtractor++ config file.")
    parser.add_argument(
        "--write-default-config",
        action="store_true",
        help="Write a commented placeholder config beside outputs and pass it to SourceXtractor++.",
    )
    parser.add_argument(
        "--sourcex-arg",
        action="append",
        default=[],
        help="Extra SourceXtractor++ argument token. Repeat for multiple tokens.",
    )
    parser.add_argument("--detect-on", choices=["original", "residual"], default="original")
    parser.add_argument("--smooth-sigma-pixels", type=float, default=15.0)
    parser.add_argument("--dilation-radius", type=int, default=3)
    parser.add_argument("--min-area", type=int, default=5)
    parser.add_argument("--max-area", type=int, default=500)
    parser.add_argument("--max-elongation", type=float, default=None)
    parser.add_argument("--min-compactness", type=float, default=None)
    parser.add_argument("--mask-large-objects", action="store_true")
    parser.add_argument("--exclude-central-radius", type=float, default=10.0)
    parser.add_argument("--galaxy-centre", default="auto", help="auto, none, or x,y pixel coordinates.")
    parser.add_argument("--save-intermediate", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Print SourceXtractor++ command without running it.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input_path)
    if input_path.is_dir():
        fits_paths = sorted(input_path.glob(args.glob))
        if args.limit is not None:
            fits_paths = fits_paths[: args.limit]
        if not fits_paths:
            raise FileNotFoundError(f"No files matching {args.glob!r} found in {input_path}.")
    else:
        fits_paths = [input_path]

    for fits_path in fits_paths:
        outputs = build_foreground_mask(
            fits_path,
            args.output_dir,
            sourcextractor_cmd=args.sourcextractor_cmd,
            detect_on=args.detect_on,
            smooth_sigma_pixels=args.smooth_sigma_pixels,
            dilation_radius=args.dilation_radius,
            min_area=args.min_area,
            max_area=args.max_area,
            max_elongation=args.max_elongation,
            min_compactness=args.min_compactness,
            mask_large_objects=args.mask_large_objects,
            exclude_central_radius=args.exclude_central_radius,
            galaxy_centre=args.galaxy_centre,
            save_intermediate=args.save_intermediate,
            overwrite=args.overwrite,
            hdu_index=args.hdu_index,
            sourcex_config=args.sourcex_config,
            write_default_config=args.write_default_config,
            extra_sourcex_args=args.sourcex_arg,
            dry_run=args.dry_run,
        )
        print(f"SourceXtractor++ mask workflow for {fits_path}:")
        for key, value in outputs.items():
            if key == "masked_fraction":
                print(f"  {key}: {100.0 * float(value):.3f}% of finite pixels")
            else:
                print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
