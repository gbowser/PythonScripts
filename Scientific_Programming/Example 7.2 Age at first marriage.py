import numpy as np
import matplotlib.pyplot as plt

year, age_m, age_f = np.loadtxt(
    "eg7-marriage-ages.txt", unpack=True, skiprows=3
)
fig, ax = plt.subplots()

# Plot ages with male or female symbols as markers
ax.plot(
    year,
    age_m,
    marker="$\u2642$",
    markersize=14,
    c="tab:blue",
    lw=2,
    mfc="tab:blue",
    mec="tab:blue",
)
ax.plot(
    year,
    age_f,
    marker="$\u2640$",
    markersize=14,
    c="tab:pink",
    lw=2,
    mfc="tab:pink",
    mec="tab:pink",
)
ax.grid()

ax.set_xlabel("Year")
ax.set_ylabel("Age")
ax.set_title("Median age at first marriage in the US, 1890 - 2010")

plt.show()