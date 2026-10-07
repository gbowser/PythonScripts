"""Standardise timestamp-based filenames in the Camera Uploads directory.

For example::

    20261006 142305.jpg  -> 2026-10-06 14.23.05.jpg
    20261006 142305.heic -> 2026-10-06 14.23.05.heic
    20261006 142305.mp4  -> 2026-10-06 14.23.05.mp4
    20210627_082844_01.jpg -> 2021-06-27 08.28.44-01.jpg

Run with ``--dry-run`` to preview the changes without renaming anything.
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path


DEFAULT_DIRECTORY = Path(r"D:\Dropbox\Camera Uploads")
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".heic", ".mp4"}
STANDARD_NAME = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}) "
    r"(?P<hour>\d{2})\.(?P<minute>\d{2})\.(?P<second>\d{2})"
    r"(?:-(?P<serial>\d{2,}))?"
    r"(?P<extension>\.jpe?g|\.heic|\.mp4)$",
    re.IGNORECASE,
)
STANDARD_WITH_UNPADDED_SERIAL = re.compile(
    r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}) "
    r"(?P<hour>\d{2})\.(?P<minute>\d{2})\.(?P<second>\d{2})"
    r"-(?P<serial_plain>\d+)"
    r"(?P<extension>\.jpe?g|\.heic|\.mp4)$",
    re.IGNORECASE,
)
COMPACT_NAME = re.compile(
    r"^(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})[ _-]?"
    r"(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})"
    r"(?:(?:[_-](?P<serial_plain>\d+))|(?:\s*\((?P<serial_parenthesised>\d+)\)))?"
    r"(?P<extension>\.jpe?g|\.heic|\.mp4)$",
    re.IGNORECASE,
)


def standard_name(file_name: str) -> str | None:
    """Return the standard filename, or None if the name is not recognised."""
    match = COMPACT_NAME.fullmatch(file_name)
    if match is None:
        match = STANDARD_WITH_UNPADDED_SERIAL.fullmatch(file_name)
    if match is None:
        return None

    extension = match.group("extension").lower()
    if extension == ".jpeg":
        extension = ".jpg"
    serial_text = match.groupdict().get("serial_plain") or match.groupdict().get(
        "serial_parenthesised"
    )
    parts = {
        key: int(value)
        for key, value in match.groupdict().items()
        if key in {"year", "month", "day", "hour", "minute", "second"}
    }
    try:
        timestamp = datetime(**parts)
    except ValueError:
        return None

    serial = f"-{int(serial_text):02d}" if serial_text is not None else ""
    return timestamp.strftime("%Y-%m-%d %H.%M.%S") + serial + extension


def rename_camera_files(directory: Path, dry_run: bool = False) -> tuple[int, int]:
    """Rename recognised files and return (renamed_count, skipped_count)."""
    renamed = 0
    skipped = 0

    for source in sorted(directory.iterdir(), key=lambda path: path.name.lower()):
        if not source.is_file():
            continue

        if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(f"SKIP (unsupported type): {source.name}")
            skipped += 1
            continue

        if STANDARD_NAME.fullmatch(source.name):
            continue

        new_name = standard_name(source.name)
        if new_name is None:
            print(f"SKIP (unrecognised): {source.name}")
            skipped += 1
            continue

        destination = source.with_name(new_name)
        if destination.exists():
            print(f"SKIP (destination exists): {source.name} -> {new_name}")
            skipped += 1
            continue

        action = "WOULD RENAME" if dry_run else "RENAMED"
        print(f"{action}: {source.name} -> {new_name}")
        if not dry_run:
            source.rename(destination)
        renamed += 1

    return renamed, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rename timestamped JPG, JPEG, HEIC and MP4 files to "
            "yyyy-mm-dd hh.mm.ss.ext."
        )
    )
    parser.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=DEFAULT_DIRECTORY,
        help=f"directory to process (default: {DEFAULT_DIRECTORY})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show proposed changes without renaming files",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.directory.is_dir():
        raise SystemExit(f"Directory does not exist: {args.directory}")

    renamed, skipped = rename_camera_files(args.directory, args.dry_run)
    verb = "would be renamed" if args.dry_run else "renamed"
    print(f"\nFinished: {renamed} file(s) {verb}; {skipped} file(s) skipped.")


if __name__ == "__main__":
    main()
