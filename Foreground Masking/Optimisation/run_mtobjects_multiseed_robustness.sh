#!/usr/bin/env bash
set -u

python_bin="/root/venvs/pythonscripts/bin/python"
project="/mnt/c/Users/gordo/Documents/Github/PythonScripts"
optimisation_root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_displayed_frame_5toy_optimisation"
output="$optimisation_root/MTObjects_multiseed_robustness"
log="$output/multiseed_robustness.log"
complete="$output/multiseed_robustness.complete"
failed="$output/multiseed_robustness.failed"

mkdir -p "$output"
printf '[%s] Starting three-seed MTObjects robustness evaluation.\n' "$(date '+%F %T')" >> "$log"
"$python_bin" "$project/Foreground Masking/Optimisation/evaluate_mtobjects_multiseed_robustness.py" \
    --clean-list "$project/Foreground Masking/Optimisation/clean_galaxies_revised22.txt" \
    --manifest "$project/Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv" \
    --rejection-json "$optimisation_root/MTObjects_cross_validation/mtobjects_toy_cross_validation_rejected.json" \
    --output-dir "$output" --mtobjects-root /root/mtobjects-linux-final20 \
    --seeds 202608501 202608601 202608701 --workers 4 --toys-per-image 5 >> "$log" 2>&1
exit_code=$?
if (( exit_code == 0 )); then
    touch "$complete"
    printf '[%s] Three-seed robustness evaluation completed.\n' "$(date '+%F %T')" >> "$log"
else
    touch "$failed"
    printf '[%s] Three-seed robustness evaluation failed with code %s.\n' "$(date '+%F %T')" "$exit_code" >> "$log"
fi
exit "$exit_code"
