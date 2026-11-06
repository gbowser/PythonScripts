"""Nominal tax accounting at the boundary of the real-pound portfolio engine."""
from dataclasses import replace

import numpy as np

from tax import update_loss_forward
from withdrawals import plan_withdrawals, taxable_pension


class NominalTaxLedger:
    """Retain actual pound acquisition costs and capital losses, without deflating them."""

    def __init__(self, opening_real_balances, gains, tfc_remaining=(0.0,0.0), tax_free_shares=(0.0,0.0)):
        self.bases = np.array([opening_real_balances[0]-gains[0],
                               opening_real_balances[3]-gains[1]], dtype=float)
        if np.any(self.bases < 0):
            raise ValueError('GIA acquisition costs cannot be negative.')
        self.tfc_remaining = np.array(tfc_remaining,dtype=float)
        self.tax_free_shares = tuple(tax_free_shares)
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
                 nominal_yields, threshold_scale, dividend_shares, pension_relief=(0.0,0.0),
                 taxes_enabled=True, *, property_income=(0.0,0.0), params=None,
                 estate_goals=None):
        balances = real_balances*price_index
        target = real_target*price_index
        if params is None:
            # Preserve canonical solver inputs from the legacy grouped
            # non-savings treatment, including property before rounding.
            non_savings = np.asarray(non_savings)+np.asarray(property_income)
            property_income = (0.0,0.0)
        forced = np.zeros(6)
        remaining = self.tfc_remaining.copy()
        ns = np.array(non_savings,dtype=float)
        if estate_goals is not None:
            pair = np.minimum(np.maximum(0.0,estate_goals), balances[[2,5]])
            if pair.sum() > target: pair *= target/pair.sum()
            forced[[2,5]] = pair
            for j in range(2):
                taxable = taxable_pension(pair[j],self.tax_free_shares[j],remaining[j])
                ns[j] += taxable
                remaining[j] -= pair[j]-taxable
            balances = np.maximum(0.0,balances-forced)
            target = max(0.0,target-forced.sum())
            if balances[[0,1,3,4]].sum() >= target-1e-8:
                balances[[2,5]] = 0.0
        plan = plan_withdrawals(balances,self.bases,self.losses,ns,interest,nominal_yields,
                    target,threshold_scale,dividend_shares,pension_relief,taxes_enabled,self.year_gains,
                    tax_free_shares=self.tax_free_shares,tfc_remaining=remaining,
                    property_income=property_income,params=params,gia_first=estate_goals is not None)
        return replace(plan,withdrawals=(plan.withdrawals+forced)/price_index,
                       shortfall=plan.shortfall/price_index)

    def record_pension_withdrawals(self, nominal_withdrawals):
        gross = np.asarray(nominal_withdrawals)[[2,5]]
        free = np.minimum(gross*np.array(self.tax_free_shares),self.tfc_remaining)
        self.tfc_remaining -= free
        return free

    def record_disposals(self, real_balances, real_withdrawals, price_index):
        """Accumulate monthly nominal gains; settle losses/allowance once a year."""
        for j in range(2):
            k = j*3
            fraction = real_withdrawals[k]/real_balances[k] if real_balances[k] > 0 else 0.0
            self.year_gains[j] += real_withdrawals[k]*price_index-self.bases[j]*fraction
            self.bases[j] *= 1-fraction

    def finish_year(self, threshold_scale, params=None):
        self.losses = np.array([update_loss_forward(g, loss, threshold_scale, params)
                                for g, loss in zip(self.year_gains, self.losses)])
        return self.year_gains.copy()

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
