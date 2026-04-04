import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

from pathlib import Path
file_path = Path(__file__).with_name("hygdata_v3-abridged.csv")

# Read in data and calculate stellar temperature from the Ballesteros formula.
df = pd.read_csv(file_path)
df["T"] = 4600 * (1 / (0.92 * df["ci"] + 1.7) + 1 / (0.92 * df["ci"] + 0.62))

# Set the aspect ratio for maximum clarity.
fig, ax = plt.subplots(figsize=(6, 8))
# Log-log plot with suitable ticks and labels.
ax.scatter(df["T"], df["lum"], s=0.5, c="k")
ax.set_yscale("log")
ax.set_xscale("log")
ax.set_ylim(1.0e-6, 1.0e5)
ax.set_xlim(30000, 1000)
ax.set_xticks([30000, 10000, 5000, 3000, 1000])
# The chosen xticks don't get used unless we explicitly set a ScalarFormatter.
ax.get_xaxis().set_major_formatter(ScalarFormatter())
ax.set_xlabel("Temperature /K")
ax.set_ylabel("Luminosity relative to Sun")

plt.show()