#!/usr/bin/env python3
"""Blind 0-3 contamination-severity reviewer for selecting the cleanest 20."""

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
    DEFAULT_ROOT = Path(r"D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\final_cleanest20_severity_review")
else:
    DEFAULT_ROOT = Path("/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/final_cleanest20_severity_review")

INSTRUCTIONS = """Assign contamination severity from the original image only.

0 — None: no convincing unrelated contaminant affecting the useful galaxy image.
1 — Minor: faint, isolated or peripheral contamination; unlikely to dominate a measurement.
2 — Moderate: clear contamination that could affect measurements but is limited or maskable.
3 — Severe: bright, numerous, central or widespread contaminants.

Use the full 0–3 scale comparatively. Names and earlier classifications are hidden.
The final cleanest 20 will be ordered by severity, with earlier blind Clean status
used only as a tie-break after this independent scoring."""


class SeverityReviewer(tk.Tk):
    def __init__(self, manifest: Path, panels: Path, output: Path):
        super().__init__(); self.title("Final Cleanest-20 Severity Review"); self.geometry("1100x900")
        self.rows = self.read(manifest); self.panels = panels; self.output = output
        self.saved = {row["audit_id"]: row for row in self.read(output)} if output.exists() else {}
        self.index = 0; self.photo: tk.PhotoImage | None = None
        self.notes_var = tk.StringVar(); self.status_var = tk.StringVar(); self.score_var = tk.StringVar()
        self._build(); self._bind_keys(); self.protocol("WM_DELETE_WINDOW", self.close); self.show_current()

    @staticmethod
    def read(path: Path) -> list[dict[str, str]]:
        with path.open(newline="", encoding="utf-8") as handle: return list(csv.DictReader(handle))

    def _build(self) -> None:
        top = ttk.Frame(self, padding=8); top.pack(fill="x")
        ttk.Button(top, text="◀ Previous", command=self.previous).pack(side="left")
        ttk.Button(top, text="Next ▶", command=self.next).pack(side="left", padx=6)
        ttk.Button(top, text="Next unscored", command=self.next_unscored).pack(side="left", padx=8)
        ttk.Button(top, text="Instructions", command=lambda: messagebox.showinfo("Severity instructions", INSTRUCTIONS)).pack(side="left")
        ttk.Label(top, textvariable=self.status_var).pack(side="right")
        self.canvas = tk.Canvas(self, background="#202020", highlightthickness=0); self.canvas.pack(fill="both", expand=True, padx=8)
        self.item = self.canvas.create_image(0, 0, anchor="n"); self.canvas.bind("<Configure>", self.resized)
        controls = ttk.Frame(self, padding=9); controls.pack(fill="x")
        ttk.Label(controls, text="Severity:").grid(row=0, column=0, sticky="w")
        labels = (("0 — None", 0), ("1 — Minor", 1), ("2 — Moderate", 2), ("3 — Severe", 3))
        for column, (text, value) in enumerate(labels, start=1):
            ttk.Button(controls, text=text, width=14, command=lambda score=value: self.score(score)).grid(row=0, column=column, padx=4)
        ttk.Label(controls, textvariable=self.score_var).grid(row=0, column=5, padx=12, sticky="w")
        ttk.Label(controls, text="Notes:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        notes = ttk.Entry(controls, textvariable=self.notes_var); notes.grid(row=1, column=1, columnspan=5, sticky="ew", pady=(8, 0))
        notes.bind("<FocusOut>", lambda _e: self.save()); controls.columnconfigure(5, weight=1)

    def _bind_keys(self) -> None:
        for value in range(4): self.bind(str(value), lambda _event, score=value: self.score(score))
        self.bind("<Left>", lambda _e: self.previous()); self.bind("<Right>", lambda _e: self.next())

    def current(self) -> dict[str, str]: return self.rows[self.index]

    def show_current(self) -> None:
        row = self.current(); saved = self.saved.get(row["audit_id"], {})
        self.notes_var.set(saved.get("notes", "")); score = saved.get("severity", "")
        self.score_var.set(f"Recorded severity: {score}" if score != "" else "Not yet scored")
        original = tk.PhotoImage(file=self.panels / f"field_{row['audit_id']}.png")
        self.update_idletasks(); width=max(300,self.canvas.winfo_width()-20); height=max(300,self.canvas.winfo_height()-10)
        factor=max(1,math.ceil(original.width()/width),math.ceil(original.height()/height)); self.photo=original.subsample(factor,factor) if factor>1 else original
        self.canvas.itemconfigure(self.item,image=self.photo); self.canvas.coords(self.item,max(self.photo.width()//2,self.canvas.winfo_width()//2),0)
        count=sum(item.get("severity","")!="" for item in self.saved.values()); self.status_var.set(f"Severity field {row['audit_id']} of {len(self.rows)} | scored {count}/{len(self.rows)}")

    def resized(self,event) -> None:
        if self.photo: self.canvas.coords(self.item,max(self.photo.width()//2,event.width//2),0)

    def score(self,value:int) -> None:
        row=self.current(); self.saved[row["audit_id"]]={**row,"severity":str(value),"notes":self.notes_var.get().strip(),"reviewed_at":datetime.now().isoformat(timespec="seconds")}
        self.score_var.set(f"Recorded severity: {value}"); self.write()

    def save(self) -> None:
        row=self.current()
        if row["audit_id"] in self.saved:
            self.saved[row["audit_id"]]["notes"]=self.notes_var.get().strip(); self.write()

    def write(self) -> None:
        self.output.parent.mkdir(parents=True,exist_ok=True); temp=self.output.with_suffix(self.output.suffix+".tmp")
        fields=["audit_id","name","input_group","clean_similarity_margin","severity","notes","reviewed_at"]
        with temp.open("w",newline="",encoding="utf-8") as handle:
            writer=csv.DictWriter(handle,fieldnames=fields); writer.writeheader()
            for row in self.rows:
                if row["audit_id"] in self.saved: writer.writerow(self.saved[row["audit_id"]])
        temp.replace(self.output)

    def previous(self)->None: self.save(); self.index=(self.index-1)%len(self.rows); self.show_current()
    def next(self)->None: self.save(); self.index=(self.index+1)%len(self.rows); self.show_current()
    def next_unscored(self)->None:
        self.save()
        for offset in range(1,len(self.rows)+1):
            candidate=(self.index+offset)%len(self.rows)
            if self.saved.get(self.rows[candidate]["audit_id"],{}).get("severity","")=="": self.index=candidate; self.show_current(); return
        messagebox.showinfo("Complete","All fields have a severity score.")
    def close(self)->None: self.save(); self.destroy()


def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,default=DEFAULT_ROOT/"severity_manifest.csv")
    parser.add_argument("--panels",type=Path,default=DEFAULT_ROOT/"panels")
    parser.add_argument("--output",type=Path,default=DEFAULT_ROOT/"severity_decisions.csv")
    args=parser.parse_args(); app=SeverityReviewer(args.manifest,args.panels,args.output); app.mainloop(); return 0


if __name__=="__main__": raise SystemExit(main())
