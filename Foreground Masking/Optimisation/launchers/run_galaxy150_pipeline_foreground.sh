#!/usr/bin/env bash
set -uo pipefail

cd "/mnt/c/Users/gordo/Documents/Github/PythonScripts"
root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_haigh_aligned_bright150_galaxy150_sep_sensitivity"
mto_dir="$root/MTObjects_cross_validation"
mto_log="$root/mto_galaxy150_cross_validation.log"

if [[ ! -f "$mto_dir/mtobjects_toy_cross_validation_best.json" && ! -f "$mto_dir/mtobjects_toy_cross_validation_rejected.json" ]]; then
  /root/venvs/pythonscripts/bin/python \
    "Foreground Masking/Optimisation/cross_validate_toy_objects_MTObjects.py" \
    --clean-list "Foreground Masking/Optimisation/clean_galaxies_revised22.txt" \
    --manifest "Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv" \
    --pc Desktop --mtobjects-root "/root/mtobjects-linux-final20" \
    --injection-manifest "$root/paired_injections/paired_toy_injection_manifest.json" \
    --cv-injection-sets training_seed_1 training_seed_2 training_seed_3 \
    --evaluation-injection-sets validation_seed_1 validation_seed_2 \
    --workers 16 --initial-points 8 --max-iter 72 --toys-per-image 5 \
    --convergence-min-trials 40 --convergence-patience 20 \
    --convergence-relative-tolerance 0.001 --convergence-absolute-tolerance 1e-5 \
    --output-dir "$mto_dir" \
    --study-storage-dir "/root/haigh-aligned-bright150-galaxy150-optuna-studies/MTObjects" \
    --bg-variance-log --bg-variance-step 0 --calibrate-bg-variance \
    --max-mask-exceedance-fraction 0.20 --catastrophic-masked-fraction 0.30 \
    --excess-masking-penalty 1.0 \
    --final-min-toy-detection-rate 0.50 --final-min-mean-toy-recall 0.30 \
    >> "$mto_log" 2>&1
fi

if [[ ! -f "$mto_dir/mtobjects_toy_cross_validation_best.json" && ! -f "$mto_dir/mtobjects_toy_cross_validation_rejected.json" ]]; then
  printf '[%s] MTO exited without a terminal result; supervisor restart required.\n' "$(date --iso-8601=seconds)" >> "$root/windows_pipeline_supervisor.log"
  exit 3
fi

# This script is resumable and immediately proceeds because MTO is terminal.
exec bash "Foreground Masking/Optimisation/queue_sep_merging_after_mto.sh"
