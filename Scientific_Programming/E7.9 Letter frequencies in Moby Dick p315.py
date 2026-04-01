import matplotlib.pyplot as plt
from pathlib import Path

text_file = "moby-dick.txt"

data_path = Path(__file__).with_name(text_file)

letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
# Initialize the dictionary of letter counts: {'A': 0, 'B': 0, ...}
lcount = dict([(l, 0) for l in letters])

# Read in the text and count the letter occurences
with open(data_path, encoding="utf-8", errors="ignore") as f:
    for l in f.read():
        try:
            lcount[l.upper()] += 1
        except KeyError:
            # Ignore characters that are not letters
            pass
# The total number of letters
norm = sum(lcount.values())

fig = plt.figure()
ax = fig.add_subplot(111)
# The bar chart, with letters along the horizontal axis and the calculated
# letter frequencies as percentages as the bar height
x = range(26)
ax.bar(
    x,
    [lcount[l] / norm * 100 for l in letters],
    width=0.8,
    color="g",
    alpha=0.5,
    align="center",
)
ax.set_xticks(x)
ax.set_xticklabels(letters)
ax.tick_params(axis="x", direction="out")
ax.set_xlim(-0.5, 25.5)
ax.yaxis.grid(True, ls=":", lw=0.5)
ax.set_ylabel("Letter frequency, %")
plt.show()
