from dataclasses import replace

import numpy as np
import pytest

from simulation import Settings, run_path
from tax_ledger import NominalTaxLedger


def test_each_isa_receives_twenty_thousand_nominal_each_year():
    s = Settings(years=7, withdrawal=0, gift=0, ann_pension_contribution=0)
    p = run_path(s, [.025]*7)
    assert p.gia_to_isa_gordon.iloc[1:].tolist() == pytest.approx([20000]*7)
    assert p.gia_to_isa_ann.iloc[1:].tolist() == pytest.approx([20000]*7)
    assert p.gia_to_isa_ann_real.iloc[7] == pytest.approx(20000/1.02**7)
    assert p.gross_withdrawal.iloc[1:].sum() == 0
    assert p.portfolio_real.iloc[-1] == pytest.approx(s.starting_balance*(1.045/1.02)**7)


def test_transfer_limited_to_own_gia_balance_and_not_repeated_with_empty_gia():
    s = Settings(years=2, starting_balance=65000, inflation=0, withdrawal=0, gift=0,
                 income_yield=0, ann_pension_contribution=0)
    p = run_path(s, [0, 0], account_balances=[5000, 10000, 0, 50000, 0, 0], initial_gains=[0, 0])
    assert p.gia_to_isa_gordon.iloc[1:].tolist() == [5000, 0]
    assert p.gia_to_isa_ann.iloc[1:].tolist() == [20000, 20000]
    assert p['Gordon ISA'].iloc[1] == 15000
    assert p['Ann ISA'].iloc[-1] == 40000
    assert p.portfolio_nominal.iloc[-1] == 65000


@pytest.mark.parametrize('initial_gain,expected_gain,expected_cgt,expected_losses', [
    (90000, 27000, 5760, 0), (-20000, -6000, 0, 6000)])
def test_isa_sale_and_cash_sale_share_one_cgt_allowance_and_loss_pool(initial_gain, expected_gain, expected_cgt, expected_losses):
    balances = np.array([0, 0, 0, 100000, 0, 0], dtype=float)
    ledger = NominalTaxLedger(balances, [0, initial_gain])
    ledger.begin_year()
    transfers, gains = ledger.fund_isas(balances, 1.0)
    assert transfers.tolist() == [0, 20000]
    plan = ledger.allocate(balances, 30000, 1, [0, 60000], [0, 0], [0, 0], 1, [.5, .5])
    realised = ledger.realise(balances, plan.withdrawals, 1, 1)
    assert realised[1] == pytest.approx(expected_gain, abs=.01)
    assert plan.taxes[1].capital_gains_tax == pytest.approx(expected_cgt, abs=.01)
    assert ledger.losses[1] == pytest.approx(expected_losses, abs=.01)
