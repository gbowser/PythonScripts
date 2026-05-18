"""Small environment check for a handful of scientific Python packages."""

from __future__ import annotations

import importlib
import shutil
import subprocess
import sys


REQUIRED_IMPORTS = {
    "matplotlib": "matplotlib",
    "pandas": "pandas",
    "scipy": "scipy",
    "astropy": "astropy",
    "astroquery": "astroquery",
    "ffmpeg": "ffmpeg",
    "openpyxl": "openpyxl",
}


def main() -> int:
    failed = False

    print(f"Python: {sys.version.split()[0]}")
    print()

    for label, module_name in REQUIRED_IMPORTS.items():
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            failed = True
            print(f"[FAIL] {label}: {exc.__class__.__name__}: {exc}")
        else:
            version = getattr(module, "__version__", "unknown version")
            print(f"[ OK ] {label}: {version}")

    print()

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        ffmpeg_version = "unknown version"
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                check=True,
            )
        except Exception:
            pass
        else:
            first_line = result.stdout.splitlines()[0] if result.stdout else ""
            if first_line:
                ffmpeg_version = first_line.replace("ffmpeg version ", "", 1).strip()

        print(f"[ OK ] ffmpeg executable: {ffmpeg_version} ({ffmpeg_path})")
    else:
        print("[WARN] ffmpeg executable not found on PATH")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
