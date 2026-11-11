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
    from openpyxl import load_workbook
    from statistics import mean,stdev
    wb=load_workbook(DEFAULT_WORKBOOK,read_only=True,data_only=True)
    try:
        sheet=wb['Pension_Performance']
        assert source['history'][0]['period_start']==sheet['B50'].value.date().isoformat()
        assert source['history'][-1]['period_end']==sheet['C50'].value.date().isoformat()
        assert source['portfolio_cagr']==pytest.approx(sheet['E50'].value)
        assert source['cpi_cagr']==pytest.approx(sheet['H50'].value)
        annual=[sheet.cell(r,4).value-sheet.cell(r,7).value for r in range(16,26)]
        assert source['mean_y']==pytest.approx(mean(annual))
        assert source['std_y']==pytest.approx(stdev(annual))
    finally:
        wb.close()
    for row in source['history']:
        assert row['inflation'] + row['y'] == pytest.approx(row['nominal_return'])


@pytest.mark.parametrize('sheet_name',['Pension','Pensions'])
def test_last_valuation_row_not_maximum_date(sheet_name):
    from sources import latest_valuation
    from datetime import date
    class Sheet:
        def iter_rows(self,**kwargs):
            return iter([(date(2026,11,8),None,None,None,None,None,None,100),
                         (date(2026,11,7),None,None,None,None,None,None,120),
                         (date(2026,11,9),None,None,None,None,None,None,None)])
    class Book(dict):
        @property
        def sheetnames(self): return list(self)
    value=latest_valuation(Book({sheet_name:Sheet()}))
    assert value['balance']==120
    assert value['valuation_date']=='2026-11-07'
    assert value['valuation_source']==f'{sheet_name}!B2/I2'


def test_startup_refresh_preserves_later_manual_edits():
    from sources import read_latest_valuation
    from streamlit.testing.v1 import AppTest
    if not Path(DEFAULT_WORKBOOK).exists(): pytest.skip('Local source workbook unavailable')
    expected=read_latest_valuation()
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    assert not app.exception
    assert app.session_state.balance_raw==expected['balance']
    assert app.session_state.start_date.isoformat()==expected['valuation_date']
    from simulation import ACCOUNT_NAMES,REFERENCE_BALANCES
    actual=[app.session_state['balance_'+name+'_raw'] for name in ACCOUNT_NAMES]
    assert sum(actual)==pytest.approx(expected['balance'])
    for value,weight in zip(actual,REFERENCE_BALANCES):
        assert value==pytest.approx(expected['balance']*weight/REFERENCE_BALANCES.sum())
    next(w for w in app.text_input if w.label=='Starting portfolio (£)').set_value('£4,000,000').run()
    assert app.session_state.balance_raw==4000000
