from dataclasses import replace
from pathlib import Path
import json

import numpy as np
import pytest

from simulation import Settings, run_path
from tax_ledger import NominalTaxLedger
from withdrawals import plan_withdrawals

CASES = json.loads((Path(__file__).parent/'fixtures'/'nominal_engine_portfolio.json').read_text(encoding='utf-8'))['cases']


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['name'])
def test_real_engine_preserves_pre_refactor_portfolio_forecasts(case):
    settings = Settings(**case['settings'])
    result = run_path(settings, case['ys'], case['crash_year'])
    for expected in case['expected']:
        row = result.loc[result.year == expected['year']].iloc[0]
        assert row.portfolio_real == pytest.approx(expected['portfolio_real'], abs=.01, rel=0)
        assert row.portfolio_nominal == pytest.approx(expected['portfolio_nominal'], abs=.01, rel=0)


def test_real_growth_and_real_cashflow_accounting():
    s = Settings(years=4, gift=100000, gift_years=3, property_sale_enabled=True,
                 property_sale_date='2028-05-01', taxes_enabled=False)
    result = run_path(s, [.025]*4, crash_year=3)
    assert result.real_return.iloc[1] == pytest.approx(1.045/1.02-1)
    assert result.real_return.iloc[1] != pytest.approx(.025)
    assert result.regular_requested_real.iloc[1:].tolist() == pytest.approx([150000/1.02]*4)
    assert result.gift_requested_real.iloc[1] == pytest.approx(100000/1.02)
    assert result.gift_requested_real.iloc[2] == pytest.approx(100000/1.02**2)
    for _, row in result.iloc[1:].iterrows():
        closing = (row.opening_portfolio_real+row.investment_gain_real+row.property_sale_proceeds_real
                   -row.gross_withdrawal_real+row.ann_pension_contribution_gross_real)
        assert row.portfolio_real == pytest.approx(closing, abs=.0001)
        assert row.portfolio_nominal == pytest.approx(row.portfolio_real*row.inflation_index)
        assert row['Ann GIA_real'] == pytest.approx(row['Ann GIA']/row.inflation_index)


def test_nominal_tax_basis_is_not_inflation_indexed():
    real_balances = np.array([0, 0, 0, 100000, 0, 0], dtype=float)
    ledger = NominalTaxLedger(real_balances, [0, 0])
    prices = 1.02**2
    # No real growth: £100k of purchasing power is £104,040 nominal after two
    # years. Tax must recognise the £4,040 nominal gain, not a zero real gain.
    plan = ledger.allocate(real_balances, 100000, prices, [0, 60000], [0, 0],
                           [0, 0], 1.0, [.5, .5])
    gains = ledger.realise(real_balances, plan.withdrawals, prices, 1.0)
    assert gains[1] == pytest.approx(4040)
    assert plan.taxes[1].capital_gains_tax == pytest.approx((4040-3000)*.24)
    assert plan.withdrawals.sum() == pytest.approx(100000)


def test_tax_allocator_is_stable_under_currency_conversion_roundoff():
    values = np.array([200000, 0, 800000, 250000, 0, 500000], dtype=float)
    args = ([150000, 230000], [0, 0], [3354, 22513], [1644, 352], [5000, 6000], 150000, 1.0, [.5, .5])
    first = plan_withdrawals(values, *args)
    second = plan_withdrawals(values*(1+1e-14), *args)
    assert second.withdrawals == pytest.approx(first.withdrawals, abs=.0001)
    assert sum(t.total for t in second.taxes) == pytest.approx(sum(t.total for t in first.taxes), abs=.01)
