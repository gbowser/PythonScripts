#!/usr/bin/env bash
set -u

python_bin="/root/venvs/pythonscripts/bin/python"
project="/mnt/c/Users/gordo/Documents/Github/PythonScripts"
base="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_displayed_frame_5toy_optimisation/MTObjects_multiseed_optimisation_pilot_v3"
output="$base/failure_mode_analysis"
log="$output/failure_analysis_progress.log"
complete="$output/failure_analysis.complete"
failed="$output/failure_analysis.failed"

mkdir -p "$output"
rm -f "$complete" "$failed"
printf '[%s] Starting MTObjects failure-mode analysis.\n' "$(date '+%F %T')" > "$log"

"$python_bin" "$project/Foreground Masking/Optimisation/analyse_mtobjects_failure_modes.py" \
  --best-json "$base/optimisation/mtobjects_parameter_optimisation_best.json" \
  --clean-list "$project/Foreground Masking/Optimisation/clean_galaxies_revised22.txt" \
  --manifest "$project/Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv" \
  --injection-manifest "$base/paired_injections/paired_toy_injection_manifest.json" \
  --optimisation-summary "$base/optimisation/mtobjects_parameter_optimisation_summary.csv" \
  --output-dir "$output" \
  --mtobjects-root /root/mtobjects-linux-final20 \
  --workers 8 >> "$log" 2>&1
exit_code=$?
if (( exit_code == 0 )); then
  touch "$complete"
  printf '[%s] Failure-mode analysis completed successfully.\n' "$(date '+%F %T')" >> "$log"
else
  touch "$failed"
  printf '[%s] Failure-mode analysis failed with code %s.\n' "$(date '+%F %T')" "$exit_code" >> "$log"
fi
exit "$exit_code"
