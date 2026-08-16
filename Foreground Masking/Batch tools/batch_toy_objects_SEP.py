#!/usr/bin/env python3
"""Canonical all-galaxy batch runner for Toy Objects optimised SEP masks."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(FOREGROUND_ROOT.parent))
for folder in ("Batch tools", "PhotUtils", "Interactive tools", "Shared", "Utilities"):
    sys.path.insert(0, str(FOREGROUND_ROOT / folder))

import batch_sep_all_galaxies as batch
from canonical_tool_helpers import insert_detected_pc_arg


if __name__ == "__main__":
    insert_detected_pc_arg(sys.argv)
    if "--source" not in sys.argv:
        sys.argv[1:1] = ["--source", "toy-object"]
    if "--toy-diagnostics" not in sys.argv:
        sys.argv[1:1] = ["--toy-diagnostics"]
    batch.main()
