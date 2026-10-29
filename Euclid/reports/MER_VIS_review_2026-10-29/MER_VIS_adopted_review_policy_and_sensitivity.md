# MER VIS adopted review policy and sensitivity results

29 October 2026. All 19 centre-pilot assessments are complete. The latest review changes one case from unassessed to visually usable; the recommendations otherwise stand.

## Latest galaxy: 2697242050653408730

The reviewer selected outer disc contours because the inner contours follow spiral structure. The saved interval contains two accepted disc ellipses. Disc PA is 127.95° (provisional), bar PA is 74.33°, and no inclination is available under the current minimum-three rule. The centre is now visually confirmed. This is a visual recovery, not a complete deprojection measurement. Status: provisional_incomplete_disc. No inclination has been invented from the two samples.

## Changes adopted

- Confirmation is tied to an exact refit ID and centre reference coordinates. Six previously unverified-centre workflow warnings are resolved by the matching saved Looks correct assessments; their raw provenance is preserved.
- Fixed-centre consistency with zero exclusions is informational. It is not evidence that the physical centre was independently recovered.
- Sparse sampling is a caution, not automatic deletion of visually approved values. The six-sample target and 10°/0.15 PA/ellipticity thresholds remain unchanged; records carry adoption status separately from raw warnings.
- The reviewed export keeps uncertain discs out of adopted deprojection geometry, while retaining the FITS paths, raw measurements and visual bar decisions.
- The full 2,777-row library was passed through the new adoption/export stage. It retains every original catalogue column and adds reviewed selections, adoption reasons, raw/effective issues, reference coordinates and sensitivity outcomes.
- This export applies the 19 current-round reviews. The original 58-entry review is preserved separately. The other 2,758 rows are unreviewed in this round; they are not refitted or silently rejected as bad galaxies.

## Current-round outcomes

| Status | Count |
|---|---:|
| withheld_disc_uncertain | 4 |
| reviewed_supported | 5 |
| reviewed_provisional | 9 |
| provisional_incomplete_disc | 1 |

There are 15 visually usable discs and four uncertain discs; all 19 bars are convincing by visual assessment. Eighteen centres are marked correct, one uncertain. Five complete selections pass the current screens and are eligible for the next automatic processing stage. Nine complete selections remain provisional; one additional selection lacks inclination. These are readiness states, not counts of physically correct versus incorrect galaxies.

## Sensitivity experiment

Twenty independent Photutils trial fits were run: the adopted centre shifted by ±1 native pixel along each pixel axis for five galaxies. Each trial used a fixed centre and the same physical disc/bar radial bounds as the reviewed selection. Six additional interval probes per galaxy moved either interval edge, or both edges together, by 10% of the saved disc interval width, without refitting. All 19 baseline selected geometries reproduce their saved numerical values to 1e-9.

PA differences use the shortest axial difference modulo 180°. The table gives the maximum absolute departure from the reviewed baseline among the probes, not a standard error or confidence interval. Counts of accepted samples can change between trials.

| Galaxy ID | Centre-probe max ΔPA | Centre-probe max Δi | Interval-probe max ΔPA | Interval-probe max Δi |
|---|---:|---:|---:|---:|
| 2681494150647395085 | 34.41° | 9.52° | 63.84° | 3.12° |
| -524824554283124036 | 0.42° | 0.34° | 8.55° | 0.10° |
| -599118107493216367 | 2.53° | 10.05° | 0.09° | 0.90° |
| -537890362287224823 | 1.65° | 0.92° | 7.80° | 0.52° |
| -663928688473758026 | 48.65° | 2.48° | 11.47° | 0.24° |

- **2681494150647395085:** strong sensitivity remains. Retain provisional geometry, not an automatic transform. A single representative disc PA is not secure from these selected contours.
- **−599118107493216367:** disc PA looks stable but inclination changes by 10.05° under the centre probes. Five samples over only 0.313 arcsec do not establish a representative outer-disc shape. Retain provisional geometry.
- **−524824554283124036:** the chosen outer interval is stable to the tested one-pixel shifts; maximum PA change is 0.42° and inclination change 0.34°. Boundary changes produce up to 8.55° PA change. This supports retaining the visual choice with limited-sampling status, despite its large difference from the Euclid whole-source detection shape.
- **−537890362287224823:** the mean disc geometry is relatively stable to these probes, but radial PA variation remains, and the selected bar still has two samples with no supported automatic bar PA. Keep visual bar confirmation separate from its missing numerical angle.
- **−663928688473758026:** disc PA is weakly constrained, as expected from the round selected disc. One centre probe leaves only two disc samples, with no inclination. The reported 48.65° maximum PA shift includes this incomplete-disc trial; complete-geometry probes have smaller PA changes. Near-face-on remains informational, but incomplete measurements cannot be transformed.

### Near-face-on transformed-image check

`MER_VIS_near_face_on_sensitivity.png` compares the reviewed image with the centre probes using the existing WCS-based face-on/bar-horizontal transformation, the actual trial centre, one common output grid, and one common display stretch. The incomplete probe is left blank. For the three complete probes, maximum native-input mapping changes across the output circle are 1.33, 3.70 and 3.45 pixels; RMS changes are 1.09, 1.68 and 1.60 pixels. These include the deliberately imposed centre translation and changes to inclination and bar alignment; they are diagnostic displacements, not formal uncertainty estimates. The visual effect is smaller than the PA numbers alone suggest, but is not zero. No adopted FITS image was overwritten.

## Remaining disposition

The four uncertain discs remain withheld: 2756030807655229287, −518633776290631360, 2654474268655808169 and 2645436353651870062. Their bar classifications remain convincing. The newly completed galaxy 2697242050653408730 remains incomplete rather than uncertain, because the reviewer approves the visible disc but only two selected numerical contours support it.

Use these labelled cases as regression checks. Process supported selections automatically; handle provisional complete selections deliberately and keep incomplete/uncertain discs out of automatic deprojection. Request additional manual review only for new failures or scientifically material sensitivity, rather than another broad campaign. The present changes do not justify a blind full-library refit or global loosening of thresholds.

## Data and implementation

- `MER_VIS_reviewed_adoption_manifest.csv` / `.json`: full-library overlay with original measurements and explicit reviewed/adopted fields.
- `MER_VIS_sensitivity_results.json`: selected-profile metrics for every experiment.
- `MER_VIS_near_face_on_sensitivity.png`: transformed science preview.
- `source_reviews_completed.json`: immutable review snapshot supporting this report.
- Installed review tool: confirmation-aware status display and CSV export; raw fitting numbers and user notes remain unchanged.

The experiment used 10° PA and 5° inclination changes as attention markers for reporting only. The inclination marker is exploratory, not a newly calibrated quality cut. Centre tolerance calibration remains unresolved because most pilot fits imposed the centre. Euclid whole-source detection shape remains a comparison, not ground truth for a selected outer-disc interval.