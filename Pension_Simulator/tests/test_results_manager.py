from pathlib import Path
from datetime import date
import pandas as pd
import json
import pytest
from streamlit.testing.v1 import AppTest
from results_store import save_run,load_run,list_runs,delete_runs,paired_deltas


@pytest.fixture(autouse=True)
def preserve_store_test_doubles(monkeypatch):
    # Production reloads these modules on reruns; preserve temporary storage
    # and synthetic selection test doubles within this test module.
    import importlib
    reload_module=importlib.reload
    monkeypatch.setattr(importlib,'reload',lambda module: module if module.__name__ in
                        {'results_store','results_manager'} else reload_module(module))


def test_path_differences_before_quantiles():
    def fixture(values):
        return {'result':{'settings':dict(start_date='2026-11-05',seed=42,simulations=2,years=1,non_stochastic=False),
            'inputs':{'model_revision':'same'},
            'details':pd.DataFrame({'simulation':[1,2],'year':[1,1],'portfolio_real':values})}}
    a,b=fixture([0,100]),fixture([100,0])
    differences,q=paired_deltas(a,b)
    assert sorted(differences.Delta)==[-100,100]
    assert q.p10.iloc[0]==-80 and q.p90.iloc[0]==80 and q.p50.iloc[0]==0
    b['result']['settings']['seed']=4
    with pytest.raises(ValueError,match='seed'): paired_deltas(a,b)


def test_save_restore_main_engine(tmp_path,monkeypatch):
    import results_store
    original_save,original_load=results_store.save_run,results_store.load_run
    monkeypatch.setattr(results_store,'save_run',lambda n,r,c:original_save(n,r,c,tmp_path))
    monkeypatch.setattr(results_store,'load_run',lambda i,d=tmp_path:original_load(i,d))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    next(w for w in app.selectbox if w.label=='Simulations').set_value(1).run()
    next(w for w in app.number_input if w.label=='Years').set_value(2).run()
    next(w for w in app.checkbox if w.label=='Choose SIPP income target automatically').uncheck().run()
    next(b for b in app.button if b.label=='Run simulation').click().run(timeout=60)
    assert not app.exception
    expected=app.session_state.result['inputs']
    assert not next(b for b in app.button if b.label=='Save simulation run').disabled, [w.value for w in app.warning]
    next(b for b in app.button if b.label=='Save simulation run').click().run()
    assert not app.exception
    assert not app.error, [e.value for e in app.error]
    rows,errors=list_runs(tmp_path)
    assert len(rows)==1 and not errors
    assert 'Years' not in rows[0] and 'Simulations' not in rows[0]
    assert rows[0]['Gift']==expected['settings']['gift']
    assert rows[0]['Mean_y']==expected['settings']['initial_y']
    restored=load_run(rows[0]['id'],tmp_path)
    pd.testing.assert_frame_equal(app.session_state.result['details'],restored['result']['details'],check_dtype=False,atol=1e-8)
    fresh=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60)
    fresh.query_params['restore']=rows[0]['id']
    fresh.run()
    assert not fresh.exception
    assert fresh.session_state.result['inputs']==expected
    assert next(w for w in fresh.number_input if w.label=='Years').value==2
    assert not any('Inputs have changed' in w.value for w in fresh.warning)
    assert len(fresh.get('plotly_chart'))==2
    assert any('font-size:1rem' in m.value and rows[0]['Name'] in m.value for m in fresh.markdown)
    delete_runs([rows[0]['id']],tmp_path)
    assert list_runs(tmp_path)==([],[])


def test_manager_comparison_window(tmp_path,monkeypatch):
    import results_manager
    import streamlit as st
    from types import SimpleNamespace
    settings=dict(start_date='2026-11-05',seed=42,simulations=2,years=1,non_stochastic=False,crash_enabled=False,property_sale_enabled=False)
    def result(values):
        return dict(settings=settings,inputs={'settings':settings,'model_revision':'same'},
            details=pd.DataFrame({'simulation':[1,2],'year':[1,1],'portfolio_real':values}),
            quantiles=pd.DataFrame([dict(year=1,value='portfolio_real',**{f'p{i}':sum(values)/2 for i in range(10,100,10)})]))
    a=save_run('baseline',result([100,200]),{},tmp_path)
    b=save_run('comparison',result([110,220]),{},tmp_path)
    c=save_run('third',result([90,180]),{},tmp_path)
    monkeypatch.setattr(results_manager,'list_runs',lambda:list_runs(tmp_path))
    monkeypatch.setattr(results_manager,'load_run',lambda i:load_run(i,tmp_path))
    real_dataframe=st.dataframe
    def select(*args,**kwargs):
        value=real_dataframe(*args,**kwargs)
        return SimpleNamespace(selection=SimpleNamespace(rows=[0,1,2])) if kwargs.get('key')=='saved_run_list' else value
    monkeypatch.setattr(st,'dataframe',select)
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60)
    app.query_params['manager']='1'
    app.run()
    assert not app.exception
    assert len(app.get('plotly_chart'))==2
    assert not any(w.label=='Difference method' for w in app.radio)
    assert not any(w.label=='Compare percentile' for w in app.selectbox)
    from charts import BAND_COLORS
    for chart in app.get('plotly_chart'):
        spec=json.loads(chart.proto.spec)
        assert ' - ' in spec['layout']['title']['text']
        assert len(spec['data'])==10
        assert spec['data'][1]['fillcolor']==BAND_COLORS[20]
        assert spec['data'][4]['name']=='Median (50th percentile)'
        assert spec['layout']['yaxis'].get('range') is None

    def mismatched_load(run_id):
        run=load_run(run_id,tmp_path)
        if run_id==b:
            run['result']['settings']['seed']=99
        return run
    monkeypatch.setattr(results_manager,'load_run',mismatched_load)
    app.run()
    assert not app.exception
    assert any('random seed' in warning.value and 'baseline:' in warning.value for warning in app.warning)
    assert len(app.get('plotly_chart'))==1


def test_compact_table_includes_model_inputs_with_fixed_widths():
    from dataclasses import asdict
    from simulation import Settings
    from results_manager import compact_run_table
    parameters=asdict(Settings())
    table,config,formats=compact_run_table([{'Name':'Test','Saved':'2026-11-07T18:00:00+00:00','Parameters':parameters}])
    assert set(parameters)-{'years','simulations'} <= set(table.columns)
    assert 'Size_KB' not in table and 'years' not in table and 'simulations' not in table
    assert config['initial_y']['width']==65
    assert config['crash_enabled']['width']==55
    assert formats['gift'](150000)=='£150,000'
    assert formats['initial_y'](.025)=='2.50%'
