param(
    [string]$OutputPath = (Join-Path $PSScriptRoot 'S4G LOGO-CV Toy Objects Methodology - 11 Cleaner Galaxies.docx')
)

$ErrorActionPreference = 'Stop'

$wdAlignParagraphLeft = 0
$wdAlignParagraphCenter = 1
$wdAlignParagraphRight = 2
$wdAlignParagraphJustify = 3
$wdCollapseEnd = 0
$wdPageBreak = 7
$wdSectionBreakNextPage = 2
$wdStyleNormal = -1
$wdStyleTitle = -63
$wdStyleSubtitle = -75
$wdStyleHeading1 = -2
$wdStyleHeading2 = -3
$wdStyleHeading3 = -4
$wdStyleListBullet = -49
$wdStyleListNumber = -50
$wdStyleCaption = -35
$wdFormatDocumentDefault = 16
$wdFieldPage = 33
$wdFieldNumPages = 26
$wdAutoFitFixed = 0
$wdCellAlignVerticalCenter = 1
$wdLineSpaceMultiple = 5
$wdBorderBottom = -3
$wdBorderTop = -1
$wdColorAutomatic = -16777216

function Color([int]$r, [int]$g, [int]$b) { return $r + 256 * $g + 65536 * $b }
$Navy = Color 31 77 120
$Blue = Color 46 116 181
$Ink = Color 32 55 72
$Muted = Color 95 99 104
$LightBlue = Color 232 238 245
$LightGray = Color 242 244 247
$PaleGold = Color 255 248 232
$Gold = Color 122 90 0
$White = Color 255 255 255
$Black = Color 0 0 0

function Set-ParagraphFormat($paragraph, [double]$before, [double]$after, [double]$line = 1.1) {
    $paragraph.Format.SpaceBefore = $before
    $paragraph.Format.SpaceAfter = $after
    $paragraph.Format.LineSpacingRule = $wdLineSpaceMultiple
    $paragraph.Format.LineSpacing = 12 * $line
    $paragraph.Format.WidowControl = -1
}

function Add-Paragraph($doc, [string]$text, [object]$style = $wdStyleNormal, [int]$align = $wdAlignParagraphLeft) {
    $p = $doc.Paragraphs.Add()
    $p.Range.Text = $text
    $p.Range.Style = $style
    $p.Alignment = $align
    Set-ParagraphFormat $p 0 6 1.1
    $p.Range.InsertParagraphAfter()
    return $p
}

function Add-Body($doc, [string]$text) {
    $p = Add-Paragraph $doc $text $wdStyleNormal $wdAlignParagraphJustify
    return $p
}

function Add-Bullet($doc, [string]$text) {
    $p = Add-Paragraph $doc $text $wdStyleListBullet $wdAlignParagraphLeft
    Set-ParagraphFormat $p 0 5 1.12
    return $p
}

function Add-Numbered($doc, [string]$text) {
    $p = Add-Paragraph $doc $text $wdStyleListNumber $wdAlignParagraphLeft
    Set-ParagraphFormat $p 0 6 1.12
    return $p
}

function Set-Cell($cell, [string]$text, [bool]$header = $false, [int]$fill = -1, [int]$align = $wdAlignParagraphLeft) {
    $cell.Range.Text = $text
    $cell.VerticalAlignment = $wdCellAlignVerticalCenter
    $cell.Range.ParagraphFormat.Alignment = $align
    $cell.Range.ParagraphFormat.SpaceBefore = 2
    $cell.Range.ParagraphFormat.SpaceAfter = 2
    $cell.Range.Font.Name = 'Calibri'
    $cell.Range.Font.Size = 9.5
    if ($header) { $cell.Range.Font.Bold = -1 } else { $cell.Range.Font.Bold = 0 }
    if ($fill -ge 0) { $cell.Shading.BackgroundPatternColor = $fill }
}

function Add-Table($doc, [object[]]$rows, [double[]]$widths, [bool]$headerRow = $true) {
    $range = $doc.Content
    $range.Collapse($wdCollapseEnd)
    $table = $doc.Tables.Add($range, $rows.Count, $rows[0].Count)
    Write-Host "Creating table: requested=$($rows.Count)x$($rows[0].Count), actual=$($table.Rows.Count)x$($table.Columns.Count), widths=$($widths.Count)"
    $table.AllowAutoFit = 0
    $table.AutoFitBehavior($wdAutoFitFixed)
    $table.Borders.Enable = 1
    $table.Range.Font.Name = 'Calibri'
    $table.Range.Font.Size = 9.5
    for ($c = 1; $c -le $widths.Count; $c++) { $table.Columns.Item($c).Width = $widths[$c - 1] }
    for ($r = 1; $r -le $rows.Count; $r++) {
        for ($c = 1; $c -le $rows[$r - 1].Count; $c++) {
            $isHeader = $headerRow -and $r -eq 1
            $fill = if ($isHeader) { $LightBlue } elseif ($r % 2 -eq 0) { $LightGray } else { $White }
            Set-Cell $table.Cell($r, $c) ([string]$rows[$r - 1][$c - 1]) $isHeader $fill
        }
    }
    if ($headerRow) { $table.Rows.Item(1).HeadingFormat = -1 }
    $after = $table.Range
    $after.Collapse($wdCollapseEnd)
    $after.InsertParagraphAfter()
    return $table
}

function Add-Callout($doc, [string]$label, [string]$text, [int]$fill = $PaleGold) {
    $range = $doc.Content
    $range.Collapse($wdCollapseEnd)
    $table = $doc.Tables.Add($range, 1, 1)
    $table.AllowAutoFit = 0
    $table.Columns.Item(1).Width = 468
    $table.Rows.Item(1).AllowBreakAcrossPages = 0
    $table.Borders.Enable = 1
    $table.Borders.InsideLineStyle = 0
    $cell = $table.Cell(1, 1)
    $cell.Range.Style = $wdStyleNormal
    $cell.Shading.BackgroundPatternColor = $fill
    $cell.VerticalAlignment = $wdCellAlignVerticalCenter
    $cell.Range.Text = "$label`r$text"
    $cell.Range.Paragraphs.Item(1).Range.Font.Bold = -1
    $cell.Range.Paragraphs.Item(1).Range.Font.Color = $Navy
    $cell.Range.Font.Name = 'Calibri'
    $cell.Range.Font.Size = 10.5
    $cell.Range.ParagraphFormat.SpaceAfter = 4
    $after = $table.Range
    $after.Collapse($wdCollapseEnd)
    $after.InsertParagraphAfter()
    $after.Paragraphs.Last.Range.Style = $wdStyleNormal
}

$output = [System.IO.Path]::GetFullPath($OutputPath)
$outputDir = Split-Path -Parent $output
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Add()

try {
    $section = $doc.Sections.Item(1)
    $section.PageSetup.PaperSize = 2
    $section.PageSetup.Orientation = 0
    $section.PageSetup.TopMargin = 72
    $section.PageSetup.BottomMargin = 72
    $section.PageSetup.LeftMargin = 72
    $section.PageSetup.RightMargin = 72
    $section.PageSetup.HeaderDistance = 35.4
    $section.PageSetup.FooterDistance = 35.4
    $section.PageSetup.OddAndEvenPagesHeaderFooter = -1
    $section.PageSetup.DifferentFirstPageHeaderFooter = -1

    $normal = $doc.Styles.Item($wdStyleNormal)
    $normal.Font.Name = 'Calibri'
    $normal.Font.Size = 11
    $normal.Font.Color = $Black
    $normal.ParagraphFormat.SpaceAfter = 6
    $normal.ParagraphFormat.LineSpacingRule = $wdLineSpaceMultiple
    $normal.ParagraphFormat.LineSpacing = 13.2

    $titleStyle = $doc.Styles.Item($wdStyleTitle)
    $titleStyle.Font.Name = 'Calibri Light'
    $titleStyle.Font.Size = 30
    $titleStyle.Font.Bold = 0
    $titleStyle.Font.Color = $Ink
    $titleStyle.ParagraphFormat.SpaceAfter = 8

    $subtitleStyle = $doc.Styles.Item($wdStyleSubtitle)
    $subtitleStyle.Font.Name = 'Calibri'
    $subtitleStyle.Font.Size = 15
    $subtitleStyle.Font.Color = $Navy
    $subtitleStyle.ParagraphFormat.SpaceAfter = 8

    foreach ($item in @(
        @($wdStyleHeading1, 16, $Blue, 16, 8),
        @($wdStyleHeading2, 13, $Blue, 12, 6),
        @($wdStyleHeading3, 12, $Navy, 8, 4)
    )) {
        $style = $doc.Styles.Item($item[0])
        $style.Font.Name = 'Calibri'
        $style.Font.Size = $item[1]
        $style.Font.Bold = -1
        $style.Font.Color = $item[2]
        $style.ParagraphFormat.SpaceBefore = $item[3]
        $style.ParagraphFormat.SpaceAfter = $item[4]
        $style.ParagraphFormat.KeepWithNext = -1
    }

    # Named override: omit running headers because LibreOffice intermittently
    # suppresses even-page header parts created by Word COM. A quiet numbered
    # footer is retained consistently across Word and LibreOffice.
    foreach ($headerType in @(1, 2, 3)) {
        $header = $section.Headers.Item($headerType).Range
        $header.Text = ''
        $header.Borders.Item($wdBorderBottom).LineStyle = 0
    }

    foreach ($footerType in @(1, 2, 3)) {
        $footer = $section.Footers.Item($footerType).Range
        $footer.Text = ''
        $footer.Font.Name = 'Calibri'
        $footer.Font.Size = 8.5
        $footer.Font.Color = $Muted
        $footer.ParagraphFormat.Alignment = $wdAlignParagraphCenter
        $footer.End = $footer.End - 1
        $footer.Collapse($wdCollapseEnd)
        $footer.Fields.Add($footer, $wdFieldPage) | Out-Null
    }

    # Editorial cover
    $spacer = Add-Paragraph $doc '' $wdStyleNormal $wdAlignParagraphCenter
    $spacer.Format.SpaceAfter = 92
    $kicker = Add-Paragraph $doc 'METHODOLOGY DOCUMENTATION' $wdStyleNormal $wdAlignParagraphCenter
    $kicker.Range.Font.Name = 'Calibri'
    $kicker.Range.Font.Size = 10
    $kicker.Range.Font.Bold = -1
    $kicker.Range.Font.Color = $Gold
    $kicker.Format.SpaceAfter = 16
    Add-Paragraph $doc 'Leave-One-Galaxy-Out Cross-Validation' $wdStyleTitle $wdAlignParagraphCenter | Out-Null
    Add-Paragraph $doc 'Toy-object optimisation using 11 visually selected "cleaner" S4G galaxies' $wdStyleSubtitle $wdAlignParagraphCenter | Out-Null
    $sub = Add-Paragraph $doc 'Calibration of SEP and MTObjects foreground-masking parameters for subsequent application to the full 182-galaxy S4G sample' $wdStyleNormal $wdAlignParagraphCenter
    $sub.Range.Font.Size = 11.5
    $sub.Range.Font.Color = $Muted
    $sub.Format.SpaceAfter = 86
    $meta = @(
        @('Study', 'S4G foreground-object removal'),
        @('Calibration sample', '11 visually reviewed, lower-contamination galaxies'),
        @('Validation design', 'Leave-one-galaxy-out cross-validation (LOGO-CV)'),
        @('Injection design', 'Two independent deterministic six-toy realisations per galaxy'),
        @('Prepared', '26 August 2026')
    )
    $mt = Add-Table $doc $meta @(125, 343) $false
    $mt.Borders.Enable = 0
    for ($r = 1; $r -le $mt.Rows.Count; $r++) {
        $mt.Cell($r,1).Range.Font.Bold = -1
        $mt.Cell($r,1).Range.Font.Color = $Navy
        $mt.Cell($r,1).Shading.BackgroundPatternColor = $White
        $mt.Cell($r,2).Shading.BackgroundPatternColor = $White
    }

    $doc.Range($doc.Content.End - 1).InsertBreak($wdPageBreak)

    Add-Paragraph $doc 'Executive summary' $wdStyleHeading1 | Out-Null
    Add-Body $doc 'This methodology uses galaxy-level leave-one-out cross-validation to calibrate foreground-masking parameters on a deliberately restricted sample of 11 S4G galaxies judged by visual review to contain relatively few pre-existing foreground objects. The images are “cleaner”, not contaminant-free. Synthetic foreground-like toy objects provide known truth for measuring recovery while monitoring collateral masking of the galaxy image.' | Out-Null
    Add-Callout $doc 'Recommended methodological description' 'Leave-one-galaxy-out cross-validation with an independent synthetic-injection validation set, followed by full-sample refitting and deployment to the complete 182-galaxy S4G sample.' $LightBlue
    Add-Body $doc 'For each of 11 folds, one galaxy is excluded and the optimiser searches for parameters using the remaining 10. The fold-derived candidate is evaluated on the excluded galaxy and is also evaluated across all 11 galaxies using a second, independently seeded toy realisation. After candidate selection, each algorithm is re-optimised using all 11 calibration galaxies. The resulting frozen parameter set is then applied uniformly to the full set of 182 science images.' | Out-Null

    Add-Paragraph $doc '1. Purpose and scientific rationale' $wdStyleHeading1 | Out-Null
    Add-Body $doc 'The purpose is to select defensible global parameters for SEP and MTObjects without treating visibly contaminated science images as if they were clean ground truth. Real S4G images contain genuine galaxy structure, instrumental artefacts and foreground or background sources. Synthetic injection supplies an exact object-level truth mask while retaining the authentic spatially varying galaxy background.' | Out-Null
    Add-Bullet $doc 'Calibration target: recovery of injected foreground-like objects.' | Out-Null
    Add-Bullet $doc 'Protection target: limit excessive or incorrect masking of the underlying science image.' | Out-Null
    Add-Bullet $doc 'Independent unit: the galaxy, not the individual toy pixel or toy object.' | Out-Null
    Add-Bullet $doc 'Deployment target: one frozen parameter set applied consistently to all 182 S4G galaxies.' | Out-Null

    Add-Paragraph $doc '2. Calibration sample' $wdStyleHeading1 | Out-Null
    Add-Body $doc 'The calibration sample contains the following 11 galaxies, selected after visual review for substantially lower foreground contamination than the wider sample. Selection is purposive rather than random and should be reported as such.' | Out-Null
    $galaxies = @(
        @('1', 'IC1954', '7', 'NGC3486'),
        @('2', 'NGC0289', '8', 'NGC3681'),
        @('3', 'NGC0986', '9', 'NGC4133'),
        @('4', 'NGC1097', '10', 'NGC4450'),
        @('5', 'NGC1367', '11', 'NGC7531'),
        @('6', 'NGC2903', '', '')
    )
    $galaxyRows = (,@('#','Galaxy','#','Galaxy')) + $galaxies
    $gt = Add-Table $doc $galaxyRows @(40,194,40,194) $true
    foreach ($r in 2..$gt.Rows.Count) { Set-Cell $gt.Cell($r,1) $gt.Cell($r,1).Range.Text.Trim([char]13,[char]7) $false $White $wdAlignParagraphCenter; Set-Cell $gt.Cell($r,3) $gt.Cell($r,3).Range.Text.Trim([char]13,[char]7) $false $White $wdAlignParagraphCenter }
    Add-Callout $doc 'Interpretation' 'The sample supports calibration for lower-contamination S4G fields. It does not, by itself, establish generalisation across every morphology, inclination, surface-brightness regime or foreground density represented among all 182 galaxies.' $PaleGold

    Add-Paragraph $doc '3. Synthetic injection design' $wdStyleHeading1 | Out-Null
    Add-Body $doc 'Each original galaxy image receives two immutable and reproducible toy-object realisations. Both SEP and MTObjects read the same materialised injection payloads, truth masks and checksums, ensuring that algorithm comparisons are paired rather than confounded by different toy placements.' | Out-Null
    $inj = @(
        @('Injection set','Purpose','Per galaxy','Total toys'),
        @('Cross-validation','Optimisation within each 10-galaxy training fold','6 toys','66'),
        @('Winner selection','Independent realisation for comparing fold-derived candidates','6 different toys','66'),
        @('Combined','Injection-realisation coverage across the experiment','12 toys','132')
    )
    Add-Table $doc $inj @(105,235,70,58) $true | Out-Null
    Add-Body $doc 'The two sets use different global random seeds. Consequently, toy positions, object classes, widths, axis ratios, position angles and peak amplitudes can differ. Independence is therefore achieved with respect to toy realisation, not with respect to the underlying galaxy sample.' | Out-Null
    Add-Bullet $doc 'Six toys are injected into each galaxy in each set.' | Out-Null
    Add-Bullet $doc 'Toy peaks span 6–30 times the robust image-noise estimate.' | Out-Null
    Add-Bullet $doc 'Truth masks are dilated by one pixel for recovery scoring.' | Out-Null
    Add-Bullet $doc 'The cross-validation and winner-selection seeds are 202608261 and 202608262, respectively.' | Out-Null
    Add-Bullet $doc 'Payload checksums protect the paired comparison from accidental regeneration or mismatch.' | Out-Null

    Add-Paragraph $doc '4. LOGO-CV fold construction' $wdStyleHeading1 | Out-Null
    Add-Body $doc 'Leave-one-galaxy-out cross-validation is the leave-one-group-out form of cross-validation, with each complete galaxy treated as one group. Eleven folds are constructed after a deterministic shuffle. Each galaxy appears once as the held-out case and appears in the training set for the other ten folds.' | Out-Null
    $flow = @(
        @('STEP 1  |  Select one held-out galaxy'),
        @('↓'),
        @('STEP 2  |  Optimise on the other 10 galaxies using injection set A'),
        @('↓'),
        @('STEP 3  |  Evaluate on the excluded galaxy and on all 11 using injection set B'),
        @('↓'),
        @('STEP 4  |  Repeat until every galaxy has been held out once'),
        @('↓'),
        @('STEP 5  |  Select a stable candidate, then refit on all 11 galaxies')
    )
    $ft = Add-Table $doc $flow @(468) $false
    $ft.Borders.Enable = 0
    for ($r=1; $r -le $ft.Rows.Count; $r++) {
        $ft.Cell($r,1).Range.ParagraphFormat.Alignment = $wdAlignParagraphCenter
        if ($r % 2 -eq 1) { $ft.Cell($r,1).Shading.BackgroundPatternColor = $LightBlue; $ft.Cell($r,1).Range.Font.Bold = -1; $ft.Cell($r,1).Range.Font.Color = $Navy }
        else { $ft.Cell($r,1).Shading.BackgroundPatternColor = $White; $ft.Cell($r,1).Range.Font.Color = $Muted }
    }
    Add-Body $doc 'With N = 11 galaxies, each fold contains 10 training galaxies and one held-out galaxy. Six held-out toys are scored per fold, producing 66 toy-level held-out observations across the full LOGO-CV cycle. These toy observations are clustered within galaxies; they must not be reported as 66 independent galaxies.' | Out-Null

    Add-Paragraph $doc '5. Optimisation within each fold' $wdStyleHeading1 | Out-Null
    Add-Body $doc 'Each fold runs a separate Optuna parameter search. Eight startup trials provide broad exploration and 32 adaptive Tree-structured Parzen Estimator trials refine the search, giving 40 trials per fold and 440 fold-training trials per algorithm. Four image workers are used for computation.' | Out-Null
    Add-Numbered $doc 'Prepare the 10 training galaxies with their fixed cross-validation injection payloads.' | Out-Null
    Add-Numbered $doc 'Run the candidate foreground-masking algorithm on every injected training image.' | Out-Null
    Add-Numbered $doc 'Measure recovery of the known truth masks and the incremental mask introduced beyond detections already present in the original image.' | Out-Null
    Add-Numbered $doc 'Combine recovery and masking terms into the algorithm-specific objective, including penalties or feasibility constraints.' | Out-Null
    Add-Numbered $doc 'Retain the best training candidate from the 40 trials for subsequent held-out assessment.' | Out-Null
    Add-Callout $doc 'Why the galaxy is the fold unit' 'Pixel-level or toy-level random splitting would leak the same galaxy background into training and validation. Holding out the complete galaxy tests transfer to a different image background and morphology.' $LightBlue

    Add-Paragraph $doc '6. Validation and candidate selection' $wdStyleHeading1 | Out-Null
    Add-Paragraph $doc '6.1 Held-out assessment' $wdStyleHeading2 | Out-Null
    Add-Body $doc 'The best candidate from each training fold is applied to the excluded galaxy. Combining the 11 held-out outcomes estimates how the optimisation procedure transfers across the cleaner-galaxy sample. Because each fold validates on one galaxy, individual fold scores may be volatile; the aggregate distribution and cross-fold stability are more informative than a single fold.' | Out-Null
    Add-Paragraph $doc '6.2 Independent injection-realisation selection' $wdStyleHeading2 | Out-Null
    Add-Body $doc 'Each of the 11 fold-derived candidates is also evaluated across all 11 galaxies using the winner-selection injection set. This prevents candidate selection from depending solely on the six particular toys used during fold training. The aggregate all-11 objective is based primarily on mean recovery and masking measures, not the median of the 11 held-out results.' | Out-Null
    Add-Paragraph $doc '6.3 Algorithm-specific rule' $wdStyleHeading2 | Out-Null
    $sel = @(
        @('Algorithm','Candidate-selection rule'),
        @('SEP','Choose the fold-derived candidate with the best aggregate all-11 objective on the independent injection realisation.'),
        @('MTObjects','First require the candidate to satisfy recovery and masking feasibility conditions; then choose the feasible candidate with the best aggregate all-11 objective.')
    )
    Add-Table $doc $sel @(95,373) $true | Out-Null
    Add-Callout $doc 'Not nested cross-validation' 'This is best described as LOGO-CV plus independent injection-realisation selection. A fully nested design would reserve every outer held-out galaxy exclusively for final assessment while performing all parameter and candidate selection inside an inner loop.' $PaleGold

    Add-Paragraph $doc '7. Full-sample refitting and deployment' $wdStyleHeading1 | Out-Null
    Add-Body $doc 'Cross-validation estimates stability and transfer; it does not deliberately discard one galaxy from the final calibration. Once the assessment stage is complete, SEP and MTObjects are each re-optimised using all 11 cleaner galaxies. These final all-11 parameters become the production configurations.' | Out-Null
    Add-Body $doc 'Deployment then freezes the selected parameters and applies them without per-galaxy retuning to all 182 S4G images. The deployment stage should preserve provenance: algorithm version, parameter JSON, detection-image mode, injection-manifest checksum, clean-list version, random seeds and run timestamp.' | Out-Null
    $deploy = @(
        @('Stage','Galaxies','Purpose','Permitted adaptation'),
        @('Fold training','10 per fold','Parameter search','Yes, within the fold'),
        @('Held-out assessment','1 per fold','Estimate transfer','No'),
        @('Winner selection','All 11; alternate toys','Compare fold candidates','Selection only'),
        @('Final refit','All 11','Production parameters','Yes, final optimisation'),
        @('Science deployment','All 182','Foreground masking','No per-galaxy retuning')
    )
    Add-Table $doc $deploy @(82,70,178,138) $true | Out-Null

    Add-Paragraph $doc '8. Quantities to report' $wdStyleHeading1 | Out-Null
    Add-Bullet $doc 'Galaxy-level sample size: 11 calibration galaxies.' | Out-Null
    Add-Bullet $doc 'Fold structure: 11 folds, each with 10 training galaxies and one held-out galaxy.' | Out-Null
    Add-Bullet $doc 'Toy counts: 66 toys in each injection set; 132 toys across both realisations.' | Out-Null
    Add-Bullet $doc 'Held-out recovery: report the mean, median, range and preferably a galaxy-level bootstrap confidence interval across the 11 held-out galaxy outcomes.' | Out-Null
    Add-Bullet $doc 'Parameter stability: report the distribution or range of major parameter values across fold winners.' | Out-Null
    Add-Bullet $doc 'Mask burden: report mean and maximum incremental masked fraction, including any feasibility threshold breaches.' | Out-Null
    Add-Bullet $doc 'Algorithm comparison: use the paired galaxy/injection design and compare component metrics rather than assuming SEP and MTObjects objective values are directly interchangeable.' | Out-Null

    Add-Paragraph $doc '9. Assumptions and limitations' $wdStyleHeading1 | Out-Null
    Add-Bullet $doc 'The 11 galaxies were selected visually and are not a random sample of the 182; selection bias is therefore possible.' | Out-Null
    Add-Bullet $doc '"Cleaner" means lower apparent contamination, not verified absence of real foreground objects.' | Out-Null
    Add-Bullet $doc 'Additional toy seeds improve sampling of injection placements but do not increase the number of independent galaxies.' | Out-Null
    Add-Bullet $doc 'The second injection set is independent of the first toy realisation but uses the same galaxy backgrounds.' | Out-Null
    Add-Bullet $doc 'LOGO-CV with only 11 galaxies can have high variance. Aggregate performance and fold stability should be emphasised.' | Out-Null
    Add-Bullet $doc 'Application to all 182 galaxies is deployment, not proof that the parameters are equally optimal for every morphology or contamination regime.' | Out-Null
    Add-Bullet $doc 'A later external validation set containing independently labelled real foreground objects would provide stronger evidence of scientific generalisability.' | Out-Null

    Add-Paragraph $doc '10. Suggested thesis wording' $wdStyleHeading1 | Out-Null
    Add-Callout $doc 'Methods paragraph' 'Foreground-masking parameters were calibrated using leave-one-galaxy-out cross-validation on 11 visually selected S4G galaxies with comparatively low foreground contamination. In each of 11 folds, parameters were optimised on 10 galaxies containing fixed synthetic foreground-like injections and assessed on the excluded galaxy. Fold-derived candidates were additionally compared across all 11 galaxies using a second deterministic injection realisation generated with a different random seed. Following cross-validation, each algorithm was refitted on the complete 11-galaxy calibration sample, and the resulting frozen parameters were applied uniformly to the full 182-galaxy S4G dataset. Galaxies, rather than individual toys or pixels, were treated as the independent sampling units.' $LightBlue
    Add-Callout $doc 'Results caveat' 'The procedure evaluates transfer within a purposively selected lower-contamination galaxy sample. The independent injection realisation reduces sensitivity to particular toy placements but does not constitute an independent galaxy validation sample.' $PaleGold

    Add-Paragraph $doc '11. Reproducibility record' $wdStyleHeading1 | Out-Null
    $rep = @(
        @('Item','Implemented value'),
        @('Clean-galaxy list','IC1954; NGC0289; NGC0986; NGC1097; NGC1367; NGC2903; NGC3486; NGC3681; NGC4133; NGC4450; NGC7531'),
        @('Fold seed','202608260'),
        @('Cross-validation injection seed','202608261'),
        @('Winner-selection injection seed','202608262'),
        @('Toys per galaxy per set','6'),
        @('Toy peak range','6-30 robust sigma'),
        @('Truth dilation','1 pixel'),
        @('Trials per fold','40: 8 startup + 32 adaptive TPE'),
        @('Workers','4'),
        @('Detection image','Original science image'),
        @('Algorithms','SEP and MTObjects'),
        @('Deployment sample','182 S4G galaxies')
    )
    Add-Table $doc $rep @(155,313) $true | Out-Null

    Add-Paragraph $doc 'References and further reading' $wdStyleHeading1 | Out-Null
    Add-Paragraph $doc 'Hastie, T., Tibshirani, R. and Friedman, J. (2009). The Elements of Statistical Learning: Data Mining, Inference, and Prediction, 2nd ed. Springer. Chapter 7 discusses model assessment and cross-validation.' $wdStyleNormal $wdAlignParagraphLeft | Out-Null
    Add-Paragraph $doc 'scikit-learn developers. Cross-validation: evaluating estimator performance. https://scikit-learn.org/stable/modules/cross_validation.html' $wdStyleNormal $wdAlignParagraphLeft | Out-Null
    Add-Paragraph $doc 'scikit-learn developers. LeaveOneOut. https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.LeaveOneOut.html' $wdStyleNormal $wdAlignParagraphLeft | Out-Null

    try { $doc.BuiltInDocumentProperties.Item('Title').Value = 'S4G LOGO-CV Toy Objects Methodology' } catch {}
    try { $doc.BuiltInDocumentProperties.Item('Subject').Value = 'Leave-one-galaxy-out optimisation using 11 cleaner galaxies and deployment to 182 S4G galaxies' } catch {}
    try { $doc.BuiltInDocumentProperties.Item('Author').Value = 'UCLan MSc Research' } catch {}
    try { $doc.BuiltInDocumentProperties.Item('Keywords').Value = 'S4G; LOGO-CV; cross-validation; toy objects; SEP; MTObjects; foreground masking' } catch {}

    $doc.Fields.Update() | Out-Null
    $doc.Repaginate()
    $doc.SaveAs2($output, $wdFormatDocumentDefault)
    Write-Output $output
}
finally {
    if ($doc) { $doc.Close(0) }
    if ($word) { $word.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc) | Out-Null
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
