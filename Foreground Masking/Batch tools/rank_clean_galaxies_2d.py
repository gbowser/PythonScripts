#!/usr/bin/env python3
"""Rank S4G galaxies by compact-source contamination in two dimensions.

The input image is high-pass filtered by subtracting a broad Gaussian model.
Photutils segments positive residuals outside a nuclear exclusion region.  A
dimensionless pollution score combines each segment's integrated significance,
area and distance from the galaxy centre.  Lower scores are cleaner.

The program writes a complete CSV ranking and a contact sheet of the cleanest
objects.  It does not modify any FITS image.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from photutils.detection import DAOStarFinder
from photutils.segmentation import deblend_sources, detect_sources
from scipy import ndimage


SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
for folder in (PROJECT_ROOT, FOREGROUND_ROOT, FOREGROUND_ROOT / "Shared"):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))

import foreground_display_helpers as display  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, detect_pc, remove_foreground_folder  # noqa: E402


def load_image(path: Path) -> np.ndarray:
    with fits.open(path) as hdul:
        image = np.squeeze(np.asarray(hdul[0].data, dtype=float))
    if image.ndim != 2:
        raise ValueError(f"Expected a 2-D FITS image, got {image.shape}")
    return image


def image_path(row: dict[str, str], pc_name: str | None, image_dir: Path | None) -> Path:
    """Resolve an image on Windows or from an explicitly mounted WSL directory."""
    if image_dir is not None:
        return image_dir / f"{row['name']}.phot.1.fits"
    if pc_name is None:
        raise ValueError("Either --pc or --image-dir is required")
    return display.image_path_for_pc(row, pc_name)


def nan_gaussian(image: np.ndarray, sigma: float) -> np.ndarray:
    finite = np.isfinite(image)
    numerator = ndimage.gaussian_filter(np.where(finite, image, 0.0), sigma, mode="nearest")
    denominator = ndimage.gaussian_filter(finite.astype(float), sigma, mode="nearest")
    return np.divide(numerator, denominator, out=np.full_like(image, np.nan), where=denominator > 1e-6)


def robust_location_scale(values: np.ndarray, sample_mask: np.ndarray) -> tuple[float, float]:
    sample = np.asarray(values)[sample_mask & np.isfinite(values)]
    if sample.size < 10:
        raise ValueError("Too few finite pixels for a noise estimate")
    location = float(np.median(sample))
    sigma = 1.4826 * float(np.median(np.abs(sample - location)))
    if not np.isfinite(sigma) or sigma <= 0:
        sigma = float(np.std(sample))
    if not np.isfinite(sigma) or sigma <= 0:
        raise ValueError("Could not estimate a positive residual noise")
    return location, sigma


def _detect(z_image: np.ndarray, valid: np.ndarray, threshold: float, min_pixels: int):
    safe = np.where(valid, z_image, 0.0)
    try:
        segmentation = detect_sources(safe, threshold, n_pixels=min_pixels, connectivity=8, mask=~valid)
    except TypeError:  # Photutils < 2
        segmentation = detect_sources(safe, threshold, npixels=min_pixels, connectivity=8, mask=~valid)
    if segmentation is None or len(segmentation.labels) == 0:
        return segmentation
    try:
        return deblend_sources(
            safe, segmentation, n_pixels=min_pixels, n_levels=32,
            contrast=0.001, progress_bar=False,
        )
    except TypeError:  # Photutils < 2
        return deblend_sources(
            safe, segmentation, npixels=min_pixels, nlevels=32,
            contrast=0.001, progress_bar=False,
        )


def score_image(
    image: np.ndarray,
    geometry: dict[str, float],
    *,
    blur_sigma: float,
    threshold: float,
    min_pixels: int,
    aperture_bar_radii: float,
    aperture_r25_radii: float,
    center_bar_radii: float,
    max_segment_fraction: float,
    galaxy_downweight_nsigma: float,
    max_scored_sources: int,
    inside_galaxy_weight: float,
    detector: str,
    dao_fwhm: float,
) -> tuple[dict[str, float | int], np.ndarray, np.ndarray]:
    yy, xx = np.indices(image.shape)
    x0, y0 = geometry["xc"] - 1.0, geometry["yc"] - 1.0
    radius = np.hypot(xx - x0, yy - y0)
    bar_pixels = geometry["bar_sma"] / geometry["pixel_scale"]
    r25_arcsec = float(geometry.get("r25", np.nan))
    r25_pixels = r25_arcsec / geometry["pixel_scale"] if np.isfinite(r25_arcsec) else 0.0
    aperture_radius = max(12.0, aperture_bar_radii * bar_pixels, aperture_r25_radii * r25_pixels)
    center_radius = max(3.0, center_bar_radii * bar_pixels)
    science = (radius <= aperture_radius) & (radius >= center_radius) & np.isfinite(image)

    model = nan_gaussian(image, blur_sigma)
    residual = image - model
    # Estimate noise in the analysis annulus. Iterative clipping prevents bright
    # stars from inflating the threshold and making dirty fields look clean.
    noise_sample = science.copy()
    location, sigma = robust_location_scale(residual, noise_sample)
    for _ in range(3):
        noise_sample = science & (np.abs(residual - location) < 4.0 * sigma)
        location, sigma = robust_location_scale(residual, noise_sample)
    z_image = (residual - location) / sigma

    # The same compact residual has very different meaning on blank sky and
    # inside a bright spiral arm.  Estimate the underlying galaxy brightness
    # from the broad model and continuously suppress detections embedded in it.
    model_sample = model[science & np.isfinite(model)]
    model_sky = float(np.percentile(model_sample, 20.0))
    galaxy_nsigma = np.maximum((model - model_sky) / sigma, 0.0)
    if np.isfinite(r25_arcsec) and r25_arcsec > 0:
        angle = np.radians(geometry["disk_pa"])
        major = -(xx - x0) * np.sin(angle) + (yy - y0) * np.cos(angle)
        minor = (xx - x0) * np.cos(angle) + (yy - y0) * np.sin(angle)
        cos_inclination = max(np.cos(np.radians(geometry["inclination"])), 0.15)
        disk_radius_arcsec = geometry["pixel_scale"] * np.hypot(major, minor / cos_inclination)
        # Soft edge avoids making the catalogue R25 value an artificial cliff.
        disk_transition = np.clip((disk_radius_arcsec / r25_arcsec - 0.75) / 0.5, 0.0, 1.0)
        structure_weight_image = inside_galaxy_weight + (1.0 - inside_galaxy_weight) * disk_transition
    else:
        structure_weight_image = np.ones(image.shape, dtype=float)

    if detector == "dao":
        finder = DAOStarFinder(
            threshold=threshold,
            fwhm=dao_fwhm,
            sharpness_range=(0.25, 0.85),
            roundness_range=(-0.6, 0.6),
            exclude_border=True,
        )
        table = finder(np.where(science, z_image, 0.0), mask=~science)
        labels = np.zeros(image.shape, dtype=np.int32)
        source_scores: list[float] = []
        source_areas: list[int] = []
        weighted_source_areas: list[float] = []
        if table is not None:
            marker_radius = max(2, int(math.ceil(dao_fwhm)))
            for next_label, source in enumerate(table, start=1):
                x = float(source["x_centroid"])
                y = float(source["y_centroid"])
                ix, iy = int(round(x)), int(round(y))
                source_radius = float(np.hypot(x - x0, y - y0))
                proximity = 0.5 + 0.5 * (1.0 - min(source_radius / aperture_radius, 1.0))
                local_galaxy_nsigma = float(galaxy_nsigma[iy, ix])
                galaxy_weight = 1.0 / (1.0 + local_galaxy_nsigma / galaxy_downweight_nsigma) ** 2
                structure_weight = float(structure_weight_image[iy, ix])
                flux = max(float(source["flux"]), 0.0)
                component_score = proximity * galaxy_weight * structure_weight * math.log1p(flux)
                source_scores.append(component_score)
                source_areas.append(1)
                weighted_source_areas.append(galaxy_weight * structure_weight)
                mx1, mx2 = max(0, ix - marker_radius), min(image.shape[1], ix + marker_radius + 1)
                my1, my2 = max(0, iy - marker_radius), min(image.shape[0], iy + marker_radius + 1)
                marker_y, marker_x = np.ogrid[my1:my2, mx1:mx2]
                marker = (marker_x - x) ** 2 + (marker_y - y) ** 2 <= marker_radius**2
                label_view = labels[my1:my2, mx1:mx2]
                label_view[marker] = next_label
        rejected_large = 0
    else:
        segmentation = _detect(z_image, science, threshold, min_pixels)
        labels = np.zeros(image.shape, dtype=np.int32) if segmentation is None else np.asarray(segmentation.data)
        kept = np.zeros(image.shape, dtype=np.int32)
        source_scores = []
        source_areas = []
        weighted_source_areas = []
        rejected_large = 0
        max_area = max(min_pixels, int(max_segment_fraction * np.count_nonzero(science)))
        next_label = 1
        for label in np.unique(labels):
            if label == 0:
                continue
            pixels = labels == label
            area = int(np.count_nonzero(pixels))
            if area > max_area:
                rejected_large += 1
                continue
            positive_z = np.maximum(z_image[pixels] - threshold, 0.0)
            integrated_excess = float(np.sum(positive_z))
            mean_radius = float(np.mean(radius[pixels]))
            proximity = 0.5 + 0.5 * (1.0 - min(mean_radius / aperture_radius, 1.0))
            local_galaxy_nsigma = float(np.median(galaxy_nsigma[pixels]))
            galaxy_weight = 1.0 / (1.0 + local_galaxy_nsigma / galaxy_downweight_nsigma) ** 2
            structure_weight = float(np.median(structure_weight_image[pixels]))
            component_score = (
                proximity * galaxy_weight * structure_weight
                * math.log1p(integrated_excess) * math.sqrt(area / min_pixels)
            )
            source_scores.append(component_score)
            source_areas.append(area)
            weighted_source_areas.append(area * galaxy_weight * structure_weight)
            kept[pixels] = next_label
            next_label += 1
        labels = kept

    strongest_scores = sorted(source_scores, reverse=True)[:max_scored_sources]
    source_score = float(np.sum(strongest_scores))
    coverage = float(np.sum(source_areas) / max(np.count_nonzero(science), 1))
    weighted_coverage = float(np.sum(weighted_source_areas) / max(np.count_nonzero(science), 1))
    pollution_score = source_score + 25.0 * weighted_coverage
    metrics: dict[str, float | int] = {
        "pollution_score": pollution_score,
        "source_score": source_score,
        "source_count": len(source_scores),
        "contaminated_pixels": int(np.sum(source_areas)),
        "coverage_fraction": coverage,
        "weighted_coverage_fraction": weighted_coverage,
        "residual_sigma": sigma,
        "aperture_radius_pixels": aperture_radius,
        "center_radius_pixels": center_radius,
        "rejected_large_segments": rejected_large,
    }
    return metrics, residual, labels


def save_contact_sheet(results: list[dict], output: Path, count: int) -> bool:
    selected = [row for row in results if "image" in row][:count]
    if not selected:
        return False
    columns = 5
    rows = math.ceil(len(selected) / columns)
    figure, axes = plt.subplots(rows, columns, figsize=(3.2 * columns, 3.2 * rows), squeeze=False)
    for axis in axes.ravel():
        axis.set_axis_off()
    for rank, (axis, row) in enumerate(zip(axes.ravel(), selected), start=1):
        image = row["image"]
        radius = int(math.ceil(row["aperture_radius_pixels"]))
        x0, y0 = int(round(row["x0"])), int(round(row["y0"]))
        x1, x2 = max(0, x0 - radius), min(image.shape[1], x0 + radius + 1)
        y1, y2 = max(0, y0 - radius), min(image.shape[0], y0 + radius + 1)
        view = image[y1:y2, x1:x2]
        label_view = row["labels"][y1:y2, x1:x2]
        finite = view[np.isfinite(view)]
        lo, hi = np.percentile(finite, [5, 99.5])
        axis.imshow(view, origin="lower", cmap="gray", vmin=lo, vmax=hi)
        if np.any(label_view):
            axis.contour(label_view > 0, levels=[0.5], colors="#ff4d4d", linewidths=0.6)
        circle = plt.Circle(
            (row["x0"] - x1, row["y0"] - y1), row["center_radius_pixels"],
            fill=False, color="#00d5ff", linewidth=0.8,
        )
        axis.add_patch(circle)
        axis.set_title(f"{rank}. {row['name']}\nscore {row['pollution_score']:.2f}; n={row['source_count']}", fontsize=9)
        axis.set_axis_off()
    figure.suptitle("Least polluted galaxies (red: detected contaminants; cyan: excluded centre)")
    figure.tight_layout()
    figure.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=display.DEFAULT_MANIFEST)
    parser.add_argument("--pc", choices=sorted(PC_RESEARCH_FOLDERS), help="Windows machine-path preset.")
    parser.add_argument("--image-dir", type=Path, help="Explicit FITS directory; useful for /mnt/... paths in WSL.")
    parser.add_argument("--output-dir", type=Path, help="Default: the selected PC's Remove foreground folder.")
    parser.add_argument("--cleanest", type=int, default=20)
    parser.add_argument("--names", nargs="+", help="Process only these galaxy names (diagnostic use).")
    parser.add_argument("--limit", type=int, help="Process only the first N images (for testing).")
    parser.add_argument("--blur-sigma", type=float, default=15.0)
    parser.add_argument("--threshold", type=float, default=4.0, help="Detection threshold in residual sigma.")
    parser.add_argument("--min-pixels", type=int, default=8)
    parser.add_argument("--detector", choices=("dao", "segmentation"), default="dao")
    parser.add_argument("--dao-fwhm", type=float, default=2.5, help="Expected point-source FWHM in pixels.")
    parser.add_argument("--aperture-bar-radii", type=float, default=3.0)
    parser.add_argument(
        "--aperture-r25-radii", type=float, default=1.25,
        help="Ensure the analysis field extends this far beyond the optical R25 scale.",
    )
    parser.add_argument("--center-bar-radii", type=float, default=0.35)
    parser.add_argument("--max-segment-fraction", type=float, default=0.08)
    parser.add_argument(
        "--galaxy-downweight-nsigma", type=float, default=5.0,
        help="Underlying galaxy brightness scale for suppressing internal structure; smaller is stronger.",
    )
    parser.add_argument(
        "--max-scored-sources", type=int, default=10,
        help="Score only the N strongest components, limiting accumulated galaxy-knot bias.",
    )
    parser.add_argument(
        "--inside-galaxy-weight", type=float, default=0.05,
        help="Relative weight of detections embedded well inside the R25 disk footprint.",
    )
    args = parser.parse_args()

    if args.pc is None and args.image_dir is None:
        try:
            args.pc = detect_pc(FOREGROUND_ROOT)
        except RuntimeError as exc:
            parser.error(f"{exc} In WSL, pass --image-dir /mnt/<drive>/path/to/s4g_images_36um.")
    if args.output_dir is None:
        if args.pc is None:
            parser.error("--output-dir is required when using --image-dir without --pc.")
        args.output_dir = remove_foreground_folder(args.pc) / "clean_galaxy_ranking_2d"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows = sorted(
        [row for row in display.read_manifest(args.manifest) if image_path(row, args.pc, args.image_dir).exists()],
        key=lambda row: row["name"].casefold(),
    )
    if args.names:
        requested = {name.casefold() for name in args.names}
        manifest_rows = [row for row in manifest_rows if row["name"].casefold() in requested]
    if args.limit is not None:
        manifest_rows = manifest_rows[: args.limit]
    results: list[dict] = []
    for index, row in enumerate(manifest_rows, start=1):
        name = row["name"]
        try:
            geometry = display.required_geometry(row)
            if geometry is None:
                raise ValueError("incomplete geometry")
            r25 = display.finite_float(row.get("R25_arcsec"))
            if r25 is not None:
                geometry["r25"] = r25
            fits_path = image_path(row, args.pc, args.image_dir)
            image = load_image(fits_path)
            metrics, _residual, labels = score_image(
                image, geometry, blur_sigma=args.blur_sigma, threshold=args.threshold,
                min_pixels=args.min_pixels, aperture_bar_radii=args.aperture_bar_radii,
                aperture_r25_radii=args.aperture_r25_radii,
                center_bar_radii=args.center_bar_radii,
                max_segment_fraction=args.max_segment_fraction,
                galaxy_downweight_nsigma=args.galaxy_downweight_nsigma,
                max_scored_sources=args.max_scored_sources,
                inside_galaxy_weight=args.inside_galaxy_weight,
                detector=args.detector,
                dao_fwhm=args.dao_fwhm,
            )
            results.append({
                "name": name, "status": "ok", **metrics, "image_path": str(fits_path),
                "image": image, "labels": labels, "x0": geometry["xc"] - 1.0, "y0": geometry["yc"] - 1.0,
            })
            print(f"[{index}/{len(manifest_rows)}] {name}: {metrics['pollution_score']:.3f}")
        except Exception as exc:
            results.append({"name": name, "status": "error", "error": str(exc)})
            print(f"[{index}/{len(manifest_rows)}] {name}: ERROR: {exc}")

    results.sort(key=lambda row: (row.get("status") != "ok", float(row.get("pollution_score", math.inf))))
    csv_path = args.output_dir / "clean_galaxy_ranking_2d.csv"
    fields = [
        "rank", "name", "status", "pollution_score", "source_score", "source_count",
        "contaminated_pixels", "coverage_fraction", "weighted_coverage_fraction", "residual_sigma", "aperture_radius_pixels",
        "center_radius_pixels", "rejected_large_segments", "image_path", "error",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        rank = 0
        for result in results:
            if result.get("status") == "ok":
                rank += 1
            writer.writerow({"rank": rank if result.get("status") == "ok" else "", **result})
    sheet_path = args.output_dir / f"cleanest_{args.cleanest}_contact_sheet.png"
    sheet_written = save_contact_sheet(results, sheet_path, args.cleanest)
    print(f"Wrote {csv_path}")
    if sheet_written:
        print(f"Wrote {sheet_path}")
    else:
        print("No contact sheet written because no images completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
