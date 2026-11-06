from dataclasses import replace
from pathlib import Path
import json

import pytest
from streamlit.testing.v1 import AppTest

from simulation import Settings, EVELYN_SCENARIOS, evelyn_preset, evelyn_reference, simulate, evelyn_mismatches


def test_seven_presets_and_original_reference_curves():
    for number, gift, y in EVELYN_SCENARIOS:
        preset = evelyn_preset(number)
        assert preset['gift'] == gift
        assert preset['gift_years'] == (5 if gift else 0)
        assert preset['initial_y'] == y
        assert preset['years'] == 34
        assert preset['std_y'] == 0
        reference = evelyn_reference(number, 60, .02)
        assert reference.year.tolist() == list(range(35))
        assert reference.gordon_age.tolist() == list(range(65, 100))
        assert reference.portfolio_real.between(0, 4500000).all()
        assert reference.portfolio_real.is_monotonic_decreasing
        assert reference.portfolio_nominal.iloc[10] == pytest.approx(reference.portfolio_real.iloc[10]*1.02**10)
    assert evelyn_reference(1, 34, .02).portfolio_real.iloc[-1] == pytest.approx(1400000, abs=60000)
    assert evelyn_reference(0, 34, .02) is None


def test_reference_is_hidden_when_preset_parameters_change():
    s = Settings(**evelyn_preset(3),evelyn_scenario=3,sipp_income_target=50270)
    assert not evelyn_mismatches(s)
    for field,value in [('gift',0),('initial_y',.20),('inflation',.03),('years',20),
                        ('annual_fee',.01),('starting_balance',5000000),
                        ('crash_enabled',True),('property_sale_enabled',True)]:
        assert evelyn_mismatches(replace(s,**{field:value}))
    # No reference data are attached to a modified run or its result exports.
    altered=replace(s,years=2,gift=0,initial_y=.20)
    result=simulate(altered)
    assert result['evelyn_reference'] is None
    assert result['evelyn_reference_mismatches']
    assert not evelyn_mismatches(replace(s,taxes_enabled=False,withdrawal_strategy='annual_tax'))
    assert not evelyn_mismatches(replace(s,non_stochastic=False,std_y=.133))


def test_preset_populates_inputs_and_graph_has_only_selected_reference():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'), default_timeout=60).run()
    next(w for w in app.radio if w.label == 'Projection mode').set_value('Evelyn preset').run()
    next(w for w in app.selectbox if w.label == 'Scenario preset').set_value(3).run()
    assert not app.exception
    assert next(n for n in app.number_input if n.label == 'Years').value == 34
    assert next(n for n in app.number_input if n.label == 'Gift duration (years)').value == 5
    assert next(n for n in app.number_input if n.label == 'Base case and first-year y (%)').value == 2.5
    assert next(n for n in app.text_input if n.label == 'Annual gift (£)').value == '£150,000'
    next(b for b in app.button if b.label == 'Run simulation').click().run(timeout=60)
    assert not app.exception
    assert not app.error
    spec = json.loads(app.get('plotly_chart')[0].proto.spec)
    assert len(spec['data']) == 2
    refs = [t for t in spec['data'] if t['name'].startswith('Evelyn S')]
    assert len(refs) == 1 and 'S3:' in refs[0]['name']
    assert spec['layout']['yaxis']['range'][0] == 0
    next(w for w in app.number_input if w.label == 'Base case and first-year y (%)').set_value(3.0).run()
    changed=json.loads(app.get('plotly_chart')[0].proto.spec)
    assert not any(t['name'].startswith('Evelyn S') for t in changed['data'])
    assert not any(m.label.startswith('Evelyn S') for m in app.metric)
    assert any('Evelyn reference hidden' in c.value for c in app.caption)
    next(w for w in app.number_input if w.label == 'Base case and first-year y (%)').set_value(2.5).run()
    restored=json.loads(app.get('plotly_chart')[0].proto.spec)
    assert any(t['name'].startswith('Evelyn S') for t in restored['data'])
    next(w for w in app.selectbox if w.label == 'Scenario preset').set_value(5).run()
    assert next(n for n in app.text_input if n.label == 'Annual gift (£)').value == '£100,000'
    assert next(n for n in app.number_input if n.label == 'Base case and first-year y (%)').value == 0
    assert any('Inputs have changed' in w.value for w in app.warning)
    next(w for w in app.selectbox if w.label == 'Scenario preset').set_value(1).run()
    assert next(n for n in app.text_input if n.label == 'Annual gift (£)').value == '£0'
    assert next(n for n in app.number_input if n.label == 'Gift duration (years)').value == 0


def test_stochastic_preset_keeps_reference_and_hides_fixed_y_curve():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=60).run()
    next(w for w in app.radio if w.label == 'Projection mode').set_value('Evelyn preset').run()
    next(w for w in app.selectbox if w.label == 'Withdrawal strategy').set_value('annual_tax').run()
    next(b for b in app.button if b.label == 'Run simulation').click().run(timeout=60)
    assert not app.exception and not app.error
    initial=json.loads(app.get('plotly_chart')[0].proto.spec)
    assert any(t['name'] == 'Our model: fixed y, no crash' for t in initial['data'])
    next(w for w in app.radio if w.label == 'Simulation type').set_value('Stochastic').run()
    pending=json.loads(app.get('plotly_chart')[0].proto.spec)
    assert not any(t['name'] == 'Our model: fixed y, no crash' for t in pending['data'])
    assert any(t['name'].startswith('Evelyn S') for t in pending['data'])
    # Reuse a completed forecast as a rendering fixture rather than running
    # 100 identical 34-year paths. Eligibility with nonzero volatility is
    # independently checked above; quantiles exist in either mode's result.
    result=app.session_state.result
    result['settings']['non_stochastic']=False
    app.session_state.result=result
    app.run()
    assert not app.exception
    spec=json.loads(app.get('plotly_chart')[0].proto.spec)
    names=[t['name'] for t in spec['data']]
    assert any(n.startswith('Evelyn S') for n in names)
    assert 'Our model: fixed y, no crash' not in names
    assert any('percentile' in n for n in names)
    assert app.session_state.result['evelyn_reference'] is not None
