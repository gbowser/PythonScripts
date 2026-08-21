param(
    [Parameter(Mandatory=$true)][string]$MetricsCsv,
    [Parameter(Mandatory=$true)][string]$SepSummaryCsv,
    [Parameter(Mandatory=$true)][string]$MtoSummaryCsv,
    [Parameter(Mandatory=$true)][string]$OutputXlsx
)

$ErrorActionPreference = 'Stop'
$metrics = @(Import-Csv -LiteralPath $MetricsCsv)
$sepArchive = @{}
Import-Csv -LiteralPath $SepSummaryCsv | ForEach-Object { $sepArchive[$_.name] = $_ }
$mtoArchive = @{}
Import-Csv -LiteralPath $MtoSummaryCsv | ForEach-Object { $mtoArchive[$_.name] = $_ }

function Num([object]$value) {
    if ($null -eq $value -or [string]::IsNullOrWhiteSpace([string]$value)) { return $null }
    return [double]::Parse([string]$value, [Globalization.CultureInfo]::InvariantCulture)
}

$excel = $null
$book = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $book = $excel.Workbooks.Add()
    while ($book.Worksheets.Count -lt 4) { [void]$book.Worksheets.Add() }

    $summary = $book.Worksheets.Item(1); $summary.Name = 'Summary'
    $comparison = $book.Worksheets.Item(2); $comparison.Name = 'Galaxy Comparison'
    $population = $book.Worksheets.Item(3); $population.Name = 'Population Metrics'
    $notes = $book.Worksheets.Item(4); $notes.Name = 'Definitions and Sources'
    while ($book.Worksheets.Count -gt 4) { $book.Worksheets.Item($book.Worksheets.Count).Delete() }

    $headers = @(
        'Galaxy','SEP Archived Mask %','MTO Archived Mask %','SEP Recalc Mask %','MTO Recalc Mask %','SEP - MTO Mask pp',
        'SEP Toy Pixel Recall %','MTO Toy Pixel Recall %','SEP - MTO Recall pp','SEP Toys Recovered >=50%','MTO Toys Recovered >=50%',
        'SEP Toy Detection %','MTO Toy Detection %','SEP Mean Per-Toy Recall %','MTO Mean Per-Toy Recall %',
        'SEP Toy-associated Precision %','MTO Toy-associated Precision %','SEP Toy F1 %','MTO Toy F1 %',
        'SEP Non-toy Mask %','MTO Non-toy Mask %','SEP Segments Kept','MTO Segments Kept','SEP Segments Raw','MTO Segments Raw',
        'SEP Runtime s','MTO Runtime s','SEP Recalc - Archive pp','MTO Recalc - Archive pp','Status'
    )
    for ($c=0; $c -lt $headers.Count; $c++) { $comparison.Cells.Item(1,$c+1).Value2 = $headers[$c] }

    $r = 2
    foreach ($item in $metrics) {
        $sepA = $sepArchive[$item.galaxy]
        $mtoA = $mtoArchive[$item.galaxy]
        $values = @(
            $item.galaxy,
            (Num $sepA.masked_fraction),(Num $mtoA.masked_fraction),(Num $item.sep_masked_fraction),(Num $item.mto_masked_fraction),
            (Num $item.masked_fraction_difference_sep_minus_mto),
            (Num $item.sep_toy_pixel_recall),(Num $item.mto_toy_pixel_recall),(Num $item.toy_recall_difference_sep_minus_mto),
            (Num $item.sep_recovered_toys),(Num $item.mto_recovered_toys),(Num $item.sep_toy_detection_rate),(Num $item.mto_toy_detection_rate),
            (Num $item.sep_mean_per_toy_recall),(Num $item.mto_mean_per_toy_recall),(Num $item.sep_toy_associated_precision),
            (Num $item.mto_toy_associated_precision),(Num $item.sep_toy_f_score),(Num $item.mto_toy_f_score),
            (Num $item.sep_false_mask_fraction),(Num $item.mto_false_mask_fraction),(Num $item.sep_segments_kept),(Num $item.mto_segments_kept),
            (Num $item.sep_segments_raw),(Num $item.mto_segments_raw),(Num $item.sep_elapsed_seconds),(Num $item.mto_elapsed_seconds),
            ((Num $item.sep_masked_fraction) - (Num $sepA.masked_fraction)),((Num $item.mto_masked_fraction) - (Num $mtoA.masked_fraction)),$item.status
        )
        for ($c=0; $c -lt $values.Count; $c++) {
            $cell = $comparison.Cells.Item([int]$r, [int]($c + 1))
            if ($values[$c] -is [double] -or $values[$c] -is [int] -or $values[$c] -is [long]) {
                $cell.Value2 = [double]$values[$c]
            } else {
                $cell.Value2 = [string]$values[$c]
            }
            [void][Runtime.InteropServices.Marshal]::ReleaseComObject($cell)
        }
        $r++
    }
    $lastRow = $r - 1
    $comparison.Range('B2:I' + $lastRow).NumberFormat = '0.00%'
    $comparison.Range('L2:U' + $lastRow).NumberFormat = '0.00%'
    $comparison.Range('AB2:AC' + $lastRow).NumberFormat = '0.000%'
    $comparison.Range('Z2:AA' + $lastRow).NumberFormat = '0.00'
    $comparison.Range('A1:AD1').Font.Bold = $true
    $comparison.Range('A1:AD1').Interior.Color = 0xD9EAF7
    $comparison.Range('A1:AD' + $lastRow).AutoFilter() | Out-Null
    $comparison.Application.ActiveWindow.SplitRow = 1
    $comparison.Application.ActiveWindow.FreezePanes = $true
    $comparison.Columns.Item('A').ColumnWidth = 16
    $comparison.Columns.Item('B:AD').ColumnWidth = 14
    $comparison.Rows.Item(1).WrapText = $true
    $comparison.Rows.Item(1).RowHeight = 42

    $population.Cells.Item(1,1).Value2 = 'Population statistics across 182 matched galaxies'
    $population.Range('A1:L1').Merge(); $population.Range('A1').Font.Bold=$true; $population.Range('A1').Font.Size=16
    $statHeaders = @('Metric','Method','N','Mean','Std Dev','Minimum','P10','P25','Median','P75','P90','P95','Maximum')
    for ($c=0; $c -lt $statHeaders.Count; $c++) { $population.Cells.Item(3,$c+1).Value2=$statHeaders[$c] }
    $metricDefs = @(
        @('Masked image area','SEP','D'),@('Masked image area','MTObjects','E'),
        @('Toy-pixel recall','SEP','G'),@('Toy-pixel recall','MTObjects','H'),
        @('Toy detection rate (>=50% recovered)','SEP','L'),@('Toy detection rate (>=50% recovered)','MTObjects','M'),
        @('Mean per-toy recall','SEP','N'),@('Mean per-toy recall','MTObjects','O'),
        @('Toy-associated precision','SEP','P'),@('Toy-associated precision','MTObjects','Q'),
        @('Toy F1 score','SEP','R'),@('Toy F1 score','MTObjects','S'),
        @('Non-toy mask fraction','SEP','T'),@('Non-toy mask fraction','MTObjects','U')
    )
    $pr = 4
    foreach ($def in $metricDefs) {
        $range = "'Galaxy Comparison'!$($def[2])`$2:$($def[2])`$$lastRow"
        $population.Cells.Item($pr,1).Value2=$def[0]; $population.Cells.Item($pr,2).Value2=$def[1]
        $population.Cells.Item($pr,3).Formula="=COUNT($range)"
        $population.Cells.Item($pr,4).Formula="=AVERAGE($range)"
        $population.Cells.Item($pr,5).Formula="=STDEV.S($range)"
        $population.Cells.Item($pr,6).Formula="=MIN($range)"
        $population.Cells.Item($pr,7).Formula="=PERCENTILE.INC($range,0.1)"
        $population.Cells.Item($pr,8).Formula="=PERCENTILE.INC($range,0.25)"
        $population.Cells.Item($pr,9).Formula="=MEDIAN($range)"
        $population.Cells.Item($pr,10).Formula="=PERCENTILE.INC($range,0.75)"
        $population.Cells.Item($pr,11).Formula="=PERCENTILE.INC($range,0.9)"
        $population.Cells.Item($pr,12).Formula="=PERCENTILE.INC($range,0.95)"
        $population.Cells.Item($pr,13).Formula="=MAX($range)"
        $pr++
    }
    $population.Range('D4:M' + ($pr-1)).NumberFormat='0.00%'
    $population.Range('A3:M3').Font.Bold=$true; $population.Range('A3:M3').Interior.Color=0xD9EAF7
    $population.Columns.Item('A').ColumnWidth=36; $population.Columns.Item('B').ColumnWidth=14; $population.Columns.Item('C:M').ColumnWidth=12
    $population.Application.ActiveWindow.SplitRow=3; $population.Application.ActiveWindow.FreezePanes=$true

    $summary.Range('A1:H1').Merge(); $summary.Range('A1').Value2='SEP vs MTObjects — Standard Toy Objects Comparison'
    $summary.Range('A1').Font.Bold=$true; $summary.Range('A1').Font.Size=18
    $summary.Range('A3:D3').Value2=@('Measure','SEP','MTObjects','SEP - MTO')
    $summary.Range('A3:D3').Font.Bold=$true; $summary.Range('A3:D3').Interior.Color=0xD9EAF7
    $summaryRows = @(
        @('Mean masked image area',"=AVERAGE('Galaxy Comparison'!D2:D$lastRow)","=AVERAGE('Galaxy Comparison'!E2:E$lastRow)",'=B4-C4'),
        @('Median masked image area',"=MEDIAN('Galaxy Comparison'!D2:D$lastRow)","=MEDIAN('Galaxy Comparison'!E2:E$lastRow)",'=B5-C5'),
        @('Mean toy-pixel recall',"=AVERAGE('Galaxy Comparison'!G2:G$lastRow)","=AVERAGE('Galaxy Comparison'!H2:H$lastRow)",'=B6-C6'),
        @('Median toy-pixel recall',"=MEDIAN('Galaxy Comparison'!G2:G$lastRow)","=MEDIAN('Galaxy Comparison'!H2:H$lastRow)",'=B7-C7'),
        @('Mean toy detection rate',"=AVERAGE('Galaxy Comparison'!L2:L$lastRow)","=AVERAGE('Galaxy Comparison'!M2:M$lastRow)",'=B8-C8'),
        @('Mean toy-associated precision',"=AVERAGE('Galaxy Comparison'!P2:P$lastRow)","=AVERAGE('Galaxy Comparison'!Q2:Q$lastRow)",'=B9-C9'),
        @('Mean toy F1 score',"=AVERAGE('Galaxy Comparison'!R2:R$lastRow)","=AVERAGE('Galaxy Comparison'!S2:S$lastRow)",'=B10-C10'),
        @('Mean non-toy mask fraction',"=AVERAGE('Galaxy Comparison'!T2:T$lastRow)","=AVERAGE('Galaxy Comparison'!U2:U$lastRow)",'=B11-C11')
    )
    $sr=4
    foreach($line in $summaryRows){ for($c=0;$c -lt 4;$c++){ if($c -eq 0){$summary.Cells.Item($sr,$c+1).Value2=$line[$c]}else{$summary.Cells.Item($sr,$c+1).Formula=$line[$c]} }; $sr++ }
    $summary.Range('B4:D11').NumberFormat='0.00%'
    $summary.Range('A14:D14').Value2=@('Paired outcome','Count','of 182','Interpretation')
    $summary.Range('A14:D14').Font.Bold=$true; $summary.Range('A14:D14').Interior.Color=0xD9EAF7
    $paired = @(
        @('SEP higher toy-pixel recall',"=SUMPRODUCT(--('Galaxy Comparison'!G2:G$lastRow>'Galaxy Comparison'!H2:H$lastRow))",182,'Recovery comparison'),
        @('MTObjects higher toy-pixel recall',"=SUMPRODUCT(--('Galaxy Comparison'!H2:H$lastRow>'Galaxy Comparison'!G2:G$lastRow))",182,'Recovery comparison'),
        @('SEP masks less total area',"=SUMPRODUCT(--('Galaxy Comparison'!D2:D$lastRow<'Galaxy Comparison'!E2:E$lastRow))",182,'Aggressiveness comparison'),
        @('MTObjects masks less total area',"=SUMPRODUCT(--('Galaxy Comparison'!E2:E$lastRow<'Galaxy Comparison'!D2:D$lastRow))",182,'Aggressiveness comparison'),
        @('SEP higher toy F1',"=SUMPRODUCT(--('Galaxy Comparison'!R2:R$lastRow>'Galaxy Comparison'!S2:S$lastRow))",182,'Balanced overlap comparison'),
        @('MTObjects higher toy F1',"=SUMPRODUCT(--('Galaxy Comparison'!S2:S$lastRow>'Galaxy Comparison'!R2:R$lastRow))",182,'Balanced overlap comparison')
    )
    $sr=15
    foreach($line in $paired){
        $summary.Cells.Item($sr,1).Value2=[string]$line[0]
        $summary.Cells.Item($sr,2).Formula=[string]$line[1]
        $summary.Cells.Item($sr,3).Value2=[double]$line[2]
        $summary.Cells.Item($sr,4).Value2=[string]$line[3]
        $sr++
    }
    $summary.Range('A23').Value2='Interpretation: masked area measures aggressiveness, whereas toy recall measures whether the intended injected objects were recovered. Toy-associated precision and F1 expose masks dominated by non-toy pixels. No single column should be used alone to select the preferred method.'
    $summary.Range('A23:D25').WrapText=$true; $summary.Range('A23:D25').VerticalAlignment=-4160
    $summary.Columns.Item('A').ColumnWidth=38; $summary.Range('B:D').ColumnWidth=18; $summary.Range('23:25').RowHeight=24

    $notes.Columns.Item('A').ColumnWidth=30; $notes.Columns.Item('B').ColumnWidth=110
    $notes.Cells.Item(1,1).Value2='Item'; $notes.Cells.Item(1,2).Value2='Definition / source'
    $notes.Range('A1:B1').Font.Bold=$true; $notes.Range('A1:B1').Interior.Color=0xD9EAF7
    $noteRows = @(
        @('Comparison population','182 galaxies; the identical science image, six injected toys, seed 202608299, and truth dilation 1 were used for both methods.'),
        @('Toy brightness','Standard 5–25 background-sigma toy population. The later bright-toy MTObjects sensitivity run (20–80 sigma) is deliberately excluded because it is not directly comparable with the SEP batch.'),
        @('SEP input','Science image, as required by the corrected SEP methodology.'),
        @('Masked image area','Fraction of all image pixels included in the final mask.'),
        @('Toy-pixel recall','Fraction of toy-truth pixels included in the final mask.'),
        @('Toy recovered','An individual toy is counted as recovered when at least 50% of its truth pixels are masked.'),
        @('Toy-associated precision','Toy-truth overlap divided by all masked pixels. Low values indicate that most masked pixels are not toy pixels.'),
        @('Toy F1','Harmonic mean of toy-pixel recall and toy-associated precision.'),
        @('Non-toy mask fraction','Masked pixels outside toy truth divided by all non-toy pixels.'),
        @('Recalculation platform','Ubuntu 24.04 under WSL 2, using an isolated Linux build of MTObjects. Windows Smart App Control was not disabled.'),
        @('SEP archive drift','The recalculated SEP masked fraction can differ slightly from the archived batch because the current Linux numerical/library environment is newer. Both values and their difference are reported.'),
        @('SEP archived source',$SepSummaryCsv),
        @('MTObjects archived source',$MtoSummaryCsv),
        @('Recalculated source',$MetricsCsv)
    )
    $nr=2; foreach($line in $noteRows){$notes.Cells.Item($nr,1).Value2=$line[0];$notes.Cells.Item($nr,2).Value2=$line[1];$nr++}
    $notes.Range('A1:B' + ($nr-1)).WrapText=$true; $notes.Range('A1:B' + ($nr-1)).VerticalAlignment=-4160

    foreach($sheet in @($summary,$comparison,$population,$notes)) { $sheet.UsedRange.Font.Name='Aptos'; $sheet.UsedRange.Borders.Color=0xD9D9D9 }
    $excel.CalculateFull()
    $parent = Split-Path -Parent $OutputXlsx
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent | Out-Null }
    $book.SaveAs($OutputXlsx, 51)
    Write-Output "WROTE $OutputXlsx"
    Write-Output "ROWS $($metrics.Count)"
}
finally {
    if ($book) { $book.Close($false) }
    if ($excel) { $excel.Quit() }
    foreach($obj in @($notes,$population,$comparison,$summary,$book,$excel)) { if($obj){ [void][Runtime.InteropServices.Marshal]::ReleaseComObject($obj) } }
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
