#!/usr/bin/env python3
"""Canonical optimiser for Toy Objects targeted SEP parameters."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
for folder in ("Batch tools", "PhotUtils", "Interactive tools", "Shared", "Utilities"):
    sys.path.insert(0, str(SCRIPT_DIR / folder))

from canonical_tool_helpers import insert_detected_pc_arg
import sep_toy_object_parameter_optimisation as optimiser


if __name__ == "__main__":
    insert_detected_pc_arg(sys.argv)
    optimiser.main()
