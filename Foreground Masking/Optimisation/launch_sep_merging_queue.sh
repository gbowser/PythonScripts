#!/usr/bin/env bash
set -euo pipefail

cd "/mnt/c/Users/gordo/Documents/Github/PythonScripts"
root="/mnt/d/Dropbox/Public Documents/UCLAN/MSc Research/Remove foreground objects/clean22_haigh_aligned_bright150_galaxy150_sep_sensitivity"
queue_log="$root/sep_merging_after_mto_queue_console.log"
queue_pid="$root/sep_merging_after_mto_queue.pid"

nohup bash "Foreground Masking/Optimisation/queue_sep_merging_after_mto.sh" >> "$queue_log" 2>&1 &
process_id=$!
printf '%s\n' "$process_id" > "$queue_pid"
printf 'Queued SEP merging experiment behind MTObjects (queue PID %s).\n' "$process_id"
