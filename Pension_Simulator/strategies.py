"""Deterministic policy selection; this is a marginal estate-tax scenario model."""
from dataclasses import replace
import pandas as pd

UNLIMITED_TARGET = 1e12


def assess_family_tax(path, settings, year=None):
    year = year or settings.estate_assessment_year or settings.years
    through = path[(path.year > 0) & (path.year <= year)]
    row = path.loc[path.year == year].iloc[0]
    pension = row['Gordon SIPP_real']+row['Ann SIPP_real']
    lifetime = float(through.total_tax_real.sum())
    iht = settings.iht_rate*row.portfolio_real
    beneficiary = settings.beneficiary_income_tax_rate*(1-settings.iht_rate)*pension
    minimum = float(through.spendable_after_tax_real.min())
    return dict(assessment_year=year,lifetime_tax_real=lifetime,
                iht_real=iht,beneficiary_tax_real=beneficiary,
                death_taxes_real=iht+beneficiary,family_tax=lifetime+iht+beneficiary,
                sipp_left_real=pension,minimum_spendable_real=minimum)


def select_strategy(settings, runner):
    """Evaluate a coarse policy grid then five refinements around its best point.

    T=0 is the legacy annual-tax policy, so it is always a feasible comparator.
    No surplus pension drawdowns or first-death transitions are assumed.
    """
    cache={}
    def evaluate(target):
        target=float(target)
        if target not in cache:
            policy=replace(settings,sipp_income_target=target)
            path=runner(policy)
            row=assess_family_tax(path,policy)
            row.update(T=target,target_label='SIPP first' if target == UNLIMITED_TARGET else f'£{target:,.0f}')
            cache[target]=(row,path)
        return cache[target][0]['family_tax']
    grid=[0,12570,50270,75000,100000,125140,UNLIMITED_TARGET]
    if settings.withdrawal_strategy == 'estate' and settings.sipp_income_target is None:
        for t in grid: evaluate(t)
        best=min(grid,key=evaluate); k=grid.index(best)
        lo=grid[max(0,k-1)]
        hi=grid[min(len(grid)-1,k+1)]
        if hi == UNLIMITED_TARGET:
            hi=max(250000,settings.withdrawal*2,lo*2)
        for j in range(1,6): evaluate(lo+(hi-lo)*j/6)
        chosen=min(cache,key=lambda t:(evaluate(t),t))
    else:
        chosen=settings.sipp_income_target or 0.0
        evaluate(chosen)
    effective=replace(settings,sipp_income_target=chosen)
    rows=[item[0] for _,item in sorted(cache.items())]
    comparison=pd.DataFrame(rows)
    comparison['selected']=comparison['T'].eq(chosen)
    sensitivity=[]
    for t,(row,path) in sorted(cache.items()):
        for year in (15,20,25,30):
            if year <= settings.years:
                item=assess_family_tax(path,settings,year)
                item.update(T=t,target_label=row['target_label'],selected=t==chosen)
                sensitivity.append(item)
    return effective,comparison,pd.DataFrame(sensitivity),cache[chosen][1]
