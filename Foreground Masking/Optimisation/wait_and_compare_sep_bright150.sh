#!/usr/bin/env bash
set -euo pipefail

cd "/mnt/c/Users/gordo/Documents/Github/PythonScripts"

large_root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_displayed_frame_5toy_optimisation"
bright_root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_haigh_aligned_bright150_optimisation"
sep_root="$bright_root/SEP_cross_validation"
output="$bright_root/SEP_comparison_with_larger_toys"
log="$bright_root/sep_large_toy_comparison.log"

printf '[%s] Waiting for the bright compact-toy SEP result.\n' "$(date --iso-8601=seconds)" >> "$log"
while [[ ! -f "$sep_root/sep_toy_cross_validation_best.json" && ! -f "$sep_root/sep_toy_cross_validation_rejected.json" ]]; do
  sleep 20
done

printf '[%s] SEP result found; starting larger-toy comparison while MTObjects continues.\n' "$(date --iso-8601=seconds)" >> "$log"
/root/venvs/pythonscripts/bin/python \
  "Foreground Masking/Optimisation/compare_sep_large_vs_bright_compact.py" \
  --large-root "$large_root" \
  --bright-root "$bright_root" \
  --output-dir "$output" \
  >> "$log" 2>&1
printf '[%s] SEP comparison complete.\n' "$(date --iso-8601=seconds)" >> "$log"
