"""Real-pound portfolio simulation, with a separate nominal tax ledger."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date
from calendar import monthrange
from pathlib import Path
import math

import numpy as np
import pandas as pd

from tax_ledger import NominalTaxLedger
from tax import owner_tax
from tax_rules import period_tax_year, parameters_for_year
from strategies import select_strategy, assess_family_tax

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
                crash_enabled=False, property_sale_enabled=False)



def evelyn_mismatches(settings):
    """Compare against the documented preset and our agreed comparison baseline.

    Original charts have no underlying account/tax data. Do not invent adviser
    tax or allocation assumptions: these do not change gross portfolio flows.
    """
    if not settings.evelyn_scenario:
        return []
    expected=evelyn_preset(settings.evelyn_scenario)
    # Stochastic paths may be compared with the original deterministic
    # illustration when their central return and cash-flow assumptions match.
    expected.pop('non_stochastic')
    expected.pop('std_y')
    expected.update(inflation=.02,starting_balance=4335877.0,annual_fee=0.0,ann_pension_contribution=0.0)
    labels={'years':'projection length',
            'initial_y':'return above CPI',
            'gift':'annual gift','gift_years':'gift duration','withdrawal':'regular withdrawal',
            'ann_property':'rental profit','crash_enabled':'market crisis',
            'property_sale_enabled':'property sale','ann_pension_contribution':'pension contribution',
            'ann_contribution_from_portfolio':'contribution funding',
            'gordon_citibank_pension':'Citibank pension','gordon_interest':'Gordon bank interest',
            'ann_interest':'Ann bank interest','inflation':'CPI inflation',
            'starting_balance':'starting portfolio','annual_fee':'additional investment fee'}
    differences=[]
    for key,value in expected.items():
        actual=getattr(settings,key)
        same=(math.isclose(actual,value,rel_tol=1e-10,abs_tol=1e-8)
              if isinstance(value,(float,int)) and not isinstance(value,bool) else actual == value)
        if not same: differences.append(labels[key])
    return differences

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
    initial_y: float = -.006227264187740222
    std_y: float = .13304562358622968
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
    property_sale_mode: str = "date"
    property_sale_threshold: float = 1000000.0
    ann_pension_contribution: float = 2880.0
    ann_contribution_is_net: bool = True
    ann_contribution_from_portfolio: bool = False
    ann_state_pension: float = 9494.0
    gordon_state_weekly: float = 241.30
    dividend_share_gordon: float | None = .5
    dividend_share_ann: float | None = .5

    gordon_tax_free_share: float = 0.0
    ann_tax_free_share: float = 0.25
    ann_lsa_remaining: float = 268275.0
    gordon_lsa_remaining: float = 0.0
    withdrawal_strategy: str = "estate"
    sipp_income_target: float | None = None
    iht_rate: float = .40
    beneficiary_income_tax_rate: float = .40
    estate_assessment_year: int | None = None
    tax_rules: str = "current_law"
    annual_fee: float = 0.0

    def validate(self):
        if self.property_sale_mode not in {'date','threshold'}:
            raise ValueError('Choose date or threshold for the property sale trigger.')
        if self.withdrawal_strategy not in {'estate','annual_tax'}:
            raise ValueError('Choose estate or annual_tax withdrawal strategy.')
        if self.tax_rules not in {'current_law','legacy_2026_27'}:
            raise ValueError('Choose current_law or legacy_2026_27 tax rules.')
        for value in (self.gordon_tax_free_share,self.ann_tax_free_share):
            if not 0 <= value <= .25: raise ValueError('Tax-free shares must be 0–25%.')
        for value in (self.gordon_lsa_remaining,self.ann_lsa_remaining):
            if value < 0: raise ValueError('Remaining lump sum allowances cannot be negative.')
        if self.sipp_income_target is not None and self.sipp_income_target < 0:
            raise ValueError('The SIPP taxable-income target cannot be negative.')
        if self.estate_assessment_year is not None and not 1 <= self.estate_assessment_year <= self.years:
            raise ValueError('Estate assessment year must be within the projection.')
        if not 0 <= self.iht_rate <= 1 or not 0 <= self.beneficiary_income_tax_rate <= 1:
            raise ValueError('Estate tax rates must be 0–100%.')
        if not 0 <= self.annual_fee < 1: raise ValueError('Annual fee must be 0–100%, excluding 100%.')
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
                  "ann_state_pension", "property_sale_amount", "property_sale_threshold", "gordon_state_weekly", "seed"]:
            if getattr(self, n) < 0:
                raise ValueError(f"{n} cannot be negative.")
        for v in (self.dividend_share_gordon, self.dividend_share_ann):
            if v is not None and not 0 <= v <= 1:
                raise ValueError("Dividend shares must be between 0 and 1.")
        if self.gordon_citibank_growth is not None and self.gordon_citibank_growth <= -1:
            raise ValueError("Citibank pension growth must exceed -100%.")
        date.fromisoformat(self.start_date)
        if self.property_sale_enabled and self.property_sale_mode == "date" and date.fromisoformat(self.property_sale_date) < date.fromisoformat(self.start_date):
            raise ValueError("The rental-property sale date cannot precede the valuation date.")
        first_end=anniversary(date.fromisoformat(self.start_date),1)
        gross,_,_=pension_contribution(self,first_end)
        if gross > 3600+1e-8:
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




def pension_contribution(settings,when):
    """Gross credit, bank cash and gross relief-eligible contribution at year end."""
    eligible=when < date(2032,6,26)
    amount=settings.ann_pension_contribution
    if settings.ann_contribution_is_net:
        gross=amount/.8 if eligible else amount
        return gross,amount,gross if eligible else 0.0
    return amount,amount*(.8 if eligible else 1),amount if eligible else 0.0

def threshold_property_sale(settings,ys,crash_year,opening_balance):
    """First monthly crossing of the real total portfolio before sale proceeds.

    Gross portfolio flows and common returns/fees are independent of account
    selection and bank-paid tax. This cheap prepass therefore determines the
    event separately for each return/crash path without borrowing future sale
    proceeds. It checks opening value, monthly market/fee changes, then the
    value after the planned monthly cash outflow. An immediate sale can fund
    that same payment if the portfolio would otherwise be exhausted.
    """
    s=settings; start=date.fromisoformat(s.start_date); value=float(opening_balance)
    threshold=s.property_sale_threshold
    crossed=lambda v: v <= threshold+1e-7
    if crossed(value): return start,1,0,value
    for year in range(1,s.years+1):
        a,b=anniversary(start,year-1),anniversary(start,year)
        factor=((1+max(-1.0,s.inflation+ys[year-1]))/(1+s.inflation))**(1/12)
        factor*=(1-s.annual_fee)**(1/12)
        gift=s.gift if year <= s.gift_years and (not crash_year or year < crash_year) else 0.0
        contribution,net_contribution,relief=pension_contribution(s,b)
        for month in range(1,13):
            value*=factor
            if year == crash_year and month == 12: value*=1-s.crash_loss
            month_index=a.year*12+a.month-1+month
            my,mm=divmod(month_index,12); mm+=1
            when=date(my,mm,min(a.day,monthrange(my,mm)[1]))
            if crossed(value): return when,year,month,max(0.0,value)
            prices=(1+s.inflation)**(year-1+month/12)
            outflow=s.withdrawal*(4 if month == 12 else 1)/15
            if month == 12:
                outflow+=gift/prices
                if s.ann_contribution_from_portfolio: outflow+=net_contribution/prices
            after=max(0.0,value-outflow)
            if crossed(after): return when,year,month,after
            value=after
            if month == 12: value+=contribution/prices
    return None,None,None,None

def run_path(settings, ys, crash_year=0, account_balances=None, initial_gains=None):
    s = settings
    start = date.fromisoformat(s.start_date)
    sale_date = (date.fromisoformat(s.property_sale_date)
                 if s.property_sale_enabled and s.property_sale_mode == 'date' else None)
    trigger_year=trigger_month=trigger_value=None
    if s.property_sale_enabled and s.property_sale_mode == 'threshold':
        total=s.starting_balance if account_balances is None else float(np.sum(account_balances))
        sale_date,trigger_year,trigger_month,trigger_value=threshold_property_sale(s,ys,crash_year,total)
    balances = (REFERENCE_BALANCES/REFERENCE_BALANCES.sum()*s.starting_balance
                if account_balances is None else np.array(account_balances, dtype=float).copy())
    gains = REFERENCE_GAINS if initial_gains is None else initial_gains
    if np.any(balances < 0):
        raise ValueError("Account balances and GIA acquisition costs cannot be negative.")
    tax_ledger = NominalTaxLedger(balances,gains,
        (s.gordon_lsa_remaining,s.ann_lsa_remaining),(s.gordon_tax_free_share,s.ann_tax_free_share))
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
        real_return = (1+total_return)/(1+s.inflation)-1
        sold_this_year = sale_date is not None and (a < sale_date <= b or (year == 1 and sale_date == a))
        sale_proceeds = s.property_sale_amount if sold_this_year else 0.0
        remaining_fraction = (b-sale_date).days/(b-a).days if sold_this_year else 0.0
        if sold_this_year and s.property_sale_mode == 'threshold':
            # Align triggered deposits to the engine's equal monthly periods;
            # report dates retain calendar month anniversaries for readability.
            remaining_fraction=1-trigger_month/12
        # The annual crash occurs at period end. A sale on that exact date is
        # deposited after the crash; earlier proceeds are exposed to it.
        sale_factor = ((1+normal_return)**remaining_fraction if remaining_fraction > 0 else 1.0)
        if crash and remaining_fraction > 0:
            sale_factor *= 1-s.crash_loss
        sale_investment_gain = sale_proceeds*(sale_factor-1)
        sale_price_index = opening_price_index*(1+s.inflation)**(1-remaining_fraction)
        sale_proceeds_real = sale_proceeds/sale_price_index
        sale_gain_real = sale_proceeds*(sale_factor/cpi_index-1/sale_price_index)
        rent_fraction = (max(0.0, min(1.0, (sale_date-a).days/(b-a).days))
                         if sale_date is not None else 1.0)
        rental_profit = s.ann_property*rent_fraction
        tax_year = period_tax_year(a,b)
        params = parameters_for_year(tax_year,s.inflation) if s.tax_rules == 'current_law' else None
        scale = params.allowance/12570 if params is not None else threshold_scale(year,s.inflation)
        target_scale = scale
        state_g = pension_during(a, b, date(2028, 6, 27), s.gordon_state_weekly*52, uprate)
        state_a = pension_during(a, b, date(2023, 6, 26), s.ann_state_pension, uprate)
        citibank_growth = s.inflation if s.gordon_citibank_growth is None else s.gordon_citibank_growth
        citibank = s.gordon_citibank_pension*(1+citibank_growth)**(year-1)
        gift = s.gift if year <= s.gift_years and (not crash_year or year < crash_year) else 0.0
        contribution,contribution_net,pension_relief=pension_contribution(s,b)
        contribution_draw = contribution_net if s.ann_contribution_from_portfolio else 0.0
        other_income = np.array([state_g+citibank,state_a])
        property_income = [0.0,rental_profit]
        target = s.sipp_income_target if s.sipp_income_target is not None else 50270.0
        estate_mode = s.withdrawal_strategy == 'estate' and target > 0
        rooms = np.maximum(0.0,target*target_scale-other_income-property_income)
        shares = np.array(tax_ledger.tax_free_shares)
        # Gross-up is capped at remaining nominal LSA, including partial exhaustion.
        goals = rooms+np.minimum(rooms*shares/(1-shares),tax_ledger.tfc_remaining)
        tfc_taken = np.zeros(2)
        fees = fees_real = 0.0
        yields, withdrawals = np.zeros(2), np.zeros(6)
        regular_paid_real = 0.0
        withdrawals_real = np.zeros(6)
        regular = regular_paid = gift_paid = gross = gross_real = shortfall = shortfall_real = 0.0
        investment_gain = investment_gain_real = 0.0
        isa_transfers, isa_gains = np.zeros(2), np.zeros(2)
        solver_warning = False
        # Monthly receipts are £10k for months 1–11 and £40k in month 12
        # at the default £150k annual Day-0 spending level. Each payment is
        # inflated from Day 0; growth is compounded evenly between months.
        sale_t = 1-remaining_fraction if sold_this_year else None
        monthly_nominal_factor = (1+normal_return)**(1/12)
        monthly_real_factor = monthly_nominal_factor/(1+s.inflation)**(1/12)
        for month in range(1, 13):
            t0, t1 = (month-1)/12, month/12
            prices = opening_price_index*(1+s.inflation)**t1
            old_prices = opening_price_index*(1+s.inflation)**t0
            before = balances.copy()
            month_yield = before[[0, 3]]*old_prices*s.income_yield/12
            balances *= monthly_real_factor
            month_nominal_gain = before.sum()*old_prices*(monthly_nominal_factor-1)
            deposit_real = 0.0
            deposit_now = sold_this_year and (t0 < sale_t <= t1 or (month == 1 and sale_t == 0))
            if deposit_now:
                deposit_real = sale_proceeds_real
                part = t1-sale_t
                deposit_end = sale_proceeds*(1+normal_return)**part
                balances[3] += deposit_end/prices
                month_nominal_gain += deposit_end-sale_proceeds
                month_yield[1] += sale_proceeds*s.income_yield*part
            if crash and month == 12:
                # A sale exactly at the period end is deposited after the crash.
                exempt = sale_proceeds/prices if deposit_now and sale_t == 1 else 0.0
                exposed = balances.copy(); exposed[3] -= exempt
                month_nominal_gain -= exposed.sum()*prices*s.crash_loss
                balances -= exposed*s.crash_loss
            market_after = balances.sum()
            balances *= (1-s.annual_fee)**(1/12)
            month_fee_real = market_after-balances.sum()
            fees_real += month_fee_real
            fees += month_fee_real*prices
            investment_gain += month_nominal_gain
            investment_gain_real += balances.sum()-before.sum()-deposit_real+month_fee_real
            yields += month_yield
            tax_ledger.reinvest(month_yield, sale_proceeds if deposit_now else 0.0)
            # Retain the annual ISA subscription at the period end, before
            # the final month's scheduled receipt and any gift.
            if month == 12:
                isa_transfers, isa_gains = tax_ledger.fund_isas(balances, prices)
            regular_month_real = s.withdrawal*(4 if month == 12 else 1)/15
            regular_month = regular_month_real*prices
            regular += regular_month
            gift_month = gift if month == 12 else 0.0
            contribution_month = contribution_draw if month == 12 else 0.0
            target_real = regular_month_real+(gift_month+contribution_month)/prices
            non_savings = other_income+withdrawals[[2,5]]-tfc_taken
            monthly_goals = goals*(4 if month == 12 else 1)/15 if estate_mode else None
            plan = tax_ledger.allocate(balances, target_real, prices, non_savings,
                                      [s.gordon_interest, s.ann_interest], yields, scale,
                                      (s.dividend_share_gordon, s.dividend_share_ann),
                                      (0.0,pension_relief),s.taxes_enabled,property_income=property_income,params=params,
                                      estate_goals=monthly_goals)
            if month == 12 and s.ann_contribution_from_portfolio and (shortfall > .01 or plan.shortfall*prices > .01):
                contribution = pension_relief = contribution_net = contribution_draw = contribution_month = 0.0
                target_real = regular_month_real+gift_month/prices
                plan = tax_ledger.allocate(balances, target_real, prices, non_savings,
                                          [s.gordon_interest, s.ann_interest], yields, scale,
                                          (s.dividend_share_gordon, s.dividend_share_ann),
                                          taxes_enabled=s.taxes_enabled,property_income=property_income,params=params,
                                          estate_goals=monthly_goals)
            tax_ledger.record_disposals(balances, plan.withdrawals, prices)
            tfc_taken += tax_ledger.record_pension_withdrawals(plan.withdrawals*prices)
            balances = np.maximum(0.0, balances-plan.withdrawals)
            month_gross_real = float(plan.withdrawals.sum())
            month_gross = month_gross_real*prices
            withdrawals += plan.withdrawals*prices
            withdrawals_real += plan.withdrawals
            regular_paid += min(regular_month, month_gross)
            regular_paid_real += min(regular_month_real, month_gross_real)
            gift_paid += min(gift_month, max(0.0, month_gross-regular_month-contribution_month))
            gross_real += month_gross_real
            gross += month_gross
            shortfall += plan.shortfall*prices
            shortfall_real += plan.shortfall
            solver_warning |= plan.solver_fallback
        balances[5] += contribution/cpi_index
        regular_real = s.withdrawal
        # Aggregate the actual twelve receipts, reinvested income and disposals.
        # Tax allowances and carried-forward losses are applied once per year.
        realised = tax_ledger.year_gains.copy()
        taxes = [owner_tax(n+withdrawals[j*3+2]-tfc_taken[j], interest, yields[j], realised[j],
                           tax_ledger.losses[j],scale,share,relief,property_income=property_income[j],params=params)
                 for j, (n, interest, share, relief) in enumerate(zip(
                     other_income, [s.gordon_interest, s.ann_interest],
                     [s.dividend_share_gordon, s.dividend_share_ann], [0.0, pension_relief]))]
        if not s.taxes_enabled:
            taxes = [replace(t, income_tax=0.0, capital_gains_tax=0.0) for t in taxes]
        tax_ledger.finish_year(scale,params)
        tax = sum(t.total for t in taxes)
        tax_paid = min(regular_paid, tax)
        spendable_after_tax = max(0.0, regular_paid-tax)
        row = {"year": year, "date": b.isoformat(), "period_start": a.isoformat(),
                     "tax_year": f"{tax_year}/{str(tax_year+1)[-2:]}",
                     "withdrawal_strategy": s.withdrawal_strategy,"tax_rules":s.tax_rules,
                     "sipp_income_target": target*target_scale if estate_mode else 0.0,
                     "personal_allowance": params.allowance if params else 12570*scale,
                     "basic_band": params.basic_band if params else 37700*scale,
                     "tax_free_cash_gordon": tfc_taken[0], "tax_free_cash_ann": tfc_taken[1],
                     "lsa_remaining_gordon": tax_ledger.tfc_remaining[0],
                     "lsa_remaining_ann": tax_ledger.tfc_remaining[1],
                     "sipp_taxable_gordon": withdrawals[2]-tfc_taken[0],
                     "sipp_taxable_ann": withdrawals[5]-tfc_taken[1],
                     "non_savings_gordon": other_income[0]+withdrawals[2]-tfc_taken[0],
                     "non_savings_ann": other_income[1]+withdrawals[5]-tfc_taken[1]+rental_profit,
                     "annual_fees": fees,"annual_fees_real":fees_real,
                     "opening_portfolio": float(opening.sum()*opening_price_index), "y": float(ys[year-1]),
                     "normal_nominal_return": normal_return, "total_return": total_return,
                     "real_return": real_return,
                     "return_clipped": clipped, "crash": crash,
                     "investment_gain": float(investment_gain),
                     "opening_portfolio_real": float(opening.sum()),
                     "investment_gain_real": float(investment_gain_real),
                     "property_sale_proceeds_real": sale_proceeds_real,
                     "property_sale_investment_gain_real": sale_gain_real,
                     "property_sale_proceeds": sale_proceeds,
                     "property_sale_actual_date": sale_date.isoformat() if sold_this_year else None,
                     "property_sale_triggered": bool(sold_this_year and s.property_sale_mode == 'threshold'),
                     "property_sale_trigger_value_real": trigger_value if sold_this_year and trigger_year else None,
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
                     "income_tax": sum(t.income_tax for t in taxes),
                     "cgt": sum(t.capital_gains_tax for t in taxes), "total_tax": tax,
                     "tax_paid": tax_paid, "unpaid_tax": max(0.0, tax-tax_paid),
                     "spendable_after_tax": spendable_after_tax,
                     "shortfall": shortfall, "state_pension_gordon": state_g,
                     "state_pension_ann": state_a, "citibank_pension_gordon": citibank,
                     "external_interest_gordon": s.gordon_interest,
                     "external_interest_ann": s.ann_interest,
                     "external_income": state_g+state_a+citibank+rental_profit+s.gordon_interest+s.ann_interest,
                     "gia_yield_gordon": yields[0], "gia_yield_ann": yields[1],
                     "gordon_dividends": taxes[0].dividends,
                     "ann_dividends": taxes[1].dividends,
                     "realised_gain_gordon": realised[0], "realised_gain_ann": realised[1],
                     "loss_forward_gordon": tax_ledger.losses[0], "loss_forward_ann": tax_ledger.losses[1],
                     "solver_warning": solver_warning,
                     **dict(zip(ACCOUNT_NAMES, balances*cpi_index)),
                     **{f"withdrawal_{n}": v for n, v in zip(ACCOUNT_NAMES, withdrawals)}}
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
        row['regular_paid_real'] = regular_paid_real
        row['spendable_after_tax_real'] = max(0.0,regular_paid_real-tax_paid/cpi_index)
        for name, value in zip(ACCOUNT_NAMES, withdrawals_real):
            row['withdrawal_'+name+'_real'] = value
        row['shortfall_real'] = shortfall_real
        rows.append(row)
    for name in ACCOUNT_NAMES:
        rows[0][name+'_real'] = rows[0][name]
    table=pd.DataFrame(rows)
    table['net_annual_income']=household_net_income(table,real=False)
    table['net_annual_income_real']=household_net_income(table,real=True)
    return table


def household_net_income(table,real=True):
    """Actual regular receipts plus external cash income less full tax liability.

    Gifts, property-sale principal and reinvested GIA yield are not household
    income. Keep deficits negative instead of masking tax shortfalls at zero.
    Regular real receipts already reflect their individual monthly dates;
    external annual income and tax use the existing period-end deflation.
    """
    suffix='_real' if real else ''
    return table['regular_paid'+suffix]+table['external_income'+suffix]-table['total_tax'+suffix]


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
    runner = lambda policy: run_path(policy,np.full(policy.years,policy.initial_y),0,account_balances,initial_gains)
    settings,comparison,sensitivity,base = select_strategy(settings,runner)
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
    stress = (run_path(settings, np.full(settings.years, settings.initial_y), settings.deterministic_crash_year,
                       account_balances, initial_gains) if settings.crash_enabled else None)
    details = pd.concat(paths, ignore_index=True)
    quantiles = []
    for value in ("portfolio_nominal", "portfolio_real", "net_annual_income_real"):
        data=details.query("year > 0") if value == "net_annual_income_real" else details
        q = data.groupby("year")[value].quantile(np.arange(.1, 1, .1)).unstack()
        q.columns = [f"p{int(round(c*100))}" for c in q.columns]
        q.insert(0, "value", value)
        quantiles.append(q.reset_index())
    reference_mismatches=evelyn_mismatches(settings)
    reference=(None if reference_mismatches else
               evelyn_reference(settings.evelyn_scenario,settings.years,settings.inflation))
    if progress:
        progress(1.0)
    return {"settings": asdict(settings), "details": details, "base": base, "stress": stress,
            "evelyn_reference": reference,"evelyn_reference_mismatches":reference_mismatches,
            "strategy_comparison": comparison,"strategy_sensitivity":sensitivity,
            "family_tax_summary":assess_family_tax(base,settings),
            "spending_summary":spending_summary(base),
            "quantiles": pd.concat(quantiles, ignore_index=True), "crash_years": crash_years.tolist()}


def spending_summary(base):
    years=base[base.year > 0]
    lowest=years.loc[years.spendable_after_tax_real.idxmin()]
    return dict(average_household_real=float(household_net_income(years).mean()),minimum_real=float(years.spendable_after_tax_real.min()),
                average_real=float(years.spendable_after_tax_real.mean()),
                lowest_year=int(lowest.year),lifetime_tax_real=float(years.total_tax_real.sum()))
