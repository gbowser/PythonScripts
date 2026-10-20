# Comparison of Codex geometry with the supplied VIS manifest

20 October 2026

## Main findings

All 2777 rows match one to one by exact object ID. All coordinates and FITS filenames match. Neither source was modified. There is no evidence of a global 90-degree or sign reversal between these two fitted-geometry tables. No additional Euclid catalogue PA correction was applied to the supplied fitted angles.

The supplied file reports 2776 ok results and one failure, compared with 2207 provisional fits and 570 failures in the original Codex run. It provides an ok result for 569 of our failed fits. A returned result is not independent evidence of correctness: the fitting, masking, radial selections and acceptance rules differ. Its status ok also does not mean that a bar was detected.

## Numerical comparison

Differences are Codex minus supplied. PA differences wrap into [-90,90) because ellipse axes have a 180-degree ambiguity. Values below are median absolute differences, not uncertainties.

| Subset | Disc PA | Bar PA | Inclination |
|---|---:|---:|---:|
| All common results | 9.56° (n=2207) | 1.60° (n=2164) | 3.89° (n=2207) |
| Codex revised unflagged | 4.75° (n=601) | 1.96° (n=590) | 3.28° (n=601) |
| Both unflagged | 2.84° (n=436) | 2.09° (n=432) | 3.02° (n=436) |

The revised Codex subset has 601 fits: face-on is informational and unstable disc PA is ignored for face-on objects. Both unflagged additionally requires the supplied flags field to be empty (436 discs/inclinations; 432 available bars). Flag definitions differ between pipelines, so this is a screening intersection, not an independently validated sample.

| Quantity, all common results | Within 10° | Difference >20° | 90th percentile absolute difference |
|---|---:|---:|---:|
| Disc PA | 1134/2207 (51.4%) | 698 | 52.22° |
| Bar PA | 1954/2164 (90.3%) | 114 | 9.63° |
| Inclination | 1705/2207 (77.3%) | 196 | 18.67° |

## Why inclination differs

Our original inclination assumes an infinitely thin circular disc: i = acos(q), with q0=0. The supplied values closely match the finite-thickness formula i = acos(sqrt((q²-q0²)/(1-q0²))) with q0=0.2, clipping to the physical range. Here q=1-disc_eps. This is inferred from the numbers, not confirmed by supplied source code. The median absolute residual to that formula is only 0.031° across 2776 rows, consistent with rounding. The thin-disc formula instead has a median residual of 1.27°.

Across common fits, our inclination is lower by a median signed 2.44°. Recalculating the supplied inclinations with q0=0 reduces the median absolute difference from 3.89° to 3.47°, with median signed difference -0.90°. Remaining differences arise from different fitted axis ratios; the thickness assumption is not the whole explanation.

## Why disc and bar results differ

Disc ranges differ: our lower and upper disc boundaries are farther out by median signed 0.90 and 0.85 arcsec respectively. Different radial choices can sample different arms, rings, bulge/bar contamination or outer-disc contours. This is a measured methodological difference, not proof of the physical cause of each outlier.

The supplied methods are standard (2719), recentred (40), recentred_relaxed (9), relaxed (6), smoothed (2), and one blank failed entry. Thus 57 ok results explicitly record an alternative to standard fitting. The field names suggest changed centres, criteria or smoothing, but exact implementation requires the generating code.

The supplied bar classifications are A (2577), B (132), no_bar_detected (67), plus one blank failed row. A/B definitions were not included, so they are not treated as equivalent to our quality flags. Among our common fits, 43 supplied bar angles are missing; they are excluded, not set to zero.

Overall bar agreement is strong and direct: a global +90° would worsen its median absolute difference from 1.60° to 88.40°. For disc PA it would worsen agreement from 9.56° to 80.44°. This fitted-manifest comparison is separate from the raw Euclid detection-catalogue convention issue.

## Largest disc disagreements

| Galaxy ID | Codex disc PA | Supplied disc PA | Signed difference |
|---|---:|---:|---:|
| 2726854926652655657 | 71.49° | 161.20° | -89.71° |
| -617725912471873623 | 67.47° | 157.80° | +89.67° |
| -621114740476807958 | 89.09° | 179.70° | +89.39° |
| 2676192291642798215 | 133.51° | 42.90° | -89.39° |
| -627315340480918453 | 124.17° | 33.30° | -89.13° |

## Review priorities

836 common-fit galaxies differ by more than 20° in at least one available quantity. The separate review CSV lists them; its ordering uses the largest PA difference, rather than claiming a scientific quality ranking.

Review the 569 recovered cases and large disc disagreements using the images and both sets of radial selections. Inspect near-face-on disc disagreements as orientation ambiguities rather than automatic quality defects. Review large bar differences independently; close disc agreement does not guarantee a good bar fit. Do not replace the adopted geometry solely because one pipeline returns more results.

The supplied CSV contains no explicit angle-convention definition or method documentation. Direct agreement strongly supports compatible sky-PA conventions, particularly for bars, but cannot prove algorithmic independence. The supplied errors were not combined with our radial scatter as formal significance tests because these are different error measures and the fits use the same images.

## Sources

Supplied: C:\Users\gordo\Downloads\Euclid_VIS_disc_bar_PA_manifest.csv

Codex: D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry\MER_VIS_local_geometry_manifest.csv

The full joined CSV preserves both sets of values, flags, methods, ranges and errors, and adds signed differences. summary.json records checksums and machine-readable statistics.