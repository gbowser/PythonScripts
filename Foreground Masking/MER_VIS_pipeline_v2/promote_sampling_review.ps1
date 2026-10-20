$ErrorActionPreference='Stop'
$taskRoot='C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\MER_VIS_pipeline_v2'
$dataRoot='D:\Dropbox\Public Documents\UCLAN\MSc Research\Euclid'
$projectRoot='C:\Users\gordo\Documents\Github\PythonScripts\Euclid'
$reportRoot=Join-Path $projectRoot 'reports\MER_VIS_current'
$cardsRoot=Join-Path $dataRoot 'MER_VIS_galaxy_reports'
$current=Join-Path $cardsRoot 'all_2777'
$staging=Join-Path $cardsRoot 'all_2777_sampling_review'
$obsolete=Join-Path $cardsRoot 'all_2777_superseded_sampling'
$verification=Get-Content -Raw -LiteralPath (Join-Path $staging 'MER_VIS_report_verification.json') | ConvertFrom-Json
if($verification.galaxies -ne 2777 -or $verification.PDF_files -ne 47 -or -not $verification.source_manifest_unchanged){throw 'Unverified staging report collection'}
if(Test-Path -LiteralPath $obsolete){throw 'Unexpected obsolete target already exists'}
$audit=Join-Path $reportRoot 'audit'
New-Item -ItemType Directory -Path $audit -Force | Out-Null
foreach($file in @('MER_VIS_report_summary.json','MER_VIS_report_verification.json','MER_VIS_report_review_index.csv')) {Copy-Item -LiteralPath (Join-Path $current $file) -Destination (Join-Path $audit ('before_sampling_review_'+$file)) -Force}
Copy-Item -LiteralPath (Join-Path $taskRoot 'review_audit\before_sampling_review_manifest.csv') -Destination (Join-Path $audit 'before_sampling_review_geometry_manifest.csv') -Force
Copy-Item -LiteralPath (Join-Path $taskRoot 'review_audit\review_consistency_checks.json') -Destination $audit -Force
Copy-Item -LiteralPath (Join-Path $taskRoot 'review_audit\sampling_review_audit.json') -Destination $audit -Force
foreach($name in @('Euclid_MER_VIS_outcomes_summary.docx','Euclid_MER_VIS_disc_PA_and_inclination_explained.docx')) {Copy-Item -LiteralPath (Join-Path $taskRoot ('current_report\output\'+$name)) -Destination (Join-Path $reportRoot $name) -Force}
Copy-Item -LiteralPath (Join-Path $taskRoot 'current_report\output\Euclid_MER_VIS_outcomes_summary_reviewed.pptx') -Destination (Join-Path $reportRoot 'Euclid_MER_VIS_outcomes_summary.pptx') -Force
$oldWord=Join-Path $reportRoot 'Euclid_MER_VIS_disc_PA_and_inclination_explained_updated.docx'
if(Test-Path -LiteralPath $oldWord){Remove-Item -LiteralPath $oldWord -Force}
$nameDest=Join-Path $reportRoot 'catalogue_names';New-Item -ItemType Directory -Path $nameDest -Force | Out-Null
Get-ChildItem -LiteralPath (Join-Path $taskRoot 'catalogue_names') -File | Copy-Item -Destination $nameDest -Force
$codeDest=Join-Path $projectRoot 'adaptive_MER_VIS'
foreach($name in @('fit_adaptive_MER_VIS_geometry.py','make_MER_VIS_galaxy_report_cards.py','generate_all_MER_VIS_galaxy_reports.py','assemble_parallel_MER_VIS_reports.py')) {Copy-Item -LiteralPath (Join-Path $taskRoot ('review_code\'+$name)) -Destination (Join-Path $codeDest $name) -Force}
foreach($name in @('apply_sampling_review.py','query_catalogue_names.py','query_hyperleda_names.py','query_simbad_aliases.py','assign_catalogue_names.py')) {Copy-Item -LiteralPath (Join-Path $taskRoot $name) -Destination (Join-Path $codeDest $name) -Force}
Move-Item -LiteralPath $current -Destination $obsolete
Move-Item -LiteralPath $staging -Destination $current
Copy-Item -LiteralPath (Join-Path $current 'MER_VIS_report_verification.json') -Destination (Join-Path $audit 'current_report_verification.json') -Force
Copy-Item -LiteralPath (Join-Path $dataRoot 'Euclid_MER_VIS_geometry\MER_VIS_v2_summary.json') -Destination (Join-Path $audit 'current_v2_summary.json') -Force
# The exact obsolete generated-report folder is checked before recursive deletion.
$resolved=[System.IO.Path]::GetFullPath($obsolete)
if($resolved -ne [System.IO.Path]::GetFullPath((Join-Path $cardsRoot 'all_2777_superseded_sampling')) -or -not $resolved.StartsWith([System.IO.Path]::GetFullPath($cardsRoot)+'\',[System.StringComparison]::OrdinalIgnoreCase)){throw 'Deletion boundary check failed'}
for($retry=0;$retry -lt 8;$retry++) {
 try {if(Test-Path -LiteralPath $resolved){Remove-Item -LiteralPath $resolved -Recurse -Force};break}
 catch {if($retry -eq 7){throw};Start-Sleep -Seconds 2}
}
Write-Output 'PROMOTED: 2777 PNGs and 47 PDFs; updated Word and PowerPoint; obsolete published versions deleted.'
