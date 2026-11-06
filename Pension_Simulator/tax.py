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


def _legacy_income_tax(non_savings, interest, dividends, scale=1.0, *,
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


def _legacy_owner_tax(non_savings, external_interest, yield_income, gain, loss_forward,
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


def update_loss_forward(gain, prior_losses, scale, params=None):
    if gain < 0:
        return prior_losses-gain
    return max(0.0, prior_losses-max(0.0, gain-(params.cgt_exemption if params is not None else 3000*scale)))


def _allocation_vertices(p, s, d, rem, n, basic, additional, psa, starting, da):
    """Vertices of the piecewise-linear PA allocation problem (property/savings).

    All kinks are vertical, horizontal or x+y=constant. Enumerating their
    intersections avoids a local numerical minimum in the three-way allocation.
    """
    if rem <= 0:
        return [(0.0, 0.0)]
    xs = {0.0, p, rem, rem-s, rem-d, n+p-starting}
    for band in (basic, additional):
        xs.update((n+p-band, n+p+psa-band))
    ys = {0.0, s, s-psa, rem, rem-p, rem-d}
    zs = {rem, rem-d, da-d+rem, s+n+p-starting-psa}
    for band in (basic, additional):
        zs.update((n+p+s-band, n+p+s+da-band))
    points = {(x,y) for x in xs for y in ys}
    points.update((x,z-x) for x in xs for z in zs)
    points.update((z-y,y) for y in ys for z in zs)
    return [(max(0.0,x), max(0.0,y)) for x,y in points
            if -1e-7 <= x <= p+1e-7 and -1e-7 <= y <= s+1e-7
            and -1e-7 <= rem-x-y <= d+1e-7]


def income_tax(non_savings, interest, dividends, scale=1.0, *, property_income=0.0,
               params=None, gift_aid_gross=0.0, relief_at_source_gross=0.0,
               dividend_rates=(.1075,.3575,.3935), truncate_components=False):
    if params is None:
        return _legacy_income_tax(non_savings+property_income, interest, dividends, scale,
            gift_aid_gross=gift_aid_gross, relief_at_source_gross=relief_at_source_gross,
            dividend_rates=dividend_rates, truncate_components=truncate_components)
    n,p,s,d = [max(0.0,float(v)) for v in (non_savings,property_income,interest,dividends)]
    gross = n+p+s+d
    relief = gift_aid_gross+relief_at_source_gross
    pa = max(0.0, params.allowance-max(0.0,gross-relief-params.taper_start)/2)
    nt = max(0.0,n-pa)
    rem = min(p+s+d,max(0.0,pa-n))
    basic = params.basic_band+relief
    additional = params.additional_threshold+relief
    taxable = max(0.0,gross-pa)
    psa = params.savings_allowances[0 if taxable <= basic else 1 if taxable <= additional else 2]
    costs=[]
    for ap,ass in _allocation_vertices(p,s,d,rem,nt,basic,additional,psa,params.starting_band,params.dividend_allowance):
        pt,st,dt = max(0,p-ap),max(0,s-ass),max(0,d-(rem-ap-ass))
        sn = min(st,max(0,params.starting_band-nt-pt)+psa)
        dn = min(dt,params.dividend_allowance)
        costs.append(sum((band_tax(0,nt,basic,additional,params.other_rates),
                          band_tax(nt,pt,basic,additional,params.property_rates),
                          band_tax(nt+pt+sn,st-sn,basic,additional,params.savings_rates),
                          band_tax(nt+pt+st+dn,dt-dn,basic,additional,params.dividend_rates))))
    return min(costs),pa,taxable


def owner_tax(non_savings, external_interest, yield_income, gain, loss_forward,
              scale=1.0, dividend_share=None, relief_at_source_gross=0.0, *,
              property_income=0.0, params=None):
    if params is None:
        return _legacy_owner_tax(non_savings+property_income, external_interest, yield_income,
                                 gain,loss_forward,scale,dividend_share,relief_at_source_gross)
    # The app uses fixed dividend shares. Retain automatic mix support for API
    # callers by checking a dense deterministic set plus allowance breakpoints.
    y=max(0.0,yield_income)
    shares = [dividend_share] if dividend_share is not None else [k/100 for k in range(101)]
    best=None
    for share in shares:
        div=y*share; interest=max(0.0,external_interest)+y-div
        cost,pa,taxable=income_tax(non_savings,interest,div,property_income=property_income,
                                 params=params,relief_at_source_gross=relief_at_source_gross)
        tg=max(0.0,gain-max(0.0,loss_forward)-params.cgt_exemption)
        low=min(tg,max(0.0,params.basic_band+relief_at_source_gross-taxable))
        item=TaxResult(cost,low*.18+(tg-low)*.24,div,interest,pa,taxable)
        if best is None or item.total < best.total: best=item
    return best
