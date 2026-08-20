"""Apply the Phase 2 Spike Gate component selector to batch products."""

from __future__ import annotations

import numpy as np

import spike_gate_objective


def filter_products(data, geometry, params, products, tool, profile_width_pixels: int = 3):
    """Return a copy of SEP/MTObjects products containing gate-supported components only."""
    science = np.asarray(data, dtype=float)
    radius_arcsec = tool.display.profile_radius_pixels(science, geometry) * geometry["pixel_scale"]
    gate_image, _residual, _nonfinite = tool.prepare_detection_image(
        science, str(params.get("spike_gate_detect_on", "residual"))
    )
    gate_view, x_axis, y_axis = tool.display.deproject_bar_aligned_cutout(
        gate_image, geometry, radius_arcsec
    )
    half_width = 0.5 * int(profile_width_pixels) * geometry["pixel_scale"]
    radii, intensity = tool.display.bar_major_axis_profile(gate_view, x_axis, y_axis, half_width)
    spikes = tool.detect_profile_spikes(
        radii,
        intensity,
        excess_fraction=float(params["spike_excess_fraction"]),
        neighbour_inner_arcsec=float(params["spike_neighbour_inner_arcsec"]),
        neighbour_outer_arcsec=float(params["spike_neighbour_outer_arcsec"]),
        side_offset_samples=int(params["spike_side_offset_samples"]),
        side_drop_fraction=float(params["spike_side_drop_fraction"]),
        center_exclusion_arcsec=float(params.get("spike_center_exclusion_arcsec", params.get("exclude_center_pixels", 0.0))),
    )
    spikes = tool.expand_boolean_mask(spikes, int(params["spike_window_samples"]))

    raw_mask = np.asarray(products["mask"], dtype=bool)
    def labels_to_view(component_labels):
        view, _x, _y = tool.display.deproject_bar_aligned_cutout(
            np.asarray(component_labels, dtype=float), geometry, radius_arcsec, order=0
        )
        return np.where(np.isfinite(view), view, 0.0)

    mask, metrics = spike_gate_objective.retain_gate_supported_components(
        raw_mask, labels_to_view, x_axis, y_axis, spikes, half_width
    )
    cleaned = np.array(science, copy=True)
    finite_unmasked = np.isfinite(science) & ~mask
    replacement = float(np.nanmedian(science[finite_unmasked])) if np.any(finite_unmasked) else 0.0
    cleaned[mask] = replacement

    updated = dict(products)
    updated["mask"] = mask
    updated["cleaned"] = cleaned
    updated["spike_samples"] = spikes
    updated["phase2_component_metrics"] = metrics
    segmentation = np.asarray(products.get("filtered_segmentation", np.zeros(mask.shape, dtype=int)))
    rows = []
    for row in products.get("rows", []):
        item = dict(row)
        label_value = int(item.get("label", 0))
        item["kept"] = bool(label_value > 0 and np.any(mask & (segmentation == label_value)))
        rows.append(item)
    updated["rows"] = rows
    return updated
