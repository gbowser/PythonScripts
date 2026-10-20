# Adaptive MER VIS geometry v2

The current results replace the original fixed-centre, fixed-interval run.

## Scientific policy

- Fit centres from the light distribution; preserve catalogue and fitted centres.
- Use native pixels for smaller objects and adaptive binning for larger objects.
- Fit multiple starting geometries, with an outer-pass attempt and labelled recovery.
- Normal samples require stop code 0. Code 2 means iteration limit, admitted only under labelled relaxed recovery.
- Record independent disc and bar outcomes. No accepted bar does not erase the disc result.
- Report nearly face-on in `codex_information`, not as a counted quality issue. Do not raise disc_PA_unstable for q>0.9.
- PAs are observed sky major-axis directions from North towards East, modulo180, using local WCS.
- Inclination remains q0=0. Euclid comparison PA retains the adopted extra +90 after WCS conversion.
- Flag operational centre offset and scatter thresholds. Do not equate a light centroid automatically with the physical nucleus.

The initial adaptive script and failure-only recovery script are separate for provenance. The recovery script preserves zero-strict-sample trial profiles and also tries catalogue/local-flux centres. It never overwrites a successful initial fit. `finalize_MER_VIS_geometry.py` records the recovery audit and recomputes the WCS comparison for all targets.

## Reproduce a new run

Use Python with astropy, photutils, numpy and scipy. The report generators also need matplotlib, pandas, reportlab, Pillow and pypdf. The task used official Astropy8.0.2 and Photutils3.1.1 wheels in a separate environment because Windows blocked the previous environment's binary.

From PythonScripts, choose a NEW result folder:

```powershell
python .\Euclid\adaptive_MER_VIS\fit_adaptive_MER_VIS_geometry.py --catalogue .\Euclid\datalabs_MER_VIS\MER_VIS_geometry_comparison_manifest.csv --segmentation .\Euclid\datalabs_MER_VIS\MER_VIS_datalabs_manifest.csv --input-dir 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_cutouts' --output-dir 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid\Euclid_MER_VIS_geometry_NEW' --workers 12
```

The run is checkpointed and can be resumed with the same command. Changes in algorithm, input catalogue or segmentation require a new folder. Finalization expects all2777 rows, compares against a baseline manifest and performs explicit failed-target recovery. Report generation accepts `--geometry-dir` and `--output-dir`; assembly and verification accept `--input-dir`. Do not mix old card metadata with new results.

The final collection's verification JSON checks every card's geometry against the manifest, missing bars, QI grouping, PNG dimensions, every PDF's page/card counts and the source hash.
