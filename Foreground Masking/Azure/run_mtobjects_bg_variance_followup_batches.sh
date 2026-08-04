#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
venv_path="${VENV_PATH:-$repo_root/.venv-azure-mtobjects}"
mtobjects_root="${MTOBJECTS_ROOT:-$(dirname "$repo_root")/mtobjects}"
manifest="${MANIFEST:-/home/azureuser/data/mtobjects-20/manifest/azure_mtobjects_20_manifest.csv}"
result_root="${RESULT_ROOT:-/home/azureuser/data/results/mtobjects-bg-variance-rerun}"
stamp="$(date +%Y%m%d_%H%M%S)"
followup_root="$result_root/followup_$stamp"
log_dir="$followup_root/logs"

toy_best="${TOY_BEST:-$(find "$result_root/mtobjects-toy-bg-variance" -type f -name mtobjects_parameter_optimisation_best.json | sort | tail -n 1)}"
spike_best="${SPIKE_BEST:-$(find "$result_root/mtobjects-spike-bg-variance" -type f -name mtobjects_spike_optimisation_best.json | sort | tail -n 1)}"
sep_toy_best="${SEP_TOY_BEST:-$(find /home/azureuser/data/results/full-optimisers/sep-toy -type f -name sep_toy_object_optimisation_best.json | sort | tail -n 1)}"
sep_spike_best="${SEP_SPIKE_BEST:-$(find /home/azureuser/data/results/full-optimisers/sep-spike -type f -name sep_spike_optimisation_best.json | sort | tail -n 1)}"

mkdir -p "$log_dir"

cd "$repo_root"
source "$venv_path/bin/activate"
export MTOBJECTS_ROOT="$mtobjects_root"
export FOREGROUND_MASKING_PC="${FOREGROUND_MASKING_PC:-Desktop}"

echo "Follow-up root: $followup_root"
echo "Manifest: $manifest"
echo "MTObjects toy best: $toy_best"
echo "MTObjects spike best: $spike_best"
echo "SEP toy best: $sep_toy_best"
echo "SEP spike best: $sep_spike_best"

python "Foreground Masking/Batch tools/batch_sep_all_galaxies.py" \
  --manifest "$manifest" \
  --best-json "$sep_spike_best" \
  --output-dir "$followup_root/sep-spike" \
  --run-label "SEP Spike Gate support for MTObjects bg_variance rerun" \
  --replace-summary \
  > "$log_dir/sep_spike_batch.out.log" \
  2> "$log_dir/sep_spike_batch.err.log"

python "Foreground Masking/Batch tools/batch_sep_all_galaxies.py" \
  --manifest "$manifest" \
  --best-json "$sep_toy_best" \
  --output-dir "$followup_root/sep-toy" \
  --run-label "SEP Toy Object support for MTObjects bg_variance rerun" \
  --replace-summary \
  > "$log_dir/sep_toy_batch.out.log" \
  2> "$log_dir/sep_toy_batch.err.log"

python "Foreground Masking/Batch tools/apply_optimised_mtobjects_all_galaxies.py" \
  --manifest "$manifest" \
  --best-json "$spike_best" \
  --output-dir "$followup_root/mtobjects-spike" \
  --run-label "MTObjects Spike Gate bg_variance rerun" \
  > "$log_dir/mtobjects_spike_batch.out.log" \
  2> "$log_dir/mtobjects_spike_batch.err.log"

python "Foreground Masking/Batch tools/apply_optimised_mtobjects_all_galaxies.py" \
  --manifest "$manifest" \
  --best-json "$toy_best" \
  --output-dir "$followup_root/mtobjects-toy" \
  --run-label "MTObjects Toy Object bg_variance rerun" \
  > "$log_dir/mtobjects_toy_batch.out.log" \
  2> "$log_dir/mtobjects_toy_batch.err.log"

python "Foreground Masking/Utilities/make_all_method_galaxy_comparison_pngs.py" \
  --mtobjects-spike-summary "$followup_root/mtobjects-spike/mtobjects_optimised_apply_summary.csv" \
  --mtobjects-toy-summary "$followup_root/mtobjects-toy/mtobjects_optimised_apply_summary.csv" \
  --sep-spike-summary "$followup_root/sep-spike/sep_optimised_apply_summary.csv" \
  --sep-toy-summary "$followup_root/sep-toy/sep_optimised_apply_summary.csv" \
  --output-dir "$followup_root/all-method-comparison-pngs" \
  --require-all \
  > "$log_dir/composite_pngs.out.log" \
  2> "$log_dir/composite_pngs.err.log"

echo "Follow-up batches and composites complete: $followup_root"
