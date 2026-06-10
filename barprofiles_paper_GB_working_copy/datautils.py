"""Small table-reading helper used by the converted paper scripts."""

from __future__ import annotations

from pathlib import Path

import numpy as np


class TableData:
    """Container with both dict-style and attribute-style column access."""

    def __init__(self, columns: dict[str, np.ndarray]) -> None:
        self._columns = columns

    def __getitem__(self, key: str) -> np.ndarray:
        return self._columns[key]

    def __getattr__(self, name: str) -> np.ndarray:
        try:
            return self._columns[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __len__(self) -> int:
        first_col = next(iter(self._columns.values()))
        return len(first_col)

    @property
    def columns(self) -> tuple[str, ...]:
        return tuple(self._columns)


def _coerce_column(values: list[str]) -> np.ndarray:
    try:
        return np.array([float(value) for value in values])
    except ValueError:
        return np.array(values, dtype=str)


def ReadCompositeTable(filename: str | Path, columnRow: int | None = None, dataFrame: bool = True) -> TableData:
    """Read a whitespace-separated table with a commented header row.

    The original analysis used a local ``datautils.ReadCompositeTable`` helper
    that is not included in this repository. This replacement implements the
    subset needed here: columns are returned as NumPy arrays and can be accessed
    as either ``table["logmstar"]`` or ``table.logmstar``.
    """

    path = Path(filename)
    header: list[str] | None = None
    rows: list[list[str]] = []

    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("#"):
                candidate = line[1:].strip().split()
                if candidate and candidate[0] == "name":
                    header = candidate
                continue
            rows.append(line.split())

    if header is None:
        raise ValueError(f"No commented header row found in {path}")
    if not rows:
        raise ValueError(f"No data rows found in {path}")

    columns = {
        name: _coerce_column([row[index] for row in rows])
        for index, name in enumerate(header)
    }
    return TableData(columns)
