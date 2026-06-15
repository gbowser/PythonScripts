"""Codex-created standalone reproduction for Erwin paper Figures 9-11.

This script uses the Erwin paper working-copy data files and the same hard-coded
logistic coefficients present in ``barprofiles_figures_for_paper.py``. It writes
a combined PDF/PNG plus CSV audit files for the binned frequencies and plotted
logistic-fit coefficients.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
ERWIN_DIR = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Erwin")
OUTPUT_DIR = ERWIN_DIR / "barprofiles_python_figure_output"

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import barprofile_utils as barprof_utils
import datautils as du
import plotutils as pu


COEFFICIENTS = {
    "fig9_bpmorph_logmstar": (-63.006435900515456, 6.122222852940198),
    "fig9_ed17_logmstar": (-42.79, 4.13),
    "fig9_no_ed17_logmstar": (-63.124788674436815, 6.1900522187150075),
    "fig10_bpmorph_logvrot": (-57.964663254824956, 27.008022585107422),
    "fig11_psh_pe_logmstar": (-46.69821364293907, 4.611871122156639),
    "fig11_psh_vpd_logmstar": (-50.61399257635582, 5.018288081365982),
}


def logistic(x: np.ndarray, intercept: float, slope: float) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-(intercept + slope * x)))


def get_names(filename: Path) -> list[str]:
    names: list[str] = []
    with filename.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("[-]"):
                continue
            names.append(line.split()[0][3:].strip())
    return names


def frequency_rows(
    figure: str,
    label: str,
    values: np.ndarray,
    positive_indices: list[int],
    negative_indices: list[int],
    start: float,
    stop: float,
    step: float,
) -> list[dict[str, float | int | str]]:
    bin_edges = np.arange(start, stop, step)
    n_positive, bins = np.histogram(values[positive_indices], bins=bin_edges)
    n_negative, _ = np.histogram(values[negative_indices], bins=bin_edges)
    rows: list[dict[str, float | int | str]] = []

    for i in range(len(n_positive)):
        total = int(n_positive[i] + n_negative[i])
        if total == 0:
            frequency = err_low = err_high = math.nan
        else:
            frequency, err_low, err_high = pu.Binomial(int(n_positive[i]), total)
        rows.append(
            {
                "figure": figure,
                "series": label,
                "bin_start": float(bins[i]),
                "bin_end": float(bins[i + 1]),
                "bin_center": float(0.5 * (bins[i] + bins[i + 1])),
                "n_positive": int(n_positive[i]),
                "n_negative": int(n_negative[i]),
                "n_total": total,
                "frequency": frequency,
                "err_low": err_low,
                "err_high": err_high,
            }
        )
    return rows


def plot_frequency(
    ax: plt.Axes,
    values: np.ndarray,
    positive_indices: list[int],
    negative_indices: list[int],
    start: float,
    stop: float,
    step: float,
    offset: float = 0.0,
    **kwargs,
) -> None:
    pu.PlotFrequency(
        values,
        positive_indices,
        negative_indices,
        start,
        stop,
        step,
        offset=offset,
        noErase=True,
        axisObj=ax,
        **kwargs,
    )


def write_frequency_csv(rows: list[dict[str, float | int | str]]) -> Path:
    output_path = OUTPUT_DIR / "figures9_10_11_frequency_bins.csv"
    fieldnames = [
        "figure",
        "series",
        "bin_start",
        "bin_end",
        "bin_center",
        "n_positive",
        "n_negative",
        "n_total",
        "frequency",
        "err_low",
        "err_high",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def write_coefficients_csv() -> Path:
    output_path = OUTPUT_DIR / "figures9_10_11_logistic_coefficients.csv"
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["fit", "intercept", "slope"])
        for name, (intercept, slope) in COEFFICIENTS.items():
            writer.writerow([name, intercept, slope])
    return output_path


def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)

    s4g_table = du.ReadCompositeTable(DATA_DIR / "s4gbars_table.dat", columnRow=29, dataFrame=True)
    modinc_names = get_names(DATA_DIR / "s4gbars_bp-buckling_profiles_checklist.dat")
    faceon_names = get_names(DATA_DIR / "s4g_faceon_names.dat")
    main_names = modinc_names + faceon_names

    stellar_mass = {str(s4g_table.name[i]): float(s4g_table.logmstar[i]) for i in range(len(s4g_table))}
    logmstar_main = {name: stellar_mass[name] for name in main_names}
    logmstar_modinc = np.array([stellar_mass[name] for name in modinc_names])

    vrot = {
        str(s4g_table.name[i]): -99.0
        if float(s4g_table.V_rot[i]) <= 0
        else math.log10(float(s4g_table.V_rot[i]))
        for i in range(len(s4g_table))
    }
    logvrot_modinc = np.array([vrot[name] for name in modinc_names])

    _, morphology = barprof_utils.GetGalaxyNamesAndDict_morphology()
    bp_morph_indices = [i for i, name in enumerate(modinc_names) if morphology[name] == "B/P"]
    non_bp_morph_indices = [i for i, name in enumerate(modinc_names) if morphology[name] != "B/P"]

    pe = barprof_utils.GetClassifications(barprof_utils.classificationsFile_pe, barprof_utils.scrambleMap)
    vpd = barprof_utils.GetClassifications(barprof_utils.classificationsFile_vd2, barprof_utils.scrambleMap)
    logmstar_s4g_pe, psh_pe_indices, non_psh_pe_indices = barprof_utils.GetValuesAndIndices(pe, logmstar_main)
    logmstar_s4g_vpd, psh_vpd_indices, non_psh_vpd_indices = barprof_utils.GetValuesAndIndices(vpd, logmstar_main)

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2))
    frequency_audit_rows: list[dict[str, float | int | str]] = []

    x_mass = np.arange(9.0, 11.5, 0.01)
    x_vrot = np.arange(1.4, 2.6, 0.01)

    ax = axes[0]
    plot_frequency(ax, logmstar_modinc, bp_morph_indices, non_bp_morph_indices, 8.0, 11.5, 0.25, fmt="ko")
    ax.plot(x_mass, logistic(x_mass, *COEFFICIENTS["fig9_bpmorph_logmstar"]), "0.5", ls="--", lw=2.5, label="Logistic fit")
    ax.plot(x_mass, logistic(x_mass, *COEFFICIENTS["fig9_ed17_logmstar"]), "0.6", ls="--", lw=1.5, label="Fit from ED17")
    ax.plot(x_mass, logistic(x_mass, *COEFFICIENTS["fig9_no_ed17_logmstar"]), "g", ls=":", lw=1.5, label="Fit excluding ED17 galaxies")
    ax.set_title("Figure 9\nB/P bulges vs stellar mass")
    ax.set_xlabel(r"$\log \, M_{\star}$ [$M_{\odot}$]")
    ax.set_ylabel("f(B/P)")
    ax.set_xlim(8.0, 11.5)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=8, loc="upper left", frameon=False)
    frequency_audit_rows.extend(
        frequency_rows("Figure 9", "B/P morphology", logmstar_modinc, bp_morph_indices, non_bp_morph_indices, 8.0, 11.5, 0.25)
    )

    ax = axes[1]
    plot_frequency(ax, logvrot_modinc, bp_morph_indices, non_bp_morph_indices, 1.4, 2.5, 0.05, fmt="ko")
    ax.plot(x_vrot, logistic(x_vrot, *COEFFICIENTS["fig10_bpmorph_logvrot"]), "0.5", ls="--", lw=2.5, label="Logistic fit")
    ax.set_title("Figure 10\nB/P bulges vs rotation velocity")
    ax.set_xlabel(r"$\log V_{\rm rot}$ [km s$^{-1}$]")
    ax.set_ylabel("f(B/P)")
    ax.set_xlim(1.4, 2.5)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=8, loc="upper left", frameon=False)
    frequency_audit_rows.extend(
        frequency_rows("Figure 10", "B/P morphology", logvrot_modinc, bp_morph_indices, non_bp_morph_indices, 1.4, 2.5, 0.05)
    )

    ax = axes[2]
    plot_frequency(
        ax,
        logmstar_s4g_pe,
        psh_pe_indices,
        non_psh_pe_indices,
        8.0,
        11.5,
        0.25,
        offset=-0.01,
        fmt="mo",
        mfc="None",
        label="PE [spirals]",
    )
    plot_frequency(
        ax,
        logmstar_s4g_vpd,
        psh_vpd_indices,
        non_psh_vpd_indices,
        8.0,
        11.5,
        0.25,
        offset=0.01,
        fmt="bo",
        label="VPD [spirals]",
    )
    ax.plot(x_mass, logistic(x_mass, *COEFFICIENTS["fig9_bpmorph_logmstar"]), "0.5", ls="--", lw=2, label="B/P-bulge logistic fit")
    ax.plot(x_mass, logistic(x_mass, *COEFFICIENTS["fig11_psh_pe_logmstar"]), "m", ls="--", lw=2, label="logistic fit (PE)")
    ax.plot(x_mass, logistic(x_mass, *COEFFICIENTS["fig11_psh_vpd_logmstar"]), "b", ls="--", lw=2, label="logistic fit (VPD)")
    ax.set_title("Figure 11\nP+Sh profiles vs stellar mass")
    ax.set_xlabel(r"$\log \, M_{\star}$ [$M_{\odot}$]")
    ax.set_ylabel("f(P+Sh profile)")
    ax.set_xlim(8.0, 11.5)
    ax.set_ylim(-0.05, 1.05)
    ax.legend(fontsize=8, loc="upper left", frameon=False)
    frequency_audit_rows.extend(
        frequency_rows("Figure 11", "P+Sh PE", logmstar_s4g_pe, psh_pe_indices, non_psh_pe_indices, 8.0, 11.5, 0.25)
    )
    frequency_audit_rows.extend(
        frequency_rows("Figure 11", "P+Sh VPD", logmstar_s4g_vpd, psh_vpd_indices, non_psh_vpd_indices, 8.0, 11.5, 0.25)
    )

    fig.suptitle("Reproduction of Erwin paper Figures 9-11", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.92))

    pdf_path = OUTPUT_DIR / "figures9_10_11_logistic_frequency_reproduction.pdf"
    png_path = OUTPUT_DIR / "figures9_10_11_logistic_frequency_reproduction.png"
    fig.savefig(pdf_path)
    fig.savefig(png_path, dpi=200)

    frequency_csv = write_frequency_csv(frequency_audit_rows)
    coefficients_csv = write_coefficients_csv()

    print(f"Wrote {pdf_path}")
    print(f"Wrote {png_path}")
    print(f"Wrote {frequency_csv}")
    print(f"Wrote {coefficients_csv}")
    print(f"B/P morphology sample: {len(modinc_names)} galaxies")
    print(f"Main PE/VPD classification sample: {len(main_names)} galaxies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
