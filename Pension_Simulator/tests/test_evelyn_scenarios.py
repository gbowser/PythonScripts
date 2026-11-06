from dataclasses import replace
from pathlib import Path
import json

import pytest
from streamlit.testing.v1 import AppTest

from simulation import Settings, EVELYN_SCENARIOS, evelyn_preset, evelyn_reference, simulate


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


def test_selected_reference_is_fixed_when_model_inputs_change():
    s = Settings(years=2, non_stochastic=True, evelyn_scenario=3, taxes_enabled=False)
    a = simulate(s)
    b = simulate(replace(s, gift=0, initial_y=.20))
    assert a['evelyn_reference'].equals(b['evelyn_reference'])
    assert a['base'].portfolio_real.iloc[-1] != b['base'].portfolio_real.iloc[-1]
    assert 'evelyn_scenarios' not in a


def test_preset_populates_inputs_and_graph_has_only_selected_reference():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'), default_timeout=60).run()
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
    next(w for w in app.selectbox if w.label == 'Scenario preset').set_value(5).run()
    assert next(n for n in app.text_input if n.label == 'Annual gift (£)').value == '£100,000'
    assert next(n for n in app.number_input if n.label == 'Base case and first-year y (%)').value == 0
    assert any('Inputs have changed' in w.value for w in app.warning)
    next(w for w in app.selectbox if w.label == 'Scenario preset').set_value(1).run()
    assert next(n for n in app.text_input if n.label == 'Annual gift (£)').value == '£0'
    assert next(n for n in app.number_input if n.label == 'Gift duration (years)').value == 0
