SELECT COUNT(DISTINCT w.object_id) AS overlapping_candidates FROM dr1.mer_morphology_wide_survey w JOIN dr1.mer_morphology_deep_survey d ON w.object_id=d.object_id WHERE w.data_set_release='DR1_R2'
AND (w.smooth_or_featured_featured_or_disk + w.smooth_or_featured_smooth) > 0
AND (w.smooth_or_featured_featured_or_disk + w.smooth_or_featured_smooth) < 1.0E100
AND w.smooth_or_featured_featured_or_disk >= 0
AND w.smooth_or_featured_smooth >= 0
AND (w.smooth_or_featured_featured_or_disk) - 0.8 * (w.smooth_or_featured_featured_or_disk + w.smooth_or_featured_smooth) >= 0
AND (w.disk_edge_on_no + w.disk_edge_on_yes) > 0
AND (w.disk_edge_on_no + w.disk_edge_on_yes) < 1.0E100
AND w.disk_edge_on_no >= 0
AND w.disk_edge_on_yes >= 0
AND (w.disk_edge_on_no) - 0.8 * (w.disk_edge_on_no + w.disk_edge_on_yes) >= 0
AND (w.has_spiral_arms_yes + w.has_spiral_arms_no) > 0
AND (w.has_spiral_arms_yes + w.has_spiral_arms_no) < 1.0E100
AND w.has_spiral_arms_yes >= 0
AND w.has_spiral_arms_no >= 0
AND (w.has_spiral_arms_yes) - 0.8 * (w.has_spiral_arms_yes + w.has_spiral_arms_no) >= 0
AND (w.bar_strong + w.bar_weak + w.bar_no) > 0
AND (w.bar_strong + w.bar_weak + w.bar_no) < 1.0E100
AND w.bar_strong >= 0
AND w.bar_weak >= 0
AND w.bar_no >= 0
AND (w.bar_strong + w.bar_weak) - 0.8 * (w.bar_strong + w.bar_weak + w.bar_no) >= 0
AND d.data_set_release='DR1_R2'
AND (d.smooth_or_featured_featured_or_disk + d.smooth_or_featured_smooth) > 0
AND (d.smooth_or_featured_featured_or_disk + d.smooth_or_featured_smooth) < 1.0E100
AND d.smooth_or_featured_featured_or_disk >= 0
AND d.smooth_or_featured_smooth >= 0
AND (d.smooth_or_featured_featured_or_disk) - 0.8 * (d.smooth_or_featured_featured_or_disk + d.smooth_or_featured_smooth) >= 0
AND (d.disk_edge_on_no + d.disk_edge_on_yes) > 0
AND (d.disk_edge_on_no + d.disk_edge_on_yes) < 1.0E100
AND d.disk_edge_on_no >= 0
AND d.disk_edge_on_yes >= 0
AND (d.disk_edge_on_no) - 0.8 * (d.disk_edge_on_no + d.disk_edge_on_yes) >= 0
AND (d.has_spiral_arms_yes + d.has_spiral_arms_no) > 0
AND (d.has_spiral_arms_yes + d.has_spiral_arms_no) < 1.0E100
AND d.has_spiral_arms_yes >= 0
AND d.has_spiral_arms_no >= 0
AND (d.has_spiral_arms_yes) - 0.8 * (d.has_spiral_arms_yes + d.has_spiral_arms_no) >= 0
AND (d.bar_strong + d.bar_weak + d.bar_no) > 0
AND (d.bar_strong + d.bar_weak + d.bar_no) < 1.0E100
AND d.bar_strong >= 0
AND d.bar_weak >= 0
AND d.bar_no >= 0
AND (d.bar_strong + d.bar_weak) - 0.8 * (d.bar_strong + d.bar_weak + d.bar_no) >= 0