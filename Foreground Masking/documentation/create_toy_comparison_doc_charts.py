from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(args.metrics)

    colors = {"SEP": "#1f77b4", "MTObjects": "#2e8b57"}
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.3), constrained_layout=True)
    recovery_labels = ["Toy-pixel\nrecall", "Toy detection\nrate", "Mean per-toy\nrecall"]
    sep_recovery = 100 * np.array([
        data.sep_toy_pixel_recall.mean(),
        data.sep_toy_detection_rate.mean(),
        data.sep_mean_per_toy_recall.mean(),
    ])
    mto_recovery = 100 * np.array([
        data.mto_toy_pixel_recall.mean(),
        data.mto_toy_detection_rate.mean(),
        data.mto_mean_per_toy_recall.mean(),
    ])
    x = np.arange(len(recovery_labels)); width = 0.36
    axes[0].bar(x - width / 2, sep_recovery, width, label="SEP", color=colors["SEP"])
    axes[0].bar(x + width / 2, mto_recovery, width, label="MTObjects", color=colors["MTObjects"])
    axes[0].set_xticks(x, recovery_labels); axes[0].set_ylim(0, 100); axes[0].set_ylabel("Mean across 182 galaxies [%]")
    axes[0].set_title("Toy recovery performance", fontweight="bold")
    axes[0].legend(frameon=False)
    for container in axes[0].containers:
        axes[0].bar_label(container, fmt="%.1f", padding=3, fontsize=9)

    other_labels = ["Masked image\narea", "Toy-associated\nprecision", "Toy F1"]
    sep_other = 100 * np.array([
        data.sep_masked_fraction.mean(),
        data.sep_toy_associated_precision.mean(),
        data.sep_toy_f_score.mean(),
    ])
    mto_other = 100 * np.array([
        data.mto_masked_fraction.mean(),
        data.mto_toy_associated_precision.mean(),
        data.mto_toy_f_score.mean(),
    ])
    x = np.arange(len(other_labels))
    axes[1].bar(x - width / 2, sep_other, width, color=colors["SEP"])
    axes[1].bar(x + width / 2, mto_other, width, color=colors["MTObjects"])
    axes[1].set_xticks(x, other_labels); axes[1].set_ylabel("Mean across 182 galaxies [%]")
    axes[1].set_title("Mask extent and overlap quality", fontweight="bold")
    for container in axes[1].containers:
        axes[1].bar_label(container, fmt="%.2f", padding=3, fontsize=9)
    for ax in axes:
        ax.grid(axis="y", alpha=0.25); ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(args.output_dir / "toy_comparison_headline_metrics.png", dpi=180, facecolor="white")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), constrained_layout=True)
    plots = [
        ("mto_toy_pixel_recall", "sep_toy_pixel_recall", "Toy-pixel recall", (0, 1)),
        ("mto_masked_fraction", "sep_masked_fraction", "Masked image fraction", (0, 0.35)),
    ]
    for ax, (xcol, ycol, title, limits) in zip(axes, plots):
        ax.scatter(data[xcol], data[ycol], s=24, alpha=0.65, color="#34495e", edgecolors="none")
        ax.plot(limits, limits, "--", color="#b22222", linewidth=1.4, label="Equal performance")
        ax.set_xlim(limits); ax.set_ylim(limits); ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("MTObjects"); ax.set_ylabel("SEP"); ax.set_title(title, fontweight="bold")
        ax.grid(alpha=0.2); ax.legend(frameon=False, loc="upper left")
    fig.savefig(args.output_dir / "toy_comparison_paired_scatter.png", dpi=180, facecolor="white")
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
