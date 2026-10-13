"""Full-library coordinates and sequential, bounded Euclid availability checks."""
from __future__ import annotations

import csv
import io
import warnings
from datetime import datetime, timezone
from pathlib import Path

import requests
from astropy.io import fits
from astropy.wcs import FITSFixedWarning

from build_euclid_frame_query import build_query, number

TAP_URL = "https://eas.esac.esa.int/tap-server/tap/sync"
FIELDS = ["name", "ra_deg", "dec_deg", "radius_arcmin", "instrument", "match_mode",
          "status", "calibrated_frame_oid", "file_name", "file_path", "product_id",
          "observation_id", "filter_name", "checked_utc", "error"]


def library_targets(path, names=None, exclude=(), radius_override=None):
    from extract_euclid_bars import celestial_wcs
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    wanted = {name.casefold() for name in names} if names else None
    excluded = {name.casefold() for name in exclude}
    all_names = {row["name"].casefold() for row in rows}
    missing = ((wanted or set()) | excluded) - all_names
    if missing:
        raise ValueError(f"Names absent from library: {sorted(missing)}")
    targets = []
    seen = set()
    for row in rows:
        name = row["name"]
        if name.casefold() in excluded or (wanted is not None and name.casefold() not in wanted):
            continue
        if name.casefold() in seen:
            raise ValueError(f"Duplicate library galaxy: {name}")
        seen.add(name.casefold())
        image = Path(row["image_path"])
        if not image.is_file():
            raise ValueError(f"{name}: original FITS needed for sky centre: {image}")
        xc = number(row["center_x_pix"], f"{name} centre x")
        yc = number(row["center_y_pix"], f"{name} centre y")
        bar = number(row["bar_sma_arcsec"], f"{name} bar semi-major axis")
        radius = number(radius_override, "radius override") if radius_override is not None else max(3 * bar, 45) / 60
        if not 0 < radius <= 10800:
            raise ValueError(f"{name}: radius must be >0 and <=10800 arcmin")
        # Read headers only, removing undeclared SIP in the same way as extraction.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FITSFixedWarning)
            wcs = celestial_wcs(fits.getheader(image))
        centre = wcs.pixel_to_world(xc - 1, yc - 1).icrs
        ra = number(centre.ra.deg, f"{name} RA")
        dec = number(centre.dec.deg, f"{name} Dec")
        targets.append(dict(name=name, ra_deg=ra, dec_deg=dec, radius_arcmin=radius))
    if not targets:
        raise ValueError("No library galaxies selected")
    print(f"Loaded {len(targets)} library galaxies; centres from original S4G WCS.", flush=True)
    return targets


def check_availability(targets, output_dir, instrument="VIS", match="footprint", filter_name=None, timeout=30):
    output_dir.mkdir(parents=True, exist_ok=True)
    report = []
    # One request at a time; a single metadata match is enough to prove availability.
    with requests.Session() as session:
        for index, target in enumerate(targets, 1):
            record = {field: "" for field in FIELDS}
            record.update(target, instrument=instrument, match_mode=match,
                          checked_utc=datetime.now(timezone.utc).isoformat())
            query = build_query([target], 1, instrument, match, filter_name)
            try:
                response = session.post(TAP_URL, data={"REQUEST": "doQuery", "LANG": "ADQL",
                                        "FORMAT": "csv", "QUERY": query, "MAXREC": "1"}, timeout=timeout)
                response.raise_for_status()
                reader = csv.DictReader(io.StringIO(response.text))
                if "calibrated_frame_oid" not in (reader.fieldnames or []):
                    raise ValueError(f"Unexpected TAP response: {response.text[:500]}")
                rows = list(reader)
                if len(rows) > 1:
                    raise ValueError("TAP response exceeded the one-row metadata limit")
                record["status"] = "available" if rows else "not_available"
                if rows:
                    for field in ("calibrated_frame_oid", "file_name", "file_path", "product_id", "observation_id", "filter_name"):
                        record[field] = rows[0].get(field, "")
            except (requests.RequestException, ValueError, csv.Error) as exc:
                record.update(status="error", error=str(exc))
            report.append(record)
            # Checkpoint after every galaxy so interrupted scans retain completed results.
            temporary = output_dir / "frame_availability.csv.tmp"
            with temporary.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(report)
            temporary.replace(output_dir / "frame_availability.csv")
            print(f"[{index}/{len(targets)}] {target['name']}: {record['status']}", flush=True)
    return report
