#!/usr/bin/env python3
"""Interactive reviewer for Gaia/2MASS-assisted clean-galaxy candidates."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import math
import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


if os.name == "nt":
    REVIEW_ROOT = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects")
else:
    REVIEW_ROOT = Path("/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects")
DEFAULT_ROOT = REVIEW_ROOT / "gaia_zero_57_hybrid_ranking"
PHASE2_ROOT = REVIEW_ROOT / "catalogue_review_phase2_next30"
PHASE3_ROOT = REVIEW_ROOT / "catalogue_review_phase3_clean_similarity"
CLASSIFICATIONS = ("Clean", "Ambiguous", "Polluted")
INSTRUCTIONS = """Purpose

Classify whether each galaxy field is suitable for foreground-sensitive science measurements. You are judging unrelated compact sources that could contaminate the galaxy measurement—not the galaxy's own bars, arms, rings, or star-forming structure.

How to inspect the three panels

1. Original 3.6 μm: decide whether obvious compact objects are superimposed on or close to the galaxy.
2. Gaussian residual: compact positive peaks are easier to see, but arms and star-forming knots also appear here. A residual peak alone is not proof of a foreground object.
3. Catalogue candidates: red circles are reliable 2MASS point sources; yellow circles are weaker Gaia evidence. Circles are supporting evidence, not an automatic classification.

Classification rubric

Clean
• No convincing bright foreground point source likely to affect the galaxy measurement.
• Catalogue circles are absent, very faint, clearly outside the useful galaxy region, or appear to be galaxy structure.

Ambiguous
• A compact source may be foreground, but could plausibly be a galaxy knot, arm feature, or background object.
• Use this when the scientific impact is uncertain rather than guessing.

Polluted
• One or more convincing bright, compact foreground sources overlap or lie close enough to the galaxy to affect measurements.
• Several moderate point sources can also justify Polluted.

What not to penalise

Do not mark a field Polluted merely because the galaxy has a bright nucleus, clumpy arms, a ring, a bar, or internal star formation. Judge only plausible unrelated sources and their likely scientific impact.

Workflow

Record a decision, add a short note when useful, then move to the next field. Progress is saved automatically. The resulting labels will be used to calibrate and validate the automatic ranking; they do not alter any FITS image or mask."""


class CatalogueReviewer(tk.Tk):
    def __init__(self, ranking: Path, panels: Path, decisions: Path):
        super().__init__()
        self.title("Catalogue-assisted Galaxy Cleanliness Reviewer")
        self.geometry("1500x900")
        self.ranking_path = ranking
        self.panels_dir = panels
        self.decisions_path = decisions
        self.rows = self._read_rows(ranking)
        if not self.rows:
            raise ValueError(f"No ranking rows found in {ranking}")
        self.decisions = self._read_decisions(decisions)
        self.index = 0
        self.photo: tk.PhotoImage | None = None
        self.classification_var = tk.StringVar()
        self.notes_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.progress_var = tk.StringVar()
        self._build_ui()
        self._bind_keys()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.show_current()

    @staticmethod
    def _read_rows(path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    @staticmethod
    def _read_decisions(path: Path) -> dict[str, dict[str, str]]:
        if not path.exists():
            return {}
        with path.open(newline="", encoding="utf-8") as handle:
            return {row["name"]: row for row in csv.DictReader(handle)}

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=8)
        header.pack(fill="x")
        ttk.Button(header, text="◀ Previous", command=self.previous).pack(side="left")
        ttk.Button(header, text="Next ▶", command=self.next).pack(side="left", padx=(6, 18))
        self.name_combo = ttk.Combobox(
            header, textvariable=self.name_var,
            values=[row["name"] for row in self.rows], state="readonly", width=18,
        )
        self.name_combo.pack(side="left")
        self.name_combo.bind("<<ComboboxSelected>>", self.jump_to_name)
        ttk.Button(header, text="Next unreviewed", command=self.next_unreviewed).pack(side="left", padx=8)
        ttk.Button(header, text="Instructions", command=self.show_instructions).pack(side="left")
        ttk.Label(header, textvariable=self.progress_var).pack(side="right")

        self.canvas = tk.Canvas(self, background="#202020", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8)
        self.image_item = self.canvas.create_image(0, 0, anchor="n")
        self.canvas.bind("<Configure>", self._canvas_resized)

        controls = ttk.Frame(self, padding=10)
        controls.pack(fill="x")
        ttk.Label(controls, text="Decision:").grid(row=0, column=0, sticky="w")
        for column, label in enumerate(CLASSIFICATIONS, start=1):
            ttk.Radiobutton(
                controls, text=f"{label} (Ctrl+{label[0].upper()})",
                variable=self.classification_var, value=label,
                command=self.save_current,
            ).grid(row=0, column=column, padx=10, sticky="w")
        ttk.Label(controls, text="Notes:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        notes = ttk.Entry(controls, textvariable=self.notes_var)
        notes.grid(row=1, column=1, columnspan=4, sticky="ew", pady=(10, 0))
        notes.bind("<FocusOut>", lambda _event: self.save_current())
        notes.bind("<Return>", lambda _event: (self.save_current(), self.next()))
        controls.columnconfigure(4, weight=1)
        ttk.Label(
            controls,
            text="Red = scored 2MASS point source; yellow = weak Gaia evidence; cyan = excluded centre (when shown).",
        ).grid(row=2, column=0, columnspan=5, sticky="w", pady=(10, 0))
        ttk.Label(
            controls,
            text="Goal: judge plausible unrelated compact sources and their scientific impact—not the galaxy's own structure.",
        ).grid(row=3, column=0, columnspan=5, sticky="w", pady=(4, 0))

    def _bind_keys(self) -> None:
        self.bind("<Left>", lambda _event: self.previous())
        self.bind("<Right>", lambda _event: self.next())
        self.bind("<Control-c>", lambda _event: self.classify("Clean"))
        self.bind("<Control-a>", lambda _event: self.classify("Ambiguous"))
        self.bind("<Control-p>", lambda _event: self.classify("Polluted"))

    def show_instructions(self) -> None:
        window = tk.Toplevel(self)
        window.title("Reviewer instructions")
        window.geometry("760x700")
        window.transient(self)
        frame = ttk.Frame(window, padding=12)
        frame.pack(fill="both", expand=True)
        text_widget = tk.Text(frame, wrap="word", padx=10, pady=10)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        text_widget.insert("1.0", INSTRUCTIONS)
        text_widget.configure(state="disabled")
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def current_row(self) -> dict[str, str]:
        return self.rows[self.index]

    def _canvas_resized(self, event) -> None:
        """Keep the review panel centred after Tk lays out or resizes the canvas."""
        if self.photo is not None:
            self.canvas.coords(self.image_item, max(self.photo.width() // 2, event.width // 2), 0)

    def show_current(self) -> None:
        row = self.current_row()
        name = row["name"]
        self.name_var.set(name)
        decision = self.decisions.get(name, {})
        self.classification_var.set(decision.get("classification", ""))
        self.notes_var.set(decision.get("notes", ""))
        panel = self.panels_dir / f"{name}.png"
        if panel.exists():
            original = tk.PhotoImage(file=panel)
            # Tk reports a width of 1 before its first layout pass.  Force that
            # pass so the initial galaxy is scaled and positioned correctly.
            self.update_idletasks()
            canvas_width = self.canvas.winfo_width()
            if canvas_width <= 10:
                canvas_width = self.winfo_screenwidth() - 40
            available_width = max(300, canvas_width - 20)
            factor = max(1, math.ceil(original.width() / available_width))
            self.photo = original.subsample(factor, factor) if factor > 1 else original
            self.canvas.itemconfigure(self.image_item, image=self.photo)
            center_x = max(self.photo.width() // 2, canvas_width // 2)
            self.canvas.coords(self.image_item, center_x, 0)
            self.canvas.configure(scrollregion=(0, 0, max(canvas_width, self.photo.width()), self.photo.height()))
        else:
            self.photo = None
            self.canvas.itemconfigure(self.image_item, image="")
        reviewed = sum(1 for row in self.rows if row["name"] in self.decisions and self.decisions[row["name"]].get("classification"))
        self.progress_var.set(
            f"Rank {row['rank']} of {len(self.rows)}  |  score {float(row['hybrid_score']):.3f}  |  "
            f"2MASS {row['twomass_count']}  |  weak Gaia {row['weak_gaia_count']}  |  reviewed {reviewed}/{len(self.rows)}"
        )

    def save_current(self) -> None:
        row = self.current_row()
        classification = self.classification_var.get().strip()
        notes = self.notes_var.get().strip()
        if classification or notes:
            self.decisions[row["name"]] = {
                "rank": row["rank"], "name": row["name"],
                "classification": classification, "notes": notes,
                "hybrid_score": row["hybrid_score"],
                "twomass_count": row["twomass_count"],
                "weak_gaia_count": row["weak_gaia_count"],
                "reviewed_at": datetime.now().isoformat(timespec="seconds"),
            }
        self.write_decisions()

    def write_decisions(self) -> None:
        self.decisions_path.parent.mkdir(parents=True, exist_ok=True)
        fields = ["rank", "name", "classification", "notes", "hybrid_score", "twomass_count", "weak_gaia_count", "reviewed_at"]
        temporary = self.decisions_path.with_suffix(self.decisions_path.suffix + ".tmp")
        with temporary.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in self.rows:
                if row["name"] in self.decisions:
                    writer.writerow(self.decisions[row["name"]])
        temporary.replace(self.decisions_path)

    def classify(self, value: str) -> None:
        self.classification_var.set(value)
        self.save_current()
        self.next()

    def previous(self) -> None:
        self.save_current()
        self.index = (self.index - 1) % len(self.rows)
        self.show_current()

    def next(self) -> None:
        self.save_current()
        self.index = (self.index + 1) % len(self.rows)
        self.show_current()

    def next_unreviewed(self) -> None:
        self.save_current()
        for offset in range(1, len(self.rows) + 1):
            candidate = (self.index + offset) % len(self.rows)
            name = self.rows[candidate]["name"]
            if not self.decisions.get(name, {}).get("classification"):
                self.index = candidate
                self.show_current()
                return
        messagebox.showinfo("Review complete", "Every galaxy has a classification.")

    def jump_to_name(self, _event=None) -> None:
        self.save_current()
        selected = self.name_var.get()
        self.index = next(index for index, row in enumerate(self.rows) if row["name"] == selected)
        self.show_current()

    def close(self) -> None:
        self.save_current()
        self.destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ranking", type=Path, default=DEFAULT_ROOT / "gaia_zero_hybrid_ranking.csv")
    parser.add_argument("--panels", type=Path, default=DEFAULT_ROOT / "review_panels")
    parser.add_argument("--decisions", type=Path, default=DEFAULT_ROOT / "catalogue_cleanliness_reviews.csv")
    parser.add_argument("--phase2", action="store_true", help="Open the prepared next-30 review set.")
    parser.add_argument("--phase3", action="store_true", help="Open the clean-reference similarity review set.")
    args = parser.parse_args()
    if args.phase2:
        args.ranking = PHASE2_ROOT / "gaia_zero_hybrid_ranking.csv"
        args.panels = PHASE2_ROOT / "review_panels"
        args.decisions = PHASE2_ROOT / "catalogue_cleanliness_reviews_phase2.csv"
    if args.phase3:
        args.ranking = PHASE3_ROOT / "gaia_zero_hybrid_ranking.csv"
        args.panels = PHASE3_ROOT / "review_panels"
        args.decisions = PHASE3_ROOT / "catalogue_cleanliness_reviews_phase3.csv"
    app = CatalogueReviewer(args.ranking, args.panels, args.decisions)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
