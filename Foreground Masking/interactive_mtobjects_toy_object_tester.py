#!/usr/bin/env python3
"""Launch the MTObjects Toy Object interactive tester."""

from __future__ import annotations

import sys

import toy_object_interactive_core as toy


if __name__ == "__main__":
    sys.argv[1:1] = ["--algorithm", "MTObjects"]
    toy.main()
