param(
    [int]$ExpectedBatchCount = 182,
    [int]$ExpectedCleanCount = 40
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

foreach ($folder in @($mtFolder, $sepFolder)) {
    $renamed = 0
    foreach ($name in $names) {
        $matches = @(Get-ChildItem -LiteralPath $folder -Filter "$name`_*.png" -File)
        if ($matches.Count -ne 1) {
            throw "Expected one PNG for calibration galaxy '$name' in '$folder'; found $($matches.Count)."
        }
        if ($matches[0].BaseName -notlike '*_clean') {
            $newName = $matches[0].BaseName + '_clean' + $matches[0].Extension
            Rename-Item -LiteralPath $matches[0].FullName -NewName $newName
            $renamed++
        }
    }

    $all = @(Get-ChildItem -LiteralPath $folder -Filter '*.png' -File)
    $clean = @($all | Where-Object { $_.BaseName -like '*_clean' })
    if ($all.Count -gt $ExpectedBatchCount -or $clean.Count -ne $ExpectedCleanCount) {
        throw "Post-rename verification failed in '$folder': all=$($all.Count), clean=$($clean.Count), renamed=$renamed."
    }
    Write-Status "Verified '$folder': $($all.Count)/$ExpectedBatchCount PNGs available; $($clean.Count) calibration PNGs suffixed _clean; renamed now=$renamed."
}

Write-Status 'Calibration filename suffix operation completed successfully.'
