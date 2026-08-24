param(
  [string]$WorkDir='C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\documentation\toy_comparison_doc_qa',
  [string]$ComparisonPng='D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\Toy Objects comparison\20260821_104129\NGC3627_MTO_left_SEP_right_clean.png'
)
$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Force -Path $WorkDir | Out-Null

function Ole([string]$hex) {
  $hex=$hex.TrimStart('#'); $r=[Convert]::ToInt32($hex.Substring(0,2),16); $g=[Convert]::ToInt32($hex.Substring(2,2),16); $b=[Convert]::ToInt32($hex.Substring(4,2),16)
  return $r + 256*$g + 65536*$b
}
$navy=Ole '#0B2545'; $blue=Ole '#2E74B5'; $darkBlue=Ole '#1F4D78'; $gray=Ole '#555555'; $light=Ole '#F2F4F7'; $callout=Ole '#E8EEF5'; $white=Ole '#FFFFFF'

function Configure-Document($doc,[string]$runningTitle) {
  foreach($section in $doc.Sections){
    $section.PageSetup.PageWidth=612; $section.PageSetup.PageHeight=792
    $section.PageSetup.TopMargin=72; $section.PageSetup.BottomMargin=72; $section.PageSetup.LeftMargin=72; $section.PageSetup.RightMargin=72
    $section.PageSetup.HeaderDistance=35.4; $section.PageSetup.FooterDistance=35.4
    $header=$section.Headers.Item(1).Range; $header.Text=$runningTitle; $header.Font.Name='Calibri'; $header.Font.Size=9; $header.Font.Color=$gray
    $footer=$section.Footers.Item(1).Range; $footer.Text='Foreground Masking Research  |  '; $footer.Font.Name='Calibri'; $footer.Font.Size=9; $footer.Font.Color=$gray
    $footer.Collapse(0); [void]$footer.Fields.Add($footer,-1,'PAGE',$true)
  }
  $normal=$doc.Styles.Item('Normal'); $normal.Font.Name='Calibri'; $normal.Font.Size=11; $normal.Font.Color=$gray
  $normal.ParagraphFormat.SpaceBefore=0; $normal.ParagraphFormat.SpaceAfter=6; $normal.ParagraphFormat.LineSpacingRule=5; $normal.ParagraphFormat.LineSpacing=13.2
  $h1=$doc.Styles.Item('Heading 1'); $h1.Font.Name='Calibri'; $h1.Font.Size=16; $h1.Font.Bold=$true; $h1.Font.Color=$blue
  $h1.ParagraphFormat.SpaceBefore=16; $h1.ParagraphFormat.SpaceAfter=8; $h1.ParagraphFormat.KeepWithNext=$true
  $h2=$doc.Styles.Item('Heading 2'); $h2.Font.Name='Calibri'; $h2.Font.Size=13; $h2.Font.Bold=$true; $h2.Font.Color=$blue
  $h2.ParagraphFormat.SpaceBefore=12; $h2.ParagraphFormat.SpaceAfter=6; $h2.ParagraphFormat.KeepWithNext=$true
  $h3=$doc.Styles.Item('Heading 3'); $h3.Font.Name='Calibri'; $h3.Font.Size=12; $h3.Font.Bold=$true; $h3.Font.Color=$darkBlue
  $h3.ParagraphFormat.SpaceBefore=8; $h3.ParagraphFormat.SpaceAfter=4; $h3.ParagraphFormat.KeepWithNext=$true
}
function Add-Text($sel,[string]$text,[string]$style='Normal') {
  $sel.Style=$style; $sel.Font.Bold=0; $sel.Font.Italic=0; $sel.TypeText($text); $sel.TypeParagraph()
}
function Add-TitleBlock($sel,[string]$title,[string]$subtitle,[string]$status) {
  $sel.Style='Normal'; $sel.Font.Name='Calibri'; $sel.Font.Size=10; $sel.Font.Bold=1; $sel.Font.Color=$blue; $sel.TypeText('FOREGROUND MASKING RESEARCH'); $sel.TypeParagraph()
  $sel.Font.Size=25; $sel.Font.Bold=1; $sel.Font.Color=$navy; $sel.TypeText($title); $sel.TypeParagraph()
  $sel.Font.Size=13; $sel.Font.Bold=0; $sel.Font.Color=$gray; $sel.TypeText($subtitle); $sel.TypeParagraph()
  $sel.Font.Size=10; $sel.TypeText('Prepared: 24 August 2026'); $sel.TypeParagraph(); $sel.TypeText('Status: '+$status); $sel.TypeParagraph(); $sel.TypeParagraph()
}
function Add-Callout($sel,[string]$label,[string]$text) {
  $sel.Style='Normal'; $p=$sel.Paragraphs.Item(1); $p.Shading.BackgroundPatternColor=$callout; $p.Format.LeftIndent=10; $p.Format.RightIndent=10; $p.Format.SpaceBefore=6; $p.Format.SpaceAfter=10
  $sel.Font.Color=$navy; $sel.Font.Bold=1; $sel.TypeText($label+': '); $sel.Font.Bold=0; $sel.TypeText($text); $sel.TypeParagraph()
  $sel.ParagraphFormat.LeftIndent=0; $sel.ParagraphFormat.RightIndent=0; $sel.Shading.BackgroundPatternColor=$white
}
function Add-Bullets($sel,[string[]]$items) {
  foreach($item in $items){ $sel.Style='Normal'; $sel.Range.ListFormat.ApplyBulletDefault(); $sel.TypeText($item); $sel.TypeParagraph() }
  $sel.Range.ListFormat.RemoveNumbers(); $sel.ParagraphFormat.LeftIndent=0; $sel.ParagraphFormat.FirstLineIndent=0
}
function Add-Numbered($sel,[string[]]$items) {
  foreach($item in $items){ $sel.Style='Normal'; $sel.Range.ListFormat.ApplyNumberDefault(); $sel.TypeText($item); $sel.TypeParagraph() }
  $sel.Range.ListFormat.RemoveNumbers(); $sel.ParagraphFormat.LeftIndent=0; $sel.ParagraphFormat.FirstLineIndent=0
}
function Add-Table($doc,$sel,[object[]]$rows,[double[]]$widths) {
  $table=$doc.Tables.Add($sel.Range,$rows.Count,$widths.Count); $table.AllowAutoFit=$false; $table.Borders.Enable=1
  for($c=1;$c -le $widths.Count;$c++){ $table.Columns.Item($c).Width=$widths[$c-1] }
  for($r=1;$r -le $rows.Count;$r++){
    for($c=1;$c -le $widths.Count;$c++){
      $cell=$table.Cell($r,$c); $cell.Range.Text=[string]$rows[$r-1][$c-1]; $cell.Range.Font.Name='Calibri'; $cell.Range.Font.Size=9.5; $cell.VerticalAlignment=1
      $cell.TopPadding=4; $cell.BottomPadding=4; $cell.LeftPadding=6; $cell.RightPadding=6
      if($r -eq 1){$cell.Range.Font.Bold=1;$cell.Range.Font.Color=$navy;$cell.Shading.BackgroundPatternColor=$light}
    }
  }
  $table.Rows.Item(1).HeadingFormat=-1
  $sel.SetRange($table.Range.End,$table.Range.End); $sel.TypeParagraph(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($table)
}
function Add-Figure($sel,[string]$path,[double]$width,[string]$caption) {
  $shape=$sel.InlineShapes.AddPicture($path,$false,$true); $shape.LockAspectRatio=-1; $shape.Width=$width; $sel.TypeParagraph()
  $sel.Style='Normal'; $sel.Font.Name='Calibri'; $sel.Font.Size=9; $sel.Font.Italic=1; $sel.Font.Color=$gray; $sel.ParagraphFormat.Alignment=1; $sel.TypeText($caption); $sel.TypeParagraph(); $sel.ParagraphFormat.Alignment=0; $sel.Font.Italic=0
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($shape)
}
function Add-PageBreak($sel){$sel.InsertBreak(7)}
function Save-Doc($doc,[string]$base){
  $docx=Join-Path $WorkDir ($base+'.docx'); $pdf=Join-Path $WorkDir ($base+'.pdf'); $doc.SaveAs2($docx,16); $doc.ExportAsFixedFormat($pdf,17); return @($docx,$pdf)
}

$methodParameterRows=@(
  @('Parameter','SEP search range','MTObjects search range'),
  @('Detection threshold / move factor','detect_thresh 0.6-2.0','move_factor 0.0-1.0'),
  @('Minimum area','5-35 pixels','1-40 pixels'),
  @('Deblending','16/32/64; contrast 0.001-0.03','Not applicable'),
  @('Background','mesh 32/64/128/256; filter 1/3/5/7/9','bg_variance calibrated log-wise'),
  @('Dilation radius','1-6 pixels','1-6 pixels'),
  @('Maximum component area','20-8000 pixels','20-3000 pixels'),
  @('Maximum elongation','1.5-30.0','2.0-15.0')
)
$selectedRows=@(
  @('Setting','SEP selected','MTObjects selected'),
  @('Winning fold','4','3'),
  @('Core sensitivity','detect_thresh 1.9811','move_factor 0.8052'),
  @('Minimum area','12','5'),
  @('Deblending','32; contrast 0.001043','-'),
  @('Background','mesh 32; filter 1','variance 0.0008210'),
  @('Gaussian FWHM','-','0.42985'),
  @('Minimum distance','-','0.21516'),
  @('Dilation radius','4','3'),
  @('Maximum area','4885','2987'),
  @('Maximum elongation','11.8404','12.3811'),
  @('Central exclusion','8 pixels','8 pixels')
)

$word=$null
try{
  $word=New-Object -ComObject Word.Application; $word.Visible=$false; $word.DisplayAlerts=0
  Write-Output 'STAGE=word_started'

  $doc=$word.Documents.Add(); Configure-Document $doc 'Toy Objects Methodology'; $sel=$word.Selection
  Write-Output 'STAGE=methodology_started'
  Add-TitleBlock $sel 'Toy Objects Foreground-Masking Methodology' 'Four-fold optimisation and matched 182-galaxy evaluation of SEP and MTObjects' 'Definitive methodology record'
  Add-Callout $sel 'Scope' 'This document describes only the Toy Objects identification experiment. SEP and MTObjects operate on original science images. Spike Gate residual-image identification is a separate study and is not used here.'
  Add-Text $sel '1. Research question' 'Heading 1'
  Add-Text $sel 'The experiment asks how effectively SEP and MTObjects can identify and mask known synthetic foreground-like sources while limiting unnecessary masking of the underlying science image. Synthetic truth provides an objective recovery target that is unavailable for real, unlabelled foreground objects.'
  Add-Text $sel '2. Evidence hierarchy' 'Heading 1'
  Add-Bullets $sel @(
    'Optimisation evidence: four folds of the same 40 low-foreground calibration galaxies; each fold trains on 30 and validates on the held-out 10.',
    'Selection evidence: each fold winner is evaluated on its method-specific common 40-galaxy injection set, and the best candidate is selected.',
    'Direct method comparison: both selected algorithms are applied to all 182 galaxies using identical standard toy placements and truth masks. This matched evaluation is the primary basis for SEP-versus-MTObjects conclusions.'
  )
  Add-Text $sel 'Important comparability note' 'Heading 2'
  Add-Text $sel 'The SEP and MTObjects optimisation runs used the same galaxies and fold membership but different optimisation evaluation seeds (SEP 202608199; MTObjects 202608299). Their cross-validation scores therefore describe method-specific tuning and are not a strictly paired head-to-head test. The final 182-galaxy comparison corrects this by reconstructing the same six toys per galaxy with seed 202608299 for both algorithms.'
  Add-Text $sel '3. Galaxy sample and cross-validation' 'Heading 1'
  Add-Table $doc $sel @(
    @('Design element','Implementation'),
    @('Calibration sample','40 galaxies listed in CleanGalaxies.txt, selected for low foreground contamination.'),
    @('Fold design','Four fixed groups of 10 galaxies. For each fold: 30 training galaxies and 10 held-out validation galaxies.'),
    @('Optimisation trials','40 trials per fold: 8 startup evaluations followed by 32 Optuna TPE trials.'),
    @('Parallelism','10 image workers.'),
    @('Image input','Original science image for both SEP and MTObjects.'),
    @('Maximum permitted mask','15% during optimisation.'),
    @('Final evaluation','182 galaxies, six standard toys per image, matched seed 202608299.')
  ) @(125,343)
  Add-Text $sel '4. Synthetic-object construction' 'Heading 1'
  Add-Text $sel 'Six non-overlapping toys are placed wholly within the investigated galaxy region and away from image boundaries. The injection model uses the robust image noise scale so toy brightness is comparable across galaxies.'
  Add-Table $doc $sel @(
    @('Property','Specification'),
    @('Object mixture','Star 50%; compact cluster 20%; elliptical galaxy 30%.'),
    @('Peak amplitude','Uniformly sampled from 5 to 25 times the robust background sigma.'),
    @('FWHM','Stars/clusters: 2-10 pixels; galaxies: 5-22 pixels.'),
    @('Galaxy axis ratio','Uniformly sampled from 0.35 to 0.95.'),
    @('Position angle','Uniformly sampled from 0 to 180 degrees.'),
    @('Truth definition','Pixels at or above 8% of the model peak, then circularly dilated by one pixel.'),
    @('Placement controls','Inside the investigated region, image-edge margin applied, and no overlap with earlier toys.')
  ) @(125,343)
  Add-Text $sel '5. Masking pipelines' 'Heading 1'
  Add-Text $sel 'SEP' 'Heading 2'; Add-Text $sel 'SEP estimates the background, detects thresholded connected sources, deblends detections, filters components by area and elongation, excludes the protected centre, and dilates accepted segments. Detection is always performed on the science image.'
  Add-Text $sel 'MTObjects' 'Heading 2'; Add-Text $sel 'MTObjects uses a max-tree representation controlled by move factor, minimum distance, Gaussian smoothing and calibrated background variance. Accepted components are filtered by minimum/maximum area and elongation, protected-centre exclusion and dilation. Detection is always performed on the science image.'
  Add-Text $sel 'Documentation-constrained search spaces' 'Heading 2'; Add-Table $doc $sel $methodParameterRows @(155,156,157)
  Add-Text $sel '6. Objective functions' 'Heading 1'
  Add-Text $sel 'Optimisation uses the incremental mask: the mask produced after toy injection minus the baseline mask from the uninjected science image. This isolates masking attributable to the toys during tuning.'
  Add-Text $sel 'Common metrics' 'Heading 2'
  Add-Bullets $sel @(
    'Pixel recall: toy-truth pixels recovered by the incremental mask divided by all toy-truth pixels.',
    'Pixel precision: toy-truth overlap divided by all incremental masked pixels.',
    'F1 score: harmonic mean of pixel recall and precision.',
    'Mean per-toy recall: average recovered fraction across individual toys.',
    'Toy detection rate: fraction of toys for which at least 50% of truth pixels are masked.',
    'Data-loss terms: mean masked fraction, false-positive fraction and a hard 15% maximum-mask cap.'
  )
  Add-Text $sel 'SEP scalar score' 'Heading 2'
  Add-Text $sel 'Recovery = 0.45 x mean pixel recall + 0.20 x mean F1 + 0.25 x mean per-toy recall + 0.20 x toy detection rate. Data loss = 0.35 x mean masked fraction + 0.05 x false-positive fraction. The maximised score is recovery minus data loss; exceeding the 15% cap invokes a large infeasibility penalty.'
  Add-Text $sel 'MTObjects recovery-constrained score' 'Heading 2'
  Add-Text $sel 'Recovery = 0.45 x mean F1 + 0.35 x mean per-toy recall + 0.20 x toy detection rate. Data loss = 0.50 x mean masked fraction + 0.10 x false-positive fraction. A trial is infeasible if it masks no incremental pixels, toy detection is below 0.25, or mean per-toy recall is below 0.20. The 15% maximum-mask cap is then applied.'
  Add-Text $sel '7. Selected configurations' 'Heading 1'; Add-Table $doc $sel $selectedRows @(155,156,157)
  Add-Text $sel '8. Final 182-galaxy evaluation' 'Heading 1'
  Add-Text $sel 'The selected configurations were applied to the complete 182-galaxy sample. The matched comparison reconstructs identical toys and evaluates the final mask, not the incremental optimisation mask. This reflects what a user receives from the production-style batch.'
  Add-Bullets $sel @(
    'Six matched standard toys per galaxy; seed 202608299; truth dilation one pixel.',
    'Per-galaxy outputs include total masked fraction, toy-pixel recall, per-toy detection, toy-associated precision, F1, non-toy masking, segments and runtime.',
    'Diagnostic PNGs contain original image, original plus toys, mask, recovered image, original/processed isophotes and original/processed bar-major profiles.',
    'Processed profile gaps are filled using the established log-linear bridge.',
    'The 40 calibration galaxies retain the filename suffix _clean.'
  )
  Add-Text $sel '9. Reproducibility and interpretation limits' 'Heading 1'
  Add-Bullets $sel @(
    'Toy Objects provide known synthetic truth but do not reproduce every real foreground morphology or brightness distribution.',
    'High toy recall does not by itself prove preservation of galaxy morphology; mask extent and visual diagnostics remain necessary.',
    'Toy-associated precision is expected to be low when algorithms also mask genuine foreground sources already present in the science image.',
    'Cross-validation metrics and final 182-galaxy metrics use different denominators (incremental versus final mask) and must not be compared as if identical.',
    'The later 20-80 sigma bright-toy MTObjects sensitivity experiment is excluded from the matched standard-toy comparison.'
  )
  Add-Text $sel '10. Authoritative sources' 'Heading 1'
  Add-Text $sel 'SEP optimisation: D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\sep toy cross validation\20260817_161404'
  Add-Text $sel 'MTObjects optimisation: D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\mtobjects toy recovery followup\20260816_063455'
  Add-Text $sel 'Matched statistics: D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\documentation\Toy Objects SEP vs MTObjects Statistical Comparison.xlsx'
  Write-Output 'STAGE=methodology_content_complete'
  $methodPaths=Save-Doc $doc 'Toy Objects SEP and MTObjects Methodology'; Write-Output 'STAGE=methodology_saved'; $doc.Close(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc)

  $doc=$word.Documents.Add(); Configure-Document $doc 'Toy Objects Results'; $sel=$word.Selection
  Write-Output 'STAGE=results_started'
  Add-TitleBlock $sel 'Toy Objects Results: SEP versus MTObjects' 'Matched 182-galaxy comparison using standard injected toys' 'Results, interpretation and recommendation'
  Add-Callout $sel 'Executive conclusion' 'SEP recovered a larger fraction of toy pixels and achieved the higher F1 score at essentially the same mean masked area. MTObjects achieved a nearly identical whole-toy detection rate and a substantially lower extreme masked-area tail. SEP is therefore preferred when recovery is the priority, but only with an explicit per-image area guardrail and morphology review; MTObjects remains the more conservative fallback for high-risk galaxies.'
  Add-Text $sel '1. Comparison basis' 'Heading 1'
  Add-Text $sel 'All direct conclusions in this report use the matched 182-galaxy standard-toy comparison. Each algorithm received the same science image, six toys, placement seed 202608299 and truth mask. Both batches completed successfully for all 182 galaxies.'
  Add-Text $sel '2. Population results' 'Heading 1'
  Add-Table $doc $sel @(
    @('Metric','SEP','MTObjects','SEP - MTO'),
    @('Mean masked image area','8.82%','8.89%','-0.07 pp'),
    @('Median masked image area','8.36%','8.77%','-0.41 pp'),
    @('Mean toy-pixel recall','70.57%','62.42%','+8.15 pp'),
    @('Median toy-pixel recall','82.88%','63.82%','+19.06 pp'),
    @('Mean toy detection rate','68.68%','68.96%','-0.27 pp'),
    @('Mean per-toy recall','68.86%','67.78%','+1.08 pp'),
    @('Mean toy-associated precision','0.700%','0.560%','+0.140 pp'),
    @('Mean toy F1','1.381%','1.107%','+0.274 pp'),
    @('Mean non-toy mask fraction','8.77%','8.85%','-0.07 pp')
  ) @(195,91,91,91)
  Add-Figure $sel (Join-Path $WorkDir 'toy_comparison_headline_metrics.png') 468 'Figure 1. Mean recovery, mask extent and overlap-quality metrics across 182 matched galaxies.'
  Add-Text $sel '3. Paired galaxy-level outcomes' 'Heading 1'
  Add-Table $doc $sel @(
    @('Paired outcome','Galaxies','Interpretation'),
    @('SEP higher toy-pixel recall','121 / 182','SEP advantage in two-thirds of the sample.'),
    @('MTObjects higher toy-pixel recall','57 / 182','Four exact ties.'),
    @('SEP masks less total area','121 / 182','SEP is not systematically more aggressive in the typical case.'),
    @('MTObjects masks less total area','61 / 182','No ties.'),
    @('SEP higher toy F1','134 / 182','SEP more often delivers the better recovery/precision balance.'),
    @('MTObjects higher toy F1','47 / 182','One exact tie.')
  ) @(210,80,178)
  Add-Figure $sel (Join-Path $WorkDir 'toy_comparison_paired_scatter.png') 468 'Figure 2. Each point is one galaxy; the dashed diagonal marks equal performance.'
  Add-Text $sel '4. Distribution and outlier behaviour' 'Heading 1'
  Add-Table $doc $sel @(
    @('Masked-area statistic','SEP','MTObjects'),
    @('10th percentile','4.91%','6.01%'),
    @('25th percentile','6.30%','6.90%'),
    @('Median','8.36%','8.77%'),
    @('75th percentile','10.35%','10.27%'),
    @('90th percentile','13.23%','11.94%'),
    @('95th percentile','15.14%','12.68%'),
    @('Maximum','33.26%','19.02%')
  ) @(220,124,124)
  Add-Text $sel 'The average masked areas are almost identical, but SEP has a heavier upper tail. The final full-sample evaluation includes galaxies unlike the 40 calibration cases, so the optimisation-era 15% cap does not guarantee that every production image remains below 15%. SEP outputs above the threshold require automatic flagging and manual review.'
  Add-Text $sel '5. Calibration and generalisation' 'Heading 1'
  Add-Table $doc $sel @(
    @('Selected-candidate metric','SEP (fold 4)','MTObjects (fold 3)'),
    @('Held-out mean toy recall','40.14%','52.55%'),
    @('Held-out toy detection rate','40.00%','55.00%'),
    @('Held-out mean masked fraction','6.20%','8.82%'),
    @('All-40 mean toy recall','45.38%','50.70%'),
    @('All-40 toy detection rate','45.42%','53.33%'),
    @('All-40 mean masked fraction','5.71%','9.07%')
  ) @(220,124,124)
  Add-Text $sel 'These optimisation figures are reported for reproducibility, not as a paired algorithm comparison: the two tuning runs used different injection seeds and incremental-mask scoring. The matched 182-galaxy result is the appropriate head-to-head evidence.'
  Add-PageBreak $sel
  Add-Text $sel '6. Visual comparison: NGC3627' 'Heading 1'
  Add-Figure $sel $ComparisonPng 468 'Figure 3. NGC3627 matched Toy Objects diagnostic: MTObjects on the left, SEP on the right. The dashed black divider separates the methods.'
  Add-Text $sel 'The paired layout makes the practical trade-off visible: compare the same toy boundaries, total mask extent, recovery outlines, isophote preservation and profile bridges before accepting a method for a specific galaxy.'
  Add-Text $sel '7. Interpretation' 'Heading 1'
  Add-Bullets $sel @(
    'SEP has the stronger average toy-pixel recovery: +8.15 percentage points, with a much larger median advantage.',
    'Whole-toy detection is effectively tied. SEP tends to recover more of each toy rather than simply detecting more toys.',
    'Mean total masking is effectively tied, and SEP masks less area in 121 galaxies; however, SEP has the more severe high-mask outliers.',
    'Both toy-associated precision values are below 1%. This does not mean nearly all masking is necessarily wrong: the denominator includes masks of real objects already present, while truth labels cover only injected toys. It does show that toy overlap alone is an incomplete measure of scientific selectivity.',
    'Toy Objects test synthetic recovery. They do not establish accuracy for real foreground objects without a labelled real-object validation set.'
  )
  Add-Text $sel '8. Recommendation' 'Heading 1'
  Add-Text $sel 'Primary recommendation' 'Heading 2'
  Add-Text $sel 'Use SEP as the preferred Toy Objects masking configuration when the main requirement is maximal recovery of foreground-like sources, because it produces higher recall and F1 without increasing mean masked area.'
  Add-Text $sel 'Required SEP safeguards' 'Heading 2'
  Add-Bullets $sel @(
    'Flag any image with masked area above 15%, and treat values above 20% as automatic manual-review cases.',
    'Reject or review large coherent components that resemble arms, rings, bars or extended galaxy structure.',
    'Retain the eight-panel diagnostic and inspect processed isophotes and bar-major profiles.',
    'Record both total masked area and toy/target recovery; neither is sufficient alone.'
  )
  Add-Text $sel 'When to prefer MTObjects' 'Heading 2'
  Add-Text $sel 'Use MTObjects as the conservative alternative for galaxies where SEP enters the high-mask tail, where coherent morphology appears threatened, or where a lower maximum mask extent is more important than peak pixel recall.'
  Add-Text $sel '9. Next improvements' 'Heading 1'
  Add-Numbered $sel @(
    'Repeat cross-validation with exactly the same toy placements and seeds for both algorithms, enabling genuinely paired fold-level selection.',
    'Add morphology-protection terms for azimuthal span, annular coherence and overlap with low-frequency galaxy structure.',
    'Optimise a constrained Pareto objective over toy recovery, masked area and profile/isophote preservation rather than relying on one scalar score.',
    'Create a manually labelled real-foreground validation subset and report real-object recall, false-mask area and profile relevance.',
    'Evaluate a guarded hybrid: SEP first, with MTObjects fallback for SEP high-mask or morphology-risk cases.'
  )
  Add-Text $sel '10. Outputs and sources' 'Heading 1'
  Add-Text $sel 'Statistical workbook: D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\documentation\Toy Objects SEP vs MTObjects Statistical Comparison.xlsx'
  Add-Text $sel 'Visual comparison folder: D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\Toy Objects comparison\20260821_104129'
  Add-Text $sel 'SEP batch: D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\SEP all galaxy batch\sep_toy_20260817_161404'
  Add-Text $sel 'MTObjects batch: D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\mtobjects all galaxy batch\mtobjects_toy_recovery_20260816_063455'
  Write-Output 'STAGE=results_content_complete'
  $resultPaths=Save-Doc $doc 'Toy Objects SEP versus MTObjects Results and Recommendations'; Write-Output 'STAGE=results_saved'; $doc.Close(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc)

  $word.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word); $word=$null
  Write-Output ('METHOD_DOCX='+$methodPaths[0]); Write-Output ('METHOD_PDF='+$methodPaths[1]); Write-Output ('RESULT_DOCX='+$resultPaths[0]); Write-Output ('RESULT_PDF='+$resultPaths[1])
} finally {
  if($word){try{$word.Quit()}catch{}; [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)}
  [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
