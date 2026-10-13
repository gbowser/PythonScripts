"""Generate bounded ADQL for manual download of individual calibrated frames.

Offline by default. --check-availability submits bounded metadata queries only.
"""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_MANIFEST = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Clean_Galaxy_Output\euclid_geometry_manifest.csv")
DEFAULT_LIBRARY = HERE.parent / "Erwin_s4g_image_downloader" / "geometry_output" / "s4g_image_geometry_manifest.csv"
PRODUCTS = {"VIS": "DpdVisCalibratedQuadFrame", "NISP": "DpdNirCalibratedFrame"}
TARGET_COLUMNS = ["name", "ra_deg", "dec_deg", "radius_arcmin"]


def number(value, label):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def read_targets(path, manifest=False, names=None, radius_override=None):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = ["name", "center_ra_deg", "center_dec_deg", "radius_arcsec"] if manifest else TARGET_COLUMNS
        if not set(required).issubset(reader.fieldnames or []):
            raise ValueError(f"{path} must contain columns: {', '.join(required)}")
        rows = list(reader)
    selected = {name.strip().casefold() for name in names} if names else None
    targets = []
    seen = set()
    for row in rows:
        name = row["name"].strip()
        if selected is not None and name.casefold() not in selected:
            continue
        if not name or name.casefold() in seen:
            raise ValueError(f"Empty or duplicate galaxy name: {name!r}")
        seen.add(name.casefold())
        ra = number(row["center_ra_deg" if manifest else "ra_deg"], f"{name} RA")
        dec = number(row["center_dec_deg" if manifest else "dec_deg"], f"{name} Dec")
        radius = number(row["radius_arcsec" if manifest else "radius_arcmin"], f"{name} radius")
        if manifest:
            radius /= 60.0
        if radius_override is not None:
            radius = number(radius_override, "radius override")
        if not 0 <= ra < 360 or not -90 <= dec <= 90:
            raise ValueError(f"{name}: RA must be [0,360), Dec must be [-90,90], in degrees")
        if not 0 < radius <= 10800:
            raise ValueError(f"{name}: radius must be >0 and <=10800 arcminutes")
        targets.append(dict(name=name, ra_deg=ra, dec_deg=dec, radius_arcmin=radius))
    if selected is not None and selected - seen:
        raise ValueError(f"Galaxies absent from input: {', '.join(sorted(selected - seen))}")
    if not targets:
        raise ValueError("No galaxies selected")
    return targets


def build_query(targets, max_images=5, instrument="VIS", match="footprint", filter_name=None):
    if not isinstance(max_images, int) or not 1 <= max_images <= 5:
        raise ValueError("This first version permits only 1 to 5 images TOTAL")
    if instrument not in PRODUCTS or match not in ("footprint", "centre"):
        raise ValueError("Invalid instrument or cone match mode")
    if filter_name is not None and filter_name not in ("VIS", "NIR_Y", "NIR_J", "NIR_H"):
        raise ValueError("Invalid filter")
    if filter_name and (instrument == "VIS") != (filter_name == "VIS"):
        raise ValueError("Filter does not belong to the selected instrument")
    cones = []
    for target in targets:
        ra, dec, radius = target["ra_deg"], target["dec_deg"], target["radius_arcmin"] / 60.0
        circle = f"CIRCLE('ICRS', {ra:.12f}, {dec:.12f}, {radius:.12f})"
        if match == "footprint":
            cones.append(f"INTERSECTS({circle}, f.fov) = 1")
        else:
            cones.append(f"CONTAINS(POINT('ICRS', f.ra, f.dec), {circle}) = 1")
    conditions = [f"f.instrument_name = '{instrument}'", f"f.product_type = '{PRODUCTS[instrument]}'"]
    if filter_name:
        conditions.append(f"f.filter_name = '{filter_name}'")
    if match == "footprint":
        conditions.append("f.fov IS NOT NULL")
    conditions.append("(\n    " + "\n    OR ".join(cones) + "\n  )")
    # One SELECT/OR avoids multiplying a per-galaxy TOP limit or repeating frames.
    return (f"SELECT TOP {max_images} f.*\nFROM sedm.calibrated_frame AS f\nWHERE "
            + "\n  AND ".join(conditions)
            + "\nORDER BY f.observation_id, f.start_time_mjd, f.calibrated_frame_oid\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--manifest", type=Path, help="Extraction geometry manifest (default: existing Dropbox manifest)")
    source.add_argument("--targets-csv", type=Path, help="CSV: name,ra_deg,dec_deg,radius_arcmin")
    source.add_argument("--library", action="store_true", help="Use the full S4G galaxy library, transferring each centre through its original FITS WCS")
    parser.add_argument("--library-manifest", type=Path, default=DEFAULT_LIBRARY)
    parser.add_argument("--exclude", nargs="+", default=[], help="Optional galaxy names to exclude from library mode")
    parser.add_argument("--check-availability", action="store_true", help="Check each cone against public TAP; retrieve at most one metadata row per target, no images")
    parser.add_argument("--timeout", type=float, default=30, help="Metadata request timeout in seconds")
    parser.add_argument("--galaxies", nargs="+", help="Subset of input names; omit to include all")
    parser.add_argument("--radius-arcmin", type=float, help="Override the radius for every selected galaxy")
    parser.add_argument("--max-images", type=int, choices=range(1, 6), default=5, help="Total query result cap, never per galaxy")
    parser.add_argument("--instrument", choices=PRODUCTS, default="VIS")
    parser.add_argument("--filter", dest="filter_name", choices=("VIS", "NIR_Y", "NIR_J", "NIR_H"))
    parser.add_argument("--match", choices=("footprint", "centre"), default="footprint",
                        help="Footprint overlap (recommended) or frame-centre cone search")
    parser.add_argument("--output-dir", type=Path, default=HERE / "queries")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        path = args.library_manifest if args.library else args.targets_csv or args.manifest or DEFAULT_MANIFEST
        if args.exclude and not args.library:
            raise ValueError("--exclude requires --library")
        if args.timeout <= 0 or not math.isfinite(args.timeout):
            raise ValueError("--timeout must be positive and finite")
        if args.library:
            from euclid_frame_availability import library_targets
            targets = library_targets(path, args.galaxies, args.exclude, args.radius_arcmin)
        else:
            targets = read_targets(path, manifest=args.targets_csv is None,
                                   names=args.galaxies, radius_override=args.radius_arcmin)
        query = build_query(targets, args.max_images, args.instrument, args.match, args.filter_name)
        files = [args.output_dir / "individual_calibrated_frames.sql", args.output_dir / "galaxy_cones.csv"]
        if path.resolve() in [f.resolve() for f in files]:
            raise ValueError("Output files must not replace the input CSV")
        if not args.overwrite and any(f.exists() for f in files):
            raise ValueError("Query outputs already exist; use --overwrite or a new --output-dir")
        if args.check_availability:
            from euclid_frame_availability import check_availability
            report_path = args.output_dir / "frame_availability.csv"
            if report_path.exists() and not args.overwrite:
                raise ValueError("Availability report exists; use --overwrite or a new --output-dir")
            report = check_availability(targets, args.output_dir, args.instrument, args.match,
                                        args.filter_name, args.timeout)
            available = [target for target, record in zip(targets, report) if record["status"] == "available"]
            # Only offer confirmed matches for manual download after a live check.
            if available:
                query = build_query(available, args.max_images, args.instrument, args.match, args.filter_name)
            else:
                query = (f"SELECT TOP {args.max_images} f.*\nFROM sedm.calibrated_frame AS f\nWHERE 1 = 0\n")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        files[0].write_text(query, encoding="utf-8")
        with files[1].open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=TARGET_COLUMNS)
            writer.writeheader()
            writer.writerows(targets)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if not args.check_availability:
        for target in targets:
            print(f"{target['name']}: RA={target['ra_deg']:.8f} deg, Dec={target['dec_deg']:.8f} deg; radius={target['radius_arcmin']:.5f} arcmin")
    print(f"Saved {files[0]} and {files[1]}")
    print(f"Manual archive query: at most {args.max_images} calibrated {args.instrument} frame rows TOTAL.")
    if args.check_availability:
        failures = sum(record["status"] == "error" for record in report)
        print(f"Availability: {len(available)} galaxies matched; {failures} query errors. See frame_availability.csv.")
        print("Metadata queries only; no images downloaded. SQL includes confirmed matches only.")
        if failures:
            raise SystemExit(1)
    else:
        print("No archive query submitted and no images downloaded.")


if __name__ == "__main__":
    main()
