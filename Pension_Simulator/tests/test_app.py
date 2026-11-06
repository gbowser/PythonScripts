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
    assert len(app.metric) == 3
    assert len(app.get("plotly_chart")) == 1
    assert {b.label for b in app.get("download_button")} == {
        "Deciles CSV", "Base case CSV", "All paths and assumptions ZIP", "Interactive chart HTML"}
    next(n for n in app.text_input if n.label == "Annual gift (£)").set_value("£100,000").run()
    assert any("Inputs have changed" in w.value for w in app.warning)


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
    assert any(m.label == 'Forecast final portfolio' for m in app.metric)


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
