# Pension Simulator

Streamlit model for Gordon and Ann Bowser. Balances are projected in valuation-date pounds, with a separate nominal income-tax and CGT ledger. The Word manual is [docs/Pension_Simulator_Model_Guide.docx](docs/Pension_Simulator_Model_Guide_Updated.docx).

## Run

From this directory in PowerShell:

```powershell
.\Run_Pension_Simulator.ps1
```

Open http://localhost:8501. Keep the terminal open; Ctrl+C stops the server. A fresh install needs Python 3.12+, a virtual environment and `pip install -r requirements.txt`.

## Projection modes

**Custom** restores the ten-year y mean and sample standard deviation. Other controls retain their displayed values. Inputs remain editable. **Evelyn preset** exposes these 34-year non-stochastic comparisons:

| Preset | Annual gift | Gift years | Nominal total return |
|---|---:|---:|---|
| S1 | £0 | 0 | CPI + 2.5% |
| S2 | £100,000 | 5 | CPI + 2.5% |
| S3 | £150,000 | 5 | CPI + 2.5% |
| S4 | £200,000 | 5 | CPI + 2.5% |
| S5 | £100,000 | 5 | CPI only |
| S6 | £150,000 | 5 | CPI only |
| S7 | £200,000 | 5 | CPI only |

Presets set the regular annual Day-0 withdrawal to £150,000, the specified gifts/returns, and disable crashes and property sale. They preserve personal pension income, bank interest, rent and Ann's contribution settings. They also retain tax rules, withdrawal strategy, tax-free assumptions, fees and other shared controls. A one-time update restores personal values that the old presets cleared. The past gift is already reflected in the starting portfolio. The original Evelyn chart is shown only when portfolio-driving assumptions match the comparison baseline (2% CPI, £4,335,877 opening balance, zero additional fees). External income and tax/account-order settings do not affect the gross portfolio comparison. Switching to Stochastic, changing the simulation count or volatility, and retaining Ann's pension top-ups are allowed while retaining the reference. The original Evelyn illustration excludes those top-ups; our model includes them. The original chart is approximate digitisation, not adviser numerical data, and is not rescaled or extrapolated beyond year 34.

## Cash flows and accounts

Opening total: £4,335,877 on 5 November 2026. The six source account weights are scaled proportionally to that total and remain editable. Starting GIA gain proxies are £5,804 for Gordon and £7,674 for Ann, twice the roughly six-month CGT YTD annotations; they are not verified acquisition costs.

The £150,000 regular annual amount is constant Day-0 purchasing power. It is paid 1/15 at months 1–11 and 4/15 at month 12, each inflated continuously from Day 0. At 2% CPI, year-one nominal receipts total £151,896. Family gifts are additional, fixed nominal amounts for the selected duration; they stop permanently in the crash year. Taxes are paid within the regular bank receipt and never grossed up into an extra portfolio withdrawal.

Annual nominal return is CPI + y, including the selected reinvested yield (2.67% initially). The real factor is `(1 + CPI + y) / (1 + CPI)`. Annual returns compound evenly in twelve monthly steps. A crisis is a separate multiplicative loss at year-end. Additional annual fees default to 0% and compound monthly; avoid double-counting fees already included in calibrated returns. All accounts receive the same total return and fee rate.

Every year up to £20,000 nominal moves from each owner's GIA to their own ISA at the period end, before the final monthly receipt. This is an internal transfer, limited by available GIA. Disposal gains are included in that owner's annual total. ISA funds may subsequently be withdrawn. There is one annual CGT exemption and capital-loss settlement, not twelve.

Gordon defaults to fully taxable pension withdrawals and zero LSA. Ann defaults to 25% tax-free cash per pension withdrawal, capped at £268,275 remaining nominal LSA. This new assumption must be confirmed from her statement; set her share to zero if it was already taken. The optimiser never consumes LSA while searching, only when recording actual withdrawals.

Custom external defaults remain Citibank pension £3,354.36 CPI-linked, gross bank interest £1,644/£352, Ann rent £13,019 and State Pension inputs £241.30 weekly for Gordon and £9,494 annually for Ann at the 2026/27 reference. State Pensions use the selected triple-lock assumptions and eligibility dates. External income is taxed but neither offsets the regular portfolio receipt nor automatically reinvests. GIA yield is 50% dividends and 50% securities interest for each owner by default. Charity donations are ignored.

Ann's default contribution is **£2,880 cash from the bank**. While eligible, £720 relief makes **£3,600 gross** in her SIPP. Payments stop when relief is unavailable (from age 75 in this model). Gross-entry mode remains available; API flags `ann_contribution_is_net=False` and `ann_contribution_requires_relief=False` retain the previous fixed-gross, post-75 behaviour for reproducing older configurations. Contributions occur at period end. Portfolio funding is optional and is skipped when obligations cannot be funded. Gordon's Citibank pension remains £3,354.36 initially and increases with CPI by default.

Property sale can be triggered by a **specified date** or a **real portfolio threshold**. In threshold mode, every path is checked at opening and each monthly observation after market returns/fees/crash, including its planned cash outflow. The first value at or below the threshold triggers an immediate sale; proceeds may fund that month's payment. Sale happens once. The threshold is in valuation-date pounds, while sale proceeds remain the entered nominal amount. Proceeds go to Ann's GIA at full acquisition cost with no property-sale CGT, and rent stops on the actual sale date. Triggered sale dates and observed values are included in annual tables/CSVs. The model does not infer intramonth market movements or include a sale delay.

## Withdrawal strategies

The default **estate** policy draws both pensions towards a common taxable-income target, scaled with the allowance/basic-band index and adjusted for other non-savings income and available tax-free cash. Goals are spread over monthly payment weights and scaled together if they exceed cash need. GIA/ISA cover the remainder, with GIA first where tax is equal. The full optimiser can draw more pensions if those accounts are insufficient. No surplus pension withdrawals or reinvestment are assumed.

Automatic target selection evaluates deterministic base cases at 0, £12,570, £50,270, £75,000, £100,000, £125,140 and effectively unlimited (pension first), then five refinements around the best coarse point. T=0 uses the former annual-tax policy. The selected target is reused for every stochastic path and the stress case.

The real objective is income tax and CGT through the assessment year, plus marginal IHT on the portfolio at that year, plus beneficiary income tax on pension left after IHT. Default rates are 40% each, giving a 64% combined marginal death tax on pension wealth. The default assessment is the final year; earlier years 15/20/25/30 are shown where within the horizon. Both nil-rate bands are assumed used by other property and the residence nil-rate band absent. This is a marginal scenario comparison, not a complete estate calculation.

**annual_tax** retains the previous numerical current-year tax search. To reproduce the previous monthly model also select **legacy_2026_27**, set both pension tax-free shares to 0%, and use zero additional fees. The saved S1 baseline is regression-tested. Neither strategy guarantees a globally optimal full-life plan.

## Tax rules

**current_law** is now the default. Each anniversary period uses the tax year containing its midpoint (Nov 2026–Nov 2027 maps to 2027/28). Other non-savings income is taxed first, then property, savings and dividends. Property/savings rates become 22/42/47% in 2027/28; ordinary pensions remain 20/40/45%, dividends 10.75/35.75/39.35%. Remaining PA is beneficially allocated after other non-savings income.

PA £12,570 and basic band £37,700 remain frozen through 2030/31, then rise annually with selected CPI without catch-up. The taper point £100,000, additional taxable threshold £125,140, CGT exemption £3,000, dividend allowance £500, savings allowances and starting band stay nominally fixed, as do ISA and LSA limits. The additional taxable-income threshold is not reduced by PA again. Future indexation uses selected CPI without statutory rounding.

**legacy_2026_27** preserves 2026/27 rates, grouped non-savings/property treatment and the former cumulative five-year CPI scaling at years 6/11/16 onward. Direct tax helper calls without annual parameters retain that legacy interface, including historical 2025/26 validation examples.

**Remove all taxes** disables income tax and CGT, not the estate assessment rates or pension contribution relief. Under fixed gross cash flows and common account returns, strategies and the tax switch do not change total portfolio value; they change account mix and spendable bank cash. Taxes beyond the regular receipt are shown as unpaid. No bank balance or extra tax withdrawal is assumed.

## Return calibration

Read-only cached workbook values come from `D:\Dropbox\My Documents\Home Finances\GPB_Portfolio_2026.xlsm`. Macros are never executed. Pensions columns B/I supply the latest dated balance. Recalculate and save Excel first when cached formula values are stale.

Calibration uses ten separate anniversary years in Pension_Performance A6:J51, D16:D25 minus G16:G25, covering 5 November 2016 to 5 November 2026. Returns are time-weighted and adjusted for payments. The matched CPI figures retain the workbook's two-month lag. Annual y is nominal portfolio return minus annual CPI inflation, consistent with the model's additive CPI + y definition. The arithmetic mean is 2.600557%, and sample standard deviation is 10.117933 percentage points. These are the Custom default mean (also the fixed first-year y) and annual volatility; independent Normal draws begin in year two. Evelyn preset returns are unchanged. Ten annual observations still leave substantial uncertainty about future returns.

Excel E50 portfolio CAGR is 5.960599%, H50 CPI CAGR is 3.607521%, a difference of 2.353078 percentage points. J50 additionally subtracts B10's 2.5% target and is -0.146922 percentage points. These compound measures are cross-checks, not the arithmetic mean used for Normal annual y draws. The app displays both statistics. The old P/Q series and December CPI CSV are not used for calibration. The ignored local snapshot is `data/portfolio_snapshot.json`.

## Outputs and limits

The app shows portfolio and real net-income graphs; headline summary statistics have been removed. Strategy comparisons and earlier-death sensitivities appear in an expander and the results ZIP. Annual exports include nominal/real cash, pension tax-free amounts, remaining LSA, tax year, chosen target, fees, costs, gains and balances. Real receipts sum payments deflated at their actual dates; annual tax is deflated at period end. A portfolio ending at zero does not prove all required payments were met.

Both owners retain their own accounts, allowances and bands throughout the horizon. First death and survivor transitions are not modelled. Gifts may be potentially exempt transfers under the seven-year rule or normal expenditure out of income, but gift exemptions and death-tax add-backs are excluded. Bank balances, detailed share matching and all personal reliefs are outside scope. Optional surplus pension drawdowns and reinvestment are deferred. Property-sale CGT is excluded by instruction. Remaining differences from Evelyn have not been fully reconciled.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

`tax_rules.py` builds annual parameters, `strategies.py` selects deterministic targets and estate sensitivities, and both are included in the app's model fingerprint. ZIP assumptions retain the settings, source and code fingerprint. Changed inputs or code flag old results; run again before comparing forecasts.

## Official sources checked 6 November 2026

- [HMRC property, savings and dividend technical note](https://www.gov.uk/government/publications/changes-to-tax-rates-for-property-savings-and-dividend-income/change-to-tax-rates-for-property-savings-and-dividend-income-technical-note)
- [HMRC pension IHT technical note](https://www.gov.uk/government/publications/inheritance-tax-on-pensions-technical-note/technical-note-inheritance-tax-on-pensions)
- [Income tax threshold freeze through April 2031](https://www.gov.uk/government/publications/maintaining-income-tax-and-equivalent-national-insurance-contributions-thresholds-until-5-april-2031)

Stochastic mode and volatility changes retain an otherwise matching Evelyn reference: it is a deterministic comparator for the simulated distribution. The fixed-y/no-crash model trace is shown only in non-stochastic mode; stochastic graphs show deciles and an eligible Evelyn reference.

## Net annual income chart

The minimum-income metric has been replaced by a real annual household-income graph. It shows actual regular portfolio receipts plus external State Pensions, Citibank pension, rental profit and bank interest, less the full income-tax and CGT liability. Gifts, property-sale principal and reinvested GIA yield are excluded, and voluntary pension contributions are not deducted. Deficits remain negative rather than being floored at zero. Stochastic mode shows the median and a shaded 10th–90th percentile band across the simulated paths; non-stochastic mode shows the selected forecast, including any crash. External income can continue after portfolio depletion. The graph always uses valuation-date purchasing power even when the portfolio graph is set to nominal. `net_annual_income` and `net_annual_income_real` are included in annual exports; real-income deciles are included in the Deciles CSV. The offline HTML download contains both graphs. No headline income or portfolio statistics are shown above the graphs.

## PDF report

After running a simulation, open **Download results → PDF report**. The two-page report starts with the saved simulation's parameters and opening account balances, followed by both graphs. The portfolio uses the selected real/nominal view; annual income remains real. Curves, percentile shading and the eligible dashed Evelyn reference are carried into sharp vector PDF graphics. The download is disabled when inputs or model code have changed until the simulation is rerun, so parameters and results agree. ReportLab is included in requirements.txt; no browser installation is required. The report is generated locally and does not change input files.

Both stochastic graphs use eight shaded percentile bands: green above the median and pink/red below it, darker near the median and lighter towards P10/P90. The median is drawn on top as a dark line. The PDF uses the same colours, fills and curves.
