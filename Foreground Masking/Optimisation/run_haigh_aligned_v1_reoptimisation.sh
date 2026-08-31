#!/usr/bin/env bash
set -euo pipefail

project_root="/mnt/c/Users/gordo/Documents/Github/PythonScripts"
output_root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_haigh_aligned_source_optimisation"
log_path="$output_root/haigh_aligned_cross_validation.log"
pid_path="$output_root/haigh_aligned_cross_validation.pid"
python_path="/root/venvs/pythonscripts/bin/python"

mkdir -p "$output_root"
if [[ -f "$pid_path" ]]; then
    previous_pid="$(tr -d '[:space:]' < "$pid_path")"
    if [[ -n "$previous_pid" ]] && kill -0 "$previous_pid" 2>/dev/null; then
        echo "Haigh-aligned optimisation is already running as PID $previous_pid"
        exit 2
    fi
fi

echo "$$" > "$pid_path"
{
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Haigh-aligned v1 SEP + MTObjects re-optimisation"
    echo "Manifest: $output_root/paired_injections/paired_toy_injection_manifest.json"
    echo "Training sets: training_seed_1 training_seed_2 training_seed_3"
    echo "Validation sets: validation_seed_1 validation_seed_2"
    echo "Folds: 22; maximum trials per fold: 80; workers: 8"
} > "$log_path"

cd "$project_root"
exec "$python_path" "Foreground Masking/Optimisation/run_haigh_aligned_clean22_cross_validation.py" \
    --manifest "Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv" \
    --clean-list "Foreground Masking/Optimisation/clean_galaxies_revised22.txt" \
    --injection-manifest "$output_root/paired_injections/paired_toy_injection_manifest.json" \
    --output-root "$output_root" \
    --mtobjects-root /root/mtobjects-linux-final20 \
    --study-storage-root /root/haigh-aligned-v1-optuna-studies \
    --workers 8 >> "$log_path" 2>&1
