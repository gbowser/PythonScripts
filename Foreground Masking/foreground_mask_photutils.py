#!/usr/bin/env python3
"""
Build foreground/background compact-source masks for barred-galaxy FITS images.

The scientific product is a binary mask: 0 means usable science pixel, 1 means
masked contaminant. Optional cleaned images are only previews and should not be
used in place of mask-aware bar-profile measurements.

Examples
--------
python foreground_mask_photutils.py IC2007_deprojected_bar_aligned.fits --output-dir ./mask_outputs
python foreground_mask_photutils.py ./s4g_images_36um --glob "NGC*.fits" --limit 5 --output-dir ./mask_outputs

Required packages
-----------------
pip install astropy photutils scipy matplotlib numpy
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from photutils.segmentation import deblend_sources, detect_sources
from scipy import ndimage


def load_fits_image(path: str | Path, hdu_index: int = 0) -> tuple[np.ndarray, fits.Header]:
    """Load a FITS image and return floating-point data plus a copied header."""
    with fits.open(path) as hdul:
        data = np.asarray(hdul[hdu_index].data, dtype=float)
        header = hdul[hdu_index].header.copy()

    if data.ndim != 2:
        raise ValueError(f"Expected a 2D FITS image, got shape {data.shape}.")

    return data, header


def robust_sigma(data: np.ndarray, mask: np.ndarray | None = None) -> float:
    """Estimate robust scatter using 1.4826 times the median absolute deviation."""
    values = np.asarray(data, dtype=float)
    good = np.isfinite(values)
    if mask is not None:
        good &= ~np.asarray(mask, dtype=bool)

    sample = values[good]
    if sample.size == 0:
        raise ValueError("No finite unmasked pixels are available for sigma estimation.")

    med = np.median(sample)
    mad = np.median(np.abs(sample - med))
    sigma = 1.4826 * mad
    if not np.isfinite(sigma) or sigma <= 0:
        sigma = float(np.nanstd(sample))
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError("Could not estimate a positive finite background scatter.")

    return float(sigma)


def make_smooth_galaxy_model(data: np.ndarray, sigma_pixels: float) -> np.ndarray:
    """Create a broad Gaussian-smoothed galaxy model while preserving NaN regions."""
    if sigma_pixels <= 0:
        raise ValueError("sigma_pixels must be positive.")

    finite = np.isfinite(data)
    filled = np.where(finite, data, 0.0)
    weights = finite.astype(float)

    smooth_data = ndimage.gaussian_filter(filled, sigma=sigma_pixels, mode="nearest")
    smooth_weights = ndimage.gaussian_filter(weights, sigma=sigma_pixels, mode="nearest")

    model = np.full_like(data, np.nan, dtype=float)
    good = smooth_weights > 1.0e-6
    model[good] = smooth_data[good] / smooth_weights[good]
    return model


def make_residual_image(data: np.ndarray, smooth_model: np.ndarray) -> np.ndarray:
    """Return residual image: original image minus smooth galaxy model."""
    return np.asarray(data, dtype=float) - np.asarray(smooth_model, dtype=float)


def detect_compact_sources(
    residual: np.ndarray,
    nsigma: float = 5.0,
    npixels: int = 8,
    deblend: bool = True,
    deblend_nlevels: int = 32,
    deblend_contrast: float = 0.001,
):
    """Detect compact positive residual sources using Photutils segmentation."""
    finite = np.isfinite(residual)
    if not np.any(finite):
        return None

    residual_median = float(np.nanmedian(residual[finite]))
    sigma = robust_sigma(residual)
    threshold = residual_median + nsigma * sigma
    detection_image = np.where(finite, residual, residual_median)

    try:
        segm = detect_sources(
            detection_image,
            threshold=threshold,
            n_pixels=npixels,
            connectivity=8,
            mask=~finite,
        )
    except TypeError:
        segm = detect_sources(
            detection_image,
            threshold=threshold,
            npixels=npixels,
            connectivity=8,
            mask=~finite,
        )

    if segm is None or len(segm.labels) == 0:
        return segm

    if deblend:
        try:
            segm = deblend_sources(
                detection_image,
                segm,
                n_pixels=npixels,
                n_levels=deblend_nlevels,
                contrast=deblend_contrast,
                progress_bar=False,
            )
        except TypeError:
            segm = deblend_sources(
                detection_image,
                segm,
                npixels=npixels,
                nlevels=deblend_nlevels,
                contrast=deblend_contrast,
                progress_bar=False,
            )

    return segm


def _segment_shape_stats(segm_data: np.ndarray, label: int) -> dict[str, float]:
    yy, xx = np.nonzero(segm_data == label)
    area = int(xx.size)
    if area == 0:
        return {"area": 0, "elongation": np.inf, "x_centroid": np.nan, "y_centroid": np.nan}

    x_centroid = float(np.mean(xx))
    y_centroid = float(np.mean(yy))
    if area < 3:
        elongation = 1.0
    else:
        coords = np.column_stack((xx - x_centroid, yy - y_centroid))
        covariance = np.cov(coords, rowvar=False)
        eigenvalues = np.linalg.eigvalsh(covariance)
        eigenvalues = np.maximum(eigenvalues, 0.0)
        major = np.sqrt(eigenvalues[-1])
        minor = np.sqrt(eigenvalues[0])
        elongation = float(major / minor) if minor > 0 else np.inf

    return {
        "area": float(area),
        "elongation": elongation,
        "x_centroid": x_centroid,
        "y_centroid": y_centroid,
    }


def filter_segments(
    segm,
    data: np.ndarray,
    residual: np.ndarray,
    min_area: int | None = None,
    max_area: int | None = None,
    max_elongation: float | None = None,
    galaxy_center: tuple[float, float] | None = None,
    exclude_center_radius_pixels: float = 0.0,
    min_peak_residual_nsigma: float | None = None,
    centroid_distance_func=None,
):
    """Remove detections that are too small, too large, too elongated, or nuclear."""
    if segm is None or len(segm.labels) == 0:
        return None, []

    segm_data = np.asarray(segm.data)
    residual_sigma = robust_sigma(residual)
    residual_median = float(np.nanmedian(residual[np.isfinite(residual)]))

    kept_labels: list[int] = []
    rows: list[dict[str, float | int | bool]] = []

    for label in segm.labels:
        stats = _segment_shape_stats(segm_data, int(label))
        segment_pixels = segm_data == label
        peak_residual = float(np.nanmax(np.where(segment_pixels, residual, np.nan)))

        keep = True
        if min_area is not None and stats["area"] < min_area:
            keep = False
        if max_area is not None and stats["area"] > max_area:
            keep = False
        if max_elongation is not None and stats["elongation"] > max_elongation:
            keep = False
        if min_peak_residual_nsigma is not None:
            peak_nsigma = (peak_residual - residual_median) / residual_sigma
            if peak_nsigma < min_peak_residual_nsigma:
                keep = False

        if centroid_distance_func is not None and exclude_center_radius_pixels > 0:
            radius = float(centroid_distance_func(stats))
            if radius < exclude_center_radius_pixels:
                keep = False
        elif galaxy_center is not None and exclude_center_radius_pixels > 0:
            x0, y0 = galaxy_center
            radius = np.hypot(stats["x_centroid"] - x0, stats["y_centroid"] - y0)
            if radius < exclude_center_radius_pixels:
                keep = False
        else:
            radius = np.nan

        if keep:
            kept_labels.append(int(label))

        rows.append(
            {
                "label": int(label),
                "area": int(stats["area"]),
                "elongation": float(stats["elongation"]),
                "x_centroid": float(stats["x_centroid"]),
                "y_centroid": float(stats["y_centroid"]),
                "peak_residual": peak_residual,
                "distance_from_center": float(radius),
                "kept": bool(keep),
            }
        )

    filtered = segm.copy()
    remove_labels = sorted(set(int(label) for label in segm.labels) - set(kept_labels))
    if remove_labels:
        filtered.remove_labels(remove_labels, relabel=True)

    return filtered, rows


def segmentation_to_mask(segm, shape: tuple[int, int]) -> np.ndarray:
    """Convert a Photutils segmentation image to a boolean contaminant mask."""
    if segm is None or len(segm.labels) == 0:
        return np.zeros(shape, dtype=bool)
    return np.asarray(segm.data) > 0


def dilate_mask(mask: np.ndarray, dilation_radius_pixels: int) -> np.ndarray:
    """Dilate a mask with a circular footprint to include PSF wings."""
    mask = np.asarray(mask, dtype=bool)
    if dilation_radius_pixels <= 0:
        return mask

    radius = int(dilation_radius_pixels)
    yy, xx = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    footprint = (xx * xx + yy * yy) <= radius * radius
    return ndimage.binary_dilation(mask, structure=footprint)


def save_mask_fits(mask: np.ndarray, header: fits.Header, output_path: str | Path) -> None:
    """Save binary mask as integer FITS data with the input image geometry."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    mask_header = header.copy()
    mask_header["BUNIT"] = "mask"
    mask_header["MASKVAL"] = (1, "Masked contaminant pixel")
    mask_header["HISTORY"] = "Foreground mask created with foreground_mask_photutils.py"

    fits.PrimaryHDU(data=np.asarray(mask, dtype=np.uint8), header=mask_header).writeto(
        output_path, overwrite=True
    )


def _asinh_stretch(image: np.ndarray, lower_percentile: float = 1.0, upper_percentile: float = 99.5):
    finite = np.isfinite(image)
    if not np.any(finite):
        return np.zeros_like(image, dtype=float), 0.0, 1.0

    vmin, vmax = np.nanpercentile(image[finite], [lower_percentile, upper_percentile])
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
        vmin = float(np.nanmin(image[finite]))
        vmax = float(np.nanmax(image[finite]))
    if vmax <= vmin:
        vmax = vmin + 1.0

    scaled = (image - vmin) / (vmax - vmin)
    stretched = np.arcsinh(10.0 * np.clip(scaled, 0.0, 1.0)) / np.arcsinh(10.0)
    return stretched, vmin, vmax


def _save_image(path: Path, image: np.ndarray, title: str, cmap: str = "gray") -> None:
    display, _, _ = _asinh_stretch(image)
    fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    ax.imshow(display, origin="lower", cmap=cmap)
    ax.set_title(title)
    ax.set_axis_off()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def make_diagnostic_plots(
    data: np.ndarray,
    smooth: np.ndarray,
    residual: np.ndarray,
    mask: np.ndarray,
    output_dir: str | Path,
    prefix: str,
    segm=None,
) -> None:
    """Create diagnostic PNG images for the mask-building workflow."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _save_image(output_dir / f"{prefix}_original.png", data, "Original image")
    _save_image(output_dir / f"{prefix}_smooth_model.png", smooth, "Smooth galaxy model")
    _save_image(output_dir / f"{prefix}_residual.png", residual, "Residual image")

    candidates = np.zeros(data.shape, dtype=float) if segm is None else np.asarray(segm.data, dtype=float)
    _save_image(output_dir / f"{prefix}_candidates.png", candidates, "Candidate segmentation", cmap="viridis")

    display, _, _ = _asinh_stretch(data)
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
    fig.savefig(output_dir / f"{prefix}_before_after_comparison.png", dpi=180)
    plt.close(fig)


def make_optional_cleaned_image(data: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Fill masked pixels from nearest unmasked neighbours for visual inspection only."""
    finite_unmasked = np.isfinite(data) & ~mask
    if not np.any(finite_unmasked):
        raise ValueError("Cannot create cleaned preview: no finite unmasked pixels remain.")

    _, nearest_indices = ndimage.distance_transform_edt(~finite_unmasked, return_indices=True)
    cleaned = np.array(data, copy=True)
    fill_pixels = mask & np.isfinite(data)
    cleaned[fill_pixels] = data[tuple(index[fill_pixels] for index in nearest_indices)]
    return cleaned


def save_candidate_table(rows: list[dict[str, float | int | bool]], output_path: str | Path) -> None:
    """Save simple CSV diagnostics for segment filtering decisions."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "label",
        "area",
        "elongation",
        "x_centroid",
        "y_centroid",
        "peak_residual",
        "distance_from_center",
        "kept",
    ]
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(",".join(columns) + "\n")
        for row in rows:
            handle.write(",".join(str(row[column]) for column in columns) + "\n")


def build_foreground_mask(
    fits_path: str | Path,
    output_dir: str | Path,
    smooth_sigma_pixels: float = 15.0,
    detection_nsigma: float = 5.0,
    npixels: int = 8,
    dilation_radius_pixels: int = 3,
    deblend: bool = True,
    min_area: int | None = None,
    max_area: int | None = 500,
    max_elongation: float | None = 6.0,
    galaxy_center: tuple[float, float] | None = None,
    exclude_center_radius_pixels: float = 0.0,
    min_peak_residual_nsigma: float | None = None,
    make_cleaned: bool = False,
    hdu_index: int = 0,
) -> dict[str, Path]:
    """Run the full mask workflow and write FITS/PNG diagnostics."""
    fits_path = Path(fits_path)
    output_dir = Path(output_dir)
    prefix = fits_path.stem.replace("_deprojected_bar_aligned", "")

    data, header = load_fits_image(fits_path, hdu_index=hdu_index)
    smooth = make_smooth_galaxy_model(data, smooth_sigma_pixels)
    residual = make_residual_image(data, smooth)

    segm = detect_compact_sources(
        residual,
        nsigma=detection_nsigma,
        npixels=npixels,
        deblend=deblend,
    )
    filtered_segm, candidate_rows = filter_segments(
        segm,
        data,
        residual,
        min_area=min_area,
        max_area=max_area,
        max_elongation=max_elongation,
        galaxy_center=galaxy_center,
        exclude_center_radius_pixels=exclude_center_radius_pixels,
        min_peak_residual_nsigma=min_peak_residual_nsigma,
    )

    raw_mask = segmentation_to_mask(filtered_segm, data.shape)
    mask = dilate_mask(raw_mask, dilation_radius_pixels)

    outputs = {
        "mask": output_dir / f"{prefix}_foreground_mask.fits",
        "candidates_csv": output_dir / f"{prefix}_candidates.csv",
        "masked_preview": output_dir / f"{prefix}_masked_preview.png",
        "residual": output_dir / f"{prefix}_residual.png",
        "candidates": output_dir / f"{prefix}_candidates.png",
        "smooth_model": output_dir / f"{prefix}_smooth_model.png",
        "before_after": output_dir / f"{prefix}_before_after_comparison.png",
    }

    save_mask_fits(mask, header, outputs["mask"])
    save_candidate_table(candidate_rows, outputs["candidates_csv"])
    make_diagnostic_plots(data, smooth, residual, mask, output_dir, prefix, segm=filtered_segm)

    if make_cleaned:
        cleaned = make_optional_cleaned_image(data, mask)
        cleaned_path = output_dir / f"{prefix}_cleaned_optional.fits"
        cleaned_header = header.copy()
        cleaned_header["HISTORY"] = "Optional nearest-neighbour cleaned preview; not for science measurements"
        fits.PrimaryHDU(data=cleaned, header=cleaned_header).writeto(cleaned_path, overwrite=True)
        outputs["cleaned_optional"] = cleaned_path

    return outputs


def _parse_center(value: str | None) -> tuple[float, float] | None:
    if value is None:
        return None
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("Galaxy centre must be supplied as x,y in pixel coordinates.")
    return float(parts[0]), float(parts[1])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect compact foreground/background contaminants in galaxy FITS images."
    )
    parser.add_argument("input_path", help="Input 2D FITS image, or a folder of FITS images.")
    parser.add_argument("--output-dir", default="./mask_outputs", help="Directory for FITS/PNG outputs.")
    parser.add_argument("--glob", default="*.fits", help="Filename pattern used when input_path is a folder.")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of folder images to process.")
    parser.add_argument("--hdu-index", type=int, default=0, help="FITS HDU index containing the image.")
    parser.add_argument("--smooth-sigma-pixels", type=float, default=15.0)
    parser.add_argument("--detection-nsigma", type=float, default=5.0)
    parser.add_argument("--npixels", type=int, default=8)
    parser.add_argument("--dilation-radius-pixels", type=int, default=3)
    parser.add_argument("--no-deblend", action="store_true", help="Disable Photutils deblending.")
    parser.add_argument("--min-area", type=int, default=None, help="Minimum segment area to keep.")
    parser.add_argument("--max-area", type=int, default=500, help="Maximum segment area to keep.")
    parser.add_argument("--max-elongation", type=float, default=6.0, help="Maximum segment elongation to keep.")
    parser.add_argument(
        "--galaxy-center",
        type=_parse_center,
        default=None,
        help="Optional x,y pixel centre for nuclear exclusion.",
    )
    parser.add_argument(
        "--exclude-center-radius-pixels",
        type=float,
        default=0.0,
        help="Do not mask segments inside this radius from --galaxy-center.",
    )
    parser.add_argument(
        "--min-peak-residual-nsigma",
        type=float,
        default=None,
        help="Optional extra peak-residual significance cut.",
    )
    parser.add_argument(
        "--make-cleaned",
        action="store_true",
        help="Also write an optional nearest-neighbour cleaned preview FITS.",
    )
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
            smooth_sigma_pixels=args.smooth_sigma_pixels,
            detection_nsigma=args.detection_nsigma,
            npixels=args.npixels,
            dilation_radius_pixels=args.dilation_radius_pixels,
            deblend=not args.no_deblend,
            min_area=args.min_area,
            max_area=args.max_area,
            max_elongation=args.max_elongation,
            galaxy_center=args.galaxy_center,
            exclude_center_radius_pixels=args.exclude_center_radius_pixels,
            min_peak_residual_nsigma=args.min_peak_residual_nsigma,
            make_cleaned=args.make_cleaned,
            hdu_index=args.hdu_index,
        )
        print(f"Wrote foreground-mask outputs for {fits_path}:")
        for name, path in outputs.items():
            print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
