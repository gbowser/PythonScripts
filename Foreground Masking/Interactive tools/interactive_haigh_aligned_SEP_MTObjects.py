#!/usr/bin/env python3
"""Review revised Haigh-aligned saved injections with SEP and MTObjects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from tkinter import messagebox

from matplotlib.lines import Line2D
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
FOREGROUND_ROOT = SCRIPT_DIR.parent
for folder in (SCRIPT_DIR, FOREGROUND_ROOT, FOREGROUND_ROOT / "Shared"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import foreground_display_helpers as display  # noqa: E402
import interactive_toy_objects_SEP_MTObjects as base  # noqa: E402
from machine_paths import PC_RESEARCH_FOLDERS, detect_pc  # noqa: E402


MODEL_VERSION = "haigh-aligned-s4g-empty-field-injections-v2"
LEGACY_MODEL_VERSION = "haigh-aligned-s4g-injections-v1"
SUPPORTED_MODEL_VERSIONS = {MODEL_VERSION, LEGACY_MODEL_VERSION}


def find_latest_manifest(pc: str) -> Path | None:
    # Use the same Windows/WSL translation as the parent reviewer. Calling
    # remove_foreground_folder() directly in WSL produces an unusable D:\ path.
    root = base.research_output_root(pc)
    matches: list[Path] = []
    for path in root.rglob("paired_toy_injection_manifest.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("injection_model_version") in SUPPORTED_MODEL_VERSIONS:
            matches.append(path)
    if not matches:
        return None
    return max(
        matches,
        key=lambda path: (
            json.loads(path.read_text(encoding="utf-8-sig")).get("injection_model_version") == MODEL_VERSION,
            path.stat().st_mtime,
        ),
    )


def default_pc() -> str:
    try:
        return detect_pc(FOREGROUND_ROOT)
    except RuntimeError:
        # This tool is normally launched in WSL, where Windows drive roots are
        # not visible to the generic host detector. The research data for this
        # workstation are on /mnt/d.
        return "Desktop"


class HaighAlignedReviewer(base.CombinedToyTester):
    """Saved-set-only reviewer; manual legacy Gaussian toys are disabled."""

    def __init__(self, args: argparse.Namespace):
        self.placement_region: np.ndarray | None = None
        self.batch_placement_metadata: dict = {}
        if args.injection_manifest is None:
            args.injection_manifest = find_latest_manifest(args.pc)
        if args.injection_manifest is None:
            raise FileNotFoundError(
                "No Haigh-aligned injection manifest was found. Generate one with "
                "generate_haigh_aligned_multiseed_manifest.py or pass --injection-manifest."
            )
        manifest = json.loads(args.injection_manifest.read_text(encoding="utf-8-sig"))
        if manifest.get("injection_model_version") not in SUPPORTED_MODEL_VERSIONS:
            raise ValueError(f"The selected manifest is not a supported Haigh-aligned model: {args.injection_manifest}")
        self.haigh_output_root = args.injection_manifest.parent.parent
        sep_winner, mto_winner = self._haigh_winner_paths()
        if args.sep_best is None and sep_winner.exists():
            args.sep_best = sep_winner
        if args.mto_best is None and mto_winner.exists():
            args.mto_best = mto_winner
        super().__init__(args)
        self.title("Haigh-aligned SEP and MTObjects Source-Injection Reviewer")
        self._adapt_source_controls()
        labels = tuple(self.batch_set_keys)
        self.batch_set_combo.configure(values=labels)
        self.batch_set_info.set(
            "Select Training 1–3 or Validation 1–2. The exact PSF/Sérsic payload loads automatically."
        )
        if labels:
            self.batch_set_var.set(labels[0])
            self.load_batch_toy_set()

    def _adapt_source_controls(self) -> None:
        """Remove legacy manual-toy controls and clarify the physical source UI."""
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)

        for widget in descendants(self):
            try:
                title = str(widget.cget("text"))
            except Exception:  # ttk widgets without a text option
                continue
            if title.startswith("Toy specification"):
                widget.pack_forget()
            elif title == "Saved five-toy batch arrangement":
                widget.configure(text="Saved contaminant arrangement (1–5 sources in total)")
        self._update_toys_state()

    def _populate_galaxies(self) -> None:
        """Offer only galaxies having payloads in every saved arrangement."""
        injection_sets = list((self.injection_manifest_data.get("injection_sets") or {}).values())
        available_sets = [set((item.get("galaxies") or {}).keys()) for item in injection_sets]
        available = set.intersection(*available_sets) if available_sets else set()
        labels: list[str] = []
        self.label_to_name = {}
        for row in self.rows:
            name = row["name"]
            if name not in available:
                continue
            classification = self.classifications.get(name, "Clean")
            label = f"{name} - {classification}"
            labels.append(label)
            self.label_to_name[label] = name
        labels.sort(key=lambda label: self.label_to_name[label].casefold())
        self.galaxy_combo.configure(values=labels)
        if not labels:
            raise ValueError("The selected injection manifest has no galaxies matching the science catalogue.")
        self.galaxy_var.set(labels[0])
        self.load_galaxy()

    def _source_description(self) -> str:
        if not self.batch_toy_records:
            return "No saved contaminant arrangement is loaded."
        stars = sum(row.get("object_type") == "star" for row in self.batch_toy_records)
        galaxies = len(self.batch_toy_records) - stars
        lines = [
            f"TOTAL {len(self.batch_toy_records)} contaminants = {stars} IRAC-PSF star(s) + "
            f"{galaxies} PSF-convolved Sérsic background galaxy/galaxies."
        ]
        if self.batch_placement_metadata:
            lines.append(
                "Placement: locally quiet pixels away from galaxy structure and existing compact objects; "
                f"eligible area {float(self.batch_placement_metadata.get('eligible_fraction', 0)):.1%} "
                "of displayed frame."
            )
        for row in self.batch_toy_records:
            toy_id = int(row.get("toy_id", len(lines)))
            peak = float(row.get("peak_sigma", float("nan")))
            if row.get("object_type") == "star":
                lines.append(
                    f"S{toy_id}  Star: FWHM {float(row.get('psf_fwhm_arcsec', 1.66)):.2f}″ "
                    f"({float(row.get('psf_fwhm_pixels', row.get('fwhm_pixels', 0))):.2f} px), "
                    f"peak {peak:.1f}σ."
                )
            else:
                lines.append(
                    f"G{toy_id}  Background galaxy: Re {float(row.get('effective_radius_arcsec', 0)):.2f}″, "
                    f"n {float(row.get('sersic_index', 0)):.2f}, "
                    f"q {float(row.get('axis_ratio', 1)):.2f}, "
                    f"PA {float(row.get('pa_deg', 0)):.0f}°, peak {peak:.1f}σ."
                )
        return "\n".join(lines)

    def load_batch_toy_set(self, redraw: bool = True) -> None:
        selected_label = self.batch_set_var.get()
        set_name = self.batch_set_keys.get(selected_label, selected_label)
        name = self.label_to_name.get(self.galaxy_var.get(), "")
        set_payload = (self.injection_manifest_data.get("injection_sets") or {}).get(set_name, {})
        if selected_label != "Manual toys only" and name not in (set_payload.get("galaxies") or {}):
            self._clear_batch_payload()
            self._update_toys_state()
            messagebox.showwarning(
                "No saved contaminants",
                f"{name} is not present in {selected_label}. Select one of the manifest's saved galaxies.",
            )
            return
        super().load_batch_toy_set(redraw=False)
        if self.batch_toy_records:
            record = self.injection_manifest_data["injection_sets"][set_name]["galaxies"][name]
            self.batch_placement_metadata = dict(record.get("placement_region") or {})
            payload_path = self._platform_payload_path(str(record["payload_path"]))
            with np.load(payload_path, allow_pickle=False) as payload:
                self.placement_region = (
                    np.asarray(payload["placement_region"], dtype=bool)
                    if "placement_region" in payload.files else None
                )
            self.batch_set_info.set(self._source_description())
        if redraw and self.data is not None:
            self.draw_preview()

    def _clear_batch_payload(self) -> None:
        super()._clear_batch_payload()
        self.placement_region = None
        self.batch_placement_metadata = {}

    def _update_toys_state(self) -> None:
        super()._update_toys_state()
        count = len(self.batch_toy_records)
        state = "IN" if self.toys_enabled else "OUT"
        self.toy_count.set(f"{count} contaminants total | {state}")
        self.toys_button_text.set(
            "Contaminants IN — click to show the clean baseline"
            if self.toys_enabled else
            "Contaminants OUT — click to restore the saved contaminants"
        )

    def _draw_image(self, axis, image, title, *, mask=False, residual=False,
                    catalogue=False, truth=None) -> None:
        """Draw physical source classes separately instead of one generic outline."""
        super()._draw_image(
            axis, image, title, mask=mask, residual=residual,
            catalogue=catalogue, truth=None,
        )
        if truth is None or not self.toys_enabled or self.batch_truth_labels is None:
            return
        label_view, x_axis, y_axis = self._display_view(self.batch_truth_labels, order=0)
        legend_classes: set[str] = set()
        rounded_labels = np.where(np.isfinite(label_view), np.rint(label_view), 0).astype(np.int32)
        for row in self.batch_toy_records:
            toy_id = int(row.get("toy_id", 0))
            footprint = rounded_labels == toy_id
            if not np.any(footprint):
                continue
            is_star = row.get("object_type") == "star"
            colour = "#00d83a" if is_star else "#ff00c8"
            prefix = "S" if is_star else "G"
            legend_classes.add("star" if is_star else "galaxy")
            axis.contour(
                x_axis, y_axis, footprint.astype(float), levels=[0.5],
                colors=[colour], linewidths=2.2, zorder=13,
            )
            yy, xx = np.nonzero(footprint)
            cx, cy = int(round(float(np.median(xx)))), int(round(float(np.median(yy))))
            axis.annotate(
                f"{prefix}{toy_id}", (x_axis[cx], y_axis[cy]), xytext=(5, 5),
                textcoords="offset points", color=colour, fontsize=9, fontweight="bold",
                bbox={"boxstyle": "round,pad=0.16", "facecolor": "black", "alpha": 0.68,
                      "edgecolor": colour}, zorder=14,
            )
        handles = []
        if "star" in legend_classes:
            handles.append(Line2D([0], [0], color="#00d83a", lw=2.2, label="S = IRAC-PSF star"))
        if "galaxy" in legend_classes:
            handles.append(Line2D([0], [0], color="#ff00c8", lw=2.2,
                                  label="G = PSF-convolved Sérsic galaxy"))
        if handles:
            axis.legend(handles=handles, loc="upper right", fontsize=8,
                        facecolor="white", framealpha=0.82)

    def _rename_source_titles(self) -> None:
        for axis in (self.axes[0, 0], self.axes[1, 0]):
            axis.set_title(axis.get_title().replace("toys", "contaminants").replace("Toys", "Contaminants"))

    def draw_preview(self) -> None:
        super().draw_preview()
        self._rename_source_titles()
        self.canvas.draw_idle()

    def draw_results(self, injected=None, truth=None):
        fractions = super().draw_results(injected=injected, truth=truth)
        self._rename_source_titles()
        self.canvas.draw_idle()
        return fractions

    def _haigh_winner_paths(self) -> tuple[Path, Path]:
        return (
            self.haigh_output_root / "SEP_cross_validation" / "sep_toy_cross_validation_best.json",
            self.haigh_output_root
            / "MTObjects_cross_validation"
            / "mtobjects_toy_cross_validation_best.json",
        )

    def reload_optimised_parameters(self) -> None:
        """Reload only winners produced by this revised source-injection experiment."""
        sep_path, mto_path = self._haigh_winner_paths()
        available_sep = sep_path if sep_path.exists() else None
        available_mto = mto_path if mto_path.exists() else None
        try:
            sep_defaults = base.production_params(
                available_sep,
                base.core.AZURE_MEAN_PARAMS["SEP"],
                base.sep_batch.load_best_params,
            )
            mto_defaults = base.production_params(
                available_mto,
                base.core.AZURE_MEAN_PARAMS["MTObjects"],
                base.mto_batch.load_best_params,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Parameter reload failed", str(exc))
            return
        self.sep_best, self.mto_best = available_sep, available_mto
        self.sep_defaults, self.mto_defaults = sep_defaults, mto_defaults
        self.reset_parameters()
        sep_source = str(available_sep) if available_sep else "built-in defaults (new winner pending)"
        mto_source = str(available_mto) if available_mto else "built-in defaults (new winner pending)"
        self.source_var.set(f"Haigh-aligned parameters: SEP {sep_source}; MTObjects {mto_source}")
        self.status.set("Reloaded the latest winners from the revised source-injection experiment.")

    def on_click(self, event) -> None:
        messagebox.showinfo(
            "Saved physical sources only",
            "Manual legacy Gaussian toys are disabled in this revised reviewer. "
            "Choose a saved Training or Validation arrangement, then press Calculate.",
        )

    def clear_toys(self) -> None:
        messagebox.showinfo(
            "Use Toys IN / OUT",
            "The saved physical sources are immutable. Use the Toys IN / OUT button to compare with the clean baseline.",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=display.DEFAULT_MANIFEST)
    parser.add_argument("--injection-manifest", type=Path)
    parser.add_argument("--pc", choices=sorted(PC_RESEARCH_FOLDERS), default=default_pc())
    parser.add_argument("--sep-best", type=Path)
    parser.add_argument("--mto-best", type=Path)
    parser.add_argument("--mtobjects-root", type=Path)
    return parser.parse_args()


def main() -> int:
    HaighAlignedReviewer(parse_args()).mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
