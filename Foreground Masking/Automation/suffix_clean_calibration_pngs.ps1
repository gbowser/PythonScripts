param(
    [int]$ExpectedBatchCount = 182,
    [int]$ExpectedCleanCount = 40,
    [int]$PollSeconds = 20,
    [int]$TimeoutMinutes = 180
)

$ErrorActionPreference = 'Stop'
$cleanList = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\CleanGalaxies.txt'
$mtFolder = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\mtobjects all galaxy batch\mtobjects_toy_recovery_20260816_063455_eight_panel_aligned'
$sepFolder = 'D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects\SEP all galaxy batch\sep_toy_cv_20260815_175144_eight_panel_aligned'
$logPath = Join-Path $PSScriptRoot 'suffix_clean_calibration_pngs.log'

function Write-Status([string]$Message) {
    $line = '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    $line | Tee-Object -FilePath $logPath -Append
}

$names = @(Get-Content -LiteralPath $cleanList |
    ForEach-Object { $_.Trim() } |
    Where-Object { $_ } |
    Sort-Object -Unique)

if ($names.Count -ne $ExpectedCleanCount) {
    throw "Expected $ExpectedCleanCount unique calibration names, found $($names.Count)."
}

$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
do {
    $mtCount = @(Get-ChildItem -LiteralPath $mtFolder -Filter '*.png' -File -ErrorAction SilentlyContinue).Count
    $sepCount = @(Get-ChildItem -LiteralPath $sepFolder -Filter '*.png' -File -ErrorAction SilentlyContinue).Count
    Write-Status "Waiting for completed batches: MTObjects=$mtCount/$ExpectedBatchCount; SEP=$sepCount/$ExpectedBatchCount"
    if ($mtCount -eq $ExpectedBatchCount -and $sepCount -eq $ExpectedBatchCount) { break }
    if ($mtCount -gt $ExpectedBatchCount -or $sepCount -gt $ExpectedBatchCount) {
        throw 'A batch contains more PNGs than expected; refusing to rename an ambiguous output set.'
    }
    Start-Sleep -Seconds $PollSeconds
} while ((Get-Date) -lt $deadline)

if ($mtCount -ne $ExpectedBatchCount -or $sepCount -ne $ExpectedBatchCount) {
    throw "Timed out before both batches reached $ExpectedBatchCount PNGs."
}

foreach ($folder in @($mtFolder, $sepFolder)) {
    $renamed = 0
    foreach ($name in $names) {
        $matches = @(Get-ChildItem -LiteralPath $folder -Filter "$name`_*.png" -File |
            Where-Object { $_.BaseName -notlike '*_clean' })
        if ($matches.Count -ne 1) {
            throw "Expected one unsuffixed PNG for '$name' in '$folder'; found $($matches.Count)."
        }
        $newName = $matches[0].BaseName + '_clean' + $matches[0].Extension
        Rename-Item -LiteralPath $matches[0].FullName -NewName $newName
        $renamed++
    }

    $all = @(Get-ChildItem -LiteralPath $folder -Filter '*.png' -File)
    $clean = @($all | Where-Object { $_.BaseName -like '*_clean' })
    if ($all.Count -ne $ExpectedBatchCount -or $clean.Count -ne $ExpectedCleanCount -or $renamed -ne $ExpectedCleanCount) {
        throw "Post-rename verification failed in '$folder': all=$($all.Count), clean=$($clean.Count), renamed=$renamed."
    }
    Write-Status "Verified '$folder': $($all.Count) PNGs total; $($clean.Count) calibration PNGs suffixed _clean."
}

Write-Status 'Calibration filename suffix operation completed successfully.'
