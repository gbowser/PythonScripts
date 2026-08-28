#!/usr/bin/env python3
"""Original-image-only blind audit of galaxy-field cleanliness decisions."""

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
    DEFAULT_ROOT = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\blind_cleanliness_consistency_audit")
    REMAINING_ROOT = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\blind_cleanliness_remaining_71")
else:
    DEFAULT_ROOT = Path("/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/blind_cleanliness_consistency_audit")
    REMAINING_ROOT = Path("/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/blind_cleanliness_remaining_71")

INSTRUCTIONS = """Purpose

This audit checks whether the definition of a visually clean galaxy is stable
when catalogue circles, residuals, scores, names and previous decisions are hidden.

Judge the ORIGINAL image only.

Clean: no convincing unrelated compact foreground source substantially pollutes
the useful galaxy image. Do not penalise the nucleus, bar, arms, rings or coherent
star-forming structure.

Polluted: one or more convincing unrelated compact sources overlap the galaxy or
are bright/close enough to compromise foreground-sensitive measurements.

Ambiguous: use only when the image alone genuinely cannot distinguish an unrelated
source from galaxy structure. Do not try to reproduce an earlier decision.

The identity is revealed only after a decision is recorded. Move to the next field
without changing an answer merely because the revealed name is familiar."""


class BlindAudit(tk.Tk):
    def __init__(self, manifest: Path, panels: Path, output: Path):
        super().__init__()
        self.title("Blind Galaxy Cleanliness Consistency Audit")
        self.geometry("1100x900")
        self.rows = self.read_rows(manifest)
        self.panels, self.output = panels, output
        self.saved = {row["audit_id"]: row for row in self.read_rows(output)} if output.exists() else {}
        self.index = 0
        self.photo: tk.PhotoImage | None = None
        self.decision_var = tk.StringVar(); self.notes_var = tk.StringVar()
        self.progress_var = tk.StringVar(); self.reveal_var = tk.StringVar()
        self.decision_status_var = tk.StringVar()
        self._build(); self._bind_keys(); self.protocol("WM_DELETE_WINDOW", self.close); self.show_current()

    @staticmethod
    def read_rows(path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def _build(self) -> None:
        top = ttk.Frame(self, padding=8); top.pack(fill="x")
        ttk.Button(top, text="◀ Previous", command=self.previous).pack(side="left")
        ttk.Button(top, text="Next ▶", command=self.next).pack(side="left", padx=6)
        ttk.Button(top, text="Next undecided", command=self.next_undecided).pack(side="left", padx=(10, 6))
        ttk.Button(top, text="Instructions", command=lambda: messagebox.showinfo("Instructions", INSTRUCTIONS)).pack(side="left")
        ttk.Label(top, textvariable=self.progress_var).pack(side="right")
        self.canvas = tk.Canvas(self, background="#202020", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=8)
        self.image_item = self.canvas.create_image(0, 0, anchor="n")
        self.canvas.bind("<Configure>", self.resized)
        controls = ttk.Frame(self, padding=9); controls.pack(fill="x")
        ttk.Label(controls, text="Decision:").grid(row=0, column=0, sticky="w")
        for column, label in enumerate(("Clean", "Ambiguous", "Polluted"), start=1):
            ttk.Button(controls, text=label, command=lambda value=label: self.classify(value),
                       width=12).grid(row=0, column=column, padx=5, sticky="w")
        ttk.Label(controls, textvariable=self.decision_status_var).grid(row=0, column=4, padx=(12, 5), sticky="w")
        ttk.Button(controls, text="Reveal identity after deciding", command=self.reveal).grid(row=0, column=5, padx=10)
        ttk.Label(controls, textvariable=self.reveal_var).grid(row=0, column=6, sticky="w")
        ttk.Label(controls, text="Notes:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        notes = ttk.Entry(controls, textvariable=self.notes_var)
        notes.grid(row=1, column=1, columnspan=6, sticky="ew", pady=(8, 0))
        notes.bind("<FocusOut>", lambda _e: self.save_current())
        controls.columnconfigure(6, weight=1)

    def _bind_keys(self) -> None:
        self.bind("<Control-c>", lambda _event: self.classify("Clean"))
        self.bind("<Control-a>", lambda _event: self.classify("Ambiguous"))
        self.bind("<Control-p>", lambda _event: self.classify("Polluted"))
        self.bind("<Left>", lambda _event: self.previous())
        self.bind("<Right>", lambda _event: self.next())

    def current(self) -> dict[str, str]: return self.rows[self.index]

    def show_current(self) -> None:
        row = self.current(); saved = self.saved.get(row["audit_id"], {})
        self.decision_var.set(saved.get("blind_decision", "")); self.notes_var.set(saved.get("notes", ""))
        decision = self.decision_var.get()
        self.decision_status_var.set(f"Recorded: {decision}" if decision else "Not yet decided")
        self.reveal_var.set("")
        original = tk.PhotoImage(file=self.panels / f"field_{row['audit_id']}.png")
        self.update_idletasks(); width = max(300, self.canvas.winfo_width() - 20)
        height = max(300, self.canvas.winfo_height() - 10)
        factor = max(1, math.ceil(original.width() / width), math.ceil(original.height() / height))
        self.photo = original.subsample(factor, factor) if factor > 1 else original
        self.canvas.itemconfigure(self.image_item, image=self.photo)
        self.canvas.coords(self.image_item, max(self.photo.width() // 2, self.canvas.winfo_width() // 2), 0)
        decided = sum(bool(item.get("blind_decision")) for item in self.saved.values())
        self.progress_var.set(f"Blind field {row['audit_id']} of {len(self.rows)}  |  decided {decided}/{len(self.rows)}")

    def resized(self, event) -> None:
        if self.photo: self.canvas.coords(self.image_item, max(self.photo.width() // 2, event.width // 2), 0)

    def reveal(self) -> None:
        if not self.decision_var.get():
            messagebox.showwarning("Decide first", "Record a blind decision before revealing the identity.")
            return
        row = self.current()
        self.reveal_var.set(f"{row['name']} (previously {row['previous_label']})")

    def classify(self, value: str) -> None:
        self.decision_var.set(value)
        self.decision_status_var.set(f"Recorded: {value}")
        self.save_current()

    def save_current(self) -> None:
        row = self.current(); decision = self.decision_var.get().strip(); notes = self.notes_var.get().strip()
        if decision or notes:
            self.saved[row["audit_id"]] = {
                **row, "blind_decision": decision, "notes": notes,
                "reviewed_at": datetime.now().isoformat(timespec="seconds"),
            }
        self.output.parent.mkdir(parents=True, exist_ok=True)
        temp = self.output.with_suffix(self.output.suffix + ".tmp")
        fields = ["audit_id", "name", "previous_label", "source", "blind_decision", "notes", "reviewed_at"]
        with temp.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
            for item in self.rows:
                if item["audit_id"] in self.saved: writer.writerow(self.saved[item["audit_id"]])
        temp.replace(self.output)

    def previous(self) -> None: self.save_current(); self.index = (self.index - 1) % len(self.rows); self.show_current()
    def next(self) -> None: self.save_current(); self.index = (self.index + 1) % len(self.rows); self.show_current()
    def next_undecided(self) -> None:
        self.save_current()
        for offset in range(1, len(self.rows) + 1):
            candidate = (self.index + offset) % len(self.rows)
            if not self.saved.get(self.rows[candidate]["audit_id"], {}).get("blind_decision"):
                self.index = candidate; self.show_current(); return
        messagebox.showinfo("Complete", "All blind fields have a decision.")
    def close(self) -> None: self.save_current(); self.destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_ROOT / "blind_audit_manifest.csv")
    parser.add_argument("--panels", type=Path, default=DEFAULT_ROOT / "panels")
    parser.add_argument("--output", type=Path, default=DEFAULT_ROOT / "blind_audit_decisions.csv")
    parser.add_argument("--remaining", action="store_true", help="Open the 71-field remaining-population blind review.")
    args = parser.parse_args()
    if args.remaining:
        args.manifest = REMAINING_ROOT / "blind_audit_manifest.csv"
        args.panels = REMAINING_ROOT / "panels"
        args.output = REMAINING_ROOT / "blind_remaining_decisions.csv"
    app = BlindAudit(args.manifest, args.panels, args.output); app.mainloop(); return 0


if __name__ == "__main__": raise SystemExit(main())
