> Current status (29 October 2026): all 19 centre-pilot reviews are complete. See [reviewed geometry policy](REVIEW_ADOPTION_MER_VIS.md) for adoption statuses and the sensitivity experiment.

# MER VIS centre-acceptance re-review

Prepared 28 October 2026. The completed 58-galaxy review and original geometry remain preserved.

## Open the new round

Run the usual launcher:

```powershell
& "C:\Users\gordo\Documents\Github\PythonScripts\Euclid\review_MER_VIS\Start MER VIS Review.cmd"
```

It now opens the separate 19-galaxy centre-policy round. The original completed review remains available through **Start Original MER VIS Review.cmd**. New assessments are saved under `review_MER_VIS/saved_reviews_centre_v3`; the earlier records remain under `review_MER_VIS/saved_reviews`. The new round starts at 0 reviewed.

## Changes adopted for this pilot

- Every ellipse is checked against one explicit reference centre, in native pixels and arcseconds. The reference is not replaced with the mean of subsequently selected drifting ellipses. Its origin is recorded.
- Default pilot tolerance: `offset ≤ min(3 native pixels, max(1 native pixel, 0.05 × semi-major axis in native pixels))`. This is adjustable under **Explore the review thresholds → Centre acceptance screen**. Numerical limits need validation on this round; they are not a calibrated universal physical threshold.
- Accepted and marginal candidates use the same centre gate. Numerical relaxation cannot override centre displacement. Rejected samples remain available with their rejection reason and displacement in the point tooltip.
- Fixed-centre recovery fits were made for 18 cases. The reference for each previously reviewed example is the adopted centre assessed in that review. Six new examples have automatic, explicitly unverified references requiring visual confirmation. One previously uncertain-centre case retains its old trial rather than receiving an automatic new fit.
- Sparse sampling and PA variation are checked independently; sparse sampling no longer hides PA variation. Near-face-on PA ambiguity remains informational.
- The new automatic batch entry point `fit_centred_MER_VIS_geometry.py` applies the same reference and policy. It tests a free-centre fit and can retry at the fixed reference; an explicit --ids, --limit or --all choice is required. It writes separate trial outputs. The full 2,777-object library has not been rerun or adopted.

## What to inspect

1. Turn on **Ellipses** and **Centre markers**. Small coloured crosses identify the centres of displayed ellipses, alongside the larger adopted/catalogue/proposed markers. Check the reference against the nucleus.
2. Turn on **Show diagnostic ranges** when needed. The additional **Ellipse centre displacement** plot is shown only when centre diagnostics are relevant. The dashed red curve is the tolerance; measurements above it are excluded. Defaults still start with diagnostics and ellipse overlays off.
3. A fixed-centre trial has zero drift by constraint. Zero drift does not demonstrate a correct centre, good ellipse shape, or reliable disc PA. The original quality checks still apply.
4. Use **Previous assessment (preserved)** to read the earlier decisions and notes. The geometry table adds **Previous reviewed selection** beside the original automatic result and the current trial. The previous values are historical references, not recalculated to match the new filter.
5. Open **science / model / residual diagnostic**. Science and the Photutils elliptical model share a display stretch. Residuals show science minus model over the fitted region at ±5 sky-noise units; red is positive, blue negative, and white is invalid/outside model coverage. Bars, arms, neighbours and other real structure can leave residuals. A central residual pattern can motivate a centre check, but is not a unique diagnosis of miscentring.
6. If the nucleus reference needs adjustment, use **Pick centre**, recompute, and then assess the newly displayed trial. Changing only the yellow proposed cross does not change the fit.
7. Save a fresh assessment for this round. Previous notes remain available in the read-only panel; the new note box starts blank to distinguish the new assessment. Usable structure, a convincing bar and a trustworthy numerical disc PA need separate judgements.

## First four priority cases

| Galaxy | Previous reviewed PA | Current trial PA | Current selected PA RMS | Selected disc ellipses |
|---|---:|---:|---:|---:|
| -663928688473758026 | 42.68° | 61.38° | 20.55° | 3 |
| 2756030807655229287 | 59.62° | 47.74° | 25.84° | 3 |
| -595029565493921205 | 55.31° | 55.69° | 11.22° | 5 |
| -537890362287224823 | 63.69° | 62.64° | 15.36° | 5 |

All four still show PA variation. They are deliberately first in the queue; fixing ellipse centres has not been treated as proof that the whole disc has one reliable orientation.

## Re-review list

| Galaxy | Group | Reason |
|---|---|---|
| -663928688473758026 | Centre acceptance — priority re-review | Previous review / geometry uncertainty; validate centre and fixed-centre shape |
| 2756030807655229287 | Centre acceptance — priority re-review | Previous review / geometry uncertainty; validate centre and fixed-centre shape |
| -595029565493921205 | Centre acceptance — priority re-review | Previous review / geometry uncertainty; validate centre and fixed-centre shape |
| -537890362287224823 | Centre acceptance — priority re-review | Previous review / geometry uncertainty; validate centre and fixed-centre shape |
| -518633776290631360 | Centre acceptance — priority re-review | Previous review / geometry uncertainty; validate centre and fixed-centre shape |
| 2681494150647395085 | Centre acceptance — priority re-review | Previous review / geometry uncertainty; validate centre and fixed-centre shape |
| 2654474268655808169 | Centre acceptance — priority re-review | Previous review / geometry uncertainty; validate centre and fixed-centre shape |
| -586374330510251740 | Centre acceptance — priority re-review | Previous review / geometry uncertainty; validate centre and fixed-centre shape |
| -524824554283124036 | Centre acceptance — priority re-review | Previous review / geometry uncertainty; validate centre and fixed-centre shape |
| 2645436353651870062 | Centre acceptance — priority re-review | Previous review / geometry uncertainty; validate centre and fixed-centre shape |
| 2697242050653408730 | Centre acceptance — priority re-review | Previous review / geometry uncertainty; validate centre and fixed-centre shape |
| -524724591298089738 | Centre acceptance — clean references | Previously clean reference; confirm no degradation |
| 2724315227685324582 | Centre acceptance — clean references | Previously clean reference; confirm no degradation |
| -615088650482896879 | Centre acceptance — new validation examples | new_clean; centre needs visual confirmation |
| 2654162178650796134 | Centre acceptance — new validation examples | new_clean; centre needs visual confirmation |
| -646641404494431826 | Centre acceptance — new validation examples | new_centre; centre needs visual confirmation |
| 2690070926643224042 | Centre acceptance — new validation examples | new_centre; centre needs visual confirmation |
| -599118107493216367 | Centre acceptance — new validation examples | new_geometry; centre needs visual confirmation |
| 2634901320657220727 | Centre acceptance — new validation examples | new_geometry; centre needs visual confirmation |

## Verification and limits

- The 18 new fits completed with 18 science/model/residual diagnostics. One uncertain-centre comparison is retained without a new automatic refit. All 19 cases are pending human review.
- Checks cover native-pixel reference/limit consistency in Python and JavaScript, zero/one/two-ellipse handling, marginal-pool gating, independent PA/sampling flags, saved review round trips, local API protections, original FITS read-only handling, SVG render logic, original calculations, and all 19 served campaign cases.
- The synthetic reference-centre test recovered the expected PA and inclination. The batch entry point was also exercised with a known synthetic reference.
- Full browser automation was unavailable in this session. Served data, rendered SVG generation and diagnostic PNGs were checked; browser layout still needs confirmation when the tool is opened.
- Original review JSON SHA-256: `53992fbbb9f67991c03e65842595d2644295324a185f4a2475a478b5f121b69d`. The original master-geometry manifest and the completed review were not modified.
- Trial calculations and the pilot tolerance must be validated before any full-library science adoption.
