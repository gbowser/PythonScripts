"""Nominal tax accounting at the boundary of the real-pound portfolio engine."""
from dataclasses import replace

import numpy as np

from tax import update_loss_forward
from withdrawals import plan_withdrawals


class NominalTaxLedger:
    """Retain actual pound acquisition costs and capital losses, without deflating them."""

    def __init__(self, opening_real_balances, gains):
        self.bases = np.array([opening_real_balances[0]-gains[0],
                               opening_real_balances[3]-gains[1]], dtype=float)
        if np.any(self.bases < 0):
            raise ValueError('GIA acquisition costs cannot be negative.')
        self.losses = np.zeros(2)
        self.year_gains = np.zeros(2)

    def begin_year(self):
        self.year_gains.fill(0.0)

    def fund_isas(self, real_balances, price_index, nominal_limit=20000.0):
        """Sell each owner's GIA and subscribe to their own ISA, in place.

        Proceeds stay inside the portfolio. Carry-forward losses and the annual
        CGT exemption are applied once, after combining all this year's sales.
        """
        transfers, gains = np.zeros(2), np.zeros(2)
        for j in range(2):
            gia, isa = j*3, j*3+1
            amount_real = min(real_balances[gia], nominal_limit/price_index)
            fraction = amount_real/real_balances[gia] if real_balances[gia] > 0 else 0.0
            transfers[j] = amount_real*price_index
            gains[j] = transfers[j]-self.bases[j]*fraction
            self.bases[j] *= 1-fraction
            self.year_gains[j] += gains[j]
            real_balances[gia] -= amount_real
            real_balances[isa] += amount_real
        return transfers, gains

    def reinvest(self, nominal_yields, nominal_sale_proceeds=0.0):
        self.bases += nominal_yields
        self.bases[1] += nominal_sale_proceeds

    def allocate(self, real_balances, real_target, price_index, non_savings, interest,
                 nominal_yields, threshold_scale, dividend_shares, pension_relief=(0.0, 0.0),
                 taxes_enabled=True):
        nominal_plan = plan_withdrawals(
            real_balances*price_index, self.bases, self.losses, non_savings, interest,
            nominal_yields, real_target*price_index, threshold_scale, dividend_shares,
            pension_relief, taxes_enabled, self.year_gains)
        # Only liabilities remain nominal. The portfolio receives withdrawals
        # and funding shortfalls expressed in valuation-date purchasing power.
        return replace(nominal_plan, withdrawals=nominal_plan.withdrawals/price_index,
                       shortfall=nominal_plan.shortfall/price_index)

    def realise(self, real_balances, real_withdrawals, price_index, threshold_scale):
        gains = []
        for j in range(2):
            index = j*3
            fraction = real_withdrawals[index]/real_balances[index] if real_balances[index] > 0 else 0.0
            gain = self.year_gains[j]+real_withdrawals[index]*price_index-self.bases[j]*fraction
            gains.append(gain)
            self.bases[j] *= 1-fraction
            self.losses[j] = update_loss_forward(gain, self.losses[j], threshold_scale)
        return gains
