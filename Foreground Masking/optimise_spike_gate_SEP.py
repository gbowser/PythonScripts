#!/usr/bin/env python3
"""Canonical optimiser for Spike Gate targeted SEP parameters."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
for folder in ("Batch tools", "PhotUtils", "Interactive tools", "Shared", "Utilities"):
    sys.path.insert(0, str(SCRIPT_DIR / folder))

from canonical_tool_helpers import insert_detected_pc_arg
import optimise_sep_spike_gate_parameters as optimiser


if __name__ == "__main__":
    insert_detected_pc_arg(sys.argv)
    optimiser.main()
