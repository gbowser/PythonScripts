#!/usr/bin/env bash
set -u

python_bin="/root/venvs/pythonscripts/bin/python"
project="/mnt/c/Users/gordo/Documents/Github/PythonScripts"
optimisation_root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_displayed_frame_5toy_optimisation"
application_root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_displayed_frame_5toy_all182_application"
sep_best="$optimisation_root/SEP_cross_validation/sep_toy_cross_validation_best.json"
mto_best="$optimisation_root/MTObjects_cross_validation/mtobjects_toy_cross_validation_best.json"
mto_rejected="$optimisation_root/MTObjects_cross_validation/mtobjects_toy_cross_validation_rejected.json"
optimisation_complete="$optimisation_root/80trial_convergence_continuation.complete"
runner="$project/Foreground Masking/Batch tools/run_clean22_all_galaxy_toy_comparison.py"
log="$application_root/all182_png_watch.log"
complete_marker="$application_root/all182_png_sets.complete"
failed_marker="$application_root/all182_png_sets.failed"

mkdir -p "$application_root"
printf '[%s] Waiting for successful SEP and MTObjects optimisation winners.\n' "$(date '+%F %T')" >> "$log"

while [[ ! -f "$optimisation_complete" ]]; do
    if [[ -f "$mto_rejected" ]]; then
        printf '[%s] MTObjects optimisation was rejected; production PNG batches will not run.\n' "$(date '+%F %T')" >> "$log"
        touch "$failed_marker"
        exit 2
    fi
    sleep 60
done

if [[ ! -f "$sep_best" || ! -f "$mto_best" || -f "$mto_rejected" ]]; then
    printf '[%s] Optimisation completed without both accepted winner files; production PNG batches will not run.\n' "$(date '+%F %T')" >> "$log"
    touch "$failed_marker"
    exit 3
fi

while [[ ! -f "$complete_marker" ]]; do
    printf '[%s] Starting/resuming SEP, MTObjects and combined 182-galaxy PNG production.\n' "$(date '+%F %T')" >> "$log"
    "$python_bin" "$runner" \
        --manifest "$project/Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv" \
        --clean-list "$project/Foreground Masking/Optimisation/clean_galaxies_revised22.txt" \
        --sep-best "$sep_best" --mto-best "$mto_best" \
        --mtobjects-root "/root/mtobjects-linux-final20" \
        --output-root "$application_root" --expected-galaxies 182 --toys-per-image 5 >> "$log" 2>&1
    exit_code=$?
    printf '[%s] All-galaxy PNG runner exited with code %s.\n' "$(date '+%F %T')" "$exit_code" >> "$log"
    if (( exit_code == 0 )); then
        touch "$complete_marker"
        exit 0
    fi
    sleep 60
done
