#!/usr/bin/env bash
set -euo pipefail

cd "/mnt/c/Users/gordo/Documents/Github/PythonScripts"
root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_haigh_aligned_bright150_galaxy150_sep_sensitivity"
sep="$root/SEP_cross_validation"
queue_log="$root/mto_after_sep_queue.log"

printf '[%s] MTObjects queued behind SEP.\n' "$(date --iso-8601=seconds)" >> "$queue_log"
while [[ ! -f "$sep/sep_toy_cross_validation_best.json" && ! -f "$sep/sep_toy_cross_validation_rejected.json" ]]; do
  sleep 20
done
printf '[%s] SEP terminal result found; starting MTObjects.\n' "$(date --iso-8601=seconds)" >> "$queue_log"
bash "Foreground Masking/Optimisation/launch_mto_bright150_galaxy150_16_workers.sh" >> "$queue_log" 2>&1
nohup /root/venvs/pythonscripts/bin/python \
  "Foreground Masking/Optimisation/watch_mto_bright150_galaxy150.py" \
  >/dev/null 2>&1 &
printf '[%s] MTObjects watchdog started.\n' "$(date --iso-8601=seconds)" >> "$queue_log"
