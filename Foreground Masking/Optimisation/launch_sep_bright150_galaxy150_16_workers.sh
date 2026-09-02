#!/usr/bin/env bash
set -euo pipefail

cd "/mnt/c/Users/gordo/Documents/Github/PythonScripts"
run_root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_haigh_aligned_bright150_galaxy150_sep_sensitivity"
run_log="$run_root/sep_galaxy150_cross_validation.log"
run_pid="$run_root/sep_galaxy150_cross_validation.pid"
mkdir -p "$run_root"

nohup /root/venvs/pythonscripts/bin/python \
  "Foreground Masking/Optimisation/cross_validate_toy_objects_SEP.py" \
  --clean-list "Foreground Masking/Optimisation/clean_galaxies_revised22.txt" \
  --manifest "Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv" \
  --pc Desktop \
  --injection-manifest "$run_root/paired_injections/paired_toy_injection_manifest.json" \
  --cv-injection-sets training_seed_1 training_seed_2 training_seed_3 \
  --evaluation-injection-sets validation_seed_1 validation_seed_2 \
  --workers 16 --initial-points 8 --max-iter 72 --toys-per-image 5 \
  --convergence-min-trials 40 --convergence-patience 20 \
  --convergence-relative-tolerance 0.001 --convergence-absolute-tolerance 1e-5 \
  --output-dir "$run_root/SEP_cross_validation" \
  --study-storage-dir "/root/haigh-aligned-bright150-galaxy150-optuna-studies/SEP" \
  --min-toy-detection-rate 0.50 --min-mean-toy-recall 0.30 \
  --pixel-recall-weight 0.25 --f-score-weight 0.30 \
  --toy-recall-weight 0.25 --toy-detection-weight 0.20 \
  --data-loss-penalty 0.50 --false-positive-penalty 0.25 \
  --max-masked-fraction 0.15 --require-final-feasible \
  >> "$run_log" 2>&1 &

process_id=$!
printf '%s\n' "$process_id" > "$run_pid"
printf 'Started SEP galaxy-size sensitivity CV with 16 workers (PID %s).\n' "$process_id"
