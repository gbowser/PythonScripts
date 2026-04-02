import csv
from datetime import datetime
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt


file_path= Path(__file__).with_name("bp-share-prices.csv")


def load_share_prices(path):
    dates = []
    closes = []
    with path.open(newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            dates.append(datetime.strptime(row["Date"], "%Y-%m-%d"))
            closes.append(float(row["Close"]))
    return dates, closes


dates, closes = load_share_prices(file_path)
fig, ax = plt.subplots()
ax.plot(dates, closes, c="g")
ax.fill_between(dates, 0, closes, facecolor="g", alpha=0.5)

ax.set_xlim(min(dates), max(dates))

price_max = max(closes)


def get_xy(date):
    """Return the (x,y) coordinates of the share price on a given date."""
    x = datetime.strptime(date, "%Y-%m-%d")
    index = dates.index(x)
    return dates[index], closes[index]


# A vertical arrows and labels.
x, y = get_xy("2002-04-30")
ax.annotate(
    "Global oil market\ndownturn",
    (x, y),
    xytext=(x, 725),
    arrowprops=dict(facecolor="black", shrink=0.05, linewidth=0.1),
    ha="center",
)
x, y = get_xy("2010-04-20")
ax.annotate(
    "Deepwater Horizon\noil spill",
    (x, y),
    xytext=(x, 775),
    arrowprops=dict(facecolor="black", shrink=0.05, linewidth=0.1),
    ha="center",
)
x, y = get_xy("2020-03-05")
ax.annotate(
    "Covid pandemic",
    (x, y),
    xytext=(x, 700),
    arrowprops=dict(facecolor="black", shrink=0.05, linewidth=0.1),
    ha="center",
)

ax.xaxis.set_major_locator(mdates.YearLocator(2))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
plt.setp(ax.get_xticklabels(), rotation=90)
ax.set_ylim(0, 875)

plt.show()
