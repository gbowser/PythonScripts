param(
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"

$Python = "C:\Users\gordo\AppData\Local\Programs\Python\Python313\python.exe"
$Repo = "C:\Users\gordo\Documents\Github\PythonScripts"
$ForegroundDir = Join-Path $Repo "Foreground Masking"
$SEPSpikeOptimiser = Join-Path $ForegroundDir "optimise_sep_spike_gate_parameters.py"
$SEPToyOptimiser = Join-Path $ForegroundDir "sep_toy_object_parameter_optimisation.py"
$SEPBatch = Join-Path $ForegroundDir "batch_sep_all_galaxies.py"

$Root = "D:\Dropbox\Public Documents\UCLAN\MSc Research\Remove foreground objects"
$LogRoot = Join-Path $ForegroundDir "run_logs"
$MasterLog = Join-Path $LogRoot ("aggressive_sep_optimisations_and_batches_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

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

Write-MasterLog "Aggressive SEP optimisation and batch run started."
Write-MasterLog "Master log: $MasterLog"

$spikeLog = Join-Path $LogRoot ("aggressive_sep_spike_optimisation_{0}.txt" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
$spikeExit = Run-Step `
    -Name "Aggressive SEP Spike Gate optimisation" `
    -LogPath $spikeLog `
    -Command @(
        $Python,
        $SEPSpikeOptimiser,
        "--max-images", "20",
        "--initial-points", "12",
        "--max-iter", "48",
        "--detect-on", "residual",
        "--progress-galaxies"
    )
if ($spikeExit -ne 0) {
    Write-MasterLog "Stopping because SEP Spike Gate optimisation failed."
    exit $spikeExit
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

$spikeRun = Latest-RunDir -Parent (Join-Path $Root "sep spike optimisation") -BestName "sep_spike_optimisation_best.json"
$toyRun = Latest-RunDir -Parent (Join-Path $Root "sep toy optimisation") -BestName "sep_toy_object_optimisation_best.json"
if (-not $spikeRun -or -not $toyRun) {
    Write-MasterLog "Could not find one or both new SEP best JSON files."
    exit 1
}

$spikeBest = Join-Path $spikeRun.FullName "sep_spike_optimisation_best.json"
$toyBest = Join-Path $toyRun.FullName "sep_toy_object_optimisation_best.json"
$spikeOut = Join-Path $Root ("SEP all galaxy batch\sep_spike_gate_aggressive_{0}" -f $spikeRun.Name)
$toyOut = Join-Path $Root ("SEP all galaxy batch\sep_toy_object_aggressive_{0}" -f $toyRun.Name)

Run-Step `
    -Name "Aggressive SEP Spike Gate all-galaxy batch" `
    -LogPath (Join-Path $spikeOut "terminal_log.txt") `
    -Command @(
        $Python,
        $SEPBatch,
        "--best-json", $spikeBest,
        "--source", "spike-gate",
        "--run-label", ("Aggressive SEP Spike Gate {0}" -f $spikeRun.Name),
        "--output-dir", $spikeOut,
        "--require-best-json"
    )

Run-Step `
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

Write-MasterLog "Aggressive SEP optimisation and batch run finished."
