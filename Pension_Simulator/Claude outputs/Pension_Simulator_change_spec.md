# Pension_Simulator — change specification for UK appropriateness

Prepared 6 November 2026 from a review of `simulation.py`, `tax.py`, `tax_ledger.py`, `withdrawals.py`, `sources.py`, `app.py` (calculation paths) and `docs/Pension_Simulator_Model_Guide.docx`. All 54 existing tests pass before these changes.

Implement the sections in order. Each section lists the decision, the code to change and the tests to add. Keep every existing behaviour available behind a setting where noted, so earlier runs can be reproduced.

---

## 0. Decisions already made by the owners

| Topic | Decision |
|---|---|
| Gordon's SIPP | Maximum tax-free cash already taken. All future withdrawals fully taxable (current behaviour — keep). |
| Ann's SIPP | Status unknown; assume the adviser-recommended route: Ann's 25% tax-free entitlement is still available and taken as 25% of each withdrawal (UFPLS / phased drawdown), up to her remaining Lump Sum Allowance. Make this a setting so it can be switched off if her statement shows it was already taken. |
| Regular withdrawal | £150,000 a year in valuation-date pounds, CPI-indexed so it is constant in real terms (current behaviour — keep). |
| Tax payment | All income tax and CGT paid out of the cash received; no extra portfolio withdrawal for tax (current behaviour — keep). |
| Account order | Inheritance-tax planning must shape which accounts are drawn first. |

---

## 1. Tax-free cash (pension commencement lump sum) per owner

**Problem.** `withdrawals.py` and `simulation.py` treat every SIPP withdrawal as fully taxable non-savings income.

**Change.**

1. Add to `Settings`:
   - `gordon_tax_free_share: float = 0.0`
   - `ann_tax_free_share: float = 0.25`
   - `ann_lsa_remaining: float = 268275.0` (nominal; the Lump Sum Allowance is a fixed cash figure — do not index it)
   - `gordon_lsa_remaining: float = 0.0`
   - Validate shares in [0, 0.25] and allowances ≥ 0.
2. Track cumulative tax-free cash taken per owner in `NominalTaxLedger` (`self.tfc_remaining`, nominal).
3. Everywhere SIPP withdrawals enter tax as non-savings income, replace `w_sipp` with its taxable part:
   `taxable = w_sipp − min(share × w_sipp, tfc_remaining)`.
   This applies in `withdrawals._plan_withdrawals.taxes()`, `withdrawals.plan_withdrawals` (final reconciliation), the monthly `non_savings` list in `simulation.run_path`, and the year-end `owner_tax` call.
4. Reduce `tfc_remaining` only when withdrawals are actually recorded (`record_disposals` or a new `record_pension_withdrawals`), not during the optimiser search.
5. Add output columns `tax_free_cash_gordon`, `tax_free_cash_ann`, `lsa_remaining_ann`.
6. Update the `app.py` caption that says "all tax-free cash has already been taken", and add the two share inputs and the LSA input under "Accounts and tax inputs".

**Tests.**
- With `ann_tax_free_share=0.25`, a £40,000 Ann SIPP withdrawal adds £30,000 to her taxable income.
- Tax-free cash stops once cumulative TFC reaches `ann_lsa_remaining`.
- With both shares 0, results are identical to the current model.

---

## 2. Regular withdrawal and tax payment — keep, but report spending power

The engine already pays 11 × 1/15 and 1 × 4/15 of £150,000 each year, inflated from Day 0, and pays tax from the receipt. Do not change this.

**Add reporting**, because the gross-withdrawal design means spendable income falls when the SIPPs become the main source:
- `spendable_after_tax_real` already exists — add summary metrics in `app.py`: minimum and average real spendable after tax across years (base case), and the year it's lowest.
- Add `lifetime_tax_real` (sum of `total_tax_real`) to the summary metrics.

**Test.** `regular_paid_real` = £150,000 in every fully funded year (within £0.01).

Current baseline for reference (S1 preset, 2% CPI): real spendable falls from about £149k in year 1 to about £101k by year 12. Lifetime tax is about £2.21m nominal.

---

## 3. Estate-aware withdrawal strategy (main change)

### 3.1 Why

`_plan_withdrawals` minimises only the current year's tax, and its shortcut `if isa >= target: w = zeros(4)` spends all ISA money before touching the SIPPs. In S1 this drains the ISAs and GIAs by year 11. After that it forces £190k–£290k a year from the SIPPs, and from year 18 Gordon alone draws £213k+ (losing his personal allowance). Tax averages about £4k a year (real) in years 1–10, then £49k in years 11–20 and £61k in years 21–34.

From 6 April 2027, unused pension funds are in the estate for IHT (Finance Act 2026). When the member dies at 75 or over, the beneficiary also pays income tax on what they draw. Under the new ITEPA s567B deduction, where the IHT is not paid by the scheme, the beneficiary's taxable pension income is reduced by the IHT paid. The effective rate on pension left at death is therefore about `IHT + b × (1 − IHT)` — 64% for a 40% beneficiary. ISAs and GIAs bear IHT only, and GIA unrealised gains are wiped by the CGT uplift on death. That reverses the current ISA-first order.

### 3.2 New settings

- `withdrawal_strategy: str = "estate"` — options `"estate"` (new) and `"annual_tax"` (current behaviour, for reproducing earlier runs).
- `sipp_income_target: float | None = None` — per-owner target for taxable non-savings income each tax year, in today's pounds (scaled with thresholds). `None` means choose it automatically (3.4).
- `iht_rate: float = 0.40`
- `beneficiary_income_tax_rate: float = 0.40`
- `estate_assessment_year: int | None = None` — year at which the second death is assumed for the objective; `None` = final projection year.

### 3.3 Policy applied each year (in `simulation.run_path` / `tax_ledger.allocate`)

1. At the start of each year, for each owner compute
   `room_j = max(0, T × scale − other_non_savings_income_j)`
   where other income is State Pension, Citibank and (Ann) rental profit. Gross it up for tax-free cash: `sipp_goal_j = room_j / (1 − share_j)` while TFC remains.
2. Spread `sipp_goal_j` across the 12 months in proportion to the payment pattern (1/15 … 4/15), capped by that month's remaining cash need and the SIPP balance. Draw Ann's and Gordon's goals together, not one after the other, so both personal allowances and bands are used.
3. Fund the rest of the month's need from GIA and ISA using the existing optimiser with the SIPP caps set to zero. Pass the forced SIPP taxable amounts into `non_savings` so the GIA/ISA choice sees the correct marginal rates.
4. If GIA + ISA cannot fund the rest, fall back to the SIPPs, splitting between owners to equalise marginal rates. The existing full optimiser with all six accounts is acceptable here.
5. In `"estate"` mode, remove the `isa >= target` shortcut.
6. Tie-break between GIA and ISA when tax is equal: draw GIA first (it is taxed every year on its yield, and its embedded gain is small). Keep the annual £20k bed-and-ISA transfer.

### 3.4 Choosing T automatically

Objective (minimise, real pounds):

```
family_tax = Σ_years total_tax_real
           + iht_rate × portfolio_real[assessment_year]
           + beneficiary_income_tax_rate × (1 − iht_rate) × (Gordon SIPP + Ann SIPP)_real[assessment_year]
```

Because all accounts earn the same return and gross withdrawals are fixed, the portfolio total is the same under every strategy. In practice the comparison is lifetime tax against the extra death tax on the pension left.

- In `simulate()`, when `sipp_income_target is None`, run the deterministic base case for candidates T ∈ {0 (legacy behaviour), 12,570, 50,270, 75,000, 100,000, 125,140, unlimited (SIPP first)}. Pick the minimum `family_tax`, then refine with a golden-section or 5-point search between its neighbours. Use the chosen T for every stochastic path and the stress case.
- Return a `strategy_comparison` DataFrame: T, lifetime tax, death taxes, family_tax, SIPP left at assessment, minimum real spendable. Show it in an expander in `app.py` and include it in the ZIP.
- Also report `family_tax` at assessment years 15, 20, 25 and 30, so the owners can see whether the choice holds for an earlier second death.
- Assume both nil-rate bands are used by the house and the rental property, and that the residence nil-rate band has tapered away (estate over £2.35m). So `iht_rate` is the marginal rate on the whole portfolio. State this in the UI.

### 3.5 Optional (phase 2)

- "Surplus drawdown": when a SIPP draw at T exceeds the cash need, reinvest the net surplus into that owner's ISA (within unused £20k) and otherwise GIA. Only worthwhile if 3.4 shows T above the level that £150k alone can absorb.
- A first-death year, after which the survivor holds both ISAs and SIPPs and has only one personal allowance and one set of bands.

### 3.6 Tests

- `"annual_tax"` mode reproduces today's S1 base case exactly.
- In `"estate"` mode with T = £50,270, each owner's taxable non-savings income equals the scaled target in every year where SIPP balance and cash need allow.
- The total portfolio path is identical across strategies (same returns, same gross withdrawals).
- `family_tax` for the chosen T ≤ `family_tax` for T = 0.
- No account goes negative; shortfalls match the legacy strategy when funds are exhausted.

Rough check from the review (S1, my own annual approximation, not the model): filling each owner's basic-rate band from the SIPPs cut lifetime tax from about £2.21m to £1.84m nominal, before tax-free cash and before counting death taxes.

---

## 4. Tax law: bring rules up to current legislation

Add `tax_rules: str = "current_law"` with `"legacy_2026_27"` reproducing today's assumptions (2026/27 rates held fixed, all thresholds raised by 5-year cumulative CPI at years 6, 11, 16…). The guide records that legacy assumption as agreed, so keep it selectable, but default to current law.

### 4.1 Map each projection period to a tax year

Periods run 5 Nov–5 Nov. Assign each period the tax year containing its midpoint (period 1, Nov 2026–Nov 2027 → 2027/28). Expose `tax_year` in the output rows. Moving to true 6 April tax years is a better long-term fix but larger. Note it as future work.

### 4.2 Rates from 2027/28 (`tax.py`)

- Savings income: 22% / 42% / 47% (starting rate, the £5,000 band and the savings allowance unchanged).
- Property income (Ann's rental profit, England/Wales/NI): 22% / 42% / 47%.
- Dividends: 10.75% / 35.75% / 39.35% (already correct from 2026/27).
- Other non-savings income (pensions, State Pension): 20% / 40% / 45%.
- Order of taxation: other non-savings → property → savings → dividends.
- Personal allowance and reliefs: set against other non-savings income first; any remainder against property, savings or dividends in whichever way is most beneficial. Extend the existing candidate search in `income_tax` to a three-way allocation.
- This needs rental profit passed separately from other non-savings income. Change the `owner_tax` / `income_tax` signatures and every caller (`withdrawals.py` ×2, `simulation.py`).

Source: GOV.UK "Change to tax rates for property, savings and dividend income — technical note" (26 Nov 2025).

### 4.3 Thresholds

- Personal allowance £12,570, basic-rate band £37,700 and higher-rate threshold £50,270 frozen to 5 April 2031. Then increase each year by CPI from 2031/32 (statutory indexation resumes). No one-off catch-up for the freeze years.
- Hold fixed in nominal terms (no automatic indexation in law): the £100,000 taper point, CGT annual exemption £3,000, dividend allowance £500, savings allowance £1,000/£500, the £5,000 starting band, the ISA £20,000 limit and the LSA.
- Additional-rate threshold £125,140: hold fixed (conservative). Make it a constant so it can be changed.
- Replace the single `threshold_scale` with a small `TaxParameters` dataclass built per year (allowance, basic band, additional threshold, taper start, CGT exemption, dividend allowance, savings allowance, rates).

### 4.4 Formula fix

In `income_tax` and `owner_tax`, the additional-rate threshold is computed as `125140*scale + relief − pa`. The higher-rate limit applies to taxable income, so it should be `additional_threshold + relief`, without subtracting the allowance. The two agree today only because the allowance is fully tapered at £125,140. Once the allowance is indexed and £125,140 isn't, they diverge.

### 4.5 Tests

- 2027/28: £10,000 taxable savings interest for a basic-rate taxpayer (after nil bands) is taxed at 22%.
- GOV.UK worked example: employment £30,000, property £3,000, savings £400, dividends £200 → £4,146 before finance-cost relief.
- Allowance stays £12,570 for periods up to 2030/31 and is £12,570 × (1+CPI) in 2031/32.
- `legacy_2026_27` reproduces current results.

---

## 5. Smaller recommendations

1. **Fees.** Add `annual_fee: float = 0.0`, deducted monthly from all accounts. Evelyn's illustrations will be after their fees. Without this the model is optimistic, and fees may explain much of the remaining gap with the Evelyn curve.
2. **Return calibration.** The Custom default (mean −0.62% after inflation, standard deviation 13.3 points) comes from five years dominated by 2022's 10% CPI. Show a warning in the UI that it is a very thin basis for a 30-year central assumption, and display the 95% confidence interval of the mean (about ±16 points with n = 5).
3. **Gifts.** £150k a year of gifts are potentially exempt transfers (7-year rule), or may qualify as normal expenditure out of income. Not modelled — add a note in the UI and the guide.
4. **Deaths.** Note clearly that both personal allowances and sets of bands are assumed for the whole horizon (see phase-2 item in 3.5).
5. **Docs.** Update `docs/Pension_Simulator_Model_Guide.docx`: Accounts and income, Tax and withdrawal selection, Modelling boundaries. Also update the "Model conventions and tax sources" expander in `app.py` and add the new GOV.UK sources (IHT on pensions technical note; property/savings/dividend rates technical note).
6. **Code fingerprint.** `app.py` hashes a fixed list of files for `model_revision`. Add any new module.

---

## 6. Open points for the owners (do not block implementation)

- Confirm from Ann's SIPP statement whether her funds are uncrystallised. If tax-free cash was already taken, set `ann_tax_free_share = 0`.
- Beneficiaries' likely income tax rate (default 40%).
- Whether to plan around a particular second-death age (default: end of projection), or to rely on the sensitivity table in 3.4.
