from dataclasses import replace
from datetime import date

import numpy as np
import pytest

from simulation import Settings as ModelSettings, run_path

def Settings(**changes):
    options=dict(withdrawal_strategy='annual_tax', tax_rules='legacy_2026_27', ann_tax_free_share=0.0)
    options.update(changes)
    return ModelSettings(**options)



def settings(**changes):
    base = Settings(start_date="2026-01-01", starting_balance=1000, years=3,
                    inflation=0, initial_y=0, income_yield=0, withdrawal=0, gift=0,
                    gordon_citibank_pension=0, gordon_interest=0, ann_interest=0,
                    ann_state_pension=0, ann_pension_contribution=0,
                    property_sale_enabled=True, property_sale_date="2026-07-02",
                    property_sale_amount=100000)
    return replace(base, **changes)


def path(s, returns=None, crash=0):
    return run_path(s, [0]*s.years if returns is None else returns, crash,
                    account_balances=[0, 1000, 0, 0, 0, 0], initial_gains=[0, 0])


def test_midperiod_sale_stops_rent_and_deposits_once_without_cgt():
    s = settings()
    p = path(s)
    assert p.rental_profit_ann.iloc[1] == pytest.approx(13019*182/365)
    assert p.rental_profit_ann.iloc[2:].tolist() == [0, 0]
    assert p.property_sale_proceeds.iloc[1:].tolist() == [100000, 0, 0]
    assert p['Ann GIA'].iloc[1:].tolist() == [80000, 60000, 40000]
    assert p['Ann ISA'].iloc[1:].tolist() == [20000, 40000, 60000]
    assert (p.cgt.iloc[1:] == 0).all()
    assert p.portfolio_nominal.iloc[-1] == 101000


def test_proceeds_gain_only_postsale_return_and_have_full_acquisition_cost():
    s = settings(withdrawal=1000, ann_property=0)
    p = path(s, [.1, .1, .1])
    expected_gain = 100000*(1.1**(183/365)-1)
    assert p.property_sale_investment_gain.iloc[1] == pytest.approx(expected_gain)
    assert p.investment_gain.iloc[1] < 100+expected_gain  # early receipts stop earning returns
    # Cash from ISA covers part of spending; any GIA sale taxes only the
    # investment gain fraction, not the tax-exempt property-sale principal.
    assert 0 < p.realised_gain_ann.iloc[1] < 20000  # ISA subscription sells only a gain fraction
    for _, r in p.iloc[1:].iterrows():
        assert r.portfolio_nominal == pytest.approx(
            r.opening_portfolio+r.investment_gain+r.property_sale_proceeds-r.gross_withdrawal, abs=.001)


def test_sale_on_period_boundaries_and_disabled_or_outside_horizon():
    s = settings(property_sale_date="2027-01-01")
    p = path(s)
    assert p.rental_profit_ann.iloc[1] == 13019
    assert p.rental_profit_ann.iloc[2] == 0
    assert p.property_sale_proceeds.iloc[1:].tolist() == [100000, 0, 0]
    assert p.property_sale_investment_gain.iloc[1] == 0
    first = path(replace(s, property_sale_date=s.start_date))
    assert first.rental_profit_ann.iloc[1] == 0
    assert first.property_sale_proceeds.iloc[1] == 100000
    for config in [replace(s, property_sale_enabled=False), replace(s, property_sale_date="2030-01-01")]:
        result = path(config)
        assert result.property_sale_proceeds.iloc[1:].sum() == 0
        assert (result.rental_profit_ann.iloc[1:] == 13019).all()
    with pytest.raises(ValueError, match="precede"):
        replace(s, property_sale_date="2025-12-31").validate()


def test_new_gia_yield_is_taxed_and_zero_proceeds_still_end_rental():
    s = settings(property_sale_date="2026-01-01", income_yield=.1)
    p = path(s)
    assert p.gia_yield_ann.iloc[1] == 10000
    assert p.income_tax.iloc[1] == 0  # within PA with no other Ann income
    q = path(replace(s, property_sale_amount=0))
    assert (q.rental_profit_ann.iloc[1:] == 0).all()
    assert q.property_sale_proceeds.iloc[1:].sum() == 0


def test_crash_exposes_invested_proceeds_but_not_period_end_deposit():
    s = settings(property_sale_date="2026-01-01", ann_property=0)
    p = path(s, [.1, 0, 0], crash=1)
    assert p.property_sale_investment_gain.iloc[1] == pytest.approx(100000*(1.1*.6-1))
    q = path(replace(s, property_sale_date="2027-01-01"), [.1, 0, 0], crash=1)
    assert q.property_sale_investment_gain.iloc[1] == 0
    assert q['Ann GIA'].iloc[1] == 80000
    assert q.gia_to_isa_ann.iloc[1] == 20000
