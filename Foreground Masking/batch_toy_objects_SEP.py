#!/usr/bin/env python3
"""Canonical all-galaxy batch runner for Toy Objects optimised SEP masks."""

from __future__ import annotations

import sys

import batch_sep_all_galaxies as batch


if __name__ == "__main__":
    if "--source" not in sys.argv:
        sys.argv[1:1] = ["--source", "toy-object"]
    batch.main()
