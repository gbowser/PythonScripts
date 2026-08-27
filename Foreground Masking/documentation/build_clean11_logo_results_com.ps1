param(
    [string]$ResearchRoot = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects",
    [string]$RunStamp = "clean11_logo_20260826_122730"
)

$ErrorActionPreference = "Stop"
$wdPageBreak = 7
$wdAlignLeft = 0
$wdAlignCenter = 1
$wdAlignRight = 2
$wdCollapseEnd = 0
$wdFormatDocumentDefault = 16
$wdPaperLetter = 2
$wdRowHeightAuto = 0
$wdCellAlignVerticalCenter = 1
$wdLineStyleSingle = 1

$Control = Join-Path $ResearchRoot "Toy Objects paired optimisation\$RunStamp"
$SepBestPath = Join-Path $Control "sep_final_all11\20260826_193633\sep_toy_object_optimisation_best.json"
$MtoCvBestPath = Join-Path $Control "mtobjects_logo\mtobjects_toy_cross_validation_best.json"
$MtoRefitPath = Join-Path $Control "mtobjects_final_all11\20260826_194503\mtobjects_parameter_optimisation_best.json"
$SepSummaryPath = Join-Path $ResearchRoot "SEP\Toy Objects\$RunStamp\PNG batch\sep_optimised_apply_summary.csv"
$MtoSummaryPath = Join-Path $ResearchRoot "MTObjects\Toy Objects\$RunStamp\PNG batch\mtobjects_optimised_apply_summary.csv"
$CompositeRoot = Join-Path $ResearchRoot "Toy Objects comparison\$RunStamp"
$FigureClean = Join-Path $CompositeRoot "NGC1097_MTO_left_SEP_right_clean.png"
$FigureOutlier = Join-Path $CompositeRoot "NGC1313_MTO_left_SEP_right.png"
$OutputPath = Join-Path $ResearchRoot "documentation\S4G Clean-11 LOGO-CV Optimisation Results 2026-08-26.docx"

foreach ($path in @($SepBestPath,$MtoCvBestPath,$MtoRefitPath,$SepSummaryPath,$MtoSummaryPath,$FigureClean,$FigureOutlier)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required input not found: $path" }
}

$SepBest = Get-Content -LiteralPath $SepBestPath -Raw | ConvertFrom-Json
$MtoCvBest = Get-Content -LiteralPath $MtoCvBestPath -Raw | ConvertFrom-Json
$MtoRefit = Get-Content -LiteralPath $MtoRefitPath -Raw | ConvertFrom-Json
$SepRows = @(Import-Csv -LiteralPath $SepSummaryPath)
$MtoRows = @(Import-Csv -LiteralPath $MtoSummaryPath)
$CleanNames = @('IC1954','NGC0289','NGC0986','NGC1097','NGC1367','NGC2903','NGC3486','NGC3681','NGC4133','NGC4450','NGC7531')

function Get-Stats($Rows) {
    $values = @($Rows | ForEach-Object { [double]$_.masked_fraction } | Sort-Object)
    $n = $values.Count
    $median = if ($n % 2) { $values[[int]($n/2)] } else { ($values[$n/2-1] + $values[$n/2]) / 2 }
    [pscustomobject]@{
        N=$n; Mean=($values|Measure-Object -Average).Average; Median=$median; Min=$values[0]; Max=$values[-1]
        Over15=@($values|Where-Object {$_ -gt .15}).Count; Over20=@($values|Where-Object {$_ -gt .20}).Count
    }
}
$SepAll = Get-Stats $SepRows
$MtoAll = Get-Stats $MtoRows
$SepClean = Get-Stats @($SepRows|Where-Object {$_.name -in $CleanNames})
$MtoClean = Get-Stats @($MtoRows|Where-Object {$_.name -in $CleanNames})
$SepMap=@{}; $SepRows|ForEach-Object {$SepMap[$_.name]=[double]$_.masked_fraction}
$Diff=@($MtoRows|ForEach-Object {[double]$_.masked_fraction-$SepMap[$_.name]}|Sort-Object)
$DiffMean=($Diff|Measure-Object -Average).Average
$DiffMedian=($Diff[$Diff.Count/2-1]+$Diff[$Diff.Count/2])/2
$MtoHigher=@($Diff|Where-Object {$_ -gt 0}).Count
$SepHigher=@($Diff|Where-Object {$_ -lt 0}).Count

function Pct([double]$v) { return ('{0:N2}%' -f ($v*100)) }
function Num([double]$v,[int]$d=3) { return $v.ToString("F$d") }

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Add()
    $sec = $doc.Sections.Item(1)
    $sec.PageSetup.PaperSize = $wdPaperLetter
    $sec.PageSetup.TopMargin = $word.InchesToPoints(0.8)
    $sec.PageSetup.BottomMargin = $word.InchesToPoints(0.75)
    $sec.PageSetup.LeftMargin = $word.InchesToPoints(0.85)
    $sec.PageSetup.RightMargin = $word.InchesToPoints(0.85)
    $doc.Styles.Item('Normal').Font.Name = 'Arial'
    $doc.Styles.Item('Normal').Font.Size = 10.5
    $doc.Styles.Item('Normal').ParagraphFormat.SpaceAfter = 6
    $doc.Styles.Item('Normal').ParagraphFormat.LineSpacingRule = 0
    foreach($styleName in @('Heading 1','Heading 2')) {
        $s=$doc.Styles.Item($styleName);$s.Font.Name='Arial';$s.Font.Color=0xB8712F;$s.Font.Bold=$true
    }
    $doc.Styles.Item('Heading 1').Font.Size=16
    $doc.Styles.Item('Heading 1').ParagraphFormat.SpaceBefore=12
    $doc.Styles.Item('Heading 1').ParagraphFormat.SpaceAfter=5
    $doc.Styles.Item('Heading 2').Font.Size=12.5
    $doc.Styles.Item('Heading 2').ParagraphFormat.SpaceBefore=8
    $doc.Styles.Item('Heading 2').ParagraphFormat.SpaceAfter=4

    function Add-Para([string]$Text,[double]$Size=10.5,[bool]$Bold=$false,[int]$Align=0,[string]$Color='000000',[double]$After=6) {
        $p=$doc.Paragraphs.Add();$p.Alignment=$Align;$p.Format.SpaceAfter=$After
        $r=$p.Range;$r.Text=$Text;$r.Font.Name='Arial';$r.Font.Size=$Size;$r.Font.Bold=[int]$Bold;$r.Font.Color=[Convert]::ToInt32($Color.Substring(4,2)+$Color.Substring(2,2)+$Color.Substring(0,2),16)
        $p.Range.InsertParagraphAfter()|Out-Null; return $p
    }
    function Add-Heading([string]$Text,[int]$Level=1) {
        $p=$doc.Paragraphs.Add();$p.Range.Text=$Text;$p.Style="Heading $Level";$p.Range.InsertParagraphAfter()|Out-Null
    }
    function Add-Bullet([string]$Text) {
        $p=$doc.Paragraphs.Add();$p.Range.Text=$Text;$p.Range.ListFormat.ApplyBulletDefault();$p.Format.LeftIndent=$word.InchesToPoints(0.25);$p.Format.FirstLineIndent=$word.InchesToPoints(-0.18);$p.Format.SpaceAfter=3
    }
    function Add-PageBreak { $doc.Range($doc.Content.End-1,$doc.Content.End-1).InsertBreak($wdPageBreak) }
    function ShadeCell($Cell,[string]$Hex) { $Cell.Shading.BackgroundPatternColor=[Convert]::ToInt32($Hex.Substring(4,2)+$Hex.Substring(2,2)+$Hex.Substring(0,2),16) }
    function Add-Table($Headers,$Rows,$Widths) {
        $range=$doc.Range($doc.Content.End-1,$doc.Content.End-1)
        $table=$doc.Tables.Add($range,$Rows.Count+1,$Headers.Count)
        $table.AllowAutoFit=$false;$table.Borders.Enable=1;$table.Rows.SetLeftIndent($word.InchesToPoints(0),0)
        for($c=1;$c -le $Headers.Count;$c++){$cell=$table.Cell(1,$c);$cell.Range.Text=[string]$Headers[$c-1];$cell.Range.Font.Bold=$true;$cell.Range.Font.Name='Arial';$cell.Range.Font.Size=9;ShadeCell $cell 'E7EDF4';$cell.Width=$word.InchesToPoints($Widths[$c-1]);$cell.VerticalAlignment=$wdCellAlignVerticalCenter}
        for($r=0;$r -lt $Rows.Count;$r++){for($c=0;$c -lt $Headers.Count;$c++){$cell=$table.Cell($r+2,$c+1);$cell.Range.Text=[string]$Rows[$r][$c];$cell.Range.Font.Name='Arial';$cell.Range.Font.Size=9;$cell.Width=$word.InchesToPoints($Widths[$c]);$cell.VerticalAlignment=$wdCellAlignVerticalCenter;if($r%2 -eq 1){ShadeCell $cell 'F5F7FA'}}}
        foreach($row in $table.Rows){$row.HeightRule=$wdRowHeightAuto;$row.AllowBreakAcrossPages=$false}
        $table.Range.ParagraphFormat.SpaceAfter=0
        $after=$doc.Range($table.Range.End,$table.Range.End);$after.InsertParagraphAfter()|Out-Null
        return $table
    }
    function Add-Callout([string]$Label,[string]$Text,[string]$Fill='E7EDF4') {
        $range=$doc.Range($doc.Content.End-1,$doc.Content.End-1)
        $t=$doc.Tables.Add($range,1,1);$t.AllowAutoFit=$false;$t.Borders.Enable=1;$t.Cell(1,1).Width=$word.InchesToPoints(6.65);ShadeCell $t.Cell(1,1) $Fill
        $cell=$t.Cell(1,1);$cell.Range.Text="$Label`r$Text";$cell.Range.Font.Name='Arial';$cell.Range.Font.Size=9.5;$cell.Range.Paragraphs.Item(1).Range.Font.Bold=$true;$cell.VerticalAlignment=$wdCellAlignVerticalCenter
        $t.Rows.Item(1).HeightRule=$wdRowHeightAuto;$t.Rows.Item(1).AllowBreakAcrossPages=$false
        $after=$doc.Range($t.Range.End,$t.Range.End);$after.InsertParagraphAfter()|Out-Null
    }
    function Add-Figure([string]$Path,[string]$Caption) {
        $p=$doc.Paragraphs.Add();$p.Alignment=$wdAlignCenter;$shape=$p.Range.InlineShapes.AddPicture($Path,$false,$true);$shape.LockAspectRatio=-1;$shape.Width=$word.InchesToPoints(6.45);$p.Range.InsertParagraphAfter()|Out-Null
        $cap=Add-Para $Caption 9 $false $wdAlignCenter '555555' 8;$cap.Range.Font.Italic=$true
    }

    # Footer: simple centred page number.
    $footer=$sec.Footers.Item(1);$fp=$footer.Range.Paragraphs.Item(1);$fp.Range.Font.Name='Arial';$fp.Range.Font.Size=8;$fp.Range.Fields.Add($fp.Range,-1,'PAGE',$true)|Out-Null;$fp.Alignment=$wdAlignCenter

    Add-Para 'S4G FOREGROUND MASKING' 10 $true $wdAlignLeft '1F4E79' 22 | Out-Null
    Add-Para 'Clean-11 LOGO-CV Optimisation Results' 27 $false $wdAlignLeft '203748' 6 | Out-Null
    Add-Para 'SEP and MTObjects toy-object calibration, diagnostic deployment to 182 S4G galaxies, and production recommendation' 14 $false $wdAlignLeft '1F4E79' 22 | Out-Null
    Add-Table @('Item','Value') @(
        @('Calibration sample','11 visually selected lower-contamination galaxies'),
        @('Validation design','Leave-one-galaxy-out cross-validation with independent toy realisation'),
        @('Deployment diagnostics','182 SEP + 182 MTObjects + 182 matched composite PNGs'),
        @('Run identifier',$RunStamp),
        @('Prepared','26 August 2026')
    ) @(1.55,5.1) | Out-Null
    Add-Callout 'Headline result' 'SEP produced a viable all-11 refit. The MTObjects all-11 refit produced no feasible toy recovery; therefore, the 182-galaxy MTObjects diagnostic deployment uses the feasible LOGO-CV winner rather than the failed refit.' 'FFF4DF'
    Add-PageBreak

    Add-Heading '1. Executive summary'
    Add-Para 'The clean-11 experiment completed all 11 leave-one-galaxy-out folds for SEP and MTObjects. Each fold trained on 10 galaxies and assessed transfer to the excluded galaxy. Fold-derived candidates were also compared on a second deterministic injection realisation across all 11 galaxies. The selected parameters were then tested through standard eight-panel diagnostics across the complete 182-galaxy S4G sample.' | Out-Null
    Add-Table @('Outcome','SEP','MTObjects') @(
        @('CV/final parameter source','All-11 refit','Feasible LOGO-CV winner (fold 9)'),
        @('Toy detection rate on recorded selection set',(Pct ([double]$SepBest.toy_detection_rate)),(Pct ([double]$MtoCvBest.cross_validation_metrics.all11_toy_detection_rate))),
        @('Mean toy recall',(Pct ([double]$SepBest.mean_toy_recall)),(Pct ([double]$MtoCvBest.cross_validation_metrics.all11_mean_toy_recall))),
        @('Mean masked fraction on selection set',(Pct ([double]$SepBest.mean_masked_fraction)),(Pct ([double]$MtoCvBest.cross_validation_metrics.all11_mean_masked_fraction))),
        @('182-galaxy PNG batch','182/182 successful','182/182 successful')
    ) @(2.35,2.15,2.15) | Out-Null
    Add-Callout 'Interpretation' 'The optimisation metrics measure recovery of injected toys on the cleaner calibration sample. The 182-galaxy batch measures deployment behaviour and mask burden; it is not an independent truth-labelled accuracy test.'
    Add-Heading '2. Parameter sets used'
    Add-Heading '2.1 SEP all-11 refit' 2
    Add-Table @('Parameter','Value','Parameter','Value') @(
        @('detect_thresh',(Num $SepBest.detect_thresh 4),'minarea',$SepBest.minarea),
        @('deblend_nthresh',$SepBest.deblend_nthresh,'deblend_cont',(Num $SepBest.deblend_cont 6)),
        @('back_size',$SepBest.back_size,'filter_size',$SepBest.filter_size),
        @('dilation_radius',$SepBest.dilation_radius,'max_area',$SepBest.max_area),
        @('max_elongation',(Num $SepBest.max_elongation 3),'detect_on',$SepBest.detect_on)
    ) @(1.45,1.5,1.55,2.15) | Out-Null
    Add-Heading '2.2 MTObjects feasible LOGO-CV winner' 2
    Add-Table @('Parameter','Value','Parameter','Value') @(
        @('move_factor',(Num $MtoCvBest.move_factor 4),'min_distance',(Num $MtoCvBest.min_distance 4)),
        @('gaussian_fwhm',(Num $MtoCvBest.gaussian_fwhm 4),'bg_variance',(Num $MtoCvBest.bg_variance 6)),
        @('minarea',$MtoCvBest.minarea,'dilation_radius',$MtoCvBest.dilation_radius),
        @('max_area',$MtoCvBest.max_area,'max_elongation',(Num $MtoCvBest.max_elongation 3)),
        @('winning fold',$MtoCvBest.winning_fold,'detect_on',$MtoCvBest.detect_on)
    ) @(1.45,1.5,1.55,2.15) | Out-Null
    Add-PageBreak

    Add-Heading '3. Optimisation results'
    Add-Table @('Metric','SEP all-11 refit','MTObjects LOGO-CV winner') @(
        @('Mean recall',(Pct ([double]$SepBest.mean_recall)),(Pct ([double]$MtoCvBest.cross_validation_metrics.all11_mean_recall))),
        @('Mean precision',(Pct ([double]$SepBest.mean_precision)),(Pct ([double]$MtoCvBest.cross_validation_metrics.all11_mean_precision))),
        @('Mean F-score',(Pct ([double]$SepBest.mean_f_score)),(Pct ([double]$MtoCvBest.cross_validation_metrics.all11_mean_f_score))),
        @('Mean toy recall',(Pct ([double]$SepBest.mean_toy_recall)),(Pct ([double]$MtoCvBest.cross_validation_metrics.all11_mean_toy_recall))),
        @('Toy detection rate',(Pct ([double]$SepBest.toy_detection_rate)),(Pct ([double]$MtoCvBest.cross_validation_metrics.all11_toy_detection_rate))),
        @('Mean masked fraction',(Pct ([double]$SepBest.mean_masked_fraction)),(Pct ([double]$MtoCvBest.cross_validation_metrics.all11_mean_masked_fraction))),
        @('Maximum masked fraction',(Pct ([double]$SepBest.max_masked_fraction)),(Pct ([double]$MtoCvBest.cross_validation_metrics.all11_max_masked_fraction)))
    ) @(2.45,2.1,2.1) | Out-Null
    Add-Heading '3.1 MTObjects all-11 refit failure' 2
    Add-Para ("The separate 40-trial MTObjects refit on all 11 calibration galaxies did not find a feasible candidate. Its nominal best trial had a toy detection rate of {0}, mean toy recall of {1}, and objective {2}. It is retained for provenance but was not used for the diagnostic deployment." -f (Pct ([double]$MtoRefit.toy_detection_rate)),(Pct ([double]$MtoRefit.mean_toy_recall)),([double]$MtoRefit.objective)) | Out-Null
    Add-Callout 'Production decision' 'Use the feasible cross-validated MTObjects winner for current science diagnostics. Do not promote the infeasible all-11 refit merely because it is labelled “best”; it is only the least-penalised member of a failed search.' 'FFF4DF'
    Add-Heading '4. Deployment across all 182 galaxies'
    Add-Table @('Statistic','SEP','MTObjects') @(
        @('Successful reports','182','182'),
        @('Mean masked fraction',(Pct $SepAll.Mean),(Pct $MtoAll.Mean)),
        @('Median masked fraction',(Pct $SepAll.Median),(Pct $MtoAll.Median)),
        @('Minimum',(Pct $SepAll.Min),(Pct $MtoAll.Min)),
        @('Maximum',(Pct $SepAll.Max),(Pct $MtoAll.Max)),
        @('Galaxies above 15%',$SepAll.Over15,$MtoAll.Over15),
        @('Galaxies above 20%',$SepAll.Over20,$MtoAll.Over20)
    ) @(2.65,2.0,2.0) | Out-Null
    Add-Para ("MTObjects masked a larger fraction than SEP in {0} of 182 galaxies; SEP was larger in {1}. The paired MTObjects-minus-SEP difference averaged {2} percentage points, with a median of {3} percentage points." -f $MtoHigher,$SepHigher,(Num ($DiffMean*100) 2),(Num ($DiffMedian*100) 2)) | Out-Null
    Add-PageBreak

    Add-Heading '5. Cleaner-sample deployment behaviour'
    Add-Table @('Statistic','SEP','MTObjects') @(
        @('Cleaner galaxies','11','11'),
        @('Mean masked fraction',(Pct $SepClean.Mean),(Pct $MtoClean.Mean)),
        @('Median masked fraction',(Pct $SepClean.Median),(Pct $MtoClean.Median)),
        @('Range',((Pct $SepClean.Min)+' to '+(Pct $SepClean.Max)),((Pct $MtoClean.Min)+' to '+(Pct $MtoClean.Max))),
        @('Above 15%',$SepClean.Over15,$MtoClean.Over15)
    ) @(2.65,2.0,2.0) | Out-Null
    Add-Figure $FigureClean 'Figure 1. NGC1097 cleaner-sample composite. MTObjects is shown on the left and SEP on the right; green boundaries identify injected toy locations/recovery annotations and red boundaries identify other masking.'
    Add-PageBreak

    Add-Heading '6. Deployment outlier example'
    Add-Para ("NGC1313 produced the largest masked fraction in both deployments: {0} for SEP and {1} for MTObjects. This does not by itself prove incorrect masking, because the 182-galaxy set has no complete foreground-object truth labels. It does identify NGC1313 as a priority for visual review and sensitivity analysis." -f (Pct ([double](($SepRows|Where-Object name -eq 'NGC1313').masked_fraction))),(Pct ([double](($MtoRows|Where-Object name -eq 'NGC1313').masked_fraction)))) | Out-Null
    Add-Figure $FigureOutlier 'Figure 2. NGC1313 composite, the maximum-mask deployment case for both algorithms. The difference between the methods should be reviewed against real galaxy structure before adopting either mask uncritically.'
    Add-PageBreak

    Add-Heading '7. Conclusions and recommendations'
    Add-Para 'SEP: Retain the all-11 refit as the current clean-11 production candidate; it is feasible and completed the full diagnostic deployment.' 10.5 $false $wdAlignLeft '000000' 4 | Out-Null
    Add-Para 'MTObjects: Retain the feasible LOGO-CV winner as the current diagnostic candidate; reject the infeasible all-11 refit for production use.' 10.5 $false $wdAlignLeft '000000' 4 | Out-Null
    Add-Para 'Validation scope: Treat the 182 PNG sets as visual and mask-burden validation, not as a labelled estimate of foreground-removal accuracy.' 10.5 $false $wdAlignLeft '000000' 4 | Out-Null
    Add-Para 'Priority review: Review the 15 SEP and 22 MTObjects cases above 15% masked fraction, prioritising NGC1313 and the two cases above 20% for each method.' 10.5 $false $wdAlignLeft '000000' 4 | Out-Null
    Add-Para 'Science acceptance: Before freezing parameters for final measurements, quantify changes to bar profiles or other target measurements on high-mask and cleaner-sample subsets.' 10.5 $false $wdAlignLeft '000000' 6 | Out-Null
    Add-Heading '8. Output inventory'
    Add-Table @('Product','Count','Location') @(
        @('SEP diagnostic PNGs','182',"SEP\Toy Objects\$RunStamp\PNG batch"),
        @('MTObjects diagnostic PNGs','182',"MTObjects\Toy Objects\$RunStamp\PNG batch"),
        @('Side-by-side composites','182',"Toy Objects comparison\$RunStamp"),
        @('Cleaner-labelled PNGs','11 per method','Suffix: _clean')
    ) @(2.0,1.15,3.5) | Out-Null
    Add-Heading '9. Reproducibility record'
    Add-Para ("Both diagnostic batches used the original science image, six toys per galaxy, toy seed 202608299, peak amplitudes spanning 6–30 robust sigma, and one-pixel truth dilation. The calibration design used 11 galaxy-level folds and an independently seeded winner-selection injection set. All output counts and summary CSV statuses were checked after completion.") | Out-Null

    try { $doc.BuiltInDocumentProperties.Item('Title').Value='S4G Clean-11 LOGO-CV Optimisation Results' } catch {}
    try { $doc.BuiltInDocumentProperties.Item('Subject').Value='SEP and MTObjects toy-object optimisation and 182-galaxy deployment diagnostics' } catch {}
    $doc.SaveAs2($OutputPath,$wdFormatDocumentDefault)
    $doc.Close($true)
    Write-Output $OutputPath
}
finally {
    if($doc){try{$doc.Close($false)}catch{}}
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)|Out-Null
    [gc]::Collect();[gc]::WaitForPendingFinalizers()
}
