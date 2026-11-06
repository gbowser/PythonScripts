from dataclasses import replace
from pathlib import Path
import json

import numpy as np
import pytest

from simulation import Settings,run_path,simulate,evelyn_preset
from tax import income_tax,owner_tax
from tax_rules import parameters_for_year,period_tax_year,TaxParameters
from tax_ledger import NominalTaxLedger
from withdrawals import plan_withdrawals
from strategies import assess_family_tax
from datetime import date


def quiet(**changes):
    options=dict(years=1,starting_balance=100000,inflation=0,initial_y=0,withdrawal=40000,
                 gift=0,income_yield=0,gordon_citibank_pension=0,gordon_interest=0,
                 ann_interest=0,ann_property=0,ann_state_pension=0,ann_pension_contribution=0,
                 withdrawal_strategy='annual_tax')
    options.update(changes)
    return Settings(**options)


def test_ann_25_percent_tax_free_cash_and_actual_lsa_consumption():
    s=quiet()
    p=run_path(s,[0],account_balances=[0,0,0,0,0,100000],initial_gains=[0,0])
    r=p.iloc[1]
    assert r.tax_free_cash_ann == pytest.approx(10000)
    assert r.sipp_taxable_ann == pytest.approx(30000)
    assert r.income_tax == pytest.approx((30000-12570)*.2)
    assert r.lsa_remaining_ann == pytest.approx(258275)
    ledger=NominalTaxLedger(np.array([0,0,0,0,0,100000.]),[0,0],[0,1000],[0,.25])
    before=ledger.tfc_remaining.copy()
    ledger.allocate(np.array([0,0,0,0,0,100000.]),40000,1,[0,0],[0,0],[0,0],1,[.5,.5])
    assert ledger.tfc_remaining == pytest.approx(before)


def test_lsa_is_nominal_capped_across_years():
    s=quiet(years=2,ann_lsa_remaining=11000)
    p=run_path(s,[0,0],account_balances=[0,0,0,0,0,100000],initial_gains=[0,0])
    assert p.tax_free_cash_ann.iloc[1:].tolist() == pytest.approx([10000,1000])
    assert p.lsa_remaining_ann.iloc[2] == 0
    assert p.sipp_taxable_ann.iloc[2] == pytest.approx(39000)


def test_legacy_s1_reproduces_saved_monthly_baseline():
    fixture=json.loads((Path(__file__).parent/'fixtures/monthly_legacy_s1.json').read_text())
    s=Settings(**fixture['settings'],withdrawal_strategy='annual_tax',tax_rules='legacy_2026_27',ann_tax_free_share=0)
    p=run_path(s,[s.initial_y]*s.years)
    for i,row in enumerate(fixture['rows'][1:],1):
        for field in ['portfolio_real','portfolio_nominal','total_tax','Gordon SIPP','Ann SIPP']:
            assert p.iloc[i][field] == pytest.approx(row[field],abs=.02,rel=0)


def test_estate_policy_uses_both_targets_and_preserves_cash_path():
    s=Settings(**evelyn_preset(1),sipp_income_target=50270)
    p=run_path(s,[.025]*34)
    legacy=run_path(replace(s,withdrawal_strategy='annual_tax'),[.025]*34)
    assert p.portfolio_real.to_numpy() == pytest.approx(legacy.portfolio_real.to_numpy(),abs=.01)
    assert p.non_savings_gordon.iloc[1:6].tolist() == pytest.approx(p.personal_allowance.iloc[1:6]/12570*50270)
    assert p.non_savings_ann.iloc[1:6].tolist() == pytest.approx(p.personal_allowance.iloc[1:6]/12570*50270)
    assert (p[['Gordon SIPP','Ann SIPP']].values >= 0).all()
    assert p.regular_paid_real.iloc[1:].tolist() == pytest.approx([150000]*34,abs=.01)


def test_auto_target_improves_objective_and_exports_earlier_death_sensitivities():
    s=Settings(**evelyn_preset(1))
    r=simulate(s)
    c=r['strategy_comparison']
    chosen=c[c.selected].iloc[0]
    assert chosen.family_tax <= c.loc[c['T']==0,'family_tax'].iloc[0]+.01
    assert set(r['strategy_sensitivity'].assessment_year) == {15,20,25,30}
    assert r['settings']['sipp_income_target'] == chosen['T']
    assert r['spending_summary']['lifetime_tax_real'] == pytest.approx(r['base'].total_tax_real.sum())
    # Earlier-death objective includes only taxes paid through that assessment.
    f=assess_family_tax(r['base'],s,15)
    assert f['lifetime_tax_real'] == pytest.approx(r['base'].query('year <= 15').total_tax_real.sum())


def test_estate_gia_first_tie_break_and_exhaustion():
    plan=plan_withdrawals(np.array([50000.,50000,0,0,0,0]),[50000,0],[0,0],[0,0],[0,0],[0,0],10000,1,[.5,.5],gia_first=True)
    assert plan.withdrawals[0] == pytest.approx(10000,abs=.01)
    s=quiet(starting_balance=1000,withdrawal=150000,withdrawal_strategy='estate',sipp_income_target=50270)
    a=run_path(s,[0],account_balances=[0,0,1000,0,0,0],initial_gains=[0,0])
    b=run_path(replace(s,withdrawal_strategy='annual_tax'),[0],account_balances=[0,0,1000,0,0,0],initial_gains=[0,0])
    assert a.shortfall.iloc[1] == pytest.approx(b.shortfall.iloc[1])
    assert a.portfolio_real.iloc[-1] == 0


def test_current_law_rates_allowance_freeze_and_additional_band():
    p=parameters_for_year(2027,.02)
    assert income_tax(20000,11000,0,params=p)[0]-(20000-12570)*.2 == pytest.approx(10000*.22)
    assert income_tax(30000,400,200,property_income=3000,params=p)[0] == pytest.approx(4146)
    for y in range(2026,2031): assert parameters_for_year(y,.02).allowance == 12570
    q=parameters_for_year(2031,.02)
    assert q.allowance == pytest.approx(12570*1.02)
    assert q.basic_band == pytest.approx(37700*1.02)
    assert q.taper_start == 100000 and q.cgt_exemption == 3000 and q.dividend_allowance == 500
    assert q.additional_threshold == 125140
    # An indexed PA can remain at the frozen additional taxable-income limit.
    huge=replace(p,allowance=30000)
    tax,pa,taxable=income_tax(130000,0,0,params=huge)
    assert pa == 15000 and taxable == 115000
    assert tax == pytest.approx(37700*.2+(115000-37700)*.4)
    assert period_tax_year(date(2026,11,5),date(2027,11,5)) == 2027


def test_fees_are_monthly_and_separate_from_return():
    s=quiet(withdrawal=0,annual_fee=.012,taxes_enabled=False)
    p=run_path(s,[.05],account_balances=[0,100000,0,0,0,0],initial_gains=[0,0])
    assert p.portfolio_nominal.iloc[1] == pytest.approx(100000*1.05*.988)
    row=p.iloc[1]
    assert row.portfolio_real == pytest.approx(row.opening_portfolio_real+row.investment_gain_real-row.annual_fees_real)


@pytest.mark.parametrize('field,value',[('ann_tax_free_share',.26),('ann_lsa_remaining',-1),('annual_fee',1),('iht_rate',1.1),('estate_assessment_year',2)])
def test_new_setting_validation(field,value):
    with pytest.raises(ValueError): replace(quiet(),**{field:value}).validate()


def test_three_way_allowance_allocation_beats_independent_coarse_grid():
    from tax import band_tax
    p=parameters_for_year(2027,.02)
    for n,prop,sav,div in [(0,9000,12000,5000),(3000,18000,3000,11000),(10000,2000,8000,8000)]:
        actual,pa,taxable=income_tax(n,sav,div,property_income=prop,params=p)
        rem=max(0,pa-n); nt=max(0,n-pa)
        best=float('inf')
        for ap in np.linspace(max(0,rem-sav-div),min(prop,rem),31):
            for ass in np.linspace(max(0,rem-ap-div),min(sav,rem-ap),31):
                pt=prop-ap; st=sav-ass; dt=div-(rem-ap-ass)
                sn=min(st,max(0,5000-nt-pt)+1000)
                dn=min(dt,500)
                cost=(band_tax(0,nt,37700,125140,(.2,.4,.45))+
                      band_tax(nt,pt,37700,125140,(.22,.42,.47))+
                      band_tax(nt+pt+sn,st-sn,37700,125140,(.22,.42,.47))+
                      band_tax(nt+pt+st+dn,dt-dn,37700,125140,(.1075,.3575,.3935)))
                best=min(best,cost)
        assert actual <= best+.00001


def test_chosen_target_is_reused_for_stochastic_and_stress_paths():
    s=quiet(years=2,simulations=100,withdrawal_strategy='estate',std_y=.02,
            crash_enabled=True,deterministic_crash_year=2)
    r=simulate(s,initial_gains=[0,0])
    chosen=r['settings']['sipp_income_target']
    assert r['details'].query('year > 0').sipp_income_target.unique().tolist() == [chosen]
    assert r['stress'].sipp_income_target.iloc[1:].tolist() == [chosen,chosen]
    assert r['details'].simulation.nunique() == 100
