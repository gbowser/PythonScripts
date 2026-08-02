param(
    [switch]$DryRun,
    [ValidateSet("Desktop", "Laptop")]
    [string]$PC = "Desktop"
)

$ErrorActionPreference = "Continue"

$Python = "C:\Users\gordo\AppData\Local\Programs\Python\Python313\python.exe"
$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$SEPToyOptimiser = Join-Path $ForegroundDir "Optimisation\optimise_toy_objects_SEP.py"
$SEPBatch = Join-Path $ForegroundDir "Batch tools\batch_sep_all_galaxies.py"

$ResearchRoot = if ($PC -eq "Laptop") { "C:\Users\gordo\Dropbox\Public Documents\UCLAN\MSc Research" } else { "D:\Dropbox\Public Documents\UCLAN\MSc Research" }
$Root = Join-Path $ResearchRoot "Remove foreground objects"
$LogRoot = Join-Path $ForegroundDir "run_logs"
$MasterLog = Join-Path $LogRoot ("continue_aggressive_sep_after_spike_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$SpikeRun = "20260724_150938"
$SpikeBest = Join-Path $Root "sep spike optimisation\$SpikeRun\sep_spike_optimisation_best.json"

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
    $oldNativePreference = $PSNativeCommandUseErrorActionPreference
    $PSNativeCommandUseErrorActionPreference = $false
    & $exe @args 2>&1 | Tee-Object -FilePath $LogPath -Append
    $exitCode = $LASTEXITCODE
    $PSNativeCommandUseErrorActionPreference = $oldNativePreference
    if ($exitCode -eq 0) {
        Write-MasterLog "DONE $Name"
    }
    else {
        Write-MasterLog "FAILED $Name exit_code=$exitCode"
    }
    return $exitCode
}

function Latest-RunDir {
    param(
        [string]$Parent,
        [string]$BestName
    )
    Get-ChildItem -Path $Parent -Directory |
        Where-Object { $_.Name -notmatch "\.bad_" -and (Test-Path (Join-Path $_.FullName $BestName)) } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

Write-MasterLog "Continuing aggressive SEP run after completed Spike Gate optimisation."
Write-MasterLog "Using Spike Gate best JSON: $SpikeBest"

if (-not (Test-Path $SpikeBest)) {
    Write-MasterLog "Missing completed Spike Gate best JSON."
    exit 1
}

$toyLog = Join-Path $LogRoot ("aggressive_sep_toy_optimisation_{0}.txt" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$toyExit = Run-Step `
    -Name "Aggressive SEP Toy Object optimisation" `
    -LogPath $toyLog `
    -Command @(
        $Python,
        $SEPToyOptimiser,
        "--max-images", "20",
        "--toys-per-image", "6",
        "--initial-points", "8",
        "--max-iter", "32",
        "--detect-on", "residual",
        "--max-masked-fraction", "0.15",
        "--data-loss-penalty", "0.35",
        "--false-positive-penalty", "0.05"
    )
if ($toyExit -ne 0) {
    Write-MasterLog "Stopping because SEP Toy Object optimisation failed."
    exit $toyExit
}

if ($DryRun) {
    Write-MasterLog "Dry run complete."
    exit 0
}

$toyRun = Latest-RunDir -Parent (Join-Path $Root "sep toy optimisation") -BestName "sep_toy_object_optimisation_best.json"
if (-not $toyRun) {
    Write-MasterLog "Could not find new SEP Toy Object best JSON."
    exit 1
}

$toyBest = Join-Path $toyRun.FullName "sep_toy_object_optimisation_best.json"
$spikeOut = Join-Path $Root ("SEP all galaxy batch\sep_spike_gate_aggressive_$SpikeRun")
$toyOut = Join-Path $Root ("SEP all galaxy batch\sep_toy_object_aggressive_{0}" -f $toyRun.Name)

$spikeBatchExit = Run-Step `
    -Name "Aggressive SEP Spike Gate all-galaxy batch" `
    -LogPath (Join-Path $spikeOut "terminal_log.txt") `
    -Command @(
        $Python,
        $SEPBatch,
        "--best-json", $SpikeBest,
        "--source", "spike-gate",
        "--run-label", "Aggressive SEP Spike Gate $SpikeRun",
        "--output-dir", $spikeOut,
        "--require-best-json"
    )
if ($spikeBatchExit -ne 0) {
    Write-MasterLog "Aggressive SEP Spike Gate batch failed; continuing to Toy Object batch."
}

$toyBatchExit = Run-Step `
    -Name "Aggressive SEP Toy Object all-galaxy batch" `
    -LogPath (Join-Path $toyOut "terminal_log.txt") `
    -Command @(
        $Python,
        $SEPBatch,
        "--best-json", $toyBest,
        "--source", "toy-object",
        "--run-label", ("Aggressive SEP Toy Object {0}" -f $toyRun.Name),
        "--output-dir", $toyOut,
        "--require-best-json"
    )

if ($spikeBatchExit -ne 0 -or $toyBatchExit -ne 0) {
    Write-MasterLog "Continuation finished with batch failure(s)."
    exit 1
}

Write-MasterLog "Aggressive SEP continuation finished successfully."

