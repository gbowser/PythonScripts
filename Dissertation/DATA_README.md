# Historical degree-course data

On 17 November 2026 the user confirmed that the Gaia data from the completed
degree course are no longer needed. Removed:

- `1728381349715O-result.vot.gz`: Gaia DR1 Pleiades cone-query export.
- `Gaia Test1.vot.gz`: Gaia DR3 Pleiades query export.
- `mydata.csv` and `mydata-specific-params.csv`: Gaia query CSV exports.

Scripts and other course materials remain as historical source. Programs that
read these files cannot run without downloading/recreating their inputs; the
query examples are retained, but were not rerun. No deletion was made to the
current foreground-masking project's Gaia-derived rankings or code.

The deletion inventory and hashes are in research archive
`Repository_maintenance/2026-11-17_git_storage/deleted_gaia_data.json`.
