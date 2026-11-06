from pathlib import Path
from datetime import date
from streamlit.testing.v1 import AppTest


def test_browser_app_runs_and_marks_changed_inputs():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=60).run()
    assert not app.exception
    next(n for n in app.number_input if n.label == "Years").set_value(2).run()
    next(b for b in app.button if b.label == "Run simulation").click().run(timeout=60)
    assert not app.exception
    assert not app.error
    assert len(app.metric) == 0
    assert len(app.get("plotly_chart")) == 2
    assert not next(b for b in app.get('download_button') if b.label == 'PDF report').disabled
    assert app.session_state.pdf_report_data.startswith(b'%PDF-')
    import json
    income=json.loads(app.get('plotly_chart')[1].proto.spec)
    assert income['layout']['yaxis']['title']['text'] == 'Net annual income (£, valuation-date purchasing power)'
    assert {t['name'] for t in income['data']} == {'10th percentile','90th percentile','Median net annual income'}
    assert not any('Min real net income' in m.label for m in app.metric)
    assert {b.label for b in app.get("download_button")} == {
        "PDF report", "Deciles CSV", "Base case CSV", "All paths and assumptions ZIP", "Interactive chart HTML"}
    next(n for n in app.text_input if n.label == "Annual gift (£)").set_value("£100,000").run()
    assert any("Inputs have changed" in w.value for w in app.warning)
    assert next(b for b in app.get('download_button') if b.label == 'PDF report').disabled


def test_property_sale_controls_reach_simulation_and_mark_stale():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=60).run()
    next(n for n in app.number_input if n.label == "Years").set_value(2).run()
    next(c for c in app.checkbox if c.label == "Sell rental property").check().run()
    next(d for d in app.date_input if d.label == "Rental property sale date").set_value(date(2027, 6, 1)).run()
    next(n for n in app.text_input if n.label == "Rental property sale proceeds (£)").set_value("£300,000").run()
    next(b for b in app.button if b.label == "Run simulation").click().run(timeout=60)
    assert not app.exception
    assert not app.error
    result = app.session_state.result
    assert result['settings']['property_sale_date'] == '2027-06-01'
    assert result['base'].property_sale_proceeds.sum() == 300000
    assert result['base'].rental_profit_ann.iloc[-1] == 0
    next(n for n in app.text_input if n.label == "Rental property sale proceeds (£)").set_value("£350,000").run()
    assert any("Inputs have changed" in w.value for w in app.warning)


def test_shared_return_mean_and_tax_button():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=60).run()
    assert not any('Mean y from year 2' in n.label for n in app.number_input)
    next(n for n in app.number_input if n.label == 'Years').set_value(2).run()
    next(n for n in app.number_input if n.label == 'Base case and first-year y (%)').set_value(7.0).run()
    next(n for n in app.number_input if n.label == 'Annual standard deviation of y (%)').set_value(0.0).run()
    next(b for b in app.button if b.label == 'Remove all taxes').click().run()
    next(b for b in app.button if b.label == 'Run simulation').click().run(timeout=60)
    assert not app.exception
    result = app.session_state.result
    assert result['settings']['taxes_enabled'] is False
    assert (result['details'].query('year > 0').y == .07).all()
    assert result['details'].total_tax.sum() == 0
    assert result['base'].total_tax.sum() == 0
    next(b for b in app.button if b.label == 'Restore taxes').click().run()
    assert app.session_state.taxes_enabled is True
    assert any('Inputs have changed' in w.value for w in app.warning)


def test_non_stochastic_mode_runs_one_zero_volatility_forecast():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=60).run()
    next(r for r in app.radio if r.label == 'Simulation type').set_value('Non-stochastic (zero volatility)').run()
    next(n for n in app.number_input if n.label == 'Years').set_value(2).run()
    volatility = next(n for n in app.number_input if n.label == 'Annual standard deviation of y (%)')
    assert volatility.value == 0
    assert volatility.disabled
    next(b for b in app.button if b.label == 'Run simulation').click().run(timeout=60)
    assert not app.exception
    assert not app.error
    assert app.session_state.result['settings']['non_stochastic']
    assert app.session_state.result['details'].simulation.nunique() == 1
    assert not app.metric


def test_app_reloads_stale_settings_definition():
    # Reproduce the long-running server retaining the old class after a code
    # update; app.py must recover before constructing the new Settings schema.
    import simulation
    from dataclasses import make_dataclass
    simulation.Settings = make_dataclass('Settings', [])
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=60).run()
    assert not app.exception
    next(r for r in app.radio if r.label == 'Simulation type').set_value('Non-stochastic (zero volatility)').run()
    next(n for n in app.number_input if n.label == 'Years').set_value(2).run()
    next(b for b in app.button if b.label == 'Run simulation').click().run(timeout=60)
    assert not app.exception
    assert app.session_state.result['settings']['non_stochastic']


def test_custom_return_defaults_and_reapply_historical_estimates():
    from sources import load_snapshot
    try:
        source = load_snapshot()
    except FileNotFoundError:
        from simulation import Settings
        source = {'mean_y': Settings().initial_y, 'std_y': Settings().std_y}
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=60).run()
    mean = lambda: next(w for w in app.number_input if w.label == 'Base case and first-year y (%)')
    std = lambda: next(w for w in app.number_input if w.label == 'Annual standard deviation of y (%)')
    assert abs(mean().value-source['mean_y']*100) < 1e-8
    assert abs(std().value-source['std_y']*100) < 1e-8
    mean().set_value(8.0).run()
    if not any(b.label == 'Use five-year y estimates' for b in app.button):
        return
    next(b for b in app.button if b.label == 'Use five-year y estimates').click().run()
    assert not app.exception
    assert abs(mean().value-source['mean_y']*100) < 1e-8
    assert abs(std().value-source['std_y']*100) < 1e-8


def test_custom_restores_historical_returns_after_cpi_only_preset():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=60).run()
    historical_mean = next(w for w in app.number_input if w.label == 'Base case and first-year y (%)').value
    historical_std = next(w for w in app.number_input if w.label == 'Annual standard deviation of y (%)').value
    next(w for w in app.radio if w.label == 'Projection mode').set_value('Evelyn preset').run()
    next(w for w in app.selectbox if w.label == 'Scenario preset').set_value(5).run()
    assert next(w for w in app.number_input if w.label == 'Base case and first-year y (%)').value == 0
    next(w for w in app.radio if w.label == 'Projection mode').set_value('Custom').run()
    next(w for w in app.radio if w.label == 'Simulation type').set_value('Stochastic').run()
    assert not app.exception
    assert next(w for w in app.number_input if w.label == 'Base case and first-year y (%)').value == historical_mean
    assert next(w for w in app.number_input if w.label == 'Annual standard deviation of y (%)').value == historical_std
    # Manual custom edits must survive ordinary reruns.
    next(w for w in app.number_input if w.label == 'Base case and first-year y (%)').set_value(1.25).run()
    assert next(w for w in app.number_input if w.label == 'Base case and first-year y (%)').value == 1.25


def test_existing_custom_session_gets_new_return_defaults_once():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=60)
    app.session_state.initial_y = 0.0
    app.session_state.std_y = 0.0
    app.run()
    assert not app.exception
    assert next(w for w in app.number_input if w.label == 'Base case and first-year y (%)').value < 0
    assert next(w for w in app.number_input if w.label == 'Annual standard deviation of y (%)').value > 13


def test_new_pension_strategy_tax_and_fee_controls_reach_engine():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=60).run()
    next(w for w in app.radio if w.label == 'Simulation type').set_value('Non-stochastic (zero volatility)').run()
    next(w for w in app.number_input if w.label == 'Years').set_value(1).run()
    assert next(w for w in app.selectbox if w.label == 'Withdrawal strategy').value == 'estate'
    assert next(w for w in app.selectbox if w.label == 'Tax rules').value == 'current_law'
    shares=[w for w in app.number_input if w.label == 'Tax-free share of SIPP withdrawals (%)']
    assert [w.value for w in shares] == [0.0,25.0]
    shares[1].set_value(0.0).run()
    next(w for w in app.selectbox if w.label == 'Withdrawal strategy').set_value('annual_tax').run()
    next(w for w in app.selectbox if w.label == 'Tax rules').set_value('legacy_2026_27').run()
    next(w for w in app.number_input if w.label == 'Additional annual investment fee (%)').set_value(1.0).run()
    next(b for b in app.button if b.label == 'Run simulation').click().run(timeout=60)
    assert not app.exception and not app.error
    r=app.session_state.result
    assert r['settings']['ann_tax_free_share'] == 0
    assert r['settings']['annual_fee'] == .01
    assert r['settings']['withdrawal_strategy'] == 'annual_tax'
    assert r['settings']['tax_rules'] == 'legacy_2026_27'
    assert len(app.metric) == 0
    assert 'strategy_comparison' in r and 'strategy_sensitivity' in r
