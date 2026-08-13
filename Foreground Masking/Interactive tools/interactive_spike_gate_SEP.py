#!/usr/bin/env python3
"""Canonical interactive Spike Gate + SEP foreground-mask tester."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(FOREGROUND_ROOT.parent))
for folder in ("Batch tools", "PhotUtils", "Interactive tools", "Shared", "Utilities"):
    sys.path.insert(0, str(FOREGROUND_ROOT / folder))

from canonical_tool_helpers import insert_detected_pc_arg
import interactive_sep_spike_gate_parameter_tester as tool


if __name__ == "__main__":
    insert_detected_pc_arg(sys.argv)
    tool.main()
