# Existing WSL optimisation launchers

The two root wrappers now live here:

- `run_clean22_watchdog.sh`: starts the existing clean22 cross-validation watcher.
- `run_galaxy150_pipeline_foreground.sh`: runs the existing resumable galaxy150
  MTO/SEP sequence.

Their existing WSL distributions, absolute research-data paths and scientific
parameters are unchanged. The Windows supervisor
`Foreground Masking/Optimisation/supervise_galaxy150_pipeline_windows.ps1` now
references the relocated wrapper, including quoting for its path's spaces.
No optimisation job or WSL process was launched during the reorganisation.
