param(
  [string]$OutputDir='D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\documentation',
  [string]$WorkDir='C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\documentation\phase2_com_qa'
)
$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Force -Path $OutputDir,$WorkDir | Out-Null

$style=@'
<style>
@page { size: 8.5in 11in; margin: 1in; }
body { font-family: Calibri, Arial, sans-serif; font-size: 11pt; line-height: 1.20; color:#333; }
h1 { font-size:25pt; color:#0B2545; margin:0 0 5pt; }
h2 { font-size:16pt; color:#2E74B5; margin:16pt 0 8pt; page-break-after:avoid; }
h3 { font-size:13pt; color:#2E74B5; margin:12pt 0 6pt; page-break-after:avoid; }
p { margin:0 0 6pt; }
.kicker { color:#9A6A00; font-weight:bold; font-size:10pt; letter-spacing:1pt; }
.subtitle { font-size:13pt; color:#555; margin-bottom:12pt; }
.meta { font-size:10pt; margin-bottom:2pt; }
.rule { border-top:2px solid #2E74B5; margin:10pt 0 12pt; }
.callout { background:#E8EEF5; border-left:5px solid #2E74B5; padding:10pt 12pt; margin:8pt 0 12pt; }
table { width:100%; border-collapse:collapse; margin:8pt 0 12pt; page-break-inside:auto; }
th { background:#F2F4F7; color:#0B2545; font-weight:bold; }
th,td { border:1px solid #AAB4BE; padding:6pt; vertical-align:top; font-size:9.5pt; }
tr { page-break-inside:avoid; }
li { margin-bottom:6pt; }
.footer { color:#777; font-size:8.5pt; margin-top:18pt; border-top:1px solid #D7DBE2; padding-top:5pt; }
</style>
'@
function Wrap-Html($title,$subtitle,$status,$body) {
@"
<!DOCTYPE html><html><head><meta charset='utf-8'>$style</head><body>
<div class='kicker'>FOREGROUND MASKING RESEARCH</div><h1>$title</h1>
<div class='subtitle'>$subtitle</div><div class='meta'>Prepared: 20 August 2026</div>
<div class='meta'>Status: $status</div><div class='rule'></div>$body
<div class='footer'>Spike Gate Phase 2 | 20 August 2026</div></body></html>
"@
}
function Save-WordHtml($word,$name,$html) {
  Write-Host "Creating $name ..."
  $htmlPath=Join-Path $WorkDir ($name -replace '\.docx$','.html')
  $localDocx=Join-Path $WorkDir $name
  $pdf=Join-Path $WorkDir ($name -replace '\.docx$','.pdf')
  [IO.File]::WriteAllText($htmlPath,$html,[Text.UTF8Encoding]::new($false))
  $doc=$word.Documents.Open($htmlPath,$false,$false)
  foreach($section in $doc.Sections){
    $section.PageSetup.TopMargin=72; $section.PageSetup.BottomMargin=72
    $section.PageSetup.LeftMargin=72; $section.PageSetup.RightMargin=72
  }
  $doc.SaveAs2($localDocx,16)
  $doc.ExportAsFixedFormat($pdf,17)
  $doc.Close(0)
  Copy-Item -LiteralPath $localDocx -Destination (Join-Path $OutputDir $name) -Force
  Write-Host "Created $name"
}

$method=@'
<div class='callout'><b>Methodological principle.</b> Spike Gate supplies evidence from residual images; SEP and MTObjects segment only the original science images. Gate evidence selects credible connected components, but never becomes the science-image input.</div>
<h2>1. Purpose and rationale</h2><p>Earlier objective-only agreement could reward a large mask simply because it overlapped a Spike Gate target. Phase 2 changes the gate from a score-only term into an explicit connected-component selector. Recovery credit is therefore conditional on compact, gate-supported science-image segmentation.</p>
<h2>2. Processing architecture</h2><ol><li>Generate Spike Gate candidate evidence from the residual image.</li><li>Run SEP or MTObjects on the original science image within documentation-supported parameter ranges.</li><li>Label connected components in native science-image coordinates.</li><li>Project each native label map once into the common deprojected diagnostic view.</li><li>Retain only components satisfying target intersection, support fraction and size constraints.</li><li>Apply the accepted mask and replace masked profile samples with a log-linear bridge for profile diagnostics.</li></ol>
<h2>3. Component retention rules</h2><table><tr><th>Rule</th><th>Requirement</th><th>Purpose</th></tr><tr><td>Target intersection</td><td>Intersects the compact gate target</td><td>Direct candidate association</td></tr><tr><td>Support fraction</td><td>At least 20% of projected pixels inside permitted support</td><td>Rejects incidental overlap</td></tr><tr><td>Maximum extent</td><td>No more than 8% of diagnostic view</td><td>Rejects galaxy-scale components</td></tr><tr><td>Coordinates</td><td>Native labels projected once</td><td>Avoids repeated interpolation and denominator drift</td></tr></table>
<h2>4. Optimisation objective</h2><p>The scalar objective balances recovery with scientific protection. A zero or near-zero detection receives an explicit penalty only when credible gate candidates are present.</p><ul><li>Gate target recovery and candidate detection rate.</li><li>Supported-mask precision.</li><li>Excess area outside permitted support.</li><li>Protected galaxy loss and native-image masked fraction.</li><li>Non-gate profile masking and bridge-span penalties.</li><li>Explicit zero-detection penalty for credible candidates.</li></ul>
<h2>5. Audit and release gate</h2><p>Fifteen gate-positive, high-risk galaxies formed a stress-test audit. Each algorithm used a short 24-trial search. Full execution was conditional on acceptable component behaviour. MTO was permitted to proceed as a conservative diagnostic run; SEP was not.</p>
<h2>6. Implementation</h2><table><tr><th>Role</th><th>File</th></tr><tr><td>Objective and component logic</td><td>Foreground Masking/Shared/spike_gate_objective.py</td></tr><tr><td>Batch filter</td><td>Foreground Masking/Shared/spike_gate_component_filter.py</td></tr><tr><td>SEP optimiser</td><td>Foreground Masking/Optimisation/optimise_spike_gate_SEP.py</td></tr><tr><td>MTO optimiser</td><td>Foreground Masking/Optimisation/optimise_spike_gate_MTObjects.py</td></tr><tr><td>Audit evaluator</td><td>Foreground Masking/Optimisation/evaluate_constrained_spike_gate_batch.py</td></tr></table>
<h2>7. Interpretation limits</h2><p>Low masked area demonstrates conservatism, not necessarily correct foreground recovery. Phase 2 is a profile-protection diagnostic and must not yet be described as a complete foreground-object catalogue.</p>
'@
$results=@'
<div class='callout'><b>Executive conclusion.</b> Phase 2 removed the galaxy-scale overmasking failure mode. MTObjects is the stronger diagnostic candidate; SEP failed the stress-test audit and should not enter a production-style batch in its present configuration.</div>
<h2>1. Stress-test audit</h2><table><tr><th>Metric</th><th>SEP</th><th>MTObjects</th></tr><tr><td>Objective</td><td>153.6543; infeasible</td><td>57.8821; narrowly infeasible</td></tr><tr><td>Mean gate recovery</td><td>11.1%</td><td>49.3%</td></tr><tr><td>Candidate detection</td><td>11.7%</td><td>63.3%</td></tr><tr><td>Supported precision</td><td>Not competitive</td><td>58.1%</td></tr><tr><td>Zero detections</td><td>11/15</td><td>2/15</td></tr><tr><td>Mean masked area</td><td>0.00258%</td><td>0.00500%</td></tr><tr><td>Decision</td><td>Do not proceed</td><td>Proceed diagnostically</td></tr></table><p>The two MTO zero-detection cases were NGC4020 and NGC4532. The subsequent full run was explicitly diagnostic rather than production deployment.</p>
<h2>2. NGC3627 discrepancy resolved</h2><ul><li>SEP: zero retained components, zero recovery and zero masking.</li><li>MTO: three gate-supported components, recovery 1.0 and candidate detection 1.0.</li><li>MTO masked 0.0146% while preserving spiral structure and isophotal alignment.</li></ul>
<h2>3. 182-galaxy MTO diagnostic batch</h2><table><tr><th>Measure</th><th>Result</th></tr><tr><td>Completion</td><td>182/182 successful; zero failures</td></tr><tr><td>Gate-positive</td><td>127</td></tr><tr><td>Gate-negative</td><td>55; all left unmasked</td></tr><tr><td>Gate-positive with accepted mask</td><td>97/127 (76.4%)</td></tr><tr><td>Gate-positive with no accepted component</td><td>30/127 (23.6%)</td></tr><tr><td>Overall non-zero / zero masks</td><td>97 / 85</td></tr></table>
<h2>4. Masked-area distribution</h2><table><tr><th>Statistic</th><th>Masked area</th></tr><tr><td>Mean</td><td>0.002778%</td></tr><tr><td>Median</td><td>0.000685%</td></tr><tr><td>75th percentile</td><td>0.003443%</td></tr><tr><td>90th percentile</td><td>0.010300%</td></tr><tr><td>95th percentile</td><td>0.013278%</td></tr><tr><td>99th percentile</td><td>0.016678%</td></tr><tr><td>Maximum</td><td>0.021179% - NGC6412</td></tr></table>
<h2>5. High-mask review</h2><table><tr><th>Galaxy</th><th>Area</th><th>Review</th></tr><tr><td>NGC6412</td><td>0.02118%</td><td>Two compact off-centre masks; galaxy preserved</td></tr><tr><td>NGC1672</td><td>0.01946%</td><td>Four narrow profile-associated masks; stable isophotes</td></tr><tr><td>NGC3627</td><td>0.01458%</td><td>Major improvement over earlier aggressive SEP result</td></tr><tr><td>NGC5236</td><td>0.01428%</td><td>25 accepted from 11,537 raw segments; manual/performance flag</td></tr></table>
<h2>6. Scientific interpretation</h2><ul><li>Phase 2 sharply reduces damage to coherent galaxy morphology.</li><li>MTO is presently the stronger Spike Gate profile-protection candidate.</li><li>Thirty gate-positive galaxies received no accepted mask, so recall remains incomplete.</li><li>SEP remains excluded until it reliably yields compact gate-associated components.</li><li>The result is a conservative diagnostic, not a complete foreground catalogue.</li></ul><p><b>Output:</b> D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\MTO\Spike Gate\20260819_202509</p>
'@
$improve=@'
<div class='callout'><b>Recommended direction.</b> Retain MTObjects Phase 2 as the diagnostic baseline. Improve gate credibility and candidate matching first, then add local recovery only for credible unmatched candidates. Do not broaden the global mask to recover misses.</div>
<h2>1. Prioritised improvements</h2><table><tr><th>Priority</th><th>Option</th><th>Implementation intent</th></tr><tr><td>1</td><td>Gate credibility model</td><td>Score amplitude, side-drop, width, residual compactness, multi-width persistence and 2-D residual agreement.</td></tr><tr><td>2</td><td>Native-coordinate target/support</td><td>Use one traceable coordinate system and conserved denominators.</td></tr><tr><td>3</td><td>Candidate-specific association</td><td>Report matched, unmatched, split and merged candidates; optimise candidate-level recall and precision.</td></tr><tr><td>4</td><td>Morphology protection</td><td>Penalise annular coherence, azimuthal span, arm-like elongation and low-frequency galaxy overlap.</td></tr><tr><td>5</td><td>Two-stage local recovery</td><td>Search a small native window for credible misses under tighter area and morphology caps.</td></tr><tr><td>6</td><td>Manual labelled validation</td><td>Label 20-30 galaxies including NGC4020, NGC4532 and NGC5236.</td></tr><tr><td>7</td><td>Stratified cross-validation</td><td>Balance scale, inclination, morphology, gate count and foreground density.</td></tr><tr><td>8</td><td>Runtime controls</td><td>Cap raw components, set time/memory limits and checkpoint/resume.</td></tr></table>
<h2>2. Staged programme</h2><ol><li>Build gate-credibility labels and candidate-level matching diagnostics.</li><li>Implement morphology protection and native-coordinate accounting.</li><li>Run stratified four-fold optimisation on the labelled subset.</li><li>Add local recovery for credible unmatched gates and re-audit misses.</li><li>Approve a new 182-galaxy batch only if quantitative and visual criteria pass.</li></ol>
<h2>3. Acceptance criteria</h2><table><tr><th>Criterion</th><th>Threshold</th></tr><tr><td>Mean credible-candidate recovery</td><td>At least 0.70</td></tr><tr><td>Candidate detection</td><td>At least 0.75</td></tr><tr><td>High-credibility zero detections</td><td>None unexplained</td></tr><tr><td>Mean protected galaxy loss</td><td>No more than 0.01</td></tr><tr><td>Mean / maximum native masked fraction</td><td>No more than 0.02 / 0.05</td></tr><tr><td>Coherent structure removal</td><td>None confirmed in labelled audit</td></tr><tr><td>Cross-fold behaviour</td><td>Stable across four stratified folds</td></tr></table>
<h2>4. Decision rule</h2><p>Advance to production-style use only when candidate recovery improves without exceeding morphology-protection and area limits. If local recovery increases galaxy loss, retain the conservative baseline and route uncertain cases to manual review.</p>
'@

$word=$null
try {
  $word=New-Object -ComObject Word.Application
  $word.Visible=$false; $word.DisplayAlerts=0; $word.ScreenUpdating=$false
  Save-WordHtml $word 'Spike Gate Phase 2 Methodology.docx' (Wrap-Html 'Spike Gate Phase 2 Methodology' 'Component-constrained optimisation of SEP and MTObjects on science images' 'Methodology record' $method)
  Save-WordHtml $word 'Spike Gate Phase 2 Results.docx' (Wrap-Html 'Spike Gate Phase 2 Results' 'Audit comparison and 182-galaxy MTObjects diagnostic batch' 'Results and scientific interpretation' $results)
  Save-WordHtml $word 'Spike Gate Phase 2 Improvement Options.docx' (Wrap-Html 'Spike Gate Phase 2 Improvement Options' 'Prioritised route from conservative diagnostic to validated masking workflow' 'Recommendations and acceptance criteria' $improve)
  $word.Quit(); [Runtime.InteropServices.Marshal]::FinalReleaseComObject($word)|Out-Null; $word=$null
} finally { if($word){try{$word.Quit()}catch{}} }
