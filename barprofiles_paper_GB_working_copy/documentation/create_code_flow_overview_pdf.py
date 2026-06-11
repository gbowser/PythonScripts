"""Codex-created generator for the bar-profiles code-flow overview PDF."""

from __future__ import annotations

from pathlib import Path
from textwrap import wrap

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch


OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_PDF = OUTPUT_DIR / "barprofiles_code_flow_overview.pdf"


COLORS = {
    "title": "#203040",
    "subtitle": "#56616b",
    "blue": "#dceaf7",
    "green": "#dff1e3",
    "yellow": "#fff2cc",
    "red": "#f9dddd",
    "grey": "#edf0f2",
    "line": "#59636d",
}


def new_page(title: str, subtitle: str | None = None):
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.06, 0.94, title, fontsize=22, weight="bold", color=COLORS["title"], va="top")
    if subtitle:
        ax.text(0.06, 0.895, subtitle, fontsize=10.5, color=COLORS["subtitle"], va="top")
    return fig, ax


def paragraph(ax, x: float, y: float, text: str, width_chars: int = 95, size: float = 10.5, color: str = "#222"):
    wrapped = "\n".join(wrap(text, width=width_chars, break_long_words=False))
    ax.text(x, y, wrapped, fontsize=size, color=color, va="top", linespacing=1.35)


def wrap_lines(text: str, width: int) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line:
            lines.append("")
        else:
            lines.extend(wrap(raw_line, width=width, break_long_words=False))
    return "\n".join(lines)


def box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body: str,
    fill: str,
    title_size: float = 11,
    body_size: float = 8.8,
):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.015",
        linewidth=1.0,
        edgecolor="#8a949e",
        facecolor=fill,
    )
    ax.add_patch(patch)
    ax.text(x + 0.018, y + h - 0.026, title, fontsize=title_size, weight="bold", va="top", color="#1d2730")
    wrapped = wrap_lines(body, width=max(20, int(w * 92)))
    ax.text(x + 0.018, y + h - 0.065, wrapped, fontsize=body_size, va="top", color="#26323b", linespacing=1.25)


def arrow(ax, start: tuple[float, float], end: tuple[float, float]):
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(arrowstyle="->", lw=1.5, color=COLORS["line"], shrinkA=4, shrinkB=4),
    )


def bullet_list(ax, x: float, y: float, items: list[str], size: float = 9.3, gap: float = 0.045):
    for i, item in enumerate(items):
        ax.text(x, y - i * gap, f"- {item}", fontsize=size, color="#222", va="top", linespacing=1.25)


def page_overview(pdf: PdfPages):
    fig, ax = new_page(
        "Bar Profiles Code Flow Overview",
        "High-level map of the inputs, scripts, helper functions, and generated outputs.",
    )
    paragraph(
        ax,
        0.06,
        0.82,
        "The repository now has three related workflows: image download and geometry linking, "
        "isophote/profile plotting, and paper-figure reproduction from catalogue tables.",
        width_chars=105,
        size=11,
    )

    box(
        ax,
        0.07,
        0.50,
        0.25,
        0.20,
        "1. Images + Geometry",
        "Download S4G FITS images.\n\nBuild a manifest linking images to geometry fields.",
        COLORS["blue"],
        body_size=8.3,
    )
    box(
        ax,
        0.38,
        0.50,
        0.25,
        0.20,
        "2. Isophote Plots",
        "Open each FITS image.\n\nDraw isophotes and bar axes, then extract bar-major and bar-minor profiles.",
        COLORS["green"],
        body_size=8.3,
    )
    box(
        ax,
        0.69,
        0.50,
        0.25,
        0.20,
        "3. Paper Figures",
        "Use catalogue tables, sample lists, and PE/VPD classifications.\n\nReproduce histogram and logistic-frequency figures.",
        COLORS["yellow"],
        body_size=8.3,
    )
    arrow(ax, (0.32, 0.60), (0.38, 0.60))
    arrow(ax, (0.63, 0.60), (0.69, 0.60))

    ax.text(0.06, 0.38, "Key distinction", fontsize=14, weight="bold", color=COLORS["title"])
    bullet_list(
        ax,
        0.08,
        0.33,
        [
            "Image plots are derived from FITS images plus geometry.",
            "Figures 6, 9, 10, and 11 are reproduced from catalogue tables and human classifications.",
            "PE and VPD profile classes are not calculated by the code; they are read from classification files.",
        ],
        size=10.2,
        gap=0.055,
    )

    ax.text(0.06, 0.15, f"Output PDF: {OUTPUT_PDF.name}", fontsize=9, color=COLORS["subtitle"])
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_images_geometry(pdf: PdfPages):
    fig, ax = new_page("Workflow 1: S4G Images And Geometry")

    box(
        ax,
        0.06,
        0.70,
        0.26,
        0.17,
        "Input: galaxy list",
        "scrambled_map.txt\n\nIdentifies the 182 galaxies to download.",
        COLORS["grey"],
    )
    box(
        ax,
        0.39,
        0.70,
        0.26,
        0.17,
        "download script",
        "read_galaxy_names()\ndownload_image()\nmain()",
        COLORS["blue"],
    )
    box(
        ax,
        0.72,
        0.70,
        0.22,
        0.17,
        "Output: FITS images",
        "s4g_images_36um/*.fits",
        COLORS["green"],
    )
    arrow(ax, (0.32, 0.785), (0.39, 0.785))
    arrow(ax, (0.65, 0.785), (0.72, 0.785))

    box(
        ax,
        0.06,
        0.43,
        0.26,
        0.18,
        "Input: catalogue fields",
        "s4gbars_table.dat\nFITS images\n\nProvides centre, PA, inc., and bar radius.",
        COLORS["grey"],
    )
    box(
        ax,
        0.39,
        0.43,
        0.26,
        0.18,
        "geometry manifest script",
        "read_scrambled_map()\nread_s4g_table()\nfind_image_file()\nbuild_manifest_rows()\nmain()",
        COLORS["blue"],
        title_size=10.3,
    )
    box(
        ax,
        0.72,
        0.43,
        0.22,
        0.18,
        "Output: manifest CSV",
        "geometry_output/\nmanifest CSV",
        COLORS["green"],
    )
    arrow(ax, (0.32, 0.52), (0.39, 0.52))
    arrow(ax, (0.65, 0.52), (0.72, 0.52))

    paragraph(
        ax,
        0.06,
        0.28,
        "The manifest is the bridge between catalogue data and image data. Later plotting code does not need to "
        "re-query catalogues; it reads one row per galaxy from this CSV and follows the linked FITS file path.",
        width_chars=110,
        size=10.5,
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_isophote_plots(pdf: PdfPages):
    fig, ax = new_page("Workflow 2: Isophote And Profile Plotting")

    box(
        ax,
        0.06,
        0.66,
        0.25,
        0.20,
        "Inputs",
        "geometry manifest CSV\n\ns4g_images_36um/*.fits",
        COLORS["grey"],
    )
    box(
        ax,
        0.38,
        0.66,
        0.27,
        0.20,
        "isophote plotting script",
        "read_manifest()\nselected_rows()\nload_fits_image()\nobserved_bar_minor_pa()\nsample_profile()\nmake_plot()\nmain()",
        COLORS["blue"],
        title_size=10.3,
        body_size=8.2,
    )
    box(
        ax,
        0.72,
        0.66,
        0.22,
        0.20,
        "Outputs",
        "isophote_output/*.pdf\n\nCombined PDF and/or individual galaxy PDFs.",
        COLORS["green"],
    )
    arrow(ax, (0.31, 0.76), (0.38, 0.76))
    arrow(ax, (0.65, 0.76), (0.72, 0.76))

    ax.text(0.06, 0.51, "What the plotting code does", fontsize=14, weight="bold", color=COLORS["title"])
    bullet_list(
        ax,
        0.08,
        0.46,
        [
            "Loads image pixels from the FITS file linked in the manifest.",
            "Uses catalogue geometry to place the galaxy centre, bar major axis, and projected bar minor axis.",
            "Draws isophote contours so the image structure can be inspected visually.",
            "Samples light profiles along the bar-major and bar-minor directions.",
            "Writes visual diagnostic PDFs; it does not create PE/VPD classifications.",
        ],
        size=9.8,
        gap=0.052,
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def page_paper_figures(pdf: PdfPages):
    fig, ax = new_page("Workflow 3: Paper Figure Reproduction")

    box(
        ax,
        0.05,
        0.68,
        0.27,
        0.20,
        "Input data files",
        "s4gbars_table.dat\nscrambled_map.txt\nclassifications_pe.txt\nclassifications_vd_revised.txt\ns4g_faceon_names.dat\nB/P checklist file",
        COLORS["grey"],
        body_size=8.0,
    )
    box(
        ax,
        0.38,
        0.68,
        0.27,
        0.20,
        "Figure 6 script",
        "reproduce_figure6_histograms.py\n\nget_names()\nbuild_stellar_mass_dict()\nget_classification_values()\nplot_panel()\nwrite_counts_csv()",
        COLORS["yellow"],
        body_size=7.5,
    )
    box(
        ax,
        0.72,
        0.68,
        0.22,
        0.20,
        "Figure 6 outputs",
        "figure6 histogram PDF/PNG\n\nfigure6 counts CSV",
        COLORS["green"],
        body_size=8.0,
    )
    arrow(ax, (0.32, 0.78), (0.38, 0.78))
    arrow(ax, (0.65, 0.78), (0.72, 0.78))

    box(
        ax,
        0.38,
        0.38,
        0.27,
        0.20,
        "Figures 9-11 script",
        "reproduce_figures9_10_11.py\n\nfrequency_rows()\nplot_frequency()\nwrite_frequency_csv()\nwrite_coefficients_csv()",
        COLORS["yellow"],
        body_size=7.8,
    )
    box(
        ax,
        0.72,
        0.38,
        0.22,
        0.20,
        "Figures 9-11 outputs",
        "figures9-11 PDF/PNG\n\nfrequency bins CSV\nlogistic coefficients CSV",
        COLORS["green"],
        body_size=8.0,
    )
    arrow(ax, (0.32, 0.48), (0.38, 0.48))
    arrow(ax, (0.65, 0.48), (0.72, 0.48))

    box(
        ax,
        0.05,
        0.11,
        0.89,
        0.17,
        "Important limitation",
        "Figures 6, 9, 10, and 11 are not measured from the downloaded images alone. "
        "They depend on catalogue values such as logMstar and V_rot, plus human classifications "
        "such as PE/VPD profile classes and B/P morphology. The statistical figures reproduce "
        "the paper's tabulated inputs.",
        COLORS["red"],
        body_size=8.5,
    )

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    with PdfPages(OUTPUT_PDF) as pdf:
        page_overview(pdf)
        page_images_geometry(pdf)
        page_isophote_plots(pdf)
        page_paper_figures(pdf)
    print(f"Wrote {OUTPUT_PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
