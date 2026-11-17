SELECT COUNT(*) AS candidate_rows, COUNT(DISTINCT m.object_id) AS distinct_objects FROM dr1.mer_morphology_deep_survey m WHERE m.data_set_release='DR1_R2'
AND (m.smooth_or_featured_featured_or_disk + m.smooth_or_featured_smooth) > 0
AND (m.smooth_or_featured_featured_or_disk + m.smooth_or_featured_smooth) < 1.0E100
AND m.smooth_or_featured_featured_or_disk >= 0
AND m.smooth_or_featured_smooth >= 0
AND (m.smooth_or_featured_featured_or_disk) - 0.8 * (m.smooth_or_featured_featured_or_disk + m.smooth_or_featured_smooth) >= 0
AND (m.disk_edge_on_no + m.disk_edge_on_yes) > 0
AND (m.disk_edge_on_no + m.disk_edge_on_yes) < 1.0E100
AND m.disk_edge_on_no >= 0
AND m.disk_edge_on_yes >= 0
AND (m.disk_edge_on_no) - 0.8 * (m.disk_edge_on_no + m.disk_edge_on_yes) >= 0
AND (m.has_spiral_arms_yes + m.has_spiral_arms_no) > 0
AND (m.has_spiral_arms_yes + m.has_spiral_arms_no) < 1.0E100
AND m.has_spiral_arms_yes >= 0
AND m.has_spiral_arms_no >= 0
AND (m.has_spiral_arms_yes) - 0.8 * (m.has_spiral_arms_yes + m.has_spiral_arms_no) >= 0
AND (m.bar_strong + m.bar_weak + m.bar_no) > 0
AND (m.bar_strong + m.bar_weak + m.bar_no) < 1.0E100
AND m.bar_strong >= 0
AND m.bar_weak >= 0
AND m.bar_no >= 0
AND (m.bar_strong + m.bar_weak) - 0.8 * (m.bar_strong + m.bar_weak + m.bar_no) >= 0