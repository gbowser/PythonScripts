# Laptop Codex Environment Briefing

This note is for Codex running on the laptop PC. It summarises the recent foreground-masking environment and code changes in the `PythonScripts` repository.

## Repository

Working repository:

```text
C:\Users\gordo\Documents\Github\PythonScripts
```

Main project folder:

```text
Foreground Masking
```

## Environment Changes

`optuna` has been added as a dependency for the optimisation scripts.

Check or install it with:

```powershell
pip install optuna
```

Or install from the repository dependency file:

```powershell
pip install -r requirements.txt
```

SEP is used by the SEP-based optimiser.

Check or install it with:

```powershell
pip install sep
```

The MTObjects optimiser depends on the local MTObjects setup already available on the main PC. On a fresh machine, confirm that the `MTObjects` command/package works before running the MTObjects optimiser.

Word is available on the main PC. LibreOffice is available at:

```text
C:\Program Files\LibreOffice\program\soffice.exe
```

## Main Scripts

MTObjects Spike Gate optimiser:

```text
Foreground Masking\optimise_mtobjects_spike_gate_parameters.py
```

Apply optimised MTObjects parameters to all galaxies:

```text
Foreground Masking\apply_optimised_mtobjects_all_galaxies.py
```

SEP Spike Gate optimiser:

```text
Foreground Masking\optimise_sep_spike_gate_parameters.py
```

## Documentation Files

MTObjects optimiser documentation:

```text
Foreground Masking\documentation\MTObjects Spike Gate Optuna Optimisation Documentation.docx
```

SEP optimiser documentation:

```text
Foreground Masking\documentation\SEP Spike Gate Optuna Optimisation Documentation.docx
```

This laptop handoff note:

```text
Foreground Masking\documentation\Laptop Codex Environment Briefing.md
```

## MTObjects Optimiser

Fresh run:

```powershell
python "Foreground Masking\optimise_mtobjects_spike_gate_parameters.py" --max-images 20 --initial-points 12 --max-iter 48
```

Resume run:

```powershell
python "Foreground Masking\optimise_mtobjects_spike_gate_parameters.py" --resume-output-dir "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\mtobjects spike optimisation\YYYYMMDD_HHMMSS" --max-images 20 --initial-points 12 --max-iter 48
```

Default output parent:

```text
D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\mtobjects spike optimisation
```

## SEP Optimiser

Fresh run:

```powershell
python "Foreground Masking\optimise_sep_spike_gate_parameters.py" --max-images 20 --initial-points 16 --max-iter 64
```

Resume run:

```powershell
python "Foreground Masking\optimise_sep_spike_gate_parameters.py" --resume-output-dir "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\sep spike optimisation\YYYYMMDD_HHMMSS" --max-images 20 --initial-points 16 --max-iter 64
```

Prepare-only check:

```powershell
python "Foreground Masking\optimise_sep_spike_gate_parameters.py" --max-images 20 --prepare-only
```

Default output parent:

```text
D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\sep spike optimisation
```

## Spike Gate Optimisation Logic

Both optimisers use Spike Gate samples from the intensity/bar-major profile as the target evidence for spike removal.

The Spike Gate stage identifies suspicious profile features that look like foreground-object contamination. These samples become the target regions Optuna tries to remove.

Optuna then searches image-processing parameters that maximise spike removal while minimising unrelated data loss.

The objective rewards:

- High masking coverage at Spike Gate sample locations.

The objective penalises:

- Masking in non-spike profile regions.
- High total masked image fraction.
- Broad profile damage away from spike locations.
- Large changes to the overall bar-major profile.

## MTObjects Process

The MTObjects optimiser uses MTObjects as the foreground-object detection and masking engine.

Optuna varies MTObjects-related parameters such as movement factor, distance, smoothing, minimum area, dilation radius, maximum object area, and elongation filtering.

The resulting best-parameter JSON can then be used by:

```text
Foreground Masking\apply_optimised_mtobjects_all_galaxies.py
```

That script processes galaxies using the optimised MTObjects settings and produces reports showing:

- Galaxy-centred original image.
- Original isophotes.
- Processed isophotes.
- Original bar-major profile.
- Processed bar-major profile.

## SEP Process

The SEP optimiser uses SEP as the foreground-object detection and masking engine instead of MTObjects.

Optuna varies SEP-related parameters including:

- Detection threshold.
- Minimum object area.
- Deblend threshold count.
- Deblend contrast.
- Background mesh size.
- Filter size.
- Dilation radius.
- Maximum object area.
- Maximum elongation.

SEP is expected to be faster than MTObjects, but it may be more sensitive to galaxy structure, deblending behaviour, and background-estimation settings.

## Running Both Optimisers Together

The MTObjects and SEP optimisers can run at the same time because they use separate scripts, separate default output folders, and separate Optuna SQLite study databases.

Do not point both scripts at the same `--resume-output-dir`.

Use the matching resume folder:

- MTObjects resumes under `mtobjects spike optimisation`.
- SEP resumes under `sep spike optimisation`.

Running both together is safe in normal use, but it may make the machine slower because both scripts repeatedly read FITS files and perform image-processing passes.

## Output Files

Both optimisers write timestamped output folders containing:

- Configuration JSON.
- Prepared galaxy/case CSV.
- Trial summary CSV.
- Trial detail CSV.
- Best-parameter JSON.
- Optuna SQLite study database.

The scripts also print timestamped progress to the terminal window during preparation and optimisation.

## Practical Cautions

Spike Gate samples are profile-based evidence, not ground truth. Visual review is still needed before treating a parameter set as final.

Some galaxies may be skipped if Spike Gate finds no spike samples.

If an optimisation run is interrupted, resume it with `--resume-output-dir` pointing at the timestamped folder from that run.

Do not resume the SEP script into an MTObjects output folder, or the MTObjects script into a SEP output folder.
