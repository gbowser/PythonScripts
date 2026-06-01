import matplotlib.pyplot as plt
import numpy as np


def adaptive_gaussian_smooth(x, y, smooth_scale):
    """
    Adaptive Gaussian smoothing for unevenly sampled 1D data.

    Parameters
    ----------
    x : 1D array
        Independent variable, e.g. position or time.
    y : 1D array
        Dependent variable to smooth.
    smooth_scale : float or 1D array
        Gaussian smoothing width in the same units as x.
        Can be a scalar, or an array of length len(x).

    Returns
    -------
    y_smooth : 1D array
        Smoothed profile.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    if np.isscalar(smooth_scale):
        sigma = np.full_like(x, float(smooth_scale), dtype=float)
    else:
        sigma = np.asarray(smooth_scale, dtype=float)

    if len(sigma) != len(x):
        raise ValueError("smooth_scale must be a scalar or have the same length as x.")

    y_smooth = np.zeros_like(y, dtype=float)

    for i in range(len(x)):
        w = np.exp(-0.5 * ((x - x[i]) / sigma[i]) ** 2)
        y_smooth[i] = np.sum(w * y) / np.sum(w)

    return y_smooth


# ------------------------------------------------------------
# Example data: unevenly sampled noisy 1D profile
# ------------------------------------------------------------

np.random.seed(42)

# Uneven sampling in x
x = np.sort(np.random.uniform(0, 10, 180))

# Underlying smooth signal: broad wave + narrow feature
true_signal = (
    np.sin(1.2 * x)
    + 0.35 * np.sin(3.0 * x)
    + 1.2 * np.exp(-0.5 * ((x - 6.0) / 0.35) ** 2)
)

# Add random noise
noise = np.random.normal(0, 0.35, size=len(x))
y = true_signal + noise

# Adaptive smoothing scale:
# use narrower smoothing near the sharp feature, broader elsewhere
smooth_scale = 0.45 - 0.25 * np.exp(-0.5 * ((x - 6.0) / 0.8) ** 2)

y_smooth = adaptive_gaussian_smooth(x, y, smooth_scale)

# ------------------------------------------------------------
# Plot
# ------------------------------------------------------------

plt.figure(figsize=(10, 6))
plt.scatter(x, y, s=18, alpha=0.6, label="Original noisy data")
plt.plot(x, true_signal, linewidth=2, label="Underlying true signal")
plt.plot(
    x,
    y_smooth,
    marker="o",
    markersize=4,
    linewidth=3,
    label="Adaptive Gaussian smoothed data",
)

plt.xlabel("x")
plt.ylabel("y")
plt.title("Adaptive Gaussian Smoothing of Unevenly Sampled Data")
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()

plt.savefig("adaptive_gaussian_smoothing_example.png", dpi=200)
plt.show()
