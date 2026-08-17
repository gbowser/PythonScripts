$ErrorActionPreference = 'Stop'

$outDir = 'C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\Documentation\comparison_presentation'
$pptx = Join-Path $outDir 'SEP and MTObjects Masking Recommendations 20260816.pptx'
$renderDir = Join-Path $outDir 'rendered'
$sepImage = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\SEP all galaxy batch\sep_toy_cv_20260816_185737\NGC1313_sep_thr1.9_area14_deb0.0030_dil6.png'
$mtoImage = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\mtobjects all galaxy batch\mtobjects_toy_recovery_20260816_063455_eight_panel_aligned\NGC1313_mtobjects_optimised_report.png'
New-Item -ItemType Directory -Path $outDir,$renderDir -Force | Out-Null

$pp = New-Object -ComObject PowerPoint.Application
$pp.Visible = -1
$deck = $pp.Presentations.Add()
$deck.PageSetup.SlideWidth = 1280
$deck.PageSetup.SlideHeight = 720

$ink = 0x000000
$muted = 0x666666
$blue = 0xFF8D3D
$lightBlue = 0xF4CB6D
$panel = 0xEDEDED
$white = 0xFFFFFF
$amber = 0xD99E29
$brown = 0x7A5200
$red = 0x3B35B8

function Add-Text($slide, $text, $x, $y, $w, $h, $size, $bold=$false, $color=$ink, $font='Arial') {
    $s = $slide.Shapes.AddTextbox(1, $x, $y, $w, $h)
    $s.TextFrame.TextRange.Text = $text
    $s.TextFrame.TextRange.Font.Name = $font
    $s.TextFrame.TextRange.Font.Size = $size
    $s.TextFrame.TextRange.Font.Bold = [int]$bold
    $s.TextFrame.TextRange.Font.Color.RGB = $color
    $s.TextFrame.MarginLeft = 0; $s.TextFrame.MarginRight = 0
    $s.TextFrame.MarginTop = 0; $s.TextFrame.MarginBottom = 0
    $s.TextFrame.WordWrap = -1
    return $s
}
function Add-Rect($slide, $x, $y, $w, $h, $fill, $line=$fill) {
    $s = $slide.Shapes.AddShape(1, $x, $y, $w, $h)
    $s.Fill.ForeColor.RGB = $fill
    $s.Line.ForeColor.RGB = $line
    return $s
}
function Add-Title($slide, $title, $number) {
    Add-Text $slide $title 64 46 1120 54 36 $true $ink | Out-Null
    Add-Text $slide ("{0:00}" -f $number) 1188 52 40 25 14 $true $muted | Out-Null
    $r = $slide.Shapes.AddLine(64, 112, 1216, 112); $r.Line.ForeColor.RGB = 0xB8BCB4; $r.Line.Weight = 1
}
function Add-Footer($slide) {
    Add-Text $slide 'MSc Research | Toy-object foreground masking | 16 August 2026' 64 684 780 18 11 $false $muted | Out-Null
}
function Add-Notes($slide, $sourceText) {
    try {
        $body = $slide.NotesPage.Shapes.Placeholders.Item(2)
        $body.TextFrame.TextRange.Text = "[Sources]`r`n$sourceText"
    } catch {}
}
function Add-BulletList($slide, $items, $x, $y, $w, $h, $size=22, $color=$ink) {
    $s = Add-Text $slide ($items -join "`r") $x $y $w $h $size $false $color
    $r = $s.TextFrame.TextRange
    for ($i=1; $i -le $items.Count; $i++) {
        $p = $r.Paragraphs($i)
        $p.ParagraphFormat.Bullet.Visible = -1
        $p.ParagraphFormat.SpaceAfter = 12
    }
    return $s
}
function Add-MetricBar($slide, $label, $value, $max, $x, $y, $w, $color) {
    Add-Text $slide $label $x $y 215 28 18 $true $ink | Out-Null
    Add-Rect $slide ($x+220) ($y+2) $w 22 $panel | Out-Null
    Add-Rect $slide ($x+220) ($y+2) ($w*$value/$max) 22 $color | Out-Null
    Add-Text $slide (("{0:N1}%" -f $value)) ($x+230+$w) $y 85 28 18 $true $ink | Out-Null
}

# 1 - title
$s = $deck.Slides.Add(1, 12)
Add-Text $s 'MASKING DECISION' 72 68 420 28 18 $true $blue | Out-Null
Add-Text $s 'SEP or MTObjects?' 72 190 820 76 58 $true $ink | Out-Null
Add-Text $s 'Evidence from four-fold toy-object optimisation and 182-galaxy production runs' 72 286 860 78 27 $false $muted | Out-Null
Add-Rect $s 72 410 1136 4 $blue | Out-Null
Add-Text $s 'Recommendation: combine both methods with explicit scientific safety gates.' 72 450 980 64 28 $true $ink | Out-Null
Add-Text $s 'Decision briefing | 16 August 2026' 72 624 600 25 16 $false $muted | Out-Null
Add-Notes $s 'Project SEP and MTObjects optimisation outputs; comparison report dated 16 August 2026.'

# 2 - decision
$s = $deck.Slides.Add(2, 12); Add-Title $s 'The evidence supports a gated two-algorithm workflow' 2
Add-Text $s 'USE TOGETHER' 64 150 260 28 18 $true $blue | Out-Null
Add-Text $s 'SEP finds more toys.' 64 198 500 54 34 $true $ink | Out-Null
Add-Text $s 'MTObjects is less likely to over-mask galaxy structure.' 64 270 500 84 26 $false $muted | Out-Null
Add-Rect $s 630 152 2 420 $panel | Out-Null
Add-Text $s 'Operating rule' 684 150 440 32 22 $true $ink | Out-Null
Add-BulletList $s @('Accept components found by both methods','Screen SEP-only components by size, shape and position','Quarantine masks above 15% or with profile damage','Fall back to MTObjects or a conservative SEP rerun') 684 204 470 300 22 | Out-Null
Add-Rect $s 684 525 470 64 0xE1F3E8 0xE1F3E8 | Out-Null
Add-Text $s 'One unattended method: MTObjects' 704 542 430 30 22 $true $ink | Out-Null
Add-Footer $s; Add-Notes $s 'Project comparison report, sections 4–5.'

# 3 - experiment
$s = $deck.Slides.Add(3, 12); Add-Title $s 'The comparison separates recovery from production risk' 3
$x0=78; $gap=35; $bw=250
foreach ($i in 0..3) {
    $x=$x0+$i*($bw+$gap)
    Add-Rect $s $x 185 $bw 210 $(if($i -eq 3){0xD0EDFA}else{$panel}) | Out-Null
    Add-Text $s ("FOLD {0}" -f ($i+1)) ($x+20) 205 170 26 17 $true $blue | Out-Null
    Add-Text $s '30 train' ($x+20) 260 190 40 29 $true $ink | Out-Null
    Add-Text $s '10 held out' ($x+20) 307 190 36 23 $false $muted | Out-Null
    Add-Text $s '40 common-set check' ($x+20) 350 210 26 17 $false $muted | Out-Null
}
Add-Text $s 'Then: selected model to all 182 galaxies, producing aligned eight-panel PNG reports' 78 446 1070 44 28 $true $ink | Out-Null
Add-Text $s 'Caveat: the SEP and MTObjects runs used different toy-injection seeds and different scalar objectives. Compare shared recovery and masking metrics, not raw objective scores.' 78 524 1080 78 19 $false $muted | Out-Null
Add-Footer $s; Add-Notes $s 'SEP CV run 20260816_185737; MTObjects recovery run 20260816_063455.'

# 4 - CV evidence
$s = $deck.Slides.Add(4, 12); Add-Title $s 'SEP recovered more injected contaminants across held-out folds' 4
Add-Text $s 'Four-fold held-out mean' 76 140 360 28 20 $true $muted | Out-Null
Add-MetricBar $s 'Toy recall | SEP' 57.3 65 76 205 470 $blue
Add-MetricBar $s 'Toy recall | MTO' 47.6 65 76 255 470 $brown
Add-MetricBar $s 'Toy detection | SEP' 57.9 65 76 335 470 $blue
Add-MetricBar $s 'Toy detection | MTO' 50.4 65 76 385 470 $brown
Add-MetricBar $s 'Masked area | SEP' 6.6 15 76 485 470 $blue
Add-MetricBar $s 'Masked area | MTO' 7.5 15 76 535 470 $brown
Add-Rect $s 895 185 285 290 0xF7F7F7 | Out-Null
Add-Text $s '+9.7 pp' 925 222 220 54 38 $true $blue | Out-Null
Add-Text $s 'SEP toy-recall advantage' 925 280 210 56 18 $false $muted | Out-Null
Add-Text $s '+7.5 pp' 925 355 220 54 38 $true $blue | Out-Null
Add-Text $s 'SEP toy-detection advantage' 925 413 220 56 18 $false $muted | Out-Null
Add-Footer $s; Add-Notes $s 'Held-out means calculated from four-fold SEP and MTObjects result summaries.'

# 5 - production risk
$s = $deck.Slides.Add(5, 12); Add-Title $s 'Production behaviour reverses the safety ranking' 5
Add-Text $s 'Masked image area across 182 galaxies' 76 140 500 30 20 $true $muted | Out-Null
Add-MetricBar $s 'Mean | SEP' 11.7 45 76 205 520 $blue
Add-MetricBar $s 'Mean | MTO' 8.9 45 76 255 520 $brown
Add-MetricBar $s '95th percentile | SEP' 20.0 45 76 335 520 $blue
Add-MetricBar $s '95th percentile | MTO' 12.7 45 76 385 520 $brown
Add-MetricBar $s 'Maximum | SEP' 42.0 45 76 465 520 $blue
Add-MetricBar $s 'Maximum | MTO' 19.0 45 76 515 520 $brown
Add-Text $s '30' 980 210 150 52 40 $true $red | Out-Null
Add-Text $s 'SEP galaxies above 15%' 980 263 190 52 18 $false $muted | Out-Null
Add-Text $s '1' 980 386 150 52 40 $true $brown | Out-Null
Add-Text $s 'MTObjects galaxy above 15%' 980 439 190 52 18 $false $muted | Out-Null
Add-Footer $s; Add-Notes $s 'SEP and MTObjects 182-galaxy apply-summary CSV files.'

# 6 - visual evidence
$s = $deck.Slides.Add(6, 12); Add-Title $s 'NGC1313 illustrates why recovery needs a safety gate' 6
Add-Text $s 'SEP | 42.0% masked' 68 132 540 30 22 $true $blue | Out-Null
Add-Text $s 'MTObjects | 19.0% masked' 672 132 540 30 22 $true $brown | Out-Null
$s.Shapes.AddPicture($sepImage, 0, -1, 68, 174, 540, 405) | Out-Null
$s.Shapes.AddPicture($mtoImage, 0, -1, 672, 174, 540, 405) | Out-Null
Add-Text $s 'Use the mask, recovered-image outlines, isophotes and bar-major profiles together, not masked fraction alone.' 68 608 1120 48 20 $true $ink | Out-Null
Add-Footer $s; Add-Notes $s "User-generated PNG reports: $sepImage ; $mtoImage"

# 7 - choice
$s = $deck.Slides.Add(7, 12); Add-Title $s 'Choose the operating mode before choosing the algorithm' 7
Add-Text $s 'UNATTENDED SCIENTIFIC BATCH' 72 160 500 28 18 $true $brown | Out-Null
Add-Text $s 'Use MTObjects' 72 207 500 48 34 $true $ink | Out-Null
Add-BulletList $s @('Lower mean and tail masking','Only one result above the 15% review gate','Safer default for preserving galaxy structure') 72 280 500 200 22 | Out-Null
Add-Rect $s 630 158 2 400 $panel | Out-Null
Add-Text $s 'RECOVERY-FIRST + HUMAN REVIEW' 686 160 500 28 18 $true $blue | Out-Null
Add-Text $s 'Use gated SEP' 686 207 500 48 34 $true $ink | Out-Null
Add-BulletList $s @('Higher toy recall and detection','Review every mask above 15%','Reject obvious isophote or bar-profile damage') 686 280 500 200 22 | Out-Null
Add-Text $s 'Best overall: retain both component maps and accept agreement automatically.' 72 586 1100 42 25 $true $ink | Out-Null
Add-Footer $s; Add-Notes $s 'Project comparison report, decision and operating recommendation.'

# 8 - objective
$s = $deck.Slides.Add(8, 12); Add-Title $s 'Optimise recovery and scientific safety as separate goals' 8
$items=@(
    @('Hard constraints','Reject >15% masks, low detection, or profile-damage failures.'),
    @('Tail-risk loss','Penalise the worst 10% of galaxies, not only the mean.'),
    @('Component metrics','Reward per-toy recovery; penalise false components and area separately.'),
    @('Profile preservation','Add isophote, centre-gradient and bar-major-profile distortion.'),
    @('Repeated seeds','Optimise median recovery plus lower-tail performance over several injections.'),
    @('Pareto selection','Keep recovery, false masking and profile damage as visible objectives.')
)
for($i=0;$i -lt $items.Count;$i++){
    $col=$i%2; $row=[math]::Floor($i/2); $x=72+$col*596; $y=150+$row*158
    Add-Text $s $items[$i][0] $x $y 510 30 23 $true $(if($col -eq 0){$blue}else{$brown}) | Out-Null
    Add-Text $s $items[$i][1] $x ($y+42) 500 76 18 $false $ink | Out-Null
}
Add-Footer $s; Add-Notes $s 'Recommendations derived from observed cross-validation and production-tail behaviour.'

# 9 - close
$s = $deck.Slides.Add(9, 12); Add-Title $s 'Build a robust masking pipeline in six steps' 9
$steps=@('Review the 30 SEP reports above 15%','Save labelled components from both algorithms','Implement agreement and SEP-only screening rules','Add masked-area and profile-damage release gates','Re-optimise with repeated seeds and tail-risk loss','Benchmark Photutils as an independent third method')
for($i=0;$i -lt $steps.Count;$i++){
    $y=146+$i*78
    Add-Text $s ("{0}" -f ($i+1)) 78 ($y-2) 44 44 28 $true $(if($i -lt 3){$blue}else{$brown}) | Out-Null
    Add-Text $s $steps[$i] 146 $y 960 42 23 $(if($i -eq 0){$true}else{$false}) $ink | Out-Null
}
Add-Rect $s 1115 146 5 432 $panel | Out-Null
Add-Text $s 'Decision' 72 620 130 26 18 $true $muted | Out-Null
Add-Text $s 'Approve gated ensemble development; use MTObjects until the gates are validated.' 212 615 980 38 24 $true $ink | Out-Null
Add-Footer $s; Add-Notes $s 'Photutils SourceFinder: https://photutils.readthedocs.io/en/stable/api/photutils.segmentation.SourceFinder.html'

$deck.SaveAs($pptx, 24)
$deck.Export($renderDir, 'PNG', 1600, 900)
$deck.Close(); $pp.Quit()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($deck) | Out-Null
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($pp) | Out-Null
Write-Output $pptx
