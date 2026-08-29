#!/usr/bin/env bash
set -u

python_bin="/root/venvs/pythonscripts/bin/python"
project="/mnt/c/Users/gordo/Documents/Github/PythonScripts"
output_root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_displayed_frame_5toy_optimisation"
runner="$project/Foreground Masking/Optimisation/run_clean22_full_cross_validation.py"
current_final="$output_root/MTObjects_cross_validation/mtobjects_toy_cross_validation_best.json"
current_rejected="$output_root/MTObjects_cross_validation/mtobjects_toy_cross_validation_rejected.json"
log="$output_root/80trial_convergence_continuation.log"
complete_marker="$output_root/80trial_convergence_continuation.complete"
started_marker="$output_root/80trial_convergence_continuation.started"
stale_limit_seconds=1800
start_mode="${1:-wait}"

if [[ "$start_mode" != "--start-now" ]]; then
    printf '[%s] Waiting for the current 40-trial SEP/MTObjects run to finish.\n' "$(date '+%F %T')" >> "$log"
    while [[ ! -f "$current_final" && ! -f "$current_rejected" ]]; do sleep 60; done
    while pgrep -f '[r]un_clean22_full_cross_validation.py|[c]ross_validate_toy_objects_(SEP|MTObjects).py|[o]ptimise_toy_objects_(SEP|MTObjects).py' >/dev/null; do
        sleep 60
    done
else
    printf '[%s] Immediate continuation requested; preserving and resuming all completed trials.\n' \
        "$(date '+%F %T')" >> "$log"
fi

if [[ ! -f "$started_marker" ]]; then
    [[ -f "$current_final" ]] && cp -n "$current_final" "$current_final.40trial.json"
    [[ -f "$current_rejected" ]] && cp -n "$current_rejected" "$current_rejected.40trial.json"
    touch "$started_marker"
fi

while [[ ! -f "$complete_marker" ]]; do
    if pgrep -f '[r]un_clean22_full_cross_validation.py' >/dev/null; then
        latest_update=$(find "$output_root/SEP_cross_validation" "$output_root/MTObjects_cross_validation" \
            -type f \( -name '*optimisation_summary.csv' -o -name 'optuna_convergence.json' \) \
            -printf '%T@\n' 2>/dev/null | sort -nr | head -n 1)
        if [[ -n "$latest_update" ]]; then
            age_seconds=$(( $(date +%s) - ${latest_update%.*} ))
            if (( age_seconds > stale_limit_seconds )); then
                printf '[%s] No continuation update for %ss; terminating frozen process tree for clean resume.\n' \
                    "$(date '+%F %T')" "$age_seconds" >> "$log"
                pkill -TERM -f '[o]ptimise_toy_objects_(SEP|MTObjects).py' || true
                pkill -TERM -f '[c]ross_validate_toy_objects_(SEP|MTObjects).py' || true
                pkill -TERM -f '[r]un_clean22_full_cross_validation.py' || true
                sleep 30
            fi
        fi
        sleep 60
        continue
    fi

    printf '[%s] Starting/resuming optimisation-only continuation (40 minimum, 80 maximum, patience 20).\n' \
        "$(date '+%F %T')" >> "$log"
    "$python_bin" "$runner" \
        --manifest "$project/Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv" \
        --clean-list "$project/Foreground Masking/Optimisation/clean_galaxies_revised22.txt" \
        --injection-manifest "$output_root/paired_injections/paired_toy_injection_manifest.json" \
        --output-root "$output_root" --mtobjects-root "/root/mtobjects-linux-final20" \
        --study-storage-root "/root/clean22-displayed-frame-5toy-optuna-studies" \
        --workers 4 --initial-points 8 --max-iter 72 --toys-per-image 5 \
        --convergence-min-trials 40 --convergence-patience 20 \
        --convergence-relative-tolerance 0.001 --convergence-absolute-tolerance 0.00001 >> "$log" 2>&1
    exit_code=$?
    printf '[%s] Continuation runner exited with code %s.\n' "$(date '+%F %T')" "$exit_code" >> "$log"
    if (( exit_code == 0 )); then
        touch "$complete_marker"
        break
    fi
    sleep 30
done

printf '[%s] 80-trial convergence-controlled optimisation complete; no 182-galaxy batch was run.\n' \
    "$(date '+%F %T')" >> "$log"
