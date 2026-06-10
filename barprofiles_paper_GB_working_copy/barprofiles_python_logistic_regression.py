"""Python replacement for the R logistic-regression script.

This intentionally leaves ``barprofiles_R_logistic_regression.R`` untouched.
It reads the same data tables and fits the same binomial GLM models using
statsmodels.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "python_logistic_output"


fit_records: list[dict[str, float | str]] = []
summary_blocks: list[str] = []


def read_if_exists(filename: str) -> pd.DataFrame | None:
    path = DATA_DIR / filename
    if not path.exists():
        print(f"Skipping missing table: {path}")
        return None
    return pd.read_csv(path, sep=r"\s+", comment="#")


def summarize_fit(label: str, formula: str, data: pd.DataFrame | None):
    if data is None:
        return None
    fit = smf.glm(formula=formula, data=data, family=sm.families.Binomial()).fit()
    header = f"\nModel: {label}\nFormula: {formula}"
    summary = fit.summary().as_text()
    print(header)
    print(summary)
    summary_blocks.append(f"{header}\n{summary}")
    for term in fit.params.index:
        fit_records.append(
            {
                "model": label,
                "formula": formula,
                "term": term,
                "coef": fit.params[term],
                "std_err": fit.bse[term],
                "z": fit.tvalues[term],
                "p_value": fit.pvalues[term],
            }
        )
    return fit


def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    print(DATA_DIR)
    print(PROJECT_DIR)
    print(f"Writing Python logistic-regression output to: {OUTPUT_DIR}")

    table_profs1 = read_if_exists("PSh_profile-vs-stuff.dat")
    summarize_fit("profs1_logMstar", "PSh_profile_both ~ logMstar", table_profs1)
    summarize_fit("profs1_t_leda", "PSh_profile_both ~ t_leda", table_profs1)
    summarize_fit("profs1_logfgas", "PSh_profile_both ~ logfgas", table_profs1)

    table_profs2 = read_if_exists("PSh_profile-vs-stuff_modinc.dat")
    summarize_fit("profs2_logVrot", "PSh_profile_both ~ logVrot", table_profs2)
    summarize_fit("profs2_logMstar", "PSh_profile_both ~ logMstar", table_profs2)
    summarize_fit("profs2_t_leda", "PSh_profile_both ~ t_leda", table_profs2)
    summarize_fit("profs2_logfgas", "PSh_profile_both ~ logfgas", table_profs2)

    table_profs4 = read_if_exists("PSh_profile-vs-stuff_gmr_modinc.dat")
    summarize_fit("profs4_logMstar", "PSh_profile_both ~ logMstar", table_profs4)
    summarize_fit("profs4_t_leda", "PSh_profile_both ~ t_leda", table_profs4)
    summarize_fit("profs4_logfgas", "PSh_profile_both ~ logfgas", table_profs4)
    summarize_fit("profs4_gmr_sga_tc", "PSh_profile_both ~ gmr_sga_tc", table_profs4)

    table_profs3 = read_if_exists("PSh_profile-vs-stuff_gmr+a2max.dat")
    summarize_fit("profs3_logMstar", "PSh_profile_both ~ logMstar", table_profs3)
    summarize_fit("profs3_t_leda", "PSh_profile_both ~ t_leda", table_profs3)
    summarize_fit("profs3_logfgas", "PSh_profile_both ~ logfgas", table_profs3)
    summarize_fit("profs3_gmr_sga_tc", "PSh_profile_both ~ gmr_sga_tc", table_profs3)
    summarize_fit("profs3_A2_max", "PSh_profile_both ~ A2_max", table_profs3)

    table_bp = read_if_exists("bp_morph-vs-logmstar-logmbaryon-logvrot_modinc.dat")
    summarize_fit("bp_logMstar", "bp_morph ~ logMstar", table_bp)
    summarize_fit("bp_logVrot", "bp_morph ~ logVrot", table_bp)

    (OUTPUT_DIR / "logistic_regression_summaries.txt").write_text(
        "\n\n".join(summary_blocks) + "\n",
        encoding="utf-8",
    )
    pd.DataFrame(fit_records).to_csv(
        OUTPUT_DIR / "logistic_regression_coefficients.csv",
        index=False,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
