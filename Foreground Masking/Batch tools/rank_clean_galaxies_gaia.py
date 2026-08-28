#!/usr/bin/env python3
"""Rank galaxy fields using Gaia-matched compact sources in the 3.6-um image."""

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
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table
from astropy.wcs import WCS
import astropy.units as u
from astroquery.gaia import Gaia


SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
for folder in (PROJECT_ROOT, FOREGROUND_ROOT / "Shared", SCRIPT_DIR):
    if str(folder) not in sys.path:
        sys.path.append(str(folder))

import foreground_display_helpers as display  # noqa: E402
import rank_clean_galaxies_2d as base  # noqa: E402


def load_fits(path: Path) -> tuple[np.ndarray, fits.Header]:
    with fits.open(path) as hdul:
        data = np.squeeze(np.asarray(hdul[0].data, dtype=float))
        header = hdul[0].header.copy()
    if data.ndim != 2:
        raise ValueError(f"Expected a 2-D FITS image, got {data.shape}")
    return data, header


def query_gaia(center: SkyCoord, radius_deg: float, cache_path: Path, max_g_mag: float) -> Table:
    if cache_path.exists():
        return Table.read(cache_path, format="ascii.ecsv")
    query = f"""
        SELECT source_id, ra, dec, phot_g_mean_mag, parallax, parallax_over_error,
               pmra, pmdec, pmra_error, pmdec_error, astrometric_params_solved,
               ruwe, visibility_periods_used, duplicated_source
        FROM gaiadr3.gaia_source
        WHERE 1=CONTAINS(
            POINT('ICRS', ra, dec),
            CIRCLE('ICRS', {center.ra.deg:.10f}, {center.dec.deg:.10f}, {radius_deg:.10f})
        )
        AND phot_g_mean_mag <= {max_g_mag:.3f}
        AND ruwe < 1.4
        AND visibility_periods_used >= 9
        AND astrometric_params_solved IN (31, 95)
        AND duplicated_source = 'false'
    """
    table = Gaia.launch_job_async(query, dump_to_file=False).get_results()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    table.write(cache_path, format="ascii.ecsv", overwrite=True)
    return table


def score_gaia_sources(
    image: np.ndarray,
    header: fits.Header,
    geometry: dict[str, float],
    table: Table,
    *,
    blur_sigma: float,
    aperture_bar_radii: float,
    center_bar_radii: float,
    residual_threshold: float,
    max_scored_sources: int,
    inside_structure_floor: float,
    min_astrometric_significance: float,
) -> tuple[dict[str, float | int], list[dict[str, float]], np.ndarray]:
    wcs = WCS(header).celestial
    model = base.nan_gaussian(image, blur_sigma)
    residual = image - model
    yy, xx = np.indices(image.shape)
    x0, y0 = geometry["xc"] - 1.0, geometry["yc"] - 1.0
    radius = np.hypot(xx - x0, yy - y0)
    bar_pixels = geometry["bar_sma"] / geometry["pixel_scale"]
    aperture_radius = max(12.0, aperture_bar_radii * bar_pixels)
    center_radius = max(3.0, center_bar_radii * bar_pixels)
    annulus = (radius <= aperture_radius) & (radius >= center_radius) & np.isfinite(residual)
    location, sigma = base.robust_location_scale(residual, annulus)
    for _ in range(3):
        clipped = annulus & (np.abs(residual - location) < 4.0 * sigma)
        location, sigma = base.robust_location_scale(residual, clipped)
    z_image = (residual - location) / sigma
    model_sample = model[annulus & np.isfinite(model)]
    model_sky = float(np.percentile(model_sample, 20.0))
    galaxy_nsigma = np.maximum((model - model_sky) / sigma, 0.0)

    if len(table):
        coords = SkyCoord(np.asarray(table["ra"]) * u.deg, np.asarray(table["dec"]) * u.deg)
        gx, gy = wcs.world_to_pixel(coords)
    else:
        gx, gy = np.array([]), np.array([])
    candidates: list[dict[str, float]] = []
    marker_map = np.zeros(image.shape, dtype=np.int32)
    for index, (source, x, y) in enumerate(zip(table, gx, gy), start=1):
        if not np.isfinite(x) or not np.isfinite(y):
            continue
        ix, iy = int(round(float(x))), int(round(float(y)))
        if ix < 2 or iy < 2 or ix >= image.shape[1] - 2 or iy >= image.shape[0] - 2:
            continue
        distance = float(np.hypot(x - x0, y - y0))
        if distance < center_radius or distance > aperture_radius:
            continue
        parallax_significance = (
            abs(float(source["parallax_over_error"]))
            if np.isfinite(source["parallax_over_error"]) else 0.0
        )
        pm_terms = []
        for value_name, error_name in (("pmra", "pmra_error"), ("pmdec", "pmdec_error")):
            value, error = float(source[value_name]), float(source[error_name])
            if np.isfinite(value) and np.isfinite(error) and error > 0:
                pm_terms.append((value / error) ** 2)
        proper_motion_significance = math.sqrt(sum(pm_terms)) if pm_terms else 0.0
        astrometric_significance = max(parallax_significance, proper_motion_significance)
        if astrometric_significance < min_astrometric_significance:
            continue
        cutout = z_image[iy - 2 : iy + 3, ix - 2 : ix + 3]
        peak_z = float(np.nanmax(cutout))
        if not np.isfinite(peak_z) or peak_z < residual_threshold:
            continue
        underlying = float(galaxy_nsigma[iy, ix])
        structure_weight = inside_structure_floor + (1.0 - inside_structure_floor) / (1.0 + underlying / 5.0)
        astrometric_weight = min(1.0, astrometric_significance / 10.0)
        score = astrometric_weight * structure_weight * math.log1p(peak_z - residual_threshold)
        candidates.append(
            {
                "x": float(x), "y": float(y), "peak_residual_nsigma": peak_z,
                "g_mag": float(source["phot_g_mean_mag"]), "structure_weight": structure_weight,
                "astrometric_significance": astrometric_significance,
                "score": score, "source_id": int(source["source_id"]),
            }
        )
        marker_map[max(0, iy - 3) : iy + 4, max(0, ix - 3) : ix + 4] = index
    candidates.sort(key=lambda item: item["score"], reverse=True)
    strongest = candidates[:max_scored_sources]
    pollution_score = float(sum(item["score"] for item in strongest))
    return {
        "pollution_score": pollution_score,
        "gaia_catalog_count": len(table),
        "gaia_ir_match_count": len(candidates),
        "strong_match_count": len(strongest),
        "residual_sigma": sigma,
        "aperture_radius_pixels": aperture_radius,
        "center_radius_pixels": center_radius,
    }, candidates, marker_map


def save_sheet(results: list[dict], output: Path, count: int) -> None:
    selected = results[:count]
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
        finite = view[np.isfinite(view)]
        lo, hi = np.percentile(finite, [5, 99.5])
        axis.imshow(view, origin="lower", cmap="gray", vmin=lo, vmax=hi)
        for candidate in row["candidates"]:
            color = "#ff3b30" if candidate in row["candidates"][: row["strong_match_count"]] else "#ffcc00"
            axis.add_patch(plt.Circle((candidate["x"] - x1, candidate["y"] - y1), 4, fill=False, color=color, lw=0.8))
        axis.add_patch(plt.Circle((row["x0"] - x1, row["y0"] - y1), row["center_radius_pixels"], fill=False, color="#00d5ff", lw=0.8))
        axis.set_title(f"{rank}. {row['name']}\nscore {row['pollution_score']:.2f}; matches={row['gaia_ir_match_count']}", fontsize=9)
    figure.suptitle("Gaia-assisted clean ranking (red: scored; yellow: other Gaia/IR matches)")
    figure.tight_layout()
    figure.savefig(output, dpi=160, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=display.DEFAULT_MANIFEST)
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--names", nargs="+")
    parser.add_argument("--cleanest", type=int, default=20)
    parser.add_argument("--blur-sigma", type=float, default=5.0)
    parser.add_argument("--aperture-bar-radii", type=float, default=3.0)
    parser.add_argument("--center-bar-radii", type=float, default=0.35)
    parser.add_argument("--residual-threshold", type=float, default=4.0)
    parser.add_argument("--max-scored-sources", type=int, default=5)
    parser.add_argument("--inside-structure-floor", type=float, default=0.25)
    parser.add_argument("--max-g-mag", type=float, default=20.5)
    parser.add_argument("--min-astrometric-significance", type=float, default=3.0)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = args.output_dir / "gaia_cache"
    rows = display.read_manifest(args.manifest)
    if args.names:
        names = {name.casefold() for name in args.names}
        rows = [row for row in rows if row["name"].casefold() in names]
    results: list[dict] = []
    for index, row in enumerate(rows, start=1):
        name = row["name"]
        try:
            path = args.image_dir / f"{name}.phot.1.fits"
            image, header = load_fits(path)
            geometry = display.required_geometry(row)
            if geometry is None:
                raise ValueError("incomplete geometry")
            wcs = WCS(header).celestial
            center = wcs.pixel_to_world(geometry["xc"] - 1.0, geometry["yc"] - 1.0)
            query_radius_deg = args.aperture_bar_radii * geometry["bar_sma"] / 3600.0
            table = query_gaia(center, query_radius_deg, cache_dir / f"{name}_v3.ecsv", args.max_g_mag)
            metrics, candidates, marker_map = score_gaia_sources(
                image, header, geometry, table, blur_sigma=args.blur_sigma,
                aperture_bar_radii=args.aperture_bar_radii,
                center_bar_radii=args.center_bar_radii,
                residual_threshold=args.residual_threshold,
                max_scored_sources=args.max_scored_sources,
                inside_structure_floor=args.inside_structure_floor,
                min_astrometric_significance=args.min_astrometric_significance,
            )
            results.append({"name": name, **metrics, "image": image, "candidates": candidates, "markers": marker_map, "x0": geometry["xc"] - 1.0, "y0": geometry["yc"] - 1.0})
            print(f"[{index}/{len(rows)}] {name}: {metrics['pollution_score']:.3f} ({metrics['gaia_ir_match_count']} matches)", flush=True)
        except Exception as exc:
            print(f"[{index}/{len(rows)}] {name}: ERROR: {exc}", flush=True)
    results.sort(key=lambda item: item["pollution_score"])
    fields = ["rank", "name", "pollution_score", "gaia_catalog_count", "gaia_ir_match_count", "strong_match_count", "residual_sigma", "aperture_radius_pixels", "center_radius_pixels"]
    with (args.output_dir / "clean_galaxy_ranking_gaia.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for rank, result in enumerate(results, start=1):
            writer.writerow({"rank": rank, **result})
    save_sheet(results, args.output_dir / f"cleanest_{args.cleanest}_gaia_contact_sheet.png", args.cleanest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
