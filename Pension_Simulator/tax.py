"""2026/27 England/Wales/NI tax model; rates held fixed by scenario design."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN


@dataclass(frozen=True)
class TaxResult:
    income_tax: float
    capital_gains_tax: float
    dividends: float
    interest: float
    allowance: float
    taxable_income: float

    @property
    def total(self):
        return self.income_tax + self.capital_gains_tax


def band_tax(start, amount, basic, additional, rates):
    """Tax an income interval; nil-rate income still occupies its tax bands."""
    end = start + max(0.0, amount)
    return (max(0.0, min(end, basic)-start)*rates[0]
            + max(0.0, min(end, additional)-max(start, basic))*rates[1]
            + max(0.0, end-max(start, additional))*rates[2])


def income_tax(non_savings, interest, dividends, scale=1.0, *,
               gift_aid_gross=0.0, relief_at_source_gross=0.0,
               dividend_rates=(.1075, .3575, .3935), truncate_components=False):
    """Allocate unused PA between savings/dividends at the beneficial breakpoints.

    Non-savings PA priority is used (pension/property income). Savings starting
    rate, PSA and dividend nil-rate band are then applied in statutory order.
    """
    n, s, d = (max(0.0, float(v)) for v in (non_savings, interest, dividends))
    gross = n+s+d
    relief = gift_aid_gross+relief_at_source_gross
    pa = max(0.0, 12570*scale-max(0.0, gross-relief-100000*scale)/2)
    n_tax = max(0.0, n-pa)
    rem = min(s+d, max(0.0, pa-n))
    basic = 37700*scale+relief
    additional = 125140*scale+relief-pa
    taxable = max(0.0, gross-pa)
    psa = (1000 if taxable <= basic else 500 if taxable <= additional else 0)*scale
    starter = max(0.0, 5000*scale-n_tax)
    lo, hi = max(0.0, rem-d), min(rem, s)
    candidates = [lo, hi, s-starter-psa, s-(basic-n_tax),
                  s-(additional-n_tax), 500*scale-d+rem]
    costs = []
    for a in {min(hi, max(lo, a)) for a in candidates}:
        st, dt = s-a, d-(rem-a)
        s_nil = min(st, starter+psa)
        d_nil = min(dt, 500*scale)
        components = [band_tax(0, n_tax, basic, additional, (.2, .4, .45)),
                      band_tax(n_tax+s_nil, st-s_nil, basic, additional, (.2, .4, .45)),
                      band_tax(n_tax+st+d_nil, dt-d_nil, basic, additional, dividend_rates)]
        if truncate_components:
            components = [float(Decimal(str(c)).quantize(Decimal('.01'), rounding=ROUND_DOWN)) for c in components]
        costs.append(sum(components))
    return min(costs), pa, taxable


def owner_tax(non_savings, external_interest, yield_income, gain, loss_forward,
              scale=1.0, dividend_share=None, relief_at_source_gross=0.0):
    """None dividend_share means choose the best hypothetical interest/dividend mix.

    The mix changes tax character only, never the amount of investment return.
    Reinvested income in an ISA/SIPP is excluded before calling this function.
    """
    y = max(0.0, yield_income)
    n = max(0.0, non_savings)
    e = max(0.0, external_interest)
    if dividend_share is None:
        gross = n+e+y
        pa = max(0.0, 12570*scale-max(0.0, gross-relief_at_source_gross-100000*scale)/2)
        nt = max(0.0, n-pa)
        rem = max(0.0, pa-n)
        taxable = max(0.0, gross-pa)
        basic, additional = 37700*scale+relief_at_source_gross, 125140*scale+relief_at_source_gross-pa
        psa = (1000 if taxable <= basic else 500 if taxable <= additional else 0)*scale
        starter = max(0.0, 5000*scale-nt)
        # All kinks in savings/dividend tax as the mixture changes. Include PA
        # allocation boundaries because savings nil-rate bands can free PA.
        savings_levels = [e, e+y, 0, rem, starter+psa, rem+starter+psa,
                          basic-nt, rem+basic-nt, additional-nt,
                          rem+additional-nt, e+y-500*scale,
                          e+y-rem-500*scale]
        dividends = {min(y, max(0.0, e+y-v)) for v in savings_levels}
    else:
        dividends = {y*dividend_share}
    best = None
    for div in dividends:
        interest = e+y-div
        cost, pa, taxable = income_tax(n, interest, div, scale, relief_at_source_gross=relief_at_source_gross)
        taxable_gain = max(0.0, gain-max(0.0, loss_forward)-3000*scale)
        low_gain = min(taxable_gain, max(0.0, 37700*scale+relief_at_source_gross-taxable))
        cgt = low_gain*.18+(taxable_gain-low_gain)*.24
        result = TaxResult(cost, cgt, div, interest, pa, taxable)
        if best is None or result.total < best.total:
            best = result
    return best


def update_loss_forward(gain, prior_losses, scale):
    if gain < 0:
        return prior_losses-gain
    return max(0.0, prior_losses-max(0.0, gain-3000*scale))
