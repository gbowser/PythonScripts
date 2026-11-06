"""Minimise tax while allocating a fixed gross portfolio withdrawal."""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import minimize

from tax import TaxResult, owner_tax


@dataclass
class WithdrawalPlan:
    withdrawals: np.ndarray   # Gordon GIA/ISA/SIPP, Ann GIA/ISA/SIPP
    taxes: list
    shortfall: float
    solver_fallback: bool = False


def plan_withdrawals(balances, bases, losses, non_savings, external_interest,
                     yield_income, target, scale, dividend_shares=(None, None), pension_relief=(0.0, 0.0),
                     taxes_enabled=True, prior_gains=(0.0, 0.0), *,
                     tax_free_shares=(0.0,0.0), tfc_remaining=(0.0,0.0),
                     property_income=(0.0,0.0), params=None, gia_first=False):
    """Use stable sub-penny solver inputs; reconcile against exact cash balances.

    Converting real holdings to nominal pounds introduces tiny floating-point
    differences. Canonical inputs stop those differences selecting different
    local optima at nonsmooth tax bands. This never rounds actual cash flows.
    """
    raw_balances = np.asarray(balances, dtype=float)
    if not taxes_enabled:
        return _plan_withdrawals(raw_balances, bases, losses, non_savings, external_interest,
                                 yield_income, target, scale, dividend_shares, pension_relief, False, prior_gains, tax_free_shares=tax_free_shares, tfc_remaining=tfc_remaining,
                                 property_income=property_income, params=params, gia_first=gia_first)
    canonical = lambda values: np.round(np.asarray(values, dtype=float), 4)
    plan = _plan_withdrawals(canonical(raw_balances), canonical(bases), canonical(losses),
                            canonical(non_savings), canonical(external_interest), canonical(yield_income),
                            round(float(target), 4), scale, dividend_shares, canonical(pension_relief), True,
                            canonical(prior_gains), tax_free_shares=tax_free_shares, tfc_remaining=tfc_remaining,
                            property_income=property_income, params=params, gia_first=gia_first)
    withdrawals = np.minimum(raw_balances, np.maximum(0.0, plan.withdrawals))
    remaining = min(target, float(raw_balances.sum()))-float(withdrawals.sum())
    for k in (1, 4, 0, 3, 2, 5):
        adjustment = (min(remaining, raw_balances[k]-withdrawals[k]) if remaining >= 0 else
                      max(remaining, -withdrawals[k]))
        withdrawals[k] += adjustment
        remaining -= adjustment
    taxes = []
    for j in range(2):
        k = j*3
        ratio = 1-bases[j]/raw_balances[k] if raw_balances[k] > 0 else 0.0
        taxes.append(owner_tax(non_savings[j]+taxable_pension(withdrawals[k+2], tax_free_shares[j], tfc_remaining[j]), external_interest[j],
                               yield_income[j], prior_gains[j]+ratio*withdrawals[k], losses[j], scale,
                               dividend_shares[j], pension_relief[j], property_income=property_income[j], params=params))
    return WithdrawalPlan(withdrawals, taxes, max(0.0, target-float(raw_balances.sum())), plan.solver_fallback)


def _plan_withdrawals(balances, bases, losses, non_savings, external_interest,
                      yield_income, target, scale, dividend_shares=(None, None), pension_relief=(0.0, 0.0),
                      taxes_enabled=True, prior_gains=(0.0, 0.0), *,
                     tax_free_shares=(0.0,0.0), tfc_remaining=(0.0,0.0),
                     property_income=(0.0,0.0), params=None, gia_first=False):
    """Minimise this year's household tax with four bounded decision variables.

    ISA cash is the residual. Multi-start SLSQP handles band/allowance kinks;
    all candidates are reconciled to the fixed gross withdrawal afterwards.
    Tax is paid from Gordon's bank receipts, never added to this target.
    This is a numerical search, not a proof of a global minimum.
    """
    balances = np.asarray(balances, dtype=float)
    if not taxes_enabled:
        available = float(balances.sum())
        withdrawals = balances*min(1.0, target/available) if available > 0 else np.zeros(6)
        results = []
        for j in range(2):
            share = 1.0 if dividend_shares[j] is None else dividend_shares[j]
            results.append(TaxResult(0.0, 0.0, yield_income[j]*share,
                                     external_interest[j]+yield_income[j]*(1-share), 0.0, 0.0))
        return WithdrawalPlan(withdrawals, results, max(0.0, target-available))
    ids = [0, 2, 3, 5]
    caps = balances[ids]
    isa = balances[1]+balances[4]
    ratios = [1-bases[j]/balances[3*j] if balances[3*j] > 0 else 0 for j in range(2)]
    unit = 100000.0

    def taxes(w):
        return [owner_tax(non_savings[j]+taxable_pension(w[2*j+1], tax_free_shares[j], tfc_remaining[j]), external_interest[j],
                          yield_income[j], prior_gains[j]+ratios[j]*w[2*j], losses[j],
                          scale, dividend_shares[j], pension_relief[j], property_income=property_income[j], params=params) for j in range(2)]

    def total_tax(w):
        return sum(t.total for t in taxes(w))

    if isa >= target and (not gia_first or caps[[0,2]].sum() == 0):
        # Additional pension income cannot lower tax here. Zero taxable sales
        # achieves the baseline liability, so no numerical search is needed.
        w = np.zeros(4)
        isa_draw = target
        shortfall = 0.0
        fallback = False
    else:
        candidates = []

        def reconcile(direction):
            """Fund the gross target; never add tax or overdraw an account."""
            need = target
            def cash(fraction):
                v = direction*fraction
                return v.sum()+isa-need
            if cash(1) < -1e-5:
                direction = caps.copy()
            if cash(1) < -1e-5:
                return direction, isa, max(0.0, -cash(1))
            if gia_first:
                v=direction*min(1.0,need/max(1e-12,direction.sum()))
                draw=min(isa,max(0.0,need-v.sum()))
                return v,draw,max(0.0,need-v.sum()-draw)
            lo, hi = 0.0, 1.0
            for _ in range(42):
                mid = (lo+hi)/2
                if cash(mid) >= 0:
                    hi = mid
                else:
                    lo = mid
            v = direction*hi
            draw = min(isa, max(0.0, need-v.sum()))
            return v, draw, max(0.0, need-v.sum()-draw)

        # Construct feasible starts with different ownership and wrapper order.
        starts = []
        if gia_first:
            # Include the exact GIA-first candidate: among equal-tax choices
            # use the taxable account before the ISA. Do not introduce a tax
            # penalty merely to satisfy this ordering.
            v = np.zeros(4)
            need = target
            for k in (0, 2):
                v[k] = min(caps[k], need)
                need -= v[k]
            starts.append(v)
        for order in ([0, 2, 1, 3], [1, 3, 0, 2], [2, 0, 3, 1]):
            v = np.zeros(4)
            required = max(0.0, target-isa)*1.8
            for k in order:
                v[k] = min(caps[k], required)
                required -= v[k]
            starts.append(v)
        starts.append(caps*min(1.0, target/max(1.0, caps.sum())*1.6))
        upper = caps/unit

        def net(x):
            v = x*unit
            return v.sum()/unit

        def objective(x):
            return total_tax(x*unit)/unit

        fallback = False
        if caps.sum()+isa < target:
            w, isa_draw, shortfall = caps.copy(), isa, max(0.0, target-caps.sum()-isa)
        else:
            for start in starts:
                candidates.append(reconcile(start))
                result = minimize(objective, start/unit, method="SLSQP",
                                  bounds=list(zip(np.zeros(4), upper)),
                                  constraints=[{"type": "ineq", "fun": lambda x: net(x)-(target-isa)/unit},
                                               {"type": "ineq", "fun": lambda x: target/unit-net(x)}],
                                  options={"maxiter": 100, "ftol": 1e-10, "eps": 1e-6})
                v = np.clip(result.x*unit, 0, caps)
                # Repair small constraint drift using remaining capacities,
                # then gross down along the candidate's withdrawal direction.
                deficit = max(0.0, target-isa-v.sum())
                if deficit > .001:
                    room = caps-v
                    if room.sum() > 0:
                        v += room*min(1.0, 2*deficit/room.sum())
                candidates.append(reconcile(v))
                if not result.success:
                    fallback = True
            feasible = [c for c in candidates if c[2] < .01]
            if not feasible:
                raise RuntimeError("Withdrawal optimisation could not reconcile available funds.")
            w, isa_draw, shortfall = min(feasible, key=lambda c: (round(total_tax(c[0]), 6), -c[0][[0,2]].sum()) if gia_first else total_tax(c[0]))
    withdrawals = np.zeros(6)
    withdrawals[ids] = w
    withdrawals[1] = min(balances[1], isa_draw)
    withdrawals[4] = max(0.0, isa_draw-withdrawals[1])
    return WithdrawalPlan(withdrawals, taxes(w), shortfall, fallback)


def taxable_pension(gross, share, remaining):
    return gross-min(max(0.0,remaining),max(0.0,gross)*share)
