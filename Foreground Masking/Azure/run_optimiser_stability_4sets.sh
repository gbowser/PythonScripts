#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
venv_path="${VENV_PATH:-$repo_root/.venv-azure-mtobjects}"
manifest="${MANIFEST:-/home/azureuser/data/mtobjects-182/manifest/azure_mtobjects_182_manifest.csv}"
result_root="${RESULT_ROOT:-/home/azureuser/data/results/optimiser-stability-4sets-20260804}"
wait_pid="${WAIT_PID:-}"
workers="${WORKERS:-8}"
max_images="${MAX_IMAGES:-20}"
initial_points="${INITIAL_POINTS:-8}"
max_iter="${MAX_ITER:-32}"
seeds="${SEEDS:-202608041 202608042 202608043 202608044}"

cd "$repo_root"
source "$venv_path/bin/activate"
export FOREGROUND_MASKING_PC="${FOREGROUND_MASKING_PC:-Desktop}"
export MTOBJECTS_ROOT="${MTOBJECTS_ROOT:-/home/azureuser/src/mtobjects}"

mkdir -p "$result_root/logs"

if [[ -n "$wait_pid" ]]; then
  echo "Waiting for prerequisite PID $wait_pid before stability study."
  while kill -0 "$wait_pid" 2>/dev/null; do
    sleep 30
  done
fi

run_one() {
  local seed="$1"
  local name="$2"
  local script="$3"
  local outdir="$4"
  shift 4
  mkdir -p "$outdir"
  echo "[$(date '+%F %T')] Starting $name seed=$seed"
  python "$script" \
    --manifest "$manifest" \
    --output-dir "$outdir" \
    --max-images "$max_images" \
    --initial-points "$initial_points" \
    --max-iter "$max_iter" \
    --workers "$workers" \
    --seed "$seed" \
    "$@" \
    > "$result_root/logs/${name}_seed_${seed}.out.log" \
    2> "$result_root/logs/${name}_seed_${seed}.err.log"
  echo "[$(date '+%F %T')] Finished $name seed=$seed"
}

for seed in $seeds; do
  seed_root="$result_root/seed_$seed"
  run_one "$seed" "sep_spike_gate" "Foreground Masking/Optimisation/optimise_spike_gate_SEP.py" "$seed_root/sep_spike_gate" --no-progress-galaxies
  run_one "$seed" "sep_toy_objects" "Foreground Masking/Optimisation/optimise_toy_objects_SEP.py" "$seed_root/sep_toy_objects"
  run_one "$seed" "spike_gate_MTObjects" "Foreground Masking/Optimisation/optimise_spike_gate_MTObjects.py" "$seed_root/spike_gate_MTObjects" --no-progress-galaxies
  run_one "$seed" "toy_objects_MTObjects" "Foreground Masking/Optimisation/optimise_toy_objects_MTObjects.py" "$seed_root/toy_objects_MTObjects"
done

python "Foreground Masking/Azure/build_stability_parameter_workbook.py" \
  --run-root "$result_root" \
  --output "$result_root/optimiser_parameter_stability_4sets.xlsx" \
  > "$result_root/logs/workbook.out.log" \
  2> "$result_root/logs/workbook.err.log"

echo "[$(date '+%F %T')] Stability study complete: $result_root/optimiser_parameter_stability_4sets.xlsx"
