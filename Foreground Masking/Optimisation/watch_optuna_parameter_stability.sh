#!/usr/bin/env bash
set -u
python_bin="/root/venvs/pythonscripts/bin/python"
project="/mnt/c/Users/gordo/Documents/Github/PythonScripts"
study_root="/root/clean22-displayed-frame-5toy-optuna-studies"
output_root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_displayed_frame_5toy_optimisation"
audit="$project/Foreground Masking/Optimisation/audit_optuna_parameter_stability.py"
complete="$output_root/80trial_convergence_continuation.complete"
log="$output_root/optuna_parameter_stability_watch.log"

while true; do
    "$python_bin" "$audit" --study-root "$study_root" --output-dir "$output_root" >> "$log" 2>&1
    [[ -f "$complete" ]] && break
    sleep 120
done
printf '[%s] Final parameter-stability audit complete.\n' "$(date '+%F %T')" >> "$log"
