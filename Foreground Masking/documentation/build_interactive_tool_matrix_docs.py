#!/usr/bin/env python3
"""Build the DOCX reference for canonical optimisation, interactive, and batch tools."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt


OUT_PATHS = [
    Path(__file__).resolve().parent / "Foreground Masking Canonical Tools Reference.docx",
    Path(__file__).resolve().parent / "Foreground Masking Interactive Tools Matrix.docx",
]


COMBINATIONS = [
    ("SEP", "spike_gate"),
    ("SEP", "toy_objects"),
    ("MTObjects", "spike_gate"),
    ("MTObjects", "toy_objects"),
]


def style_document(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)
    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(10)
    for style_name in ["Heading 1", "Heading 2"]:
        style = doc.styles[style_name]
        style.font.name = "Arial"
        style.font.bold = True


def add_code(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(9)


def main() -> None:
    doc = Document()
    style_document(doc)
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Foreground Masking Canonical Tools Reference")
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(18)
    subtitle = doc.add_paragraph(f"Updated {date.today().isoformat()}")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph(
        "The maintained tools form a three-by-four set: optimise, interactive, and batch entry points for SEP and "
        "MTObjects with Spike Gate and Toy Objects. Each launcher auto-detects Laptop or Desktop from the configured "
        "hostname, with the code drive as a fallback. --pc remains available as an explicit override."
    )

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    headers = ["Engine", "Method", "Role", "Canonical filename"]
    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True

    for engine, method in COMBINATIONS:
        for role in ("optimise", "interactive", "batch"):
            cells = table.add_row().cells
            values = [engine, method.replace("_", " ").title(), role.title(), f"{role}_{method}_{engine}.py"]
            for cell, value in zip(cells, values):
                cell.text = value

    doc.add_heading("Launch Commands", level=1)
    add_code(doc, 'python "Foreground Masking\\optimise_spike_gate_SEP.py"')
    add_code(doc, 'python "Foreground Masking\\interactive_spike_gate_SEP.py"')
    add_code(doc, 'python "Foreground Masking\\batch_spike_gate_SEP.py"')

    doc.add_heading("Parameter hand-off", level=1)
    doc.add_paragraph(
        "Every optimiser writes its best parameter dictionary to a method-specific JSON file in its timestamped "
        "output directory. The matching canonical interactive and batch launchers automatically locate and load the "
        "newest JSON for the detected device. Pass --best-json (or --params-json where supported) to override it."
    )

    doc.add_heading("Device detection", level=1)
    doc.add_paragraph(
        "The configured hostname selects the matching research tree; the drive containing the running code is used "
        "as a fallback. Set FOREGROUND_MASKING_PC to Laptop or Desktop, or pass --pc, when an explicit override is needed."
    )

    doc.add_heading("Support-code folders", level=1)
    doc.add_paragraph(
        "Only the twelve canonical launchers are kept in the Foreground Masking root. Supporting programs are grouped "
        "under Batch tools, PhotUtils, Interactive tools, Shared, Utilities, and Automation. The canonical launchers "
        "add these folders to the Python search path automatically."
    )

    doc.add_heading("Documentation Rule", level=1)
    doc.add_paragraph(
        "Maintained documentation deliverables in this folder are DOCX files only. Render folders, PDFs, and "
        "standalone PNG documentation intermediates are disposable QA artifacts and should not be retained."
    )

    for out_path in OUT_PATHS:
        doc.save(out_path)
        print(out_path)


if __name__ == "__main__":
    main()
