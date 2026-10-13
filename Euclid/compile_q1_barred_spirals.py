"""Compile a bounded Q1 barred-spiral candidate list with verified VIS FITS metadata.

Streams catalogue metadata until 25 suitable candidates are found; no images
are downloaded. This is a reproducible shortlist, not a complete census.
"""
import argparse
import csv
import io
import math
from datetime import datetime, timezone
from pathlib import Path

import requests

from build_euclid_frame_query import build_query

RECORD = 15106473
CATALOGUE_URL = f"https://zenodo.org/api/records/{RECORD}/files/morphology_catalogue.csv/content"
TAP_URL = "https://eas.esac.esa.int/tap-server/tap/sync"


def shortlist(session, limit):
    results = []
    inspected = 0
    with session.get(CATALOGUE_URL, stream=True, timeout=45) as response:
        response.raise_for_status()
        reader = csv.DictReader(line.decode("utf-8") for line in response.iter_lines() if line)
        for row in reader:
            inspected += 1
            try:
                disc = float(row["smooth-or-featured_featured-or-disk_fraction"])
                face_on = float(row["disk-edge-on_no_fraction"])
                arms = float(row["has-spiral-arms_yes_fraction"])
                strong = float(row["bar_strong_fraction"])
                weak = float(row["bar_weak_fraction"])
                width = float(row["cutout_width_arcsec"])
                ra, dec = float(row["right_ascension"]), float(row["declination"])
            except (ValueError, KeyError):
                continue
            if not all(math.isfinite(v) for v in (disc, face_on, arms, strong, weak, width, ra, dec)):
                continue
            if row["release_name"] != "Q1_R1" or min(disc, face_on, arms, strong + weak) < 0.8:
                continue
            if row.get("warning_galaxy_fails_training_cuts", "").lower() not in ("false", "0"):
                continue
            results.append(dict(name=f"Euclid_{row['object_id']}", object_id=row["object_id"],
                                tile_index=row["tile_index"], ra_deg=ra, dec_deg=dec,
                                radius_arcmin=width / 120, cutout_width_arcsec=width,
                                featured_fraction=disc, not_edge_on_fraction=face_on,
                                spiral_fraction=arms, strong_bar_fraction=strong,
                                weak_bar_fraction=weak, bar_fraction=strong + weak,
                                segmentation_area=row["segmentation_area"],
                                mag_segmentation=row["mag_segmentation"],
                                morphology_source=f"https://zenodo.org/records/{RECORD}"))
            if len(results) >= limit:
                break
    print(f"Selected {len(results)} candidates after inspecting {inspected} catalogue rows (not a complete catalogue scan).", flush=True)
    return results, inspected


def verify(session, targets):
    records = []
    for index, target in enumerate(targets, 1):
        circle = f"CIRCLE('ICRS', {target['ra_deg']:.12f}, {target['dec_deg']:.12f}, {target['radius_arcmin']/60:.12f})"
        point = f"POINT('ICRS', {target['ra_deg']:.12f}, {target['dec_deg']:.12f})"
        query = f"""SELECT TOP 1 f.calibrated_frame_oid, f.file_name, f.file_path,
f.product_id, f.observation_id, f.filter_name, f.release_name
FROM sedm.calibrated_frame AS f
WHERE f.instrument_name = 'VIS'
AND f.product_type = 'DpdVisCalibratedQuadFrame'
AND f.release_name = 'Q1_R1'
AND f.fov IS NOT NULL
AND INTERSECTS({circle}, f.fov) = 1
AND CONTAINS({point}, f.fov) = 1
ORDER BY f.calibrated_frame_oid
"""
        record = dict(target, status="", error="", checked_utc=datetime.now(timezone.utc).isoformat())
        try:
            response = session.post(TAP_URL, data={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query, "MAXREC": "1"}, timeout=30)
            response.raise_for_status()
            reader = csv.DictReader(io.StringIO(response.text))
            if "calibrated_frame_oid" not in (reader.fieldnames or []):
                raise ValueError(response.text[:400])
            rows = list(reader)
            if len(rows) > 1:
                raise ValueError("Unexpected excess rows")
            record["status"] = "available" if rows else "not_available"
            if rows:
                record.update(rows[0])
        except (requests.RequestException, ValueError) as exc:
            record.update(status="error", error=str(exc))
        records.append(record)
        print(f"[{index}/{len(targets)}] {target['object_id']}: {record['status']}", flush=True)
    return records


def write_csv(path, records):
    fields = list(dict.fromkeys(key for record in records for key in record))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=int, default=25)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "q1_barred_spirals")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.candidates <= 100:
        parser.error("Candidate limit must be between 1 and 100")
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.overwrite:
        parser.error("Output directory is not empty; use --overwrite")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with requests.Session() as session:
        targets, inspected = shortlist(session, args.candidates)
        if not targets:
            raise ValueError("No candidates selected")
        records = verify(session, targets)
    available = [record for record in records if record["status"] == "available"]
    write_csv(args.output_dir / "availability_checks.csv", records)
    if available:
        write_csv(args.output_dir / "verified_barred_spirals.csv", available)
        write_csv(args.output_dir / "galaxy_cones.csv", [{key: row[key] for key in ("name", "ra_deg", "dec_deg", "radius_arcmin")} for row in available])
        query = build_query(available)
        query = query.replace("  AND f.fov IS NOT NULL", "  AND f.release_name = 'Q1_R1'\n  AND f.fov IS NOT NULL")
        (args.output_dir / "manual_download_top5.sql").write_text(query)
    notes = f"""# Q1 barred spiral candidate shortlist

Selected the first {len(targets)} qualifying entries in catalogue order after
streaming {inspected} rows of Zenodo record {RECORD}; this is not an exhaustive
census or a ranking of the best/largest galaxies. {len(available)} have verified
public individual calibrated VIS FITS metadata in release Q1_R1.

Selection: expected vote fractions >=0.8 for featured/disc, not edge-on,
spiral arms, and strong+weak bar. The catalogue training-cut warning must be
false. These are automated Galaxy Zoo/Zoobot morphology candidates, not
independently visually confirmed classifications. Conditional fractions must
not be interpreted as unconditional probabilities of a galaxy being barred.

Files: verified_barred_spirals.csv holds the available list and one example
calibrated exposure per object; availability_checks.csv includes all checks.
galaxy_cones.csv can be passed to build_euclid_frame_query.py --targets-csv.
manual_download_top5.sql returns at most five exposure rows across all targets.
No FITS images have been downloaded; example frame files may be shared by many
galaxies. Footprint coverage includes the galaxy centre but does not prove the
entire galaxy is covered, or exclude detector gaps/bad pixels. Full exposures
are multi-extension files, not galaxy-centred cutouts.

The radius is half the catalogue display cutout width, converted to arcminutes;
it is NOT a measured galaxy or bar radius and is not deprojected. Object IDs
are retained as exact strings, including negative signs. No NGC/IC aliases
have been asserted. Centres are catalogue barycentres in ICRS decimal degrees.

Morphology data: https://zenodo.org/records/{RECORD}
Morphology paper: https://doi.org/10.1051/0004-6361/202555140
VIS FITS format: https://doi.org/10.1051/0004-6361/202554594
Archive: https://eas.esac.esa.int/sas/
Verified UTC: {datetime.now(timezone.utc).isoformat()}
"""
    (args.output_dir / "README.md").write_text(notes)
    print(f"Saved {len(available)} verified candidates in {args.output_dir}")
    if any(record["status"] == "error" for record in records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
