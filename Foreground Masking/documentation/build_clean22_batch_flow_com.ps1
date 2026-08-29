param(
    [string]$OutputPath = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\documentation\Revised 22 Galaxy Toy Object Optimisation - Data and Program Flow.docx'
)

$ErrorActionPreference = 'Stop'
$wdAlignLeft = 0; $wdAlignCenter = 1; $wdAlignRight = 2
$wdPageBreak = 7; $wdStyleNormal = -1; $wdLineSpaceMultiple = 5
$wdPaperLetter = 2; $wdFormatDocumentDefault = 16
$wdFieldPage = 33; $wdFieldNumPages = 26

function Bgr([int]$r,[int]$g,[int]$b) { return $r + 256*$g + 65536*$b }
$navy = Bgr 31 77 120; $blue = Bgr 46 116 181; $pale = Bgr 232 238 245
$light = Bgr 244 246 249; $gold = Bgr 122 90 0; $gray = Bgr 90 90 90
$green = Bgr 25 122 53; $red = Bgr 155 28 28; $white = Bgr 255 255 255

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $word.Documents.Add()

try {
    $sec = $doc.Sections.Item(1)
    $sec.PageSetup.PaperSize = $wdPaperLetter
    $sec.PageSetup.TopMargin = 72; $sec.PageSetup.BottomMargin = 72
    $sec.PageSetup.LeftMargin = 72; $sec.PageSetup.RightMargin = 72
    $sec.PageSetup.HeaderDistance = 35.4; $sec.PageSetup.FooterDistance = 35.4
    $sec.PageSetup.OddAndEvenPagesHeaderFooter = 0
    $sec.PageSetup.DifferentFirstPageHeaderFooter = 0

    $normal = $doc.Styles.Item('Normal')
    $normal.Font.Name = 'Calibri'; $normal.Font.Size = 10.5; $normal.Font.Color = Bgr 0 0 0
    $normal.ParagraphFormat.SpaceBefore = 0; $normal.ParagraphFormat.SpaceAfter = 6
    $normal.ParagraphFormat.LineSpacingRule = $wdLineSpaceMultiple; $normal.ParagraphFormat.LineSpacing = 13
    foreach ($entry in @(
        @('Heading 1',16,$blue,18,10), @('Heading 2',13,$blue,14,7), @('Heading 3',12,$navy,10,5)
    )) {
        $s=$doc.Styles.Item($entry[0]); $s.Font.Name='Calibri'; $s.Font.Size=$entry[1]
        $s.Font.Bold=$true; $s.Font.Color=$entry[2]; $s.ParagraphFormat.SpaceBefore=$entry[3]
        $s.ParagraphFormat.SpaceAfter=$entry[4]; $s.ParagraphFormat.KeepWithNext=$true
    }

    $header = $sec.Headers.Item(1).Range
    $header.Text = 'Foreground Masking Research | Revised clean-22 batch flow'
    $header.Font.Name='Calibri'; $header.Font.Size=8.5; $header.Font.Color=$gray
    $header.ParagraphFormat.Alignment=$wdAlignLeft
    $footer = $sec.Footers.Item(1).Range
    $footer.Text='Technical process specification  |  Page '
    $footer.Font.Name='Calibri'; $footer.Font.Size=8.5; $footer.Font.Color=$gray
    $footer.ParagraphFormat.Alignment=$wdAlignRight
    $footer.Collapse(0); $footer.Fields.Add($footer,$wdFieldPage) | Out-Null

    function End-Range { $r=$doc.Range($doc.Content.End-1,$doc.Content.End-1); return $r }
    function Add-Para([string]$text,[string]$style='Normal',[int]$align=$wdAlignLeft,[bool]$bold=$false,[double]$size=0,[int]$color=-1) {
        $r=End-Range; $r.Text=$text; $r.Style=$style; $r.ParagraphFormat.Alignment=$align
        if($bold){$r.Font.Bold=$true}; if($size -gt 0){$r.Font.Size=$size}; if($color -ge 0){$r.Font.Color=$color}
        $r.InsertParagraphAfter() | Out-Null; return $r
    }
    function Add-Bullet([string]$text) {
        $r=End-Range; $r.Text=$text; $r.Style='Normal'; $r.ListFormat.ApplyBulletDefault()
        $r.ParagraphFormat.LeftIndent=36; $r.ParagraphFormat.FirstLineIndent=-18; $r.ParagraphFormat.SpaceAfter=4
        $r.InsertParagraphAfter() | Out-Null
    }
    function Add-Number([string]$text) {
        $r=End-Range; $r.Text=$text; $r.Style='Normal'; $r.ListFormat.ApplyNumberDefault()
        $r.ParagraphFormat.LeftIndent=36; $r.ParagraphFormat.FirstLineIndent=-18; $r.ParagraphFormat.SpaceAfter=4
        $r.InsertParagraphAfter() | Out-Null
    }
    function Add-PageBreak { $r=End-Range; $r.InsertBreak($wdPageBreak) | Out-Null }
    function Shade-Cell($cell,[int]$colour,[int]$fontColour,[bool]$bold=$false) {
        $cell.Shading.BackgroundPatternColor=$colour; $cell.Range.Font.Color=$fontColour; $cell.Range.Font.Bold=$bold
        $cell.VerticalAlignment=1
    }
    function Add-Table([object[]]$headers,[object[]]$rows,[double[]]$widths) {
        $r=End-Range; $t=$doc.Tables.Add($r,$rows.Count+1,$headers.Count)
        $t.AllowAutoFit=$false; $t.Borders.Enable=1; $t.Range.Font.Name='Calibri'; $t.Range.Font.Size=9
        for($c=1;$c -le $headers.Count;$c++){$t.Cell(1,$c).Range.Text=[string]$headers[$c-1]; Shade-Cell $t.Cell(1,$c) $pale $navy $true; $t.Columns.Item($c).Width=$widths[$c-1]}
        for($i=0;$i -lt $rows.Count;$i++){
            for($c=0;$c -lt $headers.Count;$c++){$t.Cell($i+2,$c+1).Range.Text=[string]$rows[$i][$c]}
        }
        $t.Rows.Item(1).HeadingFormat=$true; $t.Range.ParagraphFormat.SpaceAfter=2
        $after=$doc.Range($t.Range.End,$t.Range.End); $after.InsertParagraphAfter() | Out-Null
        return $t
    }
    function Add-Flow([string[]]$labels) {
        $cols=$labels.Count*2-1; $r=End-Range; $t=$doc.Tables.Add($r,1,$cols); $t.AllowAutoFit=$false; $t.Borders.Enable=0
        $arrowWidth=14.0; $boxWidth=(468.0-($labels.Count-1)*$arrowWidth)/$labels.Count
        for($i=0;$i -lt $labels.Count;$i++){
            $cell=$t.Cell(1,2*$i+1); $cell.Range.Text=$labels[$i]; Shade-Cell $cell $navy $white $true
            $cell.Range.ParagraphFormat.Alignment=$wdAlignCenter; $cell.Range.Font.Size=9; $cell.Width=$boxWidth
            if($i -lt $labels.Count-1){$a=$t.Cell(1,2*$i+2); $a.Range.Text=[string][char]0x2192; $a.Range.Font.Size=14; $a.Range.Font.Color=$blue; $a.Range.ParagraphFormat.Alignment=$wdAlignCenter; $a.Width=$arrowWidth}
        }
        $after=$doc.Range($t.Range.End,$t.Range.End); $after.InsertParagraphAfter() | Out-Null
    }
    function Add-Callout([string]$label,[string]$text,[int]$colour=$blue) {
        $r=End-Range; $t=$doc.Tables.Add($r,1,1); $t.AllowAutoFit=$false; $t.Columns.Item(1).Width=468
        $t.Borders.Enable=0; $t.Cell(1,1).Shading.BackgroundPatternColor=$light
        $t.Cell(1,1).Range.Text="$label`r$text"; $t.Cell(1,1).Range.Font.Name='Calibri'; $t.Cell(1,1).Range.Font.Size=10
        $t.Cell(1,1).Range.Paragraphs.Item(1).Range.Font.Bold=$true; $t.Cell(1,1).Range.Paragraphs.Item(1).Range.Font.Color=$colour
        $after=$doc.Range($t.Range.End,$t.Range.End); $after.InsertParagraphAfter() | Out-Null
    }

    # Cover
    Add-Para 'TECHNICAL PROCESS SPECIFICATION' 'Normal' $wdAlignCenter $true 10 $gold | Out-Null
    Add-Para 'Revised 22-Galaxy Toy Object Optimisation' 'Normal' $wdAlignCenter $true 26 $navy | Out-Null
    Add-Para 'Displayed-frame data flow, convergence-controlled optimisation and decision pathway for SEP and MTObjects' 'Normal' $wdAlignCenter $false 14 $gray | Out-Null
    Add-Para '' | Out-Null
    Add-Flow @('22 clean galaxies','Displayed-frame toys','22-fold Optuna CV','Stability audit','Freeze parameters','182-galaxy application')
    Add-Para '' | Out-Null
    Add-Callout 'Purpose' 'Define the auditable path from the visually revised clean calibration sample to reproducible parameter optimisation within the galaxy area of interest, followed by selection of frozen SEP and MTObjects configurations and application to the full 182-galaxy population.' $navy
    Add-Para 'Configuration documented: 29 August 2026' 'Normal' $wdAlignCenter $false 10 $gray | Out-Null
    Add-Para 'Environment: Windows host + Ubuntu 24.04 under WSL2 | Python virtual environment: /root/venvs/pythonscripts' 'Normal' $wdAlignCenter $false 9 $gray | Out-Null
    Add-PageBreak

    Add-Para 'Document map' 'Heading 1' | Out-Null
    Add-Para 'This document distinguishes data artefacts from programs and identifies the control points that preserve comparability between SEP and MTObjects.' | Out-Null
    $tocRange=End-Range; $doc.TablesOfContents.Add($tocRange,$true,1,3) | Out-Null
    Add-PageBreak

    Add-Para '1. End-to-end batch architecture' 'Heading 1' | Out-Null
    Add-Flow @('Visual review labels','Clean-22 list','Immutable AOI toys','22 fold studies/method','Stability review','Freeze + apply to 182')
    Add-Callout 'Key design rule' 'SEP and MTObjects do not receive separately randomised toys. Both methods read the same materialised delta image, truth mask, truth labels and toy metadata from one checksum-protected manifest.' $green
    Add-Para 'The process separates calibration from deployment. The 22 galaxies are used to tune and compare parameters. The current continuation pauses after optimisation, held-out evaluation, convergence assessment and parameter-stability reporting so the evidence can be reviewed. The next planned stage freezes one configuration per method and applies it without retraining to the 182-galaxy geometry manifest.' | Out-Null
    Add-Para 'Primary stages' 'Heading 2' | Out-Null
    foreach($x in @(
        'Selection: retain only the 22 fields classified Clean in the corrected wide, negative, galaxy-centred review.',
        'Injection: create cross-validation and winner-selection toy sets with different deterministic seeds.',
        'Optimisation: run leave-one-galaxy-out Optuna studies independently for SEP and MTObjects.',
        'Selection: score every fold winner on the same independent 22-galaxy winner-selection set.',
        'Decision gate: compare objective convergence, near-optimal parameter stability, fold transfer and runtime before choosing a frozen configuration.',
        'Full-population application: use the chosen SEP and MTObjects configurations on all 182 galaxies and generate the usual method-specific and combined diagnostics.'
    )){Add-Number $x}

    Add-Para '2. Input sample: the revised 22 clean galaxies' 'Heading 1' | Out-Null
    Add-Para 'The clean sample is an explicit data file rather than a filename convention or an inferred rank cutoff. It is derived from the latest categorical re-review and contains exactly the galaxies labelled Clean.' | Out-Null
    $names=@('NGC4765','NGC3486','NGC4405','IC1954','NGC4579','NGC3681','PGC013821','NGC1367','NGC4639','NGC4981','NGC3684','NGC0289','NGC4102','NGC0986','NGC3227','NGC0578','NGC4450','NGC7531','NGC3359','NGC3627','NGC2903','NGC1097')
    $nameRows=@(); for($i=0;$i -lt 8;$i++){$row=@(); for($j=0;$j -lt 3;$j++){$k=$i+8*$j; $row+=if($k -lt $names.Count){"$($k+1). $($names[$k])"}else{''}}; $nameRows+=,@($row)}
    Add-Table @('Clean galaxies 1-8','Clean galaxies 9-16','Clean galaxies 17-22') $nameRows @(156,156,156) | Out-Null
    Add-Table @('Input','Role','Validation') @(
        @('clean_galaxies_revised22.txt','Authoritative calibration membership','22 unique names; exact match to current Clean decisions'),
        @('s4g_image_geometry_manifest.csv','182-galaxy image paths and geometry','Required centre, PA, inclination, bar size and pixel scale'),
        @('*.phot.1.fits','Original 3.6 micrometre science images','SHA-256 recorded for each injected case'),
        @('candidate_union_rereview_decisions.csv','Selection provenance','22 Clean, 5 Ambiguous, 51 Polluted at completion')
    ) @(135,205,128) | Out-Null

    Add-Para '3. Toy creation and insertion' 'Heading 1' | Out-Null
    Add-Flow @('Load FITS + geometry','Derive investigated region','Draw position/type/shape','Render model + truth','Reject overlap/outside','Save immutable payload')
    Add-Para 'Two injection sets are generated for every clean galaxy. The cross_validation set is used inside fold training; the winner_selection set is independently seeded and is used to choose among the 22 fold winners. Each set contains five toys per galaxy, giving 110 toys per set and 220 materialised toys in total.' | Out-Null
    Add-Table @('Property','Implementation') @(
        @('Types','Star 50%; compact cluster 20%; small galaxy 30%'),
        @('Brightness','Uniform peak amplitude from 6 to 30 robust background sigma'),
        @('Nominal size','Stars/clusters: 2-10 px FWHM; galaxies: 5-22 px FWHM'),
        @('Analysis area','Finite pixels in the displayed, galaxy-centred, deprojected square used for visual Clean/Ambiguous/Polluted classification'),
        @('Placement','Inside that displayed galaxy area of interest, away from its boundary and non-overlapping with earlier toys; unused parts of a larger FITS mosaic are excluded'),
        @('Truth','Per-toy label image plus union truth mask, dilated by one pixel'),
        @('Reproducibility','Global set seed plus CRC32-derived per-galaxy seed'),
        @('Materialisation','Compressed NPZ containing delta, truth_mask and truth_labels; hashes stored in JSON')
    ) @(125,343) | Out-Null
    Add-Para 'Adaptive placement fallback' 'Heading 2' | Out-Null
    Add-Para 'The generator first attempts the requested five toys at normal size within the displayed deprojected area of interest. If a dense or small region cannot accommodate them, it retries at FWHM scales 0.85 and 0.70, then retries progressively fewer toys at original size. Requested count, actual count, scale, analysis-region pixel count and fallback flag are recorded per galaxy. In the current displayed-frame manifest all 44 cases (22 galaxies x 2 injection sets) accepted five toys at normal size; no fallback was used.' | Out-Null
    Add-Callout 'Correction from earlier runs' 'Earlier optimisation results used mask fractions and/or toy placement relative to a larger FITS frame. Those results are not comparable with the visual classifications and are treated as superseded. The current metric version is paired-toy-metrics-displayed-frame-v2.' $red
    Add-Callout 'Why materialise?' 'A failed or altered random draw cannot make one method appear better. SEP and MTObjects consume identical pixels and identical truth definitions.' $green

    Add-Para '4. SEP masking program flow' 'Heading 1' | Out-Null
    Add-Flow @('Injected image','SEP background mesh','Threshold + convolution','Deblend segmentation','Area/shape/centre filters','Dilate mask','Evaluate truth overlap')
    Add-Para 'SEP processing is provided by sep_processing.sep_products(). It builds a background model, subtracts it, convolves with the selected filter kernel and calls sep.extract. The segmentation is filtered by maximum area, elongation and central exclusion; retained components are dilated to form the final mask.' | Out-Null
    Add-Table @('Optimised SEP parameter','Search space') @(
        @('detect_thresh','0.6-2.0 sigma'),@('minarea','5-35 pixels'),@('deblend_nthresh','16, 32 or 64'),
        @('deblend_cont','0.001-0.03, logarithmic'),@('back_size','32, 64, 128 or 256'),
        @('filter_size','1, 3, 5, 7 or 9'),@('dilation_radius','1-6 pixels'),
        @('max_area','20-8000 pixels'),@('max_elongation','1.5-30')
    ) @(205,263) | Out-Null
    Add-Para 'The cleaned image replaces masked pixels with the median of finite unmasked pixels for diagnostic display. Optimisation is driven by the mask-to-truth comparison rather than the cosmetic appearance of that replacement.' | Out-Null

    Add-Para '5. MTObjects masking program flow' 'Heading 1' | Out-Null
    Add-Flow @('Injected image','Preprocess + Gaussian option','Construct max-tree','Filter significant nodes','Relabel segments','Area/shape/centre filters','Dilate + evaluate')
    Add-Para 'MTObjects processing is provided by mtobjects_spike_gate_processing.mtobjects_products(). It preprocesses the finite image, constructs an OriginalMaxTree, floods and filters the tree, relabels significant components, applies the common geometric filters and dilates the retained segmentation.' | Out-Null
    Add-Table @('Optimised MTObjects parameter','Search space') @(
        @('move_factor','0.0-1.0'),@('min_distance','0.0-1.0'),@('gaussian_fwhm','0.0-5.0'),
        @('bg_variance','10^-4 to 10^4; calibrated/log search in this run'),@('minarea','1-40 pixels'),
        @('dilation_radius','1-6 pixels'),@('max_area','20-3000 pixels'),@('max_elongation','2.0-15.0')
    ) @(205,263) | Out-Null
    Add-Callout 'Concurrency constraint' 'MTObjects workers are separate processes, not threads, because the MTObjects library changes its working directory while loading C libraries. Linux fork allows prepared arrays to be shared copy-on-write.' $gold

    Add-Para '6. Mask scoring and objective functions' 'Heading 1' | Out-Null
    Add-Para 'Each method is scored against the materialised truth mask within the same displayed deprojected area of interest. The case evaluator records pixel recall, precision, F-score, mean per-toy recall, whole-toy detection rate, displayed-frame masked fraction, displayed-frame false-positive fraction and segment count.' | Out-Null
    Add-Table @('Component','SEP weighting','MTObjects weighting') @(
        @('Pixel recall','0.45','Included through F-score'),
        @('Pixel F-score','0.20','0.45'),
        @('Mean per-toy recall','0.25','0.35'),
        @('Whole-toy detection rate','0.20','0.20'),
        @('Data loss','0.35 x mean masked fraction','0.35 x mean masked fraction'),
        @('False positives','0.05 x capped false-positive fraction','0.05 x capped false-positive fraction'),
        @('Hard controls','Large penalty above 15% maximum masked fraction','Same cap plus minimum recovery feasibility gates')
    ) @(155,156,157) | Out-Null
    Add-Para 'The optimiser minimises objective. For a feasible trial under the displayed-frame mask cap, objective is the negative of the composite score. Cap violations receive a large positive penalty. MTObjects additionally rejects trials that produce no incremental mask pixels or fail its minimum toy-detection and mean-toy-recall criteria.' | Out-Null

    Add-Para '7. Optuna and 22-fold optimisation' 'Heading 1' | Out-Null
    Add-Flow @('Hold out 1 galaxy','Optimise on other 21','40-80 Optuna trials','Objective convergence test','Score held-out galaxy','Repeat x22 + stability audit')
    Add-Table @('Setting','Value') @(
        @('Fold design','Leave one galaxy out: 22 folds; 21 train + 1 held out'),
        @('Trial budget','Minimum 40; maximum 80 total completed trials per fold'),
        @('Sampler start','8 initial TPE startup points; subsequent trials are guided'),
        @('Objective early stop','After at least 40 trials, stop after 20 completed trials without meaningful improvement'),
        @('Meaningful improvement','Relative tolerance 0.1% of objective scale with absolute floor 1e-5'),
        @('Parallel workers','4'),
        @('Methods','SEP completes first; MTObjects then runs using the same injection manifest'),
        @('Study storage','Persistent SQLite studies below /root/clean22-displayed-frame-5toy-optuna-studies'),
        @('Winner selection','Each fold winner is rescored on the common independent 22-galaxy winner_selection set; minimum objective wins'),
        @('Outputs','Best JSON, fold summaries, candidate CSV, held-out detail CSV and configuration JSON')
    ) @(135,333) | Out-Null
    Add-Para 'A held-out fold is never used to fit the candidate parameters for that fold. Its role is to estimate transfer to an unseen galaxy. The final selection adds a second protection: all 22 candidate winners are compared on the same independently injected dataset.' | Out-Null
    Add-Para 'Objective and model-parameter stability' 'Heading 2' | Out-Null
    Add-Para 'Objective convergence alone does not demonstrate that the masking model is well identified. Several materially different parameter combinations can occupy a near-equal objective plateau. A separate read-only audit therefore examines the elite trials (normally the best 20%, bounded to 5-20 trials) without changing Optuna sampling or the early-stop decision.' | Out-Null
    Add-Table @('Diagnostic','Interpretation') @(
        @('Normalised numerical IQR','Spread of each numerical parameter relative to its declared search range; IQR above 0.15 is flagged'),
        @('Categorical dominance','Most common elite value; dominance below 70% is flagged'),
        @('Near-optimal clusters','Connected groups in normalised parameter space; multiple groups indicate alternative near-optimal states'),
        @('Strong correlations','Absolute Spearman correlation of at least 0.75 identifies compensating parameter relationships'),
        @('Cross-fold stability','Median/IQR or dominant value of each winning parameter across the available folds'),
        @('Combined classification','Objective stable/continuing crossed with parameters stable/multimodal')
    ) @(155,313) | Out-Null
    Add-Callout 'Selection implication' 'A broad stable near-optimal region is preferable to an isolated winning trial. Objective-stable but multimodal folds are retained and reported; parameter instability is diagnostic evidence, not currently a hard reason to run indefinitely.' $gold

    Add-Para '8. Orchestration, monitoring and restart behaviour' 'Heading 1' | Out-Null
    Add-Table @('Program','Responsibility') @(
        @('generate_paired_toy_manifest.py','Create and checksum both injection sets; apply adaptive placement'),
        @('run_clean22_full_cross_validation.py','Run SEP 22-fold CV, then MTObjects 22-fold CV'),
        @('cross_validate_toy_objects_SEP.py','Manage SEP folds, held-out scoring and final winner'),
        @('cross_validate_toy_objects_MTObjects.py','Manage MTObjects folds, feasibility checks and final winner'),
        @('optimise_toy_objects_SEP.py','Optuna objective and worker evaluation for one SEP fold'),
        @('optimise_toy_objects_MTObjects.py','Optuna objective and process-worker evaluation for one MTObjects fold'),
        @('watch_clean22_displayed_frame_5toy_80trial.sh','Resume studies, recover freezes and enforce the optimisation-only 80-trial continuation'),
        @('monitor_clean22_80trial_convergence.ps1','Visible progress plus objective/parameter stability classifications'),
        @('audit_optuna_parameter_stability.py','Read every SQLite study; quantify elite dispersion, clustering, correlations and cross-fold stability'),
        @('watch_optuna_parameter_stability.sh','Refresh parameter-stability outputs every two minutes until completion')
    ) @(190,278) | Out-Null
    Add-Para 'Completed trials remain in persistent SQLite storage and are reused. An interrupted RUNNING trial is marked failed and replaced rather than counted as complete. Candidate selection searches best-result JSON files across original and continuation directories, preventing a resumed fold from selecting only its newest trials. The watchdog regards 30 minutes without an update as a freeze and restarts the affected process chain cleanly.' | Out-Null
    Add-Para 'Runtime benchmarking' 'Heading 2' | Out-Null
    Add-Para 'Every trial summary records elapsed_seconds, worker count, Python version, platform and parameter values. Each cross-validation root also receives fold_timing.csv with start/end times, wall seconds, training and held-out counts, trials before/after, new-trial count, completion reason, hostname, logical CPU count and worker count. This supports later local 4/8/12-worker tests and like-for-like Azure benchmarking.' | Out-Null

    Add-Para '9. Next stage: application to the full 182-galaxy population' 'Heading 1' | Out-Null
    Add-Flow @('SEP winner JSON','SEP batch on 182','SEP PNG + CSV')
    Add-Flow @('MTObjects winner JSON','MTObjects batch on 182','MTO PNG + CSV')
    Add-Flow @('Matched SEP/MTO PNGs','Composite utility','182 combined comparisons')
    Add-Callout 'Current execution boundary' 'The active convergence-controlled continuation performs optimisation and validation only. This is a one-off pause for review, not removal of the 182-galaxy application from the methodology.' $gold
    Add-Para 'The next stage begins after both methods have been reported and the objective/parameter-stability evidence has been reviewed. Parameters will then be frozen and applied to all 182 galaxies; there will be no further Optuna training on that population. The geometry manifest supplies each image path and galaxy geometry.' | Out-Null
    Add-Table @('Production entry point','Input','Output') @(
        @('batch_toy_objects_SEP.py','SEP winner JSON + 182-row manifest','One SEP diagnostic PNG per galaxy and sep_optimised_apply_summary.csv'),
        @('batch_toy_objects_MTObjects.py','MTObjects winner JSON + MTObjects library + manifest','One MTObjects diagnostic PNG per galaxy and mtobjects_optimised_apply_summary.csv'),
        @('combine_toy_method_pngs.py','Matched SEP and MTObjects PNG directories','One side-by-side comparison PNG per galaxy')
    ) @(175,145,148) | Out-Null
    Add-Bullet 'Expected production directories: SEP, MTObjects and Combined under the clean-22 all182 application root.'
    Add-Bullet 'The future production design will use the agreed displayed-frame toy configuration; adaptive placement metadata must be retained if a field requires fewer toys.'
    Add-Bullet 'Per-galaxy errors are logged and resumable. Completion requires 182 successful unique galaxy rows or explicit resolution of any exception.'
    Add-Bullet 'The combined view is generated after both method-specific PNG sets are complete.'

    Add-Para '10. Data lineage and audit trail' 'Heading 1' | Out-Null
    Add-Table @('Artefact','What it proves') @(
        @('candidate_union_rereview_decisions.csv','Human categorical basis for the 22 clean fields'),
        @('clean_galaxies_revised22.txt','Exact calibration membership consumed by the batch'),
        @('paired_toy_injection_manifest.json + SHA-256','Seeds, source hashes, payload hashes, toy properties, fold membership and fallback use'),
        @('payloads/cross_validation/*.npz','Exact injected deltas and truth used during fold optimisation'),
        @('payloads/winner_selection/*.npz','Independent common comparison set used to choose the final winner'),
        @('cross_validation_config.json','Run arguments, parameter bounds and fold membership'),
        @('*optimisation_summary.csv','Trial-level objectives, metrics, status and parameters'),
        @('fold_timing.csv','Per-fold wall time, new and cumulative trial counts, worker count and machine/runtime metadata'),
        @('optuna_parameter_stability.csv/.json','Live fold classifications, elite dispersion, clusters, correlations and unstable parameters'),
        @('optuna_parameter_stability_across_folds.csv','Cross-fold spread of the currently winning parameter values'),
        @('*toy_cross_validation_best.json','Selected production parameters and winning-fold provenance'),
        @('*optimised_apply_summary.csv','Per-galaxy 182-population completion and errors')
    ) @(205,263) | Out-Null
    Add-Callout 'Interpretation boundary' 'The 22 galaxies are low-contamination calibration fields, not empty images and not perfect truth. Artificial toys provide the known detection truth; the clean fields reduce interference from unknown foreground sources.' $red

    Add-Para '11. Acceptance checks' 'Heading 1' | Out-Null
    foreach($x in @(
        'Selection file contains exactly 22 unique names and matches the latest Clean decisions.',
        'Both injection sets contain all 22 galaxies, valid hashes and a recorded actual toy count.',
        'SEP and MTObjects read the same injection manifest and named injection sets.',
        'Every fold completes at least 40 trials and then either satisfies the 20-trial objective-convergence rule or reaches 80 completed trials.',
        'Parameter-stability outputs cover all available SEP and MTObjects SQLite studies and identify multimodal/unstable elite parameters.',
        'Per-trial elapsed_seconds and per-fold timing records are present for runtime benchmarking.',
        'Cross-validation candidate CSV contains 22 fold winners per method.',
        'Winner JSON identifies the selected fold and independent 22-galaxy metrics.',
        'The one-off review gate is completed and one SEP and one MTObjects configuration are explicitly frozen before full-population processing.',
        'The next-stage production gate requires complete SEP, MTObjects and Combined outputs for all 182 galaxies or documented exceptions.'
    )){Add-Bullet $x}

    Add-Para 'Appendix A. Program-to-data dependency map' 'Heading 1' | Out-Null
    Add-Table @('Producer','Data artefact','Consumer') @(
        @('Interactive catalogue reviewer','candidate_union_rereview_decisions.csv','Clean-list preparation'),
        @('Clean-list preparation','clean_galaxies_revised22.txt','Manifest generator and CV drivers'),
        @('Manifest generator','paired manifest + NPZ payloads','SEP and MTObjects optimisers/CV'),
        @('SEP CV + stability audit','SEP candidates, winner and stability evidence','Parameter decision; later SEP all-182 batch'),
        @('MTObjects CV + stability audit','MTO candidates, winner and stability evidence','Parameter decision; later MTObjects all-182 batch'),
        @('SEP and MTO batches','Method PNGs + per-galaxy summaries','Composite generator and comparison report'),
        @('Composite generator','Combined PNG set','Visual review and final study documentation')
    ) @(150,170,148) | Out-Null

    Add-Para 'Appendix B. Principal storage locations' 'Heading 1' | Out-Null
    Add-Table @('Location','Contents') @(
        @('Foreground Masking/Optimisation','Clean list, manifest generator, optimisers, CV drivers and monitors'),
        @('Foreground Masking/Shared','SEP and MTObjects masking implementations and common display logic'),
        @('Foreground Masking/Batch tools','All-galaxy method runners and composite orchestration'),
        @('.../clean22_displayed_frame_5toy_optimisation/paired_injections','Immutable displayed-AOI clean-22 injection manifest and payloads'),
        @('.../clean22_displayed_frame_5toy_optimisation/SEP_cross_validation','SEP folds, timing, trial summaries and winner'),
        @('.../clean22_displayed_frame_5toy_optimisation/MTObjects_cross_validation','MTObjects folds, timing, trial summaries and winner'),
        @('.../clean22_displayed_frame_5toy_optimisation/optuna_parameter_stability*','Live within-fold and cross-fold stability evidence'),
        @('/root/clean22-displayed-frame-5toy-optuna-studies','Persistent SEP and MTObjects SQLite studies'),
        @('Future all182 application root','Deferred SEP, MTObjects and Combined production outputs')
    ) @(250,218) | Out-Null

    $doc.Fields.Update() | Out-Null
    $doc.TablesOfContents.Item(1).Update() | Out-Null
    $doc.Repaginate()
    try {$doc.BuiltInDocumentProperties.Item('Title').Value='Revised 22-Galaxy Toy Object Optimisation - Data and Program Flow'} catch {}
    try {$doc.BuiltInDocumentProperties.Item('Subject').Value='SEP and MTObjects foreground-masking batch methodology'} catch {}
    try {$doc.BuiltInDocumentProperties.Item('Author').Value='Gordon Brown'} catch {}
    $outDir=Split-Path -Parent $OutputPath; New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $doc.SaveAs2($OutputPath,$wdFormatDocumentDefault)
    $doc.Close($false); $word.Quit()
    [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($doc) | Out-Null
    [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) | Out-Null
    Write-Output $OutputPath
} catch {
    try {$doc.Close($false)} catch {}; try {$word.Quit()} catch {}
    throw
}
