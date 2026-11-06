"""Read cached Excel values without opening Excel or executing macros."""
from __future__ import annotations

import csv
import json
import math
from bisect import bisect_left
from datetime import date, datetime
from pathlib import Path
from statistics import mean, stdev

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent
DEFAULT_WORKBOOK = r"D:\Dropbox\My Documents\Home Finances\GPB_Portfolio_2026.xlsm"
SNAPSHOT = ROOT / "data" / "portfolio_snapshot.json"


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    return value if isinstance(value, date) else None


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def interpolate(points, when):
    """Log-linear interpolation of the cash-flow-adjusted performance index."""
    dates = [p[0] for p in points]
    k = bisect_left(dates, when)
    if k < len(points) and dates[k] == when:
        return points[k][1]
    if k == 0 or k == len(points):
        raise ValueError(f"Performance data does not bracket {when}; no extrapolation is used.")
    (d0, v0), (d1, v1) = points[k-1:k+1]
    if (d1-d0).days > 120:
        raise ValueError(f"Performance data has a gap longer than 120 days around {when}.")
    weight = (when-d0).days / (d1-d0).days
    return math.exp(math.log(v0)*(1-weight) + math.log(v1)*weight)


def read_workbook(path=DEFAULT_WORKBOOK, cpi_path=ROOT / "data" / "cpi_december.csv"):
    with Path(cpi_path).open(newline="", encoding="utf-8") as f:
        cpi = {int(r["year"]): float(r["index"]) for r in csv.DictReader(f)}
    if any(not math.isfinite(v) or v <= 0 for v in cpi.values()):
        raise ValueError("CPI indices must be positive finite numbers.")
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        valuations = []
        for row in wb["Pensions"].iter_rows(min_col=2, max_col=9, values_only=True):
            d, v = _date(row[0]), row[7]
            if d and _number(v) and v > 0:
                valuations.append((d, float(v)))
        if not valuations:
            raise ValueError("No dated positive balances in Pensions columns B/I.")
        latest_date, balance = max(valuations, key=lambda p: p[0])
        points = {}
        for row in wb["Pension_Performance"].iter_rows(min_row=41, min_col=16, max_col=17, values_only=True):
            d, v = _date(row[0]), row[1]
            if d and _number(v) and v > 0 and d <= latest_date:
                points[d] = float(v)
    finally:
        wb.close()
    points = sorted(points.items())
    if not points:
        raise ValueError("No positive performance index observations in P41:Q onwards.")
    # A complete calendar year needs both December CPI indices and bracketing
    # performance observations. Partial current years are deliberately excluded.
    end_year = min(latest_date.year-1, points[-1][0].year, max(cpi))
    years = list(range(end_year-4, end_year+1))
    history = []
    for year in years:
        if year not in cpi or year-1 not in cpi:
            raise ValueError(f"Add December D7BT CPI indices for {year-1} and {year} to the CPI CSV.")
        start = interpolate(points, date(year-1, 12, 31))
        end = interpolate(points, date(year, 12, 31))
        nominal = end/start-1
        inflation = cpi[year]/cpi[year-1]-1
        history.append({"year": year, "start_index": start, "end_index": end,
                        "cpi_start": cpi[year-1], "cpi_end": cpi[year],
                        "nominal_return": nominal, "inflation": inflation,
                        "y": nominal-inflation,
                        "exact_real_return": (1+nominal)/(1+inflation)-1})
    return {"workbook": str(Path(path).resolve()), "valuation_date": latest_date.isoformat(),
            "balance": balance, "history": history,
            "mean_y": mean(h["y"] for h in history),
            "std_y": stdev(h["y"] for h in history),
            "cpi_source": "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7bt/mm23",
            "cpi_verified": "2026-11-06", "performance_rows": len(points)}


def load_snapshot():
    if not SNAPSHOT.exists():
        raise FileNotFoundError("No saved portfolio snapshot. Load the workbook in the app first.")
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def save_snapshot(snapshot):
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    temp = SNAPSHOT.with_suffix(".tmp")
    temp.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    temp.replace(SNAPSHOT)


if __name__ == "__main__":
    snapshot = read_workbook()
    save_snapshot(snapshot)
    print(json.dumps(snapshot, indent=2))
