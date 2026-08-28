param([string]$OutputDirectory = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\final20_toy_optimisation')
$ErrorActionPreference = 'Stop'

function E([object]$Value) { [System.Net.WebUtility]::HtmlEncode([string]$Value) }
function Table([string[]]$Headers, [object[]]$Rows) {
    $text = '<table><thead><tr>' + (($Headers | ForEach-Object { '<th>' + (E $_) + '</th>' }) -join '') + '</tr></thead><tbody>'
    foreach ($row in $Rows) { $text += '<tr>' + (($row | ForEach-Object { '<td>' + (E $_) + '</td>' }) -join '') + '</tr>' }
    return $text + '</tbody></table>'
}

$rankingPath = Join-Path $OutputDirectory '..\final_cleanest20_severity_review\final_cleanest20_ranking.csv'
$sepRun = Join-Path $OutputDirectory 'SEP\20260828_064912'
$mtoRun = Join-Path $OutputDirectory 'MTObjects\20260828_065235'
$ranking = Import-Csv -LiteralPath $rankingPath | Where-Object selected_top20 -eq 'yes'
$sep = Get-Content -Raw -LiteralPath (Join-Path $sepRun 'sep_toy_object_optimisation_best.json') | ConvertFrom-Json
$mto = Get-Content -Raw -LiteralPath (Join-Path $mtoRun 'mtobjects_parameter_optimisation_best.json') | ConvertFrom-Json
$rankRows = foreach ($r in $ranking) { ,@($r.final_rank,$r.name,$r.severity,$r.prior_blind_group,$r.selection_basis) }
$sepParams = foreach ($p in $sep.params.PSObject.Properties) { ,@($p.Name,[string]$p.Value) }
$mtoParams = foreach ($p in $mto.params.PSObject.Properties) { ,@($p.Name,[string]$p.Value) }
$batchRows = @(
    ,@('Catalogue batch 1','49','11','7','31','Gaia-zero/hybrid'),
    ,@('Catalogue batch 2','30','0','1','29','Next positive-score fields'),
    ,@('Catalogue batch 3','30','0','0','30','Clean-reference similarity'),
    ,@('Blind consistency audit','21','10','3','8','Original-only shuffled audit'),
    ,@('Remaining blind review','71','0','1','70','All previously unreviewed fields')
)
$designRows = @(
    ,@('Calibration galaxies','20'),,@('Injection sets','Cross-validation and winner-selection'),
    ,@('Toys per galaxy per set','6'),,@('Toys per set','120'),,@('Total materialised toys','240'),
    ,@('Type mixture','50% stars; 20% clusters; 30% galaxies'),,@('Peak amplitude','6–30 robust image sigma'),
    ,@('Truth dilation','1 pixel'),,@('Trials per algorithm','40 (8 initial + 32 adaptive)'),
    ,@('Workers','4'),,@('Detection image','Original science image')
)
$sepMetrics = @(
    ,@('Status',$sep.status),,@('Objective (minimised)',('{0:F6}' -f [double]$sep.objective)),
    ,@('Recovery score',('{0:F6}' -f [double]$sep.score)),,@('Toy detection rate',('{0:P2}' -f [double]$sep.toy_detection_rate)),
    ,@('Mean toy recall',('{0:P2}' -f [double]$sep.mean_toy_recall)),,@('Mean pixel recall',('{0:P2}' -f [double]$sep.mean_recall)),
    ,@('Mean pixel precision',('{0:P3}' -f [double]$sep.mean_precision)),,@('Mean F-score',('{0:F4}' -f [double]$sep.mean_f_score)),
    ,@('Mean masked fraction',('{0:P2}' -f [double]$sep.mean_masked_fraction)),,@('Worst masked fraction',('{0:P2}' -f [double]$sep.max_masked_fraction)),
    ,@('False-positive fraction',('{0:P2}' -f [double]$sep.false_positive_fraction))
)
$mtoMetrics = @(
    ,@('Status',$mto.status),,@('Penalised objective',('{0:F1}' -f [double]$mto.objective)),
    ,@('Recovery-infeasible flag',[string]$mto.recovery_infeasible),,@('Toy detection rate',('{0:P2}' -f [double]$mto.toy_detection_rate)),
    ,@('Mean toy recall',('{0:P2}' -f [double]$mto.mean_toy_recall)),,@('Mean masked fraction',('{0:P4}' -f [double]$mto.mean_masked_fraction)),
    ,@('Worst masked fraction',('{0:P4}' -f [double]$mto.max_masked_fraction))
)
$paths = @(
    ,@('Final ranking',(Resolve-Path $rankingPath).Path),
    ,@('Clean-list input','C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\Optimisation\clean_galaxies_final20.txt'),
    ,@('Paired manifest',(Join-Path $OutputDirectory 'paired_injections\paired_toy_injection_manifest.json')),
    ,@('SEP run',$sepRun),,@('MTObjects run',$mtoRun)
)

$html = @"
<!doctype html><html><head><meta charset="utf-8"><style>
@page { size:A4; margin:1.7cm; } body{font-family:Calibri,Arial,sans-serif;font-size:10.5pt;line-height:1.28;color:#222}
h1{font-size:18pt;color:#17365d;border-bottom:1px solid #9fbad0;padding-bottom:3pt;page-break-after:avoid} h2{font-size:13pt;color:#365f91;page-break-after:avoid}
.title{text-align:center;font-size:24pt;font-weight:bold;color:#17365d;margin-top:50pt}.subtitle{text-align:center;color:#666;margin-bottom:30pt}
table{border-collapse:collapse;width:100%;margin:8pt 0 14pt 0;font-size:9pt} th{background:#d9eaf7;font-weight:bold} th,td{border:1px solid #8a8a8a;padding:4pt;vertical-align:top}
.warning{border-left:5px solid #c00000;background:#fce4e4;padding:8pt}.note{border-left:5px solid #4472c4;background:#eaf2f8;padding:8pt}.small{font-size:8.5pt;color:#555;word-break:break-all}
</style></head><body>
<div class="title">Selection of Low-Contamination Galaxies and Toy-Object Mask Optimisation</div><div class="subtitle">Final report — 28 August 2026</div>
<h1>Executive summary</h1><p>All 182 S4G galaxy fields were reviewed. Under the final blind visual criterion, 10 were Clean, 4 Ambiguous and 168 Polluted. Because fewer than 20 were strictly Clean, a final severity exercise selected the 20 least polluted fields. These 20 are calibration fields; they are not 20 equally uncontaminated galaxies.</p>
<p>SEP completed 40 paired-toy trials and produced a feasible candidate with toy detection rate $(E ('{0:P1}' -f [double]$sep.toy_detection_rate)) and mean toy recall $(E ('{0:P1}' -f [double]$sep.mean_toy_recall)). MTObjects completed 40 trials but recovered no toys. Its recorded best row is infeasible and must not be used as a production parameter set.</p>
<h1>1. Objective and definitions</h1><p>The objective was to find fields with the fewest bright unrelated foreground objects for foreground-mask calibration. Galaxy nuclei, bars, rings, arms and coherent star-forming structure were not contaminants. Global visual cleanliness and bar-profile-specific impact were treated separately.</p>
<h1>2. Selection process</h1><h2>2.1 Automated evidence</h2><p>A Gaussian-smoothed 3.6 μm image was subtracted from the centred original, the central galaxy region was excluded, and positive compact residuals were measured. Photutils/DAO-style detections were supplemented with Gaia DR3 astrometric evidence and 2MASS point-source evidence. Detections on strong galaxy structure were downweighted, not discarded.</p><p>Image-only scoring remained sensitive to spiral arms, rings and star-forming knots. NGC1097 demonstrated that automated evidence could not replace visual assessment.</p>
<h2>2.2 Review stages</h2>$(Table @('Stage','N','Clean','Ambiguous','Polluted','Basis') $batchRows)
<p>Catalogue panels contained the original, Gaussian residual and catalogue overlay. Red marked scored 2MASS sources and yellow marked weaker Gaia evidence. The overlays were supporting evidence rather than automatic labels.</p>
<h2>2.3 Ambiguous-profile experiment</h2><p>Eight ambiguous fields were tested with manually positioned circular masks and before/after bar-major-axis profiles. Three were labelled Clean and five Polluted. All measured profile changes were zero because the masks did not intersect the narrow profile aperture; the labels described global field contamination, not demonstrated profile contamination.</p>
<h2>2.4 Blind consistency and full-population review</h2><p>A 21-field identity-hidden, original-only audit gave 10 Clean, 3 Ambiguous and 8 Polluted, with 14/19 (74%) agreement with previous decisions. The remaining 71 fields were then reviewed identically: 0 Clean, 1 Ambiguous and 70 Polluted. Final full-population totals were 10 Clean, 4 Ambiguous and 168 Polluted.</p>
<h2>2.5 Severity shortlist</h2><p>A blind shortlist combined 10 Clean, 4 Ambiguous and 16 low-score Polluted fields. Severity was 0 none, 1 minor, 2 moderate and 3 severe. Counts were 12, 2, 4 and 12 respectively. Severity was primary; prior blind group and then clean-reference similarity broke ties.</p><div class="note">Only 18 fields scored 0–2. Positions 19–20 cross the severity-3 boundary: NGC4102 was retained from the Ambiguous group and NGC0918 was the nearest remaining Polluted field to the Clean feature pattern.</div>
<h1>3. Final cleanest 20</h1>$(Table @('Rank','Galaxy','Severity','Prior group','Selection basis') $rankRows)<p>Ranks within a severity tier are tie-break order, not a continuous contamination measurement. The first 10 are blind-confirmed Clean; ranks 11–20 broaden the calibration population to the requested 20.</p>
<h1>4. Paired Toy Objects design</h1>$(Table @('Design item','Value') $designRows)<p>One shared immutable manifest supplied identical toys to SEP and MTObjects. It records per-galaxy seeds and SHA-256 checksums for science images, injection payloads, deltas and truth masks. The independent winner-selection set was generated but not used in these initial optimisation runs.</p>
<h1>5. SEP result</h1>$(Table @('Metric','SEP optimum') $sepMetrics)<h2>Best SEP parameters</h2>$(Table @('Parameter','Value') $sepParams)<p>The optimum respected the 15% worst-image ceiling (12.93%) and recovered about 41% of toys. Pixel precision was low because much incremental mask area lay outside toy truth. This is a feasible candidate requiring independent winner-selection and visual validation.</p>
<h1>6. MTObjects result</h1>$(Table @('Metric','Recorded result') $mtoMetrics)<h2>Recorded MTObjects row — diagnostic only</h2>$(Table @('Parameter','Value') $mtoParams)<div class="warning"><b>Do not use these MTObjects parameters in production.</b> Toy recovery was zero and objective 59.0 is the explicit infeasibility penalty. Mean mask coverage was only about 0.0016%. The current background/significance/area search regime is mismatched to these data.</div>
<h1>7. Recommended next step</h1><p>Validate SEP on the independent winner-selection set and examine its low precision per galaxy. For MTObjects, calibrate background variance and broaden the source-significance/area regime with a small diagnostic grid; rerun optimisation only after at least one configuration demonstrates non-zero toy recovery. Compare both methods on the identical winner-selection payloads.</p>
<h1>8. Reproducibility paths</h1><div class="small">$(Table @('Artifact','Path') $paths)</div>
</body></html>
"@

$localWork = Join-Path $env:TEMP 'clean_galaxy_report_com'
New-Item -ItemType Directory -Path $localWork -Force | Out-Null
$htmlPath = Join-Path $localWork 'Clean_Galaxy_Selection_and_Toy_Object_Optimisation_source.html'
$localDocx = Join-Path $localWork 'Clean_Galaxy_Selection_and_Toy_Object_Optimisation.docx'
$localPdf = Join-Path $localWork 'Clean_Galaxy_Selection_and_Toy_Object_Optimisation.pdf'
$docxPath = Join-Path $OutputDirectory 'Clean_Galaxy_Selection_and_Toy_Object_Optimisation.docx'
$pdfPath = Join-Path $OutputDirectory 'Clean_Galaxy_Selection_and_Toy_Object_Optimisation.pdf'
[System.IO.File]::WriteAllText($htmlPath,$html,[System.Text.UTF8Encoding]::new($true))
Write-Output 'HTML source written.'
$word=$null;$doc=$null
try {
    $word=New-Object -ComObject Word.Application; $word.Visible=$false; $word.DisplayAlerts=0; Write-Output 'Word started.'
    $doc=$word.Documents.Open($htmlPath,$false,$false); Write-Output 'HTML opened in Word.'
    $doc.SaveAs2($localDocx,16); Write-Output 'Local DOCX saved.'
    $doc.ExportAsFixedFormat($localPdf,17); Write-Output 'Local PDF exported.'
    $doc.Close($false);$doc=$null;$word.Quit();$word=$null
} finally {
    if($doc -ne $null){try{$doc.Close($false)}catch{}}
    if($word -ne $null){try{$word.Quit()}catch{}}
}
Copy-Item -LiteralPath $localDocx -Destination $docxPath -Force
Copy-Item -LiteralPath $localPdf -Destination $pdfPath -Force
Copy-Item -LiteralPath $htmlPath -Destination (Join-Path $OutputDirectory 'Clean_Galaxy_Selection_and_Toy_Object_Optimisation_source.html') -Force
Write-Output 'Completed files copied to Dropbox.'
Write-Output "DOCX=$docxPath";Write-Output "PDF=$pdfPath"
