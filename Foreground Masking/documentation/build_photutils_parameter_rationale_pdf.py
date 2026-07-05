from __future__ import annotations

import textwrap
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


DOC_DIR = Path(__file__).resolve().parent
OUTPUT_PDF = DOC_DIR / "Photutils Parameter Rationale.pdf"
DROPBOX_DIR = Path(
    r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\documentation"
)


def wrapped(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def draw_header(ax, title: str) -> None:
    ax.text(0.05, 0.965, title, fontsize=17, fontweight="bold", color="#1F4D78", va="top")
    ax.text(0.05, 0.928, f"Generated {date.today().isoformat()}", fontsize=8.5, color="0.35", va="top")
    ax.plot([0.05, 0.95], [0.905, 0.905], color="#D9E2F3", linewidth=1.2)


def add_paragraph(ax, y: float, text: str, *, width: int = 122, size: float = 8.7) -> float:
    body = wrapped(text, width)
    ax.text(0.05, y, body, fontsize=size, va="top", linespacing=1.25)
    return y - 0.022 * (body.count("\n") + 1) - 0.012


def add_table(ax, y: float, rows: list[tuple[str, str]]) -> float:
    row_heights = []
    wrapped_rows = []
    for left, right in rows:
        left_text = wrapped(left, 26)
        right_text = wrapped(right, 78)
        lines = max(left_text.count("\n") + 1, right_text.count("\n") + 1)
        row_heights.append(0.032 + 0.020 * lines)
        wrapped_rows.append((left_text, right_text))

    x0, x1, x2 = 0.05, 0.31, 0.95
    for idx, ((left, right), height) in enumerate(zip(wrapped_rows, row_heights)):
        y_next = y - height
        fill = "#E8EEF5" if idx == 0 else ("#F2F4F7" if idx % 2 else "white")
        ax.add_patch(
            plt.Rectangle((x0, y_next), x2 - x0, height, facecolor=fill, edgecolor="0.55", linewidth=0.45)
        )
        ax.plot([x1, x1], [y_next, y], color="0.55", linewidth=0.45)
        weight = "bold" if idx == 0 else "normal"
        color = "#1F4D78" if idx == 0 else "black"
        ax.text(x0 + 0.008, y - 0.012, left, fontsize=7.6, va="top", fontweight=weight, color=color)
        ax.text(x1 + 0.008, y - 0.012, right, fontsize=7.6, va="top", fontweight=weight, color=color)
        y = y_next
    return y - 0.02


def build() -> Path:
    OUTPUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(OUTPUT_PDF) as pdf:
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.set_axis_off()
        draw_header(ax, "Photutils Parameter Rationale")
        y = 0.875
        y = add_paragraph(
            ax,
            y,
            "The current spike-gated pipeline is deliberately conservative. Photutils finds compact bright residual-source candidates, "
            "but the bar-major intensity profile spike gate decides whether those candidates are allowed to affect the science profile.",
        )
        y = add_paragraph(
            ax,
            y,
            "The aim is to remove foreground-object contamination that causes narrow bar-profile spikes while preserving bar, ring, "
            "spiral-arm, nuclear, ansa, and shoulder structure. Earlier global Photutils runs showed that aggressive parameters can "
            "remove large amounts of valid galaxy light.",
        )
        ax.text(0.05, y, "Current Parameter Interpretation", fontsize=11.5, fontweight="bold", color="#1F4D78", va="top")
        y -= 0.026
        rows = [
            ("Parameter", "Role and rationale"),
            ("Masking model: spike-gated", "Main protection layer. Photutils detections are candidates only; final masking requires intersection with detected bar-major profile spike samples."),
            ("Residual image", "Photutils runs on science image minus a Gaussian-smoothed galaxy model, so compact sources stand out while broad galaxy light is suppressed."),
            ("Detection threshold", "Brightness threshold in residual-sigma units. Lower values detect fainter objects but risk over-masking. Higher values are safer but can miss weaker foreground objects."),
            ("Smooth sigma: 15 px", "Controls the broad galaxy model. Too small can absorb compact objects into the model or create galaxy-structure residuals; too large can leave broad gradients."),
            ("Connected-pixel minimum: 8 px", "Rejects single-pixel noise and tiny artifacts. Lower values catch smaller sources but increase false positives."),
            ("Dilation radius: 3 px", "Grows retained masks to include source wings. Larger values remove more foreground light but damage nearby galaxy data more quickly."),
            ("Max segment area: 500 px", "Rejects large residual patches that are often galaxy arms, rings, or background structure rather than compact foreground objects."),
            ("Max elongation: 6", "Rejects stretched segments, protecting against spiral arms, bars, streaks, and diffuse residuals."),
        ]
        add_table(ax, y, rows)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.set_axis_off()
        draw_header(ax, "Photutils Parameter Rationale")
        y = 0.875
        rows = [
            ("Parameter", "Role and rationale"),
            ("Central exclusion radius: 12 px", "Protects the nucleus and nuclear rings, which are easy for residual-source detection to mistake for contaminants."),
            ("Profile width: 3 px", "A narrow profile strip preserves local spikes while reducing single-pixel noise."),
            ("Bridge merge gap: 12 samples", "Merges nearby masked profile gaps before straight log-linear interpolation. Too large can bridge valid data."),
        ]
        y = add_table(ax, y, rows)
        ax.text(0.05, y, "Optimisation Strategy", fontsize=11.5, fontweight="bold", color="#1F4D78", va="top")
        y -= 0.032
        for item in [
            "Keep spike-gated mode as the safe science product for shoulder-recognition profiles.",
            "Optimise global Photutils masking separately, because it is trying to solve a broader image-cleaning problem.",
            "Use positive spike galaxies and no-spike control galaxies together; a parameter set must remove real spikes without changing clean profiles.",
            "Track masked segment count, masked pixel fraction, affected bar-profile samples, and profile-shape change.",
            "Tune detection_nsigma, dilation radius, max area, and smooth sigma first; npixels, max elongation, and central exclusion are secondary controls.",
            "Expect global Photutils masking to need stricter parameters than spike-gated masking, because it lacks the profile gate.",
        ]:
            y = add_paragraph(ax, y, f"- {item}", width=118)

        ax.text(0.05, y, "Practical Recommendation", fontsize=11.5, fontweight="bold", color="#1F4D78", va="top")
        y -= 0.032
        y = add_paragraph(
            ax,
            y,
            "For the production spike-gated run, 3.5 sigma can be acceptable because only segments that coincide with profile spikes are applied. "
            "For global Photutils runs, 3.5 sigma is expected to be aggressive and should be treated as a diagnostic comparison rather than a final science mask.",
        )
        add_paragraph(
            ax,
            y,
            "The proposed optimiser should score candidate parameter sets in tiers: first identify spike-positive performance, then penalise damage to no-spike controls, "
            "then inspect the best few parameter sets visually before processing the full sample.",
        )
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    DROPBOX_DIR.mkdir(parents=True, exist_ok=True)
    (DROPBOX_DIR / OUTPUT_PDF.name).write_bytes(OUTPUT_PDF.read_bytes())
    return OUTPUT_PDF


if __name__ == "__main__":
    print(build())
