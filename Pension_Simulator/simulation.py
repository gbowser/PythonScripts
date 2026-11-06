"""Real-pound portfolio simulation, with a separate nominal tax ledger."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date
from pathlib import Path
import math

import numpy as np
import pandas as pd

from tax_ledger import NominalTaxLedger

ACCOUNT_NAMES = ["Gordon GIA", "Gordon ISA", "Gordon SIPP", "Ann GIA", "Ann ISA", "Ann SIPP"]
REFERENCE_BALANCES = np.array([179128, 407395, 2766090, 543702, 340267, 350021], dtype=float)
# User-specified starting-gain proxies: double the ~six-month CGT YTD
# annotations in the account schedule, rather than its Taxable Gains column.
REFERENCE_GAINS = [2*2902.0, 2*3837.0]

EVELYN_SCENARIOS = (
    (1, 0.0, .025),
    (2, 100000.0, .025),
    (3, 150000.0, .025),
    (4, 200000.0, .025),
    (5, 100000.0, 0.0),
    (6, 150000.0, 0.0),
    (7, 200000.0, 0.0),
)


def evelyn_label(number, gift, y):
    gifts = "no further gifts" if gift == 0 else f"£{gift/1000:.0f}k gifts × 5 years"
    growth = "CPI + 2.5%" if y else "CPI only"
    return f"Evelyn S{number}: {gifts}; {growth}"


def evelyn_preset(number):
    _, gift, y = next(s for s in EVELYN_SCENARIOS if s[0] == number)
    return dict(non_stochastic=True, years=34, initial_y=y, std_y=0.0,
                gift=gift, gift_years=5 if gift else 0, withdrawal=150000.0,
                ann_property=10000.0, crash_enabled=False, property_sale_enabled=False,
                ann_pension_contribution=0.0, ann_contribution_from_portfolio=False,
                gordon_citibank_pension=0.0, gordon_interest=0.0, ann_interest=0.0)


def evelyn_reference(number, years, inflation):
    if not number:
        return None
    data = pd.read_csv(Path(__file__).resolve().parent/'data'/'evelyn_reference.csv')
    data = data.loc[(data.scenario == number) & (data.year <= years)].copy()
    data = data.rename(columns={'portfolio_real_approx': 'portfolio_real'})
    # Original images show only real pounds. Nominal values are a conversion
    # using the selected CPI assumption, not a separate adviser forecast.
    data['portfolio_nominal'] = data.portfolio_real*(1+inflation)**data.year
    return data


@dataclass(frozen=True)
class Settings:
    start_date: str = "2026-11-05"
    starting_balance: float = 4335877.0
    years: int = 30
    simulations: int = 100
    non_stochastic: bool = False
    evelyn_scenario: int = 0
    inflation: float = .02
    initial_y: float = .025
    std_y: float = .10
    taxes_enabled: bool = True
    income_yield: float = .0267
    withdrawal: float = 150000.0
    gift: float = 150000.0
    gift_years: int = 10
    crash_enabled: bool = False
    crash_loss: float = .40
    crash_window: int = 20
    deterministic_crash_year: int = 10
    seed: int = 42
    earnings_growth: float = .025
    gordon_citibank_pension: float = 3354.36
    gordon_citibank_growth: float | None = None  # None follows scenario CPI
    gordon_interest: float = 1644.0
    ann_interest: float = 352.0
    ann_property: float = 13019.0
    property_sale_enabled: bool = False
    property_sale_date: str = "2031-11-05"
    property_sale_amount: float = 325000.0
    ann_pension_contribution: float = 2880.0
    ann_contribution_from_portfolio: bool = False
    ann_state_pension: float = 9494.0
    gordon_state_weekly: float = 241.30
    dividend_share_gordon: float | None = .5
    dividend_share_ann: float | None = .5

    def validate(self):
        if self.evelyn_scenario not in range(8):
            raise ValueError('Choose Custom or Evelyn scenario 1–7.')
        for name, value in asdict(self).items():
            if isinstance(value, (int, float)) and not math.isfinite(value):
                raise ValueError(f"{name} must be finite.")
        if not 1 <= self.years <= 60 or not (1 if self.non_stochastic else 100) <= self.simulations <= 2000:
            raise ValueError("Use 1–60 years and 100–2000 simulations.")
        if not -.5 < self.inflation <= .3 or self.std_y < 0:
            raise ValueError("Inflation must be between -50% and 30%; volatility cannot be negative.")
        if self.inflation+self.initial_y <= -1:
            raise ValueError("The initial total return must exceed -100%.")
        if not 0 <= self.crash_loss <= 1 or not 1 <= self.crash_window <= 20:
            raise ValueError("Crash loss must be 0–100%; its window must be 1–20 years.")
        if self.crash_enabled and not 1 <= self.deterministic_crash_year <= self.years:
            raise ValueError("The deterministic crash year must be within the projection.")
        for n in ["starting_balance", "income_yield", "withdrawal", "gift", "gift_years", "gordon_interest",
                  "gordon_citibank_pension", "ann_interest", "ann_property", "ann_pension_contribution",
                  "ann_state_pension", "property_sale_amount", "gordon_state_weekly", "seed"]:
            if getattr(self, n) < 0:
                raise ValueError(f"{n} cannot be negative.")
        for v in (self.dividend_share_gordon, self.dividend_share_ann):
            if v is not None and not 0 <= v <= 1:
                raise ValueError("Dividend shares must be between 0 and 1.")
        if self.gordon_citibank_growth is not None and self.gordon_citibank_growth <= -1:
            raise ValueError("Citibank pension growth must exceed -100%.")
        date.fromisoformat(self.start_date)
        if self.property_sale_enabled and date.fromisoformat(self.property_sale_date) < date.fromisoformat(self.start_date):
            raise ValueError("The rental-property sale date cannot precede the valuation date.")
        if self.ann_pension_contribution > 3600:
            raise ValueError("Without relevant earnings, this model supports at most £3,600 gross annual pension contributions.")


def anniversary(start, years):
    try:
        return start.replace(year=start.year+years)
    except ValueError:
        return date(start.year+years, 2, 28)


def threshold_scale(year, inflation):
    return (1+inflation)**(5*((year-1)//5))


def pension_during(start, end, eligibility, annual_2026, uprate):
    """Prorate State Pension around eligibility and each 6 April uprating."""
    boundaries = {start, end}
    if start < eligibility < end:
        boundaries.add(eligibility)
    for y in range(start.year, end.year+1):
        d = date(y, 4, 6)
        if start < d < end:
            boundaries.add(d)
    total = 0.0
    points = sorted(boundaries)
    for a, b in zip(points, points[1:]):
        if a >= eligibility:
            tax_year = a.year if a >= date(a.year, 4, 6) else a.year-1
            amount = annual_2026*(1+uprate)**(tax_year-2026)
            tax_start, tax_end = date(tax_year, 4, 6), date(tax_year+1, 4, 6)
            total += amount*(b-a).days/(tax_end-tax_start).days
    return total


def run_path(settings, ys, crash_year=0, account_balances=None, initial_gains=None):
    s = settings
    start = date.fromisoformat(s.start_date)
    sale_date = date.fromisoformat(s.property_sale_date) if s.property_sale_enabled else None
    balances = (REFERENCE_BALANCES/REFERENCE_BALANCES.sum()*s.starting_balance
                if account_balances is None else np.array(account_balances, dtype=float).copy())
    gains = REFERENCE_GAINS if initial_gains is None else initial_gains
    if np.any(balances < 0):
        raise ValueError("Account balances and GIA acquisition costs cannot be negative.")
    tax_ledger = NominalTaxLedger(balances, gains)
    rows = [{"year": 0, "date": start.isoformat(), "portfolio_nominal": float(balances.sum()),
             "portfolio_real": float(balances.sum()), "inflation_index": 1.0,
             **dict(zip(ACCOUNT_NAMES, balances))}]
    uprate = max(.025, s.inflation, s.earnings_growth)
    for year in range(1, s.years+1):
        tax_ledger.begin_year()
        a, b = anniversary(start, year-1), anniversary(start, year)
        opening = balances.copy()
        opening_price_index = (1+s.inflation)**(year-1)
        cpi_index = opening_price_index*(1+s.inflation)
        normal_return = s.inflation+ys[year-1]
        clipped = normal_return < -1.0
        normal_return = max(-1.0, normal_return)
        crash = year == crash_year
        total_return = (1+normal_return)*(1-s.crash_loss if crash else 1)-1
        real_factor = (1+total_return)/(1+s.inflation)
        real_return = real_factor-1
        sold_this_year = sale_date is not None and (a < sale_date <= b or (year == 1 and sale_date == a))
        sale_proceeds = s.property_sale_amount if sold_this_year else 0.0
        remaining_fraction = (b-sale_date).days/(b-a).days if sold_this_year else 0.0
        # The annual crash occurs at period end. A sale on that exact date is
        # deposited after the crash; earlier proceeds are exposed to it.
        sale_factor = ((1+normal_return)**remaining_fraction if remaining_fraction > 0 else 1.0)
        if crash and remaining_fraction > 0:
            sale_factor *= 1-s.crash_loss
        sale_investment_gain = sale_proceeds*(sale_factor-1)
        sale_price_index = opening_price_index*(1+s.inflation)**(1-remaining_fraction)
        sale_proceeds_real = sale_proceeds/sale_price_index
        sale_real_factor = sale_factor/(1+s.inflation)**remaining_fraction
        sale_end_value_real = sale_proceeds_real*sale_real_factor
        sale_gain_real = sale_end_value_real-sale_proceeds_real
        rent_fraction = (max(0.0, min(1.0, (sale_date-a).days/(b-a).days))
                         if sale_date is not None else 1.0)
        rental_profit = s.ann_property*rent_fraction
        # Yield is part of total_return, never an additional return. GIA
        # reinvestment adds acquisition cost so income is not also taxed as CGT.
        yields = opening[[0, 3]]*opening_price_index*s.income_yield
        yields[1] += sale_proceeds*s.income_yield*remaining_fraction
        balances *= real_factor
        balances[3] += sale_end_value_real
        tax_ledger.reinvest(yields, sale_proceeds)
        isa_transfers, isa_gains = tax_ledger.fund_isas(balances, cpi_index)
        scale = threshold_scale(year, s.inflation)
        state_g = pension_during(a, b, date(2028, 6, 27), s.gordon_state_weekly*52, uprate)
        state_a = pension_during(a, b, date(2023, 6, 26), s.ann_state_pension, uprate)
        citibank_growth = s.inflation if s.gordon_citibank_growth is None else s.gordon_citibank_growth
        citibank = s.gordon_citibank_pension*(1+citibank_growth)**(year-1)
        # Keep the established year-end timing: the first £150k nominal
        # receipt is paid after one year's inflation, so its constant real
        # value is £150k/(1+CPI). No first-year uplift is introduced here.
        regular_real = s.withdrawal/(1+s.inflation)
        regular = regular_real*cpi_index
        gift = s.gift if year <= s.gift_years and (not crash_year or year < crash_year) else 0.0
        contribution = s.ann_pension_contribution
        # Contributions occur at period end. Ann turns 75 on 26 June 2032.
        pension_relief = contribution if b < date(2032, 6, 26) else 0.0
        contribution_net = contribution-.2*pension_relief
        contribution_draw = contribution_net if s.ann_contribution_from_portfolio else 0.0
        plan = tax_ledger.allocate(balances, regular_real+(gift+contribution_draw)/cpi_index, cpi_index,
                                [state_g+citibank, state_a+rental_profit], [s.gordon_interest, s.ann_interest],
                                yields, scale,
                                (s.dividend_share_gordon, s.dividend_share_ann), (0.0, pension_relief), s.taxes_enabled)
        if s.ann_contribution_from_portfolio and plan.shortfall*cpi_index > .01:
            # No contribution or relief is assumed when the portfolio cannot
            # fund all requested obligations. Recalculate the tax without it.
            contribution = pension_relief = contribution_net = contribution_draw = 0.0
            plan = tax_ledger.allocate(balances, regular_real+gift/cpi_index, cpi_index,
                                    [state_g+citibank, state_a+rental_profit], [s.gordon_interest, s.ann_interest],
                                    yields, scale,
                                    (s.dividend_share_gordon, s.dividend_share_ann), taxes_enabled=s.taxes_enabled)
        realised = tax_ledger.realise(balances, plan.withdrawals, cpi_index, scale)
        balances = np.maximum(0.0, balances-plan.withdrawals)
        balances[5] += contribution/cpi_index
        tax = sum(t.total for t in plan.taxes)
        gross_real = float(plan.withdrawals.sum())
        gross = gross_real*cpi_index
        regular_paid = min(regular, gross)
        gift_paid = min(gift, max(0.0, gross-regular_paid-contribution_draw))
        # Gordon pays tax from his regular bank receipt; it is not another
        # portfolio withdrawal and must not reduce family gifts a second time.
        tax_paid = min(regular_paid, tax)
        spendable_after_tax = max(0.0, regular_paid-tax)
        row = {"year": year, "date": b.isoformat(), "period_start": a.isoformat(),
                     "opening_portfolio": float(opening.sum()*opening_price_index), "y": float(ys[year-1]),
                     "normal_nominal_return": normal_return, "total_return": total_return,
                     "real_return": real_return,
                     "return_clipped": clipped, "crash": crash,
                     "investment_gain": float(opening.sum()*opening_price_index*total_return+sale_investment_gain),
                     "opening_portfolio_real": float(opening.sum()),
                     "investment_gain_real": float(opening.sum()*real_return+sale_gain_real),
                     "property_sale_proceeds_real": sale_proceeds_real,
                     "property_sale_investment_gain_real": sale_gain_real,
                     "property_sale_proceeds": sale_proceeds,
                     "property_sale_investment_gain": sale_investment_gain,
                     "rental_profit_ann": rental_profit,
                     "portfolio_nominal": float(balances.sum()*cpi_index),
                     "portfolio_real": float(balances.sum()), "inflation_index": cpi_index,
                     "threshold_scale": scale, "regular_requested": regular, "regular_paid": regular_paid,
                     "gift_requested": gift, "gift_paid": gift_paid, "gross_withdrawal": gross,
                     "gia_to_isa_gordon": isa_transfers[0], "gia_to_isa_ann": isa_transfers[1],
                     "gia_to_isa_gain_gordon": isa_gains[0], "gia_to_isa_gain_ann": isa_gains[1],
                     "ann_pension_contribution_gross": contribution,
                     "ann_pension_contribution_net": contribution_net,
                     "ann_pension_relief_at_source": .2*pension_relief,
                     "ann_contribution_portfolio_draw": contribution_draw,
                     "ann_contribution_external_cash": contribution_net-contribution_draw,
                     "income_tax": sum(t.income_tax for t in plan.taxes),
                     "cgt": sum(t.capital_gains_tax for t in plan.taxes), "total_tax": tax,
                     "tax_paid": tax_paid, "unpaid_tax": max(0.0, tax-tax_paid),
                     "spendable_after_tax": spendable_after_tax,
                     "shortfall": plan.shortfall*cpi_index, "state_pension_gordon": state_g,
                     "state_pension_ann": state_a, "citibank_pension_gordon": citibank,
                     "external_interest_gordon": s.gordon_interest,
                     "external_interest_ann": s.ann_interest,
                     "external_income": state_g+state_a+citibank+rental_profit+s.gordon_interest+s.ann_interest,
                     "gia_yield_gordon": yields[0], "gia_yield_ann": yields[1],
                     "gordon_dividends": plan.taxes[0].dividends,
                     "ann_dividends": plan.taxes[1].dividends,
                     "realised_gain_gordon": realised[0], "realised_gain_ann": realised[1],
                     "loss_forward_gordon": tax_ledger.losses[0], "loss_forward_ann": tax_ledger.losses[1],
                     "solver_warning": plan.solver_fallback,
                     **dict(zip(ACCOUNT_NAMES, balances*cpi_index)),
                     **{f"withdrawal_{n}": v*cpi_index for n, v in zip(ACCOUNT_NAMES, plan.withdrawals)}}
        # Preserve nominal export columns and add explicit real reporting
        # counterparts. True real investment gains above exclude inflation;
        # nominal taxable gains below are only deflated for presentation.
        non_money = {'year', 'y', 'normal_nominal_return', 'total_return', 'real_return',
                     'inflation_index', 'threshold_scale', 'portfolio_nominal'}
        for name, value in list(row.items()):
            if name not in non_money and not name.endswith('_real') and isinstance(value, (int, float, np.number)) and not isinstance(value, (bool, np.bool_)):
                row.setdefault(name+'_real', value/cpi_index)
        row['gross_withdrawal_real'] = gross_real
        row['regular_requested_real'] = regular_real
        row['shortfall_real'] = plan.shortfall
        rows.append(row)
    for name in ACCOUNT_NAMES:
        rows[0][name+'_real'] = rows[0][name]
    return pd.DataFrame(rows)


def simulate(settings, account_balances=None, initial_gains=None, progress=None):
    if settings.non_stochastic:
        settings = replace(settings, std_y=0.0, simulations=1)
    settings.validate()
    if account_balances is not None:
        v = np.asarray(account_balances, dtype=float)
        if v.shape != (6,) or not np.all(np.isfinite(v)) or np.any(v < 0):
            raise ValueError("Supply six finite, nonnegative account balances.")
        if not np.isclose(v.sum(), settings.starting_balance, atol=.01, rtol=0):
            raise ValueError("The six account balances must sum to the starting portfolio.")
    if initial_gains is not None and (len(initial_gains) != 2 or not np.all(np.isfinite(initial_gains))):
        raise ValueError("Supply two finite GIA unrealised-gain figures.")
    returns_seed, crash_seed = np.random.SeedSequence(settings.seed).spawn(2)
    rng, crash_rng = np.random.default_rng(returns_seed), np.random.default_rng(crash_seed)
    ys = (np.full((1, settings.years), settings.initial_y) if settings.non_stochastic else
          rng.normal(settings.initial_y, settings.std_y, (settings.simulations, settings.years)))
    ys[:, 0] = settings.initial_y
    crash_years = (crash_rng.integers(1, min(settings.crash_window, settings.years)+1, settings.simulations)
                   if settings.crash_enabled else np.zeros(settings.simulations, dtype=int))
    if settings.non_stochastic and settings.crash_enabled:
        crash_years = np.array([settings.deterministic_crash_year])
    paths = []
    for k in range(settings.simulations):
        path = run_path(settings, ys[k], int(crash_years[k]), account_balances, initial_gains)
        path.insert(0, "simulation", k+1)
        paths.append(path)
        if progress:
            progress(.8*(k+1)/settings.simulations)
    base = run_path(settings, np.full(settings.years, settings.initial_y), 0, account_balances, initial_gains)
    stress = (run_path(settings, np.full(settings.years, settings.initial_y), settings.deterministic_crash_year,
                       account_balances, initial_gains) if settings.crash_enabled else None)
    details = pd.concat(paths, ignore_index=True)
    quantiles = []
    for value in ("portfolio_nominal", "portfolio_real"):
        q = details.groupby("year")[value].quantile(np.arange(.1, 1, .1)).unstack()
        q.columns = [f"p{int(round(c*100))}" for c in q.columns]
        q.insert(0, "value", value)
        quantiles.append(q.reset_index())
    reference = evelyn_reference(settings.evelyn_scenario, settings.years, settings.inflation)
    if progress:
        progress(1.0)
    return {"settings": asdict(settings), "details": details, "base": base, "stress": stress,
            "evelyn_reference": reference,
            "quantiles": pd.concat(quantiles, ignore_index=True), "crash_years": crash_years.tolist()}
