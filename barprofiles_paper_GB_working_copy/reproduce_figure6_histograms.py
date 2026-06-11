"""Codex-created standalone reproduction of Erwin paper Figure 6.

The original converted paper script writes these histograms as six separate
PDFs. This focused script rebuilds the same inputs and writes a single
multi-panel figure, plus a small CSV with the per-panel counts.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
OUTPUT_DIR = PROJECT_DIR / "python_figure_output"

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import barprofile_utils as barprof_utils
import datautils as du


PROFILE_ORDER = ("BP", "Exp", "FT", "2S")
PROFILE_LABELS = {
    "BP": "Peak+Sh",
    "Exp": "Exp",
    "FT": "Flat-top (FT)",
    "2S": "Two-slope (2S)",
}
PROFILE_STYLES = {
    "Exp": {"color": "c", "histtype": "bar", "alpha": 1.0, "lw": 1.0},
    "FT": {"color": "b", "histtype": "step", "alpha": 1.0, "lw": 2.5, "ls": "--"},
    "2S": {"color": "r", "histtype": "bar", "alpha": 0.5, "lw": 1.0},
    "BP": {"color": "k", "histtype": "step", "alpha": 1.0, "lw": 2.0},
}


def get_names(filename: Path) -> list[str]:
    """Return included galaxy names from the paper sample-list format."""

    names: list[str] = []
    with filename.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith("[-]"):
                continue
            names.append(line.split()[0][3:].strip())
    return names


def build_stellar_mass_dict() -> tuple[dict[str, float], list[str], list[str]]:
    s4g_table = du.ReadCompositeTable(DATA_DIR / "s4gbars_table.dat", columnRow=29, dataFrame=True)

    modinc_names = get_names(DATA_DIR / "s4gbars_bp-buckling_profiles_checklist.dat")
    faceon_names = get_names(DATA_DIR / "s4g_faceon_names.dat")
    main_names = set(modinc_names + faceon_names)

    stellar_mass = {
        str(s4g_table.name[i]): float(s4g_table.logmstar[i])
        for i in range(len(s4g_table))
        if str(s4g_table.name[i]) in main_names
    }
    return stellar_mass, modinc_names, faceon_names


def get_classification_values(stellar_mass: dict[str, float], faceon_names: list[str]):
    pe_classifications = barprof_utils.GetClassifications(
        barprof_utils.classificationsFile_pe, barprof_utils.scrambleMap
    )
    vd_classifications = barprof_utils.GetClassifications(
        barprof_utils.classificationsFile_vd2, barprof_utils.scrambleMap
    )

    pe_all, pe_faceon, pe_modinc = barprof_utils.MakeValuesDict(
        pe_classifications, stellar_mass, faceon_names
    )
    vd_all, vd_faceon, vd_modinc = barprof_utils.MakeValuesDict(
        vd_classifications, stellar_mass, faceon_names
    )

    return {
        "PE": {"All": pe_all, "B/P-detection": pe_modinc, "Face-on": pe_faceon},
        "VPD": {"All": vd_all, "B/P-detection": vd_modinc, "Face-on": vd_faceon},
    }


def plot_panel(ax: plt.Axes, values_by_profile: dict[str, list[float]], title: str, ylim: int) -> None:
    bins = np.arange(8.0, 11.5, 0.25)
    handles_by_profile = {}

    for profile in ("Exp", "FT", "2S", "BP"):
        values = values_by_profile.get(profile, [])
        style = PROFILE_STYLES[profile]
        _, _, patches = ax.hist(
            values,
            bins=bins,
            label=PROFILE_LABELS[profile],
            **style,
        )
        handles_by_profile[profile] = patches[0] if patches else None

    ax.set_title(title, fontsize=11)
    ax.set_xlim(8.0, 11.25)
    ax.set_ylim(0, ylim)
    ax.set_xlabel(r"$\log \, M_{\star}$ [$M_{\odot}$]")
    ax.set_ylabel(r"$N$")
    ax.tick_params(labelsize=9)

    handles = [handles_by_profile[key] for key in PROFILE_ORDER if handles_by_profile[key] is not None]
    labels = [PROFILE_LABELS[key] for key in PROFILE_ORDER if handles_by_profile[key] is not None]
    ax.legend(handles, labels, loc="upper left", fontsize=8, frameon=False)


def write_counts_csv(values: dict[str, dict[str, dict[str, list[float]]]]) -> Path:
    output_path = OUTPUT_DIR / "figure6_logmstar_histogram_counts.csv"
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["classifier", "sample", "profile", "plotted_in_figure", "n"])
        for classifier, sample_dict in values.items():
            for sample, values_by_profile in sample_dict.items():
                for profile in sorted(values_by_profile):
                    writer.writerow(
                        [
                            classifier,
                            sample,
                            profile,
                            "yes" if profile in PROFILE_ORDER else "no",
                            len(values_by_profile.get(profile, [])),
                        ]
                    )
    return output_path


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    stellar_mass, modinc_names, faceon_names = build_stellar_mass_dict()
    values = get_classification_values(stellar_mass, faceon_names)

    fig, axes = plt.subplots(3, 2, figsize=(8.0, 9.0), sharex=True)
    rows = [
        ("All", "Combined classified sample", 20),
        ("B/P-detection", "Moderate inclination, low bar/disk PA offset", 18),
        ("Face-on", "Near face-on", 7),
    ]
    columns = [("PE", "PE classifications"), ("VPD", "VPD classifications")]

    for row_index, (sample_key, sample_title, ylim) in enumerate(rows):
        for col_index, (classifier, classifier_title) in enumerate(columns):
            plot_panel(
                axes[row_index, col_index],
                values[classifier][sample_key],
                f"{classifier_title}\n{sample_title}",
                ylim,
            )

    fig.suptitle("Figure 6 reproduction: profile-classified stellar-mass distributions", fontsize=13)
    fig.text(
        0.5,
        0.01,
        f"Sample lists: {len(modinc_names)} B/P-detection galaxies (i=40-70 deg, dPA<=60 deg) "
        f"and {len(faceon_names)} face-on galaxies (i<30 deg).",
        ha="center",
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 0.96))

    figure_path = OUTPUT_DIR / "figure6_logmstar_classification_histograms.pdf"
    png_path = OUTPUT_DIR / "figure6_logmstar_classification_histograms.png"
    fig.savefig(figure_path)
    fig.savefig(png_path, dpi=200)
    counts_path = write_counts_csv(values)

    print(f"Wrote {figure_path}")
    print(f"Wrote {png_path}")
    print(f"Wrote {counts_path}")
    print(f"B/P-detection sample: {len(modinc_names)} galaxies")
    print(f"Face-on sample: {len(faceon_names)} galaxies")


if __name__ == "__main__":
    main()
