# Azure Linux MTObjects optimisation

This folder contains the headless Linux setup for all four foreground-mask
optimisers. It targets an Ubuntu x86-64 Azure VM and does not require a GPU.

## Recommended first machine

For a compatibility test, use an available x86-64 Ubuntu 24.04 LTS VM with
2 vCPUs and 8 GiB RAM; the initial verified deployment used `Standard_D2ns_v6`
in UK South. Resize to 8 vCPUs for the full parallel benchmark. Start with
pay-as-you-go while testing and move to Spot only after restart/resume has been
verified.

Set a small subscription budget alert before creating the VM. Stopping it in
the guest OS is not sufficient to stop compute billing: deallocate or delete
the VM in Azure when the run is finished.

## Install and verify

Clone `PythonScripts` and `CarolineHaigh/mtobjects` beside one another, then run
from the `PythonScripts` checkout:

```bash
bash "Foreground Masking/Azure/bootstrap_mtobjects_ubuntu.sh"
```

The script installs GCC, GSL, and Tkinter; builds MTObjects' four shared
libraries; creates a Python virtual environment; installs the scientific
packages; and loads every MTObjects library as a smoke test.

## Run

Copy the input manifest, FITS images, and smooth-model files to the VM, retaining
their relative layout or supplying an Azure-specific manifest. The manifest's
`image_path` values must be valid Linux paths (for example `/data/images/...`),
not the existing `C:\` or `D:\` paths. Then:

```bash
source .venv-azure-mtobjects/bin/activate
export MTOBJECTS_ROOT="$(dirname "$PWD")/mtobjects"
python "Foreground Masking/Optimisation/optimise_toy_objects_MTObjects.py" \
  --manifest /data/manifest.csv \
  --output-dir /data/results/mtobjects-toy \
  --workers 8
```

`--workers` parallelises images inside a trial. Optuna trials remain sequential,
so TPE behaviour is stable and only the parent process writes result files.
Use `--workers 1` to reproduce the original execution path.

The other three optimisers use the same worker model:

```bash
python "Foreground Masking/Optimisation/optimise_toy_objects_SEP.py" \
  --manifest /data/manifest.csv --output-dir /data/results/sep-toy --workers 8

python "Foreground Masking/Optimisation/optimise_spike_gate_SEP.py" \
  --manifest /data/manifest.csv --output-dir /data/results/sep-spike --workers 8

python "Foreground Masking/Optimisation/optimise_spike_gate_MTObjects.py" \
  --manifest /data/manifest.csv --output-dir /data/results/mtobjects-spike \
  --mtobjects-root "$(dirname "$PWD")/mtobjects" --workers 8
```

Each optimiser keeps Optuna trials sequential and returns per-image results in
manifest order, so a fixed seed produces the same score and parameter sequence
with `--workers 1` and `--workers 8`. On Linux the pool uses `fork`, allowing
prepared image arrays to be shared copy-on-write. On Windows it uses `spawn`.
