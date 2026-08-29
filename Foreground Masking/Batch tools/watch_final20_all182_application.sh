#!/usr/bin/env bash
set -u

python_bin="/root/venvs/pythonscripts/bin/python"
project="/mnt/c/Users/gordo/Documents/Github/PythonScripts"
output_root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/final20_toy_optimisation"
application_root="$output_root/all182_application"
runner="$project/Foreground Masking/Batch tools/run_final20_all_galaxy_toy_comparison.py"
log="$application_root/all182_watchdog.log"

mkdir -p "$application_root"
while true; do
    combined_count=$(find "$application_root/Combined" -maxdepth 1 -type f -name '*.png' 2>/dev/null | wc -l)
    if (( combined_count >= 182 )); then
        printf '[%s] All 182 combined PNGs detected; watchdog complete.\n' "$(date '+%F %T')" >> "$log"
        break
    fi
    if pgrep -f '[r]un_final20_all_galaxy_toy_comparison.py' >/dev/null; then
        sleep 60
        continue
    fi
    printf '[%s] All-182 runner absent; resuming incomplete work.\n' "$(date '+%F %T')" >> "$log"
    FOREGROUND_MASKING_PC=Desktop "$python_bin" "$runner" \
        --manifest "$project/Erwin_s4g_image_downloader/geometry_output/s4g_image_geometry_manifest.csv" \
        --clean-list "$project/Foreground Masking/Optimisation/clean_galaxies_final20.txt" \
        --sep-best "$output_root/SEP_cross_validation/sep_toy_cross_validation_best.json" \
        --mto-best "$output_root/MTObjects_cross_validation/mtobjects_toy_cross_validation_best.json" \
        --mtobjects-root /root/mtobjects-linux-final20 \
        --output-root "$application_root" --expected-galaxies 182 >> "$log" 2>&1
    printf '[%s] Runner exited with code %s.\n' "$(date '+%F %T')" "$?" >> "$log"
    sleep 30
done
