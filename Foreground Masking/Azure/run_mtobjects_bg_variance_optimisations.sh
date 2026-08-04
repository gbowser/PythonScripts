#!/usr/bin/env bash
set -euo pipefail

# Run the MTObjects toy-object and Spike Gate optimisations on an Azure Linux VM,
# allowing bg_variance to be optimised at the high-precision interactive step.
#
# Example:
#   bash "Foreground Masking/Azure/run_mtobjects_bg_variance_optimisations.sh" \
#     /data/manifest.csv /data/results

manifest="${1:-/data/manifest.csv}"
result_root="${2:-/data/results}"
workers="${WORKERS:-32}"
max_images="${MAX_IMAGES:-20}"
seed="${SEED:-20260804}"
bg_variance_min="${BG_VARIANCE_MIN:-0.0001}"
bg_variance_max="${BG_VARIANCE_MAX:-10000.0}"
bg_variance_step="${BG_VARIANCE_STEP:-0.0001}"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
venv_path="${VENV_PATH:-$repo_root/.venv-azure-mtobjects}"
mtobjects_root="${MTOBJECTS_ROOT:-$(dirname "$repo_root")/mtobjects}"
run_stamp="$(date +%Y%m%d_%H%M%S)"
log_dir="$result_root/logs/mtobjects_bg_variance_$run_stamp"
queue_log="$log_dir/queue.log"

mkdir -p "$log_dir" "$result_root/mtobjects-toy-bg-variance" "$result_root/mtobjects-spike-bg-variance"

if [[ ! -f "$manifest" ]]; then
  echo "Manifest not found: $manifest" >&2
  exit 1
fi

if [[ ! -d "$mtobjects_root" ]]; then
  echo "MTObjects root not found: $mtobjects_root" >&2
  exit 1
fi

if [[ ! -f "$venv_path/bin/activate" ]]; then
  echo "Virtual environment not found: $venv_path" >&2
  echo "Run Foreground Masking/Azure/bootstrap_mtobjects_ubuntu.sh first, or set VENV_PATH." >&2
  exit 1
fi

runner="$log_dir/run_queue.sh"
cat > "$runner" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$repo_root"
source "$venv_path/bin/activate"
export MTOBJECTS_ROOT="$mtobjects_root"

echo "[\$(date '+%F %T')] Starting MTObjects toy-object bg_variance optimisation"
python "Foreground Masking/Optimisation/optimise_toy_objects_MTObjects.py" \\
  --manifest "$manifest" \\
  --output-dir "$result_root/mtobjects-toy-bg-variance" \\
  --max-images "$max_images" \\
  --workers "$workers" \\
  --seed "$seed" \\
  --bg-variance-min "$bg_variance_min" \\
  --bg-variance-max "$bg_variance_max" \\
  --bg-variance-step "$bg_variance_step" \\
  > "$log_dir/toy_objects.out.log" \\
  2> "$log_dir/toy_objects.err.log"
echo "[\$(date '+%F %T')] Finished MTObjects toy-object optimisation"

echo "[\$(date '+%F %T')] Starting MTObjects Spike Gate bg_variance optimisation"
python "Foreground Masking/Optimisation/optimise_spike_gate_MTObjects.py" \\
  --manifest "$manifest" \\
  --output-dir "$result_root/mtobjects-spike-bg-variance" \\
  --mtobjects-root "$mtobjects_root" \\
  --max-images "$max_images" \\
  --workers "$workers" \\
  --seed "$seed" \\
  --bg-variance-min "$bg_variance_min" \\
  --bg-variance-max "$bg_variance_max" \\
  --bg-variance-step "$bg_variance_step" \\
  > "$log_dir/spike_gate.out.log" \\
  2> "$log_dir/spike_gate.err.log"
echo "[\$(date '+%F %T')] Finished MTObjects Spike Gate optimisation"
EOF

chmod +x "$runner"
nohup "$runner" > "$queue_log" 2>&1 &
pid="$!"

echo "Started MTObjects bg_variance optimisation queue."
echo "PID: $pid"
echo "Queue log: $queue_log"
echo "Toy log: $log_dir/toy_objects.out.log"
echo "Spike log: $log_dir/spike_gate.out.log"
