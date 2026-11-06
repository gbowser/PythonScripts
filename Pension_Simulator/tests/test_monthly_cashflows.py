from dataclasses import replace

import numpy as np
import pytest

from simulation import Settings as ModelSettings, run_path

def Settings(**changes):
    options=dict(withdrawal_strategy='annual_tax', tax_rules='legacy_2026_27', ann_tax_free_share=0.0)
    options.update(changes)
    return ModelSettings(**options)



def quiet(**changes):
    return replace(Settings(years=1, starting_balance=100000, inflation=0, initial_y=0,
                            withdrawal=15000, gift=0, income_yield=0,
                            gordon_citibank_pension=0, gordon_interest=0, ann_interest=0,
                            ann_property=0, ann_state_pension=0, ann_pension_contribution=0), **changes)


def test_first_year_inflation_and_actual_nominal_receipts():
    s = quiet(starting_balance=1000000, withdrawal=150000, inflation=.02, taxes_enabled=False)
    p = run_path(s, [.025], account_balances=[0, 1000000, 0, 0, 0, 0], initial_gains=[0, 0])
    expected = sum((40000 if m == 12 else 10000)*1.02**(m/12) for m in range(1,13))
    assert p.regular_requested.iloc[1] == pytest.approx(151896.067004)
    assert p.regular_paid.iloc[1] == pytest.approx(expected)
    assert p.regular_paid_real.iloc[1] == pytest.approx(150000)
    assert p.gross_withdrawal_real.iloc[1] == pytest.approx(150000)
    assert p['withdrawal_Gordon ISA_real'].iloc[1] == pytest.approx(150000)


def test_monthly_sipp_receipts_share_one_personal_allowance():
    s = quiet()
    p = run_path(s, [0], account_balances=[0, 0, 100000, 0, 0, 0], initial_gains=[0, 0])
    assert p.income_tax.iloc[1] == pytest.approx((15000-12570)*.2)
    assert p.total_tax.iloc[1] == pytest.approx(486)
    assert p.spendable_after_tax.iloc[1] == pytest.approx(14514)


@pytest.mark.parametrize('gain', [90000, -20000])
def test_monthly_gia_disposals_share_one_cgt_exemption_and_loss_pool(gain):
    s = quiet(withdrawal=30000, ann_property=60000)
    p = run_path(s, [0], account_balances=[0, 0, 0, 100000, 0, 0], initial_gains=[0, gain])
    row = p.iloc[1]
    realised = gain*(row['withdrawal_Ann GIA']+row.gia_to_isa_ann)/100000
    assert row.realised_gain_ann == pytest.approx(realised, abs=.001)
    assert row.cgt == pytest.approx(max(0, realised-3000)*.24, abs=.001)
    assert row.loss_forward_ann == pytest.approx(max(0, -realised), abs=.001)


def test_late_property_sale_does_not_fund_earlier_missed_receipts():
    s = quiet(starting_balance=1000, withdrawal=150000, taxes_enabled=False,
              property_sale_enabled=True, property_sale_date='2027-11-05', property_sale_amount=1000000)
    p = run_path(s, [0], account_balances=[0, 1000, 0, 0, 0, 0], initial_gains=[0, 0])
    assert p.regular_paid.iloc[1] == pytest.approx(41000)
    assert p.shortfall.iloc[1] == pytest.approx(109000)
    assert p.portfolio_nominal.iloc[1] == pytest.approx(960000)


def test_full_crash_preserves_receipts_already_paid():
    s = quiet(withdrawal=15000, crash_loss=1, taxes_enabled=False)
    p = run_path(s, [0], crash_year=1, account_balances=[0, 100000, 0, 0, 0, 0], initial_gains=[0, 0])
    assert p.regular_paid.iloc[1] == pytest.approx(11000)
    assert p.shortfall.iloc[1] == pytest.approx(4000)
    assert p.portfolio_nominal.iloc[1] == 0
