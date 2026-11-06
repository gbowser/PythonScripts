from dataclasses import replace
from datetime import date
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from simulation import Settings as ModelSettings, pension_during, run_path, simulate, threshold_scale

def Settings(**changes):
    options=dict(withdrawal_strategy='annual_tax', tax_rules='legacy_2026_27', ann_tax_free_share=0.0, ann_contribution_is_net=False)
    options.update(changes)
    return ModelSettings(**options)

from sources import interpolate, read_workbook
from tax import income_tax, owner_tax, update_loss_forward
from withdrawals import plan_withdrawals


def test_income_tax_published_examples_and_taper():
    assert income_tax(12570, 0, 0)[0] == 0
    assert income_tax(50270, 0, 0)[0] == pytest.approx(7540)
    assert income_tax(125140, 0, 0)[0] == pytest.approx(42516)
    # HMRC dividend example: £29,570 wages + £3,000 dividends.
    assert income_tax(29570, 0, 3000)[0] == pytest.approx(3400+2500*.1075)


def test_gordon_historical_hmrc_calculation_2025_26():
    # Historic income only: RBC 7,666, James Hay 37,000, Citibank 3,354;
    # bank + securities interest 1,804 and UK/foreign dividends 595.
    # HMRC displayed a rounded gross Gift Aid band extension of 1,263.
    liability, pa, taxable = income_tax(7666+37000+3354, 1804, 475+120,
                                      gift_aid_gross=1263,
                                      dividend_rates=(.0875, .3375, .3935))
    assert pa == 12570
    assert taxable == 37849
    assert round(liability, 2) == 7259.11
    assert round(17466-liability, 2) == 10206.89
    # Historic rates are explicit; the forward model still uses 2026/27 rates.
    assert income_tax(48020, 1804, 595, gift_aid_gross=1263)[0] > liability


def test_ann_historical_hmrc_calculation_2025_26():
    liability, pa, taxable = income_tax(13019+9306, 352+815, 6769+10344,
                                      relief_at_source_gross=2880,
                                      dividend_rates=(.0875, .3375, .3935),
                                      truncate_components=True)
    assert pa == 12570
    assert taxable == 28035
    assert liability == pytest.approx(3438.03)


def test_citibank_is_ordinary_pension_income_not_savings():
    s = Settings(years=2, withdrawal=0, gift=0, income_yield=0,
                 gordon_interest=0, ann_property=0, ann_state_pension=0,
                 gordon_citibank_pension=20000, gordon_citibank_growth=.02, ann_interest=0)
    p = run_path(s, [.025, .025])
    assert p.income_tax.iloc[1] == pytest.approx((20000-12570)*.2)
    assert p.citibank_pension_gordon.iloc[1] == 20000
    assert p.citibank_pension_gordon.iloc[2] == 20400
    assert p.external_interest_gordon.iloc[1] == 0
    assert p.external_income.iloc[1] == 20000
    # Applying savings allowances to this pension would understate its tax.
    assert p.income_tax.iloc[1] > income_tax(0, 20000, 0)[0]


def test_savings_allowances_occupy_bands_and_pa_allocation():
    assert income_tax(12570, 6000, 0)[0] == 0
    assert income_tax(20000, 2000, 0)[0] == pytest.approx(1486+200)
    # Allocate remaining PA to dividends where savings starting-rate covers interest.
    assert income_tax(10000, 3000, 3000)[0] == pytest.approx(0)
    # Dividend allowance occupies basic-rate space; it is not a deduction.
    assert income_tax(50270, 0, 1000)[0] == pytest.approx(7540+500*.3575)


def test_capital_gains_examples_and_losses():
    assert owner_tax(32570, 0, 0, 12600, 0).capital_gains_tax == pytest.approx(1728)
    assert owner_tax(32570, 0, 0, 52600, 0).capital_gains_tax == pytest.approx(10842)
    assert update_loss_forward(-5000, 1000, 1) == 6000
    assert update_loss_forward(4000, 6000, 1) == 5000
    assert owner_tax(10000, 0, 0, 8000, 6000).capital_gains_tax == 0


def test_auto_income_mix_is_no_worse_than_grid():
    for n in (0, 9494, 20000, 45000, 98000, 130000):
        automatic = owner_tax(n, 3354, 14000, 5000, 0)
        grid = [owner_tax(n, 3354, 14000, 5000, 0, dividend_share=f).total for f in np.linspace(0, 1, 101)]
        assert automatic.total <= min(grid)+1e-6


def test_thresholds_increase_only_every_five_years():
    assert threshold_scale(5, .02) == 1
    assert threshold_scale(6, .02) == pytest.approx(1.02**5)
    assert threshold_scale(10, .02) == pytest.approx(1.02**5)
    assert threshold_scale(11, .02) == pytest.approx(1.02**10)


def test_state_pension_eligibility_and_april_uprating():
    eligible = date(2028, 6, 27)
    assert pension_during(date(2027, 11, 5), date(2028, 6, 27), eligible, 10000, .025) == 0
    result = pension_during(date(2028, 6, 27), date(2028, 11, 5), eligible, 10000, .025)
    assert result == pytest.approx(10000*1.025**2*(date(2028, 11, 5)-eligible).days/365)
    assert pension_during(date(2026, 4, 6), date(2027, 4, 6), date(2023, 6, 26), 9494, .025) == 9494


def test_cashflow_yield_is_not_double_counted_and_gifts_stop():
    s = Settings(years=4, withdrawal=1000, gift=500, gift_years=4, income_yield=.0267)
    p = run_path(s, np.full(4, .025), crash_year=2)
    assert p.gift_requested.iloc[1:].tolist() == [500, 0, 0, 0]
    assert p.total_return.iloc[1] == pytest.approx(.045)
    assert p.total_return.iloc[2] == pytest.approx(1.045*.6-1)
    assert p.regular_requested.iloc[2] == pytest.approx(sum((1000*(4 if m == 12 else 1)/15)*1.02**(1+m/12) for m in range(1,13)))
    for _, r in p.iloc[1:].iterrows():
        assert r.portfolio_nominal == pytest.approx(r.opening_portfolio+r.investment_gain-r.gross_withdrawal+r.ann_pension_contribution_gross, abs=.001)
        assert r.gross_withdrawal == pytest.approx(r.regular_paid+r.gift_paid+r.ann_contribution_portfolio_draw, abs=.001)
        assert r.spendable_after_tax == pytest.approx(max(0, r.regular_paid-r.total_tax))
        assert r.portfolio_real == pytest.approx(r.portfolio_nominal/r.inflation_index)


def test_isa_taxfree_and_all_sipp_withdrawals_taxable():
    params = ([0, 0], [0, 0], [0, 0], [0, 0], [0, 0])
    isa = plan_withdrawals([0, 500000, 0, 0, 0, 0], *params, target=150000, scale=1)
    assert sum(t.total for t in isa.taxes) == 0
    assert isa.withdrawals.sum() == 150000
    sipp = plan_withdrawals([0, 0, 500000, 0, 0, 0], *params, target=100000, scale=1)
    assert sum(t.total for t in sipp.taxes) > 0
    assert sipp.withdrawals.sum() == pytest.approx(100000, abs=.01)


def test_withdrawal_optimizer_against_two_sipp_grid():
    plan = plan_withdrawals([0, 0, 200000, 0, 0, 200000], [0, 0], [0, 0], [10000, 20000],
                            [0, 0], [0, 0], 80000, 1)
    gross = plan.withdrawals.sum()
    # At the selected gross, no allocation on this independent grid should pay less tax.
    grid = [owner_tax(10000+x, 0, 0, 0, 0).total+owner_tax(20000+gross-x, 0, 0, 0, 0).total
            for x in np.linspace(0, gross, 1001)]
    assert sum(t.total for t in plan.taxes) <= min(grid)+.01


def test_exhaustion_never_borrows_and_reports_unpaid_obligations():
    s = Settings(years=2, starting_balance=1000, withdrawal=150000, gift=150000, ann_pension_contribution=0)
    p = run_path(s, [.025, .025], account_balances=[0, 1000, 0, 0, 0, 0], initial_gains=[0, 0])
    assert p.portfolio_nominal.tolist()[1:] == [0, 0]
    assert (p.shortfall.iloc[1:] > 0).all()
    assert p.gift_paid.iloc[1] == 0


def test_cpi_linked_citibank_and_family_gift_cutoff():
    s = Settings(years=3, withdrawal=0, gift=5000, gift_years=3, income_yield=0,
                 gordon_citibank_pension=20000)
    p = run_path(s, [.025]*3, crash_year=2)
    assert p.citibank_pension_gordon.iloc[2] == pytest.approx(20000*1.02)
    assert p.gift_paid.iloc[1:].tolist() == pytest.approx([5000, 0, 0])
    assert p.gross_withdrawal.iloc[2] == 0


def test_historical_relief_reduces_adjusted_net_income():
    # Gross donation extends the basic band and reduces adjusted net income.
    plain = income_tax(105000, 0, 0)
    donor = income_tax(105000, 0, 0, gift_aid_gross=1250)
    assert donor[1] == pytest.approx(plain[1]+625)
    assert donor[0] < plain[0]


def test_charity_excluded_and_bank_interest_external_gross():
    s = Settings(years=1, starting_balance=1000, withdrawal=0, gift=0, income_yield=0,
                 initial_y=-.02, gordon_citibank_pension=0, gordon_interest=0,
                 ann_property=0, ann_state_pension=0, ann_interest=0, ann_pension_contribution=0)
    p = run_path(s, [-.02], account_balances=[0, 1000, 0, 0, 0, 0], initial_gains=[0, 0])
    assert p.portfolio_nominal.iloc[1] == pytest.approx(1000)
    assert p.gross_withdrawal.iloc[1] == 0
    assert not any('charitable' in c for c in p.columns)
    defaults = Settings()
    assert defaults.gordon_interest == 1644
    assert defaults.ann_interest == 352
    q = run_path(replace(s, gordon_interest=20000), [-.02],
                 account_balances=[0, 1000, 0, 0, 0, 0], initial_gains=[0, 0])
    assert q.external_interest_gordon.iloc[1] == 20000
    assert q.income_tax.iloc[1] == pytest.approx(income_tax(0, 20000, 0)[0])


def test_ann_contribution_funding_and_age75_relief_cutoff():
    s = Settings(years=2, start_date='2030-11-05', withdrawal=0, gift=0, initial_y=-.02,
                 income_yield=0, ann_property=13019)
    p = run_path(s, [-.02, -.02])
    assert p.ann_pension_contribution_gross.iloc[1:].tolist() == [2880, 2880]
    assert p.ann_pension_contribution_net.iloc[1:].tolist() == [2304, 2880]
    assert p.ann_pension_relief_at_source.iloc[1:].tolist() == [576, 0]
    assert p.ann_contribution_external_cash.iloc[1:].tolist() == [2304, 2880]
    assert (p.ann_contribution_portfolio_draw.iloc[1:] == 0).all()
    q = run_path(replace(s, ann_contribution_from_portfolio=True), [-.02, -.02])
    assert q.ann_contribution_portfolio_draw.iloc[1:].tolist() == [2304, 2880]
    assert (q.ann_contribution_external_cash.iloc[1:] == 0).all()
    for _, row in q.iloc[1:].iterrows():
        assert row.gross_withdrawal == pytest.approx(row.ann_contribution_portfolio_draw, abs=.001)
        assert row.portfolio_nominal == pytest.approx(row.opening_portfolio-row.gross_withdrawal+2880)


def test_contribution_relief_flows_through_owner_tax():
    plain = owner_tax(105000, 0, 0, 10000, 0, dividend_share=.8)
    relief = owner_tax(105000, 0, 0, 10000, 0, dividend_share=.8, relief_at_source_gross=2880)
    assert relief.allowance == pytest.approx(plain.allowance+1440)
    assert relief.total < plain.total
    assert Settings().ann_property == 13019


def test_reproducible_draws_and_zero_volatility():
    s = Settings(years=2, std_y=0, initial_y=.07, withdrawal=0, gift=0)
    a, b = simulate(s), simulate(s)
    assert a["details"].equals(b["details"])
    assert a["details"].query("year==2").portfolio_nominal.nunique() == 1
    assert a["details"].query("year==2").portfolio_nominal.iloc[0] == pytest.approx(a["base"].portfolio_nominal.iloc[-1])
    c = simulate(replace(s, crash_enabled=True, crash_window=2, deterministic_crash_year=2))
    assert set(c["crash_years"]) <= {1, 2}
    assert c["base"].equals(a["base"])
    assert c["details"].query("year==1").y.nunique() == 1
    assert (a['details'].query('year > 0').y == .07).all()


def test_taxes_reduce_bank_spending_not_portfolio_value():
    s = Settings(years=4, withdrawal=300000, taxes_enabled=False)
    no_tax = run_path(s, [.025]*4)
    taxed = run_path(replace(s, taxes_enabled=True), [.025]*4)
    for column in ['income_tax', 'cgt', 'total_tax', 'tax_paid', 'unpaid_tax']:
        assert (no_tax[column].iloc[1:] == 0).all()
    for _, row in no_tax.iloc[1:].iterrows():
        assert row.gross_withdrawal == pytest.approx(row.regular_requested+row.gift_requested, abs=.001)
    assert taxed.total_tax.sum() > 0
    assert no_tax.portfolio_nominal.tolist() == pytest.approx(taxed.portfolio_nominal.tolist(), abs=.01)
    assert no_tax.spendable_after_tax.sum() > taxed.spendable_after_tax.sum()
    for _, row in taxed.iloc[1:].iterrows():
        assert row.gross_withdrawal == pytest.approx(row.regular_requested+row.gift_requested, abs=.001)
        assert row.gift_paid == pytest.approx(row.gift_requested)
    # Existing pension deposits and their relief stay independent of the switch.
    assert no_tax.ann_pension_relief_at_source.equals(taxed.ann_pension_relief_at_source)


def test_non_stochastic_mode_zeroes_volatility_and_fixes_crash_date():
    s = Settings(years=3, non_stochastic=True, std_y=.5, initial_y=.04,
                 taxes_enabled=False)
    a = simulate(s)
    b = simulate(replace(s, seed=123456))
    assert a['settings']['std_y'] == 0
    assert a['settings']['simulations'] == 1
    assert a['details'].simulation.nunique() == 1
    assert a['details'].equals(b['details'])
    assert (a['details'].query('year>0').y == .04).all()
    assert a['details'].portfolio_nominal.tolist() == a['base'].portfolio_nominal.tolist()
    crash = simulate(replace(s, crash_enabled=True, deterministic_crash_year=2))
    assert crash['crash_years'] == [2]
    assert crash['details'].query('crash==True').year.tolist() == [2]
    assert crash['details'].portfolio_nominal.tolist() == crash['stress'].portfolio_nominal.tolist()


def test_interpolation_and_bad_input():
    p = [(date(2020, 12, 30), 100), (date(2021, 1, 1), 121)]
    assert interpolate(p, date(2020, 12, 31)) == pytest.approx(110)
    with pytest.raises(ValueError):
        interpolate(p, date(2022, 1, 1))
    with pytest.raises(ValueError):
        simulate(Settings(inflation=float("nan")))


def test_workbook_reader(tmp_path):
    from openpyxl import Workbook
    wb = Workbook()
    s = wb.active
    s.title = "Pensions"
    s.cell(1, 2, date(2026, 11, 5)); s.cell(1, 9, 4335877)
    # A later row with an older date must not replace the latest valuation.
    s.cell(2, 2, date(2026, 11, 4)); s.cell(2, 9, 4323674)
    h = wb.create_sheet("Pension_Performance")
    h.cell(10, 2, .025)
    h.cell(11, 2, 2)
    for row, y in enumerate(range(2026, 2020, -1), 16):
        h.cell(row, 1, f'{y-1}–{y}')
        h.cell(row, 2, date(y-1, 11, 5)); h.cell(row, 3, date(y, 11, 5))
        h.cell(row, 4, .01*(y-2020)); h.cell(row, 5, 100); h.cell(row, 6, 102); h.cell(row, 7, .02)
    path = tmp_path/"fixture.xlsx"
    wb.save(path)
    out = read_workbook(path)
    assert out["balance"] == 4335877
    assert [h["year"] for h in out["history"]] == list(range(2022, 2027))

    assert out["mean_y"] == pytest.approx(.02)
    assert out["std_y"] == pytest.approx(np.std([0, .01, .02, .03, .04], ddof=1))
    assert out["cpi_lag_months"] == 2
    expected_cagr = np.prod([1.02,1.03,1.04,1.05,1.06])**.2-1
    assert out["portfolio_cagr"] == pytest.approx(expected_cagr)
    assert out["cpi_cagr"] == pytest.approx(.02)
    assert out["cagr_y"] == pytest.approx(expected_cagr-.02)
    assert out["vs_target_cagr"] == pytest.approx(expected_cagr-.02-.025)
    h.cell(16, 7, .05)
    wb.save(path)
    with pytest.raises(ValueError, match="Inconsistent CPI"):
        read_workbook(path)
