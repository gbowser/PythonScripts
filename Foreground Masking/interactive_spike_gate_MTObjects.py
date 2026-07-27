#!/usr/bin/env python3
"""Canonical interactive Spike Gate + MTObjects foreground-mask tester."""

from __future__ import annotations

import sys

from canonical_tool_helpers import insert_best_json_arg, latest_best_json, pc_from_argv
import mtobjects_spike_gate_processing as tool


if __name__ == "__main__":
    pc_name = pc_from_argv(sys.argv, tool.DEFAULT_PC)
    insert_best_json_arg(sys.argv, latest_best_json(pc_name, "spike_gate", "MTObjects"))
    tool.main()
