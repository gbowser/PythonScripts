param([switch]$PrepareOnly, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$env:FOREGROUND_MASKING_PC = 'Laptop'
$env:PYTHONPATH = $null
Set-Location -LiteralPath $root
$python = Join-Path $root '.venv\Scripts\python.exe'
$argsList = @((Join-Path $root 'Euclid\review_MER_VIS\review_MER_VIS.py'), '--data-root', 'C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research\Euclid', '--campaign', (Join-Path $root 'Euclid\review_MER_VIS\centre_policy_MER_VIS_campaign.json'), '--output', (Join-Path $root 'laptop_setup\MER_review'), '--port', '8878')
if ($PrepareOnly) { $argsList += '--prepare-only' }
if ($NoBrowser) { $argsList += '--no-browser' }
& $python @argsList
exit $LASTEXITCODE
