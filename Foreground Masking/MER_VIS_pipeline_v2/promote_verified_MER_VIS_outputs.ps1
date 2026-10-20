$ErrorActionPreference='Stop'
$projectRoot='C:\Users\gordo\Documents\Github\PythonScripts\Euclid'
$dataRoot='D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid'
$workRoot='C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\MER_VIS_pipeline_v2'
$reportsRoot=Join-Path $projectRoot 'reports'
$currentReports=Join-Path $reportsRoot 'MER_VIS_current'
$geo=Join-Path $dataRoot 'Euclid_MER_VIS_geometry'
$newGeo=Join-Path $dataRoot 'Euclid_MER_VIS_geometry_v2'
$oldGeo=Join-Path $dataRoot 'Euclid_MER_VIS_geometry_superseded'
$cards=Join-Path $dataRoot 'MER_VIS_galaxy_reports\all_2777'
$newCards=Join-Path $dataRoot 'MER_VIS_galaxy_reports\all_2777_v2'
$oldCards=Join-Path $dataRoot 'MER_VIS_galaxy_reports\all_2777_superseded'
function Assert-Within([string]$target,[string]$root) {
 $resolved=[IO.Path]::GetFullPath($target);$boundary=[IO.Path]::GetFullPath($root).TrimEnd('\')+'\'
 if (-not $resolved.StartsWith($boundary,[StringComparison]::OrdinalIgnoreCase)) { throw "Unsafe target outside intended root: $resolved" }
 return $resolved
}
foreach($target in @($geo,$newGeo,$oldGeo,$cards,$newCards,$oldCards)) { $null=Assert-Within $target $dataRoot }
$null=Assert-Within $currentReports $reportsRoot
$verification=Get-Content -LiteralPath (Join-Path $newCards 'MER_VIS_report_verification.json') -Raw | ConvertFrom-Json
if ($verification.galaxies -ne 2777 -or $verification.PDF_embedded_cards -ne 2777 -or -not $verification.source_manifest_unchanged) { throw 'New galaxy outputs are not verified' }
foreach($file in @('Euclid_MER_VIS_outcomes_summary.docx','Euclid_MER_VIS_disc_PA_and_inclination_explained.docx','Euclid_MER_VIS_outcomes_summary.pptx')) {
 if (-not (Test-Path -LiteralPath (Join-Path $workRoot ('current_report\output\'+$file)))) { throw "Missing report $file" }
}
if (-not (Test-Path -LiteralPath (Join-Path $workRoot 'current_report\comparison\comparison_summary.md'))) { throw 'Missing current comparison' }
if ((Test-Path -LiteralPath $oldGeo) -or (Test-Path -LiteralPath $oldCards)) { throw 'Superseded staging directory already exists' }
New-Item -ItemType Directory -Path (Join-Path $currentReports 'audit') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $currentReports 'comparison') -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $geo 'MER_VIS_local_geometry_manifest.csv') -Destination (Join-Path $currentReports 'audit\original_v1_geometry_manifest.csv')
Copy-Item -LiteralPath (Join-Path $geo 'MER_VIS_local_geometry_run.json') -Destination (Join-Path $currentReports 'audit\original_v1_run.json')
Copy-Item -LiteralPath (Join-Path $geo 'MER_VIS_local_geometry_summary.json') -Destination (Join-Path $currentReports 'audit\original_v1_summary.json')
Copy-Item -LiteralPath (Join-Path $cards 'MER_VIS_report_summary.json') -Destination (Join-Path $currentReports 'audit\original_v1_report_summary.json')
Copy-Item -Path (Join-Path $workRoot 'current_report\output\*') -Destination $currentReports -Force
Copy-Item -Path (Join-Path $workRoot 'current_report\comparison\*') -Destination (Join-Path $currentReports 'comparison') -Force
Copy-Item -LiteralPath (Join-Path $newGeo 'MER_VIS_v2_summary.json') -Destination (Join-Path $currentReports 'audit\current_v2_summary.json')
Copy-Item -LiteralPath (Join-Path $newGeo 'MER_VIS_failed_recovery_audit.json') -Destination (Join-Path $currentReports 'audit\current_v2_recovery_audit.json')
Copy-Item -LiteralPath (Join-Path $newGeo 'MER_VIS_visual_review_audit.json') -Destination (Join-Path $currentReports 'audit\current_visual_review_audit.json')
Copy-Item -LiteralPath (Join-Path $newGeo 'MER_VIS_v2_run.json') -Destination (Join-Path $currentReports 'audit\current_v2_run.json')
Copy-Item -LiteralPath (Join-Path $newCards 'MER_VIS_report_verification.json') -Destination (Join-Path $currentReports 'audit\current_report_verification.json')
# Move only the four explicitly checked result directories. Raw cutouts are never moved.
Move-Item -LiteralPath $geo -Destination $oldGeo
Move-Item -LiteralPath $newGeo -Destination $geo
Move-Item -LiteralPath $cards -Destination $oldCards
Move-Item -LiteralPath $newCards -Destination $cards
$runPath=Join-Path $cards 'MER_VIS_report_run.json'
$run=Get-Content -LiteralPath $runPath -Raw | ConvertFrom-Json
$run.source=Join-Path $geo 'MER_VIS_local_geometry_manifest.csv'
$run | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $runPath -Encoding utf8
# Delete only superseded products after the verified replacements occupy canonical paths.
foreach($obsolete in @($oldGeo,$oldCards)) {
 $checked=Assert-Within $obsolete $dataRoot
 Remove-Item -LiteralPath $checked -Recurse -Force
}
$pilot=Join-Path $dataRoot 'MER_VIS_galaxy_reports\pilot_10'
if (Test-Path -LiteralPath $pilot) { $checked=Assert-Within $pilot (Join-Path $dataRoot 'MER_VIS_galaxy_reports');Remove-Item -LiteralPath $checked -Recurse -Force }
$inventory=Get-Content -LiteralPath (Join-Path $workRoot 'superseded_report_inventory.json') -Raw | ConvertFrom-Json
foreach($entry in $inventory) {
 foreach($file in $entry.files) { $checked=Assert-Within $file $reportsRoot;if (Test-Path -LiteralPath $checked) { Remove-Item -LiteralPath $checked -Force } }
 $checked=Assert-Within $entry.directory $reportsRoot
 if ((Test-Path -LiteralPath $checked) -and @(Get-ChildItem -LiteralPath $checked -Force).Count -eq 0) { Remove-Item -LiteralPath $checked -Force }
}
'Updated outputs and removed superseded versions.'
