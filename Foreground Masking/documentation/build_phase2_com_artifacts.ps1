param(
    [string]$OutputDir = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\documentation",
    [string]$QaDir = "C:\Users\gordo\Documents\Github\PythonScripts\Foreground Masking\documentation\phase2_com_qa",
    [switch]$SkipDocs
)

$ErrorActionPreference = "Stop"
$navy = 0x45250B
$blue = 0xB5742E
$lightBlue = 0xF5EEE8
$lightGray = 0xF7F4F2
$darkGray = 0x4B4B4B
$green = 0x4F7D2D
$red = 0x1C1C9B
$gold = 0x006A9A

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
New-Item -ItemType Directory -Force -Path $QaDir | Out-Null

function Set-WordStyles($doc) {
    $normal = $doc.Styles.Item("Normal")
    $normal.Font.Name = "Calibri"
    $normal.Font.Size = 11
    $normal.Font.Color = $darkGray
    $normal.ParagraphFormat.SpaceAfter = 6
    $normal.ParagraphFormat.LineSpacingRule = 5
    $normal.ParagraphFormat.LineSpacing = 13.2
    foreach ($spec in @(
        @{Name="Heading 1"; Size=16; Before=16; After=8; Color=$blue},
        @{Name="Heading 2"; Size=13; Before=12; After=6; Color=$blue},
        @{Name="Heading 3"; Size=12; Before=8; After=4; Color=$navy}
    )) {
        $s = $doc.Styles.Item($spec.Name)
        $s.Font.Name = "Calibri"
        $s.Font.Size = $spec.Size
        $s.Font.Bold = $true
        $s.Font.Color = $spec.Color
        $s.ParagraphFormat.SpaceBefore = $spec.Before
        $s.ParagraphFormat.SpaceAfter = $spec.After
        $s.ParagraphFormat.KeepWithNext = $true
    }
}

function Add-TitleBlock($doc, $title, $subtitle, $status) {
    $p = $doc.Paragraphs.Add()
    $p.Range.Text = "FOREGROUND MASKING RESEARCH"
    $p.Range.Font.Name = "Calibri"
    $p.Range.Font.Size = 10
    $p.Range.Font.Bold = $true
    $p.Range.Font.Color = $gold
    $p.Format.SpaceAfter = 7
    $p = $doc.Paragraphs.Add()
    $p.Range.Text = $title
    $p.Range.Font.Name = "Calibri"
    $p.Range.Font.Size = 25
    $p.Range.Font.Bold = $true
    $p.Range.Font.Color = $navy
    $p.Format.SpaceAfter = 5
    $p = $doc.Paragraphs.Add()
    $p.Range.Text = $subtitle
    $p.Range.Font.Size = 13
    $p.Range.Font.Color = $darkGray
    $p.Format.SpaceAfter = 12
    foreach ($line in @("Prepared: 20 August 2026", "Status: $status")) {
        $p = $doc.Paragraphs.Add()
        $p.Range.Text = $line
        $p.Range.Font.Size = 10
        $p.Format.SpaceAfter = 2
    }
    $p = $doc.Paragraphs.Add()
    $p.Range.Text = ""
    $p.Borders.Item(-3).LineStyle = 1
    $p.Borders.Item(-3).Color = $blue
    $p.Borders.Item(-3).LineWidth = 12
    $p.Format.SpaceAfter = 10
}

function Add-Heading($doc, $text, $level=1) {
    $p = $doc.Paragraphs.Add()
    $p.Range.Text = $text
    $p.Style = "Heading $level"
}

function Add-Para($doc, $text, [bool]$bold=$false) {
    $p = $doc.Paragraphs.Add()
    $p.Range.Text = $text
    $p.Range.Font.Bold = $bold
    $p.Range.Font.Name = "Calibri"
    $p.Range.Font.Size = 11
    $p.Format.SpaceAfter = 6
}

function Add-Bullets($doc, $items) {
    foreach ($item in $items) {
        $p = $doc.Paragraphs.Add()
        $p.Range.Text = $item
        $p.Range.ListFormat.ApplyBulletDefault()
        $p.Range.ParagraphFormat.LeftIndent = 36
        $p.Range.ParagraphFormat.FirstLineIndent = -18
        $p.Range.ParagraphFormat.SpaceAfter = 8
    }
}

function Add-Table($doc, $headers, $rows, $widths=$null) {
    $range = $doc.Range($doc.Content.End - 1, $doc.Content.End - 1)
    $table = $doc.Tables.Add($range, $rows.Count + 1, $headers.Count)
    $table.AllowAutoFit = $false
    $table.Borders.Enable = 1
    $table.Rows.Item(1).Range.Font.Bold = $true
    $table.Rows.Item(1).Shading.BackgroundPatternColor = $lightGray
    for ($c=1; $c -le $headers.Count; $c++) {
        $table.Cell(1,$c).Range.Text = [string]$headers[$c-1]
        if ($widths) { $table.Columns.Item($c).Width = $widths[$c-1] }
    }
    for ($r=0; $r -lt $rows.Count; $r++) {
        for ($c=0; $c -lt $headers.Count; $c++) {
            $table.Cell($r+2,$c+1).Range.Text = [string]$rows[$r][$c]
        }
    }
    $table.Range.Font.Name = "Calibri"
    $table.Range.Font.Size = 9.5
    $table.Range.ParagraphFormat.SpaceAfter = 2
    $doc.Range($doc.Content.End - 1, $doc.Content.End - 1).InsertParagraphAfter()
    return $table
}

function Add-Callout($doc, $label, $text, $color=$blue) {
    $table = Add-Table $doc @($label) @(,@($text)) @(468)
    $table.Rows.Item(1).Shading.BackgroundPatternColor = $color
    $table.Rows.Item(1).Range.Font.Color = 0xFFFFFF
    $table.Rows.Item(2).Shading.BackgroundPatternColor = $lightBlue
}

function Set-HeaderFooter($doc, $label) {
    foreach ($section in $doc.Sections) {
        $section.PageSetup.TopMargin = 72
        $section.PageSetup.BottomMargin = 72
        $section.PageSetup.LeftMargin = 72
        $section.PageSetup.RightMargin = 72
        $section.PageSetup.HeaderDistance = 35.4
        $section.PageSetup.FooterDistance = 35.4
        $h = $section.Headers.Item(1).Range
        $h.Text = $label
        $h.Font.Name = "Calibri"
        $h.Font.Size = 8.5
        $h.Font.Color = 0x777777
        $f = $section.Footers.Item(1).Range
        $f.Text = "Spike Gate Phase 2 | 20 August 2026"
        $f.Font.Name = "Calibri"
        $f.Font.Size = 8.5
        $f.Font.Color = 0x777777
        $f.ParagraphFormat.Alignment = 2
    }
}

function Save-Doc($word, $doc, $name) {
    Write-Host "Saving $name ..."
    $path = Join-Path $OutputDir $name
    $localPath = Join-Path $QaDir $name
    $pdf = Join-Path $QaDir ($name -replace '\.docx$', '.pdf')
    Set-HeaderFooter $doc ($name -replace '\.docx$', '')
    Write-Host "Header and footer complete for $name"
    $doc.SaveAs2($localPath, 16)
    $doc.ExportAsFixedFormat($pdf, 17)
    $doc.Close(0)
    Copy-Item -LiteralPath $localPath -Destination $path -Force
    Write-Host "Saved $name"
    return $path
}

function Build-Methodology($word) {
    Write-Host "Building methodology document ..."
    $doc = $word.Documents.Add()
    Set-WordStyles $doc
    Add-TitleBlock $doc "Spike Gate Phase 2 Methodology" "Component-constrained optimisation of SEP and MTObjects on science images" "Methodology record"
    Add-Callout $doc "Methodological principle" "Spike Gate supplies evidence from residual images; SEP and MTObjects segment only the original science images. Gate evidence selects credible connected components, but never becomes the science-image input."
    Add-Heading $doc "1. Purpose and rationale"
    Add-Para $doc "Earlier objective-only agreement could reward a large mask simply because it overlapped a Spike Gate target. Phase 2 changes the gate from a score-only term into an explicit connected-component selector. This makes recovery credit conditional on compact, gate-supported science-image segmentation."
    Add-Heading $doc "2. Processing architecture"
    Add-Bullets $doc @(
        "Generate the Spike Gate candidate evidence from the residual image.",
        "Run SEP or MTObjects on the original science image within documentation-supported parameter ranges.",
        "Label connected components in native science-image coordinates.",
        "Project each native label map once into the common deprojected diagnostic view.",
        "Retain only components that satisfy target intersection, support fraction and size constraints.",
        "Apply the accepted mask and replace masked bar-profile samples with a log-linear bridge for diagnostic profiles."
    )
    Add-Heading $doc "3. Component retention rules"
    Add-Table $doc @("Rule","Requirement","Purpose") @(
        @("Target intersection","Component intersects the compact gate target","Establishes direct candidate association"),
        @("Support fraction",">= 20% of projected component pixels fall inside permitted support","Rejects weak incidental overlap"),
        @("Maximum extent","Component occupies <= 8% of diagnostic view","Rejects galaxy-scale components"),
        @("Coordinate handling","Native labels projected once","Avoids repeated interpolation and denominator drift")
    ) @(105,120,243) | Out-Null
    Add-Heading $doc "4. Optimisation objective"
    Add-Para $doc "The scalar objective balances recovery with scientific protection. A zero or near-zero detection receives an explicit penalty only when credible gate candidates are present."
    Add-Bullets $doc @(
        "Gate target recovery and gate candidate detection rate.",
        "Supported-mask precision.",
        "Excess area outside permitted gate support.",
        "Protected galaxy loss and total native-image masked fraction.",
        "Non-gate bar-profile masking and bridge-span penalties.",
        "Zero-detection penalty for credible candidates."
    )
    Add-Heading $doc "5. Audit and release gate"
    Add-Para $doc "Fifteen gate-positive, high-risk galaxies formed a stress-test audit. Each algorithm used a short 24-trial search. Full four-fold or 182-galaxy execution was conditional on acceptable audit behaviour. MTO was permitted to proceed as a conservative diagnostic run; SEP was not."
    Add-Heading $doc "6. Implementation and reproducibility"
    Add-Table $doc @("Role","Implementation file") @(
        @("Objective and native component logic","Foreground Masking/Shared/spike_gate_objective.py"),
        @("Batch component filtering","Foreground Masking/Shared/spike_gate_component_filter.py"),
        @("SEP optimisation","Foreground Masking/Optimisation/optimise_spike_gate_SEP.py"),
        @("MTO optimisation","Foreground Masking/Optimisation/optimise_spike_gate_MTObjects.py"),
        @("Constrained audit","Foreground Masking/Optimisation/evaluate_constrained_spike_gate_batch.py"),
        @("Visible automation","Foreground Masking/Automation/run_phase2_spike_gate_audit_visible.ps1")
    ) @(150,318) | Out-Null
    Add-Heading $doc "7. Interpretation limits"
    Add-Para $doc "Low masked area demonstrates conservatism, not necessarily correct foreground recovery. Phase 2 is a profile-protection diagnostic and must not yet be described as a complete foreground-object catalogue. Candidate credibility and manually labelled validation remain essential."
    return Save-Doc $word $doc "Spike Gate Phase 2 Methodology.docx"
}

function Build-Results($word) {
    Write-Host "Building results document ..."
    $doc = $word.Documents.Add()
    Set-WordStyles $doc
    Add-TitleBlock $doc "Spike Gate Phase 2 Results" "Audit comparison and 182-galaxy MTObjects diagnostic batch" "Results and scientific interpretation"
    Add-Callout $doc "Executive conclusion" "Phase 2 removed the galaxy-scale overmasking failure mode. MTObjects is the stronger diagnostic candidate; SEP failed the stress-test audit and should not enter a production-style batch in its present configuration."
    Add-Heading $doc "1. Stress-test audit"
    Add-Table $doc @("Metric","SEP","MTObjects") @(
        @("Objective","153.6543; infeasible","57.8821; narrowly infeasible"),
        @("Mean gate recovery","11.1%","49.3%"),
        @("Candidate detection","11.7%","63.3%"),
        @("Supported precision","Not competitive","58.1%"),
        @("Zero detections","11/15","2/15"),
        @("Mean masked area","0.00258%","0.00500%"),
        @("Decision","Do not proceed","Proceed diagnostically")
    ) @(180,144,144) | Out-Null
    Add-Para $doc "The two MTO zero-detection cases were NGC4020 and NGC4532. The result remained narrowly outside provisional hard constraints, so the subsequent full run was explicitly diagnostic rather than production deployment."
    Add-Heading $doc "2. NGC3627 discrepancy resolved"
    Add-Bullets $doc @(
        "SEP: zero retained components, zero recovery and zero masking.",
        "MTO: three gate-supported components, recovery 1.0 and candidate detection 1.0.",
        "MTO masked 0.0146% of the native image while preserving spiral structure and isophotal alignment."
    )
    Add-Heading $doc "3. 182-galaxy MTO diagnostic batch"
    Add-Table $doc @("Measure","Result") @(
        @("Completion","182/182 successful; 0 failures"),
        @("Gate-positive","127"),
        @("Gate-negative","55; all left unmasked"),
        @("Gate-positive with accepted mask","97/127 (76.4%)"),
        @("Gate-positive with no accepted component","30/127 (23.6%)"),
        @("Overall non-zero masks","97/182"),
        @("Overall zero masks","85/182")
    ) @(230,238) | Out-Null
    Add-Heading $doc "4. Masked-area distribution"
    Add-Table $doc @("Statistic","Masked area") @(
        @("Mean","0.002778%"), @("Median","0.000685%"), @("75th percentile","0.003443%"),
        @("90th percentile","0.010300%"), @("95th percentile","0.013278%"), @("99th percentile","0.016678%"),
        @("Maximum","0.021179% - NGC6412")
    ) @(230,238) | Out-Null
    Add-Heading $doc "5. High-mask visual review"
    Add-Table $doc @("Galaxy","Masked area","Review") @(
        @("NGC6412","0.02118%","Two compact off-centre masks; galaxy structure preserved"),
        @("NGC1672","0.01946%","Four narrow profile-associated masks; isophotes stable"),
        @("NGC3627","0.01458%","Major improvement over earlier aggressive SEP result"),
        @("NGC5236","0.01428%","25 accepted from 11,537 raw segments; manual/performance flag")
    ) @(85,80,303) | Out-Null
    Add-Heading $doc "6. Scientific interpretation"
    Add-Bullets $doc @(
        "Phase 2 sharply reduces damage to coherent galaxy morphology.",
        "MTO is presently the stronger candidate for Spike Gate profile protection.",
        "Thirty gate-positive galaxies received no accepted mask, so recall remains incomplete.",
        "SEP remains excluded until its science-image segmentation reliably yields compact gate-associated components.",
        "The output is a conservative diagnostic, not a complete foreground catalogue."
    )
    Add-Para $doc "Batch output: D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\MTO\Spike Gate\20260819_202509"
    return Save-Doc $word $doc "Spike Gate Phase 2 Results.docx"
}

function Build-Improvements($word) {
    Write-Host "Building improvement-options document ..."
    $doc = $word.Documents.Add()
    Set-WordStyles $doc
    Add-TitleBlock $doc "Spike Gate Phase 2 Improvement Options" "Prioritised route from conservative diagnostic to validated masking workflow" "Recommendations and acceptance criteria"
    Add-Callout $doc "Recommended direction" "Retain MTObjects Phase 2 as the diagnostic baseline. Improve gate credibility and candidate matching first, then add local recovery only for credible unmatched candidates. Do not broaden the global mask to recover misses."
    Add-Heading $doc "1. Prioritised improvements"
    $options = @(
        @("1","Gate credibility model","Score amplitude, side-drop, width, residual compactness, multi-width persistence and 2-D residual agreement."),
        @("2","Native-coordinate target/support","Use one traceable coordinate system and conserved denominators for recovery, precision and protected loss."),
        @("3","Candidate-specific association","Report matched, unmatched, split and merged candidates; optimise candidate-level recall and precision."),
        @("4","Morphology protection","Penalise annular coherence, large azimuthal span, tangential arm-like elongation and low-frequency galaxy overlap."),
        @("5","Two-stage local recovery","For credible misses only, search a small native window under tighter area and morphology caps."),
        @("6","Manual labelled validation","Label 20-30 galaxies, including NGC4020, NGC4532, NGC5236 and high-discrepancy cases."),
        @("7","Stratified cross-validation","Balance folds by scale, inclination, morphology, gate count and foreground density; report uncertainty and stability."),
        @("8","Runtime controls","Cap raw components, enforce time/memory limits and checkpoint/resume; NGC5236 required 4m17s and 11,537 segments.")
    )
    Add-Table $doc @("Priority","Option","Implementation intent") $options @(45,120,303) | Out-Null
    Add-Heading $doc "2. Proposed staged programme"
    Add-Bullets $doc @(
        "Stage A - build gate credibility labels and candidate-level matching diagnostics.",
        "Stage B - implement morphology-protection terms and native-coordinate accounting.",
        "Stage C - run stratified four-fold optimisation on the labelled subset.",
        "Stage D - introduce local recovery for credible unmatched gates and re-audit misses.",
        "Stage E - approve a new 182-galaxy batch only if quantitative and visual release criteria pass."
    )
    Add-Heading $doc "3. Acceptance criteria for the next iteration"
    Add-Table $doc @("Criterion","Threshold") @(
        @("Mean credible-candidate recovery",">= 0.70"),
        @("Candidate detection",">= 0.75"),
        @("High-credibility zero detections","None unexplained"),
        @("Mean protected galaxy loss","<= 0.01"),
        @("Mean / maximum native masked fraction","<= 0.02 / <= 0.05"),
        @("Coherent structure removal","None confirmed in labelled audit"),
        @("Cross-fold behaviour","Stable across four stratified folds")
    ) @(300,168) | Out-Null
    Add-Heading $doc "4. Decision rule"
    Add-Para $doc "Advance to production-style use only when candidate recovery improves without exceeding morphology-protection and area limits. If local recovery increases galaxy loss, retain the conservative baseline and route uncertain cases to manual review."
    return Save-Doc $word $doc "Spike Gate Phase 2 Improvement Options.docx"
}

function Add-PptText($slide, $text, $left, $top, $width, $height, $size=22, $bold=$false, $color=0x333333, $align=1) {
    $shape = $slide.Shapes.AddTextbox(1,$left,$top,$width,$height)
    $shape.TextFrame.TextRange.Text = $text
    $shape.TextFrame.TextRange.Font.Name = "Aptos"
    $shape.TextFrame.TextRange.Font.Size = $size
    $shape.TextFrame.TextRange.Font.Bold = [int]$bold
    $shape.TextFrame.TextRange.Font.Color.RGB = $color
    $shape.TextFrame.TextRange.ParagraphFormat.Alignment = $align
    $shape.TextFrame.MarginLeft = 3; $shape.TextFrame.MarginRight = 3
    $shape.TextFrame.MarginTop = 2; $shape.TextFrame.MarginBottom = 2
    return $shape
}

function Add-PptTitle($slide, $title, $number) {
    Add-PptText $slide $title 48 30 840 55 35 $true $navy | Out-Null
    Add-PptText $slide ("{0:D2}" -f $number) 900 34 35 28 13 $true $blue 3 | Out-Null
    $line = $slide.Shapes.AddLine(48,92,912,92)
    $line.Line.ForeColor.RGB = $blue
    $line.Line.Weight = 1.5
}

function Add-Metric($slide,$value,$label,$left,$top,$width) {
    Add-PptText $slide $value $left $top $width 55 31 $true $blue 2 | Out-Null
    Add-PptText $slide $label $left ($top+54) $width 46 17 $false $darkGray 2 | Out-Null
}

function Build-Presentation($ppt) {
    Write-Host "Building PowerPoint deck ..."
    $pres = $ppt.Presentations.Add()
    $pres.PageSetup.SlideWidth = 960
    $pres.PageSetup.SlideHeight = 540
    $blank = 12
    $s = $pres.Slides.Add(1,$blank)
    $bg = $s.Background.Fill; $bg.ForeColor.RGB = 0xFAF9F7; $bg.Solid()
    Add-PptText $s "FOREGROUND MASKING RESEARCH" 60 70 840 32 17 $true $gold 2 | Out-Null
    Add-PptText $s "Spike Gate Phase 2" 60 150 840 70 48 $true $navy 2 | Out-Null
    Add-PptText $s "Conservative foreground masking with connected-component gate support" 110 232 740 60 24 $false $darkGray 2 | Out-Null
    Add-PptText $s "SEP audit | MTObjects audit | 182-galaxy diagnostic run" 160 340 640 35 18 $true $blue 2 | Out-Null
    Add-PptText $s "20 August 2026" 360 440 240 25 15 $false 0x777777 2 | Out-Null

    $s = $pres.Slides.Add(2,$blank); Add-PptTitle $s "Why Phase 2 was necessary" 2
    Add-PptText $s "Objective-only agreement could reward a galaxy-scale mask simply because it overlapped a Spike Gate target." 70 130 820 80 27 $true $navy 2 | Out-Null
    Add-PptText $s "The consequence" 90 260 220 35 21 $true $red 2 | Out-Null
    Add-PptText $s "High apparent recovery`nwithout scientifically safe masking" 70 305 260 80 19 $false $darkGray 2 | Out-Null
    Add-PptText $s "Phase 2 correction" 370 260 220 35 21 $true $green 2 | Out-Null
    Add-PptText $s "Recovery credit only for compact,`ngate-supported connected components" 350 305 260 80 19 $false $darkGray 2 | Out-Null
    Add-PptText $s "Release gate" 650 260 220 35 21 $true $blue 2 | Out-Null
    Add-PptText $s "Audit first; run 182 galaxies only`nwhen component behaviour is credible" 630 305 260 80 19 $false $darkGray 2 | Out-Null

    $s = $pres.Slides.Add(3,$blank); Add-PptTitle $s "Residual evidence; science-image segmentation" 3
    $steps = @(
        @("1","Residual image","Spike Gate candidates"), @("2","Science image","SEP or MTObjects"),
        @("3","Native components","Target + support + size rules"), @("4","Final mask","Log-linear profile bridge")
    )
    for ($i=0;$i -lt 4;$i++) {
        $x = 52 + 225*$i
        Add-PptText $s $steps[$i][0] $x 145 50 45 28 $true $blue 2 | Out-Null
        Add-PptText $s $steps[$i][1] ($x+45) 138 150 36 21 $true $navy 1 | Out-Null
        Add-PptText $s $steps[$i][2] ($x+45) 180 150 60 17 $false $darkGray 1 | Out-Null
        if ($i -lt 3) { Add-PptText $s ">" ($x+195) 160 25 35 25 $true $gold 2 | Out-Null }
    }
    Add-PptText $s "Retention rules" 80 300 180 35 23 $true $navy | Out-Null
    Add-PptText $s "Intersects compact target`n>=20% inside permitted support`n<=8% of diagnostic view" 80 345 300 100 19 $false $darkGray | Out-Null
    Add-PptText $s "Protection terms" 530 300 180 35 23 $true $navy | Out-Null
    Add-PptText $s "Excess-area penalty`nProtected galaxy loss`nZero-detection penalty for credible gates" 530 345 340 100 19 $false $darkGray | Out-Null

    $s = $pres.Slides.Add(4,$blank); Add-PptTitle $s "MTObjects outperforms SEP in the stress test" 4
    Add-Metric $s "11.1%" "SEP mean gate recovery" 65 135 190
    Add-Metric $s "49.3%" "MTO mean gate recovery" 285 135 190
    Add-Metric $s "11/15" "SEP zero detections" 505 135 190
    Add-Metric $s "2/15" "MTO zero detections" 725 135 170
    Add-PptText $s "SEP" 90 300 120 35 25 $true $red 2 | Out-Null
    Add-PptText $s "Infeasible; earlier apparent recovery was largely driven by galaxy-scale components. Do not proceed." 60 345 360 100 19 $false $darkGray 2 | Out-Null
    Add-PptText $s "MTObjects" 600 300 180 35 25 $true $green 2 | Out-Null
    Add-PptText $s "Narrowly infeasible, but compact component behaviour justified a conservative diagnostic batch." 540 345 360 100 19 $false $darkGray 2 | Out-Null

    $s = $pres.Slides.Add(5,$blank); Add-PptTitle $s "NGC3627: compact masks preserve structure" 5
    $img = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\MTO\Spike Gate\20260819_202509\NGC3627_mtobjects_optimised_report_clean.png"
    if (Test-Path -LiteralPath $img) { $s.Shapes.AddPicture($img,0,-1,55,112,560,398) | Out-Null }
    Add-PptText $s "MTO Phase 2" 650 145 240 35 25 $true $green 2 | Out-Null
    Add-PptText $s "3 gate-supported components`n100% gate recovery`n100% candidate detection`n0.0146% masked area" 650 205 240 140 22 $false $darkGray 2 | Out-Null
    Add-PptText $s "Spiral structure and isophotal alignment are preserved." 640 385 260 70 20 $true $navy 2 | Out-Null

    $s = $pres.Slides.Add(6,$blank); Add-PptTitle $s "182-galaxy MTO diagnostic run" 6
    Add-Metric $s "182/182" "successful; zero failures" 70 130 200
    Add-Metric $s "127" "gate-positive galaxies" 290 130 180
    Add-Metric $s "97" "accepted non-zero masks" 500 130 180
    Add-Metric $s "55/55" "gate-negative left unmasked" 710 130 190
    Add-PptText $s "Masked-area distribution" 80 300 300 35 23 $true $navy | Out-Null
    Add-PptText $s "Mean 0.002778%`nMedian 0.000685%`n95th percentile 0.013278%`nMaximum 0.021179% (NGC6412)" 80 345 330 125 19 $false $darkGray | Out-Null
    Add-PptText $s "Interpretation" 560 300 220 35 23 $true $navy | Out-Null
    Add-PptText $s "Very low mask area confirms conservatism.`nIt does not, by itself, prove correct recovery." 520 345 350 90 21 $true $blue 2 | Out-Null

    $s = $pres.Slides.Add(7,$blank); Add-PptTitle $s "Limitations that still matter" 7
    Add-PptText $s "30/127" 70 145 210 60 37 $true $red 2 | Out-Null
    Add-PptText $s "gate-positive galaxies had no accepted component" 55 210 240 65 19 $false $darkGray 2 | Out-Null
    Add-PptText $s "NGC5236" 370 145 220 60 29 $true $gold 2 | Out-Null
    Add-PptText $s "11,537 raw segments`n4m17s runtime`nmanual and performance flag" 360 210 240 90 19 $false $darkGray 2 | Out-Null
    Add-PptText $s "Not a catalogue" 680 145 220 60 29 $true $navy 2 | Out-Null
    Add-PptText $s "Phase 2 protects bar-profile analysis; it is not yet a complete foreground-object inventory." 660 210 250 90 19 $false $darkGray 2 | Out-Null
    Add-PptText $s "Low area is a safety signal. Candidate-level validation is the missing correctness signal." 120 385 720 65 25 $true $blue 2 | Out-Null

    $s = $pres.Slides.Add(8,$blank); Add-PptTitle $s "Improve recall locally, not globally" 8
    Add-PptText $s "Retain MTO Phase 2 as the conservative diagnostic baseline." 70 125 820 45 28 $true $navy 2 | Out-Null
    Add-PptText $s "1" 90 225 45 40 26 $true $blue 2 | Out-Null
    Add-PptText $s "Score gate credibility and match candidates explicitly" 145 220 700 42 21 $true $darkGray | Out-Null
    Add-PptText $s "2" 90 290 45 40 26 $true $blue 2 | Out-Null
    Add-PptText $s "Add native-coordinate accounting and morphology protection" 145 285 700 42 21 $true $darkGray | Out-Null
    Add-PptText $s "3" 90 355 45 40 26 $true $blue 2 | Out-Null
    Add-PptText $s "Recover only credible misses with a tightly constrained local search" 145 350 700 42 21 $true $darkGray | Out-Null
    Add-PptText $s "Release target: >=70% credible-candidate recovery, >=75% detection, no coherent galaxy-structure loss." 100 445 760 45 20 $true $green 2 | Out-Null

    $path = Join-Path $OutputDir "Spike Gate Phase 2 Results Summary.pptx"
    $localPath = Join-Path $QaDir "Spike Gate Phase 2 Results Summary.pptx"
    $pres.SaveAs($localPath,24)
    $slidesDir = Join-Path $QaDir "slides"
    New-Item -ItemType Directory -Force -Path $slidesDir | Out-Null
    $pres.Export($slidesDir,"PNG",1920,1080)
    $pres.Close()
    Copy-Item -LiteralPath $localPath -Destination $path -Force
    Write-Host "Saved PowerPoint deck"
    return $path
}

$word = $null; $ppt = $null
try {
    $outputs = @()
    if (-not $SkipDocs) {
        $word = New-Object -ComObject Word.Application
        $word.Visible = $false
        $word.DisplayAlerts = 0
        $word.ScreenUpdating = $false
        $outputs += Build-Methodology $word
        $outputs += Build-Results $word
        $outputs += Build-Improvements $word
        $word.Quit()
        [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) | Out-Null
        $word = $null
    }
    $ppt = New-Object -ComObject PowerPoint.Application
    $ppt.Visible = -1
    $outputs += Build-Presentation $ppt
    $ppt.Quit()
    [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($ppt) | Out-Null
    $ppt = $null
    Write-Output "CREATED"
    $outputs | ForEach-Object { Write-Output $_ }
} finally {
    if ($word) { try { $word.Quit() } catch {}; [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) | Out-Null }
    if ($ppt) { try { $ppt.Quit() } catch {}; [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($ppt) | Out-Null }
}
