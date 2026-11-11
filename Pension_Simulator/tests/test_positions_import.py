import os
from pathlib import Path
import pytest
from positions_import import newest_positions,read_positions,POSITIONS_FOLDER
from simulation import Settings,simulate,ACCOUNT_NAMES
from streamlit.testing.v1 import AppTest


def test_select_newest_export_by_modified_time(tmp_path):
    old=tmp_path/'positions-old.xlsx'; new=tmp_path/'positions-new.xlsx'
    old.write_bytes(b'old');new.write_bytes(b'new')
    os.utime(old,(100,100));os.utime(new,(200,200))
    assert newest_positions(tmp_path)==new


def test_actual_export_and_import_button():
    if not POSITIONS_FOLDER.exists(): pytest.skip('Local export unavailable')
    imported=read_positions()
    assert set(imported['accounts'])==set(ACCOUNT_NAMES)
    assert imported['total']==pytest.approx(sum(a['value'] for a in imported['accounts'].values()))
    for owner in ['Gordon','Ann']:
        a=imported['accounts'][owner+' GIA']
        assert a['dividend_share']==pytest.approx(a['dividends']/a['income'])
        assert a['income_yield']==pytest.approx(a['income']/a['value'])
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    next(b for b in app.button if b.label=='Import latest Evelyn positions spreadsheet').click().run()
    assert not app.exception and not app.error
    assert app.session_state.balance_raw==pytest.approx(imported['total'])
    for name in ACCOUNT_NAMES:
        assert app.session_state['balance_'+name+'_raw']==pytest.approx(imported['accounts'][name]['value'])
    for j,owner in enumerate(['Gordon','Ann']):
        a=imported['accounts'][owner+' GIA']
        assert app.session_state[f'annualised_gain_{j}_raw']==pytest.approx(a['gain'])
        assert app.session_state[f'fixed_dividend_share_{j}']==pytest.approx(a['dividend_share']*100)
        assert app.session_state[f'gia_income_yield_{j}']==pytest.approx(a['income_yield']*100)
    assert app.session_state.gia_separate_yields


def test_distinct_gia_yields_feed_tax_income_without_extra_return():
    s=Settings(years=1,simulations=1,non_stochastic=True,starting_balance=600000,
        inflation=0,initial_y=0,withdrawal=0,gift=0,ann_pension_contribution=0,
        taxes_enabled=False,sipp_income_target=0,gia_income_yield_gordon=.01,gia_income_yield_ann=.02)
    r=simulate(s,[100000]*6,[0,0])
    row=r['details'].query('year == 1').iloc[0]
    assert row.gia_yield_gordon==pytest.approx(1000)
    assert row.gia_yield_ann==pytest.approx(2000)
    assert row.portfolio_nominal==pytest.approx(600000)


def test_unknown_gia_income_stops_import(monkeypatch,tmp_path):
    import positions_import as importer
    file=tmp_path/'positions-test.xlsx';file.write_bytes(b'fixture')
    monkeypatch.setattr(importer,'newest_positions',lambda folder:file)
    class Sheet:
        title='Positions'
        def iter_rows(self,**kwargs):
            return iter([('Instrument Name','Valuation','Valuation Currency','Unrealized PL','Unrealized PL Currency','annualIncome','annualIncomeCurrency','accountName','securityType'),
                ('Unknown mixed fund',100,'GBP',1,'GBP','10','GBP','GORDON BOWSER AL.2749.DIM.002','Mixed Unknown')])
    class Workbook(list):
        def close(self): pass
    monkeypatch.setattr(importer,'load_workbook',lambda *a,**k:Workbook([Sheet()]))
    with pytest.raises(ValueError,match='Cannot classify GIA income'):
        importer.read_positions(tmp_path)
