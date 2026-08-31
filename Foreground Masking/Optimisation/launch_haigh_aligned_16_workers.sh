#!/usr/bin/env bash
set -euo pipefail

cd "/mnt/c/Users/gordo/Documents/Github/PythonScripts"

run_root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_haigh_aligned_source_optimisation"
run_log="$run_root/haigh_aligned_cross_validation.log"
run_pid="$run_root/haigh_aligned_cross_validation.pid"

nohup /root/venvs/pythonscripts/bin/python \
  "Foreground Masking/Optimisation/run_haigh_aligned_clean22_cross_validation.py" \
  --manifest "Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv" \
  --clean-list "Foreground Masking/Optimisation/clean_galaxies_revised22.txt" \
  --injection-manifest "$run_root/paired_injections/paired_toy_injection_manifest.json" \
  --output-root "$run_root" \
  --mtobjects-root "/root/mtobjects-linux-final20" \
  --study-storage-root "/root/haigh-aligned-v1-optuna-studies" \
  --workers 16 \
  >> "$run_log" 2>&1 &

process_id=$!
printf '%s\n' "$process_id" > "$run_pid"
printf 'Started Haigh-aligned cross-validation with 16 workers (PID %s).\n' "$process_id"
