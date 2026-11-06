from dataclasses import replace
import numpy as np
import pytest

from simulation import Settings,run_path,simulate


def settings(**changes):
    options=dict(years=2,starting_balance=1000,withdrawal=15000,gift=0,inflation=0,initial_y=0,
                 income_yield=0,gordon_citibank_pension=20000,gordon_interest=0,ann_interest=0,
                 ann_property=0,ann_state_pension=0,gordon_state_weekly=0,ann_pension_contribution=0,
                 withdrawal_strategy='annual_tax',gordon_tax_free_share=0,ann_tax_free_share=0)
    options.update(changes)
    return Settings(**options)


def test_external_income_continues_after_portfolio_depletion():
    s=settings()
    p=run_path(s,[0,0],account_balances=[0,1000,0,0,0,0],initial_gains=[0,0])
    assert p.regular_paid.iloc[1:].tolist() == pytest.approx([1000,0])
    assert p.net_annual_income_real.iloc[1:].tolist() == pytest.approx([19514,18514])
    assert p.net_annual_income_real.iloc[2] > 0


def test_income_subtracts_full_tax_and_excludes_gifts_from_receipts():
    s=settings(years=1,starting_balance=100000,gift=85000,gift_years=1,gordon_citibank_pension=0)
    p=run_path(s,[0],account_balances=[0,0,100000,0,0,0],initial_gains=[0,0])
    row=p.iloc[1]
    assert row.gift_paid == pytest.approx(85000)
    assert row.regular_paid == pytest.approx(15000)
    assert row.total_tax > row.regular_paid
    assert row.net_annual_income_real == pytest.approx(15000-row.total_tax)
    assert row.net_annual_income_real < 0
    assert row.spendable_after_tax_real == 0  # old receipt-only measure is retained separately


def test_real_income_uses_monthly_deflation_without_double_counting_reinvestment():
    s=settings(years=1,starting_balance=1000000,withdrawal=150000,inflation=.02,
               gordon_citibank_pension=0,income_yield=.0267,taxes_enabled=False)
    p=run_path(s,[.025],account_balances=[1000000,0,0,0,0,0],initial_gains=[0,0])
    row=p.iloc[1]
    assert row.gia_yield_gordon > 0
    assert row.net_annual_income_real == pytest.approx(150000)
    assert row.net_annual_income == pytest.approx(row.regular_paid)


def test_income_deciles_use_the_simulated_paths_and_exclude_year_zero():
    s=settings(starting_balance=50000,withdrawal=20000,std_y=.2,simulations=100)
    r=simulate(s,account_balances=[0,50000,0,0,0,0],initial_gains=[0,0])
    q=r['quantiles'].query("value == 'net_annual_income_real'")
    assert q.year.tolist() == [1,2]
    for year in (1,2):
        values=r['details'].query('year == @year').net_annual_income_real.to_numpy()
        row=q[q.year == year].iloc[0]
        assert [row.p10,row.p50,row.p90] == pytest.approx(np.quantile(values,[.1,.5,.9]))
