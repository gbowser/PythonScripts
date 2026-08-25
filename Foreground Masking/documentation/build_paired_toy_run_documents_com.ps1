param(
    [string]$ResearchRoot = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects',
    [string]$RunStamp = '20260824_115154'
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName Microsoft.Office.Interop.Word
$DocDir = Join-Path $ResearchRoot 'documentation'
$Control = Join-Path $ResearchRoot "Toy Objects paired optimisation\$RunStamp"
$AnalysisPath = Join-Path $Control 'analysis\paired_toy_run_analysis.json'
$RecoveryChart = Join-Path $Control 'analysis\paired_toy_held_out_recovery.png'
$Composite = Join-Path $ResearchRoot "Toy Objects comparison\$RunStamp\NGC3627_MTO_left_SEP_right_clean.png"
$MethodPath = Join-Path $DocDir 'Toy Objects SEP and MTObjects Methodology.docx'
$ResultsPath = Join-Path $DocDir 'Toy Objects SEP versus MTObjects Results and Recommendations.docx'
$ImprovementsPath = Join-Path $DocDir 'Toy Objects SEP and MTObjects Next Improvements - Detailed Guide.docx'

foreach ($path in @($AnalysisPath, $RecoveryChart, $Composite)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required report input missing: $path" }
}
$a = Get-Content -LiteralPath $AnalysisPath -Raw | ConvertFrom-Json
if ($a.sep.production_182.successful -ne 182 -or $a.mtobjects.production_182.successful -ne 182) {
    throw "Production summaries are incomplete: SEP=$($a.sep.production_182.successful), MTObjects=$($a.mtobjects.production_182.successful)."
}

function Ole([string]$hex) {
    $hex=$hex.TrimStart('#')
    $r=[Convert]::ToInt32($hex.Substring(0,2),16); $g=[Convert]::ToInt32($hex.Substring(2,2),16); $b=[Convert]::ToInt32($hex.Substring(4,2),16)
    return $r + 256*$g + 65536*$b
}
function Pct($value,[int]$places=2) { return ('{0:N'+$places+'}%') -f (100.0*[double]$value) }
function Num($value,[int]$places=3) { return ('{0:N'+$places+'}') -f [double]$value }
function Param($value,[int]$places=4) {
    if ($value -is [int] -or $value -is [long]) { return [string]$value }
    return ('{0:N'+$places+'}') -f [double]$value
}

$navy=Ole '#0B2545'; $blue=Ole '#2E74B5'; $darkBlue=Ole '#1F4D78'; $gray=Ole '#555555'; $light=Ole '#F2F4F7'; $callout=Ole '#E8EEF5'; $white=Ole '#FFFFFF'; $orange=Ole '#D97904'
$wdStyleNormal=[Microsoft.Office.Interop.Word.WdBuiltinStyle]::wdStyleNormal
$wdStyleHeading1=[Microsoft.Office.Interop.Word.WdBuiltinStyle]::wdStyleHeading1
$wdStyleHeading2=[Microsoft.Office.Interop.Word.WdBuiltinStyle]::wdStyleHeading2
$wdStyleHeading3=[Microsoft.Office.Interop.Word.WdBuiltinStyle]::wdStyleHeading3

function Style-Id([string]$style) {
    switch ($style) {
        'Normal' { return $wdStyleNormal }
        'Heading 1' { return $wdStyleHeading1 }
        'Heading 2' { return $wdStyleHeading2 }
        'Heading 3' { return $wdStyleHeading3 }
        default { throw "Unsupported Word style: $style" }
    }
}

function Configure-Document($doc,[string]$runningTitle) {
    foreach($section in $doc.Sections){
        $section.PageSetup.PageWidth=612; $section.PageSetup.PageHeight=792
        $section.PageSetup.TopMargin=72; $section.PageSetup.BottomMargin=72; $section.PageSetup.LeftMargin=72; $section.PageSetup.RightMargin=72
        $section.PageSetup.HeaderDistance=35.4; $section.PageSetup.FooterDistance=35.4
        $section.PageSetup.OddAndEvenPagesHeaderFooter=0; $section.PageSetup.DifferentFirstPageHeaderFooter=0
        foreach($headerIndex in @(1,2,3)) {
            $header=$section.Headers.Item($headerIndex).Range; $header.Text=$runningTitle; $header.Font.Name='Calibri'; $header.Font.Size=9; $header.Font.Color=$gray
            $footer=$section.Footers.Item($headerIndex).Range; $footer.Text='Foreground Masking Research  |  '; $footer.Font.Name='Calibri'; $footer.Font.Size=9; $footer.Font.Color=$gray
            $footer.Collapse(0); [void]$footer.Fields.Add($footer,-1,'PAGE',$true)
        }
    }
    # Built-in numeric style IDs work across localized and stricter Word COM installations.
    $normal=$doc.Styles.Item($wdStyleNormal); $normal.Font.Name='Calibri'; $normal.Font.Size=11; $normal.Font.Color=$gray
    $normal.ParagraphFormat.SpaceBefore=0; $normal.ParagraphFormat.SpaceAfter=6; $normal.ParagraphFormat.LineSpacingRule=5; $normal.ParagraphFormat.LineSpacing=13.2
    $h1=$doc.Styles.Item($wdStyleHeading1); $h1.Font.Name='Calibri'; $h1.Font.Size=16; $h1.Font.Bold=$true; $h1.Font.Color=$blue
    $h1.ParagraphFormat.SpaceBefore=16; $h1.ParagraphFormat.SpaceAfter=8; $h1.ParagraphFormat.KeepWithNext=$true
    $h2=$doc.Styles.Item($wdStyleHeading2); $h2.Font.Name='Calibri'; $h2.Font.Size=13; $h2.Font.Bold=$true; $h2.Font.Color=$blue
    $h2.ParagraphFormat.SpaceBefore=12; $h2.ParagraphFormat.SpaceAfter=6; $h2.ParagraphFormat.KeepWithNext=$true
    $h3=$doc.Styles.Item($wdStyleHeading3); $h3.Font.Name='Calibri'; $h3.Font.Size=12; $h3.Font.Bold=$true; $h3.Font.Color=$darkBlue
    $h3.ParagraphFormat.SpaceBefore=8; $h3.ParagraphFormat.SpaceAfter=4; $h3.ParagraphFormat.KeepWithNext=$true
}
function Add-Text($sel,[string]$text,[string]$style='Normal') {
    $sel.Style=(Style-Id $style); $sel.Font.Bold=0; $sel.Font.Italic=0; $sel.ParagraphFormat.Alignment=0; $sel.TypeText($text); $sel.TypeParagraph()
}
function Add-TitleBlock($sel,[string]$title,[string]$subtitle,[string]$status) {
    $sel.Style=$wdStyleNormal; $sel.Font.Name='Calibri'; $sel.Font.Size=10; $sel.Font.Bold=1; $sel.Font.Color=$blue; $sel.TypeText('FOREGROUND MASKING RESEARCH'); $sel.TypeParagraph()
    $sel.Font.Size=25; $sel.Font.Bold=1; $sel.Font.Color=$navy; $sel.TypeText($title); $sel.TypeParagraph()
    $sel.Font.Size=13; $sel.Font.Bold=0; $sel.Font.Color=$gray; $sel.TypeText($subtitle); $sel.TypeParagraph()
    $sel.Font.Size=10; $sel.TypeText('Prepared: 24 August 2026'); $sel.TypeParagraph(); $sel.TypeText('Run: '+$RunStamp); $sel.TypeParagraph(); $sel.TypeText('Status: '+$status); $sel.TypeParagraph(); $sel.TypeParagraph()
}
function Add-Callout($sel,[string]$label,[string]$text) {
    $sel.Style=$wdStyleNormal; $p=$sel.Paragraphs.Item(1); $p.Shading.BackgroundPatternColor=$callout; $p.Format.LeftIndent=10; $p.Format.RightIndent=10; $p.Format.SpaceBefore=6; $p.Format.SpaceAfter=10
    $sel.Font.Color=$navy; $sel.Font.Bold=1; $sel.TypeText($label+': '); $sel.Font.Bold=0; $sel.TypeText($text); $sel.TypeParagraph()
    $sel.ParagraphFormat.LeftIndent=0; $sel.ParagraphFormat.RightIndent=0; $sel.Shading.BackgroundPatternColor=$white
}
function Add-Bullets($sel,[string[]]$items) {
    foreach($item in $items){ $sel.Style=$wdStyleNormal; $sel.Range.ListFormat.ApplyBulletDefault(); $sel.TypeText($item); $sel.TypeParagraph() }
    $sel.Range.ListFormat.RemoveNumbers(); $sel.ParagraphFormat.LeftIndent=0; $sel.ParagraphFormat.FirstLineIndent=0
}
function Add-Numbered($sel,[string[]]$items) {
    foreach($item in $items){ $sel.Style=$wdStyleNormal; $sel.Range.ListFormat.ApplyNumberDefault(); $sel.TypeText($item); $sel.TypeParagraph() }
    $sel.Range.ListFormat.RemoveNumbers(); $sel.ParagraphFormat.LeftIndent=0; $sel.ParagraphFormat.FirstLineIndent=0
}
function Add-Table($doc,$sel,[object[]]$rows,[double[]]$widths) {
    $table=$doc.Tables.Add($sel.Range,$rows.Count,$widths.Count); $table.AllowAutoFit=$false; $table.Borders.Enable=1
    for($c=1;$c -le $widths.Count;$c++){ $table.Columns.Item($c).Width=$widths[$c-1] }
    for($r=1;$r -le $rows.Count;$r++){
        for($c=1;$c -le $widths.Count;$c++){
            $cell=$table.Cell($r,$c); $cell.Range.Text=[string]$rows[$r-1][$c-1]; $cell.Range.Font.Name='Calibri'; $cell.Range.Font.Size=9.25; $cell.VerticalAlignment=1
            $cell.TopPadding=4; $cell.BottomPadding=4; $cell.LeftPadding=6; $cell.RightPadding=6
            if($r -eq 1){$cell.Range.Font.Bold=1;$cell.Range.Font.Color=$navy;$cell.Shading.BackgroundPatternColor=$light}
        }
    }
    $table.Rows.Item(1).HeadingFormat=-1
    $sel.SetRange($table.Range.End,$table.Range.End); $sel.TypeParagraph(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($table)
}
function Add-Figure($sel,[string]$path,[double]$width,[string]$caption) {
    $shape=$sel.InlineShapes.AddPicture($path,$false,$true); $shape.LockAspectRatio=-1; $shape.Width=$width; $sel.TypeParagraph()
    $sel.Style=$wdStyleNormal; $sel.Font.Name='Calibri'; $sel.Font.Size=9; $sel.Font.Italic=1; $sel.Font.Color=$gray; $sel.ParagraphFormat.Alignment=1; $sel.TypeText($caption); $sel.TypeParagraph(); $sel.ParagraphFormat.Alignment=0; $sel.Font.Italic=0
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($shape)
}
function Add-PageBreak($sel){$sel.InsertBreak(7)}
function Open-For-Rewrite($word,[string]$path) {
    # Build from a clean document and let SaveAs2 replace the named deliverable.
    # This avoids inheriting locks or malformed state from an older report file.
    return $word.Documents.Add()
}
function Save-Doc($doc,[string]$path) {
    if($doc.Path){$doc.Save()}else{$doc.SaveAs2($path,16)}
}

$sepWinner=$a.sep.winner; $mtoWinner=$a.mtobjects.winner
$sepAll=$sepWinner.independent_selection_all40; $mtoAll=$mtoWinner.independent_selection_all40
$pair=$a.paired_held_out_comparisons
$sepProd=$a.sep.production_182; $mtoProd=$a.mtobjects.production_182

$word=$null; $startedWord=$false; $docs=@()
try {
    # Use an isolated Word instance. Attaching to an existing instance can inherit a
    # stale COM server after a failed automation run and can interfere with documents
    # the user already has open.
    $word=New-Object -ComObject Word.Application; $word.Visible=$false; $startedWord=$true
    $word.DisplayAlerts=0

    # Methodology
    $doc=Open-For-Rewrite $word $MethodPath; $docs += $doc; Configure-Document $doc 'Toy Objects Methodology'; $doc.Activate(); $sel=$word.Selection; $sel.SetRange(0,0)
    Add-TitleBlock $sel 'Toy Objects Foreground-Masking Methodology' 'Paired four-fold optimisation and 182-galaxy diagnostic production using SEP and MTObjects' 'Current definitive methodology'
    Add-Callout $sel 'Scope' 'Toy Objects provide synthetic truth for evaluating two masking algorithms. SEP and MTObjects both detect on the original science image. Spike Gate is a separate identification methodology and is excluded.'
    Add-Text $sel '1. Research design' 'Heading 1'
    Add-Text $sel 'The experiment measures recovery of known injected foreground-like objects while quantifying collateral masking. It uses four-fold cross-validation on 40 low-foreground galaxies, a separate common 40-galaxy injection set for selecting among fold winners, and production diagnostics for all 182 galaxies.'
    Add-Table $doc $sel @(
        @('Design element','Recorded implementation'),
        @('Calibration sample','40 unique galaxies in CleanGalaxies.txt'),
        @('Cross-validation','Four fixed folds; 30 training and 10 held out per fold'),
        @('Optimisation budget','40 trials per fold: 8 startup plus 32 TPE trials'),
        @('Parallelism','10 image workers; algorithms run sequentially'),
        @('Detection input','Original science image for SEP and MTObjects'),
        @('Production set','182 galaxies; three validated PNG collections')
    ) @(132,336)
    Add-Text $sel '2. Immutable paired injection contract' 'Heading 1'
    Add-Text $sel "A single manifest was generated before optimisation and marked immutable. Its SHA-256 checksum is $($a.manifest.sha256). Each galaxy record stores the science-image checksum, global and per-galaxy seeds, toy type, centre, amplitude, FWHM, axis ratio, position angle, payload checksum, injection-delta checksum and truth-mask checksum. Both optimisers load and verify the same materialised payloads."
    Add-Table $doc $sel @(
        @('Injection set','Seed','Galaxies','Toys','Purpose'),
        @('cross_validation',[string]$a.manifest.sets.cross_validation.global_seed,[string]$a.manifest.sets.cross_validation.galaxies,[string]$a.manifest.sets.cross_validation.toys,'Training within each fold'),
        @('winner_selection',[string]$a.manifest.sets.winner_selection.global_seed,[string]$a.manifest.sets.winner_selection.galaxies,[string]$a.manifest.sets.winner_selection.toys,'Common independent selection of fold winners')
    ) @(100,65,65,55,183)
    Add-Text $sel '3. Toy population' 'Heading 1'
    Add-Bullets $sel @(
        'Six non-overlapping toys per galaxy, placed wholly inside the investigated region and away from image boundaries.',
        'Mixture: stars 50%, compact clusters 20%, elliptical galaxies 30%.',
        'Peak amplitude: 6-30 times robust background sigma, exactly 20% above the previous 5-25 sigma range.',
        'FWHM: 2-10 pixels for stars/clusters and 5-22 pixels for galaxies; galaxy axis ratio 0.35-0.95; position angle 0-180 degrees.',
        'Truth pixels are defined from the toy model and dilated by one pixel.'
    )
    Add-Text $sel '4. Search spaces and selected parameters' 'Heading 1'
    Add-Table $doc $sel @(
        @('Parameter','SEP search range','SEP winner','MTObjects search range','MTObjects winner'),
        @('Sensitivity','detect_thresh 0.6-2.0',(Param $sepWinner.params.detect_thresh 4),'move_factor 0.0-1.0',(Param $mtoWinner.params.move_factor 4)),
        @('Minimum area','5-35',[string]$sepWinner.params.minarea,'1-40',[string]$mtoWinner.params.minarea),
        @('Deblending','16/32/64; 0.001-0.03',([string]$sepWinner.params.deblend_nthresh+'; '+(Param $sepWinner.params.deblend_cont 6)),'n/a','n/a'),
        @('Background','mesh 32/64/128/256',[string]$sepWinner.params.back_size,'variance 0.0001-10000 outer bound',(Param $mtoWinner.params.bg_variance 7)),
        @('Filter/smoothing','filter 1/3/5/7/9',[string]$sepWinner.params.filter_size,'Gaussian FWHM 0-5',(Param $mtoWinner.params.gaussian_fwhm 4)),
        @('Dilation radius','1-6',[string]$sepWinner.params.dilation_radius,'1-6',[string]$mtoWinner.params.dilation_radius),
        @('Maximum area','20-8000',[string]$sepWinner.params.max_area,'20-3000',[string]$mtoWinner.params.max_area),
        @('Maximum elongation','1.5-30',(Param $sepWinner.params.max_elongation 3),'2-15',(Param $mtoWinner.params.max_elongation 3))
    ) @(90,100,80,115,83)
    Add-Text $sel '5. Common evaluator and denominators' 'Heading 1'
    Add-Text $sel 'The paired-toy-metrics-v1 evaluator is called without alteration by both algorithms. For each image, the uninjected science image is processed first to create a baseline mask. The injected image is then processed with the same parameters.'
    Add-Bullets $sel @(
        'Incremental mask = injected-image mask minus baseline mask. Optimisation recovery and collateral-loss terms use this denominator.',
        'Final mask = complete mask delivered for the injected image. Final metrics describe operational masked area, including pre-existing detections.',
        'Pixel recall = truth overlap divided by truth pixels; precision = truth overlap divided by candidate-mask pixels; F1 is their harmonic mean.',
        'Mean toy recall averages the recovered fraction over six toys; a toy is counted as recovered when at least 50% of its truth pixels are masked.',
        'False-positive fraction counts masked pixels outside toy truth relative to non-truth image area.'
    )
    Add-Text $sel '6. Objective functions and feasibility' 'Heading 1'
    Add-Text $sel 'SEP recovery combines pixel recall (0.45), F1 (0.20), mean toy recall (0.25) and toy detection rate (0.20). Mean mask and false-positive penalties have weights 0.35 and 0.05. MTObjects recovery combines F1 (0.45), mean toy recall (0.35) and detection rate (0.20), with mask and false-positive penalties of 0.50 and 0.10. Both impose a 15% worst-image cap. MTObjects additionally rejects zero/near-zero recovery using minimum detection-rate 0.25 and minimum mean-toy-recall 0.20 constraints.'
    Add-Text $sel '7. Cross-validation and winner selection' 'Heading 1'
    Add-Numbered $sel @(
        'Hold out one fixed group of ten galaxies and optimise 40 trials on the remaining 30.',
        'Evaluate that fold winner on its ten held-out galaxies using the common winner-selection injections.',
        'Evaluate each fold winner on the same independent 40-galaxy winner-selection set.',
        'For SEP, select the lowest all-40 objective. For MTObjects, first require feasibility in every fold, then select the lowest all-40 objective.',
        'Record algorithm, software commit, Python version, platform, worker count, manifest path and complete parameter JSON in every result row.'
    )
    Add-Text $sel '8. Production PNG batches' 'Heading 1'
    Add-Text $sel 'Each winner was applied to all 182 galaxies with deterministic matched injections: seed 202608299, six toys, truth dilation one pixel and 6-30 sigma peaks. The two batch implementations use the same injection algorithm and parameters. The calibration manifest itself contains the 40 optimisation galaxies; extending immutable payload/checksum coverage to all 182 production galaxies remains a reproducibility improvement.'
    Add-Bullets $sel @(
        'Every method PNG contains eight panels: original, original plus toys with green truth boundaries, mask, recovered image, original/processed isophotes and original/processed bar-major profiles.',
        'Recovered-image boundaries distinguish correct toy-associated masks from other masked regions.',
        'Processed profiles use the established log-linear bridge through masked intervals.',
        'Calibration-galaxy filenames carry the suffix _clean.',
        'A third landscape collection places MTObjects left and SEP right with a thick black dashed divider.'
    )
    Add-Text $sel '9. Reproducibility limitations' 'Heading 1'
    Add-Bullets $sel @(
        'Synthetic toys provide exact truth but do not cover the full morphology and brightness distribution of real foreground contaminants.',
        'Masked percentage measures aggressiveness, not whether coherent galaxy structure was harmed.',
        'Incremental and final-mask percentages answer different questions and must be labelled explicitly.',
        'The 182 diagnostic batches are deterministic but should be upgraded to read a full immutable production manifest rather than reconstructing injections from code and seed.'
    )
    Save-Doc $doc $MethodPath; $doc.Close(-1)

    # Results and conclusions
    $doc=Open-For-Rewrite $word $ResultsPath; $docs += $doc; Configure-Document $doc 'Toy Objects Results and Conclusions'; $doc.Activate(); $sel=$word.Selection; $sel.SetRange(0,0)
    Add-TitleBlock $sel 'Toy Objects Results: SEP versus MTObjects' 'Paired 20%-brighter injection experiment with held-out and 182-galaxy evidence' 'Final results and recommendations'
    Add-Callout $sel 'Headline' ('MTObjects recovered more toys in paired held-out testing, but SEP produced a smaller toy-induced incremental mask and the stronger composite objective/F1. The final production masks must therefore be interpreted as a recovery-versus-preservation trade-off rather than a single universal winner.')
    Add-Text $sel '1. Validation status' 'Heading 1'
    Add-Table $doc $sel @(
        @('Deliverable','SEP','MTObjects','Combined'),
        @('Four-fold optimisation',('Complete; winner fold '+$sepWinner.winning_fold),('Complete; winner fold '+$mtoWinner.winning_fold),'n/a'),
        @('Held-out galaxy rows','40','40','Paired one-to-one'),
        @('182-galaxy PNG batch','182 successful','182 successful','182 successful'),
        @('Failures','0','0','0')
    ) @(135,111,111,111)
    Add-Text $sel '2. Paired held-out results' 'Heading 1'
    Add-Table $doc $sel @(
        @('Metric','SEP mean','MTObjects mean','MTO - SEP','Galaxy wins (SEP / MTO / ties)'),
        @('Mean toy recall',(Pct $pair.mean_toy_recall.sep.mean),(Pct $pair.mean_toy_recall.mtobjects.mean),(Pct $pair.mean_toy_recall.mtobjects_minus_sep_mean),([string]$pair.mean_toy_recall.sep_higher+' / '+$pair.mean_toy_recall.mtobjects_higher+' / '+$pair.mean_toy_recall.ties)),
        @('Toys recovered of six',(Num $pair.recovered_toys.sep.mean 2),(Num $pair.recovered_toys.mtobjects.mean 2),(Num $pair.recovered_toys.mtobjects_minus_sep_mean 2),([string]$pair.recovered_toys.sep_higher+' / '+$pair.recovered_toys.mtobjects_higher+' / '+$pair.recovered_toys.ties)),
        @('Pixel recall',(Pct $pair.recall.sep.mean),(Pct $pair.recall.mtobjects.mean),(Pct $pair.recall.mtobjects_minus_sep_mean),([string]$pair.recall.sep_higher+' / '+$pair.recall.mtobjects_higher+' / '+$pair.recall.ties)),
        @('Pixel precision',(Pct $pair.precision.sep.mean 3),(Pct $pair.precision.mtobjects.mean 3),(Pct $pair.precision.mtobjects_minus_sep_mean 3),([string]$pair.precision.sep_higher+' / '+$pair.precision.mtobjects_higher+' / '+$pair.precision.ties)),
        @('F1',(Pct $pair.f_score.sep.mean 3),(Pct $pair.f_score.mtobjects.mean 3),(Pct $pair.f_score.mtobjects_minus_sep_mean 3),([string]$pair.f_score.sep_higher+' / '+$pair.f_score.mtobjects_higher+' / '+$pair.f_score.ties)),
        @('Incremental masked area',(Pct $pair.masked_fraction.sep.mean),(Pct $pair.masked_fraction.mtobjects.mean),(Pct $pair.masked_fraction.mtobjects_minus_sep_mean),([string]$pair.masked_fraction.sep_higher+' / '+$pair.masked_fraction.mtobjects_higher+' / '+$pair.masked_fraction.ties)),
        @('Final masked area',(Pct $pair.final_masked_fraction.sep.mean),(Pct $pair.final_masked_fraction.mtobjects.mean),(Pct $pair.final_masked_fraction.mtobjects_minus_sep_mean),([string]$pair.final_masked_fraction.sep_higher+' / '+$pair.final_masked_fraction.mtobjects_higher+' / '+$pair.final_masked_fraction.ties))
    ) @(120,75,85,75,113)
    Add-Figure $sel $RecoveryChart 430 'Figure 1. Paired held-out recovery across the 40 calibration galaxies. Each algorithm is evaluated on identical winner-selection truth.'
    Add-Text $sel 'Interpretation' 'Heading 2'
    Add-Bullets $sel @(
        ('MTObjects increased mean per-toy recall by '+(Pct $pair.mean_toy_recall.mtobjects_minus_sep_mean)+'; the bootstrap 95% interval for the paired mean difference is '+(Pct $pair.mean_toy_recall.mean_difference_bootstrap_95_ci[0])+' to '+(Pct $pair.mean_toy_recall.mean_difference_bootstrap_95_ci[1])+'.'),
        ('MTObjects recovered '+(Num $pair.recovered_toys.mtobjects_minus_sep_mean 2)+' additional toys per galaxy on average and recovered more toys in '+$pair.recovered_toys.mtobjects_higher+' galaxies, versus '+$pair.recovered_toys.sep_higher+' for SEP.'),
        ('The recovery gain required '+(Pct $pair.masked_fraction.mtobjects_minus_sep_mean)+' more toy-induced incremental masked area on average.'),
        'SEP had the higher mean precision and F1 because its incremental mask was more selective. Precision remains numerically low for both methods because truth toys occupy very little of each image and masks also respond to real sources and galaxy structure.',
        'SEP had the larger final mask on average despite its smaller incremental response. This indicates more baseline masking on uninjected images and demonstrates why incremental and final metrics must be reported together.'
    )
    Add-Text $sel '3. Fold stability and independent winner selection' 'Heading 1'
    $foldRows=,@('Method/fold','Held-out score','Toy recall','Detection rate','Mean incremental mask')
    foreach($f in $a.sep.cross_validation.folds){$foldRows+=,@(('SEP '+$f.fold),(Num $f.held_out_score 4),(Pct $f.held_out_mean_toy_recall),(Pct $f.held_out_toy_detection_rate),(Pct $f.held_out_mean_masked_fraction))}
    foreach($f in $a.mtobjects.cross_validation.folds){$foldRows+=,@(('MTObjects '+$f.fold),(Num $f.held_out_score 4),(Pct $f.held_out_mean_toy_recall),(Pct $f.held_out_toy_detection_rate),(Pct $f.held_out_mean_masked_fraction))}
    Add-Table $doc $sel $foldRows @(85,85,92,92,114)
    Add-Text $sel ('SEP winner fold '+$sepWinner.winning_fold+' achieved independent all-40 score '+(Num $sepAll.score 4)+', mean toy recall '+(Pct $sepAll.mean_toy_recall)+', detection rate '+(Pct $sepAll.toy_detection_rate)+' and mean incremental mask '+(Pct $sepAll.mean_masked_fraction)+'. MTObjects winner fold '+$mtoWinner.winning_fold+' achieved score '+(Num $mtoAll.score 4)+', mean toy recall '+(Pct $mtoAll.mean_toy_recall)+', detection rate '+(Pct $mtoAll.toy_detection_rate)+' and mean incremental mask '+(Pct $mtoAll.mean_masked_fraction)+'. The scores use different method-specific recovery weightings, so component metrics are the safer head-to-head evidence.')
    Add-PageBreak $sel
    Add-Text $sel '4. Production 182-galaxy mask extent' 'Heading 1'
    Add-Table $doc $sel @(
        @('Statistic','SEP final mask','MTObjects final mask'),
        @('Mean',(Pct $sepProd.masked_fraction.mean),(Pct $mtoProd.masked_fraction.mean)),
        @('Median',(Pct $sepProd.masked_fraction.median),(Pct $mtoProd.masked_fraction.median)),
        @('10th percentile',(Pct $sepProd.masked_fraction.p10),(Pct $mtoProd.masked_fraction.p10)),
        @('25th percentile',(Pct $sepProd.masked_fraction.p25),(Pct $mtoProd.masked_fraction.p25)),
        @('75th percentile',(Pct $sepProd.masked_fraction.p75),(Pct $mtoProd.masked_fraction.p75)),
        @('90th percentile',(Pct $sepProd.masked_fraction.p90),(Pct $mtoProd.masked_fraction.p90)),
        @('Maximum',(Pct $sepProd.masked_fraction.maximum),(Pct $mtoProd.masked_fraction.maximum)),
        @('Galaxies above 10%',[string]$sepProd.masked_fraction_threshold_counts.above_10_percent,[string]$mtoProd.masked_fraction_threshold_counts.above_10_percent),
        @('Galaxies above 15%',[string]$sepProd.masked_fraction_threshold_counts.above_15_percent,[string]$mtoProd.masked_fraction_threshold_counts.above_15_percent),
        @('Galaxies above 20%',[string]$sepProd.masked_fraction_threshold_counts.above_20_percent,[string]$mtoProd.masked_fraction_threshold_counts.above_20_percent)
    ) @(180,144,144)
    Add-Text $sel 'These production percentages are final mask fractions from injected images. They describe operational mask extent, not toy-specific recovery. The 40-galaxy paired evaluator remains the controlled source for recovery and attribution. Any production galaxy above the 15% optimisation cap should be treated as a mandatory review case rather than assumed acceptable.'
    Add-PageBreak $sel
    Add-Text $sel '5. Visual comparison' 'Heading 1'
    Add-Figure $sel $Composite 455 'Figure 2. NGC3627: MTObjects on the left and SEP on the right, separated by a black dashed line. Both panels use the same deterministic toy injection.'
    Add-Text $sel '6. Conclusions' 'Heading 1'
    Add-Bullets $sel @(
        'The zero-mask failure mode has been resolved for MTObjects: every selected candidate met the recovery constraints and every fold showed non-zero recovery.',
        'MTObjects is the stronger recovery-priority method for these brighter toys: it recovers more toy pixels and more complete toys across most held-out galaxies.',
        'SEP is the more selective toy-induced detector: it achieves higher precision/F1 and masks less additional area after injection.',
        'Neither method is yet proven superior for preservation of bar and disc morphology because total masked area is not a morphology-risk metric.',
        'The paired design removes injection-seed confounding from the algorithm comparison and is materially more defensible than the previous separate-seed runs.'
    )
    Add-Text $sel '7. Recommendation' 'Heading 1'
    Add-Callout $sel 'Recommended operating position' 'Do not choose a universal winner from toy recovery alone. Use MTObjects when missing a credible foreground source is the dominant risk, with a hard total-mask and morphology guardrail. Use SEP when minimising toy-induced collateral masking is the dominant risk, also with a final-mask guardrail because its baseline masks can be larger.'
    Add-Numbered $sel @(
        'Make morphology-risk measurement the next optimisation priority: protected-zone overlap, largest-component fraction, annular continuity and bar-profile bridge length.',
        'Run multi-objective optimisation on recovery, incremental collateral masking and morphology risk rather than compressing all goals into one scalar.',
        'Validate both frozen winners on a manually labelled real-foreground subset before adopting either for final science production.',
        'Test a guarded hybrid that selects or combines masks only when explicit quality rules are satisfied.',
        'Extend immutable materialised injections and checksums from the 40 optimisation galaxies to all 182 production diagnostics.'
    )
    Add-Text $sel '8. Authoritative outputs' 'Heading 1'
    Add-Bullets $sel @(
        ('SEP optimisation: '+(Join-Path $ResearchRoot "SEP\Toy Objects\$RunStamp\optimisation")),
        ('MTObjects optimisation: '+(Join-Path $ResearchRoot "MTObjects\Toy Objects\$RunStamp\optimisation")),
        ('Paired manifest and analysis: '+$Control),
        ('SEP PNGs: '+$a.png_outputs.sep),
        ('MTObjects PNGs: '+$a.png_outputs.mtobjects),
        ('Combined PNGs: '+$a.png_outputs.combined)
    )
    Save-Doc $doc $ResultsPath; $doc.Close(-1)

    # Further improvements
    $doc=Open-For-Rewrite $word $ImprovementsPath; $docs += $doc; Configure-Document $doc 'Toy Objects Further Improvements'; $doc.Activate(); $sel=$word.Selection; $sel.SetRange(0,0)
    Add-TitleBlock $sel 'Toy Objects: Further Improvements' 'Updated programme following the paired 20%-brighter SEP and MTObjects experiment' 'Prioritised implementation guide'
    Add-Callout $sel 'Status change' 'The former Improvement 1 - identical optimisation injections, checksums, fixed folds, common evaluator and runtime metadata - has now been implemented for the 40-galaxy optimisation experiment. It is no longer the principal blocker. The next priority is explicit measurement of damage to coherent galaxy structure.'
    Add-Text $sel '1. Completed foundation: paired optimisation truth' 'Heading 1'
    Add-Table $doc $sel @(
        @('Requirement','Status','Evidence'),
        @('Single immutable injection manifest','Complete','paired_toy_injection_manifest.json; SHA-256 recorded'),
        @('Image, payload, delta and truth checksums','Complete','Verified when materialised injections are loaded'),
        @('Identical folds and truth for both algorithms','Complete','Fold seed 202608150; 40 paired held-out rows'),
        @('Common metrics and denominators','Complete','paired-toy-metrics-v1 evaluator'),
        @('Baseline plus injected masks','Complete','Incremental and final fields retained'),
        @('Software/runtime/worker metadata','Complete','Commit, Python, platform, workers and parameter JSON in rows'),
        @('Immutable coverage for all 182 production galaxies','Partial','Production uses deterministic common seed/code; materialised checksummed payloads cover the 40 calibration galaxies')
    ) @(150,75,243)
    Add-Text $sel 'Immediate closure action' 'Heading 2'
    Add-Text $sel 'Generate a production injection set containing all 182 galaxies and make both batch tools load it through the same checksum-verifying function used by optimisation. Store a production-manifest checksum in both summary CSVs and reject a batch if any galaxy payload differs.'
    Add-Text $sel '2. Improvement 2 - quantify coherent morphology loss' 'Heading 1'
    Add-Text $sel 'Why it matters' 'Heading 2'
    Add-Text $sel 'The current results show why total mask percentage is insufficient: SEP produced the smaller incremental mask but the larger mean final mask, while MTObjects recovered more toys. Neither fact identifies whether a mask cuts across a bar, nucleus, spiral arm or coherent isophote.'
    Add-Text $sel 'Metrics to implement' 'Heading 2'
    Add-Bullets $sel @(
        'Protected-zone overlap: fraction of mask within the nucleus, bar corridor and science-defined isophotal zones.',
        'Largest connected-component fraction and maximum radial/azimuthal span: detects coherent over-masks hidden inside an acceptable total percentage.',
        'Annular continuity loss: change in valid-pixel coverage around matched elliptical annuli.',
        'Isophotal disruption: contour fragmentation, displacement and area change before versus after masking.',
        'Bar-profile bridge burden: masked length, longest bridge, number of bridges and bridge fraction inside the bar region.',
        'Asymmetry of masking across the bar major axis and between opposite annular sectors.'
    )
    Add-Text $sel 'Implementation and acceptance' 'Heading 2'
    Add-Numbered $sel @(
        'Compute metrics for baseline and injected masks separately so pre-existing algorithm behaviour is not attributed to toys.',
        'Have an astronomer label a stratified sample as safe, review or severe morphology damage.',
        'Fit thresholds only on a development subset; freeze them before validation.',
        'Accept the metric family only if it ranks severe cases above safe cases and explains obvious visual failures such as long profile bridges.'
    )
    Add-Text $sel '3. Improvement 3 - Pareto optimisation' 'Heading 1'
    Add-Text $sel 'Replace winner-takes-all scalar selection with explicit objectives: maximise per-toy recall/detection; minimise incremental non-toy mask; minimise final morphology risk. Retain the 15% hard cap and recovery feasibility rules.'
    Add-Bullets $sel @(
        'Use the same four folds, immutable injections and evaluator so gains are attributable to optimisation rather than changed truth.',
        'Retain every non-dominated candidate and publish recovery-versus-mask and recovery-versus-morphology plots.',
        'Predeclare three operating points: recovery-priority, balanced and preservation-priority.',
        'Select the production point using held-out evidence and frozen feasibility thresholds, not the training score.',
        'Repeat with at least three independent injection manifests to measure sensitivity to toy placement.'
    )
    Add-Text $sel '4. Improvement 4 - real foreground validation' 'Heading 1'
    Add-Text $sel 'Toy truth is controlled but synthetic. Create a manually labelled subset of approximately 30-50 galaxies spanning apparent size, inclination, bar length, surface brightness, crowding and foreground density.'
    Add-Table $doc $sel @(
        @('Annotation layer','Purpose'),
        @('Definite foreground objects','Measure real-object detection and pixel recovery'),
        @('Ambiguous objects','Separate uncertainty from clear errors'),
        @('Galaxy structure to protect','Measure scientifically harmful masking'),
        @('Ignore/invalid regions','Exclude defects and unusable boundaries'),
        @('Reviewer confidence','Support sensitivity analysis and adjudication')
    ) @(165,303)
    Add-Text $sel 'Freeze all parameters before inspecting validation outcomes. Report object recall, pixel recall/precision, protected-structure false positives, mask burden and inter-reviewer agreement. Do not tune on this subset.'
    Add-Text $sel '5. Improvement 5 - guarded hybrid' 'Heading 1'
    Add-Text $sel 'The paired result supports a hybrid hypothesis: MTObjects supplies higher recovery, while SEP supplies a more selective incremental response. A hybrid should be evaluated only after morphology-risk thresholds are calibrated.'
    Add-Numbered $sel @(
        'Run both frozen algorithms and compute recovery proxies, total mask, morphology risk and method disagreement.',
        'Use MTObjects where recovery evidence is strong and risk remains below limits.',
        'Use SEP where MTObjects breaches morphology or total-mask guardrails and SEP remains feasible.',
        'Send extreme disagreement or dual failure to manual review; never silently choose a mask.',
        'Compare selection, intersection and constrained-union variants against each single method on held-out and real-labelled data.'
    )
    Add-Text $sel '6. Improvement 6 - robustness across toy difficulty' 'Heading 1'
    Add-Text $sel 'The present run uses 6-30 sigma peaks, 20% brighter than the earlier range. A production decision should not depend on one brightness distribution.'
    Add-Bullets $sel @(
        'Create preregistered faint, standard and bright strata, for example 4-12, 6-30 and 20-80 sigma, without mixing them during reporting.',
        'Report recovery curves by peak sigma, FWHM, object type, axis ratio and local galaxy surface brightness.',
        'Use multiple immutable seeds and hierarchical summaries so galaxy and injection variability are both visible.',
        'Test whether selected parameters remain feasible when toys lie near strong bars, spiral arms and steep nuclear gradients.'
    )
    Add-Text $sel '7. Prioritised roadmap' 'Heading 1'
    Add-Table $doc $sel @(
        @('Priority','Work package','Gate to proceed'),
        @('1','Extend immutable manifest to all 182 and add production checksum columns','182 matched payloads; no checksum mismatch; three PNG sets reproducible'),
        @('2','Morphology-risk pilot and reviewer labels','Metrics discriminate safe versus severe masks'),
        @('3','Pareto optimisation across multiple manifests','Stable feasible operating points across folds/seeds'),
        @('4','Frozen real-foreground validation','Recovery and structure-preservation evidence agrees with intended use'),
        @('5','Guarded hybrid evaluation','Improves primary metrics without unacceptable review burden'),
        @('6','Final production rerun and documentation','182 successes; all flags and provenance retained')
    ) @(55,205,208)
    Add-Text $sel '8. Recommended next decision' 'Heading 1'
    Add-Callout $sel 'Recommendation' 'Complete the all-182 immutable production manifest, then implement and label morphology-risk metrics before spending another full optimisation budget. Once those measures are stable, run paired Pareto optimisation for SEP and MTObjects across multiple seeds. This sequence addresses the largest remaining scientific uncertainty: not whether a toy was found, but whether the recovered mask preserves the galaxy structures needed for analysis.'
    Save-Doc $doc $ImprovementsPath; $doc.Close(-1)

    [pscustomobject]@{Methodology=$MethodPath;Results=$ResultsPath;Improvements=$ImprovementsPath} | ConvertTo-Json
}
finally {
    if($word -ne $null -and $startedWord){$word.Quit()}
    if($word -ne $null){[void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)}
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
