"""Check ten-year calibration against published workbook summary figures."""
import pytest
from sources import read_workbook, DEFAULT_WORKBOOK
from simulation import Settings
from pathlib import Path


def test_ten_year_workbook_calibration():
    if not Path(DEFAULT_WORKBOOK).exists():
        pytest.skip("Local source workbook unavailable")
    source = read_workbook()
    assert source['performance_rows'] == 10
    assert source['history'][0]['period_start'] == '2016-11-05'
    assert source['history'][-1]['period_end'] == '2026-11-05'
    # Independently published ten-year CAGR in E50 and CPI CAGR in H50.
    assert source['portfolio_cagr'] == pytest.approx(0.05960598944111695)
    assert source['cpi_cagr'] == pytest.approx(0.0360752099694539)
    assert source['mean_y'] == pytest.approx(0.02600556938565014)
    assert source['std_y'] == pytest.approx(0.1011793257146728)
    assert Settings().initial_y == pytest.approx(source['mean_y'])
    assert Settings().std_y == pytest.approx(source['std_y'])
    for row in source['history']:
        assert row['inflation'] + row['y'] == pytest.approx(row['nominal_return'])
