#!/usr/bin/env bash
set -u

base="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_displayed_frame_5toy_optimisation/MTObjects_multiseed_optimisation_pilot_v3"
runner="/root/run_mtobjects_multiseed_optimisation_pilot.sh"
complete="$base/multiseed_optimisation_pilot.complete"
failed="$base/multiseed_optimisation_pilot.failed"
log="$base/wsl_multiseed_optimisation_supervisor.log"

mkdir -p "$base"
printf '[%s] WSL-native pilot supervision started.\n' "$(date '+%F %T')" >> "$log"
while [[ ! -f "$complete" ]]; do
    if ! pgrep -f '[r]un_mtobjects_multiseed_optimisation_pilot.sh' >/dev/null; then
        [[ -f "$failed" ]] && rm -f "$failed"
        printf '[%s] Pilot runner absent; starting/resuming it.\n' "$(date '+%F %T')" >> "$log"
        bash "$runner" >> "$log" 2>&1
        exit_code=$?
        printf '[%s] Pilot runner returned code %s.\n' "$(date '+%F %T')" "$exit_code" >> "$log"
        [[ -f "$complete" ]] && break
        sleep 30
        continue
    fi
    sleep 60
done
printf '[%s] Pilot completion marker found; supervision finished.\n' "$(date '+%F %T')" >> "$log"
