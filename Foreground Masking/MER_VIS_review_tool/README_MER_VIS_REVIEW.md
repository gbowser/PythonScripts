# MER VIS sample review

Double-click **Start MER VIS Review.cmd** in this folder. It opens a local browser application. No Datalabs connection, account or internet connection is required.

The launcher uses the working scientific Python environment already installed for this project. Keep `Foreground Masking/MER_VIS_pipeline_v2/dependencies` available. If starting in a different environment, install `requirements_MER_VIS_review.txt`, then run `python review_MER_VIS.py`.

## Start with a few examples

1. Choose a **Review group** on the left. There are 48 unique examples, rather than a queue of 2,694 galaxies.
2. Explore the FITS light distribution. **Faint disc**, **Balanced** and **Bright core** are starting presets. Change **Minimum**, **Maximum**, **Gamma** and **Linear / Log / Asinh** to expose different structures. Higher gamma lifts faint light. These affect display only.
3. Use the mouse wheel or Zoom buttons to zoom, and drag the image to pan. **Galaxy view** restores the target view; **Full cutout** shows the wider field. Wide views may be downsampled; zoom in for native pixels. Image aspect ratio and native orientation are preserved. N/E arrows come from the FITS WCS.
4. In the profiles, green is the selected disc interval and orange the candidate bar interval. Blue points are pipeline-accepted; grey points are excluded. Lines break across excluded samples. If using the exploratory marginal pool, additional candidates are pink.
5. Choose **Disc** or **Bar**, then drag an interval edge in either plot. Alternatively enter inner/outer radii. The table updates PA, inclination, sample count, gap and scatter. **Reset intervals** restores the stored selections. If you see no convincing bar, tick **Treat as no convincing bar** to remove its trial angle while retaining the disc result.
6. Expand **Explore the review thresholds** to vary the sparse-sampling count, gap, PA RMS, ellipticity range and small-feature thresholds, or disable a screen. These are local what-if calculations, not changes to the pipeline.
7. Record disc, bar and centre assessments, the suggested rule action, and a short note. Click **Save and next**. Ctrl+Enter also saves and advances. Left/right arrows navigate when you are not typing.

You need not complete all 48. A few clear and borderline cases in each group may already establish the next useful change. The initial set contains 12 sparse-sampling examples, 12 candidate-bar size examples, 12 ellipticity examples, six well-sampled PA-variation examples and six no-flag comparisons. Some boundary cases deliberately do not trigger the corresponding current flag. Other coexisting issues remain visible.

## What is saved

Saved reviews are in this folder's **saved_reviews** subfolder:

- `MER_VIS_saved_reviews.json`: authoritative decisions, notes, intervals, display settings, rules and trial calculations.
- `MER_VIS_saved_reviews.csv`: convenient flat summary for comparison and analysis. **Export reviews CSV** downloads a fresh copy.
- `MER_VIS_review_sample.csv` and `.json`: the fixed, reproducible sample and why each galaxy was chosen.

If Excel locks the CSV, the JSON review still saves. Close the CSV and save another review, or export a fresh copy. Merely adjusting brightness or browsing does not mark a galaxy reviewed. Unsaved browser drafts are kept on this computer; use **Save review** to persist decisions in the review files.

Close the browser and reopen the launcher to continue. To stop the background process, use **Stop local server** at the bottom of the left panel. The server is accessible only on 127.0.0.1. Reopening the launcher reuses the running app or starts a new instance.

## Interpretation

- Original values use the stored selected disc/bar samples, including the pipeline's brightness-based selection. Editing intervals uses the chosen accepted sample pool inside the new radial bounds; it does not refit any ellipse or automatically search for a different bar.
- The exploratory marginal pool applies the existing relaxed numerical checks to previously measured ellipses. It includes valid stop-code 0/2 samples with coverage ≥50%, ellipticity error <0.20, PA error <20°, positive intensity and a relaxed centre tolerance. Stop code 2 means the iteration limit, not normal convergence. Marginal points do not become validated measurements simply because they are displayed.
- Disc PA is a weighted axial mean; RMS scatter uses wrapped angular deviations about an unweighted axial mean. Inclination is acos(median b/a), with q0=0. Reported angles are observed sky angles, North towards East modulo 180°.
- The unchanged pipeline bar selection displays its stored class A or B. After editing the bar interval or sample pool, the tool gives an A/B-style interval diagnostic, not a new automated bar search or confirmation of a physical bar. A small feature can be a bar, bulge, arm, ring or noise structure.
- Nearly-face-on discs are informational. The sampling and PA-variation flags are suppressed for b/a >0.90. Adjacent ellipse measurements are correlated; counts, RMS and leave-one-out sensitivity are not independent statistical confidence intervals.
- The initial sample is purposively stratified. It cannot establish how common each failure mode is across the full catalogue.

The application reads the existing cutouts in `D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_cutouts` through their manifest paths. It never modifies science FITS files, fitted profiles, the geometry manifest, published PNG/PDF reports or the pipeline thresholds. After review, we can use your saved assessments to propose and validate a pipeline change.
