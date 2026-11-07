from dataclasses import replace
from datetime import date
import numpy as np
import pytest

from simulation import Settings,run_path,simulate,pension_contribution


def settings(**changes):
    options=dict(start_date='2026-01-01',years=3,starting_balance=100000,inflation=0,
                 initial_y=0,withdrawal=15000,gift=0,income_yield=0,annual_fee=0,
                 gordon_citibank_pension=0,gordon_interest=0,ann_interest=0,
                 ann_state_pension=0,gordon_state_weekly=0,ann_property=12000,
                 ann_pension_contribution=0,withdrawal_strategy='annual_tax',taxes_enabled=False,
                 property_sale_enabled=True,property_sale_mode='threshold',property_sale_threshold=90000,
                 property_sale_amount=200000)
    options.update(changes)
    return Settings(**options)


def path(s,returns=None,crash=0):
    return run_path(s,[0]*s.years if returns is None else returns,crash,
                    account_balances=[0,s.starting_balance,0,0,0,0],initial_gains=[0,0])


def test_threshold_crossing_withdrawals_sell_once_and_stop_rent():
    p=path(settings())
    assert p.property_sale_proceeds.iloc[1:].tolist() == [200000,0,0]
    assert p.property_sale_actual_date.iloc[1] == '2026-11-01'  # tenth monthly payment
    assert p.property_sale_trigger_value_real.iloc[1] == pytest.approx(90000)
    assert p.rental_profit_ann.iloc[1] == pytest.approx(12000*304/365)
    assert p.rental_profit_ann.iloc[2:].tolist() == [0,0]
    assert p.portfolio_real.iloc[1] == pytest.approx(285000)
    assert p.shortfall.iloc[1:].sum() == 0


def test_threshold_not_reached_and_disabled_sale_keep_rental_income():
    s=settings(withdrawal=0,property_sale_threshold=50000)
    p=path(s)
    assert p.property_sale_proceeds.iloc[1:].sum() == 0
    assert (p.rental_profit_ann.iloc[1:] == 12000).all()
    q=path(replace(s,property_sale_enabled=False,property_sale_threshold=200000))
    assert q.property_sale_proceeds.iloc[1:].sum() == 0


def test_opening_value_trigger_is_immediate_and_has_no_rent():
    p=path(settings(property_sale_threshold=100000))
    assert p.property_sale_actual_date.iloc[1] == '2026-01-01'
    assert p.rental_profit_ann.iloc[1:].sum() == 0
    assert p.portfolio_real.iloc[1] == pytest.approx(285000)


def test_threshold_zero_sale_can_fund_the_payment_which_exhausts_portfolio():
    p=path(settings(starting_balance=500,property_sale_threshold=0,years=1))
    assert p.property_sale_actual_date.iloc[1] == '2026-02-01'
    assert p.regular_paid.iloc[1] == pytest.approx(15000)
    assert p.shortfall.iloc[1] == 0
    assert p.portfolio_real.iloc[1] == pytest.approx(185500)


def test_crash_can_trigger_sale_after_loss_and_proceeds_are_not_crashed_again():
    p=path(settings(withdrawal=0,property_sale_threshold=70000,crash_loss=.4),crash=1)
    assert p.property_sale_actual_date.iloc[1] == '2027-01-01'
    assert p.property_sale_trigger_value_real.iloc[1] == pytest.approx(60000)
    assert p.portfolio_real.iloc[1] == pytest.approx(260000)
    assert p.property_sale_investment_gain.iloc[1] == 0


def test_threshold_is_real_and_each_path_uses_its_own_returns():
    s=settings(withdrawal=0,inflation=.02,property_sale_threshold=95000)
    steady=path(s,[0,0,0])
    falling=path(s,[-.12,0,0])
    assert steady.property_sale_proceeds.sum() == 0
    assert falling.property_sale_proceeds.sum() == 200000
    assert falling.property_sale_trigger_value_real.dropna().iloc[0] <= 95000
    assert falling.rental_profit_ann.iloc[-1] == 0
    event=falling[falling.property_sale_triggered].iloc[0]
    assert event.property_sale_trigger_value == pytest.approx(
        event.property_sale_trigger_value_real*event.property_sale_proceeds/event.property_sale_proceeds_real)
    # Nominal sums and the real ledger reconcile after the triggered deposit.
    for _,r in falling.iloc[1:].iterrows():
        assert r.portfolio_real == pytest.approx(r.opening_portfolio_real+r.investment_gain_real+
            r.property_sale_proceeds_real-r.gross_withdrawal_real-r.annual_fees_real)


def test_threshold_sale_and_legacy_date_mode_are_distinct_and_validated():
    s=settings(property_sale_date='2020-01-01')
    s.validate()  # unused date does not prevent a threshold run
    with pytest.raises(ValueError): replace(s,property_sale_mode='date').validate()
    for change in [{'property_sale_threshold':-1},{'property_sale_threshold':float('nan')},
                   {'property_sale_mode':'unknown'}]:
        with pytest.raises(ValueError): replace(s,**change).validate()


def test_bank_contribution_is_grossed_up_then_stops_when_relief_ends():
    s=settings(start_date='2030-11-05',property_sale_enabled=False,withdrawal=0,
               ann_pension_contribution=2880,ann_contribution_is_net=True,ann_contribution_requires_relief=True)
    p=path(s)
    assert p.ann_pension_contribution_net.iloc[1:].tolist() == [2880,0,0]
    assert p.ann_pension_contribution_gross.iloc[1:].tolist() == [3600,0,0]
    assert p.ann_pension_relief_at_source.iloc[1:].tolist() == [720,0,0]
    assert pension_contribution(s,date(2032,6,26)) == (0,0,0)
    assert pension_contribution(s,date(2032,6,25)) == (3600,2880,3600)
