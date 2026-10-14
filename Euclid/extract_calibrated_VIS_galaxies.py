"""Extract detector-plane Q1 galaxy cutouts with SCI, RMS, FLG and native WCS.

No rotation, deprojection, resampling, or combination of exposures is applied.
Cutouts touching a quadrant boundary are trimmed and marked partial.
"""
import argparse
import csv
import math
from pathlib import Path

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_scales
import astropy.units as u

HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid Download Data")
DEFAULT_OUTPUT = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid Single Galaxies")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--targets-csv", type=Path, default=HERE / "q1_barred_spirals" / "verified_barred_spirals.csv")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--deproject-existing", action="store_true", help="Deproject saved native cutouts using the geometry CSV")
    parser.add_argument("--geometry-csv", type=Path, default=HERE / "q1_barred_spirals" / "deprojection_geometry.csv")
    args = parser.parse_args()
    if args.deproject_existing:
        from deproject_calibrated_VIS_galaxies import process_existing
        process_existing(args.output_dir, args.geometry_csv, args.overwrite)
        return
    with args.targets_csv.open(newline="", encoding="utf-8-sig") as handle:
        targets = list(csv.DictReader(handle))
    coordinates = SkyCoord([float(t["ra_deg"]) for t in targets] * u.deg,
                           [float(t["dec_deg"]) for t in targets] * u.deg)
    paths = sorted(args.input_dir.glob("*.fits"))
    if not paths:
        parser.error("No downloaded FITS exposures found")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_dir / "single_galaxy_manifest.csv"
    if manifest_path.exists() and not args.overwrite:
        parser.error("Manifest exists; use --overwrite")
    records = []
    for path in paths:
        print(f"Inspecting {path.name}", flush=True)
        with fits.open(path, memmap=True) as hdul:
            matches = {}
            for index, hdu in enumerate(hdul):
                if not hdu.name.endswith(".SCI") or len(hdu.shape) != 2:
                    continue
                wcs = WCS(hdu.header).celestial
                xx, yy = wcs.world_to_pixel(coordinates)
                height, width = hdu.shape
                for target_index, (x, y) in enumerate(zip(xx, yy)):
                    if not (np.isfinite(x) and np.isfinite(y)) or not (0 <= x < width and 0 <= y < height):
                        continue
                    margin = min(x, y, width - 1 - x, height - 1 - y)
                    if target_index not in matches or margin > matches[target_index][0]:
                        matches[target_index] = (margin, index, x, y, wcs)
            for target_index, target in enumerate(targets):
                record = dict(object_id=target["object_id"], ra_deg=target["ra_deg"],
                              dec_deg=target["dec_deg"], source_exposure=str(path.resolve()),
                              status="centre_not_on_science_detector", output_file="",
                              science_extension="", requested_width_arcsec=target["cutout_width_arcsec"],
                              centre_x_pix="", centre_y_pix="", naxis1="", naxis2="",
                              partial_quadrant_cutout="", valid_science_fraction="")
                if target_index not in matches:
                    records.append(record)
                    continue
                _, index, x, y, wcs = matches[target_index]
                science = hdul[index]
                scale = np.abs(proj_plane_pixel_scales(wcs)) * 3600
                size_x, size_y = (int(math.ceil(float(target["cutout_width_arcsec"]) / s)) for s in scale)
                raw_xmin, raw_ymin = math.floor(x - (size_x - 1) / 2), math.floor(y - (size_y - 1) / 2)
                xmin, ymin = max(0, raw_xmin), max(0, raw_ymin)
                xmax, ymax = min(science.shape[1], raw_xmin + size_x), min(science.shape[0], raw_ymin + size_y)
                partial = xmax - xmin < size_x or ymax - ymin < size_y
                slices = (slice(ymin, ymax), slice(xmin, xmax))
                header = science.header.copy()
                header.update(wcs.slice(slices).to_header(relax=True))
                for key in ("EXTNAME", "XTENSION", "PCOUNT", "GCOUNT", "EXTVER", "CHECKSUM", "DATASUM"):
                    if key in header:
                        del header[key]
                for key in ("TELESCOP", "INSTRUME", "FILTER", "DATE-OBS", "EXPTIME", "BUNIT"):
                    if key not in header and key in hdul[0].header:
                        header[key] = hdul[0].header[key]
                header["OBJECT"] = target["name"]
                header["GALID"] = target["object_id"]
                header["GALRA"] = float(target["ra_deg"])
                header["GALDEC"] = float(target["dec_deg"])
                header["CENX"] = x - xmin + 1
                header["CENY"] = y - ymin + 1
                header["SRCEXT"] = science.name
                header["SRCFILE"] = path.name
                header["PARTIAL"] = partial
                header.add_history("Native calibrated SCI cutout; no resampling or deprojection.")
                header.add_history("Requested size from Galaxy Zoo display width, not a measured bar radius.")
                data = np.array(science.section[slices], copy=True)
                output_hdus = [fits.PrimaryHDU(data, header)]
                prefix = science.name[:-4]
                for kind in ("RMS", "FLG"):
                    name = prefix + "." + kind
                    if name in hdul:
                        auxiliary = hdul[name]
                        auxiliary_header = auxiliary.header.copy()
                        auxiliary_header.update(wcs.slice(slices).to_header(relax=True))
                        for key in ("CHECKSUM", "DATASUM"):
                            if key in auxiliary_header:
                                del auxiliary_header[key]
                        output_hdus.append(fits.ImageHDU(np.array(auxiliary.section[slices], copy=True), auxiliary_header, name=kind))
                output = args.output_dir / f"{target['name']}_{path.stem}_cutout.fits"
                fits.HDUList(output_hdus).writeto(output, overwrite=args.overwrite, checksum=True)
                recovered = WCS(fits.getheader(output)).celestial.pixel_to_world(x - xmin, y - ymin)
                if recovered.separation(coordinates[target_index]).arcsec > 1e-5:
                    raise ValueError(f"WCS verification failed for {output}")
                record.update(status="extracted", output_file=str(output.resolve()),
                              science_extension=science.name, centre_x_pix=x - xmin + 1,
                              centre_y_pix=y - ymin + 1, naxis1=data.shape[1], naxis2=data.shape[0],
                              partial_quadrant_cutout=partial, valid_science_fraction=float(np.isfinite(data).mean()))
                records.append(record)
                print(f"Extracted {target['object_id']}: {data.shape}, {science.name}, partial={partial}", flush=True)
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    print(f"Saved {sum(r['status']=='extracted' for r in records)} FITS cutouts; report: {manifest_path}")


if __name__ == "__main__":
    main()
