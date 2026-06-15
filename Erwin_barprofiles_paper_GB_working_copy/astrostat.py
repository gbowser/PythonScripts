"""Codex-created compatibility helpers used by the Erwin paper scripts."""

import numpy as np


def logistic(x, a, b):
    """Return the standard linear logistic probability for x."""

    return 1.0 / (1.0 + np.exp(-(a + b * x)))
