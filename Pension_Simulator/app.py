"""Run with: python -m streamlit run app.py"""
from dataclasses import asdict
from datetime import date, datetime
from zoneinfo import ZoneInfo
import io
from html import escape
import json
import math
import importlib
import hashlib
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import t as student_t
import streamlit as st

# Refresh local model definitions on every Streamlit rerun. A long-running
# Windows server can otherwise retain an older Settings class after edits.
import tax_rules as tax_rules_model
import strategies as strategy_model
import tax as tax_model
import withdrawals as withdrawal_model
import tax_ledger as tax_ledger_model
import simulation as simulation_model
import sources as source_model
import pdf_report as pdf_report_model
import charts as charts_model
for model in (tax_rules_model,tax_model,withdrawal_model,tax_ledger_model,strategy_model,simulation_model,source_model,pdf_report_model,charts_model):
    importlib.reload(model)

from simulation import (ACCOUNT_NAMES, REFERENCE_BALANCES, REFERENCE_GAINS, EVELYN_SCENARIOS,
                        Settings, anniversary, simulate, evelyn_label, evelyn_preset, evelyn_mismatches, household_net_income)
from sources import DEFAULT_WORKBOOK, load_snapshot, read_workbook, save_snapshot
from pdf_report import build_pdf_report
from charts import add_percentile_bands

st.set_page_config(page_title="Pension Simulator", page_icon="£", layout="wide")
import results_store as results_store_model
importlib.reload(results_store_model)
from results_store import save_run, load_run, proposed_name
if st.query_params.get('manager') == '1':
    import results_manager as results_manager_model
    importlib.reload(results_manager_model)
    from results_manager import render_manager
    render_manager()
    st.stop()
if st.query_params.get('restore'):
    try:
        restored = load_run(st.query_params['restore'])
        for key, value in restored['controls'].items():
            st.session_state[key] = value
        st.session_state.run_controls = restored['controls']
        st.session_state.result = restored['result']
        st.session_state.source = restored['result'].get('source')
        st.session_state.result_signature = json.dumps(restored['result']['inputs'],sort_keys=True)
        st.session_state.restored_run_name = restored['name']
    except (OSError,ValueError,KeyError) as error:
        st.error('Cannot restore saved run: '+str(error))
    st.query_params.pop('restore')
st.link_button('Open Simulation Results Manager', '?manager=1')
if st.session_state.get('restored_run_name'):
    name = escape(st.session_state.restored_run_name)
    st.markdown('<h1 style="display:flex;align-items:baseline;flex-wrap:wrap;gap:0.5rem 1.25rem">'
                'Pension Simulator'
                '<span style="font-size:1rem;font-weight:400;color:var(--text-color);'
                'opacity:0.7;overflow-wrap:anywhere">'+name+'</span></h1>',unsafe_allow_html=True)
else:
    st.title("Pension Simulator")
st.caption("Gordon & Ann · real-pound portfolio forecasts · separate nominal tax calculations")


def percent(label, default, key, minimum=-100.0, maximum=100.0):
    # Initialise once; passing both a default and an existing session value
    # produces Streamlit's conflicting-widget-state warning on preset/restore.
    if key not in st.session_state:
        st.session_state[key] = float(default*100)
    return st.number_input(label, min_value=float(minimum), max_value=float(maximum),
                           step=.1, format="%.2f", key=key)/100


def money(label, default, key, decimals=0, minimum=0.0, maximum=None, disabled=False):
    # Streamlit number_input cannot group thousands or show a £ prefix.
    # Keep the numeric value separately so rounding the display never rounds
    # calculated defaults (notably proportional account allocations).
    raw_key = key+"_raw"
    if key not in st.session_state:
        st.session_state[raw_key] = float(default)
        st.session_state[key] = f"£{default:,.{decimals}f}"
    elif isinstance(st.session_state[key], (int, float)):
        st.session_state[raw_key] = float(st.session_state[key])
        st.session_state[key] = f"£{st.session_state[raw_key]:,.{decimals}f}"

    def commit():
        try:
            value = float(st.session_state[key].replace('£', '').replace(',', '').strip())
            if not math.isfinite(value) or (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
                return
            st.session_state[raw_key] = value
            st.session_state[key] = f"£{value:,.{decimals}f}"
        except ValueError:
            pass

    entered = st.text_input(label, key=key, on_change=commit, disabled=disabled)
    try:
        parsed = float(entered.replace('£', '').replace(',', '').strip())
        if not math.isfinite(parsed) or (minimum is not None and parsed < minimum) or (maximum is not None and parsed > maximum):
            raise ValueError
    except ValueError:
        st.error(f"Enter a valid pound amount for {label}." +
                 (f" Maximum: £{maximum:,.0f}." if maximum is not None else ""))
        st.stop()
    return st.session_state[raw_key]


def present_table(table):
    rates = {"nominal_return", "inflation", "y", "exact_real_return", "normal_nominal_return", "total_return", "real_return"}
    formats = {}
    for name in table.select_dtypes(include="number").columns:
        if name in {"year", "simulation", "scenario", "gordon_age", "source_row", "assessment_year"}:
            formats[name] = "{:.0f}"
        elif name in {"cpi_start", "cpi_end"}:
            formats[name] = "{:.1f}"
        elif name in rates:
            formats[name] = "{:.2%}"
        elif name in {"inflation_index", "threshold_scale"}:
            formats[name] = "{:.4f}"
        else:
            formats[name] = "£{:,.0f}"
    return table.style.format(formats, na_rep="—")


def cashflow_table(table, real):
    """Select one currency view without showing duplicate reporting columns."""
    displayed = table.copy()
    if real:
        for name in table.columns:
            if name+'_real' in table.columns:
                displayed[name] = table[name+'_real']
    aliases = [name for name in displayed if name.endswith('_real') and name != 'portfolio_real']
    return displayed.drop(columns=aliases+(['portfolio_nominal'] if real else ['portfolio_real']), errors='ignore')


if "source" not in st.session_state or (st.session_state.source and st.session_state.source.get("calibration_method") != "ten_anniversary_twr_years"):
    try:
        st.session_state.source = load_snapshot()
    except (OSError, ValueError):
        st.session_state.source = None

with st.expander("Portfolio source and historical calibration", expanded=st.session_state.source is None):
    path = st.text_input("Excel workbook (cached values; macros are never run)", DEFAULT_WORKBOOK)
    if st.button("Read latest workbook and recalibrate"):
        try:
            with st.spinner("Reading workbook…"):
                source = read_workbook(path)
                save_snapshot(source)
                st.session_state.source = source
                # Update only the source-driven controls on an explicit refresh.
                for key in ("balance", "start_date", "initial_y", "std_y"):
                    st.session_state.pop(key, None)
                for name in ACCOUNT_NAMES:
                    st.session_state.pop("balance_"+name, None)
                st.rerun()
        except (OSError, ValueError, KeyError) as error:
            st.error(str(error))
    source = st.session_state.source
    if source:
        st.write(f"Saved valuation: **£{source['balance']:,.0f}** at **{source['valuation_date']}**. "
                 f"Historical mean y: **{source['mean_y']:.2%}**; sample standard deviation: **{source['std_y']:.2%}**.")
        if 'portfolio_cagr' in source:
            st.write(f"Ten-year compound annual rates: portfolio **{source['portfolio_cagr']:.3%}**, "
                     f"CPI **{source['cpi_cagr']:.3%}**, difference **{source['cagr_y']:.3%}**.")
            if source.get('vs_target_cagr') is not None:
                st.caption(f"Row 50 reconciliation: E50 minus H50 = {source['cagr_y']:.3%}. "
                           f"J50 also subtracts the {source['target_margin']:.2%} target margin, "
                           f"giving {source['vs_target_cagr']:.3%}. The arithmetic annual mean above "
                           "is used for Normal y draws; CAGR already includes compounding effects.")
        n=len(source['history'])
        if n >= 2:
            margin=student_t.ppf(.975,n-1)*source['std_y']/math.sqrt(n)
            st.warning(f"Only {n} annual observations support a long-term return assumption. "
                       f"Indicative 95% confidence interval for mean y: "
                       f"{source['mean_y']-margin:.2%} to {source['mean_y']+margin:.2%} "
                       "(independent Normal annual observations assumed).")
        history = pd.DataFrame(source["history"])
        st.dataframe(present_table(history), hide_index=True)
        st.caption("Ten consecutive single-year time-weighted returns ending at the valuation date, from "
                   "Pension_Performance A6:J51. y = portfolio return minus CPI inflation; sample standard "
                   "deviation uses ten annual observations, not overlapping multi-year averages. "
                   "The workbook's configured CPI lag is retained. Exact compounded real returns are also shown.")
        st.caption(f"Source: {source.get('performance_source', 'Legacy snapshot — refresh the workbook')}. "
                   f"CPI lag: {source.get('cpi_lag_months', 'unknown')} months.")

        if st.button("Use ten-year y estimates"):
            st.session_state.initial_y = source['mean_y']*100
            st.session_state.std_y = source['std_y']*100
            st.rerun()
    else:
        st.info("Load the workbook to initialise historical mean and volatility. You can also enter assumptions manually below.")

defaults = Settings()
source = source or {"balance": defaults.starting_balance, "valuation_date": defaults.start_date,
                    "std_y": defaults.std_y, "mean_y": defaults.initial_y}

# Restore personal inputs cleared by the old Evelyn preset once. Future
# manual edits, including zero contributions, survive ordinary reruns.
if st.session_state.get('personal_income_defaults_version') != 1:
    for key,value,decimals in [('citibank',defaults.gordon_citibank_pension,2),
                               ('ann_contribution',2880.0,0),
                               ('g_bank_interest_confirmed',defaults.gordon_interest,0),
                               ('a_bank_interest_confirmed',defaults.ann_interest,0)]:
        if st.session_state.get(key+'_raw',0) == 0:
            st.session_state[key+'_raw']=value
            st.session_state[key]=f'£{value:,.{decimals}f}'
    if st.session_state.get('ann_rental_confirmed_raw') == 10000:
        st.session_state.ann_rental_confirmed_raw=defaults.ann_property
        st.session_state.ann_rental_confirmed=f'£{defaults.ann_property:,.0f}'
    st.session_state.ann_contribution_net_mode=st.session_state.get('ann_contribution_raw',2880) <= 2880
    st.session_state.personal_income_defaults_version=1

# Migrate existing browser sessions once, before constructing return widgets.
# Streamlit retains explicit session values when a widget's default changes.
if st.session_state.get('custom_return_defaults_version') != 2:
    if st.session_state.get('projection_mode', 'Custom') == 'Custom':
        st.session_state.initial_y = source['mean_y']*100
        st.session_state.std_y = source['std_y']*100
    st.session_state.custom_return_defaults_version = 2

with st.sidebar:
    st.header("Projection")

    def apply_scenario():
        number = st.session_state.selected_evelyn
        if not number:
            st.session_state.initial_y = source['mean_y']*100
            st.session_state.std_y = source['std_y']*100
            return
        st.session_state.last_evelyn = number
        preset = evelyn_preset(number)
        widget_map = {'years': 'projection_years', 'initial_y': 'initial_y',
                      'gift_years': 'gift_years', 'crash_enabled': 'crash_enabled',
                      'property_sale_enabled': 'property_sale_enabled'}
        for field, key in widget_map.items():
            value = preset[field]*100 if field in {'initial_y', 'std_y'} else preset[field]
            st.session_state[key] = value
        # Keep a historical volatility ready for switching the preset to stochastic.
        st.session_state.std_y = source['std_y']*100
        st.session_state.simulation_type = 'Non-stochastic (zero volatility)'
        st.session_state.simulation_count = 1
        money_map = {'gift': 'gift', 'withdrawal': 'withdrawal'}
        for field, key in money_map.items():
            value = preset[field]
            st.session_state[key+'_raw'] = value
            st.session_state[key] = f'£{value:,.2f}' if key == 'citibank' else f'£{value:,.0f}'

    if 'projection_mode' not in st.session_state:
        st.session_state.projection_mode = ('Evelyn preset' if st.session_state.get('selected_evelyn', 0) else 'Custom')

    def switch_projection_mode():
        if st.session_state.projection_mode == 'Custom':
            st.session_state.initial_y = source['mean_y']*100
            st.session_state.std_y = source['std_y']*100
        else:
            st.session_state.selected_evelyn = st.session_state.get('last_evelyn', 1)
            apply_scenario()

    projection_mode = st.radio('Projection mode', ['Custom', 'Evelyn preset'],
                               horizontal=True, key='projection_mode', on_change=switch_projection_mode)
    if projection_mode == 'Evelyn preset':
        labels = {n: evelyn_label(n, g, y) for n, g, y in EVELYN_SCENARIOS}
        if st.session_state.get('selected_evelyn', 0) not in labels:
            st.session_state.selected_evelyn = st.session_state.get('last_evelyn', 1)
            apply_scenario()
        selected_evelyn = st.selectbox('Scenario preset', list(labels), format_func=labels.get,
                                       key='selected_evelyn', on_change=apply_scenario)
        st.caption('Choose a preset to set gifts and returns, then Run simulation. Personal income and pension contributions are preserved. The past gift is already included in the starting balance. The original Evelyn reference remains visible as a benchmark, including when you add stochastic simulations or pension top-ups.')
    else:
        selected_evelyn = 0
        st.caption(f"Custom: historical y defaults are {source['mean_y']:.2%} mean and "
                   f"{source['std_y']:.2%} standard deviation. Inputs remain editable. "
                   "Switching to Custom restores these two estimates; other settings stay as displayed.")
    def sync_simulation_count():
        if st.session_state.simulation_type != 'Stochastic':
            st.session_state.simulation_count = 1
        elif st.session_state.get('simulation_count', 100) == 1:
            st.session_state.simulation_count = 100

    def sync_simulation_type():
        st.session_state.simulation_type = ('Non-stochastic (zero volatility)'
                                            if st.session_state.simulation_count == 1 else 'Stochastic')

    if 'simulation_count' not in st.session_state:
        st.session_state.simulation_count = (1 if st.session_state.get('simulation_type') ==
                                             'Non-stochastic (zero volatility)' else 100)
    mode = st.radio("Simulation type", ["Stochastic", "Non-stochastic (zero volatility)"],
                    key='simulation_type', on_change=sync_simulation_count)
    non_stochastic = mode != "Stochastic"
    start = st.date_input("Valuation date", date.fromisoformat(source["valuation_date"]), key="start_date")
    balance = money("Starting portfolio (£)", source["balance"], "balance")
    years = st.number_input("Years", 1, 60, 30, key='projection_years')
    simulations = st.selectbox("Simulations", [1, 10, 100, 500, 1000],
                               format_func=lambda n: '1 (Non-stochastic)' if n == 1 else str(n),
                               key='simulation_count', on_change=sync_simulation_type)
    seed = st.number_input("Random seed", 0, 2147483647, 42, disabled=non_stochastic,key="random_seed")
    st.header("Returns")
    inflation = percent("Fixed CPI inflation (%)", .02, "inflation", -10, 30)
    initial_y = percent("Base case and first-year y (%)", source["mean_y"], "initial_y", -50, 100)
    if non_stochastic:
        std_y = 0.0
        st.number_input("Annual standard deviation of y (%)", value=0.0, format="%.2f", disabled=True,
                        key="deterministic_volatility")
    else:
        std_y = percent("Annual standard deviation of y (%)", source["std_y"], "std_y", 0, 100)
    annual_fee = percent("Additional annual investment fee (%)",0.0,"annual_fee",0,20)
    st.caption("Fees are deducted monthly. Leave at zero if your return estimate is already after fees.")
    yield_rate = percent("Reinvested income yield (%)", .0267, "yield", 0, 30)
    st.caption("Total return = CPI + y. Income yield is included in this return.")
    st.caption("The portfolio is calculated in real pounds using (1 + CPI + y) ÷ (1 + CPI) − 1. Tax is calculated separately in nominal pounds.")
    st.caption("One forecast with fixed CPI + y every year; all volatility is zero." if non_stochastic else
               "From year two, annual y is drawn around the same selected y used in year one.")
    st.header("Taxes")
    if "taxes_enabled" not in st.session_state:
        st.session_state.taxes_enabled = True

    def switch_taxes():
        st.session_state.taxes_enabled = not st.session_state.taxes_enabled

    st.button("Remove all taxes" if st.session_state.taxes_enabled else "Restore taxes",
              on_click=switch_taxes)
    taxes_enabled = st.session_state.taxes_enabled
    st.caption("Income tax and CGT: " + ("on." if taxes_enabled else "off. Pension contribution relief is unchanged."))
    st.header("Withdrawals and gifts")
    withdrawal = money("Annual regular withdrawal (£)", 150000, "withdrawal")
    gift = money("Annual gift (£)", 150000, "gift")
    gift_years = st.number_input("Gift duration (years)", 0, 60, 10, key='gift_years')
    st.caption("Regular withdrawals: 11 monthly payments of 1/15 of the annual amount, then 4/15 in month 12, each inflated from Day 0. Gifts stay fixed. Gordon pays tax from his annual bank receipt; no extra tax withdrawal is made from Evelyn.")
    st.header("Market crisis")
    crash_enabled = st.checkbox("Include a one-off crash", False, key='crash_enabled')
    crash_loss = percent("Crash loss (%)", .4, "crash_loss", 0, 100)
    crash_window = st.number_input("Random crash within first N years", 1, min(20, years), min(20, years), disabled=non_stochastic,key="crash_window")
    stress_year = st.number_input("Deterministic stress-case crash year", 1, years, min(10, years), disabled=not non_stochastic,key="stress_year")
    st.caption("Normal annual return is followed by the crash loss. Gifts stop in the crash year and never resume.")
    st.header("Rental property sale")
    property_sale_enabled = st.checkbox("Sell rental property", False, key='property_sale_enabled')
    property_sale_mode = st.radio('Rental property sale trigger',['date','threshold'],
        format_func=lambda value: 'Specified date' if value == 'date' else 'Portfolio value threshold',
        disabled=not property_sale_enabled,key='property_sale_mode')
    property_sale_threshold = money('Sell when portfolio reaches (£, real)',defaults.property_sale_threshold,
        'property_sale_threshold',disabled=not property_sale_enabled or property_sale_mode != 'threshold')
    property_sale_date = st.date_input("Rental property sale date", anniversary(start, 5),
                                       min_value=start, key="property_sale_date", disabled=not property_sale_enabled or property_sale_mode != 'date')
    property_sale_amount = money("Rental property sale proceeds (£)", defaults.property_sale_amount,
                                 "property_sale_amount", disabled=not property_sale_enabled)
    st.caption("Proceeds are nominal pounds credited to Ann's GIA with no property CGT. "
               "Rental profit stops on the sale date; the sale year's profit is prorated by days.")
    if property_sale_mode == 'threshold':
        st.caption('The threshold is in valuation-date purchasing power. Each path is checked at the start and monthly, '
                   'after market changes and including that month’s withdrawals. Sale is assumed immediate at the first '
                   'value at or below the threshold; proceeds can fund that month’s payment. '
                   'The property is sold only once, and rent stops on its actual sale date.')
    if property_sale_enabled and property_sale_mode == 'date' and property_sale_date > anniversary(start, years):
        st.caption("The selected sale falls after the projection, so it has no effect on these results.")

with st.expander("Accounts and tax inputs"):
    st.write("Starting account balances are scaled from the 15 October account schedule. "
             "Starting GIA gain assumptions use twice the approximately six-month CGT YTD figures: "
             "Gordon £2,902 × 2 = £5,804; Ann £3,837 × 2 = £7,674, as requested.")
    scaled = REFERENCE_BALANCES/REFERENCE_BALANCES.sum()*balance
    c1, c2 = st.columns(2)
    account_values, gains, shares, tfc_shares, lsas = [], [], [], [], []
    for j, col in enumerate((c1, c2)):
        with col:
            st.subheader(("Gordon", "Ann")[j])
            for k in range(j*3, j*3+3):
                # Default allocation follows the total unless explicitly edited.
                account_values.append(money(ACCOUNT_NAMES[k]+" (£)", scaled[k], "balance_"+ACCOUNT_NAMES[k]))
            gains.append(money("GIA unrealised gain (£)", REFERENCE_GAINS[j], f"annualised_gain_{j}", minimum=None))
            fraction = percent("Dividends as share of GIA yield (%)", .5, f"fixed_dividend_share_{j}", 0, 100)
            shares.append(fraction)
            tfc_shares.append(percent('Tax-free share of SIPP withdrawals (%)',
                defaults.gordon_tax_free_share if j == 0 else defaults.ann_tax_free_share,f'tfc_share_{j}',0,25))
            lsas.append(money('Remaining lump sum allowance (£)',
                defaults.gordon_lsa_remaining if j == 0 else defaults.ann_lsa_remaining,f'lsa_{j}'))
    if st.button("Reset account balances to proportional allocation"):
        for name in ACCOUNT_NAMES:
            st.session_state.pop("balance_"+name, None)
        st.rerun()
    st.write(f"Account total: **£{sum(account_values):,.0f}**")
    st.caption("Gordon defaults to no remaining tax-free cash. Ann defaults to 25% tax-free withdrawals, capped by her remaining nominal LSA. Confirm Ann’s pension statement; set her share to zero if already taken. "
               "Each GIA defaults to 50% dividends and 50% securities interest; the split is editable for each owner.")
    st.caption("Automatic ISA funding: each year, up to £20,000 nominal moves from Gordon's GIA to Gordon's ISA "
               "and from Ann's GIA to Ann's ISA, limited by each GIA balance. This uses the assumed full available allowance. "
               "Transfers occur after growth and before ordinary year-end withdrawals; ISA money can then be used by the withdrawal optimiser. "
               "Transfers stay inside the portfolio. GIA sale gains are included in the annual tax calculation, paid from Gordon's bank receipt.")
    st.subheader('Withdrawal and estate assumptions')
    strategy = st.selectbox('Withdrawal strategy',['estate','annual_tax'],
        format_func=lambda x: 'Estate-aware pension drawdown' if x == 'estate' else 'Minimise current annual tax',
        key='withdrawal_strategy')
    tax_rules = st.selectbox('Tax rules',['current_law','legacy_2026_27'],
        format_func=lambda x: 'Current law' if x == 'current_law' else 'Legacy 2026/27 with five-year indexation',key='tax_rules')
    auto_target = st.checkbox('Choose SIPP income target automatically',True,key='auto_target')
    target_input = money('Taxable income target per owner (£)',50270,'sipp_income_target',disabled=auto_target)
    sipp_target = None if auto_target else target_input
    iht_rate = percent('Marginal inheritance tax rate (%)',.4,'iht_rate',0,100)
    beneficiary_rate = percent('Beneficiary pension income tax rate (%)',.4,'beneficiary_rate',0,100)
    final_death = st.checkbox('Assess estate at final projection year',True,key='final_death')
    assessment_input = st.number_input('Estate assessment year',1,years,min(years,30),disabled=final_death,key='assessment_input')
    assessment_year = None if final_death else assessment_input
    st.caption('The estate objective assumes both nil-rate bands are used by other property and no residence nil-rate band remains. '
               'The marginal IHT rate applies to the whole investment portfolio. Beneficiary tax applies to pensions after IHT, '
               'assuming death at 75 or over. Earlier-death assessments are sensitivities, not actual death transitions.')
    st.caption('Both owners retain their own allowances and tax bands for the whole horizon. First death and survivor changes '
               'are not modelled. Gifts may be potentially exempt transfers under the seven-year rule or qualify as normal '
               'expenditure out of income; gift exemptions and death-tax add-backs are not modelled.')
    c1, c2, c3 = st.columns(3)
    with c1:
        citibank = money("Gordon Citibank pension per year (£)", defaults.gordon_citibank_pension, "citibank", decimals=2)
        citibank_cpi = st.checkbox("Increase Citibank pension with CPI", True, key="citibank_cpi")
        citibank_growth = (None if citibank_cpi else
                           percent("Citibank annual pension increase (%)", 0.0, "citibank_growth", -10, 30))
        g_interest = money("Gordon gross external bank interest per year (£)", defaults.gordon_interest, "g_bank_interest_confirmed")
        state_weekly = money("Gordon full State Pension, 2026/27 (£/week)", 241.30, "state_weekly", decimals=2)
    with c2:
        a_interest = money("Ann gross external bank interest per year (£)", defaults.ann_interest, "a_bank_interest_confirmed")
        a_property = money("Ann taxable rental profit per year (£)", defaults.ann_property, "ann_rental_confirmed")
        contribution_is_net=st.checkbox('Enter Ann contribution as bank cash',True,key='ann_contribution_net_mode')
        contribution_label=('Ann annual bank contribution (£)' if contribution_is_net
                            else 'Ann annual gross SIPP contribution (£)')
        a_contribution = money(contribution_label,defaults.ann_pension_contribution,
                                'ann_contribution',maximum=2880.0 if contribution_is_net else 3600.0)
        contribution_portfolio = st.checkbox("Fund Ann's contribution from portfolio", False, key='contribution_portfolio')
        a_state = money("Ann State Pension, 2026/27 (£/year)", 9494.0, "ann_state")
    with c3:
        earnings = percent("Future earnings growth for triple lock (%)", .025, "earnings", -10, 30)
        st.caption("Triple lock = max(CPI, earnings growth, 2.5%). Gordon starts on 27 June 2028. "
                   "Pensions are prorated for eligibility and 6 April upratings.")
    st.caption("External income is taxed but does not reduce the specified portfolio withdrawal or get reinvested. Taxes are paid from Gordon's bank receipt within the regular withdrawal. "
               "External interest and rental income stay fixed in nominal pounds; Citibank pension increases are editable. "
               "Evelyn GIA income in the original schedule is replaced by the yield calculation, avoiding double counting.")
    st.caption("Gordon's P60 confirms £3,354.36 of Citibank pension, not savings interest. "
               "Gross external bank interest defaults to £1,644 for Gordon and £352 for Ann. "
               "Securities interest and UK/foreign dividends are already included in the GIA yield. "
               "RBC income ended in 2025/26. Historical James Hay withdrawals, PAYE deductions and the indicated refund "
               "are not additional recurring income or tax charges.")
    st.caption("Charitable donations are excluded from forecast withdrawals and tax relief, as requested. "
               "The historical returns imply dividend shares of 78.81% of Gordon's GIA income and 95.45% of Ann's. "
               "These are historical reference figures; the forecast uses your selected dividend shares, defaulting to 50% each. "
               "Ann's £9,306 State Pension in the return relates to 2025/26; the newer schedule's £9,494 remains the starting forecast amount.")
    st.caption("Ann's default £2,880 annual bank payment receives £720 relief while eligible, giving £3,600 gross in the SIPP. "
               "Contributions stop when relief is unavailable (from age 75 in this model). Gross-entry mode is also available. "
               "Contributions occur at each period end. If portfolio-funded, the cash payment is an additional "
               "withdrawal and is skipped when obligations cannot be fully funded. Evelyn presets preserve personal income and contribution inputs.")


settings = Settings(start_date=start.isoformat(), starting_balance=balance, years=years,
                    evelyn_scenario=selected_evelyn,
                    non_stochastic=non_stochastic,
                    simulations=simulations, seed=seed, inflation=inflation, initial_y=initial_y,
                    std_y=std_y, taxes_enabled=taxes_enabled, income_yield=yield_rate, withdrawal=withdrawal,
                    gift=gift, gift_years=gift_years, crash_enabled=crash_enabled,
                    crash_loss=crash_loss, crash_window=crash_window, deterministic_crash_year=stress_year,
                    earnings_growth=earnings, gordon_citibank_pension=citibank,
                    gordon_citibank_growth=citibank_growth, gordon_interest=g_interest,
                    ann_interest=a_interest, ann_property=a_property,
                    property_sale_enabled=property_sale_enabled, property_sale_date=property_sale_date.isoformat(),
                    property_sale_amount=property_sale_amount,
                    property_sale_mode=property_sale_mode,property_sale_threshold=property_sale_threshold,
                    ann_pension_contribution=a_contribution, ann_contribution_is_net=contribution_is_net,
                    ann_contribution_from_portfolio=contribution_portfolio,
                    ann_state_pension=a_state, gordon_state_weekly=state_weekly,
                    dividend_share_gordon=shares[0], dividend_share_ann=shares[1],
                    gordon_tax_free_share=tfc_shares[0],ann_tax_free_share=tfc_shares[1],
                    gordon_lsa_remaining=lsas[0],ann_lsa_remaining=lsas[1],
                    withdrawal_strategy=strategy,sipp_income_target=sipp_target,
                    iht_rate=iht_rate,beneficiary_income_tax_rate=beneficiary_rate,
                    estate_assessment_year=assessment_year,tax_rules=tax_rules,annual_fee=annual_fee)
model_root = Path(__file__).resolve().parent
model_revision = hashlib.sha256(b''.join((model_root/name).read_bytes() for name in
    ['app.py', 'simulation.py', 'withdrawals.py', 'tax_ledger.py', 'tax.py', 'data/evelyn_reference.csv', 'sources.py', 'tax_rules.py', 'strategies.py', 'pdf_report.py', 'charts.py', 'results_store.py', 'results_manager.py'])).hexdigest()
signature = json.dumps({"settings": asdict(settings), "accounts": account_values, "gains": gains,
                        "model_revision": model_revision}, sort_keys=True)

if st.button("Run simulation", type="primary"):
    bar = st.progress(0, text="Simulating annual returns, withdrawals and bank-paid taxes…")
    try:
        result = simulate(settings, account_values, gains, progress=lambda p: bar.progress(p))
        result["inputs"] = json.loads(signature)
        result["source"] = st.session_state.source
        st.session_state.run_controls = {k:v for k,v in st.session_state.items()
            if isinstance(v,(str,int,float,bool,date)) and k not in
            {'result_signature','pdf_report_key','pdf_report_filename','save_run_name','restored_run_name'}}
        st.session_state.result = result
        st.session_state.result_signature = signature
        st.session_state.pop('save_run_name',None)
    except (ValueError, RuntimeError) as error:
        st.error(str(error))
    finally:
        bar.empty()

if "result" not in st.session_state:
    st.info("Set the assumptions, then select Run simulation. The 30-year model calculates taxes and account withdrawals for every path.")
else:
    result = st.session_state.result
    if st.session_state.result_signature != signature:
        st.warning("Inputs have changed, or the model code has been updated. These results show the previous run; select Run simulation to update them.")
    with st.expander('Save simulation run'):
        if 'save_run_name' not in st.session_state:
            st.session_state.save_run_name = proposed_name(result)
        name = st.text_input('Saved run name',key='save_run_name')
        st.caption('Stores the completed run and its original inputs, including all paths in compressed JSON. Saved locally in data/saved_runs; not uploaded.')
        if st.button('Save simulation run',disabled=st.session_state.result_signature != signature):
            try:
                save_run(name,result,st.session_state.get('run_controls',{}))
                st.success('Saved '+name)
            except (ValueError,OSError) as error:
                st.error(str(error))
    real = st.radio("Show portfolio values in", ["Real pounds", "Nominal pounds"], horizontal=True) == "Real pounds"
    field = "portfolio_real" if real else "portfolio_nominal"
    q = result["quantiles"].query("value == @field")
    base = result["base"]
    detail = result["details"]
    deterministic_result = result["settings"].get("non_stochastic", False)
    reference = result.get('evelyn_reference')
    reference_number = result['settings'].get('evelyn_scenario', 0)
    reference_reasons=evelyn_mismatches(settings)
    # Hide immediately when controls diverge, including while old results
    # await rerunning. Never overlay an old preset against a newly selected one.
    if reference_reasons or selected_evelyn != reference_number:
        reference=None
    if selected_evelyn and reference is None:
        reasons=reference_reasons or result.get('evelyn_reference_mismatches',[])
        st.caption('Evelyn reference hidden: '+(', '.join(reasons)+' differ from the preset comparison assumptions.'
                   if reasons else 'run the selected preset to show its matching reference.'))
    with st.expander('Withdrawal strategy comparison'):
        st.caption('Deterministic base-case comparison in real pounds. T=0 reproduces the annual-tax policy. '
                   'One target is selected and reused for stochastic and stress paths. Tax sums stop at the assessment year. '
                   'This is a policy search, not a complete estate plan. It does not withdraw and reinvest surplus pension cash.')
        if 'strategy_comparison' in result:
            st.dataframe(present_table(result['strategy_comparison'].drop(columns='T')),hide_index=True)
            st.write('Earlier second-death assessments')
            st.dataframe(present_table(result['strategy_sensitivity'].drop(columns='T',errors='ignore')),hide_index=True)
    fig = go.Figure()
    if not deterministic_result:
        add_percentile_bands(fig,q.year,q)
    if deterministic_result and non_stochastic:
        fig.add_trace(go.Scatter(x=base.year, y=base[field], name="Our model: fixed y, no crash",
                                 hovertemplate="Year %{x} · Base: £%{y:,.0f}<extra></extra>",
                                 line=dict(color="#d47724", width=3, dash="solid")))
    if result["stress"] is not None:
        stress = result["stress"]
        fig.add_trace(go.Scatter(x=stress.year, y=stress[field], name="Fixed y with crash",
                                 hovertemplate="Year %{x} · Stress: £%{y:,.0f}<extra></extra>",
                                 line=dict(color="#ad3045", width=2, dash="dot")))
    if reference is not None:
        fig.add_trace(go.Scatter(x=reference.year, y=reference[field], mode='lines',
                                 name=f'Evelyn S{reference_number}: original chart (approx.)',
                                 line=dict(color='#0072b2', width=3, dash='dash'),
                                 hovertemplate='Year %{x} · approximately £%{y:,.0f}<extra>Evelyn chart estimate</extra>'))
    fig.update_layout(height=540, xaxis_title="Years from valuation date",
                      yaxis_title="Portfolio (£, valuation-date purchasing power)" if real else "Portfolio (£, nominal)",
                      yaxis_tickprefix="£", yaxis_tickformat=",.0f",
                      yaxis_rangemode="tozero", yaxis_range=[0, None], hovermode="x unified",
                      margin=dict(t=20, l=20, r=20, b=20), legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")
    if reference is not None:
        st.caption(f"Evelyn S{reference_number} is the original real-value chart, approximately digitised from the supplied Word document "
                   "and rounded to £10,000, not another run of our model. Years 0–34 correspond to Gordon's ages 65–99. "
                   "The reference is not rescaled to our starting balance and is not extended beyond year 34. "
                   "In nominal view it is converted using this run's CPI assumption. Simulation count and volatility do not change the reference. Our model includes your selected pension top-ups; the original Evelyn illustration does not. Other projection inputs must match the preset comparison assumptions.")
    st.caption("Non-stochastic forecast: zero volatility and fixed CPI + y each year. Any enabled crash uses the selected fixed year."
               if deterministic_result else
               "Green bands are above the median and pink/red below it, with darker bands nearer the median. Deciles describe each year’s distribution, not individual investable paths. "
               "The deterministic base case holds y at its initial value; simulated y is random from year two.")
    if detail.return_clipped.fillna(False).any():
        st.warning("Some normal draws implied a loss below 100%; those returns were limited to a 100% loss.")
    if detail.solver_warning.fillna(False).any():
        st.caption("Some optimisation starts did not converge. Feasible alternatives were compared and every selected cash flow reconciled. "
                   "The withdrawal strategy uses a numerical tax search; a global optimum is not guaranteed.")
    st.subheader('Net annual income after tax in real terms')
    income_data=detail.query('year > 0').copy()
    if 'net_annual_income_real' not in income_data:
        income_data['net_annual_income_real']=household_net_income(income_data)
    income_fig=go.Figure()
    if deterministic_result:
        forecast=income_data.sort_values('year')
        income_fig.add_trace(go.Scatter(x=forecast.year,y=forecast.net_annual_income_real,
            mode='lines',name='Net annual income after tax',line=dict(color='#246b47',width=3),
            hovertemplate='Year %{x} · £%{y:,.0f}<extra></extra>'))
    else:
        income_q=(income_data.groupby('year').net_annual_income_real
                  .quantile(np.arange(.1,1,.1)).unstack())
        income_q.columns=[f'p{int(round(c*100))}' for c in income_q.columns]
        add_percentile_bands(income_fig,income_q.index,income_q)
    income_fig.update_layout(height=420,xaxis_title='Years from valuation date',
        xaxis=dict(dtick=1 if result['settings']['years'] <= 15 else 5),
        yaxis_title='Net annual income (£, valuation-date purchasing power)',
        yaxis_tickprefix='£',yaxis_tickformat=',.0f',yaxis_rangemode='tozero',hovermode='x unified',
        margin=dict(t=20,l=20,r=20,b=20),legend=dict(orientation='h'))
    st.plotly_chart(income_fig,width='stretch')
    st.caption('Actual regular portfolio receipts plus State Pensions, Citibank pension, rental profit and external bank interest, '
               'less the full income-tax and CGT liability. Always shown in valuation-date pounds. '
               'Family gifts, property-sale proceeds and reinvested investment income are excluded; '
               'voluntary pension contributions are not deducted. Negative values indicate a cash deficit after tax.')
    st.caption('The median and shaded 10th–90th percentile range use the simulated paths for each year. Green is above the median, pink/red below it; darker bands are nearer the median, '
               'including any portfolio depletion. External income continues after the portfolio runs out.'
               if not deterministic_result else
               'This is the selected non-stochastic forecast, including any enabled fixed-year crash.')
    with st.expander("Annual cash flows and account balances"):
        selection = st.selectbox("Inspect", ["Base case"] + (["Fixed y with crash"] if result["stress"] is not None else [])
                                + (['Evelyn reference (approx.)'] if reference is not None else [])
                                + [f"Simulation {i}" for i in sorted(detail.simulation.unique())])
        table = (base if selection == "Base case" else result["stress"] if selection == "Fixed y with crash"
                 else reference if selection == 'Evelyn reference (approx.)'
                 else detail[detail.simulation == int(selection.split()[-1])])
        st.dataframe(present_table(cashflow_table(table, real)), hide_index=True)
        st.caption('All monetary amounts in this table are in '+
                   ('valuation-date purchasing power (real pounds).' if real else 'nominal pounds.')+
                   ' Tax liabilities are calculated in nominal pounds and converted only for the real display. CSV exports retain both views.')
        st.caption("Regular paid is the gross amount transferred to Gordon's bank. Tax paid comes from that receipt, not an additional Evelyn withdrawal. "
                   "Spendable after tax shows the remaining regular receipt. Unpaid tax identifies any liability exceeding that receipt; it is not funded by the portfolio. "
                   "Shortfall measures unfunded portfolio withdrawals. Balances cannot become negative and no borrowing is assumed.")
    with st.expander("Download results"):
        current_run=st.session_state.result_signature == signature
        pdf_data=b''
        if current_run:
            pdf_key=hashlib.sha256((signature+str(real)+str(reference is not None)).encode()).hexdigest()
            if st.session_state.get('pdf_report_key') != pdf_key:
                st.session_state.pdf_report_data=build_pdf_report(result,fig,income_fig,real=real)
                st.session_state.pdf_report_key=pdf_key
                st.session_state.pdf_report_filename='pension_simulation_report_'+datetime.now(ZoneInfo('Europe/London')).strftime('%Y-%m-%d_%H-%M-%S')+'.pdf'
            pdf_data=st.session_state.pdf_report_data
        st.download_button('PDF report',pdf_data,st.session_state.get('pdf_report_filename','pension_simulation_report.pdf'),'application/pdf',
                           disabled=not current_run,
                           help='Simulation parameters followed by both graphs. Run the simulation after changing inputs before exporting.')
        st.download_button("Deciles CSV", result["quantiles"].to_csv(index=False), "pension_deciles.csv", "text/csv")
        st.download_button("Base case CSV", base.to_csv(index=False), "pension_base_case.csv", "text/csv")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("assumptions.json", json.dumps({"inputs": result["inputs"], "source": result["source"],
                              "evelyn_reference": ({'scenario': reference_number,
                                  'source': 'Scenario Projections 2026-10-21.docx',
                                  'method': 'Approximate chart digitisation, rounded to GBP 10,000; no rescaling',
                                  'nominal_conversion_cpi': result['settings']['inflation']}
                                  if reference is not None else None)}, indent=2))
            for name, table in [("all_paths.csv", detail), ("base_case.csv", base), ("deciles.csv", result["quantiles"])]:
                archive.writestr(name, table.to_csv(index=False))
            for name in ('strategy_comparison','strategy_sensitivity'):
                if name in result:
                    archive.writestr(name+'.csv',result[name].to_csv(index=False))
            if result["stress"] is not None:
                archive.writestr("stress_case.csv", result["stress"].to_csv(index=False))
            if reference is not None:
                archive.writestr(f"evelyn_scenario_{reference_number}_reference_approx.csv", reference.to_csv(index=False))
            archive.writestr("crash_years.json", json.dumps(result["crash_years"]))
        st.download_button("All paths and assumptions ZIP", buffer.getvalue(), "pension_simulation.zip", "application/zip")
        chart_html=fig.to_html(include_plotlyjs=True)
        chart_html=chart_html.replace('</body>',income_fig.to_html(full_html=False,include_plotlyjs=False)+'</body>')
        st.download_button("Interactive chart HTML", chart_html, "pension_forecast.html", "text/html")

with st.expander("Model conventions and tax sources"):
    st.markdown("""
    Monthly receipts retain constant Day-0 purchasing power. Annual periods are assigned to the UK tax year
    containing their midpoint. Current law uses 22/42/47% property and savings rates from 2027/28,
    and keeps personal allowance/basic band frozen through 2030/31, then indexes annually with CPI without catch-up.
    Other allowances and thresholds remain fixed nominal. Legacy mode retains the previous five-year indexation.
    Nominal GIA costs and losses are tracked separately from real portfolio values. ISA transfers remain internal.

    The estate strategy draws from both pensions towards a common taxable-income target, then GIA/ISA,
    with a full optimiser fallback if needed. Automatic selection compares lifetime tax plus marginal IHT and
    beneficiary income tax on pension left. The death objective is a valuation only: both owners remain alive in
    the forecast, with two allowances and tax bands throughout. Gifts, exemptions and seven-year add-backs are excluded
    from this objective. Ann defaults to 25% tax-free pension cash subject to her remaining fixed nominal LSA;
    Gordon defaults to zero. These inputs are editable. No surplus pension drawdowns are reinvested.
    Additional fees default to zero and are deducted monthly; avoid double-counting fees already in returns.

    Verified 6 November 2026:
    [Pension IHT technical note](https://www.gov.uk/government/publications/inheritance-tax-on-pensions-technical-note/technical-note-inheritance-tax-on-pensions) ·
    [Property and savings technical note](https://www.gov.uk/government/publications/changes-to-tax-rates-for-property-savings-and-dividend-income/change-to-tax-rates-for-property-savings-and-dividend-income-technical-note) ·
    [Income tax](https://www.gov.uk/income-tax-rates) ·
    [Dividend tax](https://www.gov.uk/tax-on-dividends) ·
    [Savings allowances](https://www.gov.uk/apply-tax-free-interest-on-savings/how-much-tax-you-pay) ·
    [CGT](https://www.gov.uk/capital-gains-tax/rates) ·
    [Capital losses](https://www.gov.uk/capital-gains-tax/losses) ·
    [State Pension](https://www.gov.uk/new-state-pension/what-youll-get) ·
    [State Pension age](https://www.gov.uk/government/publications/state-pension-age-timetable/state-pension-age-timetable).
    """)
