# Pension Simulator

Python browser application for Gordon and Ann's retirement portfolio. It models annual growth, reinvested income, withdrawals, gifts and tax separately across their six accounts. It produces 10th–90th percentile forecasts, a highlighted median, a deterministic base case, optional crisis scenarios, and downloadable cash-flow records.

The investment engine holds all six account balances in **valuation-date real pounds**. A separate nominal tax ledger calculates tax liabilities and account selection. Nominal portfolio values are derived for display/export. Taxes remain payable from Gordon's regular bank receipt, not as extra portfolio withdrawals.

## Run

From this folder in PowerShell:

```powershell
.\Run_Pension_Simulator.ps1
```

Open **http://localhost:8501** if the browser does not open automatically. The server binds to the local machine. To stop it, press Ctrl+C in its terminal.

For a fresh installation with Python 3.12 or later:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\Run_Pension_Simulator.ps1
```

The project environment has already been prepared on this computer. It uses the available bundled Python 3.12 runtime; recreating the environment on another machine needs its own installed Python. No Excel installation is required. The workbook is opened read-only, macros are never executed, and the source files are not altered.

The app refreshes its local tax, withdrawal and simulation module definitions on every rerun. This prevents a running Streamlit process retaining an old Settings class after code updates (previously producing `unexpected keyword argument 'non_stochastic'`).

## Using the app

Choose **Stochastic** or **Non-stochastic (zero volatility)** under Simulation type in the sidebar. Non-stochastic mode runs a single forecast with fixed CPI + y every year, overrides volatility to zero, and ignores the random seed and simulation count. If a crisis is enabled, its date is the selected deterministic stress-case year rather than a random year. The chart shows the fixed-return base and, when enabled, the fixed-year crash case without decile bands. Taxes, spending, gifts, contributions and the property-sale controls apply in either mode. The selected mode, effective zero volatility and single path are recorded in exported assumptions.

Use **Scenario preset** to choose Custom inputs or one of the seven Evelyn scenarios from `Scenario Projections 2026-10-21.docx`. Choosing a scenario populates the controls; **Run simulation** then calculates our model from those displayed inputs and overlays **only that scenario's original Evelyn reference curve**. There are no seven simultaneous modelled comparison lines. The preset defaults to a 34-year non-stochastic run, producing two lines: our model and Evelyn's selected reference. Inputs remain editable after applying a preset, and results are marked stale until rerun. Custom inputs removes the Evelyn reference on the next run and keeps the current control values.

| Fixed comparison | Annual family gifts for five years | Annual growth |
| --- | ---: | --- |
| Evelyn S1 | None | CPI + 2.5% |
| Evelyn S2 | £100,000 | CPI + 2.5% |
| Evelyn S3 | £150,000 | CPI + 2.5% |
| Evelyn S4 | £200,000 | CPI + 2.5% |
| Evelyn S5 | £100,000 | CPI only |
| Evelyn S6 | £150,000 | CPI only |
| Evelyn S7 | £200,000 | CPI only |

Presets preserve the selected valuation date, initial investment balance, account allocation, starting-gain assumptions, CPI, State Pension rates/triple lock, dividend shares and taxes-enabled setting. They set the regular annual withdrawal to £150,000 rising with CPI, rental profit to £10,000, and the gift amount/duration and growth shown above. They select a 34-year non-stochastic run and disable Citibank pension, bank interest, new SIPP contributions, property sale and crashes, matching the stated reference scenario assumptions. The initial £150,000 gift is **not deducted again**, following the user's clarification that it is already reflected in the starting portfolio. Tax is calculated under our current model and paid within Gordon's regular bank receipt; outside income does not offset that gross portfolio receipt. Differences from Evelyn remain visible rather than being calibrated away.

The supplied document contains images, **not underlying chart data**. `data/evelyn_reference.csv` contains approximate total bar values digitised from each of those seven original images, rounded to £10,000. `scripts/extract_evelyn_reference.py` reproduces the extraction using visually checked £0 and £4.5 million gridlines and the top of each green total bar. Gordon's ages 65–99 are mapped to years 0–34. These estimates are not exact adviser calculations. For example, S1's final bar reads approximately £1.36 million, consistent with the prose's rounded £1.4 million.

The original reference values are fixed: they are **not rescaled** to our starting balance, recomputed when controls change, or extrapolated beyond year 34. A shorter projection displays the overlapping years only. The charts provide real pounds; nominal view converts those reference values using the selected CPI assumption, labelled as a conversion rather than an original nominal adviser forecast. The original reference and our model may therefore start at slightly different balances. The annual Inspect selector and results ZIP include the selected reference data; exported assumptions identify the source, scenario and approximate extraction method. A Custom run includes no reference CSV.

1. Open **Portfolio source and historical calibration** and select **Read latest workbook and recalibrate** when the workbook changes. The initial local snapshot is already prepared from 5 November 2026.
2. Set returns, spending, gifts and crisis controls in the sidebar. The initial fixed CPI assumption is 2%.
3. Review **Accounts and tax inputs**. If you change the starting total, use **Reset account balances to proportional allocation**, or enter six balances that sum to the new total.
4. Select **Run simulation**. The default run calculates 100 paths across 30 years. Tax optimisation makes this slower than a return-only Monte Carlo model; a progress indicator shows completion.
5. Switch between nominal and real pounds. Inspect any individual path or the base case in the annual table. Download deciles, a base case, the interactive chart, or a ZIP containing all paths and the assumptions used.

Changing a control does not silently replace the previous result. The app marks results as out of date until you run again. The random seed makes comparisons reproducible. Separate random streams generate returns and crash dates so toggling the crash does not change the normal return draws.

The stale-result check also fingerprints the app, model, tax code and reference CSV. A code update therefore flags a displayed old result even when its inputs have not changed. This prevents forecasts from before a model correction being mistaken for fresh results. The model revision is included in exported input metadata.

Displayed amounts use pound signs and thousands separators, generally to the nearest pound. Pension payment inputs with known pence retain two decimal places. CPI indices have one decimal place; returns and percentage controls have two. Tables show years as integers and inflation/threshold multipliers to four decimal places. Currency fields accept either `£4,335,877` or plain numbers. Display formatting preserves the underlying precision of calculations and unedited proportional account balances; CSV exports retain numeric precision for further analysis.

The annual cash-flow table follows the selected real/nominal view and hides duplicate currency columns. CSV exports preserve the original nominal column names for compatibility and add `_real` counterparts; `portfolio_real` and `portfolio_nominal` remain explicit. `real_return` records the actual purchasing-power return. `investment_gain_real` is real investment growth after inflation, not simply nominal investment gain divided by CPI. `property_sale_proceeds_real` values the deposit at the actual sale date, and `property_sale_investment_gain_real` measures its subsequent real return. These form a reconciled real cash-flow ledger. Nominal tax liabilities, taxable gains and capital-loss pools are deflated only for real-pound reporting; their legal tax calculations remain nominal.

### Real-pound calculation conventions

The input y retains its agreed meaning as an **additive nominal margin above CPI**. Each year's exact real growth factor is `(1 + CPI + y) / (1 + CPI)`, followed by any crisis factor. For CPI 2% and y 2.5%, the real return is approximately **2.451%**, not 2.5%. This refactor does not change the growth assumptions or re-fit the model to Evelyn's charts.

The first annual £150,000 bank transfer is still paid at the end of year one, without an initial CPI uplift. Its real value is therefore `£150,000 / (1 + CPI)`, and that purchasing-power amount stays constant in later years. This preserves the previous timing and forecast exactly; at 2% CPI it is approximately £147,059 at each year end. Fixed nominal gifts and pension contributions are divided by the price index for their payment year. Property-sale proceeds use the price index at the sale date and earn real returns for the remaining part of the year.

`tax_ledger.py` retains nominal GIA acquisition costs, reinvested-income additions and capital-loss pools. It converts the current real account values and cash target into nominal amounts for annual tax-efficient allocation, then returns real withdrawals to the portfolio engine. Acquisition costs are not indexed for inflation: a holding that merely keeps pace with inflation can still generate a nominal taxable gain. State Pensions, outside income, tax bands and pension relief remain in the nominal tax/reporting layer.

The numerical tax optimiser uses canonical inputs at £0.0001 precision to prevent currency-conversion floating-point noise from choosing different local solutions. Actual cash amounts and liabilities are reconciled against unrounded balances afterwards. Account selection and tax estimates may differ from earlier numerically sensitive local solutions, while aggregate investment forecasts are preserved. Seven frozen pre-refactor cases verify portfolio values to a penny across normal growth, gifts, a property sale plus crash, zero inflation, deflation, stochastic returns and a total investment loss.

## Starting portfolio and historical returns

The workbook path defaults to `D:\Dropbox\My Documents\Home Finances\GPB_Portfolio_2026.xlsm`.

- `Pensions`: scan columns B (date) and I (balance), selecting the latest dated positive balance. The current result is **£4,335,877 on 5 November 2026**. An older date in a later row does not replace it.
- `Pension_Performance`: read date and theoretical portfolio index from P41/Q41 downwards. This is the workbook's adjusted performance series, rather than raw balances distorted by cash withdrawals.
- Use the latest five complete calendar years with CPI data. Currently these are 2021–2025. Interpolate log portfolio index levels at 31 December between the surrounding observations. Do not extrapolate or bridge gaps longer than 120 days.
- Calculate nominal annual return from the ratio of year-end indices, then subtract December-to-December CPI inflation to obtain y. This follows the requested additive `nominal return = CPI + y` convention. The table also shows exact compounded real returns `(1 + nominal)/(1 + inflation) - 1`; these are different from the additive y parameter.
- Show the arithmetic historical mean and sample standard deviation (`ddof=1`) of the five y observations. Current historical mean y is approximately **0.1374%**, with standard deviation **12.6242%**. The historical mean is informational; the selected first-year y also sets the mean for later years. The historical standard deviation provides the editable volatility default.

December CPI indices are stored with provenance in `data/cpi_december.csv`, using ONS D7BT, 2015=100. Update this CSV from ONS when the next complete calendar year is available. The app deliberately refuses to silently substitute an older five-year window if a required index is missing. There is no background network download.

The saved local snapshot is `data/portfolio_snapshot.json`. It is excluded from Git because it contains personal financial data. Each exported ZIP includes the source metadata and historical calibration used for that run.

The account schedule in the Word specification is scaled proportionally to the starting total:

| Owner | Account | Reference value | Initial unrealised gains |
| --- | --- | ---: | ---: |
| Gordon | GIA | £179,128 | £5,804 |
| Gordon | ISA | £407,395 | — |
| Gordon | SIPP | £2,766,090 | — |
| Ann | GIA | £543,702 | £7,674 |
| Ann | ISA | £340,267 | — |
| Ann | SIPP | £350,021 | — |

The six listed rows sum to £4,586,603. Their balances scale; the GIA gain amounts remain editable. Under the user's later correction, starting gain assumptions are twice the approximately six-month CGT YTD annotations: **Gordon £2,902 × 2 = £5,804** and **Ann £3,837 × 2 = £7,674**. These replace the previous £34,196/£103,029 figures from the Taxable Gains column. The annualised figures are used as user-specified starting-gain proxies in the pooled acquisition-cost calculation; they are not charged as a fixed annual CGT bill. Future realised gains and CGT continue to be calculated from simulated sales.

## Agreed cash-flow rules

- Thirty annual periods by default, starting at the valuation date. Year one uses the selected y₀, initially 2.5%, for every path. From year two, each simulated y is an independent normal draw with mean y₀ and the editable standard deviation. There is one y control, with no separate mean for subsequent years. Parameters do not roll forward from simulated returns.
- The deterministic base holds y at y₀ throughout and has no crash. With crashes disabled, setting volatility to zero makes every stochastic path match the base.
- The sidebar's **Remove all taxes** button turns off income tax and capital gains tax, including taxes on external income and SIPP withdrawals. **Restore taxes** reverses it. Select Run simulation to update results after switching. In the no-tax scenario withdrawals fund only the specified spending, family gifts and any portfolio-funded pension contribution; no tax gross-up is added. Withdrawals are allocated proportionally across accounts because every account is tax-free in this scenario. Pension contribution amounts and relief-at-source credits remain unchanged, isolating the effect of removing tax charges. The switch is included in exported assumptions and applies to stochastic, base and stress paths alike.
- Total nominal return is fixed CPI + y. The 2.67% annual income yield is **included**, reinvested, and never added to total return a second time. GIA income is taxable even when reinvested; ISA/SIPP internal income is sheltered.
- Apply annual growth first, then make year-end withdrawals. Income yield is measured on opening account balances. Regular spending is £150,000 in year one, then rises with CPI. It always leaves the portfolio; external income never reduces it.
- Tax is calculated but paid from Gordon's bank account **within** the regular £150,000 CPI-linked annual receipt. It is not added to the portfolio withdrawal target. Family gifts remain additional portfolio withdrawals, defaulting to £150,000 per year for ten years without inflation increases. `regular_paid` is the gross bank receipt; `spendable_after_tax` is the receipt less the calculated tax, floored at zero. `tax_paid` records the part of that receipt used for tax. `unpaid_tax` flags any liability exceeding the regular receipt; no extra portfolio withdrawal is assumed to cover it. This model does not track Gordon's separate pre-existing bank balance.
- An enabled crisis occurs once per simulated path, uniformly within the first N years (N defaults to 20). Normal annual growth is followed by the adjustable crisis loss, initially 40%. Thus a normal 4.5% year with a 40% crisis returns `1.045 × 0.6 − 1 = −37.3%`. Subsequent years return to normal draws. Gifts stop in the crisis year and never restart. A separate deterministic stressed line uses a selectable crisis year.
- Normal distributions can imply returns below −100%. Such draws are floored at −100%, recorded and flagged; limited-liability portfolio values cannot become negative.
- Gordon's Citibank pension defaults to **£3,354.36** annually, taxed as ordinary pension income and increasing with scenario CPI, as confirmed by the user. A custom annual increase can be selected instead. This corrects the initial implementation, which had incorrectly classified the schedule's Citibank amount as savings interest. Ann's annual taxable rental profit is **£13,019**, confirmed from the return. External interest and rental income remain fixed nominal amounts. Their taxes are paid from Gordon's regular bank receipt, with no additional portfolio withdrawal. External receipts are assumed spent outside the simulated portfolio and are not reinvested, except for Ann's separately specified pension contribution.
- Ann contributes **£2,880 gross annually**, fixed in nominal pounds, at each period end. The default funding assumption is an external bank payment: **£2,304 net plus £576 relief at source** while she is under 75. This is an explicit modelling assumption because the user confirmed the amount but did not specify its funding source. It can be changed to portfolio funding in the app. The gross contribution is added to Ann's SIPP after growth and withdrawals, so it earns returns from the next period. Basic-rate relief is credited inside the SIPP and is not also subtracted from the income-tax bill. Gross contributions extend her income-tax bands, reduce adjusted net income for the allowance taper and affect the CGT basic-rate band while eligible.
- Ann turns 75 on **26 June 2032**. Period-end contributions before that date qualify for relief; later contributions continue at £2,880 gross but have no tax relief, so the bank payment becomes £2,880. This assumes her provider accepts contributions after age 75. The app caps this input at £3,600 gross for the current no-relevant-earnings model. Pension/property income is not treated as relevant earnings. No tax-free portion of SIPP withdrawals is introduced, preserving the agreed fully taxable withdrawal assumption.
- If portfolio funding is selected, the net pension contribution is an additional portfolio withdrawal. When the portfolio cannot fund all annual requested obligations, the contribution is skipped and its tax relief is removed before recalculating withdrawals. Externally funded contributions can continue after portfolio exhaustion; they are explicit new capital, not investment return.
- Gross external bank interest defaults to **£1,644 for Gordon** and **£352 for Ann**, using the reported bank-interest amounts and the user's confirmation that bank interest is external and received gross. Securities/gilt interest and dividends are internal to the modelled GIA yield and are never added a second time.
- Each annual period automatically funds **Gordon's ISA from Gordon's GIA** and **Ann's ISA from Ann's GIA**, up to **£20,000 nominal per person**, limited by the remaining balance in that person's GIA. The real transfer amount is £20,000 divided by that year's closing CPI index. The £20,000 limit stays fixed, including when income-tax thresholds are uprated. The model assumes the full allowance is available and does not model subscriptions elsewhere. It follows the existing one-allowance-per-anniversary-period approximation rather than separate 6 April transaction scheduling.
- ISA subscriptions occur after annual growth and any property-sale deposit, before ordinary year-end withdrawals. They are internal transfers, not spending or part of `gross_withdrawal`; total portfolio value is conserved. ISA balances may subsequently fund the regular cash withdrawal under the existing current-year tax minimisation rule. Thus the gross subscription need not equal the increase in the ISA's closing balance. New ISA holdings earn sheltered income from the next period. This applies to Custom and all Evelyn presets, with taxes enabled or disabled.
- Funding an ISA entails selling GIA holdings. The model reduces the GIA's pooled nominal acquisition cost proportionately and combines the transfer sale's gain/loss with all other GIA sales in that year. It applies the owner's CGT exemption and carried-forward losses **once to the combined gain**, not separately for each sale. Any CGT is paid within Gordon's regular bank receipt. Annual exports identify `gia_to_isa_gordon`, `gia_to_isa_ann` and the corresponding transfer gains, with `_real` reporting counterparts. `realised_gain_gordon/ann` include both transfer and ordinary withdrawal sales.
- Charitable donations are excluded from both forecast withdrawals and forecast tax relief, following the user's final instruction that they are paid from a bank account and sufficiently small to ignore. Historical Gift Aid remains relevant only to reproducing the supplied historical tax calculation. Family gifts continue to follow the separate gift and crash controls.
- **Rental property sale** controls in the sidebar optionally sell the property on a specified date for specified nominal proceeds. No property CGT is charged, as requested. Rental profit is prorated by actual days up to the sale date, then becomes zero permanently. The proceeds are credited once to Ann's GIA and added pound-for-pound to its acquisition cost; the deposit itself creates neither taxable income nor a GIA capital gain. Subsequent investment income and gains receive normal GIA tax treatment. The chart shows the investment portfolio, so the property is outside it until sold.
- Sale proceeds earn the normal annual return compounded for the fraction of the sale period remaining. Their income yield is prorated over that fraction and included in that return, not added again. The annual crash is assumed to occur at period end: proceeds invested before then experience the crash in full; proceeds deposited on the exact period-end date arrive after the crash. Sale proceeds are available for the year's year-end withdrawals. A sale on the initial valuation date is included in year one, while year zero shows only the starting investment portfolio. A sale on a later anniversary is included once at that anniversary. Sales beyond the horizon have no effect; dates before the valuation date are rejected. Annual exports identify rental profit, sale proceeds and investment gain on the proceeds separately.
- Ann's starting annual State Pension is £9,494 from the supplied schedule, treated as her 2026/27 amount. Gordon's full new State Pension starts on **27 June 2028**, using the current full rate of £241.30/week × 52 as the 2026/27 reference. Both uprate each 6 April by max(fixed CPI, editable future earnings growth, 2.5%). Earnings growth initially defaults to 2.5%. Payments are prorated by actual days for eligibility and tax-year uprating dates.
- On exhaustion, available portfolio withdrawals fund the regular gross bank receipt first, then family gifts; taxes are accounted for within the bank receipt. No borrowing is assumed. Ann's explicitly modelled externally funded pension contribution can replenish the SIPP at period end; no other replenishment is assumed. `shortfall` measures requested portfolio cash that could not be transferred, separately from any tax exceeding the bank receipt.

## Tax model

The app uses the 2026/27 England/Wales/Northern Ireland regime, verified on 6 November 2026. Rates are held fixed for all future years **by the requested scenario assumption**, including where legislation may otherwise specify future changes. Each anniversary period receives one full set of annual allowances. This approximates UK tax years; it is not a partial-year tax return calculation.

Ordinary income uses the £12,570 personal allowance, tapering above £100,000, and 20%/40%/45% rates. Savings use the savings starting-rate band and personal savings allowance. Dividends use the £500 nil-rate allowance with 10.75%/35.75%/39.35% rates. Nil-rate savings and dividends still occupy their income-tax bands. Non-savings income receives personal allowance priority; remaining allowance is allocated beneficially between savings and dividends.

Both SIPPs have exhausted their tax-free cash. Every pound withdrawn from them is ordinary taxable income. ISA income, gains and withdrawals are exempt. GIA sales realise a proportionate share of the pooled gain or loss. Reinvested gross GIA income increases acquisition cost, avoiding double taxation of the reinvestment as capital gain. CGT uses the £3,000 exemption and 18%/24% rates, with each person's remaining basic-rate band and carried-forward realised losses. Previous losses offset gains only down to that year's exemption. Loss pools remain separate by owner.

All monetary tax thresholds and allowances, including taper thresholds, savings and dividend allowances and the CGT exemption, are uprated by cumulative CPI at the start of years 6, 11, 16, 21 and 26. They remain fixed between those points. Rates do not change.

### Income mix and withdrawal optimisation

Each owner's GIA income yield defaults to **50% dividends and 50% securities interest**, as requested. The two dividend percentages are independently editable. The app no longer automatically chooses a tax-efficient income mix. Changing the split affects tax character without changing total investment return; external bank interest remains separate.

The annual withdrawal optimiser searches bounded GIA sales and SIPP withdrawals across both owners. ISA withdrawals supply any residual cash. The gross funding target is regular bank receipts plus family gifts and any portfolio-funded pension contribution. Tax is the minimisation objective, **not an additional cash requirement**: Gordon pays it from his regular bank receipt. The solver compares multiple SLSQP starts and feasible wrapper-order candidates, then reconciles the selected withdrawal total. With uniform account returns, enabling taxes changes account selection and spendable bank cash, not the aggregate portfolio withdrawal or total projected value.

This minimises tax numerically for the current year and does not optimise lifetime tax or inheritance outcomes. Because allowances and tax bands create nonsmooth functions, **a global minimum is not guaranteed**. Some starts can fail to converge; the app identifies those runs, compares feasible alternatives, and verifies cash sufficiency. A zero-incremental-tax ISA-only solution is used directly where available. It does not harvest unused pension/CGT allowances merely to preserve ISAs for future years when current tax would be unchanged.

No transfers of assets between owners, ISA subscriptions other than the specified own-GIA funding, share-by-share matching, foreign tax credits, marriage allowance, pension contributions other than Ann's specified recurring amount, death, inheritance tax, transaction fees or separate management fees are modelled. Returns should therefore be entered net of investment fees but before personal taxes. Cash gifts are modelled as withdrawals; gifts of securities are outside this model.

## Source authority

### Comparison with Evelyn Scenario 1

Page 1 of `D:\Dropbox\My Documents\Home Finances\Pension\Scenario Projections 2026-10-21.pdf` describes one immediate £150,000 gift, £150,000 annual expenditure rising with CPI, £10,000 rental income and State Pensions, and CPI + 2.5% growth. It reports approximately £1.4 million in real assets at Gordon's age 99 (34 years).

Our label **base case** means fixed returns with the current controls, not the adviser’s Scenario 1. The original app defaults include £150,000 annual gifts for ten years, and the user's explicit instruction makes the full £150,000 leave the portfolio regardless of external income, with tax formerly withdrawn additionally. That additional-tax rule has since been removed at the user's request. These were material differences from the likely spending-net-of-income interpretation of the adviser’s chart.

The following **historical diagnostic used the former rule of withdrawing additional portfolio money for taxes**. It is superseded by the user's later correction that tax comes from Gordon's bank receipt. Using a common £4,335,877 post-gift investment balance, 34 annual periods, 2% CPI, 2.5% y, no recurring gifts, no crash/property sale, £10,000 rental profit, the specified State Pension amounts and triple lock, taxes enabled, and no pension contributions, Citibank pension or external bank interest gave:

| Diagnostic treatment | Outcome |
| --- | --- |
| Full £150,000 CPI-linked portfolio withdrawal; external income does not offset it | First funding shortfall around year 30 |
| Same tax model, but rental income and State Pensions offset the £150,000 CPI-linked spending target | Approximately £1,595,502 real portfolio after 34 years |

These were separate diagnostic calculations. The production model's agreed withdrawal rule was **not** changed. No second immediate gift was deducted because the common starting balance was treated as post-gift. The £1.60 million diagnostic result is close to the PDF's £1.4 million but does not establish its precise tax, fee, inflation, account-allocation or cash-flow timing assumptions; those are not all specified on page 1. The starting balances also differ. The PDF's spending-net-of-income treatment is an inference supported by the numerical comparison, not a verified statement of its underlying calculation.

The user's answers in the conversation control implementation where they differ from the Word document or PDF. The PDF is a portfolio containing two embedded forecast emails; these were opened as supporting forecast examples. Historical requests inside those emails (including an immediate gift or an expenditure calculation reduced by external income) are not new instructions and have not overridden the agreed settings.

### Gordon income evidence supplied after the first implementation

The Citibank P60 and two HMRC PDFs relate to **2025/26**, ending 5 April 2026. They provide historical evidence; printed instructions to file, submit, retain or pay are not instructions to the simulator or permission to act on an HMRC account.

| Historical item | Evidence | Forward treatment |
| --- | ---: | --- |
| Citibank pension | £3,354.36 gross; no PAYE deducted on this P60 | Recurring ordinary pension income, using the precise P60 amount rather than the whole-pound return amount |
| RBC income | £7,666 | Excluded: the return states 2025/26 is the final year of RBC income |
| James Hay withdrawals | £37,000; PAYE £15,028 | Historical portfolio withdrawals, not a second recurring external pension; future withdrawals remain decisions of the simulator |
| UK bank interest | £1,644 | Gross external interest, confirmed by the user |
| Securities/gilt interest | £160 | Included in GIA yield, confirmed by the user |
| UK dividends | £475 | Included in GIA yield, confirmed by the user |
| Foreign dividends | £120 | Included in GIA yield, confirmed by the user |
| Charitable Gift Aid payments | £1,010 net; HMRC displayed gross band extension £1,263 | Historical validation only; excluded from forecasts under the user's final instruction |
| Total income | £50,419 | Historical calculation only |
| Income tax liability | £7,259.11 | Historical 2025/26 rates and Gift Aid relief; not the annual forecast tax bill |
| PAYE deducted | £17,466 | Credit against the historic liability, not additional tax expense |
| Indicated overpayment | £10,206.89 | Not added to the starting portfolio; the supplied calculation shows 95% completion and does not establish submission, receipt or continued availability of the refund |

The return's capital-gains pages contain no populated loss carry-forward figure. They do not establish a new current unrealised gain or a usable capital-loss pool. The existing gain assumptions remain editable.

A regression test reproduces the displayed £7,259.11 income tax and £10,206.89 PAYE overpayment using 2025/26 dividend rates and the displayed Gift Aid band extension. This does **not** replace the 2026/27 rates used in forecasts. The tax helper accepts explicit historical dividend rates and gross Gift Aid relief for this test; no future Gift Aid relief or donation is assumed.

Source files (read-only): `Citibank Pension P60 April 2026.pdf`, `HMRC_ View your calculation - View your full calculation 2026-05-14.pdf`, and `viewTaxReturnPdf 2026-05-14.pdf`, in `D:\Dropbox\My Documents\Tax\2026\Gordon`.

### Ann income evidence supplied subsequently

Ann's return and calculation cover 2025/26. They show:

| Historical item | Amount | Forward treatment |
| --- | ---: | --- |
| Gross bank interest | £352 | External gross interest; taxable separately from GIA yield |
| Securities/gilt interest | £815 | Already included in GIA yield |
| UK dividends | £6,769 | Already included in GIA yield |
| Foreign dividends | £10,344 | Already included in GIA yield |
| State Pension | £9,306 | Historical amount; retain the newer schedule's £9,494 2026/27 reference and triple lock |
| Taxable rental profit | £13,019 | Confirmed annual forecast profit |
| Personal pension contribution | £2,880 gross, as entered in the return and used by HMRC to extend the band | Confirmed recurring gross annual contribution; funding and age-related relief conventions described above |
| Total income | £40,605 | Historical validation only |
| Income tax | £3,438.03 | Historical validation only; calculate forecast tax afresh |

The historic GIA income mix implied by the reported securities interest and dividends is **78.81% dividends for Gordon** (`595 / (595 + 160)`) and **95.45% for Ann** (`17,113 / (17,113 + 815)`). Bank interest is excluded from these ratios. These are historical reference percentages. The user's later instruction sets the forecast defaults to **50% dividends for both owners**, replacing the automatic tax-efficient mix.

The statement's £1,662.03 payment on account and the calculation's £1,719.01/£1,719.02 future payments on account are payments towards liabilities, not additional annual tax costs. The annual model recognises tax once and does not reconstruct historical HMRC cash settlements or infer that a requested payment remains outstanding. These documents do not authorise a payment or account action.

The supplied capital-gains page has £23,971 in both gains and losses boxes, while proceeds minus costs are £10,471. Those figures do not reconcile without further computations. No historic loss pool or change to current unrealised gains is inferred from them. The current simulation still uses the original, editable unrealised gains and zero initial carried-forward losses.

A regression test reproduces Ann's displayed **£3,438.03** income-tax calculation with the historical 2025/26 dividend rates, the £2,880 gross pension-relief band extension, and the displayed calculation's truncation of income-category tax amounts to pennies. Forecast calculations retain full precision and 2026/27 rates. This check is a reproduction of the supplied calculation, not confirmation that a draft return was submitted or correct in every respect.

Source files (read-only): `Ann Self-Assessment Statement 2026-06-09.pdf`, `HMRC_ View your calculation - View your full calculation 2026-05-14.pdf`, and `viewTaxReturnPdf 2026-05-14.pdf`, in `D:\Dropbox\My Documents\Tax\2026\Ann`.

- [ONS CPI D7BT](https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7bt/mm23)
- [Income tax bands and allowances](https://www.gov.uk/income-tax-rates)
- [Dividend rates](https://www.gov.uk/tax-on-dividends)
- [Savings starting rate and personal savings allowance](https://www.gov.uk/apply-tax-free-interest-on-savings/how-much-tax-you-pay)
- [CGT rates and exemption](https://www.gov.uk/capital-gains-tax/rates)
- [Capital loss carry-forward](https://www.gov.uk/capital-gains-tax/losses)
- [State Pension rate and triple lock](https://www.gov.uk/new-state-pension/what-youll-get)
- [State Pension age timetable](https://www.gov.uk/government/publications/state-pension-age-timetable/state-pension-age-timetable)
- [Gift Aid relief](https://www.gov.uk/donating-to-charity/gift-aid)
- [Pension contribution tax relief](https://www.gov.uk/tax-on-your-private-pension/pension-tax-relief)
- [ISA allowances and subscriptions](https://www.gov.uk/individual-savings-accounts/how-isas-work)

## Developer notes

`sources.py` reads/calibrates Excel; `simulation.py` maintains real balances and generates paths/deciles; `tax_ledger.py` handles nominal acquisition costs, losses and the real/nominal allocation boundary; `tax.py` calculates individual liabilities; `withdrawals.py` allocates the fixed gross cash target; `app.py` presents controls and exports. Each path's CSV includes returns, opening and closing values, tax, requested/paid withdrawals, shortfall, external income, realised gains, loss pools and all six account balances and withdrawals in both reporting currencies.

Run checks from this directory:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Tests cover published tax examples, savings and dividend allowances, CGT/losses, optimised income mix, pension eligibility, five-year threshold jumps, crisis gifting, yield double counting, portfolio exhaustion, reproducibility, workbook extraction, cash-flow reconciliation, and the browser app's run/chart/download/stale-results flow.
