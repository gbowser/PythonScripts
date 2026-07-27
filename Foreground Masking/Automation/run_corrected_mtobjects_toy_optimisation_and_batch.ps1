param(
    [switch]$DryRun,
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop"
)

$ErrorActionPreference = "Continue"

$Python = "C:\Users\gordo\AppData\Local\Programs\Python\Python313\python.exe"
$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$OptimiserScript = Join-Path $ForegroundDir "optimise_toy_objects_MTObjects.py"
$BatchScript = Join-Path $ForegroundDir "Batch tools\apply_optimised_mtobjects_all_galaxies.py"

$ResearchRoot = if ($PC -eq "Laptop") { "C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research" } else { "D:\Dropbox\Public Documents\UCLAN\MSc Research" }
$Root = Join-Path $ResearchRoot "Remove foreground objects"
$OptimisationParent = Join-Path $Root "mtobjects toy optimisation"
$BatchParent = Join-Path $Root "mtobjects all galaxy batch"
$LogRoot = Join-Path $Root "all galaxy batch scheduled run logs"
$MasterLog = Join-Path $LogRoot ("corrected_mtobjects_toy_optimisation_and_batch_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

function Write-MasterLog {
    param([string]$Message)
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $MasterLog) | Out-Null
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -Path $MasterLog -Value $line
}

function Run-Step {
    param(
        [string]$Name,
        [string]$LogPath,
        [string[]]$Command
    )
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LogPath) | Out-Null
    Write-MasterLog "START $Name"
    Write-MasterLog ("COMMAND " + ($Command -join " "))
    if ($DryRun) {
        Write-MasterLog "DRY RUN $Name"
        return 0
    }
    $exe = $Command[0]
    $args = @()
    if ($Command.Count -gt 1) {
        $args = $Command[1..($Command.Count - 1)]
    }
    & $exe @args 2>&1 | Tee-Object -FilePath $LogPath -Append
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
        Write-MasterLog "DONE $Name"
    }
    else {
        Write-MasterLog "FAILED $Name exit_code=$exitCode"
    }
    return $exitCode
}

Write-MasterLog "Corrected MTObjects toy-object optimisation and batch runner started."

$optimiserLog = Join-Path $LogRoot ("corrected_mtobjects_toy_optimisation_{0}.txt" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$optimiserExit = Run-Step `
    -Name "Corrected MTObjects Toy Object optimisation" `
    -LogPath $optimiserLog `
    -Command @(
        $Python,
        $OptimiserScript,
        "--pc", $PC,
        "--max-images", "20",
        "--toys-per-image", "6",
        "--initial-points", "8",
        "--max-iter", "32",
        "--mtobjects-detect-on", "original",
        "--max-masked-fraction", "0.15",
        "--data-loss-penalty", "2.0",
        "--false-positive-penalty", "0.5"
    )

if ($DryRun) {
    Write-MasterLog "Dry run complete."
    exit 0
}

if ($optimiserExit -ne 0) {
    Write-MasterLog "Stopping before batch because optimisation failed."
    exit $optimiserExit
}

$runDir = Get-ChildItem -Path $OptimisationParent -Directory |
    Where-Object { $_.Name -notmatch "\.bad_" -and (Test-Path (Join-Path $_.FullName "mtobjects_parameter_optimisation_best.json")) } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $runDir) {
    Write-MasterLog "No corrected MTObjects toy-object best JSON found."
    exit 1
}

$bestJson = Join-Path $runDir.FullName "mtobjects_parameter_optimisation_best.json"
$batchOut = Join-Path $BatchParent ("mtobjects_toy_object_{0}" -f $runDir.Name)
$batchLog = Join-Path $batchOut "terminal_log.txt"

Write-MasterLog "Using corrected best JSON: $bestJson"
Write-MasterLog "Batch output: $batchOut"

$batchExit = Run-Step `
    -Name "Corrected MTObjects Toy Object all-galaxy batch" `
    -LogPath $batchLog `
    -Command @(
        $Python,
        $BatchScript,
        "--pc", $PC,
        "--best-json", $bestJson,
        "--source", "toy-object",
        "--run-label", ("MTObjects Toy Object capped 15pct {0}" -f $runDir.Name),
        "--output-dir", $batchOut
    )

if ($batchExit -eq 0) {
    Write-MasterLog "Corrected MTObjects toy-object optimisation and batch finished successfully."
}
else {
    Write-MasterLog "Corrected MTObjects toy-object batch failed with exit_code=$batchExit."
}
exit $batchExit

