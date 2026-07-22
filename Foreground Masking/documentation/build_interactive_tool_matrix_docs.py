#!/usr/bin/env python3
"""Build the DOCX index for supported SEP and MTObjects interactive tools."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt


OUT_PATH = Path(__file__).resolve().parent / "Foreground Masking Interactive Tools Matrix.docx"


TOOLS = [
    [
        "SEP",
        "Spike Gate",
        "interactive_sep_spike_gate_parameter_tester.py",
        "interactive_sep_spike_gate_parameter_tester",
        "Tune and inspect SEP masks constrained by bar-profile Spike Gate evidence.",
    ],
    [
        "SEP",
        "Toy Object",
        "interactive_sep_toy_object_tester.py",
        "interactive_sep_toy_object_tester",
        "Place a toy object by click or coordinate entry, then test recovery with current SEP best parameters.",
    ],
    [
        "MTObjects",
        "Spike Gate",
        "interactive_mtobjects_spike_gate_parameter_tester.py",
        "interactive_mtobjects_spike_gate_parameter_tester",
        "Tune and inspect MTObjects masks with the Spike Gate comparison panels.",
    ],
    [
        "MTObjects",
        "Toy Object",
        "interactive_mtobjects_toy_object_tester.py",
        "interactive_mtobjects_toy_object_tester",
        "Place a toy object by click or coordinate entry, then test recovery with current MTObjects best parameters.",
    ],
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
    run = title.add_run("Foreground Masking Interactive Tools Matrix")
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(18)
    subtitle = doc.add_paragraph(f"Updated {date.today().isoformat()}")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph(
        "The maintained interactive tools are organized as a two-by-two set: SEP and MTObjects, each with "
        "Spike Gate and Toy Object methods. Standard non-spike interactive SEP and MTObjects variants are retired; "
        "batch application now uses optimized parameter JSON files. The launcher filenames below are the supported "
        "interactive entry points."
    )

    table = doc.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    headers = ["Algorithm", "Method", "Launcher", "Output Folder", "Purpose"]
    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True

    for row in TOOLS:
        cells = table.add_row().cells
        for cell, value in zip(cells, row):
            cell.text = value

    doc.add_heading("Launch Commands", level=1)
    add_code(doc, 'python "Foreground Masking\\interactive_sep_spike_gate_parameter_tester.py"')
    add_code(doc, 'python "Foreground Masking\\interactive_sep_toy_object_tester.py"')
    add_code(doc, 'python "Foreground Masking\\interactive_mtobjects_spike_gate_parameter_tester.py"')
    add_code(doc, 'python "Foreground Masking\\interactive_mtobjects_toy_object_tester.py"')

    doc.add_heading("Toy Object Placement", level=1)
    doc.add_paragraph(
        "The Toy Object tools let the user choose the toy location interactively by clicking the deprojected, "
        "bar-aligned image or by typing deprojected x/y arcsec coordinates. The complete toy truth mask must stay "
        "inside the investigated galaxy cutout. PNG diagnostics are written to the method-specific output folder."
    )

    doc.add_heading("Documentation Rule", level=1)
    doc.add_paragraph(
        "Maintained documentation deliverables in this folder are DOCX files only. Render folders, PDFs, and "
        "standalone PNG documentation intermediates are disposable QA artifacts and should not be retained."
    )

    doc.save(OUT_PATH)
    print(OUT_PATH)


if __name__ == "__main__":
    main()
