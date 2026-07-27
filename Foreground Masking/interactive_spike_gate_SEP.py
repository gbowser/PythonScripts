#!/usr/bin/env python3
"""Canonical interactive Spike Gate + SEP foreground-mask tester."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent))
for folder in ("Batch tools", "PhotUtils", "Interactive tools", "Shared", "Utilities"):
    sys.path.insert(0, str(SCRIPT_DIR / folder))

from canonical_tool_helpers import insert_best_json_arg, insert_detected_pc_arg, latest_best_json
import interactive_sep_spike_gate_parameter_tester as tool


if __name__ == "__main__":
    pc_name = insert_detected_pc_arg(sys.argv)
    insert_best_json_arg(sys.argv, latest_best_json(pc_name, "spike_gate", "SEP"))
    tool.main()
