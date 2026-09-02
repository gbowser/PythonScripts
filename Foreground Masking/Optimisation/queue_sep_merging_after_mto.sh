#!/usr/bin/env bash
set -uo pipefail

cd "/mnt/c/Users/gordo/Documents/Github/PythonScripts"
root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_haigh_aligned_bright150_galaxy150_sep_sensitivity"
mto="$root/MTObjects_cross_validation"
output="$root/SEP_merging_sensitivity"
queue_log="$root/sep_merging_after_mto_queue.log"
run_log="$root/sep_merging_sensitivity.log"
result="$output/sep_merging_sensitivity_result.json"

printf '[%s] SEP merging experiment queued behind MTObjects.\n' "$(date --iso-8601=seconds)" >> "$queue_log"
while [[ ! -f "$mto/mtobjects_toy_cross_validation_best.json" && ! -f "$mto/mtobjects_toy_cross_validation_rejected.json" ]]; do
  sleep 30
done
printf '[%s] MTObjects terminal result found; starting SEP merging experiment.\n' "$(date --iso-8601=seconds)" >> "$queue_log"

mkdir -p "$output"
attempt=0
while [[ ! -f "$result" && $attempt -lt 3 ]]; do
  attempt=$((attempt + 1))
  printf '[%s] Starting/resuming SEP merging experiment attempt %d/3.\n' "$(date --iso-8601=seconds)" "$attempt" >> "$queue_log"
  /root/venvs/pythonscripts/bin/python \
    "Foreground Masking/Optimisation/run_sep_merging_sensitivity.py" \
    --geometry-manifest "Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv" \
    --injection-manifest "$root/paired_injections/paired_toy_injection_manifest.json" \
    --clean-list "Foreground Masking/Optimisation/clean_galaxies_revised22.txt" \
    --output-dir "$output" --pc Desktop --trials 80 --workers 16 \
    >> "$run_log" 2>&1
  status=$?
  printf '[%s] Attempt %d exited with status %d.\n' "$(date --iso-8601=seconds)" "$attempt" "$status" >> "$queue_log"
  [[ -f "$result" ]] || sleep 20
done

if [[ -f "$result" ]]; then
  printf '[%s] SEP merging experiment completed successfully.\n' "$(date --iso-8601=seconds)" >> "$queue_log"
  exit 0
fi
printf '[%s] SEP merging experiment failed after three resumable attempts.\n' "$(date --iso-8601=seconds)" >> "$queue_log"
exit 3
