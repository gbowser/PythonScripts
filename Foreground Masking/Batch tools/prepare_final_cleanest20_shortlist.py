#!/usr/bin/env python3
"""Prepare a blind 30-field shortlist for final contamination-severity scoring."""

from __future__ import annotations

import argparse
import csv
import hashlib
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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def combined_labels(paths: list[Path]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for path in paths:
        if not path.exists():
            continue
        for row in read_csv(path):
            label = row.get("blind_decision") or row.get("decision") or row.get("classification") or ""
            if label:
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
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.imshow(view, origin="lower", cmap="gray", vmin=lo, vmax=hi)
    ax.set_axis_off(); ax.set_title(f"Severity field {audit_id}", fontsize=15)
    fig.tight_layout(); output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, bbox_inches="tight", facecolor="white"); plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=display.DEFAULT_MANIFEST)
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--decisions", nargs="+", type=Path, required=True)
    parser.add_argument("--phase3-selection", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--polluted-count", type=int, default=16)
    args = parser.parse_args()

    labels = combined_labels(args.decisions)
    clean = sorted(name for name, label in labels.items() if label == "Clean")
    ambiguous = sorted(name for name, label in labels.items() if label == "Ambiguous")
    similarity_rows = read_csv(args.phase3_selection)
    polluted = [row["name"] for row in similarity_rows if labels.get(row["name"]) == "Polluted"][: args.polluted_count]
    candidates = [(name, "Clean") for name in clean] + [(name, "Ambiguous") for name in ambiguous] + [(name, "Polluted-shortlist") for name in polluted]
    if len(candidates) != len(clean) + len(ambiguous) + args.polluted_count:
        raise ValueError("Not enough labelled Polluted candidates in the phase-3 similarity selection")
    candidates.sort(key=lambda item: hashlib.sha256(f"severity-v1:{item[0]}".encode()).hexdigest())
    manifest = {row["name"]: row for row in display.read_manifest(args.manifest)}
    output_rows = []
    for number, (name, group) in enumerate(candidates, start=1):
        audit_id = f"{number:02d}"
        geometry = display.required_geometry(manifest[name])
        if geometry is None:
            raise ValueError(f"Incomplete geometry for {name}")
        with fits.open(args.image_dir / f"{name}.phot.1.fits") as hdul:
            image = np.squeeze(np.asarray(hdul[0].data, dtype=float))
        save_panel(image, geometry, audit_id, args.output_dir / "panels" / f"field_{audit_id}.png")
        similarity = next((row["clean_similarity_margin"] for row in similarity_rows if row["name"] == name), "")
        output_rows.append({"audit_id": audit_id, "name": name, "input_group": group, "clean_similarity_margin": similarity})
        print(f"[{number}/{len(candidates)}] field {audit_id}", flush=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "severity_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output_rows[0])); writer.writeheader(); writer.writerows(output_rows)
    print(f"Prepared {len(output_rows)} severity fields")
    return 0


if __name__ == "__main__": raise SystemExit(main())
