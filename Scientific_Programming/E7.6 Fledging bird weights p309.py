import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Read in the data: day before fledging, wing loading and error for two broods.
dt = np.dtype(
    [
        ("day", "i2"),
        ("wl1", "f8"),
        ("wl1-err", "f8"),
        ("wl2", "f8"),
        ("wl2-err", "f8"),
    ]
)
data_path = Path(__file__).with_name("fledging-data.csv")
# Equivalent form: data_path = Path(__file__).parent / "fledging-data.csv"
data = np.loadtxt(data_path, dtype=dt, delimiter=",")

# Weighted fit of exponential decay to the data. This is a linear least-squares
# problem because y = Aexp(-Bx) => ln y = ln A - Bx = mx + c.
p1_fit = np.poly1d(
    np.polyfit(data["day"], np.log(data["wl1"]), 1, w=np.log(data["wl1"]) ** -2)
)
p2_fit = np.poly1d(
    np.polyfit(data["day"], np.log(data["wl2"]), 1, w=np.log(data["wl2"]) ** -2)
)
wl1fit = np.exp(p1_fit(data["day"]))
wl2fit = np.exp(p2_fit(data["day"]))

# Plot the data points with their uncertainties and the fits.
fig, ax = plt.subplots()


# wl1 data: white circles, black borders, with error bars.
ax.errorbar(
    data["day"],
    data["wl1"],
    yerr=data["wl1-err"],
    ls="",
    marker="o",
    color="k",
    mfc="w",
    mec="k",
    capsize=3,
)
ax.plot(data["day"], wl1fit, "k", lw=1.5)

# wl2 data: black filled circles, with error bars.
ax.errorbar(
    data["day"],
    data["wl2"],
    yerr=data["wl2-err"],
    ls="",
    marker="o",
    color="k",
    mfc="k",
    mec="k",
    capsize=3,
)
ax.plot(data["day"], wl2fit, "k", lw=1.5)

ax.set_xlim(15, 0)
ax.set_ylim(0.003, 0.012)
ax.set_xlabel("Days pre-fledging")
ax.set_ylabel(r"Wing loading ($\mathrm{g\,mm^{-2}}$)")
plt.show()
