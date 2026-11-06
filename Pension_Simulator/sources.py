"""Read cached Excel values without opening Excel or executing macros."""
from __future__ import annotations

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


def read_workbook(path=DEFAULT_WORKBOOK):
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
        sheet = wb["Pension_Performance"]
        # The workbook's published single-year TWR returns already exclude
        # payments. Use five independent anniversary years, not overlapping
        # multi-year annualised returns or the obsolete P/Q value series.
        records = []
        for cells in sheet.iter_rows(min_row=16, max_row=36, min_col=1, max_col=9):
            row = [cell.value for cell in cells]
            a, b = _date(row[1]), _date(row[2])
            nominal, c0, c1, inflation = row[3], row[4], row[5], row[6]
            if not (a and b and b <= latest_date and 364 <= (b-a).days <= 366):
                continue
            if not all(_number(v) for v in (nominal, c0, c1, inflation)) or min(c0, c1) <= 0:
                raise ValueError(f"Missing cached return/CPI values in Pension_Performance row {cells[0].row}; recalculate and save the workbook.")
            if not math.isclose(inflation, c1/c0-1, abs_tol=1e-8):
                raise ValueError(f"Inconsistent CPI calculation in Pension_Performance row {cells[0].row}.")
            records.append({"year": b.year, "period_start": a.isoformat(), "period_end": b.isoformat(),
                            "source_row": cells[0].row, "nominal_return": nominal,
                            "cpi_start": c0, "cpi_end": c1, "inflation": inflation,
                            "y": nominal-inflation,
                            "exact_real_return": (1+nominal)/(1+inflation)-1})
        history = sorted(records, key=lambda h: h["period_end"])[-5:]
        if len(history) != 5 or history[-1]['period_end'] != latest_date.isoformat():
            raise ValueError("Need five complete single-year TWR records ending at the latest valuation in Pension_Performance A16:I36.")
        if any(a['period_end'] != b['period_start'] for a, b in zip(history, history[1:])):
            raise ValueError("The five annual performance records must form consecutive years.")
        cpi_lag = sheet['B11'].value
        target_margin = sheet['B10'].value
    finally:
        wb.close()
    portfolio_cagr = math.prod(1+h["nominal_return"] for h in history)**(1/5)-1
    cpi_cagr = math.prod(1+h["inflation"] for h in history)**(1/5)-1
    return {"portfolio_cagr": portfolio_cagr, "cpi_cagr": cpi_cagr,
            "cagr_y": portfolio_cagr-cpi_cagr, "target_margin": target_margin,
            "vs_target_cagr": portfolio_cagr-cpi_cagr-target_margin if _number(target_margin) else None,
            "workbook": str(Path(path).resolve()), "valuation_date": latest_date.isoformat(),
            "balance": balance, "history": history,
            "mean_y": mean(h["y"] for h in history),
            "std_y": stdev(h["y"] for h in history),
            "calibration_method": "five_anniversary_twr_years",
            "performance_source": "Pension_Performance A6:J51; individual years D16:D20 minus G16:G20",
            "cpi_lag_months": cpi_lag,
            "cpi_source": "Workbook CPI indices and configured lag in Pension_Performance B11",
            "performance_rows": len(history)}


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
