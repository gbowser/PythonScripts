#!/usr/bin/env bash
set -euo pipefail

cd "/mnt/c/Users/gordo/Documents/Github/PythonScripts"
run_root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_haigh_aligned_bright150_galaxy150_sep_sensitivity"
run_log="$run_root/mto_galaxy150_cross_validation.log"
run_pid="$run_root/mto_galaxy150_cross_validation.pid"

nohup /root/venvs/pythonscripts/bin/python \
  "Foreground Masking/Optimisation/cross_validate_toy_objects_MTObjects.py" \
  --clean-list "Foreground Masking/Optimisation/clean_galaxies_revised22.txt" \
  --manifest "Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv" \
  --pc Desktop --mtobjects-root "/root/mtobjects-linux-final20" \
  --injection-manifest "$run_root/paired_injections/paired_toy_injection_manifest.json" \
  --cv-injection-sets training_seed_1 training_seed_2 training_seed_3 \
  --evaluation-injection-sets validation_seed_1 validation_seed_2 \
  --workers 16 --initial-points 8 --max-iter 72 --toys-per-image 5 \
  --convergence-min-trials 40 --convergence-patience 20 \
  --convergence-relative-tolerance 0.001 --convergence-absolute-tolerance 1e-5 \
  --output-dir "$run_root/MTObjects_cross_validation" \
  --study-storage-dir "/root/haigh-aligned-bright150-galaxy150-optuna-studies/MTObjects" \
  --bg-variance-log --bg-variance-step 0 --calibrate-bg-variance \
  --max-mask-exceedance-fraction 0.20 --catastrophic-masked-fraction 0.30 \
  --excess-masking-penalty 1.0 \
  --final-min-toy-detection-rate 0.50 --final-min-mean-toy-recall 0.30 \
  >> "$run_log" 2>&1 &

process_id=$!
printf '%s\n' "$process_id" > "$run_pid"
printf 'Started MTObjects galaxy-size sensitivity CV with 16 workers (PID %s).\n' "$process_id"
