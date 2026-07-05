# Classifier Agreement Analysis

Source workbook: `D:\Dropbox\Public Documents\UCLAN\MSc Research\Shoulder_Recognition_Erwin\PE_VPD_galaxy_classifications_with_definitions.xlsx`
Rows in source sheet: 182
Rows with valid 4-class human labels: 180
Rows with usable binary SRA labels: 171
Rows with both valid human labels and usable binary SRA labels: 170

## Executive Summary

- Human unanimous agreement across PE, VPD, and GB is 72.2% on the 180 galaxies with valid 4-class human labels.
- Fleiss' kappa for the three human classifiers is 0.716, a chance-corrected measure of multi-rater agreement.
- Pairwise human agreement is strongest for PE vs VPD (kappa 0.815) and weakest for GB vs PE (kappa 0.639).
- Using GB visual class as the row grouping, PE and VPD both match GB most often for `Exp` (83.3%) and least often for `Two-slope (2S)` (41.7%).
- The class-dependence of unanimous human agreement is tested with chi-square: chi2=11.54, dof=3, p=0.009126.
- Against the human-majority shoulder/non-shoulder label, SRA has accuracy 72.9%, balanced accuracy 76.7%, sensitivity for shoulders 87.3%, specificity for no-shoulders 66.1%, and kappa 0.463.
- For shoulder detection specifically, SRA is more sensitive than conservative: it misses 7 human-majority shoulder galaxies, but calls shoulders in 39 human-majority non-shoulder galaxies.
- When all three humans identify shoulders, SRA calls shoulders in 91.8%; when no humans identify shoulders, SRA still calls shoulders in 32.3%.
- Among non-shoulder human-majority classes, SRA shoulder calls are most frequent for `Exp` (35.4%).

## Label Handling

- Human agreement uses PE profile label, VPD profile label, and GB visual class.
- Human profile classes are canonicalized to Peak+Sh, Exp, Flat-top (FT), and Two-slope (2S).
- GB rows marked Unclear are retained in the cleaned-label CSV but excluded from the 4-class human-agreement statistics.
- SRA is treated as binary: Shoulders vs No Shoulders. SRA rows marked Too Noisy are excluded from binary SRA agreement metrics.
- Cleaned labels are written to `cleaned_classifier_labels.csv`.

## Human Pairwise Agreement

| pair | n | exact agreement | cohen kappa |
| --- | --- | --- | --- |
| PE vs VPD | 182 | 0.879 | 0.815 |
| GB vs PE | 180 | 0.756 | 0.639 |
| GB vs VPD | 180 | 0.800 | 0.703 |

## Human Agreement by GB Class

| GB class | n | PE matches GB | VPD matches GB | PE and VPD both match GB | PE/VPD agree with each other |
| --- | --- | --- | --- | --- | --- |
| Peak+Sh | 75 | 0.747 | 0.773 | 0.733 | 0.933 |
| Exp | 60 | 0.850 | 0.950 | 0.833 | 0.867 |
| Flat-top (FT) | 33 | 0.727 | 0.697 | 0.606 | 0.758 |
| Two-slope (2S) | 12 | 0.417 | 0.500 | 0.417 | 0.917 |

## Class-Specific One-vs-Rest Agreement

| class | PE vs GB | PE vs VPD | VPD vs GB |
| --- | --- | --- | --- |
| Exp | 0.552 | 0.822 | 0.669 |
| Flat-top (FT) | 0.652 | 0.682 | 0.737 |
| Peak+Sh | 0.741 | 0.914 | 0.754 |
| Two-slope (2S) | 0.535 | 0.692 | 0.545 |

## SRA Binary Agreement

| reference | n | tp | fn | fp | tn | accuracy | balanced_accuracy | sensitivity_shoulders | specificity_no_shoulders | precision_shoulders | kappa |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PE | 171 | 48 | 5 | 40 | 78 | 0.737 | 0.783 | 0.906 | 0.661 | 0.545 | 0.479 |
| VPD | 171 | 47 | 9 | 41 | 74 | 0.708 | 0.741 | 0.839 | 0.643 | 0.534 | 0.421 |
| GB | 170 | 54 | 15 | 33 | 68 | 0.718 | 0.728 | 0.783 | 0.673 | 0.621 | 0.438 |
| Human majority | 170 | 48 | 7 | 39 | 76 | 0.729 | 0.767 | 0.873 | 0.661 | 0.552 | 0.463 |

## SRA Shoulder Identification

This section treats the humans as shoulder detectors by mapping `Peak+Sh` to `Shoulders` and all other profile classes to `No Shoulders`. The strongest reference is the human-majority binary label.

- Human-majority comparison: TP=48, FN=7, FP=39, TN=76.
- Sensitivity to human-majority shoulders is 87.3%; specificity to human-majority non-shoulders is 66.1%.
- The asymmetry is important: SRA catches most human-majority shoulder cases, but the price is 39 shoulder calls among human-majority non-shoulders.
- For borderline human cases, SRA shoulder-call rate is 50.0% when two humans vote shoulders and 42.1% when one human votes shoulders.

### SRA by Number of Human Shoulder Votes

| human shoulder votes | n | SRA Shoulders | SRA No Shoulders | SRA shoulder rate |
| --- | --- | --- | --- | --- |
| 0 | 96 | 31 | 65 | 0.323 |
| 1 | 19 | 8 | 11 | 0.421 |
| 2 | 6 | 3 | 3 | 0.500 |
| 3 | 49 | 45 | 4 | 0.918 |

### SRA by Human-Majority Profile Class

| human majority class | human binary expectation | n | SRA Shoulders | SRA No Shoulders | SRA shoulder rate | SRA disagreement count | SRA disagreement rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Peak+Sh | Shoulders | 55 | 48 | 7 | 0.873 | 7 | 0.127 |
| Exp | No Shoulders | 79 | 28 | 51 | 0.354 | 28 | 0.354 |
| Flat-top (FT) | No Shoulders | 30 | 10 | 20 | 0.333 | 10 | 0.333 |
| Two-slope (2S) | No Shoulders | 6 | 1 | 5 | 0.167 | 1 | 0.167 |

### SRA Disagreement Cases

The full list of 46 SRA-vs-human-majority disagreement cases is written to `sra_disagreement_cases.csv`.

### SRA vs Human Majority Confusion Matrix

| Human majority | Shoulders | No Shoulders |
| --- | --- | --- |
| Shoulders | 48 | 7 |
| No Shoulders | 39 | 76 |

## Figures

- human_class_distribution: `human_class_distribution.png`
- human_kappa_heatmap: `human_pairwise_kappa_heatmap.png`
- human_agreement_by_gb_class: `human_agreement_by_gb_class.png`
- sra_majority_confusion: `sra_vs_human_majority_confusion.png`
- sra_binary_metrics: `sra_binary_metrics.png`
- sra_by_human_votes: `sra_shoulders_by_human_shoulder_votes.png`
- sra_by_majority_class: `sra_shoulders_by_human_majority_class.png`
