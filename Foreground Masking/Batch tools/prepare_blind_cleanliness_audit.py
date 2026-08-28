#!/usr/bin/env python3
"""Prepare an original-image-only, identity-hidden cleanliness consistency audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits


SCRIPT_DIR = Path(__file__).resolve().parent
SHARED_DIR = SCRIPT_DIR.parent / "Shared"
if str(SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(SHARED_DIR))
import foreground_display_helpers as display  # noqa: E402


GORDON_NAMES = {
    "IC1954", "NGC0289", "NGC0986", "NGC1097", "NGC1367", "NGC2903",
    "NGC3486", "NGC3681", "NGC4133", "NGC4450", "NGC7531",
}


def csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def prior_labels(paths: list[Path]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for path in paths:
        for row in csv_rows(path):
            label = row.get("blind_decision") or row.get("decision") or row.get("classification") or ""
            if label in {"Clean", "Polluted"}:
                labels[row["name"]] = label
    return labels


def save_panel(image: np.ndarray, geometry: dict[str, float], audit_id: str, output: Path) -> None:
    x0, y0 = geometry["xc"] - 1.0, geometry["yc"] - 1.0
    radius = max(12.0, 3.0 * geometry["bar_sma"] / geometry["pixel_scale"])
    x1, x2 = max(0, int(x0 - radius)), min(image.shape[1], int(x0 + radius + 1))
    y1, y2 = max(0, int(y0 - radius)), min(image.shape[0], int(y0 + radius + 1))
    view = image[y1:y2, x1:x2]
    finite = view[np.isfinite(view)]
    lo, hi = np.percentile(finite, [5.0, 99.5])
    figure, axis = plt.subplots(figsize=(7, 7))
    axis.imshow(view, origin="lower", cmap="gray", vmin=lo, vmax=hi)
    axis.set_axis_off()
    axis.set_title(f"Blind field {audit_id}", fontsize=15)
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=display.DEFAULT_MANIFEST)
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, nargs="+", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--remaining", action="store_true",
        help="Prepare every manifest galaxy absent from all supplied decision files.",
    )
    args = parser.parse_args()

    labels = prior_labels(args.decisions)
    manifest = {row["name"]: row for row in display.read_manifest(args.manifest)}
    if args.remaining:
        selected = set(manifest) - set(labels)
    else:
        clean = {name for name, label in labels.items() if label == "Clean"}
        selected = clean | GORDON_NAMES
    missing = sorted(selected - manifest.keys())
    if missing:
        raise ValueError(f"Missing manifest rows: {', '.join(missing)}")
    # A deterministic hash gives a reproducible shuffle without encoding the
    # previous class or catalogue rank in the presentation order.
    ordered = sorted(selected, key=lambda name: hashlib.sha256(f"blind-audit-v1:{name}".encode()).hexdigest())
    output_rows = []
    for number, name in enumerate(ordered, start=1):
        audit_id = f"{number:02d}"
        row = manifest[name]
        geometry = display.required_geometry(row)
        if geometry is None:
            raise ValueError(f"Incomplete geometry for {name}")
        with fits.open(args.image_dir / f"{name}.phot.1.fits") as hdul:
            image = np.squeeze(np.asarray(hdul[0].data, dtype=float))
        save_panel(image, geometry, audit_id, args.output_dir / "panels" / f"field_{audit_id}.png")
        previous = labels.get(name, "Unreviewed")
        if args.remaining:
            source = "previously unreviewed"
        else:
            source = "Gordon" if name in GORDON_NAMES else "confirmed-clean reference"
        output_rows.append({"audit_id": audit_id, "name": name, "previous_label": previous, "source": source})
        print(f"[{number}/{len(ordered)}] field {audit_id}", flush=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "blind_audit_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0]))
        writer.writeheader(); writer.writerows(output_rows)
    print(f"Prepared {len(output_rows)} blind fields in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
