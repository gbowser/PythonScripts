# Reviewed geometry and centre confirmation

The current centre-pilot round has 19 completed assessments. Saved visual decisions
and numerical measurements remain separate. No fitting limits were globally relaxed.

## Centre confirmation

“Looks correct” confirms the centre of the saved fit, identified by its refit ID and
reference X/Y in native FITS pixels. Selecting another fit or changing the reference
does not carry that confirmation forward. Original automatic-centre provenance is
retained. A matching visual confirmation resolves the workflow warning “Centre
reference unverified”; it does not erase the original warning from the audit export.

Fixed-centre fits have zero centre drift by construction. With no excluded samples,
centre consistency is informational, not an active shape-quality warning. A correct
centre is necessary but does not prove the selected ellipses trace the outer disc.

## Geometry adoption

The evidence table shows the adoption status of the **saved selection**. Changes to
intervals need a new saved assessment before they affect that status.

| Status | Meaning |
|---|---|
| reviewed_supported | Disc and centre approved; complete geometry and current screens pass. Eligible for the next automatic processing stage, not a claim of independently verified truth. |
| reviewed_provisional | Disc visually approved and complete values available, with numerical cautions, face-on sensitivity, or an unsupported bar PA. Retained for analysis; requires deliberate handling before automatic deprojection. |
| provisional_incomplete_disc | Disc visually apparent but insufficient numerical evidence for a complete adopted disc geometry. Raw provisional PA remains in the selected-measurement columns. |
| withheld_disc_uncertain | Disc is uncertain or not approved. No disc geometry is adopted for automatic transformation. Bar classification and measurements remain available separately. |
| withheld_centre_unconfirmed | The current fit/reference lacks a matching positive centre assessment. |
| unreviewed | No completed assessment in the selected review source. This does not overwrite earlier reviews stored in another round. |

Six selected disc ellipses remain a preferred target. Fewer do not automatically
invalidate a visually approved disc: at least three can supply provisional PA and
inclination. Three adjacent isophotes are not three independent observations. With
three radii there are two gaps, so the largest gap is necessarily at least 50% of
the span; a 53% gap adds little evidence beyond the small count itself.

The 10° PA-RMS and 0.15 ellipticity-range screens remain unchanged. Near-face-on is
informational; a poorly determined PA may have less effect on deprojection, but its
effect must be checked rather than assumed absent. Two bar samples can support a
visual judgement but do not become a robust automatic PA measurement.

## Files and repeatable commands

`export_MER_VIS_reviewed_geometry.py` writes a new library manifest, preserving all
original catalogue columns and adding reviewed measurements, decisions, provenance,
raw/effective warnings and adopted geometry. `automatic_deprojection_ready` is the
explicit gate for automatic face-on, bar-aligned processing. Uncertain or incomplete
disc values must not be filled from an unrelated whole-source Euclid proxy.

The current export covers all 2,777 library rows and applies this round's 19 saved
assessments. The original 58-entry review is preserved separately, not silently
merged. Unreviewed rows retain the existing pipeline measurements.

`test_MER_VIS_centre_sensitivity.py` produces isolated ±1-native-pixel fixed-centre
trials for five identified cases. It never updates saved review files or latest-fit
indexes. The accompanying experiment also shifts selected radial interval boundaries
by 10% of their width. These are sensitivity probes, not confidence intervals or a
calibration of centre uncertainties.

See `../reports/MER_VIS_review_2026-10-29/MER_VIS_adopted_review_policy_and_sensitivity.md`
for outcomes, numerical comparisons and remaining exceptions. No further broad
manual review is requested; unresolved cases remain explicitly provisional/withheld.
