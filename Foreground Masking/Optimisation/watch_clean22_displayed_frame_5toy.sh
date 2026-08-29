#!/usr/bin/env bash
set -u

python_bin="/root/venvs/pythonscripts/bin/python"
project="/mnt/c/Users/gordo/Documents/Github/PythonScripts"
output_root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_displayed_frame_5toy_optimisation"
runner="$project/Foreground Masking/Optimisation/run_clean22_full_cross_validation.py"
final_result="$output_root/MTObjects_cross_validation/mtobjects_toy_cross_validation_best.json"
rejected_result="$output_root/MTObjects_cross_validation/mtobjects_toy_cross_validation_rejected.json"
watch_log="$output_root/displayed_frame_cross_validation_watchdog.log"
stale_limit_seconds=1800

while [[ ! -f "$final_result" && ! -f "$rejected_result" ]]; do
    if pgrep -f '[r]un_clean22_full_cross_validation.py' >/dev/null; then
        latest_update=$(find "$output_root/SEP_cross_validation" "$output_root/MTObjects_cross_validation" \
            -type f -name '*optimisation_summary.csv' -printf '%T@\n' 2>/dev/null | sort -nr | head -n 1)
        if [[ -n "$latest_update" ]]; then
            age_seconds=$(( $(date +%s) - ${latest_update%.*} ))
            if (( age_seconds > stale_limit_seconds )); then
                printf '[%s] No trial update for %ss; terminating frozen optimisation for a clean resume.\n' \
                    "$(date '+%F %T')" "$age_seconds" >> "$watch_log"
                pkill -TERM -f '[o]ptimise_toy_objects_(SEP|MTObjects).py' || true
                pkill -TERM -f '[c]ross_validate_toy_objects_(SEP|MTObjects).py' || true
                pkill -TERM -f '[r]un_clean22_full_cross_validation.py' || true
                sleep 30
            fi
        fi
        sleep 60
        continue
    fi
    printf '[%s] Corrected optimisation absent; starting/resuming displayed-frame studies.\n' "$(date '+%F %T')" >> "$watch_log"
    "$python_bin" "$runner" \
        --manifest "$project/Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv" \
        --clean-list "$project/Foreground Masking/Optimisation/clean_galaxies_revised22.txt" \
        --injection-manifest "$output_root/paired_injections/paired_toy_injection_manifest.json" \
        --output-root "$output_root" --mtobjects-root "/root/mtobjects-linux-final20" \
        --study-storage-root "/root/clean22-displayed-frame-5toy-optuna-studies" \
        --workers 4 --initial-points 8 --max-iter 32 --toys-per-image 5 >> "$watch_log" 2>&1
    exit_code=$?
    printf '[%s] Runner exited with code %s.\n' "$(date '+%F %T')" "$exit_code" >> "$watch_log"
    sleep 30
done

if [[ -f "$final_result" ]]; then status="Final corrected MTObjects result detected"; else status="Corrected MTObjects scientific rejection detected"; fi
printf '[%s] %s; watchdog complete.\n' "$(date '+%F %T')" "$status" >> "$watch_log"
