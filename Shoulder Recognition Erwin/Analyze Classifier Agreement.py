from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from machine_paths import PC_RESEARCH_FOLDERS, shoulder_folder  # noqa: E402

DEFAULT_PC = "Laptop"
WORKBOOK_NAME = "PE_VPD_galaxy_classifications_with_definitions.xlsx"
DEFAULT_WORKBOOK = shoulder_folder(DEFAULT_PC) / WORKBOOK_NAME
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "classifier_agreement_analysis"

HUMAN_RATERS = ["PE", "VPD", "GB"]
HUMAN_LABEL_COLUMNS = {
    "PE": "PE profile label",
    "VPD": "VPD profile label",
    "GB": "GB visual class",
}
PROFILE_CLASSES = ["Peak+Sh", "Exp", "Flat-top (FT)", "Two-slope (2S)"]
SRA_COLUMN = "sra_classification"


def canonical_profile_label(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    normalised = text.lower().replace(" ", "")
    if normalised in {"bp", "bp?", "bp(?)", "peak+sh", "peak+sh?", "peak+shoulders"}:
        return "Peak+Sh"
    if normalised in {"exp", "exp?", "exp(n)", "exp(n)?", "exponential"}:
        return "Exp"
    if normalised in {"ft", "ft?", "ft(n)", "ft(n)?", "flat-top", "flat-top(ft)", "flattop", "flattop(ft)"}:
        return "Flat-top (FT)"
    if normalised in {"2s", "2s?", "2s(n)", "2s(n)?", "two-slope", "two-slope(2s)", "twoslope", "twoslope(2s)"}:
        return "Two-slope (2S)"
    if normalised == "unclear":
        return "Unclear"
    return text


def canonical_sra_binary(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip().lower()
    if text == "shoulders":
        return "Shoulders"
    if text == "no shoulders":
        return "No Shoulders"
    return None


def cohen_kappa(a: pd.Series, b: pd.Series, labels: list[str]) -> float:
    observed = pd.crosstab(
        pd.Categorical(a, categories=labels),
        pd.Categorical(b, categories=labels),
        dropna=False,
    ).to_numpy(dtype=float)
    n = observed.sum()
    if n == 0:
        return math.nan
    po = np.trace(observed) / n
    row = observed.sum(axis=1) / n
    col = observed.sum(axis=0) / n
    pe = float(np.dot(row, col))
    if math.isclose(1.0, pe):
        return math.nan
    return (po - pe) / (1 - pe)


def fleiss_kappa(ratings: pd.DataFrame, labels: list[str]) -> float:
    matrix = np.array(
        [[sum(row == label) for label in labels] for row in ratings.to_numpy()],
        dtype=float,
    )
    n_items, n_raters = matrix.shape[0], len(ratings.columns)
    if n_items == 0 or n_raters < 2:
        return math.nan
    p_j = matrix.sum(axis=0) / (n_items * n_raters)
    p_i = ((matrix * matrix).sum(axis=1) - n_raters) / (n_raters * (n_raters - 1))
    p_bar = p_i.mean()
    p_e = (p_j * p_j).sum()
    if math.isclose(1.0, p_e):
        return math.nan
    return float((p_bar - p_e) / (1 - p_e))


def binary_metrics(y_true: pd.Series, y_pred: pd.Series) -> dict[str, float | int]:
    labels = ["Shoulders", "No Shoulders"]
    tab = pd.crosstab(
        pd.Categorical(y_true, categories=labels),
        pd.Categorical(y_pred, categories=labels),
        dropna=False,
    )
    tp = int(tab.loc["Shoulders", "Shoulders"])
    fn = int(tab.loc["Shoulders", "No Shoulders"])
    fp = int(tab.loc["No Shoulders", "Shoulders"])
    tn = int(tab.loc["No Shoulders", "No Shoulders"])
    total = tp + fn + fp + tn

    def safe(num: float, den: float) -> float:
        return num / den if den else math.nan

    return {
        "n": total,
        "tp": tp,
        "fn": fn,
        "fp": fp,
        "tn": tn,
        "accuracy": safe(tp + tn, total),
        "balanced_accuracy": np.nanmean([safe(tp, tp + fn), safe(tn, tn + fp)]),
        "sensitivity_shoulders": safe(tp, tp + fn),
        "specificity_no_shoulders": safe(tn, tn + fp),
        "precision_shoulders": safe(tp, tp + fp),
        "kappa": cohen_kappa(y_true, y_pred, labels),
    }


def percent(value: float) -> str:
    if pd.isna(value):
        return "NA"
    return f"{100 * value:.1f}%"


def markdown_table(df: pd.DataFrame, floatfmt: str = ".3f") -> str:
    if df.empty:
        return "_No rows._"
    headers = [str(column) for column in df.columns]
    integer_like_columns = {
        column
        for column in df.columns
        if pd.api.types.is_numeric_dtype(df[column])
        and df[column].dropna().map(lambda value: float(value).is_integer()).all()
    }
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        values = []
        for column, value in row.items():
            if isinstance(value, (float, np.floating)):
                if pd.isna(value):
                    values.append("NA")
                elif column in integer_like_columns:
                    values.append(str(int(value)))
                else:
                    values.append(format(float(value), floatfmt))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_csv(df: pd.DataFrame, output_dir: Path, name: str) -> Path:
    path = output_dir / name
    df.to_csv(path, index=False)
    return path


def plot_class_distribution(class_counts: pd.DataFrame, output_dir: Path) -> Path:
    path = output_dir / "human_class_distribution.png"
    pivot = class_counts.pivot(index="class", columns="rater", values="count").reindex(PROFILE_CLASSES)
    ax = pivot.plot(kind="bar", figsize=(9, 5), color=["#2f6f9f", "#84a98c", "#c65d3a"])
    ax.set_title("Human Classifier Label Distribution")
    ax.set_xlabel("")
    ax.set_ylabel("Number of galaxies")
    ax.legend(title="")
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def plot_heatmap(
    matrix: pd.DataFrame,
    title: str,
    path: Path,
    fmt: str = ".2f",
    xlabel: str | None = None,
    ylabel: str | None = None,
) -> Path:
    fig, ax = plt.subplots(figsize=(7, 5.5))
    values = matrix.to_numpy(dtype=float)
    vmax = np.nanmax(values)
    im = ax.imshow(values, cmap="Blues", vmin=0, vmax=vmax)
    ax.set_xticks(range(len(matrix.columns)), matrix.columns)
    ax.set_yticks(range(len(matrix.index)), matrix.index)
    ax.set_title(title)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    for i in range(len(matrix.index)):
        for j in range(len(matrix.columns)):
            value = matrix.iloc[i, j]
            label = "" if pd.isna(value) else format(value, fmt)
            text_color = "#ffffff" if float(value) >= 0.55 * vmax else "#111827"
            ax.text(j, i, label, ha="center", va="center", color=text_color, fontweight="700")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.subplots_adjust(left=0.24, right=0.90, bottom=0.16, top=0.88)
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def plot_human_agreement_by_class(df: pd.DataFrame, output_dir: Path) -> Path:
    path = output_dir / "human_agreement_by_gb_class.png"
    ax = df.set_index("GB class")[
        ["PE matches GB", "VPD matches GB", "PE and VPD both match GB"]
    ].plot(kind="bar", figsize=(10, 5), color=["#2f6f9f", "#84a98c", "#c65d3a"])
    ax.set_title("Human Agreement Conditional on GB Visual Class")
    ax.set_xlabel("")
    ax.set_ylabel("Agreement rate")
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(lambda x, pos: f"{100 * x:.0f}%")
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def plot_sra_metrics(df: pd.DataFrame, output_dir: Path) -> Path:
    path = output_dir / "sra_binary_metrics.png"
    metrics = ["accuracy", "balanced_accuracy", "sensitivity_shoulders", "specificity_no_shoulders", "kappa"]
    plot_df = df.set_index("reference")[metrics]
    ax = plot_df.plot(kind="bar", figsize=(11, 5), color=["#315f72", "#52796f", "#84a98c", "#c65d3a", "#8a4f7d"])
    ax.set_title("SRA Binary Agreement with Human Shoulder Labels")
    ax.set_xlabel("")
    ax.set_ylim(0, 1)
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def plot_sra_by_human_votes(df: pd.DataFrame, output_dir: Path) -> Path:
    path = output_dir / "sra_shoulders_by_human_shoulder_votes.png"
    plot_df = df.sort_values("human shoulder votes")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(plot_df["human shoulder votes"].astype(str), plot_df["SRA shoulder rate"], color="#52796f")
    ax.set_title("SRA Shoulder Calls vs Human Shoulder Votes")
    ax.set_xlabel("Number of human classifiers calling Peak+Sh")
    ax.set_ylabel("Fraction called Shoulders by SRA")
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(lambda x, pos: f"{100 * x:.0f}%")
    for x, (_, row) in enumerate(plot_df.iterrows()):
        ax.text(x, row["SRA shoulder rate"] + 0.03, f"n={int(row['n'])}", ha="center", va="bottom")
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def plot_sra_by_majority_class(df: pd.DataFrame, output_dir: Path) -> Path:
    path = output_dir / "sra_shoulders_by_human_majority_class.png"
    order = PROFILE_CLASSES
    plot_df = df.set_index("human majority class").reindex(order).dropna(subset=["SRA shoulder rate"])
    colors = ["#2f6f9f" if label == "Peak+Sh" else "#c65d3a" for label in plot_df.index]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(plot_df.index, plot_df["SRA shoulder rate"], color=colors)
    ax.set_title("SRA Shoulder-Call Rate by Human-Majority Profile Class")
    ax.set_xlabel("")
    ax.set_ylabel("Fraction called Shoulders by SRA")
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(lambda x, pos: f"{100 * x:.0f}%")
    ax.tick_params(axis="x", rotation=35)
    for x, (_, row) in enumerate(plot_df.iterrows()):
        ax.text(x, row["SRA shoulder rate"] + 0.03, f"n={int(row['n'])}", ha="center", va="bottom")
    ax.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()
    return path


def analyze(workbook_path: Path, output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_excel(workbook_path, sheet_name="Classifications")

    clean = pd.DataFrame({"galaxy name": df["galaxy name"]})
    for rater, column in HUMAN_LABEL_COLUMNS.items():
        clean[rater] = df[column].map(canonical_profile_label)
    clean["SRA"] = df[SRA_COLUMN].map(canonical_sra_binary)
    clean["SRA raw"] = df[SRA_COLUMN]

    clean["human_unanimous"] = clean[HUMAN_RATERS].nunique(axis=1) == 1
    clean["human_majority_class"] = clean[HUMAN_RATERS].mode(axis=1, dropna=True)[0]
    clean["human_majority_is_unanimous"] = clean["human_unanimous"]
    clean["human_majority_shoulder_binary"] = np.where(clean["human_majority_class"] == "Peak+Sh", "Shoulders", "No Shoulders")
    clean["human_shoulder_votes"] = clean[HUMAN_RATERS].eq("Peak+Sh").sum(axis=1)

    valid_humans = clean[clean[HUMAN_RATERS].isin(PROFILE_CLASSES).all(axis=1)].copy()
    valid_sra = clean[clean["SRA"].isin(["Shoulders", "No Shoulders"])].copy()
    valid_all = valid_humans[valid_humans["SRA"].isin(["Shoulders", "No Shoulders"])].copy()

    class_counts = []
    for rater in HUMAN_RATERS:
        counts = clean[rater].value_counts(dropna=False)
        for label, count in counts.items():
            class_counts.append({"rater": rater, "class": label, "count": int(count)})
    class_counts_df = pd.DataFrame(class_counts)

    pair_rows = []
    kappa_matrix = pd.DataFrame(index=HUMAN_RATERS, columns=HUMAN_RATERS, dtype=float)
    agreement_matrix = pd.DataFrame(index=HUMAN_RATERS, columns=HUMAN_RATERS, dtype=float)
    for left in HUMAN_RATERS:
        for right in HUMAN_RATERS:
            pair_valid = clean[clean[[left, right]].isin(PROFILE_CLASSES).all(axis=1)]
            exact = float((pair_valid[left] == pair_valid[right]).mean())
            kappa = cohen_kappa(pair_valid[left], pair_valid[right], PROFILE_CLASSES)
            kappa_matrix.loc[left, right] = kappa
            agreement_matrix.loc[left, right] = exact
            if left < right:
                pair_rows.append({"pair": f"{left} vs {right}", "n": len(pair_valid), "exact agreement": exact, "cohen kappa": kappa})
    pairwise_df = pd.DataFrame(pair_rows)

    class_agreement_rows = []
    for label in PROFILE_CLASSES:
        subset = valid_humans[valid_humans["GB"] == label]
        class_agreement_rows.append(
            {
                "GB class": label,
                "n": len(subset),
                "PE matches GB": float((subset["PE"] == subset["GB"]).mean()),
                "VPD matches GB": float((subset["VPD"] == subset["GB"]).mean()),
                "PE and VPD both match GB": float(((subset["PE"] == subset["GB"]) & (subset["VPD"] == subset["GB"])).mean()),
                "PE/VPD agree with each other": float((subset["PE"] == subset["VPD"]).mean()),
            }
        )
    class_agreement_df = pd.DataFrame(class_agreement_rows)

    contingency = np.array(
        [
            [
                int(((valid_humans["GB"] == label) & valid_humans["human_unanimous"]).sum()),
                int(((valid_humans["GB"] == label) & ~valid_humans["human_unanimous"]).sum()),
            ]
            for label in PROFILE_CLASSES
        ]
    )
    chi2, chi_p, chi_dof, _ = chi2_contingency(contingency)

    class_binary_rows = []
    for label in PROFILE_CLASSES:
        for left, right in [("PE", "VPD"), ("PE", "GB"), ("VPD", "GB")]:
            pair_valid = clean[clean[[left, right]].isin(PROFILE_CLASSES).all(axis=1)]
            y_left = np.where(pair_valid[left] == label, label, f"not {label}")
            y_right = np.where(pair_valid[right] == label, label, f"not {label}")
            labels = [label, f"not {label}"]
            class_binary_rows.append(
                {
                    "class": label,
                    "pair": f"{left} vs {right}",
                    "n": len(pair_valid),
                    "one-vs-rest agreement": float((y_left == y_right).mean()),
                    "one-vs-rest kappa": cohen_kappa(pd.Series(y_left), pd.Series(y_right), labels),
                }
            )
    class_binary_df = pd.DataFrame(class_binary_rows)

    sra_rows = []
    for reference in HUMAN_RATERS + ["Human majority"]:
        if reference == "Human majority":
            tmp = valid_all.copy()
            human_binary = tmp["human_majority_shoulder_binary"]
        else:
            tmp = valid_sra[valid_sra[reference].isin(PROFILE_CLASSES)].copy()
            human_binary = np.where(tmp[reference] == "Peak+Sh", "Shoulders", "No Shoulders")
        metrics = binary_metrics(pd.Series(human_binary, index=tmp.index), tmp["SRA"])
        sra_rows.append({"reference": reference, **metrics})
    sra_metrics_df = pd.DataFrame(sra_rows)

    majority_confusion = pd.crosstab(
        pd.Categorical(valid_all["human_majority_shoulder_binary"], categories=["Shoulders", "No Shoulders"]),
        pd.Categorical(valid_all["SRA"], categories=["Shoulders", "No Shoulders"]),
        rownames=["Human majority"],
        colnames=["SRA"],
        dropna=False,
    )

    sra_vote_rows = []
    for votes in range(4):
        subset = valid_all[valid_all["human_shoulder_votes"] == votes]
        sra_shoulders = int((subset["SRA"] == "Shoulders").sum())
        sra_vote_rows.append(
            {
                "human shoulder votes": votes,
                "n": len(subset),
                "SRA Shoulders": sra_shoulders,
                "SRA No Shoulders": int((subset["SRA"] == "No Shoulders").sum()),
                "SRA shoulder rate": sra_shoulders / len(subset) if len(subset) else math.nan,
            }
        )
    sra_by_votes_df = pd.DataFrame(sra_vote_rows)

    sra_majority_rows = []
    for label in PROFILE_CLASSES:
        subset = valid_all[valid_all["human_majority_class"] == label]
        sra_shoulders = int((subset["SRA"] == "Shoulders").sum())
        expected_sra = "Shoulders" if label == "Peak+Sh" else "No Shoulders"
        disagreement = int((subset["SRA"] != expected_sra).sum())
        sra_majority_rows.append(
            {
                "human majority class": label,
                "human binary expectation": expected_sra,
                "n": len(subset),
                "SRA Shoulders": sra_shoulders,
                "SRA No Shoulders": int((subset["SRA"] == "No Shoulders").sum()),
                "SRA shoulder rate": sra_shoulders / len(subset) if len(subset) else math.nan,
                "SRA disagreement count": disagreement,
                "SRA disagreement rate": disagreement / len(subset) if len(subset) else math.nan,
            }
        )
    sra_by_majority_class_df = pd.DataFrame(sra_majority_rows)

    disagreement_cases = valid_all[valid_all["SRA"] != valid_all["human_majority_shoulder_binary"]].copy()
    disagreement_cases["SRA disagreement type"] = np.where(
        disagreement_cases["SRA"].eq("Shoulders"),
        "SRA false positive vs human majority",
        "SRA false negative vs human majority",
    )
    disagreement_cases = disagreement_cases[
        [
            "galaxy name",
            "PE",
            "VPD",
            "GB",
            "human_shoulder_votes",
            "human_majority_class",
            "human_majority_shoulder_binary",
            "SRA",
            "SRA raw",
            "SRA disagreement type",
        ]
    ].sort_values(["SRA disagreement type", "human_majority_class", "galaxy name"])

    clean_path = write_csv(clean, output_dir, "cleaned_classifier_labels.csv")
    write_csv(class_counts_df, output_dir, "human_class_counts.csv")
    write_csv(pairwise_df, output_dir, "human_pairwise_agreement.csv")
    write_csv(class_agreement_df, output_dir, "human_agreement_by_gb_class.csv")
    write_csv(class_binary_df, output_dir, "human_class_specific_one_vs_rest_agreement.csv")
    write_csv(sra_metrics_df, output_dir, "sra_binary_agreement_metrics.csv")
    write_csv(sra_by_votes_df, output_dir, "sra_by_human_shoulder_votes.csv")
    write_csv(sra_by_majority_class_df, output_dir, "sra_by_human_majority_class.csv")
    write_csv(disagreement_cases, output_dir, "sra_disagreement_cases.csv")
    majority_confusion.to_csv(output_dir / "sra_vs_human_majority_confusion.csv")

    figures = {
        "human_class_distribution": plot_class_distribution(class_counts_df, output_dir),
        "human_kappa_heatmap": plot_heatmap(kappa_matrix.astype(float), "Human Pairwise Cohen's Kappa", output_dir / "human_pairwise_kappa_heatmap.png"),
        "human_agreement_by_gb_class": plot_human_agreement_by_class(class_agreement_df, output_dir),
        "sra_majority_confusion": plot_heatmap(
            majority_confusion.astype(float),
            "SRA vs Human Majority Shoulder Label",
            output_dir / "sra_vs_human_majority_confusion.png",
            fmt=".0f",
            xlabel="SRA label",
            ylabel="Human majority label",
        ),
        "sra_binary_metrics": plot_sra_metrics(sra_metrics_df, output_dir),
        "sra_by_human_votes": plot_sra_by_human_votes(sra_by_votes_df, output_dir),
        "sra_by_majority_class": plot_sra_by_majority_class(sra_by_majority_class_df, output_dir),
    }

    report_path = output_dir / "classifier_agreement_report.md"
    write_report(
        report_path,
        workbook_path,
        clean,
        valid_humans,
        valid_sra,
        valid_all,
        pairwise_df,
        class_agreement_df,
        class_binary_df,
        sra_metrics_df,
        sra_by_votes_df,
        sra_by_majority_class_df,
        disagreement_cases,
        majority_confusion,
        chi2,
        chi_p,
        chi_dof,
        figures,
        clean_path,
    )

    return {
        "report": report_path,
        "figures": figures,
        "pairwise": pairwise_df,
        "class_agreement": class_agreement_df,
        "sra_metrics": sra_metrics_df,
        "sra_by_votes": sra_by_votes_df,
        "sra_by_majority_class": sra_by_majority_class_df,
    }


def write_report(
    path: Path,
    workbook_path: Path,
    clean: pd.DataFrame,
    valid_humans: pd.DataFrame,
    valid_sra: pd.DataFrame,
    valid_all: pd.DataFrame,
    pairwise_df: pd.DataFrame,
    class_agreement_df: pd.DataFrame,
    class_binary_df: pd.DataFrame,
    sra_metrics_df: pd.DataFrame,
    sra_by_votes_df: pd.DataFrame,
    sra_by_majority_class_df: pd.DataFrame,
    disagreement_cases: pd.DataFrame,
    majority_confusion: pd.DataFrame,
    chi2: float,
    chi_p: float,
    chi_dof: int,
    figures: dict[str, Path],
    clean_path: Path,
) -> None:
    fleiss = fleiss_kappa(valid_humans[HUMAN_RATERS], PROFILE_CLASSES)
    unanimous_rate = float(valid_humans["human_unanimous"].mean())
    best_class = class_agreement_df.sort_values("PE and VPD both match GB", ascending=False).iloc[0]
    weakest_class = class_agreement_df.sort_values("PE and VPD both match GB", ascending=True).iloc[0]
    sra_majority = sra_metrics_df[sra_metrics_df["reference"] == "Human majority"].iloc[0]
    sra_three_humans = sra_by_votes_df[sra_by_votes_df["human shoulder votes"] == 3].iloc[0]
    sra_zero_humans = sra_by_votes_df[sra_by_votes_df["human shoulder votes"] == 0].iloc[0]
    sra_two_humans = sra_by_votes_df[sra_by_votes_df["human shoulder votes"] == 2].iloc[0]
    sra_one_human = sra_by_votes_df[sra_by_votes_df["human shoulder votes"] == 1].iloc[0]
    false_positive_count = int(((valid_all["human_majority_shoulder_binary"] == "No Shoulders") & (valid_all["SRA"] == "Shoulders")).sum())
    false_negative_count = int(((valid_all["human_majority_shoulder_binary"] == "Shoulders") & (valid_all["SRA"] == "No Shoulders")).sum())
    false_positive_classes = sra_by_majority_class_df[sra_by_majority_class_df["human majority class"] != "Peak+Sh"].sort_values(
        "SRA shoulder rate", ascending=False
    )
    worst_false_positive_class = false_positive_classes.iloc[0]

    lines = [
        "# Classifier Agreement Analysis",
        "",
        f"Source workbook: `{workbook_path}`",
        f"Rows in source sheet: {len(clean)}",
        f"Rows with valid 4-class human labels: {len(valid_humans)}",
        f"Rows with usable binary SRA labels: {len(valid_sra)}",
        f"Rows with both valid human labels and usable binary SRA labels: {len(valid_all)}",
        "",
        "## Executive Summary",
        "",
        f"- Human unanimous agreement across PE, VPD, and GB is {percent(unanimous_rate)} on the {len(valid_humans)} galaxies with valid 4-class human labels.",
        f"- Fleiss' kappa for the three human classifiers is {fleiss:.3f}, a chance-corrected measure of multi-rater agreement.",
        f"- Pairwise human agreement is strongest for {pairwise_df.sort_values('cohen kappa', ascending=False).iloc[0]['pair']} (kappa {pairwise_df.sort_values('cohen kappa', ascending=False).iloc[0]['cohen kappa']:.3f}) and weakest for {pairwise_df.sort_values('cohen kappa').iloc[0]['pair']} (kappa {pairwise_df.sort_values('cohen kappa').iloc[0]['cohen kappa']:.3f}).",
        f"- Using GB visual class as the row grouping, PE and VPD both match GB most often for `{best_class['GB class']}` ({percent(best_class['PE and VPD both match GB'])}) and least often for `{weakest_class['GB class']}` ({percent(weakest_class['PE and VPD both match GB'])}).",
        f"- The class-dependence of unanimous human agreement is tested with chi-square: chi2={chi2:.2f}, dof={chi_dof}, p={chi_p:.4g}.",
        f"- Against the human-majority shoulder/non-shoulder label, SRA has accuracy {percent(sra_majority['accuracy'])}, balanced accuracy {percent(sra_majority['balanced_accuracy'])}, sensitivity for shoulders {percent(sra_majority['sensitivity_shoulders'])}, specificity for no-shoulders {percent(sra_majority['specificity_no_shoulders'])}, and kappa {sra_majority['kappa']:.3f}.",
        f"- For shoulder detection specifically, SRA is more sensitive than conservative: it misses {false_negative_count} human-majority shoulder galaxies, but calls shoulders in {false_positive_count} human-majority non-shoulder galaxies.",
        f"- When all three humans identify shoulders, SRA calls shoulders in {percent(sra_three_humans['SRA shoulder rate'])}; when no humans identify shoulders, SRA still calls shoulders in {percent(sra_zero_humans['SRA shoulder rate'])}.",
        f"- Among non-shoulder human-majority classes, SRA shoulder calls are most frequent for `{worst_false_positive_class['human majority class']}` ({percent(worst_false_positive_class['SRA shoulder rate'])}).",
        "",
        "## Label Handling",
        "",
        "- Human agreement uses PE profile label, VPD profile label, and GB visual class.",
        "- Human profile classes are canonicalized to Peak+Sh, Exp, Flat-top (FT), and Two-slope (2S).",
        "- GB rows marked Unclear are retained in the cleaned-label CSV but excluded from the 4-class human-agreement statistics.",
        "- SRA is treated as binary: Shoulders vs No Shoulders. SRA rows marked Too Noisy are excluded from binary SRA agreement metrics.",
        f"- Cleaned labels are written to `{clean_path.name}`.",
        "",
        "## Human Pairwise Agreement",
        "",
        markdown_table(pairwise_df, floatfmt=".3f"),
        "",
        "## Human Agreement by GB Class",
        "",
        markdown_table(class_agreement_df, floatfmt=".3f"),
        "",
        "## Class-Specific One-vs-Rest Agreement",
        "",
        markdown_table(class_binary_df.pivot(index="class", columns="pair", values="one-vs-rest kappa").reset_index(), floatfmt=".3f"),
        "",
        "## SRA Binary Agreement",
        "",
        markdown_table(sra_metrics_df, floatfmt=".3f"),
        "",
        "## SRA Shoulder Identification",
        "",
        "This section treats the humans as shoulder detectors by mapping `Peak+Sh` to `Shoulders` and all other profile classes to `No Shoulders`. The strongest reference is the human-majority binary label.",
        "",
        f"- Human-majority comparison: TP={int(sra_majority['tp'])}, FN={int(sra_majority['fn'])}, FP={int(sra_majority['fp'])}, TN={int(sra_majority['tn'])}.",
        f"- Sensitivity to human-majority shoulders is {percent(sra_majority['sensitivity_shoulders'])}; specificity to human-majority non-shoulders is {percent(sra_majority['specificity_no_shoulders'])}.",
        f"- The asymmetry is important: SRA catches most human-majority shoulder cases, but the price is {false_positive_count} shoulder calls among human-majority non-shoulders.",
        f"- For borderline human cases, SRA shoulder-call rate is {percent(sra_two_humans['SRA shoulder rate'])} when two humans vote shoulders and {percent(sra_one_human['SRA shoulder rate'])} when one human votes shoulders.",
        "",
        "### SRA by Number of Human Shoulder Votes",
        "",
        markdown_table(sra_by_votes_df, floatfmt=".3f"),
        "",
        "### SRA by Human-Majority Profile Class",
        "",
        markdown_table(sra_by_majority_class_df, floatfmt=".3f"),
        "",
        "### SRA Disagreement Cases",
        "",
        f"The full list of {len(disagreement_cases)} SRA-vs-human-majority disagreement cases is written to `sra_disagreement_cases.csv`.",
        "",
        "### SRA vs Human Majority Confusion Matrix",
        "",
        markdown_table(majority_confusion.reset_index(), floatfmt=".0f"),
        "",
        "## Figures",
        "",
    ]
    for name, figure_path in figures.items():
        lines.append(f"- {name}: `{figure_path.name}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze PE/VPD/GB human agreement and compare SRA shoulder detections.")
    parser.add_argument(
        "--pc",
        choices=sorted(PC_RESEARCH_FOLDERS),
        default=DEFAULT_PC,
        help="Select which Dropbox research-folder location to use for default paths.",
    )
    parser.add_argument("--workbook", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    if args.workbook is None:
        args.workbook = shoulder_folder(args.pc) / WORKBOOK_NAME
    return args


def main() -> int:
    args = parse_args()
    if not args.workbook.exists():
        raise FileNotFoundError(f"Workbook not found: {args.workbook}")
    result = analyze(args.workbook, args.output_dir)
    print(f"Report written to: {result['report']}")
    print(f"Output folder: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
