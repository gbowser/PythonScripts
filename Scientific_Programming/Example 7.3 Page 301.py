from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rc

font_properties = {"family": "serif", "weight": "bold", "size": 16}
rc("font", **font_properties)
# The default line width is a bit thin, so let's increase it:
rc("lines", linewidth=2)    


fig, ax = plt.subplots()

cities = ["Boston", "Houston", "Detroit", "San Jose", "Phoenix"]
# line styles: solid, dashes, dots, dash-dots, and dot-dot-dash
linestyles = [
    {"ls": "-"},
    {"ls": "--"},
    {"ls": ":"},
    {"ls": "-."},
    {"dashes": [2, 4, 2, 4, 8, 4]},
]

data_dir = Path(__file__).resolve().parent

for i, city in enumerate(cities):
    filestem = city.lower().replace(" ", "_")
    filename = data_dir / f"{filestem}.tsv"
    yr, pop = np.loadtxt(filename, unpack=True)
    (line,) = ax.plot(yr, pop / 1.0e6, label=city, color="k", **linestyles[i])
ax.legend(loc="upper left")
ax.set_xlim(1800, 2020)
ax.set_xlabel("Year")
ax.set_ylabel("Population (millions)")
ax.set_title("Population of Five US Cities", fontsize=16, fontname="serif", color="navy")
plt.show()
