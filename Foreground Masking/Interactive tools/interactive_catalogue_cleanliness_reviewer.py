#!/usr/bin/env python3
"""Interactive reviewer for Gaia/2MASS-assisted clean-galaxy candidates."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import os
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk


if os.name == "nt":
    REVIEW_ROOT = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects")
else:
    REVIEW_ROOT = Path("/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects")
DEFAULT_ROOT = REVIEW_ROOT / "gaia_zero_57_hybrid_ranking"
PHASE2_ROOT = REVIEW_ROOT / "catalogue_review_phase2_next30"
PHASE3_ROOT = REVIEW_ROOT / "catalogue_review_phase3_clean_similarity"
CLEANEST30_ROOT = REVIEW_ROOT / "cleanest30_catalogue_rereview"
CANDIDATE_UNION_ROOT = REVIEW_ROOT / "clean_candidate_union_rereview"
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
        self.photo: ImageTk.PhotoImage | None = None
        self.panel_path: Path | None = None
        self.resize_job: str | None = None
        self.classification_var = tk.StringVar()
        self.notes_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.progress_var = tk.StringVar()
        self.current_decision_var = tk.StringVar(value="Current classification: NOT REVIEWED")
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
        self.current_decision_label = tk.Label(
            controls, textvariable=self.current_decision_var,
            font=("TkDefaultFont", 11, "bold"), padx=10, pady=5,
            background="#555555", foreground="white",
        )
        self.current_decision_label.grid(row=0, column=0, columnspan=5, sticky="ew", pady=(0, 8))
        ttk.Label(controls, text="Change decision:").grid(row=1, column=0, sticky="w")
        for column, label in enumerate(CLASSIFICATIONS, start=1):
            ttk.Radiobutton(
                controls, text=f"{label} (Ctrl+{label[0].upper()})",
                variable=self.classification_var, value=label,
                command=self.save_current,
            ).grid(row=1, column=column, padx=10, sticky="w")
        ttk.Label(controls, text="Notes:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        notes = ttk.Entry(controls, textvariable=self.notes_var)
        notes.grid(row=2, column=1, columnspan=4, sticky="ew", pady=(10, 0))
        notes.bind("<FocusOut>", lambda _event: self.save_current())
        notes.bind("<Return>", lambda _event: (self.save_current(), self.next()))
        controls.columnconfigure(4, weight=1)
        ttk.Label(
            controls,
            text="Red = scored 2MASS point source; yellow = weak Gaia evidence; cyan = excluded centre (when shown).",
        ).grid(row=3, column=0, columnspan=5, sticky="w", pady=(10, 0))
        ttk.Label(
            controls,
            text="Goal: judge plausible unrelated compact sources and their scientific impact—not the galaxy's own structure.",
        ).grid(row=4, column=0, columnspan=5, sticky="w", pady=(4, 0))

    def _show_decision_status(self, classification: str) -> None:
        colours = {
            "Clean": ("#197a35", "white"),
            "Ambiguous": ("#d99600", "black"),
            "Polluted": ("#b3261e", "white"),
        }
        if classification in colours:
            background, foreground = colours[classification]
            text = f"Current classification: {classification.upper()}"
        else:
            background, foreground = "#555555", "white"
            text = "Current classification: NOT REVIEWED"
        self.current_decision_var.set(text)
        self.current_decision_label.configure(background=background, foreground=foreground)

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
        """Debounce redraws while making the panel as large as the canvas permits."""
        if self.resize_job is not None:
            self.after_cancel(self.resize_job)
        self.resize_job = self.after(100, self._render_current_panel)

    def _render_current_panel(self) -> None:
        self.resize_job = None
        if self.panel_path is None or not self.panel_path.exists():
            self.photo = None
            self.canvas.itemconfigure(self.image_item, image="")
            return
        self.update_idletasks()
        available_width = max(300, self.canvas.winfo_width() - 12)
        available_height = max(250, self.canvas.winfo_height() - 12)
        with Image.open(self.panel_path) as source:
            scale = min(available_width / source.width, available_height / source.height)
            width = max(1, int(round(source.width * scale)))
            height = max(1, int(round(source.height * scale)))
            resized = source.resize((width, height), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(resized)
        self.canvas.itemconfigure(self.image_item, image=self.photo)
        self.canvas.coords(self.image_item, self.canvas.winfo_width() // 2, 6)
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), height + 12))

    def show_current(self) -> None:
        row = self.current_row()
        name = row["name"]
        self.name_var.set(name)
        decision = self.decisions.get(name, {})
        self.classification_var.set(decision.get("classification", ""))
        self._show_decision_status(decision.get("classification", ""))
        self.notes_var.set(decision.get("notes", ""))
        panel = self.panels_dir / f"{name}.png"
        if panel.exists():
            self.panel_path = panel
            self._render_current_panel()
        else:
            self.panel_path = None
            self.photo = None
            self.canvas.itemconfigure(self.image_item, image="")
        reviewed = sum(1 for row in self.rows if row["name"] in self.decisions and self.decisions[row["name"]].get("classification"))
        class_counts = {
            label: sum(
                1 for candidate in self.rows
                if self.decisions.get(candidate["name"], {}).get("classification") == label
            )
            for label in CLASSIFICATIONS
        }
        membership = []
        if row.get("in_original40", "").lower() == "yes":
            membership.append("original 40")
        if row.get("in_latest_top50", "").lower() == "yes":
            membership.append("latest top 50")
        membership_text = "  |  " + " + ".join(membership) if membership else ""
        self.progress_var.set(
            f"Rank {row['rank']} of {len(self.rows)}  |  score {float(row['hybrid_score']):.3f}  |  "
            f"2MASS {row['twomass_count']}  |  weak Gaia {row['weak_gaia_count']}"
            f"{membership_text}  |  Clean {class_counts['Clean']}  |  "
            f"Ambiguous {class_counts['Ambiguous']}  |  Polluted {class_counts['Polluted']}  |  "
            f"reviewed {reviewed}/{len(self.rows)}"
        )

    def save_current(self) -> None:
        row = self.current_row()
        classification = self.classification_var.get().strip()
        self._show_decision_status(classification)
        notes = self.notes_var.get().strip()
        if classification or notes:
            self.decisions[row["name"]] = {
                "rank": row["rank"], "name": row["name"],
                "classification": classification, "notes": notes,
                "hybrid_score": row["hybrid_score"],
                "twomass_count": row["twomass_count"],
                "weak_gaia_count": row["weak_gaia_count"],
                "in_original40": row.get("in_original40", ""),
                "in_latest_top50": row.get("in_latest_top50", ""),
                "reviewed_at": datetime.now().isoformat(timespec="seconds"),
            }
        self.write_decisions()
        self._update_running_totals()

    def _update_running_totals(self) -> None:
        """Refresh the header after a decision without reloading the panel image."""
        row = self.current_row()
        reviewed = sum(
            1 for candidate in self.rows
            if self.decisions.get(candidate["name"], {}).get("classification")
        )
        counts = {
            label: sum(
                1 for candidate in self.rows
                if self.decisions.get(candidate["name"], {}).get("classification") == label
            )
            for label in CLASSIFICATIONS
        }
        membership = []
        if row.get("in_original40", "").lower() == "yes":
            membership.append("original 40")
        if row.get("in_latest_top50", "").lower() == "yes":
            membership.append("latest top 50")
        membership_text = "  |  " + " + ".join(membership) if membership else ""
        self.progress_var.set(
            f"Rank {row['rank']} of {len(self.rows)}  |  score {float(row['hybrid_score']):.3f}  |  "
            f"2MASS {row['twomass_count']}  |  weak Gaia {row['weak_gaia_count']}"
            f"{membership_text}  |  Clean {counts['Clean']}  |  Ambiguous {counts['Ambiguous']}  |  "
            f"Polluted {counts['Polluted']}  |  reviewed {reviewed}/{len(self.rows)}"
        )

    def write_decisions(self) -> None:
        self.decisions_path.parent.mkdir(parents=True, exist_ok=True)
        fields = ["rank", "name", "classification", "notes", "hybrid_score", "twomass_count", "weak_gaia_count", "in_original40", "in_latest_top50", "reviewed_at"]
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
    parser.add_argument(
        "--cleanest30", action="store_true",
        help="Open the fresh categorical re-review of the 30 least-polluted finalists.",
    )
    parser.add_argument(
        "--candidate-union", action="store_true",
        help="Review the union of the original 40 and latest all-galaxy top 50.",
    )
    args = parser.parse_args()
    if args.phase2:
        args.ranking = PHASE2_ROOT / "gaia_zero_hybrid_ranking.csv"
        args.panels = PHASE2_ROOT / "review_panels"
        args.decisions = PHASE2_ROOT / "catalogue_cleanliness_reviews_phase2.csv"
    if args.phase3:
        args.ranking = PHASE3_ROOT / "gaia_zero_hybrid_ranking.csv"
        args.panels = PHASE3_ROOT / "review_panels"
        args.decisions = PHASE3_ROOT / "catalogue_cleanliness_reviews_phase3.csv"
    if args.cleanest30:
        args.ranking = CLEANEST30_ROOT / "gaia_zero_hybrid_ranking.csv"
        args.panels = CLEANEST30_ROOT / "review_panels"
        args.decisions = CLEANEST30_ROOT / "cleanest30_rereview_decisions.csv"
    if args.candidate_union:
        args.ranking = CANDIDATE_UNION_ROOT / "gaia_zero_hybrid_ranking.csv"
        args.panels = CANDIDATE_UNION_ROOT / "review_panels"
        args.decisions = CANDIDATE_UNION_ROOT / "candidate_union_rereview_decisions.csv"
    app = CatalogueReviewer(args.ranking, args.panels, args.decisions)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
