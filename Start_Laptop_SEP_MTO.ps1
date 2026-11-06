param([switch]$PrintParameterSources)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$env:FOREGROUND_MASKING_PC = 'Laptop'
$env:PYTHONPATH = $null
Set-Location -LiteralPath $root
$python = Join-Path $root '.venv\Scripts\python.exe'
$config = Join-Path $root 'laptop_setup\config'
$research = 'C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects'
$sep = Join-Path $config 'sep-diagnostic-rejected-fold20.json'
$mto = Join-Path $research 'clean22_haigh_aligned_bright150_galaxy150_sep_sensitivity\MTObjects_cross_validation\mtobjects_toy_cross_validation_best.json'
foreach ($path in @($sep,$mto,(Join-Path $config 'paired-injections-laptop.json'))) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Required configuration missing: $path" }
}
Write-Host 'SEP: REJECTED optimisation diagnostic fold 20. MTO: FINAL winner. See laptop_setup/config/provenance.json.'
$argsList = @((Join-Path $root 'Foreground Masking\Interactive tools\interactive_toy_objects_SEP_MTObjects.py'), '--pc', 'Laptop', '--manifest', (Join-Path $root 'Erwin_s4g_image_downloader\geometry_output\s4g_image_geometry_manifest.csv'), '--mtobjects-root', (Join-Path (Split-Path $root -Parent) 'mtobjects'), '--sep-best', $sep, '--mto-best', $mto, '--injection-manifest', (Join-Path $config 'paired-injections-laptop.json'), '--output', (Join-Path $root 'laptop_setup\SEP_MTO_comparisons'))
if ($PrintParameterSources) { $argsList += '--print-parameter-sources' }
& $python @argsList
exit $LASTEXITCODE
