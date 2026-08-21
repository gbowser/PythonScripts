"""Create side-by-side MTObjects/SEP Toy Objects comparison PNGs."""

from __future__ import annotations

import argparse
from pathlib import Path
import time

from PIL import Image, ImageDraw


def galaxy_key(path: Path, method: str) -> tuple[str, bool]:
    marker = "_mtobjects_" if method == "mto" else "_sep_"
    name = path.stem
    if marker not in name:
        raise ValueError(f"Cannot identify galaxy in {path.name}")
    galaxy = name.split(marker, 1)[0]
    return galaxy, name.endswith("_clean")


def indexed(folder: Path, method: str) -> dict[str, tuple[Path, bool]]:
    result: dict[str, tuple[Path, bool]] = {}
    for path in sorted(folder.glob("*.png")):
        galaxy, clean = galaxy_key(path, method)
        if galaxy in result:
            raise ValueError(f"Duplicate {method} PNG for {galaxy}")
        result[galaxy] = (path, clean)
    return result


def resize_to_height(image: Image.Image, height: int) -> Image.Image:
    if image.height == height:
        return image
    width = round(image.width * height / image.height)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mto-dir", type=Path, required=True)
    parser.add_argument("--sep-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--gutter", type=int, default=40)
    parser.add_argument("--divider-width", type=int, default=10)
    parser.add_argument("--dash-length", type=int, default=48)
    parser.add_argument("--dash-gap", type=int, default=28)
    args = parser.parse_args()

    mto = indexed(args.mto_dir, "mto")
    sep = indexed(args.sep_dir, "sep")
    missing_mto = sorted(set(sep) - set(mto))
    missing_sep = sorted(set(mto) - set(sep))
    if missing_mto or missing_sep:
        raise ValueError(f"Unmatched galaxies: missing MTO={missing_mto}; missing SEP={missing_sep}")

    args.output_dir.mkdir(parents=True, exist_ok=False)
    names = sorted(mto, key=str.casefold)
    started = time.perf_counter()
    for index, galaxy in enumerate(names, 1):
        mto_path, mto_clean = mto[galaxy]
        sep_path, sep_clean = sep[galaxy]
        if mto_clean != sep_clean:
            raise ValueError(f"Calibration suffix mismatch for {galaxy}")
        with Image.open(mto_path) as left_source, Image.open(sep_path) as right_source:
            left = left_source.convert("RGB")
            right = right_source.convert("RGB")
            target_height = max(left.height, right.height)
            left = resize_to_height(left, target_height)
            right = resize_to_height(right, target_height)
            canvas = Image.new("RGB", (left.width + args.gutter + right.width, target_height), "white")
            canvas.paste(left, (0, 0))
            canvas.paste(right, (left.width + args.gutter, 0))
            divider_x = left.width + args.gutter // 2
            draw = ImageDraw.Draw(canvas)
            step = args.dash_length + args.dash_gap
            for y0 in range(0, target_height, step):
                y1 = min(target_height - 1, y0 + args.dash_length)
                draw.line((divider_x, y0, divider_x, y1), fill="black", width=args.divider_width)
            suffix = "_clean" if mto_clean else ""
            output = args.output_dir / f"{galaxy}_MTO_left_SEP_right{suffix}.png"
            canvas.save(output, format="PNG", optimize=True)
        elapsed = time.perf_counter() - started
        remaining = len(names) - index
        eta = elapsed / index * remaining
        print(f"[{index}/{len(names)}] {galaxy}: ok; eta={eta:.0f}s", flush=True)

    print(f"Completed: {len(names)}; output={args.output_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
