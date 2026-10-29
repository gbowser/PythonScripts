> Active centre-acceptance re-review: the usual launcher now opens a separate 19-galaxy round. Read [CENTRE_POLICY_MER_VIS_REVIEW.md](CENTRE_POLICY_MER_VIS_REVIEW.md) for the new reference-centre checks, comparison columns and residual diagnostics. Earlier reviews and notes remain under `saved_reviews`; the new round uses `saved_reviews_centre_v3`. Use `Start Original MER VIS Review.cmd` to reopen the completed original review.

# MER VIS sample review

Double-click **Start MER VIS Review.cmd** in this folder. It opens a local browser application. No Datalabs connection, account or internet connection is required.

The launcher uses the working scientific Python environment already installed for this project. Keep `Foreground Masking/MER_VIS_pipeline_v2/dependencies` available. If starting in a different environment, install `requirements_MER_VIS_review.txt`, then run `python review_MER_VIS.py`.

## Start with a few examples

1. Choose a **Review group** on the left. There are 58 unique examples, rather than a queue of 2,694 galaxies.
2. Explore the FITS light distribution. **Faint disc**, **Balanced** and **Bright core** are starting presets. Change **Minimum**, **Maximum**, **Gamma** and **Linear / Log / Asinh** to expose different structures. Higher gamma lifts faint light. These affect display only.
3. Use the mouse wheel or Zoom buttons to zoom, and drag the image to pan. **Galaxy view** restores the target view; **Full cutout** shows the wider field. Wide views may be downsampled; zoom in for native pixels. Image aspect ratio and native orientation are preserved. N/E arrows come from the FITS WCS.
4. In the profiles, green is the selected disc interval and orange the candidate bar interval. Blue points are pipeline-accepted; grey points are excluded. Lines break across excluded samples. If using the exploratory marginal pool, additional candidates are pink.
5. Choose **Disc** or **Bar**, then drag an interval edge in either plot. Alternatively enter inner/outer radii. The table updates PA, inclination, sample count, gap and scatter. **Reset intervals** restores the stored selections. If you see no convincing bar, tick **Treat as no convincing bar** to remove its trial angle while retaining the disc result.
6. Expand **Explore the review thresholds** to vary the sparse-sampling count, gap, PA RMS, ellipticity range and small-feature thresholds, or disable a screen. These are local what-if calculations, not changes to the pipeline.
7. Record disc, bar and centre assessments, the suggested rule action, and a short note. Click **Save and next**. Ctrl+Enter also saves and advances. Left/right arrows navigate when you are not typing.

You need not complete all 58. A few clear and borderline cases in each group may already establish the next useful change. The initial set contains 12 sparse-sampling examples, 12 candidate-bar size examples, 12 ellipticity examples, six well-sampled PA-variation examples and 12 No Quality Issues references (six nearly face-on and six at other inclinations). Some boundary cases deliberately do not trigger the corresponding current flag. Other coexisting issues remain visible.

## What is saved

Saved reviews are in this folder's **saved_reviews** subfolder:

- `MER_VIS_saved_reviews.json`: authoritative decisions, notes, intervals, display settings, rules and trial calculations.
- `MER_VIS_saved_reviews.csv`: convenient flat summary for comparison and analysis. **Export reviews CSV** downloads a fresh copy.
- `MER_VIS_review_sample.csv` and `.json`: the fixed, reproducible sample and why each galaxy was chosen.

If Excel locks the CSV, the JSON review still saves. Close the CSV and save another review, or export a fresh copy. Merely adjusting brightness or browsing does not mark a galaxy reviewed. Unsaved browser drafts are kept on this computer; use **Save review** to persist decisions in the review files.

Close the browser and reopen the launcher to continue. To stop the background process, use **Stop local server** at the bottom of the left panel. The server is accessible only on 127.0.0.1. Reopening the launcher reuses the running app or starts a new instance.

## Interpretation

- Original values use the stored selected disc/bar samples, including the pipeline's brightness-based selection. Editing intervals uses the chosen accepted sample pool inside the new radial bounds; interval edits do not refit ellipses or automatically search for another bar. The separate centre retry below reruns fitting.
- The exploratory marginal pool applies the existing relaxed numerical checks to previously measured ellipses. It includes valid stop-code 0/2 samples with coverage ≥50%, ellipticity error <0.20, PA error <20°, positive intensity and a relaxed centre tolerance. Stop code 2 means the iteration limit, not normal convergence. Marginal points do not become validated measurements simply because they are displayed.
- Disc PA is a weighted axial mean; RMS scatter uses wrapped angular deviations about an unweighted axial mean. Inclination is acos(median b/a), with q0=0. Reported angles are observed sky angles, North towards East modulo 180°.
- The unchanged pipeline bar selection displays its stored class A or B. After editing the bar interval or sample pool, the tool gives an A/B-style interval diagnostic, not a new automated bar search or confirmation of a physical bar. A small feature can be a bar, bulge, arm, ring or noise structure.
- Nearly-face-on discs are informational. The sampling and PA-variation flags are suppressed for b/a >0.90. Adjacent ellipse measurements are correlated; counts, RMS and leave-one-out sensitivity are not independent statistical confidence intervals.
- The initial sample is purposively stratified. It cannot establish how common each failure mode is across the full catalogue.

The application reads the existing cutouts in `D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_cutouts` through their manifest paths. It never modifies original science FITS files, original fitted profiles, the master geometry manifest, published PNG/PDF reports or the pipeline thresholds. Manual-centre retries create separate profiles and results. After review, we can use your saved assessments to propose and validate a pipeline change.

## PixInsight AutoSTF view

Choose **PixInsight AutoSTF** from Stretch, or click its preset button. This reuses the monochrome midtones-transfer AutoStretch from `interactive_toy_objects_SEP_MTObjects.py`: normalise the finite displayed pixels, estimate median and 1.4826 × MAD, clip shadows at median minus 2.8 sigma, and set midtones to map the background median to 0.25. Auto shadows and Target background are adjustable; Gamma = 1 preserves the base curve. Min/max are automatic in this mode. Other gamma values are an additional display adjustment.

This is a PixInsight-style implementation, not the PixInsight application engine. It uses statistics from the current displayed preview, so a different crop or a downsampled preview can look different from PixInsight using the entire original FITS image. Source pixels and geometry are unchanged. The defaults are documented in the [PixInsight DisplayFunction source](https://gitlab.com/pixinsight/PCL/-/raw/master/include/pcl/DisplayFunction.h).

The reference group is named **No Quality Issues** in the Review group menu. The expansion preserves the earlier 48 sample IDs and all saved reviews, while adding six clean nearly-face-on references. Nearly-face-on is informational and is not used as a quality issue.

## Failed galaxies

Choose **Failed galaxies** in Review group. This includes all four failed fits in the current manifest, not a sample of failures. The failure reason is shown above the image. The full cutout opens initially, with the usual stretch, zoom and pan controls. No red adopted-centre marker or accepted ellipse overlays are shown for failed fits; any grey profile measurements are unadopted. Disc/bar interval trials are disabled, but assessments and notes can still be saved. Existing sample IDs and saved reviews are preserved.

PixInsight AutoSTF is the default view and the first Stretch option. Existing display drafts are migrated to this default once; subsequent display choices are remembered per galaxy. Assessments, geometry intervals and science files are unchanged.

## Correct a centre and recompute

1. Open **Update centre and recompute**, below the image navigation buttons.
2. Zoom in to distinguish the nucleus from foreground stars and star-forming knots. Choose **Pick centre on image**, then click the nucleus. The yellow cross is the proposed position. Alternatively enter Centre X/Y in zero-based native FITS pixels. These are not screen pixels; Y increases upwards in this viewer. **Use catalogue position** restores the original catalogue coordinates.
3. Initially leave **Keep this centre fixed during fitting** checked. Unchecking permits the ellipse centres to move from the seed. A fixed fit has zero centre scatter by construction, which is not independent validation of the nucleus.
4. Click **Recompute from this centre** and wait. The local background worker reads native science pixels, reruns the adaptive Photutils fitter, and recomputes the accepted profile, disc/bar intervals, PAs, inclination, axis ratio, scatter, centre offset, bar signature and quality flags. One fit runs at a time, with a ten-minute timeout. No global quality thresholds are relaxed by this action; the existing labelled recovery path is retained.
5. The refreshed image and profiles show the manual-centre result. **Original pipeline** retains the baseline angles in the comparison table. The issue line shows the new flags and clearly identifies a manual-centre refit. It can still fail or return no accepted bar. The Failed galaxies group continues to mean failures in the original manifest.
6. Use **Show original fit** and **Show last refit** to compare. Save your assessment and notes when satisfied. Recomputed files are stored automatically even before an assessment is saved. **Download refit metrics CSV** exports the complete updated row, including the recalculated Euclid differences and disc sampling statistics.

Each attempt gets a unique folder under `saved_reviews/refits/`, containing `request.json`, `result.json`, `MER_VIS_manual_refit_manifest.csv`, a new ellipse-profile CSV and logs. The request records the selected native-pixel centre, centre-lock setting, original manifest hash and fitter hash. These retry files are separate from the original geometry manifest, profiles and FITS files. Euclid catalogue measurements are retained unchanged and their deltas are recalculated against the new measured geometry. The latest attempt is available again after restarting the tool; assessment decisions remain saved only by **Save review**.

The new fitter is a separate copy of the adaptive pipeline with explicit centre input, no automatic jump to a brightness peak, optional centre locking and centre offsets measured against the original catalogue position. It uses the same segmentation size catalogue in `Euclid/datalabs_MER_VIS/MER_VIS_datalabs_manifest.csv`. It does not automatically publish revised PNG/PDF reports or replace the master catalogue. A recovered fit remains provisional pending review of the nucleus and physical disc/bar identification.
