param(
  [string]$OutputDir='D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\documentation',
  [string]$WorkDir='C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\documentation\phase2_com_qa'
)
$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Force -Path $OutputDir,$WorkDir | Out-Null

function Add-Line($doc,$text,$kind='body') {
  $r=$doc.Range($doc.Content.End-1,$doc.Content.End-1)
  $r.InsertAfter($text+"`r")
  $p=$doc.Paragraphs.Item($doc.Paragraphs.Count-1)
  $p.Range.Font.Name='Calibri'; $p.Range.Font.Color=0x333333
  $p.Format.SpaceAfter=6; $p.Format.LineSpacingRule=5; $p.Format.LineSpacing=13.2
  switch($kind){
    'kicker' {$p.Range.Font.Size=10;$p.Range.Font.Bold=$true;$p.Range.Font.Color=0x006A9A;$p.Format.SpaceAfter=7}
    'title' {$p.Range.Font.Size=25;$p.Range.Font.Bold=$true;$p.Range.Font.Color=0x45250B;$p.Format.SpaceAfter=5}
    'subtitle' {$p.Range.Font.Size=13;$p.Range.Font.Color=0x555555;$p.Format.SpaceAfter=12}
    'meta' {$p.Range.Font.Size=10;$p.Format.SpaceAfter=2}
    'h1' {$p.Range.Font.Size=16;$p.Range.Font.Bold=$true;$p.Range.Font.Color=0xB5742E;$p.Format.SpaceBefore=16;$p.Format.SpaceAfter=8;$p.Format.KeepWithNext=$true}
    'h2' {$p.Range.Font.Size=13;$p.Range.Font.Bold=$true;$p.Range.Font.Color=0xB5742E;$p.Format.SpaceBefore=12;$p.Format.SpaceAfter=6;$p.Format.KeepWithNext=$true}
    'lead' {$p.Range.Font.Size=11;$p.Range.Font.Bold=$true;$p.Range.Font.Color=0x45250B;$p.Shading.BackgroundPatternColor=0xF5EEE8;$p.Format.LeftIndent=10;$p.Format.RightIndent=10;$p.Format.SpaceBefore=8;$p.Format.SpaceAfter=12}
    'bullet' {$p.Range.Font.Size=11;$p.Range.ListFormat.ApplyBulletDefault();$p.Format.LeftIndent=36;$p.Format.FirstLineIndent=-18;$p.Format.SpaceAfter=8}
    default {$p.Range.Font.Size=11}
  }
}
function Add-Title($doc,$title,$subtitle,$status){
  Add-Line $doc 'FOREGROUND MASKING RESEARCH' 'kicker'; Add-Line $doc $title 'title'; Add-Line $doc $subtitle 'subtitle'
  Add-Line $doc 'Prepared: 20 August 2026' 'meta'; Add-Line $doc ("Status: "+$status) 'meta'; Add-Line $doc '' 'body'
}
function Save-Report($word,$name,$title,$subtitle,$status,$content){
  Write-Host "Building $name ..."
  $doc=$word.Documents.Add()
  Write-Host "Document created for $name"
  $doc.Content.Text='Preparing report'
  $short = if($name -like '*Methodology*'){'phase2_method.docx'}elseif($name -like '*Improvement*'){'phase2_next.docx'}else{'phase2_results.docx'}
  $local=Join-Path $WorkDir $short; $pdf=Join-Path $WorkDir ($short -replace '\.docx$','.pdf')
  $doc.SaveAs2($local,16)
  Write-Host "Empty DOCX container saved for $name"
  $lines=@('FOREGROUND MASKING RESEARCH',$title,$subtitle,'Prepared: 20 August 2026',("Status: "+$status),'')
  foreach($item in $content){
    if($item.Kind -eq 'bullet'){$lines += ("    - "+$item.Text)} else {$lines += $item.Text}
    $lines += ''
  }
  $doc.Content.Text=($lines -join "`r")
  Write-Host "Content inserted for $name"
  $doc.Content.Font.Name='Calibri';$doc.Content.Font.Size=11;$doc.Content.Font.Color=0x333333
  $doc.Content.ParagraphFormat.SpaceAfter=6;$doc.Content.ParagraphFormat.LineSpacingRule=5;$doc.Content.ParagraphFormat.LineSpacing=13.2
  $doc.Paragraphs.Item(1).Range.Font.Size=10;$doc.Paragraphs.Item(1).Range.Font.Bold=$true;$doc.Paragraphs.Item(1).Range.Font.Color=0x006A9A
  $doc.Paragraphs.Item(2).Range.Font.Size=25;$doc.Paragraphs.Item(2).Range.Font.Bold=$true;$doc.Paragraphs.Item(2).Range.Font.Color=0x45250B
  $doc.Paragraphs.Item(3).Range.Font.Size=13;$doc.Paragraphs.Item(3).Range.Font.Color=0x555555
  foreach($s in $doc.Sections){$s.PageSetup.TopMargin=72;$s.PageSetup.BottomMargin=72;$s.PageSetup.LeftMargin=72;$s.PageSetup.RightMargin=72}
  $doc.Save(); $doc.ExportAsFixedFormat($pdf,17); $doc.Close(0)
  Write-Host "Saved and exported $name"
  Copy-Item -LiteralPath $local -Destination (Join-Path $OutputDir $name) -Force
  Write-Host "Created $name"
}
function I($text,$kind='body'){[pscustomobject]@{Text=$text;Kind=$kind}}

$method=@(
 I 'Methodological principle: Spike Gate supplies evidence from residual images; SEP and MTObjects segment only the original science images. Gate evidence selects credible connected components, but never becomes the science-image input.' 'lead',
 I '1. Purpose and rationale' 'h1', I 'Earlier objective-only agreement could reward a large mask simply because it overlapped a Spike Gate target. Phase 2 changes the gate from a score-only term into an explicit connected-component selector. Recovery credit is therefore conditional on compact, gate-supported science-image segmentation.',
 I '2. Processing architecture' 'h1', I 'Generate Spike Gate candidate evidence from the residual image.' 'bullet', I 'Run SEP or MTObjects on the original science image within documentation-supported parameter ranges.' 'bullet', I 'Label connected components in native science-image coordinates.' 'bullet', I 'Project each native label map once into the common deprojected diagnostic view.' 'bullet', I 'Retain only components satisfying target intersection, support fraction and size constraints.' 'bullet', I 'Apply the accepted mask and replace masked profile samples with a log-linear bridge for profile diagnostics.' 'bullet',
 I '3. Component retention rules' 'h1', I 'Target intersection' 'h2', I 'The component must intersect the compact gate target, establishing direct candidate association.', I 'Support fraction' 'h2', I 'At least 20% of projected component pixels must fall inside the permitted support region.', I 'Maximum extent' 'h2', I 'A component may occupy no more than 8% of the diagnostic view, rejecting galaxy-scale structures.', I 'Coordinate handling' 'h2', I 'Native labels are projected once to avoid repeated interpolation and denominator drift.',
 I '4. Optimisation objective' 'h1', I 'The scalar objective balances recovery with scientific protection. A zero or near-zero detection receives an explicit penalty only when credible gate candidates are present.', I 'Gate target recovery and candidate detection rate.' 'bullet', I 'Supported-mask precision.' 'bullet', I 'Excess area outside permitted support.' 'bullet', I 'Protected galaxy loss and native-image masked fraction.' 'bullet', I 'Non-gate profile masking and bridge-span penalties.' 'bullet', I 'Explicit zero-detection penalty for credible candidates.' 'bullet',
 I '5. Audit and release gate' 'h1', I 'Fifteen gate-positive, high-risk galaxies formed a stress-test audit. Each algorithm used a short 24-trial search. Full execution was conditional on acceptable component behaviour. MTO was permitted to proceed as a conservative diagnostic run; SEP was not.',
 I '6. Implementation' 'h1', I 'Objective and native component logic: Foreground Masking/Shared/spike_gate_objective.py' 'bullet', I 'Batch component filtering: Foreground Masking/Shared/spike_gate_component_filter.py' 'bullet', I 'SEP optimiser: Foreground Masking/Optimisation/optimise_spike_gate_SEP.py' 'bullet', I 'MTO optimiser: Foreground Masking/Optimisation/optimise_spike_gate_MTObjects.py' 'bullet', I 'Audit evaluator: Foreground Masking/Optimisation/evaluate_constrained_spike_gate_batch.py' 'bullet',
 I '7. Interpretation limits' 'h1', I 'Low masked area demonstrates conservatism, not necessarily correct foreground recovery. Phase 2 is a profile-protection diagnostic and must not yet be described as a complete foreground-object catalogue.'
)
$results=@(
 I 'Executive conclusion: Phase 2 removed the galaxy-scale overmasking failure mode. MTObjects is the stronger diagnostic candidate; SEP failed the stress-test audit and should not enter a production-style batch in its present configuration.' 'lead',
 I '1. Stress-test audit' 'h1', I 'SEP' 'h2', I 'Objective 153.6543 (infeasible); mean gate recovery 11.1%; candidate detection 11.7%; zero detections 11/15; mean masked area 0.00258%. Decision: do not proceed.', I 'MTObjects' 'h2', I 'Objective 57.8821 (narrowly infeasible); mean gate recovery 49.3%; candidate detection 63.3%; supported precision 58.1%; zero detections 2/15; mean masked area 0.00500%. Decision: proceed diagnostically.', I 'The two MTO zero-detection cases were NGC4020 and NGC4532. The full run remained explicitly diagnostic rather than production deployment.',
 I '2. NGC3627 discrepancy resolved' 'h1', I 'SEP produced zero retained components, zero recovery and zero masking.' 'bullet', I 'MTO produced three gate-supported components, recovery 1.0 and candidate detection 1.0.' 'bullet', I 'MTO masked 0.0146% while preserving spiral structure and isophotal alignment.' 'bullet',
 I '3. 182-galaxy MTO diagnostic batch' 'h1', I '182/182 successful; zero failures.' 'bullet', I '127 gate-positive galaxies; 55 gate-negative galaxies, all left unmasked.' 'bullet', I '97/127 gate-positive galaxies had a non-zero accepted mask (76.4%).' 'bullet', I '30/127 gate-positive galaxies had no accepted component (23.6%).' 'bullet', I 'Overall: 97 non-zero masks and 85 zero masks.' 'bullet',
 I '4. Masked-area distribution' 'h1', I 'Mean 0.002778%; median 0.000685%; 75th percentile 0.003443%; 90th 0.010300%; 95th 0.013278%; 99th 0.016678%; maximum 0.021179% (NGC6412).',
 I '5. High-mask visual review' 'h1', I 'NGC6412 (0.02118%): two compact off-centre masks; galaxy structure preserved.' 'bullet', I 'NGC1672 (0.01946%): four narrow profile-associated masks; isophotes stable.' 'bullet', I 'NGC3627 (0.01458%): major improvement over the earlier aggressive SEP result.' 'bullet', I 'NGC5236 (0.01428%): 25 accepted from 11,537 raw segments; manual and performance flag.' 'bullet',
 I '6. Scientific interpretation' 'h1', I 'Phase 2 sharply reduces damage to coherent galaxy morphology.' 'bullet', I 'MTO is presently the stronger Spike Gate profile-protection candidate.' 'bullet', I 'Thirty gate-positive galaxies received no accepted mask, so recall remains incomplete.' 'bullet', I 'SEP remains excluded until it reliably yields compact gate-associated components.' 'bullet', I 'The result is a conservative diagnostic, not a complete foreground catalogue.' 'bullet', I 'Batch output: D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\MTO\Spike Gate\20260819_202509'
)
$improve=@(
 I 'Recommended direction: Retain MTObjects Phase 2 as the diagnostic baseline. Improve gate credibility and candidate matching first, then add local recovery only for credible unmatched candidates. Do not broaden the global mask to recover misses.' 'lead',
 I '1. Prioritised improvements' 'h1', I '1. Gate credibility model' 'h2', I 'Score amplitude, side-drop, width, residual compactness, multi-width persistence and 2-D residual agreement.', I '2. Native-coordinate target and support' 'h2', I 'Use one traceable coordinate system and conserved denominators for recovery, precision and protected loss.', I '3. Candidate-specific association' 'h2', I 'Report matched, unmatched, split and merged candidates; optimise candidate-level recall and precision.', I '4. Morphology protection' 'h2', I 'Penalise annular coherence, azimuthal span, arm-like elongation and low-frequency galaxy overlap.', I '5. Two-stage local recovery' 'h2', I 'Search a small native window for credible misses under tighter area and morphology caps.', I '6. Manual labelled validation' 'h2', I 'Label approximately 20-30 galaxies including NGC4020, NGC4532 and NGC5236.', I '7. Stratified cross-validation' 'h2', I 'Balance image scale, inclination, morphology, gate count and foreground density.', I '8. Runtime controls' 'h2', I 'Cap raw components, enforce time and memory limits and checkpoint/resume.',
 I '2. Staged programme' 'h1', I 'Build gate-credibility labels and candidate-level matching diagnostics.' 'bullet', I 'Implement morphology protection and native-coordinate accounting.' 'bullet', I 'Run stratified four-fold optimisation on the labelled subset.' 'bullet', I 'Add local recovery for credible unmatched gates and re-audit misses.' 'bullet', I 'Approve a new 182-galaxy batch only if quantitative and visual criteria pass.' 'bullet',
 I '3. Acceptance criteria' 'h1', I 'Mean credible-candidate recovery at least 0.70.' 'bullet', I 'Candidate detection at least 0.75.' 'bullet', I 'No unexplained zero detections for high-credibility candidates.' 'bullet', I 'Mean protected galaxy loss no more than 0.01.' 'bullet', I 'Mean and maximum native masked fractions no more than 0.02 and 0.05.' 'bullet', I 'No confirmed coherent structure removal in the labelled audit.' 'bullet', I 'Stable behaviour across four stratified folds.' 'bullet',
 I '4. Decision rule' 'h1', I 'Advance to production-style use only when candidate recovery improves without exceeding morphology-protection and area limits. If local recovery increases galaxy loss, retain the conservative baseline and route uncertain cases to manual review.'
)

$word=$null
try{
 $word=New-Object -ComObject Word.Application;$word.Visible=$true;$word.DisplayAlerts=-1;$word.ScreenUpdating=$true
 Save-Report $word 'Spike Gate Phase 2 Methodology.docx' 'Spike Gate Phase 2 Methodology' 'Component-constrained optimisation of SEP and MTObjects on science images' 'Methodology record' $method
 Save-Report $word 'Spike Gate Phase 2 Results.docx' 'Spike Gate Phase 2 Results' 'Audit comparison and 182-galaxy MTObjects diagnostic batch' 'Results and scientific interpretation' $results
 Save-Report $word 'Spike Gate Phase 2 Improvement Options.docx' 'Spike Gate Phase 2 Improvement Options' 'Prioritised route from conservative diagnostic to validated masking workflow' 'Recommendations and acceptance criteria' $improve
 $word.Quit();[Runtime.InteropServices.Marshal]::FinalReleaseComObject($word)|Out-Null;$word=$null
}finally{if($word){try{$word.Quit()}catch{}}}
