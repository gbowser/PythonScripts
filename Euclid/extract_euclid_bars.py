"""Extract Euclid galaxies using the S4G catalogue geometry and bar display radius.

Source images are read through FITS sections, never converted in their entirety.
The aligned FITS has physical offset axes, not a fictitious celestial WCS.
"""
from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from scipy.ndimage import map_coordinates

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / "Foreground Masking"
sys.path.insert(0, str(ROOT / "Shared"))
import foreground_display_helpers as display

DEFAULT_INPUT = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid Sample Data\bars")
DEFAULT_OUTPUT = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Clean_Galaxy_Output")


def celestial_wcs(header):
    """Follow the existing GUI policy for undeclared SIP in resampled images."""
    cleaned = header.copy()
    if not any("-SIP" in str(cleaned.get(f"CTYPE{i}", "")) for i in (1, 2)):
        for key in list(cleaned):
            if re.match(r"^(A|B|AP|BP)_(ORDER|DMAX|\d+_\d+)$", key):
                del cleaned[key]
    return WCS(cleaned).celestial


def local_pixel_matrix(wcs, centre, xc, yc):
    """Pixel offsets to west/north arcseconds at the galaxy centre."""
    columns = []
    for dx, dy in ((1, 0), (0, 1)):
        east, north = centre.spherical_offsets_to(wcs.pixel_to_world(xc + dx, yc + dy))
        columns.append((-east.arcsec, north.arcsec))
    return np.asarray(columns).T


def extract(path, row, output, overwrite=False):
    geometry = display.required_geometry(row)
    if geometry is None:
        raise ValueError(f"{path.stem}: incomplete source geometry")
    source = Path(row["image_path"])
    if not source.is_file():
        raise FileNotFoundError(f"Original S4G FITS needed to transfer centre: {source}")
    source_wcs = celestial_wcs(fits.getheader(source))
    centre = source_wcs.pixel_to_world(geometry["xc"] - 1, geometry["yc"] - 1)
    observed_path = output / f"{path.stem}_observed.fits"
    aligned_path = output / f"{path.stem}_bar_aligned.fits"
    if not overwrite and (observed_path.exists() or aligned_path.exists()):
        raise FileExistsError(f"Outputs already exist for {path.stem}; use --overwrite")
    with fits.open(path, memmap=True) as hdul:
        hdu = hdul[0]
        if int(hdu.header.get("NAXIS", 0)) != 2:
            raise ValueError(f"{path}: primary HDU must contain a 2D image")
        header = hdu.header.copy()
        wcs = celestial_wcs(header)
        xc, yc = (float(v) for v in wcs.world_to_pixel(centre))
        height, width = hdu.shape
        if not (0 <= xc < width and 0 <= yc < height):
            raise ValueError(f"{path.stem}: transferred centre lies outside Euclid image")
        matrix = local_pixel_matrix(wcs, centre, xc, yc)
        scale = float(np.linalg.norm(matrix[:, 1]))
        geometry.update(xc=xc + 1, yc=yc + 1, pixel_scale=scale)
        # Same radius policy as the interactive tool, using the full-image bounds.
        bounds = type("ImageBounds", (), {"shape": (height, width)})()
        radius = display.profile_radius_pixels(bounds, geometry)
        transform = display.image_transform(geometry["disk_pa"], geometry["inclination"], geometry["bar_pa"])
        # Account for the local Euclid WCS rotation and handedness before deprojection.
        transform = transform @ (matrix / scale)
        sign = 1.0 if transform[1, 1] >= 0 else -1.0
        transform *= sign
        inverse = np.linalg.inv(transform)
        corners = np.array([[-radius, -radius, radius, radius], [-radius, radius, -radius, radius]])
        footprint = inverse @ corners
        xmin = max(0, math.floor(xc + min(-radius, footprint[0].min())) - 2)
        xmax = min(width, math.ceil(xc + max(radius, footprint[0].max())) + 3)
        ymin = max(0, math.floor(yc + min(-radius, footprint[1].min())) - 2)
        ymax = min(height, math.ceil(yc + max(radius, footprint[1].max())) + 3)
        data = np.array(hdu.section[ymin:ymax, xmin:xmax], dtype=np.float32)
    finite = np.isfinite(data)
    filled = np.where(finite, data, 0)
    support = finite.astype(np.float32)
    axis = np.arange(-radius, radius + 1, dtype=float)
    aligned = np.empty((len(axis), len(axis)), dtype=np.float32)
    # Process strips so even the largest bar does not require full coordinate grids.
    for start in range(0, len(axis), 128):
        xx, yy = np.meshgrid(axis, axis[start:start + 128])
        offsets = inverse @ np.vstack((xx.ravel(), yy.ravel()))
        coordinates = [offsets[1].reshape(xx.shape) + yc - ymin,
                       offsets[0].reshape(xx.shape) + xc - xmin]
        sampled = map_coordinates(filled, coordinates, order=1, mode="constant", cval=0, prefilter=False)
        valid = map_coordinates(support, coordinates, order=0, mode="constant", cval=0)
        aligned[start:start + len(yy)] = np.where(valid > 0.5, sampled, np.nan)
    observed_header = wcs.slice((slice(ymin, ymax), slice(xmin, xmax))).to_header(relax=True)
    for key in ("BUNIT", "FILTER", "TELESCOP", "INSTRUME"):
        if key in header:
            observed_header[key] = header[key]
    fits.writeto(observed_path, data, observed_header, overwrite=overwrite)
    aligned_header = fits.Header()
    for index in (1, 2):
        aligned_header[f"CTYPE{index}"] = "LINEAR"
        aligned_header[f"CUNIT{index}"] = "arcsec"
        aligned_header[f"CRPIX{index}"] = radius + 1
        aligned_header[f"CRVAL{index}"] = 0.0
        aligned_header[f"CDELT{index}"] = scale
    for key, value in (("OBJECT", path.stem), ("DISKPA", geometry["disk_pa"]),
                       ("INCL", geometry["inclination"]), ("BARPA", geometry["bar_pa"]),
                       ("BARSMA", geometry["bar_sma"]), ("VIEWRAD", radius * scale),
                       ("CENRA", centre.ra.deg), ("CENDEC", centre.dec.deg), ("ORIENT", sign)):
        aligned_header[key] = value
    if "BUNIT" in header:
        aligned_header["BUNIT"] = header["BUNIT"]
    aligned_header.add_history("S4G centre transferred through celestial WCS; disc deprojected.")
    aligned_header.add_history("Bar aligned with x axis; offsets are in the deprojected plane.")
    fits.writeto(aligned_path, aligned, aligned_header, overwrite=overwrite)
    result = dict(row)
    result.update(name=path.stem, image_path=str(observed_path.resolve()), image_exists=True,
                  source_euclid_image=str(path.resolve()), source_s4g_image=str(source),
                  aligned_image_path=str(aligned_path.resolve()),
                  center_x_pix=xc - xmin + 1, center_y_pix=yc - ymin + 1,
                  euclid_full_center_x_pix=xc + 1, euclid_full_center_y_pix=yc + 1,
                  center_ra_deg=centre.ra.deg, center_dec_deg=centre.dec.deg,
                  image_naxis1=data.shape[1], image_naxis2=data.shape[0],
                  pixel_scale_arcsec_x=float(np.linalg.norm(matrix[:, 0])), pixel_scale_arcsec_y=scale,
                  crpix1=observed_header["CRPIX1"], crpix2=observed_header["CRPIX2"],
                  crval1_deg=observed_header["CRVAL1"], crval2_deg=observed_header["CRVAL2"],
                  image_pa_axis2_deg=math.degrees(math.atan2(-matrix[0, 1], matrix[1, 1])),
                  radius_pixels=radius, radius_arcsec=radius * scale,
                  aligned_center_x_pix=radius + 1, aligned_center_y_pix=radius + 1,
                  aligned_naxis1=len(axis), aligned_naxis2=len(axis),
                  cutout_origin_x_zero_based=xmin, cutout_origin_y_zero_based=ymin,
                  orientation_sign=sign, centre_source="Salo/S4G pixel centre -> S4G WCS -> Euclid WCS")
    for i in range(2):
        for j in range(2):
            result[f"observed_to_aligned_{i}{j}"] = transform[i, j]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--source-manifest", type=Path, default=display.DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--galaxies", nargs="+", help="Optional galaxy names, e.g. NGC1255")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    rows = {r["name"].upper(): r for r in display.read_manifest(args.source_manifest)}
    paths = sorted(args.input_dir.glob("*.fits"))
    if args.galaxies:
        selected = {name.upper() for name in args.galaxies}
        paths = [p for p in paths if p.stem.upper() in selected]
        missing = selected - {p.stem.upper() for p in paths}
        if missing:
            parser.error(f"Requested FITS images missing: {sorted(missing)}")
    if not paths:
        parser.error("No matching FITS images found")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = args.output_dir / "euclid_geometry_manifest.csv"
    if manifest.exists() and not args.overwrite:
        parser.error("Manifest already exists; use --overwrite or a new output directory")
    results = []
    for path in paths:
        if path.stem.upper() not in rows:
            raise ValueError(f"No catalogue geometry for {path.stem}")
        print(f"Extracting {path.stem} ...", flush=True)
        result = extract(path, rows[path.stem.upper()], args.output_dir, args.overwrite)
        result["source_geometry_manifest"] = str(args.source_manifest.resolve())
        results.append(result)
        print(f"  radius {result['radius_arcsec']:.2f} arcsec; aligned shape {result['aligned_naxis1']} squared", flush=True)
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved {manifest}")


if __name__ == "__main__":
    main()
