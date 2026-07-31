#!/usr/bin/env python3
"""Build one six-panel comparison PNG per galaxy from existing batch reports.

The compositor uses standalone per-method bar-major profile PNGs when they
are recorded in the batch summaries.  Older batches remain supported by
falling back to crops of their full report PNGs. The output layout is:

1. galaxy-centred original image,
2. original bar-major profile,
3. SEP processed bar-major profile using Spike Gate parameters,
4. SEP processed bar-major profile using toy-object parameters,
5. MTObjects processed bar-major profile using Spike Gate parameters,
6. MTObjects processed bar-major profile using toy-object parameters.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
import sys
import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = FOREGROUND_ROOT.parent
SUPPORT_DIRS = tuple(FOREGROUND_ROOT / name for name in ("Batch tools", "PhotUtils", "Interactive tools", "Shared", "Utilities"))
for path in (PROJECT_ROOT, FOREGROUND_ROOT, SCRIPT_DIR, *SUPPORT_DIRS):
    if str(path) not in sys.path:
        sys.path.append(str(path))

from machine_paths import PC_RESEARCH_FOLDERS, detect_pc, remove_foreground_folder


PANEL_W = 900
PANEL_H = 860
TITLE_H = 56
GAP = 34
PAGE_MARGIN = 46
TARGET_PLOT_LEFT = 120
TARGET_PLOT_RIGHT = PANEL_W - TARGET_PLOT_LEFT
TARGET_X0 = PANEL_W // 2
BACKGROUND = "white"
PANEL_BORDER = (215, 220, 226)
TITLE_COLOR = (20, 28, 38)
PLACEHOLDER_COLOR = (245, 247, 250)


def newest_summary(root: Path, patterns: tuple[str, ...]) -> Path:
    """Return the newest full-sized batch summary matching any pattern.

    Batch summaries are written incrementally, so modification time alone can
    select an interrupted partial run.  Prefer summaries with the largest row
    count, then use modification time to select the newest completed run.
    """
    candidates = {
        path.resolve()
        for pattern in patterns
        for path in root.glob(pattern)
        if path.is_file()
    }
    if not candidates:
        return root / "missing_batch_summary.csv"
    row_counts: dict[Path, int] = {}
    for path in candidates:
        try:
            with path.open(newline="", encoding="utf-8-sig") as handle:
                row_counts[path] = sum(1 for _ in csv.DictReader(handle))
        except (OSError, csv.Error):
            row_counts[path] = 0
    largest = max(row_counts.values())
    full_summaries = [path for path, count in row_counts.items() if count == largest]
    return max(full_summaries, key=lambda path: path.stat().st_mtime)


def default_paths(pc_name: str) -> dict[str, Path]:
    root = remove_foreground_folder(pc_name)
    return {
        "mtobjects_spike": newest_summary(
            root,
            (
                "mtobjects optimised foreground removal/spike-gate/*/mtobjects_optimised_apply_summary.csv",
                "mtobjects all galaxy batch/mtobjects_spike_gate_*/mtobjects_optimised_apply_summary.csv",
            ),
        ),
        "mtobjects_toy": newest_summary(
            root,
            (
                "mtobjects optimised foreground removal/toy-object/*/mtobjects_optimised_apply_summary.csv",
                "mtobjects all galaxy batch/mtobjects_toy_object_*/mtobjects_optimised_apply_summary.csv",
            ),
        ),
        "sep_spike": newest_summary(
            root,
            ("SEP all galaxy batch/sep_spike_gate_*/sep_optimised_apply_summary.csv",),
        ),
        "sep_toy": newest_summary(
            root,
            ("SEP all galaxy batch/sep_toy_object_*/sep_optimised_apply_summary.csv",),
        ),
        "output": root / "all method galaxy comparison panels",
    }


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    font_dir = Path("C:/Windows/Fonts")
    candidates = [
        font_dir / ("arialbd.ttf" if bold else "arial.ttf"),
        font_dir / ("segoeuib.ttf" if bold else "segoeui.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def load_summary(path: Path, image_field: str = "report_png") -> dict[str, Path]:
    if not path.is_file():
        return {}
    rows: dict[str, Path] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("status", "")).lower() != "ok":
                continue
            name = row.get("name") or row.get("image")
            report = row.get(image_field)
            if not name or not report:
                continue
            report_path = Path(report)
            if report_path.is_file():
                rows[name] = report_path
    return rows


def crop_box(image: Image.Image, layout: str, panel: str) -> tuple[int, int, int, int]:
    width, height = image.size
    if layout == "mtobjects":
        boxes = {
            "original": (0.055, 0.085, 0.485, 0.370),
            "original_profile": (0.055, 0.745, 0.485, 0.982),
            "processed_profile": (0.525, 0.725, 0.965, 0.982),
        }
    elif layout == "sep":
        boxes = {
            # The SEP report's processed profile occupies the full lower-right
            # subplot.  The previous 0.885 right edge clipped its positive-x
            # side before alignment, making x=0 appear far to the right.
            "processed_profile": (0.515, 0.810, 0.990, 1.000),
        }
    else:
        raise ValueError(f"Unknown layout: {layout}")
    left, top, right, bottom = boxes[panel]
    return (int(left * width), int(top * height), int(right * width), int(bottom * height))


def crop_report(path: Path | None, layout: str, panel: str) -> Image.Image | None:
    if path is None or not path.is_file():
        return None
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        return rgb.crop(crop_box(rgb, layout, panel))


def load_image(path: Path | None) -> Image.Image | None:
    if path is None or not path.is_file():
        return None
    with Image.open(path) as image:
        return image.convert("RGB")


def longest_true_run(values: np.ndarray) -> int:
    best = 0
    current = 0
    for value in values:
        if bool(value):
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def detect_plot_box(image: Image.Image) -> tuple[int, int, int, int] | None:
    arr = np.asarray(image.convert("RGB"))
    dark = (arr[:, :, 0] < 90) & (arr[:, :, 1] < 90) & (arr[:, :, 2] < 90)
    height, width = dark.shape
    col_runs = np.array([longest_true_run(dark[:, x]) for x in range(width)])
    row_runs = np.array([longest_true_run(dark[y, :]) for y in range(height)])
    cols = np.where(col_runs > 0.25 * height)[0]
    rows = np.where(row_runs > 0.25 * width)[0]
    if not len(cols) or not len(rows):
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]), int(rows[-1])


def normalise_x_axis(crop: Image.Image) -> Image.Image:
    contained_size = (PANEL_W - 28, PANEL_H - TITLE_H - 22)
    plot_box = detect_plot_box(crop)
    if plot_box is None:
        return ImageOps.contain(crop, contained_size, method=Image.Resampling.LANCZOS)

    left, _top, right, _bottom = plot_box
    plot_width = max(1.0, float(right - left))
    source_x0 = left + 0.5 * plot_width
    target_plot_width = TARGET_PLOT_RIGHT - TARGET_PLOT_LEFT
    scale = target_plot_width / plot_width
    resized_width = max(1, int(round(crop.width * scale)))
    resized_height = max(1, int(round(crop.height * scale)))
    if scale <= 0 or scale > 4.0 or resized_width * resized_height > 12_000_000:
        return ImageOps.contain(crop, contained_size, method=Image.Resampling.LANCZOS)

    resized = crop.resize(
        (resized_width, resized_height),
        Image.Resampling.LANCZOS,
    )
    # All source profiles use symmetric limits around x=0.  Mapping the full
    # detected axes rectangle onto one fixed target rectangle therefore puts
    # x=0 at the panel centre and vertically aligns all three rows.
    paste_x = int(round(TARGET_X0 - source_x0 * scale))
    available_height = PANEL_H - TITLE_H - 18
    paste_y = TITLE_H + max(0, (available_height - resized.height) // 2)

    canvas = Image.new("RGB", (PANEL_W, PANEL_H - TITLE_H), BACKGROUND)
    canvas.paste(resized, (paste_x, max(0, paste_y - TITLE_H)))
    return canvas


def make_placeholder(title: str, detail: str) -> Image.Image:
    image = Image.new("RGB", (PANEL_W, PANEL_H), PLACEHOLDER_COLOR)
    draw = ImageDraw.Draw(image)
    title_font = load_font(28, bold=True)
    text_font = load_font(22)
    lines = [title, "", *textwrap.wrap(detail, width=42)]
    y = PANEL_H // 2 - 55
    for index, line in enumerate(lines):
        font = title_font if index == 0 else text_font
        box = draw.textbbox((0, 0), line, font=font)
        draw.text(((PANEL_W - (box[2] - box[0])) // 2, y), line, fill=(95, 105, 120), font=font)
        y += 34 if index == 0 else 28
    return image


def fit_panel(
    crop: Image.Image | None,
    title: str,
    missing_detail: str,
    *,
    normalise_axes: bool = True,
) -> Image.Image:
    title_font = load_font(30, bold=True)
    canvas = Image.new("RGB", (PANEL_W, PANEL_H), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    title_box = draw.textbbox((0, 0), title, font=title_font)
    draw.text(((PANEL_W - (title_box[2] - title_box[0])) // 2, 14), title, fill=TITLE_COLOR, font=title_font)
    if crop is None:
        content = make_placeholder(title, missing_detail).crop((0, TITLE_H, PANEL_W, PANEL_H))
    elif not normalise_axes:
        content = ImageOps.contain(
            crop,
            (PANEL_W - 28, PANEL_H - TITLE_H - 22),
            method=Image.Resampling.LANCZOS,
        )
    else:
        content = normalise_x_axis(crop)
    x = (PANEL_W - content.width) // 2
    y = TITLE_H + (PANEL_H - TITLE_H - content.height) // 2
    canvas.paste(content, (x, y))
    draw.rectangle((0, 0, PANEL_W - 1, PANEL_H - 1), outline=PANEL_BORDER, width=2)
    return canvas


def compose_one(
    name: str,
    reports: dict[str, dict[str, Path]],
    profiles: dict[str, dict[str, Path]],
    output_dir: Path,
) -> Path:
    source_original = reports["mtobjects_spike"].get(name) or reports["sep_spike"].get(name)
    panels = [
        fit_panel(
            crop_report(source_original, "mtobjects", "original"),
            f"{name}: centred original",
            "No source report was found for the original image.",
        ),
        fit_panel(
            crop_report(source_original, "mtobjects", "original_profile"),
            "Original bar-major profile",
            "No source report was found for the original profile.",
        ),
        fit_panel(
            load_image(profiles["sep_spike"].get(name))
            or crop_report(reports["sep_spike"].get(name), "sep", "processed_profile"),
            "SEP: Spike Gate parameters",
            "SEP Spike Gate report is missing or not complete.",
            normalise_axes=name not in profiles["sep_spike"],
        ),
        fit_panel(
            load_image(profiles["sep_toy"].get(name))
            or crop_report(reports["sep_toy"].get(name), "sep", "processed_profile"),
            "SEP: Toy Objects parameters",
            "SEP Toy Object report is missing or not complete.",
            normalise_axes=name not in profiles["sep_toy"],
        ),
        fit_panel(
            load_image(profiles["mtobjects_spike"].get(name))
            or crop_report(reports["mtobjects_spike"].get(name), "mtobjects", "processed_profile"),
            "MTObjects: Spike Gate parameters",
            "MTObjects Spike Gate report is missing or not complete.",
            normalise_axes=name not in profiles["mtobjects_spike"],
        ),
        fit_panel(
            load_image(profiles["mtobjects_toy"].get(name))
            or crop_report(reports["mtobjects_toy"].get(name), "mtobjects", "processed_profile"),
            "MTObjects: Toy Objects parameters",
            "MTObjects Toy Object report is missing or not complete.",
            normalise_axes=name not in profiles["mtobjects_toy"],
        ),
    ]

    page_w = PAGE_MARGIN * 2 + PANEL_W * 2 + GAP
    page_h = PAGE_MARGIN * 2 + PANEL_H * 3 + GAP * 2
    page = Image.new("RGB", (page_w, page_h), BACKGROUND)
    positions = [
        (PAGE_MARGIN, PAGE_MARGIN),
        (PAGE_MARGIN + PANEL_W + GAP, PAGE_MARGIN),
        (PAGE_MARGIN, PAGE_MARGIN + PANEL_H + GAP),
        (PAGE_MARGIN + PANEL_W + GAP, PAGE_MARGIN + PANEL_H + GAP),
        (PAGE_MARGIN, PAGE_MARGIN + 2 * (PANEL_H + GAP)),
        (PAGE_MARGIN + PANEL_W + GAP, PAGE_MARGIN + 2 * (PANEL_H + GAP)),
    ]
    for panel, position in zip(panels, positions):
        page.paste(panel, position)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{name}_all_method_comparison.png"
    page.save(output_path, optimize=True)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pc", choices=sorted(PC_RESEARCH_FOLDERS), default=detect_pc(FOREGROUND_ROOT))
    parser.add_argument("--mtobjects-spike-summary", type=Path, default=None)
    parser.add_argument("--mtobjects-toy-summary", type=Path, default=None)
    parser.add_argument("--sep-spike-summary", type=Path, default=None)
    parser.add_argument("--sep-toy-summary", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--names", nargs="*", help="Optional galaxy names to render.")
    parser.add_argument("--max-galaxies", type=int, default=None)
    parser.add_argument("--require-all", action="store_true", help="Only render galaxies with all four method reports present.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = default_paths(args.pc)
    output_dir = args.output_dir or (paths["output"] / datetime.now().strftime("%Y%m%d_%H%M%S"))
    summaries = {
        "mtobjects_spike": args.mtobjects_spike_summary or paths["mtobjects_spike"],
        "mtobjects_toy": args.mtobjects_toy_summary or paths["mtobjects_toy"],
        "sep_spike": args.sep_spike_summary or paths["sep_spike"],
        "sep_toy": args.sep_toy_summary or paths["sep_toy"],
    }
    for method, summary in summaries.items():
        print(f"Input {method}: {summary}", flush=True)
    reports = {
        method: load_summary(summary) for method, summary in summaries.items()
    }
    profiles = {
        method: load_summary(summary, "profile_png") for method, summary in summaries.items()
    }
    if args.names:
        names = list(args.names)
    else:
        names = sorted(set().union(*(set(mapping) for mapping in reports.values())))
    if args.require_all:
        names = [name for name in names if all(name in mapping for mapping in reports.values())]
    if args.max_galaxies is not None:
        names = names[: max(0, args.max_galaxies)]

    print(f"Rendering {len(names)} galaxy comparison PNGs to {output_dir}", flush=True)
    for index, name in enumerate(names, start=1):
        output_path = compose_one(name, reports, profiles, output_dir)
        print(f"{index}/{len(names)} {name}: {output_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
