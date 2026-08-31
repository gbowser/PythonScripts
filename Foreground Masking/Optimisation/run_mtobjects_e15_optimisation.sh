#!/usr/bin/env bash
set -u

python_bin="/root/venvs/pythonscripts/bin/python"
project="/mnt/c/Users/gordo/Documents/Github/PythonScripts"
source_base="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_displayed_frame_5toy_optimisation/MTObjects_multiseed_optimisation_pilot_v3"
base="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_displayed_frame_5toy_optimisation/MTObjects_multiseed_E15_optimisation_v4"
manifest="$source_base/paired_injections/paired_toy_injection_manifest.json"
optimisation="$base/optimisation"
validation="$base/held_out_validation"
study_dir="/root/mtobjects-multiseed-e15-v4-optuna"
log="$base/e15_optimisation.log"
complete="$base/e15_optimisation.complete"
failed="$base/e15_optimisation.failed"
clean_list="$project/Foreground Masking/Optimisation/clean_galaxies_revised22.txt"
source_manifest="$project/Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv"

mkdir -p "$base" "$optimisation" "$validation" "$study_dir"
rm -f "$complete" "$failed"
printf '[%s] Starting/resuming E15-controlled MTObjects optimisation.\n' "$(date '+%F %T')" >> "$log"

mapfile -t names < "$clean_list"
"$python_bin" "$project/Foreground Masking/Optimisation/optimise_toy_objects_MTObjects.py" \
    --manifest "$source_manifest" --pc Desktop --mtobjects-root /root/mtobjects-linux-final20 \
    --output-dir "$optimisation" --fixed-output-dir --names "${names[@]}" --max-images 22 \
    --toys-per-image 5 --truth-dilation 1 --toy-peak-sigma-min 6 --toy-peak-sigma-max 30 \
    --injection-manifest "$manifest" --injection-sets training_seed_1 training_seed_2 training_seed_3 \
    --mtobjects-detect-on original --initial-points 8 --max-iter 72 --workers 8 \
    --seed 202609601 --study-name mtobjects-multiseed-e15-v4 \
    --study-storage-dir "$study_dir" --convergence-min-trials 40 --convergence-patience 20 \
    --convergence-relative-tolerance 0.001 --convergence-absolute-tolerance 0.00001 \
    --bg-variance-min 0.0001 --bg-variance-max 0.001 --bg-variance-step 0 --bg-variance-log \
    --max-masked-fraction 0.15 --max-mask-exceedance-fraction 0.20 \
    --catastrophic-masked-fraction 0.30 --excess-masking-penalty 1.0 \
    --data-loss-penalty 0.5 --false-positive-penalty 0.1 \
    --min-toy-detection-rate 0.25 --min-mean-toy-recall 0.20 >> "$log" 2>&1
exit_code=$?
if (( exit_code != 0 )); then
    touch "$failed"; printf '[%s] Optimisation failed with code %s.\n' "$(date '+%F %T')" "$exit_code" >> "$log"; exit "$exit_code"
fi

best="$optimisation/mtobjects_parameter_optimisation_best.json"
if [[ ! -f "$best" ]]; then
    touch "$failed"; printf '[%s] Optimisation ended without a best-result JSON.\n' "$(date '+%F %T')" >> "$log"; exit 2
fi

"$python_bin" "$project/Foreground Masking/Optimisation/evaluate_mtobjects_multiseed_winner.py" \
    --best-json "$best" --clean-list "$clean_list" --manifest "$source_manifest" \
    --injection-manifest "$manifest" --injection-sets validation_seed_1 validation_seed_2 \
    --output-dir "$validation" --mtobjects-root /root/mtobjects-linux-final20 --workers 8 \
    --max-masked-fraction 0.15 --max-mask-exceedance-fraction 0.20 \
    --catastrophic-masked-fraction 0.30 --excess-masking-penalty 1.0 \
    --min-toy-detection-rate 0.50 --min-mean-toy-recall 0.30 >> "$log" 2>&1
exit_code=$?
if (( exit_code != 0 )); then
    touch "$failed"; printf '[%s] Held-out validation crashed with code %s.\n' "$(date '+%F %T')" "$exit_code" >> "$log"; exit "$exit_code"
fi

touch "$complete"
printf '[%s] E15 optimisation and held-out validation completed.\n' "$(date '+%F %T')" >> "$log"

