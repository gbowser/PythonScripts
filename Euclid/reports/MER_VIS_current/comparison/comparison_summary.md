# MER VIS geometry compared with the supplied method

20 October 2026

This compares the current measurements and quality classifications with the separately supplied fitted table. All 2777 object IDs match. Missing bar measurements are excluded rather than replaced with zero. This document contains no comparison with earlier pipeline versions.

| Subset | Disc PA median absolute difference | Bar PA median absolute difference | Inclination median absolute difference |
|---|---:|---:|---:|
| All common measurements | 2.76° (n=2773) | 0.45° (n=2292) | 2.37° (n=2773) |
| Current measurements with no counted flags | 0.71° (n=93) | 0.39° (n=93) | 1.90° (n=93) |
| Neither table has counted flags | 0.55° (n=81) | 0.38° (n=81) | 1.91° (n=81) |

PA is North towards East modulo 180°. Signed axial differences wrap into [-90°,90°). No additional 90° adjustment is applied to the supplied fitted angles; the adopted +90° applies only to the Euclid detection-catalogue comparison.

Our inclination uses a circular thin disc (q0=0); the supplied method uses q0=0.2. These are consistency comparisons using the same images and Photutils, not independent accuracy measurements.

The no-counted-flags subsets use the current sparse-sampling and radial-PA-variation rules. Adjacent ellipse samples are correlated. Nearly-face-on discs are informational and exempt from both PA review flags.

448 common-fit objects differ by over 20° in at least one available quantity. See large_differences_for_review.csv. The joined CSV retains all current values, catalogue names, flags and signed differences.